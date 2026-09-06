# -*- coding: utf-8 -*-
"""P13 — LA TRANSCRIPTION VISE LA PISTE DE DIALOGUE, DECALE AU BON ENDROIT,
ET DIT CE QU'ELLE VA DEPENSER (route POST /api/subtitles/transcribe).

Run : & $PY tests/test_subs_transcribe_cible.py   (depuis backend/)

CE QUE LE JOURNAL DU 06/09/2026 A MONTRE (fait n°1 du lot 5) :
`transcribe: s1_drift-746849.mp3 (11.8s) via elevenlabs` — la route
transcrivait le VIEUX MP3 de A1 (premier clip `a1` porteur d'une source, dans
l'ordre du tableau), jamais le plan `kapwing_sample` de l'utilisateur ; et
`_subs_cues_to_segments(cues)` posait les mots AU TEMPS DU FICHIER, sans le
`start` ni le `srcIn` du clip. Ca « marchait avant » parce que le vestige A1
etait a t = 0. AUCUN banc ne frappait cette route (mesure : 0 occurrence de
`subtitles/transcribe` dans backend/tests avant ce fichier).

CE QUE CE BANC FERME :
  [1] un clip A1 a `start=28.876` produit des repliques a 28.876 et plus,
      coupees a `end` ; `srcIn` retranche (`start − srcIn`) ;
  [2] deux clips A1 → DEUX appels, dans l'ordre des `start` (pas du tableau),
      deux decalages, `usd` cumule, `sources` nomme les deux fichiers ;
      deux clips ADJACENTS (trou 0,1 s) → la marque `clip` SEULE coupe la
      replique a la frontiere ; UN MEME FICHIER sur deux clips (la lame) →
      UN appel, `usd` simple, `sources` le nomme une fois — `transcribe`
      envoie et facture le fichier ENTIER a chaque appel (mesure) ;
  [3] `src` explicite (le geste PAR PLAN) → UN appel, decale par le clip
      porteur — dialogue avant v1, sans porteur decalage 0 (dit) ;
  [4] sans clip de dialogue → la premiere V1 (au plus tot) ; sans rien → 400
      « Aucun média » ; `provider:"xx"` → 400 (la ValueError sortait en 500) ;
  [5] la langue : « auto », vide ou absente → `language=None` chez le moteur
      (sa detection) ; un code → transmis ; le calage gratuit recoit « fr » ;
  [6] la LOI DES PISTES est celle du rendu (`_tracks_meta`) : une piste de bus
      dialogue sous un autre identifiant est visee, une a1 re-busee ne l'est
      plus, une piste bouclee jamais ;
  [7] l'ETAT VIDE : un moteur qui rend `[]` fait finir le job `failed` avec
      « aucun mot horodaté » — le banc rougit sans mourir ;
  [8] AUCUN APPEL RESEAU : `transcribe_service.transcribe` est BOUCHONNE par
      attribut de module (il compte ses appels et rend des mots a 0..3 s),
      `_key` rend une fausse cle (donc `resolve_provider` et
      `available_providers` REELS voient une cle, et la ValueError du
      fournisseur inconnu reste REELLE — c'est elle que [4] mesure),
      `httpx.post`/`httpx.get` sont coupes et comptes.

LES SOURCES SONT DES FICHIERS REELS MINUSCULES ecrits dans le dossier
temporaire (`DEEPOTUS_DATA_DIR`), pas un `_subs_resolve` bouchonne : la
resolution `{audio}` (dossier audio) et `{name}` (outputs/uploads) est
exercee telle que le tiroir l'emploie, et un fichier qui n'existe pas rend
bien « Aucun média ». `transcribe` etant bouchonne, aucun ffprobe ne les
lit — un octet suffit.

LES TACHES DE FOND : le travail tourne en `BackgroundTasks`. MESURE dans ce
banc (ligne `bg_le_job_est_fini_a_la_sortie_de_la_requete`) : avec
`TestClient`, la tache s'execute AVANT que `post()` ne rende la main — le
premier GET /jobs/{id} est deja `done`, zero attente. Le banc compte les
relances qu'il a du faire et exige zero : si un jour la tache devient
vraiment asynchrone, cette ligne rougit et dit combien.

LA REGLE DES ASSERTIONS NEGATIVES (en-tete de test_montage_media.py) : toute
negation est conjointe a un positif — « 0 appel » va avec « statut 400 et
detail attendu », « aucun reseau » avec « N appels au bouchon », « pas de
decalage » avec « le premier mot est a 0 ET le job est done ».

MUTATIONS JOUEES SUR LA ROUTE (06/09/2026, chacune rejouee puis retiree) —
voir le rapport du commit : retirer le decalage, retirer le tri, ne prendre
que la premiere source, retirer l'enveloppe ValueError, retirer la marque
`clip` (R10 : le banc ROUGIT — deux lignes — et ne meurt plus : la revue
avait mesure un KeyError a la ligne des aides, faute n°6), retirer le cache
par fichier (R12 : la lame paie deux fois, trois lignes rougissent seules).
"""
import json
import os
import pathlib
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
TMP = tempfile.mkdtemp(prefix="dzp13_")
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
from app.api import routes as R                             # noqa: E402
from app.services import transcribe_service as T            # noqa: E402

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
# Sans cette ligne, un banc qui croit ecrire dans TMP ecrit dans les donnees
# reelles de l'utilisateur (mesure sur un autre banc, 28/08).
check("prevol_le_dossier_de_donnees_est_le_temporaire",
      str(settings.images_path).startswith(TMP)
      and str(settings.outputs_path).startswith(TMP),
      f"images={settings.images_path} outputs={settings.outputs_path}")

