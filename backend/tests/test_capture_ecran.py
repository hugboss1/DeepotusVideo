# -*- coding: utf-8 -*-
"""t315 (28/10/2026) (D1, tâches 3 et 4) — l'enregistreur de l'app côté écran, joué sous node (aucun navigateur).
Plan docs/superpowers/plans/2026-10-28-t315-capture.md, spec boîte à outils §8.1-8.3.
[L] dz-capture-logique.js : l'élément cliqué ne donne jamais la valeur d'un champ ni le texte d'un non-contrôle ;
    zone secrète (data-dz-secret, type=password) ; normalisation et passage fenêtre -> scène (rogné, hors cadre
    null) ; encart borné ; MIME (MP4 d'abord, WebM ensuite, audio) ; surface (onglet, cet onglet) ; piste des clics
    (écran dédoublonné, secret sans libellé, t croissant) ; zoom en direct (1 hors fenêtre, borné au cadre) ;
[S] dz-capture-scene.js (faux canvas) : calques triés par z, CAVIARDAGE posé d'office, dernier, indélébile (z ≥ 900
    refusé, retrait ignoré, second caviardage refusé) ; mesure des secrets donnée à la création, après les crochets ; caches peints APRÈS
    l'écran ; mesure en panne -> image noire ; calque en panne sauté ; horloge démarrée/arrêtée ; flux unique ;
[U] dz-capture.js sous faux DOM : bouton « Enregistrer » dans la barre (avant « Demander »), grisé sans
    getDisplayMedia ; boîte de départ (caméra JAMAIS cochée d'office, même gardée cochée) ; refus du partage, surface
    « écran entier », autre onglet : ni micro ni caméra ouverts, aucune session demandée, pistes coupées ; anglais ;
[P] livraison : copies shared == dist, index.html charge le module une fois après dz-whatsapp-espace.js ; aucune
    écoute clavier hors du piège Tab des boîtes ; aucune lecture de `.value` dans la logique des clics ; ni
    alert/confirm/prompt ni emoji ; clés capture.* FR/EN à 3 segments, mêmes variables, toutes employées, assemblées.
Run (depuis backend/) : & $PY tests/test_capture_ecran.py"""
import json, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    try:
        cond = cond() if callable(cond) else cond
    except Exception as e:                                  # noqa: BLE001
        cond, detail = False, f"{detail} {e!r}"
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:700]}")


SH = REPO / "frontend" / "shared"
DI = REPO / "frontend" / "dist" / "shared"
FICHIERS = ["dz-capture.js", "dz-capture-logique.js", "dz-capture-scene.js"]
DICO = json.loads((SH / "i18n" / "capture.json").read_text("utf-8"))
TXT = (SH / "dz-capture.js").read_text("utf-8")
LOG = (SH / "dz-capture-logique.js").read_text("utf-8")
SCN = (SH / "dz-capture-scene.js").read_text("utf-8")


def node(script: str) -> dict:
    d = pathlib.Path(tempfile.mkdtemp(prefix="dzcapjs_"))
    f = d / "banc.mjs"
    f.write_text(script, "utf-8")
    r = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    out = r.stdout.strip().splitlines()
    if r.returncode or not out:
        raise RuntimeError((r.stderr or r.stdout)[-1500:])
    return json.loads(out[-1])


URL = lambda nom: (SH / nom).resolve().as_uri()               # noqa: E731

