import React, { useState, useEffect, useCallback, useId } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { postsAPI, teamsAPI } from '../lib/api';
import { useAuth } from '../context/AuthContext';
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
  Send,
  FileText,
  Clock,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Loader2,
  Trash2,
  CalendarOff,
  ImageIcon,
  ChevronLeft,
  ChevronRight,
  Filter,
  X,
  RefreshCw,
  Inbox,
  CalendarClock,
  Globe,
  Info,
  Ban,
  Layers,
} from 'lucide-react';

/* ─────────────────────────────────────────────────────────
   CONSTANTS — exact enum values from backend
───────────────────────────────────────────────────────── */
const PLATFORMS = ['facebook', 'instagram', 'linkedin', 'twitter', 'youtube', 'pinterest'];
const PAGE_LIMIT = 10;

const PLATFORM_META = {
  facebook:  { name: 'Facebook',   icon: FacebookIcon,  color: 'text-[#1877F2]' },
  instagram: { name: 'Instagram',  icon: InstagramIcon, color: 'text-[#E4405F]' },
  linkedin:  { name: 'LinkedIn',   icon: LinkedInIcon,  color: 'text-[#0A66C2]' },
  twitter:   { name: 'X/Twitter',  icon: TwitterIcon,   color: 'text-slate-800 dark:text-slate-200' },
  youtube:   { name: 'YouTube',    icon: YouTubeIcon,   color: 'text-[#FF0000]' },
  pinterest: { name: 'Pinterest',  icon: PinterestIcon, color: 'text-[#BD081C]' },
};

// backend PostStatus enum values
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

// backend PublishResultStatus enum values
const RESULT_LABEL = {
  pending:                      'Pending',
  success:                      'Published',
  failed:                       'Failed',
  pending_external_integration: 'Awaiting Integration',
  unconfigured:                 'OAuth not configured',
};

const STATUS_TABS = [
  { key: 'all',                 label: 'All' },
  { key: 'draft',               label: 'Drafts' },
  { key: 'pending_approval',    label: 'Pending' },
  { key: 'approved',            label: 'Approved' },
  { key: 'rejected',            label: 'Rejected' },
  { key: 'scheduled',           label: 'Scheduled' },
  { key: 'queued',              label: 'Queued' },
  { key: 'published',           label: 'Published' },
  { key: 'failed',              label: 'Failed' },
];

/* ─────────────────────────────────────────────────────────
   HELPERS
───────────────────────────────────────────────────────── */
const fmtDate = (iso) => {
  if (!iso) return null;
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
};

const truncate = (str, n = 140) =>
  str && str.length > n ? str.slice(0, n) + '\u2026' : (str || '');

/* ─────────────────────────────────────────────────────────
   STATUS BADGE
───────────────────────────────────────────────────────── */
const PostStatusBadge = ({ status }) => {
  const meta = STATUS_BADGE[status] ?? { variant: 'neutral', label: status };
  const Icon = meta.icon;
  return (
    <Badge variant={meta.variant} size="xs" showDot={false}>
      {Icon && (
        <Icon
          className={`h-3 w-3 flex-shrink-0 ${status === 'publishing' ? 'animate-spin' : ''}`}
          aria-hidden="true"
        />
      )}
      {meta.label}
    </Badge>
  );
};

/* ─────────────────────────────────────────────────────────
   PLATFORM PILLS
───────────────────────────────────────────────────────── */
const PlatformPills = ({ platforms }) => {
  if (!platforms || platforms.length === 0) {
    return <span className="text-xs text-slate-400 dark:text-slate-600">No platform</span>;
  }
  return (
    <div className="flex flex-wrap gap-1">
      {platforms.slice(0, 4).map((p) => {
        const meta = PLATFORM_META[p];
        const Icon = meta?.icon;
        return (
          <span
            key={p}
            title={meta?.name ?? p}
            className={`flex h-5 w-5 items-center justify-center rounded-full bg-slate-100 dark:bg-slate-800 ${meta?.color ?? 'text-slate-400'}`}
          >
            {Icon ? (
              <Icon className="h-3 w-3" aria-label={meta?.name ?? p} />
            ) : (
              p[0].toUpperCase()
            )}
          </span>
        );
      })}
      {platforms.length > 4 && (
        <span className="text-xs text-slate-400 dark:text-slate-500 self-center">
          +{platforms.length - 4}
        </span>
      )}
    </div>
  );
};

