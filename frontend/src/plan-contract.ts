import type { PlanInput, PlanResult } from './model';

// 前端与服务端的响应契约。页面只消费这里的字段，不在本地重新计算。
export interface PlanScenario {
  id: 'conservative' | 'baseline' | 'optimistic';
  label: string;
  nominal_return: number;
  target: number;
  projected: number;
  gap: number;
}
export interface PlanResponse {
  template_id: string;
  schema_version: string;
  mode: 'demo' | 'backend';
  plan_input: PlanInput;
  result: PlanResult;
  scenarios: PlanScenario[];
  explanation: string;
  warnings: string[];
}
export interface PlanErrorResponse {
  code: 'VALIDATION_ERROR' | 'SCHEMA_VERSION_MISMATCH' | 'CALCULATION_ERROR';
  message: string;
  field_errors?: { field: string; message: string }[];
}
