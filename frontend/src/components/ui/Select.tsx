import * as RadixSelect from '@radix-ui/react-select';
import { ChevronDown, Check } from 'lucide-react';

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

interface SelectProps {
  value?: string;
  onValueChange?: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  label?: string;
  disabled?: boolean;
  className?: string;
}

export default function Select({
  value,
  onValueChange,
  options,
  placeholder = 'Select…',
  label,
  disabled,
  className = '',
}: SelectProps) {
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      {label && (
        <span className="font-mono text-[10px] tracking-widest uppercase text-dim">
          {label}
        </span>
      )}
      <RadixSelect.Root value={value} onValueChange={onValueChange} disabled={disabled}>
        <RadixSelect.Trigger
          className={[
            'flex items-center justify-between',
            'bg-transparent text-ink font-mono text-xs',
            'border-b border-border px-0 py-1.5',
            'focus:outline-none focus:border-gold-dim',
            'data-[placeholder]:text-faint',
            'transition-colors duration-150',
            'disabled:opacity-40 disabled:cursor-not-allowed',
            'cursor-pointer w-full',
          ].join(' ')}
        >
          <RadixSelect.Value placeholder={placeholder} />
          <RadixSelect.Icon>
            <ChevronDown size={12} className="text-dim" />
          </RadixSelect.Icon>
        </RadixSelect.Trigger>

        <RadixSelect.Portal>
          <RadixSelect.Content
            className={[
              'bg-parchment border border-border',
              'shadow-[var(--shadow-panel)]',
              'z-50 overflow-hidden',
            ].join(' ')}
            position="popper"
            sideOffset={4}
          >
            <RadixSelect.Viewport>
              {options.map((opt) => (
                <RadixSelect.Item
                  key={opt.value}
                  value={opt.value}
                  disabled={opt.disabled}
                  className={[
                    'flex items-center justify-between',
                    'px-3 py-2 font-mono text-xs text-dim',
                    'cursor-pointer select-none',
                    'hover:text-ink hover:bg-overlay',
                    'data-[state=checked]:text-gold',
                    'data-[disabled]:opacity-40 data-[disabled]:cursor-not-allowed',
                    'focus:outline-none focus:bg-overlay',
                    'transition-colors duration-100',
                  ].join(' ')}
                >
                  <RadixSelect.ItemText>{opt.label}</RadixSelect.ItemText>
                  <RadixSelect.ItemIndicator>
                    <Check size={10} className="text-gold" />
                  </RadixSelect.ItemIndicator>
                </RadixSelect.Item>
              ))}
            </RadixSelect.Viewport>
          </RadixSelect.Content>
        </RadixSelect.Portal>
      </RadixSelect.Root>
    </div>
  );
}
