# Finitions UI — chantier 2 : dialogues maison partout — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** plus aucun `confirm` / `alert` / `prompt` natif (le « 127.0.0.1:8765 indique » des captures) — ni dans le Vectorlab, ni dans le bundle React — remplacés par un dialogue maison asynchrone au thème de l'application.

**Architecture :** un module pur `mod-dialogue.js` (spécification d'un dialogue, touches, cycle de focus — bancable sous node) + une partie DOM (`initDialogue(VL)` → `VL.dialogue.confirmer / informer / saisir`, rendus dans `#vlDlg` avec le patron `.vl-dlg-boite` / `.vl-dlg-tete` de mod-impression). Les appelants deviennent `async`. Pour le bundle : une couche `frontend/patches/dialogue.js` injectée par `scripts/patch_bundle_dialogue.py` (maillon neuf en queue de chaîne avant `version`), qui pose `window.__dzDialogue` et remplace `window.alert` ; les 11 sites `confirm(` du bundle sont réécrits en `await window.__dzDialogue.confirmer(`.

**Tech :** ES modules du Vectorlab, banc `node frontend/vectorlab/qa/run.mjs`, patcher python à contrat (octets, garde-chaîne, sonde), pytest miroir `backend/tests/test_dialogue_bundle.py`.

---

## Relevé (code lu le 20/09/2026, branche `chantier/vectorlab-affinity` à `b5ea7ea`)

| Module | Ligne | Appel natif | Fonction appelante | Devient |
|---|---|---|---|---|
| mod-biblio | 148 | `prompt("Nom de la copie…")` | `async dupliquer(id)` | `await VL.dialogue.saisir` |
| mod-biblio | 161 | `confirm("Supprimer ce document ?…")` | `async supprimer(id)` | `await VL.dialogue.confirmer` (danger) |
| mod-biblio | 197 | `confirm("Des modifications non sauvées…")` | écouteur clic `#btnBiblio` | écouteur `async` |
| mod-brouillon | 50 | `confirm("Un brouillon… Le restaurer ?")` | `surCharge()` (sync, appelée avant `charger()`) | `async` ; boutons « Restaurer » / « Repartir du serveur », heure du brouillon dans le titre |
| mod-charpente | 65 | `prompt("Nom du calque :")` | commande `calqueRenommer.faire` | `faire: async () => …` |
| mod-charpente | 66 | `confirm("Supprimer le calque…")` | commande `calqueSupprimer.faire` | `faire: async () => …` (danger) |
| mod-export | 111 | `prompt("Lier l'export 2× à quelle entité ?")` | `async` (appelle `exporterPNG`) | `await VL.dialogue.saisir` |
| mod-export | 125 | — | commentaire, pas un appel | rien |
| mod-image | 221 | `prompt("Décrire l'image à générer…")` | `async generer()` | `saisir` |
| mod-image | 255 | `prompt("Quelle image ?")` | fonction sync qui `throw` | devient `async` ; ses appelants `await` |
| mod-layers | 109 | `prompt("Nom du calque :")` | `renommer(id)` | `async` |
| mod-layers | 156 | `confirm("Supprimer le calque…")` | écouteur clic `#listeCalques` | écouteur `async` (danger) |
| mod-planches | 60 | `prompt("Nom de la planche :")` | écouteur clic | `async` |
| mod-plateau | 85 | `prompt("Clé du terrain…")` | écouteur clic `#terPlus` | `async` |
| mod-plateau | 93-95 | 3 × `prompt` (nom, couleur, hauteur) | `retoucher(cle, neuf)` | `async`, trois `saisir` enchaînés |
| mod-tools | 246 | `prompt("Texte :")` | pointerdown outil texte (repli si `VL.poserTexte` absent) | `async` sur la branche |
| mod-tools | 554 | `prompt("Texte :")` | dblclick (repli si `VL.editerTexte` absent) | `async` sur la branche |
| mod-vitrail | 9 | — | commentaire | rien |

18 appels réels (le spec en comptait 20 : deux sont des commentaires).
Le bundle `frontend/dist/assets/index-BEOJX8L5.js` : 11 `confirm(` (dont
`"Remove this feed?"` ×2, un `window.confirm(` dans une `function(){}` non
async, un `confirm("Delete this job…")` dans un `onClick:f=>{…}` non
async — tous les autres dans des `async()=>{…}` / `async function`),
33 `alert(` (dont 15 `window.alert(`). Aucun composant de dialogue
générique dans `frontend/src` (`PersonaCreatorModal` est spécifique) : la
voie est le patcher. Ancre d'injection `/*__DZ_TRANSFERT_END__*/` : 1
occurrence. Aucun `.bak_*` dans ce worktree (non suivis par git) : le
maillon neuf se crée son backup au premier passage, puis `version` est
rejoué en dernier (procédure de `patcher-lit-le-bundle-en-octets`).

Hôte DOM : `index.html:180` porte `#impDlg`/`#traceDlg` ; on ajoute
`<div id="vlDlg" class="vl-dlg hidden"></div>`. Jetons : `--aff-fond`,
`--aff-bord`, `--aff-texte`, `--aff-muet`, `--aff-sel`, `--aff-champ`
(mod-theme). Le rouge de danger n'a pas de jeton : `#c0392b` n'est pas
dans `LEGACY` (theme.test refuse seulement les hex hérités), on l'écrit
tout de même en jeton local `--vl-danger` défini dans la règle `.vl-dlg`.

---

### Task 1 : module pur `mod-dialogue.js` (RED → GREEN)

**Files :**
- Create : `frontend/vectorlab/js/mod-dialogue.js`
- Test : `frontend/vectorlab/qa/dialogue.test.mjs`

- [ ] **Step 1 : le banc**

```js
// dialogue.test.mjs — mod-dialogue : la spécification pure d'un dialogue
// maison (confirmer / informer / saisir), les touches et le cycle de focus.
import { dialogue_spec, dialogue_touche, focus_suivant } from "../js/mod-dialogue.js";
const echecs = [];
const ok = (nom, cond, detail = "") => { if (!cond) echecs.push(nom + (detail ? " — " + String(detail).slice(0, 200) : "")); };
{
  const c = dialogue_spec("confirmer", "Supprimer le calque « A » ?\nSes objets aussi.", { danger: true });
  ok("confirmer : titre par défaut, corps en lignes, deux boutons OK/Annuler, OK danger, défaut = annuler quand danger",
     c.titre === "Confirmer" && c.corps.length === 2 && c.boutons.length === 2
     && c.boutons[0].role === "annuler" && c.boutons[1].role === "ok" && c.boutons[1].danger === true && c.defaut === "annuler", JSON.stringify(c));
  const c2 = dialogue_spec("confirmer", "Continuer ?", { ok: "Restaurer", annuler: "Repartir du serveur", titre: "Brouillon" });
  ok("confirmer : libellés et titre personnalisés, défaut = ok sans danger", c2.titre === "Brouillon" && c2.boutons[1].libelle === "Restaurer" && c2.boutons[0].libelle === "Repartir du serveur" && c2.defaut === "ok", JSON.stringify(c2));
  const i = dialogue_spec("informer", "Enregistré.");
  ok("informer : un seul bouton Fermer (role ok), défaut ok, pas de champ", i.boutons.length === 1 && i.boutons[0].role === "ok" && i.defaut === "ok" && i.champ === null, JSON.stringify(i));
  const s = dialogue_spec("saisir", "Nom :", { valeur: "calque 1", valider: "Renommer" });
  ok("saisir : un champ avec la valeur initiale, bouton OK libellé, défaut ok", s.champ && s.champ.valeur === "calque 1" && s.boutons[1].libelle === "Renommer" && s.defaut === "ok", JSON.stringify(s));
  ok("état vide : message vide → corps [], type inconnu → informer", dialogue_spec("saisir", "").corps.length === 0 && dialogue_spec("zzz", "x").boutons.length === 1);
  ok("touches : Entrée = défaut, Échap = annuler (ou ok pour informer), autre = null",
     dialogue_touche(c, "Enter") === "annuler" && dialogue_touche(c2, "Enter") === "ok" && dialogue_touche(c, "Escape") === "annuler" && dialogue_touche(i, "Escape") === "ok" && dialogue_touche(c, "a") === null);
  ok("focus piégé : Tab avance, Maj+Tab recule, cyclique", focus_suivant(3, 2, false) === 0 && focus_suivant(3, 0, true) === 2 && focus_suivant(3, 1, false) === 2 && focus_suivant(0, 0, false) === -1);
}
if (echecs.length) { console.error("ECHECS dialogue :\n- " + echecs.join("\n- ")); process.exit(1); }
console.log("QA dialogue : PASS (7 controles)");
```

- [ ] **Step 2 : RED** — `node frontend/vectorlab/qa/dialogue.test.mjs` → échec `Cannot find module`.

- [ ] **Step 3 : le module (partie pure + DOM)**

```js
// mod-dialogue.js — dialogues maison (confirmer / informer / saisir) qui
// REMPLACENT confirm/alert/prompt natifs (le « 127.0.0.1:8765 indique »
// des captures du 19/09). Partie pure bancable en tête ; DOM ensuite.
export function dialogue_spec(type, message, o = {}) {
  const t = ["confirmer", "informer", "saisir"].includes(type) ? type : "informer";
  const corps = String(message ?? "").split("\n").map((l) => l.trim()).filter(Boolean);
  const titre = o.titre || { confirmer: "Confirmer", informer: "Information", saisir: "Saisie" }[t];
  const okLib = o.ok || o.valider || (t === "informer" ? "Fermer" : "OK");
  const boutons = t === "informer"
    ? [{ role: "ok", libelle: okLib, danger: false }]
    : [{ role: "annuler", libelle: o.annuler || "Annuler", danger: false },
       { role: "ok", libelle: okLib, danger: !!o.danger }];
  const champ = t === "saisir" ? { valeur: String(o.valeur ?? ""), placeholder: o.placeholder || "" } : null;
  const defaut = (t === "confirmer" && o.danger) ? "annuler" : "ok";
  return { type: t, titre, corps, boutons, champ, defaut };
}
export function dialogue_touche(spec, key) {
  if (key === "Enter") return spec.defaut;
  if (key === "Escape") return spec.type === "informer" ? "ok" : "annuler";
  return null;
}
export function focus_suivant(n, i, arriere) {
  if (!n) return -1;
  return ((arriere ? i - 1 : i + 1) + n) % n;
}

/* ── DOM ── */
export function initDialogue(VL) {
  const $ = (s) => document.querySelector(s);
  let hote = $("#vlDlg");
  if (!hote) { hote = document.createElement("div"); hote.id = "vlDlg"; hote.className = "vl-dlg hidden"; document.body.appendChild(hote); }
  let courant = null;   // { resoudre, spec }
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  function fermer(role) {
    if (!courant) return;
    const { resoudre, spec } = courant; courant = null;
    const val = spec.type === "saisir" ? (hote.querySelector("input") || {}).value : null;
    hote.classList.add("hidden"); hote.innerHTML = "";
    if (spec.type === "confirmer") resoudre(role === "ok");
    else if (spec.type === "saisir") resoudre(role === "ok" ? String(val ?? "") : null);
    else resoudre(undefined);
  }
  function ouvrir(spec) {
    if (courant) fermer("annuler");
    return new Promise((resoudre) => {
      courant = { resoudre, spec };
      hote.innerHTML = `<div class="vl-dlg-boite vl-dlg-petite" role="dialog" aria-modal="true" aria-label="${esc(spec.titre)}">
        <div class="vl-dlg-tete"><b>${esc(spec.titre)}</b><span class="spacer"></span><button data-role="${spec.type === "informer" ? "ok" : "annuler"}" title="Fermer">✕</button></div>
        <div class="vl-dlg-corps">${spec.corps.map((l) => `<p>${esc(l)}</p>`).join("")}${spec.champ ? `<input type="text" value="${esc(spec.champ.valeur)}" placeholder="${esc(spec.champ.placeholder)}">` : ""}</div>
        <div class="vl-dlg-pied">${spec.boutons.map((b) => `<button data-role="${b.role}" class="${b.danger ? "vl-dlg-danger" : ""}${b.role === spec.defaut ? " vl-dlg-defaut" : ""}">${esc(b.libelle)}</button>`).join("")}</div>
      </div>`;
      hote.classList.remove("hidden");
      hote.querySelectorAll("[data-role]").forEach((b) => b.addEventListener("click", () => fermer(b.dataset.role)));
      const champ = hote.querySelector("input");
      if (champ) { champ.focus(); champ.select(); }
      else (hote.querySelector(".vl-dlg-pied .vl-dlg-defaut") || hote.querySelector(".vl-dlg-pied button")).focus();
    });
  }
  hote.addEventListener("click", (ev) => { if (ev.target === hote && courant) fermer(courant.spec.type === "informer" ? "ok" : "annuler"); });
  document.addEventListener("keydown", (ev) => {
    if (!courant) return;
    ev.stopPropagation();
    if (ev.key === "Tab") {
      const f = [...hote.querySelectorAll("input, button")];
      const i = Math.max(0, f.indexOf(document.activeElement));
      ev.preventDefault(); f[focus_suivant(f.length, i, ev.shiftKey)]?.focus(); return;
    }
    const role = dialogue_touche(courant.spec, ev.key);
    if (role) { ev.preventDefault(); fermer(role); }
  }, true);
  VL.dialogue = {
    confirmer: (message, o = {}) => ouvrir(dialogue_spec("confirmer", message, o)),
    informer: (message, o = {}) => ouvrir(dialogue_spec("informer", message, o)),
    saisir: (message, o = {}) => ouvrir(dialogue_spec("saisir", message, o)),
    ouvert: () => !!courant,
  };
}
```

- [ ] **Step 4 : GREEN** — `node frontend/vectorlab/qa/dialogue.test.mjs` → `PASS (7 controles)`.

- [ ] **Step 5 : CSS + hôte + init** — `vectorlab.css` (après `.vl-dlg-tete input[type="search"]`) :

```css
.vl-dlg { --vl-danger: #c0392b; }
.vl-dlg-petite { width: min(440px, 92vw); }
.vl-dlg-corps { padding: 12px 14px; display: flex; flex-direction: column; gap: 8px; font-size: 13px; line-height: 1.45; }
.vl-dlg-corps p { margin: 0; }
.vl-dlg-corps input { background: var(--aff-champ); color: var(--aff-texte); border: 1px solid var(--aff-bord); border-radius: 4px; padding: 5px 8px; font: inherit; }
.vl-dlg-pied { display: flex; gap: 8px; justify-content: flex-end; padding: 10px 14px; border-top: 1px solid var(--aff-bord); }
.vl-dlg-pied button { min-width: 88px; height: 28px; padding: 0 12px; border-radius: 4px; background: var(--aff-champ); color: var(--aff-texte); border: 1px solid var(--aff-bord); cursor: pointer; }
.vl-dlg-pied button.vl-dlg-defaut { background: var(--aff-sel); border-color: var(--aff-sel); color: var(--aff-texte); }
.vl-dlg-pied button.vl-dlg-danger { background: var(--vl-danger); border-color: var(--vl-danger); color: var(--aff-texte); }
.vl-dlg-pied button:focus-visible { outline: 2px solid var(--aff-cyan); outline-offset: 1px; }
```

`index.html` : `<div id="vlDlg" class="vl-dlg hidden"></div>` après `#impDlg`. `core.js` : `import { initDialogue } from "./mod-dialogue.js";` et `initDialogue(VL);` **avant** `initBiblio(VL)` (ligne ~769) — tout appelant doit trouver `VL.dialogue`.

- [ ] **Step 6 :** `node frontend/vectorlab/qa/run.mjs && git add … && git commit --only frontend/vectorlab/js/mod-dialogue.js frontend/vectorlab/qa/dialogue.test.mjs frontend/vectorlab/vectorlab.css frontend/vectorlab/index.html frontend/vectorlab/js/core.js -m "vectorlab : mod-dialogue — confirmer / informer / saisir maison, pur + DOM, jetons --aff-*"`

### Task 2 : les 18 appels du Vectorlab

**Files :** les dix modules du relevé.

- [ ] **Step 1 :** pour chaque ligne du relevé, remplacer selon la colonne « Devient ». Formes exactes :
  - `prompt(msg, val)` → `await VL.dialogue.saisir(msg, { valeur: val })` (résultat `null` = annulé, comme `prompt`) ;
  - `confirm(msg)` → `await VL.dialogue.confirmer(msg)` ; suppressions : `{ ok: "Supprimer", danger: true }` ;
  - mod-brouillon : `await VL.dialogue.confirmer(\`Un ${brouillon_libelle(b)} de ce document n'a pas été sauvé.\nRepartir du serveur = version ${etat.meta.version}, le brouillon est alors oublié.\`, { titre: "Brouillon non sauvé", ok: "Restaurer", annuler: "Repartir du serveur" })` ; `surCharge` devient `async` — vérifier au code que `charger()` l'`await` (sinon l'`await` de la promesse dans core : `if (VL.surCharge) await VL.surCharge(...)`) ;
  - mod-image 255 : la fonction devient `async` ; ses appelants (grep `imageCible(`) posent `await`.
