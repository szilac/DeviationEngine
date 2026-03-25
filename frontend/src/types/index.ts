/**
 * TypeScript type definitions for multi-report Deviation Engine API.
 *
 * These types match the updated backend Pydantic models exactly to ensure
 * type safety across the frontend-backend boundary.
 */

/**
 * Types of historical deviation scenarios.
 */
export const ScenarioType = {
  LOCAL_DEVIATION: 'local_deviation',
  GLOBAL_DEVIATION: 'global_deviation',
  REALITY_FRACTURE: 'reality_fracture',
  GEOLOGICAL_SHIFT: 'geological_shift',
  EXTERNAL_INTERVENTION: 'external_intervention',
} as const;

export type ScenarioType = typeof ScenarioType[keyof typeof ScenarioType];

/**
 * Narrative generation modes.
 */
export const NarrativeMode = {
  NONE: 'none',
  BASIC: 'basic',
  ADVANCED_OMNISCIENT: 'advanced_omniscient',
  ADVANCED_CUSTOM_POV: 'advanced_custom_pov',
} as const;

export type NarrativeMode = typeof NarrativeMode[keyof typeof NarrativeMode];

/**
 * Generation types for timeline content.
 */
export const GenerationType = {
  INITIAL: 'initial',
  EXTENSION: 'extension',
  BRANCH_POINT: 'branch_point',
} as const;

export type GenerationType = typeof GenerationType[keyof typeof GenerationType];

/**
 * Request payload for generating an alternate history timeline.
 *
 * Matches backend TimelineCreationRequest model.
 */
export interface TimelineCreationRequest {
  /** Date of the historical deviation point (YYYY-MM-DD format) */
  deviation_date: string;

  /** Description of what changed in history (10-500 characters) */
  deviation_description: string;

  /** Number of years to simulate the alternate timeline (1-50) */
  simulation_years: number;

  /** Type of deviation scenario */
  scenario_type: ScenarioType;

  /** Mode for narrative generation */
  narrative_mode?: NarrativeMode;

  /** Custom perspective instructions (required for ADVANCED_CUSTOM_POV mode) */
  narrative_custom_pov?: string;

  /** Use AI Smart Search (RAG) for historical context. Defaults to true. */
  use_rag?: boolean;

  /** Client-generated token for SSE progress subscription. */
  progress_token?: string;

  /** @deprecated Use narrative_mode instead. Kept for backwards compatibility. */
  include_narrative?: boolean;
}

/**
 * Generation - unified content for a time period (replaces Report).
 *
 * Contains all content (structured report + narrative + media) for a specific time period.
 * Matches backend Generation model.
 */
export interface Generation {
  /** Unique generation identifier */
  id: string;

  /** Parent timeline identifier */
  timeline_id: string;

  /** Sequential order number (1, 2, 3...) */
  generation_order: number;

  /** Type of generation */
  generation_type: GenerationType;

  /** Year when this generation period starts (relative to deviation) */
  start_year: number;

  /** Year when this generation period ends (relative to deviation) */
  end_year: number;

  /** Number of years this generation covers */
  period_years: number;

  // === STRUCTURED REPORT ===
  /** High-level overview of how history changed in this period */
  executive_summary: string;

  /** Government, international relations, diplomacy */
  political_changes: string;

  /** Military conflicts, wars, and armed tensions */
  conflicts_and_wars: string;

  /** Trade, industry, financial systems */
  economic_impacts: string;

  /** Culture, demographics, social movements */
  social_developments: string;

  /** Innovation pace, key technologies affected */
  technological_shifts: string;

  /** Important people in this alternate timeline period */
  key_figures: string;

  /** Lasting effects by end of this period */
  long_term_implications: string;

  /** Report translations (future feature) */
  report_translations?: Record<string, any> | null;

  // === NARRATIVE ===
  /** Mode for narrative generation */
  narrative_mode?: NarrativeMode | null;

  /** Story-like narrative of the alternate history for this period (optional) */
  narrative_prose?: string | null;

  /** Custom perspective instructions */
  narrative_custom_pov?: string | null;

  /** Narrative translations (future feature) */
  narrative_translations?: Record<string, string> | null;

  // === AUDIO (Future Feature) ===
  /** Audio script text */
  audio_script?: string | null;

  /** Audio script format */
  audio_script_format?: 'podcast' | 'documentary' | 'news_report' | 'storytelling' | null;

  /** URL to audio file */
  audio_url?: string | null;

  /** Local path to audio file */
  audio_local_path?: string | null;

  /** Audio duration in seconds */
  audio_duration_seconds?: number | null;

  /** Voice model used */
  audio_voice_model?: string | null;

  /** Voice settings JSON */
  audio_voice_settings?: Record<string, any> | null;

  /** Audio translations (future feature) */
  audio_translations?: Record<string, any> | null;

  // === SOURCE TRACKING ===
  /** ID of skeleton used to generate this (optional) */
  source_skeleton_id?: string | null;

  /** Additional source context */
  source_context?: string | null;

  // === MODEL TRACKING ===
  /** LLM provider used for report generation (optional) */
  report_model_provider?: string | null;

  /** Specific model used for report generation (optional) */
  report_model_name?: string | null;

  /** LLM provider used for narrative generation (optional) */
  narrative_model_provider?: string | null;

  /** Specific model used for narrative generation (optional) */
  narrative_model_name?: string | null;

  /** LLM provider used for audio generation (optional) */
  audio_model_provider?: string | null;

  /** Specific model used for audio generation (optional) */
  audio_model_name?: string | null;

  /** UTC timestamp when generation was created (ISO 8601 format) */
  created_at: string;

  /** UTC timestamp when generation was last updated (ISO 8601 format) */
  updated_at: string;
}

/**
 * @deprecated Use Generation instead. Kept for backwards compatibility.
 *
 * Structured analytical report for a specific time period.
 *
 * Contains comprehensive analysis across multiple domains for a given period.
 * Matches backend StructuredReport model.
 */
export interface StructuredReport {
  /** Unique report identifier */
  id: string;

  /** Year when this report period starts (relative to deviation) */
  start_year: number;

  /** Year when this report period ends (relative to deviation) */
  end_year: number;

  /** Number of years this report covers */
  period_years: number;

  /** Order of this report within the timeline (1, 2, 3...) */
  report_order: number;

  /** High-level overview of how history changed in this period */
  executive_summary: string;

  /** Government, international relations, diplomacy */
  political_changes: string;

  /** Military conflicts, wars, and armed tensions */
  conflicts_and_wars: string;

  /** Trade, industry, financial systems */
  economic_impacts: string;

  /** Culture, demographics, social movements */
  social_developments: string;

  /** Innovation pace, key technologies affected */
  technological_shifts: string;

  /** Important people in this alternate timeline period */
  key_figures: string;

  /** Lasting effects by end of this period */
  long_term_implications: string;

  /** LLM provider used for report generation (optional) */
  model_provider?: string;

  /** Specific model used for report generation (optional) */
  model_name?: string;

  /** UTC timestamp when report was created (ISO 8601 format) */
  generated_at: string;
}

/**
 * Structured report with optional narrative prose.
 *
 * Extends StructuredReport to include narrative content and skeleton tracking.
 * Matches backend ReportWithNarrative model.
 */
export interface ReportWithNarrative extends StructuredReport {
  /** Story-like narrative of the alternate history for this period (optional) */
  narrative_prose: string | null;

  /** LLM provider used for narrative generation (optional) */
  narrative_model_provider?: string;

  /** Specific model used for narrative generation (optional) */
  narrative_model_name?: string;

  /** ID of skeleton used to generate this report (optional) */
  skeleton_id?: string | null;

  /** Whether this report has a skeleton snapshot */
  has_skeleton_snapshot?: boolean;
}

/**
 * Complete alternate history timeline with branching support.
 *
 * Matches backend Timeline model.
 */
export interface Timeline {
  /** Unique timeline identifier (UUID) */
  id: string;

