# -*- coding: utf-8 -*-
"""L5 — COULEUR cote backend. En-tete recopie de test_montage_l3.py
(l.102-134 : env, check, J, TestClient sans port ouvert ; fin : fermeture des
handles puis rmtree) : dossier de donnees NEUF par execution, toute lecture
gardee — un banc qui meurt sur un acces nu ne dit pas quelles assertions
manquent (faute n6 : le DETAIL est evalue AVANT le court-circuit de la
condition, il ne doit donc jamais lever).
Run : & $PY tests/test_montage_l5.py   (depuis backend/)

[1] D-27 / D-29 / D-33 — MOTEUR D'EFFETS. Dix types neufs dans
`effects_engine` (wheels, curves, colormatch, huesat, monochrome, denoise,
deflicker, deband, chromakey, tmix), Nettete etendue (`sharpen` gagne `mode`
unsharp|cas, defaut = commande d'avant le lot octet pour octet), points de
courbe CACHES au rack (`catalog()[t]["points"]`, hors `params`), categorie
neuve `correction`. Chaque constructeur est lu a la chaine ET rendu pour de
vrai (ffmpeg de `effects_preview.ffmpeg_bin()`, mesure PIL).

Les mesures ffmpeg reelles sont en SKIP si ffmpeg est injoignable, comme les
bancs-miroirs du depot.
"""
import json, os, sys, tempfile, subprocess, pathlib, shutil
sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzl5_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from fastapi.testclient import TestClient                # noqa: E402
from app.main import app                                 # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def J(resp):
    """Corps JSON, ou {} — le banc doit ROUGIR, pas mourir sur un .json() nu."""
    try:
        v = resp.json()
    except Exception:
        return {}
    return v if isinstance(v, dict) else {"_liste": v}


c = TestClient(app, raise_server_exceptions=False)
c.__enter__()

from app.services import effects_engine as FX            # noqa: E402
from app.services import effects_preview as PV           # noqa: E402


def F(nom, defaut=None):
    """`getattr` module — un attribut ABSENT (avant l'implementation) doit
    faire ROUGIR les checks qui le lisent, jamais TUER le banc."""
    return getattr(FX, nom, defaut)


def CH(eff, ctx=None):
    """Chaine emise pour UN effet, jointe — jamais d'exception."""
    try:
        return ";".join(FX.build_chain([eff], "a", "b", "u",
                                       ctx or {"w": 64, "h": 64, "dur": 1.0, "fps": 25}))
    except Exception as e:                               # noqa: BLE001
        return f"EXC {e!r}"


def ONE(eff, ctx=None):
    """Constructeur appele DIRECTEMENT (pas de build_chain qui remplacerait
    une exception par `null`) — une exception devient une chaine lisible."""
    try:
        fn = (F("EFFECTS", {}) or {}).get(eff.get("type"))
        if fn is None:
            return "ABSENT"
        return ";".join(fn(eff, "a", "b", "u", ctx or {"w": 64, "h": 64, "dur": 1.0, "fps": 25}))
    except Exception as e:                               # noqa: BLE001
        return f"EXC {e!r}"


NEUFS = ("wheels", "curves", "colormatch", "huesat", "monochrome",
         "denoise", "deflicker", "deband", "chromakey", "tmix")

# =============================================================================
print("\n[1] D-27 D-29 D-33 — moteur d'effets")
# =============================================================================
try:
    CAT = FX.catalog()
except Exception as _e:                                  # noqa: BLE001
    CAT = {}
    print("  (catalog() a leve : %r)" % _e)
try:
    CATS = {x.get("id"): x for x in FX.categories()}
except Exception as _e:                                  # noqa: BLE001
    CATS = {}
EFF = F("EFFECTS", {}) or {}

check("t1_les_dix_types_neufs_au_catalogue_et_au_moteur",
      all(t in CAT and t in EFF for t in NEUFS) and "grade_basic" in CAT,
      str([t for t in NEUFS if t not in CAT or t not in EFF]))
