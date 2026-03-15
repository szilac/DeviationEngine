"""
Chat Service for Historical Figure Conversations.

Handles chat session management, message sending with RAG retrieval,
and conversation history.
"""

import logging
import time
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload

from app.db_models import (
    CharacterDB,
    CharacterChunkDB,
    CharacterProfileDB,
    ChatSessionDB,
    ChatMessageDB,
    TimelineDB,
)
from app.exceptions import NotFoundError, AIGenerationError, ValidationError

logger = logging.getLogger(__name__)


# ============================================================================
# Session Management
# ============================================================================


async def create_chat_session(
    character_id: str,
    character_year_context: int,
    session_name: Optional[str],
    db: AsyncSession,
    profile_id: Optional[str] = None,
) -> ChatSessionDB:
    """
    Create a new chat session with a character.

    Args:
        character_id: Character UUID.
        character_year_context: The year the character "speaks from".
        session_name: Optional user-provided name.
        db: Database session.
        profile_id: Optional profile UUID to use for this session.

    Returns:
        Created ChatSessionDB record.

    Raises:
        NotFoundError: If character or profile not found.
        ValidationError: If character profile not ready.
    """
    # Load character
    result = await db.execute(
        select(CharacterDB).where(CharacterDB.id == character_id)
    )
    character = result.scalar_one_or_none()
    if not character:
        raise NotFoundError(f"Character {character_id} not found")

    if character.profile_status != "ready":
        raise ValidationError(
            f"Character profile is not ready (status: {character.profile_status}). "
            "Generate the profile first."
        )

    # Validate profile_id if provided
    if profile_id:
        result = await db.execute(
            select(CharacterProfileDB).where(
                CharacterProfileDB.id == profile_id,
                CharacterProfileDB.character_id == character_id,
            )
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise NotFoundError(f"Profile {profile_id} not found for character {character_id}")
        if profile.profile_status != "ready":
            raise ValidationError(
                f"Profile is not ready (status: {profile.profile_status})."
            )

    session = ChatSessionDB(
        id=str(uuid4()),
        character_id=character_id,
        timeline_id=character.timeline_id,
        character_year_context=character_year_context,
        session_name=session_name,
        profile_id=profile_id,
        is_active=True,
        message_count=0,
    )
    db.add(session)
    await db.flush()

    logger.info(
        f"Created chat session {session.id} for character {character.name} "
        f"(year context: {character_year_context}, profile: {profile_id})"
    )
    return session


async def get_chat_session(
    session_id: str,
    db: AsyncSession,
) -> ChatSessionDB:
    """
    Get a chat session by ID.

    Args:
        session_id: Session UUID.
        db: Database session.

    Returns:
        ChatSessionDB record.

    Raises:
        NotFoundError: If session not found.
    """
    result = await db.execute(
        select(ChatSessionDB).where(ChatSessionDB.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError(f"Chat session {session_id} not found")
    return session


async def list_sessions_for_timeline(
    timeline_id: str,
    db: AsyncSession,
) -> List[ChatSessionDB]:
    """
    List all chat sessions for a timeline.

    Args:
        timeline_id: Timeline UUID.
        db: Database session.

    Returns:
        List of ChatSessionDB records.

    Raises:
        NotFoundError: If timeline not found.
    """
    result = await db.execute(select(TimelineDB).where(TimelineDB.id == timeline_id))
    if not result.scalar_one_or_none():
        raise NotFoundError(f"Timeline {timeline_id} not found")

    result = await db.execute(
        select(ChatSessionDB)
        .where(ChatSessionDB.timeline_id == timeline_id)
        .order_by(ChatSessionDB.updated_at.desc())
    )
    return list(result.scalars().all())


async def close_chat_session(
    session_id: str,
    db: AsyncSession,
) -> ChatSessionDB:
    """
    Close an active chat session.

    Args:
        session_id: Session UUID.
        db: Database session.

    Returns:
        Updated ChatSessionDB record.

    Raises:
        NotFoundError: If session not found.
        ValidationError: If session already closed.
    """
    session = await get_chat_session(session_id, db)
    if not session.is_active:
        raise ValidationError("Chat session is already closed")

    session.is_active = False
    await db.flush()

    logger.info(f"Closed chat session {session_id}")
    return session


async def delete_chat_session(
    session_id: str,
    db: AsyncSession,
) -> None:
    """
    Delete a chat session and all its messages.

    Args:
        session_id: Session UUID.
        db: Database session.

    Raises:
        NotFoundError: If session not found.
    """
    session = await get_chat_session(session_id, db)
    await db.delete(session)
    await db.flush()
    logger.info(f"Deleted chat session {session_id}")


# ============================================================================
# Message Handling
# ============================================================================


async def send_message(
    session_id: str,
    user_message_text: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Send a user message and generate a character response.

    1. Validates session is active
    2. Stores user message
    3. Retrieves RAG context from character chunks
    4. Builds conversation history
    5. Calls impersonator agent
    6. Stores character response

    Args:
        session_id: Session UUID.
        user_message_text: The user's message text.
        db: Database session.

    Returns:
        Dict with user_message and character_response ChatMessageDB records.

    Raises:
        NotFoundError: If session not found.
        ValidationError: If session is closed.
        AIGenerationError: If response generation fails.
    """
    # Load session
    session = await get_chat_session(session_id, db)
    if not session.is_active:
        raise ValidationError("Cannot send messages to a closed session")

    # Load character with chunks
    result = await db.execute(
        select(CharacterDB)
        .options(selectinload(CharacterDB.character_chunks))
        .where(CharacterDB.id == session.character_id)
    )
    character = result.scalar_one_or_none()
    if not character:
        raise NotFoundError(f"Character {session.character_id} not found")

    # Determine which chunks to use: profile-specific or all
    if session.profile_id:
        result = await db.execute(
            select(CharacterChunkDB)
            .where(CharacterChunkDB.profile_id == session.profile_id)
        )
        active_chunks = list(result.scalars().all())
    else:
        active_chunks = list(character.character_chunks)

    # Store user message
    user_msg = ChatMessageDB(
        id=str(uuid4()),
        session_id=session_id,
        role="user",
        content=user_message_text,
    )
    db.add(user_msg)
    await db.flush()

    # Build conversation history from previous messages
    conversation_history = await _build_conversation_history(session_id, db, limit=10)

    # Get RAG context from character chunks
    context_chunks = _format_character_chunks_for_context(
        active_chunks,
        session.character_year_context,
    )

    # Retrieve additional timeline context via vector store
    rag_context = await _retrieve_rag_context(
        character, session.character_year_context, user_message_text
    )
    if rag_context:
        context_chunks = f"{context_chunks}\n\n{rag_context}"

    # Build chunk list for impersonator agent
    chunk_dicts = [
        {
            "chunk_type": c.chunk_type,
            "content": c.content,
            "year_start": c.year_start,
            "year_end": c.year_end,
        }
        for c in active_chunks
    ]

    # Call impersonator agent
    start_time = time.time()
    from app.agents.impersonator_agent import generate_response

    model = None
    try:
        from app.services.llm_service import create_pydantic_ai_model_for_agent
        from app.models import AgentType
        model = await create_pydantic_ai_model_for_agent(db, AgentType.IMPERSONATOR)
    except Exception:
        logger.debug("No LLM config available, using agent default")

    response_text = await generate_response(
        character_name=character.name,
        character_title=character.title,
        short_bio=character.short_bio or "",
        role_summary=character.role_summary,
        profile_chunks=chunk_dicts,
        character_year_context=session.character_year_context,
        user_message=user_message_text,
        conversation_history=conversation_history,
        context_chunks=context_chunks,
        model=model,
    )

    generation_time_ms = int((time.time() - start_time) * 1000)

    # Count retrieved chunks
    retrieved_count = len(active_chunks)

    # Store character response
    char_msg = ChatMessageDB(
        id=str(uuid4()),
        session_id=session_id,
        role="character",
        content=response_text,
        model_provider=getattr(model, "name", None) or "google" if model else "google",
        model_name=str(model) if model else "gemini-2.5-flash",
        generation_time_ms=generation_time_ms,
        retrieved_chunks=retrieved_count,
    )
    db.add(char_msg)

    # Update session stats
    session.message_count = (session.message_count or 0) + 2
    session.last_message_at = datetime.now(timezone.utc)
    await db.flush()

    logger.info(
        f"Chat response generated for session {session_id}: "
        f"{len(response_text)} chars in {generation_time_ms}ms"
    )

    return {
        "user_message": user_msg,
        "character_response": char_msg,
    }


async def get_message_history(
    session_id: str,
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Get paginated message history for a session.

    Args:
        session_id: Session UUID.
        db: Database session.
        limit: Max messages to return.
        offset: Number of messages to skip.

    Returns:
        Dict with messages, total, limit, offset.

    Raises:
        NotFoundError: If session not found.
    """
    # Verify session exists
    await get_chat_session(session_id, db)

    # Get total count
    count_result = await db.execute(
        select(func.count(ChatMessageDB.id))
        .where(ChatMessageDB.session_id == session_id)
    )
    total = count_result.scalar()

    # Get messages with pagination
    result = await db.execute(
        select(ChatMessageDB)
        .where(ChatMessageDB.session_id == session_id)
        .order_by(ChatMessageDB.created_at)
        .offset(offset)
        .limit(limit)
    )
    messages = list(result.scalars().all())

    return {
        "messages": messages,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def regenerate_last_response(
    session_id: str,
    db: AsyncSession,
) -> ChatMessageDB:
    """
    Regenerate the last character response in a session.

    Deletes the last character message and generates a new one based
    on the last user message.

    Args:
        session_id: Session UUID.
        db: Database session.

    Returns:
        New ChatMessageDB for the character response.

    Raises:
        NotFoundError: If session not found.
        ValidationError: If session is closed or no messages to regenerate.
    """
    session = await get_chat_session(session_id, db)
    if not session.is_active:
        raise ValidationError("Cannot regenerate in a closed session")

    # Get the last two messages (should be user + character)
    result = await db.execute(
        select(ChatMessageDB)
        .where(ChatMessageDB.session_id == session_id)
        .order_by(ChatMessageDB.created_at.desc())
        .limit(2)
    )
    recent_messages = list(result.scalars().all())

    if not recent_messages:
        raise ValidationError("No messages to regenerate")

    # Find the last character message and the preceding user message
    last_char_msg = None
    last_user_msg = None
    for msg in recent_messages:
        if msg.role == "character" and last_char_msg is None:
            last_char_msg = msg
        elif msg.role == "user" and last_user_msg is None:
            last_user_msg = msg

    if not last_char_msg or not last_user_msg:
        raise ValidationError("No character response to regenerate")

    # Delete the old character response
    await db.delete(last_char_msg)
    session.message_count = max(0, (session.message_count or 0) - 1)
    await db.flush()

    # Re-send the user message to get a new response
    send_result = await send_message(session_id, last_user_msg.content, db)

    # The send_message created a new user message - we need to delete it
    # since we already have the original. Also adjust the count.
    new_user_msg = send_result["user_message"]
    await db.delete(new_user_msg)
    session.message_count = max(0, (session.message_count or 0) - 1)
    await db.flush()

    return send_result["character_response"]


# ============================================================================
# Helper Functions
# ============================================================================


async def _build_conversation_history(
    session_id: str,
    db: AsyncSession,
    limit: int = 10,
) -> Optional[str]:
    """
    Build formatted conversation history from recent messages.

    Args:
        session_id: Session UUID.
        db: Database session.
        limit: Max messages to include.

    Returns:
        Formatted conversation string or None if no history.
    """
    result = await db.execute(
        select(ChatMessageDB)
        .where(ChatMessageDB.session_id == session_id)
        .order_by(ChatMessageDB.created_at.desc())
        .limit(limit)
    )
    messages = list(reversed(result.scalars().all()))

    if not messages:
        return None

    parts = []
    for msg in messages:
        role_label = "User" if msg.role == "user" else "You"
        parts.append(f"**{role_label}:** {msg.content}")

    return "\n\n".join(parts)


def _format_character_chunks_for_context(
    chunks: List[CharacterChunkDB],
    character_year_context: int,
) -> str:
    """
    Format character profile chunks for RAG context, filtered by year.

    Args:
        chunks: List of CharacterChunkDB records.
        character_year_context: Year context for filtering.

    Returns:
        Formatted context string.
    """
    relevant_chunks = []
    for chunk in chunks:
        # Include chunks that are within the year context or have no year range
        if chunk.year_start and chunk.year_start > character_year_context:
            continue
        relevant_chunks.append(chunk)

    if not relevant_chunks:
        return ""

    parts = ["## Character Profile Context"]
    for chunk in relevant_chunks:
        chunk_type = chunk.chunk_type.replace("_", " ").title()
        year_range = ""
        if chunk.year_start and chunk.year_end:
            year_range = f" ({chunk.year_start}-{chunk.year_end})"
        parts.append(f"\n### {chunk_type}{year_range}\n{chunk.content}")

    return "\n".join(parts)


async def _retrieve_rag_context(
    character: CharacterDB,
    character_year_context: int,
    user_message: str,
) -> Optional[str]:
    """
    Retrieve additional timeline context from the vector store.

    Args:
        character: Character record.
        character_year_context: Year context.
        user_message: User's message for query.

    Returns:
        Formatted context string or None.
    """
    try:
        from app.services.vector_store_service import get_vector_store_service
        vs = get_vector_store_service()
        if not vs.enabled:
            return None

        # Query character-specific chunks from vector store
        if "historical_figures" in vs.collections:
            query_embedding = vs._embed_texts(
                [user_message],
                task_type=vs.embedding_query_task_type,
            )[0]

            results = vs.collections["historical_figures"].query(
                query_embeddings=[query_embedding],
                n_results=3,
                where={
                    "character_id": character.id,
                },
                include=["documents", "metadatas"],
            )

            if results["documents"] and results["documents"][0]:
                parts = ["## Additional Timeline Context"]
                for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
                    chunk_type = metadata.get("chunk_type", "unknown").replace("_", " ").title()
                    parts.append(f"\n### {chunk_type}\n{doc}")
                return "\n".join(parts)

        return None

    except Exception as e:
        logger.debug(f"RAG retrieval failed for chat: {e}")
        return None
