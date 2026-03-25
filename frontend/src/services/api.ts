/**
 * API service for communicating with the Deviation Engine backend.
 *
 * This module provides a type-safe interface for all backend API calls
 * with proper error handling and response transformation.
 */

import axios from 'axios';
import type { AxiosError, AxiosInstance } from 'axios';
import type {
  TimelineCreationRequest,
  Timeline,
  TimelineListItem,
  TimelineExtensionRequest,
  TimelineBranchRequest,
  HealthResponse,
  ErrorResponse,
  ApiResponse,
  LLMConfig,
  LLMConfigRequest,
  AvailableModels,
  Skeleton,
  SkeletonGenerationRequest,
  SkeletonEventsUpdateRequest,
  GenerateFromSkeletonRequest,
  AgentType,
  AgentLLMConfig,
  AgentLLMConfigRequest,
  AllLLMConfigs,
  AgentUsesGlobalResponse,
  ImagePromptSkeleton,
  ImagePromptSkeletonUpdate,
  TimelineImage,
  TranslationResponse,
  NarrativeTranslationResponse,
  TranslationUsage,
  TranslationConfig,
  TranslationConfigRequest,
  SupportedLanguage,
  DebugSettings,
  DebugSettingsUpdate,
  PurgeDataResponse,
  Character,
  CharacterDetail,
  ChatSession,
  ChatMessage,
  CreateCustomCharacterRequest,
  CreateChatSessionRequest,
  DetectCharactersResponse,
  GenerateProfileResponse,
  SendMessageResponse,
  ChatMessagesResponse,
  CharacterProfile,
} from '../types';

/**
 * Base API URL from environment variables.
 * Defaults to localhost:8000 for development.
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Configured axios instance with base URL and common settings.
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes - AI generation can take time
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Transform axios errors into our standard ErrorResponse format.
 */
function handleApiError(error: unknown): ErrorResponse {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<any>;

    // If backend returned an error response
    if (axiosError.response?.data) {
      const data = axiosError.response.data;

      // Handle FastAPI's HTTPException format (uses 'detail' instead of 'message')
      if (data.detail) {
        return {
          error: 'APIError',
          message: data.detail,
        };
      }

      // Handle our custom error format
      if (data.error || data.message) {
        return data;
      }
    }

    // Network or timeout errors
    if (axiosError.code === 'ECONNABORTED') {
      return {
        error: 'TimeoutError',
        message: 'Request timed out. Timeline generation may take up to 2 minutes.',
      };
    }

    if (axiosError.code === 'ERR_NETWORK') {
      return {
        error: 'NetworkError',
        message: 'Unable to connect to the server. Please ensure the backend is running.',
      };
    }

    // Generic axios error
    return {
      error: 'RequestError',
      message: axiosError.message || 'An error occurred while communicating with the server.',
    };
  }

  // Non-axios error
  return {
    error: 'UnknownError',
    message: 'An unexpected error occurred.',
  };
}

/**
 * Generate a new alternate history timeline.
 *
 * @param request - Timeline creation parameters
 * @returns Promise resolving to the generated timeline or error
 */