_cv = CAT.get("curves") or {}
check("t1_courbes_points_caches_hors_params",
      isinstance(_cv.get("params"), list)
      and not any(str(p).startswith("pts_") for p in _cv.get("params") or [])
      and _cv.get("points") == ["pts_m", "pts_r", "pts_g", "pts_b"]
      and "grade_basic" in CAT and "points" not in CAT.get("grade_basic", {}),
      str((_cv.get("params"), _cv.get("points"), "points" in CAT.get("grade_basic", {}))))
check("t1_hidden_contrat",
      (F("_HIDDEN", {}) or {}).get("curves") == ("pts_m", "pts_r", "pts_g", "pts_b")
      and F("_CURVE_KEYS") == ("pts_m", "pts_r", "pts_g", "pts_b"),
      str((F("_HIDDEN"), F("_CURVE_KEYS"))))
_cor = CATS.get("correction") or {}
check("t1_categorie_correction_trois_effets",
      _cor.get("count") == 3 and bool(_cor.get("label"))
      and all((CAT.get(t) or {}).get("cat") == "correction" for t in ("denoise", "deflicker", "deband")),
      str((_cor, [(CAT.get(t) or {}).get("cat") for t in ("denoise", "deflicker", "deband")])))
check("t1_etalonnage_onze",
      (CATS.get("etalonnage") or {}).get("count") == 11
      and all((CAT.get(t) or {}).get("cat") == "etalonnage"
              for t in ("wheels", "curves", "colormatch", "huesat", "monochrome")),
      str((CATS.get("etalonnage"), [(CAT.get(t) or {}).get("cat") for t in
                                     ("wheels", "curves", "colormatch", "huesat", "monochrome")])))
check("t1_chromakey_cadrage_tmix_mouvement",
      (CAT.get("chromakey") or {}).get("cat") == "cadrage"
      and (CAT.get("tmix") or {}).get("cat") == "mouvement",
      str(((CAT.get("chromakey") or {}).get("cat"), (CAT.get("tmix") or {}).get("cat"))))
_hints = {t: (CAT.get(t) or {}).get("hint") or "" for t in NEUFS}
check("t1_aides_francaises_courtes",
      all(0 < len(h) <= 90 for h in _hints.values())
      and _hints.get("chromakey") == "Rend transparente une couleur — sur un plan superposé (V2).",
      str({t: len(h) for t, h in _hints.items()}))


def B(t, p):
    return ((CAT.get(t) or {}).get("bounds") or {}).get(p) or {}


check("t1_bornes_roues",
      all(B("wheels", f"lift_{k}").get("min") == -0.5 and B("wheels", f"lift_{k}").get("max") == 0.5
          and B("wheels", f"lift_{k}").get("default") == 0
          and B("wheels", f"gamma_{k}").get("min") == 0.25 and B("wheels", f"gamma_{k}").get("max") == 4
          and B("wheels", f"gamma_{k}").get("default") == 1
          and B("wheels", f"gain_{k}").get("min") == 0 and B("wheels", f"gain_{k}").get("max") == 2
          and B("wheels", f"gain_{k}").get("default") == 1
          and B("wheels", f"gain_{k}").get("step") == 0.01 for k in "rgb")
      and len((CAT.get("wheels") or {}).get("params") or []) == 9,
      str((CAT.get("wheels") or {}).get("bounds")))
check("t1_bornes_accord_et_huesat",
      B("colormatch", "y_gain").get("min") == 0.5 and B("colormatch", "y_gain").get("max") == 2
      and B("colormatch", "v_off").get("min") == -128 and B("colormatch", "v_off").get("max") == 128
      and len((CAT.get("colormatch") or {}).get("params") or []) == 6
      and B("huesat", "hue").get("min") == -180 and B("huesat", "sat").get("max") == 100
      and B("huesat", "strength").get("min") == 1 and B("huesat", "strength").get("default") == 1
      and B("huesat", "colors").get("choices") == ["a", "r", "y", "g", "c", "b", "m"],
      str(((CAT.get("colormatch") or {}).get("bounds"), (CAT.get("huesat") or {}).get("bounds"))))
