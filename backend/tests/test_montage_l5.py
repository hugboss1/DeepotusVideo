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
vrai (ffmpeg de `effects_preview.ffmpeg_bin()`) : une boucle de FUMEE rend
chaque type neuf (+ sharpen cas) aux defauts et aux bornes hautes (image non
vide exigee) ; wheels, curves, huesat, colormatch et chromakey sont en plus
MESURES a l'image (PIL). Regle UNIQUE de lecture des courbes : vecteurs
partages `tests/l5_courbes_vecteurs.json` (rejoues aussi par le client).

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
# M-4 (revue T1) : la force par defaut est 10 (desaturation complete mesuree)
# et l'aide le dit ; temoin : l'aide d'un autre type ne parle pas de force.
check("t1_huesat_aide_dit_force_10",
      "force 10" in _hints.get("huesat", "").lower()
      and "force 10" not in _hints.get("monochrome", "").lower(),
      repr(_hints.get("huesat")))


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
      and B("huesat", "strength").get("min") == 1 and B("huesat", "strength").get("default") == 10
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

# --- REGLE UNIQUE de lecture (decision 24/09 : Python et JS divergeaient) ---
# Jetons separes par blancs ASCII (espace, tab, CR, LF) OU virgules ; jeton
# valide = NOMBRE/NOMBRE exactement (pas de `_`, ni inf/nan, un seul `/`) ;
# jeton invalide SAUTE ; 256 jetons lus au plus. Temoin dans chaque check :
# la meme forme ecrite proprement est lue.
check("t1_cc_jeton_invalide_saute_les_autres_gardes",
      CC("0.1/0.2 zz") == "0/0.2 0.1/0.2 1/0.2"
      and CC("0.5/0.6/0.7 0.2/0.3") == "0/0.3 0.2/0.3 1/0.3",
      str((CC("0.1/0.2 zz"), CC("0.5/0.6/0.7 0.2/0.3"))))
check("t1_cc_virgules_separent",
      CC("0/0, 0.5/0.6, 1/1") == "0/0 0.5/0.6 1/1", CC("0/0, 0.5/0.6, 1/1"))
check("t1_cc_souligne_et_infini_refuses",
      CC("1_0/0.5") == "0/0 1/1" and CC("10/0.5") == "0/0.5 1/0.5"
      and CC("-inf/0.2 0.5/0.5") == "0/0.5 0.5/0.5 1/0.5",
      str((CC("1_0/0.5"), CC("10/0.5"), CC("-inf/0.2 0.5/0.5"))))
check("t1_cc_x1c_n_est_pas_un_separateur",
      CC("0/0\x1c0.5/0.6 1/1") == "0/1 1/1" and CC("0/0 0.5/0.6 1/1") == "0/0 0.5/0.6 1/1",
      str((CC("0/0\x1c0.5/0.6 1/1"),)))
try:
    _VEC = json.loads((pathlib.Path(__file__).resolve().parent
                       / "l5_courbes_vecteurs.json").read_text(encoding="utf-8"))
except Exception as _e:                                  # noqa: BLE001
    print("  (vecteurs illisibles : %r)" % _e)
    _VEC = []
_vko = [(v.get("in"), v.get("out"), CC(v.get("in"))) for v in _VEC
        if isinstance(v, dict) and CC(v.get("in")) != v.get("out")]
check("t1_cc_vecteurs_partages_rejoues",
      isinstance(_VEC, list) and len(_VEC) >= 40 and not _vko
      and any(v.get("in") == "0/0\x1c0.5/0.6 1/1" for v in _VEC if isinstance(v, dict)),
      "%d vecteurs, ecarts %r" % (len(_VEC), _vko[:4]))

# --- identite -> null ; non neutre -> le filtre (temoin dans la meme expression)
_ID = [
    ("wheels", {}, {"gain_r": 1.5}, "lutrgb"),
    ("curves", {"pts_m": "0/0 1/1"}, {"pts_m": "0/0 0.5/0.7 1/1"}, "curves="),
    ("colormatch", {}, {"y_gain": 1.2, "y_off": 10}, "lutyuv"),
    ("huesat", {}, {"sat": -100, "colors": "r"}, "huesaturation"),
    ("denoise", {"intensity": 0}, {"intensity": 50}, "hqdn3d"),
]
for t, neutre, actif, filt in _ID:
    # M-5 (revue T1) : le cote neutre passe par le CONSTRUCTEUR direct —
    # build_chain avale les exceptions en `null` et ferait passer un
    # constructeur casse pour une identite.
    _n = ONE(dict({"type": t}, **neutre))
    _a = ONE(dict({"type": t}, **actif))
    check(f"t1_identite_null_{t}",
          t in EFF and _n == "[a]null[b]" and filt in _a and "null" not in _a,
          str((_n, _a)))

# --- colormatch PIVOTE autour de 128 (decision du controleur, 24/09) ---------
# Un gain sur U/V ne doit pas deplacer un gris neutre : (val-128)*G+128+O.
check("t1_colormatch_pivote_128",
      ONE({"type": "colormatch", "y_gain": 1.2, "y_off": 10})
      == "[a]lutyuv=y='clip((val-128)*1.200+128+10.000,0,255)'"
         ":u='clip((val-128)*1.000+128+0.000,0,255)'"
         ":v='clip((val-128)*1.000+128+0.000,0,255)'[b]"
      and "(val-128)*1.500+128-5.000" in ONE({"type": "colormatch", "u_gain": 1.5, "u_off": -5}),
      ONE({"type": "colormatch", "y_gain": 1.2, "y_off": 10}))

# --- M-6 : injections, avec temoin positif -------------------------------------
_hs_bad = ONE({"type": "huesat", "sat": -50, "colors": "r;[x]"})
_hs_ok = ONE({"type": "huesat", "sat": -50, "colors": "g"})
check("t1_huesat_colors_hors_liste_neutralise",
      "colors=r+y+g+c+b+m+a" in _hs_bad and "[x]" not in _hs_bad
      and _hs_ok.endswith("colors=g[b]"),
      str((_hs_bad, _hs_ok)))
