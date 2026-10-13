"""Traduction L10 (t150) : les messages d'erreur du backend traduits à la sortie.

  1. erreurs.json est à jour : scripts/i18n_l10_erreurs.py --check (toutes les HTTPException et raise *Error à texte
     fixe des sources ont leur entrée, aucune traduction manquante ni fautive) ;
  2. chaque entrée : fr et en non vides, mêmes variables, le côté `src` est bien le gabarit du code ;
  3. aller-retour : chaque gabarit source rempli de valeurs témoins est reconnu et rendu par l'autre gabarit ;
  4. le gestionnaire d'HTTPException : Accept-Language en / fr traduit, SANS en-tête rien ne change (les bancs) ;
  5. EXEMPTS : « Chapter not found » (testé par atelier.js) n'est jamais traduit.
  6. un seul mécanisme avec G10 (t192) : aucun gabarit L10 n'est le français d'une clé de messages.json (un message
     passé par Message/Refus/_msg_g n'est plus un littéral), et un refus G10 déjà rendu dans la langue de la requête
     traverse le gestionnaire sans être retraduit.
  7. l'étape des jobs (décision G10) : les `current_step` littéraux des sources sont au dictionnaire (sauf « Complete »,
     que le bundle compare), GET /jobs et GET /jobs/{id} rendent étape et erreur dans la langue de l'en-tête.
Run: <python embarqué> backend/tests/test_i18n_l10.py
"""
import asyncio
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
ICI = pathlib.Path(__file__).resolve().parent
RACINE = ICI.parent.parent
sys.path.insert(0, str(ICI.parent))

from app.i18n import erreurs as ERR                       # noqa: E402

OK, KO = [], []
VAR = re.compile(r"\{(\w+)\}")


def verifier(nom, cond, info=""):
    (OK if cond else KO).append(nom)
    print(("  PASS  " if cond else "  FAIL  ") + nom + ("" if cond else f"  — {info}"))


# 1. générateur à jour
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_l10_erreurs.py"), "--check"],
                   capture_output=True, text=True, encoding="utf-8")
verifier("1.1 erreurs.json à jour (--check)", r.returncode == 0, (r.stdout + r.stderr)[-600:])
D = ERR.dico()
verifier("1.2 plus de 1500 messages au dictionnaire", len(D) > 1500, len(D))

# 2. forme des entrées
mauvais = [k for k, e in D.items()
           if not e.get("fr") or not e.get("en") or e.get("src") not in ("fr", "en")
           or set(VAR.findall(e["fr"])) != set(VAR.findall(e["en"])) or not k.startswith("erreur.")]
verifier("2.1 fr, en, src et mêmes variables partout", not mauvais, mauvais[:5])
nfr = sum(1 for e in D.values() if e["src"] == "fr")
verifier("2.2 les deux langues sources présentes (le code est surtout en français)",
         nfr > len(D) / 2 and len(D) - nfr > 100, (nfr, len(D) - nfr))
traduits = sum(1 for e in D.values() if e["fr"] != e["en"])
verifier("2.3 au moins 95 % des messages réellement traduits (les autres sont techniques)",
         traduits >= 0.95 * len(D), (traduits, len(D)))

# 3. aller-retour sur tout le dictionnaire
ratés = []
for k, e in D.items():
    src, autre = e[e["src"]], e["en" if e["src"] == "fr" else "fr"]
    vals = {v: f"«T{i}»" for i, v in enumerate(dict.fromkeys(VAR.findall(src)))}
    rempli = VAR.sub(lambda m: vals[m.group(1)], src)
    attendu = VAR.sub(lambda m: vals[m.group(1)], autre)
    obtenu = ERR.texte(rempli, "en" if e["src"] == "fr" else "fr")
    # un même message peut exister sous deux gabarits (seul le nom de variable change) : l'autre traduction gagne,
    # tant qu'elle traduit bien et garde toutes les valeurs
    if obtenu != attendu and ((attendu != rempli and obtenu == rempli) or any(v not in obtenu for v in vals.values())):
        ratés.append((k, rempli, obtenu))
verifier("3.1 chaque gabarit rempli est rendu dans l'autre langue, valeurs gardées", not ratés, ratés[:3])
verifier("3.2 inconnu : passe tel quel", ERR.texte("Upstream exploded (code 7)", "en") == "Upstream exploded (code 7)")
verifier("3.3 sans langue connue : inchangé", ERR.texte(next(iter(D.values()))["fr"], "de") == next(iter(D.values()))["fr"])

# 5. exempts
src_atelier = (RACINE / "frontend" / "atelier" / "atelier.js").read_text("utf-8")
verifier("5.1 atelier.js teste toujours /Chapter not found/", "/Chapter not found/i.test(e.message)" in src_atelier)
verifier("5.2 « Chapter not found » n'est jamais traduit",
         ERR.texte("Chapter not found", "fr") == "Chapter not found"
         and not any(e["src"] == "en" and e["en"] == "Chapter not found" for e in D.values()))


# 6. un seul mécanisme avec G10 (t192)
_MSG = json.loads((ICI.parent / "app" / "i18n" / "messages.json").read_text("utf-8"))
_SRC = {e[e["src"]] for e in D.values()}
doubles = [k for k, e in _MSG.items() if e.get("fr") in _SRC or e.get("en") in _SRC]
verifier("6.1 aucun message à la fois clé de messages.json et gabarit L10", not doubles, doubles[:5])

