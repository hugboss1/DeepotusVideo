# -*- coding: utf-8 -*-
"""Icônes G6 (10/10/2026) — la suite « Deepotus Glyph » posée dans l'Atelier, les Matières, l'Établi, le Plateau 3D,
le 3D Studio et les fichiers partagés dz-champ-ia.js / dz-maj.js (liste de travail :
docs/icones/suite-finale/implementation.json, entrées dont `source` est sous ces dossiers).

  [1] le runtime : chaque page du lot charge dz-icons.css et dz-icons.js, une fois, le script APRÈS dz-i18n.js (s'il
      y est) et AVANT les scripts du lab ; chaque page porte le favicon de l'application : le LOGO (/api/branding/logo) ; aucun emoji de MARQUE
      (🐙) hors contenu : la marque est dz-marque-poulpe, le logo en image.
  [2] chaque site de la liste porte sa clé : toute entrée `cle_finale` du périmètre trouve sa clé dans le(s)
      fichier(s) de sa source (sauf DEUX sites non posables, dits et justifiés : une <option> ne porte pas de SVG) ;
      et le compte de chaque clé par fichier est FIGÉ (hors commentaires) — un site perdu ou doublé se voit.
  [3] plus aucun des anciens glyphes remplacés : chaque fragment remplacé (relevé dans les tables du lot) est absent ;
      et le recensement des glyphes de la liste qui restent (hors commentaires) est figé — ce sont des TEXTES
      (toasts, aides, infobulles qui citent un bouton) ou les deux sites non posables.
  [4] chaque clé posée existe dans la suite (sprite et runtime) : aucune icône vide ; le runtime EXÉCUTÉ sous node
      rend chacune.
  [5] les fichiers partagés : copie servie frontend/dist/shared identique octet pour octet ; ils tirent l'icône du
      SPRITE (pas du runtime, que toutes leurs pages ne chargent pas) ; node --check de chaque JS modifié.
Run : & $PY tests/test_icones_g6.py   (depuis backend/)
"""
import collections, json, pathlib, re, shutil, subprocess, sys, urllib.parse

sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
NODE = shutil.which("node")
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label}  {str(detail)[:600]}")


def lire(rel):
    return (ROOT / rel).read_bytes().decode("utf-8").replace("\r\n", "\n")


def sans_commentaires(t, f):
    if f.endswith(".html"):
        t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    if f.endswith(".js"):
        t = re.sub(r"(?m)^\s*//.*$", "", t)
        t = re.sub(r"(?<![:\"'`\\])//[^\n\"'`]*$", "", t, flags=re.M)
    return t


RX_CLE = re.compile(r"dz-(?:action|etat|media|nav|cat|edit|lab3d|calque|outil-vec|marque)-[a-z0-9-]+")
PAGES = ["frontend/atelier/index.html", "frontend/materialforge/index.html", "frontend/etabli/index.html",
         "frontend/plateau/index.html", "frontend/studio3d/index.html"]
LIEN = '<link rel="stylesheet" href="/shared/icons/dz-icons.css">'
SCRIPT = '<script src="/shared/icons/dz-icons.js"></script>'
I18N = '<script src="/shared/dz-i18n.js"></script>'
PREFIXES = ("frontend/atelier/", "frontend/materialforge/", "frontend/etabli/", "frontend/plateau/",
            "frontend/studio3d/", "frontend/shared/")
# une <option> ne porte pas de SVG : ces deux sites marquent une option PARMI d'autres (entité de la bible, photo
# du téléphone) — aucune icône « de liste » devant le <select> ne dirait laquelle. Glyphe gardé, signalé au rapport.
NON_POSABLES = {"plateau.scene.entite-bible": "◆", "studio3d.vues.mobile-note": "📱"}

# trois sites dont le dessin vivait en CSS ou dans une <option> : l'icône est devenue un ÉLÉMENT, ailleurs
RELOGES = {
    "etabli.chrono.etape-lourde": "frontend/etabli/etabli.js",          # « ⚠ » de .etape.lourde b::after -> gabarit
    "matieres.galerie.tri-resolution": "frontend/materialforge/index.html",  # « Résolution ↓ » (option) -> devant #galSort
    "matieres.rail.groupe-chevron": "frontend/materialforge/materialforge.js",  # chevron tracé en CSS -> grpSummary
}

