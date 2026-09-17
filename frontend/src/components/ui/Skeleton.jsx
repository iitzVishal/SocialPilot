import React from 'react';

export const Skeleton = ({ className = '', ...props }) => {
  return (
    <div
      className={`animate-pulse rounded-xl ${className}`}
      style={{ background: 'var(--active-nav-bg)', border: '1px solid var(--sp-border)' }}
      {...props}
    />
  );
};
