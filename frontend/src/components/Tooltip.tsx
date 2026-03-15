import React, { useState, useRef, useEffect } from 'react';

interface TooltipProps {
  content: string | React.ReactNode;
  children: React.ReactNode;
  position?: 'top' | 'bottom' | 'left' | 'right';
  maxWidth?: string;
  disabled?: boolean;
}

const Tooltip: React.FC<TooltipProps> = ({
  content,
  children,
  position = 'top',
  maxWidth = '280px',
  disabled = false,
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0, left: 0 });
  const triggerRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isVisible && triggerRef.current && tooltipRef.current) {
      const triggerRect = triggerRef.current.getBoundingClientRect();
      const tooltipRect = tooltipRef.current.getBoundingClientRect();

      let top = 0;
      let left = 0;

      switch (position) {
        case 'top':
          top = -tooltipRect.height - 10;
          left = (triggerRect.width - tooltipRect.width) / 2;
          break;
        case 'bottom':
          top = triggerRect.height + 10;
          left = (triggerRect.width - tooltipRect.width) / 2;
          break;
        case 'left':
          top = (triggerRect.height - tooltipRect.height) / 2;
          left = -tooltipRect.width - 10;
          break;
        case 'right':
          top = (triggerRect.height - tooltipRect.height) / 2;
          left = triggerRect.width + 10;
          break;
      }

      setTooltipPosition({ top, left });
    }
  }, [isVisible, position]);

  if (disabled) return <>{children}</>;

  // Arrow position styles per direction
  const arrowStyle: React.CSSProperties = {
    position: 'absolute',
    width: '6px',
    height: '6px',
    backgroundColor: 'var(--color-parchment, #2A1F0A)',
    transform: 'rotate(45deg)',
    ...(position === 'top'    && { bottom: '-4px', left: '50%', marginLeft: '-3px', borderRight: '1px solid', borderBottom: '1px solid', borderColor: 'var(--color-border, #4A3D1A)' }),
    ...(position === 'bottom' && { top:    '-4px', left: '50%', marginLeft: '-3px', borderLeft:  '1px solid', borderTop:    '1px solid', borderColor: 'var(--color-border, #4A3D1A)' }),
    ...(position === 'left'   && { right:  '-4px', top:  '50%', marginTop:  '-3px', borderRight: '1px solid', borderTop:    '1px solid', borderColor: 'var(--color-border, #4A3D1A)' }),
    ...(position === 'right'  && { left:   '-4px', top:  '50%', marginTop:  '-3px', borderLeft:  '1px solid', borderBottom: '1px solid', borderColor: 'var(--color-border, #4A3D1A)' }),
  };

  return (
    <div
      ref={triggerRef}
      className="relative inline-block"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
      onFocus={() => setIsVisible(true)}
      onBlur={() => setIsVisible(false)}
    >
      {children}

      {isVisible && (
        <div
          ref={tooltipRef}
          className="absolute z-50 pointer-events-none"
          style={{ top: `${tooltipPosition.top}px`, left: `${tooltipPosition.left}px`, width: maxWidth }}
        >
          <div className="relative bg-parchment border border-border px-3 py-2 shadow-[0_4px_16px_rgba(0,0,0,0.5)]">
            <div className="font-body text-xs text-dim leading-relaxed">
              {content}
            </div>
            <div style={arrowStyle} />
          </div>
        </div>
      )}
    </div>
  );
};

export default Tooltip;

export const InfoIcon: React.FC<{ content: string | React.ReactNode; className?: string; maxWidth?: string; position?: 'top' | 'bottom' | 'left' | 'right' }> = ({
  content,
  className = '',
  maxWidth,
  position,
}) => (
  <Tooltip content={content} maxWidth={maxWidth} position={position}>
    <button
      type="button"
      className={`inline-flex items-center justify-center w-4 h-4 font-mono text-[9px] text-faint border border-border hover:border-gold-dim hover:text-gold transition-colors ${className}`}
      aria-label="More information"
    >
      ?
    </button>
  </Tooltip>
);
