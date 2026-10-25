# -*- coding: utf-8 -*-
"""Studio t229 — A2 : les boutons de zoom ± zooment autour du CENTRE de la vue (17/10/2026).

Relevé (base 1be65c00) : la molette (`onWheel:M`) recalcule le pan pour garder fixe le point sous le curseur
(`x:S-(S-ce.x)*(J/h)`), mais les boutons ± ne faisaient que `b(R=>Math.max(.3,R-.1))` / `b(R=>Math.min(1.5,R+.1))` :
le pan ne bougeait pas, le zoom pivotait autour du coin (0,0) du canevas (`transformOrigin:"0 0"`) et la vue partait
vers le haut à gauche. Correctif : `dzZoomCentre(cv,h,J,z,b)` au niveau du module, même formule que la molette avec
le centre du rectangle du canevas comme pivot ; les deux boutons l'appellent avec `N.current`.

Ce que ce banc garde :
  [A] câblage : les deux boutons appellent `dzZoomCentre(N.current,h,…)` avec les mêmes bornes .3 / 1.5 et le même
      pas .1 qu'avant ; la molette est inchangée ; `dzZoomCentre` déclarée une fois, au niveau du module ;
  [F] sous node, avec les VRAIES expressions onClick extraites du bundle : le point central du canevas reste fixe à
      ± 0,5 px sur une suite de clics + et −, depuis un pan quelconque ; bornes respectées ; à la borne, aucun appel
      (ni pan ni zoom) ; sans canevas (ref nulle) le zoom change quand même, sans erreur ;
  [D] maillon de queue `dzstudio`, famille E* : sans les E* = 1be65c00 (t228 livré) octet pour octet, inverse =
      02f8162c, comptes figés, aucun texte visible neuf, aucun useState.
Run (depuis backend/) : & $PY tests/test_studio_zoom_boutons.py"""
import json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI))
sys.path.insert(0, str(RACINE / "scripts"))

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

ARR = 'r.jsx(se,{name:"dz-action-zoom-arriere",size:26,onClick:'
AVT = 'r.jsx(se,{name:"dz-action-zoom-avant",size:26,onClick:'


def expr_clic(s, tete):
    """L'expression onClick d'un bouton (jusqu'au `})` qui ferme ses props)."""
    i = s.find(tete)
    if i < 0:
        return ""
    i += len(tete)
    j = s.find("})", i)
    return s[i:j] if j > 0 else ""


print("[A] câblage des boutons")
E_ARR, E_AVT = expr_clic(BUNDLE, ARR), expr_clic(BUNDLE, AVT)
check("A1 boutons zoom ± trouvés, une seule fois", BUNDLE.count(ARR) == 1 and BUNDLE.count(AVT) == 1)
check("A2 − : dzZoomCentre(N.current,h,Math.max(.3,h-.1),z,b)",
      E_ARR == "()=>dzZoomCentre(N.current,h,Math.max(.3,h-.1),z,b)", E_ARR)
check("A3 + : dzZoomCentre(N.current,h,Math.min(1.5,h+.1),z,b)",
      E_AVT == "()=>dzZoomCentre(N.current,h,Math.min(1.5,h+.1),z,b)", E_AVT)
check("A4 plus de zoom sans pan (b(R=>…) seul) sur les boutons",
      "b(R=>Math.max(.3,R-.1))" not in BUNDLE and "b(R=>Math.min(1.5,R+.1))" not in BUNDLE)
check("A5 molette inchangée (pivot = curseur)",
      BUNDLE.count("J=Math.max(.3,Math.min(1.5,h-R.deltaY*.0015));J!==h&&(z(ce=>({x:S-(S-ce.x)*(J/h),"
                   "y:L-(L-ce.y)*(J/h)})),b(J))") == 1)
check("A6 dzZoomCentre déclarée une fois, au niveau du module (devant dzRaccRef)",
      BUNDLE.count("function dzZoomCentre(cv,h,J,z,b){") == 1
      and 0 <= BUNDLE.find("function dzZoomCentre(cv,h,J,z,b){") < BUNDLE.find("function dzRaccRef(el){"))
check("A7 le canevas reste N (ref) et la vue pivote en 0 0",
      BUNDLE.count("transform:`translate(${_.x}px, ${_.y}px) scale(${h})`,transformOrigin:\"0 0\"") == 1)

