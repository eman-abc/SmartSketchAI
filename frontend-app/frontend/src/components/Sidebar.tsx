import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { fetchUserImages } from '../lib/api';

type SidebarProps = {
  onSelectImage?: (image: any) => void;
};

function Sidebar({ onSelectImage }: SidebarProps) {
  const location = useLocation();
  const { isAuthenticated, logout } = useAuth();
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      setLoading(true);
      fetchUserImages()
        .then((data) => setHistory(data))
        .catch((err) => console.error('Failed to fetch history:', err))
        .finally(() => setLoading(false));
    }
  }, [isAuthenticated]);

  return (
    <div className="w-64 bg-gray-50 dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 flex flex-col h-full">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex-1 overflow-y-auto">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Chat History</h2>
        {loading ? (
          <p className="text-xs text-gray-500 animate-pulse">Loading history...</p>
        ) : history.length > 0 ? (
          <ul className="space-y-2">
            {history.map((item) => (
              <li
                key={item.id}
                onClick={() => onSelectImage?.(item)}
                className="text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 px-3 py-2 rounded-lg cursor-pointer transition-colors truncate"
                title={item.prompt}
              >
                {item.prompt}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-gray-500">No generations yet</p>
        )}
      </div>
      
      <div className="p-4 border-t border-gray-200 dark:border-gray-700">
        <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Navigate</h2>
        <ul className="space-y-1">
          <li>
            <Link
              to="/"
              className={`text-sm px-3 py-2 rounded-lg transition-colors block ${
                location.pathname === '/'
                  ? 'text-gray-900 dark:text-white bg-gray-100 dark:bg-gray-700 font-medium'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              Chat Interface
            </Link>
          </li>
          {!isAuthenticated && (
            <>
              <li>
                <Link
                  to="/login"
                  className={`text-sm px-3 py-2 rounded-lg transition-colors block ${
                    location.pathname === '/login'
                      ? 'text-gray-900 dark:text-white bg-gray-100 dark:bg-gray-700 font-medium'
                      : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  Sign In
                </Link>
              </li>
              <li>
                <Link
                  to="/register"
                  className={`text-sm px-3 py-2 rounded-lg transition-colors block ${
                    location.pathname === '/register'
                      ? 'text-gray-900 dark:text-white bg-gray-100 dark:bg-gray-700 font-medium'
                      : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  Sign Up
                </Link>
              </li>
            </>
          )}
          {isAuthenticated && (
            <li>
              <button
                type="button"
                onClick={() => logout()}
                className="text-sm px-3 py-2 rounded-lg transition-colors block w-full text-left text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                Sign out
              </button>
            </li>
          )}
          <li>
            <Link
              to="/settings"
              className={`text-sm px-3 py-2 rounded-lg transition-colors block ${
                location.pathname.startsWith('/settings')
                  ? 'text-gray-900 dark:text-white bg-gray-100 dark:bg-gray-700 font-medium'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              Settings
            </Link>
          </li>
        </ul>
      </div>
    </div>
  );
}

export default Sidebar;