_cv_bad = ONE({"type": "curves", "pts_m": "0/0 0.5/0.7';[x] 1/1"})
_cv_ok = ONE({"type": "curves", "pts_m": "0/0 0.5/0.7 1/1"})
check("t1_courbe_piegee_neutralisee",
      "[x]" not in _cv_bad and "';" not in _cv_bad and _cv_bad == "[a]null[b]"
      and _cv_ok == "[a]curves=interp=pchip:m='0/0 0.5/0.7 1/1'[b]",
      str((_cv_bad, _cv_ok)))

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
# M-3 : seuils d'atadenoise = defauts ffmpeg (0,02 / 0,04) a l'intensite 50,
# doubles a 100 (les plafonds 0,3 / 5 d'ffmpeg ne sont jamais atteints).
_dn100 = ONE({"type": "denoise", "mode": "atadenoise", "intensity": 100})
check("t1_atadenoise_seuils_defauts_ffmpeg_et_doubles",
      "0a=0.0200:0b=0.0400:1a=0.0200:1b=0.0400:2a=0.0200:2b=0.0400" in _dn
      and "0a=0.0400:0b=0.0800" in _dn100 and ":s=9" in _dn100,
      str((_dn, _dn100)))
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
    # PIVOTE : (Y-128)*1.2+128+10 (126 -> ~135.6 ; l'ancienne forme donnait 161)
    check("t1_rendu_colormatch_sur_y",
          _y0 is not None and _ym is not None and 124 <= _y0[0] <= 128
          and abs(_ym[0] - ((_y0[0] - 128) * 1.2 + 128 + 10)) <= 3,
          str((_y0, _ym)))
    # Un gris neutre reste neutre en U sous un gain U de 1,5 ; temoin : un
    # decalage U de 20 le deplace bien (le plan U est lu, la mesure vit).
    _u0 = MOY(REND([], [GRIS], fmt="gray", tail="extractplanes=u"))
    _ug = MOY(REND([{"type": "colormatch", "u_gain": 1.5}], [GRIS],
                   fmt="gray", tail="extractplanes=u"))
    _uo = MOY(REND([{"type": "colormatch", "u_off": 20}], [GRIS],
                   fmt="gray", tail="extractplanes=u"))
    check("t1_rendu_colormatch_gain_u_garde_le_gris_neutre",
          None not in (_u0, _ug, _uo) and abs(_u0[0] - 128) <= 2
          and abs(_ug[0] - _u0[0]) <= 2 and _uo[0] - _u0[0] >= 15,
          str((_u0, _ug, _uo)))
    # Fond vert pur superpose sur du bleu : la cle rend le vert transparent.
    _VERT, _BLEU = "color=c=0x00FF00:s=64x64:d=1", "color=c=0x0000FF:s=64x64:d=1"
    _k = MOY(REND([{"type": "chromakey"}], [_VERT, _BLEU], tail="null[k];[1:v][k]overlay=format=auto"))
    _k0 = MOY(REND([], [_VERT, _BLEU], tail="null[k];[1:v][k]overlay=format=auto"))
    check("t1_rendu_chromakey_laisse_voir_le_bleu",
          _k is not None and _k0 is not None and _k[2] >= 240 and _k0[2] <= 40 and _k0[1] >= 200,
          str((_k, _k0)))

    # M-4 : la force par DEFAUT (10) desature completement la bande rouge ;
    # temoin : force 1 la laisse coloree (mesure du plan : (133,73,73)).
    _hd = REND([{"type": "huesat", "sat": -100, "colors": "r"}], [str(_mire)], w=96)
    _h1 = REND([{"type": "huesat", "sat": -100, "colors": "r", "strength": 1}], [str(_mire)], w=96)
    _Rd = MOY(_hd, (8, 8, 24, 56)) if _hd else None
    _R1 = MOY(_h1, (8, 8, 24, 56)) if _h1 else None
    check("t1_rendu_huesat_force_defaut_desature_completement",
          None not in (_Rd, _R1) and max(_Rd) - min(_Rd) <= 8 and max(_R1) - min(_R1) >= 40,
          str((_Rd, _R1)))

    # I-1 : FUMEE — chaque type neuf (+ sharpen cas) rendu pour de vrai aux
    # defauts ET aux bornes hautes. Une image non vide est exigee : une
    # chaine refusee par ffmpeg (option inconnue, valeur hors plage) rougit.
    def HAUT(t):
        """Parametres a leur borne HAUTE (range : max ; choice : dernier)."""
        d = {"type": t}
        for p, b in ((CAT.get(t) or {}).get("bounds") or {}).items():
            if b.get("type") == "range" and "max" in b:
                d[p] = b["max"]
            elif b.get("type") == "choice" and b.get("choices"):
                d[p] = b["choices"][-1]
        return d

    _FUM = [({"type": t}, "defaut") for t in NEUFS] + [(HAUT(t), "haut") for t in NEUFS]
    _FUM += [({"type": "denoise", "mode": "atadenoise"}, "defaut"),
             (dict(HAUT("denoise"), mode="hqdn3d"), "haut"),
             ({"type": "sharpen", "mode": "cas"}, "defaut"),
             (dict(HAUT("sharpen"), mode="cas"), "haut"),
             ({"type": "curves", "pts_m": "0/0 0.5/0.9 1/1", "pts_r": "0/0.2 1/0.8",
               "pts_g": "0/1 1/0", "pts_b": "0.2/0 0.8/1"}, "haut")]
    _SRC = "testsrc2=s=64x64:d=1"
    _ko = []
    for _e, _qui in _FUM:
        _im = REND([_e], [_SRC])
        if _im is None or _im.size != (64, 64):
            _ko.append((_qui, _e))
    # Temoins : la meme machine rend None sur un filtre inconnu (la fumee
    # SAIT rougir) et une image sur une source nue.
    _casse = REND([], [_SRC], tail="zz_filtre_inconnu=1")
    _nu = REND([], [_SRC])
    check("t1_fumee_rendu_reel_tous_types_neufs_defauts_et_bornes_hautes",
          len(_FUM) == 25 and not _ko and _casse is None and _nu is not None
          and all(e.get("type") in EFF for e, _ in _FUM)
          and HAUT("colormatch").get("y_gain") == 2 and HAUT("tmix").get("frames") == "7",
          str((len(_FUM), _ko)))

# =============================================================================
print("\n[3] D-28 — accord de couleur (color_match.py)")
# =============================================================================
# ETAT VIDE : avant T3 `app.services.color_match` et `app.services.grading`
# n'existent pas -> CM / GR valent None, chaque appel rend un temoin
# ("ABSENT", None) et TOUS les checks [3] [4] rougissent ; les temoins
# positifs (source sans effet, ffmpeg nu hors duree) restent lisibles.
import asyncio                                           # noqa: E402
try:
    from app.services import color_match as CM           # noqa: E402
except Exception as _e:                                  # noqa: BLE001
    print("  (color_match absent : %r)" % _e)
    CM = None
try:
    from app.services import grading as GR               # noqa: E402
except Exception as _e:                                  # noqa: BLE001
    print("  (grading absent : %r)" % _e)
    GR = None


