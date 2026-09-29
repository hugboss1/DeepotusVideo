"""Diagnostic en un écran (plan Settings T1 — tâche #15 du suivi, 29/09/2026).

Trois mesures indépendantes :
  · le poids de DATA_ROOT par catégorie (marche sur disque, cache 300 s — mesuré
    le 03/09 : 4,3 s pour 14,9 Go, insupportable à chaque ouverture d'écran) ;
    les catégories ne s'emboîtent jamais (pas de double compte), `rebut_*` est
    compté à part, le reste tombe dans « Autre » : la somme des catégories est
    le total ;
  · le journal loguru filtré (WARNING / ERROR / CRITICAL) des trois derniers
    fichiers `deepotus-*.log` ;
  · un test LÉGER par clé : un appel authentifié qui ne dépense rien. Jamais la
    valeur d'une clé dans un résultat (message d'exception compris).
Les hooks réseau (`_get`, et HeyGen) sont remplacés au banc (test_diagnostic).
"""
import asyncio
import os
import re
import shutil
import time
from pathlib import Path

import httpx

from app.config import DATA_ROOT, SSL_VERIFY

# Catégories (nom, chemin relatif à DATA_ROOT). Disposition relevée le 29/09/2026 sur le DATA_ROOT réel ; aucune
# n'en contient une autre (le banc le vérifie).
CATEGORIES = [
    ("Images (Bibliothèque)", "assets/images"),
    ("Rendus vidéo", "assets/outputs/videos"),
    ("Rendus finaux", "assets/outputs/final"),
    ("Audio des rendus", "assets/outputs/audio"),
    ("Sous-titres", "assets/outputs/captions"),
    ("Envois (vidéos importées)", "assets/outputs/uploads"),
    ("Cache du Montage", "assets/outputs/montage_cache"),
    ("Cache des rendus", "assets/outputs/_cache"),
    ("3D Meshy", "assets/outputs/meshy3d"),
    ("Assets 3D", "assets/outputs/assets3d"),
    ("Decks Cardforge", "assets/outputs/decks"),
    ("Matières", "assets/outputs/materials"),
    ("Sprites", "assets/outputs/sprites"),
    ("Audio (Bibliothèque)", "assets/audio"),
    ("Impression 3D", "assets/print3d"),
    ("Vectorlab", "assets/vector"),
    ("News", "assets/news"),
    ("Projets de montage", "assets/montage_projects"),
    ("Modèles Cardforge", "cardforge_models"),
    ("Séries Cardforge", "cardforge_series"),
    ("Cache", "cache"),
    ("Journal", "logs"),
    ("Base de données", "deepotus.db"),
]
_cache: dict = {"t": 0.0, "racine": None, "val": None}


def _taille(p: Path) -> tuple[int, int]:
    """(octets, fichiers) d'un fichier ou d'une arborescence ; les erreurs d'accès sont ignorées."""
    try:
        if p.is_file():
            return p.stat().st_size, 1
    except OSError:
        return 0, 0
    octets = fichiers = 0
    for racine, _d, fs in os.walk(p, onerror=lambda e: None):
        for f in fs:
            try:
                octets += os.stat(os.path.join(racine, f)).st_size
                fichiers += 1
            except OSError:
                pass
    return octets, fichiers


