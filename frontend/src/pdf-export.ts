// 规划报告：把全周期页的摘要、两条曲线与策略对比画到 canvas，再嵌进 A4 PDF。
import { PDFDocument } from 'pdf-lib';

export interface ReportRow { age: number; phase: string; income: number; pension: number; passive: number; expense: number; medical: number; soft: number; assets: number }
export interface ReportVariant { label: string; retirement_age: number; success_rate: number; final_assets: number; affordable_monthly_expense: number }
export interface ReportData {
  pensionMonthly: number;
  finalAssets: number;
  breakEvenAge: number | null;
  depletedAge: number | null;
  successRate: number;
  affordableMonthly: number;
  affordableWorking: number;
  requiredIncome: number | null;
  rows: ReportRow[];
  variants: ReportVariant[];
}

const W = 1240;
const H = 1754;
const GREEN = '#24573f';
const SAGE = '#8ca47d';
const CLAY = '#b89a68';
const INK = '#2f3a2e';

const money = (value: number) => Math.round(value).toLocaleString('zh-CN');
const wan = (value: number) => `${(value / 10000).toFixed(1)} 万`;

function surface(): { canvas: HTMLCanvasElement; ctx: CanvasRenderingContext2D } {
  const canvas = document.createElement('canvas');
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext('2d')!;
  ctx.fillStyle = '#fbfcf9';
  ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = GREEN;
  ctx.fillRect(0, 0, W, 12);
  return { canvas, ctx };
}

function text(ctx: CanvasRenderingContext2D, value: string, x: number, y: number, size: number, color = INK, weight = '400'): void {
  ctx.fillStyle = color;
  ctx.font = `${weight} ${size}px "PingFang SC", "Microsoft YaHei", sans-serif`;
  ctx.fillText(value, x, y);
}

function axes(ctx: CanvasRenderingContext2D, rows: ReportRow[], min: number, max: number, x: number, y: number, w: number, h: number): { sx: (age: number) => number; sy: (value: number) => number } {
  const first = rows[0].age;
  const last = rows[rows.length - 1].age;
  const sx = (age: number) => x + ((age - first) / Math.max(last - first, 1)) * w;
  const sy = (value: number) => y + h - ((value - min) / Math.max(max - min, 1)) * h;
  ctx.strokeStyle = '#e2e7dc';
  ctx.fillStyle = '#8a9683';
  ctx.font = '400 20px "PingFang SC", sans-serif';
  for (let i = 0; i <= 4; i += 1) {
    const value = min + ((max - min) * i) / 4;
    const py = sy(value);
    ctx.beginPath();
    ctx.moveTo(x, py);
    ctx.lineTo(x + w, py);
    ctx.stroke();
    ctx.fillText(`${Math.round(value / 10000)}万`, x - 78, py + 7);
  }
  for (const age of [first, rows[Math.floor(rows.length / 3)].age, rows[Math.floor((rows.length * 2) / 3)].age, last]) {
    ctx.fillText(`${age}岁`, sx(age) - 18, y + h + 34);
  }
  return { sx, sy };
}

