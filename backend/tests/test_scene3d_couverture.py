# -*- coding: utf-8 -*-
"""t338 (A8 du lot Scenario, 29/10/2026) — la COUVERTURE d'un plan depuis la même scène : plan large, contre-champ
(règle des 180° tenue), gros plan. Géométrie PURE (scene3d_couverture), recalculée à la main ici.

  [1] le plan large : même axe que la caméra du plan, focale 24 mm, le sujet (et l'interlocuteur) entier dans le cadre,
      encombrement 0,40 ; type mesuré « wide » ou « establishing » ;
  [2] le contre-champ AVEC interlocuteur : la caméra regarde l'interlocuteur, reste du MÊME côté de l'axe
      sujet ↔ interlocuteur (règle des 180°), cadre l'interlocuteur à la taille du sujet dans le plan d'origine ;
      la caméra du plan sur l'axe : dit, jamais inventé ;
  [3] le contre-champ SANS interlocuteur : 180° autour du sujet (contrechamp de la caméra), même distance, même focale ;
  [4] le gros plan : sur le sujet choisi, focale 85 mm, h = 0,85, type « close-up » ; la mesure du Plateau
      (scene3d.mesure) donne la même chose ;
  [5] noms, prompts, identifiants stables ; refus nommés (pas de sujet, cible inconnue) ;
  [6] l'interlocuteur choisi d'office : la capsule / l'entité la plus proche, jamais un repère ni un faisceau.
Run : & $PY tests/test_scene3d_couverture.py   (depuis backend/)
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


from app.services import scene3d as S, scene3d_couverture as C  # noqa: E402


def capsule(iid, x, z=0.0, role="decor", nom=None, **k):
    return {"id": iid, "nom": nom or iid, "source": {"kind": "proxy", "forme": "capsule"}, "dims": [0.5, 1.7, 0.4],
            "role": role, "transform": {"pos": [x, 0, z], "rot": [0, 0, 0], "scale": 1}, **k}


def boite(iid, x, z=0.0, role="decor", nom=None):
    return {"id": iid, "nom": nom or iid, "source": {"kind": "proxy", "forme": "boite"}, "dims": [1, 1, 1],
            "role": role, "transform": {"pos": [x, 0, z], "rot": [0, 0, 0], "scale": 1}}


SC = {"aspect": "16:9", "capteur_mm": 14.2,
      "instances": [capsule("marie", 0, role="sujet", nom="Marie"), capsule("paul", 2, nom="Paul"),
                    boite("banc", -3, 2, nom="banc")]}
BASE = {"orbit": [30, 90, 5], "target": [0, 0.85, 0], "fov": S.fov_de_focale(35, 14.2)}
ASP = 16 / 9


def pos(cam):
    return S.position_camera(cam["orbit"], cam["target"])


def cote(a, b, p):
    u = [b[0] - a[0], b[2] - a[2]]
    return u[0] * (p[2] - a[2]) - u[1] * (p[0] - a[0])


def hy(inst, cam):
    pr = S.projeter(S.coins(inst), cam, ASP)
    ys = [p[1] for p in pr if p[0] is not None]
    xs = [p[0] for p in pr if p[0] is not None]
    return (max(ys) - min(ys)) / 2, (max(xs) - min(xs)) / 2, len(ys) == 8 and all(abs(v) <= 1 for v in xs + ys)


R = C.couverture(SC, BASE, partenaire_id="paul")
cams = {c["id"]: c for c in R["cameras"]}
check("0a_trois_cameras_nommees_dans_l_ordre", [c["id"] for c in R["cameras"]] == ["large", "contrechamp", "gros_plan"]
      and [c["nom"] for c in R["cameras"]] == ["Plan large", "Contre-champ — Paul", "Gros plan — Marie"],
      [c["nom"] for c in R["cameras"]])

print("[1] le plan large")
L = cams["large"]
cm = C.centre(SC["instances"][0]), C.centre(SC["instances"][1])
mil = [(a + b) / 2 for a, b in zip(*cm)]
check("1a_cadre_le_milieu_du_sujet_et_de_l_interlocuteur", max(abs(a - b) for a, b in zip(L["camera"]["target"], mil)) < 1e-9)
d0 = [p - t for p, t in zip(pos(BASE), mil)]
d1 = [p - t for p, t in zip(pos(L["camera"]), mil)]
n0, n1 = math.hypot(*d0), math.hypot(*d1)
check("1b_meme_axe_que_la_camera_du_plan", max(abs(a / n0 - b / n1) for a, b in zip(d0, d1)) < 1e-6)
check("1c_focale_24_mm", abs(L["focale_mm"] - 24) < 1e-6 and abs(L["camera"]["fov"] - S.fov_de_focale(24, 14.2)) < 1e-9)
pts = S.coins(SC["instances"][0]) + S.coins(SC["instances"][1])
pr = S.projeter(pts, L["camera"], ASP)
enc = max((max(p[1] for p in pr) - min(p[1] for p in pr)) / 2, (max(p[0] for p in pr) - min(p[0] for p in pr)) / 2)
check("1d_les_deux_entiers_encombrement_0_40", abs(enc - 0.40) < 2e-3 and all(abs(p[0]) <= 1 and abs(p[1]) <= 1 for p in pr),
      round(enc, 4))
check("1e_type_mesure_large", L["shot_type"] in ("wide", "establishing") and L["dans_cadre"], L["shot_type"])

print("\n[2] le contre-champ avec interlocuteur (règle des 180°)")
K = cams["contrechamp"]
A, B = cm
check("2a_regarde_l_interlocuteur", max(abs(a - b) for a, b in zip(K["camera"]["target"], B)) < 1e-9)
s0, s1 = cote(A, B, pos(BASE)), cote(A, B, pos(K["camera"]))
check("2b_meme_cote_de_l_axe", s0 * s1 > 0 and R["regle_180"]["respectee"] and R["regle_180"]["cote_base"] ==
      R["regle_180"]["cote_contrechamp"] == (1 if s0 > 0 else -1), (s0, s1, R["regle_180"]))
check("2c_axe_nomme", R["regle_180"]["axe"] == ["marie", "paul"] and "180" in R["regle_180"]["explication"])
h_base = hy(SC["instances"][0], BASE)[0]
check("2d_interlocuteur_a_la_taille_du_sujet_d_origine", abs(hy(SC["instances"][1], K["camera"])[0] - h_base) < 2e-3,
      (hy(SC["instances"][1], K["camera"])[0], h_base))
pc = pos(K["camera"])
check("2e_du_cote_du_sujet_epaule", (pc[0] - mil[0]) * (B[0] - A[0]) < 0, pc)
check("2f_focale_du_plan_gardee", abs(K["camera"]["fov"] - BASE["fov"]) < 1e-9)
SUR = {"orbit": [90, 90, 5], "target": [0, 0.85, 0], "fov": BASE["fov"]}       # caméra SUR l'axe (x = 5)
R2 = C.couverture(SC, SUR, partenaire_id="paul")
check("2g_camera_sur_l_axe_dite", R2["regle_180"]["cote_base"] == 0 and not R2["regle_180"]["respectee"]
      and "axe" in R2["regle_180"]["avertissement"], R2["regle_180"])

print("\n[3] sans interlocuteur")
SC1 = {"aspect": "16:9", "capteur_mm": 14.2, "instances": [capsule("marie", 0, role="sujet", nom="Marie"),
                                                          boite("banc", -3, 2, nom="banc")]}
R3 = C.couverture(SC1, BASE)
K3 = next(c for c in R3["cameras"] if c["id"] == "contrechamp")
check("3a_180_degres_autour_du_sujet", abs(K3["camera"]["orbit"][0] - 210) < 1e-6
      and abs(K3["camera"]["orbit"][1] - 90) < 1e-6 and abs(K3["camera"]["orbit"][2] - 5) < 1e-6, K3["camera"])
check("3b_nom_et_axe", K3["nom"] == "Contre-champ" and R3["regle_180"]["axe"] is None and R3["partenaire"] is None)

print("\n[4] le gros plan")
G = cams["gros_plan"]
h, _x, dedans = hy(SC["instances"][0], G["camera"])
check("4a_h_0_85_focale_85_type_close_up", abs(h - 0.85) < 2e-3 and abs(G["focale_mm"] - 85) < 1e-6
      and G["shot_type"] == "close-up", (h, G["focale_mm"], G["shot_type"]))
m = S.mesure(SC, G["camera"])
check("4b_la_mesure_du_plateau_dit_pareil", m["shot_type"] == "close-up" and abs(m["h"] - G["h"]) < 1e-3, (m, G["h"]))
Gp = next(c for c in C.couverture(SC, BASE, partenaire_id="paul", gros_plan_id="paul")["cameras"] if c["id"] == "gros_plan")
check("4c_gros_plan_sur_une_autre_instance", Gp["nom"] == "Gros plan — Paul" and Gp["cible_id"] == "paul"
      and max(abs(a - b) for a, b in zip(Gp["camera"]["target"], B)) < 1e-9)

print("\n[5] prompts, refus")
check("5a_prompts_anglais_statiques", L["prompt"].startswith("wide shot, static, locked-off shot at ")
      and K["prompt"].startswith("reverse shot on Paul, ") and G["prompt"].startswith("close-up on Marie, ")
      and all(c["prompt"].endswith(" mm") for c in R["cameras"]), [c["prompt"] for c in R["cameras"]])
check("5b_deterministe", C.couverture(SC, BASE, partenaire_id="paul") == R)
for lab, f in (("sans_sujet", lambda: C.couverture({"aspect": "16:9", "instances": [boite("b", 0)]}, BASE)),
               ("interlocuteur_inconnu", lambda: C.couverture(SC, BASE, partenaire_id="zz")),
               ("interlocuteur_egal_sujet", lambda: C.couverture(SC, BASE, partenaire_id="marie")),
               ("gros_plan_inconnu", lambda: C.couverture(SC, BASE, gros_plan_id="zz"))):
    try:
        f()
        check(f"5c_refus_{lab}", False)
    except ValueError as e:
        check(f"5c_refus_{lab}", bool(str(e)), e)

print("\n[6] l'interlocuteur d'office")
SC6 = {"aspect": "16:9", "capteur_mm": 14.2,
       "instances": [capsule("marie", 0, role="sujet"), boite("mur", 0.5), capsule("loin", 6),
                     capsule("pres", 3, nom="Paul"), capsule("rep", 1, role="repere"),
                     capsule("lum", 1.5, role="faisceau")]}
check("6a_la_capsule_la_plus_proche_hors_repere_et_faisceau", C.couverture(SC6, BASE)["partenaire"] == "pres",
      C.couverture(SC6, BASE)["partenaire"])
check("6b_partenaire_aucun_force_le_180_autour_du_sujet",
      C.couverture(SC6, BASE, partenaire_id="")["partenaire"] is None)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
