/**
 * RippleMapVisualization
 *
 * D3 force-directed graph showing causal ripple effects from a historical deviation.
 * Nodes are coloured by domain, sized by magnitude, and positioned by time_offset_years.
 * Supports zoom/pan, drag, hover tooltips, click highlighting and a ripple animation.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import type { CausalNode, CausalEdge, CausalDomain, CausalRelationship, EdgeStrength, ConfidenceLevel } from '../types';

// ─── Constants ──────────────────────────────────────────────────────────────

// Quantum Manuscript palette — same mapping as RippleMapFilters & RippleMapNodeDetail
const DOMAIN_COLOR: Record<CausalDomain, string> = {
  political:    '#C0392B', // rubric
  economic:     '#6A8040', // success (olive)
  technological:'#4FC3F7', // quantum
  social:       '#D4A017', // gold
  cultural:     '#B8820A', // warning (amber)
  military:     '#8B2218', // rubric-dim
};

const CONFIDENCE_OPACITY: Record<ConfidenceLevel, number> = {
  high: 0.90,
  medium: 0.65,
  speculative: 0.40,
};

const EDGE_DASH: Record<EdgeStrength, string | null> = {
  direct: null,
  indirect: '8,4',
  subtle: '3,4',
};

const EDGE_WIDTH: Record<EdgeStrength, number> = {
  direct: 2,
  indirect: 1.5,
  subtle: 1,
};

const REL_COLOR: Record<CausalRelationship, string> = {
  causes:      '#C0392B', // rubric
  enables:     '#6A8040', // success
  prevents:    '#5A4E30', // faint
  accelerates: '#4FC3F7', // quantum
  weakens:     '#B8820A', // warning
  transforms:  '#D4A017', // gold
};

const nodeRadius = (magnitude: number) => 8 + magnitude * 5;

function getLinearGridTicks(ticks: number[], xScale: d3.ScaleLinear<number, number>): { t: number; x: number }[] {
  return ticks.map(t => ({ t, x: xScale(t) }));
}

function getRingInterval(maxOffset: number): { major: number; minor: number | null } {
  if (maxOffset <= 5)  return { major: 1,  minor: null };
  if (maxOffset <= 15) return { major: 5,  minor: 1    };
  if (maxOffset <= 40) return { major: 10, minor: 5    };
  return               { major: 20, minor: 10           };
}

// ─── Types ───────────────────────────────────────────────────────────────────

interface SimNode extends d3.SimulationNodeDatum {
  id: string;
  data: CausalNode;
}

interface SimLink extends d3.SimulationLinkDatum<SimNode> {
  data: CausalEdge;
}

// ─── Props ───────────────────────────────────────────────────────────────────

interface RippleMapVisualizationProps {
  nodes: CausalNode[];
  edges: CausalEdge[];
  width: number;
  height: number;
  onNodeClick: (node: CausalNode) => void;
  viewMode: 'linear' | 'radial';
}

// ─── Helper: apply highlight/dim styles ─────────────────────────────────────

function applySelectionStyles(
  selectedId: string | null,
  linkSel: d3.Selection<SVGLineElement, SimLink, SVGGElement, unknown>,
  circleSel: d3.Selection<SVGCircleElement, SimNode, SVGGElement, unknown>,
  labelSel: d3.Selection<SVGTextElement, SimNode, SVGGElement, unknown>
) {
  if (selectedId === null) {
    linkSel
      .attr('stroke', (d) => REL_COLOR[d.data.relationship])
      .attr('stroke-width', (d) => EDGE_WIDTH[d.data.strength])
      .attr('stroke-opacity', 0.55)
      .attr('marker-end', (d) => `url(#arrow-${d.data.relationship})`);
    circleSel
      .attr('fill-opacity', (d) => CONFIDENCE_OPACITY[d.data.confidence])
      .attr('stroke-opacity', 1);
    labelSel.attr('fill-opacity', 1);
    return;
  }

  // Build connected set
  const connectedIds = new Set<string>([selectedId]);
  const connectedLinks = new Set<SimLink>();
  linkSel.each((d) => {
    const src = (d.source as SimNode).id;
    const tgt = (d.target as SimNode).id;
    if (src === selectedId || tgt === selectedId) {
      connectedIds.add(src);
      connectedIds.add(tgt);
      connectedLinks.add(d);
    }
  });

  linkSel
    .attr('stroke', (d) => (connectedLinks.has(d) ? REL_COLOR[d.data.relationship] : '#2E2210'))
    .attr('stroke-width', (d) =>
      connectedLinks.has(d) ? EDGE_WIDTH[d.data.strength] + 1 : EDGE_WIDTH[d.data.strength]
    )
    .attr('stroke-opacity', (d) => (connectedLinks.has(d) ? 0.9 : 0.08))
    .attr('marker-end', (d) => (connectedLinks.has(d) ? `url(#arrow-${d.data.relationship})` : 'none'));

  circleSel
    .attr('fill-opacity', (d) =>
      connectedIds.has(d.id) ? CONFIDENCE_OPACITY[d.data.confidence] : 0.08
    )
    .attr('stroke-opacity', (d) => (connectedIds.has(d.id) ? 1 : 0.05));

  labelSel.attr('fill-opacity', (d) => (connectedIds.has(d.id) ? 1 : 0.15));
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function RippleMapVisualization({
  nodes,
  edges,
  width,
  height,
  onNodeClick,
  viewMode,
}: RippleMapVisualizationProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const simulationRef = useRef<d3.Simulation<SimNode, SimLink> | null>(null);
  const simLinksRef = useRef<SimLink[]>([]);
  const simNodesRef = useRef<SimNode[]>([]);
  const nodePositionsRef = useRef<Map<string, { x: number; y: number }>>(new Map());
  const zoomTransformRef = useRef<d3.ZoomTransform>(d3.zoomIdentity);
  const prevViewModeRef = useRef<'linear' | 'radial' | null>(null);
  const prevDimensionsRef = useRef<{ width: number; height: number } | null>(null);

  const [tooltip, setTooltip] = useState<{ x: number; y: number; node: CausalNode | null }>({
    x: 0,
    y: 0,
    node: null,
  });

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const selectedNodeIdRef = useRef<string | null>(null);
  selectedNodeIdRef.current = selectedNodeId;

  // ── Tooltip handlers ────────────────────────────────────────────────────────
  const handleMouseEnter = useCallback((event: MouseEvent, causalNode: CausalNode) => {
    const [x, y] = d3.pointer(event, document.body);
    setTooltip({ x, y, node: causalNode });
  }, []);

  const handleMouseLeave = useCallback(() => {
    setTooltip({ x: 0, y: 0, node: null });
  }, []);

  // ── BFS ripple animation ────────────────────────────────────────────────────
  const triggerRipple = useCallback((clickedId: string) => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    const simNodes = simNodesRef.current;
    const simLinks = simLinksRef.current;

    const nodeMap = new Map(simNodes.map((n) => [n.id, n]));
    const adjacency = new Map<string, string[]>();
    simNodes.forEach((n) => adjacency.set(n.id, []));
    simLinks.forEach((l) => {
      const src = (l.source as SimNode).id;
      const tgt = (l.target as SimNode).id;
      adjacency.get(src)?.push(tgt);
      adjacency.get(tgt)?.push(src);
    });

    const visited = new Set([clickedId]);
    const queue: Array<{ id: string; depth: number }> = [{ id: clickedId, depth: 0 }];
    const nodesLayer = svg.select<SVGGElement>('g.nodes-layer');

    while (queue.length > 0) {
      const { id, depth } = queue.shift()!;
      if (depth > 0) {
        const n = nodeMap.get(id);
        if (n && n.x !== undefined && n.y !== undefined) {
          const r = nodeRadius(n.data.magnitude);
          nodesLayer
            .append('circle')
            .attr('cx', n.x!)
            .attr('cy', n.y!)
            .attr('r', r)
            .attr('fill', 'none')
            .attr('stroke', DOMAIN_COLOR[n.data.domain])
            .attr('stroke-width', 2)
            .attr('stroke-opacity', 0.85)
            .attr('pointer-events', 'none')
            .transition()
            .delay(depth * 220)
            .duration(620)
            .ease(d3.easeQuadOut)
            .attr('r', r + 30)
            .attr('stroke-opacity', 0)
            .remove();
        }
      }
      for (const nb of adjacency.get(id) ?? []) {
        if (!visited.has(nb)) {
          visited.add(nb);
          queue.push({ id: nb, depth: depth + 1 });
        }
      }
    }
  }, []);

  // ── Main D3 effect ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (!svgRef.current) return;
    if (simulationRef.current) simulationRef.current.stop();

    // Read the SVG's actual rendered size from the DOM.  getBoundingClientRect()
    // is authoritative because the SVG is styled width/height: 100% and fills
    // its container exactly — so this always returns the true container size
    // regardless of what width/height props say.
    const { width: w, height: h } = svgRef.current.getBoundingClientRect();
    if (w === 0 || h === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    setSelectedNodeId(null);

    // ── Defs ────────────────────────────────────────────────────────────────
    const defs = svg.append('defs');

    // Glow filter for deviation point
    const glow = defs
      .append('filter')
      .attr('id', 'glow')
      .attr('x', '-50%').attr('y', '-50%')
      .attr('width', '200%').attr('height', '200%');
    const blur = glow.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'blur');
    blur; // suppress unused warning
    const merge = glow.append('feMerge');
    merge.append('feMergeNode').attr('in', 'blur');
    merge.append('feMergeNode').attr('in', 'SourceGraphic');

    // Arrowhead per relationship colour
    (Object.entries(REL_COLOR) as [CausalRelationship, string][]).forEach(([rel, color]) => {
      defs
        .append('marker')
        .attr('id', `arrow-${rel}`)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 18).attr('refY', 0)
        .attr('markerWidth', 6).attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', color)
        .attr('opacity', 0.75);
    });

    // Flat node gradients — vellum centre fades to domain color edge (manuscript ink wash)
    (Object.entries(DOMAIN_COLOR) as [CausalDomain, string][]).forEach(([domain, color]) => {
      const grad = defs
        .append('radialGradient')
        .attr('id', `glass-${domain}`)
        .attr('cx', '50%').attr('cy', '50%')
        .attr('r', '70%')
        .attr('gradientUnits', 'objectBoundingBox');
      grad.append('stop').attr('offset', '0%')
        .attr('stop-color', '#2E2210'); // surface
      grad.append('stop').attr('offset', '100%')
        .attr('stop-color', color);
    });

    // Empty state
    if (nodes.length === 0) {
      svg.append('text')
        .attr('x', w / 2).attr('y', h / 2)
        .attr('text-anchor', 'middle')
        .attr('fill', '#8A7A50')
        .attr('font-size', '12px')
        .attr('font-family', "'Source Code Pro', monospace")
        .text('No causal graph data available.');
      return;
    }

    // ── Time-axis scale ──────────────────────────────────────────────────────
    const offsets = nodes.map((n) => n.time_offset_years);
    const minT = Math.min(...offsets);
    const maxT = Math.max(...offsets);
    const xScale = d3
      .scaleLinear()
      .domain(minT === maxT ? [minT, minT + 1] : [minT, maxT])
      .range([w * 0.1, w * 0.9]);

    // ── Zoom container ───────────────────────────────────────────────────────
    // Reset zoom to identity when viewMode changes (re-centers radial on deviation
    // point); preserve the saved transform when only filters/nodes change.
    const viewModeChanged = prevViewModeRef.current !== null && prevViewModeRef.current !== viewMode;
    prevViewModeRef.current = viewMode;

    const prev = prevDimensionsRef.current;
    // Compare actual DOM dims (w, h) — not props — so any real container resize
    // clears stale node positions and re-centers the layout.
    const dimsShifted = prev !== null && (
      Math.abs(prev.width - w) > 20 || Math.abs(prev.height - h) > 20
    );
    prevDimensionsRef.current = { width: w, height: h };

    if (viewModeChanged || dimsShifted) {
      zoomTransformRef.current = d3.zoomIdentity;
      nodePositionsRef.current.clear(); // discard stale positions so layout starts centred
    }

    const zoomG = svg.append('g').attr('class', 'zoom-container');

    const zoomBehavior = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.2, 4])
      .on('zoom', (event) => {
        zoomTransformRef.current = event.transform;
        zoomG.attr('transform', event.transform.toString());
      });

    svg
      .call(zoomBehavior)
      .on('click', (event) => {
        if ((event.target as Element).tagName === 'svg') {
          setSelectedNodeId(null);
        }
      });

    // Apply saved (or reset) transform so zoomG always starts at the right position
    zoomG.attr('transform', zoomTransformRef.current.toString());
    svg.call(zoomBehavior.transform, zoomTransformRef.current);

    // ── Linear view: vertical time grid ──────────────────────────────────────
    if (viewMode === 'linear') {
      const gridGroup = zoomG.append('g').attr('class', 'time-grid').lower();
      const gridTicks = [...new Set(offsets)].sort((a, b) => a - b);
      const majorTicks = gridTicks.length <= 8 ? gridTicks : d3.ticks(minT, maxT, 8);

      getLinearGridTicks(majorTicks, xScale).forEach(({ t, x: tx }) => {
        gridGroup.append('line')
          .attr('x1', tx).attr('y1', 0)
          .attr('x2', tx).attr('y2', h)
          .attr('stroke', 'rgba(74,61,26,0.3)')
          .attr('stroke-width', 1)
          .attr('stroke-dasharray', '4,4')
          .attr('pointer-events', 'none');
        gridGroup.append('text')
          .attr('x', tx)
          .attr('y', 18)
          .attr('text-anchor', 'middle')
          .attr('fill', '#5A4E30')
          .attr('font-size', '10px')
          .attr('font-family', "'Source Code Pro', monospace")
          .attr('pointer-events', 'none')
          .text(`+${t}yr`);
      });

      svg.append('text')
        .attr('x', w / 2)
        .attr('y', h - 8)
        .attr('text-anchor', 'middle')
        .attr('fill', '#5A4E30')
        .attr('font-size', '10px')
        .attr('font-family', "'Source Code Pro', monospace")
        .attr('pointer-events', 'none')
        .text('Years after deviation point');
    }

    // ── Radial view: concentric ring background ────────────────────────────────
    const cx = w / 2;
    const cy = h / 2;

    if (viewMode === 'radial') {
      const ringGroup = zoomG.append('g').attr('class', 'radial-bg').lower();
      // Use maxT (absolute years from deviation) so rings align with node positions.
      const ringMax = maxT === 0 ? 1 : maxT;
      const { major: majorInt, minor: minorInt } = getRingInterval(ringMax);
      const ringRadiusScale = d3.scaleLinear()
        .domain([0, ringMax])
        .range([0, Math.min(w, h) * 0.44]);

      // Minor rings (absolute year values, matching radiusScale in simulation)
      if (minorInt) {
        for (let t = minorInt; t <= ringMax; t += minorInt) {
          if (t % majorInt === 0) continue;
          ringGroup.append('circle')
            .attr('cx', cx).attr('cy', cy)
            .attr('r', ringRadiusScale(t))
            .attr('fill', 'none')
            .attr('stroke', 'rgba(74,61,26,0.18)')
            .attr('stroke-width', 0.5)
            .attr('pointer-events', 'none');
        }
      }

      // Major rings + labels
      for (let t = majorInt; t <= ringMax; t += majorInt) {
        const r = ringRadiusScale(t);
        ringGroup.append('circle')
          .attr('cx', cx).attr('cy', cy)
          .attr('r', r)
          .attr('fill', 'none')
          .attr('stroke', 'rgba(122,92,16,0.35)')
          .attr('stroke-width', 1)
          .attr('pointer-events', 'none');
        ringGroup.append('text')
          .attr('x', cx)
          .attr('y', cy - r - 4)
          .attr('text-anchor', 'middle')
          .attr('fill', '#5A4E30')
          .attr('font-size', '10px')
          .attr('font-family', "'Source Code Pro', monospace")
          .attr('pointer-events', 'none')
          .text(`+${t}yr`);
      }

      // Centre dot label
      ringGroup.append('text')
        .attr('x', cx).attr('y', cy + 3)
        .attr('text-anchor', 'middle')
        .attr('fill', '#5A4E30')
        .attr('font-size', '9px')
        .attr('font-family', "'Source Code Pro', monospace")
        .attr('pointer-events', 'none')
        .text('deviation');
    }

    // ── Build sim data ───────────────────────────────────────────────────────

    const simNodes: SimNode[] = nodes.map((n) => {
      const saved = nodePositionsRef.current.get(n.id);
      return {
        id: n.id,
        data: n,
        x: saved?.x ?? (viewMode === 'radial' ? cx : xScale(n.time_offset_years)),
        y: saved?.y ?? cy + (Math.random() - 0.5) * 80,
      };
    });
    const nodeById = new Map(simNodes.map((n) => [n.id, n]));

    const simLinks: SimLink[] = edges
      .filter((e) => nodeById.has(e.source_node_id) && nodeById.has(e.target_node_id))
      .map((e) => ({
        source: nodeById.get(e.source_node_id)!,
        target: nodeById.get(e.target_node_id)!,
        data: e,
      }));

    simNodesRef.current = simNodes;
    simLinksRef.current = simLinks;

    // ── Simulation ───────────────────────────────────────────────────────────
    const maxR = Math.min(w, h) * 0.46;
    const radiusScale = d3.scaleLinear()
      .domain([0, maxT === minT ? 1 : maxT])
      .range([0, maxR]);

    // Pin deviation point to center in radial mode
    simNodes.forEach((n) => {
      if (viewMode === 'radial' && n.data.is_deviation_point) {
        n.fx = cx;
        n.fy = cy;
        n.x  = cx;
        n.y  = cy;
      } else {
        n.fx = null;
        n.fy = null;
      }
    });

    const simulation = d3
      .forceSimulation<SimNode, SimLink>(simNodes)
      .alphaDecay(0.022)
      .force('link', d3.forceLink<SimNode, SimLink>(simLinks).id((d) => d.id).distance(viewMode === 'linear' ? 130 : 180))
      .force('charge', d3.forceManyBody<SimNode>().strength(viewMode === 'linear' ? -300 : -600));

    if (viewMode === 'linear') {
      simulation
        .force('x', d3.forceX<SimNode>((d) => xScale(d.data.time_offset_years)).strength(0.85))
        .force('y', d3.forceY<SimNode>(cy).strength(0.06))
        .force('collide', d3.forceCollide<SimNode>((d) => nodeRadius(d.data.magnitude) + 7));
    } else {
      simulation
        .force('radial', d3.forceRadial<SimNode>(
          (d) => d.data.is_deviation_point ? 0 : radiusScale(d.data.time_offset_years),
          cx, cy
        ).strength(0.75))
        .force('collide', d3.forceCollide<SimNode>((d) => nodeRadius(d.data.magnitude) + 22));
    }

    simulationRef.current = simulation;

    // ── Edge layer ───────────────────────────────────────────────────────────
    const edgesLayer = zoomG.append('g').attr('class', 'edges-layer');
    const linkSel = edgesLayer
      .selectAll<SVGLineElement, SimLink>('line.edge')
      .data(simLinks)
      .join('line')
      .attr('class', 'edge')
      .attr('stroke', (d) => REL_COLOR[d.data.relationship])
      .attr('stroke-width', (d) => EDGE_WIDTH[d.data.strength])
      .attr('stroke-dasharray', (d) => EDGE_DASH[d.data.strength] ?? null)
      .attr('stroke-opacity', 0.55)
      .attr('marker-end', (d) => `url(#arrow-${d.data.relationship})`);

    // ── Node layer ───────────────────────────────────────────────────────────
    const nodesLayer = zoomG.append('g').attr('class', 'nodes-layer');
    const nodeGroups = nodesLayer
      .selectAll<SVGGElement, SimNode>('g.node-group')
      .data(simNodes)
      .join('g')
      .attr('class', 'node-group')
      .style('cursor', 'pointer');

    // Dashed outer ring for deviation point — gold, manuscript style
    nodeGroups
      .filter((d) => d.data.is_deviation_point)
      .append('circle')
      .attr('r', (d) => nodeRadius(d.data.magnitude) + 9)
      .attr('fill', 'none')
      .attr('stroke', '#D4A017')
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '4,3')
      .attr('stroke-opacity', 0.7)
      .attr('pointer-events', 'none');

    // Main circle — flat fill with vellum-to-domain gradient
    const circleSel = nodeGroups
      .append('circle')
      .attr('class', 'node-circle')
      .attr('r', (d) => nodeRadius(d.data.magnitude))
      .attr('fill', (d) => `url(#glass-${d.data.domain})`)
      .attr('fill-opacity', (d) => CONFIDENCE_OPACITY[d.data.confidence])
      .attr('stroke', (d) => d.data.is_deviation_point ? '#D4A017' : DOMAIN_COLOR[d.data.domain])
      .attr('stroke-width', (d) => d.data.is_deviation_point ? 1.5 : 1)
      .attr('stroke-opacity', 0.8)
      .attr('filter', (d) => (d.data.is_deviation_point ? 'url(#glow)' : null));

    // Label
    const labelSel = nodeGroups
      .append('text')
      .attr('class', 'node-label')
      .attr('dy', (d) => nodeRadius(d.data.magnitude) + 13)
      .attr('text-anchor', 'middle')
      .attr('fill', '#8A7A50')
      .attr('fill-opacity', 1)
      .attr('font-size', '10px')
      .attr('font-family', "'Source Code Pro', monospace")
      .attr('pointer-events', 'none')
      .text((d) => (d.data.label.length > 26 ? d.data.label.slice(0, 24) + '…' : d.data.label));

    // ── Drag ────────────────────────────────────────────────────────────────
    nodeGroups.call(
      d3
        .drag<SVGGElement, SimNode>()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        })
    );

    // ── Events ──────────────────────────────────────────────────────────────
    nodeGroups
      .on('mouseenter', (event: MouseEvent, d) => handleMouseEnter(event, d.data))
      .on('mouseleave', () => handleMouseLeave())
      .on('click', (event: MouseEvent, d) => {
        event.stopPropagation();
        const prev = selectedNodeIdRef.current;
        const next = d.id === prev ? null : d.id;
        setSelectedNodeId(next);
        applySelectionStyles(next, linkSel, circleSel, labelSel);
        if (next !== null) {
          onNodeClick(d.data);
          triggerRipple(d.id);
        }
      });

    // ── Tick ────────────────────────────────────────────────────────────────
    simulation.on('tick', () => {
      // Persist positions for warm-start on view switch
      simNodes.forEach((n) => {
        if (n.x !== undefined && n.y !== undefined) {
          nodePositionsRef.current.set(n.id, { x: n.x, y: n.y });
        }
      });
      linkSel
        .attr('x1', (d) => (d.source as SimNode).x ?? 0)
        .attr('y1', (d) => (d.source as SimNode).y ?? 0)
        .attr('x2', (d) => (d.target as SimNode).x ?? 0)
        .attr('y2', (d) => (d.target as SimNode).y ?? 0);
      nodeGroups.attr('transform', (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);
    });

    return () => { simulation.stop(); };
  }, [nodes, edges, width, height, handleMouseEnter, handleMouseLeave, triggerRipple, onNodeClick, viewMode]);

  // Re-apply styles when selection cleared externally (bg click)
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    applySelectionStyles(
      selectedNodeId,
      svg.selectAll<SVGLineElement, SimLink>('line.edge'),
      svg.selectAll<SVGCircleElement, SimNode>('circle.node-circle'),
      svg.selectAll<SVGTextElement, SimNode>('text.node-label')
    );
  }, [selectedNodeId]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <svg
        ref={svgRef}
        style={{ display: 'block', width: '100%', height: '100%', background: 'transparent' }}
      />

      {tooltip.node && (
        <div
          className="pointer-events-none fixed z-50 bg-parchment border border-border px-3 py-2"
          style={{
            left: tooltip.x + 16,
            top: tooltip.y + 12,
            maxWidth: 220,
          }}
        >
          <p className="font-mono text-[9px] tracking-widest uppercase mb-1" style={{ color: DOMAIN_COLOR[tooltip.node.domain] }}>
            § {tooltip.node.domain}
          </p>
          <p className="font-body text-ink text-xs leading-snug mb-1">{tooltip.node.label}</p>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[9px]" style={{ color: DOMAIN_COLOR[tooltip.node.domain] }}>
              {'●'.repeat(tooltip.node.magnitude)}
              <span style={{ color: '#4A3D1A' }}>{'●'.repeat(5 - tooltip.node.magnitude)}</span>
            </span>
            <span
              className="font-mono tracking-widest uppercase"
              style={{
                fontSize: 9,
                color: tooltip.node.confidence === 'high' ? '#6A8040'
                  : tooltip.node.confidence === 'medium' ? '#B8820A'
                  : '#5A4E30',
              }}
            >
              {tooltip.node.confidence}
            </span>
          </div>
          {tooltip.node.is_deviation_point && (
            <p className="mt-1.5 font-mono text-[9px] tracking-widest uppercase text-gold">
              ◈ Deviation Point
            </p>
          )}
        </div>
      )}
    </div>
  );
}
