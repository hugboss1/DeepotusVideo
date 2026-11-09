# -*- coding: utf-8 -*-
"""Mutations t482 (F6.5, 09/11/2026) : Seedance 2.5 en 1080p, membre à part (`seedance-2.5-1080p`). Chaque mutation doit
faire ÉCHOUER backend/tests/test_video_models.py ou backend/tests/test_modeles_fiches.py. Sources copiées AVANT,
restaurées après chaque mutation, comparées octet à octet à la fin.
Run (depuis la racine) : & $PY scripts/mutations_seedance_1080p.py"""
import filecmp, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[1]
SAUVE = pathlib.Path(tempfile.mkdtemp(prefix="mut_s25_1080_"))
F = {"fal": RACINE / "backend/app/services/fal_service.py", "prix": RACINE / "backend/app/services/pricing.py",
     "ffr": RACINE / "docs/agent/modeles/fr/seedance.md", "fen": RACINE / "docs/agent/modeles/en/seedance.md"}
for k, p in F.items():
    shutil.copy2(p, SAUVE / (k + ".orig"))
BANCS = [[sys.executable, "backend/tests/test_video_models.py"], [sys.executable, "backend/tests/test_modeles_fiches.py"]]
M = [
 ("prix", '"seedance-2.5-1080p":  {"1080p": 1.164},', '"seedance-2.5-1080p":  {"1080p": 0.473},'),
 ("prix", '"seedance-2.5-1080p":  {"1080p": 1.164},', ''),
 ("fal", '"resolutions": ["1080p"], "end_image": True, "seed": False,', '"resolutions": ["720p", "1080p"], "end_image": True, "seed": False,'),
 ("fal", '"resolutions": ["480p", "720p"], "end_image": True, "seed": False,', '"resolutions": ["480p", "720p", "1080p"], "end_image": True, "seed": False,'),
 ("fal", '"label": "Seedance 2.5 (1080p)", "provider": "fal", "family": "seedance25",', '"label": "Seedance 2.5 (1080p)", "provider": "fal", "family": "seedance2",'),
 ("fal", '"label": "Seedance 2.5 (1080p)", "provider": "fal", "family": "seedance25",\n        "endpoint": "bytedance/seedance-2.5/image-to-video",',
  '"label": "Seedance 2.5 (1080p)", "provider": "fal", "family": "seedance25",\n        "endpoint": "bytedance/seedance-2.0/image-to-video",'),
 ("ffr", "seedance-2.5, seedance-2.5-1080p]", "seedance-2.5]"),
 ("fen", "seedance-2.5, seedance-2.5-1080p]", "seedance-2.5]"),
]
tues = 0
try:
    for i, (k, a, b) in enumerate(M, 1):
        p = F[k]; s = p.read_bytes().decode("utf-8")
        a2, b2 = (a.replace("\n", "\r\n"), b.replace("\n", "\r\n")) if "\r\n" in s and a not in s else (a, b)
        assert s.count(a2) >= 1, (i, k, a)
        p.write_bytes(s.replace(a2, b2, 1).encode("utf-8"))
        rouge = False
        for banc in BANCS:
            r = subprocess.run(banc, cwd=RACINE, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               env={**os.environ, "PYTHONUTF8": "1"})
            if r.returncode != 0:
                rouge = True
                break
        shutil.copy2(SAUVE / (k + ".orig"), p)
        tues += rouge
        print(("TUÉE   " if rouge else "SURVIT ") + f"M{i} {k}: {a.strip()[:64]!r}")
finally:
    for k, p in F.items():
        shutil.copy2(SAUVE / (k + ".orig"), p)
    print("restauré, identique :", all(filecmp.cmp(SAUVE / (k + ".orig"), p, shallow=False) for k, p in F.items()))
print(f"{tues}/{len(M)} mutations tuées")
sys.exit(0 if tues == len(M) else 1)
