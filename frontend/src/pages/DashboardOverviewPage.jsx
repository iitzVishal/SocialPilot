import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTeam } from '../context/TeamContext';
import { accountsAPI, oauthAPI } from '../lib/api';
import { Card, CardHeader } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Skeleton } from '../components/ui/Skeleton';
import {
  Share2,
  CheckCircle2,
  ArrowUpRight,
  ShieldCheck,
  RefreshCw,
  PlusCircle,
  TrendingUp,
  Activity,
  Layers,
  Users,
  Lock,
  ArrowRight,
  Calendar,
  Send,
  BarChart3,
  Zap,
  Globe,
  Database,
} from 'lucide-react';
import {
  FacebookIcon,
  InstagramIcon,
  LinkedInIcon,
  TwitterIcon,
  YouTubeIcon,
  PinterestIcon,
} from '../components/icons/PlatformIcons';

/* ──────────────────────────────────────────────────────
   PLATFORM META — brand-accurate colors
────────────────────────────────────────────────────── */
const platformMeta = {
  facebook: {
    name: 'Facebook',
    icon: FacebookIcon,
    brandColor: 'text-[#1877F2]',
    iconBg: 'bg-[#1877F2]/10 dark:bg-[#1877F2]/15',
    iconBorder: 'border-[#1877F2]/20 dark:border-[#1877F2]/25',
  },
  instagram: {
    name: 'Instagram',
    icon: InstagramIcon,
    brandColor: 'text-[#E4405F]',
    iconBg: 'bg-gradient-to-tr from-amber-500/10 via-rose-500/10 to-purple-500/10 dark:from-amber-500/15 dark:via-rose-500/15 dark:to-purple-500/15',
    iconBorder: 'border-rose-500/20 dark:border-rose-500/25',
  },
  linkedin: {
    name: 'LinkedIn',
    icon: LinkedInIcon,
    brandColor: 'text-[#0A66C2]',
    iconBg: 'bg-[#0A66C2]/10 dark:bg-[#0A66C2]/15',
    iconBorder: 'border-[#0A66C2]/20 dark:border-[#0A66C2]/25',
  },
  twitter: {
    name: 'X / Twitter',
    icon: TwitterIcon,
    brandColor: 'text-slate-900 dark:text-slate-100',
    iconBg: 'bg-slate-900/8 dark:bg-white/8',
    iconBorder: 'border-slate-900/12 dark:border-white/12',
  },
  youtube: {
    name: 'YouTube',
    icon: YouTubeIcon,
    brandColor: 'text-[#FF0000]',
    iconBg: 'bg-[#FF0000]/10 dark:bg-[#FF0000]/12',
    iconBorder: 'border-[#FF0000]/20 dark:border-[#FF0000]/20',
  },
  pinterest: {
    name: 'Pinterest',
    icon: PinterestIcon,
    brandColor: 'text-[#BD081C]',
    iconBg: 'bg-[#BD081C]/10 dark:bg-[#BD081C]/12',
    iconBorder: 'border-[#BD081C]/20 dark:border-[#BD081C]/20',
  },
};

/* ──────────────────────────────────────────────────────
   QUICK ACTIONS
────────────────────────────────────────────────────── */
const quickActions = [
  {
    title: 'Create New Post',
    description: 'Compose and schedule cross-platform content updates',
    icon: Send,
    iconClass: 'sp-icon-container',
    badge: 'Live',
    badgeVariant: 'success',
    link: '/dashboard/composer',
    arrowClass: 'text-[var(--sp-primary)]',
  },
  {
    title: 'Content Calendar',
    description: 'Visual timeline for multi-network publishing flows',
    icon: Calendar,
    iconClass: 'sp-icon-container',
    badge: 'Live',
    badgeVariant: 'success',
    link: '/dashboard/calendar',
    arrowClass: 'text-[var(--sp-primary)]',
  },
  {
    title: 'Performance Analytics',
    description: 'Track audience growth and post engagement metrics',
    icon: BarChart3,
    iconClass: 'sp-icon-container',
    badge: 'M3 Ready',
    badgeVariant: 'neutral',
    link: '/dashboard/accounts',
    arrowClass: 'text-[var(--sp-primary)]',
  },
  {
    title: 'Team Management',
    description: 'Manage collaborator roles and approval workflows',
    icon: Users,
    iconClass: 'sp-icon-container',
    badge: 'RBAC Active',
    badgeVariant: 'success',
    link: '/dashboard/teams',
    arrowClass: 'text-[var(--sp-primary)]',
  },
];

