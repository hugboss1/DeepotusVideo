# -*- coding: utf-8 -*-
"""Import Figma → Bibliothèque (plan 2026-08-28-bibliotheque-unifiee).

Un lien de calque Figma (node-id présent) devient un PNG de la
Bibliothèque via l'API REST officielle (`GET /v1/images/{key}`) et le
Personal Access Token de l'utilisateur (`FIGMA_TOKEN` du .env). Les deux
pas réseau passent par des HOOKS module (`_get_json`, `_get_bytes`) —
monkeypatchés au banc, qui ne sort jamais (patron _lancer_startfile).
"""
from __future__ import annotations

import re
from pathlib import Path

_RE_CLE = re.compile(r"figma\.com/(?:file|design)/([A-Za-z0-9]+)")
_RE_NODE = re.compile(r"[?&]node-id=([0-9]+)(?:-|:|%3A|%3a)([0-9]+)")

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def figma_cible(url: str) -> dict:
    """{cle, node} depuis un lien Figma — refus PARLANTS sinon."""
    u = str(url or "")
    m = _RE_CLE.search(u)
    if not m:
        raise ValueError("pas un lien Figma (attendu "
                         "figma.com/design/... ou figma.com/file/...)")
    n = _RE_NODE.search(u)
    if not n:
        raise ValueError("le lien ne pointe pas un calque : dans Figma, "
                         "sélectionne l'élément puis copie SON lien "
                         "(clic droit → Copy link — le node-id doit être "
                         "dans l'URL)")
    return {"cle": m.group(1), "node": f"{n.group(1)}:{n.group(2)}"}


async def _get_json(url: str, jeton: str) -> dict:  # pragma: no cover — mock
    import httpx
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(url, headers={"X-Figma-Token": jeton})
        if r.status_code != 200:
            return {"err": f"Figma {r.status_code}: {r.text[:200]}"}
        return r.json()


async def _get_bytes(url: str) -> bytes:            # pragma: no cover — mock
    import httpx
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as c:
        r = await c.get(url)
        return r.content if r.status_code == 200 else b""


async def importer(url: str, jeton: str, dossier) -> str:
    """Rend le nom du PNG écrit dans `dossier`. ValueError = lien fautif
    (400), RuntimeError = Figma fautif (502). Ré-importer RÉÉCRIT en place
    (même nom) : rafraîchir un calque ne duplique jamais."""
    cible = figma_cible(url)
    api = (f"https://api.figma.com/v1/images/{cible['cle']}"
           f"?ids={cible['node']}&format=png&scale=2")
    rep = await _get_json(api, jeton)
    if rep.get("err"):
        raise RuntimeError(str(rep["err"]))
    lien = (rep.get("images") or {}).get(cible["node"])
    if not lien:
        raise RuntimeError("Figma n'a pas rendu ce calque ("
                           + str(rep.get("error") or rep.get("status")
                                 or "réponse vide") + ")")
    octets = await _get_bytes(str(lien))
    if not octets.startswith(_PNG_MAGIC):
        raise RuntimeError("le rendu Figma n'est pas un PNG lisible")
    nom = f"figma_{cible['cle']}_{cible['node'].replace(':', '-')}.png"
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / nom).write_bytes(octets)
    return nom
