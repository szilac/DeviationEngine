import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getTimeline, extendTimeline, generateExtensionSkeleton, deleteTimeline, deleteGeneration, exportTimeline } from '../services/api';
import type { Timeline, Generation, ErrorResponse, TimelineExtensionRequest, SupportedLanguage } from '../types';
import { TimelineUtils } from '../types';
import TimelineHeader from '../components/layout/TimelineHeader';
import GenerationSelector from '../components/layout/GenerationSelector';
import { ContentView } from '../components/ContentView';
import { SkeletonModal } from '../components/SkeletonModal';
import ImagePromptEditorModal from '../components/ImagePromptEditorModal';
import ExtensionForm from '../components/ExtensionForm';
import ImageGenerationDialog from '../components/ImageGenerationDialog';
import AudioStudioOverlay from '../components/overlays/AudioStudioOverlay';
import CharactersOverlay from '../components/overlays/CharactersOverlay';
import RippleMapOverlay from '../components/overlays/RippleMapOverlay';
import NovellaOverlay from '../components/overlays/NovellaOverlay';
import Dialog from '../components/ui/Dialog';
import { useScrollSpy } from '../hooks/useScrollSpy';

type ContentTab = 'structured' | 'narrative' | 'images';

const structuredSectionIds = [
  'executive-summary',
  'political-changes',
  'conflicts-wars',
  'economic-impacts',
  'social-developments',
  'technological-shifts',
  'key-figures',
  'long-term-implications',
];

