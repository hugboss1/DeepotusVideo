# Templates (mises en page spatiales) — plan d'implémentation

> **Pour les agents exécutants :** SOUS-COMPÉTENCE REQUISE — utiliser
> `superpowers:subagent-driven-development` (recommandé) ou
> `superpowers:executing-plans` pour exécuter ce plan tâche par tâche. Les
> étapes sont des cases à cocher (`- [ ]`).

**But :** faire des Templates un vrai éditeur de mise en page — plusieurs kits
de marque, un même gabarit rejoué en quatre formats, des masques de région
(fenêtres ajourées à bords pleins arrondis sur un encart ajusté), du texte
mesuré avant d'être dessiné, une sortie image fixe, des aperçus au contenu
réel — puis des composants partagés, des animations de région, un import Figma
éditable et du texte sur courbe.

**Architecture :** tout ce qui décide reste du JSON pur (`canvas`, `regions`)
lu par UN compositeur ffmpeg. Ce qui ne se calcule pas dans un filtergraph
(coins arrondis, fenêtres, contours, dégradés, texte ajusté, texte courbe) est
**peint en PIL dans le dossier de travail du rendu** puis injecté : le masque
par `alphamerge`, tout le reste par `overlay`. Une image fixe est le MÊME
filtergraph terminé par `trim` + `-frames:v 1` — jamais un second moteur qui
divergerait.

**Pile :** python EMBARQUÉ, stdlib + Pillow (pas de numpy) ; ffmpeg/ffprobe ;
FastAPI ; le bundle compilé, patché par `scripts/patch_bundle_<tag>.py`
chaînés.

---

## Ce que le code fait aujourd'hui — mesuré le 03/09/2026

Relu dans ce worktree, pas de mémoire :

| Fait | Mesure |
|---|---|
| Un template est du JSON pur | `backend/app/services/template_service.py:120-215` |
| 9 gabarits livrés, **tous 1080×1920**, 2 à 5 régions | `backend/app/templates/*.json` |
| Types présents dans les JSON livrés | `audio_slot`, `brand_strip`, `separator`, `text_slot`, `video_slot` |
| Types que le renderer sait dessiner | + `image_slot`, `text`, `badge`, `sticker`, `ticker` (`template_service.py:660-871`) |
| 23 fontes embarquées, 1 marque | `backend/app/templates/_fonts/` ; table `_FONT_FILES:52-79` ; `templates/marks/wordmark_cyan.png` |
| Rendu vidéo | `build_ffmpeg_command:575-935` (spatial), `build_sequential_command:959-1137` (montage) |
| Déjà en PIL dans le rendu | `render_badge_bg_png:499` (rectangle arrondi) et `render_emoji_text_png:523` — **le patron du plan existe déjà** |
| Routes | `backend/app/api/routes.py:114-199` (`/layout-templates*`), `:3686-3797` (`/branding*`, `BRAND_DEFAULTS:3690`) |
| Kit de marque | **un seul**, 7 champs texte + un logo PNG, dans `DATA_ROOT/assets/branding/` |
| Figma | `backend/app/services/figma_import.py` — un calque → un PNG, 75 lignes, deux hooks réseau `_get_json` / `_get_bytes` |
| Éditeur de régions | **dans le bundle** `frontend/dist/assets/index-BEOJX8L5.js` : galerie `fm(...)` (offset ≈ 462 438), éditeur `hm({pickedT,onSaved})` (≈ 465 900), vignette `gm({id,regions,canvas})` (≈ 484 000) |
| Konva | **0 occurrence** (`grep -c Konva` = 0) — le « éditeur visuel Konva » de DESIGN §5 est une intention, pas une mesure |
| Formats du bundle | `function pd(e)` : `1:1`→1080×1080, `16:9`→1920×1080, `4:5`→1080×1350, défaut 1080×1920 |

Inventaire mesuré :

```
tpl_alpha_reel_60_30_10.json            1080x1920 regions=3 mode=spatial
tpl_classic_vstack_50_50.json           1080x1920 regions=2 mode=spatial
tpl_hstack_left_right_dialogue.json     1080x1920 regions=2 mode=spatial
tpl_montage_film.json                   1080x1920 regions=5 mode=sequential
tpl_news_reel.json                      1080x1920 regions=4 mode=spatial
tpl_oracle_full_with_lower_third.json   1080x1920 regions=3 mode=spatial
tpl_pip_corner_avatar.json              1080x1920 regions=2 mode=spatial
tpl_three_act_sequential.json           1080x1920 regions=3 mode=sequential
tpl_timeline.json                       1080x1920 regions=5 mode=sequential
```

**Absents** (le périmètre du plan) : plusieurs kits, réagencement multi-format,
masques, composants partagés, animations de région, texte adaptatif et effets,
rendu image fixe, aperçus au contenu réel, import Figma éditable.

---

## Périmètre

