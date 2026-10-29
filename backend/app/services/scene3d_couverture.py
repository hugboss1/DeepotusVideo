# -*- coding: utf-8 -*-
"""t338 (A8 du lot Scenario, 29/10/2026) — la COUVERTURE d'un plan, depuis la même scène du Plateau. PUR : des
nombres entrent, des caméras sortent (banc tests/test_scene3d_couverture.py, attendus recalculés à la main).

Chez scenario.com (« one take, many angles ») une performance est recoupée en plusieurs angles, une focale par angle.
Ici, depuis la caméra du plan (son premier keyframe, sinon la caméra courante), trois caméras NOMMÉES :

  * PLAN LARGE — même axe de visée, focale 24 mm (ou plus large si le plan l'est déjà), le sujet et son interlocuteur
    ENTIERS dans le cadre (encombrement 0,40 : la plus grande des demi-étendues verticale et horizontale du cadre) ;
  * CONTRE-CHAMP — avec un interlocuteur : la caméra passe du côté du sujet et regarde l'interlocuteur. RÈGLE DES
    180° : l'axe d'action est la droite sujet ↔ interlocuteur (au sol) ; la caméra du contre-champ est le SYMÉTRIQUE de
    celle du plan par le plan médiateur de cet axe, qui garde la distance à l'axe ET le côté — les regards restent
    raccord (l'un regarde à gauche, l'autre à droite). L'interlocuteur est cadré à la taille du sujet dans le plan
    d'origine. Une caméra du plan posée SUR l'axe n'a pas de côté : c'est dit (avertissement), rien n'est inventé.
    Sans interlocuteur : le contrechamp de la caméra, 180° autour du sujet, même distance, même focale ;
  * GROS PLAN — sur le sujet (ou l'instance choisie), même direction, focale 85 mm (ou plus longue si le plan l'est),
    h = 0,85 : le seuil « close-up » de scene3d.SEUILS, que la mesure du Plateau relit à l'identique.

La distance est CHERCHÉE (dichotomie, 60 pas) sur la projection exacte de scene3d.projeter : pas d'approximation du
petit angle. L'interlocuteur choisi d'office est la capsule ou l'entité de la bible la plus proche du sujet, jamais un
repère ni un faisceau ; `partenaire_id=""` force « aucun ».
"""
import math

from app.services import previs_palette as PP
from app.services import scene3d as S

FOCALE_LARGE = 24.0
FOCALE_GROS_PLAN = 85.0
ENCOMBREMENT_LARGE = 0.40
H_GROS_PLAN = 0.85
EXPLICATION_180 = ("Règle des 180° : l'axe d'action relie le sujet à son interlocuteur ; toutes les caméras restent du "
                   "même côté de cet axe, pour que les regards et les directions restent raccord d'un plan à l'autre.")


def centre(inst) -> list:
    cs = S.coins(inst)
    return [sum(p[i] for p in cs) / 8 for i in range(3)]


def _unit(v):
    n = math.sqrt(sum(x * x for x in v))
    if n < 1e-9:
        raise ValueError("direction nulle.")
    return [x / n for x in v]


def orbite_de(pos, target, theta_prec=None) -> list:
    """Position caméra → [θ°, φ°, r] (convention de scene3d), θ prolongé au plus près de `theta_prec`."""
    d = [pos[i] - target[i] for i in range(3)]
    r = math.sqrt(sum(x * x for x in d))
    if r < 1e-9:
        raise ValueError("caméra confondue avec sa cible.")
    ph = math.degrees(math.acos(max(-1.0, min(1.0, d[1] / r))))
    th = math.degrees(math.atan2(d[0], d[2]))
    if theta_prec is not None:
        th += 360 * round((theta_prec - th) / 360)
    return [th, ph, r]


def _etendues(points, cam, asp):
    pr = S.projeter(points, cam, asp)
    devant = [p for p in pr if p[0] is not None]
    if len(devant) < len(pr):
        return math.inf, math.inf, False
    ys, xs = [p[1] for p in devant], [p[0] for p in devant]
    dedans = all(abs(v) <= 1 for v in xs + ys)
    return (max(ys) - min(ys)) / 2, (max(xs) - min(xs)) / 2, dedans


