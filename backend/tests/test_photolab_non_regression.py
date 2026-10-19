# -*- coding: utf-8 -*-
"""t250 (Photolab M1, 20/10/2026) — garde « ne rien écraser » d'une montée du moteur photocraft.

La RÉFÉRENCE (tests/photolab_etats_reference.json) est le relevé de l'écran sur le moteur 0.3.0 : état de chaque entrée
de menu générée, outils actifs, onglets de panneau présents, ensemble TRAITES_PAR_ECRAN. Le banc relève l'écran
d'aujourd'hui (scripts/photolab_etats.mjs, le VRAI code de l'écran) sur le registre d'un moteur et vérifie :
  [1] aucune entrée qui marchait (actif / inactif) ne repasse « bientôt » ni ne disparaît ;
  [2] le nombre de « bientôt » ne monte pas ;
  [3] aucun outil actif ne repasse p2:false ; aucun onglet de panneau ne disparaît ;
  [4] TRAITES_PAR_ECRAN garde tous ses ids (l'écran continue de les faire lui-même, sans le moteur) ;
  [5] les 18 sections de Préférences restent de l'écran (jamais prefs.* du moteur).
Hors ligne : aucun moteur lancé ; node requis.

Run : & $PY -X utf8 tests/test_photolab_non_regression.py [--commandes <registre.json>]   (depuis backend/)
  --commandes : éprouver un registre CANDIDAT (ex. tests/photocraft_commandes_0.10.0.json) avant de monter de version.
  --ecrire    : (une seule fois, sur le moteur de référence) réécrit la référence. Jamais pour faire passer le banc."""
import json, pathlib, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
RACINE = BACKEND.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))
from app.services import photolab_registre as PR              # noqa: E402
import photocraft_version as V                                  # noqa: E402

REFERENCE = BACKEND / "tests" / "photolab_etats_reference.json"
NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


def releve(chemin_commandes: pathlib.Path) -> dict:
    """États de l'écran sur ce registre : forme de GET /api/photolab/commandes, puis le code réel de l'écran."""
    brut = json.loads(chemin_commandes.read_text(encoding="utf-8"))
    liste = brut if isinstance(brut, list) else (brut or {}).get("commands") or []
    reg = PR.structurer(liste)
    servi = [{**c, "champs": reg[c["id"]]["champs"]} for c in liste]
    with tempfile.TemporaryDirectory() as t:
        t = pathlib.Path(t)
        (t / "registre.json").write_text(json.dumps(servi, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run([NODE, str(RACINE / "scripts" / "photolab_etats.mjs"), str(RACINE), str(t / "registre.json"),
                            str(t / "etats.json")], capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0:
            raise RuntimeError("photolab_etats.mjs : " + (r.stderr or r.stdout))
        return json.loads((t / "etats.json").read_text(encoding="utf-8"))


def comparer(ref: dict, cur: dict) -> dict:
    """Écarts bloquants entre la référence et le relevé courant ; [] partout = aucune régression."""
    perdues = sorted(i for i, e in ref["entrees"].items()
                     if e["etat"] != "bientot" and cur["entrees"].get(i, {}).get("etat", "absent") in ("bientot", "absent"))
    return {
        "entrees_perdues": perdues,
        "outils_perdus": sorted(o for o, a in ref["outils"].items() if a and not cur["outils"].get(o)),
        "panneaux_perdus": sorted(p for p, a in ref["panneaux"].items() if a and not cur["panneaux"].get(p)),
        "ecran_perdus": sorted(set(ref["traites_par_ecran"]) - set(cur["traites_par_ecran"])),
    }


def main(args) -> int:
    if not NODE:
        check("0 node est présent (requis pour relire l'écran)", False)
        return 1
    chemin = pathlib.Path(args[args.index("--commandes") + 1]) if "--commandes" in args else V.fichier_commandes()
    print(f"registre éprouvé : {chemin.name}")
    cur = releve(chemin)
    if "--ecrire" in args:
        REFERENCE.write_text(json.dumps({"_source": f"{chemin.name} + écran d'origin/main (t250, 20/10/2026)", **cur},
                                        ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        print("référence réécrite :", cur["compte"])
        return 0
    ref = json.loads(REFERENCE.read_text(encoding="utf-8"))
    check("0 la référence est celle du moteur 0.3.0 (632 ids de menu, dont 91 « bientôt », au 20/10)",
          ref["_source"].startswith("photocraft_commandes_0.3.0.json") and len(ref["entrees"]) == 632
          and ref["compte"].get("bientot") == 91, ref.get("compte"))

    e = comparer(ref, cur)
    check("1 aucune entrée qui marchait ne repasse « bientôt » ni ne disparaît", not e["entrees_perdues"],
          e["entrees_perdues"][:20])
    check("2 le nombre de « bientôt » ne monte pas",
          cur["compte"].get("bientot", 0) <= ref["compte"].get("bientot", 0), (ref["compte"], cur["compte"]))
    check("3a aucun outil actif ne repasse « bientôt »", not e["outils_perdus"], e["outils_perdus"])
    check("3b aucun onglet de panneau ne disparaît", not e["panneaux_perdus"], e["panneaux_perdus"])
    check("4 TRAITES_PAR_ECRAN garde tous ses ids", not e["ecran_perdus"], e["ecran_perdus"][:20])
    prefs = [i for i in cur["traites_par_ecran"] if i.startswith("edit.preferences.")]
    check("5 les 18 sections de Préférences restent de l'écran", len(prefs) >= 18, len(prefs))

    # Information (non bloquante) : ce que le registre éprouvé ouvre de plus, et les entrées passées actif → inactif
    # (`enabled` du registre sans document ouvert).
    gagnees = sorted(i for i, x in cur["entrees"].items()
                     if x["etat"] != "bientot" and ref["entrees"].get(i, {}).get("etat", "bientot") == "bientot")
    inactives = sorted(i for i, x in cur["entrees"].items()
                       if x["etat"] == "inactif" and ref["entrees"].get(i, {}).get("etat") == "actif")
    print(f"  INFO  compte référence {ref['compte']} → aujourd'hui {cur['compte']}")
    print(f"  INFO  {len(gagnees)} entrée(s) sortie(s) de « bientôt » : {gagnees[:15]}")
    print(f"  INFO  {len(inactives)} entrée(s) actif → inactif (sans document) : {inactives[:15]}")

    # Le banc s'éprouve lui-même : une référence où l'on retire un id d'écran, un outil, une entrée active
    # doit être VUE comme une régression par comparer().
    faux = json.loads(json.dumps(cur))
    une_active = next(i for i, x in faux["entrees"].items() if x["etat"] == "actif")
    faux["entrees"][une_active]["etat"] = "bientot"
    faux["outils"][next(o for o, a in faux["outils"].items() if a)] = False
    faux["traites_par_ecran"] = faux["traites_par_ecran"][1:]
    del faux["panneaux"][next(p for p, a in faux["panneaux"].items() if a)]
    e2 = comparer(cur, faux)
    check("6 le banc voit une régression fabriquée (entrée, outil, panneau, écran)",
          e2["entrees_perdues"] == [une_active] and len(e2["outils_perdus"]) == 1 and len(e2["panneaux_perdus"]) == 1
          and len(e2["ecran_perdus"]) == 1, e2)

    print(f"\n{ok} PASS / {fail} FAIL")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