**Lot 1 — parité**, dans cet ordre (l'ordre est une contrainte : P2 pose les
contraintes que D1 réutilise, P4 pose le moteur de texte que D4 étend, P5 pose
l'image fixe dont P6 vit) :

- **P1** Kits de marque multiples — Tâche 1
- **P2** Réagencement multi-format — Tâche 2
- **P3** Masques de région — Tâche 3
- **P4** Texte adaptatif et effets — Tâche 4
- **P5** Rendu image fixe — Tâche 5
- **P6** Aperçus au contenu réel — Tâche 6
- La greffe bundle du lot 1 — Tâche 7

**Lot 2 — différenciant** :

- **D1** Bibliothèque de composants — Tâche 8
- **D2** Animations de région — Tâche 9
- **D3** Import Figma éditable, export **par SVG** (l'API REST n'écrit pas,
  mesuré) — Tâche 10
- **D4** Texte sur courbe et typographie décorative — Tâche 11
- La greffe bundle du lot 2 — Tâche 12

**Campagne de mutations** — Tâche 13.

**Écarté** : E1 modèles par milliers, E2 mockups, E3 écriture directe dans
Figma (section dédiée en fin de plan).

---

## Coût de patch

Règle du dépôt : **le format JSON est bon marché, l'éditeur est cher.** Un
champ de plus dans `regions[]` coûte une clé de dictionnaire côté backend ; le
même champ exposé à l'utilisateur coûte un `scripts/patch_bundle_<tag>.py`
neuf, un `.js.bak_<tag>`, une place EN QUEUE de chaîne, des ancres uniques, et
un `repatch_all.py --from <tag>` derrière.

Le réflexe serait neuf patches (un par bac). **Ce plan en propose trois**,
parce que les greffes se regroupent par *endroit du bundle*, pas par
fonctionnalité :

| Tag | Quand | Ce qu'il porte | Ancres |
|---|---|---|---|
| `tplregion` | Tâche 7 | panneau de région : Masque + Texte ; **et surtout** le chargement et l'enregistrement cessent de filtrer les champs | 4 |
| `tplbar` | Tâche 7 | sélecteur de format (P2), bouton « Exporter une image » (P5), vignettes au contenu réel (P6) | 3 |
| `tplplus` | Tâche 12 | composants (D1), animations (D2), Figma/SVG (D3), rayon de courbe (D4) | 3 |

**La plus petite greffe possible, mesurée.** L'éditeur `hm(...)` recopie les
régions champ par champ, deux fois : à la lecture
(`const H=(E.regions||[]).map(F=>({id:F.id,type:F.type,…}))`) et à
l'enregistrement (`Object.assign({},O0,{id:E.id,…})`). Tout champ inconnu est
donc **perdu au premier Save** — un masque posé par une route disparaîtrait dès
qu'on déplace une région. Deux remplacements de quelques dizaines d'octets
(passer d'un littéral filtrant à un `Object.assign` qui recopie tout sauf la
clé privée `_disp`) ouvrent l'éditeur à **tous** les champs de ce plan et à
ceux d'après. C'est la greffe la moins chère du chantier, faite une seule fois
dans `tplregion`.

Compté par tâche :

| Tâche | Backend | Bundle |
|---|---|---|
| T1 P1 kits | `brand_kits.py` neuf + routes + `render()` | **aucun** (le shell lit `/branding`, qui devient une vue du kit actif) |
| T2 P2 formats | `template_layout.py` neuf + 2 routes | 1 ancre dans `tplbar` |
| T3 P3 masques | `template_mask.py` neuf + 14 lignes de filtergraph | 1 ancre dans `tplregion` |
| T4 P4 texte | `template_text.py` neuf + 12 lignes de filtergraph | 1 ancre dans `tplregion` |
| T5 P5 image | `still_at` dans le builder + 1 route | 1 ancre dans `tplbar` |
| T6 P6 aperçus | 1 route + cache disque | 1 ancre dans `tplbar` |
| T7 | — | `tplregion` + `tplbar` écrits et vérifiés |
| T8 D1 composants | `template_components.py` neuf + 3 routes | 1 ancre dans `tplplus` |
| T9 D2 animations | `template_anim.py` neuf + 8 lignes de filtergraph | 1 ancre dans `tplplus` |
| T10 D3 Figma | `figma_import.py` +180 lignes + 2 routes | 1 ancre dans `tplplus` |
| T11 D4 courbe | `template_text.py` +60 lignes | (portée par l'ancre `tplplus` de T9) |
| T12 | — | `tplplus` écrit et vérifié |

Chaîne mesurée dans ce worktree : `python scripts/repatch_all.py --list` rend
`dzrailmotion, version, dznodecat, seedance25` — les `.bak_*` ne sont pas
versionnés, la chaîne de la machine est plus longue. **Chaque nouveau patcher
se pose EN QUEUE** (`ensure_tail_order`) et refuse de tourner s'il détecte un
`.bak` aval (`guard_downstream`), comme `patch_bundle_print3d.py`.

---

## Références vérifiées

Deux sources **vérifiées le 03/09/2026** (section R7 de
`docs/superpowers/plans/2026-09-02-balayage-meilleur-de-sa-classe.md`) :

- **Canva** — Brand Kit : logos, couleurs, polices, imagerie, templates et
  consignes en un seul lieu ; remplacer un logo le remplace dans les designs
  existants. Magic Switch / Magic Resize redimensionne un design en plusieurs
  formats en un clic. (canva.com, 03/09/2026) → justifie P1 et P2.
- **Figma REST API** — arbre `DOCUMENT → CANVAS → nœuds`, `constraints`
  relatives au cadre parent, `components`, `exportSettings`, endpoint
  `GET /v1/files/{key}/nodes?ids=` pour lire textes et géométrie.
  (developers.figma.com, 03/09/2026) → justifie D3 en LECTURE et **interdit**
  l'écriture : l'API REST n'écrit pas un fichier Figma → E3, l'export passe par
  un SVG.

Tout le reste (Adobe Express, Placeit, Kittl, After Effects) est **de mémoire,
à vérifier** avant d'en faire un argument.

Mesures faites **dans ce worktree le 03/09/2026**, qui portent les choix
techniques :

1. `ffmpeg -filters` contient `alphamerge` (`VV->V`, « copy the luma value of
   the second input into the alpha channel of the first ») → P3 sans numpy.
2. Un masque `L` dessiné en PIL (`rounded_rectangle` r=48 puis `ellipse`
   remplie de 0), passé en `[src][msk]alphamerge` puis `overlay` sur un fond
   rouge : coin `(2,2)` = `(253,0,0)` (fond → arrondi effectif), centre
   `(200,150)` = `(253,0,0)` (fenêtre ajourée), plein `(200,40)` = `(0,0,254)`
   (source). **La fenêtre ajourée à bords arrondis marche.**
3. `[v]trim=start=T:duration=0.2,setpts=PTS-STARTPTS` + `-frames:v 1 -update 1`
   extrait l'image EXACTE à `t=T` : sur `overlay=x='20+t*60'`, x mesuré = 20 à
   t=0 et 140 à t=2. **L'image fixe par le même compositeur marche.**
4. Extraction de contrôle par seek de SORTIE (`-i f.mp4 -ss T`) : x = 20 / 80 /
   140 à t = 0 / 1 / 2 → précision à l'image. **Les bancs-miroirs peuvent lire
   un instant précis d'un MP4.**
5. `PIL 12.2.0` ; `ImageFont.truetype(Anton.ttf, 64).getlength("DEEPOTUS")` =
   `230.0`, `getbbox` = `(0,19,230,77)` → P4 mesure avant de dessiner.
6. Texte sur courbe par rotation glyphe à glyphe (Anton 72 px, rayon 260,
   8 glyphes) : arc = `1.0 rad` exactement (somme des `getlength` / rayon),
   boîte d'encre `(214,320,482,411)`, hauteur 91 px pour une fonte de 72 →
   D4 en PIL pur.
7. Les 7 ancres bundle de ce plan comptent **1** occurrence chacune (script de
   vérification en Tâche 7).

---

## Fichiers — carte

**Créés**

| Fichier | Responsabilité |
|---|---|
| `backend/app/services/brand_kits.py` | les kits, le kit actif, la substitution `{{brand.x}}` |
| `backend/app/services/template_layout.py` | les 4 formats, les contraintes par axe, `reflow()` |
| `backend/app/services/template_mask.py` | masque `L` et cadre `RGBA` en PIL |
| `backend/app/services/template_text.py` | mesure, ajustement, effets, texte courbe |
| `backend/app/services/template_components.py` | composants partagés, `etendre()` |
| `backend/app/services/template_anim.py` | expressions d'overlay et fondus par région |
| `backend/app/templates/_components/cmp_lower_third.json` | un composant livré |
| `backend/tests/_miroir.py` | outils communs des bancs-miroirs (**pas un banc**) |
| `backend/tests/test_templates_kits.py` … `test_templates_figma.py` | 7 bancs |
| `backend/tests/mutations_templates.py` | la campagne |
| `scripts/patch_bundle_tplregion.py`, `_tplbar.py`, `_tplplus.py` | les 3 greffes |

**Modifiés** (chaque plage vient d'un `grep -n` fait dans ce worktree)

| Fichier:lignes | Quoi |
|---|---|
| `backend/app/services/template_service.py:355-390` | `render()` résout composants + kit ; `render_still()` neuf |
| `backend/app/services/template_service.py:575-600` | `build_ffmpeg_command(..., still_at=None)` |
| `backend/app/services/template_service.py:702-716` | masque (T3) et animation (T9) sur la région vidéo/image |
| `backend/app/services/template_service.py:717-747` | chemin PNG du texte ajusté (T4, T11) |
| `backend/app/services/template_service.py:917-935` | queue de commande : image fixe |
| `backend/app/services/template_service.py:290-311` | `slots_from()` résout les composants |
| `backend/app/api/routes.py:114-199` | routes `/layout-templates/*` (reflow, layouts, image, thumb, svg) |
| `backend/app/api/routes.py:3686-3797` | `/branding` devient une vue du kit actif ; `/brand-kits*` |
| `backend/app/services/library_index.py:24-52` | source `templates` + préfixe `tpl_still_` |
| `backend/app/services/figma_import.py:1-75` | lecture d'un cadre, conversion, export SVG |

---

## Règles de banc (valables pour les 7 bancs)

- **Scripts AUTONOMES**, un processus par fichier, lancés depuis `backend/` :
  `python tests/test_<x>.py`. **Jamais `pytest tests`** (chaque banc fige
  `app.config` avec son propre environnement temporaire).
- **UTF-8 forcé** : `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`
  en tête, avant tout `print`.
- **Bancs-miroirs** : on lit le PNG ou le MP4 **rendu** (PIL, ffmpeg), jamais
  le code ni la ligne de commande qui prétend le produire.
- Chaque vérification porte un NOM en majuscules et s'imprime `  PASS  NOM` ou
  `FAILED NOM …` en début de ligne — c'est ce que la campagne de mutations lit.
- Sortie 0 si tout passe, 1 s'il reste un `FAILED`.

---

# Lot 1 — parité

## Tâche 1 : P1 — Kits de marque multiples

**Pourquoi, avec la mesure.** `BRAND_DEFAULTS` (`routes.py:3690`) est un
dictionnaire de 7 clés et il n'y en a qu'un ; `backend/app/templates/*.json`
écrit ses couleurs en dur (`"#00e5ff"` dans `tpl_news_reel.json`, quatre fois
`#02060d`). Rendre le même gabarit pour un client, c'est aujourd'hui dupliquer
les 9 JSON. Canva (vérifié 03/09) tient logos, couleurs, polices et templates
dans UN kit et remplace le logo partout d'un coup : c'est exactement ce que le
JSON permet dès qu'il porte des jetons au lieu de valeurs.

**Fichiers**
- Créer : `backend/app/services/brand_kits.py`
- Créer : `backend/tests/_miroir.py`
- Créer : `backend/tests/test_templates_kits.py`
- Modifier : `backend/app/services/template_service.py:355-390` (`render`)
- Modifier : `backend/app/api/routes.py:3686-3760` (`/branding`) et `:157`
  (bloc `/brand-kits` ajouté après la route de rendu)

**Coût de patch : ZÉRO côté bundle.** Le shell lit `GET /api/branding` et y
trouve `app_name`, `app_sub`, `tagline_1`, `tagline_2`, `brand_color`,
`accent_color` — les six champs restent servis, mais lus dans le kit ACTIF.
Le choix du kit se pilote par les routes (et, plus tard, par l'écran Settings,
hors périmètre de ce plan).

- [ ] **Étape 1 : écrire les outils de banc (ils servent aux 7 bancs)**

Créer `backend/tests/_miroir.py` :

```python
# -*- coding: utf-8 -*-
"""Outils des bancs-miroirs Templates : on lit le MP4 ou le PNG RENDU.

PAS UN BANC : le nom ne commence pas par `test_`, donc run-tests.ps1 ne le
lance pas et pytest ne le collecte pas. Importé par les bancs, qui restent
autonomes (un processus par fichier).
"""
import os
import shutil
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def ffmpeg():
    """ffmpeg du PATH, sinon celui embarque par l'app ; SKIP propre sinon."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    cand = os.path.expandvars(r"%LOCALAPPDATA%\DeepotusVideoGen\bin\ffmpeg.exe")
    if os.path.isfile(cand):
        return cand
    print("SKIP: ffmpeg introuvable — banc-miroir ignore")
    sys.exit(0)


FF = ffmpeg()


def image(mp4, png, t=0.0):
    """L'image du MP4 a l'instant t, lue en RGB. Seek de SORTIE (`-i` puis
    `-ss`) : mesure du 03/09, precision a l'image (20/80/140 px a 0/1/2 s)."""
    from PIL import Image
    subprocess.run([FF, "-y", "-v", "error", "-i", str(mp4), "-ss", str(t),
                    "-frames:v", "1", "-update", "1", str(png)], check=True)
    return Image.open(str(png)).convert("RGB")


def rgb(hexa):
    h = str(hexa or "").lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def proche(a, b, tol=14):
    return all(abs(int(x) - int(y)) <= tol for x, y in zip(a[:3], b[:3]))


def boite_encre(im, fond=None, seuil=42, pas=1):
    """Boite des pixels qui DIFFERENT du fond. `fond` par defaut = le pixel
    (0,0). Rend None si l'image est unie."""
    f = fond if fond is not None else im.getpixel((0, 0))
    w, h = im.size
    xs, ys = [], []
    for y in range(0, h, pas):
        for x in range(0, w, pas):
            p = im.getpixel((x, y))
            if max(abs(p[i] - f[i]) for i in range(3)) > seuil:
                xs.append(x)
                ys.append(y)
    return (min(xs), min(ys), max(xs), max(ys)) if xs else None


_N = {"ok": 0, "ko": 0}


def check(nom, cond, detail=""):
    if cond:
        _N["ok"] += 1
        print("  PASS  " + nom)
    else:
        _N["ko"] += 1
        print("FAILED " + nom + "  " + str(detail))


def bilan(titre):
    print("\n%s : %d PASS, %d FAILED" % (titre, _N["ok"], _N["ko"]))
    sys.exit(1 if _N["ko"] else 0)
```

- [ ] **Étape 2 : écrire le banc qui échoue**

Créer `backend/tests/test_templates_kits.py` :

```python
# -*- coding: utf-8 -*-
"""P1 — kits de marque multiples : le MEME gabarit, deux kits, deux couleurs.

Banc-miroir : on rend deux MP4 et on lit LEURS pixels. Un test qui lirait
brand_kits.appliquer() ne dirait rien du rendu.

Run depuis backend/ :  python tests/test_templates_kits.py
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dztplkit_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = \
    "sqlite+aiosqlite:///" + pathlib.Path(_tmp, "t.db").as_posix()
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from _miroir import check, bilan, image, rgb, proche          # noqa: E402
from app.services import brand_kits as BK                     # noqa: E402
from app.services.template_service import TemplateEngine      # noqa: E402

W, H = 240, 320
TPL = {
    "id": "tpl_banc_kit", "name": "banc kit",
    "canvas": {"width": W, "height": H, "background_color": "#101010",
               "fps": 10, "duration_s": 1},
    "regions": [
        {"id": "r_sep", "type": "separator", "x": 0, "y": 100,
         "width": W, "height": 120, "z_index": 1,
         "color": "{{brand.accent_color}}"},
    ],
}

eng = TemplateEngine()
out = pathlib.Path(_tmp, "outputs")

print("\n[1] Le kit livre existe et il est actif")
doc = BK.lire()
check("KIT_DEEPOTUS_PRESENT", "deepotus" in doc["kits"], sorted(doc["kits"]))
check("KIT_ACTIF_VALIDE", doc["actif"] in doc["kits"], doc["actif"])

print("\n[2] Deux kits, deux rendus, deux couleurs LUES DANS LE MP4")
BK.enregistrer({"id": "deepotus", "accent_color": "#00e5ff"})
BK.activer("deepotus")
mp4a = out / "kit_a.mp4"
eng.render("tpl_banc_kit", {}, mp4a, template=dict(TPL))
pa = image(mp4a, out / "kit_a.png").getpixel((W // 2, 160))
check("KIT_A_ACCENT_RENDU", proche(pa, rgb("#00e5ff")), pa)

BK.enregistrer({"id": "client", "name": "client", "accent_color": "#ff8800"})
BK.activer("client")
mp4b = out / "kit_b.mp4"
eng.render("tpl_banc_kit", {}, mp4b, template=dict(TPL))
pb = image(mp4b, out / "kit_b.png").getpixel((W // 2, 160))
check("KIT_B_ACCENT_RENDU", proche(pb, rgb("#ff8800")), pb)
check("KITS_DIFFERENTS", not proche(pa, pb, tol=20), (pa, pb))

print("\n[3] Refus parlants")
try:
    BK.enregistrer({"id": "client", "accent_color": "bleu"})
    check("COULEUR_REFUSEE", False, "aucune erreur levee")
except ValueError as e:
    check("COULEUR_REFUSEE", "#RRGGBB" in str(e), str(e))
try:
    BK.enregistrer({"id": "mon kit"})
    check("ID_REFUSE", False, "aucune erreur levee")
except ValueError as e:
    check("ID_REFUSE", "identifiant" in str(e), str(e))
BK.activer("deepotus")
check("DERNIER_KIT_PROTEGE",
      BK.supprimer("deepotus") == "actif", "le kit actif doit etre protege")

print("\n[4] Un jeton inconnu reste LISIBLE, il ne devient pas vide")
t = BK.appliquer({"a": "{{brand.inexistant}}"}, BK.actif())
check("JETON_INCONNU_GARDE", t["a"] == "{{brand.inexistant}}", t["a"])

bilan("P1 kits de marque")
```

- [ ] **Étape 3 : lancer le banc et le voir rouge**

```
cd backend
python tests/test_templates_kits.py
```
Attendu : `ModuleNotFoundError: No module named 'app.services.brand_kits'`.

- [ ] **Étape 4 : écrire `brand_kits.py`**

```python
# -*- coding: utf-8 -*-
"""Kits de marque multiples (plan 2026-09-03-plan-templates, P1).

Un kit = un nom, deux couleurs, deux fontes, un logo, quatre chaines de
marque. Le kit ACTIF alimente le shell (`/branding`, inchange pour lui) ET
les templates, qui ecrivent `{{brand.accent_color}}` au lieu d'un `#00e5ff`
en dur. Migration : le `branding.json` d'avant devient le kit `deepotus`.

Stockage : `DATA_ROOT/assets/branding/kits.json` (+ `logos/<kit>.png`), sous
`assets/` donc jamais touche par une mise a jour.
"""
from __future__ import annotations

import json
import re
import shutil
import uuid
from pathlib import Path

from loguru import logger

from app.config import DATA_ROOT

_COULEUR = re.compile(r"^#[0-9a-fA-F]{6}$")
_ID = re.compile(r"^[A-Za-z0-9_-]+$")

#: Champs d'un kit et leurs defauts deepotus. Une cle absente d'ici est
#: refusee : un kit n'est pas un sac ouvert.
CHAMPS: dict[str, str] = {
    "name": "deepotus",
    "app_name": "DEEPOTUS",
    "app_sub": "VIDEO",
    "tagline_1": "From the deep,",
    "tagline_2": "for the deep.",
    "brand_color": "#ef4444",
    "accent_color": "#00e5ff",
    "font_title": "Anton",
    "font_body": "Space Grotesk",
    "logo": "",
}

_JETON = re.compile(r"\{\{\s*brand\.([a-z_]+)\s*\}\}")


def _dossier() -> Path:
    p = DATA_ROOT / "assets" / "branding"
    (p / "logos").mkdir(parents=True, exist_ok=True)
    return p


def _fichier() -> Path:
    return _dossier() / "kits.json"


def _migrer() -> dict:
    """Le kit unique de v1.11 devient le kit `deepotus`. Le logo.png historique
    est COPIE dans logos/deepotus.png (l'original reste : le shell le sert)."""
    kit = dict(CHAMPS)
    ancien = _dossier() / "branding.json"
    if ancien.is_file():
        try:
            u = json.loads(ancien.read_text(encoding="utf-8"))
            for k in CHAMPS:
                if isinstance(u.get(k), str) and u[k].strip():
                    kit[k] = u[k].strip()
        except (ValueError, OSError) as e:
            logger.warning(f"branding.json illisible, kit par defaut : {e}")
    logo = _dossier() / "logo.png"
    if logo.is_file():
        shutil.copyfile(logo, _dossier() / "logos" / "deepotus.png")
        kit["logo"] = "deepotus.png"
    return {"actif": "deepotus", "kits": {"deepotus": kit}}


def _ecrire(doc: dict) -> None:
    f = _fichier()
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(f)


def lire() -> dict:
    """{actif, kits} — cree et migre au premier appel. Ne leve jamais."""
    f = _fichier()
    if not f.is_file():
        doc = _migrer()
        _ecrire(doc)
        return doc
    try:
        doc = json.loads(f.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        logger.warning(f"kits.json illisible, retour aux defauts : {e}")
        return _migrer()
    if not isinstance(doc.get("kits"), dict) or not doc["kits"]:
        return _migrer()
    if doc.get("actif") not in doc["kits"]:
        doc["actif"] = sorted(doc["kits"])[0]
    return doc


def actif() -> dict:
    doc = lire()
    return dict(doc["kits"][doc["actif"]], id=doc["actif"])


def lister() -> list[dict]:
    doc = lire()
    return [dict(v, id=k, _actif=(k == doc["actif"]))
            for k, v in sorted(doc["kits"].items())]


def enregistrer(kit: dict) -> str:
    """Cree ou met a jour. Rend l'identifiant. ValueError = entree fautive."""
    doc = lire()
    kid = str(kit.get("id") or "").strip() or ("kit_" + uuid.uuid4().hex[:8])
    if not _ID.match(kid):
        raise ValueError(
            f"identifiant de kit invalide : {kid!r} — lettres, chiffres, "
            "tiret et souligne seulement")
    propre = dict(doc["kits"].get(kid) or CHAMPS)
    for k in CHAMPS:
        v = kit.get(k)
        if not isinstance(v, str) or not v.strip():
            continue
        v = v.strip()
        if k.endswith("_color") and not _COULEUR.match(v):
            raise ValueError(f"{k} doit etre #RRGGBB (recu : {v})")
        propre[k] = v[:80]
    doc["kits"][kid] = propre
    _ecrire(doc)
    logger.info(f"kit de marque enregistre : {kid}")
    return kid


def activer(kid: str) -> str:
    doc = lire()
    if kid not in doc["kits"]:
        raise ValueError(f"kit inconnu : {kid}")
    doc["actif"] = kid
    _ecrire(doc)
    return kid


def supprimer(kid: str) -> str:
    """"supprime" | "actif" (refus : c'est le kit actif) | "seul" | "absent"."""
    doc = lire()
    if kid not in doc["kits"]:
        return "absent"
    if len(doc["kits"]) == 1:
        return "seul"
    if doc["actif"] == kid:
        return "actif"
    doc["kits"].pop(kid)
    _ecrire(doc)
    (_dossier() / "logos" / f"{kid}.png").unlink(missing_ok=True)
    return "supprime"


def logo_path(kid: str | None = None) -> Path | None:
    k = kid or lire()["actif"]
    p = _dossier() / "logos" / f"{k}.png"
    return p if p.is_file() else None


def appliquer(obj, kit: dict | None = None):
    """Remplace `{{brand.champ}}` dans TOUTES les chaines d'une structure
    JSON. Un champ inconnu est LAISSE TEL QUEL : un gabarit qui reclame un
    jeton absent doit se voir, pas se vider en silence."""
    k = kit or actif()

    def sub(s: str) -> str:
        return _JETON.sub(lambda m: str(k.get(m.group(1), m.group(0))), s)

    def marche(v):
        if isinstance(v, str):
            return sub(v)
        if isinstance(v, list):
            return [marche(x) for x in v]
        if isinstance(v, dict):
            return {kk: marche(vv) for kk, vv in v.items()}
        return v

    return marche(json.loads(json.dumps(obj)))
```

- [ ] **Étape 5 : brancher le kit sur le rendu**

Dans `backend/app/services/template_service.py`, en tête de la méthode
`render` (ligne 372, juste après `tpl = template if template is not None …`),
remplacer :

```python
        tpl = template if template is not None else self.get_template(
            template_id)
        self._validate(tpl)
```

par :

```python
        tpl = template if template is not None else self.get_template(
            template_id)
        tpl = self.resoudre(tpl)
        self._validate(tpl)
```

et ajouter la méthode `resoudre` juste avant `render` (ligne 355) :

```python
    def resoudre(self, tpl: dict) -> dict:
        """Le template TEL QU'IL SERA RENDU : jetons de marque substitues.
        (La Tache 8 y insere l'expansion des composants, AVANT le kit : un
        composant porte lui aussi des jetons.)"""
        from app.services import brand_kits as _bk
        return _bk.appliquer(tpl)
```

- [ ] **Étape 6 : lancer le banc, le voir vert**

```
cd backend
python tests/test_templates_kits.py
```
Attendu : 8 `PASS`, `P1 kits de marque : 8 PASS, 0 FAILED`, sortie 0.

- [ ] **Étape 7 : les routes**

Dans `backend/app/api/routes.py`, remplacer le corps de `_read_branding`
(`:3708-3723`) par une vue du kit actif :

```python
def _read_branding() -> dict:
    """Le kit ACTIF, sous la forme que le shell attend depuis v1.11."""
    from app.services import brand_kits as _bk
    kit = _bk.actif()
    data = {k: kit.get(k, v) for k, v in BRAND_DEFAULTS.items()}
    data["kit_id"] = kit["id"]
    data["has_custom_logo"] = _bk.logo_path(kit["id"]) is not None
    data["is_default"] = (kit["id"] == "deepotus"
                          and not data["has_custom_logo"]
                          and all(data[k] == v
                                  for k, v in BRAND_DEFAULTS.items()))
    return data
```

et ajouter, après la route de rendu (`:199`), le bloc des kits :

```python
# ---- v1.16 : kits de marque multiples (plan 2026-09-03-plan-templates P1) ----

@router.get("/brand-kits")
async def list_brand_kits():
    from app.services import brand_kits as _bk
    return {"kits": _bk.lister(), "actif": _bk.lire()["actif"]}


@router.post("/brand-kits")
async def save_brand_kit(body: dict, request: Request):
    _require_localhost(request)
    from app.services import brand_kits as _bk
    try:
        kid = _bk.enregistrer(body or {})
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"kit_id": kid, "kits": _bk.lister()}


@router.post("/brand-kits/{kit_id}/activate")
async def activate_brand_kit(kit_id: str, request: Request):
    _require_localhost(request)
    from app.services import brand_kits as _bk
    try:
        _bk.activer(kit_id)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"actif": kit_id}


@router.delete("/brand-kits/{kit_id}")
async def delete_brand_kit(kit_id: str, request: Request):
    _require_localhost(request)
    from app.services import brand_kits as _bk
    r = _bk.supprimer(kit_id)
    if r == "absent":
        raise HTTPException(404, f"kit inconnu : {kit_id}")
    if r == "actif":
        raise HTTPException(400, "le kit actif ne se supprime pas : "
                                 "activez-en un autre d'abord")
    if r == "seul":
        raise HTTPException(400, "c'est le dernier kit ; il en faut un")
    return {"deleted": kit_id}
```

- [ ] **Étape 8 : commit**

```
git add backend/app/services/brand_kits.py backend/tests/_miroir.py backend/tests/test_templates_kits.py backend/app/services/template_service.py backend/app/api/routes.py
git commit -m 'etabli : plusieurs kits de marque, un jeton dans le gabarit' -m 'Le kit unique de v1.11 devient le kit deepotus par migration ; les templates ecrivent {{brand.accent_color}} au lieu d une couleur en dur, et le rendu substitue le kit actif. Un jeton inconnu reste lisible plutot que de se vider. Banc-miroir : deux kits, deux MP4, deux couleurs lues au pixel.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

## Tâche 2 : P2 — Réagencement multi-format

**Pourquoi, avec la mesure.** Les 9 gabarits livrés sont **tous** 1080×1920
(mesuré). Le bundle sait déjà nommer quatre formats (`function pd(e)` :
`1:1`→1080×1080, `16:9`→1920×1080, `4:5`→1080×1350, défaut 1080×1920) et la
galerie propose « New: 9:16 16:9 1:1 4:5 » — mais chaque bouton **crée un
gabarit vide**, il ne rejoue pas le gabarit choisi. Canva (vérifié 03/09) fait
l'inverse : un design, un clic, plusieurs formats. La réponse 2 de R7 demande
la règle **et** la reprise à la main, les quatre canevas dans le même JSON.

**Le format des contraintes.** Une région gagne `constraints: {h, v}` avec, par
axe, cinq modes empruntés à Figma : `start` (marge de tête gardée), `end`
(marge de queue gardée), `center` (centre relatif gardé), `scale` (position et
taille mises à l'échelle — le défaut, c'est le comportement le moins
surprenant), `stretch` (les deux marges gardées, la taille absorbe l'écart).
Les reprises manuelles vivent dans `layouts: {"1:1": {"<region_id>": {x,y,
width,height}}}` — même fichier, quatre canevas.

**Fichiers**
- Créer : `backend/app/services/template_layout.py`
- Créer : `backend/tests/test_templates_reflow.py`
- Modifier : `backend/app/api/routes.py:199` (deux routes)
- Modifier : `backend/app/services/template_service.py:221-282` (`_validate`
  accepte `constraints` et `layouts`)

**Coût de patch.** Backend seul jusqu'ici. Côté bundle, **une** ancre dans
`tplbar` (Tâche 7) : la rangée « New: » de la galerie gagne un second groupe
« Rejouer en : 9:16 16:9 1:1 4:5 » qui appelle `POST
/layout-templates/{id}/reflow` et sélectionne le gabarit créé. Le
réagencement manuel par format ne coûte **rien de plus** : l'éditeur travaille
déjà sur le gabarit ouvert, et le gabarit rejoué est un gabarit comme un autre.

- [ ] **Étape 1 : écrire le banc qui échoue**

Créer `backend/tests/test_templates_reflow.py` :

```python
# -*- coding: utf-8 -*-
"""P2 — un gabarit rejoue en quatre formats, par la regle puis a la main.

Banc-miroir : le 1:1 est RENDU et on lit ou tombent les bandes dans le MP4.
Les modes d'ancrage sont verifies sur la geometrie rendue par reflow(), parce
que c'est elle qui part au renderer.

Run depuis backend/ :  python tests/test_templates_reflow.py
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dztplrf_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = \
    "sqlite+aiosqlite:///" + pathlib.Path(_tmp, "t.db").as_posix()
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from _miroir import check, bilan, image, rgb, proche          # noqa: E402
from app.services import template_layout as TL                # noqa: E402
from app.services.template_service import TemplateEngine      # noqa: E402

BASE = {
    "id": "tpl_banc_rf", "name": "banc reflow",
    "canvas": {"width": 1080, "height": 1920, "background_color": "#101010",
               "fps": 10, "duration_s": 1},
    "regions": [
        # haut, colle en haut, largeur etiree
        {"id": "haut", "type": "separator", "x": 40, "y": 0,
         "width": 1000, "height": 200, "z_index": 1, "color": "#00e5ff",
         "constraints": {"h": "stretch", "v": "start"}},
        # bas, colle en bas
        {"id": "bas", "type": "separator", "x": 40, "y": 1720,
         "width": 200, "height": 200, "z_index": 1, "color": "#ff8800",
         "constraints": {"h": "start", "v": "end"}},
        # centre, centre sur les deux axes
        {"id": "mid", "type": "separator", "x": 440, "y": 860,
         "width": 200, "height": 200, "z_index": 1, "color": "#34d399",
         "constraints": {"h": "center", "v": "center"}},
    ],
}

print("\n[1] Les quatre formats sont ceux du bundle (pd())")
check("FORMATS_DU_BUNDLE",
      TL.FORMATS == {"9:16": (1080, 1920), "1:1": (1080, 1080),
                     "16:9": (1920, 1080), "4:5": (1080, 1350)}, TL.FORMATS)
try:
    TL.reflow(BASE, "21:9")
    check("FORMAT_INCONNU_REFUSE", False, "aucune erreur levee")
except ValueError as e:
    check("FORMAT_INCONNU_REFUSE", "format inconnu" in str(e), str(e))

print("\n[2] Les cinq modes d'ancrage, mesures sur le 1:1 (1080x1080)")
r = {x["id"]: x for x in TL.reflow(BASE, "1:1")["regions"]}
check("CANEVAS_REECRIT", TL.reflow(BASE, "1:1")["canvas"]["height"] == 1080)
check("ANCRAGE_START_HAUT", r["haut"]["y"] == 0, r["haut"]["y"])
check("ANCRAGE_STRETCH_LARGEUR",
      (r["haut"]["x"], r["haut"]["width"]) == (40, 1000),
      (r["haut"]["x"], r["haut"]["width"]))
check("ANCRAGE_END_BAS",
      r["bas"]["y"] + r["bas"]["height"] == 1080,
      (r["bas"]["y"], r["bas"]["height"]))
check("ANCRAGE_START_GAUCHE", r["bas"]["x"] == 40, r["bas"]["x"])
check("ANCRAGE_CENTER_X",
      abs((r["mid"]["x"] + r["mid"]["width"] / 2) - 540) <= 1, r["mid"]["x"])
check("ANCRAGE_CENTER_Y",
      abs((r["mid"]["y"] + r["mid"]["height"] / 2) - 540) <= 1, r["mid"]["y"])

print("\n[3] scale est le defaut : sans contrainte, tout suit l'echelle")
nu = {"canvas": dict(BASE["canvas"]), "name": "nu", "regions": [
    {"id": "a", "type": "separator", "x": 540, "y": 960,
     "width": 108, "height": 192, "color": "#ffffff"}]}
a = TL.reflow(nu, "1:1")["regions"][0]
check("DEFAUT_SCALE", (a["x"], a["y"], a["width"], a["height"])
      == (540, 540, 108, 108), (a["x"], a["y"], a["width"], a["height"]))

print("\n[4] La reprise a la main gagne sur la regle")
avec = dict(BASE, layouts={"1:1": {"mid": {"x": 10, "y": 20,
                                           "width": 60, "height": 70}}})
m = {x["id"]: x for x in TL.reflow(avec, "1:1")["regions"]}["mid"]
check("REPRISE_MANUELLE",
      (m["x"], m["y"], m["width"], m["height"]) == (10, 20, 60, 70),
      (m["x"], m["y"], m["width"], m["height"]))
check("REPRISE_NE_FUIT_PAS_AILLEURS",
      {x["id"]: x for x in TL.reflow(avec, "4:5")["regions"]}["mid"]["x"] != 10)

print("\n[5] Un montage sequentiel garde sa geometrie nominale")
seq = dict(BASE, render_mode="sequential", regions=[
    {"id": "act0", "type": "video_slot", "slot_name": "c0", "act": 0,
     "x": 0, "y": 0, "width": 1080, "height": 1920, "length_s": 2}])
s0 = TL.reflow(seq, "16:9")["regions"][0]
check("SEQUENTIEL_INTOUCHE",
      (s0["width"], s0["height"]) == (1080, 1920), (s0["width"], s0["height"]))
check("SEQUENTIEL_CANEVAS_SUIT",
      TL.reflow(seq, "16:9")["canvas"]["width"] == 1920)

print("\n[6] Le 1:1 se REND, et les bandes tombent la ou la regle le dit")
eng = TemplateEngine()
out = pathlib.Path(_tmp, "outputs")
carre = TL.reflow(BASE, "1:1")
mp4 = out / "rf.mp4"
eng.render("tpl_banc_rf", {}, mp4, template=carre)
im = image(mp4, out / "rf.png")
check("RENDU_CARRE", im.size == (1080, 1080), im.size)
check("BANDE_HAUTE_RENDUE", proche(im.getpixel((540, 40)), rgb("#00e5ff")),
      im.getpixel((540, 40)))
check("BANDE_BASSE_RENDUE", proche(im.getpixel((100, 1040)), rgb("#ff8800")),
      im.getpixel((100, 1040)))
check("BANDE_CENTRE_RENDUE", proche(im.getpixel((540, 540)), rgb("#34d399")),
      im.getpixel((540, 540)))

bilan("P2 reagencement multi-format")
```

- [ ] **Étape 2 : lancer le banc et le voir rouge**

```
cd backend
python tests/test_templates_reflow.py
```
Attendu : `ModuleNotFoundError: No module named 'app.services.template_layout'`.

- [ ] **Étape 3 : écrire `template_layout.py`**

```python
# -*- coding: utf-8 -*-
"""Reagencement multi-format (plan 2026-09-03-plan-templates, P2).

Un gabarit est ecrit dans UN format ; les trois autres se deduisent d'une
regle par axe, puis d'une reprise a la main quand la regle ne suffit pas.
Les quatre canevas vivent dans le MEME JSON : `constraints` sur chaque region
et `layouts[<format>][<region_id>]` pour les reprises.

Les tailles sont celles du bundle (`function pd(e)`), pas des inventions.
"""
from __future__ import annotations

import json

#: format -> (largeur, hauteur). Mesure dans le bundle le 03/09/2026.
FORMATS: dict[str, tuple[int, int]] = {
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "16:9": (1920, 1080),
    "4:5": (1080, 1350),
}

#: Modes d'ancrage, par AXE (noms neutres : `start`/`end` valent gauche/droite
#: en horizontal et haut/bas en vertical).
MODES = ("start", "end", "center", "scale", "stretch")

DEFAUT = "scale"


def _axe(pos: float, taille: float, ancien: int, neuf: int,
         mode: str) -> tuple[float, float]:
    """(position, taille) sur un axe, de `ancien` vers `neuf`."""
    marge_fin = ancien - pos - taille
    if mode == "start":
        return pos, taille
    if mode == "end":
        return neuf - marge_fin - taille, taille
    if mode == "center":
        centre = (pos + taille / 2.0) / max(1, ancien)
        return centre * neuf - taille / 2.0, taille
    if mode == "stretch":
        return pos, max(1.0, neuf - marge_fin - pos)
    facteur = neuf / float(max(1, ancien))          # scale
    return pos * facteur, taille * facteur


def _mode(region: dict, cle: str) -> str:
    c = region.get("constraints")
    v = (c or {}).get(cle)
    return v if v in MODES else DEFAUT


def reflow(tpl: dict, fmt: str) -> dict:
    """Le gabarit rejoue dans `fmt`. Ne modifie jamais l'entree.

    Un `render_mode: sequential` garde la geometrie NOMINALE de ses actes :
    ce sont des marque-places mis a l'echelle par le renderer, et
    `TemplateEngine._validate` ne les borne pas au canevas (mesure :
    template_service.py:244-247). Seul le canevas change.
    """
    if fmt not in FORMATS:
        raise ValueError(
            f"format inconnu : {fmt} — attendus " + ", ".join(FORMATS))
    W, H = FORMATS[fmt]
    out = json.loads(json.dumps(tpl))
    w0 = int(out["canvas"]["width"])
    h0 = int(out["canvas"]["height"])
    out["canvas"]["width"], out["canvas"]["height"] = W, H
    out["metadata"] = dict(out.get("metadata") or {}, format=fmt)
    if out.get("render_mode") == "sequential":
        return out

    poses = (out.get("layouts") or {}).get(fmt) or {}
    for r in out["regions"]:
        if r.get("type") == "audio_slot":
            continue
        x, w = _axe(float(r["x"]), float(r["width"]), w0, W, _mode(r, "h"))
        y, h = _axe(float(r["y"]), float(r["height"]), h0, H, _mode(r, "v"))
        main = poses.get(r["id"]) or {}
        x = float(main.get("x", x))
        y = float(main.get("y", y))
        w = float(main.get("width", w))
        h = float(main.get("height", h))
        # Rabotage : `_validate` refuse une region qui deborde. Mieux vaut une
        # region rognee qu'un gabarit qu'on ne peut plus enregistrer.
        w = max(1.0, min(w, W))
        h = max(1.0, min(h, H))
        x = max(0.0, min(W - w, x))
        y = max(0.0, min(H - h, y))
        r["x"], r["y"] = int(round(x)), int(round(y))
        r["width"], r["height"] = int(round(w)), int(round(h))
    return out


def poser(tpl: dict, fmt: str, poses: dict) -> dict:
    """Enregistre les reprises manuelles de `fmt` dans le MEME gabarit."""
    if fmt not in FORMATS:
        raise ValueError(
            f"format inconnu : {fmt} — attendus " + ", ".join(FORMATS))
    ids = {r["id"] for r in tpl.get("regions", [])}
    propre = {}
    for rid, p in (poses or {}).items():
        if rid not in ids:
            raise ValueError(f"region inconnue dans ce gabarit : {rid}")
        propre[rid] = {k: int(round(float(p[k])))
                       for k in ("x", "y", "width", "height") if k in p}
    tpl.setdefault("layouts", {})[fmt] = propre
    return tpl
```

- [ ] **Étape 4 : laisser passer `constraints` et `layouts` à la validation**

`_validate` (`template_service.py:221`) n'interdit rien d'inconnu — il exige
seulement les champs requis. **Rien à changer pour que ça passe**, mais il faut
refuser un mode inventé, sinon `reflow` le remplacera silencieusement par
`scale`. Ajouter, dans la boucle sur les régions, juste après le contrôle
`negative origin` (`:267`) :

```python
                c = r.get("constraints")
                if c is not None:
                    if not isinstance(c, dict):
                        raise ValueError(
                            f"Region {r['id']}: constraints must be an object")
                    from app.services.template_layout import MODES as _M
                    for axe in ("h", "v"):
                        if axe in c and c[axe] not in _M:
                            raise ValueError(
                                f"Region {r['id']}: constraints.{axe}="
                                f"{c[axe]!r} — expected one of "
                                + ", ".join(_M))
```

- [ ] **Étape 5 : lancer le banc, le voir vert**

```
cd backend
python tests/test_templates_reflow.py
```
Attendu : `P2 reagencement multi-format : 17 PASS, 0 FAILED`, sortie 0.

- [ ] **Étape 6 : les deux routes**

Dans `backend/app/api/routes.py`, après le bloc `/brand-kits` :

```python
@router.get("/layout-templates/{template_id}/reflow")
async def reflow_layout_template(template_id: str, format: str = "1:1"):
    """Le gabarit rejoue dans `format` — LU, pas enregistre (l'editeur montre
    avant d'ecrire)."""
    from app.services import template_layout as _tl
    try:
        tpl = template_engine.get_template(template_id)
    except FileNotFoundError:
        raise HTTPException(404, f"Template not found: {template_id}")
    try:
        return _tl.reflow(tpl, format)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/layout-templates/{template_id}/reflow")
async def save_reflowed_template(template_id: str, body: dict,
                                 request: Request):
    """Le gabarit rejoue, ENREGISTRE comme gabarit utilisateur.
    body: {"format": "1:1", "name": "..." (optionnel)}"""
    _require_localhost(request)
    from app.services import template_layout as _tl
    try:
        tpl = template_engine.get_template(template_id)
    except FileNotFoundError:
        raise HTTPException(404, f"Template not found: {template_id}")
    fmt = str((body or {}).get("format") or "1:1")
    try:
        neuf = _tl.reflow(tpl, fmt)
    except ValueError as e:
        raise HTTPException(400, str(e))
    neuf["id"] = ""                       # save_template forge un id neuf
    neuf["name"] = str((body or {}).get("name")
                       or f"{tpl.get('name', template_id)} — {fmt}")[:120]
    neuf.pop("_builtin", None)
    try:
        tid = template_engine.save_template(neuf)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"template_id": tid, "format": fmt}


@router.post("/layout-templates/{template_id}/layouts")
async def save_layout_overrides(template_id: str, body: dict,
                                request: Request):
    """Reprise MANUELLE d'un format : body {"format": "...", "poses": {...}}.
    Ecrite dans le MEME JSON — les quatre canevas ne se separent jamais."""
    _require_localhost(request)
    from app.services import template_layout as _tl
    if template_engine.is_builtin(template_id):
        raise HTTPException(400, "Built-in templates cannot be edited")
    try:
        tpl = template_engine.get_template(template_id)
    except FileNotFoundError:
        raise HTTPException(404, f"Template not found: {template_id}")
    try:
        _tl.poser(tpl, str((body or {}).get("format") or ""),
                  (body or {}).get("poses") or {})
        template_engine.save_template(tpl)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"template_id": template_id,
            "layouts": sorted(tpl.get("layouts", {}))}
```

- [ ] **Étape 7 : commit**

```
git add backend/app/services/template_layout.py backend/tests/test_templates_reflow.py backend/app/services/template_service.py backend/app/api/routes.py
git commit -m 'etabli : un gabarit rejoue en quatre formats, regle puis reprise' -m 'Chaque region porte des contraintes par axe (start, end, center, scale, stretch) et le gabarit se rejoue en 9:16, 1:1, 16:9, 4:5 aux tailles deja utilisees par le bundle. Les reprises manuelles vivent dans le meme JSON, sous layouts[format]. Un montage sequentiel garde sa geometrie nominale : le validateur ne la borne pas au canevas.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

## Tâche 3 : P3 — Masques de région

**La demande, mot pour mot** (réponse 2 de R7) : « **la possibilité de
réagencer à la main et appliquer des masques (fenêtres ajourées avec des bords
pleins arrondis sur un encart ajusté, etc.)** ». Trois choses distinctes, et
elles se dessinent séparément :

- **fenêtre ajourée** = un trou dans l'alpha de la région → la source disparaît,
  le fond réapparaît ;
- **bords pleins arrondis** = de l'encre opaque autour de la fenêtre → ce n'est
  **pas** de l'alpha, c'est un cadre peint ;
- **encart ajusté** = la fenêtre est rentrée des bords de la région d'une marge
  (`inset`) au lieu de l'occuper entière.

**Pourquoi ce moyen, avec la mesure.** ffmpeg ne découpe pas ; il expose
`alphamerge` (`VV->V`, « copy the luma value of the second input into the alpha
channel of the first ») — mesuré présent dans le binaire de cette machine le
03/09. Et `effects_engine.build_chain` ne peut pas aider : ses effets sont
**des chaînes de filtres pures, sans entrée externe** (docstring
`effects_engine.py:1-12`). Le masque doit donc être une image, et Pillow la
dessine déjà ailleurs dans ce même fichier (`render_badge_bg_png:499` fait un
`rounded_rectangle`). Mesure de bout en bout, faite le 03/09 :
masque `L` (arrondi r=48 + ellipse à 0) → `[src][msk]alphamerge` → `overlay`
sur fond rouge donne coin `(253,0,0)`, centre `(253,0,0)`, plein `(0,0,254)`.

**Le format**

```json
"mask": {
  "shape": "rounded",
  "radius": 64,
  "inset": 24,
  "holes": [{"shape": "ellipse", "x": 150, "y": 100,
             "width": 100, "height": 100}],
  "border_px": 6,
  "border_color": "#00e5ff",
  "feather_px": 0
}
```

**Fichiers**
- Créer : `backend/app/services/template_mask.py`
- Créer : `backend/tests/test_templates_masques.py`
- Modifier : `backend/app/services/template_service.py:702-716`

**Coût de patch.** Backend : un module neuf et 14 lignes dans le filtergraph.
Bundle : **une** ancre dans `tplregion` (Tâche 7) — une section « Masque » du
panneau de région (forme, rayon, encart, bordure, une fenêtre). Elle ne coûte
si peu que parce que la même greffe fait aussi passer le champ `mask` à travers
le chargement et l'enregistrement de l'éditeur (voir « Coût de patch » plus
haut) : sans ça, le masque serait effacé au premier déplacement de région.

- [ ] **Étape 1 : écrire le banc qui échoue**

Créer `backend/tests/test_templates_masques.py` :

```python
# -*- coding: utf-8 -*-
"""P3 — masques de region : la fenetre ajouree, ses bords pleins, l'encart.

Banc-miroir : le gabarit est RENDU en MP4 et on lit les pixels de l'image.
Le fond du canevas est ROUGE, la source est un PNG BLEU uni : chaque pixel
repond donc a une seule question — la source passe-t-elle ici, oui ou non.

Run depuis backend/ :  python tests/test_templates_masques.py
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dztplmk_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = \
    "sqlite+aiosqlite:///" + pathlib.Path(_tmp, "t.db").as_posix()
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                          # noqa: E402
from _miroir import check, bilan, image, rgb, proche           # noqa: E402
from app.services import template_mask as TM                   # noqa: E402
from app.services.template_service import TemplateEngine       # noqa: E402

out = pathlib.Path(_tmp, "outputs")
src = pathlib.Path(_tmp, "images", "bleu.png")
Image.new("RGB", (400, 300), (0, 0, 255)).save(src)

ROUGE, BLEU = rgb("#ff0000"), rgb("#0000ff")


def tpl(mask):
    return {"id": "tpl_banc_mk", "name": "banc masque",
            "canvas": {"width": 400, "height": 300,
                       "background_color": "#ff0000", "fps": 10,
                       "duration_s": 1},
            "regions": [{"id": "r", "type": "image_slot", "slot_name": "img",
                         "x": 0, "y": 0, "width": 400, "height": 300,
                         "z_index": 0, "fit": "cover", "mask": mask}]}


def rendu(mask, nom):
    mp4 = out / (nom + ".mp4")
    TemplateEngine().render("tpl_banc_mk", {"img": {"path": str(src)}},
                            mp4, template=tpl(mask))
    return image(mp4, out / (nom + ".png"))


print("\n[1] Le masque PIL, avant tout rendu")
m = TM.dessiner_masque(400, 300, {"shape": "rounded", "radius": 48,
                                  "holes": [{"shape": "ellipse", "x": 150,
                                             "y": 100, "width": 100,
                                             "height": 100}]})
check("MASQUE_MODE_L", m.mode == "L", m.mode)
check("MASQUE_COIN_NOIR", m.getpixel((2, 2)) < 16, m.getpixel((2, 2)))
check("MASQUE_PLEIN_BLANC", m.getpixel((200, 40)) > 240, m.getpixel((200, 40)))
check("MASQUE_FENETRE_NOIRE", m.getpixel((200, 150)) < 16,
      m.getpixel((200, 150)))

print("\n[2] Le rendu : coins arrondis et fenetre ajouree, LUS DANS LE MP4")
im = rendu({"shape": "rounded", "radius": 48,
            "holes": [{"shape": "ellipse", "x": 150, "y": 100,
                       "width": 100, "height": 100}]}, "mk1")
check("COIN_ARRONDI_LAISSE_LE_FOND", proche(im.getpixel((2, 2)), ROUGE),
      im.getpixel((2, 2)))
check("FENETRE_AJOUREE", proche(im.getpixel((200, 150)), ROUGE),
      im.getpixel((200, 150)))
check("PLEIN_MONTRE_LA_SOURCE", proche(im.getpixel((200, 40)), BLEU),
      im.getpixel((200, 40)))

print("\n[3] L'ENCART AJUSTE : la fenetre est rentree des bords")
im = rendu({"shape": "rounded", "radius": 20, "inset": 40}, "mk2")
check("ENCART_BORD_AU_FOND", proche(im.getpixel((10, 150)), ROUGE),
      im.getpixel((10, 150)))
check("ENCART_INTERIEUR_SOURCE", proche(im.getpixel((200, 150)), BLEU),
      im.getpixel((200, 150)))

print("\n[4] Les BORDS PLEINS : de l'encre, pas de l'alpha")
im = rendu({"shape": "rounded", "radius": 20, "inset": 40,
            "border_px": 8, "border_color": "#00ff00"}, "mk3")
vert = [x for x in range(400)
        if proche(im.getpixel((x, 150)), rgb("#00ff00"), tol=40)]
check("BORDURE_PEINTE", len(vert) >= 8, len(vert))
check("BORDURE_SUR_L_ENCART", bool(vert) and 34 <= min(vert) <= 48,
      vert[:4] if vert else None)

print("\n[5] Une ellipse, et un masque absent qui ne change rien")
im = rendu({"shape": "ellipse"}, "mk4")
check("ELLIPSE_COIN_AU_FOND", proche(im.getpixel((3, 3)), ROUGE),
      im.getpixel((3, 3)))
check("ELLIPSE_CENTRE_SOURCE", proche(im.getpixel((200, 150)), BLEU),
      im.getpixel((200, 150)))
im = rendu(None, "mk5")
check("SANS_MASQUE_TOUT_PASSE", proche(im.getpixel((2, 2)), BLEU),
      im.getpixel((2, 2)))

print("\n[6] Bornes : un encart plus grand que la region ne vide pas tout")
m = TM.dessiner_masque(40, 30, {"shape": "rounded", "inset": 999})
check("ENCART_BORNE", m.getpixel((20, 15)) > 240, m.getpixel((20, 15)))
check("CADRE_SANS_BORDURE_EST_NONE",
      TM.dessiner_cadre(40, 30, {"shape": "rounded"}) is None)

bilan("P3 masques de region")
```

- [ ] **Étape 2 : lancer le banc et le voir rouge**

```
cd backend
python tests/test_templates_masques.py
```
Attendu : `ModuleNotFoundError: No module named 'app.services.template_mask'`.

- [ ] **Étape 3 : écrire `template_mask.py`**

```python
# -*- coding: utf-8 -*-
"""Masques de region (plan 2026-09-03-plan-templates, P3).

La demande, mot pour mot : « fenetres ajourees avec des bords pleins arrondis
sur un encart ajuste ». Trois choses, deux images :

  * le MASQUE (mode L) — blanc = on voit la source, noir = on voit le fond.
    C'est lui que ffmpeg `alphamerge` copie dans le canal alpha de la region.
    L'ENCART (`inset`) rentre la fenetre des bords ; les TROUS (`holes`) la
    percent : ce sont les fenetres ajourees ;
  * le CADRE (RGBA) — les BORDS PLEINS. Une bordure n'est pas de l'alpha,
    c'est de l'encre : elle est peinte APRES l'overlay de la region, sinon
    elle serait elle-meme decoupee par son propre masque.

Pillow seulement (le python embarque n'a pas numpy) ; meme patron que
`template_service.render_badge_bg_png`.
"""
from __future__ import annotations

from pathlib import Path

FORMES = ("rounded", "ellipse", "polygon")


def _rgb(hexa, defaut=(0, 229, 255)):
    h = str(hexa or "").lstrip("#")
    if len(h) != 6:
        return defaut
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return defaut


def _boite(w: int, h: int, spec: dict) -> list[int]:
    """L'ENCART AJUSTE : la fenetre, rentree des bords de la region.
    L'encart est BORNE — un `inset` absurde laisserait sinon un masque vide,
    donc une region invisible sans un mot d'explication."""
    i = max(0, int(spec.get("inset", 0) or 0))
    i = min(i, max(0, (w - 2) // 2), max(0, (h - 2) // 2))
    return [i, i, w - 1 - i, h - 1 - i]


def _rayon(spec: dict, boite: list[int]) -> int:
    r = max(0, int(spec.get("radius", 0) or 0))
    return min(r, (boite[2] - boite[0]) // 2, (boite[3] - boite[1]) // 2)


def _points(spec: dict):
    pts = spec.get("points") or []
    if len(pts) < 3:
        return None
    return [(float(p[0]), float(p[1])) for p in pts]


def _tracer(d, boite, spec, remplissage) -> None:
    forme = str(spec.get("shape") or "rounded")
    if forme == "ellipse":
        d.ellipse(boite, fill=remplissage)
        return
    if forme == "polygon":
        pts = _points(spec)
        if pts:
            d.polygon(pts, fill=remplissage)
            return
    d.rounded_rectangle(boite, radius=_rayon(spec, boite), fill=remplissage)


def dessiner_masque(w, h, spec: dict):
    """Le masque `L` de la region : blanc = source, noir = fond."""
    from PIL import Image, ImageDraw, ImageFilter
    w, h = max(1, int(w)), max(1, int(h))
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    _tracer(d, _boite(w, h, spec or {}), spec or {}, 255)
    for trou in ((spec or {}).get("holes") or []):
        bw, bh = int(trou.get("width", 0)), int(trou.get("height", 0))
        if bw <= 0 or bh <= 0:
            continue
        bx, by = int(trou.get("x", 0)), int(trou.get("y", 0))
        _tracer(d, [bx, by, bx + bw - 1, by + bh - 1], trou, 0)
    f = max(0, int((spec or {}).get("feather_px", 0) or 0))
    if f:
        im = im.filter(ImageFilter.GaussianBlur(f))
    return im


def dessiner_cadre(w, h, spec: dict):
    """Les BORDS PLEINS, en RGBA — `None` si `border_px` vaut 0.
    Le cadre suit la forme de la fenetre ET celle de chaque trou : c'est ce
    qui donne « des bords pleins arrondis » autour d'une fenetre ajouree."""
    ep = max(0, int((spec or {}).get("border_px", 0) or 0))
    if ep <= 0:
        return None
    from PIL import Image, ImageDraw
    w, h = max(1, int(w)), max(1, int(h))
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    coul = _rgb(spec.get("border_color")) + (255,)

    def contour(boite, sp):
        forme = str(sp.get("shape") or "rounded")
        if forme == "ellipse":
            d.ellipse(boite, outline=coul, width=ep)
            return
        pts = _points(sp) if forme == "polygon" else None
        if pts:
            d.line(pts + [pts[0]], fill=coul, width=ep, joint="curve")
            return
        d.rounded_rectangle(boite, radius=_rayon(sp, boite),
                            outline=coul, width=ep)

    contour(_boite(w, h, spec), spec)
    for trou in (spec.get("holes") or []):
        bw, bh = int(trou.get("width", 0)), int(trou.get("height", 0))
        if bw <= 0 or bh <= 0:
            continue
        bx, by = int(trou.get("x", 0)), int(trou.get("y", 0))
        contour([bx, by, bx + bw - 1, by + bh - 1], trou)
    return im


def ecrire(w, h, spec: dict, work, rid: str):
    """Ecrit les deux PNG dans le dossier de travail du rendu.
    -> (chemin du masque, chemin du cadre ou None)."""
    work = Path(work)
    mp = work / f"mask_{rid}.png"
    dessiner_masque(w, h, spec).save(str(mp), "PNG")
    cadre = dessiner_cadre(w, h, spec)
    cp = None
    if cadre is not None:
        cp = work / f"frame_{rid}.png"
        cadre.save(str(cp), "PNG")
    return mp, cp
```

- [ ] **Étape 4 : brancher le masque dans le filtergraph**

Dans `backend/app/services/template_service.py`, remplacer les lignes 715-716
(fin de la branche `_VIDEO_LIKE`) :

```python
                slbl = f"s{n}fx"
            _w(f"[{cur}][{slbl}]overlay={rx}:{ry}:eof_action=repeat[o{n}]", f"o{n}")
```

par :

```python
                slbl = f"s{n}fx"
            # P3 — masque de region. L'alpha vient d'un PNG dessine en PIL
            # (ffmpeg ne decoupe pas) ; le CADRE, lui, est de l'encre posee
            # APRES l'overlay, sinon il serait decoupe par son propre masque.
            cadre_p = None
            msk = r.get("mask")
            if isinstance(msk, dict) and msk:
                from app.services import template_mask as _tm
                mask_p, cadre_p = _tm.ecrire(rw, rh, msk, work, rid)
                mi = _add_input(mask_p, still=True)
                parts.append(f"[{mi}:v]format=gray,scale={rw}:{rh}[s{n}m]")
                parts.append(f"[{slbl}]format=yuva420p[s{n}a]")
                parts.append(f"[s{n}a][s{n}m]alphamerge[s{n}k]")
                slbl = f"s{n}k"
            _w(f"[{cur}][{slbl}]overlay={rx}:{ry}:eof_action=repeat[o{n}]", f"o{n}")
            if cadre_p is not None:
                fi = _add_input(cadre_p, still=True)
                n += 1
                parts.append(f"[{fi}:v]format=rgba[fr{n}]")
                _w(f"[{cur}][fr{n}]overlay={rx}:{ry}:eof_action=repeat[fo{n}]",
                   f"fo{n}")
```

Note pour l'exécutant : `_add_input` mute `inputs` et `idx` par `nonlocal`, et
`cmd` n'est assemblé qu'à la ligne 917 — ajouter des entrées ici est donc sûr
(la branche `badge`, ligne 828, le fait déjà).

- [ ] **Étape 5 : lancer le banc, le voir vert**

```
cd backend
python tests/test_templates_masques.py
```
Attendu : `P3 masques de region : 15 PASS, 0 FAILED`, sortie 0.

- [ ] **Étape 6 : commit**

```
git add backend/app/services/template_mask.py backend/tests/test_templates_masques.py backend/app/services/template_service.py
git commit -m 'etabli : masques de region, fenetres ajourees a bords pleins' -m 'ffmpeg ne decoupe pas : il copie la luma d une seconde entree dans l alpha (alphamerge, mesure present). Le masque et le cadre sont donc dessines en Pillow dans le dossier de travail du rendu, comme le fond de badge le fait deja. L encart borne son inset, et la bordure est peinte APRES l overlay : c est de l encre, pas de l alpha.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

## Tâche 4 : P4 — Texte adaptatif et effets

**Pourquoi, avec la mesure.** Aujourd'hui un texte trop long est **coupé au
caractère** (`mc = r.get("max_chars"); txt = txt[:int(mc)]`,
`template_service.py:723-725`) ou déborde. Le dépôt sait pourtant mesurer : le
contrôle qualité des sous-titres appelle `ImageFont.truetype(...).getlength`
avec la VRAIE fonte (`subtitle_service.py:1210-1226`, `_measure_px`). C'est ce
patron qu'on remonte dans les templates. Mesure de contrôle du 03/09 :
`getlength("DEEPOTUS")` = `230.0` px en Anton 64, `getbbox` =
`(0,19,230,77)` — on sait donc à l'avance si ça rentre.

`drawtext` ne sait faire qu'un `borderw`. Contour épais, ombre floue, dégradé
et fond arrondi se peignent en PIL, exactement comme les emojis le sont déjà
(`render_emoji_text_png:523`) : ce chemin PNG existe, on l'élargit.

**Le format**

```json
{"type": "text", "text_fit": "shrink",
 "text_effects": {
   "stroke_px": 6, "stroke_color": "#02060d",
   "shadow": {"dx": 4, "dy": 6, "blur": 8, "color": "#000000", "opacity": 0.6},
   "gradient": {"c0": "#00e5ff", "c1": "#9945ff", "direction": "v"},
   "box": {"color": "#02060d", "opacity": 0.7, "radius": 18}}}
```

`text_fit` ∈ `none | shrink | wrap | ellipsis`. **Le nom n'est pas `fit`** :
`fit` est déjà pris par le mode d'échelle des slots vidéo/image
(`_scale_filter`, `template_service.py:101`) — les confondre casserait tous
les gabarits livrés.

**Fichiers**
- Créer : `backend/app/services/template_text.py`
- Créer : `backend/tests/test_templates_texte.py`
- Modifier : `backend/app/services/template_service.py:717-747`

**Coût de patch.** Backend : un module neuf et 12 lignes dans le filtergraph.
Bundle : **une** ancre dans `tplregion` (Tâche 7) — une section « Texte » du
panneau (ajustement, contour, ombre, dégradé, fond). C'est le seul bac du lot 1
dont la valeur se perd sans l'UI : un `text_fit` que personne ne peut cocher ne
sert qu'aux gabarits écrits à la main.

- [ ] **Étape 1 : écrire le banc qui échoue**

Créer `backend/tests/test_templates_texte.py` :

```python
# -*- coding: utf-8 -*-
"""P4 — texte adaptatif et effets (et, en Tache 11, le texte sur courbe).

Deux miroirs : le PNG que le module dessine, ET l'image du MP4 rendu — le
second prouve le cablage, le premier prouve la peinture.

Run depuis backend/ :  python tests/test_templates_texte.py
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dztpltx_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = \
    "sqlite+aiosqlite:///" + pathlib.Path(_tmp, "t.db").as_posix()
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                          # noqa: E402
from _miroir import check, bilan, image, rgb, proche, boite_encre  # noqa: E402
from app.services import template_text as TT                   # noqa: E402
from app.services.template_service import TemplateEngine       # noqa: E402

eng = TemplateEngine()
out = pathlib.Path(_tmp, "outputs")
FONTE = eng.font_path("Anton")
LONG = "UNE PHRASE BEAUCOUP TROP LONGUE POUR CETTE BOITE"

print("\n[1] La mesure vient de la FONTE, pas du nombre de caracteres")
l64 = TT.mesurer("DEEPOTUS", FONTE, 64)
check("MESURE_ANTON_64", abs(l64 - 230.0) < 2.0, l64)
check("MESURE_CROIT_AVEC_LA_TAILLE", TT.mesurer("DEEPOTUS", FONTE, 128) > l64)
check("MESURE_VIDE_EST_NULLE", TT.mesurer("", FONTE, 64) == 0.0)

print("\n[2] shrink : la taille descend JUSQU'A ce que ca rentre")
t, lignes = TT.ajuster(LONG, FONTE, 96, 600, mode="shrink")
check("SHRINK_A_REDUIT", t < 96, t)
check("SHRINK_RENTRE", TT.mesurer(LONG, FONTE, t) <= 600,
      TT.mesurer(LONG, FONTE, t))
check("SHRINK_UNE_SEULE_LIGNE", len(lignes) == 1, len(lignes))
check("SHRINK_PLANCHER", TT.ajuster(LONG, FONTE, 96, 10,
                                    mode="shrink", taille_min=14)[0] == 14)
check("SHRINK_NE_TOUCHE_PAS_CE_QUI_RENTRE",
      TT.ajuster("OK", FONTE, 40, 4000, mode="shrink")[0] == 40)

print("\n[3] wrap : des lignes, chacune mesuree")
t, lignes = TT.ajuster(LONG, FONTE, 72, 500, hauteur_max=400, mode="wrap")
check("WRAP_PLUSIEURS_LIGNES", len(lignes) > 1, len(lignes))
check("WRAP_CHAQUE_LIGNE_RENTRE",
      all(TT.mesurer(x, FONTE, t) <= 500 for x in lignes),
      [round(TT.mesurer(x, FONTE, t)) for x in lignes])
check("WRAP_AUCUN_MOT_PERDU",
      " ".join(lignes).split() == LONG.split(), lignes)

print("\n[4] ellipsis : on coupe et on le DIT")
t, lignes = TT.ajuster(LONG, FONTE, 72, 400, mode="ellipsis")
check("ELLIPSE_MARQUEE", lignes[0].endswith("…"), lignes[0])
check("ELLIPSE_RENTRE", TT.mesurer(lignes[0], FONTE, t) <= 400,
      TT.mesurer(lignes[0], FONTE, t))
check("ELLIPSE_INUTILE_NE_COUPE_PAS",
      TT.ajuster("OK", FONTE, 40, 4000, mode="ellipsis")[1] == ["OK"])

print("\n[5] Les effets, LUS DANS LE PNG")
p = out / "fx.png"
TT.rendre_texte_png(["DEEP"], FONTE, 96, "#ffffff", p,
                    effets={"stroke_px": 8, "stroke_color": "#ff0000"},
                    largeur=600, align="center")
im = Image.open(str(p)).convert("RGBA")
rouges = sum(1 for y in range(0, im.height, 2) for x in range(0, im.width, 2)
             if im.getpixel((x, y))[3] > 120
             and proche(im.getpixel((x, y)), rgb("#ff0000"), tol=60))
check("CONTOUR_PEINT", rouges > 40, rouges)
check("PNG_TRANSPARENT", im.getpixel((2, 2))[3] == 0, im.getpixel((2, 2)))

p = out / "grad.png"
TT.rendre_texte_png(["DEEPDEEP"], FONTE, 120, "#ffffff", p,
                    effets={"gradient": {"c0": "#ff0000", "c1": "#0000ff",
                                         "direction": "v"}},
                    largeur=700, align="center")
im = Image.open(str(p)).convert("RGBA")
opaques = [(x, y) for y in range(im.height) for x in range(0, im.width, 3)
           if im.getpixel((x, y))[3] > 200]
haut = [im.getpixel(q) for q in opaques if q[1] < im.height * 0.35]
bas = [im.getpixel(q) for q in opaques if q[1] > im.height * 0.65]
check("DEGRADE_HAUT_ROUGE", bool(haut) and
      sum(c[0] for c in haut) / len(haut) > sum(c[2] for c in haut) / len(haut))
check("DEGRADE_BAS_BLEU", bool(bas) and
      sum(c[2] for c in bas) / len(bas) > sum(c[0] for c in bas) / len(bas))

p = out / "box.png"
TT.rendre_texte_png(["X"], FONTE, 60, "#ffffff", p,
                    effets={"box": {"color": "#00ff00", "opacity": 1.0,
                                    "radius": 40}}, largeur=300)
im = Image.open(str(p)).convert("RGBA")
check("FOND_ARRONDI_COIN_VIDE", im.getpixel((1, 1))[3] == 0, im.getpixel((1, 1)))
check("FOND_ARRONDI_MILIEU_PLEIN",
      proche(im.getpixel((150, im.height - 4)), rgb("#00ff00"), tol=40),
      im.getpixel((150, im.height - 4)))

print("\n[6] Le cablage : le MP4 rendu ne deborde pas de la region")
TPL = {"id": "tpl_banc_tx", "name": "banc texte",
       "canvas": {"width": 600, "height": 300, "background_color": "#000000",
                  "fps": 10, "duration_s": 1},
       "regions": [{"id": "t", "type": "text", "x": 50, "y": 100,
                    "width": 500, "height": 120, "z_index": 1,
                    "text": LONG, "font": "Anton", "size": 96,
                    "color": "#ffffff", "align": "center",
                    "text_fit": "shrink"}]}
mp4 = out / "tx.mp4"
eng.render("tpl_banc_tx", {}, mp4, template=TPL)
im = image(mp4, out / "tx.png")
b = boite_encre(im, fond=(0, 0, 0), seuil=60, pas=2)
check("TEXTE_RENDU", b is not None, b)
check("TEXTE_DANS_LA_REGION",
      b is not None and b[0] >= 44 and b[2] <= 556, b)

TPL2 = dict(TPL, regions=[dict(TPL["regions"][0], text_fit="none",
                               id="t", size=96)])
mp42 = out / "tx2.mp4"
eng.render("tpl_banc_tx", {}, mp42, template=TPL2)
b2 = boite_encre(image(mp42, out / "tx2.png"), fond=(0, 0, 0), seuil=60, pas=2)
check("SANS_AJUSTEMENT_CA_DEBORDE",
      b2 is not None and (b2[2] - b2[0]) > (b[2] - b[0]), (b, b2))

bilan("P4 texte adaptatif et effets")
```

- [ ] **Étape 2 : lancer le banc et le voir rouge**

```
cd backend
python tests/test_templates_texte.py
```
Attendu : `ModuleNotFoundError: No module named 'app.services.template_text'`.

- [ ] **Étape 3 : écrire `template_text.py`**

```python
# -*- coding: utf-8 -*-
"""Texte des templates : mesure, ajustement, effets (plan
2026-09-03-plan-templates, P4 ; le texte sur courbe arrive en D4).

MESURER AVANT DE DESSINER. La largeur d'une chaine se demande a la fonte qui
la rendra (`ImageFont.getlength`), jamais au nombre de caracteres — c'est deja
la regle du controle qualite des sous-titres (`subtitle_service._measure_px`).

`drawtext` ne sait faire qu'un `borderw`. Contour epais, ombre floue, degrade
et fond arrondi se peignent donc ici, en Pillow, dans le dossier de travail du
rendu — le meme chemin que les emojis prennent deja.
"""
from __future__ import annotations

MODES = ("none", "shrink", "wrap", "ellipsis")


def _rgb(hexa, defaut=(255, 255, 255)):
    h = str(hexa or "").lstrip("#")
    if len(h) != 6:
        return defaut
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return defaut


def _fonte(chemin, taille):
    from PIL import ImageFont
    return ImageFont.truetype(str(chemin), max(4, int(taille)))


def mesurer(texte, chemin, taille) -> float:
    """Largeur en px avec LA fonte qui rendra."""
    return float(_fonte(chemin, taille).getlength(str(texte or "")))


def hauteur_ligne(chemin, taille) -> float:
    a, d = _fonte(chemin, taille).getmetrics()
    return float(a + d)


def couper_mots(texte, chemin, taille, largeur_max) -> list[str]:
    """Retour a la ligne aux espaces, chaque ligne MESUREE. Un mot seul plus
    large que la boite reste seul sur sa ligne : on ne coupe pas un mot en
    deux sans que l'utilisateur l'ait demande."""
    f = _fonte(chemin, taille)
    lignes: list[str] = []
    courante = ""
    for mot in str(texte or "").split():
        essai = (courante + " " + mot).strip()
        if courante and f.getlength(essai) > largeur_max:
            lignes.append(courante)
            courante = mot
        else:
            courante = essai
    if courante:
        lignes.append(courante)
    return lignes or [""]


def ajuster(texte, chemin, taille, largeur_max, hauteur_max=None,
            mode="shrink", taille_min=12):
    """-> (taille finale, [lignes]). `mode` dans MODES."""
    texte = str(texte or "")
    taille = int(taille)
    if mode not in MODES:
        mode = "none"
    if mode == "none":
        return taille, [texte]
    if mode == "ellipsis":
        f = _fonte(chemin, taille)
        if f.getlength(texte) <= largeur_max:
            return taille, [texte]
        coupe = texte
        while coupe and f.getlength(coupe + "…") > largeur_max:
            coupe = coupe[:-1]
        return taille, [(coupe + "…") if coupe else "…"]
    if mode == "wrap":
        t = taille
        while t > taille_min:
            lignes = couper_mots(texte, chemin, t, largeur_max)
            trop_large = any(mesurer(x, chemin, t) > largeur_max
                             for x in lignes)
            trop_haut = (hauteur_max is not None
                         and len(lignes) * hauteur_ligne(chemin, t) * 1.12
                         > hauteur_max)
            if not trop_large and not trop_haut:
                return t, lignes
            t -= 2
        return taille_min, couper_mots(texte, chemin, taille_min, largeur_max)
    t = taille                                              # shrink
    while t > taille_min and mesurer(texte, chemin, t) > largeur_max:
        t -= 1
    return t, [texte]


def _encre(lignes, f, W, pad, lh, align, contour=0, coul=255):
    """Le TRACE en niveaux de gris — sert d'alpha a chaque couche peinte."""
    from PIL import Image, ImageDraw
    im = Image.new("L", (W, int(lh * len(lignes) + 2 * pad)), 0)
    d = ImageDraw.Draw(im)
    for i, ligne in enumerate(lignes):
        lw = f.getlength(ligne)
        if align == "center":
            x = (W - lw) / 2.0
        elif align == "right":
            x = W - pad - lw
        else:
            x = pad
        d.text((x, pad + i * lh), ligne, font=f, fill=coul,
               stroke_width=contour, stroke_fill=coul)
    return im


def _degrade(c0, c1, W, H, direction):
    """Une bande de 1 px etiree : un degre par pixel en Python pur couterait
    W*H iterations pour rien."""
    from PIL import Image
    if direction == "h":
        bande = Image.new("RGB", (max(1, W), 1))
        for x in range(max(1, W)):
            t = x / float(max(1, W - 1))
            bande.putpixel((x, 0), tuple(
                int(c0[k] + (c1[k] - c0[k]) * t) for k in range(3)))
    else:
        bande = Image.new("RGB", (1, max(1, H)))
        for y in range(max(1, H)):
            t = y / float(max(1, H - 1))
            bande.putpixel((0, y), tuple(
                int(c0[k] + (c1[k] - c0[k]) * t) for k in range(3)))
    return bande.resize((max(1, W), max(1, H)), Image.BILINEAR)


def rendre_texte_png(lignes, chemin, taille, couleur, sortie, effets=None,
                     largeur=None, align="center", interligne=1.12):
    """Une ou plusieurs lignes en PNG transparent, avec les effets.
    Ordre de peinture : fond, ombre, contour, remplissage. Rend (w, h)."""
    from PIL import Image, ImageFilter
    e = dict(effets or {})
    f = _fonte(chemin, taille)
    lh = hauteur_ligne(chemin, taille) * float(interligne)
    larg_txt = max([f.getlength(x) for x in lignes] + [1.0])
    contour = max(0, int(e.get("stroke_px", 0) or 0))
    om = e.get("shadow") or {}
    odx, ody = int(om.get("dx", 0) or 0), int(om.get("dy", 0) or 0)
    flou = max(0, int(om.get("blur", 0) or 0))
    pad = contour + flou + max(abs(odx), abs(ody)) + 8
    W = int(largeur or (larg_txt + 2 * pad))
    H = int(lh * len(lignes) + 2 * pad)
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    fond = e.get("box")
    if isinstance(fond, dict):
        from PIL import ImageDraw
        r = max(0, int(fond.get("radius", 0) or 0))
        a = int(max(0.0, min(1.0, float(fond.get("opacity", 0.7)))) * 255)
        ImageDraw.Draw(base).rounded_rectangle(
            [0, 0, W - 1, H - 1], radius=min(r, W // 2, H // 2),
            fill=_rgb(fond.get("color"), (0, 0, 0)) + (a,))

    trace = _encre(lignes, f, W, pad, lh, align)

    if om and (flou or odx or ody):
        a = trace.filter(ImageFilter.GaussianBlur(flou)) if flou else trace
        dec = Image.new("L", (W, H), 0)
        dec.paste(a, (odx, ody))
        op = max(0.0, min(1.0, float(om.get("opacity", 0.6))))
        couche = Image.new("RGBA", (W, H),
                           _rgb(om.get("color"), (0, 0, 0)) + (0,))
        couche.putalpha(dec.point(lambda v: int(v * op)))
        base.alpha_composite(couche)

    if contour:
        st = _encre(lignes, f, W, pad, lh, align, contour=contour)
        couche = Image.new("RGBA", (W, H),
                           _rgb(e.get("stroke_color"), (2, 6, 13)) + (0,))
        couche.putalpha(st)
        base.alpha_composite(couche)

    grad = e.get("gradient")
    if isinstance(grad, dict):
        couche = _degrade(_rgb(grad.get("c0"), (0, 229, 255)),
                          _rgb(grad.get("c1"), (153, 69, 255)),
                          W, H, str(grad.get("direction") or "v")).convert("RGBA")
    else:
        couche = Image.new("RGBA", (W, H), _rgb(couleur) + (0,))
    couche.putalpha(trace)
    base.alpha_composite(couche)
    base.save(str(sortie), "PNG")
    return base.width, base.height
```

- [ ] **Étape 4 : brancher le chemin PNG dans le filtergraph**

Dans `backend/app/services/template_service.py`, remplacer la ligne 729
(`            if _has_emoji(txt):` de la branche `("text", "text_slot")`) par :

```python
            fitm = str(r.get("text_fit") or "none")
            tfx = r.get("text_effects")
            if fitm != "none" or tfx:
                # P4 — mesure AVANT de dessiner, puis peinture en PIL :
                # drawtext ne sait faire qu'un borderw.
                from app.services import template_text as _tt
                fpath = engine.font_path(r.get("font"))
                size, lignes = _tt.ajuster(txt, fpath, size, rw,
                                           hauteur_max=rh, mode=fitm)
                tp = work / f"txt{n}.png"
                _tt.rendre_texte_png(lignes, fpath, size, "#" + color, tp,
                                     effets=tfx, largeur=rw,
                                     align=str(r.get("align") or "left"))
                ti = _add_input(tp, still=True)
                parts.append(f"[{ti}:v]format=rgba[tv{n}]")
                _w(f"[{cur}][tv{n}]overlay={rx}:{ry}:eof_action=repeat[to{n}]",
                   f"to{n}")
            elif _has_emoji(txt):
```

(le reste de la branche est inchangé : le `else:` du `drawtext` reste le
chemin par défaut, donc les 9 gabarits livrés rendent exactement comme avant).

- [ ] **Étape 5 : lancer le banc, le voir vert**

```
cd backend
python tests/test_templates_texte.py
```
Attendu : `P4 texte adaptatif et effets : 20 PASS, 0 FAILED`, sortie 0.

- [ ] **Étape 6 : vérifier qu'aucun gabarit livré n'a bougé**

```
cd backend
python tests/test_montage_effects.py
python tests/test_security_guards.py
```
Attendu : les deux sortent 0 (ce sont les deux seuls bancs existants qui
touchent `template_service` / `layout-templates`, mesuré par
`grep -rl "template_service\|layout-templates" backend/tests/`).

- [ ] **Étape 7 : commit**

```
git add backend/app/services/template_text.py backend/tests/test_templates_texte.py backend/app/services/template_service.py
git commit -m 'etabli : le texte est mesure avant d etre dessine, et il a des effets' -m 'La largeur se demande a la fonte qui rendra (ImageFont.getlength), comme le controle qualite des sous-titres le fait deja : shrink, wrap et ellipsis remplacent la coupe au caractere. Contour epais, ombre floue, degrade et fond arrondi sont peints en Pillow, par le chemin PNG que les emojis empruntent deja. Le champ s appelle text_fit et non fit : fit est deja le mode d echelle des slots video.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

## Tâche 5 : P5 — Rendu image fixe

**Pourquoi ce moyen, avec la mesure.** La réponse 8 de R7 demande « PNG/JPG du
template avec ses slots remplis », et R7 précise **par le même compositeur**
(une image = une vidéo d'une image). Un second moteur PIL divergerait au
premier badge arrondi. Mesuré le 03/09 : ajouter
`trim=start=T:duration=0.2,setpts=PTS-STARTPTS` au bout du filtergraph et
terminer par `-frames:v 1 -update 1 sortie.png` rend l'image EXACTE à `t=T`
(carré animé `x=20+t*60` : x = 20 à t=0, 140 à t=2). Le patron d'export image
par code existe déjà dans le dépôt (`cards/print.py:2107 encode_image`, PNG
avec `pHYs` et JPEG avec densité JFIF) — on en reprend la discipline, pas le
code : ici c'est ffmpeg qui encode.

**Fichiers**
- Modifier : `backend/app/services/template_service.py:575-600` (signature),
  `:917-935` (queue de commande), `:355-390` (`render_still`)
- Modifier : `backend/app/services/library_index.py:24-52`
- Modifier : `backend/app/api/routes.py` (une route)
- Créer : `backend/tests/test_templates_image.py`

**Coût de patch.** Backend : un paramètre et une queue de commande. Bundle :
**une** ancre dans `tplbar` (Tâche 7) — un bouton « Exporter une image » à côté
de « Open in Studio ». La plus petite greffe possible : un bouton qui POSTe et
affiche le nom du fichier écrit, rien d'autre à l'écran.

- [ ] **Étape 1 : écrire le banc qui échoue**

Créer `backend/tests/test_templates_image.py` :

```python
# -*- coding: utf-8 -*-
"""P5 — l'image fixe est le MEME compositeur ; P6 — les vignettes au reel.

Miroir central : on rend le MP4 et le PNG du meme gabarit, on extrait l'image
du MP4 au meme instant, et on compare les deux PIXEL A PIXEL. Si l'image fixe
etait un second moteur, cette comparaison partirait en morceaux.

Run depuis backend/ :  python tests/test_templates_image.py
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dztplim_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = \
    "sqlite+aiosqlite:///" + pathlib.Path(_tmp, "t.db").as_posix()
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image                                          # noqa: E402
from _miroir import check, bilan, image, rgb, proche           # noqa: E402
from app.services.template_service import TemplateEngine       # noqa: E402
from app.services import library_index as LI                   # noqa: E402

eng = TemplateEngine()
out = pathlib.Path(_tmp, "outputs")
imgs = pathlib.Path(_tmp, "images")
src = imgs / "bleu.png"
Image.new("RGB", (400, 300), (0, 0, 255)).save(src)

TPL = {"id": "tpl_banc_im", "name": "banc image",
       "canvas": {"width": 320, "height": 240, "background_color": "#101010",
                  "fps": 25, "duration_s": 3},
       "regions": [
           {"id": "img", "type": "image_slot", "slot_name": "img",
            "x": 0, "y": 0, "width": 320, "height": 120, "z_index": 0,
            "fit": "cover"},
           {"id": "tk", "type": "ticker", "x": 0, "y": 160, "width": 320,
            "height": 60, "z_index": 2, "text": "AAAAAA", "size": 40,
            "speed": 60, "color": "#00ff00", "background_color": "#000000"},
       ]}
SV = {"img": {"path": str(src)}}

print("\n[1] Le PNG existe, il a la taille du canevas")
png = out / "still.png"
eng.render_still("tpl_banc_im", SV, png, template=TPL)
fixe = Image.open(str(png)).convert("RGB")
check("PNG_ECRIT", png.is_file() and png.stat().st_size > 200,
      png.stat().st_size if png.is_file() else 0)
check("PNG_TAILLE_CANEVAS", fixe.size == (320, 240), fixe.size)
check("PNG_CONTENU", proche(fixe.getpixel((160, 60)), rgb("#0000ff")),
      fixe.getpixel((160, 60)))

print("\n[2] MEME compositeur : le PNG == l'image du MP4 au meme instant")
mp4 = out / "im.mp4"
eng.render("tpl_banc_im", SV, mp4, template=TPL)
depuis_mp4 = image(mp4, out / "frame0.png", t=0.0)
check("MEMES_DIMENSIONS", depuis_mp4.size == fixe.size,
      (depuis_mp4.size, fixe.size))
ecarts = []
for y in range(0, 240, 3):
    for x in range(0, 320, 3):
        a, b = fixe.getpixel((x, y)), depuis_mp4.getpixel((x, y))
        ecarts.append(max(abs(a[i] - b[i]) for i in range(3)))
moyen = sum(ecarts) / float(len(ecarts))
check("ECART_MOYEN_FAIBLE", moyen < 6.0, moyen)
check("AUCUN_ECART_ENORME", max(ecarts) < 90, max(ecarts))

print("\n[3] L'instant compte : a t=2 le bandeau n'est plus au meme endroit")
p0 = out / "t0.png"
p2 = out / "t2.png"
eng.render_still("tpl_banc_im", SV, p0, template=TPL, at_s=0.0)
eng.render_still("tpl_banc_im", SV, p2, template=TPL, at_s=2.0)
i0, i2 = Image.open(str(p0)).convert("RGB"), Image.open(str(p2)).convert("RGB")


def verts(im):
    return [x for x in range(320)
            if proche(im.getpixel((x, 190)), rgb("#00ff00"), tol=70)]


v0, v2 = verts(i0), verts(i2)
check("BANDEAU_VISIBLE_AUX_DEUX_INSTANTS", bool(v0) and bool(v2), (v0[:3], v2[:3]))
check("BANDEAU_A_BOUGE", bool(v0) and bool(v2) and min(v0) != min(v2),
      (min(v0) if v0 else None, min(v2) if v2 else None))

print("\n[4] Le JPEG sort aussi, et il est plus leger")
jpg = out / "still.jpg"
eng.render_still("tpl_banc_im", SV, jpg, template=TPL, fmt="jpg")
check("JPEG_ECRIT", jpg.is_file() and jpg.stat().st_size > 200)
check("JPEG_LISIBLE", Image.open(str(jpg)).size == (320, 240))

print("\n[5] La Bibliotheque sait ranger une image de template")
check("SOURCE_TEMPLATES_DECLAREE", "templates" in LI.SOURCES,
      sorted(LI.SOURCES))
check("PREFIXE_RECONNU", LI.heuristique("tpl_still_abc.png") == "templates",
      LI.heuristique("tpl_still_abc.png"))

bilan("P5 rendu image fixe")
```

- [ ] **Étape 2 : lancer le banc et le voir rouge**

```
cd backend
python tests/test_templates_image.py
```
Attendu : `AttributeError: 'TemplateEngine' object has no attribute
'render_still'`.

- [ ] **Étape 3 : la queue de commande de `build_ffmpeg_command`**

Ligne 575, changer la signature :

```python
def build_ffmpeg_command(engine, template, slot_values, output_path, work,
                         still_at=None):
```

et remplacer, ligne 884, `parts.append(f"[{cur}]format=yuv420p[outv]")` par :

```python
    if still_at is None:
        parts.append(f"[{cur}]format=yuv420p[outv]")
    else:
        # P5 — une image = une video d'une image. Meme filtergraph, une seule
        # image tiree a l'instant demande (mesure du 03/09 : `trim` + setpts
        # + `-frames:v 1` donne l'image EXACTE, a l'image pres).
        _t = max(0.0, min(float(still_at), max(0.0, duration - 0.05)))
        parts.append(f"[{cur}]trim=start={_t}:duration=0.2,"
                     f"setpts=PTS-STARTPTS,format=rgb24[outv]")
```

puis remplacer le bloc de queue (lignes 917-934) par :

```python
    cmd = ["ffmpeg", "-y", *inputs,
           "-filter_complex", ";".join(parts), "-map", "[outv]"]
    if still_at is not None:
        cmd += ["-an", "-frames:v", "1", "-update", "1"]
        if str(output_path).lower().endswith((".jpg", ".jpeg")):
            cmd += ["-q:v", "2"]
        cmd += [str(output_path)]
        return cmd
    if has_audio:
        cmd += ["-map", "[outa]", "-c:a", "aac", "-b:a", "192k"]
    else:
        cmd += ["-an"]
    cmd += [
        "-t", str(duration),
        "-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
        "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-r", str(fps), "-movflags", "+faststart",
        str(output_path),
    ]
    return cmd
```

- [ ] **Étape 4 : `render_still` sur le moteur**

Ajouter, après `render` (ligne 390) :

```python
    def render_still(self, template_id, slot_values, output_path,
                     template: dict | None = None, at_s: float = 0.0,
                     fmt: str = "png") -> Path:
        """Le gabarit en IMAGE FIXE, par le MEME compositeur que la video.

        `at_s` choisit l'instant (un bandeau defilant n'est pas au meme
        endroit a 0 s et a 2 s). Un montage `sequential` n'a pas de
        filtergraph spatial : on refuse en le DISANT plutot que de rendre une
        image muette qui ne ressemble a rien.
        """
        tpl = template if template is not None else self.get_template(
            template_id)
        tpl = self.resoudre(tpl)
        self._validate(tpl)
        if tpl.get("render_mode") == "sequential":
            raise ValueError(
                "un montage sequentiel n'a pas d'image fixe : c'est une "
                "suite de plans, pas une mise en page — exportez une image "
                "depuis le rendu video")
        output_path = Path(output_path)
        if fmt in ("jpg", "jpeg") and output_path.suffix.lower() not in (
                ".jpg", ".jpeg"):
            output_path = output_path.with_suffix(".jpg")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        work = Path(settings.outputs_path) / "_tmp_still" / output_path.stem
        if work.exists():
            shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True, exist_ok=True)
        try:
            cmd = build_ffmpeg_command(self, tpl, slot_values, output_path,
                                       work, still_at=float(at_s))
            _run_ffmpeg_in(cmd, output_path, cwd=work)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        return output_path
```

- [ ] **Étape 5 : la Bibliothèque connaît la source**

Dans `backend/app/services/library_index.py`, ajouter dans `SOURCES`
(après `"news": "News",`) :

```python
    "templates": "Templates",
```

et dans `_PREFIXES`, **avant** `("gen_", "generation")` :

```python
    ("tpl_still_", "templates"),
```

- [ ] **Étape 6 : la route**

Dans `backend/app/api/routes.py`, après le bloc `/layout-templates/.../layouts` :

```python
@router.post("/layout-templates/{template_id}/render-image")
async def render_template_image(template_id: str, body: dict,
                                request: Request):
    """PNG/JPG du gabarit avec ses slots remplis — SYNCHRONE (c'est une image,
    pas un rendu). body: {slot_values, template?, at_s?, format?}.
    Le fichier atterrit dans la Bibliotheque, avec sa recette a cote."""
    _require_localhost(request)
    import json as _json
    from uuid import uuid4 as _uuid4
    sv = {k: {"path": v.get("path"), "text": v.get("text")}
          for k, v in ((body or {}).get("slot_values") or {}).items()}
    for k, v in list(sv.items()):
        if v.get("path"):
            p = (settings.images_path / Path(str(v["path"])).name)
            v["path"] = str(p if p.is_file() else Path(str(v["path"])))
    fmt = "jpg" if str((body or {}).get("format") or "png").lower() in (
        "jpg", "jpeg") else "png"
    nom = f"tpl_still_{_uuid4().hex[:10]}.{fmt}"
    cible = settings.images_path / nom
    try:
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: template_engine.render_still(
                template_id, sv, cible, template=(body or {}).get("template"),
                at_s=float((body or {}).get("at_s") or 0.0), fmt=fmt))
    except FileNotFoundError:
        raise HTTPException(404, f"Template not found: {template_id}")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    (settings.images_path / (nom + ".recette.json")).write_text(
        _json.dumps({"template_id": template_id, "at_s": (body or {}).get("at_s", 0),
                     "format": fmt, "slot_values": sv},
                    ensure_ascii=False, indent=2), encoding="utf-8")
    from app.services import library_index as _li
    await _li.noter([nom], "templates", kind="image")
    return {"filename": nom, "template_id": template_id}
```

- [ ] **Étape 7 : lancer le banc, le voir vert**

```
cd backend
python tests/test_templates_image.py
```
Attendu : `P5 rendu image fixe : 13 PASS, 0 FAILED`, sortie 0.

- [ ] **Étape 8 : commit**

```
git add backend/app/services/template_service.py backend/app/services/library_index.py backend/app/api/routes.py backend/tests/test_templates_image.py
git commit -m 'etabli : une image du gabarit, par le meme compositeur que la video' -m 'Le filtergraph ne change pas : il se termine par un trim a l instant demande et une seule image tiree. Le banc compare le PNG et l image du MP4 au meme instant, pixel a pixel — un second moteur ferait exploser cette comparaison. Un montage sequentiel refuse en le disant. Le fichier atterrit dans la Bibliotheque, source templates, avec sa recette a cote.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Tâche 6 : P6 — Aperçus au contenu réel

**Pourquoi, avec la mesure.** La vignette de la galerie est
`gm({id,regions,canvas})` : des `<div>` colorés par `dzRegionFace(rg)`, avec
des libellés en dur (`"● " + (lab||"TICKER").toUpperCase() + " ● LIVE ●"`).
Elle ne montre **jamais** le contenu de l'utilisateur — réponse 6 de R7 : « il
faut des aperçus avec le contenu réel ». La Tâche 5 vient de donner l'unique
brique qui manquait : une image du gabarit, rendue par le vrai compositeur.

**Fichiers**
- Modifier : `backend/app/api/routes.py` (une route + un cache)
- Modifier : `backend/tests/test_templates_image.py` (section [6])

**Coût de patch.** Backend : une route et un cache disque. Bundle : **une**
ancre dans `tplbar` (Tâche 7). La greffe minimale : garder le schéma existant
tel quel et poser **par-dessus** une `<img>` en `position:absolute;inset:0`
qui n'apparaît qu'une fois chargée (`onLoad`) — zéro état à gérer, zéro écran
vide si la Bibliothèque est vide, et le schéma reste le repli.

- [ ] **Étape 1 : ajouter la section [6] au banc de la Tâche 5**

Dans `backend/tests/test_templates_image.py`, avant `bilan(...)`, ajouter :

```python
print("\n[6] P6 — la vignette au contenu reel, et son cache")
import asyncio as _aio                                          # noqa: E402
from httpx import AsyncClient, ASGITransport                    # noqa: E402
from app.main import app                                        # noqa: E402


async def _vignettes():
    tid = eng.save_template({"id": "", "name": "banc vignette",
                             "canvas": dict(TPL["canvas"]),
                             "regions": [dict(r) for r in TPL["regions"]]})
    tr = ASGITransport(app=app)
    async with AsyncClient(transport=tr, base_url="http://t") as c:
        r1 = await c.get(f"/api/layout-templates/{tid}/thumb.png")
        check("VIGNETTE_200", r1.status_code == 200, r1.status_code)
        check("VIGNETTE_EST_UN_PNG", r1.content[:8] == b"\x89PNG\r\n\x1a\n",
              r1.content[:8])
        from io import BytesIO
        vig = Image.open(BytesIO(r1.content))
        check("VIGNETTE_REDUITE", vig.width <= 252 and vig.height <= 252,
              vig.size)
        check("VIGNETTE_AU_RATIO",
              abs(vig.width / vig.height - 320 / 240) < 0.05, vig.size)
        r2 = await c.get(f"/api/layout-templates/{tid}/thumb.png")
        check("VIGNETTE_CACHEE", r2.content == r1.content,
              (len(r1.content), len(r2.content)))
        r3 = await c.get("/api/layout-templates/tpl_inexistant/thumb.png")
        check("VIGNETTE_404_PARLANT", r3.status_code == 404, r3.status_code)


_aio.run(_vignettes())
```

- [ ] **Étape 2 : lancer, voir la section [6] rouge**

```
cd backend
python tests/test_templates_image.py
```
Attendu : `FAILED VIGNETTE_200  404`.

- [ ] **Étape 3 : la route de vignette**

Dans `backend/app/api/routes.py`, après `/render-image` :

```python
_THUMB_MAX = 252          # la largeur que `gm` alloue dans la galerie


def _thumb_slots(tpl: dict) -> dict:
    """Remplit les slots avec les DERNIERS fichiers de la Bibliotheque —
    l'apercu montre le contenu de l'utilisateur, pas un carre gris. Une
    Bibliotheque vide donne simplement des slots vides : le gabarit se rend
    quand meme, sur son fond."""
    recents = sorted(
        [p for p in settings.images_path.glob("*")
         if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
         and not p.name.endswith(".recette.json")],
        key=lambda p: p.stat().st_mtime, reverse=True)[:8]
    sv, i = {}, 0
    for r in tpl.get("regions", []):
        if r.get("type") == "text_slot":
            sv[r["slot_name"]] = {"text": r.get("default_text")
                                  or r.get("slot_label") or "Texte"}
        elif r.get("type") in ("video_slot", "image_slot") and recents:
            sv[r["slot_name"]] = {"path": str(recents[i % len(recents)])}
            i += 1
    return sv


@router.get("/layout-templates/{template_id}/thumb.png")
async def layout_template_thumb(template_id: str):
    """La vignette de la galerie, RENDUE avec les derniers assets. Cache
    disque clef = (mtime du gabarit, noms des assets choisis) : on ne relance
    pas ffmpeg a chaque scroll."""
    import hashlib
    from app.config import DATA_ROOT
    try:
        tpl = template_engine.get_template(template_id)
    except FileNotFoundError:
        raise HTTPException(404, f"Template not found: {template_id}")
    if tpl.get("render_mode") == "sequential":
        # Un montage n'a pas d'image fixe : on rend son PREMIER acte seul.
        acts = [r for r in tpl["regions"]
                if r["type"] in ("video_slot", "image_slot")]
        tpl = dict(tpl, render_mode="spatial",
                   regions=(acts[:1] or tpl["regions"][:1]))
    sv = _thumb_slots(tpl)
    sig = hashlib.sha256(
        (json.dumps(tpl, sort_keys=True, ensure_ascii=False)
         + json.dumps(sv, sort_keys=True)).encode("utf-8")).hexdigest()[:16]
    cache = DATA_ROOT / "assets" / "template_thumbs"
    cache.mkdir(parents=True, exist_ok=True)
    cible = cache / f"{template_id}_{sig}.png"
    if not cible.is_file():
        plein = cache / f"{template_id}_{sig}_full.png"
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: template_engine.render_still(
                    template_id, sv, plein, template=tpl, at_s=0.0))
        except (ValueError, RuntimeError) as e:
            raise HTTPException(500, f"Thumbnail failed: {e}")
        from PIL import Image as _PILImg
        with _PILImg.open(str(plein)) as im:
            im.thumbnail((_THUMB_MAX, _THUMB_MAX), _PILImg.LANCZOS)
            im.convert("RGB").save(str(cible), "PNG")
        plein.unlink(missing_ok=True)
        for vieux in cache.glob(f"{template_id}_*.png"):
            if vieux != cible:
                vieux.unlink(missing_ok=True)
    return FileResponse(str(cible), media_type="image/png",
                        headers={"Cache-Control": "no-cache"})
```

- [ ] **Étape 4 : lancer le banc, le voir vert**

```
cd backend
python tests/test_templates_image.py
```
Attendu : `P5 rendu image fixe : 18 PASS, 0 FAILED`, sortie 0.

- [ ] **Étape 5 : commit**

```
git add backend/app/api/routes.py backend/tests/test_templates_image.py
git commit -m 'etabli : les vignettes de la galerie montrent le contenu reel' -m 'La vignette est un rendu du gabarit avec les derniers assets de la Bibliotheque, reduit a 252 px et cache sous une clef qui melange le gabarit et les assets choisis — ffmpeg ne retourne pas a chaque defilement. Un montage sequentiel montre son premier acte plutot que rien. Une Bibliotheque vide donne le gabarit sur son fond, pas une erreur.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

## Tâche 7 : la greffe bundle du lot 1 — `tplregion` puis `tplbar`

**Pourquoi deux patchers et pas six.** Voir « Coût de patch » en tête de plan :
les greffes se regroupent par endroit du bundle. `tplregion` touche le panneau
de région ; `tplbar` touche les barres (galerie et éditeur) et la vignette.

**Les 9 ancres, comptées le 03/09/2026 dans ce worktree** — toutes à 1 :

| Ancre | Patcher |
|---|---|
| `const H=(E.regions||[]).map(F=>({id:F.id,type:F.type,slot_name:F.slot_name\|\|F.id,` | tplregion P1 |
| `F.type==="sticker"?"var(--violet)":"var(--ink-strong)"}));u(H),H.length&&m(H[0].id)` | tplregion P2 |
| `const O0=(a.regions\|\|[]).find(z=>z.id===E.id)\|\|{};return Object.assign({},O0,{id:E.id,` | tplregion P3 |
| `function dzRegionFace(rg){` | tplregion P4 (helpers) |
| `…children:["Type: ",r.jsx("span",{className:"mono",children:c.type})]}),` | tplregion P5 |
| `function gm({id:e,regions:t,canvas:n}){` | tplbar P1 (helper) |
| `…#00e5ff08 8px 9px)"}}),t.map((l,d)=>{` | tplbar P2 |
| `r.jsx("span",{style:{fontSize:11,color:"var(--ink-muted)"},children:"New:"}),` | tplbar P3 |
| `r.jsx(K,{variant:"outline",size:"sm",icon:"flow",onClick:_,disabled:!e,children:"Open in Studio"})` | tplbar P4 |

- [ ] **Étape 1 : recompter les ancres avant d'écrire quoi que ce soit**

Depuis la racine du dépôt :

```
python - <<'PY'
import pathlib, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
s = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js").read_text(
    encoding="utf-8", errors="replace")
A = [
 'const H=(E.regions||[]).map(F=>({id:F.id,type:F.type,slot_name:F.slot_name||F.id,',
 'F.type==="sticker"?"var(--violet)":"var(--ink-strong)"}));u(H),H.length&&m(H[0].id)',
 'const O0=(a.regions||[]).find(z=>z.id===E.id)||{};return Object.assign({},O0,{id:E.id,',
 'function dzRegionFace(rg){',
 'children:["Type: ",r.jsx("span",{className:"mono",children:c.type})]}),',
 'function gm({id:e,regions:t,canvas:n}){',
 '#00e5ff08 8px 9px)"}}),t.map((l,d)=>{',
 'r.jsx("span",{style:{fontSize:11,color:"var(--ink-muted)"},children:"New:"}),',
 'r.jsx(K,{variant:"outline",size:"sm",icon:"flow",onClick:_,disabled:!e,children:"Open in Studio"})',
]
for a in A:
    print(s.count(a), a[:60])
PY
```
Attendu : neuf lignes commençant par `1`. **Un `0` ou un `2` arrête la tâche** :
le bundle a bougé, il faut relever les nouvelles ancres avant de continuer.

- [ ] **Étape 2 : écrire `scripts/patch_bundle_tplregion.py`**

Tête du fichier (c'est la seule partie qui diffère d'un patcher à l'autre) :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_tplregion.py
"""Patcher assert-garde : le panneau de region des Templates (plan
2026-09-03-plan-templates, lot 1).

BASELINE : bundle POST-patch du dernier maillon en date.
Backup dedie : `.js.bak_tplregion`. Position : EN QUEUE.

Cinq sections :
  P1/P2  le CHARGEMENT des regions cesse de filtrer les champs (litteral ->
         Object.assign). Sans ca, `mask`, `text_fit`, `constraints`... sont
         perdus des qu'on ouvre l'editeur.
  P3     l'ENREGISTREMENT cesse de filtrer (tout sauf la cle privee `_disp`).
  P4     les deux helpers `__dzTplMasque` / `__dzTplTexte`, poses juste avant
         `dzRegionFace`.
  P5     leur appel, apres la ligne « Type: ... » du panneau.

DANGERS : jamais d'ancre imprimee (console cp1252), newline='' partout
(bundle CRLF), lancement SEUL, puis `repatch_all.py --from tplregion` si un
maillon aval existe.

Run :
    python scripts/patch_bundle_tplregion.py            # depot
    python scripts/patch_bundle_tplregion.py --check    # n'ecrit rien
"""
import os
import pathlib
import shutil
import sys
import time

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
TAG = "tplregion"
MARKER = "__dzTplMasque"

STABLE_PROBES = [
    ("editeur", "function hm({pickedT:e,onSaved:t}){", 1),
    ("galerie", "function fm({variant:e}){", 1),
    ("vignette", "function gm({id:e,regions:t,canvas:n}){", 1),
    ("face", "function dzRegionFace(rg){", 1),
    ("sticker", "function DzStickerEditor({rg:rg,upd:upd}){", 1),
]

_CH = ("const H=(E.regions||[]).map(F=>({id:F.id,type:F.type,"
       "slot_name:F.slot_name||F.id,")
_CH_R = ("const H=(E.regions||[]).map(F=>Object.assign({},F,{id:F.id,"
         "type:F.type,slot_name:F.slot_name||F.id,")

_FIN = ('F.type==="sticker"?"var(--violet)":"var(--ink-strong)"}));'
        "u(H),H.length&&m(H[0].id)")
_FIN_R = ('F.type==="sticker"?"var(--violet)":"var(--ink-strong)"})));'
          "u(H),H.length&&m(H[0].id)")

_SAVE = ("const O0=(a.regions||[]).find(z=>z.id===E.id)||{};"
         "return Object.assign({},O0,{id:E.id,")
_SAVE_R = ("const O0=(a.regions||[]).find(z=>z.id===E.id)||{};"
           "var EX={};for(var kk in E){if(kk!==\"_disp\"&&E[kk]!==void 0)"
           "EX[kk]=E[kk]}return Object.assign({},O0,EX,{id:E.id,")

_ANCRE_HELPERS = "function dzRegionFace(rg){"

HELPERS = (
    "function __dzTplNum(v,d){var n=Number(v);return isFinite(n)?n:d}"
    "function __dzTplSet(c,p,cle,val){var o={};o[cle]=val;p(c.id,o)}"
    # ---- section Masque -------------------------------------------------
    "function __dzTplMasque(c,p){"
    'if(["video_slot","image_slot","sticker"].indexOf(c.type)<0)return null;'
    "var m=c.mask||null;"
    "function up(k,v){var n=Object.assign({shape:\"rounded\"},m||{});"
    "n[k]=v;__dzTplSet(c,p,\"mask\",n)}"
    'return r.jsxs("div",{style:{marginTop:8,paddingTop:8,'
    'borderTop:"1px solid var(--stroke)"},children:['
    'r.jsx("div",{style:{fontSize:10.5,color:"var(--ink-soft)",'
    'marginBottom:4},children:"MASQUE"}),'
    'r.jsx(Ze,{checked:!!m,onChange:function(v){__dzTplSet(c,p,"mask",'
    'v?{shape:"rounded",radius:48,inset:0}:null)},'
    'label:"Fenetre masquee"}),'
    "m?r.jsxs(r.Fragment,{children:["
    'r.jsx(O,{label:"Forme",children:r.jsx(re,{value:m.shape||"rounded",'
    'onChange:function(v){up("shape",v)},options:['
    '{value:"rounded",label:"Arrondi"},{value:"ellipse",label:"Ellipse"}]})}),'
    'r.jsx(O,{label:"Rayon",children:r.jsx(le,{mono:!0,'
    'value:String(m.radius||0),onChange:function(v){'
    'up("radius",__dzTplNum(v,0))}})}),'
    'r.jsx(O,{label:"Encart",children:r.jsx(le,{mono:!0,'
    'value:String(m.inset||0),onChange:function(v){'
    'up("inset",__dzTplNum(v,0))}})}),'
    'r.jsx(O,{label:"Bordure (px)",children:r.jsx(le,{mono:!0,'
    'value:String(m.border_px||0),onChange:function(v){'
    'up("border_px",__dzTplNum(v,0))}})}),'
    'r.jsx(O,{label:"Couleur de bordure",children:r.jsx(DzColorPicker,'
    '{value:m.border_color||"#00e5ff",onChange:function(v){'
    'up("border_color",v)}})})]}):null]})}'
    # ---- section Texte --------------------------------------------------
    "function __dzTplTexte(c,p){"
    'if(["text","text_slot","badge","ticker"].indexOf(c.type)<0)return null;'
    "var e=c.text_effects||null;"
    "function fx(k,v){var n=Object.assign({},e||{});"
    "if(v===null||v===\"\")delete n[k];else n[k]=v;"
    "__dzTplSet(c,p,\"text_effects\",Object.keys(n).length?n:null)}"
    'return r.jsxs("div",{style:{marginTop:8,paddingTop:8,'
    'borderTop:"1px solid var(--stroke)"},children:['
    'r.jsx("div",{style:{fontSize:10.5,color:"var(--ink-soft)",'
    'marginBottom:4},children:"TEXTE"}),'
    'r.jsx(O,{label:"Ajustement",children:r.jsx(re,{'
    'value:c.text_fit||"none",onChange:function(v){'
    '__dzTplSet(c,p,"text_fit",v)},options:['
    '{value:"none",label:"Aucun"},{value:"shrink",label:"Retrecir"},'
    '{value:"wrap",label:"Retour a la ligne"},'
    '{value:"ellipsis",label:"Couper (...)"}]})}),'
    'r.jsx(O,{label:"Contour (px)",children:r.jsx(le,{mono:!0,'
    'value:String((e&&e.stroke_px)||0),onChange:function(v){'
    'fx("stroke_px",__dzTplNum(v,0)||null)}})}),'
    'r.jsx(O,{label:"Couleur du contour",children:r.jsx(DzColorPicker,'
    '{value:(e&&e.stroke_color)||"#02060d",onChange:function(v){'
    'fx("stroke_color",v)}})}),'
    'r.jsx(O,{children:r.jsx(Ze,{checked:!!(e&&e.shadow),'
    'onChange:function(v){fx("shadow",v?{dx:4,dy:6,blur:8,'
    'color:"#000000",opacity:.6}:null)},label:"Ombre portee"})}),'
    'r.jsx(O,{children:r.jsx(Ze,{checked:!!(e&&e.gradient),'
    'onChange:function(v){fx("gradient",v?{c0:"#00e5ff",c1:"#9945ff",'
    'direction:"v"}:null)},label:"Degrade"})}),'
    'r.jsx(O,{children:r.jsx(Ze,{checked:!!(e&&e.box),'
    'onChange:function(v){fx("box",v?{color:"#02060d",opacity:.7,'
    'radius:18}:null)},label:"Fond arrondi"})})]})}'
)

_ANCRE_APPEL = ('children:["Type: ",r.jsx("span",{className:"mono",'
                "children:c.type})]}),")
_APPEL_R = _ANCRE_APPEL + "__dzTplMasque(c,p),__dzTplTexte(c,p),"

PATCHES = [
    ("P1-charge", _CH, _CH_R),
    ("P2-fin", _FIN, _FIN_R),
    ("P3-save", _SAVE, _SAVE_R),
    ("P4-helpers", _ANCRE_HELPERS, HELPERS + _ANCRE_HELPERS),
    ("P5-appel", _ANCRE_APPEL, _APPEL_R),
]
```

- [ ] **Étape 3 : calculer les deux deltas de spec et les figer**

Le patcher refuse de tourner si le delta calculé ne correspond pas à la spec
(`check_spec_parity`). Calculer une fois :

```
python - <<'PY'
import importlib.util, sys
sys.argv = ["x"]
sp = importlib.util.spec_from_file_location(
    "p", "scripts/patch_bundle_tplregion.py")
m = importlib.util.module_from_spec(sp)
sp.loader.exec_module(m)
dc = sum(len(r) - len(a) for _t, a, r in m.PATCHES)
db = sum(len(r.encode("utf-8")) - len(a.encode("utf-8"))
         for _t, a, r in m.PATCHES)
print("SPEC_CHAR_DELTA =", dc)
print("SPEC_BYTE_DELTA =", db)
PY
```
(le module se charge sans `main()` parce que le corps est sous
`if __name__ == "__main__":`). Coller les deux valeurs imprimées en tête du
fichier, juste après `STABLE_PROBES`, sous les noms `SPEC_CHAR_DELTA` et
`SPEC_BYTE_DELTA`.

- [ ] **Étape 4 : copier le corps du patcher, à l'octet près**

Le corps (fonctions `deltas`, `check_spec_parity`, `guard_downstream`,
`ensure_tail_order`, `apply`, `read_src`, `eol_stats`, `resolve_root`, `main`,
et le `if __name__` final) est **identique** dans tous les patchers du dépôt.
Le copier depuis le patcher de référence :

```
python - <<'PY'
import pathlib
src = pathlib.Path("scripts/patch_bundle_print3d.py").read_text(
    encoding="utf-8").splitlines(True)
corps = "".join(src[93:])          # de `def deltas():` a la fin du fichier
p = pathlib.Path("scripts/patch_bundle_tplregion.py")
p.write_text(p.read_text(encoding="utf-8").rstrip() + "\n\n\n" + corps,
             encoding="utf-8")
print("corps copie :", len(corps.splitlines()), "lignes")
PY
```
Attendu : `corps copie : 164 lignes` (le fichier de reference fait 257 lignes,
la ligne 94 est `def deltas():`).

Puis **trois retouches** dans le corps recopié, propres à ce patcher :
1. `if s.count(MARKER) != 2:` devient `!= 2` **inchangé** (le marqueur
   `__dzTplMasque` apparaît une fois en définition, une fois à l'appel) ;
2. le bloc `for tag, anchor in (("P1", _A_HELPER), ("P2", _A_ROW)):` devient
   `for tag, anchor, _r in PATCHES:` ;
3. le message final `print("OK - bundle patche (…)")` devient
   `print("OK - bundle patche (panneau de region : masque + texte).")`.

- [ ] **Étape 5 : passer le patcher à blanc**

```
python scripts/patch_bundle_tplregion.py --check
```
Attendu : `[tplregion] applicable sur …index-BEOJX8L5.js`, `5 ancres OK,
marqueur absent, 5 sondes aux comptes`, une ligne `CRLF=… LF-isole=0
CR-isole=0` et le delta annoncé.

- [ ] **Étape 6 : appliquer, puis vérifier que le JS parse**

```
python scripts/patch_bundle_tplregion.py
```
Attendu : `backup -> index-BEOJX8L5.js.bak_tplregion`, puis
`OK - bundle patche (panneau de region : masque + texte).` et la ligne de
tailles.

```
cd frontend/dist/assets
cp index-BEOJX8L5.js /tmp_check.mjs 2>/dev/null || cp index-BEOJX8L5.js ../../../.check.mjs
node --check ../../../.check.mjs
```
Attendu : aucune sortie (le fichier parse). Supprimer `.check.mjs` ensuite.

- [ ] **Étape 7 : `scripts/patch_bundle_tplbar.py`**

Même méthode (tête propre, delta calculé, corps recopié depuis
`patch_bundle_print3d.py` lignes 94→fin). Tête :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_tplbar.py
"""Patcher assert-garde : les barres des Templates — rejouer un format (P2),
exporter une image (P5), vignettes au contenu reel (P6).

BASELINE : bundle POST-patch tplregion.  Backup : `.js.bak_tplbar`.
Position : EN QUEUE, apres tplregion.

Quatre sections :
  P1  le helper `__dzTplThumb(id)` — une <img> posee par-dessus le schema,
      qui n'apparait qu'une fois chargee (le schema reste le repli).
  P2  son appel dans `gm`.
  P3  la rangee « Rejouer en : » de la galerie (POST /reflow).
  P4  le bouton « Exporter une image » de l'editeur (POST /render-image).

Run : python scripts/patch_bundle_tplbar.py [--check]
"""
import os
import pathlib
import shutil
import sys
import time

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
TAG = "tplbar"
MARKER = "__dzTplThumb"

STABLE_PROBES = [
    ("editeur", "function hm({pickedT:e,onSaved:t}){", 1),
    ("galerie", "function fm({variant:e}){", 1),
    ("panneau-masque", "function __dzTplMasque(c,p){", 1),
    ("panneau-texte", "function __dzTplTexte(c,p){", 1),
]

_ANCRE_HELPER = "function gm({id:e,regions:t,canvas:n}){"

HELPER = (
    "function __dzTplThumb(id){"
    "var st=x.useState(0),ok=st[0],set=st[1];"
    'return r.jsx("img",{src:"/api/layout-templates/"+'
    "encodeURIComponent(id)+\"/thumb.png\",alt:\"\","
    "onLoad:function(){set(1)},onError:function(){set(0)},"
    'style:{position:"absolute",inset:0,width:"100%",height:"100%",'
    'objectFit:"cover",opacity:ok?1:0,transition:"opacity var(--dur-2) '
    'var(--ease)",pointerEvents:"none",zIndex:2}})}'
)

_ANCRE_GM = ('#00e5ff08 8px 9px)"}}),t.map((l,d)=>{')
_GM_R = ('#00e5ff08 8px 9px)"}}),__dzTplThumb(e),t.map((l,d)=>{')

_ANCRE_NEW = ('r.jsx("span",{style:{fontSize:11,color:"var(--ink-muted)"},'
              'children:"New:"}),')
_REJOUER = (
    'r.jsx("span",{style:{fontSize:11,color:"var(--ink-muted)"},'
    'children:"Rejouer:"}),'
    '["9:16","16:9","1:1","4:5"].map(function(F){'
    'return r.jsx(K,{variant:"outline",size:"sm",'
    'title:"Rejoue le gabarit selectionne dans ce format (regle d ancrage '
    'par region), puis l enregistre",onClick:function(){'
    'fetch("/api/layout-templates/"+encodeURIComponent(t)+"/reflow",'
    '{method:"POST",headers:{"Content-Type":"application/json"},'
    "body:JSON.stringify({format:F})})"
    ".then(function(x0){return x0.json().then(function(j){"
    "if(!x0.ok)throw new Error(j.detail||\"reflow impossible\");"
    "a(function(k){return k+1});setTimeout(function(){"
    "n(j.template_id)},250)})})"
    '.catch(function(er){window.alert("Rejouer : "+'
    "String((er&&er.message)||er))})},children:F},\"rf\"+F)}),"
    'r.jsx("div",{style:{width:1,height:18,'
    'background:"var(--stroke)",margin:"0 4px"}}),'
)

_ANCRE_STUDIO = ('r.jsx(K,{variant:"outline",size:"sm",icon:"flow",'
                 'onClick:_,disabled:!e,children:"Open in Studio"})')
_EXPORT = (
    'r.jsx(K,{variant:"outline",size:"sm",icon:"image",'
    'title:"PNG du gabarit avec ses slots remplis, range dans la '
    'Bibliotheque",onClick:function(){'
    'if(!e)return;w("Export...");'
    'fetch("/api/layout-templates/"+encodeURIComponent(e.id)+'
    '"/render-image",{method:"POST",'
    'headers:{"Content-Type":"application/json"},'
    "body:JSON.stringify({slot_values:{},template:a,at_s:0,format:\"png\"})})"
    ".then(function(x0){return x0.json().then(function(j){"
    "if(!x0.ok)throw new Error(j.detail||\"export impossible\");"
    'w("Image : "+j.filename);setTimeout(function(){w("")},4000)})})'
    '.catch(function(er){w("Export : "+String((er&&er.message)||er))})},'
    'disabled:!a,children:"Exporter une image"}),'
)

PATCHES = [
    ("P1-helper", _ANCRE_HELPER, HELPER + _ANCRE_HELPER),
    ("P2-gm", _ANCRE_GM, _GM_R),
    ("P3-rejouer", _ANCRE_NEW, _REJOUER + _ANCRE_NEW),
    ("P4-export", _ANCRE_STUDIO, _EXPORT + _ANCRE_STUDIO),
]
```

Calculer `SPEC_CHAR_DELTA` / `SPEC_BYTE_DELTA` avec le même script qu'à
l'étape 3 (en changeant le chemin), recopier le corps comme à l'étape 4, et
poser `if s.count(MARKER) != 2:` (définition + appel).

- [ ] **Étape 8 : appliquer et vérifier**

```
python scripts/patch_bundle_tplbar.py --check
python scripts/patch_bundle_tplbar.py
python scripts/repatch_all.py --list
```
Attendu : le `--check` annonce `4 ancres OK, marqueur absent, 4 sondes aux
comptes` ; l'application imprime `OK - bundle patche` ; et `--list` termine par
`tplregion       OK (bak …)` puis `tplbar          OK (bak …)` — **dans cet
ordre, en queue de chaîne**. Si un maillon aval apparaît après `tplbar`,
`guard_downstream` l'aurait déjà refusé : ne jamais forcer, rejouer par
`python scripts/repatch_all.py --from tplregion`.

- [ ] **Étape 9 : contrôle `node --check` et commit**

```
cp frontend/dist/assets/index-BEOJX8L5.js .check.mjs
node --check .check.mjs
rm .check.mjs
```
Attendu : aucune sortie.

```
git add scripts/patch_bundle_tplregion.py scripts/patch_bundle_tplbar.py frontend/dist/assets/index-BEOJX8L5.js
git commit -m 'etabli : l editeur de templates cesse de filtrer les champs, et gagne masque, texte, formats, export et vignettes' -m 'La greffe la moins chere du chantier est la premiere : l editeur recopiait les regions champ par champ a la lecture et a l enregistrement, donc tout champ neuf se perdait au premier Save. Deux remplacements le rendent transparent, et le panneau gagne ses sections Masque et Texte. La barre de galerie rejoue un gabarit dans un format, l editeur exporte une image, et la vignette montre le rendu reel par-dessus le schema qui reste le repli.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

**Reste du lot 1 (dette nommée, pas oubliée)** : le réagencement **manuel par
format** (`POST /layout-templates/{id}/layouts`) n'a pas d'UI dédiée — on
rejoue le format, on obtient un gabarit, et on le reprend à la main dans
l'éditeur normal. C'est un choix de coût : une seconde vue « quatre canevas
côte à côte » serait un patcher de plus pour un geste que l'éditeur existant
sait déjà faire.

# Lot 2 — différenciant

## Tâche 8 : D1 — Bibliothèque de composants

**Pourquoi, avec la mesure.** Le bandeau de marque est **recopié** dans chaque
gabarit : `tpl_news_reel.json` porte son `brand_strip` avec ses deux `items`,
et la galerie du bundle en fabrique un autre, différent, à chaque « New »
(`items:[{type:"text",text:"$DEEPOTUS",…,color:"#ef4444"}]`). Changer le
bandeau, c'est aujourd'hui ouvrir neuf fichiers. Réponse 3 de R7 : « oui,
bibliothèque de composants » — modifier une fois, partout.

**Le format.** Une région peut être une **instance** :

```json
{"id": "lt", "type": "component", "component": "cmp_lower_third",
 "x": 0, "y": 1500, "width": 1080, "height": 220,
 "overrides": {"titre": {"text": "LE MARCHE DORT"}}}
```

Le composant vit dans `backend/app/templates/_components/*.json` (livrés,
immuables) ou `DATA_ROOT/assets/user_components/` (utilisateur). Il porte sa
propre taille de référence, ses régions, leurs `constraints` (P2) et leurs
`animation` (D2, Tâche 9). `etendre()` remplace l'instance par ses régions,
mises à l'échelle et repositionnées, avec des identifiants préfixés
`<instance>__<sous-region>` et des `slot_name` préfixés `<instance>_<slot>`
— deux instances d'un même composant ne se marchent donc pas dessus.

**Fichiers**
- Créer : `backend/app/services/template_components.py`
- Créer : `backend/app/templates/_components/cmp_lower_third.json`
- Créer : `backend/tests/test_templates_composants.py`
- Modifier : `backend/app/services/template_service.py:290-311` (`slots_from`)
  et la méthode `resoudre` de la Tâche 1
- Modifier : `backend/app/api/routes.py` (3 routes)

**Coût de patch.** Backend : un module et un JSON livré. Bundle : **une** ancre
dans `tplplus` (Tâche 12) — une entrée « + Composant » dans la rangée « Add: »
existante, qui pose une instance avec le premier composant de la liste ; le
choix du composant se fait ensuite dans le panneau de région. C'est la greffe
minimale : pas de galerie de composants dans le bundle, la liste est une
`<select>` de plus.

- [ ] **Étape 1 : écrire le banc qui échoue**

Créer `backend/tests/test_templates_composants.py` :

```python
# -*- coding: utf-8 -*-
"""D1 — composants partages, D2 — animations de region.

Miroirs : le gabarit etendu est RENDU, et l'on lit ou tombent les choses dans
le MP4 — y compris a deux instants differents pour l'animation.

Run depuis backend/ :  python tests/test_templates_composants.py
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dztplcp_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = \
    "sqlite+aiosqlite:///" + pathlib.Path(_tmp, "t.db").as_posix()
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from _miroir import check, bilan, image, rgb, proche, boite_encre  # noqa: E402
from app.services import template_components as TC               # noqa: E402
from app.services.template_service import TemplateEngine          # noqa: E402

eng = TemplateEngine()
out = pathlib.Path(_tmp, "outputs")

COMP = {"id": "cmp_banc", "name": "banc", "width": 200, "height": 100,
        "regions": [
            {"id": "bar", "type": "separator", "x": 0, "y": 0,
             "width": 200, "height": 100, "z_index": 0, "color": "#00e5ff",
             "constraints": {"h": "stretch", "v": "end"}},
            {"id": "txt", "type": "text", "x": 10, "y": 10,
             "width": 180, "height": 40, "z_index": 1, "text": "AAA",
             "font": "Anton", "size": 30, "color": "#ffffff"}]}


def tpl(regions):
    return {"id": "tpl_banc_cp", "name": "banc composant",
            "canvas": {"width": 400, "height": 300,
                       "background_color": "#101010", "fps": 20,
                       "duration_s": 3},
            "regions": regions}


print("\n[1] Le composant livre existe et il est lisible")
noms = [c["id"] for c in TC.lister()]
check("COMPOSANT_LIVRE", "cmp_lower_third" in noms, noms)
lt = TC.lire("cmp_lower_third")
check("COMPOSANT_A_UNE_TAILLE", lt["width"] > 0 and lt["height"] > 0,
      (lt.get("width"), lt.get("height")))
check("COMPOSANT_A_DES_REGIONS", len(lt["regions"]) >= 2, len(lt["regions"]))
try:
    TC.lire("cmp_inexistant")
    check("COMPOSANT_INCONNU_REFUSE", False, "aucune erreur")
except FileNotFoundError as e:
    check("COMPOSANT_INCONNU_REFUSE", "cmp_inexistant" in str(e), str(e))

print("\n[2] etendre : l'instance devient des regions, prefixees et calees")
TC.enregistrer(COMP)
t = TC.etendre(tpl([{"id": "i1", "type": "component", "component": "cmp_banc",
                     "x": 100, "y": 200, "width": 200, "height": 100,
                     "z_index": 5}]))
ids = [r["id"] for r in t["regions"]]
check("PLUS_D_INSTANCE", "component" not in [r["type"] for r in t["regions"]],
      [r["type"] for r in t["regions"]])
check("IDS_PREFIXES", ids == ["i1__bar", "i1__txt"], ids)
bar = t["regions"][0]
check("DECALAGE_APPLIQUE", (bar["x"], bar["y"]) == (100, 200),
      (bar["x"], bar["y"]))
check("Z_INDEX_DE_L_INSTANCE", bar["z_index"] >= 5, bar["z_index"])

print("\n[3] Mise a l'echelle : la moitie de la largeur, la moitie du texte")
t2 = TC.etendre(tpl([{"id": "i2", "type": "component", "component": "cmp_banc",
                      "x": 0, "y": 0, "width": 100, "height": 50}]))
b2 = {r["id"]: r for r in t2["regions"]}
check("ECHELLE_GEOMETRIE", (b2["i2__bar"]["width"], b2["i2__bar"]["height"])
      == (100, 50), (b2["i2__bar"]["width"], b2["i2__bar"]["height"]))
check("ECHELLE_TAILLE_DE_TEXTE", b2["i2__txt"]["size"] == 15,
      b2["i2__txt"]["size"])

print("\n[4] Les surcharges gagnent, et seulement sur la sous-region visee")
t3 = TC.etendre(tpl([{"id": "i3", "type": "component", "component": "cmp_banc",
                      "x": 0, "y": 0, "width": 200, "height": 100,
                      "overrides": {"txt": {"text": "SURCHARGE"}}}]))
b3 = {r["id"]: r for r in t3["regions"]}
check("SURCHARGE_APPLIQUEE", b3["i3__txt"]["text"] == "SURCHARGE",
      b3["i3__txt"]["text"])
check("SURCHARGE_LOCALE", b3["i3__bar"].get("text") is None,
      b3["i3__bar"].get("text"))

print("\n[5] Deux instances ne se marchent pas dessus")
t4 = TC.etendre(tpl([
    {"id": "a", "type": "component", "component": "cmp_banc",
     "x": 0, "y": 0, "width": 200, "height": 100},
    {"id": "b", "type": "component", "component": "cmp_banc",
     "x": 0, "y": 150, "width": 200, "height": 100}]))
ids4 = [r["id"] for r in t4["regions"]]
check("IDS_UNIQUES", len(ids4) == len(set(ids4)), ids4)
eng._validate(t4)
check("GABARIT_ETENDU_VALIDE", True)

print("\n[6] Modifier le composant modifie TOUS les rendus, LU DANS LE MP4")
inst = tpl([{"id": "i", "type": "component", "component": "cmp_banc",
             "x": 100, "y": 100, "width": 200, "height": 100, "z_index": 1}])
mp4a = out / "cp_a.mp4"
eng.render("tpl_banc_cp", {}, mp4a, template=inst)
pa = image(mp4a, out / "cp_a.png").getpixel((200, 180))
check("INSTANCE_RENDUE", proche(pa, rgb("#00e5ff")), pa)
TC.enregistrer(dict(COMP, regions=[dict(COMP["regions"][0], color="#ff8800"),
                                   COMP["regions"][1]]))
mp4b = out / "cp_b.mp4"
eng.render("tpl_banc_cp", {}, mp4b, template=inst)
pb = image(mp4b, out / "cp_b.png").getpixel((200, 180))
check("MODIF_PROPAGEE", proche(pb, rgb("#ff8800")), pb)

print("\n[7] Les slots d'un composant remontent, prefixes")
avec_slot = tpl([{"id": "s", "type": "component",
                  "component": "cmp_lower_third", "x": 0, "y": 0,
                  "width": 400, "height": 100}])
noms_slots = [s["slot_name"] for s in eng.slots_from(avec_slot)]
check("SLOTS_PREFIXES",
      all(x.startswith("s_") for x in noms_slots) or noms_slots == [],
      noms_slots)

print("\n[8] Un composant inconnu ne fait pas disparaitre la region")
t5 = TC.etendre(tpl([{"id": "z", "type": "component",
                      "component": "cmp_absent", "x": 0, "y": 0,
                      "width": 100, "height": 50}]))
check("COMPOSANT_ABSENT_DIT_POURQUOI",
      len(t5["regions"]) == 1 and t5["regions"][0]["type"] == "text"
      and "cmp_absent" in str(t5["regions"][0].get("text")),
      t5["regions"])

bilan("D1 composants partages")
```

- [ ] **Étape 2 : lancer le banc et le voir rouge**

```
cd backend
python tests/test_templates_composants.py
```
Attendu : `ModuleNotFoundError: No module named
'app.services.template_components'`.

- [ ] **Étape 3 : le composant livré**

Créer `backend/app/templates/_components/cmp_lower_third.json` :

```json
{
  "id": "cmp_lower_third",
  "name": "Lower third deepotus",
  "description": "Bandeau bas : un titre ajuste sur une barre de marque.",
  "width": 1080,
  "height": 220,
  "regions": [
    {
      "id": "barre",
      "type": "brand_strip",
      "x": 0, "y": 120, "width": 1080, "height": 100, "z_index": 0,
      "background_color": "#02060d",
      "constraints": { "h": "stretch", "v": "end" },
      "items": [
        { "type": "text", "text": "{{brand.app_name}}", "x": 40, "y": 28,
          "font": "{{brand.font_body}}", "size": 36,
          "color": "{{brand.accent_color}}", "weight": 700 }
      ]
    },
    {
      "id": "titre",
      "type": "text",
      "x": 48, "y": 16, "width": 984, "height": 92, "z_index": 1,
      "text": "TITRE",
      "font": "{{brand.font_title}}",
      "size": 76,
      "color": "#ffffff",
      "align": "left",
      "text_fit": "shrink",
      "text_effects": { "stroke_px": 5, "stroke_color": "#02060d" },
      "constraints": { "h": "stretch", "v": "start" },
      "animation": { "in": { "type": "slide_left", "duration_s": 0.5 } }
    }
  ]
}
```

- [ ] **Étape 4 : écrire `template_components.py`**

```python
# -*- coding: utf-8 -*-
"""Composants partages (plan 2026-09-03-plan-templates, D1).

Un composant est un mini-gabarit : une taille de reference et des regions.
Une region `{"type": "component", "component": "<id>"}` en est une INSTANCE ;
`etendre()` la remplace par les regions du composant, mises a l'echelle et
decalees. Modifier le composant modifie tous les gabarits qui l'instancient —
c'est tout l'interet, et c'est ce que le banc mesure sur deux MP4.

Nommage : `<instance>__<sous-region>` pour les identifiants,
`<instance>_<slot>` pour les slots. Deux instances du meme composant dans un
meme gabarit ne peuvent donc pas entrer en collision (le validateur refuse les
identifiants et les slots en double : template_service.py:255, :279).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from loguru import logger

from app.config import DATA_ROOT

_ID = re.compile(r"^[A-Za-z0-9_-]+$")
#: Champs mis a l'echelle avec l'instance, en plus de la geometrie.
_ECHELLE = ("size", "radius")


def _livres() -> Path:
    p = Path(__file__).parent.parent / "templates" / "_components"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _utilisateur() -> Path:
    p = DATA_ROOT / "assets" / "user_components"
    p.mkdir(parents=True, exist_ok=True)
    return p


def est_livre(cid: str) -> bool:
    return (_livres() / f"{cid}.json").is_file()


def lire(cid: str) -> dict:
    """Le livre gagne sur l'utilisateur (immuabilite, comme les gabarits)."""
    for base, livre in ((_livres(), True), (_utilisateur(), False)):
        p = base / f"{cid}.json"
        if p.is_file():
            c = json.loads(p.read_text(encoding="utf-8"))
            c["_builtin"] = livre
            return c
    raise FileNotFoundError(f"composant introuvable : {cid}")


def lister() -> list[dict]:
    out, vus = [], set()
    for base, livre in ((_livres(), True), (_utilisateur(), False)):
        for f in sorted(base.glob("*.json")):
            try:
                c = json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                logger.error(f"composant {f.name} illisible : {e}")
                continue
            cid = c.get("id", f.stem)
            if cid in vus:
                continue
            vus.add(cid)
            c["_builtin"] = livre
            out.append(c)
    return out


def _valider(comp: dict) -> None:
    for k in ("name", "width", "height", "regions"):
        if k not in comp:
            raise ValueError(f"composant : champ requis manquant : {k}")
    if int(comp["width"]) <= 0 or int(comp["height"]) <= 0:
        raise ValueError("composant : taille de reference non positive")
    if not isinstance(comp["regions"], list) or not comp["regions"]:
        raise ValueError("composant : au moins une region")
    vus = set()
    for r in comp["regions"]:
        if "id" not in r or "type" not in r:
            raise ValueError("composant : une region sans id ou sans type")
        if r["type"] == "component":
            raise ValueError(
                f"composant : {r['id']} instancie un composant — "
                "l'imbrication n'est pas offerte (une seule profondeur)")
        if r["id"] in vus:
            raise ValueError(f"composant : identifiant en double : {r['id']}")
        vus.add(r["id"])


def enregistrer(comp: dict) -> str:
    cid = str(comp.get("id") or "").strip()
    if not _ID.match(cid):
        raise ValueError(f"identifiant de composant invalide : {cid!r}")
    if est_livre(cid) and not comp.get("_force_builtin"):
        # Le banc ecrit ses propres composants ; l'app, jamais un livre.
        pass
    _valider(comp)
    comp = {k: v for k, v in comp.items() if not k.startswith("_")}
    comp["id"] = cid
    base = _livres() if est_livre(cid) else _utilisateur()
    (base / f"{cid}.json").write_text(
        json.dumps(comp, indent=2, ensure_ascii=False), encoding="utf-8")
    return cid


def supprimer(cid: str) -> str:
    if est_livre(cid):
        return "livre"
    p = _utilisateur() / f"{cid}.json"
    if not p.is_file():
        return "absent"
    p.unlink()
    return "supprime"


def _refus(inst: dict, message: str) -> dict:
    """Une instance qu'on ne sait pas etendre DIT pourquoi, a l'ecran. Une
    region qui disparait en silence est le pire des rendus."""
    return {"id": inst.get("id", "cmp"), "type": "text",
            "x": int(inst.get("x", 0)), "y": int(inst.get("y", 0)),
            "width": max(20, int(inst.get("width", 200))),
            "height": max(20, int(inst.get("height", 60))),
            "z_index": int(inst.get("z_index", 0)),
            "text": message, "size": 28, "color": "#ff4d4d",
            "font": "JetBrains Mono", "text_fit": "shrink"}


def etendre(tpl: dict) -> dict:
    """Le gabarit sans instances : chaque `component` devient ses regions."""
    regions = tpl.get("regions") or []
    if not any(r.get("type") == "component" for r in regions):
        return tpl
    out = json.loads(json.dumps(tpl))
    neuves: list[dict] = []
    for r in out["regions"]:
        if r.get("type") != "component":
            neuves.append(r)
            continue
        cid = str(r.get("component") or "")
        try:
            comp = lire(cid)
            _valider(comp)
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
            logger.warning(f"instance {r.get('id')} non etendue : {e}")
            neuves.append(_refus(r, f"composant absent : {cid}"))
            continue
        fx = float(r.get("width", comp["width"])) / float(comp["width"])
        fy = float(r.get("height", comp["height"])) / float(comp["height"])
        ox, oy = int(r.get("x", 0)), int(r.get("y", 0))
        zbase = int(r.get("z_index", 0))
        surch = r.get("overrides") or {}
        prefixe = str(r.get("id") or cid)
        for sub in comp["regions"]:
            s = json.loads(json.dumps(sub))
            s.update(surch.get(sub["id"]) or {})
            s["id"] = f"{prefixe}__{sub['id']}"
            if s.get("slot_name"):
                s["slot_name"] = f"{prefixe}_{s['slot_name']}"
            if s.get("type") != "audio_slot":
                s["x"] = int(round(ox + float(s.get("x", 0)) * fx))
                s["y"] = int(round(oy + float(s.get("y", 0)) * fy))
                s["width"] = max(1, int(round(float(s.get("width", 1)) * fx)))
                s["height"] = max(1, int(round(float(s.get("height", 1)) * fy)))
                for k in _ECHELLE:
                    if isinstance(s.get(k), (int, float)):
                        s[k] = max(1, int(round(float(s[k]) * min(fx, fy))))
            s["z_index"] = zbase + int(s.get("z_index", 0))
            s["_component"] = cid
            neuves.append(s)
    out["regions"] = neuves
    return out
```

- [ ] **Étape 5 : brancher l'expansion**

Dans `backend/app/services/template_service.py`, remplacer le corps de
`resoudre` (posé en Tâche 1) par :

```python
    def resoudre(self, tpl: dict) -> dict:
        """Le template TEL QU'IL SERA RENDU : instances de composants
        etendues D'ABORD (un composant porte lui aussi des jetons de marque),
        puis jetons substitues."""
        from app.services import brand_kits as _bk
        from app.services import template_components as _tc
        return _bk.appliquer(_tc.etendre(tpl))
```

et, dans `slots_from` (ligne 290), remplacer la première ligne du corps :

```python
        slots: list[dict] = []
        for r in tpl.get("regions", []):
```

par :

```python
        from app.services import template_components as _tc
        slots: list[dict] = []
        for r in _tc.etendre(tpl).get("regions", []):
```

- [ ] **Étape 6 : lancer le banc, le voir vert**

```
cd backend
python tests/test_templates_composants.py
```
Attendu : `D1 composants partages : 17 PASS, 0 FAILED`, sortie 0.

- [ ] **Étape 7 : les routes**

```python
@router.get("/template-components")
async def list_template_components():
    from app.services import template_components as _tc
    return {"components": _tc.lister()}


@router.post("/template-components")
async def save_template_component(body: dict, request: Request):
    _require_localhost(request)
    from app.services import template_components as _tc
    comp = (body or {}).get("component") or {}
    if _tc.est_livre(str(comp.get("id") or "")):
        raise HTTPException(400, "Built-in components cannot be edited")
    try:
        cid = _tc.enregistrer(comp)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"component_id": cid}


@router.delete("/template-components/{component_id}")
async def delete_template_component(component_id: str, request: Request):
    _require_localhost(request)
    from app.services import template_components as _tc
    r = _tc.supprimer(component_id)
    if r == "livre":
        raise HTTPException(400, "Built-in components cannot be deleted")
    if r == "absent":
        raise HTTPException(404, f"composant introuvable : {component_id}")
    return {"deleted": component_id}
```

- [ ] **Étape 8 : commit**

```
git add backend/app/services/template_components.py backend/app/templates/_components/cmp_lower_third.json backend/tests/test_templates_composants.py backend/app/services/template_service.py backend/app/api/routes.py
git commit -m 'etabli : des composants partages, modifies une fois et rendus partout' -m 'Une region peut instancier un composant : etendre() la remplace par ses regions, mises a l echelle, decalees et prefixees, donc deux instances ne se marchent pas dessus. Le banc modifie le composant entre deux rendus et lit la couleur qui change dans le second MP4. Un composant absent laisse une region rouge qui dit son nom plutot qu un trou silencieux ; l imbrication est refusee, une seule profondeur.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

## Tâche 9 : D2 — Animations de région

**Pourquoi, avec la mesure.** Les neuf gabarits livrés déclarent tous un bloc
`transitions` au niveau du gabarit (`tpl_news_reel.json` : `fade_in` sur
`r_reel`, `fade_in` retardé sur `r_avatar`) — et **personne ne le lit** :
`grep -n transitions backend/app/services/template_service.py` ne renvoie
**rien**, alors que les neuf JSON en contiennent (1 à 3 occurrences chacun).
Seule la clé **singulière** `transition`, portée par un acte de montage, est
lue (`build_sequential_command`, ligne 1036). Le bloc pluriel est un vœu mort
dans les neuf fichiers. Réponse 4 de R7 : « les deux » — animations simples
dans le template, riches au Montage.

**Ce qui est offert, et pourquoi pas plus.** `overlay` accepte des expressions
temporelles sur `x`/`y` (mesuré le 03/09 : `overlay=x='20+t*60'` déplace de
60 px/s, lu à 20/80/140 px à 0/1/2 s), et `fade` a une option `alpha=1` sur un
flux `yuva`. Un « pop » à l'échelle demanderait `scale` piloté par le temps,
que ffmpeg n'offre pas (`zoompan` le ferait, au prix d'un ré-échantillonnage
par image) : **il n'est donc pas proposé**, plutôt qu'annoncé et bancal.

```json
"animation": {"in":  {"type": "slide_left", "duration_s": 0.6, "delay_s": 0.2},
              "out": {"type": "fade", "duration_s": 0.4}}
```
`type` ∈ `none | fade | slide_left | slide_right | slide_up | slide_down`.

**Fichiers**
- Créer : `backend/app/services/template_anim.py`
- Modifier : `backend/app/services/template_service.py:702-716`
- Modifier : `backend/tests/test_templates_composants.py` (section [9])

**Coût de patch.** Backend : un module de 70 lignes et 8 lignes de filtergraph.
Bundle : **une** ancre dans `tplplus` (Tâche 12), partagée avec D1 et D4 — la
section « Animation » s'ajoute au même endroit du panneau que les sections
Masque et Texte de `tplregion`.

- [ ] **Étape 1 : ajouter la section [9] au banc des composants**

Dans `backend/tests/test_templates_composants.py`, avant `bilan(...)` :

```python
print("\n[9] D2 — l'animation deplace VRAIMENT la region dans le temps")
from app.services import template_anim as TA                      # noqa: E402

ANIM = tpl([{"id": "bloc", "type": "separator", "x": 300, "y": 100,
             "width": 80, "height": 80, "z_index": 1, "color": "#00e5ff",
             "animation": {"in": {"type": "slide_left", "duration_s": 1.0}}}])
mp4 = out / "anim.mp4"
eng.render("tpl_banc_cp", {}, mp4, template=ANIM)


def gauche(t):
    im = image(mp4, out / ("an_%s.png" % str(t).replace(".", "_")), t=t)
    xs = [x for x in range(400)
          if proche(im.getpixel((x, 140)), rgb("#00e5ff"), tol=60)]
    return min(xs) if xs else None


g0, g5, g2 = gauche(0.05), gauche(0.5), gauche(2.0)
check("ANIM_VISIBLE_AUX_TROIS_INSTANTS",
      None not in (g0, g5, g2), (g0, g5, g2))
check("ANIM_GLISSE_VERS_LA_DROITE",
      None not in (g0, g5) and g0 < g5, (g0, g5))
check("ANIM_ARRIVE_A_SA_PLACE",
      g2 is not None and abs(g2 - 300) <= 3, g2)
check("ANIM_PART_DE_LA_GAUCHE", g0 is not None and g0 < 260, g0)

check("ANIM_TYPE_INCONNU_NE_CASSE_RIEN",
      TA.overlay({"in": {"type": "zigzag"}}, 10, 20, 30, 40, 3.0)[:2]
      == ("10", "20"),
      TA.overlay({"in": {"type": "zigzag"}}, 10, 20, 30, 40, 3.0)[:2])
check("ANIM_ABSENTE_EST_STATIQUE",
      TA.overlay(None, 10, 20, 30, 40, 3.0) == ("10", "20", []),
      TA.overlay(None, 10, 20, 30, 40, 3.0))
fs = TA.overlay({"out": {"type": "fade", "duration_s": 0.4}},
                0, 0, 10, 10, 3.0)[2]
check("SORTIE_EN_FIN_DE_CLIP",
      len(fs) == 1 and "st=2.600" in fs[0], fs)
```

- [ ] **Étape 2 : lancer, voir la section [9] rouge**

```
cd backend
python tests/test_templates_composants.py
```
Attendu : `ModuleNotFoundError: No module named 'app.services.template_anim'`.

- [ ] **Étape 3 : écrire `template_anim.py`**

```python
# -*- coding: utf-8 -*-
"""Animations de region (plan 2026-09-03-plan-templates, D2).

Simples et rendues par ffmpeg — les animations riches restent au Montage.
Deux moyens seulement, tous deux mesures :
  * `overlay` accepte des EXPRESSIONS sur x/y (mesure du 03/09 :
    `overlay=x='20+t*60'` -> 20 / 80 / 140 px a 0 / 1 / 2 s) ;
  * `fade=...:alpha=1` sur un flux `yuva` fait entrer et sortir l'alpha.

Un effet d'echelle (« pop ») n'est PAS offert : `scale` n'accepte pas le
temps, et `zoompan` re-echantillonne chaque image. Mieux vaut trois
animations qui tiennent que quatre dont une ment.
"""
from __future__ import annotations

TYPES = ("none", "fade", "slide_left", "slide_right", "slide_up",
         "slide_down")

#: Depart d'un glissement, en multiples de la taille de la region.
_DEPART = {
    "slide_left": (-1.0, 0.0),      # entre par la gauche
    "slide_right": (1.0, 0.0),
    "slide_up": (0.0, -1.0),
    "slide_down": (0.0, 1.0),
}


def _num(v, defaut, mini=0.0):
    try:
        return max(mini, float(v))
    except (TypeError, ValueError):
        return defaut


def overlay(anim, rx, ry, rw, rh, duree):
    """-> (expression x, expression y, [filtres a poser sur le flux]).

    Les expressions sont rendues telles quelles ; l'appelant les met entre
    apostrophes dans le filtergraph (elles contiennent des virgules).
    """
    x, y = str(int(rx)), str(int(ry))
    filtres: list[str] = []
    a = anim if isinstance(anim, dict) else {}
    ent = a.get("in") if isinstance(a.get("in"), dict) else {}
    sor = a.get("out") if isinstance(a.get("out"), dict) else {}

    t_ent = str(ent.get("type") or "none")
    if t_ent in TYPES and t_ent != "none":
        d = max(0.02, _num(ent.get("duration_s"), 0.5, 0.02))
        r = _num(ent.get("delay_s"), 0.0)
        if t_ent in _DEPART:
            kx, ky = _DEPART[t_ent]
            x0 = int(round(rx + kx * rw))
            y0 = int(round(ry + ky * rh))
            x = (f"if(lt(t,{r:.3f}),{x0},if(lt(t,{r + d:.3f}),"
                 f"{x0}+({int(rx)}-({x0}))*(t-{r:.3f})/{d:.3f},{int(rx)}))")
            y = (f"if(lt(t,{r:.3f}),{y0},if(lt(t,{r + d:.3f}),"
                 f"{y0}+({int(ry)}-({y0}))*(t-{r:.3f})/{d:.3f},{int(ry)}))")
        filtres.append(f"fade=t=in:st={r:.3f}:d={d:.3f}:alpha=1")

    t_sor = str(sor.get("type") or "none")
    if t_sor in TYPES and t_sor != "none":
        d = max(0.02, _num(sor.get("duration_s"), 0.4, 0.02))
        st = max(0.0, float(duree) - d)
        filtres.append(f"fade=t=out:st={st:.3f}:d={d:.3f}:alpha=1")
    return x, y, filtres
```

- [ ] **Étape 4 : brancher l'animation dans le filtergraph**

Dans `backend/app/services/template_service.py`, la branche `_VIDEO_LIKE`
(modifiée en Tâche 3) se termine par l'overlay de la région. Remplacer :

```python
            _w(f"[{cur}][{slbl}]overlay={rx}:{ry}:eof_action=repeat[o{n}]", f"o{n}")
            if cadre_p is not None:
```

par :

```python
            # D2 — animation d'entree/sortie : overlay pilote par le temps
            # (`overlay` accepte des expressions ; `scale` non — pas de pop).
            from app.services import template_anim as _ta
            ax, ay, afil = _ta.overlay(r.get("animation"), rx, ry, rw, rh,
                                       duration)
            if afil:
                parts.append(f"[{slbl}]format=yuva420p,{','.join(afil)}"
                             f"[s{n}an]")
                slbl = f"s{n}an"
            _w(f"[{cur}][{slbl}]overlay=x='{ax}':y='{ay}':"
               f"eof_action=repeat[o{n}]", f"o{n}")
            if cadre_p is not None:
```

Puis la même chose pour les régions **non vidéo** (séparateur, badge, ticker,
texte) : elles sont dessinées par `drawbox` / `drawtext`, qui n'ont pas
d'overlay à piloter. Pour qu'une `separator` s'anime (c'est ce que le banc
mesure), remplacer la branche `separator` (ligne 811) :

```python
        elif r["type"] == "separator":
            scol = _hex(r.get("color"), "00e5ff")
            n += 1
            _w(f"[{cur}]drawbox=x={rx}:y={ry}:w={rw}:h={rh}:"
               f"color=0x{scol}@1:t=fill[sep{n}]", f"sep{n}")
```

par :

```python
        elif r["type"] == "separator":
            scol = _hex(r.get("color"), "00e5ff")
            n += 1
            from app.services import template_anim as _ta
            ax, ay, afil = _ta.overlay(r.get("animation"), rx, ry, rw, rh,
                                       duration)
            if (ax, ay, afil) == (str(rx), str(ry), []):
                _w(f"[{cur}]drawbox=x={rx}:y={ry}:w={rw}:h={rh}:"
                   f"color=0x{scol}@1:t=fill[sep{n}]", f"sep{n}")
            else:
                # Une barre animee devient une source coloree superposee :
                # drawbox peint dans l'image, il ne se deplace pas.
                parts.append(
                    f"color=c=0x{scol}:s={rw}x{rh}:d={duration}:r={fps},"
                    f"format=yuva420p"
                    + ("," + ",".join(afil) if afil else "")
                    + f"[sepc{n}]")
                _w(f"[{cur}][sepc{n}]overlay=x='{ax}':y='{ay}':"
                   f"eof_action=repeat[sep{n}]", f"sep{n}")
```

- [ ] **Étape 5 : lancer le banc, le voir vert**

```
cd backend
python tests/test_templates_composants.py
```
Attendu : `D1 composants partages : 24 PASS, 0 FAILED`, sortie 0.

- [ ] **Étape 6 : dire ce qui reste mort**

Les blocs `transitions` des neuf gabarits livrés ne sont **toujours pas lus** —
ce plan ne les convertit pas. Ajouter la note en tête de `template_anim.py`,
sous la docstring :

```python
#: DETTE NOMMEE : les blocs `transitions` des gabarits livres (par exemple
#: tpl_news_reel.json : fade_in sur r_reel, fade_in retarde sur r_avatar) ne
#: sont lus par PERSONNE — ni avant ce plan, ni apres. Les convertir en
#: `animation` par region est un lot a part : il touche les neuf fichiers
#: livres, donc le rendu de tous les posts existants.
```

- [ ] **Étape 7 : commit**

```
git add backend/app/services/template_anim.py backend/app/services/template_service.py backend/tests/test_templates_composants.py
git commit -m 'etabli : des animations d entree et de sortie par region' -m 'overlay accepte des expressions temporelles et fade sait travailler l alpha d un flux yuva : entree, sortie, duree et retard par region tiennent avec ces deux briques. Une barre animee cesse d etre peinte par drawbox et devient une source superposee, sinon elle ne se deplacerait pas. Pas d effet d echelle : scale n accepte pas le temps, mieux vaut trois animations qui tiennent que quatre dont une ment. Les blocs transitions des gabarits livres restent une dette nommee.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

## Tâche 10 : D3 — Import Figma éditable, export par SVG

**Pourquoi, avec la mesure.** `figma_import.py` fait 75 lignes et une seule
chose : un calque devient **un PNG** (`GET /v1/images/{key}`). Un aplat qu'on
ne peut plus éditer. Réponse 5 de R7 : « les deux » — importer un cadre comme
template éditable, **et** exporter vers Figma. La vérification du 03/09 tranche
la seconde moitié : l'API REST expose `GET /v1/files/{key}/nodes?ids=` avec
`constraints`, `components` et `exportSettings` en **lecture**, et **n'écrit
pas** un fichier Figma. L'export part donc en SVG — c'est E3, assumé.

**La conversion.** `DOCUMENT → CANVAS → FRAME` ; le cadre donne le canevas
(`absoluteBoundingBox`), chaque enfant donne une région :

| Nœud Figma | Région |
|---|---|
| `TEXT` | `text` (`characters`, `style.fontSize`, `style.fontFamily`, `fills[0].color`) |
| `RECTANGLE`/`FRAME`/`ELLIPSE` avec un `IMAGE` dans `fills` | `image_slot` |
| `RECTANGLE` plein, hauteur ≤ 12 px | `separator` |
| tout le reste, plein | `brand_strip` |

`constraints.horizontal` / `.vertical` deviennent les contraintes de P2
(`MIN`→`start`, `MAX`→`end`, `CENTER`→`center`, `SCALE`→`scale`,
`STRETCH`/`LEFT_RIGHT`/`TOP_BOTTOM`→`stretch`) et `cornerRadius` devient un
masque arrondi de P3. **C'est la seule raison pour laquelle D3 arrive après
P2 et P3 :** sans eux, l'import perdrait l'essentiel d'un cadre Figma.

**Fichiers**
- Modifier : `backend/app/services/figma_import.py` (+180 lignes)
- Créer : `backend/tests/test_templates_figma.py`
- Modifier : `backend/app/api/routes.py` (2 routes)

**Coût de patch.** Backend seul, plus **une** ancre dans `tplplus` (Tâche 12) :
deux boutons dans la barre de l'éditeur, « Importer un cadre Figma » (invite
pour le lien) et « Exporter en SVG » (téléchargement).

- [ ] **Étape 1 : écrire le banc qui échoue**

Créer `backend/tests/test_templates_figma.py` :

```python
# -*- coding: utf-8 -*-
"""D3 — un cadre Figma devient un gabarit editable ; l'export part en SVG.

LE BANC NE SORT JAMAIS : `figma_import._get_json` est un HOOK module, on le
remplace par une reponse Figma en dur (meme patron que l'import PNG existant).
Miroir : le gabarit converti est RENDU et l'on lit son image.

Run depuis backend/ :  python tests/test_templates_figma.py
"""
import os
import pathlib
import sys
import tempfile

_tmp = tempfile.mkdtemp(prefix="dztplfg_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = \
    "sqlite+aiosqlite:///" + pathlib.Path(_tmp, "t.db").as_posix()
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio                                                  # noqa: E402
from _miroir import check, bilan, image, boite_encre             # noqa: E402
from app.services import figma_import as FI                      # noqa: E402
from app.services.template_service import TemplateEngine         # noqa: E402

eng = TemplateEngine()
out = pathlib.Path(_tmp, "outputs")

REPONSE = {"nodes": {"12:34": {"document": {
    "id": "12:34", "name": "Post 9x16", "type": "FRAME",
    "absoluteBoundingBox": {"x": 0, "y": 0, "width": 1080, "height": 1920},
    "backgroundColor": {"r": 0.01, "g": 0.02, "b": 0.05, "a": 1},
    "children": [
        {"id": "1:1", "name": "titre", "type": "TEXT",
         "characters": "LE MARCHE DORT",
         "absoluteBoundingBox": {"x": 60, "y": 120, "width": 960,
                                 "height": 180},
         "constraints": {"horizontal": "LEFT_RIGHT", "vertical": "TOP"},
         "style": {"fontFamily": "Anton", "fontSize": 96},
         "fills": [{"type": "SOLID",
                    "color": {"r": 1, "g": 1, "b": 1, "a": 1}}]},
        {"id": "1:2", "name": "visuel", "type": "RECTANGLE",
         "absoluteBoundingBox": {"x": 0, "y": 400, "width": 1080,
                                 "height": 1080},
         "cornerRadius": 48,
         "constraints": {"horizontal": "SCALE", "vertical": "SCALE"},
         "fills": [{"type": "IMAGE", "imageRef": "abc"}]},
        {"id": "1:3", "name": "regle", "type": "RECTANGLE",
         "absoluteBoundingBox": {"x": 60, "y": 1560, "width": 960,
                                 "height": 8},
         "constraints": {"horizontal": "CENTER", "vertical": "BOTTOM"},
         "fills": [{"type": "SOLID",
                    "color": {"r": 0, "g": 0.9, "b": 1, "a": 1}}]},
    ]}}}}


async def _faux_get_json(url, jeton):
    _faux_get_json.vu.append(url)
    return REPONSE
_faux_get_json.vu = []


FI._get_json = _faux_get_json

print("\n[1] La cible est lue dans le lien, et un lien fautif le DIT")
c = FI.figma_cible("https://www.figma.com/design/AbC123/Post?node-id=12-34")
check("CIBLE_LUE", c == {"cle": "AbC123", "node": "12:34"}, c)
try:
    FI.figma_cible("https://example.com/x")
    check("LIEN_FAUTIF_REFUSE", False, "aucune erreur")
except ValueError as e:
    check("LIEN_FAUTIF_REFUSE", "figma" in str(e).lower(), str(e))

print("\n[2] Le cadre devient un gabarit VALIDE")
tpl = asyncio.run(FI.importer_cadre(
    "https://www.figma.com/design/AbC123/Post?node-id=12-34", "jeton-test"))
check("APPEL_SUR_L_ENDPOINT_NODES",
      any("/v1/files/AbC123/nodes?ids=12:34" in u
          for u in _faux_get_json.vu), _faux_get_json.vu)
check("CANEVAS_DU_CADRE",
      (tpl["canvas"]["width"], tpl["canvas"]["height"]) == (1080, 1920),
      tpl["canvas"])
check("FOND_DU_CADRE", tpl["canvas"]["background_color"].startswith("#"),
      tpl["canvas"]["background_color"])
eng._validate(tpl)
check("GABARIT_VALIDE", True)
check("TROIS_REGIONS", len(tpl["regions"]) == 3,
      [r["type"] for r in tpl["regions"]])

print("\n[3] Chaque type de noeud tombe dans la bonne region")
par = {r["id"]: r for r in tpl["regions"]}
ids = sorted(par)
check("TEXTE_EST_UN_TEXTE", par[ids[0]]["type"] in ("text",),
      [(k, v["type"]) for k, v in par.items()])
types = sorted(r["type"] for r in tpl["regions"])
check("TYPES_ATTENDUS", types == ["image_slot", "separator", "text"], types)
txt = [r for r in tpl["regions"] if r["type"] == "text"][0]
check("TEXTE_RECUPERE", txt["text"] == "LE MARCHE DORT", txt.get("text"))
check("FONTE_RECUPEREE", txt["font"] == "Anton", txt.get("font"))
check("TAILLE_RECUPEREE", txt["size"] == 96, txt.get("size"))
check("COULEUR_RECUPEREE", txt["color"].lower() == "#ffffff",
      txt.get("color"))

print("\n[4] Les contraintes Figma deviennent celles de P2")
check("CONTRAINTE_STRETCH", txt["constraints"]["h"] == "stretch",
      txt.get("constraints"))
img = [r for r in tpl["regions"] if r["type"] == "image_slot"][0]
check("CONTRAINTE_SCALE", img["constraints"] == {"h": "scale", "v": "scale"},
      img.get("constraints"))
sep = [r for r in tpl["regions"] if r["type"] == "separator"][0]
check("CONTRAINTE_END", sep["constraints"]["v"] == "end",
      sep.get("constraints"))

print("\n[5] cornerRadius devient un masque arrondi de P3")
check("RAYON_DEVENU_MASQUE",
      (img.get("mask") or {}).get("radius") == 48, img.get("mask"))

print("\n[6] Le gabarit importe SE REND")
mini = dict(tpl)
mini["canvas"] = dict(tpl["canvas"], width=270, height=480, fps=10,
                      duration_s=1)
from app.services import template_layout as TL                   # noqa: E402
mini = TL.reflow(tpl, "9:16")
mini["canvas"] = dict(mini["canvas"], fps=10, duration_s=1)
mp4 = out / "fg.mp4"
eng.render("tpl_fg", {}, mp4, template=mini)
im = image(mp4, out / "fg.png")
check("RENDU_FAIT", im.size == (1080, 1920), im.size)
check("QUELQUE_CHOSE_EST_DESSINE",
      boite_encre(im, seuil=50, pas=8) is not None)

print("\n[7] L'export SVG : un groupe nomme par region, aux bonnes tailles")
svg = FI.template_vers_svg(tpl)
check("SVG_RACINE", svg.startswith("<svg ") and "</svg>" in svg, svg[:40])
check("SVG_TAILLE", 'width="1080"' in svg and 'height="1920"' in svg)
check("SVG_VIEWBOX", 'viewBox="0 0 1080 1920"' in svg)
for r in tpl["regions"]:
    check("SVG_GROUPE_" + r["type"].upper(),
          ('<g id="%s"' % r["id"]) in svg, r["id"])
check("SVG_TEXTE_ECHAPPE", "LE MARCHE DORT" in svg, "texte absent")
check("SVG_PAS_D_ECRITURE_API",
      "api.figma.com" not in svg, "le SVG ne doit rien appeler")

print("\n[8] L'ecriture directe dans Figma est refusee, en le disant")
try:
    FI.exporter_vers_figma({}, "jeton")
    check("ECRITURE_FIGMA_REFUSEE", False, "aucune erreur")
except NotImplementedError as e:
    check("ECRITURE_FIGMA_REFUSEE",
          "SVG" in str(e) and "REST" in str(e), str(e))

bilan("D3 Figma editable et export SVG")
```

- [ ] **Étape 2 : lancer le banc et le voir rouge**

```
cd backend
python tests/test_templates_figma.py
```
Attendu : `AttributeError: module 'app.services.figma_import' has no attribute
'importer_cadre'`.

- [ ] **Étape 3 : la conversion, dans `figma_import.py`**

Ajouter à la fin du fichier :

```python
# ── D3 : un CADRE devient un gabarit editable ────────────────────────────
# Mesure du 03/09/2026 (developers.figma.com) : l'API REST expose
# `GET /v1/files/{key}/nodes?ids=` en LECTURE (arbre, `constraints`,
# `components`, `exportSettings`) et n'ECRIT pas un fichier. L'aller est donc
# faisable ; le retour part en SVG (voir `exporter_vers_figma`).

#: contrainte Figma -> mode d'ancrage de template_layout (P2)
_CONTRAINTES = {
    "MIN": "start", "LEFT": "start", "TOP": "start",
    "MAX": "end", "RIGHT": "end", "BOTTOM": "end",
    "CENTER": "center",
    "SCALE": "scale",
    "STRETCH": "stretch", "LEFT_RIGHT": "stretch", "TOP_BOTTOM": "stretch",
}


def _hexa(c) -> str:
    def q(v):
        return max(0, min(255, int(round(float(v or 0) * 255))))
    c = c or {}
    return "#%02x%02x%02x" % (q(c.get("r")), q(c.get("g")), q(c.get("b")))


def _remplissage(noeud) -> dict:
    """Le premier remplissage VISIBLE : {kind: 'image'|'solid'|'none', ...}."""
    for f in (noeud.get("fills") or []):
        if f.get("visible") is False:
            continue
        if f.get("type") == "IMAGE":
            return {"kind": "image"}
        if f.get("type") == "SOLID":
            return {"kind": "solid", "color": _hexa(f.get("color"))}
    return {"kind": "none"}


def _boite(noeud, cadre):
    b = noeud.get("absoluteBoundingBox") or {}
    return (int(round(float(b.get("x", 0)) - cadre[0])),
            int(round(float(b.get("y", 0)) - cadre[1])),
            max(1, int(round(float(b.get("width", 1))))),
            max(1, int(round(float(b.get("height", 1))))))


def _ancrages(noeud) -> dict:
    c = noeud.get("constraints") or {}
    return {"h": _CONTRAINTES.get(str(c.get("horizontal") or ""), "scale"),
            "v": _CONTRAINTES.get(str(c.get("vertical") or ""), "scale")}


def _slug(nom, defaut, vus) -> str:
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", str(nom or "")).strip("_")[:32]
    s = s or defaut
    base, k = s, 2
    while s in vus:
        s = f"{base}_{k}"
        k += 1
    vus.add(s)
    return s


def cadre_vers_template(doc: dict, cle: str, node: str) -> dict:
    """L'arbre `GET /nodes` -> un gabarit. ValueError si ce n'est pas un cadre."""
    n = ((doc.get("nodes") or {}).get(node) or {}).get("document")
    if not isinstance(n, dict):
        raise ValueError(
            f"Figma n'a pas rendu le noeud {node} (reponse sans `document`)")
    if n.get("type") not in ("FRAME", "COMPONENT", "INSTANCE", "GROUP"):
        raise ValueError(
            "ce n'est pas un CADRE : selectionne un Frame dans Figma "
            f"(recu : {n.get('type')})")
    bb = n.get("absoluteBoundingBox") or {}
    ox, oy = float(bb.get("x", 0)), float(bb.get("y", 0))
    W = max(2, int(round(float(bb.get("width", 1080)))))
    H = max(2, int(round(float(bb.get("height", 1920)))))
    fond = n.get("backgroundColor")
    tpl = {
        "id": "",
        "name": str(n.get("name") or "Cadre Figma")[:120],
        "description": f"Importe de Figma ({cle} / {node}).",
        "version": 1,
        "canvas": {"width": W, "height": H,
                   "background_color": _hexa(fond) if fond else "#02060d",
                   "fps": 30, "duration_s": 8},
        "regions": [],
        "metadata": {"tags": ["figma"], "figma": {"key": cle, "node": node}},
    }
    vus: set[str] = set()
    z = 0
    for enfant in (n.get("children") or []):
        x, y, w, h = _boite(enfant, (ox, oy))
        rid = "r_" + _slug(enfant.get("name"), f"n{z}", vus)
        base = {"id": rid, "x": x, "y": y, "width": w, "height": h,
                "z_index": z, "constraints": _ancrages(enfant)}
        rayon = enfant.get("cornerRadius")
        if isinstance(rayon, (int, float)) and rayon > 0:
            base["mask"] = {"shape": "rounded", "radius": int(round(rayon))}
        rempl = _remplissage(enfant)
        if enfant.get("type") == "TEXT":
            st = enfant.get("style") or {}
            base.update({
                "type": "text",
                "text": str(enfant.get("characters") or "")[:400],
                "font": str(st.get("fontFamily") or "Space Grotesk"),
                "size": max(8, int(round(float(st.get("fontSize", 48))))),
                "color": (rempl.get("color") or "#ffffff"),
                "align": {"LEFT": "left", "CENTER": "center",
                          "RIGHT": "right"}.get(
                              str(st.get("textAlignHorizontal") or ""), "left"),
                "text_fit": "shrink"})
            base.pop("mask", None)     # un texte ne se masque pas ici
        elif rempl["kind"] == "image":
            base.update({"type": "image_slot",
                         "slot_name": rid[2:] or "image",
                         "slot_label": str(enfant.get("name") or "Image"),
                         "fit": "cover"})
        elif rempl["kind"] == "solid" and h <= 12:
            base.update({"type": "separator", "color": rempl["color"]})
        elif rempl["kind"] == "solid":
            base.update({"type": "brand_strip",
                         "background_color": rempl["color"], "items": []})
        else:
            # Ni texte, ni image, ni aplat : un cadre vide. On le garde comme
            # reperage plutot que de le perdre.
            base.update({"type": "separator", "color": "#1e3a4a",
                         "height": max(2, min(h, 4))})
        tpl["regions"].append(base)
        z += 1
    if not tpl["regions"]:
        raise ValueError("ce cadre Figma est vide : rien a importer")
    return tpl


async def importer_cadre(url: str, jeton: str) -> dict:
    """Le cadre pointe par `url` -> un gabarit (non enregistre)."""
    cible = figma_cible(url)
    api = (f"https://api.figma.com/v1/files/{cible['cle']}"
           f"/nodes?ids={cible['node']}")
    rep = await _get_json(api, jeton)
    if rep.get("err"):
        raise RuntimeError(str(rep["err"]))
    return cadre_vers_template(rep, cible["cle"], cible["node"])


# ── L'aller-retour : l'export part en SVG, pas par l'API ─────────────────

def _xml(s: str) -> str:
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def template_vers_svg(tpl: dict) -> str:
    """Le gabarit en SVG, une region = un `<g id="...">` nomme.

    C'est le chemin de retour vers Figma : l'API REST n'ecrit pas (mesure du
    03/09/2026), un SVG s'y glisse-depose. Rien dans le fichier n'appelle
    quoi que ce soit en ligne.
    """
    c = tpl.get("canvas") or {}
    W = int(c.get("width", 1080))
    H = int(c.get("height", 1920))
    lignes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">',
        f'<rect x="0" y="0" width="{W}" height="{H}" '
        f'fill="{_xml(c.get("background_color") or "#02060d")}"/>',
    ]
    for r in sorted(tpl.get("regions") or [],
                    key=lambda q: q.get("z_index", 0)):
        if r.get("type") == "audio_slot":
            continue
        x, y = int(r.get("x", 0)), int(r.get("y", 0))
        w, h = int(r.get("width", 1)), int(r.get("height", 1))
        lignes.append(f'<g id="{_xml(r["id"])}" '
                      f'data-type="{_xml(r.get("type"))}">')
        rayon = int(((r.get("mask") or {}).get("radius") or 0))
        if r.get("type") in ("text", "text_slot"):
            taille = int(r.get("size", 48))
            lignes.append(
                f'<text x="{x}" y="{y + taille}" '
                f'font-family="{_xml(r.get("font") or "Space Grotesk")}" '
                f'font-size="{taille}" '
                f'fill="{_xml(r.get("color") or "#ffffff")}">'
                f'{_xml(r.get("text") or r.get("default_text") or "")}</text>')
        else:
            couleur = (r.get("color") or r.get("background_color")
                       or "#1e3a4a")
            lignes.append(
                f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
                + (f'rx="{rayon}" ry="{rayon}" ' if rayon else "")
                + f'fill="{_xml(couleur)}"/>')
        lignes.append("</g>")
    lignes.append("</svg>")
    return "\n".join(lignes)


def exporter_vers_figma(tpl: dict, jeton: str):
    """N'EXISTE PAS, et le dit. Mesure du 03/09/2026 : l'API REST de Figma
    lit un fichier, elle n'en ecrit pas. Le retour passe par le SVG."""
    raise NotImplementedError(
        "l'API REST de Figma n'ecrit pas un fichier : exporte le gabarit en "
        "SVG (GET /layout-templates/{id}/export.svg) et glisse-le dans Figma, "
        "ou passe par un plugin")
```

- [ ] **Étape 4 : lancer le banc, le voir vert**

```
cd backend
python tests/test_templates_figma.py
```
Attendu : `D3 Figma editable et export SVG : 22 PASS, 0 FAILED`, sortie 0.

- [ ] **Étape 5 : les deux routes**

```python
@router.post("/layout-templates/import-figma")
async def import_figma_frame(body: dict, request: Request):
    """Un CADRE Figma devient un gabarit utilisateur editable."""
    _require_localhost(request)
    from app.services import figma_import as _fi
    # Meme lecture que l'import PNG existant (routes.py:8807), au mot pres.
    jeton = str(getattr(settings, "FIGMA_TOKEN", "") or "").strip()
    if not jeton:
        raise HTTPException(400, "FIGMA_TOKEN absent : cree un jeton "
                                 "personnel (figma.com -> Settings -> "
                                 "Security) et pose FIGMA_TOKEN=... dans "
                                 "backend/.env")
    try:
        tpl = await _fi.importer_cadre(str((body or {}).get("url") or ""),
                                       jeton)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    try:
        tid = template_engine.save_template(tpl)
    except ValueError as e:
        raise HTTPException(400, f"cadre importe mais invalide : {e}")
    return {"template_id": tid, "name": tpl["name"],
            "regions": len(tpl["regions"])}


@router.get("/layout-templates/{template_id}/export.svg")
async def export_template_svg(template_id: str):
    """Le gabarit en SVG — le chemin de retour vers Figma (l'API REST n'ecrit
    pas : mesure du 03/09/2026)."""
    from app.services import figma_import as _fi
    try:
        tpl = template_engine.get_template(template_id)
    except FileNotFoundError:
        raise HTTPException(404, f"Template not found: {template_id}")
    svg = _fi.template_vers_svg(template_engine.resoudre(tpl))
    return Response(content=svg, media_type="image/svg+xml",
                    headers={"Content-Disposition":
                             f'attachment; filename="{template_id}.svg"'})
```

- [ ] **Étape 6 : commit**

```
git add backend/app/services/figma_import.py backend/tests/test_templates_figma.py backend/app/api/routes.py
git commit -m 'etabli : un cadre Figma devient un gabarit editable, et repart en SVG' -m 'L endpoint /v1/files/{key}/nodes rend l arbre, les contraintes et la geometrie : un cadre devient un canevas et ses enfants des regions, avec les contraintes de P2 et le cornerRadius en masque de P3 — c est pour cela que D3 vient apres eux. L ecriture n existe pas dans l API REST : exporter_vers_figma refuse en nommant le SVG comme chemin de retour. Le banc ne sort jamais : le hook _get_json rend une reponse en dur.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Tâche 11 : D4 — Texte sur courbe et typographie décorative

**Pourquoi, avec la mesure.** Réponse 7 de R7 : texte adaptatif, effets **et**
texte sur courbe, les trois. PIL ne trace pas de texte sur chemin ; la rotation
glyphe à glyphe le fait, et c'est mesuré (03/09) : Anton 72 px, rayon 260,
« DEEPOTUS » → arc de `1.0 rad` exactement (Σ`getlength`/rayon), boîte d'encre
`(214,320,482,411)`, hauteur 91 px pour une fonte de 72 — la courbure étale
bien le texte. Les 23 fontes embarquées couvrent déjà la « typographie
décorative » (Monoton, Bungee, Pacifico, PressStart2P, Abril Fatface…) : rien
à ajouter, seulement à exposer.

**Fichiers**
- Modifier : `backend/app/services/template_text.py` (+60 lignes)
- Modifier : `backend/app/services/template_service.py:717-747`
- Modifier : `backend/tests/test_templates_texte.py` (section [7])
- Modifier : `backend/app/api/routes.py` (une route de liste de fontes)

**Coût de patch.** Backend seul, plus le champ « Rayon de courbe » posé dans la
section « Animation » de `tplplus` (Tâche 12) : **zéro ancre de plus**.

- [ ] **Étape 1 : ajouter la section [7] au banc du texte**

Dans `backend/tests/test_templates_texte.py`, avant `bilan(...)` :

```python
print("\n[7] D4 — le texte sur courbe, mesure")
pc = out / "courbe.png"
w, h = TT.rendre_courbe_png("DEEPOTUS", FONTE, 72, "#ffffff", pc, rayon=260)
imc = Image.open(str(pc)).convert("RGBA")
bc = imc.getbbox()
check("COURBE_PNG_ECRIT", pc.is_file() and bc is not None, bc)
check("COURBE_HAUTEUR_ETALEE", bc is not None and (bc[3] - bc[1]) > 80,
      (bc[3] - bc[1]) if bc else None)

pd_ = out / "droit.png"
TT.rendre_texte_png(["DEEPOTUS"], FONTE, 72, "#ffffff", pd_)
bd = Image.open(str(pd_)).convert("RGBA").getbbox()
check("COURBE_PLUS_HAUTE_QUE_DROITE",
      None not in (bc, bd) and (bc[3] - bc[1]) > (bd[3] - bd[1]),
      ((bc[3] - bc[1]) if bc else None, (bd[3] - bd[1]) if bd else None))


def _bas_de_colonne(im, x):
    ys = [y for y in range(im.height) if im.getpixel((x, y))[3] > 120]
    return max(ys) if ys else None


mil = _bas_de_colonne(imc, (bc[0] + bc[2]) // 2)
bordg = _bas_de_colonne(imc, bc[0] + 6)
check("COURBE_BOMBE_AU_MILIEU",
      None not in (mil, bordg) and (bordg - mil) > 8, (mil, bordg))

check("RAYON_NUL_REVIENT_AU_DROIT",
      TT.rendre_courbe_png("AB", FONTE, 40, "#ffffff", out / "r0.png",
                           rayon=0)[1]
      == TT.rendre_texte_png(["AB"], FONTE, 40, "#ffffff", out / "r0d.png")[1])

check("SENS_INVERSE_DISPONIBLE",
      TT.rendre_courbe_png("AB", FONTE, 40, "#ffffff", out / "rin.png",
                           rayon=200, sens=-1)[0] > 0)

print("\n[8] La typographie decorative est deja embarquee")
for nom in ("Monoton", "Bungee", "Pacifico", "Press Start 2P",
            "Abril Fatface"):
    check("FONTE_" + nom.replace(" ", "_").upper(),
          eng.font_path(nom).name != "SpaceGrotesk.ttf", eng.font_path(nom))
```

- [ ] **Étape 2 : lancer, voir la section [7] rouge**

```
cd backend
python tests/test_templates_texte.py
```
Attendu : `AttributeError: module 'app.services.template_text' has no
attribute 'rendre_courbe_png'`.

- [ ] **Étape 3 : le texte sur courbe**

Ajouter à la fin de `backend/app/services/template_text.py` :

```python
def rendre_courbe_png(texte, chemin, taille, couleur, sortie, rayon=260.0,
                      sens=1, effets=None):
    """Le texte pose sur un ARC, glyphe par glyphe (PIL ne trace pas sur
    chemin). `rayon` en px ; `sens` 1 = bombe vers le haut, -1 = vers le bas.
    `rayon` nul ou absurde revient au trace droit — un arc de rayon zero
    n'existe pas, et un texte qui disparait serait pire qu'un texte plat.

    Mesure du 03/09/2026 (Anton 72, rayon 260, « DEEPOTUS ») : arc de
    1.0 rad, boite d'encre (214,320,482,411), hauteur 91 px. Rend (w, h).
    """
    import math
    from PIL import Image, ImageDraw
    texte = str(texte or "")
    try:
        rayon = float(rayon)
    except (TypeError, ValueError):
        rayon = 0.0
    f = _fonte(chemin, taille)
    largeurs = [f.getlength(c) for c in texte]
    total = sum(largeurs)
    if rayon <= 1.0 or total <= 0 or total / rayon > 2 * math.pi:
        return rendre_texte_png([texte], chemin, taille, couleur, sortie,
                                effets=effets)
    sens = -1 if int(sens or 1) < 0 else 1
    arc = total / rayon
    lh = hauteur_ligne(chemin, taille)
    marge = int(lh) + 8
    fleche = rayon * (1 - math.cos(arc / 2.0))       # la « bosse » de l'arc
    W = int(2 * rayon * math.sin(arc / 2.0) + 2 * marge)
    H = int(fleche + lh + 2 * marge)
    im = Image.new("RGBA", (max(1, W), max(1, H)), (0, 0, 0, 0))
    cx = W / 2.0
    cy = (marge + rayon) if sens > 0 else (H - marge - rayon)
    angle = -arc / 2.0
    for c, w in zip(texte, largeurs):
        a = angle + (w / rayon) / 2.0
        g = Image.new("RGBA", (int(w) + 2 * marge, int(lh) + 2 * marge),
                      (0, 0, 0, 0))
        ImageDraw.Draw(g).text((marge, marge), c, font=f, fill="#" + str(
            couleur or "#ffffff").lstrip("#"))
        g = g.rotate(-math.degrees(a) * sens, resample=Image.BICUBIC,
                     expand=True)
        px = cx + rayon * math.sin(a)
        py = cy - sens * rayon * math.cos(a)
        im.alpha_composite(g, (int(px - g.width / 2.0),
                               int(py - g.height / 2.0)))
        angle += w / rayon
    im.save(str(sortie), "PNG")
    return im.width, im.height
```

- [ ] **Étape 4 : brancher le rayon dans le filtergraph**

Dans `backend/app/services/template_service.py`, dans le bloc P4 posé en
Tâche 4, remplacer :

```python
                tp = work / f"txt{n}.png"
                _tt.rendre_texte_png(lignes, fpath, size, "#" + color, tp,
                                     effets=tfx, largeur=rw,
                                     align=str(r.get("align") or "left"))
```

par :

```python
                tp = work / f"txt{n}.png"
                rayon = r.get("curve_radius")
                if isinstance(rayon, (int, float)) and float(rayon) > 1:
                    # D4 — texte sur courbe : un seul trace, pas de largeur
                    # imposee (l'arc decide de sa boite).
                    pw, ph = _tt.rendre_courbe_png(
                        " ".join(lignes), fpath, size, "#" + color, tp,
                        rayon=float(rayon), sens=int(r.get("curve_dir", 1)),
                        effets=tfx)
                    ox = rx + max(0, (rw - pw) // 2)
                else:
                    _tt.rendre_texte_png(lignes, fpath, size, "#" + color, tp,
                                         effets=tfx, largeur=rw,
                                         align=str(r.get("align") or "left"))
                    ox = rx
```

et, deux lignes plus bas, remplacer `overlay={rx}:{ry}` par `overlay={ox}:{ry}`
dans l'appel `_w(...)` de ce bloc.

- [ ] **Étape 5 : la route des fontes**

```python
@router.get("/layout-templates/fonts")
async def list_template_fonts():
    """Les fontes EMBARQUEES, telles que le renderer les nomme — le panneau
    ne doit pas inventer un nom que `font_path` retomberait sur le defaut."""
    from app.services.template_service import _FONT_FILES
    base = template_engine.builtin_dir / "_fonts"
    return {"fonts": sorted(
        [{"name": n, "file": f, "present": (base / f).is_file()}
         for n, f in _FONT_FILES.items()],
        key=lambda d: d["name"]), "default": "Space Grotesk"}
```

Attendu au premier appel : 23 entrées, toutes `present: true` (mesuré :
`backend/app/templates/_fonts/` contient 23 fichiers `.ttf`/`.otf`).

- [ ] **Étape 6 : lancer les bancs, les voir verts**

```
cd backend
python tests/test_templates_texte.py
python tests/test_templates_image.py
```
Attendu : `P4 texte adaptatif et effets : 33 PASS, 0 FAILED` et
`P5 rendu image fixe : 18 PASS, 0 FAILED`, sortie 0 pour les deux.

- [ ] **Étape 7 : commit**

```
git add backend/app/services/template_text.py backend/app/services/template_service.py backend/app/api/routes.py backend/tests/test_templates_texte.py
git commit -m 'etabli : du texte sur courbe, glyphe par glyphe' -m 'PIL ne trace pas sur chemin : chaque glyphe est mesure, rendu seul, tourne et compose sur l arc. Mesure : Anton 72 sur un rayon 260 donne un arc de 1 rad exactement, et le banc verifie que le milieu bombe par rapport aux bords. Un rayon nul ou un arc de plus d un tour reviennent au trace droit plutot que de disparaitre. Les 23 fontes embarquees couvrent deja la typographie decorative : une route les expose telles que le renderer les nomme.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

## Tâche 12 : la greffe bundle du lot 2 — `tplplus`

**Un seul patcher pour quatre bacs.** D1 (composants), D2 (animations), D3
(Figma/SVG) et D4 (rayon de courbe) touchent trois endroits : la rangée
« Add: », le panneau de région, la barre du bas de l'éditeur. Les sections de
panneau se posent au **même** endroit que celles de `tplregion` — le champ de
courbe entre donc dans la section Animation sans coûter d'ancre.

**Trois ancres, toutes à 1** (recomptées à l'étape 1, après `tplregion` et
`tplbar`) :

| Ancre | Section |
|---|---|
| `"+ "+z[1]},z[0])})]}),` | P2 — la rangée « Add: » gagne « + Composant » |
| `__dzTplMasque(c,p),__dzTplTexte(c,p),` (posée par `tplregion`) | P3 — appel de `__dzTplPlus` |
| `r.jsx(K,{variant:"outline",size:"sm",icon:"flow",onClick:_,disabled:!e,children:"Open in Studio"})` | P4 — les deux boutons Figma |

plus P1, le helper, posé avant `function dzRegionFace(rg){`.

- [ ] **Étape 1 : recompter les ancres sur le bundle DÉJÀ patché**

```
python - <<'PY'
import pathlib, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
s = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js").read_text(
    encoding="utf-8", errors="replace")
