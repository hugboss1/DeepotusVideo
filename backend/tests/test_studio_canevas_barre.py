# -*- coding: utf-8 -*-
"""Studio t228 — A1 : la barre du graphe sur deux ou trois lignes ne cache plus le graphe (17/10/2026).

Relevé (base eda56717, backend de preuve, 1500 px, inspecteur ouvert) : la barre `data-dz-gbar` fait 107 px
(`--dz-gbar-h`), le canevas garde `top:48` → 59 px du canevas sous la barre, le haut d'Article News / Script News /
Avatar HeyGen masqué de 14 px ; l'encart des raccourcis (`top:60` fixe dans le canevas) recouvre Avatar HeyGen. À 1500
fermé (75 px) et à 1920 (75 / 48 px) rien n'est caché. Décision de l'utilisateur (maquette t228-maquette.png) :
option B, le canevas commence SOUS la barre et suit sa hauteur en direct ; l'encart se replie en pastille « ⌘ »
quand il chevauche un nœud ; pas de bouton « Recadrer ».

Ce que ce banc garde :
  [A] canevas : `top:"var(--dz-gbar-h, 48px)"` (plus de `top:48` fixe) ; les conversions écran → graphe passent
      toujours par `getBoundingClientRect` du canevas (dépôt, lien, molette) ;
  [B] encart : `top:12` dans le canevas, `ref` rappelé à chaque rendu (fonction en ligne) vers `dzRaccRef`, le texte
      complet dans `data-dz-racc-plein` (mêmes clés dzT qu'avant), la pastille `data-dz-racc-pastille` (« ⌘ ») ;
  [F] `dzRaccRef` sous node (DOM simulé) : chevauchement → pastille + infobulle = texte complet ; sinon encart plein ;
      test sur la taille PLEINE mémorisée (pas d'oscillation en pastille) ; bords qui se touchent ≠ chevauchement ;
      un seul ResizeObserver sur le canevas, qui relance le test ;
  [D] maillon de queue `dzstudio`, famille D* : sans les D* = eda56717 (t227 livré) octet pour octet, inverse =
      02f8162c, comptes figés, aucun texte visible neuf, aucun useState.
Run (depuis backend/) : & $PY tests/test_studio_canevas_barre.py"""
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


def tranche(s, a, b):
    i = s.find(a)
    if i < 0:
        return ""
    j = s.find(b, i)
    return s[i:j] if j > 0 else ""


print("[A] canevas sous la barre")
CANVAS = tranche(BUNDLE, "onMouseDown:V,onWheel:M,onDragOver:C,onDrop:Q,style:{", "backgroundImage:")
check("A1 canevas du Studio trouvé (onDrop:Q)", bool(CANVAS))
check("A2 canevas à top:var(--dz-gbar-h, 48px)", 'top:"var(--dz-gbar-h, 48px)"' in CANVAS, CANVAS[:160])
check("A3 plus de top:48 fixe sur le canevas", "inset:0,top:48," not in CANVAS
      and BUNDLE.count('onDrop:Q,style:{position:"absolute",inset:0,top:48,') == 0)
check("A4 la barre pose toujours --dz-gbar-h sur leur parent commun (ResizeObserver)",
      BUNDLE.count('p.style.setProperty("--dz-gbar-h",Math.ceil(el.getBoundingClientRect().height)+"px")') == 1
      and BUNDLE.count("ref:__dzGbarRef,\"data-dz-gbar\":\"1\"") == 1)
LH = tranche(BUNDLE, "function Lh({variant:e,onScheduleRender:t}){", "async function")
check("A5 dépôt, lien et molette convertissent depuis le rectangle du canevas (N.current)",
      LH.count("N.current.getBoundingClientRect()") >= 3 and "(de=N.current)==null?void 0:de.getBoundingClientRect()" in LH)
check("A6 bandeau d'erreur toujours sous la barre (calc --dz-gbar-h + 8)",
      BUNDLE.count('top:"calc(var(--dz-gbar-h, 48px) + 8px)"') == 1)

print("[B] encart des raccourcis")
RACC = tranche(BUNDLE, '"data-dz-racc":"1"', ',w&&r.jsx(Jh,')
check("B1 encart balisé data-dz-racc, une seule fois", BUNDLE.count('"data-dz-racc":"1"') == 1 and bool(RACC))
check("B2 ref en ligne (rappelée à chaque rendu) vers dzRaccRef",
      'r.jsxs("div",{ref:function(e_){dzRaccRef(e_)},"data-dz-racc":"1"' in BUNDLE)
check("B3 encart à top:12 dans le canevas (plus de top:60)",
      'style:{position:"absolute",right:12,top:12,zIndex:4,' in RACC and "top:60" not in RACC)
