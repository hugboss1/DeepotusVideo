# -*- coding: utf-8 -*-
"""Guides fournisseurs, clés appliquées à chaud, test à l'enregistrement (plan Settings T8 — tâche #17, 29/09/2026).
Banc-miroir : après un POST, le banc RELIT le `.env` sur disque, l'objet `settings`, `os.environ`, et surtout les
identifiants que le client `fal_client` enverrait VRAIMENT (le cache `_auth` de son client module) et la clé du
`HeyGenClient` mémorisé par `pipeline` — les deux captures que « écrire dans settings » ne suffisait pas à changer.
Témoin : la base 1656085 répond `restart_required: True` et n'a pas de guides. Zéro réseau (tests de clé remplacés).
Run : & $PY tests/test_guides_et_cles.py   (depuis backend/)"""
import asyncio, json, os, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzcles_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
(_tmp / ".env").write_text("FAL_KEY=ancienne\nHEYGEN_API_KEY=hg-ancienne\n", encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from loguru import logger                                           # noqa: E402
logger.remove()
from fastapi.testclient import TestClient                          # noqa: E402
import fal_client                                                   # noqa: E402
from app.main import app                                            # noqa: E402
from app.config import settings                                     # noqa: E402
from app.api import routes as R                                     # noqa: E402
from app.services import diagnostic as D, guides_fournisseurs as G  # noqa: E402

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


def env():
    return (_tmp / ".env").read_text(encoding="utf-8")


appels = []


async def _faux_test(nom, valeur):
    appels.append(nom)
    return {"ok": True, "message": f"accepté ({nom})"}


async def _faux_x(cles):
    appels.append("X")
    return {"ok": True, "message": "compte @moi"}

D.tester_cle, D.tester_x = _faux_test, _faux_x


def auth_fal():
    async def _lire():
        return (await fal_client.async_client._auth).header_value
    return asyncio.run(_lire())


print("\n[0] témoin : la base 1656085")
racine = pathlib.Path(__file__).resolve().parents[2]
vieux = subprocess.run(["git", "show", "1656085:backend/app/api/routes.py"], cwd=racine, capture_output=True).stdout.decode("utf-8")
g0 = subprocess.run(["git", "show", "1656085:backend/app/services/guides_fournisseurs.py"], cwd=racine, capture_output=True)
check("0.1 TÉMOIN : l'ancien set_key exigeait toujours un redémarrage, et aucun guide n'existait",
      vieux.count('"restart_required": True,') == 2 and g0.returncode != 0, "")

print("\n[1] guides")
g = G.tous()
for cle in sorted(D.TESTABLES):
    e = g.get(cle) or {}
    check(f"1.x {cle} : console https, textes FR et EN, lien OUVERT le 29/09",
          e.get("console", "").startswith("https://") and len(e.get("fr", "")) > 80 and len(e.get("en", "")) > 80
          and e.get("verifie_le") == "2026-09-29", json.dumps(e, ensure_ascii=False)[:160])
brut = json.dumps(g)
check("1.2 aucun des quatre liens qui avaient bougé au 29/09",
      all(x not in brut for x in ("console.anthropic.com", "/app/settings/api-keys", "figma.com/developers/api",
                                  "ai.google.dev/pricing")), "")
check("1.3 les quatre clés X partagent un guide", g["X_API_SECRET"] == g["X_API_KEY"] == g["X_ACCESS_SECRET"], "")

with TestClient(app, client=("127.0.0.1", 50000)) as c:
    r = c.get("/api/reglages/guides")
    check("1.4 route /api/reglages/guides", r.status_code == 200 and set(D.TESTABLES) <= set(r.json()["guides"]), str(r.status_code))

    print("\n[2] application à chaud")
    check("2.0 le client fal a DÉJÀ mis en cache l'ancienne clé (état de départ réaliste)", auth_fal() == "Key ancienne", auth_fal())
    vieux_client = fal_client.async_client
    j = c.post("/api/settings/keys", json={"entries": [{"name": "FAL_KEY", "value": "cle-neuve"}]}).json()
    check("2.1 plus de redémarrage exigé", j["restart_required"] is False and j["restart_for"] == [] and "appliqué" in j["message"], json.dumps(j))
    check("2.2 .env, settings et os.environ portent la nouvelle clé",
          "FAL_KEY=cle-neuve" in env() and settings.FAL_KEY == "cle-neuve" and os.environ["FAL_KEY"] == "cle-neuve", "")
    check("2.3 le client fal envoie la NOUVELLE clé (son cache d'identifiants est renouvelé)", auth_fal() == "Key cle-neuve", auth_fal())
    check("2.4 les alias du module suivent le nouveau client (subscribe_async, submit_async, upload_file_async)",
          fal_client.async_client is not vieux_client and all(getattr(fal_client, n).__self__ is fal_client.async_client
          for n in ("subscribe_async", "submit_async", "upload_file_async")) and fal_client.subscribe.__self__ is fal_client.sync_client, "")
    check("2.5 la réponse ne renvoie jamais la valeur", "cle-neuve" not in json.dumps(j), "")

    R.pipeline._heygen = None
    check("2.6 départ : pipeline.heygen mémorise l'ancienne clé HeyGen", R.pipeline.heygen.api_key == "hg-ancienne", "")
    c.post("/api/settings/keys", json={"name": "HEYGEN_API_KEY", "value": "hg-neuve"})
    check("2.7 après enregistrement, pipeline.heygen parle avec la NOUVELLE clé", R.pipeline.heygen.api_key == "hg-neuve",
          R.pipeline.heygen.api_key)

    j = c.post("/api/settings/keys", json={"name": "FIGMA_TOKEN", "value": "figd_xyz"}).json()
    check("2.8 FIGMA_TOKEN écrit et appliqué", "FIGMA_TOKEN=figd_xyz" in env() and settings.FIGMA_TOKEN == "figd_xyz"
          and j["restart_required"] is False, "")
    c.post("/api/settings/keys", json={"name": "FIGMA_TOKEN", "value": ""})
    check("2.9 valeur vide : la clé est effacée partout (settings au défaut, os.environ sans elle)",
          settings.FIGMA_TOKEN == "" and "FIGMA_TOKEN" not in os.environ, repr(settings.FIGMA_TOKEN))

    j = c.post("/api/settings/keys", json={"name": "ARTICLE_READER_FALLBACK", "value": "false"}).json()
    check("2.10 champ booléen validé comme au démarrage : « false » -> False, à chaud",
          settings.ARTICLE_READER_FALLBACK is False and j["restart_required"] is False, json.dumps(j))
    j = c.post("/api/settings/keys", json={"name": "ARTICLE_READER_FALLBACK", "value": "peut-être"}).json()
    check("2.11 valeur refusée par pydantic : on DIT redémarrage, settings intact",
          j["restart_required"] is True and j["restart_for"] == ["ARTICLE_READER_FALLBACK"]
          and settings.ARTICLE_READER_FALLBACK is False and "Redémarrage" in j["message"], json.dumps(j, ensure_ascii=False))

    j = c.post("/api/settings/provider-defaults", json={"summarizer": "Ollama"}).json()
    check("2.12 fournisseurs par défaut : appliqués à chaud aussi", settings.SUMMARIZER_PROVIDER == "ollama"
          and j["restart_required"] is False, json.dumps(j))

    print("\n[3] test à l'enregistrement")
    appels.clear()
    c.post("/api/settings/keys", json={"name": "OPENAI_API_KEY", "value": "sk-1"})
    check("3.1 sans `tester`, aucun appel au fournisseur", appels == [], str(appels))
    j = c.post("/api/settings/keys", json={"entries": [{"name": "OPENAI_API_KEY", "value": "sk-2"},
                                                       {"name": "OPENAI_MODEL", "value": "gpt-x"}], "tester": True}).json()
    check("3.2 `tester: true` : la clé testable est testée, le modèle (non testable) non",
          appels == ["OPENAI_API_KEY"] and j["tests"] == {"OPENAI_API_KEY": {"ok": True, "message": "accepté (OPENAI_API_KEY)"}}
          and "sk-2" not in json.dumps(j), json.dumps(j))
    appels.clear()
    j = c.post("/api/settings/keys", json={"entries": [{"name": "X_API_KEY", "value": "a"}], "tester": True}).json()
    check("3.3 une clé X se teste avec les QUATRE (un seul test X, jamais clé par clé)", appels == ["X"] and "X" in j["tests"], json.dumps(j))

with TestClient(app, client=("192.168.1.20", 50000)) as c2:
    avant = env()
    check("4.1 hors boucle locale : écriture refusée et .env intact",
          c2.post("/api/settings/keys", json={"name": "FAL_KEY", "value": "pirate"}).status_code == 403 and env() == avant
          and settings.FAL_KEY == "cle-neuve", "")
    check("4.2 hors boucle locale : guides refusés", c2.get("/api/reglages/guides").status_code == 403, "")

print(f"\n{ok} ok, {fail} fail")
sys.exit(1 if fail else 0)
