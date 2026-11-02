import type { PageManifest } from './page-types';

const TIMEOUT_MS = 20_000;
const FIELD_TYPES = new Set([
  'text',
  'number',
  'decimal',
  'date',
  'select',
  'checkbox',
  'textarea',
  'tier',
]);

export class PageLoadError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'PageLoadError';
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isField(value: unknown): boolean {
  return (
    isRecord(value) &&
    typeof value.name === 'string' &&
    typeof value.label === 'string' &&
    typeof value.type === 'string' &&
    FIELD_TYPES.has(value.type) &&
    typeof value.required === 'boolean'
  );
}

function isSection(value: unknown): boolean {
  return (
    isRecord(value) &&
    typeof value.id === 'string' &&
    typeof value.title === 'string' &&
    Array.isArray(value.fields) &&
    value.fields.every(isField)
  );
}

function isExecution(value: unknown): boolean {
  return (
    isRecord(value) &&
    typeof value.command === 'string' &&
    typeof value.version === 'string' &&
    typeof value.question === 'string' &&
    isRecord(value.inputs) &&
    Array.isArray(value.outputs) &&
    value.outputs.every(
      (output: unknown) =>
        isRecord(output) &&
        typeof output.name === 'string' &&
        typeof output.question === 'string' &&
        typeof output.visible === 'boolean',
    )
  );
}

function isPage(value: unknown): value is PageManifest {
  return (
    isRecord(value) &&
    typeof value.id === 'string' &&
    typeof value.version === 'string' &&
    typeof value.title === 'string' &&
    typeof value.description === 'string' &&
    Array.isArray(value.sections) &&
    value.sections.every(isSection) &&
    Array.isArray(value.executions) &&
    value.executions.every(isExecution) &&
    Array.isArray(value.rules)
  );
}

export async function loadPage(pageId = 'retirement'): Promise<PageManifest> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(`/api/pages/${encodeURIComponent(pageId)}`, {
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    });
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      throw new PageLoadError(
        isRecord(payload) && typeof payload.message === 'string'
          ? payload.message
          : `页面清单返回 ${response.status}。`,
      );
    }
    if (!isPage(payload)) throw new PageLoadError('页面清单格式不正确。');
    return payload;
  } catch (error) {
    if (error instanceof PageLoadError) throw error;
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new PageLoadError('页面清单响应超时，请重试。');
    }
    throw new PageLoadError('无法连接测算服务，请确认后端已启动。');
  } finally {
    clearTimeout(timer);
  }
}
