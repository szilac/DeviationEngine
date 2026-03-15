type BadgeVariant = 'default' | 'gold' | 'rubric' | 'quantum' | 'success' | 'warning';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

const variantClasses: Record<BadgeVariant, string> = {
  default:  'text-dim  border-border',
  gold:     'text-gold  border-gold-dim',
  rubric:   'text-rubric border-rubric-dim',
  quantum:  'text-quantum border-quantum/30',
  success:  'text-success border-success/40',
  warning:  'text-warning border-warning/40',
};

export default function Badge({ children, variant = 'default', className = '' }: BadgeProps) {
  return (
    <span
      className={[
        'inline-flex items-center px-2 py-0.5',
        'font-mono text-[10px] tracking-widest uppercase',
        'border',
        variantClasses[variant],
        className,
      ].join(' ')}
    >
      {children}
    </span>
  );
}
