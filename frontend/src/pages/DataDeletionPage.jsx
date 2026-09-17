import React from 'react';
import { Link } from 'react-router-dom';
import { Trash2, ArrowLeft, CheckCircle2 } from 'lucide-react';

export function DataDeletionPage() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      {/* Header / Nav */}
      <header className="border-b border-slate-800 bg-slate-950/60 backdrop-blur sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-400 to-green-600 flex items-center justify-center shadow-lg shadow-emerald-900/30">
              <Trash2 className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg text-white">SocialPilot</span>
          </Link>
          <Link
            to="/"
            className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-emerald-400 transition"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Home
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-4xl mx-auto px-4 sm:px-6 py-12">
        <div className="space-y-8">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">Meta Platform Compliance</span>
            <h1 className="text-3xl sm:text-4xl font-extrabold text-white mt-1">User Data Deletion Instructions</h1>
            <p className="text-sm text-slate-400 mt-2">
              In accordance with Meta Platform Policy and international privacy laws, you have the right to request the complete deletion of your data collected by SocialPilot.
            </p>
          </div>

          <div className="prose prose-invert max-w-none text-slate-300 space-y-6 text-sm leading-relaxed">
            {/* Option 1 */}
            <section className="bg-slate-800/40 border border-slate-800 rounded-xl p-6">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <h2 className="text-lg font-bold text-white">Option 1: Disconnect and Delete Within SocialPilot (Instant)</h2>
              </div>
              <p>You can instantly delete all stored access tokens and platform connections directly from your SocialPilot account:</p>
              <ol className="list-decimal pl-5 space-y-1 mt-2">
                <li>Log in to your SocialPilot account at <Link to="/login" className="text-emerald-400 hover:underline">socialpilot.com/login</Link>.</li>
                <li>Navigate to <strong className="text-white">Dashboard &rarr; Accounts</strong>.</li>
                <li>Find your connected Facebook or Instagram account.</li>
                <li>Click the <strong className="text-rose-400">Disconnect</strong> button and confirm deletion.</li>
              </ol>
              <p className="mt-2 text-xs text-slate-400">This action immediately purges your encrypted OAuth access token and account association from our database.</p>
            </section>

            {/* Option 2 */}
            <section className="bg-slate-800/40 border border-slate-800 rounded-xl p-6">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <h2 className="text-lg font-bold text-white">Option 2: Revoke Access via Facebook / Meta Settings</h2>
              </div>
              <p>You can remove SocialPilot permissions directly from your Facebook account:</p>
              <ol className="list-decimal pl-5 space-y-1 mt-2">
                <li>Go to your Facebook account's <strong className="text-white">Settings &amp; Privacy &rarr; Settings</strong>.</li>
                <li>Click on <strong className="text-white">Apps and Websites</strong> in the left-hand menu.</li>
                <li>Find <strong className="text-white">SocialPilot</strong> in the list of active apps.</li>
                <li>Click <strong className="text-white">Remove</strong>.</li>
                <li>Check the box to delete all posts, videos, or events that SocialPilot may have published on your behalf, then click <strong className="text-white">Remove</strong>.</li>
              </ol>
            </section>

            {/* Option 3 */}
            <section className="bg-slate-800/40 border border-slate-800 rounded-xl p-6">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <h2 className="text-lg font-bold text-white">Option 3: Request Complete Account &amp; Data Purge via Email</h2>
              </div>
              <p>
                To request permanent deletion of your complete SocialPilot user account, team memberships, scheduled posts,
                and associated analytical records:
              </p>
              <p className="mt-2">
                Send an email from your registered account email to:{' '}
                <span className="text-emerald-400 font-semibold">support@socialpilot.test</span> with the subject line:{' '}
                <code className="bg-slate-800 px-2 py-0.5 rounded text-emerald-300">Data Deletion Request</code>.
              </p>
              <p className="mt-2 text-xs text-slate-400">
                Our support team will process your request and permanently delete all records within 48 hours, sending you a confirmation email upon completion.
              </p>
            </section>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 bg-slate-950/60 py-6 text-center text-xs text-slate-500">
        <div className="max-w-5xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <span>&copy; 2026 SocialPilot. All rights reserved.</span>
          <div className="flex gap-4">
            <Link to="/privacy-policy" className="hover:text-slate-300">Privacy Policy</Link>
            <Link to="/terms" className="hover:text-slate-300">Terms of Service</Link>
            <Link to="/data-deletion" className="hover:text-slate-300">Data Deletion</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default DataDeletionPage;
