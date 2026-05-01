import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import ForensicConsole from './ForensicConsole';

describe('ForensicConsole', () => {
  it('shows placeholder when no logs exist', () => {
    render(<ForensicConsole logs={[]} />);
    expect(screen.getByText(/awaiting stream events/i)).toBeInTheDocument();
  });

  it('renders stream logs with stage and message', () => {
    render(
      <ForensicConsole
        logs={[
          {
            id: '1',
            timestamp: '10:52:00 PM',
            stage: 'analyzer',
            message: '[Analyzer] Extracting eye color...',
            percent: 15,
            level: 'info',
          },
          {
            id: '2',
            timestamp: '10:52:10 PM',
            stage: 'artist',
            message: '[Artist] Denoising: 45%...',
            percent: 45,
            level: 'result',
          },
        ]}
      />
    );

    expect(screen.getByText('[Analyzer] Extracting eye color...')).toBeInTheDocument();
    expect(screen.getByText('[Artist] Denoising: 45%...')).toBeInTheDocument();
    expect(screen.getByText('[analyzer]')).toBeInTheDocument();
    expect(screen.getByText('[artist]')).toBeInTheDocument();
  });
});