def _camera(target, direction, r, fov, theta_prec):
    p = [target[i] + direction[i] * r for i in range(3)]
    return {"orbit": orbite_de(p, target, theta_prec), "target": list(target), "fov": fov}


def _distance(points, target, direction, fov, asp, cible, mode, theta_prec):
    """La distance où la métrique vaut `cible` (« y » : demi-étendue verticale ; « max » : la plus grande des deux)."""
    def met(r):
        h, w, _d = _etendues(points, _camera(target, direction, r, fov, theta_prec), asp)
        return h if mode == "y" else max(h, w)
    lo, hi = 0.05, 2000.0
    for _ in range(60):
        mi = math.sqrt(lo * hi)
        if met(mi) > cible:
            lo = mi
        else:
            hi = mi
    return math.sqrt(lo * hi)


def _angle(ph):
    return "eye-level" if 80 <= ph <= 100 else ("high angle" if ph < 80 else "low angle")


def _sortie(id_, nom, tete, cam, sujet, asp, cap, cible):
    h, _w, dedans = _etendues(S.coins(sujet), cam, asp)
    f = S.focale_de_fov(cam["fov"], cap)
    o = cam["orbit"]
    return {"id": id_, "nom": nom, "camera": {"orbit": list(o), "target": list(cam["target"]), "fov": cam["fov"]},
            "focale_mm": round(f, 3), "h": round(h, 4), "shot_type": S.type_de_plan(h), "dans_cadre": dedans,
            "prompt": f"{tete}, static, locked-off shot at {o[2]:.1f} m, {_angle(o[1])}, {f:.0f} mm",
            "cible_id": cible.get("id"), "cible": PP.libelle(cible)}


def _par_id(instances, iid, quoi):
    for i in instances:
        if i.get("id") == iid:
            return i
    raise ValueError(f"{quoi} inconnu dans la scène : {iid}.")


def partenaire_d_office(instances, sujet):
    """La capsule ou l'entité de la bible la plus proche du sujet (au sol), hors repères et faisceaux."""
    a = centre(sujet)
    cands = [i for i in instances if i is not sujet and i.get("id") != sujet.get("id") and i.get("role") != "repere"
             and not PP.est_faisceau(i) and ((i.get("source") or {}).get("forme") == "capsule" or i.get("entity_id"))
             and i.get("dims")]
    if not cands:
        return None
    return min(cands, key=lambda i: (math.hypot(centre(i)[0] - a[0], centre(i)[2] - a[2]), str(i.get("id"))))


