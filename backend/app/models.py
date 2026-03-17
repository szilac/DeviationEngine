"""
Pydantic data models for DeviationEngine redesigned API.

This module defines data models for the redesigned schema supporting:
- Timeline branching (create alternate timelines from alternate timelines)
- Unified generation model (reports + extensions + branches all use 'generations')
- Native translation support
- Integrated multimedia
- Future-proof audio features
"""

from datetime import datetime, date, timezone
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from uuid import UUID, uuid4
from typing import List, Optional, Dict, Any


# ============================================================================
# Language Constants
# ============================================================================

LANGUAGES = [
    {"code": "hu", "name": "Hungarian"},
    {"code": "de", "name": "German"},
    {"code": "es", "name": "Spanish"},
    {"code": "it", "name": "Italian"},
    {"code": "fr", "name": "French"},
    {"code": "pt", "name": "Portuguese"},
    {"code": "pl", "name": "Polish"},
    {"code": "nl", "name": "Dutch"},
    {"code": "ja", "name": "Japanese"},
    {"code": "zh", "name": "Chinese"},
]


# ============================================================================
# Core Enums
# ============================================================================


class ScenarioType(str, Enum):
    """Types of historical deviation scenarios."""

    LOCAL_DEVIATION = "local_deviation"
    GLOBAL_DEVIATION = "global_deviation"
    REALITY_FRACTURE = "reality_fracture"
    GEOLOGICAL_SHIFT = "geological_shift"
    EXTERNAL_INTERVENTION = "external_intervention"


class NarrativeMode(str, Enum):
    """Narrative generation modes."""

    NONE = "none"  # No narrative generation
    BASIC = "basic"  # Single-pass narrative from historian agent
    ADVANCED_OMNISCIENT = "advanced_omniscient"  # Two-pass: structured + omniscient storyteller
    ADVANCED_CUSTOM_POV = "advanced_custom_pov"  # Two-pass: structured + custom POV storyteller


class GenerationType(str, Enum):
    """Types of generations within a timeline."""

    INITIAL = "initial"  # First generation for a timeline
    EXTENSION = "extension"  # Temporal extension of existing timeline
    BRANCH_POINT = "branch_point"  # Branch creation point


class SkeletonType(str, Enum):
    """Types of skeletons."""

    TIMELINE_DRAFT = "timeline_draft"  # Draft for new timeline
    EXTENSION_DRAFT = "extension_draft"  # Draft for timeline extension
    BRANCH_DRAFT = "branch_draft"  # Draft for timeline branch


class SkeletonStatus(str, Enum):
    """Skeleton workflow status."""

    PENDING = "pending"  # Just generated, waiting for user review
    EDITING = "editing"  # User is actively editing
    APPROVED = "approved"  # User approved, ready to generate
    GENERATED = "generated"  # DEPRECATED: Previously marked after generation, now skeletons remain editable


class LLMProvider(str, Enum):
    """LLM provider options."""

    GOOGLE = "google"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    CLIPROXY = "cliproxy"


class AgentType(str, Enum):
    """Valid agent types for configuration."""

    HISTORIAN = "historian"
    STORYTELLER = "storyteller"
    SKELETON = "skeleton"
    SKELETON_HISTORIAN = "skeleton_historian"
    ILLUSTRATOR = "illustrator"
    SCRIPT_WRITER = "script_writer"
    TRANSLATOR = "translator"
    CHARACTER_PROFILER = "character_profiler"
    IMPERSONATOR = "impersonator"
    RIPPLE_ANALYST = "ripple_analyst"


class ImagePromptSkeletonStatus(str, Enum):
    """Status values for image prompt skeletons."""

    PENDING = "pending"
    EDITING = "editing"
    APPROVED = "approved"
    GENERATING = "generating"
    COMPLETED = "completed"


# ============================================================================
# Agent Output Models (unchanged from original)
# ============================================================================


class TimelineOutput(BaseModel):
    """
    Output model for AI-generated timeline content.

    This class represents the structured output from the AI agent before
    it gets converted to the final Generation model.
    """

    timeline_name: str = Field(
        default="Alternate Timeline",
        description="Short 3-5 word timeline name (REQUIRED - captures essence of deviation)"
    )
    executive_summary: str = Field(..., description="High-level overview of how history changed")
    political_changes: str = Field(..., description="Government, international relations, diplomacy")
    conflicts_and_wars: str = Field(..., description="Military conflicts, wars, and armed tensions")
    economic_impacts: str = Field(..., description="Trade, industry, financial systems")
    social_developments: str = Field(..., description="Culture, demographics, social movements")
    technological_shifts: str = Field(..., description="Innovation pace, key technologies affected")
    key_figures: str = Field(..., description="Important people in this alternate timeline")
    long_term_implications: str = Field(..., description="Lasting effects by end of period")
    narrative_prose: Optional[str] = Field(None, description="Optional story-like narrative")

    @field_validator('timeline_name', mode='before')
    @classmethod
    def generate_fallback_name(cls, v, info):
        """Generate a fallback timeline name if LLM doesn't provide one."""
        if v is None or v == "":
            # Try to generate a name from executive summary if available
            exec_summary = info.data.get('executive_summary', '')
            if exec_summary:
                # Extract first few significant words as fallback
                words = exec_summary.split()[:5]
                return ' '.join(words) if words else "Alternate Timeline"
            return "Alternate Timeline"
        return v


# ============================================================================
# Core Data Models (REDESIGNED)
# ============================================================================


class Generation(BaseModel):
    """
    Unified content for a time period within a timeline.

    Replaces the old Report/StructuredReport/ReportWithNarrative concepts.
    Each generation represents analysis for a specific time period.
    """

    model_config = ConfigDict(from_attributes=True)

    # Identity
    id: UUID = Field(default_factory=uuid4, description="Unique generation identifier")
    timeline_id: UUID = Field(..., description="Parent timeline ID")

    # Ordering
    generation_order: int = Field(..., description="Sequence number within timeline")
    generation_type: GenerationType = Field(..., description="Type of generation")

    # Period
    start_year: int = Field(..., description="Starting year (relative to deviation)")
    end_year: int = Field(..., description="Ending year (relative to deviation)")
    period_years: int = Field(..., description="Number of years covered")

    # Structured report (8 sections)
    executive_summary: str = Field(..., description="High-level overview")
    political_changes: str = Field(..., description="Government and diplomacy")
    conflicts_and_wars: str = Field(..., description="Military conflicts")
    economic_impacts: str = Field(..., description="Trade and industry")
    social_developments: str = Field(..., description="Culture and demographics")
    technological_shifts: str = Field(..., description="Innovation")
    key_figures: str = Field(..., description="Important people")
    long_term_implications: str = Field(..., description="Effects at end of period")

    # Translations
    report_translations: Optional[Dict[str, Any]] = Field(
        None, description="Translated reports (JSON)"
    )

    # Narrative
    narrative_mode: Optional[NarrativeMode] = Field(None, description="Narrative mode used")
    narrative_prose: Optional[str] = Field(None, description="Story-like narrative")
    narrative_custom_pov: Optional[str] = Field(None, description="Custom POV character")
    narrative_translations: Optional[Dict[str, str]] = Field(
        None, description="Translated narratives (JSON)"
    )

    # Audio
    audio_script: Optional[str] = Field(None, description="Podcast/documentary script")
    audio_script_format: Optional[str] = Field(None, description="Script format type")
    audio_url: Optional[str] = Field(None, description="URL to audio file")
    audio_local_path: Optional[str] = Field(None, description="Local file path")
    audio_duration_seconds: Optional[int] = Field(None, description="Duration in seconds")
    audio_voice_model: Optional[str] = Field(None, description="Voice model identifier")
    audio_voice_settings: Optional[Dict[str, Any]] = Field(
        None, description="Voice settings (JSON)"
    )
    audio_translations: Optional[Dict[str, Any]] = Field(
        None, description="Audio files in different languages (JSON)"
    )

    # Source tracking
    source_skeleton_id: Optional[UUID] = Field(None, description="Skeleton used for generation")
    source_context: Optional[str] = Field(None, description="Additional context used")

    # Model tracking
    report_model_provider: Optional[str] = Field(None, description="LLM provider for report")
    report_model_name: Optional[str] = Field(None, description="Model for report")
    narrative_model_provider: Optional[str] = Field(None, description="LLM provider for narrative")
    narrative_model_name: Optional[str] = Field(None, description="Model for narrative")
    audio_model_provider: Optional[str] = Field(None, description="LLM provider for audio")
    audio_model_name: Optional[str] = Field(None, description="Model for audio")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp"
    )

    @property
    def period_description(self) -> str:
        """Human-readable description of the time period."""
        if self.start_year == 0:
            return f"Years 0-{self.end_year} ({self.period_years} years)"
        return f"Years {self.start_year}-{self.end_year} ({self.period_years} years)"


