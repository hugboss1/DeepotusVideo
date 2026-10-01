# -*- coding: utf-8 -*-
"""Vérification de mise à jour (plan Settings T10 — tâche #18, 29/09/2026) : cache, cadence, versions, préversion,
téléchargement gardé (redirections comprises), routes.
Banc-miroir : le cache est relu SUR LE DISQUE (maj.json), le fichier téléchargé octet à octet. Zéro réseau : `_json`
est remplacé, et le téléchargement passe par un `httpx.MockTransport` qui rejoue la chaîne mesurée le 29/09
(github.com → 302 → release-assets.githubusercontent.com).
Run : & $PY tests/test_mise_a_jour.py   (depuis backend/)"""
import asyncio, json, os, pathlib, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzmaj_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()
import httpx                                                        # noqa: E402
from app.config import APP_VERSION                                  # noqa: E402
from app.services import mise_a_jour as M                           # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


EXE = "https://github.com/hugboss1/DeepotusVideo/releases/download/v9.1.0/DeepotusVideoGen-Setup-9.1.0.exe"
REPONSE = {
    "tag_name": "v9.1.0", "name": "Deepotus Video Gen v9.1.0", "body": "- plafonds de dépense\n- coffre",
    "html_url": "https://github.com/hugboss1/DeepotusVideo/releases/tag/v9.1.0",
    "published_at": "2026-10-01T09:00:00Z", "draft": False, "prerelease": False,
    "assets": [
        {"name": "notes.txt", "size": 12, "browser_download_url": "https://github.com/x/notes.txt"},
        {"name": "piege.exe", "size": 5, "browser_download_url": "https://exemple.invalide/piege.exe"},
        {"name": "DeepotusVideoGen-Setup-9.1.0.exe", "size": 32, "browser_download_url": EXE},
    ],
}
APPELS = []


async def _faux_json(url, timeout=10.0):
    APPELS.append(url)
    return 200, json.loads(json.dumps(REPONSE))
M._json = _faux_json


def cache():
    return json.loads((_tmp / "maj.json").read_text(encoding="utf-8"))


