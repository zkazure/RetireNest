import type { CommandManifest, CommandOutputSpec } from './command-types';

/** 命令浏览器输出表的一行：标签、单位、格式化后的值。 */
export interface OutputRow {
  name: string;
  label: string;
  unit: string | null;
  value: string;
}

const DEFAULT_DIGITS = 4;

function formatNumber(value: number, digits: number): string {
  if (!Number.isFinite(value)) return '—';
  return new Intl.NumberFormat('zh-CN', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(value);
}

function formatScalar(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'number') return formatNumber(value, DEFAULT_DIGITS);
  if (typeof value === 'boolean') return value ? '是' : '否';
  if (typeof value === 'string') return value;
  return String(value);
}

function formatSeries(value: unknown[]): string {
  if (value.length === 0) return '空数组';
  const head = value.slice(0, 3).map(formatScalar).join('、');
  return value.length > 3 ? `${head}…（共 ${value.length} 项）` : `共 ${value.length} 项：${head}`;
}

function formatObject(value: Record<string, unknown>): string {
  const keys = Object.keys(value);
  if (keys.length === 0) return '空对象';
  return keys
    .map(key => {
      const item = value[key];
      return Array.isArray(item) ? `${key}[${item.length}]` : `${key}=${formatScalar(item)}`;
    })
    .join(' · ');
}

/**
 * 按 manifest 的 type/precision 格式化一个输出值。
 * decimal 在协议里是字符串，原样展示，避免二次舍入。
 */
export function formatOutputValue(spec: CommandOutputSpec, value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (spec.type === 'decimal' && typeof value === 'string') return value;
  if (Array.isArray(value)) return formatSeries(value);
  if (typeof value === 'object') return formatObject(value as Record<string, unknown>);
  if (typeof value === 'number') {
    return formatNumber(value, spec.precision ?? DEFAULT_DIGITS);
  }
  return formatScalar(value);
}

/**
 * 生成输出表的行：只列 visible !== false 的输出，缺值也保留一行「—」，
 * 便于对照 manifest 检查命令是否少返回了字段。
 */
export function buildOutputRows(
  command: CommandManifest,
  outputs: Record<string, unknown>,
): OutputRow[] {
  return command.outputs
    .filter(spec => spec.visible !== false)
    .map(spec => ({
      name: spec.name,
      label: spec.question,
      unit: spec.unit ?? null,
      value: formatOutputValue(spec, outputs[spec.name]),
    }));
}
