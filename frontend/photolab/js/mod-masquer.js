// mod-masquer.js — Sélection › Sélectionner et masquer… (t157). La référence ouvre un espace à part ; l'amont, un
// formulaire sans aperçu. Ici : un dialogue non modal (la toile reste zoomable) dont les 7 VUES sont calculées par le
// moteur sur une copie (POST /masquer/apercu : select.refineEdge puis calques unis, masques, visibilités), OK =
// select.refineEdge avec la sortie choisie (précédé de select.inverse si « Inverser » est coché). Touches de la
// référence : F parcourt les vues, X les coupe, P montre l'original, et la lettre de chaque vue.
// Fonctions PURES exportées (qa/masques.test.mjs).

import { coquilleReglage, derniereGagne, chargerImage, identiteDocument, DELAI_APERCU } from "./mod-dialogue-reglage.js";
import { maxSideRequete } from "./mod-cycle.js";
import { raccourciAffiche } from "./mod-menus.js";

// Les 7 vues de la référence, avec leur touche (VUES_MASQUER du pont, même ordre).
export const VUES = [
  { id: "oignon", lettre: "O", cle: "photolab.masquer.vue_oignon" }, { id: "fourmis", lettre: "M", cle: "photolab.masquer.vue_fourmis" },
  { id: "incrustation", lettre: "V", cle: "photolab.masquer.vue_incrustation" }, { id: "noir", lettre: "A", cle: "photolab.masquer.vue_noir" },
  { id: "blanc", lettre: "T", cle: "photolab.masquer.vue_blanc" }, { id: "nb", lettre: "K", cle: "photolab.masquer.vue_nb" },
  { id: "calques", lettre: "Y", cle: "photolab.masquer.vue_calques" },
];
export const SORTIES = ["selection", "layerMask", "newLayer", "newLayerWithMask"];
const LIB_SORTIES = { selection: "photolab.masquer.sortie_selection", layerMask: "photolab.masquer.sortie_layermask",
  newLayer: "photolab.masquer.sortie_newlayer", newLayerWithMask: "photolab.masquer.sortie_newlayerwithmask" };
// Réglages (bornes du moteur, smartselect_cmds.rs ; le pont refuse au-delà) et valeurs de départ.
export const REGLAGES = [
  { cle: "radius", lib: "photolab.masquer.radius", min: 0, max: 250, pas: 1, unite: "px", groupe: "contours" },
  { cle: "smartRadius", lib: "photolab.masquer.smartradius", type: "case", groupe: "contours" },
  { cle: "smooth", lib: "photolab.masquer.smooth", min: 0, max: 100, pas: 1, groupe: "global" },
  { cle: "feather", lib: "photolab.masquer.feather", min: 0, max: 250, pas: 0.1, unite: "px", groupe: "global" },
  { cle: "contrast", lib: "photolab.masquer.contrast", min: 0, max: 100, pas: 1, unite: "%", groupe: "global" },
  { cle: "shiftEdge", lib: "photolab.masquer.shiftedge", min: -100, max: 100, pas: 1, unite: "%", groupe: "global" },
  { cle: "decontaminate", lib: "photolab.masquer.decontaminate", type: "case", groupe: "sortie" },
  { cle: "amount", lib: "photolab.masquer.amount", min: 0, max: 100, pas: 1, unite: "%", groupe: "sortie" },
  { cle: "sampleAllLayers", lib: "photolab.masquer.samplealllayers", type: "case", groupe: "sortie" },
];
export const DEPART = { radius: 0, smartRadius: false, smooth: 0, feather: 0, contrast: 0, shiftEdge: 0, decontaminate: false,
  amount: 100, sampleAllLayers: false, output: "selection", vue: "incrustation", transparence: 50, inverser: false };
const MEMOIRE = "dzPhotolabMasquerMemoire";        // clé du stockage local (Mémoriser les paramètres)

// Raccourci de la référence (et de l'amont, menus.rs) : le catalogue n'en porte pas pour cette entrée. Posé sur l'arbre
// des menus, il est affiché ET pris par mod-raccourcis (indexRaccourcis lit l'arbre).
export const RACCOURCI = "Cmd+Alt+R";
export function decorerMasquer(menus, lang = "fr") {
  const voir = (l) => (l || []).map((e) => (e.id === "select.selectAndMask" ? { ...e, raccourci: raccourciAffiche(RACCOURCI, lang) }
    : e.entrees ? { ...e, entrees: voir(e.entrees) } : e));
  return (menus || []).map((m) => ({ ...m, entrees: voir(m.entrees) }));
}

