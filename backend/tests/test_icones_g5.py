# -*- coding: utf-8 -*-
"""Icônes G5 (10/10/2026) — la suite « Deepotus Glyph » posée dans le Spritelab et le Tilelab.

Liste de travail : docs/icones/suite-finale/implementation.json, entrées dont `source` est sous frontend/spritelab/
ou frontend/tilelab/ et qui portent une `cle_finale` (124 sites ; les 14 autres sont du texte seul, on n'y touche pas).

  [1] runtime : dz-icons.css et dz-icons.js chargés dans les deux pages, le script APRÈS /shared/dz-i18n.js et AVANT
      les modules du lab (feuille.js, tilelab.js…).
  [2] chaque site de la liste porte SA clé finale, à sa place (ancre propre au site : libellé, id, title) ; la table des
      ancres couvre exactement les sites du JSON, et la clé lue dans le JSON est celle qui est cherchée.
  [3] comptes par clé : nombre d'usages dans le périmètre = nombre de sites du JSON, aux écarts DÉCLARÉS près
      (aide de l'éditeur qui montre ses quatre boutons, aides partagées toastOk / playIcone) ; aucune autre clé.
  [4] plus aucun des anciens emojis / glyphes remplacés dans les fichiers du périmètre (commentaires retirés) ; les
      flèches et ≈ qui restent sont du texte relevé « texte seul » ou hors liste — vérifiés site par site.
  [5] chaque clé employée existe dans le sprite (statique) ou dans DZ_ICONS (dzIcone) ; CSS : ✖ du pseudo-élément remplacé,
      décalage d'un pixel orienté dans les quatre directions.
  [6] node --check des JS modifiés.
Run : & $PY tests/test_icones_g5.py   (depuis backend/)
"""
import collections, json, pathlib, re, shutil, subprocess, sys
import sys as _s9, pathlib as _p9; _s9.path.insert(0, str(_p9.Path(__file__).resolve().parent)); import _labs_avant_l9  # noqa: E402,F401  (t149 : Spritelab, Tile Lab, Studio3D, Plateau, lib3d d'avant la traduction L9)

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
FRONT = ROOT / "frontend"
NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label}  {str(detail)[:400]}")


FICHIERS = {
    "sh": "spritelab/index.html", "sj": "spritelab/spritelab.js", "sc": "spritelab/spritelab.css",
    "th": "tilelab/index.html", "tj": "tilelab/tilelab.js", "jj": "tilelab/jeu.js", "pj": "tilelab/peintre.js",
}


def lire(cle_f):
    return (FRONT / FICHIERS[cle_f]).read_text(encoding="utf-8")


def sans_commentaires(t, f):
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S) if f.endswith(".html") else t
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    if f.endswith(".js"):
        t = re.sub(r"(?m)(^|[^:\"'`])//[^\n]*", r"\1", t)
    return t


def STAT(k):
    return (r'<svg class="dzi dzi--\d+" aria-hidden="true" focusable="false"><use href="/shared/icons/dz-icons\.svg#'
            + re.escape(k) + r'"></use></svg>')


def DYN(k):
    return r'dzIcone\("' + re.escape(k) + r'", \{ taille: \d+ \}\)'


