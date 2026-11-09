# -*- coding: utf-8 -*-
"""Mutations t478 (F6.1, 09/11/2026) : palier de qualité de GPT Image et d'Ideogram 4.5 (pricing, image_providers,
route /images/generate, catalogue, pastille de dz-champ-ia). Chaque mutation doit faire ÉCHOUER
backend/tests/test_qualite_image.py. Une mutation de dz-champ-ia.js est recopiée dans dist/shared. Sources copiées
AVANT, restaurées après chaque mutation, comparées octet à octet à la fin.
Run (depuis la racine) : & $PY scripts/mutations_qualite_image.py"""
import filecmp, os, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[1]
SAUVE = pathlib.Path(tempfile.mkdtemp(prefix="mut_qualite_image_"))
F = {"prix": RACINE / "backend/app/services/pricing.py", "ip": RACINE / "backend/app/services/image_providers.py",
     "rt": RACINE / "backend/app/api/routes.py", "cat": RACINE / "backend/app/services/catalogue_ia.py",
     "ci": RACINE / "frontend/shared/dz-champ-ia.js"}
COPIES = {"ci": RACINE / "frontend/dist/shared/dz-champ-ia.js"}
for k, p in F.items():
    shutil.copy2(p, SAUVE / (k + ".orig"))
for k, p in COPIES.items():
    shutil.copy2(p, SAUVE / (k + ".dist"))
