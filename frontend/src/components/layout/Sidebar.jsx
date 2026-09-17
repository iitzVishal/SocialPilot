import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Share2,
  Settings,
  LogOut,
  ShieldCheck,
  Calendar,
  Layers,
  BarChart3,
  ChevronRight,
  Send,
  LayoutList,
  Users,
  Bell,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Badge } from '../ui/Badge';

const navItems = [
  { name: 'Overview',           path: '/dashboard',               icon: LayoutDashboard },
  { name: 'Notifications',      path: '/dashboard/notifications', icon: Bell },
  { name: 'Analytics',          path: '/dashboard/analytics',     icon: BarChart3 },
  { name: 'Campaigns',          path: '/dashboard/campaigns',     icon: Layers },
  { name: 'Post Composer',      path: '/dashboard/composer',      icon: Send },
  { name: 'My Posts',           path: '/dashboard/posts',         icon: LayoutList },
  { name: 'Content Calendar',   path: '/dashboard/calendar',      icon: Calendar },
  { name: 'Teams & Workspaces', path: '/dashboard/teams',         icon: Users },
  { name: 'Social Accounts',    path: '/dashboard/accounts',      icon: Share2 },
  { name: 'Settings & Theme',   path: '/dashboard/settings',      icon: Settings },
];


const upcomingModules = [];


export const Sidebar = ({ onClose }) => {
  const { user, logout } = useAuth();

  const getRoleVariant = (role) => {
    switch (role) {
      case 'administrator':  return 'primary';
      case 'marketing_team': return 'success';
      case 'business_user':  return 'warning';
      default:               return 'neutral';
    }
  };

  const formatRole = (role) => {
    if (!role) return 'Creator';
    return role.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  };

  const initial = user?.full_name
    ? user.full_name.charAt(0).toUpperCase()
    : user?.email?.charAt(0).toUpperCase() || 'U';

  return (
    <aside className="flex h-full w-64 flex-col border-r transition-colors"
      style={{
        background: 'var(--bg-sidebar)',
        borderColor: 'var(--border-default)',
      }}
    >

      {/* ── Brand Header ── */}
      <div className="flex h-16 items-center gap-3 px-5 border-b" style={{ borderColor: 'var(--border-default)' }}>
        {/* Green shield logo icon */}
        <div className="relative flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl text-white"
          style={{ background: 'linear-gradient(135deg, #15803D, #22C55E)', boxShadow: '0 0 16px rgba(34,197,94,0.25)' }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M12 2L4 6v6c0 5.25 3.5 10.15 8 11.35C16.5 22.15 20 17.25 20 12V6l-8-4z" fill="white" opacity="0.9"/>
            <path d="M9 12l2 2 4-4" stroke="#15803D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>

        <div>
          <span className="flex items-center gap-1.5 text-sm font-bold tracking-tight font-heading" style={{ color: 'var(--text-primary)' }}>
            SocialPilot
            <span className="rounded px-1.5 py-0.5 text-[10px] font-bold border"
              style={{ background: 'var(--active-nav-bg)', color: 'var(--sp-primary)', borderColor: 'var(--border-subtle)' }}
            >
              PRO
            </span>
          </span>
          <p className="text-xs font-medium leading-none mt-0.5" style={{ color: 'var(--text-muted)' }}>
            Plan. Publish. Perform.
          </p>
        </div>
      </div>

      {/* ── Navigation ── */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-5">

        {/* Core Modules */}
        <div>
          <p className="px-2.5 mb-2 text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
            Core Modules
          </p>
          <nav className="space-y-0.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === '/dashboard'}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-150 ${
                      isActive
                        ? 'font-semibold border'
                        : 'hover:border hover:border-transparent'
                    }`
                  }
                  style={({ isActive }) => isActive ? {
                    background: 'var(--active-nav-bg)',
                    color: 'var(--sp-primary)',
                    borderColor: 'var(--sp-border)',
                  } : {
                    color: 'var(--text-secondary)',
                    border: '1px solid transparent',
                  }}
                >
                  {({ isActive }) => (
                    <>
                      <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg transition-colors"
                        style={isActive ? {
                          background: 'var(--active-nav-bg)',
                          color: 'var(--sp-primary)',
                        } : {
                          color: 'var(--text-muted)',
                        }}
                      >
                        <Icon className="h-4 w-4" aria-hidden="true" />
                      </span>
                      <span className="flex-1">{item.name}</span>
                      {isActive && (
                        <ChevronRight className="h-3.5 w-3.5" style={{ color: 'var(--sp-primary)' }} aria-hidden="true" />
                      )}
                    </>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Coming Soon */}
        <div className="pt-3 border-t" style={{ borderColor: 'var(--border-default)' }}>
          <p className="px-2.5 mb-2 text-[10px] font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
            Coming Soon
          </p>
          <div className="space-y-0.5 opacity-60">
            {upcomingModules.map((item) => {
              const Icon = item.icon;
              return (
                <div
                  key={item.name}
                  className="group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium cursor-not-allowed"
                  style={{ color: 'var(--text-muted)' }}
                >
                  <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg" style={{ color: 'var(--text-muted)' }}>
                    <Icon className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <span className="flex-1 font-medium">{item.name}</span>
                  <Badge variant="soon" size="xs" showDot={false}>
                    {item.milestone}
                  </Badge>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── User Footer ── */}
      <div className="border-t p-3" style={{ borderColor: 'var(--border-default)' }}>
        <div className="flex items-center justify-between gap-2 rounded-xl p-2 transition-colors">
          <div className="flex items-center gap-2.5 overflow-hidden">
            {/* Avatar */}
            <div className="relative flex-shrink-0">
              <div className="flex h-8 w-8 items-center justify-center rounded-full text-white text-xs font-bold"
                style={{ background: 'linear-gradient(135deg, #15803D, #22C55E)' }}
              >
                {initial}
              </div>
              {/* Online status dot */}
              <div className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full border-2"
                style={{ background: '#22C55E', borderColor: 'var(--bg-sidebar)' }}
              />
            </div>
            {/* Name + role */}
            <div className="min-w-0">
              <p className="truncate text-xs font-bold font-heading leading-none" style={{ color: 'var(--text-primary)' }}>
                {user?.full_name || 'SocialPilot User'}
              </p>
              <div className="mt-1">
                <Badge variant={getRoleVariant(user?.role)} size="xs" showDot={false}>
                  <ShieldCheck className="h-2.5 w-2.5" aria-hidden="true" />
                  {formatRole(user?.role)}
                </Badge>
              </div>
            </div>
          </div>

          {/* Sign out */}
          <button
            onClick={logout}
            title="Sign out"
            aria-label="Sign out of SocialPilot"
            className="flex-shrink-0 rounded-lg p-1.5 transition-colors cursor-pointer focus-visible:outline-none"
            style={{ color: 'var(--text-muted)' }}
          >
            <LogOut className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        </div>
      </div>
    </aside>
  );
};
