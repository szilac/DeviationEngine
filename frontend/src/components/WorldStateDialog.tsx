import type { WorldEntity, WorldStateSnapshot } from '../types';
import Dialog from './ui/Dialog';

interface WorldStateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  snapshot?: WorldStateSnapshot | null;
}

const heading = 'font-mono text-[10px] tracking-widest uppercase text-gold mb-2';

export default function WorldStateDialog({ open, onOpenChange, snapshot }: WorldStateDialogProps) {
  const byType = new Map<string, WorldEntity[]>();
  snapshot?.entities.forEach((e) => byType.set(e.type, [...(byType.get(e.type) ?? []), e]));

  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="World State Snapshot"
      description={snapshot
        ? `As of ${snapshot.as_of_year} · ${snapshot.entities.length} entities · ${snapshot.relations.length} relations`
        : undefined}
      width="max-w-3xl"
    >
      {!snapshot ? (
        <p className="font-mono text-xs text-dim">
          No snapshot stored for this generation (extraction failed or it predates the feature).
        </p>
      ) : (
        <div className="space-y-6 text-sm text-ink">
          <p className="leading-relaxed">{snapshot.summary}</p>

          {[...byType].map(([type, entities]) => (
            <section key={type}>
              <h3 className={heading}>{type} ({entities.length})</h3>
              <ul className="space-y-1.5">
                {entities.map((e) => (
                  <li key={e.name}>
                    <span className="font-semibold">{e.name}</span>
                    <span className="text-dim"> — {e.status}</span>
                    {e.note && <p className="text-xs text-dim mt-0.5">{e.note}</p>}
                  </li>
                ))}
              </ul>
            </section>
          ))}

          {snapshot.relations.length > 0 && (
            <section>
              <h3 className={heading}>Relations ({snapshot.relations.length})</h3>
              <ul className="space-y-1">
                {snapshot.relations.map((r) => (
                  <li
                    key={`${r.source}|${r.relation}|${r.target}`}
                    className={r.active ? '' : 'text-faint line-through'}
                    title={r.active ? undefined : 'Inactive'}
                  >
                    {r.source} <span className="font-mono text-xs text-dim">{r.relation}</span> {r.target}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </Dialog>
  );
}
