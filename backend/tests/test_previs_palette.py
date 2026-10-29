# -*- coding: utf-8 -*-
"""t333 (A3 du lot Scenario, 29/10/2026) — la PREVIS COLORÉE ET NOMMÉE : palette des proxys par entité de bible /
matière, légende lisible (écran FR/EN) et injectée dans les prompts (anglais), faisceaux de lumière exclus.

  [1] la palette : contrastée (écart de couleur minimal entre deux teintes), aucune teinte grise ni proche du sol ;
  [2] la couleur d'une entité est STABLE : même clé → même couleur d'une scène à l'autre (préférence par empreinte
      crc32, jamais hash() de Python), ajouter une instance APRÈS ne change pas les couleurs déjà données, deux clés
      d'une même scène n'ont jamais la même couleur tant que la palette suffit ;
  [3] les clés : entité de la bible > matière saisie > nom (« (bible) », « (copie) » retirés) ; les copies partagent ;
  [4] la légende : accord du français (« cylindres verts », « capsule verte », « sphères blanches »), anglais
      (« green cylinders »), formes mêlées → « formes » ; le prompt anglais nomme chaque forme ;
  [5] les faisceaux (rôle « faisceau » ou nom qui le dit) : hors palette, hors légende, listés, et le prompt le dit ;
  [6] la table pour Blender : couleur linéaire (sRGB → linéaire), objets, matériau nommé ;
  [7] la phrase ajoutée au prompt de l'image du plan.
Run : & $PY tests/test_previs_palette.py   (depuis backend/)
"""
import os
import sys
import zlib

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


from app.services import previs_palette as PP  # noqa: E402


def inst(iid, nom, forme="boite", role="decor", entity_id=None, matiere=None, kind="proxy"):
    src = {"kind": "proxy", "forme": forme} if kind == "proxy" else {"kind": "assets3d", "job": "j1", "file": "model.glb"}
    d = {"id": iid, "nom": nom, "source": src, "role": role, "dims": [1, 1, 1],
         "transform": {"pos": [0, 0, 0], "rot": [0, 0, 0], "scale": 1}, "entity_id": entity_id}
    if matiere is not None:
        d["matiere"] = matiere
    return d


print("[1] la palette")
P = PP.PALETTE
check("1a_dix_teintes_au_moins_hex_valides", len(P) >= 10 and all(len(c["hex"]) == 7 and c["hex"][0] == "#" for c in P))


def rgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


ecarts = [sum((a - b) ** 2 for a, b in zip(rgb(x["hex"]), rgb(y["hex"]))) ** 0.5 for i, x in enumerate(P) for y in P[i + 1:]]
check("1b_contrastee_ecart_minimal_superieur_a_80", min(ecarts) > 80, round(min(ecarts), 1))
gris = [c["hex"] for c in P if max(rgb(c["hex"])) - min(rgb(c["hex"])) < 30 and 60 < sum(rgb(c["hex"])) / 3 < 200]
check("1c_aucun_gris_moyen_confondu_avec_le_sol_ou_un_repere", not gris, gris)
check("1d_chaque_teinte_a_ses_noms_fr_accordes_et_en",
      all(set(c["fr"]) == {"m", "f", "mp", "fp"} and c["en"] for c in P))

print("\n[2] stabilité")
a = PP.palette([inst("c1", "Cyprès", "cylindre"), inst("m", "Marie (bible)", "capsule", "sujet", entity_id="ent-marie")])
b = PP.palette([inst("x", "Banc"), inst("m2", "Marie", "capsule", "sujet", entity_id="ent-marie")])
coul = lambda t, cle: next(e["couleur"] for e in t["table"] if e["cle"] == cle)  # noqa: E731
check("2a_meme_entite_meme_couleur_dans_deux_scenes", coul(a, "entite:ent-marie") == coul(b, "entite:ent-marie"),
      (coul(a, "entite:ent-marie"), coul(b, "entite:ent-marie")))
pref = zlib.crc32(b"entite:ent-marie") % len(P)
check("2b_preference_par_crc32_et_entites_servies_d_abord", coul(b, "entite:ent-marie") == P[pref]["hex"]
      and coul(a, "entite:ent-marie") == P[pref]["hex"], (pref, coul(b, "entite:ent-marie")))
base = [inst(f"i{k}", f"objet {k}") for k in range(6)]
t1 = PP.palette(base)
t2 = PP.palette(base + [inst("neuf", "lampadaire")])
check("2c_ajouter_apres_ne_change_rien_avant",
      all(coul(t1, e["cle"]) == coul(t2, e["cle"]) for e in t1["table"]))
t3 = PP.palette([inst(f"i{k}", f"objet {k}") for k in range(len(P))])
check("2d_cles_distinctes_couleurs_distinctes_tant_que_la_palette_suffit",
      len({e["couleur"] for e in t3["table"]}) == len(P) and not t3["partagees"])
t4 = PP.palette([inst(f"i{k}", f"objet {k}") for k in range(len(P) + 2)])
check("2e_au_dela_les_couleurs_partagees_sont_dites", len(t4["partagees"]) == 2, t4["partagees"])
check("2f_deterministe", PP.palette(base) == PP.palette(base))

print("\n[3] les clés")
t = PP.palette([inst("c1", "Cyprès", "cylindre"), inst("c2", "Cyprès (copie)", "cylindre"),
                inst("z", "bloc", matiere="ajoncs"), inst("e", "Lanterne (bible)", entity_id="ent-l", kind="assets3d")])
cles = [e["cle"] for e in t["table"]]
check("3a_les_copies_partagent_la_cle_et_la_couleur", cles.count("matiere:cypres") == 1
      and next(e for e in t["table"] if e["cle"] == "matiere:cypres")["ids"] == ["c1", "c2"], t["table"])
