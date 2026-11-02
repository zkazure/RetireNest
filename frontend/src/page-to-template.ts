import type { FormField, FormRule, FormSection, FormTemplate } from './form-types';
import type { PageFieldSpec, PageManifest, PageSectionSpec } from './page-types';

// 页面清单只携带后端给的文案与约束；这里只做结构转换，不补任何业务字段。
function toField(field: PageFieldSpec): FormField {
  const converted: FormField = {
    name: field.name,
    label: field.label,
    type: field.type,
    required: field.required,
  };
  if (field.integer) converted.integer = true;
  if (field.unit) converted.unit = field.unit;
  if (field.defaultValue !== undefined) converted.defaultValue = field.defaultValue;
  if (field.min !== undefined) converted.min = field.min;
  if (field.max !== undefined) converted.max = field.max;
  if (field.precision !== undefined) converted.precision = field.precision;
  if (field.maxLength !== undefined) converted.maxLength = field.maxLength;
  if (field.hint) converted.hint = field.hint;
  if (field.options) {
    converted.options = field.options.map(option => ({
      label: option.label,
      value: option.value,
    }));
  }
  if (field.allowCustom) converted.allowCustom = true;
  if (field.visibleWhen) {
    converted.visibleWhen = field.visibleWhen.map(condition => ({
      field: condition.field,
      equals: condition.equals,
    }));
  }
  return converted;
}

function toSection(section: PageSectionSpec): FormSection {
  const converted: FormSection = {
    id: section.id,
    title: section.title,
    fields: section.fields.map(toField),
  };
  if (section.description) converted.description = section.description;
  if (section.toggle) {
    converted.toggle = {
      name: section.toggle.name,
      label: section.toggle.label,
      defaultValue: section.toggle.defaultValue,
    };
  }
  return converted;
}

function toRule(rule: PageManifest['rules'][number]): FormRule {
  const converted: FormRule = {
    type: rule.type,
    left: rule.left,
    right: rule.right,
    message: rule.message,
  };
  if (rule.minimum !== undefined) converted.minimum = rule.minimum;
  return converted;
}

export function pageToTemplate(page: PageManifest): FormTemplate {
  return {
    id: page.id,
    version: page.version,
    title: page.title,
    description: page.description,
    optionSets: {},
    sections: page.sections.map(toSection),
    rules: page.rules.map(toRule),
  };
}