# ── [L] la logique pure ──
print("[L] dz-capture-logique.js")
L = node(r"""
const L = await import(%s);
function N(tag, attrs, texte, parent){ return {tagName: tag.toUpperCase(), attrs: attrs||{}, innerText: texte, textContent: texte,
  value: "VALEUR-SAISIE", parent: parent||null, parentNode: parent||null,
  getAttribute(k){ return k in this.attrs ? this.attrs[k] : null; },
  closest(sel){ let x=this; while(x){ if(match(x,sel)) return x; x=x.parent; } return null; } }; }
function match(x, sel){ return sel.split(",").map(s=>s.trim()).some(s=>{
  if (s==='[data-dz-secret]') return x.getAttribute('data-dz-secret')!==null;
  if (s==='input[type="password"]') return x.tagName==='INPUT' && x.getAttribute('type')==='password';
  let m=/^([a-z]+)(?:\[([\w-]+)(?:="([^"]*)")?\])?$/.exec(s) || /^\[([\w-]+)(?:="([^"]*)")?\]$/.exec(s);
  if (!m) return false;
  if (s.startsWith('[')) return x.getAttribute(m[1])!==null && (m[2]===undefined || x.getAttribute(m[1])===m[2]);
  return x.tagName.toLowerCase()===m[1] && (!m[2] || (x.getAttribute(m[2])!==null && (m[3]===undefined || x.getAttribute(m[2])===m[3])));
}); }
const out = {};
const bouton = N("button", {title: "Lancer"}, "Générer\nla vidéo");
const span = N("span", {}, "x", bouton);
out.c1 = L.cibleClic(span);
const champ = N("input", {placeholder: "Ta clé", type: "text"}, "");
out.c2 = L.cibleClic(champ);
out.c3 = L.cibleClic(N("button", {}, "x".repeat(41)));
out.c4 = L.cibleClic(N("div", {"aria-label": "Zone"}, "Un long texte de contenu"));
const ecran = N("div", {"data-dz-secret": "ecran"}, "");
out.s1 = L.estSecret(N("b", {}, "k", N("div", {}, "", ecran)));
out.s2 = L.estSecret(N("input", {type: "password"}, ""));
out.s3 = L.estSecret(N("input", {type: "text"}, ""));
out.s4 = L.estSecret({parentNode: ecran});
out.n1 = L.normaliser(150, 75, {x: 50, y: 25, l: 200, h: 100});
out.n2 = L.normaliser(-10, 900, {x: 0, y: 0, l: 100, h: 100});
out.v1 = L.versScene({x: 60, y: 35, l: 40, h: 20}, {x: 50, y: 25, l: 200, h: 100}, 400, 200);
out.v2 = L.versScene({x: 0, y: 0, l: 10, h: 10}, {x: 50, y: 25, l: 200, h: 100}, 400, 200);
out.v3 = L.versScene({x: 230, y: 100, l: 100, h: 100}, {x: 50, y: 25, l: 200, h: 100}, 400, 200);
out.e1 = L.bornerEncart({x: 0.95, y: -1, l: 2, h: 0.01});
out.e2 = L.bornerEncart(null);
out.f = [L.formeLue("vif"), L.formeLue("rond")];
out.m1 = L.choisirMime(m => true, "scene");
out.m2 = L.choisirMime(m => m.startsWith("video/webm"), "video");
out.m3 = L.choisirMime(m => m.startsWith("audio/webm"), "audio");
out.m4 = L.choisirMime(m => { throw new Error("x"); }, "scene");
out.vs = [L.verifierSurface({displaySurface: "monitor"}, null, "j"), L.verifierSurface({displaySurface: "window"}, null, "j"),
  L.verifierSurface({displaySurface: "browser"}, {handle: "j"}, "j"), L.verifierSurface({displaySurface: "browser"}, {handle: "z"}, "j"),
  L.verifierSurface({displaySurface: "browser"}, null, "j"), L.verifierSurface(null, null, "j"),
  L.verifierSurface({displaySurface: "browser"}, null, "j", true)];
let h = 1000; const P = L.creerPiste(() => h);
P.debut(); h = 1100; P.ecran("quick"); h = 1200; P.ecran("quick"); h = 1300; P.ecran("settings");
h = 1450; P.clic({x: .1, y: .2, bouton: 9, ecran: "settings", secret: true, cible: {balise: "input", role: "", t: "Clé", i: "sk-ant"}});
h = 1500; P.clic({x: .3, y: .4, bouton: 2, ecran: "settings", cible: {balise: "button", role: "", t: "Ouvrir", i: ""}});
out.p = P.json();
out.z0 = L.vueZoom(null, 5, 100, 100);
out.z1 = L.vueZoom({cx: 100, cy: 100, debut: 0}, L.DUREE_ZOOM / 2, 100, 100);
out.z2 = L.vueZoom({cx: 50, cy: 50, debut: 0}, L.DUREE_ZOOM + 1, 100, 100);
out.d = [L.duree(0), L.duree(61500), L.duree(-5)];
out.css = L.CSS_MASQUE; out.sel = L.SELECTEURS_SECRETS;
console.log(JSON.stringify(out));
""" % json.dumps(URL("dz-capture-logique.js")))
check("L1 libellé d'un contrôle : première ligne, infobulle title", L["c1"] == {"balise": "button", "role": "", "t": "Générer", "i": "Lancer"}, L["c1"])
check("L2 un champ ne donne JAMAIS sa valeur ni son texte : placeholder seul", L["c2"]["t"] == "" and L["c2"]["i"] == "Ta clé"
      and "VALEUR" not in json.dumps(L), L["c2"])
check("L3 libellé de plus de 40 caractères écarté", L["c3"]["t"] == "")
check("L4 un non-contrôle ne donne pas son texte (contenu), seulement son aria-label", L["c4"] == {"balise": "div", "role": "", "t": "", "i": "Zone"}, L["c4"])
check("L5 zone secrète : enfant d'un écran secret, mot de passe ; pas un champ texte ; nœud sans closest",
      L["s1"] and L["s2"] and not L["s3"] and L["s4"])
