import './style.css';
import { loadPage, PageLoadError } from './page-client';
import { pageToTemplate } from './page-to-template';
import { PageRunError, runPage } from './page-runner';
import { FormRenderer } from './form-renderer';
import { collectValues } from './form-data';
import { CommandApiError } from './command-client';
import { openGeneration } from './generation';
import { playIntro } from './intro';
import type { FormPreset, FormTemplate } from './form-types';
import type { PageManifest } from './page-types';

interface Row { age: number; phase: string; income: number; pension: number; passive: number; expense: number; medical: number; soft: number; assets: number }
interface ProjectOutput { pension_monthly: number; break_even_age: number | null; depleted_age: number | null; final_assets: number; peak_assets: number; rows: Row[] }
interface SimulateOutput { success_rate: number; terminal_p10: number; terminal_median: number; terminal_p90: number; affordable_monthly_expense: number; affordable_working_expense: number; required_monthly_income: number | null; depleted_p10: number | null; depleted_median: number | null }
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

function niceAxis(value: number, maxIntervals = 5): { max: number; step: number } {
  const target = Math.max(value, 1) / maxIntervals;
  const magnitude = 10 ** Math.floor(Math.log10(target));
  for (const unit of [1, 2, 2.5, 5, 10]) {
    const step = unit * magnitude;
    const intervals = Math.ceil(Math.max(value, 1) / step);
    if (intervals <= maxIntervals) return { max: step * intervals, step };
  }
  return { max: Math.max(value, 1), step: Math.max(value, 1) };
}

function chartFrame(rows: Row[], maxValue: number) {
  const width = 720, height = 280, padTop = 20, padBottom = 28;
  const { max, step } = niceAxis(maxValue);
  const scaleY = (value: number) => padTop + (1 - value / max) * (height - padTop - padBottom);
  const scaleX = (age: number) => 44 + ((age - rows[0].age) / (rows[rows.length - 1].age - rows[0].age || 1)) * (width - 56);
  const grid = Array.from({ length: Math.round(max / step) + 1 }, (_, index) => {
    const value = index * step;
    return `<line x1="44" y1="${scaleY(value)}" x2="${width - 12}" y2="${scaleY(value)}" stroke="${COLORS.line}" stroke-dasharray="3 5"/><text x="38" y="${scaleY(value) + 4}" text-anchor="end" class="axis-text">${axisLabel(value)}</text>`;
  }).join('');
  const ageTicks = [rows[0].age, rows[Math.floor(rows.length / 3)].age, rows[Math.floor((2 * rows.length) / 3)].age, rows[rows.length - 1].age]
    .map(age => `<text x="${scaleX(age)}" y="${height - 6}" text-anchor="middle" class="axis-text">${age}岁</text>`).join('');
  return { width, height, scaleX, scaleY, axis: grid + ageTicks };
}

function legendOf(series: { color: string; label: string }[]): string {
  return `<div class="chart-legend">${series.map(item => `<span class="legend"><i style="background:${item.color}"></i>${escapeHtml(item.label)}</span>`).join('')}</div>`;
}

function stackedChart(rows: Row[], series: { value: (row: Row) => number; color: string; label: string }[], options: { label: string }) {
  const values = rows.map(row => series.map(item => Math.max(item.value(row), 0)));
  const totals = values.map(row => row.reduce((sum, value) => sum + value, 0));
  const frame = chartFrame(rows, Math.max(...totals, 1));
  const bands = series.map((item, index) => {
    const tops: [number, number][] = [];
    const bottoms: [number, number][] = [];
    rows.forEach((row, rowIndex) => {
      const bottom = values[rowIndex].slice(0, index).reduce((sum, value) => sum + value, 0);
      const top = bottom + values[rowIndex][index];
      tops.push([frame.scaleX(row.age), frame.scaleY(top)]);
      bottoms.push([frame.scaleX(row.age), frame.scaleY(bottom)]);
    });
    return `<path d="${pathOf(tops)} ${pathOf(bottoms.reverse()).replace(/^M/, 'L')} Z" fill="${item.color}" opacity=".88"><title>${escapeHtml(item.label)}</title></path>`;
  }).join('');
  const total = `<path d="${pathOf(rows.map((row, index) => [frame.scaleX(row.age), frame.scaleY(totals[index])]))}" fill="none" stroke="${COLORS.ink}" stroke-width="2" stroke-dasharray="5 4"/>`;
  const legend = legendOf([...series, { color: COLORS.ink, label: '收入合计' }]);
  return legend + svg(frame.width, frame.height, frame.axis + bands + total, options.label);
}

