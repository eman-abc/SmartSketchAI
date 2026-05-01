import type { ReactNode } from 'react';
import ForensicStudioHeader from './ForensicStudioHeader';

type ForensicStudioLayoutProps = {
  children: ReactNode;
  navRight?: ReactNode;
};

export default function ForensicStudioLayout({ children, navRight }: ForensicStudioLayoutProps) {
  return (
    <div className="flex min-h-screen flex-col bg-forensic-studio text-text-high antialiased">
      <ForensicStudioHeader navRight={navRight} />
      <main className="min-h-0 flex-1">{children}</main>
    </div>
  );
}