/* ─────────────────────────────────────────────────────────
   SKELETON
───────────────────────────────────────────────────────── */
const SkeletonCard = () => (
  <div className="sp-card flex items-start gap-4 p-4 animate-pulse">
    <div className="flex-1 space-y-2.5 py-1">
      <div className="h-3.5 bg-slate-200 dark:bg-slate-800 rounded w-3/4" />
      <div className="h-3 bg-slate-100 dark:bg-slate-800/60 rounded w-full" />
      <div className="h-3 bg-slate-100 dark:bg-slate-800/60 rounded w-1/2" />
      <div className="flex gap-2 pt-1">
        <div className="h-4 w-4 bg-slate-200 dark:bg-slate-800 rounded-full" />
        <div className="h-4 w-4 bg-slate-200 dark:bg-slate-800 rounded-full" />
      </div>
    </div>
    <div className="flex flex-col items-end gap-2">
      <div className="h-5 w-16 bg-slate-200 dark:bg-slate-800 rounded-full" />
      <div className="h-7 w-20 bg-slate-100 dark:bg-slate-800/60 rounded-lg" />
    </div>
  </div>
);

/* ─────────────────────────────────────────────────────────
   EMPTY STATE
───────────────────────────────────────────────────────── */
const EmptyState = ({ statusFilter, platformFilter, hasDateFilter, onClearFilters }) => {
  const hasFilters = statusFilter !== 'all' || platformFilter !== 'all' || hasDateFilter;

  const titles = {
    all:                'No posts yet',
    draft:              'No drafts',
    scheduled:          'No scheduled posts',
    queued:             'No queued posts',
    published:          'No published posts',
    partially_published:'No partially published posts',
    failed:             'No failed posts',
    cancelled:          'No cancelled posts',
  };

  const hints = {
    all:                'Create your first post using the Post Composer.',
    draft:              'Posts saved as drafts will appear here.',
    scheduled:          'Posts scheduled for future publishing will appear here.',
    queued:             'Posts queued for immediate publishing will appear here.',
    published:          'Successfully published posts will appear here.',
    partially_published:'Posts that partially published will appear here.',
    failed:             'Posts that failed to publish will appear here.',
    cancelled:          'Cancelled posts will appear here.',
  };

  return (
    <div className="flex flex-col items-center justify-center py-20 text-center gap-4">
      <div className="flex h-16 w-16 items-center justify-center rounded-3xl bg-slate-100 dark:bg-slate-800 text-slate-300 dark:text-slate-600">
        {hasFilters
          ? <Filter className="h-7 w-7" aria-hidden="true" />
          : <Inbox className="h-7 w-7" aria-hidden="true" />
        }
      </div>
      <div>
        <p className="text-sm font-bold text-slate-800 dark:text-slate-200">
          {hasFilters ? 'No posts match your filters' : (titles[statusFilter] ?? 'No posts')}
        </p>
        <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 max-w-xs mx-auto">
          {hasFilters
            ? 'Try clearing the filters to see all posts.'
            : (hints[statusFilter] ?? `Posts with "${statusFilter}" status will appear here.`)}
        </p>
      </div>
      {hasFilters ? (
        <Button variant="outline" size="sm" icon={X} onClick={onClearFilters}>
          Clear Filters
        </Button>
      ) : (
        <Link to="/dashboard/composer">
          <Button variant="primary" size="sm" icon={Send}>
            Create New Post
          </Button>
        </Link>
      )}
    </div>
  );
};