  // === BRANCHING SUPPORT (NEW) ===
  /** Parent timeline ID (null for root timelines) */
  parent_timeline_id?: string | null;

  /** Year where this branch diverges from parent */
  branch_point_year?: number | null;

  /** Description of what changes at the branch point */
  branch_deviation_description?: string | null;

  // === ROOT DEVIATION ===
  /** Date of the original historical deviation (YYYY-MM-DD format) */
  root_deviation_date: string;

  /** Description of the original deviation */
  root_deviation_description: string;

  /** Type of deviation scenario */
  scenario_type: ScenarioType;

  /** Short AI-generated timeline name (3-5 words) */
  timeline_name?: string | null;

  // === GENERATIONS (replaces reports) ===
  /** Generations covering different time periods */
  generations: Generation[];

  /** UTC timestamp when timeline was created (ISO 8601 format) */
  created_at: string;

  /** UTC timestamp when timeline was last updated (ISO 8601 format) */
  updated_at: string;

  // === DEPRECATED FIELDS ===
  /** @deprecated Use root_deviation_date/description instead */
  deviation_point?: TimelineCreationRequest;

  /** @deprecated Calculate from generations instead */
  total_simulation_years?: number;

  /** @deprecated Use generations instead */
  reports?: ReportWithNarrative[];

  /** @deprecated Use created_at instead */
  generated_at?: string;
}

/**
 * Simplified timeline model for list endpoints.
 *
 * Contains only essential fields for displaying timeline lists.
 * Matches backend TimelineListItem model.
 */
export interface TimelineListItem {
  /** Unique timeline identifier (UUID) */
  id: string;

  /** Parent timeline ID (null for root timelines) */
  parent_timeline_id?: string | null;

  /** Date of the root historical deviation (YYYY-MM-DD format) */
  root_deviation_date: string;

  /** Brief description of the root deviation */
  root_deviation_description: string;

  /** Type of deviation scenario */
  scenario_type: ScenarioType;

  /** Short AI-generated timeline name (3-5 words) */
  timeline_name?: string | null;

  /** Number of generations in this timeline */
  generation_count: number;

  /** UTC timestamp when timeline was created (ISO 8601 format) */
  created_at: string;

  /** Number of audio scripts created from this timeline's generations */
  audio_script_count: number;

  // === DEPRECATED FIELDS ===
  /** @deprecated Use root_deviation_date instead */
  deviation_date?: string;

  /** @deprecated Use root_deviation_description instead */
  deviation_description?: string;

  /** @deprecated Calculate from generations instead */
  total_simulation_years?: number;

  /** @deprecated Use generation_count instead */
  report_count?: number;

  /** @deprecated Use created_at instead */
  generated_at?: string;
}

/**
 * Request payload for creating a new root timeline.
 *
 * Matches backend TimelineCreationRequest model.
 */
export interface TimelineCreationRequest {
  /** Date of the historical deviation point (YYYY-MM-DD format) */
  deviation_date: string;

  /** Description of what changed in history (10-500 characters) */
  deviation_description: string;

  /** Number of years to simulate the alternate timeline (1-50) */
  simulation_years: number;

  /** Type of deviation scenario */
  scenario_type: ScenarioType;

  /** Mode for narrative generation */
  narrative_mode?: NarrativeMode;

  /** Custom perspective instructions (required for ADVANCED_CUSTOM_POV mode) */
  narrative_custom_pov?: string;
}

/**
 * Request payload for extending an existing timeline.
 *
 * Matches backend TimelineExtensionRequest model.
 */
export interface TimelineExtensionRequest {
  /** UUID of the existing timeline to extend */
  timeline_id: string;

  /** Number of additional years to simulate forward (1-30) */
  additional_years: number;

  /** Optional additional information, circumstances, or events to consider (max 2000 chars) */
  additional_context?: string;

  /** Mode for narrative generation */
  narrative_mode?: NarrativeMode;

  /** Custom perspective instructions (required for ADVANCED_CUSTOM_POV mode) */
  narrative_custom_pov?: string;

  /** Use AI Smart Search (RAG) for historical context. Defaults to true. */
  use_rag?: boolean;

  /** @deprecated Use narrative_mode instead. Kept for backwards compatibility. */
  include_narrative?: boolean;

  /** Client-generated token for SSE progress subscription */
  progress_token?: string;
}

/**
 * Request payload for branching from an existing timeline.
 *
 * Matches backend TimelineBranchRequest model.
 */
export interface TimelineBranchRequest {
  /** UUID of the source timeline to branch from */
  source_timeline_id: string;

  /** Year where the branch diverges (relative to root deviation) */
  branch_point_year: number;

  /** Description of what changes at this point (10-500 characters) */
  branch_deviation_description: string;

  /** Number of years to simulate forward from branch point (1-50) */
  simulation_years: number;

  /** Mode for narrative generation */
  narrative_mode?: NarrativeMode;

  /** Custom perspective instructions (required for ADVANCED_CUSTOM_POV mode) */
  narrative_custom_pov?: string;
}

/**
 * Health check response from API.
 *
 * Matches backend HealthResponse model.
 */
export interface HealthResponse {
  /** Health status of the API */
  status: string;

  /** API version */
  version: string;
}

/**
 * Error response from API.
 *
 * Standard error format returned by custom exception handlers.
 */
export interface ErrorResponse {
  /** Error type/name */
  error: string;

  /** Human-readable error message */
  message: string;

  /** Additional error details (optional) */
  details?: Record<string, unknown>;
}

/**
 * API client response wrapper for async operations.
 */
export interface ApiResponse<T> {
  /** Response data (if successful) */
  data?: T;

  /** Error information (if failed) */
  error?: ErrorResponse;

  /** HTTP status code */
  status: number;
}

/**
 * Helper type for report selection in UI
 */
export interface ReportSelection {
  /** The selected report */
  report: ReportWithNarrative;

  /** Index in the reports array */
  index: number;

  /** Whether this is the first report */
  isFirst: boolean;

  /** Whether this is the latest report */
  isLatest: boolean;
}

/**
 * Utility functions for working with multi-generation timelines
 */
export const TimelineUtils = {
  /**
   * Get a human-readable description of a generation's time period
   */
  getGenerationPeriodDescription: (generation: Generation): string => {
    if (generation.start_year === 0) {
      return `Years 0-${generation.end_year} (${generation.period_years} years)`;
    } else {
      return `Years ${generation.start_year}-${generation.end_year} (${generation.period_years} years)`;
    }
  },

  /**
   * Get the latest generation from a timeline
   */
  getLatestGeneration: (timeline: Timeline): Generation | null => {
    if (!timeline.generations || timeline.generations.length === 0) {
      return null;
    }
    return timeline.generations.reduce((latest, current) =>
      current.generation_order > latest.generation_order ? current : latest
    );
  },

  /**
   * Get the first generation from a timeline
   */
  getFirstGeneration: (timeline: Timeline): Generation | null => {
    if (!timeline.generations || timeline.generations.length === 0) {
      return null;
    }
    return timeline.generations.reduce((first, current) =>
      current.generation_order < first.generation_order ? current : first
    );
  },

  /**
   * Get a generation by its order number
   */
  getGenerationByOrder: (timeline: Timeline, order: number): Generation | null => {
    return timeline.generations.find(generation => generation.generation_order === order) || null;
  },

  /**
   * Sort generations by order
   */
  sortGenerationsByOrder: (generations: Generation[]): Generation[] => {
    return [...generations].sort((a, b) => a.generation_order - b.generation_order);
  },

  /**
   * Get absolute years for a generation (deviation date + relative years)
   */
  getAbsoluteYears: (timeline: Timeline, generation: Generation): { startYear: number; endYear: number } => {
    const deviationYear = new Date(timeline.root_deviation_date).getFullYear();
    return {
      startYear: deviationYear + generation.start_year,
      endYear: deviationYear + generation.end_year
    };
  },

  /**
   * Get total years simulated across all generations in a timeline
   */
  getTotalYearsSimulated: (timeline: Timeline): number => {
    if (!timeline.generations || timeline.generations.length === 0) {
      return 0;
    }
    return Math.max(...timeline.generations.map(g => g.end_year));
  },

  /**
   * @deprecated Use getGenerationPeriodDescription instead
   */
  getReportPeriodDescription: (report: StructuredReport): string => {
    if (report.start_year === 0) {
      return `Years 0-${report.end_year} (${report.period_years} years)`;
    } else {
      return `Years ${report.start_year}-${report.end_year} (${report.period_years} years)`;
    }
  },

  /**
   * @deprecated Use getLatestGeneration instead
   */
  getLatestReport: (timeline: Timeline): Generation | null => {
    return TimelineUtils.getLatestGeneration(timeline);
  },

  /**
   * @deprecated Use getFirstGeneration instead
   */
  getFirstReport: (timeline: Timeline): Generation | null => {
    return TimelineUtils.getFirstGeneration(timeline);
  },

  /**
   * @deprecated Use getGenerationByOrder instead
   */
  getReportByOrder: (timeline: Timeline, order: number): Generation | null => {
    return TimelineUtils.getGenerationByOrder(timeline, order);
  },

  /**
   * @deprecated Use sortGenerationsByOrder instead
   */
  sortReportsByOrder: (generations: Generation[]): Generation[] => {
    return TimelineUtils.sortGenerationsByOrder(generations);
  }
};