check("t1_bornes_modes_surcharges_par_entree",
      B("denoise", "mode").get("choices") == ["hqdn3d", "atadenoise"]
      and B("sharpen", "mode").get("choices") == ["unsharp", "cas"]
      and B("sharpen", "mode").get("default") == "unsharp"
      and B("chromakey", "key").get("default") == "#00ff00"
      and B("chromakey", "despill").get("choices") == ["aucun", "vert", "bleu"]
      and B("chromakey", "despill").get("default") == "vert"
      and B("tmix", "frames").get("choices") == ["3", "5", "7"]
      and B("deflicker", "size").get("min") == 2 and B("deflicker", "size").get("max") == 15
      and B("deflicker", "size").get("default") == 5
      and B("gradient", "blend").get("choices") == list(FX.BLEND_MODES),
      str([B("denoise", "mode"), B("sharpen", "mode"), B("chromakey", "despill"), B("tmix", "frames")]))

# --- curves_clean -------------------------------------------------------------
_cc = F("curves_clean")


def CC(s):
    try:
        return _cc(s) if _cc else "ABSENT"
    except Exception as e:                               # noqa: BLE001
        return f"EXC {e!r}"


check("t1_cc_point_unique_prolonge_aux_extremites",
      CC("0.5/0.6") == "0/0.6 0.5/0.6 1/0.6" and CC("0/0 0.5/0.7 1/1") == "0/0 0.5/0.7 1/1",
      str((CC("0.5/0.6"), CC("0/0 0.5/0.7 1/1"))))
check("t1_cc_trie", CC("1/1 0/0 0.5/0.7") == "0/0 0.5/0.7 1/1", CC("1/1 0/0 0.5/0.7"))
check("t1_cc_x_duplique_dernier_gagne",
      CC("0/0 0.5/0.2 0.5/0.7 1/1") == "0/0 0.5/0.7 1/1", CC("0/0 0.5/0.2 0.5/0.7 1/1"))
_vingt = " ".join(f"{k / 19:.4f}/{(k / 19) ** 2:.4f}" for k in range(20))
_c20 = CC(_vingt).split(" ")
check("t1_cc_seize_points_au_plus_extremites_gardees",
      len(_c20) == 16 and _c20[0].startswith("0/") and _c20[-1].startswith("1/")
      and len(CC("0/0 0.5/0.5 1/1").split(" ")) == 3,
      str(_c20))
check("t1_cc_invalide_identite",
      CC("abc") == "0/0 1/1" and CC("") == "0/0 1/1" and CC(None) == "0/0 1/1"
      and CC("0/0 0.5/0.7 1/1") != "0/0 1/1",
      str((CC("abc"), CC(""), CC(None))))
check("t1_cc_y_borne",
      CC("0/0 0.5/1.4 1/1") == "0/0 0.5/1 1/1" and CC("0/-3 1/1") == "0/0 1/1"
      and CC("0/0 0.25/0.1234 1/1") == "0/0 0.25/0.123 1/1",
      str((CC("0/0 0.5/1.4 1/1"), CC("0/-3 1/1"), CC("0/0 0.25/0.1234 1/1"))))

