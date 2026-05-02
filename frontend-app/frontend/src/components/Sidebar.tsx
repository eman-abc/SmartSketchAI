import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { fetchUserImages } from '../lib/api';
import type { GenerateResult } from '../types';

type SidebarProps = {
  onSelectImage?: (image: GenerateResult) => void;
};

function IconChat() {
  return (
    <svg className="h-4 w-4 shrink-0 text-brand" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
  );
}

function IconSettings() {
  return (
    <svg className="h-4 w-4 shrink-0 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  );
}

function IconSignIn() {
  return (
    <svg className="h-4 w-4 shrink-0 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
    </svg>
  );
}

function navLinkClasses(active: boolean) {
  return [
    'flex items-center gap-2 rounded-2xl px-3 py-2.5 text-sm font-medium transition duration-200',
    active
      ? 'bg-brand/15 text-brand ring-1 ring-brand/35'
      : 'text-muted hover:bg-white/5 hover:text-text-high',
  ].join(' ');
}

function Sidebar({ onSelectImage }: SidebarProps) {
  const location = useLocation();
  const { isAuthenticated, logout } = useAuth();
  const [history, setHistory] = useState<GenerateResult[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) return;
    setLoading(true);
    fetchUserImages()
      .then((data: GenerateResult[]) => setHistory(Array.isArray(data) ? data : []))
      .catch(() => { })
      .finally(() => setLoading(false));
  }, [isAuthenticated]);

  return (
    <aside className="flex h-full w-[17.5rem] shrink-0 flex-col gap-6 overflow-hidden rounded-3xl border border-studio bg-panel/95 px-6 pt-12 pb-6 shadow-panel backdrop-blur-sm animate-fade-in">
      <div className="min-h-0 flex-1 flex flex-col rounded-2xl border border-white/[0.08] bg-surface/50 p-4">
        <div className="mb-4 flex items-center justify-between gap-2 border-b border-studio pb-3">
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">Session artifacts</h2>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto pr-1">
          {loading ? (
            <p className="text-xs text-muted animate-pulse">Loading history…</p>
          ) : history.length > 0 ? (
            <ul className="space-y-1.5">
              {history.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => onSelectImage?.(item)}
                    className="w-full rounded-xl border border-transparent px-3 py-2 text-left text-xs leading-snug text-muted transition duration-200 hover:border-studio hover:bg-panel hover:text-text-high"
                    title={item.prompt}
                  >
                    {item.prompt ?? 'Untitled sketch'}
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-muted">No generations yet.</p>
          )}
        </div>
      </div>

      <div className="rounded-2xl border border-white/[0.08] bg-surface/50 p-4">
        <div className="mb-4 border-b border-studio pb-3">
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">Navigate</h2>
        </div>
        <ul className="space-y-1">
          <li>
            <Link to="/" className={navLinkClasses(location.pathname === '/')}>
              <IconChat />
              Chat Interface
            </Link>
          </li>
          {!isAuthenticated && (
            <>
              <li>
                <Link to="/login" className={navLinkClasses(location.pathname === '/login')}>
                  <IconSignIn />
                  Sign In
                </Link>
              </li>
              <li>
                <Link to="/register" className={navLinkClasses(location.pathname === '/register')}>
                  <IconSignIn />
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
                className="flex w-full items-center gap-2 rounded-2xl px-3 py-2.5 text-left text-sm font-medium text-muted transition duration-200 hover:bg-white/5 hover:text-danger"
              >
                <svg className="h-4 w-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                Sign out
              </button>
            </li>
          )}
          <li>
            <Link
              to="/settings"
              className={navLinkClasses(location.pathname.startsWith('/settings'))}
            >
              <IconSettings />
              Settings
            </Link>
          </li>
        </ul>
      </div>
    </aside>
  );
}

export default Sidebar;
