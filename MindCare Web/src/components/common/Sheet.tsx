// ============================================================
// MindCare — Sheet (modal dialog shell)
// Bottom sheet on phones, centred dialog from `sm` up. Locks page
// scroll and closes on Escape / backdrop tap while open.
// ============================================================

import React, { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';

interface SheetProps {
  open: boolean;
  onClose: () => void;
  /** id of the heading that names the dialog */
  labelledBy: string;
  children: React.ReactNode;
}

const Sheet: React.FC<SheetProps> = ({ open, onClose, labelledBy, children }) => {
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener('keydown', onKey);
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center sm:p-6">
          <motion.div
            className="absolute inset-0 bg-gray-900/50 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            aria-hidden="true"
          />

          <motion.div
            role="dialog"
            aria-modal="true"
            aria-labelledby={labelledBy}
            className="relative w-full sm:max-w-lg max-h-[92dvh] overflow-y-auto bg-[#FBF8F3] rounded-t-3xl sm:rounded-3xl shadow-2xl"
            initial={{ y: 40, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 40, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          >
            {/* Grab handle (phones) */}
            <div className="sm:hidden mx-auto mt-3 h-1.5 w-10 rounded-full bg-gray-300" aria-hidden="true" />

            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="absolute top-4 right-4 p-2 rounded-full text-gray-500 hover:bg-gray-100 hover:text-gray-900 transition-colors"
            >
              <X size={18} />
            </button>

            {children}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

/** Shared field styling for forms inside a Sheet. */
export const sheetInputClass =
  'w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-base sm:text-sm text-gray-900 placeholder:text-gray-400 focus:border-gray-900 focus:outline-none focus:ring-2 focus:ring-gray-900/10 transition';

export default Sheet;
