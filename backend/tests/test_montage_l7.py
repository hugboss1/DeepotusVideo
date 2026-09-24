# -*- coding: utf-8 -*-
"""L7 — LIVRAISON cote backend (D-19 coins arrondis et ombre portee sur un
overlay). En-tete recopie de test_montage_l4.py (env, check, A, V1SPEC/FLAT,
OVBUILD de test_montage_l3.py) : dossier de donnees NEUF par execution, toute
lecture gardee — un banc qui meurt sur un acces nu ne dit pas quelles
assertions manquent.
Run : & $PY tests/test_montage_l7.py   (depuis backend/)

[1] D-19 `_ov_transform` : deux champs de plus dans `spec` — `radius` (px,
entier 0..200 par `int(round())`, invalide → 0 avec warning) et `shadow`
(0|1 : vrai numerique ≥ 0,5 ou True → 1). Poses SANS x/y/scale/rotate, ils
rendent tout de meme `tf` non-None (`{x:.5,y:.5,scale:1,rotate:0,radius,
shadow}`) : la chaine AVEC transformation est necessaire (ECART DATE
24/09/2026 : un overlay historique « cover » qui ne recoit qu'un rayon passe
en chaine transformee plein cadre, c'est le prix). Absents → tf None
(temoin : la chaine cover reste octet pour octet celle de L3).
[2] CHAINE. `radius` → UN maillon `geq=` place apres l'opacite
(colorchannelmixer / format=rgba) et AVANT `rotate=`, dont le rayon est
borne DANS l'expression par `min(R,min(W/2,H/2))` (ECART DATE 24/09/2026 :
le plan ecrit `min(R,W/2,H/2)` — MESURE ffmpeg 8.1.1 : `min` n'accepte que
DEUX arguments, « Error initializing filters » ; la forme imbriquee passe).
REVUE 24/09/2026 (B-1) : le rayon du client est en px du canvas natif
(petit cote 1080, ou 1920 en paysage) et w/h sont ceux du RENDU (apercu =
canvas/4, preset 2160) → `rrad = max(1, round(radius·k))`, k = w/1080 si
w ≤ h sinon w/1920 (`ratio` n'est PAS connu de `_build_montage_command` :
mesure, la signature ne le porte pas) : radius 40 → 40 en 1080x1920, 10 en
270x480, 2 en 64x64. COUT DATE (B-3, revue 24/09/2026, 1080p) : geq ≈
0,105 s/image, ×29 la chaine nue ; masque statique par `alphamerge` note
pour L7-B, pas fait. `shadow` → le maillon `[idx:v]{och}[ov{j}]` devient
cinq : `[oa{j}]`, `split[oo{j}][os{j}]`, `pad=iw+6u:ih+6u:3u:3u` (l'image),
`colorchannelmixer rr=0:gg=0:bb=0:aa=0.55,pad=…:4u:4u,boxblur=u` (l'ombre,
decalee de u PUIS floutee — B-2 : boxblur AVANT pad floutait un alpha
constant dans son propre cadre, mesure alpha 0 → 140 sur 1 px ; apres pad
le degrade existe : colonne mediane d'une ombre 240x140 u=2, alpha
140,140,134,123,106,84,62,50 de y=140 a 147 ; RE-REVUE R-1 : canvas +6u, marge
droite/bas 2u ≥ u+1 pour que le degrade ne soit jamais coupe — a +4u le
dernier rang valait alpha 75/51/41 puis 0, ressaut de 16 % ; a +6u 17/5/1),
u = max(1, round(6·k)) ;
`[osp{j}][op{j}]overlay=0:0:format=auto[ov{j}]` (B-4, rgba conserve) — le
label final `[ov{j}]` et le maillon de composition sont INCHANGES. `setpts` est dans `och` : le split herite du
meme PTS des deux cotes (mesure [M]). Sans les deux champs → chaine octet
pour octet identique (temoin). Chaine « cover » (tf None, `radius` pose
sur le dict overlay mais pas dans tf) et echelle animee (`zp`, D-14) →
ignores avec warning.
[M] MESURE ffmpeg REELLE (SKIP si absent) : 2 s, fond `color=c=blue`
480x270 (k = 0,25 : rayon 60 → 15 px, u = 2), overlay PNG rouge 240x140 en
`radius=60, shadow=1` (scale 0,5 → ow2 240, image posee en (120,65), pad
252x152 en (114,59), ombre dure de (122,67) a (361,206), dernier rang du
canvas y=210) → rc 0, fichier
> 0 ; DEUX pixels lus par `ffmpeg -ss 1 … -vf crop=1:1:X:Y -f rawvideo
-pix_fmt rgb24 -` (format=rgb24 AVANT crop : en yuv420p un crop 1x1 a une
chroma de 0 px et ffmpeg refuse) : le coin de l'image (121,66) est BLEU (fond), le milieu
du bord haut (240,66) est ROUGE (overlay) ; un troisieme, 1 px sous le
bord bas (240,205), est un bleu ASSOMBRI (l'ombre dure, alpha 0,55) ; un
quatrieme HORS de l'emprise (240,225) ≈ fond ; un sixieme au DERNIER rang du
canvas padde (240,210) ≈ fond ± 8 (R-1) ; un cinquieme dans le degrade
(240,207) est STRICTEMENT entre l'ombre dure et le fond (B-2 : sans le
flou apres pad, ce pixel serait le fond).
Regle des assertions negatives : chaque « pas de X » est precede dans la
MEME expression du temoin positif qui prouve que la mesure a eu lieu.
"""
import os, sys, tempfile, subprocess, pathlib, shutil
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzl7_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.services import montage_service as MS           # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def A(nom, defaut):
    return getattr(MS, nom, defaut)


