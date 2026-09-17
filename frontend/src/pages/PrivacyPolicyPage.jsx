import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldCheck, ArrowLeft } from 'lucide-react';

export function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      {/* Header / Nav */}
      <header className="border-b border-slate-800 bg-slate-950/60 backdrop-blur sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-400 to-green-600 flex items-center justify-center shadow-lg shadow-emerald-900/30">
              <ShieldCheck className="w-5 h-5 text-white" />
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
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">Legal</span>
            <h1 className="text-3xl sm:text-4xl font-extrabold text-white mt-1">Privacy Policy</h1>
            <p className="text-sm text-slate-400 mt-2">Last updated: September 16, 2026</p>
          </div>

          <div className="prose prose-invert max-w-none text-slate-300 space-y-6 text-sm leading-relaxed">
            <section className="bg-slate-800/40 border border-slate-800 rounded-xl p-6">
              <h2 className="text-lg font-bold text-white mb-2">1. Overview</h2>
              <p>
                SocialPilot ("we", "our", or "us") provides a social media scheduling and analytics management platform.
                This Privacy Policy describes how we collect, store, process, and protect your personal information and
                social platform data when you use our website, services, and web applications.
              </p>
            </section>

            <section className="bg-slate-800/40 border border-slate-800 rounded-xl p-6">
              <h2 className="text-lg font-bold text-white mb-2">2. Information We Collect</h2>
              <ul className="list-disc pl-5 space-y-2 text-slate-300">
                <li><strong className="text-white">Account Information:</strong> Your name, email address, password hash, and profile avatar.</li>
                <li><strong className="text-white">Social Platform Credentials:</strong> When you connect Facebook, Instagram, LinkedIn, X, YouTube, or Pinterest accounts via official OAuth 2.0, we receive authorization codes, encrypted access tokens, and public account identifiers.</li>
                <li><strong className="text-white">Published & Scheduled Content:</strong> Post text, media attachments (images, videos), scheduled dates, and publishing statuses.</li>
                <li><strong className="text-white">Performance Metrics:</strong> Public social engagement statistics (reach, impressions, likes, comments) fetched via provider APIs for your dashboard analytics.</li>
              </ul>
            </section>

            <section className="bg-slate-800/40 border border-slate-800 rounded-xl p-6">
              <h2 className="text-lg font-bold text-white mb-2">3. How We Use Your Data</h2>
              <p>We use your data solely to provide and enhance our services:</p>
              <ul className="list-disc pl-5 space-y-1 mt-2">
                <li>Authenticating you and managing workspace authorization.</li>
                <li>Connecting to authorized social media platforms via official APIs.</li>
                <li>Dispatching scheduled posts and campaigns to your connected accounts.</li>
                <li>Aggregating analytics data and generating performance reports.</li>
              </ul>
              <p className="mt-3 text-emerald-400 font-medium">We never sell, rent, or trade your personal data or social tokens to any third parties.</p>
            </section>

            <section className="bg-slate-800/40 border border-slate-800 rounded-xl p-6">
              <h2 className="text-lg font-bold text-white mb-2">4. Data Security & Token Protection</h2>
              <p>
                All sensitive third-party access tokens and refresh tokens are encrypted at rest using industry-standard
                cryptographic algorithms (Fernet symmetric encryption). All network communication between the client, backend,
                and social platform APIs is strictly conducted over encrypted HTTPS connections.
              </p>
            </section>

            <section className="bg-slate-800/40 border border-slate-800 rounded-xl p-6">
              <h2 className="text-lg font-bold text-white mb-2">5. User Control & Data Deletion</h2>
              <p>
                You retain complete control over your connected accounts. You can revoke access at any time from your
                Dashboard Accounts page, or follow our dedicated{' '}
                <Link to="/data-deletion" className="text-emerald-400 hover:underline">
                  Data Deletion Instructions
                </Link>{' '}
                to request the permanent removal of your stored account data.
              </p>
            </section>

            <section className="bg-slate-800/40 border border-slate-800 rounded-xl p-6">
              <h2 className="text-lg font-bold text-white mb-2">6. Contact Us</h2>
              <p>
                If you have questions regarding this Privacy Policy or your personal information, please contact us at:{' '}
                <span className="text-emerald-400 font-semibold">privacy@socialpilot.test</span>
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

export default PrivacyPolicyPage;
