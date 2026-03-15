import { forwardRef } from 'react';
import type { ButtonHTMLAttributes } from 'react';

type Variant = 'primary' | 'ghost' | 'rubric' | 'quantum';
type Size    = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const variantClasses: Record<Variant, string> = {
  primary: [
    'bg-gold text-vellum border border-gold',
    'hover:bg-gold-2 hover:border-gold-2',
    'disabled:opacity-40 disabled:cursor-not-allowed',
  ].join(' '),

  ghost: [
    'bg-transparent text-dim border border-border',
    'hover:text-ink hover:border-gold-dim',
    'disabled:opacity-40 disabled:cursor-not-allowed',
  ].join(' '),

  rubric: [
    'bg-transparent text-rubric border border-rubric-dim',
    'hover:bg-rubric-dim hover:text-ink',
    'disabled:opacity-40 disabled:cursor-not-allowed',
  ].join(' '),

  quantum: [
    'bg-transparent text-quantum border border-quantum/30',
    'hover:border-quantum hover:text-wave',
    'disabled:opacity-40 disabled:cursor-not-allowed',
  ].join(' '),
};

const sizeClasses: Record<Size, string> = {
  sm: 'px-3 py-1 text-[10px] tracking-widest',
  md: 'px-4 py-2 text-xs tracking-widest',
  lg: 'px-6 py-3 text-sm tracking-widest',
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'ghost', size = 'md', className = '', children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={[
          'font-mono uppercase transition-colors duration-150 cursor-pointer',
          'focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-gold',
          variantClasses[variant],
          sizeClasses[size],
          className,
        ].join(' ')}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
export default Button;