def CALL(mod, nom, *a, **k):
    """mod.nom(*a, **k), ou une chaine temoin — jamais d'exception."""
    f = getattr(mod, nom, None) if mod is not None else None
    if f is None:
        return "ABSENT"
    try:
        return f(*a, **k)
    except Exception as e:                               # noqa: BLE001
        return "EXC %s: %s" % (type(e).__name__, e)


def STATS_OK(s):
    """{y,u,v} -> (moyenne, ecart-type) flottants."""
    try:
        return set(s) == {"y", "u", "v"} and all(
            len(s[k]) == 2 and all(isinstance(x, float) for x in s[k]) for k in "yuv")
    except Exception:                                    # noqa: BLE001
        return False


def SV(s, k, i=0):
    """s[k][i] ou None."""
    try:
        return s[k][i]
    except Exception:                                    # noqa: BLE001
        return None


FX3 = pathlib.Path(TMP) / "l5t3"
FX3.mkdir(parents=True, exist_ok=True)


def MKV(nom, src, vf="", d=2, extra=None):
    """Fabrique une video 320x180 25 i/s (lavfi) ; chemin str ou None."""
    out = FX3 / nom
    args = [FF, "-y", "-v", "error"] + (extra or ["-f", "lavfi", "-i", src])
    if vf:
        args += ["-vf", vf]
    args += ["-t", str(d), "-pix_fmt", "yuv420p", str(out)]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=120)
        return str(out) if r.returncode == 0 and out.is_file() else None
    except Exception:                                    # noqa: BLE001
        return None


_NZ = "noise=alls=20:allf=t"
ORG = MKV("orange.mp4", "color=c=0xc06030:s=320x180:r=25:d=2", _NZ)
TS = MKV("testsrc2.mp4", "testsrc2=s=320x180:r=25:d=2")
GRIS = MKV("gris.mp4", "color=c=0x808080:s=320x180:r=25:d=2", _NZ)
GPLAT = MKV("gris_plat.mp4", "color=c=0x808080:s=320x180:r=25:d=2")
TEINTE = MKV("teinte.mp4", "color=c=0xa08058:s=320x180:r=25:d=2", "noise=alls=8:allf=t")
NOIR = MKV("noir.mp4", "color=c=black:s=320x180:r=25:d=2")
BLANC = MKV("blanc.mp4", "color=c=white:s=320x180:r=25:d=2")
# Reference NEUTRE a forte chroma : moitie rouge (200,40,40), moitie cyan
# (40,200,200) -> Cb/Cr moyens 128 (calcul BT.601), ecart-type ~50.
NCH = MKV("neutre_chroma.mp4", "", "", extra=[
    "-f", "lavfi", "-i", "color=c=0xc82828:s=160x180:r=25:d=2",
    "-f", "lavfi", "-i", "color=c=0x28c8c8:s=160x180:r=25:d=2",
    "-filter_complex", "[0:v][1:v]hstack=inputs=2"])
check("t3_fixtures_fabriquees", None not in (ORG, TS, GRIS, GPLAT, TEINTE, NOIR, BLANC, NCH),
      str((ORG, TS, GRIS, GPLAT, TEINTE, NOIR, BLANC, NCH)))

S_ORG, S_TS = CALL(CM, "frame_stats", ORG, 1.0), CALL(CM, "frame_stats", TS, 1.0)
S_GRIS, S_TEI = CALL(CM, "frame_stats", GRIS, 1.0), CALL(CM, "frame_stats", TEINTE, 1.0)
S_NCH = CALL(CM, "frame_stats", NCH, 1.0)
check("t3_frame_stats_forme_yuv_moyenne_ecart",
      all(STATS_OK(s) for s in (S_ORG, S_TS, S_GRIS, S_TEI, S_NCH)),
      str((S_ORG, S_TS)))
# L'orange est tres bleu-negatif / rouge-positif ; le gris neutre ne l'est pas.
check("t3_frame_stats_orange_teinte_gris_neutre",
      STATS_OK(S_ORG) and STATS_OK(S_GRIS)
      and SV(S_ORG, "u") < 105 and SV(S_ORG, "v") > 160
      and abs(SV(S_GRIS, "u") - 128) <= 2 and abs(SV(S_GRIS, "v") - 128) <= 2,
      str((S_ORG, S_GRIS)))
# PLAGE LIMITEE : noir -> Y 16, blanc -> Y 235 (plage pleine : 0 / 255).
_sn, _sb = CALL(CM, "frame_stats", NOIR, 1.0), CALL(CM, "frame_stats", BLANC, 1.0)
check("t3_frame_stats_plage_limitee_noir16_blanc235",
      STATS_OK(_sn) and STATS_OK(_sb) and abs(SV(_sn, "y") - 16) <= 2 and abs(SV(_sb, "y") - 235) <= 2
      and abs(SV(_sn, "u") - 128) <= 2,
      str((_sn, _sb)))
# Au-dela de la duree : la derniere image lisible, pas une erreur.
_sfar = CALL(CM, "frame_stats", TS, 50.0)
check("t3_frame_stats_hors_duree_derniere_image", STATS_OK(_sfar), str(_sfar))


def RENDU_STATS(src, effs, t=1.0):
    """Stats (plage limitee) de l'image etalonnee par `graded_frame`."""
    p = CALL(GR, "graded_frame", src, t, effs, None, 256, "png")
    if not isinstance(p, pathlib.Path):
        return ("RENDU", p)
    return CALL(CM, "image_stats", p)


def ALIGNE(a, b, tol=6.0):
    try:
        return max(abs(a[k][0] - b[k][0]) for k in "yuv") < tol
    except Exception:                                    # noqa: BLE001
        return False


def ECART(a, b):
    try:
        return round(max(abs(a[k][0] - b[k][0]) for k in "yuv"), 2)
    except Exception:                                    # noqa: BLE001
        return None


def EFF_OK(e):
    try:
        return (e.get("type") == "colormatch"
                and all(0.5 <= e[f"{k}_gain"] <= 2 and -128 <= e[f"{k}_off"] <= 128 for k in "yuv"))
    except Exception:                                    # noqa: BLE001
        return False


# (a) testsrc2 accorde sur l'orange (gain < 1 : cas facile).
E1 = CALL(CM, "match_effect", S_ORG, S_TS)
R1 = RENDU_STATS(TS, [E1] if isinstance(E1, dict) else [])
R1_0 = RENDU_STATS(TS, [])
check("t3_match_testsrc_sur_orange_moyennes_alignees_6",
      EFF_OK(E1) and ALIGNE(R1, S_ORG) and not ALIGNE(R1_0, S_ORG, 20),
      str((E1, ECART(R1, S_ORG), ECART(R1_0, S_ORG))))
