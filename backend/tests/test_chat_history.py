"""
Tests for the native message history upgrade in chat_service.py.

Covers _build_message_history: role mapping, token budget, alternation repair,
and current-message exclusion.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.db_models import ChatMessageDB
from app.services.chat_service import _build_message_history
from pydantic_ai.messages import ModelRequest, ModelResponse


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def session_id() -> str:
    return str(uuid4())


async def _insert_messages(
    db: AsyncSession,
    session_id: str,
    roles: list[str],
    content_prefix: str = "msg",
) -> list[ChatMessageDB]:
    """Helper: insert ChatMessageDB records with distinct timestamps and return them."""
    base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    msgs = []
    for i, role in enumerate(roles):
        msg = ChatMessageDB(
            id=str(uuid4()),
            session_id=session_id,
            role=role,
            content=f"{content_prefix}_{i}",
            created_at=base_time + timedelta(seconds=i),
        )
        db.add(msg)
        msgs.append(msg)
    await db.flush()
    return msgs


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_returns_empty_list_when_no_history(db_session: AsyncSession, session_id: str):
    """No prior messages → empty list, not None."""
    fake_current_id = str(uuid4())
    result = await _build_message_history(session_id, db_session, exclude_id=fake_current_id)
    assert result == []


@pytest.mark.asyncio
async def test_returns_empty_list_when_only_current_message_exists(
    db_session: AsyncSession, session_id: str
):
    """Only the current user message is in DB → exclude it → empty list."""
    msgs = await _insert_messages(db_session, session_id, ["user"])
    current_id = msgs[0].id

    result = await _build_message_history(session_id, db_session, exclude_id=current_id)
    assert result == []


@pytest.mark.asyncio
async def test_maps_user_role_to_model_request(db_session: AsyncSession, session_id: str):
    """DB role 'user' maps to ModelRequest."""
    msgs = await _insert_messages(db_session, session_id, ["user", "character", "user"])
    current_id = msgs[2].id  # exclude the latest user message

    result = await _build_message_history(session_id, db_session, exclude_id=current_id)

    assert len(result) == 2
    assert isinstance(result[0], ModelRequest)
    assert isinstance(result[1], ModelResponse)


@pytest.mark.asyncio
async def test_maps_character_role_to_model_response(db_session: AsyncSession, session_id: str):
    """DB role 'character' maps to ModelResponse."""
    msgs = await _insert_messages(db_session, session_id, ["user", "character", "user"])
    current_id = msgs[2].id

    result = await _build_message_history(session_id, db_session, exclude_id=current_id)

    assert isinstance(result[1], ModelResponse)
    assert result[1].parts[0].content == "msg_1"


@pytest.mark.asyncio
async def test_preserves_message_content(db_session: AsyncSession, session_id: str):
    """Content from DB is preserved in the typed messages."""
    msgs = await _insert_messages(
        db_session, session_id, ["user", "character", "user"], content_prefix="hello"
    )
    current_id = msgs[2].id

    result = await _build_message_history(session_id, db_session, exclude_id=current_id)

    assert result[0].parts[0].content == "hello_0"
    assert result[1].parts[0].content == "hello_1"


@pytest.mark.asyncio
async def test_excludes_current_user_message_by_id(db_session: AsyncSession, session_id: str):
    """The message whose id matches exclude_id is not included."""
    msgs = await _insert_messages(db_session, session_id, ["user", "character", "user"])
    current_id = msgs[2].id

    result = await _build_message_history(session_id, db_session, exclude_id=current_id)

    ids_in_result = [m.parts[0].content for m in result]
    assert "msg_2" not in ids_in_result
    assert len(result) == 2



@pytest.mark.asyncio
async def test_token_budget_drops_oldest_when_over_budget(
    db_session: AsyncSession, session_id: str
):
    """Oldest messages are excluded when total char count exceeds TOKEN_BUDGET."""
    from app.services.chat_service import TOKEN_BUDGET

    # Create 5 messages where the first pair is very long (exceeds half the char budget)
    # Char budget = TOKEN_BUDGET * 4; long messages each take slightly more than half
    long = "x" * (TOKEN_BUDGET * 2 + 100)
    short = "y" * 10

    base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    msgs: list[ChatMessageDB] = []
    for i, (role, content) in enumerate([
        ("user", long),      # old, should be dropped
        ("character", long), # old, should be dropped
        ("user", short),
        ("character", short),
        ("user", short),     # current
    ]):
        msg = ChatMessageDB(
            id=str(uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            created_at=base_time + timedelta(seconds=i),
        )
        db_session.add(msg)
        msgs.append(msg)
    await db_session.flush()

    current_id = msgs[4].id
    result = await _build_message_history(session_id, db_session, exclude_id=current_id)

    # Only the 2 short messages should fit
    assert len(result) == 2
    assert result[0].parts[0].content == short
    assert result[1].parts[0].content == short


@pytest.mark.asyncio
async def test_repairs_consecutive_user_messages(db_session: AsyncSession, session_id: str):
    """Consecutive same-role messages are repaired by dropping the orphan."""
    # Simulate: user, user, character, user (current)
    # After excluding current: user, user, character
    # The first user has no following character → orphan, should be dropped
    msgs = await _insert_messages(
        db_session, session_id, ["user", "user", "character", "user"]
    )
    current_id = msgs[3].id

    result = await _build_message_history(session_id, db_session, exclude_id=current_id)

    # Should alternate cleanly: user, character
    assert len(result) == 2
    assert isinstance(result[0], ModelRequest)
    assert isinstance(result[1], ModelResponse)


@pytest.mark.asyncio
async def test_repairs_consecutive_character_messages(db_session: AsyncSession, session_id: str):
    """Consecutive character messages are repaired by dropping the orphan."""
    # user, character, character, user (current) → after exclude: user, char, char
    # Second char has no preceding user → orphan
    msgs = await _insert_messages(
        db_session, session_id, ["user", "character", "character", "user"]
    )
    current_id = msgs[3].id

    result = await _build_message_history(session_id, db_session, exclude_id=current_id)

    assert len(result) == 2
    assert isinstance(result[0], ModelRequest)
    assert isinstance(result[1], ModelResponse)


@pytest.mark.asyncio
async def test_messages_ordered_oldest_to_newest(db_session: AsyncSession, session_id: str):
    """The returned list is ordered oldest → newest (chronological)."""
    msgs = await _insert_messages(
        db_session, session_id, ["user", "character", "user", "character", "user"]
    )
    current_id = msgs[4].id

    result = await _build_message_history(session_id, db_session, exclude_id=current_id)

    # First should be user (oldest), last should be character
    assert isinstance(result[0], ModelRequest)
    assert isinstance(result[-1], ModelResponse)
    assert result[0].parts[0].content == "msg_0"