class Media(BaseModel):
    """Media attached to generations (images, audio, video)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4, description="Unique media identifier")
    generation_id: UUID = Field(..., description="Parent generation ID")

    media_type: str = Field(..., description="Type of media (image, audio, video)")
    media_order: int = Field(..., description="Display order within generation")

    prompt_text: Optional[str] = Field(None, description="AI prompt used for generation")
    media_url: str = Field(..., description="URL to media file")
    media_local_path: Optional[str] = Field(None, description="Local file path")

    event_year: Optional[int] = Field(None, description="Associated year in timeline")
    title: Optional[str] = Field(None, description="User-friendly title")
    description: Optional[str] = Field(None, description="Caption or description")

    is_user_added: bool = Field(False, description="Manually added by user")
    is_user_modified: bool = Field(False, description="User edited AI-generated content")

    model_provider: Optional[str] = Field(None, description="LLM provider for prompt")
    model_name: Optional[str] = Field(None, description="Model for prompt")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp"
    )


class Timeline(BaseModel):
    """
    Complete alternate history timeline with branching support.

    Timelines can branch from other timelines, creating a tree structure.
    """

    model_config = ConfigDict(from_attributes=True)

    # Identity
    id: UUID = Field(default_factory=uuid4, description="Unique timeline identifier")

    # Branching support (NEW)
    parent_timeline_id: Optional[UUID] = Field(None, description="Parent timeline (if branched)")
    branch_point_year: Optional[int] = Field(None, description="Year where branch diverged")
    branch_deviation_description: Optional[str] = Field(
        None, description="What changed at branch point"
    )

    # Root deviation
    root_deviation_date: date = Field(..., description="Original deviation date")
    root_deviation_description: str = Field(..., description="Original deviation")
    scenario_type: ScenarioType = Field(..., description="Type of scenario")

    # Timeline name (short, AI-generated title)
    timeline_name: Optional[str] = Field(None, description="Short 3-5 word timeline name")

    # Generations (replaces reports)
    generations: List[Generation] = Field(default_factory=list, description="All generations")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp"
    )

    @property
    def latest_generation(self) -> Optional[Generation]:
        """Get most recent generation."""
        if not self.generations:
            return None
        return max(self.generations, key=lambda g: g.generation_order)

    @property
    def total_years_simulated(self) -> int:
        """Calculate total years from all generations."""
        if not self.generations:
            return 0
        return max(g.end_year for g in self.generations)

    @property
    def is_branch(self) -> bool:
        """Check if this is a branched timeline."""
        return self.parent_timeline_id is not None

    def get_generation_by_order(self, order: int) -> Optional[Generation]:
        """Get a specific generation by its order number."""
        for generation in self.generations:
            if generation.generation_order == order:
                return generation
        return None


class TimelineListItem(BaseModel):
    """Simplified timeline model for list endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique timeline identifier")

    # Branching info
    parent_timeline_id: Optional[UUID] = Field(None, description="Parent timeline (if branched)")
    branch_point_year: Optional[int] = Field(None, description="Branch divergence year")

    # Root deviation
    root_deviation_date: date = Field(..., description="Original deviation date")
    root_deviation_description: str = Field(..., description="Brief description")
    scenario_type: ScenarioType = Field(..., description="Type of scenario")

    # Timeline name (short, AI-generated title)
    timeline_name: Optional[str] = Field(None, description="Short 3-5 word timeline name")

    # Summary stats
    total_years_simulated: int = Field(..., description="Total years simulated")
    generation_count: int = Field(..., description="Number of generations")

    created_at: datetime = Field(..., description="Creation timestamp")

    # Audio content indicator
    audio_script_count: int = Field(0, description="Number of audio scripts created from this timeline")


# ============================================================================
# Request Models (REDESIGNED)
# ============================================================================


class TimelineCreationRequest(BaseModel):
    """Request for creating a new root timeline."""

    deviation_date: date = Field(..., description="Date of historical deviation", examples=["1914-06-28"])
    deviation_description: str = Field(
        ...,
        min_length=10,
        max_length=1500,
        description="Description of what changed in history",
    )
    simulation_years: int = Field(..., ge=1, le=50, description="Number of years to simulate")
    scenario_type: ScenarioType = Field(..., description="Type of deviation scenario")
    narrative_mode: NarrativeMode = Field(
        default=NarrativeMode.BASIC, description="Mode for narrative generation"
    )
    narrative_custom_pov: Optional[str] = Field(
        None, description="Custom perspective instructions (for ADVANCED_CUSTOM_POV)"
    )
    use_rag: Optional[bool] = Field(
        default=None,
        description="Use AI Smart Search (RAG) for historical context. If None, uses global CONTEXT_RETRIEVAL_MODE setting"
    )

    @model_validator(mode='after')
    def set_default_use_rag(self):
        """Set use_rag from environment if not explicitly provided."""
        if self.use_rag is None:
            import os
            # Read from environment variable (same as debug settings)
            context_mode = os.getenv("CONTEXT_RETRIEVAL_MODE", "rag").lower()
            self.use_rag = (context_mode == "rag")
        return self

    @field_validator("deviation_date")
    @classmethod
    def validate_deviation_date(cls, v: date) -> date:
        """Validate that deviation date is within acceptable historical range."""
        min_date = date(1880, 1, 1)
        max_date = date(2004, 12, 31)

        if v < min_date or v > max_date:
            raise ValueError(
                f"Deviation date must be between {min_date} and {max_date}. "
                f"This ensures sufficient historical context and avoids recent events."
            )
        return v

    @field_validator("narrative_custom_pov")
    @classmethod
    def validate_custom_pov(cls, v: Optional[str]) -> Optional[str]:
        """Validate custom POV: convert empty string to None, validate length if provided."""
        if v is not None and v.strip() == "":
            return None
        if v is not None and (len(v) < 10 or len(v) > 500):
            raise ValueError("Custom perspective must be between 10 and 500 characters")
        return v


class TimelineExtensionRequest(BaseModel):
    """Request for extending existing timeline."""

    timeline_id: UUID = Field(..., description="UUID of timeline to extend")
    additional_years: int = Field(..., ge=1, le=30, description="Additional years to simulate")
    additional_context: Optional[str] = Field(
        None, max_length=2000, description="Optional additional context"
    )
    narrative_mode: NarrativeMode = Field(
        default=NarrativeMode.BASIC, description="Mode for narrative generation"
    )
    narrative_custom_pov: Optional[str] = Field(
        None, description="Custom perspective instructions (for ADVANCED_CUSTOM_POV)"
    )
    use_rag: Optional[bool] = Field(
        default=None,
        description="Use AI Smart Search (RAG) for historical context. If None, uses global CONTEXT_RETRIEVAL_MODE setting"
    )

    @model_validator(mode='after')
    def set_default_use_rag(self):
        """Set use_rag from environment if not explicitly provided."""
        if self.use_rag is None:
            import os
            # Read from environment variable (same as debug settings)
            context_mode = os.getenv("CONTEXT_RETRIEVAL_MODE", "rag").lower()
            self.use_rag = (context_mode == "rag")
        return self

    @field_validator("additional_context")
    @classmethod
    def validate_additional_context(cls, v: Optional[str]) -> Optional[str]:
        """Validate additional context: convert empty string to None."""
        if v is not None and v.strip() == "":
            return None
        return v

    @field_validator("narrative_custom_pov")
    @classmethod
    def validate_custom_pov(cls, v: Optional[str]) -> Optional[str]:
        """Validate custom POV: convert empty string to None, validate length if provided."""
        if v is not None and v.strip() == "":
            return None
        if v is not None and (len(v) < 10 or len(v) > 500):
            raise ValueError("Custom perspective must be between 10 and 500 characters")
        return v


