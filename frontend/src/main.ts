import './style.css';
import { calculatePlan, defaultInput, validateInput, type PlanInput, type PlanResult } from './model';
import templateJson from './form-template.json';
import { validateTemplate, buildRequest } from './form-data';
import { FormRenderer } from './form-renderer';
import { toDemoInput } from './form-adapter';
import type { PlanRequest } from './form-types';
validateTemplate(templateJson);
const template = templateJson;
let submittedRequest: PlanRequest | null = null;

const icons: Record<string, string> = {
  nest: '<path d="M4 13V8l8-5 8 5v5M6 13l6 3 6-3M4 17l8 4 8-4M8 10l4 2 4-2"/>',
  grid: '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
  sliders: '<path d="M4 7h16M4 17h16M8 4v6M16 14v6"/>',
  arrow: '<path d="M5 12h14m-5-5 5 5-5 5"/>',
  download: '<path d="M12 3v12m-4-4 4 4 4-4M4 16v5h16v-5"/>',
  leaf: '<path d="M20 3C10 2 3 7 5 15c8 4 15-2 15-12ZM5 20l10-11"/>',
  spark: '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v.1"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  wallet: '<path d="M20 8V5H5a2 2 0 0 0 0 4h15v11H5a2 2 0 0 1-2-2V7m17 6h-5v4h5"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  chevron: '<path d="m9 5 7 7-7 7"/>',
};
const icon = (name: string, cls = '') => `<svg class="icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] ?? icons.info}</svg>`;
const money = (value: number) => Math.round(value).toLocaleString('zh-CN');
const wan = (value: number) => (value / 10000).toFixed(1);
let currentInput: PlanInput = { ...defaultInput };
let activeScenario = 1;
let hasGeneratedPlan = false;
let isGenerating = false;
const escapeHtml = (value: string) => value.replace(/[&<>"']/g, char => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char]!));
let toastTimer: ReturnType<typeof setTimeout>;
let toastHideTimer: ReturnType<typeof setTimeout>;

const app = document.querySelector<HTMLDivElement>('#app')!;
app.innerHTML = `
  <section class="startup-intro" id="startup-intro" aria-label="欢迎来到退有所算">
    <div class="intro-orbit" aria-hidden="true"></div>
    <div class="intro-content"><span class="intro-leaf">${icon('leaf')}</span><p class="intro-eyebrow">RETIRENEST</p><h1><span class="intro-title-line">给未来的自己</span><span class="intro-title-line">多一点从容</span></h1><p class="intro-caption"><span>从今天的一小步开始</span><span>让理想生活慢慢生长</span></p><span class="intro-line" aria-hidden="true"></span></div>
    <button class="intro-skip" id="skip-intro">跳过动画 ${icon('arrow')}</button>
  </section>
  <div class="shell" inert>
    <main id="overview">
      <header class="page-heading"><a class="brand" href="#overview" aria-label="退有所算首页"><span class="brand-icon">${icon('nest')}</span><span>退有所算<small>RETIRENEST</small></span></a><button class="button button-outline" id="export-button" hidden disabled title="生成规划后可导出">${icon('download')}导出规划</button></header>
      <div class="workspace-grid">
        <section class="card profile-card" aria-labelledby="profile-title"><div class="section-heading"><div><span class="step-label">01 / YOUR PROFILE</span><h1 id="profile-title" tabindex="-1">我的规划信息</h1></div></div>
          <form id="plan-form">
            <p class="template-description" id="template-description"></p>
            <div id="template-fields"></div>
            <div class="api-config"><label class="field" for="api-key"><span>API Key <span class="optional-label">可选</span></span><div class="input-wrap"><input type="password" id="api-key" name="apiKey" placeholder="填写你的 API Key" autocomplete="off" spellcheck="false" aria-describedby="api-key-hint" /></div></label><p class="field-hint" id="api-key-hint">当前仅提供输入栏，尚未接入接口；留空也可生成本地演示规划。</p></div>
            <p class="form-error" id="form-error" role="alert" hidden></p><button type="submit" class="button button-primary calculate-button">生成我的退休规划 ${icon('arrow')}</button><div class="form-footer">${icon('check')}信息仅用于当前页面测算，不会上传</div>
          </form>
        </section>
        <section class="generation-panel card" id="generation-panel" hidden aria-labelledby="generation-title">
          <div class="generation-orbit" aria-hidden="true"><span class="generation-spinner"></span><span class="generation-leaf">${icon('leaf')}</span></div>
          <span class="step-label">SHAPING YOUR FUTURE</span>
          <h1 id="generation-title" tabindex="-1">正在生成你的退休规划</h1>
          <p id="generation-message" role="status" aria-live="polite">正在整理你的规划信息…</p>
          <div class="generation-steps" aria-hidden="true"><span class="active">整理信息</span><i></i><span>测算目标</span><i></i><span>对比情景</span></div>
          <p class="generation-footnote">把今天的数字，变成未来的方向。</p>
        </section>
        <div class="results-column" id="results" aria-live="polite" aria-atomic="false" hidden></div>
      </div>

    </main>
  </div><div class="toast" id="toast" role="status" hidden></div>
  <dialog id="help-dialog"><div class="dialog-top"><h2>关于这份退休测算</h2><button class="icon-button" id="close-help" aria-label="关闭说明">×</button></div><p>这是前端演示，所有结果由本地公式计算，尚未连接 AI 或后端。</p><p>所有金额以今天的购买力展示。实际年回报 = (1 + 名义年回报) ÷ (1 + 通胀率) − 1。工作期间的年结余和退休后的支出缺口统一按年末计入。</p><p>退休资金目标为退休后各年支出减养老金的折现总额；退休时预计资产为当前净资产与未来结余的累积值。</p><p>假设收支及养老金随通胀同步变化，负债直接抵减资产，不另算利息；不计税费、收益波动或政策变化。城市不参与计算。结果用于展示与学习，不构成投资或养老金政策建议。</p><button class="button button-primary" id="understood-button">了解了</button></dialog>
`;

function chart(input: PlanInput, result: PlanResult): string {
  const width = 760, height = 240, left = 58, right = 25, top = 18, bottom = 36;
  const plotWidth = width - left - right, plotHeight = height - top - bottom;
  const allValues = result.points.map(point => point.assets);
  const max = Math.max(result.target * 1.12, ...allValues, 10000);
  const min = Math.min(0, ...allValues) * 1.08;
  const x = (age: number) => left + (age - input.age) / (input.lifeExpectancy - input.age) * plotWidth;
  const y = (value: number) => top + (max - value) / (max - min) * plotHeight;
  const pathFor = (points: typeof result.points) => points.map((p, i) => `${i === 0 ? 'M' : 'L'}${x(p.age).toFixed(2)},${y(p.assets).toFixed(2)}`).join(' ');
  const split = result.yearsToRetirement;
  const accumulation = result.points.slice(0, split + 1), retirement = result.points.slice(split);
  const area = `${pathFor(result.points)} L${x(input.lifeExpectancy)},${y(min)} L${left},${y(min)} Z`;
  const ticks = Array.from(new Set([input.age, ...Array.from({length: 9}, (_, i) => (i + 2) * 10).filter(age => age > input.age + 3 && age < input.lifeExpectancy - 3), input.lifeExpectancy]));
  return `<svg class="projection-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="从 ${input.age} 岁到 ${input.lifeExpectancy} 岁的预计资产变化，退休时预计 ${wan(result.projected)} 万元"><defs><linearGradient id="chart-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#5e906a" stop-opacity=".17"/><stop offset="100%" stop-color="#5e906a" stop-opacity=".01"/></linearGradient></defs><rect x="${x(input.retirementAge)}" y="${top}" width="${width - right - x(input.retirementAge)}" height="${plotHeight}" fill="#f7f8f3"/>${[0,1,2,3].map(i => {const value = min + (max - min) * i / 3; return `<line x1="${left}" y1="${y(value)}" x2="${width-right}" y2="${y(value)}" stroke="#e9ede8" stroke-dasharray="3 5"/><text x="${left-10}" y="${y(value)+4}" text-anchor="end">${Math.round(value/10000)}万</text>`;}).join('')}<path d="${area}" fill="url(#chart-fill)"/><line x1="${left}" x2="${width-right}" y1="${y(result.target)}" y2="${y(result.target)}" stroke="#b89a68" stroke-dasharray="5 5"/><text x="${width-right}" y="${Math.max(13,y(result.target)-8)}" text-anchor="end" class="target-label">退休目标 ${wan(result.target)}万</text><path d="${pathFor(accumulation)}" stroke="#327359" stroke-width="3" fill="none"/><path d="${pathFor(retirement)}" stroke="#8ca47d" stroke-width="2.5" fill="none"/><line x1="${x(input.retirementAge)}" x2="${x(input.retirementAge)}" y1="${top}" y2="${height-bottom}" stroke="#adbba7" stroke-dasharray="4 4"/><circle cx="${x(input.retirementAge)}" cy="${y(result.projected)}" r="5" fill="#327359" stroke="white" stroke-width="2"/>${ticks.map(age=>`<text x="${x(age)}" y="${height-11}" text-anchor="middle">${age}岁</text>`).join('')}<text x="${x(input.retirementAge)+8}" y="${height-bottom-8}" class="retirement-label">${input.retirementAge}岁退休</text></svg>`;
}

function renderResults() {
  const result = calculatePlan(currentInput);
  const submittedCount = Object.keys(submittedRequest?.values ?? {}).length;
  const savingExtra = Math.max(0, result.requiredMonthlySaving - result.monthlySurplus);
  const coverage = Math.min(100, result.coverage);
  const scenarios = [{ name: '保守情景', subtitle: '更审慎地看待未来', delta: -1, mark: '01' }, { name: '基准情景', subtitle: '按当前假设稳步前行', delta: 0, mark: '02' }, { name: '乐观情景', subtitle: '让时间释放更多可能', delta: 1, mark: '03' }];
  document.querySelector('#results')!.innerHTML = `
    <div class="results-toolbar"><div><span class="step-label">YOUR RETIREMENT PLAN</span><h1 id="result-title" tabindex="-1">你的退休规划</h1></div><button type="button" class="button button-outline" id="back-button">${icon('arrow', 'back-arrow')}返回修改</button></div>
    <p class="result-template-note">本次按模板收集了 ${submittedCount} 项信息。当前结果为基础字段的本地演示；扩展模块待后端接入。</p>
    <section class="card result-summary"><div class="section-heading"><div><span class="step-label">02 / YOUR RETIREMENT OUTLOOK</span><h2>你的退休规划概览</h2></div><span class="subtle-badge">${escapeHtml(currentInput.city)} · ${currentInput.age}岁出发</span></div><div class="summary-subtitle">距离 ${currentInput.retirementAge} 岁退休，还有 <strong>${result.yearsToRetirement} 年</strong> 的准备时间。</div><div class="metrics"><div class="metric"><div class="metric-label">${icon('target')}退休所需资金</div><div class="metric-value">${wan(result.target)}<span>万元</span></div><p>覆盖退休后 ${result.retirementYears} 年的支出缺口</p></div><div class="metric"><div class="metric-label">${icon('wallet')}退休时预计资产</div><div class="metric-value">${wan(result.projected)}<span>万元</span></div><p>按当前每月结余 ${money(result.monthlySurplus)} 元测算</p></div><div class="metric metric-gap"><div class="metric-label">${icon('leaf')}${result.gap > 0 ? '还需准备' : '预计资金余量'}</div><div class="metric-value">${wan(result.gap > 0 ? result.gap : result.projected-result.target)}<span>万元</span></div><p>${result.gap > 0 ? '把差距拆小，未来更有方向' : '当前假设下已覆盖退休目标'}</p></div></div><div class="coverage-row"><span>退休目标准备度</span><div class="progress-track"><span style="width:${coverage}%"></span></div><strong>${result.coverage.toFixed(0)}%</strong></div><div class="saving-note">${icon('info')}<span>${result.gap > 0 ? `若维持当前假设，每月结余达到 <strong>¥${money(result.requiredMonthlySaving)}</strong> 可覆盖目标，比现在多 <strong>¥${money(savingExtra)}</strong>。` : '按当前假设，你已走在实现退休目标的路径上。可以调整退休年龄，看看未来的更多可能。'}</span></div></section>
    <section class="card chart-card"><div class="section-heading"><div><h2>让未来的资产，有迹可循</h2><p class="section-description">从积累到退休，看看资金如何陪伴你的每个阶段。</p></div><span class="chart-unit">单位：万元</span></div><div class="chart-legend"><span><i class="legend-dot green"></i>资产积累期</span><span><i class="legend-dot sage"></i>退休支取期</span><span><i class="legend-dash"></i>退休资金目标</span></div>${chart(currentInput,result)}<div class="chart-bottom">${icon('clock')}<span>${result.depletedAge ? `当前路径下，资产预计在 ${result.depletedAge} 岁出现不足，可尝试增加结余或调整退休计划。` : `按当前假设，资产可支持至规划终点 ${currentInput.lifeExpectancy} 岁。`}</span></div></section>
    <section class="card scenario-section" id="scenarios"><div class="section-heading"><div><h2>同一个目标，看看不同的可能</h2><p class="section-description">仅调整名义年回报，其余条件保持不变。</p></div><span class="subtle-badge">3 种情景</span></div><div class="scenario-grid">${scenarios.map((scenario,index)=> {const rate = Math.max(-5,Math.min(15,currentInput.nominalReturn+scenario.delta)); const scenarioResult = calculatePlan({...currentInput,nominalReturn:rate});return `<button type="button" class="scenario-card ${index === activeScenario ? 'selected' : ''}" data-scenario="${index}" aria-pressed="${index === activeScenario}"><div class="scenario-title"><strong>${scenario.name}</strong><span class="scenario-radio">${index === activeScenario ? icon('check') : ''}</span></div><p>${scenario.subtitle}</p><div class="scenario-amount">${wan(scenarioResult.projected)}<span>万元</span></div><div class="scenario-footer"><span>名义年回报 ${rate.toFixed(1)}%</span><span>${scenarioResult.gap > 0 ? '缺口 '+wan(scenarioResult.gap)+'万' : '目标已覆盖'}</span></div></button>`;}).join('')}</div><div class="scenario-detail" id="scenario-detail"></div></section>
    <section class="insight-card" id="insights"><span class="insight-icon">${icon('spark')}</span><div class="insight-content"><div class="insight-heading"><h2>把数字，变成下一步</h2><span>规则解读 · AI 待接入</span></div><p>${result.gap > 0 ? `你还有 ${result.yearsToRetirement} 年的准备时间。当前每月结余为 ${money(result.monthlySurplus)} 元，目标准备度约 ${result.coverage.toFixed(0)}%。先尝试在可承受范围内调整收支，再观察目标缺口如何变化。` : `你的当前路径已覆盖目标。距离退休还有 ${result.yearsToRetirement} 年，建议定期更新真实收支和养老金假设，观察计划是否仍符合期待。`}</p><button class="text-button" id="adjust-button">调整我的规划 ${icon('arrow')}</button></div></section>
    <div class="disclaimer">${icon('info')}<span>金额均为今天的购买力。本地演示假设不代表未来实际收益；结果用于学习展示，不构成投资建议。<button class="inline-link" id="method-button">查看测算说明</button></span></div>
  `;
  document.querySelectorAll<HTMLButtonElement>('[data-scenario]').forEach(button => button.addEventListener('click', () => { activeScenario = Number(button.dataset.scenario); renderResults(); }));
  const selected = scenarios[activeScenario];
  const rate = Math.max(-5, Math.min(15,currentInput.nominalReturn + selected.delta));
  const selectedResult = calculatePlan({...currentInput, nominalReturn: rate});
  document.querySelector('#scenario-detail')!.textContent = `${selected.name}：实际年回报 ${(selectedResult.realReturn*100).toFixed(2)}%，退休资金目标 ${wan(selectedResult.target)} 万，预计退休资产 ${wan(selectedResult.projected)} 万。${selectedResult.gap > 0 ? `资金缺口 ${wan(selectedResult.gap)} 万。` : '预计可覆盖目标。'}点击卡片仅切换对比说明。`;
  document.querySelector('#adjust-button')!.addEventListener('click', showForm);
  document.querySelector('#back-button')!.addEventListener('click', showForm);
  document.querySelector('#method-button')!.addEventListener('click',openHelp);
}
function toast(message: string) {
  const element = document.querySelector<HTMLDivElement>('#toast')!;
  clearTimeout(toastTimer);
  clearTimeout(toastHideTimer);
  element.classList.remove('toast-enter', 'toast-exit');
  element.textContent = message;
  element.hidden = false;
  // Restart the entrance when a new message replaces an existing toast.
  void element.offsetWidth;
  element.classList.add('toast-enter');
  toastTimer = setTimeout(()=>{
    element.classList.remove('toast-enter');
    element.classList.add('toast-exit');
    toastHideTimer = setTimeout(()=>{
      element.hidden = true;
      element.classList.remove('toast-exit');
    }, reducedMotion ? 0 : 300);
  }, 3200);
}
function openHelp() { document.querySelector<HTMLDialogElement>('#help-dialog')!.showModal(); }
const form = document.querySelector<HTMLFormElement>('#plan-form')!;
form.noValidate = true;
const renderer = new FormRenderer(document.querySelector<HTMLElement>('#template-fields')!, template);
document.querySelector('#profile-title')!.textContent = template.title;
document.querySelector('#template-description')!.textContent = template.description;
for (const eventName of ['input','change']) form.addEventListener(eventName,()=>{
  const summary = document.querySelector<HTMLElement>('#form-error')!;
  summary.hidden = true;
  summary.textContent = '';
});
form.addEventListener('submit',async event=>{
  event.preventDefault();
  if (isGenerating) return;
  const collected = renderer.collect();
  const request = buildRequest(template, collected.values);
  const errorElement = document.querySelector<HTMLParagraphElement>('#form-error')!;
  if (collected.errors.length) {
    errorElement.hidden = false; errorElement.textContent = collected.errors[0].message; return;
  }
  let next: PlanInput;
  try { next = toDemoInput(request); }
  catch (error) {
    errorElement.hidden = false;
    errorElement.textContent = error instanceof Error ? error.message : '模板与本地演示字段不匹配。';
    return;
  }
  const error = validateInput(next);
  errorElement.hidden = !error; errorElement.textContent = error ?? '';
  if (error) return;
  isGenerating = true;
  const submitButton = form.querySelector<HTMLButtonElement>('[type="submit"]')!;
  const panel = document.querySelector<HTMLElement>('#generation-panel')!;
  const message = document.querySelector<HTMLElement>('#generation-message')!;
  const stages = ['正在整理你的规划信息…', '正在测算退休资金与资产轨迹…', '正在生成情景对比与规划解读…'];
  submitButton.disabled = true;
  document.querySelector<HTMLElement>('.profile-card')!.hidden = true;
  document.querySelector<HTMLElement>('#results')!.hidden = true;
  document.querySelector<HTMLElement>('#export-button')!.hidden = true;
  panel.classList.remove('generation-exit');
  panel.hidden = false;
  window.scrollTo({top: 0, behavior: 'instant'});
  document.querySelector<HTMLElement>('#generation-title')!.focus({preventScroll:true});
  try {
    for (const [index, stage] of stages.entries()) {
      message.textContent = stage;
      panel.querySelectorAll('.generation-steps > span').forEach((item, step) => {
        item.classList.toggle('active', step === index);
        item.classList.toggle('complete', step < index);
      });
      await new Promise<void>(resolve => setTimeout(resolve, reducedMotion ? 0 : 600));
    }
    currentInput = next; submittedRequest = request; activeScenario = 1;
    renderResults(); hasGeneratedPlan = true;
    panel.classList.add('generation-exit');
    if (!reducedMotion) await new Promise<void>(resolve => setTimeout(resolve, 400));
    panel.hidden = true;
    panel.classList.remove('generation-exit');
    showView('results');
    toast('规划已生成，可以随时返回修改信息。');
  } catch {
    panel.hidden = true; showView('form');
    errorElement.hidden = false;
    errorElement.textContent = '生成规划遇到问题，请检查填写信息后重试。';
  } finally {
    panel.classList.remove('generation-exit');
    isGenerating = false;
    submitButton.disabled = false;
  }
});
let isExporting = false;
document.querySelector('#export-button')!.addEventListener('click',async ()=>{
  if (isExporting || !hasGeneratedPlan || document.querySelector<HTMLElement>('#results')!.hidden) return;
  const button = document.querySelector<HTMLButtonElement>('#export-button')!;
  const snapshot = {...currentInput};
  isExporting = true; button.disabled = true;
  button.textContent = '正在生成 PDF…';
  button.setAttribute('aria-busy', 'true');
  try {
    const { createPlanPdf } = await import('./pdf-export');
    const bytes = await createPlanPdf(snapshot);
    const url = URL.createObjectURL(new Blob([new Uint8Array(bytes).buffer], {type:'application/pdf'}));
    const anchor = document.createElement('a');
    anchor.href = url; anchor.download = 'RetireNest-退休规划.pdf';
    document.body.append(anchor); anchor.click(); anchor.remove();
    setTimeout(()=>URL.revokeObjectURL(url),30000);
    toast('退休规划 PDF 已生成，下载已开始。');
  } catch {
    toast('PDF 生成失败，请重试。');
  } finally {
    isExporting = false;
    button.disabled = document.querySelector<HTMLElement>('#results')!.hidden;
    button.innerHTML = icon('download') + '导出规划';
    button.removeAttribute('aria-busy');
  }
});
for (const id of ['close-help','understood-button']) document.querySelector(`#${id}`)!.addEventListener('click',()=>document.querySelector<HTMLDialogElement>('#help-dialog')!.close());
function showView(view: 'form' | 'results') {
  const isResults = view === 'results';
  document.querySelector<HTMLElement>('.profile-card')!.hidden = isResults;
  document.querySelector<HTMLElement>('#results')!.hidden = !isResults;
  const exportButton = document.querySelector<HTMLButtonElement>('#export-button')!;
  exportButton.hidden = !isResults;
  exportButton.disabled = !isResults || isExporting;
  exportButton.title = isResults ? '导出当前规划摘要' : '生成规划后可导出';
  window.scrollTo({top: 0, behavior: 'instant'});
  document.querySelector<HTMLElement>(isResults ? '#result-title' : '#profile-title')!.focus({preventScroll:true});
}
function showForm() { showView('form'); }
document.querySelector('.brand')!.addEventListener('click', event => {
  event.preventDefault(); if (!isGenerating) showForm();
});

const intro = document.querySelector<HTMLElement>('#startup-intro')!;
const shell = document.querySelector<HTMLElement>('.shell')!;
let introClosing = false;
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
function finishIntro() {
  if (introClosing) return;
  introClosing = true;
  clearTimeout(introTimer);
  shell.inert = false;
  intro.classList.add('intro-exit');
  document.body.classList.remove('intro-active');
  document.querySelector<HTMLElement>('#profile-title')!.focus({preventScroll:true});
  setTimeout(()=>intro.remove(), reducedMotion ? 0 : 400);
}
const introTimer = setTimeout(finishIntro, reducedMotion ? 0 : 2600);
document.querySelector('#skip-intro')!.addEventListener('click',finishIntro);
intro.addEventListener('keydown',event => {if (event.key === 'Escape') finishIntro();});
if (!reducedMotion) {
  document.body.classList.add('intro-active');
  document.querySelector<HTMLButtonElement>('#skip-intro')!.focus({preventScroll:true});
}