/* ─────────────────────────────────────────────────────────
   PUBLISH RESULTS DETAIL
───────────────────────────────────────────────────────── */
const PublishResultsDetail = ({ publishResults }) => {
  if (!publishResults || Object.keys(publishResults).length === 0) return null;
  return (
    <div className="mt-2 space-y-1.5">
      {Object.entries(publishResults).map(([accountId, result]) => {
        const isSuccess = result.status === 'success';
        const isUnconfigured =
          result.status === 'unconfigured' ||
          result.status === 'pending_external_integration';
        return (
          <div
            key={accountId}
            className={`flex items-start gap-2 rounded-lg px-2.5 py-1.5 text-[11px] border ${
              isSuccess
                ? 'bg-emerald-50/60 dark:bg-emerald-500/8 text-emerald-700 dark:text-emerald-400 border-emerald-200/60 dark:border-emerald-500/15'
                : isUnconfigured
                ? 'bg-amber-50/60 dark:bg-amber-500/8 text-amber-700 dark:text-amber-400 border-amber-200/60 dark:border-amber-500/15'
                : 'bg-rose-50/60 dark:bg-rose-500/8 text-rose-700 dark:text-rose-400 border-rose-200/60 dark:border-rose-500/15'
            }`}
          >
            <span className="font-semibold flex-shrink-0">
              {PLATFORM_META[result.platform]?.name ?? result.platform}:
            </span>
            <span className="break-words">
              {RESULT_LABEL[result.status] ?? result.status}
              {result.error_message ? ` \u2014 ${result.error_message}` : ''}
              {result.external_post_id ? ` (ID: ${result.external_post_id})` : ''}
            </span>
          </div>
        );
      })}
    </div>
  );
};

