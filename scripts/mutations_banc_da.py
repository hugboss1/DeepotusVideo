# -*- coding: utf-8 -*-
"""Mutations t489 (FDA) : méthode « ancre » de la planche (routes, board_service) et banc scripts/banc_da_coherence.py.
Chaque mutation doit faire ÉCHOUER backend/tests/test_atelier_methode.py ou backend/tests/test_banc_da.py. Sources
copiées AVANT, restaurées après chaque mutation, comparées octet à octet à la fin.
Run (depuis la racine) : & $PY scripts/mutations_banc_da.py"""
import filecmp, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[1]
SAUVE = pathlib.Path(tempfile.mkdtemp(prefix="mut_banc_da_"))
F = {"rt": RACINE / "backend/app/api/routes.py", "bs": RACINE / "backend/app/services/board_service.py",
     "bd": RACINE / "scripts/banc_da_coherence.py"}
for k, p in F.items():
    shutil.copy2(p, SAUVE / (k + ".orig"))
BANCS = [[sys.executable, "backend/tests/test_atelier_methode.py"], [sys.executable, "backend/tests/test_banc_da.py"]]
M = [
 # route
 ("rt", 'methode = str(body.get("methode") or (recipe or {}).get("methode") or "actuel")', 'methode = str(body.get("methode") or "actuel")'),
 ("rt", 'if methode != "actuel" and e.kind != "character":', 'if False:'),
 ("rt", 'if methode == "ancre_multi" and (provider == "flux" or not IP.multi_references(provider)):', 'if False:'),
 ("rt", 'if face_maitre and not (settings.images_path / face_maitre).is_file():', 'if False:'),
 ("rt", '"n": len(plan["panels"]) - (1 if face_maitre else 0)', '"n": len(plan["panels"])'),
 ("rt", '            if face_maitre and key == "face_front":', '            if False:'),
 ("rt", '            if chain_on and methode != "actuel":', '            if False:'),
 ("rt", '                if methode == "ancre_multi" and key in BS.VUES_MULTI:', '                if False:'),
 ("rt", '                if sim is not None and sim < BS.SEUIL_HEROS:', '                if False:'),
 ("rt", '                    if sim2 is not None and sim2 > sim:', '                    if sim2 is not None:'),
 ("rt", '                recipe_panels[-1]["profondeur"] = BS.profondeur(key, methode)', '                pass'),
 ("rt", '            rec["methode"] = methode\n', '            pass\n'),
 ("rt", 'if methode != "actuel" and key == "front" and e.kind == "character" and not seeds_by_key:', 'if key == "front" and e.kind == "character" and not seeds_by_key:'),
 # board_service
 ("bs", '"the accessories, the color palette and the lighting.{st} {_FOND_POSITIF[0].upper()}{_FOND_POSITIF[1:]}."', '"the accessories, the color palette and the lighting.{st} Sharp focus, no text."'),
 ("bs", '        vue = ROLES_MULTI + " " + vue', '        vue = vue'),
 ("bs", '    if methode == "actuel" and cle in ("left", "back"):\n        return 2', '    if False:\n        return 2'),
 ("bs", 'VUES_MULTI = {"left": ("face_front", "front"), "back": ("face_front", "front")}', 'VUES_MULTI = {"left": ("front", "face_front"), "back": ("front", "face_front")}'),
 # banc : règle de décision et vote
 ("bd", 'raisons.append(("M3 +10 % en moyenne", gain >= 0.10,', 'raisons.append(("M3 +10 % en moyenne", gain >= 0.05,'),
 ("bd", 'all(x >= -0.05 for x in pires)', 'True'),
 ("bd", 'part >= 0.60', 'part >= 0.50'),
 ("bd", 'surcout <= 0.20', 'surcout <= 0.40'),
 ("bd", '        if x.get("choix") == "e":\n            continue', '        pass'),
 ("bd", 'neuf_gagne = (x.get("choix") == "g") == bool(x.get("neuf_a_gauche"))', 'neuf_gagne = x.get("choix") == "g"'),
 ("bd", 'g, d = (a, b) if rnd.random() < 0.5 else (b, a)', 'g, d = (b, a)'),
 ("bd", 'jugees = total_planches * max(0, min(juge_reps, REPETITIONS)) // REPETITIONS', 'jugees = total_planches'),
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