# id du site → (fichier, avant, après) : l'icône de la clé finale doit se trouver EXACTEMENT entre les deux.
# Pour les fichiers .js, `${…}` entoure l'icône dans un gabarit : il fait partie de l'avant / après.
A = {
    # ── Spritelab, page ──
    "spritelab.entete.marque": ("sh", '<div class="brand">', ' <b>Sprite Lab</b>'),
    "spritelab.entete.retour": ("sh", 'title="Retour à l\'app">', ' App</a>'),
    "spritelab.source.onglet-starter": ("sh", 'sans aucune clé API">', ' Démarrer</button>'),
    "spritelab.source.onglet-image": ("sh", 'sur fond uni">', ' Image</button>'),
    "spritelab.source.onglet-render": ("sh", 'render vidéo existant">', ' Render</button>'),
    "spritelab.source.onglet-upload": ("sh", 'vidéo de ton PC">', ' Vidéo</button>'),
    "spritelab.source.onglet-feuille": ("sh", 'tout en local">', ' Feuille</button>'),
    "spritelab.source.onglet-bible": ("sh", 'vient de la bible">', ' Bible</button>'),
    "spritelab.source.onglet-prompt": ("sh", 'pixeliser en local">', ' Prompt</button>'),
    "spritelab.source.recherche-imgSearch": ("sh", '<div class="search-wrap">', '<input id="imgSearch" class="search" placeholder="Filtrer les images…"></div>'),
    "spritelab.source.recherche-renderSearch": ("sh", '<div class="search-wrap">', '<input id="renderSearch" class="search" placeholder="Filtrer les renders…"></div>'),
    "spritelab.source.recherche-feuilleSearch": ("sh", '<div class="search-wrap">', '<input id="feuilleSearch" class="search" placeholder="Filtrer les planches de la Library…"></div>'),
    "spritelab.source.recherche-entSearch": ("sh", '<div class="search-wrap">', '<input id="entSearch" class="search" placeholder="Filtrer les personnages…"></div>'),
    "spritelab.image.animer": ("sh", 'extraction des frames">', ' Animer (Seedance, fond uni)</button>'),
    "spritelab.upload.choisir": ("sh", '<label class="btn" for="vidFile">', ' Choisir une vidéo (mp4/mov/webm)</label>'),
    "spritelab.feuille.ouvrir-png": ("sh", '<label class="btn" for="feuilleFile">', ' Ouvrir un PNG de mon PC</label>'),
    "spritelab.bible.quatre": ("sh", '(local, gratuit)">', ' 4 directions (planche)</button>'),
    "spritelab.bible.huit": ("sh", 'feuille de 8 directions (local, gratuit)">', ' 8 directions (modèle 3D)</button>'),
    "spritelab.prompt.generer": ("sh", 'comme source">', ' Générer les images</button>'),
    "spritelab.frames.tout": ("sh", 'title="Tout garder / tout enlever">', ' Tout</button>'),
    "spritelab.frames.reextraire": ("sh", 'ci-dessous (local, gratuit)">', ' Ré-extraire</button>'),
    "spritelab.animation.ajout-tag": ("sh", 'plage d\'images">', ' Tag</button>'),
    "spritelab.reglages.generer-sheet": ("sh", 'réglages ci-dessus">', ' Générer le sheet</button>'),
    "spritelab.previz.lecture-pause": ("sh", '<button id="playBtn" class="btn" title="Lecture / pause" aria-label="Lecture / pause">', '</button>'),
    "spritelab.previz.miroir": ("sh", 'aria-label="Miroir gauche / droite (Invert L/R)">', '</button>'),
    "spritelab.exports.dlSheet": ("sh", 'cellules transparentes)">', ' Sheet PNG</a>'),
    "spritelab.exports.dlZip": ("sh", 'SpriteSheetImporter.cs">', ' ZIP (frames + pack Unity)</a>'),
    "spritelab.exports.dlGif": ("sh", 'title="La préviz animée GIF">', ' GIF</a>'),
    "spritelab.exports.dlGodot": ("sh", 'corriger la dépendance)">', ' Godot .tres</a>'),
    "spritelab.exports.dlAtlas": ("sh", 'Phaser et PixiJS">', ' Atlas JSON</a>'),
    "spritelab.exports.dlAse": ("sh", 'les tags">', ' Aseprite .ase</a>'),
    "spritelab.exports.dlP2d": ("sh", 'sprites et flipbook">', ' Paper2D</a>'),
    "spritelab.exports.save-library": ("sh", 'comme nœud Image)">', ' Save to Library</button>'),
    "spritelab.exports.vers-studio": ("sh", 'avec ce sheet comme nœud Image">', ' → Studio</button>'),
    "spritelab.editeur.appliquer": ("sh", 'rien n\'est re-détouré)">', ' Appliquer</button>'),
    "spritelab.editeur.annuler": ("sh", 'feuille actuelle">', ' Annuler</button>'),
    "spritelab.hitbox.precedente": ("sh", 'aria-label="Frame précédente">', '</button>'),
    "spritelab.hitbox.suivante": ("sh", 'aria-label="Frame suivante">', '</button>'),
    "spritelab.hitbox.copier": ("sh", '(Ctrl+C)">', ' Copier</button>'),
    "spritelab.hitbox.coller": ("sh", '(Ctrl+V)">', ' Coller</button>'),
    "spritelab.hitbox.effacer": ("sh", 'choisi (Suppr)">', ' Effacer</button>'),
    "spritelab.squelette.outil-os": ("sh", 'l\'os choisi">', ' Os</button>'),
    "spritelab.squelette.outil-piece": ("sh", 'suit l\'os choisi">', ' Pièce</button>'),
    "spritelab.squelette.ecrire": ("sh", 'côté serveur (local, gratuit)">', ' Écrire le rig</button>'),
    "spritelab.squelette.dl-spine": ("sh", '(dossier spine/)">', ' Spine JSON</a>'),
    "spritelab.feuille.decaler-1-px-vers-le-haut": ("sh", 'data-dx="0" data-dy="-1" title="1 px vers le haut" aria-label="1 px vers le haut">', '</button>'),
    "spritelab.feuille.decaler-1-px-vers-la-gauche": ("sh", 'data-dx="-1" data-dy="0" title="1 px vers la gauche" aria-label="1 px vers la gauche">', '</button>'),
    "spritelab.feuille.decaler-1-px-vers-la-droite": ("sh", 'data-dx="1" data-dy="0" title="1 px vers la droite" aria-label="1 px vers la droite">', '</button>'),
    "spritelab.feuille.decaler-1-px-vers-le-bas": ("sh", 'data-dx="0" data-dy="1" title="1 px vers le bas" aria-label="1 px vers le bas">', '</button>'),
    "spritelab.feuille.section-ajout": ("sh", 'dans l\'ordre de lecture">', ' depuis la sélection</button>'),
    "spritelab.feuille.copier-json": ("sh", 'fps, sections)">', ' Copier le JSON</button>'),
    "spritelab.feuille.dl-json": ("sh", 'title="Télécharge le manifest JSON">', ' JSON</button>'),
    "spritelab.feuille.dl-png": ("sh", 'la planche alignée (PNG)">', ' Planche alignée</button>'),
    "spritelab.feuille.save-library": ("sh", 'le Vectorlab">', ' Save to Library</button>'),
    # ── Spritelab, script ──
    "spritelab.frames.cout": ("sj", 'el.innerHTML = d && d.total_usd != null ? `${', '} $${(+d.total_usd).toFixed(3)}` : "";\n  } catch (e) { el.textContent = ""; }\n}\n\n/* ───────── génération'),
    "spritelab.prompt.cout": ("sj", 'el.innerHTML = d && d.total_usd != null ? `${', '} $${(+d.total_usd).toFixed(3)}` : "";\n  } catch (e) { el.textContent = ""; }\n}\n\nasync function generateFromPrompt'),
    "spritelab.frames.frame-ecartee": ("sj", '<span class="frame-x">${', '}</span>'),
    "spritelab.animation.retirer-tag": ("sj", 'aria-label="Retirer ce tag">${', '}</button>'),
    "spritelab.editeur.cellule-left": ("sj", 'aria-label="Vers la gauche"${k === 0 ? " disabled" : ""}>${', '}</button>'),
    "spritelab.editeur.cellule-dup": ("sj", 'aria-label="Dupliquer"${n >= 64 ? " disabled" : ""}>${', '}</button>'),
    "spritelab.editeur.cellule-del": ("sj", 'aria-label="Supprimer"${n <= 1 ? " disabled" : ""}>${', '}</button>'),
    "spritelab.editeur.cellule-right": ("sj", 'aria-label="Vers la droite"${k === n - 1 ? " disabled" : ""}>${', '}</button>'),
    "spritelab.squelette.liste-os": ("sj", 'pièces s\'y accrochent">${', '}</span>'),
    "spritelab.squelette.suppr-os": ("sj", 'aria-label="Supprimer cet os, ses enfants et leurs pièces">${', '}</button>'),
    "spritelab.squelette.liste-piece": ("sj", '<span class="sk-ico">${', '}</span>'),
    "spritelab.squelette.suppr-piece": ("sj", 'aria-label="Supprimer cette pièce">${', '}</button>'),
    "spritelab.squelette.indice-vide": ("sj", 'avec l\'outil ${', '} Os</div>`'),
    "spritelab.feuille.section-retirer": ("sj", 'title="Retirer" aria-label="Retirer">${', '}</button>'),
    "spritelab.previz.lecture-play": ("sj", 'player.playing ? dzIcone("dz-media-pause", { taille: 16 }) : ', ';'),
}
# réussites : le site appelle toastOk (qui pose dz-etat-succes, ancienne coche) ; l'ancre est l'appel lui-même
TOASTS = {
    "spritelab.toast.sprite-sheet-genere": ("sj", 'toastOk("Sprite sheet généré");'),
    "spritelab.toast.feuille-reassemblee": ("sj", 'toastOk("Feuille réassemblée", " — local, gratuit");'),
    "spritelab.toast.sheet-copie-dans-la-library": ("sj", 'toastOk(`Sheet copié dans la Library${d && d.filename ? " : " + d.filename : ""}`, " — réutilisable'),
    "spritelab.toast.4-directions": ("sj", 'await finirFeuille(d.job_id, st, ["4 directions depuis la planche", " — gratuit, local"]);'),
    "spritelab.toast.8-directions": ("sj", '? ["8 directions", " — rendu opaque, clé chroma locale appliquée"] : ["8 directions", " — rendu déjà détouré"]);'),
    "spritelab.toast.image-s-generee-s": ("sj", 'toastOk(`${noms.length} image(s) générée(s)`, " — détourage'),
    "spritelab.toast.sprite-pret": ("sj", 'toastOk("Sprite prêt", " — gratuit, généré en local");'),
    "spritelab.toast.dernier-sheet-recharge": ("sj", 'toastOk("Dernier sheet rechargé");'),
    "tilelab.toast.tuile-prete": ("tj", 'toastOk(`Tuile prête : raccord ${d.seam_before} → ${after}`, ` (Library : ${finalName})`);'),
}
A.update({
    # ── Tilelab, page ──
    "tilelab.entete.marque": ("th", '<div class="brand">', ' <b>Tile Lab</b>'),
    "tilelab.entete.retour": ("th", 'title="Retour à l\'app">', ' App</a>'),
    "tilelab.modes.onglet-seamless": ("th", 'seamless (existant)">', ' Seamless</button>'),
    "tilelab.modes.onglet-feuille": ("th", 'exports — tout en local">', ' Feuille de tuiles</button>'),
    "tilelab.modes.onglet-jeu": ("th", 'vers Tiled, LDtk, Godot">', ' Jeu</button>'),
    "tilelab.modes.onglet-formes": ("th", 'qui pave sans couture">', ' Formes</button>'),
    "tilelab.modes.onglet-peintre": ("th", '(auto-tiling)">', ' Peintre</button>'),
    "tilelab.source.recherche-imgSearch": ("th", '<div class="search-wrap">', '<input id="imgSearch" class="search" placeholder="Filtrer les images…"></div>'),
    "tilelab.source.recherche-feuilleSearch": ("th", '<div class="search-wrap">', '<input id="feuilleSearch" class="search" placeholder="Filtrer les planches de la Library…"></div>'),
    "tilelab.source.recherche-jeuSearch": ("th", '<div class="search-wrap">', '<input id="jeuSearch" class="search" placeholder="Filtrer les matières…"></div>'),
    "tilelab.source.recherche-formeSearch": ("th", '<div class="search-wrap">', '<input id="formeSearch" class="search" placeholder="Filtrer les matières…"></div>'),
    "tilelab.feuille.ouvrir-png": ("th", '<label class="btn" for="feuilleFile">', ' Ouvrir un PNG de mon PC</label>'),
    "tilelab.jeu.source-lib": ("th", '<button id="jeuSrcLib" class="tl-srcb on" data-src="lib">', ' Bibliothèque</button>'),
    "tilelab.jeu.source-forge": ("th", '<button id="jeuSrcForge" class="tl-srcb" data-src="forge" title="Les matières du Material Forge — leur couleur de base">', ' Material Forge</button>'),
    "tilelab.forme.source-lib": ("th", '<button id="formeSrcLib" class="tl-srcb on" data-src="lib">', ' Bibliothèque</button>'),
    "tilelab.forme.source-forge": ("th", '<button id="formeSrcForge" class="tl-srcb" data-src="forge" title="Les matières du Material Forge — leur couleur de base">', ' Material Forge</button>'),
    "tilelab.lieu.prompt": ("th", 'rien n\'est généré">', ' Prompt du lieu</button>'),
    "tilelab.lieu.copier": ("th", 'title="Copier le prompt">', ' Copier le prompt</button>'),
    "tilelab.peintre.hint-jeu": ("th", 'avec le jeu fabriqué dans le mode ', ' Jeu.'),
    "tilelab.peintre.effacer": ("th", '(garde la taille)">', ' Tout effacer</button>'),
    "tilelab.seamless.rendre": ("th", 'rejoint la Library">', ' Rendre seamless</button>'),
    "tilelab.feuille.avant": ("th", 'aria-label="Un cran vers l\'avant (les placements suivent)">', '</button>'),
    "tilelab.feuille.apres": ("th", 'aria-label="Un cran vers l\'arrière">', '</button>'),
    "tilelab.feuille.vider": ("th", 'title="Retire tous les placements">', ' Vider</button>'),
    "tilelab.feuille.export-tlDlFeuille": ("th", '+ marge) + JSON">', ' Feuille alignée + JSON</button>'),
    "tilelab.feuille.export-tlDlTileset": ("th", 'JSON des placements">', ' Tileset + JSON</button>'),
    "tilelab.feuille.export-tlDlTuiles": ("th", 'un PNG par tuile">', ' Tuiles séparées (zip)</button>'),
    "tilelab.feuille.export-tlSaveLib": ("th", '(tiles_feuille_)">', ' Save to Library</button>'),
    "tilelab.peintre.export-pePng": ("th", 'download="carte.png">', ' carte.png</a>'),
    "tilelab.peintre.export-peJson": ("th", 'download="carte.json">', ' carte.json</a>'),
    "tilelab.jeu.fabriquer": ("th", '(tile_…_atlas.png)">', ' Fabriquer le jeu</button>'),
    "tilelab.jeu.nouvel-apercu": ("th", '(nouvelle graine)">', ' Nouvel aperçu</button>'),
    "tilelab.jeu.mesurer": ("th", 'contre son seuil">', ' Mesurer</button>'),
    "tilelab.jeu.export-expAtlas": ("th", 'que chaque format désigne">', ' atlas.png</button>'),
    "tilelab.jeu.export-expTiled": ("th", '(mixed / edge)">', ' Tiled .tsx</button>'),
    "tilelab.jeu.export-expLdtk": ("th", 'règles d\'auto-layer">', ' LDtk .ldtk</button>'),
    "tilelab.jeu.export-expGodot": ("th", 'avec terrain set">', ' Godot .tres</button>'),
    "tilelab.formes.fabriquer": ("th", '<button id="formeRun" class="btn primary big" disabled title="Local et gratuit (PIL)">', ' Fabriquer la tuile</button>'),
    "tilelab.formes.export-expFormeAtlas": ("th", '<button id="expFormeAtlas" class="btn">', ' atlas.png</button>'),
    "tilelab.formes.export-expFormeTiled": ("th", '<button id="expFormeTiled" class="btn">', ' Tiled .tsx</button>'),
    "tilelab.formes.export-expFormeGodot": ("th", '<button id="expFormeGodot" class="btn">', ' Godot .tres</button>'),
    "tilelab.seamless.dl-tuile": ("th", '(déjà dans la Library)">', ' Tuile PNG</a>'),
    "tilelab.seamless.vers-studio": ("th", 'avec cette tuile comme nœud Image">', ' → Studio</button>'),
    # ── Tilelab, scripts ──
    "tilelab.jeu.slot-materiau": ("jj", '(m.source === "materiau" ? ', ' + " " : "") + esc(m.nom)'),
    "tilelab.peintre.erreur-jeu": ("pj", 'statut("Fabrique d\'abord un jeu dans le mode " + ', ' + " Jeu : le peintre pose SES tuiles.", true, true);'),
    "tilelab.peintre.statut-jeu": ("pj", 'else $("#peJeu").innerHTML = "aucun jeu — fabrique-le dans le mode " + ', ' + " Jeu";'),
})
# écarts déclarés au compte par clé : (clé, delta, raison)
ECARTS = [
    ("dz-edit-monter", +1, "aide de l'éditeur : « Réordonne (◀ ▶) » montre les boutons réels"),
    ("dz-edit-descendre", +1, "aide de l'éditeur"),
    ("dz-action-dupliquer", +1, "aide de l'éditeur : « duplique (⧉) »"),
    ("dz-action-retirer", +1, "aide de l'éditeur : « supprime (✕) » montre le bouton de la cellule"),
    ("dz-media-pause", +1, "playIcone() rend pause OU lecture : la pause y figure aussi"),
    ("dz-etat-succes", 2 - 9, "neuf réussites passent par toastOk, une aide par lab (Spritelab, Tilelab)"),
]