/**
 * ============================================================================
 * LLM Provider Configuration Types
 * ============================================================================
 */

/**
 * LLM provider options.
 */
export type LLMProvider = 'google' | 'openrouter' | 'ollama' | 'anthropic' | 'openai' | 'cliproxy';

/**
 * LLM configuration interface.
 *
 * Represents the current LLM provider configuration.
 */
export interface LLMConfig {
  /** Current LLM provider */
  provider: LLMProvider;

  /** Current model identifier */
  model_name: string;

  /** Whether Google API key is configured (env or DB) */
  api_key_google_set: boolean;

  /** Whether OpenRouter API key is configured (env or DB) */
  api_key_openrouter_set: boolean;

  /** Whether Anthropic API key is configured (env or DB) */
  api_key_anthropic_set: boolean;

  /** Whether OpenAI API key is configured (env or DB) */
  api_key_openai_set: boolean;

  /** Ollama server base URL (if configured) */
  ollama_base_url?: string;

  /** Last update timestamp (UTC) */
  updated_at: string;
}

/**
 * LLM configuration request interface.
 *
 * Used for updating LLM provider configuration.
 */
export interface LLMConfigRequest {
  /** LLM provider to use */
  provider: LLMProvider;

  /** Model identifier */
  model_name: string;

  /** Optional Google Gemini API key */
  api_key_google?: string;

  /** Optional OpenRouter API key */
  api_key_openrouter?: string;

  /** Optional Anthropic API key */
  api_key_anthropic?: string;

  /** Optional OpenAI API key */
  api_key_openai?: string;

  /** Optional Ollama server base URL */
  ollama_base_url?: string;
}

/**
 * Available models response interface.
 *
 * Contains lists of available models per provider.
 */
export interface AvailableModels {
  /** Available Google Gemini models */
  google: string[];

  /** Available OpenRouter models */
  openrouter: string[];

  /** Available Ollama models */
  ollama: string[];

  /** Available Anthropic Claude models */
  anthropic: string[];

  /** Available OpenAI models */
  openai: string[];

  /** Available CLIProxyAPI models */
  cliproxy: string[];
}

/**
 * ============================================================================
 * Per-Agent LLM Configuration Types (NEW)
 * ============================================================================
 */

/**
 * AI agent types that can have individual LLM configurations.
 */
export const AgentType = {
  HISTORIAN: 'historian',
  STORYTELLER: 'storyteller',
  SKELETON: 'skeleton',
  SKELETON_HISTORIAN: 'skeleton_historian',
  ILLUSTRATOR: 'illustrator',
  SCRIPT_WRITER: 'script_writer',
  TRANSLATOR: 'translator',
  CHARACTER_PROFILER: 'character_profiler',
  IMPERSONATOR: 'impersonator',
  RIPPLE_ANALYST: 'ripple_analyst',
} as const;

export type AgentType = typeof AgentType[keyof typeof AgentType];

/**
 * Agent-specific LLM configuration.
 *
 * Represents an override configuration for a specific agent.
 * If no override exists, the agent uses the global LLM configuration.
 */
export interface AgentLLMConfig {
  /** Configuration ID */
  id: number;

  /** Agent type this configuration applies to */
  agent_type: AgentType;

  /** LLM provider for this agent */
  provider: LLMProvider;

  /** Model identifier for this agent */
  model_name: string;

  /** Whether Google API key is configured for this agent */
  api_key_google_set: boolean;

  /** Whether OpenRouter API key is configured for this agent */
  api_key_openrouter_set: boolean;

  /** Whether Anthropic API key is configured for this agent */
  api_key_anthropic_set: boolean;

  /** Whether OpenAI API key is configured for this agent */
  api_key_openai_set: boolean;

  /** Ollama server base URL for this agent (if configured) */
  ollama_base_url?: string | null;

  /** Max tokens override for this agent (optional) */
  max_tokens?: number | null;

  /** Temperature override for this agent (optional) */
  temperature?: number | null;

  /** Whether this configuration is enabled */
  enabled: boolean;

  /** UTC timestamp when config was created */
  created_at: string;

  /** UTC timestamp when config was last updated */
  updated_at: string;
}

/**
 * Request payload for creating/updating agent-specific LLM configuration.
 */
export interface AgentLLMConfigRequest {
  /** Agent type to configure */
  agent_type: AgentType;

  /** LLM provider to use */
  provider: LLMProvider;

  /** Model identifier */
  model_name: string;

  /** Optional Google Gemini API key override */
  api_key_google?: string;

  /** Optional OpenRouter API key override */
  api_key_openrouter?: string;

  /** Optional Anthropic API key override */
  api_key_anthropic?: string;

  /** Optional OpenAI API key override */
  api_key_openai?: string;

  /** Optional Ollama server base URL override */
  ollama_base_url?: string;

  /** Optional max tokens override (1024-32768) */
  max_tokens?: number;

  /** Optional temperature override (0.0-2.0) */
  temperature?: number;

  /** Whether this configuration is enabled */
  enabled?: boolean;
}

/**
 * Complete LLM configuration including global and per-agent settings.
 */
export interface AllLLMConfigs {
  /** Global (default) LLM configuration */
  global_config: LLMConfig;

  /** Per-agent configuration overrides */
  agent_configs: Record<AgentType, AgentLLMConfig>;

  /** List of agents that have overrides configured */
  agents_with_overrides: AgentType[];

  /** List of agents using the global configuration */
  agents_using_global: AgentType[];
}

/**
 * Response when getting an agent config that doesn't exist.
 */
export interface AgentUsesGlobalResponse {
  /** Message indicating agent uses global config */
  message: string;

  /** Flag indicating this is a "uses global" response */
  using_global: true;
}

/**
 * Utility functions for working with per-agent LLM configurations.
 */
