# -*- coding: utf-8 -*-
"""E-B — BANC CROISE client/backend : les LITERAUX que la couche `montage.js`
et le bundle livre ecrivent en dur doivent etre CEUX du backend, de la
feuille et des infobulles, sinon le client promet ce que le serveur ne tient
pas (ou l'inverse). Fichier SEPARE de test_montage_eb.py (un processus, un
code de sortie) : il ne monte NI TestClient NI l'app — il lit la couche, le
bundle, la feuille et les sources du backend en OCTETS, et importe le
service seul pour `media_rules()`. Modele : test_montage_l3_croise.py.
Run : & $PY tests/test_montage_eb_croise.py   (depuis backend/)

CE QUI EST COMPARE, ET COMMENT. Chaque literal est extrait par une regex
GARDEE : le temoin positif (la regex trouve EXACTEMENT UNE fois) est une
assertion a part entiere, avant toute lecture du groupe — faute n°6 : aucune
lecture nue, une regex qui ne trouve rien fait ROUGIR le banc, pas mourir.

  [1] E-2 : `DZM_PROV_LBL` (couche) vs les providers REELLEMENT ecrits dans
      backend/app (`provider="…"`, `_PROVIDER = "…"`, l'enum `Provider`) :
      chaque cle de la table est un provider connu du backend, chaque
      provider connu a un groupe OU tombe « tel quel » (liste pinnee, mesuree
      le 23/09/2026) ; le repli `seedance` du provider NUL est le meme des
      deux cotes (`coalesce(JobRecord.provider, "seedance")`) ;
  [2] E-8 : `dzmInspW` 260/480/300 vs `.svm-insp{width:300px` de la feuille
      amont (son-vfx-montage.css) et l'infobulle « 260–480 px » du bundle ;
  [3] E-9 : `dzmTlH` .3/.7 vs l'infobulle « 30–70 % » du bundle ;
  [4] E-2 : `DZM_MED_PAGE=24` vs l'URL du tiroir (`limit="+DZM_MED_PAGE`,
      aucun literal `limit=`) et la borne `min(200, …)` de `list_jobs` ;
  [5] E-5/E-8/E-9 : les quatre cles localStorage, chacune LUE (getItem) et
      ECRITE (setItem) dans le bundle livre, comptes pinnes ;
  [6] E-2 : `media_rules()` = la source UNIQUE : une definition dans
      backend/app, deux appels (la route `/media-rules` et `GET /jobs?video=1`),
      et son resultat est `_VIDEO_EXTS` (comportement, pas seulement le texte).

Regle des assertions negatives : chaque « n'est pas » est precede dans la
MEME expression du temoin positif qui etablit que la mesure a eu lieu.
"""
import os
import re
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzebx_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, ".."))

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


def lire(rel):
    """Le fichier en OCTETS, decode, LF — ou "" (le banc rougit, ne meurt pas)."""
    p = os.path.join(ROOT, *rel.split("/"))
    try:
        return open(p, "rb").read().decode("utf-8-sig").replace("\r\n", "\n")
    except OSError:
        return ""


def un(motif, texte, flags=0):
    """LA regex gardee : rend le match si le motif est trouve EXACTEMENT une
    fois, None sinon. Le compte est rendu a part pour le detail des lignes."""
    ms = list(re.finditer(motif, texte, flags))
    return (ms[0] if len(ms) == 1 else None), len(ms)


def num(m, i):
    """Groupe i du match en float, ou None — jamais un float() nu."""
    try:
        return float(m.group(i)) if m else None
    except (TypeError, ValueError):
        return None


JS = lire("frontend/patches/montage.js")
BUN = lire("frontend/dist/assets/index-BEOJX8L5.js")
PIPE = lire("backend/app/services/pipeline.py")
ROUTES = lire("backend/app/api/routes.py")
CSS = lire("frontend/dist/shared/son-vfx-montage.css")
check("x0_couche_bundle_pipeline_routes_et_feuille_sont_lus_en_octets_et_non_vides",
      len(JS) > 100_000 and len(BUN) > 1_000_000 and len(PIPE) > 10_000
      and len(ROUTES) > 100_000 and len(CSS) > 10_000,
      (len(JS), len(BUN), len(PIPE), len(ROUTES), len(CSS)))

try:
    from app.services import montage_service as MS      # noqa: E402
except Exception as e:                                  # le banc rougit
    MS = None
    print(f"  (import du service impossible : {e!r})")


def A(nom, defaut):
    return getattr(MS, nom, defaut) if MS is not None else defaut


