import './command-browser.css';
import { CommandApiError } from './command-client';
import { buildOutputRows } from './command-output';
import { loadCommands, runCommand } from './command-registry';
import type {
  CommandExecutionResponse,
  CommandInputSpec,
  CommandManifest,
} from './command-types';

const app = document.querySelector<HTMLDivElement>('#command-app')!;

const escapeHtml = (value: unknown) =>
  String(value).replace(
    /[&<>"']/g,
    char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]!,
  );

let commands: CommandManifest[] = [];
let selectedId: string | null = null;

app.innerHTML = `
  <header class="cmd-header">
    <a class="cmd-brand" href="/">退有所算<small>RETIRENEST</small></a>
    <div class="cmd-heading">
      <p class="cmd-eyebrow">COMMAND EXPLORER</p>
      <h1>命令浏览器</h1>
      <p class="cmd-subtitle">按后端 manifest 生成输入表单；每个命令只返回领域输出，页面如何组合由前端决定。</p>
    </div>
  </header>
  <main class="cmd-layout">
    <aside class="cmd-sidebar">
      <p class="cmd-sidebar-title">已注册命令</p>
      <div id="command-list" class="cmd-list"><p class="cmd-muted">正在加载…</p></div>
    </aside>
    <section class="cmd-detail" id="command-detail">
      <p class="cmd-muted">正在读取命令清单…</p>
    </section>
  </main>
`;

async function init() {
  try {
    commands = await loadCommands();
    renderList();
    if (commands[0]) selectCommand(commands[0]);
    else detailError('前端注册表中没有可用命令。');
  } catch (error) {
    const message =
      error instanceof CommandApiError ? error.message : '无法读取命令清单，请确认后端已启动。';
    detailError(message);
  }
}

function renderList() {
  const list = document.querySelector<HTMLDivElement>('#command-list')!;
  list.innerHTML = commands
    .map(
      command => `
        <button type="button" class="cmd-list-item" data-command="${escapeHtml(command.id)}">
          <span class="cmd-list-id">${escapeHtml(command.id)}</span>
          <span class="cmd-list-question">${escapeHtml(command.question)}</span>
          <span class="cmd-list-meta">v${escapeHtml(command.version)}${command.as_of ? ` · ${escapeHtml(command.as_of)}` : ''}</span>
        </button>`,
    )
    .join('');
  list.querySelectorAll<HTMLButtonElement>('[data-command]').forEach(button => {
    button.addEventListener('click', () => {
      const command = commands.find(item => item.id === button.dataset.command);
      if (command) selectCommand(command);
    });
  });
  markSelected();
}

function markSelected() {
  document.querySelectorAll<HTMLButtonElement>('[data-command]').forEach(button => {
    const active = button.dataset.command === selectedId;
    button.classList.toggle('selected', active);
    button.setAttribute('aria-pressed', String(active));
  });
}

function selectCommand(command: CommandManifest) {
  selectedId = command.id;
  markSelected();
  const detail = document.querySelector<HTMLElement>('#command-detail')!;
  detail.innerHTML = `
    <div class="cmd-detail-head">
      <div>
        <p class="cmd-eyebrow">${escapeHtml(command.id)}</p>
        <h2>${escapeHtml(command.question)}</h2>
        <p class="cmd-description">${escapeHtml(command.description ?? '')}</p>
      </div>
      <div class="cmd-version">
        <span>v${escapeHtml(command.version)}</span>
        ${command.as_of ? `<span>as of ${escapeHtml(command.as_of)}</span>` : ''}
      </div>
    </div>
    <form id="command-form" class="cmd-form">
      <div class="cmd-grid">
        ${command.inputs.map(renderInput).join('')}
      </div>
      <div class="cmd-actions">
        <button type="submit" class="cmd-button">执行命令</button>
        <button type="button" class="cmd-button cmd-button-ghost" id="command-fill">填充示例</button>
        <button type="button" class="cmd-button cmd-button-ghost" id="command-clear">清空</button>
        <span class="cmd-hint">输入来自 manifest；decimal 用字符串，date 用 YYYY-MM-DD。</span>
      </div>
      <p class="cmd-error" id="command-error" role="alert" hidden></p>
    </form>
    <section class="cmd-output-wrap">
      <div class="cmd-output-head">
        <h3>输出</h3>
        <span class="cmd-hint">按 manifest 渲染；原始 JSON 可展开</span>
      </div>
      <p class="cmd-muted" id="command-empty">执行后在这里查看 outputs。</p>
      <p class="cmd-run-meta" id="command-meta" hidden></p>
      <table class="cmd-output-table" id="command-table" hidden>
        <thead>
          <tr><th scope="col">输出</th><th scope="col">值</th></tr>
        </thead>
        <tbody></tbody>
      </table>
      <details class="cmd-json" id="command-json-wrap" hidden>
        <summary>原始 JSON</summary>
        <pre class="cmd-output" id="command-json"></pre>
      </details>
    </section>
  `;
  const form = detail.querySelector<HTMLFormElement>('#command-form')!;
  form.addEventListener('submit', event => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    void executeSelected(command);
  });
  form.addEventListener('change', () => syncRequiredFields(command, form));
  form.addEventListener('input', () => syncRequiredFields(command, form));

  const example = command.examples?.[0]?.inputs;
  const fillButton = detail.querySelector<HTMLButtonElement>('#command-fill')!;
  fillButton.disabled = !example;
  fillButton.title = example ? '用 manifest 的第一条示例填表' : '该命令没有示例';
  fillButton.addEventListener('click', () => fillValues(command, form, example ?? {}));
  detail.querySelector<HTMLButtonElement>('#command-clear')!.addEventListener('click', () =>
    fillValues(command, form, {}),
  );
  syncRequiredFields(command, form);
}

