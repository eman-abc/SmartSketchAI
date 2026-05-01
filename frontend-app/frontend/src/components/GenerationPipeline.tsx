import type { ForensicLogEntry } from '../types';

const STEPS = [
  { key: 'analyzer', label: 'Analyzer' },
  { key: 'route', label: 'Route' },
  { key: 'artist', label: 'Artist' },
  { key: 'verify', label: 'Verify' },
] as const;

function pipelineIndex(logs: ForensicLogEntry[], isGenerating: boolean): number {
  if (logs.some((l) => l.level === 'result')) return 3;

  const scan = [...logs].reverse();
  for (const l of scan) {
    const st = (l.stage ?? '').toLowerCase();
    const msg = (l.message ?? '').toLowerCase();
    if (st.includes('verify') || msg.includes('verif')) return 3;
    if (st === 'artist' || msg.includes('denois') || msg.includes('render')) return 2;
    if (st === 'modal' || st === 'router' || st === 'route' || msg.includes('modal')) return 1;
    if (st === 'analyzer' || msg.includes('analy')) return 0;
  }

  if (isGenerating || logs.length > 0) return 0;
  return -1;
}

type GenerationPipelineProps = {
  logs: ForensicLogEntry[];
  isGenerating: boolean;
};

export default function GenerationPipeline({ logs, isGenerating }: GenerationPipelineProps) {
  const activeIdx = pipelineIndex(logs, isGenerating);

  return (
    <div className="mb-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">
          Pipeline
        </h3>
        {isGenerating && (
          <span className="rounded-full bg-warning/15 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-warning">
            Processing
          </span>
        )}
      </div>
      <ul className="flex flex-col gap-2">
        {STEPS.map((step, idx) => {
          const reached = activeIdx >= idx;
          const current = activeIdx === idx;
          const dotCls = reached
            ? current
              ? 'bg-brand shadow-soft-glow'
              : 'bg-success'
            : 'bg-muted/25';

          const labelCls = reached
            ? current
              ? 'text-brand font-semibold'
              : 'text-text-high'
            : 'text-muted';

          return (
            <li key={step.key} className="flex items-start gap-2.5 text-xs transition duration-200">
              <span
                className={`mt-0.5 h-2 w-2 shrink-0 rounded-full ring-2 ring-studio/60 ${dotCls}`}
                aria-hidden
              />
              <div className="min-w-0 flex-1">
                <span className={labelCls}>{step.label}</span>
                {current && isGenerating ? (
                  <p className="mt-0.5 text-[10px] text-muted">
                    {idx === 0 && 'Analyzing…'}
                    {idx === 1 && 'Routing tool…'}
                    {idx === 2 && 'Generating…'}
                    {idx === 3 && 'Verifying…'}
                  </p>
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
