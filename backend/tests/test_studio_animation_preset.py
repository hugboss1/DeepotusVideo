# -*- coding: utf-8 -*-
"""Studio, nœud Animation — le champ « Preset » agit sur l'élément sélectionné (17/10/2026).

Relevé (base 39241c15) : `mk(t)` crée chaque élément (+ Text / + Sticker / + Image) avec DEUX `keyframes` ; l'aperçu
(`dzKfs` → `sampleAt`) et le rendu backend (`animation_service.kfs_of` → `transform_at`) lisent `keyframes` dès qu'il
y en a deux, et ne retombent sur `from`/`to` que sinon. Or `applyPreset` n'écrivait QUE `from`/`to`/`easing`/`preset` :
le Preset était enregistré, affiché dans le menu, mais ignoré partout. Pire : le menu montrait le nom enregistré, donc
re-choisir le même preset ne déclenchait aucun `onChange`.
Correctif (maillon de queue dzstudio, famille G*) :
  - G1 : `applyPreset` écrit deux `keyframes` (t 0 = `from` + l'easing du preset, t 1 = `to`), retire `from`/`to`,
    garde le reste de l'élément et ramène la keyframe active à 0 ; `dzPresetDe(el)` rend le nom du preset SEULEMENT si
    les keyframes de l'élément sont exactement celles du preset (deux clés, mêmes valeurs), sinon "" ;
  - G2 : le menu Preset affiche `dzPresetDe(cur)` : un preset périmé ou retouché à la main s'affiche « — » et peut
    être choisi de nouveau.
Ce que ce banc garde :
  [A] câblage dans le bundle ;
  [F] sous node, avec les VRAIES fonctions extraites du bundle (PRESETS, applyPreset, dzKfs, dzEase, sampleAt) :
      l'aperçu suit chaque preset, depuis un élément neuf et depuis un élément à trois keyframes ; le reste de
      l'élément est gardé ; le menu se dérive des keyframes ;
  [R] rendu backend : `animation_service.transform_at` sur l'élément produit par l'inspecteur suit le preset au
      début et à la fin de l'entrée (c'est ce que reçoit POST /api/animate, `elements` tels quels) ;
  [D] maillon de queue `dzstudio`, famille G* : sans les G* = 39241c15 (t230 livré) octet pour octet, inverse =
      02f8162c, comptes figés, aucun texte visible neuf, aucun useState.
Run (depuis backend/) : & $PY tests/test_studio_animation_preset.py"""
import json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI))
sys.path.insert(0, str(RACINE / "scripts"))
sys.path.insert(0, str(RACINE / "backend"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if callable(cond):
        try:
            cond = cond()
        except Exception as e:  # noqa: BLE001
            cond, detail = False, f"{detail} [{type(e).__name__}: {e}]"
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BUN_P = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
RAW = BUN_P.read_bytes()
BUNDLE = RAW.decode("utf-8")
CLES = ("x", "y", "scale", "rotation", "opacity")

print("[A] câblage de l'inspecteur Animation")
check("A1 applyPreset déclarée une fois", BUNDLE.count("function applyPreset(name){") == 1)
_i = BUNDLE.find("function applyPreset(name){")
AP = BUNDLE[_i:BUNDLE.find("function upload(ev){", _i)]
check("A2 applyPreset écrit des keyframes et ramène la keyframe active à 0",
      "keyframes:[" in AP and "setAk(0)" in AP, AP[:200])
check("A3 applyPreset retire from/to (plus d'ambiguïté avec les keyframes)",
      "delete ne.from" in AP and "delete ne.to" in AP)
check("A4 le menu Preset affiche dzPresetDe(cur), plus cur.preset brut",
      BUNDLE.count('r.jsx(O,{label:"Preset",children:r.jsx(re,{value:dzPresetDe(cur),') == 1
      and 'r.jsx(O,{label:"Preset",children:r.jsx(re,{value:cur.preset||"",' not in BUNDLE)
check("A5 le choix d'un preset appelle toujours applyPreset (onChange inchangé)",
      BUNDLE.count("onChange:function(v){v&&applyPreset(v)}") == 1)

print("[F] sous node : l'aperçu suit le preset")
HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");
const cut=(a,b)=>{const i=S.indexOf(a),j=S.indexOf(b,i);if(i<0||j<0)throw new Error("introuvable : "+a);return S.slice(i,j)};
const BLK=cut("var PRESETS=","function upload(ev){");
const KFS=cut("function dzKfs(el){","function curKfs(){");
const EAS=cut("function dzEase(n,t){","function sampleAt(el,u){");
const SMP=cut("function sampleAt(el,u){","function play(){");
function portee(els,sel){
 const st={els:els,ak:7,nAk:0};
 const f=new Function("els","sel","cur","setEls","setAk",KFS+EAS+SMP+BLK+
  ";return{PRESETS,applyPreset,sampleAt,dzPresetDe:typeof dzPresetDe==='function'?dzPresetDe:null}");
 const R=f(els,sel,els[sel],(a)=>{st.els=a},(v)=>{st.nAk++;st.ak=v});
 return{st,R};
}
const neuf=()=>({id:"el_a",type:"text",text:"RIPPLED",style:{font:"Anton",size:80},
 keyframes:[{t:0,x:50,y:60,scale:.6,rotation:0,opacity:0,easing:"easeOutBack"},{t:1,x:50,y:45,scale:1,rotation:0,opacity:1}],
 start:1.5,dur:.8,hold:2,preset:null});
const trois=()=>Object.assign(neuf(),{type:"image",text:undefined,filename:"logo.png",
 keyframes:[{t:0,x:10,y:10,scale:1,rotation:0,opacity:1,easing:"linear"},{t:.5,x:20,y:80,scale:2,rotation:45,opacity:1,easing:"easeIn"},{t:1,x:90,y:90,scale:1,rotation:0,opacity:1}]});
const rnd=o=>{const z={};for(const k of ["x","y","scale","rotation","opacity"])z[k]=Math.round(o[k]*1000)/1000;return z};
const OUT={presets:{},noms:[]};
const P0=portee([neuf()],0).R.PRESETS;OUT.noms=Object.keys(P0);
for(const nom of OUT.noms){
 const r={};
 for(const [cas,fab] of [["neuf",neuf],["trois",trois]]){
  const p=portee([{id:"autre"},fab()],1);p.R.applyPreset(nom);const el=p.st.els[1];
  const q=portee(p.st.els,1);
  r[cas]={u0:rnd(q.R.sampleAt(el,0)),u1:rnd(q.R.sampleAt(el,1)),nkf:(el.keyframes||[]).length,
   ease0:el.keyframes&&el.keyframes[0]&&el.keyframes[0].easing,preset:el.preset,
   aFromTo:("from" in el)||("to" in el),ak:p.st.ak,nAk:p.st.nAk,el:el,autre:p.st.els[0],
   affiche:q.R.dzPresetDe?q.R.dzPresetDe(el):null};
 }
 r.from=P0[nom].from;r.to=P0[nom].to;r.easing=P0[nom].easing;OUT.presets[nom]=r;
}
// le menu : périmé (preset enregistré, keyframes de mk) ; retouché à la main ; easing changé
const pe=portee([Object.assign(neuf(),{preset:"slide-down"})],0);
OUT.perime=pe.R.dzPresetDe?pe.R.dzPresetDe(pe.st.els[0]):null;
const pr=portee([neuf()],0);pr.R.applyPreset("pop");const ret=JSON.parse(JSON.stringify(pr.st.els[0]));
ret.keyframes[1].x=61;OUT.retouche=portee([ret],0).R.dzPresetDe?portee([ret],0).R.dzPresetDe(ret):null;
const ez=JSON.parse(JSON.stringify(pr.st.els[0]));ez.keyframes[0].easing="linear";
OUT.easing=portee([ez],0).R.dzPresetDe?portee([ez],0).R.dzPresetDe(ez):null;
const k3=JSON.parse(JSON.stringify(pr.st.els[0]));k3.keyframes.push({t:1.5,x:5,y:5,scale:1,rotation:0,opacity:1});
OUT.trois=portee([k3],0).R.dzPresetDe?portee([k3],0).R.dzPresetDe(k3):null;
OUT.vide=portee([neuf()],0).R.dzPresetDe?portee([neuf()],0).R.dzPresetDe(neuf()):null;
// rien de sélectionné : applyPreset ne fait rien
const rien=portee([],0);rien.R.applyPreset("pop");OUT.rien=rien.st.els.length;
console.log(JSON.stringify(OUT));
"""


def node_run():
    with tempfile.TemporaryDirectory() as td:
        h = pathlib.Path(td) / "h.js"
        h.write_text(HARNAIS, encoding="utf-8")
        p = subprocess.run(["node", str(h), str(BUN_P)], capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if p.returncode != 0:
            raise RuntimeError(p.stderr[-500:])
        return json.loads(p.stdout.strip().splitlines()[-1])


try:
    O = node_run()
    err = ""
except Exception as e:  # noqa: BLE001
    O, err = {}, str(e)[:300]
PR = O.get("presets") or {}
check("F1 les fonctions de l'inspecteur s'exécutent sous node", bool(O), err)
check("F2 les 8 presets sont lus", O.get("noms") == ["fade-in", "slide-up", "slide-down", "slide-left", "slide-right",
                                                       "pop", "zoom-in", "ken-burns"], str(O.get("noms")))


def egal(a, b):
    return all(abs(float(a.get(k, -1e9)) - float(b.get(k, 0))) < 1e-6 for k in CLES)


for cas, lib in (("neuf", "élément neuf (2 keyframes de mk)"), ("trois", "élément à 3 keyframes")):
    mauvais = [n for n, r in PR.items() if not (egal(r[cas]["u0"], r["from"]) and egal(r[cas]["u1"], r["to"]))]
    check(f"F3 {lib} : l'aperçu part du « from » et arrive au « to » de chaque preset", bool(PR) and not mauvais,
          str(mauvais) + " " + str({n: (PR[n][cas]["u0"], PR[n]["from"]) for n in mauvais[:1]}))
    mauvais = [n for n, r in PR.items() if r[cas]["nkf"] != 2 or r[cas].get("ease0") != r["easing"]]
    check(f"F4 {lib} : deux keyframes, la première porte l'easing du preset", bool(PR) and not mauvais, str(mauvais))
check("F5 from/to retirés, preset nommé, keyframe active ramenée à 0",
      bool(PR) and all(not r[c]["aFromTo"] and r[c]["preset"] == n and r[c]["ak"] == 0 and r[c]["nAk"] == 1
                       for n, r in PR.items() for c in ("neuf", "trois")),
      str({n: (r["neuf"]["aFromTo"], r["neuf"]["ak"]) for n, r in list(PR.items())[:2]}))
GARDE = ("id", "type", "text", "style", "start", "dur", "hold", "filename")
check("F6 le reste de l'élément est gardé (id, type, texte, style, start/dur/hold, fichier), l'autre élément intact",
      bool(PR) and all(r["neuf"]["el"].get(k) == {"id": "el_a", "type": "text", "text": "RIPPLED",
                                                   "style": {"font": "Anton", "size": 80}, "start": 1.5, "dur": .8,
                                                   "hold": 2}.get(k) for r in PR.values() for k in GARDE)
      and all(r["trois"]["el"].get("filename") == "logo.png" and r["trois"]["autre"] == {"id": "autre"}
              for r in PR.values()))
check("F7 le menu affiche le preset appliqué", bool(PR) and all(r[c]["affiche"] == n for n, r in PR.items()
                                                                 for c in ("neuf", "trois")),
      str({n: r["neuf"]["affiche"] for n, r in list(PR.items())[:3]}))
check("F8 preset périmé (nom enregistré, keyframes d'origine) : le menu affiche « — » (re-choisissable)",
      O.get("perime") == "", repr(O.get("perime")))
check("F9 keyframe retouchée à la main : le menu affiche « — »", O.get("retouche") == "", repr(O.get("retouche")))
check("F10 seul l'easing changé : le preset reste affiché (le mouvement est le sien)", O.get("easing") == "pop",
      repr(O.get("easing")))
check("F11 élément sans preset : « — »", O.get("vide") == "", repr(O.get("vide")))
check("F13 une keyframe ajoutée après celles du preset : « — » (le mouvement n'est plus le sien)", O.get("trois") == "",
      repr(O.get("trois")))
check("F12 aucun élément sélectionné : applyPreset ne fait rien", O.get("rien") == 0, repr(O.get("rien")))

print("[R] rendu backend : transform_at suit le preset")
try:
    from app.services import animation_service as A   # noqa: E402
    err = ""
except Exception as e:  # noqa: BLE001
    A, err = None, str(e)[:200]
check("R1 animation_service importé", A is not None, err)
if A is not None and PR:
    mauvais = []
    for n, r in PR.items():
        for c in ("neuf", "trois"):
            el = r[c]["el"]
            d0 = A.transform_at(el, el["start"])
            d1 = A.transform_at(el, el["start"] + el["dur"])
            if not (d0 and d1 and egal(d0, r["from"]) and egal(d1, r["to"])):
                mauvais.append((n, c, d0, d1))
    check("R2 pour chaque preset, le rendu part du « from » au début de l'entrée et arrive au « to » à sa fin",
          not mauvais, str(mauvais[:1]))
    el = PR["slide-down"]["neuf"]["el"]
    mi = A.transform_at(el, el["start"] + el["dur"] / 2)
    # easeOut(½) = ¾ : y = 35 + 20·¾ = 50, opacité ¾ (la base, keyframes de mk en easeOutBack, donnait ≈ 1,09)
    check("R3 slide-down à mi-entrée (easeOut) : y = 50, opacité 0,75, x fixe à 50",
          bool(mi) and abs(mi["y"] - 50) < 1e-6 and abs(mi["opacity"] - .75) < 1e-6 and mi["x"] == 50, str(mi))
    check("R4 hors fenêtre (avant start, après start+dur+hold) : rien dessiné",
          A.transform_at(el, el["start"] - .01) is None and A.transform_at(el, el["start"] + el["dur"] + el["hold"] + .01) is None)
else:
    check("R2 rendu backend vérifiable", False, "pas d'éléments produits")

print("[D] maillon dzstudio, famille G*")
import patch_bundle_dzstudio as M                                    # noqa: E402
import _i18n_l1_aide as AIDE                                         # noqa: E402


# t280 : la couche sonvfx a été retouchée après ces bases (consignée L4 + G1, réinjectée par refresh_layer) — le bloc
# SONVFX attendu est celui du livré ; ce banc vérifie ses maillons HORS de ce bloc
def git_bundle(rev):
    b_ = _git_bundle_brut(rev)
    return None if b_ is None else __import__("_i18n_l1_aide").base_avec_couches_livrees(
        b_, (RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js").read_bytes())


def _git_bundle_brut(rev):
    r_ = subprocess.run(["git", "show", f"{rev}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
    if r_.returncode != 0:
        return None
    b_ = r_.stdout                                  # blob normalisé LF (autocrlf) → les CRLF du fichier extrait
    return b_ if b"\r\n" in b_ else b_.replace(b"\n", b"\r\n")


PG = list(getattr(M, "PAIRES_G", []))
_AVG = M.PAIRES_AB + M.PAIRES_C + M.PAIRES_F + M.PAIRES_D + M.PAIRES_E
_NAV = len(_AVG)
check("D1 famille G* déclarée (PAIRES_G, 2 paires), juste après les E*", len(PG) == 2
      and M.PAIRES[:_NAV] == _AVG and M.PAIRES[_NAV:_NAV + len(PG)] == PG, str(len(PG)))
try:
    avant = M.defaire(AIDE.avant_dzmotion(BUNDLE))       # t235 : le maillon dzmotion, posé APRÈS, défait d'abord
except AssertionError as e:
    avant = None
    check("D2 toutes les paires sont dans le livré", False, str(e)[:160])
base_t230 = git_bundle("39241c15")
base_t224 = git_bundle("02f8162c")
check("D3 inverse = 02f8162c octet pour octet", avant is not None and base_t224 is not None
      and AIDE.avant_dzstudio(BUNDLE).encode("utf-8") == base_t224)


def sans_g(s):
    for a_, r_ in M.PAIRES[:_NAV]:
        s = s.replace(a_, r_, 1)
    return s


check("D4 sans les G* = 39241c15 (t230 livré) octet pour octet", avant is not None and base_t230 is not None and bool(PG)
      and sans_g(avant).encode("utf-8") == base_t230)
check("D5 aller-retour exact", avant is not None and M.appliquer(avant) == AIDE.avant_dzmotion(BUNDLE))
check("D6 comptes figés (useState 731, v2.8.0 ×4, DzTracks 181)",
      BUNDLE.count("x.useState(") == 731 and BUNDLE.count("v2.8.0") == 4 and BUNDLE.count("DzTracks") == 181)
check("D7 octets : CRLF préservés, aucun LF nu", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
check("D8 aucun .bak_dzstudio laissé", not (BUN_P.parent / (BUN_P.name + ".bak_dzstudio")).exists())
check("D9 aucun texte visible neuf (dzT inchangés), aucun useState dans les G*",
      bool(PG) and all(r_.count("dzT(") == a_.count("dzT(") and "useState" not in r_ for a_, r_ in PG))
check("D10 garde : un bundle t230 (sans les G*) est « partiellement appliqué »",
      avant is not None and bool(PG) and M.partiel(sans_g(avant)) and not M.partiel(BUNDLE))
rc = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_dzstudio.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", cwd=str(RACINE), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check("D11 --check : déjà appliqué", rc.returncode == 0 and "déjà appliqué" in rc.stdout, rc.stdout + rc.stderr)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
