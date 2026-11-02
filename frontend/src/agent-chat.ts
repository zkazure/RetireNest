import './agent-chat.css';
import { SseParser, type SseEvent } from './agent-stream';

interface ToolError {
  code: string;
  message: string;
  field_errors?: { field: string; message: string }[];
}

interface ToolCallRecord {
  tool_call_id?: string;
  tool_name: string;
  command_id: string | null;
  version: string | null;
  inputs: unknown;
  outputs: unknown;
  ok: boolean;
  error: ToolError | null;
}

interface AgentReply {
  session_id: string;
  reply: string;
  tool_calls: ToolCallRecord[];
  warnings: string[];
  model: string;
}

interface StreamPayload {
  type?: string;
  session_id?: string;
  tool_call_id?: string;
  tool_name?: string;
  command_id?: string | null;
  version?: string | null;
  inputs?: unknown;
  outputs?: unknown;
  ok?: boolean;
  error?: ToolError | null;
  reply?: string;
  tool_calls?: ToolCallRecord[];
  warnings?: string[];
  model?: string;
  code?: string;
  message?: string;
}

class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

class StreamUnavailable extends Error {}

const root = document.querySelector<HTMLElement>('#agent-app');
if (!root) throw new Error('缺少 #agent-app');
root.innerHTML = `
  <header class="agent-header">
    <div>
      <p class="agent-kicker">RetireNest</p>
      <h1>规划对话</h1>
      <p class="agent-subtitle">把“我能退休吗”拆成储蓄、风险、寿命和提取率，逐个用确定性工具算给你看。</p>
    </div>
    <nav class="agent-nav" aria-label="页面导航">
      <a href="/">测算主页</a>
      <a href="/commands.html">命令浏览器</a>
    </nav>
  </header>

  <main class="agent-main">
    <section class="agent-panel" aria-label="退休规划对话">
      <div class="agent-toolbar">
        <label class="agent-token">
          <span>访问令牌</span>
          <input id="agent-token" type="password" autocomplete="off" spellcheck="false" placeholder="服务端启用 Bearer 时填写" />
        </label>
        <button id="agent-reset" type="button" class="agent-secondary">新会话</button>
      </div>

      <p id="agent-status" class="agent-status" role="status">未连接；发送第一条消息开始。</p>
      <div id="agent-messages" class="agent-messages" aria-live="polite"></div>
      <div id="agent-warnings" class="agent-warnings" hidden></div>

      <form id="agent-composer" class="agent-composer">
        <label class="agent-label" for="agent-message">你的问题</label>
        <textarea id="agent-message" rows="2" maxlength="4000" placeholder="例如：我 30 岁，月入 2 万，月支出 1.2 万，资产 50 万，想 55 岁退休。"></textarea>
        <div class="agent-composer-actions">
          <p class="agent-disclaimer">结果是基于假设的估算，不构成个性化投资建议。工具轨迹可展开核对数字。</p>
          <button id="agent-send" type="submit">发送</button>
        </div>
      </form>
    </section>
  </main>
`;

function byId<T extends HTMLElement>(id: string): T {
  const element = document.getElementById(id);
  if (!element) throw new Error(`缺少元素 #${id}`);
  return element as T;
}

const tokenInput = byId<HTMLInputElement>('agent-token');
const resetButton = byId<HTMLButtonElement>('agent-reset');
const statusEl = byId<HTMLParagraphElement>('agent-status');
const messagesEl = byId<HTMLDivElement>('agent-messages');
const warningsEl = byId<HTMLDivElement>('agent-warnings');
const form = byId<HTMLFormElement>('agent-composer');
const messageInput = byId<HTMLTextAreaElement>('agent-message');
const sendButton = byId<HTMLButtonElement>('agent-send');

let sessionId: string | null = null;
let busy = false;
let token = '';
let toolSequence = 0;
let toolCards = new Map<string, HTMLDetailsElement>();
let activeAssistantText: HTMLParagraphElement | null = null;
let activeTools: HTMLDivElement | null = null;

function setStatus(text: string, kind: 'muted' | 'info' | 'error' = 'muted'): void {
  statusEl.textContent = text;
  statusEl.className = `agent-status ${kind}`;
}

function setBusy(value: boolean): void {
  busy = value;
  sendButton.disabled = value;
  sendButton.textContent = value ? '思考中…' : '发送';
  resetButton.disabled = value;
}

function startTurn(): void {
  activeAssistantText = null;
  activeTools = null;
  toolCards = new Map();
  toolSequence = 0;
  warningsEl.hidden = true;
  warningsEl.textContent = '';
}

