import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Menu, Sun, Moon, Laptop, Search, Bell, HelpCircle, Zap, CheckCheck, ExternalLink, ArrowRight } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { WorkspaceSelector } from './WorkspaceSelector';
import { notificationsAPI } from '../../lib/api';

export const Header = ({ onMenuClick, title = 'Workspace' }) => {
  const { theme, setTheme, user } = useAuth();
  const navigate = useNavigate();

  const [unreadCount, setUnreadCount] = useState(0);
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [recentNotifs, setRecentNotifs] = useState([]);
  const [loadingNotifs, setLoadingNotifs] = useState(false);
  const popoverRef = useRef(null);

  const fetchUnreadCount = useCallback(async () => {
    if (!user) return;
    try {
      const res = await notificationsAPI.getUnreadCount();
      setUnreadCount(res.data.count ?? 0);
    } catch (err) {
      // Quiet fail for header count
    }
  }, [user]);

  useEffect(() => {
    fetchUnreadCount();
    // Poll unread count every 30 seconds
    const interval = setInterval(fetchUnreadCount, 30000);
    return () => clearInterval(interval);
  }, [fetchUnreadCount]);

  const loadRecentNotifications = async () => {
    setLoadingNotifs(true);
    try {
      const res = await notificationsAPI.list({ limit: 5 });
      setRecentNotifs(res.data.items || []);
    } catch (err) {
      console.error('Failed to load header notifications:', err);
    } finally {
      setLoadingNotifs(false);
    }
  };

  const togglePopover = () => {
    if (!popoverOpen) {
      loadRecentNotifications();
    }
    setPopoverOpen(!popoverOpen);
  };

  // Close popover when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) {
        setPopoverOpen(false);
      }
    };
    if (popoverOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [popoverOpen]);

  const handleMarkItemRead = async (id, link, e) => {
    if (e) e.stopPropagation();
    try {
      await notificationsAPI.markAsRead(id);
      setRecentNotifs((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((c) => Math.max(0, c - 1));
      if (link) {
        setPopoverOpen(false);
        navigate(link);
      }
    } catch (err) {
      console.error('Failed to mark read:', err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsAPI.markAllAsRead();
      setRecentNotifs((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error('Failed to mark all read:', err);
    }
  };

  const cycleTheme = () => {
    if (theme === 'light') setTheme('dark');
    else if (theme === 'dark') setTheme('system');
    else setTheme('light');
  };

  const getThemeIcon = () => {
    if (theme === 'light')  return <Sun  className="h-4 w-4" style={{ color: '#F59E0B' }} aria-hidden="true" />;
    if (theme === 'dark')   return <Moon className="h-4 w-4" style={{ color: '#22C55E' }} aria-hidden="true" />;
    return <Laptop className="h-4 w-4" style={{ color: 'var(--text-muted)' }} aria-hidden="true" />;
  };

  const initial = user?.full_name
    ? user.full_name.charAt(0).toUpperCase()
    : user?.email?.charAt(0).toUpperCase() || 'U';

  const iconBtnStyle = {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '32px',
    height: '32px',
    borderRadius: '10px',
    border: '1px solid var(--border-default)',
    background: 'var(--bg-surface-secondary)',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  };

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between px-4 sm:px-6 backdrop-blur-md transition-colors"
      style={{
        background: 'var(--bg-header)',
        borderBottom: '1px solid var(--border-default)',
      }}
    >

      {/* Left: mobile toggle + workspace selector + page title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          aria-label="Open navigation menu"
          className="lg:hidden rounded-xl p-2 transition-colors cursor-pointer"
          style={{ color: 'var(--text-secondary)', background: 'transparent' }}
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </button>

        <WorkspaceSelector />

        <span className="select-none hidden sm:inline" style={{ color: 'var(--text-muted)' }}>/</span>

        <div>
          <h2 className="text-xs sm:text-sm font-bold tracking-tight" style={{ color: 'var(--text-muted)' }}>
            {title}
          </h2>
        </div>
      </div>

      {/* Center: Search */}
      <div className="hidden md:flex items-center flex-1 max-w-sm mx-6">
        <div className="relative w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 pointer-events-none" style={{ color: 'var(--text-muted)' }} aria-hidden="true" />
          <input
            type="search"
            placeholder="Search anything…"
            aria-label="Search the workspace"
            className="w-full rounded-xl py-1.5 pl-8.5 pr-12 text-xs transition-all focus:outline-none"
            style={{
              background: 'var(--input-bg)',
              border: '1px solid var(--input-border)',
              color: 'var(--input-text)',
            }}
          />
          <div className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none">
            <kbd className="rounded px-1.5 py-0.5 text-[10px] font-semibold"
              style={{ border: '1px solid var(--border-default)', background: 'var(--bg-surface-secondary)', color: 'var(--text-muted)' }}
            >
              ⌘K
            </kbd>
          </div>
        </div>
      </div>

      {/* Right: Controls */}
      <div className="flex items-center gap-2">

        {/* API Status pill */}
        <div className="hidden xl:flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold"
          style={{ border: '1px solid var(--border-accent)', background: 'var(--active-nav-bg)', color: 'var(--sp-primary)' }}
        >
          <span className="h-1.5 w-1.5 rounded-full animate-sp-pulse-glow" style={{ background: '#22C55E' }} aria-hidden="true" />
          API Live
        </div>

        {/* Quick Create Post button */}
        <button
          type="button"
          onClick={() => navigate('/dashboard/composer')}
          aria-label="Create new post"
          className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer hover:opacity-90"
          style={{
            background: 'linear-gradient(135deg, #15803D, #22C55E)',
            color: '#FFFFFF',
            boxShadow: '0 0 16px rgba(34,197,94,0.25)',
          }}
        >
          <Zap className="h-3.5 w-3.5" aria-hidden="true" />
          New Post
        </button>

        {/* Notifications Button & Popover */}
        <div className="relative" ref={popoverRef}>
          <button
            type="button"
            onClick={togglePopover}
            aria-label={`View notifications (${unreadCount} unread)`}
            style={iconBtnStyle}
          >
            <Bell className="h-4 w-4" aria-hidden="true" />
            {unreadCount > 0 && (
              <span
                className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-bold text-white shadow-xs"
                style={{ background: '#EF4444' }}
              >
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {/* Notifications Dropdown Popover */}
          {popoverOpen && (
            <div
              className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl border shadow-2xl z-50 overflow-hidden"
              style={{ background: 'var(--bg-card)', borderColor: 'var(--border-default)' }}
            >
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'var(--border-default)' }}>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold font-heading" style={{ color: 'var(--text-primary)' }}>
                    Notifications
                  </span>
                  {unreadCount > 0 && (
                    <span className="rounded-full px-2 py-0.5 text-[10px] font-bold text-white" style={{ background: '#22C55E' }}>
                      {unreadCount} new
                    </span>
                  )}
                </div>
                {unreadCount > 0 && (
                  <button
                    onClick={handleMarkAllRead}
                    className="text-xs font-medium flex items-center gap-1 cursor-pointer transition-opacity hover:opacity-80"
                    style={{ color: 'var(--sp-primary)' }}
                  >
                    <CheckCheck className="h-3.5 w-3.5" /> Mark all read
                  </button>
                )}
              </div>

              {/* Items List */}
              <div className="max-h-80 overflow-y-auto divide-y" style={{ borderColor: 'var(--border-subtle)' }}>
                {loadingNotifs ? (
                  <div className="p-4 space-y-3">
                    <div className="h-12 w-full rounded-xl bg-black/5 dark:bg-white/5 animate-pulse" />
                    <div className="h-12 w-full rounded-xl bg-black/5 dark:bg-white/5 animate-pulse" />
                  </div>
                ) : recentNotifs.length === 0 ? (
                  <div className="py-8 text-center px-4">
                    <Bell className="h-8 w-8 mx-auto mb-2 opacity-20" style={{ color: 'var(--text-muted)' }} />
                    <p className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>You're all caught up!</p>
                    <p className="text-[11px] mt-0.5" style={{ color: 'var(--text-muted)' }}>No notifications to display.</p>
                  </div>
                ) : (
                  recentNotifs.map((n) => (
                    <div
                      key={n.id}
                      onClick={() => handleMarkItemRead(n.id, n.link)}
                      className="flex items-start gap-3 p-3 text-left transition-colors cursor-pointer hover:bg-black/3 dark:hover:bg-white/3"
                      style={{ background: n.is_read ? 'transparent' : 'var(--active-nav-bg)' }}
                    >
                      <div className="h-2 w-2 mt-1.5 rounded-full flex-shrink-0"
                        style={{ background: n.is_read ? 'transparent' : 'var(--sp-primary)' }}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-bold truncate" style={{ color: 'var(--text-primary)' }}>{n.title}</p>
                        <p className="text-[11px] line-clamp-2 mt-0.5 leading-snug" style={{ color: 'var(--text-secondary)' }}>{n.message}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Footer */}
              <div className="p-2.5 border-t text-center" style={{ borderColor: 'var(--border-default)', background: 'var(--bg-surface-secondary)' }}>
                <Link
                  to="/dashboard/notifications"
                  onClick={() => setPopoverOpen(false)}
                  className="inline-flex items-center gap-1.5 text-xs font-bold transition-opacity hover:opacity-80"
                  style={{ color: 'var(--sp-primary)' }}
                >
                  View All Notifications <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* Help */}
        <button
          type="button"
          aria-label="Help & Documentation"
          className="hidden sm:flex"
          style={iconBtnStyle}
        >
          <HelpCircle className="h-4 w-4" aria-hidden="true" />
        </button>

        {/* Theme Toggle */}
        <button
          onClick={cycleTheme}
          title={`Theme: ${theme} — click to cycle`}
          aria-label="Toggle visual theme"
          style={iconBtnStyle}
        >
          {getThemeIcon()}
        </button>

        {/* Divider + Avatar */}
        <div className="hidden sm:flex items-center gap-2 pl-2" style={{ borderLeft: '1px solid var(--border-default)' }}>
          <div className="relative flex h-8 w-8 items-center justify-center rounded-full text-white text-xs font-bold"
            style={{ background: 'linear-gradient(135deg, #15803D, #22C55E)', boxShadow: '0 0 12px rgba(34,197,94,0.2)' }}
          >
            {initial}
            <div className="absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full border-2"
              style={{ background: '#22C55E', borderColor: 'var(--bg-header)' }}
            />
          </div>
        </div>
      </div>
    </header>
  );
};

