/**
 * Audio service for script generation and audio file management.
 *
 * Provides type-safe interface for audio-related backend API calls.
 */

import axios from 'axios';
import type {
  ScriptPreset,
  AudioScript,
  ScriptTranslation,
  AudioFile,
  ScriptGenerationRequest,
  ScriptUpdateRequest,
  AudioGenerationRequest,
  PresetCreateRequest,
  PresetUpdateRequest,
  ScriptStatus,
  NotebookLMGenerateRequest,
  NotebookLMJob,
  NLMAvailabilityResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 600000, // 10 minutes for audio generation (can be slow)
  headers: {
    'Content-Type': 'application/json',
  },
});

// ===== PRESETS =====

/**
 * Get all script presets.
 */
export async function getPresets(): Promise<ScriptPreset[]> {
  const response = await api.get<ScriptPreset[]>('/api/audio/presets');
  return response.data;
}

/**
 * Get specific preset by ID.
 */
export async function getPresetById(presetId: string): Promise<ScriptPreset> {
  const response = await api.get<ScriptPreset>(`/api/audio/presets/${presetId}`);
  return response.data;
}

/**
 * Create custom preset.
 */
export async function createPreset(data: PresetCreateRequest): Promise<ScriptPreset> {
  const response = await api.post<ScriptPreset>('/api/audio/presets', data);
  return response.data;
}

/**
 * Update custom preset.
 */
export async function updatePreset(
  presetId: string,
  data: PresetUpdateRequest
): Promise<ScriptPreset> {
  const response = await api.put<ScriptPreset>(`/api/audio/presets/${presetId}`, data);
  return response.data;
}

/**
 * Delete custom preset (soft delete).
 */
export async function deletePreset(presetId: string): Promise<void> {
  await api.delete(`/api/audio/presets/${presetId}`);
}

// ===== SCRIPTS =====

/**
 * Generate audio script from generation content.
 */
export async function generateScript(
  request: ScriptGenerationRequest
): Promise<AudioScript> {
  const response = await api.post<AudioScript>('/api/audio/scripts/generate', request);
  return response.data;
}

/**
 * List scripts with optional filters.
 */
export async function listScripts(params?: {
  status?: ScriptStatus;
  preset_id?: string;
}): Promise<AudioScript[]> {
  const response = await api.get<AudioScript[]>('/api/audio/scripts', { params });
  return response.data;
}

/**
 * Get script by ID.
 */
export async function getScriptById(scriptId: string): Promise<AudioScript> {
  const response = await api.get<AudioScript>(`/api/audio/scripts/${scriptId}`);
  return response.data;
}

/**
 * Update script content (draft only).
 */
export async function updateScript(
  scriptId: string,
  data: ScriptUpdateRequest
): Promise<AudioScript> {
  const response = await api.put<AudioScript>(`/api/audio/scripts/${scriptId}`, data);
  return response.data;
}

/**
 * Approve script for audio generation.
 */
export async function approveScript(scriptId: string): Promise<AudioScript> {
  const response = await api.post<AudioScript>(`/api/audio/scripts/${scriptId}/approve`);
  return response.data;
}

/**
 * Delete script and associated files.
 */
export async function deleteScript(scriptId: string): Promise<void> {
  await api.delete(`/api/audio/scripts/${scriptId}`);
}

// ===== HELPER: Get scripts for a timeline =====

/**
 * Get all scripts that use generations from a specific timeline.
 * Filters client-side since there's no direct backend endpoint.
 */
export async function getScriptsForTimeline(
  generationIds: string[]
): Promise<AudioScript[]> {
  const allScripts = await listScripts();

  // Filter scripts that have at least one generation_id from this timeline
  return allScripts.filter(script =>
    script.generation_ids.some(gid => generationIds.includes(gid))
  );
}

// ===== TRANSLATIONS =====

/**
 * Translate script to target language.
 */
export const translateScript = async (
  scriptId: string,
  request: {
    target_languages: string[];
    method: 'deepl' | 'llm';
  }
): Promise<ScriptTranslation[]> => {
  const response = await api.post(`/api/audio/scripts/${scriptId}/translate`, request);
  return response.data;
};

export const deleteScriptTranslation = async (
  scriptId: string,
  languageCode: string
): Promise<void> => {
  await api.delete(`/api/audio/scripts/${scriptId}/translations/${languageCode}`);
};

/**
 * Get all translations for a script.
 */
export async function getScriptTranslations(
  scriptId: string
): Promise<ScriptTranslation[]> {
  const response = await api.get<ScriptTranslation[]>(
    `/api/audio/scripts/${scriptId}/translations`
  );
  return response.data;
}

/**
 * Update translation content.
 */
export async function updateTranslation(
  translationId: string,
  translatedContent: string
): Promise<ScriptTranslation> {
  const response = await api.put<ScriptTranslation>(
    `/api/audio/translations/${translationId}`,
    { script_content: translatedContent }
  );
  return response.data;
}

// ===== AUDIO GENERATION =====

/**
 * Generate audio from approved script.
 */
export async function generateAudio(
  request: AudioGenerationRequest
): Promise<AudioFile> {
  const { script_id, language_code = 'en', voice_settings, voice_ids } = request;

  const response = await api.post<AudioFile>(
    '/api/audio/generate',
    { voice_settings, voice_ids },
    {
      params: {
        script_id,
        language_code,
      }
    }
  );
  return response.data;
}

/**
 * Get all audio files for a script.
 */
export async function getScriptAudioFiles(scriptId: string): Promise<AudioFile[]> {
  const response = await api.get<AudioFile[]>(`/api/audio/scripts/${scriptId}/audio`);
  return response.data;
}

/**
 * Delete audio file.
 */
export async function deleteAudioFile(audioFileId: string): Promise<void> {
  await api.delete(`/api/audio/${audioFileId}`);
}

/**
 * Get audio file URL for playback.
 * Constructs full URL from relative path.
 */
export function getAudioFileUrl(audioFile: AudioFile): string {
  // audio_url is already a relative path like "/audio/{id}.wav"
  return `${API_BASE_URL}${audioFile.audio_url}`;
}

// ============================================================================
// NotebookLM Studio Integration
// ============================================================================

/**
 * Check if nlm CLI is installed and authenticated.
 */
export async function checkNLMAvailable(): Promise<NLMAvailabilityResponse> {
  const response = await api.get<NLMAvailabilityResponse>('/api/notebooklm/available');
  return response.data;
}

/**
 * Start a new NotebookLM generation job.
 * Returns immediately — job runs in background. Poll getNLMJob() for status.
 */
export async function startNLMJob(
  request: NotebookLMGenerateRequest
): Promise<NotebookLMJob> {
  const response = await api.post<NotebookLMJob>('/api/notebooklm/jobs', request);
  return response.data;
}

/**
 * Get current status of a NotebookLM job.
 */
export async function getNLMJob(jobId: string): Promise<NotebookLMJob> {
  const response = await api.get<NotebookLMJob>(`/api/notebooklm/jobs/${jobId}`);
  return response.data;
}

/**
 * List all NotebookLM jobs for a timeline.
 */
export async function listNLMJobs(timelineId?: string): Promise<NotebookLMJob[]> {
  const response = await api.get<NotebookLMJob[]>('/api/notebooklm/jobs', {
    params: timelineId ? { timeline_id: timelineId } : undefined,
  });
  return response.data;
}

/**
 * Delete a NotebookLM job record.
 */
export async function deleteNLMJob(jobId: string): Promise<void> {
  await api.delete(`/api/notebooklm/jobs/${jobId}`);
}
