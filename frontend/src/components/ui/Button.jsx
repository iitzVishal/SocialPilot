import React from 'react';
import { Loader2 } from 'lucide-react';

const variants = {
  primary:
    'bg-gradient-to-r from-emerald-600 to-green-500 hover:from-emerald-500 hover:to-green-400 text-white font-semibold shadow-md active:scale-[0.98] border-0',
  secondary:
    'bg-[var(--sp-surface-2)] text-[var(--sp-text)] border border-[var(--sp-border)] hover:border-[var(--sp-border-strong)] shadow-sm',
  outline:
    'border border-[var(--sp-border)] hover:border-[var(--sp-border-strong)] hover:bg-[var(--active-nav-bg)] text-[var(--sp-text-secondary)] hover:text-[var(--sp-text)]',
  danger:
    'bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500 text-white shadow-sm active:scale-[0.98]',
  ghost:
    'text-[var(--sp-text-secondary)] hover:text-[var(--sp-text)] hover:bg-[var(--active-nav-bg)]',
  success:
    'bg-gradient-to-r from-emerald-600 to-green-500 hover:from-emerald-500 hover:to-green-400 text-white shadow-sm active:scale-[0.98]',
  'hero-cta':
    'bg-gradient-to-r from-emerald-600 to-green-500 hover:from-emerald-500 hover:to-green-400 !text-white font-bold shadow-lg border-0 ring-0',
};

const sizes = {
  xs: 'px-2.5 py-1 text-xs rounded-lg gap-1 font-medium',
  sm: 'px-3.5 py-1.5 text-xs rounded-xl gap-1.5 font-medium',
  md: 'px-4 py-2 text-sm rounded-xl gap-2 font-medium',
  lg: 'px-5 py-2.5 text-base rounded-xl gap-2.5 font-semibold',
};

export const Button = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled = false,
  className = '',
  icon: Icon,
  ...props
}) => {
  return (
    <button
      disabled={disabled || isLoading}
      className={`inline-flex items-center justify-center transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--sp-primary)] disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer ${variants[variant] || variants.primary} ${sizes[size]} ${className}`}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
      ) : (
        Icon && <Icon className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
      )}
      {children}
    </button>
  );
};