export function vueSuivante(id) {
  const i = VUES.findIndex((v) => v.id === id);
  return VUES[(i + 1) % VUES.length].id;
}
export function vueParLettre(lettre) {
  const v = VUES.find((x) => x.lettre === String(lettre || "").toUpperCase());
  return v ? v.id : null;
}
// Un nombre saisi -> borné à son réglage (virgule décimale admise) ; illisible -> valeur de départ.
export function borner(r, brut) {
  const n = typeof brut === "number" ? brut : Number(String(brut).trim().replace(",", "."));
  if (!Number.isFinite(n)) return DEPART[r.cle];
  const x = Math.min(r.max, Math.max(r.min, n));
  return r.pas >= 1 ? Math.round(x) : Math.round(x * 10) / 10;
}
// Les réglages envoyés au moteur (sans la sortie, la vue, la transparence ni Inverser).
export function reglagesEnvoyes(v) {
  const o = {};
  for (const r of REGLAGES) o[r.cle] = r.type === "case" ? v[r.cle] === true : borner(r, v[r.cle]);
  return o;
}
// OK : les commandes, dans l'ordre (Inverser d'abord).
export function commandesValidation(v) {
  const c = [];
  if (v.inverser) c.push({ command: "select.inverse", params: {} });
  c.push({ command: "select.refineEdge", params: { ...reglagesEnvoyes(v), output: SORTIES.includes(v.output) ? v.output : "selection" } });
  return c;
}
// Mémoire de l'écran (« Mémoriser les paramètres ») : seules les clés connues et de bon type reviennent.
export function depuisMemoire(brut) {
  const v = { ...DEPART };
  if (!brut || typeof brut !== "object") return v;
  for (const r of REGLAGES) {
    if (!(r.cle in brut)) continue;
    v[r.cle] = r.type === "case" ? brut[r.cle] === true : borner(r, brut[r.cle]);
  }
  if (SORTIES.includes(brut.output)) v.output = brut.output;
  if (VUES.some((x) => x.id === brut.vue)) v.vue = brut.vue;
  if (Number.isFinite(brut.transparence)) v.transparence = Math.min(100, Math.max(0, Math.round(brut.transparence)));
  return v;
}

/* ───────────── côté DOM ───────────── */