- [ ] **Step 2 :** `grep -n -E "\b(confirm|alert|prompt)\(" frontend/vectorlab/js/*.js` ne rend plus que les deux commentaires ; `node --check` sur chaque module touché ; `node frontend/vectorlab/qa/run.mjs` vert.
- [ ] **Step 3 :** commit `--only` des dix modules (+ core.js si `charger` change) : `vectorlab : les 18 appels natifs confirm/prompt passent par VL.dialogue`.

### Task 3 : le bundle — couche `dialogue.js` + `patch_bundle_dialogue.py` + pytest miroir

**Files :**
- Create : `frontend/patches/dialogue.js`, `scripts/patch_bundle_dialogue.py`, `backend/tests/test_dialogue_bundle.py`
- Modify : `frontend/dist/assets/index-BEOJX8L5.js` (par le patcher)

- [ ] **Step 1 : pytest RED** — `backend/tests/test_dialogue_bundle.py` (discipline de `test_transfert_bundle.py` : charger le patcher comme module, ancres des deux côtés, bloc = couche octet pour octet, CRLF en octets, `read_text(` absent du patcher) :

```python
"""Miroir de la couche « dialogues maison » du bundle. Run: python tests/test_dialogue_bundle.py"""
import importlib.util, pathlib, re, sys
sys.stdout.reconfigure(encoding="utf-8")
RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
BUNDLE = RACINE / "frontend/dist/assets/index-BEOJX8L5.js"
COUCHE = RACINE / "frontend/patches/dialogue.js"
PATCHER = RACINE / "scripts/patch_bundle_dialogue.py"
ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")
def load(nom, chemin):
    spec = importlib.util.spec_from_file_location(nom, chemin); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
P = load("patch_bundle_dialogue", PATCHER)
raw = BUNDLE.read_bytes(); s = raw.decode("utf-8-sig")
couche = COUCHE.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
check("patcher : lit en octets (pas de read_text)", "read_text(" not in PATCHER.read_text(encoding="utf-8"))
check("bundle : CRLF conservés (octets)", raw.count(b"\r\n") > 15000 and raw.count(b"\n") == raw.count(b"\r\n"))
i, j = s.find(P.BEGIN), s.find(P.END)
check("bloc injecté présent une fois", s.count(P.BEGIN) == 1 and s.count(P.END) == 1 and i < j)
check("bloc = la couche octet pour octet", s[i:j + len(P.END)].replace("\r\n", "\n") == couche.strip())
for tag, a, r, n in P.PATCHES:
    check(f"{tag} : ancre consommée", s.count(a) == 0, str(s.count(a)))
    check(f"{tag} : remplacement présent ×{n}", s.count(r) == n, str(s.count(r)))
check("plus aucun confirm( natif dans le bundle", re.search(r"(?<![\w.])confirm\(", s) is None)
check("window.confirm hors couche absent", s.replace(s[i:j], "").count("window.confirm(") == 0)
check("la couche remplace window.alert", "window.alert = " in couche and "__dzDialogue" in couche)
check("la couche ne cite aucune ancre du patcher", all(a not in couche for _, a, _, _ in P.PATCHES))
check("sonde amont : le maillon transfert est là ×1", s.count("__DZ_TRANSFERT_END__") == 1)
print(f"\n{ok} PASS, {fail} FAIL"); sys.exit(1 if fail else 0)
```

