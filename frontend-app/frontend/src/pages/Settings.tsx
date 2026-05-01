import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import ForensicStudioLayout from '../components/layout/ForensicStudioLayout';

function Settings() {
  const { theme, setTheme } = useTheme();
  const [textSize, setTextSize] = useState(100);
  const [fontDisplay, setFontDisplay] = useState('Inter');

  return (
    <ForensicStudioLayout
      navRight={
        <Link to="/" className="btn-ghost rounded-2xl text-xs sm:text-sm">
          ← Workspace
        </Link>
      }
    >
      <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:py-10">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4 border-b border-studio pb-6">
          <div>
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.25em] text-muted">Configuration</p>
            <h1 className="text-3xl font-semibold tracking-tight text-text-high sm:text-4xl">Settings</h1>
          </div>
        </div>

        <div className="glass-card border-studio/80 p-6 shadow-panel sm:p-8">
          <div className="border-b border-studio pb-8">
            <div className="mb-6 flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-2xl border border-studio bg-surface text-brand">
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </span>
                <h2 className="text-lg font-semibold text-text-high">Display preferences</h2>
              </div>
            </div>

            <div className="space-y-8 pl-0 sm:pl-2">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <span className="text-sm font-medium text-text-high">Theme</span>
                <div className="flex items-center gap-2 rounded-2xl border border-studio bg-surface p-1">
                  <button
                    type="button"
                    onClick={() => setTheme('light')}
                    className={`rounded-xl p-2.5 transition duration-200 ${
                      theme === 'light'
                        ? 'bg-brand/20 text-brand shadow-soft-glow'
                        : 'text-muted hover:bg-white/5 hover:text-text-high'
                    }`}
                    title="Light mode"
                  >
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    onClick={() => setTheme('dark')}
                    className={`rounded-xl p-2.5 transition duration-200 ${
                      theme === 'dark'
                        ? 'bg-brand/20 text-brand shadow-soft-glow'
                        : 'text-muted hover:bg-white/5 hover:text-text-high'
                    }`}
                    title="Dark mode"
                  >
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                    </svg>
                  </button>
                </div>
              </div>

              <div>
                <div className="mb-2 flex items-center justify-between">
                  <label className="text-sm font-medium text-text-high">Text size</label>
                  <span className="font-mono text-sm text-brand">{textSize}%</span>
                </div>
                <input
                  type="range"
                  min={50}
                  max={150}
                  value={textSize}
                  onChange={(e) => setTextSize(Number(e.target.value))}
                  className="h-2 w-full cursor-pointer appearance-none rounded-full bg-muted/20 accent-brand"
                />
              </div>

              <div>
                <label htmlFor="font-display" className="mb-2 block text-sm font-medium text-text-high">
                  Font display
                </label>
                <div className="relative">
                  <select
                    id="font-display"
                    value={fontDisplay}
                    onChange={(e) => setFontDisplay(e.target.value)}
                    className="input-studio w-full cursor-pointer appearance-none pr-10"
                  >
                    <option>Inter</option>
                    <option>Roboto</option>
                    <option>Open Sans</option>
                    <option>Lato</option>
                    <option>Montserrat</option>
                  </select>
                  <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
                    <svg className="h-5 w-5 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="border-b border-studio py-8">
            <button type="button" className="flex w-full items-center justify-between gap-3 text-left">
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-2xl border border-studio bg-surface text-muted">
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </span>
                <h2 className="text-lg font-semibold text-text-high">Model defaults</h2>
              </div>
              <svg className="h-5 w-5 shrink-0 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>

          <div className="border-b border-studio py-8">
            <button type="button" className="flex w-full items-center justify-between gap-3 text-left">
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-2xl border border-studio bg-surface text-muted">
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </span>
                <h2 className="text-lg font-semibold text-text-high">Advanced settings</h2>
              </div>
              <svg className="h-5 w-5 shrink-0 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>

          <div className="grid grid-cols-1 gap-6 pt-8 md:grid-cols-2">
            <div className="rounded-2xl border border-studio bg-surface/80 p-6 shadow-panel transition duration-200 hover:border-brand/25">
              <div className="mb-4 flex items-center gap-3">
                <span className="text-brand">
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </span>
                <h3 className="text-lg font-semibold text-text-high">Legal & information</h3>
              </div>
              <ul className="space-y-3 text-sm">
                <li>
                  <Link to="/settings/privacy" className="font-medium text-brand transition hover:text-brand/80 hover:underline">
                    Privacy Policy
                  </Link>
                </li>
                <li>
                  <Link to="/settings/terms" className="font-medium text-brand transition hover:text-brand/80 hover:underline">
                    Terms of Service
                  </Link>
                </li>
              </ul>
            </div>

            <div className="rounded-2xl border border-studio bg-surface/80 p-6 shadow-panel transition duration-200 hover:border-brand/25">
              <div className="mb-4 flex items-center gap-3">
                <span className="text-brand-secondary">
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </span>
                <h3 className="text-lg font-semibold text-text-high">Help & feedback</h3>
              </div>
              <p className="mb-4 text-sm leading-relaxed text-muted">
                Suggestions, bugs, or workflow issues — we read every report.
              </p>
              <Link
                to="/settings/feedback"
                className="btn-primary flex w-full items-center justify-center gap-2 py-2.5 text-sm shadow-panel"
              >
                <span>Send feedback</span>
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </ForensicStudioLayout>
  );
}

export default Settings;
