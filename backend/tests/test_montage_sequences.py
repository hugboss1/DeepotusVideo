# -*- coding: utf-8 -*-
"""t117 — PLUSIEURS SÉQUENCES : transitions et vitesse sur les pistes vidéo HAUTES (plein cadre et incrustation).
Banc-MIROIR : on lit le FICHIER rendu (images décodées), jamais le code qui prétend le produire.

LES SOURCES DISENT CE QU'ELLES SONT : `a.mp4` porte son numéro d'image dans le ROUGE (R = 4·N), `b.mp4` dans le VERT
(G = 4·N), à 10 i/s ; V1 est BLEU uni. Une couleur lue dans le rendu dit donc quelle image de quelle source est là.

[1] fondu plein cadre : A [1,3[ puis B [3,5[ en contact, fondu 0,8 s — V1 visible avant / après la piste ; A puis B
    à leur place, aux bonnes images de source ; au centre de la jonction, MÉLANGE de A et B et AUCUN bleu (pas de
    trou transparent pendant le fondu : les deux toiles sont opaques) ; durée = timeline.
[2] trou TRANSPARENT et vitesse : A [1,2[, B [3,4.5[ ×2 — dans le trou, V1 (bleu) et non du noir ; B avance de DEUX
    images de source par image rendue ; la durée timeline de B ne change pas.
[3] incrustation sans HALO : deux pièces rouges réduites (0,5) à gauche puis à droite, fondu 1 s — à mi-fondu la
    pièce de gauche est du rouge à 50 % sur le bleu (≈ 128,0,128) ; sans prémultiplication, xfade rendait ≈ 64 de
    rouge (MESURÉ 06/10, voir le plan).
[4] identité : une piste haute SANS transition ni vitesse → commande identique à l'octet à celle d'avant (champ
    `tr` ajouté ou non) ; témoin : la même piste AVEC un fondu change la commande.
[5] la ROUTE : un plan haut garde `transition`, `transition_s`, `speed` (bornée comme V1) et `tr` ; sans eux, les
    clés sont ABSENTES.
Run : & $PY tests/test_montage_sequences.py   (depuis backend/)"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TMP = tempfile.mkdtemp(prefix="dzseq_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(TMP, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


FF = shutil.which("ffmpeg")
if not FF:
    print("SKIP: ffmpeg introuvable"); sys.exit(0)

from app.config import settings                      # noqa: E402
from app.services import montage_service as MS       # noqa: E402

W, H, FPS = 64, 36, 10
SRC = settings.outputs_path / "seq_src"
SRC.mkdir(parents=True, exist_ok=True)


def fabrique(nom, geq, d=8):
    p = SRC / nom
    subprocess.run([FF, "-v", "error", "-y", "-f", "lavfi", "-i", f"nullsrc=s={W}x{H}:r={FPS}:d={d}",
                    "-vf", f"geq={geq},format=yuv444p", "-c:v", "libx264", "-qp", "0", str(p)], check=True)
    return p


V1P = fabrique("bleu.mp4", "r=0:g=0:b=255")
AP = fabrique("a.mp4", "r='min(255,4*N)':g=0:b=0")
BP = fabrique("b.mp4", "r=0:g='min(255,4*N)':b=0")
RP = fabrique("rouge.mp4", "r=255:g=0:b=0")
VP = fabrique("vert.mp4", "r=0:g=255:b=0")


def v1(d=8.0):
    return [{"path": V1P, "src_dur": 8.0, "src_in": 0.0, "start": 0.0, "end": d, "transition": None,
             "transition_s": None, "speed": 0.0, "dz": None, "reframe": None, "retime": None, "stab": None,
             "effects": None}]


def ov(path, st, en, src_in=0.0, tr="v2", tf=None, **kw):
    o = {"path": path, "is_image": False, "src_dur": 8.0, "src_in": src_in, "start": st, "end": en,
         "opacity": None, "tf": tf, "mp": None, "layer": 0, "tr": tr}
    o.update(kw)
    return o


def build(v2, d=8.0):
    out = str(pathlib.Path(TMP) / f"r{abs(hash(json.dumps(v2, default=str)))}.mp4")
    cmd, total = MS._build_montage_command(v1(d), v2, [], None, w=W, h=H, fps=FPS, mix_db={}, ducking=False,
                                           duration_master=False, preview=False, out=out)
    return cmd, total, out


def rendre(v2, d=8.0):
    cmd, total, out = build(v2, d)
    r = subprocess.run([FF] + cmd[1:], capture_output=True, text=True)
    if r.returncode:
        return {"err": r.stderr[-400:], "total": total}
    raw = subprocess.run([FF, "-v", "error", "-i", out, "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    fs = W * H * 3
    return {"n": len(raw) // fs, "total": total, "raw": raw, "fs": fs}


def px(res, t, x=W // 2, y=H // 2):
    """moyenne RGB d'un carré 4×4 autour de (x, y), à l'image de l'instant t"""
    if "raw" not in res:
        return None
    i = int(round(t * FPS))
    if i >= res["n"]:
        return None
    base = i * res["fs"]
    acc = [0, 0, 0]
    for yy in range(y - 2, y + 2):
        for xx in range(x - 2, x + 2):
            o = base + (yy * W + xx) * 3
            for c in range(3):
                acc[c] += res["raw"][o + c]
    return tuple(round(v / 16) for v in acc)


