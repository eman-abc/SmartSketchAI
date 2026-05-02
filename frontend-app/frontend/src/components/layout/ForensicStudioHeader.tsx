import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

type ForensicStudioHeaderProps = {
  navRight?: ReactNode;
};

export default function ForensicStudioHeader({ navRight }: ForensicStudioHeaderProps) {
  return (
    <header className="sticky top-0 z-30 h-16 shrink-0 border-b border-studio/80 bg-panel/95 shadow-sm backdrop-blur-sm">
      <div className="mx-auto flex h-full max-w-[1920px] items-center justify-between gap-4 px-4 sm:px-6">
        <Link to="/" className="group flex min-w-0 items-center gap-2.5 transition duration-200 hover:opacity-95 sm:gap-3">
          <span className="shrink-0 rounded-xl border border-brand/35 bg-brand/10 px-2 py-0.5 text-[9px] font-bold uppercase tracking-[0.18em] text-brand shadow-soft-glow sm:px-2.5">
            Studio
          </span>
          <span className="truncate text-sm font-semibold tracking-tight text-text-high transition-colors group-hover:text-brand sm:text-base">
            SmartSketch AI
          </span>
        </Link>
        {navRight ? (
          <nav className="flex shrink-0 flex-wrap items-center justify-end gap-2">{navRight}</nav>
        ) : null}
      </div>
    </header>
  );
}
