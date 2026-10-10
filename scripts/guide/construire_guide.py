# -*- coding: utf-8 -*-
"""Construit le guide utilisateur v3 (skill guide-deepotus) depuis docs/guide/src/.

Entrées : src/chapitres.json (sommaire), src/{fr,en}/<id>.html (fragments), src/scenes/<chap>/<scene>/scene.json
(+ captures), src/gabarit/guide.{css,js}, frontend/shared/icons/dz-icons.js (icônes), frontend/<lab>/aide/index.json
(fiches animées), backend/app/config.py (APP_VERSION : la version s'écrit ICI, plus jamais à la main).
Sorties : docs/guide/fr.html, en.html, index.html (redirige selon la langue de l'app), img/scenes/…, img/fiches/….

    python scripts/guide/construire_guide.py           écrit les sorties
    python scripts/guide/construire_guide.py --check   code 1 si une sortie n'est pas à jour (texte comparé en LF)
    python scripts/guide/construire_guide.py --pdf     écrit puis imprime Deepotus-Guide-FR.pdf / -EN.pdf (Edge headless)

Dans un fragment :
  <i data-dz="dz-nav-montage"></i>                        icône de l'app (SVG en ligne, décorative)
  <figure class="scene" data-scene="montage/couper"></figure>   scène animée (captures + repères, voir motion.md)
  <figure class="fiche" data-fiche="vectorlab/<id>"></figure>   fiche animée d'un lab (WebP 320×200)
Un chapitre sans fragment n'est pas publié ; les anciens ancres (c0…c21) deviennent des alias.
"""
import html
import json
import pathlib
import re
import shutil
import subprocess
import sys
import unicodedata

RACINE = pathlib.Path(__file__).resolve().parents[2]
GUIDE = RACINE / "docs" / "guide"
SRC = GUIDE / "src"
LANGS = ("fr", "en")

TXT = {
    "fr": {"titre": "Guide de Deepotus Video Gen", "court": "Guide", "chercher": "Chercher dans le guide",
           "autre": "English", "autre_titre": "Read this guide in English", "theme": "Changer de thème",
           "imprimer": "Imprimer", "menu": "Sommaire", "dans": "Dans ce chapitre",
           "chapeau": "Tout ce que vous pouvez faire avec l'application, une tâche à la fois : des étapes courtes, "
                      "des images animées tirées de l'application, et les icônes que vous verrez à l'écran.",
           "pied": "Deepotus Video Gen {v} — guide construit depuis l'application réelle. Tout fonctionne en local sur "
                   "votre machine ; seuls les appels aux fournisseurs (fal.ai, HeyGen, ElevenLabs…) passent par "
                   "Internet, avec vos propres clés.",
           "pause": "Pause", "fiche": "Fiche animée"},
    "en": {"titre": "Deepotus Video Gen guide", "court": "Guide", "chercher": "Search the guide",
           "autre": "Français", "autre_titre": "Lire ce guide en français", "theme": "Switch theme",
           "imprimer": "Print", "menu": "Contents", "dans": "In this chapter",
           "chapeau": "Everything you can do with the app, one task at a time: short steps, animated pictures taken "
                      "from the real app, and the icons you will see on screen.",
           "pied": "Deepotus Video Gen {v} — guide built from the real app. Everything runs locally on your machine; "
                   "only calls to providers (fal.ai, HeyGen, ElevenLabs…) go over the Internet, with your own keys.",
           "pause": "Pause", "fiche": "Animated card"},
}


def version():
    m = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', (RACINE / "backend/app/config.py").read_text("utf-8"), re.M)
    return "v" + m.group(1)


def icones():
    js = (RACINE / "frontend/shared/icons/dz-icons.js").read_text("utf-8")
    return {k: json.loads(v) for k, v in re.findall(r'^\s*"(dz-[a-z0-9-]+)":\s*("(?:[^"\\]|\\.)*")', js, re.M)}


ICO = None
ANCRES_FR = {}


def svg(cle, titre=None):
    if cle.startswith("dz-marque-") and cle not in ICO:
        # les icônes de marque sont des IMAGES dans l'app (le logo du kit actif) : le guide montre le logo par défaut
        return f'<img class="dzi dzi-logo" src="img/logo.png" alt="{html.escape(titre or "")}">'
    if cle not in ICO:
        raise SystemExit(f"icône inconnue : {cle}")
    s = ICO[cle].replace("<svg ", '<svg focusable="false" ', 1)
    if titre:
        return f'<span class="dzi" role="img" aria-label="{html.escape(titre)}">{s}</span>'
    return f'<span class="dzi" aria-hidden="true">{s}</span>'


