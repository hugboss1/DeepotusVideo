# -*- coding: utf-8 -*-
"""Guide utilisateur v3 (t169, skill guide-deepotus) : le guide construit est à jour, bilingue À L'IDENTIQUE, et ne
ment ni sur ses icônes, ni sur ses images, ni sur ses ancres.

Témoin : le guide v2.8.0 (commit e7fb1ac1) n'avait ni src/, ni index.html (/guide/ répondait 404), et sa version
s'écrivait à la main.
Run : & $PY tests/test_guide_v3.py   (depuis backend/, python EMBARQUÉ)"""
import json
from html import unescape as html_unescape
import pathlib
import re
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parents[2]
GUIDE = RACINE / "docs" / "guide"
SRC = GUIDE / "src"
PY = sys.executable

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {label}")
    else:
        fail += 1
        print(f"  FAIL  {label} {str(detail)[:600]}")


def git(*a):
    return subprocess.run(["git", *a], cwd=RACINE, capture_output=True, text=True, encoding="utf-8").stdout


def lancer(*a):
    r = subprocess.run([PY, *a], cwd=RACINE, capture_output=True, text=True, encoding="utf-8")
    return r.returncode, (r.stdout + r.stderr).strip()


SOM = json.loads((SRC / "chapitres.json").read_text("utf-8"))
PAGES = {l: (GUIDE / f"{l}.html").read_text("utf-8") for l in ("fr", "en")}
ICO = set(re.findall(r'^\s*"(dz-[a-z0-9-]+)":', (RACINE / "frontend/shared/icons/dz-icons.js").read_text("utf-8"), re.M))
VERSION = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', (RACINE / "backend/app/config.py").read_text("utf-8"), re.M).group(1)

print("\n[0] témoin : le guide v2.8.0")
check("0.1 TÉMOIN : l'ancien guide n'avait ni sources, ni index.html",
      git("ls-tree", "--name-only", "e7fb1ac1", "docs/guide/").split() == [
          "docs/guide/Deepotus-Guide-EN.pdf", "docs/guide/Deepotus-Guide-FR.pdf", "docs/guide/en.html",
          "docs/guide/fr.html", "docs/guide/img"], git("ls-tree", "--name-only", "e7fb1ac1", "docs/guide/"))

print("\n[1] les sorties sont celles des sources")
rc, out = lancer("scripts/guide/construire_guide.py", "--check")
check("1.1 construire_guide.py --check : à jour", rc == 0 and out.endswith("à jour"), out)
rc, out = lancer("scripts/guide/relever_manques.py", "--check")
check("1.2 relever_manques.py --check : MANQUES.md à jour", rc == 0, out)
check("1.3 la version vient de APP_VERSION, en-tête ET pied, dans les deux langues",
      all(h.count(f"v{VERSION}") >= 3 for h in PAGES.values()), [h.count(f"v{VERSION}") for h in PAGES.values()])

print("\n[2] bilingue à l'identique")
publies = {l: [c["id"] for c in SOM["chapitres"] if (SRC / l / f"{c['id']}.html").is_file()] for l in ("fr", "en")}
check("2.1 mêmes chapitres publiés en FR et en EN", publies["fr"] == publies["en"] and publies["fr"],
      set(publies["fr"]) ^ set(publies["en"]))
SQUELETTE = {"h3": r"<h3\b", "h4": r"<h4\b", "étape": r'class="step"|<ol class="etapes"', "li d'étapes": r"<li>",
             "astuce": r'class="tip"|<aside class="astuce"', "attention": r'class="warn"|<aside class="attention"',
             "coût": r'<aside class="cout"', "recette": r'class="recipe"', "table": r"<table\b", "image": r"<img\b",
             "scène": r'<figure class="scene"', "fiche": r'<figure class="fiche"', "icône": r"data-dz=",
             "touche": r"<kbd>", "libellé": r'<b class="ui">', "lien externe": r'href="https?://'}
ecarts = []
for cid in publies["fr"]:
    f, e = ((SRC / l / f"{cid}.html").read_text("utf-8") for l in ("fr", "en"))
    for nom, rx in SQUELETTE.items():
        nf, ne = len(re.findall(rx, f)), len(re.findall(rx, e))
        if nf != ne:
            ecarts.append(f"{cid}:{nom} {nf}≠{ne}")
    if re.findall(r'\bid="([^"]+)"', f) != re.findall(r'\bid="([^"]+)"', e):
        ecarts.append(f"{cid}:ids")