export const AgentConfigUtils = {
  /**
   * Get human-readable agent name
   */
  getAgentDisplayName: (agentType: AgentType): string => {
    const names: Record<AgentType, string> = {
      historian: 'Historian',
      storyteller: 'Storyteller',
      skeleton: 'Skeleton Generator',
      skeleton_historian: 'Skeleton Historian',
      illustrator: 'Illustrator',
      script_writer: 'Script Writer',
      translator: 'Translator',
      character_profiler: 'Character Profiler',
      impersonator: 'Impersonator',
      ripple_analyst: 'Ripple Analyst',
    };
    return names[agentType];
  },

  /**
   * Get agent description
   */
  getAgentDescription: (agentType: AgentType): string => {
    const descriptions: Record<AgentType, string> = {
      historian: 'Generates structured timeline reports with analytical sections',
      storyteller: 'Creates advanced narrative prose for timeline reports',
      skeleton: 'Generates editable event outlines for timeline creation',
      skeleton_historian: 'Expands skeleton outlines into comprehensive reports',
      illustrator: 'Creates detailed image prompts for timeline visualization',
      script_writer: 'Generates audio scripts from timeline content for podcasts and documentaries',
      translator: 'Generates translation from various sources with LLM',
      character_profiler: 'Generates structured biographical profiles for historical figures',
      impersonator: 'Conducts in-character conversations as historical figures',
      ripple_analyst: 'Extracts causal nodes and edges to build interactive causal graphs',
    };
    return descriptions[agentType];
  },

  /**
   * Check if an agent has an override configured
   */
  hasOverride: (allConfigs: AllLLMConfigs, agentType: AgentType): boolean => {
    return allConfigs.agents_with_overrides.includes(agentType);
  },

  /**
   * Get effective config for an agent (override or global)
   */
  getEffectiveConfig: (
    allConfigs: AllLLMConfigs,
    agentType: AgentType
  ): LLMConfig | AgentLLMConfig => {
    const override = allConfigs.agent_configs[agentType];
    return override || allConfigs.global_config;
  },
};

/**
 * ============================================================================
 * Skeleton Timeline Types (NEW)
 * ============================================================================
 */

/**
 * Skeleton status options.
 */
export const SkeletonStatus = {
  PENDING: 'pending',
  EDITING: 'editing',
  APPROVED: 'approved',
  REPORT_GENERATED: 'report_generated',
} as const;

export type SkeletonStatus = typeof SkeletonStatus[keyof typeof SkeletonStatus];

/**
 * Single event in a skeleton timeline.
 */
export interface SkeletonEvent {
  /** Unique event identifier */
  id: string;

  /** Parent skeleton identifier */
  skeleton_id: string;

  /** Date of the event (YYYY-MM-DD) */
  event_date: string;

  /** Year relative to deviation (0 = deviation year) */
  event_year: number;

  /** Geographic location (city, country/region) */
  location: string;

  /** Event description (2-3 sentences) */
  description: string;

  /** Position in timeline (0-based) */
  event_order: number;

  /** Whether this event was added by the user */
  is_user_added: boolean;

  /** Whether this event was modified by the user */
  is_user_modified: boolean;

  /** UTC timestamp when event was created */
  created_at: string;

  /** UTC timestamp when event was last updated */
  updated_at: string;
}

/**
 * Complete skeleton timeline with events.
 */
export interface Skeleton {
  /** Unique skeleton identifier */
  id: string;

  /** Linked timeline ID (if report generated) */
  timeline_id: string | null;

  /** Linked generation ID (if report generated) */
  generation_id: string | null;

  /** Type of skeleton (timeline_draft, extension_draft, branch_draft) */
  skeleton_type: 'timeline_draft' | 'extension_draft' | 'branch_draft';

  /** Current status of the skeleton */
  status: SkeletonStatus;

  // For timeline drafts
  /** Date of the historical deviation (YYYY-MM-DD) - only for timeline_draft */
  deviation_date: string | null;

  /** Description of what changed - only for timeline_draft */
  deviation_description: string | null;

  /** Scenario type - only for timeline_draft */
  scenario_type: string | null;

  // For extension/branch drafts
  /** Parent timeline ID - for extension_draft and branch_draft */
  parent_timeline_id: string | null;

  /** Extension start year - for extension_draft */
  extension_start_year: number | null;

  /** Extension end year - for extension_draft */
  extension_end_year: number | null;

  /** Branch point year - for branch_draft */
  branch_point_year: number | null;

  /** Branch deviation description - for branch_draft */
  branch_deviation_description: string | null;

  /** Array of skeleton events (15-25 typically) */
  events: SkeletonEvent[];

  /** LLM provider used for generation */
  model_provider: string | null;

  /** Specific model used for generation */
  model_name: string | null;

  /** UTC timestamp when skeleton was generated */
  generated_at: string;

  /** UTC timestamp when skeleton was approved */
  approved_at: string | null;
}

/**
 * Request payload for generating a skeleton timeline.
 */
export interface SkeletonGenerationRequest {
  /** Date of the historical deviation (YYYY-MM-DD, 1900-1950) */
  deviation_date: string;

  /** Description of what changed (10-500 characters) */
  deviation_description: string;

  /** Number of years to simulate (1-50) */
  simulation_years: number;

  /** Type of deviation scenario */
  scenario_type: ScenarioType;

  /** Use AI Smart Search (RAG) for historical context. Defaults to true. */
  use_rag?: boolean;
}

/**
 * Event update payload (for creating or updating events).
 */
export interface SkeletonEventUpdate {
  /** Event ID (null for new events, UUID for updates) */
  id: string | null;

  /** Date of the event (YYYY-MM-DD) */
  event_date: string;

  /** Geographic location */
  location: string;

  /** Event description */
  description: string;

  /** Position in timeline (0-based) */
  event_order: number;
}

/**
 * Request payload for updating skeleton events.
 */
export interface SkeletonEventsUpdateRequest {
  /** Events to create or update */
  events_update: SkeletonEventUpdate[];

  /** Event IDs to delete */
  deleted_event_ids: string[];
}

/**
 * Request payload for generating report from skeleton.
 */
export interface GenerateFromSkeletonRequest {
  /** Skeleton UUID */
  skeleton_id: string;

  /** Mode for narrative generation */
  narrative_mode?: NarrativeMode;

  /** Custom perspective instructions (required for ADVANCED_CUSTOM_POV mode) */
  narrative_custom_pov?: string | null;

  /** Use AI Smart Search (RAG) for historical context. Defaults to true. */
  use_rag?: boolean;

  /** Client-generated token for SSE progress subscription. */
  progress_token?: string;
}

/**
 * Utility functions for working with skeleton timelines.
 */
export const SkeletonUtils = {
  /**
   * Sort events by order
   */
  sortEventsByOrder: (events: SkeletonEvent[]): SkeletonEvent[] => {
    return [...events].sort((a, b) => a.event_order - b.event_order);
  },

  /**
   * Check if skeleton can be edited
   * Note: Skeletons can always be edited regardless of status to allow reuse
   */
  canEdit: (_skeleton: Skeleton): boolean => {
    return true; // Always allow editing for skeleton reusability
  },

  /**
   * Check if skeleton can be approved
   * Only show approve button if not already approved
   */
  canApprove: (skeleton: Skeleton): boolean => {
    return skeleton.status === SkeletonStatus.PENDING || skeleton.status === SkeletonStatus.EDITING;
  },

  /**
   * Check if report can be generated from skeleton
   * Allow generating multiple reports from the same skeleton
   */
  canGenerateReport: (skeleton: Skeleton): boolean => {
    return skeleton.status === SkeletonStatus.APPROVED || skeleton.status === SkeletonStatus.REPORT_GENERATED;
  },

  /**
   * Get absolute year for an event
   */
  getAbsoluteYear: (skeleton: Skeleton, event: SkeletonEvent): number | null => {
    if (!skeleton.deviation_date) {
      // Return null if deviation date is not available (e.g., during skeleton creation)
      return null;
    }
    const deviationYear = new Date(skeleton.deviation_date).getFullYear();
    return deviationYear + event.event_year;
  },

  /**
   * Get year range for skeleton
   */
  getYearRange: (skeleton: Skeleton): { startYear: number; endYear: number } | null => {
    if (!skeleton.deviation_date || skeleton.events.length === 0) {
      // Return null if deviation date is not available or no events (e.g., during skeleton creation)
      return null;
    }
    const deviationYear = new Date(skeleton.deviation_date).getFullYear();
    const eventYears = skeleton.events.map(e => e.event_year);
    const minYear = Math.min(...eventYears);
    const maxYear = Math.max(...eventYears);
    return {
      startYear: deviationYear + minYear,
      endYear: deviationYear + maxYear,
    };
  },
};

/**
 * ============================================================================
 * Image Generation Types
 * ============================================================================
 */

/**
 * Media types supported by the system.
 */
