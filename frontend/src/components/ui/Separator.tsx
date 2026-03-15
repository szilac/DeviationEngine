import * as RadixSeparator from '@radix-ui/react-separator';

interface SeparatorProps {
  orientation?: 'horizontal' | 'vertical';
  variant?: 'single' | 'double';
  className?: string;
}

export default function Separator({
  orientation = 'horizontal',
  variant = 'single',
  className = '',
}: SeparatorProps) {
  if (orientation === 'vertical') {
    return (
      <RadixSeparator.Root
        orientation="vertical"
        decorative
        className={`w-px bg-border self-stretch ${className}`}
      />
    );
  }

  if (variant === 'double') {
    return (
      <div className={`double-rule my-2 ${className}`} aria-hidden="true" />
    );
  }

  return (
    <RadixSeparator.Root
      orientation="horizontal"
      decorative
      className={`h-px bg-border w-full ${className}`}
    />
  );
}