check("2.2 chaque chapitre a le MÊME squelette en FR et en EN (titres, étapes, encadrés, scènes, ids…)", not ecarts, ecarts)
desequilibres = []
for l in ("fr", "en"):
    for cid in publies[l]:
        f = (SRC / l / f"{cid}.html").read_text("utf-8")
        for t in ("div", "section", "aside", "table", "figure", "ol", "ul", "article"):
            o, c = len(re.findall(rf"<{t}[\s>]", f)), f.count(f"</{t}>")
            if o != c:
                desequilibres.append(f"{l}/{cid}:{t} {o}≠{c}")
check("2.4 chaque fragment ferme ce qu'il ouvre (une balise de trop sortait un chapitre de la colonne)",
      not desequilibres, desequilibres)
check("2.3 les deux pages ont les mêmes ancres", sorted(re.findall(r'\bid="([^"]+)"', PAGES["fr"])) ==
      sorted(re.findall(r'\bid="([^"]+)"', PAGES["en"])))

print("\n[3] icônes, images, ancres")
cles = {k for l in ("fr", "en") for c in publies[l] for k in re.findall(r'data-dz="([^"]+)"', (SRC / l / f"{c}.html").read_text("utf-8"))}
cles |= {c["icone"] for c in SOM["chapitres"]}
inconnues = sorted(k for k in cles if k not in ICO and not k.startswith("dz-marque-"))
check("3.1 toute icône citée existe dans dz-icons.js", not inconnues, inconnues)
manquantes = sorted({s for h in PAGES.values() for s in re.findall(r'<img[^>]+src="([^"]+)"', h) if not (GUIDE / s).is_file()})
check("3.2 toute image citée existe sur le disque", not manquantes, manquantes)
for l, h in PAGES.items():
    ids = set(re.findall(r'\bid="([^"]+)"', h))
    balisage = re.sub(r"<script\b.*?</script>", "", h, flags=re.S)        # le JS fabrique ses liens depuis l'index
    mortes = sorted({a for a in re.findall(r'href="#([^"]+)"', balisage) if a not in ids})
    check(f"3.3 [{l}] tout lien interne arrive sur une ancre", not mortes, mortes)
    alias = [f"c{i}" for i in range(22)]
    check(f"3.4 [{l}] les 22 anciens ancres c0-c21 existent encore (liens de l'app, PDF imprimés)",
          all(a in ids for a in alias), [a for a in alias if a not in ids])
    check(f"3.5 [{l}] les 18 ancres lex-* du lexique de l'Établi", len([i for i in ids if i.startswith("lex-")]) == 18)
    check(f"3.6 [{l}] aucune icône vide (SVG en ligne)", '<span class="dzi" aria-hidden="true"></span>' not in h)

print("\n[4] scènes animées")
scenes = sorted(p.parent for p in (SRC / "scenes").rglob("scene.json"))
check("4.0 au moins une scène (le lecteur est prouvé sur une vraie)", scenes, scenes)
for d in scenes:
    s = json.loads((d / "scene.json").read_text("utf-8"))
    W, H = s["taille"]
    prob = []
    for k, t in enumerate(s["temps"]):
        if not 0 <= t["capture"] < len(s["captures"]):
            prob.append(f"temps {k} : capture {t['capture']}")
        for cle in ("curseur", "ancre"):
            if t.get(cle) and not (0 <= t[cle][0] <= W and 0 <= t[cle][1] <= H):
                prob.append(f"temps {k} : {cle} hors capture")
        if t.get("surligne"):
            x, y, w, h = t["surligne"]
            if not (x >= 0 and y >= 0 and w > 0 and h > 0 and x + w <= W and y + h <= H):
                prob.append(f"temps {k} : surligne hors capture")
        if t.get("bulle") and not (t["bulle"].get("fr") and t["bulle"].get("en")):
            prob.append(f"temps {k} : bulle sans FR ou EN")
        if t.get("clic") and not t.get("curseur"):
            prob.append(f"temps {k} : clic sans curseur")
    for cap in s["captures"]:
        for f in (cap.values() if isinstance(cap, dict) else [cap]):
            if not (d / f).is_file():
                prob.append(f"capture absente {f}")
            else:
                from PIL import Image
                with Image.open(d / f) as im:
                    if list(im.size) != [W, H]:
                        prob.append(f"{f} : {im.size} ≠ taille {W}×{H}")
    check(f"4.1 scène {d.relative_to(SRC / 'scenes').as_posix()} : repères dans la capture, bulles FR+EN", not prob, prob)

