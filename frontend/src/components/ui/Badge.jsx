import React from 'react';

const variantClasses = {
  success: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/25 dark:border-emerald-500/20',
  warning: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/25 dark:border-amber-500/20',
  danger:  'bg-rose-500/10  text-rose-700  dark:text-rose-400  border-rose-500/25  dark:border-rose-500/20',
  neutral: 'bg-slate-100    text-slate-600  dark:bg-slate-800/80 dark:text-slate-400 border-slate-200 dark:border-slate-700/80',
  primary: 'bg-violet-500/10 text-violet-700 dark:text-violet-400 border-violet-500/25 dark:border-violet-500/20',
  blue:    'bg-blue-500/10  text-blue-700  dark:text-blue-400  border-blue-500/25  dark:border-blue-500/20',
  cyan:    'bg-cyan-500/10  text-cyan-700  dark:text-cyan-400  border-cyan-500/25  dark:border-cyan-500/20',
  soon:    'bg-slate-100/80 text-slate-400  dark:bg-slate-800/50 dark:text-slate-500 border-slate-200/80 dark:border-slate-700/50',
  active:  'bg-violet-500/10 text-violet-700 dark:text-violet-300 border-violet-500/25 dark:border-violet-500/30',
};

export const Badge = ({ children, variant = 'neutral', size = 'sm', showDot = true, className = '' }) => {
  const sizeClasses = size === 'xs' ? 'px-2 py-0.5 text-[10px]' : 'px-2.5 py-0.5 text-xs font-medium';
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border font-medium ${variantClasses[variant] || variantClasses.neutral} ${sizeClasses} ${className}`}
    >
      {showDot && <span className="h-1.5 w-1.5 rounded-full bg-current opacity-80 flex-shrink-0" />}
      {children}
    </span>
  );
};