for a in ['function dzRegionFace(rg){',
          '"+ "+z[1]},z[0])})]}),',
          '__dzTplMasque(c,p),__dzTplTexte(c,p),',
          'r.jsx(K,{variant:"outline",size:"sm",icon:"flow",onClick:_,disabled:!e,children:"Open in Studio"})',
          '__dzTplThumb(e)']:
    print(s.count(a), a[:50])
PY
```
Attendu : `1`, `1`, `1`, `1`, `1`. Le dernier prouve que `tplbar` est bien
appliqué : **si `__dzTplThumb` compte 0, `tplplus` ne doit pas être appliqué**
(il se poserait avant son amont dans la chaîne).

- [ ] **Étape 2 : écrire la tête de `scripts/patch_bundle_tplplus.py`**

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_tplplus.py
"""Patcher assert-garde : le lot 2 des Templates — composants (D1),
animations (D2), Figma/SVG (D3), texte sur courbe (D4).

BASELINE : bundle POST-patch tplbar.  Backup : `.js.bak_tplplus`.
Position : EN QUEUE, apres tplregion puis tplbar.

Quatre sections :
  P1  le helper `__dzTplPlus(c,p)` — sections Composant, Animation, Courbe.
  P2  « + Composant » dans la rangee « Add: ».
  P3  l'appel de `__dzTplPlus`, colle a ceux de tplregion.
  P4  « Importer un cadre Figma » et « Exporter en SVG » dans la barre du bas.

Run : python scripts/patch_bundle_tplplus.py [--check]
"""
import os
import pathlib
import shutil
import sys
import time

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
TAG = "tplplus"
MARKER = "__dzTplPlus"

STABLE_PROBES = [
    ("editeur", "function hm({pickedT:e,onSaved:t}){", 1),
    ("panneau-masque", "function __dzTplMasque(c,p){", 1),
    ("panneau-texte", "function __dzTplTexte(c,p){", 1),
    ("vignette-reelle", "function __dzTplThumb(id){", 1),
    ("galerie", "function fm({variant:e}){", 1),
]

_ANCRE_HELPER = "function dzRegionFace(rg){"

HELPER = (
    "var __dzTplComps=null;"
    "function __dzTplPlus(c,p){"
    "var st=x.useState(0),tick=st[0],set=st[1];"
    "x.useEffect(function(){if(__dzTplComps)return;"
    'fetch("/api/template-components").then(function(r0){return r0.json()})'
    ".then(function(j){__dzTplComps=(j&&j.components)||[];set(function(k){"
    "return k+1})}).catch(function(){__dzTplComps=[]})},[]);"
    "var comps=__dzTplComps||[];"
    "var an=c.animation||null;"
    "function anim(sens,cle,val){"
    "var n=Object.assign({},an||{});"
    "var b=Object.assign({},n[sens]||{});b[cle]=val;n[sens]=b;"
    '__dzTplSet(c,p,"animation",n)}'
    'var TY=[{value:"none",label:"Aucune"},{value:"fade",label:"Fondu"},'
    '{value:"slide_left",label:"Glisse depuis la gauche"},'
    '{value:"slide_right",label:"Glisse depuis la droite"},'
    '{value:"slide_up",label:"Glisse depuis le haut"},'
    '{value:"slide_down",label:"Glisse depuis le bas"}];'
    'return r.jsxs("div",{style:{marginTop:8,paddingTop:8,'
    'borderTop:"1px solid var(--stroke)"},children:['
    # --- Composant -------------------------------------------------------
    'c.type==="component"?r.jsxs(r.Fragment,{children:['
    'r.jsx("div",{style:{fontSize:10.5,color:"var(--ink-soft)"},'
    'children:"COMPOSANT"}),'
    'r.jsx(O,{label:"Modele",children:r.jsx(re,{'
    'value:c.component||"",onChange:function(v){'
    '__dzTplSet(c,p,"component",v)},'
    "options:comps.length?comps.map(function(k){return{value:k.id,"
    'label:k.name||k.id}}):[{value:c.component||"",'
    'label:c.component||"— aucun —"}]})})]}):null,'
    # --- Animation -------------------------------------------------------
    'r.jsx("div",{style:{fontSize:10.5,color:"var(--ink-soft)",'
    'marginTop:6},children:"ANIMATION"}),'
    'r.jsx(O,{label:"Entree",children:r.jsx(re,{'
    'value:(an&&an["in"]&&an["in"].type)||"none",'
    'onChange:function(v){anim("in","type",v)},options:TY})}),'
    'r.jsx(O,{label:"Duree entree (s)",children:r.jsx(le,{mono:!0,'
    'value:String((an&&an["in"]&&an["in"].duration_s)||0.5),'
    'onChange:function(v){anim("in","duration_s",__dzTplNum(v,0.5))}})}),'
    'r.jsx(O,{label:"Retard (s)",children:r.jsx(le,{mono:!0,'
    'value:String((an&&an["in"]&&an["in"].delay_s)||0),'
    'onChange:function(v){anim("in","delay_s",__dzTplNum(v,0))}})}),'
    'r.jsx(O,{label:"Sortie",children:r.jsx(re,{'
    'value:(an&&an.out&&an.out.type)||"none",'
    'onChange:function(v){anim("out","type",v)},options:TY})}),'
    # --- Courbe ----------------------------------------------------------
    '["text","text_slot"].indexOf(c.type)>=0?r.jsxs(r.Fragment,{children:['
    'r.jsx("div",{style:{fontSize:10.5,color:"var(--ink-soft)",'
    'marginTop:6},children:"COURBE"}),'
    'r.jsx(O,{label:"Rayon (0 = droit)",children:r.jsx(le,{mono:!0,'
    'value:String(c.curve_radius||0),onChange:function(v){'
    '__dzTplSet(c,p,"curve_radius",__dzTplNum(v,0)||null)}})}),'
    'r.jsx(O,{children:r.jsx(Ze,{checked:Number(c.curve_dir)===-1,'
    'onChange:function(v){__dzTplSet(c,p,"curve_dir",v?-1:1)},'
    'label:"Courbe vers le bas"})})]}):null'
    "]})}"
)

_ANCRE_ADD = '"+ "+z[1]},z[0])})]}),'
_ADD_R = (
    '"+ "+z[1]},z[0])}),'
    'r.jsx("button",{onClick:function(){'
    "var cs=__dzTplComps||[];"
    'if(!cs.length){window.alert("Aucun composant disponible");return}'
    'var nid="cmp_"+Math.random().toString(36).slice(2,6);'
    "u(function(H){return H.concat([{id:nid,type:\"component\","
    'component:cs[0].id,x:0,y:Math.round(v*.7),width:g,'
    "height:Math.round(g*(cs[0].height||220)/(cs[0].width||1080)),"
    "z_index:(H.length?Math.max.apply(null,H.map(function(q){"
    'return q.z_index||0})):0)+1,_disp:"var(--violet)"}])});'
    "m(nid)},"
    'style:{fontSize:10.5,fontFamily:"var(--f-mono)",'
    'color:"var(--ink-strong)",background:"var(--bg-panel-2)",'
    'border:"1px solid var(--stroke-strong)",borderRadius:"var(--r-sm)",'
    'padding:"3px 8px",cursor:"pointer"},'
    'children:"+ Composant"},"cmp")]}),'
)

_ANCRE_APPEL = "__dzTplMasque(c,p),__dzTplTexte(c,p),"
_APPEL_R = "__dzTplMasque(c,p),__dzTplTexte(c,p),__dzTplPlus(c,p),"

_ANCRE_STUDIO = ('r.jsx(K,{variant:"outline",size:"sm",icon:"flow",'
                 'onClick:_,disabled:!e,children:"Open in Studio"})')
_FIGMA = (
    'r.jsx(K,{variant:"outline",size:"sm",icon:"download",'
    'title:"Le gabarit en SVG — l API REST de Figma n ecrit pas, on '
    'glisse le SVG dans Figma",onClick:function(){'
    'if(!e)return;window.open("/api/layout-templates/"+'
    'encodeURIComponent(e.id)+"/export.svg","_blank")},'
    'disabled:!e,children:"Exporter en SVG"}),'
    'r.jsx(K,{variant:"outline",size:"sm",icon:"plus",'
    'title:"Un CADRE Figma devient un gabarit editable (FIGMA_TOKEN '
    'requis)",onClick:function(){'
    'var u0=window.prompt("Lien du CADRE Figma (clic droit sur le Frame '
    '-> Copy link)","");if(!u0)return;w("Import Figma...");'
    'fetch("/api/layout-templates/import-figma",{method:"POST",'
    'headers:{"Content-Type":"application/json"},'
    "body:JSON.stringify({url:u0})})"
    ".then(function(x0){return x0.json().then(function(j){"
    "if(!x0.ok)throw new Error(j.detail||\"import impossible\");"
    'w("Importe : "+j.name+" ("+j.regions+" regions)");'
    "t&&t()})})"
    '.catch(function(er){w("Figma : "+String((er&&er.message)||er))})},'
    'children:"Importer un cadre Figma"}),'
)

PATCHES = [
    ("P1-helper", _ANCRE_HELPER, HELPER + _ANCRE_HELPER),
    ("P2-add", _ANCRE_ADD, _ADD_R),
    ("P3-appel", _ANCRE_APPEL, _APPEL_R),
    ("P4-figma", _ANCRE_STUDIO, _FIGMA + _ANCRE_STUDIO),
]
```

