# -*- coding: utf-8 -*-
"""t127 T1 (07/10/2026) — la géométrie pure du Plateau 3D (`app.services.scene3d`), spec
docs/superpowers/specs/2026-08-29-plateau-previsualisation-3d-design.md §5. Aucun navigateur, aucune E/S : chaque
attendu est recalculé ici à la main (trigonométrie écrite dans le banc), jamais lu sur le code testé.

  [1] focale ↔ champ vertical (§5.1) ;
  [2] position de caméra depuis l'orbite [θ°, φ°, r] (convention <model-viewer>, gardée pour les keyframes) ;
  [3] projection et `shot_type` mesuré (§5.2) — le cas de la spec : un sujet de 1,7 m à 6 m en 35 mm ;
  [4] interpolation des keyframes et easing ;
  [5] mouvement déduit (§5.3) — UNE ligne de la table = UN cas, plus les attributs et l'avertissement hors cadre ;
  [6] le prompt de mouvement (§5.4) écrit depuis les chiffres.
Run : & $PY tests/test_scene3d.py   (depuis backend/)
"""
import math
import os
import sys

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


def proche(a, b, tol=1e-6):
    return a is not None and abs(a - b) <= tol


try:
    from app.services import scene3d as S
except Exception as e:                       # le banc rougit, ne meurt pas
    S = None
    print(f"  (import impossible : {e!r})")
check("x0_module_importe", S is not None)
if S is None:
    print(f"\n=== {ok} passed, {fail} failed ===")
    sys.exit(1)

SUJET = {"id": "s", "role": "sujet", "dims": [0.5, 1.7, 0.4], "transform": {"pos": [0, 0, 0], "rot": [0, 0, 0], "scale": 1}}
DECOR = {"id": "d", "role": "decor", "dims": [4, 3, 0.2], "transform": {"pos": [0, 0, -3], "rot": [0, 0, 0], "scale": 1}}
SCENE = {"aspect": "16:9", "capteur_mm": 14.2, "instances": [DECOR, SUJET]}

print("\n[1] focale ↔ champ")
fov35 = math.degrees(2 * math.atan(14.2 / (2 * 35)))
check("1a_fov_de_35mm_super35", proche(S.fov_de_focale(35, 14.2), fov35), (S.fov_de_focale(35, 14.2), fov35))
check("1b_aller_retour_focale", proche(S.focale_de_fov(S.fov_de_focale(85, 14.2), 14.2), 85, 1e-9))
check("1c_24mm_plus_large_que_85mm", S.fov_de_focale(24, 14.2) > S.fov_de_focale(85, 14.2))
for bad in (0, -5, float("nan"), None, "x"):
    try:
        S.fov_de_focale(bad, 14.2)
        check(f"1d_focale_illisible_refusee_{bad!r}", False)
    except ValueError:
        check(f"1d_focale_illisible_refusee_{bad!r}", True)

print("\n[2] orbite → position")
p = S.position_camera([0, 90, 6], [0, 0.85, 0])
check("2a_theta0_phi90_devant_sur_+Z_a_hauteur_de_cible", all(proche(a, b) for a, b in zip(p, [0, 0.85, 6])), p)
p = S.position_camera([90, 90, 2], [0, 0, 0])
check("2b_theta90_sur_+X", all(proche(a, b) for a, b in zip(p, [2, 0, 0])), p)
p = S.position_camera([0, 0, 3], [1, 1, 1])
check("2c_phi0_au_zenith", all(proche(a, b) for a, b in zip(p, [1, 4, 1])), p)

print("\n[3] projection et shot_type")
CAM = {"orbit": [0, 90, 6], "target": [0, 0.85, 0], "fov": fov35}
m = S.mesure(SCENE, CAM)
tanv = math.tan(math.radians(fov35) / 2)
# coins avant (z = +0,2, donc à 5,8 m) : ±0,85 m autour de la cible → la plus grande extension verticale
h_attendu = (0.85 / (5.8 * tanv)) * 2 / 2
check("3a_h_du_cas_de_la_spec_recalcule_a_la_main", proche(m["h"], round(h_attendu, 4), 1e-4), (m["h"], h_attendu))
check("3b_shot_type_medium_entre_045_et_075", m["shot_type"] == "medium" and 0.45 < m["h"] < 0.75, m)
check("3c_distance_et_focale_rendues", proche(m["distance_m"], 6.0, 1e-9) and proche(m["focale_mm"], 35, 1e-6), m)
check("3d_sujet_dans_le_cadre", m["dans_cadre"] is True, m)
types = [S.mesure(SCENE, {"orbit": [0, 90, r], "target": [0, 0.85, 0], "fov": fov35})["shot_type"] for r in (40, 12, 6, 5, 3)]   # h ≈ 0,105 · 0,355 · 0,722 · 0,873 · 1,52
check("3e_rapprocher_la_camera_parcourt_l_echelle_des_plans",
      types == ["establishing", "wide", "medium", "close-up", "extreme close-up"], types)
