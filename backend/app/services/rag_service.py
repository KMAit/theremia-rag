"""
RAG Service — wraps LangChain + ChromaDB.

The RAG pipeline is intentionally treated as a black box for this exercise.
This module focuses on clean integration and predictable IO contracts.
"""


import logging
from typing import Any

from langchain.schema import HumanMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import Chroma

from app.core.config import settings

from app.core.constants import OpenAIModel

logger = logging.getLogger("theremia.rag")

# ── Cost table (USD per 1k tokens) ─────────────────────────────────────────────
# NOTE:
# - For Ollama (local), cost is effectively 0 for this exercise.
# - For OpenAI/OpenRouter, this is a simple estimate.
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
        "provider": "OpenAI/OpenRouter",
        "input_cost_per_1k": 0.00015,
        "output_cost_per_1k": 0.0006,
        "context_window": 128000,
    },
    {
        "id": "gpt-4o",
        "name": "GPT-4o",
        "provider": "OpenAI/OpenRouter",
        "input_cost_per_1k": 0.005,
        "output_cost_per_1k": 0.015,
        "context_window": 128000,
    },
    {
        "id": "gpt-4-turbo",
        "name": "GPT-4 Turbo",
        "provider": "OpenAI/OpenRouter",
        "input_cost_per_1k": 0.01,
        "output_cost_per_1k": 0.03,
        "context_window": 128000,
    },
    {
        "id": "gpt-3.5-turbo",
        "name": "GPT-3.5 Turbo",
        "provider": "OpenAI/OpenRouter",
        "input_cost_per_1k": 0.0005,
        "output_cost_per_1k": 0.0015,
        "context_window": 16385,
    },
]


def get_available_models_for_current_provider() -> list[dict]:
    provider = (settings.LLM_PROVIDER or "openai").lower()

    if provider == "ollama":
        return [
            {
                "id": settings.OLLAMA_MODEL,
                "name": f"Ollama {settings.OLLAMA_MODEL}",
                "provider": "Ollama (local)",
                "input_cost_per_1k": 0.0,
                "output_cost_per_1k": 0.0,
                "context_window": 0,
            }
        ]

    return AVAILABLE_MODELS


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    costs = MODEL_COSTS.get(model, MODEL_COSTS["gpt-4o-mini"])
    return (input_tokens / 1000 * costs["input"]) + (output_tokens / 1000 * costs["output"])


def get_allowed_models() -> set[str]:
    provider = (settings.LLM_PROVIDER or "openai").lower()
    if provider == "ollama":
        return {settings.OLLAMA_MODEL}
    return {m.value for m in OpenAIModel}

def _resolve_provider_model_id(public_model_id: str) -> str:
    """
    Keep the public API stable (model_id like 'gpt-4o-mini'), but adapt to provider needs.

    - OpenAI expects: 'gpt-4o-mini'
    - OpenRouter often expects: 'openai/gpt-4o-mini'
    - Ollama ignores this and uses settings.OLLAMA_MODEL
    """
    provider = (settings.LLM_PROVIDER or "openai").lower()

    if provider == "openrouter":
        return f"openai/{public_model_id}"

    return public_model_id


def get_embeddings():
    provider = (settings.EMBEDDINGS_PROVIDER or "openai").lower()

    if provider == "huggingface":
        from langchain_community.embeddings import HuggingFaceEmbeddings

        model_name = settings.HF_EMBEDDING_MODEL or "sentence-transformers/all-MiniLM-L6-v2"
        return HuggingFaceEmbeddings(model_name=model_name)

    # Default: OpenAI embeddings
    from langchain_openai import OpenAIEmbeddings

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required when EMBEDDINGS_PROVIDER=openai")

    return OpenAIEmbeddings(
        model=settings.DEFAULT_EMBEDDING_MODEL,
        api_key=settings.OPENAI_API_KEY,
    )


def get_or_create_vectorstore(collection_name: str) -> Chroma:
    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embeddings(),
        persist_directory=settings.CHROMA_PERSIST_DIR,
    )


async def ingest_document(file_path: str, doc_id: str) -> dict[str, Any]:
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

    for chunk in chunks:
        chunk.metadata["doc_id"] = doc_id

    collection_name = f"doc_{doc_id.replace('-', '_')}"
    vectorstore = get_or_create_vectorstore(collection_name)

    # NOTE: LangChain vectorstore add is sync in many implementations
    vectorstore.add_documents(chunks)

    return {
        "page_count": page_count,
        "chunk_count": len(chunks),
        "collection_name": collection_name,
    }