impl = json.loads((ROOT / "docs" / "icones" / "suite-finale" / "implementation.json").read_text(encoding="utf-8"))
SITES = {e["id"]: e for e in impl if str(e.get("source", "")).startswith(("frontend/spritelab/", "frontend/tilelab/"))}
POSES = {i: e for i, e in SITES.items() if e.get("cle_finale")}
TEXTES = {i: e for i, e in SITES.items() if not e.get("cle_finale")}
T = {k: lire(k) for k in FICHIERS}

print("[1] runtime chargé dans les deux pages")
for f, modules in (("sh", ['import * as SLF from "./feuille.js"', '<script src="spritelab.js">']),
                   ("th", ['import * as T from "./feuille_tuiles.js"', '<script src="tilelab.js">'])):
    t = T[f]
    css, js, i18n = t.find('<link rel="stylesheet" href="/shared/icons/dz-icons.css">'), \
        t.find('<script src="/shared/icons/dz-icons.js"></script>'), t.find('<script src="/shared/dz-i18n.js"></script>')
    check(f"1.1 {FICHIERS[f]} : dz-icons.css dans <head>", 0 <= css < t.find("</head>"))
    check(f"1.2 {FICHIERS[f]} : dz-icons.js APRÈS dz-i18n.js et AVANT les modules du lab",
          0 <= i18n < js and all(0 <= js < t.find(m) for m in modules), (i18n, js, [t.find(m) for m in modules]))
    check(f"1.3 {FICHIERS[f]} : chargé une seule fois", t.count("/shared/icons/dz-icons.js") == 1 and t.count("/shared/icons/dz-icons.css") == 1)

