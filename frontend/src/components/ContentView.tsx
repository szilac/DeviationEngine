import { AnimatePresence, motion } from 'motion/react';
import type { Timeline, Generation, SupportedLanguage } from '../types';
import StructuredReportView from './StructuredReportView';
import NarrativeView from './NarrativeView';
import ImageGallery from './ImageGallery';
import Button from './ui/Button';

type ContentTab = 'structured' | 'narrative' | 'images';

interface ContentViewProps {
  timeline: Timeline;
  selectedGeneration: Generation | null;
  activeTab: ContentTab;
  onTabChange: (tab: ContentTab) => void;
  currentLanguage: SupportedLanguage;
  onLanguageChange: (lang: SupportedLanguage) => void;
  translatedContent?: any;
  translatedNarrative?: any;
  onTranslationComplete: () => void;
  activeSection?: string;
  onSectionNavigate?: (id: string) => void;
  onGenerateImages?: () => void;
  onDeleteGeneration?: () => void;
}

const TABS: { value: ContentTab; label: string }[] = [
  { value: 'structured',  label: 'Report'    },
  { value: 'narrative',   label: 'Narrative' },
  { value: 'images',      label: 'Images'    },
];

export function ContentView({
  timeline,
  selectedGeneration,
  activeTab,
  onTabChange,
  currentLanguage,
  onLanguageChange,
  translatedContent,
  translatedNarrative,
  onTranslationComplete,
  onGenerateImages,
  onDeleteGeneration,
}: ContentViewProps) {

  return (
    <div className="flex flex-col h-full bg-parchment">

      {/* Tab bar */}
      <div className="border-b border-border px-6 shrink-0">
        <div className="flex">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.value;
            return (
              <button
                key={tab.value}
                onClick={() => onTabChange(tab.value)}
                className={[
                  'px-4 py-3 font-mono text-[10px] tracking-widest uppercase',
                  'border-b-2 -mb-px transition-colors duration-150',
                  'focus:outline-none cursor-pointer',
                  isActive
                    ? 'text-gold border-gold'
                    : 'text-dim border-transparent hover:text-ink',
                ].join(' ')}
              >
                § {tab.label}
              </button>
            );
          })}

          {/* Generation actions — far right */}
          {selectedGeneration && (
            <div className="ml-auto flex items-center gap-2 py-2">
              {activeTab === 'images' && onGenerateImages && (
                <Button variant="primary" size="sm" onClick={onGenerateImages}>
                  + Generate Images
                </Button>
              )}
              {onDeleteGeneration && (
                <Button variant="rubric" size="sm" onClick={onDeleteGeneration}>
                  Delete Generation
                </Button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Scrollable content area */}
      <div className="flex-1 overflow-y-auto">
        {!selectedGeneration ? (
          <div className="flex items-center justify-center h-full">
            <p className="font-mono text-xs text-faint tracking-widest uppercase">
              Select a chronicle from the left panel
            </p>
          </div>
        ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              className="max-w-4xl mx-auto px-8 py-8"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.18, ease: [0.4, 0, 0.2, 1] }}
            >
              {activeTab === 'structured' && (
                <StructuredReportView
                  generation={selectedGeneration}
                  timeline={timeline}
                  translatedContent={translatedContent}
                  currentLanguage={currentLanguage}
                  onLanguageChange={onLanguageChange}
                  onTranslated={onTranslationComplete}
                />
              )}
              {activeTab === 'narrative' && (
                <NarrativeView
                  generation={selectedGeneration}
                  timeline={timeline}
                  translatedNarrative={translatedNarrative}
                  currentLanguage={currentLanguage}
                  onLanguageChange={onLanguageChange}
                  onTranslated={onTranslationComplete}
                />
              )}
              {activeTab === 'images' && (
                <ImageGallery
                  timeline={timeline}
                  generationId={selectedGeneration.id}
                  onImageDeleted={() => {}}
                />
              )}
            </motion.div>
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
