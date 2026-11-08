# -*- coding: utf-8 -*-
"""t433 (lot M0 « Méthodes », 08/11/2026) — construit backend/app/knowledge/methodes.json, le catalogue bilingue des
méthodes, à partir des fiches du relevé Scenario (docs/superpowers/specs/assets/2026-11-08-scenario-explorations/
fiches.json, textes rédigés par nous) et de leur anglais (fiches_en.json, même dossier).

Conception validée : docs/superpowers/specs/2026-11-08-scenario-explorations-agents-design.md (§3 les 9 agents
métier, §5 où les méthodes apparaissent). Aucun texte ni média de Scenario n'est copié : chaque fiche garde un lien
« source » vers la page d'origine et, pour les skills sous licence MIT, la mention `licence_skill`.

Run : python scripts/methodes_construire.py [--check]   (--check : échoue si le fichier versionné n'est pas à jour)
"""
from __future__ import annotations

import json
import pathlib
import sys

RACINE = pathlib.Path(__file__).resolve().parent.parent
SRC = RACINE / "docs" / "superpowers" / "specs" / "assets" / "2026-11-08-scenario-explorations"
SORTIE = RACINE / "backend" / "app" / "knowledge" / "methodes.json"

FAMILLES = {
    "previs-blender": ("Previs Blender → image finale", "Blender previs → final picture"),
    "film-agent-blender": ("Film fabriqué dans Blender", "Film built in Blender"),
    "video-edit-chaine": ("Édition vidéo en chaîne", "Chained video edits"),
    "video-personnage-voix": ("Personnages, jeu et voix", "Characters, acting and voice"),
    "motion-code": ("Motion design en code", "Motion design in code"),
    "pub-marketing": ("Publicités et formats courts", "Ads and short formats"),
    "produit-ecommerce": ("Produit et e-commerce", "Product and e-commerce"),
    "mode-beaute": ("Mode", "Fashion"),
    "image-edit-reference": ("Retouche et références", "Edits and references"),
    "game-assets-2d": ("Assets de jeu 2D", "2D game assets"),
    "game-assets-3d": ("Assets de jeu 3D", "3D game assets"),
    "jeu-jouable": ("Jeux jouables", "Playable games"),
    "monde-3d-interactif": ("Mondes 3D interactifs", "Interactive 3D worlds"),
    "benchmark-modeles": ("Comparatifs de modèles", "Model comparisons"),
    "livre-illustre-educatif": ("Livre illustré et pédagogie", "Picture books and explainers"),
}