function renderInput(spec: CommandInputSpec): string {
  const id = `cmd-input-${spec.name}`;
  const required = spec.required ? 'required' : '';
  const unit = spec.unit ? `<span class="cmd-unit">${escapeHtml(spec.unit)}</span>` : '';
  const mark = `<em class="cmd-required-mark" data-required-mark="${escapeHtml(spec.name)}"${spec.required ? '' : ' hidden'}>*</em>`;
  const label = `
    <label class="cmd-label" for="${id}">
      <span>${escapeHtml(spec.question)}${mark}</span>
      ${unit}
    </label>`;
  const attrs = `id="${id}" name="${escapeHtml(spec.name)}" data-input="${escapeHtml(spec.name)}" ${required}`;

  let control: string;
  if (spec.type === 'enum') {
    const options = (spec.options ?? [])
      .map(option => `<option value="${escapeHtml(option)}">${escapeHtml(option)}</option>`)
      .join('');
    const defaultValue = spec.default === undefined || spec.default === null ? '' : String(spec.default);
    control = `<select ${attrs}><option value="">请选择</option>${options}</select>`;
    control = control.replace(
      `<option value="${escapeHtml(defaultValue)}">`,
      `<option value="${escapeHtml(defaultValue)}" selected>`,
    );
  } else if (spec.type === 'boolean') {
    const checked = spec.default === true ? 'checked' : '';
    control = `<input type="checkbox" ${attrs} ${checked} />`;
  } else if (spec.type === 'integer' || spec.type === 'number') {
    const step = spec.type === 'integer' ? '1' : 'any';
    const min = spec.constraints?.min !== undefined ? `min="${escapeHtml(spec.constraints.min)}"` : '';
    const max = spec.constraints?.max !== undefined ? `max="${escapeHtml(spec.constraints.max)}"` : '';
    const defaultValue = spec.default === undefined || spec.default === null ? '' : String(spec.default);
    control = `<input type="number" step="${step}" ${min} ${max} ${attrs} value="${escapeHtml(defaultValue)}" />`;
  } else if (spec.type === 'date') {
    control = `<input type="date" ${attrs} />`;
  } else {
    const inputMode = spec.type === 'decimal' ? 'inputmode="decimal"' : '';
    const maxLength =
      spec.constraints?.max_length !== undefined
        ? `maxlength="${escapeHtml(spec.constraints.max_length)}"`
        : '';
    const defaultValue = spec.default === undefined || spec.default === null ? '' : String(spec.default);
    control = `<input type="text" ${inputMode} ${maxLength} ${attrs} value="${escapeHtml(defaultValue)}" />`;
  }

  return `<div class="cmd-field">${label}${control}</div>`;
}

function collectInputs(command: CommandManifest): Record<string, unknown> {
  const inputs: Record<string, unknown> = {};
  const form = document.querySelector<HTMLFormElement>('#command-form')!;
  for (const spec of command.inputs) {
    const element = form.querySelector<HTMLInputElement | HTMLSelectElement>(
      `[data-input="${spec.name}"]`,
    );
    if (!element) continue;
    if (spec.type === 'boolean') {
      inputs[spec.name] = (element as HTMLInputElement).checked;
      continue;
    }
    const value = element.value.trim();
    if (!value) continue;
    if (spec.type === 'integer' || spec.type === 'number') {
      inputs[spec.name] = Number(value);
    } else {
      inputs[spec.name] = value;
    }
  }
  return inputs;
}

type FormControl = HTMLInputElement | HTMLSelectElement;

function findControl(form: HTMLFormElement, name: string): FormControl | null {
  return form.querySelector<FormControl>(`[data-input="${name}"]`);
}

function controlValue(form: HTMLFormElement, name: string): unknown {
  const element = findControl(form, name);
  if (!element) return undefined;
  if (element instanceof HTMLInputElement && element.type === 'checkbox') return element.checked;
  return element.value;
}

