import { CommandApiError, executeCommand } from './command-client';
import type { FieldError, FormValues } from './form-types';
import type { PageExecutionSpec, PageManifest } from './page-types';
import { buildInputs, enabledExecutions } from './page-values';

export interface PageExecutionResult {
  execution: PageExecutionSpec;
  outputs: Record<string, unknown>;
}

export class PageRunError extends Error {
  readonly fieldErrors: FieldError[];

  constructor(message: string, fieldErrors: FieldError[] = []) {
    super(message);
    this.name = 'PageRunError';
    this.fieldErrors = fieldErrors;
  }
}

// 按页面清单顺序逐个执行命令；字段错误合并，非字段错误立即中止。
export async function runPage(
  page: PageManifest,
  values: FormValues,
): Promise<PageExecutionResult[]> {
  const results: PageExecutionResult[] = [];
  const fieldErrors = new Map<string, string>();
  let message = '';

  for (const execution of enabledExecutions(page, values)) {
    try {
      const response = await executeCommand(
        execution.command,
        execution.version,
        buildInputs(values, execution),
      );
      results.push({ execution, outputs: response.outputs });
    } catch (error) {
      if (!(error instanceof CommandApiError)) throw error;
      for (const item of error.fieldErrors) {
        if (!fieldErrors.has(item.field)) fieldErrors.set(item.field, item.message);
      }
      if (error.fieldErrors.length === 0) {
        throw new PageRunError(error.message, [...fieldErrors].map(toFieldError));
      }
      if (!message) message = error.message;
    }
  }

  if (fieldErrors.size > 0) {
    throw new PageRunError(
      message || '请检查输入。',
      [...fieldErrors].map(toFieldError),
    );
  }
  return results;
}

function toFieldError([field, message]: [string, string]): FieldError {
  return { field, message };
}