# ── [1] E-2 : DZM_PROV_LBL vs les providers du backend ───────────────────
print("\n[1] E-2 : la table des groupes de provenance vs les providers du backend")
mT, nT = un(r'var DZM_PROV_LBL=\{([^}]*)\};', JS)
check("x1_DZM_PROV_LBL_est_lu_une_fois_dans_la_couche", nT == 1 and mT is not None, nT)
_corps = mT.group(1) if mT else ""
TABLE = dict(re.findall(r'(\w+):"([^"]+)"', _corps))
check("x1_la_table_porte_au_moins_cinq_cles_et_des_libelles_non_vides",
      len(TABLE) >= 5 and all(v for v in TABLE.values()), TABLE)
# les providers REELS du backend : chaque `provider="…"` / `provider='…'`
# ecrit dans backend/app, les `_PROVIDER = "…"` et les valeurs de l'enum
_srcs = []
for d, _, fs in os.walk(os.path.join(ROOT, "backend", "app")):
    for f in fs:
        if f.endswith(".py"):
            _srcs.append(lire(os.path.relpath(os.path.join(d, f), ROOT).replace("\\", "/")))
_tout = "\n".join(_srcs)
check("x1_les_sources_du_backend_sont_lues", len(_srcs) >= 20 and len(_tout) > 500_000, (len(_srcs), len(_tout)))
BACK = set(re.findall(r'''\bprovider\s*=\s*["']([a-z0-9_]+)["']''', _tout))
BACK |= set(re.findall(r'^_[A-Z_]*PROVIDER\s*=\s*"([a-z0-9_]+)"', _tout, re.M))
_enum = un(r'class Provider\(str, Enum\):\n(?:    .*\n)+?(?=\n)', lire("backend/app/models/schemas.py"))
check("x1_l_enum_Provider_est_lue_une_fois", _enum[1] == 1 and _enum[0] is not None, _enum[1])
ENUM = set(re.findall(r'= "([a-z0-9_]+)"', _enum[0].group(0))) if _enum[0] else set()
check("x1_l_enum_porte_les_cinq_providers_historiques",
      ENUM == {"seedance", "heygen", "composition", "template", "news"}, sorted(ENUM))
BACK |= ENUM
# LA LISTE MESUREE le 23/09/2026 — pinnee : un provider qui apparait ou
# disparait du backend doit passer par ici (et par la table, ou par « tel quel »).
MESURE = {"seedance", "heygen", "composition", "template", "news", "episode", "ugc",
          "montage", "animation", "asset3d", "sprite2d", "card3d",
          "montage_proxy", "montage_stab"}
check("x1_les_providers_du_backend_sont_exactement_les_quatorze_mesures",
      len(BACK) >= 10 and BACK == MESURE, sorted(BACK ^ MESURE))
check("x1_chaque_cle_de_la_table_est_un_provider_connu_du_backend",
      len(TABLE) >= 5 and set(TABLE) <= BACK, sorted(set(TABLE) - BACK))
TEL_QUEL = BACK - set(TABLE)
check("x1_les_providers_sans_groupe_tombent_tel_quel_et_sont_ceux_ci",
      len(TABLE) >= 5 and len(BACK) >= 10
      and TEL_QUEL == {"asset3d", "sprite2d", "card3d", "montage_proxy", "montage_stab"},
      sorted(TEL_QUEL))
# les deux precalculs « tel quel » ne sont jamais servis : list_jobs les ecarte
mEx, nEx = un(r'\.notin_\(\(_PROXY_PROVIDER, _STAB_PROVIDER\)\)', PIPE)
_pp = un(r'^_PROXY_PROVIDER = "([a-z_]+)"', lire("backend/app/services/montage_service.py"), re.M)
_sp = un(r'^_STAB_PROVIDER = "([a-z_]+)"', lire("backend/app/services/montage_service.py"), re.M)
check("x1_les_deux_precalculs_tel_quel_sont_ecartes_par_list_jobs_avant_toute_chip",
      nEx == 1 and _pp[1] == 1 and _sp[1] == 1 and _pp[0] is not None and _sp[0] is not None
      and {_pp[0].group(1), _sp[0].group(1)} == {"montage_proxy", "montage_stab"}
      and {_pp[0].group(1), _sp[0].group(1)} <= TEL_QUEL, (nEx, _pp[1], _sp[1]))