print("[F] sous node : le centre de la vue reste fixe")
HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");const E=JSON.parse(fs.readFileSync(process.argv[3],"utf8"));
const i=S.indexOf("function dzZoomCentre(cv,h,J,z,b){"),j=S.indexOf("function dzRaccRef(el){",i);
if(i<0||j<0)throw new Error("dzZoomCentre introuvable");
const dzZoomCentre=new Function(S.slice(i,j)+";return dzZoomCentre")();
function etat(w,hh,zoom,pan){
 const st={h:zoom,pan:{x:pan.x,y:pan.y},nz:0,nb:0};
 const cv=w==null?null:{getBoundingClientRect:()=>({left:300,top:107,right:300+w,bottom:107+hh,width:w,height:hh})};
 const z=f=>{st.nz++;st.pan=typeof f=="function"?f(st.pan):f};const b=v=>{st.nb++;st.h=typeof v=="function"?v(st.h):v};
 const clic=ex=>new Function("N","h","z","b","dzZoomCentre","return "+ex)({current:cv},st.h,z,b,dzZoomCentre)();
 return{st,clic,cx:w/2,cy:hh/2};
}
// point du graphe sous le centre du canevas
const sousCentre=e=>({x:(e.cx-e.st.pan.x)/e.st.h,y:(e.cy-e.st.pan.y)/e.st.h});
const OUT={};
// 1. suite de clics depuis un pan quelconque (1000 px de large, inspecteur ouvert)
let e=etat(1000,640,.75,{x:-137,y:58});const g0=sousCentre(e);let derive=0;const zs=[];
for(const k of ["+","+","+","-","-","-","-","-","+","-"]){e.clic(k=="+"?E.avt:E.arr);const g=sousCentre(e);
 derive=Math.max(derive,Math.abs((g.x-g0.x)*e.st.h),Math.abs((g.y-g0.y)*e.st.h));zs.push(Math.round(e.st.h*100))}
