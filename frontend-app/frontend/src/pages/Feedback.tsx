import { useState } from 'react';
import { Link } from 'react-router-dom';
import ForensicStudioLayout from '../components/layout/ForensicStudioLayout';

function Feedback() {
  const [feedback, setFeedback] = useState('');
  const [feedbackType, setFeedbackType] = useState('General Feedback');
  const [allowContact, setAllowContact] = useState(false);

  const handleFeedbackChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    if (value.length <= 2000) setFeedback(value);
  };

  return (
    <ForensicStudioLayout
      navRight={
        <Link to="/settings" className="btn-ghost rounded-2xl text-xs sm:text-sm">
          ← Settings
        </Link>
      }
    >
      <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:py-10">
        <div className="glass-card border-studio/80 p-6 shadow-panel sm:p-8">
          <div className="mb-8 border-b border-studio pb-6">
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.25em] text-muted">Support</p>
            <h1 className="text-3xl font-semibold tracking-tight text-text-high">Send feedback</h1>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              Bugs, features, or workflow friction — detail helps us prioritize.
            </p>
          </div>

          <div className="space-y-6">
            <div>
              <label htmlFor="feedback-type" className="mb-2 block text-xs font-semibold uppercase tracking-wider text-muted">
                Feedback type
              </label>
              <div className="relative">
                <select
                  id="feedback-type"
                  value={feedbackType}
                  onChange={(e) => setFeedbackType(e.target.value)}
                  className="input-studio w-full cursor-pointer appearance-none pr-10"
                >
                  <option>General Feedback</option>
                  <option>Bug Report</option>
                  <option>Feature Request</option>
                  <option>Performance Issue</option>
                  <option>Other</option>
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
                  <svg className="h-5 w-5 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
            </div>

            <div>
              <label htmlFor="feedback-text" className="mb-2 block text-xs font-semibold uppercase tracking-wider text-muted">
                Your feedback{' '}
                <span className="font-mono font-normal text-brand/80">({feedback.length}/2000)</span>
              </label>
              <textarea
                id="feedback-text"
                value={feedback}
                onChange={handleFeedbackChange}
                placeholder="Describe steps, expected vs actual behavior, device, and session context if relevant…"
                rows={8}
                className="input-studio min-h-[180px] w-full resize-none"
              />
            </div>

            <div className="flex items-center gap-3 rounded-2xl border border-studio bg-surface/50 px-4 py-3">
              <button
                type="button"
                onClick={() => setAllowContact(!allowContact)}
                className={`relative inline-flex h-7 w-12 shrink-0 items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-brand/40 focus:ring-offset-2 focus:ring-offset-background ${
                  allowContact ? 'bg-brand shadow-soft-glow' : 'bg-muted/30'
                }`}
                role="switch"
                aria-checked={allowContact}
              >
                <span
                  className={`inline-block h-5 w-5 transform rounded-full bg-slate-950 shadow transition-transform duration-200 ${
                    allowContact ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
              <label className="cursor-pointer text-sm text-text-high">
                I agree to be contacted about this feedback
              </label>
            </div>

            <div className="flex flex-wrap justify-end gap-3 border-t border-studio pt-6">
              <Link to="/settings" className="btn-secondary px-6 py-2.5 text-sm">
                Cancel
              </Link>
              <button type="button" className="btn-primary px-6 py-2.5 text-sm shadow-panel">
                Submit feedback
              </button>
            </div>
          </div>
        </div>
      </div>
    </ForensicStudioLayout>
  );
}

export default Feedback;