- [ ] **Step 2 : la couche** `frontend/patches/dialogue.js` (vanilla DOM, jetons de la charte `--srf-panel`, `--brd-hard`, `--txt-hi`, `--txt-mid`, mono 9,5 px pour l'en-tête, aucun arrondi de châssis) :

```js
/*__DZ_DIALOGUE_BEGIN__*/
/* dialogue.js — dialogues maison du bundle : `window.__dzDialogue.confirmer(msg, o)` → Promise<bool>,
   `.informer(msg)` → Promise<void>. Remplace `window.alert` (non bloquant, même contrat visuel) ;
   les sites `confirm(` du bundle sont réécrits par le patcher en `await window.__dzDialogue.confirmer(`.
   Charte design_handoff_icones_couleurs §1/§2.1 : surfaces --srf-panel, filets --brd-hard, textes --txt-*,
   en-tête IBM Plex Mono 9,5 px letter-spacing .12em, aucun arrondi de châssis. */
(function () {
  if (window.__dzDialogue) return;
  var S = {
    voile: "position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center",
    boite: "width:420px;max-width:92vw;background:var(--srf-panel,#13171c);border:1px solid var(--brd-hard,#2a3138);color:var(--txt-hi,#e6e9ee);box-shadow:0 18px 50px rgba(0,0,0,.5);font:13px/1.45 system-ui,sans-serif",
    tete: "padding:9px 14px;border-bottom:1px solid var(--brd-soft,#222830);font:9.5px 'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--txt-mid,#9aa4ae)",
    corps: "padding:14px;white-space:pre-wrap;color:var(--txt-base,#cfd6e2)",
    pied: "display:flex;gap:8px;justify-content:flex-end;padding:10px 14px;border-top:1px solid var(--brd-soft,#222830)",
    btn: "min-width:88px;height:28px;padding:0 12px;background:var(--srf-raised,#1b2028);border:1px solid var(--brd-hard,#2a3138);color:var(--txt-hi,#e6e9ee);cursor:pointer;font:inherit",
    ok: "background:var(--accent,#2b6fd6);border-color:var(--accent,#2b6fd6)",
    danger: "background:#c0392b;border-color:#c0392b"
  };
  var courant = null;
  function ouvrir(type, message, o) {
    o = o || {};
    return new Promise(function (resoudre) {
      if (courant) courant(false);
      var voile = document.createElement("div"); voile.setAttribute("style", S.voile); voile.setAttribute("role", "dialog"); voile.setAttribute("aria-modal", "true");
      var danger = !!o.danger || /supprimer|delete|remove|irr[eé]versible/i.test(String(message));
      var titre = o.titre || (type === "confirmer" ? "Confirmer" : "Information");
      var boutons = type === "confirmer"
        ? [["annuler", o.annuler || "Annuler", ""], ["ok", o.ok || (danger ? "Supprimer" : "OK"), danger ? S.danger : S.ok]]
        : [["ok", o.ok || "Fermer", S.ok]];
      var defaut = (type === "confirmer" && danger) ? "annuler" : "ok";
      var boite = document.createElement("div"); boite.setAttribute("style", S.boite);
      var tete = document.createElement("div"); tete.setAttribute("style", S.tete); tete.textContent = titre;
      var corps = document.createElement("div"); corps.setAttribute("style", S.corps); corps.textContent = String(message == null ? "" : message);
      var pied = document.createElement("div"); pied.setAttribute("style", S.pied);
      var fin = function (role) {
        if (!courant) return; courant = null;
        document.removeEventListener("keydown", surTouche, true);
        voile.remove(); resoudre(type === "confirmer" ? role === "ok" : undefined);
      };
      courant = function () { fin("annuler"); };
      var surTouche = function (ev) {
        ev.stopPropagation();
        if (ev.key === "Enter") { ev.preventDefault(); fin(defaut); }
        else if (ev.key === "Escape") { ev.preventDefault(); fin(type === "confirmer" ? "annuler" : "ok"); }
        else if (ev.key === "Tab") { ev.preventDefault(); var f = pied.querySelectorAll("button"); var i = Array.prototype.indexOf.call(f, document.activeElement); f[((ev.shiftKey ? i - 1 : i + 1) + f.length) % f.length].focus(); }
      };
      var focusDefaut = null;
      boutons.forEach(function (b) {
        var el = document.createElement("button"); el.type = "button"; el.setAttribute("style", S.btn + ";" + b[2]); el.textContent = b[1]; el.dataset.role = b[0];
        el.addEventListener("click", function () { fin(b[0]); }); pied.appendChild(el);
        if (b[0] === defaut) focusDefaut = el;
      });
      boite.appendChild(tete); boite.appendChild(corps); boite.appendChild(pied); voile.appendChild(boite);
      voile.addEventListener("click", function (ev) { if (ev.target === voile) fin(type === "confirmer" ? "annuler" : "ok"); });
      document.body.appendChild(voile);
      document.addEventListener("keydown", surTouche, true);
      if (focusDefaut) focusDefaut.focus();
    });
  }
  window.__dzDialogue = {
    confirmer: function (m, o) { return ouvrir("confirmer", m, o); },
    informer: function (m, o) { return ouvrir("informer", m, o); },
    ouvert: function () { return !!courant; }
  };
  window.alert = function (m) { return window.__dzDialogue.informer(m); };
})();
/*__DZ_DIALOGUE_END__*/
```

- [ ] **Step 3 : le patcher** `scripts/patch_bundle_dialogue.py` — copie des helpers `lire/ecrire/nl/guard_downstream` de `patch_bundle_transfert.py` (en OCTETS), `TAG = "dialogue"`, `ANCHOR_INJECT = "/*__DZ_TRANSFERT_END__*/"`, `apply(s, a, r, tag, n)` qui exige `s.count(a) == n`, `PATCHES` à quatre colonnes `(tag, ancre, remplacement, n)` :

```python
D = "await window.__dzDialogue.confirmer("
PATCHES = [
    ("D1-son",     'onClick:async()=>{confirm("Delete ce son ?")&&',              'onClick:async()=>{' + D + '"Delete ce son ?")&&', 1),
    ("D2-image",   'onClick:async()=>{confirm("Delete cette image ?")&&',         'onClick:async()=>{' + D + '"Delete cette image ?")&&', 1),
    ("D3-render",  'onClick:async()=>{confirm("Delete this render and its files?")&&', 'onClick:async()=>{' + D + '"Delete this render and its files?")&&', 1),
    ("D4-job",     'onClick:f=>{var m;(m=f==null?void 0:f.stopPropagation)==null||m.call(f),confirm("Delete this job and its files?")&&(o==null||o())}',
                   'onClick:async f=>{var m;(m=f==null?void 0:f.stopPropagation)==null||m.call(f),(' + D + '"Delete this job and its files?"))&&(o==null||o())}', 1),
    ("D5-feed-if", 'async function del(id){if(!confirm("Remove this feed?"))return;', 'async function del(id){if(!' + D + '"Remove this feed?"))return;', 1),
    ("D6-feed-f",  'async function f(v){if(confirm("Remove this feed?")){',      'async function f(v){if(' + D + '"Remove this feed?")){', 1),
    ("D7-rendu3d", 'onClick:function(){if(window.confirm("Supprimer définitivement ce rendu 3D ?")){', 'onClick:async function(){if(' + D + '"Supprimer définitivement ce rendu 3D ?")){', 1),
    ("D8-layout",  "async function dzDelTemplate(id,nm,refresh,selId,setSel){if(!confirm('Delete le layout \"'", "async function dzDelTemplate(id,nm,refresh,selId,setSel){if(!" + D + "'Delete le layout \"'", 1),
]
```
  Les 11 `confirm(` du relevé : D1..D8 en couvrent 8 ; les 3 restants se relèvent au `--check` (`re.findall(r".{80}(?<![\w.])confirm\(.{40}", s)`) et s'ajoutent à la table AVANT de tourner — le banc « plus aucun confirm( natif » reste rouge tant qu'il en manque un. Sonde de maillon amont : `s.count("__DZ_TRANSFERT_END__") == 1` sinon abort. `--check` liste les ancres sans écrire.

- [ ] **Step 4 :** `python scripts/patch_bundle_dialogue.py --check` puis sans `--check` (crée `.bak_dialogue`) ; `node --check frontend/dist/assets/index-BEOJX8L5.js` ; `PYTHONIOENCODING=utf-8 python backend/tests/test_dialogue_bundle.py` → 0 FAIL ; `python backend/tests/test_transfert_bundle.py` et `test_montage_bundle.py` toujours verts (les maillons amont intacts).
- [ ] **Step 5 : `version` en queue** — `patch_bundle_version.py` est le dernier maillon : ici aucun `.bak_version` n'existe (non suivi), le bundle courant porte déjà `v2.8.0` ×4, il n'y a rien à rejouer ; `python scripts/repatch_all.py --list` doit montrer `dialogue OK` seul. Noter dans l'en-tête du patcher : « BASELINE : bundle POST-patch version 2.8.0 ; au prochain bump, archiver `.bak_version` puis relancer version seul ».
- [ ] **Step 6 :** commit `--only frontend/patches/dialogue.js scripts/patch_bundle_dialogue.py backend/tests/test_dialogue_bundle.py frontend/dist/assets/index-BEOJX8L5.js` : `bundle : dialogues maison — window.alert remplacé, 11 confirm réécrits en await __dzDialogue.confirmer (patch_bundle_dialogue, queue de chaîne)`.

### Task 4 : preuve en réel (8799, navigateur intégré, 1400 × 900)

- [ ] **Step 1 :** backend du worktree : `DEEPOTUS_DATA_DIR=<scratchpad>/data PORT=8799 python -m uvicorn app.main:app --host 127.0.0.1 --port 8799` (cwd `backend`), en arrière-plan.
- [ ] **Step 2 :** `resize_window` 1400 × 900 ; ouvrir `http://127.0.0.1:8799/vectorlab/` puis un document (créer par `POST /api/vector/docs` avec `v: 1`).
- [ ] **Step 3 :** dans la page : `window.confirm = window.alert = window.prompt = () => { throw new Error("natif interdit"); }` ; `onerror` + `console.error` capturés.
- [ ] **Step 4 :** suppression de calque : ajouter un calque (`VL.menuAction("calqueAjouter")` ou bouton +), clic réel sur la poubelle de `#listeCalques` → `#vlDlg` visible (mesurer `offsetHeight > 0`, bouton `.vl-dlg-danger` présent, `document.activeElement` = bouton Annuler), Entrée → dialogue fermé, calque conservé ; recommencer, clic « Supprimer » → calques −1. Aucune erreur « natif interdit ».
- [ ] **Step 5 :** restauration de brouillon : écrire `localStorage[brouillon_cle(docId)]` avec `brouillon_faire(docId, version, docModifié)`, recharger la page → dialogue « Brouillon non sauvé » avec deux boutons libellés « Restaurer » / « Repartir du serveur » ; « Restaurer » → `etat.sale === true`.
- [ ] **Step 6 :** export lié : `VL.menuAction` de l'export 2× vers la bible (ou appel direct de la fonction) → dialogue de saisie ; Échap → `null`, aucune requête PUT.
- [ ] **Step 7 :** bundle : ouvrir `http://127.0.0.1:8799/` ; `window.confirm = () => { throw … }` ; `window.alert("x")` → un `[role=dialog]` apparaît, Échap le ferme ; `await __dzDialogue.confirmer("Delete ?")` avec clic réel sur « Supprimer » → `true`. Un vrai site : dans la Library, clic poubelle d'une image de test → le dialogue maison s'affiche (Annuler → l'image reste).
- [ ] **Step 8 :** `taskkill /PID <8799> /F` ; consigner les mesures dans le relevé.

### Task 5 : déploiement, mémoire, push

- [ ] **Step 1 :** table `git hash-object` installé / base (`b5ea7ea`) / cible (HEAD) pour : `frontend/vectorlab/{index.html,vectorlab.css,js/core.js,js/mod-dialogue.js,js/mod-*.js touchés}`, `frontend/dist/assets/index-BEOJX8L5.js`. Installé = base pour chaque fichier existant, sinon STOP.
- [ ] **Step 2 :** `_backup_predeploy_2026-09-20-dialogues\` ; copie ; re-table : installé = cible. Statiques seuls : aucune relance.
- [ ] **Step 3 :** relevé en tête de ce plan (livré / TDD / prouvé / déployé / reste) ; mémoire `vectorlab-finitions-ui.md` + ligne MEMORY.md ; `git push`.

## Auto-revue

- Couverture du spec : module pur + DOM (T1), 18 appels (T2), brouillon deux boutons + heure (T2), bundle par patcher à contrat (T3), preuve stub-qui-lève sur suppression / restauration / export (T4), déploiement (T5). Le « composant du bundle s'il existe » : vérifié absent.
- Cohérence des noms : `VL.dialogue.confirmer/informer/saisir`, `dialogue_spec/dialogue_touche/focus_suivant`, `window.__dzDialogue`, `BEGIN/END/PATCHES` du patcher lus par le banc.
