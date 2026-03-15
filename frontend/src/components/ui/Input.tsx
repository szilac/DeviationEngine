import { forwardRef } from 'react';
import type { InputHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, className = '', id, ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label
            htmlFor={id}
            className="font-mono text-[10px] tracking-widest uppercase text-dim"
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={id}
          className={[
            'bg-transparent text-ink font-body text-base',
            'border-0 border-b border-border',
            'px-0 py-1.5',
            'placeholder:text-faint',
            'focus:outline-none focus-visible:border-gold-dim',
            'transition-colors duration-150',
            'disabled:opacity-40 disabled:cursor-not-allowed',
            className,
          ].join(' ')}
          {...props}
        />
      </div>
    );
  }
);

Input.displayName = 'Input';
export default Input;
