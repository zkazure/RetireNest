import type { PlanInput, PlanResult } from './model';

// Proposed integration contract. No HTTP request is issued in the current demo.
export interface PlanResponse {
  template_id: string;
  schema_version: string;
  mode: 'demo' | 'backend';
  plan_input: PlanInput;
  result: PlanResult;
  scenarios: {
    id: 'conservative' | 'baseline' | 'optimistic';
    label: string;
    nominal_return: number;
    target: number;
    projected: number;
    gap: number;
  }[];
  explanation: string;
  warnings: string[];
}
export interface PlanErrorResponse {
  code: 'VALIDATION_ERROR' | 'SCHEMA_VERSION_MISMATCH' | 'CALCULATION_ERROR';
  message: string;
  field_errors?: { field: string; message: string }[];
}
