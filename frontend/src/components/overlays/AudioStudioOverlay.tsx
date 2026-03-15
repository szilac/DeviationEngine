import type { Timeline } from '../../types';
import Dialog from '../ui/Dialog';
import AudioStudioPanel from '../AudioStudioPanel';

interface AudioStudioOverlayProps {
  open: boolean;
  onClose: () => void;
  timeline: Timeline;
}

export default function AudioStudioOverlay({ open, onClose, timeline }: AudioStudioOverlayProps) {
  return (
    <Dialog
      open={open}
      onOpenChange={(v) => !v && onClose()}
      variant="overlay"
      title="Audio Studio"
    >
      <div className="h-screen overflow-auto px-6 py-8">
        <div className="mb-6">
          <p className="rubric-label">§ Audio Studio</p>
          <h2 className="font-display text-2xl text-gold mt-1">
            {timeline.timeline_name || 'Audio Production'}
          </h2>
        </div>
        <AudioStudioPanel
          timeline={timeline}
          onScriptCreated={(script) => {
            console.log('Script created:', script);
          }}
        />
      </div>
    </Dialog>
  );
}
