# -*- coding: utf-8 -*-
"""P1 #3 (28/09/2026) — HUIT CONTROLES INERTES (onChange vide).

Releve dans le .bak_montage (temoin) : `onChange:()=>{}` x8 sur des controles
visibles —
  Studio, panneau « Graph » (Fh) : Format, FPS, Render name (fige render.mp4),
    « Avatar node is duration master », Tail pad, Loudness target ;
  Quick (um) : « Voice (HeyGen comp) » ;
  Templates (fm) : « Search… ».
Mesures qui fondent les decisions (groupe P1 du maillon montage) :
  - le compilateur du Studio (Mh) lit Render.format et Render.name, PAS
    Render.fps (canevas fige a 30) -> Format et Render name BRANCHES sur le
    noeud Render (onUpdateNode), FPS RETIRE ;
  - duree maitre, tail pad et loudness vivent dans les noeuds AvatarMaster,
    SpatialCompose, Upload et Loudness -> la section devient un RESUME en
    lecture seule tire du graphe (dzGraphResume), « Providers » aussi (il
    affichait toujours « fal.ai · HeyGen · ElevenLabs ») ;
  - Quick pose voiceover_enabled:!1 dans les deux requetes : le toggle ne
    pilotait rien, le brancher lancerait une voix off payante -> RETIRE ;
  - Templates : le champ filtre vraiment (dzTplFiltre, nom/id/tags, sans
    casse ni accents), la selection reste lue dans la liste complete.
INVARIANT EXECUTE : Fh est rendu sous node avec des composants-temoins ;
chaque onChange de l'arbre est appele et DOIT produire un effet (onUpdateNode
ou onRename). Temoin : le Fh du .bak, rendu de la meme facon, a SIX onChange
sans effet. Faute n6 : details par _d().
Run : & $PY tests/test_p1_controles_inertes.py   (depuis backend/)
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(ROOT / "scripts"))
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
NODE = shutil.which("node")
INERTE = "onChange:()=>{}"


def _node(js):
    """Execute un script node ; renvoie (code, stdout json ou None, stderr)."""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(js)
    try:
        r = subprocess.run([NODE, f.name], capture_output=True, text=True, encoding="utf-8")
    finally:
        os.unlink(f.name)
    try:
        return r.returncode, json.loads(r.stdout), r.stderr
    except Exception:
        return r.returncode, None, r.stderr + r.stdout[:300]


def _entre(txt, debut, fin):
    i = txt.find(debut)
    j = txt.find(fin, i)
    return txt[i:j] if i >= 0 and j > i else ""


print("\n[0] preconditions et temoins (.bak_montage)")
check("0.1 .bak_montage present, node present", bool(bak) and bool(NODE), _d(str(BAK), NODE))
check("0.2 temoin : HUIT onChange:()=>{} dans le .bak", bak.count(INERTE) == 8, _d(bak.count(INERTE)))
for _t in ('label:"Voice (HeyGen comp)"', 'value:"render.mp4",onChange:()=>{}', 'label:"FPS",children:r.jsx(re,{value:30,onChange:()=>{}',
           'label:"Avatar node is duration master"', 'children:"fal.ai · HeyGen · ElevenLabs"',
           'placeholder:"Search…",style:{width:220},value:"",onChange:()=>{}'):
    check(f"0.3 temoin x1 dans le .bak : {_t[:48]}", bak.count(_t) == 1, _d(bak.count(_t)))

print("\n[1] bundle : plus aucun controle inerte")
check("1.1 onChange:()=>{} : 0 dans le bundle", s.count(INERTE) == 0, _d(s.count(INERTE)))
for _t in ('label:"Voice (HeyGen comp)"', '"render.mp4"', 'label:"FPS",children:r.jsx(re,{value:30',
           'label:"Avatar node is duration master"', 'children:"fal.ai · HeyGen · ElevenLabs"', 'label:"Loudness target"'):
    check(f"1.2 absent du bundle : {_t[:48]}", s.count(_t) == 0, _d(s.count(_t)))
check("1.3 Quick : les deux requetes gardent voiceover_enabled:!1 (comportement inchange)",
      s.count("voiceover_enabled:!1") == bak.count("voiceover_enabled:!1") >= 2, _d(s.count("voiceover_enabled:!1")))

print("\n[2] dzGraphResume execute (resume du graphe, lecture seule)")
RES = _entre(s, "function dzGraphResume(", "function dzIsImgNode(")
check("2.1 dzGraphResume present x1, juste avant dzIsImgNode", bool(RES) and s.count("function dzGraphResume(") == 1, "")
VEC = {
    "vide": {"nodes": [], "edges": []},
    "demo": {"nodes": [
        {"id": "r1", "type": "Render", "props": {"format": "16:9", "name": "oracle"}},
        {"id": "a1", "type": "AvatarMaster", "props": {"tailPadS": 0.4}},
        {"id": "l1", "type": "Loudness", "props": {"lufs": -16}},
        {"id": "s1", "type": "Seedance", "props": {}},
        {"id": "h1", "type": "HeyGenAvatar", "props": {}},
        {"id": "v1", "type": "Voiceover", "props": {"provider": "elevenlabs"}},
        {"id": "n1", "type": "NewsScript", "props": {}}], "edges": []},
    "spatial": {"nodes": [{"id": "c1", "type": "SpatialCompose", "props": {"useAsMaster": True, "tailPadS": 0.6}}], "edges": []},
    "ugc": {"nodes": [{"id": "u1", "type": "Upload", "props": {"jobId": "j", "durationS": 12, "master": True}}], "edges": []},
    "local": {"nodes": [{"id": "x1", "type": "Upscale", "props": {"mode": "simple"}},
                        {"id": "x2", "type": "RemoveBG", "props": {"method": "local"}},
                        {"id": "x3", "type": "NewsIllustration", "props": {}}], "edges": []},
    "defauts": {"nodes": [{"id": "x1", "type": "Upscale", "props": {}}, {"id": "v1", "type": "Voiceover", "props": {"provider": "voicebox"}}], "edges": []},
}
rc, out, err = _node(RES + "\nvar V=" + json.dumps(VEC) + ";var o={};for(var k in V){var q=dzGraphResume(V[k]);"
                     "o[k]={rn:q.rn?q.rn.id:null,maitre:q.maitre,loud:q.loud,prov:q.prov}}process.stdout.write(JSON.stringify(o))")
check("2.2 s'execute", rc == 0 and out is not None, _d(err[-300:]))
out = out or {}
check("2.3 graphe vide : rien d'invente (tirets partout)",
      out.get("vide") == {"rn": None, "maitre": "—", "loud": "—", "prov": "—"}, _d(out.get("vide")))
check("2.4 demo : Render trouve, maitre Avatar master tail 0.4 s, -16 LUFS, services dans l'ordre des noeuds",
      out.get("demo") == {"rn": "r1", "maitre": "Avatar master · tail 0.4 s", "loud": "-16 LUFS",
                          "prov": "fal.ai · HeyGen · ElevenLabs · LLM"}, _d(out.get("demo")))
check("2.5 Spatial compose maitre", (out.get("spatial") or {}).get("maitre") == "Spatial compose · slot avatar · tail 0.6 s", _d(out.get("spatial")))
check("2.6 UGC maitre", (out.get("ugc") or {}).get("maitre") == "UGC · 12 s", _d(out.get("ugc")))
check("2.7 Upscale simple, RemoveBG local, NewsIllustration (fetch gratuit) : aucun service", (out.get("local") or {}).get("prov") == "—", _d(out.get("local")))
check("2.8 defauts : Upscale sans mode = IA fal ; Voiceover voicebox = Voicebox", (out.get("defauts") or {}).get("prov") == "fal.ai · Voicebox", _d(out.get("defauts")))

print("\n[3] INVARIANT execute : tout onChange du panneau Graph a un effet")
HARNAIS = r"""
var calls=[];var r={Fragment:"F",jsx:function(t,p){return{t:t,p:p||{}}},jsxs:function(t,p){return{t:t,p:p||{}}}};
function ie(p){return null}function O(p){return null}function re(p){return null}function le(p){return null}
function se(p){return null}function Ze(p){return null}function Oe(p){return null}function dziOpen(){}
function walk(n,acc){if(!n||typeof n!=="object")return acc;if(Array.isArray(n)){n.forEach(function(c){walk(c,acc)});return acc}
 if(n.p){if(typeof n.p.onChange==="function")acc.push(n);walk(n.p.children,acc)}return acc}