async def delete_document_vectors(collection_name: str) -> None:
    """Delete a Chroma collection entirely (best-effort)."""
    try:
        import chromadb

        client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        client.delete_collection(collection_name)
    except Exception:
        logger.debug("Collection %s not found, skipping delete", collection_name)


def _build_llm(public_model_id: str):
    """
    Build an LLM client depending on provider.
    - For Ollama: uses settings.OLLAMA_MODEL (0€ local)
    - For OpenRouter/OpenAI: uses the public model id (stable API contract)
    """
    provider = (settings.LLM_PROVIDER or "openai").lower()

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0,
        )

    resolved_model = _resolve_provider_model_id(public_model_id)

    if provider == "openrouter":
        from langchain_openai import ChatOpenAI

        if not settings.OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY is required when LLM_PROVIDER=openrouter")

        return ChatOpenAI(
            model=resolved_model,
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            temperature=0,
        )

    # Default: OpenAI
    from langchain_openai import ChatOpenAI

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

    return ChatOpenAI(
        model=resolved_model,
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
    )


async def query_documents(
    question: str,
    document_ids: list[str],
    collection_names: list[str],
    chat_history: list[dict],
    model: str | None = None,
) -> dict[str, Any]:
    """
    Retrieve relevant chunks across collections and generate answer.
    Returns { answer, sources, tokens_used, cost_usd }.
    """
    model = model or settings.DEFAULT_LLM_MODEL
    provider = (settings.LLM_PROVIDER or "openai").lower()

    if not collection_names:
        return {
            "answer": "No documents are attached to this conversation. Please upload and select documents first.",
            "sources": [],
            "tokens_used": 0,
            "cost_usd": 0.0,
            "model": settings.OLLAMA_MODEL if provider == "ollama" else model,
        }

    all_docs_with_scores = []
    for cname in collection_names:
        try:
            vs = get_or_create_vectorstore(cname)
            results = vs.similarity_search_with_score(question, k=settings.RETRIEVAL_K)
            all_docs_with_scores.extend(results)
        except Exception as exc:
            logger.warning("Failed to query collection %s: %s", cname, exc)
            continue

    all_docs_with_scores.sort(key=lambda x: x[1])
    top_docs = all_docs_with_scores[: settings.RETRIEVAL_K]

    context = "\n\n---\n\n".join([doc.page_content for doc, _ in top_docs])

    history_text = ""
    for msg in chat_history[-6:]:
        role = "User" if msg["role"] == "user" else "Assistant"
        history_text += f"{role}: {msg['content']}\n"

    system_prompt = f"""You are a helpful document assistant for Theremia, a precision medicine company.
Answer the user's question based ONLY on the provided document context.
If the answer is partially in the context, use what's available and indicate it's partial.
Be precise and cite which part of the documents supports your answer.

Context from documents:
{context}

Previous conversation:
{history_text}"""

    llm = _build_llm(model)
    response = llm.invoke([HumanMessage(content=f"{system_prompt}\n\nUser question: {question}")])

    answer = getattr(response, "content", "")

    # Token usage extraction varies by provider
    usage = (getattr(response, "response_metadata", {}) or {}).get("token_usage", {}) or {}
    input_tokens = int(usage.get("prompt_tokens", 0) or 0)
    output_tokens = int(usage.get("completion_tokens", 0) or 0)
    total_tokens = input_tokens + output_tokens

    # For Ollama/local, keep cost at 0
    provider = (settings.LLM_PROVIDER or "openai").lower()
    if provider == "ollama":
        cost_usd = 0.0
    else:
        cost_usd = round(compute_cost(model, input_tokens, output_tokens), 6)

    sources = []
    for doc, score in top_docs:
        meta = doc.metadata or {}
        sources.append(
            {
                "doc_id": meta.get("doc_id", ""),
                "doc_name": str(meta.get("source", "Unknown")).split("/")[-1],
                "chunk": doc.page_content[:400],
                "score": round(float(score), 4),
                "page": meta.get("page", None),
            }
        )

    return {
        "answer": answer,
        "sources": sources,
        "tokens_used": total_tokens,
        "cost_usd": cost_usd,
        "model": settings.OLLAMA_MODEL if provider == "ollama" else model,
    }