BANC = [sys.executable, "backend/tests/test_qualite_image.py"]
M = [
 # registre et devis
 ("prix", '_F_GPT25 = {"low": 0.12,', '_F_GPT25 = {"low": 0.11,'),
 ("prix", '"xhigh": 1.8, "max": 4.0}', '"xhigh": 1.78, "max": 4.0}'),
 ("prix", '_F_GPT2 = {"low": 0.035,', '_F_GPT2 = {"low": 0.03,'),
 ("prix", '"ideogram-4.5": {"low": 0.137,', '"ideogram-4.5": {"low": 0.13,'),
 ("prix", '_F_GPT25_DIRECT = {"low": 0.12, "medium": 0.25, "high": 1.0}', '_F_GPT25_DIRECT = _F_GPT25'),
 ("prix", 'return q if q in table else QUALITE_DEFAUT', 'return q or QUALITE_DEFAUT'),
 ("prix", "        if q and q != QUALITE_DEFAUT:                     # high : ligne inchangée, à l'octet\n            unit = unit * facteur_qualite(model, q)",
  "        if q and q != QUALITE_DEFAUT:                     # high : ligne inchangée, à l'octet\n            unit = unit"),
 ("prix", 'if q and q != QUALITE_DEFAUT:                     # high', 'if q:                     # high'),
 # requêtes
 ("ip", '"quality": qualite or "high",', '"quality": "high",'),
 ("ip", 'if qualite and "quality" in m.get("extra", {}):', 'if qualite:'),
 ("ip", 'payload["quality"] = qualite or "high"', 'payload["quality"] = "high"'),
 ("ip", "    elif qualite:      # t478", "    elif False:      # t478"),
 ("ip", "image_paths=refs, qualite=q,", "image_paths=refs,"),
 ("ip", 'qualite=q or "high")', 'qualite="high")'),
 ("ip", 'q_dir = q if (qualite or provider.startswith("gpt-image-2.5")) else None', "q_dir = q"),
 # route
 ("rt", 'return (await _atelier_setting(_s, "image_qualite:" + model)).strip().lower() or None', "return None"),
 ("rt", 'q = str((body or {}).get("qualite") or "").strip().lower()\n    if q or', 'q = ""\n    if q or'),
 ("rt", '"model": model, "qualite": qualite}, _categorie_image(body))   # tâche #16\n        background', '"model": model}, _categorie_image(body))   # tâche #16\n        background'),
 ("rt", 'payload["quality"] = _PRX.qualite_image(model, qualite)', "pass"),
 ("rt", '"qualite": out.get("qualite"),', ""),
 ("rt", 'res["qualite"] = _PRX.qualite_image(model, qualite)', "pass"),
 ("rt", "if v in e[\"qualites\"]:\n                    choisies[e[\"id\"]] = v", "if v:\n                    choisies[e[\"id\"]] = v"),
 # catalogue
 ("cat", 'out[-1]["qualites"] = {q: round(usd * f, 5) for q, f in facteurs.items()}', "pass"),
 # pastille
 ("ci", '"image_qualite:" + cour', '"image_qualite"'),
 ("ci", 'prixUsd(mq.qualites[q], "image")', "\"\""),
 ("ci", ".dzia-qbtn{padding:2px 7px;font-size:11px;border:1px solid rgba(139,92,246,.45);border-radius:var(--r);",
  ".dzia-qbtn{padding:2px 7px;font-size:11px;border:1px solid rgba(139,92,246,.45);border-radius:4px;"),
 ("copie", "", ""),
 # t479 (F6.2) : réécriture du prompt
 ("ip", '"reecriture": "enable_prompt_expansion"},', '},'),
 ("ip", "if reecriture is not None and m.get(\"reecriture\") and not edit:", "if reecriture is not None and m.get(\"reecriture\"):"),
 ("ip", "args[m[\"reecriture\"]] = bool(reecriture)", "args[m[\"reecriture\"]] = True"),
 ("ip", "                                             reecriture=reecriture)", "                                             )"),
 ("rt", "    if isinstance(v, bool):\n        return v", "    if v is not None:\n        return bool(v)"),
 ("rt", 'return {"0": False, "1": True}.get(r)', "return None"),
 ("rt", "        if reecriture is not None:\n            res[\"reecriture\"] = reecriture", "        pass"),
 ("rt", '"reecriture": out.get("reecriture"),', ""),
 ("rt", 'if v in ("0", "1"):\n                    reecritures[e["id"]] = v == "1"', 'if v:\n                    reecritures[e["id"]] = v == "1"'),
 ("cat", 'out[-1]["reecriture"] = True', "pass"),
 ("ci", "rchoisie: (d.reecritures || {})[e.id] !== false", "rchoisie: !!(d.reecritures || {})[e.id]"),
 ("ci", 'nv ? "1" : "0"', 'nv ? "1" : ""'),
 # t480 (F6.3) : plusieurs références pour GPT Image via fal
 ("ip", "urls = [u for u in urls if u][:REF_MAX_GPT_FAL]\n    if urls:", "urls = [u for u in urls if u][:1]\n    if urls:"),
 ("ip", "REF_MAX_GPT_FAL = 16", "REF_MAX_GPT_FAL = 9"),
 ("ip", "        for ch in chemins[:REF_MAX_GPT_FAL]:", "        for ch in chemins[:1]:"),
 ("ip", "refs_gpt = list(image_paths) if image_paths else image_path", "refs_gpt = image_path"),
 ("ip", "    return (m in (\"nano-banana\", \"nano-banana-pro\") or m in _FAL_GPT", "    return (m in (\"nano-banana\", \"nano-banana-pro\")"),
 ("ip", "or bool((FAL_IMAGES.get(m) or {}).get(\"edit\")))", "or m in FAL_IMAGES)"),
 ("prix", "if refs and model in IMAGE_REF_USD:", "if False:"),
 ("prix", "n * refs * IMAGE_REF_USD[model]))", "refs * IMAGE_REF_USD[model]))"),
 ("prix", '"gpt-image-2.5-sunburst-fal": 0.012}', '"gpt-image-2.5-sunburst-fal": 0.008}'),
 ("rt", '"refs": 1 + len(refs_idv)}', '"refs": len(refs_idv)}'),
 ("rt", "if not IP.multi_references(model):          # t480", "if model not in (\"nano-banana\", \"nano-banana-pro\"):          # t480"),
]
tues = 0
try:
    for i, (k, a, b) in enumerate(M, 1):
        if k == "copie":
            p = F["ci"]
            p.write_bytes(p.read_bytes() + b"\n")                       # la source dérive, la copie servie non
            etiquette = "copie dist/shared en retard"
        else:
            p = F[k]; s = p.read_bytes().decode("utf-8")
            a2, b2 = (a.replace("\n", "\r\n"), b.replace("\n", "\r\n")) if "\r\n" in s and a not in s else (a, b)
            assert s.count(a2) >= 1, (i, k, a)
            p.write_bytes(s.replace(a2, b2, 1).encode("utf-8"))
            if k in COPIES:
                shutil.copy2(p, COPIES[k])
            etiquette = f"{k}: {a.strip()[:64]!r}"
        r = subprocess.run(BANC, cwd=RACINE, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env={**os.environ, "PYTHONUTF8": "1"})
        kk = "ci" if k == "copie" else k
        shutil.copy2(SAUVE / (kk + ".orig"), F[kk])
        if kk in COPIES:
            shutil.copy2(SAUVE / (kk + ".dist"), COPIES[kk])
        ok = r.returncode != 0; tues += ok
        print(("TUÉE   " if ok else "SURVIT ") + f"M{i} {etiquette}")
finally:
    for k, p in F.items():
        shutil.copy2(SAUVE / (k + ".orig"), p)
    for k, p in COPIES.items():
        shutil.copy2(SAUVE / (k + ".dist"), p)
    print("restauré, identique :", all(filecmp.cmp(SAUVE / (k + ".orig"), p, shallow=False) for k, p in F.items())
          and all(filecmp.cmp(SAUVE / (k + ".dist"), p, shallow=False) for k, p in COPIES.items()))
print(f"{tues}/{len(M)} mutations tuées")
sys.exit(0 if tues == len(M) else 1)