class GenerateFromSkeletonRequest(BaseModel):
    """Request for generating timeline from skeleton."""
    skeleton_id: UUID
    narrative_mode: Optional[NarrativeMode] = NarrativeMode.BASIC
    narrative_custom_pov: Optional[str] = None
    use_rag: Optional[bool] = Field(
        default=None,
        description="Use AI Smart Search (RAG) for historical context. If None, uses global CONTEXT_RETRIEVAL_MODE setting"
    )

    @model_validator(mode='after')
    def set_default_use_rag(self):
        """Set use_rag from environment if not explicitly provided."""
        if self.use_rag is None:
            import os
            # Read from environment variable (same as debug settings)
            context_mode = os.getenv("CONTEXT_RETRIEVAL_MODE", "rag").lower()
            self.use_rag = (context_mode == "rag")
        return self

    @field_validator("narrative_custom_pov")
    @classmethod
    def validate_custom_pov(cls, v: Optional[str]) -> Optional[str]:
        """Validate custom POV: convert empty string to None, validate length if provided."""
        if v is not None and v.strip() == "":
            return None
        if v is not None and (len(v) < 10 or len(v) > 500):
            raise ValueError("Custom perspective must be between 10 and 500 characters")
        return v


class ExtendFromSkeletonRequest(BaseModel):
    """Request for extending timeline from skeleton."""
    timeline_id: UUID
    skeleton_id: UUID
    narrative_mode: Optional[NarrativeMode] = NarrativeMode.BASIC
    narrative_custom_pov: Optional[str] = None
    use_rag: Optional[bool] = Field(
        default=None,
        description="Use AI Smart Search (RAG) for historical context. If None, uses global CONTEXT_RETRIEVAL_MODE setting"
    )

    @model_validator(mode='after')
    def set_default_use_rag(self):
        """Set use_rag from environment if not explicitly provided."""
        if self.use_rag is None:
            import os
            # Read from environment variable (same as debug settings)
            context_mode = os.getenv("CONTEXT_RETRIEVAL_MODE", "rag").lower()
            self.use_rag = (context_mode == "rag")
        return self

    @field_validator("narrative_custom_pov")
    @classmethod
    def validate_custom_pov(cls, v: Optional[str]) -> Optional[str]:
        """Validate custom POV: convert empty string to None, validate length if provided."""
        if v is not None and v.strip() == "":
            return None
        if v is not None and (len(v) < 10 or len(v) > 500):
            raise ValueError("Custom perspective must be between 10 and 500 characters")
        return v


class TimelineBranchRequest(BaseModel):
    """Request for branching from existing timeline."""

    source_timeline_id: UUID = Field(..., description="Timeline to branch from")
    branch_point_year: int = Field(..., description="Year where branch diverges")
    branch_deviation_description: str = Field(
        ..., min_length=10, max_length=500, description="What changed at branch point"
    )
    simulation_years: int = Field(..., ge=1, le=50, description="Years to simulate after branch")
    narrative_mode: NarrativeMode = Field(
        default=NarrativeMode.BASIC, description="Mode for narrative generation"
    )
    narrative_custom_pov: Optional[str] = Field(
        None, description="Custom perspective instructions (for ADVANCED_CUSTOM_POV)"
    )

    @field_validator("narrative_custom_pov")
    @classmethod
    def validate_custom_pov(cls, v: Optional[str]) -> Optional[str]:
        """Validate custom POV: convert empty string to None, validate length if provided."""
        if v is not None and v.strip() == "":
            return None
        if v is not None and (len(v) < 10 or len(v) > 500):
            raise ValueError("Custom perspective must be between 10 and 500 characters")
        return v


# ============================================================================
# Skeleton Models (UPDATED)
# ============================================================================


class SkeletonEventCreate(BaseModel):
    """Request model for creating a skeleton event."""

    event_date: date = Field(..., description="Date of the event (YYYY-MM-DD)")
    location: str = Field(..., min_length=2, max_length=255, description="Geographic location")
    description: str = Field(..., min_length=10, max_length=2000, description="Event description")


class SkeletonEventUpdate(BaseModel):
    """Request model for updating a skeleton event."""

    id: Optional[UUID] = Field(None, description="Event ID (null for new events)")
    event_date: date = Field(..., description="Date of the event (YYYY-MM-DD)")
    location: str = Field(..., min_length=2, max_length=255, description="Location")
    description: str = Field(..., min_length=10, max_length=2000, description="Description")
    event_order: int = Field(..., ge=0, description="Position in timeline (0-based)")


class SkeletonEventsUpdateRequest(BaseModel):
    """Request model for bulk updating skeleton events."""

    events_update: List["SkeletonEventUpdate"] = Field(
        default_factory=list, description="List of events to create or update"
    )
    deleted_event_ids: List[UUID] = Field(
        default_factory=list, description="List of event IDs to delete"
    )


