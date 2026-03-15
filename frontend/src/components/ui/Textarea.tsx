import { forwardRef } from 'react';
import type { TextareaHTMLAttributes } from 'react';

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
}

const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
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
        <textarea
          ref={ref}
          id={id}
          className={[
            'bg-transparent text-ink font-body text-base',
            'border border-border',
            'px-3 py-2',
            'placeholder:text-faint',
            'focus:outline-none focus:border-gold-dim',
            'transition-colors duration-150',
            'resize-y min-h-[80px]',
            'disabled:opacity-40 disabled:cursor-not-allowed',
            className,
          ].join(' ')}
          {...props}
        />
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';
export default Textarea;
