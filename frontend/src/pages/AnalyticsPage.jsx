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
import { analyticsAPI, reportsAPI, campaignsAPI } from '../lib/api';
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
  Users,
  Eye,
  MousePointer,
  ThumbsUp,
  MessageSquare,
  DollarSign,
  TrendingDown,
  Check,
  HelpCircle,
  X,
  Loader2,
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
  const [activeTab, setActiveTab] = useState('overview');
  const [days, setDays] = useState(30);

  // Overview states
  const [overview, setOverview] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [campaigns, setCampaigns] = useState(null);

  // Engagement states
  const [engagement, setEngagement] = useState(null);
  const [engagementLoading, setEngagementLoading] = useState(false);

  // Audience states
  const [audience, setAudience] = useState(null);
  const [audienceLoading, setAudienceLoading] = useState(false);

  // ROI states
  const [roi, setRoi] = useState(null);
  const [roiLoading, setRoiLoading] = useState(false);

  // Comparison states
  const [allCampaigns, setAllCampaigns] = useState([]);
  const [selectedCompIds, setSelectedCompIds] = useState([]);
  const [compData, setCompData] = useState(null);
  const [compLoading, setCompLoading] = useState(false);

  // General states
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [syncNotice, setSyncNotice] = useState(null);

  const teamId = currentTeam?.id;

  const fetchOverview = useCallback(async () => {
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
      setError(err?.response?.data?.detail || 'Failed to load overview data.');
    } finally {
      setLoading(false);
    }
  }, [teamId, days]);

  const fetchEngagement = useCallback(async () => {
    if (!teamId) return;
    setEngagementLoading(true);
    try {
      const res = await analyticsAPI.getEngagement(teamId, { days });
      setEngagement(res.data);
    } catch (err) {
      console.error('Failed to load engagement analytics:', err);
    } finally {
      setEngagementLoading(false);
    }
  }, [teamId, days]);

  const fetchAudience = useCallback(async () => {
    if (!teamId) return;
    setAudienceLoading(true);
    try {
      const res = await analyticsAPI.getAudience(teamId, { days });
      setAudience(res.data);
    } catch (err) {
      console.error('Failed to load audience analytics:', err);
    } finally {
      setAudienceLoading(false);
    }
  }, [teamId, days]);

  const fetchROI = useCallback(async () => {
    if (!teamId) return;
    setRoiLoading(true);
    try {
      const res = await analyticsAPI.getROI(teamId, days);
      setRoi(res.data);
    } catch (err) {
      console.error('Failed to load ROI analytics:', err);
    } finally {
      setRoiLoading(false);
    }
  }, [teamId, days]);

  const fetchCampaignsForComparison = useCallback(async () => {
    if (!teamId) return;
    try {
      const res = await campaignsAPI.list(teamId, { limit: 100 });
      const items = res.data?.items || [];
      setAllCampaigns(items);
      if (selectedCompIds.length === 0 && items.length >= 2) {
        setSelectedCompIds(items.slice(0, 3).map(c => c.id));
      }
    } catch (err) {
      console.error('Failed to load campaigns list for comparison:', err);
    }
  }, [teamId, selectedCompIds.length]);

  const runComparison = useCallback(async (idsToCompare) => {
    const ids = idsToCompare || selectedCompIds;
    if (!teamId || ids.length < 2) return;
    setCompLoading(true);
    try {
      const res = await campaignsAPI.compare(teamId, ids);
      setCompData(res.data);
    } catch (err) {
      console.error('Failed to compare campaigns:', err);
    } finally {
      setCompLoading(false);
    }
  }, [teamId, selectedCompIds]);

  // Initial load
  useEffect(() => {
    fetchOverview();
    fetchCampaignsForComparison();
  }, [fetchOverview, fetchCampaignsForComparison]);

  // Tab switch effect
  useEffect(() => {
    if (activeTab === 'engagement') fetchEngagement();
    if (activeTab === 'audience') fetchAudience();
    if (activeTab === 'roi') fetchROI();
    if (activeTab === 'comparison' && selectedCompIds.length >= 2 && !compData) {
      runComparison();
    }
  }, [activeTab, fetchEngagement, fetchAudience, fetchROI, runComparison, selectedCompIds.length, compData]);

  const handleSyncAnalytics = async () => {
    if (!teamId || syncing) return;
    setSyncing(true);
    setSyncNotice(null);
    try {
      const res = await analyticsAPI.sync(teamId);
      setSyncNotice(`Analytics sync triggered. ${res.data?.message || 'Fetching real-time social metrics in background.'}`);
      setTimeout(() => {
        fetchOverview();
        if (activeTab === 'engagement') fetchEngagement();
        if (activeTab === 'audience') fetchAudience();
        if (activeTab === 'roi') fetchROI();
        if (activeTab === 'comparison') runComparison();
      }, 2500);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to trigger analytics sync.');
    } finally {
      setSyncing(false);
    }
  };

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
      link.setAttribute('download', `SocialPilot_Workspace_Report_${days}d.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download PDF report:', err);
      alert('Failed to generate PDF report.');
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
      link.setAttribute('download', `SocialPilot_Workspace_Report_${days}d.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download Excel report:', err);
      alert('Failed to generate Excel report.');
    } finally {
      setDownloadingExcel(false);
    }
  };

  const toggleComparisonCampaign = (id) => {
    const updated = selectedCompIds.includes(id)
      ? selectedCompIds.filter(x => x !== id)
      : [...selectedCompIds, id];
    setSelectedCompIds(updated);
    if (updated.length >= 2) {
      runComparison(updated);
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

  return (
    <div className="space-y-6 pb-8 animate-sp-fade-in-up">
      {/* ── Page Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold font-heading" style={{ color: 'var(--text-primary)' }}>
            Analytics & Intelligence
          </h1>
          <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
            Workspace performance and multi-platform analytics for <span className="font-semibold">{currentTeam?.name}</span>
            {lastRefreshed && (
              <span className="ml-2 text-xs opacity-60">
                · Synced {lastRefreshed.toLocaleTimeString()}
              </span>
            )}
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <PeriodSelector value={days} onChange={setDays} />

          {/* Sync Analytics Trigger */}
          <button
            onClick={handleSyncAnalytics}
            disabled={syncing}
            title="Sync metrics with social APIs"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all hover:shadow-xs disabled:opacity-50 cursor-pointer bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-400 border-indigo-500/25"
          >
            <Zap className={`h-3.5 w-3.5 ${syncing ? 'animate-spin text-amber-400' : 'text-indigo-400'}`} />
            {syncing ? 'Syncing...' : 'Sync Social Data'}
          </button>

          {/* Export PDF */}
          <button
            onClick={handleExportPDF}
            disabled={downloadingPdf}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all hover:shadow-xs disabled:opacity-50 cursor-pointer"
            style={{ borderColor: 'var(--border-default)', background: 'var(--bg-card)', color: 'var(--text-primary)' }}
          >
            <FileText className={`h-3.5 w-3.5 ${downloadingPdf ? 'animate-bounce text-red-400' : 'text-red-500'}`} />
            {downloadingPdf ? 'PDF…' : 'PDF'}
          </button>

          {/* Export Excel */}
          <button
            onClick={handleExportExcel}
            disabled={downloadingExcel}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all hover:shadow-xs disabled:opacity-50 cursor-pointer"
            style={{ borderColor: 'var(--border-default)', background: 'var(--bg-card)', color: 'var(--text-primary)' }}
          >
            <FileSpreadsheet className={`h-3.5 w-3.5 ${downloadingExcel ? 'animate-bounce text-emerald-400' : 'text-emerald-500'}`} />
            {downloadingExcel ? 'Excel…' : 'Excel'}
          </button>

          <button
            onClick={() => {
              fetchOverview();
              if (activeTab === 'engagement') fetchEngagement();
              if (activeTab === 'audience') fetchAudience();
              if (activeTab === 'roi') fetchROI();
              if (activeTab === 'comparison') runComparison();
            }}
            disabled={loading}
            title="Refresh"
            className="h-9 w-9 flex items-center justify-center rounded-xl border transition-all hover:shadow-sm disabled:opacity-50 cursor-pointer"
            style={{ borderColor: 'var(--border-default)', background: 'var(--bg-card)' }}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} style={{ color: 'var(--text-muted)' }} />
          </button>
        </div>
      </div>

      {/* Sync notice banner */}
      {syncNotice && (
        <div className="flex items-center justify-between p-3 rounded-xl border border-indigo-500/30 bg-indigo-500/10 text-xs text-indigo-300">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>{syncNotice}</span>
          </div>
          <button onClick={() => setSyncNotice(null)} className="text-gray-400 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* ── Navigation Tabs (Milestone 3) ── */}
      <div className="flex border-b border-[var(--border-default)] gap-2 overflow-x-auto pb-px">
        {[
          { id: 'overview', label: 'Overview', icon: BarChart3 },
          { id: 'engagement', label: 'Engagement Analytics', icon: Zap },
          { id: 'audience', label: 'Audience Growth', icon: Activity },
          { id: 'roi', label: 'Marketing ROI', icon: TrendingUp },
          { id: 'comparison', label: 'Campaign Comparison', icon: Layers },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 transition-all whitespace-nowrap cursor-pointer ${
              activeTab === tab.id
                ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* ═══════════════════════════════════════════════════════════
          TAB 1: OVERVIEW
      ═══════════════════════════════════════════════════════════ */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* KPI Stat Row */}
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

          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
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

          {/* Status Breakdown + Account Health */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
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
                </div>
              )}
            </SectionCard>
          </div>

          {/* Campaign Performance Table */}
          <SectionCard
            title="Campaign Performance"
            subtitle="Publishing metrics per campaign"
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
                      {['Campaign', 'Status', 'Platforms', 'Total Posts', 'Published', 'Scheduled', 'Publish Rate'].map(h => (
                        <th key={h} className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-gray-400">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border-subtle)] text-gray-200">
                    {campaignRows.map(row => (
                      <tr key={row.campaign_id} className="hover:bg-white/5 transition-colors">
                        <td className="px-3 py-3 font-medium text-[var(--text-primary)]">{row.name}</td>
                        <td className="px-3 py-3">
                          <span className="text-xs px-2 py-0.5 rounded-full bg-gray-500/10 text-gray-300 font-semibold border border-gray-500/20">
                            {row.status}
                          </span>
                        </td>
                        <td className="px-3 py-3">
                          <div className="flex flex-wrap gap-1">
                            {(row.target_platforms ?? []).map(p => (
                              <span key={p} className="text-[10px] uppercase font-semibold px-1.5 py-0.5 rounded bg-[var(--sp-surface-2)] text-gray-300 border border-[var(--sp-border)]">
                                {p}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="px-3 py-3 font-semibold">{row.total_posts}</td>
                        <td className="px-3 py-3 text-emerald-400 font-semibold">{row.published_posts}</td>
                        <td className="px-3 py-3 text-blue-400 font-semibold">{row.scheduled_posts}</td>
                        <td className="px-3 py-3 font-bold text-indigo-400">{row.publish_rate}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </SectionCard>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════
          TAB 2: ENGAGEMENT ANALYTICS
      ═══════════════════════════════════════════════════════════ */}
      {activeTab === 'engagement' && (
        <div className="space-y-6">
          {/* Top KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              loading={engagementLoading}
              icon={Eye}
              label={`Total Impressions (${days}d)`}
              value={engagement?.totals?.impressions?.toLocaleString() ?? '0'}
              iconColor="#3B82F6"
              iconBg="rgba(59,130,246,0.12)"
            />
            <StatCard
              loading={engagementLoading}
              icon={Users}
              label="Audience Reach"
              value={engagement?.totals?.reach?.toLocaleString() ?? '0'}
              iconColor="#A855F7"
              iconBg="rgba(168,85,247,0.12)"
            />
            <StatCard
              loading={engagementLoading}
              icon={ThumbsUp}
              label="Total Engagements"
              value={engagement?.totals?.engagements?.toLocaleString() ?? '0'}
              sub={`${(engagement?.totals?.likes || 0).toLocaleString()} likes · ${(engagement?.totals?.comments || 0).toLocaleString()} comments`}
              iconColor="#22C55E"
              iconBg="rgba(34,197,94,0.12)"
            />
            <StatCard
              loading={engagementLoading}
              icon={TrendingUp}
              label="Engagement Rate"
              value={`${(engagement?.totals?.engagement_rate || 0).toFixed(2)}%`}
              sub="Engagements / Impressions"
              iconColor="#F59E0B"
              iconBg="rgba(245,158,11,0.12)"
            />
          </div>

          {/* Interactions Breakdown */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl border border-[var(--sp-border)] bg-[var(--sp-card)]">
              <span className="text-xs text-gray-400 flex items-center gap-1.5">
                <ThumbsUp className="w-3.5 h-3.5 text-blue-400" /> Likes & Reactions
              </span>
              <p className="text-xl font-bold text-[var(--sp-text)] mt-1">
                {(engagement?.totals?.likes || 0).toLocaleString()}
              </p>
            </div>
            <div className="p-4 rounded-xl border border-[var(--sp-border)] bg-[var(--sp-card)]">
              <span className="text-xs text-gray-400 flex items-center gap-1.5">
                <MessageSquare className="w-3.5 h-3.5 text-emerald-400" /> Comments & Replies
              </span>
              <p className="text-xl font-bold text-[var(--sp-text)] mt-1">
                {(engagement?.totals?.comments || 0).toLocaleString()}
              </p>
            </div>
            <div className="p-4 rounded-xl border border-[var(--sp-border)] bg-[var(--sp-card)]">
              <span className="text-xs text-gray-400 flex items-center gap-1.5">
                <Share2 className="w-3.5 h-3.5 text-purple-400" /> Shares & Retweets
              </span>
              <p className="text-xl font-bold text-[var(--sp-text)] mt-1">
                {(engagement?.totals?.shares || 0).toLocaleString()}
              </p>
            </div>
            <div className="p-4 rounded-xl border border-[var(--sp-border)] bg-[var(--sp-card)]">
              <span className="text-xs text-gray-400 flex items-center gap-1.5">
                <MousePointer className="w-3.5 h-3.5 text-amber-400" /> Clicks & Link Taps
              </span>
              <p className="text-xl font-bold text-[var(--sp-text)] mt-1">
                {(engagement?.totals?.clicks || 0).toLocaleString()}
              </p>
            </div>
          </div>

          {/* Platform Engagement Breakdown */}
          <SectionCard
            title="Platform Engagement Breakdown"
            subtitle="Normalized metrics across connected social networks"
            icon={Globe}
          >
            {engagementLoading ? (
              <div className="space-y-3">
                {[1, 2, 3].map(i => <Skeleton key={i} className="h-8 w-full rounded" />)}
              </div>
            ) : Object.keys(engagement?.by_platform || {}).length === 0 ? (
              <div className="py-8 text-center text-sm text-gray-400">
                No platform engagement recorded for this period yet. Click &quot;Sync Social Data&quot; to ingest latest metrics.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[var(--sp-surface-2)] text-gray-400 uppercase font-semibold">
                    <tr>
                      <th className="py-2.5 px-3">Platform</th>
                      <th className="py-2.5 px-3">Impressions</th>
                      <th className="py-2.5 px-3">Reach</th>
                      <th className="py-2.5 px-3">Likes</th>
                      <th className="py-2.5 px-3">Comments</th>
                      <th className="py-2.5 px-3">Shares</th>
                      <th className="py-2.5 px-3">Clicks</th>
                      <th className="py-2.5 px-3">Rate</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--sp-border)] text-gray-200">
                    {Object.entries(engagement?.by_platform || {}).map(([plat, m]) => (
                      <tr key={plat} className="hover:bg-white/5 transition-colors">
                        <td className="py-3 px-3 font-bold uppercase text-[var(--sp-text)]">{plat}</td>
                        <td className="py-3 px-3 font-medium">{(m.impressions || 0).toLocaleString()}</td>
                        <td className="py-3 px-3 font-medium">{(m.reach || 0).toLocaleString()}</td>
                        <td className="py-3 px-3">{(m.likes || 0).toLocaleString()}</td>
                        <td className="py-3 px-3">{(m.comments || 0).toLocaleString()}</td>
                        <td className="py-3 px-3">{(m.shares || 0).toLocaleString()}</td>
                        <td className="py-3 px-3">{(m.clicks || 0).toLocaleString()}</td>
                        <td className="py-3 px-3 font-bold text-indigo-400">
                          {(m.engagement_rate || 0).toFixed(2)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </SectionCard>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════
          TAB 3: AUDIENCE GROWTH
      ═══════════════════════════════════════════════════════════ */}
      {activeTab === 'audience' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <StatCard
              loading={audienceLoading}
              icon={Users}
              label="Total Audience"
              value={(audience?.total_followers || 0).toLocaleString()}
              sub="Across all connected accounts"
              iconColor="#3B82F6"
              iconBg="rgba(59,130,246,0.12)"
            />
            <StatCard
              loading={audienceLoading}
              icon={TrendingUp}
              label={`Net Audience Growth (${days}d)`}
              value={
                audience?.net_growth != null
                  ? (audience.net_growth >= 0 ? `+${audience.net_growth.toLocaleString()}` : audience.net_growth.toLocaleString())
                  : '0'
              }
              sub={`${(audience?.growth_rate || 0).toFixed(2)}% growth rate`}
              iconColor="#22C55E"
              iconBg="rgba(34,197,94,0.12)"
            />
            <StatCard
              loading={audienceLoading}
              icon={Activity}
              label="Connected Social Channels"
              value={audience?.accounts?.length || 0}
              sub="Active profile syncs"
              iconColor="#A855F7"
              iconBg="rgba(168,85,247,0.12)"
            />
          </div>

          {/* Connected Accounts Audience Table */}
          <SectionCard
            title="Connected Accounts & Audience Distribution"
            subtitle="Real follower counts and historical trajectory"
            icon={Globe}
          >
            {audienceLoading ? (
              <div className="space-y-3">
                {[1, 2, 3].map(i => <Skeleton key={i} className="h-8 w-full rounded" />)}
              </div>
            ) : (audience?.accounts || []).length === 0 ? (
              <div className="py-8 text-center text-sm text-gray-400">
                No active social accounts with audience tracking found. Connect accounts in Account Management.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[var(--sp-surface-2)] text-gray-400 uppercase font-semibold">
                    <tr>
                      <th className="py-2.5 px-3">Account Name</th>
                      <th className="py-2.5 px-3">Platform</th>
                      <th className="py-2.5 px-3">Followers / Subscribers</th>
                      <th className="py-2.5 px-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--sp-border)] text-gray-200">
                    {(audience?.accounts || []).map((acc) => (
                      <tr key={acc.account_id} className="hover:bg-white/5 transition-colors">
                        <td className="py-3 px-3 font-bold text-[var(--sp-text)]">{acc.account_name}</td>
                        <td className="py-3 px-3 uppercase text-gray-400 font-semibold">{acc.platform}</td>
                        <td className="py-3 px-3 font-bold text-indigo-400">
                          {(acc.current_followers || 0).toLocaleString()}
                        </td>
                        <td className="py-3 px-3">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            Active Sync
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </SectionCard>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════
          TAB 4: MARKETING ROI
      ═══════════════════════════════════════════════════════════ */}
      {activeTab === 'roi' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              loading={roiLoading}
              icon={DollarSign}
              label="Total Marketing Spend"
              value={`$${(roi?.total_cost || 0).toLocaleString()}`}
              sub="Across all campaigns"
              iconColor="#3B82F6"
              iconBg="rgba(59,130,246,0.12)"
            />
            <StatCard
              loading={roiLoading}
              icon={TrendingUp}
              label="Attributed Revenue"
              value={`$${(roi?.total_return || 0).toLocaleString()}`}
              sub="Marketing value generated"
              iconColor="#22C55E"
              iconBg="rgba(34,197,94,0.12)"
            />
            <StatCard
              loading={roiLoading}
              icon={Zap}
              label="Aggregate Marketing ROI"
              value={roi ? `${roi.overall_roi >= 0 ? `+${roi.overall_roi.toFixed(1)}%` : `${roi.overall_roi.toFixed(1)}%`}` : '0.0%'}
              sub={roi?.overall_roi >= 0 ? 'Net Positive Return' : 'Net Loss'}
              iconColor={roi?.overall_roi >= 0 ? '#22C55E' : '#EF4444'}
              iconBg={roi?.overall_roi >= 0 ? 'rgba(34,197,94,0.12)' : 'rgba(239,68,68,0.12)'}
            />
            <StatCard
              loading={roiLoading}
              icon={Activity}
              label="Cost per Engagement (CPE)"
              value={roi?.cpe ? `$${roi.cpe.toFixed(2)}` : '—'}
              sub={roi?.cpc ? `CPC: $${roi.cpc.toFixed(2)}` : undefined}
              iconColor="#F59E0B"
              iconBg="rgba(245,158,11,0.12)"
            />
          </div>

          {/* Campaign ROI Performance Table */}
          <SectionCard
            title="Campaign ROI & Financial Returns"
            subtitle="Calculated marketing ROI, Cost per Engagement, and Cost per Click per campaign"
            icon={TrendingUp}
          >
            {roiLoading ? (
              <div className="space-y-3">
                {[1, 2, 3].map(i => <Skeleton key={i} className="h-8 w-full rounded" />)}
              </div>
            ) : (roi?.campaigns || []).length === 0 ? (
              <div className="py-8 text-center text-sm text-gray-400">
                No campaign financial data found. Assign budgets and revenue to campaigns in Campaign Management.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-[var(--sp-surface-2)] text-gray-400 uppercase font-semibold">
                    <tr>
                      <th className="py-2.5 px-3">Campaign</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">Budget ($)</th>
                      <th className="py-2.5 px-3">Revenue ($)</th>
                      <th className="py-2.5 px-3">Net Profit ($)</th>
                      <th className="py-2.5 px-3">ROI %</th>
                      <th className="py-2.5 px-3">CPE ($)</th>
                      <th className="py-2.5 px-3">CPC ($)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--sp-border)] text-gray-200">
                    {(roi?.campaigns || []).map((c) => {
                      const net = (c.revenue || 0) - (c.cost || 0);
                      const isPositive = (c.roi_percentage || 0) >= 0;
                      return (
                        <tr key={c.campaign_id} className="hover:bg-white/5 transition-colors">
                          <td className="py-3 px-3 font-bold text-[var(--sp-text)]">{c.name}</td>
                          <td className="py-3 px-3 uppercase text-gray-400 font-semibold">{c.status}</td>
                          <td className="py-3 px-3 font-medium">${(c.cost || 0).toLocaleString()}</td>
                          <td className="py-3 px-3 font-medium text-emerald-400">${(c.revenue || 0).toLocaleString()}</td>
                          <td className={`py-3 px-3 font-bold ${net >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            ${net.toLocaleString()}
                          </td>
                          <td className="py-3 px-3">
                            <span className={`px-2 py-0.5 rounded-full text-xs font-bold border ${
                              isPositive ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                            }`}>
                              {isPositive ? `+${(c.roi_percentage || 0).toFixed(1)}%` : `${(c.roi_percentage || 0).toFixed(1)}%`}
                            </span>
                          </td>
                          <td className="py-3 px-3 font-medium">{c.cpe != null ? `$${c.cpe.toFixed(2)}` : '—'}</td>
                          <td className="py-3 px-3 font-medium">{c.cpc != null ? `$${c.cpc.toFixed(2)}` : '—'}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </SectionCard>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════
          TAB 5: CAMPAIGN COMPARISON
      ═══════════════════════════════════════════════════════════ */}
      {activeTab === 'comparison' && (
        <div className="space-y-6">
          <SectionCard
            title="Select Campaigns to Compare"
            subtitle="Choose 2 or more campaigns to benchmark cross-platform performance"
            icon={Layers}
            action={
              selectedCompIds.length >= 2 ? (
                <button
                  onClick={() => runComparison()}
                  disabled={compLoading}
                  className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs rounded-lg transition-colors flex items-center gap-1.5"
                >
                  {compLoading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Recalculate Comparison
                </button>
              ) : null
            }
          >
            {allCampaigns.length === 0 ? (
              <p className="text-xs text-gray-400">No campaigns found in workspace.</p>
            ) : (
              <div className="flex flex-wrap gap-2.5">
                {allCampaigns.map(c => {
                  const isChecked = selectedCompIds.includes(c.id);
                  return (
                    <button
                      key={c.id}
                      onClick={() => toggleComparisonCampaign(c.id)}
                      className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-xs font-semibold transition-all cursor-pointer ${
                        isChecked
                          ? 'border-indigo-500 bg-indigo-600/15 text-indigo-300 ring-1 ring-indigo-500/30'
                          : 'border-[var(--sp-border)] bg-[var(--sp-surface-2)] text-gray-400 hover:text-gray-200'
                      }`}
                    >
                      <span className={`w-3.5 h-3.5 rounded flex items-center justify-center border text-[9px] ${
                        isChecked ? 'border-indigo-500 bg-indigo-600 text-white' : 'border-gray-500'
                      }`}>
                        {isChecked && '✓'}
                      </span>
                      <span>{c.name}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </SectionCard>

          {compLoading ? (
            <div className="flex flex-col items-center justify-center py-16 space-y-3">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
              <p className="text-sm text-gray-400">Generating comparative analysis...</p>
            </div>
          ) : compData?.campaigns?.length ? (
            <div className="space-y-6">
              {/* Highlight cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {(() => {
                  const items = compData.campaigns;
                  const highestROI = [...items].sort((a, b) => b.roi_percentage - a.roi_percentage)[0];
                  const highestEng = [...items].sort((a, b) => b.total_engagements - a.total_engagements)[0];
                  const highestReach = [...items].sort((a, b) => b.total_reach - a.total_reach)[0];
                  return (
                    <>
                      <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/5 space-y-1">
                        <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1">
                          <TrendingUp className="w-3.5 h-3.5" /> Highest ROI Leader
                        </span>
                        <p className="text-base font-bold text-[var(--sp-text)] truncate">{highestROI?.campaign_name}</p>
                        <p className="text-xs font-bold text-emerald-400">+{highestROI?.roi_percentage?.toFixed(1)}% ROI</p>
                      </div>

                      <div className="p-4 rounded-xl border border-indigo-500/30 bg-indigo-500/5 space-y-1">
                        <span className="text-xs text-indigo-400 font-semibold flex items-center gap-1">
                          <ThumbsUp className="w-3.5 h-3.5" /> Engagement Leader
                        </span>
                        <p className="text-base font-bold text-[var(--sp-text)] truncate">{highestEng?.campaign_name}</p>
                        <p className="text-xs font-bold text-indigo-400">{highestEng?.total_engagements?.toLocaleString()} engagements</p>
                      </div>

                      <div className="p-4 rounded-xl border border-purple-500/30 bg-purple-500/5 space-y-1">
                        <span className="text-xs text-purple-400 font-semibold flex items-center gap-1">
                          <Users className="w-3.5 h-3.5" /> Audience Reach Leader
                        </span>
                        <p className="text-base font-bold text-[var(--sp-text)] truncate">{highestReach?.campaign_name}</p>
                        <p className="text-xs font-bold text-purple-400">{highestReach?.total_reach?.toLocaleString()} reached</p>
                      </div>
                    </>
                  );
                })()}
              </div>

              {/* Comparative Table */}
              <div className="overflow-x-auto rounded-xl border border-[var(--sp-border)]">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-[var(--sp-surface-2)] text-gray-400 uppercase font-semibold border-b border-[var(--sp-border)]">
                    <tr>
                      <th className="py-3 px-4">Campaign</th>
                      <th className="py-3 px-3">Status</th>
                      <th className="py-3 px-3">Posts</th>
                      <th className="py-3 px-3">Impressions</th>
                      <th className="py-3 px-3">Reach</th>
                      <th className="py-3 px-3">Engagements</th>
                      <th className="py-3 px-3">Rate %</th>
                      <th className="py-3 px-3">Budget</th>
                      <th className="py-3 px-3">Revenue</th>
                      <th className="py-3 px-4">ROI %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--sp-border)] text-gray-200">
                    {compData.campaigns.map((item) => {
                      const isPositive = item.roi_percentage >= 0;
                      return (
                        <tr key={item.campaign_id} className="hover:bg-white/5 transition-colors">
                          <td className="py-3 px-4 font-bold text-[var(--sp-text)]">
                            <div>{item.campaign_name}</div>
                            {item.objective && (
                              <div className="text-[10px] text-gray-400 font-normal">{item.objective}</div>
                            )}
                          </td>
                          <td className="py-3 px-3 uppercase text-gray-400 font-semibold">{item.status}</td>
                          <td className="py-3 px-3">{item.published_posts} / {item.total_posts}</td>
                          <td className="py-3 px-3 font-medium">{item.total_impressions.toLocaleString()}</td>
                          <td className="py-3 px-3 font-medium">{item.total_reach.toLocaleString()}</td>
                          <td className="py-3 px-3 font-bold text-indigo-400">{item.total_engagements.toLocaleString()}</td>
                          <td className="py-3 px-3 font-semibold">{item.engagement_rate.toFixed(2)}%</td>
                          <td className="py-3 px-3 font-medium">${item.budget.toLocaleString()}</td>
                          <td className="py-3 px-3 font-medium text-emerald-400">${item.revenue.toLocaleString()}</td>
                          <td className="py-3 px-4">
                            <span className={`px-2 py-0.5 rounded-full text-xs font-bold border ${
                              isPositive ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                            }`}>
                              {isPositive ? `+${item.roi_percentage.toFixed(1)}%` : `${item.roi_percentage.toFixed(1)}%`}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="p-8 text-center border border-dashed border-[var(--sp-border)] rounded-xl text-gray-400 text-sm">
              Select at least 2 campaigns above to generate side-by-side comparative analytics.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