function ReportViewPage() {
  const { timelineId } = useParams<{ timelineId: string }>();
  const navigate = useNavigate();

  // Core data state
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [selectedGeneration, setSelectedGeneration] = useState<Generation | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<ErrorResponse | null>(null);

  // Content tab state
  const [activeContentTab, setActiveContentTab] = useState<ContentTab>('structured');

  // Overlay states (replaces drawerContent)
  const [showRippleMap, setShowRippleMap]     = useState(false);
  const [showAudio, setShowAudio]             = useState(false);
  const [showCharacters, setShowCharacters]   = useState(false);
  const [showNovella, setShowNovella]         = useState(false);
  const [showExtend, setShowExtend]           = useState(false);
  const [showImages, setShowImages]           = useState(false);
  const [showSkeletonModal, setShowSkeletonModal] = useState(false);

  // Extension state
  const [isExtending, setIsExtending] = useState(false);
  const [extensionError, setExtensionError] = useState<ErrorResponse | null>(null);

  // Translation state
  const [currentLanguage, setCurrentLanguage] = useState<SupportedLanguage>('en');
  const [translatedContent, setTranslatedContent] = useState<Record<string, any>>({});
  const [translatedNarrative, setTranslatedNarrative] = useState<Record<string, string>>({});

  // Image generation state
  const [showImagePromptEditor, setShowImagePromptEditor] = useState(false);
  const [currentImagePromptSkeletonId, setCurrentImagePromptSkeletonId] = useState<string | null>(null);

  const activeSection = useScrollSpy(
    activeContentTab === 'structured' ? structuredSectionIds : []
  );

  useEffect(() => {
    if (timelineId) fetchTimelineData(timelineId);
  }, [timelineId]);

  useEffect(() => {
    if (timeline && timeline.generations.length > 0) {
      const latest = TimelineUtils.getLatestGeneration(timeline);
      if (latest) setSelectedGeneration(latest);
    } else {
      setSelectedGeneration(null);
    }
  }, [timeline]);

  useEffect(() => {
    if (selectedGeneration) {
      setTranslatedContent(selectedGeneration.report_translations ?? {});
      setTranslatedNarrative(selectedGeneration.narrative_translations ?? {});
      setCurrentLanguage('en');
      window.scrollTo(0, 0);
    } else {
      setTranslatedContent({});
      setTranslatedNarrative({});
      setCurrentLanguage('en');
    }
  }, [selectedGeneration?.id]);

  const fetchTimelineData = async (id: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await getTimeline(id);
      if (response.error) setError(response.error);
      else if (response.data) setTimeline(response.data);
    } catch {
      setError({ error: 'UnknownError', message: 'Failed to load timeline.' });
    }
    setIsLoading(false);
  };

  const handleSectionNavigate = (sectionId: string) => {
    document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const handleExtendTimeline = async (
    additionalYears: number,
    narrativeMode: import('../types').NarrativeMode,
    customPov?: string,
    additionalContext?: string,
    useSkeletonWorkflow?: boolean
  ) => {
    if (!timelineId) return;
    setIsExtending(true);
    setExtensionError(null);

    try {
      if (useSkeletonWorkflow) {
        const response = await generateExtensionSkeleton(timelineId, additionalYears, additionalContext);
        if (response.error) {
          setExtensionError(response.error);
        } else if (response.data) {
          sessionStorage.setItem('extensionNarrativeMode', narrativeMode);
          if (customPov) sessionStorage.setItem('extensionNarrativeCustomPov', customPov);
          sessionStorage.setItem('extensionParentTimelineId', timelineId);
          navigate(`/skeleton-workflow?id=${response.data.id}`);
        }
      } else {
        const request: TimelineExtensionRequest = {
          timeline_id: timelineId,
          additional_years: additionalYears,
          additional_context: additionalContext,
          narrative_mode: narrativeMode,
          narrative_custom_pov: customPov,
        };
        const response = await extendTimeline(request);
        if (response.error) setExtensionError(response.error);
        else if (response.data) {
          setTimeline(response.data);
          setShowExtend(false);
        }
      }
    } catch {
      setExtensionError({ error: 'UnknownError', message: 'An unexpected error occurred during extension.' });
    } finally {
      setIsExtending(false);
    }
  };

  const handleImagePromptsGenerated = (skeletonId: string) => {
    setCurrentImagePromptSkeletonId(skeletonId);
    setShowImages(false);
    setShowImagePromptEditor(true);
  };

  const handleImagePromptEditorComplete = () => {
    setShowImagePromptEditor(false);
    setCurrentImagePromptSkeletonId(null);
    setActiveContentTab('images');
    if (timelineId) fetchTimelineData(timelineId);
  };

  const handleTranslationComplete = () => {
    if (timelineId) fetchTimelineData(timelineId);
  };

  const handleExportTimeline = async () => {
    if (!timelineId) return;
    try {
      const response = await exportTimeline(timelineId);
      if (response.error) {
        setError(response.error);
      } else if (response.data) {
        const { blob, filename } = response.data;
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }
    } catch {
      setError({ error: 'UnknownError', message: 'Failed to export timeline.' });
    }
  };

  const handleDeleteTimeline = async () => {
    if (!timelineId) return;
    if (!confirm('Are you sure you want to delete this timeline? This action cannot be undone.')) return;
    try {
      const response = await deleteTimeline(timelineId);
      if (response.error) setError(response.error);
      else navigate('/library');
    } catch {
      setError({ error: 'UnknownError', message: 'Failed to delete timeline.' });
    }
  };

  const handleDeleteGeneration = async () => {
    if (!timelineId || !selectedGeneration) return;
    if (!confirm('Are you sure you want to delete this generation? This action cannot be undone.')) return;
    try {
      const response = await deleteGeneration(timelineId, selectedGeneration.id);
      if (response.error) setError(response.error);
      else fetchTimelineData(timelineId);
    } catch {
      setError({ error: 'UnknownError', message: 'Failed to delete generation.' });
    }
  };

  // ── Loading ──────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center bg-vellum">
        <div className="text-center">
          <p className="font-mono text-xs text-dim tracking-widest uppercase animate-pulse">
            Loading chronicle…
          </p>
        </div>
      </div>
    );
  }

  // ── Error ────────────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="h-screen flex items-center justify-center bg-vellum">
        <div className="max-w-md w-full mx-4 border border-rubric-dim p-6 corner-brackets">
          <p className="rubric-label mb-2">Error</p>
          <p className="font-body text-ink">{error.message || 'An error occurred'}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 font-mono text-xs text-dim hover:text-ink tracking-widest uppercase transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!timeline) {
    return (
      <div className="h-screen flex items-center justify-center bg-vellum">
        <p className="font-mono text-xs text-dim tracking-widest uppercase">No timeline data found.</p>
      </div>
    );
  }

  // ── Main layout ──────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] overflow-hidden bg-vellum">

      {/* Timeline-level header */}
      <TimelineHeader
        timeline={timeline}
        onRippleMap={() => setShowRippleMap(true)}
        onNovella={() => setShowNovella(true)}
        onAudioStudio={() => setShowAudio(true)}
        onCharacters={() => setShowCharacters(true)}
        onExport={handleExportTimeline}
        onDeleteTimeline={handleDeleteTimeline}
        onViewSkeleton={() => setShowSkeletonModal(true)}
      />

      {/* Two-zone layout */}
      <div className="flex flex-1 overflow-hidden">

        {/* Left: Generation selector */}
        <GenerationSelector
          timeline={timeline}
          selectedGenId={selectedGeneration?.id ?? null}
          onSelect={setSelectedGeneration}
          onExtend={() => setShowExtend(true)}
        />

        {/* Right: Generation content */}
        <div className="flex-1 overflow-hidden">
          <ContentView
            timeline={timeline}
            selectedGeneration={selectedGeneration}
            activeTab={activeContentTab}
            onTabChange={setActiveContentTab}
            currentLanguage={currentLanguage}
            onLanguageChange={setCurrentLanguage}
            translatedContent={currentLanguage !== 'en' ? translatedContent[currentLanguage] : undefined}
            translatedNarrative={currentLanguage !== 'en' ? translatedNarrative[currentLanguage] : undefined}
            onTranslationComplete={handleTranslationComplete}
            activeSection={activeSection}
            onSectionNavigate={handleSectionNavigate}
            onGenerateImages={() => setShowImages(true)}
            onDeleteGeneration={handleDeleteGeneration}
          />
        </div>
      </div>

      {/* ── Overlays ─────────────────────────────────────────────────────── */}

      <RippleMapOverlay
        open={showRippleMap}
        onClose={() => setShowRippleMap(false)}
        timeline={timeline}
      />

      <AudioStudioOverlay
        open={showAudio}
        onClose={() => setShowAudio(false)}
        timeline={timeline}
      />

      <CharactersOverlay
        open={showCharacters}
        onClose={() => setShowCharacters(false)}
        timeline={timeline}
      />

      <NovellaOverlay
        open={showNovella}
        onClose={() => setShowNovella(false)}
        timeline={timeline}
      />

      {/* Extend dialog */}
      <Dialog
        open={showExtend}
        onOpenChange={(v) => setShowExtend(v)}
        title="Extend Chronicle"
        description="Add more years to this alternate timeline"
        width="max-w-xl"
      >
        <ExtensionForm
          timeline={timeline}
          onSubmit={handleExtendTimeline}
          isLoading={isExtending}
        />
        {extensionError && (
          <div className="mt-4 border border-rubric-dim p-3">
            <p className="font-mono text-[10px] tracking-widest uppercase text-rubric mb-1">Extension Error</p>
            <p className="font-body text-dim text-sm">{extensionError.message}</p>
          </div>
        )}
      </Dialog>

      {/* Image generation dialog */}
      <Dialog
        open={showImages}
        onOpenChange={(v) => setShowImages(v)}
        title="Generate Images"
        description="Create period-appropriate imagery for this generation"
        width="max-w-xl"
      >
        {selectedGeneration && (
          <ImageGenerationDialog
            timeline={timeline}
            generationId={selectedGeneration.id}
            onSuccess={handleImagePromptsGenerated}
          />
        )}
      </Dialog>

      {/* Skeleton modal */}
      {showSkeletonModal && selectedGeneration?.source_skeleton_id && (
        <SkeletonModal
          timeline={timeline}
          generationId={selectedGeneration.id}
          onClose={() => setShowSkeletonModal(false)}
        />
      )}

      {/* Image prompt editor modal */}
      {showImagePromptEditor && currentImagePromptSkeletonId && selectedGeneration && (
        <ImagePromptEditorModal
          skeletonId={currentImagePromptSkeletonId}
          timeline={timeline}
          generation={selectedGeneration}
          onComplete={handleImagePromptEditorComplete}
          onCancel={() => {
            setShowImagePromptEditor(false);
            setCurrentImagePromptSkeletonId(null);
          }}
        />
      )}
    </div>
  );
}

export default ReportViewPage;
