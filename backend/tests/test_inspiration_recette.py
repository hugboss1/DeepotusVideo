# -*- coding: utf-8 -*-
"""t512 (RV2, 26/11/2026) — banc de la lecture sur devis d'une vidéo de référence et de sa RECETTE.

Sections :
  1. pures : mots_par_minute ; normaliser_recette (bornes, rôles inconnus -> autre, nombres pris aux MESURES, briques
     triées) ; garder_recette (un texte qui reprend 12 mots de la source est vidé et signalé) ; empreinte_texte et
     suite_dans_empreinte ;
  2. routes (vraie vidéo ffmpeg avec son ; transcription et Claude remplacés, aucun réseau) : devis-lecture gratuit
     (transcription + texte) ; lecture sans accord -> 400 ; accord trop bas -> 409 cout ; lecture 200 : recette, garde
     contre la copie, rangée dans l'espace, `inspire_de` ; plafond « campagnes » appelé avant la transcription ;
     seconde lecture gardée (deja_payee) ; capture (non vidéo) -> 400 matiere ; sans clé de transcription -> 503 ;
  3. purge R4 : la transcription quitte texte_capte, son empreinte reste et reconnaît une suite copiée.
Run (depuis backend/) : & $PY tests/test_inspiration_recette.py"""
import json, os, pathlib, shutil, subprocess, sys, tempfile
from datetime import datetime, timedelta, timezone
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzinsrc_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
for d in ("images", "outputs"):
    (_tmp / d).mkdir(exist_ok=True)
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "ELEVENLABS_API_KEY"):
    os.environ[k] = ""
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))
from loguru import logger                                           # noqa: E402
logger.remove()

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


from app.config import settings                                     # noqa: E402
from app.services import inspiration_recette as IR                  # noqa: E402
from app.services import inspiration_video as IV                    # noqa: E402
from app.services import inspiration as I                           # noqa: E402
from app.services import moteurs_texte as MT                        # noqa: E402
from app.services import transcribe_service as TS                   # noqa: E402
from app.services import plafonds as PLAF                           # noqa: E402

settings.ANTHROPIC_API_KEY = "cle-de-banc"
settings.ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

PAROLE = ("Tu paies chaque mois pour un outil que tu ouvres deux fois par semaine et personne ne te le dit jamais "
          "en face alors regarde bien ce chiffre")
COPIEE = "un outil que tu ouvres deux fois par semaine et personne ne te le dit jamais"
MOTS = [{"i": i, "w": w, "raw": w, "start": round(i * 0.25, 2), "end": round(i * 0.25 + 0.2, 2)}
        for i, w in enumerate(PAROLE.split())]
REPONSE = {"texte_ecran": "99 $ PAR MOIS", "structure": [
    {"role": "promesse", "debut": 2.0, "fin": 4.0, "regle": "une promesse chiffrée", "visuel": "barres"},
    {"role": "accroche", "debut": -1, "fin": 2.0, "regle": "une question qui vise le portefeuille", "visuel": "texte"},
    {"role": "inconnu", "debut": 4.0, "fin": 99, "regle": COPIEE, "visuel": "hologramme"},
    {"role": "appel", "debut": 5, "fin": 5, "regle": "vide", "visuel": "texte"}],
    "soustitres": {"lignes": 2, "mots_par_ligne": 4, "apparition": "mot à mot", "mot_en_pastille": True, "badge": "oui",
                   "position": "bas"},
    "image": {"fond": "noir uni", "couleurs": 3, "fil_de_progression": True, "transition_de_marque": "logo en volet"},
    "appel": {"type": "commentaire", "montre_a_l_ecran": True},
    "a_ne_pas_reprendre": ["le nom de la marque", "la palette exacte"], "duree_s": 999}
APPELS = []
TRANS = []
PLAF_APPELS = []


class _Rep:
    status_code = 200
    text = ""

    def __init__(self, t): self._t = t

    def json(self): return {"content": [{"type": "text", "text": self._t}], "usage": {"input_tokens": 1, "output_tokens": 1}}


def faux_post(url, headers=None, json=None, timeout=None, verify=None):
    APPELS.append(json)
    import json as _j
    return _Rep(_j.dumps(REPONSE, ensure_ascii=False))


MT.httpx.post = faux_post
CLE_STT = {"ok": True}


def faux_estimer(d, provider=None):
    if not CLE_STT["ok"]:
        return {"ok": False, "usd": 0.0, "reason": "Aucune clé de transcription configurée (Réglages : ElevenLabs ou OpenAI)."}
    return {"ok": True, "provider": "elevenlabs", "usd": round(d / 60 * 0.4, 4), "eta_s": 5}


def faux_transcrire(audio, provider=None, language=None, timeout=600.0):
    TRANS.append((pathlib.Path(audio).name, provider, language, pathlib.Path(audio).stat().st_size > 0))
    return {"ok": True, "words": MOTS, "text": PAROLE}


TS.estimate_transcription = faux_estimer
TS.transcribe = faux_transcrire
_vrai_verifier = PLAF.verifier


