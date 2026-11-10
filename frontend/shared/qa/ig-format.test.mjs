// t494 (09/11/2026) — dz-ig-format.js : le format Instagram d'un post, joué sur un DOM simulé.
// Séries : lecture, formes, essai_graduation, carrousel (ordre, bornes), depot (accord, sans_fal), erreurs (409, 422,
// panne), fige, idempotence, changement_de_post.
// Lancer : node frontend/shared/qa/ig-format.test.mjs
import { readFileSync } from "node:fs";
import vm from "node:vm";

const SRC = readFileSync(new URL("../dz-ig-format.js", import.meta.url), "utf8");
const DICO = readFileSync(new URL("../dz-i18n-dico.js", import.meta.url), "utf8");

let n = 0;
const echecs = [];
const ok = (nom, cond, detail = "") => { n++; if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 300) : "")); };
const J = (x) => JSON.parse(JSON.stringify(x));
const tick = () => new Promise((r) => setTimeout(r, 10));

class Noeud {
  constructor(tag) { this.tagName = String(tag).toUpperCase(); this.attrs = {}; this.children = []; this.parent = null; this.ec = {}; this._t = ""; this.value = ""; this.checked = false; }
  get firstChild() { return this.children[0] || null; }
  get parentNode() { return this.parent; }
  appendChild(c) { if (c.parent) c.parent.removeChild(c); c.parent = this; this.children.push(c); return c; }
  removeChild(c) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); c.parent = null; return c; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  hasAttribute(k) { return k in this.attrs; }
  removeAttribute(k) { delete this.attrs[k]; }
  set textContent(t) { this.children.forEach((c) => { c.parent = null; }); this.children = []; this._t = String(t); }
  get textContent() { return this._t + this.children.map((c) => c.textContent).join(""); }
  set innerHTML(v) { throw new Error("innerHTML interdit"); }
  addEventListener(t, f) { (this.ec[t] = this.ec[t] || []).push(f); }
  fire(t) { (this.ec[t] || []).forEach((f) => f({ type: t, target: this, preventDefault() {} })); }
  click() { if (!("disabled" in this.attrs)) this.fire("click"); }
  *tous() { yield this; for (const c of this.children) yield* c.tous(); }
}
const tous = (r, p) => [...r.tous()].filter(p);
const marques = (r, v) => tous(r, (x) => x.attrs["data-dz-igformat"] === v);
const marque = (r, v) => marques(r, v)[0];
const txt = (x) => (x ? x.textContent : "");

const ctxD = { window: {} };
vm.createContext(ctxD);
vm.runInContext(DICO, ctxD);
const D = ctxD.window.DZ_I18N;
const FR = (cle, vars) => {
  let s = (D[cle] || {}).fr || cle;
  if (vars) s = s.replace(/\{(\w+)\}/g, (m, k) => (vars[k] != null ? String(vars[k]) : m));
  return s;
};
const reponse = (status, json) => ({ ok: status >= 200 && status < 300, status, json: async () => J(json === undefined ? {} : json) });

function monde({ format = {}, reglage = {}, put = null, panne = false } = {}) {
  const appels = [];
  const etat = {
    reglage: Object.assign({ depot_fal: false, fal_pret: true, formes: ["reel", "essai", "image", "carrousel", "story"], graduations: ["MANUAL", "SS_PERFORMANCE"], carrousel: [2, 3] }, reglage),
    format: Object.assign({ forme: "reel", graduation: "MANUAL", images: [], exige_depot: false, a_video: true, statut: "draft" }, format),
  };
  const win = {
    dzT: FR,
    fetch: async (url, init = {}) => {
      const m = init.method || "GET", corps = init.body ? JSON.parse(init.body) : undefined;
      appels.push({ url: String(url), methode: m, corps });
      if (panne) throw new Error("réseau coupé");
      if (url === "/api/schedule/instagram/reglage") {
        if (m === "PUT") { etat.reglage.depot_fal = corps.depot_fal; return reponse(200, { depot_fal: corps.depot_fal }); }
        return reponse(200, etat.reglage);
      }
      if (url === "/api/images") return reponse(200, { images: [{ filename: "a.png" }, { filename: "b <i>.jpg" }, "c.webp", { filename: "d.png" }] });
      if (String(url).endsWith("/instagram")) {
        if (m === "PUT") {
          if (put) return put(corps);
          Object.assign(etat.format, corps, { exige_depot: ["essai", "image", "carrousel"].includes(corps.forme) });
          return reponse(200, etat.format);
        }
        return reponse(200, etat.format);
      }
      return reponse(404, {});
    },
  };
  const doc = { createElement: (t) => new Noeud(t), head: new Noeud("head"), documentElement: new Noeud("html") };
  const ctx = { window: win, document: doc, console, encodeURIComponent, Promise, JSON, Array, Object, String };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx);
  return { win, appels, etat, Dz: win.__dzIgFormat, hote: new Noeud("div") };
}
const puts = (m) => m.appels.filter((a) => a.methode === "PUT" && a.url.endsWith("/instagram"));

