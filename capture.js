(() => {
  if (window !== top) return;
  function selector(el) {
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
    if (!event.isTrusted || !(el instanceof HTMLInputElement)) return;
    let kind;
    if (el.type === 'password') kind = 'password';
    else if (['text', 'email'].includes(el.type) &&
             (el.type === 'email' || /username|user.name|login|email/i.test([el.autocomplete, el.id, el.name].join(' ')))) kind = 'username';
    if (kind) window.recordAction({action: 'accountFocus', kind, selector: selector(el), url: location.href});
  }, true);
  function record(event) {
    if (!event.isTrusted || !(event.target instanceof Element)) return;
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