# le repli du provider NUL : « seedance » des deux cotes, une fois chacun
mG, nG = un(r'function dzmProvGroupe\(p\)\{var k=\(p==null\|\|p===""\)\?"(\w+)":String\(p\);return DZM_PROV_LBL\[k\]\|\|k\}', JS)
mC, nC = un(r'func\.coalesce\(JobRecord\.provider, "(\w+)"\)\.in_\(provs\)', PIPE)
check("x1_le_provider_nul_est_lu_seedance_dans_la_couche_et_dans_list_jobs",
      nG == 1 and nC == 1 and mG is not None and mC is not None
      and mG.group(1) == mC.group(1) == "seedance" and "seedance" in TABLE, (nG, nC))
check("x1_le_groupe_du_repli_est_Studio_comme_heygen_composition_animation",
      "seedance" in TABLE and TABLE.get("seedance") == "Studio"
      and all(TABLE.get(k) == "Studio" for k in ("heygen", "composition", "animation")), TABLE)

# ── [2] E-8 : dzmInspW vs la feuille et l'infobulle ──────────────────────
print("\n[2] E-8 : les bornes de l'inspecteur")
mW, nW = un(r'function dzmInspW\(raw\)\{return Math\.round\(dzmClamp\(raw,(\d+),(\d+),(\d+)\)\)\}', JS)
check("x2_dzmInspW_est_lu_une_fois", nW == 1 and mW is not None, nW)
js_w = (num(mW, 1), num(mW, 2), num(mW, 3))
mCss, nCss = un(r'^\.svm-insp\{width:(\d+)px;', CSS, re.M)
check("x2_la_feuille_amont_ecrit_la_largeur_de_l_aside_une_fois", nCss == 1 and mCss is not None, nCss)
check("x2_le_defaut_de_la_couche_est_la_largeur_de_la_feuille_amont_300",
      js_w[2] is not None and num(mCss, 1) == js_w[2] == 300, (js_w, mCss and mCss.group(1)))
mTip, nTip = un(r"Glisser pour redimensionner l'inspecteur \((\d+)–(\d+) px\)", BUN)
check("x2_l_infobulle_du_bundle_dit_les_bornes_de_la_couche_260_480",
      nTip == 1 and mTip is not None and (num(mTip, 1), num(mTip, 2)) == (js_w[0], js_w[1]) == (260.0, 480.0),
      (nTip, js_w))
check("x2_le_defaut_est_dans_les_bornes", js_w[0] is not None and js_w[0] <= js_w[2] <= js_w[1], js_w)

# ── [3] E-9 : dzmTlH vs l'infobulle ──────────────────────────────────────
print("\n[3] E-9 : les bornes de la hauteur de la timeline")
mH, nH = un(r'var n=dzmClamp\(raw,(\.\d+)\*t,(\.\d+)\*t,NaN\);', JS)
check("x3_la_borne_de_tlH_est_lue_une_fois", nH == 1 and mH is not None, nH)
js_h = (num(mH, 1), num(mH, 2))
mTh, nTh = un(r'Glisser pour régler la hauteur de la timeline \((\d+)–(\d+) %\)', BUN)
check("x3_l_infobulle_du_bundle_dit_30_70_et_la_couche_borne_3_7",
      nTh == 1 and mTh is not None and js_h == (0.3, 0.7)
      and (num(mTh, 1), num(mTh, 2)) == (js_h[0] * 100, js_h[1] * 100), (nTh, js_h))
# la meme infobulle vient du patcher (section EB7b) : une seule ecriture livree
mP, nP = un(r'Glisser pour régler la hauteur de la timeline \(30–70 %\)', lire("scripts/patch_bundle_montage.py"))
check("x3_le_patcher_porte_l_infobulle_une_fois_comme_le_bundle", nP == 1 and nTh == 1, (nP, nTh))

# ── [4] E-2 : DZM_MED_PAGE vs l'URL et la borne serveur ──────────────────
print("\n[4] E-2 : la page du tiroir vs la borne du serveur")
mPg, nPg = un(r'var DZM_MED_PAGE=(\d+),DZM_MED_REPOS=(\d+);', JS)
check("x4_DZM_MED_PAGE_et_REPOS_sont_lus_une_fois", nPg == 1 and mPg is not None, nPg)
mU, nU = un(r'var u="/api/jobs\?limit="\+DZM_MED_PAGE\+"&offset="\+off\+"&video=1"', JS)
# (le commentaire du tiroir cite l'URL avec `limit=24` en clair : on ne
#  compte que la forme CODE, entre guillemets)
check("x4_l_url_du_tiroir_prend_la_constante_et_aucun_literal_limit_dans_le_code",
      nU == 1 and mU is not None and JS.count('"/api/jobs?limit=') == 1
      and re.search(r'"/api/jobs\?limit=\d', JS) is None, (nU, JS.count('"/api/jobs?limit=')))
