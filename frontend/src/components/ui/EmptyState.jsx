import React from 'react';
import { Button } from './Button';

export const EmptyState = ({ icon: Icon, title, description, actionLabel, onAction }) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center rounded-2xl border border-dashed"
      style={{ background: 'var(--sp-surface-2)', borderColor: 'var(--sp-border)' }}
    >
      {Icon && (
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl mb-4 border"
          style={{ background: 'var(--active-nav-bg)', borderColor: 'var(--sp-border)', color: 'var(--sp-primary)' }}
        >
          <Icon className="h-7 w-7" />
        </div>
      )}
      <h3 className="text-base font-bold font-heading" style={{ color: 'var(--sp-text)' }}>{title}</h3>
      <p className="mt-1 text-xs max-w-sm" style={{ color: 'var(--sp-text-secondary)' }}>{description}</p>
      {actionLabel && onAction && (
        <div className="mt-6">
          <Button onClick={onAction} variant="primary">
            {actionLabel}
          </Button>
        </div>
      )}
    </div>
  );
};
