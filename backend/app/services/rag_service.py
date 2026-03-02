"""
RAG Service — wraps LangChain + ChromaDB.
Treats AI pipeline as a black box; focus on clean integration.
"""

import logging

from langchain.schema import HumanMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import settings

logger = logging.getLogger("theremia.rag")

# ── Cost table (USD per 1k tokens) ──────────────────────────────────────────
MODEL_COSTS = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
}

AVAILABLE_MODELS = [
    {
        "id": "gpt-4o-mini",
        "name": "GPT-4o Mini",
        "provider": "OpenAI",
        "input_cost_per_1k": 0.00015,
        "output_cost_per_1k": 0.0006,
        "context_window": 128000,
    },
    {
        "id": "gpt-4o",
        "name": "GPT-4o",
        "provider": "OpenAI",
        "input_cost_per_1k": 0.005,
        "output_cost_per_1k": 0.015,
        "context_window": 128000,
    },
    {
        "id": "gpt-4-turbo",
        "name": "GPT-4 Turbo",
        "provider": "OpenAI",
        "input_cost_per_1k": 0.01,
        "output_cost_per_1k": 0.03,
        "context_window": 128000,
    },
    {
        "id": "gpt-3.5-turbo",
        "name": "GPT-3.5 Turbo",
        "provider": "OpenAI",
        "input_cost_per_1k": 0.0005,
        "output_cost_per_1k": 0.0015,
        "context_window": 16385,
    },
]


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    costs = MODEL_COSTS.get(model, MODEL_COSTS["gpt-4o-mini"])
    return (input_tokens / 1000 * costs["input"]) + (output_tokens / 1000 * costs["output"])


def get_embeddings():
    return OpenAIEmbeddings(
        model=settings.DEFAULT_EMBEDDING_MODEL,
        openai_api_key=settings.OPENAI_API_KEY,
    )


def get_or_create_vectorstore(collection_name: str) -> Chroma:
    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embeddings(),
        persist_directory=settings.CHROMA_PERSIST_DIR,
    )


async def ingest_document(file_path: str, doc_id: str) -> dict:
    """
    Parse PDF → split → embed → store in Chroma.
    Returns { page_count, chunk_count, collection_name }.
    """
    loader = PyMuPDFLoader(file_path)
    pages = loader.load()
    page_count = len(pages)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(pages)

    # Tag each chunk with doc_id for later filtering
    for chunk in chunks:
        chunk.metadata["doc_id"] = doc_id

    collection_name = f"doc_{doc_id.replace('-', '_')}"
    vectorstore = get_or_create_vectorstore(collection_name)
    vectorstore.add_documents(chunks)

    return {
        "page_count": page_count,
        "chunk_count": len(chunks),
        "collection_name": collection_name,
    }


async def delete_document_vectors(collection_name: str):
    """Delete a Chroma collection entirely."""
    try:
        import chromadb

        client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        client.delete_collection(collection_name)
    except Exception:
        logger.debug("Collection %s not found, skipping delete", collection_name)


async def query_documents(
    question: str,
    document_ids: list[str],
    collection_names: list[str],
    chat_history: list[dict],
    model: str | None = None,
) -> dict:
    """
    Retrieve relevant chunks across collections and generate answer.
    Returns { answer, sources, tokens_used, cost_usd }.
    """
    model = model or settings.DEFAULT_LLM_MODEL

    if not collection_names:
        return {
            "answer": "No documents are attached to this conversation. Please upload and select documents first.",
            "sources": [],
            "tokens_used": 0,
            "cost_usd": 0.0,
        }

    # Merge retrievers from all collections
    all_docs_with_scores = []
    for cname in collection_names:
        try:
            vs = get_or_create_vectorstore(cname)
            results = vs.similarity_search_with_score(question, k=settings.RETRIEVAL_K)
            all_docs_with_scores.extend(results)
        except Exception as e:
            logger.warning("Failed to query collection: %s", e)
            continue

    # Sort by score (lower = better for L2) and take top K
    all_docs_with_scores.sort(key=lambda x: x[1])
    top_docs = all_docs_with_scores[: settings.RETRIEVAL_K]

    # Build context
    context_parts = [doc.page_content for doc, _ in top_docs]
    context = "\n\n---\n\n".join(context_parts)

    # Format chat history for the prompt
    history_text = ""
    for msg in chat_history[-6:]:  # last 3 turns
        role = "User" if msg["role"] == "user" else "Assistant"
        history_text += f"{role}: {msg['content']}\n"

    system_prompt = f"""You are a helpful document assistant for Theremia, a precision medicine company.
Answer the user's question based ONLY on the provided document context.
If the answer is not in the context, say so clearly.
Be precise, scientific, and cite which part of the documents supports your answer.

Context from documents:
{context}

Previous conversation:
{history_text}"""

    llm = ChatOpenAI(
        model=model,
        openai_api_key=settings.OPENAI_API_KEY,
        temperature=0,
    )

    response = llm.invoke([HumanMessage(content=f"{system_prompt}\n\nUser question: {question}")])

    answer = response.content
    usage = response.response_metadata.get("token_usage", {})
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)
    total_tokens = input_tokens + output_tokens
    cost = compute_cost(model, input_tokens, output_tokens)

    # Build sources list
    sources = []
    for doc, score in top_docs:
        meta = doc.metadata
        sources.append(
            {
                "doc_id": meta.get("doc_id", ""),
                "doc_name": meta.get("source", "Unknown").split("/")[-1],
                "chunk": doc.page_content[:400],
                "score": round(float(score), 4),
                "page": meta.get("page", None),
            }
        )

    return {
        "answer": answer,
        "sources": sources,
        "tokens_used": total_tokens,
        "cost_usd": round(cost, 6),
    }