def near(a, b, tol=12):
    return a is not None and all(abs(x - y) <= tol for x, y in zip(a, b))


print("\n[0] témoins : les sources disent ce qu'elles sont")
r0 = rendre([])
check("temoin_v1_seul_est_bleu_et_dure_8_s", r0.get("n") == 80 and near(px(r0, 4.0), (0, 0, 255)), (r0.get("n"), px(r0, 4.0), r0.get("err")))
ra = rendre([ov(AP, 0, 8)])
check("temoin_a_porte_son_image_dans_le_rouge", near(px(ra, 2.0), (80, 0, 0), 8) and near(px(ra, 5.0), (200, 0, 0), 8),
      (px(ra, 2.0), px(ra, 5.0)))

print("\n[1] fondu plein cadre entre deux plans en contact")
r1 = rendre([ov(AP, 1, 3, src_in=1.0), ov(BP, 3, 5, src_in=1.0, transition="fade", transition_s=0.8)])
check("f1_rendu_et_duree_timeline", r1.get("n") == 80 and r1.get("total") == 8.0, (r1.get("n"), r1.get("total"), r1.get("err")))
check("f1_v1_visible_avant_et_apres_la_piste", near(px(r1, 0.5), (0, 0, 255)) and near(px(r1, 5.5), (0, 0, 255)),
      (px(r1, 0.5), px(r1, 5.5)))
# A au temps 2,0 : local 1,0 + src_in 1,0 → source 2,0 s → image 20 → R = 80
check("f1_a_a_sa_place_a_la_bonne_image", near(px(r1, 2.0), (80, 0, 0), 10), px(r1, 2.0))
# B au temps 4,6 : local 1,6 + 1,0 → image 26 → G = 104
check("f1_b_a_sa_place_a_la_bonne_image", near(px(r1, 4.6), (0, 104, 0), 10), px(r1, 4.6))
m = px(r1, 3.0)
# au centre : moitié de A (poignée RÉELLE : source 3,0 s → R 120 → 60) et moitié de B (source 1,0 s → G 40 → 20)
check("f1_au_centre_de_la_jonction_melange_de_a_et_b", m is not None and 40 <= m[0] <= 80 and 10 <= m[1] <= 30, m)
check("f1_aucun_bleu_pendant_le_fondu_(pas_de_trou)", m is not None and m[2] <= 12 and px(r1, 2.7)[2] <= 12
      and px(r1, 3.3)[2] <= 12, (px(r1, 2.7), m, px(r1, 3.3)))
cmd1 = " ".join(build([ov(AP, 1, 3, src_in=1.0), ov(BP, 3, 5, src_in=1.0, transition="fade", transition_s=0.8)])[0])
_c1 = build([ov(AP, 1, 3, src_in=1.0), ov(BP, 3, 5, src_in=1.0, transition="fade", transition_s=0.8)])[0]
_ib = _c1.index(str(BP))
# B entre à 1,0 s de source avec une amorce de 0,4 s : sa poignée RÉELLE est lue dans la source dès 0,6 s (loi de V1)
check("f1_la_poignee_de_b_est_lue_dans_la_source_(pas_figee)",
      "-ss" in _c1[_ib - 5:_ib] and _c1[_c1.index("-ss", _ib - 5) + 1] == "0.6", _c1[_ib - 5:_ib + 1])
