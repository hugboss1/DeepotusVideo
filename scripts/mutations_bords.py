"""Mutations du banc test_charte_bords (t374) : chaque mutant DOIT rougir le banc.

Les mutants visent surtout les GÉNÉRATEURS (scripts/charte_bords.py, scripts/charte_aplatir_rayons.py) : la feuille
dz-bords.css étant comparée à la sortie du générateur, un générateur fautif doit être pris par les contrôles de sens
(ronds gardés, sérialisation, imports suivis, finitions), pas seulement par « feuille périmée ».
Restauration sûre : les octets de chaque fichier touché sont copiés AVANT, réécrits APRÈS, puis comparés.
Ne pas lancer en même temps que d'autres bancs (les fichiers sont réécrits le temps d'un mutant).
Run (depuis la racine) : & $PY scripts/mutations_bords.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
F = RACINE / "frontend"
S = RACINE / "scripts"
BANC = RACINE / "backend" / "tests" / "test_charte_bords.py"

# (nom, fichier, avant, après) — `avant` doit être présent une seule fois.
MUTANTS = [
    ("coque sans le lien dz-bords", F / "dist/index.html", '<link rel="stylesheet" href="/shared/dz-bords.css">', ""),
    ("dz-bords liée AVANT dz-charte", F / "dist/index.html",
     '<link rel="stylesheet" href="/shared/dz-charte.css">',
     '<link rel="stylesheet" href="/shared/dz-bords.css"><link rel="stylesheet" href="/shared/dz-charte.css">'),
    ("feuille : une règle retirée à la main", F / "shared/dz-bords.css",
     ".svm-clip{border-radius:var(--radius)!important}\r\n", ""),
    ("générateur : un disque carré n'est plus reconnu", S / "charte_bords.py",
     "abs(w - h) < 0.01 and float(m.group(1)) * 2 >= w - 0.01)", "False)"),
    ("générateur : « :focus-visible » générique gardé", S / "charte_bords.py",
     'if sel.endswith(" :focus-visible"):', 'if sel.endswith(" :focus-visible-x"):'),
    ("générateur : le code JS n'est plus coupé", S / "charte_bords.py",
     'return sel if sel[:1] in (".", "#", "[", ":", "*") else ""', "return brut.strip()"),
    ("générateur : nombre nu sans px", S / "charte_bords.py",
     'else p + "px" for p in val.split())', "else p for p in val.split())"),
    ("générateur : imports non suivis", S / "charte_bords.py",
     "a_lire += re.findall(", "_x = re.findall("),
    ("finition : sélecteur de modèle sur deux lignes", S / "charte_bords.py",
     "min-width:0;white-space:nowrap;overflow:hidden;", "min-width:0;overflow:hidden;"),
    ("finition : coin d'ascenseur blanc", S / "charte_bords.py",
     "::-webkit-scrollbar-corner{background:transparent}", "::-webkit-scrollbar-corner{}"),
    ("finition : gris Tailwind 400 hors charte", S / "charte_bords.py",
     ".text-slate-400,.text-slate-500{color:var(--fg-3)}", ".text-slate-500{color:var(--fg-3)}"),
    ("finition : texte blanc repeint", S / "charte_bords.py",
     ".text-slate-100{color:var(--fg-1)}", ".text-white,.text-slate-100{color:var(--fg-1)}"),
    ("labs : un disque carré aplati en carré", S / "charte_aplatir_rayons.py",
     "if w and h and abs(w - h) < 0.01 and float(m.group(1)) * 2 >= w - 0.01:", "if False:"),
    ("labs : scripts figés de « Demander » plus exclus", S / "charte_aplatir_rayons.py",
     'FIGES = ("dz-agent.js", "dz-agent-pointeur.js")', 'FIGES = ("dz-agent-pointeur.js",)'),
    ("labs : un rayon littéral revient (Photolab)", F / "photolab/photolab.css",
     "@import url(\"/shared/deepotus.tokens.css\");", "@import url(\"/shared/deepotus.tokens.css\");\n.dz-mut{border-radius:3px}"),
    ("Vectorlab : texte rendu aux gris maison", F / "vectorlab/vectorlab.css",
     "--aff-texte: var(--fg-2); --aff-muet: var(--fg-3);", ""),
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
