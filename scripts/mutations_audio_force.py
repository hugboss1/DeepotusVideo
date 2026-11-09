# -*- coding: utf-8 -*-
"""Mutations t483 (F6.6, 09/11/2026) : piste son imposée retirée (`audio_force`, `couper_piste_imposee`, pipeline,
bloc Membres, fiches). Chaque mutation doit faire ÉCHOUER backend/tests/test_audio_force.py ou
backend/tests/test_modeles_fiches.py. Sources copiées AVANT, restaurées après chaque mutation, comparées à la fin.
Run (depuis la racine) : & $PY scripts/mutations_audio_force.py"""
import filecmp, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[1]
SAUVE = pathlib.Path(tempfile.mkdtemp(prefix="mut_audio_force_"))
F = {"fal": RACINE / "backend/app/services/fal_service.py", "pipe": RACINE / "backend/app/services/pipeline.py",
     "mf": RACINE / "backend/app/services/modeles_fiches.py", "gfr": RACINE / "docs/agent/modeles/fr/gemini-omni.md",
     "ken": RACINE / "docs/agent/modeles/en/kling.md"}
for k, p in F.items():
    shutil.copy2(p, SAUVE / (k + ".orig"))
BANCS = [[sys.executable, "backend/tests/test_audio_force.py"], [sys.executable, "backend/tests/test_modeles_fiches.py"]]
M = [
 ("fal", '"resolution_maj": True, "end_image": True, "seed": True,\n        "audio_param": None, "audio_force": True,',
  '"resolution_maj": True, "end_image": True, "seed": True,\n        "audio_param": None,'),
 ("fal", "    if not (model or {}).get(\"audio_force\"):\n        return False", "    if False:\n        return False"),
 ("fal", "        if not _F.a_une_piste_audio(path):\n            return False", "        if False:\n            return False"),
 ("fal", '"-map", "0:v", "-an", "-c:v", "copy",', '"-map", "0:v", "-an", "-c:v", "libx264",'),
 ("fal", "        muet.replace(path)", "        pass"),
 ("fal", "    except Exception as e:  # noqa: BLE001 — la piste reste, le clip est gardé", "    except ZeroDivisionError as e:  # noqa: BLE001 — la piste reste, le clip est gardé"),
 ("pipe", "await asyncio.to_thread(couper_piste_imposee, model, video_dest)", "pass"),
 ("pipe", "await asyncio.to_thread(couper_piste_imposee, model, dest)", "pass"),
 ("mf", 'son_retire=bool(r.get("audio_force")))', 'son_retire=False)'),
 ("mf", 'else ("removed" if en else "retiré") if m.get("son_retire")', 'else ("removed" if en else "sans interrupteur") if m.get("son_retire")'),
 ("gfr", "L'app la retire au téléchargement", "Prévoir de la remplacer au montage"),
 ("ken", "the app removes the track they deliver on download", "the clip may arrive with a generated track"),
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