# §3 de la conception : l'agent métier qui portera la méthode, et la tâche du suivi qui le livre.
AGENTS = {
    "realisateur": {"fr": "Réalisateur", "en": "Director", "tache": "t436", "lot": "M3",
                    "role_fr": "Met en scène dans Blender et tient la continuité d'un plan à l'autre.",
                    "role_en": "Stages shots in Blender and keeps continuity from shot to shot.",
                    "familles": ["previs-blender", "film-agent-blender"]},
    "monteur": {"fr": "Monteur", "en": "Editor", "tache": "t435", "lot": "M2",
                "role_fr": "Monte, étalonne et retouche une prise en chaîne, titres posés en code.",
                "role_en": "Cuts, grades and edits a take step by step, with titles set in code.",
                "familles": ["video-edit-chaine", "motion-code"]},
    "directeur_acteurs": {"fr": "Directeur d'acteurs", "en": "Casting director", "tache": "t438", "lot": "M5",
                          "role_fr": "Dirige personnages, voix et doublage avec une identité stable.",
                          "role_en": "Directs characters, voices and dubbing with a stable identity.",
                          "familles": ["video-personnage-voix"]},
    "retoucheur": {"fr": "Retoucheur", "en": "Retoucher", "tache": "t437", "lot": "M4",
                   "role_fr": "Change une seule chose dans une image et vérifie que le reste n'a pas bougé.",
                   "role_en": "Changes one thing in a picture and checks that nothing else moved.",
                   "familles": ["image-edit-reference", "mode-beaute"]},
    "declinaisons": {"fr": "Déclinaisons produit", "en": "Product variations", "tache": "t437", "lot": "M4",
                     "role_fr": "Décline un produit exact en couleurs, mondes et visuels de boutique.",
                     "role_en": "Turns one exact product into colorways, worlds and shop visuals.",
                     "familles": ["produit-ecommerce"]},
    "publicitaire": {"fr": "Publicitaire", "en": "Ad maker", "tache": "t439", "lot": "M6",
                     "role_fr": "Fabrique pubs, bandes-annonces et formats courts calés sur le rythme.",
                     "role_en": "Makes ads, trailers and short formats cut to the beat.",
                     "familles": ["pub-marketing"]},
    "artiste_2d": {"fr": "Artiste 2D de jeu", "en": "2D game artist", "tache": "t440", "lot": "M7",
                   "role_fr": "Produit sprites, tuiles, effets et décors 2D prêts pour le moteur.",
                   "role_en": "Produces engine-ready sprites, tiles, effects and 2D sets.",
                   "familles": ["game-assets-2d"]},
    "artiste_3d": {"fr": "Artiste 3D de jeu", "en": "3D game artist", "tache": "t441", "lot": "M8",
                   "role_fr": "Produit modèles, pièces, matières et mondes 3D légers.",
                   "role_en": "Produces light 3D models, parts, materials and worlds.",
                   "familles": ["game-assets-3d", "monde-3d-interactif", "jeu-jouable"]},
    "editeur_illustre": {"fr": "Éditeur illustré", "en": "Picture-book editor", "tache": "t442", "lot": "M9",
                         "role_fr": "Compose albums et planches pédagogiques, texte posé en code.",
                         "role_en": "Lays out picture books and explainer plates, text set in code.",
                         "familles": ["livre-illustre-educatif"]},
    # §3 : les comparatifs ne forment pas un agent mais l'OUTIL transverse « Arbitre » (B6), livré avec M9
    "arbitre": {"fr": "Arbitre", "en": "Referee", "tache": "t442", "lot": "M9", "outil": True,
                "role_fr": "Outil commun : compare des modèles à armes égales, coût et temps notés.",
                "role_en": "Shared tool: compares models on equal terms, with cost and time logged.",
                "familles": ["benchmark-modeles"]},
}

# Écran de l'app (id stable) : libellés et vue de la barre des applications qui l'héberge.
ECRANS = {
    "quick": ("Quick", "Quick", "quick"), "studio": ("Studio", "Studio", "studio"),
    "episodes": ("Chapitres", "Chapters", "episodes"), "blender": ("Scène Blender", "Blender scene", "episodes"),
    "sonvfx": ("Son & VFX", "Sound & VFX", "sonvfx"), "montage": ("Montage", "Editing", "montage"),
    "templates": ("Modèles", "Templates", "templates"), "espaces": ("Espaces de marque", "Brand spaces", "settings"),
    "campagnes": ("Campagnes", "Campaigns", "settings"), "scheduler": ("Planificateur", "Scheduler", "scheduler"),
    "news": ("News", "News", "news"), "library": ("Bibliothèque", "Library", "library"),
    "photolab": ("Photolab", "Photolab", "photolab"), "vectorlab": ("Vectorlab", "Vectorlab", "vectorlab"),
    "avatarlive": ("Avatar live", "Avatar live", "avatarlive"),
    "assets2d": ("Assets 2D", "2D Assets", "assets3d"), "spritelab": ("Spritelab", "Spritelab", "assets3d"),
    "tilelab": ("Tilelab", "Tilelab", "assets3d"), "cardforge": ("Card Forge", "Card Forge", "assets3d"),
    "studio3d": ("Studio 3D", "3D Studio", "assets3d"), "etabli": ("Établi", "Workbench", "assets3d"),
    "matieres": ("Matières", "Materials", "assets3d"), "forge3d": ("Forge 3D", "3D Forge", "assets3d"),
    "lib3d": ("Lib3D", "Lib3D", "assets3d"),
}
_CIBLES = {
    "Scène Blender": ["blender"], "Montage": ["montage"], "Chapitres/Épisodes": ["episodes"], "Son & VFX": ["sonvfx"],
    "Studio": ["studio"], "Lib3D": ["lib3d"], "Studio 3D": ["studio3d"], "Assets 2D": ["assets2d"],
    "Templates": ["templates"], "Spritelab": ["spritelab"], "Forge 3D": ["forge3d"], "Campagnes": ["campagnes"],
    "Campagnes (agent marketing)": ["campagnes"], "Matières": ["matieres"], "Photolab": ["photolab"],
    "Établi": ["etabli"], "Studio 3D / Établi / Matières / Forge 3D": ["studio3d", "etabli", "matieres", "forge3d"],
    "Tilelab": ["tilelab"], "Espaces de marque": ["espaces"], "Vectorlab": ["vectorlab"], "Quick": ["quick"],
    "Avatar live": ["avatarlive"], "Planificateur social": ["scheduler"], "News/Veille": ["news"],
    "Bibliothèque": ["library"], "Card Forge": ["cardforge"],
}
_FILTRES = {"Play": ("Jouer", "Play"), "Watch": ("Regarder", "Watch"), "Explore": ("Explorer", "Explore"),
            "Create": ("Créer", "Create")}


