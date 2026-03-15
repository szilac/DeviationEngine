import * as RadixDialog from '@radix-ui/react-dialog';
import { AnimatePresence, motion } from 'motion/react';
import { X } from 'lucide-react';
import type { ReactNode } from 'react';

interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
  description?: string;
  children: ReactNode;
  /** 'panel' = standard card dialog; 'overlay' = full-viewport overlay */
  variant?: 'panel' | 'overlay';
  /** Width for 'panel' variant */
  width?: string;
}

export default function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  variant = 'panel',
  width = 'max-w-lg',
}: DialogProps) {
  const isOverlay = variant === 'overlay';

  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal forceMount>
        <AnimatePresence>
          {open && (
            <>
        {/* Backdrop */}
        <RadixDialog.Overlay asChild forceMount>
          <motion.div
            className={[
              'fixed inset-0 z-40',
              isOverlay ? 'bg-vellum' : 'bg-black/60 backdrop-blur-sm',
            ].join(' ')}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          />
        </RadixDialog.Overlay>

        {isOverlay ? (
          /* Full-viewport overlay variant — slides up */
          <RadixDialog.Content asChild forceMount>
            <motion.div
              className="fixed inset-0 z-50 bg-vellum overflow-auto focus:outline-none"
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 24 }}
              transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
            >
              <RadixDialog.Title className="sr-only">
                {title || 'Dialog'}
              </RadixDialog.Title>
              <RadixDialog.Close
                className="absolute top-4 right-4 font-mono text-xs text-dim tracking-widest uppercase hover:text-ink transition-colors focus:outline-none flex items-center gap-1.5"
                aria-label="Close"
              >
                <X size={12} /> Close
              </RadixDialog.Close>
              {children}
            </motion.div>
          </RadixDialog.Content>
        ) : (
          /* Panel variant — full-screen scroll container with inner card */
          <RadixDialog.Content
            className="fixed inset-0 z-50 overflow-y-auto focus:outline-none"
            aria-describedby={description ? 'dialog-desc' : undefined}
          >
            <div className="flex min-h-full items-center justify-center p-4 py-8">
              <div className={['bg-parchment border border-border w-full p-6 corner-brackets shadow-[var(--shadow-panel)]', width].join(' ')}>
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div>
                    {title && (
                      <RadixDialog.Title className="font-display text-xl text-gold leading-tight">
                        {title}
                      </RadixDialog.Title>
                    )}
                    {description && (
                      <RadixDialog.Description
                        id="dialog-desc"
                        className="font-mono text-xs text-dim mt-1"
                      >
                        {description}
                      </RadixDialog.Description>
                    )}
                  </div>
                  <RadixDialog.Close
                    className="text-dim hover:text-ink transition-colors focus:outline-none ml-4 shrink-0 cursor-pointer"
                    aria-label="Close"
                  >
                    <X size={16} />
                  </RadixDialog.Close>
                </div>

                {children}
              </div>
            </div>
          </RadixDialog.Content>
        )}
            </>
          )}
        </AnimatePresence>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