check("L6 normaliser : 0..1 dans le cadre, borné", L["n1"] == {"x": 0.5, "y": 0.5} and L["n2"] == {"x": 0, "y": 1})
check("L7 fenêtre -> scène (×2), hors cadre null, rogné au bord", L["v1"] == {"x": 20, "y": 20, "l": 80, "h": 40}
      and L["v2"] is None and L["v3"] == {"x": 360, "y": 150, "l": 40, "h": 50}, (L["v1"], L["v3"]))
check("L8 encart borné (taille 0,08..0,6, tenu dans le cadre) ; défaut", L["e1"] == {"x": 0.4, "y": 0, "l": 0.6, "h": 0.08}
      and L["e2"]["l"] == 0.22, L["e1"])
check("L9 forme inconnue -> cercle", L["f"] == ["vif", "cercle"])
check("L10 MIME : MP4/H.264 d'abord, WebM ensuite, audio Opus ; navigateur muet -> vide",
      L["m1"].startswith("video/mp4;codecs=avc1") and L["m2"] == "video/webm;codecs=vp9" and L["m3"] == "audio/webm;codecs=opus"
      and L["m4"] == "")
check("L11 surface : écran entier et fenêtre refusés, cet onglet ok, autre onglet refusé ; sans poignée : inconnu si "
      "le navigateur ne sait pas la lire, AUTRE ONGLET s'il le sait (revue finale C1)",
      L["vs"] == ["pas_onglet", "pas_onglet", "ok", "autre_onglet", "inconnu", "pas_onglet", "autre_onglet"], L["vs"])
ev = L["p"]["evenements"]
check("L12 piste : écran dédoublonné, t depuis le début", [e.get("ecran") for e in ev if e["type"] == "ecran"] == ["quick", "settings"]
      and [e["t"] for e in ev] == [100, 300, 450, 500], ev)
check("L13 clic secret : ni libellé ni infobulle ; bouton inconnu -> 0", ev[2].get("secret") is True
      and ev[2]["cible"]["t"] == "" and ev[2]["cible"]["i"] == "" and ev[2]["bouton"] == 0 and "sk-ant" not in json.dumps(ev))
check("L14 clic ordinaire : cible gardée, bouton droit", ev[3]["cible"]["t"] == "Ouvrir" and ev[3]["bouton"] == 2)
check("L15 zoom : 1 hors fenêtre, ~1,5 au milieu, décalage borné au cadre",
      L["z0"] == {"k": 1, "ox": 0, "oy": 0} and abs(L["z1"]["k"] - 1.5) < 1e-6 and L["z1"]["ox"] == -50 and L["z1"]["oy"] == -50
      and L["z2"]["k"] == 1, L["z1"])
check("L16 minuteur mm:ss", L["d"] == ["00:00", "01:01", "00:00"])
check("L17 masque : le sélecteur couvre data-dz-secret ET type=password ; la feuille floute les deux et rend l'écran inerte",
      L["sel"] == '[data-dz-secret], input[type="password"]' and 'html[data-dz-capture] input[type="password"]' in L["css"]
      and "blur(" in L["css"] and '[data-dz-secret="ecran"]' in L["css"] and "pointer-events:none" in L["css"])