print("[2] chaque site porte sa clé finale, à sa place")
check("2.0 périmètre : 124 sites à poser, 14 en texte seul", len(POSES) == 124 and len(TEXTES) == 14, (len(POSES), len(TEXTES)))
check("2.1 la table des ancres couvre exactement les sites du JSON", set(A) | set(TOASTS) == set(POSES),
      sorted(set(POSES) ^ (set(A) | set(TOASTS))))
for i, (f, avant, apres) in sorted(A.items()):
    if i not in POSES:
        continue
    k = POSES[i]["cle_finale"]
    motif = STAT(k) if f.endswith("h") else DYN(k)
    rx = re.escape(avant) + motif + re.escape(apres)
    n = len(re.findall(rx, T[f]))
    check(f"2.2 {i} → {k}", n == 1, f"{n} correspondance(s) dans {FICHIERS[f]}")
for i, (f, appel) in sorted(TOASTS.items()):
    if i not in POSES:
        continue
    k = POSES[i]["cle_finale"]
    check(f"2.3 {i} → {k} (par toastOk)", T[f].count(appel) >= 1, appel)
for f in ("sj", "tj"):
    m = re.search(r"function toastOk\(avant, apres\) \{(.*?)\n\}", T[f], re.S)
    check(f"2.4 {FICHIERS[f]} : toastOk pose dz-etat-succes entre le texte échappé et la suite",
          bool(m) and re.search(r'esc\(avant\) \+ " " \+ ' + DYN("dz-etat-succes") + r' \+ esc\(apres \|\| ""\)', m.group(1)), m and m.group(1))
