// A frame around the page and a small control bar, so recording and playback can be
// finished or stopped from the browser even when the Clicker Bot window is behind it.
(() => {
  if (window !== top) return;
  const mode = window.__clickerBotMode;
  const host = document.createElement('clicker-bot-overlay');
  const root = host.attachShadow({mode: 'open'});
  root.innerHTML = `<style>
    :host { all: initial; }
    .frame { position: fixed; inset: 0; border: 3px solid #c23430; pointer-events: none; z-index: 2147483646; }
    .bar { position: fixed; right: 16px; bottom: 16px; z-index: 2147483647; display: flex; align-items: center;
           gap: 8px; padding: 6px 6px 6px 14px; background: #302a29; color: #fff; border-radius: 8px;
           font: 600 13px/1.2 -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
           box-shadow: 0 4px 16px rgba(0, 0, 0, .25); }
    .dot { width: 8px; height: 8px; border-radius: 50%; background: #f44336; animation: pulse 1.3s ease-in-out infinite; }
    .bar.left { right: auto; left: 16px; }
    .label { margin-right: 4px; white-space: nowrap; cursor: pointer; }
    button { all: unset; cursor: pointer; padding: 7px 12px; border-radius: 6px; background: #c23430; color: #fff; font: inherit; }
    button.secondary { background: rgba(255, 255, 255, .14); }
    button:hover { filter: brightness(1.12); }
    button:focus-visible { outline: 2px solid #fff; outline-offset: 1px; }
    button:disabled { opacity: .5; cursor: default; }
    @keyframes pulse { 50% { opacity: .35; } }
    @media (prefers-reduced-motion: reduce) { .dot { animation: none; } }
  </style><div class="frame"></div><div class="bar" role="toolbar" aria-label="Clicker Bot"><span class="dot"></span><span class="label" title="Çubuğu diğer köşeye taşı"></span></div>`;
  const bar = root.querySelector('.bar');
  const label = root.querySelector('.label');
  const buttons = [];
  // The bar can cover a page control; clicking its label moves it to the other corner.
  label.addEventListener('click', () => bar.classList.toggle('left'));
  function button(text, command, secondary) {
    const el = document.createElement('button');
    el.textContent = text;
    if (secondary) el.className = 'secondary';
    el.addEventListener('click', () => {
      buttons.forEach(b => { b.disabled = true; });
      label.textContent = command === 'cancel' ? 'İptal ediliyor…' : 'Durduruluyor…';
      window.clickerBotControl(command);
    });
    buttons.push(el);
    bar.append(el);
  }
  if (mode === 'record') {
    label.textContent = 'Kaydediliyor';
    button('Bitir', 'finish');
    button('İptal', 'cancel', true);
  } else {
    label.textContent = 'Oynatılıyor';
    button('Durdur', 'stop');
  }
  window.__clickerBotOverlay = {
    progress: text => { label.textContent = text; },
    visible: shown => { host.style.display = shown ? '' : 'none'; },
  };
  function mount() {
    if (!host.isConnected && document.documentElement) document.documentElement.append(host);
  }
  mount();
  document.addEventListener('DOMContentLoaded', mount);
  setInterval(mount, 1000);
  if (window.clickerBotState) window.clickerBotState().then(text => { if (text) label.textContent = text; });
})();
