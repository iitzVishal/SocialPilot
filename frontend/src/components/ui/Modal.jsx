import React, { useEffect } from 'react';
import { X } from 'lucide-react';

export const Modal = ({ isOpen, onClose, title, description, children, maxWidth = 'max-w-lg' }) => {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = 'unset';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity duration-300"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Dialog */}
      <div
        className={`sp-card relative z-10 w-full ${maxWidth} p-6 shadow-2xl transition-all duration-200 my-8`}
      >
        <div className="flex items-start justify-between gap-4 pb-4 border-b" style={{ borderColor: 'var(--sp-border)' }}>
          <div>
            {title && <h3 className="text-lg font-bold font-heading" style={{ color: 'var(--sp-text)' }}>{title}</h3>}
            {description && <p className="text-xs mt-1" style={{ color: 'var(--sp-text-muted)' }}>{description}</p>}
          </div>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="rounded-lg p-1.5 transition-colors cursor-pointer"
            style={{ color: 'var(--sp-text-muted)' }}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mt-4">{children}</div>
      </div>
    </div>
  );
};