check("2.5 finirFeuille rend sa réussite par toastOk(msg[0], msg[1])", "toastOk(msg[0], msg[1]);" in T["sj"])
m = re.search(r"function playIcone\(\) \{(.*?)\n\}", T["sj"], re.S)
check("2.6 playIcone : pause pendant la lecture, lecture à l'arrêt",
      bool(m) and re.search(r"player\.playing \? " + DYN("dz-media-pause") + " : " + DYN("dz-media-lecture"), m.group(1)))
check("2.7 le bouton lecture / pause ne reçoit plus que playIcone (4 appels, aucun glyphe)",
      T["sj"].count("playIcone();") == 4 and '$("#playBtn").textContent' not in T["sj"], T["sj"].count("playIcone();"))

print("[3] comptes par clé")
attendu = collections.Counter(e["cle_finale"] for e in POSES.values())
for k, d, _ in ECARTS:
    attendu[k] += d
vu = collections.Counter()
for f, t in T.items():
    t = sans_commentaires(t, FICHIERS[f])
    vu.update(re.findall(r'/shared/icons/dz-icons\.svg#(dz-[a-z0-9-]+)"', t))
    vu.update(re.findall(r'dzIcone\("(dz-[a-z0-9-]+)"', t))
for k in sorted(set(attendu) | set(vu)):
    check(f"3.1 {k} : {attendu[k]} usage(s)", vu[k] == attendu[k], f"vu {vu[k]}")

