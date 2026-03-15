"""
Tests for media service operations.

Tests media (images, audio, video) operations with the redesigned schema:
- Media creation
- Media retrieval by generation
- Media retrieval by timeline
- Media updates
- Media deletion
"""

import pytest
from uuid import uuid4, UUID

from app.services import media_service
from app.db_models import MediaDB


# ============================================================================
# Media Creation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_media_for_generation(db_session, timeline_with_generation):
    """Test creating media for a generation."""
    generation = timeline_with_generation.generations[0]

    media = await media_service.create_media(
        db=db_session,
        generation_id=generation.id,
        media_type="image",
        media_order=1,
        prompt_text="Portrait of Franz Ferdinand in 1920",
        media_url="https://example.com/image1.jpg",
        event_year=6,
        title="Franz Ferdinand in 1920",
        description="The Archduke in his later years",
        model_provider="google",
        model_name="gemini-pro",
    )

    assert media["id"] is not None
    assert str(media["generation_id"]) == generation.id
    assert media["media_type"] == "image"
    assert media["media_url"] == "https://example.com/image1.jpg"
    assert media["event_year"] == 6
    assert media["is_user_added"] == False


@pytest.mark.asyncio
async def test_create_user_added_media(db_session, timeline_with_generation):
    """Test creating user-added media."""
    generation = timeline_with_generation.generations[0]

    media = await media_service.create_media(
        db=db_session,
        generation_id=generation.id,
        media_type="image",
        media_order=1,
        media_url="https://user-upload.com/image.jpg",
        title="User uploaded image",
        is_user_added=True,
    )

    assert media["is_user_added"] == True
    assert media["prompt_text"] is None  # User-added might not have prompt


# ============================================================================
# Media Retrieval Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_media_by_generation(db_session, media_db, timeline_with_generation):
    """Test retrieving all media for a generation."""
    generation = timeline_with_generation.generations[0]

    # Create additional media
    await media_service.create_media(
        db=db_session,
        generation_id=generation.id,
        media_type="image",
        media_order=2,
        media_url="https://example.com/image2.jpg",
        title="Second image",
    )

    media_list = await media_service.get_media_by_generation(
        db=db_session, generation_id=generation.id
    )

    assert len(media_list) >= 2  # At least the 2 we created
    # Should be ordered by media_order
    assert media_list[0]["media_order"] <= media_list[1]["media_order"]


@pytest.mark.asyncio
async def test_get_media_by_timeline(db_session, timeline_with_generation):
    """Test retrieving all media for a timeline (across all generations)."""
    generation = timeline_with_generation.generations[0]

    # Create media for first generation
    await media_service.create_media(
        db=db_session,
        generation_id=generation.id,
        media_type="image",
        media_order=1,
        media_url="https://example.com/image1.jpg",
        title="Generation 1 Image",
    )

    # Add extension generation
    from app.services.timeline_service import extend_timeline_with_new_generation
    from app.models import TimelineOutput, NarrativeMode

    extension_output = TimelineOutput(
        executive_summary="Extension",
        political_changes="Politics",
        conflicts_and_wars="Conflicts",
        economic_impacts="Economy",
        social_developments="Society",
        technological_shifts="Tech",
        key_figures="Figures",
        long_term_implications="Implications",
    )

    new_generation = await extend_timeline_with_new_generation(
        db=db_session,
        timeline_id=timeline_with_generation.id,
        extension_output=extension_output,
        additional_years=10,
        narrative_mode=NarrativeMode.NONE,
        historian_provider="google",
        historian_model_name="gemini-pro",
    )

    # Create media for second generation
    await media_service.create_media(
        db=db_session,
        generation_id=new_generation.id,
        media_type="image",
        media_order=1,
        media_url="https://example.com/image2.jpg",
        title="Generation 2 Image",
    )

    # Get all media for timeline
    media_list = await media_service.get_media_by_timeline(
        db=db_session, timeline_id=timeline_with_generation.id
    )

    # Should have media from both generations
    assert len(media_list) >= 2


@pytest.mark.asyncio
async def test_get_media_by_id(db_session, media_db):
    """Test retrieving a specific media item by ID."""
    media = await media_service.get_media(db=db_session, media_id=UUID(media_db.id))

    assert media is not None
    assert str(media["id"]) == media_db.id


@pytest.mark.asyncio
async def test_get_media_not_found(db_session):
    """Test retrieving non-existent media."""
    fake_id = uuid4()
    media = await media_service.get_media(db=db_session, media_id=fake_id)

    assert media is None


# ============================================================================
# Media Update Tests
# ============================================================================


@pytest.mark.asyncio
async def test_update_media_prompt(db_session, media_db):
    """Test updating media prompt text via direct DB update."""
    from sqlalchemy import update

    await db_session.execute(
        update(MediaDB).where(MediaDB.id == media_db.id).values(
            prompt_text="Updated prompt text", is_user_modified=1
        )
    )
    await db_session.flush()

    media = await media_service.get_media(db=db_session, media_id=UUID(media_db.id))
    assert media["prompt_text"] == "Updated prompt text"
    assert media["is_user_modified"] == True


