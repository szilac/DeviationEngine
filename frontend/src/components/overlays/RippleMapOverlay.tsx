import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import type { Timeline, RippleMap, CausalNode, CausalDomain } from '../../types';
import { getRippleMap, generateRippleMap, addGenerationsToRippleMap } from '../../services/api';
import RippleMapVisualization from '../RippleMapVisualization';
import RippleMapFilters from '../RippleMapFilters';
import RippleMapNodeDetail from '../RippleMapNodeDetail';
import { X } from 'lucide-react';

interface RippleMapOverlayProps {
  open: boolean;
  onClose: () => void;
  timeline: Timeline;
}

export default function RippleMapOverlay({ open, onClose, timeline }: RippleMapOverlayProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  const [rippleMap, setRippleMap] = useState<RippleMap | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<CausalNode | null>(null);
  const [selectedGenIds, setSelectedGenIds] = useState<Set<string>>(new Set());
  const [viewMode, setViewMode] = useState<'linear' | 'radial'>('radial');
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  const [activeDomains, setActiveDomains] = useState<Set<CausalDomain>>(
    new Set(['political', 'economic', 'technological', 'social', 'cultural', 'military'])
  );
  const [activeGenerationIds, setActiveGenerationIds] = useState<Set<string>>(new Set());

  // Load ripple map on open
  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError(null);
    getRippleMap(timeline.id).then((res) => {
      if (res.data) {
        setRippleMap(res.data);
        setActiveGenerationIds(new Set(res.data.included_generation_ids));
      }
      setLoading(false);
    });
  }, [open, timeline.id]);

  // Resize observer
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDimensions({ width: entry.contentRect.width, height: entry.contentRect.height });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const allGenIds = timeline.generations.map((g) => g.id);
  const includedIds = new Set(rippleMap?.included_generation_ids ?? []);
  const newGenIds = allGenIds.filter((id) => !includedIds.has(id));

  const filteredNodes = useMemo(
    () =>
      rippleMap?.nodes.filter(
        (n) =>
          n.is_deviation_point ||
          (activeDomains.has(n.domain) &&
            (activeGenerationIds.size === 0 || activeGenerationIds.has(n.source_generation_id)))
      ) ?? [],
    [rippleMap, activeDomains, activeGenerationIds]
  );

  const filteredEdges = useMemo(() => {
    const ids = new Set(filteredNodes.map((n) => n.id));
    return rippleMap?.edges.filter((e) => ids.has(e.source_node_id) && ids.has(e.target_node_id)) ?? [];
  }, [rippleMap, filteredNodes]);

  const handleToggleDomain = useCallback((domain: CausalDomain) => {
    setActiveDomains((prev) => {
      const next = new Set(prev);
      if (next.has(domain) && next.size > 1) next.delete(domain);
      else next.add(domain);
      return next;
    });
  }, []);

  const handleToggleGeneration = useCallback((id: string) => {
    setActiveGenerationIds((prev) => {
      const next = new Set(prev);
      if (next.has(id) && next.size > 1) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleResetFilters = useCallback(() => {
    setActiveDomains(new Set(['political', 'economic', 'technological', 'social', 'cultural', 'military']));
    if (rippleMap) setActiveGenerationIds(new Set(rippleMap.included_generation_ids));
  }, [rippleMap]);

  const handleGenerate = async () => {
    if (selectedGenIds.size === 0) return;
    setGenerating(true);
    setError(null);
    const res = await generateRippleMap(timeline.id, [...selectedGenIds]);
    if (res.data) {
      setRippleMap(res.data);
      setActiveGenerationIds(new Set(res.data.included_generation_ids));
    } else {
      setError(res.error?.message ?? 'Generation failed.');
    }
    setGenerating(false);
  };

  const handleAddGenerations = async () => {
    if (newGenIds.length === 0) return;
    setGenerating(true);
    setError(null);
    const res = await addGenerationsToRippleMap(timeline.id, newGenIds);
    if (res.data) {
      setRippleMap(res.data);
      setActiveGenerationIds(new Set(res.data.included_generation_ids));
    } else {
      setError(res.error?.message ?? 'Failed to add generations.');
    }
    setGenerating(false);
  };

  return (
    <AnimatePresence>
    {open && (
    <motion.div
      className="fixed inset-0 z-50 bg-vellum flex flex-col"
      initial={{ opacity: 0, scale: 1.015 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 1.015 }}
      transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
    >
      {/* Header */}
      <div className="px-6 py-3 border-b border-border flex items-center gap-4 shrink-0">
        <div className="flex-1 min-w-0">
          <p className="rubric-label">§ Ripple Map</p>
          <h2 className="font-display text-lg text-gold leading-tight truncate">
            {timeline.timeline_name || timeline.root_deviation_description}
          </h2>
        </div>

        {rippleMap && (
          <div className="flex items-center gap-3 shrink-0">
            {/* View toggle */}
            <div className="flex border border-border">
              {(['radial', 'linear'] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setViewMode(mode)}
                  className={[
                    'px-3 py-1 font-mono text-[10px] tracking-widest uppercase transition-colors cursor-pointer',
                    viewMode === mode ? 'bg-surface text-gold' : 'text-faint hover:text-dim',
                    mode === 'radial' ? 'border-r border-border' : '',
                  ].join(' ')}
                >
                  {mode === 'radial' ? '⊚ Radial' : '⟶ Linear'}
                </button>
              ))}
            </div>
            {/* Stats */}
            <div className="font-mono text-[9px] text-faint hidden sm:flex items-center gap-3">
              <span>{rippleMap.total_nodes} nodes</span>
              {rippleMap.dominant_domain && <span className="capitalize">{rippleMap.dominant_domain}</span>}
              {rippleMap.max_ripple_depth > 0 && <span>depth {rippleMap.max_ripple_depth}</span>}
            </div>
          </div>
        )}

        <button
          onClick={onClose}
          className="text-dim hover:text-ink transition-colors cursor-pointer shrink-0 p-1"
        >
          <X size={16} />
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="px-5 py-2 border-b border-rubric-dim flex items-center justify-between shrink-0">
          <p className="font-mono text-[10px] text-rubric">{error}</p>
          <button onClick={() => setError(null)} className="text-rubric hover:text-ink cursor-pointer ml-4">
            <X size={12} />
          </button>
        </div>
      )}

      {/* Add-generations banner */}
      {rippleMap && newGenIds.length > 0 && !generating && (
        <div className="px-5 py-2 border-b border-gold-dim/40 flex items-center gap-3 shrink-0">
          <span className="font-mono text-[10px] text-gold">
            {newGenIds.length} new chronicle{newGenIds.length > 1 ? 's' : ''} available
          </span>
          <button
            onClick={handleAddGenerations}
            className="font-mono text-[10px] uppercase tracking-widest border border-gold-dim text-gold hover:border-gold px-3 py-1 transition-colors cursor-pointer"
          >
            Add to Ripple Map
          </button>
        </div>
      )}

      {/* Main area */}
      <div className="flex-1 relative overflow-hidden" ref={containerRef}>

        {/* Loading */}
        {(loading || generating) && (
          <div className="absolute inset-0 z-30 flex flex-col items-center justify-center bg-vellum/80 backdrop-blur-sm">
            <span className="w-6 h-6 border border-gold border-t-transparent animate-spin mb-3" />
            <p className="font-mono text-[10px] tracking-widest uppercase text-dim">
              {generating ? 'Generating causal graph…' : 'Loading ripple map…'}
            </p>
          </div>
        )}

        {/* Generation picker (no map yet) */}
        {!loading && !rippleMap && !generating && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <div className="bg-parchment border border-border p-8 max-w-md w-full mx-4 corner-brackets space-y-5">
              <p className="rubric-label">§ Generate Ripple Map</p>
              <p className="font-body text-sm text-dim leading-relaxed">
                The Ripple Analyst agent will extract causal nodes and edges from the selected
                chronicles and build an interactive causal graph.
              </p>

              <div className="space-y-2">
                <label className="font-mono text-[10px] tracking-widest uppercase text-faint block mb-2">
                  Select Chronicles
                </label>
                {timeline.generations.map((gen, idx) => {
                  const checked = selectedGenIds.has(gen.id);
                  return (
                    <div
                      key={gen.id}
                      onClick={() => setSelectedGenIds((prev) => {
                        const next = new Set(prev);
                        if (next.has(gen.id)) next.delete(gen.id);
                        else next.add(gen.id);
                        return next;
                      })}
                      className={[
                        'flex items-center gap-3 px-3 py-2.5 border cursor-pointer transition-colors',
                        checked ? 'border-gold-dim bg-surface' : 'border-border hover:border-gold-dim/50',
                      ].join(' ')}
                    >
                      <div className={`w-3 h-3 border shrink-0 flex items-center justify-center ${checked ? 'border-gold' : 'border-border'}`}>
                        {checked && <div className="w-1.5 h-1.5 bg-gold" />}
                      </div>
                      <div>
                        <div className={`font-mono text-[11px] tracking-widest ${checked ? 'text-gold' : 'text-ink'}`}>
                          Chronicle {idx + 1}
                        </div>
                        <div className="font-mono text-[9px] text-faint">
                          {gen.start_year}–{gen.end_year} · {gen.period_years} years
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              <button
                onClick={handleGenerate}
                disabled={selectedGenIds.size === 0}
                className={[
                  'w-full px-5 py-2.5 font-mono text-[10px] tracking-widest uppercase border transition-colors',
                  selectedGenIds.size > 0
                    ? 'border-gold text-gold hover:bg-gold/10 cursor-pointer'
                    : 'border-border text-faint cursor-not-allowed opacity-50',
                ].join(' ')}
              >
                § Generate Ripple Map
              </button>
            </div>
          </div>
        )}

        {/* The visualization */}
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
    </motion.div>
    )}
    </AnimatePresence>
  );
}