check("f1_la_commande_premultiplie_puis_deprepremultiplie_une_fois",
      cmd1.count("premultiply=inplace=1") >= 2 and cmd1.count("unpremultiply=inplace=1") == 1 and "xfade=transition=fade" in cmd1,
      cmd1[:200])

print("\n[2] trou transparent et vitesse ×2")
r2 = rendre([ov(AP, 1, 2), ov(BP, 3, 4.5, speed=2.0)])
check("v2_rendu", r2.get("n") == 80, (r2.get("n"), r2.get("err")))
check("v2_le_trou_laisse_voir_v1_(bleu,_pas_noir)", near(px(r2, 2.5), (0, 0, 255)), px(r2, 2.5))
g1, g2 = px(r2, 3.2), px(r2, 3.7)
# ×2 : 0,5 s rendue = 1,0 s de source = 10 images = 40 de vert
check("v2_b_avance_de_deux_images_de_source_par_image_rendue", g1 and g2 and 32 <= g2[1] - g1[1] <= 48, (g1, g2))
check("v2_b_a_la_bonne_image_et_garde_sa_place", near(px(r2, 4.0), (0, 80, 0), 10) and near(px(r2, 4.7), (0, 0, 255)),
      (px(r2, 4.0), px(r2, 4.7)))

print("\n[3] incrustation qui fond d'une place à l'autre, sans halo")
G = {"x": 0.25, "y": 0.5, "scale": 0.5, "rotate": 0.0}
D = {"x": 0.75, "y": 0.5, "scale": 0.5, "rotate": 0.0}
r3 = rendre([ov(RP, 1, 3, tf=G), ov(RP, 3, 5, tf=D, transition="fade", transition_s=1.0)])
check("i3_rendu", r3.get("n") == 80, (r3.get("n"), r3.get("err")))
check("i3_avant_le_fondu_rouge_a_gauche_bleu_a_droite", near(px(r3, 2.0, 16), (255, 0, 0), 14) and near(px(r3, 2.0, 48), (0, 0, 255), 14),
      (px(r3, 2.0, 16), px(r3, 2.0, 48)))
mg, md = px(r3, 3.0, 16), px(r3, 3.0, 48)
check("i3_a_mi_fondu_rouge_a_50_pourcent_sur_le_bleu_des_deux_cotes_(pas_de_halo)",
      mg and md and 110 <= mg[0] <= 150 and 105 <= mg[2] <= 150 and 110 <= md[0] <= 150, (mg, md))
check("i3_apres_le_fondu_rouge_a_droite_bleu_a_gauche", near(px(r3, 4.0, 48), (255, 0, 0), 14) and near(px(r3, 4.0, 16), (0, 0, 255), 14),
      (px(r3, 4.0, 48), px(r3, 4.0, 16)))

# deux toiles d'alpha DIFFÉRENTS : rouge opaque → vert à 50 %. Prémultiplié (juste) : à mi-fondu (0,5 ; 0,25 ; 0 ;
# α 0,75) → sur le bleu (128, 64, 64). Sans prémultiplier, xfade mélange les couleurs droites : vert ≈ 128 (faux).
r3b = rendre([ov(RP, 1, 3, tf=G), ov(VP, 3, 5, tf=G, opacity=0.5, transition="fade", transition_s=1.0)])
mb = px(r3b, 3.0, 16)
check("i3_rouge_opaque_vers_vert_a_50_pourcent_le_vert_a_mi_fondu_est_premultiplie",
      r3b.get("n") == 80 and mb is not None and 45 <= mb[1] <= 85 and 105 <= mb[0] <= 150, (mb, r3b.get("err")))