function isRequired(spec: CommandInputSpec, form: HTMLFormElement): boolean {
  if (spec.required) return true;
  const when = spec.required_when;
  if (!when) return false;
  const actual = controlValue(form, when.field);
  return actual !== undefined && String(actual) === String(when.equals);
}

/** required_when 只在控制字段等于 equals 时生效；星号与原生 required 同步更新。 */
function syncRequiredFields(command: CommandManifest, form: HTMLFormElement) {
  for (const spec of command.inputs) {
    const element = findControl(form, spec.name);
    if (!element) continue;
    const required = isRequired(spec, form);
    element.required = required;
    const mark = form.querySelector<HTMLElement>(`[data-required-mark="${spec.name}"]`);
    if (mark) mark.hidden = !required;
  }
}

function setControlValue(spec: CommandInputSpec, element: FormControl, value: unknown) {
  if (spec.type === 'boolean') {
    (element as HTMLInputElement).checked = value === true;
  } else if (value === undefined || value === null) {
    element.value = '';
  } else {
    element.value = String(value);
  }
  element.dispatchEvent(new Event('change', { bubbles: true }));
}

/** 用一条值表覆盖全部输入：缺项回落到 manifest 的 default，再缺就清空。 */
function fillValues(
  command: CommandManifest,
  form: HTMLFormElement,
  values: Record<string, unknown>,
) {
  for (const spec of command.inputs) {
    const element = findControl(form, spec.name);
    if (!element) continue;
    const hasValue = Object.prototype.hasOwnProperty.call(values, spec.name);
    setControlValue(spec, element, hasValue ? values[spec.name] : spec.default);
  }
  syncRequiredFields(command, form);
}

function renderOutputs(command: CommandManifest, response: CommandExecutionResponse) {
  const table = document.querySelector<HTMLTableElement>('#command-table')!;
  const body = table.querySelector<HTMLTableSectionElement>('tbody')!;
  const rows = buildOutputRows(command, response.outputs);
  body.innerHTML = rows.length
    ? rows
        .map(
          row => `
          <tr>
            <th scope="row">
              <span class="cmd-output-label">${escapeHtml(row.label)}</span>
              <code class="cmd-output-name">${escapeHtml(row.name)}</code>
            </th>
            <td>
              <span class="cmd-output-value">${escapeHtml(row.value)}</span>
              ${row.unit ? `<span class="cmd-unit">${escapeHtml(row.unit)}</span>` : ''}
            </td>
          </tr>`,
        )
        .join('')
    : '<tr><td colspan="2" class="cmd-muted">manifest 中没有可展示的输出。</td></tr>';
  table.hidden = false;

  const meta = document.querySelector<HTMLElement>('#command-meta')!;
  const parts = [response.command_id, `v${response.version}`];
  if (response.meta?.as_of) parts.push(`as of ${response.meta.as_of}`);
  parts.push(response.meta?.deterministic === false ? '非确定性' : '确定性');
  meta.textContent = parts.join(' · ');
  meta.hidden = false;

  const jsonWrap = document.querySelector<HTMLDetailsElement>('#command-json-wrap')!;
  jsonWrap.open = false;
  document.querySelector<HTMLElement>('#command-json')!.textContent = JSON.stringify(
    response,
    null,
    2,
  );
  jsonWrap.hidden = false;
}

async function executeSelected(command: CommandManifest) {
  const form = document.querySelector<HTMLFormElement>('#command-form')!;
  const button = form.querySelector<HTMLButtonElement>('button[type="submit"]')!;
  const errorElement = document.querySelector<HTMLElement>('#command-error')!;
  const emptyElement = document.querySelector<HTMLElement>('#command-empty')!;
  const tableElement = document.querySelector<HTMLElement>('#command-table')!;
  const metaElement = document.querySelector<HTMLElement>('#command-meta')!;
  const jsonWrap = document.querySelector<HTMLElement>('#command-json-wrap')!;

  errorElement.hidden = true;
  errorElement.textContent = '';
  emptyElement.hidden = false;
  tableElement.hidden = true;
  metaElement.hidden = true;
  jsonWrap.hidden = true;
  button.disabled = true;
  button.textContent = '执行中…';

  try {
    const response = await runCommand(command.id, collectInputs(command));
    renderOutputs(command, response);
    emptyElement.hidden = true;
  } catch (error) {
    errorElement.hidden = false;
    if (error instanceof CommandApiError) {
      const fields = error.fieldErrors
        .map(item => `${item.field}：${item.message}`)
        .join('\n');
      errorElement.textContent = `${error.code}：${error.message}${fields ? `\n${fields}` : ''}`;
    } else {
      errorElement.textContent = '命令执行失败，请稍后重试。';
    }
  } finally {
    button.disabled = false;
    button.textContent = '执行命令';
  }
}

function detailError(message: string) {
  document.querySelector<HTMLElement>('#command-detail')!.innerHTML =
    `<p class="cmd-error">${escapeHtml(message)}</p>`;
}

void init();
