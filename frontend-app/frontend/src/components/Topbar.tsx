import ForensicStudioHeader from './layout/ForensicStudioHeader';

type TopBarProps = {
  onNewSession?: () => void;
};

/** Workspace header — same sticky chrome as other Forensic Studio routes. */
function TopBar({ onNewSession }: TopBarProps) {
  return (
    <ForensicStudioHeader
      navRight={
        <>
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