async def sc():
    print("\n[1] versions")
    check("1.1 « v » initial ignoré, nombres comparés (2.10.0 > 2.9.9), suffixe toléré, illisible = 0.0.0",
          M._tuple("v2.6.0") == (2, 6, 0) and M._tuple("v2.10.0") > M._tuple("v2.9.9")
          and M._tuple("2.6.0-rc1") == (2, 6, 0) and M._tuple("nimporte") == (0, 0, 0), "")

    print("\n[2] vérification et cache")
    r = await M.verifier()
    check("2.1 URL exacte de l'API GitHub, dépôt constant", APPELS == ["https://api.github.com/repos/hugboss1/DeepotusVideo/releases/latest"], str(APPELS))
    check("2.2 9.1.0 > installée : disponible, les deux versions dites", r["disponible"] is True and r["tag"] == "v9.1.0"
          and r["installee"] == APP_VERSION, json.dumps(r)[:200])
    check("2.3 l'installeur choisi est le .exe servi par les Releases de CE dépôt (ni notes.txt, ni un .exe étranger)",
          r["asset"] == {"nom": "DeepotusVideoGen-Setup-9.1.0.exe", "octets": 32, "url": EXE}, json.dumps(r["asset"]))
    check("2.4 notes de version et lien présents", "coffre" in r["notes"] and r["url"].endswith("/v9.1.0"), "")
    check("2.5 cache écrit sur le disque", cache()["tag"] == "v9.1.0", "")
    await M.verifier()
    check("2.6 moins de 24 h : aucun second appel", len(APPELS) == 1, str(len(APPELS)))
    await M.verifier(force=True)
    check("2.7 force : on redemande", len(APPELS) == 2, str(len(APPELS)))
    c = cache(); c["verifie_a"] = time.time() - 25 * 3600
    (_tmp / "maj.json").write_text(json.dumps(c), encoding="utf-8")
    await M.verifier()
    check("2.8 plus de 24 h : on redemande", len(APPELS) == 3, str(len(APPELS)))
    c = cache(); c["installee"] = "0.0.1"
    (_tmp / "maj.json").write_text(json.dumps(c), encoding="utf-8")
    await M.verifier()
    check("2.9 un cache écrit par une AUTRE version installée n'est pas frais (après une mise à jour, on redemande)",
          len(APPELS) == 4 and cache()["installee"] == APP_VERSION, str(len(APPELS)))

    print("\n[3] jamais bloquant")
    async def _casse(url, timeout=10.0):
        raise OSError("le réseau est coupé")
    M._json = _casse
    r = await M.verifier(force=True)
    check("3.1 réseau coupé : le cache répond, l'échec est DIT", r["tag"] == "v9.1.0" and r["erreur"].startswith("le réseau"), json.dumps(r)[:200])
    async def _404(url, timeout=10.0):
        return 404, {"message": "Not Found"}
    M._json = _404
    (_tmp / "maj.json").unlink()
    r = await M.verifier(force=True)
    check("3.2 sans cache et GitHub en 404 : rien d'annoncé, l'erreur est dite", r["disponible"] is False and r["erreur"] == "GitHub a répondu 404", json.dumps(r)[:200])
    M._json = _faux_json

    print("\n[4] préversion et version déjà installée")
    REPONSE["prerelease"] = True
    r = await M.verifier(force=True)
    check("4.1 une préversion n'est pas proposée", r["disponible"] is False and r["tag"] == "" and r["asset"] == {}, json.dumps(r)[:200])
    REPONSE["prerelease"] = False
    REPONSE["tag_name"] = "v" + APP_VERSION
    r = await M.verifier(force=True)
    check("4.2 la Release publiée = la version installée : pas de mise à jour", r["disponible"] is False and r["tag"] == "v" + APP_VERSION, "")
    maj, mineur, _p = M._tuple(APP_VERSION)
    REPONSE["tag_name"] = f"v{maj}.{mineur + 10 if mineur < 10 else mineur * 10}.0"
    r = await M.verifier(force=True)
    check("4.3 v%s.%s.0 face à %s : PLUS RÉCENTE par les nombres (le texte dirait l'inverse)" % (maj, mineur + 10 if mineur < 10 else mineur * 10, APP_VERSION),
          r["disponible"] is True and r["tag"].lstrip("v") < APP_VERSION, json.dumps(r)[:160])
    REPONSE["tag_name"] = "v9.1.0"
    await M.verifier(force=True)

    print("\n[5] téléchargement gardé")
    r = await M.telecharger("https://exemple.invalide/vilain.exe", "v.exe", 10)
    check("5.1 URL hors des Releases du dépôt : refus dit", r["ok"] is False and "github.com/hugboss1/DeepotusVideo" in r["erreur"], json.dumps(r))
    r = await M.telecharger("https://github.com/autre/depot/releases/download/v1/x.exe", "x.exe", 10)
    check("5.2 un AUTRE dépôt GitHub : refusé aussi", r["ok"] is False, json.dumps(r))

    corps = b"MZ" + b"\0" * 30
    def _chaine(dest):
        def h(req):
            if req.url.host == "github.com":
                return httpx.Response(302, headers={"Location": dest})
            return httpx.Response(200, content=corps, headers={"content-length": str(len(corps))})
        return httpx.MockTransport(h)
    vrai_flux = M._flux

    async def _flux_ok(url, cible, taille, etat):
        await vrai_flux(url, cible, taille, etat, transport=_chaine("https://release-assets.githubusercontent.com/asset/1?sig=x"))
    M._flux = _flux_ok
    r = await M.telecharger(EXE, "DeepotusVideoGen-Setup-9.1.0.exe", 32)
    f = pathlib.Path(r.get("chemin", ""))
    check("5.3 chaîne réelle (302 vers release-assets.githubusercontent.com) : fichier écrit, octet pour octet",
          r["ok"] is True and f.is_file() and f.read_bytes() == corps, json.dumps(r))
    check("5.4 rangé dans DATA_ROOT/telechargements, aucun .partiel laissé, rien lancé",
          f.parent == _tmp / "telechargements" and not list(f.parent.glob("*.partiel")), "")
    e = M.etat_telechargement()
    check("5.5 état lisible : fini, 32/32 octets, chemin", e["fini"] is True and e["en_cours"] is False and e["octets"] == 32
          and e["total"] == 32 and e["chemin"] == str(f), json.dumps(e))

    async def _flux_vilain(url, cible, taille, etat):
        await vrai_flux(url, cible, taille, etat, transport=_chaine("https://exemple.invalide/pire.exe"))
    M._flux = _flux_vilain
    r = await M.telecharger(EXE, "b.exe", 32)
    check("5.6 une redirection HORS GitHub interrompt tout, rien n'est gardé",
          r["ok"] is False and "exemple.invalide" in r["erreur"] and not (_tmp / "telechargements" / "b.exe").exists()
          and not (_tmp / "telechargements" / "b.exe.partiel").exists(), json.dumps(r))
    M._flux = _flux_ok
    r = await M.telecharger(EXE, "c.exe", 999)
    check("5.7 taille reçue ≠ taille annoncée : refus, fichier supprimé", r["ok"] is False and "999" in r["erreur"]
          and not (_tmp / "telechargements" / "c.exe").exists(), json.dumps(r))
    r = await M.telecharger(EXE, "../../evade.exe", 32)
    check("5.8 un nom avec des « ../ » reste DANS le dossier", r["ok"] is True and pathlib.Path(r["chemin"]).parent == _tmp / "telechargements", json.dumps(r))

