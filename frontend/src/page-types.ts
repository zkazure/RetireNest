// 后端页面清单的类型。页面只消费这里的字段，不在本地保存问题文案。
export type PageFieldType =
  | 'text'
  | 'number'
  | 'decimal'
  | 'date'
  | 'select'
  | 'checkbox'
  | 'textarea'
  | 'tier';

export interface PageCondition {
  field: string;
  equals: string | boolean;
}

export interface PageFieldSpec {
  name: string;
  label: string;
  type: PageFieldType;
  required: boolean;
  integer?: boolean;
  unit?: string | null;
  defaultValue?: string | number | boolean;
  min?: number;
  max?: number;
  precision?: number;
  maxLength?: number;
  hint?: string;
  options?: { label: string; value: string }[];
  tiers?: { value: string; label: string; amount: number }[];
  derive?: string | null;
  allowCustom?: boolean;
  visibleWhen?: PageCondition[];
  source?: { command: string; input: string };
}

export interface PageToggleSpec {
  name: string;
  label: string;
  defaultValue: boolean;
}

export interface PageSectionSpec {
  id: string;
  title: string;
  description?: string | null;
  toggle?: PageToggleSpec | null;
  fields: PageFieldSpec[];
}

export interface PageOutputSpec {
  name: string;
  question: string;
  type: string;
  unit?: string | null;
  precision?: number | null;
  semantic?: string | null;
  visible: boolean;
  time_axis?: Record<string, unknown> | null;
}

export interface PageExecutionSpec {
  command: string;
  version: string;
  question: string;
  description?: string;
  inputs: Record<string, string>;
  toggle?: string | null;
  outputs: PageOutputSpec[];
}

export interface PageRuleSpec {
  type: 'lessThan' | 'dateBefore' | 'minimumDifference';
  left: string;
  right: string;
  message: string;
  minimum?: number;
}

export interface PagePresetSpec {
  id: string;
  label: string;
  description?: string | null;
  values: Record<string, string | boolean>;
}

export interface PageManifest {
  id: string;
  version: string;
  title: string;
  description: string;
  sections: PageSectionSpec[];
  executions: PageExecutionSpec[];
  rules: PageRuleSpec[];
  presets: PagePresetSpec[];
}
