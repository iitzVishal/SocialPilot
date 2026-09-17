import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../components/ui/Button';
import { Sparkles, Mail, ArrowLeft, Info } from 'lucide-react';

export const ForgotPasswordPage = () => {
  const [email, setEmail] = useState('');
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setIsSubmitted(true);
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[#f0f9ff] dark:bg-[#0b0f19] relative overflow-hidden transition-colors">
      {/* Ambient background gradients */}
      <div className="absolute -top-40 -right-40 h-96 w-96 rounded-full bg-cyan-500/15 dark:bg-pink-500/15 blur-3xl pointer-events-none" aria-hidden="true" />
      <div className="absolute -bottom-40 -left-40 h-96 w-96 rounded-full bg-emerald-500/15 dark:bg-violet-600/15 blur-3xl pointer-events-none" aria-hidden="true" />

      <div className="w-full max-w-md relative z-10">
        {/* Brand Logo Header */}
        <div className="text-center mb-8">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-tr from-sky-500 via-cyan-500 to-emerald-500 dark:from-indigo-600 dark:via-purple-600 dark:to-pink-600 text-white shadow-lg shadow-cyan-500/25 dark:shadow-purple-500/25 mb-4">
            <Sparkles className="h-6 w-6" aria-hidden="true" />
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white font-heading">
            Reset your password
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1 font-medium">
            Enter your account email to receive recovery instructions
          </p>
        </div>

        {/* Card Form */}
        <div className="rounded-2xl border border-slate-200/90 bg-white p-8 shadow-xl dark:border-slate-800 dark:bg-slate-900/95 transition-standard">
          {/* Milestone notice */}
          <div className="mb-6 flex items-start gap-3 rounded-xl border border-cyan-500/20 dark:border-violet-500/20 bg-cyan-50/50 dark:bg-violet-950/40 p-3.5 text-xs text-cyan-900 dark:text-violet-300 font-medium">
            <Info className="h-4 w-4 flex-shrink-0 mt-0.5 text-cyan-600 dark:text-violet-400" aria-hidden="true" />
            <span>
              <strong>Note:</strong> Automated email password reset workflows are scheduled for an upcoming security release.
            </span>
          </div>

          {isSubmitted ? (
            <div className="text-center py-4 space-y-4">
              <div className="p-3 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-500/20 rounded-xl text-xs text-emerald-700 dark:text-emerald-300 font-medium">
                If an account exists for <strong>{email}</strong>, password reset instructions will be sent once the email service is activated.
              </div>
              <Link to="/login" className="inline-block">
                <Button variant="outline" size="md" icon={ArrowLeft}>
                  Return to Sign In
                </Button>
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-800 dark:text-slate-200 mb-1.5 font-heading">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 dark:text-slate-500 pointer-events-none" aria-hidden="true" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@company.com"
                    className="w-full rounded-xl border border-slate-300 bg-white py-2.5 pl-10 pr-4 text-sm text-slate-900 placeholder:text-slate-500 focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:placeholder:text-slate-400 dark:focus:border-violet-400 dark:focus:bg-slate-800 transition-colors"
                  />
                </div>
              </div>

              <Button
                type="submit"
                variant="primary"
                size="lg"
                className="w-full mt-2"
              >
                Send Reset Link
              </Button>
            </form>
          )}

          <div className="mt-6 text-center border-t border-slate-100 dark:border-slate-800 pt-4">
            <Link
              to="/login"
              className="inline-flex items-center gap-1.5 text-xs font-bold text-cyan-600 hover:text-cyan-700 dark:text-violet-400 dark:hover:text-violet-300 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 dark:focus-visible:ring-violet-500 rounded-sm"
            >
              <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
              Back to Sign In
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