V1F = str(pathlib.Path(TMP) / "v1.mp4")
pathlib.Path(V1F).write_bytes(b"x")
OVF = str(pathlib.Path(TMP) / "ov.png")
pathlib.Path(OVF).write_bytes(b"x")


def V1SPEC(**kw):
    d = {"path": V1F, "src_dur": 4.0, "src_in": 0.0, "start": 0.0, "end": 4.0,
         "transition": "cut", "transition_s": 0.0, "speed": 0.0, "effects": None}
    d.update(kw)
    return d


def FLAT(cmd):
    return " ".join(cmd) if isinstance(cmd, list) else str(cmd)


def OVBUILD(w=64, h=64, **ov):
    """`_build_montage_command` avec un V1 et UN overlay V2 — recopie de
    tests/test_montage_l3.py ; `tf` passe TEL QUEL (deja valide) sauf si
    `raw=` est donne : le dict passe alors par MS._ov_transform comme /render."""
    o = {"path": OVF, "is_image": True, "src_dur": 0.0, "src_in": 0.0, "start": 1.0,
         "end": 3.0, "opacity": None, "tf": None, "mp": None, "layer": 0}
    mpts = ov.pop("motion_points", None)
    raw = ov.pop("raw", None)
    o.update(ov)
    if raw is not None:
        o["tf"] = MS._ov_transform(raw)
    if mpts is not None:
        o["mp"] = MS._motion_points({"start": o["start"], "end": o["end"], "motion_points": mpts})
    try:
        cmd, _ = MS._build_montage_command([V1SPEC()], [o], [], None, w=w, h=h, fps=25, mix_db={},
                                           ducking=False, duration_master=False, preview=True,
                                           out=os.path.join(TMP, "o.mp4"))
    except Exception as e:                 # faute n°6 : rougir, pas mourir
        return "%s: %s" % (type(e).__name__, e)
    return FLAT(cmd)


