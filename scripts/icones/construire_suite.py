# -*- coding: utf-8 -*-
"""Construit la suite d'icônes « Deepotus Glyph » servie à toute l'application.

Entrées (docs/icones/) :
  suite-finale/svg/dz-*.svg      la refonte (une icône par fonction)
  suite-finale/choix/dz-*.svg    les dessins que l'utilisateur a préférés à la refonte
  choix-utilisateur.json         ses choix (option « refonte » | « kit:<clé> » | « actuel:<clé> »)
  nouvelle-suite/dz-*.svg        le kit reçu (pour les choix « kit: »)

Sorties (identiques octet pour octet dans frontend/shared/icons et frontend/dist/shared/icons) :
  dz-icons.svg   sprite : un <symbol id="dz-…"> par icône dessinée
  dz-icons.js    window.DZ_ICONS (clé -> SVG autonome), window.DZ_ICONS_IMAGES (clé -> URL)
                 et window.dzIcone(cle, {taille, titre, classe}) -> balisage prêt à poser
  dz-icons.css   la classe .dzi (taille, couleur héritée)

Usage : python scripts/icones/construire_suite.py [--check]
  --check : ne réécrit rien, sort en 1 si une sortie diffère de ce que le générateur produirait.
"""
import json
import pathlib
import re
import sys

RACINE = pathlib.Path(__file__).resolve().parents[2]
DOCS = RACINE / "docs" / "icones"
SORTIES = [RACINE / "frontend" / "shared" / "icons", RACINE / "frontend" / "dist" / "shared" / "icons"]

# Choix « actuel: » qui désignent une IMAGE de l'application et non un dessin : la clé
# est servie par cette URL (balise <img>) au lieu d'un glyphe.
IMAGES = {
    "logo-marque": "/api/branding/logo",
    "splash-jpg": "/assets/dz-splash.jpg",
}


def lire_svg(p):
    t = p.read_text(encoding="utf-8").strip()
    if "<script" in t.lower() or re.search(r"\son\w+=", t):
        raise SystemExit(f"SVG refusé (script ou gestionnaire) : {p}")
    # la taille vient de l'emploi (dzIcone, CSS) : jamais du fichier
    tete, reste = t.split(">", 1)
    tete = re.sub(r'\s(?:width|height)="[^"]*"', "", tete)
    return tete + ">" + reste


def interieur(svg):
    """Le contenu de la balise <svg> et ses attributs de présentation utiles au <symbol>."""
    m = re.match(r"<svg([^>]*)>(.*)</svg>$", svg, re.S)
    if not m:
        raise SystemExit("SVG mal formé : " + svg[:80])
    attrs = dict(re.findall(r'\s([\w:-]+)="([^"]*)"', m.group(1)))
    garder = {k: v for k, v in attrs.items()
              if k in ("fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin")}
    return garder, m.group(2)


