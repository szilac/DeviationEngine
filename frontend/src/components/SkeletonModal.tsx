import React, { useState, useEffect, useRef } from 'react';
import type { Timeline } from '../types';
import { getTimelineSkeletonSnapshot } from '../services/api';
import SkeletonEventViewer from './SkeletonEventViewer';
import { X } from 'lucide-react';

interface SkeletonModalProps {
  timeline: Timeline;
  generationId?: string;
  onClose: () => void;
}

interface SkeletonSnapshotData {
  timeline_id: string;
  skeleton_id: string;
  events: any[];
  snapshot_created_at: string;
}

export const SkeletonModal: React.FC<SkeletonModalProps> = ({
  timeline,
  generationId,
  onClose,
}) => {
  const [skeleton, setSkeleton] = useState<SkeletonSnapshotData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchSkeleton = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await getTimelineSkeletonSnapshot(timeline.id, generationId);

        if (response.error) {
          setError(response.error.message);
        } else if (response.data) {
          setSkeleton(response.data);
        } else {
          setError('No skeleton data available');
        }
      } catch (err) {
        console.error('Failed to fetch skeleton', err);
        setError('An unexpected error occurred while loading skeleton');
      } finally {
        setLoading(false);
      }
    };

    fetchSkeleton();
  }, [timeline.id, generationId]);

  // Handle Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  // Focus trap
  useEffect(() => {
    const modal = modalRef.current;
    if (!modal) return;

    const focusableElements = modal.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    const handleTabKey = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement?.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement?.focus();
      }
    };

    modal.addEventListener('keydown', handleTabKey);
    firstElement?.focus();

    return () => {
      modal.removeEventListener('keydown', handleTabKey);
    };
  }, [loading, skeleton]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="skeleton-modal-title"
        className="bg-parchment border border-border shadow-[var(--shadow-panel)] max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border shrink-0">
          <div>
            <p className="rubric-label">§ Source Skeleton</p>
            <h2 id="skeleton-modal-title" className="font-display text-xl text-gold leading-tight">
              Source Skeleton Events
            </h2>
            <p className="font-mono text-[10px] text-dim mt-0.5">
              The approved timeline draft that generated this report
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-dim hover:text-ink transition-colors cursor-pointer"
            aria-label="Close modal"
          >
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3">
              <span className="w-5 h-5 border border-gold border-t-transparent rounded-full animate-spin" />
              <p className="font-mono text-[10px] tracking-widest uppercase text-dim">Loading skeleton events…</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-16 gap-2">
              <p className="font-mono text-[10px] tracking-widest uppercase text-rubric">Error Loading Skeleton</p>
              <p className="font-body text-sm text-dim">{error}</p>
            </div>
          ) : skeleton ? (
            <SkeletonEventViewer
              snapshot={skeleton}
              deviationDate={timeline.root_deviation_date}
              deviationDescription={timeline.root_deviation_description}
            />
          ) : (
            <div className="flex items-center justify-center py-16">
              <p className="font-mono text-[10px] tracking-widest uppercase text-faint">No skeleton data available</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