@pytest.mark.asyncio
async def test_update_media_title_and_description(db_session, media_db):
    """Test updating media title and description via direct DB update."""
    from sqlalchemy import update

    await db_session.execute(
        update(MediaDB).where(MediaDB.id == media_db.id).values(
            title="New Title", description="New Description", is_user_modified=1
        )
    )
    await db_session.flush()

    media = await media_service.get_media(db=db_session, media_id=UUID(media_db.id))
    assert media["title"] == "New Title"
    assert media["description"] == "New Description"
    assert media["is_user_modified"] == True


@pytest.mark.asyncio
async def test_update_media_order(db_session, timeline_with_generation):
    """Test reordering media via direct DB update."""
    from sqlalchemy import update

    generation = timeline_with_generation.generations[0]
    generation_id = generation.id  # Capture before expire_all()

    media1 = await media_service.create_media(
        db=db_session,
        generation_id=generation_id,
        media_type="image",
        media_order=1,
        media_url="https://example.com/image1.jpg",
        title="First",
    )

    media2 = await media_service.create_media(
        db=db_session,
        generation_id=generation_id,
        media_type="image",
        media_order=2,
        media_url="https://example.com/image2.jpg",
        title="Second",
    )

    await db_session.execute(
        update(MediaDB).where(MediaDB.id == str(media1["id"])).values(media_order=2)
    )
    await db_session.execute(
        update(MediaDB).where(MediaDB.id == str(media2["id"])).values(media_order=1)
    )
    await db_session.flush()
    db_session.expire_all()

    media_list = await media_service.get_media_by_generation(
        db=db_session, generation_id=generation_id
    )
    media1_updated = next((m for m in media_list if str(m["id"]) == str(media1["id"])), None)
    media2_updated = next((m for m in media_list if str(m["id"]) == str(media2["id"])), None)
    assert media1_updated["media_order"] == 2
    assert media2_updated["media_order"] == 1


# ============================================================================
# Media Deletion Tests
# ============================================================================


@pytest.mark.asyncio
async def test_delete_media(db_session, media_db):
    """Test deleting media."""
    media_id = media_db.id

    success = await media_service.delete_media(db=db_session, media_id=UUID(media_id))

    assert success is True

    # Verify deleted
    media = await media_service.get_media(db=db_session, media_id=UUID(media_id))
    assert media is None


@pytest.mark.asyncio
async def test_delete_nonexistent_media(db_session):
    """Test deleting non-existent media."""
    fake_id = uuid4()
    success = await media_service.delete_media(db=db_session, media_id=fake_id)

    assert success is False


# ============================================================================
# Media Type Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_audio_media(db_session, timeline_with_generation):
    """Test creating audio media (future feature)."""
    generation = timeline_with_generation.generations[0]

    media = await media_service.create_media(
        db=db_session,
        generation_id=generation.id,
        media_type="audio",
        media_order=1,
        media_url="https://example.com/audio1.mp3",
        title="Audio narration",
        description="Audio description of the period",
    )

    assert media["media_type"] == "audio"


@pytest.mark.asyncio
async def test_filter_media_by_type(db_session, timeline_with_generation):
    """Test filtering media by type."""
    generation = timeline_with_generation.generations[0]

    # Create mixed media types
    await media_service.create_media(
        db=db_session,
        generation_id=generation.id,
        media_type="image",
        media_order=1,
        media_url="https://example.com/image1.jpg",
        title="Image 1",
    )

    await media_service.create_media(
        db=db_session,
        generation_id=generation.id,
        media_type="audio",
        media_order=2,
        media_url="https://example.com/audio1.mp3",
        title="Audio 1",
    )

    await media_service.create_media(
        db=db_session,
        generation_id=generation.id,
        media_type="image",
        media_order=3,
        media_url="https://example.com/image2.jpg",
        title="Image 2",
    )

    # Get all media
    all_media = await media_service.get_media_by_generation(
        db=db_session, generation_id=generation.id
    )

    # Filter by type
    images = [m for m in all_media if m["media_type"] == "image"]
    audio = [m for m in all_media if m["media_type"] == "audio"]

    assert len(images) == 2
    assert len(audio) == 1


# ============================================================================
# Media Model Tracking Tests
# ============================================================================


@pytest.mark.asyncio
async def test_media_tracks_generation_model(db_session, timeline_with_generation):
    """Test that media tracks which model generated the prompt."""
    generation = timeline_with_generation.generations[0]

    media = await media_service.create_media(
        db=db_session,
        generation_id=generation.id,
        media_type="image",
        media_order=1,
        prompt_text="Generated prompt",
        media_url="https://example.com/image.jpg",
        model_provider="openrouter",
        model_name="anthropic/claude-3-opus",
    )

    assert media["model_provider"] == "openrouter"
    assert media["model_name"] == "anthropic/claude-3-opus"


# ============================================================================
# Cascade Deletion Tests
# ============================================================================


@pytest.mark.asyncio
async def test_media_deleted_when_generation_deleted(db_session, timeline_with_generation):
    """Test that media is deleted when its generation is deleted (cascade)."""
    from app.services.timeline_service import delete_timeline

    generation = timeline_with_generation.generations[0]

    # Create media
    media = await media_service.create_media(
        db=db_session,
        generation_id=generation.id,
        media_type="image",
        media_order=1,
        media_url="https://example.com/image.jpg",
        title="Test image",
    )

    media_id = media["id"]

    # Delete the timeline (which deletes generations, which should cascade to media)
    await delete_timeline(db=db_session, timeline_id=timeline_with_generation.id)

    # Media should be gone
    media = await media_service.get_media(db=db_session, media_id=media_id)
    assert media is None