function expenseChart(rows: Row[]) {
  const series = [
    { value: (row: Row) => row.expense - row.medical - row.soft, color: COLORS.sage, label: '生活' },
    { value: (row: Row) => row.medical, color: COLORS.clay, label: '医疗' },
    { value: (row: Row) => row.soft, color: COLORS.green, label: '软性' },
  ];
  const width = 720, height = 342, left = 48, right = width - 16;
  const padTop = 16, panelHeight = 84, gap = 20;
  const scaleX = (age: number) => left + ((age - rows[0].age) / (rows[rows.length - 1].age - rows[0].age || 1)) * (right - left);
  const panels = series.map((item, index) => {
    const y0 = padTop + index * (panelHeight + gap);
    const max = niceAxis(Math.max(...rows.map(item.value), 1), 3).max;
    const scaleY = (value: number) => y0 + panelHeight - (value / max) * panelHeight;
    const grid = [0, max].map(value => `<line x1="${left}" y1="${scaleY(value)}" x2="${right}" y2="${scaleY(value)}" stroke="${COLORS.line}" stroke-dasharray="3 5"/><text x="${left - 10}" y="${scaleY(value) + 4}" text-anchor="end" class="axis-text">${axisLabel(value)}</text>`).join('');
    const path = `<path d="${pathOf(rows.map(row => [scaleX(row.age), scaleY(item.value(row))]))}" fill="none" stroke="${item.color}" stroke-width="2.5"/>`;
    return `<text x="${left}" y="${y0 - 4}" class="axis-text" style="fill:${item.color}">${item.label}</text>${grid}${path}`;
  }).join('');
  const ageTicks = [rows[0].age, rows[Math.floor(rows.length / 3)].age, rows[Math.floor((2 * rows.length) / 3)].age, rows[rows.length - 1].age]
    .map(age => `<text x="${scaleX(age)}" y="${height - 6}" text-anchor="middle" class="axis-text">${age}岁</text>`).join('');
  return legendOf(series) + svg(width, height, panels + ageTicks, '不同年龄的生活、医疗与软性支出');
}

function axisLabel(value: number): string {
  const wanValue = value / 10000;
  return `${Number.isInteger(wanValue) ? wanValue : wanValue.toFixed(1)}万`;
}

function cashflowChart(rows: Row[], retirementAge: number) {
  const width = 720, height = 280, padTop = 16, padBottom = 28;
  const all = rows.flatMap(row => [row.income, row.pension, row.passive, row.expense]);
  const min = Math.min(...all, 0), max = Math.max(...all, 1);
  const scaleY = (value: number) => padTop + (1 - (value - min) / (max - min || 1)) * (height - padTop - padBottom);
  const scaleX = (age: number) => 44 + ((age - rows[0].age) / (rows[rows.length - 1].age - rows[0].age || 1)) * (width - 56);
  const deficit = rows.filter(row => row.income + row.pension + row.passive < row.expense).map(row => `<rect x="${scaleX(row.age) - 3}" y="${height - padBottom - 4}" width="6" height="4" fill="${COLORS.red}" opacity=".55"/>`).join('');
  const body = axes(width, height, rows, min, max, scaleY, scaleX) + deficit +
    `<line x1="${scaleX(retirementAge)}" y1="${padTop}" x2="${scaleX(retirementAge)}" y2="${height - padBottom}" stroke="${COLORS.clay}" stroke-dasharray="4 4"/>` +
    `<text x="${scaleX(retirementAge) + 6}" y="${padTop + 12}" class="axis-text">${retirementAge} 岁退休</text>` +
    `<path d="${pathOf(rows.filter(row => row.income > 0).map(row => [scaleX(row.age), scaleY(row.income)]))}" fill="none" stroke="${COLORS.green}" stroke-width="2.5"/>` +
    `<path d="${pathOf(rows.filter(row => row.pension > 0).map(row => [scaleX(row.age), scaleY(row.pension)]))}" fill="none" stroke="${COLORS.ink}" stroke-width="2.5"/>` +
    `<path d="${pathOf(rows.map(row => [scaleX(row.age), scaleY(row.passive)]))}" fill="none" stroke="${COLORS.sage}" stroke-width="2.5"/>` +
    `<path d="${pathOf(rows.map(row => [scaleX(row.age), scaleY(row.expense)]))}" fill="none" stroke="${COLORS.clay}" stroke-width="2.5"/>`;
  const legend = `<div class="chart-legend"><span class="legend"><i style="background:${COLORS.green}"></i>工资</span><span class="legend"><i style="background:${COLORS.ink}"></i>养老金</span><span class="legend"><i style="background:${COLORS.sage}"></i>资产收益</span><span class="legend"><i style="background:${COLORS.clay}"></i>支出</span><span class="legend"><i style="background:${COLORS.red}"></i>结余为负</span></div>`;
  return legend + svg(width, height, body, '主动收入、资产收益与支出随年龄变化');
}

