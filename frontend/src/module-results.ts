import type { PageExecutionSpec, PageOutputSpec } from './page-types';

export interface ModuleResult {
  execution: PageExecutionSpec;
  outputs: Record<string, unknown>;
}

const escapeHtml = (value: unknown) =>
  String(value).replace(
    /[&<>"']/g,
    char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]!,
  );

function toNumber(value: unknown): number | null {
  const number = typeof value === 'string' ? Number(value) : value;
  return typeof number === 'number' && Number.isFinite(number) ? number : null;
}

function formatPlain(value: number, digits?: number | null): string {
  if (digits === null || digits === undefined) {
    return value.toLocaleString('zh-CN', { maximumFractionDigits: 2 });
  }
  return value.toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function formatRatio(value: number): string {
  return `${formatPlain(value * 100, 4).replace(/\.?0+$/, '')}%`;
}

function digitsFor(output: PageOutputSpec): number | null {
  if (output.precision !== null && output.precision !== undefined) return output.precision;
  return output.type === 'integer' ? 0 : null;
}

function seriesSummary(
  output: PageOutputSpec,
  value: unknown,
): { text: string; note: string } | null {
  if (typeof value !== 'object' || value === null) return null;
  const series = (value as Record<string, unknown>).total;
  if (!Array.isArray(series) || series.length === 0) return null;
  const first = toNumber(series[0]);
  const last = toNumber(series[series.length - 1]);
  if (first === null || last === null) return null;
  const digits = digitsFor(output);
  const suffix = output.unit ? ` ${output.unit}` : '';
  return {
    text: `${formatPlain(first, digits)}${suffix}`,
    note: `末年 ${formatPlain(last, digits)}${suffix}`,
  };
}

function renderMetric(output: PageOutputSpec, value: unknown): string {
  if (value === null || value === undefined) return '';

  let text: string;
  let note = '';
  if (output.type === 'object') {
    const summary = seriesSummary(output, value);
    if (!summary) return '';
    text = summary.text;
    note = summary.note;
  } else if (output.semantic === 'ratio') {
    const number = toNumber(value);
    if (number === null) return '';
    text = formatRatio(number);
  } else if (output.type === 'text') {
    text = String(value);
  } else {
    const number = toNumber(value);
    if (number === null) return '';
    text = formatPlain(number, digitsFor(output));
  }

  const unit =
    output.type === 'object' || output.semantic === 'ratio' || !output.unit
      ? ''
      : `<span>${escapeHtml(output.unit)}</span>`;
  return `<div class="module-metric"><div class="module-metric-label">${escapeHtml(
    output.question,
  )}</div><div class="module-metric-value">${escapeHtml(text)}${unit}</div>${
    note ? `<p class="module-metric-note">${escapeHtml(note)}</p>` : ''
  }</div>`;
}

function renderCard(result: ModuleResult): string {
  const rows = result.execution.outputs
    .filter(output => output.visible)
    .map(output => renderMetric(output, result.outputs[output.name]))
    .filter(Boolean)
    .join('');
  if (!rows) return '';

  const id = `module-${result.execution.command.replace(/\./g, '-')}`;
  const description = result.execution.description
    ? `<p class="section-description">${escapeHtml(result.execution.description)}</p>`
    : '';
  return `<section class="card module-card" aria-labelledby="${id}">
    <div class="section-heading"><div><h2 id="${id}">${escapeHtml(
      result.execution.question,
    )}</h2>${description}</div></div>
    <div class="module-metrics">${rows}</div>
  </section>`;
}

export function renderModuleResults(results: ModuleResult[]): string {
  return results.map(renderCard).filter(Boolean).join('');
}
