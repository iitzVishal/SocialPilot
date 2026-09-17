import React, { useState, useEffect, useCallback, useId } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { teamsAPI } from '../lib/api';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import {
  Users,
  ChevronLeft,
  Crown,
  Trash2,
  Edit2,
  Plus,
  Loader2,
  AlertCircle,
  X,
  UserPlus,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  Trash,
  LogOut,
  Mail,
  Activity,
  Clock,
  RefreshCw,
} from 'lucide-react';

const ROLE_META = {
  administrator:  { label: 'Team Admin',        variant: 'primary',  color: 'text-violet-600 dark:text-violet-400' },
  marketing_team: { label: 'Marketing Team',    variant: 'success',  color: 'text-emerald-600 dark:text-emerald-400' },
  business_user:  { label: 'Business Partner',  variant: 'warning',  color: 'text-amber-600 dark:text-amber-400' },
  content_creator:{ label: 'Content Creator',   variant: 'neutral',  color: 'text-slate-650 dark:text-slate-400' },
};

const ACTION_META = {
  team_create: { label: 'Workspace Created', variant: 'success' },
  team_update: { label: 'Workspace Updated', variant: 'info' },
  member_add: { label: 'Member Added', variant: 'success' },
  member_remove: { label: 'Member Removed', variant: 'danger' },
  member_role_change: { label: 'Role Updated', variant: 'warning' },
  invitation_create: { label: 'Invitation Sent', variant: 'warning' },
  invitation_accept: { label: 'Invitation Accepted', variant: 'success' },
  invitation_reject: { label: 'Invitation Rejected', variant: 'danger' },
  invitation_cancel: { label: 'Invitation Cancelled', variant: 'neutral' },
};

const formatRelativeTime = (isoString) => {
  if (!isoString) return '';
  const date = new Date(isoString);
  const now = new Date();
  const seconds = Math.floor((now - date) / 1000);
  if (seconds < 60) return 'Just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return date.toLocaleDateString();
};