# --- identite -> null ; non neutre -> le filtre (temoin dans la meme expression)
_ID = [
    ("wheels", {}, {"gain_r": 1.5}, "lutrgb"),
    ("curves", {"pts_m": "0/0 1/1"}, {"pts_m": "0/0 0.5/0.7 1/1"}, "curves="),
    ("colormatch", {}, {"y_gain": 1.2, "y_off": 10}, "lutyuv"),
    ("huesat", {}, {"sat": -100, "colors": "r"}, "huesaturation"),
    ("denoise", {"intensity": 0}, {"intensity": 50}, "hqdn3d"),
]
for t, neutre, actif, filt in _ID:
    _n = CH(dict({"type": t}, **neutre))
    _a = CH(dict({"type": t}, **actif))
    check(f"t1_identite_null_{t}",
          t in EFF and "null" in _n and filt not in _n and filt in _a and "null" not in _a,
          str((_n, _a)))

# Sans point neutre naturel (un monochrome est TOUJOURS gris, un deflicker
# lisse TOUJOURS) : le filtre est emis aux defauts, et une valeur absurde est
# ramenee dans ses bornes (le rendu du Montage n'applique pas coerce_params).
_SANS = [
    ("monochrome", {"cb": 9, "cr": -9}, "monochrome=cb=1.00:cr=-1.00"),
    ("deflicker", {"size": 999}, "deflicker=size=15:mode=am"),
    ("deband", {"intensity": 100}, "deband=1thr=0.045"),
    ("chromakey", {"similarity": 500, "despill": "aucun"}, "similarity=1.000"),
    ("tmix", {"frames": "9"}, "tmix=frames=3"),
]
for t, absurde, attendu in _SANS:
    _d = ONE({"type": t})
    _x = ONE(dict({"type": t}, **absurde))
    check(f"t1_defauts_et_bornes_{t}",
          t in EFF and "null" not in _d and not _d.startswith(("EXC", "ABSENT")) and attendu in _x,
          str((_d, _x)))
_ck = ONE({"type": "chromakey"})
_ckb = ONE({"type": "chromakey", "despill": "bleu", "key": "#0000ff"})
_ck0 = ONE({"type": "chromakey", "despill": "aucun"})
check("t1_chromakey_alpha_et_despill",
      "format=yuva420p,chromakey=color=0x00ff00" in _ck and "despill=type=green" in _ck
      and "despill=type=blue" in _ckb and "0x0000ff" in _ckb
      and "chromakey=" in _ck0 and "despill" not in _ck0,
      str((_ck, _ckb, _ck0)))
_dn = ONE({"type": "denoise", "mode": "atadenoise"})
check("t1_denoise_deux_modes",
      "atadenoise=" in _dn and "hqdn3d" not in _dn
      and ONE({"type": "denoise"}) == "[a]hqdn3d=4.000:3.000:6.000:4.500[b]",
      str((_dn, ONE({"type": "denoise"}))))
check("t1_tmix_cinq", ONE({"type": "tmix", "frames": "5"}) == "[a]tmix=frames=5[b]",
      ONE({"type": "tmix", "frames": "5"}))

# --- Nettete : defaut OCTET POUR OCTET celui de 81bfde3 ------------------------
# Constante recopiee de `_sharpen` a 81bfde3 : unsharp=5:5:{0.5+2.0*t:.2f}:5:5:0.0
# avec t = intensite 60 par defaut -> 1.70.
_SH_AVANT = "[a]unsharp=5:5:1.70:5:5:0.0[b]"
_SH_AVANT_80 = "[a]unsharp=5:5:2.10:5:5:0.0[b]"
_sc = ONE({"type": "sharpen", "mode": "cas", "intensity": 60})
check("t1_sharpen_defaut_inchange_et_cas",
      ONE({"type": "sharpen"}) == _SH_AVANT
      and ONE({"type": "sharpen", "intensity": 80}) == _SH_AVANT_80
      and ONE({"type": "sharpen", "mode": "unsharp"}) == _SH_AVANT
      and ONE({"type": "sharpen", "mode": "zzz"}) == _SH_AVANT
      and "cas=strength=0.60" in _sc and "unsharp" not in _sc,
      str((ONE({"type": "sharpen"}), _sc)))