# 7. l'étape des jobs
sys.path.insert(0, str(RACINE / "scripts"))
import i18n_l10_erreurs as GEN                            # noqa: E402
_SOURCES = GEN.extraire()
_ET = ["Rendu ffmpeg (aperçu 480p)", "Failed", "Échec", "Terminé", "Resolving {tasks} clip(s) in parallel"]
verifier("7.1 les étapes littérales des jobs sont relevées et traduites",
         all(g in _SOURCES for g in _ET) and ERR.texte("Rendu ffmpeg", "en") == "ffmpeg render"
         and ERR.texte("Resolving 3 clip(s) in parallel", "fr") == "Résolution de 3 clip(s) en parallèle",
         [g for g in _ET if g not in _SOURCES])
_BUN = next((RACINE / "frontend" / "dist" / "assets").glob("index-*.js")).read_text("utf-8")
verifier("7.2 « Complete » (comparé par le bundle) n'est jamais traduit",
         'current_step!=="Complete"' in _BUN and "Complete" not in _SOURCES and ERR.texte("Complete", "fr") == "Complete")

# 4. le gestionnaire, par la vraie application
async def _http():
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.services.storage import init_db
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        corps = {"op": "crop", "filename": "nope.png"}
        brut = (await c.post("/api/images/process", json=corps)).json()["detail"]
        fr = (await c.post("/api/images/process", json=corps, headers={"Accept-Language": "fr"})).json()["detail"]
        en = (await c.post("/api/images/process", json=corps, headers={"Accept-Language": "en-US,en;q=0.9"})).json()["detail"]
        verifier("4.1 sans en-tête : le message du code (anglais du socle)", brut == "Source image not found: nope.png", brut)
        verifier("4.2 Accept-Language fr : traduit en français, la variable gardée",
                 fr != brut and "nope.png" in fr and "introuvable" in fr.lower(), fr)
        verifier("4.3 Accept-Language en : anglais", en == brut, en)
        corps = {"op": "crop", "filename": "../x.png"}
        brut = (await c.post("/api/images/process", json=corps)).json()["detail"]
        en = (await c.post("/api/images/process", json=corps, headers={"Accept-Language": "en"})).json()["detail"]
        fr = (await c.post("/api/images/process", json=corps, headers={"Accept-Language": "fr"})).json()["detail"]
        verifier("4.4 message français sans en-tête : inchangé", brut.startswith("filename refusé"), brut)
        verifier("4.5 Accept-Language en : traduit, la valeur citée gardée",
                 en != brut and "'../x.png'" in en and "refus" not in en, en)
        verifier("4.6 Accept-Language fr : le français du code", fr == brut, fr)
        # 6.2 : un refus G10 (Refus « ia.sfx.modele_inconnu », rendu par _txt_g) traverse le gestionnaire intact
        from app import i18n as _I
        corps = {"modele": "inconnu-l10", "prompt": "x"}
        brut = (await c.post("/api/audio/sfx", json=corps)).json()["detail"]
        en = (await c.post("/api/audio/sfx", json=corps, headers={"Accept-Language": "en"})).json()["detail"]
        fr = (await c.post("/api/audio/sfx", json=corps, headers={"Accept-Language": "fr"})).json()["detail"]
        from app.services import sfx_service as _SX
        v = dict(id=repr("inconnu-l10"), connus=", ".join(_SX.ids_sfx(_SX.SFX_TEXTE)))
        verifier("6.2 refus G10 : en = la clé en anglais, fr = la clé en français, une seule traduction",
                 en == _I.msg("ia.sfx.modele_inconnu", "en", **v) and fr == _I.msg("ia.sfx.modele_inconnu", "fr", **v)
                 and en != fr and brut in (en, fr), (brut, en, fr))
        # 7.3 : un job en base, lu par la route avec et sans en-tête
        from app.services.storage import async_session_factory, JobRecord
        async with async_session_factory() as session:
            session.add(JobRecord(id="l10-job", status="failed", progress=40, provider="montage", image_filename="l10.png",
                                  current_step="Rendu ffmpeg (aperçu 480p)", error="Source image not found: a.png"))
            await session.commit()
        brut = (await c.get("/api/jobs/l10-job")).json()
        en = (await c.get("/api/jobs/l10-job", headers={"Accept-Language": "en"})).json()
        fr = (await c.get("/api/jobs/l10-job", headers={"Accept-Language": "fr"})).json()
        liste = [j for j in (await c.get("/api/jobs", headers={"Accept-Language": "en"})).json() if j["job_id"] == "l10-job"]
        verifier("7.3 sans en-tête : étape et erreur du code",
                 brut["current_step"] == "Rendu ffmpeg (aperçu 480p)" and brut["error"] == "Source image not found: a.png", brut)
        verifier("7.4 GET /jobs/{id} en anglais : étape traduite, erreur anglaise gardée",
                 en["current_step"] == "ffmpeg render (480p preview)" and en["error"] == brut["error"], en)
        verifier("7.5 GET /jobs/{id} en français : étape gardée, erreur traduite",
                 fr["current_step"] == brut["current_step"] and fr["error"] != brut["error"] and "a.png" in fr["error"], fr)
        verifier("7.6 GET /jobs (liste) en anglais : la même étape traduite",
                 len(liste) == 1 and liste[0]["current_step"] == en["current_step"], liste)
    d = {"message": "Source image not found: a.png", "code": "x", "usd": 1.5}
    t = ERR.detail(d, "fr")
    verifier("4.7 detail dict : le champ message traduit sur une COPIE, le reste intact",
             t is not d and t["message"] != d["message"] and t["code"] == "x" and t["usd"] == 1.5
             and d["message"] == "Source image not found: a.png", t)

asyncio.run(_http())
print(f"\n{len(OK)} ok, {len(KO)} échec(s)")
sys.exit(1 if KO else 0)