export function initMasquer(PL) {
  const T = (cle, vars) => (window.dzT ? window.dzT(cle, vars) : cle);
  const lire = () => { try { const s = localStorage.getItem(MEMOIRE); return s ? JSON.parse(s) : null; } catch (e) { return null; } };
  const ecrire = (v) => { try { if (v) localStorage.setItem(MEMOIRE, JSON.stringify(v)); else localStorage.removeItem(MEMOIRE); } catch (e) { /* stockage refusé */ } };

  PL.ouvrirMasquer = function ouvrirMasquer() {
    const doc = PL.etat.doc;
    if (!doc) return;
    if (!doc.hasSelection) { PL.signaler(T("photolab.masquer.sans_selection"), true); return; }
    construire();
  };
  PL.actions = PL.actions || {};
  PL.actions["select.selectAndMask"] = () => PL.ouvrirMasquer();
  PL.decorateursMenus = PL.decorateursMenus || [];
  PL.decorateursMenus.push((menus) => decorerMasquer(menus, window.dzLang ? window.dzLang() : "fr"));

  function construire() {
    const memoire = lire();
    let v = depuisMemoire(memoire);
    let memoriser = !!memoire;
    let fini = false, apercuPose = false, minuterie = null, coupe = false, original = false;
    const etat = { identite: identiteDocument(PL.etat.doc, PL.etat.generation) };
    const coq = coquilleReglage(PL, {
      titre: T("photolab.masquer.titre"), classe: "pl-masquer", avecApercu: true,
      valider: () => fermer("ok"), annuler: () => fermer("annuler"),
      reinitialiser: () => { v = { ...DEPART }; tout(); planifier(); },
      surCaseApercu: (coche) => { if (coche) planifier(); else effacerApercu(); },
    });
    const el = (tag, classe, texte) => { const e = document.createElement(tag); if (classe) e.className = classe; if (texte != null) e.textContent = texte; return e; };
    const ctls = [];
    const section = (cle) => { const s = el("fieldset", "msk-section"); s.appendChild(el("legend", "", T(cle))); coq.corps.appendChild(s); return s; };

    /* Mode d'affichage */
    const sAff = section("photolab.masquer.affichage");
    const vue = el("select", "msk-vue"); vue.setAttribute("aria-label", T("photolab.masquer.vue"));
    for (const x of VUES) { const o = el("option", "", T(x.cle) + " (" + x.lettre + ")"); o.value = x.id; vue.appendChild(o); }
    vue.addEventListener("change", () => { v.vue = vue.value; coupe = false; planifier(); });
    const lVue = el("label", "msk-ligne"); lVue.append(el("span", "", T("photolab.masquer.vue")), vue);
    const orig = el("input"); orig.type = "checkbox";
    orig.addEventListener("change", () => { original = orig.checked; planifier(); });
    const lOrig = el("label", "msk-case"); lOrig.append(orig, el("span", "", T("photolab.masquer.original") + " (P)"));
    const transp = el("input", "msk-curseur"); transp.type = "range"; transp.min = "0"; transp.max = "100"; transp.step = "1";
    const transpN = el("input", "msk-nombre"); transpN.type = "number"; transpN.min = "0"; transpN.max = "100";
    transp.addEventListener("input", () => { v.transparence = Number(transp.value); transpN.value = transp.value; });
    transp.addEventListener("change", () => planifier());
    transpN.addEventListener("change", () => { v.transparence = Math.min(100, Math.max(0, Math.round(Number(transpN.value)) || 0)); tout(); planifier(); });
    const lTr = el("div", "msk-reglage"); const tTr = el("div", "msk-haut");
    tTr.append(el("span", "", T("photolab.masquer.transparence")), el("span", "msk-val")); tTr.lastChild.append(transpN, el("span", "pl-unite", "%"));
    lTr.append(tTr, transp);
    sAff.append(lVue, lOrig, lTr);

    /* réglages */
    const groupes = { contours: section("photolab.masquer.contours"), global: section("photolab.masquer.global") };
    const sSortie = section("photolab.masquer.sortie");
    groupes.sortie = sSortie;
    const actions = el("div", "msk-actions");
    const inverser = el("input"); inverser.type = "checkbox";
    inverser.addEventListener("change", () => { v.inverser = inverser.checked; planifier(); });
    const lInv = el("label", "msk-case"); lInv.append(inverser, el("span", "", T("photolab.masquer.inverser")));
    actions.appendChild(lInv);
    groupes.global.appendChild(actions);
    for (const r of REGLAGES) {
      const s = groupes[r.groupe];
      if (r.type === "case") {
        const k = el("input"); k.type = "checkbox";
        k.addEventListener("change", () => { v[r.cle] = k.checked; tout(); planifier(); });
        const l = el("label", "msk-case"); l.dataset.cle = r.cle;
        l.append(k, el("span", "", T(r.lib)));
        s.insertBefore(l, r.groupe === "global" ? actions : null);
        ctls.push(() => { k.checked = v[r.cle] === true; });
        continue;
      }
      const n = el("input", "msk-nombre"); n.type = "number"; n.min = String(r.min); n.max = String(r.max); n.step = String(r.pas);
      const c = el("input", "msk-curseur"); c.type = "range"; c.min = String(r.min); c.max = String(r.max); c.step = String(r.pas);
      c.setAttribute("aria-label", T(r.lib));
      c.addEventListener("input", () => { v[r.cle] = borner(r, c.value); n.value = String(v[r.cle]); });
      c.addEventListener("change", () => planifier());
      n.addEventListener("change", () => { v[r.cle] = borner(r, n.value); tout(); planifier(); });
      const l = el("div", "msk-reglage"); l.dataset.cle = r.cle;
      const h = el("div", "msk-haut"); const val = el("span", "msk-val"); val.appendChild(n);
      if (r.unite) val.appendChild(el("span", "pl-unite", r.unite));
      h.append(el("span", "", T(r.lib)), val);
      l.append(h, c);
      s.insertBefore(l, r.groupe === "global" ? actions : null);
      ctls.push(() => {
        n.value = String(v[r.cle]); c.value = String(v[r.cle]);
        if (r.cle === "amount") { n.disabled = c.disabled = !v.decontaminate; }
      });
    }
    const sortie = el("select", "msk-sortie");
    for (const x of SORTIES) { const o = el("option", "", T(LIB_SORTIES[x])); o.value = x; sortie.appendChild(o); }
    sortie.addEventListener("change", () => { v.output = sortie.value; });
    const lSortie = el("label", "msk-ligne"); lSortie.append(el("span", "", T("photolab.masquer.sortie_vers")), sortie);
    sSortie.appendChild(lSortie);
    const mem = el("input"); mem.type = "checkbox";
    mem.addEventListener("change", () => { memoriser = mem.checked; if (!memoriser) ecrire(null); });
    const lMem = el("label", "msk-case msk-memoire"); lMem.append(mem, el("span", "", T("photolab.masquer.memoriser")));
    coq.corps.append(lMem, coq.erreur);

    function tout() {
      vue.value = v.vue; orig.checked = original; inverser.checked = !!v.inverser; sortie.value = v.output; mem.checked = memoriser;
      transp.value = String(v.transparence); transpN.value = String(v.transparence);
      // décontaminer impose un nouveau calque masqué (moteur) : la sortie le dit
      sortie.disabled = !!v.decontaminate;
      if (v.decontaminate) sortie.value = "newLayerWithMask";
      ctls.forEach((f) => f());
    }

    /* aperçu du moteur */
    const demander = derniereGagne((c) => PL.api("POST", "/masquer/apercu", c, 0, true));
    const apercuActif = () => coq.caseApercu && coq.caseApercu.checked && !fini && !!PL.etat.doc;
    function effacerApercu() {
      clearTimeout(minuterie); demander.annuler(); coq.occupe(false);
      PL.fourmisApercu = null;
      if (apercuPose) { apercuPose = false; PL.cycle(); } else if (PL.dessinerFourmis) PL.dessinerFourmis();
    }
    function planifier() {
      clearTimeout(minuterie);
      if (!apercuActif()) return;
      if (original || coupe) { effacerApercu(); return; }
      minuterie = setTimeout(lancer, DELAI_APERCU);
    }
    async function lancer() {
      if (!apercuActif() || original || coupe) return;
      const voulu = PL.vue.maxSideVoulu();
      coq.occupe(true);
      const r = await demander({ reglages: reglagesEnvoyes(v), vue: v.vue, transparence: v.transparence, inverser: !!v.inverser,
        maxSide: maxSideRequete(voulu, PL.etat.doc) });
      if (r.perime) return;
      coq.occupe(demander.enVol());
      if (fini || !apercuActif() || original || coupe) return;
      if (r.erreur) { coq.montrerErreur(T("photolab.reglage.erreur_apercu") + " " + (r.erreur.message || "")); return; }
      let im;
      try { im = await chargerImage(r.valeur.url); } catch (e) { coq.montrerErreur(T("photolab.reglage.erreur_apercu")); return; }
      if (fini || !apercuActif()) return;
      coq.montrerErreur("");
      PL.fourmisApercu = v.vue === "fourmis" && Array.isArray(r.valeur.bounds) ? r.valeur.bounds : null;
      PL.vue.poserApercu(im, voulu);
      apercuPose = true;
      if (PL.dessinerFourmis) PL.dessinerFourmis();
    }
    etat.surRenduReel = () => { if (apercuActif()) { apercuPose = false; planifier(); } };

    // Touches de la référence (hors champ de saisie numérique) : F, X, P, lettres des vues.
    coq.boite.addEventListener("keydown", (ev) => {
      if (ev.ctrlKey || ev.metaKey || ev.altKey || (ev.target && /^(INPUT|SELECT)$/.test(ev.target.tagName) && ev.target.type !== "checkbox" && ev.target.type !== "range")) return;
      const k = ev.key.toUpperCase();
      if (k === "F") { v.vue = vueSuivante(v.vue); coupe = false; }
      else if (k === "X") coupe = !coupe;
      else if (k === "P") original = !original;
      else { const id = vueParLettre(k); if (!id) return; v.vue = id; coupe = false; }
      ev.preventDefault();
      tout(); planifier();
    }, true);

    function fermer(role) {
      if (fini) return;
      fini = true;
      clearTimeout(minuterie);
      demander.annuler();
      coq.retirer();
      PL.libererReglage(etat);
      PL.fourmisApercu = null;
      if (role === "ok") {
        if (memoriser) ecrire(v); else ecrire(null);
        const efface = apercuPose;
        const cmds = commandesValidation(v);
        (async () => {
          let ok = true;
          for (const c of cmds) { const r = await PL.executer(c.command, c.params); if (!(r && r.ok)) { ok = false; break; } }
          if (!ok && efface) PL.cycle();
        })();
      } else if (apercuPose) PL.cycle();
      else if (PL.dessinerFourmis) PL.dessinerFourmis();
    }
    etat.fermer = fermer;
    PL.prendreReglage(etat);
    tout();
    coq.placer();
    planifier();
  }
}
