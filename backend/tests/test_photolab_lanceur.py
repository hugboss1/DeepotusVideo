# -*- coding: utf-8 -*-
"""t137 (07/10/2026) — l'entrée « Photolab » de la barre des applications
(scripts/patch_bundle_photolab.py, plan docs/superpowers/plans/2026-10-07-photolab-p2-ecran.md, Task D1).

  [1] le maillon : lecture en octets, parité de ses deltas, et REJEU — appliqué au bundle de main d'avant t137
      (BASE) dans un dossier temporaire, avec les fins de ligne du poste, il rend EXACTEMENT le bundle de référence ;
      un second passage est refusé (« double application ») ; aucun .bak laissé.
  [2] le bundle : chaque section une fois (icône, entrée de rail APRÈS vectorlab, vue iframe `/photolab/`, vue
      navigable dans `Yu`), compteurs figés des maillons aval intacts (`x.useState(` 731, `DzTracks` 181), CRLF
      intacts, `node --check` (script et module).
  [3] sous node : la carte des icônes `Sh` extraite du bundle et exécutée avec un jsx minimal — `Sh.photolab` existe
      et rend un `<g fill="currentColor">` ; le rail rend l'entrée Photolab juste après Vectorlab.
Run : & $PY tests/test_photolab_lanceur.py   (depuis backend/)
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
HERE = pathlib.Path(__file__).resolve().parent
RACINE = HERE.parent.parent
BASE = "73c9cfe2"                      # main juste avant t137 (fusion #263, bundle de t134 368f29ea, sans Photolab)
# le bundle de référence : tant que t137 n'est pas commis, le bundle du poste ; une fois commis, épingler ici le
# commit de t137 (comme T125 dans test_assets2d_lanceur) — sinon la couche suivante qui bouge le bundle rougit [1c]
T137 = "db72da5b"   # commit t137 : le bundle de reference (comme T125 pour assets2d)
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


SCRIPT = RACINE / "scripts" / "patch_bundle_photolab.py"
SRC = SCRIPT.read_bytes().decode("utf-8") if SCRIPT.is_file() else ""
BUNB = (RACINE / REL).read_bytes()
BUN = BUNB.decode("utf-8")

ENTREE_VL = '{id:"vectorlab",label:"Vectorlab",icon:"vectorpen",desc:"Éditeur vectoriel & vitrail",new:!0},'
ENTREE_PL = '{id:"photolab",label:"Photolab",icon:"photolab",desc:"Retouche d\'image & calques",new:!0},'
VUE_PL = ('s==="photolab"&&r.jsx("iframe",{src:"/photolab/",title:"Photolab",style:{position:"absolute",inset:0,'
          'width:"100%",height:"100%",border:"0",background:"var(--bg-base)"}},"pplab"),')

print("\n[1] le maillon")
check("1a_lecture_et_ecriture_en_octets", bool(SRC) and "read_text(" not in SRC and "write_text(" not in SRC
      and "read_bytes()" in SRC, len(SRC))
sys.path.insert(0, str(RACINE / "scripts"))
try:
    import patch_bundle_photolab as P
except Exception as e:                       # le banc rougit, ne meurt pas
    P = None
    print(f"  (import du maillon impossible : {e!r})")
check("1b_parite_des_deltas", P is not None and P.deltas() == (P.SPEC_CHAR_DELTA, P.SPEC_BYTE_DELTA),
      P and P.deltas())
base = subprocess.run(["git", "show", f"{BASE}:{REL}"], cwd=str(RACINE), capture_output=True).stdout
eol = b"\r\n" if BUNB.count(b"\r\n") == BUNB.count(b"\n") else b"\n"
if T137:
    reference = subprocess.run(["git", "show", f"{T137}:{REL}"], cwd=str(RACINE), capture_output=True).stdout
else:
    reference = BUNB
reference = reference.replace(b"\r\n", b"\n").replace(b"\n", eol)
TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzpl_"))
try:
    (TMP / "frontend/dist/assets").mkdir(parents=True)
    # le bundle de BASE tel que le poste de travail le porte (CRLF, comme le bundle commis ici)
    (TMP / REL).write_bytes(base.replace(b"\r\n", b"\n").replace(b"\n", eol))
    PY = sys.executable
    r1 = subprocess.run([PY, str(SCRIPT)], cwd=str(TMP), capture_output=True, text=True, encoding="utf-8",
                        errors="replace")
    rejoue = (TMP / REL).read_bytes()
    check("1c_rejeu_sur_le_bundle_de_main_rend_le_bundle_de_reference_octet_pour_octet",
          len(base) > 1_000_000 and len(reference) > 1_000_000 and r1.returncode == 0 and rejoue == reference,
          (r1.returncode, (r1.stdout + r1.stderr)[-300:], len(rejoue), len(reference)))
    check("1e_aucun_bak_laisse_apres_application",
          r1.returncode == 0 and not list((TMP / "frontend/dist/assets").glob("*.bak_*")),
          [p.name for p in (TMP / "frontend/dist/assets").glob("*.bak_*")])
    r2 = subprocess.run([PY, str(SCRIPT)], cwd=str(TMP), capture_output=True, text=True, encoding="utf-8",
                        errors="replace")
    check("1d_second_passage_refuse_double_application", r1.returncode == 0 and r2.returncode != 0
          and "double application" in (r2.stdout + r2.stderr) and (TMP / REL).read_bytes() == rejoue,
          (r2.returncode, (r2.stdout + r2.stderr)[-200:]))
    r3 = subprocess.run([PY, str(SCRIPT), "--check"], cwd=str(TMP), capture_output=True, text=True,
                        encoding="utf-8", errors="replace")
    check("1f_check_refuse_aussi_sur_un_bundle_deja_patche", r3.returncode != 0
          and "double application" in (r3.stdout + r3.stderr), (r3.returncode, (r3.stdout + r3.stderr)[-200:]))
finally:
    shutil.rmtree(TMP, ignore_errors=True)
check("1g_aucun_bak_photolab_dans_le_depot", not (RACINE / (REL + ".bak_photolab")).exists())

print("\n[2] le bundle")
check("2a_icone_photolab_une_fois_avant_gamegrid",
      BUN.count('photolab:r.jsxs("g",{fill:"currentColor",children:[') == 1
      and 0 < BUN.find("photolab:r.jsxs(") < BUN.find('gamegrid:r.jsxs("g",{fill:"currentColor",children:['))
check("2b_entree_de_rail_juste_apres_vectorlab", BUN.count(ENTREE_PL) == 1 and BUN.count(ENTREE_VL + ENTREE_PL) == 1)
check("2c_vue_iframe_photolab_apres_la_vue_vectorlab",
      BUN.count(VUE_PL) == 1 and BUN.count('"pvlab"),' + VUE_PL) == 1 and BUN.count('src:"/photolab/"') == 1)
check("2d_photolab_est_une_vue_navigable",
      BUN.count('"news","library","settings","vectorlab","photolab"],sg=Yu.includes(') == 1)
check("2e_compteurs_des_maillons_aval_intacts", BUN.count("x.useState(") == 731 and BUN.count("DzTracks") == 181,
      (BUN.count("x.useState("), BUN.count("DzTracks")))
check("2f_fins_de_ligne_intactes_en_octets", BUNB.count(b"\r\n") > 15000 and BUNB.count(b"\r\n") == BUNB.count(b"\n"),
      (BUNB.count(b"\r\n"), BUNB.count(b"\n")))
check("2g_icone_en_currentColor_sans_couleur_en_dur", (lambda s: "#" not in s and "rgb" not in s and "oklch" not in s
      and 'fillRule:"evenodd"' in s and 'opacity:".32"' in s)(
          BUN[BUN.find("photolab:r.jsxs("):BUN.find("gamegrid:r.jsxs(")]))
if NODE:
    r = subprocess.run([NODE, "--check", str(RACINE / REL)], capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    check("2h_node_check_script", r.returncode == 0, (r.stderr or "")[-300:])
    with (RACINE / REL).open("rb") as fh:
        r = subprocess.run([NODE, "--input-type=module", "--check"], stdin=fh, capture_output=True)
    check("2i_node_check_module", r.returncode == 0, (r.stderr or b"")[-300:])
else:
    check("2h_node_present", False, "node absent du PATH")

print("\n[3] sous node")
i0 = BUN.find("Sh={")
i1 = BUN.find("};function X(", i0) + 1 if i0 > 0 else -1
carte = BUN[i0:i1] if 0 < i0 < i1 else ""
# le tableau du rail : celui qui se termine par l'entrée Settings
k1 = BUN.find('{id:"settings",label:"Settings",icon:"cog",desc:"Keys, paths, persona"}]')
k0 = BUN.rfind("=[", 0, k1)
rail = BUN[k0 + 1:k1 + len('{id:"settings",label:"Settings",icon:"cog",desc:"Keys, paths, persona"}]')] \
    if 0 < k0 < k1 else ""
PROBE = r"""
"use strict";
var r={jsx:function(t,p,k){return {t:t,p:p,k:k}},jsxs:function(t,p,k){return {t:t,p:p,k:k}}};
var __CARTE__;
var RAIL=__RAIL__;
var g=Sh.photolab;
function kids(n){var c=n&&n.p&&n.p.children;return c==null?[]:(Array.isArray(c)?c:[c])}
var ids=RAIL.map(function(e){return e.id});
var pl=RAIL.filter(function(e){return e.id==="photolab"})[0]||null;
console.log(JSON.stringify({existe:!!g,tag:g&&g.t,fill:g&&g.p&&g.p.fill,enfants:kids(g).map(function(n){return [n.t,
  n.p.fillRule||null,n.p.opacity||null]}),ids:ids,pl:pl,icones:ids.every(function(i){
  var e=RAIL.filter(function(x){return x.id===i})[0];return !!Sh[e.icon]})}));
