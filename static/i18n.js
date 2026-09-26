'use strict';
// The Portuguese source text is the key. Only registered UI nodes are translated;
// domain names, user labels, raw diagnostics and license texts are never rewritten.
const I18n = (() => {
  let language = 'pt-BR', english = {};
  const bindings = [];
  function t(source, args = {}) {
    const template = language === 'en' ? (english[source] ?? source) : source;
    return template.replace(/\{(\w+)\}/g, (match, key) => args[key] ?? match);
  }
  function capture() {
    const walker = document.createTreeWalker(document.documentElement, NodeFilter.SHOW_TEXT);
    let node;
    while ((node = walker.nextNode())) {
      if (node.parentElement.closest('script,style,pre')) continue;
      const target = node;
      const original = node.textContent, source = original.trim();
      if (Object.hasOwn(english, source)) bindings.push(() => {
        target.textContent = original.replace(source, t(source));
      });
    }
    document.querySelectorAll('[placeholder],[aria-label]').forEach(element => {
      for (const attribute of ['placeholder', 'aria-label']) {
        const source = element.getAttribute(attribute);
        if (Object.hasOwn(english, source)) bindings.push(() => element.setAttribute(attribute, t(source)));
      }
    });
  }
  async function init() {
    const response = await fetch('/en.json');
    if (!response.ok) throw Error('Could not load translations / Não foi possível carregar as traduções.');
    english = await response.json();
    capture();
  }
  function set(value) {
    language = value === 'en' ? 'en' : 'pt-BR';
    document.documentElement.lang = language;
    bindings.forEach(update => update());
    document.getElementById('language').value = language;
  }
  function policy(value) {
    return String(value || '').split(' · ').map(part => t(part)).join(' · ');
  }
  return {init, set, t, policy, get language() { return language; }};
})();
