import { motion } from 'motion/react';
import type { Timeline, Generation } from '../../types';
import { Plus } from 'lucide-react';

interface GenerationSelectorProps {
  timeline: Timeline;
  selectedGenId: string | null;
  onSelect: (gen: Generation) => void;
  onExtend: () => void;
}

const ROMAN = ['I','II','III','IV','V','VI','VII','VIII','IX','X'];

function toRoman(n: number): string {
  return ROMAN[n - 1] ?? String(n);
}

function getActualYear(timeline: Timeline, relativeYear: number): number {
  const base = timeline.root_deviation_date
    ? parseInt(timeline.root_deviation_date.split('-')[0])
    : 0;
  return base + relativeYear;
}

function genTypeLabel(gen: Generation): string {
  if (gen.generation_order === 1) return 'Initial';
  if (gen.generation_type === 'extension') return 'Extension';
  if (gen.generation_type === 'branch_point') return 'Branch';
  return 'Chronicle';
}

export default function GenerationSelector({
  timeline,
  selectedGenId,
  onSelect,
  onExtend,
}: GenerationSelectorProps) {
  const sorted = [...timeline.generations].sort(
    (a, b) => a.generation_order - b.generation_order
  );

  return (
    <aside className="flex flex-col h-full bg-vellum border-r border-border" style={{ width: 200 }}>

      {/* Header + Extend button */}
      <div className="px-4 pt-4 pb-3 border-b border-border shrink-0 space-y-3">
        <p className="font-mono text-[10px] tracking-widest uppercase text-dim">§ Chronicles</p>
        <button
          onClick={onExtend}
          className={[
            'w-full flex items-center justify-center gap-2',
            'border border-gold text-gold bg-gold/5',
            'px-3 py-2',
            'font-mono text-[10px] tracking-widest uppercase',
            'hover:bg-gold/15 transition-colors duration-150 cursor-pointer',
          ].join(' ')}
        >
          <Plus size={11} />
          Extend Chronicle
        </button>
        <div className="double-rule" />
      </div>

      {/* Generation list */}
      <div className="flex-1 overflow-y-auto py-1">
        {sorted.map((gen, idx) => {
          const isActive = gen.id === selectedGenId;
          const startYear = getActualYear(timeline, gen.start_year);
          const endYear = getActualYear(timeline, gen.end_year);
          const hasNarrative = !!gen.narrative_prose;
          const hasAudio = !!gen.audio_url || !!gen.audio_local_path;

          return (
            <motion.button
              key={gen.id}
              onClick={() => onSelect(gen)}
              className={[
                'w-full text-left px-4 py-3 transition-colors duration-150',
                'focus:outline-none cursor-pointer',
                isActive
                  ? 'bg-surface border-l-2 border-gold'
                  : 'border-l-2 border-transparent hover:bg-overlay',
              ].join(' ')}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1], delay: idx * 0.06 }}
            >
              {/* Title row */}
              <div className="flex items-baseline gap-1.5">
                <span className="font-display text-sm text-ink leading-tight">
                  Generation {toRoman(gen.generation_order)}
                </span>
              </div>

              {/* Year range */}
              <p className="font-mono text-[10px] text-dim mt-0.5">
                {startYear} — {endYear}
              </p>

              {/* Status row */}
              <p className="font-mono text-[10px] text-faint mt-1">
                {genTypeLabel(gen)}
                {hasNarrative && <span className="ml-1">· narrative</span>}
                {hasAudio && <span className="ml-1 text-quantum">· audio ✓</span>}
              </p>
            </motion.button>
          );
        })}
      </div>

    </aside>
  );
}