/* ─────────────────────────────────────────────────────────
   POST CARD
───────────────────────────────────────────────────────── */
const PostCard = ({ post, onDelete, onCancel, onUnschedule, onApprove, onReject, isApprover }) => {
  const [expanded, setExpanded] = useState(false);
  const navigate = useNavigate();

  const { status } = post;
  const hasMedia = post.media_attachments && post.media_attachments.length > 0;
  const hasResults =
    post.publish_results && Object.keys(post.publish_results).length > 0;

  const canEdit      = status === 'draft' || status === 'rejected';
  const canUnschedule = status === 'scheduled';
  const canCancel    = status === 'queued';
  const canDelete    = status === 'draft' || status === 'cancelled';
  const canExpand    = hasResults;
  const showTaskId   = (status === 'queued' || status === 'publishing') && post.celery_task_id;

  return (
    <article
      className="sp-card p-4 sm:p-5 transition-all duration-200"
      aria-label={`Post: ${post.title || truncate(post.base_content, 60)}`}
    >
      <div className="flex flex-col sm:flex-row sm:items-start gap-3">

        {/* ── Content column ── */}
        <div className="flex-1 min-w-0">
          {post.title && (
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-600 mb-1">
              {post.title}
            </p>
          )}

          <p className="text-sm text-slate-800 dark:text-slate-200 leading-relaxed break-words">
            {truncate(post.base_content)}
          </p>

          {/* Meta row */}
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 mt-2.5">
            <PlatformPills platforms={post.target_platforms} />

            {hasMedia && (
              <span className="flex items-center gap-1 text-[11px] text-slate-400 dark:text-slate-500">
                <ImageIcon className="h-3 w-3" aria-hidden="true" />
                {post.media_attachments.length} media
              </span>
            )}

            {post.status === 'rejected' && post.rejection_reason && (
              <div className="mt-2.5 w-full rounded-xl border border-rose-200/80 bg-rose-500/5 px-3 py-2 text-xs text-rose-600 dark:text-rose-400">
                <span className="font-bold">Rejection feedback: </span>
                {post.rejection_reason}
              </div>
            )}

            {post.scheduled_at && (
              <span className="flex items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400">
                <CalendarClock className="h-3 w-3" aria-hidden="true" />
                Scheduled: {fmtDate(post.scheduled_at)}
              </span>
            )}

            {post.published_at && (
              <span className="flex items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400">
                <Globe className="h-3 w-3" aria-hidden="true" />
                Published: {fmtDate(post.published_at)}
              </span>
            )}

            <span className="flex items-center gap-1 text-[11px] text-slate-400 dark:text-slate-600 ml-auto">
              <Clock className="h-3 w-3" aria-hidden="true" />
              {fmtDate(post.created_at)}
            </span>
          </div>

          {/* Task ID pill for queued/publishing */}
          {showTaskId && (
            <p className="mt-1.5 text-[10px] font-mono text-slate-400 dark:text-slate-600" title={post.celery_task_id}>
              Task: {post.celery_task_id.slice(0, 8)}&hellip;
            </p>
          )}

          {/* Expandable publish results */}
          {canExpand && (
            <div className="mt-2">
              <button
                type="button"
                onClick={() => setExpanded((v) => !v)}
                aria-expanded={expanded}
                aria-controls={`results-${post.id}`}
                className="flex items-center gap-1 text-[11px] font-semibold text-violet-600 dark:text-violet-400 hover:underline cursor-pointer focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-violet-500 rounded"
              >
                <Info className="h-3 w-3" aria-hidden="true" />
                {expanded ? 'Hide' : 'Show'} publish details
              </button>
              {expanded && (
                <div id={`results-${post.id}`}>
                  <PublishResultsDetail publishResults={post.publish_results} />
                </div>
              )}
            </div>
          )}
        </div>

        {/* ── Status + actions column ── */}
        <div className="flex sm:flex-col items-center sm:items-end gap-2 flex-shrink-0">
          <PostStatusBadge status={status} />

          <div className="flex items-center gap-1.5 mt-0 sm:mt-2">
            {canEdit && (
              <button
                type="button"
                onClick={() => navigate(`/dashboard/composer?draft=${post.id}`)}
                title="Edit draft (opens Composer)"
                aria-label="Edit draft in Composer"
                className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-violet-700 dark:text-violet-400 bg-violet-500/8 dark:bg-violet-500/12 hover:bg-violet-500/15 dark:hover:bg-violet-500/20 transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500"
              >
                <FileText className="h-3.5 w-3.5" aria-hidden="true" />
                <span className="hidden sm:inline">Edit</span>
              </button>
            )}

            {canUnschedule && (
              <button
                type="button"
                onClick={() => onUnschedule(post.id)}
                title="Revert to draft"
                aria-label="Unschedule — revert to draft"
                className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-amber-700 dark:text-amber-400 bg-amber-500/8 dark:bg-amber-500/12 hover:bg-amber-500/15 dark:hover:bg-amber-500/20 transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
              >
                <CalendarOff className="h-3.5 w-3.5" aria-hidden="true" />
                <span className="hidden sm:inline">Unschedule</span>
              </button>
            )}

            {canCancel && (
              <button
                type="button"
                onClick={() => onCancel(post.id)}
                title="Cancel queued post"
                aria-label="Cancel queued post"
                className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-rose-700 dark:text-rose-400 bg-rose-500/8 dark:bg-rose-500/12 hover:bg-rose-500/15 dark:hover:bg-rose-500/20 transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500"
              >
                <Ban className="h-3.5 w-3.5" aria-hidden="true" />
                <span className="hidden sm:inline">Cancel</span>
              </button>
            )}

            {canDelete && (
              <button
                type="button"
                onClick={() => onDelete(post.id)}
                title="Delete permanently"
                aria-label="Delete post permanently"
                className="flex items-center justify-center rounded-lg p-1.5 text-slate-400 dark:text-slate-600 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-500"
              >
                <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            )}

            {status === 'pending_approval' && (
              isApprover ? (
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => onApprove(post.id)}
                    title="Approve post"
                    className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-emerald-700 dark:text-emerald-400 bg-emerald-500/8 dark:bg-emerald-500/12 hover:bg-emerald-500/20 transition-colors cursor-pointer"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Approve</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => onReject(post.id)}
                    title="Reject post"
                    className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-semibold text-rose-700 dark:text-rose-400 bg-rose-500/8 dark:bg-rose-500/12 hover:bg-rose-500/20 transition-colors cursor-pointer"
                  >
                    <XCircle className="h-3.5 w-3.5" />
                    <span>Reject</span>
                  </button>
                </div>
              ) : (
                <span className="text-xs text-slate-400 dark:text-slate-500 italic">
                  Awaiting approval
                </span>
              )
            )}
          </div>
        </div>
      </div>
    </article>
  );
};