def construire():
    choix = json.loads((DOCS / "choix-utilisateur.json").read_text(encoding="utf-8"))
    refonte = {p.stem: p for p in sorted((DOCS / "suite-finale" / "svg").glob("dz-*.svg"))}
    kit = {p.stem: p for p in sorted((DOCS / "nouvelle-suite").glob("dz-*.svg")) if p.stem != "dz-icons"}
    perso = {p.stem: p for p in sorted((DOCS / "suite-finale" / "choix").glob("dz-*.svg"))}
    icones, images, origine = {}, {}, {}
    for cle, chemin in refonte.items():
        opt = (choix.get(cle) or {}).get("option") or "refonte"
        if opt == "refonte":
            icones[cle] = lire_svg(chemin); origine[cle] = "refonte"
        elif opt.startswith("kit:"):
            icones[cle] = lire_svg(kit[opt[4:]]); origine[cle] = opt
        elif opt.startswith("actuel:"):
            nom = opt[7:]
            if nom in IMAGES:
                images[cle] = IMAGES[nom]; origine[cle] = opt
            elif cle in perso:
                icones[cle] = lire_svg(perso[cle]); origine[cle] = opt
            else:
                raise SystemExit(f"{cle} : choix {opt} sans dessin dans suite-finale/choix/")
        else:
            raise SystemExit(f"{cle} : option inconnue {opt!r}")
    inconnus = sorted(set(choix) - set(refonte))
    if inconnus:
        raise SystemExit(f"choix pour des clés absentes de la suite : {inconnus}")

    syms = []
    for cle, svg in icones.items():
        attrs, corps = interieur(svg)
        attrs.setdefault("fill", "currentColor")
        a = "".join(f' {k}="{v}"' for k, v in attrs.items())
        syms.append(f'<symbol id="{cle}" viewBox="0 0 24 24"{a}>{corps}</symbol>')
    sprite = ('<svg xmlns="http://www.w3.org/2000/svg" style="display:none">\n'
              + "\n".join(syms) + "\n</svg>\n")

    js = (
        "/* Deepotus Glyph — généré par scripts/icones/construire_suite.py : ne pas éditer à la main.\n"
        "   Licences : dessins Deepotus ; dz-reseau-* = simple-icons (CC0, marques de leurs propriétaires) ;\n"
        "   dz-outil-photo-doigt = Lucide (ISC, frontend/photolab/icones/LICENSE-lucide.txt).\n"
        "   window.dzIcone(cle, {taille, titre, classe}) rend le balisage d'une icône ;\n"
        "   sans titre, l'icône est décorative (aria-hidden) : le sens est porté par le bouton. */\n"
        "(function () {\n"
        "  var I = " + json.dumps(icones, ensure_ascii=False, indent=0, sort_keys=True) + ";\n"
        "  var IMG = " + json.dumps(images, ensure_ascii=False, sort_keys=True) + ";\n"
        "  function esc(t) { return String(t).replace(/[&<>\"]/g, function (c) {\n"
        "    return { \"&\": \"&amp;\", \"<\": \"&lt;\", \">\": \"&gt;\", '\"': \"&quot;\" }[c]; }); }\n"
        "  function dzIcone(cle, o) {\n"
        "    o = o || {};\n"
        "    var t = o.taille || 16, cl = \"dzi\" + (o.classe ? \" \" + o.classe : \"\");\n"
        "    var aria = o.titre ? ' role=\"img\" aria-label=\"' + esc(o.titre) + '\"' : ' aria-hidden=\"true\" focusable=\"false\"';\n"
        "    if (IMG[cle]) return '<img class=\"' + cl + '\" src=\"' + IMG[cle] + '\" width=\"' + t + '\" height=\"' + t + '\" alt=\"' + (o.titre ? esc(o.titre) : \"\") + '\">';\n"
        "    var s = I[cle];\n"
        "    if (!s) { if (window.console) window.console.warn(\"dzIcone : clé inconnue \" + cle); return \"\"; }\n"
        "    return s.replace(\"<svg\", '<svg class=\"' + cl + '\" width=\"' + t + '\" height=\"' + t + '\"' + aria);\n"
        "  }\n"
        "  window.DZ_ICONS = I;\n"
        "  window.DZ_ICONS_IMAGES = IMG;\n"
        "  window.dzIcone = dzIcone;\n"
        "})();\n"
    )
    css = (
        "/* Deepotus Glyph — généré par scripts/icones/construire_suite.py */\n"
        ".dzi{display:inline-block;width:1em;height:1em;vertical-align:-.125em;flex:none;color:inherit}\n"
        "svg.dzi:not([fill=\"none\"]){fill:currentColor}\n"
        ".dzi--16{width:16px;height:16px}.dzi--18{width:18px;height:18px}.dzi--20{width:20px;height:20px}.dzi--24{width:24px;height:24px}\n"
        "img.dzi{object-fit:contain}\n"
    )
    return {"dz-icons.svg": sprite, "dz-icons.js": js, "dz-icons.css": css}, origine


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sorties, origine = construire()
    verif = "--check" in sys.argv
    ecarts = []
    for dossier in SORTIES:
        for nom, texte in sorties.items():
            p = dossier / nom
            octets = texte.encode("utf-8")
            if verif:
                if not p.exists() or p.read_bytes().replace(b"\r\n", b"\n") != octets:
                    ecarts.append(str(p.relative_to(RACINE)))
            else:
                dossier.mkdir(parents=True, exist_ok=True)
                p.write_bytes(octets)
    if verif:
        if ecarts:
            print("À régénérer :", *ecarts, sep="\n  ")
            sys.exit(1)
        print("OK — suite à jour.")
        return
    n = {}
    for v in origine.values():
        n[v.split(":")[0]] = n.get(v.split(":")[0], 0) + 1
    print(f"OK — {len(origine)} clés ({n}) écrites dans", ", ".join(str(d.relative_to(RACINE)) for d in SORTIES))


if __name__ == "__main__":
    main()