check("B4 texte complet dans data-dz-racc-plein, mêmes clés dzT, sur une ligne",
      '"data-dz-racc-plein":"1"' in RACC and 'whiteSpace:"nowrap"' in RACC
      and 'dzT("studio.graphe.raccourci_noeuds")' in RACC and 'dzT("studio.graphe.raccourci_executer")' in RACC
      and RACC.count("r.jsx(\"kbd\",{style:ns,children:") == 4)
check("B5 pastille data-dz-racc-pastille « ⌘ », cachée au départ",
      '"data-dz-racc-pastille":"1",style:{display:"none"},children:r.jsx("kbd",{style:ns,children:"⌘"})' in RACC)
check("B6 dzRaccRef déclarée une fois, au niveau du module (devant __dzGbarRef)",
      BUNDLE.count("function dzRaccRef(el){") == 1
      and BUNDLE.find("function dzRaccRef(el){") < BUNDLE.find("function __dzGbarRef(el){"))

print("[F] dzRaccRef sous node (DOM simulé)")
HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");
const i=S.indexOf("function dzRaccRef(el){"),j=S.indexOf("function __dzGbarRef(el){",i);
if(i<0||j<0)throw new Error("dzRaccRef introuvable");
const ROS=[];global.ResizeObserver=function(cb){this.cb=cb;this.obs=[];this.observe=t=>this.obs.push(t);ROS.push(this)};
const dzRaccRef=new Function(S.slice(i,j)+";return dzRaccRef")();
const R=1147,T=175,FULL=[242,33],PILL=[30,27];
function rect(l,t,r,b){return{left:l,top:t,right:r,bottom:b,width:r-l,height:b-t}}
function monde(nodes){
 const st=()=>({});const pl={style:{display:"flex"},childNodes:[{textContent:"/"},{textContent:" nœuds"},{textContent:"⌘K"},{textContent:" palette"},{textContent:"⌘⏎"},{textContent:" exécuter"}]};
 const pa={style:{display:"none"}};
 const cv={nodes,querySelectorAll:s=>s==="[data-node-id]"?cv.nodes.map(n=>({getBoundingClientRect:()=>rect(...n)})):[]};
 const at={};
 const el={parentNode:cv,style:{},title:"",getAttribute:k=>k in at?at[k]:null,setAttribute:(k,v)=>{at[k]=String(v)},
  querySelector:s=>s==="[data-dz-racc-plein]"?pl:s==="[data-dz-racc-pastille]"?pa:null,
  getBoundingClientRect(){const p=at["data-dz-pli"]==="1",w=(p?PILL:FULL)[0],h=(p?PILL:FULL)[1];return rect(R-w,T,R,T+h)}};
 return{el,cv,pl,pa,at};
}
function etat(m){return{pli:m.at["data-dz-pli"],pl:m.pl.style.display,pa:m.pa.style.display,title:m.el.title,
 pad:m.el.style.padding,rad:m.el.style.borderRadius}}