m2 = S.mesure(SCENE, {"orbit": [0, 90, 6], "target": [3, 0.85, 0], "fov": fov35})
check("3f_cible_deportee_le_sujet_sort_du_cadre", m2["dans_cadre"] is False and m["dans_cadre"] is True, m2)
mseuils = S.mesure(SCENE, CAM, seuils={"establishing": 0.1, "wide": 0.2, "medium": 0.3, "close-up": 0.5})
check("3g_seuils_configurables_rendus_avec_la_mesure",
      mseuils["shot_type"] == "extreme close-up" and mseuils["seuils"]["medium"] == 0.3 and m["seuils"] == S.SEUILS, mseuils)
m3 = S.mesure(dict(SCENE, aspect="9:16"), CAM)
check("3h_le_format_9_16_ne_change_pas_h_mais_le_cadre_horizontal",
      proche(m3["h"], m["h"], 1e-9) and m3["dans_cadre"] is True, (m3["h"], m["h"]))
try:
    S.mesure({"aspect": "16:9", "instances": [DECOR]}, CAM)
    check("3i_sans_sujet_refus", False)
except ValueError as e:
    check("3i_sans_sujet_refus", "sujet" in str(e), e)
sujet_tourne = dict(SUJET, transform={"pos": [0, 0, 0], "rot": [0, 90, 0], "scale": 2})
mt = S.mesure({"aspect": "16:9", "instances": [sujet_tourne]}, {"orbit": [0, 90, 12], "target": [0, 1.7, 0], "fov": fov35})
# échelle 2 → 3,4 m de haut ; tourné de 90° autour de Y → profondeur 0,5×2 = 1 m, coins avant à 11,5 m
h_t = (1.7 / (11.5 * tanv))
check("3j_rotation_et_echelle_appliquees_aux_coins", proche(mt["h"], round(h_t, 4), 1e-4), (mt["h"], h_t))

CAMX = {"orbit": [0, 90, 6], "target": [-1.7, 0.85, 0], "fov": fov35}   # sujet décalé de 1,7 m à droite de la visée
mx16, mx9 = S.mesure(SCENE, CAMX), S.mesure(dict(SCENE, aspect="9:16"), CAMX)
# bord droit du sujet : x = 1,7 + 0,25 = 1,95 m à 5,8 m → ndc 16:9 = 1,95 / (5,8·tan·16/9) ≈ 0,93 ; en 9:16 ≈ 2,9
check("3k_le_format_decide_du_hors_cadre_horizontal", mx16["dans_cadre"] is True and mx9["dans_cadre"] is False, (mx16, mx9))
mpied = S.mesure(SCENE, {"orbit": [0, 90, 6], "target": [0, 0, 0], "fov": fov35})
# cible AU PIED : le sujet va de 0 (centre de l'image) à +1,7 m — h = 1,7 / (5,8·tan) / 2, PAS le bord haut seul
check("3l_cible_asymetrique_h_est_la_demi_etendue", abs(mpied["h"] - round(1.7 / (5.8 * tanv) / 2, 4)) < 1e-4, mpied)

print("\n[4] interpolation")
KF = [{"t": 0, "orbit": [0, 90, 6], "target": [0, 1, 0], "fov": 30, "easing": "linear"},
      {"t": 4, "orbit": [40, 80, 2], "target": [0, 1, 0], "fov": 30}]
mi = S.interpoler(KF, 2)
check("4a_lineaire_a_mi_chemin", proche(mi["orbit"][0], 20) and proche(mi["orbit"][2], 4) and proche(mi["orbit"][1], 85), mi)
KF2 = [dict(KF[0], easing="ease-in-out"), KF[1]]
check("4b_ease_in_out_lent_au_depart_symetrique",
      S.interpoler(KF2, 1)["orbit"][0] < 10 and proche(S.interpoler(KF2, 2)["orbit"][0], 20) and S.interpoler(KF2, 3)["orbit"][0] > 30)
check("4c_bornes_tenues_hors_plage", proche(S.interpoler(KF, -1)["orbit"][2], 6) and proche(S.interpoler(KF, 9)["orbit"][2], 2))
check("4d_un_seul_keyframe_fixe", proche(S.interpoler(KF[:1], 3)["orbit"][2], 6))

print("\n[5] mouvement déduit (table §5.3)")


def kf(t, th, ph, r, tgt=(0, 0.85, 0), fov=None):
    return {"t": t, "orbit": [th, ph, r], "target": list(tgt), "fov": fov or fov35}


