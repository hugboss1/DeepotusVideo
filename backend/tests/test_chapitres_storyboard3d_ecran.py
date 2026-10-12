# -*- coding: utf-8 -*-
"""t189 (G7, plan « Génération IA enrichie », 12/10/2026) — l'ÉCRAN de l'Atelier : storyboard 3D (SAM 3 → Plateau) et
vidéo d'un plan, sur chaque carte du storyboard (le serveur est prouvé par test_storyboard3d / test_chapitres_video).

  [S] statique sur frontend/atelier/atelier.js :
      S1 les boutons de la carte dans l'ordre Image de production → Reconstruire en 3D → Générer le plan → Plateau 3D,
         chacun avec title et aria-label par dzT, et une icône EXISTANTE de la suite (dz-icons.js) ;
      S2 les écouteurs sont branchés, la vignette vidéo est posée dans la carte et suivie ;
      S3 pour CHAQUE tir (objets3d, vidéo) : dialogue maison → `if (!choix) return;` → POST, dans cet ORDRE (une
         confirmation court-circuitée ne passe pas) ; la route appelée est la bonne ;
      S4 aucun dialogue natif (window.prompt / alert / confirm, ni prompt( / confirm( nus) dans le script ;
      S5 DzModelesIA.select sur la nature passée ; objets3d pour le storyboard 3D ; video_fl / video_i2v selon
         keyframe_end ; aucune option `disabled` dans le bloc t189 (une clé manquante reste choisissable) ;
      S6 chaque dzT du bloc t189 existe dans atelier.json, fr et en non vides, mêmes variables ; le défaut first-last
         de l'écran est celui de la route (_VIDEO_PLAN_FL) ; la vignette suit GET /api/jobs/{id}, s'arrête quand la carte
         disparaît, puis lit /api/jobs/{id}/video dans un <video> muet avec contrôles ; les classes CSS existent.
  [N] sous node (fonctions EXTRAITES du script, dialogue et API simulés) :
      N1 natureVideoPlan : video_fl avec une borne de fin, video_i2v sans ;
      N2 objetsDuPlan : personnages d'abord, puis objets, puis décors ; dates / ambiances écartées ;
      N3 debutVideoPlan : borne du Plateau > image de production > croquis > rien ;
      N4 videoPlan : avec fin -> nature video_fl, présélection veo-3.1-fast-fal, /video-models non lu ; sans fin ->
         video_i2v, présélection = défaut de l'app (/video-models) ; annulé -> AUCUN POST ; confirmé -> POST
         /shots/{id}/video {video_model} ;
      N5 objets3dPlan : le champ est prérempli ; annulé -> AUCUN POST ; confirmé -> POST /shots/{id}/objets3d
         {modele, prompt} ; plan sans image -> aucun dialogue.
Run (depuis backend/) : & $PY tests/test_chapitres_storyboard3d_ecran.py
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parent.parent
FRONT = RACINE / "frontend"
NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:500]}")


JS = (FRONT / "atelier" / "atelier.js").read_bytes().decode("utf-8").replace("\r\n", "\n")
CSS = (FRONT / "atelier" / "atelier.css").read_bytes().decode("utf-8")
DICO = json.loads((FRONT / "shared" / "i18n" / "atelier.json").read_text("utf-8"))
ICONES = (FRONT / "shared" / "icons" / "dz-icons.js").read_text("utf-8")
ROUTES = (RACINE / "backend" / "app" / "api" / "routes.py").read_text("utf-8")


def fonction(nom: str) -> str:
    """Le texte d'une fonction de premier niveau (déclaration jusqu'à la première « } » en colonne 0)."""
    m = re.search(r"^(?:async )?function " + re.escape(nom) + r"\(.*?^}\n", JS, flags=re.S | re.M)
    return m.group(0) if m else ""


debut_bloc = JS.find("/* ═════════ t189 (G7)")
fin_bloc = JS.find("/* ═════════ tâche #62 (plan chapitres T6)", debut_bloc)
BLOC = JS[debut_bloc:fin_bloc] if 0 <= debut_bloc < fin_bloc else ""

print("\n[S] statique")
rb = fonction("renderBoard")
pos = [rb.find(f'class="btn ghost act-{k}"') for k in ("prod", "objets3d", "video", "plateau")]
check("S1a les boutons de la carte : prod → objets3d → video → plateau", all(p >= 0 for p in pos) and pos == sorted(pos), pos)
for k, ico in (("objets3d", "dz-lab3d-generer-modele"), ("video", "dz-media-generer-video")):
    m = re.search(r'<button class="btn ghost act-' + k + r'" title="\$\{dzT\("([^"]+)"\)\}" aria-label="\$\{dzT\("([^"]+)"\)\}">\$\{ico\("([^"]+)"\)\}</button>', rb)
    check(f"S1b act-{k} : title et aria-label par dzT, icône {ico}", bool(m) and m.group(3) == ico, m and m.groups())
    check(f"S1c l'icône {ico} existe dans la suite (dz-icons.js)", f'"{ico}"' in ICONES)
check("S2a les écouteurs des deux boutons sont branchés",
      'card.querySelector(".act-objets3d").addEventListener("click", () => objets3dPlan(id));' in rb
      and 'card.querySelector(".act-video").addEventListener("click", () => videoPlan(id));' in rb)
check("S2b la vignette vidéo est posée dans la carte et suivie", "${vignetteVideo(s)}" in rb and "suivreVideo(card, sh());" in rb)

for nom, route in (("objets3dPlan", "/objets3d`"), ("videoPlan", "/video`")):
    f = fonction(nom)
    g = f.find("const choix = await dialoguePlanIA(")
    r = f.find("if (!choix) return;", g) if g >= 0 else -1
    p = f.find('api.send("POST"')
    check(f"S3a {nom} : dialogue maison → if (!choix) return; → POST, dans cet ordre", f and 0 <= g < r < p, (g, r, p))
    check(f"S3b {nom} : un seul POST, vers {route}", f.count('api.send("POST"') == 1 and route in f[p:p + 120], f[p:p + 120])

nat = re.findall(r"\b(?:window\.)?(prompt|alert|confirm)\s*\(", re.sub(r"/\*.*?\*/|//[^\n]*", "", JS, flags=re.S))
check("S4 aucun dialogue natif (prompt / alert / confirm) dans le script", not nat, nat[:5])

dlg = fonction("dialoguePlanIA")
check("S5a dialoguePlanIA remplit le sélecteur par DzModelesIA.select sur la nature demandée",
      "window.DzModelesIA.select(sel, o.nature, { valeur: o.valeur })" in dlg)
check("S5b le storyboard 3D demande la nature « objets3d »", 'nature: "objets3d"' in fonction("objets3dPlan"))
nv = fonction("natureVideoPlan")
check("S5c la vidéo demande video_fl avec une borne de fin, video_i2v sinon",
      'keyframe_end ? "video_fl" : "video_i2v"' in nv and "const nature = natureVideoPlan(s);" in fonction("videoPlan")
      and "nature," in fonction("videoPlan"))
check("S5d aucune option `disabled` dans le bloc t189 (une clé manquante reste choisissable)",
      BLOC and "disabled" not in BLOC and "desactive" not in BLOC)

cles = sorted(set(re.findall(r'"(atelier\.[a-z0-9_.]+)"', BLOC + rb[rb.find("act-objets3d") - 40:rb.find("act-plateau")])))
manque = [c for c in cles if c not in DICO or not DICO[c].get("fr") or not DICO[c].get("en")]
check(f"S6a les {len(cles)} clés dzT du bloc existent, fr et en non vides", len(cles) >= 30 and not manque, manque[:6])
var_ko = [c for c in cles if c in DICO and set(re.findall(r"\{(\w+)\}", DICO[c]["fr"])) != set(re.findall(r"\{(\w+)\}", DICO[c]["en"]))]
check("S6b mêmes variables {x} en fr et en", not var_ko, var_ko)
for c in ("atelier.plan.reconstruire3d", "atelier.plan.objets", "atelier.plan.objets_poses", "atelier.plan.video",
          "atelier.plan.video_fin"):
    check(f"S6c la clé du plan {c} est utilisée", f'"{c}"' in JS and c in DICO)
m = re.search(r'_VIDEO_PLAN_FL = "([^"]+)"', ROUTES)
check("S6d le défaut first-last de l'écran est celui de la route", m and f'const MODELE_VIDEO_FIN = "{m.group(1)}";' in BLOC,
      m and m.group(1))
sv = fonction("suivreVideo")
check("S6e la vignette suit GET /api/jobs/{id}, s'arrête quand la carte disparaît, et au statut final",
      'fetch("/api/jobs/" + encodeURIComponent(job))' in sv and "if (!box.isConnected) return;" in sv
      and 'j.status === "done"' in sv and 'j.status === "failed"' in sv and "setTimeout(tour, st.pas)" in sv
      and "clearTimeout(suivisVideo.get(cle));" in sv and "if (etatsVideo.has(job))" in sv)
check("S6f la vidéo terminée est lue dans un <video> muet avec contrôles (/api/jobs/{id}/video)",
      re.search(r'<video class="shot-video-lecteur" src="/api/jobs/\$\{encodeURIComponent\(job\)\}/video" muted controls', sv) is not None)
check("S6g les classes du dialogue et de la vignette ont leur CSS",
      all(c in CSS for c in (".dzp-box", ".dzp-body", ".dzp-pied", ".dzp-prix", ".dzp-err", ".shot-video video", ".shot-video-etat")))


vp, rd = fonction("videoPlan"), fonction("rendreDevisVideo")
check("S7a le prix de la vidéo est le DEVIS serveur : plus aucun calcul usd × durée dans videoPlan / rendreDevisVideo",
      bool(vp and rd) and not re.search(r"usd\s*\*|\*\s*(?:duree|s\.duration_s)|duration_s\s*\*", vp + rd)
      and "/video/devis?video_model=${encodeURIComponent(modele)}" in vp and "devisRendu: (d) => rendreDevisVideo(d, duree)," in vp,
      re.findall(r".{0,30}\*.{0,30}", vp + rd)[:4])
check("S7b le dialogue relit le devis à chaque changement de modèle et ignore une réponse périmée ; un refus bloque le tir",
      "if (o.devis && sel.value) lireDevis();" in dlg and "if (n !== jeton || sel.value !== modele) return;" in dlg
      and "if (devis && devis.modele === sel.value && devis.refus) { err.textContent = devis.refus; return; }" in dlg)

print("\n[N] sous node")
if not NODE:
    check("N node introuvable", False)
else:
    morceaux = [re.search(r'^const MODELE_VIDEO_FIN = "[^"]+";', JS, flags=re.M).group(0),
                re.search(r"^const tirsEnCours = .*?;$", JS, flags=re.M).group(0)]
    for nom in ("objetsDuPlan", "natureVideoPlan", "debutVideoPlan", "prixDzp", "objets3dPlan", "videoPlan"):
        morceaux.append(fonction(nom))
    code = "\n".join(morceaux)
    prog = r"""