# ── LES BOUCHONS ───────────────────────────────────────────────────────────
APPELS = []          # (nom du fichier, provider, language) — un par transcribe
N_APPELS = [0]       # le TOTAL, jamais vide par un `del APPELS[:]`
RESEAU = []          # tout httpx.post/get — doit rester VIDE
ALIGN = []           # (lang) — un par align_narration_clips


def _mots(n=3):
    """N mots a 0..n s, 0,9 s chacun — la forme interne de `_norm_words`."""
    txt = "un deux trois quatre cinq six".split()
    return [{"i": i, "w": txt[i], "raw": txt[i], "punct": "",
             "start": float(i), "end": float(i) + 0.9,
             "speech_end": float(i) + 0.9, "weight": 0.0}
            for i in range(n)]


BOUCHON = {"words": _mots(3), "usd": 0.0013, "source": "elevenlabs",
           "leve": None}


def faux_transcribe(audio_path, *, provider=None, language=None,
                    timeout=600.0):
    APPELS.append((pathlib.Path(audio_path).name, provider, language))
    N_APPELS[0] += 1
    if BOUCHON["leve"] is not None:
        raise BOUCHON["leve"]
    ws = [dict(w) for w in BOUCHON["words"]]
    return {"ok": True, "source": BOUCHON["source"], "lang": language or "",
            "start": ws[0]["start"] if ws else 0.0,
            "end": ws[-1]["end"] if ws else 0.0,
            "words": ws, "cues": [], "text": " ".join(w["raw"] for w in ws),
            "audio": pathlib.Path(audio_path).name,
            "audio_duration_s": 3.0, "usd_estimated": BOUCHON["usd"],
            "silences": [], "spans": []}


def faux_align(clips, resolve_audio, lang="fr"):
    ALIGN.append(lang)
    return {"words": _mots(2), "blocks": len(clips)}


def _interdit(*a, **k):
    RESEAU.append(str(a[0] if a else k.get("url")))
    raise AssertionError("appel réseau interdit dans ce banc")


T_TRANSCRIBE_REEL = T.transcribe
T.transcribe = faux_transcribe
T.align_narration_clips = faux_align
T._key = lambda pid: "cle-de-banc"          # une cle SIMULEE, fonctions reelles
httpx.post = _interdit
httpx.get = _interdit

check("bouchon_transcribe_en_place_et_distinct_du_reel",
      T.transcribe is faux_transcribe and T_TRANSCRIBE_REEL is not faux_transcribe
      and callable(T_TRANSCRIBE_REEL))
# La cle simulee est vue par les fonctions REELLES — c'est ce qui rend la
# ValueError de [4] reelle et non bouchonnee.
try:
    _prov = T.resolve_provider(None)
    _dispo = [p["id"] for p in T.available_providers() if p["available"]]
except Exception as e:                                          # noqa: BLE001
    _prov, _dispo = temoin(e), []
check("bouchon_la_cle_simulee_rend_un_fournisseur_reel",
      _prov == "elevenlabs" and _dispo == ["elevenlabs", "openai"],
      f"resolve={_prov!r} disponibles={_dispo}")

# ── LES SOURCES : des fichiers REELS d'un octet ────────────────────────────
AUDIO = pathlib.Path(TMP) / "audio"
UPL = pathlib.Path(TMP) / "outputs" / "uploads"
AUDIO.mkdir(parents=True, exist_ok=True)
UPL.mkdir(parents=True, exist_ok=True)
for _n in ("voix_a.mp3", "voix_b.mp3"):
    (AUDIO / _n).write_bytes(b"x")
(UPL / "plan.mp4").write_bytes(b"x")
(UPL / "plan2.mp4").write_bytes(b"x")

SRC_A = {"audio": "voix_a.mp3"}          # dossier audio ({audio})
SRC_B = {"audio": "voix_b.mp3"}
SRC_V = {"name": "plan.mp4"}             # outputs/uploads ({name}, resolve_media)
SRC_V2 = {"name": "plan2.mp4"}
SRC_ABSENT = {"audio": "jamais.mp3"}


def A1(src, start, end, src_in=None, tr="a1", cid=None):
    c = {"id": cid or f"{tr}_{start}", "tr": tr, "src": src,
         "name": pathlib.Path(str(src.get("audio") or src.get("name"))).name,
         "start": start, "end": end}
    if src_in is not None:
        c["srcIn"] = src_in
    return c


# ── LE CLIENT, ET LA MESURE DES TACHES DE FOND ─────────────────────────────
client = TestClient(app)
RELANCES = []        # combien de GET il a fallu avant `done`/`failed`


