# -*- coding: utf-8 -*-
"""Catalogue des éléments de l'assistant « Demander » (spec 2026-10-19-agent-catalogue-design.md § 1-2).

  python scripts/agent/catalogue.py              met docs/agent/catalogue/ à jour depuis le code
  python scripts/agent/catalogue.py --check      code 1 si le catalogue n'est pas à jour, ou si un écran couvert
                                                 (_couverture.json) garde des fiches extrait/perime/retire
  python scripts/agent/catalogue.py --rapport    par écran : nombre de fiches par état

Fusion SANS écraser : role, synonymes, localisateur, guide, notes (et l'écran si ecran_fixe) viennent du skill
connaissance-agent et sont toujours gardés. Une fiche neuve est « extrait » ; une fiche rédigée dont la source change
devient « perime » ; une fiche dont la source disparaît devient « retire » (le skill la supprime).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import catalogue_sources as S                                               # noqa: E402

RACINE = ICI.parents[1]
DOSSIER = RACINE / "docs" / "agent" / "catalogue"
ETATS = ("extrait", "redige", "perime", "retire")
GARDES = ("role", "synonymes", "localisateur", "guide", "notes")
ORDRE = ("id", "ecran", "ecran_fixe", "cadre", "type", "libelle", "infobulle", "icone", "reglages", "fiche", "role",
         "synonymes", "guide", "localisateur", "notes", "sources", "empreinte", "etat")


def empreinte(e: dict) -> str:
    vu = {k: e.get(k) for k in ("type", "libelle", "infobulle", "icone")}
    return hashlib.sha1(json.dumps(vu, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:12]


def fusionner(existants: dict, extraits: dict) -> dict:
    out = {}
    for i, brut in extraits.items():
        e = dict(brut)
        e["empreinte"] = empreinte(e)
        a = existants.get(i)
        if a is None:
            e.update(role={"fr": "", "en": ""}, synonymes={"fr": [], "en": []}, localisateur=None, guide=None,
                     etat="extrait")
        else:
            for k in GARDES:
                if k in a:
                    e[k] = a[k]
            e.setdefault("role", {"fr": "", "en": ""})
            e.setdefault("synonymes", {"fr": [], "en": []})
            e.setdefault("localisateur", None)
            e.setdefault("guide", None)
            if a.get("ecran_fixe"):
                e["ecran"], e["ecran_fixe"] = a["ecran"], True
            if a.get("etat") == "retire":
                e["etat"] = "redige" if (a.get("role") or {}).get("fr") else "extrait"
            elif a.get("etat") == "redige" and a.get("empreinte") != e["empreinte"]:
                e["etat"] = "perime"
            else:
                e["etat"] = a.get("etat", "extrait")
        out[i] = e
    for i, a in existants.items():
        if i not in out:
            out[i] = {**a, "etat": "retire"}
    return out


def _ligne(f: dict) -> str:
    rang = {k: n for n, k in enumerate(ORDRE)}
    return json.dumps({k: f[k] for k in sorted(f, key=lambda k: rang.get(k, 99))}, ensure_ascii=False)


def texte_fichier(ecran: str, fiches: list) -> str:
    lignes = ",\n".join("    " + _ligne(f) for f in sorted(fiches, key=lambda f: f["id"]))
    return '{\n  "ecran": ' + json.dumps(ecran) + ',\n  "fiches": [\n' + lignes + "\n  ]\n}\n"


def par_ecran(fiches: dict) -> dict:
    g = {}
    for f in fiches.values():
        g.setdefault(f.get("ecran") or "commun", []).append(f)
    return g


def charger(dossier=DOSSIER) -> dict:
    out = {}
    for f in sorted(pathlib.Path(dossier).glob("*.json")):
        if not f.name.startswith("_"):
            for x in json.loads(f.read_text(encoding="utf-8"))["fiches"]:
                out[x["id"]] = x
    return out


def ecrire(dossier, fiches: dict) -> None:
    dossier = pathlib.Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    groupes = par_ecran(fiches)
    for f in dossier.glob("*.json"):
        if not f.name.startswith("_") and f.stem not in groupes:
            f.unlink()
    for ecran, liste in groupes.items():
        (dossier / f"{ecran}.json").write_text(texte_fichier(ecran, liste), encoding="utf-8", newline="\n")


def calculer(racine: pathlib.Path) -> tuple[pathlib.Path, dict, dict]:
    dossier = racine / "docs" / "agent" / "catalogue"
    existants = charger(dossier) if dossier.is_dir() else {}
    return dossier, existants, fusionner(existants, S.extraire(racine))


def couverture(dossier: pathlib.Path) -> list:
    f = dossier / "_couverture.json"
    return json.loads(f.read_text(encoding="utf-8")).get("ecrans", []) if f.exists() else []


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    racine = pathlib.Path(argv[argv.index("--racine") + 1]) if "--racine" in argv else RACINE
    dossier, existants, fiches = calculer(racine)
    if "--check" in argv:
        attendu = {e: texte_fichier(e, l) for e, l in par_ecran(fiches).items()}
        present = {f.stem: f.read_text(encoding="utf-8") for f in dossier.glob("*.json")
                   if not f.name.startswith("_")} if dossier.is_dir() else {}
        if attendu != present:
            print("catalogue PAS à jour : lance python scripts/agent/catalogue.py puis le skill connaissance-agent")
            return 1
        couverts = set(couverture(dossier))
        reste = sorted(f["id"] for f in fiches.values() if f.get("ecran") in couverts and f["etat"] != "redige")
        if reste:
            print(f"{len(reste)} fiche(s) à rédiger sur des écrans couverts : {', '.join(reste[:20])}")
            return 1
        print(f"catalogue à jour : {len(fiches)} fiches")
        return 0
    if "--rapport" in argv:
        for ecran, liste in sorted(par_ecran(fiches).items()):
            n = {e: sum(1 for f in liste if f["etat"] == e) for e in ETATS}
            print(f"{ecran:12} " + "  ".join(f"{e}={n[e]}" for e in ETATS))
        return 0
    ecrire(dossier, fiches)
    print(f"{len(fiches)} fiches écrites dans {dossier}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
