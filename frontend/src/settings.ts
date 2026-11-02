// 设置页：填模型服务参数，保存在本地，可选地做一次真实连通性测试。
import './style.css';
import './settings.css';
import { clearSettings, hasModelKey, loadSettings, saveSettings, type LlmSettings } from './settings-store';

const byId = <T extends HTMLElement>(id: string) => document.querySelector<T>(`#${id}`)!;
const form = byId<HTMLFormElement>('settings-form');
const apiKey = byId<HTMLInputElement>('api-key');
const baseUrl = byId<HTMLInputElement>('base-url');
const model = byId<HTMLInputElement>('model');
const token = byId<HTMLInputElement>('token');
const showKey = byId<HTMLInputElement>('show-key');
const serverStatus = byId<HTMLElement>('server-status');
const errorBox = byId<HTMLElement>('settings-error');
const okBox = byId<HTMLElement>('settings-ok');

function read(): LlmSettings {
  return { apiKey: apiKey.value.trim(), baseUrl: baseUrl.value.trim(), model: model.value.trim(), token: token.value.trim() };
}

function fill(settings: LlmSettings): void {
  apiKey.value = settings.apiKey;
  baseUrl.value = settings.baseUrl;
  model.value = settings.model;
  token.value = settings.token;
}

function status(message: string, kind: 'error' | 'ok' | 'muted' = 'muted'): void {
  errorBox.hidden = kind !== 'error';
  okBox.hidden = kind !== 'ok';
  if (kind === 'error') errorBox.textContent = message;
  if (kind === 'ok') okBox.textContent = message;
}

function headersFor(settings: LlmSettings): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (settings.apiKey) {
    headers['X-LLM-Api-Key'] = settings.apiKey;
    if (settings.model) headers['X-LLM-Model'] = settings.model;
    if (settings.baseUrl) headers['X-LLM-Base-Url'] = settings.baseUrl;
  }
  if (settings.token) headers.Authorization = `Bearer ${settings.token}`;
  return headers;
}

async function loadServerStatus(): Promise<void> {
  try {
    const response = await fetch('/api/agent/config', { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(String(response.status));
    const body = await response.json() as { configured?: { enabled?: boolean; model?: string | null; missing?: string[] } };
    const configured = body.configured ?? {};
    serverStatus.textContent = configured.enabled
      ? `服务端已配置模型：${configured.model ?? '未知模型'}；不填密钥也可以直接对话。`
      : '服务端没有配置模型，需要在这里填写密钥与模型名。';
  } catch {
    serverStatus.textContent = '读不到服务端状态，确认后端已启动。';
  }
}

showKey.addEventListener('change', () => {
  apiKey.type = showKey.checked ? 'text' : 'password';
  token.type = showKey.checked ? 'text' : 'password';
});

form.addEventListener('submit', event => {
  event.preventDefault();
  const settings = read();
  if (!hasModelKey(settings)) {
    status('API Key 与模型名都要填。', 'error');
    return;
  }
  if (settings.baseUrl && !/^https?:\/\//.test(settings.baseUrl)) {
    status('Base URL 需要以 http:// 或 https:// 开头。', 'error');
    return;
  }
  saveSettings(settings);
  status('已保存到本浏览器。', 'ok');
});

byId<HTMLButtonElement>('test-button').addEventListener('click', async () => {
  const button = byId<HTMLButtonElement>('test-button');
  const settings = read();
  if (!hasModelKey(settings)) {
    status('API Key 与模型名都要填。', 'error');
    return;
  }
  button.disabled = true;
  button.textContent = '测试中…';
  status('正在发送一条测试消息，会产生一次真实调用。', 'muted');
  try {
    const response = await fetch('/api/agent/chat', {
      method: 'POST',
      headers: headersFor(settings),
      body: JSON.stringify({ message: '用一句话确认你能收到这条消息。' }),
    });
    const body = await response.json().catch(() => null) as { reply?: string; message?: string } | null;
    if (!response.ok) {
      status(body?.message ?? `连接失败（${response.status}）。`, 'error');
    } else {
      status(`连接正常，模型回复：${(body?.reply ?? '').slice(0, 80)}`, 'ok');
    }
  } catch {
    status('请求没有发出去，检查网络或后端地址。', 'error');
  } finally {
    button.disabled = false;
    button.textContent = '测试连接';
  }
});

byId<HTMLButtonElement>('clear-button').addEventListener('click', () => {
  clearSettings();
  fill({ apiKey: '', baseUrl: '', model: '', token: '' });
  status('已清除本地设置。', 'ok');
});

fill(loadSettings());
void loadServerStatus();
