// 首屏动画：沿用经典页的叶子轨道与两行标题，做成可复用的一次性覆盖层。
const ICONS = {
  leaf: '<path d="M20 3C10 2 3 7 5 15c8 4 15-2 15-12ZM5 20l10-11"/>',
  arrow: '<path d="M5 12h14m-5-5 5 5-5 5"/>',
};
const icon = (name: keyof typeof ICONS) =>
  `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name]}</svg>`;

export function playIntro(durationMs = 2600): void {
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const section = document.createElement('section');
  section.className = 'startup-intro';
  section.id = 'startup-intro';
  section.setAttribute('aria-label', '欢迎来到退有所算');
  section.innerHTML = `
    <div class="intro-orbit" aria-hidden="true"></div>
    <div class="intro-content">
      <span class="intro-leaf">${icon('leaf')}</span>
      <p class="intro-eyebrow">RETIRENEST</p>
      <h1><span class="intro-title-line">给未来的自己</span><span class="intro-title-line">多一点从容</span></h1>
      <p class="intro-caption"><span>从今天的一小步开始</span><span>让理想生活慢慢生长</span></p>
      <span class="intro-line" aria-hidden="true"></span>
    </div>
    <button class="intro-skip" type="button">跳过动画 ${icon('arrow')}</button>`;
  document.body.append(section);
  document.body.classList.add('intro-active');

  let closing = false;
  const finish = () => {
    if (closing) return;
    closing = true;
    window.clearTimeout(timer);
    section.classList.add('intro-exit');
    document.body.classList.remove('intro-active');
    document.querySelector<HTMLElement>('#form-host input, #form-host select')?.focus({ preventScroll: true });
    window.setTimeout(() => section.remove(), reduced ? 0 : 400);
  };
  const timer = window.setTimeout(finish, reduced ? 0 : durationMs);
  section.querySelector<HTMLButtonElement>('.intro-skip')!.addEventListener('click', finish);
  section.addEventListener('keydown', event => { if (event.key === 'Escape') finish(); });
}
