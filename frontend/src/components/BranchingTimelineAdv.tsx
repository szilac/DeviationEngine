/**
 * BranchingTimeline Component (Redesigned)
 *
 * - Curved living branches (glow, gradient, dash drift, particles)
 * - Main timeline with dual-layer baseline + energy track
 * - Ribbons of uncertainty
 * - Noise + cursor-force deflection
 * - Zoom/Pan with axis rescale
 * - Prefers-reduced-motion aware
 * - Historical events intentionally omitted
 */

import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { createNoise2D } from 'simplex-noise';
import alea from 'alea';

// API base URL - uses environment variable or defaults to localhost for development
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface TimelineListItem {
  id: string;
  root_deviation_date: string;
  root_deviation_description: string;
  generation_count: number;
  created_at: string;
}

interface Generation {
  id: string;
  start_year: number;
  end_year: number;
  period_years: number;
  generation_order: number;
  executive_summary: string;
  created_at: string;
}

interface FullTimeline {
  id: string;
  root_deviation_date: string;
  root_deviation_description: string;
  scenario_type: string;
  generations: Generation[];
  created_at: string;
}

interface BranchingTimelineProps {
  selectedTimeline?: TimelineListItem;
  selectedTimelines?: TimelineListItem[];
  onTimelineClick?: (timelineId: string) => void;
  className?: string;
}

interface TooltipData {
  content: string;
  x: number;
  y: number;
  visible: boolean;
}