print("[4] anciens glyphes et emojis remplacés : partis")
VIEUX = set()
for e in POSES.values():
    if e["cle_visuelle"] != "aucune":
        VIEUX.add(e["cle_visuelle"].split(" ", 1)[-1])
TEXTE_PERMIS = {"←", "→", "↑", "↓", "≈", "+"}   # restent comme texte ailleurs : vérifiés site par site ci-dessous
for f, t in T.items():
    t = sans_commentaires(t, FICHIERS[f])
    restes = sorted(g for g in VIEUX - TEXTE_PERMIS if g in t)
    check(f"4.1 {FICHIERS[f]} : aucun ancien emoji / glyphe", not restes, restes)
check("4.2 ← App, ↑ ← → ↓ des décalages, ≈ du coût, « + depuis la sélection » : partis",
      ">+ depuis" not in T["sh"] and "← App" not in T["sh"] + T["th"] and not re.search(r">[↑↓←→]</button>", T["sh"]) and "`≈" not in T["sj"])
check("4.3 aucune loupe dans les placeholders", "placeholder=\"🔎" not in T["sh"] + T["th"])
check("4.4 texte seul inchangé : flèche avant → après, cases « clique une image ↓ », seuils ≤ / <",
      '<span class="tl-arrow">→</span>' in T["th"] and T["th"].count("clique une image ↓") == 2 and T["jj"].count('"≤"') == 3)