# (b) orange accorde sur testsrc2 (gain 2 : le cas dur, bruit amplifie).
E2 = CALL(CM, "match_effect", S_TS, S_ORG)
R2 = RENDU_STATS(ORG, [E2] if isinstance(E2, dict) else [])
check("t3_match_orange_sur_testsrc_moyennes_alignees_6",
      EFF_OK(E2) and E2["u_gain"] >= 1.9 and ALIGNE(R2, S_TS),
      str((E2, ECART(R2, S_TS))))
# (b') decalage hors [-128,128] : le Reinhard NAIF (gain borne puis decalage
# borne) rate la moyenne de ~80 ; on REDUIT le gain pour garder la moyenne
# (priorite a la moyenne). Forme pivotee (decision controleur 24/09) :
# sortie moyenne = (mu_t-128)·G + 128 + O.
_ref_b, _tgt_b = {"y": (200.0, 40.0), "u": (128.0, 5.0), "v": (128.0, 5.0)}, \
                 {"y": (60.0, 10.0), "u": (128.0, 5.0), "v": (128.0, 5.0)}
E2b = CALL(CM, "match_effect", _ref_b, _tgt_b)
try:
    _moy_b = (60.0 - 128) * E2b["y_gain"] + 128 + E2b["y_off"]
    _naif_b = (60.0 - 128) * 2.0 + 128 + max(-128, min(128, 200.0 - 128 - 2.0 * (60.0 - 128)))
except Exception:                                        # noqa: BLE001
    _moy_b = _naif_b = None
check("t3_match_decalage_hors_bornes_gain_reduit_moyenne_gardee",
      EFF_OK(E2b) and _moy_b is not None and abs(_moy_b - 200) <= 0.5 and abs(_naif_b - 200) > 50
      and E2b["y_gain"] < 2,
      str((E2b, _moy_b, _naif_b)))
# (c) revue T1 : la forme `val·G+O` agissait AUTOUR DE 0 sur U/V ; forme
# PIVOTEE (decision controleur 24/09) `(val-128)·G+128+O`, O = mu_r-128 -
# G·(mu_t-128). Un gris neutre accorde sur lui-meme, puis sur une reference
# neutre a FORTE chroma (gain chroma 2, decalage ~0) : u, v restent 128 +/- 2.
# Un decalage non pivote (mu_r - mu_t = 0 avec la forme pivotee, ou la
# forme non pivotee avec O = 0) donnerait 2·128 -> 255.
E3 = CALL(CM, "match_effect", S_GRIS, S_GRIS)
R3 = RENDU_STATS(GRIS, [E3] if isinstance(E3, dict) else [])
check("t3_gris_neutre_accorde_sur_lui_meme_reste_neutre",
      EFF_OK(E3) and STATS_OK(R3) and abs(SV(R3, "u") - 128) <= 2 and abs(SV(R3, "v") - 128) <= 2,
      str((E3, R3)))
E4 = CALL(CM, "match_effect", S_NCH, S_GRIS)
R4 = RENDU_STATS(GRIS, [E4] if isinstance(E4, dict) else [])
check("t3_gris_sur_ref_neutre_forte_chroma_gain2_reste_neutre",
      EFF_OK(E4) and E4["u_gain"] >= 1.9 and abs(E4["u_off"]) <= 2
      and STATS_OK(R4) and abs(SV(R4, "u") - 128) <= 2 and abs(SV(R4, "v") - 128) <= 2,
      str((E4, R4)))
# (d) ecart-type nul (aplat) : aucun gain invente, pas de division par zero.
E5 = CALL(CM, "match_effect", {"y": (100.0, 0.0), "u": (128.0, 0.0), "v": (128.0, 0.0)},
          {"y": (50.0, 0.0), "u": (120.0, 0.0), "v": (128.0, 0.0)})
check("t3_match_ecart_type_nul_gain_1",
      EFF_OK(E5) and E5["y_gain"] == 1 and abs(E5["y_off"] - 50) < 1e-6 and abs(E5["u_off"] - 8) < 1e-6,
      str(E5))
# (e) auto : un plan teinte est neutralise, un plan neutre n'est PAS teinte.
EA = CALL(CM, "auto_effect", S_TEI)
RA = RENDU_STATS(TEINTE, [EA] if isinstance(EA, dict) else [])
try:
    _du0, _dv0 = abs(S_TEI["u"][0] - 128), abs(S_TEI["v"][0] - 128)
    _du1, _dv1 = abs(RA["u"][0] - 128), abs(RA["v"][0] - 128)
    _dy = abs(RA["y"][0] - S_TEI["y"][0])
except Exception:                                        # noqa: BLE001
    _du0 = _dv0 = _du1 = _dv1 = _dy = None
check("t3_auto_neutralise_un_plan_teinte",
      EFF_OK(EA) and _du0 is not None and _du0 >= 8 and _dv0 >= 8
      and _du1 <= _du0 / 2 and _dv1 <= _dv0 / 2 and _dy <= 3,
      str((EA, (_du0, _dv0), (_du1, _dv1), _dy)))
check("t3_auto_contraste_releve_si_plat_pas_si_riche",
      EFF_OK(EA) and EA["y_gain"] > 1.2 and isinstance(CALL(CM, "auto_effect", S_TS), dict)
      and CALL(CM, "auto_effect", S_TS)["y_gain"] == 1,
      str((EA, CALL(CM, "auto_effect", S_TS))))
EN = CALL(CM, "auto_effect", S_GRIS)
RN = RENDU_STATS(GRIS, [EN] if isinstance(EN, dict) else [])
check("t3_auto_sur_plan_neutre_ne_teinte_pas",
      EFF_OK(EN) and abs(EN["u_off"]) <= 2 and abs(EN["v_off"]) <= 2
      and STATS_OK(RN) and abs(SV(RN, "u") - 128) <= 2 and abs(SV(RN, "v") - 128) <= 2,
      str((EN, RN)))

# =============================================================================
print("\n[4] D-31 — image etalonnee, scopes, routes (grading.py)")
# =============================================================================
from PIL import Image as _PI                             # noqa: E402


def IMG(p):
    try:
        return _PI.open(p).copy()
    except Exception:                                    # noqa: BLE001
        return None


def SZ(p):
    """Taille de l'image `p`, ou None — jamais d'exception (faute n6)."""
    im = IMG(p)
    return im.size if im is not None else None