const OUT={};
// 1. aucun nœud sous l'encart
let m=monde([[100,300,265,446]]);dzRaccRef(m.el);OUT.libre=etat(m);
// 2. un nœud sous l'encart (Avatar HeyGen à 1500 px)
const n0=ROS.length;m=monde([[898,190,1063,354]]);dzRaccRef(m.el);OUT.chevauche=etat(m);
// 3. repassage en pastille : le nœud ne touche que la zone PLEINE (pas la pastille) → reste en pastille
dzRaccRef(m.el);OUT.stable=etat(m);
// 4. le nœud s'éloigne → encart plein ; relance par le ResizeObserver
m.cv.nodes=[[100,400,265,546]];ROS[ROS.length-1].cb();OUT.eloigne=etat(m);
OUT.ro={n:ROS.length-n0,obs:ROS[ROS.length-1].obs.length,obsCv:ROS[ROS.length-1].obs[0]===m.cv};
dzRaccRef(m.el);dzRaccRef(m.el);OUT.roUnique=ROS.length-n0;
// 5. bords qui se touchent : nœud dont le bord droit = bord gauche de l'encart plein
m=monde([[700,180,R-FULL[0],260]]);dzRaccRef(m.el);OUT.bord=etat(m);
// 6. nœud sous la pastille seulement (à droite) → pastille
m=monde([[1130,190,1300,300]]);dzRaccRef(m.el);OUT.droite=etat(m);
// 7. ref null (démontage) → rien
OUT.nul=(()=>{try{dzRaccRef(null);return "ok"}catch(e){return String(e)}})();
console.log(JSON.stringify(OUT));
"""


def node_run():
    with tempfile.TemporaryDirectory() as td:
        h = pathlib.Path(td) / "h.js"
        h.write_text(HARNAIS, encoding="utf-8")
        p = subprocess.run(["node", str(h), str(BUN_P)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode != 0:
            raise RuntimeError(p.stderr[-500:])
        return json.loads(p.stdout.strip().splitlines()[-1])


try:
    O = node_run()
    err = ""
except Exception as e:  # noqa: BLE001
    O, err = {}, str(e)[:300]
TXT = "/ nœuds ⌘K palette ⌘⏎ exécuter"
PLEIN = {"pli": "0", "pl": "flex", "pa": "none", "title": "", "pad": "6px 10px", "rad": "var(--r-sm)"}
PASTILLE = {"pli": "1", "pl": "none", "pa": "inline-flex", "title": TXT, "pad": "4px 6px", "rad": "999px"}
check("F1 dzRaccRef s'exécute sous node", bool(O), err)
check("F2 aucun nœud dessous → encart plein, pas d'infobulle", O.get("libre") == PLEIN, str(O.get("libre")))
check("F3 nœud dessous → pastille « ⌘ », infobulle = texte complet", O.get("chevauche") == PASTILLE, str(O.get("chevauche")))
check("F4 en pastille, le test garde la taille PLEINE mémorisée (pas d'oscillation)",
      O.get("stable") == PASTILLE, str(O.get("stable")))
check("F5 le nœud s'éloigne → encart plein (relancé par le ResizeObserver)", O.get("eloigne") == PLEIN, str(O.get("eloigne")))
check("F6 un seul ResizeObserver, posé sur le canevas", O.get("ro") == {"n": 1, "obs": 1, "obsCv": True}
      and O.get("roUnique") == 1, str(O.get("ro")) + str(O.get("roUnique")))
check("F7 bords qui se touchent ≠ chevauchement", O.get("bord") == PLEIN, str(O.get("bord")))
check("F8 nœud sous la seule zone de la pastille → pastille", O.get("droite") == PASTILLE, str(O.get("droite")))
check("F9 ref null (démontage) sans erreur", O.get("nul") == "ok", str(O.get("nul")))

print("[D] maillon dzstudio, famille D*")
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


PD = list(getattr(M, "PAIRES_D", []))
_NAD = len(M.PAIRES_AB + M.PAIRES_C + M.PAIRES_F)            # t229 : les E* viennent après les D* → borné à ses familles
check("D1 famille D* déclarée (PAIRES_D, 3 paires), juste après AB + C + F", len(PD) == 3
      and M.PAIRES[:_NAD] == M.PAIRES_AB + M.PAIRES_C + M.PAIRES_F and M.PAIRES[_NAD:_NAD + len(PD)] == PD,
      str(len(PD)))
try:
    avant = M.defaire(AIDE.avant_dzmotion(BUNDLE))       # t235 : le maillon dzmotion, posé APRÈS, défait d'abord
except AssertionError as e:
    avant = None
    check("D2 toutes les paires sont dans le livré", False, str(e)[:160])
base_t227 = git_bundle("eda56717")
base_t224 = git_bundle("02f8162c")
check("D3 inverse = 02f8162c octet pour octet", avant is not None and base_t224 is not None
      and AIDE.avant_dzstudio(BUNDLE).encode("utf-8") == base_t224)


def sans_d(s):
    for a_, r_ in M.PAIRES_AB + M.PAIRES_C + M.PAIRES_F:
        s = s.replace(a_, r_, 1)
    return s


check("D4 sans les D* = eda56717 (t227 livré) octet pour octet", avant is not None and base_t227 is not None and bool(PD)
      and sans_d(avant).encode("utf-8") == base_t227)
check("D5 aller-retour exact", avant is not None and M.appliquer(avant) == AIDE.avant_dzmotion(BUNDLE))
check("D6 comptes figés (useState 731, v2.8.0 ×4, DzTracks 181)",
      BUNDLE.count("x.useState(") == 731 and BUNDLE.count("v2.8.0") == 4 and BUNDLE.count("DzTracks") == 181)
check("D7 octets : CRLF préservés, aucun LF nu", RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n"))
check("D8 aucun .bak_dzstudio laissé", not (BUN_P.parent / (BUN_P.name + ".bak_dzstudio")).exists())
check("D9 aucun texte visible neuf (dzT inchangés), aucun useState dans les D*",
      bool(PD) and all(r_.count("dzT(") == a_.count("dzT(") and "useState" not in r_ for a_, r_ in PD))
check("D10 garde : un bundle t227 (sans les D*) est « partiellement appliqué »",
      avant is not None and bool(PD) and M.partiel(sans_d(avant)) and not M.partiel(BUNDLE))
rc = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_dzstudio.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", cwd=str(RACINE), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check("D11 --check : déjà appliqué", rc.returncode == 0 and "déjà appliqué" in rc.stdout, rc.stdout + rc.stderr)

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