const BranchingTimeline: React.FC<BranchingTimelineProps> = ({
  selectedTimeline,
  selectedTimelines,
  onTimelineClick,
  className = ''
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [groundTruthReports, setGroundTruthReports] = useState<any[]>([]);
  const [fullTimeline, setFullTimeline] = useState<FullTimeline | null>(null);
  const [fullTimelines, setFullTimelines] = useState<Map<string, FullTimeline>>(new Map());
  const [tooltip, setTooltip] = useState<TooltipData>({ content: '', x: 0, y: 0, visible: false });
  const [enableAnimations, setEnableAnimations] = useState<boolean>(false);

  // Color palette — Quantum Manuscript tokens
  const BRANCH_COLOR = '#9E4A3A'; // rubric sanguine — red ink for alternate history branches

  // Timeline configuration
  const TIMELINE_START = 1870;
  const TIMELINE_END = 2010;
  const SVG_WIDTH = 1000;

  const BRANCH_SPACING = 25;
  const PADDING_TOP = 200;
  const PADDING_BOTTOM = 300;
  // Maximum lanes above and below the main line; earliest deviations occupy the outermost lanes.
  const maxTimelinesPerSide = 3;
  const SVG_HEIGHT = PADDING_TOP + PADDING_BOTTOM + (maxTimelinesPerSide * BRANCH_SPACING * 2);
  const MAIN_TIMELINE_Y = PADDING_TOP + (maxTimelinesPerSide * BRANCH_SPACING);

  // Branching particle configuration (routing-aware layer)
  const BRANCHING_PARTICLE_COUNT = 60;
  const BRANCHING_PARTICLE_RADIUS = 3;
  const BRANCHING_PARTICLE_COLOR = '#E8D8A0'; // ink — parchment particles
  const BRANCHING_PARTICLE_OPACITY = 0.30; // Very transparent
  const BRANCH_SPLIT_PROBABILITY = 0.15; // 25% chance per deviation encounter
  const BRANCHING_MAIN_DURATION_RANGE: [number, number] = [15000, 25000]; // Slower, more ethereal
  const BRANCHING_BRANCH_DURATION_RANGE: [number, number] = [8000, 15000];
  const DEVIATION_HIT_TOLERANCE_FACTOR = 0.003;

  type LaneSide = 'above' | 'below';

  interface LaneAssignment {
    laneIndex: number; // 0 is closest to main; larger is further out
    side: LaneSide;
  }

  // Given a side and lane index, compute the absolute Y position.
  const getTimelineYForLane = (side: LaneSide, laneIndex: number): number => {
    const offset = BRANCH_SPACING * (laneIndex + 1);
    return side === 'above'
      ? MAIN_TIMELINE_Y - offset
      : MAIN_TIMELINE_Y + offset;
  };

  const getTimelineColor = (_index: number): string => BRANCH_COLOR;

  const calculateSafeTooltipPosition = (
    mouseX: number,
    mouseY: number,
    tooltipWidth = 220,
    tooltipHeight = 56
  ): { x: number; y: number } => {
    const padding = 12;
    const offsetY = 10;
    const viewportWidth = window.innerWidth || 1024;
    const viewportHeight = window.innerHeight || 768;

    // Start centered horizontally on cursor, above by default
    let x = mouseX;
    let y = mouseY - offsetY - tooltipHeight;

    // If there is not enough space above, flip below
    if (y < padding) {
      y = mouseY + offsetY;
    }

    // Clamp horizontally so tooltip never overflows viewport
    const halfW = tooltipWidth / 2;
    if (x - halfW < padding) x = padding + halfW;
    if (x + halfW > viewportWidth - padding) x = viewportWidth - padding - halfW;

    // Clamp vertically inside viewport
    if (y < padding) y = padding;
    if (y + tooltipHeight > viewportHeight - padding) {
      y = Math.max(padding, viewportHeight - padding - tooltipHeight);
    }

    return { x, y };
  };

  // Load ground truth reports
  useEffect(() => {
    const fetchGroundTruthReports = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/ground-truth-reports`);
        if (response.ok) {
          const reports = await response.json();
          setGroundTruthReports(reports);
        }
      } catch (error) {
        console.error('Error fetching ground truth reports:', error);
      }
    };
    fetchGroundTruthReports();
  }, []);

  // Load full timeline data (legacy single)
  useEffect(() => {
    if (!selectedTimeline) {
      setFullTimeline(null);
      return;
    }
    const fetchFullTimeline = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/timeline/${selectedTimeline.id}`);
        if (response.ok) {
          const timelineData = await response.json();
          setFullTimeline(timelineData);
        }
      } catch (error) {
        console.error('Error fetching full timeline:', error);
      }
    };
    fetchFullTimeline();
  }, [selectedTimeline]);

  // Load multiple full timelines
  useEffect(() => {
    if (!selectedTimelines || selectedTimelines.length === 0) {
      setFullTimelines(new Map());
      return;
    }
    const fetchAllTimelines = async () => {
      const newFullTimelines = new Map<string, FullTimeline>();
      await Promise.all(
        selectedTimelines.map(async (timeline) => {
          try {
            const response = await fetch(`${API_BASE_URL}/api/timeline/${timeline.id}`);
            if (response.ok) {
              const timelineData = await response.json();
              newFullTimelines.set(timeline.id, timelineData);
            }
          } catch (error) {
            console.error(`Error fetching timeline ${timeline.id}:`, error);
          }
        })
      );
      setFullTimelines(newFullTimelines);
    };
    fetchAllTimelines();
  }, [selectedTimelines]);

  // D3 visualization
  useEffect(() => {
    if (!svgRef.current) return;

    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    // Base scales
    const xScale = d3.scaleLinear()
      .domain([TIMELINE_START, TIMELINE_END])
      .range([50, SVG_WIDTH - 50]);

    // Root groups
    const root = svg.append('g').attr('class', 'root');
    const axisG = root.append('g').attr('class', 'axisG');
    const contentG = root.append('g').attr('class', 'contentG');
    const gridG = contentG.append('g').attr('class', 'gridG');
    const mainG = contentG.append('g').attr('class', 'main-track');

    // Defs: glow + gradient
    const defs = svg.append('defs');

    const glow = defs.append('filter')
      .attr('id', 'soft-glow')
      .attr('x', '-30%').attr('y', '-30%')
      .attr('width', '160%').attr('height', '160%')
      .attr('filterUnits', 'userSpaceOnUse');
    glow.append('feGaussianBlur')
      .attr('in', 'SourceGraphic').attr('stdDeviation', 2).attr('result', 'blur');
    const fm = glow.append('feMerge');
    fm.append('feMergeNode').attr('in', 'blur');
    fm.append('feMergeNode').attr('in', 'SourceGraphic');

    function ensureGradient(id: string, base: string) {
      let g = defs.select(`#${id}`) as d3.Selection<SVGLinearGradientElement, unknown, null, undefined>;
      if (g.empty()) {
        g = defs.append('linearGradient').attr('id', id)
          .attr('x1', '0%').attr('x2', '100%')
          .attr('y1', '0%').attr('y2', '0%');
        g.append('stop').attr('offset', '0%').attr('stop-color', base).attr('stop-opacity', 0.9);
        g.append('stop').attr('offset', '100%').attr('stop-color', base).attr('stop-opacity', 0.5);
      }
      return `url(#${id})`;
    }

    // Axis (decades), lives outside contentG so it's not transformed; rescaled on zoom
    const decades = d3.range(TIMELINE_START, TIMELINE_END + 1, 10);
    const axisBottom = d3.axisBottom(xScale)
      .tickValues(decades)
      .tickFormat(d3.format('d') as any)
      .tickSizeOuter(0);
    axisG
      .attr('transform', `translate(0, ${MAIN_TIMELINE_Y + 32})`)
      .call(axisBottom as any);
    axisG.selectAll('path, line')
      .attr('stroke', '#4A3D1A')
      .attr('vector-effect', 'non-scaling-stroke');
    axisG.selectAll('text')
      .attr('fill', '#8A7A50')
      .attr('font-size', 11)
      .attr('font-family', "'Source Code Pro', monospace")
      .attr('font-weight', 400);

    // Faint decade grid lines (drawn into gridG, which sits behind all content)
    decades.forEach(year => {
      gridG.append('line')
        .attr('x1', xScale(year))
        .attr('x2', xScale(year))
        .attr('y1', 0)
        .attr('y2', SVG_HEIGHT)
        .attr('stroke', '#4A3D1A')
        .attr('stroke-opacity', 0.18)
        .attr('stroke-width', 0.5)
        .attr('vector-effect', 'non-scaling-stroke');
    });

    // Cloud-style stroke animation: subtle wandering + alpha pulse; replaces dashed look.
    function animateCloudStroke(
      sel: d3.Selection<SVGPathElement, unknown, any, any>,
      baseOpacity = 0.55,
      thickness = 7
    ) {
      if (reduceMotion) {
        sel
          .attr('stroke-width', thickness)
          .attr('stroke-linecap', 'round')
          .attr('stroke-linejoin', 'round')
          .attr('opacity', baseOpacity)
          .attr('stroke-dasharray', null);
        return { stop: () => {} };
      }

      sel
        .attr('stroke-width', thickness)
        .attr('stroke-linecap', 'round')
        .attr('stroke-linejoin', 'round')
        .attr('stroke-dasharray', null);

      let frameId: number;
      const noise = createNoise2D(alea('cloud-stroke'));
      const start = performance.now();

      const tick = () => {
        const t = (performance.now() - start) / 4000;
        // soft opacity breathing
        const alpha = baseOpacity + 0.12 * Math.sin(t * 2 * Math.PI);
        // micro jitter so segments feel vaporous rather than one rigid body
        const wobble = 0.85 + 0.35 * noise(0.6, t * 1.4);
        sel
          .attr('opacity', alpha)
          .attr('stroke-width', thickness * wobble);
        frameId = requestAnimationFrame(tick);
      };

      frameId = requestAnimationFrame(tick);
      return {
        stop: () => {
          if (frameId) cancelAnimationFrame(frameId);
        }
      };
    }

    // Shared pointer state in content coordinates (not screen)
    const pointer = { x: 0, y: 0, active: false };
    let currentTransform = d3.zoomIdentity;

    // Types for routing-aware branching particles
    type BranchMeta = {
      id: string;
      color: string;
      branchPath: SVGPathElement;
      deviationX: number;
      branchTotalLength: number;
    };

    type DeviationRouterEntry = {
      mainLength: number;
      branches: BranchMeta[];
    };

    // Geometry references for routing particles (effect-local, cleaned via track/cleanup)
    const branchesMeta: BranchMeta[] = [];
    let mainPath: SVGPathElement | null = null;
    let mainTotalLength = 0;
    let deviationRouter: DeviationRouterEntry[] = [];

    function attachPointerHandlers(svgSel: d3.Selection<SVGSVGElement, unknown, any, any>) {
      svgSel
        .on('pointerenter', () => { pointer.active = true; })
        .on('pointermove', (event: PointerEvent) => {
          const [sx, sy] = d3.pointer(event, svgSel.node());
          pointer.x = currentTransform.invertX(sx);
          pointer.y = currentTransform.invertY(sy);
          pointer.active = true;
        })
        .on('pointerleave', () => { pointer.active = false; });
    }

    // Reactive path (noise + cursor force)
    function deflectedWavyPath(
      xScale: d3.ScaleLinear<number, number>,
      startYear: number,
      endYear: number,
      baseY: number,
      seed: string,
      ampNoise = 1.2,
      spring = 0.06,
      damping = 0.85
    ) {
      const makeNoise2D = (s: string) => createNoise2D(alea(s));
      // Use finer segmentation so the cloud feels composed of many smaller segments
      const span = Math.max(1, endYear - startYear);
      const steps = Math.max(132, Math.min(480, Math.floor(span * 8))); // higher resolution than before
      const noise2D = makeNoise2D(seed);

      type Pt = { x: number; y0: number; y: number; v: number; year: number };
      const pts: Pt[] = [];

      for (let i = 0; i <= steps; i++) {
        const t = i / steps;
        const year = startYear + t * (endYear - startYear);
        const x = xScale(year);
        pts.push({ x, y0: baseY, y: baseY, v: 0, year });
      }

      const lineGen = d3.line<[number, number]>()
        .curve(d3.curveCatmullRom.alpha(0.7)); // slightly tighter curve for smoother micro-movements

      const pathSel = d3.create('svg:path').attr('fill', 'none');
      const t0 = performance.now();

      if (reduceMotion) {
        const displayStatic = pts.map(p => [p.x, p.y0] as [number, number]);
        pathSel.attr('d', lineGen(displayStatic) || '');
        return { node: pathSel.node() as SVGPathElement, stop: () => {} };
      }

      // Set initial d attribute so getTotalLength() works immediately
      const initialDisplay = pts.map(p => [p.x, p.y] as [number, number]);
      pathSel.attr('d', lineGen(initialDisplay) || '');

      const timer = d3.timer((now) => {
        const time = (now - t0) / 4500;

        for (const p of pts) {
          // higher-frequency noise in x/y-space to break up large rigid chunks
          const noise = noise2D(p.year * 0.18, time) * ampNoise;

          let deflect = 0;
          // Cursor force feedback disabled on main line for calmer behavior.
          // if (pointer.active) {
          //   const dx = p.x - pointer.x;
          //   const w = Math.exp(-(dx * dx) / (2 * sigmaPx * sigmaPx));
          //   const dir = p.y0 > pointer.y ? 1 : -1;
          //   deflect = ampCursor * w * dir;
          // }

          const target = p.y0 + noise + deflect;
          const accel = (target - p.y) * spring;
          p.v = (p.v + accel) * damping;
          p.y += p.v;
        }

        const display = pts.map(p => [p.x, p.y] as [number, number]);
        pathSel.attr('d', lineGen(display) || '');
      });

      return { node: pathSel.node() as SVGPathElement, stop: () => timer.stop() };
    }

    function mainEnergyPath(params: {
      xScale: d3.ScaleLinear<number, number>;
      startYear: number;
      endYear: number;
      baseY: number;
      seed?: string;
      ampNoise?: number;
      ampCursor?: number;
      sigmaPx?: number;
      spring?: number;
      damping?: number;
    }) {
      const {
        xScale, startYear, endYear, baseY,
        seed = 'main', ampNoise = 0.8 // ampCursor, sigmaPx, spring, damping are fixed in deflectedWavyPath
       } = params;
       // Main line: use a gentle wavy path with noise only; cursor force is disabled inside deflectedWavyPath.
       return deflectedWavyPath(
         xScale,
         startYear,
         endYear,
         baseY,
         seed,
         ampNoise
       );
    }

    // Track timers/animations to clean up
    const cleaners: Array<() => void> = [];
    const track = (stopper?: { stop: () => void }) => {
      if (!stopper) return;
      cleaners.push(() => stopper.stop());
    };

    // Attach pointer and zoom
    attachPointerHandlers(svg);

    // Zoom/Pan: transform contentG; rescale axis
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.8, 10])
      .translateExtent([[0, 0], [SVG_WIDTH, SVG_HEIGHT]])
      .on('zoom', (event) => {
        currentTransform = event.transform;
        contentG.attr('transform', currentTransform.toString());
        const zx = currentTransform.rescaleX(xScale);
        (axisBottom as any).scale(zx);
        axisG.call(axisBottom as any);
        axisG.selectAll('path, line').attr('vector-effect', 'non-scaling-stroke');
      });
    svg.call(zoom as any);

    // Main timeline layers

    // Baseline hairline (straight)
    mainG.append('line')
      .attr('x1', xScale(TIMELINE_START))
      .attr('y1', MAIN_TIMELINE_Y)
      .attr('x2', xScale(TIMELINE_END))
      .attr('y2', MAIN_TIMELINE_Y)
      .attr('stroke', '#7A5C10')
      .attr('stroke-width', 3)
      .attr('opacity', 0.5)
      .attr('vector-effect', 'non-scaling-stroke');

    // Energy track (wavy/deflected) with cloud-like appearance
    const energy = mainEnergyPath({
      xScale,
      startYear: TIMELINE_START,
      endYear: TIMELINE_END,
      baseY: MAIN_TIMELINE_Y,
      seed: 'main-track',
      ampNoise: reduceMotion ? 0 : 0.8,
      ampCursor: 0,
      sigmaPx: 160,
    });
    const energySel = d3.select(energy.node)
      .attr('stroke', ensureGradient('main-grad', '#D4A017'))
      .attr('stroke-width', 5)
      .attr('opacity', 0.6)
      .attr('vector-effect', 'non-scaling-stroke')
      .attr('filter', 'url(#soft-glow)')
      .attr('stroke-dasharray', null);
    mainG.node()?.appendChild(energy.node);
    track(energy);

    // Capture main path geometry for routing-aware particles
    mainPath = energy.node as SVGPathElement;
    if (mainPath) {
      const len = mainPath.getTotalLength();
      if (Number.isFinite(len) && len > 0) {
        mainTotalLength = len;
      }
    }

    // Cloud-style soft wandering stroke instead of dashed line
    if (enableAnimations) {
      const cloudMainStop = animateCloudStroke(energySel as any, 0.55, 8);
      track(cloudMainStop);
    }
    // Old particle system removed - using routing-aware branching particles instead
    // const particlesMainStop = animateParticles(energy.node, '#a7f3d0', 3);
    // track(particlesMainStop);

    // Ground truth segments (aligned to baseline; keep stable hit targets)
    if (groundTruthReports.length > 0) {
      contentG.selectAll('.ground-truth-segment')
        .data(groundTruthReports)
        .enter()
        .append('rect')
        .attr('class', 'ground-truth-segment')
        .attr('x', (d: any) => xScale(d.start_year))
        .attr('y', MAIN_TIMELINE_Y - 5) // position directly on the main timeline line
        .attr('width', (d: any) => Math.max(4, xScale(d.end_year) - xScale(d.start_year)))
        .attr('height', 10)
        .attr('fill', 'transparent') // invisible but interactive
        .attr('opacity', 0)          // ensure no visible color
        .attr('rx', 3)
        .attr('vector-effect', 'non-scaling-stroke')
        .style('cursor', 'pointer')
        .on('mouseenter', (event: PointerEvent, d: any) => {
          const [mouseX, mouseY] = d3.pointer(event, document.body as any);
          const { x, y } = calculateSafeTooltipPosition(mouseX, mouseY);
          setTooltip({
            content: `${d.title || 'Historical Report'}: Click to view`,
            x, y, visible: true
          });
        })
        .on('mouseleave', () => setTooltip(prev => ({ ...prev, visible: false })))
        .on('click', (_event: any, d: any) => {
          if (onTimelineClick) onTimelineClick(`ground-truth:${d.id}`);
        });
    }

    // Branches rendering

    // Compute stable, non-crossing lane assignments:
    // - We keep using the existing alternating side pattern (even index -> above, odd -> below)
    //   so that visual layout remains familiar.
    // - Within each side, we sort by deviation year ASC.
    // - Earliest deviation on that side gets the OUTERMOST lane (largest laneIndex),
    //   later deviations move inward. This guarantees vertical ordering never inverts,
    //   so branches do not cross.
    const laneAssignments = new Map<string, LaneAssignment>();

    const assignLanes = (timelines: TimelineListItem[]) => {
      if (!timelines || timelines.length === 0) return;

      type WithMeta = {
        timeline: TimelineListItem;
        index: number;
        deviationYear: number;
        side: LaneSide;
      };

      const metas: WithMeta[] = timelines.map((tl, idx) => {
        const deviationYear = new Date(tl.root_deviation_date).getFullYear();
        const side: LaneSide = idx % 2 === 0 ? 'above' : 'below';
        return { timeline: tl, index: idx, deviationYear, side };
      });

      // Group by side, then assign lanes independently per side.
      (['above', 'below'] as LaneSide[]).forEach((side) => {
        const group = metas.filter(m => m.side === side);
        if (group.length === 0) return;

        // Sort by deviation date ascending (earliest first).
        group.sort((a, b) => a.deviationYear - b.deviationYear);

        // Earliest -> outermost lane (max index); later -> move inward.
        // This matches the requirement "earliest deviation is on the outermost lane".
        const maxIndex = Math.min(maxTimelinesPerSide, group.length) - 1;

        group.forEach((meta, i) => {
          const laneIndex = Math.max(0, maxIndex - i);
          laneAssignments.set(meta.timeline.id, { laneIndex, side });
        });
      });
    };

    // Precompute assignments for the current selection set.
    if (selectedTimelines && selectedTimelines.length > 0) {
      assignLanes(selectedTimelines);
    } else if (selectedTimeline) {
      // Single branch: default to above, closest lane.
      laneAssignments.set(selectedTimeline.id, { laneIndex: 0, side: 'above' });
    }

    function renderBranch(timeline: TimelineListItem, index: number, full: FullTimeline) {
      const assignment = laneAssignments.get(timeline.id);
      const color = getTimelineColor(index);
      const branchY = assignment
        ? getTimelineYForLane(assignment.side, assignment.laneIndex)
        : getTimelineYForLane(index % 2 === 0 ? 'above' : 'below', 0);
      const deviationYear = new Date(timeline.root_deviation_date).getFullYear();
      const deviationX = xScale(deviationYear);

      const totalSimulationYears = full.generations && full.generations.length > 0
        ? Math.max(...full.generations.map(g => g.end_year))
        : 0;
      const endYear = deviationYear + totalSimulationYears;

      // Use the actual end year (no visual shift) so the branch end aligns with the x-axis date.
      const endVisual = Math.min(endYear, TIMELINE_END);
      const branchEndX = xScale(endVisual);

      const grad = ensureGradient(`branch-grad-${index}`, color);

      // Build a smooth, graceful branch path:
      // - Starts at deviation on the main line
      // - Eases toward target branchY
      // - As X increases, asymptotically approaches branchY (never a hard "elbow")
      // - If the branch doesn't reach full height within its timespan, that's fine:
      //   extensions can continue it later.
      const continuousPts: [number, number][] = [];

      const spanX = branchEndX - deviationX;
      const steps = Math.max(48, Math.min(220, Math.floor(spanX / 6)));

      for (let i = 0; i <= steps; i++) {
        const t = i / steps; // 0..1 along branch lifespan
        const x = deviationX + t * spanX;

        // Smooth easing for vertical offset:
        // near deviation: close to main line
        // further along: approaches branchY
        const ease = 1 - Math.exp(-3 * t); // exponential ease toward 1
        const y = MAIN_TIMELINE_Y + ease * (branchY - MAIN_TIMELINE_Y);

        continuousPts.push([x, y]);
      }

      const branchBaseLine = d3.line<[number, number]>()
        .curve(d3.curveCatmullRom.alpha(0.7));

      // Paths for base and energy line; we'll drive them via a timer (loose rope)
      const branchBasePath = contentG.append('path')
        .attr('stroke', grad)
        .attr('fill', 'none')
        .attr('stroke-linecap', 'round')
        .attr('opacity', 0.6)
        .attr('filter', 'url(#soft-glow)')
        .attr('vector-effect', 'non-scaling-stroke');

      const branchEnergyPath = contentG.append('path')
        .attr('fill', 'none')
        .attr('stroke', grad)
        .attr('stroke-width', 3)
        .attr('stroke-linecap', 'round')
        .attr('opacity', 0.9)
        .attr('vector-effect', 'non-scaling-stroke')
        .attr('stroke-dasharray', null)
        .attr('filter', 'url(#soft-glow)');

      // Seed initial static curve for branchEnergyPath so getPointAtLength is valid immediately.
      if (continuousPts.length > 1) {
        const initialD = branchBaseLine(continuousPts) || '';
        branchBasePath.attr('d', initialD);
        branchEnergyPath.attr('d', initialD);
      }

      // Floating end anchor (small random drift in a circle)
      const floatNoise = createNoise2D(alea(`${timeline.id}-end-float`));
      const floatRadius = 7; // px, subtle
      const floatSpeed = 0.11;

      // Precompute base parametric positions (t in [0,1]) for samples
      const sampleCount = Math.max(48, Math.min(220, Math.floor((branchEndX - deviationX) / 6)));
      const samples = d3.range(sampleCount + 1).map((i) => i / sampleCount);

      if (reduceMotion || !enableAnimations) {
        // Static graceful curve without floating behavior
        const EASE_MAX = 1 - Math.exp(-3); // ≈0.9502 — normalise so t=1 reaches exactly branchY
        const staticPts = samples.map((t) => {
          const x = deviationX + t * (branchEndX - deviationX);
          const ease = (1 - Math.exp(-3 * t)) / EASE_MAX;
          const y = MAIN_TIMELINE_Y + ease * (branchY - MAIN_TIMELINE_Y);
          return [x, y] as [number, number];
        });
        const dBase = branchBaseLine(staticPts) || '';
        branchBasePath.attr('d', dBase);
        branchEnergyPath.attr('d', dBase);
      } else {
        const t0 = performance.now();
        const laneNoise = createNoise2D(alea(`${timeline.id}-lane`));

        const timer = d3.timer((now) => {
          const tGlobal = (now - t0) / 1000;

          // Floating end dot position (base noise)
          let endFx = branchEndX + floatNoise(tGlobal * floatSpeed, 0) * floatRadius;
          let endFy = branchY + floatNoise(0, tGlobal * floatSpeed) * floatRadius;

          // Cursor perturbance: if pointer is close, gently attract end anchor toward it,
          // but clamp the displacement so it stays within the floating radius region.
          if (pointer.active) {
            const dx = pointer.x - branchEndX;
            const dy = pointer.y - branchY;
            const dist = Math.sqrt(dx * dx + dy * dy);

            // Only react within CURSOR_INFLUENCE radius around the static end position
            const CURSOR_INFLUENCE = 150
            if (dist > 0 && dist < CURSOR_INFLUENCE) {
              const influence = (CURSOR_INFLUENCE - dist) / CURSOR_INFLUENCE; // 0..1
              const pull = 0.1 * influence;       // max 0.1 scaling
              // Target position pulled slightly toward cursor
              const targetFx = branchEndX + dx * pull;
              const targetFy = branchY + dy * pull;

              // Blend noise-based float with attracted target, then clamp to floating circle
              const mix = 0.4; // how much cursor affects vs. base float
              endFx = endFx * (1 - mix) + targetFx * mix;
              endFy = endFy * (1 - mix) + targetFy * mix;

              const relX = endFx - branchEndX;
              const relY = endFy - branchY;
              const relDist = Math.sqrt(relX * relX + relY * relY);
              if (relDist > floatRadius) {
                const s = floatRadius / relDist;
                endFx = branchEndX + relX * s;
                endFy = branchY + relY * s;
              }
            }
          }

          const basePts: [number, number][] = [];
          const energyPts: { x: number; y: number; v: number }[] = [];

          samples.forEach((t, idx) => {
            const isStart = idx === 0;
            const isEnd = idx === samples.length - 1;

            let x: number;
            let y: number;

            if (isStart) {
              x = deviationX;
              y = MAIN_TIMELINE_Y;
            } else if (isEnd) {
              x = endFx;
              y = endFy;
            } else {
              // Interpolate between fixed start & floating end
              x = deviationX + t * (endFx - deviationX);

              // Ease vertically between main line and floating end Y
              const ease = 1 - Math.exp(-3 * t);
              const targetLaneY = MAIN_TIMELINE_Y + ease * (endFy - MAIN_TIMELINE_Y);

              y = targetLaneY;
            }

            basePts.push([x, y]);

            // Initialize / update energy points with extra wobble (loose rope)
            if (!energyPts[idx]) {
              energyPts[idx] = { x, y, v: 0 };
            } else {
              energyPts[idx].x = x;
            }
          });

          // Update energy Y with noise-based elasticity
          energyPts.forEach((p, idx) => {
            const isStart = idx === 0;
            const isEnd = idx === energyPts.length - 1;
            const baseY = basePts[idx][1];

            if (isStart || isEnd) {
              p.y = baseY;
              p.v = 0;
              return;
            }

            const tNorm = idx / (energyPts.length - 1);
            const n =
              laneNoise(p.x * 0.02, tGlobal * 0.9 + tNorm * 2.3) * 2.0 +
              laneNoise(p.x * 0.006, tGlobal * 0.35 + tNorm * 5.2) * 1.0;

            const target = baseY + n;
            const accel = (target - p.y) * 0.12;
            p.v = (p.v + accel) * 0.82;
            p.y += p.v;
          });

          const dBase = branchBaseLine(basePts) || '';
          const dEnergy = branchBaseLine(energyPts.map(p => [p.x, p.y] as [number, number])) || '';

          branchBasePath.attr('d', dBase);
          branchEnergyPath.attr('d', dEnergy);

          // Update end dot in the same frame so it stays perfectly in sync with the path tip
          endDot.attr('cx', endFx).attr('cy', endFy);
        });

        track({ stop: () => timer.stop() });
      }

      // Apply cloud glow to energy path
      if (enableAnimations) {
        track(animateCloudStroke(branchEnergyPath as any, 0.50, 6));
      }

      // Capture branch geometry for routing-aware particles
      const branchPathNode = branchEnergyPath.node() as SVGPathElement | null;
      if (branchPathNode) {
        const branchTotalLength = branchPathNode.getTotalLength();
        if (Number.isFinite(branchTotalLength) && branchTotalLength > 0) {
          branchesMeta.push({
            id: timeline.id,
            color,
            branchPath: branchPathNode,
            deviationX,
            branchTotalLength
          });
        }
      }

      // Deviation point marker — manuscript medallion (diamond vertex)
      const devGroup = contentG.append('g')
        .attr('transform', `translate(${deviationX},${MAIN_TIMELINE_Y})`)
        .attr('filter', 'url(#soft-glow)')
        .style('cursor', 'pointer')
        .on('mouseenter', (event: PointerEvent) => {
          const [mouseX, mouseY] = d3.pointer(event, document.body as any);
          const { x, y } = calculateSafeTooltipPosition(mouseX, mouseY, 280);
          setTooltip({
            content: `${timeline.root_deviation_description} (${deviationYear})`,
            x, y, visible: true
          });
        })
        .on('mouseleave', () => {
          setTooltip(prev => ({ ...prev, visible: false }));
        })
        .on('click', () => onTimelineClick && onTimelineClick(timeline.id));
      devGroup.append('polygon')
        .attr('points', '0,-8 7,0 0,8 -7,0')
        .attr('fill', '#1C1508')
        .attr('stroke', color)
        .attr('stroke-width', 1.5)
        .attr('opacity', 0.95);
      devGroup.append('circle')
        .attr('r', 2.5)
        .attr('fill', color)
        .attr('opacity', 0.9);

      // Floating end point marker that follows the animated end anchor
      const endDot = contentG.append('circle')
        .attr('r', 3.5)
        .attr('fill', '#1C1508')
        .attr('stroke', color)
        .attr('stroke-width', 1.5)
        .attr('opacity', 0.85)
        .attr('filter', 'url(#soft-glow)');

      if (reduceMotion || !enableAnimations) {
        // Static: place dot at exact branch end (the timer won't run, so set it here)
        endDot
          .attr('cx', branchEndX)
          .attr('cy', branchY);
      }
      // Animated: endDot is updated each frame inside the d3.timer above

      // Generation segments (click targets):
      // Make them follow the same curved branch path using slices of continuousPts.
      if (full.generations && full.generations.length > 0) {
        const maxEnd = Math.max(...full.generations.map(g => g.end_year));
        const lanePoints = continuousPts; // already covers connector + horizontal

        const markers = full.generations.map(g => {
          const actualStart = deviationYear + g.start_year;
          const actualEnd = deviationYear + g.end_year;

          const startT = (actualStart - deviationYear) / (maxEnd || 1);
          const endT = (actualEnd - deviationYear) / (maxEnd || 1);

          const startIdx = Math.max(0, Math.min(lanePoints.length - 1, Math.floor(startT * (lanePoints.length - 1))));
          const endIdx = Math.max(startIdx, Math.min(lanePoints.length - 1, Math.floor(endT * (lanePoints.length - 1))));

          const slice = lanePoints.slice(startIdx, endIdx + 1) as [number, number][];
          const dPath = d3.line<[number, number]>()
            .curve(d3.curveCatmullRom.alpha(0.7))(slice) || '';

          return {
            order: g.generation_order,
            summary: g.executive_summary,
            actualStart,
            actualEnd,
            d: dPath
          };
        });

        contentG.selectAll(`.gen-seg-${index}`)
          .data(markers)
          .enter()
          .append('path')
          .attr('class', `gen-seg-${index}`)
          .attr('d', d => d.d)
          .attr('fill', 'none')
          .attr('stroke', color)
          .attr('stroke-width', 4)
          .attr('opacity', 0.22)
          .attr('stroke-linecap', 'round')
          .attr('filter', 'url(#soft-glow)')
          .attr('vector-effect', 'non-scaling-stroke')
          .style('cursor', 'pointer')
          .on('mouseenter', (event: PointerEvent, d: any) => {
             const [mouseX, mouseY] = d3.pointer(event, document.body as any);
             const { x, y } = calculateSafeTooltipPosition(mouseX, mouseY, 320);
             setTooltip({
               content: `Report ${d.order}: ${d.actualStart}-${d.actualEnd} — ${String(d.summary || '').slice(0, 110)}...`,
               x, y, visible: true
             });
           })
          .on('mouseleave', () => {
             setTooltip(prev => ({ ...prev, visible: false }));
           })
          .on('click', () => onTimelineClick && onTimelineClick(timeline.id));
      }

      // Year labels — Source Code Pro, manuscript palette
      contentG.append('text')
        .attr('x', deviationX)
        .attr('y', MAIN_TIMELINE_Y - 14)
        .attr('text-anchor', 'middle')
        .attr('fill', color)
        .attr('font-size', 10)
        .attr('font-family', "'Source Code Pro', monospace")
        .attr('font-weight', 400)
        .text(deviationYear.toString());
      contentG.append('text')
        .attr('x', branchEndX)
        .attr('y', branchY + 18)
        .attr('text-anchor', 'middle')
        .attr('fill', color)
        .attr('font-size', 10)
        .attr('font-family', "'Source Code Pro', monospace")
        .attr('font-weight', 400)
        .text(endYear.toString());
    }

    // Render single or multiple
    if (selectedTimelines && selectedTimelines.length > 0 && fullTimelines.size > 0) {
      selectedTimelines.forEach((tl, idx) => {
        const full = fullTimelines.get(tl.id);
        if (full) renderBranch(tl, idx, full);
      });
    } else if (selectedTimeline && fullTimeline) {
      renderBranch(selectedTimeline, 0, fullTimeline);
    }

    // Build deviation router mapping main path arc-length to branch deviations
    if (mainPath && branchesMeta.length && mainTotalLength > 0) {
      const S = 150;
      const samples: { L: number; x: number }[] = [];
      for (let k = 0; k <= S; k++) {
        const L = (k / S) * mainTotalLength;
        const pt = mainPath.getPointAtLength(L);
        samples.push({ L, x: pt.x });
      }

      const EPS = Math.max(
        mainTotalLength * DEVIATION_HIT_TOLERANCE_FACTOR,
        4 // px-ish fallback in arc-length terms for robustness
      );

      const routerMap = new Map<number, BranchMeta[]>();

      branchesMeta.forEach((bm) => {
        // Find nearest sample in x to the branch's deviationX
        let bestIdx = 0;
        let bestDist = Infinity;
        for (let i = 0; i < samples.length; i++) {
          const d = Math.abs(samples[i].x - bm.deviationX);
          if (d < bestDist) {
            bestDist = d;
            bestIdx = i;
          }
        }
        const targetL = samples[bestIdx].L;

        // Group by nearby mainLength within EPS
        let matchedKey: number | null = null;
        for (const key of routerMap.keys()) {
          if (Math.abs(key - targetL) <= EPS) {
            matchedKey = key;
            break;
          }
        }

        const key = matchedKey ?? targetL;
        const arr = routerMap.get(key) ?? [];
        arr.push(bm);
        routerMap.set(key, arr);
      });

      deviationRouter = Array.from(routerMap.entries())
        .map(([mainLength, branches]) => ({ mainLength, branches }))
        .sort((a, b) => a.mainLength - b.mainLength);
    }

    // Branching particles: semantic flow along main and branches
    function animateBranchingParticles(): { stop: () => void } {
      // Respect reduced-motion and require routing data
      if (reduceMotion || !mainPath || !deviationRouter.length || mainTotalLength <= 0) {
        return { stop: () => {} };
      }

      const layer = contentG.append('g')
        .attr('class', 'branching-particles-layer');

      let running = true;
      const particles: d3.Selection<SVGCircleElement, unknown, any, any>[] = [];

      const [mainMinDur, mainMaxDur] = BRANCHING_MAIN_DURATION_RANGE;
      const [branchMinDur, branchMaxDur] = BRANCHING_BRANCH_DURATION_RANGE;
      const tolerance = Math.max(
        mainTotalLength * DEVIATION_HIT_TOLERANCE_FACTOR,
        4
      );

      // Find a deviation hit near current main arc-length
      const findDeviationHit = (L: number): DeviationRouterEntry | null => {
        for (const entry of deviationRouter) {
          if (Math.abs(L - entry.mainLength) <= tolerance) {
            return entry;
          }
        }
        return null;
      };

      const pickBranch = (branches: BranchMeta[]): BranchMeta =>
        branches.length === 1
          ? branches[0]
          : branches[Math.floor(Math.random() * branches.length)];

      const startOnBranch = (
        circleSel: d3.Selection<SVGCircleElement, unknown, any, any>,
        branchMeta: BranchMeta
      ) => {
        if (!running) return;

        const branchPath = branchMeta.branchPath;
        const branchTotalLength = branchMeta.branchTotalLength;
        if (!branchPath || !Number.isFinite(branchTotalLength) || branchTotalLength <= 0) {
          // Fallback: restart on main if geometry invalid
          startOnMain(circleSel);
          return;
        }

        const branchDuration =
          branchMinDur + Math.random() * (branchMaxDur - branchMinDur);

        // Keep the same ethereal white color on branches
        circleSel
          .interrupt()
          .attr('fill', BRANCHING_PARTICLE_COLOR)
          .transition()
            .duration(300)
            .attr('opacity', BRANCHING_PARTICLE_OPACITY)
          .transition()
            .duration(branchDuration)
            .ease(d3.easeLinear)
            .attrTween('transform', () => {
              const L0 = 0;
              const L1 = branchTotalLength;
              return (t) => {
                if (!running) return '';
                const L = L0 + t * (L1 - L0);
                const pt = branchPath.getPointAtLength(Math.min(L, L1));
                return `translate(${pt.x},${pt.y})`;
              };
            })
          .transition()
            .duration(500)
            .attr('opacity', 0.0)
            .on('end', () => {
              if (!running || circleSel.empty()) return;
              startOnMain(circleSel);
            });
      };

      const startOnMain = (
        circleSel: d3.Selection<SVGCircleElement, unknown, any, any>
      ) => {
        if (!running || !mainPath || mainTotalLength <= 0) return;

        // 20% of particles start at the beginning to ensure good coverage at the start
        // 80% spawn randomly along the entire path
        const startL = Math.random() < 0.2
          ? 0
          : Math.random() * mainTotalLength;

        // Calculate duration proportional to remaining distance to maintain consistent speed
        // BRANCHING_MAIN_DURATION_RANGE is for traveling the full timeline
        const fullJourneyDuration = mainMinDur + Math.random() * (mainMaxDur - mainMinDur);
        const remainingFraction = (mainTotalLength - startL) / mainTotalLength;
        const mainDuration = fullJourneyDuration * remainingFraction;

        // Set initial position on main path before fade-in
        const startPt = mainPath.getPointAtLength(startL);

        circleSel
          .interrupt()
          .attr('fill', BRANCHING_PARTICLE_COLOR)
          .attr('opacity', 0.0)
          .attr('transform', `translate(${startPt.x},${startPt.y})`)
          .transition()
            .duration(500)
            .attr('opacity', BRANCHING_PARTICLE_OPACITY)
          .transition()
            .duration(mainDuration)
            .ease(d3.easeLinear)
            .attrTween('transform', () => {
              let splitDone = false;
              const checkedDeviations = new Set<number>(); // Track which deviations we've already checked

              return (t) => {
                if (!running || !mainPath) return `translate(0,0)`;

                const L = startL + t * (mainTotalLength - startL);

                // Only allow splitting after particle has traveled at least 20% of its journey
                // AND has traveled some minimum absolute distance on main
                const minProgressBeforeSplit = 0.2;
                const minDistanceBeforeSplit = mainTotalLength * 0.1; // 10% of total main length

                if (!splitDone && deviationRouter.length && t > minProgressBeforeSplit) {
                  const distanceTraveled = (L - startL);
                  if (distanceTraveled > minDistanceBeforeSplit) {
                    const hit = findDeviationHit(L);
                    // Only check split probability ONCE per deviation point
                    if (hit && !checkedDeviations.has(hit.mainLength)) {
                      checkedDeviations.add(hit.mainLength);
                      if (Math.random() < BRANCH_SPLIT_PROBABILITY) {
                        splitDone = true;
                        const chosen = pickBranch(hit.branches);
                        // Hand off to branch in next tick to avoid clobbering current transition stack
                        setTimeout(() => {
                          if (running) {
                            startOnBranch(circleSel, chosen);
                          }
                        }, 0);
                      }
                    }
                  }
                }

                const pt = mainPath.getPointAtLength(
                  Math.min(L, mainTotalLength)
                );
                return `translate(${pt.x},${pt.y})`;
              };
            })
          .transition()
            .duration(500)
            .attr('opacity', 0.0)
            .on('end', () => {
              if (!running) return;
              if (!circleSel.empty()) {
                startOnMain(circleSel);
              }
            });
      };

      for (let i = 0; i < BRANCHING_PARTICLE_COUNT; i++) {
        const circle = layer.append('circle')
          .attr('r', BRANCHING_PARTICLE_RADIUS)
          .attr('fill', BRANCHING_PARTICLE_COLOR)
          .attr('opacity', 0.0)
          .attr('filter', 'url(#soft-glow)');
        particles.push(circle);
        startOnMain(circle);
      }

      return {
        stop: () => {
          running = false;
          particles.forEach((c) => {
            c.interrupt();
            c.remove();
          });
          layer.remove();
        }
      };
    }

    // Enable branching particles once routing is ready
    if (enableAnimations && !reduceMotion && mainPath && mainTotalLength > 0 && deviationRouter.length > 0) {
      const branching = animateBranchingParticles();
      track(branching);
    }

    // Cleanup: stop timers, remove zoom
    return () => {
      cleaners.forEach(fn => fn());
      svg.on('.zoom', null as any);
    };
  }, [
    selectedTimeline,
    fullTimeline,
    selectedTimelines,
    fullTimelines,
    groundTruthReports,
    onTimelineClick,
    enableAnimations
  ]);

  return (
    <div className={`relative overflow-hidden ${className}`} style={{ minHeight: `${SVG_HEIGHT}px` }}>
      {/* Animation Toggle */}
      <div className="absolute top-3 right-3 z-20">
        <button
          onClick={() => setEnableAnimations(!enableAnimations)}
          className={`px-3 py-1 border font-mono text-[9px] tracking-widest uppercase transition-colors ${
            enableAnimations
              ? 'border-gold text-gold hover:bg-gold/10'
              : 'border-border text-dim hover:border-gold-dim hover:text-ink'
          }`}
          title={enableAnimations ? "Disable animations" : "Enable animations"}
        >
          {enableAnimations ? '◉ Motion' : '○ Motion'}
        </button>
      </div>

      {/* SVG */}
      <div className="relative z-10">
        <svg
          ref={svgRef}
          width={SVG_WIDTH}
          height={SVG_HEIGHT}
          className="w-full h-auto"
          viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
        />

        {/* Tooltip */}
        {tooltip.visible && (
          <div
            className="fixed z-30 bg-parchment text-ink px-3 py-2 pointer-events-none border border-border max-w-xs font-caption text-xs"
            style={{ left: tooltip.x, top: tooltip.y, transform: 'translate(-50%, 0)' }}
          >
            {tooltip.content}
          </div>
        )}
      </div>
    </div>
  );
};

export default BranchingTimeline;