import { useEffect, useState } from 'react';
import type { CriticReport, GenerateResult, EditResult, ForensicLogEntry } from '../types';
import { convertSketchStyle, exportForensicReport, ageForensicSketch } from '../lib/api';
import ForensicConsole from './ForensicConsole';
import GenerationPipeline from './GenerationPipeline';

type RightPanelProps = {
  generateResult?: GenerateResult | null;
  editResult?: EditResult | null;
  prompt?: string;
  onUpdateResult?: (result: GenerateResult | EditResult | unknown) => void;
  forensicLogs?: ForensicLogEntry[];
  isGenerating?: boolean;
};

type SketchStyle = 'photo' | 'pencil' | 'charcoal' | 'forensic';

const STYLE_LABELS: Record<SketchStyle, string> = {
  photo: 'Photo',
  pencil: 'Pencil',
  charcoal: 'Charcoal',
  forensic: 'Forensic',
};

function scorePercent(value: number | undefined | null): number {
  if (value == null || typeof value !== 'number') return 0;
  return Math.round(Math.min(1, Math.max(0, value < 1 ? value : value / 100)) * 100);
}

export default function RightPanel({
  generateResult = null,
  editResult = null,
  prompt = '',
  onUpdateResult,
  forensicLogs = [],
  isGenerating = false,
}: RightPanelProps) {
  const [activeStyle, setActiveStyle] = useState<SketchStyle>('photo');
  const [styleLoading, setStyleLoading] = useState(false);
  const [styledImageUrl, setStyledImageUrl] = useState<string | null>(null);
  const [exportLoading, setExportLoading] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [years, setYears] = useState(15);
  const [ageLoading, setAgeLoading] = useState(false);

  useEffect(() => {
    if (generateResult == null && editResult == null) {
      setStyledImageUrl(null);
      setActiveStyle('photo');
      setStyleLoading(false);
      setExportLoading(false);
      setExportError(null);
      setAgeLoading(false);
    }
  }, [generateResult, editResult]);

  const hasGenerate = generateResult != null;
  const hasEdit = editResult != null;

  const currentResult = hasEdit ? editResult : generateResult;
  const baseImageUrl = hasEdit ? editResult?.edited_image_url : generateResult?.image_url;
  const currentImage = styledImageUrl ?? baseImageUrl;

  const scores = currentResult?.scores ?? {};
  const rawClip = (scores as Record<string, number | undefined>)?.clip_score ?? (scores as Record<string, number>).combined_score;
  const clip = rawClip != null && rawClip > 1 ? Math.round(rawClip) : scorePercent(rawClip);
  const identity = hasEdit
    ? scorePercent(editResult?.identity_score)
    : scorePercent(generateResult?.scores?.identity_score);

  const meta = (currentResult?.metadata ?? {}) as Record<string, unknown>;
  const seed = meta.seed != null ? String(meta.seed) : '—';
  const modelVersion = meta.model_version != null ? String(meta.model_version) : 'SDXL-1.0';
  const displayPrompt = hasEdit ? editResult?.edit_prompt : prompt;
  const auditId = hasEdit ? editResult?.edit_id : generateResult?.generation_id;
  const imageId = hasEdit ? editResult?.id : generateResult?.id;
  const criticReport = (hasEdit ? editResult?.critic_report : generateResult?.critic_report) as CriticReport | null | undefined;

  const handleStyleChange = async (style: SketchStyle) => {
    if (style === activeStyle || styleLoading) return;

    if (style === 'photo') {
      setActiveStyle('photo');
      setStyledImageUrl(null);
      return;
    }

    const generationId = generateResult?.generation_id;
    if (!generationId) return;

    setStyleLoading(true);
    setActiveStyle(style);
    try {
      const res = await convertSketchStyle({ generation_id: generationId, style });
      setStyledImageUrl(res.styled_image_url ?? null);
    } catch {
      setActiveStyle('photo');
      setStyledImageUrl(null);
    } finally {
      setStyleLoading(false);
    }
  };

  const handleExport = async () => {
    const generationId = generateResult?.generation_id ?? editResult?.edit_id;
    if (!generationId || exportLoading) return;

    setExportLoading(true);
    setExportError(null);
    try {
      const blob = await exportForensicReport(generationId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `SmartSketch_Report_${generationId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setExportLoading(false);
    }
  };

  const handleAge = async () => {
    const originalImageId = generateResult?.id;
    if (!originalImageId || ageLoading) return;

    setAgeLoading(true);
    try {
      const res = await ageForensicSketch({
        original_image_id: originalImageId,
        years,
        prompt: displayPrompt || undefined,
      });
      onUpdateResult?.(res);
    } catch {
      // keep UI quiet — errors surface in workspace if needed
    } finally {
      setAgeLoading(false);
    }
  };

  const scoreBarTone = (value: number) =>
    value >= 70 ? 'bg-success' : value >= 55 ? 'bg-warning' : 'bg-muted/35';

  return (
    <div className="flex h-full w-[22rem] shrink-0 flex-col gap-6 overflow-y-auto rounded-3xl border border-studio bg-panel/90 px-6 pt-12 pb-6 shadow-panel backdrop-blur-md animate-fade-in">
      <div className="glass-card p-5 transition duration-200 ease-out hover:-translate-y-1">
        <div className="mb-4 flex items-center justify-between border-b border-studio pb-3">
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">Sketch preview</h2>
          {styleLoading ? (
            <span className="rounded-full bg-warning/15 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-warning">
              Converting
            </span>
          ) : null}
        </div>
        <div className="overflow-hidden rounded-2xl border border-studio ring-1 ring-white/10">
          <div className="relative flex aspect-square items-center justify-center bg-background">
            {currentImage ? (
              <>
                <img
                  src={currentImage}
                  alt="Forensic sketch"
                  className={`absolute inset-0 h-full w-full object-contain transition duration-300 ${styleLoading ? 'opacity-35 blur-[1px]' : 'opacity-100'
                    }`}
                />
                <span className="absolute left-3 top-3 rounded-full bg-slate-950/70 px-3 py-1 text-xs font-medium text-slate-200 backdrop-blur-sm">
                  {styleLoading ? 'Processing…' : 'Preview ready'}
                </span>
                {styleLoading && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <svg className="h-8 w-8 animate-spin text-brand" fill="none" viewBox="0 0 24 24" aria-hidden>
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  </div>
                )}
              </>
            ) : (
              <span className="text-sm text-muted">No sketch yet</span>
            )}
            <span className="pointer-events-none absolute bottom-3 right-3 select-none text-[10px] font-semibold uppercase tracking-[0.25em] text-muted/70">
              Research use only
            </span>
          </div>
          <p className="border-t border-studio bg-surface px-3 py-2 text-center text-[10px] uppercase tracking-[0.2em] text-muted">
            Live composite channel
          </p>
        </div>

        {hasGenerate && (
          <div className="mt-4">
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted">Sketch mode</p>
            <div className="flex gap-1.5">
              {(Object.keys(STYLE_LABELS) as SketchStyle[]).map((style) => (
                <button
                  key={style}
                  type="button"
                  onClick={() => handleStyleChange(style)}
                  disabled={styleLoading}
                  className={`flex-1 rounded-2xl border py-2 text-xs font-semibold transition duration-200 ${activeStyle === style
                      ? 'border-brand/45 bg-brand/15 text-brand shadow-soft-glow'
                      : 'border-studio bg-panel/80 text-muted hover:border-brand/30 hover:text-text-high'
                    } disabled:pointer-events-none disabled:opacity-40`}
                >
                  {STYLE_LABELS[style]}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {hasGenerate && (
        <div className="glass-card p-5 transition duration-200 ease-out hover:-translate-y-1">
          <h3 className="mb-4 border-b border-studio pb-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">
            Aging progression
          </h3>

          <div className="space-y-4">
            <div>
              <div className="mb-2 flex justify-between text-[10px] font-semibold uppercase tracking-wide text-muted">
                <span>Regression</span>
                <span className="font-mono text-brand">{years > 0 ? `+${years}` : years} yr</span>
                <span>Progression</span>
              </div>
              <input
                type="range"
                min="-40"
                max="40"
                step="5"
                value={years}
                onChange={(e) => setYears(parseInt(e.target.value, 10))}
                className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-muted/25 accent-brand"
              />
            </div>

            <button
              type="button"
              onClick={handleAge}
              disabled={ageLoading || years === 0}
              className="btn-secondary flex w-full items-center justify-center gap-2 border-brand/25 py-2.5 text-xs font-semibold text-brand hover:border-brand/50 hover:bg-brand/10"
            >
              {ageLoading ? (
                <>
                  <svg className="h-4 w-4 animate-spin text-brand" fill="none" viewBox="0 0 24 24" aria-hidden>
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Simulating…
                </>
              ) : (
                <>
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Apply progression
                </>
              )}
            </button>
          </div>
        </div>
      )}

      <div className="glass-card p-5 transition duration-200 ease-out hover:-translate-y-1">
        <GenerationPipeline logs={forensicLogs} isGenerating={isGenerating} />
        <ForensicConsole logs={forensicLogs} />
      </div>

      {criticReport?.reasoning_summary && (
        <div className="glass-card p-5 transition duration-200 ease-out hover:-translate-y-1">
          <h2 className="mb-4 border-b border-studio pb-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">
            Critic notes
          </h2>
          <div className="space-y-3 text-xs leading-relaxed text-muted">
            <div className="flex items-center justify-between gap-2">
              <span
                className={`inline-flex items-center gap-1.5 font-semibold ${criticReport.decision === 'revise' ? 'text-warning' : 'text-success'
                  }`}
              >
                <span
                  className={`h-2 w-2 shrink-0 rounded-full ${criticReport.decision === 'revise' ? 'bg-warning' : 'bg-success'
                    }`}
                />
                {criticReport.decision === 'revise' ? 'Revision suggested' : 'Accepted'}
              </span>
              {criticReport.score != null && (
                <span className="font-mono text-text-high">{Math.round(criticReport.score)}/100</span>
              )}
            </div>
            <p className="text-text-high/90">{criticReport.reasoning_summary}</p>
            {criticReport.missing_features && criticReport.missing_features.length > 0 && (
              <Row label="Missing" value={criticReport.missing_features.slice(0, 3).join(', ')} wrap />
            )}
            {criticReport.prompt_adjustment && (
              <Row label="Adjustment" value={criticReport.prompt_adjustment} wrap />
            )}
          </div>
        </div>
      )}

      <div className="glass-card p-5 transition duration-200 ease-out hover:-translate-y-1">
        <h2 className="mb-4 border-b border-studio pb-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">
          Evaluation scores
        </h2>
        <div className="space-y-4">
          {[
            { label: 'CLIP score', value: clip, hint: 'Prompt alignment' },
            { label: hasEdit ? 'Identity preserved' : 'ArcFace', value: identity, hint: 'Face consistency' },
          ].map(({ label, value, hint }) => (
            <div key={label}>
              <div className="mb-1 flex items-center justify-between">
                <div>
                  <span className="text-xs font-medium text-text-high">{label}</span>
                  <p className="text-[11px] text-muted">{hint}</p>
                </div>
                <span
                  className={`font-mono text-sm font-semibold ${value >= 70 ? 'text-success' : value >= 55 ? 'text-warning' : 'text-muted'
                    }`}
                >
                  {hasGenerate || hasEdit ? `${value}%` : '—'}
                </span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-muted/20">
                <div
                  className={`h-full rounded-full transition-[width] duration-500 ease-out ${scoreBarTone(value)}`}
                  style={{ width: `${value}%` }}
                />
              </div>
            </div>
          ))}
        </div>
        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-[11px] text-muted">
          <span className="inline-flex items-center gap-2">
            <span className="h-2 w-2 shrink-0 rounded-full bg-success" />
            Good ≥70
          </span>
          <span className="inline-flex items-center gap-2">
            <span className="h-2 w-2 shrink-0 rounded-full bg-warning" />
            OK 55–70
          </span>
        </div>
      </div>

      <div className="glass-card p-5 transition duration-200 ease-out hover:-translate-y-1">
        <h2 className="mb-4 border-b border-studio pb-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">
          Metadata audit
        </h2>
        <div className="space-y-3 text-xs">
          <Row label={hasEdit ? 'Edit prompt' : 'Prompt'} value={displayPrompt || '—'} wrap />
          <Row label="Model" value={modelVersion} />
          <Row label="Seed" value={seed} mono />
          <Row label={hasEdit ? 'Edit ID' : 'Image ID'} value={imageId != null ? `#${imageId}` : '—'} />
          <Row label="Audit ID" value={auditId || '—'} mono truncate />
        </div>

        {exportError && <p className="mt-3 text-xs text-danger">{exportError}</p>}
        <button
          type="button"
          onClick={handleExport}
          disabled={exportLoading || (!hasGenerate && !hasEdit)}
          className="btn-secondary mt-4 flex w-full items-center justify-center gap-2 border border-studio py-3 text-sm font-semibold hover:border-brand/40 hover:shadow-soft-glow disabled:pointer-events-none disabled:opacity-40"
        >
          {exportLoading ? (
            <>
              <svg className="h-4 w-4 animate-spin text-brand" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Generating PDF…
            </>
          ) : (
            <>
              <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              Export PDF report
            </>
          )}
        </button>
      </div>
    </div>
  );
}

function Row({
  label,
  value,
  mono = false,
  wrap = false,
  truncate = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
  wrap?: boolean;
  truncate?: boolean;
}) {
  return (
    <div className={`flex ${wrap ? 'flex-col gap-1' : 'items-start justify-between gap-2'}`}>
      <span className="shrink-0 text-muted">{label}</span>
      <span
        className={`text-right font-medium text-text-high ${mono ? 'font-mono text-[11px] text-brand/90' : ''} ${truncate ? 'max-w-[10rem] truncate' : ''} ${wrap ? 'text-left' : ''}`}
      >
        {value}
      </span>
    </div>
  );
}
