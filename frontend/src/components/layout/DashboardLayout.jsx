import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';

export const DashboardLayout = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  const getPageTitle = (pathname) => {
    if (pathname.includes('/composer'))      return 'Post Composer';
    if (pathname.includes('/posts'))         return 'My Posts';
    if (pathname.includes('/calendar'))      return 'Content Calendar';
    if (pathname.includes('/teams'))         return 'Teams & Workspaces';
    if (pathname.includes('/accounts'))      return 'Social Accounts';
    if (pathname.includes('/campaigns'))     return 'Campaigns';
    if (pathname.includes('/analytics'))     return 'Analytics Dashboard';
    if (pathname.includes('/notifications')) return 'Notifications';
    if (pathname.includes('/settings'))      return 'Settings & Appearance';
    return 'Workspace Overview';
  };

  return (
    <div className="sp-bg-atmospheric flex min-h-screen transition-colors" style={{ background: 'var(--bg-page)', color: 'var(--text-primary)' }}>

      {/* Desktop Sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col z-40">
        <Sidebar />
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div
            className="fixed inset-0 backdrop-blur-xs"
            style={{ background: 'rgba(0,0,0,0.5)' }}
            onClick={() => setMobileMenuOpen(false)}
            aria-hidden="true"
          />
          <div className="relative z-10 flex w-72 flex-col shadow-2xl" style={{ background: 'var(--bg-sidebar)' }}>
            <Sidebar onClose={() => setMobileMenuOpen(false)} />
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="relative z-10 flex flex-1 flex-col lg:pl-64 min-w-0">
        <Header
          onMenuClick={() => setMobileMenuOpen(true)}
          title={getPageTitle(location.pathname)}
        />
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
