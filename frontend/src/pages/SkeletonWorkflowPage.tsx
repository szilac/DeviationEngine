/**
 * Skeleton Workflow Page
 *
 * Orchestrates the skeleton timeline generation workflow:
 * 1. Generate skeleton from deviation parameters
 * 2. Edit skeleton events
 * 3. Approve skeleton
 * 4. Generate full report
 */

import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import type {
  Skeleton,
  SkeletonEventUpdate,
  GenerateFromSkeletonRequest,
  NarrativeMode,
} from '../types';
import { NarrativeMode as NarrativeModeEnum } from '../types';
import { api, extendFromSkeleton } from '../services/api';
import SkeletonEditor from '../components/SkeletonEditor';
import NarrativeModeSelector from '../components/wizard/NarrativeModeSelector';
import InkTitle from '../components/layout/InkTitle';

const SkeletonWorkflowPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [skeleton, setSkeleton] = useState<Skeleton | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [isExtensionSkeleton, setIsExtensionSkeleton] = useState(false);
  const [parentTimelineId, setParentTimelineId] = useState<string | null>(null);

  const [narrativeMode, setNarrativeMode] = useState<NarrativeMode>(NarrativeModeEnum.BASIC);
  const [customPov, setCustomPov] = useState<string>('');

  useEffect(() => {
    const skeletonId = searchParams.get('id');
    if (skeletonId) loadSkeleton(skeletonId);
  }, [searchParams]);

  const loadSkeleton = async (skeletonId: string) => {
    setIsLoading(true);
    setError(null);

    const response = await api.getSkeleton(skeletonId);
    if (response.error) { setError(response.error.message); setIsLoading(false); return; }

    const loadedSkeleton = response.data!;
    setSkeleton(loadedSkeleton);

    if (loadedSkeleton.skeleton_type === 'extension_draft' && loadedSkeleton.parent_timeline_id) {
      setIsExtensionSkeleton(true);
      setParentTimelineId(loadedSkeleton.parent_timeline_id);
      const extMode = sessionStorage.getItem('extensionNarrativeMode');
      const extPov = sessionStorage.getItem('extensionNarrativeCustomPov');
      if (extMode) setNarrativeMode(extMode as NarrativeMode);
      if (extPov) setCustomPov(extPov);
    } else {
      setIsExtensionSkeleton(false);
      setParentTimelineId(null);
      sessionStorage.removeItem('extensionParentTimelineId');
      sessionStorage.removeItem('extensionNarrativeMode');
      sessionStorage.removeItem('extensionNarrativeCustomPov');
    }

    setIsLoading(false);
  };

  const handleSaveEvents = async (eventsUpdate: SkeletonEventUpdate[], deletedIds: string[]) => {
    if (!skeleton) return;
    setIsSaving(true);
    setError(null);
    const response = await api.updateSkeletonEvents(skeleton.id, { events_update: eventsUpdate, deleted_event_ids: deletedIds });
    if (response.error) { setError(response.error.message); setIsSaving(false); return; }
    setSkeleton(response.data!);
    setIsSaving(false);
  };

  const handleApprove = async () => {
    if (!skeleton) return;
    setIsSaving(true);
    setError(null);
    const response = await api.approveSkeleton(skeleton.id);
    if (response.error) { setError(response.error.message); setIsSaving(false); return; }
    setSkeleton(response.data!);
    setIsSaving(false);
  };

  const handleGenerateReport = async () => {
    if (!skeleton) return;
    if (narrativeMode === NarrativeModeEnum.ADVANCED_CUSTOM_POV && !customPov.trim()) {
      setError('Please provide custom perspective instructions for Advanced Custom POV mode');
      return;
    }
    setIsGenerating(true);
    setError(null);

    try {
      if (isExtensionSkeleton && parentTimelineId) {
        const response = await extendFromSkeleton(parentTimelineId, skeleton.id, narrativeMode, narrativeMode === NarrativeModeEnum.ADVANCED_CUSTOM_POV ? customPov : undefined);
        if (response.error) { setError(response.error.message); setIsGenerating(false); return; }
        sessionStorage.removeItem('extensionParentTimelineId');
        sessionStorage.removeItem('extensionNarrativeMode');
        sessionStorage.removeItem('extensionNarrativeCustomPov');
        navigate(`/reports/${parentTimelineId}`);
      } else {
        const request: GenerateFromSkeletonRequest = {
          skeleton_id: skeleton.id,
          narrative_mode: narrativeMode,
          narrative_custom_pov: narrativeMode === NarrativeModeEnum.ADVANCED_CUSTOM_POV ? customPov : undefined,
        };
        const response = await api.generateFromSkeleton(request);
        if (response.error) { setError(response.error.message); setIsGenerating(false); return; }
        navigate(`/reports/${response.data!.id}`);
      }
    } catch (_err) {
      setError('An unexpected error occurred during report generation');
      setIsGenerating(false);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-vellum flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="inline-block w-10 h-10 border border-gold border-t-transparent rounded-full animate-spin" />
          <p className="font-mono text-[10px] tracking-widest uppercase text-dim">Loading skeleton...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error && !skeleton) {
    return (
      <div className="min-h-screen bg-vellum flex items-center justify-center px-4">
        <div className="max-w-md w-full bg-parchment border border-rubric p-6 corner-brackets">
          <h2 className="font-display text-xl text-rubric mb-2">Error</h2>
          <p className="font-body text-sm text-dim">{error}</p>
        </div>
      </div>
    );
  }

  // No skeleton state
  if (!skeleton) {
    return (
      <div className="min-h-screen bg-vellum flex items-center justify-center px-4">
        <div className="max-w-md w-full bg-parchment border border-border p-6 corner-brackets">
          <h2 className="font-display text-xl text-ink mb-2">No Skeleton Found</h2>
          <p className="font-body text-sm text-dim mb-5">
            Generate a skeleton from the Deviation Console to begin your workflow.
          </p>
          <button
            onClick={() => navigate('/console')}
            className="font-mono text-[10px] tracking-widest uppercase border border-gold text-gold px-4 py-2 hover:bg-gold/10 transition-colors"
          >
            Go to Console
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-vellum">
      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* Page Header */}
        <header className="mb-6 pb-5 border-b border-border">
          <InkTitle className="font-display text-2xl md:text-3xl text-ink" delay={0.1}>
            {isExtensionSkeleton ? 'Extension Skeleton Workflow' : 'Skeleton Workflow'}
          </InkTitle>
          <p className="font-body text-sm text-dim mt-1 max-w-2xl">
            Review, refine, and approve your AI-generated skeleton timeline before generating a full analytical report.
          </p>
        </header>

        {/* Inline error banner */}
        {error && (
          <div className="mb-5 flex items-start gap-3 p-3 border border-rubric/50 bg-rubric/5">
            <span className="font-mono text-[10px] text-rubric shrink-0">ERR</span>
            <p className="font-body text-sm text-dim">{error}</p>
            <button onClick={() => setError(null)} className="ml-auto text-faint hover:text-dim font-mono">×</button>
          </div>
        )}

        {/* Top action bar — always visible so the primary CTA is never buried */}
        <div className="mb-6 flex items-center justify-between px-5 py-3 bg-parchment border border-border">
          <div className="flex items-center gap-3">
            <span className={`font-mono text-[9px] tracking-widest uppercase border px-2 py-0.5 ${
              skeleton.status === 'approved' || skeleton.status === 'report_generated'
                ? 'border-success/50 text-success'
                : 'border-gold-dim text-gold-dim'
            }`}>
              {skeleton.status === 'approved' || skeleton.status === 'report_generated'
                ? '✓ Approved'
                : skeleton.status === 'pending' ? 'Pending Review' : skeleton.status}
            </span>
            <span className="font-mono text-[9px] text-faint">
              {skeleton.events?.length ?? 0} events
            </span>
          </div>

          <div className="flex gap-3">
            {skeleton.status === 'pending' && (
              <button
                onClick={handleApprove}
                disabled={isSaving}
                className="font-mono text-[9px] tracking-widest uppercase border border-quantum/60 text-quantum px-5 py-2 hover:bg-quantum/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isSaving ? 'Approving…' : 'Approve Skeleton'}
              </button>
            )}
            {(skeleton.status === 'approved' || skeleton.status === 'report_generated') && (
              <button
                onClick={handleGenerateReport}
                disabled={isGenerating}
                className="font-mono text-[9px] tracking-widest uppercase border border-gold text-gold px-5 py-2 hover:bg-gold/10 hover:shadow-[var(--shadow-gold)] transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isGenerating ? 'Generating…' : 'Generate Full Report'}
              </button>
            )}
          </div>
        </div>

        {/* Narrative Mode (shown after approval) */}
        {(skeleton?.status === 'approved' || skeleton?.status === 'report_generated') && (
          <section className="mb-6 bg-parchment border border-border p-6 corner-brackets" aria-label="Narrative Generation Settings">
            <div className="mb-4 pb-3 border-b border-border">
              <h2 className="font-mono text-[9px] tracking-widest uppercase text-dim">Narrative Generation Settings</h2>
              <p className="font-body text-sm text-dim mt-1">
                Choose how the narrative layer should be generated when creating the final report.
              </p>
            </div>
            <NarrativeModeSelector
              narrativeMode={narrativeMode}
              customPov={customPov}
              onModeChange={setNarrativeMode}
              onCustomPovChange={setCustomPov}
            />
          </section>
        )}

        {/* Skeleton Editor */}
        <section aria-label="Skeleton Timeline Editor">
          <SkeletonEditor
            skeleton={skeleton}
            onSave={handleSaveEvents}
            onApprove={handleApprove}
            onGenerateReport={handleGenerateReport}
            isSaving={isSaving}
            isGenerating={isGenerating}
          />
        </section>

        {/* Generation progress */}
        {isGenerating && (
          <div className="mt-5 flex items-center gap-3 p-4 border border-gold/30 bg-gold/5">
            <div className="w-4 h-4 border border-gold border-t-transparent rounded-full animate-spin shrink-0" />
            <div>
              <p className="font-mono text-[10px] tracking-widest uppercase text-gold">Generating Full Report...</p>
              <p className="font-body text-xs text-dim mt-0.5">
                This may take 1–2 minutes while the AI analyzes your skeleton.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SkeletonWorkflowPage;