class _Journal:
    """Remplace MS.logger le temps d'un appel : capte les warning."""
    def __init__(self): self.msgs = []
    def warning(self, m, *a, **k): self.msgs.append(str(m))
    def __getattr__(self, k): return lambda *a, **k2: None


def _avec_journal(fn):
    _lg0, _jl = MS.logger, _Journal()
    MS.logger = _jl
    try:
        r = fn()
    except Exception as e:
        r = "%s: %s" % (type(e).__name__, e)
    finally:
        MS.logger = _lg0
    return r, _jl.msgs


def _seg(cmd, j=0):
    """Le morceau de la chaine overlay entre `[1:v]` et `[ov{j}]` inclus."""
    if not isinstance(cmd, str) or "[1:v]" not in cmd:
        return ""
    s = cmd[cmd.find("[1:v]"):]
    k = s.find("[ov%d]" % j)
    return s[:k + len("[ov%d]" % j)] if k >= 0 else s[:400]


print("\n[1] D-19 _ov_transform : radius (0..200 entier) et shadow (0|1)")
_ovt = A("_ov_transform", None)
def OVT(d):
    try:
        return _ovt(d) if callable(_ovt) else "ABSENT"
    except Exception as e:
        return "%s: %s" % (type(e).__name__, e)

_t1 = OVT({"x": .5, "y": .5, "scale": 1, "radius": 40, "shadow": 1})
check("d19_radius_40_et_shadow_1_sont_portes_par_tf",
      isinstance(_t1, dict) and _t1.get("radius") == 40 and _t1.get("shadow") == 1
      and isinstance(_t1["radius"], int) and isinstance(_t1["shadow"], int), _t1)
_t2 = OVT({"x": .5, "y": .5, "scale": 1})
check("d19_sans_les_deux_champs_tf_porte_radius_0_et_shadow_0_temoin_scale",
      isinstance(_t2, dict) and _t2.get("scale") == 1.0 and _t2.get("radius") == 0 and _t2.get("shadow") == 0, _t2)
check("d19_radius_999_borne_a_200_et_moins_1_a_0",
      (OVT({"x": .5, "radius": 999}) or {}).get("radius") == 200
      and (OVT({"x": .5, "radius": -1}) or {}).get("radius") == 0, (OVT({"x": .5, "radius": 999}), OVT({"x": .5, "radius": -1})))
check("d19_radius_est_arrondi_a_l_entier",
      (OVT({"x": .5, "radius": 39.6}) or {}).get("radius") == 40
      and (OVT({"x": .5, "radius": "25"}) or {}).get("radius") == 25, (OVT({"x": .5, "radius": 39.6}), OVT({"x": .5, "radius": "25"})))
_t3, _w3 = _avec_journal(lambda: OVT({"x": .5, "radius": "abc"}))
check("d19_radius_abc_retombe_a_0_avec_warning_temoin_x",
      isinstance(_t3, dict) and _t3.get("x") == 0.5 and _t3.get("radius") == 0
      and any("radius" in m and "invalide" in m for m in _w3), (_t3, _w3))
check("d19_shadow_True_1_2_valent_1_et_0_None_valent_0",
      all((OVT({"x": .5, "shadow": v}) or {}).get("shadow") == 1 for v in (True, "1", 2, 1, 0.5))
      and all((OVT({"x": .5, "shadow": v}) or {}).get("shadow") == 0 for v in (0, None, False, 0.4, "0")),
      [(v, (OVT({"x": .5, "shadow": v}) or {}).get("shadow")) for v in (True, "1", 2, 0, None, False, 0.4)])
_t4, _w4 = _avec_journal(lambda: OVT({"x": .5, "shadow": "oui"}))
check("d19_shadow_non_numerique_retombe_a_0_avec_warning",
      isinstance(_t4, dict) and _t4.get("shadow") == 0 and any("shadow" in m and "invalide" in m for m in _w4), (_t4, _w4))
