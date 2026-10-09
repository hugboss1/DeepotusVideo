# -*- coding: utf-8 -*-
"""Extrait le registre des noeuds du Studio (l'objet `Me` du bundle) vers backend/app/assets/studio_nodes.json, que la
validation d'import d'un graphe lit (tache #69 du suivi, plan-studio T6, 02/10/2026).

Le bundle reste la SOURCE : ce JSON en est un miroir. backend/tests/test_studio_graph_io.py surveille la derive entre
les deux (un noeud ajoute au bundle sans relancer ce script fait rougir la serie).
Le bundle est lu en OCTETS (le mode texte aplatirait ses CRLF) et l'objet `Me` est borne par appariement d'accolades,
pas par une longueur devinee.

Run : python scripts/qa/dump_studio_registry.py [--check]
"""
import json
import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
CIBLE = RACINE / "backend" / "app" / "assets" / "studio_nodes.json"
DEBUT = 'Me={Image:{cat:"source",title:"Image"'

# t142 (traduction L2) : un titre ou une description peut être `dzT("clé")` (texte affiché dans la langue de
# l'interface) ; le miroir garde le texte ANGLAIS d'origine, lu au dictionnaire frontend/shared/i18n/*.json
TEXTE = r'(?:"([^"]*)"|dzT\("([a-z0-9_.]+)"\))'
ENTREE = re.compile(
    r'(?:^|[{,])([A-Za-z]+):\{cat:"(source|gen|edit|compose|audio|motion|master|output)",'
    r'title:' + TEXTE + r',desc:' + TEXTE + r',inPorts:\[([^\]]*)\],outPorts:\[([^\]]*)\]')
PORT = re.compile(r'\{id:"([A-Za-z0-9_]+)",type:"([a-z]+)"\}')


def _dico() -> dict:
    d = {}
    for f in sorted((RACINE / "frontend" / "shared" / "i18n").glob("*.json")):
        d.update(json.loads(f.read_bytes().decode("utf-8")))
    return d


def _texte(lit, cle, dico):
    if not cle:
        return lit
    if cle not in dico:
        raise SystemExit(f"[registre] cle {cle} absente du dictionnaire")
    return dico[cle]["en"]


def segment(s: str) -> str:
    """Le texte de l'objet `Me`, accolades comprises (les chaines sont sautees)."""
    k = s.index(DEBUT) + 3
    prof, i, chaine = 0, k, None
    while i < len(s):
        c = s[i]
        if chaine:
            if c == "\\":
                i += 2
                continue
            if c == chaine:
                chaine = None
        elif c in "\"'`":
            chaine = c
        elif c == "{":
            prof += 1
        elif c == "}":
            prof -= 1
            if prof == 0:
                return s[k:i + 1]
        i += 1
    raise SystemExit("[registre] objet Me non referme")


def extraire() -> dict:
    s = BUNDLE.read_bytes().decode("utf-8")
    seg = segment(s)
    types, dico = {}, _dico()
    for nom, cat, titre, titre_cle, _desc, _desc_cle, ip, op in ENTREE.findall(seg):
        types[nom] = {
            "cat": cat,
            "title": _texte(titre, titre_cle, dico),
            "in": [p[0] for p in PORT.findall(ip)],
            "out": [p[0] for p in PORT.findall(op)],
            "in_types": {p[0]: p[1] for p in PORT.findall(ip)},
            "out_types": {p[0]: p[1] for p in PORT.findall(op)},
        }
    entrees = len(re.findall(r'(?:^|[{,])[A-Za-z]+:\{cat:"', seg))
    if len(types) < 30 or len(types) != entrees:
        raise SystemExit(
            f"[registre] {len(types)} types extraits sur {entrees} entrees (34 au 02/10) — la forme du registre a "
            "change, relire l'expression ENTREE avant d'ecrire quoi que ce soit.")
    return {"source": BUNDLE.name, "count": len(types), "types": types}


def texte(doc: dict) -> str:
    return json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def main():
    doc = extraire()
    t = texte(doc)
    if "--check" in sys.argv:
        actuel = CIBLE.read_bytes().decode("utf-8").replace("\r\n", "\n") if CIBLE.is_file() else ""
        if actuel != t:
            print(f"[registre] DERIVE : {CIBLE.name} ne correspond plus au bundle. Relance sans --check.")
            return 1
        print(f"[registre] a jour ({doc['count']} types)")
        return 0
    CIBLE.parent.mkdir(parents=True, exist_ok=True)
    CIBLE.write_bytes(t.encode("utf-8"))
    print(f"[registre] ecrit {CIBLE} ({doc['count']} types)")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.exit(main())