function txt(n){if(n==null)return"";if(typeof n==="string"||typeof n==="number")return String(n);if(Array.isArray(n))return n.map(txt).join(" ");
 return n.p?txt(n.p.children):""}
function essai(g){calls=[];var tree=Fh({graph:g,onRename:function(v){calls.push(["rename",v])},onUpdateNode:function(id,pp){calls.push(["node",id,pp])}});
 var ctl=walk(tree,[]),inertes=[],effets=[];ctl.forEach(function(c){var n0=calls.length;var v=(c.p.options&&c.p.options.length)?(typeof c.p.options[1]==="object"?c.p.options[1].value:c.p.options[1]):"x-banc";
  c.p.onChange(v);if(calls.length===n0)inertes.push(c.p.label||c.p.placeholder||c.t.name||"?");else effets.push(calls[calls.length-1])});
 return{n:ctl.length,inertes:inertes,effets:effets,texte:txt(tree)}}
"""
G = {"name": "g.graph", "nodes": [{"id": "r1", "type": "Render", "props": {"format": "9:16", "name": "oracle"}},
                                  {"id": "a1", "type": "AvatarMaster", "props": {"tailPadS": 0.4}}], "edges": []}
G0 = {"name": "g0", "nodes": [{"id": "s1", "type": "Seedance", "props": {}}], "edges": []}
FH_NEW = _entre(s, "function Fh(", "function dzIsImgNode(")   # Fh (en-tete replie dans R8in3) puis dzGraphResume
FH_OLD = _entre(bak, "function Fh(", "function dzIsImgNode(")
rc1, o1, e1 = _node(HARNAIS + FH_NEW + "\nprocess.stdout.write(JSON.stringify({g:essai(" + json.dumps(G) + "),g0:essai(" + json.dumps(G0) + ")}))")
rc0, o0, e0 = _node(HARNAIS + FH_OLD + "\nprocess.stdout.write(JSON.stringify({g:essai(" + json.dumps(G) + ")}))")
check("3.1 temoin : le Fh du .bak rendu au harnais a SIX onChange sans effet", rc0 == 0 and o0 and len(o0["g"]["inertes"]) == 6,
      _d(e0[-200:], o0 and o0["g"]["inertes"]))
check("3.2 Fh livre : 0 onChange sans effet (graphe avec Render)", rc1 == 0 and o1 and o1["g"]["n"] >= 3 and o1["g"]["inertes"] == [],
      _d(e1[-300:], o1 and o1["g"]))
_ef = (o1 or {}).get("g", {}).get("effets", [])
check("3.3 Format -> onUpdateNode(r1,{format}) ; Render name -> onUpdateNode(r1,{name}) ; Graph name -> onRename",
      ["node", "r1", {"format": "1:1"}] in _ef and ["node", "r1", {"name": "x-banc"}] in _ef and ["rename", "x-banc"] in _ef, _d(_ef))
_t1 = (o1 or {}).get("g", {}).get("texte", "")
check("3.4 le resume dit le vrai maitre du graphe et les vrais services", "Avatar master · tail 0.4 s" in _t1 and "fal.ai · HeyGen" not in _t1, _d(_t1[-300:]))
_g0 = (o1 or {}).get("g0", {})
check("3.5 sans noeud Render : seul le nom du graphe est editable, et le panneau dit d'ajouter un Render",
      _g0.get("n") == 1 and _g0.get("inertes") == [] and "Ajoute un nœud Render" in _g0.get("texte", ""), _d(_g0))
check("3.7 en-tete de Fh REPLIE dans R8in3 (son ancre est ce remplacement) : x1 livre, R8in3 intact sinon",
      s.count("function Fh({graph:e,onRename:t,onUpdateNode:U}){var dzRs=dzGraphResume(e),dzRn=dzRs.rn,") == 1
      and s.count(P.R_R8IN3) == 1 and "onUpdateNode" not in P.A_R8IN3, "")
check("3.6 l'appelant passe onUpdateNode a Fh", s.count("r.jsx(Fh,{graph:t,onRename:i,onUpdateNode:U})") == 1
      and bak.count("r.jsx(Fh,{graph:t,onRename:i})") == 1, "")

print("\n[4] Templates : la recherche filtre vraiment")
TF = _entre(s, "function dzTplFiltre(", "function fm(")
L = [{"id": "tpl_news_reel", "name": "News Reel", "tags": ["news", "1080×1920"]},
     {"id": "tpl_custom_ab", "name": "Écran partagé", "tags": ["split"]},
     {"id": "tpl_x", "name": "Oracle", "tags": []}]
rc, tf, err = _node(TF + "\nvar L=" + json.dumps(L) + ";var ids=function(a){return a.map(function(t){return t.id})};"
                    "process.stdout.write(JSON.stringify({vide:dzTplFiltre(L,'')===L,blanc:dzTplFiltre(L,'   ')===L,news:ids(dzTplFiltre(L,'NEWS')),"
                    "accent:ids(dzTplFiltre(L,'ecran')),tag:ids(dzTplFiltre(L,'split')),id:ids(dzTplFiltre(L,'custom')),rien:ids(dzTplFiltre(L,'zzz'))}))")
check("4.1 dzTplFiltre s'execute", rc == 0 and tf is not None, _d(err[-300:]))
tf = tf or {}
check("4.2 requete vide ou blanche : la liste d'origine (meme objet)", tf.get("vide") is True and tf.get("blanc") is True, _d(tf))
check("4.3 nom sans casse, sans accents, par tag et par id", tf.get("news") == ["tpl_news_reel"] and tf.get("accent") == ["tpl_custom_ab"]
      and tf.get("tag") == ["tpl_custom_ab"] and tf.get("id") == ["tpl_custom_ab"] and tf.get("rien") == [], _d(tf))
_ifm = s.find("function fm({variant:e}){")
FM = s[_ifm:_ifm + 60000] if _ifm >= 0 else ""
check("4.4 fm : etat dzTq declare, champ branche (value + onChange)", "[dzTq,dzSetTq]=x.useState(\"\")" in FM
      and 'placeholder:"Search…",style:{width:220},value:dzTq,onChange:dzSetTq' in FM, "")
check("4.5 fm : la grille rend dzTplFiltre(d,dzTq), la selection reste lue dans d (liste complete)",
      FM.count("children:dzTplFiltre(d,dzTq).map(f=>{const m=t===f.id;") == 1 and "u=d.find(f=>f.id===t)||d[0]" in FM, "")

print("\n[5] groupe P1 du maillon et syntaxe")
_P1 = [t for t, _a, _r in getattr(P, "P1", [])]
check("5.1 P1 en queue de PATCHES : P1fg1 puis les sections de la tache #3",
      _P1[:1] == ["P1fg1-rangee-figma-token-dans-les-reglages"] and len(_P1) == 9
      and [t for t, _a, _r in P.PATCHES[-len(_P1):]] == _P1, _d(_P1))
_nc = subprocess.run([NODE, "--check", str(BUNDLE)], capture_output=True, text=True) if NODE else None
check("5.2 le bundle ENTIER passe node --check", _nc is not None and _nc.returncode == 0, _d(_nc.stderr[-300:] if _nc else ""))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