# ── DONNÉES FIGÉES (recensement de l'état posé, 10/10/2026) ──
# compte des clés posées par fichier, hors commentaires
ATTENDU = {
    'frontend/atelier/index.html': {
        'dz-action-ajouter': 5,
        'dz-action-apercu': 1,
        'dz-action-choisir-bibliotheque': 1,
        'dz-action-decouper-plans': 1,
        'dz-action-exporter': 6,
        'dz-action-fermer': 7,
        'dz-action-importer': 4,
        'dz-action-lancer': 1,
        'dz-action-nouveau': 1,
        'dz-action-reecrire-ia': 2,
        'dz-action-retirer': 1,
        'dz-action-retour': 1,
        'dz-action-suggerer': 1,
        'dz-action-supprimer': 1,
        'dz-action-valider': 2,
        'dz-action-vider': 2,
        'dz-calque-vectoriel': 1,
        'dz-cat-ambiance': 1,
        'dz-cat-date': 1,
        'dz-cat-decor': 1,
        'dz-cat-lieu': 1,
        'dz-cat-objet': 1,
        'dz-cat-personnage': 1,
        'dz-edit-lier': 1,
        'dz-edit-paragraphes': 1,
        'dz-edit-symbole': 1,
        'dz-etat-attente': 1,
        'dz-media-animatique': 2,
        'dz-media-film': 1,
        'dz-media-generer-voix': 1,
        'dz-media-manuscrit': 2,
        'dz-media-reel': 1,
        'dz-nav-direction-artistique': 2,
        'dz-nav-episodes': 1,
        'dz-nav-versions': 1,
    },
    'frontend/atelier/atelier.js': {
        'dz-action-ajouter': 1,
        'dz-action-aleatoire': 2,
        'dz-action-choisir-bibliotheque': 1,
        'dz-action-copier': 1,
        'dz-action-deplier': 1,
        'dz-action-lancer-recette': 1,
        'dz-action-mesurer': 1,
        'dz-action-restaurer': 1,
        'dz-action-suggerer': 1,
        'dz-action-supprimer': 2,
        'dz-action-telecharger': 1,
        'dz-action-valider': 1,
        'dz-edit-descendre': 1,
        'dz-edit-energie': 1,
        'dz-edit-lier': 1,
        'dz-edit-monter': 1,
        'dz-etat-enregistre': 2,
        'dz-etat-information': 1,
        'dz-etat-mobile': 1,
        'dz-etat-origine': 1,
        'dz-etat-verrouille': 2,
        'dz-lab3d-camera': 1,
        'dz-lab3d-generer-modele': 1,
        'dz-media-apparitions': 1,
        'dz-media-cloner-voix': 1,
        'dz-media-duree': 1,
        'dz-media-film': 1,
        'dz-media-generer-image': 3,
        'dz-media-generer-voix': 1,
        'dz-media-image': 1,
        'dz-media-lecture': 3,
        'dz-media-reel': 1,
        'dz-media-voix': 1,
        'dz-nav-bibliotheque': 1,
        'dz-nav-plateau': 1,
    },
    'frontend/materialforge/index.html': {
        'dz-action-aide': 1,
        'dz-action-apercu': 1,
        'dz-action-capturer': 1,
        'dz-action-chercher': 3,
        'dz-action-choisir-bibliotheque': 1,
        'dz-action-comparer': 1,
        'dz-action-deplier': 3,
        'dz-action-fabriquer': 1,
        'dz-action-importer': 1,
        'dz-action-reinitialiser': 2,
        'dz-action-retirer': 1,
        'dz-action-retour': 2,
        'dz-action-supprimer': 1,
        'dz-action-telecharger': 1,
        'dz-action-trier': 1,
        'dz-cat-matieres': 1,
        'dz-lab3d-forger-matiere': 2,
        'dz-lab3d-hdri': 1,
        'dz-lab3d-lumiere': 2,
        'dz-lab3d-procedural': 1,
        'dz-media-pack-depart': 1,
    },
    'frontend/materialforge/materialforge.js': {
        'dz-action-chercher': 1,
        'dz-action-deplier': 1,
        'dz-action-dupliquer': 1,
        'dz-action-reprendre-reglages': 1,
        'dz-action-supprimer': 2,
        'dz-action-telecharger': 4,
        'dz-cat-matieres': 1,
        'dz-etat-avertissement': 1,
        'dz-etat-erreur': 1,
        'dz-etat-information': 2,
        'dz-etat-succes': 1,
        'dz-lab3d-deriver-maps': 3,
        'dz-lab3d-forger-matiere': 1,
        'dz-media-pack-depart': 1,
    },
    'frontend/etabli/index.html': {
        'dz-action-aide': 1,
        'dz-action-fermer': 1,
        'dz-action-importer': 1,
        'dz-action-retour': 1,
        'dz-lab3d-impression-3d': 2,
    },
    'frontend/etabli/etabli.js': {
        'dz-etat-avertissement': 1,
        'dz-etat-cache': 1,
        'dz-etat-option-active': 2,
        'dz-etat-visible': 1,
        'dz-lab3d-orienter': 1,
        'dz-outil-vec-couteau': 1,
        'dz-outil-vec-mesure': 1,
    },
    'frontend/etabli/aide.js': {
        'dz-nav-guide': 1,
    },
    'frontend/plateau/index.html': {
        'dz-action-ajouter': 1,
        'dz-action-capturer': 1,
        'dz-action-retour': 1,
        'dz-action-telecharger': 1,
        'dz-lab3d-capsule': 1,
        'dz-lab3d-cube': 1,
        'dz-lab3d-cylindre': 1,
        'dz-lab3d-sphere': 1,
        'dz-media-image-cle': 1,
        'dz-media-lecture': 1,
    },
    'frontend/plateau/plateau.js': {
        'dz-etat-avertissement': 1,
        'dz-etat-succes': 2,
        'dz-media-image-cle-retirer': 1,
        'dz-media-lecture': 1,
        'dz-media-pause': 1,
        'dz-nav-plateau': 1,
    },
    'frontend/studio3d/index.html': {
        'dz-action-convertir': 1,
        'dz-action-envoyer-vers': 1,
        'dz-action-importer': 3,
        'dz-action-reinitialiser': 1,
        'dz-cat-3d': 1,
        'dz-cat-sprites': 1,
        'dz-lab3d-generer-modele': 3,
        'dz-lab3d-rig': 2,
        'dz-media-pause': 1,
        'dz-nav-etabli': 1,
    },
    'frontend/studio3d/studio3d.js': {
        'dz-lab3d-generer-modele': 1,
        'dz-media-lecture': 1,
        'dz-media-pause': 1,
        'dz-nav-etabli': 1,
    },
    'frontend/studio3d/fal.js': {
        'dz-lab3d-rig': 2,
    },
    'frontend/studio3d/vues.js': {
        'dz-action-detourer': 1,
        'dz-action-regenerer': 1,
        'dz-lab3d-generer-modele': 4,
    },
    'frontend/shared/dz-champ-ia.js': {
        'dz-action-deplier': 1,
        'dz-media-arret': 3,
        'dz-media-dicter': 2,
    },
    'frontend/shared/dz-maj.js': {
        'dz-action-telecharger': 1,
    },
}
# les glyphes de la liste (anciens dessins des sites du lot, ◌ compris : l'autre état de l'œil de l'Établi)
GLYPHES = '¶×←↑→↓↩↺↻⇔⌄⏱⏳■▶▾◆◈◉◌◧☀⚒⚓⚠⚡⛓⛶✂✍✓✔✕✨❙➕⤒⧉⬆⬇＋🎙🎞🎥🎨🎬🎭🎲👁📄📏📚📤📥📱📺🔁🔊🔎🔒🔗🕘🖼🗑🚀🧊🧬'
# ce qu'il en reste, hors commentaires : des TEXTES qui citent un bouton (toasts, aides, infobulles,
# placeholders), les flèches d'une phrase (« A → B »), les deux sites non posables, et le « ↻ » d'état du
# bouton voice-over d'une scène (le voice-over existe déjà) gardé à côté de son icône
GLYPHES_RESTANTS = {
    'frontend/atelier/index.html': {'→': 2, '✨': 1, '🎞': 1, '🎨': 1, '📚': 1, '🕘': 1},
    'frontend/atelier/atelier.js': {'¶': 3, '→': 8, '↻': 1, '⏱': 2, '▾': 1, '⚠': 1, '⛓': 1, '✨': 3, '＋': 1, '🎙': 2, '🎨': 3, '🎬': 4, '🎭': 6, '📚': 2, '🔁': 4, '🔊': 3, '🔒': 1, '🕘': 1, '🧊': 2, '🧬': 1},
    'frontend/atelier/atelier.css': {},
    'frontend/materialforge/index.html': {'×': 1, '☀': 2},
    'frontend/materialforge/materialforge.js': {'×': 7, '↑': 1, '→': 4, '↓': 1},
    'frontend/materialforge/materialforge.css': {},
    'frontend/etabli/index.html': {},
    'frontend/etabli/etabli.js': {'×': 4, '→': 12},
    'frontend/etabli/aide.js': {'→': 3},
    'frontend/etabli/etabli.css': {},
    'frontend/plateau/index.html': {},
    'frontend/plateau/plateau.js': {'×': 1, '◆': 2},
    'frontend/plateau/plateau.css': {},
    'frontend/studio3d/index.html': {'📱': 1},
    'frontend/studio3d/studio3d.js': {'→': 10, '↺': 1},
    'frontend/studio3d/fal.js': {'→': 6},
    'frontend/studio3d/vues.js': {'↻': 1, '✂': 1, '📱': 1},
    'frontend/studio3d/studio3d.css': {},
    'frontend/shared/dz-champ-ia.js': {'🎨': 2},
    'frontend/shared/dz-maj.js': {},
}
# les fragments remplacés (fichier, ligne d'origine portant le glyphe) : aucun ne doit subsister
ANCIENS = [
    ('frontend/atelier/index.html', '>📚 Manuscrit</button>'),
    ('frontend/atelier/index.html', 'title="Supprimer ce chapitre">🗑</button>'),
    ('frontend/atelier/index.html', '>🕘 Versions</button>'),
    ('frontend/atelier/index.html', 'title="Retour à l\'app">← App</a>'),
    ('frontend/atelier/index.html', '<label class="btn" for="importFile">📄 Importer (txt/docx/pdf)</label>'),
    ('frontend/atelier/index.html', '>⬇ .docx</button>'),
    ('frontend/atelier/index.html', '>⬇ .pdf</button>'),
    ('frontend/atelier/index.html', 'data-kind="character">➕ Personnage</button>'),
    ('frontend/atelier/index.html', 'data-kind="place">➕ Lieu</button>'),
    ('frontend/atelier/index.html', 'data-kind="object">➕ Objet</button>'),
    ('frontend/atelier/index.html', 'data-kind="date">➕ Date</button>'),
    ('frontend/atelier/index.html', 'data-kind="ambiance">➕ Ambiance</button>'),
    ('frontend/atelier/index.html', 'data-kind="decor">➕ Décor</button>'),
    ('frontend/atelier/index.html', '<option value="">🔗 Lier à…</option>'),
    ('frontend/atelier/index.html', '<option value="">✍ Réécrire…</option>'),
    ('frontend/atelier/index.html', '>🎭 Adapter (IA)</button>'),
    ('frontend/atelier/index.html', '>👁 Lire</button>'),
    ('frontend/atelier/index.html', '>🔊 Voice-over</button>'),
    ('frontend/atelier/index.html', 'download>⬇ .fountain</a>'),
    ('frontend/atelier/index.html', '>📥 Importer .fountain / .fdx</label>'),
    ('frontend/atelier/index.html', '>🗑 Réinitialiser</button>'),
    ('frontend/atelier/index.html', '>🎬 Découper (IA)</button>'),
    ('frontend/atelier/index.html', '>¶ Paragraphes</button>'),
    ('frontend/atelier/index.html', '>＋ Plan</button>'),
    ('frontend/atelier/index.html', '>📺 Épisode</button>'),
    ('frontend/atelier/index.html', '>⬇ PDF</button>'),
    ('frontend/atelier/index.html', '>🎞 Animatique</button>'),
    ('frontend/atelier/index.html', '<span>◧ Éléments vectoriels</span>'),
    ('frontend/atelier/index.html', '>＋ Décor</button>'),
    ('frontend/atelier/index.html', '>＋ Lumière</button>'),
    ('frontend/atelier/index.html', '>＋ Personnage</button>'),
    ('frontend/atelier/index.html', '>⧉ Bibliothèque</button>'),
    ('frontend/atelier/index.html', '<button id="addEntity" class="btn">＋ Nouveau</button>'),
    ('frontend/atelier/index.html', '>🎨 DA</button>'),
    ('frontend/atelier/index.html', '>📤 Fichier</label>'),
    ('frontend/atelier/index.html', '>🔗 URL</button>'),
    ('frontend/atelier/index.html', '<button id="libClose" class="btn ghost">✕</button>'),
    ('frontend/atelier/index.html', '<button id="daClose" class="btn ghost">✕</button>'),
    ('frontend/atelier/index.html', '<button id="spClose" class="btn ghost">✕</button>'),
    ('frontend/atelier/index.html', '<button id="msClose" class="btn ghost">✕</button>'),
    ('frontend/atelier/index.html', '<button id="verClose" class="btn ghost" title="Fermer">✕</button>'),
    ('frontend/atelier/index.html', '<button id="animClose" class="btn ghost" title="Fermer">✕</button>'),
    ('frontend/atelier/index.html', '<button id="reeClose" class="btn ghost" title="Fermer sans rien écrire">✕</button>'),
    ('frontend/atelier/index.html', '<b>🎨 Direction artistique du projet</b>'),
    ('frontend/atelier/index.html', '>✨ (Re)proposer</button>'),
    ('frontend/atelier/index.html', '>🖼 Choisir</button>'),
    ('frontend/atelier/index.html', '>✕ Retirer</button>'),
    ('frontend/atelier/index.html', '>✔ Appliquer au projet</button>'),
    ('frontend/atelier/index.html', '<b>📚 Agent Manuscrit — ingestion complète</b>'),
    ('frontend/atelier/index.html', ">🚀 Lancer l'agent</button>"),
    ('frontend/atelier/index.html', '<span class="ms-warn">⏳ plusieurs'),
    ('frontend/atelier/index.html', '>🎞 Monter</button>'),
    ('frontend/atelier/index.html', '>🎬 Film</button>'),
    ('frontend/atelier/index.html', '>⚡ Reel</button>'),
    ('frontend/atelier/index.html', '>✔ Appliquer</button>'),
    ('frontend/atelier/atelier.js', '`<p>📱 Emporté par le téléphone'),
    ('frontend/atelier/atelier.js', '$("#saveState").textContent = "enregistré ✓";'),
    ('frontend/atelier/atelier.js', '$("#styleSaved").textContent = "✓";'),
    ('frontend/atelier/atelier.js', '`<option value="">🔗 Lier à…</option>`'),
    ('frontend/atelier/atelier.js', 'title="Seed verrouillé de la planche">🔒 ${e.seed}</span>'),
    ('frontend/atelier/atelier.js', '(Blender, Unity, Unreal, three.js)">🧊 GLB</a>'),
    ('frontend/atelier/atelier.js', '— un seul seed pour tous les angles)">🎨 Planche</button>'),
    ('frontend/atelier/atelier.js', '<button class="btn act-roll" title="Nouvelle planche, seed aléatoire">🎲</button>'),
    ('frontend/atelier/atelier.js', 'title="Rejoue la recette verrouillée (prompt exact + seed) — image identique garantie">🔁</button>'),
    ('frontend/atelier/atelier.js', 'chapitre par chapitre">⛓ Apparitions</button>'),
    ('frontend/atelier/atelier.js', '<button class="btn ghost act-del" title="Supprimer l\'entité">🗑</button>'),
    ('frontend/atelier/atelier.js', '🎙 <span class="voice-name">'),
    ('frontend/atelier/atelier.js', 'title="Pré-écouter la voix">▶</button>'),
    ('frontend/atelier/atelier.js', 'du même profil">🎙 Suggérer</button>'),
    ('frontend/atelier/atelier.js', 'parmi toutes les voix du compte">⌄ Toutes</button>'),
    ('frontend/atelier/atelier.js', 'emplacement de voix du compte">🧬 Cloner</button>'),
    ('frontend/atelier/atelier.js', 'title="Ajouter depuis la Library">＋</button>'),
    ('frontend/atelier/atelier.js', 'el.textContent = `🎬 shotcraft · ${shotcraft.status.cards} fiches · ` +'),
    ('frontend/atelier/atelier.js', '" selected" : ""}>⚡ —</option>`'),
    ('frontend/atelier/atelier.js', '`${v === cur ? " selected" : ""}>⚡ ${ENERGY_LABELS[v]}</option>`'),
    ('frontend/atelier/atelier.js', 'c\'est la durée de la scène">⏱ ${fmtDur(s.duration_s)}</span>'),
    ('frontend/atelier/atelier.js', 'title="Écouter le voice-over de la scène">▶</button>'),
    ('frontend/atelier/atelier.js', 'La durée réelle minute la scène.">🔊${s.vo_audio ? " ↻" : ""}</button>'),
    ('frontend/atelier/atelier.js', '<div class="scene-cam">🎥 <input'),
    ('frontend/atelier/atelier.js', '<div class="seedtag">🔒 ${s.sketch_seed}</div>'),
    ('frontend/atelier/atelier.js', 'title="Générer le croquis (même seed si déjà généré)">🎨</button>'),
    ('frontend/atelier/atelier.js', 'title="Nouveau croquis (seed aléatoire)">🎲</button>'),
    ('frontend/atelier/atelier.js', 'coût affiché et confirmé avant">🖼</button>'),
    ('frontend/atelier/atelier.js', 'capturer ses images de début et de fin">🎥</button>'),
    ('frontend/atelier/atelier.js', '<span>🖼 ${s.image_refs || 0} réf.</span>'),
    ('frontend/atelier/atelier.js', 'comparées à la vue de chaque entité">📏</button>'),
    ('frontend/atelier/atelier.js', 'title="Monter" ${i === 0 ? "disabled" : ""}>↑</button>'),
    ('frontend/atelier/atelier.js', 'title="Descendre" ${i === shots.length - 1 ? "disabled" : ""}>↓</button>'),
    ('frontend/atelier/atelier.js', 'title="Insérer un plan après">＋</button>'),
    ('frontend/atelier/atelier.js', 'title="Supprimer le plan">🗑</button>'),
    ('frontend/atelier/atelier.js', 'if (v) b.textContent = `${n === "film" ? "🎬 Film" : "⚡ Reel"} · ${v.plans} plan(s), ${fmtDur(v.duree_s)}`;'),
    ('frontend/atelier/atelier.js', 'title="Pré-écouter">▶</button>'),
    ('frontend/atelier/atelier.js', '<button class="btn vc-pick" title="Attribuer cette voix">✓</button>'),
    ('frontend/atelier/atelier.js', 'd.chapter_id ? "⚓" : "◇"}</span>'),
    ('frontend/atelier/atelier.js', 'le texte courant est gardé en instantané avant">↩ Restaurer</button>'),
    ('frontend/atelier/atelier.js', 'copiez son texte">⧉ Copier le texte</button>'),
    ('frontend/atelier/atelier.js', 'title="Cocher les entités présentes dans ce plan">⛓ entités du plan</summary>'),
    ('frontend/materialforge/index.html', '<div class="brand">✨ <b>Material Forge</b></div>'),
    ('frontend/materialforge/index.html', 'title="Retour à l\'app">← App</a>'),
    ('frontend/materialforge/index.html', 'id="tabForge" type="button">⚒ Forger</button>'),
    ('frontend/materialforge/index.html', 'id="tabGen" type="button">◈ Générateurs</button>'),
    ('frontend/materialforge/index.html', '<span class="drop-ic">⬆</span>'),
    ('frontend/materialforge/index.html', 'déjà présente dans la Library">📚 Library</button>'),
    ('frontend/materialforge/index.html', '<button class="btn ghost sm" id="refClear" title="Retirer la référence">✕</button>'),
    ('frontend/materialforge/index.html', '<input class="search sm" id="libSearch" placeholder="🔎 Filtrer les images…">'),
    ('frontend/materialforge/index.html', 'title="Effacer les quatre coins">↺ Coins</button>'),
    ('frontend/materialforge/index.html', '👁 Aperçu de la préparation</button>'),
    ('frontend/materialforge/index.html', 'Invite exacte envoyée au modèle <i class="chev">▾</i></summary>'),
    ('frontend/materialforge/index.html', 'id="genGo" type="button">◈ Créer la matière</button>'),
    ('frontend/materialforge/index.html', '<span id="genLabel">⚒ Forger la matière</span>'),
    ('frontend/materialforge/index.html', 'title="Retour à la galerie">← Galerie</button>'),
    ('frontend/materialforge/index.html', 'embarquées dans l\'installation">📚 Catalogue CC0</button>'),
    ('frontend/materialforge/index.html', '<input class="search sm" id="galSearch" placeholder="🔎 Filtrer…">'),
    ('frontend/materialforge/index.html', 'sous la même ambiance et la même caméra">⇔ Comparer</button>'),
    ('frontend/materialforge/index.html', 'glisse le disque ☀ dans le rendu">☀ Lumière</button>'),
    ('frontend/materialforge/index.html', '<div class="light-puck hidden" id="puck" title="Glisse pour déplacer la lumière">☀</div>'),
    ('frontend/materialforge/index.html', 'équirectangulaire (.hdr) ou une image 2:1">＋ HDRI…</label>'),
    ('frontend/materialforge/index.html', 'title="Supprimer l\'ambiance importée sélectionnée">🗑</button>'),
    ('frontend/materialforge/index.html', 'title="Rétablir toutes les propriétés par défaut">↺ Défauts</button>'),
    ('frontend/materialforge/index.html', 'qui se téléchargent depuis le groupe Maps.">⛶ Vignette de la carte</button>'),
    ('frontend/materialforge/index.html', '<input class="search" id="propSearch" placeholder="🔎 Filtrer les réglages de l\'inspecteur"'),
    ('frontend/materialforge/index.html', '<button class="btn strong wide big" id="btnExport">⬇ Télécharger</button>'),
    ('frontend/materialforge/materialforge.js', 'const dot = done ? "✓" : String(i + 1);'),
    ('frontend/materialforge/materialforge.js', '$("#genLabel").textContent = b ? "⚒ Forge en cours…" : "⚒ Forger la matière";'),
    ('frontend/materialforge/materialforge.js', '{ id: "res", label: "Résolution ↓" },'),
    ('frontend/materialforge/materialforge.js', '<div class="empty-ic">⚠</div>'),
    ('frontend/materialforge/materialforge.js', '<div class="empty-ic">🔎</div>'),
    ('frontend/materialforge/materialforge.js', '<div class="empty-ic">⚒</div>'),
    ('frontend/materialforge/materialforge.js', 'data-empty="catalog">📚 Catalogue CC0 (30 matières)</button>'),
    ('frontend/materialforge/materialforge.js', 'if (!c.n) return "◧ maps";'),
    ('frontend/materialforge/materialforge.js', 'const tete = "◧ " + c.n + " maps";'),
    ('frontend/materialforge/materialforge.js', 'title="Supprimer la matière et ses maps — un second clic confirme">✕</button>'),
    ('frontend/materialforge/materialforge.js', 'b.textContent = "✕";'),
    ('frontend/materialforge/materialforge.js', 'title="Copie locale et gratuite de cette matière">⧉ Dupliquer</button>'),
    ('frontend/materialforge/materialforge.js', 'dans le rail de gauche">↺ Invite</button>'),
    ('frontend/materialforge/materialforge.js', '? "⚠ " + gains.map('),
    ('frontend/materialforge/materialforge.js', 'dl.textContent = "⬇ Télécharger ce ZIP";'),
    ('frontend/materialforge/materialforge.js', 'rb.textContent = "↻ Re-dériver les maps";'),
    ('frontend/materialforge/materialforge.js', 'btn.textContent = "↻ Dérivation…";'),
    ('frontend/materialforge/materialforge.js', 'btn.textContent = "↻ Re-dériver les maps";'),
    ('frontend/materialforge/materialforge.js', '$("#btnExport").innerHTML = "⬇ Télécharger";'),
    ('frontend/materialforge/materialforge.js', '$("#btnExport").innerHTML = "⬇ " + esc(d.archive)'),
    ('frontend/plateau/index.html', 'title="Une boîte — mur, table, caisse">＋ Boîte</button>'),
    ('frontend/plateau/index.html', 'title="Une capsule — un personnage debout">＋ Capsule</button>'),
    ('frontend/plateau/index.html', 'title="Un cylindre — colonne, tronc">＋ Cylindre</button>'),
    ('frontend/plateau/index.html', 'title="Une sphère">＋ Sphère</button>'),
    ('frontend/plateau/index.html', 'title="Poser ce maillage (niveau allégé : 2 500 triangles)">＋</button>'),
    ('frontend/plateau/index.html', 'title="Revenir au storyboard de l\'Atelier">← Atelier</a>'),
    ('frontend/plateau/index.html', '<button class="btn" id="btnPlay" title="Lire le mouvement en boucle (Espace)">▶</button>'),
    ('frontend/plateau/index.html', 'avec la caméra courante (K)">◆ Keyframe</button>'),
    ('frontend/plateau/index.html', 'download aria-disabled="true">↓ GLB</a>'),
    ('frontend/plateau/plateau.js', '${m.plan ? `<div class="${m.plan.ecart ? "ecart" : ""}">plan écrit : ${esc(m.plan.shot_type)}${m.plan.ecart ? ` — le cadre donne ${esc(m.shot_type)}` : " ✓"}</div>` : ""}`;'),
    ('frontend/plateau/plateau.js', '<button class="btn" data-x="${i}" title="Retirer ce keyframe">×</button>'),
    ('frontend/plateau/plateau.js', '$("#btnPlay").textContent = P.lecture ? "❚❚" : "▶";'),
    ('frontend/plateau/plateau.js', '${m.plan.ecart ? " — écart" : " ✓"}</div>'),
    ('frontend/plateau/plateau.js', '`<div class="avert">⚠ ${esc(a)}</div>`'),
    ('frontend/plateau/plateau.js', 'ouvrez-la depuis le storyboard (🎥).</div>`'),
    ('frontend/studio3d/index.html', "→ Atelier fal (rig d'un job)</button>"),
    ('frontend/studio3d/index.html', '⤒ Importer un modèle (OBJ, STL, glTF, GLB)'),
    ('frontend/studio3d/index.html', '→ ranger ce job au banc · gratuit</button>'),
    ('frontend/studio3d/index.html', '→ ouvrir Game Assets 3D (fal)</button>'),
    ('frontend/studio3d/index.html', '→ vues de la planche · gratuit</button>'),
    ('frontend/studio3d/index.html', '→ jeu de vues depuis les photos · gratuit</button>'),
    ('frontend/studio3d/index.html', 'les tâches Meshy, elles, continuent">❙❙ Pause</button>'),
    ('frontend/studio3d/index.html', '<button id="btnReplay" title="Réinitialise l\'affichage du graphe (aucune tâche annulée)">↺</button>'),
    ('frontend/studio3d/index.html', '<button class="next-step" id="goSprite">04 · Sprite Sheet →</button>'),
    ('frontend/studio3d/index.html', '<button class="next-step" id="goEtabli">07 · Établi 3D →</button>'),
    ('frontend/studio3d/vues.js', 'title="Régénérer CETTE vue seulement, avec un prompt corrigé">↻</button>'),
    ('frontend/studio3d/vues.js', 'title="Retirer le fond — local, gratuit">✂</button>'),
    ('frontend/studio3d/studio3d.js', '$("#btnPlay").textContent = S.playing ? "❙❙ Pause" : "▶ Lecture";'),
    ('frontend/studio3d/studio3d.js', '<span class="node-door">ouvrir →</span>'),
    ('frontend/etabli/index.html', 'title="Revenir au graphe du 3D Studio">← 3D Studio</button>'),
    ('frontend/etabli/index.html', 'title="Fermer la comparaison">A/B ✕</button>'),
    ('frontend/etabli/index.html', '(dossier sous assets/print3d)">→ Impression 3D</button>'),
    ('frontend/etabli/etabli.js', 'sp.textContent = SURPLOMB.actif ? "Surplombs ✓" : "Surplombs";'),
    ('frontend/etabli/etabli.js', 'tr.textContent = TRANCHES.actives ? "Tranches ✓" : "Tranches";'),
    ('frontend/etabli/etabli.js', '>${PLQ.masquees.has(x.cle) ? "◌" : "◉"}</button>'),
    ('frontend/etabli/aide.js', 'Le chapitre complet du guide, avec les ressources vérifiées →</a>`;'),
    ('frontend/etabli/etabli.css', '.etape.lourde b::after { content: " ⚠"; color: var(--amber); }'),
    ('frontend/shared/dz-champ-ia.js', 'if (e === "ecoute" || e === "prise") { txt = "■"; cls = "dzia-mstop"; titre = TITRE_STOP; }'),
    ('frontend/shared/dz-champ-ia.js', 'poserAttr(b, "aria-pressed", txt === "■" ? "true" : "false");'),
    ('frontend/atelier/atelier.js', 'Le moteur et son coût sont annoncés avant de lancer.">🧊 3D</button>'),
    ('frontend/atelier/atelier.js', 'd.chapter_id ? ico("dz-etat-origine") : "◇"}'),
]