def masque(cle):
    s = ICO[cle].replace('"', "'").replace("#", "%23").replace("\n", " ")
    return f'url("data:image/svg+xml;utf8,{s}")'


def slug(t):
    t = unicodedata.normalize("NFD", re.sub(r"<[^>]+>", "", html.unescape(t))).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:48] or "s"


def texte(h):
    h = re.sub(r"<(script|style)\b.*?</\1>", " ", h, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h))).strip()


def ecrire_si_change(chemin, contenu, sorties):
    sorties[chemin] = contenu


def copier(src, dst, sorties):
    sorties[dst] = src.read_bytes()


# ── scènes et fiches ─────────────────────────────────────────────────────────
def scene(ref, lang, sorties):
    dossier = SRC / "scenes" / ref
    d = json.loads((dossier / "scene.json").read_text("utf-8"))
    imgs = []
    for k, cap in enumerate(d["captures"]):
        src = dossier / (cap[lang] if isinstance(cap, dict) else cap)
        nom = f"img/scenes/{ref}/{src.name}"
        copier(src, GUIDE / nom, sorties)
        cls = ["vu"] if k == 0 else []
        if k == max(t["capture"] for t in d["temps"]):
            cls.append("fin")
        imgs.append(f'<img src="{nom}" alt="" loading="lazy" width="{d["taille"][0]}" height="{d["taille"][1]}"'
                    + (f' class="{" ".join(cls)}"' if cls else "") + ">")
    barres = "".join(f'<button type="button" aria-label="{k + 1}"><i></i></button>' for k in range(len(d["temps"])))
    trois = "".join(
        f'<figure><img src="img/scenes/{ref}/{pathlib.Path(d["captures"][t["capture"]] if not isinstance(d["captures"][t["capture"]], dict) else d["captures"][t["capture"]][lang]).name}" alt="" loading="lazy">'
        f'<figcaption>{k + 1}. {t["bulle"][lang] if t.get("bulle") else ""}</figcaption></figure>'
        for k, t in enumerate(d["temps"]))
    donnees = json.dumps({"taille": d["taille"], "temps": d["temps"]}, ensure_ascii=False).replace("</", "<\\/")
    leg = d.get("legende", d.get("titre", {})).get(lang, "")
    return (f'<figure class="scene" data-scene="{ref}"><div class="cadre">{"".join(imgs)}'
            f'<button type="button" class="g-btn pause" title="{TXT[lang]["pause"]}" aria-pressed="false">'
            f'{svg("dz-media-pause")}</button></div><div class="temps">{barres}</div>'
            f'<div class="trois">{trois}</div><figcaption>{leg}</figcaption>'
            f'<script type="application/json">{donnees}</script></figure>')


def fiche(ref, lang, sorties):
    lab, ident = ref.split("/", 1)
    idx = json.loads((RACINE / "frontend" / lab / "aide" / "index.json").read_text("utf-8"))
    entrees = idx if isinstance(idx, list) else idx.get("fiches", idx)
    if isinstance(entrees, dict):
        e = entrees[ident]
    else:
        e = next(x for x in entrees if x.get("id") == ident)
    img = e.get("webp") or e.get("image") or e.get("fichier")
    src = RACINE / "frontend" / lab / "aide" / pathlib.Path(img).name
    nom = f"img/fiches/{lab}/{src.name}"
    copier(src, GUIDE / nom, sorties)
    titre = e.get("titre", ident) if isinstance(e.get("titre"), str) else e["titre"].get(lang, ident)
    phrase = e.get("phrase", "") if isinstance(e.get("phrase", ""), str) else e["phrase"].get(lang, "")
    return (f'<figure class="fiche" data-fiche="{ref}"><img src="{nom}" alt="{html.escape(TXT[lang]["fiche"])} : '
            f'{html.escape(titre)}" loading="lazy" width="320" height="200"><figcaption><b>{html.escape(titre)}</b>'
            f'{html.escape(phrase)}</figcaption></figure>')


