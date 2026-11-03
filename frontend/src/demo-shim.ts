// 静态演示层：只在 `VITE_DEMO=true` 的演示构建里生效。
//
// GitHub Pages 上起不了 FastAPI，所以把页面清单与三条命令的输出预先算成夹具，
// 这里拦截 `/api` 请求直接喂数据，并把表单锁成只读、加上「静态演示」提示。
// 默认构建里 `installDemoShim()` 立刻返回，不参与任何逻辑。

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

const PAGE_ID = 'retirement.lifecycle';
const env = (import.meta as unknown as { env?: Record<string, string> }).env ?? {};
const ENABLED = env.VITE_DEMO === 'true';
const BASE = env.BASE_URL ?? '/';

const realFetch: typeof fetch | null =
  typeof window === 'undefined' ? null : window.fetch.bind(window);

let loading: Promise<Fixtures | null> | null = null;

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function loadFixtures(): Promise<Fixtures | null> {
  if (loading) return loading;
  if (!realFetch) return Promise.resolve(null);
  loading = realFetch(new URL(`${BASE}demo/fixtures.json`, location.href).toString())
    .then(async response => (response.ok ? ((await response.json()) as Fixtures) : null))
    .catch(() => null);
  return loading;
}

function canonical(value: Record<string, unknown>): string {
  const sorted: Record<string, unknown> = {};
  for (const key of Object.keys(value).sort()) sorted[key] = value[key];
  return JSON.stringify(sorted);
}

function parseInputs(init?: RequestInit): Record<string, unknown> {
  if (!init?.body || typeof init.body !== 'string') return {};
  try {
    const body = JSON.parse(init.body) as { inputs?: Record<string, unknown> };
    return body.inputs ?? {};
  } catch {
    return {};
  }
}

function matchScenario(
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

async function answer(input: RequestInfo | URL, init?: RequestInit): Promise<Response | null> {
  const url =
    typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
  const path = new URL(url, location.href).pathname;

  if (path.startsWith('/api/agent/')) {
    return json(
      { code: 'AGENT_DISABLED', message: '静态演示不含规划对话，请在本地运行完整版。' },
      503,
    );
  }
  if (!path.startsWith('/api/')) return null;

  const data = await loadFixtures();
  if (!data) return null;

  if (path === `/api/pages/${PAGE_ID}`) return json(data.page);
  if (path.startsWith('/api/commands/')) {
    const commandId = decodeURIComponent(path.slice('/api/commands/'.length));
    const command = matchScenario(data, commandId, parseInputs(init));
    if (!command) {
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
  return json({ code: 'DEMO_STATIC', message: '静态演示不提供该端点。' }, 404);
}

function installFetch(): void {
  if (!realFetch) return;
  window.fetch = (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const answerPromise = answer(input, init);
    return answerPromise.then(response => response ?? realFetch(input, init));
  };
}

function styleSheet(): void {
  const style = document.createElement('style');
  style.textContent = `
    .demo-banner {
      display: flex; flex-wrap: wrap; align-items: baseline; gap: 10px;
      margin: 0 0 22px; padding: 12px 16px;
      border: 1px dashed #d9c98f; border-radius: 10px; background: #fdf8e8;
      font-size: 12.5px; color: #7a6a3a; line-height: 1.6;
    }
    .demo-banner strong { color: #5f5222; font-weight: 650; }
    .demo-banner code {
      padding: 1px 6px; border-radius: 4px; background: #f3ecd3;
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
    '<strong>静态演示</strong>' +
    '<span>这里只有三份预先算好的人生：切换上方画像看结果，数字是真实引擎算的，但页面不重算。</span>' +
    '<span>填自己的数字请本地运行 <code>make dev</code>。</span>';
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

function noteStatic(): void {
  const note = document.querySelector<HTMLElement>('#preset-host .preset-note');
  if (note) note.textContent = '静态演示：只能切换预置画像，表单不参与重算';
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
      if (!chip) return;
      const form = document.querySelector<HTMLFormElement>('#plan-form');
      window.setTimeout(() => {
        noteStatic();
        if (form) run(form);
      }, 0);
    },
    true,
  );
}

function firstRun(): void {
  const form = document.querySelector<HTMLFormElement>('#plan-form');
  const chip = document.querySelector<HTMLElement>('#preset-host .preset-chip');
  if (!form || !chip) return;
  chip.click();
  window.setTimeout(() => {
    noteStatic();
    lockForm();
    run(form);
  }, 0);
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
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
}
