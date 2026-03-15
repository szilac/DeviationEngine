import React, { useState, useEffect } from 'react';
import { getCharacter, listCharacterProfiles, getCharacterProfile, deleteCharacterProfile } from '../services/api';
import type { CharacterDetail, CharacterChunk, CharacterProfile } from '../types';
import { CharacterUtils } from '../types';
import { X, Trash2 } from 'lucide-react';

interface CharacterProfileViewerProps {
  characterId: string;
  onClose: () => void;
}

const CharacterProfileViewer: React.FC<CharacterProfileViewerProps> = ({
  characterId,
  onClose,
}) => {
  const [character, setCharacter] = useState<CharacterDetail | null>(null);
  const [profiles, setProfiles] = useState<CharacterProfile[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<CharacterProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      setError(null);
      const [charResponse, profilesResponse] = await Promise.all([
        getCharacter(characterId, false),
        listCharacterProfiles(characterId),
      ]);
      if (charResponse.data) {
        setCharacter(charResponse.data);
      } else {
        setError(charResponse.error?.message || 'Failed to load character');
      }
      if (profilesResponse.data) {
        const readyProfiles = profilesResponse.data.filter((p) => p.profile_status === 'ready');
        setProfiles(readyProfiles);
        if (readyProfiles.length > 0) {
          await loadProfileDetail(readyProfiles[0].id);
        }
      }
      setIsLoading(false);
    };
    load();
  }, [characterId]);

  const loadProfileDetail = async (profileId: string) => {
    setIsLoadingProfile(true);
    const response = await getCharacterProfile(characterId, profileId);
    if (response.data) setSelectedProfile(response.data);
    setIsLoadingProfile(false);
  };

  const handleSelectProfile = async (profile: CharacterProfile) => {
    if (selectedProfile?.id === profile.id) return;
    await loadProfileDetail(profile.id);
  };

  const handleDeleteProfile = async () => {
    if (!selectedProfile) return;
    if (!confirm(`Delete the ${selectedProfile.cutoff_year} profile? This cannot be undone.`)) return;
    const response = await deleteCharacterProfile(characterId, selectedProfile.id);
    if (response.data) {
      const remaining = profiles.filter((p) => p.id !== selectedProfile.id);
      setProfiles(remaining);
      if (remaining.length > 0) {
        await loadProfileDetail(remaining[0].id);
      } else {
        setSelectedProfile(null);
      }
    }
  };

  if (isLoading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
        <div className="bg-parchment border border-border px-10 py-8 text-center">
          <div className="animate-spin h-6 w-6 border-2 border-gold border-t-transparent mx-auto mb-4" />
          <p className="font-body text-sm text-dim">Loading profile...</p>
        </div>
      </div>
    );
  }

  if (error || !character) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
        <div className="bg-parchment border border-border p-8 max-w-md">
          <p className="rubric-label mb-3">§ Error</p>
          <p className="font-body text-sm text-dim mb-5">{error || 'Character not found'}</p>
          <button
            onClick={onClose}
            className="px-4 py-2 border border-border font-mono text-[10px] tracking-widest uppercase text-dim hover:border-gold-dim hover:text-ink transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  const chunks = selectedProfile?.chunks || [];
  const chunksByType = chunks.reduce<Record<string, CharacterChunk[]>>(
    (acc, chunk) => {
      if (!acc[chunk.chunk_type]) acc[chunk.chunk_type] = [];
      acc[chunk.chunk_type].push(chunk);
      return acc;
    },
    {}
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70" onClick={onClose}>
      <div
        className="bg-parchment border border-border max-w-2xl w-full mx-4 max-h-[85vh] flex flex-col shadow-[0_8px_40px_rgba(0,0,0,0.6)]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-border">
          <div className="space-y-1">
            <p className="rubric-label">§ Historical Figure</p>
            <h2 className="font-display text-2xl text-gold leading-tight">
              {character.full_name || character.name}
            </h2>
            {character.title && (
              <p className="font-body text-sm text-dim">{character.title}</p>
            )}
            <div className="flex items-center gap-3 pt-1">
              {(character.birth_year || character.death_year) && (
                <span className="font-mono text-[10px] text-faint tracking-wider">
                  {CharacterUtils.formatYears(character.birth_year, character.death_year)}
                </span>
              )}
              <span className="font-mono text-[10px] tracking-widest uppercase text-gold-dim border border-gold-dim px-1.5 py-0.5">
                {CharacterUtils.getProfileStatusLabel(character.profile_status)}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-faint hover:text-ink hover:border-border border border-transparent transition-colors"
            aria-label="Close"
          >
            <X size={15} />
          </button>
        </div>

        {/* Profile selector */}
        {profiles.length > 0 && (
          <div className="px-6 pt-4 pb-3 border-b border-border">
            <div className="flex items-center justify-between mb-2.5">
              <span className="font-mono text-[9px] tracking-widest uppercase text-faint">
                {profiles.length > 1 ? 'Available Profiles' : 'Profile'}
              </span>
              {selectedProfile && (
                <button
                  onClick={handleDeleteProfile}
                  className="flex items-center gap-1 font-mono text-[9px] tracking-wider text-faint hover:text-rubric transition-colors"
                  title="Delete this profile"
                >
                  <Trash2 size={11} />
                  Delete
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {profiles.map((profile) => (
                <button
                  key={profile.id}
                  onClick={() => handleSelectProfile(profile)}
                  className={`px-3 py-1.5 border font-mono text-[10px] tracking-wider transition-colors ${
                    selectedProfile?.id === profile.id
                      ? 'border-gold text-gold bg-surface/60'
                      : 'border-border text-dim bg-surface/20 hover:border-gold-dim hover:text-ink'
                  }`}
                >
                  {profile.cutoff_year}
                  <span className="opacity-50 ml-1.5">({profile.chunk_count} chunks)</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {isLoadingProfile ? (
            <div className="text-center py-10">
              <div className="animate-spin h-5 w-5 border-2 border-gold border-t-transparent mx-auto mb-3" />
              <p className="font-body text-sm text-faint">Loading profile...</p>
            </div>
          ) : selectedProfile ? (
            <>
              {selectedProfile.short_bio && (
                <div>
                  <p className="font-mono text-[9px] tracking-widest uppercase text-dim mb-2">Biography</p>
                  <div className="double-rule mb-3" />
                  <p className="font-body text-[17px] text-ink leading-[1.75]">{selectedProfile.short_bio}</p>
                </div>
              )}

              {selectedProfile.role_summary && (
                <div>
                  <p className="font-mono text-[9px] tracking-widest uppercase text-dim mb-2">Role in Timeline</p>
                  <div className="double-rule mb-3" />
                  <p className="font-body text-[17px] text-ink leading-[1.75]">{selectedProfile.role_summary}</p>
                </div>
              )}

              {selectedProfile.importance_score != null && (
                <div className="flex items-center gap-3">
                  <span className="font-mono text-[9px] tracking-widest uppercase text-faint">Importance</span>
                  <div className="w-28 h-1 bg-surface overflow-hidden">
                    <div
                      className="h-full bg-gold-dim"
                      style={{ width: `${selectedProfile.importance_score * 100}%` }}
                    />
                  </div>
                  <span className="font-mono text-[10px] text-gold-dim">
                    {(selectedProfile.importance_score * 100).toFixed(0)}%
                  </span>
                </div>
              )}

              {Object.entries(chunksByType).map(([type, typeChunks]) => (
                <div key={type}>
                  <p className="font-mono text-[9px] tracking-widest uppercase text-dim mb-2">
                    {CharacterUtils.getChunkTypeLabel(type as any)}
                  </p>
                  <div className="double-rule mb-3" />
                  {typeChunks.map((chunk) => (
                    <div key={chunk.id} className="font-body text-base text-ink leading-relaxed mb-2">
                      {chunk.content}
                      {(chunk.year_start || chunk.year_end) && (
                        <span className="font-mono text-[10px] text-faint ml-2">
                          ({chunk.year_start || '?'}–{chunk.year_end || '?'})
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              ))}
            </>
          ) : (
            <p className="font-body text-sm text-faint italic py-4">
              No profiles generated yet. Generate a profile to see detailed information.
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default CharacterProfileViewer;
