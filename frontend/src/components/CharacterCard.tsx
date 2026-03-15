import type { Character, CharacterProfileSummary } from '../types';
import { CharacterUtils, CharacterProfileStatus, CharacterSource } from '../types';
import { MessageSquare, User, Sparkles, Trash2 } from 'lucide-react';

interface CharacterCardProps {
  character: Character;
  sessionCount?: number;
  onChat: (character: Character) => void;
  onViewProfile: (character: Character) => void;
  onGenerateProfile: (character: Character) => void;
  onDelete: (character: Character) => void;
}

const STATUS_CLASSES: Record<string, string> = {
  ready:      'text-success border-success/40',
  pending:    'text-dim    border-border',
  generating: 'text-warning border-warning/40',
  error:      'text-rubric  border-rubric-dim',
};

const STATUS_LABELS: Record<string, string> = {
  ready: 'Ready', pending: 'Pending', generating: 'Generating…', error: 'Error',
};

const CharacterCard = ({
  character,
  sessionCount = 0,
  onChat,
  onViewProfile,
  onGenerateProfile,
  onDelete,
}: CharacterCardProps) => {
  const isGenerating = character.profile_status === CharacterProfileStatus.GENERATING;
  const isReady      = character.profile_status === CharacterProfileStatus.READY;
  const statusKey    = character.profile_status ?? 'pending';

  return (
    <div className="bg-surface border border-border hover:border-gold-dim transition-colors duration-150 p-4 corner-brackets">

      {/* Top row */}
      <div className="flex items-start justify-between mb-2">
        <div className="min-w-0 flex-1">
          <h3 className="font-display text-base text-ink truncate leading-tight">
            {character.name}
          </h3>
          {character.title && (
            <p className="font-caption text-xs text-dim italic truncate mt-0.5">
              {character.title}
            </p>
          )}
        </div>
        {/* Status badge */}
        <span className={`font-mono text-[9px] tracking-widest uppercase border px-2 py-0.5 shrink-0 ml-2 ${STATUS_CLASSES[statusKey] ?? STATUS_CLASSES.pending}`}>
          {isGenerating && (
            <span className="inline-block w-2 h-2 border border-current border-t-transparent animate-spin mr-1 align-middle" />
          )}
          {STATUS_LABELS[statusKey] ?? statusKey}
        </span>
      </div>

      {/* Years + source */}
      <div className="flex items-center gap-2 mb-2">
        {(character.birth_year || character.death_year) && (
          <span className="font-mono text-[10px] text-dim">
            {CharacterUtils.formatYears(character.birth_year, character.death_year)}
          </span>
        )}
        <span className={`font-mono text-[9px] tracking-widest uppercase px-1.5 py-0.5 border ${
          character.character_source === CharacterSource.AUTO_DETECTED
            ? 'border-quantum/30 text-quantum'
            : 'border-gold-dim text-gold-dim'
        }`}>
          {character.character_source === CharacterSource.AUTO_DETECTED ? 'Detected' : 'Custom'}
        </span>
        {/* Importance bar */}
        {character.importance_score != null && (
          <div className="ml-auto w-10 h-px bg-border overflow-hidden">
            <div
              className="h-full bg-gold-dim"
              style={{ width: `${character.importance_score * 100}%` }}
            />
          </div>
        )}
      </div>

      {/* Short bio */}
      {character.short_bio && (
        <p className="font-body text-xs text-dim line-clamp-2 mb-3 leading-relaxed">
          {character.short_bio}
        </p>
      )}

      {/* Profile year chips */}
      {character.profiles && character.profiles.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {character.profiles.map((profile: CharacterProfileSummary) => (
            <span
              key={profile.id}
              className={`font-mono text-[9px] px-1.5 py-0.5 border ${
                profile.profile_status === 'ready'
                  ? 'border-success/40 text-success'
                  : profile.profile_status === 'generating'
                  ? 'border-warning/40 text-warning'
                  : 'border-border text-faint'
              }`}
            >
              {profile.cutoff_year}{profile.profile_status === 'ready' ? ' ✓' : profile.profile_status === 'generating' ? ' …' : ''}
            </span>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-1.5 pt-2 border-t border-border">
        <ActionBtn
          onClick={() => onChat(character)}
          disabled={!isReady}
          title={isReady ? 'Start chat' : 'Generate profile first'}
          icon={<MessageSquare size={10} />}
          label={sessionCount > 0 ? `Chat (${sessionCount})` : 'Chat'}
          active={isReady}
        />
        <ActionBtn
          onClick={() => onViewProfile(character)}
          icon={<User size={10} />}
          label="Profile"
        />
        <ActionBtn
          onClick={() => onGenerateProfile(character)}
          disabled={isGenerating}
          icon={<Sparkles size={10} />}
          label={isReady ? '+ Profile' : 'Generate'}
          accent
        />
        <button
          onClick={() => onDelete(character)}
          className="ml-auto text-faint hover:text-rubric transition-colors cursor-pointer"
          title="Delete"
        >
          <Trash2 size={11} />
        </button>
      </div>
    </div>
  );
};

function ActionBtn({
  onClick,
  disabled,
  title,
  icon,
  label,
  active,
  accent,
}: {
  onClick: () => void;
  disabled?: boolean;
  title?: string;
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  accent?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={[
        'flex items-center gap-1 px-2 py-1 font-mono text-[9px] tracking-widest uppercase border transition-colors duration-150 cursor-pointer',
        disabled
          ? 'border-border text-faint cursor-not-allowed opacity-40'
          : accent
          ? 'border-gold-dim text-gold-dim hover:border-gold hover:text-gold'
          : active
          ? 'border-gold-dim text-gold hover:border-gold'
          : 'border-border text-dim hover:border-gold-dim hover:text-ink',
      ].join(' ')}
    >
      {icon}
      {label}
    </button>
  );
}

export default CharacterCard;
