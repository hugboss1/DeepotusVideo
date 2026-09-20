"""Texte & logo (D7) — la bibliothèque de polices DÉPOSÉES par
l'utilisateur, à côté de celles du dist (OFL) : `DATA_ROOT/fonts/<nom>`,
vérifiées par leur magic (TTF 00010000 / true, OTF OTTO, WOFF wOFF, WOFF2
wOF2), nom assaini, jamais de chemin. Globale au poste, pas au document.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from app.config import DATA_ROOT

DOSSIER = DATA_ROOT / "fonts"
_EXT = {".ttf", ".otf", ".woff", ".woff2"}
_NOM = re.compile(r"^[A-Za-z0-9_-]+\.(ttf|otf|woff|woff2)$")
_MAGIC = (b"\x00\x01\x00\x00", b"true", b"OTTO", b"wOFF", b"wOF2")


def _sain(nom: str) -> str:
    base = Path(str(nom or "")).name
    racine, ext = os.path.splitext(base)
    racine = re.sub(r"\s+", "-", racine.strip())
    racine = re.sub(r"[^A-Za-z0-9_-]", "", racine)
    return f"{racine}{ext.lower()}"


def octets_valides(nom: str, octets: bytes) -> bool:
    n = _sain(nom)
    return bool(_NOM.match(n)) and os.path.splitext(n)[1] in _EXT and len(octets) >= 12 and octets[:4] in _MAGIC


def lister() -> list[dict]:
    if not DOSSIER.is_dir():
        return []
    out = []
    for p in sorted(DOSSIER.iterdir()):
        if p.is_file() and _NOM.match(p.name):
            out.append({"nom": p.name, "famille": p.stem})
    return out


def deposer(nom: str, octets: bytes) -> str:
    if any(x in str(nom or "") for x in ("/", "\\", "..")):
        raise ValueError("police : un nom de fichier, pas un chemin")
    n = _sain(nom)
    if not octets_valides(n, octets):
        raise ValueError("police : fichier TTF / OTF / WOFF / WOFF2 attendu (nom [A-Za-z0-9_-])")
    DOSSIER.mkdir(parents=True, exist_ok=True)
    tmp = DOSSIER / (n + ".tmp")
    tmp.write_bytes(octets)
    os.replace(tmp, DOSSIER / n)
    return n


def lire(nom: str):
    if not _NOM.match(str(nom or "")):
        return None
    p = DOSSIER / nom
    return p.read_bytes() if p.is_file() else None


MEDIA = {".ttf": "font/ttf", ".otf": "font/otf", ".woff": "font/woff", ".woff2": "font/woff2"}
