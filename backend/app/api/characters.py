"""
Characters & Chat Router - Historical figure chat endpoints.

This module handles:
- Character detection and creation
- Character profile generation
- Chat session management
- Message sending and history
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import (
    CharacterResponse,
    CharacterDetailResponse,
    CharacterChunkResponse,
    CharacterProfileResponse,
    CharacterProfileSummary,
    DetectCharactersResponse,
    GenerateProfileRequest,
    GenerateProfileResponse,
    CustomCharacterCreateRequest,
    ChatSessionCreateRequest,
    ChatSessionResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    SendMessageResponse,
    MessageHistoryResponse,
)
from app.services import character_service, chat_service, chat_export_service
from app.exceptions import NotFoundError, AIGenerationError, ValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["characters", "chat"])


# ============================================================================
# Character Management Endpoints
# ============================================================================


@router.get(
    "/timelines/{timeline_id}/characters",
    response_model=List[CharacterResponse],
    summary="List characters for a timeline",
)
async def list_characters(
    timeline_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all characters for a given timeline."""
    try:
        characters = await character_service.list_characters_for_timeline(timeline_id, db)
        results = []
        for c in characters:
            resp = CharacterResponse.model_validate(c)
            # Build profile summaries from eagerly loaded profiles
            if hasattr(c, "profiles") and c.profiles:
                resp.profiles = [
                    CharacterProfileSummary(
                        id=p.id,
                        cutoff_year=p.cutoff_year,
                        profile_status=p.profile_status,
                        short_bio=p.short_bio,
                        chunk_count=len(p.chunks) if hasattr(p, "chunks") and p.chunks else 0,
                        created_at=p.created_at,
                    )
                    for p in c.profiles
                ]
            results.append(resp)
        return results
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.post(
    "/timelines/{timeline_id}/characters/detect",
    response_model=DetectCharactersResponse,
    summary="Detect historical figures in timeline",
)
async def detect_characters(
    timeline_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Detect historical figures from timeline content and create character records."""
    try:
        result = await character_service.detect_figures_in_timeline(timeline_id, db)
        return DetectCharactersResponse(
            timeline_id=timeline_id,
            detected_figures=result["detected_figures"],
            created_characters=result["created_characters"],
            characters=[CharacterResponse.model_validate(c) for c in result["characters"]],
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.post(
    "/timelines/{timeline_id}/characters/custom",
    response_model=CharacterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom character",
)
async def create_custom_character(
    timeline_id: str,
    request: CustomCharacterCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a user-defined custom character for a timeline."""
    try:
        character = await character_service.create_custom_character(
            timeline_id=timeline_id,
            name=request.name,
            full_name=request.full_name,
            title=request.title,
            user_provided_bio=request.user_provided_bio,
            birth_year=request.birth_year,
            death_year=request.death_year,
            db=db,
        )
        return CharacterResponse.model_validate(character)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/characters/{character_id}/generate-profile",
    response_model=GenerateProfileResponse,
    summary="Generate character profile",
)
async def generate_profile(
    character_id: str,
    request: Optional[GenerateProfileRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """Generate an AI profile for a character using the Character Profiler Agent."""
    try:
        cutoff_year = request.cutoff_year if request else None
        result = await character_service.generate_character_profile(
            character_id, db, cutoff_year=cutoff_year
        )
        profile = result["profile"]
        profile_resp = CharacterProfileResponse(
            id=profile.id,
            character_id=profile.character_id,
            cutoff_year=profile.cutoff_year,
            profile_status=profile.profile_status,
            profile_generated_at=profile.profile_generated_at,
            profile_model_provider=profile.profile_model_provider,
            profile_model_name=profile.profile_model_name,
            short_bio=profile.short_bio,
            role_summary=profile.role_summary,
            importance_score=profile.importance_score,
            chunk_count=result["chunk_count"],
            created_at=profile.created_at,
            updated_at=profile.updated_at,
        )
        character = result["character"]
        char_resp = CharacterResponse.model_validate(character)
        # Build profile summaries from eagerly loaded profiles
        if hasattr(character, "profiles") and character.profiles:
            char_resp.profiles = [
                CharacterProfileSummary(
                    id=p.id,
                    cutoff_year=p.cutoff_year,
                    profile_status=p.profile_status,
                    short_bio=p.short_bio,
                    chunk_count=len(p.chunks) if hasattr(p, "chunks") and p.chunks else 0,
                    created_at=p.created_at,
                )
                for p in character.profiles
            ]
        return GenerateProfileResponse(
            message="Profile generated successfully",
            character_id=character_id,
            status=result["status"],
            chunk_count=result["chunk_count"],
            profile=profile_resp,
            character=char_resp,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except AIGenerationError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get(
    "/characters/{character_id}",
    response_model=CharacterDetailResponse,
    summary="Get character detail",
)
async def get_character(
    character_id: str,
    include_chunks: bool = Query(False, description="Include profile chunks"),
    db: AsyncSession = Depends(get_db),
):
    """Get full character detail, optionally with profile chunks."""
    try:
        character = await character_service.get_character_by_id(
            character_id, db, include_chunks=include_chunks
        )
        response = CharacterDetailResponse.model_validate(character)
        if include_chunks and hasattr(character, "character_chunks"):
            response.chunks = [
                CharacterChunkResponse.model_validate(c) for c in character.character_chunks
            ]
        return response
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.get(
    "/characters/{character_id}/profiles",
    response_model=List[CharacterProfileResponse],
    summary="List profiles for a character",
)
async def list_profiles(
    character_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all date-scoped profiles for a character."""
    try:
        profiles = await character_service.list_profiles(character_id, db)
        result = []
        for p in profiles:
            chunk_count = len(p.chunks) if hasattr(p, "chunks") and p.chunks else 0
            result.append(CharacterProfileResponse(
                id=p.id,
                character_id=p.character_id,
                cutoff_year=p.cutoff_year,
                profile_status=p.profile_status,
                profile_generated_at=p.profile_generated_at,
                profile_model_provider=p.profile_model_provider,
                profile_model_name=p.profile_model_name,
                short_bio=p.short_bio,
                role_summary=p.role_summary,
                importance_score=p.importance_score,
                chunk_count=chunk_count,
                created_at=p.created_at,
                updated_at=p.updated_at,
            ))
        return result
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.get(
    "/characters/{character_id}/profiles/{profile_id}",
    response_model=CharacterProfileResponse,
    summary="Get profile detail",
)
async def get_profile(
    character_id: str,
    profile_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific profile with its chunks."""
    try:
        profile = await character_service.get_profile(
            character_id, profile_id, db, include_chunks=True
        )
        chunks = None
        chunk_count = 0
        if hasattr(profile, "chunks") and profile.chunks:
            chunk_count = len(profile.chunks)
            chunks = [CharacterChunkResponse.model_validate(c) for c in profile.chunks]
        return CharacterProfileResponse(
            id=profile.id,
            character_id=profile.character_id,
            cutoff_year=profile.cutoff_year,
            profile_status=profile.profile_status,
            profile_generated_at=profile.profile_generated_at,
            profile_model_provider=profile.profile_model_provider,
            profile_model_name=profile.profile_model_name,
            short_bio=profile.short_bio,
            role_summary=profile.role_summary,
            importance_score=profile.importance_score,
            chunk_count=chunk_count,
            created_at=profile.created_at,
            updated_at=profile.updated_at,
            chunks=chunks,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.delete(
    "/characters/{character_id}/profiles/{profile_id}",
    summary="Delete a character profile",
)
async def delete_profile(
    character_id: str,
    profile_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a character profile and its associated chunks."""
    try:
        await character_service.delete_profile(character_id, profile_id, db)
        return {"message": "Profile deleted successfully", "profile_id": profile_id}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.delete(
    "/timelines/{timeline_id}/characters/unprofiled",
    summary="Delete all unprofiled auto-detected characters",
)
async def delete_unprofiled_characters(
    timeline_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete all auto-detected characters without a ready profile for a timeline."""
    deleted = await character_service.delete_unprofiled_characters(timeline_id, db)
    return {"message": f"Deleted {deleted} unprofiled characters", "deleted": deleted}


@router.delete(
    "/characters/{character_id}",
    summary="Delete a character",
)
async def delete_character(
    character_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a character and all associated chat sessions."""
    try:
        await character_service.delete_character(character_id, db)
        return {"message": "Character deleted successfully", "character_id": character_id}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


# ============================================================================
# Chat Endpoints
# ============================================================================


@router.post(
    "/characters/{character_id}/chat/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a chat session",
)
async def create_chat_session(
    character_id: str,
    request: ChatSessionCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat session with a character at a specific year context."""
    try:
        session = await chat_service.create_chat_session(
            character_id=character_id,
            character_year_context=request.character_year_context,
            session_name=request.session_name,
            db=db,
            profile_id=request.profile_id,
        )
        return ChatSessionResponse.model_validate(session)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.get(
    "/chat/sessions/{session_id}",
    response_model=ChatSessionResponse,
    summary="Get chat session detail",
)
async def get_chat_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a chat session by ID."""
    try:
        session = await chat_service.get_chat_session(session_id, db)
        return ChatSessionResponse.model_validate(session)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.get(
    "/chat/sessions/{session_id}/export",
    summary="Export chat session as markdown",
)
async def export_chat_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Export a chat session as a downloadable markdown file."""
    try:
        markdown = await chat_export_service.export_chat_session(session_id, db)
        return Response(content=markdown, media_type="text/markdown")
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.post(
    "/chat/sessions/{session_id}/messages",
    response_model=SendMessageResponse,
    summary="Send a message",
)
async def send_message(
    session_id: str,
    request: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send a user message and get an in-character response."""
    try:
        result = await chat_service.send_message(
            session_id=session_id,
            user_message_text=request.message,
            db=db,
        )
        return SendMessageResponse(
            user_message=ChatMessageResponse.model_validate(result["user_message"]),
            character_response=ChatMessageResponse.model_validate(result["character_response"]),
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except AIGenerationError as e:
        raise HTTPException(status_code=500, detail=e.message)


@router.get(
    "/chat/sessions/{session_id}/messages",
    response_model=MessageHistoryResponse,
    summary="Get message history",
)
async def get_messages(
    session_id: str,
    limit: int = Query(50, ge=1, le=200, description="Max messages to return"),
    offset: int = Query(0, ge=0, description="Messages to skip"),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated message history for a chat session."""
    try:
        result = await chat_service.get_message_history(session_id, db, limit, offset)
        return MessageHistoryResponse(
            messages=[ChatMessageResponse.model_validate(m) for m in result["messages"]],
            total=result["total"],
            limit=result["limit"],
            offset=result["offset"],
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.get(
    "/timelines/{timeline_id}/chat/sessions",
    response_model=List[ChatSessionResponse],
    summary="List chat sessions for a timeline",
)
async def list_sessions(
    timeline_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all chat sessions for a timeline."""
    try:
        sessions = await chat_service.list_sessions_for_timeline(timeline_id, db)
        return [ChatSessionResponse.model_validate(s) for s in sessions]
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.post(
    "/chat/sessions/{session_id}/close",
    response_model=ChatSessionResponse,
    summary="Close a chat session",
)
async def close_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Close an active chat session."""
    try:
        session = await chat_service.close_chat_session(session_id, db)
        return ChatSessionResponse.model_validate(session)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.delete(
    "/chat/sessions/{session_id}",
    summary="Delete a chat session",
)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a chat session and all its messages."""
    try:
        await chat_service.delete_chat_session(session_id, db)
        return {"message": "Chat session deleted successfully", "session_id": session_id}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.post(
    "/chat/sessions/{session_id}/regenerate",
    response_model=ChatMessageResponse,
    summary="Regenerate last response",
)
async def regenerate_response(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Regenerate the last character response in a chat session."""
    try:
        message = await chat_service.regenerate_last_response(session_id, db)
        return ChatMessageResponse.model_validate(message)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except AIGenerationError as e:
        raise HTTPException(status_code=500, detail=e.message)
