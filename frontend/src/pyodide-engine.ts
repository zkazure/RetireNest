// 浏览器内的计算引擎：Pyodide 把 CPython 编译成 WebAssembly，直接跑仓库里那份 Python。
//
// 为什么不移植成 JS：口径只能有一份。移植等于把计算逻辑抄一遍，两次改动之后
// 页面上的数字就和 README 分叉了。这里用同一份源码，代价只是首次要下约 10 MB 运行时。

export interface EngineFailure {
  code: string;
  message: string;
  status: number;
  fieldErrors: { field: string; message: string }[];
}

export class EngineError extends Error {
  readonly code: string;
  readonly status: number;
  readonly fieldErrors: { field: string; message: string }[];

  constructor(failure: EngineFailure) {
    super(failure.message);
    this.name = 'EngineError';
    this.code = failure.code;
    this.status = failure.status;
    this.fieldErrors = failure.fieldErrors;
  }
}

interface Bridge {
  page_json(): string;
  run_json(commandId: string, version: string, inputsJson: string): string;
}

interface PyodideApi {
  unpackArchive(
    buffer: ArrayBuffer,
    format: string,
    options?: { extractDir?: string },
  ): Promise<void>;
  runPython(code: string): unknown;
  pyimport(name: string): Bridge;
}

const PYODIDE_VERSION = '0.27.7';
const INDEX_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;
const ARCHIVE = 'demo/py/engine.zip';

let bridge: Bridge | null = null;
let starting: Promise<Bridge> | null = null;

function baseUrl(): string {
  const env = (import.meta as unknown as { env?: Record<string, string> }).env ?? {};
  return env.BASE_URL ?? '/';
}

async function start(): Promise<Bridge> {
  if (bridge) return bridge;
  const moduleUrl = `${INDEX_URL}pyodide.mjs`;
  const mod = (await import(/* @vite-ignore */ moduleUrl)) as unknown as {
    loadPyodide: (options: { indexURL: string }) => Promise<PyodideApi>;
  };
  const pyodide = await mod.loadPyodide({ indexURL: INDEX_URL });

  const response = await fetch(new URL(`${baseUrl()}${ARCHIVE}`, location.href).toString());
  if (!response.ok) throw new Error(`引擎包下载失败：${response.status}`);
  const archive = await response.arrayBuffer();

  await pyodide.unpackArchive(archive, 'zip', { extractDir: '/engine' });
  pyodide.runPython("import sys\nif '/engine' not in sys.path: sys.path.insert(0, '/engine')");
  bridge = pyodide.pyimport('demo_bridge');
  return bridge;
}

export function engineReady(): Promise<Bridge> {
  if (!starting) {
    starting = start().catch(error => {
      starting = null;
      throw error instanceof Error ? error : new Error(String(error));
    });
  }
  return starting;
}

export async function enginePage(): Promise<unknown> {
  const ready = await engineReady();
  return JSON.parse(ready.page_json());
}

export async function engineRun(
  commandId: string,
  version: string,
  inputs: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const ready = await engineReady();
  const raw = ready.run_json(commandId, version, JSON.stringify(inputs));
  const parsed = JSON.parse(raw) as {
    outputs?: Record<string, unknown>;
    error?: { code: string; message: string; status: number; field_errors?: unknown };
  };
  if (parsed.error) {
    const errors = Array.isArray(parsed.error.field_errors)
      ? (parsed.error.field_errors as { field: string; message: string }[])
      : [];
    throw new EngineError({
      code: parsed.error.code,
      message: parsed.error.message,
      status: parsed.error.status ?? 500,
      fieldErrors: errors,
    });
  }
  return parsed.outputs ?? {};
}