# ── [S] la scène, faux canvas ──
print("[S] dz-capture-scene.js")
S = node(r"""
const M = await import(%s);
const ops = [];
function Ctx(){ return new Proxy({}, {get(t,k){ if (k in t) return t[k]; return (...a) => ops.push([k, ...a.map(x => typeof x === "object" ? "obj" : x)]); },
  set(t,k,v){ t[k]=v; ops.push(["=" + k, v]); return true; }}); }
const doc = { createElement(){ return { width: 0, height: 0, getContext(){ return Ctx(); }, captureStream(f){ ops.push(["captureStream", f]); return {id: "flux"}; } }; } };
let tic = null, arrets = 0;
const horloge = { demarrer(f, ms){ tic = f; ops.push(["horloge", ms]); return 7; }, arreter(id){ arrets++; } };
let MESURE = () => [];
const sc = M.creerScene({largeur: 400, hauteur: 200, fps: 25, doc, horloge, maintenant: () => 1000, secrets: (s) => MESURE(s)});
const out = {};
out.c0 = sc.calques();
sc.ajouterCalque(M.calqueEcran()); sc.ajouterCalque({id: "skin", z: 700, dessiner(){ ops.push(["skin"]); }});
sc.ajouterCalque({id: "fond", z: 10, dessiner(){ ops.push(["fond"]); }});
sc.ajouterCalque(M.calqueClics()); sc.ajouterCalque(M.calqueEncart());
out.c1 = sc.calques().map(c => c.id);
const essai = (f) => { try { f(); return "ok"; } catch (e) { return "refus"; } };
out.r = [essai(() => sc.ajouterCalque({id: "dessus", z: 900, dessiner(){}})), essai(() => sc.ajouterCalque({id: "dessus", z: 5000, dessiner(){}})),
  essai(() => sc.ajouterCalque({id: "caviardage", z: 0, dessiner(){}})), essai(() => sc.ajouterCalque({id: "x"}))];
sc.retirerCalque("caviardage"); out.c2 = sc.calques().map(c => c.id);
let mesures = 0;
const video = {readyState: 4, videoWidth: 800, videoHeight: 400};
sc.source("ecran", video);
MESURE = (s) => { mesures++; return [{x: 10, y: 20, l: 30, h: 40, ecran: false}, {x: 200, y: 50, l: 150, h: 100, ecran: true}]; };
// un skin qui tente de figer les secrets (revue finale I3) : la mesure passe après lui
const retirer = sc.surImage((s) => { s.etat.secrets = []; });
sc.etat.textes.masque = "Masqué";
ops.length = 0; sc.dessiner(1000);
out.ops = ops.map(o => o[0]);
const iEcran = ops.findIndex(o => o[0] === "drawImage"), iSkin = ops.findIndex(o => o[0] === "skin");
const caches = ops.map((o, i) => [o, i]).filter(([o]) => o[0] === "fillRect" && o[3] !== 400);
out.ordre = {iEcran, iSkin, caches: caches.map(([o, i]) => i), texte: ops.filter(o => o[0] === "fillText").map(o => o[1])};
out.mesures = mesures; retirer(); out.surImage = typeof sc.avantImage;
MESURE = () => { throw new Error("mesure en panne"); };
ops.length = 0; sc.dessiner(1000);
const fr = ops.filter(o => o[0] === "fillRect");
out.noir = fr.length ? fr[fr.length - 1] : null;
MESURE = () => [];
sc.ajouterCalque({id: "panne", z: 300, dessiner(){ throw new Error("x"); }});
ops.length = 0; sc.dessiner(1000); out.apresPanne = ops.some(o => o[0] === "skin");
sc.demarrer(); sc.demarrer(); out.actif = sc.actif(); out.horloge = ops.filter(o => o[0] === "horloge");
sc.arreter(); sc.arreter(); out.arrets = arrets; out.actif2 = sc.actif();
const f1 = sc.flux(30), f2 = sc.flux(12); out.flux = [f1 === f2, ops.filter(o => o[0] === "captureStream").length];
console.log(JSON.stringify(out));
""" % json.dumps(URL("dz-capture-scene.js")))
check("S1 creerScene pose d'office le caviardage", S["c0"] == [{"id": "caviardage", "z": 900}], S["c0"])
check("S2 calques triés par z, caviardage dernier", S["c1"] == ["fond", "ecran", "clics", "encart", "skin", "caviardage"], S["c1"])
check("S3 z ≥ 900 refusé, second caviardage refusé, calque sans dessin refusé", S["r"] == ["refus", "refus", "refus", "refus"], S["r"])
check("S4 retirer le caviardage est sans effet", S["c2"][-1] == "caviardage")
check("S5 la mesure des secrets (donnée à la création) passe à chaque image, APRÈS les crochets : un skin ne la fige pas ; "
      "plus d'avantImage remplaçable", S["mesures"] == 1 and S["surImage"] == "undefined")
o = S["ordre"]
check("S6 caches peints APRÈS l'écran et le skin (deux secrets -> deux caches), texte sur l'écran secret",
      o["iEcran"] >= 0 and len(o["caches"]) == 2 and all(i > o["iEcran"] and i > o["iSkin"] for i in o["caches"])
      and o["texte"] == ["Masqué"], o)
check("S7 mesure en panne -> la dernière peinture couvre TOUTE l'image", S["noir"] == ["fillRect", 0, 0, 400, 200], S["noir"])
check("S8 un calque en panne est sauté, les suivants dessinent", S["apresPanne"] is True)
check("S9 horloge démarrée une fois (40 ms à 25 i/s), arrêtée une fois", S["actif"] and S["horloge"] == [["horloge", 40]]
      and S["arrets"] == 1 and not S["actif2"], S)
check("S10 flux unique (captureStream une fois)", S["flux"] == [True, 1], S["flux"])

