import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { notificationsAPI } from '../lib/api';
import {
  Bell,
  CheckCircle2,
  AlertCircle,
  UserPlus,
  UserMinus,
  ShieldAlert,
  Send,
  CheckCheck,
  XCircle,
  Layers,
  Info,
  RefreshCw,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';

/* ─────────────────────────────────────────────────────
   TYPE METADATA & ICONS
───────────────────────────────────────────────────── */
const TYPE_CONFIG = {
  team_invitation:     { label: 'Invitation',  icon: UserPlus,    color: '#3B82F6', bg: 'rgba(59,130,246,0.12)' },
  invitation_accepted: { label: 'Accepted',    icon: CheckCircle2,color: '#22C55E', bg: 'rgba(34,197,94,0.12)' },
  invitation_rejected: { label: 'Declined',    icon: XCircle,     color: '#EF4444', bg: 'rgba(239,68,68,0.12)' },
  team_member_added:   { label: 'Member Added',icon: UserPlus,    color: '#22C55E', bg: 'rgba(34,197,94,0.12)' },
  team_member_removed: { label: 'Member Left', icon: UserMinus,   color: '#EF4444', bg: 'rgba(239,68,68,0.12)' },
  role_changed:        { label: 'Role Update', icon: ShieldAlert, color: '#F59E0B', bg: 'rgba(245,158,11,0.12)' },
  post_submitted:      { label: 'Approval Req',icon: Send,        color: '#F59E0B', bg: 'rgba(245,158,11,0.12)' },
  post_approved:       { label: 'Post Approved',icon: CheckCircle2,color: '#22C55E', bg: 'rgba(34,197,94,0.12)' },
  post_rejected:       { label: 'Post Rejected',icon: XCircle,    color: '#EF4444', bg: 'rgba(239,68,68,0.12)' },
  post_published:      { label: 'Published',   icon: Send,        color: '#22C55E', bg: 'rgba(34,197,94,0.12)' },
  post_failed:         { label: 'Publish Fail',icon: AlertCircle, color: '#EF4444', bg: 'rgba(239,68,68,0.12)' },
  campaign_created:    { label: 'Campaign',    icon: Layers,      color: '#A855F7', bg: 'rgba(168,85,247,0.12)' },
  campaign_updated:    { label: 'Campaign',    icon: Layers,      color: '#A855F7', bg: 'rgba(168,85,247,0.12)' },
  campaign_completed:  { label: 'Campaign',    icon: CheckCircle2,color: '#22C55E', bg: 'rgba(34,197,94,0.12)' },
  system:              { label: 'System',      icon: Info,        color: '#64748B', bg: 'rgba(100,116,139,0.12)' },
};

function formatTimeAgo(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diffSec = Math.floor((now - date) / 1000);

  if (diffSec < 60) return 'Just now';
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  if (diffSec < 604800) return `${Math.floor(diffSec / 86400)}d ago`;
  return date.toLocaleDateString();
}

export default function NotificationsPage() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState('all'); // 'all' | 'unread'
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [markingAll, setMarkingAll] = useState(false);

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        page,
        limit: 15,
        unread: filter === 'unread' ? true : undefined,
      };
      const res = await notificationsAPI.list(params);
      setData(res.data);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load notifications.');
    } finally {
      setLoading(false);
    }
  }, [filter, page]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  const handleMarkAsRead = async (id, link, e) => {
    if (e) e.stopPropagation();
    try {
      await notificationsAPI.markAsRead(id);
      setData((prev) => {
        if (!prev) return prev;
        const updatedItems = prev.items.map((item) =>
          item.id === id ? { ...item, is_read: true, read_at: new Date().toISOString() } : item
        );
        return {
          ...prev,
          items: updatedItems,
          unread_count: Math.max(0, prev.unread_count - 1),
        };
      });
      if (link) {
        navigate(link);
      }
    } catch (err) {
      console.error('Failed to mark notification read:', err);
    }
  };

  const handleMarkAllAsRead = async () => {
    setMarkingAll(true);
    try {
      await notificationsAPI.markAllAsRead();
      setData((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          items: prev.items.map((item) => ({ ...item, is_read: true, read_at: new Date().toISOString() })),
          unread_count: 0,
        };
      });
    } catch (err) {
      console.error('Failed to mark all read:', err);
    } finally {
      setMarkingAll(false);
    }
  };

  const items = data?.items ?? [];
  const unreadCount = data?.unread_count ?? 0;
  const totalPages = data?.total_pages ?? 1;

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold font-heading" style={{ color: 'var(--text-primary)' }}>
              Notifications
            </h1>
            {unreadCount > 0 && (
              <Badge variant="primary" size="sm" showDot={false}>
                {unreadCount} Unread
              </Badge>
            )}
          </div>
          <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
            Stay updated with workspace events, post approvals, and team invitations.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllAsRead}
              disabled={markingAll}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer hover:shadow-xs disabled:opacity-50"
              style={{ borderColor: 'var(--border-default)', background: 'var(--bg-card)', color: 'var(--text-primary)' }}
            >
              <CheckCheck className="h-3.5 w-3.5" style={{ color: 'var(--sp-primary)' }} />
              {markingAll ? 'Marking...' : 'Mark All as Read'}
            </button>
          )}

          <button
            onClick={fetchNotifications}
            disabled={loading}
            title="Refresh notifications"
            className="h-9 w-9 flex items-center justify-center rounded-xl border transition-all hover:shadow-xs disabled:opacity-50"
            style={{ borderColor: 'var(--border-default)', background: 'var(--bg-card)' }}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} style={{ color: 'var(--text-muted)' }} />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b" style={{ borderColor: 'var(--border-default)' }}>
        {[
          { key: 'all', label: 'All Notifications' },
          { key: 'unread', label: `Unread (${unreadCount})` },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => {
              setFilter(tab.key);
              setPage(1);
            }}
            className="px-4 py-2.5 text-xs font-semibold transition-all relative cursor-pointer"
            style={{
              color: filter === tab.key ? 'var(--sp-primary)' : 'var(--text-muted)',
              borderBottom: filter === tab.key ? '2px solid var(--sp-primary)' : '2px solid transparent',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Error state */}
      {error && !loading && (
        <div className="flex flex-col items-center justify-center py-16 gap-3">
          <AlertCircle className="h-10 w-10 text-red-500" />
          <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{error}</p>
          <button
            onClick={fetchNotifications}
            className="px-4 py-1.5 rounded-xl text-xs font-semibold text-white cursor-pointer"
            style={{ background: 'var(--sp-primary)' }}
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-16 w-full rounded-2xl" />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && items.length === 0 && (
        <div
          className="flex flex-col items-center justify-center py-20 rounded-2xl border text-center p-6"
          style={{ background: 'var(--bg-card)', borderColor: 'var(--border-default)' }}
        >
          <div className="h-12 w-12 rounded-2xl flex items-center justify-center mb-3" style={{ background: 'var(--active-nav-bg)' }}>
            <Bell className="h-6 w-6" style={{ color: 'var(--sp-primary)' }} />
          </div>
          <p className="text-base font-bold font-heading" style={{ color: 'var(--text-primary)' }}>
            {filter === 'unread' ? 'No Unread Notifications' : "You're All Caught Up!"}
          </p>
          <p className="text-xs max-w-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            {filter === 'unread'
              ? 'You have read all your notifications.'
              : 'When team members invite you, update roles, or submit posts for approval, notifications will appear here.'}
          </p>
        </div>
      )}

      {/* Notifications List */}
      {!loading && !error && items.length > 0 && (
        <div className="space-y-2">
          {items.map((item) => {
            const config = TYPE_CONFIG[item.type] || TYPE_CONFIG.system;
            const Icon = config.icon;
            return (
              <div
                key={item.id}
                onClick={() => handleMarkAsRead(item.id, item.link)}
                className="group flex items-start gap-4 p-4 rounded-2xl border transition-all duration-150 cursor-pointer hover:shadow-md"
                style={{
                  background: item.is_read ? 'var(--bg-card)' : 'var(--active-nav-bg)',
                  borderColor: item.is_read ? 'var(--border-default)' : 'var(--sp-border)',
                }}
              >
                {/* Type Icon */}
                <div
                  className="h-10 w-10 rounded-xl flex items-center justify-center flex-shrink-0 transition-transform group-hover:scale-105"
                  style={{ background: config.bg }}
                >
                  <Icon className="h-5 w-5" style={{ color: config.color }} />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded-full border"
                      style={{
                        color: config.color,
                        borderColor: `${config.color}30`,
                        background: `${config.color}10`,
                      }}
                    >
                      {config.label}
                    </span>
                    <span className="text-[11px] font-medium" style={{ color: 'var(--text-muted)' }}>
                      {formatTimeAgo(item.created_at)}
                    </span>
                    {!item.is_read && (
                      <span className="h-2 w-2 rounded-full flex-shrink-0" style={{ background: 'var(--sp-primary)' }} title="Unread" />
                    )}
                  </div>

                  <p className="text-sm font-bold font-heading mt-1" style={{ color: 'var(--text-primary)' }}>
                    {item.title}
                  </p>
                  <p className="text-xs leading-relaxed mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                    {item.message}
                  </p>
                </div>

                {/* Action Controls */}
                <div className="flex items-center gap-2 flex-shrink-0 self-center">
                  {item.link && (
                    <span className="text-xs font-medium flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: 'var(--sp-primary)' }}>
                      View <ExternalLink className="h-3 w-3" />
                    </span>
                  )}
                  {!item.is_read && (
                    <button
                      onClick={(e) => handleMarkAsRead(item.id, null, e)}
                      title="Mark as read"
                      className="p-1.5 rounded-lg border transition-all cursor-pointer hover:bg-black/5 dark:hover:bg-white/5"
                      style={{ borderColor: 'var(--border-default)', color: 'var(--text-muted)' }}
                    >
                      <CheckCheck className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {!loading && !error && totalPages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t" style={{ borderColor: 'var(--border-default)' }}>
          <p className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
            Page <span className="font-bold text-primary">{page}</span> of <span className="font-bold text-primary">{totalPages}</span>
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1.5 rounded-lg border text-xs font-medium cursor-pointer disabled:opacity-40"
              style={{ borderColor: 'var(--border-default)', background: 'var(--bg-card)' }}
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-1.5 rounded-lg border text-xs font-medium cursor-pointer disabled:opacity-40"
              style={{ borderColor: 'var(--border-default)', background: 'var(--bg-card)' }}
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
