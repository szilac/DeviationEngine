"""
Character Service for Historical Figure Chat.

Handles character detection, creation, profile generation, and CRUD operations.
"""

import logging
import random
import re
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db_models import (
    CharacterDB,
    CharacterChunkDB,
    CharacterProfileDB,
    TimelineDB,
    GenerationDB,
)
from app.models import CharacterProfileOutput, CharacterChunkOutput
from app.exceptions import NotFoundError, AIGenerationError

logger = logging.getLogger(__name__)


# ============================================================================
# Character Detection
# ============================================================================


_NON_PERSON_WORDS = {
    # Concepts / phenomena
    "bonds", "deserts", "containment", "protocol", "doctrine", "accord", "treaty",
    "pact", "alliance", "charter", "declaration", "manifesto", "agenda", "initiative",
    "programme", "program", "reform", "revolution", "movement", "uprising", "crisis",
    "collapse", "emergence", "transition", "expansion", "occupation", "invasion",
    "liberation", "restoration", "resistance", "suppression", "integration",
    # Institutions / bodies
    "act", "commission", "assembly", "institute", "bureau", "ministry", "department",
    "council", "court", "board", "union", "league", "federation", "corporation",
    "agency", "office", "committee", "congress", "parliament", "senate", "republic",
    "empire", "regime", "administration", "government", "coalition", "party",
    # Locations / geographic descriptors
    "states", "kingdom", "nations", "territories", "province", "region", "continent",
    "peninsula", "archipelago", "corridor", "basin", "highlands", "lowlands",
    # Alternate-history / sci-fi / fantasy genre words
    "aetheric", "arcane", "quantum", "temporal", "dimensional", "fracture",
    "anomaly", "nexus", "rift", "breach", "void", "flux", "convergence",
    "divergence", "paradox", "singularity", "cascade", "disruption",
    # Section headings / report structure words
    "summary", "analysis", "impacts", "developments", "changes", "shifts",
    "implications", "consequences", "effects", "overview", "introduction",
    "conclusion", "section", "chapter", "figures", "timeline",
}


def _is_plausible_person_name(name: str) -> bool:
    """
    Return True only if the name looks like an actual person's name.

    Filters out concepts, places, institutions, and alternate-history jargon
    that NER or regex might incorrectly tag as people.

    Args:
        name: Candidate name string.

    Returns:
        True if the name passes all heuristic checks.
    """
    # Strip possessives before checking (e.g. "Albert Camus's" → "Albert Camus")
    name = re.sub(r"[''\u2019]s?$", "", name).strip()

    # Must have at least 2 whitespace-separated tokens
    tokens = name.split()
    if len(tokens) < 2:
        return False

    # Reject if any token (lowercased) is in the non-person word list
    if any(tok.lower().rstrip("s") in _NON_PERSON_WORDS or tok.lower() in _NON_PERSON_WORDS
           for tok in tokens):
        return False

    # Reject names containing non-alphabetic characters beyond apostrophe/hyphen/period
    if re.search(r"[^A-Za-z '\-\.]", name):
        return False

    # Each real-name token should start with a capital letter and be mostly lowercase after
    for tok in tokens:
        tok_clean = tok.rstrip(".")
        if not tok_clean or not tok_clean[0].isupper():
            return False
        # Allow initials (single letter + optional period), but reject ALL-CAPS tokens > 1 char
        if len(tok_clean) > 1 and tok_clean.isupper():
            return False

    return True


def _clean_name(name: str) -> str:
    """Strip possessives and surrounding punctuation from a detected name."""
    name = re.sub(r"[''\u2019]s?$", "", name).strip()
    return name.strip(".,;:!?\"'")


def _extract_figures_from_text(text: str) -> List[str]:
    """
    Extract potential historical figure names from text using regex heuristics.

    Looks for capitalized multi-word names (2-4 words). This is a fallback
    when spaCy is not available.

    Args:
        text: Text to scan for names.

    Returns:
        List of potential figure names (deduplicated).
    """
    # Match capitalized multi-word names (e.g., "Winston Churchill", "Franklin D. Roosevelt")
    pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+){1,3})\b'
    matches = re.findall(pattern, text)

    figures = []
    seen = set()
    for name in matches:
        name = _clean_name(name.strip())
        if not _is_plausible_person_name(name):
            continue
        name_lower = name.lower()
        if name_lower not in seen:
            seen.add(name_lower)
            figures.append(name)

    return figures