asyncio.run(sc())

print("\n[6] routes")
from fastapi.testclient import TestClient                          # noqa: E402
from app.main import app                                            # noqa: E402
with TestClient(app, client=("127.0.0.1", 50000)) as c:
    n = len(APPELS)
    j = c.get("/api/reglages/maj").json()
    check("6.1 GET /maj : le cache, sans appel réseau", j["tag"] == "v9.1.0" and len(APPELS) == n, str(len(APPELS) - n))
    j = c.post("/api/reglages/maj/verifier").json()
    check("6.2 POST /maj/verifier : une vérification forcée", len(APPELS) == n + 1 and j["disponible"] is True, "")
    lances = []

    async def _faux_telecharger(url, nom, octets):
        lances.append((url, nom, octets))
        return {"ok": True}
    vrai_tel = M.telecharger
    M.telecharger = _faux_telecharger
    j = c.post("/api/reglages/maj/telecharger").json()
    import time as _t; _t.sleep(0.3)
    check("6.3 POST /maj/telecharger : rend la main aussitôt et lance l'installeur de la Release EN FOND",
          j == {"ok": True, "lance": True, "nom": "DeepotusVideoGen-Setup-9.1.0.exe", "octets": 32}
          and lances == [(EXE, "DeepotusVideoGen-Setup-9.1.0.exe", 32)], json.dumps(j))
    M._ETAT["en_cours"] = True
    check("6.4 déjà en cours : 409", c.post("/api/reglages/maj/telecharger").status_code == 409, "")
    M._ETAT["en_cours"] = False
    check("6.5 suivi du téléchargement", c.get("/api/reglages/maj/telechargement").json()["fini"] is True, "")
    REPONSE["tag_name"] = "v" + APP_VERSION
    c.post("/api/reglages/maj/verifier")
    check("6.6 rien à mettre à jour : 404, rien lancé", c.post("/api/reglages/maj/telecharger").status_code == 404 and len(lances) == 1, "")
    M.telecharger = vrai_tel
import sys as _sys, os as _os; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # noqa: E401,E702
import _jeton_appareil as _JA  # noqa: E402 — tache #56 : le reseau local exige un jeton d'appareil (garde exterieure)
with TestClient(app, client=("192.168.1.20", 50000), headers=_JA.entetes(app)) as c2:
    check("6.7 hors boucle locale : lecture et téléchargement refusés", c2.get("/api/reglages/maj").status_code == 403
          and c2.post("/api/reglages/maj/telecharger").status_code == 403, "")

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