# ── un chapitre ──────────────────────────────────────────────────────────────
def chapitre(c, fam, lang, sorties, index):
    frag = (SRC / lang / f"{c['id']}.html").read_text("utf-8").replace("\r\n", "\n")
    frag = re.sub(r'<i data-dz="([a-z0-9-]+)"(?: data-titre="([^"]*)")?></i>',
                  lambda m: svg(m.group(1), m.group(2)), frag)
    frag = re.sub(r'<figure class="scene" data-scene="([^"]+)"></figure>', lambda m: scene(m.group(1), lang, sorties), frag)
    frag = re.sub(r'<figure class="fiche" data-fiche="([^"]+)"></figure>', lambda m: fiche(m.group(1), lang, sorties), frag)
    vus = set(re.findall(r'\bid="([^"]+)"', frag))
    # les ancres des sections sont celles du FRANÇAIS, au même rang dans l'anglais : la bascule de langue garde
    # la section lue (le banc garantit le même squelette dans les deux langues)
    if lang == "fr":
        francais = [slug(t) for t in re.findall(r"<h3[^>]*>(.*?)</h3>", frag, re.S)]
        ANCRES_FR[c["id"]] = francais
    rang = iter(ANCRES_FR.get(c["id"], []))

    def h3(m):
        attrs, corps = m.group(1), m.group(2)
        i = re.search(r'id="([^"]+)"', attrs)
        ident = i.group(1) if i else f"{c['id']}-{next(rang, None) or slug(corps)}"
        if i:
            next(rang, None)
        while not i and ident in vus:
            ident += "-2"
        vus.add(ident)
        if not i:
            attrs += f' id="{ident}"'
        return f'<h3{attrs}>{corps}<a class="ancre" href="#{ident}" aria-label="#">#</a></h3>'
    frag = re.sub(r"<h3([^>]*)>(.*?)</h3>", h3, frag, flags=re.S)
    alias = "".join(f'<span class="alias" id="{a}"></span>' for a in c["anciens"] if a not in vus)
    titre = c[lang]
    # index de recherche : le chapitre, puis chacune de ses sections h3
    parts = re.split(r'(?=<h3[^>]*\bid=")', frag)
    index.append({"c": titre, "t": titre, "a": c["id"], "x": texte(parts[0])[:900]})
    for p in parts[1:]:
        m = re.match(r'<h3[^>]*\bid="([^"]+)"[^>]*>(.*?)</h3>', p, re.S)
        index.append({"c": titre, "t": texte(m.group(2)).rstrip("#").strip(), "a": m.group(1), "x": texte(p[m.end():])[:900]})
    return (f'<section class="chapitre" id="{c["id"]}" style="--fam:var({fam["couleur"]})" data-etat="{c.get("etat", "v3")}">'
            f'{alias}<header><span class="pastille">{svg(c["icone"])}</span><span class="famille">{fam[lang]}</span>'
            f'<h2>{html.escape(titre)}<a class="ancre" href="#{c["id"]}" aria-label="#">#</a></h2></header>\n'
            f"{frag.strip()}\n</section>")


def page(som, lang, sorties):
    t, v = TXT[lang], version()
    autre = "en" if lang == "fr" else "fr"
    familles = {f["id"]: f for f in som["familles"]}
    publies = [c for c in som["chapitres"] if (SRC / lang / f"{c['id']}.html").is_file()]
    index, sections, nav, cartes, fam_cour = [], [], [], [], None
    for c in publies:
        f = familles[c["famille"]]
        sections.append(chapitre(c, f, lang, sorties, index))
        if c["famille"] != fam_cour:
            fam_cour = c["famille"]
            nav.append(f'<h2 style="--fam:var({f["couleur"]})">{f[lang]}</h2>')
        nav.append(f'<a href="#{c["id"]}" style="--fam:var({f["couleur"]})">{svg(c["icone"])}<span>{html.escape(c[lang])}</span></a>')
        cartes.append(f'<a href="#{c["id"]}" style="--fam:var({f["couleur"]})">{svg(c["icone"])}<b>{html.escape(c[lang])}</b></a>')
    css = (SRC / "gabarit/guide.css").read_text("utf-8")
    css += f':root{{--m-info:{masque("dz-etat-information")};--m-alerte:{masque("dz-etat-avertissement")}}}'
    js = (SRC / "gabarit/guide.js").read_text("utf-8")
    idx = json.dumps(index, ensure_ascii=False).replace("</", "<\\/")
    corps = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t["titre"]} {v}</title>