print("\n[5] la page tourne")
with tempfile.TemporaryDirectory() as t:
    for l, h in PAGES.items():
        js = re.findall(r"<script>(.*?)</script>", h, re.S)[-1]
        p = pathlib.Path(t) / f"g_{l}.js"
        p.write_text(js, "utf-8")
        r = subprocess.run(["node", "--check", str(p)], capture_output=True, text=True)
        check(f"5.1 [{l}] le script de la page est du JavaScript valide", r.returncode == 0, r.stderr)
        idx = json.loads(re.search(r'<script type="application/json" id="g-index">(.*?)</script>', h, re.S).group(1))
        check(f"5.2 [{l}] l'index de recherche couvre chaque chapitre publié",
              {e["a"] for e in idx} >= set(publies[l]), set(publies[l]) - {e["a"] for e in idx})
    idx_js = re.search(r"<script>(.*?)</script>", (GUIDE / "index.html").read_text("utf-8"), re.S).group(1)
    res = []
    for stocke, nav in ((None, "fr-FR"), (None, "de-DE"), ("en", "fr-FR"), ("fr", "en-US")):
        code = ("var out=null;var location={hash:'#c18',replace:function(u){out=u}};var navigator={language:'" + nav + "'};"
                "var localStorage={getItem:function(k){return k==='dz_lang'?" + json.dumps(stocke) + ":null}};"
                + idx_js + "console.log(out);")
        p = pathlib.Path(t) / "idx.js"
        p.write_text(code, "utf-8")
        res.append(subprocess.run(["node", str(p)], capture_output=True, text=True).stdout.strip())
    check("5.3 /guide/ redirige vers la langue de l'app (dz_lang), sinon du navigateur, en gardant l'ancre",
          res == ["fr.html#c18", "en.html#c18", "en.html#c18", "fr.html#c18"], res)

print("\n[6] chapitres réécrits (état v3) : la grammaire du skill")
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿①-⓿←-⇿⌀-⏿️]")
v3 = [c["id"] for c in SOM["chapitres"] if c.get("etat") == "v3" and c["id"] in publies["fr"]]
for cid in v3:
    for l in ("fr", "en"):
        f = (SRC / l / f"{cid}.html").read_text("utf-8")
        check(f"6.1 [{l}] {cid} : aucun emoji ni glyphe en guise d'icône", not EMOJI.search(f), EMOJI.findall(f)[:8])
        check(f"6.2 [{l}] {cid} : pas de capture fixe héritée (img.shot) — des scènes", 'class="shot"' not in f)
print(f"  ({len(v3)} chapitre(s) en état v3, {len(publies['fr']) - len(v3)} migré(s) de la v2.8.0)")


def _corpus(lang):
    """Les textes que l'utilisateur peut LIRE à l'écran : dictionnaires i18n de la langue, et en français les sources
    de l'interface (bundle React, pages des labs) dont le français est la langue de référence."""
    morceaux = []
    for f in (RACINE / "frontend/shared/i18n").glob("*.json"):
        for v in json.loads(f.read_text("utf-8")).values():
            if isinstance(v, dict) and v.get(lang):
                morceaux.append(v[lang])
    if lang == "fr":
        for motif in ("frontend/dist/assets/index-*.js", "frontend/*/index.html", "frontend/*/*.js", "frontend/shared/*.js"):
            morceaux += [p.read_text("utf-8", errors="replace") for p in RACINE.glob(motif)]
    else:
        for motif in ("frontend/dist/assets/index-*.js",):
            morceaux += [p.read_text("utf-8", errors="replace") for p in RACINE.glob(motif)]
        # labs PAS ENCORE traduits : en anglais, l'écran montre encore leurs libellés français (le guide le dit)
        for lab in NON_TRADUITS:
            morceaux += [p.read_text("utf-8", errors="replace") for p in (RACINE / "frontend" / lab).glob("*.*")
                         if p.suffix in (".js", ".html")]
    # la planche des icônes du guide a ses propres boutons (filtres de famille, Imprimer) : ils existent aussi à l'écran
    p = GUIDE / f"lexique-icones-{lang}.html"
    if p.is_file():
        morceaux.append(p.read_text("utf-8"))
    return "\n".join(morceaux).replace("’", "'")


