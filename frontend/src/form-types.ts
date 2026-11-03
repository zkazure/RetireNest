export type FormValue = string | number | boolean | null;
export type RawValues = Record<string, string | boolean>;
export type FormValues = Record<string, FormValue>;
export type FieldType = 'text' | 'number' | 'decimal' | 'date' | 'select' | 'checkbox' | 'textarea' | 'tier' | 'multi';
export interface Condition { field: string; equals: string | boolean }
export interface FormField {
  name: string;
  label: string;
  type: FieldType;
  required?: boolean;
  integer?: boolean;
  min?: number;
  max?: number;
  step?: number;
  precision?: number;
  maxLength?: number;
  unit?: string;
  placeholder?: string;
  hint?: string;
  defaultValue?: string | number | boolean;
  options?: {label: string; value: string}[];
  tiers?: {value: string; label: string; amount: number}[];
  derive?: string;
  optionsSource?: string;
  allowCustom?: boolean;
  visibleWhen?: Condition[];
}
export interface FormSection {
  id: string;
  title: string;
  description?: string;
  collapsible?: boolean;
  toggle?: {name: string; label: string; defaultValue: boolean};
  fields: FormField[];
}
export interface FormRule {
  type: 'lessThan' | 'dateBefore' | 'minimumDifference';
  left: string;
  right: string;
  minimum?: number;
  message: string;
}
export interface FormPreset {
  id: string;
  label: string;
  description?: string;
  values: Record<string, string | boolean>;
}
export interface FormTemplate {
  id: string;
  version: string;
  title: string;
  description: string;
  optionSets: Record<string, {label: string; value: string}[]>;
  sections: FormSection[];
  rules: FormRule[];
  presets: FormPreset[];
}
export interface FieldError { field: string; message: string }
