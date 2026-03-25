import type { Timeline } from '../../types';
import Dialog from '../ui/Dialog';
import NovellaPanel from '../NovellaPanel';

interface NovellaOverlayProps {
  open: boolean;
  onClose: () => void;
  timeline: Timeline;
}

export default function NovellaOverlay({ open, onClose, timeline }: NovellaOverlayProps) {
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()} variant="overlay" title="Standalone Story Studio">
      <div className="h-screen flex flex-col">
        <div className="px-6 py-5 border-b border-border shrink-0">
          <p className="rubric-label">§ Standalone Story Studio</p>
          <h2 className="font-display text-2xl text-gold mt-1">
            {timeline.timeline_name || 'Standalone Story'}
          </h2>
          <p className="font-caption text-sm text-dim mt-1">
            A creative work drawn from all generations in this timeline
          </p>
        </div>
        <div className="flex-1 min-h-0">
          <NovellaPanel timeline={timeline} />
        </div>
      </div>
    </Dialog>
  );
}
