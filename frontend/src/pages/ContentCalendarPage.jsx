import React, { useState, useEffect, useCallback, useId } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { postsAPI } from '../lib/api';
import { useTeam } from '../context/TeamContext';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import {
  FacebookIcon,
  InstagramIcon,
  LinkedInIcon,
  TwitterIcon,
  YouTubeIcon,
  PinterestIcon,
} from '../components/icons/PlatformIcons';
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  Plus,
  Filter,
  X,
  RefreshCw,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Loader2,
  Trash2,
  CalendarOff,
  Ban,
  Layers,
  Info,
  Globe,
  FileText,
  CalendarClock,
  Eye,
} from 'lucide-react';

/* ─────────────────────────────────────────────────────────
   CONSTANTS
───────────────────────────────────────────────────────── */
const PLATFORMS = ['facebook', 'instagram', 'linkedin', 'twitter', 'youtube', 'pinterest'];
const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];
const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const PLATFORM_META = {
  facebook:  { name: 'Facebook',   icon: FacebookIcon,  color: 'text-[#1877F2]', bg: 'bg-[#1877F2]/10 dark:bg-[#1877F2]/15' },
  instagram: { name: 'Instagram',  icon: InstagramIcon, color: 'text-[#E4405F]', bg: 'bg-[#E4405F]/10 dark:bg-[#E4405F]/15' },
  linkedin:  { name: 'LinkedIn',   icon: LinkedInIcon,  color: 'text-[#0A66C2]', bg: 'bg-[#0A66C2]/10 dark:bg-[#0A66C2]/15' },
  twitter:   { name: 'X/Twitter',  icon: TwitterIcon,   color: 'text-slate-800 dark:text-slate-200', bg: 'bg-slate-200 dark:bg-slate-805' },
  youtube:   { name: 'YouTube',    icon: YouTubeIcon,   color: 'text-[#FF0000]', bg: 'bg-[#FF0000]/10 dark:bg-[#FF0000]/15' },
  pinterest: { name: 'Pinterest',  icon: PinterestIcon, color: 'text-[#BD081C]', bg: 'bg-[#BD081C]/10 dark:bg-[#BD081C]/15' },
};

const STATUS_BADGE = {
  draft:               { variant: 'neutral', label: 'Draft',         icon: FileText },
  pending_approval:    { variant: 'warning', label: 'Pending Approval', icon: Clock },
  approved:            { variant: 'success', label: 'Approved',     icon: CheckCircle2 },
  rejected:            { variant: 'danger',  label: 'Rejected',     icon: XCircle },
  scheduled:           { variant: 'blue',    label: 'Scheduled',     icon: CalendarClock },
  queued:              { variant: 'cyan',    label: 'Queued',        icon: Layers },
  publishing:          { variant: 'warning', label: 'Publishing',    icon: Loader2 },
  published:           { variant: 'success', label: 'Published',     icon: CheckCircle2 },
  partially_published: { variant: 'warning', label: 'Partial',       icon: AlertCircle },
  failed:              { variant: 'danger',  label: 'Failed',        icon: XCircle },
  cancelled:           { variant: 'neutral', label: 'Cancelled',     icon: Ban },
};

const RESULT_LABEL = {
  pending:                      'Pending',
  success:                      'Published',
  failed:                       'Failed',
  pending_external_integration: 'Awaiting Integration',
  unconfigured:                 'OAuth not configured',
};

/* ─────────────────────────────────────────────────────────
   HELPERS
───────────────────────────────────────────────────────── */
const fmtTime = (iso) => {
  if (!iso) return '';
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
  });
};

