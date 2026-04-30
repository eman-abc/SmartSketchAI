import { useState } from 'react';
import { Link } from 'react-router-dom';

function TermsOfService() {
  const [expandedSections, setExpandedSections] = useState<Set<number>>(new Set([1]));
  const [activeSection, setActiveSection] = useState(5);

  const toggleSection = (sectionNumber: number) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionNumber)) {
      newExpanded.delete(sectionNumber);
    } else {
      newExpanded.add(sectionNumber);
    }
    setExpandedSections(newExpanded);
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
    <div className="flex-1 overflow-y-auto bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Back to Settings Link */}
        <div className="mb-6">
          <Link to="/settings" className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1 transition-colors">
            <span>←</span>
            <span>Back to Settings</span>
          </Link>
        </div>

        <div className="flex gap-6">
          {/* Main Content Card */}
          <div className="flex-1 bg-white rounded-lg shadow-sm border border-gray-200 p-8">
            {/* Title Section */}
            <div className="mb-8">
              <h1 className="text-4xl font-bold text-gray-900 mb-2">Terms of Service</h1>
              <p className="text-sm text-gray-600">Last updated: August 30, 2025</p>
            </div>

            {/* Accordion Sections */}
            <div className="space-y-4">
              {sections.map((section) => {
                const isExpanded = expandedSections.has(section.number);
                return (
                  <div key={section.number} className="border border-gray-200 rounded-lg overflow-hidden">
                    <button
                      onClick={() => toggleSection(section.number)}
                      className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors text-left"
                    >
                      <div className="flex items-center gap-4">
                        <span className="text-lg font-semibold text-gray-900 min-w-[32px]">
                          {section.number}.
                        </span>
                        <span className="text-lg font-semibold text-gray-900">{section.title}</span>
                      </div>
                      <svg
                        className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                    {isExpanded && (
                      <div className="px-4 pb-4 pl-16">
                        <p className="text-sm text-gray-700 leading-relaxed">{section.content}</p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Table of Contents Sidebar */}
          <div className="w-64 flex-shrink-0">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 sticky top-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Table of Contents</h2>
              <nav className="space-y-1">
                {sections.map((section) => {
                  const isActive = activeSection === section.number;
                  return (
                    <button
                      key={section.number}
                      onClick={() => {
                        setActiveSection(section.number);
                        if (!expandedSections.has(section.number)) {
                          toggleSection(section.number);
                        }
                      }}
                      className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                        isActive
                          ? 'bg-blue-600 text-white font-medium'
                          : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                      }`}
                    >
                      {section.title}
                    </button>
                  );
                })}
              </nav>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TermsOfService;

