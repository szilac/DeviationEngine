/**
 * Skeleton Event Viewer Component (Read-Only)
 *
 * Displays skeleton events in a read-only format for viewing the skeleton
 * snapshot that was used to generate a timeline report.
 */

import { useMemo } from 'react';

interface SkeletonEventSnapshot {
  id: string;
  event_date: string;
  event_year: number;
  location: string;
  description: string;
  event_order: number;
  is_user_added: boolean;
  is_user_modified: boolean;
}

interface SkeletonSnapshotData {
  timeline_id: string;
  skeleton_id: string;
  events: SkeletonEventSnapshot[];
  snapshot_created_at: string;
}

interface SkeletonEventViewerProps {
  snapshot: SkeletonSnapshotData;
  deviationDate: string;
  deviationDescription: string;
}

const SkeletonEventViewer: React.FC<SkeletonEventViewerProps> = ({
  snapshot,
  deviationDate,
  deviationDescription,
}) => {
  const sortedEvents = useMemo(
    () => [...snapshot.events].sort((a, b) => a.event_order - b.event_order),
    [snapshot.events]
  );

  const getAbsoluteYear = (eventYear: number): number =>
    new Date(deviationDate).getFullYear() + eventYear;

  return (
    <div className="space-y-5">

      {/* Deviation metadata */}
      <div className="border border-border bg-surface/40 px-4 py-3 grid grid-cols-3 gap-4">
        <div>
          <p className="font-mono text-[9px] tracking-widest uppercase text-faint mb-0.5">Deviation Date</p>
          <p className="font-mono text-[11px] text-ink">{deviationDate}</p>
        </div>
        <div>
          <p className="font-mono text-[9px] tracking-widest uppercase text-faint mb-0.5">Total Events</p>
          <p className="font-mono text-[11px] text-ink">{snapshot.events.length}</p>
        </div>
        <div className="col-span-3 border-t border-border pt-3 mt-1">
          <p className="font-mono text-[9px] tracking-widest uppercase text-faint mb-0.5">Deviation</p>
          <p className="font-body text-sm text-dim leading-relaxed">{deviationDescription}</p>
        </div>
      </div>

      {/* Events */}
      <div className="space-y-2">
        <p className="font-mono text-[9px] tracking-widest uppercase text-faint">Key Events</p>

        {sortedEvents.map((event, index) => {
          const borderClass = event.is_user_added
            ? 'border-quantum/50'
            : event.is_user_modified
            ? 'border-gold-dim'
            : 'border-border';

          return (
            <div key={event.id} className={`border ${borderClass} bg-parchment px-4 py-3`}>
              {/* Event header row */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-[10px] border border-gold-dim text-gold w-6 h-5 flex items-center justify-center shrink-0">
                    {index + 1}
                  </span>
                  <span className="font-mono text-[10px] text-dim">
                    {event.event_date} · {getAbsoluteYear(event.event_year)}
                  </span>
                </div>
                <div className="flex gap-1.5">
                  {event.is_user_added && (
                    <span className="font-mono text-[8px] tracking-widest uppercase border border-quantum/50 text-quantum px-1.5 py-px">
                      Added
                    </span>
                  )}
                  {event.is_user_modified && (
                    <span className="font-mono text-[8px] tracking-widest uppercase border border-gold-dim text-gold-dim px-1.5 py-px">
                      Modified
                    </span>
                  )}
                </div>
              </div>

              {/* Event details */}
              <div className="space-y-1.5">
                <div>
                  <span className="font-mono text-[9px] tracking-widest uppercase text-faint">Location</span>
                  <p className="font-body text-sm text-ink">{event.location}</p>
                </div>
                <div>
                  <span className="font-mono text-[9px] tracking-widest uppercase text-faint">Description</span>
                  <p className="font-body text-sm text-dim leading-relaxed">{event.description}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Snapshot metadata */}
      <div className="border-t border-border pt-3">
        <p className="font-mono text-[9px] text-faint">
          Snapshot: {new Date(snapshot.snapshot_created_at).toLocaleString()}
          {' · '}ID: {snapshot.skeleton_id.substring(0, 8)}…
        </p>
      </div>
    </div>
  );
};

export default SkeletonEventViewer;
