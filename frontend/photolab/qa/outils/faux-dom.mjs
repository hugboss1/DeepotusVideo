// qa/outils/faux-dom.mjs — un DOM minuscule pour faire tourner les éditeurs de l'écran sous node (bancs *.test.mjs).
// Juste ce que mod-reglages / mod-dialogue-reglage / mod-courbes touchent : arbre, attributs, dataset, écouteurs,
// propagation vers les parents puis le document, focus (document.activeElement). Aucun rendu, aucune mise en page.
class Noeud {
  constructor(tag, doc) {
    this.tagName = String(tag).toUpperCase();
    this.ownerDocument = doc;
    this.children = []; this.parentNode = null;
    this.attrs = {}; this.dataset = {}; this.style = {}; this._l = {};
    this.hidden = false; this.className = ""; this._texte = ""; this.value = ""; this.checked = false; this.id = "";
    this.disabled = false; this.type = "";
    const cl = new Set();
    this.classList = { add: (c) => cl.add(c), remove: (c) => cl.delete(c), contains: (c) => cl.has(c),
      toggle: (c, oui) => { if (oui === undefined ? !cl.has(c) : oui) cl.add(c); else cl.delete(c); } };
  }
  get textContent() { return this._texte + this.children.map((c) => c.textContent).join(""); }
  set textContent(v) { this.children.forEach((c) => { c.parentNode = null; }); this.children = []; this._texte = String(v); }
  set innerHTML(v) { this.textContent = ""; }
  appendChild(c) { if (c.parentNode) c.remove(); c.parentNode = this; this.children.push(c); return c; }
  append(...cs) { for (const c of cs) this.appendChild(typeof c === "string" ? Object.assign(new Noeud("#text", this.ownerDocument), { _texte: c }) : c); }
  replaceChildren(...cs) { this.textContent = ""; this.append(...cs); }
  insertAdjacentHTML() {}
  remove() { const p = this.parentNode; if (p) { p.children = p.children.filter((x) => x !== this); this.parentNode = null; } }
  contains(n) { for (let x = n; x; x = x.parentNode) if (x === this) return true; return false; }
  get isConnected() { let x = this; while (x.parentNode) x = x.parentNode; return x === this.ownerDocument; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  removeAttribute(k) { delete this.attrs[k]; }
  addEventListener(t, f) { (this._l[t] = this._l[t] || []).push(f); }
  removeEventListener(t, f) { this._l[t] = (this._l[t] || []).filter((g) => g !== f); }
  // Événement qui remonte : la cible, ses parents, puis le document.
  envoyer(type, props = {}) {
    let arret = false;
    const ev = { type, target: this, button: 0, pointerId: 1, clientX: 0, clientY: 0, preventDefault() {}, stopPropagation() { arret = true; }, ...props };
    for (let x = this; x && !arret; x = x.parentNode) (x._l[type] || []).slice().forEach((f) => f(ev));
    return ev;
  }
  querySelector() { return null; }
  querySelectorAll() { return []; }
  getBoundingClientRect() { return { left: 0, top: 0, width: 262, height: 262, right: 262, bottom: 262 }; }
  get offsetWidth() { return 262; }
  get offsetHeight() { return 262; }
  focus() { this.ownerDocument.activeElement = this; }
  blur() { if (this.ownerDocument.activeElement === this) this.ownerDocument.activeElement = this.ownerDocument.body; }
  setPointerCapture() {}
  releasePointerCapture() {}
  // Tous les descendants qui satisfont f (ordre du document).
  tous(f) { const r = []; const voir = (n) => { for (const c of n.children) { if (f(c)) r.push(c); voir(c); } }; voir(this); return r; }
}

export function installerFauxDom() {
  const doc = new Noeud("#document", null);
  doc.ownerDocument = doc;
  doc.createElement = (t) => new Noeud(t, doc);
  doc.createElementNS = (ns, t) => new Noeud(t, doc);
  doc.body = doc.createElement("body");
  doc.appendChild(doc.body);
  doc.activeElement = doc.body;
  globalThis.document = doc;
  globalThis.window = globalThis.window || { addEventListener() {}, removeEventListener() {} };
  globalThis.innerWidth = 1600; globalThis.innerHeight = 1000;
  return doc;
}
