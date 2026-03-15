/**
 * Ground Truth Report Page
 *
 * Displays historical ground truth reports (actual history) for different time periods.
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface GroundTruthReport {
  id: string;
  start_year: number;
  end_year: number;
  period_years: number;
  title: string;
  content: string;
  type: string;
}

export default function GroundTruthReportPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const navigate = useNavigate();

  const [report, setReport] = useState<GroundTruthReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReport = async () => {
      if (!reportId) return;
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch(`${API_BASE_URL}/api/ground-truth-reports/${reportId}`);
        if (response.ok) {
          setReport(await response.json());
        } else if (response.status === 404) {
          setError('Ground truth report not found for this period.');
        } else {
          setError(`Failed to load report: ${response.statusText}`);
        }
      } catch (err) {
        setError('Failed to load ground truth report. Please try again.');
        console.error('Error fetching ground truth report:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchReport();
  }, [reportId]);

  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center space-y-3">
          <div className="animate-spin h-8 w-8 border border-gold rounded-full border-t-transparent mx-auto" />
          <p className="font-caption text-sm text-dim">Loading historical record…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-screen flex items-center justify-center px-4">
        <div className="max-w-md w-full border border-rubric-dim bg-rubric/5 p-6">
          <div className="rubric-label mb-3">§ Error</div>
          <p className="font-body text-sm text-dim mb-5">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="border border-border text-dim hover:border-gold-dim hover:text-ink
                       font-mono text-xs tracking-widest uppercase px-5 py-2.5 transition-colors"
          >
            BACK TO HOME
          </button>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="h-screen flex items-center justify-center">
        <p className="font-caption text-sm text-dim">No report data found.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen py-10 px-4">
      <div className="max-w-3xl mx-auto">

        {/* Back link */}
        <div className="mb-8">
          <Link
            to="/"
            className="inline-flex items-center gap-2 font-mono text-xs text-dim tracking-widest
                       uppercase hover:text-gold transition-colors"
          >
            <svg width="14" height="10" viewBox="0 0 14 10" fill="none">
              <path d="M5 1L1 5l4 4M1 5h12" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
            </svg>
            Back to Home
          </Link>
        </div>

        {/* Header */}
        <div className="mb-8">
          <span className="rubric-label">§ Ground Truth History</span>
          <h1 className="font-display text-3xl text-gold mt-3 mb-2">{report.title}</h1>
          <p className="font-caption text-sm text-dim italic">
            Historical record spanning {report.period_years} year{report.period_years !== 1 ? 's' : ''}
            {' '}— {report.start_year}–{report.end_year}
          </p>
          <div className="double-rule mt-4" />
        </div>

        {/* Report content */}
        <div className="border border-border bg-surface px-8 py-8">
          <div
            className="prose max-w-none
                       prose-headings:font-display prose-headings:text-gold prose-headings:font-normal
                       prose-h1:text-2xl prose-h2:text-xl prose-h3:text-lg
                       prose-p:font-body prose-p:text-ink prose-p:leading-relaxed
                       prose-strong:text-ink prose-strong:font-semibold
                       prose-li:font-body prose-li:text-ink
                       prose-code:font-mono prose-code:text-quantum prose-code:text-xs
                       prose-a:text-quantum hover:prose-a:text-wave
                       prose-blockquote:border-l-2 prose-blockquote:border-gold-dim
                       prose-blockquote:pl-4 prose-blockquote:text-dim prose-blockquote:not-italic
                       prose-hr:border-border"
          >
            <ReactMarkdown>{report.content}</ReactMarkdown>
          </div>
        </div>

        {/* Footer metadata */}
        <div className="mt-4 flex justify-between items-baseline">
          <span className="font-mono text-xs text-faint">|ground-truth⟩</span>
          <span className="font-mono text-xs text-faint">{report.start_year}–{report.end_year}</span>
        </div>

      </div>
    </div>
  );
}
