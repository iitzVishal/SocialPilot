/**
 * AnalyticsPage — Milestone 4 Step 3
 *
 * Displays real internal metrics from the SocialPilot workspace:
 * - Post counts by status (period + lifetime)
 * - Daily published post trend (SVG line chart)
 * - Platform breakdown (horizontal bar chart)
 * - Campaign performance table
 * - Social account health
 *
 * External engagement metrics (likes, reach) are intentionally NOT shown
 * and a clear informational banner explains why.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useTeam } from '../context/TeamContext';
import { analyticsAPI, reportsAPI } from '../lib/api';
import {
  BarChart3,
  TrendingUp,
  Send,
  Calendar,
  CheckCircle2,
  Clock,
  XCircle,
  AlertCircle,
  Layers,
  Share2,
  RefreshCw,
  Info,
  ChevronDown,
  Activity,
  Zap,
  Globe,
  FileText,
  FileSpreadsheet,
} from 'lucide-react';
import { Skeleton } from '../components/ui/Skeleton';
import { Badge } from '../components/ui/Badge';

/* ─────────────────────────────────────────────────────
   PLATFORM CONFIG
───────────────────────────────────────────────────── */
const PLATFORM_META = {
  facebook:  { label: 'Facebook',  color: '#1877F2' },
  instagram: { label: 'Instagram', color: '#E4405F' },
  linkedin:  { label: 'LinkedIn',  color: '#0A66C2' },
  twitter:   { label: 'X / Twitter', color: '#1DA1F2' },
  youtube:   { label: 'YouTube',   color: '#FF0000' },
  pinterest: { label: 'Pinterest', color: '#E60023' },
};

const STATUS_META = {
  published:        { label: 'Published',       color: '#22C55E', icon: CheckCircle2 },
  scheduled:        { label: 'Scheduled',       color: '#3B82F6', icon: Clock },
  draft:            { label: 'Draft',           color: '#94A3B8', icon: BarChart3 },
  failed:           { label: 'Failed',          color: '#EF4444', icon: XCircle },
  pending_approval: { label: 'Pending Approval',color: '#F59E0B', icon: AlertCircle },
  cancelled:        { label: 'Cancelled',       color: '#6B7280', icon: XCircle },
};

const CAMPAIGN_STATUS_META = {
  active:    { label: 'Active',    variant: 'success' },
  draft:     { label: 'Draft',     variant: 'neutral' },
  paused:    { label: 'Paused',    variant: 'warning' },
  completed: { label: 'Completed', variant: 'primary' },
  archived:  { label: 'Archived', variant: 'neutral' },
};

/* ─────────────────────────────────────────────────────
   PURE SVG CHARTS (zero external dependencies)
───────────────────────────────────────────────────── */

/** Sparkline / area line chart */
function LineChart({ data = [], height = 120, color = '#22C55E', label = 'published' }) {
  const svgRef = useRef(null);
  if (!data.length) return null;

  const values = data.map(d => d[label] ?? 0);
  const maxVal = Math.max(...values, 1);
  const padding = { top: 8, right: 8, bottom: 24, left: 32 };
  const W = 600;
  const H = height;

  const innerW = W - padding.left - padding.right;
  const innerH = H - padding.top - padding.bottom;

  const xStep = innerW / (values.length - 1 || 1);

  const points = values.map((v, i) => ({
    x: padding.left + i * xStep,
    y: padding.top + innerH - (v / maxVal) * innerH,
    v,
  }));

  const linePath = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(' ');

  const areaPath = [
    linePath,
    `L ${points[points.length - 1].x.toFixed(1)} ${(padding.top + innerH).toFixed(1)}`,
    `L ${points[0].x.toFixed(1)} ${(padding.top + innerH).toFixed(1)}`,
    'Z',
  ].join(' ');

  // Y-axis ticks
  const yTicks = [0, Math.round(maxVal / 2), maxVal];

  // X-axis labels (show every ~7 days)
  const xLabels = data
    .map((d, i) => ({ i, date: d.date }))
    .filter((_, i) => i === 0 || i === data.length - 1 || i % 7 === 0);

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${W} ${H}`}
      className="w-full"
      style={{ height }}
      aria-label={`${label} chart`}
    >
      <defs>
        <linearGradient id={`grad-${label}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>

      {/* Y-axis guide lines */}
      {yTicks.map(tick => {
        const yPos = padding.top + innerH - (tick / maxVal) * innerH;
        return (
          <g key={tick}>
            <line
              x1={padding.left}
              y1={yPos}
              x2={W - padding.right}
              y2={yPos}
              stroke="currentColor"
              strokeOpacity="0.08"
              strokeWidth="1"
            />
            <text
              x={padding.left - 4}
              y={yPos + 4}
              textAnchor="end"
              fontSize="9"
              fill="currentColor"
              fillOpacity="0.5"
            >
              {tick}
            </text>
          </g>
        );
      })}

      {/* Area fill */}
      <path d={areaPath} fill={`url(#grad-${label})`} />

      {/* Line */}
      <path
        d={linePath}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />

      {/* X-axis labels */}
      {xLabels.map(({ i, date }) => (
        <text
          key={i}
          x={padding.left + i * xStep}
          y={H - 4}
          textAnchor="middle"
          fontSize="9"
          fill="currentColor"
          fillOpacity="0.5"
        >
          {date ? date.slice(5) : ''}
        </text>
      ))}

      {/* Dots on latest point */}
      {points.length > 0 && (
        <circle
          cx={points[points.length - 1].x}
          cy={points[points.length - 1].y}
          r="4"
          fill={color}
          stroke="white"
          strokeWidth="1.5"
        />
      )}
    </svg>
  );
}

