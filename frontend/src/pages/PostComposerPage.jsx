import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
  useId,
} from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTeam } from '../context/TeamContext';
import { accountsAPI, postsAPI, mediaAPI } from '../lib/api';
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
  Clock,
  FileText,
  ImagePlus,
  X,
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  Info,
  Loader2,
  Eye,
  CalendarClock,
  Trash2,
  Globe,
  AtSign,
  AlignLeft,
  Sparkles,
} from 'lucide-react';

/* ─────────────────────────────────────────────────────────
   CONSTANTS
───────────────────────────────────────────────────────── */
const PLATFORM_CONFIG = {
  facebook: {
    name: 'Facebook',
    icon: FacebookIcon,
    charLimit: 63206,
    color: 'text-[#1877F2]',
    bg: 'bg-[#1877F2]/10 dark:bg-[#1877F2]/15',
    border: 'border-[#1877F2]/25 dark:border-[#1877F2]/30',
    activeBg: 'bg-[#1877F2]/10 dark:bg-[#1877F2]/15',
    activeBorder: 'border-[#1877F2]/50',
    avatarBg: 'bg-[#1877F2]',
    accepts: ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'video/mp4'],
    maxFileMB: 100,
    previewNote: 'Supports text, images, video, and links.',
  },
  instagram: {
    name: 'Instagram',
    icon: InstagramIcon,
    charLimit: 2200,
    color: 'text-[#E4405F]',
    bg: 'bg-gradient-to-tr from-amber-500/10 via-rose-500/10 to-purple-500/10',
    border: 'border-rose-500/25 dark:border-rose-500/30',
    activeBg: 'bg-rose-500/10 dark:bg-rose-500/12',
    activeBorder: 'border-rose-500/50',
    avatarBg: 'bg-gradient-to-tr from-amber-500 via-rose-500 to-purple-600',
    accepts: ['image/jpeg', 'image/png', 'image/webp', 'video/mp4'],
    maxFileMB: 100,
    previewNote: 'Requires at least one image or video.',
  },
  linkedin: {
    name: 'LinkedIn',
    icon: LinkedInIcon,
    charLimit: 3000,
    color: 'text-[#0A66C2]',
    bg: 'bg-[#0A66C2]/10 dark:bg-[#0A66C2]/15',
    border: 'border-[#0A66C2]/25',
    activeBg: 'bg-[#0A66C2]/10 dark:bg-[#0A66C2]/15',
    activeBorder: 'border-[#0A66C2]/50',
    avatarBg: 'bg-[#0A66C2]',
    accepts: ['image/jpeg', 'image/png', 'image/gif', 'video/mp4'],
    maxFileMB: 200,
    previewNote: 'Professional posts with up to 9 images.',
  },
  twitter: {
    name: 'X / Twitter',
    icon: TwitterIcon,
    charLimit: 280,
    color: 'text-slate-900 dark:text-slate-100',
    bg: 'bg-slate-900/8 dark:bg-white/8',
    border: 'border-slate-900/20 dark:border-slate-400/20',
    activeBg: 'bg-slate-900/10 dark:bg-white/10',
    activeBorder: 'border-slate-700 dark:border-slate-400',
    avatarBg: 'bg-slate-900 dark:bg-white',
    accepts: ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'video/mp4'],
    maxFileMB: 512,
    previewNote: '280 character limit. Threads not yet supported.',
  },
  youtube: {
    name: 'YouTube',
    icon: YouTubeIcon,
    charLimit: 5000,
    color: 'text-[#FF0000]',
    bg: 'bg-[#FF0000]/10 dark:bg-[#FF0000]/12',
    border: 'border-[#FF0000]/25',
    activeBg: 'bg-[#FF0000]/10 dark:bg-[#FF0000]/12',
    activeBorder: 'border-[#FF0000]/50',
    avatarBg: 'bg-[#FF0000]',
    accepts: ['video/mp4', 'video/mpeg', 'video/quicktime', 'video/x-msvideo'],
    maxFileMB: 256000,
    previewNote: 'Video only. Title and description required.',
  },
  pinterest: {
    name: 'Pinterest',
    icon: PinterestIcon,
    charLimit: 500,
    color: 'text-[#BD081C]',
    bg: 'bg-[#BD081C]/10 dark:bg-[#BD081C]/12',
    border: 'border-[#BD081C]/25',
    activeBg: 'bg-[#BD081C]/10 dark:bg-[#BD081C]/12',
    activeBorder: 'border-[#BD081C]/50',
    avatarBg: 'bg-[#BD081C]',
    accepts: ['image/jpeg', 'image/png', 'image/webp'],
    maxFileMB: 20,
    previewNote: 'Static images only. Board selection required.',
  },
};

const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'video/mp4'];
const MAX_MEDIA_MB = 100;
const MAX_MEDIA_COUNT = 4;

/* ─────────────────────────────────────────────────────────
   SMALL HELPER COMPONENTS
───────────────────────────────────────────────────────── */
const ValidationMessage = ({ message, type = 'error' }) => {
  if (!message) return null;
  const isError = type === 'error';
  return (
    <div
      role="alert"
      className={`flex items-start gap-2 rounded-lg px-3 py-2 text-xs font-medium ${
        isError
          ? 'bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-500/20'
          : 'bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-500/20'
      }`}
    >
      {isError
        ? <AlertCircle className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" aria-hidden="true" />
        : <Info className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" aria-hidden="true" />
      }
      <span>{message}</span>
    </div>
  );
};

const SectionLabel = ({ children, htmlFor }) => (
  <label
    htmlFor={htmlFor}
    className="block text-xs font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-2"
  >
    {children}
  </label>
);

const CharCounter = ({ current, limit }) => {
  const remaining = limit - current;
  const pct = current / limit;
  const color =
    pct >= 1 ? 'text-rose-600 dark:text-rose-400' :
    pct >= 0.9 ? 'text-amber-600 dark:text-amber-400' :
    'text-slate-400 dark:text-slate-500';
  return (
    <span className={`text-xs font-semibold tabular-nums ${color}`} aria-live="polite" aria-atomic="true">
      {remaining >= 0 ? remaining : `${Math.abs(remaining)} over`}
    </span>
  );
};

