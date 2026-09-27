# -*- coding: utf-8 -*-
"""STUDIO 27/09/2026 — GROUPE R8 DU MAILLON montage.

Retours utilisateur (captures du Studio, rendu 427b1a6d) :
  - l'avatar HeyGen decale dans le News Reel : le template impose le format de
    la generation (autorite : pipeline._heygen_aspect_for_slot, banc
    test_template_avatar_format) ; le Studio l'AFFICHE dans l'inspecteur du
    noeud HeyGen (R8st1 dzHgAspect/dzHgTarget/DzHgFormat, R8hg1) ;
  - « Open graph… » sur deux lignes, chevron decale -> bouton icone folderOpen
    qui deroule la liste (R8og1, R8ic1) ;
  - les trois points decoratifs de l'inspecteur -> repli du panneau de droite
    (R8st1 dziSt/dziOpen/__dzInsp + CSS, R8in1..R8in4, R8ic1 panelR).
Le recensement du 27/09 (bundle + vectorlab, spritelab, tilelab, cardforge,
materialforge, atelier, etabli, montage) n'a trouve AUCUN autre bouton trois
points DECORATIF dans un en-tete de panneau : celui de la bibliotheque de
templates ouvre un vrai menu (Duplicate/Delete) et reste — controle [4].

METHODE : bundle livre contre .bak_montage (temoin : l'etat d'avant le
maillon) ; les fonctions pures extraites du bundle sont EXECUTEES sous node
(regle de format croisee avec la regle Python sur les memes vecteurs ; dziOpen
contre un faux document/localStorage). Regle des assertions negatives : chaque
« absent » a son temoin positif dans le .bak. Faute n6 : details par _d().
Run : & $PY tests/test_studio_r8.py   (depuis backend/)
"""
import json, os, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzr8_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ.setdefault("FAL_KEY", "test-key")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT / "scripts"))
from loguru import logger                                  # noqa: E402
logger.remove()
from app.services import pipeline as PL                    # noqa: E402
import patch_bundle_montage as P                           # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def _d(*a):
    try:
        return json.dumps(a, ensure_ascii=False, default=str)[:400]
    except Exception as e:                                   # pragma: no cover
        return f"(detail illisible : {e})"


BUNDLE = ROOT / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BAK = BUNDLE.with_name(BUNDLE.name + ".bak_montage")
s = BUNDLE.read_bytes().decode("utf-8")
bak = BAK.read_bytes().decode("utf-8") if BAK.is_file() else ""
crlf = "\r\n" in s
nl = lambda t: P.nl(t, crlf)
NODE = shutil.which("node")
R8 = list(getattr(P, "R8", []))

print("\n[0] preconditions")
check("0.1 .bak_montage present (temoin)", bool(bak), _d(str(BAK)))
check("0.2 node present", bool(NODE), _d(NODE))
check("0.3 groupe R8 : seize sections, en QUEUE de PATCHES", len(R8) == 16 and P.PATCHES[-16:] == R8,
      _d([t[0] for t in P.PATCHES[-9:]]))

print("\n[1] chaque section : ancre x1 dans le .bak, remplacement x1 dans le livre")
for tag, a, r in R8:
    check(f"1 {tag} : ancre x1 (.bak), remplacement x1 (livre), ancre {'gardee' if a in r else 'consommee'}",
          bak.count(nl(a)) == 1 and s.count(nl(r)) == 1 and s.count(nl(a)) == (1 if a in r else 0),
          _d(bak.count(nl(a)), s.count(nl(r)), s.count(nl(a))))

print("\n[2] format HeyGen : la regle du Studio = la regle du rendu (node contre Python)")
_i = s.find("function dzHgAspect(w,h){"); _j = s.find("function dzHgTarget(", _i)
_fa = s[_i:_j] if _i >= 0 and _j > _i else ""
_i2 = _j; _j2 = s.find("var __dzHgTpl={};", _i2)
_ft = s[_i2:_j2] if _i2 >= 0 and _j2 > _i2 else ""
VEC = [(1080, 680), (1080, 1920), (1080, 1080), (1920, 1080), (1080, 1350), (540, 960), (1080, 1300),
       (1080, 1500), (1080, 608), (1000, 1000), (1360, 1000), (760, 1000), (0, 680), (1080, 0), ("x", 680), (-5, 10)]


def py_rule(w, h):
    return PL._heygen_aspect_for_slot({"regions": [{"type": "video_slot", "slot_name": "a", "width": w,
                                                    "height": h}]}, "a")


