import { PDFDocument, PageSizes } from 'pdf-lib';
import type { PlanInput, PlanResult } from './model';
import type { PlanScenario } from './plan-contract';

// Render at twice A4 CSS resolution to preserve local Chinese fonts without
// shipping a large font file. Each page is embedded as a high-resolution image.
const W = 794, H = 1123;
const green = '#24573f', muted = '#7c8b77', line = '#e4eadf';
const yuan = (n: number) => Math.round(n).toLocaleString('zh-CN') + ' 元';
const wan = (n: number) => (n / 10000).toFixed(1) + ' 万元';
const font = '"Microsoft YaHei", "PingFang SC", sans-serif';

class ReportPage {
  readonly canvas = document.createElement('canvas');
  readonly ctx: CanvasRenderingContext2D;
  constructor(title: string, page: number, date: string) {
    this.canvas.width = W * 2; this.canvas.height = H * 2;
    const ctx = this.canvas.getContext('2d');
    if (!ctx) throw new Error('浏览器不支持报告绘制');
    this.ctx = ctx; ctx.scale(2, 2);
    this.box(0, 0, W, H, '#ffffff');
    this.box(0, 0, W, 8, green);
    this.text('退有所算', 48, 52, 25, green, true);
    this.text('RETIRENEST / 退休规划报告', 49, 78, 10, muted);
    this.text(date, 746, 54, 10, muted, false, 'right');
    this.rule(101);
    this.text(title, 48, 143, 23, green, true);
    this.rule(1069);
    this.text('本地后端测算 · 金额均以今天的购买力计价 · 不构成投资建议', 48, 1092, 9, muted);
    this.text(`${page} / 2`, 746, 1092, 10, muted, false, 'right');
  }
  text(value: string, x: number, y: number, size = 12, color = '#344b37', bold = false, align: CanvasTextAlign = 'left', maxWidth?: number) {
    const ctx = this.ctx;
    ctx.font = `${bold ? 600 : 400} ${size}px ${font}`;
    ctx.fillStyle = color; ctx.textAlign = align;
    ctx.fillText(value, x, y, maxWidth);
  }
  paragraph(value: string, x: number, y: number, width: number, size = 12, color = muted, leading = 22) {
    const ctx = this.ctx; ctx.font = `400 ${size}px ${font}`;
    let row = '', baseline = y;
    for (const char of value) {
      if (char === '\n' || ctx.measureText(row + char).width > width) {
        this.text(row, x, baseline, size, color); baseline += leading; row = '';
        if (char === '\n') continue;
      }
      row += char;
    }
    if (row) this.text(row, x, baseline, size, color);
    return baseline + leading;
  }
  box(x: number, y: number, width: number, height: number, color: string) {
    this.ctx.fillStyle = color; this.ctx.fillRect(x, y, width, height);
  }
  rule(y: number, x = 48, width = 698) {
    this.ctx.strokeStyle = line; this.ctx.lineWidth = 1;
    this.ctx.beginPath(); this.ctx.moveTo(x, y); this.ctx.lineTo(x + width, y); this.ctx.stroke();
  }
  title(title: string, y: number) { this.text(title, 48, y, 15, green, true); }
}

function drawChart(page: ReportPage, input: PlanInput, result: PlanResult) {
  const ctx = page.ctx, left = 105, right = 728, top = 762, bottom = 964;
  const maximum = Math.max(10000, result.target * 1.1, ...result.points.map(p => p.assets));
  const minimum = Math.min(0, ...result.points.map(p => p.assets)) * 1.05;
  const x = (age: number) => left + (age - input.age) / (input.lifeExpectancy - input.age) * (right - left);
  const y = (amount: number) => top + (maximum - amount) / (maximum - minimum) * (bottom - top);
  ctx.save();
  page.box(x(input.retirementAge), top, right - x(input.retirementAge), bottom - top, '#f5f7ef');
  for (let i = 0; i < 4; i++) {
    const amount = minimum + (maximum - minimum) * i / 3;
    page.rule(y(amount), left, right - left);
    page.text((amount / 10000).toFixed(0) + '万', left - 10, y(amount) + 4, 9, muted, false, 'right');
  }
  ctx.strokeStyle = '#b59863'; ctx.setLineDash([5, 4]);
  ctx.beginPath(); ctx.moveTo(left, y(result.target)); ctx.lineTo(right, y(result.target)); ctx.stroke();
  ctx.setLineDash([]);
  page.text('退休目标 ' + wan(result.target), right, y(result.target) - 8, 9, '#a08753', false, 'right');
  result.points.forEach((point, index) => {
    if (index === 0) return;
    const previous = result.points[index - 1];
    ctx.strokeStyle = point.age <= input.retirementAge ? '#327359' : '#8ca47d'; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.moveTo(x(previous.age), y(previous.assets)); ctx.lineTo(x(point.age), y(point.assets)); ctx.stroke();
  });
  ctx.strokeStyle = '#8ca47d'; ctx.lineWidth = 1; ctx.setLineDash([3, 4]);
  ctx.beginPath(); ctx.moveTo(x(input.retirementAge), top); ctx.lineTo(x(input.retirementAge), bottom); ctx.stroke();
  ctx.setLineDash([]);
  for (const age of [input.age, input.retirementAge, input.lifeExpectancy]) {
    page.text(`${age}岁${age === input.retirementAge ? '退休' : ''}`, x(age), bottom + 20, 10, muted, false, 'center');
  }
  ctx.restore();
}