def poids_disque(racine: Path = DATA_ROOT, cache_s: int = 300) -> dict:
    racine = Path(racine)
    if _cache["val"] and _cache["racine"] == racine and time.time() - _cache["t"] < cache_s:
        return _cache["val"]
    cats = []
    for nom, rel in CATEGORIES:
        p = racine / rel
        o, f = _taille(p) if p.exists() else (0, 0)
        cats.append({"nom": nom, "chemin": str(p), "octets": o, "fichiers": f})
    rebuts = sorted(x for x in racine.glob("rebut_*") if x.is_dir()) if racine.is_dir() else []
    ro = rf = 0
    for x in rebuts:
        o, f = _taille(x)
        ro += o
        rf += f
    cats.append({"nom": "Rebuts", "chemin": " ; ".join(str(x) for x in rebuts), "octets": ro, "fichiers": rf})
    total, tf = _taille(racine) if racine.exists() else (0, 0)
    cats.append({"nom": "Autre", "chemin": str(racine), "octets": max(0, total - sum(c["octets"] for c in cats)),
                 "fichiers": max(0, tf - sum(c["fichiers"] for c in cats))})
    try:
        libre = shutil.disk_usage(racine if racine.exists() else racine.anchor or ".").free
    except OSError:
        libre = 0
    val = {"racine": str(racine), "categories": cats, "total_octets": total, "libre_octets": libre,
           "mesure_le": time.strftime("%Y-%m-%d %H:%M:%S")}
    _cache.update(t=time.time(), racine=racine, val=val)
    return val


# « 2026-09-28 18:15:10.486 | WARNING  | app.services.marketing:_fetch_x_metrics_sync:612 - x metrics … »
_LIGNE = re.compile(r"^(\S+ \S+) \| (WARNING|ERROR|CRITICAL)\s*\| (\S+) - (.*)$")


def journal_erreurs(dossier: Path = DATA_ROOT / "logs", n: int = 50) -> list[dict]:
    dossier = Path(dossier)
    fichiers = sorted(dossier.glob("deepotus-*.log")) if dossier.is_dir() else []
    out: list[dict] = []
    for f in fichiers[-3:]:
        try:
            lignes = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for ligne in lignes:
            m = _LIGNE.match(ligne)
            if m:
                out.append({"quand": m.group(1), "niveau": m.group(2), "ou": m.group(3), "message": m.group(4)})
    return out[-n:] if n > 0 else []


async def _get(url: str, headers: dict | None = None, timeout: float = 15.0):
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=timeout) as c:
        r = await c.get(url, headers=headers or {})
    try:
        corps = r.json()
    except ValueError:
        corps = r.text[:200]
    return r.status_code, corps


def _msg(corps) -> str:
    if isinstance(corps, dict):
        e = corps.get("error") or corps.get("detail") or corps.get("message") or corps.get("description")
        if isinstance(e, dict):
            e = e.get("message") or str(e)
        return str(e or corps)[:200]
    return str(corps)[:200]


def _res(ok, message, **details):
    return {"ok": ok, "message": message, "details": details}


async def _simple(url, headers, ok_sur=(200,), libelle=""):
    code, corps = await _get(url, headers)
    if code in ok_sur:
        return code, corps, _res(True, f"clé acceptée ({libelle or code})")
    if code in (401, 403):
        return code, corps, _res(False, f"refusée ({code}) : {_msg(corps)}")
    return code, corps, _res(None, f"indéterminé (HTTP {code}) : {_msg(corps)}")


def _sans(texte: str, secret: str) -> str:
    """Un message ne recopie jamais la clé (une exception peut porter l'URL qui la contient)."""
    return texte.replace(secret, "…") if secret else texte