class SkeletonEventResponse(BaseModel):
    """Response model for a skeleton event."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Event ID")
    skeleton_id: UUID = Field(..., description="Parent skeleton ID")
    event_date: date = Field(..., description="Event date")
    event_year: int = Field(..., description="Year relative to deviation")
    location: str = Field(..., description="Geographic location")
    description: str = Field(..., description="Event description")
    event_order: int = Field(..., description="Display order")
    is_user_added: bool = Field(..., description="True if manually added")
    is_user_modified: bool = Field(..., description="True if edited")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class SkeletonResponse(BaseModel):
    """Response model for a skeleton."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Skeleton ID")
    timeline_id: Optional[UUID] = Field(None, description="Associated timeline ID")
    generation_id: Optional[UUID] = Field(None, description="Associated generation ID")

    skeleton_type: SkeletonType = Field(..., description="Type of skeleton")
    status: SkeletonStatus = Field(..., description="Current status")

    # For timeline drafts
    deviation_date: Optional[date] = Field(None, description="Deviation date")
    deviation_description: Optional[str] = Field(None, description="Deviation description")
    scenario_type: Optional[ScenarioType] = Field(None, description="Scenario type")

    # For extension/branch drafts
    parent_timeline_id: Optional[UUID] = Field(None, description="Parent timeline")
    extension_start_year: Optional[int] = Field(None, description="Extension start year")
    extension_end_year: Optional[int] = Field(None, description="Extension end year")
    branch_point_year: Optional[int] = Field(None, description="Branch point year")
    branch_deviation_description: Optional[str] = Field(None, description="Branch deviation")

    # Model metadata
    model_provider: Optional[str] = Field(None, description="LLM provider used")
    model_name: Optional[str] = Field(None, description="Model used")

    # Timestamps
    generated_at: datetime = Field(..., description="Generation timestamp")
    approved_at: Optional[datetime] = Field(None, description="Approval timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Events
    events: List[SkeletonEventResponse] = Field(default_factory=list, description="Skeleton events")

    @property
    def period_years(self) -> Optional[int]:
        """
        Calculate the period years covered by this skeleton.

        For timeline drafts: calculated from events span
        For extension drafts: extension_end_year - extension_start_year
        For branch drafts: calculated from events span
        """
        if self.skeleton_type == SkeletonType.EXTENSION_DRAFT:
            if self.extension_start_year is not None and self.extension_end_year is not None:
                return self.extension_end_year - self.extension_start_year

        # For timeline and branch drafts, calculate from events
        if self.events:
            min_year = min(event.event_year for event in self.events)
            max_year = max(event.event_year for event in self.events)
            return max_year - min_year + 1

        return None

    @property
    def start_year(self) -> int:
        """
        Get the start year for this skeleton.

        For timeline/branch drafts: 0 (starts from deviation)
        For extension drafts: extension_start_year
        """
        if self.skeleton_type == SkeletonType.EXTENSION_DRAFT:
            return self.extension_start_year or 0
        return 0

    @property
    def end_year(self) -> Optional[int]:
        """
        Get the end year for this skeleton.

        For extension drafts: extension_end_year
        For timeline/branch drafts: calculated from period_years
        """
        if self.skeleton_type == SkeletonType.EXTENSION_DRAFT:
            return self.extension_end_year

        if self.period_years is not None:
            return self.start_year + self.period_years

        return None


# ============================================================================
# LLM Configuration Models (unchanged)
# ============================================================================


class LLMConfigRequest(BaseModel):
    """Request model for updating LLM configuration."""

    provider: LLMProvider = Field(..., description="LLM provider to use")
    model_name: str = Field(..., min_length=1, max_length=100, description="Model identifier")
    api_key_google: Optional[str] = Field(None, description="Google Gemini API key (optional)")
    api_key_openrouter: Optional[str] = Field(None, description="OpenRouter API key (optional)")
    ollama_base_url: Optional[str] = Field(None, description="Ollama server base URL (optional)")
    api_key_anthropic: Optional[str] = Field(None, description="Anthropic API key (optional)")
    api_key_openai: Optional[str] = Field(None, description="OpenAI API key (optional)")

    @field_validator("api_key_google", "api_key_openrouter", "ollama_base_url", "api_key_anthropic", "api_key_openai")
    @classmethod
    def validate_api_keys(cls, v: Optional[str]) -> Optional[str]:
        """Trim whitespace and convert empty strings to None."""
        if v is not None and v.strip() == "":
            return None
        return v.strip() if v else None


class LLMConfigResponse(BaseModel):
    """Response model for LLM configuration."""

    model_config = ConfigDict(from_attributes=True)

    provider: LLMProvider = Field(..., description="Current LLM provider")
    model_name: str = Field(..., description="Current model identifier")
    api_key_google_set: bool = Field(..., description="Whether Google API key is configured")
    api_key_openrouter_set: bool = Field(..., description="Whether OpenRouter API key is configured")
    ollama_base_url: Optional[str] = Field(None, description="Ollama server base URL")
    api_key_anthropic_set: bool = Field(..., description="Whether Anthropic API key is configured")
    api_key_openai_set: bool = Field(..., description="Whether OpenAI API key is configured")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")


class AvailableModelsResponse(BaseModel):
    """Response model for available models per provider."""

    google: List[str] = Field(..., description="Available Google Gemini models")
    openrouter: List[str] = Field(..., description="Available OpenRouter models")
    ollama: List[str] = Field(..., description="Available Ollama models")
    anthropic: List[str] = Field(..., description="Available Anthropic Claude models")
    openai: List[str] = Field(..., description="Available OpenAI models")
    cliproxy: List[str] = Field(..., description="Available CLIProxyAPI models")


class AgentLLMConfigRequest(BaseModel):
    """Request model for creating/updating per-agent LLM config."""

    agent_type: AgentType = Field(..., description="Type of agent to configure")
    provider: LLMProvider = Field(..., description="LLM provider to use")
    model_name: str = Field(..., min_length=1, max_length=100, description="Model identifier")

    # Optional API key/URL overrides
    api_key_google: Optional[str] = Field(None, description="Google API key override (optional)")
    api_key_openrouter: Optional[str] = Field(None, description="OpenRouter API key override (optional)")
    ollama_base_url: Optional[str] = Field(None, description="Ollama server URL override (optional)")
    api_key_anthropic: Optional[str] = Field(None, description="Anthropic API key override (optional)")
    api_key_openai: Optional[str] = Field(None, description="OpenAI API key override (optional)")

    # Optional model settings overrides
    max_tokens: Optional[int] = Field(None, ge=1024, le=32768, description="Max tokens override")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Temperature override")

    enabled: bool = Field(True, description="Whether this override is active")

    @field_validator("api_key_google", "api_key_openrouter", "ollama_base_url", "api_key_anthropic", "api_key_openai")
    @classmethod
    def validate_api_keys(cls, v: Optional[str]) -> Optional[str]:
        """Trim whitespace and convert empty strings to None."""
        if v is not None and v.strip() == "":
            return None
        return v.strip() if v else None


class AgentLLMConfigResponse(BaseModel):
    """Response model for per-agent LLM config."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Configuration ID")
    agent_type: AgentType = Field(..., description="Type of agent")
    provider: LLMProvider = Field(..., description="LLM provider")
    model_name: str = Field(..., description="Model identifier")

    # Security: Don't expose full keys, just whether they're set
    api_key_google_set: bool = Field(..., description="Whether Google API key is set")
    api_key_openrouter_set: bool = Field(..., description="Whether OpenRouter API key is set")
    ollama_base_url: Optional[str] = Field(None, description="Ollama server URL")
    api_key_anthropic_set: bool = Field(..., description="Whether Anthropic API key is configured for this agent")
    api_key_openai_set: bool = Field(..., description="Whether OpenAI API key is configured for this agent")

    max_tokens: Optional[int] = Field(None, description="Max tokens override")
    temperature: Optional[float] = Field(None, description="Temperature override")
    enabled: bool = Field(..., description="Whether this override is active")

    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")


class AllLLMConfigsResponse(BaseModel):
    """Response model containing all LLM configurations."""

    global_config: LLMConfigResponse = Field(..., description="Global default configuration")
    agent_configs: Dict[AgentType, AgentLLMConfigResponse] = Field(
        ..., description="Per-agent configurations (only includes configured agents)"
    )
    agents_with_overrides: List[AgentType] = Field(..., description="Agents with custom configs")
    agents_using_global: List[AgentType] = Field(..., description="Agents using global config")


# ============================================================================
# Agent Output Models
# ============================================================================


class StructuredReport(BaseModel):
    """Structured analytical report output from historian agent (8 sections only)."""

    executive_summary: str = Field(..., description="High-level overview")
    political_changes: str = Field(..., description="Government and diplomacy")
    conflicts_and_wars: str = Field(..., description="Military conflicts")
    economic_impacts: str = Field(..., description="Trade and industry")
    social_developments: str = Field(..., description="Culture and demographics")
    technological_shifts: str = Field(..., description="Innovation")
    key_figures: str = Field(..., description="Important people")
    long_term_implications: str = Field(..., description="Effects at end of period")


# ============================================================================
# Utility Response Models
# ============================================================================


class HistoricalEvent(BaseModel):
    """Model for historical events in the original timeline."""

    title: str = Field(..., description="Brief title of the event")
    start_year: int = Field(..., description="Year when the event started")
    end_year: int = Field(..., description="Year when the event ended")
    event_type: str = Field(..., description="Type of event (milestone, period, conflict, etc.)")
    impact_level: str = Field(..., description="Level of historical impact (low, medium, high)")
    description: str = Field(..., description="Detailed description of the event")

    @property
    def duration_years(self) -> int:
        """Calculate the duration of the event in years."""
        return self.end_year - self.start_year + 1

    @property
    def is_period(self) -> bool:
        """Check if this event spans multiple years."""
        return self.end_year > self.start_year


# ============================================================================
# Image Generation Models
# ============================================================================


class ImagePromptUpdate(BaseModel):
    """Model for updating an image prompt during editing phase."""

    id: Optional[str] = Field(None, description="Prompt ID (None for new prompts)")
    prompt_text: str = Field(..., min_length=10, max_length=2000, description="Detailed image generation prompt")
    event_year: Optional[int] = Field(None, description="Associated year in timeline")
    title: str = Field(..., min_length=1, max_length=255, description="User-friendly title")
    description: Optional[str] = Field(None, max_length=1000, description="Brief description or caption")
    prompt_order: int = Field(..., ge=0, description="Display order (0-indexed)")
    style_notes: Optional[str] = Field(None, max_length=500, description="Style guidance")


class ImagePromptSkeletonCreate(BaseModel):
    """Request model for generating image prompt skeleton."""

    timeline_id: UUID = Field(..., description="UUID of the timeline")
    generation_id: Optional[UUID] = Field(None, description="Optional UUID of specific generation")
    num_images: int = Field(..., ge=3, le=20, description="Number of images to generate")
    focus_areas: Optional[List[str]] = Field(None, description="Optional focus areas")

    @field_validator('focus_areas')
    @classmethod
    def validate_focus_areas(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate focus areas."""
        if v is not None:
            valid_areas = {"political", "economic", "social", "technological", "military", "cultural"}
            invalid = set(v) - valid_areas
            if invalid:
                raise ValueError(f"Invalid focus areas: {invalid}. Valid areas: {valid_areas}")
        return v


class ImagePromptSkeletonResponse(BaseModel):
    """Response model for image prompt skeleton."""

    id: UUID = Field(..., description="Unique skeleton identifier")
    timeline_id: UUID = Field(..., description="Parent timeline UUID")
    generation_id: Optional[UUID] = Field(None, description="Optional specific generation UUID")
    status: str = Field(..., description="Current status")
    num_images: int = Field(..., description="Number of images to generate")
    focus_areas: Optional[List[str]] = Field(None, description="Optional focus areas")
    prompts: List[dict] = Field(default_factory=list, description="List of image prompts")
    model_provider: Optional[str] = Field(None, description="LLM provider used")
    model_name: Optional[str] = Field(None, description="Specific model used")
    created_at: datetime = Field(..., description="Creation timestamp")
    approved_at: Optional[datetime] = Field(None, description="Approval timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")


class TimelineImageResponse(BaseModel):
    """Response model for timeline images."""

    id: UUID = Field(..., description="Unique image identifier")
    timeline_id: UUID = Field(..., description="Parent timeline UUID")
    generation_id: Optional[UUID] = Field(None, description="Optional specific generation UUID")
    media_type: str = Field(..., description="Type of media")
    prompt_text: str = Field(..., description="Prompt used for generation")
    image_url: str = Field(..., description="URL to the generated image")
    event_year: Optional[int] = Field(None, description="Associated year in timeline")
    title: str = Field(..., description="User-friendly title")
    description: Optional[str] = Field(None, description="Brief description or caption")
    media_order: int = Field(..., description="Display order")
    is_user_added: bool = Field(default=False, description="True if user manually added")
    is_user_modified: bool = Field(default=False, description="True if user edited prompt")
    model_provider: Optional[str] = Field(None, description="LLM provider")
    model_name: Optional[str] = Field(None, description="Specific model")
    generated_at: Optional[datetime] = Field(None, description="Generation timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")


class GenerateImagesRequest(BaseModel):
    """Request model for generating images from approved prompt skeleton."""

    skeleton_id: UUID = Field(..., description="UUID of the approved prompt skeleton")


# ============================================================================
# Translation Service Models
# ============================================================================


class TranslationRequest(BaseModel):
    """Request model for translating generation content."""

    target_language: str = Field(
        ...,
        min_length=2,
        max_length=5,
        description="Target language code (e.g., 'hu', 'de', 'es', 'it')"
    )
    method: str = Field(
        'deepl',
        pattern=r'^(deepl|llm)$',
        description="Translation method: 'deepl' or 'llm'"
    )

    @field_validator("target_language")
    @classmethod
    def validate_target_language(cls, v: str) -> str:
        """Validate that target language is supported."""
        supported_languages = {"hu", "de", "es", "it", "fr", "pt", "pl", "nl", "ja", "zh"}
        v_lower = v.lower()
        if v_lower not in supported_languages:
            raise ValueError(
                f"Language '{v}' is not supported. "
                f"Supported languages: {', '.join(sorted(supported_languages))}"
            )
        return v_lower


class TranslationResponse(BaseModel):
    """Response model for generation translation."""

    generation_id: UUID = Field(..., description="Generation UUID")
    timeline_id: UUID = Field(..., description="Parent timeline UUID")
    generation_order: int = Field(..., description="Generation order number")
    target_language: str = Field(..., description="Target language code")
    translations: Dict[str, str] = Field(..., description="Translated sections")
    character_count: int = Field(..., description="Total characters translated")
    cached: bool = Field(..., description="Whether result was cached")
    translated_at: datetime = Field(..., description="Translation timestamp (UTC)")


class NarrativeTranslationResponse(BaseModel):
    """Response model for narrative prose translation."""

    generation_id: UUID = Field(..., description="Generation UUID")
    timeline_id: UUID = Field(..., description="Parent timeline UUID")
    generation_order: int = Field(..., description="Generation order number")
    target_language: str = Field(..., description="Target language code")
    narrative_prose: str = Field(..., description="Translated narrative text")
    character_count: int = Field(..., description="Total characters translated")
    cached: bool = Field(..., description="Whether result was cached")
    translated_at: datetime = Field(..., description="Translation timestamp (UTC)")


class TranslationUsageResponse(BaseModel):
    """Response model for translation usage statistics."""

    year_month: str = Field(..., description="Month in YYYY-MM format")
    characters_used: int = Field(..., description="Characters translated this month")
    characters_limit: int = Field(..., description="Monthly character limit")
    percentage_used: float = Field(..., description="Percentage of limit used")
    api_calls: int = Field(..., description="Number of API calls made")
    estimated_cost: float = Field(default=0.00, description="Estimated cost in USD")


class TranslationConfigRequest(BaseModel):
    """Request model for updating translation configuration."""

    api_key: str = Field(..., min_length=1, description="DeepL API authentication key")
    api_tier: str = Field(default="free", description="API tier (free or pro)")
    enabled: bool = Field(default=True, description="Enable/disable translation service")

    @field_validator("api_tier")
    @classmethod
    def validate_api_tier(cls, v: str) -> str:
        """Validate API tier."""
        if v.lower() not in ("free", "pro"):
            raise ValueError("API tier must be 'free' or 'pro'")
        return v.lower()

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate and trim API key."""
        return v.strip()


class TranslationConfigResponse(BaseModel):
    """Response model for translation configuration."""

    model_config = ConfigDict(from_attributes=True)

    enabled: bool = Field(..., description="Whether translation is enabled")
    api_tier: str = Field(..., description="API tier (free or pro)")
    api_key_set: bool = Field(..., description="Whether API key is configured")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")


# ============================================================================
# Audio Content Generation Models
# ============================================================================


class ScriptType(str, Enum):
    """Types of audio scripts."""

    PODCAST = "podcast"
    DOCUMENTARY = "documentary"
    NEWS_REPORT = "news_report"
    STORYTELLING = "storytelling"


class ScriptTone(str, Enum):
    """Tone options for scripts."""

    FORMAL = "formal"
    CASUAL = "casual"
    DRAMATIC = "dramatic"
    NEUTRAL = "neutral"
    HUMOROUS = "humorous"
    AUTHORITATIVE = "authoritative"


class ScriptPacing(str, Enum):
    """Pacing options for scripts."""

    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"
    VARIED = "varied"


class ScriptStatus(str, Enum):
    """Script workflow status."""

    DRAFT = "draft"
    APPROVED = "approved"
    AUDIO_GENERATED = "audio_generated"


class ScriptPreset(BaseModel):
    """Script preset configuration."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique preset identifier")
    name: str = Field(..., description="Preset display name")
    description: str = Field(..., description="User-facing description")
    script_type: ScriptType = Field(..., description="Type of script")
    tone: ScriptTone = Field(..., description="Tone setting")
    pacing: ScriptPacing = Field(..., description="Pacing setting")
    voice_count: int = Field(..., ge=1, le=2, description="Number of voices (1 or 2)")
    voice_roles: Dict[str, str] = Field(..., description="Voice role definitions")
    style_instructions: str = Field(..., description="Detailed style instructions for agent")
    prompt_template_name: str = Field(..., description="Jinja2 template filename")
    is_system: bool = Field(..., description="True if built-in system preset")
    is_active: bool = Field(..., description="True if active, false if soft-deleted")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")