print("[1] runtime et favicon")
_m = re.search(r'"dz-marque-icone-app": "([^"]+)"', lire("frontend/shared/icons/dz-icons.js"))
logo_url = _m.group(1) if _m else None
for p in PAGES:
    t = lire(p)
    i_s, i_i = t.find(SCRIPT), t.find(I18N)
    labo = [m.start() for m in re.finditer(r'<script\b[^>]*\bsrc="(?!/)[^"]+"', t)]
    check(f"1.1 {p} : dz-icons.css et dz-icons.js, une fois chacun", t.count(LIEN) == 1 and t.count(SCRIPT) == 1)
    check(f"1.2 {p} : le script après dz-i18n.js ({'présent' if i_i >= 0 else 'absent'}) et avant les scripts du lab",
          i_s >= 0 and (i_i < 0 or i_i < i_s) and labo and all(i_s < k for k in labo), (i_i, i_s, labo))
    # choix de l'utilisateur (G0 dd9e3307) : l'icône d'application est le LOGO réel, servi par /api/branding/logo
    # (l'URL de DZ_ICONS_IMAGES["dz-marque-icone-app"]), plus un dessin de la suite
    check(f"1.3 {p} : favicon = logo Deepotus (/api/branding/logo, PNG), une fois",
          t.count('<link rel="icon"') == 1 and '<link rel="icon" type="image/png" href="/api/branding/logo">' in t
          and logo_url == "/api/branding/logo", logo_url)