const vm = require("vm");
const CODE = %s;
const journal = { dialogues: [], posts: [], gets: [], toasts: [] };
let reponse = null;
const ctx = {
  console, encodeURIComponent, Number, Math, Promise, JSON,
  shots: [], entities: [],
  location: { href: "" },
  window: { __dzDialogue: { confirmer: async () => false }, DzModelesIA: { prix: (u) => "$" + u } },
  dzT: (k, v) => k + (v ? JSON.stringify(v) : ""),
  toast: (m, e) => journal.toasts.push([m, !!e]),
  renderBoard: () => {},
  api: {
    get: async (p) => { journal.gets.push(p); if (p === "/video-models") return { default: "seedance-2.5" }; return {}; },
    send: async (m, p, b) => { journal.posts.push([m, p, b]); return { n: 3, usd: 0.5, video: "job-1" }; },
  },
  dialoguePlanIA: async (o) => { journal.dialogues.push(o); return reponse; },
};
vm.createContext(ctx);
vm.runInContext(CODE + "\nthis.F = { objetsDuPlan, natureVideoPlan, debutVideoPlan, objets3dPlan, videoPlan };", ctx);
const F = ctx.F;
(async () => {
  const R = {};
  R.n1 = [F.natureVideoPlan({ keyframe_end: "fin.png" }), F.natureVideoPlan({ keyframe_end: null }), F.natureVideoPlan({})];
  const ents = [{ id: "t", kind: "object", name: "Table" }, { id: "d", kind: "date", name: "1912" },
                { id: "v", kind: "character", name: "Vane" }, { id: "s", kind: "decor", name: "Salon" },
                { id: "a", kind: "ambiance", name: "Pluie" }, { id: "i", kind: "character", name: "Ilse" }];
  R.n2 = F.objetsDuPlan({ entities: ["t", "d", "v", "s", "a", "i", "inconnue"] }, ents);
  R.n3 = [F.debutVideoPlan({ keyframe_image: "k.png", image: "p.png", sketch_image: "c.png" }),
          F.debutVideoPlan({ image: "p.png", sketch_image: "c.png" }), F.debutVideoPlan({ sketch_image: "c.png" }),
          F.debutVideoPlan({})].map(d => d && d.fichier);
  ctx.entities = ents;
  ctx.shots.push({ id: "fl", idx: 0, duration_s: 5, keyframe_image: "k.png", keyframe_end: "e.png", entities: ["t", "v"] },
                 { id: "i2v", idx: 1, duration_s: 4, image: "p.png", entities: [] },
                 { id: "nu", idx: 2, duration_s: 4, entities: ["v"] });
  // N4 : la vidéo
  reponse = null; await F.videoPlan("fl");
  const d1 = journal.dialogues.pop();
  R.n4_fl = { nature: d1 && d1.nature, valeur: d1 && d1.valeur, gets: journal.gets.slice(), posts: journal.posts.length,
              toasts: journal.toasts.length,
              images: d1 && d1.images.map(x => x.fichier || null) };
  reponse = null; await F.videoPlan("i2v");
  const d2 = journal.dialogues.pop();
  R.n4_i2v = { nature: d2 && d2.nature, valeur: d2 && d2.valeur, gets: journal.gets.slice(), posts: journal.posts.length,
               toasts: journal.toasts.length };
  reponse = { modele: "kling-3-fl", texte: "" }; await F.videoPlan("fl");
  R.n4_post = journal.posts.slice();
  journal.posts.length = 0; journal.dialogues.length = 0;
  // N5 : le storyboard 3D
  journal.toasts.length = 0;
  reponse = null; await F.objets3dPlan("i2v");
  const d3 = journal.dialogues.pop();
  ctx.shots[1].entities = ["t", "v"];
  reponse = null; await F.objets3dPlan("i2v");
  const d4 = journal.dialogues.pop();
  R.n5_annule = { posts: journal.posts.length, toasts: journal.toasts.length, nature: d4 && d4.nature, champ: d4 && d4.champ.valeur, vide: d3 && d3.champ.valeur };
  reponse = { modele: "sam-3-3d-objects", texte: "Vane, Table" }; await F.objets3dPlan("i2v");
  R.n5_post = journal.posts.slice();
  journal.posts.length = 0; journal.dialogues.length = 0;
  reponse = { modele: "sam-3-3d-objects", texte: "x" }; await F.objets3dPlan("nu");
  R.n5_sans_image = { dialogues: journal.dialogues.length, posts: journal.posts.length };
  console.log(JSON.stringify(R));
})().catch(e => { console.log(JSON.stringify({ erreur: String(e && e.stack || e) })); });
""" % json.dumps(code)
    with tempfile.TemporaryDirectory(prefix="dzsb3d_") as tmp:
        f = pathlib.Path(tmp) / "banc.js"
        f.write_text(prog, "utf-8")
        r = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    try:
        R = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        R = {"erreur": (r.stdout + r.stderr)[-600:]}
    check("N0 le banc node a tourné", "erreur" not in R, R.get("erreur"))
    check("N1 natureVideoPlan : video_fl avec une fin, video_i2v sans", R.get("n1") == ["video_fl", "video_i2v", "video_i2v"], R.get("n1"))
    check("N2 objetsDuPlan : personnages d'abord, puis objets, puis décors ; dates et ambiances écartées",
          R.get("n2") == "Vane, Ilse, Table, Salon", R.get("n2"))
    check("N3 debutVideoPlan : borne du Plateau > production > croquis > rien", R.get("n3") == ["k.png", "p.png", "c.png", None], R.get("n3"))
    a = R.get("n4_fl") or {}
    check("N4a avec fin : nature video_fl, présélection veo-3.1-fast-fal, /video-models non lu, début et fin montrés",
          a.get("nature") == "video_fl" and a.get("valeur") == "veo-3.1-fast-fal" and a.get("gets") == []
          and a.get("images") == ["k.png", "e.png"], a)
    b = R.get("n4_i2v") or {}
    check("N4b sans fin : nature video_i2v, présélection = défaut de l'app (/video-models)",
          b.get("nature") == "video_i2v" and b.get("valeur") == "seedance-2.5" and b.get("gets") == ["/video-models"], b)
    check("N4c annulé : AUCUN POST, aucun toast (rien n'est lancé après le dialogue)",
          a.get("posts") == 0 and b.get("posts") == 0 and a.get("toasts") == 0 and b.get("toasts") == 0, (a, b))
    check("N4d confirmé : POST /shots/fl/video {video_model}",
          R.get("n4_post") == [["POST", "/shots/fl/video", {"video_model": "kling-3-fl"}]], R.get("n4_post"))
    c = R.get("n5_annule") or {}
    check("N5a le champ « Objets à isoler » est prérempli (personnage d'abord), vide sans entité ; nature objets3d",
          c.get("champ") == "Vane, Table" and c.get("vide") == "" and c.get("nature") == "objets3d", c)
    check("N5b annulé : AUCUN POST, aucun toast", c.get("posts") == 0 and c.get("toasts") == 0, c)
    check("N5c confirmé : POST /shots/i2v/objets3d {modele, prompt}",
          R.get("n5_post") == [["POST", "/shots/i2v/objets3d", {"modele": "sam-3-3d-objects", "prompt": "Vane, Table"}]],
          R.get("n5_post"))
    check("N5d plan sans image : ni dialogue ni POST", R.get("n5_sans_image") == {"dialogues": 0, "posts": 0},
          R.get("n5_sans_image"))

print("\n[D] le dialogue vidéo sous node, DOM simulé, devis serveur simulé")
if NODE:
    morceaux = [re.search(r'^const MODELE_VIDEO_FIN = "[^"]+";', JS, flags=re.M).group(0),
                re.search(r"^const ORIGINES_VIDEO = \{.*?\};", JS, flags=re.M | re.S).group(0),
                re.search(r"^const tirsEnCours = .*?;$", JS, flags=re.M).group(0)]
    for nom in ("natureVideoPlan", "debutVideoPlan", "prixDzp", "dialoguePlanIA", "rendreDevisVideo", "videoPlan"):
        morceaux.append(fonction(nom))
    code = "\n".join(morceaux)
    modeles = (FRONT / "shared" / "dz-modeles-ia.js").read_text("utf-8")
    prog = r"""
