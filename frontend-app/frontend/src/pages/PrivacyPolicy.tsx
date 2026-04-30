import { Link } from 'react-router-dom';

function PrivacyPolicy() {
  return (
    <div className="flex-1 overflow-y-auto bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Back to Settings Link */}
        <div className="mb-6">
          <Link to="/settings" className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1 transition-colors">
            <span>←</span>
            <span>Back to Settings</span>
          </Link>
        </div>

        {/* Main Content Card */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
          {/* Title Section */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">Privacy Policy</h1>
            <p className="text-sm text-gray-600">Last Updated: August 30, 2025</p>
          </div>

          {/* Key Takeaways Box */}
          <div className="bg-gray-50 rounded-lg border border-gray-200 p-6 mb-8">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">++ Key Takeaways</h2>
            <p className="text-sm text-gray-700 mb-4 leading-relaxed">
              We value your privacy. This summary provides a high-level overview of how we handle your data. For full details, please read the sections below.
            </p>
            <ul className="space-y-2 text-sm text-gray-700">
              <li className="flex items-start gap-2">
                <span className="text-gray-400 mt-1">•</span>
                <span>We collect personal data you provide and usage data to improve our services.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-gray-400 mt-1">•</span>
                <span>Your generated images and prompts are processed but remain your intellectual property.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-gray-400 mt-1">•</span>
                <span>We use industry-standard security measures to protect your information.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-gray-400 mt-1">•</span>
                <span>You have the right to access, correct, or delete your personal data.</span>
              </li>
            </ul>
          </div>

          {/* Table of Contents */}
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Table of Contents</h2>
            <ol className="space-y-2 text-sm text-gray-700">
              <li className="flex items-start gap-3">
                <span className="text-gray-500 font-medium min-w-[24px]">1.</span>
                <span className="hover:text-gray-900 cursor-pointer transition-colors">Introduction</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-gray-500 font-medium min-w-[24px]">2.</span>
                <span className="hover:text-gray-900 cursor-pointer transition-colors">Information We Collect</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-gray-500 font-medium min-w-[24px]">3.</span>
                <span className="hover:text-gray-900 cursor-pointer transition-colors">How We Use Your Information</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-gray-500 font-medium min-w-[24px]">4.</span>
                <span className="hover:text-gray-900 cursor-pointer transition-colors">Data Sharing and Disclosure</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-gray-500 font-medium min-w-[24px]">5.</span>
                <span className="hover:text-gray-900 cursor-pointer transition-colors">Data Retention and Security</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-gray-500 font-medium min-w-[24px]">6.</span>
                <span className="hover:text-gray-900 cursor-pointer transition-colors">Your Rights and Choices</span>
              </li>
            </ol>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PrivacyPolicy;

