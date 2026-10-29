# -*- coding: utf-8 -*-
"""t333 + t338 (A3 + A8 du lot Scenario, 29/10/2026) — l'ÉCRAN du Plateau 3D : previs colorée (légende, matière,
faisceaux exclus des captures) et couverture du plan (caméras nommées : voir, capturer, nouveau plan, image du plan).

  [1] la page : chaque hôte lu par le bloc existe, sections « Previs colorée » et « Couverture », règle des 180° dite ;
  [2] le câblage de plateau.js (posé par la saisie L9 scripts/i18n_l9/t333.py, table réversible) : palette demandée au
      serveur sur la scène AFFICHÉE, matière dans la fiche, rôle « faisceau », capture qui envoie la scène, couverture,
      nouveau plan et image du plan derrière un bouton ARMÉ (aucun dialogue natif) ;
  [3] SOUS NODE, les vraies fonctions du bloc (extraites de plateau.js) : un faisceau (rôle OU nom repéré par le
      serveur) est CACHÉ pendant le rendu de capture puis rendu visible — et seulement lui ; couleur de la palette,
      repli sinon ; le rendu de capture cache AVANT de rendre et rend visible APRÈS avoir lu le tampon ;
  [4] FR/EN : chaque clé t333_/t338_ du script et chaque texte neuf de la page sont au dictionnaire plateau.json.
Run : & $PY tests/test_plateau_previs_ecran.py   (depuis backend/)
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
RACINE = HERE.parent.parent
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


def lire(rel):
    return (RACINE / rel).read_bytes().decode("utf-8").replace("\r\n", "\n")


HTML, JS = lire("frontend/plateau/index.html"), lire("frontend/plateau/plateau.js")
DICO = json.loads(lire("frontend/shared/i18n/plateau.json"))

print("[1] la page")
for i in ("legende", "faisceaux", "legPrompt", "covPartenaire", "covGrosPlan", "btnCouverture", "covAvert", "cameras"):
    check(f"1a_hote_{i}", f'id="{i}"' in HTML and f'$("#{i}")' in JS)
check("1b_sections_dans_l_ordre_avant_les_sorties", 0 < HTML.find(">Previs colorée<") < HTML.find(">Couverture<")
      < HTML.find(">Sorties<"))
check("1c_regle_des_180_expliquee", "<summary>La règle des 180°</summary>" in HTML and "même côté de cet axe" in HTML)
check("1d_gratuit_dit_avant_le_geste", "gratuit, tout local" in HTML)

print("\n[2] le câblage")
check("2a_palette_de_la_scene_affichee", '`${API}/${P.scene.id}/palette`, "POST", { scene: sceneAffichée() }' in JS)
check("2b_la_sauvegarde_rafraichit_la_palette", re.search(r"function sauver\(\) \{\n  P\.dirty = true;\n  previsBientot\(\);", JS))
check("2c_matiere_et_role_faisceau_dans_la_fiche", 'data-k="matiere"' in JS and '["sujet", "decor", "repere", "faisceau"].map(' in JS
      and 'else if (k === "matiere") i.matiere = el.value.trim() || null;' in JS and "faisceau: __dzT9(\"plateau.pl_role.faisceau\"" in JS)
check("2d_capture_debut_fin_envoie_la_scene", "{ quand, image_b64: b64, scene: sceneAffichée() }" in JS)
check("2e_capture_de_camera_nommee", '{ quand: "camera", camera_id: id, image_b64: image, scene: sceneAffichée() }' in JS)
check("2f_couverture_rangee_et_cameras", '`${API}/${P.scene.id}/couverture`, "POST", corps)' in JS and "enregistrer: true" in JS
      and "/nouveau-plan`" in JS)
check("2g_gestes_qui_ecrivent_derriere_un_bouton_arme", JS.count('if (b.dataset.arm !== "1") {') == 2
      and JS.count("confirmer: true") >= 3)
check("2h_aucun_dialogue_natif", not re.search(r"\b(alert|confirm|prompt)\(", JS))
check("2i_la_couverture_rangee_est_relue_a_l_ouverture", "previsOuvrir();" in JS and "P.couverture = P.scene.couverture || null;" in JS)
check("2j_maillages_et_proxys_peints_previs_jamais_grise", "function recolorer()" in JS and "o.traverse((m) => {" in JS)

print("\n[3] sous node : les fonctions du bloc")


def fonction(nom):
    m = re.search(r"\nfunction " + nom + r"\(.*?\n\}\n", JS, re.S)
    return m.group(0) if m else ""


SRC = "\n".join(fonction(n) for n in ("estFaisceauAffiche", "couleurPrevis", "basculerFaisceaux"))
rendre = fonction("rendreA")
check("3a_fonctions_trouvees", SRC.count("function ") == 3 and rendre, len(SRC))
i_cache, i_rendu = rendre.find("basculerFaisceaux(false)"), rendre.find("r.render(V.scene, c);")
i_lu, i_rend = rendre.find('toDataURL("image/png")'), rendre.find("basculerFaisceaux(true, vus)")
check("3b_rendu_de_capture_cache_avant_et_rend_apres", 0 <= i_cache < i_rendu < i_lu < i_rend, (i_cache, i_rendu, i_lu, i_rend))
PROBE = SRC + """
const COUL_FAISCEAU = "#ffe8a3";
const obj = (id) => ({ id, visible: true });
const P = { palette: null, mesh: new Map(), scene: { instances: [
  { id: "sujet", role: "sujet" }, { id: "phare", role: "decor", nom: "Faisceau du phare" },
  { id: "lum", role: "faisceau" }, { id: "arbre", role: "decor" }, { id: "cache", role: "faisceau" }] } };