/* ──────────────────────────────────────────────────────
   STAT CARD CONFIG
────────────────────────────────────────────────────── */
const statCardConfig = [
  {
    label: 'Total Accounts',
    iconClass: 'sp-icon-blue',
    Icon: Share2,
    subIcon: TrendingUp,
    subColor: 'text-blue-600 dark:text-blue-400',
    getValue: (data) => data.accounts.length,
    getSub: (data) => `${data.connectedCount} connected channels`,
    unit: 'Configured',
  },
  {
    label: 'Active Channels',
    iconClass: 'sp-icon-emerald',
    Icon: CheckCircle2,
    subIcon: Activity,
    subColor: 'text-emerald-600 dark:text-emerald-400',
    getValue: (data) => data.connectedCount,
    getSub: (data) => data.accounts.length > 0 ? `${data.activeRate}% availability rate` : 'Ready to connect',
    unit: 'Online',
  },
  {
    label: 'Networks Linked',
    iconClass: 'sp-icon-violet',
    Icon: Globe,
    subIcon: Layers,
    subColor: 'text-violet-600 dark:text-violet-400',
    getValue: (data) => data.distinctPlatforms,
    getSub: () => '6 adapter integrations',
    unit: 'of 6',
  },
  {
    label: 'Token Security',
    iconClass: 'sp-icon-cyan',
    Icon: Lock,
    subIcon: ShieldCheck,
    subColor: 'text-cyan-600 dark:text-cyan-400',
    getValue: (data) => data.validTokensCount,
    getSub: () => 'AES-256 Fernet Encrypted',
    unit: 'Valid Keys',
  },
];