MARQUE = ["frontend/atelier/index.html", "frontend/atelier/preview.html", "frontend/materialforge/index.html",
          "frontend/etabli/index.html", "frontend/plateau/index.html", "frontend/studio3d/index.html",
          "frontend/atelier/atelier.js", "frontend/materialforge/materialforge.js", "frontend/etabli/etabli.js",
          "frontend/plateau/plateau.js", "frontend/studio3d/studio3d.js", "frontend/studio3d/fal.js",
          "frontend/studio3d/vues.js"]
poulpes = [f for f in MARQUE if "🐙" in sans_commentaires(lire(f), f)]
check("1.4 aucun emoji de marque 🐙 hors commentaires dans les pages et scripts du lot", not poulpes, poulpes)
for f in ("frontend/atelier/index.html", "frontend/atelier/preview.html"):
    check(f"1.5 {f} : la marque = le logo en image (dz-marque-poulpe)",
          '<div class="brand"><img class="dzi dzi--20" src="/api/branding/logo" alt=""> <b>Atelier Chapitre</b>' in lire(f))

print("[2] chaque site porte sa clé")
liste = json.loads(lire("docs/icones/suite-finale/implementation.json"))
sites = [x for x in liste if x["source"].startswith(PREFIXES) and x.get("cle_finale")]
check("2.0 la liste du lot : 190 sites à poser", len(sites) == 190, len(sites))
manques = []
for x in sites:
    if x["id"] in NON_POSABLES:
        continue
    parts = [s.strip() for s in x["source"].split(";")]
    premier = parts[0].split(":")[0]
    dossier = premier.rsplit("/", 1)[0]
    fichiers = {premier}
    for s in parts[1:]:
        nom = s.split(":")[0]
        fichiers.add(premier if nom.isdigit() else dossier + "/" + nom)
    if x["id"] in RELOGES:
        fichiers = {RELOGES[x["id"]]}
    for f in fichiers:
        if x["cle_finale"] not in RX_CLE.findall(sans_commentaires(lire(f), f)):
            manques.append((x["id"], f, x["cle_finale"]))
