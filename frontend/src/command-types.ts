export type CommandInputType =
  | 'integer'
  | 'number'
  | 'decimal'
  | 'date'
  | 'enum'
  | 'boolean'
  | 'text';

export interface CommandInputSpec {
  name: string;
  question: string;
  type: CommandInputType;
  unit?: string | null;
  required?: boolean;
  default?: unknown;
  options?: string[];
  constraints?: Record<string, unknown>;
  semantic?: string | null;
  required_when?: { field: string; equals: unknown } | null;
  /** 给 LLM 看的参数说明；命令浏览器不展示。 */
  description?: string | null;
}

export interface CommandOutputSpec {
  name: string;
  question: string;
  type: string;
  unit?: string | null;
  semantic?: string | null;
  precision?: number | null;
  time_axis?: Record<string, unknown> | null;
  /** false 表示实现细节（数组下标、回显输入），命令浏览器不展示。 */
  visible?: boolean;
  description?: string | null;
}

export interface CommandExample {
  name?: string;
  inputs: Record<string, unknown>;
}

export interface CommandManifest {
  id: string;
  version: string;
  question: string;
  description?: string;
  inputs: CommandInputSpec[];
  outputs: CommandOutputSpec[];
  deterministic?: boolean;
  as_of?: string | null;
  examples?: CommandExample[];
  /** 工具选择指引；命令浏览器不展示，后续 Agent 使用。 */
  when_to_use?: string;
  when_not_to_use?: string;
}

export interface CommandListResponse {
  protocol_version: string;
  commands: CommandManifest[];
}

export interface CommandExecutionResponse {
  command_id: string;
  version: string;
  outputs: Record<string, unknown>;
  meta?: {
    deterministic?: boolean;
    as_of?: string | null;
  };
}

export interface CommandFieldError {
  field: string;
  message: string;
}

export interface CommandErrorBody {
  code: string;
  message: string;
  field_errors?: CommandFieldError[];
}