NON_TRADUITS = ("atelier",)                    # à retirer quand le lab passe par les lots Traduction
CORPUS = {l: _corpus(l) for l in ("fr", "en")}
TOLERES = {"Deepotus Video Gen", "FR", "EN"}            # nom de l'icône du Bureau ; boutons de langue du pied du rail
for cid in v3:
    for l in ("fr", "en"):
        f = (SRC / l / f"{cid}.html").read_text("utf-8")
        absents = sorted({u for u in (html_unescape(x).replace("’", "'") for x in re.findall(r'<b class="ui">(.*?)</b>', f))
                          if u not in TOLERES and u not in CORPUS[l]})
        check(f"6.3 [{l}] {cid} : chaque libellé d'interface cité existe à l'écran", not absents, absents)

print("\n[7] lexique imprimable des icônes (t170)")
LEX = {e["cle"]: e for e in json.loads((RACINE / "docs/icones/suite-finale/lexique.json").read_text("utf-8"))}
TXT = {}
for f in sorted((SRC / "lexique").glob("*.json")):
    TXT.update(json.loads(f.read_text("utf-8")))
check("7.1 chaque icône de la suite (526) a un nom et une fonction en FR et en EN",
      set(TXT) == set(LEX) and all(TXT[k][c][l].strip() for k in TXT for c in ("nom", "fonction") for l in ("fr", "en")),
      (len(TXT), len(LEX), sorted(set(LEX) ^ set(TXT))[:5]))
check("7.2 aucune fonction ne dépasse 14 mots (une planche se lit d'un coup d'œil)",
      all(len(TXT[k]["fonction"][l].split()) <= 14 for k in TXT for l in ("fr", "en")))
check("7.3 aucune entité HTML ni glyphe d'interface dans les textes du lexique",
      not any("&amp;" in json.dumps(v, ensure_ascii=False) for v in TXT.values()))
for l in ("fr", "en"):
    p = GUIDE / f"lexique-icones-{l}.html"
    h = p.read_text("utf-8") if p.is_file() else ""
    check(f"7.4 [{l}] la planche montre les {len(LEX)} icônes, chacune avec son dessin",
          h.count('<article class="lx-ic"') == len(LEX) and h.count('<span class="pic"><span class="dzi"') +
          h.count('<span class="pic"><img class="dzi') == len(LEX), h.count('<article class="lx-ic"'))
    check(f"7.5 [{l}] la planche a sa feuille d'impression A4 et son bouton Imprimer",
          "@page { size:A4" in h and "window.print()" in h)
    check(f"7.6 [{l}] le chapitre « Lire les icônes » mène à la planche et au PDF de SA langue",
          f'href="lexique-icones-{l}.html"' in PAGES[l] and f'href="Deepotus-Icones-{l.upper()}.pdf"' in PAGES[l])
    check(f"7.7 [{l}] le PDF de la planche existe", (GUIDE / f"Deepotus-Icones-{l.upper()}.pdf").is_file())
fiches = {f"{lab}/{e['id']}" for lab in ("vectorlab", "photolab", "spritelab", "tilelab")
          for e in json.loads((RACINE / "frontend" / lab / "aide" / "index.json").read_text("utf-8"))}
citees = set(re.findall(r'data-fiche="([^"]+)"', (SRC / "fr" / "icones.html").read_text("utf-8")))
check(f"7.8 la galerie du chapitre montre TOUTES les fiches animées des labs ({len(fiches)})", citees == fiches,
      sorted(fiches ^ citees))
en = json.loads((SRC / "fiches-en.json").read_text("utf-8"))
idx_en = {f"{lab}/{e['id']}": e for lab in ("vectorlab", "photolab", "spritelab", "tilelab")
          for e in json.loads((RACINE / "frontend" / lab / "aide" / "index.json").read_text("utf-8"))}
sans_en = sorted(f for f in fiches if not idx_en[f].get("titre_en") and not (f in en and en[f]["titre"] and en[f]["phrase"]))
check("7.9 chaque fiche a son titre et sa phrase en anglais (ceux du lab d'abord, sinon src/fiches-en.json)",
      not sans_en, sans_en)
doublons = sorted(f for f in en if f in idx_en and idx_en[f].get("titre_en"))
check("7.10 src/fiches-en.json ne double pas une fiche que son lab a traduite (le lab fait foi)", not doublons, doublons)

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
