import { Link } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import ForensicStudioHeader from './layout/ForensicStudioHeader';

type TopBarProps = {
  onNewSession?: () => void;
};

/** Workspace header — same sticky chrome as other Forensic Studio routes. */
function TopBar({ onNewSession }: TopBarProps) {
  const { theme, toggleTheme } = useTheme();

  return (
    <ForensicStudioHeader
      navRight={
        <>
          <Link
            to="/settings"
            className="btn-ghost rounded-2xl px-3 py-2 text-xs font-medium text-muted hover:text-brand sm:text-sm"
          >
            Settings
          </Link>
          <button
            type="button"
            onClick={toggleTheme}
            className="btn-ghost rounded-2xl p-2.5 text-muted hover:text-brand"
            title={theme === 'light' ? 'Dark mode' : 'Light mode'}
          >
            {theme === 'light' ? (
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            ) : (
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            )}
          </button>
          <span className="hidden items-center gap-2 rounded-full border border-studio bg-success/10 px-2.5 py-1 text-[10px] font-medium text-success sm:inline-flex">
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success/60 opacity-60" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-success" />
            </span>
            Live
          </span>
          <button type="button" onClick={() => onNewSession?.()} className="btn-primary text-xs sm:text-sm">
            New session
          </button>
        </>
      }
    />
  );
}

export default TopBar;
