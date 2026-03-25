import type { Timeline } from '../../types';
import { BookOpen, Download, MoreHorizontal, GitBranch, Mic, Users, Trash2, FileText } from 'lucide-react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import InkTitle from './InkTitle';
import { InfoIcon } from '../Tooltip';

interface TimelineHeaderProps {
  timeline: Timeline;
  onRippleMap: () => void;
  onAudioStudio: () => void;
  onCharacters: () => void;
  onNovella: () => void;
  onExport: () => void;
  onDeleteTimeline: () => void;
  onViewSkeleton: () => void;
}

function toRoman(n: number): string {
  const vals = [1000,900,500,400,100,90,50,40,10,9,5,4,1];
  const syms = ['M','CM','D','CD','C','XC','L','XL','X','IX','V','IV','I'];
  let result = '';
  for (let i = 0; i < vals.length; i++) {
    while (n >= vals[i]) { result += syms[i]; n -= vals[i]; }
  }
  return result;
}

export default function TimelineHeader({
  timeline,
  onRippleMap,
  onAudioStudio,
  onCharacters,
  onNovella,
  onExport,
  onDeleteTimeline,
  onViewSkeleton,
}: TimelineHeaderProps) {
  const deviationYear = timeline.root_deviation_date
    ? timeline.root_deviation_date.split('-')[0]
    : '??';

  const totalYears = timeline.generations.reduce(
    (sum, g) => Math.max(sum, g.end_year),
    0
  );
  const lastGen = timeline.generations[timeline.generations.length - 1];
  const endYear = lastGen
    ? parseInt(deviationYear) + lastGen.end_year
    : parseInt(deviationYear);

  const scenarioLabel = (timeline.scenario_type ?? '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());

  const shortId = timeline.id.split('-')[0].toUpperCase();

  return (
    <div
      className="relative z-10 bg-vellum border-b border-border px-6"
      style={{ borderTop: '2px solid #7A5C10' }}
    >
      <div className="flex items-center justify-between h-16">

        {/* Left: title + metadata */}
        <div className="min-w-0 flex-1 pr-4">
          <div className="flex items-center gap-2 min-w-0">
            <InkTitle
              className="font-display text-gold text-[22px] leading-tight truncate min-w-0"
              delay={0.05}
            >
              {timeline.timeline_name || timeline.root_deviation_description}
            </InkTitle>
            <InfoIcon
              content={timeline.root_deviation_description}
              maxWidth="420px"
              position="bottom"
            />
          </div>
          <p className="font-mono text-[10px] text-dim tracking-wide mt-0.5">
            <span className="text-quantum">|TL-{shortId}⟩</span>
            <span className="mx-2 text-faint">·</span>
            {scenarioLabel}
            <span className="mx-2 text-faint">·</span>
            {deviationYear}
            {totalYears > 0 && (
              <>
                <span className="mx-2 text-faint">—</span>
                {endYear}
                <span className="ml-2 text-faint">({toRoman(timeline.generations.length)} {timeline.generations.length === 1 ? 'chronicle' : 'chronicles'})</span>
              </>
            )}
          </p>
        </div>

        {/* Right: action buttons */}
        <div className="flex items-center gap-0.5 shrink-0">
          <ActionBtn icon={<GitBranch size={11} />} label="Ripple Map" onClick={onRippleMap} />
          <ActionBtn icon={<Mic size={11} />} label="Audio" onClick={onAudioStudio} />
          <ActionBtn icon={<Users size={11} />} label="Characters" onClick={onCharacters} />
          <ActionBtn icon={<BookOpen size={11} />} label="Standalone Story" onClick={onNovella} />

          <div className="w-px h-5 bg-border mx-1.5" />

          <ActionBtn icon={<Download size={11} />} label="Export" onClick={onExport} />

          {/* More menu */}
          <DropdownMenu.Root>
            <DropdownMenu.Trigger asChild>
              <button
                className="flex items-center px-2 py-1.5 font-mono text-[10px] tracking-widest uppercase text-dim hover:text-ink transition-colors duration-150 focus:outline-none cursor-pointer"
                aria-label="More actions"
              >
                <MoreHorizontal size={14} />
              </button>
            </DropdownMenu.Trigger>

            <DropdownMenu.Portal>
              <DropdownMenu.Content
                className="bg-parchment border border-border shadow-[var(--shadow-panel)] z-50 min-w-[180px]"
                align="end"
                sideOffset={4}
              >
                {timeline.generations[0]?.source_skeleton_id && (
                  <DropdownItem onClick={onViewSkeleton} icon={<FileText size={11} />}>
                    View skeleton source
                  </DropdownItem>
                )}
                <DropdownItem onClick={onDeleteTimeline} icon={<Trash2 size={11} />} danger>
                  Delete timeline
                </DropdownItem>
                <DropdownMenu.Arrow className="fill-border" />
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>
        </div>
      </div>
    </div>
  );
}

function ActionBtn({
  icon,
  label,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1.5 px-2.5 py-1.5 font-mono text-[10px] tracking-widest uppercase text-dim hover:text-gold transition-colors duration-150 focus:outline-none cursor-pointer"
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

function DropdownItem({
  children,
  onClick,
  icon,
  danger = false,
}: {
  children: React.ReactNode;
  onClick: () => void;
  icon?: React.ReactNode;
  danger?: boolean;
}) {
  return (
    <DropdownMenu.Item
      onClick={onClick}
      className={[
        'flex items-center gap-2 px-3 py-2',
        'font-mono text-[10px] tracking-widest uppercase',
        'cursor-pointer focus:outline-none transition-colors duration-100',
        danger
          ? 'text-rubric-dim hover:text-rubric hover:bg-rubric/10'
          : 'text-dim hover:text-ink hover:bg-overlay',
      ].join(' ')}
    >
      {icon}
      {children}
    </DropdownMenu.Item>
  );
}