CAS = [
    ("rayon_baisse_push_in", [kf(0, 0, 90, 6.2), kf(4, 0, 90, 2.4)], "slow push-in"),
    ("rayon_monte_pull_out", [kf(0, 0, 90, 2.4), kf(4, 0, 90, 6.2)], "slow pull-out"),
    ("theta_360_orbite", [kf(0, 0, 90, 5), kf(2, 180, 90, 5), kf(4, 360, 90, 5)], "360-degree orbit"),
    ("cible_bouge_rayon_constant_tracking", [kf(0, 0, 90, 5, (0, 0.85, 0)), kf(4, 0, 90, 5, (3, 0.85, 0))], "tracking shot"),
    ("camera_descend_grue", [kf(0, 0, 40, 6), kf(4, 0, 88, 6)], "crane shot descending"),
    ("rayon_baisse_fov_monte_vertigo", [kf(0, 0, 90, 6, fov=20), kf(4, 0, 90, 2.5, fov=50)], "dolly zoom (vertigo effect)"),
    ("rayon_monte_fov_baisse_vertigo_inverse", [kf(0, 0, 90, 2.5, fov=50), kf(4, 0, 90, 6, fov=20)], "dolly zoom (vertigo effect)"),
    ("theta_grand_en_moins_de_05s_whip", [kf(0, 0, 90, 5), kf(0.3, 90, 90, 5), kf(3, 90, 90, 5)], "whip pan transition"),
    ("tout_constant_plan_fixe", [kf(0, 0, 90, 5), kf(4, 1, 90, 5.02)], "static, locked-off"),
]
for nom, kfs, attendu in CAS:
    r = S.mouvement(SCENE, kfs)
    check(f"5_{nom}", r["camera_move"] == attendu, (r["camera_move"], r.get("deltas")))
r1 = S.mouvement(SCENE, [kf(0, 0, 90, 5)])
check("5j_un_seul_keyframe_plan_fixe", r1["camera_move"] == "static, locked-off", r1)
jamais = {"handheld with subtle shake", "rack focus reveal", "low angle dramatic"}
rendus = {S.mouvement(SCENE, kfs)["camera_move"] for _n, kfs, _a in CAS}
check("5k_les_trois_valeurs_hors_de_portee_ne_sont_jamais_mesurees", not (rendus & jamais) and len(rendus) == 8, rendus)
check("5l_toutes_les_valeurs_rendues_appartiennent_a_CameraMove",
      rendus <= {m.value for m in __import__("app.models.schemas", fromlist=["CameraMove"]).CameraMove}, rendus)
rb = S.mouvement(SCENE, [kf(0, 0, 105, 6), kf(4, 0, 105, 3)])
check("5m_camera_sous_l_horizon_attribut_low_angle_propose_pas_mesure",
      rb["camera_move"] == "slow push-in" and "low angle dramatic" in rb["attributs"], rb)
rh = S.mouvement(SCENE, [kf(0, 0, 90, 6, (0, 0.85, 0)), kf(4, 0, 90, 6, (6, 0.85, 0))])
check("5n_sujet_hors_cadre_pendant_le_mouvement_avertit",
      rh["camera_move"] == "tracking shot" and any("hors du cadre" in a for a in rh["avertissements"]), rh["avertissements"])
r0 = S.mouvement(SCENE, CAS[0][1])
check("5o_temoin_sans_sortie_aucun_avertissement", r0["avertissements"] == [], r0["avertissements"])
rm = S.mouvement(SCENE, [kf(0, 0, 88, 6), kf(4, 0, 40, 6)])
check("5q_grue_montante_hors_vocabulaire_plan_fixe_et_dit",
      rm["camera_move"] == "static, locked-off" and any("aucune valeur du vocabulaire" in a for a in rm["avertissements"]), rm)
rl = S.mouvement(SCENE, [kf(0, 0, 90, 5), kf(3, 90, 90, 5)])
check("5r_pivot_lent_de_90_degres_n_est_pas_un_whip", rl["camera_move"] == "static, locked-off"
      and any("aucune valeur du vocabulaire" in a for a in rl["avertissements"]), rl)
for bad in ([], [{"t": "x"}], [kf(0, 0, 90, 5), kf(0, 0, 90, 4)]):
    try:
        S.mouvement(SCENE, bad)
        check(f"5p_keyframes_invalides_refuses_{len(bad)}", False)
    except ValueError:
        check(f"5p_keyframes_invalides_refuses_{len(bad)}", True)

print("\n[6] prompt de mouvement")
pr = S.mouvement(SCENE, [kf(0, 0, 90, 6.2), kf(4, 0, 90, 2.4, (0.6, 0.85, 0))])["motion_prompt"]
check("6a_prompt_ecrit_depuis_les_chiffres",
      "slow dolly in from 6.2 m to 2.4 m" in pr and "35 mm" in pr and "eye-level" in pr, pr)
check("6b_position_du_sujet_au_tiers", "left third" in pr, pr)
pr2 = S.mouvement(SCENE, [kf(0, 0, 90, 5)])["motion_prompt"]
check("6c_plan_fixe_dit_locked_off", "locked-off" in pr2 and "centered" in pr2, pr2)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
