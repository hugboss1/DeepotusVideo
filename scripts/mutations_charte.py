"""Mutations du banc test_charte_jetons (t370) : chaque mutant DOIT rougir le banc.

Restauration sûre : les octets de chaque fichier touché sont copiés AVANT, réécrits APRÈS, puis comparés.
Run (depuis la racine) : & $PY scripts/mutations_charte.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
F = RACINE / "frontend"
BANC = RACINE / "backend" / "tests" / "test_charte_jetons.py"

# (nom, fichier, avant, après) — `avant` doit être présent une seule fois.
MUTANTS = [
    ("coque sans le lien", F / "dist/index.html", '<link rel="stylesheet" href="/shared/dz-charte.css">', ""),
    ("coque : lien AVANT la feuille du bundle", F / "dist/index.html",
     '<link rel="stylesheet" crossorigin href="/assets/index-CBtHJYWz.css">',
     '<link rel="stylesheet" href="/shared/dz-charte.css"><link rel="stylesheet" crossorigin href="/assets/index-CBtHJYWz.css">'),
    ("tokens partagés sans @import", F / "shared/deepotus.tokens.css", '@import url("/shared/dz-charte.css");', ""),
    ("spritelab : @import après une règle (ignoré)", F / "spritelab/spritelab.css",
     '@import url("/shared/dz-charte.css");', '.x{}@import url("/shared/dz-charte.css");'),
    ("photolab sans les tokens", F / "photolab/photolab.css", '@import url("/shared/deepotus.tokens.css");', ""),
    ("--radius à 2px", F / "shared/dz-charte.css", "--radius:0;", "--radius:2px;"),
    ("--r rendu à 10px", F / "shared/dz-charte.css", "--r:var(--radius);", "--r:10px;"),
    ("--fg-2 retiré", F / "shared/dz-charte.css", "--fg-2:var(--ink,#c4bfb6);", ""),
    ("--fg-1 en hexadécimal", F / "shared/dz-charte.css", "--fg-1:var(--ink-strong,#f2efe9);", "--fg-1:#f2efe9;"),
    ("règle d'élément dans la charte", F / "shared/dz-charte.css", "--pad-1:4px;", "--pad-1:4px;}body{color:red;"),
    ("tokens : --r-lg rendu à 14px", F / "shared/deepotus.tokens.css",
     "--r-lg:var(--radius); /* t370", "--r-lg:14px; /* t370"),
    ("tokens : fil de défilement arrondi", F / "shared/deepotus.tokens.css",
     "background-clip:content-box;border-radius:var(--radius)}", "background-clip:content-box;border-radius:99px}"),
    ("atelier : --r-sm rendu à 6px", F / "atelier/atelier.css", "--r-sm:var(--radius);", "--r-sm:6px;"),
    ("cliquet : un rayon de plus dans whatsapp", F / "whatsapp/whatsapp.css",
     "html, body { height: 100%;", ".dz-mut{border-radius:6px}\nhtml, body { height: 100%;"),
]


def banc() -> int:
    return subprocess.run([sys.executable, str(BANC)], cwd=RACINE / "backend",
                          capture_output=True, text=True, encoding="utf-8", errors="replace").returncode


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if banc() != 0:
        print("le banc est ROUGE avant toute mutation : arrêt")
        return 2
    tues = 0
    for nom, fic, avant, apres in MUTANTS:
        # Une feuille de /shared est mutée AVEC sa copie servie : sinon seul le contrôle d'identité rougirait.
        copie = F / "dist" / fic.relative_to(F) if fic.is_relative_to(F / "shared") else None
        cibles = [fic] + ([copie] if copie and copie.is_file() else [])
        sauve = {c: c.read_bytes() for c in cibles}
        texte = sauve[fic].decode("utf-8")
        if texte.count(avant) != 1:
            print(f"  ANCRE  {nom} : {texte.count(avant)} occurrence(s) dans {fic.name}")
            continue
        try:
            for c in cibles:
                c.write_bytes(texte.replace(avant, apres).encode("utf-8"))
            rc = banc()
        finally:
            for c, o in sauve.items():
                c.write_bytes(o)
        assert all(c.read_bytes() == o for c, o in sauve.items()), f"restauration ratée : {cibles}"
        tue = rc != 0
        tues += tue
        print(f"  {'TUÉ ' if tue else 'VIT '}  {nom}")
    print(f"\n{tues}/{len(MUTANTS)} mutants tués")
    return 0 if tues == len(MUTANTS) else 1


if __name__ == "__main__":
    sys.exit(main())
