import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import GlobalErrorBoundary from './GlobalErrorBoundary';

function CrashingChild({ shouldCrash }: { shouldCrash: boolean }) {
  if (shouldCrash) {
    throw new Error('Exploded test child');
  }

  return <div>Recovered child</div>;
}

describe('GlobalErrorBoundary', () => {
  it('renders fallback UI after a child throws and can reset', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    const { rerender } = render(
      <GlobalErrorBoundary>
        <CrashingChild shouldCrash />
      </GlobalErrorBoundary>
    );

    expect(screen.getByRole('heading', { name: /something went wrong/i })).toBeInTheDocument();
    expect(screen.getByText('Exploded test child')).toBeInTheDocument();

    rerender(
      <GlobalErrorBoundary>
        <CrashingChild shouldCrash={false} />
      </GlobalErrorBoundary>
    );

    await userEvent.click(screen.getByRole('button', { name: /try again/i }));

    expect(screen.getByText('Recovered child')).toBeInTheDocument();
    expect(consoleSpy).toHaveBeenCalled();

    consoleSpy.mockRestore();
  });
});
