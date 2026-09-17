import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Card, CardHeader } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import {
  User,
  Mail,
  ShieldCheck,
  Sun,
  Moon,
  Laptop,
  CheckCircle2,
  Lock,
  LogOut,
  Sparkles,
} from 'lucide-react';

export const SettingsPage = () => {
  const { user, updateProfile, theme, setTheme, logout } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState('');

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setSaveError('');
    setSaveSuccess(false);
    setIsSaving(true);

    try {
      await updateProfile({ full_name: fullName });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      setSaveError(err.response?.data?.detail || 'Failed to update profile.');
    } finally {
      setIsSaving(false);
    }
  };

  const formatRole = (role) => {
    if (!role) return 'Content Creator';
    return role.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Page Title */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 font-heading">
          Account & Appearance Settings
        </h1>
        <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
          Manage your personal profile, security permissions, and visual theme preferences
        </p>
      </div>

      {/* 1. Profile Management Card */}
      <Card>
        <CardHeader
          title="Profile Information"
          description="Update your personal details. Sensitive attributes (ID, Email, Role) are protected by backend RBAC."
        />

        <form onSubmit={handleProfileSubmit} className="mt-6 space-y-4">
          {saveSuccess && (
            <div className="flex items-center gap-2 rounded-xl bg-emerald-500/10 p-3 text-xs text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 font-semibold">
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
              <span>Profile updated successfully!</span>
            </div>
          )}

          {saveError && (
            <div className="rounded-xl bg-rose-500/10 p-3 text-xs text-rose-600 dark:text-rose-400 border border-rose-500/20">
              {saveError}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-800 dark:text-slate-200 mb-1.5">
                Full Name
              </label>
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 dark:text-slate-500 pointer-events-none" aria-hidden="true" />
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Your full name"
                  className="sp-input w-full rounded-xl py-2.5 pl-10 pr-4 text-sm transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-800 dark:text-slate-200 mb-1.5">
                Email Address (Read Only)
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 dark:text-slate-500 pointer-events-none" aria-hidden="true" />
                <input
                  type="email"
                  disabled
                  value={user?.email || ''}
                  className="sp-input w-full rounded-xl py-2.5 pl-10 pr-4 text-sm opacity-60 cursor-not-allowed"
                />
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between p-4 rounded-xl border" style={{ background: 'var(--sp-surface-2)', borderColor: 'var(--sp-border)' }}>
            <div>
              <p className="text-xs font-bold text-slate-900 dark:text-slate-100 font-heading">
                Assigned Workspace Role
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Controls module access and team publishing permissions across SocialPilot
              </p>
            </div>
            <Badge variant="primary" size="md">
              <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
              {formatRole(user?.role)}
            </Badge>
          </div>

          <div className="flex justify-end pt-2">
            <Button type="submit" variant="primary" isLoading={isSaving}>
              Save Profile Changes
            </Button>
          </div>
        </form>
      </Card>

      {/* 2. Theme & Appearance Selector */}
      <Card>
        <CardHeader
          title="Appearance & Theme"
          description="Select your preferred visual atmosphere (Settings → Appearance → Theme)"
        />

        <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Light Theme Option (Option 2: Cyber Cyan & Aurora Emerald) */}
          <button
            type="button"
            onClick={() => setTheme('light')}
            className={`flex flex-col items-center justify-center p-5 rounded-2xl border-2 transition-all cursor-pointer ${
              theme === 'light'
                ? 'border-cyan-500 bg-cyan-50/40 text-cyan-950 shadow-md shadow-cyan-500/10'
                : 'border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800'
            }`}
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-tr from-sky-400 to-emerald-400 text-white mb-3 shadow-xs">
              <Sun className="h-6 w-6" aria-hidden="true" />
            </div>
            <span className="text-sm font-bold text-slate-900 dark:text-slate-100 font-heading">
              Light Mode
            </span>
            <span className="text-[11px] text-cyan-700 dark:text-slate-400 font-semibold mt-1">
              Cyber Cyan & Aurora Emerald
            </span>
          </button>

          {/* Dark Theme Option (Option 1: Electric Neon & Cosmic Violet) */}
          <button
            type="button"
            onClick={() => setTheme('dark')}
            className={`flex flex-col items-center justify-center p-5 rounded-2xl border-2 transition-all cursor-pointer ${
              theme === 'dark'
                ? 'border-violet-500 bg-violet-950/30 text-violet-200 shadow-md shadow-violet-500/15'
                : 'border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800'
            }`}
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-tr from-indigo-500 via-purple-500 to-pink-500 text-white mb-3 shadow-xs">
              <Moon className="h-6 w-6" aria-hidden="true" />
            </div>
            <span className="text-sm font-bold text-slate-900 dark:text-slate-100 font-heading">
              Dark Mode
            </span>
            <span className="text-[11px] text-violet-400 dark:text-violet-300 font-semibold mt-1">
              Electric Neon & Cosmic Violet
            </span>
          </button>

          {/* System Default Option */}
          <button
            type="button"
            onClick={() => setTheme('system')}
            className={`flex flex-col items-center justify-center p-5 rounded-2xl border-2 transition-all cursor-pointer ${
              theme === 'system'
                ? 'border-slate-400 dark:border-slate-600 bg-slate-100 dark:bg-slate-800 shadow-xs'
                : 'border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800'
            }`}
          >
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 mb-3">
              <Laptop className="h-6 w-6" aria-hidden="true" />
            </div>
            <span className="text-sm font-bold text-slate-900 dark:text-slate-100 font-heading">
              System Default
            </span>
            <span className="text-[11px] text-slate-400 mt-1 font-medium">Sync with OS appearance</span>
          </button>
        </div>
      </Card>

      {/* 3. Security & Sign Out Card */}
      <Card>
        <CardHeader
          title="Security & Session"
          description="Account session tokens and authentication state"
        />

        <div className="mt-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 py-2">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400">
              <Lock className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <p className="text-xs font-bold text-slate-900 dark:text-slate-100 font-heading">
                JWT Authentication Active
              </p>
              <p className="text-[11px] text-slate-400">
                Encrypted token persistence with automatic refresh and route protection
              </p>
            </div>
          </div>

          <Button variant="danger" size="md" icon={LogOut} onClick={logout}>
            Sign Out
          </Button>
        </div>
      </Card>
    </div>
  );
};