_t5 = OVT({"radius": 30})
check("d19_radius_seul_rend_tf_par_defaut_centre_echelle_1_rotation_0",
      _t5 == {"x": 0.5, "y": 0.5, "scale": 1.0, "rotate": 0.0, "radius": 30, "shadow": 0}, _t5)
_t6 = OVT({"shadow": 1})
check("d19_shadow_seul_rend_tf_par_defaut",
      _t6 == {"x": 0.5, "y": 0.5, "scale": 1.0, "rotate": 0.0, "radius": 0, "shadow": 1}, _t6)
check("d19_radius_0_et_shadow_0_seuls_ne_rendent_PAS_tf_temoin_radius_1",
      OVT({"radius": 0, "shadow": 0}) is None and OVT({}) is None and OVT({"label": "a"}) is None
      and isinstance(OVT({"radius": 1}), dict), (OVT({"radius": 0, "shadow": 0}), OVT({"radius": 1})))

print("\n[2] D-19 chaine : geq apres l'opacite et avant rotate ; ombre en cinq maillons")
TF0 = {"x": .5, "y": .5, "scale": 1.0, "rotate": 0.0}
_c0 = OVBUILD(tf=dict(TF0))
_s0 = _seg(_c0)
check("d19_temoin_l3_la_chaine_transformee_sans_les_champs",
      _s0.startswith("[1:v]scale=64:-2,setsar=1,fps=25,format=rgba,setpts=PTS-STARTPTS+1.0/TB[ov0]")
      and "geq" not in _c0 and "split" not in _c0 and "boxblur" not in _c0, _s0)
check("d19_radius_0_et_shadow_0_dans_tf_laissent_la_chaine_octet_pour_octet",
      _c0.startswith("ffmpeg") and OVBUILD(tf=dict(TF0, radius=0, shadow=0)) == _c0
      and OVBUILD(raw={"x": .5, "y": .5, "scale": 1, "rotate": 0}) == _c0, _seg(OVBUILD(tf=dict(TF0, radius=0, shadow=0))))
def GEQ(r):
    return ("geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='alpha(X,Y)*(1-gt(hypot("
            "max(abs(X-W/2)-(W/2-min(%d,min(W/2,H/2))),0),"
            "max(abs(Y-H/2)-(H/2-min(%d,min(W/2,H/2))),0)),min(%d,min(W/2,H/2))))'" % (r, r, r))
GEQ40 = GEQ(40)
# Canvas natif 1080x1920 (k = 1) : le rayon du client passe tel quel.
_cr = OVBUILD(w=1080, h=1920, tf=dict(TF0, radius=40))
_sr = _seg(_cr)
check("d19_radius_40_pose_geq_une_fois_avec_min_imbrique_apres_format_rgba_et_avant_setpts",
      _sr.count("geq=") == 1 and GEQ40 in _sr and "min(40,W/2,H/2)" not in _sr
      and _sr.find("format=rgba,") < _sr.find("geq=") < _sr.find(",setpts=")
      and _sr.endswith("[ov0]") and "split" not in _sr and "boxblur" not in _sr, _sr)
# B-1 : le rayon suit l'echelle du rendu — apercu 270x480 (k = 0,25) → 10,
# 64x64 (k = 64/1080) → 2, paysage 1920x1080 (k = 1) → 40, 960x540 → 20.
check("d19_le_rayon_est_mis_a_l_echelle_du_rendu_10_en_270x480_et_2_en_64x64_temoin_40_en_1080",
      GEQ(10) in _seg(OVBUILD(w=270, h=480, tf=dict(TF0, radius=40)))
      and GEQ(2) in _seg(OVBUILD(w=64, h=64, tf=dict(TF0, radius=40)))
      and GEQ(40) in _seg(OVBUILD(w=1920, h=1080, tf=dict(TF0, radius=40)))
      and GEQ(20) in _seg(OVBUILD(w=960, h=540, tf=dict(TF0, radius=40)))
      and GEQ(40) in _sr and GEQ(10) not in _sr,
      (_seg(OVBUILD(w=270, h=480, tf=dict(TF0, radius=40)))[-160:], _seg(OVBUILD(w=64, h=64, tf=dict(TF0, radius=40)))[-160:]))
