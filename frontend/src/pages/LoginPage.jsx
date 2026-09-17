import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/Button';
import { GoogleSignInButton } from '../components/auth/GoogleSignInButton';
import { Lock, Mail, AlertCircle, Eye, EyeOff } from 'lucide-react';

export const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const searchParams = new URLSearchParams(location.search);
  const redirectParam = searchParams.get('redirect');
  const from = redirectParam || location.state?.from?.pathname || '/dashboard';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      const msg = err.response?.data?.detail || 'Authentication failed. Please check your credentials.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden transition-colors"
      style={{ background: 'var(--sp-bg)', color: 'var(--sp-text)' }}
    >
      {/* Ambient background glows */}
      <div className="absolute -top-40 -right-40 h-96 w-96 rounded-full blur-3xl pointer-events-none"
        style={{ background: 'radial-gradient(circle, rgba(34, 197, 94, 0.12) 0%, transparent 70%)' }}
        aria-hidden="true"
      />
      <div className="absolute -bottom-40 -left-40 h-96 w-96 rounded-full blur-3xl pointer-events-none"
        style={{ background: 'radial-gradient(circle, rgba(22, 163, 74, 0.08) 0%, transparent 70%)' }}
        aria-hidden="true"
      />

      <div className="w-full max-w-md relative z-10">
        {/* Brand Logo Header */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 mb-4 group text-decoration-none">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl text-white shadow-lg transition-transform group-hover:scale-105"
              style={{ background: 'linear-gradient(135deg, #15803D, #22C55E)', boxShadow: '0 0 24px rgba(34,197,94,0.3)' }}
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M12 2L4 6v6c0 5.25 3.5 10.15 8 11.35C16.5 22.15 20 17.25 20 12V6l-8-4z" fill="white" opacity="0.9"/>
                <path d="M9 12l2 2 4-4" stroke="#15803D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
          </Link>
          <h1 className="text-2xl font-extrabold tracking-tight font-heading" style={{ color: 'var(--sp-text)' }}>
            Welcome back to SocialPilot
          </h1>
          <p className="text-sm mt-1 font-medium" style={{ color: 'var(--sp-text-secondary)' }}>
            Sign in to manage your cross-platform social presence
          </p>
        </div>

        {/* Card Form */}
        <div className="rounded-2xl p-8 transition-all"
          style={{ background: 'var(--sp-card)', border: '1px solid var(--sp-border)', boxShadow: 'var(--shadow-card)' }}
        >
          {/* Google Sign-In */}
          <GoogleSignInButton onSuccess={() => navigate(from, { replace: true })} text="Continue with Google" />

          {/* Divider */}
          <div className="relative my-6 flex items-center justify-center">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t" style={{ borderColor: 'var(--sp-border)' }} />
            </div>
            <div className="relative px-3 text-xs font-bold uppercase tracking-wider" style={{ background: 'var(--sp-card)', color: 'var(--sp-text-muted)' }}>
              OR
            </div>
          </div>

          {error && (
            <div className="mb-6 flex items-start gap-3 rounded-xl p-3.5 text-xs font-medium"
              style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.25)', color: '#EF4444' }}
              role="alert"
            >
              <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email Field */}
            <div>
              <label className="block text-xs font-bold mb-1.5 font-heading" style={{ color: 'var(--sp-text)' }}>
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 pointer-events-none" style={{ color: 'var(--sp-text-muted)' }} aria-hidden="true" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  autoComplete="email"
                  className="w-full rounded-xl py-2.5 pl-10 pr-4 text-sm transition-all focus:outline-none"
                  style={{ background: 'var(--input-bg)', border: '1px solid var(--input-border)', color: 'var(--input-text)' }}
                />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-bold font-heading" style={{ color: 'var(--sp-text)' }}>
                  Password
                </label>
                <Link
                  to="/forgot-password"
                  className="text-xs font-semibold hover:underline rounded-sm"
                  style={{ color: 'var(--sp-primary)' }}
                >
                  Forgot Password?
                </Link>
              </div>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 pointer-events-none" style={{ color: 'var(--sp-text-muted)' }} aria-hidden="true" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  className="w-full rounded-xl py-2.5 pl-10 pr-10 text-sm transition-all focus:outline-none"
                  style={{ background: 'var(--input-bg)', border: '1px solid var(--input-border)', color: 'var(--input-text)' }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-lg transition-colors cursor-pointer"
                  style={{ color: 'var(--sp-text-muted)' }}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {/* Remember Me */}
            <div className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                id="remember"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="h-4 w-4 rounded cursor-pointer"
                style={{ accentColor: 'var(--sp-primary)' }}
              />
              <label htmlFor="remember" className="text-xs font-medium cursor-pointer" style={{ color: 'var(--sp-text-secondary)' }}>
                Remember this device for 30 days
              </label>
            </div>

            {/* Submit Button */}
            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full mt-2"
              isLoading={isLoading}
            >
              Sign In to SocialPilot
            </Button>
          </form>
        </div>

        {/* Footer Link */}
        <p className="text-center text-xs mt-6" style={{ color: 'var(--sp-text-muted)' }}>
          Don't have an account yet?{' '}
          <Link to="/register" className="font-semibold hover:underline" style={{ color: 'var(--sp-primary)' }}>
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
};
