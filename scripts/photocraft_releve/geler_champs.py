"""Gèle les champs des commandes dont la description change à la montée de photocraft (07/11/2026, 0.10.0 -> 0.21.0).

La liste blanche du pont suit le registre du moteur : sans ce gel, la montée ouvrirait en douce des clés neuves
(`target`, `as`, `shapePath`…) et casserait la lecture de champs existants (`"width":number`). Pour chaque commande
connue de l'ancienne version dont la lecture diffère, on garde la lecture de l'ancienne version, telle quelle.
Un lot ouvre une clé en retirant la commande de ce fichier, avec son banc.

Usage (depuis la racine du dépôt, python embarqué) :
  python scripts/photocraft_releve/geler_champs.py <ancien_registre.json> <nouveau_registre.json>
"""
import json, pathlib, sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "backend"))
SORTIE = RACINE / "backend" / "app" / "services" / "photolab_champs_geles.json"
OUVERTES = {"shape.create", "shape.edit"}                # t413 : lues au registre 0.21 (angles arrondis, flèches)


def lire(chemin):
    return json.loads(pathlib.Path(chemin).read_text(encoding="utf-8"))


def main(ancien, nouveau) -> int:
    from app.services import photolab_registre as PR
    SORTIE.write_text("{}\n", encoding="utf-8")
    PR.CHAMPS_GELES.clear()
    avant, apres = PR.structurer(lire(ancien)), PR.structurer(lire(nouveau))
    geles = {}
    for cid, a in sorted(avant.items()):
        b = apres.get(cid)
        if b is None:
            raise SystemExit(f"commande retirée par la nouvelle version : {cid}")
        if cid not in OUVERTES and (a["champs"], a["ok"], a["inconnus"]) != (b["champs"], b["ok"], b["inconnus"]):
            geles[cid] = {"champs": a["champs"], "ok": a["ok"], "inconnus": a["inconnus"]}
    SORTIE.write_text(json.dumps(geles, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(geles)} commandes gelées -> {SORTIE}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