# ── [U] l'enregistreur sous faux DOM ──
print("[U] dz-capture.js")
FAUX = r"""
const dico = %s, LANG = "%s";
globalThis.window = globalThis;
globalThis.location = {origin: "http://127.0.0.1:8797", href: "http://127.0.0.1:8797/"};
function Noeud(tag){ this.tagName = String(tag).toUpperCase(); this.enfants = []; this.attrs = {}; this.ecoutes = {}; this._t = ""; this.parent = null;
  this.style = {cssText: ""}; this.checked = false; this.disabled = false; this.value = ""; this.title = ""; this.innerHTML = ""; this.className = ""; }
Object.defineProperty(Noeud.prototype, "textContent", {get(){ return this._t + this.enfants.map(e => e.textContent).join(""); },
  set(v){ this._t = String(v); this.enfants = []; }});
Object.defineProperty(Noeud.prototype, "parentNode", {get(){ return this.parent; }});
Object.defineProperty(Noeud.prototype, "firstChild", {get(){ return this.enfants[0] || null; }});
Object.defineProperty(Noeud.prototype, "lastElementChild", {get(){ return this.enfants[this.enfants.length - 1] || null; }});
Object.defineProperty(Noeud.prototype, "isConnected", {get(){ let n = this; while (n.parent) n = n.parent; return n === document.documentElement; }});
Noeud.prototype.setAttribute = function(k, v){ this.attrs[k] = String(v); if (k === "id") this.id = String(v); };
Noeud.prototype.getAttribute = function(k){ return k in this.attrs ? this.attrs[k] : null; };
Noeud.prototype.removeAttribute = function(k){ delete this.attrs[k]; };
Noeud.prototype.toggleAttribute = function(k, b){ if (b) this.attrs[k] = ""; else delete this.attrs[k]; return b; };
Noeud.prototype.appendChild = function(e){ if (e.parent) e.remove(); e.parent = this; this.enfants.push(e); return e; };
Noeud.prototype.append = function(...l){ l.forEach(e => this.appendChild(typeof e === "string" ? texte(e) : e)); };
Noeud.prototype.replaceChildren = function(...l){ this.enfants = []; this.append(...l); };
Noeud.prototype.insertBefore = function(e, ref){ if (e.parent) e.remove(); if (!ref) return this.appendChild(e); const i = this.enfants.indexOf(ref);
  e.parent = this; this.enfants.splice(i, 0, e); return e; };
Noeud.prototype.remove = function(){ if (this.parent) { this.parent.enfants = this.parent.enfants.filter(x => x !== this); this.parent = null; } };
Noeud.prototype.addEventListener = function(t, f){ (this.ecoutes[t] = this.ecoutes[t] || []).push(f); };
Noeud.prototype.removeEventListener = function(t, f){ this.ecoutes[t] = (this.ecoutes[t] || []).filter(g => g !== f); };
Noeud.prototype.focus = function(){ document.activeElement = this; };
Noeud.prototype.click = function(){ (this.ecoutes.click || []).forEach(f => f({target: this, preventDefault(){}})); };
function tous(n, p, o = []){ if (p(n)) o.push(n); n.enfants.forEach(e => tous(e, p, o)); return o; }
function correspond(n, s){
  if (s === "#root header") return n.tagName === "HEADER" && !!tous(document.getElementById("root"), x => x === n).length;
  if (s === ".dzAgentBtn") return n.className === "dzAgentBtn";
  let m = /^input\[name="(\w+)"\]:checked$/.exec(s); if (m) return n.tagName === "INPUT" && n.attrs.name === m[1] && n.checked;
  m = /^\[([\w-]+)(?:="([^"]*)")?\]$/.exec(s); if (m) return n.getAttribute(m[1]) !== null && (m[2] === undefined || n.getAttribute(m[1]) === m[2]);
  return n.tagName.toLowerCase() === s; }
Noeud.prototype.querySelectorAll = function(sel){ const ps = sel.split(",").map(s => s.trim()); return tous(this, n => n !== this && ps.some(p => correspond(n, p))); };
Noeud.prototype.querySelector = function(sel){ return this.querySelectorAll(sel)[0] || null; };
function texte(t){ const n = new Noeud("#text"); n._t = t; return n; }
const html = new Noeud("html"), head = new Noeud("head"), body = new Noeud("body");
html.appendChild(head); html.appendChild(body);
globalThis.document = { documentElement: html, head, body, activeElement: null, createElement: t => new Noeud(t), createTextNode: texte,
  getElementById: i => tous(html, n => n.id === i)[0] || null, querySelector: s => html.querySelector(s), querySelectorAll: s => html.querySelectorAll(s) };
const root = new Noeud("div"); root.setAttribute("id", "root"); body.appendChild(root);
const header = new Noeud("header"); root.appendChild(header);
const agent = new Noeud("button"); agent.className = "dzAgentBtn"; header.appendChild(agent);
header.appendChild(new Noeud("button"));
globalThis.MutationObserver = function(){}; MutationObserver.prototype.observe = function(){};
const STOCK = {dz_view: "settings", dz_capture_options: JSON.stringify({camera: true, voix: true, mode: "app"})};
globalThis.localStorage = {getItem: k => k in STOCK ? STOCK[k] : null, setItem: (k, v) => { STOCK[k] = String(v); }};
globalThis.dzT = (k, v) => { let s = dico[k] ? dico[k][LANG] : "<absente " + k + ">"; for (const [a, b] of Object.entries(v || {})) s = s.replace("{" + a + "}", b); return s; };
globalThis.dzIcone = (c) => "<svg></svg>";
globalThis.HTMLCanvasElement = function(){}; HTMLCanvasElement.prototype.captureStream = function(){};
globalThis.MediaRecorder = function(){}; MediaRecorder.isTypeSupported = () => true;
const appels = {gum: 0, fetch: 0, arrets: 0, handle: null};
globalThis.fetch = async () => { appels.fetch++; return {ok: false, json: async () => ({})}; };
globalThis.CustomEvent = function(t, o){ this.type = t; this.detail = o && o.detail; };
globalThis.dispatchEvent = () => true; globalThis.addEventListener = () => {}; globalThis.removeEventListener = () => {};
let SURFACE = null;
function piste(surface, handle){ return { getSettings: () => ({displaySurface: surface, width: 1280, height: 720}),
  getCaptureHandle: () => (handle === undefined ? null : {handle: handle === "MOI" ? appels.handle : handle}),
  stop(){ appels.arrets++; }, addEventListener(){} }; }
Object.defineProperty(globalThis, "navigator", {value: {mediaDevices: %s}, configurable: true});
"""

