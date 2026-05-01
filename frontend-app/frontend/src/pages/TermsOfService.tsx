import { useState } from 'react';
import { Link } from 'react-router-dom';
import ForensicStudioLayout from '../components/layout/ForensicStudioLayout';

function TermsOfService() {
  const [expandedSections, setExpandedSections] = useState<Set<number>>(new Set([1]));
  const [activeSection, setActiveSection] = useState(5);

  const toggleSection = (sectionNumber: number) => {
    const next = new Set(expandedSections);
    if (next.has(sectionNumber)) next.delete(sectionNumber);
    else next.add(sectionNumber);
    setExpandedSections(next);
  };

  const sections = [
    { number: 1, title: 'Acceptance of Terms', content: 'By accessing and using SmartSketch AI, you accept and agree to be bound by the terms and provision of this agreement. If you do not agree to abide by the above, please do not use this service.' },
    { number: 2, title: 'User Accounts', content: 'You are responsible for maintaining the confidentiality of your account and password. You agree to accept responsibility for all activities that occur under your account or password.' },
    { number: 3, title: 'Content Ownership', content: 'You retain ownership of all content you create using SmartSketch AI. However, by using our service, you grant us a license to use, store, and process your content as necessary to provide the service.' },
    { number: 4, title: 'Prohibited Uses', content: 'You may not use SmartSketch AI for any illegal or unauthorized purpose. You agree not to use the service to violate any laws, infringe on any rights, or transmit any harmful or malicious code.' },
    { number: 5, title: 'Disclaimers', content: 'SmartSketch AI is provided "as is" without warranties of any kind, either express or implied. We do not guarantee that the service will be uninterrupted, secure, or error-free.' },
    { number: 6, title: 'Limitation of Liability', content: 'To the fullest extent permitted by law, SmartSketch AI shall not be liable for any indirect, incidental, special, consequential, or punitive damages resulting from your use of the service.' },
    { number: 7, title: 'Governing Law', content: 'These terms shall be governed by and construed in accordance with the laws of the jurisdiction in which SmartSketch AI operates, without regard to its conflict of law provisions.' },
    { number: 8, title: 'Changes to Terms', content: 'We reserve the right to modify these terms at any time. We will notify users of any changes by posting the new terms on this page and updating the "Last updated" date.' },
    { number: 9, title: 'Contact Information', content: 'If you have any questions about these Terms of Service, please contact us through our support channels or visit our Help & Support section in the application.' },
  ];

  return (
    <ForensicStudioLayout
      navRight={
        <Link to="/settings" className="btn-ghost rounded-2xl text-xs sm:text-sm">
          ← Settings
        </Link>
      }
    >
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:py-10">
        <div className="flex flex-col gap-8 lg:flex-row lg:gap-10">
          <div className="glass-card min-w-0 flex-1 border-studio/80 p-6 shadow-panel sm:p-8">
            <div className="mb-8 border-b border-studio pb-8">
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.25em] text-muted">Legal</p>
              <h1 className="text-3xl font-semibold tracking-tight text-text-high sm:text-4xl">Terms of Service</h1>
              <p className="mt-2 text-sm text-muted">Last updated: August 30, 2025</p>
            </div>

            <div className="space-y-3">
              {sections.map((section) => {
                const isExpanded = expandedSections.has(section.number);
                return (
                  <div
                    key={section.number}
                    className="overflow-hidden rounded-2xl border border-studio bg-surface/40 transition hover:border-brand/25"
                  >
                    <button
                      type="button"
                      onClick={() => toggleSection(section.number)}
                      className="flex w-full items-center justify-between gap-3 p-4 text-left transition hover:bg-white/[0.03] sm:p-5"
                    >
                      <div className="flex min-w-0 items-center gap-3 sm:gap-4">
                        <span className="shrink-0 font-mono text-sm font-semibold text-brand sm:text-base">
                          {section.number}.
                        </span>
                        <span className="text-base font-semibold text-text-high sm:text-lg">{section.title}</span>
                      </div>
                      <svg
                        className={`h-5 w-5 shrink-0 text-muted transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                        aria-hidden
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                    {isExpanded && (
                      <div className="border-t border-studio px-4 pb-4 pl-12 pr-4 sm:px-5 sm:pb-5 sm:pl-16">
                        <p className="text-sm leading-relaxed text-muted">{section.content}</p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <aside className="w-full shrink-0 lg:w-64">
            <div className="glass-card sticky top-20 border-studio/80 p-5 shadow-panel lg:top-24">
              <h2 className="mb-4 border-b border-studio pb-3 text-sm font-semibold uppercase tracking-[0.15em] text-muted">
                Contents
              </h2>
              <nav className="space-y-1">
                {sections.map((section) => {
                  const isActive = activeSection === section.number;
                  return (
                    <button
                      key={section.number}
                      type="button"
                      onClick={() => {
                        setActiveSection(section.number);
                        if (!expandedSections.has(section.number)) toggleSection(section.number);
                      }}
                      className={`w-full rounded-xl px-3 py-2.5 text-left text-sm transition duration-200 ${
                        isActive
                          ? 'bg-brand/20 font-semibold text-brand shadow-soft-glow'
                          : 'text-muted hover:bg-white/5 hover:text-text-high'
                      }`}
                    >
                      {section.title}
                    </button>
                  );
                })}
              </nav>
            </div>
          </aside>
        </div>
      </div>
    </ForensicStudioLayout>
  );
}

export default TermsOfService;
