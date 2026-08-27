#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""vitrail_prompt.py - compositeur de prompts Mloda Polska (stdlib pur).

Transforme une demande (sujet + variables) en prompt pret-generateur selon la
grammaire du guide « Mloda Polska » : une famille visuelle dominante, 3-6
codes formels, palette ancree en hex, lumiere explicite, garde-fous
d'originalite. Le prompt sort en anglais ; la pedagogie reste en francais.

Regle dure : AUCUN nom d'artiste du mouvement ne sort dans un prompt.
`garde_noms()` le verifie ; tout compositeur l'appelle avant de rendre.

Usage (CLI)
-----------
  # composer un prompt complet (modele de reponse §11 du guide)
  python vitrail_prompt.py --sujet "une gardienne de phare" --famille vitrail

  # doser l'ornement (1-5), fixer l'usage, meler une 2e famille limitee
  python vitrail_prompt.py --sujet "un verger la nuit" --famille vitrail \
      --intensite 5 --usage "affiche" --melange paysage

  # styliser un prompt libre existant (l'option de l'app)
  python vitrail_prompt.py --appliquer "a lighthouse keeper over a lake city"

  # sortie machine
  python vitrail_prompt.py --sujet "..." --json
  python vitrail_prompt.py --liste

La fiche (grammaire machine) est cherchee, relative a ce fichier :
`style_vitrail.json` (copie backend), puis `../fiche_style.json` (skill),
puis `fiche_style.json`. Ce fichier est COPIE byte-identique dans le backend
(`app/services/style_vitrail.py`) — le refactorer ICI, puis recopier.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

_FICHE_CANDIDATS = ("style_vitrail.json", os.path.join("..", "fiche_style.json"),
                    "fiche_style.json")
_cache_fiche: dict = {}

# Dosage d'ornement 1..5, cote prompt (miroir EN de fiche["intensites"]).
_INTENSITES_EN = {
    1: "minimal ornament: the figure, a halo, two floral motifs only",
    2: "restrained ornament: figure, halo, a few counted floral motifs",
    3: "medium ornament: an ornamental border, plants, varied glass fragments",
    4: "rich ornament: dense border, plant and celestial motifs",
    5: ("maximal ornament: integrated cosmic, plant, heraldic and "
        "architectural decor"),
}


def charger_fiche(chemin: str | None = None) -> dict:
    """Charge la grammaire machine (memoisee). `chemin` explicite prioritaire."""
    cle = chemin or "_defaut"
    if cle in _cache_fiche:
        return _cache_fiche[cle]
    if chemin:
        candidats = [chemin]
    else:
        ici = os.path.dirname(os.path.abspath(__file__))
        candidats = [os.path.normpath(os.path.join(ici, c))
                     for c in _FICHE_CANDIDATS]
    for c in candidats:
        if os.path.isfile(c):
            with open(c, encoding="utf-8") as fh:
                _cache_fiche[cle] = json.load(fh)
            return _cache_fiche[cle]
    raise FileNotFoundError(
        "fiche introuvable (cherche: %s)" % ", ".join(candidats))


def familles(fiche: dict | None = None) -> list[dict]:
    f = fiche or charger_fiche()
    return [{"id": fid, "label": fam["label"], "label_en": fam["label_en"],
             "usage_conseille": fam.get("usage_conseille", [])}
            for fid, fam in f["familles"].items()]


def garde_noms(texte: str, fiche: dict | None = None) -> str:
    """Leve ValueError si un nom d'artiste du mouvement apparait dans le
    texte. A appeler sur TOUT prompt avant l'envoi a un generateur — le grep
    coute zero, le pastiche et le refus facture coutent."""
    f = fiche or charger_fiche()
    bas = texte.lower()
    trouves = sorted({n for n in f["doctrine"]["artistes_jamais_dans_un_prompt"]
                      if n.lower() in bas})
    if trouves:
        raise ValueError(
            "nom(s) d'artiste dans le prompt (interdit par la doctrine): "
            + ", ".join(trouves))
    return texte