async def espion_verifier(op, categorie="", ref=None, confirme=None, espace_id=None):
    PLAF_APPELS.append((op.get("kind"), categorie, len(TRANS)))
    return await _vrai_verifier(op, categorie, ref=ref, confirme=confirme, espace_id=espace_id)


PLAF.verifier = espion_verifier


def section_pures():
    print("[1] pures")
    check("1a mots par minute : 24 mots en 6 s = 240", IR.mots_par_minute(MOTS, 6.0) == 240.0, IR.mots_par_minute(MOTS, 6.0))
    check("1b sans mots -> None", IR.mots_par_minute([], 6.0) is None)
    rec = {"id": "x", "source": {"lien": "https://instagram.com/reel/abc", "libelle": "Reel vu", "le": "2026-11-26"},
           "video": {"fiche": {"format": {"duree_s": 6.0, "cadre": "9:16", "boucle": False, "son": True},
                               "rythme": {"plans": 3, "duree_moyenne_s": 2.0, "duree_min_s": 2.0, "duree_max_s": 2.0}}}}
    r = IR.normaliser_recette(REPONSE, rec, MOTS)
    check("1c briques bornées à la durée, triées, vides écartées", [b["debut"] for b in r["structure"]] == [0.0, 2.0, 4.0]
          and r["structure"][-1]["fin"] == 6.0 and len(r["structure"]) == 3, r["structure"])
    check("1d rôle et visuel inconnus -> autre", r["structure"][2]["role"] == "autre" and r["structure"][2]["visuel"] == "autre")
    check("1e nombres pris aux mesures (durée 6, 3 tableaux), jamais au modèle", r["format"]["duree_s"] == 6.0
          and r["rythme"]["tableaux"] == 3 and r["rythme"]["mots_par_minute"] == 240.0, r["rythme"])
    check("1f booléens lus (« oui » = vrai), position permise", r["soustitres"]["badge"] is True and r["soustitres"]["position"] == "bas")
    check("1g compteurs jamais vérifiés", r["source"]["compteurs_verifies"] is False)
    al = IR.garder_recette(r, PAROLE + "\n99 $ PAR MOIS")
    check("1h garde : la règle qui recopie 12 mots est vidée et signalée", r["structure"][2]["regle"] == ""
          and len(al) == 1, al)
    check("1i garde : les règles abstraites restent", r["structure"][0]["regle"] == "une question qui vise le portefeuille")
    check("1j garde sans source : rien n'est touché", IR.garder_recette(IR.normaliser_recette(REPONSE, rec, MOTS), "") == [])
    e = IR.empreinte_texte(PAROLE)
    check("1k empreinte : une fenêtre par position", len(e) == len(PAROLE.split()) - 11, len(e))
    check("1l l'empreinte ne contient aucun mot de la source", not any(w.lower() in " ".join(e) for w in ("outil", "chiffre")))
    check("1m suite copiée reconnue par l'empreinte, accents et casse neutres",
          IR.suite_dans_empreinte(e, "Écoute : UN OUTIL que tu ouvres deux fois par semaine et personne ne te le dit jamais !"))
    check("1n texte neuf non reconnu", not IR.suite_dans_empreinte(e, "Un logiciel payé une seule fois, à vie, sans abonnement caché"))