const vm = require("vm");
function Elt(tag) { this.tagName = tag; this.children = []; this.listeners = {}; this._t = ""; this.className = "";
  this.attrs = {}; this.parent = null; this.value = ""; }
Elt.prototype.appendChild = function (c) { c.parent = this; this.children.push(c); return c; };
Object.defineProperty(Elt.prototype, "textContent", {
  get() { return [this._t].concat(this.children.map(c => c.textContent)).join(" "); },
  set(v) { this._t = String(v); this.children = []; } });
Elt.prototype.setAttribute = function (k, v) { this.attrs[k] = v; };
Elt.prototype.addEventListener = function (k, f) { (this.listeners[k] = this.listeners[k] || []).push(f); };
Elt.prototype.remove = function () { if (this.parent) { this.parent.children = this.parent.children.filter(x => x !== this); this.parent = null; } };
Elt.prototype.focus = function () {};
Elt.prototype.fire = async function (k) { for (const f of this.listeners[k] || []) await f({ target: this }); };
function trouver(e, cls) { if ((" " + e.className + " ").includes(" " + cls + " ")) return e;
  for (const c of e.children) { const r = trouver(c, cls); if (r) return r; } return null; }
function tous(e, tag, out = []) { if (e.tagName === tag) out.push(e); e.children.forEach(c => tous(c, tag, out)); return out; }
const pause = (ms = 15) => new Promise(r => setTimeout(r, ms));
const DEVIS = {
  "veo-3.1-fast-fal": { usd: 0.6, duree_s: 6, debut: { nom: "k.png", origine: "plateau" }, fin: { nom: "e.png" }, refus: null, cle_absente: null },
  "kling-x": { usd: 1.2, duree_s: 5, debut: { nom: "k.png", origine: "plateau" }, fin: { nom: "e.png" }, refus: null, cle_absente: "FAL_KEY" },
  "refuse-x": { usd: null, duree_s: null, debut: { nom: "k.png", origine: "plateau" }, fin: { nom: "e.png" }, refus: "REFUS-DU-SERVEUR", cle_absente: null },
  "lent": { usd: 9.99, duree_s: 8, debut: { nom: "k.png", origine: "plateau" }, fin: { nom: "e.png" }, refus: null, cle_absente: null },
};
const CATALOGUE = ["veo-3.1-fast-fal", "kling-x", "refuse-x", "lent"].map(id => ({ id, label: id, voie: "fal", usd: 0.1, unite: "s", dispo: id !== "kling-x", cle: "FAL_KEY" }));
const J = { gets: [], posts: [], toasts: [] };
let lent = null, enPanne = false;
const ctx = { console, encodeURIComponent, decodeURIComponent, Number, Math, Promise, JSON, setTimeout, clearTimeout, isFinite, String, Error };
ctx.window = ctx;
ctx.document = { createElement: t => new Elt(t), body: new Elt("body"), addEventListener() {}, removeEventListener() {} };
ctx.fetch = async (u) => ({ ok: true, status: 200, json: async () => ({ modeles: CATALOGUE }) });
ctx.dzT = (k, v) => k + (v ? JSON.stringify(v) : "");
ctx.toast = (m, e) => J.toasts.push(m);
ctx.renderBoard = () => {};
ctx.shots = [{ id: "p5", idx: 0, duration_s: 5, keyframe_image: "k.png", keyframe_end: "e.png" }];
ctx.api = {
  get: (p) => { J.gets.push(p);
    const m = /video_model=([^&]*)/.exec(p);
    if (!m) return Promise.resolve({});
    if (enPanne) return Promise.reject(new Error("reseau"));
    const id = decodeURIComponent(m[1]);
    if (id === "lent") return new Promise(r => { lent = () => r(DEVIS.lent); });
    return Promise.resolve(DEVIS[id]); },
  send: async (m, p, b) => { J.posts.push([m, p, b]); return { usd: 0.6, video: "j" }; },
};
vm.createContext(ctx);
vm.runInContext(%s, ctx);
vm.runInContext(%s + "\nthis.videoPlan = videoPlan;", ctx);
(async () => {
  const R = {};
  const body = ctx.document.body;
  const fini = ctx.videoPlan("p5");
  await pause();
  const voile = body.children[0];
  const sel = trouver(voile, "dzp-modele"), prix = trouver(voile, "dzp-prix"), err = trouver(voile, "dzp-err");
  const mention = trouver(voile, "dzp-mention"), imgs = trouver(voile, "dzp-imgs");
  const ok = tous(voile, "button").find(b => b.className.includes("primary"));
  R.ouverture = { sel: sel.value, prix: prix.textContent, imgs: imgs.textContent, devis: J.gets.filter(g => g.includes("/devis")) };
  sel.value = "refuse-x"; await sel.fire("change"); await pause();
  await ok.fire("click"); await pause();
  R.refus = { err: err.textContent, posts: J.posts.length, ouvert: body.children.length, devis: J.gets.filter(g => g.includes("/devis")) };
  sel.value = "lent"; await sel.fire("change");
  sel.value = "kling-x"; await sel.fire("change"); await pause();
  lent(); await pause();
  R.perime = { prix: prix.textContent, mention: mention.textContent, err: err.textContent };
  await ok.fire("click"); await fini; await pause();
  R.cle = { posts: J.posts.slice(), ouvert: body.children.length };
  J.posts.length = 0; enPanne = true;
  const fini2 = ctx.videoPlan("p5"); await pause();
  const v2 = body.children[0];
  R.panne = { prix: trouver(v2, "dzp-prix").textContent };
  await tous(v2, "button").find(b => b.className.includes("primary")).fire("click"); await fini2; await pause();
  R.panne.posts = J.posts.slice();
  console.log(JSON.stringify(R));
})().catch(e => console.log(JSON.stringify({ erreur: String(e && e.stack || e) })));
""" % (json.dumps(modeles), json.dumps(code))
    with tempfile.TemporaryDirectory(prefix="dzsb3dd_") as tmp:
        f = pathlib.Path(tmp) / "banc_dom.js"
        f.write_text(prog, "utf-8")
        r = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    try:
        D = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        D = {"erreur": (r.stdout + r.stderr)[-800:]}
    check("D0 le banc DOM a tourné", "erreur" not in D, D.get("erreur"))
    o = D.get("ouverture") or {}
    check("D1 à l'ouverture : devis serveur demandé pour le modèle présélectionné",
          o.get("sel") == "veo-3.1-fast-fal" and o.get("devis") == ["/shots/p5/video/devis?video_model=veo-3.1-fast-fal"], o)
    check("D2 le dialogue affiche le devis : $0.60 et 6 s générées pour un plan de 5 s, jamais $0.50",
          "$0.60" in o.get("prix", "") and '"n":6' in o.get("prix", "") and '"plan":5' in o.get("prix", "")
          and "$0.50" not in o.get("prix", ""), o.get("prix"))
    check("D3 l'origine du début et la fin viennent du devis (borne du Plateau, borne de fin)",
          "atelier.at2_video.src_plateau" in o.get("imgs", "") and "atelier.plan.video_fin" in o.get("imgs", ""), o.get("imgs"))
    rf = D.get("refus") or {}
    check("D4 changement de modèle ⇒ nouveau devis avec video_model", "/shots/p5/video/devis?video_model=refuse-x" in rf.get("devis", []), rf)
    check("D5 refus du devis ⇒ affiché en ligne, AUCUN POST, le dialogue reste ouvert",
          "REFUS-DU-SERVEUR" in rf.get("err", "") and rf.get("posts") == 0 and rf.get("ouvert") == 1, rf)
    pe = D.get("perime") or {}
    check("D6 une réponse de devis périmée (modèle changé entre-temps) est ignorée",
          "$1.20" in pe.get("prix", "") and "$9.99" not in pe.get("prix", "") and pe.get("err", "").strip() == "", pe)
    check("D7 clé absente ⇒ mention « clé X à ajouter » affichée, sans bloquer", "FAL_KEY" in pe.get("mention", ""), pe)
    ck = D.get("cle") or {}
    check("D8 ... et le POST part avec le modèle sans clé (le 503 vient au lancement)",
          ck.get("posts") == [["POST", "/shots/p5/video", {"video_model": "kling-x"}]] and ck.get("ouvert") == 0, ck)
    pn = D.get("panne") or {}
    check("D9 devis en échec réseau : coût « inconnu » dit, et le tir reste possible",
          "atelier.at2_video.devis_ko" in pn.get("prix", "") and len(pn.get("posts", [])) == 1, pn)

print("\n[M] suivi borné, anti-double tir, objets écartés (sous node)")
if NODE:
    TIRS = re.search(r"^const tirsEnCours = .*?;$", JS, flags=re.M).group(0)
    morceaux = [re.search(r'^const MODELE_VIDEO_FIN = "[^"]+";', JS, flags=re.M).group(0), TIRS,
                re.search(r"^const SUIVI_VIDEO = .*?;$", JS, flags=re.M).group(0),
                re.search(r"^const etatsVideo = .*?;$", JS, flags=re.M).group(0)]
    for nom in ("objetsDuPlan", "natureVideoPlan", "debutVideoPlan", "prixDzp", "objets3dPlan", "videoPlan", "suivreVideo"):
        morceaux.append(fonction(nom))
    code = "\n".join(morceaux)
    prog = r"""
