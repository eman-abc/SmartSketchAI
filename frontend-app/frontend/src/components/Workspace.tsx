import { useState, useCallback, useEffect, useRef } from 'react';
import { agentChat } from '../lib/api';
import type { GenerateResult } from '../types';

// Stable session thread ID — one conversation per browser tab
const SESSION_THREAD_ID = `session_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;

const PROGRESS_STEPS = [
  'Analyzing suspect description…',
  'Building facial geometry…',
  'Generating base portrait…',
  'Applying forensic details…',
  'Embedding integrity watermark…',
  'Finalizing sketch…',
];

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  image_url?: string | null;
  score?: number | null;
  generation_id?: string | null;
  image_id?: number | null;
  suspect_profile?: Record<string, unknown> | null;
};

type WorkspaceProps = {
  onGenerateResult?: (result: GenerateResult | null, prompt: string) => void;
  selectedImage?: GenerateResult | null;
};

const EXAMPLE_PROMPTS = [
  'Male suspect, mid-40s, short brown hair, square jaw, brown eyes',
  'Female, early 30s, long black hair, thin face, high cheekbones',
  'Heavy-set male, 50s, bald, thick grey beard, prominent nose',
];

export default function Workspace({ onGenerateResult, selectedImage }: WorkspaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [stepIdx, setStepIdx] = useState(0);
  const [progress, setProgress] = useState(0);

  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Scroll to bottom on new content
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Sidebar image selection → inject as assistant message
  useEffect(() => {
    if (!selectedImage) return;
    setMessages([{
      id: `history_${selectedImage.id}`,
      role: 'assistant',
      text: `Loaded from history: "${selectedImage.prompt}"`,
      image_url: selectedImage.image_url,
      generation_id: selectedImage.generation_id,
    }]);
    onGenerateResult?.(selectedImage, selectedImage.prompt);
  }, [selectedImage]); // eslint-disable-line react-hooks/exhaustive-deps

  // Progress animation while generating
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
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [loading]);

  const handleSend = useCallback(async (e: React.FormEvent | React.KeyboardEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    const userMsg: ChatMessage = { id: `u_${Date.now()}`, role: 'user', text: trimmed };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await agentChat({ message: trimmed, thread_id: SESSION_THREAD_ID });

      let aiText = 'Profile updated — keep describing the suspect to generate the sketch.';
      if (res.last_error) {
        aiText = `⚠️ ${res.last_error}`;
      } else if (res.image_url) {
        if (res.next_step === 'generate') {
          aiText = 'Generated a new face matching the profile. Keep refining or describe a new feature.';
        } else {
          aiText = 'Sketch updated. Keep refining or describe a new feature.';
        }
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
      };
      setMessages(prev => [...prev, aiMsg]);

      if (res.image_url) {
        onGenerateResult?.({
          id: res.image_id,
          image_url: res.image_url,
          prompt: trimmed,
          generation_id: res.generation_id,
          forensic_hash: res.forensic_hash,
          scores: { combined_score: res.last_score, identity_score: res.identity_score },
          metadata: res.suspect_profile,
        }, trimmed);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Something went wrong';
      setMessages(prev => [...prev, { id: `err_${Date.now()}`, role: 'assistant', text: `❌ ${msg}` }]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, onGenerateResult]);

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
    <div className="flex-1 flex flex-col bg-white dark:bg-gray-900 overflow-hidden">

      {/* Global progress bar */}
      {progress > 0 && (
        <div className="h-0.5 w-full bg-gray-200 dark:bg-gray-800">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 transition-all duration-[2500ms] ease-in-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* Chat thread */}
      <div className="flex-1 overflow-y-auto px-4 py-6">

        {/* Empty state */}
        {messages.length === 0 && !loading && (
          <div className="max-w-2xl mx-auto text-center pt-12 pb-8">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl mx-auto mb-5 flex items-center justify-center shadow-lg">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">SmartSketch AI</h2>
            <p className="text-gray-500 dark:text-gray-400 mb-8 text-sm">
              Describe a suspect in natural language. Refine iteratively — the AI remembers the full conversation.
            </p>
            <div className="space-y-2 max-w-sm mx-auto">
              {EXAMPLE_PROMPTS.map(p => (
                <button
                  key={p}
                  type="button"
                  onClick={() => { setInput(p); textareaRef.current?.focus(); }}
                  className="w-full text-left text-sm px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-blue-400 hover:text-blue-600 dark:hover:border-blue-500 dark:hover:text-blue-400 bg-gray-50 dark:bg-gray-800 transition-all duration-150"
                >
                  "{p}"
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="max-w-2xl mx-auto space-y-5">
          {messages.map(msg => (
            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} gap-3`}>

              {msg.role === 'assistant' && (
                <div className="w-8 h-8 flex-shrink-0 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center mt-1">
                  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
              )}

              <div className="max-w-md w-full">
                {/* Bubble text */}
                <div className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-blue-600 text-white rounded-tr-sm ml-auto w-fit max-w-full'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white rounded-tl-sm'
                }`}>
                  {msg.text}
                </div>

                {/* Image + score */}
                {msg.image_url && (
                  <div className="mt-2 rounded-2xl overflow-hidden border border-gray-200 dark:border-gray-700 shadow-sm">
                    <img
                      src={msg.image_url}
                      alt="Forensic sketch"
                      className="w-full object-cover cursor-zoom-in"
                      onClick={() => window.open(msg.image_url!, '_blank')}
                    />
                    {msg.score != null && (
                      <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-gray-800 text-xs text-gray-500 dark:text-gray-400">
                        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                          msg.score >= 70 ? 'bg-green-500' : msg.score >= 55 ? 'bg-yellow-500' : 'bg-red-500'
                        }`} />
                        <span>Quality: <strong className="text-gray-900 dark:text-white">{msg.score.toFixed(1)}/100</strong></span>
                        <span className="ml-auto font-mono text-gray-400 dark:text-gray-500 truncate">{msg.generation_id}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="w-8 h-8 flex-shrink-0 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center mt-1">
                  <svg className="w-4 h-4 text-gray-600 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
              )}
            </div>
          ))}

          {/* Generation skeleton */}
          {loading && (
            <div className="flex justify-start gap-3">
              <div className="w-8 h-8 flex-shrink-0 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center mt-1 animate-pulse">
                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <div className="max-w-md w-full space-y-2">
                {/* Status pill */}
                <div className="bg-gray-100 dark:bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-2.5 text-sm text-gray-600 dark:text-gray-400 flex items-center gap-2">
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                  <span className="ml-1 animate-pulse">{PROGRESS_STEPS[stepIdx]}</span>
                </div>

                {/* Image skeleton */}
                <div className="rounded-2xl overflow-hidden border border-gray-200 dark:border-gray-700">
                  <div className="w-full aspect-square bg-gradient-to-br from-gray-200 via-gray-100 to-gray-200 dark:from-gray-700 dark:via-gray-600 dark:to-gray-700 animate-pulse" />
                  <div className="px-3 py-2 bg-gray-50 dark:bg-gray-800">
                    <div className="h-3 w-36 bg-gray-200 dark:bg-gray-700 rounded-full animate-pulse" />
                  </div>
                </div>
                <p className="text-xs text-gray-400 dark:text-gray-500 pl-1">
                  First request may take 60–90s (GPU warm-up)
                </p>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input bar */}
      <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
        {messages.length > 0 && !loading && (
          <div className="max-w-2xl mx-auto flex justify-end mb-2">
            <button
              onClick={(e) => {
                e.preventDefault();
                setInput("That's the wrong person, start over and generate a new face.");
                setTimeout(() => handleSend(e), 0);
              }}
              className="text-xs flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full transition-colors border border-gray-200 dark:border-gray-700"
              title="Discard current face identity and regenerate from profile"
            >
              <span>🔄</span> Reroll Face
            </button>
          </div>
        )}
        <form onSubmit={handleSend} className="max-w-2xl mx-auto flex gap-3 items-end">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={autoResize}
            onKeyDown={handleKeyDown}
            placeholder="Describe the suspect… (Enter to send, Shift+Enter for new line)"
            disabled={loading}
            className="flex-1 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none transition-shadow placeholder-gray-400 dark:placeholder-gray-500"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="flex-shrink-0 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white p-3 rounded-xl transition-colors"
            aria-label="Send"
          >
            {loading ? (
              <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