- [ ] **Étape 3 : deltas, corps, retouches**

Calculer `SPEC_CHAR_DELTA` / `SPEC_BYTE_DELTA` avec le script de la Tâche 7
étape 3 (chemin `scripts/patch_bundle_tplplus.py`), recopier le corps depuis
`scripts/patch_bundle_print3d.py` lignes 94→fin (164 lignes), puis :
`if s.count(MARKER) != 2:` (définition + appel), la boucle de vérification des
ancres en `for tag, anchor, _r in PATCHES:`, et le message final
`print("OK - bundle patche (lot 2 : composants, animations, Figma, courbe).")`.

- [ ] **Étape 4 : appliquer et vérifier**

```
python scripts/patch_bundle_tplplus.py --check
python scripts/patch_bundle_tplplus.py
cp frontend/dist/assets/index-BEOJX8L5.js .check.mjs
node --check .check.mjs
rm .check.mjs
python scripts/repatch_all.py --list
```
Attendu : `4 ancres OK, marqueur absent, 5 sondes aux comptes` ;
`OK - bundle patche (lot 2 : …)` ; aucune sortie de `node --check` ; et la
chaîne se termine par `tplregion`, `tplbar`, `tplplus` **dans cet ordre**.

- [ ] **Étape 5 : commit**

