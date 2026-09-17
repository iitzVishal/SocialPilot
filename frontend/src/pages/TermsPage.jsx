import React from 'react';
import { Link } from 'react-router-dom';
import { FileText, ArrowLeft } from 'lucide-react';

export function TermsPage() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 flex flex-col">
      {/* Header / Nav */}
      <header className="border-b border-slate-800 bg-slate-950/60 backdrop-blur sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-400 to-green-600 flex items-center justify-center shadow-lg shadow-emerald-900/30">
              <FileText className="w-5 h-5 text-white" />
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
            <h1 className="text-3xl sm:text-4xl font-extrabold text-white mt-1">Terms of Service</h1>
            <p className="text-sm text-slate-400 mt-2">Last updated: September 16, 2026</p>
          </div>

          <div className="prose prose-invert max-w-none text-slate-300 space-y-6 text-sm leading-relaxed">
            <section className="bg-slate-800/40 border border-slate-800 rounded-xl p-6">
              <h2 className="text-lg font-bold text-white mb-2">1. Agreement to Terms</h2>
              <p>
                By creating an account, accessing, or using SocialPilot, you agree to be bound by these Terms of Service.
                If you do not agree to these terms, you may not access or use the platform.
              </p>
            </section>

            <section className="bg-slate-800/40 border border-slate-800 rounded-xl p-6">
              <h2 className="text-lg font-bold text-white mb-2">2. Acceptable Use & Account Responsibilities</h2>
              <p>
                You agree to use SocialPilot only for lawful purposes in compliance with all applicable laws and regulations.
                You are responsible for maintaining the confidentiality of your credentials and for all activities that occur
                under your account.
              </p>
              <ul className="list-disc pl-5 space-y-1 mt-2">
                <li>Do not publish spam, defamatory, infringing, or harmful content.</li>
                <li>Do not attempt to compromise the security or integrity of SocialPilot systems.</li>
                <li>Comply with all community guidelines and terms set forth by supported social media platforms.</li>
              </ul>
            </section>

            <section className="bg-slate-800/40 border border-slate-800 rounded-xl p-6">
              <h2 className="text-lg font-bold text-white mb-2">3. Third-Party Platform Policies</h2>
              <p>
                SocialPilot interacts with third-party APIs including Meta (Facebook & Instagram), LinkedIn, X, Google (YouTube),
                and Pinterest. By connecting your accounts, you agree to abide by the respective terms and developer policies
                of each platform:
              </p>
              <ul className="list-disc pl-5 space-y-1 mt-2">
                <li><a href="https://www.facebook.com/terms.php" target="_blank" rel="noreferrer" className="text-emerald-400 hover:underline">Meta Terms of Service</a> and Platform Policies</li>
                <li><a href="https://www.youtube.com/t/terms" target="_blank" rel="noreferrer" className="text-emerald-400 hover:underline">YouTube Terms of Service</a></li>
                <li><a href="https://twitter.com/en/tos" target="_blank" rel="noreferrer" className="text-emerald-400 hover:underline">X Developer Agreement</a></li>
                <li><a href="https://www.linkedin.com/legal/user-agreement" target="_blank" rel="noreferrer" className="text-emerald-400 hover:underline">LinkedIn User Agreement</a></li>
              </ul>
            </section>

            <section className="bg-slate-800/40 border border-slate-800 rounded-xl p-6">
              <h2 className="text-lg font-bold text-white mb-2">4. Termination & Account Cancellation</h2>
              <p>
                We reserve the right to suspend or terminate your account if you violate these terms or any applicable
                platform rules. You may cancel your account at any time through your dashboard settings.
              </p>
            </section>

            <section className="bg-slate-800/40 border border-slate-800 rounded-xl p-6">
              <h2 className="text-lg font-bold text-white mb-2">5. Disclaimer of Warranties & Limitation of Liability</h2>
              <p>
                SocialPilot is provided "as is" and "as available". We are not liable for any third-party network outages,
                API changes, account suspensions on external platforms, or indirect damages arising from use of our services.
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

export default TermsPage;