check("3b_la_matiere_saisie_l_emporte_sur_le_nom", "matiere:ajoncs" in cles and next(
    e for e in t["table"] if e["cle"] == "matiere:ajoncs")["libelle"] == "ajoncs")
check("3c_l_entite_l_emporte_et_le_libelle_perd_bible", "entite:ent-l" in cles and next(
    e for e in t["table"] if e["cle"] == "entite:ent-l")["libelle"] == "Lanterne")
check("3d_chaque_instance_a_sa_couleur", set(t["couleurs"]) == {"c1", "c2", "z", "e"}
      and t["couleurs"]["c1"] == t["couleurs"]["c2"])

print("\n[4] la légende")
VERT = next(c for c in P if c["en"] == "green")
ROUGE = next(c for c in P if c["en"] == "red")
BLANC = next(c for c in P if c["en"] == "white")
ent = lambda cle, formes, n, c: {"cle": cle, "libelle": cle, "couleur": c["hex"], "formes": formes, "ids": ["x"] * n,  # noqa: E731
                                 "teinte": c}
check("4a_fr_masculin_pluriel", PP.ligne_fr(ent("cyprès", ["cylindre"], 3, VERT)) == "cylindres verts = cyprès")
check("4b_fr_feminin_singulier", PP.ligne_fr(ent("Marie", ["capsule"], 1, VERT)) == "capsule verte = Marie")
check("4c_fr_feminin_pluriel_blanc", PP.ligne_fr(ent("lunes", ["sphere"], 2, BLANC)) == "sphères blanches = lunes")
check("4d_fr_masculin_singulier_rouge_bloc", PP.ligne_fr(ent("banc", ["boite"], 1, ROUGE)) == "bloc rouge = banc")
check("4e_en_pluriel", PP.ligne_en(ent("cyprès", ["cylindre"], 3, VERT)) == "green cylinders = cyprès")
check("4f_formes_melees", PP.ligne_fr(ent("arbres", ["cylindre", "sphere"], 2, VERT)) == "formes vertes = arbres"
      and PP.ligne_en(ent("arbres", ["cylindre", "sphere"], 2, VERT)) == "green shapes = arbres")
check("4g_maillage_modele", PP.ligne_en(ent("Lanterne", ["maillage"], 1, ROUGE)) == "red model = Lanterne"
      and PP.ligne_fr(ent("Lanterne", ["maillage"], 1, ROUGE)) == "modèle rouge = Lanterne")
lg = PP.palette([inst("c1", "Cyprès", "cylindre"), inst("c2", "Cyprès", "cylindre"),
                 inst("m", "Marie", "capsule", "sujet")])
check("4h_legende_dans_les_deux_langues", len(lg["legende"]["fr"]) == 2 and len(lg["legende"]["en"]) == 2
      and lg["legende"]["fr"][0].startswith("cylindres ") and lg["legende"]["fr"][0].endswith(" = Cyprès"))
check("4i_le_prompt_nomme_chaque_forme", lg["prompt"].startswith("Colour-coded previs: ")
      and all(x in lg["prompt"] for x in lg["legende"]["en"]) and "Light" not in lg["prompt"], lg["prompt"])
check("4j_scene_vide_aucun_prompt", PP.palette([])["prompt"] == "" and PP.palette([])["legende"] == {"fr": [], "en": []})
rep = PP.palette([inst("r", "marque au sol", role="repere"), inst("a", "arbre")])
check("4k_les_reperes_hors_legende", [e["cle"] for e in rep["table"]] == ["matiere:arbre"] and "r" not in rep["couleurs"])

print("\n[5] les faisceaux")
f = PP.palette([inst("ph", "Faisceau du phare", "cylindre"), inst("l", "lumière", "cylindre", role="faisceau"),
                inst("v", "Voiture")])
check("5a_hors_palette_et_hors_legende", [e["cle"] for e in f["table"]] == ["matiere:voiture"]
      and "ph" not in f["couleurs"] and "l" not in f["couleurs"], f["table"])
check("5b_listes_avec_leur_raison", sorted((x["id"], x["raison"]) for x in f["faisceaux"]) == [("l", "role"), ("ph", "nom")])
check("5c_le_prompt_le_dit", "light beams" in f["prompt"].lower() and "not solid" in f["prompt"].lower(), f["prompt"])
check("5d_detecteur", all(PP.est_faisceau(inst("q", n)) for n in ("faisceau", "Light beam", "god rays", "cône de lumière",
                                                                  "Volume de lumière", "rayon lumineux"))
      and not any(PP.est_faisceau(inst("q", n)) for n in ("lampe", "phare", "Rayonnage", "lumineux salon")))

print("\n[6] la table pour Blender")
bl = lg["blender"]
check("6a_version_et_materiaux_nommes", bl["version"] == 1 and len(bl["materiaux"]) == 2
      and all(m["nom"].startswith("previs_") for m in bl["materiaux"]))
m0 = bl["materiaux"][0]
r8 = int(m0["hex"][1:3], 16) / 255
lin = r8 / 12.92 if r8 <= 0.04045 else ((r8 + 0.055) / 1.055) ** 2.4
check("6b_couleur_lineaire_srgb", abs(m0["rgba_lineaire"][0] - round(lin, 5)) < 1e-6 and m0["rgba_lineaire"][3] == 1.0)
check("6c_objets_et_exclus", m0["objets"] == ["c1", "c2"] and bl["exclus"] == [])

print("\n[7] le prompt de l'image du plan")
p = PP.phrase_image(lg["prompt"])
check("7a_phrase_image_dit_la_derniere_reference_et_la_legende", "last reference image" in p and lg["prompt"] in p
      and "not its colours" in p, p)
check("7b_sans_legende_rien", PP.phrase_image("") == "")

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