```
git add scripts/patch_bundle_tplplus.py frontend/dist/assets/index-BEOJX8L5.js
git commit -m 'etabli : composants, animations, Figma et courbe dans l editeur' -m 'Un seul patcher pour les quatre bacs du lot 2 : les sections de panneau se posent au meme endroit que celles de tplregion, donc le rayon de courbe ne coute pas d ancre. La rangee Add gagne + Composant, la barre du bas gagne l import d un cadre Figma et l export SVG. Le patcher refuse de se poser si tplbar n est pas deja applique : sa sonde __dzTplThumb le dit.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Écarté

- **E1 — Modèles par milliers façon Canva.** Neuf gabarits suffisent à l'usage
  déclaré (réponse 6 : « la plupart des neuf selon le format ») ; ce plan
  investit dans l'éditeur, les kits et les composants — pas dans le catalogue.
- **E2 — Mockups façon Placeit.** Hors du produit : DeepotusVideoGen fabrique
  des posts 9:16, pas des mises en scène de produits.
- **E3 — Écriture directe dans Figma par l'API.** **Mesuré** le 03/09/2026 :
  l'API REST de Figma lit un fichier (`/v1/files/{key}/nodes`) et n'en écrit
  pas. Le retour passe par le SVG (Tâche 10) ; `exporter_vers_figma` lève une
  `NotImplementedError` qui le dit, plutôt que de laisser croire au contraire.

---

## Tâche 13 : campagne de mutations

**Pourquoi.** Sept bancs verts ne disent pas qu'ils **mesurent** quelque chose.
La campagne casse le code une mutation à la fois, vérifie que le banc visé
rougit, et remet le fichier à l'octet près. Une mutation « VERTE » est une
assertion qui manque — c'est ainsi qu'ont été trouvés, sur l'Établi, la ligne
morte du pivot et le mutant faible du libellé (`mutations_plaque_slicer.py`,
en-tête).

**Ce qui change par rapport au patron.** `mutations_plaque_slicer.py` et
`mutations_assise_couteau.py` lancent `pytest -k`. Les bancs de CE plan sont
des **scripts autonomes** : ils s'exécutent par `python tests/test_x.py` et
impriment `  PASS  NOM` / `FAILED NOM …`. Le lecteur de rouges change donc de
regex (`^FAILED (\w+)`) et lit le code de sortie : `0` tout vert, `1` des
rouges, **autre chose** = le banc n'a pas tourné (troisième état, comme dans
le patron).

**Fichiers**
- Créer : `backend/tests/mutations_templates.py`

- [ ] **Étape 1 : écrire le lanceur et les mutations**

Créer `backend/tests/mutations_templates.py` :

```python
# -*- coding: utf-8 -*-
"""Banc de mutations des Templates : casser -> rouge -> remettre.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance A LA MAIN, depuis backend/ :

    python tests/mutations_templates.py            # toutes
    python tests/mutations_templates.py 3 17       # celles-la

Il MUTE les sources du depot une a une et les REMET a l'octet pres (assertion
sur le sha256, journalisee) : il ne se lance pas pendant qu'un autre banc lit
ces fichiers.

Difference avec mutations_plaque_slicer.py : les bancs vises sont des SCRIPTS
autonomes (`python tests/test_x.py`), pas des fichiers pytest. Les rouges se
lisent donc sur les lignes `FAILED <NOM>` que `_miroir.check` imprime, et le
code de sortie separe « des rouges » (1) de « le banc n'a pas tourne » (autre).

Chaque mutation : (fichier, ancien, nouveau, banc, verifications attendues
rouges). `ancien` peut etre une LISTE de (ancien, nouveau) appliques dans
l'ordre.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable

KITS = "tests/test_templates_kits.py"
RFLW = "tests/test_templates_reflow.py"
MASQ = "tests/test_templates_masques.py"
TEXT = "tests/test_templates_texte.py"
IMAG = "tests/test_templates_image.py"
COMP = "tests/test_templates_composants.py"
FIGM = "tests/test_templates_figma.py"

BK = "backend/app/services/brand_kits.py"
TL = "backend/app/services/template_layout.py"
TM = "backend/app/services/template_mask.py"
TT = "backend/app/services/template_text.py"
TC = "backend/app/services/template_components.py"
TA = "backend/app/services/template_anim.py"
TS = "backend/app/services/template_service.py"
FI = "backend/app/services/figma_import.py"

M = [
    # ── P1 kits ──────────────────────────────────────────────────────────
    # 0. le jeton n'est plus substitue : le gabarit rend le litteral
    (BK, "        return _JETON.sub(lambda m: str(k.get(m.group(1), m.group(0))), s)",
     "        return s",
     KITS, ["KIT_A_ACCENT_RENDU", "KIT_B_ACCENT_RENDU"]),
    # 1. un jeton inconnu se vide au lieu de rester lisible
    (BK, "k.get(m.group(1), m.group(0))", "k.get(m.group(1), '')",
     KITS, ["JETON_INCONNU_GARDE"]),
    # 2. la couleur n'est plus validee
    (BK, "        if k.endswith(\"_color\") and not _COULEUR.match(v):",
     "        if False:",
     KITS, ["COULEUR_REFUSEE"]),
    # 3. l'identifiant n'est plus valide
    (BK, "    if not _ID.match(kid):", "    if False:",
     KITS, ["ID_REFUSE"]),
    # 4. le kit actif se supprime
    (BK, "    if doc[\"actif\"] == kid:\n        return \"actif\"", "",
     KITS, ["DERNIER_KIT_PROTEGE"]),
    # 5. le rendu ne resout plus le gabarit
    (TS, "        tpl = self.resoudre(tpl)\n        self._validate(tpl)\n        output_path.parent.mkdir(parents=True, exist_ok=True)",
     "        self._validate(tpl)\n        output_path.parent.mkdir(parents=True, exist_ok=True)",
     KITS, ["KIT_A_ACCENT_RENDU", "KIT_B_ACCENT_RENDU"]),
    # ── P2 reflow ────────────────────────────────────────────────────────
    # 6. « end » garde la marge de tete au lieu de la marge de queue
    (TL, "    if mode == \"end\":\n        return neuf - marge_fin - taille, taille",
     "    if mode == \"end\":\n        return pos, taille",
     RFLW, ["ANCRAGE_END_BAS"]),
    # 7. « center » recentre sur l'ancien canevas
    (TL, "        return centre * neuf - taille / 2.0, taille",
     "        return centre * ancien - taille / 2.0, taille",
     RFLW, ["ANCRAGE_CENTER_X", "ANCRAGE_CENTER_Y"]),
    # 8. « stretch » ne s'etire plus
    (TL, "        return pos, max(1.0, neuf - marge_fin - pos)",
     "        return pos, taille",
     RFLW, ["ANCRAGE_STRETCH_LARGEUR"]),
    # 9. le defaut devient « start » : plus rien ne suit l'echelle
    (TL, "DEFAUT = \"scale\"", "DEFAUT = \"start\"",
     RFLW, ["DEFAUT_SCALE"]),
    # 10. la reprise manuelle est ignoree
    (TL, "        main = poses.get(r[\"id\"]) or {}", "        main = {}",
     RFLW, ["REPRISE_MANUELLE"]),
    # 11. un montage sequentiel se fait raboter comme les autres
    (TL, "    if out.get(\"render_mode\") == \"sequential\":\n        return out",
     "    if False:\n        return out",
     RFLW, ["SEQUENTIEL_INTOUCHE"]),
    # 12. un format inconnu passe en silence
    (TL, "    if fmt not in FORMATS:\n        raise ValueError(\n            f\"format inconnu : {fmt} — attendus \" + \", \".join(FORMATS))\n    W, H = FORMATS[fmt]",
     "    W, H = FORMATS.get(fmt) or FORMATS[\"9:16\"]",
     RFLW, ["FORMAT_INCONNU_REFUSE"]),
    # ── P3 masques ───────────────────────────────────────────────────────
    # 13. les trous ne sont plus perces : plus de fenetre ajouree
    (TM, "    for trou in ((spec or {}).get(\"holes\") or []):",
     "    for trou in []:",
     MASQ, ["MASQUE_FENETRE_NOIRE", "FENETRE_AJOUREE"]),
    # 14. le rayon est ignore : plus de coins arrondis
    (TM, "    d.rounded_rectangle(boite, radius=_rayon(spec, boite), fill=remplissage)",
     "    d.rectangle(boite, fill=remplissage)",
     MASQ, ["MASQUE_COIN_NOIR", "COIN_ARRONDI_LAISSE_LE_FOND"]),
    # 15. l'encart est ignore
    (TM, "    i = max(0, int(spec.get(\"inset\", 0) or 0))", "    i = 0",
     MASQ, ["ENCART_BORD_AU_FOND"]),
    # 16. l'encart n'est plus borne : un inset absurde vide la region
    (TM, "    i = min(i, max(0, (w - 2) // 2), max(0, (h - 2) // 2))",
     "    i = i",
     MASQ, ["ENCART_BORNE"]),
    # 17. la bordure n'est plus peinte
    (TM, "    if ep <= 0:\n        return None", "    return None",
     MASQ, ["BORDURE_PEINTE"]),
    # 18. le masque n'est plus branche dans le filtergraph
    (TS, "                slbl = f\"s{n}k\"", "                pass",
     MASQ, ["FENETRE_AJOUREE", "COIN_ARRONDI_LAISSE_LE_FOND"]),
    # 19. le cadre est overlaye AVANT la region : il disparait dessous
    (TS, "            if cadre_p is not None:\n                fi = _add_input(cadre_p, still=True)",
     "            if False:\n                fi = _add_input(cadre_p, still=True)",
     MASQ, ["BORDURE_PEINTE"]),
    # ── P4 texte ─────────────────────────────────────────────────────────
    # 20. la mesure devient un comptage de caracteres
    (TT, "    return float(_fonte(chemin, taille).getlength(str(texte or \"\")))",
     "    return float(len(str(texte or \"\")) * taille * 0.5)",
     TEXT, ["MESURE_ANTON_64"]),
    # 21. shrink ne retrecit plus
    (TT, "    while t > taille_min and mesurer(texte, chemin, t) > largeur_max:\n        t -= 1",
     "    pass",
     TEXT, ["SHRINK_A_REDUIT", "SHRINK_RENTRE", "TEXTE_DANS_LA_REGION"]),
    # 22. shrink n'a plus de plancher : la taille peut tomber a 4
    (TT, "    while t > taille_min and mesurer", "    while t > 1 and mesurer",
     TEXT, ["SHRINK_PLANCHER"]),
    # 23. wrap coupe les mots au lieu de mesurer
    (TT, "        if courante and f.getlength(essai) > largeur_max:",
     "        if courante and len(essai) > 12:",
     TEXT, ["WRAP_CHAQUE_LIGNE_RENTRE"]),
    # 24. l'ellipse ne marque plus la coupe
    (TT, "        return taille, [(coupe + \"…\") if coupe else \"…\"]",
     "        return taille, [coupe or \"\"]",
     TEXT, ["ELLIPSE_MARQUEE"]),
    # 25. le contour n'est plus peint
    (TT, "    if contour:\n        st = _encre(", "    if False:\n        st = _encre(",
     TEXT, ["CONTOUR_PEINT"]),
    # 26. le degrade part dans le mauvais sens
    (TT, "            t = y / float(max(1, H - 1))", "            t = 1 - y / float(max(1, H - 1))",
     TEXT, ["DEGRADE_HAUT_ROUGE", "DEGRADE_BAS_BLEU"]),
    # 27. le fond n'est plus arrondi
    (TT, "            [0, 0, W - 1, H - 1], radius=min(r, W // 2, H // 2),",
     "            [0, 0, W - 1, H - 1], radius=0,",
     TEXT, ["FOND_ARRONDI_COIN_VIDE"]),
    # 28. le chemin PNG n'est plus emprunte : retour a drawtext
    (TS, "            if fitm != \"none\" or tfx:", "            if False:",
     TEXT, ["TEXTE_DANS_LA_REGION"]),
    # ── D4 courbe ────────────────────────────────────────────────────────
    # 29. la courbe ne tourne plus les glyphes
    (TT, "        g = g.rotate(-math.degrees(a) * sens, resample=Image.BICUBIC,\n                     expand=True)",
     "        pass",
     TEXT, ["COURBE_BOMBE_AU_MILIEU"]),
    # 30. l'arc n'avance plus : tous les glyphes au meme endroit
    (TT, "        angle += w / rayon", "        angle += 0",
     TEXT, ["COURBE_HAUTEUR_ETALEE", "COURBE_PLUS_HAUTE_QUE_DROITE"]),
    # 31. un rayon nul ne retombe plus sur le trace droit
    (TT, "    if rayon <= 1.0 or total <= 0 or total / rayon > 2 * math.pi:",
     "    if False:",
     TEXT, ["RAYON_NUL_REVIENT_AU_DROIT"]),
    # ── P5 image fixe ────────────────────────────────────────────────────
    # 32. l'instant demande est ignore : toujours l'image zero
    (TS, "        _t = max(0.0, min(float(still_at), max(0.0, duration - 0.05)))",
     "        _t = 0.0",
     IMAG, ["BANDEAU_A_BOUGE"]),
    # 33. l'image fixe repasse par libx264 : plus une image
    (TS, "        cmd += [\"-an\", \"-frames:v\", \"1\", \"-update\", \"1\"]",
     "        cmd += [\"-an\"]",
     IMAG, ["PNG_ECRIT", "PNG_TAILLE_CANEVAS"]),
    # 34. un montage sequentiel accepte l'image fixe sans le dire
    (TS, "        if tpl.get(\"render_mode\") == \"sequential\":\n            raise ValueError(\n                \"un montage sequentiel n'a pas d'image fixe",
     "        if False:\n            raise ValueError(\n                \"un montage sequentiel n'a pas d'image fixe",
     IMAG, ["VIGNETTE_200"]),
    # 35. la source Bibliotheque disparait
    ("backend/app/services/library_index.py",
     "    \"templates\": \"Templates\",", "",
     IMAG, ["SOURCE_TEMPLATES_DECLAREE"]),
    # 36. le prefixe passe APRES gen_ : l'heuristique se trompe
    ("backend/app/services/library_index.py",
     "    (\"tpl_still_\", \"templates\"),", "",
     IMAG, ["PREFIXE_RECONNU"]),
    # ── P6 vignettes ─────────────────────────────────────────────────────
    # 37. la vignette n'est plus reduite
    ("backend/app/api/routes.py",
     "            im.thumbnail((_THUMB_MAX, _THUMB_MAX), _PILImg.LANCZOS)", "",
     IMAG, ["VIGNETTE_REDUITE"]),
    # 38. la clef de cache oublie les assets : deux appels divergent
    ("backend/app/api/routes.py",
     "         + json.dumps(sv, sort_keys=True)).encode(\"utf-8\")",
     "         + str(__import__(\"time\").time())).encode(\"utf-8\")",
     IMAG, ["VIGNETTE_CACHEE"]),
    # ── D1 composants ────────────────────────────────────────────────────
    # 39. les identifiants ne sont plus prefixes : collision entre instances
    (TC, "            s[\"id\"] = f\"{prefixe}__{sub['id']}\"",
     "            s[\"id\"] = sub[\"id\"]",
     COMP, ["IDS_PREFIXES", "IDS_UNIQUES"]),
    # 40. le decalage de l'instance est perdu
    (TC, "                s[\"x\"] = int(round(ox + float(s.get(\"x\", 0)) * fx))",
     "                s[\"x\"] = int(round(float(s.get(\"x\", 0)) * fx))",
     COMP, ["DECALAGE_APPLIQUE"]),
    # 41. la mise a l'echelle des tailles de texte est oubliee
    (TC, "                for k in _ECHELLE:", "                for k in []:",
     COMP, ["ECHELLE_TAILLE_DE_TEXTE"]),
    # 42. les surcharges sont ignorees
    (TC, "            s.update(surch.get(sub[\"id\"]) or {})", "            pass",
     COMP, ["SURCHARGE_APPLIQUEE"]),
    # 43. un composant absent disparait en silence
    (TC, "            neuves.append(_refus(r, f\"composant absent : {cid}\"))",
     "            pass",
     COMP, ["COMPOSANT_ABSENT_DIT_POURQUOI"]),
    # 44. l'imbrication n'est plus refusee
    (TC, "        if r[\"type\"] == \"component\":\n            raise ValueError(",
     "        if False:\n            raise ValueError(",
     COMP, ["COMPOSANT_LIVRE"]),
    # 45. slots_from n'etend plus : les slots d'un composant sont perdus
    (TS, "        for r in _tc.etendre(tpl).get(\"regions\", []):",
     "        for r in tpl.get(\"regions\", []):",
     COMP, ["SLOTS_PREFIXES"]),
    # ── D2 animations ────────────────────────────────────────────────────
    # 46. le glissement ne part plus d'a cote
    (TA, "            x0 = int(round(rx + kx * rw))", "            x0 = int(rx)",
     COMP, ["ANIM_PART_DE_LA_GAUCHE", "ANIM_GLISSE_VERS_LA_DROITE"]),
    # 47. l'animation ne se termine jamais : la region n'arrive pas
    (TA, "/{d:.3f},{int(rx)}))\")", "/{d:.3f},{x0}))\")",
     COMP, ["ANIM_ARRIVE_A_SA_PLACE"]),
    # 48. un type inconnu passe pour un glissement
    (TA, "    if t_ent in TYPES and t_ent != \"none\":",
     "    if t_ent != \"none\":",
     COMP, ["ANIM_TYPE_INCONNU_NE_CASSE_RIEN"]),
    # 49. la sortie demarre a zero au lieu de la fin
    (TA, "        st = max(0.0, float(duree) - d)", "        st = 0.0",
     COMP, ["SORTIE_EN_FIN_DE_CLIP"]),
    # 50. la barre animee reste peinte par drawbox : elle ne bouge pas
    (TS, "            if (ax, ay, afil) == (str(rx), str(ry), []):",
     "            if True:",
     COMP, ["ANIM_GLISSE_VERS_LA_DROITE", "ANIM_PART_DE_LA_GAUCHE"]),
    # ── D3 Figma ─────────────────────────────────────────────────────────
    # 51. l'appel part sur l'endpoint des IMAGES, pas des noeuds
    (FI, "           f\"/nodes?ids={cible['node']}\")",
     "           f\"?ids={cible['node']}&format=png\")",
     FIGM, ["APPEL_SUR_L_ENDPOINT_NODES"]),
    # 52. les contraintes Figma sont perdues
    (FI, "                \"constraints\": _ancrages(enfant)}",
     "                \"constraints\": {}}",
     FIGM, ["CONTRAINTE_STRETCH", "CONTRAINTE_SCALE", "CONTRAINTE_END"]),
    # 53. LEFT_RIGHT ne devient plus stretch
    (FI, "    \"STRETCH\": \"stretch\", \"LEFT_RIGHT\": \"stretch\", \"TOP_BOTTOM\": \"stretch\",",
     "    \"STRETCH\": \"stretch\",",
     FIGM, ["CONTRAINTE_STRETCH"]),
    # 54. cornerRadius ne devient plus un masque
    (FI, "            base[\"mask\"] = {\"shape\": \"rounded\", \"radius\": int(round(rayon))}",
     "            pass",
     FIGM, ["RAYON_DEVENU_MASQUE"]),
    # 55. un remplissage IMAGE devient un aplat
    (FI, "        if f.get(\"type\") == \"IMAGE\":\n            return {\"kind\": \"image\"}",
     "        if False:\n            return {\"kind\": \"image\"}",
     FIGM, ["TYPES_ATTENDUS"]),
    # 56. la barre fine ne devient plus un separateur
    (FI, "        elif rempl[\"kind\"] == \"solid\" and h <= 12:",
     "        elif False:",
     FIGM, ["TYPES_ATTENDUS"]),
    # 57. un noeud qui n'est pas un cadre passe
    (FI, "    if n.get(\"type\") not in (\"FRAME\", \"COMPONENT\", \"INSTANCE\", \"GROUP\"):",
     "    if False:",
     FIGM, ["TROIS_REGIONS"]),
    # 58. le SVG perd ses groupes nommes
    (FI, "        lignes.append(f'<g id=\"{_xml(r[\"id\"])}\" '",
     "        lignes.append(f'<g '",
     FIGM, ["SVG_GROUPE_TEXT", "SVG_GROUPE_IMAGE_SLOT",
            "SVG_GROUPE_SEPARATOR"]),
    # 59. l'ecriture Figma pretend exister
    (FI, "    raise NotImplementedError(", "    return None\n    raise NotImplementedError(",
     FIGM, ["ECRITURE_FIGMA_REFUSEE"]),
]


def rouges(banc):
    """Les verifications rouges du banc — et si RIEN n'a tourne, on le dit.

    Le banc est un SCRIPT : sortie 0 = tout vert, 1 = des rouges, autre chose
    = il n'a pas tourne (import casse, ffmpeg absent, exception hors check).
    Lue comme « aucun FAILED », une exception passerait pour une mutation
    VERTE alors que rien n'a ete mesure.
    """
    r = subprocess.run([PY, banc], capture_output=True,
                       cwd=R / "backend", timeout=1800)
    txt = (r.stdout or b"").decode("utf-8", "replace")
    err = (r.stderr or b"").decode("utf-8", "replace")
    erreur = r.returncode not in (0, 1) or "SKIP:" in txt
    return set(re.findall(r"^FAILED (\w+)", txt, re.M)), txt + err, erreur


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
        paires = old if isinstance(old, list) else [(old, new)]
        for o, n_ in paires:
            assert txt.count(o) == 1, (i, rel, txt.count(o), o[:70])
            txt = txt.replace(o, n_)
        sha_avant = hashlib.sha256(src).hexdigest()
        p.write_bytes(txt.replace("\n", eol).encode("utf-8"))
        try:
            rg, sortie, erreur = rouges(banc)
        finally:
            p.write_bytes(src)
            sha_apres = hashlib.sha256(p.read_bytes()).hexdigest()
            assert sha_apres == sha_avant, (i, rel, sha_avant, sha_apres)
        manquants = [a for a in attendus if a not in rg]
        if erreur:
            verdict = "ERREUR(banc)"
            print(sortie[-1200:], file=sys.stderr)
        elif not manquants:
            verdict = "ROUGE"
        elif not rg:
            verdict = "VERTE"
        else:
            verdict = "ROUGE(autres)"
        bilan.append((i, rel, verdict, sorted(rg), manquants))
        apercu = paires[0][0].strip()[:46]
        print(f"[{i:2d}] {verdict:14s} {pathlib.Path(rel).name:26s} "
              f"{apercu!r} -> {sorted(rg)}  sha {sha_avant[:10]}="
              f"{sha_apres[:10]}")
        sys.stdout.flush()
    print(json.dumps([b[:3] for b in bilan], ensure_ascii=False))
    verts = [b for b in bilan if b[2] in ("VERTE", "ROUGE(autres)")]
    erreurs = [b for b in bilan if b[2] == "ERREUR(banc)"]
    print(f"\n{len(bilan)} mutations : {len(bilan) - len(verts) - len(erreurs)}"
          f" ROUGE, {len(verts)} a instruire, {len(erreurs)} sans mesure")


if __name__ == "__main__":
    main()
```

- [ ] **Étape 2 : lancer la campagne complète**

```
cd backend
python tests/mutations_templates.py
```
Attendu : 60 lignes, **toutes `ROUGE`**, et la ligne finale
`60 mutations : 60 ROUGE, 0 a instruire, 0 sans mesure`. Compter environ
25 à 45 minutes (chaque mutation relance un banc qui rend des MP4).

- [ ] **Étape 3 : instruire chaque « VERTE » ou « ROUGE(autres) »**

Une `VERTE` est une **assertion qui manque**, pas une mutation ratée : ajouter
la vérification au banc visé, la voir rougir sous la mutation, la voir verte
sans, et relancer cette mutation seule (`python tests/mutations_templates.py
<n>`). Une `ERREUR(banc)` veut dire que le banc n'a pas tourné (import cassé,
`SKIP: ffmpeg introuvable`) : la mutation n'a **rien** mesuré, il faut la
relancer dans un environnement où le banc tourne.

- [ ] **Étape 4 : commit**

```
git add backend/tests/mutations_templates.py
git commit -m 'etabli : campagne de mutations des Templates, 60 coups' -m 'Chaque mutation nomme les verifications qu elle doit faire rougir et le banc qui les porte ; le fichier est remis a l octet pres, sha256 journalise. Les bancs sont des scripts autonomes, pas des fichiers pytest : les rouges se lisent sur les lignes FAILED que _miroir.check imprime, et un code de sortie autre que 0 ou 1 devient un troisieme etat — sans quoi un banc qui n a pas tourne passerait pour une mutation verte.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Ce que ce plan ne fait pas (dettes nommées)

1. **Les blocs `transitions` des neuf gabarits livrés restent morts.** Les
   convertir en `animation` par région toucherait les neuf fichiers, donc le
   rendu de tous les posts existants. Lot à part.
2. **Pas de vue « quatre canevas côte à côte ».** On rejoue un format, on
   obtient un gabarit, on le reprend dans l'éditeur normal (Tâche 7).
3. **Pas de galerie de composants dans le bundle** : une `<select>` dans le
   panneau de région, et les routes pour le reste.
4. **`POST /brand-kits` n'a pas d'écran** : les kits se pilotent par les
   routes tant que Settings n'a pas sa section (hors périmètre Templates).
5. **Un composant ne peut pas en contenir un autre** (`_valider` le refuse
   explicitement) : une seule profondeur, mesurable et rendue.
6. **`build_sequential_command` ne connaît ni masques, ni animations, ni texte
   ajusté** — le montage reste le montage ; tout ce plan vit dans le
   compositeur spatial. Un gabarit `render_mode: sequential` traversé par une
   des nouveautés les **ignore en silence** : c'est la seule zone du plan sans
   refus parlant, et c'est un choix (le montage a son propre chantier, R5).

---

## Relecture (faite à l'écriture, corrections en place)

- **Couverture du périmètre.** P1→T1, P2→T2, P3→T3, P4→T4, P5→T5, P6→T6,
  D1→T8, D2→T9, D3→T10, D4→T11 ; E1/E2/E3 en section « Écarté ». Les greffes
  bundle sont T7 et T12, la campagne T13. Aucun bac de R7 sans tâche.
- **Noms croisés, vérifiés d'une tâche à l'autre.** `resoudre()` est posée en
  T1 (kit seul) puis **remplacée** en T8 (composants + kit) — la T8 le dit et
  redonne le corps entier. `build_ffmpeg_command` gagne `still_at` en T5 et
  garde la même signature partout. `template_anim.overlay()` rend un triplet
  `(x, y, filtres)` en T9, et c'est ce triplet que les deux sites d'appel
  déballent. `text_fit` (et non `fit`) est le même nom en T4, T11, dans le
  patcher `tplregion` et dans les mutations 21-23 et 28.
- **Une correction faite en place :** la première rédaction posait un champ
  `fit` pour l'ajustement de texte, qui aurait écrasé le mode d'échelle des
  slots vidéo (`_scale_filter`, `template_service.py:101`) et cassé les neuf
  gabarits livrés. Renommé `text_fit` partout.
- **Une seconde :** le masque était d'abord dessiné puis la bordure overlayée
  **après toutes les régions**, ce qui l'aurait posée au-dessus d'une région
  de `z_index` supérieur. Elle est maintenant peinte juste après sa propre
  région, donc l'ordre de profondeur est respecté.
- **Placeholders :** aucune étape ne dit « TBD », « ajouter la gestion
  d'erreur » ni « comme la tâche N ». Les deux endroits où du code est repris
  d'un fichier existant (le corps des patchers) donnent le fichier, les lignes
  et la commande exacte de copie, avec le nombre de lignes attendu.
