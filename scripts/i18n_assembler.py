"""Assemble les dictionnaires de l'interface (frontend/shared/i18n/*.json) en UN script classique,
frontend/shared/dz-i18n-dico.js (window.DZ_I18N), copié octet pour octet dans frontend/dist/shared/.

t134 (traduction, lot 0, 07/10/2026). Un seul fichier chargé par <script> avant le runtime dz-i18n.js : aucun lab
n'a de fetch à attendre au démarrage. Les clés sont triées et le JSON est écrit d'une seule façon : rejouer
l'assemblage donne les mêmes octets (test_i18n_l0 2.5 le vérifie), une clé ajoutée sans réassembler se voit.

Usage : python scripts/i18n_assembler.py            (écrit les deux copies)
        python scripts/i18n_assembler.py --check    (code 1 si l'assemblé n'est pas à jour)
"""
import json, pathlib, sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
DOSSIER = RACINE / "frontend" / "shared" / "i18n"
CIBLES = [RACINE / "frontend" / "shared" / "dz-i18n-dico.js", RACINE / "frontend" / "dist" / "shared" / "dz-i18n-dico.js"]
CRLF = "\r\n"
ENTETE = [
    "/* dz-i18n-dico.js — FICHIER ASSEMBLÉ, ne pas éditer : la source est frontend/shared/i18n/*.json,",
    "   l'assembleur scripts/i18n_assembler.py (t134). Une clé zone.objet.role -> {fr, en} ; le français est la langue",
    "   de référence. Chargé avant /shared/dz-i18n.js dans la SPA et les huit pages à part. */",
]


def assembler(dossier=DOSSIER) -> bytes:
    tout = {}
    for f in sorted(pathlib.Path(dossier).glob("*.json")):
        for k, v in json.loads(f.read_text("utf-8")).items():
            if k in tout:
                raise SystemExit(f"clé en double : {k} ({f.name})")
            tout[k] = {"fr": v["fr"], "en": v["en"]}
    lignes = ENTETE + ["window.DZ_I18N = Object.assign(window.DZ_I18N || {}, {"]
    cles = sorted(tout)
    for i, k in enumerate(cles):
        fin = "," if i < len(cles) - 1 else ""
        lignes.append("  " + json.dumps(k, ensure_ascii=False) + ": " + json.dumps(tout[k], ensure_ascii=False) + fin)
    lignes.append("});")
    return (CRLF.join(lignes) + CRLF).encode("utf-8")


def main(args):
    octets = assembler()
    if "--check" in args:
        a_jour = all(c.is_file() and c.read_bytes() == octets for c in CIBLES)
        print("à jour" if a_jour else "PAS à jour : python scripts/i18n_assembler.py")
        return 0 if a_jour else 1
    for c in CIBLES:
        c.write_bytes(octets)
    print(f"{len(octets)} octets -> " + ", ".join(str(c.relative_to(RACINE)) for c in CIBLES))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
