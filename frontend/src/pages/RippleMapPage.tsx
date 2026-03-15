/**
 * RippleMapPage
 *
 * Full-page causal graph visualization for a timeline.
 * URL: /ripple-map/:timelineId
 *
 * Flow:
 *  - Loads timeline and existing ripple map on mount
 *  - If no ripple map: shows generation picker + generate button
 *  - If ripple map exists but new generations available: shows "Add Generations" banner
 *  - Main area: RippleMapVisualization (full width/height)
 *  - Overlay: RippleMapFilters toolbar
 *  - Right side: RippleMapNodeDetail panel (when node selected)
 */

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  getTimeline,
  getRippleMap,
  generateRippleMap,
  addGenerationsToRippleMap,
} from '../services/api';
import type { Timeline, RippleMap, CausalNode, CausalDomain } from '../types';
import RippleMapVisualization from '../components/RippleMapVisualization';
import RippleMapFilters from '../components/RippleMapFilters';
import RippleMapNodeDetail from '../components/RippleMapNodeDetail';
import { ArrowLeft, Radio } from 'lucide-react';

// ─── Confidence ordering ──────────────────────────────────────────────────────

// ─── Component ────────────────────────────────────────────────────────────────

export default function RippleMapPage() {
  const { timelineId } = useParams<{ timelineId: string }>();
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);

  // ── Data state ──────────────────────────────────────────────────────────────
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [rippleMap, setRippleMap] = useState<RippleMap | null>(null);
  const [loadingTimeline, setLoadingTimeline] = useState(true);
  const [loadingMap, setLoadingMap] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Canvas dimensions ───────────────────────────────────────────────────────
  // RippleMapVisualization reads its true size from getBoundingClientRect() in
  // the D3 effect, so these values only need to be positive (to pass the render
  // guard) and to trigger D3 re-runs when the container resizes.
  const [dimensions, setDimensions] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });

  // ── Selection state ─────────────────────────────────────────────────────────
  const [selectedNode, setSelectedNode] = useState<CausalNode | null>(null);

  // ── Generation picker state (for initial generation) ────────────────────────
  const [selectedGenIds, setSelectedGenIds] = useState<Set<string>>(new Set());

  // ── View mode ────────────────────────────────────────────────────────────────
  const [viewMode, setViewMode] = useState<'linear' | 'radial'>('radial');

  // ── Filter state ─────────────────────────────────────────────────────────────
  const [activeDomains, setActiveDomains] = useState<Set<CausalDomain>>(
    new Set(['political', 'economic', 'technological', 'social', 'cultural', 'military'])
  );
  const [activeGenerationIds, setActiveGenerationIds] = useState<Set<string>>(new Set());

  // ── Resize observer ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDimensions({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // ── Fetch timeline + existing ripple map ─────────────────────────────────────
  useEffect(() => {
    if (!timelineId) return;

    (async () => {
      setLoadingTimeline(true);
      const tlRes = await getTimeline(timelineId);
      if (tlRes.error || !tlRes.data) {
        setError(tlRes.error?.message ?? 'Failed to load timeline.');
        setLoadingTimeline(false);
        setLoadingMap(false);
        return;
      }
      setTimeline(tlRes.data);
      setLoadingTimeline(false);

      setLoadingMap(true);
      const rmRes = await getRippleMap(timelineId);
      if (rmRes.data) {
        setRippleMap(rmRes.data);
        setActiveGenerationIds(new Set(rmRes.data.included_generation_ids));
      }
      setLoadingMap(false);
    })();
  }, [timelineId]);

  // ── Derived: which generation IDs are new (not yet in map) ──────────────────
  const allGenIds = timeline?.generations.map((g) => g.id) ?? [];
  const includedIds = new Set(rippleMap?.included_generation_ids ?? []);
  const newGenIds = allGenIds.filter((id) => !includedIds.has(id));

  // ── Filtered nodes / edges for the visualization ─────────────────────────────
  // Memoized to preserve stable array refs so the D3 useEffect doesn't re-run
  // (and reset zoom/pan) on unrelated state changes like selectedNode.
  const filteredNodes = useMemo(
    () =>
      rippleMap?.nodes.filter(
        (n) =>
          // Deviation point always visible regardless of domain / generation filters
          n.is_deviation_point ||
          (activeDomains.has(n.domain) &&
            (activeGenerationIds.size === 0 || activeGenerationIds.has(n.source_generation_id)))
      ) ?? [],
    [rippleMap, activeDomains, activeGenerationIds]
  );

  const filteredEdges = useMemo(() => {
    const filteredNodeIds = new Set(filteredNodes.map((n) => n.id));
    return (
      rippleMap?.edges.filter(
        (e) => filteredNodeIds.has(e.source_node_id) && filteredNodeIds.has(e.target_node_id)
      ) ?? []
    );
  }, [rippleMap, filteredNodes]);

  // ── Reset filters ─────────────────────────────────────────────────────────────
  const handleResetFilters = useCallback(() => {
    setActiveDomains(
      new Set(['political', 'economic', 'technological', 'social', 'cultural', 'military'])
    );
    if (rippleMap) {
      setActiveGenerationIds(new Set(rippleMap.included_generation_ids));
    }
  }, [rippleMap]);

  // ── Toggle domain ─────────────────────────────────────────────────────────────
  const handleToggleDomain = useCallback((domain: CausalDomain) => {
    setActiveDomains((prev) => {
      const next = new Set(prev);
      if (next.has(domain)) {
        if (next.size > 1) next.delete(domain); // keep at least one
      } else {
        next.add(domain);
      }
      return next;
    });
  }, []);

  // ── Toggle generation ─────────────────────────────────────────────────────────
  const handleToggleGeneration = useCallback((id: string) => {
    setActiveGenerationIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        if (next.size > 1) next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  // ── Generate ripple map ────────────────────────────────────────────────────────
  const handleGenerate = async () => {
    if (!timelineId || selectedGenIds.size === 0) return;
    setGenerating(true);
    setError(null);
    const res = await generateRippleMap(timelineId, [...selectedGenIds]);
    if (res.error || !res.data) {
      setError(res.error?.message ?? 'Generation failed.');
    } else {
      setRippleMap(res.data);
      setActiveGenerationIds(new Set(res.data.included_generation_ids));
    }
    setGenerating(false);
  };

  // ── Add new generations to existing map ────────────────────────────────────────
  const handleAddGenerations = async () => {
    if (!timelineId || newGenIds.length === 0) return;
    setGenerating(true);
    setError(null);
    const res = await addGenerationsToRippleMap(timelineId, newGenIds);
    if (res.error || !res.data) {
      setError(res.error?.message ?? 'Failed to add generations.');
    } else {
      setRippleMap(res.data);
      setActiveGenerationIds(new Set(res.data.included_generation_ids));
    }
    setGenerating(false);
  };

  // ── Render: loading ─────────────────────────────────────────────────────────
  if (loadingTimeline) {
    return (
      <div className="h-screen flex items-center justify-center bg-vellum">
        <Spinner label="Loading timeline…" />
      </div>
    );
  }

  if (error && !timeline) {
    return (
      <div className="h-screen flex items-center justify-center bg-vellum">
        <div className="text-center space-y-4">
          <p className="text-rubric font-body">{error}</p>
          <button
            onClick={() => navigate(-1)}
            className="px-4 py-2 border border-border text-dim hover:border-gold-dim hover:text-ink font-mono text-xs tracking-widest uppercase transition-colors"
          >
            Go back
          </button>
        </div>
      </div>
    );
  }

  // ── Render: main ────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-screen bg-vellum">
      {/* ── Top bar ────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 px-4 py-2.5 border-b border-border flex-shrink-0 bg-vellum">
        <Link
          to={`/reports/${timelineId}`}
          className="flex items-center gap-1.5 font-mono text-[9px] tracking-widest uppercase text-dim hover:text-gold transition-colors"
        >
          <ArrowLeft className="w-3 h-3" />
          Back
        </Link>

        <span className="text-faint">|</span>

        <div className="flex items-center gap-2 min-w-0">
          <Radio className="w-3 h-3 text-quantum flex-shrink-0" />
          <span className="rubric-label">§ Ripple Map</span>
          {timeline && (
            <span className="font-body text-dim text-sm truncate">
              {' — '}
              {new Date(timeline.root_deviation_date).getFullYear()}
              {': '}
              {timeline.root_deviation_description.length > 60
                ? timeline.root_deviation_description.slice(0, 58) + '…'
                : timeline.root_deviation_description}
            </span>
          )}
        </div>

        {rippleMap && (
          <div className="ml-auto flex items-center gap-3 flex-shrink-0">
            {/* View toggle */}
            <div className="flex border border-border">
              {(['linear', 'radial'] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setViewMode(mode)}
                  className={`px-3 py-1 font-mono text-[9px] tracking-widest uppercase transition-colors ${
                    viewMode === mode
                      ? 'bg-gold/10 text-gold border-r border-border last:border-r-0'
                      : 'text-dim hover:text-ink border-r border-border last:border-r-0'
                  }`}
                >
                  {mode === 'linear' ? '⟶ Linear' : '⊚ Radial'}
                </button>
              ))}
            </div>
            {/* Stats */}
            <div className="flex items-center gap-3 font-mono text-[9px] text-dim">
              <span>{rippleMap.total_nodes} nodes</span>
              {rippleMap.dominant_domain && (
                <span className="capitalize">{rippleMap.dominant_domain} dominant</span>
              )}
              {rippleMap.max_ripple_depth > 0 && (
                <span>depth {rippleMap.max_ripple_depth}</span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── Error banner ───────────────────────────────────────────────────── */}
      {error && (
        <div className="px-4 py-2 border-b border-rubric/30 bg-rubric/10 text-rubric font-body text-sm flex items-center justify-between flex-shrink-0">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-rubric-dim hover:text-rubric ml-4 font-mono text-xs">
            ✕
          </button>
        </div>
      )}

      {/* ── Add-generations banner ─────────────────────────────────────────── */}
      {rippleMap && newGenIds.length > 0 && !generating && (
        <div className="px-4 py-2 border-b border-quantum/20 bg-quantum/5 text-quantum font-body text-sm flex items-center gap-3 flex-shrink-0">
          <span>
            {newGenIds.length} new generation{newGenIds.length > 1 ? 's' : ''} available.
          </span>
          <button
            onClick={handleAddGenerations}
            className="px-3 py-1 border border-quantum/40 text-quantum hover:bg-quantum/10 font-mono text-[9px] tracking-widest uppercase transition-colors"
          >
            Add to Ripple Map
          </button>
        </div>
      )}

      {/* ── Main content area ──────────────────────────────────────────────── */}
      <div className="flex-1 relative overflow-hidden" ref={containerRef}>

        {/* Generating spinner overlay */}
        {generating && (
          <div className="absolute inset-0 z-30 flex items-center justify-center bg-vellum/80 backdrop-blur-sm">
            <Spinner label="Generating causal graph…" />
          </div>
        )}

        {/* Loading map spinner */}
        {loadingMap && !generating && (
          <div className="absolute inset-0 z-20 flex items-center justify-center bg-vellum/60">
            <Spinner label="Loading ripple map…" />
          </div>
        )}

        {/* No ripple map yet: generation picker */}
        {!loadingMap && !rippleMap && !generating && timeline && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <div className="corner-brackets bg-parchment border border-border p-8 max-w-md w-full mx-4 space-y-5">
              <div className="flex items-center gap-3">
                <Radio className="w-5 h-5 text-quantum" />
                <h2 className="font-display text-ink text-lg">Generate Ripple Map</h2>
              </div>
              <p className="font-body text-dim text-sm leading-relaxed">
                The Ripple Analyst agent will extract causal nodes and edges from the selected
                generation reports and build an interactive causal graph.
              </p>

              <div className="space-y-2">
                <p className="rubric-label">§ Select generations</p>
                {timeline.generations.map((gen, idx) => {
                  const checked = selectedGenIds.has(gen.id);
                  return (
                    <label
                      key={gen.id}
                      className={`flex items-center gap-3 p-3 cursor-pointer transition-colors border ${
                        checked ? 'border-gold/50 bg-gold/5' : 'border-border hover:border-gold-dim'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => {
                          setSelectedGenIds((prev) => {
                            const next = new Set(prev);
                            if (next.has(gen.id)) next.delete(gen.id);
                            else next.add(gen.id);
                            return next;
                          });
                        }}
                        className="w-4 h-4 accent-gold"
                      />
                      <div className="flex flex-col min-w-0">
                        <span className="font-body text-ink text-sm">
                          Generation {idx + 1}
                        </span>
                        <span className="font-mono text-[9px] text-dim">
                          {gen.start_year}–{gen.end_year} · {gen.period_years} years
                        </span>
                      </div>
                    </label>
                  );
                })}
              </div>

              <button
                onClick={handleGenerate}
                disabled={selectedGenIds.size === 0}
                className={`w-full px-4 py-3 font-mono text-xs tracking-widest uppercase transition-colors border ${
                  selectedGenIds.size === 0
                    ? 'border-border text-faint cursor-not-allowed'
                    : 'border-gold text-gold hover:bg-gold/10'
                }`}
              >
                Generate Ripple Map
              </button>
            </div>
          </div>
        )}

        {/* The graph */}
        {rippleMap && dimensions.width > 0 && dimensions.height > 0 && (
          <>
            <RippleMapVisualization
              nodes={filteredNodes}
              edges={filteredEdges}
              width={dimensions.width}
              height={dimensions.height}
              onNodeClick={setSelectedNode}
              viewMode={viewMode}
            />

            <RippleMapFilters
              activeDomains={activeDomains}
              onToggleDomain={handleToggleDomain}
              generationIds={rippleMap.included_generation_ids}
              activeGenerationIds={activeGenerationIds}
              onToggleGeneration={handleToggleGeneration}
              onReset={handleResetFilters}
            />

            {selectedNode && (
              <RippleMapNodeDetail
                node={selectedNode}
                allNodes={rippleMap.nodes}
                allEdges={rippleMap.edges}
                onClose={() => setSelectedNode(null)}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ─── Spinner helper ───────────────────────────────────────────────────────────

function Spinner({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center gap-3">
      <div className="w-10 h-10 border border-gold border-t-transparent rounded-full animate-spin" />
      <p className="font-caption text-dim text-sm">{label}</p>
    </div>
  );
}