/* ─────────────────────────────────────────────────────────
   PLATFORM PREVIEW
───────────────────────────────────────────────────────── */
const PlatformPreview = ({ platform, content, mediaFiles, user }) => {
  const cfg = PLATFORM_CONFIG[platform];
  if (!cfg) return null;
  const Icon = cfg.icon;
  const displayName = user?.full_name || 'Your Name';
  const handle = user?.email?.split('@')[0] || 'youraccount';
  const now = new Date().toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });

  return (
    <div className="sp-card overflow-hidden">
      {/* Preview header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-100 dark:border-slate-800/60">
        <div className={`flex h-5 w-5 items-center justify-center rounded ${cfg.bg} ${cfg.color}`}>
          <Icon className="h-3 w-3" aria-hidden="true" />
        </div>
        <span className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
          {cfg.name} Preview
        </span>
        <span className="ml-auto text-[10px] text-slate-300 dark:text-slate-600 italic">Not exact rendering</span>
      </div>

      <div className="p-4">
        {/* Author row */}
        <div className="flex items-center gap-2.5 mb-3">
          <div className={`h-9 w-9 rounded-full flex-shrink-0 flex items-center justify-center text-white text-sm font-bold ${cfg.avatarBg}`}>
            {displayName.charAt(0).toUpperCase()}
          </div>
          <div>
            <p className="text-sm font-bold text-slate-900 dark:text-slate-100 leading-none">{displayName}</p>
            <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
              {platform === 'twitter' ? `@${handle}` : 'Just now · '}{platform !== 'twitter' && <Globe className="inline h-2.5 w-2.5" />}
            </p>
          </div>
        </div>

        {/* Content */}
        <div className="text-sm text-slate-800 dark:text-slate-200 whitespace-pre-wrap break-words leading-relaxed min-h-[3rem]">
          {content || (
            <span className="text-slate-300 dark:text-slate-600 italic text-xs">
              Your post content will appear here…
            </span>
          )}
        </div>

        {/* Media previews */}
        {mediaFiles.length > 0 && (
          <div className={`mt-3 grid gap-1.5 ${mediaFiles.length === 1 ? 'grid-cols-1' : 'grid-cols-2'} rounded-xl overflow-hidden`}>
            {mediaFiles.slice(0, 4).map((mf) => (
              <div key={mf.localId} className="aspect-video bg-slate-100 dark:bg-slate-800 rounded-lg overflow-hidden relative">
                {mf.previewUrl && mf.file.type.startsWith('image/') ? (
                  <img src={mf.previewUrl} alt={mf.file.name} className="w-full h-full object-cover" />
                ) : mf.previewUrl && mf.file.type.startsWith('video/') ? (
                  <video src={mf.previewUrl} className="w-full h-full object-cover" muted />
                ) : (
                  <div className="flex items-center justify-center h-full text-slate-400 dark:text-slate-600 text-xs">
                    Media
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Bottom row */}
        <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800/60 flex items-center gap-3 text-xs text-slate-400 dark:text-slate-600">
          <span>{now}</span>
          {cfg.previewNote && (
            <span className="ml-auto text-[10px] italic">{cfg.previewNote}</span>
          )}
        </div>
      </div>
    </div>
  );
};

/* ─────────────────────────────────────────────────────────
   MAIN COMPOSER PAGE
───────────────────────────────────────────────────────── */
export const PostComposerPage = () => {
  const { user } = useAuth();
  const { activeTeamId, activeTeam } = useTeam();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const draftId = searchParams.get('draft') || null; // null = create mode
  const textareaId = useId();
  const titleId = useId();
  const scheduleDateId = useId();
  const scheduleTimeId = useId();
  const fileInputRef = useRef(null);
  const dropZoneRef = useRef(null);
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

  const requiresApproval = activeTeam?.require_post_approval &&
    user?.role !== 'administrator' &&
    activeTeam?.owner_id !== user?.id &&
    userRole !== 'administrator';

  /* ── Draft loading state ── */
  const [draftLoading, setDraftLoading] = useState(false);
  const [draftLoadError, setDraftLoadError] = useState(null);

  /* ── Connected accounts (from backend) ── */
  const [accounts, setAccounts] = useState([]);
  const [accountsLoading, setAccountsLoading] = useState(true);
  const [accountsError, setAccountsError] = useState(null);

  /* ── Selected accounts/platforms ── */
  const [selectedAccountIds, setSelectedAccountIds] = useState([]);

  /* ── Content ── */
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');

  /* ── Media ── */
  const [mediaFiles, setMediaFiles] = useState([]); // [{ localId, file, previewUrl, uploading, error, uploadedMediaId, uploadedUrl }]
  const [isDragging, setIsDragging] = useState(false);

  /* ── Schedule ── */
  const [scheduleDate, setScheduleDate] = useState('');
  const [scheduleTime, setScheduleTime] = useState('');

  /* ── Preview ── */
  const [previewPlatform, setPreviewPlatform] = useState(null);

  /* ── Submission ── */
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitAction, setSubmitAction] = useState(null); // 'draft' | 'schedule' | 'publish'
  const [submitResult, setSubmitResult] = useState(null); // { type: 'success'|'error', message }

  /* ── Validation ── */
  const [errors, setErrors] = useState({});

  /* ─── Load connected accounts ─── */
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setAccountsLoading(true);
        setAccountsError(null);
        const params = {};
        if (activeTeamId) {
          params.team_id = activeTeamId;
        }
        const res = await accountsAPI.list(params);
        if (!cancelled) setAccounts(res.data);
      } catch (err) {
        if (!cancelled) setAccountsError('Failed to load accounts. Please refresh.');
      } finally {
        if (!cancelled) setAccountsLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [activeTeamId]);

  /* ─── Load draft when ?draft=<id> is in the URL ─── */
  useEffect(() => {
    if (!draftId) return;
    let cancelled = false;
    const loadDraft = async () => {
      setDraftLoading(true);
      setDraftLoadError(null);
      try {
        const res = await postsAPI.get(draftId);
        if (cancelled) return;
        const post = res.data;

        // Only allow editing drafts through this flow.
        // Scheduled posts use unschedule first, then edit.
        if (post.status !== 'draft') {
          setDraftLoadError(
            `This post has status "${post.status}" and cannot be edited here. Only drafts can be edited. Use the My Posts page to manage it.`
          );
          setDraftLoading(false);
          return;
        }

        // Populate content fields
        setTitle(post.title || '');
        setContent(post.base_content || '');

        // Populate account selection (IDs from target_accounts)
        setSelectedAccountIds(post.target_accounts || []);

        // Populate schedule if present
        if (post.scheduled_at) {
          const dt = new Date(post.scheduled_at);
          // YYYY-MM-DD
          setScheduleDate(dt.toISOString().split('T')[0]);
          // HH:MM (local time input)
          const hh = String(dt.getHours()).padStart(2, '0');
          const mm = String(dt.getMinutes()).padStart(2, '0');
          setScheduleTime(`${hh}:${mm}`);
        }

        // Populate pre-existing media attachments.
        // Mark each with preExisting:true so removeMedia() does NOT call mediaAPI.delete.
        // Supply a synthetic File-like object for display; file.type and file.name are used
        // for the preview and buildMediaAttachments().
        if (post.media_attachments && post.media_attachments.length > 0) {
          const preLoaded = post.media_attachments.map((att) => ({
            localId: att.media_id,          // stable — won't collide with new uploads
            file: {
              name: att.file_name,
              type: att.file_type,
              size: att.file_size,
            },
            previewUrl: att.url,             // already a remote URL — no revokeObjectURL needed
            uploading: false,
            error: null,
            uploadedMediaId: att.media_id,  // keeps buildMediaAttachments() working
            uploadedUrl: att.url,
            preExisting: true,              // flag: do NOT delete on remove
          }));
          setMediaFiles(preLoaded);
        }
      } catch (err) {
        if (cancelled) return;
        const d = err.response?.data?.detail;
        setDraftLoadError(
          typeof d === 'string' ? d :
          Array.isArray(d) ? d.map((x) => x.msg).join(' · ') :
          err.message || 'Failed to load draft.'
        );
      } finally {
        if (!cancelled) setDraftLoading(false);
      }
    };
    loadDraft();
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftId]);

  /* ─── Auto-set preview platform when accounts are selected ─── */
  useEffect(() => {
    if (selectedAccountIds.length > 0 && !previewPlatform) {
      const acc = accounts.find((a) => selectedAccountIds.includes(a.id));
      if (acc) setPreviewPlatform(acc.platform);
    }
    if (selectedAccountIds.length === 0) setPreviewPlatform(null);
  }, [selectedAccountIds, accounts, previewPlatform]);

  /* ─── Connected accounts grouped by platform ─── */
  const connectedAccounts = accounts.filter((a) => a.connection_status === 'connected');
  const disconnectedAccounts = accounts.filter((a) => a.connection_status !== 'connected');

  /* ─── Character limit for selected platforms ─── */
  const selectedPlatforms = [...new Set(
    selectedAccountIds
      .map((id) => accounts.find((a) => a.id === id)?.platform)
      .filter(Boolean)
  )];
  const lowestCharLimit = selectedPlatforms.length > 0
    ? Math.min(...selectedPlatforms.map((p) => PLATFORM_CONFIG[p]?.charLimit ?? 10000))
    : 10000;

  /* ─── Validation ─── */
  const validate = useCallback((action) => {
    const errs = {};
    if (selectedAccountIds.length === 0) {
      errs.accounts = 'Select at least one connected account.';
    }
    if (!content.trim()) {
      errs.content = 'Post content cannot be empty.';
    } else if (content.length > lowestCharLimit) {
      errs.content = `Content exceeds the ${lowestCharLimit.toLocaleString()} character limit for ${selectedPlatforms.join(' / ')}.`;
    }
    if (action === 'schedule') {
      if (!scheduleDate || !scheduleTime) {
        errs.schedule = 'Both date and time are required for scheduling.';
      } else {
        const dt = new Date(`${scheduleDate}T${scheduleTime}`);
        if (dt <= new Date()) {
          errs.schedule = 'Scheduled time must be in the future.';
        }
      }
    }
    // Media upload errors
    const mediaErrs = mediaFiles.filter((m) => m.error).map((m) => m.error);
    if (mediaErrs.length > 0) {
      errs.media = `Some media has upload errors: ${mediaErrs[0]}`;
    }
    const uploading = mediaFiles.some((m) => m.uploading);
    if (uploading) {
      errs.media = 'Please wait for all media uploads to complete.';
    }
    return errs;
  }, [selectedAccountIds, content, lowestCharLimit, scheduleDate, scheduleTime, mediaFiles, selectedPlatforms]);

  /* ─── Account toggle ─── */
  const toggleAccount = (acc) => {
    if (acc.connection_status !== 'connected') return;
    setSelectedAccountIds((prev) =>
      prev.includes(acc.id) ? prev.filter((id) => id !== acc.id) : [...prev, acc.id]
    );
    setErrors((e) => ({ ...e, accounts: undefined }));
  };

  /* ─── Media upload ─── */
  const validateAndAddFiles = (files) => {
    const newEntries = [];
    for (const file of Array.from(files)) {
      if (!ACCEPTED_TYPES.includes(file.type)) {
        newEntries.push({ localId: crypto.randomUUID(), file, error: `Unsupported type: ${file.type}`, uploading: false });
        continue;
      }
      if (file.size > MAX_MEDIA_MB * 1024 * 1024) {
        newEntries.push({ localId: crypto.randomUUID(), file, error: `File exceeds ${MAX_MEDIA_MB} MB limit.`, uploading: false });
        continue;
      }
      const previewUrl = URL.createObjectURL(file);
      newEntries.push({ localId: crypto.randomUUID(), file, previewUrl, uploading: true, error: null, uploadedMediaId: null, uploadedUrl: null });
    }

    if (mediaFiles.length + newEntries.length > MAX_MEDIA_COUNT) {
      setErrors((e) => ({ ...e, media: `Maximum ${MAX_MEDIA_COUNT} files allowed.` }));
      return;
    }

    setMediaFiles((prev) => [...prev, ...newEntries]);
    setErrors((e) => ({ ...e, media: undefined }));

    // Upload each valid file
    newEntries.forEach((entry) => {
      if (entry.uploading) {
        uploadMediaFile(entry);
      }
    });
  };

  const uploadMediaFile = async (entry) => {
    const formData = new FormData();
    formData.append('file', entry.file);
    try {
      const res = await mediaAPI.upload(formData);
      setMediaFiles((prev) =>
        prev.map((m) =>
          m.localId === entry.localId
            ? { ...m, uploading: false, uploadedMediaId: res.data.media_id, uploadedUrl: res.data.public_url }
            : m
        )
      );
    } catch (err) {
      const msg = err.response?.data?.detail || 'Upload failed. Please remove and retry.';
      setMediaFiles((prev) =>
        prev.map((m) =>
          m.localId === entry.localId
            ? { ...m, uploading: false, error: msg }
            : m
        )
      );
    }
  };

  const removeMedia = async (localId) => {
    const entry = mediaFiles.find((m) => m.localId === localId);
    if (!entry) return;
    // Only revoke blob URLs (not remote URLs from pre-loaded drafts)
    if (entry.previewUrl && !entry.preExisting) URL.revokeObjectURL(entry.previewUrl);
    // Only call mediaAPI.delete for newly-uploaded files, NOT pre-existing draft attachments
    if (!entry.preExisting && entry.uploadedMediaId) {
      try { await mediaAPI.delete(entry.uploadedMediaId); } catch (_) { /* best-effort */ }
    }
    setMediaFiles((prev) => prev.filter((m) => m.localId !== localId));
    setErrors((e) => ({ ...e, media: undefined }));
  };

  /* ─── Drag and drop ─── */
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    validateAndAddFiles(e.dataTransfer.files);
  };

  const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = () => setIsDragging(false);

  /* ─── Build media_attachments for API ─── */
  const buildMediaAttachments = () =>
    mediaFiles
      .filter((m) => m.uploadedMediaId && m.uploadedUrl)
      .map((m) => ({
        media_id: m.uploadedMediaId,
        url: m.uploadedUrl,
        file_name: m.file.name,
        file_type: m.file.type,
        file_size: m.file.size,
      }));

  /* ─── Submit — CREATE or EDIT mode ─── */
  const handleSubmit = async (action) => {
    const errs = validate(action);
    if (Object.keys(errs).length > 0) {
      setErrors(errs);
      return;
    }
    setErrors({});
    setIsSubmitting(true);
    setSubmitAction(action);
    setSubmitResult(null);

    try {
      let res;

      if (draftId) {
        // ── EDIT MODE: PUT /api/v1/posts/{id} (PostUpdate — all fields optional) ──
        // publish_now and the top-level schedule are create-only fields;
        // PostUpdate only accepts: title, base_content, media_attachments,
        // target_platforms, target_accounts, platform_customizations, scheduled_at.
        const updatePayload = {
          title: title.trim() || null,
          base_content: content.trim(),
          target_accounts: selectedAccountIds,
          target_platforms: selectedPlatforms,
          media_attachments: buildMediaAttachments(),
          platform_customizations: {},
          // Only include scheduled_at when the user actively chose schedule action
          ...(action === 'schedule'
            ? { scheduled_at: new Date(`${scheduleDate}T${scheduleTime}`).toISOString() }
            : {}),
        };
        res = await postsAPI.update(draftId, updatePayload);
        const updatedPost = res.data;
        if (action === 'submit_approval') {
          await postsAPI.submitForApproval(draftId);
          setSubmitResult({
            type: 'success',
            message: 'Post updated and submitted for approval successfully.',
          });
        } else {
          setSubmitResult({
            type: 'success',
            message:
              action === 'draft'
                ? `Draft updated (ID: ${updatedPost.id}).`
                : action === 'schedule'
                ? `Draft updated and scheduled for ${new Date(`${scheduleDate}T${scheduleTime}`).toLocaleString()}.`
                : `Draft updated (ID: ${updatedPost.id}). Use My Posts to publish it.`,
          });
        }
        // After successful update in edit mode, go back to My Posts after a moment
        setTimeout(() => navigate('/dashboard/posts'), 2500);
      } else {
        // ── CREATE MODE: POST /api/v1/posts ──
        const payload = {
          title: title.trim() || undefined,
          base_content: content.trim(),
          target_accounts: selectedAccountIds,
          target_platforms: selectedPlatforms,
          media_attachments: buildMediaAttachments(),
          platform_customizations: {},
          publish_now: action === 'publish',
          scheduled_at: action === 'schedule' ? new Date(`${scheduleDate}T${scheduleTime}`).toISOString() : undefined,
          team_id: activeTeamId || undefined,
        };
        res = await postsAPI.create(payload);
        const postId = res.data.id;
        if (action === 'submit_approval') {
          await postsAPI.submitForApproval(postId);
          setSubmitResult({
            type: 'success',
            message: 'Post submitted for approval successfully.',
          });
          setTimeout(() => navigate('/dashboard/posts'), 2500);
        } else {
          setSubmitResult({
            type: 'success',
            message:
              action === 'draft'
                ? `Draft saved (ID: ${postId}).`
                : action === 'schedule'
                ? `Post scheduled for ${new Date(`${scheduleDate}T${scheduleTime}`).toLocaleString()}.`
                : `Post queued for publishing (ID: ${postId}). Note: real social platform adapters require OAuth configuration.`,
          });
          if (action !== 'draft') {
            setTimeout(() => navigate('/dashboard'), 3500);
          }
        }
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      let msg = 'An unexpected error occurred.';
      if (Array.isArray(detail)) {
        msg = detail.map((d) => d.msg).join(' · ');
      } else if (typeof detail === 'string') {
        msg = detail;
      } else if (err.message) {
        msg = err.message;
      }
      setSubmitResult({ type: 'error', message: msg });
    } finally {
      setIsSubmitting(false);
      setSubmitAction(null);
    }
  };

  /* ─── Min datetime for schedule inputs ─── */
  const minDate = new Date().toISOString().split('T')[0];

  /* ─────────────────────────────────────────────────────
     RENDER
  ───────────────────────────────────────────────────── */
  return (
    <div className="space-y-6 animate-sp-fade-in-up">

      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-extrabold tracking-tight text-slate-900 dark:text-slate-50 font-heading flex items-center gap-2">
            <span className={`flex h-8 w-8 items-center justify-center rounded-xl text-white shadow-sm ${
              draftId
                ? 'bg-gradient-to-tr from-amber-500 to-orange-500 shadow-amber-500/25'
                : 'bg-gradient-to-tr from-violet-600 to-blue-500 shadow-violet-500/25'
            }`}>
              {draftId
                ? <FileText className="h-4 w-4" aria-hidden="true" />
                : <Send className="h-4 w-4" aria-hidden="true" />
              }
            </span>
            {draftId ? 'Edit Draft' : 'Post Composer'}
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            {draftId
              ? 'Editing an existing draft. Changes will update the saved draft.'
              : 'Compose, schedule, and publish across your connected social accounts.'}
          </p>
          {draftId && (
            <div className="mt-1.5 flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-400/30 bg-amber-400/10 px-2.5 py-0.5 text-[11px] font-semibold text-amber-700 dark:text-amber-400">
                <FileText className="h-3 w-3" aria-hidden="true" />
                Editing draft {draftId.slice(0, 8)}&hellip;
              </span>
              <Link
                to="/dashboard/posts"
                className="text-[11px] text-slate-400 dark:text-slate-600 hover:text-violet-600 dark:hover:text-violet-400 hover:underline"
              >
                &larr; Back to My Posts
              </Link>
            </div>
          )}
        </div>

        {/* Backend integration notice */}
        <div className="flex-shrink-0 flex items-center gap-2 rounded-xl border border-amber-500/25 bg-amber-500/8 dark:bg-amber-500/10 px-3 py-2 text-xs font-medium text-amber-700 dark:text-amber-400">
          <Info className="h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />
          <span>Real publishing requires OAuth credentials for each platform.</span>
        </div>
      </div>

      {/* Draft loading state */}
      {draftLoading && (
        <div className="sp-card flex items-center gap-3 px-5 py-4">
          <Loader2 className="h-5 w-5 animate-spin text-violet-500" aria-hidden="true" />
          <div>
            <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">Loading draft&hellip;</p>
            <p className="text-xs text-slate-400 dark:text-slate-500">Fetching draft {draftId?.slice(0, 8)}&hellip;</p>
          </div>
        </div>
      )}

      {/* Draft load error */}
      {draftLoadError && (
        <div role="alert" className="flex items-start gap-3 rounded-xl border border-rose-200 dark:border-rose-500/25 bg-rose-50 dark:bg-rose-500/10 px-4 py-4 text-sm">
          <AlertCircle className="h-5 w-5 flex-shrink-0 text-rose-600 dark:text-rose-400 mt-px" aria-hidden="true" />
          <div>
            <p className="font-bold text-rose-800 dark:text-rose-300">Could not load draft</p>
            <p className="text-xs text-rose-700/80 dark:text-rose-400/80 mt-0.5">{draftLoadError}</p>
            <Link to="/dashboard/posts" className="mt-2 inline-flex text-xs font-semibold text-rose-700 dark:text-rose-400 hover:underline">
              &larr; Return to My Posts
            </Link>
          </div>
        </div>
      )}

      {/* Success / Error result banner */}
      {submitResult && (
        <div
          role="status"
          aria-live="polite"
          className={`flex items-start gap-3 rounded-xl border p-4 text-sm font-medium ${
            submitResult.type === 'success'
              ? 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/25 text-emerald-800 dark:text-emerald-300'
              : 'bg-rose-50 dark:bg-rose-500/10 border-rose-200 dark:border-rose-500/25 text-rose-800 dark:text-rose-300'
          }`}
        >
          {submitResult.type === 'success'
            ? <CheckCircle2 className="h-5 w-5 flex-shrink-0 text-emerald-600 dark:text-emerald-400 mt-px" aria-hidden="true" />
            : <AlertCircle className="h-5 w-5 flex-shrink-0 text-rose-600 dark:text-rose-400 mt-px" aria-hidden="true" />
          }
          <span>{submitResult.message}</span>
          <button
            onClick={() => setSubmitResult(null)}
            aria-label="Dismiss"
            className="ml-auto flex-shrink-0 rounded-lg p-0.5 hover:bg-black/5 dark:hover:bg-white/10 transition-colors cursor-pointer"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-6 items-start">

        {/* ═══════ LEFT COLUMN: Composer ═══════ */}
        <div className="space-y-5">

          {/* ── 1. Account Selector ── */}
          <section
            className="sp-card p-5"
            aria-labelledby="section-accounts"
          >
            <div className="flex items-center gap-2 mb-4">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg sp-icon-violet">
                <AtSign className="h-3.5 w-3.5" aria-hidden="true" />
              </div>
              <h2 id="section-accounts" className="text-sm font-bold text-slate-900 dark:text-slate-100 font-heading">
                Target Accounts {activeTeam && <span className="text-xs text-slate-400 font-normal">in {activeTeam.name}</span>}
              </h2>
              {selectedAccountIds.length > 0 && (
                <Badge variant="primary" size="xs" showDot={false} className="ml-auto">
                  {selectedAccountIds.length} selected
                </Badge>
              )}
            </div>

            {accountsLoading ? (
              <div className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500">
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                Loading accounts…
              </div>
            ) : accountsError ? (
              <ValidationMessage message={accountsError} />
            ) : connectedAccounts.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-800 p-4 text-center">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  No connected accounts found.{' '}
                  <a href="/dashboard/accounts" className="font-semibold text-violet-600 dark:text-violet-400 hover:underline">
                    Connect an account →
                  </a>
                </p>
              </div>
            ) : (
              <fieldset>
                <legend className="sr-only">Select target social accounts</legend>
                <div className="flex flex-wrap gap-2">
                  {connectedAccounts.map((acc) => {
                    const cfg = PLATFORM_CONFIG[acc.platform];
                    const Icon = cfg?.icon;
                    const isSelected = selectedAccountIds.includes(acc.id);
                    return (
                      <button
                        key={acc.id}
                        type="button"
                        role="checkbox"
                        aria-checked={isSelected}
                        onClick={() => toggleAccount(acc)}
                        className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-semibold transition-all duration-150 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-slate-900 ${
                          isSelected
                            ? `${cfg?.activeBg ?? ''} ${cfg?.activeBorder ?? 'border-violet-500'} text-slate-900 dark:text-slate-100 shadow-sm`
                            : 'border-slate-200/80 dark:border-slate-800/60 bg-slate-50/50 dark:bg-slate-800/20 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-700'
                        }`}
                      >
                        {Icon && (
                          <span className={cfg?.color ?? ''}>
                            <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                          </span>
                        )}
                        <span>{acc.account_name}</span>
                        {isSelected && <CheckCircle2 className="h-3 w-3 text-violet-600 dark:text-violet-400" aria-hidden="true" />}
                      </button>
                    );
                  })}
                </div>

                {/* Disconnected accounts — shown greyed out */}
                {disconnectedAccounts.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800/60">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-slate-300 dark:text-slate-700 mb-2">
                      Disconnected (unavailable)
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {disconnectedAccounts.map((acc) => {
                        const cfg = PLATFORM_CONFIG[acc.platform];
                        const Icon = cfg?.icon;
                        return (
                          <div
                            key={acc.id}
                            title={`${acc.account_name} — ${acc.connection_status}`}
                            className="flex items-center gap-2 rounded-xl border border-slate-100 dark:border-slate-800/40 bg-slate-50/30 dark:bg-slate-800/10 px-3 py-2 text-xs font-medium text-slate-300 dark:text-slate-700 cursor-not-allowed opacity-60"
                            aria-disabled="true"
                          >
                            {Icon && <Icon className="h-3.5 w-3.5" aria-hidden="true" />}
                            <span>{acc.account_name}</span>
                            <Badge variant="danger" size="xs" showDot={false}>{acc.connection_status}</Badge>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </fieldset>
            )}

            {errors.accounts && <div className="mt-3"><ValidationMessage message={errors.accounts} /></div>}
          </section>

          {/* ── 2. Content Editor ── */}
          <section
            className="sp-card p-5"
            aria-labelledby="section-content"
          >
            <div className="flex items-center gap-2 mb-4">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg sp-icon-blue">
                <AlignLeft className="h-3.5 w-3.5" aria-hidden="true" />
              </div>
              <h2 id="section-content" className="text-sm font-bold text-slate-900 dark:text-slate-100 font-heading">
                Content
              </h2>
            </div>

            {/* Internal title (optional) */}
            <div className="mb-4">
              <SectionLabel htmlFor={titleId}>Internal Title (optional)</SectionLabel>
              <input
                id={titleId}
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                maxLength={200}
                placeholder="E.g. 'Q3 Product Launch — Week 2'"
                aria-describedby={`${titleId}-hint`}
                className="w-full rounded-xl border border-slate-200/80 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/30 px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:border-violet-500/60 dark:focus:border-violet-500/50 focus:bg-white dark:focus:bg-slate-800/60 focus:outline-none focus:ring-2 focus:ring-violet-500/15 transition-all"
              />
              <p id={`${titleId}-hint`} className="text-[10px] text-slate-400 dark:text-slate-600 mt-1">
                Used for internal organisation only. Not published.
              </p>
            </div>

            {/* Main text area */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <SectionLabel htmlFor={textareaId}>Post Content</SectionLabel>
                {selectedPlatforms.length > 0 && (
                  <div className="flex items-center gap-1.5 text-[10px] text-slate-400 dark:text-slate-500">
                    <CharCounter current={content.length} limit={lowestCharLimit} />
                    <span>/ {lowestCharLimit.toLocaleString()} chars</span>
                  </div>
                )}
              </div>
              <textarea
                id={textareaId}
                value={content}
                onChange={(e) => { setContent(e.target.value); setErrors((er) => ({ ...er, content: undefined })); }}
                placeholder="Write your post content here…"
                rows={7}
                aria-required="true"
                aria-describedby={errors.content ? `${textareaId}-error` : undefined}
                className={`w-full resize-y rounded-xl border bg-slate-50/50 dark:bg-slate-800/30 px-3.5 py-3 text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-violet-500/15 transition-all leading-relaxed ${
                  errors.content
                    ? 'border-rose-400 dark:border-rose-500/60 focus:border-rose-400'
                    : content.length > lowestCharLimit
                    ? 'border-amber-400 dark:border-amber-500/60 focus:border-amber-400'
                    : 'border-slate-200/80 dark:border-slate-700/60 focus:border-violet-500/60 dark:focus:border-violet-500/50 focus:bg-white dark:focus:bg-slate-800/60'
                }`}
              />
              {errors.content && (
                <div id={`${textareaId}-error`} className="mt-2">
                  <ValidationMessage message={errors.content} />
                </div>
              )}

              {/* Platform char limits info */}
              {selectedPlatforms.length > 1 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {selectedPlatforms.map((p) => (
                    <span key={p} className="inline-flex items-center gap-1 text-[10px] text-slate-400 dark:text-slate-600 border border-slate-100 dark:border-slate-800 rounded-full px-2 py-0.5">
                      {PLATFORM_CONFIG[p]?.name}: {PLATFORM_CONFIG[p]?.charLimit.toLocaleString()}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </section>

          {/* ── 3. Media Upload ── */}
          <section
            className="sp-card p-5"
            aria-labelledby="section-media"
          >
            <div className="flex items-center gap-2 mb-4">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg sp-icon-cyan">
                <ImagePlus className="h-3.5 w-3.5" aria-hidden="true" />
              </div>
              <h2 id="section-media" className="text-sm font-bold text-slate-900 dark:text-slate-100 font-heading">
                Media
              </h2>
              <span className="text-xs text-slate-400 dark:text-slate-500 ml-auto">
                {mediaFiles.length}/{MAX_MEDIA_COUNT} files
              </span>
            </div>

            {/* Drop zone */}
            {mediaFiles.length < MAX_MEDIA_COUNT && (
              <div
                ref={dropZoneRef}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => fileInputRef.current?.click()}
                role="button"
                tabIndex={0}
                aria-label="Drop media files here or click to browse"
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click(); }}
                className={`relative flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-8 text-center cursor-pointer transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 ${
                  isDragging
                    ? 'border-violet-500 bg-violet-500/5 dark:bg-violet-500/8'
                    : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 hover:bg-slate-50/50 dark:hover:bg-slate-800/20'
                }`}
              >
                <div className={`flex h-10 w-10 items-center justify-center rounded-full transition-colors ${
                  isDragging ? 'bg-violet-500/15 text-violet-600 dark:text-violet-400' : 'bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500'
                }`}>
                  <ImagePlus className="h-5 w-5" aria-hidden="true" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                    {isDragging ? 'Drop files here' : 'Drop files or click to browse'}
                  </p>
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
                    JPEG, PNG, GIF, WebP, MP4 · Max {MAX_MEDIA_MB} MB · Up to {MAX_MEDIA_COUNT} files
                  </p>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={ACCEPTED_TYPES.join(',')}
                  multiple
                  className="sr-only"
                  aria-hidden="true"
                  tabIndex={-1}
                  onChange={(e) => validateAndAddFiles(e.target.files)}
                />
              </div>
            )}

            {/* Uploaded file list */}
            {mediaFiles.length > 0 && (
              <div className="mt-3 space-y-2">
                {mediaFiles.map((mf) => (
                  <div
                    key={mf.localId}
                    className={`flex items-center gap-3 rounded-xl border p-3 transition-colors ${
                      mf.error
                        ? 'border-rose-200 dark:border-rose-500/30 bg-rose-50/50 dark:bg-rose-500/5'
                        : 'border-slate-200/80 dark:border-slate-800/50 bg-slate-50/30 dark:bg-slate-800/20'
                    }`}
                  >
                    {/* Thumbnail */}
                    <div className="h-12 w-12 flex-shrink-0 rounded-lg overflow-hidden bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
                      {mf.previewUrl && mf.file.type.startsWith('image/') ? (
                        <img src={mf.previewUrl} alt={mf.file.name} className="h-full w-full object-cover" />
                      ) : mf.previewUrl && mf.file.type.startsWith('video/') ? (
                        <video src={mf.previewUrl} className="h-full w-full object-cover" muted />
                      ) : (
                        <ImagePlus className="h-5 w-5 text-slate-300 dark:text-slate-600" aria-hidden="true" />
                      )}
                    </div>
                    {/* File info */}
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate">{mf.file.name}</p>
                      <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">
                        {(mf.file.size / (1024 * 1024)).toFixed(2)} MB
                        {mf.uploading && ' · Uploading…'}
                        {mf.uploadedMediaId && ' · Uploaded ✓'}
                      </p>
                      {mf.error && <p className="text-[10px] text-rose-600 dark:text-rose-400 mt-0.5">{mf.error}</p>}
                    </div>
                    {/* Status */}
                    <div className="flex-shrink-0">
                      {mf.uploading ? (
                        <Loader2 className="h-4 w-4 animate-spin text-violet-500" aria-label="Uploading" />
                      ) : mf.error ? (
                        <AlertCircle className="h-4 w-4 text-rose-500" aria-label="Upload error" />
                      ) : (
                        <CheckCircle2 className="h-4 w-4 text-emerald-500" aria-label="Upload complete" />
                      )}
                    </div>
                    {/* Remove */}
                    <button
                      type="button"
                      onClick={() => removeMedia(mf.localId)}
                      aria-label={`Remove ${mf.file.name}`}
                      className="flex-shrink-0 rounded-lg p-1 text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-500/10 transition-colors cursor-pointer"
                    >
                      <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {errors.media && <div className="mt-3"><ValidationMessage message={errors.media} /></div>}
          </section>

          {/* ── 4. Scheduling ── */}
          <section
            className="sp-card p-5"
            aria-labelledby="section-schedule"
          >
            <div className="flex items-center gap-2 mb-4">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg sp-icon-emerald">
                <CalendarClock className="h-3.5 w-3.5" aria-hidden="true" />
              </div>
              <h2 id="section-schedule" className="text-sm font-bold text-slate-900 dark:text-slate-100 font-heading">
                Schedule (optional)
              </h2>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <SectionLabel htmlFor={scheduleDateId}>Date</SectionLabel>
                <input
                  id={scheduleDateId}
                  type="date"
                  value={scheduleDate}
                  min={minDate}
                  onChange={(e) => { setScheduleDate(e.target.value); setErrors((er) => ({ ...er, schedule: undefined })); }}
                  aria-describedby={errors.schedule ? 'schedule-error' : undefined}
                  className="w-full rounded-xl border border-slate-200/80 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/30 px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:border-violet-500/60 focus:bg-white dark:focus:bg-slate-800/60 focus:outline-none focus:ring-2 focus:ring-violet-500/15 transition-all [color-scheme:light] dark:[color-scheme:dark]"
                />
              </div>
              <div>
                <SectionLabel htmlFor={scheduleTimeId}>Time</SectionLabel>
                <input
                  id={scheduleTimeId}
                  type="time"
                  value={scheduleTime}
                  onChange={(e) => { setScheduleTime(e.target.value); setErrors((er) => ({ ...er, schedule: undefined })); }}
                  aria-describedby={errors.schedule ? 'schedule-error' : undefined}
                  className="w-full rounded-xl border border-slate-200/80 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/30 px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:border-violet-500/60 focus:bg-white dark:focus:bg-slate-800/60 focus:outline-none focus:ring-2 focus:ring-violet-500/15 transition-all [color-scheme:light] dark:[color-scheme:dark]"
                />
              </div>
            </div>

            {errors.schedule && (
              <div id="schedule-error" className="mt-3">
                <ValidationMessage message={errors.schedule} />
              </div>
            )}

            <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-2">
              All times are in your local timezone. Leave blank to save as draft.
            </p>
          </section>

          {/* ── Action Buttons ── */}
          <div className="flex flex-wrap items-center gap-3 pb-2">
            <Button
              variant="ghost"
              size="md"
              icon={FileText}
              isLoading={isSubmitting && submitAction === 'draft'}
              disabled={isSubmitting || draftLoading}
              onClick={() => handleSubmit('draft')}
            >
              {draftId ? 'Update Draft' : 'Save Draft'}
            </Button>

            {requiresApproval ? (
              <Button
                variant="primary"
                size="md"
                icon={Send}
                isLoading={isSubmitting && submitAction === 'submit_approval'}
                disabled={isSubmitting || draftLoading}
                onClick={() => handleSubmit('submit_approval')}
              >
                Submit for Approval
              </Button>
            ) : (
              <>
                <Button
                  variant="outline"
                  size="md"
                  icon={Clock}
                  isLoading={isSubmitting && submitAction === 'schedule'}
                  disabled={isSubmitting || draftLoading || (!scheduleDate && !scheduleTime)}
                  onClick={() => handleSubmit('schedule')}
                >
                  {draftId ? 'Update & Schedule' : 'Schedule Post'}
                </Button>

                {!draftId && (
                  <Button
                    variant="primary"
                    size="md"
                    icon={Send}
                    isLoading={isSubmitting && submitAction === 'publish'}
                    disabled={isSubmitting}
                    onClick={() => handleSubmit('publish')}
                    className="ml-auto sm:ml-0"
                  >
                    Publish Now
                  </Button>
                )}
              </>
            )}

            {draftId && (
              <Link to="/dashboard/posts" className="ml-auto sm:ml-0">
                <Button variant="secondary" size="md" disabled={isSubmitting}>
                  Cancel Edit
                </Button>
              </Link>
            )}
          </div>

          {requiresApproval && (
            <div className="flex items-start gap-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 p-3.5 text-xs text-amber-600 dark:text-amber-400">
              <Info className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-bold">Approval Required</p>
                <p className="mt-0.5">This workspace requires approval before posts can be scheduled or published.</p>
              </div>
            </div>
          )}

          {/* Publish disclaimer */}
          <p className="text-[11px] text-slate-400 dark:text-slate-500 -mt-2 pb-2">
            <Info className="inline h-3 w-3 mr-1" aria-hidden="true" />
            {!requiresApproval
              ? "Publish Now" + " queues to the Celery worker. Real delivery to live social platforms requires OAuth credentials to be configured per platform."
              : "Post will be routed to team owners/admins for verification before actual publication/scheduling."}
          </p>
        </div>

        {/* ═══════ RIGHT COLUMN: Preview ═══════ */}
        <div className="space-y-4 xl:sticky xl:top-20">

          {/* Platform preview tabs */}
          <div className="sp-card overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-100 dark:border-slate-800/60">
              <Eye className="h-4 w-4 text-slate-400 dark:text-slate-500" aria-hidden="true" />
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100 font-heading">
                Post Preview
              </h2>
            </div>

            {selectedPlatforms.length === 0 ? (
              <div className="p-8 flex flex-col items-center text-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 dark:bg-slate-800 text-slate-300 dark:text-slate-600">
                  <Sparkles className="h-5 w-5" aria-hidden="true" />
                </div>
                <p className="text-xs text-slate-400 dark:text-slate-500">
                  Select an account above to see a platform preview.
                </p>
              </div>
            ) : (
              <>
                {/* Platform switcher tabs */}
                {selectedPlatforms.length > 1 && (
                  <div className="flex gap-1 px-3 pt-3 overflow-x-auto">
                    {selectedPlatforms.map((p) => {
                      const cfg = PLATFORM_CONFIG[p];
                      const Icon = cfg?.icon;
                      return (
                        <button
                          key={p}
                          type="button"
                          onClick={() => setPreviewPlatform(p)}
                          aria-pressed={previewPlatform === p}
                          className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-semibold whitespace-nowrap transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 ${
                            previewPlatform === p
                              ? 'bg-violet-500/10 dark:bg-violet-500/15 text-violet-700 dark:text-violet-300 border border-violet-500/20'
                              : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/50'
                          }`}
                        >
                          {Icon && <Icon className={`h-3.5 w-3.5 ${cfg?.color ?? ''}`} aria-hidden="true" />}
                          {cfg?.name}
                        </button>
                      );
                    })}
                  </div>
                )}

                {/* Preview card */}
                <div className="p-3">
                  <PlatformPreview
                    platform={previewPlatform || selectedPlatforms[0]}
                    content={content}
                    mediaFiles={mediaFiles}
                    user={user}
                  />
                </div>
              </>
            )}
          </div>

          {/* Selected account summary */}
          {selectedAccountIds.length > 0 && (
            <div className="sp-card p-4">
              <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-3">
                Publishing To
              </h3>
              <div className="space-y-2">
                {selectedAccountIds.map((id) => {
                  const acc = accounts.find((a) => a.id === id);
                  if (!acc) return null;
                  const cfg = PLATFORM_CONFIG[acc.platform];
                  const Icon = cfg?.icon;
                  return (
                    <div key={id} className="flex items-center gap-2.5">
                      <span className={`${cfg?.color ?? ''}`}>
                        {Icon && <Icon className="h-4 w-4" aria-hidden="true" />}
                      </span>
                      <span className="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate flex-1">
                        {acc.account_name}
                      </span>
                      <Badge variant="success" size="xs" showDot={true}>live</Badge>
                    </div>
                  );
                })}
              </div>
              <button
                type="button"
                onClick={() => setSelectedAccountIds([])}
                className="mt-3 text-[11px] text-slate-400 dark:text-slate-600 hover:text-rose-500 dark:hover:text-rose-400 transition-colors cursor-pointer"
              >
                Clear selection
              </button>
            </div>
          )}

          {/* Checklist */}
          <div className="sp-card p-4">
            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-3">
              Pre-publish Checklist
            </h3>
            <div className="space-y-2">
              {[
                { label: 'Account selected', ok: selectedAccountIds.length > 0 },
                { label: 'Content not empty', ok: content.trim().length > 0 },
                { label: 'Within char limit', ok: content.length <= lowestCharLimit && content.length > 0 },
                { label: 'Media uploaded', ok: mediaFiles.length === 0 || mediaFiles.every((m) => m.uploadedMediaId && !m.error) },
                { label: 'No upload errors', ok: mediaFiles.filter((m) => m.error).length === 0 },
              ].map(({ label, ok }) => (
                <div key={label} className="flex items-center gap-2 text-xs">
                  {ok
                    ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 flex-shrink-0" aria-hidden="true" />
                    : <div className="h-3.5 w-3.5 rounded-full border-2 border-slate-200 dark:border-slate-700 flex-shrink-0" aria-hidden="true" />
                  }
                  <span className={ok ? 'text-slate-700 dark:text-slate-300' : 'text-slate-400 dark:text-slate-600'}>
                    {label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