def MOYZ(im, box=None):
    try:
        z = (im.crop(box) if box else im).convert("L")
        _gf = getattr(z, "get_flattened_data", None) or z.getdata
        px = list(_gf())
        return sum(px) / len(px)
    except Exception:                                    # noqa: BLE001
        return None


EXPO = [{"type": "grade_basic", "exposure": -100}]
g0 = CALL(GR, "graded_frame", TS, 1.0)
g0i = IMG(g0) if isinstance(g0, pathlib.Path) else None
check("t4_graded_frame_png_512_par_defaut",
      g0i is not None and g0i.size == (512, 288) and str(g0).endswith(".png")
      and "montage_cache" in str(g0),
      str((g0, g0i.size if g0i else None)))
g240 = CALL(GR, "graded_frame", TS, 1.0, None, None, 240, "jpg")
try:
    _jb = pathlib.Path(g240).read_bytes()[:3]
except Exception:                                        # noqa: BLE001
    _jb = b""
check("t4_graded_frame_jpeg_240", _jb == b"\xff\xd8\xff" and IMG(g240) is not None
      and IMG(g240).size == (240, 136), str((g240, _jb)))
gd = CALL(GR, "graded_frame", GPLAT, 1.0, EXPO)
gn = CALL(GR, "graded_frame", GPLAT, 1.0)
_ld, _ln = MOYZ(IMG(gd)), MOYZ(IMG(gn))
check("t4_graded_frame_applique_la_pile_plus_sombre",
      None not in (_ld, _ln) and 120 <= _ln <= 136 and _ln - _ld >= 20, str((_ld, _ln)))
# Masque ellipse au centre : centre assombri, coin intact.
MSK = {"shape": "ellipse", "x": 0.3, "y": 0.3, "w": 0.4, "h": 0.4, "soft": 0}
gm = CALL(GR, "graded_frame", GPLAT, 1.0, EXPO, MSK)
_im = IMG(gm)
_c, _k = MOYZ(_im, (246, 134, 266, 154)), MOYZ(_im, (0, 0, 20, 20))
check("t4_graded_frame_masque_centre_sombre_coin_intact",
      None not in (_c, _k, _ln) and _ln - _c >= 20 and abs(_k - _ln) <= 3, str((_c, _k, _ln)))
# Hors duree : ffmpeg NU ne rend rien (temoin mesure), graded_frame recule.
_far = FX3 / "far.png"
try:
    subprocess.run([FF, "-y", "-v", "error", "-ss", "50", "-i", TS, "-frames:v", "1", str(_far)],
                   capture_output=True, timeout=60)
except Exception:                                        # noqa: BLE001
    pass
gfar = CALL(GR, "graded_frame", TS, 50.0)
check("t4_hors_duree_ffmpeg_nu_rien_graded_frame_derniere_image",
      not _far.exists() and IMG(gfar) is not None, str((_far.exists(), gfar)))
# Revue T3 R-1 : le recul fixe de 0,1 s lisait `format=duration`. MESURE
# (24/09, 8.1.1 = 9.0.1) : a 5 i/s sur 2 s, -ss 1,85 et au-dela ne rendent
# RIEN ; video 2 s + audio 2,3 s, `format=duration` vaut 2,3 et -ss 2,0 et
# au-dela ne rendent rien. Temoins : ffmpeg NU ne rend rien a 1,9 / 2,2.
F5 = MKV("f5.mp4", "testsrc2=s=320x180:r=5:d=2")
FA = MKV("fa.mp4", "", d=2.3, extra=["-f", "lavfi", "-i", "testsrc2=s=320x180:r=25:d=2",
                                     "-f", "lavfi", "-i", "sine=d=2.3", "-c:a", "aac"])


def NU(src, t, nom):
    """ffmpeg NU a `t` : l'image existe-t-elle ? (temoin des fixtures)"""
    o = FX3 / nom
    try:
        subprocess.run([FF, "-y", "-v", "error", "-ss", str(t), "-i", src, "-frames:v", "1", str(o)],
                       capture_output=True, timeout=60)
    except Exception:                                    # noqa: BLE001
        pass
    return o.exists()


_nu5, _nua = NU(F5, 1.9, "nu5.png") if F5 else None, NU(FA, 2.2, "nua.png") if FA else None
g5 = CALL(GR, "graded_frame", F5, 2.0)
ga = CALL(GR, "graded_frame", FA, 2.2)
check("t4_fin_lisible_5ips_et_audio_plus_long_temoins_nus_vides",
      None not in (F5, FA) and _nu5 is False and _nua is False
      and SZ(g5) == (512, 288) and SZ(ga) == (512, 288),
      str((F5, FA, _nu5, _nua, g5, ga)))
# Revue T3 (second tour) : en .mkv / .webm, `stream=duration` est VIDE — la
# duree du flux video est dans le tag `DURATION` (« 00:00:02.000000000 ») ;
# le repli `format=duration` inclut l'audio plus long (mesure : 2,623 s pour
# une video de 2,00 s + audio 2,6 s). Temoin : ffmpeg NU a 2,5 ne rend rien.
FMK = MKV("fa26.mkv", "", d=2.6, extra=["-f", "lavfi", "-i", "testsrc2=s=320x180:r=25:d=2",
                                        "-f", "lavfi", "-i", "sine=d=2.6", "-c:a", "aac"])
FWB = MKV("fa26.webm", "", d=2.6, extra=["-f", "lavfi", "-i", "testsrc2=s=320x180:r=25:d=2",
                                         "-f", "lavfi", "-i", "sine=d=2.6",
                                         "-c:v", "libvpx", "-c:a", "libopus"])
_numk = NU(FMK, 2.5, "nuk.png") if FMK else None
_nuwb = NU(FWB, 2.5, "nuwb.png") if FWB else None
gmk = CALL(GR, "graded_frame", FMK, 2.5)
gwb = CALL(GR, "graded_frame", FWB, 2.5)
_pmk = CALL(GR, "_probe", pathlib.Path(FMK)) if FMK else None
_pwb = CALL(GR, "_probe", pathlib.Path(FWB)) if FWB else None
check("t4_mkv_webm_duree_du_flux_par_tag_temoins_nus_vides",
      None not in (FMK, FWB) and _numk is False and _nuwb is False
      and SZ(gmk) == (512, 288) and SZ(gwb) == (512, 288),
      str((FMK, FWB, _numk, _nuwb, gmk, gwb, _pmk, _pwb)))
# Lecture robuste du tag : heures/minutes comptees, variante de cle, illisible -> 0.
_hv = [CALL(GR, "_hms", v) for v in ("01:02:03.5", "00:01:02.500000000", "2.5", "abc", "1:2:3:4", None)]
_tv = [CALL(GR, "_tag_duree", s_) for s_ in ({"tags": {"DURATION-eng": "00:00:02.000000000"}},
                                             {"tags": {"duration": "0:00:01.5"}}, {"tags": {}}, {})]