class AudioScript(BaseModel):
    """Audio script model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique script identifier")
    generation_ids: List[UUID] = Field(..., description="Generation UUIDs used as source")
    title: str = Field(..., description="Script title")
    description: Optional[str] = Field(None, description="Optional script description")
    preset_id: str = Field(..., description="Preset used for generation (can be UUID or string ID)")
    preset: Optional[ScriptPreset] = Field(None, description="Populated preset (from join)")
    custom_instructions: Optional[str] = Field(None, description="User custom instructions")
    script_content: str = Field(..., description="Markdown script with speaker markers")
    script_structure: str = Field(..., description="'single_voice' or 'dual_voice'")
    word_count: int = Field(..., description="Total word count")
    estimated_duration_seconds: int = Field(..., description="Estimated audio duration")
    status: ScriptStatus = Field(..., description="Workflow status")
    model_provider: Optional[str] = Field(None, description="LLM provider used")
    model_name: Optional[str] = Field(None, description="Model used")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    approved_at: Optional[datetime] = Field(None, description="Approval timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")


class ScriptTranslation(BaseModel):
    """Script translation model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique translation identifier")
    script_id: UUID = Field(..., description="Parent script ID")
    language_code: str = Field(..., description="ISO 639-1 language code")
    language_name: str = Field(..., description="Human-readable language name")
    translated_content: str = Field(..., description="Translated markdown script")
    word_count: Optional[int] = Field(None, description="Word count of translated text")
    translation_method: str = Field('deepl', description="Translation method: 'deepl' or 'llm'")
    is_human_translated: bool = Field(..., description="True if human-translated")
    translation_quality_score: Optional[float] = Field(None, description="Quality score (0-1)")
    translation_model_provider: Optional[str] = Field(None, description="LLM provider used")
    translation_model_name: Optional[str] = Field(None, description="Model used")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")


