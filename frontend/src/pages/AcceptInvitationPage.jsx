import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTeam } from '../context/TeamContext';
import { invitationsAPI } from '../lib/api';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Mail, CheckCircle2, XCircle, AlertCircle, Loader2 } from 'lucide-react';

export const AcceptInvitationPage = () => {
  const { token } = useParams();
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const { refreshTeams } = useTeam();

  const [invite, setInvite] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState(null);

  useEffect(() => {
    const fetchInvite = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await invitationsAPI.get(token);
        setInvite(res.data);
      } catch (err) {
        const d = err.response?.data?.detail;
        setError(typeof d === 'string' ? d : 'Failed to retrieve invitation details.');
      } finally {
        setLoading(false);
      }
    };
    fetchInvite();
  }, [token]);

  const handleAccept = async () => {
    setActionLoading(true);
    try {
      const res = await invitationsAPI.accept(token);
      setSuccessMsg('Invitation accepted successfully! Switching to your workspace...');
      
      // Set the active team ID in local storage so context auto-selects it
      localStorage.setItem('socialpilot_active_team_id', res.data.team_id);
      
      // Refresh teams in context
      await refreshTeams();

      setTimeout(() => {
        navigate('/dashboard');
      }, 1500);
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === 'string' ? d : 'Failed to accept invitation.');
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    setActionLoading(true);
    try {
      await invitationsAPI.reject(token);
      setSuccessMsg('Invitation rejected.');
      setTimeout(() => {
        navigate('/dashboard');
      }, 1500);
    } catch (err) {
      const d = err.response?.data?.detail;
      setError(typeof d === 'string' ? d : 'Failed to reject invitation.');
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-[#070d19] text-slate-800 dark:text-slate-100 p-4">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-violet-600" />
          <p className="text-xs font-semibold">Validating invitation token...</p>
        </div>
      </div>
    );
  }

  // Handle wrong or invalid token first
  if (error && !successMsg) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-[#070d19] p-4">
        <div className="w-full max-w-md rounded-2xl border border-rose-200/80 dark:border-rose-500/25 bg-white dark:bg-[#0D1426] p-6 shadow-xl text-center space-y-4">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-rose-50 dark:bg-rose-500/10 text-rose-600">
            <XCircle className="h-6 w-6" />
          </div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-50 font-heading">
            Invitation Error
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {error}
          </p>
          <div className="pt-2">
            <Link to="/dashboard">
              <Button variant="primary" size="sm">
                Go to Dashboard
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Handle successful acceptance/rejection message
  if (successMsg) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-[#070d19] p-4">
        <div className="w-full max-w-md rounded-2xl border border-emerald-250/80 dark:border-emerald-500/20 bg-white dark:bg-[#0D1426] p-6 shadow-xl text-center space-y-4">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-50 font-heading">
            Success
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {successMsg}
          </p>
        </div>
      </div>
    );
  }

  // Handle Unauthenticated State
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-[#070d19] p-4">
        <div className="w-full max-w-md rounded-2xl border border-slate-200/80 dark:border-slate-800/50 bg-white dark:bg-[#0D1426] p-6 shadow-xl text-center space-y-4">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-violet-50 dark:bg-violet-500/10 text-violet-600">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-50 font-heading">
            Authentication Required
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            You must be signed in to accept an invitation. Sign in or register using the same email address that received the invitation: <strong className="text-slate-850 dark:text-slate-100">{invite?.email}</strong>.
          </p>
          <div className="flex gap-3 justify-center pt-2">
            <Link to={`/login?redirect=/invite/${token}`}>
              <Button variant="primary" size="sm">
                Login
              </Button>
            </Link>
            <Link to={`/register?redirect=/invite/${token}`}>
              <Button variant="outline" size="sm">
                Register
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Handle Email Mismatch State
  if (user?.email?.toLowerCase() !== invite?.email?.toLowerCase()) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-[#070d19] p-4">
        <div className="w-full max-w-md rounded-2xl border border-rose-250/80 dark:border-rose-500/20 bg-white dark:bg-[#0D1426] p-6 shadow-xl text-center space-y-4">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-rose-50 dark:bg-rose-500/10 text-rose-600">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-slate-50 font-heading">
            Email Address Mismatch
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            This invitation was sent to <strong className="text-rose-700 dark:text-rose-400 font-mono">{invite?.email}</strong>. You are currently logged in as <strong className="text-slate-800 dark:text-slate-200 font-mono">{user?.email}</strong>.
          </p>
          <p className="text-xs text-slate-450 dark:text-slate-500 leading-relaxed">
            Please log out and sign in with the correct account to accept this invitation.
          </p>
          <div className="pt-2">
            <Link to="/logout">
              <Button variant="danger" size="sm">
                Log Out
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Display Acceptance Panel
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-[#070d19] p-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-200/80 dark:border-slate-800/50 bg-white dark:bg-[#0D1426] p-6 shadow-xl space-y-5 animate-sp-fade-in-up">
        
        {/* Header Visual */}
        <div className="text-center space-y-2">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-tr from-violet-600 to-blue-500 text-white shadow-md shadow-violet-500/20">
            <Mail className="h-5 w-5" />
          </div>
          <h1 className="text-xl font-extrabold text-slate-900 dark:text-slate-50 font-heading">
            Team Invitation
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            You have been invited to join a workspace on SocialPilot.
          </p>
        </div>

        {/* Invitation Meta Details */}
        <div className="rounded-xl bg-slate-50 dark:bg-slate-800/20 border border-slate-100 dark:border-slate-800/50 p-4 space-y-3.5 text-xs">
          <div className="flex justify-between items-center pb-2.5 border-b border-slate-100 dark:border-slate-800/40">
            <span className="text-slate-450 dark:text-slate-500">Workspace</span>
            <span className="font-bold text-slate-800 dark:text-slate-100">{invite?.team?.name}</span>
          </div>

          <div className="flex justify-between items-center pb-2.5 border-b border-slate-100 dark:border-slate-800/40">
            <span className="text-slate-450 dark:text-slate-500">Invited Role</span>
            <span className="capitalize font-bold text-violet-600 dark:text-violet-400">{invite?.role?.replace('_', ' ')}</span>
          </div>

          <div className="flex justify-between items-center">
            <span className="text-slate-450 dark:text-slate-500">Invited By</span>
            <span className="font-semibold text-slate-700 dark:text-slate-350">{invite?.invited_by?.full_name || invite?.invited_by?.email}</span>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex gap-3 pt-2">
          <Button
            variant="ghost"
            size="sm"
            className="flex-1"
            onClick={handleReject}
            disabled={actionLoading}
          >
            Decline
          </Button>
          <Button
            variant="primary"
            size="sm"
            className="flex-1 font-bold"
            onClick={handleAccept}
            isLoading={actionLoading}
          >
            Accept & Join
          </Button>
        </div>
      </div>
    </div>
  );
};
