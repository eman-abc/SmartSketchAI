import type { ForensicLogEntry } from '../types';

type ForensicConsoleProps = {
  logs: ForensicLogEntry[];
};

const LEVEL_DOT: Record<ForensicLogEntry['level'], string> = {
  info: 'bg-brand shadow-soft-glow',
  error: 'bg-danger',
  result: 'bg-success',
};

const LEVEL_LABEL: Record<ForensicLogEntry['level'], string> = {
  info: 'text-brand',
  error: 'text-danger',
  result: 'text-success',
};

export default function ForensicConsole({ logs }: ForensicConsoleProps) {
  return (
    <div className="glass-card border-slate-700/40 p-4 transition duration-200 ease-out hover:-translate-y-0.5">
      <h2 className="mb-4 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">
        Forensic Console
      </h2>
      <div className="max-h-[11rem] space-y-2 overflow-y-auto rounded-2xl border border-slate-700 bg-[#0f172a] p-3 font-mono text-[11px] leading-relaxed text-slate-200">
        {logs.length === 0 ? (
          <p className="text-muted">Awaiting stream events…</p>
        ) : (
          logs.map((log) => (
            <p key={log.id} className="flex gap-2 break-words border-b border-slate-700/70 pb-2 last:border-0 last:pb-0">
              <span className={`mt-1 inline-block h-1.5 w-1.5 shrink-0 rounded-full ${LEVEL_DOT[log.level]}`} aria-hidden />
              <span className="min-w-0 flex-1">
                <span className="text-muted">[{log.timestamp}]</span>{' '}
                <span className={LEVEL_LABEL[log.level]}>[{log.stage}]</span>{' '}
                <span className="text-slate-200">{log.message}</span>
                {typeof log.percent === 'number' ? (
                  <span className="text-muted"> ({Math.round(log.percent)}%)</span>
                ) : null}
              </span>
            </p>
          ))
        )}
      </div>
    </div>
  );
}
