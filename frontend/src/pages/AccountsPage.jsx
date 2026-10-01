import React, { useState, useEffect } from 'react';
import { accountsAPI, oauthAPI } from '../lib/api';
import { useTeam } from '../context/TeamContext';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { EmptyState } from '../components/ui/EmptyState';
import { Skeleton } from '../components/ui/Skeleton';
import {
  Share2,
  PlusCircle,
  RefreshCw,
  Trash2,
  Sliders,
  Activity,
  AlertCircle,
  CheckCircle2,
  ShieldCheck,
  Lock,
  ExternalLink,
  Info,
} from 'lucide-react';
import {
  FacebookIcon,
  InstagramIcon,
  LinkedInIcon,
  TwitterIcon,
  YouTubeIcon,
  PinterestIcon,
} from '../components/icons/PlatformIcons';

const platforms = [
  { id: 'all', name: 'All Platforms' },
  { id: 'facebook', name: 'Facebook', icon: FacebookIcon },
  { id: 'instagram', name: 'Instagram', icon: InstagramIcon },
  { id: 'linkedin', name: 'LinkedIn', icon: LinkedInIcon },
  { id: 'twitter', name: 'X / Twitter', icon: TwitterIcon },
  { id: 'youtube', name: 'YouTube', icon: YouTubeIcon },
  { id: 'pinterest', name: 'Pinterest', icon: PinterestIcon },
];

const platformBrandStyles = {
  facebook: { name: 'Facebook', color: 'text-[#1877F2]', bg: 'bg-[#1877F2]/10', border: 'border-[#1877F2]/20' },
  instagram: { name: 'Instagram', color: 'text-[#E4405F]', bg: 'bg-gradient-to-tr from-amber-500/10 via-rose-500/10 to-purple-500/10', border: 'border-[#E4405F]/20' },
  linkedin: { name: 'LinkedIn', color: 'text-[#0A66C2]', bg: 'bg-[#0A66C2]/10', border: 'border-[#0A66C2]/20' },
  twitter: { name: 'X / Twitter', color: 'text-slate-900 dark:text-slate-100', bg: 'bg-slate-100 dark:bg-slate-800', border: 'border-slate-300 dark:border-slate-700' },
  youtube: { name: 'YouTube', color: 'text-[#FF0000]', bg: 'bg-[#FF0000]/10', border: 'border-[#FF0000]/20' },
  pinterest: { name: 'Pinterest', color: 'text-[#BD081C]', bg: 'bg-[#BD081C]/10', border: 'border-[#BD081C]/20' },
};