print("[5] clés connues, CSS")
sprite = (FRONT / "shared" / "icons" / "dz-icons.svg").read_text(encoding="utf-8")
ids = set(re.findall(r'<symbol id="([^"]+)"', sprite))
js_icons = (FRONT / "shared" / "icons" / "dz-icons.js").read_text(encoding="utf-8")
check("5.1 chaque clé employée est dessinée (sprite et DZ_ICONS)",
      all(k in ids and f'"{k}":' in js_icons for k in vu), sorted(k for k in vu if k not in ids))
css = T["sc"]
check("5.2 la frame écartée montre .frame-x (dz-etat-exclu), plus de ✖ en ::after",
      "::after{content" not in css and ".frame.off .frame-x{" in css and ".frame .frame-x{display:none}" in css)
check("5.3 dz-edit-decaler-px orientée dans les quatre directions",
      all(r in css for r in ('.fNudge[data-dx="-1"] .dzi{transform:rotate(180deg)}', '.fNudge[data-dy="-1"] .dzi{transform:rotate(-90deg)}',
                             '.fNudge[data-dy="1"] .dzi{transform:rotate(90deg)}')))
check("5.4 la loupe du champ de recherche est posée dans le champ", ".search-wrap > .dzi{position:absolute" in css and ".search-wrap > .search{padding-left:30px}" in css)

print("[6] node --check")
if not NODE:
    check("6.0 node disponible", False)
else:
    for f in ("sj", "tj", "jj", "pj"):
        r = subprocess.run([NODE, "--check", str(FRONT / FICHIERS[f])], capture_output=True, text=True, encoding="utf-8")
        check(f"6.1 node --check {FICHIERS[f]}", r.returncode == 0, r.stderr[-300:])

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