class _Rep:
    def __init__(self, r):
        self.status = r.status_code
        try:
            self.body = r.json()
        except ValueError as e:
            self.body = {"_temoin": temoin(e), "_texte": r.text[:200]}

    def __repr__(self):
        return f"<{self.status} {json.dumps(self.body, ensure_ascii=False)[:300]}>"


def post(body):
    try:
        return _Rep(client.post("/api/subtitles/transcribe", json=body))
    except Exception as e:                                      # noqa: BLE001
        t = temoin(e)
        print(f"  ----  POST /transcribe a leve : {t}")
        return _Rep(type("R", (), {"status_code": -1, "text": t,
                                   "json": lambda self: {"_temoin": t}})())


def job(jid, attente=6):
    """GET /jobs/{jid}, relance au plus `attente` fois si le job court encore
    — et NOTE combien de relances il a fallu (mesure des taches de fond)."""
    n = 0
    while True:
        try:
            r = _Rep(client.get(f"/api/subtitles/jobs/{jid}"))
        except Exception as e:                                  # noqa: BLE001
            t = temoin(e)
            print(f"  ----  GET /jobs a leve : {t}")
            return {"status": t}
        st = r.body.get("status") if isinstance(r.body, dict) else None
        if st in ("done", "failed") or n >= attente:
            RELANCES.append(n)
            return r.body if isinstance(r.body, dict) else {"status": r.body}
        n += 1


def lance(body):
    """POST puis GET : rend (reponse du POST, corps du job ou {})."""
    r = post(body)
    jid = r.body.get("job_id") if isinstance(r.body, dict) else None
    return r, (job(jid) if jid else {})


def segs(j):
    return [(float(s["start"]), float(s["end"])) for s in (j.get("segments") or [])]


K_START, K_END = 28.876, 44.849          # kapwing_sample.mp4 sur V1 (15,973 s)

print("\n[1] UN CLIP A1 A 28,876 s : les répliques y sont, coupées au clip")
del APPELS[:]
r, j = lance({"clips": [A1(SRC_A, K_START, K_END, 0)], "lang": "fr"})
sg = segs(j)
check("a1_la_route_accepte_et_nomme_la_source",
      r.status == 200 and r.body.get("source") == "stt"
      and r.body.get("sources") == ["voix_a.mp3"]
      and "voix_a.mp3" in str(r.body.get("message")), repr(r))
check("a1_un_seul_appel_au_moteur_sur_le_bon_fichier_en_francais",
      APPELS == [("voix_a.mp3", None, "fr")], repr(APPELS))
check("a1_le_job_finit_done_et_porte_le_cout_le_fournisseur_les_sources",
      j.get("status") == "done" and j.get("provider") == "elevenlabs"
      and j.get("usd") == 0.0013 and j.get("sources") == ["voix_a.mp3"]
      and j.get("step") == "terminé",
      f'status={j.get("status")!r} usd={j.get("usd")!r} '
      f'provider={j.get("provider")!r} sources={j.get("sources")!r} '
      f'err={j.get("error")!r}')
# LE DECALAGE : le premier mot du fichier (0,0 s) tombe a 28,876 ; TOUT est
# au-dela du debut du clip et en deca de sa fin. Le conjoint positif :
# le job est done ET il y a des repliques.
check("a1_le_premier_mot_est_pose_au_start_du_clip",
      bool(sg) and sg[0][0] == K_START, f"segments={sg}")
check("a1_toutes_les_repliques_tiennent_dans_le_clip",
      bool(sg) and all(K_START <= a < b <= K_END for a, b in sg)
      and j.get("words") == 3, f"segments={sg} words={j.get('words')}")
check("bg_le_job_est_fini_a_la_sortie_de_la_requete",
      RELANCES == [0], f"relances={RELANCES}")

print("\n[1-bis] `srcIn` retranche, et la fin du clip coupe")
del APPELS[:]
# clip [5, 7] lu depuis 1,0 s : mot 0 (0→0,9) tombe a 4→4,9 : HORS clip,
# jete ; mot 1 → 5→5,9 ; mot 2 → 6→6,9.
r, j = lance({"clips": [A1(SRC_A, 5.0, 7.0, 1.0)]})
sg = segs(j)
check("srcin_le_mot_d_avant_le_clip_est_jete_les_deux_autres_decales",
      j.get("status") == "done" and j.get("words") == 2
      and bool(sg) and sg[0][0] == 5.0 and all(5.0 <= a < b <= 7.0 for a, b in sg),
      f"words={j.get('words')} segments={sg} err={j.get('error')!r}")
# clip court [28,876 ; 30] : le mot 1 (29,876→30,776) est ROGNE a 30,0, le
# mot 2 (30,876→) est jete.
r, j = lance({"clips": [A1(SRC_A, K_START, 30.0, 0)]})
sg = segs(j)
check("fin_le_mot_qui_deborde_est_rogne_le_suivant_jete",
      j.get("status") == "done" and j.get("words") == 2
      and bool(sg) and max(b for _a, b in sg) == 30.0
      and min(a for a, _b in sg) == K_START,
      f"words={j.get('words')} segments={sg} err={j.get('error')!r}")