/* ─────────────────────────────────────────────────────────
   CONFIRM MODAL
───────────────────────────────────────────────────────── */
const ConfirmModal = ({ open, action, onConfirm, onCancel, isLoading, error }) => {
  if (!open) return null;

  const cfg = {
    delete:     { title: 'Delete Post?',     body: 'This permanently removes the post. Cannot be undone.', btnLabel: 'Delete', btnVariant: 'danger' },
    cancel:     { title: 'Cancel Post?',     body: 'The queued post will be cancelled and the Celery task revoked.', btnLabel: 'Cancel Post', btnVariant: 'outline' },
    unschedule: { title: 'Unschedule Post?', body: 'The post reverts to Draft and the scheduled Celery task is cancelled.', btnLabel: 'Unschedule', btnVariant: 'outline' },
  };
  const { title, body, btnLabel, btnVariant } = cfg[action] ?? { title: 'Confirm', body: '', btnLabel: 'Confirm', btnVariant: 'primary' };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
    >
      <div
        className="absolute inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-sm"
        onClick={onCancel}
        aria-hidden="true"
      />
      <div className="sp-card relative w-full max-w-sm p-6 shadow-2xl">
        <h3 id="confirm-title" className="text-sm font-bold text-slate-900 dark:text-slate-100 mb-2">
          {title}
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">{body}</p>

        {error && (
          <div className="mb-4 flex items-start gap-2 rounded-lg border border-rose-200 dark:border-rose-500/25 bg-rose-50 dark:bg-rose-500/10 px-3 py-2 text-xs text-rose-700 dark:text-rose-400">
            <AlertCircle className="h-3.5 w-3.5 flex-shrink-0 mt-px" aria-hidden="true" />
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onCancel} disabled={isLoading}>
            Go Back
          </Button>
          <Button variant={btnVariant} size="sm" isLoading={isLoading} onClick={onConfirm}>
            {btnLabel}
          </Button>
        </div>
      </div>
    </div>
  );
};

