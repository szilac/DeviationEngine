import type { CausalNode, CausalEdge, CausalDomain, CausalRelationship } from '../types';

interface RippleMapNodeDetailProps {
  node: CausalNode | null;
  allNodes: CausalNode[];
  allEdges: CausalEdge[];
  onClose: () => void;
}

// Manuscript palette — same mapping as RippleMapFilters
const DOMAIN_COLORS: Record<CausalDomain, string> = {
  political:    '#C0392B', // rubric
  economic:     '#6A8040', // success (olive)
  technological:'#4FC3F7', // quantum
  social:       '#D4A017', // gold
  cultural:     '#B8820A', // warning (amber)
  military:     '#8B2218', // rubric-dim
};

const RELATIONSHIP_COLORS: Record<CausalRelationship, string> = {
  causes:      '#C0392B', // rubric
  enables:     '#6A8040', // success
  prevents:    '#5A4E30', // faint
  accelerates: '#4FC3F7', // quantum
  weakens:     '#B8820A', // warning
  transforms:  '#D4A017', // gold
};

function formatDuration(s: string): string {
  const withSpaces = s.replace(/_/g, ' ');
  if (!withSpaces) return withSpaces;
  return withSpaces.charAt(0).toUpperCase() + withSpaces.slice(1);
}

function MagnitudeDots({ magnitude, domain }: { magnitude: number; domain: CausalDomain }) {
  const color = DOMAIN_COLORS[domain];
  const total = 5;
  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: total }, (_, i) => (
        <span
          key={i}
          style={{ color: i < magnitude ? color : '#374151', fontSize: '1rem', lineHeight: 1 }}
        >
          {i < magnitude ? '●' : '○'}
        </span>
      ))}
    </div>
  );
}

function ConfidenceBadge({ confidence }: { confidence: CausalNode['confidence'] }) {
  const styles: Record<CausalNode['confidence'], string> = {
    high:        'text-success border-success/50',
    medium:      'text-warning border-warning/50',
    speculative: 'text-faint border-border',
  };
  return (
    <span className={`px-2 py-0.5 border font-mono text-[9px] tracking-widest uppercase ${styles[confidence]}`}>
      {confidence}
    </span>
  );
}

function RelationshipBadge({ relationship }: { relationship: CausalRelationship }) {
  const color = RELATIONSHIP_COLORS[relationship];
  return (
    <span
      style={{ color, borderColor: color }}
      className="px-1.5 py-0.5 border font-mono text-[9px] tracking-widest uppercase"
    >
      {relationship}
    </span>
  );
}

export default function RippleMapNodeDetail({
  node,
  allNodes,
  allEdges,
  onClose,
}: RippleMapNodeDetailProps) {
  if (!node) return null;

  const incomingEdges = allEdges.filter((e) => e.target_node_id === node.id);
  const outgoingEdges = allEdges.filter((e) => e.source_node_id === node.id);

  const nodeById = (id: string): CausalNode | undefined =>
    allNodes.find((n) => n.id === id);

  const domainColor = DOMAIN_COLORS[node.domain];

  return (
    <div className="absolute right-4 top-4 bottom-4 w-80 overflow-y-auto z-10 bg-parchment border border-border">
      {/* Header */}
      <div className="sticky top-0 z-10 px-4 pt-4 pb-3 bg-parchment border-b border-border">
        <div className="flex items-start justify-between gap-2">
          <div className="flex flex-col gap-1.5 min-w-0">
            <span
              className="self-start rubric-label"
              style={{ color: domainColor }}
            >
              § {node.domain}
            </span>

            <h2 className="font-display text-ink text-sm leading-snug">{node.label}</h2>

            {node.is_deviation_point && (
              <span className="self-start px-2 py-0.5 border border-gold/50 text-gold font-mono text-[9px] tracking-widest uppercase">
                ◈ Deviation Point
              </span>
            )}
          </div>

          <button
            onClick={onClose}
            className="flex-shrink-0 text-dim hover:text-ink transition-colors mt-0.5 w-6 h-6 flex items-center justify-center font-mono text-xs"
            aria-label="Close panel"
          >
            ✕
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-1.5 mt-2.5">
          <span className="px-2 py-0.5 border border-border font-mono text-[9px] text-dim">
            {node.sub_domain}
          </span>
          <ConfidenceBadge confidence={node.confidence} />
          <span className="px-2 py-0.5 border border-quantum/40 font-mono text-[9px] text-quantum">
            +{node.time_offset_years}y
          </span>
        </div>
      </div>

      {/* Body */}
      <div className="px-4 pb-5 space-y-4 pt-3">
        <div className="flex items-center gap-3">
          <span className="rubric-label w-12 flex-shrink-0">Impact</span>
          <MagnitudeDots magnitude={node.magnitude} domain={node.domain} />
        </div>

        <p className="font-body text-ink text-sm leading-relaxed">{node.description}</p>

        <div className="font-mono text-[9px] text-dim">
          <span className="text-faint">DURATION · </span>
          {formatDuration(node.duration)}
        </div>

        {node.affected_regions.length > 0 && (
          <div>
            <p className="rubric-label mb-1.5">§ Affected Regions</p>
            <div className="flex flex-wrap gap-1.5">
              {node.affected_regions.map((region) => (
                <span
                  key={region}
                  className="px-2 py-0.5 border border-border font-mono text-[9px] text-dim"
                >
                  {region}
                </span>
              ))}
            </div>
          </div>
        )}

        {node.key_figures.length > 0 && (
          <div>
            <p className="rubric-label mb-1.5">§ Key Figures</p>
            <div className="flex flex-wrap gap-1.5">
              {node.key_figures.map((figure) => (
                <span
                  key={figure}
                  className="px-2 py-0.5 border border-gold/40 font-mono text-[9px] text-gold"
                >
                  {figure}
                </span>
              ))}
            </div>
          </div>
        )}

        {incomingEdges.length > 0 && (
          <div>
            <p className="rubric-label mb-2">← Caused by</p>
            <div className="space-y-2">
              {incomingEdges.map((edge) => {
                const sourceNode = nodeById(edge.source_node_id);
                return (
                  <div
                    key={`in-${edge.source_node_id}-${edge.target_node_id}`}
                    className="flex flex-col gap-1 p-2 bg-surface/40 border border-border"
                  >
                    <span className="font-body text-ink text-xs leading-snug">
                      {sourceNode?.label ?? edge.source_node_id}
                    </span>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <RelationshipBadge relationship={edge.relationship} />
                      {edge.time_delay && (
                        <span className="font-mono text-[9px] text-faint">{edge.time_delay}</span>
                      )}
                    </div>
                    {edge.description && (
                      <p className="font-body text-dim text-xs leading-snug">{edge.description}</p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {outgoingEdges.length > 0 && (
          <div>
            <p className="rubric-label mb-2">→ Leads to</p>
            <div className="space-y-2">
              {outgoingEdges.map((edge) => {
                const targetNode = nodeById(edge.target_node_id);
                return (
                  <div
                    key={`out-${edge.source_node_id}-${edge.target_node_id}`}
                    className="flex flex-col gap-1 p-2 bg-surface/40 border border-border"
                  >
                    <span className="font-body text-ink text-xs leading-snug">
                      {targetNode?.label ?? edge.target_node_id}
                    </span>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <RelationshipBadge relationship={edge.relationship} />
                      {edge.time_delay && (
                        <span className="font-mono text-[9px] text-faint">{edge.time_delay}</span>
                      )}
                    </div>
                    {edge.description && (
                      <p className="font-body text-dim text-xs leading-snug">{edge.description}</p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