check("srcin_deux_appels_pour_ces_deux_lancements", len(APPELS) == 2, repr(APPELS))

print("\n[2] DEUX CLIPS A1 : deux appels, l'ordre des start, deux décalages, usd cumulé")
del APPELS[:]
# B (10 s) est liste APRES A (28,876) dans le tableau : le tri par start
# doit le faire passer en premier.
r, j = lance({"clips": [A1(SRC_A, K_START, K_END, 0), A1(SRC_B, 10.0, 13.0, 0)]})
sg = segs(j)
check("deux_appels_dans_l_ordre_des_start_pas_du_tableau",
      APPELS == [("voix_b.mp3", None, None), ("voix_a.mp3", None, None)],
      repr(APPELS))
check("deux_sources_nommees_dans_l_ordre_et_usd_cumule",
      r.status == 200 and j.get("status") == "done"
      and j.get("sources") == ["voix_b.mp3", "voix_a.mp3"]
      and j.get("usd") == 0.0026 and j.get("words") == 6,
      f'sources={j.get("sources")!r} usd={j.get("usd")!r} words={j.get("words")!r}')
_b = [s for s in sg if s[0] < 20]
_a = [s for s in sg if s[0] >= 20]
check("deux_decalages_chacun_au_start_de_son_clip",
      bool(_b) and bool(_a) and _b[0][0] == 10.0 and _a[0][0] == K_START
      and all(10.0 <= a < b <= 13.0 for a, b in _b)
      and all(K_START <= a < b <= K_END for a, b in _a),
      f"B={_b} A={_a}")
# Deux sources ne fusionnent JAMAIS dans une meme replique (marque `clip`).
# CONJOINT POSITIF SEULEMENT : ces deux clips sont a 15,9 s l'un de l'autre,
# `group_words` les coupe deja par `max_gap_s` 0,7 (revue du 06/09) — la
# ligne qui mesure la marque est celle des clips ADJACENTS, en [2-bis].
check("deux_sources_aucune_replique_ne_les_enjambe",
      bool(sg) and not any(a < 13.0 < b for a, b in sg) and len(sg) >= 2,
      f"segments={sg}")
# LE `step` NOMME CHAQUE FICHIER AVEC SON RANG. La derniere valeur visible
# est « terminé » : le step intermediaire se mesure PENDANT la course, par
# un bouchon qui lit le journal des jobs au moment de l'appel.
STEPS_VUS = []


def _lit_le_step(audio_path, **kw):
    APPELS.append((pathlib.Path(audio_path).name, kw.get("provider"),
                   kw.get("language")))
    N_APPELS[0] += 1
    _j = [v for v in R._SUBS_JOBS.values() if v.get("status") == "running"]
    STEPS_VUS.append(_j[-1].get("step") if _j else None)
    return {"ok": True, "source": "elevenlabs", "words": _mots(3),
            "text": "un deux trois", "usd_estimated": 0.001}


T.transcribe = _lit_le_step
r, j = lance({"clips": [A1(SRC_A, K_START, K_END, 0), A1(SRC_B, 10.0, 13.0, 0)]})
T.transcribe = faux_transcribe
check("step_pendant_la_course_nomme_chaque_fichier_avec_son_rang",
      STEPS_VUS == ["transcription de voix_b.mp3 (1/2)",
                    "transcription de voix_a.mp3 (2/2)"]
      and j.get("status") == "done",
      f"steps={STEPS_VUS} status={j.get('status')!r}")

print("\n[2-bis] DEUX CLIPS ADJACENTS : la marque `clip` SEULE sépare les répliques")
# La revue du 06/09 a mesure que les deux clips de [2] sont a 15,9 s l'un de
# l'autre : `group_words` les coupait deja par `max_gap_s` 0,7, et la ligne
# verdissait SANS la marque. Ici B [10 ; 12] puis A [12 ; 14] : mots a 10,
# 11 puis 12, 13 (0,9 s chacun, sans ponctuation, 15 caracteres, 3,9 s de
# bout en bout) — trou de 0,1 s, sous TOUS les seuils de `group_words`
# (42 caracteres, 6 s, 0,7 s) : sans la marque, UNE replique 10 → 13,9
# enjamberait les deux sources. Mutation R10 (marque retiree) : cette ligne
# et `aide_shift_decale_coupe_et_marque_le_clip` rougissent, seules.
del APPELS[:]
r, j = lance({"clips": [A1(SRC_A, 12.0, 14.0, 0), A1(SRC_B, 10.0, 12.0, 0)]})
sg = segs(j)
check("adjacents_la_marque_clip_seule_coupe_la_replique_a_la_frontiere",
      j.get("status") == "done" and j.get("words") == 4 and len(sg) == 2
      and sg[0] == (10.0, 11.9) and sg[1] == (12.0, 13.9)
      and APPELS == [("voix_b.mp3", None, None), ("voix_a.mp3", None, None)],
      f"segments={sg} words={j.get('words')} appels={APPELS}")