check("t4_tag_duration_lu_hms_variantes_illisible_zero",
      _hv == [3723.5, 62.5, 2.5, 0.0, 0.0, 0.0] and _tv == [2.0, 1.5, 0.0, 0.0], str((_hv, _tv)))
# Cache : deuxieme appel IDENTIQUE sans aucun sous-processus ; un autre
# reglage en relance un (temoin positif de l'espion).
_sp = {"n": 0, "cmds": []}
_run0 = subprocess.run


def _espion_run(*a, **k):
    _sp["n"] += 1
    try:
        _sp["cmds"].append([str(x) for x in (a[0] if a else k.get("args") or [])])
    except Exception:                                    # noqa: BLE001
        pass
    return _run0(*a, **k)


# M-3 : un succes du cache RAFRAICHIT la date du fichier (LRU approche).
try:
    os.utime(gd, (1000, 1000))
except Exception as _e:                                  # noqa: BLE001
    print("  (utime gd : %r)" % _e)
subprocess.run = _espion_run
try:
    gd2 = CALL(GR, "graded_frame", GPLAT, 1.0, EXPO)
    _n_hit = _sp["n"]
    gd3 = CALL(GR, "graded_frame", GPLAT, 1.0, [{"type": "grade_basic", "exposure": -50}])
    _n_miss = _sp["n"] - _n_hit
    sc1 = CALL(GR, "scopes_png", TS, 1.0)
    _n_sc = _sp["n"]
    sc1b = CALL(GR, "scopes_png", TS, 1.0)
    _n_sc_hit = _sp["n"] - _n_sc
finally:
    subprocess.run = _run0
try:
    _mt_hit = pathlib.Path(gd2).stat().st_mtime
except Exception:                                        # noqa: BLE001
    _mt_hit = None
check("t4_cache_second_appel_sans_ffmpeg_autre_reglage_avec",
      gd2 == gd and isinstance(gd, pathlib.Path) and _n_hit == 0 and _n_miss >= 1
      and isinstance(gd3, pathlib.Path) and gd3 != gd,
      str((gd, gd2, gd3, _n_hit, _n_miss)))
check("t4_cache_servi_rafraichit_la_date", _mt_hit is not None and _mt_hit > 1e9, str(_mt_hit))
# M-2 : ffprobe en memoire (source deja sondee -> UN seul sous-processus,
# ffmpeg) ; PNG sans `-q:v` (mesure : octets identiques avec ou sans).
_png_cmds = [cm for cm in _sp["cmds"] if "-filter_complex" in cm and cm[-1].endswith(".png")]
check("t4_probe_en_memoire_un_seul_sous_processus_png_sans_q",
      _n_miss == 1 and len(_png_cmds) >= 2 and not any("-q:v" in cm for cm in _png_cmds),
      str((_n_miss, [cm[:1] + cm[-3:] for cm in _sp["cmds"]])))
sci = IMG(sc1) if isinstance(sc1, pathlib.Path) else None
check("t4_scopes_png_512x512_et_cache",
      sci is not None and sci.size == (512, 512) and sc1b == sc1 and _n_sc_hit == 0,
      str((sc1, sci.size if sci else None, _n_sc_hit)))
sc2 = CALL(GR, "scopes_png", TS, 1.0, EXPO)
try:
    _dif = pathlib.Path(sc2).read_bytes() != pathlib.Path(sc1).read_bytes()
except Exception:                                        # noqa: BLE001
    _dif = False
check("t4_scopes_calcules_sur_l_image_etalonnee", _dif and sc2 != sc1, str((sc1, sc2)))
# Revue T3 (second tour) : le SECOND ESSAI est garde SEUL. Les fixtures
# passent au premier essai grace au recul ; ici `_probe` GONFLE la duree
# d'une image (dur + 1/fps) : le premier essai tombe sur 2,0 s de la source
# 5 i/s (muet, mesure), seul le second (t - 1/fps) rend. Deux ffmpeg exiges.
_probe0 = getattr(GR, "_probe", None)


def _probe_gonfle(p):
    d_, w_, h_, f_ = _probe0(p)
    return (d_ + 1.0 / f_, w_, h_, f_)


try:
    pathlib.Path(g5).unlink()
except Exception as _e:                                  # noqa: BLE001
    print("  (unlink g5 : %r)" % _e)
_sp["n"], _sp["cmds"] = 0, []
_se = "ABSENT"
if _probe0 is not None and F5:
    GR._probe = _probe_gonfle
    subprocess.run = _espion_run
    try:
        _se = CALL(GR, "graded_frame", F5, 2.0)
    finally:
        subprocess.run = _run0
        GR._probe = _probe0
_ff_se = [cm for cm in _sp["cmds"] if "-filter_complex" in cm]
check("t4_second_essai_seul_rend_quand_le_premier_est_muet",
      SZ(_se) == (512, 288) and len(_ff_se) == 2,
      str((_se, [cm[cm.index("-ss") + 1] if "-ss" in cm else "?" for cm in _ff_se])))
# I-1 : sous Windows `os.replace` leve PermissionError [WinError 5] quand la
# cible est ouverte en lecture (FileResponse qui la sert, mesure 24/09). Un
# re-rendu de la meme cle ne doit ni lever ni laisser de `.tmp.` orphelin.
_gi = CALL(GR, "graded_frame", TS, 1.3, None, None, 64, "png")
try:
    _parts = GR._grade_graph([], None, 64, 36, "gout")
    with open(_gi, "rb"):
        _ri = CALL(GR, "_render", pathlib.Path(TS), 1.3, _parts, "gout", _gi, "l'image etalonnee")
    _orph = sorted(p.name for p in _gi.parent.glob(_gi.stem + ".*.tmp*"))
except Exception as _e:                                  # noqa: BLE001
    _ri, _orph = repr(_e), None
if os.name == "nt":                                      # verrou Windows seul
    check("t4_cible_ouverte_en_lecture_rerendu_sans_erreur_ni_tmp",
          isinstance(_gi, pathlib.Path) and _ri == _gi and _orph == [], str((_gi, _ri, _orph)))
else:
    check("t4_cible_ouverte_en_lecture_SKIP", True)
    print("  SKIP  t4_cible_ouverte_en_lecture : pas de verrou de lecture hors Windows")
