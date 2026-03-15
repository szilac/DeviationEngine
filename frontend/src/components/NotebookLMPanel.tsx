import { useState, useEffect, useRef } from 'react';
import { ChevronDown } from 'lucide-react';
import type { Timeline, NotebookLMJob, NLMAudioFormat, NLMAudioLength } from '../types';
import {
  NLM_FORMAT_LABELS,
  NLM_LENGTH_LABELS,
  NLM_STATUS_LABELS,
} from '../types';
import * as audioService from '../services/audioService';
import GenerationContentSelector from './GenerationContentSelector';

interface ContentSelection {
  generationIds: Set<string>;
  includeReports: Set<string>;
  includeNarratives: Set<string>;
}

interface NotebookLMPanelProps {
  timeline: Timeline;
}

const NLM_LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'hu', name: 'Hungarian' },
  { code: 'de', name: 'German' },
  { code: 'es', name: 'Spanish' },
  { code: 'fr', name: 'French' },
  { code: 'it', name: 'Italian' },
];

const TERMINAL_STATUSES = new Set(['completed', 'failed']);
const POLL_INTERVAL_MS = 15000;

export default function NotebookLMPanel({ timeline }: NotebookLMPanelProps) {
  const [nlmAvailable, setNlmAvailable] = useState<boolean | null>(null);
  const [nlmError, setNlmError] = useState<string | null>(null);

  const [selection, setSelection] = useState<ContentSelection>({
    generationIds: new Set(),
    includeReports: new Set(),
    includeNarratives: new Set(),
  });
  const [nlmFormat, setNlmFormat] = useState<NLMAudioFormat>('deep_dive');
  const [nlmLength, setNlmLength] = useState<NLMAudioLength>('default');
  const [nlmFocus, setNlmFocus] = useState('');
  const [languageCode, setLanguageCode] = useState('en');

  const [activeJob, setActiveJob] = useState<NotebookLMJob | null>(null);
  const [pastJobs, setPastJobs] = useState<NotebookLMJob[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => { isMountedRef.current = false; };
  }, []);

  useEffect(() => {
    audioService.checkNLMAvailable().then((res) => {
      setNlmAvailable(res.available && res.authenticated);
      if (!res.available) setNlmError('nlm CLI not found. Run: pip install notebooklm-cli');
      else if (!res.authenticated) setNlmError('Not authenticated. Run: nlm login');
    });
  }, []);

  useEffect(() => {
    audioService.listNLMJobs(timeline.id).then((jobs) => {
      const completed = jobs.filter((j) => TERMINAL_STATUSES.has(j.status));
      const running = jobs.find((j) => !TERMINAL_STATUSES.has(j.status));
      setPastJobs(completed);
      if (running) {
        setActiveJob(running);
        schedulePoll(running.id);
      }
    });
    return () => { if (pollTimerRef.current) clearTimeout(pollTimerRef.current); };
  }, [timeline.id]);

  const schedulePoll = (jobId: string) => {
    pollTimerRef.current = setTimeout(async () => {
      try {
        const updated = await audioService.getNLMJob(jobId);
        if (!isMountedRef.current) return;
        setActiveJob(updated);
        if (TERMINAL_STATUSES.has(updated.status)) {
          if (updated.status === 'completed') setPastJobs((prev) => [updated, ...prev]);
          setActiveJob(null);
        } else {
          schedulePoll(jobId);
        }
      } catch {
        schedulePoll(jobId);
      }
    }, POLL_INTERVAL_MS);
  };

  const handleSubmit = async () => {
    setError(null);
    setIsSubmitting(true);
    try {
      const job = await audioService.startNLMJob({
        generation_ids: Array.from(selection.generationIds),
        timeline_id: timeline.id,
        nlm_format: nlmFormat,
        nlm_length: nlmLength,
        nlm_focus: nlmFocus.trim() || undefined,
        language_code: languageCode,
        include_reports: selection.includeReports.size > 0,
        include_narratives: selection.includeNarratives.size > 0,
      });
      setActiveJob(job);
      setSelection({ generationIds: new Set(), includeReports: new Set(), includeNarratives: new Set() });
      setNlmFocus('');
      schedulePoll(job.id);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(e.response?.data?.detail || e.message || 'Failed to start job');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteJob = async (jobId: string) => {
    await audioService.deleteNLMJob(jobId);
    setPastJobs((prev) => prev.filter((j) => j.id !== jobId));
  };

  const canSubmit =
    nlmAvailable === true &&
    !activeJob &&
    !isSubmitting &&
    selection.generationIds.size > 0 &&
    (selection.includeReports.size > 0 || selection.includeNarratives.size > 0);

  const API_BASE = (import.meta as { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL ?? 'http://localhost:8000';

  return (
    <div className="px-6 pb-6 pt-4 text-ink">

      {/* Notifications — above columns */}
      {nlmAvailable === false && (
        <div className="border border-rubric-dim px-4 py-2.5 mb-4">
          <p className="font-mono text-[10px] text-rubric">{nlmError}</p>
        </div>
      )}
      {error && (
        <div className="border border-rubric-dim px-4 py-2.5 mb-4">
          <p className="font-mono text-[10px] text-rubric">{error}</p>
        </div>
      )}
      {activeJob && (
        <div className="border border-gold-dim bg-surface/30 px-4 py-3 space-y-1.5 mb-4">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 border border-gold border-t-transparent animate-spin shrink-0" />
            <p className="font-mono text-[10px] tracking-widest uppercase text-gold">
              {NLM_STATUS_LABELS[activeJob.status]}
            </p>
          </div>
          <p className="font-mono text-[9px] text-faint">
            {NLM_FORMAT_LABELS[activeJob.nlm_format]} · {NLM_LENGTH_LABELS[activeJob.nlm_length]}
            {activeJob.nlm_focus && ` · "${activeJob.nlm_focus}"`}
          </p>
          <p className="font-mono text-[9px] text-faint">Typically 5–20 minutes.</p>
        </div>
      )}

      {/* Two-column layout */}
      <div className="grid grid-cols-[1fr_1.3fr] gap-6">

        {/* ── Left column: content + generate + past jobs ── */}
        <div className="space-y-4">

          {/* Step 1 */}
          <section className="space-y-2">
            <h3 className="font-mono text-[10px] tracking-widest uppercase text-dim flex items-center gap-2">
              <span className="font-mono text-[10px] border border-gold-dim text-gold w-5 h-5 flex items-center justify-center shrink-0">1</span>
              Select Content
            </h3>
            <div className="border border-border bg-surface/40 p-3">
              <GenerationContentSelector
                generations={timeline.generations}
                selection={selection}
                onSelectionChange={setSelection}
                disabled={!!activeJob || isSubmitting}
              />
            </div>
          </section>

          {/* Generate button */}
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className={[
              'w-full px-6 py-3 font-mono text-[10px] tracking-widest uppercase border transition-all flex items-center justify-center gap-3',
              canSubmit
                ? 'border-gold text-gold hover:bg-gold/10 cursor-pointer'
                : 'border-border text-faint cursor-not-allowed opacity-50',
            ].join(' ')}
          >
            {isSubmitting ? (
              <>
                <span className="w-3 h-3 border border-gold border-t-transparent animate-spin" />
                Starting…
              </>
            ) : (
              'Generate NotebookLM Audio'
            )}
          </button>

          {/* Past generations */}
          {pastJobs.length > 0 && (
            <section className="space-y-2">
              <h3 className="font-mono text-[10px] tracking-widest uppercase text-dim flex items-center gap-2">
                <span className="text-gold">§</span>
                Past Generations ({pastJobs.length})
              </h3>
              <div className="space-y-1.5">
                {pastJobs.map((job) => (
                  <div key={job.id} className="border border-border bg-surface/20 p-3 space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <span className="font-display text-sm text-ink">
                          {NLM_FORMAT_LABELS[job.nlm_format]}
                        </span>
                        <span className="font-mono text-[9px] text-faint ml-2">
                          {NLM_LENGTH_LABELS[job.nlm_length]}
                          {job.language_code !== 'en' && ` · ${NLM_LANGUAGES.find((l) => l.code === job.language_code)?.name ?? job.language_code}`}
                        </span>
                      </div>
                      <button
                        onClick={() => handleDeleteJob(job.id)}
                        className="font-mono text-[9px] text-faint hover:text-rubric transition-colors tracking-widest uppercase shrink-0"
                      >
                        Remove
                      </button>
                    </div>
                    {job.status === 'failed' && (
                      <p className="font-mono text-[10px] text-rubric">{job.error_message ?? 'Generation failed'}</p>
                    )}
                    {job.status === 'completed' && job.audio_url && (
                      <audio
                        controls
                        className="w-full mt-1"
                        src={`${API_BASE}${job.audio_url}`}
                      />
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* ── Right column: configure ── */}
        <div className="space-y-4">

          {/* Step 2 */}
          <section className="space-y-2">
            <h3 className="font-mono text-[10px] tracking-widest uppercase text-dim flex items-center gap-2">
              <span className="font-mono text-[10px] border border-gold-dim text-gold w-5 h-5 flex items-center justify-center shrink-0">2</span>
              Configure
            </h3>
            <div className="border border-border bg-surface/40 p-4 space-y-5">

              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="font-mono text-[10px] tracking-widest uppercase text-dim block mb-2">Format</label>
                  <div className="relative">
                    <select
                      value={nlmFormat}
                      onChange={(e) => setNlmFormat(e.target.value as NLMAudioFormat)}
                      disabled={!!activeJob || isSubmitting}
                      className="appearance-none bg-transparent border-b border-border text-ink font-mono text-[10px] tracking-widest uppercase focus:outline-none focus:border-gold-dim hover:border-gold-dim disabled:opacity-40 cursor-pointer w-full py-1 pr-5 transition-colors"
                    >
                      {(Object.entries(NLM_FORMAT_LABELS) as [NLMAudioFormat, string][]).map(([val, label]) => (
                        <option key={val} value={val} style={{ backgroundColor: '#271E0A', color: '#E8D8A0' }}>{label}</option>
                      ))}
                    </select>
                    <ChevronDown size={9} className="absolute right-0 top-1/2 -translate-y-1/2 text-faint pointer-events-none" />
                  </div>
                </div>
                <div>
                  <label className="font-mono text-[10px] tracking-widest uppercase text-dim block mb-2">Length</label>
                  <div className="relative">
                    <select
                      value={nlmLength}
                      onChange={(e) => setNlmLength(e.target.value as NLMAudioLength)}
                      disabled={!!activeJob || isSubmitting}
                      className="appearance-none bg-transparent border-b border-border text-ink font-mono text-[10px] tracking-widest uppercase focus:outline-none focus:border-gold-dim hover:border-gold-dim disabled:opacity-40 cursor-pointer w-full py-1 pr-5 transition-colors"
                    >
                      {(Object.entries(NLM_LENGTH_LABELS) as [NLMAudioLength, string][]).map(([val, label]) => (
                        <option key={val} value={val} style={{ backgroundColor: '#271E0A', color: '#E8D8A0' }}>{label}</option>
                      ))}
                    </select>
                    <ChevronDown size={9} className="absolute right-0 top-1/2 -translate-y-1/2 text-faint pointer-events-none" />
                  </div>
                </div>
              </div>

              <div>
                <label className="font-mono text-[10px] tracking-widest uppercase text-dim block mb-2">Language</label>
                <div className="relative">
                  <select
                    value={languageCode}
                    onChange={(e) => setLanguageCode(e.target.value)}
                    disabled={!!activeJob || isSubmitting}
                    className="appearance-none bg-transparent border-b border-border text-ink font-mono text-[10px] tracking-widest uppercase focus:outline-none focus:border-gold-dim hover:border-gold-dim disabled:opacity-40 cursor-pointer w-full py-1 pr-5 transition-colors"
                  >
                    {NLM_LANGUAGES.map((lang) => (
                      <option key={lang.code} value={lang.code} style={{ backgroundColor: '#271E0A', color: '#E8D8A0' }}>{lang.code.toUpperCase()} — {lang.name}</option>
                    ))}
                  </select>
                  <ChevronDown size={9} className="absolute right-0 top-1/2 -translate-y-1/2 text-faint pointer-events-none" />
                </div>
              </div>

              <div>
                <label className="font-mono text-[10px] tracking-widest uppercase text-dim block mb-2">
                  Focus Instructions <span className="text-faint font-normal normal-case">(Optional)</span>
                </label>
                <textarea
                  value={nlmFocus}
                  onChange={(e) => setNlmFocus(e.target.value)}
                  disabled={!!activeJob || isSubmitting}
                  placeholder='e.g. "Discuss as if you lived through these events"'
                  maxLength={500}
                  rows={4}
                  className="w-full bg-transparent border border-border text-ink font-body text-sm px-3 py-2 placeholder:text-faint placeholder:font-mono placeholder:text-[10px] focus:outline-none focus:border-gold-dim disabled:opacity-40 resize-none transition-colors"
                />
                <div className="text-right font-mono text-[9px] text-faint mt-1">{nlmFocus.length}/500</div>
              </div>
            </div>
          </section>
        </div>

      </div>
    </div>
  );
}
