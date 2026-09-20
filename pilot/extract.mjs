import { JSDOM, VirtualConsole } from 'jsdom';
import { computeAccessibleName, getRole } from 'dom-accessibility-api';
import { createHash } from 'node:crypto';

export const hash = s => createHash('sha256').update(s).digest('hex');
const clean = s => (s || '').replace(/\s+/g, ' ').trim();
const options = { computedStyleSupportsPseudoElements: false };
export function extract(html, url, source = {}) {
  const dom = new JSDOM(html, { url, virtualConsole: new VirtualConsole() });
  const d = dom.window.document;
  const result = [];
  const seen = new Set();
  for (const el of d.querySelectorAll('button,a[href],input,select,textarea,img,[role="button"],[role="link"]')) {
    if (el.closest('[hidden],[inert],[aria-hidden="true"],template') || el.matches('input[type="hidden"]')) continue;
    const original = clean(computeAccessibleName(el, options));
    if (!original || original.length > 120) continue;
    // Mask only explicit name attributes. Keep naturally named text controls out
    // of this benchmark; they are already accessible without an injected name.
    const saved = [];
    for (const n of [el, ...el.querySelectorAll('*')]) {
      for (const attr of ['aria-label', 'aria-labelledby', 'alt']) {
        if (n.hasAttribute(attr)) { saved.push([n, attr, n.getAttribute(attr)]); n.removeAttribute(attr); }
      }
    }
    let masked;
    try {
      if (computeAccessibleName(el, options).trim()) continue;
      const clone = el.cloneNode(true);
      clone.querySelectorAll('script,style,template').forEach(n => n.remove());
      for (const n of [clone, ...clone.querySelectorAll('*')]) {
        for (const a of [...n.attributes]) {
          if (!['id','class','name','type','role','href','src','data-tooltip','data-action'].includes(a.name)) n.removeAttribute(a.name);
          else if (['href','src'].includes(a.name)) {
            try { n.setAttribute(a.name, new URL(a.value, url).pathname); } catch { n.removeAttribute(a.name); }
          }
        }
      }
      masked = clone.outerHTML.slice(0, 1200);
    } finally { for (const [n, a, v] of saved) n.setAttribute(a, v); }
    const key = hash(masked);
    if (seen.has(key)) continue;
    seen.add(key);
    const siblings = [...(el.parentElement?.children || [])].filter(n => n !== el)
      .map(n => clean(computeAccessibleName(n, options))).filter(n => n && n !== original).slice(0, 3);
    const heading = clean(el.closest('section,article,main,nav,form')?.querySelector('h1,h2,h3')?.textContent);
    result.push({id:hash(url+'\n'+key).slice(0,20), source:{...source,url}, reference:original,
      input:{kind:getRole(el)||el.tagName.toLowerCase(), html:masked,
        context:{title:clean(d.title).slice(0,120), lang:d.documentElement.lang||'und',
          heading:heading===original?'':heading.slice(0,120), siblings,
          landmark:el.closest('nav,main,aside,form,header,footer')?.tagName.toLowerCase()||''}}});
  }
  dom.window.close();
  return result;
}