export async function generateTimeline(
  request: TimelineCreationRequest
): Promise<ApiResponse<Timeline>> {
  try {
    const response = await apiClient.post<Timeline>('/api/generate-timeline', request);

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Retrieve a list of all generated timelines.
 *
 * @returns Promise resolving to array of timeline summaries or error
 */
export async function getTimelines(): Promise<ApiResponse<TimelineListItem[]>> {
  try {
    const response = await apiClient.get<TimelineListItem[]>('/api/timelines');

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Retrieve a specific timeline by ID.
 *
 * @param timelineId - UUID of the timeline to retrieve
 * @returns Promise resolving to the complete timeline or error
 */
export async function getTimeline(
  timelineId: string
): Promise<ApiResponse<Timeline>> {
  try {
    const response = await apiClient.get<Timeline>(`/api/timeline/${timelineId}`);

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Delete a specific timeline.
 *
 * @param timelineId - UUID of the timeline to delete
 * @returns Promise resolving to success status or error
 */
export async function deleteTimeline(
  timelineId: string
): Promise<ApiResponse<void>> {
  try {
    const response = await apiClient.delete(`/api/timeline/${timelineId}`);

    return {
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Delete a specific generation from a timeline.
 *
 * @param timelineId - UUID of the timeline containing the generation
 * @param generationId - UUID of the generation to delete
 * @returns Promise resolving to success status or error
 */
export async function deleteGeneration(
  timelineId: string,
  generationId: string
): Promise<ApiResponse<void>> {
  try {
    const response = await apiClient.delete(`/api/timeline/${timelineId}/generation/${generationId}`);

    return {
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * @deprecated Use deleteGeneration instead. Kept for backwards compatibility.
 */
export const deleteReport = deleteGeneration;

/**
 * Extend an existing timeline by additional years.
 *
 * @param request - Extension parameters including timeline ID and additional years
 * @returns Promise resolving to the updated timeline or error
 */
export async function extendTimeline(
  request: TimelineExtensionRequest
): Promise<ApiResponse<Timeline>> {
  try {
    const response = await apiClient.post<Timeline>('/api/extend-timeline', request);

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Create a branch timeline from an existing timeline.
 *
 * @param request - Branch parameters including source timeline ID, branch point, and deviation
 * @returns Promise resolving to the new branched timeline or error
 */
export async function branchTimeline(
  request: TimelineBranchRequest
): Promise<ApiResponse<Timeline>> {
  try {
    const response = await apiClient.post<Timeline>('/api/branch-timeline', request);

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Check API health status.
 *
 * @returns Promise resolving to health information or error
 */
export async function checkHealth(): Promise<ApiResponse<HealthResponse>> {
  try {
    const response = await apiClient.get<HealthResponse>('/api/health');

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Get current LLM configuration.
 *
 * @returns Promise resolving to current LLM configuration or error
 */
export async function getLLMConfig(): Promise<ApiResponse<LLMConfig>> {
  try {
    const response = await apiClient.get<LLMConfig>('/api/llm-config');

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Update LLM configuration.
 *
 * @param config - New LLM configuration (provider, model, API keys)
 * @returns Promise resolving to updated configuration or error
 */
export async function updateLLMConfig(
  config: LLMConfigRequest
): Promise<ApiResponse<LLMConfig>> {
  try {
    const response = await apiClient.put<LLMConfig>('/api/llm-config', config);

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Get available models for each provider.
 *
 * @returns Promise resolving to lists of available models or error
 */
export async function getAvailableModels(): Promise<ApiResponse<AvailableModels>> {
  try {
    const response = await apiClient.get<AvailableModels>('/api/llm-models');

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * ============================================================================
 * Debug Settings API Functions
 * ============================================================================
 */

/**
 * Get current debug settings.
 *
 * @returns Promise resolving to current debug settings or error
 */
export async function getDebugSettings(): Promise<ApiResponse<DebugSettings>> {
  try {
    const response = await apiClient.get<DebugSettings>('/api/debug-settings');

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Update debug settings.
 *
 * @param settings - New debug settings
 * @returns Promise resolving to updated settings or error
 */
export async function updateDebugSettings(
  settings: DebugSettingsUpdate
): Promise<ApiResponse<DebugSettings>> {
  try {
    const response = await apiClient.put<DebugSettings>('/api/debug-settings', settings);

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * ⚠️ DANGER: Purge all user-generated data from the system.
 *
 * This removes all timelines, skeleton drafts, generations, audio, images, and vector data.
 * Only configuration settings and (optionally) ground truth data are preserved.
 *
 * @param preserveGroundTruth - If true, preserve ground truth historical data (default: true)
 * @returns Promise resolving to purge statistics or error
 */
export async function purgeAllData(
  preserveGroundTruth: boolean = true
): Promise<ApiResponse<PurgeDataResponse>> {
  try {
    const response = await apiClient.post<PurgeDataResponse>(
      '/api/purge-data',
      null,
      { params: { preserve_ground_truth: preserveGroundTruth } }
    );

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * ============================================================================
 * Skeleton Timeline API Functions (NEW)
 * ============================================================================
 */

/**
 * Generate a skeleton timeline with key events.
 *
 * @param request - Skeleton generation parameters
 * @returns Promise resolving to the generated skeleton or error
 */
export async function generateSkeleton(
  request: SkeletonGenerationRequest
): Promise<ApiResponse<Skeleton>> {
  try {
    const response = await apiClient.post<Skeleton>('/api/generate-skeleton', request);

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Retrieve a skeleton by ID.
 *
 * @param skeletonId - UUID of the skeleton to retrieve
 * @returns Promise resolving to the skeleton or error
 */
export async function getSkeleton(
  skeletonId: string
): Promise<ApiResponse<Skeleton>> {
  try {
    const response = await apiClient.get<Skeleton>(`/api/skeleton/${skeletonId}`);

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Update skeleton events (create, update, delete).
 *
 * @param skeletonId - UUID of the skeleton to update
 * @param request - Events to update and delete
 * @returns Promise resolving to the updated skeleton or error
 */
export async function updateSkeletonEvents(
  skeletonId: string,
  request: SkeletonEventsUpdateRequest
): Promise<ApiResponse<Skeleton>> {
  try {
    const response = await apiClient.put<Skeleton>(
      `/api/skeleton/${skeletonId}/events`,
      request
    );

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Approve a skeleton for report generation.
 *
 * @param skeletonId - UUID of the skeleton to approve
 * @returns Promise resolving to the approved skeleton or error
 */
export async function approveSkeleton(
  skeletonId: string
): Promise<ApiResponse<Skeleton>> {
  try {
    const response = await apiClient.post<Skeleton>(
      `/api/skeleton/${skeletonId}/approve`
    );

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Generate a full timeline report from an approved skeleton.
 *
 * @param request - Skeleton ID and narrative preferences
 * @returns Promise resolving to the generated timeline or error
 */
export async function generateFromSkeleton(
  request: GenerateFromSkeletonRequest
): Promise<ApiResponse<Timeline>> {
  try {
    const response = await apiClient.post<Timeline>(
      '/api/generate-from-skeleton',
      request
    );

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Get all skeleton timelines sorted by created date (newest first).
 *
 * @returns Promise resolving to list of all skeletons or error
 */
export async function getSkeletons(): Promise<ApiResponse<Skeleton[]>> {
  try {
    const response = await apiClient.get<Skeleton[]>('/api/skeletons');

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Delete a skeleton and all its events.
 *
 * @param skeletonId - UUID of the skeleton to delete
 * @returns Promise resolving to success status or error
 */
export async function deleteSkeleton(
  skeletonId: string
): Promise<ApiResponse<void>> {
  try {
    const response = await apiClient.delete(`/api/skeleton/${skeletonId}`);

    return {
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Get skeleton events snapshot from a timeline or specific generation.
 *
 * @param timelineId - UUID of the timeline
 * @param generationId - Optional UUID of specific generation (if not provided, returns timeline-level skeleton)
 * @returns Promise resolving to skeleton snapshot or error
 */
export async function getTimelineSkeletonSnapshot(
  timelineId: string,
  generationId?: string
): Promise<ApiResponse<{
  timeline_id: string;
  generation_id?: string;
  skeleton_id: string;
  events: any[];
  snapshot_created_at: string;
}>> {
  try {
    const url = generationId
      ? `/api/timelines/${timelineId}/skeleton-snapshot?generation_id=${generationId}`
      : `/api/timelines/${timelineId}/skeleton-snapshot`;

    const response = await apiClient.get(url);

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Generate an extension skeleton for an existing timeline.
 *
 * Creates a temporary skeleton with key events for timeline extension
 * that can be reviewed and edited before generating the full report.
 *
 * @param timelineId - UUID of the timeline to extend
 * @param additionalYears - Number of additional years to simulate
 * @param additionalContext - Optional additional information or guidance
 * @returns Promise resolving to the generated extension skeleton or error
 */
export async function generateExtensionSkeleton(
  timelineId: string,
  additionalYears: number,
  additionalContext?: string
): Promise<ApiResponse<Skeleton>> {
  try {
    const response = await apiClient.post<Skeleton>('/api/generate-extension-skeleton', {
      timeline_id: timelineId,
      additional_years: additionalYears,
      additional_context: additionalContext || undefined,
    });

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Extend a timeline from an approved extension skeleton.
 *
 * Takes a user-approved extension skeleton and generates a comprehensive
 * extension report that is added to the parent timeline.
 *
 * @param timelineId - UUID of the timeline to extend
 * @param skeletonId - UUID of the approved extension skeleton
 * @param narrativeMode - Mode for narrative generation
 * @param narrativeCustomPov - Custom perspective instructions (for ADVANCED_CUSTOM_POV mode)
 * @returns Promise resolving to the updated timeline or error
 */
export async function extendFromSkeleton(
  timelineId: string,
  skeletonId: string,
  narrativeMode: string,
  narrativeCustomPov?: string
): Promise<ApiResponse<Timeline>> {
  try {
    const response = await apiClient.post<Timeline>('/api/extend-from-skeleton', {
      timeline_id: timelineId,
      skeleton_id: skeletonId,
      narrative_mode: narrativeMode,
      narrative_custom_pov: narrativeCustomPov || undefined,
    });

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * ============================================================================
 * Per-Agent LLM Configuration API Functions (NEW)
 * ============================================================================
 */

/**
 * Get all LLM configurations (global + per-agent).
 *
 * Retrieves the global LLM configuration and any agent-specific overrides.
 *
 * @returns Promise resolving to all LLM configurations or error
 */
export async function getAllLLMConfigs(): Promise<ApiResponse<AllLLMConfigs>> {
  try {
    const response = await apiClient.get<AllLLMConfigs>('/api/llm/agents');

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Get LLM configuration for a specific agent.
 *
 * Returns the agent-specific config if it exists, otherwise indicates
 * the agent uses the global configuration.
 *
 * @param agentType - Type of agent to get config for
 * @returns Promise resolving to agent config or "uses global" response
 */
export async function getAgentLLMConfig(
  agentType: AgentType
): Promise<ApiResponse<AgentLLMConfig | AgentUsesGlobalResponse>> {
  try {
    const response = await apiClient.get<AgentLLMConfig | AgentUsesGlobalResponse>(
      `/api/llm/agents/${agentType}`
    );

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Set or update LLM configuration for a specific agent.
 *
 * Creates or updates an agent-specific LLM configuration override.
 * The agent will use this configuration instead of the global one.
 *
 * @param agentType - Type of agent to configure
 * @param config - Agent LLM configuration
 * @returns Promise resolving to the created/updated configuration or error
 */
export async function setAgentLLMConfig(
  agentType: AgentType,
  config: AgentLLMConfigRequest
): Promise<ApiResponse<AgentLLMConfig>> {
  try {
    const response = await apiClient.post<AgentLLMConfig>(
      `/api/llm/agents/${agentType}`,
      config
    );

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Delete agent-specific LLM configuration.
 *
 * Removes the agent-specific override, causing the agent to use
 * the global LLM configuration.
 *
 * @param agentType - Type of agent to remove config for
 * @returns Promise resolving to success status or error
 */
export async function deleteAgentLLMConfig(
  agentType: AgentType
): Promise<ApiResponse<void>> {
  try {
    const response = await apiClient.delete(`/api/llm/agents/${agentType}`);

    return {
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * ============================================================================
 * Image Generation API Functions (NEW)
 * ============================================================================
 */

/**
 * Generate image prompt skeleton for a timeline.
 *
 * Creates an editable skeleton of AI-generated image prompts that can be
 * reviewed and modified before generating actual images.
 *
 * @param timelineId - UUID of the timeline
 * @param generationId - Optional UUID of specific generation
 * @param numImages - Number of images to generate (3-20)
 * @param focusAreas - Optional focus areas (e.g., ["political", "economic"])
 * @returns Promise resolving to the generated skeleton or error
 */
export async function generateImagePrompts(
  timelineId: string,
  generationId: string | null,
  numImages: number,
  focusAreas: string[] | null
): Promise<ApiResponse<ImagePromptSkeleton>> {
  try {
    const response = await apiClient.post<ImagePromptSkeleton>(
      '/api/image-prompts/generate',
      {
        timeline_id: timelineId,
        generation_id: generationId,
        num_images: numImages,
        focus_areas: focusAreas,
      }
    );

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Get an image prompt skeleton by ID.
 *
 * @param skeletonId - UUID of the skeleton to retrieve
 * @returns Promise resolving to the skeleton or error
 */
export async function getImagePromptSkeleton(
  skeletonId: string
): Promise<ApiResponse<ImagePromptSkeleton>> {
  try {
    const response = await apiClient.get<ImagePromptSkeleton>(
      `/api/image-prompts/${skeletonId}`
    );

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Get all image prompt skeletons for a timeline.
 *
 * @param timelineId - UUID of the timeline
 * @returns Promise resolving to list of skeletons or error
 */
export async function getTimelineImagePrompts(
  timelineId: string
): Promise<ApiResponse<ImagePromptSkeleton[]>> {
  try {
    const response = await apiClient.get<ImagePromptSkeleton[]>(
      `/api/timelines/${timelineId}/image-prompts`
    );

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Update image prompts (create, update, delete).
 *
 * @param skeletonId - UUID of the skeleton to update
 * @param request - Prompts to update and delete
 * @returns Promise resolving to the updated skeleton or error
 */
export async function updateImagePrompts(
  skeletonId: string,
  request: ImagePromptSkeletonUpdate
): Promise<ApiResponse<ImagePromptSkeleton>> {
  try {
    const response = await apiClient.put<ImagePromptSkeleton>(
      `/api/image-prompts/${skeletonId}`,
      request
    );

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Approve an image prompt skeleton for image generation.
 *
 * @param skeletonId - UUID of the skeleton to approve
 * @returns Promise resolving to the approved skeleton or error
 */
export async function approveImagePromptSkeleton(
  skeletonId: string
): Promise<ApiResponse<ImagePromptSkeleton>> {
  try {
    const response = await apiClient.post<ImagePromptSkeleton>(
      `/api/image-prompts/${skeletonId}/approve`
    );

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Generate actual images from an approved skeleton.
 *
 * Uses pollinations.ai to generate images based on the prompts.
 *
 * @param skeletonId - UUID of the approved skeleton
 * @returns Promise resolving to list of generated images or error
 */
export async function generateImages(
  skeletonId: string
): Promise<ApiResponse<TimelineImage[]>> {
  try {
    const response = await apiClient.post<TimelineImage[]>(
      '/api/images/generate',
      {
        skeleton_id: skeletonId,
      }
    );

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Get all images for a timeline, optionally filtered by generation.
 *
 * @param timelineId - UUID of the timeline
 * @param generationId - Optional UUID of specific generation
 * @returns Promise resolving to list of images or error
 */
export async function getTimelineImages(
  timelineId: string,
  generationId?: string
): Promise<ApiResponse<TimelineImage[]>> {
  try {
    const url = generationId
      ? `/api/timelines/${timelineId}/images?generation_id=${generationId}`
      : `/api/timelines/${timelineId}/images`;

    const response = await apiClient.get<TimelineImage[]>(url);

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Delete a timeline image.
 *
 * @param imageId - UUID of the image to delete
 * @returns Promise resolving to success status or error
 */
export async function deleteTimelineImage(
  imageId: string
): Promise<ApiResponse<void>> {
  try {
    const response = await apiClient.delete(`/api/images/${imageId}`);

    return {
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Delete an image prompt skeleton.
 *
 * @param skeletonId - UUID of the skeleton to delete
 * @returns Promise resolving to success status or error
 */
export async function deleteImagePromptSkeleton(
  skeletonId: string
): Promise<ApiResponse<void>> {
  try {
    const response = await apiClient.delete(`/api/image-prompts/${skeletonId}`);

    return {
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * ============================================================================
 * Export/Import API Functions (NEW)
 * ============================================================================
 */

/**
 * Export a timeline as a .devtl file.
 *
 * Downloads the timeline as a portable JSON file that can be imported
 * into any Deviation Engine installation.
 *
 * @param timelineId - UUID of the timeline to export
 * @returns Promise resolving to blob data and filename or error
 */
export async function exportTimeline(
  timelineId: string
): Promise<ApiResponse<{ blob: Blob; filename: string }>> {
  try {
    const response = await apiClient.get(`/api/timeline/${timelineId}/export`, {
      responseType: 'blob',
    });

    // Extract filename from Content-Disposition header
    const contentDisposition = response.headers['content-disposition'];
    let filename = 'timeline.devtl';

    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1];
      }
    }

    return {
      data: {
        blob: response.data,
        filename: filename,
      },
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Import a timeline from a .devtl file.
 *
 * Uploads and validates a .devtl file, creating a new timeline with
 * a new UUID. All reports and skeleton snapshots are preserved.
 *
 * @param file - The .devtl file to import
 * @returns Promise resolving to the newly created timeline or error
 */
export async function importTimeline(
  file: File
): Promise<ApiResponse<Timeline>> {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<Timeline>('/api/timeline/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/* ============================================================================
 * Translation API Functions
 * ============================================================================
 */

/**
 * Translate all sections of a generation to a target language.
 *
 * @param generationId - UUID of the generation to translate
 * @param targetLanguage - Target language code (e.g., 'hu', 'de', 'es', 'it')
 * @param method - Translation method (deepl or llm)
 * @returns Promise resolving to translation response or error
 */
export async function translateGeneration(
  generationId: string,
  targetLanguage: SupportedLanguage,
  method: 'deepl' | 'llm' = 'deepl'
): Promise<ApiResponse<TranslationResponse>> {
  try {
    const response = await apiClient.post<TranslationResponse>(
      `/api/generations/${generationId}/translate`,
      {
        target_language: targetLanguage,
        method: method,
      }
    );

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Translate narrative prose of a generation to a target language.
 *
 * @param generationId - UUID of the generation
 * @param targetLanguage - Target language code
 * @param method - Translation method (deepl or llm)
 * @returns Promise resolving to narrative translation or error
 */
export async function translateNarrative(
  generationId: string,
  targetLanguage: SupportedLanguage,
  method: 'deepl' | 'llm' = 'deepl'
): Promise<ApiResponse<NarrativeTranslationResponse>> {
  try {
    const response = await apiClient.post<NarrativeTranslationResponse>(
      `/api/generations/${generationId}/narrative/translate`,
      {
        target_language: targetLanguage,
        method: method,
      }
    );

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Delete a generation translation (report or narrative).
 *
 * @param generationId - UUID of the generation
 * @param languageCode - Target language code
 * @param contentType - Content type (report or narrative)
 * @returns Promise resolving to void or error
 */
export async function deleteGenerationTranslation(
  generationId: string,
  languageCode: string,
  contentType: 'report' | 'narrative'
): Promise<ApiResponse<void>> {
  try {
    const response = await apiClient.delete(
      `/api/generations/${generationId}/translations/${languageCode}`,
      {
        params: { content_type: contentType },
      }
    );

    return {
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Get translation usage statistics for a specific month.
 *
 * @param month - Optional month in YYYY-MM format (defaults to current month)
 * @returns Promise resolving to usage statistics or error
 */
export async function getTranslationUsage(
  month?: string
): Promise<ApiResponse<TranslationUsage>> {
  try {
    const params = month ? { month } : {};
    const response = await apiClient.get<TranslationUsage>(
      '/api/translation/usage',
      { params }
    );

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Get translation service configuration.
 *
 * @returns Promise resolving to translation config or error
 */
export async function getTranslationConfig(): Promise<ApiResponse<TranslationConfig>> {
  try {
    const response = await apiClient.get<TranslationConfig>('/api/translation/config');

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Update translation service configuration.
 *
 * @param config - Translation configuration request
 * @returns Promise resolving to updated config or error
 */
export async function updateTranslationConfig(
  config: TranslationConfigRequest
): Promise<ApiResponse<TranslationConfig>> {
  try {
    const response = await apiClient.put<TranslationConfig>(
      '/api/translation/config',
      config
    );

    return {
      data: response.data,
      status: response.status,
    };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * ============================================================================
 * Character & Chat API Functions
 * ============================================================================
 */

/**
 * List all characters for a timeline.
 */
export async function listCharacters(
  timelineId: string
): Promise<ApiResponse<Character[]>> {
  try {
    const response = await apiClient.get<Character[]>(
      `/api/timelines/${timelineId}/characters`
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Detect characters from timeline content.
 */
export async function detectCharacters(
  timelineId: string
): Promise<ApiResponse<DetectCharactersResponse>> {
  try {
    const response = await apiClient.post<DetectCharactersResponse>(
      `/api/timelines/${timelineId}/characters/detect`
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Create a custom character for a timeline.
 */
export async function createCustomCharacter(
  timelineId: string,
  request: CreateCustomCharacterRequest
): Promise<ApiResponse<Character>> {
  try {
    const response = await apiClient.post<Character>(
      `/api/timelines/${timelineId}/characters/custom`,
      request
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Generate a character profile.
 */
export async function generateCharacterProfile(
  characterId: string,
  cutoffYear?: number
): Promise<ApiResponse<GenerateProfileResponse>> {
  try {
    const body = cutoffYear !== undefined ? { cutoff_year: cutoffYear } : {};
    const response = await apiClient.post<GenerateProfileResponse>(
      `/api/characters/${characterId}/generate-profile`,
      body
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Get character details with optional chunks.
 */
export async function getCharacter(
  characterId: string,
  includeChunks?: boolean
): Promise<ApiResponse<CharacterDetail>> {
  try {
    const params = includeChunks ? { include_chunks: true } : {};
    const response = await apiClient.get<CharacterDetail>(
      `/api/characters/${characterId}`,
      { params }
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * List all profiles for a character.
 */
export async function listCharacterProfiles(
  characterId: string
): Promise<ApiResponse<CharacterProfile[]>> {
  try {
    const response = await apiClient.get<CharacterProfile[]>(
      `/api/characters/${characterId}/profiles`
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Get a specific character profile with chunks.
 */
export async function getCharacterProfile(
  characterId: string,
  profileId: string
): Promise<ApiResponse<CharacterProfile>> {
  try {
    const response = await apiClient.get<CharacterProfile>(
      `/api/characters/${characterId}/profiles/${profileId}`
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Delete a character profile.
 */
export async function deleteCharacterProfile(
  characterId: string,
  profileId: string
): Promise<ApiResponse<{ message: string; profile_id: string }>> {
  try {
    const response = await apiClient.delete<{ message: string; profile_id: string }>(
      `/api/characters/${characterId}/profiles/${profileId}`
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Delete a character.
 */
export async function deleteCharacter(
  characterId: string
): Promise<ApiResponse<{ message: string; character_id: string }>> {
  try {
    const response = await apiClient.delete<{ message: string; character_id: string }>(
      `/api/characters/${characterId}`
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Delete all auto-detected characters without a ready profile for a timeline.
 */
export async function deleteUnprofiledCharacters(
  timelineId: string
): Promise<ApiResponse<{ message: string; deleted: number }>> {
  try {
    const response = await apiClient.delete<{ message: string; deleted: number }>(
      `/api/timelines/${timelineId}/characters/unprofiled`
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Create a chat session with a character.
 */
export async function createChatSession(
  characterId: string,
  request: CreateChatSessionRequest
): Promise<ApiResponse<ChatSession>> {
  try {
    const response = await apiClient.post<ChatSession>(
      `/api/characters/${characterId}/chat/sessions`,
      request
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Get a chat session by ID.
 */
export async function getChatSession(
  sessionId: string
): Promise<ApiResponse<ChatSession>> {
  try {
    const response = await apiClient.get<ChatSession>(
      `/api/chat/sessions/${sessionId}`
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Send a message in a chat session.
 */
export async function sendChatMessage(
  sessionId: string,
  message: string
): Promise<ApiResponse<SendMessageResponse>> {
  try {
    const response = await apiClient.post<SendMessageResponse>(
      `/api/chat/sessions/${sessionId}/messages`,
      { message }
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Get messages for a chat session.
 */
export async function getChatMessages(
  sessionId: string,
  limit?: number,
  offset?: number
): Promise<ApiResponse<ChatMessagesResponse>> {
  try {
    const params: Record<string, number> = {};
    if (limit !== undefined) params.limit = limit;
    if (offset !== undefined) params.offset = offset;
    const response = await apiClient.get<ChatMessagesResponse>(
      `/api/chat/sessions/${sessionId}/messages`,
      { params }
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Get all chat sessions for a timeline.
 */
export async function getTimelineChatSessions(
  timelineId: string
): Promise<ApiResponse<ChatSession[]>> {
  try {
    const response = await apiClient.get<ChatSession[]>(
      `/api/timelines/${timelineId}/chat/sessions`
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Close a chat session.
 */
export async function closeChatSession(
  sessionId: string
): Promise<ApiResponse<ChatSession>> {
  try {
    const response = await apiClient.post<ChatSession>(
      `/api/chat/sessions/${sessionId}/close`
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Delete a chat session.
 */
export async function deleteChatSession(
  sessionId: string
): Promise<ApiResponse<{ message: string; session_id: string }>> {
  try {
    const response = await apiClient.delete<{ message: string; session_id: string }>(
      `/api/chat/sessions/${sessionId}`
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Export a chat session as markdown.
 */
export async function exportChatSession(
  sessionId: string
): Promise<ApiResponse<string>> {
  try {
    const response = await apiClient.get<string>(
      `/api/chat/sessions/${sessionId}/export`,
      { responseType: 'text' as any }
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Regenerate the last character response.
 */
export async function regenerateChatResponse(
  sessionId: string
): Promise<ApiResponse<ChatMessage>> {
  try {
    const response = await apiClient.post<ChatMessage>(
      `/api/chat/sessions/${sessionId}/regenerate`
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return {
      error: errorResponse,
      status: axios.isAxiosError(error) ? error.response?.status || 500 : 500,
    };
  }
}

/**
 * Export all API functions.
 */
export const api = {
  // Timeline Core API functions
  generateTimeline,
  getTimelines,
  getTimeline,
  deleteTimeline,
  deleteGeneration,
  deleteReport, // deprecated alias
  extendTimeline,
  branchTimeline, // NEW: Branching feature
  checkHealth,
  // LLM Configuration API functions
  getLLMConfig,
  updateLLMConfig,
  getAvailableModels,
  // Per-Agent LLM Configuration API functions
  getAllLLMConfigs,
  getAgentLLMConfig,
  setAgentLLMConfig,
  deleteAgentLLMConfig,
  // Skeleton API functions
  generateSkeleton,
  getSkeletons,
  getSkeleton,
  updateSkeletonEvents,
  approveSkeleton,
  generateFromSkeleton,
  deleteSkeleton,
  getTimelineSkeletonSnapshot,
  // Extension Skeleton API functions
  generateExtensionSkeleton,
  extendFromSkeleton,
  // Image Generation API functions
  generateImagePrompts,
  getImagePromptSkeleton,
  getTimelineImagePrompts,
  updateImagePrompts,
  approveImagePromptSkeleton,
  generateImages,
  getTimelineImages,
  deleteTimelineImage,
  deleteImagePromptSkeleton,
  // Export/Import API functions
  exportTimeline,
  importTimeline,
  // Translation API functions
  translateGeneration,
  translateNarrative,
  deleteGenerationTranslation,
  getTranslationUsage,
  getTranslationConfig,
  updateTranslationConfig,
  // Character & Chat API functions
  listCharacters,
  detectCharacters,
  createCustomCharacter,
  generateCharacterProfile,
  getCharacter,
  listCharacterProfiles,
  getCharacterProfile,
  deleteCharacter,
  createChatSession,
  getChatSession,
  sendChatMessage,
  getChatMessages,
  getTimelineChatSessions,
  closeChatSession,
  deleteChatSession,
  regenerateChatResponse,
  exportChatSession,
  generateRippleMap,
  getRippleMap,
  addGenerationsToRippleMap,
};

// ── Ripple Map ────────────────────────────────────────────────────────────────

import type { RippleMap } from '../types';

export async function generateRippleMap(
  timelineId: string,
  generationIds: string[]
): Promise<ApiResponse<RippleMap>> {
  try {
    const response = await apiClient.post<RippleMap>(
      `/api/timelines/${timelineId}/ripple-map`,
      { generation_ids: generationIds }
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return { error: errorResponse, status: axios.isAxiosError(error) ? error.response?.status || 500 : 500 };
  }
}

export async function getRippleMap(
  timelineId: string
): Promise<ApiResponse<RippleMap | null>> {
  try {
    const response = await apiClient.get<RippleMap>(`/api/timelines/${timelineId}/ripple-map`);
    return { data: response.data, status: response.status };
  } catch (error) {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      return { data: null, status: 404 };
    }
    const errorResponse = handleApiError(error);
    return { error: errorResponse, status: axios.isAxiosError(error) ? error.response?.status || 500 : 500 };
  }
}

export async function addGenerationsToRippleMap(
  timelineId: string,
  generationIds: string[]
): Promise<ApiResponse<RippleMap>> {
  try {
    const response = await apiClient.post<RippleMap>(
      `/api/timelines/${timelineId}/ripple-map/add-generations`,
      { generation_ids: generationIds }
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return { error: errorResponse, status: axios.isAxiosError(error) ? error.response?.status || 500 : 500 };
  }
}

export default api;

// ── Novella API ───────────────────────────────────────────────────────────────

import type { TimelineNovella, NovellaGenerateRequest, NovellaContinueRequest } from '../types';

export async function generateNovella(
  timelineId: string,
  request: NovellaGenerateRequest
): Promise<ApiResponse<TimelineNovella>> {
  try {
    const response = await apiClient.post<TimelineNovella>(
      `/api/timelines/${timelineId}/novellas`,
      request
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return { error: errorResponse, status: axios.isAxiosError(error) ? error.response?.status || 500 : 500 };
  }
}

export async function continueNovella(
  novellaId: string,
  request: NovellaContinueRequest
): Promise<ApiResponse<TimelineNovella>> {
  try {
    const response = await apiClient.post<TimelineNovella>(
      `/api/novellas/${novellaId}/continue`,
      request
    );
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return { error: errorResponse, status: axios.isAxiosError(error) ? error.response?.status || 500 : 500 };
  }
}

export async function getTimelineNovellas(
  timelineId: string
): Promise<ApiResponse<TimelineNovella[]>> {
  try {
    const response = await apiClient.get<TimelineNovella[]>(`/api/timelines/${timelineId}/novellas`);
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return { error: errorResponse, status: axios.isAxiosError(error) ? error.response?.status || 500 : 500 };
  }
}

export async function getNovellaSeries(
  novellaId: string
): Promise<ApiResponse<TimelineNovella[]>> {
  try {
    const response = await apiClient.get<TimelineNovella[]>(`/api/novellas/${novellaId}/series`);
    return { data: response.data, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return { error: errorResponse, status: axios.isAxiosError(error) ? error.response?.status || 500 : 500 };
  }
}

export async function deleteNovella(
  novellaId: string
): Promise<ApiResponse<void>> {
  try {
    const response = await apiClient.delete(`/api/novellas/${novellaId}`);
    return { data: undefined, status: response.status };
  } catch (error) {
    const errorResponse = handleApiError(error);
    return { error: errorResponse, status: axios.isAxiosError(error) ? error.response?.status || 500 : 500 };
  }
}