# -*- coding: utf-8 -*-
"""t213 (Menus : Quick, 15/10/2026) — la barre d'onglets de Quick débordait de sa colonne de 360 px.

Quatre onglets en `flex:1` avec icône ET libellé (« Seedance », « HeyGen », « Composition », « Voix off » / « Voiceover »)
ne tenaient pas dans les 328 px utiles : « Composition » et « Voiced… » étaient coupés. DÉCISION DE L'UTILISATEUR
(15/10) : icônes seules, bulle au survol ; l'onglet ACTIF garde son libellé, en ellipse. Le volet étirable est écarté.

Ce que ce banc garde :
  [A] le tableau des onglets, extrait du bundle et rendu sous node (hooks absents : `o` = onglet actif, `i` = setter,
      `X` = icône factice, dzT factice) : chaque bouton porte `title` et `aria-label` = libellé (la bulle « désactivé —
      clé requise » reste celle des onglets sans clé) ; le libellé est rendu SEULEMENT dans l'onglet actif, dans un
      span en ellipse ; témoin : la base dd64488d rend les quatre libellés ;
  [B] styles anti-débordement : inactif `flex:"0 0 auto"`, actif `flex:1`, `minWidth:0`, `overflow:hidden`,
      `textOverflow:"ellipsis"`, `whiteSpace:"nowrap"` ; l'icône ne rétrécit pas ; la largeur minimale cumulée de la
      barre (onglets inactifs + actif réduit à son icône + écarts) tient dans 328 px, pour chaque onglet actif ;
  [C] « Composition » passe par dzT (`quick.onglet.composition`, FR « Composition », EN « Compositing », comme
      `avatar.job.merging`) ; clé dans menus.json (quick.json appartient au générateur L2), catalogue assemblé à jour ;
  [D] maillon de queue `dzquick` : paires t213 ×1, inverse exact, `avant_dzquick` rend le tableau d'avant ; comptes
      figés intacts (useState 731, v2.8.0 ×4, DzTracks 181).
Run (depuis backend/) : & $PY tests/test_quick_onglets.py"""
import json, os, pathlib, subprocess, sys, tempfile
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


BUN_P = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BUNDLE = BUN_P.read_bytes().decode("utf-8")
BASE = "dd64488d"
DEBUT = '[["seedance","Seedance","dz-media-generer-video",Za],'
FIN = '},B))'

# Le tableau des onglets, évalué pour chaque onglet actif ; `Za`/`_n` = clé absente (onglet désactivé).
HARNAIS = r"""
const fs=require("fs");const expr=fs.readFileSync(process.argv[2],"utf8");
const el=(t,p,k)=>({t:typeof t==="string"?t:(t&&t.name)||"?",p:p||{},k});const r={jsx:el,jsxs:el};
function X(){}const dzT=(k,v)=>"⟦"+k+(v?":"+JSON.stringify(v):"")+"⟧";
const OUT={};
for(const o of ["seedance","heygen","comp","voice"]){for(const cle of [true,false]){
 const Za=!cle,_n=!cle,i=()=>{};
 try{OUT[o+(cle?"":"-sans")]=eval(expr)}catch(e){OUT[o+(cle?"":"-sans")]={err:String(e)}}}}
process.stdout.write(JSON.stringify(OUT));
"""


