# -*- coding: utf-8 -*-
"""Migration UNIQUE du guide v2.8.0 (une page par langue, chapitres c0-c21) vers les fragments du guide v3.

Lit docs/guide/{fr,en}.html au commit SOURCE (le guide d'avant la refonte), découpe le corps en chapitres <h2 id="cN">
et écrit docs/guide/src/{fr,en}/<id>.html selon `anciens` de docs/guide/src/chapitres.json :
  - un chapitre v3 qui reprend UN ancien chapitre garde son corps tel quel (le titre h2 tombe : le gabarit le refait) ;
  - un chapitre v3 qui en reprend PLUSIEURS les met bout à bout, chacun sous un <h3 id="cN"> (ses h3 deviennent h4) ;
  - l'introduction (bloc .lead) devient le chapitre `tour`, les recettes du chapitre 14 deviennent `parcours`.
Rien n'est réécrit : seules tombent les pastilles de version datées (<span class="new">). Les chapitres migrés sont
marqués `"etat": "migre"` dans chapitres.json ; les lots de contenu les réécrivent et passent l'état à `v3`.

    python scripts/guide/migrer_v28.py            (refuse d'écraser un fragment existant)
"""
import json
import pathlib
import re
import subprocess
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
SOURCE = "e7fb1ac1"
SRC = RACINE / "docs" / "guide" / "src"


def page(lang):
    b = subprocess.run(["git", "show", f"{SOURCE}:docs/guide/{lang}.html"], cwd=RACINE, capture_output=True,
                       check=True).stdout
    return b.decode("utf-8").replace("\r\n", "\n")


def decouper(h):
    corps = h.split('<div class="toc">', 1)[1].split("</div>", 1)[1]
    corps = corps.split('<div class="footer">', 1)[0]
    lead = h.split('<div class="lead">', 1)[1].split("</div>", 1)[0].strip()
    morceaux = re.split(r'(?=<h2 id="c\d+">)', corps)
    chap = {}
    for m in morceaux:
        t = re.match(r'<h2 id="(c\d+)">(.*?)</h2>\n?', m, re.S)
        if not t:
            continue
        titre = re.sub(r'<span class="num">\d+</span>', "", t.group(2))
        titre = re.sub(r'\s*<span class="new">.*?</span>', "", titre).strip()
        chap[t.group(1)] = (titre, m[t.end():].strip())
    return lead, chap


def nettoyer(corps):
    return re.sub(r'\s*<span class="new">[^<]*</span>', "", corps)


def recettes(corps):
    """Le chapitre 14 mêle dépannage et recettes : les recettes commencent au premier h3 qui en est une."""
    m = re.search(r'(<div class="recipe">\s*)?<h3>[^<]*(Recette|Recipe)', corps)   # avec le cadre qui l'ouvre
    return (corps[:m.start()].rstrip(), corps[m.start():]) if m else (corps, "")


def main():
    som = json.loads((SRC / "chapitres.json").read_text("utf-8"))
    for lang in ("fr", "en"):
        lead, chap = decouper(page(lang))
        assert len(chap) == 22, (lang, sorted(chap))
        depannage, parcours = recettes(chap["c14"][1])
        dossier = SRC / lang
        dossier.mkdir(parents=True, exist_ok=True)
        for c in som["chapitres"]:
            if c["id"] == "tour":
                frag = f'<div class="lead">\n{lead}\n</div>'
            elif c["id"] == "parcours":
                frag = parcours
            elif not c["anciens"]:
                continue
            elif len(c["anciens"]) == 1:
                a = c["anciens"][0]
                frag = depannage if a == "c14" else chap[a][1]
            else:
                parts = []
                for a in c["anciens"]:
                    titre, corps = chap[a]
                    corps = re.sub(r"<(/?)h3>", r"<\1h4>", corps)
                    parts.append(f'<h3 id="{a}">{titre}</h3>\n{corps}')
                frag = "\n\n".join(parts)
            cible = dossier / f"{c['id']}.html"
            if cible.exists():
                sys.exit(f"refus : {cible.relative_to(RACINE)} existe déjà")
            cible.write_text(nettoyer(frag).strip() + "\n", "utf-8", newline="\n")
            print("écrit", cible.relative_to(RACINE))
    for c in som["chapitres"]:
        if (SRC / "fr" / f"{c['id']}.html").exists():
            c["etat"] = "migre"
    (SRC / "chapitres.json").write_text(json.dumps(som, ensure_ascii=False, indent=2) + "\n", "utf-8", newline="\n")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