print("\n[4] identité : sans transition ni vitesse, rien ne bouge")
sans_tr = [{k: v for k, v in o.items() if k != "tr"} for o in (ov(AP, 1, 3), ov(BP, 3, 5))]
avec_tr = [ov(AP, 1, 3), ov(BP, 3, 5)]
c_sans, c_avec = build(sans_tr)[0], build(avec_tr)[0]
c_fondu = build([ov(AP, 1, 3), ov(BP, 3, 5, transition="fade")])[0]
check("id4_temoin_avec_un_fondu_la_commande_change", "xfade=transition=fade" in " ".join(c_fondu) and c_fondu != c_avec)
check("id4_piste_haute_sans_transition_ni_vitesse_commande_identique_a_l_octet",
      c_avec[:-1] == c_sans[:-1] and "premultiply" not in " ".join(c_avec), (len(c_avec), len(c_sans)))
c_coupe = build([ov(AP, 1, 2), ov(BP, 3, 5, transition="fade")])[0]
check("id4_un_fondu_entre_plans_NON_en_contact_est_une_coupe_(chemin_historique)",
      "premultiply" not in " ".join(c_coupe) and "overlay" in " ".join(c_coupe))

print("\n[6] J1 : fondus du clip d'ajustement (sa « transition »)")
_aj = {"start": 2.0, "end": 6.0, "effects": [{"type": "invert"}]}
b0 = MS._adjust_bounded(dict(_aj), 8.0)
b1 = MS._adjust_bounded(dict(_aj, fade_in=2.0, fade_out=1.0), 8.0)
check("j6_temoin_sans_fondu_l_effet_n_a_pas_de_fondu", len(b0) == 1 and b0[0]["t0"] == 2.0 and "fade_in" not in b0[0], b0)
check("j6_le_fondu_du_clip_va_aux_effets_qui_commencent_et_finissent_avec_lui",
      len(b1) == 1 and b1[0].get("fade_in") == 2.0 and b1[0].get("fade_out") == 1.0, b1)
b2 = MS._adjust_bounded({"start": 2.0, "end": 6.0, "fade_in": 1.0,
                         "effects": [{"type": "invert", "t0": 1.0, "t1": 4.0, "fade_in": 0.2}]}, 8.0)
check("j6_un_effet_qui_ne_commence_pas_avec_le_clip_garde_son_propre_fondu",
      len(b2) == 1 and b2[0]["t0"] == 3.0 and b2[0].get("fade_in") == 0.2, b2)
b3 = MS._adjust_bounded({"start": 2.0, "end": 6.0, "fade_in": 0.5,
                         "effects": [{"type": "invert", "fade_in": 1.5}]}, 8.0)
check("j6_le_plus_long_des_deux_fondus_gagne", len(b3) == 1 and b3[0].get("fade_in") == 1.5, b3)