"""
D = {}
if NODE and carte and rail:
    p = pathlib.Path(tempfile.mkdtemp(prefix="dzpln_")) / "pl.js"
    p.write_text(PROBE.replace("__CARTE__", carte).replace("__RAIL__", rail), encoding="utf-8")
    rn = subprocess.run([NODE, str(p)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        D = json.loads((rn.stdout or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        print("  (node :", (rn.stderr or rn.stdout)[-400:], ")")
    shutil.rmtree(p.parent, ignore_errors=True)
check("3a_la_carte_des_icones_et_le_rail_s_executent_sous_node", bool(D), (bool(NODE), len(carte), len(rail)))
if D:
    check("3b_Sh_photolab_rend_un_g_en_currentColor", D["existe"] and D.get("tag") == "g" and D.get("fill") == "currentColor",
          (D["existe"], D.get("tag"), D.get("fill")))
    check("3c_anneau_evenodd_lames_et_ouverture_en_support",
          D["enfants"] == [["path", "evenodd", None], ["path", None, None], ["path", None, ".32"]], D["enfants"])
    check("3d_photolab_juste_apres_vectorlab_et_avant_settings",
          "photolab" in D["ids"] and D["ids"][D["ids"].index("photolab") - 1] == "vectorlab"
          and D["ids"][-1] == "settings" and D["ids"].count("photolab") == 1, D["ids"])
    check("3e_entree_photolab_complete", D["pl"] == {"id": "photolab", "label": "Photolab", "icon": "photolab",
          "desc": "Retouche d'image & calques", "new": True}, D["pl"])
    check("3f_chaque_entree_du_rail_a_son_icone", D["icones"] is True)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
