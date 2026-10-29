"""Angles vifs dans les feuilles des labs (t374, 29/10/2026, lot A « Finitions esthétiques »).

Réécrit, dans les feuilles CSS d'une zone de `charte_releve` (labs et /shared), chaque `border-radius` (et rayon de
coin) LITTÉRAL > 0 en `var(--r)` — qui vaut 0 depuis t370 (`--r` → `var(--radius)`). Un rayon reste rond quand il
l'est par nature :
  - les exceptions du cliquet (`50%`, `99px`, ≥ 100 px, `var(--r-pill)`) ne sont jamais touchées ;
  - un rayon qui fait d'une boîte carrée un disque (même règle : `width` = `height` en px et rayon ≥ moitié) devient
    `50%`, l'écriture assumée d'un rond (pastille, poignée, point de couleur).
Les rayons multiples (`8px 8px 0 0`) passent aussi à `var(--r)` : tous leurs coins valent 0 désormais.
Les chaînes CSS injectées par les modules JS de /shared (styles posés en ligne) sont traitées de la même façon.
Les feuilles de la COQUE ne sont pas réécrites (bancs figés du Montage) : `scripts/charte_bords.py` les couvre.

Usage : python scripts/charte_aplatir_rayons.py [--check] [zone ...]   (sans zone : toutes les zones de labs)
`--check` n'écrit rien et sort en 1 s'il reste un rayon à aplatir.
Aucune dépendance hors bibliothèque standard (python embarqué).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import charte_releve  # noqa: E402

_RAYON = re.compile(r"(?<![\w-])(border(?:-(?:top|bottom)-(?:left|right))?-radius)(\s*:\s*)([^;}{\"'`\n]+?)(\s*(?:!important)?\s*)(?=[;}\"'`\n])")
_PX = re.compile(r"^\s*([\d.]+)px\s*$")


def _dim(regle: str, prop: str) -> float | None:
    m = re.search(r"(?<![\w-])" + prop + r"\s*:\s*([\d.]+)px", regle)
    return float(m.group(1)) if m else None


def _regle_autour(texte: str, i: int) -> str:
    """Le corps `{…}` qui contient la position i (sans imbrication : une règle CSS)."""
    a = texte.rfind("{", 0, i)
    z = texte.find("}", i)
    return texte[a + 1:z] if a >= 0 and z >= 0 else ""


def remplacer(val: str, regle: str) -> str | None:
    """La nouvelle valeur, ou None si le rayon ne compte pas (nul, déjà branché, rond assumé)."""
    v = charte_releve._normal(val)
    if not charte_releve.rayon_compte(v):
        return None
    m = _PX.match(v)
    if m:
        w, h = _dim(regle, "width"), _dim(regle, "height")
        if w and h and abs(w - h) < 0.01 and float(m.group(1)) * 2 >= w - 0.01:
            return "50%"
    return "var(--r)"


def aplatir(texte: str) -> tuple[str, int]:
    n = 0
    morceaux, fin = [], 0
    for m in _RAYON.finditer(texte):
        neuf = remplacer(m.group(3), _regle_autour(texte, m.start()))
        if neuf is None:
            continue
        morceaux.append(texte[fin:m.start(3)] + neuf)
        fin = m.end(3)
        n += 1
    morceaux.append(texte[fin:])
    return "".join(morceaux), n


# Scripts de /shared FIGÉS par un banc (test_tutoriels_ecran P3 : « Demander » non modifié depuis t317) : leur CSS
# injecté dans la coque est aplati par dz-bords.css (scripts/charte_bords.py lit les scripts /shared de la page).
FIGES = ("dz-agent.js", "dz-agent-pointeur.js")


def fichiers(zones: list[str]) -> list[Path]:
    res = []
    for z in zones:
        for p in charte_releve.fichiers_zone(z):
            if p.name in FIGES:
                continue
            # les .js générés des labs (L8/L9) se régénèrent : seuls les modules de /shared sont réécrits ici
            if p.suffix == ".css" or (z == "shared" and p.suffix == ".js"):
                res.append(p)
    return res


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check = "--check" in sys.argv
    zones = args or list(charte_releve.LABS)
    total = 0
    for p in fichiers(zones):
        b = p.read_bytes()                          # en octets : les fins de ligne restent celles du fichier
        texte = b.decode("utf-8")
        neuf, n = aplatir(texte)
        if not n:
            continue
        total += n
        print(f"{p.relative_to(charte_releve.RACINE).as_posix()} : {n}")
        if not check:
            p.write_bytes(neuf.encode("utf-8"))
    print(f"{'à aplatir' if check else 'aplatis'} : {total}")
    if check and total:
        sys.exit(1)


if __name__ == "__main__":
    main()
