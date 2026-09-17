import React, { useState, useEffect, useId } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { teamsAPI } from '../lib/api';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import {
  Users,
  Plus,
  Loader2,
  AlertCircle,
  X,
  FileText,
  Clock,
  Layout,
  Crown,
  ChevronRight,
  RefreshCw,
} from 'lucide-react';

/* ─────────────────────────────────────────────────────────
   SKELETON LOADER
───────────────────────────────────────────────────────── */
const SkeletonCard = () => (
  <div className="sp-card p-5 space-y-4 animate-pulse">
    <div className="flex items-center gap-3">
      <div className="h-10 w-10 rounded-xl" style={{ background: 'var(--sp-border)' }} />
      <div className="flex-1 space-y-2">
        <div className="h-3.5 rounded w-1/2" style={{ background: 'var(--sp-border)' }} />
        <div className="h-2.5 rounded w-1/3" style={{ background: 'var(--sp-border)' }} />
      </div>
    </div>
  </div>
);


/* ─────────────────────────────────────────────────────────
   TEAMS LIST PAGE
───────────────────────────────────────────────────────── */
export const TeamsPage = () => {
  const { user } = useAuth();
  const modalNameId = useId();
  const modalDescId = useId();

  // State
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Modal State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [modalSubmitting, setModalSubmitting] = useState(false);
  const [modalError, setModalError] = useState(null);

  const fetchTeams = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await teamsAPI.list();
      setTeams(res.data);
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(
        typeof d === 'string' ? d :
        Array.isArray(d) ? d.map((x) => x.msg).join(' \u00b7 ') :
        err.message || 'Failed to retrieve teams.'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTeams();
  }, []);

  const handleCreateTeam = async (e) => {
    e.preventDefault();
    if (!newName.trim()) {
      setModalError('Workspace name is required');
      return;
    }

    setModalSubmitting(true);
    setModalError(null);
    try {
      const res = await teamsAPI.create({
        name: newName.trim(),
        description: newDesc.trim() || undefined,
      });
      setSuccessMsg(`Workspace "${res.data.name}" created successfully!`);
      setNewName('');
      setNewDesc('');
      setShowCreateModal(false);
      fetchTeams();
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err) {
      const d = err.response?.data?.detail;
      setModalError(
        typeof d === 'string' ? d :
        Array.isArray(d) ? d.map((x) => x.msg).join(' \u00b7 ') :
        err.message || 'Failed to create workspace.'
      );
    } finally {
      setModalSubmitting(false);
    }
  };

  return (
    <>
      <div className="space-y-6 animate-sp-fade-in-up">
        {/* Header Section */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h1 className="text-xl sm:text-2xl font-extrabold tracking-tight text-slate-900 dark:text-slate-50 font-heading flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-tr from-violet-600 to-blue-500 text-white shadow-sm shadow-violet-500/25">
                <Users className="h-4 w-4" aria-hidden="true" />
              </span>
              Teams & Workspaces
            </h1>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Organise, collaborate, and manage shared social accounts with your marketing teams.
            </p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              type="button"
              onClick={fetchTeams}
              aria-label="Refresh workspaces"
              title="Refresh"
              className="flex items-center justify-center h-9 w-9 rounded-xl border border-slate-200/80 dark:border-slate-800/50 bg-white dark:bg-[#0D1426] text-slate-500 dark:text-slate-400 hover:text-violet-600 dark:hover:text-violet-400 hover:border-violet-500/40 transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
            </button>
            <Button
              variant="primary"
              size="sm"
              icon={Plus}
              onClick={() => {
                setModalError(null);
                setShowCreateModal(true);
              }}
            >
              Create Team
            </Button>
          </div>
        </div>

        {/* Global Feedback Banner */}
        {successMsg && (
          <div
            role="status"
            aria-live="polite"
            className="flex items-center gap-2.5 rounded-xl border border-emerald-250 bg-emerald-50 dark:bg-emerald-500/10 dark:border-emerald-500/20 px-4 py-3 text-sm font-semibold text-emerald-800 dark:text-emerald-400"
          >
            <CheckCircleIcon className="h-4.5 w-4.5 text-emerald-600" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* API Error Box */}
        {error && (
          <div
            role="alert"
            className="flex items-start gap-3 rounded-2xl border border-rose-200/80 dark:border-rose-500/25 bg-rose-50 dark:bg-rose-500/10 p-5 text-sm text-rose-800 dark:text-rose-300"
          >
            <AlertCircle className="h-5 w-5 flex-shrink-0 mt-px" aria-hidden="true" />
            <div className="flex-1">
              <p className="font-bold">Failed to load workspaces</p>
              <p className="text-xs mt-0.5 opacity-80">{error}</p>
            </div>
            <Button variant="ghost" size="sm" icon={RefreshCw} onClick={fetchTeams}>
              Retry
            </Button>
          </div>
        )}

        {/* Workspaces Grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : teams.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-slate-200 dark:border-slate-805 p-12 text-center max-w-lg mx-auto space-y-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-50 dark:bg-slate-800/40 mx-auto text-slate-350 dark:text-slate-650">
              <Layout className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-800 dark:text-slate-200">No workspaces yet</p>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-1 leading-relaxed">
                Create a shared workspace to collaborate on content composition and manage social profiles as a team.
              </p>
            </div>
            <Button variant="outline" size="sm" icon={Plus} onClick={() => setShowCreateModal(true)}>
              Create First Workspace
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
            {teams.map((team) => {
              const isOwner = team.owner_id === user?.id;
              return (
                <div
                  key={team.id}
                  className="sp-card group p-5 flex flex-col justify-between transition-all duration-200"
                >
                  <div className="space-y-3.5">
                    {/* Upper row: Avatar & Owner Badge */}
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500/10 to-blue-500/10 dark:from-violet-500/15 dark:to-blue-500/15 border border-violet-500/10 text-violet-600 dark:text-violet-400 font-extrabold text-lg select-none">
                        {team.name.charAt(0).toUpperCase()}
                      </div>
                      <Badge variant={isOwner ? 'success' : 'neutral'} size="xs" showDot={false}>
                        {isOwner ? (
                          <span className="flex items-center gap-1">
                            <Crown className="h-3 w-3" />
                            Owner
                          </span>
                        ) : (
                          'Member'
                        )}
                      </Badge>
                    </div>

                    {/* Metadata details */}
                    <div>
                      <h2 className="text-sm font-bold font-heading transition-colors" style={{ color: 'var(--sp-text)' }}>
                        {team.name}
                      </h2>
                      <p className="text-xs mt-1 leading-relaxed line-clamp-2 min-h-[2rem]" style={{ color: 'var(--sp-text-secondary)' }}>
                        {team.description || <span className="italic text-slate-350 dark:text-slate-650">No description provided.</span>}
                      </p>
                    </div>
                  </div>

                  {/* Card bottom: Details Link */}
                  <div className="mt-5 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400 dark:text-slate-600">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      Updated {new Date(team.updated_at).toLocaleDateString()}
                    </span>
                    <Link
                      to={`/dashboard/teams/${team.id}`}
                      className="font-bold text-violet-605 dark:text-violet-400 hover:underline flex items-center gap-0.5"
                    >
                      Manage Workspace
                      <ChevronRight className="h-3 w-3" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* CREATE WORKSPACE DIALOG MODAL */}
      {showCreateModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="create-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
        >
          <div
            className="absolute inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-sm"
            onClick={() => setShowCreateModal(false)}
            aria-hidden="true"
          />
          <div className="sp-card relative w-full max-w-md p-6 shadow-2xl space-y-4 animate-sp-fade-in-up">
            <div className="flex items-center justify-between">
              <h3 id="create-modal-title" className="text-base font-bold font-heading" style={{ color: 'var(--sp-text)' }}>
                Create Workspace Team
              </h3>
              <button
                onClick={() => setShowCreateModal(false)}
                aria-label="Close dialog"
                className="rounded-lg p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
              >
                <X className="h-4.5 w-4.5" aria-hidden="true" />
              </button>
            </div>

            <form onSubmit={handleCreateTeam} className="space-y-4">
              <div>
                <label htmlFor={modalNameId} className="block text-xs font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-1.5">
                  Workspace Name
                </label>
                <input
                  id={modalNameId}
                  type="text"
                  required
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="E.g. Marketing Dept, Client Brand X"
                  maxLength={100}
                  className="w-full rounded-xl border border-slate-200/80 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/30 px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:border-violet-500/60 focus:bg-white dark:focus:bg-slate-800/60 focus:outline-none focus:ring-2 focus:ring-violet-500/15 transition-all"
                />
              </div>

              <div>
                <label htmlFor={modalDescId} className="block text-xs font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-1.5">
                  Description (optional)
                </label>
                <textarea
                  id={modalDescId}
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Enter workspace description or purpose..."
                  rows={3}
                  className="w-full rounded-xl border border-slate-200/80 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/30 px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-600 focus:border-violet-500/60 focus:bg-white dark:focus:bg-slate-800/60 focus:outline-none focus:ring-2 focus:ring-violet-500/15 transition-all resize-none"
                />
              </div>

              {modalError && (
                <div role="alert" className="flex items-start gap-2 rounded-lg border border-rose-200 dark:border-rose-500/25 bg-rose-50 dark:bg-rose-500/10 px-3 py-2 text-xs text-rose-700 dark:text-rose-450">
                  <AlertCircle className="h-3.5 w-3.5 flex-shrink-0 mt-px" aria-hidden="true" />
                  <span>{modalError}</span>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800/80">
                <Button variant="ghost" size="sm" type="button" onClick={() => setShowCreateModal(false)} disabled={modalSubmitting}>
                  Cancel
                </Button>
                <Button variant="primary" size="sm" type="submit" isLoading={modalSubmitting}>
                  Create Workspace
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
};

const CheckCircleIcon = (props) => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" {...props}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);