_js = _fa + _ft + """
var V=%s,out=V.map(function(v){return dzHgAspect(v[0],v[1])});
var G={nodes:[{id:"h",type:"HeyGenAvatar"},{id:"m",type:"AvatarMaster"},{id:"s",type:"SpatialCompose",props:{templateId:"tpl_news_reel"}},{id:"r",type:"Render"},{id:"h2",type:"HeyGenAvatar"}],
edges:[{from:"h",to:"m",toPort:"in"},{from:"m",to:"s",toPort:"avatar"},{from:"s",to:"r",toPort:"in"},{from:"h2",to:"r",toPort:"in"}]};
var G2={nodes:[{id:"h",type:"HeyGenAvatar"},{id:"s",type:"SpatialCompose",props:{}}],edges:[{from:"h",to:"s",toPort:"s3"}]};
var t1=dzHgTarget(G,"h"),t2=dzHgTarget(G,"h2"),t3=dzHgTarget(G2,"h"),t4=dzHgTarget({nodes:[],edges:[]},"h");
console.log(JSON.stringify({out:out,t1:t1&&{sc:t1.sc.id,port:t1.port},t2:t2,t3:t3&&{sc:t3.sc.id,port:t3.port},t4:t4}));
""" % json.dumps([[w, h] for w, h in VEC])
_res = {}
if NODE and _fa and _ft:
    _p = pathlib.Path(TMP) / "r8.js"
    _p.write_text(_js, encoding="utf-8")
    _r = subprocess.run([NODE, str(_p)], capture_output=True, text=True, encoding="utf-8")
    try:
        _res = json.loads(_r.stdout.strip().splitlines()[-1])
    except Exception:
        _res = {"err": (_r.stderr or _r.stdout)[-300:]}
_py = [py_rule(w, h) for w, h in VEC]
check("2.1 dzHgAspect (bundle, node) = _heygen_aspect_for_slot (Python) sur 16 vecteurs, dont 4 illisibles et 2 entre seuils log/lineaire",
      _res.get("out") == _py and _py[:4] == ["16:9", "9:16", "1:1", "16:9"] and _py[10:12] == ["16:9", "1:1"] and _py[-4:] == [None] * 4,
      _d(_res.get("out"), _py, _res.get("err")))
check("2.2 dzHgTarget : HeyGen -> Avatar master -> Spatial compose (port avatar) trouve",
      _res.get("t1") == {"sc": "s", "port": "avatar"}, _d(_res.get("t1")))
check("2.3 ... HeyGen branche sur Render seul -> null (temoin : 2.2 trouve), graphe vide -> null",
      _res.get("t1") is not None and _res.get("t2") is None and _res.get("t4") is None, _d(_res))
check("2.4 ... branche directe sur un autre port (s3) -> ce port", _res.get("t3") == {"sc": "s", "port": "s3"},
      _d(_res.get("t3")))
check("2.5 inspecteur HeyGen : DzAvatarPick PUIS DzHgFormat (graphe + noeud), une fois",
      s.count('r.jsx(DzAvatarPick,{p:n,set:o}),r.jsx(DzHgFormat,{graph:g,node:e})') == 1
      and bak.count('e.type==="HeyGenAvatar"?r.jsx(DzAvatarPick,{p:n,set:o})') == 1, "")
check("2.6 DzHgFormat lit le template par /api/layout-templates/<id> et le port par dzSpatialSlots",
      s.count('fetch("/api/layout-templates/"+encodeURIComponent(tid))') == 1
      and s.count("var sp=dzSpatialSlots(tpl,hit.sc.props||{})") == 1 and "Génération HeyGen" in s, "")

print("\n[3] « Ouvrir un graphe » : bouton icone, liste maison")
check("3.1 plus de « Open graph… » (temoin : x1 dans le .bak)", s.count("Open graph…") == 0
      and bak.count("Open graph…") == 1, _d(s.count("Open graph…"), bak.count("Open graph…")))
check("3.2 bouton K outline/sm, icone folderOpen, aria menu, liste /api/studio-graphs rafraichie",
      s.count('r.jsx(K,{variant:"outline",size:"sm",icon:"folderOpen"') == 1
      and s.count('"aria-haspopup":"menu","aria-expanded":open') == 1
      and s.count('window.addEventListener("dz-graphs-changed",load)') == 1
      and s.count('className:"dz-opengraph-item"') == 1, "")
check("3.3 fermeture : clic dehors (mousedown) et Echap, ecouteurs retires",
      s.count('document.addEventListener("mousedown",out);document.addEventListener("keydown",esc)') == 1
      and s.count('document.removeEventListener("mousedown",out);document.removeEventListener("keydown",esc)') == 1, "")