async def tester_cle(nom: str, valeur: str) -> dict:
    v = (valeur or "").strip()
    if not v:
        return _res(None, "vide")
    try:
        if nom == "FAL_KEY":
            _c, _b, r = await _simple("https://queue.fal.run/fal-ai/flux/schnell/requests/"
                                      "00000000-0000-0000-0000-000000000000/status",
                                      {"Authorization": f"Key {v}"}, ok_sur=(404,),
                                      libelle="404 sur une requête fictive, comme attendu")
            return r
        if nom == "HEYGEN_API_KEY":
            from app.services.heygen_service import HeyGenClient
            q = await HeyGenClient(api_key=v).remaining_quota()
            return _res(True, "clé acceptée", credits=q.get("remaining_quota"), usd=q.get("remaining_usd"))
        if nom == "ELEVENLABS_API_KEY":
            _c, corps, r = await _simple("https://api.elevenlabs.io/v1/user/subscription", {"xi-api-key": v})
            if r["ok"] and isinstance(corps, dict):
                u, lim = corps.get("character_count"), corps.get("character_limit")
                r["details"] = {"utilise": u, "limite": lim,
                                "restant": (lim - u) if (u is not None and lim is not None) else None}
            return r
        if nom == "MESHY_API_KEY":
            from app.services import meshy_service as MS
            _c, corps, r = await _simple(f"{MS.MESHY_API}/openapi/v1/balance", {"Authorization": f"Bearer {v}"})
            if r["ok"] and isinstance(corps, dict):
                r["details"] = {"credits": corps.get("balance")}
            return r
        if nom == "ANTHROPIC_API_KEY":
            _c, _b, r = await _simple("https://api.anthropic.com/v1/models",
                                      {"x-api-key": v, "anthropic-version": "2023-06-01"})
            return r
        if nom == "OPENAI_API_KEY":
            _c, _b, r = await _simple("https://api.openai.com/v1/models", {"Authorization": f"Bearer {v}"})
            return r
        if nom == "GEMINI_API_KEY":
            _c, _b, r = await _simple("https://generativelanguage.googleapis.com/v1beta/models", {"x-goog-api-key": v})
            return r
        if nom == "FIGMA_TOKEN":
            _c, corps, r = await _simple("https://api.figma.com/v1/me", {"X-Figma-Token": v})
            if r["ok"] and isinstance(corps, dict):
                r["details"] = {"compte": corps.get("handle")}
            return r
        if nom == "TELEGRAM_BOT_TOKEN":
            code, corps = await _get(f"https://api.telegram.org/bot{v}/getMe")
            if code == 200 and isinstance(corps, dict) and corps.get("ok"):
                return _res(True, "jeton accepté", bot=(corps.get("result") or {}).get("username"))
            return _res(False if code in (401, 404) else None, _sans(f"refusé ({code}) : {_msg(corps)}", v))
        if nom == "OLLAMA_URL":
            code, corps = await _get(f"{v.rstrip('/')}/api/tags", timeout=5.0)
            if code == 200 and isinstance(corps, dict):
                return _res(True, "Ollama joignable", modeles=[m.get("name") for m in corps.get("models", [])])
            return _res(False, f"injoignable ({code})")
        if nom.startswith("X_"):
            return _res(None, "les quatre clés X se testent ensemble (bouton du groupe « Connected accounts »)")
        return _res(None, "pas de test pour cette clé")
    except Exception as e:  # noqa: BLE001 — un test ne casse jamais l'écran
        return _res(False, _sans(f"erreur : {str(e)[:160]}", v))


async def tester_x(cles: dict) -> dict:
    """OAuth 1.0a via tweepy (déjà utilisé par marketing.py)."""
    noms = ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")
    if not all(cles.get(k) for k in noms):
        return _res(None, "il faut les quatre clés X")

    def _sync():
        import tweepy
        c = tweepy.Client(consumer_key=cles["X_API_KEY"], consumer_secret=cles["X_API_SECRET"],
                          access_token=cles["X_ACCESS_TOKEN"], access_token_secret=cles["X_ACCESS_SECRET"])
        return c.get_me()
    try:
        me = await asyncio.get_running_loop().run_in_executor(None, _sync)
        return _res(True, "compte X joint", compte=getattr(getattr(me, "data", None), "username", None))
    except Exception as e:  # noqa: BLE001
        m = str(e)[:160]
        for k in noms:
            m = _sans(m, str(cles.get(k) or ""))
        return _res(False, f"refusé : {m}")


# Les clés pour lesquelles `tester_cle` sait faire un appel authentifié qui ne dépense rien. Les autres (modèles,
# identifiants de voix, chat id…) sont des RÉGLAGES, pas des secrets à valider : l'écran n'affiche pas de bouton.
TESTABLES = {
    "FAL_KEY", "HEYGEN_API_KEY", "ELEVENLABS_API_KEY", "MESHY_API_KEY",
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "FIGMA_TOKEN",
    "TELEGRAM_BOT_TOKEN", "OLLAMA_URL",
    "X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET",
}


def testable(nom: str) -> bool:
    return nom in TESTABLES