export const MediaType = {
  IMAGE: 'image',
  AUDIO: 'audio',
  VIDEO: 'video',
  DOCUMENT: 'document',
} as const;

export type MediaType = typeof MediaType[keyof typeof MediaType];

/**
 * Image prompt skeleton status options.
 */
export const ImagePromptSkeletonStatus = {
  PENDING: 'pending',
  EDITING: 'editing',
  APPROVED: 'approved',
  GENERATING: 'generating',
  COMPLETED: 'completed',
} as const;

export type ImagePromptSkeletonStatus = typeof ImagePromptSkeletonStatus[keyof typeof ImagePromptSkeletonStatus];

/**
 * Single image prompt with metadata.
 */
export interface ImagePrompt {
  /** Detailed prompt for image generation (50-200 words) */
  prompt_text: string;

  /** Year relative to deviation point (0 = deviation year) */
  event_year: number | null;

  /** Short descriptive title (5-10 words) */
  title: string;

  /** Brief context about what this image represents (1-2 sentences) */
  description: string | null;

  /** Display order (0-based) */
  prompt_order: number;

  /** Style guidance (e.g., "photorealistic 1920s documentary") */
  style_notes: string | null;

  /** Whether user modified this prompt */
  is_user_modified?: boolean;
}

/**
 * Image prompt update payload (for creating or updating prompts).
 */
export interface ImagePromptUpdate {
  /** Prompt ID (null for new prompts) */
  id: string | null;

  /** Detailed prompt for image generation */
  prompt_text: string;

  /** Year relative to deviation point */
  event_year: number | null;

  /** Short descriptive title */
  title: string;

  /** Brief context description */
  description: string | null;

  /** Display order */
  prompt_order: number;

  /** Style guidance */
  style_notes: string | null;

  /** Whether user modified this prompt */
  is_user_modified: boolean;
}

/**
 * Image prompt skeleton with prompts.
 */
export interface ImagePromptSkeleton {
  /** Unique skeleton identifier */
  id: string;

  /** Parent timeline UUID */
  timeline_id: string;

  /** Optional specific generation UUID */
  generation_id: string | null;

  /** Current status */
  status: ImagePromptSkeletonStatus;

  /** Number of images to generate */
  num_images: number;

  /** Optional focus areas (e.g., ["political", "economic"]) */
  focus_areas: string[] | null;

  /** List of image prompts */
  prompts: ImagePrompt[];

  /** LLM provider used to generate prompts */
  model_provider: string | null;

  /** Specific model used to generate prompts */
  model_name: string | null;

  /** UTC timestamp when skeleton was created */
  created_at: string;

  /** UTC timestamp when skeleton was approved */
  approved_at: string | null;

  /** UTC timestamp when images were completed */
  completed_at: string | null;
}

/**
 * Request payload for generating image prompt skeleton.
 */
export interface ImagePromptSkeletonCreate {
  /** UUID of the timeline */
  timeline_id: string;

  /** Optional UUID of specific generation */
  generation_id: string | null;

  /** Number of images to generate (3-20) */
  num_images: number;

  /** Optional focus areas */
  focus_areas: string[] | null;
}

/**
 * Request payload for updating image prompts.
 */
export interface ImagePromptSkeletonUpdate {
  /** Prompts to create or update */
  prompts_update: ImagePromptUpdate[];

  /** Prompt indices to delete */
  deleted_prompt_indices: number[];
}

/**
 * Request payload for generating images from approved skeleton.
 */
export interface GenerateImagesRequest {
  /** UUID of the approved prompt skeleton */
  skeleton_id: string;
}

/**
 * Timeline image with metadata.
 */
export interface TimelineImage {
  /** Unique image identifier */
  id: string;

  /** Parent timeline UUID */
  timeline_id: string;

  /** Optional specific generation UUID */
  generation_id: string | null;

  /** Type of media (always "image" for now) */
  media_type: MediaType;

  /** Prompt used for generation */
  prompt_text: string;

  /** URL to the generated image */
  image_url: string;

  /** Year relative to deviation point */
  event_year: number | null;

  /** Short descriptive title */
  title: string;

  /** Brief context description */
  description: string | null;

  /** Display order */
  media_order: number;

  /** Whether this was manually added by user */
  is_user_added: boolean;

  /** Whether this was modified by user */
  is_user_modified: boolean;

  /** LLM provider that generated the prompt */
  model_provider: string | null;

  /** Specific model that generated the prompt */
  model_name: string | null;

  /** UTC timestamp when image was generated */
  generated_at: string;

  /** UTC timestamp when record was created */
  created_at: string;

  /** UTC timestamp when record was last updated */
  updated_at: string;
}

/**
 * Utility functions for working with image generation.
 */
export const ImageUtils = {
  /**
   * Sort prompts by order
   */
  sortPromptsByOrder: (prompts: ImagePrompt[]): ImagePrompt[] => {
    return [...prompts].sort((a, b) => a.prompt_order - b.prompt_order);
  },

  /**
   * Sort images by order
   */
  sortImagesByOrder: (images: TimelineImage[]): TimelineImage[] => {
    return [...images].sort((a, b) => a.media_order - b.media_order);
  },

  /**
   * Check if skeleton can be edited
   */
  canEdit: (skeleton: ImagePromptSkeleton): boolean => {
    return skeleton.status !== ImagePromptSkeletonStatus.GENERATING;
  },

  /**
   * Check if skeleton can be approved
   */
  canApprove: (skeleton: ImagePromptSkeleton): boolean => {
    return (
      skeleton.status === ImagePromptSkeletonStatus.PENDING ||
      skeleton.status === ImagePromptSkeletonStatus.EDITING
    );
  },

  /**
   * Check if images can be generated from skeleton
   */
  canGenerateImages: (skeleton: ImagePromptSkeleton): boolean => {
    return skeleton.status === ImagePromptSkeletonStatus.APPROVED;
  },

  /**
   * Get absolute year for an image
   */
  getAbsoluteYear: (timeline: Timeline, eventYear: number): number => {
    const deviationYear = new Date(timeline.root_deviation_date).getFullYear();
    return deviationYear + eventYear;
  },

  /**
   * Get valid focus areas
   */
  getValidFocusAreas: (): string[] => {
    return ['political', 'economic', 'social', 'technological', 'military', 'cultural'];
  },
};

// ============================================================================
// Translation Service Types
// ============================================================================

/**
 * Supported translation languages.
 */
export const SupportedLanguages = {
  EN: 'en',
  HU: 'hu',
  DE: 'de',
  ES: 'es',
  IT: 'it',
  FR: 'fr',
  PT: 'pt',
  PL: 'pl',
  NL: 'nl',
  JA: 'ja',
  ZH: 'zh',
} as const;

export type SupportedLanguage = typeof SupportedLanguages[keyof typeof SupportedLanguages];

/**
 * Language display information.
 */
export interface LanguageInfo {
  code: SupportedLanguage;
  name: string;
  nativeName: string;
  flag: string;
}

/**
 * Available language options with display information.
 */
export const LANGUAGES: LanguageInfo[] = [
  { code: 'en', name: 'English', nativeName: 'English', flag: '🇬🇧' },
  { code: 'hu', name: 'Hungarian', nativeName: 'Magyar', flag: '🇭🇺' },
  { code: 'de', name: 'German', nativeName: 'Deutsch', flag: '🇩🇪' },
  { code: 'es', name: 'Spanish', nativeName: 'Español', flag: '🇪🇸' },
  { code: 'it', name: 'Italian', nativeName: 'Italiano', flag: '🇮🇹' },
  { code: 'fr', name: 'French', nativeName: 'Français', flag: '🇫🇷' },
  { code: 'pt', name: 'Portuguese', nativeName: 'Português', flag: '🇵🇹' },
  { code: 'pl', name: 'Polish', nativeName: 'Polski', flag: '🇵🇱' },
  { code: 'nl', name: 'Dutch', nativeName: 'Nederlands', flag: '🇳🇱' },
];

/**
 * Request to translate generation content.
 */
