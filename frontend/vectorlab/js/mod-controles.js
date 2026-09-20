// mod-controles.js — contrôles maison des panneaux (finitions UI, 20/09/2026) :
// <vl-curseur> (piste 4 px, poignée ronde, valeur éditable, molette ±1,
// Maj ±10), <vl-curseur-couleur> (pastille colorée, mode="teinte" = roue des
// teintes), <vl-bascule> (interrupteur) et la rangée `.vl-rangee` (boutons à
// largeurs égales). Ils exposent `value` / `checked` et émettent `input` /
// `change` bubbling : les modules gardent leurs écouteurs, seuls les gabarits
// changent. En tête, les fonctions PURES bancables ; VL.ergonomie mesure les
// rangées visibles des panneaux visés et `auditer` juge (pur).

const _arrondi = (v, step) => {
  const s = step > 0 ? step : 1;
  const d = Math.max(0, -Math.floor(Math.log10(s)));
  return +(Math.round(v / s) * s).toFixed(d + 2);
};

export function curseur_valeur(x, w, { min, max, step = 1 }) {
  if (!(w > 0)) return min;
  const f = Math.max(0, Math.min(1, x / w));
  return Math.max(min, Math.min(max, _arrondi(min + f * (max - min), step)));
}

export function curseur_position(v, { min, max }) {
  if (!(max > min)) return 0;
  return Math.max(0, Math.min(1, (v - min) / (max - min)));
}

export function curseur_pas(v, sens, { min, max, step = 1 }, maj = false) {
  return Math.max(min, Math.min(max, _arrondi(v + sens * step * (maj ? 10 : 1), step)));
}

export function rangee_largeurs(n, total, gap) {
  if (!(n > 0)) return [];
  const libre = total - gap * (n - 1), base = Math.floor(libre / n);
  let reste = libre - base * n;
  return Array.from({ length: n }, () => base + (reste-- > 0 ? 1 : 0));
}

export function auditer(mesures) {
  const v = [];
  for (const m of mesures || []) {
    if (m.scrollWidth > m.clientWidth + 1) v.push({ ligne: m.id, panneau: m.panneau, type: "deborde", detail: `${m.scrollWidth} > ${m.clientWidth}` });
    for (const c of m.controles || []) {
      if (c.tag === "input" && (c.type === "range" || c.type === "checkbox")) v.push({ ligne: m.id, panneau: m.panneau, type: "natif", detail: c.type });
      if (c.h < 28) v.push({ ligne: m.id, panneau: m.panneau, type: "petit", detail: `${c.tag} ${c.h}px` });
    }
    const ws = (m.boutons || []).map((b) => b.w);
    if (ws.length > 1 && Math.max(...ws) - Math.min(...ws) > 1) v.push({ ligne: m.id, panneau: m.panneau, type: "inegal", detail: ws.join("/") });
  }
  return v;
}

