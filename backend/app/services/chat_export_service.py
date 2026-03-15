"""
Chat Export Service for Historical Figure Conversations.

Generates markdown exports from chat sessions for download.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db_models import ChatSessionDB, ChatMessageDB, CharacterDB, TimelineDB
from app.exceptions import NotFoundError

logger = logging.getLogger(__name__)


async def export_chat_session(session_id: str, db: AsyncSession) -> str:
    """
    Export a chat session as formatted markdown.

    Loads the session with its character, timeline, and messages,
    then formats everything into a downloadable markdown string.

    Args:
        session_id: Session UUID.
        db: Database session.

    Returns:
        Markdown-formatted string of the full conversation.

    Raises:
        NotFoundError: If session, character, or timeline not found.
    """
    # Load session
    result = await db.execute(
        select(ChatSessionDB).where(ChatSessionDB.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError(f"Chat session {session_id} not found")

    # Load character
    result = await db.execute(
        select(CharacterDB).where(CharacterDB.id == session.character_id)
    )
    character = result.scalar_one_or_none()
    if not character:
        raise NotFoundError(f"Character {session.character_id} not found")

    # Load timeline
    result = await db.execute(
        select(TimelineDB).where(TimelineDB.id == session.timeline_id)
    )
    timeline = result.scalar_one_or_none()
    if not timeline:
        raise NotFoundError(f"Timeline {session.timeline_id} not found")

    # Load messages ordered by creation time
    result = await db.execute(
        select(ChatMessageDB)
        .where(ChatMessageDB.session_id == session_id)
        .order_by(ChatMessageDB.created_at)
    )
    messages = list(result.scalars().all())

    # Build markdown
    timeline_name = timeline.timeline_name or timeline.root_deviation_description[:80]
    session_name = session.session_name or "Unnamed session"
    year = session.character_year_context
    export_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [
        f"# Chat with {character.name} ({year})",
        "",
        f"**Timeline:** {timeline_name}",
        f"**Character:** {character.name}",
        f"**Speaking from year:** {year}",
        f"**Session:** {session_name}",
        f"**Messages:** {len(messages)}",
        f"**Date:** {export_date}",
        "",
        "---",
    ]

    for msg in messages:
        lines.append("")
        if msg.role == "user":
            lines.append(f"**You:** {msg.content}")
        else:
            lines.append(f"**{character.name} ({year}):** {msg.content}")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Exported from Deviation Engine*")
    lines.append("")

    return "\n".join(lines)