export interface TranslationRequest {
  /** Target language code (e.g., 'hu', 'de', 'es', 'it') */
  target_language: SupportedLanguage;
}

/**
 * Response from generation translation.
 */
export interface TranslationResponse {
  /** Generation UUID */
  generation_id: string;
  /** Parent timeline UUID */
  timeline_id: string;
  /** Generation order number */
  generation_order: number;
  /** Target language code */
  target_language: SupportedLanguage;
  /** Translated sections */
  translations: {
    executive_summary: string;
    political_changes: string;
    conflicts_and_wars: string;
    economic_impacts: string;
    social_developments: string;
    technological_shifts: string;
    key_figures: string;
    long_term_implications: string;
  };
  /** Total characters translated */
  character_count: number;
  /** Whether result was from cache */
  cached: boolean;
  /** Translation timestamp (UTC) */
  translated_at: string;
}

/**
 * Response from narrative translation.
 */
export interface NarrativeTranslationResponse {
  /** Generation UUID */
  generation_id: string;
  /** Parent timeline UUID */
  timeline_id: string;
  /** Generation order number */
  generation_order: number;
  /** Target language code */
  target_language: SupportedLanguage;
  /** Translated narrative text */
  narrative_prose: string;
  /** Total characters translated */
  character_count: number;
  /** Whether result was from cache */
  cached: boolean;
  /** Translation timestamp (UTC) */
  translated_at: string;
}

/**
 * Translation usage statistics.
 */
export interface TranslationUsage {
  /** Month in YYYY-MM format */
  year_month: string;
  /** Characters translated this month */
  characters_used: number;
  /** Monthly character limit */
  characters_limit: number;
  /** Percentage of limit used */
  percentage_used: number;
  /** Number of API calls made */
  api_calls: number;
  /** Estimated cost in USD */
  estimated_cost: number;
}

/**
 * Translation configuration.
 */
export interface TranslationConfig {
  /** Whether translation is enabled */
  enabled: boolean;
  /** API tier (free or pro) */
  api_tier: 'free' | 'pro';
  /** Whether API key is configured */
  api_key_set: boolean;
  /** Last update timestamp (UTC) */
  updated_at: string;
}

/**
 * Request to update translation configuration.
 */
export interface TranslationConfigRequest {
  /** DeepL API authentication key */
  api_key: string;
  /** API tier (free or pro) */
  api_tier: 'free' | 'pro';
  /** Enable/disable translation service */
  enabled: boolean;
}

// ============================================================================
// Audio Feature Types
// ============================================================================

/**
 * Script types for audio generation.
 */
export const ScriptType = {
  PODCAST: 'podcast',
  DOCUMENTARY: 'documentary',
  NEWS_REPORT: 'news_report',
  STORYTELLING: 'storytelling',
  INTERVIEW: 'interview',
} as const;

export type ScriptType = typeof ScriptType[keyof typeof ScriptType];

/**
 * Script tone options.
 */
export const ScriptTone = {
  FORMAL: 'formal',
  CASUAL: 'casual',
  DRAMATIC: 'dramatic',
  NEUTRAL: 'neutral',
  HUMOROUS: 'humorous',
  AUTHORITATIVE: 'authoritative',
} as const;

export type ScriptTone = typeof ScriptTone[keyof typeof ScriptTone];

/**
 * Script pacing options.
 */
export const ScriptPacing = {
  FAST: 'fast',
  MEDIUM: 'medium',
  SLOW: 'slow',
  VARIED: 'varied',
} as const;

export type ScriptPacing = typeof ScriptPacing[keyof typeof ScriptPacing];

/**
 * Audio script status workflow.
 */
export const ScriptStatus = {
  DRAFT: 'draft',
  APPROVED: 'approved',
  AUDIO_GENERATED: 'audio_generated',
} as const;

export type ScriptStatus = typeof ScriptStatus[keyof typeof ScriptStatus];

/**
 * Script preset configuration.
 */
export interface ScriptPreset {
  /** Unique preset identifier */
  id: string;
  /** Preset name */
  name: string;
  /** Description of what this preset does */
  description: string;
  /** Type of script */
  script_type: ScriptType;
  /** Tone/style */
  tone: ScriptTone;
  /** Pacing */
  pacing: ScriptPacing;
  /** Number of voices (1 or 2) */
  voice_count: 1 | 2;
  /** Voice role definitions */
  voice_roles: Record<string, string>;
  /** Additional style instructions */
  style_instructions?: string;
  /** Optional prompt template name */
  prompt_template_name?: string;
  /** Whether this is a system preset */
  is_system: boolean;
  /** Whether this preset is active */
  is_active: boolean;
  /** UTC timestamp when created */
  created_at: string;
  /** UTC timestamp when last updated */
  updated_at: string;
}

/**
 * Audio script with timeline content.
 */
export interface AudioScript {
  /** Unique script identifier */
  id: string;
  /** Generation UUIDs used as source (1-10) */
  generation_ids: string[];
  /** Script title */
  title: string;
  /** Optional description */
  description?: string;
  /** Preset ID (can be string or UUID) */
  preset_id: string;
  /** Populated preset (from join) */
  preset?: ScriptPreset;
  /** User custom instructions */
  custom_instructions?: string;
  /** Markdown script with speaker markers */
  script_content: string;
  /** Script structure */
  script_structure: 'single_voice' | 'dual_voice';
  /** Total word count */
  word_count: number;
  /** Estimated audio duration in seconds */
  estimated_duration_seconds: number;
  /** Workflow status */
  status: ScriptStatus;
  /** LLM provider used */
  model_provider?: string;
  /** Model used */
  model_name?: string;
  /** UTC timestamp when created */
  created_at: string;
  /** UTC timestamp when approved */
  approved_at?: string;
  /** UTC timestamp when last updated */
  updated_at: string;
}

/**
 * Script translation.
 */
export interface ScriptTranslation {
  /** Unique translation identifier */
  id: string;
  /** Parent script UUID */
  script_id: string;
  /** Language code (ISO 639-1) */
  language_code: string;
  /** Human-readable language name */
  language_name: string;
  /** Translated content */
  translated_content: string;
  /** Whether human-translated */
  is_human_translated: boolean;
  /** Translation method used (deepl or llm) */
  translation_method: 'deepl' | 'llm';
  /** Word count of translated text */
  word_count: number;
  /** Optional quality score */
  translation_quality_score?: number;
  /** Translation model provider */
  translation_model_provider?: string;
  /** Translation model name */
  translation_model_name?: string;
  /** UTC timestamp when created */
  created_at: string;
  /** UTC timestamp when last updated */
  updated_at: string;
}

/**
 * Generated audio file.
 */
export interface AudioFile {
  /** Unique audio file identifier */
  id: string;
  /** Parent script UUID */
  script_id: string;
  /** Source type */
  source_type: 'original' | 'translation';
  /** Translation UUID (if translation) */
  script_translation_id?: string;
  /** Language code */
  language_code: string;
  /** Public URL to audio file */
  audio_url: string;
  /** Local file path (server-side) */
  audio_local_path?: string;
  /** File size in bytes */
  file_size_bytes: number;
  /** Duration in seconds */
  duration_seconds: number;
  /** Audio format (wav, mp3) */
  format: string;
  /** Sample rate */
  sample_rate?: number;
  /** Bit rate */
  bit_rate?: number;
  /** Voice model used */
  voice_model?: string;
  /** Voice settings JSON */
  voice_settings?: Record<string, any>;
  /** Voice IDs mapping */
  voice_ids?: Record<string, string>;
  /** Model provider */
  model_provider?: string;
  /** Model name */
  model_name?: string;
  /** UTC timestamp when generated */
  generated_at: string;
}

/**
 * Request to generate audio script.
 */
export interface ScriptGenerationRequest {
  /** Generation IDs to use as source (1-10) */
  generation_ids: string[];
  /** Preset ID to use */
  preset_id: string;
  /** Optional custom instructions */
  custom_instructions?: string;
  /** Optional script title */
  title?: string;
}

/**
 * Request to update script content.
 */