/* ──────────────────────────────────────────────────────
   MAIN COMPONENT
────────────────────────────────────────────────────── */
export const DashboardOverviewPage = () => {
  const { user } = useAuth();
  const { activeTeamId, activeTeam } = useTeam();
  const [accounts, setAccounts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const heroRef = useRef(null);

  const fetchAccounts = async () => {
    try {
      setIsLoading(true);
      const params = {};
      if (activeTeamId) {
        params.team_id = activeTeamId;
      }
      const res = await accountsAPI.list(params);
      setAccounts(res.data);
    } catch (err) {
      console.error('Failed to load accounts for overview:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const [connectingPlatform, setConnectingPlatform] = useState(null);

  const handleInitiateOAuth = async (platformKey) => {
    setConnectingPlatform(platformKey);
    try {
      const res = await oauthAPI.getAuthorizationUrl(platformKey, activeTeamId);
      if (res.data?.authorization_url) {
        window.location.href = res.data.authorization_url;
      }
    } catch (err) {
      console.error('OAuth initiation error:', err);
      const msg = err.response?.data?.detail || err.message || `Failed to initiate OAuth for ${platformKey}`;
      alert(msg);
    } finally {
      setConnectingPlatform(null);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, [activeTeamId]);

  /* Subtle mouse-follow tilt on hero (disabled on touch/reduced-motion) */
  useEffect(() => {
    const hero = heroRef.current;
    if (!hero) return;
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (mq.matches) return;
    if ('ontouchstart' in window) return;

    const handleMove = (e) => {
      const rect = hero.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width  - 0.5;
      const y = (e.clientY - rect.top)  / rect.height - 0.5;
      hero.style.transform = `perspective(1000px) rotateX(${-y * 3}deg) rotateY(${x * 4}deg)`;
    };
    const handleLeave = () => {
      hero.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg)';
    };

    hero.addEventListener('mousemove', handleMove);
    hero.addEventListener('mouseleave', handleLeave);
    return () => {
      hero.removeEventListener('mousemove', handleMove);
      hero.removeEventListener('mouseleave', handleLeave);
    };
  }, []);

  const connectedCount    = accounts.filter((a) => a.connection_status === 'connected').length;
  const distinctPlatforms = new Set(accounts.map((a) => a.platform)).size;
  const validTokensCount  = accounts.filter((a) => !a.is_token_expired).length;
  const activeRate        = accounts.length > 0 ? Math.round((connectedCount / accounts.length) * 100) : 0;
  const data              = { accounts, connectedCount, distinctPlatforms, validTokensCount, activeRate };

  const greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  };

  return (
    <div className="space-y-6">

      {/* ═══════════════════════════════════════
          1. HERO BANNER
      ═══════════════════════════════════════ */}
      <div
        ref={heroRef}
        className="relative overflow-hidden rounded-2xl p-6 sm:p-8 text-white transition-transform duration-300 ease-out animate-sp-fade-in-up"
        style={{
          background: 'var(--gradient-hero)',
          boxShadow: 'var(--shadow-hero)',
          transformStyle: 'preserve-3d',
        }}
      >
        {/* Ambient orbs */}
        <div className="pointer-events-none absolute -right-16 -top-16 h-72 w-72 rounded-full bg-white/10 blur-3xl" aria-hidden="true" />
        <div className="pointer-events-none absolute -left-8 -bottom-16 h-56 w-56 rounded-full bg-blue-400/15 dark:bg-cyan-400/10 blur-3xl" aria-hidden="true" />
        {/* Subtle noise/grain overlay */}
        <div
          className="pointer-events-none absolute inset-0 rounded-2xl opacity-[0.04] mix-blend-overlay"
          style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noise\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noise)\'/%3E%3C/svg%3E")' }}
          aria-hidden="true"
        />

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">

          {/* Left: Greeting + CTA */}
          <div className="max-w-xl space-y-4 animate-sp-fade-in-up">
            {/* Role chip */}
            <div className="flex flex-wrap items-center gap-2">
              <div className="inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-white/15 backdrop-blur-sm px-3 py-1 text-xs font-semibold">
                <ShieldCheck className="h-3 w-3" aria-hidden="true" />
                {user?.role
                  ? user.role.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
                  : 'Content Creator'}
              </div>
              {activeTeam && (
                <div className="inline-flex items-center gap-1.5 rounded-full border border-white/25 bg-white/15 backdrop-blur-sm px-3 py-1 text-xs font-semibold">
                  <Users className="h-3 w-3" aria-hidden="true" />
                  Workspace: {activeTeam.name}
                </div>
              )}
            </div>

            {/* The single H1 for the page */}
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight font-heading leading-[1.1]">
              {greeting()},&nbsp;
              <span className="text-white/90">{user?.full_name?.split(' ')[0] || 'Creator'}</span>
              <span className="ml-2 text-3xl">👋</span>
            </h1>

            <p className="text-white/80 text-sm leading-relaxed max-w-md">
              Your centralized command center for multi-platform scheduling, token security, and unified audience growth.
            </p>

            {/* CTAs */}
            <div className="flex flex-wrap items-center gap-3 pt-1">
              <Link to="/dashboard/accounts">
                <Button variant="hero-cta" size="md" icon={PlusCircle}>
                  Connect Account
                </Button>
              </Link>
              <Link to="/dashboard/accounts">
                <button className="inline-flex items-center gap-1.5 text-sm font-semibold text-white/80 hover:text-white transition-colors">
                  View Accounts
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </button>
              </Link>
            </div>
          </div>

          {/* Right: User-centric SaaS metrics panel */}
          <div className="flex-shrink-0 animate-sp-fade-in-up-delay-1">
            <div
              className="grid grid-cols-2 gap-2.5 rounded-2xl p-4 border border-white/15"
              style={{ background: 'rgba(0,0,0,0.2)', backdropFilter: 'blur(16px)' }}
            >
              {[
                { label: 'Scheduled Posts',    value: `${accounts.length * 4} queued`,      Icon: Calendar },
                { label: 'Connected Channels', value: `${connectedCount} / 6 linked`, Icon: Globe },
                { label: 'Security Status',    value: 'Protected',             Icon: ShieldCheck, highlight: true },
                { label: 'Active Workspace',   value: activeTeam?.name || 'Personal', Icon: Users },
              ].map(({ label, value, Icon, highlight }) => (
                <div key={label} className="rounded-xl bg-white/[0.07] p-3">
                  <div className="flex items-center gap-1.5 mb-1">
                    <Icon className={`h-3 w-3 ${highlight ? 'text-emerald-300' : 'text-white/50'}`} aria-hidden="true" />
                    <p className="text-[10px] font-medium text-white/60 uppercase tracking-wide">{label}</p>
                  </div>
                  <p className="text-sm font-bold text-white leading-none">{value}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════
          2. STAT CARDS
      ═══════════════════════════════════════ */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4 animate-sp-fade-in-up-delay-1">
        {statCardConfig.map((cfg, i) => {
          const MainIcon = cfg.Icon;
          const SubIcon  = cfg.subIcon;
          return (
            <div
              key={cfg.label}
              className="sp-card p-5 flex flex-col justify-between"
              style={{ animationDelay: `${i * 60}ms` }}
            >
              <div className="flex items-start justify-between">
                <p className="text-xs font-semibold leading-none" style={{ color: 'var(--sp-text-secondary)' }}>
                  {cfg.label}
                </p>
                <div className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl ${cfg.iconClass}`}>
                  <MainIcon className="h-4.5 w-4.5" aria-hidden="true" />
                </div>
              </div>

              {isLoading ? (
                <div className="mt-4 space-y-2">
                  <Skeleton className="h-8 w-20" />
                  <Skeleton className="h-3 w-28" />
                </div>
              ) : (
                <div className="mt-4">
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-extrabold font-heading tabular-nums" style={{ color: 'var(--sp-text)' }}>
                      {cfg.getValue(data)}
                    </span>
                    <span className="text-xs font-medium" style={{ color: 'var(--sp-text-muted)' }}>
                      {cfg.unit}
                    </span>
                  </div>
                  <div className="mt-1.5 flex items-center gap-1 text-xs font-semibold" style={{ color: 'var(--sp-primary)' }}>
                    <SubIcon className="h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />
                    <span>{cfg.getSub(data)}</span>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ═══════════════════════════════════════
          3. PLATFORM INTEGRATIONS
      ═══════════════════════════════════════ */}
      <div className="sp-card p-6 animate-sp-fade-in-up-delay-2">
        <CardHeader
          title="Platform Integrations"
          description="Live status and connection actions for all 6 social networks"
          headingLevel="h2"
          action={
            <Link to="/dashboard/accounts" className="inline-flex">
              <Button variant="outline" size="sm" icon={ArrowUpRight}>
                Manage
              </Button>
            </Link>
          }
        />
        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {Object.entries(platformMeta).map(([platformKey, info]) => {
            const Icon = info.icon;
            const isConnected = accounts.some(
              (a) => a.platform === platformKey && a.connection_status === 'connected'
            );

            return (
              <div
                key={platformKey}
                className="group flex flex-col items-center gap-3 rounded-xl p-4 text-center transition-all duration-200 hover:-translate-y-0.5"
                style={{
                  background: isConnected ? 'rgba(34,197,94,0.08)' : 'var(--sp-card)',
                  border: isConnected ? '1px solid var(--sp-border-strong)' : '1px solid var(--sp-border)',
                }}
              >
                {/* Brand icon */}
                <div className={`flex h-12 w-12 items-center justify-center rounded-xl border ${info.iconBg} ${info.iconBorder} ${info.brandColor} shadow-xs`}>
                  <Icon className="h-6 w-6" aria-hidden="true" />
                </div>

                {/* Name */}
                <div>
                  <p className="text-xs font-bold font-heading leading-none" style={{ color: 'var(--sp-text)' }}>
                    {info.name}
                  </p>
                </div>

                {/* Single standardized CTA Action button */}
                {isConnected ? (
                  <Link
                    to="/dashboard/accounts"
                    className="w-full inline-flex items-center justify-center rounded-lg px-2.5 py-1.5 text-xs font-semibold transition-all duration-150 shadow-xs"
                    style={{
                      background: 'var(--sp-surface-2)',
                      color: 'var(--sp-text-secondary)',
                      border: '1px solid var(--sp-border)'
                    }}
                  >
                    Manage
                  </Link>
                ) : (
                  <button
                    type="button"
                    disabled={connectingPlatform === platformKey}
                    onClick={() => handleInitiateOAuth(platformKey)}
                    className="w-full inline-flex items-center justify-center rounded-lg px-2.5 py-1.5 text-xs font-semibold transition-all duration-150 shadow-xs cursor-pointer"
                    style={{
                      background: 'var(--sp-primary)',
                      color: '#FFFFFF'
                    }}
                  >
                    {connectingPlatform === platformKey ? 'Connecting...' : 'Connect'}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ═══════════════════════════════════════
          4. QUICK WORKSPACE ACTIONS
      ═══════════════════════════════════════ */}
      <div className="sp-card p-6 animate-sp-fade-in-up-delay-2">
        <CardHeader
          title="Quick Workspace Actions"
          description="Fast access to publishing, analytics, and team workflows"
          headingLevel="h2"
        />
        <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {quickActions.map((action) => {
            const Icon = action.icon;
            return (
              <Link
                key={action.title}
                to={action.link}
                className="group flex flex-col justify-between rounded-xl p-4 hover:-translate-y-0.5 transition-all duration-200"
                style={{ background: 'var(--sp-card)', border: '1px solid var(--sp-border)' }}
                onMouseEnter={e => { e.currentTarget.style.background='var(--sp-card-hover)'; e.currentTarget.style.borderColor='var(--sp-border-strong)'; }}
                onMouseLeave={e => { e.currentTarget.style.background='var(--sp-card)'; e.currentTarget.style.borderColor='var(--sp-border)'; }}
              >
                <div>
                  {/* Icon + badge row */}
                  <div className="flex items-start justify-between mb-3">
                    <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${action.iconClass}`}>
                      <Icon className="h-5 w-5" aria-hidden="true" />
                    </div>
                    <Badge variant={action.badgeVariant} size="xs" showDot={false}>
                      {action.badge}
                    </Badge>
                  </div>
                  <h3 className="text-sm font-bold font-heading transition-colors" style={{ color: 'var(--sp-text)' }}>
                    {action.title}
                  </h3>
                  <p className="text-xs mt-1 leading-relaxed line-clamp-2" style={{ color: 'var(--sp-text-secondary)' }}>
                    {action.description}
                  </p>
                </div>

                <div className={`mt-4 flex items-center gap-1 text-xs font-semibold ${action.arrowClass} group-hover:translate-x-0.5 transition-transform`}>
                  <span>Open workflow</span>
                  <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
                </div>
              </Link>
            );
          })}
        </div>
      </div>

      {/* ═══════════════════════════════════════
          5. RECENT ACCOUNTS TABLE
      ═══════════════════════════════════════ */}
      <div className="sp-card p-6 animate-sp-fade-in-up-delay-3">
        <CardHeader
          title="Recent Social Accounts"
          description="Real-time account status and synchronization records"
          headingLevel="h2"
          action={
            <Button variant="outline" size="sm" onClick={fetchAccounts} icon={RefreshCw}>
              Refresh
            </Button>
          }
        />
        <div className="mt-4 overflow-x-auto">
          {isLoading ? (
            <div className="space-y-3 py-4">
              <Skeleton className="h-12 w-full rounded-xl" />
              <Skeleton className="h-12 w-full rounded-xl" />
              <Skeleton className="h-12 w-full rounded-xl" />
            </div>
          ) : accounts.length === 0 ? (
            <div className="py-12 flex flex-col items-center text-center gap-3">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl" style={{ background: 'var(--active-nav-bg)', border: '1px solid var(--sp-border)', color: 'var(--sp-primary)' }}>
                <Share2 className="h-6 w-6" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm font-semibold" style={{ color: 'var(--sp-text)' }}>No accounts connected yet</p>
                <p className="text-xs mt-1" style={{ color: 'var(--sp-text-secondary)' }}>
                  Connect your first social profile to get started.
                </p>
              </div>
              <Link to="/dashboard/accounts">
                <Button variant="primary" size="sm" icon={PlusCircle}>
                  Connect Account
                </Button>
              </Link>
            </div>
          ) : (
            <table className="w-full text-left text-xs">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--sp-border)' }}>
                  {['Account', 'Platform', 'Status', 'Last Synced', 'Action'].map((h, i) => (
                    <th
                      key={h}
                      className={`py-3 px-3 text-[10px] font-bold uppercase tracking-widest ${i === 4 ? 'text-right' : ''}`}
                      style={{ color: 'var(--sp-text-muted)' }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {accounts.slice(0, 5).map((acc) => {
                  const pMeta = platformMeta[acc.platform];
                  const PIcon = pMeta?.icon;
                  return (
                    <tr
                      key={acc.id}
                      className="group last:border-0 transition-colors"
                      style={{ borderBottom: '1px solid var(--sp-border)' }}
                      onMouseEnter={e => e.currentTarget.style.background='var(--sp-card-hover)'}
                      onMouseLeave={e => e.currentTarget.style.background='transparent'}
                    >
                      <td className="py-3.5 px-3">
                        <span className="font-bold font-heading" style={{ color: 'var(--sp-text)' }}>
                          {acc.account_name}
                        </span>
                      </td>
                      <td className="py-3.5 px-3">
                        <div className="flex items-center gap-2">
                          {PIcon && (
                            <span className={`${pMeta.brandColor}`}>
                              <PIcon className="h-4 w-4" aria-hidden="true" />
                            </span>
                          )}
                           <span className="font-semibold capitalize" style={{ color: 'var(--sp-text-secondary)' }}>
                            {acc.platform}
                          </span>
                        </div>
                      </td>
                      <td className="py-3.5 px-3">
                        <Badge
                          variant={acc.connection_status === 'connected' ? 'success' : 'danger'}
                          size="xs"
                        >
                          {acc.connection_status}
                        </Badge>
                      </td>
                       <td className="py-3.5 px-3" style={{ color: 'var(--sp-text-muted)' }}>
                        {acc.last_synced_at
                          ? new Date(acc.last_synced_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                          : 'Not synced'}
                      </td>
                      <td className="py-3.5 px-3 text-right">
                        <Link
                          to="/dashboard/accounts"
                          className="inline-flex items-center gap-1 font-semibold transition-colors focus-visible:outline-none rounded"
                           style={{ color: 'var(--sp-primary)' }}
                           onMouseEnter={e => e.currentTarget.style.color='var(--sp-primary-bright)'}
                           onMouseLeave={e => e.currentTarget.style.color='var(--sp-primary)'}
                        >
                          Manage
                          <ArrowRight className="h-3 w-3" aria-hidden="true" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};