MD_OK = r"""{
  setCaptureHandleConfig(c){ appels.handle = c.handle; },
  async getDisplayMedia(o){ appels.gdm = o; if (!SURFACE) throw new Error("refus"); const p = piste(SURFACE[0], SURFACE[1]);
    return { getVideoTracks: () => [p], getAudioTracks: () => [], getTracks: () => [p] }; },
  async getUserMedia(){ appels.gum++; throw new Error("jamais"); } }"""


def harnais(lang, md, corps):
    return (FAUX % (json.dumps(DICO), lang, md)) + "\nawait import(%s);\n" % json.dumps(URL("dz-capture.js")) + corps


U = node(harnais("fr", MD_OK, r"""
const out = {}, C = window.__dzCapture;
const b = document.querySelector("[data-dz-capture-ouvrir]");
out.place = b && b.parent === header && header.enfants.indexOf(b) === header.enfants.indexOf(agent) - 1;
out.libelle = b && b.textContent; out.grise = b && b.disabled; out.titre = b && b.title;
C.ouvrir();
const boite = document.querySelector("[data-dz-capture-boite]");
const opt = (n) => boite.querySelector('[data-dz-capture-option="' + n + '"]');
out.boite = !!boite; out.camera = opt("camera").checked; out.voix = opt("voix").checked; out.app = opt("mode-app").checked;
out.textes = boite.textContent;
document.querySelector("[data-dz-capture-boite]").remove();
SURFACE = null; out.r1 = await C.demarrer({camera: true, voix: true});
out.a1 = {gum: appels.gum, fetch: appels.fetch, gdm: appels.gdm && appels.gdm.preferCurrentTab};
SURFACE = ["monitor"]; out.r2 = await C.demarrer({camera: true, voix: true});
out.a2 = {gum: appels.gum, fetch: appels.fetch, arrets: appels.arrets};
SURFACE = ["browser", "autre"]; out.r3 = await C.demarrer({camera: true, voix: true});
out.a3 = {gum: appels.gum, fetch: appels.fetch, arrets: appels.arrets};
SURFACE = ["browser", null]; out.r4 = await C.demarrer({camera: true, voix: true});   // onglet tiers SANS poignée
out.a4 = {gum: appels.gum, fetch: appels.fetch, arrets: appels.arrets};
out.session = C.session();
console.log(JSON.stringify(out));
"""))
check("U1 bouton « Enregistrer » dans la barre du haut, juste avant « Demander »", U["place"] and U["libelle"] == DICO["capture.barre.bouton"]["fr"], U)
check("U2 disponible (getDisplayMedia, MediaRecorder, captureStream) : actif, survol explicite",
      U["grise"] is False and U["titre"] == DICO["capture.barre.titre"]["fr"])
check("U3 boîte de départ : caméra JAMAIS cochée d'office (même gardée cochée), voix cochée, « l'app seule »",
      U["boite"] and U["camera"] is False and U["voix"] is True and U["app"] is True, U)