class AudioFile(BaseModel):
    """Audio file model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique audio file identifier")
    script_id: UUID = Field(..., description="Parent script ID")
    source_type: str = Field(..., description="'original' or 'translation'")
    script_translation_id: Optional[UUID] = Field(None, description="Translation ID (if applicable)")
    language_code: str = Field(..., description="Language of the audio")
    audio_local_path: str = Field(..., description="Absolute path on local filesystem")
    audio_url: Optional[str] = Field(None, description="Relative path for frontend access")
    file_size_bytes: int = Field(..., description="File size in bytes")
    duration_seconds: int = Field(..., description="Audio duration in seconds")
    format: str = Field(..., description="Audio format (mp3, wav, pcm)")
    sample_rate: Optional[int] = Field(None, description="Sample rate (e.g., 24000 Hz)")
    bit_rate: Optional[int] = Field(None, description="Bit rate (e.g., 128000)")
    voice_model: str = Field(..., description="Voice model used")
    voice_settings: Optional[Dict[str, Any]] = Field(None, description="Voice settings JSON")
    voice_ids: Optional[Dict[str, str]] = Field(None, description="Voice IDs mapping")
    model_provider: str = Field(..., description="TTS provider")
    model_name: str = Field(..., description="TTS model name")
    generated_at: datetime = Field(..., description="Generation timestamp (UTC)")


# Request Models


class ScriptGenerationRequest(BaseModel):
    """Request to generate audio script."""

    generation_ids: List[UUID] = Field(..., min_length=1, max_length=10, description="Generation IDs to use as source")
    preset_id: str = Field(..., description="Preset ID to use for generation (can be system preset ID or custom UUID)")
    custom_instructions: Optional[str] = Field(None, max_length=1000, description="Optional custom instructions")
    title: Optional[str] = Field(None, max_length=200, description="Optional script title")


class ScriptUpdateRequest(BaseModel):
    """Request to update script content."""

    script_content: str = Field(..., min_length=100, description="Updated script content")
    title: Optional[str] = Field(None, max_length=200, description="Optional updated title")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")


class ScriptTranslationRequest(BaseModel):
    """Request to translate script."""

    target_languages: List[str] = Field(..., min_length=1, max_length=10, description="List of target language codes")
    method: str = Field('deepl', pattern=r'^(deepl|llm)$', description="Translation method: 'deepl' or 'llm'")


class AudioGenerationRequest(BaseModel):
    """Request to generate audio from script."""

    voice_settings: Optional[Dict[str, Any]] = Field(None, description="Optional voice settings")
    voice_ids: Optional[Dict[str, str]] = Field(None, description="Optional voice IDs for multi-speaker")


class PresetCreateRequest(BaseModel):
    """Request to create custom preset."""

    name: str = Field(..., min_length=3, max_length=100, description="Preset name")
    description: str = Field(..., min_length=10, max_length=500, description="Preset description")
    script_type: ScriptType = Field(..., description="Type of script")
    tone: ScriptTone = Field(..., description="Tone setting")
    pacing: ScriptPacing = Field(..., description="Pacing setting")
    voice_count: int = Field(..., ge=1, le=2, description="Number of voices")
    voice_roles: Dict[str, str] = Field(..., description="Voice role definitions")
    style_instructions: str = Field(..., min_length=50, max_length=2000, description="Style instructions")
    prompt_template_name: str = Field(default="script_writer/generic.jinja2", description="Template filename")


class PresetUpdateRequest(BaseModel):
    """Request to update custom preset."""

    name: Optional[str] = Field(None, min_length=3, max_length=100, description="Updated name")
    description: Optional[str] = Field(None, min_length=10, max_length=500, description="Updated description")
    tone: Optional[ScriptTone] = Field(None, description="Updated tone")
    pacing: Optional[ScriptPacing] = Field(None, description="Updated pacing")
    voice_roles: Optional[Dict[str, str]] = Field(None, description="Updated voice roles")
    style_instructions: Optional[str] = Field(None, min_length=50, max_length=2000, description="Updated instructions")
    prompt_template_name: Optional[str] = Field(None, description="Updated template filename")


# ============================================================================
# NotebookLM Studio Integration Models
# ============================================================================


class NLMAudioFormat(str, Enum):
    """NotebookLM audio overview formats."""

    DEEP_DIVE = "deep_dive"
    BRIEF = "brief"
    CRITIQUE = "critique"
    DEBATE = "debate"


class NLMAudioLength(str, Enum):
    """NotebookLM audio overview lengths."""

    SHORT = "short"
    DEFAULT = "default"
    LONG = "long"


class NLMJobStatus(str, Enum):
    """NotebookLM job lifecycle states."""

    PENDING = "pending"
    CREATING = "creating"
    UPLOADING = "uploading"
    GENERATING = "generating"
    POLLING = "polling"
    COMPLETED = "completed"
    FAILED = "failed"


class NotebookLMGenerateRequest(BaseModel):
    """Request to start a NotebookLM studio generation job."""
    generation_ids: List[str] = Field(..., min_length=1, max_length=10)
    timeline_id: Optional[str] = None
    content_type: str = Field(default="audio")
    nlm_format: NLMAudioFormat = NLMAudioFormat.DEEP_DIVE
    nlm_length: NLMAudioLength = NLMAudioLength.DEFAULT
    nlm_focus: Optional[str] = Field(default=None, max_length=500)
    language_code: str = Field(default="en")
    include_reports: bool = True
    include_narratives: bool = True


class NotebookLMJob(BaseModel):
    """NotebookLM job state, returned to frontend for polling."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    timeline_id: Optional[str] = None
    generation_ids: List[str]
    notebook_id: Optional[str] = None
    artifact_id: Optional[str] = None
    content_type: str
    nlm_format: NLMAudioFormat
    nlm_length: NLMAudioLength
    nlm_focus: Optional[str] = None
    language_code: str
    status: NLMJobStatus
    error_message: Optional[str] = None
    audio_local_path: Optional[str] = None
    audio_url: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime


class NLMAvailabilityResponse(BaseModel):
    """Response for nlm CLI availability check."""
    available: bool
    authenticated: bool
    error: Optional[str] = None


# ============================================================================
# Debug Settings Models
# ============================================================================


class DebugSettings(BaseModel):
    """Debug settings for RAG and Agent prompts."""

    rag_debug_mode: bool = Field(default=False, description="Enable RAG retrieval debugging logs")
    debug_agent_prompts: bool = Field(default=False, description="Save agent prompts to files")
    vector_store_enabled: bool = Field(default=True, description="Enable vector RAG (false = legacy mode)")
    context_retrieval_mode: str = Field(default="rag", description="Context retrieval mode: 'rag' or 'legacy'")


