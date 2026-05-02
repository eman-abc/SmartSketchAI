import { useState, useCallback, useEffect, useRef } from 'react';
import { agentChat, agentChatStream } from '../lib/api';
import type {
  CriticReport,
  GenerateResult,
  ForensicLogEntry,
  AgentChatResult,
  ForensicStreamStatusData,
} from '../types';

const PROGRESS_STEPS = [
  'Analyzing suspect description…',
  'Building facial geometry…',
  'Generating base portrait…',
  'Applying forensic details…',
  'Embedding integrity watermark…',
  'Finalizing sketch…',
];

function loadingStatusChip(step: string): string {
  const s = step.toLowerCase();
  if (s.includes('analyz')) return 'Analyzing…';
  if (s.includes('verif') || s.includes('finaliz') || s.includes('watermark')) return 'Verifying…';
  if (s.includes('generat') || s.includes('portrait') || s.includes('facial')) return 'Generating…';
  return 'Processing…';
}

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  image_url?: string | null;
  score?: number | null;
  generation_id?: string | null;
  image_id?: number | null;
  suspect_profile?: Record<string, unknown> | null;
  critic_report?: CriticReport | null;
};

type WorkspaceProps = {
  onGenerateResult?: (result: GenerateResult | null, prompt: string) => void;
  selectedImage?: GenerateResult | null;
  onStreamLogsChange?: (logs: ForensicLogEntry[]) => void;
  onLoadingChange?: (loading: boolean) => void;
};

const EXAMPLE_PROMPTS = [
  'Male suspect, mid-40s, short brown hair, square jaw, brown eyes',
  'Female, early 30s, long black hair, thin face, high cheekbones',
  'Heavy-set male, 50s, bald, thick grey beard, prominent nose',
];