check("d19_un_rayon_minuscule_a_l_echelle_reste_1_px_jamais_0",
      GEQ(1) in _seg(OVBUILD(w=64, h=64, tf=dict(TF0, radius=1)))
      and "geq" not in _seg(OVBUILD(w=64, h=64, tf=dict(TF0, radius=0))), _seg(OVBUILD(w=64, h=64, tf=dict(TF0, radius=1)))[-120:])
_cro = OVBUILD(w=1080, h=1920, tf=dict(TF0, radius=40, rotate=30.0), opacity=0.5)
_sro = _seg(_cro)
check("d19_geq_vient_apres_colorchannelmixer_et_avant_rotate",
      _sro.count("geq=") == 1 and "colorchannelmixer=aa=0.5" in _sro and ",rotate=" in _sro
      and _sro.find("colorchannelmixer=aa=0.5,") < _sro.find("geq=") < _sro.find(",rotate="), _sro)
check("d19_le_rayon_est_le_literal_de_tf_temoin_40_vs_12",
      "min(12,min(W/2,H/2))" in _seg(OVBUILD(w=1080, h=1920, tf=dict(TF0, radius=12)))
      and "min(12," not in _sr and "min(40," in _sr, _seg(OVBUILD(w=1080, h=1920, tf=dict(TF0, radius=12))))
def OMBRE_U(u):
    return ("[oa0]split[oo0][os0];[oo0]pad=iw+%d:ih+%d:%d:%d:color=black@0[op0];"
            "[os0]colorchannelmixer=rr=0:gg=0:bb=0:aa=0.55,pad=iw+%d:ih+%d:%d:%d:color=black@0,boxblur=%d[osp0];"
            "[osp0][op0]overlay=0:0:format=auto[ov0]" % (6 * u, 6 * u, 3 * u, 3 * u, 6 * u, 6 * u, 4 * u, 4 * u, u))
OMBRE = OMBRE_U(6)
_cs = OVBUILD(w=1080, h=1920, tf=dict(TF0, shadow=1))
_ss = _seg(_cs)
check("d19_shadow_1_split_en_cinq_maillons_et_le_label_ov0_reste_final",
      _ss.startswith("[1:v]scale=1080:-2,setsar=1,fps=25,format=rgba,setpts=PTS-STARTPTS+1.0/TB[oa0];")
      and _ss.endswith(OMBRE) and "geq" not in _ss and _cs.count("[ov0]") == 2
      and "[ov0]overlay=x=540.0-w/2:y=960.0-h/2:eof_action=pass:enable='between(t,1.0,3.0)'[ob0]" in _cs, _ss)
# B-2 : le flou vient APRES le pad de l'ombre (sinon il floute un alpha
# constant dans son propre cadre) ; B-4 : format=auto sur l'overlay interne.
check("d19_l_ombre_est_paddee_PUIS_floutee_et_l_overlay_interne_garde_rgba",
      "aa=0.55,pad=" in _ss and ",boxblur=6[osp0]" in _ss and _ss.find(":color=black@0,boxblur=6") > _ss.find("aa=0.55,pad=")
      and "boxblur=6,pad=" not in _ss and "overlay=0:0:format=auto[ov0]" in _ss, _ss[-260:])
check("d19_l_unite_d_ombre_suit_l_echelle_2_en_480x270_et_1_au_plancher_64x64",
      _seg(OVBUILD(w=480, h=270, tf=dict(TF0, shadow=1))).endswith(OMBRE_U(2))
      and _seg(OVBUILD(w=64, h=64, tf=dict(TF0, shadow=1))).endswith(OMBRE_U(1))
      and _seg(OVBUILD(w=270, h=480, tf=dict(TF0, shadow=1))).endswith(OMBRE_U(2)),
      _seg(OVBUILD(w=480, h=270, tf=dict(TF0, shadow=1)))[-200:])
