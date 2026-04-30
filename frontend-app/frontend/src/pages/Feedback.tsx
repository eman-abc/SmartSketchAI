import { useState } from 'react';
import { Link } from 'react-router-dom';

function Feedback() {
  const [feedback, setFeedback] = useState('');
  const [feedbackType, setFeedbackType] = useState('General Feedback');
  const [allowContact, setAllowContact] = useState(false);

  const handleFeedbackChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    if (value.length <= 2000) {
      setFeedback(value);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50 p-6">
      <div className="max-w-3xl mx-auto">
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
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Send Feedback</h1>
            <p className="text-sm text-gray-600">
              We value your input! Whether it's a bug, a feature idea, or general comments, please let us know.
            </p>
          </div>

          {/* Feedback Form */}
          <div className="space-y-6">
            {/* Feedback Type Dropdown */}
            <div>
              <label htmlFor="feedback-type" className="block text-sm font-medium text-gray-700 mb-2">
                Feedback Type
              </label>
              <div className="relative">
                <select
                  id="feedback-type"
                  value={feedbackType}
                  onChange={(e) => setFeedbackType(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-sm text-gray-900 bg-white appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent pr-10"
                >
                  <option>General Feedback</option>
                  <option>Bug Report</option>
                  <option>Feature Request</option>
                  <option>Performance Issue</option>
                  <option>Other</option>
                </select>
                <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                  <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
            </div>

            {/* Feedback Textarea */}
            <div>
              <label htmlFor="feedback-text" className="block text-sm font-medium text-gray-700 mb-2">
                Your Feedback <span className="text-gray-500 font-normal">{feedback.length}/2000</span>
              </label>
              <textarea
                id="feedback-text"
                value={feedback}
                onChange={handleFeedbackChange}
                placeholder="Please provide as much detail as possible..."
                rows={8}
                className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm text-gray-900 placeholder-gray-400 resize-none focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
              />
            </div>

            {/* Contact Toggle */}
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setAllowContact(!allowContact)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2 ${
                  allowContact ? 'bg-blue-600' : 'bg-gray-300'
                }`}
                role="switch"
                aria-checked={allowContact}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    allowContact ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
              <label htmlFor="contact-toggle" className="text-sm text-gray-700 cursor-pointer">
                I'm happy to be contacted about this feedback
              </label>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
              <button
                type="button"
                className="px-6 py-2.5 text-sm font-medium text-gray-900 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                className="px-6 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 transition-colors"
              >
                Submit Feedback
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Feedback;