class DebugSettingsUpdate(BaseModel):
    """Request to update debug settings."""

    rag_debug_mode: Optional[bool] = Field(None, description="Enable RAG retrieval debugging logs")
    debug_agent_prompts: Optional[bool] = Field(None, description="Save agent prompts to files")
    vector_store_enabled: Optional[bool] = Field(None, description="Enable vector RAG (false = legacy mode)")
    context_retrieval_mode: Optional[str] = Field(None, description="Context retrieval mode: 'rag' or 'legacy'")


# ============================================================================
# API Response Models
# ============================================================================


# ============================================================================
# Novella Models
# ============================================================================


class NovellaGenerateRequest(BaseModel):
    """Request to generate a new standalone novella."""

    generation_ids: List[str] = Field(
        ..., min_length=1, description="Ordered source generation UUIDs"
    )
    focus_instructions: Optional[str] = Field(
        None, max_length=1000, description="Optional author's brief / focus"
    )


class NovellaContinueRequest(BaseModel):
    """Request to generate a continuation of an existing novella."""

    generation_ids: List[str] = Field(
        ..., min_length=1, description="Ordered source generation UUIDs for this installment"
    )
    focus_instructions: Optional[str] = Field(
        None, max_length=1000, description="Optional focus for this installment"
    )


class NovellaResponse(BaseModel):
    """Response model for a single novella."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    timeline_id: str
    series_id: Optional[str]
    series_order: int
    generation_ids: List[str]
    title: str
    content: str
    focus_instructions: Optional[str]
    model_provider: str
    model_name: str
    created_at: datetime


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Health status of the API")
    version: str = Field(..., description="API version")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error type/name")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Additional error details")


class ApiResponse(BaseModel):
    """Generic API response wrapper."""

    data: Optional[dict] = Field(None, description="Response data if successful")
    error: Optional[ErrorResponse] = Field(None, description="Error information if failed")
    status: int = Field(..., description="HTTP status code")


# ============================================================================
# Historical Figure Chat Models
# ============================================================================


class CharacterProfileStatus(str, Enum):
    """Character profile generation status."""

    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    ERROR = "error"


class CharacterSource(str, Enum):
    """How a character was created."""

    AUTO_DETECTED = "auto_detected"
    USER_CREATED = "user_created"


class ChatMessageRole(str, Enum):
    """Chat message role."""

    USER = "user"
    CHARACTER = "character"


# --- Character Profile Agent Output ---


class CharacterChunkOutput(BaseModel):
    """A single chunk of character information from the profiler agent."""

    chunk_type: str = Field(..., description="Type: biography, personality, relationships, beliefs, speaking_style, event_involvement")
    content: str = Field(..., description="Chunk text content (150-400 words)")
    year_start: Optional[int] = Field(None, description="Start year for time-specific chunks")
    year_end: Optional[int] = Field(None, description="End year for time-specific chunks")
    related_figures: List[str] = Field(default_factory=list, description="Related figure names")
    tags: List[str] = Field(default_factory=list, description="Descriptive tags")


class CharacterProfileOutput(BaseModel):
    """Complete character profile from the Character Profiler Agent."""

    character_name: str = Field(..., description="Character's name")
    full_name: Optional[str] = Field(None, description="Full formal name")
    title: Optional[str] = Field(None, description="Title or role")
    birth_year: Optional[int] = Field(None, description="Birth year")
    death_year: Optional[int] = Field(None, description="Death year (null if alive)")
    short_bio: str = Field(..., description="2-3 sentence summary")
    role_summary: str = Field(..., description="Brief role description, e.g. 'British PM, 1940-1945'")
    importance_score: float = Field(..., ge=0.0, le=1.0, description="Importance to timeline (0-1)")
    chunks: List[CharacterChunkOutput] = Field(..., description="Profile chunks for vectorization")


# --- Request Models ---


class CustomCharacterCreateRequest(BaseModel):
    """Request model for creating a custom character."""

    name: str = Field(..., min_length=1, max_length=255, description="Character name")
    full_name: Optional[str] = Field(None, max_length=500, description="Full formal name")
    title: Optional[str] = Field(None, max_length=255, description="Title or role")
    user_provided_bio: str = Field(..., min_length=20, max_length=5000, description="Biographical details")
    birth_year: Optional[int] = Field(None, ge=1800, le=2000, description="Birth year")
    death_year: Optional[int] = Field(None, ge=1800, le=2000, description="Death year")

    @field_validator("death_year")
    @classmethod
    def death_after_birth(cls, v: Optional[int], info) -> Optional[int]:
        if v and info.data.get("birth_year") and v < info.data["birth_year"]:
            raise ValueError("death_year must be after birth_year")
        return v


class GenerateProfileRequest(BaseModel):
    """Request model for generating a character profile."""

    cutoff_year: Optional[int] = Field(
        None,
        description="Year cutoff for the profile. Defaults to character's last_known_year.",
    )


class ChatSessionCreateRequest(BaseModel):
    """Request model for creating a chat session."""

    character_year_context: int = Field(..., description="What year the character speaks from")
    session_name: Optional[str] = Field(None, max_length=255, description="User-provided session name")
    profile_id: Optional[str] = Field(None, description="Profile UUID to use for this session")


class ChatMessageRequest(BaseModel):
    """Request model for sending a chat message."""

    message: str = Field(..., min_length=1, max_length=5000, description="User message content")


# --- Response Models ---


class CharacterProfileSummary(BaseModel):
    """Summary of a character profile (used in character list responses)."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Profile UUID")
    cutoff_year: int = Field(..., description="Year cutoff for this profile")
    profile_status: CharacterProfileStatus = Field(..., description="Profile generation status")
    short_bio: Optional[str] = Field(None, description="2-3 sentence summary")
    chunk_count: int = Field(0, description="Number of profile chunks")
    created_at: datetime = Field(..., description="Creation timestamp")


class CharacterProfileResponse(BaseModel):
    """Full profile detail response."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Profile UUID")
    character_id: str = Field(..., description="Character UUID")
    cutoff_year: int = Field(..., description="Year cutoff for this profile")
    profile_status: CharacterProfileStatus = Field(..., description="Profile generation status")
    profile_generated_at: Optional[datetime] = Field(None, description="When profile was generated")
    profile_model_provider: Optional[str] = Field(None, description="LLM provider for profile")
    profile_model_name: Optional[str] = Field(None, description="Model used for profile")
    short_bio: Optional[str] = Field(None, description="2-3 sentence summary")
    role_summary: Optional[str] = Field(None, description="Brief role description")
    importance_score: Optional[float] = Field(None, description="Importance to timeline (0-1)")
    chunk_count: int = Field(0, description="Number of profile chunks")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    chunks: Optional[List["CharacterChunkResponse"]] = Field(None, description="Profile chunks (detail view)")


class CharacterResponse(BaseModel):
    """Response model for a character."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Character UUID")
    timeline_id: str = Field(..., description="Parent timeline UUID")
    name: str = Field(..., description="Character name")
    full_name: Optional[str] = Field(None, description="Full formal name")
    title: Optional[str] = Field(None, description="Title or role")
    character_source: CharacterSource = Field(..., description="How character was created")
    user_provided_bio: Optional[str] = Field(None, description="User-provided biography")
    birth_year: Optional[int] = Field(None, description="Birth year")
    death_year: Optional[int] = Field(None, description="Death year")
    first_appearance_generation: int = Field(..., description="First generation where character appears")
    last_known_year: int = Field(..., description="Latest year with info about character")
    profile_status: CharacterProfileStatus = Field(..., description="Profile generation status")
    profile_generated_at: Optional[datetime] = Field(None, description="When profile was generated")
    profile_model_provider: Optional[str] = Field(None, description="LLM provider for profile")
    profile_model_name: Optional[str] = Field(None, description="Model used for profile")
    short_bio: Optional[str] = Field(None, description="2-3 sentence summary")
    role_summary: Optional[str] = Field(None, description="Brief role description")
    importance_score: Optional[float] = Field(None, description="Importance to timeline (0-1)")
    profiles: List[CharacterProfileSummary] = Field(default_factory=list, description="Date-scoped profiles")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @model_validator(mode="wrap")
    @classmethod
    def _safe_profiles(cls, data: Any, handler: Any) -> "CharacterResponse":
        """Prevent lazy-load of profiles relationship in async context."""
        if hasattr(data, "_sa_instance_state"):
            state = data._sa_instance_state
            if "profiles" not in state.dict:
                # Write directly to instance __dict__ to bypass SQLAlchemy descriptor
                data.__dict__["profiles"] = []
        return handler(data)


