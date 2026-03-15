/**
 * Skeleton Editor Component
 *
 * Allows users to review and edit skeleton events before generating the full report.
 */

import { useState, useEffect } from 'react';
import type { Skeleton, SkeletonEvent, SkeletonEventUpdate } from '../types';
import { SkeletonUtils } from '../types';

interface SkeletonEditorProps {
  skeleton: Skeleton;
  onSave: (eventsUpdate: SkeletonEventUpdate[], deletedIds: string[]) => void;
  onApprove: () => void;
  onGenerateReport: () => void;
  isSaving: boolean;
  isGenerating: boolean;
}

const statusColors: Record<string, string> = {
  pending: 'border-warning/50 text-warning',
  editing: 'border-quantum/50 text-quantum',
  approved: 'border-success/50 text-success',
};

const SkeletonEditor = ({
  skeleton,
  onSave,
  onApprove: _onApprove,
  onGenerateReport: _onGenerateReport,
  isSaving,
  isGenerating: _isGenerating,
}: SkeletonEditorProps) => {
  const [events, setEvents] = useState<SkeletonEvent[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deletedIds, setDeletedIds] = useState<string[]>([]);
  const [hasChanges, setHasChanges] = useState(false);

  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newEventDraft, setNewEventDraft] = useState<{
    event_date: string;
    location: string;
    description: string;
  }>({ event_date: skeleton.deviation_date || '', location: '', description: '' });

  useEffect(() => {
    setEvents(SkeletonUtils.sortEventsByOrder(skeleton.events));
    setDeletedIds([]);
    setHasChanges(false);
  }, [skeleton]);

  const getDateConstraints = () => {
    let startYear: number;
    let endYear: number;
    const leeway = 2;

    if (skeleton.skeleton_type === 'timeline_draft' && skeleton.deviation_date) {
      const deviationYear = new Date(skeleton.deviation_date).getFullYear();
      if (skeleton.events.length > 0) {
        const years = skeleton.events.map(e => deviationYear + e.event_year);
        startYear = Math.min(...years) - leeway;
        endYear = Math.max(...years) + leeway;
      } else {
        startYear = deviationYear - 10 - leeway;
        endYear = deviationYear + 10 + leeway;
      }
    } else if (skeleton.skeleton_type === 'extension_draft' && skeleton.extension_start_year && skeleton.extension_end_year) {
      startYear = skeleton.extension_start_year - leeway;
      endYear = skeleton.extension_end_year + leeway;
    } else if (skeleton.skeleton_type === 'branch_draft' && skeleton.branch_point_year) {
      startYear = skeleton.branch_point_year - leeway;
      endYear = skeleton.branch_point_year + 20 + leeway;
    } else {
      return { minDate: undefined, maxDate: undefined };
    }

    return { minDate: `${startYear}-01-01`, maxDate: `${endYear}-12-31` };
  };

  const { minDate, maxDate } = getDateConstraints();

  const handleEventChange = (eventId: string, field: keyof SkeletonEvent, value: string | number) => {
    setEvents(prev => prev.map(e => e.id === eventId ? { ...e, [field]: value } : e));
    setHasChanges(true);
  };

  const handleAddEvent = () => {
    if (!canEdit) return;
    setNewEventDraft({ event_date: skeleton.deviation_date || '', location: '', description: '' });
    setIsAddModalOpen(true);
  };

  const handleConfirmAddEvent = () => {
    const desc = newEventDraft.description.trim();
    const loc = newEventDraft.location.trim();
    const date = newEventDraft.event_date.trim();
    if (!date || !desc) return;

    const newEvent: SkeletonEvent = {
      id: `temp-${Date.now()}`,
      skeleton_id: skeleton.id,
      event_date: date,
      event_year: 0,
      location: loc,
      description: desc,
      event_order: 0,
      is_user_added: true,
      is_user_modified: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    setEvents(prev => {
      const updated = [...prev, newEvent];
      const sorted = [...updated].sort((a, b) => {
        const aDate = a.event_date || '';
        const bDate = b.event_date || '';
        if (aDate && bDate && aDate !== bDate) return aDate.localeCompare(bDate);
        return a.event_order - b.event_order;
      });
      return sorted.map((e, i) => ({ ...e, event_order: i }));
    });

    setHasChanges(true);
    setIsAddModalOpen(false);
  };

  const handleDeleteEvent = (eventId: string) => {
    setEvents(prev => prev.filter(e => e.id !== eventId));
    if (!eventId.startsWith('temp-')) setDeletedIds([...deletedIds, eventId]);
    setHasChanges(true);
    if (editingId === eventId) setEditingId(null);
  };

  const handleSave = () => {
    const eventsUpdate: SkeletonEventUpdate[] = events.map(event => ({
      id: event.id.startsWith('temp-') ? null : event.id,
      event_date: event.event_date,
      location: event.location,
      description: event.description,
      event_order: event.event_order,
    }));
    onSave(eventsUpdate, deletedIds);
  };

  const canEdit = SkeletonUtils.canEdit(skeleton);

  const inputClass = "w-full bg-vellum border border-border text-ink px-3 py-2 font-body text-sm placeholder:text-faint focus:outline-none focus:border-gold transition-colors";

  return (
    <div className="bg-parchment border border-border corner-brackets">
      {/* Header */}
      <div className="px-5 py-3 border-b border-border flex justify-end">
        <span className={`font-mono text-[9px] tracking-widest uppercase border px-2 py-1 ${statusColors[skeleton.status] || 'border-border text-dim'}`}>
          {skeleton.status}
        </span>
      </div>

      {/* Events */}
      <div className="p-5">
        <div className="flex items-center justify-between mb-4">
          <span className="font-mono text-[9px] tracking-widest uppercase text-dim">
            Key Events <span className="text-faint ml-1">({events.length})</span>
          </span>
          {canEdit && (
            <button
              type="button"
              onClick={handleAddEvent}
              disabled={isSaving}
              className="font-mono text-[9px] tracking-widest uppercase border border-gold text-gold px-3 py-1.5 hover:bg-gold/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              + Add Event
            </button>
          )}
        </div>

        <div className="space-y-3">
          {events.map((event, index) => {
            const isEditing = editingId === event.id;
            const absoluteYear = SkeletonUtils.getAbsoluteYear(skeleton, event);

            return (
              <div
                key={event.id}
                className={`border p-4 ${
                  event.is_user_added
                    ? 'border-quantum/40 bg-quantum/5'
                    : event.is_user_modified
                    ? 'border-warning/40 bg-warning/5'
                    : 'border-border bg-surface/20'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[9px] text-faint">#{index + 1}</span>
                    {event.is_user_added && (
                      <span className="font-mono text-[9px] tracking-wider border border-quantum/50 text-quantum px-1.5 py-0.5">
                        Added
                      </span>
                    )}
                    {event.is_user_modified && (
                      <span className="font-mono text-[9px] tracking-wider border border-warning/50 text-warning px-1.5 py-0.5">
                        Modified
                      </span>
                    )}
                  </div>

                  {canEdit && (
                    <div className="flex gap-3">
                      <button
                        onClick={() => setEditingId(isEditing ? null : event.id)}
                        className="font-mono text-[9px] tracking-wider text-gold-dim hover:text-gold transition-colors"
                      >
                        {isEditing ? 'Done' : 'Edit'}
                      </button>
                      <button
                        onClick={() => handleDeleteEvent(event.id)}
                        className="font-mono text-[9px] tracking-wider text-rubric-dim hover:text-rubric transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  )}
                </div>

                {isEditing ? (
                  <div className="space-y-3 mt-2">
                    <div>
                      <label className="font-mono text-[9px] tracking-widest uppercase text-faint block mb-1">Date</label>
                      <input
                        type="date"
                        value={event.event_date}
                        min={minDate}
                        max={maxDate}
                        onChange={(e) => handleEventChange(event.id, 'event_date', e.target.value)}
                        className={inputClass}
                      />
                    </div>
                    <div>
                      <label className="font-mono text-[9px] tracking-widest uppercase text-faint block mb-1">Location</label>
                      <input
                        type="text"
                        value={event.location}
                        onChange={(e) => handleEventChange(event.id, 'location', e.target.value)}
                        placeholder="City, Country/Region"
                        className={inputClass}
                      />
                    </div>
                    <div>
                      <label className="font-mono text-[9px] tracking-widest uppercase text-faint block mb-1">Description</label>
                      <textarea
                        value={event.description}
                        onChange={(e) => handleEventChange(event.id, 'description', e.target.value)}
                        placeholder="Brief description of the event"
                        rows={3}
                        className={`${inputClass} resize-none`}
                      />
                    </div>
                  </div>
                ) : (
                  <div>
                    <div className="font-mono text-[10px] text-gold-dim mb-1">
                      {event.event_date}
                      {absoluteYear ? ` (${absoluteYear})` : ''}
                      {event.location && <span className="text-faint"> — {event.location}</span>}
                    </div>
                    <p className="font-body text-sm text-ink">{event.description}</p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Action bar — Save Changes only; Approve / Generate are in the top bar */}
      {hasChanges && canEdit && (
        <div className="flex items-center justify-between px-5 py-4 border-t border-border">
          <span className="font-mono text-[9px] tracking-wider text-warning">⚠ Unsaved changes</span>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="font-mono text-[9px] tracking-widest uppercase border border-success/60 text-success px-4 py-2 hover:bg-success/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isSaving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      )}

      {/* Help text */}
      <div className="px-5 pb-5">
        <div className="border-t border-border pt-4">
          <p className="font-mono text-[9px] tracking-widest uppercase text-faint mb-2">How it works</p>
          <ol className="space-y-1 font-body text-xs text-dim list-none">
            {[
              'Review the AI-generated skeleton events',
              'Edit, add, or delete events as needed',
              'Save your changes',
              'Approve the skeleton when ready',
              'Generate the full analytical report',
            ].map((step, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="font-mono text-[9px] text-faint shrink-0">{i + 1}.</span>
                {step}
              </li>
            ))}
          </ol>
        </div>
      </div>

      {/* Add Event Modal */}
      {canEdit && isAddModalOpen && (
        <div
          className="fixed inset-0 z-50 overflow-y-auto bg-vellum/80 backdrop-blur-sm"
          aria-modal="true"
          role="dialog"
          aria-label="Add new skeleton event"
        >
          <div className="flex min-h-full items-center justify-center p-4">
            <div className="w-full max-w-lg bg-parchment border border-border p-6 corner-brackets space-y-4 shadow-[var(--shadow-panel)]">
              <div className="flex items-start justify-between">
                <h3 className="font-display text-lg text-ink">Add New Event</h3>
                <button onClick={() => setIsAddModalOpen(false)} className="text-faint hover:text-dim font-mono">×</button>
              </div>
              <p className="font-body text-xs text-dim">
                Provide the key details. The event will be placed in correct timeline order by date.
              </p>

              <div className="space-y-3">
                <div>
                  <label className="font-mono text-[9px] tracking-widest uppercase text-faint block mb-1">Event Date</label>
                  <input
                    type="date"
                    value={newEventDraft.event_date}
                    min={minDate}
                    max={maxDate}
                    onChange={(e) => setNewEventDraft(p => ({ ...p, event_date: e.target.value }))}
                    className="w-full bg-vellum border border-border text-ink px-3 py-2 font-mono text-sm focus:outline-none focus:border-gold transition-colors"
                  />
                </div>
                <div>
                  <label className="font-mono text-[9px] tracking-widest uppercase text-faint block mb-1">Location (optional)</label>
                  <input
                    type="text"
                    value={newEventDraft.location}
                    onChange={(e) => setNewEventDraft(p => ({ ...p, location: e.target.value }))}
                    placeholder="City, Country/Region"
                    className="w-full bg-vellum border border-border text-ink px-3 py-2 font-body text-sm placeholder:text-faint focus:outline-none focus:border-gold transition-colors"
                  />
                </div>
                <div>
                  <label className="font-mono text-[9px] tracking-widest uppercase text-faint block mb-1">Description</label>
                  <textarea
                    value={newEventDraft.description}
                    onChange={(e) => setNewEventDraft(p => ({ ...p, description: e.target.value }))}
                    placeholder="Brief description of the event (2–3 sentences)"
                    rows={3}
                    className="w-full bg-vellum border border-border text-ink px-3 py-2.5 font-body text-sm placeholder:text-faint focus:outline-none focus:border-gold transition-colors resize-none"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  className="font-mono text-[9px] tracking-widest uppercase border border-border text-dim px-4 py-2 hover:border-gold-dim hover:text-ink transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConfirmAddEvent}
                  className="font-mono text-[9px] tracking-widest uppercase border border-gold text-gold px-4 py-2 hover:bg-gold/10 hover:shadow-[var(--shadow-gold)] transition-all"
                >
                  Save Event
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SkeletonEditor;