def _extract_figures_with_spacy(text: str) -> List[str]:
    """
    Extract historical figure names using spaCy NER.

    Args:
        text: Text to scan.

    Returns:
        List of person entity names.
    """
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text[:100000])  # Limit to 100k chars for performance
        persons = set()
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                name = _clean_name(ent.text.strip())
                if _is_plausible_person_name(name):
                    persons.add(name)
        return list(persons)
    except (ImportError, OSError):
        logger.warning("spaCy not available, falling back to regex extraction")
        return _extract_figures_from_text(text)


async def detect_figures_in_timeline(
    timeline_id: str,
    db: AsyncSession,
) -> Dict[str, Any]:
    """
    Detect historical figures in timeline content and create Character records.

    Scans all generations of a timeline for historical figure names using
    spaCy NER (with regex fallback), then creates CharacterDB records.

    Args:
        timeline_id: UUID of the timeline to scan.
        db: Database session.

    Returns:
        Dict with detected_figures, created_characters count, and characters list.

    Raises:
        NotFoundError: If timeline not found.
    """
    # Verify timeline exists and load generations
    result = await db.execute(
        select(TimelineDB)
        .options(selectinload(TimelineDB.generations))
        .where(TimelineDB.id == timeline_id)
    )
    timeline = result.scalar_one_or_none()
    if not timeline:
        raise NotFoundError(f"Timeline {timeline_id} not found")

    if not timeline.generations:
        return {
            "detected_figures": [],
            "created_characters": 0,
            "characters": [],
        }

    # Combine all text content for scanning
    sections = [
        "key_figures", "executive_summary", "political_changes",
        "conflicts_and_wars", "economic_impacts", "social_developments",
    ]
    combined_text = ""
    for gen in timeline.generations:
        for section in sections:
            content = getattr(gen, section, None)
            if content:
                combined_text += f"\n{content}"

    # Extract figure names and shuffle to ensure variety across scans
    figures = _extract_figures_with_spacy(combined_text)
    random.shuffle(figures)

    # Check which figures already exist for this timeline
    existing_result = await db.execute(
        select(CharacterDB.name).where(CharacterDB.timeline_id == timeline_id)
    )
    existing_names = {row[0].lower() for row in existing_result.all()}

    # Determine the latest generation info — convert offset to actual year
    latest_gen = max(timeline.generations, key=lambda g: g.generation_order)
    deviation_year = timeline.root_deviation_date.year if hasattr(timeline.root_deviation_date, 'year') else int(str(timeline.root_deviation_date)[:4])
    last_known_year = (deviation_year + latest_gen.end_year) if latest_gen else deviation_year

    # Create character records for new figures — cap at 25 per scan
    MAX_NEW_CHARACTERS_PER_SCAN = 25
    created_characters = []
    new_figure_names = []
    for name in figures:
        if len(created_characters) >= MAX_NEW_CHARACTERS_PER_SCAN:
            break
        if name.lower() in existing_names:
            continue

        character = CharacterDB(
            id=str(uuid4()),
            timeline_id=timeline_id,
            name=name,
            character_source="auto_detected",
            first_appearance_generation=1,
            last_known_year=last_known_year,
            profile_status="pending",
        )
        db.add(character)
        created_characters.append(character)
        new_figure_names.append(name)
        existing_names.add(name.lower())

    if created_characters:
        await db.flush()

    logger.info(
        f"Detected {len(figures)} figures in timeline {timeline_id}, "
        f"created {len(created_characters)} new characters"
    )

    return {
        "detected_figures": new_figure_names,
        "created_characters": len(created_characters),
        "characters": created_characters,
    }


# ============================================================================
# Character CRUD
# ============================================================================


