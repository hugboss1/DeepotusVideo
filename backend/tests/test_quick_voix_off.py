# -*- coding: utf-8 -*-
"""t212 (Menus : Quick, 15/10/2026) — l'onglet Voix off de Quick noircissait toute l'application.

Cause : dans `DzQuickVoice`, l'état du réglage de voix s'appelait `dzT` (`dzT=dztS[0]`, patch_bundle_voicemodel). Ce nom
local masquait la fonction de traduction GLOBALE `dzT`, que la traduction L2 (t142) a ensuite appelée dans le même
rendu (`dzT("quick.voix.titre")`…) : « TypeError: dzT is not a function » au premier rendu, et faute d'ErrorBoundary
React démontait tout l'arbre (fond sombre seul). Même défaut, latent, dans l'aperçu vivant du Montage : `liveSync`
déclare `var dzT=DzTracks.dzCss(…)` puis appelle `dzT("montage.overlay.aide")` pour la bulle d'une couche.

Ce que ce banc garde :
  [A] AUCUNE déclaration locale nommée `dzT` dans le bundle (ni var/let/const, ni affectation nue) ; témoin : la base
      46b94085 en a deux ;
  [B] `DzQuickVoice`, extrait du bundle et rendu une fois sous node (hooks simulés, dzT global factice), ne lève rien
      et affiche ses titres traduits ;
  [C] `DzQuickGarde` (ErrorBoundary) : une erreur d'un enfant donne un encart d'alerte traduit, « Réessayer »
      efface l'erreur, « Revenir à Seedance » appelle `retour` ; sans erreur, les enfants passent tels quels ;
  [D] câblage : le contenu défilant de Quick est enveloppé par la garde, avec une clé PAR ONGLET (changer d'onglet
      repart d'une garde neuve) et un retour vers « seedance » ; une seconde garde enveloppe l'écran Quick entier dans
      le shell (une erreur du rendu de Quick lui-même laisse le rail utilisable) ;
  [E] maillon de queue `dzquick` : posé après dzespace, inverse exact, `avant_dzquick` en tête d'`avant_dzespace`,
      aucun .bak, comptes figés intacts (useState 731, v2.8.0 ×4, DzTracks 181) ;
  [F] clés FR/EN `quick.garde.*`, catalogue assemblé à jour ;
  [G] Montage : la source de la couche sonvfx n'a plus `var dzT=` (dzZ, même longueur), le bloc du bundle est à jour
      et la retouche est consignée (L4 montage_a, RETOUCHES de G1) : les générateurs --check restent à jour.
Run (depuis backend/) : & $PY tests/test_quick_voix_off.py"""
import json, pathlib, re, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI))
sys.path.insert(0, str(RACINE / "scripts"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


import os
_ENV = dict(os.environ, PYTHONIOENCODING="utf-8")
BUN_P = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BUNDLE = BUN_P.read_bytes().decode("utf-8")
BASE = "46b94085"

# Une déclaration locale de dzT : `var|let|const dzT`, ou `dzT=` nu (pas `.dzT=`, pas `dzT==`), ou un paramètre.
_DECL = re.compile(r"(?:\b(?:var|let|const)\s+dzT\b)|(?<![\w$.])dzT\s*=(?!=)|function\s*\w*\s*\([^)]*\bdzT\b[^)]*\)")


def declarations(s):
    return [s[max(0, m.start() - 40):m.end() + 30] for m in _DECL.finditer(s)]


print("[A] aucune déclaration locale de dzT")
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
check("A0 témoin : la base 46b94085 en a deux (Quick Voix off, aperçu du Montage)",
      r0.returncode == 0 and len(declarations(r0.stdout.decode("utf-8"))) == 2)
d = declarations(BUNDLE)
check("A1 le bundle n'en a plus aucune", d == [], repr(d[:3]))


# ── le harnais node : extrait une fonction du bundle par appariement des accolades (chaînes sautées) ─────────────
HARNAIS = r"""
const fs=require("fs");const S=fs.readFileSync(process.argv[2],"utf8");const OUT={};
function extraire(debut){const a=S.indexOf(debut);if(a<0)return null;let i=S.indexOf("{",a),d=0,q=null;
 for(;i<S.length;i++){const c=S[i];if(q){if(c==="\\"){i++;continue}if(c===q)q=null;continue}
  if(c==='"'||c==="'"||c==="`"){q=c;continue}if(c==="{")d++;else if(c==="}"){d--;if(!d)break}}
 return S.slice(a,i+1)}
// un objet « quelconque » : toute propriété, tout appel rendent encore lui-même
const QQ=new Proxy(function(){},{get(t,k){if(k===Symbol.toPrimitive)return()=>"";if(k==="then")return undefined;
 if(k==="length")return 0;return QQ},apply(){return QQ}});
const x={useState:i=>[typeof i==="function"?i():i,()=>{}],useReducer:(f,i,init)=>[init?init(i):i,()=>{}],
 useEffect(){},useLayoutEffect(){},useRef:v=>({current:v===undefined?null:v}),useMemo:f=>f(),useCallback:f=>f,
 Component:class{constructor(p){this.props=p;this.state={}}setState(o){this.state=Object.assign({},this.state,typeof o==="function"?o(this.state):o)}}};
const el=(t,p,k)=>({t:typeof t==="string"?t:(t&&t.name)||"?",p:p||{},k});const r={jsx:el,jsxs:el,Fragment:"Fragment"};
const BASE={x,r,dzT:k=>"⟦"+k+"⟧",localStorage:{getItem:()=>null,setItem(){},removeItem(){}},
 window:{addEventListener(){},removeEventListener(){},dispatchEvent(){},location:{href:"http://l/"}},
 fetch:()=>new Promise(()=>{}),console:{error(){},warn(){},log(){}}};
const ENV=new Proxy(BASE,{has:()=>true,get(t,k){if(k===Symbol.unscopables)return undefined;if(k in t)return t[k];
 if(k in globalThis)return globalThis[k];return QQ}});
function texte(n){if(n==null||n===false||n===true||typeof n==="function")return"";if(typeof n==="string"||typeof n==="number")return String(n);
 if(Array.isArray(n))return n.map(texte).join(" ");if(n.p){let s="";for(const k of["label","title","placeholder","aria-label"])
  if(typeof n.p[k]==="string")s+=" "+n.p[k];return s+" "+texte(n.p.children)}return""}
function evaluer(src,nom){return new Function("ENV","with(ENV){"+src+";return "+nom+"}")(ENV)}
// [B] DzQuickVoice rendu une fois
try{const f=evaluer(extraire("function DzQuickVoice("),"DzQuickVoice");const t=f({});OUT.voix={ok:true,texte:texte(t)}}
catch(e){OUT.voix={ok:false,err:String(e&&e.message||e)}}
// [C] DzQuickGarde
try{const src=extraire("class DzQuickGarde ");const G=evaluer(src,"DzQuickGarde");const fils=el("div",{children:"enfant"});
 let retour=0;const g=new G({onglet:"voice",retour:()=>{retour++},children:fils});
 OUT.garde={sans:g.render()===fils};const st=G.getDerivedStateFromError(new Error("boum"));g.state=Object.assign({},g.state,st);
 const vue=g.render();OUT.garde.alerte=vue&&vue.p&&vue.p.role==="alert";OUT.garde.texte=texte(vue);
 const boutons=[];(function marche(n){if(!n||typeof n!=="object")return;if(Array.isArray(n))return n.forEach(marche);
  if(n.t==="button")boutons.push(n);marche(n.p&&n.p.children)})(vue);
 OUT.garde.nb=boutons.length;boutons[1]&&boutons[1].p.onClick();OUT.garde.retour=retour;
 boutons[0]&&boutons[0].p.onClick();OUT.garde.efface=g.state.err==null&&g.render()===fils;
 const g2=new G({onglet:"seedance",retour(){},children:fils});g2.state={err:new Error("x")};
 OUT.garde.nbSeedance=(function(){const b=[];(function m(n){if(!n||typeof n!=="object")return;if(Array.isArray(n))return n.forEach(m);
  if(n.t==="button")b.push(n);m(n.p&&n.p.children)})(g2.render());return b.length})();
 const g3=new G({onglet:"seedance",ecran:true,children:fils});g3.state={err:new Error("z")};OUT.garde.ecran=texte(g3.render());
 try{g.componentDidCatch(new Error("y"),{componentStack:""});OUT.garde.catch=true}catch(e){OUT.garde.catch=false}}
catch(e){OUT.garde={err:String(e&&e.message||e)}}
process.stdout.write(JSON.stringify(OUT));
"""


def node(bundle_texte):
    with tempfile.TemporaryDirectory() as td:
        b = pathlib.Path(td) / "b.js"; b.write_text(bundle_texte, encoding="utf-8")
        h = pathlib.Path(td) / "h.js"; h.write_text(HARNAIS, encoding="utf-8")
        rn = subprocess.run(["node", str(h), str(b)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return json.loads(rn.stdout)
    except ValueError:
        return {"_err": rn.stderr[-400:]}


print("[B] DzQuickVoice se rend sous node")
OUT = node(BUNDLE)
V = OUT.get("voix") or {}
check("B0 témoin : la base lève « dzT is not a function »",
      "dzT is not a function" in str((node(r0.stdout.decode("utf-8")).get("voix") or {}).get("err")))
check("B1 premier rendu sans erreur", V.get("ok") is True, str(V.get("err") or OUT.get("_err")))
for cle in ("quick.voix.titre", "quick.langue.titre", "quick.voix.texte_aide"):
    check(f"B2 {cle} traduit à l'écran", f"⟦{cle}⟧" in (V.get("texte") or ""))

def corps(s, debut):
    """Une fonction du bundle, accolades appariées (chaînes sautées), comme le harnais node."""
    a = s.find(debut)
    if a < 0:
        return ""
    i, d, q = s.find("{", a), 0, None
    while i < len(s):
        c = s[i]
        if q:
            if c == "\\":
                i += 2
                continue
            if c == q:
                q = None
        elif c in "\"'`":
            q = c
        elif c == "{":
            d += 1
        elif c == "}":
            d -= 1
            if not d:
                break
        i += 1
    return s[a:i + 1]


SEG = corps(BUNDLE, "function DzQuickVoice(")
nus = [SEG[max(0, m.start() - 30):m.end() + 10] for m in re.finditer(r"(?<![\w$.])dzT\b(?!\s*\()", SEG)]
check("B3 dans DzQuickVoice, dzT n'est plus qu'un appel (aucune valeur dzT : tune, settings, value)",
      SEG.count("dzTu") == 6 and nus == [], repr(nus[:3]))

print("[C] la garde d'onglet")
G = OUT.get("garde") or {}
check("C1 sans erreur : les enfants passent tels quels", G.get("sans") is True, str(G))
check("C2 une erreur : encart role=alert, titre traduit, message de l'erreur",
      G.get("alerte") is True and "⟦quick.garde.titre⟧" in (G.get("texte") or "") and "boum" in (G.get("texte") or ""))
check("C3 deux boutons hors Seedance (Réessayer, Revenir à Seedance), un seul sur Seedance",
      G.get("nb") == 2 and G.get("nbSeedance") == 1
      and "⟦quick.garde.reessayer⟧" in (G.get("texte") or "") and "⟦quick.garde.retour⟧" in (G.get("texte") or ""))
check("C4 « Revenir à Seedance » appelle retour", G.get("retour") == 1)
check("C5 « Réessayer » efface l'erreur et rend les enfants", G.get("efface") is True)
check("C6 componentDidCatch ne lève pas", G.get("catch") is True)
check("C7 la garde d'écran a son propre titre", "⟦quick.garde.ecran⟧" in (G.get("ecran") or "")
      and "⟦quick.garde.titre⟧" not in (G.get("ecran") or ""), str(G.get("ecran")))

print("[D] câblage dans Quick")
OUV = 'children:r.jsx(DzQuickGarde,{onglet:o,retour:function(){i("seedance")},children:o==="voice"?[dzQpUI(),r.jsx(DzQuickVoice,{},"dzqv")]:['
FER = 'dzT("quick.prompt.ouvrir_generateur")})]})]})]},"dzqg-"+o)}),o!=="voice"&&r.jsxs("div",{style:{padding:14,'
check("D1 le contenu défilant est ouvert par la garde (onglet, retour vers seedance)", BUNDLE.count(OUV) == 1)
check("D2 et refermé avec une clé par onglet", BUNDLE.count(FER) == 1)
k = BUNDLE.find(OUV)
check("D3 la garde est dans le défilant de Quick (um)",
      k > 0 and BUNDLE.rfind("function um(", 0, k) > BUNDLE.rfind("function DzQuickStage(", 0, k))
check("D4 une seconde garde enveloppe l'écran Quick entier dans le shell (le rail reste utilisable)",
      BUNDLE.count('s==="quick"&&r.jsx(DzQuickGarde,{onglet:"seedance",children:r.jsx(um,{variant:e,'
                   'activePersona:z.find(F=>F.id===P)})},"dzqg-ecran")'.replace('onglet:"seedance",', 'onglet:"seedance",ecran:!0,')) == 1
      and BUNDLE.count("r.jsx(um,{") == 1)

print("[E] maillon de queue dzquick")
import patch_bundle_dzquick as DQ                                    # noqa: E402
import _i18n_l1_aide as AIDE                                          # noqa: E402
check("E1 marqueur posé une fois", BUNDLE.count(DQ.MARKER) == DQ.MARKER_ATTENDU == 1)
try:
    avant = DQ.defaire(BUNDLE)
    DQ.appliquer(avant)
except (AssertionError, SystemExit) as e:
    avant = str(e)
check("E2 inverse exact : aller-retour à l'octet", DQ.MARKER not in avant and DQ.appliquer(avant) == BUNDLE)
check("E3 l'inverse rend le défaut d'avant (dzT=dztS[0])", "dzT=dztS[0]," in avant)
check("E4 avant_dzquick = inverse du maillon", AIDE.avant_dzquick(BUNDLE) == avant)
src_aide = (_ICI / "_i18n_l1_aide.py").read_text(encoding="utf-8")
j = src_aide.find("def avant_dzespace(")
check("E5 avant_dzquick appelé EN TÊTE d'avant_dzespace",
      j > 0 and "bundle = avant_dzquick(bundle)" in src_aide[j:src_aide.find("import patch_bundle_dzespace", j)])
check("E6 avant_dzespace(bundle) == avant_dzespace(avant_dzquick(bundle))",
      AIDE.avant_dzespace(BUNDLE) == AIDE.avant_dzespace(avant))
check("E7 aucun .bak_dzquick laissé", not BUN_P.with_name(BUN_P.name + ".bak_dzquick").exists())
check("E8 comptes figés : useState 731, v2.8.0 ×4, DzTracks 181",
      BUNDLE.count("x.useState(") == 731 and BUNDLE.count("v2.8.0") == 4 and BUNDLE.count("DzTracks") == 181)
src_dq = (RACINE / "scripts" / "patch_bundle_dzquick.py").read_text(encoding="utf-8")
check("E9 sonde amont sur dzespace, lecture/écriture en octets",
      '("dzespace", "function DzEspaceSel(", 1)' in src_dq and "read_bytes()" in src_dq and "read_text(" not in src_dq)

print("[F] clés FR/EN")
# quick.json appartient au générateur L2 : les clés du lot « Menus » vivent dans menus.json
Q = json.loads((RACINE / "frontend" / "shared" / "i18n" / "menus.json").read_text(encoding="utf-8"))
ATT = {"quick.garde.titre": ("Cet onglet a rencontré une erreur.", "This tab ran into an error."),
       "quick.garde.reessayer": ("Réessayer", "Retry"),
       "quick.garde.ecran": ("L’écran Quick a rencontré une erreur.", "The Quick screen ran into an error."),
       "quick.garde.retour": ("Revenir à Seedance", "Back to Seedance")}
for cle, (fr, en) in ATT.items():
    check(f"F1 {cle}", Q.get(cle) == {"fr": fr, "en": en}, str(Q.get(cle)))
ra = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", cwd=str(RACINE), env=_ENV)
check("F2 catalogue assemblé à jour", ra.returncode == 0, ra.stdout[-200:] + ra.stderr[-200:])

print("[G] Montage : l'aperçu vivant ne masque plus dzT")
SRC = (RACINE / "frontend" / "patches" / "son-vfx-montage.js").read_text(encoding="utf-8")
check("G1 la source sonvfx n'a plus de déclaration dzT (renommée dzZ, même longueur : positions G1 intactes)",
      declarations(SRC) == [] and "var dzZ=DzTracks.dzCss(" in SRC
      and "if(lv.style.transform!==dzZ)lv.style.transform=dzZ;" in SRC)
rl = subprocess.run([sys.executable, str(RACINE / "scripts" / "refresh_layer.py"), "--layer", "sonvfx", "--check"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(RACINE), env=_ENV)
check("G2 bloc SONVFX du bundle = sa source (refresh_layer --check)", rl.returncode == 0, (rl.stdout + rl.stderr)[-300:])
for gen in ("i18n_l4_generer.py", "i18n_l2_generer.py", "icones/g1_generer.py"):
    rg = subprocess.run([sys.executable, str(RACINE / "scripts" / gen), "--check"], capture_output=True, text=True,
                        encoding="utf-8", errors="replace", cwd=str(RACINE), env=_ENV)
    check(f"G3 {gen} --check à jour (la retouche est consignée : L4 montage_a, RETOUCHES de G1)",
          rg.returncode == 0, (rg.stdout + rg.stderr)[-200:])

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