_c0k = OVBUILD(w=1080, h=1920, tf=dict(TF0))
check("d19_l_ombre_ne_change_pas_le_maillon_de_composition_temoin_l3",
      _c0k[_c0k.find("[ov0]overlay="):_c0k.find("[ob0]")] == _cs[_cs.find("[ov0]overlay="):_cs.find("[ob0]")]
      and "[ob0]" in _c0k and "[ob0]" in _cs, (_c0k[_c0k.find("[ov0]overlay="):_c0k.find("[ob0]")], _cs[_cs.find("[ov0]overlay="):_cs.find("[ob0]")]))
_cb = OVBUILD(w=1080, h=1920, tf=dict(TF0, radius=40, shadow=1))
_sb = _seg(_cb)
check("d19_radius_et_shadow_ensemble_geq_precede_le_split",
      _sb.count("geq=") == 1 and _sb.endswith(OMBRE) and _sb.find("geq=") < _sb.find("[oa0];")
      and _sb.find(",setpts=") < _sb.find("[oa0];"), _sb)
# Deux overlays : les labels d'ombre portent l'indice j — jamais partages.
_o2 = {"path": OVF, "is_image": True, "src_dur": 0.0, "src_in": 0.0, "start": 0.0, "end": 2.0,
       "opacity": None, "tf": dict(TF0, shadow=1), "mp": None, "layer": 0}
_o3 = dict(_o2, start=2.0, end=4.0, tf=dict(TF0, shadow=1, radius=10))
try:
    _c2, _ = MS._build_montage_command([V1SPEC()], [_o2, _o3], [], None, w=1080, h=1920, fps=25, mix_db={},
                                       ducking=False, duration_master=False, preview=True,
                                       out=os.path.join(TMP, "o.mp4"))
    _c2 = FLAT(_c2)
except Exception as e:
    _c2 = "%s: %s" % (type(e).__name__, e)
check("d19_deux_overlays_ombres_portent_des_labels_indices_distincts",
      _c2.count("split[oo") == 2 and "[oa1]split[oo1][os1]" in _c2 and "[osp1][op1]overlay=0:0:format=auto[ov1]" in _c2
      and "[osp0][op0]overlay=0:0:format=auto[ov0]" in _c2 and _c2.count("geq=") == 1 and "[ob1]" in _c2, _c2[_c2.find("[2:v]"):][:400])
# Chaine cover : `radius` pose sur le dict overlay (comme un client qui
# l'enverrait sans tf) est ignore avec warning — tf None reste cover.
_cc, _wc = _avec_journal(lambda: OVBUILD(tf=None, radius=40, shadow=1))
check("d19_cover_sans_tf_ignore_radius_et_shadow_avec_warning_temoin_crop",
      "[1:v]scale=64:64:force_original_aspect_ratio=increase,crop=64:64,setsar=1,fps=25,setpts=" in _cc
      and "geq" not in _cc and "split" not in _cc and any("radius" in m or "ombre" in m or "shadow" in m for m in _wc), (_seg(_cc), _wc))
_cc0, _wc0 = _avec_journal(lambda: OVBUILD(tf=None))
check("d19_cover_sans_les_champs_n_avertit_pas_temoin",
      "crop=64:64" in _cc0 and not any("radius" in m or "shadow" in m for m in _wc0), _wc0)
# Echelle animee (D-14, zoompan) : radius et shadow ignores avec warning.
_cz, _wz = _avec_journal(lambda: OVBUILD(tf=dict(TF0, radius=40, shadow=1),
                                         motion_points=[{"t": 0, "x": .5, "y": .5, "scale": .5},
                                                        {"t": 2, "x": .5, "y": .5, "scale": 1.5}]))
