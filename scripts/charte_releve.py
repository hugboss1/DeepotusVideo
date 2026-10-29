"""Relevé de la charte visuelle (t370, 29/10/2026).

Parcourt la coque (bundle prébâti `frontend/dist` + feuilles servies à côté) et chaque lab autonome
(`frontend/<lab>`) et compte les valeurs réellement écrites pour : couleur de texte, police, taille,
graisse, `border-radius` et espacements (padding / gap). Sert deux fois :

- `python scripts/charte_releve.py --md <fichier>` écrit les tableaux du relevé (spec t370) ;
- le banc `backend/tests/test_charte_jetons.py` importe `rayons_par_zone()` pour le CLIQUET des
  `border-radius` : le nombre de rayons littéraux > 0 (hors exceptions rondes) d'une zone ne peut
  que baisser — t374 l'amènera à 0, écran par écran.

Aucune dépendance hors bibliothèque standard (python embarqué).
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
FRONT = RACINE / "frontend"

# Labs autonomes, servis dans un cadre de la coque. `shared` = scripts et feuilles de /shared.
LABS = ("atelier", "avatar", "cardforge", "etabli", "lib3d", "materialforge", "meshy", "photolab",
        "plateau", "spritelab", "studio3d", "tilelab", "vectorlab", "whatsapp", "shared")

# Code tiers ou généré qui n'est pas « notre » charte.
_EXCLUS = re.compile(r"(/qa/|/vendor/|/node_modules/|\.min\.|/three|dz-i18n-dico\.js$|dz-icons\.js$)")


def fichiers_zone(zone: str) -> list[Path]:
    if zone == "coque":
        dist = FRONT / "dist"
        res = sorted((dist / "assets").glob("index-*.css")) + sorted((dist / "assets").glob("index-*.js"))
        res += [dist / "theme-v2.css", dist / "index.html"]
        res += sorted(p for p in (dist / "shared").glob("*.css") if p.name != "dz-charte.css")
        return [p for p in res if p.is_file()]
    base = FRONT / zone
    res = []
    for p in sorted(base.rglob("*")):
        if p.suffix not in (".css", ".js") or not p.is_file():
            continue
        if _EXCLUS.search(p.as_posix()) or p.name == "dz-charte.css":
            continue
        res.append(p)
    return res


# ── extraction ───────────────────────────────────────────────────────────────
# Déclarations CSS (feuilles ET chaînes CSS injectées par les modules JS).
_DECL = re.compile(r"(?<![\w-])(color|font-family|font-size|font-weight|border(?:-(?:top|bottom)-(?:left|right))?-radius"
                   r"|padding(?:-(?:top|right|bottom|left|inline|block))?|gap)\s*:\s*([^;}{\"'`\n]+)")
# Objets de style React (bundle, modules JS) : borderRadius:6, fontSize:"12px"…
_CAMEL = re.compile(r"(?<![\w$-])(color|fontFamily|fontSize|fontWeight|borderRadius|padding|gap):\s*"
                    # nombre nu = px React ; suivi d'une unité ou d'une 2e valeur, c'est du CSS déjà compté
                    r"(\"[^\"]*\"|'[^']*'|[\d.]+(?![\d.]|[a-z%]|\s+[\d.-]|\s*!|\s*;))")
_CAMEL_NOM = {"color": "color", "fontFamily": "font-family", "fontSize": "font-size",
              "fontWeight": "font-weight", "borderRadius": "border-radius", "padding": "padding", "gap": "gap"}
# Classes Tailwind du bundle prébâti.
_TW = re.compile(r"(?<![\w-])(rounded(?:-(?:none|sm|md|lg|xl|2xl|3xl|full|\[[^\]]+\]))?"
                 r"|text-(?:xs|sm|base|lg|xl|2xl|3xl|\[\d+(?:\.\d+)?px\])"
                 r"|text-(?:slate|gray|zinc|neutral|white|ink|cyan|amber)(?:-\d{2,3})?(?:/\d+)?"
                 r"|font-(?:mono|sans|display|medium|semibold|bold|normal|light)"
                 r"|p[xytblr]?-(?:\d+(?:\.5)?|\[[^\]]+\]))(?![\w-])")


def _famille(prop: str) -> str:
    if prop.endswith("radius"):
        return "border-radius"
    if prop.startswith("padding"):
        return "padding"
    return prop


def _normal(val: str) -> str:
    val = re.sub(r"\s+", " ", val.strip().strip("\"'")).rstrip(",")
    return val.replace("!important", "").strip()


def extraire(texte: str) -> dict[str, collections.Counter]:
    out: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for prop, val in _DECL.findall(texte):
        v = _normal(val)
        # `gap:8,` / `padding:4}` d'un objet React : nombre nu, déjà compté par _CAMEL
        if prop in ("padding", "gap", "color") and re.match(r"^[\d.]+(,|$)", v):
            continue
        if v:
            out[_famille(prop)][v] += 1
    for prop, val in _CAMEL.findall(texte):
        v = _normal(val)
        if v:
            out[_CAMEL_NOM[prop]][v] += 1
    for cls in _TW.findall(texte):
        if cls.startswith("rounded"):
            out["tw:rounded"][cls] += 1
        elif cls.startswith("font-") and cls[5:] in ("mono", "sans", "display"):
            out["tw:font"][cls] += 1
        elif cls.startswith("font-"):
            out["tw:weight"][cls] += 1
        elif re.match(r"text-(xs|sm|base|lg|xl|\d?xl|\[)", cls):
            out["tw:size"][cls] += 1
        elif cls.startswith("text-"):
            out["tw:color"][cls] += 1
        else:
            out["tw:padding"][cls] += 1
    return out


def releve_zone(zone: str) -> dict[str, collections.Counter]:
    tot: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for p in fichiers_zone(zone):
        for fam, c in extraire(p.read_text(encoding="utf-8", errors="replace")).items():
            tot[fam].update(c)
    return tot


# ── rayons : ce qui compte pour le cliquet ──────────────────────────────────
# Exceptions LISTÉES et justifiées (spec t370 §Exceptions) : un rond reste rond.
#  - 50 % : pastille d'état, point de couleur, poignée circulaire, avatar ;
#  - 99px et au-delà (« pilule ») : pastilles d'état et compteurs ronds ;
#  - var(--r-pill) / rounded-full : mêmes pastilles côté bundle.
_ROND = re.compile(r"^(50%|99(px)?|\d{3,}(px)?|var\(--r-pill\)|rounded-full)$")
# Valeurs nulles ou déjà branchées sur les jetons de la charte.
_NUL = re.compile(r"^(0|0px|0 0 0 0|none|inherit|initial|unset|var\(--radius\)|rounded-none"
                  r"|var\(--r(-sm|-lg)?\))$")


def rayon_compte(valeur: str) -> bool:
    """Vrai si ce rayon est un littéral > 0 hors exceptions rondes (donc à faire disparaître en t374)."""
    v = valeur.strip()
    if _NUL.match(v) or _ROND.match(v):
        return False
    if re.fullmatch(r"(0(px)?\s*)+", v):
        return False
    return True


def rayons_par_zone() -> dict[str, int]:
    res = {}
    for zone in ("coque",) + LABS:
        r = releve_zone(zone)
        n = sum(c for v, c in r["border-radius"].items() if rayon_compte(v))
        n += sum(c for v, c in r["tw:rounded"].items() if rayon_compte(v))
        res[zone] = n
    return res


# ── rendu du relevé ─────────────────────────────────────────────────────────
_TITRES = [("color", "Couleurs de texte (CSS)"), ("tw:color", "Couleurs de texte (classes Tailwind)"),
           ("font-family", "Polices"), ("tw:font", "Polices (Tailwind)"),
           ("font-size", "Tailles"), ("tw:size", "Tailles (Tailwind)"),
           ("font-weight", "Graisses"), ("tw:weight", "Graisses (Tailwind)"),
           ("border-radius", "Rayons"), ("tw:rounded", "Rayons (Tailwind)"),
           ("padding", "Marges internes (padding)"), ("tw:padding", "Marges internes (Tailwind)"),
           ("gap", "Écarts (gap)")]


def markdown(top: int = 12) -> str:
    lignes = []
    for zone in ("coque",) + LABS:
        r = releve_zone(zone)
        n_fic = len(fichiers_zone(zone))
        lignes.append(f"### {zone} ({n_fic} fichiers)\n")
        lignes.append("| Propriété | distinctes | occurrences | valeurs les plus fréquentes |")
        lignes.append("|---|---:|---:|---|")
        for fam, titre in _TITRES:
            c = r.get(fam)
            if not c:
                continue
            vals = " · ".join(f"`{v[:48]}` ×{n}" for v, n in c.most_common(top))
            lignes.append(f"| {titre} | {len(c)} | {sum(c.values())} | {vals} |")
        lignes.append("")
    return "\n".join(lignes)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", help="écrit les tableaux par zone dans ce fichier")
    ap.add_argument("--rayons", action="store_true", help="affiche le cliquet des rayons (JSON)")
    a = ap.parse_args()
    if a.md:
        Path(a.md).write_text(markdown(), encoding="utf-8")
    if a.rayons or not a.md:
        print(json.dumps(rayons_par_zone(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
