import { afterEach, describe, expect, it, vi } from 'vitest';

import { agentChatStream } from './api';

vi.mock('./authStore', () => ({
  getAccessToken: vi.fn(() => 'test-access-token'),
  getRefreshToken: vi.fn(),
  setTokens: vi.fn(),
  clearTokens: vi.fn(),
}));

describe('agentChatStream', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('parses streamed SSE chunks and forwards events', async () => {
    const chunks = [
      'event: status\ndata: {"stage":"analyzer","message":"[Analyzer] Extracting eye color...","percent":15}\n\n',
      'event: progress\ndata: {"stage":"artist","message":"[Artist] Denoising: 45%...","percent":45}\n\n',
      'event: result\ndata: {"status":"success","thread_id":"thread_123","generation_id":"gen_1"}\n\n',
    ];

    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        const encoder = new TextEncoder();
        for (const chunk of chunks) {
          controller.enqueue(encoder.encode(chunk));
        }
        controller.close();
      },
    });

    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(stream, {
          status: 200,
          headers: { 'Content-Type': 'text/event-stream' },
        })
      )
    );

    const seen: Array<{ event: string; data: unknown }> = [];
    await agentChatStream({ message: 'test message', thread_id: 'thread_123' }, (evt) => {
      seen.push(evt);
    });

    expect(seen).toHaveLength(3);
    expect(seen[0].event).toBe('status');
    expect((seen[0].data as { stage: string }).stage).toBe('analyzer');
    expect(seen[1].event).toBe('progress');
    expect(seen[2].event).toBe('result');
    expect((seen[2].data as { thread_id: string }).thread_id).toBe('thread_123');
  });
});
