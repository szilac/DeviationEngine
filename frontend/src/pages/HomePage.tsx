/**
 * HomePage — Quantum Manuscript folio landing.
 *
 * Clean entry point. Fetches 4 most recent timelines for the
 * "Recent Chronicles" list. No visualization, no filters.
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getTimelines } from '../services/api';
import InkTitle from '../components/layout/InkTitle';
import type { TimelineListItem } from '../types';

// ── Decorative Feynman branch SVG ─────────────────────────────────────────────

const FeynmanDiagram = () => (
  <svg
    aria-hidden="true"
    focusable="false"
    viewBox="0 0 80 180"
    className="w-16 h-36 text-gold-dim opacity-60"
    fill="none"
    stroke="currentColor"
    strokeWidth="0.8"
  >
    {/* Incoming line */}
    <line x1="40" y1="0" x2="40" y2="50" />
    {/* Vertex */}
    <circle cx="40" cy="50" r="2" fill="currentColor" />
    {/* Branch A */}
    <path d="M40,50 Q20,80 15,120" strokeDasharray="2,2" />
    <circle cx="15" cy="120" r="1.5" fill="currentColor" />
    <line x1="15" y1="120" x2="15" y2="180" />
    {/* Branch B */}
    <path d="M40,50 Q60,80 65,120" />
    <circle cx="65" cy="120" r="1.5" fill="currentColor" />
    <line x1="65" y1="120" x2="65" y2="180" />
    {/* Wavy quantum exchange */}
    <path
      d="M40,50 C45,60 50,65 55,70 C60,75 65,80 60,85 C55,90 50,90 45,95"
      strokeWidth="0.5"
      className="text-quantum"
      stroke="#4FC3F7"
    />
    {/* Labels */}
    <text x="5" y="140" fontSize="5" fill="#8A7A50" fontFamily="monospace">α</text>
    <text x="68" y="140" fontSize="5" fill="#8A7A50" fontFamily="monospace">β</text>
    <text x="43" y="47" fontSize="5" fill="#D4A017" fontFamily="monospace">δ</text>
  </svg>
);

// ── Helpers ───────────────────────────────────────────────────────────────────

const formatScenario = (type: string) =>
  type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

// ── GettingStarted ────────────────────────────────────────────────────────────