check("3.4 appelant inchange : r.jsx(DzOpenGraph,{onPick: x1 (livre et .bak)",
      s.count("r.jsx(DzOpenGraph,{onPick:") == 1 and bak.count("r.jsx(DzOpenGraph,{onPick:") == 1, "")
check("3.5 icones : folderOpen et panelR x1 dans la table, AVANT more ; l'ancien `folder` (calques) garde",
      s.count("folderOpen:r.jsx(") == 1 and s.count("panelR:r.jsxs(") == 1
      and s.find("panelR:r.jsxs(") < s.find('more:r.jsxs("g"') and s.count("folder:r.jsxs(") == 1
      and bak.count("folderOpen") == 0 and bak.count("panelR") == 0, "")

print("\n[4] trois points -> repli de l'inspecteur")
check("4.1 en-tete du noeud : plus de trois points decoratifs (temoin : x1 dans le .bak)",
      s.count(nl('r.jsx(se,{name:"more"})]})})}function Fh(')) == 0
      and bak.count('r.jsx(se,{name:"more"})]})})}function Fh(') == 1, "")
check("4.2 ... remplaces par « Replier l'inspecteur » (panelR, dziOpen(!1)) dans Oh ET dans Fh",
      s.count('title:"Replier l\'inspecteur","aria-label":"Replier l\'inspecteur",className:"dz-insp-fold",'
              'onClick:function(){dziOpen(!1)}') == 2, "")
check("4.3 le menu trois points FONCTIONNEL de la bibliotheque de templates reste (name:\"more\",size:24)",
      s.count('r.jsx(se,{name:"more",size:24') == 1 and bak.count('r.jsx(se,{name:"more",size:24') == 1, "")
check("4.4 grille : dz-insp-hidden calculee au rendu depuis dziSt, a cote de dz-dock-hidden",
      s.count('+(dzdSt.open?"":" dz-dock-hidden")+(dziSt.open?"":" dz-insp-hidden")') == 1, "")
check("4.5 poignee INSPECTOR (panelR, dziOpen(!0)) AVANT la poignee NODES, x1",
      s.count('className:"dz-insp-handle"') == 1 and 0 < s.find('className:"dz-insp-handle"') < s.find('className:"dz-dock-handle"'), "")
check("4.6 CSS injectee x1 (id dz-studio-r8) : colonnes 260/1fr/0 et 0/1fr/0, poignee masquee panneau ouvert",
      s.count('st.id="dz-studio-r8"') == 1 and ".dz-studio-grid.dz-insp-hidden{grid-template-columns:260px 1fr 0px!important}" in s
      and ".dz-studio-grid.dz-dock-hidden.dz-insp-hidden{grid-template-columns:0px 1fr 0px!important}" in s
      and ".dz-studio-grid:not(.dz-insp-hidden) .dz-insp-handle{display:none}" in s, "")
_css = (ROOT / "frontend" / "dist" / "shared" / "montage.css").read_text(encoding="utf-8")
check("4.7 montage.css intacte (aucune regle dz-insp / dz-opengraph ; temoin : elle porte .dzsvm)",
      ".dzsvm" in _css and "dz-insp" not in _css and "dz-opengraph" not in _css, "")
# dziOpen sous node contre un faux DOM
_k = s.find("var dziSt="); _k2 = s.find("function dzHgAspect(", _k)
_st = s[_k:_k2] if _k >= 0 and _k2 > _k else ""
_js2 = """
var store={},cls={};var localStorage={getItem:function(k){return k in store?store[k]:null},setItem:function(k,v){store[k]=String(v)}};
var grid={classList:{toggle:function(c,on){if(on)cls[c]=1;else delete cls[c]}}};
var document={querySelector:function(q){return q===".dz-studio-grid"?grid:null}};var window={};
%s
var r={};r.init=dziSt.open;dziOpen(!1);r.ferme={open:dziSt.open,ls:store.dz_studio_insp,cls:!!cls["dz-insp-hidden"],state:window.__dzInsp.state};
window.__dzInsp.toggle();r.bascule={open:dziSt.open,ls:store.dz_studio_insp,cls:!!cls["dz-insp-hidden"]};
window.__dzInsp.close();window.__dzInsp.open();r.rouvre={open:dziSt.open,cls:!!cls["dz-insp-hidden"]};
console.log(JSON.stringify(r));
""" % _st
_r2 = {}
if NODE and _st:
    _p2 = pathlib.Path(TMP) / "r8b.js"
    _p2.write_text(_js2, encoding="utf-8")
    _o2 = subprocess.run([NODE, str(_p2)], capture_output=True, text=True, encoding="utf-8")
    try:
        _r2 = json.loads(_o2.stdout.strip().splitlines()[-1])
    except Exception:
        _r2 = {"err": (_o2.stderr or _o2.stdout)[-300:]}