const fmtFullDate = (date) => {
  if (!date) return '';
  return new Date(date).toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const truncate = (str, n = 40) =>
  str && str.length > n ? str.slice(0, n) + '\u2026' : (str || '');

const isSameDay = (d1, d2) =>
  d1.getFullYear() === d2.getFullYear() &&
  d1.getMonth() === d2.getMonth() &&
  d1.getDate() === d2.getDate();

const getPostDate = (post) => {
  const d = post.scheduled_at || post.published_at || post.created_at;
  return new Date(d);
};

/* ─────────────────────────────────────────────────────────
   EVENT DETAIL MODAL
───────────────────────────────────────────────────────── */
const EventDetailModal = ({ post, onClose, onActionSuccess }) => {
  const navigate = useNavigate();
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState(null);

  if (!post) return null;

  const { status } = post;
  const canEdit = status === 'draft';
  const canUnschedule = status === 'scheduled';
  const canCancel = status === 'queued';
  const canDelete = status === 'draft' || status === 'cancelled';
  const hasResults = post.publish_results && Object.keys(post.publish_results).length > 0;

  const handleAction = async (actionType) => {
    setActionLoading(true);
    setActionError(null);
    try {
      if (actionType === 'delete') {
        await postsAPI.delete(post.id);
      } else if (actionType === 'cancel') {
        await postsAPI.cancel(post.id);
      } else if (actionType === 'unschedule') {
        await postsAPI.unschedule(post.id);
      }
      onActionSuccess();
      onClose();
    } catch (err) {
      const d = err.response?.data?.detail;
      setActionError(
        typeof d === 'string' ? d :
        Array.isArray(d) ? d.map((x) => x.msg).join(' \u00b7 ') :
        err.message || 'Action failed.'
      );
    } finally {
      setActionLoading(false);
    }
  };

  const statusMeta = STATUS_BADGE[status] ?? { variant: 'neutral', label: status };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <div
        className="absolute inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="sp-card relative w-full max-w-lg p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto animate-sp-fade-in-up">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 id="modal-title" className="text-base font-bold text-slate-900 dark:text-slate-100">
              {post.title || 'Untitled Post'}
            </h3>
            <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
              ID: {post.id}
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close details modal"
            className="rounded-lg p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-355 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="h-4.5 w-4.5" aria-hidden="true" />
          </button>
        </div>

        {/* Status indicator */}
        <div className="flex items-center gap-2">
          <Badge variant={statusMeta.variant} size="xs" showDot={false}>
            {statusMeta.icon && (
              <statusMeta.icon
                className={`h-3 w-3 flex-shrink-0 ${status === 'publishing' ? 'animate-spin' : ''}`}
                aria-hidden="true"
              />
            )}
            {statusMeta.label}
          </Badge>
          <span className="text-xs text-slate-400 dark:text-slate-600">
            Created: {fmtFullDate(post.created_at)}
          </span>
        </div>

        {/* Content */}
        <div className="rounded-xl bg-slate-50/50 dark:bg-slate-800/20 p-4 border border-slate-100 dark:border-slate-850">
          <p className="text-sm text-slate-805 dark:text-slate-200 leading-relaxed whitespace-pre-wrap break-words">
            {post.base_content}
          </p>
        </div>

        {/* Post Schedule / Pub detail */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          {post.scheduled_at && (
            <div className="space-y-1">
              <span className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500">
                Scheduled For
              </span>
              <span className="text-slate-700 dark:text-slate-300 font-medium">
                {fmtFullDate(post.scheduled_at)}
              </span>
            </div>
          )}
          {post.published_at && (
            <div className="space-y-1">
              <span className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500">
                Published At
              </span>
              <span className="text-slate-700 dark:text-slate-300 font-medium">
                {fmtFullDate(post.published_at)}
              </span>
            </div>
          )}
        </div>

        {/* Platforms */}
        <div>
          <span className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-2">
            Target Channels
          </span>
          <div className="flex flex-wrap gap-2">
            {post.target_platforms.map((p) => {
              const meta = PLATFORM_META[p];
              const Icon = meta?.icon;
              return (
                <div
                  key={p}
                  className={`flex items-center gap-1.5 rounded-lg border border-slate-100 dark:border-slate-805/50 px-2.5 py-1.5 text-xs font-semibold ${meta?.bg ?? 'bg-slate-100'} ${meta?.color ?? 'text-slate-700'}`}
                >
                  {Icon && <Icon className="h-3.5 w-3.5" aria-hidden="true" />}
                  <span>{meta?.name ?? p}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Publish results */}
        {hasResults && (
          <div className="space-y-2">
            <span className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500">
              Publish Execution Details
            </span>
            <div className="space-y-1.5">
              {Object.entries(post.publish_results).map(([accountId, res]) => {
                const isSuccess = res.status === 'success';
                const isUnconfigured = res.status === 'unconfigured' || res.status === 'pending_external_integration';
                return (
                  <div
                    key={accountId}
                    className={`flex items-start gap-2 rounded-lg px-2.5 py-2 text-xs border ${
                      isSuccess
                        ? 'bg-emerald-50/60 dark:bg-emerald-500/8 text-emerald-700 dark:text-emerald-400 border-emerald-200/50 dark:border-emerald-500/15'
                        : isUnconfigured
                        ? 'bg-amber-50/60 dark:bg-amber-500/8 text-amber-700 dark:text-amber-400 border-amber-200/50 dark:border-amber-500/15'
                        : 'bg-rose-50/60 dark:bg-rose-500/8 text-rose-700 dark:text-rose-400 border-rose-200/50 dark:border-rose-500/15'
                    }`}
                  >
                    <span className="font-semibold flex-shrink-0">
                      {PLATFORM_META[res.platform]?.name ?? res.platform}:
                    </span>
                    <span className="break-words">
                      {RESULT_LABEL[res.status] ?? res.status}
                      {res.error_message ? ` \u2014 ${res.error_message}` : ''}
                      {res.external_post_id ? ` (ID: ${res.external_post_id})` : ''}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Action errors */}
        {actionError && (
          <div className="flex items-start gap-2 rounded-lg border border-rose-200 dark:border-rose-500/25 bg-rose-50 dark:bg-rose-500/10 px-3 py-2 text-xs text-rose-700 dark:text-rose-400">
            <AlertCircle className="h-3.5 w-3.5 flex-shrink-0 mt-px" aria-hidden="true" />
            <span>{actionError}</span>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800/80">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={actionLoading}>
            Close
          </Button>

          {canEdit && (
            <Button
              variant="primary"
              size="sm"
              icon={FileText}
              disabled={actionLoading}
              onClick={() => {
                navigate(`/dashboard/composer?draft=${post.id}`);
                onClose();
              }}
            >
              Edit Draft
            </Button>
          )}

          {canUnschedule && (
            <Button
              variant="outline"
              size="sm"
              icon={CalendarOff}
              isLoading={actionLoading}
              onClick={() => handleAction('unschedule')}
            >
              Unschedule
            </Button>
          )}

          {canCancel && (
            <Button
              variant="danger"
              size="sm"
              icon={Ban}
              isLoading={actionLoading}
              onClick={() => handleAction('cancel')}
            >
              Cancel Post
            </Button>
          )}

          {canDelete && (
            <Button
              variant="danger"
              size="sm"
              icon={Trash2}
              isLoading={actionLoading}
              onClick={() => handleAction('delete')}
            >
              Delete
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

/* ─────────────────────────────────────────────────────────
   MAIN PAGE
───────────────────────────────────────────────────────── */
export const ContentCalendarPage = () => {
  const navigate = useNavigate();
  const { activeTeamId } = useTeam();

  // Navigation state (visible month)
  const [currentMonth, setCurrentMonth] = useState(new Date());

  // Filters
  const [statusFilter, setStatusFilter] = useState('all');
  const [platformFilter, setPlatformFilter] = useState('all');

  // Selected cell for mobile detailed list
  const [selectedDate, setSelectedDate] = useState(new Date());

  // API state
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Detail Modal post
  const [selectedPost, setSelectedPost] = useState(null);

  // 1. Build calendar cells list (always exactly 42 cells)
  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth();
  const firstDay = new Date(year, month, 1);
  // Mon = 0, Sun = 6
  const startOffset = firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1;

  const cells = [];

  // Add previous month trailing days
  const prevMonthDaysCount = new Date(year, month, 0).getDate();
  for (let i = startOffset - 1; i >= 0; i--) {
    cells.push(new Date(year, month - 1, prevMonthDaysCount - i));
  }

  // Add current month days
  const currentMonthDaysCount = new Date(year, month + 1, 0).getDate();
  for (let i = 1; i <= currentMonthDaysCount; i++) {
    cells.push(new Date(year, month, i));
  }

  // Add next month leading days
  const remaining = 42 - cells.length;
  for (let i = 1; i <= remaining; i++) {
    cells.push(new Date(year, month + 1, i));
  }

  // 2. Fetch posts covering visible calendar dates range
  const loadPosts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rangeStart = new Date(cells[0]);
      rangeStart.setHours(0, 0, 0, 0);

      const rangeEnd = new Date(cells[41]);
      rangeEnd.setHours(23, 59, 59, 999);

      const params = {
        start_date: rangeStart.toISOString(),
        end_date: rangeEnd.toISOString(),
        skip: 0,
        limit: 200, // Fetch enough to cover the month grid
      };

      if (statusFilter !== 'all') params.status = statusFilter;
      if (platformFilter !== 'all') params.platform = platformFilter;
      if (activeTeamId) params.team_id = activeTeamId;

      const res = await postsAPI.list(params);
      setPosts(res.data.items ?? []);
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(
        typeof d === 'string' ? d :
        Array.isArray(d) ? d.map((x) => x.msg).join(' \u00b7 ') :
        err.message || 'Failed to retrieve posts.'
      );
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentMonth, statusFilter, platformFilter, activeTeamId]);

  useEffect(() => {
    loadPosts();
  }, [loadPosts]);

  // Reset selected date to first day of new month when month changes
  useEffect(() => {
    setSelectedDate(new Date(year, month, 1));
  }, [currentMonth, year, month]);

  // Navigate visible month
  const handlePrevMonth = () => {
    setCurrentMonth(new Date(year, month - 1, 1));
  };
  const handleNextMonth = () => {
    setCurrentMonth(new Date(year, month + 1, 1));
  };
  const handleToday = () => {
    const today = new Date();
    setCurrentMonth(new Date(today.getFullYear(), today.getMonth(), 1));
    setSelectedDate(today);
  };

  // Group fetched posts by day (YYYY-MM-DD local format)
  const getDayKey = (date) => {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  };

  const postsByDay = {};
  posts.forEach((post) => {
    const d = getPostDate(post);
    const key = getDayKey(d);
    if (!postsByDay[key]) postsByDay[key] = [];
    postsByDay[key].push(post);
  });

  const selectedDayKey = getDayKey(selectedDate);
  const selectedDayPosts = postsByDay[selectedDayKey] ?? [];

  return (
    <>
      <div className="space-y-6 animate-sp-fade-in-up">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl sm:text-2xl font-extrabold tracking-tight text-slate-900 dark:text-slate-50 font-heading flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-violet-600 to-blue-500 text-white shadow-sm shadow-violet-500/25">
                <CalendarIcon className="h-4 w-4" aria-hidden="true" />
              </span>
              Content Calendar
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Visual planner for scheduling and tracking social campaigns.
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              type="button"
              onClick={loadPosts}
              aria-label="Refresh calendar data"
              title="Refresh"
              className="flex items-center justify-center h-9 w-9 rounded-xl border border-slate-200/80 dark:border-slate-800/50 bg-white dark:bg-[#0D1426] text-slate-500 dark:text-slate-400 hover:text-violet-600 dark:hover:text-violet-400 hover:border-violet-500/40 transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
            </button>
            <Link to="/dashboard/composer">
              <Button variant="primary" size="sm" icon={Plus}>
                Create Post
              </Button>
            </Link>
          </div>
        </div>

        {/* Filters and Month Navigation Toolbar */}
        <div className="sp-card p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
          
          {/* Navigation Controls */}
          <div className="flex items-center gap-2">
            <div className="flex items-center rounded-xl border border-slate-200/80 dark:border-slate-800/50 bg-slate-50/50 dark:bg-slate-800/10 p-0.5">
              <button
                type="button"
                onClick={handlePrevMonth}
                aria-label="Previous month"
                className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-200/55 dark:hover:bg-slate-800/60 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={handleNextMonth}
                aria-label="Next month"
                className="p-1.5 rounded-lg text-slate-500 hover:text-slate-805 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-200/55 dark:hover:bg-slate-800/60 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
            <button
              type="button"
              onClick={handleToday}
              className="px-3 py-1.5 text-xs font-bold rounded-xl border border-slate-200/80 dark:border-slate-800/50 bg-white dark:bg-slate-800/20 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/60 transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500"
            >
              Today
            </button>
            <h2 className="text-sm font-extrabold text-slate-900 dark:text-slate-50 tracking-tight pl-2">
              {MONTH_NAMES[month]} {year}
            </h2>
          </div>

          {/* Filters Selectors */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <label htmlFor="calendar-status-filter" className="text-[10px] font-bold uppercase tracking-widest text-slate-450 dark:text-slate-500">
                Status:
              </label>
              <select
                id="calendar-status-filter"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="rounded-xl border border-slate-200/80 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/30 px-3 py-1.5 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/20 cursor-pointer"
              >
                <option value="all">All</option>
                <option value="draft">Draft</option>
                <option value="scheduled">Scheduled</option>
                <option value="queued">Queued</option>
                <option value="publishing">Publishing</option>
                <option value="published">Published</option>
                <option value="failed">Failed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label htmlFor="calendar-platform-filter" className="text-[10px] font-bold uppercase tracking-widest text-slate-450 dark:text-slate-500">
                Platform:
              </label>
              <select
                id="calendar-platform-filter"
                value={platformFilter}
                onChange={(e) => setPlatformFilter(e.target.value)}
                className="rounded-xl border border-slate-200/80 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/30 px-3 py-1.5 text-xs text-slate-850 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/20 cursor-pointer"
              >
                <option value="all">All Platforms</option>
                {PLATFORMS.map((p) => (
                  <option key={p} value={p}>{PLATFORM_META[p]?.name ?? p}</option>
                ))}
              </select>
            </div>

            {(statusFilter !== 'all' || platformFilter !== 'all') && (
              <button
                type="button"
                onClick={() => { setStatusFilter('all'); setPlatformFilter('all'); }}
                className="flex items-center gap-1 text-xs font-semibold text-rose-600 dark:text-rose-450 hover:underline cursor-pointer px-1 py-1 rounded"
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
                Clear
              </button>
            )}
          </div>
        </div>

        {/* API Error Box */}
        {error && (
          <div role="alert" className="flex items-start gap-3 rounded-2xl border border-rose-200/80 dark:border-rose-500/25 bg-rose-50 dark:bg-rose-500/10 p-5 text-sm text-rose-800 dark:text-rose-300">
            <AlertCircle className="h-5 w-5 flex-shrink-0 mt-px" aria-hidden="true" />
            <div className="flex-1">
              <p className="font-bold">Failed to sync calendar</p>
              <p className="text-xs mt-0.5 opacity-80">{error}</p>
            </div>
            <Button variant="ghost" size="sm" icon={RefreshCw} onClick={loadPosts}>
              Retry
            </Button>
          </div>
        )}

        {/* Two Layout Columns: Calendar Grid + Day Details Panel */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-6 items-start">
          
          {/* Calendar Month Grid */}
          <div className="sp-card p-4 shadow-sm overflow-hidden">
            {/* Weekdays Row */}
            <div className="grid grid-cols-7 gap-1 text-center mb-2">
              {WEEKDAYS.map((wd) => (
                <div key={wd} className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 py-1">
                  {wd}
                </div>
              ))}
            </div>

            {/* 42-cell Calendar Grid */}
            <div
              className="grid grid-cols-7 gap-1 border-t border-slate-100 dark:border-slate-800/80 pt-1"
              role="grid"
              aria-label={`Calendar grid for ${MONTH_NAMES[month]} ${year}`}
              aria-busy={loading}
            >
              {cells.map((cellDate, idx) => {
                const isCurrentMonth = cellDate.getMonth() === month;
                const isToday = isSameDay(cellDate, new Date());
                const isSelected = isSameDay(cellDate, selectedDate);
                const dayKey = getDayKey(cellDate);
                const dayPosts = postsByDay[dayKey] ?? [];

                return (
                  <button
                    key={idx}
                    role="gridcell"
                    type="button"
                    aria-selected={isSelected}
                    onClick={() => setSelectedDate(cellDate)}
                    className={`relative min-h-[72px] md:min-h-[105px] p-1.5 flex flex-col items-stretch text-left rounded-xl transition-all duration-150 border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 cursor-pointer ${
                      isSelected
                        ? 'bg-violet-500/5 border-violet-500 dark:border-violet-400 shadow-sm'
                        : isToday
                        ? 'border-violet-500/30 bg-slate-50/50 dark:bg-slate-800/10 dark:border-slate-700/80 hover:border-slate-350 dark:hover:border-slate-700'
                        : 'border-slate-100 dark:border-slate-800/50 hover:bg-slate-50/50 dark:hover:bg-slate-800/20'
                    }`}
                  >
                    {/* Day number & indicators */}
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-xs font-bold ${
                        isToday
                          ? 'flex h-5 w-5 items-center justify-center rounded-full bg-gradient-to-tr from-violet-650 to-blue-500 text-white shadow-sm'
                          : isCurrentMonth
                          ? 'text-slate-800 dark:text-slate-200'
                          : 'text-slate-300 dark:text-slate-650'
                      }`}>
                        {cellDate.getDate()}
                      </span>

                      {/* Small visual counter for mobile view */}
                      {dayPosts.length > 0 && (
                        <span className="flex h-1.5 w-1.5 rounded-full bg-violet-500 md:hidden" />
                      )}
                    </div>

                    {/* Event block indicators — Only visible on Desktop (md and above) */}
                    <div className="hidden md:flex flex-col gap-1 overflow-y-hidden flex-1 select-none">
                      {dayPosts.slice(0, 3).map((post) => {
                        const plat = post.target_platforms?.[0];
                        const platMeta = PLATFORM_META[plat];
                        const PlatIcon = platMeta?.icon;

                        return (
                          <div
                            key={post.id}
                            title={`${platMeta?.name ?? 'Post'}: ${post.title || truncate(post.base_content, 30)}`}
                            className={`px-1.5 py-0.5 rounded text-[9px] font-semibold flex items-center gap-1 truncate ${
                              post.status === 'published'
                                ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-450 border border-emerald-500/15'
                                : post.status === 'failed'
                                ? 'bg-rose-500/10 text-rose-700 dark:text-rose-450 border border-rose-500/15'
                                : post.status === 'pending_approval'
                                ? 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/15'
                                : 'bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 border border-slate-200/50 dark:border-slate-700/60'
                            }`}
                          >
                            {PlatIcon && (
                              <span className={platMeta.color}>
                                <PlatIcon className="h-2.5 w-2.5" />
                              </span>
                            )}
                            <span className="truncate flex-1">
                              {post.title || truncate(post.base_content, 20)}
                            </span>
                          </div>
                        );
                      })}
                      {dayPosts.length > 3 && (
                        <span className="text-[8px] font-bold text-slate-400 dark:text-slate-500 pl-1">
                          +{dayPosts.length - 3} more
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Selected Day Posts Timeline View Panel */}
          <aside
            className="sp-card p-5 space-y-4 shadow-sm"
            aria-label="Selected day schedule list"
          >
            <div>
              <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500">
                Schedule for
              </h3>
              <p className="text-sm font-extrabold text-slate-900 dark:text-slate-50 mt-1 font-heading">
                {selectedDate.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' })}
              </p>
            </div>

            {loading ? (
              <div className="flex items-center gap-2 py-8 text-xs text-slate-400 dark:text-slate-500">
                <Loader2 className="h-4 w-4 animate-spin text-violet-500" aria-hidden="true" />
                Syncing items…
              </div>
            ) : selectedDayPosts.length === 0 ? (
              <div className="py-12 text-center space-y-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-50 dark:bg-slate-800 mx-auto text-slate-355 dark:text-slate-655">
                  <CalendarClock className="h-5 w-5" aria-hidden="true" />
                </div>
                <div className="space-y-1">
                  <p className="text-xs font-bold text-slate-805 dark:text-slate-300">
                    No scheduled items
                  </p>
                  <p className="text-[10px] text-slate-450 dark:text-slate-500 max-w-[180px] mx-auto leading-relaxed">
                    Nothing is scheduled for publishing on this calendar date.
                  </p>
                </div>
                <Link to="/dashboard/composer">
                  <Button variant="ghost" size="xs" icon={Plus}>
                    Plan a Post
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
                {selectedDayPosts.map((post) => {
                  const sMeta = STATUS_BADGE[post.status] ?? { variant: 'neutral', label: post.status };
                  const mainPlatform = post.target_platforms?.[0];
                  const plMeta = PLATFORM_META[mainPlatform];
                  const PlatIcon = plMeta?.icon;

                  return (
                    <div
                      key={post.id}
                      className="group rounded-xl border border-slate-150 dark:border-slate-805/50 p-3 hover:border-slate-300/80 dark:hover:border-slate-700/60 hover:bg-slate-50/50 dark:hover:bg-slate-800/10 transition-all cursor-pointer text-left"
                      onClick={() => setSelectedPost(post)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => { if (e.key === 'Enter') setSelectedPost(post); }}
                      aria-label={`View details for post: ${post.title || truncate(post.base_content, 30)}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="text-[10px] font-bold text-slate-455 dark:text-slate-500 flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {post.scheduled_at ? fmtTime(post.scheduled_at) : 'Draft'}
                        </span>
                        <Badge variant={sMeta.variant} size="xs" showDot={false}>
                          {sMeta.label}
                        </Badge>
                      </div>

                      <p className="text-xs text-slate-800 dark:text-slate-200 font-semibold mt-2 break-words leading-relaxed">
                        {truncate(post.base_content, 80)}
                      </p>

                      <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-slate-100 dark:border-slate-850">
                        {/* Selected channel icon */}
                        {PlatIcon && (
                          <div className={`flex h-5 w-5 items-center justify-center rounded-full ${plMeta.bg} ${plMeta.color}`}>
                            <PlatIcon className="h-2.5 w-2.5" />
                          </div>
                        )}
                        <span className="text-[10px] font-bold text-violet-650 dark:text-violet-400 group-hover:underline flex items-center gap-0.5">
                          Inspect detail &rarr;
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </aside>
        </div>

      </div>

      {/* Post Details Modal */}
      {selectedPost && (
        <EventDetailModal
          post={selectedPost}
          onClose={() => setSelectedPost(null)}
          onActionSuccess={loadPosts}
        />
      )}
    </>
  );
};