export interface ScriptUpdateRequest {
  /** Updated script content */
  script_content: string;
  /** Optional updated title */
  title?: string;
  /** Optional description */
  description?: string;
}

/**
 * Request to translate script.
 */
export interface ScriptTranslationRequest {
  /** ISO 639-1 language code */
  language_code: string;
  /** Human-readable language name */
  language_name: string;
}

/**
 * Request to generate audio from script.
 */
export interface AudioGenerationRequest {
  /** Script UUID */
  script_id: string;
  /** Language code (default: 'en') */
  language_code?: string;
  /** Optional voice settings override */
  voice_settings?: Record<string, any>;
  /** Optional voice IDs override */
  voice_ids?: Record<string, string>;
}

/**
 * Request to create custom preset.
 */
export interface PresetCreateRequest {
  /** Preset name */
  name: string;
  /** Description */
  description: string;
  /** Script type */
  script_type: ScriptType;
  /** Tone */
  tone: ScriptTone;
  /** Pacing */
  pacing: ScriptPacing;
  /** Number of voices */
  voice_count: 1 | 2;
  /** Voice role definitions */
  voice_roles: Record<string, string>;
  /** Optional style instructions */
  style_instructions?: string;
  /** Optional prompt template name */
  prompt_template_name?: string;
}

/**
 * Request to update custom preset.
 */
export interface PresetUpdateRequest {
  /** Optional name update */
  name?: string;
  /** Optional description update */
  description?: string;
  /** Optional tone update */
  tone?: ScriptTone;
  /** Optional pacing update */
  pacing?: ScriptPacing;
  /** Optional voice roles update */
  voice_roles?: Record<string, string>;
  /** Optional style instructions update */
  style_instructions?: string;
  /** Optional prompt template name update */
  prompt_template_name?: string;
}

/**
 * Utility functions for working with audio scripts.
 */
export const AudioScriptUtils = {
  /**
   * Format duration in seconds to readable string
   */
  formatDuration: (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    if (minutes === 0) {
      return `${seconds}s`;
    }
    return `${minutes}m ${remainingSeconds}s`;
  },

  /**
   * Format file size in bytes to readable string
   */
  formatFileSize: (bytes: number): string => {
    const mb = bytes / (1024 * 1024);
    if (mb < 1) {
      const kb = bytes / 1024;
      return `${kb.toFixed(1)} KB`;
    }
    return `${mb.toFixed(1)} MB`;
  },

  /**
   * Check if script can be edited
   *
   * Scripts can always be edited. When editing an approved script,
   * the backend will reset it to draft status automatically.
   */
  canEdit: (_script: AudioScript): boolean => {
    return true; // Always allow editing (backend handles status reset)
  },

  /**
   * Check if script can be approved
   *
   * Scripts in draft status can be approved. Already approved scripts
   * can also be re-approved (useful after editing).
   */
  canApprove: (script: AudioScript): boolean => {
    return script.status === ScriptStatus.DRAFT || script.status === ScriptStatus.APPROVED;
  },

  /**
   * Check if audio can be generated from script
   */
  canGenerateAudio: (script: AudioScript): boolean => {
    return script.status === ScriptStatus.APPROVED || script.status === ScriptStatus.AUDIO_GENERATED;
  },

  /**
   * Get status badge color
   */
  getStatusColor: (status: ScriptStatus): string => {
    switch (status) {
      case ScriptStatus.DRAFT:
        return 'text-yellow-400';
      case ScriptStatus.APPROVED:
        return 'text-green-400';
      case ScriptStatus.AUDIO_GENERATED:
        return 'text-blue-400';
      default:
        return 'text-gray-400';
    }
  },
};

// ============================================================================
// Debug Settings
// ============================================================================

/**
 * Debug settings for RAG and agent prompts.
 */
export interface DebugSettings {
  /** Enable RAG retrieval debugging logs */
  rag_debug_mode: boolean;

  /** Save agent prompts to files */
  debug_agent_prompts: boolean;

  /** Enable vector RAG (false = legacy mode) */
  vector_store_enabled: boolean;

  /** Context retrieval mode: 'rag' or 'legacy' */
  context_retrieval_mode: 'rag' | 'legacy';
}

/**
 * Request to update debug settings.
 */
export interface DebugSettingsUpdate {
  /** Enable RAG retrieval debugging logs */
  rag_debug_mode?: boolean;

  /** Save agent prompts to files */
  debug_agent_prompts?: boolean;

  /** Enable vector RAG (false = legacy mode) */
  vector_store_enabled?: boolean;

  /** Context retrieval mode: 'rag' or 'legacy' */
  context_retrieval_mode?: 'rag' | 'legacy';
}

/**
 * Statistics from data purge operation.
 */
export interface PurgeStats {
  timelines_deleted: number;
  skeletons_deleted: number;
  image_prompts_deleted: number;
  script_translations_deleted: number;
  audio_scripts_deleted: number;
  audio_files_deleted: number;
  vector_indices_deleted: number;
  filesystem_audio_deleted: number;
  filesystem_images_deleted: number;
  filesystem_prompts_deleted: number;
  vector_store_purged: boolean;
  errors: string[];
}

/**
 * Response from data purge operation.
 */
export interface PurgeDataResponse {
  success: boolean;
  message: string;
  stats: PurgeStats;
}

// ============================================================================
// Historical Figure Chat Types
// ============================================================================

/**
 * Character source types.
 */
export const CharacterSource = {
  AUTO_DETECTED: 'auto_detected',
  USER_CREATED: 'user_created',
} as const;

export type CharacterSource = typeof CharacterSource[keyof typeof CharacterSource];

/**
 * Character profile generation status.
 */
export const CharacterProfileStatus = {
  PENDING: 'pending',
  GENERATING: 'generating',
  READY: 'ready',
  ERROR: 'error',
} as const;

export type CharacterProfileStatus = typeof CharacterProfileStatus[keyof typeof CharacterProfileStatus];

/**
 * Chat message roles.
 */
export const ChatMessageRole = {
  USER: 'user',
  CHARACTER: 'character',
} as const;

export type ChatMessageRole = typeof ChatMessageRole[keyof typeof ChatMessageRole];

/**
 * Character profile chunk types.
 */
export const CharacterChunkType = {
  BIOGRAPHY: 'biography',
  PERSONALITY: 'personality',
  RELATIONSHIPS: 'relationships',
  BELIEFS: 'beliefs',
  SPEAKING_STYLE: 'speaking_style',
  EVENT_INVOLVEMENT: 'event_involvement',
} as const;

export type CharacterChunkType = typeof CharacterChunkType[keyof typeof CharacterChunkType];

/**
 * Summary of a character profile (embedded in character list responses).
 */
export interface CharacterProfileSummary {
  id: string;
  cutoff_year: number;
  profile_status: string;
  short_bio: string | null;
  chunk_count: number;
  created_at: string;
}

/**
 * Full character profile detail.
 */
export interface CharacterProfile {
  id: string;
  character_id: string;
  cutoff_year: number;
  profile_status: string;
  profile_generated_at: string | null;
  profile_model_provider: string | null;
  profile_model_name: string | null;
  short_bio: string | null;
  role_summary: string | null;
  importance_score: number | null;
  chunk_count: number;
  created_at: string;
  updated_at: string;
  chunks?: CharacterChunk[];
}

/**
 * A historical figure character detected or created for a timeline.
 */
export interface Character {
  id: string;
  timeline_id: string;
  name: string;
  full_name: string | null;
  title: string | null;
  character_source: CharacterSource;
  user_provided_bio: string | null;
  birth_year: number | null;
  death_year: number | null;
  first_appearance_generation: number;
  last_known_year: number;
  profile_status: CharacterProfileStatus;
  profile_generated_at: string | null;
  profile_model_provider: string | null;
  profile_model_name: string | null;
  short_bio: string | null;
  role_summary: string | null;
  importance_score: number | null;
  profiles?: CharacterProfileSummary[];
  created_at: string;
  updated_at: string;
}

