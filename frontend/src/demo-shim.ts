// 静态体验层：只在 `VITE_DEMO=true` 的演示构建里生效。
//
// 两条路：优先把 `/api` 请求交给浏览器内的 Pyodide 引擎（同一份 Python，
// 表单可自由填写）；引擎起不来时退回预生成夹具，只读三个预置画像。
// 默认构建里 `installDemoShim()` 立刻返回，不参与任何逻辑。

import { EngineError, enginePage, engineReady, engineRun } from './pyodide-engine';

interface FixtureCommand {
  version: string;
  key: string;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
}

interface FixtureScenario {
  id: string;
  label: string;
  commands: Record<string, FixtureCommand>;
}

interface Fixtures {
  page: unknown;
  scenarios: FixtureScenario[];
}

type Mode = 'engine' | 'fallback';

const PAGE_ID = 'retirement.lifecycle';
const env = (import.meta as unknown as { env?: Record<string, string> }).env ?? {};
const ENABLED = env.VITE_DEMO === 'true';
const BASE = env.BASE_URL ?? '/';

const realFetch: typeof fetch | null =
  typeof window === 'undefined' ? null : window.fetch.bind(window);

let loading: Promise<Fixtures | null> | null = null;
let mode: Mode | null = null;
let deciding: Promise<Mode> | null = null;

const STATUS = {
  loading: '正在加载计算引擎（约 10 MB，只需一次）…',
  engine: '计算全部在你的浏览器里跑（Python 3.12 / WebAssembly），改完字段点「开始测算」即可。',
  fallback:
    '计算引擎没有加载成功，已退回预置画像：只能切换三个场景，不能改数字。填自己的数字请本地运行 make dev。',
} as const;

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function setStatus(text: string): void {
  const node = document.querySelector('.demo-banner .demo-status');
  if (node) node.textContent = text;
}

function loadFixtures(): Promise<Fixtures | null> {
  if (loading) return loading;
  if (!realFetch) return Promise.resolve(null);
  loading = realFetch(new URL(`${BASE}demo/fixtures.json`, location.href).toString())
    .then(async response => (response.ok ? ((await response.json()) as Fixtures) : null))
    .catch(() => null);
  return loading;
}

// 引擎起不来就退回夹具，只决定一次，避免中途来回切换。
function decide(): Promise<Mode> {
  if (mode) return Promise.resolve(mode);
  if (deciding) return deciding;
  deciding = engineReady()
    .then(() => {
      mode = 'engine';
      setStatus(STATUS.engine);
      return mode;
    })
    .catch(() => {
      mode = 'fallback';
      setStatus(STATUS.fallback);
      lockForm();
      return mode;
    });
  return deciding;
}

function canonical(value: Record<string, unknown>): string {
  const sorted: Record<string, unknown> = {};
  for (const key of Object.keys(value).sort()) sorted[key] = value[key];
  return JSON.stringify(sorted);
}

function parseBody(init?: RequestInit): { version: string; inputs: Record<string, unknown> } {
  const empty = { version: '', inputs: {} as Record<string, unknown> };
  if (!init?.body || typeof init.body !== 'string') return empty;
  try {
    const body = JSON.parse(init.body) as { version?: string; inputs?: Record<string, unknown> };
    return { version: body.version ?? '', inputs: body.inputs ?? {} };
  } catch {
    return empty;
  }
}

function matchFixture(
  data: Fixtures,
  commandId: string,
  inputs: Record<string, unknown>,
): FixtureCommand | null {
  const wanted = canonical(inputs);
  for (const scenario of data.scenarios) {
    const command = scenario.commands[commandId];
    if (command && command.key === wanted) return command;
  }
  return null;
}

async function answerPage(): Promise<Response> {
  if ((await decide()) === 'engine') return json(await enginePage());
  const data = await loadFixtures();
  if (!data) return json({ code: 'DEMO_UNAVAILABLE', message: '演示数据缺失。' }, 503);
  return json(data.page);
}

async function answerCommand(path: string, init?: RequestInit): Promise<Response> {
  const commandId = decodeURIComponent(path.slice('/api/commands/'.length));
  const body = parseBody(init);

  if ((await decide()) === 'engine') {
    try {
      const outputs = await engineRun(commandId, body.version, body.inputs);
      return json({ command_id: commandId, version: body.version, outputs });
    } catch (error) {
      if (error instanceof EngineError) {
        return json(
          { code: error.code, message: error.message, field_errors: error.fieldErrors },
          error.status || 400,
        );
      }
      return json(
        {
          code: 'CALCULATION_ERROR',
          message: `计算失败：${(error as Error).message}`,
          field_errors: [],
        },
        500,
      );
    }
  }

  const data = await loadFixtures();
  const command = data ? matchFixture(data, commandId, body.inputs) : null;
  if (!data || !command) {
    return json(
      {
        code: 'DEMO_STATIC',
        message: '静态演示只包含预置画像，换数字请本地运行完整版。',
        field_errors: [],
      },
      400,
    );
  }
  return json({ command_id: commandId, version: command.version, outputs: command.outputs });
}

