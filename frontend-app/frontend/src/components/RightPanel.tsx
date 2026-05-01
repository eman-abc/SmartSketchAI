import { useState } from 'react';
import type { GenerateResult, EditResult } from '../types';
import { convertSketchStyle, exportForensicReport, ageForensicSketch } from '../lib/api';

type RightPanelProps = {
  generateResult?: GenerateResult | null;
  editResult?: EditResult | null;
  prompt?: string;
  onUpdateResult?: (result: any) => void;
};

type SketchStyle = 'photo' | 'pencil' | 'charcoal';

const STYLE_LABELS: Record<SketchStyle, string> = {
  photo: '🖼️ Photo',
  pencil: '✏️ Pencil',
  charcoal: '🎨 Charcoal',
};

function scorePercent(value: number | undefined | null): number {
  if (value == null || typeof value !== 'number') return 0;
  return Math.round(Math.min(1, Math.max(0, value < 1 ? value : value / 100)) * 100);
}

export default function RightPanel({ 
  generateResult = null, 
  editResult = null, 
  prompt = '',
  onUpdateResult
}: RightPanelProps) {
  const [activeStyle, setActiveStyle] = useState<SketchStyle>('photo');
  const [styleLoading, setStyleLoading] = useState(false);
  const [styledImageUrl, setStyledImageUrl] = useState<string | null>(null);
  const [exportLoading, setExportLoading] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [years, setYears] = useState(15);
  const [ageLoading, setAgeLoading] = useState(false);

  const hasGenerate = generateResult != null;
  const hasEdit = editResult != null;

  const currentResult = hasEdit ? editResult : generateResult;
  const baseImageUrl = hasEdit ? editResult?.edited_image_url : generateResult?.image_url;
  const currentImage = styledImageUrl ?? baseImageUrl;

  const scores = currentResult?.scores ?? {};
  const rawClip = (scores as Record<string, number | undefined>)?.clip_score ?? (scores as any)?.combined_score;
  const clip = rawClip != null && rawClip > 1 ? Math.round(rawClip) : scorePercent(rawClip);
  const identity = hasEdit
    ? scorePercent(editResult?.identity_score)
    : scorePercent((generateResult?.scores as any)?.identity_score);

  const meta = (currentResult?.metadata ?? {}) as Record<string, unknown>;
  const seed = meta.seed != null ? String(meta.seed) : '—';
  const modelVersion = meta.model_version != null ? String(meta.model_version) : 'SDXL-1.0';
  const displayPrompt = hasEdit ? editResult?.edit_prompt : prompt;
  const auditId = hasEdit ? editResult?.edit_id : generateResult?.generation_id;
  const imageId = hasEdit ? editResult?.id : generateResult?.id;

  // ── Sketch style toggle ─────────────────────────────────────────────────
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
    } catch (err) {
      console.error('Style conversion failed:', err);
      setActiveStyle('photo');
      setStyledImageUrl(null);
    } finally {
      setStyleLoading(false);
    }
  };

  // ── Export forensic report ─────────────────────────────────────────────
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

  // ── Age Progression ───────────────────────────────────────────────────
  const handleAge = async () => {
    const originalImageId = generateResult?.id;
    if (!originalImageId || ageLoading) return;

    setAgeLoading(true);
    try {
      const res = await ageForensicSketch({
        original_image_id: originalImageId,
        years,
      });
      // Update the main view with the aged result
      // The backend returns an EditResult-like object with edited_image_url
      if (onUpdateResult) {
        onUpdateResult(res);
      }
    } catch (err) {
      console.error('Age progression failed:', err);
    } finally {
      setAgeLoading(false);
    }
  };

  return (
    <div className="w-80 bg-gray-50 dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 overflow-y-auto flex-shrink-0">
      <div className="p-4 space-y-5">

        {/* ── Preview ─────────────────────────────────────────────────── */}
        <div>
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Preview</h2>
          <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
            <div className="aspect-square bg-gray-100 dark:bg-gray-800 flex items-center justify-center relative">
              {currentImage ? (
                <>
                  <img
                    src={currentImage}
                    alt="Forensic sketch"
                    className={`w-full h-full object-contain transition-opacity duration-300 ${styleLoading ? 'opacity-40' : 'opacity-100'}`}
                  />
                  {styleLoading && (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <svg className="w-8 h-8 text-blue-500 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                    </div>
                  )}
                </>
              ) : (
                <span className="text-gray-400 dark:text-gray-500 text-sm">No sketch yet</span>
              )}
              <div className="absolute bottom-2 right-2 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm px-2 py-0.5 rounded text-xs font-medium text-gray-500 dark:text-gray-400">
                RESEARCH USE ONLY
              </div>
            </div>
          </div>

          {/* ── Sketch Style Toggle ───────────────────────────────────── */}
          {hasGenerate && (
            <div className="mt-3">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Sketch Style</p>
              <div className="flex gap-1.5">
                {(Object.keys(STYLE_LABELS) as SketchStyle[]).map(style => (
                  <button
                    key={style}
                    type="button"
                    onClick={() => handleStyleChange(style)}
                    disabled={styleLoading}
                    className={`flex-1 text-xs py-2 px-1 rounded-lg border font-medium transition-all ${
                      activeStyle === style
                        ? 'bg-blue-600 border-blue-600 text-white shadow-sm'
                        : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-blue-400 hover:text-blue-600'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    {STYLE_LABELS[style]}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── Aging & Progression ─────────────────────────────────────── */}
        {hasGenerate && (
          <div className="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
            <h3 className="text-xs font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-4">Aging & Progression</h3>
            
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-[10px] font-medium text-gray-500 dark:text-gray-400 mb-2">
                  <span>Regression</span>
                  <span className="text-blue-600 dark:text-blue-400 font-bold text-xs">{years > 0 ? `+${years}` : years} Years</span>
                  <span>Progression</span>
                </div>
                <input
                  type="range"
                  min="-40"
                  max="40"
                  step="5"
                  value={years}
                  onChange={(e) => setYears(parseInt(e.target.value))}
                  className="w-full h-1.5 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
                />
              </div>

              <button
                type="button"
                onClick={handleAge}
                disabled={ageLoading || years === 0}
                className="w-full flex items-center justify-center gap-2 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/50 disabled:opacity-40 border border-blue-200 dark:border-blue-800 py-2 rounded-xl text-xs font-semibold transition-all"
              >
                {ageLoading ? (
                  <>
                    <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Simulating Aging…
                  </>
                ) : (
                  <>
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Apply Progression
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* ── Evaluation Scores ────────────────────────────────────────── */}
        <div>
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Evaluation Scores</h2>
          <div className="space-y-3">
            {[
              { label: 'CLIP Score', value: clip, hint: 'Prompt-image alignment' },
              { label: hasEdit ? 'Identity Preserved' : 'ArcFace', value: identity, hint: 'Face consistency' },
            ].map(({ label, value, hint }) => (
              <div key={label} className="bg-white dark:bg-gray-900 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
                <div className="flex justify-between items-center mb-1">
                  <div>
                    <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{label}</span>
                    <p className="text-xs text-gray-400 dark:text-gray-500">{hint}</p>
                  </div>
                  <span className={`text-sm font-bold ${value >= 70 ? 'text-green-600 dark:text-green-400' : value >= 55 ? 'text-yellow-600 dark:text-yellow-400' : 'text-gray-400'}`}>
                    {hasGenerate || hasEdit ? `${value}%` : '—'}
                  </span>
                </div>
                <div className="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-1.5">
                  <div
                    className={`h-1.5 rounded-full transition-all duration-500 ${value >= 70 ? 'bg-green-500' : value >= 55 ? 'bg-yellow-500' : 'bg-gray-300 dark:bg-gray-600'}`}
                    style={{ width: `${value}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-2 flex gap-4 text-xs text-gray-500 dark:text-gray-400">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500 inline-block" />≥70 Good</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-yellow-500 inline-block" />55–70 OK</span>
          </div>
        </div>

        {/* ── Metadata & Audit ─────────────────────────────────────────── */}
        <div>
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Metadata & Audit</h2>
          <div className="bg-white dark:bg-gray-900 rounded-lg p-4 border border-gray-200 dark:border-gray-700 space-y-3 text-xs">
            <Row label={hasEdit ? 'Edit Prompt' : 'Prompt'} value={displayPrompt || '—'} wrap />
            <Row label="Model" value={modelVersion} />
            <Row label="Seed" value={seed} mono />
            <Row label={hasEdit ? 'Edit ID' : 'Image ID'} value={imageId != null ? `#${imageId}` : '—'} />
            <Row label="Audit ID" value={auditId || '—'} mono truncate />
          </div>

          {/* Export button */}
          {exportError && (
            <p className="mt-2 text-xs text-red-500 dark:text-red-400">{exportError}</p>
          )}
          <button
            type="button"
            onClick={handleExport}
            disabled={exportLoading || (!hasGenerate && !hasEdit)}
            className="w-full mt-3 flex items-center justify-center gap-2 bg-gray-900 dark:bg-gray-700 hover:bg-gray-800 dark:hover:bg-gray-600 disabled:opacity-40 disabled:cursor-not-allowed text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-colors"
          >
            {exportLoading ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Generating Report…
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Export PDF Forensic Report
              </>
            )}
          </button>
        </div>

      </div>
    </div>
  );
}

// Small helper component
function Row({
  label, value, mono = false, wrap = false, truncate = false,
}: { label: string; value: string; mono?: boolean; wrap?: boolean; truncate?: boolean }) {
  return (
    <div className={`flex ${wrap ? 'flex-col gap-1' : 'justify-between items-start gap-2'}`}>
      <span className="text-gray-500 dark:text-gray-400 flex-shrink-0">{label}:</span>
      <span className={`text-gray-900 dark:text-white font-medium text-right ${mono ? 'font-mono' : ''} ${truncate ? 'truncate max-w-[140px]' : ''} ${wrap ? 'text-left' : ''}`}>
        {value}
      </span>
    </div>
  );
}