check("4.8 node : ouvert par defaut ; dziOpen(false) -> classe posee, \"0\" memorise, __dzInsp.state false",
      _r2.get("init") is True and _r2.get("ferme") == {"open": False, "ls": "0", "cls": True, "state": False}, _d(_r2))
check("4.9 node : toggle rouvre (\"1\", classe retiree) ; close puis open -> ouvert",
      _r2.get("bascule") == {"open": True, "ls": "1", "cls": False} and _r2.get("rouvre") == {"open": True, "cls": False},
      _d(_r2))

print("\n[5] Save : le nom du graphe par le dialogue maison, plus par prompt()")
check("5.1 plus de window.prompt(\"Name this graph\" (temoin : x1 dans le .bak)",
      s.count('window.prompt("Name this graph:"') == 0 and bak.count('window.prompt("Name this graph:"') == 1, "")
check("5.2 await window.__dzDialogue.saisir, titre, valeur = nom courant, bouton Enregistrer ; annuler (null) sort",
      s.count('var nm=await window.__dzDialogue.saisir("Nom du graphe :",{titre:"Enregistrer le graphe",'
              'valeur:(o.name||"My graph"),ok:"Enregistrer"});if(nm==null)return;') == 1, "")
check("5.3 ... dans le onClick ASYNC du bouton Save (« Save this graph »)",
      s.count('title:"Save this graph",onClick:async()=>{try{var nm=await window.__dzDialogue.saisir(') == 1, "")
check("5.4 la couche de dialogue est dans le bundle (saisir defini) -- temoin : deja au .bak",
      'saisir: function (m, o) { return ouvrir("saisir", m, o); }' in s
      and 'saisir: function (m, o) { return ouvrir("saisir", m, o); }' in bak, "")

print("\n[6] les dix autres window.prompt( natifs -> dialogue maison")
check("6.1 plus AUCUN window.prompt( dans le bundle (temoin : 9 dans le .bak, + 2 poses par ce maillon avant le 27/09)",
      s.count("window.prompt(") == 0 and bak.count("window.prompt(") == 9, _d(s.count("window.prompt("), bak.count("window.prompt(")))
_SITES = [  # (fonction devenue async + await saisir, texte du dialogue)
    ('async function saveFav(kind){if(!cur)return;var name=await window.__dzDialogue.saisir(', "Nom de ce favori"),
    ('addEventListener("click",async function(){var lien=await window.__dzDialogue.saisir(', "Lien du calque Figma"),
    ('async function __dzPrint3d(sh){try{var rep=await window.__dzDialogue.saisir(', "Taille cible en mm"),
    ('r.jsx("button",{onClick:async function(){var nn=await window.__dzDialogue.saisir("Renommer ce rendu 3D :"', "Renommer ce rendu 3D"),
    ('onClick:async()=>{var nn=await window.__dzDialogue.saisir("Renommer l\'image :"', "Renommer l'image"),
    ('onClick:async()=>{var nn=await window.__dzDialogue.saisir("Renommer l\'asset :"', "Renommer l'asset"),
    ('async function dzSavePreset(){var lbl=await window.__dzDialogue.saisir(', "Nom du preset maison"),
    ('run:async function(){var lg=await window.__dzDialogue.saisir(', "Langue de la nouvelle piste"),
]
for _k, (_pose, _txt) in enumerate(_SITES):
    check(f"6.{_k + 2} « {_txt} » : fonction async + await saisir, x1", s.count(nl(_pose)) == 1, _d(s.count(nl(_pose))))
check("6.10 copie du chemin d'illustration : deux saisir(...).then(done) (presse-papiers refuse ET absent)",
      s.count('window.__dzDialogue.saisir("Copie ce chemin d\'illustration :",{titre:"Copier le chemin",valeur:v,ok:"Fermer"}).then(done)') == 2
      and bak.count('window.prompt("Copie ce chemin d\'illustration :",v);done()') == 2, "")
_nc = subprocess.run([NODE, "--check", str(BUNDLE)], capture_output=True, text=True) if NODE else None
check("6.12 le bundle ENTIER passe node --check (un await hors fonction async y serait une SyntaxError)",
      _nc is not None and _nc.returncode == 0, _d(_nc.stderr[-300:] if _nc else "node absent"))
check("6.11 appelants inchanges : saveFav x3 boutons, __dzPrint3d(m.short) x1 (valeur de retour jamais lue)",
      s.count('onClick:function(){saveFav("') == 3 and s.count("__dzPrint3d(m.short)}") == 1, "")

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
