import type { FormValues } from './form-types';
import type { PageExecutionSpec, PageManifest } from './page-types';

// 只提交页面清单声明的映射；开关关闭的执行整条跳过。
export function enabledExecutions(
  page: PageManifest,
  values: FormValues,
): PageExecutionSpec[] {
  return page.executions.filter(
    execution => !execution.toggle || values[execution.toggle] === true,
  );
}

export function buildInputs(
  values: FormValues,
  execution: PageExecutionSpec,
): Record<string, unknown> {
  const inputs: Record<string, unknown> = {};
  for (const [argument, field] of Object.entries(execution.inputs)) {
    const value = values[field];
    if (value === undefined || value === null) continue;
    inputs[argument] = value;
  }
  return inputs;
}