# --- couleur : 6 caracteres NON hexadecimaux ne passent plus (ecart 24/09) ----
# `_c` ne verifiait que la longueur : « ;[x]ab » partait tel quel dans le
# filtergraph (le rendu du Montage n'applique pas coerce_params).
_ckx = ONE({"type": "chromakey", "key": ";[x]ab"})
_grx = CH({"type": "gradient", "c0": ";[x]ab", "c1": "#A855F7"})
check("t1_couleur_hexa_stricte",
      "0x00ff00" in _ckx and ";[x]" not in _ckx
      and "c0=0xffffff" in _grx and "c1=0xa855f7" in _grx and ";[x]" not in _grx,
      str((_ckx, _grx[:160])))

# --- coerce_params garde les points caches NETTOYES ----------------------------
try:
    _cp = PV.coerce_params("curves", {"pts_m": "1/1 0/0 0.5/0.7", "pts_x": "1", "pts_r": ""})
except Exception as _e:                                  # noqa: BLE001
    _cp = {"EXC": repr(_e)}
try:
    _cpg = PV.coerce_params("grade_basic", {"pts_m": "0/0 1/1", "exposure": 10})
except Exception as _e:                                  # noqa: BLE001
    _cpg = {"EXC": repr(_e)}
check("t1_coerce_points_caches",
      _cp == {"pts_m": "0/0 0.5/0.7 1/1"} and "pts_m" not in _cpg and _cpg.get("exposure") == 10,
      str((_cp, _cpg)))

# --- rendu REEL ---------------------------------------------------------------
FF = PV.ffmpeg_bin()
try:
    _ver = subprocess.run([FF, "-version"], capture_output=True, text=True, timeout=30).stdout.split("\n")[0]
except Exception:                                        # noqa: BLE001
    _ver = ""
if not _ver:
    print("  SKIP rendu reel : ffmpeg injoignable")
