import type { FieldError, FormField, FormTemplate, FormValues, RawValues } from './form-types';

export function allFields(template: FormTemplate): FormField[] {
  return template.sections.flatMap(section => [
    ...(section.toggle ? [{...section.toggle, type:'checkbox' as const}] : []),
    ...section.fields,
  ]);
}
export function fieldOptions(template: FormTemplate, field: FormField) {
  return field.options ?? (field.optionsSource ? template.optionSets[field.optionsSource] : []) ?? [];
}
export function defaultValues(template: FormTemplate): RawValues {
  return Object.fromEntries(allFields(template).map(field => [field.name,
    field.type === 'checkbox' ? field.defaultValue === true : String(field.defaultValue ?? '')]));
}

// Only data is accepted in the template. No expressions, eval or HTML rendering.
export function validateTemplate(value: unknown): asserts value is FormTemplate {
  const template = value as FormTemplate;
  if (!template || typeof template.id !== 'string' || typeof template.version !== 'string' || !Array.isArray(template.sections) || !template.optionSets || !Array.isArray(template.rules)) throw new Error('表单模板格式无效。');
  const ids = new Set<string>(), names = new Set<string>();
  const supported = new Set(['text','number','decimal','date','select','checkbox','textarea','tier']);
  for (const section of template.sections) {
    if (!section || typeof section.id !== 'string' || typeof section.title !== 'string' || ids.has(section.id) || !Array.isArray(section.fields)) throw new Error('模板分组无效或重复。');
    ids.add(section.id);
    if (section.toggle && (typeof section.toggle.label !== 'string' || typeof section.toggle.defaultValue !== 'boolean')) throw new Error('模块开关配置无效。');
  }
  for (const field of allFields(template)) {
    if (!/^[a-z][a-z0-9_]*$/.test(field.name) || ['constructor','prototype','__proto__'].includes(field.name) || names.has(field.name) || typeof field.label !== 'string' || !supported.has(field.type)) throw new Error('模板字段无效、重复或类型不受支持：' + field.name);
    names.add(field.name);
    if (field.type === 'tier') {
      const tiers = field.tiers ?? [];
      const values = tiers.map((tier: {value: string}) => tier.value);
      if (!tiers.length || tiers.some(tier => typeof tier.label !== 'string' || typeof tier.value !== 'string' || typeof tier.amount !== 'number' || !tier.value) || new Set(values).size !== values.length) throw new Error('档位配置无效：' + field.name);
    }
    if (field.type === 'select') {
      if (field.optionsSource && !Array.isArray(template.optionSets[field.optionsSource])) throw new Error('缺少选项集：' + field.optionsSource);
      const options = fieldOptions(template,field);
      const values = options.map(option => option.value);
      if (!options.length || options.some(option => typeof option.label !== 'string' || typeof option.value !== 'string' || !option.value || option.value === '__custom__') || new Set(values).size !== values.length) throw new Error('下拉选项无效：' + field.name);
    }
  }
  const dependencies = new Map<string,string[]>();
  for (const section of template.sections) for (const field of section.fields) {
    const refs = (field.visibleWhen ?? []).map(condition => condition.field);
    if (refs.some(ref => !names.has(ref))) throw new Error('显示条件引用了未知字段。');
    dependencies.set(field.name, [...refs, ...(section.toggle ? [section.toggle.name] : [])]);
  }
  function visit(name: string, path = new Set<string>()) {
    if (path.has(name)) throw new Error('模板显示条件存在循环引用。');
    const next = new Set(path).add(name);
    for (const ref of dependencies.get(name) ?? []) visit(ref,next);
  }
  names.forEach(name => visit(name));
  for (const rule of template.rules) {
    if (!['lessThan','dateBefore','minimumDifference'].includes(rule.type) || !names.has(rule.left) || !names.has(rule.right) || typeof rule.message !== 'string') throw new Error('跨字段校验配置无效。');
  }
}

