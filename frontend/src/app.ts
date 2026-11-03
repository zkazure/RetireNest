import './style.css';
import { loadPage, PageLoadError } from './page-client';
import { pageToTemplate } from './page-to-template';
import { PageRunError, runPage } from './page-runner';
import { FormRenderer } from './form-renderer';
import { CommandApiError } from './command-client';
import { openGeneration } from './generation';
import { playIntro } from './intro';
import type { PageManifest } from './page-types';

interface Row { age: number; phase: string; income: number; expense: number; medical: number; soft: number; assets: number }
interface ProjectOutput { pension_monthly: number; break_even_age: number | null; depleted_age: number | null; final_assets: number; peak_assets: number; rows: Row[] }
interface SimulateOutput { success_rate: number; terminal_p10: number; terminal_median: number; terminal_p90: number; affordable_monthly_expense: number; depleted_p10: number | null; depleted_median: number | null }
interface Variant { preset_id: string; label: string; retirement_age: number; final_assets: number; success_rate: number; affordable_monthly_expense: number; depleted_age: number | null }
interface CompareOutput { variants: Variant[] }

const host = (id: string) => document.querySelector<HTMLElement>(`#${id}`)!;
const money = (value: number) => Math.round(value).toLocaleString('zh-CN');
const wan = (value: number) => `${(value / 10000).toFixed(1)} 万`;
const pct = (value: number) => `${(value * 100).toFixed(1)}%`;
const escapeHtml = (value: string) => value.replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]!));

const COLORS = { green: '#327359', sage: '#8ca47d', clay: '#b89a68', red: '#a4574b', ink: '#2f3a2e', line: '#dfe5da' };

function svg(width: number, height: number, body: string, label: string): string {
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(label)}" class="plan-chart">${body}</svg>`;
}

