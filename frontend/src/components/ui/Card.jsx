import React from 'react';

export const Card = ({ children, className = '', hover = true, accent, ...props }) => {
  return (
    <div
      className={`sp-card rounded-2xl transition-all duration-200 p-6 ${
        accent
          ? `border-l-4 ${accent}`
          : ''
      } ${
        hover
          ? 'hover:-translate-y-0.5 cursor-pointer'
          : ''
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

export const CardHeader = ({ title, description, action, headingLevel = 'h2', className = '' }) => {
  const HeadingTag = headingLevel === 'h3' ? 'h3' : 'h2';
  return (
    <div className={`flex flex-wrap items-center justify-between gap-4 pb-4 border-b ${className}`}
      style={{ borderColor: 'var(--sp-border)' }}
    >
      <div className="min-w-0 flex-1">
        {title && (
          <HeadingTag className="text-base sm:text-lg font-bold tracking-tight font-heading"
            style={{ color: 'var(--sp-text)' }}
          >
            {title}
          </HeadingTag>
        )}
        {description && (
          <p className="text-xs mt-1 leading-relaxed" style={{ color: 'var(--sp-text-muted)' }}>
            {description}
          </p>
        )}
      </div>
      {action && <div className="flex-shrink-0 flex items-center">{action}</div>}
    </div>
  );
};