function scrollToBottom(): void {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function appendUserMessage(text: string): void {
  const article = document.createElement('article');
  article.className = 'message user';
  const paragraph = document.createElement('p');
  paragraph.className = 'message-text';
  paragraph.textContent = text;
  article.append(paragraph);
  messagesEl.append(article);
  scrollToBottom();
}

function ensureAssistant(): void {
  if (activeAssistantText) return;
  const article = document.createElement('article');
  article.className = 'message assistant';
  const text = document.createElement('p');
  text.className = 'message-text';
  const tools = document.createElement('div');
  tools.className = 'tool-list';
  article.append(text, tools);
  messagesEl.append(article);
  activeAssistantText = text;
  activeTools = tools;
  scrollToBottom();
}

function ensureToolCard(payload: StreamPayload): HTMLDetailsElement {
  ensureAssistant();
  const id = payload.tool_call_id || `tool-${toolSequence++}`;
  const existing = toolCards.get(id);
  if (existing) return existing;

  const name = payload.tool_name || '未知工具';
  const command = payload.command_id || '';
  const details = document.createElement('details');
  details.className = 'tool pending';
  details.open = false;
  const summary = document.createElement('summary');
  summary.textContent = `工具：${name}${command ? `（${command}）` : ''} · 执行中`;
  const pre = document.createElement('pre');
  pre.className = 'tool-json';
  pre.textContent = '执行中…';
  details.append(summary, pre);
  activeTools?.append(details);
  toolCards.set(id, details);
  scrollToBottom();
  return details;
}

function renderToolResult(payload: StreamPayload | ToolCallRecord): void {
  const details = ensureToolCard(payload);
  const name = payload.tool_name || '未知工具';
  const command = payload.command_id || '';
  const ok = payload.ok === true;
  details.classList.remove('pending', 'ok', 'fail');
  details.classList.add(ok ? 'ok' : 'fail');
  const summary = details.querySelector('summary');
  if (summary) {
    summary.textContent = `工具：${name}${command ? `（${command}）` : ''} · ${ok ? '成功' : '失败'}`;
  }
  const pre = details.querySelector('pre');
  if (pre) {
    pre.textContent = JSON.stringify(
      {
        command_id: payload.command_id ?? null,
        inputs: payload.inputs ?? null,
        outputs: payload.outputs ?? null,
        error: payload.error ?? null,
      },
      null,
      2,
    );
  }
  scrollToBottom();
}

function renderWarnings(warnings: string[]): void {
  warningsEl.textContent = '';
  if (warnings.length === 0) {
    warningsEl.hidden = true;
    return;
  }
  warningsEl.hidden = false;
  const title = document.createElement('p');
  title.className = 'agent-warnings-title';
  title.textContent = '需要注意';
  warningsEl.append(title);
  for (const warning of warnings) {
    const item = document.createElement('p');
    item.textContent = warning;
    warningsEl.append(item);
  }
}

function renderReply(reply: AgentReply): void {
  if (reply.session_id) sessionId = reply.session_id;
  ensureAssistant();
  if (activeAssistantText) activeAssistantText.textContent = reply.reply;
  for (const record of reply.tool_calls) renderToolResult(record);
  renderWarnings(reply.warnings);
  setStatus(reply.model ? `模型：${reply.model}` : '完成', 'muted');
  scrollToBottom();
}

function showError(code: string, message: string): void {
  const hints: Record<string, string> = {
    AGENT_DISABLED:
      '服务端未配置模型：设置 RETIRENEST_LLM_API_KEY 与 RETIRENEST_LLM_MODEL，或用 RETIRENEST_AGENT_FAKE=1 启动演示。',
    AGENT_UNAUTHORIZED: '请在上方填写访问令牌；令牌由服务端 RETIRENEST_AGENT_TOKEN 或 RETIRENEST_AGENT_TOKENS 配置。',
    AGENT_SESSION_NOT_FOUND: '会话不存在或不属于当前令牌，已开始新会话。',
    AGENT_UPSTREAM_ERROR: '模型服务暂时不可用，请稍后重试。',
  };
  if (code === 'AGENT_SESSION_NOT_FOUND') sessionId = null;
  setStatus(`${message}${hints[code] ? ` ${hints[code]}` : ''}`, 'error');
}

function handleError(error: unknown): void {
  if (error instanceof ApiError) {
    showError(error.code, error.message);
    return;
  }
  showError('NETWORK_ERROR', error instanceof Error ? error.message : '网络请求失败。');
}

function requestHeaders(): Record<string, string> {
  const headers: Record<string, string> = { 'content-type': 'application/json' };
  if (token) headers.authorization = `Bearer ${token}`;
  return headers;
}

function requestBody(message: string): Record<string, unknown> {
  return sessionId ? { session_id: sessionId, message } : { message };
}

async function throwHttpError(response: Response): Promise<never> {
  let code = 'HTTP_ERROR';
  let message = `请求失败（${response.status}）`;
  try {
    const body = (await response.json()) as { code?: unknown; message?: unknown };
    if (typeof body.code === 'string') code = body.code;
    if (typeof body.message === 'string') message = body.message;
  } catch {
    // 非 JSON 错误体，保留默认文案。
  }
  throw new ApiError(response.status, code, message);
}

function handleEvent(event: SseEvent): void {
  let payload: StreamPayload;
  try {
    payload = JSON.parse(event.data) as StreamPayload;
  } catch {
    return;
  }
  const type = payload.type || event.event;
  switch (type) {
    case 'session':
      if (payload.session_id) sessionId = payload.session_id;
      setStatus('已连接，正在思考…', 'info');
      break;
    case 'tool_call':
      ensureAssistant();
      ensureToolCard(payload);
      setStatus('正在调用工具…', 'info');
      break;
    case 'tool_result':
      renderToolResult(payload);
      break;
    case 'reply':
      renderReply({
        session_id: payload.session_id ?? sessionId ?? '',
        reply: payload.reply ?? '',
        tool_calls: payload.tool_calls ?? [],
        warnings: payload.warnings ?? [],
        model: payload.model ?? '',
      });
      break;
    case 'done':
      setBusy(false);
      setStatus(payload.model ? `完成 · ${payload.model}` : '完成', 'muted');
      break;
    case 'error':
      showError(payload.code ?? 'AGENT_ERROR', payload.message ?? '请求失败。');
      setBusy(false);
      break;
    default:
      break;
  }
}

async function streamChat(message: string): Promise<void> {
  const response = await fetch('/api/agent/chat/stream', {
    method: 'POST',
    headers: requestHeaders(),
    body: JSON.stringify(requestBody(message)),
  });
  if (!response.ok) {
    if (response.status === 404 || response.status === 405) throw new StreamUnavailable();
    await throwHttpError(response);
  }
  const contentType = response.headers.get('content-type') ?? '';
  const body = response.body;
  if (!body || !contentType.includes('text/event-stream')) {
    throw new StreamUnavailable();
  }

  const reader = body.getReader();
  const decoder = new TextDecoder();
  const parser = new SseParser();
  let sawEvent = false;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    for (const event of parser.push(decoder.decode(value, { stream: true }))) {
      sawEvent = true;
      handleEvent(event);
    }
  }
  if (!sawEvent) throw new StreamUnavailable();
}