check("d19_echelle_animee_ignore_radius_et_shadow_avec_warning_temoin_zoompan",
      "zoompan" in _cz and "geq" not in _cz and "split" not in _cz and "boxblur" not in _cz
      and any("radius" in m and "anim" in m for m in _wz) and any("shadow" in m and "anim" in m for m in _wz), (_seg(_cz)[:200], _wz))
_czp, _wzp = _avec_journal(lambda: OVBUILD(w=1080, h=1920, tf=dict(TF0, radius=40, shadow=1),
                                           motion_points=[{"t": 0, "x": .2, "y": .5}, {"t": 2, "x": .8, "y": .5}]))
check("d19_position_animee_sans_echelle_garde_geq_et_ombre",
      "zoompan" not in _czp and "overlay=x='(" in _czp and _seg(_czp).count("geq=") == 1 and _seg(_czp).endswith(OMBRE)
      and not _wzp, (_seg(_czp)[:300], _wzp))

print("\n[M] mesure ffmpeg reelle : radius 60 + ombre sur fond bleu, deux pixels")
_FB = None
try:
    from app.services.effects_preview import ffmpeg_bin as _fb
    _FB = _fb()
    _BLEU = str(pathlib.Path(TMP) / "bleu.mp4")
    _gen = subprocess.run([_FB, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                           "color=c=blue:s=480x270:r=25:d=2", "-c:v", "libx264",
                           "-pix_fmt", "yuv420p", _BLEU], check=False, capture_output=True, timeout=60)
    _ROUGE = str(pathlib.Path(TMP) / "rouge.png")
    _gen2 = subprocess.run([_FB, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                            "color=c=red:s=240x140", "-frames:v", "1", _ROUGE],
                           check=False, capture_output=True, timeout=60)
    if _gen.returncode != 0 or _gen2.returncode != 0 or not os.path.isfile(_BLEU) or not os.path.isfile(_ROUGE):
        _FB = None
        print("  (ffmpeg present mais lavfi a echoue : %r)" % (_gen.stderr + _gen2.stderr)[-300:])
except Exception as _e:
    _FB = None
    print("  (ffmpeg injoignable : %s)" % _e)
if _FB is None:
    check("d19_rendu_reel_SKIP_sans_ffmpeg", True)