/**
 * A chunk of character profile knowledge.
 */
export interface CharacterChunk {
  id: string;
  chunk_type: CharacterChunkType;
  content: string;
  year_start: number | null;
  year_end: number | null;
  related_figures: string[];
  created_at: string;
}

/**
 * Character with optional profile chunks.
 */
export interface CharacterDetail extends Character {
  chunks?: CharacterChunk[];
}

/**
 * A chat session with a character.
 */
export interface ChatSession {
  id: string;
  character_id: string;
  timeline_id: string;
  character_year_context: number;
  profile_id?: string | null;
  session_name: string | null;
  is_active: boolean;
  message_count: number;
  created_at: string;
  updated_at: string;
  last_message_at: string | null;
}

/**
 * A single chat message within a session.
 */
export interface ChatMessage {
  id: string;
  session_id: string;
  role: ChatMessageRole;
  content: string;
  model_provider: string | null;
  model_name: string | null;
  generation_time_ms: number | null;
  retrieved_chunks: number | null;
  created_at: string;
}

/**
 * Request to create a custom character.
 */
export interface CreateCustomCharacterRequest {
  name: string;
  full_name?: string;
  title?: string;
  user_provided_bio: string;
  birth_year?: number;
  death_year?: number;
}

/**
 * Request to create a chat session.
 */
export interface CreateChatSessionRequest {
  character_year_context: number;
  profile_id?: string;
  session_name?: string;
}

/**
 * Response from character detection.
 */
export interface DetectCharactersResponse {
  timeline_id: string;
  detected_figures: string[];
  created_characters: number;
  characters: Character[];
}

/**
 * Response from profile generation.
 */
export interface GenerateProfileResponse {
  message: string;
  character_id: string;
  status: string;
  chunk_count: number;
  character: Character;
  profile?: CharacterProfile;
}

/**
 * Response from sending a chat message.
 */
export interface SendMessageResponse {
  user_message: ChatMessage;
  character_response: ChatMessage;
}

/**
 * Paginated chat messages response.
 */
export interface ChatMessagesResponse {
  messages: ChatMessage[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * Utility functions for character features.
 */
export const CharacterUtils = {
  /**
   * Get profile status badge color classes.
   */
  getProfileStatusColor: (status: CharacterProfileStatus): string => {
    switch (status) {
      case CharacterProfileStatus.PENDING:
        return 'text-gray-400 bg-gray-400/10';
      case CharacterProfileStatus.GENERATING:
        return 'text-amber-400 bg-amber-400/10';
      case CharacterProfileStatus.READY:
        return 'text-green-400 bg-green-400/10';
      case CharacterProfileStatus.ERROR:
        return 'text-red-400 bg-red-400/10';
      default:
        return 'text-gray-400 bg-gray-400/10';
    }
  },

  /**
   * Get human-readable profile status label.
   */
  getProfileStatusLabel: (status: CharacterProfileStatus): string => {
    switch (status) {
      case CharacterProfileStatus.PENDING:
        return 'Pending';
      case CharacterProfileStatus.GENERATING:
        return 'Generating...';
      case CharacterProfileStatus.READY:
        return 'Ready';
      case CharacterProfileStatus.ERROR:
        return 'Error';
      default:
        return 'Unknown';
    }
  },

  /**
   * Get human-readable chunk type label.
   */
  getChunkTypeLabel: (chunkType: CharacterChunkType): string => {
    const labels: Record<CharacterChunkType, string> = {
      biography: 'Biography',
      personality: 'Personality',
      relationships: 'Relationships',
      beliefs: 'Beliefs',
      speaking_style: 'Speaking Style',
      event_involvement: 'Event Involvement',
    };
    return labels[chunkType];
  },

  /**
   * Format character years display.
   */
  formatYears: (birthYear: number | null, deathYear: number | null): string => {
    if (birthYear && deathYear) return `${birthYear}–${deathYear}`;
    if (birthYear) return `b. ${birthYear}`;
    if (deathYear) return `d. ${deathYear}`;
    return '';
  },
};
// ============================================================================
// RIPPLE MAP TYPES
// ============================================================================

export type CausalDomain = 'political' | 'economic' | 'technological' | 'social' | 'cultural' | 'military';
export type ConfidenceLevel = 'high' | 'medium' | 'speculative';
export type EffectDuration = 'instant' | 'short_term' | 'long_term' | 'permanent';
export type CausalRelationship = 'causes' | 'enables' | 'prevents' | 'accelerates' | 'weakens' | 'transforms';
export type EdgeStrength = 'direct' | 'indirect' | 'subtle';
export type TimeDelay = 'immediate' | 'months' | 'years' | 'decades';

export interface CausalNode {
  id: string;
  label: string;
  description: string;
  domain: CausalDomain;
  sub_domain: string;
  magnitude: number;
  confidence: ConfidenceLevel;
  time_offset_years: number;
  duration: EffectDuration;
  affected_regions: string[];
  key_figures: string[];
  is_deviation_point: boolean;
  source_generation_id: string;
}

export interface CausalEdge {
  source_node_id: string;
  target_node_id: string;
  relationship: CausalRelationship;
  strength: EdgeStrength;
  description: string;
  time_delay: TimeDelay;
}

export interface RippleMap {
  id: string;
  timeline_id: string;
  nodes: CausalNode[];
  edges: CausalEdge[];
  included_generation_ids: string[];
  total_nodes: number;
  dominant_domain: string | null;
  max_ripple_depth: number;
  model_provider: string | null;
  model_name: string | null;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// NotebookLM Studio Integration Types
// ============================================================================

export type NLMAudioFormat = 'deep_dive' | 'brief' | 'critique' | 'debate';
export type NLMAudioLength = 'short' | 'default' | 'long';
export type NLMJobStatus =
  | 'pending'
  | 'creating'
  | 'uploading'
  | 'generating'
  | 'polling'
  | 'completed'
  | 'failed';

export const NLM_FORMAT_LABELS: Record<NLMAudioFormat, string> = {
  deep_dive: 'Deep Dive',
  brief: 'Brief Overview',
  critique: 'Critical Analysis',
  debate: 'Debate',
};

export const NLM_LENGTH_LABELS: Record<NLMAudioLength, string> = {
  short: 'Short (~5 min)',
  default: 'Standard (~10 min)',
  long: 'Long (~20 min)',
};

export const NLM_STATUS_LABELS: Record<NLMJobStatus, string> = {
  pending: 'Queued',
  creating: 'Creating notebook…',
  uploading: 'Uploading sources…',
  generating: 'Requesting generation…',
  polling: 'NotebookLM is working…',
  completed: 'Ready',
  failed: 'Failed',
};

export interface NotebookLMGenerateRequest {
  generation_ids: string[];
  timeline_id?: string;
  content_type?: 'audio';
  nlm_format: NLMAudioFormat;
  nlm_length: NLMAudioLength;
  nlm_focus?: string;
  language_code: string;
  include_reports: boolean;
  include_narratives: boolean;
}

export interface NotebookLMJob {
  id: string;
  timeline_id?: string;
  generation_ids: string[];
  notebook_id?: string;
  artifact_id?: string;
  content_type: string;
  nlm_format: NLMAudioFormat;
  nlm_length: NLMAudioLength;
  nlm_focus?: string;
  language_code: string;
  status: NLMJobStatus;
  error_message?: string;
  audio_url?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  updated_at: string;
}

export interface NLMAvailabilityResponse {
  available: boolean;
  authenticated: boolean;
  error?: string;
}

// ── Novella ──────────────────────────────────────────────────────────────────

export interface TimelineNovella {
  id: string;
  timeline_id: string;
  series_id: string | null;
  series_order: number;
  generation_ids: string[];
  title: string;
  content: string;
  focus_instructions: string | null;
  model_provider: string;
  model_name: string;
  created_at: string;
}

export interface NovellaGenerateRequest {
  generation_ids: string[];
  focus_instructions?: string;
}

export interface NovellaContinueRequest {
  generation_ids: string[];
  focus_instructions?: string;
}