def epurer_noms(texte: str, fiche: dict | None = None) -> str:
    """Retire les noms d'artistes d'un texte UTILISATEUR (avant `appliquer`) :
    la doctrine ne se negocie pas, mais un nom tape par l'utilisateur ne doit
    pas bloquer la generation — le nom disparait, le sujet reste."""
    f = fiche or charger_fiche()
    out = texte or ""
    for n in f["doctrine"]["artistes_jamais_dans_un_prompt"]:
        out = re.sub(re.escape(n), "", out, flags=re.IGNORECASE)
    return re.sub(r"[ \t]{2,}", " ", out).strip()


def _fam(fid: str, fiche: dict) -> dict:
    fam = fiche["familles"].get(fid)
    if fam is None:
        raise KeyError("famille inconnue: %r (valides: %s)"
                       % (fid, ", ".join(fiche["familles"])))
    return fam


def bloc_style(famille: str = "vitrail", fiche: dict | None = None) -> str:
    """Le bloc de style EN pret-generateur de la famille (sans garde-fous)."""
    f = fiche or charger_fiche()
    return _fam(famille, f)["bloc_en"]


def negatif(famille: str = "vitrail", fiche: dict | None = None) -> str:
    """Le prompt negatif complet: refus de la famille + garde-fous communs."""
    f = fiche or charger_fiche()
    fam = _fam(famille, f)
    return (fam["negatif_en"] + ", no text, no lettering, no title, no "
            "signature, no logo, no watermark, not a copy of any existing "
            "artwork")


def _article(nom_en: str) -> str:
    return "an" if nom_en[:1].lower() in "aeiou" else "a"


def appliquer(prompt: str, famille: str = "vitrail",
              fiche: dict | None = None) -> str:
    """Stylise un prompt libre existant : sujet de l'appelant + bloc de la
    famille + garde-fous. C'est la voie de l'option d'app (le prompt d'une
    scene d'episode, d'une planche, d'un ecran images)."""
    f = fiche or charger_fiche()
    fam = _fam(famille, f)
    p = (prompt or "").strip().rstrip(".")
    if not p:
        raise ValueError("prompt vide")
    out = ("%s, rendered as %s %s — %s. Polish modernism of the late 19th "
           "and early 20th century. %s."
           % (p, _article(fam["label_en"]), fam["label_en"], fam["bloc_en"],
              f["doctrine"]["garde_fous_en"]))
    return garde_noms(out, f)


def _composer(sujet: str, fam: dict, fiche: dict, action: str,
              composition: str, palette: str, lumiere: str,
              intensite: int, usage: str, melange: str | None) -> str:
    morceaux = ["Entirely original %s: %s%s"
                % (fam["label_en"], sujet.strip().rstrip("."),
                   (", " + action.strip().rstrip(".")) if action else "")]
    morceaux.append(fam["bloc_en"])
    if composition:
        morceaux.append("composition: " + composition)
    if lumiere:                      # sans surcharge, le bloc porte deja la
        morceaux.append("light: " + lumiere)   # lumiere de la famille
    if palette:
        morceaux.append("palette restricted to: " + palette)
    morceaux.append(_INTENSITES_EN[max(1, min(5, int(intensite)))])
    if melange:
        fam2 = _fam(melange, fiche)
        morceaux.append("with a LIMITED, subordinate addition from the %s "
                        "family" % fam2["label_en"])
    if usage:
        morceaux.append("intended use: " + usage)
    morceaux.append("Polish modernism of the late 19th and early 20th century")
    morceaux.append(fiche["doctrine"]["garde_fous_en"])
    return ". ".join(m.strip().rstrip(".") for m in morceaux if m) + "."


