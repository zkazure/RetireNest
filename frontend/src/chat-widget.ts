// 悬浮对话框：全站右下角入口，点开是一个不离开当前页面的对话面板。
import './chat-widget.css';
import { SseParser, type SseEvent } from './agent-stream';
import { hasModelKey, loadSettings } from './settings-store';

interface StreamPayload {
  type?: string;
  message?: string;
  text?: string;
  warnings?: string[];
  command_id?: string;
  code?: string;
  [key: string]: unknown;
}

const STORAGE_KEY = 'retirenest.chat.open';
const WELCOME = '问我「丁克和养娃一孩差多少」「提前十年退休行不行」都行。';

function el<K extends keyof HTMLElementTagNameMap>(tag: K, className = '', text = ''): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
}

function mount(): void {
  const root = el('div', 'chat-root');
  root.innerHTML = `
    <button class="chat-bubble" type="button" aria-label="打开规划对话" title="规划对话">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M21 12a8 8 0 0 1-8 8H7l-4 3v-5.5A8 8 0 0 1 3 12a8 8 0 0 1 8-8h2a8 8 0 0 1 8 8Z"/>
      </svg>
    </button>
    <section class="chat-panel" hidden aria-label="规划对话">
      <header class="chat-head">
        <div><strong>规划对话</strong><span>随时问，不离开当前页面</span></div>
        <button class="chat-close" type="button" aria-label="关闭对话">×</button>
      </header>
      <div class="chat-log" role="log" aria-live="polite"></div>
      <form class="chat-form">
        <textarea class="chat-input" rows="2" placeholder="说说你的情况或想问的问题…" aria-label="消息"></textarea>
        <button class="chat-send" type="submit">发送</button>
      </form>
      <div class="chat-foot">
        <span class="chat-status" aria-live="polite">未配置模型</span>
        <a class="chat-settings" href="/settings.html">模型设置</a>
      </div>
    </section>`;
  document.body.append(root);

  const bubble = root.querySelector<HTMLButtonElement>('.chat-bubble')!;
  const panel = root.querySelector<HTMLElement>('.chat-panel')!;
  const log = root.querySelector<HTMLElement>('.chat-log')!;
  const form = root.querySelector<HTMLFormElement>('.chat-form')!;
  const input = root.querySelector<HTMLTextAreaElement>('.chat-input')!;
  const send = root.querySelector<HTMLButtonElement>('.chat-send')!;
  const status = root.querySelector<HTMLElement>('.chat-status')!;

  let busy = false;
  let started = false;

  const setStatus = (text: string, kind: 'muted' | 'error' | 'info' = 'muted') => {
    status.textContent = text;
    status.dataset.kind = kind;
  };

  const tone = (text: string, kind: 'user' | 'assistant' | 'error' | 'note') => {
    const node = el('div', `chat-msg ${kind}`, text);
    log.append(node);
    log.scrollTop = log.scrollHeight;
    return node;
  };

  const open = (): void => {
    panel.hidden = false;
    bubble.setAttribute('aria-expanded', 'true');
    if (!started) {
      started = true;
      tone(WELCOME, 'note');
    }
    input.focus();
    sessionStorage.setItem(STORAGE_KEY, '1');
  };
  const close = (): void => {
    panel.hidden = true;
    bubble.setAttribute('aria-expanded', 'false');
    bubble.focus();
    sessionStorage.removeItem(STORAGE_KEY);
  };

  bubble.addEventListener('click', () => (panel.hidden ? open() : close()));
  root.querySelector('.chat-close')!.addEventListener('click', close);
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !panel.hidden) close();
  });
  // Enter 直接发送，Shift+Enter 换行；输入法组合中的回车不发送。
  input.addEventListener('keydown', event => {
    if (event.key !== 'Enter' || event.shiftKey) return;
    if (event.isComposing || event.keyCode === 229) return;
    event.preventDefault();
    form.requestSubmit();
  });
  if (sessionStorage.getItem(STORAGE_KEY) === '1') open();

  const handle = (event: SseEvent) => {
    let payload: StreamPayload = {};
    try {
      payload = JSON.parse(event.data) as StreamPayload;
    } catch {
      payload = { text: event.data };
    }
    if (event.event === 'session') return;
    if (event.event === 'tool_call') {
      tone(`正在调用 ${payload.command_id ?? '工具'}…`, 'note');
      return;
    }
    if (event.event === 'tool_result') return;
    if (event.event === 'reply') {
      tone(payload.text ?? '', 'assistant');
      for (const warning of payload.warnings ?? []) tone(warning, 'note');
      return;
    }
    if (event.event === 'error') {
      tone(payload.message ?? '对话失败，请稍后再试。', 'error');
      return;
    }
    if (event.event === 'done') {
      setBusy(false);
    }
  };

  const setBusy = (value: boolean) => {
    busy = value;
    send.disabled = value;
    input.disabled = value;
    setStatus(value ? '正在思考…' : '就绪', value ? 'info' : 'muted');
  };

  form.addEventListener('submit', async event => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text || busy) return;
    tone(text, 'user');
    input.value = '';
    setBusy(true);
    if (!hasModelKey(loadSettings())) setStatus('未配置模型，去「模型设置」填写', 'error');
    try {
      const settings = loadSettings();
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (settings.apiKey) {
        headers['X-LLM-Api-Key'] = settings.apiKey;
        if (settings.model) headers['X-LLM-Model'] = settings.model;
        if (settings.baseUrl) headers['X-LLM-Base-Url'] = settings.baseUrl;
      }
      if (settings.token) headers.Authorization = `Bearer ${settings.token}`;
      const response = await fetch('/api/agent/chat/stream', {
        method: 'POST',
        headers,
        body: JSON.stringify({ message: text }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { message?: string } | null;
        if (response.status === 503) {
          tone('还没有配置模型。点右下角的「模型设置」填好 API Key 与模型名即可，不用重启服务。', 'error');
        } else {
          tone(body?.message ?? `对话失败（${response.status}）。`, 'error');
        }
        setBusy(false);
        return;
      }
      const reader = response.body?.getReader();
      if (!reader) throw new Error('no stream');
      const parser = new SseParser();
      const decoder = new TextDecoder();
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        for (const item of parser.push(decoder.decode(value, { stream: true }))) handle(item);
      }
    } catch {
      tone('连接中断，请稍后重试。', 'error');
      setBusy(false);
    } finally {
      if (busy) setBusy(false);
      input.focus();
    }
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mount, { once: true });
} else {
  mount();
}