async def create_custom_character(
    timeline_id: str,
    name: str,
    full_name: Optional[str],
    title: Optional[str],
    user_provided_bio: str,
    birth_year: Optional[int],
    death_year: Optional[int],
    db: AsyncSession,
) -> CharacterDB:
    """
    Create a user-defined custom character.

    Args:
        timeline_id: Timeline UUID.
        name: Character name.
        full_name: Full formal name.
        title: Title or role.
        user_provided_bio: User-provided biographical details.
        birth_year: Birth year.
        death_year: Death year.
        db: Database session.

    Returns:
        Created CharacterDB record.

    Raises:
        NotFoundError: If timeline not found.
    """
    # Verify timeline exists
    result = await db.execute(
        select(TimelineDB)
        .options(selectinload(TimelineDB.generations))
        .where(TimelineDB.id == timeline_id)
    )
    timeline = result.scalar_one_or_none()
    if not timeline:
        raise NotFoundError(f"Timeline {timeline_id} not found")

    # Determine last known year from timeline — convert offset to actual year
    deviation_year = timeline.root_deviation_date.year if hasattr(timeline.root_deviation_date, 'year') else int(str(timeline.root_deviation_date)[:4])
    last_known_year = deviation_year
    if timeline.generations:
        latest_gen = max(timeline.generations, key=lambda g: g.generation_order)
        last_known_year = deviation_year + latest_gen.end_year

    character = CharacterDB(
        id=str(uuid4()),
        timeline_id=timeline_id,
        name=name,
        full_name=full_name,
        title=title,
        character_source="user_created",
        user_provided_bio=user_provided_bio,
        birth_year=birth_year,
        death_year=death_year,
        first_appearance_generation=1,
        last_known_year=last_known_year,
        profile_status="pending",
    )
    db.add(character)
    await db.flush()

    logger.info(f"Created custom character '{name}' for timeline {timeline_id}")
    return character


async def get_character_by_id(
    character_id: str,
    db: AsyncSession,
    include_chunks: bool = False,
) -> CharacterDB:
    """
    Get a character by ID, optionally with chunks.

    Args:
        character_id: Character UUID.
        db: Database session.
        include_chunks: Whether to eagerly load chunks.

    Returns:
        CharacterDB record.

    Raises:
        NotFoundError: If character not found.
    """
    query = select(CharacterDB).where(CharacterDB.id == character_id)
    if include_chunks:
        query = query.options(selectinload(CharacterDB.character_chunks))

    result = await db.execute(query)
    character = result.scalar_one_or_none()
    if not character:
        raise NotFoundError(f"Character {character_id} not found")
    return character


async def list_characters_for_timeline(
    timeline_id: str,
    db: AsyncSession,
) -> List[CharacterDB]:
    """
    List all characters for a timeline.

    Args:
        timeline_id: Timeline UUID.
        db: Database session.

    Returns:
        List of CharacterDB records.

    Raises:
        NotFoundError: If timeline not found.
    """
    # Verify timeline exists
    result = await db.execute(select(TimelineDB).where(TimelineDB.id == timeline_id))
    if not result.scalar_one_or_none():
        raise NotFoundError(f"Timeline {timeline_id} not found")

    result = await db.execute(
        select(CharacterDB)
        .options(
            selectinload(CharacterDB.profiles)
            .selectinload(CharacterProfileDB.chunks)
        )
        .where(CharacterDB.timeline_id == timeline_id)
        .order_by(CharacterDB.importance_score.desc().nulls_last(), CharacterDB.name)
    )
    return list(result.scalars().all())


async def delete_character(
    character_id: str,
    db: AsyncSession,
) -> None:
    """
    Delete a character and all associated data (chunks, sessions, messages).

    Cascade delete handles sessions and chunks via DB relationships.

    Args:
        character_id: Character UUID.
        db: Database session.

    Raises:
        NotFoundError: If character not found.
    """
    character = await get_character_by_id(character_id, db)

    # Delete vector store entries
    try:
        from app.services.vector_store_service import get_vector_store_service
        vs = get_vector_store_service()
        if vs.enabled and "historical_figures" in vs.collections:
            # Get all chunk vector IDs
            result = await db.execute(
                select(CharacterChunkDB.vector_chunk_id)
                .where(CharacterChunkDB.character_id == character_id)
                .where(CharacterChunkDB.vector_chunk_id.isnot(None))
            )
            vector_ids = [row[0] for row in result.all()]
            if vector_ids:
                vs.collections["historical_figures"].delete(ids=vector_ids)
                logger.info(f"Deleted {len(vector_ids)} vector chunks for character {character_id}")
    except Exception as e:
        logger.warning(f"Failed to delete vector chunks for character {character_id}: {e}")

    await db.delete(character)
    await db.flush()
    logger.info(f"Deleted character {character_id}")