export const AccountsPage = () => {
  const { activeTeamId } = useTeam();
  const [accounts, setAccounts] = useState([]);
  const [selectedPlatform, setSelectedPlatform] = useState('all');
  const [isLoading, setIsLoading] = useState(true);
  const [toastMessage, setToastMessage] = useState(null);

  // Connection success animation state
  const [connectionSuccess, setConnectionSuccess] = useState(null); // { platform, accountName }
  const [syncComplete, setSyncComplete] = useState(false);

  // Modals state
  const [isConnectOpen, setIsConnectOpen] = useState(false);
  const [isPermissionsOpen, setIsPermissionsOpen] = useState(false);
  const [isStatusOpen, setIsStatusOpen] = useState(false);
  const [isDisconnectOpen, setIsDisconnectOpen] = useState(false);
  const [activeAccount, setActiveAccount] = useState(null);
  const [accountStatusData, setAccountStatusData] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [connectingProvider, setConnectingProvider] = useState(null);
  const [connectError, setConnectError] = useState('');

  // Page selection state for Meta / Facebook Page Flow
  const [isPageSelectOpen, setIsPageSelectOpen] = useState(false);
  const [activeSessionToken, setActiveSessionToken] = useState(null);
  const [availablePages, setAvailablePages] = useState([]);
  const [selectedPageId, setSelectedPageId] = useState('');
  const [connectInstagram, setConnectInstagram] = useState(false);
  const [pageSelectLoading, setPageSelectLoading] = useState(false);
  const [pageSelectError, setPageSelectError] = useState('');
  // Track which platform triggered the page flow (for Instagram pre-selection)
  const [preferredPlatform, setPreferredPlatform] = useState(null);

  // Permissions Form State
  const [customPermissions, setCustomPermissions] = useState({});

  const showToast = (msg, type = 'success') => {
    setToastMessage({ msg, type });
    setTimeout(() => setToastMessage(null), 4500);
  };

  const fetchAccounts = async (platformFilter = selectedPlatform) => {
    try {
      setIsLoading(true);
      const params = {};
      if (platformFilter && platformFilter !== 'all') {
        params.platform = platformFilter;
      }
      if (activeTeamId) {
        params.team_id = activeTeamId;
      }
      const res = await accountsAPI.list(params);
      setAccounts(res.data);
    } catch (err) {
      console.error('Failed to load accounts:', err);
      showToast('Could not fetch accounts. Please check server connection.', 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const loadAvailablePages = async (token, platformHint) => {
    setPageSelectLoading(true);
    setPageSelectError('');
    setIsPageSelectOpen(true);
    setPreferredPlatform(platformHint || null);
    try {
      const res = await oauthAPI.getAvailableFacebookPages(token);
      const pages = res.data?.pages || [];
      setAvailablePages(pages);
      if (pages.length > 0) {
        setSelectedPageId(pages[0].page_id);
        // Pre-select Instagram toggle if:
        // 1. The platform hint is 'instagram', OR
        // 2. The first page already has an Instagram account linked
        const firstPageHasIg = Boolean(pages[0].has_instagram);
        setConnectInstagram(platformHint === 'instagram' ? true : firstPageHasIg);
      }
    } catch (err) {
      console.error('Failed to load available Facebook pages:', err);
      const msg = err.response?.data?.detail || 'Failed to load available Facebook Pages. OAuth session may have expired.';
      setPageSelectError(msg);
    } finally {
      setPageSelectLoading(false);
    }
  };

  const handleConnectPage = async () => {
    if (!selectedPageId || !activeSessionToken) return;
    setPageSelectLoading(true);
    setPageSelectError('');
    try {
      const res = await oauthAPI.connectFacebookPage({
        session_token: activeSessionToken,
        page_id: selectedPageId,
        connect_instagram: connectInstagram,
        team_id: activeTeamId || null,
      });
      setIsPageSelectOpen(false);
      await fetchAccounts(selectedPlatform);
      // Determine which platform to celebrate
      const platform = connectInstagram && res.data?.instagram_account ? 'instagram' : 'facebook';
      const acctName = connectInstagram && res.data?.instagram_account
        ? (res.data.instagram_account.account_name || res.data.instagram_account.account_identifier)
        : (res.data?.facebook_account?.account_name || 'your account');
      // Show success animation
      setSyncComplete(false);
      setConnectionSuccess({ platform, accountName: acctName });
      setTimeout(() => setSyncComplete(true), 2200);
      setTimeout(() => setConnectionSuccess(null), 6000);
    } catch (err) {
      console.error('Connect page error:', err);
      const msg = err.response?.data?.detail || 'Failed to connect selected page.';
      setPageSelectError(msg);
      showToast(msg, 'error');
    } finally {
      setPageSelectLoading(false);
    }
  };

  // Process OAuth Callback Query Parameters
  useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search);
    const oauthParam = searchParams.get('oauth');
    const statusParam = searchParams.get('status');
    const sessionTokenParam = searchParams.get('session_token');
    const providerParam = searchParams.get('platform') || searchParams.get('provider');
    const messageParam = searchParams.get('message');
    const accountNameParam = searchParams.get('account_name');

    if (statusParam === 'select_pages' && sessionTokenParam) {
      setActiveSessionToken(sessionTokenParam);
      // Pass the platform hint (e.g. 'instagram') so we can pre-select the toggle
      loadAvailablePages(sessionTokenParam, providerParam);
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (oauthParam === 'success' || statusParam === 'success') {
      const name = accountNameParam ? decodeURIComponent(accountNameParam) : null;
      const platform = providerParam || 'instagram';
      // Show success animation for successful connections
      setSyncComplete(false);
      setConnectionSuccess({ platform, accountName: name || (platform === 'instagram' ? 'Instagram Account' : platform) });
      setTimeout(() => setSyncComplete(true), 1800);
      setTimeout(() => {
        setConnectionSuccess(null);
        window.dispatchEvent(new CustomEvent('socialpilot:accounts-updated'));
      }, 4200);
      window.history.replaceState({}, document.title, window.location.pathname);
      fetchAccounts(selectedPlatform);
      window.dispatchEvent(new CustomEvent('socialpilot:accounts-updated'));
    } else if (oauthParam === 'error' || statusParam === 'error') {
      const msg = messageParam ? decodeURIComponent(messageParam) : `OAuth authorization failed for ${providerParam || 'provider'}.`;
      showToast(msg, 'error');
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    fetchAccounts(selectedPlatform);
  }, [selectedPlatform, activeTeamId]);

  // Handle Initiating Official OAuth Authorization Code Flow
  const handleInitiateOAuth = async (providerId) => {
    if (connectingProvider) return;
    setConnectingProvider(providerId);
    setConnectError('');
    try {
      const res = await oauthAPI.getAuthorizationUrl(providerId, activeTeamId);
      if (res.data?.authorization_url) {
        window.location.href = res.data.authorization_url;
      } else {
        setConnectError(`Failed to retrieve OAuth authorization URL for ${providerId}.`);
      }
    } catch (err) {
      console.error('OAuth initiation error:', err);
      const msg = err.response?.data?.detail || err.message || `Failed to start OAuth connection for ${providerId}.`;
      setConnectError(msg);
      showToast(msg, 'error');
    } finally {
      setConnectingProvider(null);
    }
  };

  const [syncingAccountId, setSyncingAccountId] = useState(null);

  const formatRelativeTime = (isoString) => {
    if (!isoString) return 'Never synced';
    const diff = Date.now() - new Date(isoString).getTime();
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return new Date(isoString).toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  // Sync Trigger
  const handleSyncAccount = async (account) => {
    try {
      setSyncingAccountId(account.id);
      const res = await accountsAPI.sync(account.id);
      showToast(res.data.message || `Synchronized ${account.account_name} successfully!`);
      fetchAccounts(selectedPlatform);
    } catch (err) {
      console.error('Sync error:', err);
      showToast('Failed to trigger synchronization workflow.', 'error');
    } finally {
      setSyncingAccountId(null);
    }
  };

  // Status Check Modal Trigger
  const handleOpenStatus = async (account) => {
    setActiveAccount(account);
    setIsStatusOpen(true);
    try {
      const res = await accountsAPI.getStatus(account.id);
      setAccountStatusData(res.data);
    } catch (err) {
      console.error('Status fetch error:', err);
    }
  };

  // Permissions Modal Trigger
  const handleOpenPermissions = (account) => {
    setActiveAccount(account);
    setCustomPermissions(account.platform_permissions || {});
    setIsPermissionsOpen(true);
  };

  const handleSavePermissions = async () => {
    if (!activeAccount) return;
    setActionLoading(true);
    try {
      await accountsAPI.updatePermissions(activeAccount.id, customPermissions);
      showToast(`Updated permissions for ${activeAccount.account_name}!`);
      setIsPermissionsOpen(false);
      fetchAccounts(selectedPlatform);
    } catch (err) {
      console.error('Permissions update error:', err);
      showToast('Failed to update permissions.', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // Disconnect Handler
  const handleConfirmDisconnect = async () => {
    if (!activeAccount) return;
    setActionLoading(true);
    try {
      await accountsAPI.disconnect(activeAccount.id);
      showToast(`Disconnected ${activeAccount.account_name}. Status updated to Revoked.`);
      setIsDisconnectOpen(false);
      fetchAccounts(selectedPlatform);
    } catch (err) {
      console.error('Disconnect error:', err);
      showToast('Failed to disconnect account.', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6">

      {/* ── Connection Success Overlay ── */}
      {connectionSuccess && (
        <div
          role="status"
          aria-live="polite"
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)' }}
        >
          <div
            className="relative flex flex-col items-center gap-5 rounded-3xl border p-8 sm:p-10 shadow-2xl animate-sp-fade-in-up text-center"
            style={{
              background: 'var(--sp-card)',
              borderColor: 'var(--sp-border)',
              maxWidth: 380,
              width: '100%',
            }}
          >
            {/* Animated Platform + Success Icon */}
            <div className="relative flex items-center justify-center">
              <div
                className="absolute h-24 w-24 rounded-full animate-ping opacity-25"
                style={{ background: connectionSuccess.platform === 'instagram' ? '#E4405F' : '#1877F2' }}
              />
              <div
                className="flex h-20 w-20 items-center justify-center rounded-2xl border-2 shadow-lg relative"
                style={{
                  borderColor: connectionSuccess.platform === 'instagram' ? '#E4405F' : '#1877F2',
                  background: connectionSuccess.platform === 'instagram'
                    ? 'linear-gradient(135deg, rgba(228,64,95,0.15), rgba(131,58,180,0.15))'
                    : 'rgba(24,119,242,0.12)',
                }}
              >
                {connectionSuccess.platform === 'instagram' ? (
                  <InstagramIcon className="h-10 w-10 text-[#E4405F]" />
                ) : (
                  <FacebookIcon className="h-10 w-10 text-[#1877F2]" />
                )}
                {/* Floating check badge */}
                <div className="absolute -bottom-1 -right-1 bg-emerald-500 rounded-full p-1 border-2 border-white dark:border-slate-900 shadow-md">
                  <CheckCircle2 className="h-4 w-4 text-white" />
                </div>
              </div>
            </div>

            <div className="space-y-1">
              <h2 className="text-lg sm:text-xl font-bold font-heading" style={{ color: 'var(--sp-text)' }}>
                {connectionSuccess.platform === 'instagram'
                  ? 'Instagram Connected Successfully'
                  : `${connectionSuccess.platform.charAt(0).toUpperCase() + connectionSuccess.platform.slice(1)} Connected Successfully`}
              </h2>
              <p className="text-xs sm:text-sm font-medium" style={{ color: 'var(--sp-text-secondary)' }}>
                {connectionSuccess.platform === 'instagram' && !connectionSuccess.accountName.startsWith('@')
                  ? `@${connectionSuccess.accountName}`
                  : connectionSuccess.accountName}
              </p>
            </div>

            {/* Sync Progress / Ready State */}
            <div
              className="flex items-center gap-2 rounded-xl px-4 py-2.5 text-xs font-semibold border transition-all"
              style={{
                background: syncComplete ? 'rgba(16,185,129,0.12)' : 'var(--sp-surface-2)',
                borderColor: syncComplete ? 'rgba(16,185,129,0.3)' : 'var(--sp-border)',
                color: syncComplete ? 'rgb(5,150,105)' : 'var(--sp-text-muted)',
              }}
            >
              {syncComplete ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-emerald-500 animate-sp-scale-in" />
                  <span>Your {connectionSuccess.platform === 'instagram' ? 'Instagram' : connectionSuccess.platform} account is ready.</span>
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin text-cyan-600 dark:text-violet-400" />
                  <span>Syncing your account data...</span>
                </>
              )}
            </div>

            <button
              type="button"
              onClick={() => {
                setConnectionSuccess(null);
                window.dispatchEvent(new CustomEvent('socialpilot:accounts-updated'));
              }}
              className="mt-1 text-xs font-semibold px-4 py-1.5 rounded-lg border cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              style={{ borderColor: 'var(--sp-border)', color: 'var(--sp-text-secondary)' }}
            >
              {syncComplete ? 'Done' : 'Dismiss'}
            </button>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toastMessage && (
        <div
          role="status"
          className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 rounded-2xl border p-4 shadow-xl backdrop-blur-md transition-all ${
            toastMessage.type === 'error'
              ? 'border-rose-500/20 bg-rose-500/90 text-white'
              : 'border-emerald-500/20 bg-emerald-600/90 text-white'
          }`}
        >
          {toastMessage.type === 'error' ? (
            <AlertCircle className="h-5 w-5" aria-hidden="true" />
          ) : (
            <CheckCircle2 className="h-5 w-5" aria-hidden="true" />
          )}
          <span className="text-sm font-semibold">{toastMessage.msg}</span>
        </div>
      )}

      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 font-heading">
            Social Accounts Management
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Connect and manage multi-platform profiles with token security and granular permissions
          </p>
        </div>
        <Button
          onClick={() => setIsConnectOpen(true)}
          variant="primary"
          size="md"
          icon={PlusCircle}
        >
          Connect Account
        </Button>
      </div>

      {/* Platform Filter Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-slate-200/80 dark:border-slate-800">
        {platforms.map((p) => {
          const Icon = p.icon;
          const isActive = selectedPlatform === p.id;
          return (
            <button
              key={p.id}
              onClick={() => setSelectedPlatform(p.id)}
              className={`flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-semibold whitespace-nowrap transition-standard cursor-pointer ${
                isActive
                  ? 'bg-cyan-500/15 text-cyan-800 dark:bg-violet-500/20 dark:text-violet-300 border border-cyan-500/30 dark:border-violet-500/40 shadow-xs'
                  : 'bg-[var(--sp-card)] text-[var(--sp-text-secondary)] border border-[var(--sp-border)] hover:bg-[var(--sp-card-hover)]'
              }`}
            >
              {Icon && <Icon className="h-3.5 w-3.5" aria-hidden="true" />}
              <span>{p.name}</span>
            </button>
          );
        })}
      </div>

      {/* Accounts List / Cards */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      ) : accounts.length === 0 ? (
        <EmptyState
          icon={Share2}
          title="No Social Accounts Connected"
          description={
            selectedPlatform !== 'all'
              ? `No ${selectedPlatform.toUpperCase()} accounts currently found. Connect one now.`
              : 'Connect your first social media profile to start scheduling and managing cross-platform content.'
          }
          actionLabel="Connect Your First Account"
          onAction={() => setIsConnectOpen(true)}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {accounts.map((account) => {
            const isConnected = account.connection_status === 'connected';
            const isExpired = account.is_token_expired;
            const brandStyle = platformBrandStyles[account.platform] || platformBrandStyles.facebook;
            const avatarUrl = account.platform_permissions?.picture_url || account.platform_permissions?.avatar_url || account.platform_permissions?.profile_picture_url;
            const category = account.platform_permissions?.category;

            return (
              <Card key={account.id} hover className="flex flex-col justify-between">
                <div>
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      {avatarUrl ? (
                        <img
                          src={avatarUrl}
                          alt={account.account_name}
                          className="h-11 w-11 rounded-xl object-cover border border-slate-200 dark:border-slate-700 shadow-2xs"
                        />
                      ) : (
                        <div
                          className={`flex h-11 w-11 items-center justify-center rounded-xl ${brandStyle.bg} ${brandStyle.border} border ${brandStyle.color} font-bold text-xs shadow-2xs`}
                        >
                          {account.platform.slice(0, 2).toUpperCase()}
                        </div>
                      )}
                      <div>
                        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 font-heading">
                          {account.platform === 'instagram' && !account.account_name.startsWith('@')
                            ? `@${account.account_name}`
                            : account.account_name}
                        </h3>
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <p className="text-[11px] text-slate-400 font-mono">
                            ID: {account.account_identifier}
                          </p>
                          {category && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 font-medium">
                              {category}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <Badge
                      variant={
                        account.connection_status === 'connected'
                          ? (isExpired ? 'warning' : 'success')
                          : (account.connection_status === 'expired' ? 'warning' : 'danger')
                      }
                      size="xs"
                    >
                      {account.connection_status === 'connected'
                        ? (isExpired ? 'Expired' : 'Connected')
                        : (account.connection_status === 'expired' ? 'Expired' : (account.connection_status === 'revoked' ? 'Revoked' : 'Disconnected'))}
                    </Badge>
                  </div>

                  {/* Expired / Revoked Token Warning & Reconnect CTA */}
                  {(account.connection_status === 'expired' || account.connection_status === 'revoked' || isExpired) && (
                    <div className="mt-3 flex items-center justify-between rounded-xl bg-amber-500/10 p-2.5 text-xs text-amber-600 dark:text-amber-400 border border-amber-500/20">
                      <div className="flex items-center gap-1.5">
                        <AlertCircle className="h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />
                        <span className="font-medium text-[11px]">
                          {account.connection_status === 'revoked' ? 'Access revoked. Reconnect required.' : 'Token expired. Reconnect required.'}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          // Instagram reconnects via Facebook Login flow (which discovers linked IG accounts)
                          const reconnectProvider = account.platform === 'instagram' ? 'facebook' : account.platform;
                          handleInitiateOAuth(reconnectProvider);
                        }}
                        className="text-[11px] font-bold text-amber-700 dark:text-amber-300 underline hover:no-underline cursor-pointer"
                      >
                        Reconnect
                      </button>
                    </div>
                  )}

                  {/* Account Metadata */}
                  <div className="mt-4 space-y-2 rounded-xl p-3.5 border text-[11px]" style={{ background: 'var(--sp-surface-2)', borderColor: 'var(--sp-border)' }}>
                    <div className="flex justify-between text-slate-500">
                      <span>Platform:</span>
                      <span className="font-bold text-slate-700 dark:text-slate-300 uppercase">
                        {account.platform}
                      </span>
                    </div>
                    <div className="flex justify-between text-slate-500">
                      <span>Audience / Followers:</span>
                      {account.platform_permissions?.follower_count !== undefined && account.platform_permissions?.follower_count !== null ? (
                        <span className="font-bold text-slate-700 dark:text-slate-300">
                          {Number(account.platform_permissions.follower_count).toLocaleString()}
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-400 italic">
                          Not available from {account.platform === 'instagram' ? 'Instagram' : 'Meta'} API
                        </span>
                      )}
                    </div>
                    {account.platform_permissions?.following_count !== undefined && account.platform_permissions?.following_count !== null && (
                      <div className="flex justify-between text-slate-500">
                        <span>Following:</span>
                        <span className="font-bold text-slate-700 dark:text-slate-300">
                          {Number(account.platform_permissions.following_count).toLocaleString()}
                        </span>
                      </div>
                    )}
                    <div className="flex justify-between text-slate-500">
                      <span>Total Posts:</span>
                      {account.platform_permissions?.post_count !== undefined && account.platform_permissions?.post_count !== null ? (
                        <span className="font-bold text-slate-700 dark:text-slate-300">
                          {Number(account.platform_permissions.post_count).toLocaleString()}
                        </span>
                      ) : (
                        <span className="text-[10px] text-slate-400 italic">
                          Not available from {account.platform === 'instagram' ? 'Instagram' : 'Meta'} API
                        </span>
                      )}
                    </div>
                    {account.platform_permissions?.biography && (
                      <div className="text-[11px] text-slate-500 italic pt-1 border-t border-slate-100 dark:border-slate-800 line-clamp-2">
                        &quot;{account.platform_permissions.biography}&quot;
                      </div>
                    )}
                    <div className="flex justify-between text-slate-500 pt-1">
                      <span>Last Sync:</span>
                      <span className="font-medium text-slate-700 dark:text-slate-300 flex items-center gap-1">
                        {syncingAccountId === account.id ? (
                          <span className="inline-flex items-center gap-1 text-cyan-600 dark:text-violet-400 font-semibold animate-pulse">
                            <RefreshCw className="h-3 w-3 animate-spin" /> Syncing...
                          </span>
                        ) : (
                          formatRelativeTime(account.last_synced_at)
                        )}
                      </span>
                    </div>
                    <div className="flex justify-between text-slate-500">
                      <span>Token Security:</span>
                      <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold">
                        <Lock className="h-3 w-3" aria-hidden="true" />
                        AES Encrypted
                      </span>
                    </div>
                  </div>
                </div>

                {/* Card Action Buttons */}
                <div className="mt-5 grid grid-cols-4 gap-2 pt-4 border-t border-slate-100 dark:border-slate-800">
                  <Button
                    variant="outline"
                    size="sm"
                    title="Check Connection Status"
                    aria-label="Check Connection Status"
                    onClick={() => handleOpenStatus(account)}
                    className="p-2"
                  >
                    <Activity className="h-3.5 w-3.5" aria-hidden="true" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    title="Edit Platform Permissions"
                    aria-label="Edit Platform Permissions"
                    onClick={() => handleOpenPermissions(account)}
                    className="p-2"
                  >
                    <Sliders className="h-3.5 w-3.5" aria-hidden="true" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    title={syncingAccountId === account.id ? "Syncing account..." : "Sync Now"}
                    aria-label="Trigger Synchronization"
                    onClick={() => handleSyncAccount(account)}
                    disabled={syncingAccountId === account.id}
                    className="p-2"
                  >
                    <RefreshCw className={`h-3.5 w-3.5 ${syncingAccountId === account.id ? 'animate-spin text-cyan-500' : ''}`} aria-hidden="true" />
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    title="Disconnect Account"
                    aria-label="Disconnect Account"
                    onClick={() => {
                      setActiveAccount(account);
                      setIsDisconnectOpen(true);
                    }}
                    className="p-2"
                  >
                    <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                  </Button>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* 1. Connect Account Modal */}
      <Modal
        isOpen={isConnectOpen}
        onClose={() => setIsConnectOpen(false)}
        title="Connect Social Media Profile"
        description="Select a social platform to authorize via official provider OAuth 2.0. Passwords are never collected inside SocialPilot."
      >
        {connectError && (
          <div className="mb-4 flex items-start gap-2 rounded-xl bg-rose-500/10 p-3 text-xs text-rose-600 dark:text-rose-400 border border-rose-500/20">
            <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" aria-hidden="true" />
            <span>{connectError}</span>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 py-2">
          {platforms.filter(p => p.id !== 'all').map((p) => {
            const Icon = p.icon;
            const style = platformBrandStyles[p.id];
            const isConnecting = connectingProvider === p.id;

            return (
              <button
                key={p.id}
                type="button"
                disabled={isConnecting}
                onClick={() => handleInitiateOAuth(p.id)}
                className="group flex items-center justify-between p-3.5 rounded-xl border transition-all duration-200 hover:-translate-y-0.5 cursor-pointer text-left"
                style={{ background: 'var(--sp-surface-2)', borderColor: 'var(--sp-border)' }}
              >
                <div className="flex items-center gap-3">
                  <div className={`flex h-9 w-9 items-center justify-center rounded-lg border ${style?.bg} ${style?.border} ${style?.color}`}>
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <div>
                    <p className="text-xs font-bold font-heading" style={{ color: 'var(--sp-text)' }}>
                      {p.name}
                    </p>
                    <p className="text-[10px]" style={{ color: 'var(--sp-text-muted)' }}>
                      Official OAuth 2.0
                    </p>
                  </div>
                </div>
                {isConnecting ? (
                  <span className="text-xs font-semibold animate-pulse" style={{ color: 'var(--sp-primary)' }}>
                    Connecting...
                  </span>
                ) : (
                  <ExternalLink className="h-4 w-4 opacity-60 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all" style={{ color: 'var(--sp-primary)' }} />
                )}
              </button>
            );
          })}
        </div>

        <div className="mt-4 space-y-2.5">
          <div className="rounded-xl p-3 text-[11px] border flex items-start gap-2" style={{ background: 'var(--active-nav-bg)', borderColor: 'var(--sp-border)', color: 'var(--sp-text-secondary)' }}>
            <ShieldCheck className="h-4 w-4 mt-0.5 flex-shrink-0 text-emerald-500" aria-hidden="true" />
            <div>
              <strong>Secure Multi-Tenant Isolation:</strong> Every connection is cryptographically bound to your active workspace. Access tokens are encrypted with AES-256 at rest and never exposed.
            </div>
          </div>
          
          <div className="rounded-xl p-3 text-[11px] border space-y-2 bg-slate-50 dark:bg-slate-800/60 border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-1.5 font-bold text-slate-800 dark:text-slate-200">
              <FacebookIcon className="h-3.5 w-3.5 text-[#1877F2]" />
              <InstagramIcon className="h-3.5 w-3.5 text-[#E4405F]" />
              <span>Facebook &amp; Instagram — How it works:</span>
            </div>
            <p className="text-slate-600 dark:text-slate-400">
              Both Facebook and Instagram connect via <strong>Facebook Login</strong> (Meta&apos;s unified API). You&apos;ll see a Facebook dialog — then choose which Page and/or Instagram Professional account to link.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-0.5">
              <div className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                <span className="font-semibold text-slate-800 dark:text-slate-200 block mb-0.5">📘 Facebook Pages</span>
                <span className="text-[10px] text-slate-500">Select any Facebook Page you admin to connect it for posting and analytics.</span>
              </div>
              <div className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                <span className="font-semibold text-slate-800 dark:text-slate-200 block mb-0.5">📸 Instagram Business</span>
                <span className="text-[10px] text-slate-500">If your Page has a linked Instagram Professional account, you can connect it too in the same step.</span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex justify-end pt-4">
          <Button variant="outline" onClick={() => setIsConnectOpen(false)}>
            Close
          </Button>
        </div>
      </Modal>

      {/* 2. Status Check Modal */}
      <Modal
        isOpen={isStatusOpen}
        onClose={() => setIsStatusOpen(false)}
        title={`Status: ${activeAccount?.account_name}`}
        description="Real-time connection health and token validity check"
      >
        {accountStatusData ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
              <span className="text-xs font-semibold text-slate-500">Connection State</span>
              <Badge
                variant={accountStatusData.connection_status === 'connected' ? 'success' : 'danger'}
              >
                {accountStatusData.connection_status.toUpperCase()}
              </Badge>
            </div>

            <div className="flex items-center justify-between p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800">
              <span className="text-xs font-semibold text-slate-500">Token Validity</span>
              <Badge variant={accountStatusData.is_token_expired ? 'danger' : 'success'}>
                {accountStatusData.is_token_expired ? 'Expired' : 'Valid'}
              </Badge>
            </div>

            <div className="flex items-center justify-between p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-800 text-xs">
              <span className="font-semibold text-slate-500">Token Expiry</span>
              <span className="text-slate-700 dark:text-slate-300">
                {accountStatusData.token_expires_at
                  ? new Date(accountStatusData.token_expires_at).toLocaleString()
                  : 'No expiration configured'}
              </span>
            </div>

            <div className="flex justify-end pt-2">
              <Button variant="primary" onClick={() => setIsStatusOpen(false)}>
                Close
              </Button>
            </div>
          </div>
        ) : (
          <Skeleton className="h-32 w-full" />
        )}
      </Modal>

      {/* 3. Permissions Editor Modal */}
      <Modal
        isOpen={isPermissionsOpen}
        onClose={() => setIsPermissionsOpen(false)}
        title={`Permissions: ${activeAccount?.account_name}`}
        description="Configure granular permission scopes granted to this profile"
      >
        <div className="space-y-3">
          {Object.entries(customPermissions).length === 0 ? (
            <p className="text-xs text-slate-500 py-4">No custom permissions found for this platform.</p>
          ) : (
            Object.entries(customPermissions).map(([key, value]) => (
              <label
                key={key}
                className="flex items-center justify-between p-3 rounded-xl border border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer transition-colors"
              >
                <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 capitalize">
                  {key.replace(/_/g, ' ')}
                </span>
                <input
                  type="checkbox"
                  checked={Boolean(value)}
                  onChange={(e) =>
                    setCustomPermissions({ ...customPermissions, [key]: e.target.checked })
                  }
                  className="h-4 w-4 rounded text-cyan-600 dark:text-violet-600 focus:ring-cyan-500 dark:focus:ring-violet-500"
                />
              </label>
            ))
          )}

          <div className="flex justify-end gap-2 pt-4">
            <Button variant="outline" onClick={() => setIsPermissionsOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleSavePermissions}
              isLoading={actionLoading}
            >
              Save Permissions
            </Button>
          </div>
        </div>
      </Modal>

      {/* 4. Disconnect Confirmation Modal */}
      <Modal
        isOpen={isDisconnectOpen}
        onClose={() => setIsDisconnectOpen(false)}
        title="Disconnect Social Account?"
        description="Are you sure you want to disconnect this profile? Its status will be updated to Revoked."
      >
        <div className="p-4 rounded-xl bg-rose-500/10 text-xs text-rose-600 dark:text-rose-400 mb-4 border border-rose-500/20">
          <strong>Account:</strong> {activeAccount?.account_name} ({activeAccount?.platform?.toUpperCase()})
        </div>

        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={() => setIsDisconnectOpen(false)}>
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={handleConfirmDisconnect}
            isLoading={actionLoading}
          >
            Confirm Disconnect
          </Button>
        </div>
      </Modal>

      {/* 5. Select Facebook Page Modal */}
      <Modal
        isOpen={isPageSelectOpen}
        onClose={() => setIsPageSelectOpen(false)}
        title={preferredPlatform === 'instagram' ? 'Connect Instagram via Facebook Page' : 'Select Facebook Page to Connect'}
        description={
          preferredPlatform === 'instagram'
            ? 'Instagram Professional/Business accounts are linked to Facebook Pages. Select your Page below — your linked Instagram account will be pre-selected for connection.'
            : 'Choose which Facebook Page you want to manage. If an Instagram Professional account is connected to the Page, you can also link it now.'
        }
      >
        {pageSelectError && (
          <div className="mb-4 flex items-start gap-2 rounded-xl bg-rose-500/10 p-3 text-xs text-rose-600 dark:text-rose-400 border border-rose-500/20">
            <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" aria-hidden="true" />
            <span>{pageSelectError}</span>
          </div>
        )}

        {pageSelectLoading && availablePages.length === 0 ? (
          <div className="space-y-3 py-4">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : availablePages.length === 0 ? (
          <div className="p-4 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 text-xs">
            <p className="font-semibold">No Facebook Pages Found</p>
            <p className="mt-1">
              Your Facebook account does not currently manage any Pages. You must create or be an admin of at least one Facebook Page to connect with SocialPilot.
            </p>
          </div>
        ) : (
          <div className="space-y-3 py-2">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              Available Pages ({availablePages.length})
            </label>
            <div className="max-h-64 overflow-y-auto space-y-2.5 pr-1">
              {availablePages.map((page) => {
                const isSelected = selectedPageId === page.page_id;
                return (
                  <div
                    key={page.page_id}
                    onClick={() => {
                      setSelectedPageId(page.page_id);
                      if (page.has_instagram) {
                        setConnectInstagram(true);
                      }
                    }}
                    className={`flex items-start gap-3 p-3.5 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? 'border-cyan-500 bg-cyan-500/10 dark:border-violet-500 dark:bg-violet-500/10'
                        : 'border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/40'
                    }`}
                  >
                    <input
                      type="radio"
                      name="facebook_page_select"
                      checked={isSelected}
                      onChange={() => {
                        setSelectedPageId(page.page_id);
                        if (page.has_instagram) {
                          setConnectInstagram(true);
                        }
                      }}
                      className="mt-1 h-4 w-4 text-cyan-600 dark:text-violet-600 focus:ring-cyan-500"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2.5">
                        {page.picture_url ? (
                          <img
                            src={page.picture_url}
                            alt={page.name}
                            className="h-8 w-8 rounded-lg object-cover border border-slate-200 dark:border-slate-700"
                          />
                        ) : (
                          <div className="h-8 w-8 rounded-lg bg-[#1877F2]/10 border border-[#1877F2]/20 flex items-center justify-center text-[#1877F2] font-bold text-xs">
                            FB
                          </div>
                        )}
                        <div className="truncate">
                          <p className="text-xs font-bold text-slate-900 dark:text-slate-100 truncate">
                            {page.name}
                          </p>
                          <p className="text-[10px] text-slate-400 font-mono">
                            ID: {page.page_id} {page.category ? `• ${page.category}` : ''}
                          </p>
                        </div>
                      </div>

                      {/* Instagram Linked Section for this page */}
                      {isSelected && (
                        <div className="mt-3 pt-3 border-t border-slate-200/60 dark:border-slate-800">
                          {page.has_instagram && page.instagram_account ? (
                            <div className="rounded-lg p-2.5 bg-gradient-to-tr from-amber-500/10 via-rose-500/10 to-purple-500/10 border border-[#E4405F]/20">
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  {page.instagram_account.profile_picture_url ? (
                                    <img
                                      src={page.instagram_account.profile_picture_url}
                                      alt={page.instagram_account.username}
                                      className="h-7 w-7 rounded-full object-cover border border-[#E4405F]/30"
                                    />
                                  ) : (
                                    <div className="h-7 w-7 rounded-full bg-[#E4405F]/20 flex items-center justify-center text-[#E4405F] font-bold text-[10px]">
                                      IG
                                    </div>
                                  )}
                                  <div>
                                    <p className="text-xs font-bold text-slate-900 dark:text-slate-100">
                                      @{page.instagram_account.username || page.instagram_account.name}
                                    </p>
                                    <span className="text-[9px] font-semibold text-emerald-600 dark:text-emerald-400">
                                      Connected Instagram Business Account
                                    </span>
                                  </div>
                                </div>
                              </div>
                              <label className="mt-2.5 flex items-center gap-2 text-xs font-medium text-slate-700 dark:text-slate-300 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={connectInstagram}
                                  onChange={(e) => setConnectInstagram(e.target.checked)}
                                  className="h-3.5 w-3.5 rounded text-rose-600 focus:ring-rose-500"
                                />
                                <span>Also connect linked Instagram account</span>
                              </label>
                            </div>
                          ) : (
                            <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/60 text-[11px] text-slate-500 dark:text-slate-400 border border-slate-200/60 dark:border-slate-800">
                              <p className="italic">
                                An Instagram Professional/Business account is not connected to this Facebook Page.
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className="flex justify-end gap-2 pt-4">
          <Button variant="outline" onClick={() => setIsPageSelectOpen(false)}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleConnectPage}
            isLoading={pageSelectLoading}
            disabled={!selectedPageId || availablePages.length === 0}
          >
            Connect Selected Page
          </Button>
        </div>
      </Modal>
    </div>
  );
};
