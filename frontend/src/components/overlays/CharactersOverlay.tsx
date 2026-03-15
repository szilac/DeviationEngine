import { AnimatePresence, motion } from 'motion/react';
import type { Timeline } from '../../types';
import { X } from 'lucide-react';
import CharacterListPanel from '../CharacterListPanel';
import * as RadixDialog from '@radix-ui/react-dialog';

interface CharactersOverlayProps {
  open: boolean;
  onClose: () => void;
  timeline: Timeline;
}

export default function CharactersOverlay({ open, onClose, timeline }: CharactersOverlayProps) {
  return (
    <RadixDialog.Root open={open} onOpenChange={(v) => !v && onClose()}>
      <RadixDialog.Portal forceMount>
        <AnimatePresence>
          {open && (
            <>
              <RadixDialog.Overlay asChild forceMount>
                <motion.div
                  className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                />
              </RadixDialog.Overlay>

              <RadixDialog.Content asChild forceMount>
                <motion.div
                  className="fixed top-0 right-0 bottom-0 z-50 bg-parchment border-l border-border flex flex-col focus:outline-none"
                  style={{ width: 480 }}
                  initial={{ x: '100%' }}
                  animate={{ x: 0 }}
                  exit={{ x: '100%' }}
                  transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
                >
                  <RadixDialog.Title className="sr-only">Characters</RadixDialog.Title>
                  {/* Drawer header */}
                  <div className="flex items-center justify-between px-5 py-4 border-b border-border shrink-0">
                    <div>
                      <p className="rubric-label">§ Characters</p>
                      <h2 className="font-display text-xl text-gold mt-0.5">
                        {timeline.timeline_name || 'Historical Figures'}
                      </h2>
                    </div>
                    <RadixDialog.Close
                      onClick={onClose}
                      className="text-dim hover:text-ink transition-colors duration-150 focus:outline-none cursor-pointer"
                      aria-label="Close"
                    >
                      <X size={16} />
                    </RadixDialog.Close>
                  </div>

                  {/* Drawer body */}
                  <div className="flex-1 overflow-auto">
                    <CharacterListPanel timeline={timeline} />
                  </div>
                </motion.div>
              </RadixDialog.Content>
            </>
          )}
        </AnimatePresence>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