async def delete_unprofiled_characters(
    timeline_id: str,
    db: AsyncSession,
) -> int:
    """
    Delete all auto-detected characters without a ready profile for a timeline.

    Targets only characters with character_source='auto_detected' whose
    profile_status is not 'ready', i.e. figures found by scan that the user
    never generated a profile for.

    Args:
        timeline_id: Timeline UUID.
        db: Database session.

    Returns:
        Number of characters deleted.
    """
    result = await db.execute(
        select(CharacterDB)
        .where(CharacterDB.timeline_id == timeline_id)
        .where(CharacterDB.character_source == "auto_detected")
        .where(CharacterDB.profile_status != "ready")
    )
    characters = result.scalars().all()

    for character in characters:
        try:
            from app.services.vector_store_service import get_vector_store_service
            vs = get_vector_store_service()
            if vs.enabled and "historical_figures" in vs.collections:
                chunk_result = await db.execute(
                    select(CharacterChunkDB.vector_chunk_id)
                    .where(CharacterChunkDB.character_id == character.id)
                    .where(CharacterChunkDB.vector_chunk_id.isnot(None))
                )
                vector_ids = [row[0] for row in chunk_result.all()]
                if vector_ids:
                    vs.collections["historical_figures"].delete(ids=vector_ids)
        except Exception as e:
            logger.warning(f"Failed to delete vector chunks for character {character.id}: {e}")

        await db.delete(character)

    await db.flush()
    logger.info(f"Deleted {len(characters)} unprofiled auto-detected characters from timeline {timeline_id}")
    return len(characters)


async def delete_profile(
    character_id: str,
    profile_id: str,
    db: AsyncSession,
) -> None:
    """
    Delete a character profile and its associated chunks.

    Args:
        character_id: Character UUID.
        profile_id: Profile UUID.
        db: Database session.

    Raises:
        NotFoundError: If character or profile not found.
    """
    profile = await get_profile(character_id, profile_id, db, include_chunks=True)

    # Delete vector store entries for this profile's chunks
    try:
        from app.services.vector_store_service import get_vector_store_service
        vs = get_vector_store_service()
        if vs.enabled and "historical_figures" in vs.collections:
            result = await db.execute(
                select(CharacterChunkDB.vector_chunk_id)
                .where(CharacterChunkDB.profile_id == profile_id)
                .where(CharacterChunkDB.vector_chunk_id.isnot(None))
            )
            vector_ids = [row[0] for row in result.all()]
            if vector_ids:
                vs.collections["historical_figures"].delete(ids=vector_ids)
                logger.info(f"Deleted {len(vector_ids)} vector chunks for profile {profile_id}")
    except Exception as e:
        logger.warning(f"Failed to delete vector chunks for profile {profile_id}: {e}")

    await db.delete(profile)
    await db.flush()

    # If no profiles remain, reset character status to pending
    result = await db.execute(
        select(func.count(CharacterProfileDB.id))
        .where(CharacterProfileDB.character_id == character_id)
    )
    remaining = result.scalar()
    if remaining == 0:
        character = await get_character_by_id(character_id, db)
        character.profile_status = "pending"
        await db.flush()

    logger.info(f"Deleted profile {profile_id} for character {character_id}")


# ============================================================================
# Profile Generation
# ============================================================================


def _find_nearest_profile(
    profiles: list,
    target_year: int,
    exclude_year: Optional[int] = None,
) -> Optional[Any]:
    """
    Return the profile whose cutoff_year is closest to target_year.

    Args:
        profiles: List of profile objects with a cutoff_year attribute.
        target_year: The year we are generating a new profile for.
        exclude_year: Skip profiles with this cutoff_year (the one being replaced).

    Returns:
        The nearest profile, or None if no eligible profiles exist.
    """
    candidates = [p for p in profiles if p.cutoff_year != exclude_year]
    if not candidates:
        return None
    return min(candidates, key=lambda p: abs(p.cutoff_year - target_year))


