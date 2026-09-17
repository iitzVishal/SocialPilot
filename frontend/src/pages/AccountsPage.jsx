import React, { useState, useEffect } from 'react';
import { accountsAPI, oauthAPI } from '../lib/api';
import { useTeam } from '../context/TeamContext';
import { Card, CardHeader } from '../components/ui/Card';
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

  // Process OAuth Callback Query Parameters
  useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search);
    const statusParam = searchParams.get('status');
    const providerParam = searchParams.get('platform') || searchParams.get('provider');
    const messageParam = searchParams.get('message');
    const accountNameParam = searchParams.get('account_name');

    if (statusParam === 'success') {
      const name = accountNameParam ? decodeURIComponent(accountNameParam) : (providerParam || 'Social');
      showToast(`Connected ${name} account successfully via official OAuth 2.0!`, 'success');
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (statusParam === 'error') {
      const msg = messageParam ? decodeURIComponent(messageParam) : `OAuth authorization failed for ${providerParam || 'provider'}.`;
      showToast(msg, 'error');
      window.history.replaceState({}, document.title, window.location.pathname);
    }

    fetchAccounts(selectedPlatform);
  }, [selectedPlatform, activeTeamId]);

  // Handle Initiating Official OAuth Authorization Code Flow
  const handleInitiateOAuth = async (providerId) => {
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

  // Sync Trigger
  const handleSyncAccount = async (account) => {
    try {
      setActionLoading(true);
      const res = await accountsAPI.sync(account.id);
      showToast(res.data.message || `Synchronized ${account.account_name} successfully!`);
      fetchAccounts(selectedPlatform);
    } catch (err) {
      console.error('Sync error:', err);
      showToast('Failed to trigger synchronization workflow.', 'error');
    } finally {
      setActionLoading(false);
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

            return (
              <Card key={account.id} hover className="flex flex-col justify-between">
                <div>
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div
                        className={`flex h-11 w-11 items-center justify-center rounded-xl ${brandStyle.bg} ${brandStyle.border} border ${brandStyle.color} font-bold text-xs shadow-2xs`}
                      >
                        {account.platform.slice(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 font-heading">
                          {account.account_name}
                        </h3>
                        <p className="text-[11px] text-slate-400 font-mono">
                          ID: {account.account_identifier}
                        </p>
                      </div>
                    </div>
                    <Badge
                      variant={isConnected ? (isExpired ? 'warning' : 'success') : 'danger'}
                      size="xs"
                    >
                      {isConnected ? (isExpired ? 'Expired' : 'Connected') : 'Revoked'}
                    </Badge>
                  </div>

                  {/* Account Metadata */}
                  <div className="mt-4 space-y-2 rounded-xl p-3.5 border text-[11px]" style={{ background: 'var(--sp-surface-2)', borderColor: 'var(--sp-border)' }}>
                    <div className="flex justify-between text-slate-500">
                      <span>Platform:</span>
                      <span className="font-bold text-slate-700 dark:text-slate-300 uppercase">
                        {account.platform}
                      </span>
                    </div>
                    <div className="flex justify-between text-slate-500">
                      <span>Last Sync:</span>
                      <span className="font-medium text-slate-700 dark:text-slate-300">
                        {account.last_synced_at
                          ? new Date(account.last_synced_at).toLocaleString()
                          : 'Never synced'}
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
                    title="Trigger Synchronization"
                    aria-label="Trigger Synchronization"
                    onClick={() => handleSyncAccount(account)}
                    className="p-2"
                  >
                    <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
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

        <div className="mt-4 rounded-xl p-3 text-[11px] border" style={{ background: 'var(--active-nav-bg)', borderColor: 'var(--sp-border)', color: 'var(--sp-text-secondary)' }}>
          <ShieldCheck className="h-4 w-4 inline mr-1 text-emerald-500" aria-hidden="true" />
          <strong>Secure Authentication:</strong> You will be redirected to the provider's official login page. Access tokens are encrypted with AES-256 before storage.
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
    </div>
  );
};
