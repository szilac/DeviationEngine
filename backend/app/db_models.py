"""
SQLAlchemy database models for DeviationEngine redesigned schema.

This redesigned schema supports:
- Timeline branching (create alternate timelines from alternate timelines)
- Unified generation model (reports + extensions + branches all use 'generations')
- Native translation support (JSON fields for multilingual content)
- Integrated multimedia (images, audio, future video)
- Future-proof audio features
"""

from sqlalchemy import (
    Boolean,
    Column,
    String,
    Integer,
    Float,
    Text,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, backref
from datetime import datetime, timezone
from uuid import uuid4

from app.database import Base


class TimelineDB(Base):
    """
    Timeline metadata with branching support.

    A timeline represents an alternate history scenario. Timelines can branch from
    other timelines, creating a tree structure of alternate realities.

    Attributes:
        id: UUID primary key
        parent_timeline_id: FK to parent timeline (null for root timelines)
        branch_point_year: Year where this timeline diverged from parent
        branch_deviation_description: What changed at the branch point
        root_deviation_date: Original deviation date (inherited from parent or set for root)
        root_deviation_description: Original deviation (inherited or set for root)
        scenario_type: Type of deviation scenario
        created_at: UTC timestamp of creation
        updated_at: UTC timestamp of last update
        generations: All content generations for this timeline
        children: Child timelines branching from this one
        parent: Parent timeline (if this is a branch)
    """

    __tablename__ = "timelines"

    # Identity
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Branching support (NEW)
    parent_timeline_id = Column(
        String(36),
        ForeignKey("timelines.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    branch_point_year = Column(Integer, nullable=True)
    branch_deviation_description = Column(Text, nullable=True)

    # Root deviation (inherited from parent if branched)
    root_deviation_date = Column(String(10), nullable=False, index=True)
    root_deviation_description = Column(Text, nullable=False)
    scenario_type = Column(String(50), nullable=False)

    # Timeline name (short, AI-generated title)
    timeline_name = Column(String(100), nullable=True)

    # Metadata
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    generations = relationship(
        "GenerationDB",
        back_populates="timeline",
        cascade="all, delete-orphan",
        order_by="GenerationDB.generation_order",
    )
    children = relationship(
        "TimelineDB",
        backref=backref("parent", remote_side=[id]),
        cascade="all, delete-orphan",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "scenario_type IN ('local_deviation', 'global_deviation', 'reality_fracture', 'geological_shift', 'external_intervention')",
            name="valid_scenario_type",
        ),
    )

    def __repr__(self) -> str:
        name_display = self.timeline_name or self.root_deviation_description[:50]
        return f"<Timeline {self.id}: {name_display}>"


class GenerationDB(Base):
    """
    Unified content hub for a time period within a timeline.

    Replaces the old ReportDB concept. Each generation represents analysis for a specific
    time period, whether it's the initial generation, an extension, or a branch point.

    Attributes:
        id: UUID primary key
        timeline_id: FK to parent timeline
        generation_order: Sequence number (1, 2, 3...) within timeline
        generation_type: Type of generation (initial, extension, branch_point)
        start_year: Starting year (relative to deviation)
        end_year: Ending year (relative to deviation)
        period_years: Number of years covered

        # Structured report fields (8 sections)
        executive_summary: High-level overview
        political_changes: Government and diplomacy analysis
        conflicts_and_wars: Military conflicts analysis
        economic_impacts: Trade and industry analysis
        social_developments: Cultural and demographic analysis
        technological_shifts: Innovation analysis
        key_figures: Important people
        long_term_implications: Effects at end of period
        report_translations: JSON dict of translated reports (future feature)

        # Narrative fields
        narrative_mode: Type of narrative (none, basic, advanced_omniscient, advanced_custom_pov)
        narrative_prose: Story-like narrative text
        narrative_custom_pov: Custom POV character description
        narrative_translations: JSON dict of translated narratives (future feature)

        # Audio fields (future feature)
        audio_script: Podcast/documentary script
        audio_script_format: Format type (podcast, documentary, news_report)
        audio_url: URL to audio file
        audio_local_path: Local file path
        audio_duration_seconds: Duration in seconds
        audio_voice_model: Voice model identifier
        audio_voice_settings: JSON dict of voice settings
        audio_translations: JSON dict of audio files in different languages

        # Source tracking
        source_skeleton_id: FK to skeleton used for generation (if any)
        source_context: Additional context used for generation

        # Model tracking
        report_model_provider: LLM provider for structured report
        report_model_name: Model name for structured report
        narrative_model_provider: LLM provider for narrative
        narrative_model_name: Model name for narrative
        audio_model_provider: LLM provider for audio script
        audio_model_name: Model name for audio script

        created_at: UTC timestamp of creation
        updated_at: UTC timestamp of last update
        timeline: Relationship to parent timeline
        media: All media for this generation
    """

    __tablename__ = "generations"

    # Identity
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    timeline_id = Column(
        String(36),
        ForeignKey("timelines.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )

    # Ordering
    generation_order = Column(Integer, nullable=False)
    generation_type = Column(String(20), nullable=False)

    # Period
    start_year = Column(Integer, nullable=False)
    end_year = Column(Integer, nullable=False)
    period_years = Column(Integer, nullable=False)

    # === STRUCTURED REPORT (8 sections) ===
    executive_summary = Column(Text, nullable=False)
    political_changes = Column(Text, nullable=False)
    conflicts_and_wars = Column(Text, nullable=False)
    economic_impacts = Column(Text, nullable=False)
    social_developments = Column(Text, nullable=False)
    technological_shifts = Column(Text, nullable=False)
    key_figures = Column(Text, nullable=False)
    long_term_implications = Column(Text, nullable=False)

    # Report translations (future feature)
    report_translations = Column(JSON, nullable=True)

    # === NARRATIVE ===
    narrative_mode = Column(String(30), nullable=True)
    narrative_prose = Column(Text, nullable=True)
    narrative_custom_pov = Column(Text, nullable=True)
    narrative_translations = Column(JSON, nullable=True)

    # === AUDIO (Future Feature) ===
    audio_script = Column(Text, nullable=True)
    audio_script_format = Column(String(20), nullable=True)
    audio_url = Column(Text, nullable=True)
    audio_local_path = Column(Text, nullable=True)
    audio_duration_seconds = Column(Integer, nullable=True)
    audio_voice_model = Column(String(100), nullable=True)
    audio_voice_settings = Column(JSON, nullable=True)
    audio_translations = Column(JSON, nullable=True)

    # === SOURCE TRACKING ===
    source_skeleton_id = Column(
        String(36),
        ForeignKey("skeletons.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    source_context = Column(Text, nullable=True)

    # === MODEL TRACKING ===
    report_model_provider = Column(String(50), nullable=True)
    report_model_name = Column(String(100), nullable=True)
    narrative_model_provider = Column(String(50), nullable=True)
    narrative_model_name = Column(String(100), nullable=True)
    audio_model_provider = Column(String(50), nullable=True)
    audio_model_name = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    timeline = relationship("TimelineDB", back_populates="generations")
    media = relationship(
        "MediaDB", back_populates="generation", cascade="all, delete-orphan"
    )

    # Table constraints
    __table_args__ = (
        UniqueConstraint("timeline_id", "generation_order"),
        CheckConstraint(
            "generation_type IN ('initial', 'extension', 'branch_point')",
            name="valid_generation_type",
        ),
        CheckConstraint(
            "narrative_mode IN ('none', 'basic', 'advanced_omniscient', 'advanced_custom_pov') OR narrative_mode IS NULL",
            name="valid_narrative_mode",
        ),
        CheckConstraint(
            "audio_script_format IN ('podcast', 'documentary', 'news_report') OR audio_script_format IS NULL",
            name="valid_audio_format",
        ),
    )

    def __repr__(self) -> str:
        return f"<Generation {self.id}: Timeline {self.timeline_id} Years {self.start_year}-{self.end_year}>"

    @property
    def period_description(self) -> str:
        """Human-readable description of the time period."""
        if self.start_year == 0:
            return f"Years 0-{self.end_year} ({self.period_years} years)"
        else:
            return f"Years {self.start_year}-{self.end_year} ({self.period_years} years)"


class MediaDB(Base):
    """
    Media attached to generations (images, audio, video).

    Simplified from old schema - removed unused audio/video fields, now links
    to generations instead of reports.

    Attributes:
        id: UUID primary key
        generation_id: FK to parent generation
        media_type: Type of media (image, audio, video)
        media_order: Display order within generation
        prompt_text: AI prompt used for generation
        media_url: URL to media file
        media_local_path: Local file path (optional)
        event_year: Associated year in timeline
        title: User-friendly title
        description: Caption or description
        is_user_added: True if manually added by user
        is_user_modified: True if user edited AI-generated content
        model_provider: LLM provider that generated prompt
        model_name: Model that generated prompt
        created_at: UTC timestamp of creation
        generation: Relationship to parent generation
    """

    __tablename__ = "media"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign key
    generation_id = Column(
        String(36),
        ForeignKey("generations.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )

    # Media metadata
    media_type = Column(String(20), nullable=False, index=True)
    media_order = Column(Integer, nullable=False)

    # Content
    prompt_text = Column(Text, nullable=True)
    media_url = Column(Text, nullable=False)
    media_local_path = Column(Text, nullable=True)

    # Timeline context
    event_year = Column(Integer, nullable=True)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Tracking
    is_user_added = Column(Integer, nullable=False, default=0)
    is_user_modified = Column(Integer, nullable=False, default=0)

    # Model metadata
    model_provider = Column(String(50), nullable=True)
    model_name = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Relationships
    generation = relationship("GenerationDB", back_populates="media")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "media_type IN ('image', 'audio', 'video')",
            name="valid_media_type",
        ),
    )

    def __repr__(self) -> str:
        return f"<Media {self.id}: {self.media_type} for Generation {self.generation_id}>"


class SkeletonDB(Base):
    """
    Draft/editable event outlines with type support.

    Renamed from TimelineSkeletonDB. Supports both timeline and generation drafts.

    Attributes:
        id: UUID primary key
        timeline_id: FK to associated timeline (for timeline drafts)
        generation_id: FK to associated generation (for extension drafts)
        skeleton_type: Type of skeleton (timeline_draft, extension_draft, branch_draft)

        # For timeline drafts
        deviation_date: Date of deviation (YYYY-MM-DD)
        deviation_description: What changed
        scenario_type: Type of scenario

        # For extension/branch drafts
        parent_timeline_id: FK to parent timeline
        extension_start_year: Starting year for extension
        extension_end_year: Ending year for extension
        branch_point_year: Year where branch diverges (for branches)
        branch_deviation_description: What changed at branch point

        status: Current status (pending, editing, approved, generated)
        model_provider: LLM provider used
        model_name: Model used
        generated_at: UTC timestamp of generation
        approved_at: UTC timestamp when approved
        created_at: UTC timestamp of creation
        updated_at: UTC timestamp of last update
        events: Skeleton events
        timeline: Associated timeline (if linked)
        generation: Associated generation (if linked)
    """

    __tablename__ = "skeletons"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Association (nullable until content is generated)
    timeline_id = Column(
        String(36),
        ForeignKey("timelines.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    generation_id = Column(
        String(36),
        ForeignKey("generations.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )

    # Type
    skeleton_type = Column(String(20), nullable=False, index=True)

    # For timeline drafts
    deviation_date = Column(String(10), nullable=True)
    deviation_description = Column(Text, nullable=True)
    scenario_type = Column(String(50), nullable=True)

    # For extension/branch drafts
    parent_timeline_id = Column(
        String(36),
        ForeignKey("timelines.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=True,
    )
    extension_start_year = Column(Integer, nullable=True)
    extension_end_year = Column(Integer, nullable=True)
    branch_point_year = Column(Integer, nullable=True)
    branch_deviation_description = Column(Text, nullable=True)

    # Status tracking
    status = Column(String(20), nullable=False, default="pending", index=True)

    # Model metadata
    model_provider = Column(String(50), nullable=True)
    model_name = Column(String(100), nullable=True)

    # Timestamps
    generated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    events = relationship(
        "SkeletonEventDB",
        back_populates="skeleton",
        cascade="all, delete-orphan",
        order_by="SkeletonEventDB.event_order",
    )
    timeline = relationship(
        "TimelineDB", foreign_keys=[timeline_id], backref="skeletons"
    )
    generation = relationship(
        "GenerationDB", foreign_keys=[generation_id], backref="skeletons"
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "skeleton_type IN ('timeline_draft', 'extension_draft', 'branch_draft')",
            name="valid_skeleton_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'editing', 'approved', 'generated')",
            name="valid_skeleton_status",
        ),
    )

    def __repr__(self) -> str:
        desc = self.deviation_description or self.branch_deviation_description or "Unknown"
        return f"<Skeleton {self.id}: {desc[:30]}... [{self.status}]>"


class SkeletonEventDB(Base):
    """
    Individual events within a skeleton.

    No changes from old schema - still works the same way.

    Attributes:
        id: UUID primary key
        skeleton_id: FK to parent skeleton
        event_date: Date of event (YYYY-MM-DD)
        event_year: Year relative to deviation
        location: Geographic location
        description: Brief description
        event_order: Display order
        is_user_added: True if manually added
        is_user_modified: True if edited
        created_at: UTC timestamp of creation
        updated_at: UTC timestamp of last update
        skeleton: Relationship to parent skeleton
    """

    __tablename__ = "skeleton_events"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign key
    skeleton_id = Column(
        String(36),
        ForeignKey("skeletons.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )

    # Event details
    event_date = Column(String(10), nullable=False)
    event_year = Column(Integer, nullable=False)
    location = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)

    # Ordering and tracking
    event_order = Column(Integer, nullable=False)
    is_user_added = Column(Integer, nullable=False, default=0)
    is_user_modified = Column(Integer, nullable=False, default=0)

    # Timestamps
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    skeleton = relationship("SkeletonDB", back_populates="events")

    def __repr__(self) -> str:
        return f"<SkeletonEvent {self.id}: {self.event_date} at {self.location}>"


class ImagePromptSkeletonDB(Base):
    """
    Draft image prompt skeletons for review-before-generate workflow.

    Updated to reference generations instead of reports.

    Attributes:
        id: UUID primary key
        timeline_id: FK to parent timeline
        generation_id: FK to specific generation
        status: Current status (pending, editing, approved, generating, completed)
        num_images: Number of images to generate
        focus_areas: JSON list of focus areas
        prompts_json: JSON storage of prompt objects
        model_provider: LLM provider used
        model_name: Model used
        created_at: UTC timestamp of creation
        approved_at: UTC timestamp when approved
        completed_at: UTC timestamp when completed
        updated_at: UTC timestamp of last update
        timeline: Relationship to timeline
        generation: Relationship to generation
    """

    __tablename__ = "image_prompt_skeletons"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign keys
    timeline_id = Column(
        String(36),
        ForeignKey("timelines.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    generation_id = Column(
        String(36),
        ForeignKey("generations.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )

    # Status tracking
    status = Column(String(20), nullable=False, default="pending", index=True)

    # Configuration
    num_images = Column(Integer, nullable=False)
    focus_areas = Column(JSON, nullable=True)

    # Prompts storage
    prompts_json = Column(JSON, nullable=True)

    # Model metadata
    model_provider = Column(String(50), nullable=True)
    model_name = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    approved_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    timeline = relationship("TimelineDB", backref="image_prompt_skeletons")
    generation = relationship("GenerationDB", backref="image_prompt_skeletons")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'editing', 'approved', 'generating', 'completed')",
            name="valid_image_prompt_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<ImagePromptSkeleton {self.id}: {self.num_images} images [{self.status}]>"


class LLMConfigDB(Base):
    """
    Singleton table for global LLM configuration.

    No changes from old schema.

    Attributes:
        id: Primary key (always 1)
        provider: LLM provider (google, openrouter, ollama)
        model_name: Specific model identifier
        api_key_google: Google API key (optional)
        api_key_openrouter: OpenRouter API key (optional)
        ollama_base_url: Ollama server URL (optional)
        created_at: UTC timestamp of creation
        updated_at: UTC timestamp of last update
    """

    __tablename__ = "llm_config"

    # Primary key with singleton constraint
    id = Column(Integer, primary_key=True)

    # Provider configuration
    provider = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)

    # API keys and URLs
    api_key_google = Column(Text, nullable=True)
    api_key_openrouter = Column(Text, nullable=True)
    ollama_base_url = Column(Text, nullable=True)

    # Metadata
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint("id = 1", name="singleton_constraint"),
        CheckConstraint(
            "provider IN ('google', 'openrouter', 'ollama')",
            name="valid_provider",
        ),
    )

    def __repr__(self) -> str:
        return f"<LLMConfig provider={self.provider} model={self.model_name}>"


class AgentLLMConfigDB(Base):
    """
    Per-agent LLM configuration overrides.

    No changes from old schema.

    Attributes:
        id: Primary key
        agent_type: Agent identifier
        provider: LLM provider
        model_name: Model identifier
        api_key_google: Google API key override (optional)
        api_key_openrouter: OpenRouter API key override (optional)
        ollama_base_url: Ollama URL override (optional)
        max_tokens: Max tokens override (optional)
        temperature: Temperature override (optional)
        enabled: Enable/disable flag
        created_at: UTC timestamp of creation
        updated_at: UTC timestamp of last update
    """

    __tablename__ = "agent_llm_configs"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Agent identification
    agent_type = Column(String(50), nullable=False, unique=True, index=True)

    # Provider configuration
    provider = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)

    # Optional overrides
    api_key_google = Column(Text, nullable=True)
    api_key_openrouter = Column(Text, nullable=True)
    ollama_base_url = Column(Text, nullable=True)

    # Model settings overrides
    max_tokens = Column(Integer, nullable=True)
    temperature = Column(String(10), nullable=True)

    # Enable/disable
    enabled = Column(Integer, nullable=False, default=1)

    # Metadata
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "agent_type IN ('historian', 'storyteller', 'skeleton', 'skeleton_historian', 'illustrator', 'script_writer', 'translator', 'character_profiler', 'impersonator', 'ripple_analyst')",
            name="valid_agent_type",
        ),
        CheckConstraint(
            "provider IN ('google', 'openrouter', 'ollama')",
            name="valid_agent_provider",
        ),
        CheckConstraint("enabled IN (0, 1)", name="valid_enabled"),
    )

    def __repr__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"<AgentLLMConfig {self.agent_type}: {self.provider}/{self.model_name} [{status}]>"


class TranslationConfigDB(Base):
    """
    Singleton table for translation service configuration.

    Follows the same singleton pattern as LLMConfigDB.

    Attributes:
        id: Primary key (always 1)
        api_key: DeepL API authentication key
        api_tier: API tier ('free' or 'pro')
        enabled: Whether translation service is active
        created_at: UTC timestamp of creation
        updated_at: UTC timestamp of last update
    """

    __tablename__ = "translation_config"

    # Primary key with singleton constraint
    id = Column(Integer, primary_key=True)

    # API configuration
    api_key = Column(Text, nullable=False)
    api_tier = Column(String(20), nullable=False, default="free")

    # Enable/disable
    enabled = Column(Integer, nullable=False, default=1)

    # Metadata
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint("id = 1", name="translation_singleton_constraint"),
        CheckConstraint(
            "api_tier IN ('free', 'pro')",
            name="valid_translation_tier",
        ),
        CheckConstraint("enabled IN (0, 1)", name="valid_translation_enabled"),
    )

    def __repr__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"<TranslationConfig tier={self.api_tier} [{status}]>"


class TranslationUsageDB(Base):
    """
    Monthly translation usage tracking table.

    Tracks character usage against DeepL free tier limits (500k chars/month).

    Attributes:
        id: Primary key
        year_month: Month in YYYY-MM format (unique)
        characters_used: Total characters translated this month
        api_calls: Number of API calls made this month
        characters_limit: Monthly character limit
        created_at: UTC timestamp of creation
        updated_at: UTC timestamp of last update
    """

    __tablename__ = "translation_usage"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Period tracking
    year_month = Column(String(7), nullable=False, unique=True, index=True)

    # Usage statistics
    characters_used = Column(Integer, nullable=False, default=0)
    api_calls = Column(Integer, nullable=False, default=0)
    characters_limit = Column(Integer, nullable=False, default=500000)

    # Metadata
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        percentage = (self.characters_used / self.characters_limit * 100) if self.characters_limit > 0 else 0
        return f"<TranslationUsage {self.year_month}: {self.characters_used:,}/{self.characters_limit:,} chars ({percentage:.1f}%)>"


# ============================================================================
# AUDIO CONTENT GENERATION MODELS
# ============================================================================


class ScriptPresetDB(Base):
    """
    Script preset configuration table for audio generation.

    Stores both system (built-in) and user-created custom presets for
    audio script generation. Presets define the style, tone, pacing, and
    voice configuration for generated scripts.

    Attributes:
        id: UUID primary key
        name: Preset display name (e.g., "Documentary Narration")
        description: User-facing description
        script_type: Type of script (podcast, documentary, news_report, storytelling, interview)
        tone: Tone setting (formal, casual, dramatic, neutral, humorous, authoritative)
        pacing: Pacing setting (fast, medium, slow, varied)
        voice_count: Number of voices (1 or 2)
        voice_roles: JSON dict of voice roles (e.g., {"primary": "narrator"})
        style_instructions: Detailed instructions for the Script Writer Agent
        prompt_template_name: Jinja2 template filename for this preset
        is_system: 1 for built-in presets, 0 for user-created
        is_active: 1 for active, 0 for soft-deleted
        created_at: UTC timestamp of creation
        updated_at: UTC timestamp of last update
        scripts: Related audio scripts using this preset
    """

    __tablename__ = "script_presets"

    # Identity
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Preset metadata
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)

    # Style configuration
    script_type = Column(String(20), nullable=False, index=True)
    tone = Column(String(20), nullable=False)
    pacing = Column(String(20), nullable=False)

    # Voice configuration
    voice_count = Column(Integer, nullable=False)
    voice_roles = Column(JSON, nullable=True)

    # Generation instructions
    style_instructions = Column(Text, nullable=False)
    prompt_template_name = Column(String(100), nullable=False)

    # System vs custom
    is_system = Column(Integer, default=0, index=True)
    is_active = Column(Integer, default=1, index=True)

    # Metadata
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    scripts = relationship("AudioScriptDB", back_populates="preset")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "script_type IN ('podcast', 'documentary', 'news_report', 'storytelling', 'interview')",
            name="valid_script_type",
        ),
        CheckConstraint(
            "tone IN ('formal', 'casual', 'dramatic', 'neutral', 'humorous', 'authoritative')",
            name="valid_tone",
        ),
        CheckConstraint(
            "pacing IN ('fast', 'medium', 'slow', 'varied')", name="valid_pacing"
        ),
        CheckConstraint("voice_count IN (1, 2)", name="valid_voice_count"),
        CheckConstraint("is_system IN (0, 1)", name="valid_is_system"),
        CheckConstraint("is_active IN (0, 1)", name="valid_is_active"),
    )

    def __repr__(self) -> str:
        preset_type = "System" if self.is_system else "Custom"
        status = "Active" if self.is_active else "Inactive"
        return f"<ScriptPreset {self.name} [{preset_type}, {status}]>"


class AudioScriptDB(Base):
    """
    Audio script table storing generated scripts with metadata.

    Scripts are generated from generation content using Script Writer Agent.
    They can be edited before approval and audio generation.

    Attributes:
        id: UUID primary key
        generation_ids: JSON array of generation UUIDs used as source
        title: Script title
        description: Optional script description
        preset_id: FK to script preset used
        custom_instructions: User-provided custom instructions
        script_content: Markdown script with speaker markers
        script_structure: 'single_voice' or 'dual_voice'
        word_count: Total word count
        estimated_duration_seconds: Estimated audio duration
        status: Workflow status (draft, approved, audio_generated)
        model_provider: LLM provider used for generation
        model_name: Model used for generation
        created_at: UTC timestamp of creation
        approved_at: UTC timestamp when approved
        updated_at: UTC timestamp of last update
        preset: Relationship to preset
        translations: Related translations
        audio_files: Related audio files
    """

    __tablename__ = "audio_scripts"

    # Identity
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Association with generations
    generation_ids = Column(JSON, nullable=False)

    # Metadata
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Preset and customization
    preset_id = Column(
        String(36),
        ForeignKey("script_presets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    custom_instructions = Column(Text, nullable=True)

    # Generated content
    script_content = Column(Text, nullable=False)
    script_structure = Column(String(20), nullable=False)

    # Metrics
    word_count = Column(Integer, nullable=False)
    estimated_duration_seconds = Column(Integer, nullable=False)

    # Status workflow
    status = Column(String(20), nullable=False, default="draft", index=True)

    # Model tracking
    model_provider = Column(String(50), nullable=True)
    model_name = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )
    approved_at = Column(DateTime, nullable=True)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    preset = relationship("ScriptPresetDB", back_populates="scripts")
    translations = relationship(
        "ScriptTranslationDB", back_populates="script", cascade="all, delete-orphan"
    )
    audio_files = relationship(
        "AudioFileDB", back_populates="script", cascade="all, delete-orphan"
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "script_structure IN ('single_voice', 'dual_voice')",
            name="valid_script_structure",
        ),
        CheckConstraint(
            "status IN ('draft', 'approved', 'audio_generated')",
            name="valid_script_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<AudioScript {self.id}: '{self.title}' [{self.status}]>"


class ScriptTranslationDB(Base):
    """
    Script translation table storing translated versions of scripts.

    Translations are generated using LLM translation with the structure
    and speaker markers preserved from the original script.

    Attributes:
        id: UUID primary key
        script_id: FK to parent script
        language_code: ISO 639-1 language code (e.g., 'es', 'fr')
        language_name: Human-readable language name
        translated_content: Markdown script with speaker markers in target language
        translation_method: Translation method used ('deepl' or 'llm')
        is_human_translated: 0 for AI, 1 for human translation
        translation_quality_score: Optional quality score (0-1)
        translation_model_provider: LLM provider for translation
        translation_model_name: Model for translation
        created_at: UTC timestamp of creation
        updated_at: UTC timestamp of last update
        script: Relationship to parent script
        audio_files: Related audio files generated from this translation
    """

    __tablename__ = "script_translations"

    # Identity
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    script_id = Column(
        String(36),
        ForeignKey("audio_scripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Language
    language_code = Column(String(2), nullable=False, index=True)
    language_name = Column(String(50), nullable=False)

    # Translated content
    translated_content = Column(Text, nullable=False)
    word_count = Column(Integer, nullable=True)

    # Translation method
    translation_method = Column(String(10), default='deepl', nullable=False)  # 'deepl' or 'llm'
    is_human_translated = Column(Integer, default=0)
    translation_quality_score = Column(Integer, nullable=True)

    # Model tracking (if AI-translated)
    translation_model_provider = Column(String(50), nullable=True)
    translation_model_name = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    script = relationship("AudioScriptDB", back_populates="translations")
    audio_files = relationship(
        "AudioFileDB", back_populates="translation", cascade="all, delete-orphan"
    )

    # Table constraints
    __table_args__ = (
        UniqueConstraint("script_id", "language_code", name="unique_script_language"),
        CheckConstraint("is_human_translated IN (0, 1)", name="valid_is_human"),
    )

    def __repr__(self) -> str:
        trans_type = "Human" if self.is_human_translated else "AI"
        return f"<ScriptTranslation {self.id}: {self.language_name} [{trans_type}]>"


class AudioFileDB(Base):
    """
    Audio file table storing generated audio with metadata.

    Audio files are generated from approved scripts (original or translated)
    using Google TTS (gemini-2.5-flash-preview-tts).

    Attributes:
        id: UUID primary key
        script_id: FK to parent script
        source_type: 'original' or 'translation'
        script_translation_id: FK to translation (if source_type='translation')
        language_code: Language of the audio (e.g., 'en', 'es')
        audio_local_path: Absolute path on local filesystem
        audio_url: Relative path for frontend access
        file_size_bytes: Size of audio file in bytes
        duration_seconds: Audio duration in seconds
        format: Audio format ('mp3', 'wav', 'pcm')
        sample_rate: Sample rate (e.g., 24000 Hz)
        bit_rate: Bit rate (e.g., 128000)
        voice_model: Voice model used (e.g., 'gemini-2.5-flash-preview-tts')
        voice_settings: JSON dict of voice settings
        voice_ids: JSON dict of voice IDs (e.g., {"narrator": "Kore"})
        model_provider: TTS provider
        model_name: TTS model name
        generated_at: UTC timestamp of generation
        script: Relationship to parent script
        translation: Relationship to translation (if applicable)
    """

    __tablename__ = "audio_files"

    # Identity
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    script_id = Column(
        String(36),
        ForeignKey("audio_scripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Source (original or translation)
    source_type = Column(String(20), nullable=False)
    script_translation_id = Column(
        String(36),
        ForeignKey("script_translations.id", ondelete="CASCADE"),
        nullable=True,
    )
    language_code = Column(String(2), nullable=False, index=True)

    # File information
    audio_local_path = Column(Text, nullable=False)
    audio_url = Column(Text, nullable=True)
    file_size_bytes = Column(Integer, nullable=False)

    # Audio metadata
    duration_seconds = Column(Integer, nullable=False)
    format = Column(String(10), nullable=False)
    sample_rate = Column(Integer, nullable=True)
    bit_rate = Column(Integer, nullable=True)

    # Voice configuration
    voice_model = Column(String(100), nullable=False)
    voice_settings = Column(JSON, nullable=True)
    voice_ids = Column(JSON, nullable=True)

    # Model tracking
    model_provider = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)

    # Timestamps
    generated_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )

    # Relationships
    script = relationship("AudioScriptDB", back_populates="audio_files")
    translation = relationship("ScriptTranslationDB", back_populates="audio_files")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('original', 'translation')", name="valid_source_type"
        ),
        CheckConstraint(
            "(source_type = 'original' AND script_translation_id IS NULL) OR "
            "(source_type = 'translation' AND script_translation_id IS NOT NULL)",
            name="valid_source_translation_relationship",
        ),
    )

    def __repr__(self) -> str:
        size_mb = self.file_size_bytes / 1_000_000
        return f"<AudioFile {self.id}: {self.language_code} [{self.format}, {size_mb:.1f}MB]>"


class VectorStoreIndexDB(Base):
    """
    Track indexed content in vector store for cache management.

    This table maintains a record of what content has been indexed into the
    ChromaDB vector store, enabling incremental indexing and cache invalidation.

    Attributes:
        id: UUID primary key
        content_type: Type of content ('ground_truth' | 'report' | 'narrative')
        content_id: ID of the content (generation_id for reports/narratives, filename for ground_truth)
        timeline_id: FK to timeline (null for ground_truth)
        indexed_at: UTC timestamp when content was indexed
        chunk_count: Number of chunks created from this content
        embedding_model: Name of the embedding model used
        source_hash: MD5 hash of source content for change detection
    """

    __tablename__ = "vector_store_index"

    # Identity
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Content tracking
    content_type = Column(String(20), nullable=False, index=True)
    content_id = Column(String(255), nullable=True, index=True)
    timeline_id = Column(String(36), nullable=True, index=True)

    # Indexing metadata
    indexed_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )
    chunk_count = Column(Integer, nullable=False)
    embedding_model = Column(String(100), nullable=False, default="all-MiniLM-L6-v2")
    source_hash = Column(String(32), nullable=False)

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "content_type IN ('ground_truth', 'report', 'narrative')",
            name="valid_content_type",
        ),
    )

    def __repr__(self) -> str:
        return f"<VectorStoreIndex {self.content_type}:{self.content_id} [{self.chunk_count} chunks]>"


# ============================================================================
# HISTORICAL FIGURE CHAT MODELS
# ============================================================================


class CharacterDB(Base):
    """
    Historical figure character for chat interactions.

    Characters are extracted from timeline content (auto-detected via NER/LLM)
    or created by users with custom biographical details. Enriched with
    AI-generated profiles for in-character conversations.
    """

    __tablename__ = "characters"

    # Identity
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign key
    timeline_id = Column(
        String(36),
        ForeignKey("timelines.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )

    # Character identity
    name = Column(String(255), nullable=False)
    full_name = Column(String(500), nullable=True)
    title = Column(String(255), nullable=True)

    # Character source
    character_source = Column(String(20), nullable=False, default="auto_detected")
    user_provided_bio = Column(Text, nullable=True)

    # Timeline context
    birth_year = Column(Integer, nullable=True)
    death_year = Column(Integer, nullable=True)
    first_appearance_generation = Column(Integer, nullable=False, default=1)
    last_known_year = Column(Integer, nullable=False, default=1900)

    # Profile status
    profile_status = Column(String(20), nullable=False, default="pending", index=True)
    profile_generated_at = Column(DateTime, nullable=True)
    profile_model_provider = Column(String(50), nullable=True)
    profile_model_name = Column(String(100), nullable=True)

    # Summary fields (for quick display)
    short_bio = Column(Text, nullable=True)
    role_summary = Column(String(500), nullable=True)
    importance_score = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    timeline = relationship("TimelineDB", backref="characters")
    chat_sessions = relationship(
        "ChatSessionDB",
        back_populates="character",
        cascade="all, delete-orphan",
    )
    character_chunks = relationship(
        "CharacterChunkDB",
        back_populates="character",
        cascade="all, delete-orphan",
    )
    profiles = relationship(
        "CharacterProfileDB",
        back_populates="character",
        cascade="all, delete-orphan",
        order_by="CharacterProfileDB.cutoff_year",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "profile_status IN ('pending', 'generating', 'ready', 'error')",
            name="valid_character_profile_status",
        ),
        CheckConstraint(
            "character_source IN ('auto_detected', 'user_created')",
            name="valid_character_source",
        ),
        Index("idx_character_timeline_name", "timeline_id", "name"),
    )

    def __repr__(self) -> str:
        return f"<Character {self.id}: {self.name} [{self.profile_status}]>"


class CharacterProfileDB(Base):
    """
    Date-scoped character profile.

    Each profile represents a character's persona at a specific cutoff year,
    allowing the same character to be chatted with at different points in time.
    A character can have multiple profiles (one per cutoff_year).
    """

    __tablename__ = "character_profiles"

    # Identity
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign key
    character_id = Column(
        String(36),
        ForeignKey("characters.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )

    # Profile scope
    cutoff_year = Column(Integer, nullable=False)

    # Profile status
    profile_status = Column(String(20), nullable=False, default="pending", index=True)
    profile_generated_at = Column(DateTime, nullable=True)
    profile_model_provider = Column(String(50), nullable=True)
    profile_model_name = Column(String(100), nullable=True)

    # Summary fields
    short_bio = Column(Text, nullable=True)
    role_summary = Column(String(500), nullable=True)
    importance_score = Column(Float, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    character = relationship("CharacterDB", back_populates="profiles")
    chunks = relationship(
        "CharacterChunkDB",
        back_populates="profile",
        cascade="all, delete-orphan",
    )
    chat_sessions = relationship(
        "ChatSessionDB",
        back_populates="profile",
    )

    # Table constraints
    __table_args__ = (
        UniqueConstraint("character_id", "cutoff_year", name="uq_character_cutoff_year"),
        CheckConstraint(
            "profile_status IN ('pending', 'generating', 'ready', 'error')",
            name="valid_profile_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<CharacterProfile {self.id}: character={self.character_id} year={self.cutoff_year} [{self.profile_status}]>"


class CharacterChunkDB(Base):
    """
    Individual chunk of character profile stored in vector DB.

    Each chunk represents one aspect of a character's profile
    (biography, personality, relationships, etc.) for RAG retrieval.
    """

    __tablename__ = "character_chunks"

    # Identity
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign keys
    character_id = Column(
        String(36),
        ForeignKey("characters.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id = Column(
        String(36),
        ForeignKey("character_profiles.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )

    # Chunk metadata
    chunk_type = Column(String(30), nullable=False)
    content = Column(Text, nullable=False)
    year_start = Column(Integer, nullable=True)
    year_end = Column(Integer, nullable=True)

    # Vector store reference
    vector_chunk_id = Column(String(255), nullable=True)
    source_generation_id = Column(String(36), nullable=True)
    related_figures = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    character = relationship("CharacterDB", back_populates="character_chunks")
    profile = relationship("CharacterProfileDB", back_populates="chunks")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "chunk_type IN ('biography', 'personality', 'relationships', "
            "'beliefs', 'speaking_style', 'event_involvement')",
            name="valid_chunk_type",
        ),
        Index("idx_character_chunk_type", "character_id", "chunk_type"),
    )

    def __repr__(self) -> str:
        return f"<CharacterChunk {self.id}: {self.chunk_type}>"


class ChatSessionDB(Base):
    """
    Chat session between a user and a historical figure character.

    Each session has a character_year_context that defines what year the
    character is "speaking from", enforcing temporal knowledge boundaries.
    """

    __tablename__ = "chat_sessions"

    # Identity
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign keys
    character_id = Column(
        String(36),
        ForeignKey("characters.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    timeline_id = Column(
        String(36),
        ForeignKey("timelines.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id = Column(
        String(36),
        ForeignKey("character_profiles.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )

    # Session metadata
    session_name = Column(String(255), nullable=True)
    character_year_context = Column(Integer, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, index=True)
    message_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_message_at = Column(DateTime, nullable=True)

    # Relationships
    character = relationship("CharacterDB", back_populates="chat_sessions")
    profile = relationship("CharacterProfileDB", back_populates="chat_sessions")
    messages = relationship(
        "ChatMessageDB",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessageDB.created_at",
    )

    def __repr__(self) -> str:
        return f"<ChatSession {self.id}: character={self.character_id} year={self.character_year_context}>"


class ChatMessageDB(Base):
    """
    Individual message in a chat session.

    Attributes:
        id: UUID primary key
        session_id: FK to chat session
        role: Message role (user, character)
        content: Message text content
        model_provider: LLM provider (for character messages)
        model_name: Model used (for character messages)
        generation_time_ms: Response generation time in milliseconds
        retrieved_chunks: Number of RAG chunks retrieved for context
        created_at: UTC timestamp of creation
        session: Relationship to parent session
    """

    __tablename__ = "chat_messages"

    # Identity
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign key
    session_id = Column(
        String(36),
        ForeignKey("chat_sessions.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )

    # Message content
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)

    # Model metadata (for character responses)
    model_provider = Column(String(50), nullable=True)
    model_name = Column(String(100), nullable=True)
    generation_time_ms = Column(Integer, nullable=True)
    retrieved_chunks = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Relationships
    session = relationship("ChatSessionDB", back_populates="messages")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'character')",
            name="valid_chat_message_role",
        ),
    )

    def __repr__(self) -> str:
        preview = self.content[:30] if self.content else ""
        return f"<ChatMessage {self.id}: {self.role} '{preview}...'>"


class RippleMapDB(Base):
    """
    Causal web visualization data for a timeline.

    Stores the ripple map as JSON blobs of nodes and edges.
    One ripple map per timeline, grows incrementally as generations are added.

    Attributes:
        id: UUID primary key
        timeline_id: FK to parent timeline (unique - one map per timeline)
        nodes: JSON list of CausalNode objects
        edges: JSON list of CausalEdge objects
        included_generation_ids: JSON list of generation IDs included in map
        total_nodes: Count of nodes for quick reference
        dominant_domain: Domain with most high-magnitude nodes
        max_ripple_depth: Longest causal chain length
        model_provider: LLM provider used for generation
        model_name: Model used for generation
        created_at: UTC timestamp of creation
        updated_at: UTC timestamp of last modification
    """

    __tablename__ = "ripple_maps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    timeline_id = Column(
        String(36),
        ForeignKey("timelines.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Graph data (JSON blobs)
    nodes = Column(JSON, nullable=False, default=list)
    edges = Column(JSON, nullable=False, default=list)
    included_generation_ids = Column(JSON, nullable=False, default=list)

    # Summary fields
    total_nodes = Column(Integer, nullable=False, default=0)
    dominant_domain = Column(String(20), nullable=True)
    max_ripple_depth = Column(Integer, nullable=False, default=0)

    # Model tracking
    model_provider = Column(String(50), nullable=True)
    model_name = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    timeline = relationship("TimelineDB", backref=backref("ripple_map", uselist=False))

    def __repr__(self) -> str:
        return (
            f"<RippleMapDB(id={self.id}, timeline_id={self.timeline_id}, "
            f"total_nodes={self.total_nodes})>"
        )


class NotebookLMJobDB(Base):
    """
    Tracks async NotebookLM studio content generation jobs.

    A job represents one end-to-end pipeline run: export → create notebook →
    upload sources → trigger generation → poll → download → serve.

    content_type is 'audio' now; future values: 'video', 'slides', etc.
    Once completed, audio_local_path and audio_url hold the result.
    """

    __tablename__ = "notebooklm_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    timeline_id = Column(
        String(36),
        ForeignKey("timelines.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    generation_ids = Column(JSON, nullable=False)

    # NotebookLM references (populated as pipeline progresses)
    notebook_id = Column(String(100), nullable=True)
    artifact_id = Column(String(36), nullable=True)

    # Generation configuration
    content_type = Column(String(20), nullable=False, default="audio")
    nlm_format = Column(String(20), nullable=False)
    nlm_length = Column(String(20), nullable=False)
    nlm_focus = Column(Text, nullable=True)
    language_code = Column(String(10), nullable=False, default="en")

    # Job lifecycle
    status = Column(String(20), nullable=False, default="pending", index=True)
    error_message = Column(Text, nullable=True)

    # Output (set when completed) — stored directly; AudioFileDB.script_id is NOT NULL
    audio_local_path = Column(String(500), nullable=True)
    audio_url = Column(String(200), nullable=True)

    # Timestamps
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        CheckConstraint("content_type IN ('audio')", name="valid_nlm_content_type"),
        CheckConstraint(
            "nlm_format IN ('deep_dive', 'brief', 'critique', 'debate')",
            name="valid_nlm_format",
        ),
        CheckConstraint("nlm_length IN ('short', 'default', 'long')", name="valid_nlm_length"),
        CheckConstraint(
            "status IN ('pending', 'creating', 'uploading', 'generating', 'polling', 'completed', 'failed')",
            name="valid_nlm_job_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<NotebookLMJob {self.id}: {self.content_type}/{self.nlm_format} [{self.status}]>"


class TimelineNovellaDB(Base):
    """
    Timeline-level novella generated from multiple generations.

    Attributes:
        id: UUID primary key
        timeline_id: FK to parent timeline
        series_id: shared UUID for all members of a series (null = standalone)
        series_order: 1-based position within the series
        generation_ids: ordered JSON array of source generation UUIDs
        title: AI-generated title
        content: 2,000-5,000 words of prose
        focus_instructions: optional user free-text
        model_provider: LLM provider used
        model_name: model used
        created_at: UTC timestamp
    """

    __tablename__ = "timeline_novellas"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    timeline_id = Column(
        String(36),
        ForeignKey("timelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    series_id = Column(String(36), nullable=True, index=True)
    series_order = Column(Integer, nullable=False, default=1)
    generation_ids = Column(JSON, nullable=False)
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    focus_instructions = Column(Text, nullable=True)
    model_provider = Column(String(50), nullable=False)
    model_name = Column(String(100), nullable=False)
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )

    timeline = relationship("TimelineDB", backref=backref("novellas", lazy="dynamic"))

    def __repr__(self) -> str:
        return f"<TimelineNovella {self.id}: '{self.title}' (series={self.series_id})>"