/** Horizontal bar chart for platform/status breakdown */
function HBarChart({ data = [], colorKey = 'color', maxOverride }) {
  if (!data.length) return <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No data yet.</p>;
  const max = maxOverride || Math.max(...data.map(d => d.count), 1);

  return (
    <div className="space-y-3">
      {data.map((d, i) => {
        const pct = (d.count / max) * 100;
        const meta = PLATFORM_META[d.platform] || {};
        const barColor = d.color || meta.color || '#64748B';
        return (
          <div key={i} className="flex items-center gap-3">
            <div className="w-24 flex-shrink-0 text-xs font-medium truncate text-right" style={{ color: 'var(--text-secondary)' }}>
              {d.label || meta.label || d.platform || d.name}
            </div>
            <div className="flex-1 rounded-full overflow-hidden" style={{ height: 10, background: 'var(--border-subtle)' }}>
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{ width: `${pct}%`, background: barColor }}
              />
            </div>
            <div className="w-10 text-right text-xs font-semibold flex-shrink-0" style={{ color: 'var(--text-primary)' }}>
              {d.count}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** Mini donut chart for account health */
function DonutChart({ connected = 0, expired = 0, error = 0 }) {
  const total = connected + expired + error || 1;
  const cx = 60, cy = 60, r = 44, strokeW = 14;
  const circ = 2 * Math.PI * r;

  const segments = [
    { label: 'Connected', value: connected, color: '#22C55E' },
    { label: 'Expired',   value: expired,   color: '#F59E0B' },
    { label: 'Error',     value: error,     color: '#EF4444' },
  ];

  let offset = 0;
  const arcs = segments.map(s => {
    const pct = s.value / total;
    const len = pct * circ;
    const arc = { ...s, dashArray: `${len.toFixed(1)} ${(circ - len).toFixed(1)}`, dashOffset: -offset };
    offset += len;
    return arc;
  });

  return (
    <div className="flex items-center gap-4">
      <svg width="120" height="120" viewBox="0 0 120 120">
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--border-subtle)" strokeWidth={strokeW} />
        {arcs.map((a, i) => (
          <circle
            key={i}
            cx={cx} cy={cy} r={r}
            fill="none"
            stroke={a.color}
            strokeWidth={strokeW}
            strokeDasharray={a.dashArray}
            strokeDashoffset={a.dashOffset}
            strokeLinecap="butt"
            style={{ transition: 'stroke-dasharray 0.8s ease' }}
          />
        ))}
        <text x={cx} y={cy - 6} textAnchor="middle" fontSize="18" fontWeight="700" fill="currentColor">{total}</text>
        <text x={cx} y={cy + 10} textAnchor="middle" fontSize="9" fill="currentColor" fillOpacity="0.5">accounts</text>
      </svg>
      <div className="space-y-2">
        {arcs.map((a, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <span className="h-2.5 w-2.5 rounded-full flex-shrink-0" style={{ background: a.color }} />
            <span style={{ color: 'var(--text-secondary)' }}>{a.label}</span>
            <span className="font-bold ml-auto pl-3" style={{ color: 'var(--text-primary)' }}>{a.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────
   STAT CARD
───────────────────────────────────────────────────── */
function StatCard({ icon: Icon, label, value, sub, iconColor = '#22C55E', iconBg = 'rgba(34,197,94,0.12)', loading }) {
  return (
    <div
      className="rounded-2xl p-5 border transition-all duration-200 hover:shadow-lg group"
      style={{ background: 'var(--bg-card)', borderColor: 'var(--border-default)' }}
    >
      {loading ? (
        <>
          <Skeleton className="h-9 w-9 rounded-xl mb-3" />
          <Skeleton className="h-7 w-24 mb-1" />
          <Skeleton className="h-4 w-32" />
        </>
      ) : (
        <>
          <div
            className="h-9 w-9 rounded-xl flex items-center justify-center mb-3 transition-transform group-hover:scale-110"
            style={{ background: iconBg }}
          >
            <Icon className="h-4.5 w-4.5" style={{ color: iconColor }} />
          </div>
          <p className="text-2xl font-bold font-heading" style={{ color: 'var(--text-primary)' }}>{value ?? '—'}</p>
          <p className="text-xs font-medium mt-0.5" style={{ color: 'var(--text-muted)' }}>{label}</p>
          {sub && <p className="text-[11px] mt-1.5 font-medium" style={{ color: 'var(--text-muted)' }}>{sub}</p>}
        </>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────────────
   SECTION CARD
───────────────────────────────────────────────────── */
function SectionCard({ title, subtitle, children, icon: Icon, action }) {
  return (
    <div
      className="rounded-2xl border overflow-hidden"
      style={{ background: 'var(--bg-card)', borderColor: 'var(--border-default)' }}
    >
      <div className="flex items-center justify-between px-5 py-4 border-b" style={{ borderColor: 'var(--border-default)' }}>
        <div className="flex items-center gap-2.5">
          {Icon && (
            <div className="h-7 w-7 rounded-lg flex items-center justify-center" style={{ background: 'var(--active-nav-bg)' }}>
              <Icon className="h-3.5 w-3.5" style={{ color: 'var(--sp-primary)' }} />
            </div>
          )}
          <div>
            <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{title}</p>
            {subtitle && <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>{subtitle}</p>}
          </div>
        </div>
        {action}
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────
   PERIOD SELECTOR
───────────────────────────────────────────────────── */
const PERIOD_OPTIONS = [
  { label: '7d',  days: 7 },
  { label: '14d', days: 14 },
  { label: '30d', days: 30 },
  { label: '90d', days: 90 },
];

function PeriodSelector({ value, onChange }) {
  return (
    <div className="flex items-center gap-1 rounded-xl border p-1" style={{ borderColor: 'var(--border-default)', background: 'var(--bg-page)' }}>
      {PERIOD_OPTIONS.map(o => (
        <button
          key={o.days}
          onClick={() => onChange(o.days)}
          className="px-3 py-1 rounded-lg text-xs font-semibold transition-all"
          style={
            value === o.days
              ? { background: 'var(--sp-primary)', color: '#fff' }
              : { color: 'var(--text-muted)', background: 'transparent' }
          }
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────────────────
   ANALYTICS PAGE
───────────────────────────────────────────────────── */
export default function AnalyticsPage() {
  const { currentTeam } = useTeam();
  const [days, setDays] = useState(30);
  const [overview, setOverview] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [campaigns, setCampaigns] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  const teamId = currentTeam?.id;

  const fetchAll = useCallback(async () => {
    if (!teamId) return;
    setLoading(true);
    setError(null);
    try {
      const [ovRes, tlRes, cpRes] = await Promise.all([
        analyticsAPI.getOverview(teamId, days),
        analyticsAPI.getPostsTimeline(teamId, days),
        analyticsAPI.getCampaignPerformance(teamId),
      ]);
      setOverview(ovRes.data);
      setTimeline(tlRes.data);
      setCampaigns(cpRes.data);
      setLastRefreshed(new Date());
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load analytics data.');
    } finally {
      setLoading(false);
    }
  }, [teamId, days]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [downloadingExcel, setDownloadingExcel] = useState(false);

  const handleExportPDF = async () => {
    if (!teamId || downloadingPdf) return;
    setDownloadingPdf(true);
    try {
      const response = await reportsAPI.downloadPDF(teamId, days);
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `socialpilot_report_team_${teamId}_${days}d.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download PDF report:', err);
      alert('Failed to generate PDF report. Please try again.');
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handleExportExcel = async () => {
    if (!teamId || downloadingExcel) return;
    setDownloadingExcel(true);
    try {
      const response = await reportsAPI.downloadExcel(teamId, days);
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `socialpilot_report_team_${teamId}_${days}d.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download Excel report:', err);
      alert('Failed to generate Excel report. Please try again.');
    } finally {
      setDownloadingExcel(false);
    }
  };

  /* ── Derived ── */
  const posts = overview?.posts ?? {};
  const platformData = (overview?.platform_breakdown ?? []).map(d => ({
    ...d,
    label: PLATFORM_META[d.platform]?.label || d.platform,
    color: PLATFORM_META[d.platform]?.color || '#64748B',
  }));

  const campaignRows = campaigns?.campaigns ?? [];

  /* ── No team guard ── */
  if (!teamId) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <Globe className="h-14 w-14" style={{ color: 'var(--text-muted)' }} />
        <p className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>No Workspace Selected</p>
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Select a team workspace from the header to view analytics.
        </p>
      </div>
    );
  }

  /* ── Error state ── */
  if (error && !loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <AlertCircle className="h-12 w-12 text-red-500" />
        <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{error}</p>
        <button
          onClick={fetchAll}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold text-white transition-opacity hover:opacity-80"
          style={{ background: 'var(--sp-primary)' }}
        >
          <RefreshCw className="h-4 w-4" /> Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-8">
      {/* ── Page Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-heading" style={{ color: 'var(--text-primary)' }}>
            Analytics Dashboard
          </h1>
          <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
            Real publishing metrics for <span className="font-semibold">{currentTeam?.name}</span>
            {lastRefreshed && (
              <span className="ml-2 text-xs opacity-60">
                · Refreshed {lastRefreshed.toLocaleTimeString()}
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <PeriodSelector value={days} onChange={setDays} />
          
          {/* Export PDF */}
          <button
            onClick={handleExportPDF}
            disabled={downloadingPdf}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all hover:shadow-xs disabled:opacity-50 cursor-pointer"
            style={{ borderColor: 'var(--border-default)', background: 'var(--bg-card)', color: 'var(--text-primary)' }}
          >
            <FileText className={`h-3.5 w-3.5 ${downloadingPdf ? 'animate-bounce' : ''}`} style={{ color: '#EF4444' }} />
            {downloadingPdf ? 'Generating PDF…' : 'Export PDF'}
          </button>

          {/* Export Excel */}
          <button
            onClick={handleExportExcel}
            disabled={downloadingExcel}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all hover:shadow-xs disabled:opacity-50 cursor-pointer"
            style={{ borderColor: 'var(--border-default)', background: 'var(--bg-card)', color: 'var(--text-primary)' }}
          >
            <FileSpreadsheet className={`h-3.5 w-3.5 ${downloadingExcel ? 'animate-bounce' : ''}`} style={{ color: '#22C55E' }} />
            {downloadingExcel ? 'Generating Excel…' : 'Export Excel'}
          </button>

          <button
            onClick={fetchAll}
            disabled={loading}
            title="Refresh analytics"
            className="h-9 w-9 flex items-center justify-center rounded-xl border transition-all hover:shadow-sm disabled:opacity-50 cursor-pointer"
            style={{ borderColor: 'var(--border-default)', background: 'var(--bg-card)' }}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} style={{ color: 'var(--text-muted)' }} />
          </button>
        </div>
      </div>

      {/* ── Engagement Info Banner ── */}
      {overview?.engagement && !overview.engagement.available && (
        <div
          className="flex items-start gap-3 rounded-xl border p-4"
          style={{ background: 'rgba(59,130,246,0.06)', borderColor: 'rgba(59,130,246,0.2)' }}
        >
          <Info className="h-4 w-4 mt-0.5 flex-shrink-0" style={{ color: '#3B82F6' }} />
          <div>
            <p className="text-sm font-semibold" style={{ color: '#3B82F6' }}>External Engagement Metrics Unavailable</p>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{overview.engagement.reason}</p>
          </div>
        </div>
      )}

      {/* ── KPI Stat Row ── */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <StatCard
          loading={loading}
          icon={Send}
          label={`Posts (last ${days}d)`}
          value={posts.period_total}
          iconColor="#22C55E"
          iconBg="rgba(34,197,94,0.12)"
        />
        <StatCard
          loading={loading}
          icon={CheckCircle2}
          label="Published"
          value={posts.published}
          sub={posts.success_rate != null ? `${posts.success_rate}% success rate` : undefined}
          iconColor="#22C55E"
          iconBg="rgba(34,197,94,0.12)"
        />
        <StatCard
          loading={loading}
          icon={Clock}
          label="Scheduled"
          value={posts.scheduled}
          iconColor="#3B82F6"
          iconBg="rgba(59,130,246,0.12)"
        />
        <StatCard
          loading={loading}
          icon={Layers}
          label="Active Campaigns"
          value={overview?.campaigns?.active}
          sub={overview?.campaigns?.total ? `of ${overview.campaigns.total} total` : undefined}
          iconColor="#A855F7"
          iconBg="rgba(168,85,247,0.12)"
        />
        <StatCard
          loading={loading}
          icon={Share2}
          label="Connected Accounts"
          value={overview?.accounts?.connected}
          sub={overview?.accounts?.total ? `of ${overview.accounts.total} total` : undefined}
          iconColor="#F59E0B"
          iconBg="rgba(245,158,11,0.12)"
        />
      </div>

      {/* ── Lifetime Stats Row ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Lifetime Posts', value: posts.lifetime_total, icon: Activity, color: '#22C55E' },
          { label: 'Lifetime Published', value: posts.lifetime_published, icon: CheckCircle2, color: '#22C55E' },
          { label: 'Draft Posts', value: posts.draft, icon: BarChart3, color: '#94A3B8' },
          { label: 'Failed Posts', value: posts.failed, icon: XCircle, color: '#EF4444' },
        ].map(s => (
          <StatCard
            key={s.label}
            loading={loading}
            icon={s.icon}
            label={s.label}
            value={s.value}
            iconColor={s.color}
            iconBg={`${s.color}1a`}
          />
        ))}
      </div>

      {/* ── Charts Row ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Published Trend */}
        <div className="lg:col-span-2">
          <SectionCard
            title="Published Posts Trend"
            subtitle={`Daily published post count — last ${days} days`}
            icon={TrendingUp}
          >
            {loading ? (
              <Skeleton className="h-32 w-full rounded-xl" />
            ) : overview?.daily_published_trend?.length ? (
              <LineChart
                data={overview.daily_published_trend}
                height={130}
                color="#22C55E"
                label="published"
              />
            ) : (
              <p className="text-sm py-8 text-center" style={{ color: 'var(--text-muted)' }}>
                No published posts in this period.
              </p>
            )}
          </SectionCard>
        </div>

        {/* Platform Breakdown */}
        <div>
          <SectionCard title="Posts by Platform" subtitle="Current period" icon={Globe}>
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map(i => <Skeleton key={i} className="h-6 w-full rounded" />)}
              </div>
            ) : platformData.length ? (
              <HBarChart data={platformData} />
            ) : (
              <p className="text-sm py-4 text-center" style={{ color: 'var(--text-muted)' }}>
                No platform data yet.
              </p>
            )}
          </SectionCard>
        </div>
      </div>

      {/* ── Status Breakdown + Account Health ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Post Status Breakdown */}
        <SectionCard title="Post Status Breakdown" subtitle={`Last ${days} days`} icon={BarChart3}>
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-6 w-full rounded" />)}
            </div>
          ) : (
            <HBarChart
              data={Object.entries(STATUS_META).map(([key, meta]) => ({
                platform: key,
                label: meta.label,
                color: meta.color,
                count: posts[key] ?? 0,
              })).filter(d => d.count > 0)}
            />
          )}
        </SectionCard>

        {/* Account Health */}
        <SectionCard title="Account Health" subtitle="Connected social accounts" icon={Share2}>
          {loading ? (
            <Skeleton className="h-28 w-full rounded-xl" />
          ) : (
            <div className="space-y-5">
              <DonutChart
                connected={overview?.accounts?.connected ?? 0}
                expired={overview?.accounts?.expired ?? 0}
                error={overview?.accounts?.error ?? 0}
              />
              {overview?.accounts?.by_platform?.length > 0 && (
                <HBarChart
                  data={(overview.accounts.by_platform ?? []).map(d => ({
                    ...d,
                    label: PLATFORM_META[d.platform]?.label || d.platform,
                    color: PLATFORM_META[d.platform]?.color || '#64748B',
                  }))}
                />
              )}
            </div>
          )}
        </SectionCard>
      </div>

      {/* ── Campaign Performance Table ── */}
      <SectionCard
        title="Campaign Performance"
        subtitle="Publishing metrics per campaign (last 20)"
        icon={Layers}
      >
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map(i => <Skeleton key={i} className="h-10 w-full rounded-xl" />)}
          </div>
        ) : campaignRows.length === 0 ? (
          <div className="py-10 text-center">
            <Layers className="h-10 w-10 mx-auto mb-3 opacity-20" />
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No campaigns found in this workspace.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-default)' }}>
                  {['Campaign', 'Status', 'Platforms', 'Total Posts', 'Published', 'Scheduled', 'Failed', 'Publish Rate'].map(h => (
                    <th
                      key={h}
                      className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y" style={{ borderColor: 'var(--border-subtle)' }}>
                {campaignRows.map(row => {
                  const statusMeta = CAMPAIGN_STATUS_META[row.status] || { label: row.status, variant: 'neutral' };
                  const rateColor = row.publish_rate >= 75 ? '#22C55E' : row.publish_rate >= 40 ? '#F59E0B' : '#EF4444';
                  return (
                    <tr
                      key={row.campaign_id}
                      className="transition-colors hover:bg-black/3 dark:hover:bg-white/3"
                    >
                      <td className="px-3 py-3 font-medium max-w-[180px] truncate" style={{ color: 'var(--text-primary)' }}>
                        {row.name}
                      </td>
                      <td className="px-3 py-3">
                        <Badge variant={statusMeta.variant} size="xs" showDot={false}>
                          {statusMeta.label}
                        </Badge>
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex flex-wrap gap-1">
                          {(row.target_platforms ?? []).map(p => (
                            <span
                              key={p}
                              className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold border"
                              style={{
                                color: PLATFORM_META[p]?.color || '#64748B',
                                borderColor: `${PLATFORM_META[p]?.color || '#64748B'}30`,
                                background: `${PLATFORM_META[p]?.color || '#64748B'}10`,
                              }}
                            >
                              {PLATFORM_META[p]?.label || p}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-3 py-3 text-center font-semibold" style={{ color: 'var(--text-primary)' }}>
                        {row.total_posts}
                      </td>
                      <td className="px-3 py-3 text-center font-semibold" style={{ color: '#22C55E' }}>
                        {row.published_posts}
                      </td>
                      <td className="px-3 py-3 text-center font-semibold" style={{ color: '#3B82F6' }}>
                        {row.scheduled_posts}
                      </td>
                      <td className="px-3 py-3 text-center font-semibold" style={{ color: '#EF4444' }}>
                        {row.failed_posts}
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-2">
                          <div
                            className="flex-1 rounded-full overflow-hidden"
                            style={{ height: 6, background: 'var(--border-subtle)', minWidth: 48 }}
                          >
                            <div
                              className="h-full rounded-full"
                              style={{ width: `${row.publish_rate}%`, background: rateColor }}
                            />
                          </div>
                          <span className="text-xs font-bold w-10 text-right flex-shrink-0" style={{ color: rateColor }}>
                            {row.publish_rate}%
                          </span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      {/* ── Post Activity Timeline (multi-status) ── */}
      <SectionCard
        title="Post Activity Timeline"
        subtitle={`All post status changes — last ${days} days`}
        icon={Activity}
      >
        {loading ? (
          <Skeleton className="h-32 w-full rounded-xl" />
        ) : timeline?.series?.length ? (
          <div className="space-y-4">
            {/* Legend */}
            <div className="flex flex-wrap gap-4">
              {(timeline.statuses ?? []).filter(st => {
                const total = (timeline.series ?? []).reduce((a, d) => a + (d[st] ?? 0), 0);
                return total > 0;
              }).map(st => {
                const meta = STATUS_META[st] || { label: st, color: '#64748B' };
                return (
                  <div key={st} className="flex items-center gap-1.5 text-xs">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: meta.color }} />
                    <span style={{ color: 'var(--text-muted)' }}>{meta.label}</span>
                  </div>
                );
              })}
            </div>

            {/* Stacked lines — one per status */}
            {(timeline.statuses ?? []).filter(st => {
              const total = (timeline.series ?? []).reduce((a, d) => a + (d[st] ?? 0), 0);
              return total > 0;
            }).map(st => {
              const meta = STATUS_META[st] || { label: st, color: '#64748B' };
              return (
                <div key={st}>
                  <p className="text-[11px] mb-1 font-medium" style={{ color: 'var(--text-muted)' }}>{meta.label}</p>
                  <LineChart data={timeline.series} height={70} color={meta.color} label={st} />
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-sm py-8 text-center" style={{ color: 'var(--text-muted)' }}>
            No post activity in this period.
          </p>
        )}
      </SectionCard>
    </div>
  );
}
