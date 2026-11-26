(() => {
  if (window !== top) return;
  function selector(el) {
    if (el === document.documentElement) return 'html';
    for (const key of ['data-testid', 'id', 'name']) {
      const value = el.getAttribute(key);
      if (!value) continue;
      const css = el.localName + '[' + key + '=' + CSS.escape(value) + ']';
      if (document.querySelectorAll(css).length === 1) return css;
    }
    const path = [];
    while (el && el !== document.documentElement) {
      const siblings = [...el.parentElement.children].filter(n => n.localName === el.localName);
      path.unshift(el.localName + ':nth-of-type(' + (siblings.indexOf(el) + 1) + ')');
      el = el.parentElement;
    }
    return 'html > ' + path.join(' > ');
  }
  document.addEventListener('focusin', event => {
    const el = event.target;
    if (!event.isTrusted || !(el instanceof HTMLInputElement)) return;  // the control bar is a shadow host, not an input
    let kind;
    if (el.type === 'password') kind = 'password';
    else if (['text', 'email'].includes(el.type) &&
             (el.type === 'email' || /username|user.name|login|email/i.test([el.autocomplete, el.id, el.name].join(' ')))) kind = 'username';
    if (kind) window.recordAction({action: 'accountFocus', kind, selector: selector(el), url: location.href});
  }, true);
  // A press held still for HOLD_MS becomes a hold step, and one moved over DRAG_MOVE onto another
  // element becomes a drag step, instead of a click.
  const HOLD_MS = 600, HOLD_MOVE = 6, DRAG_MOVE = 20;
  let press = null, skipClickUntil = 0, html5 = null, lastOver = null;
  // The element a drag is about: the draggable item, or a nearby element with a stable id.
  function anchor(el) {
    const marked = el.closest('[draggable=true]');
    if (marked) return marked;
    for (let node = el, depth = 0; node && depth < 3; node = node.parentElement, depth++)
      if (node.id || node.hasAttribute('data-testid')) return node;
    return el;
  }
  const ignored = el => !(el instanceof Element) || el.localName === 'clicker-bot-overlay' ||
                        el === document.body || el === document.documentElement;
  function recordDrag(source, target) {
    window.recordAction({action: 'drag', url: location.href, selector: source, to: selector(anchor(target)),
                         tag: 'drag'});
  }
  document.addEventListener('pointerdown', event => {
    const el = event.target;
    press = event.isTrusted && event.button === 0 && !ignored(el)
      ? {target: el, x: event.clientX, y: event.clientY, at: performance.now(),
         // Taken now: the element may move or be re-rendered while it is dragged.
         source: selector(anchor(el)),
         canDrag: !el.closest('input,textarea,select,[contenteditable=""],[contenteditable=true]')}
      : null;
  }, true);
  document.addEventListener('pointerup', event => {
    const start = press;
    press = null;
    if (!start || !event.isTrusted) return;
    const held = performance.now() - start.at;
    const moved = Math.hypot(event.clientX - start.x, event.clientY - start.y);
    if (moved > DRAG_MOVE) {
      if (!start.canDrag || String(getSelection())) return;  // selecting text, not dragging
      const sourceEl = start.target.isConnected ? anchor(start.target) : null;
      const below = document.elementsFromPoint(event.clientX, event.clientY)
        .find(el => !ignored(el) && !(sourceEl && sourceEl.contains(el)));
      if (!below) return;
      skipClickUntil = performance.now() + 400;
      recordDrag(start.source, below);
      return;
    }
    if (held < HOLD_MS || moved > HOLD_MOVE) return;
    skipClickUntil = performance.now() + 400;  // the click the browser fires on release
    const el = start.target.closest('button,a,input,select,textarea,[role=button]') || start.target;
    window.recordAction({action: 'hold', url: location.href, selector: selector(el), tag: el.localName,
                         duration: Math.min(30, Math.round(held / 100) / 10)});
  }, true);
  // Native (HTML5) drag and drop: the browser sends no pointerup or click for it.
  document.addEventListener('dragstart', event => {
    press = null;
    const el = event.isTrusted && !ignored(event.target) ? anchor(event.target) : null;
    // Where it sat, to notice lists that move the item while it is dragged (SortableJS and the like).
    html5 = el && {el, source: selector(el), parent: el.parentElement, index: indexIn(el)};
    lastOver = null;
  }, true);
  document.addEventListener('dragover', event => {
    if (html5 && !ignored(event.target)) lastOver = event.target;
  }, true);
  function indexIn(el) {
    return el.parentElement ? [...el.parentElement.children].indexOf(el) : -1;
  }
  function finishHtml5(target) {
    const {el, source, parent, index} = html5;
    html5 = null;
    skipClickUntil = performance.now() + 400;
    // A list moved the item while it was dragged: the drop lands on the item or the list itself, so
    // record its new place instead; on replay, drop onto whatever holds that place.
    const now = indexIn(el);
    if (parent && el.parentElement === parent && now !== index && now >= 0)
      return window.recordAction({action: 'drag', url: location.href, selector: source,
                                  to: selector(parent) + ' > :nth-child(' + (now + 1) + ')', tag: 'drag'});
    if (target && !el.contains(target)) recordDrag(source, target);
  }
  document.addEventListener('drop', event => {
    if (html5 && !ignored(event.target)) finishHtml5(event.target);
  }, true);
  document.addEventListener('dragend', () => {
    // No drop event: the page did not accept the drop, or a list moved the item under the pointer.
    if (html5) finishHtml5(lastOver);
    lastOver = null;
  }, true);
  function record(event) {
    if (!event.isTrusted || !(event.target instanceof Element)) return;
    if (event.target.localName === 'clicker-bot-overlay') return;  // Bitir / İptal / Durdur bar
    if (event.type === 'click' && performance.now() < skipClickUntil) return;
    let el = event.target;
    const action = event.type;
    const step = {action, url: location.href};
    if (action === 'click') {
      el = el.closest('button,a,input,select,textarea,[role=button]') || el;
      Object.assign(step, {x: event.clientX, y: event.clientY, scrollX, scrollY});
      if (el.matches('canvas,svg')) {
        const box = el.getBoundingClientRect();
        step.position = {x: event.clientX - box.left - el.clientLeft, y: event.clientY - box.top - el.clientTop};
      }
    } else if (action === 'change') {
      if (!el.matches('select')) return;
      step.action = 'select';
      step.values = Array.from(el.selectedOptions, option => option.value);
    } else if (action === 'keydown') {
      if (event.key !== 'Enter' || !el.matches('input')) return;
    } else {
      if (!el.matches('textarea,input:not([type]),input:is([type=text],[type=email],[type=search],[type=tel],[type=url],[type=number])')) return;
      if (/cc-|one-time-code|password/i.test(el.autocomplete)) return;
      step.value = el.value;
    }
    Object.assign(step, {selector: selector(el), tag: el.localName});
    window.recordAction(step);
  }
  for (const event of ['click', 'input', 'change', 'keydown']) document.addEventListener(event, record, true);
})();