print("\n[2-ter] UN MÊME FICHIER SUR DEUX CLIPS (la lame) : un appel, usd simple")
# La lame (Alt+C) fabrique deux clips de meme `src`, `srcIn` avance.
# `transcribe` envoie et facture le fichier ENTIER a chaque appel
# (transcribe_service : `probe_duration(p)` → `estimate_transcription`) :
# sans cache, deux appels et `usd` double (revue du 06/09). Les mots :
# clip 1 [10 ; 11,5] srcIn 0 → mot 0 (10→10,9), mot 1 rogne (11→11,5) ;
# clip 2 [11,5 ; 13] srcIn 1,5 (decalage 10) → mot 0 hors clip, jete ;
# mot 1 rogne (11,5→11,9), mot 2 (12→12,9). QUATRE mots, frontiere a 11,5.
del APPELS[:]
r, j = lance({"clips": [A1(SRC_A, 10.0, 11.5, 0, cid="k_a"),
                        A1(SRC_A, 11.5, 13.0, 1.5, cid="k_b")]})
sg = segs(j)
check("lame_un_meme_fichier_sur_deux_clips_un_seul_appel_usd_simple",
      APPELS == [("voix_a.mp3", None, None)] and j.get("status") == "done"
      and j.get("usd") == 0.0013 and j.get("sources") == ["voix_a.mp3"]
      and r.body.get("sources") == ["voix_a.mp3"]
      and str(r.body.get("message")) == "Transcription lancée sur voix_a.mp3.",
      f"appels={APPELS} usd={j.get('usd')!r} sources={j.get('sources')!r} "
      f"msg={r.body.get('message')!r}")
check("lame_chaque_clip_decale_les_memes_mots_et_la_frontiere_coupe",
      j.get("status") == "done" and j.get("words") == 4 and len(sg) == 2
      and sg[0] == (10.0, 11.5) and sg[1] == (11.5, 12.9),
      f"words={j.get('words')} segments={sg}")
# le meme fichier deux fois ET un autre : DEUX appels, dans l'ordre du
# PREMIER clip de chaque fichier, et le `step` compte les FICHIERS.
del APPELS[:]
del STEPS_VUS[:]
T.transcribe = _lit_le_step
r, j = lance({"clips": [A1(SRC_B, 20.0, 23.0, 0),
                        A1(SRC_A, 10.0, 11.5, 0, cid="k_a"),
                        A1(SRC_A, 11.5, 13.0, 1.5, cid="k_b")]})
T.transcribe = faux_transcribe
check("lame_deux_fichiers_deux_appels_et_le_step_compte_les_fichiers",
      APPELS == [("voix_a.mp3", None, None), ("voix_b.mp3", None, None)]
      and STEPS_VUS == ["transcription de voix_a.mp3 (1/2)",
                        "transcription de voix_b.mp3 (2/2)"]
      and j.get("sources") == ["voix_a.mp3", "voix_b.mp3"]
      and j.get("words") == 7 and j.get("status") == "done",
      f"appels={APPELS} steps={STEPS_VUS} sources={j.get('sources')!r} "
      f"words={j.get('words')}")

print("\n[3] `src` EXPLICITE (le geste par plan) : un appel, décalé par le clip porteur")
del APPELS[:]
# le tiroir envoie les clips qui CHEVAUCHENT le plan : ici le plan V1 et son
# jumeau A1 (meme source ? non : le jumeau porte SA source audio ; ici la
# source explicite est celle de A1).
r, j = lance({"src": SRC_A,
              "clips": [{"id": "v1u1_0", "tr": "v1", "src": SRC_V,
                         "name": "plan.mp4", "start": K_START, "end": K_END},
                        A1(SRC_A, K_START, K_END, 0)]})
sg = segs(j)
check("explicite_un_seul_appel_sur_la_source_donnee",
      APPELS == [("voix_a.mp3", None, None)], repr(APPELS))
check("explicite_decale_par_le_clip_porteur",
      j.get("status") == "done" and bool(sg) and sg[0][0] == K_START
      and all(K_START <= a < b <= K_END for a, b in sg), f"segments={sg}")
# la meme source portee par un v1 ET un a1 a des instants differents : le
# porteur de DIALOGUE decale (a1 a 40 s), pas le v1 (a 2 s).
del APPELS[:]
r, j = lance({"src": SRC_V,
              "clips": [{"id": "v", "tr": "v1", "src": SRC_V, "start": 2.0, "end": 18.0},
                        A1(SRC_V, 40.0, 56.0, 0)]})
sg = segs(j)
check("explicite_le_porteur_de_dialogue_prime_sur_v1",
      j.get("status") == "done" and bool(sg) and sg[0][0] == 40.0
      and APPELS == [("plan.mp4", None, None)], f"segments={sg} appels={APPELS}")
# deux porteurs de meme piste : le plus TOT
r, j = lance({"src": SRC_V,
              "clips": [A1(SRC_V, 40.0, 56.0, 0), A1(SRC_V, 7.0, 23.0, 0)]})
sg = segs(j)
check("explicite_a_rang_egal_le_porteur_le_plus_tot",
      j.get("status") == "done" and bool(sg) and sg[0][0] == 7.0, f"segments={sg}")