def construire_prompt(sujet: str, famille: str = "vitrail", action: str = "",
                      composition: str = "", palette: str = "",
                      lumiere: str = "", intensite: int = 3, usage: str = "",
                      melange: str | None = None,
                      fiche: dict | None = None) -> dict:
    """La formule universelle du guide (§5), executee : rend le prompt long,
    une variante (autre dosage d'ornement), le negatif et la note pedagogique.
    Leve si le sujet est vide ou si un nom d'artiste fuyait."""
    f = fiche or charger_fiche()
    if not (sujet or "").strip():
        raise ValueError("sujet requis (le contenu narratif original)")
    fam = _fam(famille, f)
    intensite = max(1, min(5, int(intensite)))
    prompt = _composer(sujet, fam, f, action, composition, palette, lumiere,
                       intensite, usage, melange)
    var_int = intensite - 1 if intensite >= 3 else intensite + 1
    variante = _composer(sujet, fam, f, action, composition, palette,
                         lumiere or fam["lumiere_en"] + ", at another hour",
                         var_int, usage, melange)
    notes = []
    if melange:
        paires_ok = {(m["base"], m["ajout"]) for m in f["melange"]["coherents"]}
        if (famille, melange) in paires_ok:
            attendu = next(m["resultat"] for m in f["melange"]["coherents"]
                           if (m["base"], m["ajout"]) == (famille, melange))
            notes.append("melange repertorie — resultat attendu : " + attendu)
        else:
            notes.append("melange NON repertorie par la matrice du guide — "
                         "garder une seule dominante nette")
    notes.append("referents pedagogiques : %s (jamais dans le prompt)"
                 % ", ".join(fam["referents_pedagogiques"]))
    codes = fam["codes"][:max(3, min(6, 2 + intensite))]
    out = {
        "famille": famille,
        "label": fam["label"],
        "codes_mobilises": codes,
        "prompt": prompt,
        "variante": variante,
        "negatif": negatif(famille, f),
        "note": " ; ".join(notes),
        "intensite": intensite,
    }
    garde_noms(out["prompt"], f)
    garde_noms(out["variante"], f)
    return out


def rendu_markdown(r: dict) -> str:
    """Le modele de reponse du guide (§11), rempli."""
    return ("## Direction visuelle\n\n"
            "**Famille :** %s\n"
            "**Codes mobilises :** %s\n"
            "**Pourquoi :** %s\n\n"
            "## Prompt\n\n```text\n%s\n```\n\n"
            "## Variante\n\n```text\n%s\n```\n\n"
            "## A eviter\n\n```text\n%s\n```\n\n"
            "## Lecture pedagogique\n\n"
            "- Intensite d'ornement : %d/5\n"
            "- %s\n"
            % (r["label"], " ; ".join(r["codes_mobilises"][:5]), r["note"],
               r["prompt"], r["variante"], r["negatif"], r["intensite"],
               r["note"]))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Compositeur de prompts Mloda Polska (grammaire du guide).")
    p.add_argument("--sujet", help="le contenu narratif original")
    p.add_argument("--famille", default="vitrail",
                   help="vitrail|symbolisme|portrait|folklore|paysage|"
                        "impressionnisme|synthetisme|decoratif")
    p.add_argument("--action", default="", help="action / etat du sujet")
    p.add_argument("--composition", default="", help="cadrage + structure")
    p.add_argument("--palette", default="", help="restreint la palette")
    p.add_argument("--lumiere", default="", help="qualite de lumiere (EN)")
    p.add_argument("--intensite", type=int, default=3, help="ornement 1-5")
    p.add_argument("--usage", default="", help="affiche, carte, couverture...")
    p.add_argument("--melange", default=None,
                   help="2e famille en ajout limite (matrice du guide)")
    p.add_argument("--appliquer", default=None, metavar="PROMPT",
                   help="stylise un prompt libre existant et sort")
    p.add_argument("--fiche", default=None, help="chemin explicite de la fiche")
    p.add_argument("--json", action="store_true", help="sortie JSON")
    p.add_argument("--liste", action="store_true", help="liste les familles")
    a = p.parse_args(argv)

    fiche = charger_fiche(a.fiche)
    if a.liste:
        for fam in familles(fiche):
            print("%-16s %s" % (fam["id"], fam["label"]))
        return 0
    if a.appliquer is not None:
        out = appliquer(a.appliquer, a.famille, fiche)
        print(json.dumps({"prompt": out}, ensure_ascii=False, indent=2)
              if a.json else out)
        return 0
    if not a.sujet:
        p.error("--sujet requis (ou --appliquer, ou --liste)")
    r = construire_prompt(a.sujet, a.famille, a.action, a.composition,
                          a.palette, a.lumiere, a.intensite, a.usage,
                          a.melange, fiche)
    print(json.dumps(r, ensure_ascii=False, indent=2) if a.json
          else rendu_markdown(r))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):      # console Windows: UTF-8 force
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