def rendre(bundle):
    a = bundle.find(DEBUT)
    if a < 0:
        return {"err": "tableau introuvable"}
    b = bundle.find(FIN, a)
    expr = bundle[a:b + len(FIN)]
    with tempfile.TemporaryDirectory() as d:
        h = pathlib.Path(d) / "h.js"; h.write_text(HARNAIS, encoding="utf-8")
        e = pathlib.Path(d) / "e.js"; e.write_text(expr, encoding="utf-8")
        rn = subprocess.run(["node", str(h), str(e)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return json.loads(rn.stdout)
    except ValueError:
        return {"err": rn.stderr[-400:]}


def textes(n):
    """Les textes rendus dans un nœud (chaînes des children, récursivement)."""
    if isinstance(n, str):
        return [n]
    if isinstance(n, list):
        return [t for c in n for t in textes(c)]
    if isinstance(n, dict) and "p" in n:
        return textes(n["p"].get("children"))
    return []


LIB = {"seedance": "Seedance", "heygen": "HeyGen", "comp": "⟦quick.onglet.composition⟧", "voice": "⟦quick.onglet.voix_off⟧"}

print("[A] libellés : bulle et aria-label partout, visibles seulement sur l'actif")
r0 = subprocess.run(["git", "show", f"{BASE}:frontend/dist/assets/index-BEOJX8L5.js"], capture_output=True, cwd=str(RACINE))
T0 = rendre(r0.stdout.decode("utf-8")) if r0.returncode == 0 else {}
t0 = T0.get("comp") or []
check("A0 témoin : la base dd64488d rend les quatre libellés (Composition en dur)",
      isinstance(t0, list) and len(t0) == 4 and all(len(textes(b)) == 1 for b in t0) and "Composition" in textes(t0[2]))
T = rendre(BUNDLE)
check("A1 le tableau se rend pour chaque onglet actif, avec et sans clé", "err" not in T and all(
    isinstance(T.get(o), list) and len(T[o]) == 4 for o in [k + s for k in LIB for s in ("", "-sans")]), str(T)[:300])
ids = list(LIB)
a2 = a3 = a4 = a5 = True
for actif in ids:
    for b, oid in zip(T.get(actif) or [], ids):
        p = b.get("p", {})
        a2 &= p.get("aria-label") == LIB[oid] and p.get("title") == LIB[oid]
        tx = textes(b)
        a3 &= (tx == [LIB[oid]]) if oid == actif else (tx == [])
    for b, oid in zip(T.get(actif + "-sans") or [], ids):
        p = b.get("p", {})
        if oid in ("seedance", "heygen", "comp"):
            a4 &= p.get("disabled") is True and p.get("title") == "⟦quick.onglet.desactive:" + json.dumps({"nom": LIB[oid]}, ensure_ascii=False, separators=(",", ":")) + "⟧"
        a5 &= p.get("aria-label") == LIB[oid]
check("A2 chaque bouton : title = aria-label = libellé", a2)
check("A3 libellé rendu SEULEMENT dans l'onglet actif", a3)
check("A4 sans clé : bulle « désactivé — clé requise » gardée", a4)
check("A5 sans clé : aria-label = libellé", a5)
span = [c for c in (T.get("comp") or [{}])[2].get("p", {}).get("children", []) if isinstance(c, dict) and c.get("t") == "span"]
sst = span[0]["p"].get("style", {}) if span else {}
check("A6 le libellé actif est un span en ellipse", bool(span) and sst.get("textOverflow") == "ellipsis"
      and sst.get("overflow") == "hidden" and sst.get("whiteSpace") == "nowrap" and sst.get("minWidth") == 0)

print("[B] styles anti-débordement")
b1 = b2 = b3 = True
LARGEUR_UTILE = 328
largeurs = {}
for actif in ids:
    tot = 0
    for b, oid in zip(T.get(actif) or [], ids):
        st = b.get("p", {}).get("style", {})
        b1 &= st.get("flex") == (1 if oid == actif else "0 0 auto")
        b2 &= st.get("minWidth") == 0 and st.get("overflow") == "hidden" and st.get("textOverflow") == "ellipsis" \
            and st.get("whiteSpace") == "nowrap"
        ico = [c for c in b["p"].get("children", []) if isinstance(c, dict) and c.get("t") == "X"]
        b3 &= bool(ico) and (ico[0]["p"].get("style") or {}).get("flexShrink") == 0
        pad = st.get("padding", "")
        ph = int(pad.split()[1].rstrip("px")) if len(pad.split()) == 2 else 99
        tot += 2 * ph + 2 + (ico[0]["p"].get("size", 99) if ico else 99)       # padding + bordure + icône
        if oid != actif:                                                       # un inactif ne rétrécit pas : son texte
            tot += sum(6 + 7 * len(t) for t in textes(b))                      # compte (écart 6 + ~7 px par signe)
    largeurs[actif] = tot + 3 * 4 + 2 * 3 + 2                                     # écarts, padding et bordure de la barre
check("B1 inactif flex:\"0 0 auto\", actif flex:1", b1)
check("B2 minWidth 0, overflow hidden, ellipsis, nowrap sur chaque bouton", b2)
check("B3 l'icône ne rétrécit pas (flexShrink 0)", b3)
check(f"B4 largeur minimale cumulée ≤ {LARGEUR_UTILE} px pour chaque onglet actif",
      largeurs and all(v <= LARGEUR_UTILE for v in largeurs.values()), repr(largeurs))

print("[C] « Composition » traduit")
cat = json.loads((RACINE / "frontend" / "shared" / "i18n" / "menus.json").read_text(encoding="utf-8"))
check("C1 clé quick.onglet.composition FR « Composition », EN « Compositing »",
      cat.get("quick.onglet.composition") == {"fr": "Composition", "en": "Compositing"})
av = json.loads((RACINE / "frontend" / "shared" / "i18n" / "avatar.json").read_text(encoding="utf-8"))
check("C2 même traduction que avatar.job.merging", av.get("avatar.job.merging", {}).get("en") == "Compositing")
quick = json.loads((RACINE / "frontend" / "shared" / "i18n" / "quick.json").read_text(encoding="utf-8"))
check("C3 absente de quick.json (générateur L2)", "quick.onglet.composition" not in quick)
check("C4 plus de « Composition » en dur dans le tableau", '["comp","Composition",' not in BUNDLE
      and '["comp",dzT("quick.onglet.composition"),' in BUNDLE)
ra = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", cwd=str(RACINE), env=dict(os.environ, PYTHONIOENCODING="utf-8"))
check("C5 catalogue assemblé à jour (i18n_assembler --check)", ra.returncode == 0, (ra.stdout + ra.stderr)[-300:])

print("[D] maillon de queue dzquick")
import patch_bundle_dzquick as DQ                                    # noqa: E402
import _i18n_l1_aide as AIDE                                          # noqa: E402
t213 = [p for p in DQ.PAIRES if "quick.onglet.composition" in p[1] or "aria-label" in p[1]]
check("D1 deux paires t213 dans le maillon", len(t213) == 2)
check("D2 chaque remplacement t213 ×1 dans le bundle", len(t213) == 2 and all(BUNDLE.count(p[1]) == 1 for p in t213))
try:
    avant = DQ.defaire(BUNDLE)
except AssertionError as e:
    avant = str(e)


def _rejoue(s):
    try:
        return DQ.appliquer(s)
    except SystemExit as e:
        return str(e)
check("D3 inverse exact : aller-retour à l'octet", DQ.MARKER not in avant and _rejoue(avant) == BUNDLE)
try:
    avant_aide = AIDE.avant_dzquick(BUNDLE)
except AssertionError as e:
    avant_aide = str(e)
check("D4 avant_dzquick rend le tableau d'avant", len(t213) == 2 and avant_aide == AIDE.avant_dzreglages(avant)
      and '["comp","Composition","dz-cat-composition",' in avant and '"aria-label":Z' not in avant)
check("D5 comptes figés intacts", BUNDLE.count("x.useState(") == 731 and BUNDLE.count("v2.8.0") == 4
      and BUNDLE.count("DzTracks") == 181)
check("D6 aucun .bak_dzquick laissé", not (BUN_P.parent / (BUN_P.name + ".bak_dzquick")).exists())

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
