import { Component, type ErrorInfo, type ReactNode } from 'react';

type GlobalErrorBoundaryProps = {
  children: ReactNode;
};

type GlobalErrorBoundaryState = {
  hasError: boolean;
  error: Error | null;
};

export default class GlobalErrorBoundary extends Component<
  GlobalErrorBoundaryProps,
  GlobalErrorBoundaryState
> {
  state: GlobalErrorBoundaryState = {
    hasError: false,
    error: null,
  };

  static getDerivedStateFromError(error: Error): GlobalErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[GlobalErrorBoundary]', {
      message: error.message,
      stack: error.stack,
      componentStack: info.componentStack,
    });
  }

  private handleTryAgain = () => {
    this.setState({ hasError: false, error: null });
  };

  private handleReload = () => {
    window.location.reload();
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <main className="flex min-h-screen flex-col items-center justify-center bg-forensic-studio px-4 py-12 text-text-high antialiased">
        <section className="glass-card w-full max-w-md border-danger/30 p-8 text-center shadow-panel">
          <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-2xl border border-danger/40 bg-danger/10">
            <svg
              aria-hidden="true"
              className="h-7 w-7 text-danger"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v4m0 4h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"
              />
            </svg>
          </div>
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.25em] text-muted">System</p>
          <h1 className="text-xl font-semibold tracking-tight text-text-high">Something went wrong</h1>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            SmartSketch hit an unexpected interface error. Your session may still be available after a retry or full
            reload.
          </p>
          {this.state.error?.message && (
            <p className="mt-4 rounded-2xl border border-studio bg-surface px-3 py-2.5 text-left font-mono text-[11px] leading-relaxed text-brand/90">
              {this.state.error.message}
            </p>
          )}
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <button type="button" onClick={this.handleTryAgain} className="btn-primary flex-1 py-3 text-sm">
              Try again
            </button>
            <button type="button" onClick={this.handleReload} className="btn-secondary flex-1 py-3 text-sm">
              Reload app
            </button>
          </div>
        </section>
      </main>
    );
  }
}