export default function Workspace({
  onGenerateResult,
  selectedImage,
  onStreamLogsChange,
  onLoadingChange,
}: WorkspaceProps) {
  const threadIdRef = useRef(`session_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`);

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [stepIdx, setStepIdx] = useState(0);
  const [progress, setProgress] = useState(0);
  const [streamLogs, setStreamLogs] = useState<ForensicLogEntry[]>([]);

  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const pushLog = useCallback((entry: Omit<ForensicLogEntry, 'id' | 'timestamp'>) => {
    setStreamLogs((prev) => {
      const next = [
        ...prev,
        {
          id: `log_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
          timestamp: new Date().toLocaleTimeString(),
          ...entry,
        },
      ].slice(-60);
      onStreamLogsChange?.(next);
      return next;
    });
  }, [onStreamLogsChange]);

  useEffect(() => {
    onLoadingChange?.(loading);
  }, [loading, onLoadingChange]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  useEffect(() => {
    if (!selectedImage) return;
    setMessages([{
      id: `history_${selectedImage.id}`,
      role: 'assistant',
      text: `Loaded from history: "${selectedImage.prompt}"`,
      image_url: selectedImage.image_url,
      generation_id: selectedImage.generation_id,
      critic_report: selectedImage.critic_report ?? null,
    }]);
    onGenerateResult?.(selectedImage, selectedImage.prompt);
  }, [selectedImage]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    onStreamLogsChange?.(streamLogs);
  }, [streamLogs, onStreamLogsChange]);

  useEffect(() => {
    if (loading) {
      setStepIdx(0);
      setProgress(5);
      let step = 0;
      intervalRef.current = setInterval(() => {
        step = Math.min(step + 1, PROGRESS_STEPS.length - 1);
        setStepIdx(step);
        setProgress(Math.min(5 + (step / (PROGRESS_STEPS.length - 1)) * 85, 90));
      }, 3000);
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current);
      setProgress(100);
      setTimeout(() => setProgress(0), 600);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [loading]);

  const handleSend = useCallback(async (e: React.FormEvent | React.KeyboardEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    const userMsg: ChatMessage = { id: `u_${Date.now()}`, role: 'user', text: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setStreamLogs([]);

    try {
      let res: AgentChatResult | null = null;
      const tid = threadIdRef.current;
      try {
        await agentChatStream(
          { message: trimmed, thread_id: tid },
          (evt) => {
            if (evt.event === 'status' || evt.event === 'progress') {
              const status = evt.data as ForensicStreamStatusData;
              if (status.percent != null && Number.isFinite(status.percent)) {
                setProgress(Math.max(5, Math.min(100, status.percent)));
              }
              if (status.message) {
                pushLog({
                  stage: status.stage ?? 'agent',
                  message: status.message,
                  percent: status.percent,
                  level: 'info',
                });
              }
            } else if (evt.event === 'result') {
              res = evt.data as AgentChatResult;
              pushLog({
                stage: 'result',
                message: 'Sketch response ready.',
                level: 'result',
                percent: 100,
              });
            } else if (evt.event === 'error') {
              const errMsg = (evt.data as { error?: string })?.error ?? 'Stream error';
              pushLog({ stage: 'error', message: errMsg, level: 'error' });
            }
          }
        );
      } catch (streamErr) {
        pushLog({
          stage: 'fallback',
          message: 'Stream unavailable, using standard endpoint.',
          level: 'info',
        });
        res = await agentChat({ message: trimmed, thread_id: tid });
        if (streamErr instanceof Error) {
          pushLog({ stage: 'fallback', message: streamErr.message, level: 'error' });
        }
      }

      if (!res) throw new Error('No response received from forensic agent');

      let aiText = 'Profile updated — keep describing the suspect to generate the sketch.';
      if (res.last_error) aiText = `⚠️ ${res.last_error}`;
      else if (res.image_url) {
        aiText =
          res.next_step === 'generate'
            ? 'Generated a new face matching the profile. Keep refining or describe a new feature.'
            : 'Sketch updated. Keep refining or describe a new feature.';
      }

      const aiMsg: ChatMessage = {
        id: `a_${Date.now()}`,
        role: 'assistant',
        text: aiText,
        image_url: res.image_url ?? null,
        score: res.last_score ?? null,
        generation_id: res.generation_id ?? null,
        image_id: res.image_id ?? null,
        suspect_profile: res.suspect_profile ?? null,
        critic_report: res.critic_report ?? null,
      };
      setMessages((prev) => [...prev, aiMsg]);

      if (res.image_url) {
        onGenerateResult?.(
          {
            id: Number(res.image_id ?? 0),
            image_url: res.image_url as string,
            prompt: trimmed,
            generation_id: (res.generation_id ?? '') as string,
            forensic_hash: res.forensic_hash,
            critic_report: res.critic_report ?? null,
            scores: {
              clip_score: res.ml_scores?.clip_score,
              combined_score: res.last_score ?? res.ml_scores?.combined_score,
              identity_score: res.identity_score ?? res.ml_scores?.identity_score,
            },
            metadata:
              (res.suspect_profile as Record<string, unknown> | undefined) ?? {},
          },
          trimmed
        );
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Something went wrong';
      setMessages((prev) => [...prev, { id: `err_${Date.now()}`, role: 'assistant', text: `❌ ${msg}` }]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, onGenerateResult, pushLog]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(e);
    }
  };

  const autoResize = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 140)}px`;
  };

  return (
    <div className="flex min-h-0 h-full min-w-0 flex-1 animate-fade-in flex-col overflow-hidden rounded-3xl bg-surface shadow-panel ring-1 ring-white/10">
      {progress > 0 && (
        <div className="h-0.5 w-full shrink-0 bg-panel">
          <div
            className="h-full bg-gradient-to-r from-brand via-brand-secondary to-brand transition-[width] duration-[1800ms] ease-out shadow-soft-glow"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      <div className="studio-canvas-grid min-h-0 flex-1 overflow-y-auto px-5 pt-12 pb-6">
        {messages.length === 0 && !loading && (
          <div className="mx-auto max-w-2xl px-4 pt-10 pb-8 text-center">
            <div className="glass-card mx-auto mb-6 inline-flex h-16 w-16 items-center justify-center rounded-3xl shadow-soft-glow">
              <svg className="h-9 w-9 text-brand" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                />
              </svg>
            </div>
            <p className="mb-3 text-[10px] uppercase tracking-[0.3em] text-muted">Composite intelligence</p>
            <h2 className="mb-3 text-2xl font-semibold tracking-tight text-text-high">SmartSketch AI</h2>
            <p className="mb-10 text-sm text-muted">
              Describe a suspect in natural language. Refine iteratively — the AI retains full session context.
            </p>
            <div className="mx-auto max-w-lg space-y-2">
              {EXAMPLE_PROMPTS.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => {
                    setInput(p);
                    textareaRef.current?.focus();
                  }}
                  className="w-full rounded-2xl border border-studio px-4 py-3 text-left text-sm text-muted transition duration-200 ease-out hover:border-brand/40 hover:text-text-high hover:shadow-soft-glow"
                >
                  &ldquo;{p}&rdquo;
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="mx-auto max-w-2xl space-y-5 pb-8">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'assistant' && (
                <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-2xl border border-studio bg-brand/15 text-brand shadow-soft-glow">
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                    />
                  </svg>
                </div>
              )}

              <div className="w-full max-w-md">
                <div
                  className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${msg.role === 'user'
                      ? 'ml-auto w-fit max-w-full bg-brand font-medium text-slate-950 rounded-tr-md shadow-soft-glow'
                      : 'border border-studio bg-panel text-text-high rounded-tl-md'
                    }`}
                >
                  {msg.text}
                </div>

                {msg.image_url && (
                  <div className="mt-3 overflow-hidden rounded-2xl border border-studio shadow-panel ring-1 ring-white/5 transition duration-200 ease-out hover:-translate-y-0.5 hover:shadow-soft-glow">
                    <div className="relative bg-background">
                      <span className="absolute left-3 top-3 z-10 rounded-full bg-slate-950/75 px-3 py-1 text-xs font-medium text-slate-200 backdrop-blur-sm">
                        Rendered output
                      </span>
                      <img
                        src={msg.image_url}
                        alt="Forensic sketch"
                        className="w-full cursor-zoom-in object-cover"
                        onClick={() => window.open(msg.image_url!, '_blank')}
                      />
                      <p className="border-t border-studio bg-panel px-4 py-2 text-center text-[10px] uppercase tracking-[0.2em] text-muted">
                        Primary composite output
                      </p>
                      {msg.score != null && (
                        <div className="flex items-center gap-2 border-t border-studio bg-panel/80 px-3 py-2 text-xs text-muted">
                          <div
                            className={`h-2 w-2 shrink-0 rounded-full ${msg.score >= 70 ? 'bg-success' : msg.score >= 55 ? 'bg-warning' : 'bg-danger'
                              }`}
                          />
                          <span>
                            Quality:{' '}
                            <strong className="font-mono text-text-high">{msg.score.toFixed(1)}/100</strong>
                          </span>
                          <span className="ml-auto truncate font-mono text-[11px] text-brand">
                            {msg.generation_id}
                          </span>
                        </div>
                      )}
                      {msg.critic_report?.reasoning_summary && (
                        <div className="border-t border-studio px-3 py-2 text-xs leading-relaxed text-muted">
                          <div className="mb-1 flex items-center gap-2">
                            <span
                              className={`h-2 w-2 shrink-0 rounded-full ${msg.critic_report.decision === 'revise' ? 'bg-warning' : 'bg-success'
                                }`}
                            />
                            <span className="font-semibold text-text-high">
                              Critic{' '}
                              {msg.critic_report.decision === 'revise' ? 'requested refinement' : 'accepted output'}
                            </span>
                            {msg.critic_report.score != null && (
                              <span className="ml-auto font-mono text-muted">
                                {Math.round(msg.critic_report.score)}/100
                              </span>
                            )}
                          </div>
                          <p>{msg.critic_report.reasoning_summary}</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-2xl border border-studio bg-panel text-muted">
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                    />
                  </svg>
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex gap-3">
              <div className="mt-1 flex h-8 w-8 shrink-0 animate-pulse items-center justify-center rounded-2xl border border-brand/40 bg-brand/20 text-brand shadow-soft-glow">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                  />
                </svg>
              </div>
              <div className="max-w-md flex-1 space-y-3">
                <div className="flex items-center gap-2 rounded-2xl rounded-tl-md border border-studio bg-panel px-4 py-2.5 text-sm text-muted">
                  <span
                    className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-brand"
                    style={{ animationDelay: '0ms' }}
                  />
                  <span
                    className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-brand"
                    style={{ animationDelay: '150ms' }}
                  />
                  <span
                    className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-brand"
                    style={{ animationDelay: '280ms' }}
                  />
                  <span className="ml-2 font-medium text-text-high">{loadingStatusChip(PROGRESS_STEPS[stepIdx])}</span>
                  <span className="truncate text-muted">· {PROGRESS_STEPS[stepIdx]}</span>
                </div>

                <div className="overflow-hidden rounded-2xl border border-studio shadow-inner">
                  <div className="studio-canvas-grid aspect-square w-full animate-pulse" />
                  <div className="border-t border-studio bg-panel px-4 py-2">
                    <div className="mx-auto mb-2 h-2 max-w-[40%] rounded-full bg-brand/30" />
                    <p className="text-center text-[10px] uppercase tracking-[0.2em] text-muted">
                      Awaiting lattice composite
                    </p>
                  </div>
                </div>
                <p className="text-xs text-muted">
                  First request may take 60–90s (GPU warm-up)
                </p>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="border-t border-studio bg-surface px-5 py-4">
        {messages.length > 0 && !loading && (
          <div className="mx-auto mb-3 flex max-w-2xl justify-end">
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                setInput("That's the wrong person, start over and generate a new face.");
                setTimeout(() => handleSend(e), 0);
              }}
              className="btn-ghost rounded-full text-xs"
              title="Discard current face identity and regenerate from profile"
            >
              Reroll face
            </button>
          </div>
        )}
        <form onSubmit={handleSend} className="mx-auto flex max-w-2xl items-end gap-3">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={autoResize}
            onKeyDown={handleKeyDown}
            placeholder="Describe the suspect… (Enter = send)"
            disabled={loading}
            className="input-studio min-h-[48px] max-h-[140px] min-w-0 flex-1 resize-none"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="btn-primary flex size-11 shrink-0 items-center justify-center p-0"
            aria-label="Send"
          >
            {loading ? (
              <svg className="h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
