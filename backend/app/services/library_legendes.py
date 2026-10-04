# -*- coding: utf-8 -*-
"""Tâche #82 PR C (04/10/2026, plan-library T12-T13) — les LÉGENDES des images, par un modèle vision PAYANT.

Décision de l'utilisateur (04/10) : la recherche « par description » regarde les images — 942 des 1009 images réelles
s'appellent gen_<hex>.png, sans tag ni recette : il n'y avait rien à lire. Deux moteurs avec un SÉLECTEUR : des légendes
par un modèle vision payant (ici) et CLIP en local (PR D). Le prix est ANNONCÉ avant tout appel (devis), le plafond
« bibliothèque » est la garde du serveur, et l'utilisateur est prévenu que les images partent chez Google.
Modèle : Gemini 2.5 Flash-Lite (relevé du 04/10/2026, ai.google.dev/gemini-api/docs/pricing : 0,10 $ / M jetons en
entrée, 0,40 $ en sortie) ; une image ramenée à 384 px compte 258 jetons (docs « image understanding ») — ≈ 0,00006 $
par image, ≈ 0,06 $ pour la bibliothèque. Le plan voulait un service local « Clipbox » qui n'existe pas, et un chemin
distant sans prix ni plafond.
Le travail tourne en TÂCHE DE FOND (≈ 1000 images), quatre appels à la fois ; GET /library/legendes/etat le suit.
"""
from __future__ import annotations

import asyncio
import base64
import io
from pathlib import Path

from loguru import logger

from app.config import settings, SSL_VERIFY

MODELE = "gemini-2.5-flash-lite"
JETONS_IMAGE, JETONS_CONSIGNE, JETONS_SORTIE = 258, 90, 70   # devis : une image <= 384 px, la consigne, ~40 mots
PARALLELE = 4
CONSIGNE = ("Décris cette image en une ou deux phrases en français, puis donne 5 à 10 mots-clés en français et en "
            "anglais, séparés par des virgules. Sujet, style, couleurs dominantes, ambiance. Pas de préambule.")
ETAT = {"en_cours": False, "total": 0, "faits": 0, "erreurs": [], "modele": MODELE, "arret": ""}
_TACHE: set = set()


def disponible() -> bool:
    return bool(settings.GEMINI_API_KEY.strip())


async def a_legender(noms: list[str] | None = None) -> list[str]:
    """Les images (au magasin) SANS légende — ou celles nommées."""
    from sqlalchemy import select
    from app.services.storage import LibraryAsset, async_session_factory
    async with async_session_factory() as s:
        q = select(LibraryAsset.filename).where(LibraryAsset.kind == "image")
        q = q.where(LibraryAsset.filename.in_(noms)) if noms else q.where(LibraryAsset.legende.is_(None))
        tous = [r[0] for r in (await s.execute(q)).fetchall()]
    return [n for n in tous if (settings.images_path / n).is_file()]


def devis(n: int) -> dict:
    from app.services import pricing as P
    d = P.estimate({"kind": "legende", "n": int(n), "model": MODELE})
    return {"n": int(n), "usd": d["total_usd"], "modele": MODELE, "cle": disponible(), "lignes": d["breakdown"]}


def _vignette(p: Path) -> str:
    from PIL import Image
    with Image.open(p) as im:
        im = im.convert("RGB")
        im.thumbnail((384, 384))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("ascii")


async def _appel(client, b64: str) -> str:
    """UN appel Gemini (couture remplacée par les bancs : aucun appel réel). Rend le texte, lève sur erreur."""
    from app.services.google_video import GOOGLE_API_BASE, google_headers
    r = await client.post(f"{GOOGLE_API_BASE}/models/{MODELE}:generateContent",
                          headers={"Content-Type": "application/json", **google_headers()},
                          json={"contents": [{"parts": [{"inline_data": {"mime_type": "image/jpeg", "data": b64}}, {"text": CONSIGNE}]}],
                                "generationConfig": {"maxOutputTokens": 200, "temperature": 0.2}})
    if r.status_code != 200:
        raise RuntimeError(f"Gemini HTTP {r.status_code} : {r.text[:160]}")
    parts = ((r.json().get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
    txt = " ".join(str(p.get("text") or "") for p in parts).strip()
    if not txt:
        raise RuntimeError("Gemini n'a rien rendu")
    return txt[:1200]


async def _ecrire(nom: str, texte: str) -> None:
    from sqlalchemy import update
    from app.services.storage import LibraryAsset, async_session_factory
    async with async_session_factory() as s:
        await s.execute(update(LibraryAsset).where(LibraryAsset.filename == nom).values(legende=texte, legende_modele=MODELE))
        await s.commit()


async def _travailler(noms: list[str]) -> None:
    import httpx
    sem = asyncio.Semaphore(PARALLELE)
    ETAT.update(en_cours=True, total=len(noms), faits=0, erreurs=[], arret="")
    async with httpx.AsyncClient(verify=SSL_VERIFY, timeout=60.0) as client:
        async def un(nom):
            if ETAT["arret"]:
                return
            async with sem:
                if ETAT["arret"]:
                    return
                try:
                    b64 = await asyncio.to_thread(_vignette, settings.images_path / nom)
                    txt = await _appel(client, b64)
                    await _ecrire(nom, txt)
                    ETAT["faits"] += 1
                except Exception as e:  # noqa: BLE001 — une image ratée n'arrête pas les autres…
                    msg = str(e)
                    ETAT["erreurs"].append({"filename": nom, "erreur": msg[:200]})
                    if "HTTP 401" in msg or "HTTP 403" in msg or "HTTP 429" in msg:
                        ETAT["arret"] = msg[:200]   # … sauf une clé refusée ou un quota : on s'arrête
        await asyncio.gather(*(un(n) for n in noms))
    ETAT["en_cours"] = False
    logger.info(f"library_legendes : {ETAT['faits']}/{ETAT['total']} image(s) légendée(s), {len(ETAT['erreurs'])} erreur(s)")


def lancer(noms: list[str]) -> bool:
    """Démarre le travail en tâche de fond ; False si un travail tourne déjà."""
    if ETAT["en_cours"]:
        return False
    ETAT.update(en_cours=True, total=len(noms), faits=0, erreurs=[], arret="")

    async def _go():
        try:
            await _travailler(noms)
        except Exception as e:  # noqa: BLE001
            ETAT.update(en_cours=False, arret=str(e)[:200])
    t = asyncio.get_running_loop().create_task(_go())
    _TACHE.add(t)
    t.add_done_callback(_TACHE.discard)
    return True


def etat() -> dict:
    return {**ETAT, "erreurs": ETAT["erreurs"][-20:], "n_erreurs": len(ETAT["erreurs"])}
