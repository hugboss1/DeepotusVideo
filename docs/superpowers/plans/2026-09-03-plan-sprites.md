# Game Assets — Sprites 2D : parité puis différenciant (plan d'implémentation)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** amener le Sprite Lab au niveau d'Aseprite/TexturePacker sur ce qu'un moteur attend d'une feuille (sortie native, tags et durées, exports Godot/atlas/Aseprite/Paper2D, post-traitement, éditeur), puis lui donner ce qu'aucun outil de sprites n'a : l'identité de la bible en 8 directions, la génération par prompt pixelisée en local, et un squelette Spine découpé depuis la feuille.

**Architecture :** tout le calcul d'image reste en Python pur PIL dans `backend/app/services/` (trois nouveaux modules à responsabilité unique : `sprite_anim.py` pour tags/durées, `sprite_post.py` pour outline/ombre/nettoyage, `sprite_export.py` pour les quatre exports écrits par code), branché dans `sprite_service._assemble` qui reste **le seul assembleur** (particules et séquences Kenney en héritent sans une ligne). Le navigateur `/spritelab` (page autonome, hors bundle) voit et manipule — réordonne, retouche, capture — et Python écrit, toujours via une route gardée. **Zéro octet du bundle n'est touché par ce plan.**

**Tech Stack :** Python 3.13 embarqué (stdlib + Pillow, **pas de numpy**), FastAPI (`backend/app/api/routes.py`), vanilla JS/CSS (`frontend/spritelab/`), `<model-viewer>` vendorisé (`/assets/model-viewer.min.js`) pour la capture 3D, bancs `pytest` lancés **un processus par fichier**.

---

## Périmètre

Les bacs de `docs/superpowers/plans/2026-09-02-balayage-meilleur-de-sa-classe.md` § R10a sont le périmètre **exact**.