// ---- lecture, formes, graduation -----------------------------------------------------------------------------------------
{
  const m = monde();
  const c = m.Dz.monter(m.hote, "p 1", { statut: "draft" });
  await tick(); await tick();
  ok("1.1 lit le réglage et le format du post (id encodé)", m.appels.map((a) => a.url).join() === "/api/schedule/instagram/reglage,/api/schedule/p%201/instagram");
  const sf = marque(m.hote, "forme"), sg = marque(m.hote, "graduation");
  ok("1.2 cinq formes traduites, Reel choisi", sf.children.length === 5 && sf.value === "reel" && sf.children[1].textContent === FR("igformat.forme.essai"));
  ok("1.3 Reel : la suite de l'essai est cachée, l'aide dit l'envoi direct, pas d'accord demandé", sg.hasAttribute("hidden")
    && txt(marque(m.hote, "aide")) === FR("igformat.aide.reel") && !marque(m.hote, "accord") && m.appels.every((a) => a.methode === "GET"));
  sf.value = "essai"; sf.fire("change"); await tick(); await tick();
  ok("1.4 essai : enregistré, la suite de l'essai apparaît", puts(m).length === 1 && puts(m)[0].corps.forme === "essai" && puts(m)[0].corps.images.length === 0
    && !sg.hasAttribute("hidden") && txt(marque(m.hote, "aide")) === FR("igformat.aide.essai"));
  ok("1.5 essai : l'accord est demandé, décoché, et le blocage est dit", !!marque(m.hote, "accord") && marque(m.hote, "accord").checked === false
    && txt(marque(m.hote, "bloque")) === FR("igformat.depot.bloque") && txt(marque(m.hote, "depot")).includes(FR("igformat.depot.accord")));
  sg.value = "SS_PERFORMANCE"; sg.fire("change"); await tick(); await tick();
  ok("1.6 graduation enregistrée", puts(m)[1].corps.graduation === "SS_PERFORMANCE");
  const acc = marque(m.hote, "accord");
  acc.checked = true; acc.fire("change"); await tick(); await tick();
  const pr = m.appels.filter((a) => a.methode === "PUT" && a.url === "/api/schedule/instagram/reglage");
  ok("1.7 cocher l'accord : PUT depot_fal vrai, le blocage disparaît", pr.length === 1 && pr[0].corps.depot_fal === true && !marque(m.hote, "bloque")
    && marque(m.hote, "accord").checked === true);
  const acc2 = marque(m.hote, "accord");
  acc2.checked = false; acc2.fire("change"); await tick(); await tick();
  ok("1.8 décocher : PUT depot_fal faux, le blocage revient", m.etat.reglage.depot_fal === false && !!marque(m.hote, "bloque"));
  // idempotence et statut
  const avant = m.appels.length;
  const c2 = m.Dz.monter(m.hote, "p 1", { statut: "draft" });
  ok("1.9 rappelé pour le même post (chaque rendu) : même composant, aucune relecture, un seul panneau", c2 === c && m.appels.length === avant && marques(m.hote, "racine").length === 1);
  m.Dz.monter(m.hote, "p 1", { statut: "posted" });
  ok("1.10 post parti : les choix sont figés", marque(m.hote, "forme").hasAttribute("disabled") && m.appels.length === avant);
  m.Dz.monter(m.hote, "p2", { statut: "draft" }); await tick(); await tick();
  ok("1.11 autre post : remonté et relu, toujours un seul panneau", marques(m.hote, "racine").length === 1 && m.appels.some((a) => a.url === "/api/schedule/p2/instagram")
    && !marque(m.hote, "forme").hasAttribute("disabled"));
  ok("1.12 sans nœud ou sans post : rien", m.Dz.monter(null, "x") === null && m.Dz.monter(m.hote, "") === null);
}