export async function createPlanPdf(input: PlanInput, result: PlanResult, scenarios: PlanScenario[], explanation: string): Promise<Uint8Array> {
  await document.fonts.ready;
  const date = new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false });
  const first = new ReportPage('你的退休规划概览', 1, date);
  first.paragraph(`${input.city} · 当前 ${input.age} 岁 · 期望 ${input.retirementAge} 岁退休 · 规划至 ${input.lifeExpectancy} 岁`, 48, 174, 698, 12);
  const cards = [
    ['退休所需资金', wan(result.target)],
    ['退休时预计资产', wan(result.projected)],
    [result.gap > 0 ? '还需准备' : '预计资金余量', wan(result.gap > 0 ? result.gap : result.projected - result.target)],
  ];
  cards.forEach(([label, value], index) => {
    const x = 48 + index * 237;
    first.box(x, 209, 224, 99, '#f2f6ec');
    first.text(label, x + 16, 236, 11, muted);
    first.text(value, x + 16, 277, 25, index === 2 ? '#a08753' : green, true, 'left', 191);
  });
  first.text(`目标准备度 ${result.coverage.toFixed(0)}%`, 48, 340, 13, green, true);
  first.paragraph(`距离退休还有 ${result.yearsToRetirement} 年。当前每月结余 ${yuan(result.monthlySurplus)}，覆盖目标所需每月结余约 ${yuan(result.requiredMonthlySaving)}。`, 48, 370, 698, 12);
  first.title('01 / 你的规划信息', 438);
  const rows = [
    ['当前月收入', yuan(input.monthlyIncome), '当前月支出', yuan(input.monthlyExpense)],
    ['现有总资产', yuan(input.assets), '现有总负债', yuan(input.debt)],
    ['退休后月支出', yuan(input.retirementExpense), '预估月养老金', yuan(input.monthlyPension)],
    ['名义年回报', input.nominalReturn + '%', '年通胀率', input.inflation + '%'],
  ];
  rows.forEach((row, index) => {
    const y = 478 + index * 43;
    first.text(row[0], 48, y, 11, muted); first.text(row[1], 365, y, 13, green, false, 'right', 190);
    first.text(row[2], 414, y, 11, muted); first.text(row[3], 746, y, 13, green, false, 'right', 190);
    first.rule(y + 14);
  });
  first.title('02 / 资产变化轨迹', 706);
  first.text('深绿：资产积累期    浅绿：退休支取期    虚线：退休资金目标', 48, 731, 10, muted);
  drawChart(first, input, result);
  first.paragraph(result.depletedAge ? `当前路径下，资产预计在 ${result.depletedAge} 岁出现不足。可调整收支或退休年龄，再观察目标变化。` : `当前假设下，资产可支持至规划终点 ${input.lifeExpectancy} 岁。`, 48, 1019, 698, 11);

  const second = new ReportPage('情景对比与测算说明', 2, date);
  second.title('03 / 三种可能的未来', 192);
  second.text('仅调整名义年回报，其余条件保持一致。', 48, 218, 11, muted);
  const headers = ['情景', '名义年回报', '退休资金目标', '预计退休资产', '资金缺口'];
  const columns = [62, 197, 335, 493, 654];
  second.box(48, 240, 698, 39, green);
  headers.forEach((header, i) => second.text(header, columns[i], 265, 11, '#ffffff'));
  scenarios.forEach((scenario, index) => {
    const y = 279 + index * 55;
    second.box(48, y, 698, 55, index % 2 === 0 ? '#f3f6ee' : '#ffffff');
    [scenario.label, scenario.nominal_return.toFixed(1) + '%', wan(scenario.target), wan(scenario.projected), scenario.gap > 0 ? wan(scenario.gap) : '已覆盖'].forEach((value, i) => second.text(value, columns[i], y + 33, 11, green, false, 'left', i === 4 ? 80 : 130));
  });
  second.title('04 / 规划解读', 495);
  second.paragraph(explanation, 48, 526, 698, 12);
  second.title('05 / 测算口径与假设', 640);
  const notes = [
    '金额统一以今天的购买力表示。实际年回报 = (1 + 名义年回报) / (1 + 通胀率) - 1。',
    '假设工资、支出和养老金随通胀同步变化。养老金为用户自填假设，视为自退休起持续领取，城市不参与计算。',
    '当前净资产 = 总资产 - 总负债。工作期每年年末计入全年结余；退休后每年年末支取 max(退休月支出 - 月养老金, 0) × 12。',
    '退休资金目标为退休后净支出的折现总额；预计资产为净资产和未来结余在退休时的累积值。',
    '负债直接抵减资产，不另算利息；不计税费、收益波动及政策变化。图表中的负资产用于展示资金不足。',
  ];
  let y = 671;
  notes.forEach((note, index) => { y = second.paragraph(`${index + 1}. ${note}`, 48, y, 698, 11, muted, 21) + 10; });
  second.box(48, 961, 698, 73, '#f3f6ee');
  second.paragraph('本报告由本地后端测算服务生成，尚未接入 AI。医疗、养老、存款等扩展信息本期未参与计算。结果用于比赛展示和学习，不构成投资建议或真实养老金测算。', 64, 987, 666, 11, muted, 21);
  const pdf = await PDFDocument.create();
  pdf.setTitle('退有所算 - 退休规划报告');
  pdf.setAuthor('RetireNest'); pdf.setSubject('个人退休规划与情景分析'); pdf.setLanguage('zh-CN');
  for (const report of [first, second]) {
    const image = await pdf.embedPng(report.canvas.toDataURL('image/png'));
    const page = pdf.addPage(PageSizes.A4);
    page.drawImage(image, { x: 0, y: 0, width: page.getWidth(), height: page.getHeight() });
    report.canvas.width = 0; report.canvas.height = 0;
  }
  return pdf.save();
}
