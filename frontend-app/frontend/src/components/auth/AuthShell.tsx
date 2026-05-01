import type { ReactNode } from 'react';
import ForensicStudioLayout from '../layout/ForensicStudioLayout';

type AuthShellProps = {
  children: ReactNode;
  footer?: ReactNode;
};

export default function AuthShell({ children, footer }: AuthShellProps) {
  return (
    <ForensicStudioLayout>
      <div className="flex flex-col items-center px-4 py-10 sm:px-6 sm:py-14">
        <p className="mb-8 text-center text-[10px] font-medium uppercase tracking-[0.28em] text-muted">
          Authorized access · Research use only
        </p>
        <div className="w-full max-w-md animate-fade-in">
          <div className="glass-card border-studio/80 p-8 shadow-panel transition duration-200 ease-out hover:border-white/[0.12]">
            {children}
          </div>
          {footer ? <div className="mt-8">{footer}</div> : null}
        </div>
      </div>
    </ForensicStudioLayout>
  );
}
