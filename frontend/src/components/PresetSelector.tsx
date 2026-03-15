import type { ScriptPreset } from '../types';

interface PresetSelectorProps {
  presets: ScriptPreset[];
  selectedPresetId: string | null;
  onSelect: (presetId: string) => void;
  onCreateCustom?: () => void;
  disabled?: boolean;
}

export default function PresetSelector({
  presets,
  selectedPresetId,
  onSelect,
  onCreateCustom,
  disabled = false,
}: PresetSelectorProps) {
  const systemPresets = presets.filter(p => p.is_system);
  const customPresets = presets.filter(p => !p.is_system);

  const PresetButton = ({ preset }: { preset: ScriptPreset }) => {
    const isSelected = selectedPresetId === preset.id;
    return (
      <button
        key={preset.id}
        onClick={() => onSelect(preset.id)}
        disabled={disabled}
        className={[
          'w-full text-left px-3 py-3 border transition-colors',
          isSelected
            ? 'border-gold bg-surface'
            : 'border-border bg-vellum hover:border-gold-dim/50',
          disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer',
        ].join(' ')}
      >
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className={`font-mono text-[10px] tracking-widest uppercase leading-tight ${isSelected ? 'text-gold' : 'text-ink'}`}>
            {preset.name}
          </div>
          <div className={[
            'w-2.5 h-2.5 border shrink-0 mt-0.5 flex items-center justify-center',
            isSelected ? 'border-gold' : 'border-border',
          ].join(' ')}>
            {isSelected && <div className="w-1 h-1 bg-gold" />}
          </div>
        </div>
        {preset.description && (
          <div className="font-body text-[11px] text-dim leading-snug line-clamp-2">{preset.description}</div>
        )}
        <div className="flex flex-wrap gap-1 mt-2">
          {[
            `${preset.voice_count}v`,
            preset.tone,
            preset.pacing,
          ].map(tag => (
            <span key={tag} className="font-mono text-[8px] tracking-widest uppercase border border-border text-faint px-1 py-px">
              {tag}
            </span>
          ))}
        </div>
      </button>
    );
  };

  return (
    <div className="space-y-3">
      {systemPresets.length > 0 && (
        <div>
          <p className="font-mono text-[9px] tracking-widest uppercase text-faint mb-2">System Presets</p>
          <div className="grid grid-cols-2 gap-2">
            {systemPresets.map(preset => <PresetButton key={preset.id} preset={preset} />)}
          </div>
        </div>
      )}

      {customPresets.length > 0 && (
        <div>
          <p className="font-mono text-[9px] tracking-widest uppercase text-faint mb-2">Custom Presets</p>
          <div className="grid grid-cols-2 gap-2">
            {customPresets.map(preset => <PresetButton key={preset.id} preset={preset} />)}
          </div>
        </div>
      )}

      {onCreateCustom && (
        <button
          onClick={onCreateCustom}
          disabled={disabled}
          className={`w-full px-4 py-3 border border-dashed border-border text-faint hover:border-gold-dim hover:text-dim transition-colors font-mono text-[10px] tracking-widest uppercase ${
            disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
          }`}
        >
          + Create Custom Preset
        </button>
      )}
    </div>
  );
}