def couverture(scene, camera, partenaire_id=None, gros_plan_id=None) -> dict:
    """{cameras: [large, contrechamp, gros_plan], partenaire, regle_180}. ValueError : sujet absent, cible inconnue."""
    insts = [i for i in (scene or {}).get("instances") or [] if isinstance(i, dict)]
    sujet = S.sujet(scene)
    if sujet.get("dims") is None:
        raise ValueError("le sujet n'a pas encore de dimensions (maillage non mesuré).")
    asp = S.aspect_de(scene)
    cap = S._num((scene or {}).get("capteur_mm", 14.2), "capteur", 0, strict=True)
    cam0 = {"orbit": S._vec(camera["orbit"], "orbit"), "target": S._vec(camera["target"], "target"),
            "fov": S._num(camera.get("fov"), "fov", 0, strict=True)}
    p0 = S.position_camera(cam0["orbit"], cam0["target"])
    th0 = cam0["orbit"][0]
    if partenaire_id is None:
        part = partenaire_d_office(insts, sujet)
    elif partenaire_id == "":
        part = None
    else:
        part = _par_id(insts, partenaire_id, "interlocuteur")
        if part is sujet or part.get("id") == sujet.get("id"):
            raise ValueError("l'interlocuteur doit être une autre instance que le sujet.")
        if part.get("dims") is None:
            raise ValueError("l'interlocuteur n'a pas encore de dimensions.")
    gp = sujet if not gros_plan_id else _par_id(insts, gros_plan_id, "cible du gros plan")
    if gp.get("dims") is None:
        raise ValueError("la cible du gros plan n'a pas encore de dimensions.")
    a = centre(sujet)
    nom_s = PP.libelle(sujet)

    # ── plan large ──
    fov_l = max(cam0["fov"], S.fov_de_focale(FOCALE_LARGE, cap))
    pts = S.coins(sujet) + (S.coins(part) if part else [])
    cible_l = [(x + y) / 2 for x, y in zip(a, centre(part))] if part else a
    dir_l = _unit([p0[i] - cible_l[i] for i in range(3)])
    r_l = _distance(pts, cible_l, dir_l, fov_l, asp, ENCOMBREMENT_LARGE, "max", th0)
    large = _sortie("large", "Plan large", "wide shot", _camera(cible_l, dir_l, r_l, fov_l, th0), sujet, asp, cap, sujet)

    # ── contre-champ ──
    regle = {"axe": None, "cote_base": None, "cote_contrechamp": None, "respectee": None,
             "explication": EXPLICATION_180, "avertissement": None}
    if part:
        b = centre(part)
        u = _unit([b[0] - a[0], 0.0, b[2] - a[2]])
        m = [(a[i] + b[i]) / 2 for i in range(3)]
        k = sum((p0[i] - m[i]) * u[i] for i in range(3))
        p1 = [p0[i] - 2 * k * u[i] for i in range(3)]              # symétrique par le plan médiateur de l'axe

        def cote(p):
            v = u[0] * (p[2] - a[2]) - u[2] * (p[0] - a[0])
            return 0 if abs(v) < 1e-6 else (1 if v > 0 else -1)
        h0 = _etendues(S.coins(sujet), cam0, asp)[0]
        h0 = h0 if math.isfinite(h0) and h0 > 1e-3 else 0.5
        dir_k = _unit([p1[i] - b[i] for i in range(3)])
        r_k = _distance(S.coins(part), b, dir_k, cam0["fov"], asp, h0, "y", th0 + 180)
        cam_k = _camera(b, dir_k, r_k, cam0["fov"], th0 + 180)
        cb, ck = cote(p0), cote(S.position_camera(cam_k["orbit"], cam_k["target"]))
        regle.update(axe=[sujet.get("id"), part.get("id")], cote_base=cb, cote_contrechamp=ck,
                     respectee=bool(cb) and cb == ck)
        if not cb:
            regle["avertissement"] = ("la caméra du plan est SUR l'axe sujet ↔ interlocuteur : elle n'a pas de côté. "
                                      "Décalez-la d'un côté puis régénérez la couverture.")
        nom_p = PP.libelle(part)
        contre = _sortie("contrechamp", f"Contre-champ — {nom_p}", f"reverse shot on {nom_p}", cam_k, part, asp, cap,
                         part)
    else:
        o = cam0["orbit"]
        cam_k = {"orbit": [o[0] + 180, o[1], o[2]], "target": list(cam0["target"]), "fov": cam0["fov"]}
        contre = _sortie("contrechamp", "Contre-champ", "reverse angle", cam_k, sujet, asp, cap, sujet)

    # ── gros plan ──
    c = centre(gp)
    fov_g = min(cam0["fov"], S.fov_de_focale(FOCALE_GROS_PLAN, cap))
    try:
        dir_g = _unit([p0[i] - c[i] for i in range(3)])
    except ValueError:
        dir_g = _unit([p0[i] - cam0["target"][i] for i in range(3)])
    r_g = _distance(S.coins(gp), c, dir_g, fov_g, asp, H_GROS_PLAN, "y", th0)
    nom_g = PP.libelle(gp)
    gros = _sortie("gros_plan", f"Gros plan — {nom_g}", f"close-up on {nom_g}", _camera(c, dir_g, r_g, fov_g, th0),
                   gp, asp, cap, gp)
    return {"cameras": [large, contre, gros], "partenaire": part.get("id") if part else None, "sujet": sujet.get("id"),
            "sujet_nom": nom_s, "regle_180": regle}