check("U4 note Element Capture absent dite dans la boîte", DICO["capture.cadre.sans_ec"]["fr"] in U["textes"])
check("U5 partage refusé : message, ni micro ni caméra, aucune session ; preferCurrentTab demandé",
      U["r1"] == {"ok": False, "message": DICO["capture.erreur.refus"]["fr"]} and U["a1"] == {"gum": 0, "fetch": 0, "gdm": True}, U["r1"])
check("U6 écran entier : refus, piste coupée, ni micro ni caméra, aucune session",
      U["r2"]["message"] == DICO["capture.erreur.surface"]["fr"] and U["a2"] == {"gum": 0, "fetch": 0, "arrets": 1}, U["a2"])
check("U7 autre onglet (Capture Handle) : refus, piste coupée, ni micro ni caméra",
      U["r3"]["message"] == DICO["capture.erreur.autre_onglet"]["fr"] and U["a3"] == {"gum": 0, "fetch": 0, "arrets": 2}, U["a3"])
check("U8 aucune session ouverte après les refus", U["session"] is None)
check("U7b revue finale C1 : un onglet tiers SANS poignée (la page en a posé une) est refusé comme autre onglet",
      U["r4"]["message"] == DICO["capture.erreur.autre_onglet"]["fr"] and U["a4"] == {"gum": 0, "fetch": 0, "arrets": 3}, U)

# ── revue finale t315 : C1 (navigateur sans Capture Handle ni Element Capture), C2 (panne après la session), I4 ──
MD_SANS = r"""{
  async getDisplayMedia(o){ const p = piste("browser"); delete p.getCaptureHandle;
    return { getVideoTracks: () => [p], getAudioTracks: () => [], getTracks: () => [p] }; },
  async getUserMedia(){ appels.gum++; return { getTracks: () => [{ stop(){ appels.arrets++; } }], getVideoTracks: () => [], getAudioTracks: () => [] }; } }"""
U3 = node(harnais("fr", MD_SANS, r"""
const r = await window.__dzCapture.demarrer({mode: "onglet", camera: true, voix: true});
console.log(JSON.stringify({r, gum: appels.gum, fetch: appels.fetch, arrets: appels.arrets, s: window.__dzCapture.session()}));
"""))
check("U10 C1 : onglet invérifiable (ni Capture Handle ni Element Capture) -> refus, piste coupée, ni micro ni caméra",
      U3["r"]["message"] == DICO["capture.erreur.verif"]["fr"] and U3["gum"] == 0 and U3["fetch"] == 0 and U3["arrets"] == 1
      and U3["s"] is None, U3)
MD_PANNE = r"""{
  setCaptureHandleConfig(c){ appels.handle = c.handle; },
  async getDisplayMedia(o){ const p = piste("browser", "MOI"); p.readyState = "live";
    return { getVideoTracks: () => [p], getAudioTracks: () => [], getTracks: () => [p] }; },
  async getUserMedia(o){ appels.gum++; return { getTracks: () => [{ stop(){ appels.arrets++; } }], getVideoTracks: () => [], getAudioTracks: () => [] }; } }"""
U4 = node(harnais("fr", MD_PANNE, r"""
// une session s'ouvre, puis l'enregistreur tombe en panne (MediaRecorder lève) : tout doit être coupé et abandonné
const req = [];
globalThis.fetch = async (u, o) => { req.push([(o && o.method) || "GET", u]); appels.fetch++;
  return {ok: true, json: async () => (u === "/api/capture/sessions" ? {id: "0123456789abcdef"} : {})}; };
globalThis.MediaStream = function(l){ this.l = l || []; this.getTracks = () => this.l; this.getVideoTracks = () => this.l; this.getAudioTracks = () => []; };
const Ctx = () => new Proxy({}, {get: (t, k) => (k in t ? t[k] : () => {}), set: (t, k, v) => { t[k] = v; return true; }});
const creer = document.createElement;
document.createElement = (t) => { const n = creer(t); if (t === "canvas") { n.getContext = Ctx; n.captureStream = () => new MediaStream([]); }
  if (t === "video") n.play = () => Promise.resolve(); return n; };
globalThis.MediaRecorder = function(){ throw new Error("enregistreur en panne"); }; MediaRecorder.isTypeSupported = () => true;
globalThis.setInterval = () => 1; globalThis.clearInterval = () => {};
const C = window.__dzCapture;
const [r1, r2] = await Promise.all([C.demarrer({camera: true, voix: true}), C.demarrer({camera: true, voix: true})]);
console.log(JSON.stringify({r1, r2, gum: appels.gum, arrets: appels.arrets, req, s: C.session(),
  attr: document.documentElement.getAttribute("data-dz-capture"), pastille: !!document.querySelector("[data-dz-capture-pastille]"),
  encart: !!document.querySelector("[data-dz-capture-encart]"), bouton: document.querySelector("[data-dz-capture-ouvrir]").textContent}));
"""))
check("U11 I4 : un second démarrer concurrent est refusé d'emblée (aucun second partage demandé)",
      U4["r2"] == {"ok": False, "message": ""} and U4["gum"] == 2, U4)