export function activeFieldNames(template: FormTemplate, raw: RawValues): Set<string> {
  const fields = new Map(allFields(template).map(field => [field.name,field]));
  const owners = new Map(template.sections.flatMap(section => section.fields.map(field => [field.name,section] as const)));
  const cache = new Map<string,boolean>();
  function active(name: string): boolean {
    if (cache.has(name)) return cache.get(name)!;
    const field = fields.get(name);
    if (!field) return false;
    const toggle = owners.get(name)?.toggle;
    const enabled = (!toggle || raw[toggle.name] === true) && (field.visibleWhen ?? []).every(condition => active(condition.field) && raw[condition.field] === condition.equals);
    cache.set(name,enabled); return enabled;
  }
  return new Set([...fields.keys()].filter(active));
}

export function collectValues(template: FormTemplate, raw: RawValues): { values: FormValues; errors: FieldError[] } {
  const active = activeFieldNames(template,raw);
  const values: FormValues = Object.create(null);
  const errors: FieldError[] = [];
  for (const field of allFields(template)) {
    if (!active.has(field.name)) continue;
    const error = (message: string) => errors.push({field:field.name,message:field.label + '：' + message});
    const value = raw[field.name];
    if (field.type === 'checkbox') {
      values[field.name] = value === true;
      if (field.required && value !== true) error('请勾选。');
      continue;
    }
    const text = typeof value === 'string' ? value.trim() : '';
    if (!text) { values[field.name] = null; if (field.required) error('请填写。'); continue; }
    if (field.maxLength !== undefined && [...text].length > field.maxLength) error(`最多 ${field.maxLength} 个字符。`);
    if (field.type === 'number' || field.type === 'decimal') {
      const number = Number(text);
      if (!Number.isFinite(number) || (field.type === 'decimal' && !/^-?\d+(?:\.\d+)?$/.test(text))) { error('请输入有效数字。'); continue; }
      if (field.integer && !Number.isSafeInteger(number)) error('请输入整数。');
      if (field.min !== undefined && number < field.min) error(`不能小于 ${field.min}。`);
      if (field.max !== undefined && number > field.max) error(`不能大于 ${field.max}。`);
      if (field.type === 'decimal' && (text.split('.')[1]?.length ?? 0) > (field.precision ?? 2)) error(`最多保留 ${field.precision ?? 2} 位小数。`);
      if (field.type === 'number' && field.step && Math.abs((number - (field.min ?? 0)) / field.step - Math.round((number - (field.min ?? 0)) / field.step)) > 1e-7) error(`请按 ${field.step} 的步长填写。`);
      values[field.name] = field.type === 'decimal' ? text : number;
    } else if (field.type === 'date') {
      const date = new Date(text+'T00:00:00Z');
      if (!/^\d{4}-\d{2}-\d{2}$/.test(text) || Number.isNaN(date.getTime()) || date.toISOString().slice(0,10) !== text) error('请输入有效日期。');
      values[field.name] = text;
    } else {
      if (field.type === 'select' && !field.allowCustom && !fieldOptions(template,field).some(option => option.value === text)) error('请选择列表中的选项。');
      if (field.type === 'tier' && !(field.tiers ?? []).some(tier => tier.value === text)) {
        const number = Number(text);
        if (!field.allowCustom) error('请选择列表中的选项。');
        else if (!/^\d+(?:\.\d+)?$/.test(text)) error('请输入有效数字。');
        else if (field.integer && !Number.isSafeInteger(number)) error('请输入整数。');
        else if (field.min !== undefined && number < field.min) error(`不能小于 ${field.min}。`);
        else if (field.max !== undefined && number > field.max) error(`不能大于 ${field.max}。`);
      }
      values[field.name] = text;
    }
  }
  for (const rule of template.rules) {
    const left = values[rule.left], right = values[rule.right];
    if (left === undefined || right === undefined || left === null || right === null || errors.some(error=>error.field === rule.left || error.field === rule.right)) continue;
    const valid = rule.type === 'lessThan' ? Number(left) < Number(right)
      : rule.type === 'dateBefore' ? String(left) < String(right)
      : Number(left) - Number(right) >= (rule.minimum ?? 0);
    if (!valid) errors.push({field:rule.right,message:rule.message});
  }
  return {values,errors};
}