async function answer(input: RequestInfo | URL, init?: RequestInit): Promise<Response | null> {
  const url =
    typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
  const path = new URL(url, location.href).pathname;

  if (path.startsWith('/api/agent/')) {
    return json(
      { code: 'AGENT_DISABLED', message: '演示版不含规划对话，请在本地运行完整版。' },
      503,
    );
  }
  if (!path.startsWith('/api/')) return null;
  if (path === `/api/pages/${PAGE_ID}`) return answerPage();
  if (path.startsWith('/api/commands/')) return answerCommand(path, init);
  return json({ code: 'DEMO_STATIC', message: '演示版不提供该端点。' }, 404);
}

function installFetch(): void {
  if (!realFetch) return;
  window.fetch = (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const answered = answer(input, init);
    return answered.then(response => response ?? realFetch(input, init));
  };
}

function styleSheet(): void {
  const style = document.createElement('style');
  style.textContent = `
    .demo-banner {
      display: flex; flex-wrap: wrap; align-items: baseline; gap: 10px;
      margin: 0 0 22px; padding: 12px 16px;
      border: 1px dashed #c9d6bd; border-radius: 10px; background: #f4f8ec;
      font-size: 12.5px; color: #4f6146; line-height: 1.6;
    }
    .demo-banner strong { color: #2c4a35; font-weight: 650; }
    .demo-banner .demo-hint { color: #7c8a72; }
    .demo-banner code {
      padding: 1px 6px; border-radius: 4px; background: #e6efd9;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px;
    }
    #form-host[inert] { opacity: .58; }
  `;
  document.head.append(style);
}

function addBanner(): void {
  const main = document.querySelector('main');
  if (!main || main.querySelector('.demo-banner')) return;
  const banner = document.createElement('div');
  banner.className = 'demo-banner';
  banner.innerHTML =
    '<strong>体验版</strong>' +
    `<span class="demo-status">${STATUS.loading}</span>` +
    '<span class="demo-hint">首次加载要几秒，之后有缓存。</span>';
  main.prepend(banner);
}

function removeChat(): boolean {
  const root = document.querySelector('.chat-root');
  root?.remove();
  return root !== null;
}

function tidyChrome(): void {
  document.querySelectorAll('.site-nav a').forEach(link => {
    const href = link.getAttribute('href') ?? '';
    if (href.endsWith('commands.html') || href.endsWith('settings.html')) link.remove();
  });
  // 聊天组件是独立模块、后于本文件挂载，删一次不够，轮询到它出现为止。
  if (removeChat()) return;
  let rounds = 0;
  const timer = window.setInterval(() => {
    if (removeChat() || (rounds += 1) > 40) window.clearInterval(timer);
  }, 50);
}

function lockForm(): void {
  const formHost = document.querySelector<HTMLElement>('#form-host');
  if (formHost && !formHost.hasAttribute('inert')) formHost.setAttribute('inert', '');
}

function run(form: HTMLFormElement): void {
  if (typeof form.requestSubmit === 'function') form.requestSubmit();
  else form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
}

function watchChips(): void {
  const bar = document.querySelector<HTMLElement>('#preset-host');
  if (!bar) return;
  bar.addEventListener(
    'click',
    event => {
      const chip = (event.target as HTMLElement | null)?.closest('.preset-chip');
      if (!chip || mode !== 'engine') return;
      const form = document.querySelector<HTMLFormElement>('#plan-form');
      window.setTimeout(() => {
        if (form) run(form);
      }, 0);
    },
    true,
  );
}

function firstRun(): void {
  const form = document.querySelector<HTMLFormElement>('#plan-form');
  const chip = document.querySelector<HTMLElement>('#preset-host .preset-chip');
  if (!form) return;
  chip?.click();
  window.setTimeout(() => run(form), 0);
}

function waitForChips(attempt = 0): void {
  if (document.querySelector('#preset-host .preset-chip')) {
    firstRun();
    return;
  }
  if (attempt > 100) return;
  window.setTimeout(() => waitForChips(attempt + 1), 50);
}

export function installDemoShim(): void {
  if (!ENABLED || typeof document === 'undefined') return;
  installFetch();
  styleSheet();
  const start = (): void => {
    tidyChrome();
    addBanner();
    watchChips();
    waitForChips();
    // 提前开跑，页面上的进度提示才有意义；失败会切到回退模式。
    void decide();
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
}