async function nonStreamingChat(message: string): Promise<void> {
  const response = await fetch('/api/agent/chat', {
    method: 'POST',
    headers: requestHeaders(),
    body: JSON.stringify(requestBody(message)),
  });
  if (!response.ok) await throwHttpError(response);
  const reply = (await response.json()) as AgentReply;
  renderReply(reply);
}

async function sendMessage(): Promise<void> {
  if (busy) return;
  const message = messageInput.value.trim();
  if (!message) {
    messageInput.focus();
    return;
  }
  token = tokenInput.value.trim();
  startTurn();
  appendUserMessage(message);
  messageInput.value = '';
  setBusy(true);
  setStatus('正在思考…', 'info');

  try {
    await streamChat(message);
  } catch (error) {
    if (error instanceof StreamUnavailable) {
      try {
        await nonStreamingChat(message);
      } catch (fallbackError) {
        handleError(fallbackError);
      }
    } else {
      handleError(error);
    }
  } finally {
    setBusy(false);
  }
}

async function resetSession(): Promise<void> {
  token = tokenInput.value.trim();
  const current = sessionId;
  sessionId = null;
  activeAssistantText = null;
  activeTools = null;
  toolCards = new Map();
  messagesEl.textContent = '';
  warningsEl.hidden = true;
  warningsEl.textContent = '';
  setStatus('新会话', 'muted');
  if (current) {
    try {
      await fetch(`/api/agent/sessions/${encodeURIComponent(current)}`, {
        method: 'DELETE',
        headers: requestHeaders(),
      });
    } catch {
      // 本地已经清空，服务端会话会按 TTL 过期。
    }
  }
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  void sendMessage();
});

resetButton.addEventListener('click', () => {
  void resetSession();
});

messageInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});