check("2.1 chaque entrée de la liste trouve sa clé dans le(s) fichier(s) de sa source", not manques, manques)
for f, attendu in ATTENDU.items():
    vu = dict(collections.Counter(RX_CLE.findall(sans_commentaires(lire(f), f))))
    check(f"2.2 {f} : compte figé des clés posées ({sum(attendu.values())})", vu == attendu,
          {k: (vu.get(k), attendu.get(k)) for k in set(vu) | set(attendu) if vu.get(k) != attendu.get(k)})

print("[3] plus aucun ancien glyphe remplacé")
restes = [(f, a) for f, a in ANCIENS if a in lire(f)]
check(f"3.1 aucun des {len(ANCIENS)} fragments remplacés ne subsiste", not restes, restes)
for f, attendu in GLYPHES_RESTANTS.items():
    t = sans_commentaires(lire(f), f)
    vu = {c: t.count(c) for c in GLYPHES if t.count(c)}
    check(f"3.2 {f} : glyphes restants = textes recensés {attendu or '{}'}", vu == attendu, vu)
for i, g in NON_POSABLES.items():
    x = next(e for e in sites if e["id"] == i)
    f = x["source"].split(":")[0]
    check(f"3.3 site non posable {i} : glyphe {g} gardé dans {f}", g in lire(f))