/* ─────────────────────────────────────────────────────────
   MAIN PAGE COMPONENT
───────────────────────────────────────────────────────── */
export const PostsPage = () => {
  const startDateId = useId();
  const endDateId   = useId();

  // Filters
  const [statusFilter,   setStatusFilter]   = useState('all');
  const [platformFilter, setPlatformFilter] = useState('all');
  const [startDate, setStartDate] = useState('');
  const [endDate,   setEndDate]   = useState('');

  // Pagination
  const [page, setPage] = useState(0);

  // Data
  const [posts,   setPosts]   = useState([]);
  const [total,   setTotal]   = useState(0);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  const { user } = useAuth();
  const { activeTeamId, activeTeam } = useTeam();
  const [userRole, setUserRole] = useState(null);

  useEffect(() => {
    if (activeTeamId) {
      teamsAPI.listMembers(activeTeamId)
        .then((res) => {
          const me = res.data.find(m => m.user_id === user.id);
          if (me) {
            setUserRole(me.role);
          }
        })
        .catch((err) => console.error('Error fetching workspace role:', err));
    } else {
      setUserRole(null);
    }
  }, [activeTeamId, user]);

  const isApprover = user?.role === 'administrator' ||
    activeTeam?.owner_id === user?.id ||
    userRole === 'administrator';

  // Confirm modal
  const [confirmModal,   setConfirmModal]   = useState(null); // { postId, action }
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [confirmError,   setConfirmError]   = useState(null);

  // Reject modal
  const [rejectModal, setRejectModal] = useState(null); // { postId, reason }

  // Banner for action errors
  const [actionBannerError, setActionBannerError] = useState(null);

  const hasDateFilter = Boolean(startDate || endDate);

  /* ─── Fetch ─── */
  const fetchPosts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { skip: page * PAGE_LIMIT, limit: PAGE_LIMIT };
      if (statusFilter !== 'all') params.status = statusFilter;
      if (platformFilter !== 'all') params.platform = platformFilter;
      if (activeTeamId) params.team_id = activeTeamId;
      if (startDate) params.start_date = new Date(startDate).toISOString();
      if (endDate) {
        const ed = new Date(endDate);
        ed.setHours(23, 59, 59, 999);
        params.end_date = ed.toISOString();
      }
      const res = await postsAPI.list(params);
      setPosts(res.data.items ?? []);
      setTotal(res.data.total ?? 0);
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(
        typeof d === 'string' ? d :
        Array.isArray(d) ? d.map((x) => x.msg).join(' \u00b7 ') :
        err.message || 'Failed to load posts.'
      );
    } finally {
      setLoading(false);
    }
  }, [statusFilter, platformFilter, startDate, endDate, page, activeTeamId]);

  useEffect(() => { fetchPosts(); }, [fetchPosts]);

  // Reset to page 0 when filters change
  useEffect(() => { setPage(0); }, [statusFilter, platformFilter, startDate, endDate]);

  /* ─── Filters ─── */
  const clearFilters = () => {
    setStatusFilter('all');
    setPlatformFilter('all');
    setStartDate('');
    setEndDate('');
    setPage(0);
  };

  /* ─── Modal ─── */
  const openConfirm  = (postId, action) => { setConfirmError(null); setConfirmModal({ postId, action }); };
  const closeConfirm = () => { setConfirmModal(null); setConfirmError(null); };

  const executeAction = async () => {
    if (!confirmModal) return;
    const { postId, action } = confirmModal;
    setConfirmLoading(true);
    setConfirmError(null);
    try {
      if (action === 'delete')     await postsAPI.delete(postId);
      else if (action === 'cancel')     await postsAPI.cancel(postId);
      else if (action === 'unschedule') await postsAPI.unschedule(postId);
      closeConfirm();
      fetchPosts();
    } catch (err) {
      const d = err.response?.data?.detail;
      setConfirmError(
        typeof d === 'string' ? d :
        Array.isArray(d) ? d.map((x) => x.msg).join(' \u00b7 ') :
        err.message || 'Action failed.'
      );
    } finally {
      setConfirmLoading(false);
    }
  };

  const handleApprovePost = async (postId) => {
    try {
      setActionBannerError(null);
      await postsAPI.approve(postId);
      fetchPosts();
    } catch (err) {
      const d = err.response?.data?.detail;
      setActionBannerError(
        typeof d === 'string' ? d : 'Failed to approve post.'
      );
    }
  };

  const handleRejectPost = async (postId, reason) => {
    try {
      setActionBannerError(null);
      await postsAPI.reject(postId, reason);
      setRejectModal(null);
      fetchPosts();
    } catch (err) {
      const d = err.response?.data?.detail;
      setActionBannerError(
        typeof d === 'string' ? d : 'Failed to reject post.'
      );
    }
  };

  /* ─── Pagination ─── */
  const totalPages = Math.max(1, Math.ceil(total / PAGE_LIMIT));
  const canPrev = page > 0;
  const canNext = page < totalPages - 1;

  /* ─────────────────────────────────────────────────────
     RENDER
  ───────────────────────────────────────────────────── */
  return (
    <>
      <div className="space-y-6 animate-sp-fade-in-up">

        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl sm:text-2xl font-extrabold tracking-tight text-slate-900 dark:text-slate-50 font-heading flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-violet-600 to-blue-500 text-white shadow-sm shadow-violet-500/25">
                <FileText className="h-4 w-4" aria-hidden="true" />
              </span>
              My Posts
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Manage drafts, scheduled, and published posts across all platforms.
            </p>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              type="button"
              onClick={fetchPosts}
              aria-label="Refresh posts list"
              title="Refresh"
              className="flex items-center justify-center h-9 w-9 rounded-xl border border-slate-200/80 dark:border-slate-800/50 bg-white dark:bg-[#0D1426] text-slate-500 dark:text-slate-400 hover:text-violet-600 dark:hover:text-violet-400 hover:border-violet-500/40 transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
            </button>
            <Link to="/dashboard/composer">
              <Button variant="primary" size="sm" icon={Send}>
                New Post
              </Button>
            </Link>
          </div>
        </div>

        {/* Action banner error */}
        {actionBannerError && (
          <div role="alert" className="flex items-start gap-3 rounded-xl border border-rose-200 dark:border-rose-500/25 bg-rose-50 dark:bg-rose-500/10 px-4 py-3 text-sm text-rose-800 dark:text-rose-300">
            <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" aria-hidden="true" />
            <span>{actionBannerError}</span>
            <button onClick={() => setActionBannerError(null)} aria-label="Dismiss" className="ml-auto cursor-pointer">
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        )}

        {/* Filters panel */}
        <div className="sp-card p-4 space-y-4">

          {/* Status tabs */}
          <div role="tablist" aria-label="Filter by post status" className="flex flex-wrap gap-1">
            {STATUS_TABS.map((tab) => {
              const isActive = statusFilter === tab.key;
              return (
                <button
                  key={tab.key}
                  role="tab"
                  aria-selected={isActive}
                  type="button"
                  onClick={() => setStatusFilter(tab.key)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all duration-150 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 ${
                    isActive
                      ? 'bg-violet-500/10 dark:bg-violet-500/15 text-violet-700 dark:text-violet-300 border border-violet-500/20 dark:border-violet-500/25'
                      : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/50 border border-transparent'
                  }`}
                >
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Platform + date filters */}
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[160px]">
              <label htmlFor="posts-platform-filter" className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-1">
                Platform
              </label>
              <select
                id="posts-platform-filter"
                value={platformFilter}
                onChange={(e) => setPlatformFilter(e.target.value)}
                className="w-full rounded-xl border border-slate-200/80 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/30 px-3 py-2 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500/50 transition-all [color-scheme:light] dark:[color-scheme:dark] cursor-pointer"
              >
                <option value="all">All Platforms</option>
                {PLATFORMS.map((p) => (
                  <option key={p} value={p}>{PLATFORM_META[p]?.name ?? p}</option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor={startDateId} className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-1">
                From
              </label>
              <input
                id={startDateId}
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="rounded-xl border border-slate-200/80 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/30 px-3 py-2 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/20 transition-all [color-scheme:light] dark:[color-scheme:dark]"
              />
            </div>

            <div>
              <label htmlFor={endDateId} className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-1">
                To
              </label>
              <input
                id={endDateId}
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="rounded-xl border border-slate-200/80 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/30 px-3 py-2 text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-violet-500/20 transition-all [color-scheme:light] dark:[color-scheme:dark]"
              />
            </div>

            {(statusFilter !== 'all' || platformFilter !== 'all' || hasDateFilter) && (
              <button
                type="button"
                onClick={clearFilters}
                className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 dark:text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-rose-500 rounded-lg px-2 py-2"
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
                Clear
              </button>
            )}

            <span className="ml-auto text-xs text-slate-400 dark:text-slate-600 self-center tabular-nums">
              {loading ? '\u2026' : `${total} post${total !== 1 ? 's' : ''}`}
            </span>
          </div>
        </div>

        {/* Posts list */}
        <div
          className="space-y-3"
          role="list"
          aria-label="Posts list"
          aria-live="polite"
          aria-busy={loading}
        >
          {loading && Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}

          {!loading && error && (
            <div role="alert" className="flex items-start gap-3 rounded-2xl border border-rose-200/80 dark:border-rose-500/25 bg-rose-50 dark:bg-rose-500/10 p-5 text-sm text-rose-800 dark:text-rose-300">
              <AlertCircle className="h-5 w-5 flex-shrink-0 mt-px" aria-hidden="true" />
              <div className="flex-1">
                <p className="font-bold">Failed to load posts</p>
                <p className="text-xs mt-0.5 opacity-80">{error}</p>
              </div>
              <button
                onClick={fetchPosts}
                aria-label="Retry loading posts"
                className="flex items-center gap-1 text-xs font-semibold hover:underline cursor-pointer flex-shrink-0"
              >
                <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" /> Retry
              </button>
            </div>
          )}

          {!loading && !error && posts.length === 0 && (
            <EmptyState
              statusFilter={statusFilter}
              platformFilter={platformFilter}
              hasDateFilter={hasDateFilter}
              onClearFilters={clearFilters}
            />
          )}

          {!loading && !error && posts.map((post) => (
            <div key={post.id} role="listitem">
              <PostCard
                post={post}
                onDelete={(id) => openConfirm(id, 'delete')}
                onCancel={(id) => openConfirm(id, 'cancel')}
                onUnschedule={(id) => openConfirm(id, 'unschedule')}
                onApprove={handleApprovePost}
                onReject={(id) => setRejectModal({ postId: id, reason: '' })}
                isApprover={isApprover}
              />
            </div>
          ))}
        </div>

        {/* Pagination */}
        {!loading && !error && total > PAGE_LIMIT && (
          <div className="sp-card flex items-center justify-between px-4 py-3">
            <p className="text-xs text-slate-500 dark:text-slate-400 tabular-nums">
              Showing {page * PAGE_LIMIT + 1}&ndash;{Math.min((page + 1) * PAGE_LIMIT, total)} of {total}
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setPage((p) => p - 1)}
                disabled={!canPrev}
                aria-label="Previous page"
                className="flex items-center justify-center h-8 w-8 rounded-xl border border-slate-200/80 dark:border-slate-800/50 bg-slate-50/50 dark:bg-slate-800/20 text-slate-500 dark:text-slate-400 hover:border-violet-500/40 hover:text-violet-600 dark:hover:text-violet-400 disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500"
              >
                <ChevronLeft className="h-4 w-4" aria-hidden="true" />
              </button>
              <span className="text-xs font-semibold text-slate-600 dark:text-slate-400 tabular-nums min-w-[3.5rem] text-center">
                {page + 1} / {totalPages}
              </span>
              <button
                type="button"
                onClick={() => setPage((p) => p + 1)}
                disabled={!canNext}
                aria-label="Next page"
                className="flex items-center justify-center h-8 w-8 rounded-xl border border-slate-200/80 dark:border-slate-800/50 bg-slate-50/50 dark:bg-slate-800/20 text-slate-500 dark:text-slate-400 hover:border-violet-500/40 hover:text-violet-600 dark:hover:text-violet-400 disabled:opacity-40 disabled:cursor-not-allowed transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500"
              >
                <ChevronRight className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Confirm modal — outside main content so it overlays */}
      <ConfirmModal
        open={!!confirmModal}
        action={confirmModal?.action}
        onConfirm={executeAction}
        onCancel={closeConfirm}
        isLoading={confirmLoading}
        error={confirmError}
      />

      {/* Reject modal */}
      {rejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="sp-card w-full max-w-md p-6 shadow-xl animate-scale-up">
            <h3 className="text-base font-extrabold text-slate-900 dark:text-slate-50 font-heading">
              Reject Post
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Please provide a brief reason for rejecting this post. The content creator will see this feedback.
            </p>
            <textarea
              rows={4}
              className="w-full mt-4 rounded-xl border border-slate-200/80 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/30 px-3.5 py-2.5 text-xs text-slate-900 dark:text-slate-100 focus:border-violet-500/60 focus:bg-white dark:focus:bg-slate-800/60 focus:outline-none focus:ring-2 focus:ring-violet-500/15 transition-all"
              placeholder="Explain why this post is rejected..."
              value={rejectModal.reason || ''}
              onChange={(e) => setRejectModal(prev => ({ ...prev, reason: e.target.value }))}
            />
            <div className="mt-5 flex items-center justify-end gap-2.5">
              <Button variant="ghost" size="sm" onClick={() => setRejectModal(null)}>
                Cancel
              </Button>
              <Button
                variant="danger"
                size="sm"
                disabled={!rejectModal.reason || !rejectModal.reason.trim()}
                onClick={() => handleRejectPost(rejectModal.postId, rejectModal.reason)}
              >
                Confirm Rejection
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