mLim, nLim = un(r'limit = max\(1, min\((\d+), int\(limit\)\)\)', PIPE)
check("x4_la_page_24_tient_dans_la_borne_1_200_du_serveur",
      nLim == 1 and mLim is not None and num(mPg, 1) == 24 and 1 <= num(mPg, 1) <= num(mLim, 1) == 200,
      (nLim, mPg and mPg.group(1), mLim and mLim.group(1)))
check("x4_la_page_du_bundle_est_celle_de_la_couche",
      mPg is not None and BUN.count(mPg.group(0)) == 1, mPg and BUN.count(mPg.group(0)))
check("x4_le_repos_de_la_frappe_est_250_ms", num(mPg, 2) == 250, mPg and mPg.group(2))

# ── [5] les quatre cles localStorage, lues ET ecrites dans le bundle ─────
print("\n[5] E-5/E-8/E-9 : les cles localStorage, lecture et ecriture")
CLES = {"dz_montage_lastfin": (1, 1), "dz_svm_insp": (1, 2), "dz_svm_tlh": (1, 1), "dz_svm_showdur": (1, 1)}
for k, (ng, ns) in CLES.items():
    g = BUN.count(f'localStorage.getItem("{k}")')
    s = BUN.count(f'localStorage.setItem("{k}"')
    check(f"x5_{k}_est_lue_x{ng}_et_ecrite_x{ns}_dans_le_bundle",
          g == ng and s == ns and g >= 1 and s >= 1, (g, s))
# les cles `dz_svm_*` / `dz_montage_last*` du bundle sont EXACTEMENT ces
# quatre plus les deux des lots anterieurs (`dz_svm_keymap`, `dz_svm_theme`),
# mesure du 23/09/2026 : une cle neuve doit passer par ici
_ANTERIEURES = {"dz_svm_keymap", "dz_svm_theme"}
_lues = set(re.findall(r'localStorage\.(?:get|set)Item\("(dz_svm_\w+|dz_montage_last\w*)"', BUN))
check("x5_les_cles_dz_svm_et_dz_montage_last_du_bundle_sont_les_quatre_plus_keymap_et_theme",
      sum(BUN.count(f'"{k}"') for k in CLES) >= 8 and len(_lues) == 6
      and _lues == set(CLES) | _ANTERIEURES, sorted(_lues))
# la couche, elle, ne touche pas localStorage : les fonctions sont pures
_coeur = JS[JS.find("function dzmFinKey(pid){"):JS.find("var DzTracks={")]
check("x5_le_coeur_E5_E8_E9_D7_de_la_couche_ne_touche_pas_localStorage",
      len(_coeur) > 2000 and _coeur.count("localStorage") == 0, (len(_coeur), _coeur.count("localStorage")))

# ── [6] media_rules() : la source unique ─────────────────────────────────
print("\n[6] E-2 : media_rules() est l'unique juge")
_defs = sum(s.count("\ndef media_rules() -> dict:") for s in _srcs)
check("x6_une_seule_definition_de_media_rules_dans_backend_app", _defs == 1, _defs)
_appels = [(rel, n) for rel, n in (
    ("routes.py", len(re.findall(r'^\s+exts = tuple\(_ms\.media_rules\(\)\.get\("video_exts"\) or \(\)\)$', ROUTES, re.M))),
    ("montage_service.py", len(re.findall(r'^    return media_rules\(\)$', lire("backend/app/services/montage_service.py"), re.M))))]
check("x6_deux_appels_la_route_jobs_video_1_et_la_route_media_rules",
      _appels == [("routes.py", 1), ("montage_service.py", 1)], _appels)
_mr = A("media_rules", None)
_ve = A("_VIDEO_EXTS", None)
_res = _mr() if callable(_mr) else None
check("x6_media_rules_rend_video_exts_egal_a_VIDEO_EXTS_et_rien_d_autre",
      callable(_mr) and isinstance(_ve, tuple) and len(_ve) >= 3 and isinstance(_res, dict)
      and list(_res.keys()) == ["video_exts"] and _res["video_exts"] == list(_ve)
      and "video_providers" not in _res, (_res, _ve))
check("x6_le_client_ne_recopie_pas_la_regle_aucune_liste_d_extensions_video_dans_la_couche",
      len(JS) > 100_000 and isinstance(_ve, tuple) and len(_ve) >= 3
      and not all(f'"{x}"' in JS for x in _ve)
      and JS.count("function dzmIsVideoJob(j,exts){") == 1,
      [x for x in _ve if f'"{x}"' in JS] if isinstance(_ve, tuple) else _ve)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