def _agent_de(famille: str) -> str:
    return next(a for a, d in AGENTS.items() if famille in d["familles"])


def construire() -> dict:
    fiches = json.loads((SRC / "fiches.json").read_text(encoding="utf-8"))
    en = json.loads((SRC / "fiches_en.json").read_text(encoding="utf-8"))
    methodes = []
    for f in sorted(fiches, key=lambda x: (-x["valeur"], x["slug"])):
        e = en[f["slug"]]
        for cle in ("methode", "controles", "pieges", "exemples"):
            assert len(e[cle + "_en"]) == len(f[cle]), (f["slug"], cle)
        ecrans = []
        for c in f["cible_app"]:
            for i in _CIBLES[c]:
                if i not in ecrans:
                    ecrans.append(i)
        methodes.append({
            "slug": f["slug"], "famille": f["famille"], "agent": _agent_de(f["famille"]),
            "filtre": f["filtre"],
            "titre": {"fr": f["titre_fr"], "en": f["titre_en"]},
            "resume": {"fr": f["resume_fr"], "en": f["resume_en"]},
            "etapes": {"fr": f["methode"], "en": e["methode_en"]},
            "controles": {"fr": f["controles"], "en": e["controles_en"]},
            "pieges": {"fr": f["pieges"], "en": e["pieges_en"]},
            "exemples": {"fr": f["exemples"], "en": e["exemples_en"]},
            "illustration": {"fr": f["illustration"], "en": e["illustration_en"]},
            "ecrans": ecrans, "modeles": f["modeles_cites"], "equivalents": f["equivalents_app"],
            "valeur": f["valeur"], "effort": f["effort"],
            "licence_skill": f["licence_skill"], "source": f["source"],
        })
    agents = {a: dict({k: d[k] for k in ("fr", "en", "role_fr", "role_en", "familles", "tache", "lot")},
                      outil=bool(d.get("outil")))
              for a, d in AGENTS.items()}
    for a in agents:
        agents[a]["nb"] = sum(1 for m in methodes if m["agent"] == a)
    return {
        "version": 1,
        "source": {"nom": "Scenario Explorations", "url": "https://www.scenario.com/explorations",
                   "releve": "2026-11-08",
                   "note_fr": "Méthodes inspirées des explorations publiques de Scenario, réécrites par Deepotus ; "
                              "aucun texte ni média de Scenario n'est repris.",
                   "note_en": "Methods inspired by Scenario's public explorations, rewritten by Deepotus; "
                              "no Scenario text or media is reused."},
        "familles": {k: {"fr": v[0], "en": v[1]} for k, v in FAMILLES.items()},
        "filtres": {k: {"fr": v[0], "en": v[1]} for k, v in _FILTRES.items()},
        "ecrans": {k: {"fr": v[0], "en": v[1], "vue": v[2]} for k, v in ECRANS.items()},
        "agents": agents,
        "methodes": methodes,
    }


def texte(d: dict) -> str:
    return json.dumps(d, ensure_ascii=False, indent=1) + "\n"


def main() -> None:
    neuf = texte(construire())
    if "--check" in sys.argv:
        if not SORTIE.exists() or SORTIE.read_text(encoding="utf-8") != neuf:
            raise SystemExit("[methodes] knowledge/methodes.json pas à jour : python scripts/methodes_construire.py")
        print("[methodes] à jour")
        return
    SORTIE.write_text(neuf, encoding="utf-8", newline="\n")
    d = json.loads(neuf)
    print(f"[methodes] {len(d['methodes'])} méthodes, {len(d['agents'])} agents -> {SORTIE.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
