# -*- coding: utf-8 -*-
"""Récupération de l'overlay MSIX (incident 14/06 → 20/07/2026).

À exécuter HORS conteneur (via dz_recover_overlay.cmd lancé par explorer.exe
ou une tâche planifiée) — un shell de session Claude verrait l'overlay au lieu
des vrais fichiers et l'opération serait un non-sens.

Étapes :
  0. Pré-vols : API joignable, aucun job actif.
  1. Stop du backend (scripts\\stop.ps1) + attente libération du port.
  2. Backups : vraie DB + DB overlay copiées dans le DATA_ROOT réel.
  3. Déploiement backend : fs_guard.py / main.py / routes.py repo → app.
  4. Copie union des assets overlay → réel (jamais d'écrasement).
  5. Merge DB sélectif : jobs overlay-only créés APRÈS le fork (14/06 19:18:29)
     et dont les fichiers existent après la copie. Les jobs d'avant le fork
     absents du réel ont été SUPPRIMÉS volontairement côté réel → ignorés.
  6. Relance via launch-silent.vbs (hors conteneur ici) + vérification
     /api/health (fs_virtualized attendu False) + présence des jobs restaurés.

Rapport : %USERPROFILE%\\dz_recovery_report.txt. L'overlay n'est PAS purgé
(décision utilisateur ultérieure).
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

LOCAL = Path(os.environ["LOCALAPPDATA"])
REAL = LOCAL / "DeepotusVideoGenData"
OVERLAY = (LOCAL / "Packages" / "Claude_pzs8sxrjxfjjc" / "LocalCache" /
           "Local" / "DeepotusVideoGenData")
APP = LOCAL / "DeepotusVideoGen"
REPO = Path(r"C:\Users\olivi\DeepotusVideo")
REPORT = Path(os.environ["USERPROFILE"]) / "dz_recovery_report.txt"
API = "http://127.0.0.1:8765/api"
FORK_CUTOFF = "2026-06-14 19:18:29"
STAMP = datetime.now().strftime("%Y%m%d_%H%M")

L: list[str] = []


def log(msg: str) -> None:
    print(msg, flush=True)
    L.append(msg)


def flush_report() -> None:
    REPORT.write_text("\n".join(L), encoding="utf-8")


def api_get(path: str, timeout: float = 10):
    with urllib.request.urlopen(API + path, timeout=timeout) as f:
        return json.load(f)


def fail(msg: str) -> None:
    log(f"ABORT: {msg}")
    flush_report()
    sys.exit(1)


log(f"RECOVERY_START {datetime.now():%Y-%m-%d %H:%M:%S} pid={os.getpid()}")

# --- Étape 0 : pré-vols -----------------------------------------------------
if not OVERLAY.exists():
    fail("overlay introuvable")
try:
    jobs = api_get("/jobs?limit=2000")
    if isinstance(jobs, dict):
        jobs = jobs.get("jobs") or []
    active = [j for j in jobs if j.get("status") not in ("done", "failed")]
    if active:
        fail(f"{len(active)} job(s) actif(s) — réessayer plus tard")
    log(f"pré-vol OK: API up, {len(jobs)} jobs, 0 actif")
except Exception as e:  # noqa: BLE001
    log(f"pré-vol: API injoignable ({e}) — backend déjà arrêté ?")

# --- Étape 1 : stop backend -------------------------------------------------
subprocess.run(
    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
     "-File", str(APP / "scripts" / "stop.ps1")],
    capture_output=True, text=True, timeout=60)
for _ in range(20):
    try:
        api_get("/health", timeout=1)
        time.sleep(0.5)
    except Exception:  # noqa: BLE001
        break
log("backend arrêté")

# --- Étape 2 : backups ------------------------------------------------------
bk_real = REAL / f"deepotus.db.backup_desandbox_{STAMP}"
bk_ovl = REAL / f"deepotus.db.overlay_{STAMP}"
shutil.copy2(REAL / "deepotus.db", bk_real)
shutil.copy2(OVERLAY / "deepotus.db", bk_ovl)
log(f"backups: {bk_real.name} ({bk_real.stat().st_size} o), "
    f"{bk_ovl.name} ({bk_ovl.stat().st_size} o)")

# --- Étape 3 : déploiement backend (repo → app) -----------------------------
deployed = []
for rel in (r"backend\app\services\fs_guard.py",
            r"backend\app\main.py",
            r"backend\app\api\routes.py"):
    src, dst = REPO / rel, APP / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    deployed.append(f"{rel} ({src.stat().st_size} o)")
log("déployé: " + "; ".join(deployed))

# --- Étape 4 : copie union assets overlay → réel ----------------------------
copied, skipped, copied_mb = [], 0, 0.0
for src in (OVERLAY / "assets").rglob("*"):
    if not src.is_file():
        continue
    rel = src.relative_to(OVERLAY)
    dst = REAL / rel
    if dst.exists():
        skipped += 1
        continue
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    copied.append(str(rel))
    copied_mb += src.stat().st_size / 1e6
log(f"copie union: {len(copied)} fichiers copiés ({copied_mb:.0f} Mo), "
    f"{skipped} déjà présents (conservés côté réel)")

# --- Étape 5 : merge DB sélectif -------------------------------------------
ro = sqlite3.connect(f"file:{OVERLAY / 'deepotus.db'}?mode=ro", uri=True)
ro.row_factory = sqlite3.Row
rw = sqlite3.connect(REAL / "deepotus.db")
rw.row_factory = sqlite3.Row

ov_cols = [r[1] for r in ro.execute("PRAGMA table_info(jobs)")]
real_cols = [r[1] for r in rw.execute("PRAGMA table_info(jobs)")]
common = [c for c in ov_cols if c in real_cols]
real_ids = {r[0] for r in rw.execute("SELECT id FROM jobs")}

restored, skipped_prefork, skipped_nofile = [], [], []
for row in ro.execute("SELECT * FROM jobs ORDER BY created_at"):
    j = dict(row)
    if j["id"] in real_ids:
        continue
    if (j.get("created_at") or "") <= FORK_CUTOFF:
        skipped_prefork.append(f"{j['created_at'][:19]} {j.get('title') or j['id']}")
        continue
    prov, short = j.get("provider") or "", j["id"][:8]
    if prov == "sprite2d":
        ok = (REAL / "assets" / "outputs" / "sprites" / short).is_dir()
    elif prov == "asset3d":
        ok = (REAL / "assets" / "outputs" / "assets3d" / short).is_dir()
    else:
        ok = any(j.get(k) and Path(j[k]).exists()
                 for k in ("final_video_path", "video_path"))
    if not ok:
        skipped_nofile.append(f"{j['created_at'][:19]} {prov} "
                              f"{j.get('title') or j['id']}")
        continue
    cols = [c for c in common if j.get(c) is not None]
    rw.execute(
        f"INSERT OR IGNORE INTO jobs ({','.join(cols)}) "
        f"VALUES ({','.join('?' * len(cols))})",
        [j[c] for c in cols])
    restored.append(f"{j['created_at'][:19]} {prov:<9} "
                    f"{(j.get('title') or j['id'])[:52]}")
rw.commit()
log(f"merge jobs: {len(restored)} restaurés, "
    f"{len(skipped_prefork)} pré-fork ignorés (supprimés côté réel), "
    f"{len(skipped_nofile)} sans fichiers ignorés")
for r in restored:
    log(f"  + {r}")
for r in skipped_nofile:
    log(f"  ~ sans fichier: {r}")

# scheduled_posts : vérification de couverture (aucune écriture)
ov_posts = {r[0] for r in ro.execute("SELECT id FROM scheduled_posts")}
real_posts = {r[0] for r in rw.execute("SELECT id FROM scheduled_posts")}
only = ov_posts - real_posts
log(f"scheduler: {len(ov_posts)} posts overlay, {len(real_posts)} réels, "
    f"overlay-only = {len(only)}" + (f" {sorted(only)}" if only else ""))
ro.close()
rw.close()

# --- Étape 6 : relance + vérification --------------------------------------
subprocess.Popen(["wscript.exe", str(APP / "scripts" / "launch-silent.vbs")])
health = None
for _ in range(90):
    time.sleep(1)
    try:
        health = api_get("/health", timeout=2)
        break
    except Exception:  # noqa: BLE001
        continue
if not health:
    fail("backend ne répond pas après relance")
log(f"relance OK — version {health.get('version')}, "
    f"fs_virtualized={health.get('fs_virtualized')}")
imgs = api_get("/images")
log(f"vérif: /api/images -> {len(imgs.get('images') or [])} images")
jobs2 = api_get("/jobs?limit=2000")
if isinstance(jobs2, dict):
    jobs2 = jobs2.get("jobs") or []
ids2 = {j.get("job_id") or j.get("id") for j in jobs2}
missing = [r for r in restored if r.split()[-1] not in
           {(j.get("title") or "")[:52] for j in jobs2}] if restored else []
log(f"vérif: /api/jobs -> {len(ids2)} jobs "
    f"(92b74f61 présent: {any(str(i).startswith('92b74f61') for i in ids2)})")
log(f"RECOVERY_END {datetime.now():%Y-%m-%d %H:%M:%S}")
flush_report()