check("U12 C2 : panne après l'ouverture de la session -> message, session serveur abandonnée (DELETE)",
      U4["r1"]["ok"] is False and DICO["capture.erreur.session"]["fr"].split("{")[0] in U4["r1"]["message"]
      and ["DELETE", "/api/capture/sessions/0123456789abcdef"] in U4["req"], U4)
check("U13 C2 : écran, micro et caméra coupés, ni pastille ni encart ni masque, enregistreur libre",
      U4["arrets"] == 3 and U4["s"] is None and U4["attr"] is None and not U4["pastille"] and not U4["encart"]
      and U4["bouton"] == DICO["capture.barre.bouton"]["fr"], U4)

U2 = node(harnais("en", "{}", r"""
const b = document.querySelector("[data-dz-capture-ouvrir]");
console.log(JSON.stringify({libelle: b.textContent, grise: b.disabled, titre: b.title}));
"""))
check("U9 anglais ; sans getDisplayMedia : grisé, la raison au survol",
      U2 == {"libelle": DICO["capture.barre.bouton"]["en"], "grise": True, "titre": DICO["capture.barre.indisponible"]["en"]}, U2)

# ── [P] livraison ──
print("[P] livraison")
check("P1 copies shared == dist (trois modules)", all((DI / f).is_file() and (DI / f).read_bytes() == (SH / f).read_bytes() for f in FICHIERS))
idx = (REPO / "frontend" / "dist" / "index.html").read_text("utf-8")
balise = '<script type="module" src="/shared/dz-capture.js"></script>'
check("P2 index.html charge dz-capture.js une fois, en module, après dz-whatsapp-espace.js",
      idx.count("dz-capture") == 1 and idx.count(balise) == 1 and idx.index(balise) > idx.index("/shared/dz-whatsapp-espace.js"))
sans_comm = lambda s: re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", s, flags=re.S))   # noqa: E731
code = sans_comm(TXT)
check("P3 une seule écoute clavier : le piège Tab/Échap des boîtes (jamais la piste)",
      len(re.findall(r'addEventListener\("key', code)) == 1 and 'b.addEventListener("keydown"' in code
      and not re.search(r'addEventListener\("(input|keyup|keypress|beforeinput|change)"', code))
check("P4 la piste des clics ne lit jamais une valeur : aucun `.value` dans la logique ni dans surAppui",
      ".value" not in sans_comm(LOG) and ".value" not in code[code.index("function surAppui"):code.index("const ecouteurs")])
check("P5 ni alert/confirm/prompt natifs", not any(re.search(r"(?<![\w.$])(?:window\.)?(?:confirm|alert|prompt)\(", sans_comm(x))
                                                   for x in (TXT, LOG, SCN)))
check("P6 aucun emoji", not any(re.search("[\U0001F300-\U0001FAFF☀-➿]", x) for x in (TXT, LOG, SCN)))
check("P7 aucun arrondi de châssis (boîtes, boutons) : seul le point rouge REC est rond",
      re.search(r'boite: "[^"]*border-radius:0', TXT) and re.search(r'bouton: "[^"]*border-radius:0', TXT)
      and re.findall(r"border-radius:[1-9][^;\"]*", TXT) == ["border-radius:50%"])
cles = set(re.findall(r'"(capture\.[a-z_]+\.[a-z_]+)"', TXT))
prefixes = {"capture.cadre.": ["app", "onglet"], "capture.forme.": ["cercle", "carre", "vif"]}
emploi = cles | {p + x for p, l in prefixes.items() for x in l}
check("P8 toutes les clés employées existent", not (emploi - set(DICO)), emploi - set(DICO))
check("P9 toutes les clés du fichier sont employées", not (set(DICO) - emploi), set(DICO) - emploi)
var = lambda s: sorted(re.findall(r"\{(\w+)\}", s))                  # noqa: E731
check("P10 FR/EN non vides, mêmes variables, clés à 3 segments",
      all(v["fr"].strip() and v["en"].strip() and var(v["fr"]) == var(v["en"]) and re.fullmatch(r"[a-z0-9]+(\.[a-z0-9_]+){2,}", k)
          for k, v in DICO.items()))
dico_js = (SH / "dz-i18n-dico.js").read_text("utf-8")
check("P11 dictionnaire assemblé (shared == dist) avec les clés capture.*",
      all(json.dumps(k) in dico_js for k in DICO) and (DI / "dz-i18n-dico.js").read_bytes() == (SH / "dz-i18n-dico.js").read_bytes())

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
