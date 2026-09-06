# -*- coding: utf-8 -*-
"""P16 — TRADUIRE LES REPLIQUES (POST /api/subtitles/translate,
GET /api/subtitles/translate/estimate).

Run : & $PY tests/test_subs_traduction.py   (depuis backend/)

LE CAS CONCRET (remontee du 06/09/2026, fait n°4 du lot 5) : « je dois
pouvoir faire fonctionner la transcription dans la langue de mon choix […]
ne serait-ce que pour pouvoir la traduire ». AUCUNE route de traduction de
sous-titres n'existait (mesure : le seul `translate_video` est HeyGen,
jamais appele).

CE QUE CE BANC FERME :
  [1] le contrat « N lignes numerotees » : N lignes → N segments aux MEMES
      start/end, textes traduits, `provider` et `usd` rendus ;
  [2] N−1 lignes → 400 « rien n'a ete ecrit », AUCUN segment rendu ;
  [3] lignes dans le desordre → remises dans l'ordre des numeros ;
  [4] une traduction qui contient « | » est conservee ENTIERE (decoupage au
      premier « | » seulement) ;
  [5] un numero duplique → 400 qui le nomme ;
  [6] bouchon qui rend "" → 400 (0 lignes sur N) sans mourir ; bouchon qui
      LEVE → 502 lisible « Le modele n'a pas repondu » ;
  [7] segments vides → 400 ; target vide → 400 — et AUCUN appel au modele
      dans ces deux cas ;
  [8] estimate sans cle → ok:false + raison lisible ; avec cle (bouchon
      d'active_provider) → usd > 0, provider nomme ;
  [9] AUCUN APPEL RESEAU : `summarizer._chat_dispatch` est BOUCHONNE par
      attribut de module (il compte ses appels), `httpx.post`/`httpx.get`
      sont coupes et comptes (0 sur tout le banc).

LA REGLE DES ASSERTIONS NEGATIVES (en-tete de test_montage_media.py) : toute
negation est conjointe a un positif — « 0 appel » va avec « statut 400 et
detail attendu », « aucun reseau » avec « N appels au bouchon ».

MUTATIONS JOUEES SUR LA ROUTE ET LE SERVICE (06/09/2026, chacune rejouee
puis retiree) — voir le rapport du commit : retirer la garde de compte
(`len(vues) != n`), retirer le re-tri par numero, decouper a TOUS les « | »,
retirer la garde du numero double, ne pas conserver start/end, retirer
l'enveloppe ValueError→400 de la route.
"""
import json
import os
import pathlib
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzp16_")
os.environ["DEEPOTUS_DATA_DIR"] = TMP
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + (TMP + "/t.db").replace("\\", "/")
os.environ["IMAGES_FOLDER"] = TMP + "/images"
os.environ["OUTPUTS_FOLDER"] = TMP + "/outputs"
os.environ.setdefault("FAL_KEY", "test-key")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import httpx                                                # noqa: E402
from fastapi.testclient import TestClient                   # noqa: E402
from app.config import settings                             # noqa: E402
from app.main import app                                    # noqa: E402
from app.services import subs_translate_service as TR       # noqa: E402
from app.services import summarizer as SZ                   # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {detail}")


_plantages = 0


def temoin(e):
    """TEMOIN d'un appel qui a LEVE — NUMEROTE et DISTINGUABLE."""
    global _plantages
    _plantages += 1
    return "%s: %s ·ECHEC#%d" % (type(e).__name__, e, _plantages)


# ── LE DOSSIER TEMPORAIRE EST BIEN CELUI QUE L'APP LIT ────────────────────
check("prevol_le_dossier_de_donnees_est_le_temporaire",
      str(settings.images_path).startswith(TMP)
      and str(settings.outputs_path).startswith(TMP),
      f"images={settings.images_path} outputs={settings.outputs_path}")

# ── LES BOUCHONS ───────────────────────────────────────────────────────────
APPELS = []          # (prompt, system, max_tokens) — un par _chat_dispatch
N_APPELS = [0]       # le TOTAL, jamais vide par un `del APPELS[:]`
RESEAU = []          # tout httpx.post/get — doit rester VIDE
BOUCHON = {"texte": "", "provider": "anthropic", "leve": None}


