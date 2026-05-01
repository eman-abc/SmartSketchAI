import { Link } from 'react-router-dom';
import ForensicStudioLayout from '../components/layout/ForensicStudioLayout';

function PrivacyPolicy() {
  return (
    <ForensicStudioLayout
      navRight={
        <Link to="/settings" className="btn-ghost rounded-2xl text-xs sm:text-sm">
          ← Settings
        </Link>
      }
    >
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:py-10">
        <div className="glass-card border-studio/80 p-6 shadow-panel sm:p-10">
          <div className="mb-8 border-b border-studio pb-8">
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.25em] text-muted">Legal</p>
            <h1 className="text-3xl font-semibold tracking-tight text-text-high sm:text-4xl">Privacy Policy</h1>
            <p className="mt-2 text-sm text-muted">Last updated: August 30, 2025</p>
          </div>

          <div className="mb-10 rounded-2xl border border-studio bg-surface/60 p-6">
            <h2 className="mb-3 text-lg font-semibold text-text-high">Key takeaways</h2>
            <p className="mb-4 text-sm leading-relaxed text-muted">
              Summary of how we handle your data; see below for full detail.
            </p>
            <ul className="space-y-2.5 text-sm leading-relaxed text-text-high/90">
              <li className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand shadow-soft-glow" aria-hidden />
                <span>We collect personal data you provide and usage data to improve our services.</span>
              </li>
              <li className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand shadow-soft-glow" aria-hidden />
                <span>Generated images and prompts are processed but remain your intellectual property.</span>
              </li>
              <li className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand shadow-soft-glow" aria-hidden />
                <span>Industry-standard safeguards are applied to protect your information.</span>
              </li>
              <li className="flex gap-2">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand shadow-soft-glow" aria-hidden />
                <span>You may request access, correction, or deletion of personal data.</span>
              </li>
            </ul>
          </div>

          <div>
            <h2 className="mb-4 text-xl font-semibold text-text-high">Table of contents</h2>
            <ol className="space-y-3 text-sm text-muted">
              {[
                'Introduction',
                'Information we collect',
                'How we use your information',
                'Data sharing and disclosure',
                'Data retention and security',
                'Your rights and choices',
              ].map((title, i) => (
                <li key={title} className="flex gap-3">
                  <span className="mt-0.5 font-mono text-brand">{i + 1}.</span>
                  <span className="text-text-high/90 transition hover:text-brand">{title}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>
    </ForensicStudioLayout>
  );
}

export default PrivacyPolicy;
