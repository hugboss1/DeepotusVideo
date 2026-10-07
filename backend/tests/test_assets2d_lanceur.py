# -*- coding: utf-8 -*-
"""t125 (07/10/2026) — la carte-lanceur « Assets 2D » du hub Game Assets
(scripts/patch_bundle_assets2d.py, spec 2026-09-19-sorceress-sprite-suite-design.md, ligne « Lanceur »).

  [1] le maillon : lecture en octets, parité de ses deltas, et REJEU — appliqué au bundle de main d'avant t125
      (BASE) dans un dossier temporaire, il rend EXACTEMENT le bundle commis ; un second passage est refusé.
  [2] le bundle commis : l'onglet `a2d` (montage, relais, rangée, panneau), teintes et icônes, CRLF intacts.
  [3] sous node : `DzAssets2D` rendu avec un jsx minimal — quatre cartes dans l'ordre, « Ouvrir » bascule l'onglet
      (sprites / tiles / cards) ou, pour Pixel, pose la demande `dz_vl_persona` puis navigue vers le Vectorlab ;
      « Guide » : lien vers le chapitre c18 pour Card Forge, GRISÉ ailleurs (jamais absent).
Run : & $PY tests/test_assets2d_lanceur.py   (depuis backend/)
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
HERE = pathlib.Path(__file__).resolve().parent
RACINE = HERE.parent.parent
BASE = "c75e276b"                      # main juste avant t125 (bundle sans le lanceur)
REL = "frontend/dist/assets/index-BEOJX8L5.js"
NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


SRC = (RACINE / "scripts" / "patch_bundle_assets2d.py").read_bytes().decode("utf-8")
BUNB = (RACINE / REL).read_bytes()
BUN = BUNB.decode("utf-8")

print("\n[1] le maillon")
check("1a_lecture_et_ecriture_en_octets", "read_text(" not in SRC and "write_text(" not in SRC and "read_bytes()" in SRC)
sys.path.insert(0, str(RACINE / "scripts"))
try:
    import patch_bundle_assets2d as P
except Exception as e:                       # le banc rougit, ne meurt pas
    P = None
    print(f"  (import du maillon impossible : {e!r})")
check("1b_parite_des_deltas", P is not None and P.deltas() == (P.SPEC_CHAR_DELTA, P.SPEC_BYTE_DELTA) == (3407, 3424),
      P and P.deltas())
base = subprocess.run(["git", "show", f"{BASE}:{REL}"], cwd=str(RACINE), capture_output=True).stdout
TMP = pathlib.Path(tempfile.mkdtemp(prefix="dza2d_"))
try:
    (TMP / "frontend/dist/assets").mkdir(parents=True)
    # le bundle de BASE tel que le poste de travail le porte (CRLF, comme le bundle commis ici)
    eol = b"\r\n" if BUNB.count(b"\r\n") == BUNB.count(b"\n") else b"\n"
    (TMP / REL).write_bytes(base.replace(b"\r\n", b"\n").replace(b"\n", eol))
    PY = sys.executable
    r1 = subprocess.run([PY, str(RACINE / "scripts/patch_bundle_assets2d.py")], cwd=str(TMP), capture_output=True,
                        text=True, encoding="utf-8", errors="replace")
    rejoue = (TMP / REL).read_bytes()
    # t129 (07/10/2026) : la référence est FIGÉE — l'empreinte git (blob, forme LF) du bundle à la fusion de #255
    # (34d05288). Comparer au bundle COURANT rougissait au premier maillon posé après celui-ci.
    import hashlib
    lf = rejoue.replace(b"\r\n", b"\n")
    check("1c_rejeu_sur_le_bundle_de_main_rend_le_bundle_de_la_fusion_octet_pour_octet",
          len(base) > 1_000_000 and r1.returncode == 0
          and hashlib.sha1(b"blob %d\x00" % len(lf) + lf).hexdigest() == "870a5bcd6bf399285c6fcc58485b50f35f61f019",
          (r1.returncode, (r1.stdout + r1.stderr)[-300:], len(rejoue)))
    (TMP / (REL + ".bak_assets2d")).unlink(missing_ok=True)
    r2 = subprocess.run([PY, str(RACINE / "scripts/patch_bundle_assets2d.py")], cwd=str(TMP), capture_output=True,
                        text=True, encoding="utf-8", errors="replace")
    check("1d_second_passage_refuse_double_application", r1.returncode == 0 and r2.returncode != 0
          and "double application" in (r2.stdout + r2.stderr), (r2.returncode, (r2.stdout + r2.stderr)[-200:]))
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print("\n[2] le bundle commis")
check("2a_le_lanceur_est_defini_une_fois_avant_le_hub",
      BUN.count("function DzAssets2D(") == 1 and 0 < BUN.find("function DzAssets2D(") < BUN.find("function DzGameAssetsHub("))
check("2b_onglet_a2d_entre_3D_Studio_et_Sprites_2D",
      BUN.count('tb("studio3d","3D Studio"),tb("a2d","Assets 2D"),tb("sprites","Sprites 2D")') == 1)
check("2c_a2d_accepte_au_montage_et_par_le_relais",
      BUN.count('||t==="cards"||t==="a2d"?t:"3d"}') == 1 and BUN.count('||d.subtab==="cards"||d.subtab==="a2d")setTab(d.subtab)') == 1)
check("2d_le_panneau_monte_le_lanceur_avec_setTab",
      BUN.count(':tab==="a2d"?r.jsx(DzAssets2D,{go:setTab},"pa2"):tab==="sprites"?') == 1)
check("2e_teintes_et_icones_a2d_et_pixel",
      BUN.count('"a2d":"var(--cat-sprites)","pixel":"var(--cat-vectoriel)"') == 1 and BUN.count('var __dzCatSVG={"a2d":\'<svg') == 1)
check("2f_fins_de_ligne_intactes_en_octets", BUNB.count(b"\r\n") > 15000 and BUNB.count(b"\r\n") == BUNB.count(b"\n"),
      (BUNB.count(b"\r\n"), BUNB.count(b"\n")))
check("2h_la_rangee_d_onglets_a_sept_colonnes", BUN.count(".dzCatBar{display:grid;grid-template-columns:repeat(7,1fr);") == 1
      and BUN.count("repeat(6,1fr)") == 0)
check("2i_vectorlab_est_une_vue_navigable",
      BUN.count('"news","library","settings","vectorlab"],sg=Yu.includes(') == 1)
check("2j_le_libelle_Guide_seul_reste_celui_de_l_amont", BUN.count('"Guide"') == 1 and BUN.count('children:"Guide ↗"') == 2)
check("2g_aucun_dialogue_natif_dans_le_lanceur",
      all(t not in BUN[BUN.find("function DzAssets2D("):BUN.find("function DzGameAssetsHub(")] for t in ("alert(", "confirm(", "prompt(")))

print("\n[3] le lanceur sous node")
i0, i1 = BUN.find("function DzAssets2D("), BUN.find("function DzGameAssetsHub(")
fn = BUN[i0:i1] if 0 < i0 < i1 else ""
h0 = BUN.find("var __dzCatHue=")
# les deux tables (`__dzCatHue`, `__dzCatSVG`) : jusqu'au « }; » qui ferme la seconde
h1 = BUN.find("};", BUN.find("var __dzCatSVG=")) + 2 if h0 > 0 else -1
maps = BUN[h0:h1] if 0 < h0 < h1 else ""
PROBE = r"""
"use strict";
var EV=[],LS={};
var window={dispatchEvent:function(e){EV.push(e)}};
function CustomEvent(t,o){this.type=t;this.detail=o&&o.detail}
var localStorage={setItem:function(k,v){LS[k]=String(v)}};
function K(p){return {K:1,p:p}}
var r={jsx:function(t,p,k){return {t:t,p:p,k:k}},jsxs:function(t,p,k){return {t:t,p:p,k:k}}};
__MAPS__
__FN__
var GO=[],T=DzAssets2D({go:function(t){GO.push(t)}});
function kids(n){var c=n&&n.p&&n.p.children;return c==null?[]:(Array.isArray(c)?c:[c])}
function tous(n,acc){acc=acc||[];if(n&&typeof n==="object"){acc.push(n);kids(n).forEach(function(k){tous(k,acc)})}return acc}
var cartes=tous(T).filter(function(n){return n.p&&n.p.className==="dzA2dC"});
var out={ids:cartes.map(function(c){return c.p["data-outil"]}),titres:[],ouvrir:[],guides:[],teintes:[],vignettes:[]};
cartes.forEach(function(c){var ns=tous(c);
  out.titres.push(ns.filter(function(n){return n.k==="n"})[0].p.children);
  out.teintes.push(c.p.style["--cat"]);
  out.vignettes.push(ns.some(function(n){return n.p&&n.p.dangerouslySetInnerHTML&&/<svg/.test(n.p.dangerouslySetInnerHTML.__html)}));
  var o=ns.filter(function(n){return n.t===K&&n.p.children==="Ouvrir"})[0];
  var av=[GO.length,EV.length];o.p.onClick();out.ouvrir.push([GO.slice(av[0]),EV.slice(av[1]).map(function(e){return e.type+":"+(e.detail&&e.detail.view)})]);
  var g=ns.filter(function(n){return n.t===K&&n.p.children==="Guide ↗"})[0],a=ns.filter(function(n){return n.t==="a"})[0];
  out.guides.push([!!g,!!(g&&g.p.disabled),a?a.p.href:null,g?String(g.p.title||""):"",g&&g.p.disabled?(g.p.style||{}).opacity:null]);
});
out.ls=LS;
console.log(JSON.stringify(out));
"""
D = {}
if NODE and fn and maps:
    p = pathlib.Path(tempfile.mkdtemp(prefix="dza2dn_")) / "a2d.js"
    p.write_text(PROBE.replace("__MAPS__", maps).replace("__FN__", fn), encoding="utf-8")
    rn = subprocess.run([NODE, str(p)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        D = json.loads((rn.stdout or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        print("  (node :", (rn.stderr or rn.stdout)[-400:], ")")
    shutil.rmtree(p.parent, ignore_errors=True)
check("3a_le_lanceur_s_execute_sous_node", bool(D), (bool(NODE), len(fn), len(maps)))
if D:
    check("3b_quatre_cartes_dans_l_ordre", D["ids"] == ["sprites", "tiles", "pixel", "cards"]
          and D["titres"] == ["Sprite Lab", "Tile Lab", "Pixel — Vectorlab", "Card Forge"], (D["ids"], D["titres"]))
    check("3c_ouvrir_bascule_l_onglet_ou_navigue_vers_le_vectorlab",
          D["ouvrir"] == [[["sprites"], []], [["tiles"], []], [[], ["deepotus:navigate:vectorlab"]], [["cards"], []]], D["ouvrir"])
    check("3d_pixel_pose_la_demande_a_usage_unique", D["ls"] == {"dz_vl_persona": "pixel"}, D["ls"])
    check("3e_guide_lien_c18_pour_card_forge_grise_ailleurs_jamais_absent",
          [g[:3] for g in D["guides"]] == [[True, True, None], [True, True, None], [True, True, None],
                                          [True, False, "/guide/fr.html#c18"]]
          and all("Pas encore" in g[3] and g[4] == 0.45 for g in D["guides"][:3]), D["guides"])
    check("3f_chaque_carte_a_sa_teinte_et_sa_vignette",
          D["teintes"] == ["var(--cat-sprites)", "var(--cat-tuiles)", "var(--cat-vectoriel)", "var(--cat-cartes)"]
          and all(D["vignettes"]), (D["teintes"], D["vignettes"]))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