# sans porteur dans le payload : decalage 0, comme avant P13 — DIT.
r, j = lance({"src": SRC_A, "clips": []})
sg = segs(j)
check("explicite_sans_porteur_decalage_zero_comme_avant",
      j.get("status") == "done" and bool(sg) and sg[0][0] == 0.0
      and j.get("words") == 3, f"segments={sg}")

print("\n[4] LES REPLIS : première V1, sans rien, fournisseur inconnu")
del APPELS[:]
# sans clip de dialogue : la premiere V1 au plus tot (la seconde est listee
# d'abord), decalee ; la musique (a2) n'est jamais une source.
r, j = lance({"clips": [{"id": "vB", "tr": "v1", "src": SRC_V2, "start": 20.0, "end": 36.0},
                        {"id": "vA", "tr": "v1", "src": SRC_V, "start": 2.0, "end": 18.0},
                        {"id": "m", "tr": "a2", "src": SRC_B, "start": 0.0, "end": 60.0}]})
sg = segs(j)
check("repli_sans_dialogue_la_premiere_v1_au_plus_tot_et_elle_seule",
      APPELS == [("plan.mp4", None, None)] and j.get("status") == "done"
      and bool(sg) and sg[0][0] == 2.0 and all(2.0 <= a < b <= 18.0 for a, b in sg),
      f"appels={APPELS} segments={sg}")
# un clip a1 dont la source n'existe pas est saute : la v1 prend le relais
del APPELS[:]
r, j = lance({"clips": [A1(SRC_ABSENT, 3.0, 9.0, 0),
                        {"id": "v", "tr": "v1", "src": SRC_V, "start": 2.0, "end": 18.0}]})
check("repli_une_source_de_dialogue_introuvable_est_sautee",
      APPELS == [("plan.mp4", None, None)] and j.get("status") == "done",
      f"appels={APPELS} status={j.get('status')!r}")
# sans rien : 400 parlant, et ZERO appel (conjoint : le detail attendu)
_n0 = len(APPELS)
r = post({"clips": []})
check("vide_sans_media_400_parlant_et_aucun_appel",
      r.status == 400 and "Aucun média" in str(r.body.get("detail"))
      and len(APPELS) == _n0, repr(r))
r = post({"clips": [A1(SRC_ABSENT, 0.0, 5.0, 0)]})
check("vide_une_seule_source_introuvable_400_et_aucun_appel",
      r.status == 400 and "Aucun média" in str(r.body.get("detail"))
      and len(APPELS) == _n0, repr(r))
# corps absent de clips : la sauvegarde du dossier TEMPORAIRE (aucune) → 400
r = post({})
check("vide_sans_clips_ni_sauvegarde_400",
      r.status == 400 and "Aucun média" in str(r.body.get("detail")), repr(r))
# fournisseur inconnu : 400 (mesure avant P13 : 500, ValueError nue), et la
# phrase de resolve_provider — REELLE — arrive dans le detail.
r = post({"clips": [A1(SRC_A, 0.0, 5.0, 0)], "provider": "xx"})
check("provider_inconnu_400_avec_la_phrase_du_service_et_aucun_appel",
      r.status == 400 and "inconnu" in str(r.body.get("detail"))
      and "xx" in str(r.body.get("detail")) and len(APPELS) == _n0, repr(r))
# fournisseur connu mais sans cle : 400 « Aucune clé » — `_key` rend "" pour
# lui seul, les fonctions restent reelles.
_key_ok = T._key
T._key = lambda pid: "" if pid == "openai" else "cle-de-banc"
r = post({"clips": [A1(SRC_A, 0.0, 5.0, 0)], "provider": "openai"})
T._key = _key_ok
check("provider_sans_cle_400_aucune_cle_et_aucun_appel",
      r.status == 400 and "Aucune clé" in str(r.body.get("detail"))
      and len(APPELS) == _n0, repr(r))
# fournisseur explicite et disponible : transmis au moteur
del APPELS[:]
r, j = lance({"clips": [A1(SRC_A, 0.0, 5.0, 0)], "provider": "openai"})
check("provider_explicite_transmis_au_moteur",
      APPELS == [("voix_a.mp3", "openai", None)] and j.get("status") == "done",
      f"appels={APPELS}")

print("\n[5] LA LANGUE : « auto », vide, absente → None ; un code → transmis ; calage → fr")
del APPELS[:]
for _lang, _attendu in (("auto", None), ("", None), (None, None), ("en", "en"),
                        ("FR", "fr"), ("Auto", None)):
    body = {"clips": [A1(SRC_A, 0.0, 5.0, 0)]}
    if _lang is not None:
        body["lang"] = _lang
    r, j = lance(body)
    _vu = APPELS[-1][2] if APPELS else "AUCUN-APPEL"
    check(f"lang_{_lang!r}_transmise_comme_{_attendu!r}",
          j.get("status") == "done" and _vu == _attendu,
          f"vu={_vu!r} status={j.get('status')!r}")
