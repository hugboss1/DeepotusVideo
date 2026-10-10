# -*- coding: utf-8 -*-
"""Valide un fichier de groupe du lexique : python docs/guide/src/lexique/valider.py <groupe>.json <familles...>"""
import json, pathlib, re, sys
sys.stdout.reconfigure(encoding="utf-8")
ici = pathlib.Path(__file__).resolve().parent
racine = ici.parents[3]
lex = json.loads((racine / "docs/icones/suite-finale/lexique.json").read_text("utf-8"))
f, familles = sys.argv[1], sys.argv[2:]
attendu = sorted(e["cle"] for e in lex if e["famille"] in familles)
d = json.loads((ici / f).read_text("utf-8"))
err = []
if sorted(d) != attendu:
    err.append(f"clés manquantes {sorted(set(attendu) - set(d))[:10]} / en trop {sorted(set(d) - set(attendu))[:10]}")
GLYPHE = re.compile("[\U0001F000-\U0001FAFF←-⇿⌀-➿■-◿️]")
for k, v in d.items():
    for champ in ("nom", "fonction"):
        for l in ("fr", "en"):
            t = (v.get(champ) or {}).get(l, "")
            if not t.strip():
                err.append(f"{k}.{champ}.{l} vide")
            elif GLYPHE.search(t):
                err.append(f"{k}.{champ}.{l} contient un glyphe")
    if len(v["nom"]["fr"].split()) > 4 or len(v["nom"]["en"].split()) > 4:
        err.append(f"{k}.nom trop long")
    for l in ("fr", "en"):
        if len(v["fonction"][l].split()) > 14:
            err.append(f"{k}.fonction.{l} : {len(v['fonction'][l].split())} mots (> 14)")
print("OK" if not err else "\n".join(err[:40]), f"({len(d)}/{len(attendu)})")
sys.exit(1 if err else 0)
