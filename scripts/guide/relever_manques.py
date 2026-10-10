# -*- coding: utf-8 -*-
"""Liste des fonctionnalités absentes du guide v2.8.0, rangées par chapitre du guide v3.

Entrées (docs/guide/src/) : chapitres.json (sommaire v3, chaque chapitre liste les écrans du relevé qu'il couvre),
releve/livraisons.json (fonctions visibles livrées depuis le 07/09/2026), releve/couverture-v2.8.json (ce que
dit le guide v2.8.0, dont ses affirmations périmées).
Sortie : docs/guide/MANQUES.md (une ligne par fonction, case à cocher pour le lot qui l'écrit).

    python scripts/guide/relever_manques.py [--check]
"""
import collections
import json
import pathlib
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
SRC = RACINE / "docs" / "guide" / "src"
SORTIE = RACINE / "docs" / "guide" / "MANQUES.md"
RECLASSER = {}


def lire(nom):
    return json.loads((SRC / nom).read_text("utf-8"))


def construire():
    global RECLASSER
    som, liv, cov = lire("chapitres.json"), lire("releve/livraisons.json"), lire("releve/couverture-v2.8.json")
    RECLASSER = lire("releve/reclasser.json") if (SRC / "releve/reclasser.json").is_file() else {}
    par_ecran = {e["ecran"]: e for e in liv["ecrans"]}
    anciens = {c["id"]: c for c in cov["chapitres"]}
    familles = {f["id"]: f["fr"] for f in som["familles"]}
    total = sum(len(e["fonctions"]) for e in liv["ecrans"])
    payantes = sum(1 for e in liv["ecrans"] for f in e["fonctions"] if f.get("payant"))
    L = ["# Guide v3 : ce qui manque au guide v2.8.0", "",
         "Généré par `scripts/guide/relever_manques.py` : ne pas éditer à la main.", "",
         f"- {total} fonctions visibles livrées depuis le 07/09/2026 (v2.8.0) ; {payantes} sont payantes.",
         f"- {sum(len(c['fonctions']) for c in cov['chapitres'])} fonctions décrites par le guide v2.8.0 "
         f"(22 chapitres c0-c21).",
         f"- {len(som['chapitres'])} chapitres dans le sommaire v3, en {len(som['familles'])} familles.", "",
         "Chaque chapitre liste d'abord ce que l'ancien guide disait de FAUX (à corriger), puis les fonctions "
         "manquantes. Le lot coche une ligne quand le chapitre l'explique.", ""]
    famille = None
    resume, faits = collections.Counter(), collections.Counter()
    for ch in som["chapitres"]:
        if ch["famille"] != famille:
            famille = ch["famille"]
            L += [f"## {familles[famille]}", ""]
        # releve/reclasser.json range une fonction dans un autre chapitre que celui de son écran (ex. HeyGen → quick)
        fonctions = [(e, f) for nom in ch["ecrans"] for e in [par_ecran[nom]] for f in e["fonctions"]
                     if RECLASSER.get(f["nom"], ch["id"]) == ch["id"]]
        fonctions += [(e, f) for e in liv["ecrans"] for f in e["fonctions"]
                      if RECLASSER.get(f["nom"]) == ch["id"] and e["ecran"] not in ch["ecrans"]]
        resume[ch["lot"]] += len(fonctions)
        faits[ch["lot"]] += len(fonctions) if ch.get("etat") == "v3" else 0
        anc = ", ".join(ch["anciens"]) or "nouveau"
        L += [f"### {ch['fr']} (`{ch['id']}`, lot {ch['lot']}, reprend : {anc}) — {len(fonctions)} manques", ""]
        perimes = [p for a in ch["anciens"] for p in anciens.get(a, {}).get("perime", [])]
        if perimes:
            L += ["À corriger dans l'ancien texte :", ""] + [f"- [ ] {p}" for p in perimes] + [""]
        ecran = None
        for e, f in fonctions:
            if e["ecran"] != ecran:
                ecran = e["ecran"]
                L += [f"**{ecran}** — accès : {e.get('acces') or '?'}", ""]
            prix = " **payant**" if f.get("payant") else (" *(coût variable)*" if f.get("payant") is None else "")
            comment = f" — *{f['comment']}*" if f.get("comment") else ""
            case = "x" if ch.get("etat") == "v3" else " "      # un chapitre réécrit (état v3) couvre ses lignes
            L.append(f"- [{case}] **{f['nom']}**{prix} : {f['quoi']}{comment} ({f.get('ref') or '?'})")
        L.append("")
    L += ["## Répartition par lot", "", "| Lot | Fonctions | Écrites |", "|---|---|---|"]
    L += [f"| {lot} | {n} | {faits[lot]} |" for lot, n in sorted(resume.items())]
    return "\n".join(L) + "\n"


def main():
    texte = construire()
    if "--check" in sys.argv:
        actuel = SORTIE.read_text("utf-8").replace("\r\n", "\n") if SORTIE.is_file() else ""
        print("à jour" if actuel == texte else "PÉRIMÉ : relancer python scripts/guide/relever_manques.py")
        return 0 if actuel == texte else 1
    SORTIE.write_text(texte, "utf-8", newline="\n")
    print(f"écrit : {SORTIE.relative_to(RACINE)} ({texte.count(chr(10))} lignes)")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
