import type {
  CommandErrorBody,
  CommandExecutionResponse,
  CommandFieldError,
  CommandListResponse,
  CommandManifest,
} from './command-types';

const TIMEOUT_MS = 20_000;

export class CommandApiError extends Error {
  readonly code: string;
  readonly fieldErrors: CommandFieldError[];
  readonly status: number;

  constructor(code: string, message: string, fieldErrors: CommandFieldError[] = [], status = 0) {
    super(message);
    this.name = 'CommandApiError';
    this.code = code;
    this.fieldErrors = fieldErrors;
    this.status = status;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isManifest(value: unknown): value is CommandManifest {
  if (!isRecord(value)) return false;
  return (
    typeof value.id === 'string' &&
    typeof value.version === 'string' &&
    typeof value.question === 'string' &&
    Array.isArray(value.inputs) &&
    Array.isArray(value.outputs)
  );
}

function isErrorBody(value: unknown): value is CommandErrorBody {
  if (!isRecord(value) || typeof value.code !== 'string' || typeof value.message !== 'string') {
    return false;
  }
  if (value.field_errors === undefined) return true;
  return (
    Array.isArray(value.field_errors) &&
    value.field_errors.every(
      item =>
        isRecord(item) && typeof item.field === 'string' && typeof item.message === 'string',
    )
  );
}

function isExecutionResponse(value: unknown): value is CommandExecutionResponse {
  return (
    isRecord(value) &&
    typeof value.command_id === 'string' &&
    typeof value.version === 'string' &&
    isRecord(value.outputs)
  );
}

async function fetchJson(url: string, init?: RequestInit): Promise<unknown> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(url, { ...init, signal: controller.signal });
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      if (isErrorBody(payload)) {
        throw new CommandApiError(
          payload.code,
          payload.message,
          payload.field_errors ?? [],
          response.status,
        );
      }
      throw new CommandApiError(
        'HTTP_ERROR',
        `命令服务返回 ${response.status}。`,
        [],
        response.status,
      );
    }
    return payload;
  } catch (error) {
    if (error instanceof CommandApiError) throw error;
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new CommandApiError('TIMEOUT', '命令服务响应超时，请重试。');
    }
    throw new CommandApiError('NETWORK_ERROR', '无法连接命令服务，请确认后端已启动。');
  } finally {
    clearTimeout(timer);
  }
}

export async function fetchCommands(): Promise<CommandListResponse> {
  const payload = await fetchJson('/api/commands');
  if (
    !isRecord(payload) ||
    typeof payload.protocol_version !== 'string' ||
    !Array.isArray(payload.commands) ||
    !payload.commands.every(isManifest)
  ) {
    throw new CommandApiError('INVALID_RESPONSE', '命令清单格式不正确。');
  }
  return payload as unknown as CommandListResponse;
}

export async function executeCommand(
  commandId: string,
  version: string,
  inputs: Record<string, unknown>,
): Promise<CommandExecutionResponse> {
  const payload = await fetchJson(`/api/commands/${encodeURIComponent(commandId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ version, inputs }),
  });
  if (!isExecutionResponse(payload)) {
    throw new CommandApiError('INVALID_RESPONSE', '命令返回格式不正确。');
  }
  return payload;
}