def fabriquer(dossier: pathlib.Path) -> pathlib.Path:
    out = dossier / "ref.mp4"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    for c in ("red", "blue", "green"):
        cmd += ["-f", "lavfi", "-i", f"color=c={c}:s=270x480:r=25:d=2"]
    cmd += ["-f", "lavfi", "-i", "sine=frequency=440:duration=6", "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]",
            "-map", "[v]", "-map", "3:a", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-t", "6", str(out)]
    subprocess.run(cmd, check=True, capture_output=True)
    return out


def section_routes():
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        print("  SAUTÉ sections 2 et 3 : ffmpeg ou ffprobe absent du PATH")
        return
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services import espaces
    with TestClient(app, client=("127.0.0.1", 50000)) as client, \
            TestClient(app, client=("192.168.1.20", 50000)) as dehors:
        EA = espaces.creer({"nom": "Studio Recette"})["id"]
        H = {"X-Dz-Espace": EA}
        r = client.post("/api/inspiration/video", headers=H, data={"source_libelle": "Reel vu", "source_lien": "https://x.example/r"},
                        files={"video": ("ref.mp4", fabriquer(_tmp).read_bytes(), "video/mp4")})
        IID = r.json()["id"]
        print("[2] devis et lecture")
        r = dehors.post(f"/api/inspiration/{IID}/lecture", json={"max_usd": 1})
        check("2a hors machine -> 401 ou 403", r.status_code in (401, 403), r.status_code)
        r = client.get(f"/api/inspiration/{IID}/devis-lecture", headers=H)
        d = r.json()
        check("2b devis gratuit : transcription + texte, disponible", r.status_code == 200 and d["disponible"]
              and d["transcription"]["usd"] == 0.04 and d["texte"]["usd"] > 0 and d["texte"]["planches"] >= 1
              and abs(d["usd"] - (d["transcription"]["usd"] + d["texte"]["usd"])) < 1e-6, d)
        check("2c aucun appel payant pour le devis", not APPELS and not TRANS and not PLAF_APPELS)
        r = client.post(f"/api/inspiration/{IID}/lecture", headers=H, json={})
        check("2d sans accord -> 400", r.status_code == 400, r.status_code)
        r = client.post(f"/api/inspiration/{IID}/lecture", headers=H, json={"max_usd": 0.0001})
        check("2e accord trop bas -> 409 cout avec le montant", r.status_code == 409 and r.json()["detail"]["code"] == "cout"
              and r.json()["detail"]["usd"] > 0.0001, r.text[:200])
        check("2f rien dépensé après un refus", not APPELS and not TRANS)
        r = client.post(f"/api/inspiration/{IID}/lecture", headers=H, json={"max_usd": d["usd"]})
        j = r.json() if r.status_code == 200 else {}
        rc = j.get("recette") or {}
        check("2g 200 : recette avec briques et sous-titres", r.status_code == 200 and len(rc.get("structure") or []) == 3
              and rc.get("soustitres", {}).get("mot_en_pastille") is True, r.text[:300])
        check("2h plafond « campagnes » vérifié AVANT la transcription", PLAF_APPELS and PLAF_APPELS[0] == ("transcribe", "campagnes", 0),
              PLAF_APPELS)
        check("2i transcription de l'audio extrait (mp3 non vide), dans la langue", TRANS and TRANS[0][0] == "voix.mp3"
              and TRANS[0][3] and TRANS[0][2] == "fr", TRANS)
        check("2j un seul appel Claude, avec les planches en images", len(APPELS) == 1
              and any(isinstance(c, dict) and c.get("type") == "image" for m in APPELS[0]["messages"]
                      for c in (m["content"] if isinstance(m["content"], list) else [])), str(APPELS[:1])[:200])
        check("2k la transcription part ENCADRÉE (<<<PREUVE)", "<<<PREUVE transcription" in json.dumps(APPELS[0], ensure_ascii=False))
        check("2l garde : la règle recopiée est vidée, alerte rendue", j.get("alertes") and
              all(COPIEE not in b["regle"] for b in rc["structure"]), j.get("alertes"))
        check("2m inspire_de rempli (R12 a), compteurs non vérifiés", rc.get("inspire_de", {}).get("lien") == "https://x.example/r")
        f = espaces.dossier() / EA / "recettes" / f"{IID}.json"
        check("2n recette rangée dans l'espace", f.is_file() and json.loads(f.read_text(encoding="utf-8"))["id"] == IID)
        check("2o dossier temporaire de lecture effacé", not (_tmp / "inspirations" / IID / "_lecture").exists())
        n = len(APPELS)
        r = client.post(f"/api/inspiration/{IID}/lecture", headers=H, json={"max_usd": d["usd"]})
        check("2p seconde lecture : gardée, sans repayer", r.status_code == 200 and r.json().get("deja_payee") and len(APPELS) == n)
        r = client.get(f"/api/inspiration/{IID}", headers=H)
        check("2q l'inspiration montre sa recette", r.json().get("recette", {}).get("structure"))
        r = client.post("/api/inspiration/capter", headers=H, data={"texte": "Un texte collé"})
        cid = r.json()["id"]
        r = client.get(f"/api/inspiration/{cid}/devis-lecture", headers=H)
        check("2r capture (non vidéo) -> 400 matiere", r.status_code == 400 and r.json()["detail"]["code"] == "matiere", r.text[:200])
        r2 = client.post("/api/inspiration/video", headers=H, files={"video": ("ref.mp4", (_tmp / "ref.mp4").read_bytes(), "video/mp4")})
        CLE_STT["ok"] = False
        r = client.post(f"/api/inspiration/{r2.json()['id']}/lecture", headers=H, json={"max_usd": 1})
        check("2s sans clé de transcription -> 503", r.status_code == 503, r.status_code)
        CLE_STT["ok"] = True
        print("[3] purge R4")
        IV.purger(datetime.now(timezone.utc) + timedelta(days=8))
        rec = I.lire(IID)
        check("3a la transcription quitte texte_capte", rec["texte_capte"] == "" and rec["empreinte_texte"])
        check("3b l'empreinte reconnaît encore une suite copiée", IR.suite_dans_empreinte(rec["empreinte_texte"], COPIEE))
        check("3c la recette reste", rec["recette"]["structure"])


def test_inspiration_recette():
    section_pures()
    section_routes()
    assert fail == 0, f"{fail} échec(s)"


if __name__ == "__main__":
    try:
        section_pures()
        section_routes()
    finally:
        shutil.rmtree(_tmp, ignore_errors=True)
    print(f"\n{ok} PASS, {fail} FAIL")
    sys.exit(1 if fail else 0)