check("lang_six_lancements_six_appels", len(APPELS) == 6, repr(APPELS))
# le calage gratuit (texte sur a1) recoit « fr » sous auto, et le code sinon
del ALIGN[:]
_n0 = len(APPELS)
for _lang, _attendu in (("auto", "fr"), ("", "fr"), ("de", "de")):
    r, j = lance({"lang": _lang,
                  "clips": [{"id": "n", "tr": "a1", "src": SRC_A, "text": "Bonjour à tous.",
                             "start": 0.0, "end": 5.0}]})
    check(f"lang_calage_{_lang!r}_recoit_{_attendu!r}",
          r.status == 200 and r.body.get("source") == "align"
          and j.get("status") == "done" and ALIGN[-1:] == [_attendu],
          f"align={ALIGN[-1:]} status={j.get('status')!r} src={r.body.get('source')!r}")
check("lang_le_calage_n_appelle_jamais_le_moteur_payant",
      len(APPELS) == _n0 and len(ALIGN) == 3, f"appels={len(APPELS) - _n0} align={ALIGN}")

print("\n[6] LA LOI DES PISTES est celle du rendu (_tracks_meta)")
del APPELS[:]
TR_A4 = [{"id": "v1", "kind": "video"},
         {"id": "a4", "kind": "audio", "bus": "dialogue"},
         {"id": "a1", "kind": "audio", "bus": "sfx"}]
r, j = lance({"tracks": TR_A4,
              "clips": [A1(SRC_A, K_START, K_END, 0),
                        A1(SRC_B, 10.0, 13.0, 0, tr="a4")]})
sg = segs(j)
check("pistes_le_bus_dialogue_sous_un_autre_identifiant_est_vise",
      APPELS == [("voix_b.mp3", None, None)] and j.get("status") == "done"
      and bool(sg) and sg[0][0] == 10.0, f"appels={APPELS} segments={sg}")
# a1 re-busee en sfx et aucune piste de dialogue : v1 prend le relais
del APPELS[:]
r, j = lance({"tracks": [{"id": "v1", "kind": "video"}, {"id": "a1", "kind": "audio", "bus": "sfx"}],
              "clips": [A1(SRC_A, K_START, K_END, 0),
                        {"id": "v", "tr": "v1", "src": SRC_V, "start": 2.0, "end": 18.0}]})
check("pistes_une_a1_sortie_du_bus_dialogue_n_est_plus_visee",
      APPELS == [("plan.mp4", None, None)] and j.get("status") == "done",
      f"appels={APPELS}")
# une piste de dialogue BOUCLEE n'est jamais une source
del APPELS[:]
r, j = lance({"tracks": [{"id": "v1", "kind": "video"},
                         {"id": "a1", "kind": "audio", "bus": "dialogue", "loop": True}],
              "clips": [A1(SRC_A, K_START, K_END, 0),
                        {"id": "v", "tr": "v1", "src": SRC_V, "start": 2.0, "end": 18.0}]})
check("pistes_une_piste_bouclee_n_est_jamais_une_source",
      APPELS == [("plan.mp4", None, None)] and j.get("status") == "done",
      f"appels={APPELS}")
# `tracks` illisible ⇒ la table historique (a1)
del APPELS[:]
r, j = lance({"tracks": ["v1", 3, None], "clips": [A1(SRC_A, K_START, K_END, 0)]})
check("pistes_une_liste_illisible_vaut_la_table_historique",
      APPELS == [("voix_a.mp3", None, None)] and j.get("status") == "done",
      f"appels={APPELS}")

print("\n[7] L'ETAT VIDE : le moteur rend [] → failed « aucun mot horodaté »")
del APPELS[:]
BOUCHON["words"] = []
r, j = lance({"clips": [A1(SRC_A, K_START, K_END, 0)]})
BOUCHON["words"] = _mots(3)
check("vide_moteur_muet_le_job_finit_failed_et_le_dit",
      r.status == 200 and j.get("status") == "failed"
      and "aucun mot horodaté" in str(j.get("error")) and j.get("step") == "échec"
      and j.get("segments") is None and len(APPELS) == 1,
      f"status={j.get('status')!r} err={j.get('error')!r} segs={j.get('segments')!r}")
# des mots tous HORS du clip : clip [100, 101] lu depuis 10 s (decalage
# 90) contre des mots a 0..3 s → 90..92,9, tous avant le clip : meme sortie
# — c'est la coupe qui les a jetes, et c'est dit. (Premiere redaction :
# srcIn 0, et le mot 0 tombait AU start — le job finissait done : mesure.)
r, j = lance({"clips": [A1(SRC_A, 100.0, 101.0, 10.0)]})
check("vide_des_mots_tous_hors_du_clip_le_job_finit_failed",
      j.get("status") == "failed" and "aucun mot horodaté" in str(j.get("error"))
      and "voix_a.mp3" in str(j.get("error")),
      f"status={j.get('status')!r} err={j.get('error')!r}")
# le moteur qui LEVE : failed, la phrase du moteur, pas un 500
BOUCHON["leve"] = RuntimeError("ElevenLabs: HTTP 401 — clé refusée")
r, j = lance({"clips": [A1(SRC_A, K_START, K_END, 0)]})
BOUCHON["leve"] = None
check("vide_le_moteur_qui_leve_fait_un_job_failed_pas_un_500",
      r.status == 200 and j.get("status") == "failed"
      and "HTTP 401" in str(j.get("error")),
      f"post={r.status} status={j.get('status')!r} err={j.get('error')!r}")