class CharacterChunkResponse(BaseModel):
    """Response model for a character profile chunk."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Chunk UUID")
    chunk_type: str = Field(..., description="Type of chunk")
    content: str = Field(..., description="Chunk content")
    year_start: Optional[int] = Field(None, description="Start year")
    year_end: Optional[int] = Field(None, description="End year")
    related_figures: Optional[List[str]] = Field(None, description="Related figures")
    created_at: datetime = Field(..., description="Creation timestamp")


class CharacterDetailResponse(CharacterResponse):
    """Character with optional profile chunks."""

    chunks: Optional[List[CharacterChunkResponse]] = Field(None, description="Profile chunks")


class DetectCharactersResponse(BaseModel):
    """Response from character detection."""

    timeline_id: str = Field(..., description="Timeline UUID")
    detected_figures: List[str] = Field(..., description="Names of detected figures")
    created_characters: int = Field(..., description="Number of new characters created")
    characters: List[CharacterResponse] = Field(..., description="Created character records")


class GenerateProfileResponse(BaseModel):
    """Response from profile generation."""

    message: str = Field(..., description="Status message")
    character_id: str = Field(..., description="Character UUID")
    status: str = Field(..., description="New profile status")
    chunk_count: int = Field(..., description="Number of profile chunks created")
    profile: CharacterProfileResponse = Field(..., description="The generated profile")
    character: CharacterResponse = Field(..., description="Updated character")


class ChatSessionResponse(BaseModel):
    """Response model for a chat session."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Session UUID")
    character_id: str = Field(..., description="Character UUID")
    timeline_id: str = Field(..., description="Timeline UUID")
    character_year_context: int = Field(..., description="Character's knowledge cutoff year")
    session_name: Optional[str] = Field(None, description="User-provided session name")
    profile_id: Optional[str] = Field(None, description="Profile UUID used for this session")
    is_active: bool = Field(True, description="Whether session is active")
    message_count: int = Field(0, description="Total messages in session")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_message_at: Optional[datetime] = Field(None, description="Last message timestamp")


class ChatMessageResponse(BaseModel):
    """Response model for a chat message."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Message UUID")
    session_id: str = Field(..., description="Session UUID")
    role: ChatMessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    model_provider: Optional[str] = Field(None, description="LLM provider (character only)")
    model_name: Optional[str] = Field(None, description="Model used (character only)")
    generation_time_ms: Optional[int] = Field(None, description="Generation time in ms")
    retrieved_chunks: Optional[int] = Field(None, description="RAG chunks used")
    created_at: datetime = Field(..., description="Creation timestamp")


class SendMessageResponse(BaseModel):
    """Response from sending a chat message."""

    user_message: ChatMessageResponse = Field(..., description="The user's message")
    character_response: ChatMessageResponse = Field(..., description="Character's response")


class MessageHistoryResponse(BaseModel):
    """Response for paginated message history."""

    messages: List[ChatMessageResponse] = Field(..., description="Message list")
    total: int = Field(..., description="Total message count")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Page offset")


# ============================================================================
# RIPPLE MAP MODELS
# ============================================================================


class CausalDomain(str, Enum):
    """Domain categories for causal nodes."""

    POLITICAL = "political"
    ECONOMIC = "economic"
    TECHNOLOGICAL = "technological"
    SOCIAL = "social"
    CULTURAL = "cultural"
    MILITARY = "military"


class ConfidenceLevel(str, Enum):
    """How plausible a consequence is."""

    HIGH = "high"
    MEDIUM = "medium"
    SPECULATIVE = "speculative"


class EffectDuration(str, Enum):
    """How long an effect persists."""

    INSTANT = "instant"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    PERMANENT = "permanent"


class CausalRelationship(str, Enum):
    """Type of causal relationship between nodes."""

    CAUSES = "causes"
    ENABLES = "enables"
    PREVENTS = "prevents"
    ACCELERATES = "accelerates"
    WEAKENS = "weakens"
    TRANSFORMS = "transforms"


class EdgeStrength(str, Enum):
    """Strength of causal link."""

    DIRECT = "direct"
    INDIRECT = "indirect"
    SUBTLE = "subtle"


class TimeDelay(str, Enum):
    """Lag between cause and effect."""

    IMMEDIATE = "immediate"
    MONTHS = "months"
    YEARS = "years"
    DECADES = "decades"


class CausalNode(BaseModel):
    """A discrete consequence node in the ripple map."""

    id: str = Field(..., description="Unique node identifier")
    label: str = Field(..., min_length=1, max_length=100, description="Short title (5-10 words)")
    description: str = Field(..., min_length=1, max_length=500, description="2-3 sentence explanation")
    domain: CausalDomain = Field(..., description="Domain category")
    sub_domain: str = Field(..., max_length=50, description="Freeform specialization (e.g. 'trade policy')")
    magnitude: int = Field(..., ge=1, le=5, description="Scale of world impact (1-5)")
    confidence: ConfidenceLevel = Field(..., description="How plausible this consequence is")
    time_offset_years: float = Field(..., ge=0, description="Years after deviation (0.5 = 6 months)")
    duration: EffectDuration = Field(..., description="How long this effect persists")
    affected_regions: List[str] = Field(default_factory=list, description="Geographic areas impacted")
    key_figures: List[str] = Field(default_factory=list, description="Historical figures involved")
    is_deviation_point: bool = Field(False, description="True for the root deviation node")
    source_generation_id: str = Field(..., description="Which generation this node came from")


class CausalEdge(BaseModel):
    """A causal relationship between two nodes."""

    source_node_id: str = Field(..., description="Causing node ID")
    target_node_id: str = Field(..., description="Affected node ID")
    relationship: CausalRelationship = Field(..., description="Type of causal link")
    strength: EdgeStrength = Field(..., description="How strong the causal link is")
    description: str = Field(..., max_length=200, description="Short label explaining the link")
    time_delay: TimeDelay = Field(..., description="Lag between cause and effect")


class RippleMapOutput(BaseModel):
    """Agent output: extracted causal graph from generation report."""

    nodes: List[CausalNode] = Field(..., description="Causal nodes extracted from report")
    edges: List[CausalEdge] = Field(..., description="Causal edges between nodes")


class RippleMapGenerateRequest(BaseModel):
    """Request to generate a ripple map."""

    generation_ids: List[str] = Field(..., min_length=1, description="Generation IDs to include")


class AddGenerationsRequest(BaseModel):
    """Request to add generations to an existing ripple map."""

    generation_ids: List[str] = Field(..., min_length=1, description="New generation IDs to add")


class RippleMapResponse(BaseModel):
    """Full ripple map response."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Ripple map UUID")
    timeline_id: str = Field(..., description="Parent timeline UUID")
    nodes: List[CausalNode] = Field(default_factory=list, description="All causal nodes")
    edges: List[CausalEdge] = Field(default_factory=list, description="All causal edges")
    included_generation_ids: List[str] = Field(default_factory=list, description="Generation IDs in map")
    total_nodes: int = Field(..., description="Count of nodes")
    dominant_domain: Optional[str] = Field(None, description="Domain with most high-magnitude nodes")
    max_ripple_depth: int = Field(0, description="Longest causal chain length")
    model_provider: Optional[str] = Field(None, description="LLM provider used for generation")
    model_name: Optional[str] = Field(None, description="Model used for generation")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")