function pathOf(points: [number, number][]): string {
  return points.map(([x, y], index) => `${index === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
}

function axes(width: number, height: number, rows: Row[], minValue: number, maxValue: number, scaleY: (v: number) => number, scaleX: (age: number) => number) {
  const lines = [0, 0.25, 0.5, 0.75, 1].map(ratio => {
    const value = minValue + (maxValue - minValue) * ratio;
    return `<line x1="44" y1="${scaleY(value)}" x2="${width - 12}" y2="${scaleY(value)}" stroke="${COLORS.line}" stroke-dasharray="3 5"/><text x="38" y="${scaleY(value) + 4}" text-anchor="end" class="axis-text">${Math.round(value / 10000)}万</text>`;
  }).join('');
  const ages = [rows[0].age, rows[Math.floor(rows.length / 3)].age, rows[Math.floor((2 * rows.length) / 3)].age, rows[rows.length - 1].age];
  const ticks = ages.map(age => `<text x="${scaleX(age)}" y="${height - 6}" text-anchor="middle" class="axis-text">${age}岁</text>`).join('');
  return lines + ticks;
}

function lineChart(rows: Row[], series: { value: (row: Row) => number; color: string; label: string }[], options: { min?: number; max?: number; label: string }) {
  const width = 720, height = 260, padTop = 16, padBottom = 28;
  const all = series.flatMap(item => rows.map(item.value));
  const min = options.min ?? Math.min(0, ...all);
  const max = options.max ?? Math.max(...all, 1);
  const scaleY = (value: number) => padTop + (1 - (value - min) / (max - min || 1)) * (height - padTop - padBottom);
  const scaleX = (age: number) => 44 + ((age - rows[0].age) / (rows[rows.length - 1].age - rows[0].age || 1)) * (width - 56);
  const body = axes(width, height, rows, min, max, scaleY, scaleX) +
    series.map(item => `<path d="${pathOf(rows.map(row => [scaleX(row.age), scaleY(item.value(row))]))}" fill="none" stroke="${item.color}" stroke-width="2.5"/>`).join('');
  const legend = series.map(item => `<span class="legend"><i style="background:${item.color}"></i>${escapeHtml(item.label)}</span>`).join('');
  return `<div class="chart-legend">${legend}</div>` + svg(width, height, body, options.label);
}

function spendingChart(rows: Row[]) {
  const picks = [0.5, 0.7, 0.9].map(ratio => rows[Math.min(rows.length - 1, Math.floor(rows.length * ratio))]);
  const width = 520, height = 220, barWidth = 64;
  const max = Math.max(...picks.map(row => row.expense), 1);
  const bars = picks.map((row, index) => {
    const x = 60 + index * 140;
    const base = row.expense - row.medical - row.soft;
    const segments: [number, string, string][] = [
      [base, COLORS.sage, '生活'],
      [row.medical, COLORS.clay, '医疗'],
      [row.soft, COLORS.green, '软性'],
    ];
    let y = height - 30;
    const parts = segments.map(([value, color, label]) => {
      const h = (value / max) * (height - 60);
      y -= h;
      return `<rect x="${x}" y="${y}" width="${barWidth}" height="${Math.max(h, 0)}" fill="${color}" rx="3"><title>${label} ${money(value)} 元</title></rect>`;
    }).join('');
    return `${parts}<text x="${x + barWidth / 2}" y="${height - 12}" text-anchor="middle" class="axis-text">${row.age}岁</text><text x="${x + barWidth / 2}" y="${y - 8}" text-anchor="middle" class="axis-text">${wan(row.expense)}</text>`;
  }).join('');
  const legend = `<div class="chart-legend"><span class="legend"><i style="background:${COLORS.sage}"></i>生活</span><span class="legend"><i style="background:${COLORS.clay}"></i>医疗</span><span class="legend"><i style="background:${COLORS.green}"></i>软性</span></div>`;
  return legend + svg(width, height, bars, '不同年龄的支出结构');
}

function cashflowChart(rows: Row[], retirementAge: number) {
  const width = 720, height = 280, padTop = 16, padBottom = 28;
  const all = rows.flatMap(row => [row.income, row.expense]);
  const min = Math.min(...all, 0), max = Math.max(...all, 1);
  const scaleY = (value: number) => padTop + (1 - (value - min) / (max - min || 1)) * (height - padTop - padBottom);
  const scaleX = (age: number) => 44 + ((age - rows[0].age) / (rows[rows.length - 1].age - rows[0].age || 1)) * (width - 56);
  const deficit = rows.filter(row => row.income < row.expense).map(row => `<rect x="${scaleX(row.age) - 3}" y="${height - padBottom - 4}" width="6" height="4" fill="${COLORS.red}" opacity=".55"/>`).join('');
  const body = axes(width, height, rows, min, max, scaleY, scaleX) + deficit +
    `<line x1="${scaleX(retirementAge)}" y1="${padTop}" x2="${scaleX(retirementAge)}" y2="${height - padBottom}" stroke="${COLORS.clay}" stroke-dasharray="4 4"/>` +
    `<text x="${scaleX(retirementAge) + 6}" y="${padTop + 12}" class="axis-text">${retirementAge} 岁退休</text>` +
    `<path d="${pathOf(rows.map(row => [scaleX(row.age), scaleY(row.income)]))}" fill="none" stroke="${COLORS.green}" stroke-width="2.5"/>` +
    `<path d="${pathOf(rows.map(row => [scaleX(row.age), scaleY(row.expense)]))}" fill="none" stroke="${COLORS.clay}" stroke-width="2.5"/>`;
  const legend = `<div class="chart-legend"><span class="legend"><i style="background:${COLORS.green}"></i>收入</span><span class="legend"><i style="background:${COLORS.clay}"></i>支出</span><span class="legend"><i style="background:${COLORS.red}"></i>结余为负</span></div>`;
  return legend + svg(width, height, body, '收入与支出随年龄变化');
}

function riskPanel(sim: SimulateOutput) {
  const bars = [
    ['保守（10% 分位）', sim.terminal_p10],
    ['中位', sim.terminal_median],
    ['乐观（90% 分位）', sim.terminal_p90],
  ].map(([label, value]) => `<div class="risk-row"><span>${label}</span><div class="risk-bar"><i style="width:${Math.min(100, (Number(value) / Math.max(sim.terminal_p90, 1)) * 100).toFixed(1)}%"></i></div><b>${wan(Number(value))}</b></div>`).join('');
  return `
    <div class="risk-headline"><strong>${pct(sim.success_rate)}</strong><span>模拟路径里资产始终不为负的比例</span></div>
    ${bars}
    <p class="field-hint">按当前配比，模拟要求成功率九成时，退休后每月可支撑 ${money(sim.affordable_monthly_expense)} 元。${sim.depleted_median ? `最可能在中位 ${sim.depleted_median} 岁出现资产不足。` : '多数路径不会耗尽资产。'}</p>`;
}

function strategyTable(variants: Variant[]) {
  const rows = variants.map(variant => `<tr>
      <td>${escapeHtml(variant.label)}</td>
      <td>${variant.retirement_age} 岁</td>
      <td>${pct(variant.success_rate)}</td>
      <td>${wan(variant.final_assets)}</td>
      <td>${money(variant.affordable_monthly_expense)} 元</td>
    </tr>`).join('');
  return `<table class="strategy-table"><thead><tr><th>策略</th><th>退休年龄</th><th>成功率</th><th>期末资产</th><th>可支撑月支出</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function card(title: string, value: string, hint: string): string {
  return `<article class="summary-card"><h3>${title}</h3><strong>${value}</strong><p>${hint}</p></article>`;
}

function render(project: ProjectOutput, sim: SimulateOutput, compare: CompareOutput) {
  const form = document.querySelector<HTMLFormElement>('#plan-form');
  if (form) form.hidden = true;
  const retirementAge = project.rows.find(row => row.phase === '退休')?.age ?? project.rows[0].age;
  host('summary-host').innerHTML = `
    <div class="summary-actions">
      <button class="button button-outline" type="button" id="pdf-button">导出 PDF</button>
      <button class="button button-outline" type="button" id="edit-button">修改参数</button>
    </div>
    <div class="summary-grid">
      ${card('退休后月养老金', `${money(project.pension_monthly)} 元`, '按推导的缴费年限与指数计算')}
      ${card('规划终点资产', wan(project.final_assets), project.depleted_age ? `${project.depleted_age} 岁出现不足` : `可支撑至 ${project.rows[project.rows.length - 1].age} 岁`)}
      ${card('结余转负', project.break_even_age ? `${project.break_even_age} 岁` : '不会转负', '收入第一次低于支出的年龄')}
      ${card('成功率', pct(sim.success_rate), '三档配比下的蒙特卡洛结果')}
    </div>`;
  host('views-host').innerHTML = `
    <section class="view-card" data-view="spending"><h2>支出结构</h2><p class="section-hint">医疗与软性支出影响的是退休后最花钱的那几年。</p>${spendingChart(project.rows)}</section>
    <section class="view-card" data-view="income"><h2>收入曲线</h2><p class="section-hint">退休那一刻收入从工资换成养老金，落差决定要提前准备多少。</p>${lineChart(project.rows, [{ value: row => row.income, color: COLORS.green, label: '收入' }], { label: '收入随年龄变化', min: 0 })}</section>
    <section class="view-card" data-view="cashflow"><h2>收支对比</h2><p class="section-hint">两条线交叉的位置，就是现金流拐点。</p>${cashflowChart(project.rows, retirementAge)}</section>
    <section class="view-card" data-view="risk"><h2>风险与生活水平</h2>${riskPanel(sim)}</section>`;
  host('strategy-host').innerHTML = `<section class="view-card" data-view="strategy"><h2>策略对比</h2><p class="section-hint">同一份画像套上五个预设，看哪种活法更宽裕。</p>${strategyTable(compare.variants)}</section>`;
  host('results').hidden = false;
  host('pdf-button').addEventListener('click', async () => {
    const button = host('pdf-button') as HTMLButtonElement;
    button.disabled = true;
    button.textContent = '正在生成…';
    try {
      const { createReportPdf } = await import('./pdf-export');
      const bytes = await createReportPdf({
        pensionMonthly: project.pension_monthly,
        finalAssets: project.final_assets,
        breakEvenAge: project.break_even_age,
        depletedAge: project.depleted_age,
        successRate: sim.success_rate,
        affordableMonthly: sim.affordable_monthly_expense,
        rows: project.rows,
        variants: compare.variants,
      });
      const url = URL.createObjectURL(new Blob([new Uint8Array(bytes)], { type: 'application/pdf' }));
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'RetireNest-全周期现金流.pdf';
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      window.alert('导出失败，请稍后重试。');
    } finally {
      button.disabled = false;
      button.textContent = '导出 PDF';
    }
  });
  host('edit-button').addEventListener('click', () => {
    const form = document.querySelector<HTMLFormElement>('#plan-form');
    if (form) form.hidden = false;
    host('results').hidden = true;
    form?.scrollIntoView({ block: 'start' });
  });
  const wanted = new URLSearchParams(location.search).get('view');
  if (wanted && VIEW_IDS.includes(wanted)) {
    document.querySelectorAll<HTMLElement>('[data-view]').forEach(node => { node.hidden = node.dataset.view !== wanted; });
  }
  host('results').scrollIntoView({ block: 'start' });
}

const TIER_FIELDS = new Set(['income', 'expense', 'assets', 'debt', 'retirement_expense', 'retirement_age', 'travel', 'entertainment', 'children']);
const VIEW_IDS = ['spending', 'income', 'cashflow', 'risk', 'strategy'];

function prefill(params: URLSearchParams): boolean {
  let complete = true;
  for (const [name, value] of params) {
    if (!TIER_FIELDS.has(name)) continue;
    const control = document.querySelector<HTMLInputElement>(`input[name="${name}"][value="${CSS.escape(value)}"]`);
    if (control) {
      control.checked = true;
      control.dispatchEvent(new Event('change', { bubbles: true }));
      continue;
    }
    // 深链里给了档位之外的数值时，落到「其他（自己填）」而不是判定预填失败。
    const other = document.querySelector<HTMLInputElement>(`input[name="${name}"][value="__custom__"]`);
    const custom = document.querySelector<HTMLInputElement>(`#field-${name}-custom`);
    if (other && custom) {
      other.checked = true;
      custom.value = value;
      other.dispatchEvent(new Event('change', { bubbles: true }));
      custom.dispatchEvent(new Event('input', { bubbles: true }));
    } else {
      complete = false;
    }
  }
  const sex = params.get('sex');
  if (sex === '男' || sex === '女') {
    const select = document.querySelector<HTMLSelectElement>('select[name="sex"]');
    if (select) { select.value = sex; select.dispatchEvent(new Event('change', { bubbles: true })); }
    else complete = false;
  } else {
    complete = false;
  }
  const city = params.get('city');
  if (city) {
    const select = document.querySelector<HTMLSelectElement>('select[name="city"]');
    if (select && [...select.options].some(option => option.value === city)) {
      select.value = city; select.dispatchEvent(new Event('change', { bubbles: true }));
    } else complete = false;
  } else complete = false;
  const birth = params.get('birth_date');
  if (birth) {
    const input = document.querySelector<HTMLInputElement>('input[name="birth_date"]');
    if (input) { input.value = birth; input.dispatchEvent(new Event('change', { bubbles: true })); }
    else complete = false;
  } else complete = false;
  return complete;
}

const STAGES = ['正在整理你的画像…', '正在测算现金流与风险…', '正在对比五种活法…'];

async function bootstrap() {
  playIntro();
  const formHost = host('form-host');
  try {
    const page: PageManifest = await loadPage('retirement.lifecycle');
    const template = pageToTemplate(page);
    const renderer = new FormRenderer(formHost, template);
    const form = document.querySelector<HTMLFormElement>('#plan-form')!;
    const params = new URLSearchParams(location.search);
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const errorElement = host('form-error');
      const collected = renderer.collect();
      if (collected.errors.length) {
        errorElement.hidden = false; errorElement.textContent = collected.errors[0].message; return;
      }
      const button = form.querySelector<HTMLButtonElement>('button[type="submit"]')!;
      button.disabled = true; button.textContent = '正在算…';
      const generation = openGeneration(STAGES);
      try {
        const results = await runPage(page, collected.values);
        generation.close();
        const find = (command: string) => results.find(item => item.execution.command === command)?.outputs as unknown;
        render(find('lifecycle.project') as ProjectOutput, find('lifecycle.simulate') as SimulateOutput, find('strategy.compare') as CompareOutput);
        errorElement.hidden = true;
      } catch (error) {
        generation.close();
        errorElement.hidden = false;
        if (error instanceof PageRunError) { renderer.setFieldErrors(error.fieldErrors); errorElement.textContent = error.message; }
        else if (error instanceof CommandApiError) errorElement.textContent = error.message;
        else errorElement.textContent = '测算遇到问题，请稍后重试。';
      } finally {
        button.disabled = false; button.textContent = '开始测算';
      }
    });
    if ([...params.keys()].some(key => key !== 'view') && prefill(params)) {
      form.requestSubmit();
    }
  } catch (error) {
    const message = error instanceof PageLoadError ? error.message : '页面清单加载失败。';
    formHost.innerHTML = `<p class="field-error">${escapeHtml(message)}</p>`;
  }
}

void bootstrap();