/* ── DOM ── */
export function initControles(VL) {
  if (typeof customElements === "undefined" || customElements.get("vl-curseur")) return;
  const num = (el, a, d) => { const v = parseFloat(el.getAttribute(a)); return Number.isFinite(v) ? v : d; };

  class VlCurseur extends HTMLElement {
    static get observedAttributes() { return ["value", "min", "max", "step", "disabled"]; }
    connectedCallback() {
      if (this._pret) { this._peindre(); return; }
      this._pret = true;
      this.tabIndex = this.hasAttribute("disabled") ? -1 : 0;
      this.setAttribute("role", "slider");
      this.innerHTML = `<span class="vl-curseur-piste"><span class="vl-curseur-plein"></span><span class="vl-curseur-poignee"></span></span><input class="vl-curseur-val" type="text" inputmode="decimal" aria-label="valeur">`;
      this._val = this.querySelector(".vl-curseur-val");
      const piste = this.querySelector(".vl-curseur-piste");
      const poser = (ev, fin) => {
        const r = piste.getBoundingClientRect();
        this._poser(curseur_valeur(ev.clientX - r.left, r.width, this._echelle()), fin);
      };
      piste.addEventListener("pointerdown", (ev) => {
        if (this.hasAttribute("disabled")) return;
        ev.preventDefault(); this.focus();
        try { piste.setPointerCapture(ev.pointerId); } catch (e) { /* synthétique */ }
        this._glisse = true; poser(ev, false);
      });
      piste.addEventListener("pointermove", (ev) => { if (this._glisse) poser(ev, false); });
      piste.addEventListener("pointerup", (ev) => { if (!this._glisse) return; this._glisse = false; poser(ev, true); });
      this.addEventListener("keydown", (ev) => {
        const s = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1 }[ev.key];
        if (s && ev.target !== this._val) { ev.preventDefault(); ev.stopPropagation(); this._poser(curseur_pas(this.value, s, this._echelle(), ev.shiftKey), true); }
      });
      this.addEventListener("wheel", (ev) => {
        if (ev.target === this._val || this.hasAttribute("disabled")) return;
        ev.preventDefault();
        this._poser(curseur_pas(this.value, ev.deltaY < 0 ? 1 : -1, this._echelle(), ev.shiftKey), true);
      }, { passive: false });
      this._val.addEventListener("change", () => {
        const v = parseFloat(String(this._val.value).replace(",", "."));
        if (Number.isFinite(v)) this._poser(curseur_pas(v, 0, this._echelle()), true); else this._peindre();
      });
      this._val.addEventListener("keydown", (ev) => { ev.stopPropagation(); if (ev.key === "Enter") this._val.blur(); });
      this._peindre();
    }
    attributeChangedCallback() { if (this._pret && !this._glisse) this._peindre(); }
    _echelle() { return { min: num(this, "min", 0), max: num(this, "max", 100), step: num(this, "step", 1) }; }
    get value() { return num(this, "value", this._echelle().min); }
    set value(v) { this.setAttribute("value", String(v)); }
    _poser(v, fin) {
      const avant = this.value;
      this.setAttribute("value", String(v)); this._peindre();
      if (v !== avant || fin) this.dispatchEvent(new Event("input", { bubbles: true }));
      if (fin) this.dispatchEvent(new Event("change", { bubbles: true }));
    }
    _peindre() {
      if (!this._val) return;
      const e = this._echelle(), f = curseur_position(this.value, e);
      this.style.setProperty("--vl-f", String(f));
      this.setAttribute("aria-valuemin", String(e.min)); this.setAttribute("aria-valuemax", String(e.max)); this.setAttribute("aria-valuenow", String(this.value));
      if (document.activeElement !== this._val) this._val.value = String(this.value);
    }
  }

  class VlCurseurCouleur extends HTMLElement {
    // mode="teinte" : piste = roue des teintes, value = 0..359 ; sinon pastille
    // de la couleur (clic = nuancier maison, double-clic = sélecteur système).
    static get observedAttributes() { return ["value", "class"]; }
    connectedCallback() {
      if (this._pret) { this._peindre(); return; }
      this._pret = true;
      const teinte = this.getAttribute("mode") === "teinte";
      this.innerHTML = teinte
        ? `<span class="vl-curseur-piste vl-teintes"><span class="vl-curseur-poignee"></span></span>`
        : `<span class="vl-couleur-pastille" title="${this.getAttribute("title") || "Clic : nuancier · double-clic : sélecteur système"}"></span><input type="color" class="vl-couleur-natif" tabindex="-1" aria-hidden="true">`;
      if (teinte) {
        const piste = this.querySelector(".vl-curseur-piste");
        const poser = (ev, fin) => { const r = piste.getBoundingClientRect(); this._poser(curseur_valeur(ev.clientX - r.left, r.width, { min: 0, max: 359, step: 1 }), fin); };
        piste.addEventListener("pointerdown", (ev) => { ev.preventDefault(); try { piste.setPointerCapture(ev.pointerId); } catch (e) { /* synthétique */ } this._glisse = true; poser(ev, false); });
        piste.addEventListener("pointermove", (ev) => { if (this._glisse) poser(ev, false); });
        piste.addEventListener("pointerup", (ev) => { if (!this._glisse) return; this._glisse = false; poser(ev, true); });
      } else {
        const natif = this.querySelector(".vl-couleur-natif"), pastille = this.querySelector(".vl-couleur-pastille");
        if (/^#[0-9a-f]{6}$/i.test(this.getAttribute("value") || "")) natif.value = this.getAttribute("value");
        pastille.addEventListener("dblclick", () => natif.click());
        pastille.addEventListener("click", (ev) => {
          if (ev.detail > 1) return;
          if (VL.ouvrirNuancier) VL.ouvrirNuancier(this.value, (hex) => this._poser(String(hex).toUpperCase(), true), pastille);
        });
        natif.addEventListener("input", () => this._poser(natif.value.toUpperCase(), false));
        natif.addEventListener("change", () => this._poser(natif.value.toUpperCase(), true));
      }
      this._peindre();
    }
    attributeChangedCallback() { if (this._pret) this._peindre(); }
    get value() { const v = this.getAttribute("value"); return this.getAttribute("mode") === "teinte" ? (parseFloat(v) || 0) : (v || "#000000"); }
    set value(v) { this.setAttribute("value", String(v)); }
    _poser(v, fin) {
      this.setAttribute("value", String(v)); this._peindre();
      this.dispatchEvent(new Event("input", { bubbles: true }));
      if (fin) this.dispatchEvent(new Event("change", { bubbles: true }));
    }
    _peindre() {
      if (this.getAttribute("mode") === "teinte") {
        this.style.setProperty("--vl-f", String(curseur_position(this.value, { min: 0, max: 359 })));
        this.style.setProperty("--vl-couleur", `hsl(${this.value} 100% 50%)`);
      } else {
        this.style.setProperty("--vl-couleur", this.classList.contains("vide") ? "transparent" : this.value);
        const n = this.querySelector(".vl-couleur-natif");
        if (n && /^#[0-9a-f]{6}$/i.test(this.value)) n.value = this.value;
      }
    }
  }

  class VlBascule extends HTMLElement {
    static get observedAttributes() { return ["checked"]; }
    connectedCallback() {
      if (this._pret) { this._peindre(); return; }
      this._pret = true;
      this.setAttribute("role", "switch"); this.tabIndex = 0;
      this.innerHTML = `<span class="vl-bascule-piste"><span class="vl-bascule-bouton"></span></span>`;
      this.addEventListener("click", (ev) => { ev.preventDefault(); if (!this.hasAttribute("disabled")) this._basculer(); });
      this.addEventListener("keydown", (ev) => { if (ev.key === " " || ev.key === "Enter") { ev.preventDefault(); ev.stopPropagation(); this._basculer(); } });
      this._peindre();
    }
    attributeChangedCallback() { if (this._pret) this._peindre(); }
    get checked() { return this.hasAttribute("checked"); }
    set checked(v) { if (v) this.setAttribute("checked", ""); else this.removeAttribute("checked"); }
    _basculer() {
      this.checked = !this.checked;
      this.dispatchEvent(new Event("input", { bubbles: true }));
      this.dispatchEvent(new Event("change", { bubbles: true }));
    }
    _peindre() { this.setAttribute("aria-checked", String(this.checked)); }
  }

  customElements.define("vl-curseur", VlCurseur);
  customElements.define("vl-curseur-couleur", VlCurseurCouleur);
  customElements.define("vl-bascule", VlBascule);

  /* ── l'audit in-page : rangées VISIBLES des panneaux visés, jugées par auditer() ── */
  const PANNEAUX = ["#panneauStyle", "#panneauApparence2", "#panneauPixel"];   // le nuancier (popover compact 210 px) est hors audit
  const MAISON = "vl-curseur, vl-bascule, vl-curseur-couleur";
  function mesurer(racines = PANNEAUX) {
    const out = [];
    for (const sel of racines) {
      const p = document.querySelector(sel); if (!p) continue;
      const lignes = [...p.querySelectorAll(".ap-ligne, .vl-rangee, .nu-ligne")]
        .filter((l) => l.getClientRects().length && l.offsetParent !== null);
      lignes.forEach((l, i) => {
        const els = [...l.querySelectorAll("input, select, button, " + MAISON)]
          .filter((c) => c.getClientRects().length)
          .filter((c) => c.matches(MAISON) || !c.closest(MAISON))
          .filter((c) => !c.classList.contains("px-pastille"));
        const controles = els.map((c) => { const r = c.getBoundingClientRect(); return { tag: c.tagName.toLowerCase(), type: c.getAttribute("type") || "", h: r.height, w: r.width, id: c.id || "" }; });
        const boutons = l.matches(".vl-rangee") ? [...l.children].filter((b) => b.tagName === "BUTTON").map((b) => ({ w: b.getBoundingClientRect().width })) : [];
        out.push({ id: `${sel} #${i}${l.id ? " " + l.id : ""}`, panneau: sel, scrollWidth: l.scrollWidth, clientWidth: l.clientWidth, controles, boutons });
      });
    }
    return out;
  }
  VL.ergonomie = { mesurer, auditer: (racines) => auditer(mesurer(racines)), PANNEAUX };
}