function line(ctx: CanvasRenderingContext2D, rows: ReportRow[], key: 'income' | 'pension' | 'passive' | 'expense' | 'assets', color: string, sx: (n: number) => number, sy: (n: number) => number): void {
  ctx.strokeStyle = color;
  ctx.lineWidth = 4;
  ctx.beginPath();
  rows.forEach((row, index) => {
    const px = sx(row.age);
    const py = sy(row[key]);
    if (index === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  });
  ctx.stroke();
}

function coverPage(data: ReportData): HTMLCanvasElement {
  const { canvas, ctx } = surface();
  text(ctx, '退有所算 · 全周期现金流报告', 96, 150, 42, GREEN, '600');
  text(ctx, '基于假设的测算，不构成个性化投资建议', 96, 196, 18, '#7c8874');

  const required = data.requiredIncome === null
    ? '超出可测算范围'
    : `${money(data.requiredIncome)} 元`;
  const cards: [string, string][] = [
    ['退休后月养老金', `${money(data.pensionMonthly)} 元`],
    ['规划终点资产', wan(data.finalAssets)],
    ['成功率', `${(data.successRate * 100).toFixed(1)}%`],
    ['可支撑退休月支出', `${money(data.affordableMonthly)} 元`],
    ['维持支出需要的月收入', required],
    ['可支撑工作期月支出', `${money(data.affordableWorking)} 元`],
  ];
  cards.forEach(([label, value], index) => {
    const x = 96 + (index % 3) * 350;
    const y = 260 + Math.floor(index / 3) * 150;
    ctx.fillStyle = '#ffffff';
    ctx.strokeStyle = '#e2e7dc';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.roundRect(x, y, 330, 120, 14);
    ctx.fill();
    ctx.stroke();
    text(ctx, label, x + 24, y + 46, 20, '#7c8874');
    text(ctx, value, x + 24, y + 92, 30, GREEN, '600');
  });

  text(ctx, '收入与支出', 96, 620, 26, GREEN, '600');
  const all = data.rows.flatMap(row => [row.income, row.pension, row.passive, row.expense]);
  const { sx, sy } = axes(ctx, data.rows, Math.min(...all, 0), Math.max(...all, 1), 180, 660, 960, 260);
  line(ctx, data.rows.filter(row => row.income > 0), 'income', GREEN, sx, sy);
  line(ctx, data.rows.filter(row => row.pension > 0), 'pension', INK, sx, sy);
  line(ctx, data.rows, 'passive', SAGE, sx, sy);
  line(ctx, data.rows, 'expense', CLAY, sx, sy);
  text(ctx, '工资', 180, 992, 18, GREEN);
  text(ctx, '养老金', 300, 992, 18, INK);
  text(ctx, '资产收益', 420, 992, 18, SAGE);
  text(ctx, '支出', 600, 992, 18, CLAY);

  text(ctx, '资产轨迹', 96, 1040, 26, GREEN, '600');
  const assets = data.rows.map(row => row.assets);
  const assetAxes = axes(ctx, data.rows, Math.min(...assets, 0), Math.max(...assets, 1), 180, 1080, 960, 260);
  line(ctx, data.rows, 'assets', SAGE, assetAxes.sx, assetAxes.sy);

  const note = data.depletedAge
    ? `按当前假设，${data.depletedAge} 岁出现资产不足；${data.breakEvenAge ? `${data.breakEvenAge} 岁结余转负。` : ''}`
    : `按当前假设，资产可支撑至 ${data.rows[data.rows.length - 1].age} 岁；${data.breakEvenAge ? `${data.breakEvenAge} 岁结余转负，但资产未耗尽。` : '全程结余为正。'}`;
  text(ctx, note, 96, 1440, 20, '#5d6a56');
  text(ctx, '选档位按区间中值计算，自己填的数按原值计算；养老金由城市、收入档与缴费年限推导；收益率与寿命假设见 docs/data-sources.md。', 96, 1480, 16, '#8a9683');
  return canvas;
}

function strategyPage(data: ReportData): HTMLCanvasElement {
  const { canvas, ctx } = surface();
  text(ctx, '五种活法的对比', 96, 150, 36, GREEN, '600');
  text(ctx, '同一份画像套上不同预设，看退休年龄、成功率与期末资产的差别。', 96, 196, 18, '#7c8874');

  const headers = ['策略', '退休年龄', '成功率', '期末资产', '可支撑退休月支出'];
  const columns = [96, 400, 570, 740, 920];
  headers.forEach((header, index) => text(ctx, header, columns[index], 280, 20, '#7c8874'));
  ctx.strokeStyle = '#e2e7dc';
  ctx.beginPath();
  ctx.moveTo(96, 300);
  ctx.lineTo(1140, 300);
  ctx.stroke();

  data.variants.forEach((variant, index) => {
    const y = 350 + index * 70;
    const cells = [
      variant.label,
      `${variant.retirement_age} 岁`,
      `${(variant.success_rate * 100).toFixed(1)}%`,
      wan(variant.final_assets),
      `${money(variant.affordable_monthly_expense)} 元`,
    ];
    cells.forEach((cell, column) => text(ctx, cell, columns[column], y, 20, column === 0 ? INK : '#4a5548'));
    if (index < data.variants.length - 1) {
      ctx.strokeStyle = '#f0f3e9';
      ctx.beginPath();
      ctx.moveTo(96, y + 26);
      ctx.lineTo(1140, y + 26);
      ctx.stroke();
    }
  });

  const max = Math.max(...data.variants.map(variant => variant.final_assets), 1);
  text(ctx, '期末资产（条形越长越宽裕）', 96, 790, 24, GREEN, '600');
  data.variants.forEach((variant, index) => {
    const y = 840 + index * 64;
    text(ctx, variant.label, 96, y + 18, 19, '#4a5548');
    ctx.fillStyle = '#eef2e9';
    ctx.beginPath();
    ctx.roundRect(300, y, 700, 24, 12);
    ctx.fill();
    ctx.fillStyle = SAGE;
    ctx.beginPath();
    ctx.roundRect(300, y, Math.max(6, (variant.final_assets / max) * 700), 24, 12);
    ctx.fill();
    text(ctx, wan(variant.final_assets), 1020, y + 19, 18, GREEN);
  });

  text(ctx, `成功率 ${(data.successRate * 100).toFixed(1)}%；模拟路径数固定，结果可复现。`, 96, 1200, 18, '#7c8874');
  text(ctx, '口径：金额为名义值，收益率按三档资产配置合成；数据与假设来源见 docs/data-sources.md。', 96, 1240, 16, '#8a9683');
  return canvas;
}

export async function createReportPdf(data: ReportData): Promise<Uint8Array> {
  const pdf = await PDFDocument.create();
  for (const canvas of [coverPage(data), strategyPage(data)]) {
    const image = await pdf.embedPng(canvas.toDataURL('image/png'));
    const page = pdf.addPage([595.28, 841.89]);
    page.drawImage(image, { x: 0, y: 0, width: 595.28, height: 841.89 });
    canvas.width = 0;
    canvas.height = 0;
  }
  return pdf.save();
}
