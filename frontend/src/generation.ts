// 三步进度：把「整理画像 → 测算现金流 → 对比策略」的等待过程讲清楚。
export interface GenerationHandle { step: (index: number) => void; close: () => void }

export function openGeneration(stages: string[]): GenerationHandle {
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const panel = document.createElement('section');
  panel.className = 'generation-panel';
  panel.setAttribute('role', 'status');
  panel.setAttribute('aria-live', 'polite');
  panel.innerHTML = `
    <h2 class="generation-title" tabindex="-1">正在为你测算</h2>
    <p class="generation-message">${stages[0] ?? ''}</p>
    <div class="generation-steps">${stages.map(() => '<span></span>').join('')}</div>`;
  document.body.append(panel);
  panel.querySelector<HTMLElement>('.generation-title')!.focus({ preventScroll: true });

  const message = panel.querySelector<HTMLElement>('.generation-message')!;
  const marks = [...panel.querySelectorAll<HTMLElement>('.generation-steps > span')];
  let index = 0;
  const show = (next: number) => {
    index = Math.max(index, Math.min(next, stages.length - 1));
    message.textContent = stages[index] ?? '';
    marks.forEach((item, step) => {
      item.classList.toggle('active', step === index);
      item.classList.toggle('complete', step < index);
    });
  };
  show(0);
  const timer = window.setInterval(() => {
    if (index < stages.length - 1) show(index + 1);
  }, reduced ? 0 : 700);

  return {
    step: show,
    close() {
      window.clearInterval(timer);
      panel.classList.add('generation-exit');
      window.setTimeout(() => panel.remove(), reduced ? 0 : 300);
    },
  };
}