for (const i of P.scene.instances) P.mesh.set(i.id, obj(i.id));
P.mesh.get("cache").visible = false;                       // déjà caché par l'utilisateur : il le reste
const out = {};
out.sansPalette = basculerFaisceaux(false).map((o) => o.id);
basculerFaisceaux(true, out.sansPalette.map((id) => P.mesh.get(id)));
P.palette = { couleurs: { sujet: "#2fb344", arbre: "#c92a2a" }, faisceaux: [{ id: "phare" }] };
const vus = basculerFaisceaux(false);
out.caches = vus.map((o) => o.id);
out.pendant = [...P.mesh.values()].filter((o) => !o.visible).map((o) => o.id).sort();
basculerFaisceaux(true, vus);
out.apres = [...P.mesh.values()].filter((o) => !o.visible).map((o) => o.id);
out.couleurs = ["sujet", "arbre", "phare", "lum"].map((id) => couleurPrevis(P.scene.instances.find((i) => i.id === id), "#888888"));
out.repli = couleurPrevis({ id: "neuf", role: "decor" }, "#888888");
console.log(JSON.stringify(out));
"""
D = {}
if NODE:
    tmp = Path(tempfile.mkdtemp(prefix="dzt333e_"))
    f = tmp / "p.mjs"
    f.write_text(PROBE, encoding="utf-8")
    r = subprocess.run([NODE, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    try:
        D = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        print("  (node :", (r.stderr or r.stdout)[-400:], ")")
    shutil.rmtree(tmp, ignore_errors=True)
check("3c_node_execute", bool(D), bool(NODE))
if D:
    check("3d_role_faisceau_cache_meme_sans_palette", D["sansPalette"] == ["lum"], D["sansPalette"])
    check("3e_faisceau_repere_par_le_serveur_aussi_cache", sorted(D["caches"]) == ["lum", "phare"]
          and D["pendant"] == ["cache", "lum", "phare"], D)
    check("3f_tout_rendu_visible_apres_sauf_ce_qui_etait_cache", D["apres"] == ["cache"], D["apres"])
    check("3g_couleurs_palette_faisceau_et_repli", D["couleurs"] == ["#2fb344", "#c92a2a", "#ffe8a3", "#ffe8a3"]
          and D["repli"] == "#888888", D)

print("\n[4] FR/EN")
cles = set(re.findall(r'__dzT9\("(plateau\.t33[38]_[a-z0-9_.]+)"', JS))
manque = sorted(k for k in cles if not (DICO.get(k, {}).get("fr") and DICO.get(k, {}).get("en")))
check("4a_chaque_cle_du_bloc_au_dictionnaire_fr_en", len(cles) >= 30 and not manque, (len(cles), manque))
neufs = ["Previs colorée", "Couverture", "Interlocuteur", "Gros plan", "Générer la couverture", "La règle des 180°",
         "Cible du gros plan"]
fr = {v["fr"] for v in DICO.values()}
check("4b_textes_neufs_de_la_page_traduits_par_la_surcouche", all(t in fr for t in neufs), [t for t in neufs if t not in fr])
check("4c_role_faisceau_traduit", DICO.get("plateau.pl_role.faisceau", {}).get("en") == "light beam")

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