# R-2b : un effet BORNE t0/t1 est juge tel qu'il s'applique en plein (les
# bornes temporelles sont retirees avant la chaine) : a t=1 un effet borne
# 5..6 s assombrit QUAND MEME l'image.
gt = CALL(GR, "graded_frame", GPLAT, 1.0, [dict(EXPO[0], t0=5, t1=6, fade_in=0.2, ease_in="smooth")])
_lt = MOYZ(IMG(gt))
check("t4_effet_borne_t0_t1_juge_en_plein",
      None not in (_lt, _ln) and _ln - _lt >= 20 and gt == gd, str((gt, gd, _lt, _ln)))
# M-1 : un effet `off: true` n'est PAS applique (build_chain ignore `off` :
# on le filtre avant) et sort de la cle ; `label` n'entre pas dans la cle.
goff = CALL(GR, "graded_frame", GPLAT, 1.0, [dict(EXPO[0], off=True)])
glab = CALL(GR, "graded_frame", GPLAT, 1.0, [dict(EXPO[0], label="Mon reglage")])
_lo = MOYZ(IMG(goff))
check("t4_effet_off_non_applique_label_hors_cle",
      goff == gn and None not in (_lo, _ln) and abs(_lo - _ln) <= 1 and glab == gd,
      str((goff, gn, _lo, _ln, glab, gd)))
# M-1 : le mtime d'une LUT `.cube` referencee entre dans la cle — la LUT
# reecrite rend une AUTRE image (temoin : identite puis assombrissement).
try:
    from app.config import settings as _cfg
    _ld = _cfg.luts_path
    _ld.mkdir(parents=True, exist_ok=True)
    _cube = _ld / "zz_t3.cube"
    _cube.write_text("LUT_3D_SIZE 2\n" + "".join(
        "%d %d %d\n" % (r_, g_, b_) for b_ in (0, 1) for g_ in (0, 1) for r_ in (0, 1)), encoding="ascii")
    os.utime(_cube, (2000, 2000))
    gl1 = CALL(GR, "graded_frame", GPLAT, 1.0, [{"type": "grade", "file": "zz_t3.cube"}])
    _cube.write_text("LUT_3D_SIZE 2\n" + "0.1 0.1 0.1\n" * 8, encoding="ascii")
    os.utime(_cube, (3000, 3000))
    gl2 = CALL(GR, "graded_frame", GPLAT, 1.0, [{"type": "grade", "file": "zz_t3.cube"}])
except Exception as _e:                                  # noqa: BLE001
    gl1 = gl2 = repr(_e)
_m1, _m2 = MOYZ(IMG(gl1)), MOYZ(IMG(gl2))
check("t4_lut_reecrite_autre_cle_autre_image",
      isinstance(gl1, pathlib.Path) and isinstance(gl2, pathlib.Path) and gl1 != gl2
      and None not in (_m1, _m2, _ln) and abs(_m1 - _ln) <= 3 and _m1 - _m2 >= 40,
      str((gl1, gl2, _m1, _m2, _ln)))
# Echec lisible : une source indecodable -> MediaError, jamais une exception nue.
_txt = FX3 / "pas_une_video.mp4"
_txt.write_text("rien", encoding="utf-8")
_ge = CALL(GR, "graded_frame", str(_txt), 1.0)
check("t4_source_indecodable_media_error", isinstance(_ge, str) and _ge.startswith("EXC MediaError"),
      str(_ge))
# Elagage borne PAR MOTIF : les plus recents survivent, un autre motif
# (filmstrip du meme dossier) n'est jamais touche. Revue T3 I-2 : les
# fixtures sont datees dans le FUTUR — datees de 1970, les vraies images du
# banc etaient plus recentes et « tout effacer » passait le check. On exige
# EXACTEMENT les deux plus recents.
import time as _time                                     # noqa: E402
_now = _time.time()
try:
    from app.services import montage_media as _MM3
    _cd = _MM3._cache_dir()
    for _i in range(5):
        _f = _cd / ("zz%02d_grade.jpg" % _i)
        _f.write_bytes(b"x")
        os.utime(_f, (_now + 1000 + _i, _now + 1000 + _i))
    (_cd / "zz_strip6x78x44.jpg").write_bytes(b"x")
    os.utime(_cd / "zz_strip6x78x44.jpg", (10, 10))
except Exception as _e:                                  # noqa: BLE001
    print("  (fixture elagage : %r)" % _e)
_pr = CALL(GR, "prune_cache", {"*_grade.*": 2})
try:
    _rest = sorted(p.name for p in _MM3._cache_dir().glob("zz*"))
except Exception:                                        # noqa: BLE001
    _rest = []
check("t4_elagage_borne_par_motif",
      isinstance(_pr, dict) and "zz_strip6x78x44.jpg" in _rest
      and [n for n in _rest if n.startswith("zz0")] == ["zz03_grade.jpg", "zz04_grade.jpg"],
      str((_pr, _rest)))
# M-3 : un `unlink` qui echoue (fichier ouvert : WinError 32, mesure) ne
# stoppe pas l'elagage des suivants.
try:
    for _i in range(5):
        _f = _cd / ("zz1%d_grade.jpg" % _i)
        _f.write_bytes(b"x")
        os.utime(_f, (_now + 2000 + _i, _now + 2000 + _i))
    with open(_cd / "zz12_grade.jpg", "rb"):
        _pr2 = CALL(GR, "prune_cache", {"*_grade.*": 2})
    _rest2 = sorted(p.name for p in _cd.glob("zz1*"))
except Exception as _e:                                  # noqa: BLE001
    _pr2, _rest2 = repr(_e), None
if os.name == "nt":                                      # verrou Windows seul
    check("t4_elagage_un_echec_n_arrete_pas_les_suivants",
          _rest2 == ["zz12_grade.jpg", "zz13_grade.jpg", "zz14_grade.jpg"], str((_pr2, _rest2)))
else:
    check("t4_elagage_un_echec_SKIP", True)
    print("  SKIP  t4_elagage_un_echec : pas de verrou de lecture hors Windows")

# --- routes : Request starlette reelle (patron test_montage_l7b.py) ---------
from app.services import montage_service as MS           # noqa: E402


def RQ(body, hote="127.0.0.1", path="/api/montage/x"):
    from starlette.requests import Request as _R
    raw = json.dumps(body).encode("utf-8")

    async def rcv():
        return {"type": "http.request", "body": raw, "more_body": False}
    return _R({"type": "http", "method": "POST", "path": path, "query_string": b"",
               "headers": [(b"content-type", b"application/json")], "client": (hote, 5000)}, rcv)


