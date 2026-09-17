import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FolderKanban,
  Plus,
  Calendar,
  DollarSign,
  Target,
  MoreVertical,
  Edit2,
  Trash2,
  ExternalLink,
  Loader2,
  AlertCircle,
  Layers,
  Filter,
  CheckCircle2,
  PauseCircle,
  Clock,
  Archive,
  FileText
} from 'lucide-react';
import { useTeam } from '../context/TeamContext';
import { campaignsAPI } from '../lib/api';

const PLATFORMS = [
  { id: 'facebook', label: 'Facebook' },
  { id: 'instagram', label: 'Instagram' },
  { id: 'linkedin', label: 'LinkedIn' },
  { id: 'twitter', label: 'X / Twitter' },
  { id: 'youtube', label: 'YouTube' },
  { id: 'pinterest', label: 'Pinterest' }
];

export default function CampaignsPage() {
  const navigate = useNavigate();
  const { currentTeam } = useTeam();
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filter & Pagination State
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCampaign, setEditingCampaign] = useState(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [formError, setFormError] = useState(null);

  // Form Fields
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    objective: '',
    target_platforms: ['instagram', 'facebook'],
    start_date: '',
    end_date: '',
    budget: 0,
    status: 'active'
  });

  const loadCampaigns = async () => {
    if (!currentTeam?.id) return;
    try {
      setLoading(true);
      setError(null);
      const params = { page, limit: 12 };
      if (statusFilter) params.status = statusFilter;

      const res = await campaignsAPI.list(currentTeam.id, params);
      setCampaigns(res.data.items || []);
      setTotal(res.data.total || 0);
      setTotalPages(res.data.total_pages || 1);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load campaigns.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCampaigns();
  }, [currentTeam?.id, statusFilter, page]);

  const handleOpenModal = (campaign = null) => {
    if (campaign) {
      setEditingCampaign(campaign);
      setFormData({
        name: campaign.name || '',
        description: campaign.description || '',
        objective: campaign.objective || '',
        target_platforms: campaign.target_platforms || [],
        start_date: campaign.start_date ? campaign.start_date.split('T')[0] : '',
        end_date: campaign.end_date ? campaign.end_date.split('T')[0] : '',
        budget: campaign.budget || 0,
        status: campaign.status || 'draft'
      });
    } else {
      setEditingCampaign(null);
      setFormData({
        name: '',
        description: '',
        objective: '',
        target_platforms: ['instagram', 'facebook'],
        start_date: '',
        end_date: '',
        budget: 0,
        status: 'active'
      });
    }
    setFormError(null);
    setIsModalOpen(true);
  };

  const handlePlatformToggle = (platformId) => {
    setFormData((prev) => {
      const exists = prev.target_platforms.includes(platformId);
      const updated = exists
        ? prev.target_platforms.filter((p) => p !== platformId)
        : [...prev.target_platforms, platformId];
      return { ...prev, target_platforms: updated };
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!currentTeam?.id) return;
    try {
      setModalLoading(true);
      setFormError(null);

      const payload = {
        name: formData.name,
        description: formData.description || null,
        objective: formData.objective || null,
        target_platforms: formData.target_platforms,
        start_date: formData.start_date ? new Date(formData.start_date).toISOString() : null,
        end_date: formData.end_date ? new Date(formData.end_date).toISOString() : null,
        budget: parseFloat(formData.budget) || 0,
        status: formData.status
      };

      if (editingCampaign) {
        await campaignsAPI.update(editingCampaign.id, currentTeam.id, payload);
      } else {
        await campaignsAPI.create(currentTeam.id, payload);
      }

      setIsModalOpen(false);
      loadCampaigns();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Failed to save campaign.');
    } finally {
      setModalLoading(false);
    }
  };

  const handleDelete = async (campaignId, campaignName) => {
    if (!window.confirm(`Are you sure you want to delete campaign "${campaignName}"?`)) return;
    try {
      await campaignsAPI.delete(campaignId, currentTeam.id);
      loadCampaigns();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete campaign.');
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'active':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"><CheckCircle2 className="w-3 h-3 mr-1" /> Active</span>;
      case 'draft':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-500/10 text-gray-400 border border-gray-500/20"><Clock className="w-3 h-3 mr-1" /> Draft</span>;
      case 'paused':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20"><PauseCircle className="w-3 h-3 mr-1" /> Paused</span>;
      case 'completed':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20"><CheckCircle2 className="w-3 h-3 mr-1" /> Completed</span>;
      case 'archived':
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20"><Archive className="w-3 h-3 mr-1" /> Archived</span>;
      default:
        return <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-500/10 text-gray-400">{status}</span>;
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--sp-text)] flex items-center gap-2">
            <FolderKanban className="w-7 h-7 text-indigo-500" />
            Campaign Management
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Organize content scheduling, objectives, budgets, and multi-platform performance metrics.
          </p>
        </div>

        <button
          onClick={() => handleOpenModal()}
          className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg shadow-sm transition-colors text-sm"
        >
          <Plus className="w-4 h-4" />
          Create Campaign
        </button>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-xl border border-[var(--sp-border)] bg-[var(--sp-card)]">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Status:</span>
          <div className="flex flex-wrap gap-1">
            {['', 'active', 'draft', 'paused', 'completed', 'archived'].map((st) => (
              <button
                key={st}
                onClick={() => { setStatusFilter(st); setPage(1); }}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                  statusFilter === st
                    ? 'bg-indigo-600 text-white'
                    : 'text-gray-400 hover:bg-[var(--sp-surface-2)] hover:text-gray-200'
                }`}
              >
                {st === '' ? 'All Statuses' : st.charAt(0).toUpperCase() + st.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className="text-xs text-gray-400">
          Showing <span className="font-semibold text-[var(--sp-text)]">{campaigns.length}</span> of{' '}
          <span className="font-semibold text-[var(--sp-text)]">{total}</span> campaigns
        </div>
      </div>

      {/* Content Area */}
      {loading ? (
        <div className="flex flex-col items-center justify-center p-12 space-y-3">
          <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
          <p className="text-sm text-gray-400">Loading campaigns...</p>
        </div>
      ) : error ? (
        <div className="p-6 rounded-xl border border-red-500/20 bg-red-500/10 text-center space-y-3">
          <AlertCircle className="w-8 h-8 text-red-400 mx-auto" />
          <p className="text-sm text-red-300">{error}</p>
          <button
            onClick={loadCampaigns}
            className="px-4 py-1.5 bg-red-600/30 hover:bg-red-600/50 text-red-200 text-xs rounded-md transition-colors"
          >
            Retry
          </button>
        </div>
      ) : campaigns.length === 0 ? (
        <div className="p-12 text-center border border-dashed border-[var(--sp-border)] rounded-xl bg-[var(--sp-card)] space-y-4">
          <FolderKanban className="w-12 h-12 text-gray-500 mx-auto opacity-50" />
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-[var(--sp-text)]">No campaigns found</h3>
            <p className="text-sm text-gray-400">
              {statusFilter
                ? `No campaigns with status "${statusFilter}".`
                : 'Create your first marketing campaign to group posts and track progress.'}
            </p>
          </div>
          <button
            onClick={() => handleOpenModal()}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-xs font-medium rounded-lg hover:bg-indigo-500 transition-colors"
          >
            <Plus className="w-4 h-4" /> Create Campaign
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {campaigns.map((c) => (
            <div
              key={c.id}
              className="flex flex-col justify-between p-5 rounded-xl border border-[var(--sp-border)] bg-[var(--sp-card)] hover:border-indigo-500/40 transition-all shadow-sm group"
            >
              <div className="space-y-3">
                {/* Card Top */}
                <div className="flex items-start justify-between gap-2">
                  <div>
                    {getStatusBadge(c.status)}
                    <h3
                      onClick={() => navigate(`/dashboard/campaigns/${c.id}`)}
                      className="text-lg font-bold text-[var(--sp-text)] mt-2 hover:text-indigo-400 cursor-pointer transition-colors line-clamp-1"
                    >
                      {c.name}
                    </h3>
                  </div>
                  <div className="flex items-center gap-1 opacity-80 group-hover:opacity-100">
                    <button
                      onClick={() => handleOpenModal(c)}
                      className="p-1.5 text-gray-400 hover:text-indigo-400 hover:bg-[var(--sp-surface-2)] rounded-md transition-colors"
                      title="Edit Campaign"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(c.id, c.name)}
                      className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-md transition-colors"
                      title="Delete Campaign"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Description / Objective */}
                {c.objective && (
                  <div className="flex items-center gap-1.5 text-xs text-indigo-400 font-medium">
                    <Target className="w-3.5 h-3.5" />
                    <span className="truncate">{c.objective}</span>
                  </div>
                )}
                {c.description && (
                  <p className="text-xs text-gray-400 line-clamp-2 leading-relaxed">
                    {c.description}
                  </p>
                )}

                {/* Metadata List */}
                <div className="pt-2 border-t border-[var(--sp-border)] space-y-2 text-xs text-gray-400">
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5 text-gray-500" /> Date Range:
                    </span>
                    <span className="font-medium text-[var(--sp-text)]">
                      {c.start_date ? new Date(c.start_date).toLocaleDateString() : 'TBD'} –{' '}
                      {c.end_date ? new Date(c.end_date).toLocaleDateString() : 'TBD'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1">
                      <DollarSign className="w-3.5 h-3.5 text-gray-500" /> Budget:
                    </span>
                    <span className="font-medium text-[var(--sp-text)]">
                      ${c.budget ? c.budget.toLocaleString() : '0'}
                    </span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1">
                      <FileText className="w-3.5 h-3.5 text-gray-500" /> Post Count:
                    </span>
                    <span className="font-semibold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full">
                      {c.post_count} posts
                    </span>
                  </div>
                </div>

                {/* Target Platforms */}
                {c.target_platforms && c.target_platforms.length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-1">
                    {c.target_platforms.map((p) => (
                      <span
                        key={p}
                        className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded bg-[var(--sp-surface-2)] text-gray-300 border border-[var(--sp-border)]"
                      >
                        {p}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Bottom Action */}
              <button
                onClick={() => navigate(`/dashboard/campaigns/${c.id}`)}
                className="mt-4 w-full py-2 bg-[var(--sp-surface-2)] hover:bg-indigo-600 hover:text-white text-gray-300 text-xs font-medium rounded-lg flex items-center justify-center gap-1.5 transition-colors"
              >
                View Campaign Details <ExternalLink className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t border-[var(--sp-border)] text-xs">
          <button
            disabled={page === 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="px-3 py-1.5 rounded-md border border-[var(--sp-border)] bg-[var(--sp-card)] text-gray-300 hover:bg-[var(--sp-surface-2)] disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-gray-400">
            Page {page} of {totalPages}
          </span>
          <button
            disabled={page === totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            className="px-3 py-1.5 rounded-md border border-[var(--sp-border)] bg-[var(--sp-card)] text-gray-300 hover:bg-[var(--sp-surface-2)] disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}

      {/* Create / Edit Campaign Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-[var(--sp-card)] border border-[var(--sp-border)] rounded-2xl shadow-xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="px-6 py-4 border-b border-[var(--sp-border)] flex items-center justify-between">
              <h2 className="text-lg font-bold text-[var(--sp-text)] flex items-center gap-2">
                <FolderKanban className="w-5 h-5 text-indigo-500" />
                {editingCampaign ? 'Edit Campaign' : 'Create New Campaign'}
              </h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-gray-400 hover:text-gray-200 text-lg leading-none"
              >
                &times;
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4 text-xs">
              {formError && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-300">
                  {formError}
                </div>
              )}

              {/* Name */}
              <div className="space-y-1">
                <label className="font-semibold text-gray-300">Campaign Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Q3 Summer Product Launch"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--sp-surface-2)] border border-[var(--sp-border)] text-[var(--sp-text)] focus:border-indigo-500 focus:outline-none"
                />
              </div>

              {/* Objective */}
              <div className="space-y-1">
                <label className="font-semibold text-gray-300">Campaign Objective</label>
                <input
                  type="text"
                  placeholder="e.g. Lead Generation & Brand Awareness"
                  value={formData.objective}
                  onChange={(e) => setFormData({ ...formData, objective: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--sp-surface-2)] border border-[var(--sp-border)] text-[var(--sp-text)] focus:border-indigo-500 focus:outline-none"
                />
              </div>

              {/* Description */}
              <div className="space-y-1">
                <label className="font-semibold text-gray-300">Description</label>
                <textarea
                  rows={3}
                  placeholder="Provide campaign notes, goals, or guidelines..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-[var(--sp-surface-2)] border border-[var(--sp-border)] text-[var(--sp-text)] focus:border-indigo-500 focus:outline-none"
                />
              </div>

              {/* Target Platforms */}
              <div className="space-y-1">
                <label className="font-semibold text-gray-300">Target Platforms</label>
                <div className="grid grid-cols-3 gap-2 pt-1">
                  {PLATFORMS.map((p) => {
                    const isSelected = formData.target_platforms.includes(p.id);
                    return (
                      <button
                        type="button"
                        key={p.id}
                        onClick={() => handlePlatformToggle(p.id)}
                        className={`px-2.5 py-1.5 rounded-lg border text-left flex items-center justify-between transition-colors ${
                          isSelected
                            ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300'
                            : 'bg-[var(--sp-surface-2)] border-[var(--sp-border)] text-gray-400 hover:text-gray-200'
                        }`}
                      >
                        <span>{p.label}</span>
                        {isSelected && <CheckCircle2 className="w-3.5 h-3.5 text-indigo-400" />}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Dates */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="font-semibold text-gray-300">Start Date</label>
                  <input
                    type="date"
                    value={formData.start_date}
                    onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-[var(--sp-surface-2)] border border-[var(--sp-border)] text-[var(--sp-text)] focus:border-indigo-500 focus:outline-none"
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-semibold text-gray-300">End Date</label>
                  <input
                    type="date"
                    value={formData.end_date}
                    onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-[var(--sp-surface-2)] border border-[var(--sp-border)] text-[var(--sp-text)] focus:border-indigo-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* Budget & Status */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="font-semibold text-gray-300">Budget ($)</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={formData.budget}
                    onChange={(e) => setFormData({ ...formData, budget: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-[var(--sp-surface-2)] border border-[var(--sp-border)] text-[var(--sp-text)] focus:border-indigo-500 focus:outline-none"
                  />
                </div>

                <div className="space-y-1">
                  <label className="font-semibold text-gray-300">Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full px-3 py-2 rounded-lg bg-[var(--sp-surface-2)] border border-[var(--sp-border)] text-[var(--sp-text)] focus:border-indigo-500 focus:outline-none"
                  >
                    <option value="draft">Draft</option>
                    <option value="active">Active</option>
                    <option value="paused">Paused</option>
                    <option value="completed">Completed</option>
                    <option value="archived">Archived</option>
                  </select>
                </div>
              </div>

              {/* Modal Footer */}
              <div className="pt-4 flex items-center justify-end gap-2 border-t border-[var(--sp-border)]">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-lg border border-[var(--sp-border)] text-gray-300 hover:bg-[var(--sp-surface-2)] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={modalLoading}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-lg flex items-center gap-2 transition-colors disabled:opacity-50"
                >
                  {modalLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                  {editingCampaign ? 'Save Changes' : 'Create Campaign'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