else:
    print("  ffmpeg :", _ver[:60])
    from PIL import Image                                # noqa: E402
    OUT = pathlib.Path(TMP) / "l5"
    OUT.mkdir(parents=True, exist_ok=True)
    _n = [0]

    def REND(effects, inputs, fmt="rgb24", tail="", w=64, h=64):
        """Rend UNE image : entree 0 -> yuv420p (comme le Montage) -> pile ->
        [tail] -> PNG. Rend l'image PIL ou None (jamais d'exception)."""
        _n[0] += 1
        out = OUT / f"r{_n[0]}.png"
        try:
            chain = FX.build_chain(effects, "s0", "fx", "u1", {"w": w, "h": h, "dur": 1.0, "fps": 25})
        except Exception:                                # noqa: BLE001
            return None
        g = ["[0:v]format=yuv420p[s0]"] + chain + [f"[fx]{tail or 'null'}[vout]"]
        args = [FF, "-y", "-v", "error"]
        for src in inputs:
            args += (["-f", "lavfi", "-i", src] if not src.endswith(".png") else ["-i", src])
        args += ["-filter_complex", ";".join(g), "-map", "[vout]", "-frames:v", "1",
                 "-pix_fmt", fmt, str(out)]
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=120)
            if r.returncode != 0 or not out.is_file():
                print("    (ffmpeg :", (r.stderr or "").strip()[-200:], ")")
                return None
            return Image.open(out).copy()
        except Exception:                                # noqa: BLE001
            return None

    def MOY(im, box=None):
        """Moyenne par canal d'une zone, ou None."""
        try:
            z = im.crop(box) if box else im
            _gf = getattr(z, "get_flattened_data", None) or z.getdata
            px = list(_gf())
            if px and isinstance(px[0], int):
                return (sum(px) / len(px),)
            return tuple(sum(p[k] for p in px) / len(px) for k in range(3))
        except Exception:                                # noqa: BLE001
            return None

    GRIS = "color=c=0x808080:s=64x64:d=1"
    _t = MOY(REND([], [GRIS]))
    _w = MOY(REND([{"type": "wheels", "gain_r": 1.5}], [GRIS]))
    check("t1_rendu_wheels_gain_rouge",
          _t is not None and _w is not None and _w[0] - _t[0] >= 40 and abs(_w[1] - _t[1]) <= 2,
          str((_t, _w)))
    _cr = MOY(REND([{"type": "curves", "pts_m": "0/0 0.5/0.7 1/1"}], [GRIS]))
    check("t1_rendu_curves_master",
          _t is not None and _cr is not None and all(175 <= v <= 183 for v in _cr)
          and all(120 <= v <= 136 for v in _t),
          str((_t, _cr)))
    # Mire trois bandes rouge / vert / bleu, 96x64.
    _mire = OUT / "mire3.png"
    try:
        _im = Image.new("RGB", (96, 64))
        for x0, col in ((0, (200, 40, 40)), (32, (40, 200, 40)), (64, (40, 40, 200))):
            _im.paste(col, (x0, 0, x0 + 32, 64))
        _im.save(_mire)
    except Exception:                                    # noqa: BLE001
        pass
    _m0 = REND([], [str(_mire)], w=96)
    _mh = REND([{"type": "huesat", "sat": -100, "colors": "r"}], [str(_mire)], w=96)
    _R0, _Rh = MOY(_m0, (8, 8, 24, 56)) if _m0 else None, MOY(_mh, (8, 8, 24, 56)) if _mh else None
    _G0, _Gh = MOY(_m0, (40, 8, 56, 56)) if _m0 else None, MOY(_mh, (40, 8, 56, 56)) if _mh else None
    check("t1_rendu_huesat_bande_rouge_seule",
          None not in (_R0, _Rh, _G0, _Gh)
          and _R0[0] - _Rh[0] >= 30 and max(abs(a - b) for a, b in zip(_G0, _Gh)) <= 2,
          str((_R0, _Rh, _G0, _Gh)))
    _y0 = MOY(REND([], [GRIS], fmt="gray", tail="extractplanes=y"))
    _ym = MOY(REND([{"type": "colormatch", "y_gain": 1.2, "y_off": 10}], [GRIS],
                   fmt="gray", tail="extractplanes=y"))
    check("t1_rendu_colormatch_sur_y",
          _y0 is not None and _ym is not None and 124 <= _y0[0] <= 128
          and abs(_ym[0] - (_y0[0] * 1.2 + 10)) <= 3,
          str((_y0, _ym)))
    # Fond vert pur superpose sur du bleu : la cle rend le vert transparent.
    _VERT, _BLEU = "color=c=0x00FF00:s=64x64:d=1", "color=c=0x0000FF:s=64x64:d=1"
    _k = MOY(REND([{"type": "chromakey"}], [_VERT, _BLEU], tail="null[k];[1:v][k]overlay=format=auto"))
    _k0 = MOY(REND([], [_VERT, _BLEU], tail="null[k];[1:v][k]overlay=format=auto"))
    check("t1_rendu_chromakey_laisse_voir_le_bleu",
          _k is not None and _k0 is not None and _k[2] >= 240 and _k0[2] <= 40 and _k0[1] >= 200,
          str((_k, _k0)))

print(f"\n=== {ok} passed, {fail} failed ===")
c.__exit__(None, None, None)
# Nettoyage : le journal loguru et le pool sqlite tiennent encore des handles
# apres le lifespan (mesure : logs/*.log, t.db-wal/-shm survivaient a un
# rmtree nu) — on les ferme d'abord, puis on efface sans jamais rougir.
try:
    from loguru import logger as _lg
    _lg.remove()
    import asyncio as _aio
    from app.services import storage as _st
    _aio.run(_st._engine.dispose())
except Exception as _e:
    print("  (fermeture des handles : %s)" % _e)
shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if fail else 0)
