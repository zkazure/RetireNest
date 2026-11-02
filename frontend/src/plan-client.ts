import type { FieldError, PlanRequest } from './form-types';
import type { PlanErrorResponse, PlanResponse, PlanScenario } from './plan-contract';

const TIMEOUT_MS = 20_000;
const SCENARIO_IDS = new Set(['conservative', 'baseline', 'optimistic']);

export class PlanApiError extends Error {
  readonly code: string;
  readonly fieldErrors: FieldError[];
  readonly status: number;

  constructor(code: string, message: string, fieldErrors: FieldError[] = [], status = 0) {
    super(message);
    this.name = 'PlanApiError';
    this.code = code;
    this.fieldErrors = fieldErrors;
    this.status = status;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function isFieldError(value: unknown): value is FieldError {
  return isRecord(value) && typeof value.field === 'string' && typeof value.message === 'string';
}

function isPlanError(value: unknown): value is PlanErrorResponse {
  if (!isRecord(value) || typeof value.code !== 'string' || typeof value.message !== 'string') {
    return false;
  }
  if (value.field_errors === undefined) return true;
  return Array.isArray(value.field_errors) && value.field_errors.every(isFieldError);
}

function isPlanInput(value: unknown): boolean {
  if (!isRecord(value) || typeof value.city !== 'string') return false;
  const numbers = [
    'age',
    'retirementAge',
    'lifeExpectancy',
    'monthlyIncome',
    'monthlyExpense',
    'assets',
    'debt',
    'retirementExpense',
    'monthlyPension',
    'nominalReturn',
    'inflation',
  ];
  return numbers.every(key => isFiniteNumber(value[key]));
}

function isProjectionPoint(value: unknown): boolean {
  return isRecord(value) && isFiniteNumber(value.age) && isFiniteNumber(value.assets);
}

function isPlanResult(value: unknown): boolean {
  if (!isRecord(value)) return false;
  const numbers = [
    'yearsToRetirement',
    'retirementYears',
    'realReturn',
    'monthlySurplus',
    'target',
    'projected',
    'gap',
    'coverage',
    'requiredMonthlySaving',
  ];
  if (!numbers.every(key => isFiniteNumber(value[key]))) return false;
  if (!(value.depletedAge === null || isFiniteNumber(value.depletedAge))) return false;
  return (
    Array.isArray(value.points) &&
    value.points.length > 0 &&
    value.points.every(isProjectionPoint)
  );
}

function isScenario(value: unknown): value is PlanScenario {
  if (!isRecord(value)) return false;
  return (
    typeof value.id === 'string' &&
    SCENARIO_IDS.has(value.id) &&
    typeof value.label === 'string' &&
    isFiniteNumber(value.nominal_return) &&
    isFiniteNumber(value.target) &&
    isFiniteNumber(value.projected) &&
    isFiniteNumber(value.gap)
  );
}

function isPlanResponse(value: unknown): value is PlanResponse {
  if (!isRecord(value)) return false;
  if (typeof value.template_id !== 'string' || typeof value.schema_version !== 'string') {
    return false;
  }
  if (value.mode !== 'demo' && value.mode !== 'backend') return false;
  if (!isPlanInput(value.plan_input) || !isPlanResult(value.result)) return false;
  if (
    !Array.isArray(value.scenarios) ||
    value.scenarios.length !== 3 ||
    !value.scenarios.every(isScenario)
  ) {
    return false;
  }
  if (typeof value.explanation !== 'string') return false;
  return Array.isArray(value.warnings) && value.warnings.every(item => typeof item === 'string');
}

export async function requestPlan(request: PlanRequest): Promise<PlanResponse> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch('/api/retirement/plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
      signal: controller.signal,
    });
    const payload: unknown = await response.json().catch(() => null);

    if (!response.ok) {
      if (isPlanError(payload)) {
        throw new PlanApiError(
          payload.code,
          payload.message,
          payload.field_errors ?? [],
          response.status,
        );
      }
      if (response.status >= 500) {
        throw new PlanApiError(
          'SERVICE_UNAVAILABLE',
          '测算服务暂时不可用，请确认后端已启动后重试。',
          [],
          response.status,
        );
      }
      throw new PlanApiError(
        'HTTP_ERROR',
        `测算服务返回 ${response.status}。`,
        [],
        response.status,
      );
    }

    if (!isPlanResponse(payload)) {
      throw new PlanApiError('INVALID_RESPONSE', '测算服务返回的数据格式不正确。');
    }
    if (
      payload.template_id !== request.template_id ||
      payload.schema_version !== request.schema_version
    ) {
      throw new PlanApiError(
        'SCHEMA_VERSION_MISMATCH',
        '表单模板版本不匹配，请刷新页面后重试。',
      );
    }
    return payload;
  } catch (error) {
    if (error instanceof PlanApiError) throw error;
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new PlanApiError('TIMEOUT', '测算服务响应超时，请重试。');
    }
    throw new PlanApiError('NETWORK_ERROR', '无法连接测算服务，请确认后端已启动。');
  } finally {
    clearTimeout(timer);
  }
}
