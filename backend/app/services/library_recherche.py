# -*- coding: utf-8 -*-
"""Tâche #82 PR C (04/10/2026, plan-library T13) — la RECHERCHE de la Bibliothèque, moteur « texte » (local, gratuit).

Décision de l'utilisateur (04/10) : deux moteurs avec un SÉLECTEUR — « texte » (ici : légendes, tags, prompts,
commentaires, noms) et « clip » (sémantique, local, PR D). Rien ne sort du PC pour chercher.
Méthode : chaque image donne des CHAMPS pondérés (légende 3, tags 3, prompt 2, commentaires 2, nom 1) ; la requête est
normalisée (minuscules, sans accents) et découpée en mots ; un mot trouve un mot du champ qui COMMENCE par lui (« phar »
trouve « phare ») ; TOUS les mots doivent être trouvés (ET) ; le score additionne le meilleur poids par mot. Une image se
reconstruit à chaque requête (≈ 1000 lignes) : pas d'index à tenir à jour, rien à invalider au renommage ou à la corbeille.
"""
from __future__ import annotations

import json
import re
import unicodedata

POIDS = {"legende": 3, "tags": 3, "prompt": 2, "commentaires": 2, "nom": 1}
MAX = 200


def normaliser(s: str) -> list[str]:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode("ascii").lower()
    return [m for m in re.split(r"[^a-z0-9]+", s) if m]


def _mots_du_nom(nom: str) -> list[str]:
    tige = nom.rsplit(".", 1)[0]
    return [m for m in normaliser(tige) if not re.fullmatch(r"[0-9a-f]{6,}|\d+", m)]   # pas les hachages ni les numéros


async def _champs() -> dict[str, dict[str, str]]:
    from sqlalchemy import select
    from app.services.storage import JobRecord, LibraryAsset, LibraryComment, async_session_factory
    out: dict[str, dict[str, str]] = {}
    async with async_session_factory() as s:
        for nom, tags, leg, rec in (await s.execute(select(LibraryAsset.filename, LibraryAsset.tags, LibraryAsset.legende,
                                                           LibraryAsset.recette).where(LibraryAsset.kind == "image"))).fetchall():
            c = {"nom": " ".join(_mots_du_nom(nom))}
            try:
                c["tags"] = " ".join(json.loads(tags or "[]") or [])
            except Exception:  # noqa: BLE001
                c["tags"] = ""
            c["legende"] = leg or ""
            try:
                c["prompt"] = str((json.loads(rec) or {}).get("prompt") or "") if rec else ""
            except Exception:  # noqa: BLE001
                c["prompt"] = ""
            c["commentaires"] = ""
            out[nom] = c
        for img, fp in (await s.execute(select(JobRecord.image_filename, JobRecord.final_prompt)
                                         .where(JobRecord.final_prompt.is_not(None)))).fetchall():
            if img in out and fp:
                out[img]["prompt"] = (out[img]["prompt"] + " " + fp).strip()
        for ref, txt in (await s.execute(select(LibraryComment.ref, LibraryComment.texte))).fetchall():
            if ref in out:
                out[ref]["commentaires"] = (out[ref]["commentaires"] + " " + (txt or "")).strip()
    return out


def _extrait(texte: str, mot: str) -> str:
    t = str(texte or "")
    norm = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii").lower()
    i = norm.find(mot)
    if i < 0:
        return t[:90]
    d = max(0, i - 35)
    return ("…" if d else "") + t[d:d + 110] + ("…" if d + 110 < len(t) else "")


async def chercher(q: str) -> dict:
    mots = [m for m in normaliser(q) if len(m) >= 2]
    if not mots:
        return {"q": q, "moteur": "texte", "mots": [], "resultats": [], "n": 0}
    res = []
    for nom, champs in (await _champs()).items():
        jetons = {k: normaliser(v) for k, v in champs.items()}
        score, pourquoi, extrait = 0, set(), ""
        for m in mots:
            meilleur, ch = 0, None
            for k, toks in jetons.items():
                if POIDS[k] > meilleur and any(t.startswith(m) for t in toks):
                    meilleur, ch = POIDS[k], k
            if not meilleur:
                break
            score += meilleur
            pourquoi.add(ch)
            if not extrait and ch in ("legende", "prompt", "commentaires"):
                extrait = _extrait(champs[ch], m)
        else:
            res.append({"filename": nom, "score": score, "champs": sorted(pourquoi), "extrait": extrait})
    res.sort(key=lambda r: (-r["score"], r["filename"]))
    return {"q": q, "moteur": "texte", "mots": mots, "resultats": res[:MAX], "n": len(res)}