async def generate_character_profile(
    character_id: str,
    db: AsyncSession,
    cutoff_year: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generate a character profile using the Character Profiler Agent.

    Creates a CharacterProfileDB record, updates the CharacterDB record,
    and creates CharacterChunkDB entries linked to the profile.
    Also indexes chunks in the vector store.

    Args:
        character_id: Character UUID.
        db: Database session.
        cutoff_year: Year cutoff for the profile. Defaults to character's last_known_year.

    Returns:
        Dict with character, profile, chunk_count, and status.

    Raises:
        NotFoundError: If character not found.
        AIGenerationError: If profile generation fails.
    """
    # Load character with timeline and existing profiles
    result = await db.execute(
        select(CharacterDB)
        .options(selectinload(CharacterDB.profiles))
        .where(CharacterDB.id == character_id)
    )
    character = result.scalar_one_or_none()
    if not character:
        raise NotFoundError(f"Character {character_id} not found")

    # Default cutoff_year to character's last_known_year
    if cutoff_year is None:
        cutoff_year = character.last_known_year

    # Load timeline with generations
    result = await db.execute(
        select(TimelineDB)
        .options(selectinload(TimelineDB.generations))
        .where(TimelineDB.id == character.timeline_id)
    )
    timeline = result.scalar_one_or_none()
    if not timeline:
        raise NotFoundError(f"Timeline {character.timeline_id} not found")

    # Check if profile for this cutoff_year already exists — delete old one
    existing_profile = None
    for p in character.profiles:
        if p.cutoff_year == cutoff_year:
            existing_profile = p
            break

    if existing_profile:
        # Delete old profile (cascade deletes chunks)
        await db.delete(existing_profile)
        await db.flush()

    # Find the nearest existing profile for biography consistency context
    nearest_profile = _find_nearest_profile(
        character.profiles,
        target_year=cutoff_year,
        exclude_year=cutoff_year,
    )
    existing_biography: Optional[str] = None
    if nearest_profile:
        bio_result = await db.execute(
            select(CharacterChunkDB).where(
                CharacterChunkDB.profile_id == nearest_profile.id,
                CharacterChunkDB.chunk_type == "biography",
            )
        )
        bio_chunk = bio_result.scalar_one_or_none()
        if bio_chunk:
            existing_biography = bio_chunk.content
            logger.debug(
                f"Using biography from profile cutoff={nearest_profile.cutoff_year} "
                f"as consistency reference for {character.name}"
            )

    # Create new profile record
    profile = CharacterProfileDB(
        id=str(uuid4()),
        character_id=character_id,
        cutoff_year=cutoff_year,
        profile_status="generating",
    )
    db.add(profile)

    # Set character-level status to generating
    character.profile_status = "generating"
    await db.flush()

    try:
        # Combine timeline content filtered by cutoff_year
        timeline_content = _build_timeline_content(timeline, cutoff_year=cutoff_year)

        # Build era string from timeline data
        dev_date = timeline.root_deviation_date
        if isinstance(dev_date, str):
            base_year = int(dev_date[:4])
        else:
            base_year = dev_date.year

        character_era = None
        if timeline.generations:
            first_gen = min(timeline.generations, key=lambda g: g.generation_order)
            era_start = first_gen.start_year
            character_era = f"{base_year + era_start}-{cutoff_year}"

        # Get deviation info
        deviation_date = str(dev_date)
        deviation_description = timeline.root_deviation_description
        scenario_type = timeline.scenario_type

        # Call the profiler agent
        from app.agents.character_profiler_agent import generate_character_profile as agent_generate

        # Try to get per-agent model from LLM service
        model = None
        try:
            from app.services.llm_service import create_pydantic_ai_model_for_agent
            from app.models import AgentType
            model = await create_pydantic_ai_model_for_agent(db, AgentType.CHARACTER_PROFILER)
        except Exception:
            logger.debug("No LLM config available, using agent default")

        profile_output: CharacterProfileOutput = await agent_generate(
            character_name=character.name,
            character_title=character.title,
            character_era=character_era,
            timeline_content=timeline_content,
            deviation_date=deviation_date,
            deviation_description=deviation_description,
            scenario_type=scenario_type,
            existing_biography=existing_biography,
            model=model,
        )

        # Update stable identity fields on character (only if not set)
        character.full_name = profile_output.full_name or character.full_name
        character.title = profile_output.title or character.title
        character.birth_year = profile_output.birth_year or character.birth_year
        character.death_year = profile_output.death_year or character.death_year
        character.profile_status = "ready"
        character.profile_generated_at = datetime.now(timezone.utc)

        # Extract model info
        model_provider = "google"
        model_name = "gemini-2.5-flash"
        if model:
            model_provider = getattr(model, "name", None) or "google"
            model_name = str(model)

        character.profile_model_provider = model_provider
        character.profile_model_name = model_name

        # Profile-specific data lives on the profile, not the character
        profile.profile_status = "ready"
        profile.profile_generated_at = datetime.now(timezone.utc)
        profile.profile_model_provider = model_provider
        profile.profile_model_name = model_name
        profile.short_bio = profile_output.short_bio
        profile.role_summary = profile_output.role_summary
        profile.importance_score = profile_output.importance_score

        # Delete old character-level chunks (legacy, not tied to a profile)
        from sqlalchemy import delete
        await db.execute(
            delete(CharacterChunkDB).where(
                CharacterChunkDB.character_id == character_id,
                CharacterChunkDB.profile_id.is_(None),
            )
        )

        # Create new chunks linked to the profile
        chunks_created = []
        for chunk_output in profile_output.chunks:
            chunk = CharacterChunkDB(
                id=str(uuid4()),
                character_id=character_id,
                profile_id=profile.id,
                chunk_type=chunk_output.chunk_type,
                content=chunk_output.content,
                year_start=chunk_output.year_start,
                year_end=chunk_output.year_end,
                related_figures=chunk_output.related_figures if chunk_output.related_figures else None,
            )
            db.add(chunk)
            chunks_created.append(chunk)

        await db.flush()

        # Index chunks in vector store
        await _index_character_chunks(character, chunks_created, db)

        # Reload character with all profiles (and their chunks for counts)
        await db.refresh(character)
        result = await db.execute(
            select(CharacterDB)
            .options(
                selectinload(CharacterDB.profiles)
                .selectinload(CharacterProfileDB.chunks)
            )
            .where(CharacterDB.id == character_id)
        )
        character = result.scalar_one()

        logger.info(
            f"Generated profile for {character.name} (cutoff={cutoff_year}): "
            f"{len(chunks_created)} chunks, importance={character.importance_score}"
        )

        return {
            "character": character,
            "profile": profile,
            "chunk_count": len(chunks_created),
            "status": "ready",
        }

    except AIGenerationError:
        character.profile_status = "error"
        profile.profile_status = "error"
        await db.flush()
        raise
    except Exception as e:
        character.profile_status = "error"
        profile.profile_status = "error"
        await db.flush()
        logger.error(f"Profile generation failed for {character_id}: {e}", exc_info=True)
        raise AIGenerationError(
            f"Profile generation failed for character {character_id}",
            details={"error": str(e)},
        ) from e


def _build_timeline_content(
    timeline: TimelineDB,
    cutoff_year: Optional[int] = None,
) -> str:
    """
    Build combined timeline content string from generations.

    Args:
        timeline: Timeline with loaded generations.
        cutoff_year: If provided, only include generations whose actual_end <= cutoff_year.

    Returns:
        Formatted timeline content.
    """
    parts = [
        f"# Alternate Timeline: {timeline.root_deviation_description}",
        f"Deviation Date: {timeline.root_deviation_date}",
        f"Scenario Type: {timeline.scenario_type}",
        "",
    ]

    sections = [
        ("Executive Summary", "executive_summary"),
        ("Political Changes", "political_changes"),
        ("Conflicts and Wars", "conflicts_and_wars"),
        ("Economic Impacts", "economic_impacts"),
        ("Social Developments", "social_developments"),
        ("Technological Shifts", "technological_shifts"),
        ("Key Figures", "key_figures"),
        ("Long-Term Implications", "long_term_implications"),
    ]

    # Compute deviation base year for offset-to-actual conversion
    dev_date = timeline.root_deviation_date
    base_year = dev_date.year if hasattr(dev_date, 'year') else int(str(dev_date)[:4])

    for gen in sorted(timeline.generations, key=lambda g: g.generation_order):
        actual_start = base_year + gen.start_year
        actual_end = base_year + gen.end_year

        # Skip generations beyond the cutoff year
        if cutoff_year is not None and actual_end > cutoff_year:
            continue

        parts.append(f"\n## Generation {gen.generation_order} ({actual_start}-{actual_end})")
        for title, attr in sections:
            content = getattr(gen, attr, None)
            if content:
                parts.append(f"\n### {title}\n{content}")

        if gen.narrative_prose:
            parts.append(f"\n### Narrative\n{gen.narrative_prose}")

    return "\n".join(parts)


async def list_profiles(
    character_id: str,
    db: AsyncSession,
) -> List[CharacterProfileDB]:
    """
    List all profiles for a character, ordered by cutoff_year.

    Args:
        character_id: Character UUID.
        db: Database session.

    Returns:
        List of CharacterProfileDB records.

    Raises:
        NotFoundError: If character not found.
    """
    result = await db.execute(
        select(CharacterDB).where(CharacterDB.id == character_id)
    )
    if not result.scalar_one_or_none():
        raise NotFoundError(f"Character {character_id} not found")

    result = await db.execute(
        select(CharacterProfileDB)
        .options(selectinload(CharacterProfileDB.chunks))
        .where(CharacterProfileDB.character_id == character_id)
        .order_by(CharacterProfileDB.cutoff_year)
    )
    return list(result.scalars().all())


async def get_profile(
    character_id: str,
    profile_id: str,
    db: AsyncSession,
    include_chunks: bool = False,
) -> CharacterProfileDB:
    """
    Get a specific profile by ID.

    Args:
        character_id: Character UUID (for validation).
        profile_id: Profile UUID.
        db: Database session.
        include_chunks: Whether to eagerly load chunks.

    Returns:
        CharacterProfileDB record.

    Raises:
        NotFoundError: If character or profile not found.
    """
    query = select(CharacterProfileDB).where(
        CharacterProfileDB.id == profile_id,
        CharacterProfileDB.character_id == character_id,
    )
    if include_chunks:
        query = query.options(selectinload(CharacterProfileDB.chunks))

    result = await db.execute(query)
    profile = result.scalar_one_or_none()
    if not profile:
        raise NotFoundError(f"Profile {profile_id} not found for character {character_id}")
    return profile


async def _index_character_chunks(
    character: CharacterDB,
    chunks: List[CharacterChunkDB],
    db: AsyncSession,
) -> None:
    """
    Index character profile chunks in the vector store.

    Args:
        character: The character record.
        chunks: List of CharacterChunkDB records to index.
        db: Database session.
    """
    try:
        from app.services.vector_store_service import get_vector_store_service
        vs = get_vector_store_service()
        if not vs.enabled or "historical_figures" not in vs.collections:
            logger.debug("Vector store not available for character indexing")
            return

        collection = vs.collections["historical_figures"]
        for chunk in chunks:
            vector_id = f"char_{character.id}_{chunk.chunk_type}_{chunk.id}"
            try:
                embedding = vs._embed_texts([chunk.content])[0]
                metadata = vs._sanitize_metadata({
                    "character_id": character.id,
                    "character_name": character.name,
                    "timeline_id": character.timeline_id,
                    "chunk_type": chunk.chunk_type,
                    "year_start": chunk.year_start,
                    "year_end": chunk.year_end,
                })
                collection.add(
                    ids=[vector_id],
                    embeddings=[embedding],
                    documents=[chunk.content],
                    metadatas=[metadata],
                )
                chunk.vector_chunk_id = vector_id
            except Exception as e:
                logger.warning(f"Failed to index chunk {chunk.id}: {e}")
                continue

        await db.flush()
        logger.info(f"Indexed {len(chunks)} chunks for character {character.name}")

    except Exception as e:
        logger.warning(f"Character vector indexing failed: {e}")
