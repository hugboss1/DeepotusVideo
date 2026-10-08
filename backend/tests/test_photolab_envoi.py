# -*- coding: utf-8 -*-
"""t139 (08/10/2026) — « Envoyer vers » le Photolab, le Vectorlab et le Tile Lab, et depuis le Photolab
(scripts/patch_bundle_plenvoi.py, plan docs/superpowers/plans/2026-10-08-photolab-p4-bibliotheque.md, B2).

  [1] le maillon : lecture en octets, parité de ses deltas, REJEU — appliqué au bundle de main d'avant t139 (BASE)
      dans un dossier temporaire, il rend EXACTEMENT le bundle de référence ; second passage refusé ; aucun .bak.
  [2] le bundle : chaque section une fois, `__dzSendTo` 2 -> 3, compteurs figés des maillons aval intacts
      (`x.useState(` 731, `DzTracks` 181), CRLF intacts, `node --check` (script et module).
  [3] sous node : le menu `__dzSendTo` EXTRAIT du bundle et exécuté (menu, navigation, toasts en doublures) — les trois
      cibles après « Sprite Lab — source », l'envoi posé puis la navigation ; pas de Photolab depuis le Photolab ; aucune
      de ces cibles pour un rendu ; `window.__dzEnvoyerVers` ouvre le même menu.
  [4] le contrat partagé : frontend/shared/dz-envoi.js servi à l'identique depuis frontend/dist/shared/.
Run : & $PY tests/test_photolab_envoi.py   (depuis backend/)
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
BASE = "85b93a00"                      # main juste avant t139 (fusion #265, t138)
# le bundle de référence : tant que t139 n'est pas commis, le bundle du poste ; une fois commis, épingler ici le
# commit de t139 (comme T137 dans test_photolab_lanceur) — sinon la couche suivante qui bouge le bundle rougit [1c]
T139 = ""
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
        print(f"  FAIL  {label} {str(detail)[:400]}")


SCRIPT = RACINE / "scripts" / "patch_bundle_plenvoi.py"
SRC = SCRIPT.read_bytes().decode("utf-8") if SCRIPT.is_file() else ""
BUNB = (RACINE / REL).read_bytes()
BUN = BUNB.decode("utf-8")

print("\n[1] le maillon")
check("1a_lecture_et_ecriture_en_octets", bool(SRC) and "read_text(" not in SRC and "write_text(" not in SRC
      and "read_bytes()" in SRC, len(SRC))
sys.path.insert(0, str(RACINE / "scripts"))
try:
    import patch_bundle_plenvoi as P
except Exception as e:                       # le banc rougit, ne meurt pas
    P = None
    print(f"  (import du maillon impossible : {e!r})")
check("1b_parite_des_deltas", P is not None and P.deltas() == (P.SPEC_CHAR_DELTA, P.SPEC_BYTE_DELTA),
      P and P.deltas())
base = subprocess.run(["git", "show", f"{BASE}:{REL}"], cwd=str(RACINE), capture_output=True).stdout
eol = b"\r\n" if BUNB.count(b"\r\n") == BUNB.count(b"\n") else b"\n"
if T139:
    reference = subprocess.run(["git", "show", f"{T139}:{REL}"], cwd=str(RACINE), capture_output=True).stdout
else:
    reference = BUNB
reference = reference.replace(b"\r\n", b"\n").replace(b"\n", eol)
TMP = pathlib.Path(tempfile.mkdtemp(prefix="dzple_"))
try:
    (TMP / "frontend/dist/assets").mkdir(parents=True)
    (TMP / REL).write_bytes(base.replace(b"\r\n", b"\n").replace(b"\n", eol))
    PY = sys.executable
    r1 = subprocess.run([PY, str(SCRIPT)], cwd=str(TMP), capture_output=True, text=True, encoding="utf-8",
                        errors="replace")
    rejoue = (TMP / REL).read_bytes()
    check("1c_rejeu_sur_le_bundle_de_main_rend_le_bundle_de_reference_octet_pour_octet",
          len(base) > 1_000_000 and len(reference) > 1_000_000 and r1.returncode == 0 and rejoue == reference,
          (r1.returncode, (r1.stdout + r1.stderr)[-300:], len(rejoue), len(reference)))
    check("1d_aucun_bak_laisse_apres_application",
          r1.returncode == 0 and not list((TMP / "frontend/dist/assets").glob("*.bak_*")),
          [p.name for p in (TMP / "frontend/dist/assets").glob("*.bak_*")])
    r2 = subprocess.run([PY, str(SCRIPT)], cwd=str(TMP), capture_output=True, text=True, encoding="utf-8",
                        errors="replace")
    check("1e_second_passage_refuse_double_application", r1.returncode == 0 and r2.returncode != 0
          and "double application" in (r2.stdout + r2.stderr) and (TMP / REL).read_bytes() == rejoue,
          (r2.returncode, (r2.stdout + r2.stderr)[-200:]))
    r3 = subprocess.run([PY, str(SCRIPT), "--check"], cwd=str(TMP), capture_output=True, text=True,
                        encoding="utf-8", errors="replace")
    check("1f_check_refuse_aussi_sur_un_bundle_deja_patche", r3.returncode != 0
          and "double application" in (r3.stdout + r3.stderr), (r3.returncode, (r3.stdout + r3.stderr)[-200:]))
finally:
    shutil.rmtree(TMP, ignore_errors=True)
check("1g_aucun_bak_plenvoi_dans_le_depot", not (RACINE / (REL + ".bak_plenvoi")).exists())

print("\n[2] le bundle")
check("2a_les_aides_une_fois_dans_la_portee_du_menu", BUN.count("function __dzEnvoi(") == 1
      and BUN.count("window.__dzEnvoyerVers=function(nom,de){") == 1
      and BUN.find("function __dzSendTo(") < BUN.find("function __dzEnvoi(") < BUN.find("function __dzToSpriteLab(src){"))
check("2b_les_trois_cibles_une_fois_juste_apres_sprite_lab_image",
      BUN.count('__dzToSpriteLab({kind:"image",filename:nom})}});if(m.de!=="photolab")items.push({lbl:"📷 Photolab') == 1
      and BUN.count('__dzEnvoi("vectorlab",nom);__dzSendNav("vectorlab")') == 1
      and BUN.count('__dzEnvoi("tilelab",nom);__dzSendNav("assets3d",{subtab:"tiles"})') == 1)
check("2c_jeton___dzSendTo_2_vers_3", BUN.count("__dzSendTo") == 3, BUN.count("__dzSendTo"))
check("2d_compteurs_des_maillons_aval_intacts", BUN.count("x.useState(") == 731 and BUN.count("DzTracks") == 181,
      (BUN.count("x.useState("), BUN.count("DzTracks")))
check("2e_fins_de_ligne_intactes_en_octets", BUNB.count(b"\r\n") > 15000 and BUNB.count(b"\r\n") == BUNB.count(b"\n"),
      (BUNB.count(b"\r\n"), BUNB.count(b"\n")))
if NODE:
    r = subprocess.run([NODE, "--check", str(RACINE / REL)], capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    check("2f_node_check_script", r.returncode == 0, (r.stderr or "")[-300:])
    with (RACINE / REL).open("rb") as fh:
        r = subprocess.run([NODE, "--input-type=module", "--check"], stdin=fh, capture_output=True)
    check("2g_node_check_module", r.returncode == 0, (r.stderr or b"")[-300:])
else:
    check("2f_node_present", False, "node absent du PATH")

print("\n[3] sous node : le menu extrait du bundle")
i0 = BUN.find("function __dzSendTo(")
i1 = BUN.find("function __dzToSpriteLab(src){")
MENU = BUN[i0:i1] if 0 < i0 < i1 else ""
HARNAIS = r"""
var window={},MENUS=[],NAV=[],ITEMS=null;
function __dzSendMenu(items,titre){ITEMS=items;MENUS.push({titre:titre,lbl:items.map(function(i){return i.lbl})})}
function __dzSendNav(v,extra){NAV.push([v,extra||null])}
function __dzToast(){}function __dzExtendClip(){}function __dzSendBible(){}function __dzToSpriteLab(){}function __dzSendSched(){}
function __dzPrint3d(){}function dzProjMenu(){}
function dzSendRecette(){return {lbl:"🍳 recette",fn:function(){}}}function dzSendStudioRendu(){return {lbl:"🎬 rendu",fn:function(){}}}
function choisir(lbl){var k=ITEMS.map(function(i){return i.lbl}).indexOf(lbl);if(k<0)return false;ITEMS[k].fn();return true}
var R={},ferme=0,ferm=function(){ferme++};
__dzSendTo({kind:"image",name:"a.png"},ferm);R.img=MENUS[0];
NAV=[];window.__dzEnvoiImg=null;R.chPl=choisir("📷 Photolab — retoucher l'image");R.envPl=window.__dzEnvoiImg;R.navPl=NAV;
NAV=[];window.__dzEnvoiImg=null;R.chVl=choisir("✒ Vectorlab — nouveau document avec l'image");R.envVl=window.__dzEnvoiImg;R.navVl=NAV;
NAV=[];window.__dzEnvoiImg=null;R.chTl=choisir("🧱 Tile Lab — source de la tuile");R.envTl=window.__dzEnvoiImg;R.navTl=NAV;R.ferme=ferme;
MENUS=[];__dzSendTo({kind:"image",name:"b.png",de:"photolab"},ferm);R.dePl=MENUS[0];
MENUS=[];__dzSendTo({kind:"render",jobId:"j1",name:"Rendu"},ferm);R.ren=MENUS[0];
MENUS=[];window.__dzEnvoyerVers("c.png","photolab");R.vers=MENUS[0];
NAV=[];window.__dzEnvoiImg=null;R.versCh=choisir("✒ Vectorlab — nouveau document avec l'image");R.versEnv=window.__dzEnvoiImg;
MENUS=[];window.__dzEnvoyerVers("d.png");R.versSans=MENUS[0];
console.log(JSON.stringify(R));
"""
D = {}
if NODE and MENU:
    p = pathlib.Path(tempfile.mkdtemp(prefix="dzplm_")) / "m.js"
    p.write_text(HARNAIS.split("var R={}")[0] + MENU + "\nvar R={}" + HARNAIS.split("var R={}")[1], encoding="utf-8")
    rn = subprocess.run([NODE, str(p)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        D = json.loads((rn.stdout or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        print("  (node :", (rn.stderr or rn.stdout)[-500:], ")")
    shutil.rmtree(p.parent, ignore_errors=True)
check("3a_le_menu_s_execute_sous_node", bool(D), (bool(NODE), len(MENU)))
if D:
    lbl = D["img"]["lbl"]
    k = lbl.index("🎮 Sprite Lab — source") if "🎮 Sprite Lab — source" in lbl else -9
    check("3b_image_les_trois_cibles_juste_apres_sprite_lab_dans_cet_ordre",
          lbl[k + 1:k + 4] == ["📷 Photolab — retoucher l'image", "✒ Vectorlab — nouveau document avec l'image",
                               "🧱 Tile Lab — source de la tuile"], lbl)
    check("3c_les_cibles_existantes_sont_toujours_la", all(x in lbl for x in (
        "🎬 Studio — nœud Image", "⚡ Quick — image de départ", "🎞 Montage — overlay à la tête de lecture",
        "🃏 Cardforge — copier img:… pour une illustration", "🎮 Sprite Lab — source")), lbl)
    for cle, cible, nav in (("Pl", "photolab", [["photolab", None]]), ("Vl", "vectorlab", [["vectorlab", None]]),
                            ("Tl", "tilelab", [["assets3d", {"subtab": "tiles"}]])):
        env = D.get("env" + cle) or {}
        check(f"3d_{cible}_pose_l_envoi_horodate_puis_navigue", D.get("ch" + cle) is True and env.get("cible") == cible
              and env.get("image") == "a.png" and isinstance(env.get("t"), (int, float)) and env["t"] > 1.7e12
              and D.get("nav" + cle) == nav, (env, D.get("nav" + cle)))
    check("3e_chaque_cible_ferme_le_modal_de_la_bibliotheque", D["ferme"] == 3, D["ferme"])
    check("3f_depuis_le_photolab_pas_de_cible_photolab_mais_vectorlab_et_tile_lab",
          "📷 Photolab — retoucher l'image" not in D["dePl"]["lbl"]
          and "✒ Vectorlab — nouveau document avec l'image" in D["dePl"]["lbl"]
          and "🧱 Tile Lab — source de la tuile" in D["dePl"]["lbl"], D["dePl"]["lbl"])
    check("3g_un_rendu_n_a_aucune_de_ces_cibles", not any(x.startswith(("📷", "✒", "🧱")) for x in D["ren"]["lbl"]),
          D["ren"]["lbl"])
    check("3h___dzEnvoyerVers_ouvre_le_meme_menu_pour_l_image_du_photolab",
          D["vers"]["titre"] == "Envoyer « c.png » vers…" and "🎬 Studio — nœud Image" in D["vers"]["lbl"]
          and "📷 Photolab — retoucher l'image" not in D["vers"]["lbl"] and D["versCh"] is True
          and (D.get("versEnv") or {}).get("image") == "c.png", D["vers"])
    check("3i___dzEnvoyerVers_sans_origine_garde_la_cible_photolab",
          "📷 Photolab — retoucher l'image" in D["versSans"]["lbl"], D["versSans"]["lbl"])

print("\n[4] le contrat partagé")
s1, s2 = RACINE / "frontend/shared/dz-envoi.js", RACINE / "frontend/dist/shared/dz-envoi.js"
check("4a_dz_envoi_servi_a_l_identique_depuis_dist_shared", s1.is_file() and s2.is_file()
      and s1.read_bytes().replace(b"\r\n", b"\n") == s2.read_bytes().replace(b"\r\n", b"\n"))
check("4b_le_bundle_et_le_contrat_parlent_du_meme_porteur",
      "window.__dzEnvoiImg={cible:c,image:n,t:Date.now()}" in BUN and "__dzEnvoiImg" in s1.read_text("utf-8"))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
