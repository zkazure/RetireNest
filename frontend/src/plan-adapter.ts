import { CommandApiError } from './command-client';
import type { PlanInput, PlanResult, ProjectionPoint } from './model';
import type { PlanResponse, PlanScenario } from './plan-contract';

const SCENARIO_IDS = new Set(['conservative', 'baseline', 'optimistic']);

function invalid(): CommandApiError {
  return new CommandApiError('INVALID_RESPONSE', '退休规划结果格式不正确。');
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function requireNumber(source: Record<string, unknown>, key: string): number {
  const value = source[key];
  if (typeof value !== 'number' || !Number.isFinite(value)) throw invalid();
  return value;
}

function toPlanInput(value: unknown): PlanInput {
  if (!isRecord(value) || typeof value.city !== 'string') throw invalid();
  return {
    city: value.city,
    age: requireNumber(value, 'age'),
    retirementAge: requireNumber(value, 'retirementAge'),
    lifeExpectancy: requireNumber(value, 'lifeExpectancy'),
    monthlyIncome: requireNumber(value, 'monthlyIncome'),
    monthlyExpense: requireNumber(value, 'monthlyExpense'),
    assets: requireNumber(value, 'assets'),
    debt: requireNumber(value, 'debt'),
    retirementExpense: requireNumber(value, 'retirementExpense'),
    monthlyPension: requireNumber(value, 'monthlyPension'),
    nominalReturn: requireNumber(value, 'nominalReturn'),
    inflation: requireNumber(value, 'inflation'),
  };
}

function toPoint(value: unknown): ProjectionPoint {
  if (!isRecord(value)) throw invalid();
  return { age: requireNumber(value, 'age'), assets: requireNumber(value, 'assets') };
}

function toPlanResult(value: unknown): PlanResult {
  if (!isRecord(value)) throw invalid();
  const points = value.points;
  if (!Array.isArray(points) || points.length === 0) throw invalid();
  const depletedAge = value.depletedAge;
  if (depletedAge !== null && typeof depletedAge !== 'number') throw invalid();
  return {
    yearsToRetirement: requireNumber(value, 'yearsToRetirement'),
    retirementYears: requireNumber(value, 'retirementYears'),
    realReturn: requireNumber(value, 'realReturn'),
    monthlySurplus: requireNumber(value, 'monthlySurplus'),
    target: requireNumber(value, 'target'),
    projected: requireNumber(value, 'projected'),
    gap: requireNumber(value, 'gap'),
    coverage: requireNumber(value, 'coverage'),
    requiredMonthlySaving: requireNumber(value, 'requiredMonthlySaving'),
    points: points.map(toPoint),
    depletedAge,
  };
}

function toScenario(value: unknown): PlanScenario {
  if (!isRecord(value) || typeof value.id !== 'string' || !SCENARIO_IDS.has(value.id)) {
    throw invalid();
  }
  if (typeof value.label !== 'string') throw invalid();
  return {
    id: value.id as PlanScenario['id'],
    label: value.label,
    nominal_return: requireNumber(value, 'nominal_return'),
    target: requireNumber(value, 'target'),
    projected: requireNumber(value, 'projected'),
    gap: requireNumber(value, 'gap'),
  };
}

export function toPlanResponse(outputs: Record<string, unknown>): PlanResponse {
  const scenarios = outputs.scenarios;
  if (!Array.isArray(scenarios) || scenarios.length !== 3) throw invalid();
  const explanation = outputs.explanation;
  const warnings = outputs.warnings;
  if (typeof explanation !== 'string') throw invalid();
  if (!Array.isArray(warnings) || !warnings.every(item => typeof item === 'string')) {
    throw invalid();
  }
  return {
    plan_input: toPlanInput(outputs.plan_input),
    result: toPlanResult({
      yearsToRetirement: outputs.years_to_retirement,
      retirementYears: outputs.retirement_years,
      realReturn: outputs.real_return,
      monthlySurplus: outputs.monthly_surplus,
      target: outputs.target,
      projected: outputs.projected,
      gap: outputs.gap,
      coverage: outputs.coverage,
      requiredMonthlySaving: outputs.required_monthly_saving,
      points: outputs.points,
      depletedAge: outputs.depleted_age,
    }),
    scenarios: scenarios.map(toScenario),
    explanation,
    warnings: warnings as string[],
  };
}
