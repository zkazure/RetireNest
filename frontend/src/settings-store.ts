// 模型设置存在浏览器本地，只在发消息时随请求头带给后端；服务端不落盘。
export interface LlmSettings {
  apiKey: string;
  baseUrl: string;
  model: string;
  token: string;
}

const STORAGE_KEY = 'retirenest.settings';

const EMPTY: LlmSettings = { apiKey: '', baseUrl: '', model: '', token: '' };

export function loadSettings(): LlmSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...EMPTY };
    const parsed = JSON.parse(raw) as Partial<LlmSettings>;
    return {
      apiKey: typeof parsed.apiKey === 'string' ? parsed.apiKey : '',
      baseUrl: typeof parsed.baseUrl === 'string' ? parsed.baseUrl : '',
      model: typeof parsed.model === 'string' ? parsed.model : '',
      token: typeof parsed.token === 'string' ? parsed.token : '',
    };
  } catch {
    return { ...EMPTY };
  }
}

export function saveSettings(settings: LlmSettings): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

export function clearSettings(): void {
  localStorage.removeItem(STORAGE_KEY);
}

export function hasModelKey(settings: LlmSettings): boolean {
  return Boolean(settings.apiKey.trim() && settings.model.trim());
}