export const TeamDetailPage = () => {
  const { teamId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const addEmailId = useId();
  const addRoleId = useId();
  const editNameId = useId();
  const editDescId = useId();

  // API State
  const [team, setTeam] = useState(null);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Success Feedback Message
  const [feedbackMsg, setFeedbackMsg] = useState(null);

  // Edit Team Modal
  const [showEditModal, setShowEditModal] = useState(false);
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editRequireApproval, setEditRequireApproval] = useState(false);
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [editError, setEditError] = useState(null);

  // Delete Confirm Modal
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);

  // Add Member Modal
  const [showAddModal, setShowAddModal] = useState(false);
  const [addEmail, setAddEmail] = useState('');
  const [addRole, setAddRole] = useState('content_creator');
  const [addSubmitting, setAddSubmitting] = useState(false);
  const [addError, setAddError] = useState(null);

  // Remove Member Confirm Modal
  const [memberToRemove, setMemberToRemove] = useState(null); // TeamMember object
  const [removeSubmitting, setRemoveSubmitting] = useState(false);

  // Invite Member Modal
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('content_creator');
  const [inviteSubmitting, setInviteSubmitting] = useState(false);
  const [inviteError, setInviteError] = useState(null);
  const [generatedLink, setGeneratedLink] = useState(null);
  const [invitations, setInvitations] = useState([]);

  // Tab & Workspace Activity Log State
  const [activeTab, setActiveTab] = useState('members');
  const [activityItems, setActivityItems] = useState([]);
  const [activityLoading, setActivityLoading] = useState(false);
  const [activityError, setActivityError] = useState(null);
  const [activityPage, setActivityPage] = useState(1);
  const [activityTotalPages, setActivityTotalPages] = useState(1);
  const [activityTotal, setActivityTotal] = useState(0);

  const loadActivity = useCallback(async (page = 1) => {
    setActivityLoading(true);
    setActivityError(null);
    try {
      const res = await teamsAPI.listActivity(teamId, { page, limit: 10 });
      setActivityItems(res.data.items || []);
      setActivityPage(res.data.page || 1);
      setActivityTotalPages(res.data.total_pages || 1);
      setActivityTotal(res.data.total || 0);
    } catch (err) {
      console.error('Failed to load workspace activity:', err);
      setActivityError(err.response?.data?.detail || 'Failed to load workspace activity log.');
    } finally {
      setActivityLoading(false);
    }
  }, [teamId]);

  useEffect(() => {
    if (activeTab === 'activity') {
      loadActivity(activityPage);
    }
  }, [activeTab, activityPage, loadActivity]);

  const loadTeamData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [teamRes, membersRes, invitesRes] = await Promise.all([
        teamsAPI.get(teamId),
        teamsAPI.listMembers(teamId),
        teamsAPI.listInvitations(teamId).catch(() => ({ data: [] })),
      ]);
      setTeam(teamRes.data);
      setMembers(membersRes.data);
      setInvitations(invitesRes.data);
      setEditName(teamRes.data.name);
      setEditDesc(teamRes.data.description || '');
      setEditRequireApproval(teamRes.data.require_post_approval || false);
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(
        typeof d === 'string' ? d :
        Array.isArray(d) ? d.map((x) => x.msg).join(' \u00b7 ') :
        err.message || 'Failed to retrieve workspace data.'
      );
    } finally {
      setLoading(false);
    }
  }, [teamId]);

  useEffect(() => {
    loadTeamData();
  }, [loadTeamData]);

  // Auth helper checks
  const isOwner = team && team.owner_id === user?.id;
  const isSystemAdmin = user?.role === 'administrator';
  const myMembership = members.find((m) => m.user_id === user?.id);
  const isTeamAdmin = myMembership && myMembership.role === 'administrator';
  const canManage = isOwner || isTeamAdmin || isSystemAdmin;

  const showFeedback = (msg) => {
    setFeedbackMsg(msg);
    setTimeout(() => setFeedbackMsg(null), 3500);
  };

  // Edit Team handler
  const handleEditTeam = async (e) => {
    e.preventDefault();
    if (!editName.trim()) {
      setEditError('Team name is required');
      return;
    }
    setEditSubmitting(true);
    setEditError(null);
    try {
      const res = await teamsAPI.update(teamId, {
        name: editName.trim(),
        description: editDesc.trim() || undefined,
        require_post_approval: editRequireApproval,
      });
      setTeam(res.data);
      setShowEditModal(false);
      showFeedback('Workspace details updated successfully!');
    } catch (err) {
      setEditError(err.response?.data?.detail || 'Failed to update workspace.');
    } finally {
      setEditSubmitting(false);
    }
  };

  // Delete Team handler
  const handleDeleteTeam = async () => {
    setDeleteSubmitting(true);
    try {
      await teamsAPI.delete(teamId);
      navigate('/dashboard/teams');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete workspace.');
      setShowDeleteModal(false);
    } finally {
      setDeleteSubmitting(false);
    }
  };

  // Add member handler
  const handleAddMember = async (e) => {
    e.preventDefault();
    if (!addEmail.trim()) {
      setAddError('User email address is required');
      return;
    }
    setAddSubmitting(true);
    setAddError(null);
    try {
      await teamsAPI.addMember(teamId, {
        email: addEmail.trim(),
        role: addRole,
      });
      setAddEmail('');
      setShowAddModal(false);
      showFeedback('Team member added successfully!');
      loadTeamData();
    } catch (err) {
      const d = err.response?.data?.detail;
      setAddError(
        typeof d === 'string' ? d :
        Array.isArray(d) ? d.map((x) => x.msg).join(' \u00b7 ') :
        err.message || 'Failed to add workspace member.'
      );
    } finally {
      setAddSubmitting(false);
    }
  };

  // Change member role
  const handleChangeRole = async (targetUserId, newRole) => {
    try {
      await teamsAPI.updateMemberRole(teamId, targetUserId, newRole);
      showFeedback('Member role updated successfully!');
      loadTeamData();
    } catch (err) {
      showFeedback(`Error updating role: ${err.response?.data?.detail || 'API error'}`);
    }
  };

  // Remove member handler
  const handleRemoveMember = async () => {
    if (!memberToRemove) return;
    setRemoveSubmitting(true);
    try {
      const isLeaving = memberToRemove.user_id === user?.id;
      await teamsAPI.removeMember(teamId, memberToRemove.user_id);
      setMemberToRemove(null);
      if (isLeaving) {
        navigate('/dashboard/teams');
      } else {
        showFeedback('Member removed from team.');
        loadTeamData();
      }
    } catch (err) {
      showFeedback(`Error: ${err.response?.data?.detail || 'Failed to remove member'}`);
      setMemberToRemove(null);
    } finally {
      setRemoveSubmitting(false);
    }
  };

  const handleCancelInvitation = async (invitationId) => {
    try {
      await teamsAPI.cancelInvitation(teamId, invitationId);
      loadTeamData();
      showFeedback('Invitation cancelled successfully.');
    } catch (err) {
      showFeedback(`Error: ${err.response?.data?.detail || 'Failed to cancel invitation'}`);
    }
  };

  const handleInviteSubmit = async (e) => {
    e.preventDefault();
    if (!inviteEmail.trim()) {
      setInviteError('User email address is required');
      return;
    }
    setInviteSubmitting(true);
    setInviteError(null);
    setGeneratedLink(null);
    try {
      const res = await teamsAPI.createInvitation(teamId, {
        email: inviteEmail.trim(),
        role: inviteRole,
      });
      const token = res.data.token;
      if (token) {
        const link = `${window.location.origin}/invite/${token}`;
        setGeneratedLink(link);
      }
      setInviteEmail('');
      showFeedback('Invitation created successfully!');
      loadTeamData();
    } catch (err) {
      const d = err.response?.data?.detail;
      setInviteError(
        typeof d === 'string' ? d :
        Array.isArray(d) ? d.map((x) => x.msg).join(' \u00b7 ') :
        err.message || 'Failed to create team invitation.'
      );
    } finally {
      setInviteSubmitting(false);
    }
  };

  if (loading && !team) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-slate-400 dark:text-slate-500 gap-3">
        <Loader2 className="h-7 w-7 animate-spin text-violet-500" aria-hidden="true" />
        <span className="text-xs font-semibold">Syncing workspace workspace...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div role="alert" className="flex items-start gap-3 rounded-2xl border border-rose-250 bg-rose-50 dark:bg-rose-500/10 p-6 text-sm text-rose-800 dark:text-rose-300">
        <AlertCircle className="h-5 w-5 flex-shrink-0 mt-px" aria-hidden="true" />
        <div className="flex-1">
          <p className="font-bold">Failed to load workspace details</p>
          <p className="text-xs mt-0.5 opacity-80">{error}</p>
          <div className="mt-3 flex gap-2">
            <Link to="/dashboard/teams">
              <Button variant="ghost" size="xs">
                &larr; Back to Workspaces
              </Button>
            </Link>
            <Button variant="outline" size="xs" icon={Plus} onClick={loadTeamData}>
              Retry Load
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-6 animate-sp-fade-in-up">
        {/* Back Link */}
        <Link
          to="/dashboard/teams"
          className="inline-flex items-center gap-1 text-xs font-bold text-slate-450 dark:text-slate-400 hover:text-violet-605 dark:hover:text-violet-400 hover:underline"
        >
          <ChevronLeft className="h-4 w-4" />
          Back to Workspaces
        </Link>

        {/* Global Feedback Banner */}
        {feedbackMsg && (
          <div
            role="status"
            aria-live="polite"
            className="flex items-center gap-2.5 rounded-xl border border-emerald-250 bg-emerald-50 dark:bg-emerald-500/10 dark:border-emerald-500/20 px-4 py-3 text-sm font-semibold text-emerald-800 dark:text-emerald-400"
          >
            <CheckCircle2 className="h-4.5 w-4.5 text-emerald-600" />
            <span>{feedbackMsg}</span>
          </div>
        )}

        {/* Workspace Card Header */}
        <div className="sp-card p-5 sm:p-6 shadow-sm flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500/10 to-blue-500/10 dark:from-violet-500/15 dark:to-blue-500/15 border border-violet-500/10 text-violet-600 dark:text-violet-400 font-extrabold text-2xl select-none flex-shrink-0">
              {team?.name.charAt(0).toUpperCase()}
            </div>
            <div>
              <h1 className="text-lg sm:text-xl font-extrabold text-slate-900 dark:text-slate-50 font-heading flex flex-wrap items-center gap-2">
                {team?.name}
                {team?.require_post_approval && (
                  <Badge variant="warning" size="xs">Requires Approvals</Badge>
                )}
              </h1>
              <p className="text-xs text-slate-400 dark:text-slate-550 mt-1 max-w-2xl leading-relaxed">
                {team?.description || <span className="italic">No description provided.</span>}
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate-450 dark:text-slate-500">
                <span className="flex items-center gap-1">
                  <Crown className="h-3.5 w-3.5 text-amber-500" />
                  Owner ID: {team?.owner_id} {isOwner && '(You)'}
                </span>
                <span>&bull;</span>
                <span>Created on {new Date(team?.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          </div>

          {/* Action Header controls */}
          <div className="flex items-center gap-2">
            {(isOwner || isSystemAdmin) && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  icon={Edit2}
                  onClick={() => {
                    setEditError(null);
                    setShowEditModal(true);
                  }}
                >
                  Edit
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  icon={Trash2}
                  onClick={() => setShowDeleteModal(true)}
                >
                  Delete Team
                </Button>
              </>
            )}
            {!isOwner && (
              <Button
                variant="danger"
                size="sm"
                icon={LogOut}
                onClick={() => setMemberToRemove(myMembership)}
              >
                Leave Team
              </Button>
            )}
          </div>
        </div>

        {/* Sub-Navigation Tabs */}
        <div className="flex border-b" style={{ borderColor: 'var(--sp-border)' }}>
          <button
            type="button"
            onClick={() => setActiveTab('members')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold font-heading border-b-2 transition-all cursor-pointer ${
              activeTab === 'members'
                ? 'border-emerald-500 text-emerald-500'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Users className="h-4 w-4" />
            Members & Invitations ({members.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('activity')}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold font-heading border-b-2 transition-all cursor-pointer ${
              activeTab === 'activity'
                ? 'border-emerald-500 text-emerald-500'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Activity className="h-4 w-4" />
            Workspace Activity Log {activityTotal > 0 && `(${activityTotal})`}
          </button>
        </div>

        {/* Members & Invitations Tab Content */}
        {activeTab === 'members' && (
          <>
            {/* Team Members List */}
            <section
              className="sp-card p-5 shadow-sm space-y-4"
              aria-labelledby="members-section-title"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-slate-800/80">
                <h2 id="members-section-title" className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5 font-heading">
                  <Users className="h-4 w-4 text-slate-400" />
                  Workspace Members ({members.length})
                </h2>
                {canManage && (
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      icon={Mail}
                      onClick={() => {
                        setInviteError(null);
                        setGeneratedLink(null);
                        setInviteEmail('');
                        setInviteRole('content_creator');
                        setShowInviteModal(true);
                      }}
                    >
                      Invite Member
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      icon={UserPlus}
                      onClick={() => {
                        setAddError(null);
                        setShowAddModal(true);
                      }}
                    >
                      Add Direct
                    </Button>
                  </div>
                )}
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="text-slate-400 dark:text-slate-550 font-bold border-b border-slate-100 dark:border-slate-800/60">
                      <th className="py-2.5 pl-2">User details</th>
                      <th className="py-2.5">Workspace Role</th>
                      <th className="py-2.5">Joined date</th>
                      {canManage && <th className="py-2.5 pr-2 text-right">Actions</th>}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800/40">
                    {members.map((member) => {
                      const mMeta = ROLE_META[member.role] ?? { label: member.role, variant: 'neutral' };
                      const isMemberOwner = member.user_id === team?.owner_id;
                      const isMe = member.user_id === user?.id;

                      return (
                        <tr key={member.id} className="group hover:bg-slate-50/50 dark:hover:bg-slate-800/10">
                          <td className="py-3 pl-2 flex items-center gap-2">
                            <div className="h-7 w-7 rounded-full bg-gradient-to-br from-violet-600 to-blue-500 text-white font-extrabold text-[10px] flex items-center justify-center">
                              {member.user.full_name?.charAt(0).toUpperCase() || member.user.email.charAt(0).toUpperCase()}
                            </div>
                            <div>
                              <p className="font-bold text-slate-800 dark:text-slate-100 flex items-center gap-1">
                                {member.user.full_name || <span className="italic text-slate-400">Unnamed User</span>}
                                {isMe && <span className="text-[10px] text-slate-400 font-normal">(You)</span>}
                              </p>
                              <p className="text-[10px] text-slate-455 dark:text-slate-500">{member.user.email}</p>
                            </div>
                          </td>
                          <td className="py-3">
                            {canManage && !isMemberOwner && !isMe ? (
                              <div className="flex items-center gap-2">
                                <select
                                  value={member.role}
                                  onChange={(e) => handleChangeRole(member.user_id, e.target.value)}
                                  className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/30 px-2 py-1 text-[11px] text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-1 focus:ring-violet-500 cursor-pointer"
                                >
                                  <option value="content_creator">Content Creator</option>
                                  <option value="business_user">Business Partner</option>
                                  <option value="marketing_team">Marketing Team</option>
                                  <option value="administrator">Team Admin</option>
                                </select>
                              </div>
                            ) : (
                              <Badge variant={mMeta.variant} size="xs" showDot={false}>
                                {isMemberOwner && <Crown className="inline h-3 w-3 mr-0.5 text-amber-500" />}
                                {mMeta.label}
                              </Badge>
                            )}
                          </td>
                          <td className="py-3 text-slate-450 dark:text-slate-500">
                            {new Date(member.created_at).toLocaleDateString()}
                          </td>
                          {canManage && (
                            <td className="py-3 pr-2 text-right">
                              {!isMemberOwner && !isMe && (
                                <button
                                  type="button"
                                  onClick={() => setMemberToRemove(member)}
                                  title="Remove member from team"
                                  className="rounded p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10 cursor-pointer transition-colors"
                                >
                                  <Trash className="h-3.5 w-3.5" />
                                </button>
                              )}
                            </td>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>

            {/* Pending Invitations List */}
            {canManage && invitations.length > 0 && (
              <section
                className="sp-card p-5 shadow-sm space-y-4"
                aria-labelledby="invitations-section-title"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-slate-800/80">
                  <h2 id="invitations-section-title" className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5 font-heading">
                    <Mail className="h-4 w-4 text-slate-400" />
                    Workspace Invitations ({invitations.length})
                  </h2>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="text-slate-400 dark:text-slate-550 font-bold border-b border-slate-100 dark:border-slate-800/60">
                        <th className="py-2.5 pl-2">Invited Email</th>
                        <th className="py-2.5">Role</th>
                        <th className="py-2.5">Status</th>
                        <th className="py-2.5">Invited At</th>
                        <th className="py-2.5 pr-2 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800/40">
                      {invitations.map((invite) => {
                        const statusMeta = {
                          pending:   { variant: 'warning', label: 'Queued' },
                          accepted:  { variant: 'success', label: 'Accepted' },
                          rejected:  { variant: 'danger',  label: 'Rejected' },
                          expired:   { variant: 'neutral', label: 'Expired' },
                          cancelled: { variant: 'neutral', label: 'Cancelled' },
                        }[invite.status] ?? { variant: 'neutral', label: invite.status };

                        const roleMeta = ROLE_META[invite.role] ?? { label: invite.role, variant: 'neutral' };

                        return (
                          <tr key={invite.id} className="group hover:bg-slate-50/50 dark:hover:bg-slate-800/10">
                            <td className="py-3 pl-2 font-bold text-slate-800 dark:text-slate-100">
                              {invite.email}
                            </td>
                            <td className="py-3">
                              <Badge variant={roleMeta.variant} size="xs" showDot={false}>
                                {roleMeta.label}
                              </Badge>
                            </td>
                            <td className="py-3">
                              <Badge variant={statusMeta.variant} size="xs" showDot={false}>
                                {statusMeta.label}
                              </Badge>
                            </td>
                            <td className="py-3 text-slate-455 dark:text-slate-500">
                              {new Date(invite.created_at).toLocaleDateString()}
                            </td>
                            <td className="py-3 pr-2 text-right">
                              {invite.status === 'pending' && (
                                <button
                                  type="button"
                                  onClick={() => handleCancelInvitation(invite.id)}
                                  title="Cancel invitation"
                                  className="rounded px-2.5 py-1 text-xs font-bold text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-500/10 cursor-pointer transition-colors"
                                >
                                  Cancel
                                </button>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </section>
            )}
          </>
        )}

        {/* Workspace Activity Audit Feed Section */}
        {activeTab === 'activity' && (
          <section className="sp-card p-5 shadow-sm space-y-4" aria-labelledby="activity-section-title">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-slate-800/80">
              <h2 id="activity-section-title" className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5 font-heading">
                <Activity className="h-4 w-4 text-emerald-500" />
                Workspace Activity Audit Log {activityTotal > 0 && `(${activityTotal} Events)`}
              </h2>
              <Button
                variant="outline"
                size="xs"
                icon={RefreshCw}
                onClick={() => loadActivity(activityPage)}
                isLoading={activityLoading}
              >
                Refresh Log
              </Button>
            </div>

            {/* Error State */}
            {activityError && (
              <div role="alert" className="flex items-start gap-3 rounded-xl border border-rose-500/20 bg-rose-500/10 p-4 text-xs text-rose-600 dark:text-rose-400">
                <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="font-bold">Failed to load activity log</p>
                  <p className="opacity-80 mt-0.5">{activityError}</p>
                </div>
                <Button variant="outline" size="xs" onClick={() => loadActivity(activityPage)}>Retry</Button>
              </div>
            )}

            {/* Loading State */}
            {activityLoading && activityItems.length === 0 && (
              <div className="flex flex-col items-center justify-center py-12 text-slate-400 gap-2">
                <Loader2 className="h-6 w-6 animate-spin text-emerald-500" />
                <span className="text-xs font-semibold">Loading workspace activity log...</span>
              </div>
            )}

            {/* Empty State */}
            {!activityLoading && !activityError && activityItems.length === 0 && (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100 dark:bg-slate-800/60 text-slate-400 mb-3">
                  <Clock className="h-6 w-6" />
                </div>
                <p className="text-sm font-bold text-slate-800 dark:text-slate-200">No activity recorded yet</p>
                <p className="text-xs text-slate-400 mt-1 max-w-sm">Workspace events like invitation dispatches, member role changes, and workspace updates will appear here.</p>
              </div>
            )}

            {/* Activity Feed Items List */}
            {activityItems.length > 0 && (
              <div className="divide-y divide-slate-100 dark:divide-slate-800/40">
                {activityItems.map((item) => {
                  const actMeta = ACTION_META[item.action] || { label: item.action, variant: 'neutral' };
                  const actorInitial = item.actor_name ? item.actor_name.charAt(0).toUpperCase() : 'S';

                  return (
                    <div key={item.id} className="py-3.5 flex items-start justify-between gap-3 group hover:bg-slate-50/50 dark:hover:bg-slate-800/10 px-2 rounded-xl transition-colors">
                      <div className="flex items-start gap-3">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-emerald-500/20 to-teal-500/20 text-emerald-500 font-extrabold text-xs flex-shrink-0 mt-0.5 border border-emerald-500/20">
                          {actorInitial}
                        </div>
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-xs font-bold text-slate-900 dark:text-slate-100 font-heading">
                              {item.actor_name}
                            </span>
                            <Badge variant={actMeta.variant} size="xs" showDot={false}>
                              {actMeta.label}
                            </Badge>
                          </div>
                          <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 leading-relaxed">
                            {item.description}
                          </p>
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0" title={item.created_at ? new Date(item.created_at).toLocaleString() : ''}>
                        <span className="text-[11px] font-medium text-slate-400 dark:text-slate-500">
                          {formatRelativeTime(item.created_at)}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Pagination Controls */}
            {activityTotalPages > 1 && (
              <div className="flex items-center justify-between pt-4 border-t border-slate-100 dark:border-slate-800/80">
                <Button
                  variant="outline"
                  size="xs"
                  disabled={activityPage <= 1 || activityLoading}
                  onClick={() => loadActivity(activityPage - 1)}
                >
                  Previous
                </Button>
                <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                  Page {activityPage} of {activityTotalPages}
                </span>
                <Button
                  variant="outline"
                  size="xs"
                  disabled={activityPage >= activityTotalPages || activityLoading}
                  onClick={() => loadActivity(activityPage + 1)}
                >
                  Next
                </Button>
              </div>
            )}
          </section>
        )}
      </div>

      {/* EDIT TEAM MODAL */}
      {showEditModal && (
        <div role="dialog" aria-modal="true" aria-labelledby="edit-modal-title" className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-sm" onClick={() => setShowEditModal(false)} aria-hidden="true" />
          <div className="sp-card relative w-full max-w-md p-6 shadow-2xl space-y-4 animate-sp-fade-in-up">
            <div className="flex items-center justify-between">
              <h3 id="edit-modal-title" className="text-base font-bold text-slate-900 dark:text-slate-100 font-heading">
                Edit Workspace Details
              </h3>
              <button onClick={() => setShowEditModal(false)} className="rounded-lg p-1 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer">
                <X className="h-4.5 w-4.5" />
              </button>
            </div>

            <form onSubmit={handleEditTeam} className="space-y-4">
              <div>
                <label htmlFor={editNameId} className="block text-xs font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-1.5">
                  Workspace Name
                </label>
                <input
                  id={editNameId}
                  type="text"
                  required
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full rounded-xl border border-slate-200/80 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/30 px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/15 focus:border-violet-500/65"
                />
              </div>

              <div>
                <label htmlFor={editDescId} className="block text-xs font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-1.5">
                  Description
                </label>
                <textarea
                  id={editDescId}
                  value={editDesc}
                  onChange={(e) => setEditDesc(e.target.value)}
                  rows={3}
                  className="w-full rounded-xl border border-slate-200/80 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/30 px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/15 focus:border-violet-500/65 resize-none"
                />
              </div>

              <div className="flex items-center gap-2 py-1">
                <input
                  id="require-approval"
                  type="checkbox"
                  checked={editRequireApproval}
                  onChange={(e) => setEditRequireApproval(e.target.checked)}
                  className="rounded border-slate-350 dark:border-slate-750 bg-slate-50 dark:bg-slate-800/20 text-violet-600 focus:ring-violet-500 h-4 w-4"
                />
                <label htmlFor="require-approval" className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Require post approval for content creators
                </label>
              </div>

              {editError && (
                <div role="alert" className="flex items-start gap-2 rounded-lg border border-rose-200 dark:border-rose-500/25 bg-rose-50 dark:bg-rose-500/10 px-3 py-2 text-xs text-rose-700">
                  <AlertCircle className="h-3.5 w-3.5 mt-px" />
                  <span>{editError}</span>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800/80">
                <Button variant="ghost" size="sm" type="button" onClick={() => setShowEditModal(false)} disabled={editSubmitting}>
                  Cancel
                </Button>
                <Button variant="primary" size="sm" type="submit" isLoading={editSubmitting}>
                  Save Changes
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* DELETE TEAM CONFIRMATION MODAL */}
      {showDeleteModal && (
        <div role="dialog" aria-modal="true" aria-labelledby="delete-modal-title" className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-sm" onClick={() => setShowDeleteModal(false)} aria-hidden="true" />
          <div className="sp-card relative w-full max-w-sm p-6 shadow-2xl space-y-4 animate-sp-fade-in-up">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-50 dark:bg-rose-500/10 text-rose-600">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <div>
              <h3 id="delete-modal-title" className="text-sm font-extrabold text-slate-900 dark:text-slate-100 font-heading">
                Delete Workspace Workspace?
              </h3>
              <p className="text-xs text-slate-450 dark:text-slate-450 mt-1 leading-relaxed">
                This action is permanent. All team configurations, memberships, and records will be deleted immediately.
              </p>
            </div>

            <div className="flex gap-2 pt-2">
              <Button variant="ghost" size="sm" className="flex-1" onClick={() => setShowDeleteModal(false)} disabled={deleteSubmitting}>
                Cancel
              </Button>
              <Button variant="danger" size="sm" className="flex-1" isLoading={deleteSubmitting} onClick={handleDeleteTeam}>
                Confirm Delete
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ADD TEAM MEMBER MODAL */}
      {showAddModal && (
        <div role="dialog" aria-modal="true" aria-labelledby="add-modal-title" className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-sm" onClick={() => setShowAddModal(false)} aria-hidden="true" />
          <div className="sp-card relative w-full max-w-md p-6 shadow-2xl space-y-4 animate-sp-fade-in-up">
            <div className="flex items-center justify-between">
              <h3 id="add-modal-title" className="text-base font-bold text-slate-900 dark:text-slate-100 font-heading">
                Add Team Member
              </h3>
              <button onClick={() => setShowAddModal(false)} className="rounded-lg p-1 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer">
                <X className="h-4.5 w-4.5" />
              </button>
            </div>

            <form onSubmit={handleAddMember} className="space-y-4">
              <div>
                <label htmlFor={addEmailId} className="block text-xs font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-1.5">
                  User Email Address
                </label>
                <input
                  id={addEmailId}
                  type="email"
                  required
                  value={addEmail}
                  onChange={(e) => setAddEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="w-full rounded-xl border border-slate-200/80 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/30 px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/15 focus:border-violet-500/65"
                />
              </div>

              <div>
                <label htmlFor={addRoleId} className="block text-xs font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-1.5">
                  Workspace Role
                </label>
                <select
                  id={addRoleId}
                  value={addRole}
                  onChange={(e) => setAddRole(e.target.value)}
                  className="w-full rounded-xl border border-slate-200/80 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/30 px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/15 focus:border-violet-500/65 cursor-pointer"
                >
                  <option value="content_creator">Content Creator</option>
                  <option value="business_user">Business Partner</option>
                  <option value="marketing_team">Marketing Team</option>
                  <option value="administrator">Team Admin</option>
                </select>
              </div>

              {addError && (
                <div role="alert" className="flex items-start gap-2 rounded-lg border border-rose-200 dark:border-rose-500/25 bg-rose-50 dark:bg-rose-500/10 px-3 py-2 text-xs text-rose-700">
                  <AlertCircle className="h-3.5 w-3.5 mt-px" />
                  <span>{addError}</span>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800/80">
                <Button variant="ghost" size="sm" type="button" onClick={() => setShowAddModal(false)} disabled={addSubmitting}>
                  Cancel
                </Button>
                <Button variant="primary" size="sm" type="submit" isLoading={addSubmitting}>
                  Add Member
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* INVITE TEAM MEMBER MODAL */}
      {showInviteModal && (
        <div role="dialog" aria-modal="true" aria-labelledby="invite-modal-title" className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-sm" onClick={() => setShowInviteModal(false)} aria-hidden="true" />
          <div className="sp-card relative w-full max-w-md p-6 shadow-2xl space-y-4 animate-sp-fade-in-up">
            <div className="flex items-center justify-between">
              <h3 id="invite-modal-title" className="text-base font-bold text-slate-900 dark:text-slate-100 font-heading">
                Invite Workspace Member
              </h3>
              <button onClick={() => setShowInviteModal(false)} className="rounded-lg p-1 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer">
                <X className="h-4.5 w-4.5" />
              </button>
            </div>

            {generatedLink ? (
              <div className="space-y-4 py-2">
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 dark:border-emerald-500/10 dark:bg-emerald-500/5 p-4 text-xs text-emerald-800 dark:text-emerald-450 space-y-2">
                  <p className="font-bold">Invitation created successfully!</p>
                  <p className="opacity-90">
                    An invitation was created for this user. Copy the link below and share it with them:
                  </p>
                  <p className="text-[10px] opacity-75 font-semibold mt-1">
                    Note: Email delivery is queued in the background. If you are in local development mode, please copy and share the link manually.
                  </p>
                  <div className="flex gap-2 items-center mt-3 bg-white dark:bg-[#080d19] border border-emerald-250/20 dark:border-emerald-500/15 rounded-lg p-2 overflow-hidden">
                    <span className="truncate flex-1 select-all text-[11px] font-mono text-slate-600 dark:text-slate-350">
                      {generatedLink}
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        navigator.clipboard.writeText(generatedLink);
                        showFeedback('Invitation link copied to clipboard!');
                      }}
                      className="px-2.5 py-1 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 text-[10px] font-bold rounded-md transition-colors"
                    >
                      Copy
                    </button>
                  </div>
                </div>
                <div className="flex justify-end pt-2">
                  <Button variant="primary" size="sm" onClick={() => setShowInviteModal(false)}>
                    Done
                  </Button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleInviteSubmit} className="space-y-4">
                <div>
                  <label htmlFor="invite-email" className="block text-xs font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-1.5">
                    User Email Address
                  </label>
                  <input
                    id="invite-email"
                    type="email"
                    required
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="colleague@company.com"
                    className="w-full rounded-xl border border-slate-200/80 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/30 px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/15 focus:border-violet-500/65"
                  />
                </div>

                <div>
                  <label htmlFor="invite-role" className="block text-xs font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-1.5">
                    Workspace Role
                  </label>
                  <select
                    id="invite-role"
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value)}
                    className="w-full rounded-xl border border-slate-200/80 dark:border-slate-700/60 bg-slate-50/50 dark:bg-slate-800/30 px-3.5 py-2.5 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-violet-500/15 focus:border-violet-500/65 cursor-pointer"
                  >
                    <option value="content_creator">Content Creator</option>
                    <option value="business_user">Business Partner</option>
                    <option value="marketing_team">Marketing Team</option>
                    <option value="administrator">Team Admin</option>
                  </select>
                </div>

                {inviteError && (
                  <div role="alert" className="flex items-start gap-2 rounded-lg border border-rose-200 dark:border-rose-500/25 bg-rose-50 dark:bg-rose-500/10 px-3 py-2 text-xs text-rose-700">
                    <AlertCircle className="h-3.5 w-3.5 mt-px" />
                    <span>{inviteError}</span>
                  </div>
                )}

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800/80">
                  <Button variant="ghost" size="sm" type="button" onClick={() => setShowInviteModal(false)} disabled={inviteSubmitting}>
                    Cancel
                  </Button>
                  <Button variant="primary" size="sm" type="submit" isLoading={inviteSubmitting}>
                    Send Invitation
                  </Button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* REMOVE MEMBER CONFIRMATION MODAL */}
      {memberToRemove && (
        <div role="dialog" aria-modal="true" aria-labelledby="remove-modal-title" className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-sm" onClick={() => setMemberToRemove(null)} aria-hidden="true" />
          <div className="sp-card relative w-full max-w-sm p-6 shadow-2xl space-y-4 animate-sp-fade-in-up">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-50 dark:bg-rose-500/10 text-rose-600">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <div>
              <h3 id="remove-modal-title" className="text-sm font-extrabold text-slate-900 dark:text-slate-100 font-heading">
                {memberToRemove.user_id === user?.id ? 'Leave Workspace Team?' : 'Remove Team Member?'}
              </h3>
              <p className="text-xs text-slate-450 dark:text-slate-450 mt-1 leading-relaxed">
                {memberToRemove.user_id === user?.id
                  ? "Are you sure you want to leave this workspace? You will lose access immediately and must be re-invited to join again."
                  : `Are you sure you want to remove member ${memberToRemove.user.full_name || memberToRemove.user.email} from the workspace?`}
              </p>
            </div>

            <div className="flex gap-2 pt-2">
              <Button variant="ghost" size="sm" className="flex-1" onClick={() => setMemberToRemove(null)} disabled={removeSubmitting}>
                Cancel
              </Button>
              <Button variant="danger" size="sm" className="flex-1" isLoading={removeSubmitting} onClick={handleRemoveMember}>
                Confirm
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