def faux_dispatch(prompt, system, max_tokens):
    APPELS.append((prompt, system, max_tokens))
    N_APPELS[0] += 1
    if BOUCHON["leve"] is not None:
        raise BOUCHON["leve"]
    return BOUCHON["texte"], BOUCHON["provider"]


def _interdit(*a, **k):
    RESEAU.append(str(a[0] if a else k.get("url")))
    raise AssertionError("appel réseau interdit dans ce banc")


DISPATCH_REEL = SZ._chat_dispatch
SZ._chat_dispatch = faux_dispatch
httpx.post = _interdit
httpx.get = _interdit

check("bouchon_dispatch_en_place_et_distinct_du_reel",
      SZ._chat_dispatch is faux_dispatch and DISPATCH_REEL is not faux_dispatch
      and callable(DISPATCH_REEL))

client = TestClient(app)
U = "/api/subtitles/translate"

SEGS = [{"start": 28.876, "end": 31.2, "text": "Bonjour tout le monde"},
        {"start": 31.4, "end": 33.0, "text": "On lance le test"},
        {"start": 40.0, "end": 44.5, "text": "Et voilà la fin"}]


def post(body):
    try:
        r = client.post(U, json=body)
        return r.status_code, r.json()
    except Exception as e:                                  # noqa: BLE001
        return -1, {"detail": temoin(e)}


# ── [1] LE CONTRAT TENU : N lignes → N segments, memes temps ──────────────
BOUCHON["texte"] = "1|Hello everyone\n2|Starting the test\n3|And that's the end"
del APPELS[:]
st, d = post({"segments": SEGS, "target": "en", "source": "fr"})
check("t1_200_et_ok", st == 200 and d.get("ok") is True, f"st={st} d={d}")
check("t1_trois_segments_textes_traduits",
      [s.get("text") for s in d.get("segments") or []]
      == ["Hello everyone", "Starting the test", "And that's the end"],
      repr(d.get("segments")))
check("t1_les_temps_sont_conserves_tels_quels",
      [(s.get("start"), s.get("end")) for s in d.get("segments") or []]
      == [(28.876, 31.2), (31.4, 33.0), (40.0, 44.5)],
      repr(d.get("segments")))
check("t1_provider_usd_source_target_rendus",
      d.get("provider") == "anthropic" and float(d.get("usd") or 0) > 0
      and d.get("source") == "fr" and d.get("target") == "en",
      f"provider={d.get('provider')} usd={d.get('usd')} "
      f"source={d.get('source')} target={d.get('target')}")
check("t1_un_seul_appel_au_modele_et_le_prompt_numerote",
      len(APPELS) == 1 and "1|Bonjour tout le monde" in APPELS[0][0]
      and "3|Et voilà la fin" in APPELS[0][0]
      and "numéro|traduction" in APPELS[0][1],
      f"appels={len(APPELS)} prompt={APPELS[0][0][:120] if APPELS else '∅'}")

# ── [3] LIGNES DANS LE DESORDRE → remises dans l'ordre des numeros ────────
BOUCHON["texte"] = "3|Three\n1|One\n2|Two"
st, d = post({"segments": SEGS, "target": "en"})
check("t3_desordre_remis_dans_l_ordre",
      st == 200 and [s.get("text") for s in d.get("segments") or []]
      == ["One", "Two", "Three"],
      f"st={st} segs={d.get('segments')}")
check("t3_les_temps_suivent_les_numeros_pas_l_ordre_des_lignes",
      (d.get("segments") or [{}])[0].get("start") == 28.876
      and (d.get("segments") or [{}, {}, {}])[2].get("end") == 44.5,
      repr(d.get("segments")))