const vm = require("vm");
const J = { gets: [], posts: [], toasts: [], dialogues: 0, delais: [] };
let maintenant = 1000000, reponses = [], minuteur = null, dialogue = null;
const ctx = {
  console, encodeURIComponent, Number, Math, Promise, JSON, String,
  Date: { now: () => maintenant },
  setTimeout: (f, ms) => { J.delais.push(ms); minuteur = f; return J.delais.length; },
  clearTimeout: () => {},
  esc: (s) => String(s), escA: (s) => String(s),
  shots: [], entities: [], location: { href: "" },
  window: { __dzDialogue: { confirmer: async () => false }, DzModelesIA: { prix: (u) => "$" + u } },
  dzT: (k, v) => k + (v ? JSON.stringify(v) : ""),
  toast: (m) => J.toasts.push(m),
  renderBoard: () => {},
  fetch: async (u) => { J.gets.push(u); const r = reponses.shift() || { status: 200, body: { status: "generating_video", progress: 10 } };
    return { status: r.status, ok: r.status === 200, json: async () => r.body }; },
  api: { get: async () => ({ default: "seedance-2.5" }),
         send: async (m, p, b) => { J.posts.push([m, p, b]);
           return p.endsWith("/objets3d") ? { n: 32, tronques: 5 } : { id: "v", video: "job-neuf", job_id: "job-neuf", usd: 0.6 }; } },
  dialoguePlanIA: (o) => { J.dialogues += 1; return new Promise(r => { dialogue = r; }); },
};
vm.createContext(ctx);
vm.runInContext(%s + "\nthis.F = { objets3dPlan, videoPlan, suivreVideo };", ctx);
const F = ctx.F;
const pause = () => new Promise(r => setImmediate(r));
const borne = (p) => Promise.race([p, new Promise(r => setTimeout(r, 300))]);   // une promesse orpheline ne fige pas le banc
function carte() { const box = { isConnected: true, innerHTML: "" }; return { box, querySelector: () => box }; }
async function tourner() { const f = minuteur; minuteur = null; if (f) { await f(); await pause(); } }
(async () => {
  const R = {};
  // I1 : 404, 404 puis 200 -> jamais « introuvable »
  const c1 = carte(); reponses = [{ status: 404 }, { status: 404 }, { status: 200, body: { status: "queued", progress: 0 } }];
  F.suivreVideo(c1, { id: "a", video: "j1" }); await pause(); const h1 = [c1.box.innerHTML];
  await tourner(); h1.push(c1.box.innerHTML); await tourner(); h1.push(c1.box.innerHTML);
  R.i1 = { html: h1, minuteur: !!minuteur };
  c1.box.isConnected = false; await tourner();
  // 404 x3 -> introuvable, terminal
  const c2 = carte(); reponses = [{ status: 404 }, { status: 404 }, { status: 404 }]; J.delais.length = 0;
  F.suivreVideo(c2, { id: "b", video: "j2" }); await pause(); await tourner(); await tourner();
  R.introuvable = { html: c2.box.innerHTML, minuteur: !!minuteur };
  // job done -> plus aucun GET au re-rendu
  const c3 = carte(); reponses = [{ status: 200, body: { status: "done" } }];
  F.suivreVideo(c3, { id: "c", video: "j3" }); await pause();
  const n = J.gets.length; const c3b = carte();
  F.suivreVideo(c3b, { id: "c", video: "j3" }); await pause();
  R.done = { html: c3b.box.innerHTML, gets: J.gets.length - n, minuteur: !!minuteur };
  // pas croissant puis arrêt après 30 min
  const c4 = carte(); reponses = []; J.delais.length = 0;
  F.suivreVideo(c4, { id: "d", video: "j4" }); await pause();
  for (let k = 0; k < 7; k++) await tourner();
  R.pas = J.delais.slice(0, 8);
  maintenant += 31 * 60 * 1000; J.delais.length = 0; await tourner();
  R.arret = { html: c4.box.innerHTML, delais: J.delais.length };
  // double clic vidéo : un seul dialogue, un seul POST, toast « déjà en cours »
  ctx.shots.push({ id: "v", idx: 0, duration_s: 4, image: "p.png", entities: [] });
  const p1 = F.videoPlan("v"); await pause(); await pause();
  await borne(F.videoPlan("v"));
  R.double = { dialogues: J.dialogues, toast: J.toasts.filter(t => t.startsWith("atelier.at2_dzp.deja_en_cours")).length };
  dialogue({ modele: "veo" }); await borne(p1);
  R.double.posts = J.posts.length;
  R.m9 = Object.keys(ctx.shots[0]).sort();
  // le verrou est libéré : un nouveau clic rouvre le dialogue
  const p2 = F.videoPlan("v"); await pause(); await pause(); R.libere = J.dialogues; dialogue(null); await p2;
  // objets3d : double clic + objets écartés dits
  J.posts.length = 0; J.toasts.length = 0; J.dialogues = 0;
  const o1 = F.objets3dPlan("v"); await pause();
  await borne(F.objets3dPlan("v"));
  dialogue({ modele: "sam-3-3d-objects", texte: "x" }); await borne(o1);
  R.obj = { dialogues: J.dialogues, posts: J.posts.length, toasts: J.toasts.slice() };
  console.log(JSON.stringify(R));
})().catch(e => console.log(JSON.stringify({ erreur: String(e && e.stack || e) })));
""" % json.dumps(code)
    with tempfile.TemporaryDirectory(prefix="dzsb3dm_") as tmp:
        f = pathlib.Path(tmp) / "banc_m.js"
        f.write_text(prog, "utf-8")
        r = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    try:
        M = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:  # noqa: BLE001
        M = {"erreur": (r.stdout + r.stderr)[-800:]}
    check("M0 le banc node a tourné", "erreur" not in M, M.get("erreur"))
    i1 = M.get("i1") or {}
    check("M1 I1 : 404, 404 puis 200 ⇒ jamais « introuvable » (en attente, puis l'état du job), le suivi continue",
          len(i1.get("html", [])) == 3 and not any("introuvable" in h for h in i1["html"])
          and "atelier.at2_video.attente" in i1["html"][0] and "atelier.at2_video.progres" in i1["html"][2] and i1.get("minuteur"), i1)
    it = M.get("introuvable") or {}
    check("M2 404 au 3e tour consécutif ⇒ « introuvable », et le suivi s'arrête",
          "atelier.at2_video.introuvable" in it.get("html", "") and not it.get("minuteur"), it)
    dn = M.get("done") or {}
    check("M3 job terminé ⇒ au re-rendu, le lecteur revient SANS aucun GET ni minuteur",
          dn.get("gets") == 0 and "<video" in dn.get("html", "") and not dn.get("minuteur"), dn)
    check("M4 pas croissant 4 s ×1,5 jusqu'à 30 s", M.get("pas") == [4000, 6000, 9000, 13500, 20250, 30000, 30000, 30000], M.get("pas"))
    ar = M.get("arret") or {}
    check("M5 au-delà de 30 min de suivi : « suivi arrêté », plus de minuteur",
          "atelier.at2_video.suivi_arrete" in ar.get("html", "") and ar.get("delais") == 0, ar)
    db = M.get("double") or {}
    check("M6 double clic vidéo pendant le vol : un seul dialogue, un seul POST, toast « déjà en cours »",
          db.get("dialogues") == 1 and db.get("posts") == 1 and db.get("toast") == 1, db)
    check("M7 le verrou est libéré à la fin (finally) : un nouveau clic rouvre le dialogue", M.get("libere") == 2, M.get("libere"))
    check("M8 M9 : après le POST vidéo, seul `video` entre dans le plan (ni job_id ni usd)",
          M.get("m9") == ["duration_s", "entities", "id", "idx", "image", "video"], M.get("m9"))
    ob = M.get("obj") or {}
    check("M9 double clic storyboard 3D : un seul dialogue, un seul POST",
          ob.get("dialogues") == 1 and ob.get("posts") == 1, ob)
    check("M10 objets écartés (tronques > 0) : le toast le dit",
          any(t.startswith("atelier.plan.objets_poses_tronques") and '"m":5' in t and '"n":32' in t for t in ob.get("toasts", [])), ob)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
