import * as RadixSlider from '@radix-ui/react-slider';

interface SliderProps {
  value?: number[];
  onValueChange?: (value: number[]) => void;
  min?: number;
  max?: number;
  step?: number;
  label?: string;
  disabled?: boolean;
  className?: string;
}

export default function Slider({
  value,
  onValueChange,
  min = 0,
  max = 100,
  step = 1,
  label,
  disabled,
  className = '',
}: SliderProps) {
  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      {label && (
        <span className="font-mono text-[10px] tracking-widest uppercase text-dim">
          {label}
        </span>
      )}
      <RadixSlider.Root
        value={value}
        onValueChange={onValueChange}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
        className="relative flex items-center w-full h-5 select-none touch-none"
      >
        <RadixSlider.Track className="bg-border relative grow h-px">
          <RadixSlider.Range className="absolute bg-gold-dim h-full" />
        </RadixSlider.Track>
        {(value ?? [0]).map((_, i) => (
          <RadixSlider.Thumb
            key={i}
            className={[
              'block w-3 h-3 bg-parchment border border-gold-dim',
              'hover:border-gold focus:outline-none focus:border-gold',
              'transition-colors duration-150',
              'disabled:opacity-40 disabled:cursor-not-allowed',
            ].join(' ')}
          />
        ))}
      </RadixSlider.Root>
    </div>
  );
}