# ── [4] UN « | » DANS LA TRADUCTION : conservee ENTIERE ───────────────────
BOUCHON["texte"] = "1|A | B | C\n2|Two\n3|Three"
st, d = post({"segments": SEGS, "target": "en"})
check("t4_le_pipe_ne_coupe_pas_la_traduction",
      st == 200 and (d.get("segments") or [{}])[0].get("text") == "A | B | C",
      f"st={st} premier={((d.get('segments') or [{}])[0]).get('text')!r}")

# ── [2] N−1 LIGNES → 400, rien n'est ecrit ────────────────────────────────
BOUCHON["texte"] = "1|One\n2|Two"
del APPELS[:]
st, d = post({"segments": SEGS, "target": "en"})
check("t2_compte_faux_400_et_dit_rien_n_a_ete_ecrit",
      st == 400 and "2 lignes sur 3" in str(d.get("detail"))
      and "rien n'a été écrit" in str(d.get("detail")),
      f"st={st} detail={d.get('detail')}")
check("t2_aucun_segment_rendu_et_l_appel_a_bien_eu_lieu",
      "segments" not in d and len(APPELS) == 1,
      f"cles={sorted(d)} appels={len(APPELS)}")
# le numero manquant est NOMME (3 lignes dont un numero hors bornes).
BOUCHON["texte"] = "1|One\n2|Two\n7|Sept"
st, d = post({"segments": SEGS, "target": "en"})
check("t2_numero_hors_bornes_400_et_le_manquant_est_nomme",
      st == 400 and "numéros manquants : 3" in str(d.get("detail")),
      f"st={st} detail={d.get('detail')}")

# ── [5] NUMERO DUPLIQUE → 400 qui le nomme ────────────────────────────────
BOUCHON["texte"] = "1|One\n1|Uno\n3|Three"
st, d = post({"segments": SEGS, "target": "en"})
check("t5_numero_double_400_qui_le_nomme",
      st == 400 and "numéro 1 en double" in str(d.get("detail")),
      f"st={st} detail={d.get('detail')}")

# ── [6] BOUCHON MUET ("") → 400 sans mourir ; BOUCHON QUI LEVE → 502 ──────
BOUCHON["texte"] = ""
st, d = post({"segments": SEGS, "target": "en"})
check("t6_reponse_vide_400_zero_ligne_sur_trois",
      st == 400 and "0 lignes sur 3" in str(d.get("detail")),
      f"st={st} detail={d.get('detail')}")
BOUCHON["leve"] = RuntimeError("moteur coupé pour le banc")
st, d = post({"segments": SEGS, "target": "en"})
check("t6_bouchon_qui_leve_502_lisible",
      st == 502 and "Le modèle n'a pas répondu" in str(d.get("detail"))
      and "moteur coupé pour le banc" in str(d.get("detail")),
      f"st={st} detail={d.get('detail')}")
BOUCHON["leve"] = None

# ── [7] ENTREES VIDES → 400, AUCUN appel au modele ────────────────────────
del APPELS[:]
st, d = post({"segments": [], "target": "en"})
check("t7_segments_vides_400_dit_la_piste_vide",
      st == 400 and "Aucune réplique" in str(d.get("detail")),
      f"st={st} detail={d.get('detail')}")
st, d = post({"segments": SEGS, "target": ""})
check("t7_target_vide_400_dit_la_langue_cible",
      st == 400 and "target" in str(d.get("detail")),
      f"st={st} detail={d.get('detail')}")
st, d = post({})
check("t7_corps_vide_400", st == 400, f"st={st} d={d}")
check("t7_zero_appel_au_modele_sur_les_trois_refus",
      len(APPELS) == 0, f"appels={APPELS}")

# ── [8] ESTIMATE : sans cle → ok:false + raison ; avec cle → usd > 0 ──────
# L'ETAT « AUCUNE CLE » EST CONSTRUIT PAR BOUCHON (active_provider → "") :
# la machine du banc PEUT porter une vraie cle dans son environnement
# (mesure : c'est le cas ici, active_provider reel rend un fournisseur) —
# un banc qui comptait sur l'absence de cle verdissait chez l'un et
# rougissait chez l'autre. Conjoint : le MEME appel, bouchonne « openai »,
# rend ok:true et usd > 0 — la branche vide n'est pas la seule mesuree.
ACTIVE_REEL = SZ.active_provider
SZ.active_provider = lambda: ""
try:
    r = client.get("/api/subtitles/translate/estimate?chars=120&target=en")
    d = r.json()