print("[4] aucune icône vide")
sprite = lire("frontend/shared/icons/dz-icons.svg")
symboles = set(re.findall(r'<symbol id="([^"]+)"', sprite))
posees = sorted({k for d in ATTENDU.values() for k in d})
check("4.1 chaque clé posée a son symbole dans le sprite", set(posees) <= symboles, sorted(set(posees) - symboles))
if not NODE:
    check("4.0 node disponible", False)
else:
    prog = """
global.window = {console: {warn: (m) => { window.__warn = (window.__warn || []).concat([m]); }}};
require(process.argv[1]);
const cles = JSON.parse(process.argv[2]);
const rendus = cles.map(k => window.dzIcone(k, {taille: 16, classe: "dzi--16"}));
console.log(JSON.stringify({vides: cles.filter((k, i) => !rendus[i].startsWith('<svg class="dzi dzi--16" width="16" height="16"')
  || !/<path|<g|<circle|<rect/.test(rendus[i])), warn: window.__warn || []}));
"""
    r = subprocess.run([NODE, "-e", prog, str(ROOT / "frontend/shared/icons/dz-icons.js"), json.dumps(posees)],
                       capture_output=True, text=True, encoding="utf-8")
    try:
        o = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        o = {"vides": ["?"], "warn": [r.stderr[-300:]]}
    check(f"4.2 le runtime rend les {len(posees)} clés posées, aucune vide ni inconnue", o["vides"] == [] and o["warn"] == [], o)