function riskPanel(sim: SimulateOutput) {
  const bars = [
    ['保守（10% 分位）', sim.terminal_p10],
    ['中位', sim.terminal_median],
    ['乐观（90% 分位）', sim.terminal_p90],
  ].map(([label, value]) => `<div class="risk-row"><span>${label}</span><div class="risk-bar"><i style="width:${Math.min(100, (Number(value) / Math.max(sim.terminal_p90, 1)) * 100).toFixed(1)}%"></i></div><b>${wan(Number(value))}</b></div>`).join('');
  const need = sim.required_monthly_income === null
    ? '超出可测算范围'
    : `每月 ${money(sim.required_monthly_income)} 元`;
  return `
    <div class="risk-headline"><strong>${pct(sim.success_rate)}</strong><span>模拟路径里资产始终不为负的比例</span></div>
    ${bars}
    <p class="field-hint">按当前配比与九成成功率：维持现有支出需要${need}收入；当前收入能支撑工作期每月 ${money(sim.affordable_working_expense)} 元、退休后每月 ${money(sim.affordable_monthly_expense)} 元的生活支出。${sim.depleted_median ? `最可能在中位 ${sim.depleted_median} 岁出现资产不足。` : '多数路径不会耗尽资产。'}</p>`;
}

function strategyTable(variants: Variant[]) {
  const rows = variants.map(variant => `<tr>
      <td>${escapeHtml(variant.label)}</td>
      <td>${variant.retirement_age} 岁</td>
      <td>${pct(variant.success_rate)}</td>
      <td>${wan(variant.final_assets)}</td>
      <td>${money(variant.affordable_monthly_expense)} 元</td>
    </tr>`).join('');
  return `<table class="strategy-table"><thead><tr><th>策略</th><th>退休年龄</th><th>成功率</th><th>期末资产</th><th>可支撑退休月支出</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function detailChart(row: Row): string {
  const living = row.expense - row.medical - row.soft;
  const negativePassive = row.passive < 0;
  const incomeTotal = row.income + row.pension + Math.max(row.passive, 0);
  const net = row.income + row.pension + row.passive - row.expense;
  const income = [
    { label: '工资', value: row.income, color: '#245441' },
    { label: '养老金', value: row.pension, color: '#4f7d62' },
    { label: '资产收益', value: row.passive, color: '#8ca47d' },
  ];
  const expense = [
    { label: '生活', value: living, color: '#b89a68' },
    { label: '医疗', value: row.medical, color: '#a4574b' },
    { label: '软性', value: row.soft, color: '#d6b88a' },
  ];
  const width = 720, height = 176, plotLeft = 64, plotRight = 620, barHeight = 40;
  const max = Math.max(incomeTotal, row.expense, 1);
  const bar = (parts: { label: string; value: number; color: string }[], y: number, total: number) => {
    let x = plotLeft;
    const segments = parts.filter(part => part.value > 0).map(part => {
      const segmentWidth = (part.value / max) * (plotRight - plotLeft);
      const rect = `<rect x="${x.toFixed(1)}" y="${y}" width="${segmentWidth.toFixed(1)}" height="${barHeight}" fill="${part.color}"><title>${part.label} ${money(part.value)} 元</title></rect>`;
      const inBar = segmentWidth > 56
        ? `<text x="${(x + segmentWidth / 2).toFixed(1)}" y="${y + 25}" text-anchor="middle" class="detail-seg">${part.label} ${wan(part.value)}</text>`
        : '';
      x += segmentWidth;
      return rect + inBar;
    }).join('');
    return segments + `<text x="${plotRight + 12}" y="${y + 26}" class="detail-total">${wan(total)}</text>`;
  };
  const netColor = net < 0 ? COLORS.red : COLORS.green;
  return legendOf([
    { color: '#245441', label: '工资' },
    { color: '#4f7d62', label: '养老金' },
    { color: '#8ca47d', label: '资产收益' },
    { color: '#b89a68', label: '生活' },
    { color: '#a4574b', label: '医疗' },
    { color: '#d6b88a', label: '软性' },
  ]) + svg(width, height, `
      <text x="12" y="41" class="detail-side">收入</text>
      <text x="12" y="101" class="detail-side">支出</text>
      ${bar(income, 16, incomeTotal)}
      ${bar(expense, 76, row.expense)}
      <g><title>${money(net)} 元</title><text x="${plotLeft}" y="152" class="detail-net" style="fill:${netColor}">当年结余 ${wan(net)}</text></g>
      ${negativePassive ? `<text x="${plotLeft + 160}" y="152" class="detail-net" style="fill:${COLORS.red}">资产收益 ${wan(row.passive)}（资产已为负）</text>` : ''}
    `, '当年收入与支出的构成对比');
}

function detailCard(rows: Row[], defaultAge: number): string {
  const options = rows.map(row => `<option value="${row.age}"${row.age === defaultAge ? ' selected' : ''}>${row.age} 岁 · ${row.phase}</option>`).join('');
  return `<section class="view-card" data-view="detail"><h2>年度明细</h2><p class="section-hint">选一年，看这一年的钱从哪来、花到哪去。</p>
      <label class="detail-bar">年份<select id="detail-age" class="detail-select">${options}</select></label>
      <div id="detail-body">${detailChart(rows.find(row => row.age === defaultAge) ?? rows[0])}</div>
    </section>`;
}

function card(title: string, value: string, hint: string): string {
  return `<article class="summary-card"><h3>${title}</h3><strong>${value}</strong><p>${hint}</p></article>`;
}

function requiredIncomeCard(sim: SimulateOutput, project: ProjectOutput) {
  const current = (project.rows.find(row => row.phase === '工作')?.income ?? 0) / 12;
  const need = sim.required_monthly_income;
  if (need === null) {
    return card('维持支出需要的月收入', '超出可测算范围', '支出远超收入上限，没有可信的建议值');
  }
  if (current <= 0) {
    return card('维持支出需要的月收入', `${money(need)} 元`, '当前没有工作期收入，无法比较缺口');
  }
  if (need <= current) {
    return card('维持支出需要的月收入', `${money(need)} 元`, `当前 ${money(current)} 元，还有 ${money(current - need)} 元余量`);
  }
  return card('维持支出需要的月收入', `${money(need)} 元`, `当前 ${money(current)} 元，每月缺口 ${money(need - current)} 元`);
}

function render(project: ProjectOutput, sim: SimulateOutput, compare: CompareOutput) {
  const form = document.querySelector<HTMLFormElement>('#plan-form');
  if (form) form.hidden = true;
  const retirementAge = project.rows.find(row => row.phase === '退休')?.age ?? project.rows[0].age;
  const retirementRow = project.rows.find(row => row.age === retirementAge) ?? project.rows[0];
  host('summary-host').innerHTML = `
    <div class="summary-actions">
      <button class="button button-outline" type="button" id="pdf-button">导出 PDF</button>
      <button class="button button-outline" type="button" id="edit-button">修改参数</button>
    </div>
    <div class="summary-grid">
      ${card('退休后月养老金', `${money(project.pension_monthly)} 元`, '按推导的缴费年限与指数计算')}
      ${card('规划终点资产', wan(project.final_assets), project.depleted_age ? `${project.depleted_age} 岁出现不足` : `可支撑至 ${project.rows[project.rows.length - 1].age} 岁`)}
      ${card('退休后月资产收益', `${money(retirementRow.passive / 12)} 元`, `按当前配比，覆盖退休后月支出的 ${pct(retirementRow.passive / Math.max(retirementRow.expense, 1))}`)}
      ${card('成功率', pct(sim.success_rate), '三档配比下的蒙特卡洛结果')}
      ${requiredIncomeCard(sim, project)}
      ${card('按当前收入可支撑的月支出', `${money(sim.affordable_working_expense)} 元`, `退休后约 ${money(sim.affordable_monthly_expense)} 元/月；只调生活支出，医疗与软性不变`)}
    </div>`;
  host('views-host').innerHTML = `
    <section class="view-card" data-view="spending"><h2>支出结构</h2><p class="section-hint">生活支出退休后降一级，医疗随年龄往上走，软性支出在有孩子时最高。</p>${expenseChart(project.rows)}</section>
    <section class="view-card" data-view="income"><h2>收入曲线</h2><p class="section-hint">工资在退休那天断掉，之后靠养老金和资产收益；资产越多，被动收入越高。</p>${stackedChart(project.rows, [{ value: row => row.income, color: COLORS.green, label: '工资' }, { value: row => row.pension, color: COLORS.clay, label: '养老金' }, { value: row => row.passive, color: COLORS.sage, label: '资产收益' }], { label: '收入构成随年龄变化' })}</section>
    <section class="view-card" data-view="cashflow"><h2>收支对比</h2><p class="section-hint">工资断了以后，被动收入接得多快，决定缺口有多大。</p>${cashflowChart(project.rows, retirementAge)}</section>
    ${detailCard(project.rows, retirementAge)}
    <section class="view-card" data-view="risk"><h2>风险与生活水平</h2>${riskPanel(sim)}</section>`;
  host('strategy-host').innerHTML = `<section class="view-card" data-view="strategy"><h2>策略对比</h2><p class="section-hint">同一份画像套上五个预设，看哪种活法更宽裕。</p>${strategyTable(compare.variants)}</section>`;
  host('results').hidden = false;
  const detailSelect = document.querySelector<HTMLSelectElement>('#detail-age');
  detailSelect?.addEventListener('change', () => {
    const row = project.rows.find(item => item.age === Number(detailSelect.value));
    if (row) host('detail-body').innerHTML = detailChart(row);
  });
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
        affordableWorking: sim.affordable_working_expense,
        requiredIncome: sim.required_monthly_income,
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

const VIEW_IDS = ['spending', 'income', 'cashflow', 'detail', 'risk', 'strategy'];

function prefill(params: URLSearchParams, renderer: FormRenderer, template: FormTemplate): boolean {
  const values: Record<string, string> = {};
  for (const [name, value] of params) {
    if (name !== 'view') values[name] = value;
  }
  // 深链与示例画像走同一条写入路径：未知字段被忽略，档位之外的数值落到「其他（自己填）」。
  renderer.applyPreset(values);
  return collectValues(template, renderer.readRaw()).errors.length === 0;
}

function renderPresets(presets: FormPreset[], renderer: FormRenderer): void {
  const bar = host('preset-host');
  if (!presets.length) return;
  bar.hidden = false;
  bar.replaceChildren();
  const lead = document.createElement('span');
  lead.className = 'preset-lead';
  lead.textContent = '一键填入画像：';
  const note = document.createElement('span');
  note.className = 'preset-note';
  note.textContent = presets[0].description ?? '';
  const chips = presets.map(preset => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = 'preset-chip';
    chip.textContent = preset.label;
    chip.addEventListener('click', () => {
      renderer.applyPreset(preset.values);
      bar.querySelectorAll('.preset-chip').forEach(node => node.classList.toggle('selected', node === chip));
      note.textContent = `已按${preset.label}画像填好，可以直接改任意一项`;
    });
    return chip;
  });
  bar.append(lead, ...chips, note);
}

const STAGES = ['正在整理你的画像…', '正在测算现金流与风险…', '正在对比五种活法…'];

async function bootstrap() {
  playIntro();
  const formHost = host('form-host');
  try {
    const page: PageManifest = await loadPage('retirement.lifecycle');
    const template = pageToTemplate(page);
    const renderer = new FormRenderer(formHost, template);
    renderPresets(template.presets, renderer);
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
    if ([...params.keys()].some(key => key !== 'view') && prefill(params, renderer, template)) {
      form.requestSubmit();
    }
  } catch (error) {
    const message = error instanceof PageLoadError ? error.message : '页面清单加载失败。';
    formHost.innerHTML = `<p class="field-error">${escapeHtml(message)}</p>`;
  }
}

void bootstrap();