def ROUTE(nom, body, hote="127.0.0.1"):
    """(statut, corps, entetes) ; l'absence de la route est un temoin."""
    f = getattr(MS, nom, None)
    if f is None:
        return ("ABSENT", None, None)
    try:
        r = asyncio.run(f(RQ(body, hote)))
    except Exception as e:                               # noqa: BLE001
        return (getattr(e, "status_code", type(e).__name__), getattr(e, "detail", str(e)), None)
    if isinstance(r, dict):
        return (200, r, None)
    return (getattr(r, "status_code", None), getattr(r, "path", None), dict(getattr(r, "headers", {}) or {}))


FP = lambda p, t=1.0: {"src": {"file_path": p}, "t": t}  # noqa: E731
st, bd, _ = ROUTE("montage_color_match", {"target": FP(TS), "ref": FP(ORG)})
check("t4_route_color_match_ref_200",
      st == 200 and isinstance(bd, dict) and bd.get("ok") is True and EFF_OK(bd.get("effect"))
      and STATS_OK(bd.get("ref")) and STATS_OK(bd.get("target")), str((st, bd)))
st, bd, _ = ROUTE("montage_color_match", {"target": FP(TEINTE), "auto": True})
check("t4_route_color_match_auto_200_ref_nulle",
      st == 200 and isinstance(bd, dict) and EFF_OK(bd.get("effect")) and bd.get("ref") is None
      and STATS_OK(bd.get("target")), str((st, bd)))
st, bd, _ = ROUTE("montage_color_match", {"target": FP(TS)})
check("t4_route_color_match_ni_ref_ni_auto_400", st == 400, str((st, bd)))
st, bd, _ = ROUTE("montage_color_match", {"target": {"src": {"file_path": str(FX3 / "absent.mp4")}, "t": 1}, "auto": True})
check("t4_route_color_match_source_inconnue_404", st == 404, str((st, bd)))
st, bd, _ = ROUTE("montage_color_match", {"target": FP(TS), "auto": True}, hote="10.0.0.9")
check("t4_route_color_match_hors_localhost_403_temoin_local_200",
      st == 403 and ROUTE("montage_color_match", {"target": FP(TS), "auto": True})[0] == 200, str((st, bd)))
st, bd, hd = ROUTE("montage_scopes", {"src": {"file_path": TS}, "t": 1.0, "effects": EXPO})
check("t4_route_scopes_png_no_store",
      st == 200 and (hd or {}).get("content-type") == "image/png"
      and (hd or {}).get("cache-control") == "no-store" and IMG(bd) is not None
      and IMG(bd).size == (512, 512), str((st, bd, hd)))
st, bd, hd = ROUTE("montage_grade_frame", {"src": {"file_path": TS}, "t": 1.0, "effects": EXPO,
                                           "mask": MSK, "w": 241})
check("t4_route_grade_frame_jpeg_w_pair_max_age",
      st == 200 and (hd or {}).get("content-type") == "image/jpeg"
      and "max-age=3600" in ((hd or {}).get("cache-control") or "") and IMG(bd) is not None
      and IMG(bd).size[0] == 240, str((st, bd, hd)))
st, bd, hd = ROUTE("montage_grade_frame", {"src": {"file_path": TS}, "t": 1.0})
check("t4_route_grade_frame_defaut_240", st == 200 and IMG(bd) is not None and IMG(bd).size[0] == 240,
      str((st, bd)))
_w9 = ROUTE("montage_grade_frame", {"src": {"file_path": TS}, "t": 1.0, "w": 9999})
_w1 = ROUTE("montage_grade_frame", {"src": {"file_path": TS}, "t": 1.0, "w": 10})
_s9, _s1 = SZ(_w9[1]), SZ(_w1[1])
check("t4_route_grade_frame_w_borne_96_640",
      _w9[0] == 200 and _s9 is not None and _s9[0] == 640
      and _w1[0] == 200 and _s1 is not None and _s1[0] == 96,
      str((_w9[:2], _s9, _w1[:2], _s1)))
_PNG = str(FX3 / "image.png")
try:
    _PI.new("RGB", (32, 32), (128, 128, 128)).save(_PNG)
except Exception:                                        # noqa: BLE001
    pass
_17 = [{"type": "grade_basic"}] * 17
_16 = [{"type": "grade_basic"}] * 16
# Revue T3 R-2 : statuts calcules AVANT le check, detail = les statuts.
_st16 = (ROUTE("montage_scopes", {"src": {"file_path": TS}, "t": 1, "effects": _17})[0],
         ROUTE("montage_grade_frame", {"src": {"file_path": TS}, "t": 1, "effects": _17})[0],
         ROUTE("montage_grade_frame", {"src": {"file_path": TS}, "t": 1, "effects": _16})[0])
check("t4_routes_plus_de_16_effets_400_temoin_16_200", _st16 == (400, 400, 200), str(_st16))
_stt = (ROUTE("montage_scopes", {"src": {"file_path": TS}, "t": -1})[0],
        ROUTE("montage_scopes", {"src": {"file_path": TS}, "t": "abc"})[0],
        ROUTE("montage_grade_frame", {"src": {"file_path": TS}, "t": 1, "effects": {"type": "x"}})[0],
        ROUTE("montage_scopes", {"src": {"file_path": TS}, "t": 1})[0])
check("t4_routes_t_illisible_ou_negatif_400_effects_non_liste_400", _stt == (400, 400, 400, 200),
      str(_stt))
_st4 = (ROUTE("montage_scopes", {"src": {"file_path": TS}, "t": 1}, hote="192.168.1.2")[0],
        ROUTE("montage_grade_frame", {"src": {"file_path": TS}, "t": 1}, hote="192.168.1.2")[0],
        ROUTE("montage_scopes", {"src": {"file_path": str(FX3 / "absent.mp4")}, "t": 1})[0],
        ROUTE("montage_grade_frame", {"src": {"file_path": _PNG}, "t": 1})[0])
check("t4_routes_scopes_grade_frame_403_404_415", _st4 == (403, 403, 404, 415), str(_st4))
# Bout a bout par HTTP (TestClient : hote `testclient`, accepte).
try:
    _h = c.post("/api/montage/grade-frame", json={"src": {"file_path": TS}, "t": 1.0})
    _hs = c.post("/api/montage/scopes", json={"src": {"file_path": TS}, "t": 1.0})
    _hc = c.post("/api/montage/color-match", json={"target": FP(TS), "auto": True})
    _hst = (_h.status_code, _h.headers.get("content-type"), _hs.status_code, _hc.status_code,
            J(_hc).get("ok"))
except Exception as _e:                                  # noqa: BLE001
    _hst = repr(_e)
check("t4_routes_montees_http", _hst == (200, "image/jpeg", 200, 200, True), str(_hst))

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