const GettingStarted = () => {
  const [open, setOpen] = useState(true);

  return (
    <div className="border border-border bg-surface/30">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-surface/50 transition-colors"
      >
        <span className="rubric-label">§ Getting Started</span>
        <span className="font-mono text-[10px] text-faint">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="px-4 pb-4 space-y-3 border-t border-border">
          {[
            {
              n: '1',
              title: 'Configure your LLM',
              desc: 'Go to Settings and choose a provider (Gemini Flash recommended — generous free tier).',
              link: '/settings',
              linkLabel: 'Open Settings →',
            },
            {
              n: '2',
              title: 'Create your first timeline',
              desc: 'Click "Define the Deviation" below, pick a preset example, and hit Generate.',
              link: '/console',
              linkLabel: 'Open Console →',
            },
            {
              n: '3',
              title: 'Explore the Atlas',
              desc: 'Once a timeline is generated, compare it against actual history in the Temporal Atlas.',
              link: '/atlas',
              linkLabel: 'Open Atlas →',
            },
          ].map(({ n, title, desc, link, linkLabel }) => (
            <div key={n} className="flex gap-3 pt-3">
              <span className="font-mono text-[10px] text-gold-dim shrink-0 mt-0.5 w-4">{n}.</span>
              <div className="space-y-0.5">
                <p className="font-body text-sm text-ink">{title}</p>
                <p className="font-body text-xs text-dim leading-relaxed">{desc}</p>
                <Link to={link} className="font-mono text-[9px] text-gold hover:text-gold-2 transition-colors tracking-wider">
                  {linkLabel}
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ── HomePage ──────────────────────────────────────────────────────────────────

const HomePage = () => {
  const [recentTimelines, setRecentTimelines] = useState<TimelineListItem[]>([]);

  useEffect(() => {
    const fetch4 = async () => {
      try {
        const response = await getTimelines();
        if (response.data) {
          const sorted = response.data.sort((a: TimelineListItem, b: TimelineListItem) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          );
          setRecentTimelines(sorted.slice(0, 4));
        }
      } catch {
        // Non-critical — page works fine without the list
      }
    };
    fetch4();
  }, []);

  return (
    <div className="min-h-[calc(100vh-56px)] bg-vellum">
      <div className="max-w-3xl mx-auto px-6 py-8">

        {/* ── Hero ── */}
        <div className="text-center mb-6">
          <InkTitle
            className="font-display text-gold leading-none mb-3"
            style={{ fontSize: 'clamp(44px, 7vw, 80px)' }}
            delay={0.1}
          >
            Deviation Engine
          </InkTitle>

          <p className="font-mono text-xs text-quantum tracking-widest mb-2">
            |ψ⟩ quantum-class alternate history simulation
          </p>

          <p className="font-caption text-base text-dim italic max-w-xl mx-auto leading-relaxed">
            Illuminate the paths not taken. Every deviation ripples through history.
          </p>
        </div>

        {/* ── Double-rule divider ── */}
        <div className="double-rule mb-8" />

        {/* ── Two-column body ── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">

          {/* Left — Illuminated intro */}
          <div className="flex gap-4">
            <div className="shrink-0 mt-1">
              <FeynmanDiagram />
            </div>

            <div className="space-y-4">
              {/* Drop cap paragraph */}
              <p className="font-body text-dim leading-relaxed">
                <span
                  className="float-left font-display text-gold leading-none mr-2"
                  style={{ fontSize: '4.5rem', lineHeight: '0.8' }}
                >
                  D
                </span>
                eviation Engine generates alternate history timelines from a single
                changed moment. Specify a historical event from 1880 to 2004, describe
                how it differs, and an ensemble of AI agents constructs the political,
                economic, social, and cultural consequences.
              </p>

              <p className="font-body text-dim leading-relaxed text-base">
                Each chronicle is a structured analytical report, a narrative prose
                account, and an image-illustrated record — a complete counterfactual
                manuscript.
              </p>
            </div>
          </div>

          {/* Right — Recent Chronicles */}
          <div>
            <p className="rubric-label mb-3">§ Recent Chronicles</p>

            {recentTimelines.length === 0 ? (
              <GettingStarted />
            ) : (
              <div className="space-y-0">
                {recentTimelines.map((tl, i) => {
                  const year = new Intl.DateTimeFormat('en', { year: 'numeric' }).format(
                    new Date(tl.root_deviation_date)
                  );
                  return (
                    <Link
                      key={tl.id}
                      to={`/reports/${tl.id}`}
                      className="block py-2.5 border-b border-border/60 group hover:bg-surface/20 -mx-2 px-2 transition-colors"
                    >
                      <div className="flex items-baseline gap-2">
                        <span className="font-mono text-[10px] text-rubric shrink-0 w-10">{year}</span>
                        <span className="font-body text-sm text-ink group-hover:text-gold-2 transition-colors truncate flex-1">
                          {tl.timeline_name || tl.root_deviation_description}
                        </span>
                        <span className="font-mono text-[8px] text-faint shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                          →
                        </span>
                      </div>
                      <div className="ml-12 flex items-center gap-2 mt-0.5">
                        <span className="font-mono text-[8px] text-faint">
                          {tl.generation_count} {tl.generation_count !== 1 ? 'chronicles' : 'chronicle'}
                        </span>
                        <span className="text-border font-mono text-[8px]">·</span>
                        <span className="font-mono text-[8px] text-gold-dim">
                          {formatScenario(tl.scenario_type)}
                        </span>
                        {i === 0 && (
                          <>
                            <span className="text-border font-mono text-[8px]">·</span>
                            <span className="font-mono text-[8px] border border-gold-dim/50 text-gold-dim px-1.5 py-0.5">
                              latest
                            </span>
                          </>
                        )}
                      </div>
                    </Link>
                  );
                })}

                {recentTimelines.length > 0 && (
                  <Link
                    to="/library"
                    className="block pt-3 font-mono text-[9px] tracking-wider text-faint hover:text-gold-dim transition-colors"
                  >
                    View all chronicles →
                  </Link>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── CTAs ── */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            to="/console"
            className="font-mono text-[11px] tracking-widest uppercase border border-gold text-gold px-8 py-3 hover:bg-gold/10 hover:shadow-[var(--shadow-gold)] transition-all w-full sm:w-auto text-center"
          >
            Define the Deviation
          </Link>
          <Link
            to="/atlas"
            className="font-mono text-[11px] tracking-widest uppercase border border-border text-dim px-8 py-3 hover:border-gold-dim hover:text-ink transition-all w-full sm:w-auto text-center"
          >
            Explore the Atlas
          </Link>
        </div>

        {/* ── Footer note ── */}
        <p className="text-center font-mono text-[8px] tracking-widest text-faint mt-14">
          Historical accuracy supported 1880 — 1970 · Plausible fiction only
        </p>
      </div>
    </div>
  );
};

export default HomePage;
