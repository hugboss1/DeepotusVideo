#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rapatrie l'état de l'app installée (%LOCALAPPDATA%\\DeepotusVideoGen) vers CE dépôt.

Contexte : entre le 2026-07-02 et le 2026-08-03, ~1 mois de travail a été fait
directement dans l'arbre de l'app (chaîne patch_bundle_*, services backend,
modules frontend v2) sans commits — le dépôt était resté sur v1.15.8. Ce script
fait converger le dépôt sur l'état réel de l'app, en une passe rejouable.

Règles :
  - Synchronise (copie app → dépôt, écrasement) : backend/, frontend/,
    scripts/, docs/, assets/, et les fichiers racine .gitignore, CHANGELOG.md,
    DESIGN.md, LICENSE, PRODUCT.md, README.md.
  - Exclut : bin/, runtime/ (payload installeur), unins*, __pycache__,
    *.pyc, .env (secrets — jamais dans l'app backend de toute façon),
    frontend/dist/assets/*.bak_* (backups de la chaîne de patch),
    .claude/ (config d'environnement locale).
  - Garde la version CANONIQUE du dépôt pour
    frontend/dist/shared/deepotus.tokens.css (source design verbatim) et la
    recopie vers l'app pour faire converger les deux arbres.
  - Purement additif+écrasement : ne supprime jamais un fichier du dépôt.

Usage :  python scripts/repatriate_from_app.py [--dry-run]
"""
from __future__ import annotations

import os
import shutil
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(os.environ.get("LOCALAPPDATA", ""), "DeepotusVideoGen")

SYNC_DIRS = ["backend", "frontend", "scripts", "docs", "assets"]
SYNC_ROOT_FILES = [".gitignore", "CHANGELOG.md", "DESIGN.md", "LICENSE",
                   "PRODUCT.md", "README.md"]
KEEP_REPO = {os.path.join("frontend", "dist", "shared", "deepotus.tokens.css")}


def excluded(rel: str, name: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    if "__pycache__" in parts or name.endswith(".pyc"):
        return True
    if name == ".env":
        return True
    if ".bak_" in name or name.endswith(".bak"):
        return True
    return False


def same(a: str, b: str) -> bool:
    try:
        if os.path.getsize(a) != os.path.getsize(b):
            return False
        with open(a, "rb") as fa, open(b, "rb") as fb:
            while True:
                ca, cb = fa.read(1 << 16), fb.read(1 << 16)
                if ca != cb:
                    return False
                if not ca:
                    return True
    except OSError:
        return False


def main() -> None:
    dry = "--dry-run" in sys.argv
    if not os.path.isdir(APP):
        sys.exit(f"arbre app introuvable : {APP}")
    copied, kept, skipped = [], [], 0

    jobs: list[tuple[str, str, str]] = []  # (src, dst, rel)
    for d in SYNC_DIRS:
        base = os.path.join(APP, d)
        if not os.path.isdir(base):
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [x for x in dirs if x != "__pycache__"]
            for name in files:
                src = os.path.join(root, name)
                rel = os.path.join(d, os.path.relpath(src, base))
                if excluded(rel, name):
                    skipped += 1
                    continue
                jobs.append((src, os.path.join(REPO, rel), rel))
    for name in SYNC_ROOT_FILES:
        src = os.path.join(APP, name)
        if os.path.isfile(src):
            jobs.append((src, os.path.join(REPO, name), name))

    for src, dst, rel in jobs:
        if rel.replace("/", os.sep) in KEEP_REPO:
            kept.append(rel)
            continue
        if os.path.isfile(dst) and same(src, dst):
            continue
        if not dry:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
        copied.append(rel)

    # convergence inverse : tokens canoniques du dépôt → app
    for rel in KEEP_REPO:
        src = os.path.join(REPO, rel)
        dst = os.path.join(APP, rel)
        if os.path.isfile(src) and not same(src, dst):
            if not dry:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
            copied.append(f"(app←repo) {rel}")

    tag = "DRY-RUN " if dry else ""
    print(f"{tag}rapatriement : {len(copied)} fichiers copiés, "
          f"{len(kept)} canoniques gardés, {skipped} exclus")
    for c in copied:
        print("  " + c)


if __name__ == "__main__":
    main()
