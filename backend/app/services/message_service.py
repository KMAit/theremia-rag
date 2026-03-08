"""
Message service.

Runs the RAG pipeline, then persists user and assistant messages in one commit.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, RAGError
from app.repositories import conversation_repository, document_repository, message_repository
from app.services import rag_service

logger = logging.getLogger("theremia.service.message")


async def get_messages(
    db: AsyncSession,
    *,
    convo_id: str,
    user_id: str,
):
    convo = await conversation_repository.get_by_id(db, convo_id, user_id)
    if convo is None:
        raise NotFoundError("Conversation")

    return await message_repository.list_by_conversation(db, convo_id)


async def ask_question(
    db: AsyncSession,
    *,
    convo_id: str,
    user_id: str,
    question: str,
    model_override: str | None,
):
    convo = await conversation_repository.get_by_id(db, convo_id, user_id)
    if convo is None:
        raise NotFoundError("Conversation")

    doc_ids: list[str] = list(convo.document_ids or [])
    collection_names: list[str] = []

    if doc_ids:
        docs = await document_repository.get_ready_by_ids(db, doc_ids, user_id)
        collection_names = [str(d.collection_name) for d in docs if d.collection_name]

    history_rows = await message_repository.get_history_rows(db, convo_id)
    history = [{"role": role, "content": content} for role, content in history_rows]

    model = model_override or str(convo.model)

    logger.info(
        "RAG query user=%s convo=%s model=%s collections=%d",
        user_id,
        convo_id,
        model,
        len(collection_names),
    )

    try:
        rag_result = await rag_service.query_documents(
            question=question,
            document_ids=doc_ids,
            collection_names=collection_names,
            chat_history=history,
            model=model,
        )
    except Exception as exc:
        logger.error("RAG pipeline failed convo=%s: %s", convo_id, exc, exc_info=True)
        raise RAGError(f"Failed to generate answer: {exc!s}") from exc

    user_msg = message_repository.make_user_message(convo_id=convo_id, content=question)
    assistant_msg = message_repository.make_assistant_message(
        convo_id=convo_id,
        content=rag_result["answer"],
        sources=rag_result.get("sources", []),
        tokens_used=rag_result.get("tokens_used", 0),
        cost_usd=rag_result.get("cost_usd", 0.0),
        model=rag_result.get("model", model),
    )

    convo.total_tokens = (convo.total_tokens or 0) + int(rag_result.get("tokens_used") or 0)
    convo.total_cost_usd = (convo.total_cost_usd or 0.0) + float(rag_result.get("cost_usd") or 0.0)

    if not history:
        convo.title = question[:60] + ("..." if len(question) > 60 else "")

    db.add(user_msg)
    db.add(assistant_msg)

    try:
        await db.commit()
        await db.refresh(assistant_msg)
    except Exception as exc:
        await db.rollback()
        logger.error("DB commit failed convo=%s: %s", convo_id, exc, exc_info=True)
        raise

    return assistant_msg