| Bac | Id | Tâche(s) | Résumé |
|---|---|---|---|
| Parité | P1 | T1 | sortie native (pas d'agrandissement) + aperçu ×1/×2/×4 NEAREST |
| Parité | P2 | T2 | tags d'animation nommés + durée par image, dans le manifeste et chaque export |
| Parité | P3 | T3, T4, T5 | exports Godot `SpriteFrames .tres`, atlas JSON Hash façon TexturePacker, Aseprite `.ase`, Unreal Paper2D |
| Parité | P4 | T6 | outline 1 px, ombre plate ou décalée, nettoyage des orphelins, lissage — PIL pur, par image, avant la feuille |
| Parité | P5 | T7, T8 | réordonner / dupliquer / supprimer, pelure d'oignon, retouche pixel sur `/spritelab` |
| Différenciant | D1 | T9, T10 | 8 directions : T9 découpe la planche de la bible (gratuit, déterministe), T10 capture 8 orbites du modèle 3D de l'entité (R10e) |
| Différenciant | D2 | T11 | prompt → image → pipeline pixel local, zéro moteur nouveau |
| Différenciant | D3 | T12 | découpe en pièces, os, export Spine JSON |
| Écarté | E1, E2 | — | palette de projet verrouillée ; moteur Retro Diffusion — voir « Écarté » |

**Socle** (T0) : une source `images` pour `/assets/sprite`. Elle n'est dans aucun bac parce qu'elle n'est pas une fonctionnalité : c'est le canal par lequel D1 (8 vues), D2 (images du prompt) et **tous les bancs de ce plan** nourrissent la feuille sans passer par ffmpeg (mesuré : `backend/tests/test_sprite_service.py:85` exige `shutil.which("ffmpeg")` et échoue sinon).

**Liens, référencés sans être replanifiés :** R3 P3 (cohérence multi-références : `image_urls` multiple de Nano Banana Pro — D1 s'y branchera quand `image_providers.generate` acceptera plusieurs références ; d'ici là un panneau par direction), R10e (modèle 3D de l'entité : `BibleEntity.model3d_job` + `GET /api/assets/3d/{job}/glb` — D1 le lit, ne le produit pas).

## Ce que le terrain dit — mesuré le 03/09/2026

| Fait | Où | Conséquence |
|---|---|---|
| `_fit_into_cell` **agrandit** toujours au carré de cellule (`scale = min(size/w, size/h)`, NEAREST si pixel) | `sprite_service.py:241-261` | P1 = un mode « native » où l'on **pose** sans redimensionner |
| Les tailles de cellule sont `(128, 256, 512)` et `cell.size` est converti par `int()` | `sprite_service.py:27,65-69` | « native » est une valeur nouvelle du même champ, pas un champ de plus |
| Le GIF d'aperçu a **une** durée : `duration=max(20, int(1000 / fps))` | `sprite_service.py:432-434` | P2 passe une liste (PIL accepte `duration=[...]`) |
| Le manifeste v1 n'a ni tags ni durées ; le pack Unity est plat (JsonUtility) | `sprite_service.py:436-448`, `348-359` | P2 ajoute `anim` au manifeste ; Unity ne bouge pas |
| Le ZIP énumère 5 noms en dur | `sprite_service.py:363-377` | P3 ajoute les 4 exports à cette liste |
| `pixelate` rend le **natif** (`scale=1` forcé côté sprite) puis la cellule agrandit | `sprite_service.py:83-89`, `pixel_ops.py:157-176` | P4 s'applique **après** pixel, donc l'outline est 1 px **natif** |
| `MaxFilter`/`MinFilter`/`MedianFilter` existent dans `ImageFilter` ; aucun numpy | `pixel_ops.py:6`, `particle_service.py:20-23` | outline = dilatation `MaxFilter(3)` de l'alpha binaire |
| La particule et l'anim Kenney appellent `SS._assemble` directement | `particle_service.py:485-487, 537-539` | tout ce que gagne `_assemble` (tags, exports) leur profite |
| `/spritelab` est monté **hors bundle**, no-cache | `main.py:301-329` | tout écran de ce plan y vit ; aucun patcher |
| Le hub du bundle est un `iframe src:"/spritelab/"` (1 occurrence, `DzGameAssetsHub` ×2) | `frontend/dist/assets/index-BEOJX8L5.js` | inchangé |
| Ce worktree a **4** `.bak_*` du bundle, **0** suivis par git | `ls frontend/dist/assets` | la chaîne de patch **n'est pas rejouable ici** : raison de plus pour ne pas la toucher |
| `/tilelab` charge `spritelab.css` | `frontend/tilelab/index.html:7` | les règles CSS ajoutées sont **additives**, sous des classes nouvelles |
| Le lecteur zoome déjà ×1/×2/×4 avec `imageSmoothingEnabled = false` et `.pix` | `spritelab.js:405,413-420`, `index.html:176-178` | P1 côté écran = une option de cellule, le lecteur est prêt |
| `PUT /atelier/settings` persiste les préférences par `PREF_IDS` | `spritelab.js:70-97` | chaque contrôle nouveau entre dans `PREF_IDS` |
| Une route PNG-body gardée existe : signature, borne 2 Mio, cible confinée | `routes.py:9307` (`/etabli/vignette`) | même patron pour la retouche (T8) et le squelette (T11) |
| La planche personnage est **4 colonnes** `front, left, right, back` sur fond `_BG=(242,239,233)`, gouttière `_GUTTER=28`, corps `body_h=560` | `board_service.py:20-21,193-230` | D1 recoupe la planche par détection des gouttières, déterministe |
| La bible ne garde **pas** les fichiers des panneaux, seulement `ref_image` = planche composite | `routes.py:5583-5597` | D1 travaille sur la planche |
| Le GLB d'une entité : `model3d_job` + `model.glb`, servi par `GET /assets/3d/{job}/{fmt}` | `routes.py:5341-5343, 1197` | D1 3D charge `/api/assets/3d/{job}/glb` dans `<model-viewer>` |
| `<model-viewer>.toBlob()` est le patron de capture du dépôt (« API officielle 3.3.3 ») | `cardforge/js/mod-forge3d.js:6304-6323` | D1 3D capture 8 orbites, Python écrit |
| `image_providers.build_banana_request` passe `image_urls: [image_url]` — **une** référence | `image_providers.py:126` | R3 P3, pas ici |
| `LI.SOURCES` connaît `"sprites"` ; `/images/generate` accepte `source` | `routes.py:1529, 4424-4438` | D2 signe ses images `sprites` |
| `/api/persona` rend `vibe_keywords`, `brand_colors` | `routes.py:108-110`, `personas/deepotus.json` | D2 injecte 3 mots-clés, jamais un nom d'artiste |
| `run-tests.ps1` lance **un processus par fichier** et bascule en mode script si le fichier appelle ses tests au niveau module | `scripts/run-tests.ps1:57-68` | chaque banc porte un `__main__` autonome |

## Coût de patch

| Tâche | Bundle | `/spritelab` (autonome) | Backend | Patcher à écrire |
|---|---|---|---|---|
| T0 source images | 0 | 0 | `sprite_service.py`, `routes.py` | aucun |
| T1 P1 native | 0 | `index.html` (1 option), `spritelab.js` (1 ligne) | `sprite_service.py` | aucun |
| T2 P2 tags/durées | 0 | fieldset « Animation » | `sprite_anim.py`, `sprite_service.py` | aucun |
| T3 P3a Godot + atlas | 0 | 2 boutons d'export | `sprite_export.py`, `routes.py` | aucun |
| T4 P3b `.ase` | 0 | 1 bouton | `sprite_export.py` | aucun |
| T5 P3c Paper2D | 0 | 1 bouton | `sprite_export.py` | aucun |
| T6 P4 post | 0 | fieldset « Post-traitement » | `sprite_post.py`, `sprite_service.py` | aucun |
| T7 P5a éditeur | 0 | bande « Éditeur » | `routes.py` (reassemble), `sprite_service.py` | aucun |
| T8 P5b pelure + retouche | 0 | canevas d'édition | `routes.py` (PUT frame) | aucun |
| T9 D1a planche | 0 | onglet « Bible » | `sprite_directions.py`, `routes.py` | aucun |
| T10 D1b 8 orbites 3D | 0 | `<model-viewer>` caché + 8 captures | `routes.py` (dépôt de vue) | aucun |
| T11 D2 prompt | 0 | onglet « Prompt » | 0 | aucun |
| T12 D3 squelette | 0 | mode « Squelette » | `sprite_skeleton.py`, `routes.py` | aucun |
| T13 mutations | 0 | 0 | `tests/mutations_sprites.py` | aucun |

Le hub Game Assets (`scripts/patch_bundle_spritelab.py`) montre déjà `/spritelab/` en iframe : rien à y changer. Si un jour un sous-onglet doit s'ajouter au hub, ce sera un patcher chaîné **après** `libsend` (queue mesurée le 28/08), rejoué par `python scripts/repatch_all.py --from <tag>` — hors de ce plan.

## Références vérifiées

- **Aseprite, `docs/ase-file-specs.md`** (raw.githubusercontent.com/aseprite/aseprite/main, relu le 03/09/2026 par `WebFetch`) : en-tête 128 octets (`DWORD size, WORD 0xA5E0, WORD frames, WORD w, WORD h, WORD depth, DWORD flags, WORD speed, DWORD 0, DWORD 0, BYTE transparent, BYTE[3], WORD ncolors, BYTE pw, BYTE ph, SHORT gx, SHORT gy, WORD gw, WORD gh, BYTE[84]`) ; en-tête de frame 16 octets (`DWORD bytes, WORD 0xF1FA, WORD old chunks, WORD duration ms, BYTE[2], DWORD chunks`) ; chunk = `DWORD size (en-tête compris), WORD type` ; calque 0x2004 (`WORD flags, WORD type, WORD child, WORD w, WORD h, WORD blend, BYTE opacity, BYTE[3], STRING name`) ; cel 0x2005 (`WORD layer, SHORT x, SHORT y, BYTE opacity, WORD type, SHORT z, BYTE[5]`, puis pour le type 2 `WORD w, WORD h, ZLIB(raw RGBA)`) ; tags 0x2018 (`WORD n, BYTE[8]`, puis par tag `WORD from, WORD to, BYTE direction 0..3, WORD repeat, BYTE[6], BYTE[3] rgb, BYTE 0, STRING name`) ; `STRING = WORD len + UTF-8` ; « For color depths more than 8bpp, palettes are optional ».
- **Godot 4, `SpriteFrames`** (docs.godotengine.org/en/stable/classes/class_spriteframes.html, 03/09/2026) : `add_frame(anim, texture, duration=1.0)` — « `duration` specifies the relative duration » ; `absolute_duration = relative_duration / (animation_fps * abs(playing_speed))` ; `set_animation_speed` en images par seconde ; boucle par `set_animation_loop`. Un `.tres` est un texte (R10a). **Non vérifié** : la sérialisation exacte du `.tres` (`format=3`, `animations = [{...}]`) est écrite de mémoire — l'utilisateur la vérifie en ouvrant le fichier dans Godot 4 ; le banc ne mesure que **notre** fichier.
- **TexturePacker, JSON Hash** (codeandweb.com, R10a 03/09/2026) : `frame`, `rotated`, `trimmed`, `spriteSourceSize`, `sourceSize` ; `meta.image`, `meta.size`, `meta.scale`.
- **Unreal Paper2D** (docs.unrealengine.com 4.27 « Paper 2D Import Options » et « PaperSpriteSheetImportFactory », codeandweb.com tutoriel Paper2D, relus le 03/09/2026 par `WebSearch`/`WebFetch`) : l'importateur « imports a sprite sheet (and associated paper sprites and textures) from a JSON file exported from Adobe Flash CS6, Texture Packer » ; « the importer assumes that all of the sprites are frames of an animation, so it will always create a Flipbook » ; « Paper2D will automatically group sprites which only differ in a number » ; TexturePacker exporte un `.paper2dsprites`. **Non vérifié** : le jeu de champs exact lu par l'importateur (pivot, trim) — T5 commence par la mesure.
- **Spine, JSON export format** (esotericsoftware.com/spine-json-format, relu le 03/09/2026 par `WebFetch`) : clés de tête `skeleton, bones, slots, skins, events, animations, ik, transform, path` ; `skeleton {hash, spine, x, y, width, height, images, audio, fps}` (tout optionnel) ; `bones [{name (requis), parent, length, x, y, rotation, scaleX, scaleY, shearX, shearY, color}]`, défauts `length=0, x=y=0, rotation=0, scale=1` ; `slots [{name, bone (requis), attachment, color, blend}]` ; **`skins` est un TABLEAU de `{name, attachments}`** où `attachments` est `slot -> nom d'attachement -> objet` — la forme « `skins.default.slot.att` » (carte de cartes) est celle de Spine 3.7 et **c'est ce que la mémoire produit** : mesuré et corrigé le 03/09 ; attachement `region {type, path, name, x, y, scaleX, scaleY, rotation, width, height, color}` ; `animations[nom].bones[os].rotate [{time, angle, curve}]` et `.translate [{time, x, y, curve}]`. **Version visée : Spine 3.8** (`skeleton.spine = "3.8.99"`) — c'est la version où `skins` est un tableau ET où la clé de rotation s'appelle `angle`.
- **Retro Diffusion** (retrodiffusion.ai, R10a 03/09) : écarté par la réponse 7, gardé en note.
- **De mémoire, non vérifiés, donc jamais un argument ici** : DragonBones (D3 n'écrit que Spine JSON), Pixel Composer, Scenario, la transparence par défaut de `<model-viewer>.toBlob()` (T9 la mesure sur le premier PNG capturé).

## Règles du plan

1. **Le mesuré prime.** Chaque tâche commence par une mesure (grep, banc rouge, `WebFetch`) et son POURQUOI la cite.
2. **Bancs autonomes.** `backend/tests/test_<x>.py` se lance par `python tests/test_<x>.py` depuis `backend/`, un processus par fichier, UTF-8 forcé dans `__main__` ; jamais `pytest tests`. Chaque banc pose son environnement (`DATABASE_URL`, `IMAGES_FOLDER`, `OUTPUTS_FOLDER`) **avant** tout import de `app`.
3. **Bancs-miroirs.** On lit la feuille PNG (PIL : dimensions, pixels), le JSON/`.tres`/`.ase` écrits (octets, champs), jamais le code qui prétend les produire ; on compte les assertions.
4. **Le navigateur voit et manipule, Python écrit.** Aucun PNG, JSON ou `.ase` n'est fabriqué côté client ; la retouche et la capture passent par une route gardée.
5. **Commits** : sujet SANS accents, corps accentué, pied `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`, pas de guillemets doubles dans `-m` (utiliser `-F` avec un fichier de message, comme ci-dessous).
6. **Pas de numpy.** Boucles Python sur `load()` seulement sur des images natives (≤ 512²), et l'on dit le coût mesuré.

Patron de message de commit (fichier `msg.txt` écrit avec `Write`, puis `git commit -F msg.txt`) :

```
sprites : T0 - la source images nourrit la feuille sans ffmpeg

Pourquoi : le banc existant exige ffmpeg (test_sprite_service.py:85) ; D1 et D2
livrent des images, pas des vidéos.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

Patron d'en-tête de banc (repris tel quel par chaque nouveau fichier de test) :

```python
"""<Ce que le banc tient — une phrase.>

Run: python tests/test_<x>.py   (depuis backend/ ; un processus par fichier)
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent

# ... tests ...

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
```

Sortie attendue d'un banc vert : `N passed in X.XXs` et code de sortie 0 ; d'un banc rouge : `FAILED tests/test_<x>.py::<nom> - AssertionError...` et code 1.

---

## Lot 1 — parité

### Tâche 0 — socle : la source `images`

**Files :**
- Modify: `backend/app/services/sprite_service.py:26-27` (constantes), `:120-166` (`resolve_source`), `:481-495` (extraction)
- Modify: `backend/app/api/routes.py:1374-1414` (fail-fast + titre)
- Test: `backend/tests/test_sprite_images_source.py` (créer)

**Pourquoi (mesuré) :** `resolve_source` ne connaît que `job|upload|video` (`sprite_service.py:130-166`) et `generate_sprites` appelle toujours ffmpeg (`:486`). D1 et D2 produisent des PNG de la Library ; les bancs de ce plan doivent tourner sans ffmpeg.

- [ ] **Étape 1 : écrire le banc rouge**

```python
"""Source `images` du Sprite Lab : des PNG de la Library deviennent les frames,
sans ffmpeg ; garde des noms ; feuille lue en PIL.

Run: python tests/test_sprite_images_source.py
"""
# ... en-tête patron (voir « Règles du plan ») ...
import asyncio  # noqa: E402
import json  # noqa: E402


def _carre(nom: str, couleur, taille=(40, 24)):
    from app.config import settings
    im = Image.new("RGBA", taille, (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([4, 4, taille[0] - 5, taille[1] - 5], fill=couleur)
    im.save(settings.images_path / nom)
    return nom


def _run(payload, job):
    from app.services import sprite_service as S
    return asyncio.run(S.generate_sprites(payload, job))


def test_resolve_images_refuse_les_noms_qui_sortent_de_la_library():
    from app.services import sprite_service as S
    _carre("ok.png", (200, 30, 30, 255))
    assert [p.name for p in S.resolve_images({"filenames": ["ok.png"]})] == ["ok.png"]
    for bad in ({}, {"filenames": []}, {"filenames": "ok.png"},
                {"filenames": ["../ok.png"]}, {"filenames": ["absent.png"]},
                {"filenames": ["ok.png"] * 65}):
        with pytest.raises(ValueError):
            S.resolve_images(bad)


def test_la_feuille_vient_des_images_sans_ffmpeg():
    from app.config import settings
    noms = [_carre(f"f{i}.png", (40 * i + 40, 30, 30, 255)) for i in range(4)]
    r = _run({"source": {"kind": "images", "filenames": noms},
              "remove_bg": "none", "cell": {"size": 128}}, "j-img")
    d = settings.outputs_path / "sprites" / "j-img"
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    assert m["source"]["kind"] == "images" and m["source"]["file"] == "f0.png"
    assert len(m["frames"]) == 4 and r["frames"] == 4
    with Image.open(d / "sheet.png") as sh:
        assert sh.size == (256, 256)                 # 2×2 cellules de 128
        px = sh.convert("RGBA").getpixel((64, 64))
    assert px[3] == 255 and px[0] == 40               # frame 0 au centre de sa cellule
    assert not (d / "_raw").exists()
```

- [ ] **Étape 2 : le voir rouge**

Run: `cd backend && python tests/test_sprite_images_source.py`
Expected: `2 failed` — `AttributeError: module ... has no attribute 'resolve_images'`, puis `ValueError: Unknown source kind: 'images'`.

- [ ] **Étape 3 : implémenter dans `sprite_service.py`**

Sous `_CELL_SIZES` :

```python
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
```

Nouvelle fonction avant `resolve_source` :

```python
def resolve_images(source: dict) -> list[Path]:
    """kind 'images' : {filenames: [...]} — 1 à 64 noms NUS d'images de la
    Library (images_path). ValueError lisible sinon ; un nom avec un chemin
    est refusé tel quel, jamais « nettoyé » (un nom est un identifiant)."""
    from app.config import settings
    names = (source or {}).get("filenames")
    if not isinstance(names, (list, tuple)) or not names:
        raise ValueError("source.filenames must be a non-empty list (1-64)")
    if len(names) > 64:
        raise ValueError("source.filenames: 64 images at most")
    out = []
    for raw in names:
        fn = Path(str(raw or "")).name
        p = settings.images_path / fn
        if not fn or fn != str(raw) or p.suffix.lower() not in _IMAGE_EXTS \
                or not p.is_file():
            raise ValueError(f"Image not found in the Library: {raw!r}")
        out.append(p)
    return out
```

Dans `resolve_source`, avant `if kind == "job":` :

```python
    if kind == "images":
        return resolve_images(source)
```

et la signature devient `-> Path | list[Path]` ; le message final liste `job|upload|video|images`.

Dans `generate_sprites`, remplacer le bloc `src = ... ; duration = ... ; raw = ...` (lignes 482-488) par :

```python
    src = await resolve_source(payload.get("source") or {})
    if isinstance(src, list):
        # T0 : images de la Library -> copies RGBA numérotées, même contrat
        # que l'extraction ffmpeg (raw_0001.png…), donc keep/sampled inchangés
        duration = 0.0
        await _step("Copying images", 15)

        def _copy_png(p: Path, dest: Path):
            from PIL import Image as _I
            dest.parent.mkdir(parents=True, exist_ok=True)
            with _I.open(p) as im:
                im.convert("RGBA").save(dest, format="PNG")

        raw = []
        for i, p in enumerate(src):
            dest = raw_dir / f"raw_{i + 1:04d}.png"
            await asyncio.to_thread(_copy_png, p, dest)
            raw.append(dest)
        src_name = src[0].name
    else:
        duration = await asyncio.to_thread(_ffprobe_duration, src)
        await _step("Extracting frames", 15)
        raw = await asyncio.to_thread(_extract_frames, src, opts["fps"], raw_dir)
        src_name = src.name
    if not raw:
        raise RuntimeError("no frames from the source")
```

et dans `source_info`, `"file": src.name` devient `"file": src_name`.

Dans `routes.py:1400` (titre du job) : `title=(body.get("title") or f"Sprites · {(src[0] if isinstance(src, list) else src).stem}")`.

- [ ] **Étape 4 : vert, puis l'ancien banc**

Run: `cd backend && python tests/test_sprite_images_source.py`
Expected: `2 passed`.
Run: `cd backend && python -m pytest tests/test_sprite_service.py -q -k normalize`
Expected: `4 passed` (les tests sans ffmpeg ; le reste demande le PATH de l'app installée, inchangé).

- [ ] **Étape 5 : commit** — `git add backend/app/services/sprite_service.py backend/app/api/routes.py backend/tests/test_sprite_images_source.py` puis `git commit -F msg.txt` (sujet : `sprites : T0 - la source images nourrit la feuille sans ffmpeg`).

### Tâche 1 — P1 : sortie native et aperçu à l'échelle entière

**Files :**
- Modify: `backend/app/services/sprite_service.py:61-72` (cellule), `:241-261` (fit), `:381-462` (`_assemble`)
- Modify: `frontend/spritelab/index.html:116-118`, `frontend/spritelab/spritelab.js:330-331`
- Test: `backend/tests/test_sprite_native.py` (créer)

**Pourquoi (mesuré) :** `_fit_into_cell` calcule `scale = min(size / w, size / h)` et redimensionne **toujours** (`sprite_service.py:250-254`) ; une frame pixel-art de 32 px livrée en cellule 128 est donc agrandie ×4 dans la feuille — le jeu doit la réduire, et perd les pixels. Le lecteur, lui, sait déjà zoomer en NEAREST (`spritelab.js:405`, `.pix` à `index.html:178`).

- [ ] **Étape 1 : banc rouge**

```python
"""P1 — cellule « native » : la feuille pose les frames à leur taille,
sans agrandissement ; les octets d'une frame sont ceux de la source.

Run: python tests/test_sprite_native.py
"""
# ... en-tête patron ...
import asyncio  # noqa: E402
import json  # noqa: E402


def _png(nom, taille, couleur):
    from app.config import settings
    im = Image.new("RGBA", taille, (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([1, 1, taille[0] - 2, taille[1] - 2], fill=couleur)
    im.save(settings.images_path / nom)
    return nom, im


def test_normalize_accepte_native_et_refuse_le_reste():
    from app.services import sprite_service as S
    assert S.normalize_opts({"cell": {"size": "native"}})["cell_size"] == 0
    assert S.normalize_opts({"cell": {"size": 256}})["cell_size"] == 256
    for bad in ({"cell": {"size": "natif"}}, {"cell": {"size": 0}}, {"cell": {"size": 64}}):
        with pytest.raises(ValueError):
            S.normalize_opts(bad)


def test_la_feuille_native_ne_redimensionne_pas():
    from app.config import settings
    from app.services import sprite_service as S
    noms, ims = zip(*[_png(f"n{i}.png", (24, 16), (10 * i + 20, 200, 30, 255)) for i in range(3)])
    r = asyncio.run(S.generate_sprites(
        {"source": {"kind": "images", "filenames": list(noms)},
         "cell": {"size": "native", "align": "feet"}, "columns": 3}, "j-nat"))
    d = settings.outputs_path / "sprites" / "j-nat"
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    assert m["native"] is True and m["grid"] == {"cols": 3, "rows": 1, "cell_w": 24, "cell_h": 24}
    with Image.open(d / "sheet.png") as sh:
        assert sh.size == (72, 24)
        # frame 1 posée « pieds » : ses 16 lignes occupent y = 8..23, octets identiques
        crop = sh.convert("RGBA").crop((24, 8, 48, 24))
    assert crop.tobytes() == ims[1].tobytes()
    assert r["grid"]["cell_w"] == 24
```

- [ ] **Étape 2 : rouge** — Run: `cd backend && python tests/test_sprite_native.py` — Expected: `2 failed` (`ValueError: cell.size must be one of (128, 256, 512)`).

- [ ] **Étape 3 : implémenter**

`normalize_opts`, bloc cellule (remplace les lignes 64-69) :

```python
    raw_size = cell.get("size")
    if raw_size in (None, "", 256):
        size = 256
    elif str(raw_size).lower() == "native":
        size = 0                       # P1 : sentinelle « pas d'agrandissement »
    else:
        try:
            size = int(raw_size)
        except (TypeError, ValueError):
            raise ValueError(f"cell.size must be 'native' or one of {_CELL_SIZES}")
        if size not in _CELL_SIZES:
            raise ValueError(f"cell.size must be 'native' or one of {_CELL_SIZES}")
```

Nouvelle fonction sous `_fit_into_cell` :

```python
def _place_into_cell(img, size: int, align: str):
    """Pose SANS redimensionner dans une cellule size×size (P1 native) :
    centré en x ; 'feet' colle le bas, 'center' centre. L'image est déjà
    RGBA et tient dans la cellule (size = plus grande dimension mesurée)."""
    from PIL import Image
    cell = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    w, h = img.size
    x = (size - w) // 2
    y = (size - h) if align == "feet" else (size - h) // 2
    cell.paste(img, (x, y), img)
    return cell
```

Dans `_assemble`, après la passe 1 (`offset = ...`) :

```python
    native = size == 0
    if native:
        # P1 : la cellule est la plus grande dimension des frames (recadrées
        # si tight), mesurée — jamais un agrandissement
        mx = 1
        for path, _ in frame_files:
            with Image.open(path) as im:
                w, h = (union[2] - union[0], union[3] - union[1]) if union else im.size
            mx = max(mx, w, h)
        size = mx
```

et dans la passe 2, `cell = _fit_into_cell(im, size, align, resample)` devient :

```python
            cell = _place_into_cell(im, size, align) if native \
                else _fit_into_cell(im, size, align, resample)
```

Le manifeste gagne `"native": native,` après `"align"`. Le pack Unity lit `manifest["grid"]["cell_w"]` : inchangé.

`index.html:117` : `<select id="cellSize"><option>128</option><option selected>256</option><option>512</option><option value="native">native (sans agrandissement)</option></select>`.

`spritelab.js:330` : `cell: { size: $("#cellSize").value === "native" ? "native" : parseInt($("#cellSize").value, 10),`. Dans `runStarter` (`:538`) `parseInt(...) || 512` reste : les particules gardent leur canevas.

- [ ] **Étape 4 : vert** — Run: `cd backend && python tests/test_sprite_native.py` — Expected: `2 passed`. Puis `python tests/test_sprite_images_source.py` — `2 passed`.

- [ ] **Étape 5 : commit** — sujet `sprites : T1 - la cellule native pose sans agrandir`.

### Tâche 2 — P2 : tags d'animation et durée par image

**Files :**
- Create: `backend/app/services/sprite_anim.py`
- Modify: `backend/app/services/sprite_service.py:31-111` (`normalize_opts`), `:381-462` (`_assemble`)
- Modify: `frontend/spritelab/index.html:153` (après le fieldset pixel), `frontend/spritelab/spritelab.js:71-73` (`PREF_IDS`), `:322-336` (corps de la requête), `:578-590` (câblage)
- Test: `backend/tests/test_sprite_anim.py` (créer)

**Pourquoi (mesuré) :** le GIF d'aperçu n'a qu'**une** durée pour toute la feuille — `duration=max(20, int(1000 / fps))` à `sprite_service.py:432-434` — et le manifeste (`:436-448`) ne porte ni tag ni durée par image. Un moteur qui lit `manifest.json` ne peut donc pas savoir que les images 0-2 sont `idle` et 3-5 `run`, ni qu'une pose tenue dure 250 ms. C'est le champ que les trois exports de T3-T5 doivent écrire ; sans lui, ils écriraient une seule animation anonyme. Mesuré aussi : **personne ne lit `manifest["version"]`** (grep sur `frontend/spritelab/`, `routes.py`, `sprite_service.py`, `particle_service.py` : 0 occurrence) — le passage en v2 ne casse rien.

- [ ] **Étape 1 : écrire le banc rouge**

Créer `backend/tests/test_sprite_anim.py` :

```python
"""P2 — tags d'animation et duree par image : le manifeste les porte, le GIF
d'apercu porte une duree PAR IMAGE, et les bornes refusent en le disant.

Run: python tests/test_sprite_anim.py   (depuis backend/)
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio  # noqa: E402
import json  # noqa: E402

import pytest  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

TAGS = [{"name": "idle", "from": 0, "to": 2, "direction": "forward"},
        {"name": "run", "from": 3, "to": 5, "direction": "pingpong",
         "repeat": 3}]
DUREES = [80, 80, 80, 150, 150, 150]


def _png(nom, couleur, taille=(24, 24)):
    from app.config import settings
    im = Image.new("RGBA", taille, (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([2, 2, taille[0] - 3, taille[1] - 3],
                                 fill=couleur)
    im.save(settings.images_path / nom)
    return nom


def test_normalize_anim_borne_tout_ce_qui_entre():
    from app.services import sprite_anim as A
    ok = A.normalize_anim({"tags": TAGS, "durations": DUREES}, 6)
    assert [t["name"] for t in ok["tags"]] == ["idle", "run"]
    assert ok["tags"][1]["direction"] == "pingpong"
    assert ok["tags"][1]["repeat"] == 3
    assert ok["tags"][0]["repeat"] == 0          # defaut : boucle infinie
    assert ok["durations"] == DUREES
    assert A.normalize_anim(None, 6, fps=8)["durations"] == [125] * 6
    assert A.spans({"tags": []}, 4) == [("default", 0, 3)]
    assert A.spans(ok, 6) == [("idle", 0, 2), ("run", 3, 5)]
    mauvais = [
        {"tags": [{"name": "idle", "from": 0, "to": 6}]},       # to >= n
        {"tags": [{"name": "idle", "from": 3, "to": 1}]},       # from > to
        {"tags": [{"name": "", "from": 0, "to": 1}]},           # nom vide
        {"tags": [{"name": "a/b", "from": 0, "to": 1}]},        # nom sale
        {"tags": [{"name": "x", "from": 0, "to": 1},
                  {"name": "x", "from": 2, "to": 3}]},          # doublon
        {"tags": [{"name": "x", "from": 0, "to": 1,
                   "direction": "spin"}]},                      # sens inconnu
        {"tags": [{"name": f"t{i}", "from": 0, "to": 1}
                  for i in range(17)]},                         # 17 > 16
        {"durations": [80] * 5},                                # mauvaise longueur
        {"durations": [80] * 5 + [9]},                          # 9 ms < 10
        {"durations": "80"},                                    # pas une liste
        {"tags": "idle"},                                       # pas une liste
    ]
    for m in mauvais:
        with pytest.raises(ValueError):
            A.normalize_anim(m, 6)


def test_le_manifeste_et_le_gif_portent_une_duree_par_image():
    from app.config import settings
    from app.services import sprite_service as S
    noms = [_png(f"a{i}.png", (30 + 40 * i, 90, 200, 255)) for i in range(6)]
    asyncio.run(S.generate_sprites(
        {"source": {"kind": "images", "filenames": noms},
         "cell": {"size": 128}, "columns": 3, "fps_sample": 8,
         "anim": {"tags": TAGS, "durations": DUREES}}, "j-anim"))
    d = settings.outputs_path / "sprites" / "j-anim"
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    assert m["version"] == 2
    assert [t["name"] for t in m["anim"]["tags"]] == ["idle", "run"]
    assert m["anim"]["durations"] == DUREES
    assert [f["duration_ms"] for f in m["frames"]] == DUREES
    # le GIF, LU : PIL ecrit les durees en centisecondes, 80 et 150 sont
    # multiples de 10 donc l'aller-retour est exact
    lues = []
    with Image.open(d / "preview.gif") as g:
        assert g.n_frames == 6
        for i in range(g.n_frames):
            g.seek(i)
            lues.append(g.info["duration"])
    assert lues == DUREES


def test_un_tag_qui_deborde_la_selection_du_filmstrip_est_refuse():
    """La route valide AVANT de connaitre le nombre d'images (n=None, borne
    a 64) ; `keep` peut ensuite reduire la feuille a 3 images. Sans le second
    appel dans _assemble, le tag `run` 3-5 passerait et Godot lirait une
    animation vide."""
    from app.config import settings
    from app.services import sprite_service as S
    noms = [_png(f"b{i}.png", (200, 40 * i + 30, 60, 255)) for i in range(6)]
    S.normalize_opts({"source": {"kind": "images", "filenames": noms},
                      "anim": {"tags": TAGS}})            # n inconnu : passe
    with pytest.raises(ValueError) as e:
        asyncio.run(S.generate_sprites(
            {"source": {"kind": "images", "filenames": noms},
             "keep": [0, 1, 2], "cell": {"size": 128},
             "anim": {"tags": TAGS}}, "j-deborde"))
    assert "run" in str(e.value) and "to < 3" in str(e.value)
    assert not (settings.outputs_path / "sprites" / "j-deborde"
                / "sheet.png").is_file()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
```

- [ ] **Étape 2 : le voir rouge**

Run: `cd backend && python tests/test_sprite_anim.py`
Expected: `3 failed` — `ModuleNotFoundError: No module named 'app.services.sprite_anim'`.

- [ ] **Étape 3 : écrire `sprite_anim.py`**

Créer `backend/app/services/sprite_anim.py` :

```python
"""P2 — tags d'animation et duree par image (plan sprites, tache 2).

UN SEUL PROPRIETAIRE DE LA VALIDATION, APPELE DEUX FOIS, et il faut le dire.
`normalize_anim` tourne une premiere fois dans `sprite_service.normalize_opts`
pour le refus rapide de la route — a ce moment le nombre d'images n'est PAS
connu (le filmstrip peut encore en retirer), donc `n=None` et les bornes de
tag sont testees contre MAX_FRAMES ; puis une seconde fois dans `_assemble`,
ou `n` est enfin le vrai. Sans le second appel un tag qui deborde la
selection passerait, et Godot lirait une animation vide (banc
`test_un_tag_qui_deborde_la_selection_du_filmstrip_est_refuse`).

Pur stdlib : ce module ne connait ni PIL, ni FastAPI, ni les reglages.
"""
from __future__ import annotations

import re

# le nom d'un tag devient un identifiant Godot (`&"idle"`) et une STRING
# Aseprite : on interdit ce qui casserait l'un des deux plutot que d'echapper
# differemment dans quatre exports.
_NOM = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _-]{0,31}$")
DIRECTIONS = ("forward", "reverse", "pingpong", "pingpong_reverse")
MAX_TAGS = 16
MAX_FRAMES = 64          # meme plafond que normalize_opts.max_frames
DUREE_MIN, DUREE_MAX = 10, 10000


def normalize_anim(spec, n: int | None, fps: int = 8) -> dict:
    """{tags, durations} normalise. `n` = nombre d'images de la feuille, ou
    None quand il n'est pas encore connu. ValueError lisible sinon (la route
    la transforme en 400)."""
    if spec in (None, ""):
        spec = {}
    if not isinstance(spec, dict):
        raise ValueError("anim must be an object {tags, durations}")
    borne = MAX_FRAMES if n is None else n

    brut = spec.get("tags") or []
    if not isinstance(brut, (list, tuple)):
        raise ValueError("anim.tags must be a list of {name, from, to}")
    if len(brut) > MAX_TAGS:
        raise ValueError(f"anim.tags: {MAX_TAGS} tags at most")
    tags, vus = [], set()
    for t in brut:
        if not isinstance(t, dict):
            raise ValueError("anim.tags: each tag is an object "
                             "{name, from, to, direction, repeat}")
        nom = str(t.get("name") or "")
        if not _NOM.match(nom):
            raise ValueError(
                f"anim tag name {nom!r}: 1-32 characters, letters, digits, "
                "space, _ or -, starting with a letter or a digit")
        if nom in vus:
            raise ValueError(f"anim tag name {nom!r} appears twice")
        vus.add(nom)
        try:
            a, b = int(t.get("from")), int(t.get("to"))
        except (TypeError, ValueError):
            raise ValueError(f"anim tag {nom!r}: from/to must be integers")
        if not 0 <= a <= b < borne:
            raise ValueError(f"anim tag {nom!r}: 0 <= from <= to < {borne} "
                             f"(got from={a}, to={b})")
        sens = str(t.get("direction") or "forward").lower()
        if sens not in DIRECTIONS:
            raise ValueError(f"anim tag {nom!r}: direction must be one of "
                             f"{', '.join(DIRECTIONS)}")
        try:
            rep = int(t.get("repeat") or 0)
        except (TypeError, ValueError):
            raise ValueError(f"anim tag {nom!r}: repeat must be an integer")
        if not 0 <= rep <= 65535:
            raise ValueError(f"anim tag {nom!r}: repeat must be 0-65535 "
                             "(0 = forever)")
        tags.append({"name": nom, "from": a, "to": b,
                     "direction": sens, "repeat": rep})

    dur = spec.get("durations")
    if dur in (None, ""):
        defaut = max(DUREE_MIN, int(round(1000 / max(1, int(fps)))))
        durations = None if n is None else [defaut] * n
    else:
        if not isinstance(dur, (list, tuple)):
            raise ValueError("anim.durations must be a list of milliseconds")
        if len(dur) > MAX_FRAMES:
            raise ValueError(f"anim.durations: {MAX_FRAMES} values at most")
        if n is not None and len(dur) != n:
            raise ValueError(f"anim.durations: {len(dur)} values for {n} "
                             "frames — give exactly one per frame")
        durations = []
        for v in dur:
            try:
                ms = int(v)
            except (TypeError, ValueError):
                raise ValueError("anim.durations: milliseconds are integers")
            if not DUREE_MIN <= ms <= DUREE_MAX:
                raise ValueError(f"anim.durations: {ms} ms is out of range "
                                 f"({DUREE_MIN}-{DUREE_MAX})")
            durations.append(ms)
    return {"tags": tags, "durations": durations}


def spans(anim: dict, n: int) -> list[tuple[str, int, int]]:
    """(nom, from, to) par animation. Sans tag : UNE animation « default »
    qui couvre la feuille. C'est le SEUL endroit qui decide de ce repli — les
    quatre exports le partagent, sinon Godot nommerait `default` la ou
    Aseprite ne nommerait rien."""
    tags = (anim or {}).get("tags") or []
    if not tags:
        return [("default", 0, max(0, n - 1))]
    return [(t["name"], t["from"], t["to"]) for t in tags]
```

- [ ] **Étape 4 : brancher dans `sprite_service.py`**

Dans `normalize_opts`, juste avant le `return` (après le bloc `keep`) :

```python
    # P2 : refus rapide sur la FORME des tags — le nombre d'images n'est pas
    # encore connu ici (le filmstrip peut en retirer), d'où n=None. La vraie
    # borne est reposée dans _assemble, seul endroit qui connaisse n.
    from app.services.sprite_anim import normalize_anim
    anim = body.get("anim")
    normalize_anim(anim, None, fps)
```

et le dictionnaire rendu gagne `"anim": anim,`.

Dans `_assemble`, juste après `n = len(frame_files)` :

```python
    from app.services.sprite_anim import normalize_anim
    anim = normalize_anim(opts.get("anim"), n, opts["fps"])
```

`opts.get` et non `opts[...]` : `particle_service` construit ses `sheet_opts` à la main (`particle_service.py:486-488` et `:537-538`) et n'y met pas `anim` — une clé obligatoire ferait planter les particules et les séquences Kenney.

Dans la passe 2, `manifest_frames.append({...})` gagne une ligne :

```python
            "duration_ms": anim["durations"][i],
```

Le GIF (remplace les lignes 432-434) :

```python
    gif_frames[0].save(
        out_dir / "preview.gif", save_all=True, append_images=gif_frames[1:],
        duration=[max(20, d) for d in anim["durations"]],
        loop=0, disposal=2, transparency=255)
```

`max(20, d)` garde la borne d'origine : sous 20 ms les navigateurs imposent leur propre plancher, et une durée écrite qui n'est pas jouée est un mensonge de moins.

Le manifeste : `"version": 1,` devient `"version": 2,` et gagne `"anim": anim,` après `"pixel"`.

- [ ] **Étape 5 : vert**

Run: `cd backend && python tests/test_sprite_anim.py`
Expected: `3 passed`.
Run: `cd backend && python tests/test_sprite_native.py && python tests/test_sprite_images_source.py`
Expected: `2 passed` puis `2 passed`.

- [ ] **Étape 6 : l'écran — fieldset « Animation »**

`frontend/spritelab/index.html`, juste après `</fieldset>` du bloc pixel (ligne 153) :

```html
      <fieldset class="animset">
        <legend>Animation (P2)</legend>
        <div class="grid2">
          <label class="fld">Durée par image <span class="unit">ms</span>
            <input id="animMs" type="number" min="10" max="10000" value="125">
          </label>
          <label class="fld">Tags
            <button id="tagAdd" class="btn ghost" type="button" title="Ajoute une animation nommée (idle, run, jump…)">➕ Tag</button>
          </label>
        </div>
        <div id="tagRows" class="tagrows"></div>
        <div class="hint">Sans tag, la feuille porte une seule animation
          <code>default</code>. Les tags sont écrits dans le manifeste, le
          <code>.tres</code> Godot, l'atlas et le <code>.ase</code>.</div>
      </fieldset>
```

`frontend/spritelab/spritelab.css`, à la fin du fichier (règles **additives**, sous des classes nouvelles — `/tilelab/index.html:7` charge cette même feuille) :

```css
/* ── P2 : tags d'animation ── */
.animset{border:1px solid var(--stroke);border-radius:var(--r);padding:8px 10px;margin:10px}
.animset legend{font-size:11.5px;color:var(--ink-soft);padding:0 4px}
.tagrows{display:flex;flex-direction:column;gap:6px;margin-top:6px}
.tagrow{display:grid;grid-template-columns:1fr 52px 52px 1fr 28px;gap:6px;align-items:center}
.tagrow input,.tagrow select{background:var(--bg-base);border:1px solid var(--stroke-strong);border-radius:6px;color:var(--ink-strong);padding:4px 6px;font-size:12px;width:100%}
.tagrow .del{border:none;background:none;color:var(--ink-muted);cursor:pointer;font-size:14px}
.tagrow .del:hover{color:var(--red)}
```

`frontend/spritelab/spritelab.js` :

`PREF_IDS` (ligne 71) gagne `"animMs"`. Sous `pixelOpts()` :

```js
/* P2 — tags d'animation. Les lignes sont l'état ; le corps de la requête est
   construit à la volée, jamais mémorisé en double. */
let tagRows = [];
function renderTags() {
  $("#tagRows").innerHTML = tagRows.map((t, i) => `
    <div class="tagrow" data-i="${i}">
      <input class="tname" value="${esc(t.name)}" placeholder="idle" maxlength="32">
      <input class="tfrom" type="number" min="0" max="63" value="${t.from}">
      <input class="tto" type="number" min="0" max="63" value="${t.to}">
      <select class="tdir">
        ${["forward", "reverse", "pingpong", "pingpong_reverse"].map(d =>
          `<option value="${d}"${d === t.direction ? " selected" : ""}>${d}</option>`).join("")}
      </select>
      <button class="del" type="button" title="Retirer ce tag">✕</button>
    </div>`).join("");
  $$("#tagRows .tagrow").forEach(row => {
    const i = parseInt(row.dataset.i, 10);
    row.querySelector(".tname").oninput = (e) => { tagRows[i].name = e.target.value; savePrefs(); };
    row.querySelector(".tfrom").onchange = (e) => { tagRows[i].from = parseInt(e.target.value, 10) || 0; savePrefs(); };
    row.querySelector(".tto").onchange = (e) => { tagRows[i].to = parseInt(e.target.value, 10) || 0; savePrefs(); };
    row.querySelector(".tdir").onchange = (e) => { tagRows[i].direction = e.target.value; savePrefs(); };
    row.querySelector(".del").onclick = () => { tagRows.splice(i, 1); renderTags(); savePrefs(); };
  });
}
function animOpts(nFrames) {
  const ms = Math.max(10, Math.min(10000, parseInt($("#animMs").value, 10) || 125));
  const tags = tagRows
    .filter(t => (t.name || "").trim())
    .map(t => ({ name: t.name.trim(), from: t.from, to: t.to, direction: t.direction }));
  return { tags, durations: new Array(nFrames).fill(ms) };
}
```

`collectPrefs()` gagne `p.tagRows = JSON.stringify(tagRows);` et `applyPrefs(p)` gagne, avant `syncPixelSet()` :

```js
  if (p.tagRows) { try { tagRows = JSON.parse(p.tagRows) || []; } catch (e) { tagRows = []; } }
  renderTags();
```

Dans `generate()`, après `if (kept.length < stripN) body.keep = kept;` :

```js
    body.anim = animOpts(kept.length);
```

Dans `wire()`, après `$("#genBtn").onclick = generate;` :

```js
  $("#tagAdd").onclick = () => {
    const n = Math.max(0, stripN - 1);
    tagRows.push({ name: "anim" + (tagRows.length + 1), from: 0, to: n,
                   direction: "forward" });
    renderTags(); savePrefs();
  };
  $("#animMs").onchange = savePrefs;
```

- [ ] **Étape 7 : commit**

Écrire `msg.txt` avec `Write` :

```
sprites : T2 - les tags d animation et la duree par image

Pourquoi : le GIF d apercu n avait qu une duree pour toute la feuille
(sprite_service.py:432-434) et le manifeste ni tag ni duree — un moteur ne
pouvait pas savoir que 0-2 est idle et 3-5 run. sprite_anim.py est le seul
proprietaire de la validation, appele deux fois : forme a la route (n
inconnu), bornes reelles dans _assemble (n connu), sinon un tag qui deborde
la selection du filmstrip passerait.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

```bash
git add backend/app/services/sprite_anim.py backend/app/services/sprite_service.py backend/tests/test_sprite_anim.py frontend/spritelab/index.html frontend/spritelab/spritelab.js frontend/spritelab/spritelab.css
git commit -F msg.txt
```

### Tâche 3 — P3a : export Godot `SpriteFrames` et atlas JSON Hash

**Files :**
- Create: `backend/app/services/sprite_export.py`
- Modify: `backend/app/services/sprite_service.py:363-377` (`build_zip_bytes`), `:449-462` (fin d'`_assemble`)
- Modify: `backend/app/api/routes.py:1457-1476` (`get_sprite_manifest`, bloc `files`), `:1501-1513` (après `/zip`)
- Modify: `frontend/spritelab/index.html:185-191` (bande d'exports), `frontend/spritelab/spritelab.js:365-373` (`showResult`)
- Test: `backend/tests/test_sprite_exports.py` (créer)

**Pourquoi (mesuré) :** la seule sortie moteur d'aujourd'hui est le pack Unity (`sprite_service.py:348-359`, `UNITY_IMPORTER_CS` à `:271-346`) et le ZIP énumère **cinq noms en dur** (`:363-377`). Un utilisateur de Godot, de Phaser ou de PixiJS repart avec un PNG et se découpe la grille à la main. R10a réponse 4 demande les quatre exports ; les deux d'ici sont du **texte**, donc mesurables ligne à ligne.

- [ ] **Étape 1 : banc rouge**

Créer `backend/tests/test_sprite_exports.py` :

```python
"""P3a — le .tres Godot et l'atlas JSON Hash, LUS sur le disque.

Banc-miroir : on ouvre les fichiers ecrits, on y cherche les regions, les
durees relatives et les noms d'animation. Jamais le code qui pretend les
produire.

Run: python tests/test_sprite_exports.py   (depuis backend/)
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import zipfile  # noqa: E402

import pytest  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

TAGS = [{"name": "idle", "from": 0, "to": 1, "direction": "forward"},
        {"name": "run", "from": 2, "to": 3, "direction": "pingpong"}]


def _png(nom, couleur, taille=(32, 32)):
    from app.config import settings
    im = Image.new("RGBA", taille, (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([3, 3, taille[0] - 4, taille[1] - 4],
                                 fill=couleur)
    im.save(settings.images_path / nom)
    return nom


@pytest.fixture(scope="module")
def dossier():
    from app.config import settings
    from app.services import sprite_service as S
    noms = [_png(f"e{i}.png", (40 + 50 * i, 120, 90, 255)) for i in range(4)]
    asyncio.run(S.generate_sprites(
        {"source": {"kind": "images", "filenames": noms},
         "cell": {"size": 128}, "columns": 2, "fps_sample": 8,
         "anim": {"tags": TAGS, "durations": [125, 125, 250, 250]}}, "j-exp"))
    return settings.outputs_path / "sprites" / "j-exp"


def test_le_tres_godot_porte_une_region_par_image_et_deux_animations(dossier):
    txt = (dossier / "sheet.tres").read_text("utf-8")
    assert txt.startswith("[gd_resource type=\"SpriteFrames\" ")
    assert "format=3]" in txt
    # load_steps = 1 (ressource) + 1 ext + 4 sub
    assert "load_steps=6" in txt
    assert 'path="res://sheet.png"' in txt
    regions = re.findall(r"region = Rect2\(([^)]*)\)", txt)
    assert regions == ["0, 0, 128, 128", "128, 0, 128, 128",
                       "0, 128, 128, 128", "128, 128, 128, 128"]
    assert txt.count('[sub_resource type="AtlasTexture"') == 4
    assert '&"idle"' in txt and '&"run"' in txt
    # duree RELATIVE = ms / 1000 * speed ; speed = fps de la feuille (8)
    assert '"speed": 8.0' in txt
    assert txt.count('"duration": 1.0') == 2      # idle : 125 ms
    assert txt.count('"duration": 2.0') == 2      # run  : 250 ms
    assert txt.count('"loop": true') == 2
    # les images de `run` sont bien 2 et 3, pas 0 et 1
    bloc = txt.split('&"run"')[0].split('"frames": [')[-1]
    assert "Frame_002" in bloc and "Frame_003" in bloc


def test_l_atlas_json_hash_a_les_champs_de_texturepacker(dossier):
    a = json.loads((dossier / "sheet.atlas.json").read_text("utf-8"))
    assert sorted(a["frames"]) == ["frame_000.png", "frame_001.png",
                                   "frame_002.png", "frame_003.png"]
    f = a["frames"]["frame_002.png"]
    assert f["frame"] == {"x": 0, "y": 128, "w": 128, "h": 128}
    assert f["rotated"] is False and f["trimmed"] is False
    assert f["spriteSourceSize"] == {"x": 0, "y": 0, "w": 128, "h": 128}
    assert f["sourceSize"] == {"w": 128, "h": 128}
    assert f["pivot"] == {"x": 0.5, "y": 0.5}
    assert a["meta"]["image"] == "sheet.png"
    assert a["meta"]["size"] == {"w": 256, "h": 256}
    assert a["meta"]["scale"] == "1"
    assert a["meta"]["format"] == "RGBA8888"
    # extension NOMMEE : JSON Hash n'a pas de champ de tags, frameTags est la
    # forme que Pixi et Phaser lisent deja (export JSON d'Aseprite)
    assert a["meta"]["frameTags"] == [
        {"name": "idle", "from": 0, "to": 1, "direction": "forward"},
        {"name": "run", "from": 2, "to": 3, "direction": "pingpong"}]


def test_l_ancrage_pieds_deplace_le_pivot_de_l_atlas():
    from app.config import settings
    from app.services import sprite_service as S
    noms = [_png(f"p{i}.png", (200, 60, 40 * i + 40, 255)) for i in range(2)]
    asyncio.run(S.generate_sprites(
        {"source": {"kind": "images", "filenames": noms},
         "cell": {"size": 128, "align": "feet"}, "columns": 2}, "j-pied"))
    a = json.loads((settings.outputs_path / "sprites" / "j-pied"
                    / "sheet.atlas.json").read_text("utf-8"))
    assert a["frames"]["frame_000.png"]["pivot"] == {"x": 0.5, "y": 0.0}


def test_le_zip_emporte_les_deux_nouveaux_exports(dossier):
    from app.services.sprite_service import build_zip_bytes
    with zipfile.ZipFile(__import__("io").BytesIO(build_zip_bytes(dossier))) as z:
        noms = set(z.namelist())
    assert {"sheet.png", "manifest.json", "sheet.unity.json",
            "SpriteSheetImporter.cs", "sheet.tres",
            "sheet.atlas.json"} <= noms


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
```

- [ ] **Étape 2 : le voir rouge**

Run: `cd backend && python tests/test_sprite_exports.py`
Expected: `4 failed` — `FileNotFoundError: ...sheet.tres`.

- [ ] **Étape 3 : écrire `sprite_export.py`**

Créer `backend/app/services/sprite_export.py` :

```python
"""P3 — les exports moteur ecrits PAR CODE (plan sprites, taches 3 a 5).

Quatre formats, un seul module, parce qu'ils lisent tous le MEME manifeste et
les MEMES tags : les separer ferait diverger la convention de nommage des
images (`frame_000.png`) entre quatre fichiers, et c'est elle que les moteurs
utilisent pour relier une animation a ses cases.

  - `godot_tres`        : ressource texte Godot 4 (SpriteFrames + AtlasTexture)
  - `atlas_json_hash`   : atlas facon TexturePacker, lu par Phaser et PixiJS
  - `aseprite_bytes`    : .ase binaire selon la specification publique (T4)
  - `paper2d_json`      : feuille pour l'importateur Unreal Paper2D (T5)

Rien ici ne touche au disque sauf `write_all`, et rien n'importe FastAPI.
"""
from __future__ import annotations

import json

from app.services.sprite_anim import spans

_APP = "DeepotusVideoGen — Sprite Lab"


def frame_name(i: int) -> str:
    """Le nom d'une case, PARTOUT. Godot, l'atlas, Paper2D et le pack Unity
    doivent s'accorder : un seul endroit le decide."""
    return f"frame_{i:03d}.png"


def _pivot(align: str) -> tuple[float, float]:
    """'feet' ancre le bas-centre de la case ; sinon le centre. Meme regle que
    `build_unity_pack` (sprite_service.py:348-359) — recopiee ici EXPRES : le
    pack Unity retourne l'axe y, pas l'atlas, et melanger les deux conventions
    dans une fonction commune est exactement ce qui produit un sprite a
    l'envers."""
    return (0.5, 0.0) if align == "feet" else (0.5, 0.5)


# ── Godot 4 : SpriteFrames en .tres ─────────────────────────────────────────
def godot_tres(manifest: dict, sheet_name: str = "sheet.png") -> str:
    """Ressource texte Godot 4. Une AtlasTexture par case, une animation par
    tag. La duree d'une image y est RELATIVE (doc Godot 4, relue le
    03/09/2026 : `absolute = relative / (animation_fps * playing_speed)`),
    donc relative = ms/1000 * speed, avec speed = fps de la feuille."""
    frames = manifest["frames"]
    n = len(frames)
    fps = float(manifest.get("fps") or 8)
    lignes = [f'[gd_resource type="SpriteFrames" load_steps={n + 2} format=3]',
              "",
              f'[ext_resource type="Texture2D" path="res://{sheet_name}" '
              f'id="1_sheet"]',
              ""]
    for f in frames:
        r = f["rect"]
        lignes += [f'[sub_resource type="AtlasTexture" '
                   f'id="Frame_{f["index"]:03d}"]',
                   'atlas = ExtResource("1_sheet")',
                   f'region = Rect2({r["x"]}, {r["y"]}, {r["w"]}, {r["h"]})',
                   ""]
    anims = []
    for nom, a, b in spans(manifest.get("anim") or {}, n):
        cases = []
        for i in range(a, b + 1):
            ms = frames[i].get("duration_ms") or int(round(1000 / fps))
            rel = round(ms / 1000.0 * fps, 4)
            cases.append('{\n"duration": %s,\n"texture": SubResource("Frame_%03d")\n}'
                         % (_num(rel), i))
        anims.append('{\n"frames": [%s],\n"loop": true,\n"name": &"%s",\n'
                     '"speed": %s\n}' % (", ".join(cases), nom, _num(fps)))
    lignes += ["[resource]",
               "animations = [%s]" % ", ".join(anims),
               ""]
    return "\n".join(lignes)


def _num(v: float) -> str:
    """Godot ecrit les flottants avec au moins une decimale ; `8` serait lu
    comme un entier et `speed` deviendrait un int, ce que SpriteFrames refuse
    au chargement."""
    s = f"{float(v):.4f}".rstrip("0")
    return s + "0" if s.endswith(".") else s


# ── atlas JSON Hash (TexturePacker) ─────────────────────────────────────────
def atlas_json_hash(manifest: dict, sheet_w: int, sheet_h: int,
                    sheet_name: str = "sheet.png") -> dict:
    """Champs verifies le 03/09/2026 (codeandweb.com) : `frame`, `rotated`,
    `trimmed`, `spriteSourceSize`, `sourceSize` ; `meta.image`, `meta.size`,
    `meta.scale`. `pivot` et `meta.frameTags` sont des EXTENSIONS assumees :
    le format n'a pas de champ de tags, et `frameTags` est la forme que Pixi
    et Phaser lisent deja (export JSON d'Aseprite)."""
    px, py = _pivot(manifest.get("align") or "center")
    out = {}
    for f in manifest["frames"]:
        r = f["rect"]
        out[frame_name(f["index"])] = {
            "frame": {"x": r["x"], "y": r["y"], "w": r["w"], "h": r["h"]},
            "rotated": False,
            # la feuille n'est jamais rognee par case : chaque case fait
            # exactement la taille de cellule, donc trimmed = False et
            # spriteSourceSize = frame a l'origine.
            "trimmed": False,
            "spriteSourceSize": {"x": 0, "y": 0, "w": r["w"], "h": r["h"]},
            "sourceSize": {"w": r["w"], "h": r["h"]},
            "pivot": {"x": px, "y": py},
        }
    tags = [{"name": t["name"], "from": t["from"], "to": t["to"],
             "direction": t["direction"]}
            for t in ((manifest.get("anim") or {}).get("tags") or [])]
    return {"frames": out,
            "meta": {"app": _APP, "version": "1.0", "image": sheet_name,
                     "format": "RGBA8888",
                     "size": {"w": sheet_w, "h": sheet_h},
                     "scale": "1", "frameTags": tags}}


# ── ecriture ────────────────────────────────────────────────────────────────
def write_all(manifest: dict, out_dir, sheet_w: int, sheet_h: int) -> list[str]:
    """Ecrit les exports a cote de sheet.png et rend les noms ecrits. UN SEUL
    appelant : `sprite_service._assemble`, apres le manifeste — c'est ce qui
    donne aux particules et aux sequences Kenney les memes exports sans une
    ligne chez elles."""
    ecrits = []
    (out_dir / "sheet.tres").write_text(godot_tres(manifest), encoding="utf-8")
    ecrits.append("sheet.tres")
    (out_dir / "sheet.atlas.json").write_text(
        json.dumps(atlas_json_hash(manifest, sheet_w, sheet_h), indent=2),
        encoding="utf-8")
    ecrits.append("sheet.atlas.json")
    return ecrits
```

- [ ] **Étape 4 : brancher dans `sprite_service.py`**

Dans `_assemble`, après le bloc du pack Unity (`SpriteSheetImporter.cs`) :

```python
    from app.services import sprite_export as SE
    SE.write_all(manifest, out_dir, sheet.width, sheet.height)
```

Dans `build_zip_bytes`, le tuple de noms (ligne 368) devient :

```python
        for name in ("sheet.png", "preview.gif", "manifest.json",
                     "sheet.unity.json", "SpriteSheetImporter.cs",
                     "sheet.tres", "sheet.atlas.json"):
```

- [ ] **Étape 5 : vert**

Run: `cd backend && python tests/test_sprite_exports.py`
Expected: `4 passed`.
Run: `cd backend && python tests/test_sprite_anim.py`
Expected: `3 passed`.

- [ ] **Étape 6 : les routes et les boutons**

`backend/app/api/routes.py`, dans `get_sprite_manifest` le dictionnaire `data["files"]` gagne :

```python
        "godot": (d / "sheet.tres").is_file(),
        "atlas": (d / "sheet.atlas.json").is_file(),
```

et juste après la route `/zip` (ligne 1513) :

```python
# Une porte par export : un `?fmt=` unique economiserait cinq lignes et
# couterait une allowlist a maintenir dans deux langages. Chaque route nomme
# SON fichier, et 404 dit lequel manque.
@router.get("/assets/sprite/{job}/godot")
async def get_sprite_godot(job: str):
    """Ressource SpriteFrames Godot 4 (texte)."""
    p = _sprite_dir(job) / "sheet.tres"
    if not p.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(p, media_type="text/plain")


@router.get("/assets/sprite/{job}/atlas")
async def get_sprite_atlas(job: str):
    """Atlas JSON Hash facon TexturePacker (Phaser, PixiJS)."""
    p = _sprite_dir(job) / "sheet.atlas.json"
    if not p.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(p, media_type="application/json")
```

`frontend/spritelab/index.html`, dans `<div id="exports">` après `dlGif` :

```html
      <a id="dlGodot" class="btn" download title="Ressource Godot 4 SpriteFrames (.tres) — une AtlasTexture par image, une animation par tag">⬇ Godot .tres</a>
      <a id="dlAtlas" class="btn" download title="Atlas JSON Hash façon TexturePacker — lu par Phaser et PixiJS">⬇ Atlas JSON</a>
```

`frontend/spritelab/spritelab.js`, dans `showResult` après la ligne `dlGif` :

```js
  $("#dlGodot").href = `/api/assets/sprite/${short}/godot`;
  $("#dlGodot").setAttribute("download", `sprites_${short}.tres`);
  $("#dlAtlas").href = `/api/assets/sprite/${short}/atlas`;
  $("#dlAtlas").setAttribute("download", `sprites_${short}.atlas.json`);
  for (const [id, ok] of [["dlGodot", m.files && m.files.godot],
                          ["dlAtlas", m.files && m.files.atlas]])
    $("#" + id).classList.toggle("hidden", !ok);
```

- [ ] **Étape 7 : commit** — `msg.txt`, sujet `sprites : T3 - le tres Godot et l atlas JSON Hash`, corps : « la seule sortie moteur etait le pack Unity et le ZIP enumerait cinq noms en dur (sprite_service.py:363-377) ; les deux exports d ici sont du texte, donc mesurables ligne a ligne. La duree Godot est RELATIVE (doc relue le 03/09) : ms/1000 * speed. » Puis :

```bash
git add backend/app/services/sprite_export.py backend/app/services/sprite_service.py backend/app/api/routes.py backend/tests/test_sprite_exports.py frontend/spritelab/index.html frontend/spritelab/spritelab.js
git commit -F msg.txt
```

### Tâche 4 — P3b : le `.ase` Aseprite, écrit selon la spécification publique

**Files :**
- Modify: `backend/app/services/sprite_export.py` (ajout de `aseprite_bytes` + branchement dans `write_all`)
- Modify: `backend/app/services/sprite_service.py:363-377` (`build_zip_bytes`)
- Modify: `backend/app/api/routes.py` (bloc `files` de `get_sprite_manifest`, route `/aseprite`)
- Modify: `frontend/spritelab/index.html` (1 bouton), `frontend/spritelab/spritelab.js` (`showResult`)
- Test: `backend/tests/test_sprite_ase.py` (créer)

**Pourquoi (mesuré) :** R10a réponse 4 demande Aseprite, et c'est le seul des quatre formats qui soit **binaire** — donc le seul où une erreur d'un octet donne un fichier qui s'ouvre à moitié ou pas du tout. Le dépôt n'écrit aujourd'hui aucun binaire de ce genre : `build_zip_bytes` (`sprite_service.py:363-377`) empaquette, il ne sérialise pas. La spécification est publique et le format est écrivable par code (R10a) ; ce qui décide de la réussite est le **sous-ensemble** écrit, et il doit être figé avant la première ligne.

- [ ] **Étape 1 : relire la spécification, et FIXER le sous-ensemble**

Relire la spécification avec **exactement** cette commande (outil `WebFetch`) :

- url : `https://raw.githubusercontent.com/aseprite/aseprite/main/docs/ase-file-specs.md`
- prompt : `Give the EXACT byte layout of: (1) the 128-byte file header field by field with types and offsets; (2) the 16-byte frame header; (3) the chunk header (size + type, and whether size includes the header); (4) the Layer Chunk 0x2004 fields in order; (5) the Cel Chunk 0x2005 fields in order including cel type 2 (compressed image); (6) the Tags Chunk 0x2018 fields in order; (7) the definition of STRING and the DWORD/WORD/SHORT/BYTE types and endianness. Also state whether a palette chunk is required for 32bpp RGBA.`

Ce qui a été mesuré le 03/09/2026 avec cette commande, et qui doit être **reconfirmé** avant d'écrire (la spécification vit sur `main`) :

| Bloc | Champs, dans l'ordre, petit-boutiste |
|---|---|
| En-tête, 128 o | `DWORD` taille du fichier · `WORD` 0xA5E0 · `WORD` images · `WORD` largeur · `WORD` hauteur · `WORD` profondeur (8/16/32) · `DWORD` drapeaux · `WORD` vitesse (obsolète) · `DWORD` 0 · `DWORD` 0 · `BYTE` index transparent · `BYTE[3]` · `WORD` nb couleurs · `BYTE` ratio px large · `BYTE` ratio px haut · `SHORT` grille x · `SHORT` grille y · `WORD` grille l · `WORD` grille h · `BYTE[84]` |
| En-tête d'image, 16 o | `DWORD` octets de l'image (en-tête compris) · `WORD` 0xF1FA · `WORD` anciens chunks · `WORD` durée ms · `BYTE[2]` · `DWORD` nouveaux chunks |
| Chunk | `DWORD` taille **en-tête compris, ≥ 6** · `WORD` type · charge utile |
| Calque 0x2004 | `WORD` drapeaux · `WORD` type · `WORD` niveau · `WORD` l (ignorée) · `WORD` h (ignorée) · `WORD` fusion · `BYTE` opacité · `BYTE[3]` · `STRING` nom |
| Cel 0x2005 | `WORD` calque · `SHORT` x · `SHORT` y · `BYTE` opacité · `WORD` type · `SHORT` z · `BYTE[5]` ; **type 2** : `WORD` l · `WORD` h · zlib(RGBA brut) |
| Tags 0x2018 | `WORD` n · `BYTE[8]` ; par tag : `WORD` de · `WORD` à · `BYTE` sens 0..3 · `WORD` répétitions · `BYTE[6]` · `BYTE[3]` rvb (obsolète) · `BYTE` 0 · `STRING` nom |
| `STRING` | `WORD` longueur en octets + UTF-8, **sans zéro terminal** |
| Palette | « For color depths more than 8bpp, palettes are optional » — donc **aucun** chunk de palette en 32 bpp |

**Sous-ensemble écrit, figé ici, et écrit aussi dans la docstring du code :** RGBA 32 bpp · **un** calque normal nommé `Layer 1`, visible et éditable (drapeaux 1|2 = 3), opacité 255, fusion normale · N images, chacune portant **un** cel de type 2 posé en (0, 0) et couvrant toute la toile · un chunk de tags dans l'image 0 quand il y a des tags · **pas** de palette, **pas** de profil colorimétrique (0x2007), **pas** de slices, **pas** de données utilisateur. Aseprite suppose sRGB en l'absence de profil : c'est la seule conséquence visible, et elle est dite.

- [ ] **Étape 2 : banc rouge**

Créer `backend/tests/test_sprite_ase.py` :

```python
"""P3b — le .ase, LU OCTET PAR OCTET.

Banc-miroir binaire : le lecteur ci-dessous ne connait pas notre ecrivain, il
suit la specification (en-tete 128 o, images, chunks) et retombe sur ses
pieds — `assert off == len(d)` est l'assertion qui attrape une taille de
chunk fausse, celle qu'un `assert magic == 0xA5E0` laisserait passer.

Run: python tests/test_sprite_ase.py   (depuis backend/)
"""
import os
import pathlib
import struct
import sys
import tempfile
import zlib

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio  # noqa: E402

import pytest  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

TETE = "<IHHHHHIHIIB3sHBBhhHH84s"
IMG = "<IHHH2sI"

TAGS = [{"name": "idle", "from": 0, "to": 1, "direction": "forward"},
        {"name": "run", "from": 2, "to": 3, "direction": "pingpong"}]


def _png(nom, couleur, taille=(20, 20)):
    from app.config import settings
    im = Image.new("RGBA", taille, (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([2, 2, taille[0] - 3, taille[1] - 3],
                                 fill=couleur)
    im.save(settings.images_path / nom)
    return nom


def lire_ase(p: pathlib.Path) -> dict:
    d = p.read_bytes()
    (taille, magic, n, w, h, depth, flags, vitesse, z1, z2, transp, _ign,
     ncolors, pw, ph, gx, gy, gw, gh, _fut) = struct.unpack(TETE, d[:128])
    assert taille == len(d), (taille, len(d))
    off, images = 128, []
    for _ in range(n):
        fb, fmagic, vieux, duree, _r, nchunks = struct.unpack(
            IMG, d[off:off + 16])
        assert fmagic == 0xF1FA
        q, chunks = off + 16, []
        for _ in range(nchunks):
            csize, ctype = struct.unpack("<IH", d[q:q + 6])
            assert csize >= 6
            chunks.append((ctype, d[q + 6:q + csize]))
            q += csize
        assert q == off + fb, (q, off, fb)
        images.append({"duree": duree, "chunks": chunks})
        off += fb
    assert off == len(d), (off, len(d))
    return {"magic": magic, "n": n, "w": w, "h": h, "depth": depth,
            "flags": flags, "z": (z1, z2), "ncolors": ncolors,
            "px": (pw, ph), "images": images}


def lire_string(b: bytes, off: int):
    (ln,) = struct.unpack("<H", b[off:off + 2])
    return b[off + 2:off + 2 + ln].decode("utf-8"), off + 2 + ln


@pytest.fixture(scope="module")
def dossier():
    from app.config import settings
    from app.services import sprite_service as S
    noms = [_png(f"s{i}.png", (60 + 50 * i, 30, 160, 255)) for i in range(4)]
    asyncio.run(S.generate_sprites(
        {"source": {"kind": "images", "filenames": noms},
         "cell": {"size": 128}, "columns": 2,
         "anim": {"tags": TAGS, "durations": [100, 100, 200, 200]}}, "j-ase"))
    return settings.outputs_path / "sprites" / "j-ase"


def test_l_en_tete_et_les_durees(dossier):
    a = lire_ase(dossier / "sheet.ase")
    assert a["magic"] == 0xA5E0
    assert a["n"] == 4 and a["w"] == 128 and a["h"] == 128
    assert a["depth"] == 32 and a["ncolors"] == 0     # 32 bpp : pas de palette
    assert a["z"] == (0, 0) and a["px"] == (1, 1)
    assert [f["duree"] for f in a["images"]] == [100, 100, 200, 200]
    # aucun chunk de palette (0x2019 / 0x0004 / 0x0011) nulle part
    types = {t for f in a["images"] for t, _ in f["chunks"]}
    assert types & {0x2019, 0x0004, 0x0011} == set()


def test_l_image_zero_porte_le_calque_le_cel_et_les_tags(dossier):
    a = lire_ase(dossier / "sheet.ase")
    types0 = [t for t, _ in a["images"][0]["chunks"]]
    assert types0 == [0x2004, 0x2005, 0x2018]
    assert [t for t, _ in a["images"][1]["chunks"]] == [0x2005]

    calque = dict(a["images"][0]["chunks"])[0x2004]
    dr, typ, niv, _lw, _lh, fusion, opac = struct.unpack("<HHHHHHB",
                                                         calque[:13])
    assert (dr, typ, niv, fusion, opac) == (3, 0, 0, 0, 255)
    nom, fin = lire_string(calque, 16)
    assert nom == "Layer 1" and fin == len(calque)

    tg = dict(a["images"][0]["chunks"])[0x2018]
    (ntags,) = struct.unpack("<H", tg[:2])
    assert ntags == 2
    off, lus = 10, []
    for _ in range(ntags):
        de, a_, sens, rep = struct.unpack("<HHBH", tg[off:off + 7])
        nom, off = lire_string(tg, off + 17)
        lus.append((nom, de, a_, sens, rep))
    assert lus == [("idle", 0, 1, 0, 0), ("run", 2, 3, 2, 0)]
    assert off == len(tg)


def test_le_cel_decompresse_donne_les_pixels_de_la_case(dossier):
    from PIL import Image as I
    a = lire_ase(dossier / "sheet.ase")
    cel = dict(a["images"][2]["chunks"])[0x2005]
    couche, x, y, opac, ctype, z = struct.unpack("<HhhBHh", cel[:11])
    assert (couche, x, y, opac, ctype, z) == (0, 0, 0, 255, 2, 0)
    w, h = struct.unpack("<HH", cel[16:20])
    assert (w, h) == (128, 128)
    brut = zlib.decompress(cel[20:])
    assert len(brut) == w * h * 4
    with I.open(dossier / "frames" / "002.png") as case:
        assert brut == case.convert("RGBA").tobytes()


def test_sans_tag_aucun_chunk_de_tags():
    from app.config import settings
    from app.services import sprite_service as S
    noms = [_png(f"u{i}.png", (10, 200, 40 * i + 40, 255)) for i in range(2)]
    asyncio.run(S.generate_sprites(
        {"source": {"kind": "images", "filenames": noms},
         "cell": {"size": 128}}, "j-sans"))
    a = lire_ase(settings.outputs_path / "sprites" / "j-sans" / "sheet.ase")
    assert [t for t, _ in a["images"][0]["chunks"]] == [0x2004, 0x2005]


def test_le_zip_emporte_le_ase(dossier):
    import io
    import zipfile
    from app.services.sprite_service import build_zip_bytes
    with zipfile.ZipFile(io.BytesIO(build_zip_bytes(dossier))) as z:
        assert "sheet.ase" in z.namelist()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
```

- [ ] **Étape 3 : le voir rouge**

Run: `cd backend && python tests/test_sprite_ase.py`
Expected: `5 failed` — `FileNotFoundError: ...sheet.ase`.

- [ ] **Étape 4 : écrire l'écrivain**

Dans `backend/app/services/sprite_export.py`, en tête, ajouter aux imports :

```python
import struct
import zlib
```

et, après `atlas_json_hash`, la section :

```python
# ── Aseprite .ase (specification publique, relue le 03/09/2026) ─────────────
# SOUS-ENSEMBLE ECRIT, ET C'EST DELIBERE : RGBA 32 bpp ; UN calque normal
# « Layer 1 » visible+editable, opacite 255 ; N images portant chacune UN cel
# de type 2 (image compressee zlib) pose en (0,0) et couvrant la toile ; un
# chunk de tags dans l'image 0 quand il y en a. PAS de palette (« for color
# depths more than 8bpp, palettes are optional »), PAS de profil
# colorimetrique 0x2007 — Aseprite suppose alors sRGB, seule consequence
# visible —, PAS de slices, PAS de donnees utilisateur.
# Petit-boutiste partout (« ASE files use Intel byte order »).
_ASE_TETE = "<IHHHHHIHIIB3sHBBhhHH84s"      # 128 octets, verifie par le banc
_ASE_IMAGE = "<IHHH2sI"                      # 16 octets
_ASE_SENS = {"forward": 0, "reverse": 1, "pingpong": 2,
             "pingpong_reverse": 3}


def _ase_string(s: str) -> bytes:
    b = s.encode("utf-8")
    if len(b) > 65535:
        raise ValueError("aseprite STRING: 65535 bytes at most")
    return struct.pack("<H", len(b)) + b


def _ase_chunk(type_: int, charge: bytes) -> bytes:
    """La taille COMPREND ses 4 octets et les 2 du type (specification) —
    l'oublier donne un fichier qui s'ouvre a moitie, jamais une erreur."""
    return struct.pack("<IH", len(charge) + 6, type_) + charge


def _ase_calque(nom: str) -> bytes:
    charge = struct.pack("<HHHHHHB3s",
                         3,        # drapeaux : 1 visible | 2 editable
                         0,        # type : normal
                         0,        # niveau d'enfant
                         0, 0,     # largeur/hauteur par defaut (ignorees)
                         0,        # fusion : normal
                         255,      # opacite
                         b"\0" * 3)
    return _ase_chunk(0x2004, charge + _ase_string(nom))


def _ase_cel(img) -> bytes:
    w, h = img.size
    charge = struct.pack("<HhhBHh5s", 0, 0, 0, 255, 2, 0, b"\0" * 5)
    return _ase_chunk(0x2005, charge + struct.pack("<HH", w, h)
                      + zlib.compress(img.convert("RGBA").tobytes()))


def _ase_tags(tags: list[dict]) -> bytes:
    charge = struct.pack("<H8s", len(tags), b"\0" * 8)
    for t in tags:
        charge += struct.pack(
            "<HHBH6s3sB", t["from"], t["to"],
            _ASE_SENS[t["direction"]], int(t.get("repeat") or 0),
            b"\0" * 6, b"\0" * 3, 0) + _ase_string(t["name"])
    return _ase_chunk(0x2018, charge)


def _ase_image(chunks: list[bytes], duree_ms: int) -> bytes:
    corps = b"".join(chunks)
    n = len(chunks)
    return struct.pack(_ASE_IMAGE, len(corps) + 16, 0xF1FA,
                       n if n < 0xFFFF else 0xFFFF,
                       max(0, min(65535, int(duree_ms))),
                       b"\0" * 2, n) + corps


def aseprite_bytes(cases: list, durees: list[int],
                   tags: list[dict] | None = None) -> bytes:
    """Les octets d'un .ase. `cases` = images PIL de MEME taille (les cases de
    la feuille), `durees` = une milliseconde par case."""
    if not cases:
        raise ValueError("aseprite: at least one frame")
    if len(durees) != len(cases):
        raise ValueError("aseprite: one duration per frame")
    w, h = cases[0].size
    for im in cases:
        if im.size != (w, h):
            raise ValueError("aseprite: every frame shares the canvas size "
                             f"({w}x{h}) — got {im.size}")
    corps = []
    for i, im in enumerate(cases):
        chunks = []
        if i == 0:
            chunks.append(_ase_calque("Layer 1"))
        chunks.append(_ase_cel(im))
        if i == 0 and tags:
            chunks.append(_ase_tags(tags))
        corps.append(_ase_image(chunks, durees[i]))
    corps_b = b"".join(corps)
    tete = struct.pack(
        _ASE_TETE, 128 + len(corps_b), 0xA5E0, len(cases), w, h,
        32,                                   # profondeur : RGBA
        1,                                    # drapeaux : opacite de calque valide
        max(1, min(65535, int(durees[0]))),   # vitesse (obsolete, par egard)
        0, 0, 0, b"\0" * 3,
        0,                                    # nb couleurs : aucune palette
        1, 1, 0, 0, 16, 16, b"\0" * 84)
    return tete + corps_b
```

et `write_all` gagne, avant le `return` :

```python
    from PIL import Image as _I
    cases, durees = [], []
    for f in manifest["frames"]:
        with _I.open(out_dir / f["file"]) as im:
            cases.append(im.convert("RGBA"))
        durees.append(f.get("duration_ms")
                      or int(round(1000 / float(manifest.get("fps") or 8))))
    (out_dir / "sheet.ase").write_bytes(
        aseprite_bytes(cases, durees,
                       (manifest.get("anim") or {}).get("tags") or []))
    ecrits.append("sheet.ase")
```

`im.convert("RGBA")` **après** `with` : `convert` rend une image neuve, détachée du fichier — sans cela le `.tobytes()` d'`_ase_cel` lirait un descripteur fermé.

- [ ] **Étape 5 : le ZIP, la route, le bouton**

`sprite_service.build_zip_bytes` : la liste de noms gagne `"sheet.ase"`.

`routes.py` : `data["files"]` gagne `"aseprite": (d / "sheet.ase").is_file(),` ; nouvelle route sous `/atlas` :

```python
@router.get("/assets/sprite/{job}/aseprite")
async def get_sprite_aseprite(job: str):
    """Le .ase (32 bpp, un calque, N images, tags) — s'ouvre dans Aseprite."""
    p = _sprite_dir(job) / "sheet.ase"
    if not p.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(p, media_type="application/octet-stream")
```

`index.html`, bande d'exports : `<a id="dlAse" class="btn" download title="Fichier Aseprite (.ase) — un calque, une image par frame, les tags">⬇ Aseprite .ase</a>`

`spritelab.js`, dans `showResult`, à la suite des deux lignes `dlAtlas` :

```js
  $("#dlAse").href = `/api/assets/sprite/${short}/aseprite`;
  $("#dlAse").setAttribute("download", `sprites_${short}.ase`);
```

et la boucle de masquage gagne son entrée :

```js
  for (const [id, ok] of [["dlGodot", m.files && m.files.godot],
                          ["dlAtlas", m.files && m.files.atlas],
                          ["dlAse", m.files && m.files.aseprite]])
    $("#" + id).classList.toggle("hidden", !ok);
```

- [ ] **Étape 6 : vert**

Run: `cd backend && python tests/test_sprite_ase.py`
Expected: `5 passed`.
Run: `cd backend && python tests/test_sprite_exports.py`
Expected: `4 passed`.

- [ ] **Étape 7 : le seul contrôle que le banc ne peut pas faire**

Le banc lit **notre** fichier avec **notre** lecture de la spécification : il ne prouve pas qu'Aseprite l'ouvre. Ouvrir `outputs/sprites/j-ase/sheet.ase` dans Aseprite et vérifier à l'œil : 4 images, deux tags `idle` et `run` dans la barre de tags, un calque `Layer 1`. Noter le résultat dans le message de commit. C'est une vérification **humaine**, elle est nommée comme telle et ne bloque pas le banc.

- [ ] **Étape 8 : commit** — sujet `sprites : T4 - le ase Aseprite ecrit selon la spec` ; corps : le sous-ensemble figé (RGBA, un calque, N cels type 2, tags), le piège de la taille de chunk qui comprend son propre en-tête, et le résultat de l'ouverture dans Aseprite.

```bash
git add backend/app/services/sprite_export.py backend/app/services/sprite_service.py backend/app/api/routes.py backend/tests/test_sprite_ase.py frontend/spritelab/index.html frontend/spritelab/spritelab.js
git commit -F msg.txt
```

### Tâche 5 — P3c : la feuille Unreal Paper2D

**Files :**
- Modify: `backend/app/services/sprite_export.py` (ajout de `paper2d_json` + `write_all`)
- Modify: `backend/app/services/sprite_service.py:363-377` (`build_zip_bytes`)
- Modify: `backend/app/api/routes.py` (bloc `files`, route `/paper2d`)
- Modify: `frontend/spritelab/index.html`, `frontend/spritelab/spritelab.js`
- Test: `backend/tests/test_sprite_paper2d.py` (créer)

**Pourquoi (mesuré) :** R10a réponse 4 demande Unreal Paper2D et R10a le note explicitement « format à relever avant le plan ». C'est le seul des quatre dont la référence soit **partiellement refusée** : voir l'étape 1.

- [ ] **Étape 1 : la mesure, et ce qu'elle a donné**

Rejouer, dans cet ordre, avec l'outil `WebFetch` :

1. url `https://dev.epicgames.com/documentation/en-us/unreal-engine/paper-2d-import-options-in-unreal-engine`, prompt `What JSON sprite-sheet format does the Paper2D importer accept, which tools export it, what assets does it create, and what JSON field names are mentioned?`
2. url `https://docs.unrealengine.com/4.27/en-US/AnimatingObjects/Paper2D/ImportOptions/`, même prompt.
3. url `https://www.codeandweb.com/texturepacker/tutorials/how-to-create-a-sprite-sheet-for-unreal-paper2d`, prompt `What exact file format and extension does TexturePacker export for Unreal Paper2D, and what JSON fields does it contain?`

**Résultat mesuré le 03/09/2026 (seconde passe) : (1) répond une page vide (table des matières seule), (2) refuse en 403, (3) refuse en 404.** La première passe du 03/09 avait retenu de la documentation 4.27 que l'importateur lit une feuille exportée depuis Adobe Flash CS6 ou TexturePacker, qu'il crée la texture, les sprites **et toujours un flipbook** (il suppose que toutes les images sont celles d'une animation), et que TexturePacker exporte un `.paper2dsprites`. **Ces deux phrases sont la seule chose que l'on tient ; le jeu de champs exact lu par l'importateur n'est pas vérifié.**

Décision, écrite ici et dans la docstring du code, parce qu'un plan qui cache une incertitude la fait payer plus tard : on écrit `sheet.paper2dsprites` dans la forme **JSON Array** de TexturePacker (`frames` est une **liste** d'objets portant `filename`), et non la forme Hash de T3. Raison mesurable : l'importateur construit **toujours** un flipbook, donc l'**ordre** des images est porteur de sens ; une liste le garantit, un objet JSON ne le garantit pas. Le banc ne mesure que **notre** fichier ; l'ouverture dans Unreal est une vérification humaine, nommée comme telle à l'étape 5. Si une des trois URL redevient lisible, la tâche corrige le fichier **et** cette section avant de commettre.

- [ ] **Étape 2 : banc rouge**

Créer `backend/tests/test_sprite_paper2d.py` :

```python
"""P3c — la feuille Paper2D, LUE sur le disque.

Ce que le banc peut prouver : notre fichier a la forme JSON Array de
TexturePacker, l'ordre des images y est celui de l'animation, et les
rectangles collent a la feuille PNG (relus en PIL). Ce qu'il ne peut PAS
prouver : qu'Unreal l'importe — la documentation Epic a refuse la relecture
du 03/09 (403 et 404). C'est ecrit dans le plan, tache 5, etape 1.

Run: python tests/test_sprite_paper2d.py   (depuis backend/)
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio  # noqa: E402
import json  # noqa: E402

import pytest  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402


def _png(nom, couleur, taille=(16, 16)):
    from app.config import settings
    im = Image.new("RGBA", taille, (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([1, 1, taille[0] - 2, taille[1] - 2],
                                 fill=couleur)
    im.save(settings.images_path / nom)
    return nom


@pytest.fixture(scope="module")
def dossier():
    from app.config import settings
    from app.services import sprite_service as S
    noms = [_png(f"w{i}.png", (200, 40 * i + 40, 30, 255)) for i in range(3)]
    asyncio.run(S.generate_sprites(
        {"source": {"kind": "images", "filenames": noms},
         "cell": {"size": 128}, "columns": 2, "fps_sample": 10}, "j-p2d"))
    return settings.outputs_path / "sprites" / "j-p2d"


def test_les_images_sont_une_LISTE_dans_l_ordre_de_l_animation(dossier):
    d = json.loads((dossier / "sheet.paper2dsprites").read_text("utf-8"))
    assert isinstance(d["frames"], list)            # Array, pas Hash
    assert [f["filename"] for f in d["frames"]] == \
        ["frame_000.png", "frame_001.png", "frame_002.png"]
    f = d["frames"][2]
    assert f["frame"] == {"x": 0, "y": 128, "w": 128, "h": 128}
    assert f["rotated"] is False and f["trimmed"] is False
    assert f["spriteSourceSize"] == {"x": 0, "y": 0, "w": 128, "h": 128}
    assert f["sourceSize"] == {"w": 128, "h": 128}
    assert f["pivot"] == {"x": 0.5, "y": 0.5}


def test_les_rectangles_collent_a_la_feuille_PNG(dossier):
    """Un rectangle juste dans le JSON et faux sur la feuille est le defaut
    que seul un banc-miroir attrape : on relit le PNG."""
    d = json.loads((dossier / "sheet.paper2dsprites").read_text("utf-8"))
    with Image.open(dossier / "sheet.png") as sh:
        assert (sh.width, sh.height) == (d["meta"]["size"]["w"],
                                         d["meta"]["size"]["h"])
        rgba = sh.convert("RGBA")
        for i, f in enumerate(d["frames"]):
            r = f["frame"]
            assert r["x"] + r["w"] <= sh.width
            assert r["y"] + r["h"] <= sh.height
            case = rgba.crop((r["x"], r["y"], r["x"] + r["w"],
                              r["y"] + r["h"]))
            with Image.open(dossier / "frames" / f"{i:03d}.png") as ref:
                assert case.tobytes() == ref.convert("RGBA").tobytes()


def test_le_meta_nomme_la_texture_et_le_zip_emporte_le_fichier(dossier):
    import io
    import zipfile
    from app.services.sprite_service import build_zip_bytes
    d = json.loads((dossier / "sheet.paper2dsprites").read_text("utf-8"))
    assert d["meta"]["image"] == "sheet.png"
    assert d["meta"]["format"] == "RGBA8888" and d["meta"]["scale"] == "1"
    with zipfile.ZipFile(io.BytesIO(build_zip_bytes(dossier))) as z:
        assert "sheet.paper2dsprites" in z.namelist()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
```

- [ ] **Étape 3 : le voir rouge**

Run: `cd backend && python tests/test_sprite_paper2d.py`
Expected: `3 failed` — `FileNotFoundError: ...sheet.paper2dsprites`.

- [ ] **Étape 4 : écrire**

Dans `sprite_export.py`, après `aseprite_bytes` :

```python
# ── Unreal Paper2D ──────────────────────────────────────────────────────────
def paper2d_json(manifest: dict, sheet_w: int, sheet_h: int,
                 sheet_name: str = "sheet.png") -> dict:
    """Feuille pour l'importateur Paper2D, en forme JSON **Array** de
    TexturePacker : `frames` est une LISTE, chaque entree portant `filename`.

    POURQUOI Array et pas Hash (celle de `atlas_json_hash`) : l'importateur
    construit TOUJOURS un flipbook, donc l'ORDRE des images porte du sens ;
    une liste le garantit, un objet JSON ne le garantit pas.

    INCERTITUDE ASSUMEE : le jeu de champs exact lu par l'importateur n'a pas
    pu etre reverifie le 03/09/2026 (documentation Epic : 403 et 404 — voir
    le plan, tache 5, etape 1). Ce que l'on tient de la premiere passe :
    l'importateur lit une feuille exportee par Adobe Flash CS6 ou
    TexturePacker, cree texture + sprites + flipbook, et TexturePacker ecrit
    un `.paper2dsprites`. Le banc ne mesure que NOTRE fichier."""
    px, py = _pivot(manifest.get("align") or "center")
    frames = []
    for f in manifest["frames"]:
        r = f["rect"]
        frames.append({
            "filename": frame_name(f["index"]),
            "frame": {"x": r["x"], "y": r["y"], "w": r["w"], "h": r["h"]},
            "rotated": False,
            "trimmed": False,
            "spriteSourceSize": {"x": 0, "y": 0, "w": r["w"], "h": r["h"]},
            "sourceSize": {"w": r["w"], "h": r["h"]},
            "pivot": {"x": px, "y": py},
        })
    return {"frames": frames,
            "meta": {"app": _APP, "version": "1.0", "image": sheet_name,
                     "format": "RGBA8888",
                     "size": {"w": sheet_w, "h": sheet_h}, "scale": "1"}}
```

`write_all` gagne, avant le `return` :

```python
    (out_dir / "sheet.paper2dsprites").write_text(
        json.dumps(paper2d_json(manifest, sheet_w, sheet_h), indent=2),
        encoding="utf-8")
    ecrits.append("sheet.paper2dsprites")
```

`build_zip_bytes` : la liste gagne `"sheet.paper2dsprites"`. `routes.py` : `data["files"]` gagne `"paper2d": (d / "sheet.paper2dsprites").is_file(),` et la route :

```python
@router.get("/assets/sprite/{job}/paper2d")
async def get_sprite_paper2d(job: str):
    """Feuille Unreal Paper2D (.paper2dsprites, JSON Array TexturePacker)."""
    p = _sprite_dir(job) / "sheet.paper2dsprites"
    if not p.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(p, media_type="application/json")
```

`index.html`, dans `<div id="exports">` :

```html
      <a id="dlP2d" class="btn" download title="Feuille Unreal Paper2D — l'importateur crée texture, sprites et flipbook">⬇ Paper2D</a>
```

`spritelab.js`, dans `showResult`, à la suite des lignes `dlAse` :

```js
  $("#dlP2d").href = `/api/assets/sprite/${short}/paper2d`;
  $("#dlP2d").setAttribute("download", `sprites_${short}.paper2dsprites`);
```

et la boucle de masquage prend sa forme définitive, les quatre exports ensemble :

```js
  for (const [id, ok] of [["dlGodot", m.files && m.files.godot],
                          ["dlAtlas", m.files && m.files.atlas],
                          ["dlAse", m.files && m.files.aseprite],
                          ["dlP2d", m.files && m.files.paper2d]])
    $("#" + id).classList.toggle("hidden", !ok);
```

- [ ] **Étape 5 : vert, puis la vérification humaine**

Run: `cd backend && python tests/test_sprite_paper2d.py`
Expected: `3 passed`.
Run: `cd backend && python tests/test_sprite_ase.py && python tests/test_sprite_exports.py`
Expected: `5 passed` puis `4 passed`.

Vérification **humaine**, nommée : importer `sheet.png` + `sheet.paper2dsprites` dans un projet Unreal (Content Browser → Import) et constater qu'un flipbook naît. Si l'importateur refuse, le message d'Unreal nomme le champ manquant — le noter, corriger `paper2d_json`, et **mettre à jour l'étape 1 de cette tâche** : c'est là que vit la vérité sur ce format.

- [ ] **Étape 6 : commit** — sujet `sprites : T5 - la feuille Unreal Paper2D`, corps : la forme Array plutôt que Hash (l'ordre porte le flipbook), et l'incertitude sur le jeu de champs, avec les trois URL et leurs codes de retour.

### Tâche 6 — P4 : post-traitement PIL pur, image par image

**Files :**
- Create: `backend/app/services/sprite_post.py`
- Modify: `backend/app/services/sprite_service.py:31-111` (`normalize_opts`), `:614-630` (la passe pixel de `generate_sprites`)
- Modify: `frontend/spritelab/index.html` (fieldset), `frontend/spritelab/spritelab.css` (2 règles), `frontend/spritelab/spritelab.js` (`PREF_IDS`, `postOpts`, `wire`)
- Test: `backend/tests/test_sprite_post.py` (créer)

**Pourquoi (mesuré) :** `pixelate` rend le **natif** (`scale` forcé à 1 — `sprite_service.py:87`, `pixel_ops.py:174-176`) et c'est la cellule qui agrandit ensuite. Un post-traitement appliqué **après** pixel et **avant** l'assemblage donne donc un outline d'**un pixel natif** — celui que le jeu affichera — et non un pâté agrandi ×4. Les briques existent sans numpy : `ImageFilter` est déjà importé par `pixel_ops.py:6` et `particle_service.py:20-23`, et il porte `MaxFilter`, `MinFilter`, `MedianFilter`, `BoxBlur`, `GaussianBlur`.

**Où le post se branche, et pourquoi PAS dans `_assemble` :** dans `generate_sprites`, juste après la passe pixel (`sprite_service.py:614-630`), sur le même patron `_pix_file`. Deux raisons mesurées : (1) l'outline et l'ombre **agrandissent la toile**, et T1 mesure la taille de cellule « native » dans la passe 1 d'`_assemble` — poser le post après cette mesure donnerait des images plus grandes que la cellule ; (2) `particle_service` appelle `_assemble` directement (`:486-490`, `:537-540`) et ne passe **pas** par `generate_sprites` : les particules et les séquences Kenney n'héritent donc pas du post, et c'est voulu — un contour de 1 px sur une étincelle de gerbe n'a pas de sens.

- [ ] **Étape 1 : banc rouge**

Créer `backend/tests/test_sprite_post.py` :

```python
"""P4 — outline, ombre, nettoyage : les PIXELS du resultat, relus en PIL.

Run: python tests/test_sprite_post.py   (depuis backend/)
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio  # noqa: E402
import json  # noqa: E402

import pytest  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

ROUGE = (220, 40, 40, 255)


def _sujet():
    """20x20 : un carre plein 8x8 en (6,6)-(13,13), un TROU d'un pixel en
    (10,10), et un pixel ORPHELIN en (18,1)."""
    im = Image.new("RGBA", (20, 20), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([6, 6, 13, 13], fill=ROUGE)
    im.putpixel((10, 10), (0, 0, 0, 0))
    im.putpixel((18, 1), ROUGE)
    return im


def test_normalize_post_refuse_ce_qui_sort_des_bornes():
    from app.services import sprite_post as P
    assert P.normalize_post(None) is None
    assert P.normalize_post({}) is None
    o = P.normalize_post({"outline": {"width": 2, "color": "#00ff00"},
                          "shadow": {"dx": -3, "dy": 4, "opacity": 128},
                          "clean": {"orphans": True, "smooth": True}})
    assert o["outline"] == {"width": 2, "color": (0, 255, 0, 255)}
    assert o["shadow"]["dx"] == -3 and o["shadow"]["dy"] == 4
    assert o["shadow"]["color"] == (0, 0, 0, 255) and o["shadow"]["blur"] == 0
    assert o["clean"] == {"orphans": True, "smooth": True}
    for m in ({"outline": {"width": 0}}, {"outline": {"width": 5}},
              {"outline": {"width": 1, "color": "vert"}},
              {"outline": {"width": 1, "color": "#12345"}},
              {"shadow": {"dx": 33}}, {"shadow": {"dy": -33}},
              {"shadow": {"dx": 1, "blur": 9}},
              {"shadow": {"dx": 1, "opacity": 300}},
              {"outline": "1"}, {"clean": "yes"}):
        with pytest.raises(ValueError):
            P.normalize_post(m)


def test_l_outline_est_un_anneau_d_un_pixel_et_l_orphelin_disparait():
    from app.services import sprite_post as P
    o = P.normalize_post({"outline": {"width": 1, "color": "#00ff00"},
                          "clean": {"orphans": True}})
    out = P.apply_post(_sujet(), o)
    assert out.size == (22, 22)          # pad = 1 de chaque cote
    px = out.load()
    # le carre s'est decale de (1,1) : (6,6)-(13,13) -> (7,7)-(14,14)
    assert px[10, 10] == ROUGE                     # interieur intact
    assert px[6, 8] == (0, 255, 0, 255)            # anneau a gauche
    assert px[15, 8] == (0, 255, 0, 255)           # anneau a droite
    assert px[8, 6] == (0, 255, 0, 255)            # anneau en haut
    assert px[5, 8][3] == 0                        # rien a 2 px du bord
    # le TROU a ete bouche AVANT l'outline, donc pas d'anneau vert dedans
    assert px[11, 11] == ROUGE
    # l'ORPHELIN (18,1) -> (19,2) a disparu, et n'a pas laisse d'anneau
    assert px[19, 2][3] == 0 and px[18, 2][3] == 0 and px[19, 3][3] == 0


def test_l_ombre_est_decalee_derriere_le_sujet():
    from app.services import sprite_post as P
    o = P.normalize_post({"shadow": {"dx": 2, "dy": 3, "color": "#000000",
                                     "opacity": 128}})
    out = P.apply_post(_sujet(), o)
    assert out.size == (26, 26)          # pad = max(|2|, |3|) = 3
    px = out.load()
    # carre (6,6)-(13,13) -> (9,9)-(16,16) ; ombre -> (11,12)-(18,19)
    assert px[18, 19] == (0, 0, 0, 128)            # ombre seule
    assert px[11, 12] == ROUGE                     # le sujet passe devant
    assert px[9, 9] == ROUGE
    assert px[8, 8][3] == 0                        # ni sujet ni ombre


def test_le_lissage_mange_une_dent_d_un_pixel():
    from app.services import sprite_post as P
    im = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([3, 3, 8, 8], fill=ROUGE)
    im.putpixel((9, 5), ROUGE)                     # dent d'un pixel de large
    out = P.apply_post(im, P.normalize_post({"clean": {"smooth": True}}))
    assert out.size == (12, 12)                    # pas d'outline : pad = 0
    assert out.load()[9, 5][3] == 0
    assert out.load()[6, 6] == ROUGE


def test_le_post_traverse_le_pipeline_et_le_manifeste_le_dit():
    from app.config import settings
    from app.services import sprite_service as S
    noms = []
    for i in range(2):
        n = f"post{i}.png"
        _sujet().save(settings.images_path / n)
        noms.append(n)
    asyncio.run(S.generate_sprites(
        {"source": {"kind": "images", "filenames": noms},
         "cell": {"size": "native"}, "columns": 2,
         "post": {"outline": {"width": 1, "color": "#00ff00"},
                  "clean": {"orphans": True}}}, "j-post"))
    d = settings.outputs_path / "sprites" / "j-post"
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    assert m["post"]["outline"]["width"] == 1
    assert m["grid"]["cell_w"] == 22            # la toile a grandi de 2 px
    with Image.open(d / "frames" / "000.png") as c:
        assert c.convert("RGBA").load()[6, 8] == (0, 255, 0, 255)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
```

- [ ] **Étape 2 : le voir rouge**

Run: `cd backend && python tests/test_sprite_post.py`
Expected: `5 failed` — `ModuleNotFoundError: No module named 'app.services.sprite_post'`.

- [ ] **Étape 3 : écrire `sprite_post.py`**

Créer `backend/app/services/sprite_post.py` :

```python
"""P4 — post-traitement d'une image de sprite, en PIL PUR (plan sprites, T6).

AUCUNE BOUCLE PYTHON PAR PIXEL, et c'est la contrainte qui a dicte chaque
choix : `MaxFilter`, `MedianFilter`, `BoxBlur` et `GaussianBlur` sont
implementes en C dans Pillow, et `point()` construit une table de 256 entrees
— pas une boucle sur les pixels. Le runtime embarque n'a pas numpy
(`pixel_ops.py` le dit deja en tete).

ORDRE : nettoyage -> contour -> ombre. Le nettoyage d'abord, sinon un pixel
orphelin recevrait son propre anneau de contour ; l'ombre en dernier, pour
qu'elle porte la silhouette CONTOUR COMPRIS — c'est ce qu'un artiste attend.

La toile GRANDIT (le contour deborde, l'ombre se decale) : `apply_post` rend
donc une image plus grande que celle qu'on lui donne. C'est pourquoi il
tourne dans `generate_sprites`, AVANT `_assemble` — qui mesure la cellule
« native » sur les images qu'on lui passe.
"""
from __future__ import annotations

import re

from PIL import Image, ImageChops, ImageFilter, ImageOps

__all__ = ["normalize_post", "apply_post"]

_HEX = re.compile(r"^#?([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


# ── normalisation ───────────────────────────────────────────────────────────
def _int(bloc: dict, nom: str, defaut: int, lo: int, hi: int) -> int:
    brut = bloc.get(nom)
    if brut is None or brut == "":
        return defaut
    try:
        v = int(brut)
    except (TypeError, ValueError):
        raise ValueError(f"post.{nom} must be an integer ({lo}..{hi})")
    if not lo <= v <= hi:
        raise ValueError(f"post.{nom} must be between {lo} and {hi}")
    return v


def _couleur(v, defaut: tuple[int, int, int, int]):
    if v in (None, ""):
        return defaut
    m = _HEX.match(str(v))
    if not m:
        raise ValueError(f"post color {v!r} must be #RRGGBB or #RRGGBBAA")
    h = m.group(1)
    vals = tuple(int(h[i:i + 2], 16) for i in range(0, len(h), 2))
    return vals if len(vals) == 4 else vals + (255,)


def normalize_post(spec) -> dict | None:
    """{outline?, shadow?, clean?} normalise, ou **None** quand rien n'est
    demande — le None fait sauter toute la passe dans `generate_sprites`,
    plutot que de payer une copie d'image pour ne rien faire."""
    if spec in (None, "", {}):
        return None
    if not isinstance(spec, dict):
        raise ValueError("post must be an object {outline, shadow, clean}")
    out: dict = {}

    ol = spec.get("outline")
    if ol not in (None, "", {}):
        if not isinstance(ol, dict):
            raise ValueError("post.outline must be an object {width, color}")
        out["outline"] = {"width": _int(ol, "width", 1, 1, 4),
                          "color": _couleur(ol.get("color"), (0, 0, 0, 255))}

    sh = spec.get("shadow")
    if sh not in (None, "", {}):
        if not isinstance(sh, dict):
            raise ValueError(
                "post.shadow must be an object {dx, dy, blur, opacity, color}")
        out["shadow"] = {"dx": _int(sh, "dx", 2, -32, 32),
                         "dy": _int(sh, "dy", 2, -32, 32),
                         "blur": _int(sh, "blur", 0, 0, 4),
                         "opacity": _int(sh, "opacity", 110, 0, 255),
                         "color": _couleur(sh.get("color"), (0, 0, 0, 255))}

    cl = spec.get("clean")
    if cl not in (None, "", {}):
        if not isinstance(cl, dict):
            raise ValueError("post.clean must be an object {orphans, smooth}")
        c = {"orphans": bool(cl.get("orphans")),
             "smooth": bool(cl.get("smooth"))}
        if c["orphans"] or c["smooth"]:
            out["clean"] = c

    return out or None


# ── briques ─────────────────────────────────────────────────────────────────
def _masque(im: Image.Image) -> Image.Image:
    """Alpha BINAIRE (seuil 128) — meme seuil que `pixel_ops.pixelate`
    (`pixel_ops.py:168`), sinon un bord a demi transparent produirait un
    contour a demi transparent et le pixel-art perdrait sa nettete."""
    return im.getchannel("A").point(lambda a: 255 if a >= 128 else 0)


def _nettoyer(im: Image.Image, cl: dict) -> Image.Image:
    mask = _masque(im)
    if cl["orphans"]:
        # BoxBlur(1) = moyenne d'une fenetre 3x3, x255. Un pixel opaque SEUL
        # vaut 255/9 = 28 ; lui plus UN voisin, 57 ; un trio, 85. Le seuil 56
        # retire donc le pixel seul et le couple, garde le trio.
        dens = mask.filter(ImageFilter.BoxBlur(1))
        mask = ImageChops.multiply(mask, dens.point(
            lambda v: 255 if v > 56 else 0))
        # TROU d'un pixel dans une zone pleine : 8 voisins sur 9 -> 226.
        trou = ImageChops.multiply(
            dens.point(lambda v: 255 if v >= 200 else 0),
            mask.point(lambda v: 255 - v))
        mask = ImageChops.lighter(mask, trou)
    if cl["smooth"]:
        # median 3x3 sur un masque binaire = vote majoritaire : une dent d'un
        # pixel disparait, un trait continu d'un pixel de large survit.
        mask = mask.filter(ImageFilter.MedianFilter(3)).point(
            lambda v: 255 if v >= 128 else 0)
    # les pixels DEVENUS opaques (trous bouches) n'ont pas de couleur sous
    # eux : on leur donne la mediane du voisinage, les autres gardent la leur.
    rgb = im.convert("RGB")
    out = Image.composite(rgb, rgb.filter(ImageFilter.MedianFilter(3)),
                          _masque(im)).convert("RGBA")
    out.putalpha(mask)
    return out


def _contour(im: Image.Image, ol: dict) -> Image.Image:
    """Dilatation de l'alpha par `MaxFilter(3)` repetee `width` fois, moins le
    masque d'origine : l'anneau EXTERIEUR, exactement `width` pixels."""
    mask = _masque(im)
    grossi = mask
    for _ in range(ol["width"]):
        grossi = grossi.filter(ImageFilter.MaxFilter(3))
    anneau = ImageChops.subtract(grossi, mask)
    r, g, b, a = ol["color"]
    couche = Image.new("RGBA", im.size, (r, g, b, 0))
    couche.putalpha(anneau.point(lambda v: v * a // 255))
    return Image.alpha_composite(couche, im)


def _ombre(im: Image.Image, sh: dict) -> Image.Image:
    mask = _masque(im)
    if sh["blur"]:
        mask = mask.filter(ImageFilter.GaussianBlur(sh["blur"]))
    r, g, b, a = sh["color"]
    opac = sh["opacity"] * a // 255
    couche = Image.new("RGBA", im.size, (r, g, b, 0))
    couche.putalpha(mask.point(lambda v: v * opac // 255))
    fond = Image.new("RGBA", im.size, (0, 0, 0, 0))
    # `paste` accepte une boite NEGATIVE et rogne : c'est ce qui rend dx/dy
    # negatifs sans arithmetique de bord (alpha_composite, lui, refuserait).
    fond.paste(couche, (sh["dx"], sh["dy"]), couche)
    return Image.alpha_composite(fond, im)


# ── op ──────────────────────────────────────────────────────────────────────
def apply_post(img: Image.Image, opts: dict | None) -> Image.Image:
    """Image -> image post-traitee, PLUS GRANDE de `pad` de chaque cote."""
    if not opts:
        return img
    im = img.convert("RGBA")
    ol, sh, cl = opts.get("outline"), opts.get("shadow"), opts.get("clean")
    pad = 0
    if ol:
        pad = max(pad, ol["width"])
    if sh:
        pad = max(pad, abs(sh["dx"]) + sh["blur"], abs(sh["dy"]) + sh["blur"])
    if pad:
        im = ImageOps.expand(im, pad, (0, 0, 0, 0))
    if cl:
        im = _nettoyer(im, cl)
    if ol:
        im = _contour(im, ol)
    if sh:
        im = _ombre(im, sh)
    return im
```

- [ ] **Étape 4 : brancher dans `sprite_service.py`**

Dans `normalize_opts`, sous le bloc `pixel` :

```python
    # P4 : post-traitement local (contour, ombre, nettoyage) — PIL pur, par
    # image, apres pixel et avant l'assemblage.
    from app.services.sprite_post import normalize_post
    post = normalize_post(body.get("post"))
```

et le dictionnaire rendu gagne `"post": post,`.

Dans `generate_sprites`, juste après la passe pixel (après `raw[i] = dest` / `await _step("Pixel-art ...")`) :

```python
    # P4 (T6) — post-traitement par image. Meme patron que la passe pixel :
    # un fichier par image dans _raw, jamais en memoire toutes ensemble.
    if opts.get("post"):
        from PIL import Image as _Ip
        from app.services.sprite_post import apply_post

        def _post_file(src_path: Path, dest: Path):
            with _Ip.open(src_path) as im:
                out = apply_post(im, opts["post"])
            out.save(dest, format="PNG")

        for i, path in enumerate(raw):
            dest = raw_dir / f"post_{i:04d}.png"
            await asyncio.to_thread(_post_file, path, dest)
            raw[i] = dest
            await _step(f"Post-traitement {i + 1}/{len(raw)}",
                        70 + int(5 * (i + 1) / len(raw)))
```

Dans `_assemble`, le manifeste gagne `"post": opts.get("post"),` après `"pixel"`. `opts.get` : `particle_service` ne pose pas cette clé.

- [ ] **Étape 5 : vert**

Run: `cd backend && python tests/test_sprite_post.py`
Expected: `5 passed`.
Run: `cd backend && python tests/test_sprite_native.py && python tests/test_sprite_exports.py`
Expected: `2 passed` puis `4 passed`.

- [ ] **Étape 6 : l'écran**

`index.html`, après le fieldset « Animation » :

```html
      <fieldset class="postset">
        <legend><label><input type="checkbox" id="postOn"> Post-traitement (P4)</label></legend>
        <div class="grid2" id="postFields">
          <label class="fld">Contour <span class="unit">px</span>
            <select id="poWidth"><option value="0" selected>aucun</option><option>1</option><option>2</option><option>3</option><option>4</option></select>
          </label>
          <label class="fld">Couleur du contour
            <input id="poColor" type="color" value="#000000">
          </label>
          <label class="fld">Ombre X / Y <span class="unit">px</span>
            <span class="pair"><input id="poDx" type="number" min="-32" max="32" value="0"><input id="poDy" type="number" min="-32" max="32" value="0"></span>
          </label>
          <label class="fld">Opacité de l'ombre <span class="unit">0-255</span>
            <input id="poOpacity" type="number" min="0" max="255" value="110">
          </label>
          <label class="fld"><span><input type="checkbox" id="poOrphans"> Nettoyer les pixels orphelins</span></label>
          <label class="fld"><span><input type="checkbox" id="poSmooth"> Lisser les bords</span></label>
        </div>
        <div class="hint">Appliqué à chaque image <b>après</b> le pixel-art et
          <b>avant</b> la feuille : le contour fait 1 px <i>natif</i>, pas
          1 px agrandi. La toile grandit d'autant.</div>
      </fieldset>
```

`spritelab.css`, à la fin :

```css
/* ── P4 : post-traitement ── */
.postset{border:1px solid var(--stroke);border-radius:var(--r);padding:8px 10px;margin:10px}
.postset legend{font-size:11.5px;color:var(--ink-soft);padding:0 4px}
.postset.off #postFields{opacity:.4;pointer-events:none}
.pair{display:flex;gap:6px}
.pair input{width:100%}
```

`spritelab.js` : `PREF_IDS` gagne `"poWidth", "poColor", "poDx", "poDy", "poOpacity"` ; `collectPrefs` gagne `postOn: $("#postOn").checked, poOrphans: $("#poOrphans").checked, poSmooth: $("#poSmooth").checked` ; `applyPrefs` les repose ; et :

```js
function syncPostSet() {
  $(".postset").classList.toggle("off", !$("#postOn").checked);
}
function postOpts() {
  if (!$("#postOn").checked) return undefined;
  const o = {};
  const w = parseInt($("#poWidth").value, 10) || 0;
  if (w > 0) o.outline = { width: w, color: $("#poColor").value };
  const dx = parseInt($("#poDx").value, 10) || 0;
  const dy = parseInt($("#poDy").value, 10) || 0;
  if (dx || dy) o.shadow = { dx, dy, opacity: parseInt($("#poOpacity").value, 10) || 110 };
  if ($("#poOrphans").checked || $("#poSmooth").checked)
    o.clean = { orphans: $("#poOrphans").checked, smooth: $("#poSmooth").checked };
  return Object.keys(o).length ? o : undefined;
}
```

Dans `generate()`, après `const px = pixelOpts(); if (px) body.pixel = px;` :

```js
    const po = postOpts(); if (po) body.post = po;
```

Dans `wire()` : `$("#postOn").onchange = () => { syncPostSet(); savePrefs(); };` et les six contrôles dans la boucle `onchange = () => { savePrefs(); updateCost(); }` ; dans `init()`, `syncPostSet();` à côté de `syncPixelSet();`.

- [ ] **Étape 7 : commit** — sujet `sprites : T6 - contour ombre et nettoyage en PIL pur` ; corps : le post tourne **après** pixel (donc 1 px natif), il **agrandit** la toile donc il vit dans `generate_sprites` et non dans `_assemble` (qui y mesure la cellule native), et les particules n'en héritent pas — c'est voulu.

### Tâche 7 — P5a : réordonner, dupliquer, supprimer

**Files :**
- Modify: `backend/app/services/sprite_service.py` (nouvelle `reassemble`, après `_assemble`)
- Modify: `backend/app/api/routes.py:1513` (route `POST /assets/sprite/{job}/reassemble`)
- Modify: `frontend/spritelab/index.html:191` (bande « Éditeur »), `frontend/spritelab/spritelab.css`, `frontend/spritelab/spritelab.js` (`showResult`, nouvelle section)
- Test: `backend/tests/test_sprite_editor.py` (créer)

**Pourquoi (mesuré) :** une fois la feuille faite, la seule façon de changer l'ordre est de refaire tout le job — donc de repayer le détourage API (`sprite_service.py:530-560`) et de reperdre la sélection du filmstrip. Les cases sont pourtant déjà sur le disque (`frames/000.png`…, écrites par `_assemble` à `:417-418`) : réassembler est gratuit et local.

**LE PIÈGE, nommé avant le code :** `_assemble` **écrit** `frames/{i:03d}.png` pendant qu'il **lit** ses entrées. Avec l'ordre `[3, 0, 0]`, l'itération 0 lit `frames/003.png` et écrit `frames/000.png` ; l'itération 1 lit `frames/000.png` — **déjà écrasé**. Les cases choisies sont donc copiées dans `_edit/` d'abord. Sans cette copie, le banc ci-dessous est vert sur `[0,1,2,3]` et faux sur `[3,0,0]` : c'est exactement l'ordre que le banc utilise.

- [ ] **Étape 1 : banc rouge**

Créer `backend/tests/test_sprite_editor.py` :

```python
"""P5a — reordonner / dupliquer / supprimer : la feuille EST relue.

Run: python tests/test_sprite_editor.py   (depuis backend/)
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio  # noqa: E402
import json  # noqa: E402

import pytest  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

COULEURS = [(220, 40, 40, 255), (40, 220, 40, 255),
            (40, 40, 220, 255), (220, 220, 40, 255)]


def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def _png(nom, couleur, taille=(24, 24)):
    from app.config import settings
    im = Image.new("RGBA", taille, (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle([2, 2, taille[0] - 3, taille[1] - 3],
                                 fill=couleur)
    im.save(settings.images_path / nom)
    return nom


def _feuille(job):
    from app.config import settings
    from app.services import sprite_service as S
    noms = [_png(f"{job}-{i}.png", c) for i, c in enumerate(COULEURS)]
    asyncio.run(S.generate_sprites(
        {"source": {"kind": "images", "filenames": noms},
         "cell": {"size": 128}, "columns": 2, "fps_sample": 8}, job))
    return settings.outputs_path / "sprites" / job


def _centres(sheet_path, n, cols, cote):
    with Image.open(sheet_path) as sh:
        rgba = sh.convert("RGBA")
        return [rgba.getpixel(((i % cols) * cote + cote // 2,
                               (i // cols) * cote + cote // 2))
                for i in range(n)]


def test_reordonner_dupliquer_supprimer_en_un_seul_ordre():
    d = _feuille("j-edit")
    r = _client().post("/api/assets/sprite/j-edit/reassemble",
                       json={"order": [3, 0, 0], "columns": 3})
    assert r.status_code == 200, r.text
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    assert len(m["frames"]) == 3
    assert m["grid"] == {"cols": 3, "rows": 1, "cell_w": 128, "cell_h": 128}
    assert m["source"]["reassembled"] is True
    # LA feuille, relue : jaune (3), rouge (0), rouge (0)
    assert _centres(d / "sheet.png", 3, 3, 128) == \
        [COULEURS[3], COULEURS[0], COULEURS[0]]
    # les exports ont ete reecrits avec les 3 nouvelles cases
    assert (d / "sheet.tres").read_text("utf-8").count(
        '[sub_resource type="AtlasTexture"') == 3
    assert len(json.loads(
        (d / "sheet.paper2dsprites").read_text("utf-8"))["frames"]) == 3
    assert not (d / "_edit").exists()          # le dossier de travail est parti


def test_les_bornes_de_l_ordre_refusent_en_le_disant():
    _feuille("j-borne")
    c = _client()
    for corps in ({"order": []}, {"order": [0, 4]}, {"order": "0"},
                  {"order": [0] * 65}, {"order": [-1]}, {"order": [1.5]},
                  {"order": [0], "columns": 99}):
        r = c.post("/api/assets/sprite/j-borne/reassemble", json=corps)
        assert r.status_code == 400, (corps, r.status_code, r.text)
    assert c.post("/api/assets/sprite/j-absent/reassemble",
                  json={"order": [0]}).status_code == 404


def test_les_tags_suivent_le_nouvel_ordre():
    d = _feuille("j-tags")
    r = _client().post("/api/assets/sprite/j-tags/reassemble",
                       json={"order": [0, 1, 2], "columns": 3,
                             "anim": {"tags": [{"name": "idle", "from": 0,
                                                "to": 2}],
                                      "durations": [90, 90, 90]}})
    assert r.status_code == 200, r.text
    m = json.loads((d / "manifest.json").read_text("utf-8"))
    assert m["anim"]["tags"][0] == {"name": "idle", "from": 0, "to": 2,
                                    "direction": "forward", "repeat": 0}
    assert [f["duration_ms"] for f in m["frames"]] == [90, 90, 90]
    assert '&"idle"' in (d / "sheet.tres").read_text("utf-8")
    # un tag qui deborde le NOUVEL ordre est refuse
    assert _client().post("/api/assets/sprite/j-tags/reassemble",
                          json={"order": [0, 1],
                                "anim": {"tags": [{"name": "x", "from": 0,
                                                   "to": 2}]}}
                          ).status_code == 400


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
```

- [ ] **Étape 2 : rouge** — Run: `cd backend && python tests/test_sprite_editor.py` — Expected: `3 failed` (`assert 404 == 200` : la route n'existe pas).

- [ ] **Étape 3 : `reassemble` dans `sprite_service.py`**

Après `_assemble` :

```python
def reassemble(out_dir: Path, order: list[int], columns=None,
               anim_spec=None) -> dict:
    """Refabrique la feuille d'un job A PARTIR DE SES PROPRES CASES.

    Gratuit et local : les cases sont deja sur le disque (`frames/000.png`…,
    ecrites par `_assemble`), donc reordonner, dupliquer ou supprimer ne
    repaie ni le detourage API ni l'extraction.

    LE PIEGE : `_assemble` ECRIT `frames/{i:03d}.png` pendant qu'il LIT ses
    entrees. Avec l'ordre [3, 0, 0], l'iteration 0 ecrit `frames/000.png` et
    l'iteration 1 le relit — deja ecrase. Les cases choisies sont donc
    copiees dans `_edit/` d'abord, et ce dossier est efface a la fin.
    """
    import shutil as _sh
    from app.services.sprite_anim import normalize_anim

    mf = out_dir / "manifest.json"
    if not mf.is_file():
        raise FileNotFoundError("manifest.json")
    ancien = json.loads(mf.read_text(encoding="utf-8"))
    if not ancien.get("grid"):
        raise ValueError("this job has no grid (frames-only probe) — "
                         "generate a sheet before editing it")
    n_old = len(ancien.get("frames") or [])

    if not isinstance(order, (list, tuple)) or not order:
        raise ValueError("order must be a non-empty list of frame indices")
    if len(order) > 64:
        raise ValueError("order: 64 frames at most")
    idx = []
    for v in order:
        if isinstance(v, bool) or not isinstance(v, int):
            raise ValueError("order: frame indices are integers")
        if not 0 <= v < n_old:
            raise ValueError(f"order: index {v} outside 0..{n_old - 1}")
        idx.append(v)

    cols = ancien["grid"]["cols"] if columns in (None, "") else columns
    if cols != "auto":
        try:
            cols = int(cols)
        except (TypeError, ValueError):
            raise ValueError("columns must be 'auto' or an integer (1-32)")
        if not 1 <= cols <= 32:
            raise ValueError("columns must be 'auto' or an integer (1-32)")

    fps = ancien.get("fps") or 8
    anim = ancien.get("anim") if anim_spec in (None, "") else anim_spec
    normalize_anim(anim, len(idx), fps)      # refus AVANT toute ecriture

    edit = out_dir / "_edit"
    _sh.rmtree(edit, ignore_errors=True)
    edit.mkdir(parents=True)
    try:
        fichiers = []
        for k, i in enumerate(idx):
            src = out_dir / (ancien["frames"][i]["file"])
            dest = edit / f"src_{k:04d}.png"
            _sh.copy2(src, dest)
            fichiers.append((dest, bool(ancien["frames"][i].get("bg_removed"))))
        # cell_size 0 = « native » (T1) : les cases FONT deja la cellule, donc
        # `_place_into_cell` les POSE sans passer par un resize — les octets
        # d'une case survivent au reassemblage, ce que le banc verifie.
        opts = {"cell_size": 0, "align": ancien.get("align") or "center",
                "trim": "animation", "columns": cols, "fps": fps,
                "pixel": ancien.get("pixel"), "post": ancien.get("post"),
                "anim": anim}
        info = dict(ancien.get("source") or {}, reassembled=True)
        return _assemble(fichiers, opts, out_dir, info)
    finally:
        _sh.rmtree(edit, ignore_errors=True)
```

- [ ] **Étape 4 : la route**

`routes.py`, après `/assets/sprite/{job}/paper2d` :

```python
@router.post("/assets/sprite/{job}/reassemble")
async def reassemble_sprite(job: str, body: dict):
    """P5a — refabrique la feuille depuis ses propres cases : `order` porte
    a la fois le reordonnancement, la duplication (un index deux fois) et la
    suppression (un index absent). En PLACE : le dossier du job ne change
    pas, donc toutes les URL de telechargement restent valides et la page
    n'a rien a re-router."""
    from app.services.sprite_service import reassemble
    d = _sprite_dir(job)
    if not (d / "manifest.json").is_file():
        raise HTTPException(404, "Not found")
    try:
        r = await asyncio.to_thread(
            reassemble, d, body.get("order"), body.get("columns"),
            body.get("anim"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "frames": r["frames"], "grid": r["grid"]}
```

- [ ] **Étape 5 : vert** — Run: `cd backend && python tests/test_sprite_editor.py` — Expected: `3 passed`.

- [ ] **Étape 6 : la bande « Éditeur »**

`index.html`, après `<div id="exports">` :

```html
    <div id="editor" class="editor hidden">
      <div class="editor-head">
        <b>Éditeur</b>
        <span id="editInfo" class="counter">—</span>
        <button id="editApply" class="btn primary" title="Réassemble la feuille avec cet ordre (local, gratuit)">✔ Appliquer</button>
        <button id="editReset" class="btn ghost" title="Revenir à l'ordre du manifeste">↺ Annuler</button>
      </div>
      <div id="editStrip" class="editstrip"></div>
      <div id="editStatus" class="status hidden"></div>
    </div>
```

`spritelab.css`, à la fin :

```css
/* ── P5a : editeur d'ordre ── */
.editor{border-top:1px solid var(--stroke);padding:10px 12px}
.editor-head{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.editstrip{display:flex;gap:8px;overflow-x:auto;padding-bottom:6px}
.editcell{flex:0 0 auto;width:76px;border:1px solid var(--stroke-strong);border-radius:8px;background:var(--bg-panel-2);padding:4px;text-align:center}
.editcell img{width:64px;height:64px;image-rendering:pixelated;background:var(--bg-base)}
.editcell .no{font-size:10.5px;color:var(--ink-muted);font-family:var(--f-mono)}
.editcell .ops{display:flex;justify-content:center;gap:2px;margin-top:2px}
.editcell .ops button{border:none;background:none;color:var(--ink-soft);cursor:pointer;font-size:12px;padding:0 2px}
.editcell .ops button:hover{color:var(--cyan)}
.editcell.sel{border-color:var(--cyan)}
```

`spritelab.js`, nouvelle section avant « préviz » :

```js
/* ───────── P5a : ordre des images ─────────
   `editOrder` est un tableau d'INDEX du manifeste : dupliquer, c'est répéter
   un index ; supprimer, c'est l'ôter. Le serveur refait la feuille — la page
   ne fabrique aucun PNG. */
let editOrder = [];

function renderEditor() {
  if (!sheet) return;
  const short = sheet.short;
  $("#editInfo").textContent = editOrder.length + " image(s)";
  $("#editStrip").innerHTML = editOrder.map((src, k) => `
    <div class="editcell" data-k="${k}">
      <img src="/api/assets/sprite/${short}/frame/${src}" alt="">
      <div class="no">#${src}</div>
      <div class="ops">
        <button data-op="left" title="Vers la gauche">◀</button>
        <button data-op="dup" title="Dupliquer">⧉</button>
        <button data-op="del" title="Supprimer">✕</button>
        <button data-op="right" title="Vers la droite">▶</button>
      </div>
    </div>`).join("");
  $$("#editStrip .ops button").forEach(b => b.onclick = () => {
    const k = parseInt(b.closest(".editcell").dataset.k, 10);
    const op = b.dataset.op;
    if (op === "left" && k > 0) editOrder.splice(k - 1, 0, editOrder.splice(k, 1)[0]);
    else if (op === "right" && k < editOrder.length - 1) editOrder.splice(k + 1, 0, editOrder.splice(k, 1)[0]);
    else if (op === "dup" && editOrder.length < 64) editOrder.splice(k, 0, editOrder[k]);
    else if (op === "del" && editOrder.length > 1) editOrder.splice(k, 1);
    renderEditor();
  });
}

async function applyEditor() {
  if (!sheet || !editOrder.length) return;
  const st = $("#editStatus");
  try {
    setStatus(st, "Réassemblage…", false, 20);
    await api.send("POST", `/assets/sprite/${sheet.short}/reassemble`,
      { order: editOrder, columns: $("#columns").value === "auto" ? "auto"
                                    : parseInt($("#columns").value, 10),
        anim: animOpts(editOrder.length) });
    const m = await api.get("/assets/sprite/" + sheet.short + "/manifest");
    clearStatus(st);
    showResult(sheet.short, m);
    toast("Feuille réassemblée ✓ — local, gratuit");
  } catch (e) {
    setStatus(st, "Échec : " + e.message, true);
  }
}
```

Dans `showResult`, après `buildPlayer(short, m);` :

```js
  editOrder = m.frames.map(f => f.index);
  $("#editor").classList.toggle("hidden", !m.grid);
  renderEditor();
```

Dans `wire()` : `$("#editApply").onclick = applyEditor;` et `$("#editReset").onclick = () => { if (sheet) { editOrder = sheet.manifest.frames.map(f => f.index); renderEditor(); } };`

- [ ] **Étape 7 : commit** — sujet `sprites : T7 - reordonner dupliquer supprimer sans repayer` ; corps : les cases sont déjà sur le disque, `_assemble` écrit là où il lit (piège nommé, dossier `_edit/`), et l'ordre porte les trois gestes.

### Tâche 8 — P5b : pelure d'oignon et retouche pixel

**Files :**
- Modify: `backend/app/api/routes.py:1493-1500` (à côté de `get_sprite_frame`), constante de borne près de `_PNG_MAGIC` (`:6386`)
- Modify: `frontend/spritelab/index.html` (le canevas d'édition), `frontend/spritelab/spritelab.css`, `frontend/spritelab/spritelab.js`
- Test: `backend/tests/test_sprite_frame_edit.py` (créer)

**Pourquoi (mesuré) :** une case ratée d'un pixel oblige aujourd'hui à refaire le job entier. La règle du dépôt donne la forme exacte de la solution : `POST /etabli/vignette` (`routes.py:9307-9400`) est **la** route d'écriture qui reçoit des octets du navigateur, et ses cinq gardes — version entière positive, cible confinée, existence de la cible, borne de taille **avant** l'examen du contenu, signature PNG — sont recopiées ici avec une sixième, propre aux sprites : **la taille de l'image doit être celle de la case**.

- [ ] **Étape 1 : banc rouge**

Créer `backend/tests/test_sprite_frame_edit.py` :

```python
"""P5b — la retouche d'une case : le navigateur voit, PYTHON ecrit.

Run: python tests/test_sprite_frame_edit.py   (depuis backend/)
"""
import io
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio  # noqa: E402

import pytest  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

MAGENTA = (255, 0, 255, 255)


def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def _octets(im) -> bytes:
    b = io.BytesIO()
    im.save(b, format="PNG")
    return b.getvalue()


@pytest.fixture(scope="module")
def dossier():
    from app.config import settings
    from app.services import sprite_service as S
    noms = []
    for i in range(3):
        n = f"r{i}.png"
        im = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
        ImageDraw.Draw(im).rectangle([2, 2, 21, 21],
                                     fill=(40 + 60 * i, 90, 120, 255))
        im.save(settings.images_path / n)
        noms.append(n)
    asyncio.run(S.generate_sprites(
        {"source": {"kind": "images", "filenames": noms},
         "cell": {"size": 128}, "columns": 3}, "j-ret"))
    return settings.outputs_path / "sprites" / "j-ret"


def test_une_case_retouchee_arrive_sur_le_disque_ET_dans_la_feuille(dossier):
    with Image.open(dossier / "frames" / "001.png") as c:
        neuve = c.convert("RGBA")
    neuve.putpixel((64, 64), MAGENTA)
    r = _client().put("/api/assets/sprite/j-ret/frame/1",
                      content=_octets(neuve),
                      headers={"Content-Type": "image/png"})
    assert r.status_code == 200, r.text
    with Image.open(dossier / "frames" / "001.png") as c:
        assert c.convert("RGBA").getpixel((64, 64)) == MAGENTA
    # la FEUILLE a suivi : case 1 = colonne 1, ligne 0
    with Image.open(dossier / "sheet.png") as sh:
        assert sh.convert("RGBA").getpixel((128 + 64, 64)) == MAGENTA
    # et aucun .tmp orphelin
    assert not list((dossier / "frames").glob("*.tmp"))


def test_les_six_gardes_mordent_dans_l_ordre(dossier):
    c = _client()
    # 1. l'index doit exister
    assert c.put("/api/assets/sprite/j-ret/frame/99",
                 content=b"\x89PNG\r\n\x1a\n").status_code == 404
    assert c.put("/api/assets/sprite/j-absent/frame/0",
                 content=b"\x89PNG\r\n\x1a\n").status_code == 404
    # 2. la taille borne AVANT l'examen du contenu
    assert c.put("/api/assets/sprite/j-ret/frame/0",
                 content=b"\x89PNG\r\n\x1a\n" + b"\0" * (3 << 20)
                 ).status_code == 413
    # 3. la signature PNG : l'en-tete Content-Type ne prouve rien
    assert c.put("/api/assets/sprite/j-ret/frame/0", content=b"pas un png",
                 headers={"Content-Type": "image/png"}).status_code == 400
    # 4. la taille de l'image DOIT etre celle de la case
    petite = Image.new("RGBA", (64, 64), MAGENTA)
    r = c.put("/api/assets/sprite/j-ret/frame/0", content=_octets(petite))
    assert r.status_code == 400 and "128" in r.text
    # 5. un index negatif n'est le numero de rien
    assert c.put("/api/assets/sprite/j-ret/frame/-1",
                 content=b"\x89PNG\r\n\x1a\n").status_code in (400, 404, 422)


def test_la_page_ne_fabrique_jamais_la_feuille():
    """La regle du depot : le navigateur voit et manipule, Python ecrit. La
    page envoie UNE case PNG ; elle n'assemble ni feuille, ni GIF, ni export."""
    racine = pathlib.Path(__file__).resolve().parent.parent.parent
    js = (racine / "frontend" / "spritelab" / "spritelab.js").read_text("utf-8")
    for interdit in ("sheet.png", "createImageBitmap(sheetImg",
                     "JSZip", "new Blob([JSON.stringify"):
        assert interdit not in js, interdit
    assert "toBlob" in js                      # la capture de la case, elle, existe
    assert js.count('"PUT", `/assets/sprite/') == 0   # le PNG passe par fetch brut


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
```

- [ ] **Étape 2 : rouge** — Run: `cd backend && python tests/test_sprite_frame_edit.py` — Expected: `3 failed` (`assert 405 == 200` : la méthode PUT n'existe pas sur cette route).

- [ ] **Étape 3 : la route**

`routes.py`, juste après `get_sprite_frame` (ligne 1500) :

```python
# 2 Mio. Une case de 512x512 en PNG pese quelques dizaines de kilo-octets ;
# la borne laisse une marge large et refuse PARLANT au lieu d'avaler. Meme
# raisonnement, meme chiffre que _ETABLI_VIGNETTE_MAX (routes.py:9306).
_SPRITE_FRAME_MAX = 2 * 1024 * 1024


@router.put("/assets/sprite/{job}/frame/{i}")
async def put_sprite_frame(job: str, i: int, request: Request):
    """P5b — depose une case retouchee. LE NAVIGATEUR VOIT ET MANIPULE,
    PYTHON ECRIT : la page dessine sur un canevas et envoie SES octets PNG ;
    la feuille, le GIF et les quatre exports sont refaits ICI, en Python, par
    `reassemble` avec l'ordre identite. Sans ce reassemblage, `frames/001.png`
    et `sheet.png` se contrediraient — pire qu'un refus, qui se dit.

    LES GARDES, dans l'ordre ou elles mordent :
      1. la CASE DOIT EXISTER (404). C'est aussi ce qui empeche de fabriquer
         un dossier de job a volonte ; `_sprite_dir` aplatit deja le nom ;
      2. la TAILLE est bornee AVANT tout examen du contenu — c'est la garde
         la moins chere, elle passe donc en premier des deux (413) ;
      3. la SIGNATURE PNG (400) : l'en-tete `Content-Type` ne prouve rien ;
      4. la TAILLE DE L'IMAGE doit etre celle de la case (400). Une case
         d'une autre taille casserait la grille : le manifeste annonce des
         cellules carrees egales, et la feuille cesserait de lui ressembler.

    FAIBLESSE CONNUE, la meme qu'a `/etabli/vignette` et dite pour la meme
    raison : `await request.body()` bufferise le corps ENTIER avant que la
    borne ne morde. Non corrige, delibere — `routes.py` compte plusieurs
    `await request.body()` sans borne du tout, et faire de celle-ci la seule
    ceremonieuse serait une incoherence pour un gain nul sur une API locale
    sans authentification.
    """
    if i < 0:
        raise HTTPException(400, f"frame {i} — les cases sont numerotees a "
                                 "partir de 0")
    p = _sprite_dir(job) / "frames" / f"{int(i):03d}.png"
    if not p.is_file():
        raise HTTPException(404, "Not found")
    octets = await request.body()
    if len(octets) > _SPRITE_FRAME_MAX:
        raise HTTPException(413, f"case : {len(octets)} octets, la borne est "
                                 f"a {_SPRITE_FRAME_MAX // 1024 // 1024} Mio "
                                 "— reduisez avant d'envoyer")
    if not octets.startswith(_PNG_MAGIC):
        raise HTTPException(400, "case : un PNG est attendu (signature "
                                 "absente, l'en-tete ne prouve rien)")
    from PIL import Image as _I
    with _I.open(p) as ref:
        attendu = ref.size
    try:
        with _I.open(io.BytesIO(octets)) as neuve:
            recu = neuve.size
    except Exception:
        raise HTTPException(400, "case : PNG illisible")
    if recu != attendu:
        raise HTTPException(400, f"case : {recu[0]}x{recu[1]} recu, "
                                 f"{attendu[0]}x{attendu[1]} attendu — une "
                                 "case d'une autre taille casserait la grille")
    tmp = p.parent / f"{p.name}.tmp"
    tmp.write_bytes(octets)
    tmp.replace(p)      # Path.replace EST os.replace : meme atomicite
    from app.services.sprite_service import reassemble
    mf = json.loads((_sprite_dir(job) / "manifest.json").read_text("utf-8"))
    ordre = [f["index"] for f in mf["frames"]]
    await asyncio.to_thread(reassemble, _sprite_dir(job), ordre,
                            mf["grid"]["cols"], mf.get("anim"))
    return {"ok": True, "frame": int(i), "octets": len(octets)}
```

**Mesuré :** `routes.py` importe `asyncio` (ligne 2) et `json` (ligne 4) au niveau du module, mais **pas `io`** (`grep -n "^import io" backend/app/api/routes.py` : aucune ligne). Ajouter donc `import io` **local**, en tête de la fonction, comme `assets_squelette`/`assets_sprite` le font déjà pour leurs imports locaux (`routes.py:1385-1386`) :

```python
    import io
```

à placer juste avant `from PIL import Image as _I`.

- [ ] **Étape 4 : vert** — Run: `cd backend && python tests/test_sprite_frame_edit.py` — Expected: `3 passed`. Puis `python tests/test_sprite_editor.py` — `3 passed`.

- [ ] **Étape 5 : le canevas d'édition, pelure d'oignon comprise**

`index.html`, dans `<div id="editor">` après `<div id="editStrip">` :

```html
      <div class="paint">
        <div class="paint-tools">
          <button id="pTool-pen" class="btn tool active" data-tool="pen" title="Crayon (B)">✏</button>
          <button id="pTool-erase" class="btn tool" data-tool="erase" title="Gomme (E)">🧽</button>
          <button id="pTool-pick" class="btn tool" data-tool="pick" title="Pipette (I)">💧</button>
          <input id="pColor" type="color" value="#ff00ff" title="Couleur du crayon">
          <select id="pZoom" title="Zoom du canevas"><option value="1">1×</option><option value="2">2×</option><option value="4" selected>4×</option><option value="8">8×</option></select>
          <label class="fld inline">Pelure <input id="pOnion" type="range" min="0" max="100" value="30"><span id="pOnionVal" class="unit">30%</span></label>
          <button id="pSave" class="btn primary" title="Écrit la case retouchée côté serveur (la feuille et les exports suivent)">💾 Enregistrer l'image</button>
          <button id="pRevert" class="btn ghost" title="Recharger la case depuis le serveur">↺</button>
        </div>
        <div id="paintStage" class="paint-stage bg-checker">
          <canvas id="pOnionCv" class="paint-cv onion"></canvas>
          <canvas id="pCv" class="paint-cv"></canvas>
        </div>
        <div id="paintStatus" class="status hidden"></div>
      </div>
```

`spritelab.css` :

```css
/* ── P5b : retouche pixel + pelure d'oignon ── */
.paint{margin-top:10px;border-top:1px solid var(--stroke);padding-top:8px}
.paint-tools{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:8px}
.paint-tools .tool.active{border-color:var(--cyan);color:var(--cyan)}
.paint-stage{position:relative;display:inline-block;line-height:0;border:1px solid var(--stroke-strong);border-radius:8px;overflow:hidden}
.paint-cv{image-rendering:pixelated;display:block}
.paint-cv.onion{position:absolute;inset:0;pointer-events:none}
```

`spritelab.js`, à la suite de la section P5a :

```js
/* ───────── P5b : retouche pixel + pelure d'oignon ─────────
   Le canevas porte la case À SA TAILLE NATIVE (le zoom est du CSS, jamais
   des pixels en plus) : `canvas.toBlob()` rend donc exactement les octets
   que le serveur attend, et la garde de taille de la route ne peut pas être
   surprise par un zoom. */
const paint = { i: 0, tool: "pen", w: 0, h: 0 };

function paintLoad(i) {
  if (!sheet) return;
  paint.i = i;
  const cv = $("#pCv"), on = $("#pOnionCv");
  const im = new Image();
  im.onload = () => {
    paint.w = im.naturalWidth; paint.h = im.naturalHeight;
    for (const c of [cv, on]) { c.width = paint.w; c.height = paint.h; }
    paintZoom();
    cv.getContext("2d").drawImage(im, 0, 0);
    paintOnion();
  };
  im.src = `/api/assets/sprite/${sheet.short}/frame/${i}?t=${Date.now()}`;
}

function paintOnion() {
  const on = $("#pOnionCv"), ctx = on.getContext("2d");
  ctx.clearRect(0, 0, on.width, on.height);
  const a = (parseInt($("#pOnion").value, 10) || 0) / 100;
  $("#pOnionVal").textContent = Math.round(a * 100) + "%";
  const k = editOrder.indexOf(paint.i);
  const prev = k > 0 ? editOrder[k - 1] : null;
  if (!a || prev == null || !sheet) return;
  const im = new Image();
  im.onload = () => { ctx.globalAlpha = a; ctx.drawImage(im, 0, 0); ctx.globalAlpha = 1; };
  im.src = `/api/assets/sprite/${sheet.short}/frame/${prev}`;
}

function paintZoom() {
  const z = parseInt($("#pZoom").value, 10) || 4;
  for (const c of [$("#pCv"), $("#pOnionCv")])
    { c.style.width = (paint.w * z) + "px"; c.style.height = (paint.h * z) + "px"; }
}

function paintAt(ev) {
  const cv = $("#pCv"), r = cv.getBoundingClientRect();
  const x = Math.floor((ev.clientX - r.left) / r.width * paint.w);
  const y = Math.floor((ev.clientY - r.top) / r.height * paint.h);
  if (x < 0 || y < 0 || x >= paint.w || y >= paint.h) return;
  const ctx = cv.getContext("2d");
  if (paint.tool === "pick") {
    const d = ctx.getImageData(x, y, 1, 1).data;
    $("#pColor").value = "#" + [d[0], d[1], d[2]]
      .map(v => v.toString(16).padStart(2, "0")).join("");
  } else if (paint.tool === "erase") {
    ctx.clearRect(x, y, 1, 1);
  } else {
    ctx.fillStyle = $("#pColor").value;
    ctx.fillRect(x, y, 1, 1);
  }
}

async function paintSave() {
  if (!sheet) return;
  const st = $("#paintStatus");
  try {
    setStatus(st, "Écriture de la case…", false, 25);
    const blob = await new Promise(res => $("#pCv").toBlob(res, "image/png"));
    const r = await fetch(
      `/api/assets/sprite/${sheet.short}/frame/${paint.i}`,
      { method: "PUT", headers: { "Content-Type": "image/png" }, body: blob });
    if (!r.ok) {
      let d = null; try { d = await r.json(); } catch (e) { d = null; }
      throw new Error((d && d.detail) || ("refusé (" + r.status + ")"));
    }
    const m = await api.get("/assets/sprite/" + sheet.short + "/manifest");
    clearStatus(st);
    showResult(sheet.short, m);
    paintLoad(paint.i);
    toast("Case écrite ✓ — feuille, GIF et exports refaits côté serveur");
  } catch (e) {
    setStatus(st, "Échec : " + e.message, true);
  }
}
```

Dans `renderEditor()`, la vignette devient cliquable : `b.closest(".editcell")` gagne un `onclick` qui appelle `paintLoad(src)` et marque `.sel`. Dans `showResult`, après `renderEditor();` : `paintLoad(editOrder[0]);`. Dans `wire()` :

```js
  $$(".paint-tools .tool").forEach(b => b.onclick = () => {
    paint.tool = b.dataset.tool;
    $$(".paint-tools .tool").forEach(x => x.classList.toggle("active", x === b));
  });
  $("#pZoom").onchange = paintZoom;
  $("#pOnion").oninput = paintOnion;
  $("#pSave").onclick = paintSave;
  $("#pRevert").onclick = () => paintLoad(paint.i);
  let down = false;
  $("#pCv").onpointerdown = (e) => { down = true; $("#pCv").setPointerCapture(e.pointerId); paintAt(e); };
  $("#pCv").onpointermove = (e) => { if (down) paintAt(e); };
  $("#pCv").onpointerup = () => { down = false; };
  window.addEventListener("keydown", (e) => {
    if (/^(INPUT|TEXTAREA|SELECT)$/.test((e.target || {}).tagName || "")) return;
    const k = { b: "pen", e: "erase", i: "pick" }[e.key.toLowerCase()];
    if (k) $("#pTool-" + (k === "pen" ? "pen" : k === "erase" ? "erase" : "pick")).click();
  });
```

- [ ] **Étape 6 : commit** — sujet `sprites : T8 - pelure d oignon et retouche pixel` ; corps : les gardes recopiées de `/etabli/vignette` plus la sixième (la taille de l'image doit être celle de la case), le réassemblage en Python après l'écriture pour que la feuille et les cases ne se contredisent jamais, et la faiblesse assumée du `request.body()`.

---

## Lot 2 — différenciant

Le lot 1 amène le Sprite Lab au niveau des outils du métier. Le lot 2 lui donne ce qu'aucun d'eux n'a : **l'identité de la bible**. C'est le seul endroit du plan où le mot « différenciant » se mérite, et il se mérite par une mesure — la planche et le modèle 3D d'une entité **existent déjà** dans le dépôt (`routes.py:5568-5576`, `:5341-5343`), personne ne les a encore reliés aux sprites.

### Tâche 9 — D1a : les 4 vues de la planche de la bible, découpées

**Files :**
- Create: `backend/app/services/sprite_directions.py`
- Modify: `backend/app/api/routes.py` (route `POST /assets/sprite/from-board`, après `/assets/sprite/{job}/reassemble`)
- Test: `backend/tests/test_sprite_directions.py` (créer)

**Pourquoi (mesuré) :** la planche d'un personnage est composée **par code**, pas par diffusion — `board_service.compose_character_board` (`board_service.py:192-228`) pose 4 colonnes `front, left, right, back` sur un fond `_BG = (242, 239, 233)` avec une gouttière `_GUTTER = 28`, les visages (`face_h = 300`) au-dessus des corps (`body_h = 560`). Son layout est donc **déterministe**, et la bible ne garde d'ailleurs que la planche composite : `e.ref_image = board` et `e.face_image = None` (`routes.py:5576-5577`). Découper cette planche est gratuit, reproductible, et rend 4 vues **de la même identité** — ce qu'un prompt neuf ne rend jamais.

**La limite, dite ici et pas cachée :** la planche porte **4** vues, pas 8. Les 4 diagonales (`southwest`, `northwest`, `northeast`, `southeast`) ne sont pas dans le dépôt et demanderaient une génération par diagonale — donc de l'argent, et une référence multiple que `image_providers.build_banana_request` ne sait pas encore passer (`image_providers.py:126` : `image_urls: [image_url]`, **une** seule). C'est **R3 P3**, référencé et non replanifié. T9 livre donc une feuille de 4 directions qui **le dit** dans son manifeste ; T10 livre les 8 par le modèle 3D, quand l'entité en a un.

- [ ] **Étape 1 : banc rouge**

Créer `backend/tests/test_sprite_directions.py` :

```python
"""D1a — la planche de la bible, DECOUPEE : 4 vues, dans l'ordre.

Le fixture ne bricole pas une fausse planche : il appelle
`board_service.compose_character_board`, celui-la meme qui compose les vraies.
On decoupe donc ce que l'application compose — si le layout change un jour, ce
banc rougit, et c'est le but.

Run: python tests/test_sprite_directions.py   (depuis backend/)
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json  # noqa: E402

import pytest  # noqa: E402
from PIL import Image  # noqa: E402

CORPS = {"front": (200, 40, 40), "left": (40, 200, 40),
         "right": (40, 40, 200), "back": (200, 200, 40)}
VISAGES = {"face_front": (120, 20, 20), "face_left": (20, 120, 20),
           "face_right": (20, 20, 120)}


def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def planche():
    from app.config import settings
    from app.services import board_service as BS
    panneaux = {}
    for cle, c in list(CORPS.items()) + list(VISAGES.items()):
        n = f"pan_{cle}.png"
        Image.new("RGB", (300, 400), c).save(settings.images_path / n)
        panneaux[cle] = n
    return BS.compose_character_board(settings.images_path, panneaux)


def test_les_quatre_colonnes_sortent_dans_l_ordre_de_la_planche(planche):
    from app.config import settings
    from app.services import sprite_directions as D
    vues = D.decouper_planche(settings.images_path / planche)
    assert list(vues) == ["front", "left", "right", "back"]
    for cle, im in vues.items():
        assert im.height == 560, (cle, im.size)     # la bande des CORPS
        c = im.convert("RGB").getpixel((im.width // 2, im.height // 2))
        assert c == CORPS[cle], (cle, c)


def test_une_planche_qui_n_est_pas_un_personnage_est_refusee_en_le_disant():
    from app.config import settings
    from app.services import sprite_directions as D
    uni = settings.images_path / "uni.png"
    Image.new("RGB", (400, 300), (242, 239, 233)).save(uni)
    with pytest.raises(ValueError) as e:
        D.decouper_planche(uni)
    assert "aucune bande" in str(e.value)
    deux = settings.images_path / "deux.png"
    im = Image.new("RGB", (400, 300), (242, 239, 233))
    im.paste(Image.new("RGB", (100, 200), (10, 10, 10)), (20, 50))
    im.paste(Image.new("RGB", (100, 200), (10, 10, 10)), (260, 50))
    im.save(deux)
    with pytest.raises(ValueError) as e2:
        D.decouper_planche(deux)
    assert "2 colonnes" in str(e2.value) and "4" in str(e2.value)


def test_la_route_fabrique_une_feuille_de_4_directions_taggees(planche):
    from app.config import settings
    c = _client()
    r = c.post("/api/assets/sprite/from-board",
               json={"board": planche, "cell": {"size": 128},
                     "remove_bg": "chroma", "columns": 4})
    assert r.status_code == 200, r.text
    short = r.json()["job_id"][:8]
    for _ in range(600):                       # le job tourne en tache de fond
        j = c.get("/api/jobs/" + r.json()["job_id"]).json()
        if j["status"] in ("done", "failed"):
            break
    assert j["status"] == "done", j.get("error")
    m = json.loads((settings.outputs_path / "sprites" / short
                    / "manifest.json").read_text("utf-8"))
    assert [t["name"] for t in m["anim"]["tags"]] == \
        ["south", "west", "east", "north"]
    assert all(t["from"] == t["to"] for t in m["anim"]["tags"])
    assert m["source"]["kind"] == "images"
    assert m["source"]["board"] == planche
    assert m["source"]["directions"] == "4/8"   # la limite est ECRITE
    assert len(m["frames"]) == 4


def test_les_gardes_du_nom_de_planche():
    c = _client()
    for corps in ({}, {"board": ""}, {"board": "../board.png"},
                  {"board": "absent.png"}, {"board": "planche.txt"}):
        r = c.post("/api/assets/sprite/from-board", json=corps)
        assert r.status_code == 400, (corps, r.status_code)
    assert c.post("/api/assets/sprite/from-board",
                  json={"entity_id": "inconnu"}).status_code == 404


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
```

- [ ] **Étape 2 : rouge** — Run: `cd backend && python tests/test_sprite_directions.py` — Expected: `4 failed` (`ModuleNotFoundError: ... sprite_directions`).

- [ ] **Étape 3 : écrire `sprite_directions.py`**

```python
"""D1 — les directions d'un sprite depuis la bible (plan sprites, T9/T10).

La planche d'un personnage est composee PAR CODE (`board_service.
compose_character_board`) : 4 colonnes front/left/right/back sur un fond
`_BG`, gouttiere `_GUTTER`, les visages au-dessus des corps. Son layout est
donc deterministe et se DECOUPE, au lieu d'etre regenere — c'est ce qui tient
l'identite, et c'est gratuit.

ON NE RECOPIE PAS LES CONSTANTES DE `board_service` COMME DES NOMBRES : on
IMPORTE `_BG`. Les recopier signifierait qu'un changement de fond la-bas
laisserait ce module vert et faux.

COUT MESURABLE : la detection ne fait PAS une boucle par pixel. Le masque est
calcule d'un coup par `ImageChops.difference` + `point` (C dans Pillow), puis
lu par tranches d'octets — `hauteur + largeur` iterations Python, chacune
deleguant a `bytes.count`.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops

from app.services.board_service import _BG

# L'ordre EST celui des colonnes de `compose_character_board`
# (`order = ["front", "left", "right", "back"]`, board_service.py:198).
COLONNES = ("front", "left", "right", "back")

# Nom de direction facon feuille 8 directions (le « sud » regarde la camera).
# `left` = profil dont le nez pointe vers la GAUCHE du cadre (le prompt du
# panneau le dit : « nose pointing to the left of the frame »), donc ouest.
VERS_HUIT = {"front": "south", "left": "west", "right": "east",
             "back": "north"}
HUIT = ("south", "southwest", "west", "northwest",
        "north", "northeast", "east", "southeast")

_LARGEUR_MIN = 8      # une colonne plus etroite est du bruit de compression
_TOL = 10             # ecart au fond papier tolere, par canal


def _runs(drapeaux: list[bool], mini: int) -> list[tuple[int, int]]:
    """Les passages consecutifs de True, d'au moins `mini` de long."""
    out, debut = [], None
    for i, v in enumerate(drapeaux):
        if v and debut is None:
            debut = i
        elif not v and debut is not None:
            if i - debut >= mini:
                out.append((debut, i))
            debut = None
    if debut is not None and len(drapeaux) - debut >= mini:
        out.append((debut, len(drapeaux)))
    return out


def decouper_planche(chemin: Path, tol: int = _TOL) -> dict[str, Image.Image]:
    """Planche composite -> {front, left, right, back} : les 4 CORPS.

    La bande de contenu la plus BASSE est celle des corps (les visages sont
    au-dessus — `compose_character_board` pose la rangee des visages en
    premier). Les colonnes sont cherchees DANS cette bande, jamais sur toute
    la hauteur : la colonne `back` n'a pas de visage, et un decoupage fait sur
    la hauteur entiere trouverait 4 colonnes en bas et 3 en haut.
    """
    with Image.open(chemin) as brut:
        im = brut.convert("RGB")
    w, h = im.size
    diff = ImageChops.difference(im, Image.new("RGB", (w, h), _BG))
    masque = diff.convert("L").point(lambda v: 255 if v > tol else 0)
    octets = masque.tobytes()

    lignes = [octets[y * w:(y + 1) * w].count(255) > 0 for y in range(h)]
    bandes = _runs(lignes, _LARGEUR_MIN)
    if not bandes:
        raise ValueError("planche : aucune bande de contenu — l'image est "
                         "uniforme, ce n'est pas une planche de personnage")
    y0, y1 = bandes[-1]
    bande = octets[y0 * w:y1 * w]
    cols = [bande[x::w].count(255) > 0 for x in range(w)]
    runs = _runs(cols, _LARGEUR_MIN)
    if len(runs) != len(COLONNES):
        raise ValueError(
            f"planche : {len(runs)} colonnes trouvees, {len(COLONNES)} "
            "attendues (front/left/right/back) — cette image n'est pas une "
            "planche de personnage composee par l'Atelier")
    return {nom: im.crop((a, y0, b, y1))
            for nom, (a, b) in zip(COLONNES, runs)}


def ecrire_vues(images_path: Path, chemin_planche: Path,
                prefixe: str) -> list[str]:
    """Ecrit les 4 vues dans la Library et rend leurs noms, DANS L'ORDRE des
    directions. Les noms portent le prefixe `gen_` : `library_index` les
    classe alors comme des images generees (mesure : `_PREFIXES` de
    `library_index.py:44-51`), et le `noter(..., "sprites")` de l'appelant
    les reclasse sous « Sprite Lab »."""
    vues = decouper_planche(chemin_planche)
    noms = []
    for cle in COLONNES:
        n = f"gen_dir_{prefixe}_{VERS_HUIT[cle]}.png"
        vues[cle].save(images_path / n, format="PNG")
        noms.append(n)
    return noms


def tags_directions(noms_directions: list[str]) -> list[dict]:
    """Un tag d'UNE image par direction : c'est exactement ce qu'est une
    feuille de directions, et cela donne a Godot et Aseprite huit (ou quatre)
    animations nommees au lieu d'une seule anonyme."""
    return [{"name": d, "from": i, "to": i, "direction": "forward"}
            for i, d in enumerate(noms_directions)]
```

- [ ] **Étape 4 : la route**

`routes.py`, après `reassemble_sprite` :

```python
@router.post("/assets/sprite/from-board")
async def sprite_from_board(body: dict, background_tasks: BackgroundTasks):
    """D1a — 4 directions decoupees dans la planche d'une entite de la bible.

    Deux entrees, une seule sortie : `entity_id` (on lit `ref_image`) ou
    `board` (un nom NU d'image de la Library). Les vues decoupees rejoignent
    la Library, puis le job passe par `assets_sprite` — LA meme porte que le
    reste du Sprite Lab, avec la source `images` de T0. Refaire ici la
    machinerie de job donnerait deux chemins a garder d'accord ; il n'y en a
    qu'un.
    """
    from uuid import uuid4 as _u4
    from app.services import sprite_directions as SD
    from app.services.storage import BibleEntity, async_session_factory

    nom_planche = None
    eid = str(body.get("entity_id") or "").strip()
    if eid:
        async with async_session_factory() as s:
            e = await s.get(BibleEntity, eid)
            if e is None:
                raise HTTPException(404, "Entity not found")
            nom_planche, nom_entite = e.ref_image, e.name
        if not nom_planche:
            raise HTTPException(
                400, f"« {nom_entite} » n'a pas de planche : genere-la "
                     "d'abord (Atelier, bouton Planche).")
    else:
        brut = body.get("board")
        nom_planche = Path(str(brut or "")).name
        nom_entite = None
        if not nom_planche or nom_planche != str(brut) \
                or Path(nom_planche).suffix.lower() not in (".png", ".jpg",
                                                            ".jpeg", ".webp"):
            raise HTTPException(400, f"board: nom d'image invalide {brut!r}")
    src = settings.images_path / nom_planche
    if not src.is_file():
        raise HTTPException(400, f"Planche introuvable dans la Library: "
                                 f"{nom_planche!r}")

    prefixe = _u4().hex[:8]
    try:
        noms = await asyncio.to_thread(SD.ecrire_vues, settings.images_path,
                                       src, prefixe)
    except ValueError as e:
        raise HTTPException(400, str(e))
    await LI.noter(noms, "sprites")

    directions = [SD.VERS_HUIT[c] for c in SD.COLONNES]
    corps = dict(body)
    corps.pop("entity_id", None)
    corps.pop("board", None)
    corps["source"] = {"kind": "images", "filenames": noms}
    corps.setdefault("remove_bg", "chroma")   # fond papier uni : cle locale gratuite
    corps.setdefault("columns", 4)
    corps["anim"] = {"tags": SD.tags_directions(directions)}
    corps.setdefault("title", "Sprites · directions · "
                              + (nom_entite or nom_planche))
    corps["_board_meta"] = {"board": nom_planche,
                            "directions": f"{len(directions)}/8"}
    return await assets_sprite(corps, background_tasks)
```

et, dans `generate_sprites` (`sprite_service.py`), `source_info` gagne les deux clés quand elles sont là :

```python
    source_info.update((payload.get("_board_meta") or {}))
```

placé juste après la construction de `source_info`. `_board_meta` porte un souligné : c'est une clé **interne**, posée par une route et lue par le service, jamais documentée à l'utilisateur — et `normalize_opts` l'ignore, donc elle ne peut pas devenir un réglage par accident.

- [ ] **Étape 5 : vert**

Run: `cd backend && python tests/test_sprite_directions.py`
Expected: `4 passed`.
Run: `cd backend && python tests/test_sprite_images_source.py && python tests/test_sprite_anim.py`
Expected: `2 passed` puis `3 passed`.

- [ ] **Étape 6 : l'onglet « Bible »**

`index.html`, `<nav class="tabs" id="srcTabs">` gagne :

```html
        <button class="tab" data-src="bible" title="Découper la planche d'une entité de la bible en 4 directions — gratuit, l'identité vient de la bible">🧬 Bible</button>
```

et, après `<div id="srcUpload">` :

```html
    <div id="srcBible" class="src-body hidden">
      <input id="entSearch" class="search" placeholder="🔎 Filtrer les entités…">
      <div id="entList" class="render-list"><div class="empty-note">Chargement de la bible…</div></div>
      <div class="animer-box">
        <div class="hint">Les 4 vues (sud, ouest, est, nord) sont
          <b>découpées</b> dans la planche : gratuit, et l'identité est celle
          de la bible. Les 4 diagonales demandent une génération par vue —
          voir l'onglet 3D si l'entité a un modèle.</div>
        <button id="bibleCut" class="btn primary" title="Découpe la planche et assemble la feuille (local, gratuit)">🧬 4 directions depuis la planche</button>
        <div id="bibleStatus" class="status hidden"></div>
      </div>
    </div>
```

`spritelab.js` : `switchSrcTab` gagne `$("#srcBible").classList.toggle("hidden", which !== "bible");` et `if (which === "bible") loadEntities();` ; puis :

```js
/* ───────── D1a : la bible ───────── */
let entities = [], selEntity = null;

async function loadEntities() {
  if (entities.length) return;
  try {
    const d = await api.get("/bible/entities");
    entities = (d.entities || d || []).filter(e => e.ref_image);
    renderEntities();
  } catch (e) {
    $("#entList").innerHTML = `<div class="empty-note">Bible indisponible : ${esc(e.message)}</div>`;
  }
}
function renderEntities() {
  const q = ($("#entSearch").value || "").toLowerCase();
  const l = entities.filter(e => !q || (e.name || "").toLowerCase().includes(q));
  $("#entList").innerHTML = l.map(e => `
    <button class="render-row${e.id === selEntity ? " sel" : ""}" data-id="${esc(e.id)}">
      <b>${esc(e.name)}</b> <span class="unit">${esc(e.kind)}</span>
      ${e.model3d_job ? '<span class="unit">· modèle 3D</span>' : ""}
    </button>`).join("")
    || `<div class="empty-note">Aucune entité avec une planche.</div>`;
  $$("#entList .render-row").forEach(b => b.onclick = () => {
    selEntity = b.dataset.id; renderEntities();
  });
}
async function cutFromBible() {
  if (!selEntity) return toast("Choisis d'abord une entité.", true);
  const st = $("#bibleStatus");
  try {
    const s = stripSettings();
    setStatus(st, "Découpe de la planche…", false, 5);
    const d = await api.send("POST", "/assets/sprite/from-board", {
      entity_id: selEntity, cell: { size: $("#cellSize").value === "native"
        ? "native" : parseInt($("#cellSize").value, 10) },
      remove_bg: "chroma", max_frames: s.max,
      pixel: pixelOpts(), post: postOpts(),
    });
    const j = await pollJob(d.job_id, jj => setStatus(st,
      `${jj.current_step || jj.status}…`, false, jj.progress || 5));
    if (j.status !== "done") throw new Error(j.error || "découpe échouée");
    const short = d.job_id.slice(0, 8);
    const m = await api.get("/assets/sprite/" + short + "/manifest");
    clearStatus(st);
    showResult(short, m);
    toast("4 directions depuis la bible ✓ — gratuit");
  } catch (e) {
    setStatus(st, "Échec : " + e.message, true);
  }
}
```

`wire()` : `$("#entSearch").oninput = renderEntities; $("#bibleCut").onclick = cutFromBible;`

- [ ] **Étape 7 : commit** — sujet `sprites : T9 - les 4 directions decoupees dans la planche de la bible` ; corps : le layout de `compose_character_board` est déterministe donc découpable, `_BG` est **importé** et non recopié, la bande des corps est la plus basse (la colonne `back` n'a pas de visage), et la limite 4/8 est **écrite dans le manifeste** au lieu d'être tue.

### Tâche 10 — D1b : les 8 orbites du modèle 3D de l'entité

**Files :**
- Modify: `backend/app/api/routes.py` (route `POST /assets/sprite/capture`)
- Modify: `frontend/spritelab/index.html` (un `<model-viewer>` caché + un bouton), `frontend/spritelab/spritelab.css`, `frontend/spritelab/spritelab.js`
- Test: `backend/tests/test_sprite_capture.py` (créer)

**Pourquoi (mesuré) :** une entité de la bible peut porter un modèle 3D — `BibleEntity.model3d_job` (`storage.py:183`), posé par `routes.py:5342`, et le GLB est servi par `GET /assets/3d/{job}/glb` (`routes.py:1197-1204`). Le dépôt sait déjà capturer un rendu `<model-viewer>` : `mv.toBlob()` dans `cardforge/js/mod-forge3d.js:6304-6323`, décrit comme « API officielle 3.3.3 ». La bibliothèque vendorisée `/assets/model-viewer.min.js` porte bien les deux morceaux nécessaires — **mesuré** : `grep -o '"camera-orbit"'` et `grep -o toBlob` sur `frontend/dist/assets/model-viewer.min.js` renvoient chacun une occurrence. Huit orbites donnent **les 8 directions**, diagonales comprises, sans une génération payante.

**Le navigateur voit et manipule, Python écrit :** la page pose la caméra et capture ; **une seule** route reçoit les octets, les garde, et écrit dans la Library. Aucun assemblage côté client.

- [ ] **Étape 1 : banc rouge**

Créer `backend/tests/test_sprite_capture.py` :

```python
"""D1b — le depot d'une vue capturee : gardes, et la MESURE de l'alpha.

Le banc ne peut pas faire tourner WebGL. Ce qu'il mesure, c'est la porte : le
nom de direction est une allowlist, la taille est bornee avant l'examen du
contenu, la signature PNG est verifiee, et la reponse DIT si l'image recue
porte de la transparence — c'est ce chiffre qui decide du detourage, pas un
souvenir sur le comportement de model-viewer.

Run: python tests/test_sprite_capture.py   (depuis backend/)
"""
import io
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402


def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def _png(mode_alpha: bool) -> bytes:
    im = Image.new("RGBA", (64, 64),
                   (0, 0, 0, 0) if mode_alpha else (18, 18, 22, 255))
    ImageDraw.Draw(im).ellipse([12, 12, 51, 51], fill=(200, 90, 40, 255))
    b = io.BytesIO()
    im.save(b, format="PNG")
    return b.getvalue()


def test_une_vue_transparente_est_ecrite_et_l_alpha_est_ANNONCE():
    from app.config import settings
    r = _client().post("/api/assets/sprite/capture?dir=northwest&prefix=abc12345",
                       content=_png(True),
                       headers={"Content-Type": "image/png"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["filename"] == "gen_dir3d_abc12345_northwest.png"
    assert d["alpha"] is True
    assert (settings.images_path / d["filename"]).is_file()


def test_une_vue_opaque_le_dit_aussi():
    r = _client().post("/api/assets/sprite/capture?dir=south&prefix=abc12345",
                       content=_png(False),
                       headers={"Content-Type": "image/png"})
    assert r.status_code == 200 and r.json()["alpha"] is False


def test_les_gardes_de_la_porte():
    c = _client()
    # la direction est une ALLOWLIST : un nom libre ecrirait un fichier choisi
    # par l'appelant dans la Library
    assert c.post("/api/assets/sprite/capture?dir=../x&prefix=abc12345",
                  content=_png(True)).status_code == 400
    assert c.post("/api/assets/sprite/capture?dir=diagonale&prefix=abc12345",
                  content=_png(True)).status_code == 400
    # le prefixe aussi : 8 hex, rien d'autre
    assert c.post("/api/assets/sprite/capture?dir=south&prefix=../e",
                  content=_png(True)).status_code == 400
    # la taille borne AVANT l'examen du contenu
    assert c.post("/api/assets/sprite/capture?dir=south&prefix=abc12345",
                  content=b"\x89PNG\r\n\x1a\n" + b"\0" * (5 << 20)
                  ).status_code == 413
    # la signature
    assert c.post("/api/assets/sprite/capture?dir=south&prefix=abc12345",
                  content=b"pas un png",
                  headers={"Content-Type": "image/png"}).status_code == 400


def test_la_page_pose_les_huit_orbites_et_ne_fabrique_rien():
    """Banc-miroir sur le frontend : les 8 azimuts sont ecrits en clair, la
    capture passe par toBlob(), et la page n'assemble aucune feuille."""
    racine = pathlib.Path(__file__).resolve().parent.parent.parent
    js = (racine / "frontend" / "spritelab" / "spritelab.js").read_text("utf-8")
    html = (racine / "frontend" / "spritelab"
            / "index.html").read_text("utf-8")
    assert "model-viewer.min.js" in html and "<model-viewer" in html
    # la table des orbites est lue TELLE QUELLE : `str(az) in js` passerait
    # sur n'importe quel chiffre du fichier et ne mordrait rien.
    for nom, az in (("south", 0), ("southwest", 45), ("west", 90),
                    ("northwest", 135), ("north", 180), ("northeast", 225),
                    ("east", 270), ("southeast", 315)):
        assert f'["{nom}", {az}]' in js, (nom, az)
    assert "camera-orbit" in js and "toBlob" in js
    assert "/assets/sprite/capture" in js


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
```

- [ ] **Étape 2 : rouge** — Run: `cd backend && python tests/test_sprite_capture.py` — Expected: `4 failed` (`assert 404 == 200`).

- [ ] **Étape 3 : la route**

`routes.py`, après `sprite_from_board` :

```python
# 5 Mio : une capture `<model-viewer>` couvre le viewport, pas une case de
# 128 px — la borne de la retouche (2 Mio) serait trop serree ici, et une
# borne trop serree se contourne en degradant l'image, ce qui est pire.
_SPRITE_CAPTURE_MAX = 5 * 1024 * 1024
_PREFIXE_HEX = re.compile(r"^[0-9a-f]{8}$")


@router.post("/assets/sprite/capture")
async def sprite_capture(request: Request, dir: str, prefix: str):
    """D1b — depose UNE vue capturee depuis `<model-viewer>` dans la Library.

    LE NAVIGATEUR VOIT ET MANIPULE, PYTHON ECRIT : la page pose la camera sur
    l'un des 8 azimuts et appelle `mv.toBlob()` (meme geste que
    `cardforge/js/mod-forge3d.js:6304-6323`) ; le fichier, lui, nait ICI.

    LES GARDES :
      1. `dir` est une ALLOWLIST des 8 noms (400). Un nom libre laisserait
         l'appelant choisir le nom d'un fichier de la Library — et un nom qui
         survit a `Path(...).name` (`..`) a deja coute un defaut dans ce
         depot (`_etabli_vignette_cible`) ;
      2. `prefix` est 8 chiffres hexadecimaux, rien d'autre (400) ;
      3. la TAILLE est bornee avant tout examen du contenu (413) ;
      4. la SIGNATURE PNG (400) : `Content-Type` ne prouve rien.

    LA MESURE QUI COMPTE : la reponse porte `alpha`, vrai quand l'image recue
    a des pixels reellement transparents. La page s'en sert pour choisir le
    detourage — la transparence par defaut de `toBlob()` n'est PAS une chose
    dont on se souvient, c'est une chose que l'on mesure ici, sur l'octet.
    """
    import io
    from app.services import sprite_directions as SD

    if dir not in SD.HUIT:
        raise HTTPException(400, f"dir: {dir!r} — l'une de "
                                 f"{', '.join(SD.HUIT)}")
    if not _PREFIXE_HEX.match(prefix or ""):
        raise HTTPException(400, "prefix: 8 chiffres hexadecimaux attendus")
    octets = await request.body()
    if len(octets) > _SPRITE_CAPTURE_MAX:
        raise HTTPException(413, f"capture : {len(octets)} octets, la borne "
                                 f"est a {_SPRITE_CAPTURE_MAX // 1024 // 1024}"
                                 " Mio")
    if not octets.startswith(_PNG_MAGIC):
        raise HTTPException(400, "capture : un PNG est attendu (signature "
                                 "absente, l'en-tete ne prouve rien)")
    from PIL import Image as _I
    try:
        with _I.open(io.BytesIO(octets)) as im:
            rgba = im.convert("RGBA")
            mini, _maxi = rgba.getchannel("A").getextrema()
    except Exception:
        raise HTTPException(400, "capture : PNG illisible")
    nom = f"gen_dir3d_{prefix}_{dir}.png"
    dest = settings.images_path / nom
    tmp = dest.parent / f"{dest.name}.tmp"
    tmp.write_bytes(octets)
    tmp.replace(dest)
    await LI.noter([nom], "sprites")
    return {"filename": nom, "alpha": mini == 0, "octets": len(octets)}
```

**Mesuré :** `re` est bien importé au niveau du module (`routes.py:6`), donc `_PREFIXE_HEX = re.compile(...)` peut vivre au module, à côté de `_SPRITE_CAPTURE_MAX`. (`io`, lui, ne l'est pas — voir T8 : d'où l'`import io` local en tête de la fonction.)

- [ ] **Étape 4 : la page — huit orbites, huit captures**

`index.html`, dans `<head>` :

```html
<script type="module" src="/assets/model-viewer.min.js"></script>
```

et, dans `<div id="srcBible">`, sous le bouton `bibleCut` :

```html
        <button id="bible3d" class="btn primary" title="Rend le modèle 3D de l'entité sous 8 angles et en fait une feuille de 8 directions — gratuit, local">🧊 8 directions depuis le modèle 3D</button>
        <div class="mv-hold"><model-viewer id="mv3d" camera-controls="false" interaction-prompt="none" disable-zoom shadow-intensity="0"></model-viewer></div>
```

`spritelab.css` :

```css
/* ── D1b : le viewport de capture ── */
.mv-hold{width:256px;height:256px;margin-top:8px;border:1px solid var(--stroke);border-radius:8px;overflow:hidden;background:transparent}
.mv-hold model-viewer{width:100%;height:100%;--poster-color:transparent}
```

Le viewport est **visible et petit** — pas caché : un `<model-viewer>` en `display:none` ne rend rien, donc `toBlob()` rendrait une image vide. C'est le piège de ce mécanisme, et il est dit ici.

`spritelab.js` :

```js
/* ───────── D1b : 8 orbites -> 8 directions ─────────
   Un azimut par direction, élévation fixe : « sud » regarde la caméra, et
   l'on tourne dans le sens horaire vu de dessus — le même ordre que
   sprite_directions.HUIT côté Python, sinon les tags mentiraient. */
const ORBITES = [["south", 0], ["southwest", 45], ["west", 90],
                 ["northwest", 135], ["north", 180], ["northeast", 225],
                 ["east", 270], ["southeast", 315]];

function hex8() {
  return Array.from({ length: 8 },
    () => "0123456789abcdef"[Math.floor(Math.random() * 16)]).join("");
}

async function captureOrbites() {
  const ent = entities.find(e => e.id === selEntity);
  if (!ent) return toast("Choisis d'abord une entité.", true);
  if (!ent.model3d_job)
    return toast("Cette entité n'a pas de modèle 3D — utilise la planche.", true);
  const st = $("#bibleStatus"), mv = $("#mv3d");
  const prefix = hex8();
  try {
    setStatus(st, "Chargement du modèle…", false, 5);
    mv.setAttribute("src", `/api/assets/3d/${ent.model3d_job}/glb`);
    await new Promise((ok, ko) => {
      mv.addEventListener("load", ok, { once: true });
      mv.addEventListener("error", () => ko(new Error("GLB illisible")), { once: true });
      setTimeout(() => ko(new Error("délai dépassé au chargement du GLB")), 60000);
    });
    const noms = [], sansAlpha = [];
    for (let k = 0; k < ORBITES.length; k++) {
      const [nom, az] = ORBITES[k];
      mv.setAttribute("camera-orbit", `${az}deg 78deg auto`);
      mv.jumpCameraToGoal && mv.jumpCameraToGoal();
      await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
      const blob = await mv.toBlob({ idealAspect: false });
      const r = await fetch(
        `/api/assets/sprite/capture?dir=${nom}&prefix=${prefix}`,
        { method: "POST", headers: { "Content-Type": "image/png" }, body: blob });
      if (!r.ok) {
        let d = null; try { d = await r.json(); } catch (e) { d = null; }
        throw new Error((d && d.detail) || ("vue " + nom + " refusée"));
      }
      const d = await r.json();
      noms.push(d.filename);
      if (!d.alpha) sansAlpha.push(nom);
      setStatus(st, `Capture ${k + 1}/8 (${nom})…`, false, 5 + k * 10);
    }
    // LA MESURE decide du detourage : si le rendu est deja transparent, on ne
    // touche a rien ; s'il est opaque, la cle chroma locale (gratuite) passe.
    const body = {
      source: { kind: "images", filenames: noms },
      remove_bg: sansAlpha.length ? "chroma" : "none",
      columns: 4,
      cell: { size: $("#cellSize").value === "native" ? "native"
                : parseInt($("#cellSize").value, 10) },
      anim: { tags: ORBITES.map(([n], i) =>
        ({ name: n, from: i, to: i, direction: "forward" })) },
      title: "Sprites · 8 directions · " + (ent.name || ""),
    };
    const px = pixelOpts(); if (px) body.pixel = px;
    const po = postOpts(); if (po) body.post = po;
    setStatus(st, "Assemblage de la feuille…", false, 88);
    const d = await api.send("POST", "/assets/sprite", body);
    const j = await pollJob(d.job_id, jj => setStatus(st,
      `${jj.current_step || jj.status}…`, false, jj.progress || 90));
    if (j.status !== "done") throw new Error(j.error || "assemblage échoué");
    const short = d.job_id.slice(0, 8);
    const m = await api.get("/assets/sprite/" + short + "/manifest");
    clearStatus(st);
    showResult(short, m);
    toast(sansAlpha.length
      ? "8 directions ✓ — rendu opaque, clé chroma appliquée"
      : "8 directions ✓ — rendu déjà détouré");
  } catch (e) {
    setStatus(st, "Échec : " + e.message, true);
  }
}
```

`wire()` : `$("#bible3d").onclick = captureOrbites;`

- [ ] **Étape 5 : vert, puis la vérification humaine**

Run: `cd backend && python tests/test_sprite_capture.py`
Expected: `4 passed`.

Vérification **humaine**, nommée : ouvrir `/spritelab/`, onglet Bible, choisir une entité qui a un modèle 3D, cliquer « 8 directions depuis le modèle 3D ». Constater 8 captures et une feuille de 8 tags. **Noter dans le message de commit ce que la route a répondu pour `alpha`** — c'est la mesure qui manquait aux références (« la transparence par défaut de `<model-viewer>.toBlob()` : de mémoire, non vérifiée »).

- [ ] **Étape 6 : commit** — sujet `sprites : T10 - huit orbites du modele 3D donnent huit directions` ; corps : la bibliothèque vendorisée porte `camera-orbit` et `toBlob` (mesuré au grep), un `<model-viewer>` en `display:none` ne rend rien donc le viewport reste visible et petit, l'allowlist des 8 noms garde la porte, et `alpha` est **mesuré** puis reporté ici.

### Tâche 11 — D2 : prompt → image → pipeline pixel local

**Files :**
- Modify: `frontend/spritelab/index.html` (onglet + panneau), `frontend/spritelab/spritelab.css`, `frontend/spritelab/spritelab.js` (`sourceBody`, onglet Prompt)
- Test: `backend/tests/test_sprite_prompt.py` (créer — banc-miroir sur le frontend + la garde de source)

**Pourquoi (mesuré) : zéro backend.** Tout existe déjà : `POST /api/images/generate` accepte un `source` et l'indexe (`routes.py:4424-4438`), `LI.SOURCES` connaît `"sprites"` (`library_index.py:32`), `/api/persona` rend `vibe_keywords` et `brand_colors` (`routes.py:108-110`, `personas/deepotus.json`), et T0 a donné au Sprite Lab une source `images`. D2 est donc **un écran**, et son coût est celui d'une image générée.

**La doctrine, tenue :** le prompt construit ici ne contient **jamais** un nom d'artiste ; le style est porté par des descripteurs (palette, taille de grille, contour) et par les mots-clés de la persona. C'est la règle du dépôt (`style_vitrail.epurer_noms`, appelée par `_generate_image_core` quand un `style` est passé) — ici on ne passe pas de `style`, donc c'est **l'écran** qui la tient, et le banc la vérifie.

- [ ] **Étape 1 : banc rouge**

Créer `backend/tests/test_sprite_prompt.py` :

```python
"""D2 — l'onglet Prompt : un banc-miroir sur le frontend, et la garde de
source cote Python.

Ce que le banc peut prouver sans reseau : le suffixe pixel-art est ecrit en
clair, aucun nom d'artiste n'est injecte, la source envoyee est bien
`images`, et `resolve_images` refuse un nom qui sort de la Library.

Run: python tests/test_sprite_prompt.py   (depuis backend/)
"""
import os
import pathlib
import re
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
JS = RACINE / "frontend" / "spritelab" / "spritelab.js"
HTML = RACINE / "frontend" / "spritelab" / "index.html"

# Les generateurs refusent ou pastichent un nom d'artiste : la doctrine du
# depot est de porter le style par des DESCRIPTEURS. Liste volontairement
# courte et explicite — elle documente l'interdit autant qu'elle le teste.
NOMS_INTERDITS = ("wyspianski", "walkuski", "mucha", "moebius", "miyazaki",
                  "greg rutkowski", "artstation")


def test_le_suffixe_pixel_art_est_un_descripteur_et_pas_un_nom():
    js = JS.read_text("utf-8")
    assert "PIXEL_SUFFIX" in js
    m = re.search(r'const PIXEL_SUFFIX = "([^"]+)"', js)
    assert m, "PIXEL_SUFFIX doit etre une constante litterale, lisible ici"
    suffixe = m.group(1).lower()
    for mot in ("pixel art", "sprite", "solid", "background"):
        assert mot in suffixe, mot
    for interdit in NOMS_INTERDITS:
        assert interdit not in js.lower(), interdit


def test_l_onglet_prompt_envoie_la_source_images_et_signe_sprites():
    js = JS.read_text("utf-8")
    html = HTML.read_text("utf-8")
    assert 'data-src="prompt"' in html
    assert '"/images/generate"' in js
    assert 'source: "sprites"' in js
    # la page construit le corps de source par UNE fonction, pas trois fois
    assert js.count("function sourceBody(") == 1
    assert 'kind: "images"' in js


def test_resolve_images_refuse_un_nom_qui_sort_de_la_library():
    from app.services import sprite_service as S
    for mauvais in ({"filenames": ["../x.png"]},
                    {"filenames": ["sous/dossier.png"]},
                    {"filenames": ["absent.png"]},
                    {"filenames": ["note.txt"]}):
        with pytest.raises(ValueError):
            S.resolve_images(mauvais)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
```

- [ ] **Étape 2 : rouge** — Run: `cd backend && python tests/test_sprite_prompt.py` — Expected: `2 failed` (les deux bancs-miroirs ; `resolve_images` passe déjà, T0 l'a écrite).

- [ ] **Étape 3 : la fonction `sourceBody`, dette de T0 payée ici**

`spritelab.js` construit aujourd'hui le corps de source à **deux** endroits — `extract()` et `generate()` — chacun en dur sur `{ kind: source.kind, job_id: source.job_id }` (`spritelab.js:325-326`). Avec la source `images` de T0, ce corps a deux formes. Une seule fonction :

```js
/* T0 + D2 : la source a deux formes (un job vidéo, ou des images de la
   Library). UNE fonction les rend, appelée par extract() et generate() —
   deux copies dériveraient, et c'est le genre de dérive qui ne se voit
   qu'une fois la génération payée. */
function sourceBody() {
  if (!source) return null;
  return source.kind === "images"
    ? { kind: "images", filenames: source.filenames }
    : { kind: source.kind, job_id: source.job_id };
}
```

et les deux sites d'appel deviennent `source: sourceBody(),`.

- [ ] **Étape 4 : l'onglet**

`index.html`, `<nav class="tabs">` gagne :

```html
        <button class="tab" data-src="prompt" title="Décrire un sprite, générer l'image, la pixeliser en local">✍ Prompt</button>
```

et le panneau, après `<div id="srcBible">` :

```html
    <div id="srcPrompt" class="src-body hidden">
      <div class="animer-box">
        <label class="fld">Sujet du sprite
          <textarea id="pmPrompt" rows="3" placeholder="Ex : a small deep-sea octopus mascot walking, side view, full body"></textarea>
        </label>
        <div id="pmChips" class="chips"></div>
        <div class="animer-row">
          <label class="fld">Images
            <select id="pmN"><option>1</option><option selected>2</option><option>3</option><option>4</option></select>
          </label>
          <label class="fld">Cadre
            <select id="pmSize"><option value="square_hd" selected>Carré</option><option value="portrait_4_3">Portrait</option><option value="landscape_4_3">Paysage</option></select>
          </label>
        </div>
        <div class="hint">Style porté par des <b>descripteurs</b> (palette,
          grille, contour), jamais par un nom d'artiste — les générateurs
          refusent ou pastichent. Le pipeline pixel local fait le reste :
          coche « Pixel-art » à droite.</div>
        <button id="pmGen" class="btn primary" title="Génère les images puis les charge comme source (coût = une image par vue)">✍ Générer les images</button>
        <div id="pmStatus" class="status hidden"></div>
      </div>
    </div>
```

`spritelab.css` :

```css
/* ── D2 : chips de persona ── */
.chips{display:flex;flex-wrap:wrap;gap:5px;margin:6px 0}
.chip{border:1px solid var(--stroke-strong);border-radius:99px;padding:2px 9px;font-size:11.5px;color:var(--ink-soft);background:var(--bg-base);cursor:pointer}
.chip.on{border-color:var(--cyan);color:var(--cyan)}
.chip.col{font-family:var(--f-mono)}
```

`spritelab.js` :

```js
/* ───────── D2 : prompt -> image -> pipeline pixel local ─────────
   Zéro moteur nouveau : /images/generate existe, LI.SOURCES connaît
   « sprites », et T0 a donné au Sprite Lab une source `images`. */
const PIXEL_SUFFIX = "pixel art sprite, chunky readable pixels, limited flat palette, crisp 1px dark outline, no anti-aliasing, plain solid green background, full body in frame, centered, no text, no watermark";
let persona = null, chipsOn = new Set();

async function loadPersona() {
  if (persona) return;
  try { persona = await api.get("/persona"); } catch (e) { persona = {}; }
  const mots = (persona.vibe_keywords || []).slice(0, 12);
  const cols = Object.values(persona.brand_colors || {});
  $("#pmChips").innerHTML =
    mots.map(m => `<span class="chip" data-v="${esc(m)}">${esc(m)}</span>`).join("")
    + cols.map(c => `<span class="chip col" data-v="palette accent ${esc(c)}">${esc(c)}</span>`).join("");
  $$("#pmChips .chip").forEach(el => el.onclick = () => {
    const v = el.dataset.v;
    if (chipsOn.has(v)) chipsOn.delete(v); else chipsOn.add(v);
    el.classList.toggle("on", chipsOn.has(v));
  });
}

function promptFinal() {
  const sujet = ($("#pmPrompt").value || "").trim();
  return [sujet, ...chipsOn, PIXEL_SUFFIX].filter(Boolean).join(", ");
}

async function generateFromPrompt() {
  const sujet = ($("#pmPrompt").value || "").trim();
  if (!sujet) return toast("Décris d'abord le sprite.", true);
  const st = $("#pmStatus");
  try {
    setStatus(st, "Génération des images…", false, 10);
    const d = await api.send("POST", "/images/generate", {
      prompt: promptFinal(),
      n: parseInt($("#pmN").value, 10) || 2,
      size: $("#pmSize").value,
      source: "sprites",
    });
    const noms = (d && d.images) || [];
    if (!noms.length) throw new Error("aucune image rendue");
    clearStatus(st);
    libImages = [];                     // la Library a changé
    loadImages();
    setSource({ kind: "images", filenames: noms,
                label: noms.length + " image(s) du prompt" });
    toast(noms.length + " image(s) générées ✓ — coche « Pixel-art » puis génère le sheet");
  } catch (e) {
    setStatus(st, "Échec : " + e.message, true);
  }
}
```

`switchSrcTab` gagne `$("#srcPrompt").classList.toggle("hidden", which !== "prompt");` et `if (which === "prompt") loadPersona();` ; `wire()` gagne `$("#pmGen").onclick = generateFromPrompt;`.

- [ ] **Étape 5 : vert**

Run: `cd backend && python tests/test_sprite_prompt.py`
Expected: `3 passed`.
Run: `cd backend && python tests/test_sprite_images_source.py`
Expected: `2 passed` (la source `images` sert maintenant trois chemins : T9, T10, T11).

- [ ] **Étape 6 : commit** — sujet `sprites : T11 - du prompt a la feuille sans moteur nouveau` ; corps : zéro backend (tout existait : `/images/generate` + `source`, `LI.SOURCES["sprites"]`, la source `images` de T0), la dette de T0 payée par `sourceBody()`, et le style porté par des descripteurs — jamais par un nom d'artiste, ce qu'un banc vérifie.

### Tâche 12 — D3 : découpe en pièces, os, export Spine JSON

**Files :**
- Create: `backend/app/services/sprite_skeleton.py`
- Modify: `backend/app/services/sprite_service.py:363-377` (`build_zip_bytes`)
- Modify: `backend/app/api/routes.py` (route `POST /assets/sprite/{job}/skeleton`, route `GET .../skeleton`)
- Modify: `frontend/spritelab/index.html`, `frontend/spritelab/spritelab.css`, `frontend/spritelab/spritelab.js` (mode « Squelette » du canevas de T8)
- Test: `backend/tests/test_sprite_skeleton.py` (créer)

**Pourquoi (mesuré) :** R10a réponse 3 demande « les deux selon l'asset » — images-clés pour les effets, **squelette 2D pour les personnages** — et la réponse 8 place l'éditeur sur `/spritelab`. Le squelette est ce que le lot 1 ne donne pas : une feuille d'images-clés se rejoue, elle ne se **repose** pas. La découpe part de la case retouchable de T8 et des cases déjà écrites par `_assemble`.

**Le périmètre, figé :** D3 livre un **rig** — pièces découpées, os, slots, skin — et **pas** d'animation. R10a demande « découpe en pièces, os et export Spine/DragonBones » : dériver des timelines depuis une feuille d'images-clés n'y est pas, et serait une invention. Les tags de la feuille produisent des **animations vides mais nommées**, pour que le fichier s'ouvre avec les bons noms dans Spine. Format écrit : **Spine JSON seulement** (DragonBones est « de mémoire, non vérifié » dans R10a et n'est donc pas un argument).

- [ ] **Étape 1 : relire le format Spine, et corriger le souvenir**

Relire avec **exactement** cette commande (outil `WebFetch`) :

- url : `https://esotericsoftware.com/spine-json-format`
- prompt : `List the exact top-level JSON keys of a Spine skeleton export, then the required/optional fields of: the "skeleton" object; each entry of "bones"; each entry of "slots"; the "skins" structure (including how attachments are keyed) and the fields of a "region" attachment; and the "animations" structure for bone rotate/translate timelines (field names for time, angle, x, y). State defaults where given.`

**Mesuré le 03/09/2026, et c'est une correction, pas une confirmation :** `skins` est un **TABLEAU** de `{name, attachments}`, où `attachments` est `slot → nom d'attachement → objet`. La forme « `skins.default.<slot>.<att>` » (carte de cartes) est celle de Spine **3.7** — et c'est exactement ce que la mémoire produit. Le reste : `skeleton` tout optionnel (`hash, spine, x, y, width, height, images, audio, fps`) ; `bones` requiert `name`, défauts `length=0, x=y=0, rotation=0, scaleX=scaleY=1` ; `slots` requiert `name` et `bone` ; l'attachement `region` porte `type, path, name, x, y, scaleX, scaleY, rotation, width, height, color` ; la clé de rotation d'une timeline s'appelle `angle`. **Version visée : Spine 3.8** (`"spine": "3.8.99"`) — celle où `skins` est un tableau **et** où la rotation s'appelle `angle`.

- [ ] **Étape 2 : banc rouge**

Créer `backend/tests/test_sprite_skeleton.py` :

```python
"""D3 — le rig Spine, LU sur le disque : squelette JSON et pieces PNG.

Run: python tests/test_sprite_skeleton.py   (depuis backend/)
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio  # noqa: E402
import json  # noqa: E402

import pytest  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

TETE = (200, 40, 40, 255)
CORPS = (40, 90, 200, 255)

RIG = {
    "frame": 0,
    "bones": [{"name": "torse", "x": 64, "y": 90, "length": 40},
              {"name": "cou", "parent": "torse", "x": 64, "y": 40,
               "length": 20, "rotation": 90}],
    "pieces": [{"name": "corps", "bone": "torse", "x": 44, "y": 60,
                "w": 40, "h": 50},
               {"name": "tete", "bone": "cou", "x": 48, "y": 16,
                "w": 32, "h": 32}],
}


def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


@pytest.fixture(scope="module")
def dossier():
    from app.config import settings
    from app.services import sprite_service as S
    noms = []
    for i in range(2):
        n = f"sk{i}.png"
        im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle([48, 16, 79, 47], fill=TETE)      # la tete
        d.rectangle([44, 60, 83, 109], fill=CORPS)    # le corps
        im.save(settings.images_path / n)
        noms.append(n)
    asyncio.run(S.generate_sprites(
        {"source": {"kind": "images", "filenames": noms},
         "cell": {"size": "native"}, "columns": 2,
         "anim": {"tags": [{"name": "idle", "from": 0, "to": 1}]}}, "j-sk"))
    return settings.outputs_path / "sprites" / "j-sk"


def test_le_squelette_a_la_forme_spine_3_8(dossier):
    r = _client().post("/api/assets/sprite/j-sk/skeleton", json=RIG)
    assert r.status_code == 200, r.text
    sk = json.loads((dossier / "spine" / "skeleton.json").read_text("utf-8"))
    assert sk["skeleton"]["spine"] == "3.8.99"
    assert sk["skeleton"]["width"] == 128 and sk["skeleton"]["height"] == 128
    assert sk["skeleton"]["images"] == "./images/"
    # un os racine est TOUJOURS emis, et les os de l'utilisateur s'y accrochent
    assert [b["name"] for b in sk["bones"]] == ["root", "torse", "cou"]
    assert sk["bones"][1]["parent"] == "root"
    assert sk["bones"][2]["parent"] == "torse"
    # y REMONTE en Spine : l'os torse est a 90 px du HAUT -> 128 - 90 = 38
    assert sk["bones"][1]["y"] == 38
    assert sk["bones"][2]["rotation"] == 90
    assert [s["name"] for s in sk["slots"]] == ["corps", "tete"]
    assert sk["slots"][0]["bone"] == "torse"
    # skins est un TABLEAU (3.8), pas une carte de cartes (3.7)
    assert isinstance(sk["skins"], list)
    assert sk["skins"][0]["name"] == "default"
    att = sk["skins"][0]["attachments"]["tete"]["tete"]
    assert att["width"] == 32 and att["height"] == 32
    # les tags donnent des animations NOMMEES (vides : D3 ne derive pas de
    # timeline depuis une feuille d'images-cles, et le dit)
    assert list(sk["animations"]) == ["idle"] and sk["animations"]["idle"] == {}


def test_les_pieces_sont_des_PNG_rognes_aux_pixels_de_la_case(dossier):
    img = dossier / "spine" / "images"
    with Image.open(img / "tete.png") as t:
        assert t.size == (32, 32)
        assert t.convert("RGBA").getpixel((16, 16)) == TETE
    with Image.open(img / "corps.png") as c:
        assert c.size == (40, 50)
        assert c.convert("RGBA").getpixel((20, 25)) == CORPS


def test_les_gardes_du_rig(dossier):
    c = _client()
    def mauvais(**over):
        r = dict(RIG)
        r.update(over)
        return c.post("/api/assets/sprite/j-sk/skeleton", json=r).status_code
    assert mauvais(bones=[]) == 400
    assert mauvais(pieces=[]) == 400
    # parent inconnu
    assert mauvais(bones=[{"name": "a", "parent": "zzz", "x": 1, "y": 1}]) == 400
    # parent qui NE PRECEDE PAS : c'est ce qui interdit les cycles
    assert mauvais(bones=[{"name": "a", "parent": "b", "x": 1, "y": 1},
                          {"name": "b", "x": 1, "y": 1}]) == 400
    # nom en double
    assert mauvais(pieces=[{"name": "x", "bone": "torse", "x": 0, "y": 0,
                            "w": 4, "h": 4},
                           {"name": "x", "bone": "torse", "x": 8, "y": 8,
                            "w": 4, "h": 4}]) == 400
    # nom sale (il devient un NOM DE FICHIER)
    assert mauvais(pieces=[{"name": "../x", "bone": "torse", "x": 0, "y": 0,
                            "w": 4, "h": 4}]) == 400
    # boite hors de la case
    assert mauvais(pieces=[{"name": "x", "bone": "torse", "x": 120, "y": 0,
                            "w": 40, "h": 4}]) == 400
    # os inconnu
    assert mauvais(pieces=[{"name": "x", "bone": "zzz", "x": 0, "y": 0,
                            "w": 4, "h": 4}]) == 400
    # image inexistante
    assert c.post("/api/assets/sprite/j-sk/skeleton",
                  json=dict(RIG, frame=9)).status_code == 400
    assert c.post("/api/assets/sprite/j-absent/skeleton",
                  json=RIG).status_code == 404


def test_le_zip_emporte_le_dossier_spine(dossier):
    import io
    import zipfile
    from app.services.sprite_service import build_zip_bytes
    with zipfile.ZipFile(io.BytesIO(build_zip_bytes(dossier))) as z:
        noms = set(z.namelist())
    assert "spine/skeleton.json" in noms
    assert "spine/images/tete.png" in noms
    assert "spine/images/corps.png" in noms


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
```

- [ ] **Étape 3 : rouge** — Run: `cd backend && python tests/test_sprite_skeleton.py` — Expected: `4 failed` (`assert 404 == 200`).

- [ ] **Étape 4 : écrire `sprite_skeleton.py`**

```python
"""D3 — decoupe en pieces, os, et export Spine JSON (plan sprites, T12).

PERIMETRE FIGE : ce module produit un RIG — pieces, os, slots, skin — et PAS
d'animation. Deriver des timelines depuis une feuille d'images-cles n'est pas
ce que R10a demande (« decoupe en pieces, os et export »), et l'inventer
donnerait un fichier qui a l'air juste et bouge faux. Les tags de la feuille
deviennent des animations NOMMEES et VIDES, pour que le fichier s'ouvre dans
Spine avec les bons noms.

FORMAT : Spine 3.8 JSON, relu le 03/09/2026. La correction qui compte :
`skins` est un TABLEAU de {name, attachments} — la carte de cartes est la
forme 3.7, et c'est ce que la memoire produit.

LES DEUX REPERES, et c'est la seule vraie difficulte :
  - le client parle en pixels de la case, origine EN HAUT A GAUCHE, y vers
    le BAS (c'est ce que voit un canevas) ;
  - Spine place son origine en (0,0) — ici le coin BAS-GAUCHE de la case —
    et fait REMONTER y.
La conversion se fait UNE FOIS, a la porte (`_vers_spine`). Deux conversions
a deux endroits, c'est un sprite a l'envers dont personne ne trouve la cause.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from PIL import Image

SPINE = "3.8.99"
_NOM = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
MAX_OS = 24
MAX_PIECES = 24


def _vers_spine(y_client: float, hauteur: int) -> float:
    """y du client (vers le bas) -> y de Spine (vers le haut). LA conversion,
    et il n'y en a qu'une dans ce module."""
    return hauteur - y_client


def _num(bloc: dict, cle: str, defaut, lo, hi, quoi: str):
    brut = bloc.get(cle, defaut)
    try:
        v = float(brut)
    except (TypeError, ValueError):
        raise ValueError(f"{quoi}: {cle} must be a number ({lo}..{hi})")
    if not lo <= v <= hi:
        raise ValueError(f"{quoi}: {cle}={v} outside {lo}..{hi}")
    return v


def normalize_rig(spec: dict, w: int, h: int) -> dict:
    """{bones, pieces} normalise, en coordonnees CLIENT. ValueError lisible."""
    if not isinstance(spec, dict):
        raise ValueError("rig must be an object {bones, pieces}")

    os_bruts = spec.get("bones") or []
    if not isinstance(os_bruts, (list, tuple)) or not os_bruts:
        raise ValueError("rig.bones must be a non-empty list")
    if len(os_bruts) > MAX_OS:
        raise ValueError(f"rig.bones: {MAX_OS} bones at most")
    os_, vus = [], {"root"}
    for b in os_bruts:
        if not isinstance(b, dict):
            raise ValueError("rig.bones: each bone is an object {name, x, y}")
        nom = str(b.get("name") or "")
        if not _NOM.match(nom):
            raise ValueError(f"bone name {nom!r}: 1-32 chars, letters, "
                             "digits, _ or -, starting with a letter or digit")
        if nom in vus:
            raise ValueError(f"bone name {nom!r} appears twice (or is 'root')")
        parent = str(b.get("parent") or "root")
        # LE PARENT DOIT PRECEDER : c'est ce qui interdit les cycles sans
        # ecrire de parcours de graphe, et Spine lit les os dans l'ordre.
        if parent not in vus:
            raise ValueError(f"bone {nom!r}: parent {parent!r} is unknown or "
                             "declared after this bone")
        vus.add(nom)
        os_.append({"name": nom, "parent": parent,
                    "x": _num(b, "x", 0, 0, w, f"bone {nom!r}"),
                    "y": _num(b, "y", 0, 0, h, f"bone {nom!r}"),
                    "length": _num(b, "length", 0, 0, max(w, h),
                                   f"bone {nom!r}"),
                    "rotation": _num(b, "rotation", 0, -360, 360,
                                     f"bone {nom!r}")})

    p_bruts = spec.get("pieces") or []
    if not isinstance(p_bruts, (list, tuple)) or not p_bruts:
        raise ValueError("rig.pieces must be a non-empty list")
    if len(p_bruts) > MAX_PIECES:
        raise ValueError(f"rig.pieces: {MAX_PIECES} pieces at most")
    pieces, vues = [], set()
    for p in p_bruts:
        if not isinstance(p, dict):
            raise ValueError("rig.pieces: each piece is an object "
                             "{name, bone, x, y, w, h}")
        nom = str(p.get("name") or "")
        # LE NOM DEVIENT UN NOM DE FICHIER (spine/images/<nom>.png) : la meme
        # regexp qu'ailleurs ne suffirait pas si elle laissait passer un `/`.
        if not _NOM.match(nom):
            raise ValueError(f"piece name {nom!r}: 1-32 chars, letters, "
                             "digits, _ or - (it becomes a file name)")
        if nom in vues:
            raise ValueError(f"piece name {nom!r} appears twice")
        vues.add(nom)
        os_nom = str(p.get("bone") or "")
        if os_nom not in vus:
            raise ValueError(f"piece {nom!r}: bone {os_nom!r} is unknown")
        x = int(_num(p, "x", 0, 0, w - 1, f"piece {nom!r}"))
        y = int(_num(p, "y", 0, 0, h - 1, f"piece {nom!r}"))
        pw = int(_num(p, "w", 0, 2, w, f"piece {nom!r}"))
        ph = int(_num(p, "h", 0, 2, h, f"piece {nom!r}"))
        if x + pw > w or y + ph > h:
            raise ValueError(f"piece {nom!r}: box {x},{y} {pw}x{ph} leaves "
                             f"the frame ({w}x{h})")
        pieces.append({"name": nom, "bone": os_nom,
                       "x": x, "y": y, "w": pw, "h": ph})
    return {"bones": os_, "pieces": pieces}


def ecrire_spine(case: Path, rig: dict, dest: Path, tags: list[dict],
                 fps: float = 8.0) -> dict:
    """Ecrit `dest/skeleton.json` + `dest/images/<piece>.png`. Rend le
    squelette. `case` = le PNG d'une case de la feuille."""
    with Image.open(case) as brut:
        im = brut.convert("RGBA")
    w, h = im.size
    (dest / "images").mkdir(parents=True, exist_ok=True)

    slots, attachements = [], {}
    for p in rig["pieces"]:
        morceau = im.crop((p["x"], p["y"], p["x"] + p["w"], p["y"] + p["h"]))
        morceau.save(dest / "images" / f"{p['name']}.png", format="PNG")
        os_ = next(b for b in rig["bones"] if b["name"] == p["bone"])
        cx = p["x"] + p["w"] / 2.0
        cy = p["y"] + p["h"] / 2.0
        slots.append({"name": p["name"], "bone": p["bone"],
                      "attachment": p["name"]})
        attachements[p["name"]] = {p["name"]: {
            "x": round(cx - os_["x"], 2),
            "y": round(_vers_spine(cy, h) - _vers_spine(os_["y"], h), 2),
            "width": p["w"], "height": p["h"], "rotation": 0}}

    os_json = [{"name": "root"}]
    for b in rig["bones"]:
        os_json.append({"name": b["name"], "parent": b["parent"],
                        "x": round(b["x"], 2),
                        "y": round(_vers_spine(b["y"], h), 2),
                        "length": round(b["length"], 2),
                        "rotation": round(b["rotation"], 2)})

    squelette = {
        "skeleton": {"spine": SPINE, "x": 0, "y": 0, "width": w, "height": h,
                     "images": "./images/", "fps": fps},
        "bones": os_json,
        "slots": slots,
        # TABLEAU, pas carte de cartes : c'est la forme 3.8 (mesuree le 03/09)
        "skins": [{"name": "default", "attachments": attachements}],
        # animations NOMMEES et VIDES : D3 ne derive pas de timeline.
        "animations": {t["name"]: {} for t in (tags or [])},
    }
    brut = json.dumps(squelette, sort_keys=True).encode("utf-8")
    squelette["skeleton"]["hash"] = hashlib.sha1(brut).hexdigest()[:11]
    (dest / "skeleton.json").write_text(
        json.dumps(squelette, indent=2), encoding="utf-8")
    return squelette
```

- [ ] **Étape 5 : les routes et le ZIP**

`routes.py`, après `sprite_capture` :

```python
@router.post("/assets/sprite/{job}/skeleton")
async def sprite_skeleton(job: str, body: dict):
    """D3 — decoupe une case en pieces, pose les os, ecrit le rig Spine.

    Le navigateur DESSINE les boites et l'arbre d'os ; il n'ecrit ni PNG de
    piece, ni JSON. Tout nait ici.
    """
    from app.services import sprite_skeleton as SK
    d = _sprite_dir(job)
    mf = d / "manifest.json"
    if not mf.is_file():
        raise HTTPException(404, "Not found")
    m = json.loads(mf.read_text(encoding="utf-8"))
    try:
        i = int(body.get("frame") or 0)
    except (TypeError, ValueError):
        raise HTTPException(400, "frame must be an integer")
    case = d / "frames" / f"{i:03d}.png"
    if not case.is_file():
        raise HTTPException(400, f"frame {i}: aucune case a ce numero")
    from PIL import Image as _I
    with _I.open(case) as im:
        w, h = im.size
    try:
        rig = SK.normalize_rig(body, w, h)
        sq = await asyncio.to_thread(
            SK.ecrire_spine, case, rig, d / "spine",
            ((m.get("anim") or {}).get("tags") or []),
            float(m.get("fps") or 8))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "bones": len(sq["bones"]), "slots": len(sq["slots"]),
            "hash": sq["skeleton"]["hash"]}


@router.get("/assets/sprite/{job}/skeleton")
async def get_sprite_skeleton(job: str):
    """Le squelette Spine JSON du job (404 tant qu'aucun rig n'a ete pose)."""
    p = _sprite_dir(job) / "spine" / "skeleton.json"
    if not p.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(p, media_type="application/json")
```

`sprite_service.build_zip_bytes`, après la boucle sur `frames/` :

```python
        sdir = out_dir / "spine"
        if sdir.is_dir():
            # rglob : le dossier porte skeleton.json ET images/<piece>.png —
            # une boucle a plat oublierait les pieces, et un rig sans ses
            # images ne s'ouvre pas.
            for f in sorted(sdir.rglob("*")):
                if f.is_file():
                    z.write(f, f"spine/{f.relative_to(sdir).as_posix()}")
```

`get_sprite_manifest` : `data["files"]` gagne `"spine": (d / "spine" / "skeleton.json").is_file(),`.

- [ ] **Étape 6 : vert**

Run: `cd backend && python tests/test_sprite_skeleton.py`
Expected: `4 passed`.
Run: `cd backend && python tests/test_sprite_exports.py && python tests/test_sprite_ase.py`
Expected: `4 passed` puis `5 passed`.

- [ ] **Étape 7 : le mode « Squelette » du canevas**

Le canevas de T8 gagne un mode : au lieu de peindre, on trace des **boîtes** (glisser) et l'on pose des **os** (clic). `index.html`, dans `.paint-tools` :

```html
          <button id="pTool-box" class="btn tool" data-tool="box" title="Pièce : glisser pour tracer une boîte (S)">▭</button>
          <button id="pTool-bone" class="btn tool" data-tool="bone" title="Os : cliquer pour le poser, il s'accroche à la pièce sélectionnée (O)">🦴</button>
          <button id="skSave" class="btn" title="Écrit le rig Spine (JSON + PNG des pièces) côté serveur">🦴 Écrire le rig</button>
```

et, sous le canevas :

```html
        <div id="skList" class="sklist"></div>
```

`spritelab.css` :

```css
/* ── D3 : rig ── */
.sklist{font-family:var(--f-mono);font-size:11px;color:var(--ink-soft);margin-top:6px;max-height:120px;overflow:auto}
.sklist .row{display:flex;gap:8px;align-items:center}
.sklist .row button{border:none;background:none;color:var(--ink-muted);cursor:pointer}
```

`spritelab.js`, à la suite de la section P5b :

```js
/* ───────── D3 : rig Spine ─────────
   La page DESSINE (boîtes, os) ; Python découpe, écrit les PNG des pièces et
   le skeleton.json. Aucune image n'est fabriquée ici. */
const rig = { pieces: [], bones: [], drag: null };

function rigDraw() {
  const ov = $("#pOnionCv"), ctx = ov.getContext("2d");
  paintOnion();                                   // repose la pelure d'abord
  ctx.save();
  ctx.lineWidth = 1; ctx.strokeStyle = "#4dd8e6";
  for (const p of rig.pieces) ctx.strokeRect(p.x + 0.5, p.y + 0.5, p.w - 1, p.h - 1);
  ctx.fillStyle = "#f0b429";
  for (const b of rig.bones) ctx.fillRect(b.x - 1, b.y - 1, 3, 3);
  if (rig.drag) {
    ctx.strokeStyle = "#f0b429";
    ctx.strokeRect(rig.drag.x + 0.5, rig.drag.y + 0.5, rig.drag.w, rig.drag.h);
  }
  ctx.restore();
  $("#skList").innerHTML =
    rig.bones.map((b, i) => `<div class="row">🦴 ${esc(b.name)} · parent ${esc(b.parent || "root")} · ${b.x},${b.y}<button data-k="b${i}">✕</button></div>`).join("")
    + rig.pieces.map((p, i) => `<div class="row">▭ ${esc(p.name)} · os ${esc(p.bone)} · ${p.x},${p.y} ${p.w}×${p.h}<button data-k="p${i}">✕</button></div>`).join("");
  $$("#skList button").forEach(b => b.onclick = () => {
    const k = b.dataset.k;
    (k[0] === "b" ? rig.bones : rig.pieces).splice(parseInt(k.slice(1), 10), 1);
    rigDraw();
  });
}

async function rigSave() {
  if (!sheet) return;
  if (!rig.bones.length || !rig.pieces.length)
    return toast("Pose au moins un os et une pièce.", true);
  const st = $("#paintStatus");
  try {
    setStatus(st, "Écriture du rig…", false, 30);
    const d = await api.send("POST", `/assets/sprite/${sheet.short}/skeleton`,
      { frame: paint.i, bones: rig.bones, pieces: rig.pieces });
    clearStatus(st);
    toast(`Rig écrit ✓ — ${d.bones} os, ${d.slots} pièces (hash ${d.hash})`);
    const m = await api.get("/assets/sprite/" + sheet.short + "/manifest");
    showResult(sheet.short, m);
  } catch (e) {
    setStatus(st, "Échec : " + e.message, true);
  }
}
```

`paintAt` gagne, en tête : `if (paint.tool === "box" || paint.tool === "bone") return;` — les deux outils du rig ont leurs propres gestes, câblés dans `wire()` :

```js
  $("#pCv").addEventListener("pointerdown", (e) => {
    if (paint.tool !== "box") return;
    const r = $("#pCv").getBoundingClientRect();
    rig.drag = { x: Math.floor((e.clientX - r.left) / r.width * paint.w),
                 y: Math.floor((e.clientY - r.top) / r.height * paint.h),
                 w: 0, h: 0 };
  });
  $("#pCv").addEventListener("pointermove", (e) => {
    if (!rig.drag) return;
    const r = $("#pCv").getBoundingClientRect();
    rig.drag.w = Math.floor((e.clientX - r.left) / r.width * paint.w) - rig.drag.x;
    rig.drag.h = Math.floor((e.clientY - r.top) / r.height * paint.h) - rig.drag.y;
    rigDraw();
  });
  $("#pCv").addEventListener("pointerup", () => {
    if (!rig.drag) return;
    const d = rig.drag; rig.drag = null;
    const x = Math.min(d.x, d.x + d.w), y = Math.min(d.y, d.y + d.h);
    const w = Math.abs(d.w), h = Math.abs(d.h);
    if (w >= 2 && h >= 2) {
      const nom = (prompt("Nom de la pièce (lettres, chiffres, _ ou -) :",
                          "piece" + (rig.pieces.length + 1)) || "").trim();
      const os = rig.bones.length ? rig.bones[rig.bones.length - 1].name : null;
      if (!nom) { rigDraw(); return; }
      if (!os) { toast("Pose d'abord un os : une pièce s'accroche à un os.", true); rigDraw(); return; }
      rig.pieces.push({ name: nom, bone: os, x, y, w, h });
    }
    rigDraw();
  });
  $("#skSave").onclick = rigSave;
```

et, dans le `keydown` de T8, `s: "box"` et `o: "bone"` rejoignent la table des raccourcis. Le clic « os » se pose dans `paintAt` avant le `return` :

```js
  if (paint.tool === "bone") {
    const nom = (prompt("Nom de l'os :", "os" + (rig.bones.length + 1)) || "").trim();
    if (nom) rig.bones.push({ name: nom, x, y,
      parent: rig.bones.length ? rig.bones[rig.bones.length - 1].name : "root" });
    rigDraw();
    return;
  }
```

- [ ] **Étape 8 : commit** — sujet `sprites : T12 - decoupe en pieces os et export Spine JSON` ; corps : périmètre figé (un rig, pas d'animation — R10a demande la découpe et les os), la correction mesurée du 03/09 (`skins` est un **tableau** en 3.8, la carte de cartes est du 3.7), et **une seule** conversion de repère (`_vers_spine`), parce que deux conversions à deux endroits donnent un sprite à l'envers dont personne ne trouve la cause.

---

## Écarté

- **E1 — Palette de projet verrouillée entre les images.** Réponse 1 de R10a : « l'état actuel me va » (presets `PALETTES` + adaptative MEDIANCUT, par image — `pixel_ops.py:34-57`, `:136-154`). Non planifié ; si la dérive de palette entre images devient visible, le point d'entrée est `_quantize_rgb`, qui sait déjà remapper sur une palette imposée (`_palette_image`) — il ne manque qu'un `palette_custom` dans `normalize_pixel_opts`.
- **E2 — Moteur pixel-art dédié (Retro Diffusion).** Réponse 7 de R10a : « génération image contrainte + pixelisation locale, pas de nouveau moteur ». T11 livre exactement cela pour le prix d'une image. Retro Diffusion (retrodiffusion.ai, vérifié le 03/09/2026 : API développeur à crédits) reste une note, pas une tâche : l'ajouter demanderait une clé, une ligne de tarif dans `pricing.py` et un fournisseur de plus à garder d'accord — pour un gain que T11 + le pipeline local n'ont pas encore prouvé absent.

---

## Campagne de mutations

### Tâche 13 — la campagne de mutations

**Files :**
- Create: `backend/tests/mutations_sprites.py`
- Test: aucun — **ce fichier n'est pas un test** (son nom ne commence pas par `test_`, `run-tests.ps1` ne le liste pas, pytest ne le collecte pas)

**Pourquoi (mesuré) :** les onze tâches précédentes ont produit onze bancs verts. Un banc vert prouve qu'il passe, pas qu'il **mord**. Le dépôt a déjà le patron et il a déjà payé : `backend/tests/mutations_plaque_slicer.py` dit en tête que « une VERTE est une assertion qui manque — c'est ainsi que la ligne morte du pivot, le trou de l'origine des règles et le mutant faible du libellé ont été trouvés ». On refait le geste sur les sprites.

**Ce qui change par rapport au patron :** la plaque avait **un** banc (`BANC = "tests/test_etabli_canevas.py"`) ; les sprites en ont onze. Chaque mutation porte donc **son** banc, et `M` passe de 4-uplets à 5-uplets. Tout le reste — vérification que la mutation s'applique une seule fois, remise à l'octet près sous `finally`, lecture du code de sortie **et** des lignes `ERROR` pour distinguer une collecte cassée d'une mutation verte — est repris tel quel, parce qu'il a déjà été payé.

- [ ] **Étape 1 : écrire le lanceur**

Créer `backend/tests/mutations_sprites.py` :

```python
"""Banc de mutations du Sprite Lab : casser -> rouge -> remettre.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance A LA MAIN, depuis backend/ :

    python tests/mutations_sprites.py           # toutes
    python tests/mutations_sprites.py 3 17      # celles-la

Il MUTE les sources du depot une a une et les REMET a l'octet pres
(assertion), donc il ne se lance pas pendant qu'un autre banc lit ces
fichiers. La liste EST l'argument de la revue : chaque mutation nomme le test
qu'elle fait rougir, et une « VERTE » est une assertion qui manque.

Difference avec `mutations_plaque_slicer.py`, dont c'est le patron : la
plaque avait UN banc, les sprites en ont onze — chaque mutation porte donc le
sien, et `M` est fait de 5-uplets.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable

SS = "backend/app/services/sprite_service.py"
SA = "backend/app/services/sprite_anim.py"
SE = "backend/app/services/sprite_export.py"
SP = "backend/app/services/sprite_post.py"
SD = "backend/app/services/sprite_directions.py"
SK = "backend/app/services/sprite_skeleton.py"
RT = "backend/app/api/routes.py"

B_NAT = "tests/test_sprite_native.py"
B_ANI = "tests/test_sprite_anim.py"
B_EXP = "tests/test_sprite_exports.py"
B_ASE = "tests/test_sprite_ase.py"
B_POS = "tests/test_sprite_post.py"
B_EDI = "tests/test_sprite_editor.py"
B_RET = "tests/test_sprite_frame_edit.py"
B_DIR = "tests/test_sprite_directions.py"
B_CAP = "tests/test_sprite_capture.py"
B_SKE = "tests/test_sprite_skeleton.py"

# (fichier, ancien, nouveau, banc, tests attendus rouges)
M = [
    # ── T1 : la cellule native ───────────────────────────────────────────────
    (SS, "        size = 0                       # P1 : sentinelle « pas d'agrandissement »",
     "        size = 128", B_NAT, ["native"]),
    (SS, "            cell = _place_into_cell(im, size, align) if native \\\n"
         "                else _fit_into_cell(im, size, align, resample)",
     "            cell = _fit_into_cell(im, size, align, resample)",
     B_NAT, ["ne_redimensionne_pas"]),
    (SS, '    y = (size - h) if align == "feet" else (size - h) // 2',
     "    y = (size - h) // 2", B_NAT, ["ne_redimensionne_pas"]),
    (SS, "                w, h = (union[2] - union[0], union[3] - union[1]) if union else im.size",
     "                w, h = im.size", B_NAT, ["ne_redimensionne_pas"]),

    # ── T2 : tags et durees ─────────────────────────────────────────────────
    (SA, "        if not 0 <= a <= b < borne:", "        if not 0 <= a <= b:",
     B_ANI, ["borne_tout_ce_qui_entre", "deborde"]),
    (SA, "    borne = MAX_FRAMES if n is None else n", "    borne = MAX_FRAMES",
     B_ANI, ["deborde"]),
    (SA, '        return [("default", 0, max(0, n - 1))]', "        return []",
     B_ANI, ["borne_tout_ce_qui_entre"]),
    (SS, '        duration=[max(20, d) for d in anim["durations"]],',
     '        duration=max(20, anim["durations"][0]),',
     B_ANI, ["duree_par_image"]),
    (SS, '            "duration_ms": anim["durations"][i],',
     '            "duration_ms": anim["durations"][0],',
     B_ANI, ["duree_par_image"]),

    # ── T3 : Godot et l'atlas ───────────────────────────────────────────────
    (SE, "            rel = round(ms / 1000.0 * fps, 4)",
     "            rel = round(ms / 1000.0, 4)", B_EXP, ["tres_godot"]),
    (SE, '    lignes = [f\'[gd_resource type="SpriteFrames" load_steps={n + 2} format=3]\',',
     '    lignes = [f\'[gd_resource type="SpriteFrames" load_steps={n + 1} format=3]\',',
     B_EXP, ["tres_godot"]),
    (SE, '    return s + "0" if s.endswith(".") else s', "    return s",
     B_EXP, ["tres_godot"]),
    (SE, '    return (0.5, 0.0) if align == "feet" else (0.5, 0.5)',
     "    return (0.5, 0.5)", B_EXP, ["ancrage_pieds"]),
    (SE, '    tags = [{"name": t["name"], "from": t["from"], "to": t["to"],\n'
         '             "direction": t["direction"]}\n'
         '            for t in ((manifest.get("anim") or {}).get("tags") or [])]',
     "    tags = []", B_EXP, ["atlas_json_hash"]),

    # ── T4 : le .ase ────────────────────────────────────────────────────────
    (SE, '    return struct.pack("<IH", len(charge) + 6, type_) + charge',
     '    return struct.pack("<IH", len(charge), type_) + charge',
     B_ASE, ["en_tete_et_les_durees"]),
    (SE, "    return struct.pack(_ASE_IMAGE, len(corps) + 16, 0xF1FA,",
     "    return struct.pack(_ASE_IMAGE, len(corps), 0xF1FA,",
     B_ASE, ["en_tete_et_les_durees"]),
    (SE, '    charge = struct.pack("<HhhBHh5s", 0, 0, 0, 255, 2, 0, b"\\0" * 5)',
     '    charge = struct.pack("<HhhBH5s", 0, 0, 0, 255, 2, b"\\0" * 5)',
     B_ASE, ["cel_decompresse"]),
    (SE, '            "<HHBH6s3sB", t["from"], t["to"],',
     '            "<HHBH6s3sB", t["to"], t["from"],',
     B_ASE, ["image_zero_porte"]),
    (SE, "        0,                                    # nb couleurs : aucune palette",
     "        256,                                  # nb couleurs : aucune palette",
     B_ASE, ["en_tete_et_les_durees"]),

    # ── T6 : le post-traitement ─────────────────────────────────────────────
    (SP, "    anneau = ImageChops.subtract(grossi, mask)", "    anneau = grossi",
     B_POS, ["outline_est_un_anneau"]),
    (SP, "            lambda v: 255 if v > 56 else 0))",
     "            lambda v: 255 if v > 0 else 0))",
     B_POS, ["outline_est_un_anneau"]),
    (SP, "            dens.point(lambda v: 255 if v >= 200 else 0),",
     "            dens.point(lambda v: 0),", B_POS, ["outline_est_un_anneau"]),
    (SP, '        pad = max(pad, abs(sh["dx"]) + sh["blur"], abs(sh["dy"]) + sh["blur"])',
     '        pad = max(pad, abs(sh["dx"]))', B_POS, ["ombre_est_decalee"]),
    (SP, [("    if cl:\n        im = _nettoyer(im, cl)\n    if ol:\n"
           "        im = _contour(im, ol)",
           "    if ol:\n        im = _contour(im, ol)\n    if cl:\n"
           "        im = _nettoyer(im, cl)")],
     None, B_POS, ["outline_est_un_anneau"]),

    # ── T7 : le reassemblage ────────────────────────────────────────────────
    (SS, '            dest = edit / f"src_{k:04d}.png"\n'
         "            _sh.copy2(src, dest)\n"
         '            fichiers.append((dest, bool(ancien["frames"][i].get("bg_removed"))))',
     '            fichiers.append((src, bool(ancien["frames"][i].get("bg_removed"))))',
     B_EDI, ["reordonner_dupliquer_supprimer"]),
    (SS, "        if not 0 <= v < n_old:", "        if v < 0:",
     B_EDI, ["bornes_de_l_ordre"]),

    # ── T8 : la retouche d'une case ─────────────────────────────────────────
    (RT, "    if recu != attendu:", "    if False:", B_RET, ["six_gardes"]),
    (RT, "    if not octets.startswith(_PNG_MAGIC):\n"
         '        raise HTTPException(400, "case : un PNG est attendu (signature "',
     '    if False:\n        raise HTTPException(400, "case : un PNG est attendu (signature "',
     B_RET, ["six_gardes"]),
    (RT, "    if len(octets) > _SPRITE_FRAME_MAX:",
     "    if len(octets) > 100 * _SPRITE_FRAME_MAX:", B_RET, ["six_gardes"]),
    (RT, "    await asyncio.to_thread(reassemble, _sprite_dir(job), ordre,\n"
         '                            mf["grid"]["cols"], mf.get("anim"))',
     "    pass", B_RET, ["case_retouchee_arrive"]),

    # ── T9 : la planche decoupee ────────────────────────────────────────────
    (SD, "    y0, y1 = bandes[-1]", "    y0, y1 = bandes[0]",
     B_DIR, ["quatre_colonnes"]),
    (SD, '    if len(runs) != len(COLONNES):', "    if False:",
     B_DIR, ["n_est_pas_un_personnage"]),
    (SD, 'VERS_HUIT = {"front": "south", "left": "west", "right": "east",',
     'VERS_HUIT = {"front": "south", "left": "east", "right": "west",',
     B_DIR, ["route_fabrique_une_feuille"]),

    # ── T10 : la capture d'une orbite ───────────────────────────────────────
    (RT, "    if dir not in SD.HUIT:", "    if False:",
     B_CAP, ["gardes_de_la_porte"]),
    (RT, '    return {"filename": nom, "alpha": mini == 0, "octets": len(octets)}',
     '    return {"filename": nom, "alpha": True, "octets": len(octets)}',
     B_CAP, ["vue_opaque"]),

    # ── T12 : le rig Spine ──────────────────────────────────────────────────
    (SK, "    return hauteur - y_client", "    return y_client",
     B_SKE, ["forme_spine_3_8"]),
    (SK, '        "skins": [{"name": "default", "attachments": attachements}],',
     '        "skins": {"default": attachements},', B_SKE, ["forme_spine_3_8"]),
    (SK, "        if parent not in vus:", "        if False:",
     B_SKE, ["gardes_du_rig"]),
    (SK, "        if not _NOM.match(nom):\n"
         '            raise ValueError(f"piece name {nom!r}: 1-32 chars, letters, "',
     '        if False:\n            raise ValueError(f"piece name {nom!r}: 1-32 chars, letters, "',
     B_SKE, ["gardes_du_rig"]),
    (SK, "        if x + pw > w or y + ph > h:", "        if False:",
     B_SKE, ["gardes_du_rig"]),
    (SS, '            for f in sorted(sdir.rglob("*")):',
     '            for f in sorted(sdir.glob("*")):',
     B_SKE, ["zip_emporte_le_dossier_spine"]),
]


def rouges(banc, k):
    """Les tests rouges du banc cible — et si RIEN n'a tourne, on le dit.

    pytest sort 0 (tout vert) ou 1 (des rouges) quand il a tourne ; 2 a 5
    quand la COLLECTE a casse (une erreur de syntaxe, un import qui leve) ou
    qu'aucun test ne correspond. Lue comme « aucun FAILED », une collecte
    cassee passerait pour une mutation VERTE alors que rien n'a ete mesure.
    On lit donc le code de sortie ET les lignes `ERROR`, et l'on rend un
    troisieme etat.
    """
    r = subprocess.run([PY, "-m", "pytest", banc, "-q", "--no-header",
                        "-p", "no:warnings", "-k", k],
                       capture_output=True, cwd=R / "backend", timeout=900)
    txt = r.stdout.decode("utf-8", "replace")
    erreur = (r.returncode not in (0, 1)
              or bool(re.search(r"^ERROR ", txt, re.M)))
    return set(re.findall(r"^FAILED [^:]+::(\w+)", txt, re.M)), txt, erreur


def main():
    seuls = sys.argv[1:]
    bilan = []
    for i, (rel, old, new, banc, attendus) in enumerate(M):
        if seuls and str(i) not in seuls:
            continue
        p = R / rel
        src = p.read_bytes()
        brut = src.decode("utf-8")
        # les fichiers de l'arbre sont en CRLF (autocrlf) : on apparie en LF
        # et l'on reecrit avec la fin de ligne du fichier ; la remise se fait
        # a l'octet pres depuis `src`.
        eol = "\r\n" if "\r\n" in brut else "\n"
        txt = brut.replace("\r\n", "\n")
        # une mutation est UN remplacement, ou une LISTE de remplacements
        # appliques dans l'ordre (quand on deplace un appel, il faut l'oter
        # d'un endroit et le poser a un autre)
        paires = old if isinstance(old, list) else [(old, new)]
        for o, n_ in paires:
            assert txt.count(o) == 1, (i, rel, txt.count(o), o[:60])
            txt = txt.replace(o, n_)
        sha_avant = hashlib.sha256(src).hexdigest()
        p.write_bytes(txt.replace("\n", eol).encode("utf-8"))
        try:
            rg, sortie, erreur = rouges(banc, " or ".join(attendus))
        finally:
            p.write_bytes(src)
            sha_apres = hashlib.sha256(p.read_bytes()).hexdigest()
            assert sha_apres == sha_avant, (i, rel, sha_avant, sha_apres)
        manquants = [a for a in attendus if not any(a in n for n in rg)]
        if erreur:
            verdict = "ERREUR(collecte)"
            print(sortie[-1200:], file=sys.stderr)
        else:
            verdict = ("ROUGE" if not manquants
                       else ("VERTE" if not rg else "ROUGE(autres)"))
        bilan.append((i, rel, verdict, sorted(rg), manquants))
        apercu = paires[0][0].strip()[:46]
        print(f"[{i:2d}] {verdict:16s} {pathlib.Path(rel).name:22s} "
              f"{apercu!r} -> {sorted(rg)}  sha {sha_avant[:10]}={sha_apres[:10]}")
        sys.stdout.flush()
    print(json.dumps([b[:3] for b in bilan], ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Étape 2 : lancer la campagne**

Run: `cd backend && python tests/mutations_sprites.py`
Expected: 41 lignes, une par mutation, chacune commençant par `[ n] ROUGE` et finissant par `sha xxxxxxxxxx=xxxxxxxxxx` (les deux empreintes **identiques** : le fichier est remis à l'octet près), puis une ligne JSON de bilan. Une ligne `ERREUR(collecte)` signifie que la mutation a cassé l'import, pas une assertion : la corriger avant de conclure quoi que ce soit.

- [ ] **Étape 3 : la seule chose à faire d'une VERTE**

Une **VERTE** n'est pas un succès : c'est un trou. Le traitement est toujours le même — **ajouter l'assertion qui manque**, pas retirer la mutation.

La mutation **3** (`w, h = (union[2] - union[0], …) if union else im.size` → `w, h = im.size`) est celle qu'on attend verte : `test_sprite_native.py` ne mesure la cellule native qu'en `trim: "animation"`, où `union` vaut `None` — la ligne mutée n'est jamais prise. Si elle sort VERTE, ajouter ce test à `backend/tests/test_sprite_native.py`, **avant** de commettre la campagne :

```python
def test_la_cellule_native_se_mesure_sur_le_CONTENU_en_mode_tight():
    """En `tight`, les images sont recadrees a l'union des contenus AVANT
    d'entrer dans la cellule : la cellule native doit donc se mesurer sur
    l'union, pas sur la taille des fichiers. Sans ce test, la ligne qui fait
    ce choix est morte pour le banc."""
    from app.config import settings
    from app.services import sprite_service as S
    noms = []
    for i in range(2):
        n = f"t{i}.png"
        im = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
        # contenu de 20x10 seulement, colle en haut a gauche
        ImageDraw.Draw(im).rectangle([4, 4, 23, 13],
                                     fill=(200, 60 * i + 60, 40, 255))
        im.save(settings.images_path / n)
        noms.append(n)
    asyncio.run(S.generate_sprites(
        {"source": {"kind": "images", "filenames": noms},
         "cell": {"size": "native"}, "trim": "tight", "columns": 2}, "j-tight"))
    m = json.loads((settings.outputs_path / "sprites" / "j-tight"
                    / "manifest.json").read_text("utf-8"))
    # union des contenus = 20x10 -> cellule native = 20, PAS 60
    assert m["grid"]["cell_w"] == 20 and m["grid"]["cell_h"] == 20
    with Image.open(settings.outputs_path / "sprites" / "j-tight"
                    / "sheet.png") as sh:
        assert sh.size == (40, 20)
```

Run: `cd backend && python tests/test_sprite_native.py` — Expected: `3 passed`.
Run: `cd backend && python tests/mutations_sprites.py 3` — Expected: `[ 3] ROUGE`.

Toute autre VERTE se traite pareil : nommer le trou, écrire l'assertion, relancer **cette** mutation seule.

- [ ] **Étape 4 : commit**

`msg.txt` :

```
sprites : T13 - la campagne de mutations du Sprite Lab

Pourquoi : onze bancs verts prouvent qu ils passent, pas qu ils mordent. 41
mutations, chacune nommant le test qu elle doit faire rougir ; le patron est
mutations_plaque_slicer.py, avec un banc PAR mutation (les sprites en ont
onze la ou la plaque en avait un). Une VERTE est une assertion qui manque :
le trou trouve par la mutation 3 (la cellule native mesuree sur l union en
mode tight) est ferme par un test de plus.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

```bash
git add backend/tests/mutations_sprites.py backend/tests/test_sprite_native.py
git commit -F msg.txt
```

- [ ] **Étape 5 : le passage complet, une fois**

Run: `cd backend && python tests/test_sprite_images_source.py && python tests/test_sprite_native.py && python tests/test_sprite_anim.py && python tests/test_sprite_exports.py && python tests/test_sprite_ase.py && python tests/test_sprite_paper2d.py && python tests/test_sprite_post.py && python tests/test_sprite_editor.py && python tests/test_sprite_frame_edit.py && python tests/test_sprite_directions.py && python tests/test_sprite_capture.py && python tests/test_sprite_prompt.py && python tests/test_sprite_skeleton.py`
Expected, dans l'ordre : `2 passed`, **`2 ou 3 passed`** (3 si la mutation 3 est sortie VERTE et que l'assertion de l'étape 3 a été ajoutée), `3 passed`, `4 passed`, `5 passed`, `3 passed`, `5 passed`, `3 passed`, `3 passed`, `4 passed`, `4 passed`, `3 passed`, `4 passed`.

Puis, et **seulement** à la main (c'est l'utilisateur qui relance l'application, jamais l'agent) :
`.\scripts\run-tests.ps1 -Filter test_sprite` — un processus par fichier, la sortie du harnais fait foi.

Enfin, les bancs voisins que ce plan touche par ricochet, parce que `_assemble` est partagé :
Run: `cd backend && python -m pytest tests/test_starter_particles.py tests/test_pixel_ops.py -q`
Expected: aucun échec — les particules et les séquences Kenney passent par `SS._assemble` (`particle_service.py:486-490`, `:537-540`) sans poser les clés `anim`, `post` ni `native`, et c'est précisément ce que les `opts.get(...)` de T2, T6 et T1 protègent.