print("\n[8] LES AIDES PURES, directement")
_w = _mots(3)
_c = {"id": "k", "tr": "a1", "start": 10.0, "end": 12.5, "srcIn": 0.5}
_s = R._subs_shift_words(_w, _c)
# `x.get("clip")` dans la CONDITION aussi : sans la marque, la ligne ROUGIT
# avec un temoin lisible (`None`) — la premiere redaction ecrivait
# `x["clip"]` et le banc MOURAIT d'un KeyError (faute n°6, revue du 06/09).
check("aide_shift_decale_coupe_et_marque_le_clip",
      [(x["start"], x["end"], x.get("clip")) for x in _s]
      == [(10.0, 10.4, "k"), (10.5, 11.4, "k"), (11.5, 12.4, "k")],
      repr([(x["start"], x["end"], x.get("clip")) for x in _s]))
check("aide_shift_sans_clip_copie_telle_quelle",
      R._subs_shift_words(_w, None) == _w
      and R._subs_shift_words(_w, None)[0] is not _w[0]
      and R._subs_shift_words([], None) == [], repr(R._subs_shift_words(_w, None)))
check("aide_shift_un_mot_illisible_est_saute",
      [x["start"] for x in R._subs_shift_words([{"start": "x", "end": 1}, _w[0]],
                                                {"start": 1.0, "end": 9.0})] == [1.0],
      repr(R._subs_shift_words([{"start": "x", "end": 1}, _w[0]], {"start": 1.0, "end": 9.0})))
check("aide_bornes_garbage_rend_des_zeros_et_end_jamais_sous_start",
      R._subs_bornes({}) == (0.0, 0.0, 0.0)
      and R._subs_bornes({"start": "abc", "end": -3, "srcIn": None}) == (0.0, 0.0, 0.0)
      and R._subs_bornes({"start": 5, "end": 2, "srcIn": 1}) == (5.0, 5.0, 1.0)
      and R._subs_bornes({"start": float("nan"), "end": 4}) == (0.0, 4.0, 0.0),
      repr((R._subs_bornes({}), R._subs_bornes({"start": 5, "end": 2, "srcIn": 1}))))
_circ = {}
_circ["me"] = _circ                     # json.dumps leve ValueError → repr
check("aide_cle_de_source_ignore_l_ordre_des_cles",
      R._subs_src_key({"b": 1, "a": 2}) == R._subs_src_key({"a": 2, "b": 1})
      and R._subs_src_key({"a": 1}) != R._subs_src_key({"a": 2})
      and R._subs_src_key(_circ).startswith("{'me'"),
      repr((R._subs_src_key({"b": 1, "a": 2}), R._subs_src_key(_circ))))
_dial = R._subs_dialogue_ids(None)
check("aide_pistes_sans_payload_la_table_historique_a1",
      _dial == {"a1"} and R._subs_dialogue_ids([]) == {"a1"}
      and R._subs_dialogue_ids(TR_A4) == {"a4"}
      and R._subs_dialogue_ids([{"id": "a1", "kind": "audio", "bus": "dialogue", "loop": True}]) == set(),
      f"{_dial} {R._subs_dialogue_ids(TR_A4)}")
_cs = [{"id": "x", "tr": "v1", "src": {"job_id": "j"}, "start": 30},
       {"id": "y", "tr": "a1", "src": {"job_id": "j"}, "start": 50},
       {"id": "z", "tr": "a1", "src": {"job_id": "j"}, "start": 20},
       {"id": "w", "tr": "a3", "src": {"job_id": "j"}, "start": 0}]
check("aide_porteur_dialogue_puis_v1_puis_le_reste_au_plus_tot",
      (R._subs_carrier(_cs, {"job_id": "j"}, {"a1"}) or {}).get("id") == "z"
      and (R._subs_carrier(_cs[:1] + _cs[3:], {"job_id": "j"}, {"a1"}) or {}).get("id") == "x"
      and (R._subs_carrier(_cs[3:], {"job_id": "j"}, {"a1"}) or {}).get("id") == "w"
      and R._subs_carrier(_cs, {"job_id": "autre"}, {"a1"}) is None
      and R._subs_carrier([], {"job_id": "j"}, {"a1"}) is None,
      repr([(R._subs_carrier(_cs, {"job_id": "j"}, {"a1"}) or {}).get("id")]))

print("\n[9] AUCUN RESEAU N'EST PARTI, et le banc a bien joue ses appels")
check("reseau_zero_appel_httpx_et_des_appels_au_bouchon",
      RESEAU == [] and N_APPELS[0] >= 25 and T.transcribe is faux_transcribe,
      f"reseau={RESEAU} appels={N_APPELS[0]}")
check("bg_aucune_relance_n_a_ete_necessaire_sur_tout_le_banc",
      bool(RELANCES) and set(RELANCES) == {0}, f"relances={RELANCES}")
check("aucun_appel_n_a_plante", _plantages == 0,
      f"{_plantages} appel(s) ont leve — voir les lignes « ---- » ci-dessus")

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