finally:
    SZ.active_provider = ACTIVE_REEL
check("t8_estimate_sans_cle_ok_false_et_raison_lisible",
      r.status_code == 200 and d.get("ok") is False
      and "Aucune clé LLM" in str(d.get("reason"))
      and float(d.get("usd") or 0) == 0.0,
      f"st={r.status_code} d={d}")
SZ.active_provider = lambda: "openai"
try:
    r = client.get("/api/subtitles/translate/estimate?chars=1200&target=en")
    d = r.json()
finally:
    SZ.active_provider = ACTIVE_REEL
check("t8_estimate_avec_cle_usd_positif_et_provider_nomme",
      r.status_code == 200 and d.get("ok") is True
      and float(d.get("usd") or 0) > 0 and d.get("provider") == "openai",
      f"st={r.status_code} d={d}")
# le cout CROIT avec les caracteres (la formule n'est pas une constante).
# 1 000 caracteres au moins : pricing._line arrondit chaque ligne a 4
# decimales (mesure, pricing.py:145) et 100 caracteres chez openai tombent
# a 0,0000 $ — l'arrondi est LA CONVENTION du depot, le banc s'y plie.
SZ.active_provider = lambda: "openai"
try:
    r1 = client.get("/api/subtitles/translate/estimate?chars=1000").json()
    r2 = client.get("/api/subtitles/translate/estimate?chars=100000").json()
finally:
    SZ.active_provider = ACTIVE_REEL
check("t8_le_cout_croit_avec_les_caracteres",
      float(r2.get("usd") or 0) > float(r1.get("usd") or 0) > 0,
      f"1000c={r1.get('usd')} 100000c={r2.get('usd')}")

# ── LE PARSEUR, EN DIRECT (les memes gardes, sans HTTP) ───────────────────
try:
    _p = TR.parse_reply("2|b\n1|a", 2)
except Exception as e:                                      # noqa: BLE001
    _p = temoin(e)
check("parse_desordre_retrie", _p == ["a", "b"], repr(_p))
try:
    _p = TR.parse_reply("bruit du modele\n1|a\n2|b", 2)
except Exception as e:                                      # noqa: BLE001
    _p = temoin(e)
check("parse_le_bruit_est_ignore_le_compte_tranche",
      _p == ["a", "b"], repr(_p))
try:
    _p = TR.parse_reply("```\n1|a\n2|b\n```", 2)
except Exception as e:                                      # noqa: BLE001
    _p = temoin(e)
check("parse_les_clotures_de_code_sont_enlevees", _p == ["a", "b"], repr(_p))
# un saut de ligne DANS une replique est aplati : une ligne par numero.
_pr, _sy = TR.build_prompt([{"text": "deux\nlignes"}], "en")
check("prompt_un_saut_de_ligne_interne_est_aplati",
      "1|deux lignes" in _pr and "deux\nlignes" not in _pr, repr(_pr[-40:]))

# ── [9] AUCUN RESEAU — conjoint : le bouchon a bien travaille ─────────────
check("reseau_zero_httpx_et_le_bouchon_a_compte_ses_appels",
      len(RESEAU) == 0 and N_APPELS[0] >= 7,
      f"reseau={RESEAU} appels_dispatch={N_APPELS[0]}")
# le fichier du banc lui-meme ne porte aucun appel vivant vers un moteur —
# les jetons sont COUPES pour que cette ligne ne se lise pas elle-meme.
_moi = pathlib.Path(__file__).read_text(encoding="utf-8")
check("hygiene_aucune_url_de_moteur_dans_le_banc",
      ("api." + "openai.com") not in _moi
      and ("api." + "elevenlabs.io") not in _moi
      and ("api." + "anthropic.com") not in _moi
      and _moi.count("httpx.post = " + "_interdit") == 1,
      "une URL de moteur ou le bouchon httpx manque")

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