<meta name="description" content="{html.escape(t["chapeau"])}">
<link rel="alternate" hreflang="{autre}" href="{autre}.html">
<style>{css}</style>
</head>
<body>
<header class="g-top">
<button type="button" class="g-btn g-menu" id="g-menu" aria-expanded="false" aria-controls="g-nav" title="{t["menu"]}">{svg("dz-action-menu")}</button>
<a class="g-marque" href="#accueil">{svg("dz-marque-poulpe")}<span>Deepotus · {t["court"]}</span><small>{v}</small></a>
<div class="g-cherche" role="search">{svg("dz-action-chercher")}<input id="g-q" type="search" placeholder="{t["chercher"]}" aria-label="{t["chercher"]}" autocomplete="off"><kbd>/</kbd><div class="g-res" role="listbox"></div></div>
<a class="g-btn" id="g-lang" href="{autre}.html" hreflang="{autre}" title="{t["autre_titre"]}"><span class="txt">{t["autre"]}</span><span aria-hidden="true">{autre.upper()}</span></a>
<button type="button" class="g-btn" id="g-theme" title="{t["theme"]}">{svg("dz-action-theme")}</button>
<button type="button" class="g-btn" onclick="window.print()" title="{t["imprimer"]}">{svg("dz-nav-cf-impression")}</button>
</header>
<div class="g-corps">
<nav class="g-nav" id="g-nav" aria-label="{t["menu"]}">{"".join(nav)}</nav>
<main>
<section class="g-accueil" id="accueil">
<h1>{t["titre"]}</h1>
<p class="chapeau">{t["chapeau"]}</p>
<div class="g-cartes-acc">{"".join(cartes)}</div>
</section>
{chr(10).join(sections)}
<div class="footer">{t["pied"].format(v=v)}</div>
</main>
<aside class="g-toc" aria-label="{t["dans"]}"><b>{t["dans"]}</b><ol></ol></aside>
</div>
<script type="application/json" id="g-index">{idx}</script>
<script>{js}</script>
</body>
</html>
"""
    sorties[GUIDE / f"{lang}.html"] = corps


INDEX = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Deepotus — Guide</title>
<script>
/* La langue du guide suit celle de l'application (dz_lang, puis dz_lang_install, puis le navigateur). */
(function () {
  var l = null;
  try { l = localStorage.getItem("dz_lang") || localStorage.getItem("dz_lang_install"); } catch (e) {}
  if (l !== "fr" && l !== "en") l = /^fr\\b/i.test(navigator.language || "fr") ? "fr" : "en";
  location.replace(l + ".html" + location.hash);
})();
</script>
</head>
<body style="background:#0a0a0c;color:#f2efe9;font-family:system-ui,sans-serif;padding:24px">
<p><a href="fr.html" style="color:#f0b429">Guide en français</a> · <a href="en.html" style="color:#f0b429">English guide</a></p>
</body>
</html>
"""


def construire():
    global ICO
    ICO = icones()
    som = json.loads((SRC / "chapitres.json").read_text("utf-8"))
    sorties = {}
    for lang in LANGS:
        page(som, lang, sorties)
    sorties[GUIDE / "index.html"] = INDEX
    copier(SRC / "gabarit/logo.png", GUIDE / "img/logo.png", sorties)
    return sorties


def norm(x):
    return x.replace(b"\r\n", b"\n") if isinstance(x, bytes) else x.replace("\r\n", "\n").encode("utf-8")


def imprimer():
    edge = next((p for p in (pathlib.Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
                             pathlib.Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
                             pathlib.Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")) if p.is_file()), None)
    if not edge:
        raise SystemExit("ni Edge ni Chrome : impossible d'imprimer le PDF")
    import tempfile
    import time
    for lang in LANGS:
        pdf = GUIDE / f"Deepotus-Guide-{lang.upper()}.pdf"
        avant = time.time()
        # Edge rend la main AVANT d'avoir écrit le PDF (son processus d'impression continue en fond : constaté le
        # 10/10, retour en 0,5 s et fichier écrit après) → profil jetable, puis on ATTEND un fichier neuf et stable
        with tempfile.TemporaryDirectory(prefix="dzguide_edge_", ignore_cleanup_errors=True) as profil:
            subprocess.run([str(edge), "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={profil}",
                            "--no-pdf-header-footer", "--virtual-time-budget=6000", f"--print-to-pdf={pdf}",
                            (GUIDE / f"{lang}.html").as_uri()], check=True, capture_output=True, timeout=300)
            taille, fin = -1, time.time() + 180
            while time.time() < fin:
                if pdf.is_file() and pdf.stat().st_mtime >= avant:
                    t = pdf.stat().st_size
                    if t == taille and t > 0:
                        break
                    taille = t
                time.sleep(1.5)
            else:
                raise SystemExit(f"le PDF {pdf.name} n'a pas été réécrit en 3 minutes")
        print(f"PDF : {pdf.relative_to(RACINE)} ({pdf.stat().st_size // 1024} Ko)")


def main():
    sorties = construire()
    if "--check" in sys.argv:
        perimes = [str(p.relative_to(RACINE)) for p, c in sorties.items() if not p.is_file() or norm(p.read_bytes()) != norm(c)]
        print("à jour" if not perimes else "PÉRIMÉ : " + ", ".join(perimes) + " — relancer python scripts/guide/construire_guide.py")
        return 1 if perimes else 0
    for p, c in sorties.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(c, bytes):
            p.write_bytes(c)
        else:
            p.write_text(c, "utf-8", newline="\n")
    print(f"écrit : {len(sorties)} fichiers ({', '.join(p.name for p in sorties if p.suffix == '.html')})")
    if "--pdf" in sys.argv:
        imprimer()
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
