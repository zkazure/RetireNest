import type { PlanInput, PlanResult } from './model';

// 页面消费的退休规划结果。它由 plan.retirement 命令的输出映射而来，
// 页面只读这里的数据，不在本地重新计算。
export interface PlanScenario {
  id: 'conservative' | 'baseline' | 'optimistic';
  label: string;
  nominal_return: number;
  target: number;
  projected: number;
  gap: number;
}
export interface PlanResponse {
  plan_input: PlanInput;
  result: PlanResult;
  scenarios: PlanScenario[];
  explanation: string;
  warnings: string[];
}
