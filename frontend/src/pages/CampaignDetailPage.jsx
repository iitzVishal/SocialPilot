import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  FolderKanban,
  Calendar,
  DollarSign,
  Target,
  FileText,
  CheckCircle2,
  Clock,
  PauseCircle,
  Archive,
  Plus,
  Loader2,
  AlertCircle,
  Edit2,
  Trash2,
  Send,
  Layers
} from 'lucide-react';
import { useTeam } from '../context/TeamContext';
import { campaignsAPI } from '../lib/api';

export default function CampaignDetailPage() {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const { currentTeam } = useTeam();

  const [campaign, setCampaign] = useState(null);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadCampaignData = async () => {
    if (!currentTeam?.id || !campaignId) return;
    try {
      setLoading(true);
      setError(null);

      // Fetch campaign details and associated posts
      const [campRes, postsRes] = await Promise.all([
        campaignsAPI.get(campaignId, currentTeam.id),
        campaignsAPI.getPosts(campaignId, currentTeam.id)
      ]);

      setCampaign(campRes.data);
      setPosts(postsRes.data.items || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load campaign details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCampaignData();
  }, [campaignId, currentTeam?.id]);

  const handleDelete = async () => {
    if (!campaign || !currentTeam?.id) return;
    if (!window.confirm(`Are you sure you want to delete campaign "${campaign.name}"?`)) return;
    try {
      await campaignsAPI.delete(campaign.id, currentTeam.id);
      navigate('/dashboard/campaigns');
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete campaign.');
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'active':
        return <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"><CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Active</span>;
      case 'draft':
        return <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-gray-500/10 text-gray-400 border border-gray-500/20"><Clock className="w-3.5 h-3.5 mr-1" /> Draft</span>;
      case 'paused':
        return <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20"><PauseCircle className="w-3.5 h-3.5 mr-1" /> Paused</span>;
      case 'completed':
        return <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20"><CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Completed</span>;
      case 'archived':
        return <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20"><Archive className="w-3.5 h-3.5 mr-1" /> Archived</span>;
      default:
        return <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-gray-500/10 text-gray-400">{status}</span>;
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-16 space-y-3">
        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
        <p className="text-sm text-gray-400">Loading campaign overview...</p>
      </div>
    );
  }

  if (error || !campaign) {
    return (
      <div className="p-8 max-w-xl mx-auto text-center space-y-4">
        <AlertCircle className="w-10 h-10 text-red-400 mx-auto" />
        <h2 className="text-lg font-bold text-[var(--sp-text)]">Error Loading Campaign</h2>
        <p className="text-sm text-gray-400">{error || 'Campaign not found.'}</p>
        <button
          onClick={() => navigate('/dashboard/campaigns')}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-500 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Campaigns
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Top Bar */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate('/dashboard/campaigns')}
          className="inline-flex items-center gap-1.5 text-xs text-gray-400 hover:text-[var(--sp-text)] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Campaigns
        </button>

        <div className="flex items-center gap-2">
          <button
            onClick={handleDelete}
            className="px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5"
          >
            <Trash2 className="w-3.5 h-3.5" /> Delete Campaign
          </button>
        </div>
      </div>

      {/* Campaign Header Banner */}
      <div className="p-6 rounded-2xl border border-[var(--sp-border)] bg-[var(--sp-card)] space-y-4 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-[var(--sp-text)]">{campaign.name}</h1>
              {getStatusBadge(campaign.status)}
            </div>
            {campaign.objective && (
              <p className="text-xs text-indigo-400 font-medium flex items-center gap-1">
                <Target className="w-3.5 h-3.5" /> Objective: {campaign.objective}
              </p>
            )}
          </div>

          <button
            onClick={() => navigate('/dashboard/composer')}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg shadow-sm transition-colors text-xs"
          >
            <Plus className="w-4 h-4" /> Add Post to Campaign
          </button>
        </div>

        {campaign.description && (
          <p className="text-sm text-gray-300 border-t border-[var(--sp-border)] pt-3 leading-relaxed">
            {campaign.description}
          </p>
        )}

        {/* Campaign Info Cards Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2">
          <div className="p-4 rounded-xl bg-[var(--sp-surface-2)] border border-[var(--sp-border)] space-y-1">
            <div className="text-xs text-gray-400 flex items-center gap-1">
              <FileText className="w-3.5 h-3.5 text-indigo-400" /> Total Posts
            </div>
            <div className="text-xl font-bold text-[var(--sp-text)]">{campaign.post_count}</div>
          </div>

          <div className="p-4 rounded-xl bg-[var(--sp-surface-2)] border border-[var(--sp-border)] space-y-1">
            <div className="text-xs text-gray-400 flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Published
            </div>
            <div className="text-xl font-bold text-emerald-400">{campaign.published_post_count}</div>
          </div>

          <div className="p-4 rounded-xl bg-[var(--sp-surface-2)] border border-[var(--sp-border)] space-y-1">
            <div className="text-xs text-gray-400 flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-amber-400" /> Scheduled
            </div>
            <div className="text-xl font-bold text-amber-400">{campaign.scheduled_post_count}</div>
          </div>

          <div className="p-4 rounded-xl bg-[var(--sp-surface-2)] border border-[var(--sp-border)] space-y-1">
            <div className="text-xs text-gray-400 flex items-center gap-1">
              <DollarSign className="w-3.5 h-3.5 text-blue-400" /> Budget Allocated
            </div>
            <div className="text-xl font-bold text-[var(--sp-text)]">
              ${campaign.budget ? campaign.budget.toLocaleString() : '0'}
            </div>
          </div>
        </div>

        {/* Platforms & Dates Footer */}
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-gray-400 pt-2 border-t border-[var(--sp-border)]">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-gray-500" />
            <span>
              Duration: {campaign.start_date ? new Date(campaign.start_date).toLocaleDateString() : 'TBD'} –{' '}
              {campaign.end_date ? new Date(campaign.end_date).toLocaleDateString() : 'TBD'}
            </span>
          </div>

          {campaign.target_platforms && campaign.target_platforms.length > 0 && (
            <div className="flex items-center gap-1">
              <span className="mr-1">Platforms:</span>
              {campaign.target_platforms.map((p) => (
                <span
                  key={p}
                  className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded bg-[var(--sp-surface-2)] text-gray-200 border border-[var(--sp-border)]"
                >
                  {p}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Associated Posts Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-[var(--sp-text)] flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-500" />
            Associated Campaign Posts ({posts.length})
          </h2>
        </div>

        {posts.length === 0 ? (
          <div className="p-10 text-center border border-dashed border-[var(--sp-border)] rounded-xl bg-[var(--sp-card)] space-y-3">
            <FileText className="w-10 h-10 text-gray-500 mx-auto opacity-50" />
            <p className="text-sm text-gray-400">No posts assigned to this campaign yet.</p>
            <button
              onClick={() => navigate('/dashboard/composer')}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-500 transition-colors"
            >
              <Plus className="w-4 h-4" /> Create First Post
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {posts.map((post) => (
              <div
                key={post.id}
                className="p-4 rounded-xl border border-[var(--sp-border)] bg-[var(--sp-card)] space-y-3 hover:border-indigo-500/30 transition-all"
              >
                <div className="flex items-center justify-between">
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-gray-500/10 text-gray-300 border border-gray-500/20">
                    {post.status}
                  </span>
                  {post.scheduled_at && (
                    <span className="text-[11px] text-gray-400 flex items-center gap-1">
                      <Clock className="w-3 h-3 text-amber-400" />{' '}
                      {new Date(post.scheduled_at).toLocaleString()}
                    </span>
                  )}
                </div>

                {post.title && (
                  <h4 className="text-sm font-bold text-[var(--sp-text)] line-clamp-1">{post.title}</h4>
                )}

                <p className="text-xs text-gray-300 line-clamp-3 leading-relaxed bg-[var(--sp-surface-2)] p-2.5 rounded-lg border border-[var(--sp-border)]">
                  {post.base_content}
                </p>

                {post.target_platforms && post.target_platforms.length > 0 && (
                  <div className="flex items-center gap-1 pt-1">
                    {post.target_platforms.map((p) => (
                      <span key={p} className="text-[10px] uppercase font-semibold text-gray-400 bg-[var(--sp-surface-2)] px-2 py-0.5 rounded border border-[var(--sp-border)]">
                        {p}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