// ---- carrousel ------------------------------------------------------------------------------------------------------------
{
  const m = monde({ format: { forme: "carrousel", images: ["c.webp"], exige_depot: true }, reglage: { depot_fal: true } });
  m.Dz.monter(m.hote, "p1", { statut: "draft" });
  await tick(); await tick(); await tick();
  const v = () => marques(m.hote, "vignette");
  ok("2.1 la Bibliothèque en vignettes, noms en titre, jamais en HTML", v().length === 4 && v()[1].attrs.title === "b <i>.jpg" && tous(m.hote, (x) => x.tagName === "I").length === 0);
  ok("2.2 l'image déjà choisie est marquée avec son rang", v()[2].attrs["aria-pressed"] === "true" && txt(v()[2]) === "1" && v()[0].attrs["aria-pressed"] === "false");
  ok("2.3 le compte et les bornes sont dits", txt(marque(m.hote, "compte")) === FR("igformat.carrousel.compte", { n: 1, min: 2, max: 3 }));
  v()[0].click(); await tick(); await tick();
  v()[3].click(); await tick(); await tick();
  ok("2.4 l'ordre est celui des clics", J(puts(m)[1].corps.images) + "" === "c.webp,a.png,d.png" && txt(v()[0]) === "2" && txt(v()[3]) === "3", JSON.stringify(puts(m).map((p) => p.corps.images)));
  const np = puts(m).length;
  v()[1].click(); await tick();
  ok("2.5 au-delà du maximum (3) : rien n'est ajouté ni envoyé", puts(m).length === np && v()[1].attrs["aria-pressed"] === "false");
  v()[2].click(); await tick(); await tick();
  ok("2.6 recliquer retire et renumérote", J(puts(m)[np].corps.images) + "" === "a.png,d.png" && txt(v()[0]) === "1" && txt(v()[3]) === "2");
  ok("2.7 accord déjà donné : coché, pas de blocage", marque(m.hote, "accord").checked === true && !marque(m.hote, "bloque"));
  const sf = marque(m.hote, "forme"); sf.value = "story"; sf.fire("change"); await tick(); await tick();
  ok("2.8 quitter le carrousel : les images ne sont plus envoyées, la grille disparaît", puts(m).slice(-1)[0].corps.images.length === 0 && v().length === 0);
}

// ---- sans fal, erreurs ------------------------------------------------------------------------------------------------------
{
  const m = monde({ format: { forme: "image", exige_depot: true }, reglage: { fal_pret: false } });
  m.Dz.monter(m.hote, "p1", {}); await tick(); await tick();
  ok("3.1 sans clé fal : dit où la poser, aucune case d'accord", txt(marque(m.hote, "sans-fal")) === FR("igformat.depot.sans_fal") && !marque(m.hote, "accord"));
  const m2 = monde({ put: () => reponse(409, { detail: "x" }) });
  m2.Dz.monter(m2.hote, "p1", {}); await tick(); await tick();
  const sf = marque(m2.hote, "forme"); sf.value = "story"; sf.fire("change"); await tick(); await tick(); await tick();
  ok("3.2 409 : dit « déjà parti », le choix revient à ce que le serveur garde", txt(marque(m2.hote, "erreur")) === FR("igformat.etat.deja_publie") && marque(m2.hote, "forme").value === "reel");
  const m3 = monde({ put: () => reponse(422, { detail: "x" }) });
  m3.Dz.monter(m3.hote, "p1", {}); await tick(); await tick();
  const s3 = marque(m3.hote, "forme"); s3.value = "image"; s3.fire("change"); await tick(); await tick(); await tick();
  ok("3.3 422 : dit « non enregistré »", txt(marque(m3.hote, "erreur")) === FR("igformat.etat.erreur_ecriture"));
  const m4 = monde({ panne: true });
  m4.Dz.monter(m4.hote, "p1", {}); await tick(); await tick();
  ok("3.4 réseau coupé à la lecture : dit, le panneau reste", txt(marque(m4.hote, "erreur")) === FR("igformat.etat.erreur_lecture") && !!marque(m4.hote, "forme"));
}

if (echecs.length) { console.log("ÉCHECS (" + echecs.length + "/" + n + ") :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("ig-format : OK (" + n + " vérifications)");