def rendre_aj(aj):
    out = str(pathlib.Path(TMP) / f"j{abs(hash(json.dumps(aj)))}.mp4")
    cmd, _t = MS._build_montage_command(v1(), [], [], None, w=W, h=H, fps=FPS, mix_db={}, ducking=False,
                                        duration_master=False, preview=False, out=out, adjust_clips=[aj])
    r = subprocess.run([FF] + cmd[1:], capture_output=True, text=True)
    if r.returncode:
        return {"err": r.stderr[-300:]}
    raw = subprocess.run([FF, "-v", "error", "-i", out, "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    return {"n": len(raw) // (W * H * 3), "raw": raw, "fs": W * H * 3}


rj0, rj1 = rendre_aj(dict(_aj)), rendre_aj(dict(_aj, fade_in=2.0))
# invert : bleu (0,0,255) → jaune (255,255,0). Sans fondu, plein dès 2,2 s ; avec 2 s de fondu, à mi-chemin à 3,0 s.
check("j6_rendu_sans_fondu_inverse_des_l_entree", near(px(rj0, 2.2), (255, 255, 0), 14) and near(px(rj0, 1.5), (0, 0, 255)),
      (px(rj0, 2.2), px(rj0, 1.5), rj0.get("err")))
mj = px(rj1, 3.0)
# la rampe suit la courbe PAR DÉFAUT des fondus d'effet (`smooth` de animation_service : 0,776 à mi-course, MESURÉ
# 06/10) — l'attendu est calculé depuis elle, pas supposé linéaire
from app.services.animation_service import ease as _ease   # noqa: E402
_u = _ease("smooth", 0.5)
_att = (round(255 * _u), round(255 * _u), round(255 * (1 - _u)))
check("j6_rendu_avec_fondu_suit_la_courbe_a_mi_chemin_puis_plein", near(mj, _att, 14)
      and near(px(rj1, 4.5), (255, 255, 0), 14), (mj, _att, px(rj1, 4.5), rj1.get("err")))

print("\n[5] la route garde transition, durée et vitesse d'un plan haut")
from fastapi.testclient import TestClient            # noqa: E402
from app.main import app                             # noqa: E402
_cap = {}
_vrai_build, _vrai_run = MS._build_montage_command, MS._run_ffmpeg


def _espion(*a, **k):
    _cap["v2"] = a[1] if len(a) > 1 else None
    _cap["aj"] = k.get("adjust_clips")
    return _vrai_build(*a, **k)


def corps(extra_b):
    return {"name": "seq", "ratio": "16:9", "preview": True, "duration_master": False,
            "tracks": [{"id": "v2", "kind": "video"}, {"id": "v1", "kind": "video"}],
            "clips": [{"tr": "v1", "src": {"file_path": str(V1P)}, "start": 0, "end": 6, "srcIn": 0, "transition": "cut"},
                      {"tr": "v2", "src": {"file_path": str(AP)}, "start": 1, "end": 3, "srcIn": 0},
                      dict({"tr": "v2", "src": {"file_path": str(BP)}, "start": 3, "end": 5, "srcIn": 0}, **extra_b)]}


with TestClient(app) as cli:
    MS._build_montage_command, MS._run_ffmpeg = _espion, (lambda cmd, out: None)
    try:
        rr = cli.post("/api/montage/render", json=corps({"transition": "wipeleft", "transition_s": 0.6, "speed": 9}))
        b_avec = [o for o in (_cap.get("v2") or []) if str(o.get("path", "")).endswith("b.mp4")]
        _cap.clear()
        rr0 = cli.post("/api/montage/render", json=corps({}))
        b_sans = [o for o in (_cap.get("v2") or []) if str(o.get("path", "")).endswith("b.mp4")]
        _cj = corps({})
        _cj["tracks"].insert(0, {"id": "j1", "kind": "adjust"})
        _cj["clips"] += [{"tr": "j1", "kind": "adjust", "start": 1, "end": 4, "fade_in": 0.5, "fade_out": True,
                          "effects": [{"type": "invert"}]},
                         {"tr": "j1", "kind": "adjust", "start": 4.5, "end": 5.5, "effects": [{"type": "invert"}]}]
        _cap.clear()
        rrj = cli.post("/api/montage/render", json=_cj)
        aj_cap = _cap.get("aj") or []
    finally:
        MS._build_montage_command, MS._run_ffmpeg = _vrai_build, _vrai_run
check("r5_la_route_garde_transition_duree_et_vitesse_bornee_comme_v1",
      rr.status_code == 200 and len(b_avec) == 1 and b_avec[0].get("transition") == "wipeleft"
      and b_avec[0].get("transition_s") == 0.6 and b_avec[0].get("speed") == 4.0 and b_avec[0].get("tr") == "v2",
      (rr.status_code, b_avec))
check("r5_sans_eux_les_cles_sont_absentes",
      rr0.status_code == 200 and len(b_sans) == 1 and "path" in b_sans[0] and b_sans[0].get("tr") == "v2"
      and not ({"transition", "transition_s", "speed"} & set(b_sans[0])), (rr0.status_code, b_sans))

# `fade_out: True` (un booléen) est refusé : ce n'est pas une durée
check("r5_les_fondus_d_un_clip_j1_arrivent_au_rendu_et_sont_absents_sans_eux",
      rrj.status_code == 200 and len(aj_cap) == 2 and aj_cap[0].get("fade_in") == 0.5
      and "fade_out" not in aj_cap[0] and "effects" in aj_cap[1] and not ({"fade_in", "fade_out"} & set(aj_cap[1])),
      (rrj.status_code, aj_cap))

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