OUT.suite={derive,zs,nz:e.st.nz,nb:e.st.nb};
// 2. un clic + au zoom 75 % depuis le pan {0,0} (le cas du relevé)
e=etat(1200,700,.75,{x:0,y:0});e.clic(E.avt);OUT.un={h:Math.round(e.st.h*100)/100,pan:{x:Math.round(e.st.pan.x*100)/100,y:Math.round(e.st.pan.y*100)/100}};
// 3. bornes : à 150 % le + ne fait rien (ni pan ni zoom) ; à 30 % le − non plus
e=etat(1200,700,1.5,{x:10,y:20});e.clic(E.avt);OUT.max={h:e.st.h,nz:e.st.nz,nb:e.st.nb,pan:e.st.pan};
e=etat(1200,700,.3,{x:10,y:20});e.clic(E.arr);OUT.min={h:e.st.h,nz:e.st.nz,nb:e.st.nb,pan:e.st.pan};
// 4. jamais au-delà des bornes : 20 clics + puis 30 clics −
e=etat(1200,700,.75,{x:0,y:0});let hi=0,lo=9;for(let k=0;k<20;k++){e.clic(E.avt);hi=Math.max(hi,e.st.h)}
for(let k=0;k<30;k++){e.clic(E.arr);lo=Math.min(lo,e.st.h)}OUT.bornes={hi,lo};
// 5. ref nulle (canevas pas encore monté) : le zoom change, le pan ne bouge pas, pas d'erreur
OUT.nul=(()=>{try{const f=etat(null,0,.75,{x:5,y:6});f.clic(E.avt);return{h:Math.round(f.st.h*100)/100,nz:f.st.nz,pan:f.st.pan}}catch(x){return String(x)}})();
console.log(JSON.stringify(OUT));
"""


def node_run():
    with tempfile.TemporaryDirectory() as td:
        h = pathlib.Path(td) / "h.js"
        h.write_text(HARNAIS, encoding="utf-8")
        ej = pathlib.Path(td) / "e.json"
        ej.write_text(json.dumps({"arr": E_ARR, "avt": E_AVT}), encoding="utf-8")
        p = subprocess.run(["node", str(h), str(BUN_P), str(ej)], capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if p.returncode != 0:
            raise RuntimeError(p.stderr[-500:])
        return json.loads(p.stdout.strip().splitlines()[-1])


try:
    O = node_run()
    err = ""
except Exception as e:  # noqa: BLE001
    O, err = {}, str(e)[:300]
SUITE = O.get("suite") or {}
check("F1 dzZoomCentre et les onClick s'exécutent sous node", bool(O), err)
check("F2 suite de clics + / − : le centre de la vue reste fixe à ± 0,5 px",
      SUITE.get("derive", 9) <= 0.5, str(SUITE.get("derive")))
check("F3 la suite suit le pas de 10 % (85 95 105 95 85 75 65 55 65 55)",
      SUITE.get("zs") == [85, 95, 105, 95, 85, 75, 65, 55, 65, 55], str(SUITE.get("zs")))
check("F4 chaque clic recalcule le pan ET le zoom (10 + 10)", SUITE.get("nz") == 10 and SUITE.get("nb") == 10,
      str(SUITE))
# 1200×700, 75 % → 85 %, pan {0,0} : x' = 600 − 600·(.85/.75) = −80 ; y' = 350 − 350·(.85/.75) = −46,67
check("F5 un clic + à 75 % depuis {0,0} : pan {−80 ; −46,67}, la vue ne part plus en haut à gauche",
      O.get("un") == {"h": 0.85, "pan": {"x": -80, "y": -46.67}}, str(O.get("un")))
check("F6 à 150 %, + ne fait rien (ni pan ni zoom)",
      O.get("max") == {"h": 1.5, "nz": 0, "nb": 0, "pan": {"x": 10, "y": 20}}, str(O.get("max")))
check("F7 à 30 %, − ne fait rien (ni pan ni zoom)",
      O.get("min") == {"h": 0.3, "nz": 0, "nb": 0, "pan": {"x": 10, "y": 20}}, str(O.get("min")))
check("F8 jamais au-delà des bornes (≤ 150 %, ≥ 30 %)",
      (O.get("bornes") or {}).get("hi", 9) <= 1.5 + 1e-9 and (O.get("bornes") or {}).get("lo", 0) >= 0.3 - 1e-9,
      str(O.get("bornes")))
check("F9 ref nulle : le zoom change, le pan reste, sans erreur",
      O.get("nul") == {"h": 0.85, "nz": 0, "pan": {"x": 5, "y": 6}}, str(O.get("nul")))

print("[D] maillon dzstudio, famille E*")
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


PE = list(getattr(M, "PAIRES_E", []))
_NAV = len(M.PAIRES_AB + M.PAIRES_C + M.PAIRES_F + M.PAIRES_D)
check("E1 famille E* déclarée (PAIRES_E, 3 paires), juste après les D*", len(PE) == 3
      and M.PAIRES[:_NAV] == M.PAIRES_AB + M.PAIRES_C + M.PAIRES_F + M.PAIRES_D and M.PAIRES[_NAV:_NAV + len(PE)] == PE,
      str(len(PE)))
try:
    avant = M.defaire(AIDE.avant_dzmotion(BUNDLE))       # t235 : le maillon dzmotion, posé APRÈS, défait d'abord
except AssertionError as e:
    avant = None
    check("E2 toutes les paires sont dans le livré", False, str(e)[:160])
base_t228 = git_bundle("1be65c00")
base_t224 = git_bundle("02f8162c")
check("E3 inverse = 02f8162c octet pour octet", avant is not None and base_t224 is not None
      and AIDE.avant_dzstudio(BUNDLE).encode("utf-8") == base_t224)


def sans_e(s):
    for a_, r_ in M.PAIRES[:_NAV]:
        s = s.replace(a_, r_, 1)
    return s


check("E4 sans les E* = 1be65c00 (t228 livré) octet pour octet", avant is not None and base_t228 is not None and bool(PE)
      and sans_e(avant).encode("utf-8") == base_t228)
check("E5 aller-retour exact", avant is not None and M.appliquer(avant) == AIDE.avant_dzmotion(BUNDLE))
check("E6 comptes figés (useState 731, v2.8.0 ×4, DzTracks 181)",
      BUNDLE.count("x.useState(") == 731 and BUNDLE.count("v2.8.0") == 4 and BUNDLE.count("DzTracks") == 181)
check("E7 octets : CRLF préservés, aucun LF nu", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
check("E8 aucun .bak_dzstudio laissé", not (BUN_P.parent / (BUN_P.name + ".bak_dzstudio")).exists())
check("E9 aucun texte visible neuf (dzT inchangés), aucun useState dans les E*",
      bool(PE) and all(r_.count("dzT(") == a_.count("dzT(") and "useState" not in r_ for a_, r_ in PE))
check("E10 garde : un bundle t228 (sans les E*) est « partiellement appliqué »",
      avant is not None and bool(PE) and M.partiel(sans_e(avant)) and not M.partiel(BUNDLE))
rc = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_dzstudio.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", cwd=str(RACINE), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check("E11 --check : déjà appliqué", rc.returncode == 0 and "déjà appliqué" in rc.stdout, rc.stdout + rc.stderr)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