else:
    _OUT = os.path.join(TMP, "d19.mp4")
    _ov = {"path": _ROUGE, "is_image": True, "src_dur": 0.0, "src_in": 0.0, "start": 0.0,
           "end": 2.0, "opacity": None, "mp": None, "layer": 0,
           "tf": OVT({"x": .5, "y": .5, "scale": .5, "radius": 60, "shadow": 1})}
    _cmd, _rc, _err = None, -1, "commande absente"
    try:
        _cmd, _ = MS._build_montage_command(
            [V1SPEC(path=_BLEU, src_dur=2.0, start=0.0, end=2.0)], [_ov], [], None,
            w=480, h=270, fps=25, mix_db={}, ducking=False, duration_master=False,
            preview=True, out=_OUT)
    except Exception as _e:                # faute n°6 : rougir, pas mourir
        _err = "%s: %s" % (type(_e).__name__, _e)
    if isinstance(_cmd, list) and _cmd:
        _cmd = [_FB] + list(_cmd[1:])
        _r = subprocess.run(_cmd, check=False, capture_output=True, text=True, timeout=180)
        _rc, _err = _r.returncode, (_r.stderr or "")[-400:]
    _size = pathlib.Path(_OUT).stat().st_size if os.path.isfile(_OUT) else -1
    check("d19_rendu_reel_rc_0_fichier_non_vide_geq_et_ombre_dans_la_commande",
          _rc == 0 and _size > 0 and "min(15,min(W/2,H/2))" in FLAT(_cmd or []) and ":8:8:color=black@0,boxblur=2[osp0]" in FLAT(_cmd or []), (_rc, _size, _err))

    def _px(x, y, t="1"):
        """Le pixel (x, y) de l'image a t s (1 par defaut), lu par ffmpeg en rgb24 brut."""
        try:
            r = subprocess.run([_FB, "-loglevel", "error", "-ss", t, "-i", _OUT, "-frames:v", "1",
                                "-vf", "format=rgb24,crop=1:1:%d:%d" % (x, y), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                               check=False, capture_output=True, timeout=60)
            return tuple(r.stdout[:3]) if len(r.stdout) >= 3 else None
        except Exception:
            return None
    _coin, _bord, _ombre, _fond = _px(121, 66), _px(240, 66), _px(240, 205), _px(10, 10)
    _hors, _degr, _dern = _px(240, 225), _px(240, 207), _px(240, 210)
    def _bleu(p): return p is not None and p[0] < 60 and p[1] < 60 and p[2] > 180
    def _rouge(p): return p is not None and p[0] > 180 and p[1] < 60 and p[2] < 60
    check("d19_rendu_reel_le_coin_de_l_overlay_est_le_bleu_du_fond_et_le_bord_est_rouge",
          _rc == 0 and _bleu(_fond) and _bleu(_coin) and _rouge(_bord), (_fond, _coin, _bord))
    check("d19_rendu_reel_l_ombre_dure_assombrit_le_fond_sous_le_bord_bas",
          _rc == 0 and _ombre is not None and _fond is not None and _ombre[0] < 60 and _ombre[1] < 60
          and 40 < _ombre[2] < _fond[2] - 40, (_ombre, _fond))
    # B-2 : hors emprise ≈ fond (± 12) ; dans le degrade, STRICTEMENT entre
    # l'ombre dure et le fond (mesure 24/09/2026, colonne x=240 : image 0..8 jusqu'a
    # y=204, ombre dure 161 en 205, degrade 185/187 en 206/207, fond 251/254 des 208).
    check("d19_rendu_reel_hors_emprise_le_fond_et_dans_le_degrade_un_bleu_intermediaire",
          _rc == 0 and _hors is not None and _degr is not None and _ombre is not None and _fond is not None
          and abs(_hors[2] - _fond[2]) <= 12 and _ombre[2] + 15 < _degr[2] < _fond[2] - 15, (_ombre, _degr, _hors, _fond))
    # R-1 : le dernier rang du canvas padde (y = 59 + 152 - 1 = 210) est deja le
    # fond (± 8) : le degrade s'eteint AVANT le bord, jamais coupe.
    check("d19_rendu_reel_le_dernier_rang_du_canvas_d_ombre_est_le_fond_le_degrade_n_est_pas_coupe",
          _rc == 0 and _dern is not None and _fond is not None and abs(_dern[2] - _fond[2]) <= 8
          and _dern[0] < 30 and _dern[1] < 30, (_dern, _fond))
    # Le setpts est DANS och : le split herite du PTS des deux cotes ; l'overlay
    # intermediaire ne decale rien → 50 images pour 2 s a 25 i/s (temoin).
    _nb = -1
    try:
        _p = subprocess.run([os.path.join(os.path.dirname(_FB), "ffprobe"), "-v", "error",
                             "-count_frames", "-select_streams", "v:0", "-show_entries",
                             "stream=nb_read_frames", "-of", "csv=p=0", _OUT],
                            check=False, capture_output=True, text=True, timeout=60)
        _nb = int((_p.stdout or "").strip() or -1)
    except (ValueError, OSError):
        pass
    _coin19 = _px(121, 66, "1.9")
    check("d19_rendu_reel_50_images_et_l_overlay_est_encore_la_a_t_1_9",
          _rc == 0 and _nb == 50 and _bleu(_coin19), (_nb, _coin19))

print(f"\n=== {ok} passed, {fail} failed ===")
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if fail else 0)
