import React, { useState, useEffect, useCallback } from 'react';
import type { Character, Timeline, ChatSession, CreateCustomCharacterRequest, CharacterProfileSummary } from '../types';
import { CharacterProfileStatus } from '../types';
import {
  listCharacters,
  detectCharacters,
  createCustomCharacter,
  generateCharacterProfile,
  deleteCharacter,
  deleteUnprofiledCharacters,
  createChatSession,
  getTimelineChatSessions,
} from '../services/api';
import CharacterCard from './CharacterCard';
import CharacterProfileViewer from './CharacterProfileViewer';
import ChatInterface from './ChatInterface';
import { Search, Plus, X, Trash2 } from 'lucide-react';

interface CharacterListPanelProps {
  timeline: Timeline;
}

type FilterStatus = 'all' | 'ready' | 'pending' | 'generating' | 'error';

const CharacterListPanel: React.FC<CharacterListPanelProps> = ({ timeline }) => {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDetecting, setIsDetecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');

  // Profile viewer state
  const [viewingProfileId, setViewingProfileId] = useState<string | null>(null);

  // Chat state
  const [chatCharacter, setChatCharacter] = useState<Character | null>(null);
  const [chatSession, setChatSession] = useState<ChatSession | null>(null);
  const [isStartingChat, setIsStartingChat] = useState(false);
  const [yearContextInput, setYearContextInput] = useState<number | ''>('');
  const [showYearPicker, setShowYearPicker] = useState<Character | null>(null);

  // Profile generation year picker state
  const [showProfileYearPicker, setShowProfileYearPicker] = useState<Character | null>(null);
  const [profileYearInput, setProfileYearInput] = useState<number | ''>('');
  const [isGeneratingProfile, setIsGeneratingProfile] = useState(false);

  // Profile-aware chat: selected profile for starting chat
  const [selectedProfileId, setSelectedProfileId] = useState<string | undefined>(undefined);

  // All timeline sessions (for showing history per character)
  const [allSessions, setAllSessions] = useState<ChatSession[]>([]);

  // Custom character form state
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createForm, setCreateForm] = useState<CreateCustomCharacterRequest>({
    name: '',
    user_provided_bio: '',
  });
  const [isCreating, setIsCreating] = useState(false);

  const loadCharacters = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    const [charResponse, sessionsResponse] = await Promise.all([
      listCharacters(timeline.id),
      getTimelineChatSessions(timeline.id),
    ]);
    if (charResponse.data) {
      setCharacters(charResponse.data);
    } else {
      setError(charResponse.error?.message || 'Failed to load characters');
    }
    if (sessionsResponse.data) {
      setAllSessions(sessionsResponse.data);
    }
    setIsLoading(false);
  }, [timeline.id]);

  useEffect(() => {
    loadCharacters();
  }, [loadCharacters]);

  const handleDetect = async () => {
    setIsDetecting(true);
    setError(null);
    const response = await detectCharacters(timeline.id);
    if (response.data) {
      setCharacters(response.data.characters);
    } else {
      setError(response.error?.message || 'Failed to detect characters');
    }
    setIsDetecting(false);
  };

  const handleGenerateProfile = (character: Character) => {
    const deviationYear = new Date(timeline.root_deviation_date).getFullYear();
    const defaultYear = character.last_known_year || deviationYear;
    setProfileYearInput(defaultYear);
    setShowProfileYearPicker(character);
  };

  const handleConfirmGenerateProfile = async () => {
    if (!showProfileYearPicker || !profileYearInput) return;
    const character = showProfileYearPicker;
    setIsGeneratingProfile(true);
    setError(null);

    // Optimistic update
    setCharacters((prev) =>
      prev.map((c) =>
        c.id === character.id
          ? { ...c, profile_status: CharacterProfileStatus.GENERATING as typeof c.profile_status }
          : c
      )
    );
    setShowProfileYearPicker(null);

    const response = await generateCharacterProfile(character.id, Number(profileYearInput));
    if (response.data) {
      setCharacters((prev) =>
        prev.map((c) => (c.id === character.id ? response.data!.character : c))
      );
    } else {
      // Revert on failure
      setCharacters((prev) =>
        prev.map((c) =>
          c.id === character.id
            ? { ...c, profile_status: CharacterProfileStatus.ERROR as typeof c.profile_status }
            : c
        )
      );
      setError(response.error?.message || 'Failed to generate profile');
    }
    setIsGeneratingProfile(false);
  };

  const handleDelete = async (character: Character) => {
    if (!confirm(`Delete ${character.name}? This will also remove all chat sessions.`)) return;
    const response = await deleteCharacter(character.id);
    if (response.data) {
      setCharacters((prev) => prev.filter((c) => c.id !== character.id));
    } else {
      setError(response.error?.message || 'Failed to delete character');
    }
  };

  const handleDeleteUnprofiled = async () => {
    const unprofiledCount = characters.filter(
      (c) => c.character_source === 'auto_detected' && c.profile_status !== 'ready'
    ).length;
    if (unprofiledCount === 0) return;
    if (!confirm(`Delete ${unprofiledCount} unprofiled scanned figure${unprofiledCount !== 1 ? 's' : ''}?`)) return;
    const response = await deleteUnprofiledCharacters(timeline.id);
    if (response.data) {
      setCharacters((prev) =>
        prev.filter((c) => !(c.character_source === 'auto_detected' && c.profile_status !== 'ready'))
      );
    } else {
      setError(response.error?.message || 'Failed to delete unprofiled characters');
    }
  };

  const handleStartChat = (character: Character) => {
    // If character has ready profiles, default to the first ready profile's year
    const readyProfiles = (character.profiles || []).filter((p) => p.profile_status === 'ready');
    const deviationYear = new Date(timeline.root_deviation_date).getFullYear();

    if (readyProfiles.length > 0) {
      setYearContextInput(readyProfiles[0].cutoff_year);
      setSelectedProfileId(readyProfiles[0].id);
    } else {
      const defaultYear = character.last_known_year || deviationYear;
      setYearContextInput(defaultYear);
      setSelectedProfileId(undefined);
    }
    setShowYearPicker(character);
  };

  const handleSelectProfile = (profile: CharacterProfileSummary) => {
    setYearContextInput(profile.cutoff_year);
    setSelectedProfileId(profile.id);
  };

  const handleResumeSession = (session: ChatSession) => {
    if (!showYearPicker) return;
    setChatCharacter(showYearPicker);
    setChatSession(session);
    setShowYearPicker(null);
    setSelectedProfileId(undefined);
  };

  const handleConfirmChat = async () => {
    if (!showYearPicker || !yearContextInput) return;
    setIsStartingChat(true);
    setError(null);

    const response = await createChatSession(showYearPicker.id, {
      character_year_context: Number(yearContextInput),
      profile_id: selectedProfileId,
    });

    if (response.data) {
      setAllSessions(prev => [response.data!, ...prev]);
      setChatCharacter(showYearPicker);
      setChatSession(response.data);
      setShowYearPicker(null);
      setSelectedProfileId(undefined);
    } else {
      setError(response.error?.message || 'Failed to start chat session');
    }
    setIsStartingChat(false);
  };

  const handleCreateCustom = async () => {
    if (!createForm.name.trim() || !createForm.user_provided_bio.trim()) return;
    setIsCreating(true);
    setError(null);

    const response = await createCustomCharacter(timeline.id, createForm);
    if (response.data) {
      setCharacters((prev) => [...prev, response.data!]);
      setShowCreateForm(false);
      setCreateForm({ name: '', user_provided_bio: '' });
    } else {
      setError(response.error?.message || 'Failed to create character');
    }
    setIsCreating(false);
  };

  const filteredCharacters = characters.filter((c) => {
    if (filterStatus === 'all') return true;
    return c.profile_status === filterStatus;
  });

  const statusCounts = {
    all: characters.length,
    ready: characters.filter((c) => c.profile_status === CharacterProfileStatus.READY).length,
    pending: characters.filter((c) => c.profile_status === CharacterProfileStatus.PENDING).length,
    generating: characters.filter((c) => c.profile_status === CharacterProfileStatus.GENERATING).length,
    error: characters.filter((c) => c.profile_status === CharacterProfileStatus.ERROR).length,
  };

  return (
    <div className="px-5 py-4 space-y-4">
      {/* Header + Actions */}
      <div className="flex items-center justify-between border-b border-border pb-4">
        <p className="rubric-label">§ Historical Figures</p>
        <div className="flex items-center gap-2">
          {characters.some((c) => c.character_source === 'auto_detected' && c.profile_status !== 'ready') && (
            <button
              onClick={handleDeleteUnprofiled}
              className="flex items-center gap-1.5 font-mono text-[10px] tracking-widest uppercase text-rubric-dim hover:text-rubric border border-border hover:border-rubric-dim px-3 py-1.5 transition-colors cursor-pointer"
              title="Delete all scanned figures without a generated profile"
            >
              <Trash2 size={10} />
              Delete Unprofiled
            </button>
          )}
          <button
            onClick={handleDetect}
            disabled={isDetecting}
            className="flex items-center gap-1.5 font-mono text-[10px] tracking-widest uppercase text-dim hover:text-gold border border-border hover:border-gold-dim px-3 py-1.5 transition-colors disabled:opacity-40 cursor-pointer"
          >
            {isDetecting
              ? <span className="animate-spin h-3 w-3 border border-dim border-t-transparent inline-block" />
              : <Search size={10} />}
            {isDetecting ? 'Scanning…' : 'Scan Timeline'}
          </button>
          <button
            onClick={() => setShowCreateForm(true)}
            className="flex items-center gap-1.5 font-mono text-[10px] tracking-widest uppercase text-dim hover:text-gold border border-border hover:border-gold-dim px-3 py-1.5 transition-colors cursor-pointer"
          >
            <Plus size={10} />
            Custom
          </button>
        </div>
      </div>

      {/* Filter tabs */}
      {characters.length > 0 && (
        <div className="flex gap-1.5 flex-wrap">
          {(['all', 'ready', 'pending', 'generating', 'error'] as FilterStatus[]).map((status) => (
            <button
              key={status}
              onClick={() => setFilterStatus(status)}
              className={[
                'px-2.5 py-1 font-mono text-[10px] tracking-widest uppercase border transition-colors cursor-pointer',
                filterStatus === status
                  ? 'text-gold border-gold-dim'
                  : 'text-faint border-border hover:text-dim',
              ].join(' ')}
            >
              {status === 'all' ? 'All' : status.charAt(0).toUpperCase() + status.slice(1)} ({statusCounts[status]})
            </button>
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="border border-rubric-dim px-4 py-2.5">
          <p className="font-mono text-[10px] text-rubric">{error}</p>
        </div>
      )}

      {/* Loading / empty states */}
      {isLoading ? (
        <div className="text-center py-12">
          <p className="font-mono text-xs text-faint tracking-widest uppercase animate-pulse">
            Loading figures…
          </p>
        </div>
      ) : characters.length === 0 ? (
        <div className="text-center py-12">
          <p className="font-body text-dim mb-1">No characters found.</p>
          <p className="font-mono text-[10px] text-faint">
            Click "Scan Timeline" to detect historical figures.
          </p>
        </div>
      ) : filteredCharacters.length === 0 ? (
        <div className="text-center py-8">
          <p className="font-body text-sm text-dim">No characters match this filter.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {filteredCharacters.map((character) => (
            <CharacterCard
              key={character.id}
              character={character}
              sessionCount={allSessions.filter(s => s.character_id === character.id).length}
              onChat={handleStartChat}
              onViewProfile={(c) => setViewingProfileId(c.id)}
              onGenerateProfile={handleGenerateProfile}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}

      {/* Create Custom Character Form (Modal) */}
      {showCreateForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setShowCreateForm(false)}>
          <div className="bg-parchment border border-border p-6 max-w-md w-full mx-4 corner-brackets" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-5">
              <p className="rubric-label">§ Create Custom Figure</p>
              <button onClick={() => setShowCreateForm(false)} className="text-dim hover:text-ink cursor-pointer"><X size={14} /></button>
            </div>

            <div className="space-y-4">
              {[
                { label: 'Name *', field: 'name', placeholder: 'e.g., Albert Einstein' },
                { label: 'Full Name', field: 'full_name', placeholder: 'e.g., Prof. Albert Einstein' },
                { label: 'Title', field: 'title', placeholder: 'e.g., Theoretical Physicist' },
              ].map(({ label, field, placeholder }) => (
                <div key={field}>
                  <label className="font-mono text-[10px] tracking-widest uppercase text-dim block mb-1">{label}</label>
                  <input
                    type="text"
                    value={(createForm as any)[field] || ''}
                    onChange={(e) => setCreateForm((f) => ({ ...f, [field]: e.target.value || undefined }))}
                    className="w-full bg-transparent border-b border-border text-ink font-body text-sm py-1.5 placeholder:text-faint focus:outline-none focus:border-gold-dim transition-colors"
                    placeholder={placeholder}
                  />
                </div>
              ))}
              <div className="grid grid-cols-2 gap-4">
                {[
                  { label: 'Birth Year', field: 'birth_year', placeholder: '1879' },
                  { label: 'Death Year', field: 'death_year', placeholder: '1955' },
                ].map(({ label, field, placeholder }) => (
                  <div key={field}>
                    <label className="font-mono text-[10px] tracking-widest uppercase text-dim block mb-1">{label}</label>
                    <input
                      type="number"
                      value={(createForm as any)[field] || ''}
                      onChange={(e) => setCreateForm((f) => ({ ...f, [field]: e.target.value ? Number(e.target.value) : undefined }))}
                      className="w-full bg-transparent border-b border-border text-ink font-mono text-sm py-1.5 placeholder:text-faint focus:outline-none focus:border-gold-dim transition-colors"
                      placeholder={placeholder}
                    />
                  </div>
                ))}
              </div>
              <div>
                <label className="font-mono text-[10px] tracking-widest uppercase text-dim block mb-1">Bio / Background *</label>
                <textarea
                  value={createForm.user_provided_bio}
                  onChange={(e) => setCreateForm((f) => ({ ...f, user_provided_bio: e.target.value }))}
                  className="w-full bg-transparent border border-border text-ink font-body text-sm p-2 placeholder:text-faint focus:outline-none focus:border-gold-dim transition-colors resize-none"
                  rows={3}
                  placeholder="Describe this figure's role in the alternate timeline…"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-border">
              <button onClick={() => setShowCreateForm(false)} className="font-mono text-[10px] tracking-widest uppercase text-dim hover:text-ink transition-colors cursor-pointer">Cancel</button>
              <button
                onClick={handleCreateCustom}
                disabled={isCreating || !createForm.name.trim() || !createForm.user_provided_bio.trim()}
                className="font-mono text-[10px] tracking-widest uppercase border border-gold-dim text-gold hover:border-gold px-4 py-1.5 transition-colors disabled:opacity-40 cursor-pointer"
              >
                {isCreating ? 'Creating…' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Year Context Picker (Modal) */}
      {showYearPicker && (() => {
        const readyProfiles = (showYearPicker.profiles || []).filter((p) => p.profile_status === 'ready');
        const characterSessions = allSessions
          .filter(s => s.character_id === showYearPicker.id)
          .sort((a, b) => new Date(b.last_message_at || b.updated_at).getTime() - new Date(a.last_message_at || a.updated_at).getTime());

        return (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => { setShowYearPicker(null); setSelectedProfileId(undefined); }}>
            <div className="bg-parchment border border-border p-6 max-w-sm w-full mx-4 corner-brackets" onClick={(e) => e.stopPropagation()}>
              <p className="rubric-label mb-2">§ Correspondence</p>
              <h3 className="font-display text-xl text-gold mb-4">{showYearPicker.name}</h3>

              {/* Previous sessions */}
              {characterSessions.length > 0 && (
                <div className="mb-5">
                  <label className="font-mono text-[10px] tracking-widest uppercase text-dim block mb-2">
                    Previous Conversations
                  </label>
                  <div className="space-y-1.5">
                    {characterSessions.map((session) => (
                      <button
                        key={session.id}
                        onClick={() => handleResumeSession(session)}
                        className="w-full flex items-center justify-between px-3 py-2 border border-border hover:border-gold-dim text-left transition-colors cursor-pointer"
                      >
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="font-mono text-[11px] text-gold shrink-0">
                            {session.character_year_context}
                          </span>
                          {session.session_name && (
                            <span className="font-body text-xs text-dim truncate">{session.session_name}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 shrink-0 ml-2">
                          <span className="font-mono text-[9px] text-faint">
                            {session.message_count} msg{session.message_count !== 1 ? 's' : ''}
                          </span>
                          {!session.is_active && (
                            <span className="font-mono text-[9px] tracking-widest uppercase border border-border text-faint px-1.5 py-0.5">
                              Closed
                            </span>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                  <div className="mt-4 mb-4 border-t border-border" />
                  <label className="font-mono text-[10px] tracking-widest uppercase text-dim block mb-3">
                    New Conversation
                  </label>
                </div>
              )}

              {/* Profile chips */}
              {readyProfiles.length > 0 && (
                <div className="mb-4">
                  <label className="font-mono text-[10px] tracking-widest uppercase text-dim block mb-2">Available Profiles</label>
                  <div className="flex flex-wrap gap-2">
                    {readyProfiles.map((profile) => (
                      <button
                        key={profile.id}
                        onClick={() => handleSelectProfile(profile)}
                        className={[
                          'px-3 py-1 font-mono text-[10px] tracking-widest border transition-colors cursor-pointer',
                          selectedProfileId === profile.id
                            ? 'border-gold text-gold'
                            : 'border-border text-dim hover:border-gold-dim',
                        ].join(' ')}
                      >
                        {profile.cutoff_year}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <label className="font-mono text-[10px] tracking-widest uppercase text-dim block mb-1">
                  {readyProfiles.length > 0 ? 'Or custom year' : 'Year Context'}
                </label>
                <input
                  type="number"
                  value={yearContextInput}
                  onChange={(e) => { setYearContextInput(e.target.value ? Number(e.target.value) : ''); setSelectedProfileId(undefined); }}
                  className="w-full bg-transparent border-b border-border text-ink font-mono text-sm py-1.5 focus:outline-none focus:border-gold-dim transition-colors placeholder:text-faint"
                  placeholder="e.g., 1925"
                />
              </div>

              <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-border">
                <button onClick={() => { setShowYearPicker(null); setSelectedProfileId(undefined); }} className="font-mono text-[10px] tracking-widest uppercase text-dim hover:text-ink transition-colors cursor-pointer">Cancel</button>
                <button
                  onClick={handleConfirmChat}
                  disabled={isStartingChat || !yearContextInput}
                  className="font-mono text-[10px] tracking-widest uppercase border border-gold-dim text-gold hover:border-gold px-4 py-1.5 transition-colors disabled:opacity-40 cursor-pointer"
                >
                  {isStartingChat ? 'Starting…' : 'Start New'}
                </button>
              </div>
            </div>
          </div>
        );
      })()}

      {/* Profile Generation Year Picker (Modal) */}
      {showProfileYearPicker && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setShowProfileYearPicker(null)}>
          <div className="bg-parchment border border-border p-6 max-w-sm w-full mx-4 corner-brackets" onClick={(e) => e.stopPropagation()}>
            <p className="rubric-label mb-2">§ Generate Profile</p>
            <h3 className="font-display text-xl text-gold mb-1">{showProfileYearPicker.name}</h3>
            <p className="font-body text-sm text-dim mb-4">
              Choose the cutoff year for this profile snapshot.
            </p>

            {showProfileYearPicker.profiles && showProfileYearPicker.profiles.length > 0 && (
              <div className="mb-4">
                <label className="font-mono text-[10px] tracking-widest uppercase text-dim block mb-1.5">Existing profiles</label>
                <div className="flex flex-wrap gap-1.5">
                  {showProfileYearPicker.profiles.map((p) => (
                    <span key={p.id} className="font-mono text-[10px] px-2 py-0.5 border border-success/40 text-success">
                      {p.cutoff_year} ✓
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div>
              <label className="font-mono text-[10px] tracking-widest uppercase text-dim block mb-1">Cutoff Year</label>
              <input
                type="number"
                value={profileYearInput}
                onChange={(e) => setProfileYearInput(e.target.value ? Number(e.target.value) : '')}
                className="w-full bg-transparent border-b border-border text-ink font-mono text-sm py-1.5 focus:outline-none focus:border-gold-dim transition-colors placeholder:text-faint"
                placeholder="e.g., 1924"
              />
              {profileYearInput && showProfileYearPicker.profiles?.some((p) => p.cutoff_year === Number(profileYearInput)) && (
                <p className="font-mono text-[10px] text-warning mt-1">
                  A profile for this year exists and will be regenerated.
                </p>
              )}
            </div>

            <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-border">
              <button onClick={() => setShowProfileYearPicker(null)} className="font-mono text-[10px] tracking-widest uppercase text-dim hover:text-ink transition-colors cursor-pointer">Cancel</button>
              <button
                onClick={handleConfirmGenerateProfile}
                disabled={isGeneratingProfile || !profileYearInput}
                className="font-mono text-[10px] tracking-widest uppercase border border-gold-dim text-gold hover:border-gold px-4 py-1.5 transition-colors disabled:opacity-40 cursor-pointer"
              >
                {isGeneratingProfile ? 'Generating…' : 'Generate'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Profile Viewer */}
      {viewingProfileId && (
        <CharacterProfileViewer
          characterId={viewingProfileId}
          onClose={() => setViewingProfileId(null)}
        />
      )}

      {/* Chat Interface */}
      {chatCharacter && chatSession && (
        <ChatInterface
          character={chatCharacter}
          session={chatSession}
          onClose={() => {
            setChatCharacter(null);
            setChatSession(null);
          }}
          onSessionUpdate={(updated) => setChatSession(updated)}
        />
      )}
    </div>
  );
};

export default CharacterListPanel;