print("[5] fichiers partagés et syntaxe")
for nom in ("dz-champ-ia.js", "dz-maj.js"):
    a, b = ROOT / "frontend/shared" / nom, ROOT / "frontend/dist/shared" / nom
    check(f"5.1 {nom} : copie servie identique octet pour octet", a.read_bytes() == b.read_bytes())
    t = lire("frontend/shared/" + nom)
    check(f"5.2 {nom} : icônes tirées du sprite (<use>), sans dépendre du runtime dz-icons.js",
          '"/shared/icons/dz-icons.svg' in t and "dzIcone(" not in t and "innerHTML" not in t)
JS = ["frontend/atelier/atelier.js", "frontend/materialforge/materialforge.js", "frontend/etabli/etabli.js",
      "frontend/etabli/aide.js", "frontend/plateau/plateau.js", "frontend/studio3d/studio3d.js",
      "frontend/studio3d/fal.js", "frontend/studio3d/vues.js", "frontend/shared/dz-champ-ia.js", "frontend/shared/dz-maj.js"]
if NODE:
    for f in JS:
        r = subprocess.run([NODE, "--check", str(ROOT / f)], capture_output=True, text=True, encoding="utf-8")
        check(f"5.3 node --check {f}", r.returncode == 0, r.stderr[-300:])

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
