# Card Forge — Game Assets « Cartes » : plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Amener Card Forge à la parité du métier (gabarits d'imprimeur MPC / TGC /
DriveThruCards, exports Tabletop Simulator et Tabletopia, dos variables, données
et localisation) puis au-delà (art du deck depuis le CSV et la bible, objets 3D du
jeu, livret / mockup / fiche produit), sans une dépendance de plus dans le Python
embarqué.

**Architecture:** Le domaine `cards/` reste ce qu'il est — dix pièces, chacune son
fichier, aucune n'important le routeur d'une voisine (règle 8), `contract.py` seule
géométrie. Les gabarits d'imprimeur n'ajoutent **aucune arithmétique** : ce sont des
couples (fond perdu, zone sûre) passés à `contract.geom()`, qui reproduit alors les
pixels publiés par MPC, TGC et DTC au pixel près (mesuré, table plus bas). Une
**onzième pièce** `edition` naît pour ce qui se livre *autour* de la carte (table
virtuelle, livret, mockup, fiche produit) ; tout le reste se pose dans les pièces
existantes, en sidecars quand le fichier canonique est déjà lourd. Le navigateur rend
et manipule, **Python écrit** — la règle du dépôt, et le verrou mécanique de
`open_card` (un bitmap hors `geom.canvas_px` est refusé) reste le garde-fou.

**Tech Stack:** Python 3.13.15 embarqué (stdlib + Pillow 12.3.0 + pypdf 6.16.2 +
python-docx 1.2.0 — mesuré, voir T1), FastAPI, JavaScript vanilla sans build
(`/cardforge/`, page autonome hors bundle), PIL pour tout le raster, pypdf pour la
structure PDF.

---

## Périmètre

**Lot 1 — parité nécessaire**, dans cet ordre :

| # | bac | ce que ça livre |
|---|---|---|
| P1 | Gabarits imprimeur | profils MPC / TGC / DTC / maison dans `contract.py`, paquet PNG recto-verso, PDF DTC, sélecteur d'écran |
| P2 | Tabletop Simulator et Tabletopia | pièce `edition`, collage 10 × 7 + objet JSON TTS, images par carte + manifeste Tabletopia |
| P3 | Dos variables + miroir | image de dos par carte (colonne CSV), mire d'alignement recto-verso imprimée |
| P4 | Données | statistiques (histogrammes), grille éditable, import Google Sheets et Notion |
| P5 | Localisation | colonnes par langue, rendu et export par langue, traduction LLM validée carte par carte |

**Lot 2 — différenciant** :

| # | bac | ce que ça livre |
|---|---|---|
| D1 | Art du deck depuis le CSV et la bible | prompt par ligne, style de série, entités de la bible, coût total avant tir, génération en lot avec lignée Bibliothèque |
| D2 | Objets 3D du jeu | jetons et pions extrudés, boîte dépliée (PDF avec plis), présentoir STL pour la Centauri |
| D3 | Autour du deck | livret de règles PDF, mockup marketing, fiche produit |

**Écarté** (une ligne chacun, section dédiée en fin de plan) : E1 scripts de génération
façon nanDECK, E2 API The Game Crafter pour envoyer le deck.

**Liens vers les autres plans du balayage — par identifiant, sans replanifier :**

- `R3 P3` (cohérence multi-références de la bible) : D1 lit la planche de référence
  d'une entité. Si `R3 P3` n'est pas encore livrée, D1 se contente de l'image de
  planche déjà écrite sur disque — il ne réimplémente pas le chaînage.
- `R7 P4` (texte adaptatif : rétrécissement, coupe, mesure PIL de la largeur avant
  rendu) : P5 en dépend pour qu'une traduction plus longue tienne dans l'emplacement.
  **P5 ne l'implémente pas** : il MESURE le débordement et le dit, et le remède vient
  de `R7 P4`.
- `R10f` (`print3d`, Établi, profils d'imprimante) : D2 écrit ses STL/3MF par
  `app.services.print3d` — `creer_export`, garde 256 mm Centauri Carbon 2. Il
  n'ajoute pas de moteur 3D.

---

## Coût de patch

**Le fait mesuré** : `/cardforge/` est une page **autonome**, servie par un mount
statique et affichée dans le hub par une `<iframe src="/cardforge/">`
(`scripts/patch_bundle_cardforge.py`, TAG `cardforge`, ancre K4, EN QUEUE de chaîne).
Le bundle ne contient que l'onglet et l'iframe.

**Conséquence, valable pour les vingt tâches de ce plan : aucune ne touche le
bundle.** Aucun `patch_bundle_*.py` n'est modifié, `scripts/repatch_all.py` n'est pas
lancé, `frontend/dist/assets/index-BEOJX8L5.js` n'est pas ouvert. Tout ce qui est
écran vit dans `frontend/cardforge/` et se recharge par un simple F5.

Le prix se déplace ailleurs, et il faut le nommer : **ajouter une pièce coûte huit
retouches CORE** (T5 les fait toutes en une fois, jamais deux fois) :

1. `backend/app/services/cards/contract.py:83` — `MODULE_IDS`
2. `backend/app/services/cards/__init__.py:74` — un `include_router` de plus
3. `frontend/cardforge/js/core.js:82` — `const MODULES`
4. `frontend/cardforge/index.html` — 1 `<link>`, 1 `<section>`, 1 `<script>`
5. `scripts/qa/lint_cardforge.py:112` — `MODULES`
6. `scripts/qa/lint_cardforge.py:100` — `Z_TABLE` (ensemble vide : la pièce ne dessine pas)
7. `scripts/qa/lint_cardforge.py:137` — `EXTRA_PY` pour les sidecars
8. un fichier de test qui porte le nom de la pièce (règle 1)

Coût par tâche, dit à chaque tâche dans une ligne **« Coût de patch »**. Résumé :

| tâche | bundle | CORE de Card Forge | patch chaîné |
|---|---|---|---|
| T1 · T2 · T3 | aucun | `contract.py` (ajout pur, aucune signature gelée touchée) | non |
| T4 | aucun | aucun (`mod-print.js` seul) | non |
| T5 | aucun | **les huit points ci-dessus, une seule fois** | non |
| T6 → T19 | aucun | aucun | non |
| T20 | aucun | aucun (banc de mutations, remet les fichiers à l'octet) | non |

---

## Références vérifiées

### Vérifiées le 03/09/2026 par la session du balayage (R10d), reprises telles quelles

- **MakePlayingCards** : poker 2,5 × 3,5 in, upload **822 × 1122 px** à 300 DPI,
  fond perdu 1/8 in (**36 px**), zone sûre **36 px de plus**
  (makeplayingcards.com, 03/09/2026).
- **The Game Crafter** : coupe à 1/8 in (**37 px**), zone sûre à 1/4 in (**75 px**),
  300 DPI ; API développeur `/api/deck` (thegamecrafter.com, 03/09/2026).
- **DriveThruCards** : fond perdu 1/8 in obligatoire, zone sûre 1/8 in dans la coupe
  (2,25 × 3,25 in), mise en page **2,75 × 3,75 in**, **PDF/X-1a:2001** polices
  incorporées, **sans traits de coupe** (drivethrucards.com, 03/09/2026).
- **Tabletop Simulator** : deck en collage **10 colonnes × 7 lignes**, objet JSON
  (`ObjectStates`, `Transform`, `Nickname`…) dans *Saved Objects*
  (kb.tabletopsimulator.com, 03/09/2026).

### Mesurées par CE plan, le 03/09/2026

**a) Le Python embarqué — commande exacte et sortie exacte.**

```powershell
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" -c "import importlib.util as u; [print(m, 'OK' if u.find_spec(m) else 'ABSENT') for m in ['PIL','pypdf','reportlab','fpdf','docx','numpy','fitz','pikepdf','openpyxl','requests','zipfile','sqlite3']]"
```

```
PIL OK
pypdf OK
reportlab ABSENT
fpdf ABSENT
docx OK
numpy ABSENT
fitz ABSENT
pikepdf ABSENT
openpyxl ABSENT
requests OK
zipfile OK
sqlite3 OK
```

Versions : Python **3.13.15**, PIL **12.3.0**, pypdf **6.16.2**, python-docx **1.2.0**.
Le relevé d'un autre plan du balayage (« `docx` et `pypdf` PRÉSENTS, `reportlab` et
`fpdf` absents ») est **confirmé**. `numpy` reste absent : aucun tableau numérique
vectorisé dans ce plan.

**b) La géométrie des trois imprimeurs sort de la règle qui existe déjà.**
Mesuré en appelant `contract.geom()` du dépôt, sans une ligne nouvelle :

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" -c "import sys; sys.path.insert(0,'.'); from app.services.cards import contract as CT; [print(l, CT.geom('poker_us',300,b,s).canvas_px, CT.geom('poker_us',300,b,s).bleed_off_px, CT.geom('poker_us',300,b,s).safe_off_px) for l,b,s in [('MPC',3.048,3.048),('TGC',3.175,3.175),('DTC',3.175,3.175)]]"
```

```
MPC (822, 1122) (36.0, 36.0) (72.0, 72.0)
TGC (825, 1125) (37.5, 37.5) (75.0, 75.0)
DTC (825, 1125) (37.5, 37.5) (75.0, 75.0)
```

| gabarit | fond perdu mm | zone sûre mm | toile px | fond perdu px | retrait zone sûre px |
|---|---|---|---|---|---|
| MPC | **3,048** | 3,048 | **822 × 1122** | **36,0** | 72,0 |
| TGC | 3,175 (1/8 in) | 3,175 | **825 × 1125** | **37,5** | **75,0** |
| DTC | 3,175 | 3,175 | **825 × 1125** = 2,75 × 3,75 in | 37,5 | 75,0 |

**Le piège, nommé** : MPC publie « fond perdu 1/8 in » ET « 822 × 1122 px ». Les deux
ne sont pas d'accord — 1/8 in à 300 DPI vaut 37,5 px, ce qui donnerait 825 × 1125.
**Le portail contrôle les pixels** : c'est **36 px = 3,048 mm** qu'il faut écrire, et
c'est ce chiffre-là, pas la phrase, qui entre dans le profil.

**c) Ce que le dépôt fait déjà, et que R10d classe à tort dans les « absents ».**

- **Le miroir recto-verso est livré, et mesuré.** `print.py:1206 origin_for()`
  retourne l'origine du verso, `print.py:1258 mirror_px()` / `1284 mirror_um()`
  mesurent l'écart au miroir parfait **case par case sur la géométrie qui sera
  écrite**, `print.py:2971 mirror_um_bytes()` le relit **dans les octets du PDF**, et
  l'en-tête `X-CF-Mirror-Um` le publie. Le commentaire d'`origin_for` cite les
  mesures du défaut corrigé (708,54 px = 59,99 mm hors centrage). **P3 n'a donc pas
  de miroir à écrire** — il lui reste la mire imprimée et le dos par carte en image.
- **`card.back` existe déjà** : `data.py:109 RESERVED = {"art","back","id"}` réserve
  la colonne « dos » du CSV, `mod-frame.js:3190` la lit comme **motif de dos du
  catalogue** (quand « dos commun » est décoché), `mod-face.js:2063` la lit comme
  **illustration du verso**. Les deux pièces lisent le même champ dans deux espaces
  de noms différents : c'est un partage non dit, et T8 le nomme.
- **Le PDF est déjà de qualité prépresse.** `print.py` écrit `/TrimBox` + `/BleedBox`
  par page, traits de coupe **vectoriels**, encre `/Separation /All /DeviceCMYK`,
  intentions de sortie (`_output_intents`, ligne 2414), XMP à la main
  (`xmp_packet`, 2456), `/Trapped`, calques optionnels, revendication **PDF/X-3:2003**
  gardée par `_pdfx_ok` (587). Il relit ensuite ses propres octets (`pdf_audit`, 3069).

**d) Tabletopia — relu le 03/09/2026 sur la documentation officielle.**

- `help.tabletopia.com/knowledge-base/how-to-prepare-graphics/` : formats **JPEG et
  PNG** ; « Try not to exceed the image size of **2000 × 2000 pixels** for each
  object » ; « Maximum objects size are **3-10 MB** », visé **1–2 MB** ; recto et
  verso dans des **fichiers séparés**, « must have front and back images of the same
  size » ; JPEG n'a pas d'alpha, donc pas de coins arrondis.
- `help.tabletopia.com/knowledge-base/card/` : « Size: **up to 1600 × 1600 mm** »,
  « Thickness: **0.2 mm** ».
- **La grille de collage n'est pas publiée par la base de connaissances de
  Tabletopia.** Ce qui est publié, c'est le contraire : **un fichier par face**.
  Le mot « collage 10 × 7 » de R10d appartient à Tabletop Simulator, pas à
  Tabletopia. T5 le confirme par un WebFetch daté avant d'écrire une ligne, et T7
  livre en conséquence **une image par face** + un manifeste, pas un collage.

**e) Tabletop Simulator — relu le 03/09/2026.**

- `kb.tabletopsimulator.com/custom-content/asset-creation/` : « Custom Deck (Square)
  **4096 × 4096** », « Custom Deck (Rectangle) **4096 × (whatever height fits)** ».
- `kb.tabletopsimulator.com/custom-content/custom-deck/` : « Select **how many cards
  the sheet will feature horizontally and vertically** » — le champ existe, **aucun
  maximum n'y est publié**.
- **Donc** : 10 × 7 est une convention de gabarit, pas un chiffre publié. Le plan la
  garde comme **défaut** (`NumWidth: 10`, `NumHeight: 7`, 70 cartes par planche) et
  **dérive** la taille par carte du plafond mesuré : 4096 / 10 = 409 px de large ;
  pour un `poker_us` (toile 825 × 1125), 409 × 558 par carte, planche 4090 × 3906 —
  sous 4096 sur les deux axes. C'est ce chiffre-là que le banc mesure.

**f) De mémoire, non vérifié, donc jamais un argument** : nanDECK (la parité au pixel
du dépôt reste, elle, mesurée par `test_cards_print.py`), Component Studio, Dextrous,
Squib, la convention TTS `CardID = 100 × id_de_deck + index` (lue dans des objets
sauvegardés, absente de la base de connaissances — T6 l'écrit **et le dit**).

---

## Décision : écrire un PDF sans une dépendance de plus

Le brief demandait une table de décision au cas où aucune bibliothèque d'écriture ne
serait disponible. **La mesure la rend courte.**

| option | disponible ? | verdict |
|---|---|---|
| `reportlab` | **ABSENT** du runtime embarqué (mesuré) | écarté — l'ajouter au build pour du raster paginé serait payer une dépendance pour un service déjà rendu |
| `fpdf` / `fpdf2` | **ABSENT** (mesuré) | écarté, même raison |
| PDF minimal écrit à la main (objets, xref, images `DCTDecode`) | possible | **écarté** : le dépôt en a déjà un meilleur |
| **PIL (`Image.save(..., "PDF")`) + pypdf (boîtes, intentions, XMP, contenu vectoriel)** | **PRÉSENTS** (PIL 12.3.0, pypdf 6.16.2) et **déjà utilisés par `print.py:2510 build_pdf`** | **retenu, pour DTC comme pour le livret de D3** |

**Aucune dépendance n'est ajoutée au build. Aucun écrivain PDF n'est écrit à la main.**

**PDF/X-1a:2001, ce qui est à portée et ce qui ne l'est pas.** `print.py` revendique
déjà PDF/X-3:2003 sous une garde mécanique (`_pdfx_ok`, 587 : la revendication n'est
écrite que si l'intention décrit une **presse**, profil de classe `prtr` et espace
CMJN). PDF/X-1a est le **même appareil, un cran plus strict** :

| exigence X-1a | état | ce que T3 fait |
|---|---|---|
| `GTS_PDFXVersion = PDF/X-1a:2001` + XMP `pdfxid` | l'appareil existe (2431, 2468), la version est en dur | la version devient un paramètre |
| en-tête ≤ PDF 1.4 | déjà géré (2530), 1.5 seulement si calques | X-1a **refuse** les calques : `layers` forcé à faux |
| `/Trapped` présent | déjà écrit (2813) | rien |
| intention de sortie CMJN de presse | déjà gardé (`_pdfx_ok`) | rien |
| **aucun espace `/ICCBased` dans le contenu** | `_image_xobject` (2163) étiquette `/ICCBased` en `rgb` et `cmyk_icc` | X-1a n'est revendicable **que** si `color == "cmyk_device"` (images `/DeviceCMYK` nues) |
| aucune transparence | `_flatten` (1836) aplatit déjà tout | rien |
| polices incorporées | **zéro police dans le fichier** : le cartouche est tracé en chemins vectoriels (`glyph`, 440 ; `text_paths`, 469) | rien — « aucune police » satisfait « toutes les polices incorporées » |

**L'écart qui reste, dit en toutes lettres dans l'écran et dans le manifeste** :
`cmyk_device` est la conversion d'appareil de Pillow — **ni retrait des sous-couleurs,
ni noir squelette** (`to_output_space`, 2142, le dit déjà). Une conformité PDF/X-1a
*complète et certifiée* suppose une séparation colorimétrique que le runtime embarqué
ne sait pas faire sans profil de l'imprimeur. Donc :

- avec un `.icc` de presse chargé (`POST /print/icc` existe déjà) → séparation
  littleCMS, revendication X-1a écrite **et relue dans les octets** ;
- sans profil → le PDF est livré **aux dimensions DTC exactes** (2,75 × 3,75 in,
  198 × 270 pt, sans traits de coupe) mais **sans revendication PDF/X** ; l'écran
  écrit la phrase « dimensions DTC tenues, conformité PDF/X-1a non revendiquée :
  chargez le profil ICC de l'imprimeur ». **L'écart est marqué, pas caché.**

---

## Structure des fichiers

```
backend/app/services/cards/
  contract.py            MODIF  + PRINTER_PROFILES, profile_geom, profile_table, MODULE_IDS
  __init__.py            MODIF  + include_router(edition)
  print.py               MODIF  + /pack, /mire, PDF/X-1a paramétré
  print_gabarits.py      NEUF   sidecar de `print` : noms de fichiers, ZIP, manifeste
  data.py                MODIF  + /stats, /sheets-import, /notion-import, /traduire, colonne dos-image
  data_stats.py          NEUF   sidecar de `data` : histogrammes, résumés de colonne
  face.py                MODIF  + /lot (coût, génération en lot)
  face_lot.py            NEUF   sidecar de `face` : prompt par ligne, bible, devis
  forge3d.py             MODIF  + kinds jeton / boite / presentoir
  forge3d_jeu.py         NEUF   sidecar de `forge3d` : géométrie des objets du jeu
  edition.py             NEUF   PIÈCE 11 : router de la pièce
  edition_vtt.py         NEUF   sidecar : collage TTS, objet JSON, paquet Tabletopia
  edition_livret.py      NEUF   sidecar : livret PDF, mockup, fiche produit

frontend/cardforge/
  index.html             MODIF  1 link + 1 section + 1 script (pièce 11)
  js/core.js             MODIF  MODULES + "edition"
  js/mod-print.js        MODIF  sélecteur de gabarit, bouton paquet, bouton mire
  js/mod-data.js         MODIF  grille éditable, histogrammes, imports, langues
  js/mod-face.js         MODIF  panneau « art du deck »
  js/mod-forge3d.js      MODIF  nœuds jeton / boîte / présentoir
  js/mod-edition.js      NEUF   PIÈCE 11
  css/mod-edition.css    NEUF   PIÈCE 11

scripts/qa/lint_cardforge.py  MODIF  MODULES, Z_TABLE, EXTRA_PY

backend/tests/
  test_cards_gabarits.py NEUF   P1 (T1–T4)
  test_cards_edition.py  NEUF   pièce 11 (T5–T7, T18–T19)
  test_cards_dos.py      NEUF   P3 (T8)
  test_cards_donnees.py  NEUF   P4 (T9–T11)
  test_cards_langues.py  NEUF   P5 (T12–T13)
  test_cards_lot_art.py  NEUF   D1 (T14–T15)
  test_cards_jeu3d.py    NEUF   D2 (T16–T17)
  mutations_cartes.py    NEUF   T20
```

**Comment on lance un banc — la seule forme admise dans ce plan :**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_gabarits.py
```

Un processus par fichier. **Jamais `pytest tests`** (la suite complète partage un
`settings` figé au premier import et des fixtures d'écriture disque : deux bancs dans
le même processus se volent leur dossier `outputs`). Chaque banc neuf finit par
`if __name__ == "__main__": raise SystemExit(pytest.main([__file__, "-q"]))`, comme
`test_cards_print.py:3222`, et force UTF-8 dans son `__main__`.

**Les bancs sont des MIROIRS** : ils relisent le PNG, le PDF, le ZIP, le JSON ou le
STL **écrits**, jamais le code qui prétend les produire. Un `assert` sur le nom d'une
fonction ne compte pas.

---

# Lot 1 — parité

## Task 1 : Les gabarits d'imprimeur entrent dans `contract.py`

**Files:**
- Modify: `backend/app/services/cards/contract.py:145-152` (juste après `SHEETS`)
- Create: `backend/tests/test_cards_gabarits.py`

**Coût de patch** : aucun. `contract.py` gagne un dictionnaire et deux fonctions ;
aucune signature gelée (`geom`, `deck_dir`, `card_mesh`) n'est touchée.

- [ ] **Step 1 : mesurer le runtime embarqué et coller la sortie dans le journal**

```powershell
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" -c "import importlib.util as u; [print(m, 'OK' if u.find_spec(m) else 'ABSENT') for m in ['PIL','pypdf','reportlab','fpdf','docx','numpy']]"
```

Attendu, mot pour mot :

```
PIL OK
pypdf OK
reportlab ABSENT
fpdf ABSENT
docx OK
numpy ABSENT
```

Si une ligne diverge, **arrêter le plan** et le dire : la table de décision PDF
repose sur cette sortie.

- [ ] **Step 2 : écrire le banc qui échoue**

Créer `backend/tests/test_cards_gabarits.py` :

```python
# -*- coding: utf-8 -*-
"""Card Forge — P1 « Gabarits imprimeur ». Les pixels, pas les phrases.

Chaque nombre attendu est ÉCRIT EN DUR, relevé le 03/09/2026 sur les portails
(MPC 822x1122 et 36 px ; TGC 37/75 px ; DTC 2,75 x 3,75 in) et JAMAIS recalculé
par la formule qu'il vérifie.

LE PIÈGE, NOMMÉ : MPC publie « fond perdu 1/8 in » ET « 822 x 1122 px ». Les deux
ne sont pas d'accord — 1/8 in vaut 37,5 px à 300 DPI, soit 825 x 1125. C'est le
PIXEL que le portail contrôle : le profil écrit 3,048 mm, pas 3,175.

Run : cd backend ; python tests/test_cards_gabarits.py
"""
import io
import os
import pathlib
import sys
import zipfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = os.environ.setdefault("CF_GABARITS_TMP", "")
import tempfile                                                  # noqa: E402
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest                                                    # noqa: E402
from app.services.cards import contract as CT                    # noqa: E402

# ── les seuils, relevés le 03/09/2026, écrits en dur ────────────────────────
GABARITS = {
    ("mpc", "poker_us"): {"canvas": [822, 1122], "bleed": [36.0, 36.0],
                          "safe_off": [72.0, 72.0]},
    ("tgc", "poker_us"): {"canvas": [825, 1125], "bleed": [37.5, 37.5],
                          "safe_off": [75.0, 75.0]},
    ("dtc", "poker_us"): {"canvas": [825, 1125], "bleed": [37.5, 37.5],
                          "safe_off": [75.0, 75.0]},
}
DTC_PAGE_PT = (198.0, 270.0)          # 2,75 x 3,75 in, en points PostScript


def test_les_trois_gabarits_sortent_les_pixels_publies():
    for (pid, fmt), att in GABARITS.items():
        g = CT.profile_geom(pid, fmt)
        assert list(g.canvas_px) == att["canvas"], (pid, g.canvas_px)
        assert list(g.bleed_off_px) == att["bleed"], (pid, g.bleed_off_px)
        assert list(g.safe_off_px) == att["safe_off"], (pid, g.safe_off_px)


def test_mpc_ecrit_36_px_et_non_un_huitieme_de_pouce():
    """La phrase du portail dit 1/8 in ; ses pixels disent 36. Le profil suit
    les PIXELS — 3,175 mm sortirait 825 x 1125 et serait refusé à l'upload."""
    pr = CT.PRINTER_PROFILES["mpc"]
    assert pr["bleed_mm"] == 3.048, pr["bleed_mm"]
    assert CT.geom("poker_us", 300, 3.175, 3.175).canvas_px == (825, 1125)
    assert CT.profile_geom("mpc", "poker_us").canvas_px == (822, 1122)


def test_dtc_fait_exactement_deux_pouces_trois_quarts_par_trois_pouces_trois_quarts():
    g = CT.profile_geom("dtc", "poker_us")
    pt = (g.canvas_px[0] * 72.0 / g.dpi, g.canvas_px[1] * 72.0 / g.dpi)
    assert pt == DTC_PAGE_PT, pt


def test_un_gabarit_refuse_un_format_qu_il_ne_sert_pas():
    with pytest.raises(ValueError) as e:
        CT.profile_geom("dtc", "square_eu")
    assert "n'accepte pas" in str(e.value)
    assert "square_eu" in str(e.value)


def test_le_catalogue_dit_la_livraison_et_la_revendication():
    tbl = {r["id"]: r for r in CT.profile_table("poker_us")}
    assert set(tbl) == {"maison", "mpc", "tgc", "dtc"}
    assert tbl["mpc"]["delivery"] == "png_zip"
    assert tbl["tgc"]["delivery"] == "png_zip"
    assert tbl["dtc"]["delivery"] == "pdf"
    assert tbl["dtc"]["pdfx"] == "PDF/X-1a:2001"
    assert tbl["dtc"]["marks"] == "none"
    assert tbl["mpc"]["geom"]["canvas_px"] == [822, 1122]
    # un gabarit qui ne sert pas le format demandé le dit par un None, pas par
    # une géométrie inventée
    carre = {r["id"]: r for r in CT.profile_table("square_eu")}
    assert carre["dtc"]["geom"] is None


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
```

- [ ] **Step 3 : lancer le banc et vérifier qu'il échoue**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_gabarits.py
```

Attendu : 5 échecs, tous avec `AttributeError: module 'app.services.cards.contract'
has no attribute 'profile_geom'` ou `... 'PRINTER_PROFILES'`.

- [ ] **Step 4 : écrire les profils dans `contract.py`**

Insérer **après** le bloc `SHEETS` (`contract.py:145-151`), avant le commentaire
`# ── la règle ──` :

```python
# ── gabarits d'imprimeur (P1) ───────────────────────────────────────────────
# UN GABARIT N'AJOUTE AUCUNE ARITHMÉTIQUE. Il choisit un fond perdu et une zone
# sûre, et la règle qui existe déjà rend les pixels que l'imprimeur publie —
# mesuré le 03/09/2026 :
#   mpc  bleed 3.048 safe 3.048 -> toile 822 x 1122, fond perdu 36,0 px
#   tgc  bleed 3.175 safe 3.175 -> toile 825 x 1125, fond perdu 37,5 px
#   dtc  bleed 3.175 safe 3.175 -> toile 825 x 1125 = 2,75 x 3,75 in
#
# LE DÉSACCORD DE MPC, ÉCRIT ICI POUR QU'IL NE SE REPERDE PAS : le portail dit
# « fond perdu 1/8 in » ET « 822 x 1122 px ». 1/8 in vaut 37,5 px à 300 DPI,
# donc 825 x 1125 — que l'upload REFUSE. C'est le pixel qui fait foi : 36 px,
# soit 3,048 mm. Une lecture littérale de la phrase casse l'envoi.
PROFILE_DELIVERY = ("png_zip", "pdf")

PRINTER_PROFILES: dict[str, dict] = {
    "maison": {
        "label": "Imposition maison — planches A4 / Letter / A3",
        "url": "",
        "delivery": "pdf",
        "bleed_mm": None,          # None -> fond perdu natif du format
        "safe_mm": None,           # None -> zone sûre = fond perdu
        "dpi": 300,
        "marks": "crop",
        "pdfx": "PDF/X-3:2003",
        "color": "rgb",
        "sheet": "a4",
        "fmts": tuple(FORMATS),
        "note": "Le comportement historique : aucune contrainte de tiers, "
                "traits de coupe, cartouche, planches imposées.",
    },
    "mpc": {
        "label": "MakePlayingCards — 822 x 1122 px, fond perdu 36 px",
        "url": "https://www.makeplayingcards.com/",
        "delivery": "png_zip",
        "bleed_mm": 3.048,
        "safe_mm": 3.048,
        "dpi": 300,
        "marks": "none",
        "pdfx": None,
        "color": "rgb",
        "sheet": "card",
        "fmts": ("poker_us", "poker_eu", "bridge_us", "tarot_us", "square_eu",
                 "mini", "domino", "business", "jumbo", "micro"),
        "note": "Un fichier par face, appariés PAR LE NOM. Le portail contrôle "
                "les PIXELS : 822 x 1122 pour un poker US. Le « 1/8 in » "
                "publié vaudrait 37,5 px et serait refusé.",
    },
    "tgc": {
        "label": "The Game Crafter — coupe 37 px, zone sûre 75 px",
        "url": "https://www.thegamecrafter.com/",
        "delivery": "png_zip",
        "bleed_mm": 3.175,
        "safe_mm": 3.175,
        "dpi": 300,
        "marks": "none",
        "pdfx": None,
        "color": "rgb",
        "sheet": "card",
        "fmts": ("poker_us", "bridge_us", "tarot_us", "square_eu", "mini",
                 "domino", "business", "jumbo", "micro"),
        "note": "La toile 825 x 1125 du dépôt EST le gabarit TGC : coupe à "
                "37,5 px du bord, zone sûre à 75 px. Un fichier par face.",
    },
    "dtc": {
        "label": "DriveThruCards — PDF 2,75 x 3,75 in, sans traits de coupe",
        "url": "https://www.drivethrucards.com/",
        "delivery": "pdf",
        "bleed_mm": 3.175,
        "safe_mm": 3.175,
        "dpi": 300,
        "marks": "none",
        "pdfx": "PDF/X-1a:2001",
        "color": "cmyk_device",
        "sheet": "card",
        "fmts": ("poker_us",),
        "note": "Une page par face, AUCUN trait de coupe (ils tomberaient dans "
                "la mise en page). PDF/X-1a n'est revendiqué qu'en CMJN sans "
                "calques ; sans profil ICC de presse, les dimensions sont "
                "tenues et la conformité N'EST PAS revendiquée.",
    },
}


def printer_profile(profile: str) -> dict:
    """Un gabarit, ou `ValueError` en énumérant la liste blanche."""
    key = str(profile or "").strip().lower()
    if key not in PRINTER_PROFILES:
        raise ValueError("Gabarit d'imprimeur inconnu: %r. Gabarits admis: %s"
                         % (profile, ", ".join(PRINTER_PROFILES)))
    return PRINTER_PROFILES[key]


def profile_geom(profile: str, fmt: str, dpi: int | None = None) -> CardGeom:
    """La géométrie d'un format SOUS un gabarit. Zéro arithmétique nouvelle :
    le gabarit ne fait que choisir les deux longueurs passées à `geom()`."""
    pr = printer_profile(profile)
    f = str(fmt or "").strip().lower()
    if f not in FORMATS:
        raise ValueError("Format de carte inconnu: %r. Formats admis: %s"
                         % (fmt, ", ".join(FORMATS)))
    if f not in pr["fmts"]:
        raise ValueError(
            "Le gabarit %s n'accepte pas le format %s. Formats acceptés: %s"
            % (pr["label"], f, ", ".join(pr["fmts"])))
    return geom(f, int(dpi or pr["dpi"]), pr["bleed_mm"], pr["safe_mm"])


def profile_table(fmt: str = DEFAULT_FMT) -> list[dict]:
    """Le catalogue des gabarits, chacun avec la géométrie qu'il impose au
    format demandé — `geom: None` s'il ne le sert pas. On ne devine jamais une
    géométrie pour un couple refusé : l'écran doit pouvoir griser la ligne."""
    out = []
    for pid, pr in PRINTER_PROFILES.items():
        row = {"id": pid, "label": pr["label"], "url": pr["url"],
               "delivery": pr["delivery"], "dpi": pr["dpi"],
               "marks": pr["marks"], "pdfx": pr["pdfx"], "color": pr["color"],
               "sheet": pr["sheet"], "note": pr["note"],
               "fmts": list(pr["fmts"]), "geom": None}
        try:
            row["geom"] = profile_geom(pid, fmt).to_dict()
        except ValueError:
            row["geom"] = None
        out.append(row)
    return out
```

- [ ] **Step 5 : relancer le banc**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_gabarits.py
```

Attendu : `5 passed`.

- [ ] **Step 6 : vérifier que rien d'ancien n'a bougé**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_core.py
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_print.py
```

Attendu : les deux passent, comme avant la tâche (aucune formule n'a changé).

- [ ] **Step 7 : commit proposé**

```bash
git add backend/app/services/cards/contract.py backend/tests/test_cards_gabarits.py
git commit -m 'cartes : les gabarits imprimeur entrent dans le contrat' -m 'MPC, The Game Crafter et DriveThruCards ne demandent aucune géométrie nouvelle : ce sont deux longueurs — fond perdu et zone sûre — passées à la règle qui existe. Mesuré le 03/09 : 3,048 mm rend 822 x 1122 avec 36 px de fond perdu, exactement ce que MPC contrôle à l  upload ; 3,175 mm rend 825 x 1125, la toile du dépôt, qui EST le gabarit TGC et la page DTC de 2,75 x 3,75 in. Le désaccord de MPC (1/8 in publié, 36 px imposés) est écrit dans le fichier pour ne pas se reperdre.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Task 2 : Le paquet imprimeur — un ZIP de PNG nommés recto / verso (MPC, TGC)

**Files:**
- Create: `backend/app/services/cards/print_gabarits.py`
- Modify: `backend/app/services/cards/print.py:3841-3878` (helper de spec) et
  `backend/app/services/cards/print.py:4326` (nouvelle route juste avant `/sheet`)
- Modify: `scripts/qa/lint_cardforge.py:137` (`EXTRA_PY`)
- Modify: `backend/tests/test_cards_gabarits.py`

**Coût de patch** : aucun côté bundle. Un sidecar de plus dans `EXTRA_PY` — le
patron sanctionné du dépôt (`forge3d_scene.py`, `forge3d_apercu.py`,
`style_walkuski.py`). Le sidecar n'a **pas** de `router` : la route reste dans
`print.py`, comme l'exige la règle 8.

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_cards_gabarits.py`, avant le `if __name__` :

```python
# ─────────────────────── T2 : le paquet imprimeur ───────────────────────────
import asyncio                                                   # noqa: E402
import struct                                                    # noqa: E402
from httpx import ASGITransport, AsyncClient                     # noqa: E402
from PIL import Image                                            # noqa: E402


def _png(w, h):
    im = Image.new("RGB", (w, h), (18, 24, 32))
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


def _ihdr(data):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


def _phys(data):
    i, out = 8, None
    while i < len(data):
        ln = struct.unpack(">I", data[i:i + 4])[0]
        tag = data[i + 4:i + 8]
        if tag == b"pHYs":
            out = struct.unpack(">II", data[i + 8:i + 16])[0]
        i += 12 + ln
    return out


async def _deck_et_paquet(profil, n=3, fmt="poker_us"):
    from app.main import app
    tr = ASGITransport(app=app)
    async with AsyncClient(transport=tr, base_url="http://t") as c:
        r = await c.post("/api/cards/decks", json={"name": "Banc gabarit"})
        did = r.json()["deck"]["id"]
        await c.patch(f"/api/cards/{did}",
                      json={"format": {"fmt": fmt, "dpi": 300}})
        g = CT.profile_geom(profil, fmt)
        w, h = g.canvas_px
        files = ([("fronts", (f"f{i}.png", _png(w, h), "image/png"))
                  for i in range(n)]
                 + [("backs", (f"b{i}.png", _png(w, h), "image/png"))
                    for i in range(n)])
        r = await c.post(f"/api/cards/{did}/print/pack",
                         data={"spec": f'{{"profile":"{profil}"}}'},
                         files=files, timeout=120.0)
        return r


def test_le_paquet_mpc_nomme_recto_verso_et_fait_822x1122():
    r = asyncio.run(_deck_et_paquet("mpc", 3))
    assert r.status_code == 200, r.text
    z = zipfile.ZipFile(io.BytesIO(r.content))
    noms = sorted(z.namelist())
    assert "mpc/manifeste.json" in noms, noms
    cartes = [n for n in noms if n.endswith(".png")]
    assert len(cartes) == 6, cartes
    assert cartes[0] == "mpc/banc-gabarit_01_recto.png", cartes[0]
    assert "mpc/banc-gabarit_01_verso.png" in cartes, cartes
    # LE PIXEL, RELU DANS LE FICHIER ÉCRIT — pas dans le plan qui l'a demandé
    for n in cartes:
        assert _ihdr(z.read(n)) == (822, 1122), (n, _ihdr(z.read(n)))
        assert _phys(z.read(n)) == 11811, n


def test_le_paquet_tgc_fait_825x1125():
    r = asyncio.run(_deck_et_paquet("tgc", 2))
    assert r.status_code == 200, r.text
    z = zipfile.ZipFile(io.BytesIO(r.content))
    for n in [x for x in z.namelist() if x.endswith(".png")]:
        assert _ihdr(z.read(n)) == (825, 1125), n


def test_le_manifeste_dit_le_gabarit_la_toile_et_le_condensat():
    import json
    r = asyncio.run(_deck_et_paquet("mpc", 2))
    z = zipfile.ZipFile(io.BytesIO(r.content))
    man = json.loads(z.read("mpc/manifeste.json").decode("utf-8"))
    assert man["profil"] == "mpc"
    assert man["canvas_px"] == [822, 1122]
    assert man["bleed_off_px"] == [36.0, 36.0]
    assert man["dpi"] == 300
    assert len(man["fichiers"]) == 4
    for f in man["fichiers"]:
        assert len(f["sha256"]) == 64
        assert f["side"] in ("recto", "verso")
        assert f["px"] == [822, 1122]


def test_un_bitmap_a_la_mauvaise_taille_est_refuse_en_le_disant():
    """Le verrou de « un seul moteur de rendu » vaut AUSSI sous gabarit : une
    carte rendue à 825 x 1125 n'entre pas dans un paquet MPC."""
    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Mauvais"})
            did = r.json()["deck"]["id"]
            return await c.post(
                f"/api/cards/{did}/print/pack",
                data={"spec": '{"profile":"mpc"}'},
                files=[("fronts", ("f.png", _png(825, 1125), "image/png"))],
                timeout=60.0)
    r = asyncio.run(go())
    assert r.status_code == 400, r.status_code
    assert "822" in r.text and "825" in r.text, r.text
```

- [ ] **Step 2 : lancer, vérifier l'échec**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_gabarits.py
```

Attendu : 4 échecs, `404` sur `/print/pack` (le filet de `cards/__init__.py`
répond « Route inconnue dans le domaine /api/cards »).

- [ ] **Step 3 : écrire le sidecar `print_gabarits.py`**

```python
# -*- coding: utf-8 -*-
"""Card Forge — P7, sidecar « gabarits » : le PAQUET qu'on envoie à l'imprimeur.

SIDECAR, pas une pièce : aucun `router` ici (règle 8 — la route vit dans
print.py, qui seul déclare `router = APIRouter()` pour le sous-préfixe
/api/cards/{did}/print). Ce fichier ne fait que des octets.

MPC et The Game Crafter apparient recto et verso PAR LE NOM DE FICHIER. Le nom
est donc un livrable, pas un détail : numéro zéro-comblé sur la largeur du deck,
côté en DERNIER segment, un seul séparateur.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile

from .contract import CardGeom, printer_profile

__all__ = ["pack_name", "deck_slug", "build_pack", "SIDE_WORDS"]

SIDE_WORDS = {"front": "recto", "back": "verso"}

# Un nom de fichier qui survit à Windows, à un ZIP et à un portail web : ASCII,
# tiret comme unique séparateur, jamais deux de suite.
_SLUG_BAD = re.compile(r"[^A-Za-z0-9]+")
_ACCENTS = str.maketrans(
    "àâäáãåçéèêëíìîïñóòôöõúùûüýÿÀÂÄÁÃÅÇÉÈÊËÍÌÎÏÑÓÒÔÖÕÚÙÛÜÝ",
    "aaaaaaceeeeiiiinooooouuuuyyAAAAAACEEEEIIIINOOOOOUUUUY")


def deck_slug(name: str) -> str:
    """Le nom du jeu, réduit à ce qu'un portail accepte. Jamais vide."""
    s = str(name or "").translate(_ACCENTS)
    s = _SLUG_BAD.sub("-", s).strip("-").lower()
    return s[:48] or "jeu"


def pack_name(profile: str, slug: str, i: int, side: str, n: int,
              ext: str) -> str:
    """`<profil>/<jeu>_<NN>_<recto|verso>.<ext>`.

    LE ZÉRO-COMBLEMENT SUIT LA TAILLE DU DECK, pas un 2 en dur : un jeu de 120
    cartes trié par nom mettrait « 100 » avant « 2 » et l'imprimeur imprimerait
    la mauvaise carte. Largeur minimale 2, pour que 9 cartes donnent 01..09.
    """
    largeur = max(2, len(str(max(1, int(n)))))
    mot = SIDE_WORDS.get(side, side)
    return "%s/%s_%0*d_%s.%s" % (profile, slug, largeur, i + 1, mot, ext)


def build_pack(profile: str, slug: str, g: CardGeom,
               faces: dict[str, dict[int, bytes]], ext: str) -> bytes:
    """Le ZIP. `faces` = {"front": {i: octets}, "back": {i: octets}} — les
    octets sont DÉJÀ encodés par `print.encode_image` : ce fichier ne réencode
    rien, il nomme, condense et archive.

    Le manifeste dit ce que le paquet CONTIENT (toile, fond perdu, condensat
    par fichier), pas ce qu'on a demandé : c'est lui qu'on relit au banc.
    """
    pr = printer_profile(profile)
    n = max([len(v) for v in faces.values()] + [1])
    entrees, index = [], []
    for side in ("front", "back"):
        for i in sorted(faces.get(side) or {}):
            data = faces[side][i]
            nom = pack_name(profile, slug, i, side, n, ext)
            entrees.append((nom, data))
            index.append({
                "nom": nom.split("/", 1)[1], "carte": i + 1,
                "side": SIDE_WORDS[side], "octets": len(data),
                "px": list(g.canvas_px),
                "sha256": hashlib.sha256(data).hexdigest(),
            })
    manifeste = {
        "profil": profile, "label": pr["label"], "url": pr["url"],
        "livraison": pr["delivery"], "note": pr["note"],
        "jeu": slug, "fmt": g.fmt, "dpi": g.dpi,
        "canvas_px": list(g.canvas_px), "trim_px": list(g.trim_px),
        "bleed_off_px": list(g.bleed_off_px),
        "safe_px": list(g.safe_px), "safe_off_px": list(g.safe_off_px),
        "bleed_mm": g.bleed_mm, "safe_mm": g.safe_mm,
        "cartes": n, "fichiers": index,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        # Le manifeste EN PREMIER : un humain qui ouvre l'archive le voit.
        z.writestr(f"{profile}/manifeste.json",
                   json.dumps(manifeste, ensure_ascii=False, indent=1))
        for nom, data in entrees:
            # STORED : un PNG est déjà compressé, le redéflater coûte du temps
            # et ne gagne rien (mesure du dépôt sur material_store).
            z.writestr(zipfile.ZipInfo(nom), data,
                       compress_type=zipfile.ZIP_STORED)
    return buf.getvalue()
```

- [ ] **Step 4 : brancher la route dans `print.py`**

Ajouter l'import en tête de `print.py` (auprès des autres imports du domaine) :

```python
from . import print_gabarits as PG
```

Ajouter le helper de spec, juste après `_spec_of` (`print.py:3841-3878`) :

```python
def _profile_spec(doc: dict, body: dict) -> tuple[str, dict]:
    """La spec d'impression SOUS un gabarit. Le gabarit gagne sur le document :
    on n'envoie pas à MPC un fichier réglé pour la maison. Les réglages qu'il
    ne touche pas (qualité, sans perte) restent ceux de l'utilisateur."""
    pid = str((body or {}).get("profile") or "maison").strip().lower()
    try:
        pr = contract.printer_profile(pid)
    except ValueError as e:
        raise HTTPException(400, str(e))
    spec = _spec_of(doc, body or {})
    if pid != "maison":
        spec = dict(spec)
        spec["bleed_mm"] = pr["bleed_mm"]
        spec["safe_mm"] = pr["safe_mm"]
        spec["dpi"] = pr["dpi"]
        spec["sheet"] = pr["sheet"]
        spec["marks"] = pr["marks"]
        spec["color"] = pr["color"]
        spec["slug"] = False if pr["marks"] == "none" else spec.get("slug")
        spec["layers"] = False if pr["pdfx"] == "PDF/X-1a:2001" \
            else spec.get("layers")
    return pid, spec
```

> `contract` est déjà importé dans `print.py` (il en tire `CardGeom`, `SHEETS`,
> `MM_PER_INCH`). Si l'import est nominatif, ajouter `from . import contract`.

Ajouter la route, **juste avant** `@router.post("/sheet")` (`print.py:4326`) :

```python
@router.post("/pack")
async def post_pack(did: str, spec: str = Form("{}"),
                    fronts: list[UploadFile] = File(default=[]),
                    backs: list[UploadFile] = File(default=[])):
    """LE PAQUET IMPRIMEUR — un ZIP de PNG (ou JPEG) nommés recto / verso.

    C'est ce que MPC et The Game Crafter attendent : pas une planche imposée,
    un fichier par face, appariés par le nom. La taille est celle du GABARIT,
    et `open_card` la fait respecter — un bitmap rendu pour la maison n'entre
    pas dans un paquet MPC, et le message donne les deux chiffres.
    """
    doc = _deck(did)
    body = _json_form(spec)
    pid, sp = _profile_spec(doc, body)
    n = max(1, len(fronts or []), len(backs or []))
    try:
        p = build_plan(sp, n, icc_of(did))
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not fronts:
        raise HTTPException(400, "Aucune carte reçue : le navigateur doit "
                                 "rendre les cartes avant le paquet")
    fmt = str(body.get("card_fmt") or "png").strip().lower()
    if fmt not in CARD_FORMATS:
        raise HTTPException(400, "Format de carte inconnu: " + fmt)
    try:
        bits = int(body.get("card_bits") or 8)
    except (TypeError, ValueError, OverflowError):
        bits = 8
    if bits not in CARD_BITS:
        raise HTTPException(400, "Profondeur inconnue: 8 ou 16 bits")

    brut = {"front": [await f.read() for f in (fronts or [])],
            "back": [await f.read() for f in (backs or [])]}

    def work():
        faces, ext = {}, "png"
        for side, blobs in brut.items():
            if not blobs:
                continue
            faces[side] = {}
            for i, data in enumerate(blobs):
                im = open_card(data, p, i)
                out, _mime, ext = encode_image(
                    im, fmt, bits, p.dpi,
                    bool(body.get("card_alpha", False)), p.jpeg_quality)
                faces[side][i] = out
        slug = PG.deck_slug(str(doc.get("name") or "Jeu"))
        return PG.build_pack(pid, slug, p.geom, faces, ext)

    try:
        out = await asyncio.to_thread(work)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("cards/print: paquet impossible")
        raise HTTPException(500, f"Paquet impossible: {e}")
    return Response(content=out, media_type="application/zip", headers={
        "Content-Disposition": f'attachment; filename="paquet_{pid}.zip"',
        "X-CF-Profile": pid,
        "X-CF-Pixels": f"{p.geom.canvas_px[0]}x{p.geom.canvas_px[1]}",
        "X-CF-Bleed-Px": f"{p.geom.bleed_off_px[0]}x{p.geom.bleed_off_px[1]}",
        "X-CF-Cards": str(n),
        "X-CF-Bytes": str(len(out)),
    })
```

- [ ] **Step 5 : autoriser le sidecar dans le lint**

`scripts/qa/lint_cardforge.py:137` :

```python
EXTRA_PY = {"forge3d": ["forge3d_scene.py", "forge3d_apercu.py"],
            "face": ["style_walkuski.py"],
            # print_gabarits.py : noms de fichiers, ZIP et manifeste du paquet
            # imprimeur (P1). Aucun router — la route reste dans print.py.
            "print": ["print_gabarits.py"]}
```

- [ ] **Step 6 : relancer le banc et le lint**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_gabarits.py
cd ..
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" scripts/qa/lint_cardforge.py
```

Attendu : `9 passed` pour le banc ; `0` (aucune violation) pour le lint.

- [ ] **Step 7 : commit proposé**

```bash
git add backend/app/services/cards/print_gabarits.py backend/app/services/cards/print.py scripts/qa/lint_cardforge.py backend/tests/test_cards_gabarits.py
git commit -m 'cartes : le paquet imprimeur, un fichier par face nomme par le deck' -m 'MPC et The Game Crafter apparient recto et verso par le NOM : le zéro-comblement suit la taille du jeu, sinon un deck de 120 cartes met 100 avant 2 et l  imprimeur imprime la mauvaise. Le manifeste dit la toile relue dans les fichiers écrits (822 x 1122, fond perdu 36 px) et le condensat de chacun ; le banc lit le ZIP, jamais le plan qui l  a demandé.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Task 3 : DriveThruCards — PDF aux dimensions exactes, PDF/X-1a quand c'est tenable

**Files:**
- Modify: `backend/app/services/cards/print.py:158-163` (`PDFX_VERSION` → table de revendications)
- Modify: `backend/app/services/cards/print.py:587-599` (`_pdfx_ok`)
- Modify: `backend/app/services/cards/print.py:2414-2443` (`_output_intents`)
- Modify: `backend/app/services/cards/print.py:2456-2496` (`xmp_packet`)
- Modify: `backend/app/services/cards/print.py:2510-2540` (`build_pdf`, choix de revendication)
- Modify: `backend/app/services/cards/print.py:4366` (`post_pdf` accepte `profile`)
- Modify: `backend/tests/test_cards_gabarits.py`

**Coût de patch** : aucun. Aucun écrivain PDF neuf, **aucune dépendance ajoutée** —
`pypdf 6.16.2` est présent (T1, step 1) et `build_pdf` écrit déjà tout l'appareil.

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_cards_gabarits.py` :

```python
# ─────────────────────── T3 : le PDF DriveThruCards ─────────────────────────
from pypdf import PdfReader                                      # noqa: E402


async def _pdf_dtc(n=2, cmjn=True, icc=None):
    from app.main import app
    tr = ASGITransport(app=app)
    async with AsyncClient(transport=tr, base_url="http://t") as c:
        r = await c.post("/api/cards/decks", json={"name": "Banc DTC"})
        did = r.json()["deck"]["id"]
        await c.patch(f"/api/cards/{did}",
                      json={"format": {"fmt": "poker_us", "dpi": 300}})
        if icc:
            await c.post(f"/api/cards/{did}/print/icc",
                         files={"file": ("p.icc", icc, "application/octet-stream")})
        g = CT.profile_geom("dtc", "poker_us")
        w, h = g.canvas_px
        files = [("fronts", (f"f{i}.png", _png(w, h), "image/png"))
                 for i in range(n)]
        spec = '{"profile":"dtc","force":true}' if cmjn else \
               '{"profile":"dtc","color":"rgb","force":true}'
        return await c.post(f"/api/cards/{did}/print/pdf",
                            data={"spec": spec}, files=files, timeout=180.0)


def test_le_pdf_dtc_fait_198_sur_270_points_et_na_aucun_trait_de_coupe():
    r = asyncio.run(_pdf_dtc(2))
    assert r.status_code == 200, r.text
    rd = PdfReader(io.BytesIO(r.content))
    assert len(rd.pages) == 2
    for pg in rd.pages:
        box = [float(v) for v in pg.mediabox]
        assert box == [0.0, 0.0, 198.0, 270.0], box
        trim = [float(v) for v in pg.trimbox]
        # la rogne = 750 x 1050 px = 180 x 252 pt, centrée : retrait de 9 pt
        assert [round(v, 4) for v in trim] == [9.0, 9.0, 189.0, 261.0], trim
    # AUCUN TRAIT : pas un seul segment vectoriel de repère dans le contenu
    assert r.headers["X-CF-Mark-Clearance"].split("/")[1] == "0", \
        r.headers["X-CF-Mark-Clearance"]


def test_la_revendication_x1a_est_ecrite_quand_elle_est_tenable():
    r = asyncio.run(_pdf_dtc(1))
    assert r.headers["X-CF-Color"] == "cmyk_device", r.headers["X-CF-Color"]
    # RELU DANS LES OCTETS, pas dans le réglage
    assert b"PDF/X-1a:2001" in r.content
    assert b"pdfxid:GTS_PDFXVersion" in r.content
    assert r.content[:8] <= b"%PDF-1.4", r.content[:8]
    assert r.headers["X-CF-Pdfx"] == "PDF/X-1a:2001", r.headers["X-CF-Pdfx"]
    assert r.headers["X-CF-Trapped"] == "/False", r.headers["X-CF-Trapped"]
    assert r.headers["X-CF-Layers"] == "aucun", r.headers["X-CF-Layers"]


def test_en_rvb_le_pdf_dtc_tient_les_dimensions_et_ne_revendique_rien():
    """L'ÉCART, DIT : X-1a interdit tout espace ICCBased dans le contenu.
    En RVB on livre quand même le bon format — et on ne promet rien."""
    r = asyncio.run(_pdf_dtc(1, cmjn=False))
    assert r.status_code == 200, r.text
    rd = PdfReader(io.BytesIO(r.content))
    assert [float(v) for v in rd.pages[0].mediabox] == [0.0, 0.0, 198.0, 270.0]
    assert b"PDF/X-1a:2001" not in r.content
    assert r.headers["X-CF-Pdfx"] == "aucune", r.headers["X-CF-Pdfx"]


def test_le_controle_avant_vol_nomme_le_gabarit_dans_son_verdict():
    r = asyncio.run(_pdf_dtc(1))
    assert "dtc" in r.headers["X-CF-Control"].lower() \
        or "DriveThru" in r.headers["X-CF-Control"], r.headers["X-CF-Control"]
```

- [ ] **Step 2 : lancer, vérifier l'échec**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_gabarits.py
```

Attendu : 4 échecs — `X-CF-Pdfx` vaut `PDF/X-3:2003` ou `aucune`, jamais
`PDF/X-1a:2001`.

- [ ] **Step 3 : paramétrer la revendication dans `print.py`**

Remplacer `print.py:158-159` :

```python
PDFX_VERSION = "PDF/X-3:2003"
```

par :

```python
# ── LES DEUX REVENDICATIONS, ET CE QU'ELLES EXIGENT EN PLUS ─────────────────
# PDF/X-3:2003 admet un espace de sortie ICC et des images étiquetées ; c'est
# la revendication historique de ce fichier. PDF/X-1a:2001 est le même
# appareil, un cran plus strict : DeviceCMYK / DeviceGray / Separation SEULS
# dans le contenu — donc AUCUN /ICCBased, donc `color == "cmyk_device"` — et
# aucun contenu optionnel (les calques sont une construction PDF 1.5).
# Ce que la revendication vaut se relit ensuite dans les octets (`pdf_audit`).
PDFX_CLAIMS = {
    "PDF/X-3:2003": {"colors": ("rgb", "cmyk_device", "cmyk_icc"),
                     "layers_ok": False},
    "PDF/X-1a:2001": {"colors": ("cmyk_device",), "layers_ok": False},
}
PDFX_VERSION = "PDF/X-3:2003"      # le défaut, inchangé
```

Remplacer `_pdfx_ok` (`print.py:587-599`) :

```python
def _pdfx_ok(oi: dict, claim: str = PDFX_VERSION, color: str = "rgb",
             layers: bool = False) -> bool:
    """La revendication `claim` est-elle TENABLE pour cette intention et ce
    réglage ?

    Vrai seulement si l'intention décrit une CONDITION DE PRESSE (registre ICC
    normalisé, ou profil fourni de classe « prtr »), ET si l'espace des visuels
    est admis par la révision demandée, ET s'il n'y a pas de contenu optionnel.
    Un profil d'écran (« mntr », le cas de sRGB) décrit la source : ISO 15930
    ne l'admet pas en `/DestOutputProfile`.

    LA LIGNE AJOUTÉE POUR X-1a : `/ICCBased` est interdit dans le CONTENU d'un
    PDF/X-1a. `_image_xobject` en pose un dès que `color` vaut `rgb` ou
    `cmyk_icc` ; seul `cmyk_device` écrit des images `/DeviceCMYK` nues.
    Revendiquer X-1a sur du RVB serait exactement le défaut que ce fichier a
    déjà corrigé une fois pour `/S /GTS_PDFX`.
    """
    spec = PDFX_CLAIMS.get(claim)
    if not spec:
        return False
    if color not in spec["colors"]:
        return False
    if layers and not spec["layers_ok"]:
        return False
    if not oi or not oi.get("press"):
        return False
    if oi.get("profile"):
        return oi.get("cls") == "prtr" and oi.get("space") == "CMYK"
    return bool(oi.get("registry")) and oi.get("space") == "CMYK"
```

Dans `_output_intents` (`print.py:2414`), la signature devient
`def _output_intents(writer, oi: dict, claim: bool | str):` et la ligne 2431 :

```python
        d[NameObject("/GTS_PDFXVersion")] = TextStringObject(
            claim if isinstance(claim, str) else PDFX_VERSION)
```

Dans `xmp_packet` (`print.py:2456`), la signature devient
`def xmp_packet(fields: dict, title: str, pdfx: bool | str) -> bytes:` et le bloc
`px` :

```python
    ver = pdfx if isinstance(pdfx, str) else (PDFX_VERSION if pdfx else "")
    px = (f'      <pdfxid:GTS_PDFXVersion>{ver}</pdfxid:GTS_PDFXVersion>\n'
          if ver else "")
    nsx = ('    xmlns:pdfxid="http://www.npes.org/pdfx/ns/id/"\n'
           if ver else "")
```

Dans `build_pdf` (`print.py:2510`), à l'endroit où la revendication est décidée
(le calcul qui alimente aujourd'hui `_pdfx_ok(...)` et `w.pdf_header`), remplacer par :

```python
    # LA RÉVISION DEMANDÉE PAR LE GABARIT, ou X-3 par défaut. `p.pdfx` vient du
    # plan ; il ne PROMET rien — `_pdfx_ok` décide, et sur les mêmes critères
    # que l'audit qui relira le fichier.
    claim = getattr(p, "pdfx", None) or PDFX_VERSION
    pdfx = _pdfx_ok(p.out_intent, claim, p.color, p.layers)
    w.pdf_header = "%PDF-1.5" if p.layers else "%PDF-1.4"
```

et passer `claim if pdfx else False` là où `_output_intents` et `xmp_packet`
recevaient un booléen.

Dans `Plan` (`print.py:842`), ajouter le champ :

```python
    pdfx: str = PDFX_VERSION
```

et dans `build_plan` (`print.py:889`), le lire de la spec avec une liste blanche :

```python
    pdfx = _pick(body, "pdfx", tuple(PDFX_CLAIMS), "La révision PDF/X") \
        if body.get("pdfx") else PDFX_VERSION
```

Enfin, `post_pdf` (`print.py:4366`) : remplacer `spec = _spec_of(doc, body)` par

```python
    pid, spec = _profile_spec(doc, body)
    if pid != "maison":
        spec["pdfx"] = contract.printer_profile(pid)["pdfx"] or PDFX_VERSION
```

et ajouter au dictionnaire d'en-têtes de la réponse :

```python
        "X-CF-Profile": pid,
```

- [ ] **Step 4 : faire dire le gabarit au contrôle avant vol**

Dans `control_line` (`print.py:4153`), préfixer la ligne rendue par le gabarit —
la spec y est déjà passée :

```python
def control_line(out: dict | None, forced: bool = False,
                 profile: str = "maison") -> str:
    ...
    # en tête de la phrase produite :
    tete = "" if profile == "maison" else \
        f"[gabarit {profile} — {contract.printer_profile(profile)['label']}] "
    return tete + <la phrase existante>
```

et l'appeler depuis `post_pdf` avec `control_line(pf, _flag(spec, "force"), pid)`.

- [ ] **Step 5 : relancer**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_gabarits.py
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_print.py
```

Attendu : `13 passed` pour les gabarits ; `test_cards_print.py` inchangé, **tout
vert** (la valeur par défaut de `pdfx` est l'ancienne constante, donc aucun PDF
existant ne change).

- [ ] **Step 6 : commit proposé**

```bash
git add backend/app/services/cards/print.py backend/tests/test_cards_gabarits.py
git commit -m 'cartes : la revendication PDF X devient un parametre, DriveThruCards entre' -m 'pypdf 6.16.2 est présent dans le runtime embarqué (mesuré) et build_pdf écrit déjà boîtes, intentions de sortie, XMP et /Trapped : PDF/X-1a n  est pas un écrivain neuf, c  est un cran de plus sur la garde qui existe. Il n  est revendiqué qu  en CMJN d  appareil sans calques, parce que X-1a interdit tout ICCBased dans le contenu ; en RVB le fichier tient les 198 x 270 points de DriveThruCards et ne promet rien. Aucune dépendance ajoutée au build.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Task 4 : L'écran — le gabarit se choisit dans la pièce 07

**Files:**
- Modify: `frontend/cardforge/js/mod-print.js:592-615` (`DEFAULTS` + clé `profile`)
- Modify: `frontend/cardforge/js/mod-print.js:2265-2278` (`state`)
- Modify: `frontend/cardforge/css/mod-print.css`
- Modify: `backend/app/services/cards/print.py:3879` (route `/gabarits`)
- Modify: `backend/tests/test_cards_gabarits.py`

**Coût de patch** : **zéro**. `/cardforge/` est autonome, hors bundle : cette tâche
se recharge par un F5.

- [ ] **Step 1 : écrire le banc-miroir qui échoue**

Ajouter à `backend/tests/test_cards_gabarits.py` :

```python
# ─────────────────────── T4 : l'écran dit le gabarit ────────────────────────
def test_la_route_gabarits_sert_le_catalogue():
    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Cat"})
            did = r.json()["deck"]["id"]
            return await c.get(f"/api/cards/{did}/print/gabarits?fmt=poker_us")
    r = asyncio.run(go())
    assert r.status_code == 200, r.text
    j = r.json()
    ids = [g["id"] for g in j["gabarits"]]
    assert ids == ["maison", "mpc", "tgc", "dtc"], ids
    mpc = j["gabarits"][1]
    assert mpc["geom"]["canvas_px"] == [822, 1122]
    assert mpc["delivery"] == "png_zip"


def test_l_ecran_ecrit_les_chiffres_du_gabarit_et_l_ecart_pdfx():
    """BANC-MIROIR : on lit le fichier SERVI au navigateur. Un gabarit qui
    n'affiche pas ses pixels ne vaut rien — l'utilisateur doit lire 822 x 1122
    AVANT de payer un envoi refusé."""
    js = (pathlib.Path(__file__).resolve().parents[2] / "frontend" / "cardforge"
          / "js" / "mod-print.js").read_text(encoding="utf-8")
    assert 'M.api.get("gabarits' in js, "le catalogue vient du backend"
    assert 'data-act="pack"' in js, "le bouton du paquet imprimeur"
    assert "profile" in js
    for phrase in (
            "822", "1122", "36",              # les pixels de MPC, à l'écran
            "825", "1125", "75",              # TGC et DTC
            "2,75", "3,75",                   # la page DriveThruCards
            "PDF/X-1a",
            # L'ÉCART, ÉCRIT DANS L'ÉCRAN et pas seulement dans un commentaire
            "conformité PDF/X-1a non revendiquée",
            "profil ICC de l’imprimeur",
            "sans retrait des sous-couleurs",
            # et le désaccord de MPC, dit à celui qui va cliquer
            "le portail contrôle les pixels"):
        assert phrase in js, phrase
```

- [ ] **Step 2 : lancer, vérifier l'échec**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_gabarits.py
```

Attendu : 2 échecs (404 sur `/gabarits`, phrases absentes de `mod-print.js`).

- [ ] **Step 3 : la route de catalogue**

Dans `print.py`, juste après `@router.get("/sheets")` (`print.py:3879`) :

```python
@router.get("/gabarits")
async def get_gabarits(did: str, fmt: str = ""):
    """Le catalogue des gabarits d'imprimeur, avec la géométrie que chacun
    impose au format demandé. `geom: null` = ce gabarit ne sert pas ce format
    — l'écran grise la ligne au lieu d'inventer des pixels."""
    doc = _deck(did)
    f = str(fmt or "").strip().lower() \
        or str((doc.get("format") or {}).get("fmt") or contract.DEFAULT_FMT)
    try:
        table = contract.profile_table(f)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"fmt": f, "gabarits": table}
```

- [ ] **Step 4 : le panneau dans `mod-print.js`**

Ajouter `profile: "maison"` à `DEFAULTS` (`mod-print.js:592`) — la clé entre donc
automatiquement dans `state` (ligne 2276, `Object.assign({}, DEFAULTS)`).

Ajouter, avant l'enregistrement, le bloc de rendu et son câblage :

```js
  /* ══ GABARITS D'IMPRIMEUR (P1) ═══════════════════════════════════════════
     Le catalogue vient du backend : cet ecran ne DERIVE aucun pixel. Les
     chiffres affiches sont ceux de `contract.profile_geom`, relus tels quels.
     ══════════════════════════════════════════════════════════════════════ */
  let GAB = [];

  /* Ce que chaque gabarit impose, en une phrase qu'on lit AVANT de cliquer.
     Le desaccord de MPC est ecrit ici, pas seulement dans un commentaire
     Python : c'est l'utilisateur qui paye un envoi refuse. */
  const GAB_NOTE = {
    mpc: "822 x 1122 px, fond perdu 36 px, zone sûre 72 px du bord. "
       + "MakePlayingCards publie « 1/8 in » mais le portail contrôle les "
       + "pixels : 1/8 in vaudrait 37,5 px, donc 825 x 1125, et l’envoi "
       + "serait refusé.",
    tgc: "825 x 1125 px, coupe à 37,5 px du bord, zone sûre à 75 px. "
       + "C’est exactement la toile du Card Forge : rien à convertir.",
    dtc: "Page de 2,75 x 3,75 in (198 x 270 pt), une face par page, "
       + "AUCUN trait de coupe. PDF/X-1a:2001 n’est revendiqué qu’en CMJN "
       + "d’appareil et sans calques.",
    maison: "Planches imposées A4 / Letter / A3, traits de coupe et "
          + "cartouche : le comportement historique.",
  };

  /* L'ECART, DIT A L'ECRAN. Le fichier part quand meme — aux bonnes
     dimensions — mais il ne promet pas ce qu'il ne tient pas. */
  function ecartPdfx(g) {
    if (!g || g.pdfx !== "PDF/X-1a:2001") return "";
    if (ICC && ICC.loaded) {
      return "Profil de presse chargé : séparation littleCMS, conformité "
           + "PDF/X-1a revendiquée et relue dans les octets du fichier.";
    }
    return "Dimensions DriveThruCards tenues, conformité PDF/X-1a non "
         + "revendiquée : la conversion CMJN est celle de l’appareil, "
         + "sans retrait des sous-couleurs ni noir squelette. Chargez le "
         + "profil ICC de l’imprimeur pour que la revendication soit écrite.";
  }

  function paintGabarits() {
    const box = HOST && HOST.querySelector("#cf-print-gabarits");
    if (!box) return;
    const cur = CF.get("print.profile", "maison");
    box.innerHTML = GAB.map((g) => {
      const on = g.id === cur;
      const ko = !g.geom;
      const px = g.geom
        ? g.geom.canvas_px[0] + " x " + g.geom.canvas_px[1] + " px · fond "
          + "perdu " + nf(g.geom.bleed_off_px[0], 1) + " px · zone sûre à "
          + nf(g.geom.safe_off_px[0], 1) + " px du bord"
        : "ce gabarit ne sert pas ce format";
      return '<button type="button" class="cf-print-gab' + (on ? " on" : "")
        + (ko ? " ko" : "") + '" data-act="profile" data-v="' + esc(g.id)
        + '"' + (ko ? " disabled" : "") + '>'
        + '<b>' + esc(g.label) + '</b>'
        + '<i class="px">' + esc(px) + '</i>'
        + '<i class="note">' + esc(GAB_NOTE[g.id] || g.note) + '</i>'
        + (g.pdfx ? '<i class="pdfx">' + esc(g.pdfx) + '</i>' : "")
        + '</button>';
    }).join("");
    const w = HOST.querySelector("#cf-print-gab-ecart");
    if (w) {
      const g = GAB.filter((x) => x.id === cur)[0];
      w.textContent = ecartPdfx(g);
      w.classList.toggle("hidden", !w.textContent);
    }
    const b = HOST.querySelector('[data-act="pack"]');
    if (b) {
      const g = GAB.filter((x) => x.id === cur)[0];
      b.classList.toggle("hidden", !g || g.delivery !== "png_zip");
    }
  }

  async function loadGabarits() {
    try {
      const r = await M.api.get("gabarits?fmt="
        + encodeURIComponent(CF.geom().fmt));
      if (r && Array.isArray(r.gabarits)) { GAB = r.gabarits; paintGabarits(); }
    } catch (e) {
      if (!(e && e.missing)) console.warn("cardforge/print: gabarits", e);
    }
  }

  /* Le paquet : le navigateur rend, le backend nomme et archive. */
  async function envoyerPaquet() {
    const cards = CF.cards();
    if (!cards.length) { CF.toast("Aucune carte à empaqueter", true); return; }
    CF.busy(true, "Rendu des cartes…");
    try {
      const fd = new FormData();
      fd.append("spec", JSON.stringify({
        profile: CF.get("print.profile", "maison"),
        card_fmt: CF.get("print.card_fmt", "png"),
        card_bits: CF.get("print.card_bits", 8),
      }));
      for (let i = 0; i < cards.length; i++) {
        fd.append("fronts", await CF.cardBlob(i, { face: "front" }),
                  "f" + i + ".png");
        fd.append("backs", await CF.cardBlob(i, { face: "back" }),
                  "b" + i + ".png");
        CF.busy(true, "Rendu " + (i + 1) + " / " + cards.length);
      }
      const r = await M.api.blob("POST", "pack", fd);
      CF.download(r.blob, "paquet_"
        + CF.get("print.profile", "maison") + ".zip");
      CF.toast("Paquet écrit : " + (r.headers["x-cf-cards"] || "?")
        + " carte(s) à " + (r.headers["x-cf-pixels"] || "?") + " px");
    } catch (e) {
      CF.toast("Paquet impossible : " + (e && e.message), true);
    } finally { CF.busy(false); }
  }
```

Dans `shell()`, insérer le conteneur en tête du panneau (avant le bloc « contrôle
avant vol ») :

```js
    '<section class="cf-print-bloc" id="cf-print-bloc-gabarit">',
    '  <h3>Gabarit d’imprimeur</h3>',
    '  <div id="cf-print-gabarits" class="cf-print-gabs"></div>',
    '  <p id="cf-print-gab-ecart" class="cf-print-ecart hidden"></p>',
    '  <button type="button" class="cf-btn" data-act="pack">',
    '    Paquet imprimeur (.zip)</button>',
    '</section>',
```

Dans `wire()`, ajouter les deux actions :

```js
      if (act === "profile") {
        M.patch({ profile: String(t.dataset.v) });
        const g = GAB.filter((x) => x.id === t.dataset.v)[0];
        if (g && g.geom) {
          M.setFormat({ bleed_mm: g.geom.bleed_mm, safe_mm: g.geom.safe_mm,
                        dpi: g.geom.dpi });
        }
        paintGabarits(); refresh(); schedulePreflight();
        return;
      }
      if (act === "pack") { envoyerPaquet(); return; }
```

Dans `init(host)`, après `paintFormats()` : `loadGabarits();` et dans l'écouteur
`CF.on("core:geom", ...)` : `loadGabarits();`.

Dans `css/mod-print.css`, ajouter (règle 4 : tout sélecteur porte `.cf-print`) :

```css
.cf-print .cf-print-gabs { display: grid; gap: 6px; }
.cf-print .cf-print-gab {
  display: grid; gap: 2px; text-align: left; padding: 8px 10px;
  border: 1px solid var(--line); border-radius: 6px;
  background: var(--bg-elev); color: inherit; cursor: pointer;
}
.cf-print .cf-print-gab.on { border-color: var(--cyan); }
.cf-print .cf-print-gab.ko { opacity: .45; cursor: not-allowed; }
.cf-print .cf-print-gab .px { font-variant-numeric: tabular-nums; opacity: .85; }
.cf-print .cf-print-gab .note,
.cf-print .cf-print-ecart { font-size: 12px; opacity: .78; line-height: 1.45; }
.cf-print .cf-print-gab .pdfx { font-size: 11px; letter-spacing: .04em; }
.cf-print .cf-print-ecart.hidden { display: none; }
```

- [ ] **Step 5 : relancer le banc et le lint**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_gabarits.py
cd ..
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" scripts/qa/lint_cardforge.py --module print
```

Attendu : `15 passed` ; lint `0`.

- [ ] **Step 6 : commit proposé**

```bash
git add frontend/cardforge/js/mod-print.js frontend/cardforge/css/mod-print.css backend/app/services/cards/print.py backend/tests/test_cards_gabarits.py
git commit -m 'cartes : le gabarit se choisit a l ecran, avec ses pixels et son ecart' -m 'Un gabarit qui n  affiche pas ses chiffres ne sert à rien : c  est l  utilisateur qui paye l  envoi refusé. Le panneau écrit 822 x 1122 et 36 px pour MPC, dit pourquoi le « 1/8 in » publié serait refusé, et écrit noir sur blanc que sans profil ICC de presse le PDF DriveThruCards tient ses dimensions sans revendiquer PDF/X-1a. Aucun patch de bundle : /cardforge/ est autonome.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Task 5 : Tabletopia relu, et la onzième pièce `edition`

**Files:**
- Modify: `backend/app/services/cards/contract.py:83-84` (`MODULE_IDS`)
- Modify: `backend/app/services/cards/__init__.py:74-76`
- Create: `backend/app/services/cards/edition.py`
- Modify: `frontend/cardforge/js/core.js:82`
- Modify: `frontend/cardforge/index.html`
- Create: `frontend/cardforge/js/mod-edition.js`, `frontend/cardforge/css/mod-edition.css`
- Modify: `scripts/qa/lint_cardforge.py:100-138`
- Create: `backend/tests/test_cards_edition.py`

**Coût de patch** : **les huit points CORE de la section « Coût de patch », une seule
fois pour tout le plan.** Zéro patch de bundle.

- [ ] **Step 1 : relire le format Tabletopia AVANT d'écrire une ligne**

R10d classe Tabletopia « de mémoire ». On vérifie, on date, on écrit le résultat.

```
WebFetch url=https://help.tabletopia.com/knowledge-base/how-to-prepare-graphics/
  prompt=Give the exact numeric specifications for preparing card/deck graphics:
  image formats accepted, maximum image resolution in pixels, how a multi-card
  sheet is described (number of cards horizontally/vertically), any bleed or safe
  zone requirement, and any file size limit. Quote the numbers verbatim.

WebFetch url=https://help.tabletopia.com/knowledge-base/card/
  prompt=Give the technical specifications of the Card object: maximum size,
  thickness, complex shape support, and any image requirement. Quote verbatim.
```

Relevé du 03/09/2026 (à confirmer, pas à recopier de confiance) :

- JPEG et PNG ; « Try not to exceed the image size of **2000 × 2000 pixels** for each
  object » ; « Maximum objects size are **3-10 MB** », visé 1–2 MB.
- Recto et verso dans des **fichiers séparés**, de **même taille en pixels**.
- Card : « Size: up to **1600 × 1600 mm** », « Thickness: **0.2 mm** ».
- **Aucune grille de collage n'est publiée.** Le « 10 × 7 » de R10d appartient à
  Tabletop Simulator.

**Décision, écrite dans le code** : TTS → collage. Tabletopia → **une image par
face** + manifeste. Si le WebFetch dit autre chose aujourd'hui, **corriger la
décision avant T7**, pas après.

- [ ] **Step 2 : écrire le banc de la coquille, qui échoue**

Créer `backend/tests/test_cards_edition.py` :

```python
# -*- coding: utf-8 -*-
"""Card Forge — pièce 11 « Édition » : ce qui se livre AUTOUR de la carte.

Table virtuelle (Tabletop Simulator, Tabletopia), livret de règles, mockup,
fiche produit. La pièce ne dessine RIEN : aucun z ne lui est alloué.

Run : cd backend ; python tests/test_cards_edition.py
"""
import asyncio
import io
import json
import os
import pathlib
import struct
import sys
import tempfile
import zipfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest                                                    # noqa: E402
from httpx import ASGITransport, AsyncClient                     # noqa: E402
from PIL import Image                                            # noqa: E402

from app.services.cards import contract as CT                    # noqa: E402

RACINE = pathlib.Path(__file__).resolve().parents[2]
FRONT = RACINE / "frontend" / "cardforge"


def test_la_piece_existe_dans_les_QUATRE_listes_qui_doivent_saccorder():
    """Le piège nommé par core.js:78 — un id présent d'un côté et absent de
    l'autre voit son sous-arbre JETÉ à chaque autosave, sans un message. Les
    quatre listes se tiennent la main."""
    assert "edition" in CT.MODULE_IDS, CT.MODULE_IDS
    js = (FRONT / "js" / "core.js").read_text(encoding="utf-8")
    assert '"edition"' in js.split("const MODULES =")[1].split("]")[0]
    lint = (RACINE / "scripts" / "qa" / "lint_cardforge.py") \
        .read_text(encoding="utf-8")
    assert '"edition": set()' in lint, "Z_TABLE : la pièce ne dessine pas"
    assert '"edition"' in lint.split("MODULES = [")[1].split("]")[0]
    init = (RACINE / "backend" / "app" / "services" / "cards" / "__init__.py") \
        .read_text(encoding="utf-8")
    assert 'prefix="/{did}/edition"' in init


def test_les_quatre_fichiers_de_la_piece_sont_la():
    for p in (FRONT / "js" / "mod-edition.js",
              FRONT / "css" / "mod-edition.css",
              RACINE / "backend/app/services/cards/edition.py",
              RACINE / "backend/tests/test_cards_edition.py"):
        assert p.is_file(), p


def test_la_coquille_est_montee_dans_la_page():
    html = (FRONT / "index.html").read_text(encoding="utf-8")
    assert 'href="css/mod-edition.css"' in html
    assert 'id="cf-panel-edition" data-mod="edition"' in html
    assert 'src="js/mod-edition.js"' in html
    # le script APRÈS core.js, et après les dix autres : l'ordre du rail
    assert html.index('js/mod-edition.js') > html.index('js/mod-capture.js')


def test_la_piece_repond_et_nenregistre_aucun_painter():
    js = (FRONT / "js" / "mod-edition.js").read_text(encoding="utf-8")
    assert js.lstrip().startswith('/*') or js.lstrip().startswith('"use strict"')
    assert '"use strict"' in js[:2000], "règle 11"
    assert "painters: []" in js, "aucun z alloué à cette pièce"
    assert 'id: "edition"' in js and "order: 11" in js

    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Édition"})
            did = r.json()["deck"]["id"]
            return await c.get(f"/api/cards/{did}/edition/cibles")
    r = asyncio.run(go())
    assert r.status_code == 200, r.text
    ids = [t["id"] for t in r.json()["cibles"]]
    assert ids == ["tts", "tabletopia"], ids


def test_le_sous_arbre_edition_survit_a_un_enregistrement():
    """Le défaut de forge3d, phases 2a→3c : un id absent de MODULE_IDS voyait
    son sous-arbre effacé en silence à chaque autosave."""
    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Survie"})
            did = r.json()["deck"]["id"]
            await c.patch(f"/api/cards/{did}",
                          json={"edition": {"cible": "tts", "cols": 10}})
            return (await c.get(f"/api/cards/{did}")).json()
    doc = asyncio.run(go())
    assert doc["deck"]["edition"]["cible"] == "tts", doc["deck"].get("edition")
    assert doc["deck"]["edition"]["cols"] == 10


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
```

- [ ] **Step 3 : lancer, vérifier l'échec**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_edition.py
```

Attendu : 5 échecs.

- [ ] **Step 4 : les huit retouches CORE**

`contract.py:83` :

```python
MODULE_IDS = ("face", "frame", "type", "data", "solid", "texture",
              "print", "gltf", "forge3d", "capture", "edition")
```

`cards/__init__.py`, après le bloc `capture` (ligne 74-76), et **avant** le filet
`@router.api_route("/{rest:path}")` :

```python
# P11 « edition » : ce qui se livre AUTOUR de la carte — table virtuelle,
# livret, mockup, fiche produit. Aucun painter : elle ne dessine pas la carte.
router.include_router(edition.router, prefix="/{did}/edition",
                      tags=["cards:edition"])
```

et l'import en tête : `from . import face, frame, data, solid, texture, gltf, forge3d, capture, edition`.
Compléter aussi le tableau d'assemblage du docstring :

```
    /api/cards/{did}/edition/…    P11    edition.py
```

`core.js:82` :

```js
  const MODULES = ["face", "frame", "type", "data", "solid", "texture", "print", "gltf", "forge3d", "capture", "edition"];
```

`index.html` : une `<link>` après `mod-capture.css`, une `<section>` après celle de
`capture`, un `<script>` après `mod-capture.js` :

```html
<link rel="stylesheet" href="css/mod-edition.css">
```
```html
    <section class="cf-panel" id="cf-panel-edition" data-mod="edition">
      <div class="cf-host cf-edition"></div>
    </section>
```
```html
<script src="js/mod-edition.js"></script>
```

`scripts/qa/lint_cardforge.py` : `Z_TABLE` gagne `"edition": set(),` ; `MODULES`
gagne `"edition"` en dernier ; `EXTRA_PY` gagne (pour T6, T7, T18, T19) :

```python
            # edition_vtt.py : collage TTS, objet JSON, paquet Tabletopia.
            # edition_livret.py : livret PDF, mockup, fiche produit.
            # Ni l'un ni l'autre n'a de router — la route vit dans edition.py.
            "edition": ["edition_vtt.py", "edition_livret.py"],
```

- [ ] **Step 5 : `edition.py`, la coquille**

```python
# -*- coding: utf-8 -*-
"""Card Forge — pièce 11 « Édition ».

CE QUI SE LIVRE AUTOUR DE LA CARTE : la table virtuelle (Tabletop Simulator,
Tabletopia), le livret de règles, le mockup marketing, la fiche produit.

Elle ne dessine RIEN : aucun z ne lui est alloué (lint, Z_TABLE). Comme P7,
elle IMPOSE des cartes rendues par `CF.renderCard` et téléversées — le
navigateur voit et manipule, Python écrit.
"""
from __future__ import annotations

import asyncio
import io
import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from loguru import logger

from . import contract
from . import edition_vtt as VTT

router = APIRouter()

# Les cibles, dans l'ordre du panneau. Chacune dit ce qu'elle SAIT, pas ce
# qu'on aimerait : la grille 10 x 7 est une convention de gabarit TTS, pas un
# chiffre publié (relevé du 03/09/2026, kb.tabletopsimulator.com — le champ
# « how many cards horizontally and vertically » existe, sans maximum).
CIBLES = [
    {"id": "tts", "label": "Tabletop Simulator — collage + objet sauvegardé",
     "livraison": "zip",
     "note": "Collage de 10 x 7 cartes par planche (convention de gabarit ; "
             "la base de connaissances publie le champ, pas le maximum) et un "
             "objet JSON à déposer dans Saved Objects. Plafond de texture "
             "mesuré : 4096 px de large pour un Custom Deck rectangulaire."},
    {"id": "tabletopia", "label": "Tabletopia — une image par face",
     "livraison": "zip",
     "note": "La documentation Tabletopia (03/09/2026) demande recto et verso "
             "dans des FICHIERS SÉPARÉS de même taille, 2000 x 2000 px au "
             "plus, 1 à 2 Mo visés. Elle ne publie AUCUNE grille de collage : "
             "on ne lui en envoie pas."},
]


def _deck(did: str) -> dict:
    """Le document du jeu, ou 400/404 — jamais un 500."""
    from . import core
    return core.deck_or_404(did)


def _json_form(spec: str) -> dict:
    try:
        v = json.loads(spec or "{}")
    except Exception:
        raise HTTPException(400, "Le champ `spec` n'est pas du JSON")
    if not isinstance(v, dict):
        raise HTTPException(400, "Le champ `spec` doit être un objet JSON")
    return v


@router.get("/cibles")
async def get_cibles(did: str):
    """Le catalogue des tables virtuelles servies, avec ce que chacune exige."""
    _deck(did)
    return {"cibles": CIBLES}
```

> `core.deck_or_404` : si le helper porte un autre nom dans `core.py`, réutiliser
> celui qui existe (`print.py:3810 _deck` fait déjà exactement cela et montre la
> forme attendue). **Ne pas dupliquer la logique de validation du `did`** :
> `contract.deck_dir` reste la seule porte.

- [ ] **Step 6 : `mod-edition.js` et `mod-edition.css`, la coquille**

```js
/* ═══════════════════════════════════════════════════════════════════════════
   Card Forge — piece 11 · Edition   [P11]
   Proprietaire exclusif de : doc.edition · aucun z · /api/cards/<did>/edition/*
   Prefixe DOM impose : id="cf-edition-..."   ·   feuille : css/mod-edition.css

   CE QUE CETTE PIECE NE FAIT PAS : dessiner une carte. Elle IMPOSE des cartes
   rendues par CF.renderCard (via CF.cardBlob) et les televerse. Elle livre ce
   qui entoure le jeu : table virtuelle, livret, mockup, fiche produit.
   ═══════════════════════════════════════════════════════════════════════════ */
"use strict";

(function () {
  const CF = (typeof window !== "undefined") ? window.CF : null;
  if (!CF) throw new Error("mod-edition: js/core.js doit etre charge avant ce fichier");

  const esc = (s) => String(s == null ? "" : s).replace(/&/g, "&amp;")
    .replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

  let M = null, HOST = null, CIBLES = [];

  const DEFAULTS = {
    cible: "tts",      /* tts | tabletopia */
    cols: 10,          /* colonnes du collage TTS */
    rows: 7,           /* lignes du collage TTS */
    nom: "",           /* surnom de l'objet sauvegarde */
  };

  function shell() {
    HOST.innerHTML = [
      '<section class="cf-edition-bloc">',
      '  <h3>Table virtuelle</h3>',
      '  <div id="cf-edition-cibles" class="cf-edition-cibles"></div>',
      '  <button type="button" class="cf-btn" data-act="exporter">',
      '    Exporter pour la table (.zip)</button>',
      '</section>',
    ].join("");
  }

  function paintCibles() {
    const box = HOST.querySelector("#cf-edition-cibles");
    const cur = CF.get("edition.cible", "tts");
    box.innerHTML = CIBLES.map((c) =>
      '<button type="button" class="cf-edition-cible'
      + (c.id === cur ? " on" : "") + '" data-act="cible" data-v="'
      + esc(c.id) + '"><b>' + esc(c.label) + '</b><i>'
      + esc(c.note) + '</i></button>').join("");
  }

  function wire() {
    HOST.addEventListener("click", (ev) => {
      const t = ev.target.closest("[data-act]");
      if (!t) return;
      const act = t.dataset.act;
      if (act === "cible") { M.patch({ cible: String(t.dataset.v) }); paintCibles(); }
      if (act === "exporter") { exporter(); }
    });
  }

  async function exporter() {
    const cards = CF.cards();
    if (!cards.length) { CF.toast("Aucune carte à exporter", true); return; }
    const cible = CF.get("edition.cible", "tts");
    CF.busy(true, "Rendu des cartes…");
    try {
      const fd = new FormData();
      fd.append("spec", JSON.stringify({
        cols: CF.get("edition.cols", 10), rows: CF.get("edition.rows", 7),
        nom: CF.get("edition.nom", "") || CF.doc().name,
      }));
      for (let i = 0; i < cards.length; i++) {
        fd.append("fronts", await CF.cardBlob(i, { face: "front" }), "f" + i + ".png");
        fd.append("backs", await CF.cardBlob(i, { face: "back" }), "b" + i + ".png");
        CF.busy(true, "Rendu " + (i + 1) + " / " + cards.length);
      }
      const r = await M.api.blob("POST", cible, fd);
      CF.download(r.blob, cible + ".zip");
      CF.toast("Écrit : " + (r.headers["x-cf-sheets"] || "?") + " planche(s), "
        + (r.headers["x-cf-cards"] || "?") + " carte(s)");
    } catch (e) {
      CF.toast("Export impossible : " + (e && e.message), true);
    } finally { CF.busy(false); }
  }

  M = CF.register({
    id: "edition",
    title: "Édition",
    icon: "\u{1F4E6}",
    order: 11,
    painters: [],
    state: Object.assign({}, DEFAULTS),
    async init(host) {
      HOST = host;
      shell();
      wire();
      try {
        const r = await M.api.get("cibles");
        if (r && Array.isArray(r.cibles)) CIBLES = r.cibles;
      } catch (e) {
        if (!(e && e.missing)) console.warn("cardforge/edition: cibles", e);
      }
      paintCibles();
      CF.on("core:doc", (p) => { if (!p || p.id === "edition") paintCibles(); });
      M.emit("ready", {});
    },
  });
})();
```

```css
/* Card Forge — piece 11 · Edition. Regle 4 : tout selecteur porte .cf-edition */
.cf-edition .cf-edition-bloc { display: grid; gap: 10px; }
.cf-edition .cf-edition-cibles { display: grid; gap: 6px; }
.cf-edition .cf-edition-cible {
  display: grid; gap: 3px; text-align: left; padding: 8px 10px;
  border: 1px solid var(--line); border-radius: 6px;
  background: var(--bg-elev); color: inherit; cursor: pointer;
}
.cf-edition .cf-edition-cible.on { border-color: var(--cyan); }
.cf-edition .cf-edition-cible i { font-size: 12px; opacity: .78; line-height: 1.45; }
```

- [ ] **Step 7 : relancer banc, lint et contrat**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_edition.py
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_core.py
cd ..
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" scripts/qa/lint_cardforge.py
node frontend/cardforge/qa/test_core_contract.mjs --geom
```

Attendu : `5 passed` ; `test_cards_core.py` vert ; lint `0` ; le contrat `--geom`
sort 0 (la géométrie n'a pas bougé).

- [ ] **Step 8 : commit proposé**

```bash
git add backend/app/services/cards/contract.py backend/app/services/cards/__init__.py backend/app/services/cards/edition.py frontend/cardforge/js/core.js frontend/cardforge/index.html frontend/cardforge/js/mod-edition.js frontend/cardforge/css/mod-edition.css scripts/qa/lint_cardforge.py backend/tests/test_cards_edition.py
git commit -m 'cartes : une onzieme piece pour ce qui se livre autour de la carte' -m 'Tabletopia relu le 03/09 sur sa documentation : recto et verso dans des FICHIERS SÉPARÉS, 2000 x 2000 px au plus, et AUCUNE grille de collage publiée — le « 10 x 7 » appartient à Tabletop Simulator. Les deux cibles ne se ressemblent donc pas, et la pièce le dit avant l  export. Les quatre listes qui doivent s  accorder (MODULE_IDS, core.js, le lint, l  assemblage) sont retouchées ensemble : un id présent d  un côté et absent de l  autre voit son sous-arbre jeté à chaque enregistrement, sans un message — c  est arrivé à forge3d.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Task 6 : Tabletop Simulator — le collage 10 × 7 et l'objet sauvegardé

**Files:**
- Create: `backend/app/services/cards/edition_vtt.py`
- Modify: `backend/app/services/cards/edition.py` (route `/tts`)
- Modify: `backend/tests/test_cards_edition.py`

**Coût de patch** : aucun (le sidecar est déjà dans `EXTRA_PY`, T5 step 4).

- [ ] **Step 1 : écrire le banc qui échoue**

Ajouter à `backend/tests/test_cards_edition.py` :

```python
# ─────────────────────── T6 : Tabletop Simulator ────────────────────────────
def _png(w, h, c=(20, 30, 40)):
    b = io.BytesIO(); Image.new("RGB", (w, h), c).save(b, "PNG")
    return b.getvalue()


def _ihdr(data):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


async def _vtt(cible, n, fmt="poker_us", spec="{}"):
    from app.main import app
    tr = ASGITransport(app=app)
    async with AsyncClient(transport=tr, base_url="http://t") as c:
        r = await c.post("/api/cards/decks", json={"name": "Jeu de table"})
        did = r.json()["deck"]["id"]
        await c.patch(f"/api/cards/{did}",
                      json={"format": {"fmt": fmt, "dpi": 300}})
        g = CT.geom(fmt, 300)
        w, h = g.canvas_px
        files = ([("fronts", (f"f{i}.png", _png(w, h), "image/png"))
                  for i in range(n)]
                 + [("backs", (f"b{i}.png", _png(w, h), "image/png"))
                    for i in range(n)])
        return await c.post(f"/api/cards/{did}/edition/{cible}",
                            data={"spec": spec}, files=files, timeout=300.0)


def test_le_collage_tts_tient_sous_le_plafond_de_texture_mesure():
    """4096 px de large est le plafond publié pour un Custom Deck rectangulaire
    (kb.tabletopsimulator.com/custom-content/asset-creation/, 03/09/2026).
    10 colonnes -> 409 px par carte ; un poker_us (825 x 1125) donne donc
    409 x 558, et la planche 4090 x 3906 — sous 4096 sur LES DEUX axes."""
    r = asyncio.run(_vtt("tts", 12))
    assert r.status_code == 200, r.text
    z = zipfile.ZipFile(io.BytesIO(r.content))
    planches = sorted(n for n in z.namelist() if n.endswith(".png"))
    assert planches == ["tts/jeu-de-table_recto_1.png",
                        "tts/jeu-de-table_verso_1.png"], planches
    for n in planches:
        w, h = _ihdr(z.read(n))
        assert (w, h) == (4090, 3906), (n, w, h)
        assert w <= 4096 and h <= 4096


def test_une_planche_par_soixante_dix_cartes_et_pas_une_de_plus():
    r = asyncio.run(_vtt("tts", 71))
    z = zipfile.ZipFile(io.BytesIO(r.content))
    rectos = sorted(n for n in z.namelist() if "_recto_" in n)
    assert rectos == ["tts/jeu-de-table_recto_1.png",
                      "tts/jeu-de-table_recto_2.png"], rectos
    assert r.headers["X-CF-Sheets"] == "2", r.headers["X-CF-Sheets"]


def test_l_objet_sauvegarde_porte_les_champs_que_tts_lit():
    r = asyncio.run(_vtt("tts", 3))
    z = zipfile.ZipFile(io.BytesIO(r.content))
    obj = json.loads(z.read("tts/jeu-de-table.json").decode("utf-8"))
    st = obj["ObjectStates"][0]
    assert st["Name"] == "DeckCustom"
    assert st["Nickname"] == "Jeu de table"
    assert set(st["Transform"]) >= {"posX", "posY", "posZ", "rotX", "rotY",
                                    "rotZ", "scaleX", "scaleY", "scaleZ"}
    cd = st["CustomDeck"]["1"]
    assert cd["NumWidth"] == 10 and cd["NumHeight"] == 7
    assert cd["UniqueBack"] is True
    assert cd["FaceURL"].endswith("jeu-de-table_recto_1.png")
    assert cd["BackURL"].endswith("jeu-de-table_verso_1.png")
    # convention CardID = 100 * id_de_deck + index, DITE dans le manifeste
    assert st["DeckIDs"] == [100, 101, 102], st["DeckIDs"]
    assert len(st["ContainedObjects"]) == 3


def test_le_manifeste_dit_ce_qui_est_convention_et_ce_qui_est_publie():
    r = asyncio.run(_vtt("tts", 3))
    z = zipfile.ZipFile(io.BytesIO(r.content))
    man = json.loads(z.read("tts/manifeste.json").decode("utf-8"))
    assert man["grille"] == [10, 7]
    assert man["plafond_px"] == 4096
    assert "convention" in man["grille_source"].lower()
    assert "kb.tabletopsimulator.com" in man["publie"]
    assert "03/09/2026" in man["publie"]
    # LE MOT QUI MANQUE AILLEURS : le fichier ne se pose pas tout seul
    assert "FaceURL" in man["a_faire"] and "URL" in man["a_faire"]


def test_le_collage_recadre_sur_la_rogne_et_non_sur_la_toile():
    """TTS ne coupe rien : le fond perdu se verrait sur la table. La carte
    posée dans la case est la ROGNE, pas la toile."""
    r = asyncio.run(_vtt("tts", 1))
    z = zipfile.ZipFile(io.BytesIO(r.content))
    man = json.loads(z.read("tts/manifeste.json").decode("utf-8"))
    assert man["source"] == "trim", man["source"]
    assert man["carte_px"] == [409, 558], man["carte_px"]
```

- [ ] **Step 2 : lancer, vérifier l'échec**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_edition.py
```

Attendu : 5 échecs, 404 sur `/edition/tts`.

- [ ] **Step 3 : écrire `edition_vtt.py`**

```python
# -*- coding: utf-8 -*-
"""Card Forge — pièce 11, sidecar « table virtuelle ».

SIDECAR, pas une pièce : aucun `router` ici (règle 8). Des octets, rien d'autre.

CE QUI EST PUBLIÉ ET CE QUI EST CONVENTION — relevé du 03/09/2026, et la
distinction est écrite dans le manifeste que l'utilisateur lira :

  PUBLIÉ (kb.tabletopsimulator.com/custom-content/asset-creation/) :
    « Custom Deck (Rectangle) 4096 x (whatever height fits) ».
  PUBLIÉ (kb.tabletopsimulator.com/custom-content/custom-deck/) :
    le champ « how many cards the sheet will feature horizontally and
    vertically » — SANS maximum.
  CONVENTION, non publiée : la grille 10 x 7 (70 cartes) des gabarits, et
    `CardID = 100 * id_de_deck + index`, lue dans des objets sauvegardés.

  PUBLIÉ (help.tabletopia.com, 03/09/2026) : Tabletopia veut recto et verso
    dans des FICHIERS SÉPARÉS de même taille, 2000 x 2000 px au plus, 1 à
    2 Mo visés — et ne publie AUCUNE grille. On ne lui envoie pas de collage.
"""
from __future__ import annotations

import hashlib
import io
import json
import zipfile

from PIL import Image

from .contract import CardGeom
from .print_gabarits import deck_slug

__all__ = ["TTS_MAX_PX", "TTS_COLS", "TTS_ROWS", "TABLETOPIA_MAX_PX",
           "trim_crop", "tts_cell_px", "build_tts", "build_tabletopia"]

TTS_MAX_PX = 4096            # publié
TTS_COLS, TTS_ROWS = 10, 7   # convention de gabarit
TABLETOPIA_MAX_PX = 2000     # publié

TTS_PUBLIE = ("kb.tabletopsimulator.com/custom-content/asset-creation/ et "
              "/custom-content/custom-deck/, relus le 03/09/2026")
TTPIA_PUBLIE = ("help.tabletopia.com/knowledge-base/how-to-prepare-graphics/ "
                "et /knowledge-base/card/, relus le 03/09/2026")


def trim_crop(im: Image.Image, g: CardGeom) -> Image.Image:
    """La ROGNE, découpée dans la toile. Une table virtuelle ne coupe rien :
    livrer la toile poserait le fond perdu sur le tapis.

    L'origine vient de `bleed_off_px`, qui peut valoir x,5 (c'est assumé par
    la règle) : on arrondit ICI, une seule fois, et le résultat fait
    EXACTEMENT `trim_px` — jamais `canvas - 2*round(bleed)`, qui perdrait un
    pixel sur les formats impériaux.
    """
    x = int(round(g.bleed_off_px[0]))
    y = int(round(g.bleed_off_px[1]))
    return im.crop((x, y, x + g.trim_px[0], y + g.trim_px[1]))


def tts_cell_px(g: CardGeom, cols: int = TTS_COLS,
                rows: int = TTS_ROWS) -> tuple[int, int]:
    """La taille d'une case, DÉRIVÉE du plafond publié — jamais codée en dur.

    On divise 4096 par le nombre de colonnes (division entière : dépasser
    d'un pixel fait rejeter la texture), puis la hauteur suit l'aspect de la
    rogne. Si la planche dépassait en hauteur, on réduit par la hauteur.
    """
    cw = TTS_MAX_PX // max(1, int(cols))
    ch = int(round(cw * g.trim_px[1] / float(g.trim_px[0])))
    if ch * rows > TTS_MAX_PX:
        ch = TTS_MAX_PX // max(1, int(rows))
        cw = int(round(ch * g.trim_px[0] / float(g.trim_px[1])))
    return (cw, ch)


def _collage(images: list[Image.Image], g: CardGeom, cols: int, rows: int,
             cw: int, ch: int) -> Image.Image:
    """Une planche. Les cases vides restent transparentes : TTS ne les tire
    pas (le nombre de cartes vient de `DeckIDs`), et un noir plein se verrait
    si l'utilisateur ouvrait le fichier."""
    n = len(images)
    used_rows = max(1, -(-n // cols))
    sheet = Image.new("RGBA", (cw * cols, ch * min(rows, used_rows)),
                      (0, 0, 0, 0))
    for k, im in enumerate(images):
        r, c = divmod(k, cols)
        tile = trim_crop(im, g).convert("RGBA").resize(
            (cw, ch), Image.LANCZOS)
        sheet.paste(tile, (c * cw, r * ch))
    return sheet


def build_tts(nom: str, g: CardGeom, fronts: list[Image.Image],
              backs: list[Image.Image], cols: int = TTS_COLS,
              rows: int = TTS_ROWS) -> tuple[bytes, int]:
    """Le ZIP : N planches recto, N planches verso, l'objet sauvegardé, le
    manifeste. -> (octets, nombre de planches)."""
    slug = deck_slug(nom)
    cw, ch = tts_cell_px(g, cols, rows)
    par = max(1, int(cols) * int(rows))
    n = len(fronts)
    planches = max(1, -(-n // par))
    fichiers, images = [], []
    for k in range(planches):
        lot_f = fronts[k * par:(k + 1) * par]
        lot_b = backs[k * par:(k + 1) * par] if backs else []
        for side, lot in (("recto", lot_f), ("verso", lot_b)):
            if not lot:
                continue
            im = _collage(lot, g, cols, rows, cw, ch)
            buf = io.BytesIO()
            im.save(buf, "PNG")
            data = buf.getvalue()
            fn = f"{slug}_{side}_{k + 1}.png"
            images.append((f"tts/{fn}", data))
            fichiers.append({"nom": fn, "side": side, "planche": k + 1,
                             "px": list(im.size), "octets": len(data),
                             "sha256": hashlib.sha256(data).hexdigest()})

    # ── l'objet sauvegardé ────────────────────────────────────────────────
    # CardID = 100 * id_de_deck + index : CONVENTION lue dans des objets
    # sauvegardés, absente de la base de connaissances. Elle est dite.
    deck_ids, contenus, custom = [], [], {}
    for k in range(planches):
        did_tts = k + 1
        custom[str(did_tts)] = {
            "FaceURL": f"{slug}_recto_{k + 1}.png",
            "BackURL": (f"{slug}_verso_{k + 1}.png" if backs
                        else f"{slug}_recto_{k + 1}.png"),
            "NumWidth": int(cols), "NumHeight": int(rows),
            "BackIsHidden": True, "UniqueBack": bool(backs), "Type": 0,
        }
        debut, fin = k * par, min(n, (k + 1) * par)
        for j in range(fin - debut):
            cid = 100 * did_tts + j
            deck_ids.append(cid)
            contenus.append({
                "Name": "Card", "CardID": cid, "Nickname": "",
                "Transform": {"posX": 0.0, "posY": 0.0, "posZ": 0.0,
                              "rotX": 0.0, "rotY": 180.0, "rotZ": 180.0,
                              "scaleX": 1.0, "scaleY": 1.0, "scaleZ": 1.0},
                "CustomDeck": {str(did_tts): custom[str(did_tts)]},
            })
    objet = {"ObjectStates": [{
        "Name": "DeckCustom", "Nickname": str(nom or "Jeu"),
        "Description": "Écrit par Deepotus Card Forge",
        "Transform": {"posX": 0.0, "posY": 1.0, "posZ": 0.0,
                      "rotX": 0.0, "rotY": 180.0, "rotZ": 180.0,
                      "scaleX": 1.0, "scaleY": 1.0, "scaleZ": 1.0},
        "DeckIDs": deck_ids, "CustomDeck": custom,
        "ContainedObjects": contenus,
    }]}

    manifeste = {
        "cible": "tts", "jeu": slug, "cartes": n, "planches": planches,
        "grille": [int(cols), int(rows)],
        "grille_source": "convention de gabarit — la base de connaissances "
                         "publie le champ « how many cards horizontally and "
                         "vertically », SANS maximum",
        "plafond_px": TTS_MAX_PX,
        "carte_px": [cw, ch], "source": "trim",
        "trim_px": list(g.trim_px), "canvas_px": list(g.canvas_px),
        "publie": TTS_PUBLIE,
        "a_faire": "Tabletop Simulator lit FaceURL et BackURL comme des URL "
                   "(ou des chemins locaux selon la version) : déposez les "
                   "PNG à un endroit atteignable et remplacez les deux "
                   "champs. Le fichier ne se pose pas tout seul.",
        "fichiers": fichiers,
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("tts/manifeste.json",
                   json.dumps(manifeste, ensure_ascii=False, indent=1))
        z.writestr(f"tts/{slug}.json",
                   json.dumps(objet, ensure_ascii=False, indent=1))
        for nom_f, data in images:
            z.writestr(zipfile.ZipInfo(nom_f), data,
                       compress_type=zipfile.ZIP_STORED)
    return buf.getvalue(), planches
```

- [ ] **Step 4 : la route dans `edition.py`**

```python
async def _lire(files: list[UploadFile], g, label: str) -> list:
    """Les bitmaps téléversés, contrôlés à la toile. Le verrou de « un seul
    moteur de rendu » vaut ici comme en P7 : un bitmap hors `canvas_px` est
    refusé, avec les deux chiffres."""
    from PIL import Image as PILImage
    out = []
    for i, f in enumerate(files or []):
        data = await f.read()
        try:
            im = PILImage.open(io.BytesIO(data))
            im.load()
        except Exception:
            raise HTTPException(400, f"{label} {i + 1} illisible")
        if tuple(im.size) != tuple(g.canvas_px):
            raise HTTPException(
                400, f"{label} {i + 1} fait {im.size[0]}x{im.size[1]} px ; "
                     f"la toile de ce format vaut {g.canvas_px[0]}x"
                     f"{g.canvas_px[1]} px. Les cartes doivent venir du "
                     f"moteur de rendu unique.")
        out.append(im.convert("RGBA"))
    return out


def _geom_du_deck(doc: dict):
    f = doc.get("format") or {}
    try:
        return contract.geom(f.get("fmt") or contract.DEFAULT_FMT,
                             int(f.get("dpi") or contract.DEFAULT_DPI),
                             f.get("bleed_mm"), f.get("safe_mm"),
                             float(f.get("corner_mm")
                                   or contract.DEFAULT_CORNER_MM))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/tts")
async def post_tts(did: str, spec: str = Form("{}"),
                   fronts: list[UploadFile] = File(default=[]),
                   backs: list[UploadFile] = File(default=[])):
    """Le deck en collage + l'objet sauvegardé de Tabletop Simulator."""
    doc = _deck(did)
    body = _json_form(spec)
    if not fronts:
        raise HTTPException(400, "Aucune carte reçue : le navigateur doit "
                                 "rendre les cartes avant l'export")
    g = _geom_du_deck(doc)
    try:
        cols = max(1, min(20, int(body.get("cols") or VTT.TTS_COLS)))
        rows = max(1, min(20, int(body.get("rows") or VTT.TTS_ROWS)))
    except (TypeError, ValueError, OverflowError):
        raise HTTPException(400, "cols et rows doivent être des entiers")
    f_im = await _lire(fronts, g, "Le recto")
    b_im = await _lire(backs, g, "Le verso")
    nom = str(body.get("nom") or doc.get("name") or "Jeu")

    def work():
        return VTT.build_tts(nom, g, f_im, b_im, cols, rows)
    try:
        out, planches = await asyncio.to_thread(work)
    except Exception as e:
        logger.exception("cards/edition: export TTS impossible")
        raise HTTPException(500, f"Export impossible: {e}")
    cw, ch = VTT.tts_cell_px(g, cols, rows)
    return Response(content=out, media_type="application/zip", headers={
        "Content-Disposition": 'attachment; filename="tts.zip"',
        "X-CF-Sheets": str(planches),
        "X-CF-Cards": str(len(f_im)),
        "X-CF-Grid": f"{cols}x{rows}",
        "X-CF-Cell-Px": f"{cw}x{ch}",
        "X-CF-Max-Px": str(VTT.TTS_MAX_PX),
    })
```

- [ ] **Step 5 : relancer**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_edition.py
```

Attendu : `10 passed`.

- [ ] **Step 6 : commit proposé**

```bash
git add backend/app/services/cards/edition_vtt.py backend/app/services/cards/edition.py backend/tests/test_cards_edition.py
git commit -m 'cartes : le deck part sur Tabletop Simulator, collage et objet sauvegarde' -m 'La case n  est pas codée en dur : elle se DÉRIVE du seul chiffre publié — 4096 px de large pour un Custom Deck rectangulaire — divisé par le nombre de colonnes, ce qui donne 409 x 558 pour un poker et une planche de 4090 x 3906, sous le plafond sur les deux axes. Le collage prend la ROGNE et non la toile : une table virtuelle ne coupe rien, le fond perdu se verrait sur le tapis. Le manifeste sépare ce qui est publié de ce qui est convention (la grille 10 x 7, le CardID à 100), et dit que FaceURL ne se remplit pas tout seul.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Task 7 : Tabletopia — une image par face, et le manifeste qui dit pourquoi

**Files:**
- Modify: `backend/app/services/cards/edition_vtt.py`
- Modify: `backend/app/services/cards/edition.py` (route `/tabletopia`)
- Modify: `backend/tests/test_cards_edition.py`

**Coût de patch** : aucun.

- [ ] **Step 1 : écrire le banc qui échoue**

```python
# ─────────────────────── T7 : Tabletopia ────────────────────────────────────
def test_tabletopia_recoit_un_fichier_par_face_et_jamais_un_collage():
    r = asyncio.run(_vtt("tabletopia", 4))
    assert r.status_code == 200, r.text
    z = zipfile.ZipFile(io.BytesIO(r.content))
    pngs = sorted(n for n in z.namelist() if n.endswith(".png"))
    assert len(pngs) == 8, pngs
    assert pngs[0] == "tabletopia/jeu-de-table_01_recto.png", pngs[0]
    assert "tabletopia/jeu-de-table_01_verso.png" in pngs


def test_tabletopia_tient_sous_2000_px_et_recto_verso_font_la_meme_taille():
    r = asyncio.run(_vtt("tabletopia", 2))
    z = zipfile.ZipFile(io.BytesIO(r.content))
    tailles = {n: _ihdr(z.read(n))
               for n in z.namelist() if n.endswith(".png")}
    for n, (w, h) in tailles.items():
        assert w <= 2000 and h <= 2000, (n, w, h)
    assert len(set(tailles.values())) == 1, tailles
    # poker_us : rogne 750 x 1050 -> plafond sur la HAUTEUR, 1428 x 2000
    assert set(tailles.values()) == {(1428, 2000)}, tailles


def test_le_manifeste_tabletopia_dit_pourquoi_il_ny_a_pas_de_collage():
    r = asyncio.run(_vtt("tabletopia", 2))
    z = zipfile.ZipFile(io.BytesIO(r.content))
    man = json.loads(z.read("tabletopia/manifeste.json").decode("utf-8"))
    assert man["collage"] is False
    assert "fichiers séparés" in man["pourquoi"].lower() \
        or "fichiers separes" in man["pourquoi"].lower()
    assert "help.tabletopia.com" in man["publie"]
    assert man["plafond_px"] == 2000
    assert man["epaisseur_mm"] == 0.2
    # le poids visé, dit pour que l'utilisateur sache pourquoi c'est du JPEG
    assert "1 à 2 Mo" in man["poids"] or "1-2" in man["poids"]


def test_un_deck_sans_verso_ne_fabrique_pas_de_verso_vide():
    """Tabletopia exige recto et verso de MÊME taille ; il n'exige pas qu'on
    invente un verso. Sans verso reçu, le paquet n'en contient aucun et le
    manifeste le dit."""
    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Sans dos"})
            did = r.json()["deck"]["id"]
            g = CT.geom("poker_us", 300)
            return await c.post(
                f"/api/cards/{did}/edition/tabletopia", data={"spec": "{}"},
                files=[("fronts", ("f.png", _png(*g.canvas_px), "image/png"))],
                timeout=120.0)
    r = asyncio.run(go())
    z = zipfile.ZipFile(io.BytesIO(r.content))
    assert not [n for n in z.namelist() if "_verso" in n], z.namelist()
    man = json.loads(z.read("tabletopia/manifeste.json").decode("utf-8"))
    assert man["verso"] == 0
```

- [ ] **Step 2 : lancer, vérifier l'échec** (404 sur `/edition/tabletopia`).

- [ ] **Step 3 : compléter `edition_vtt.py`**

```python
def tabletopia_px(g: CardGeom) -> tuple[int, int]:
    """La rogne, ramenée sous le plafond publié (2000 px), en gardant l'aspect.
    On ne grossit JAMAIS : une carte plus petite que le plafond part telle
    quelle — étirer inventerait des pixels."""
    tw, th = g.trim_px
    f = min(1.0, TABLETOPIA_MAX_PX / float(max(tw, th)))
    return (max(1, int(round(tw * f))), max(1, int(round(th * f))))


def build_tabletopia(nom: str, g: CardGeom, fronts: list[Image.Image],
                     backs: list[Image.Image]) -> bytes:
    """Le paquet Tabletopia : UN FICHIER PAR FACE.

    Pas de collage, et c'est mesuré, pas supposé : la documentation
    (03/09/2026) demande « front and back images » dans des fichiers séparés,
    de même taille, 2000 x 2000 px au plus. Elle ne publie aucune grille.
    """
    slug = deck_slug(nom)
    w, h = tabletopia_px(g)
    n = len(fronts)
    largeur = max(2, len(str(max(1, n))))
    fichiers, sorties = [], []
    for side, lot in (("recto", fronts), ("verso", backs)):
        for i, im in enumerate(lot or []):
            tile = trim_crop(im, g).convert("RGBA").resize((w, h), Image.LANCZOS)
            buf = io.BytesIO()
            tile.save(buf, "PNG")
            data = buf.getvalue()
            fn = "%s_%0*d_%s.png" % (slug, largeur, i + 1, side)
            sorties.append((f"tabletopia/{fn}", data))
            fichiers.append({"nom": fn, "carte": i + 1, "side": side,
                             "px": [w, h], "octets": len(data),
                             "sha256": hashlib.sha256(data).hexdigest()})
    manifeste = {
        "cible": "tabletopia", "jeu": slug,
        "recto": len(fronts), "verso": len(backs or []),
        "collage": False,
        "pourquoi": "La documentation de Tabletopia demande recto et verso "
                    "dans des fichiers séparés, de même taille en pixels ; "
                    "elle ne publie AUCUNE grille de collage. Le « 10 x 7 » "
                    "appartient à Tabletop Simulator, pas ici.",
        "plafond_px": TABLETOPIA_MAX_PX, "carte_px": [w, h], "source": "trim",
        "epaisseur_mm": 0.2,
        "taille_max_mm": 1600,
        "poids": "Tabletopia annonce 3 à 10 Mo au maximum par objet et "
                 "conseille 1 à 2 Mo : au-delà, passez en JPEG dans la "
                 "pièce 07 avant de réexporter.",
        "publie": TTPIA_PUBLIE,
        "fichiers": fichiers,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("tabletopia/manifeste.json",
                   json.dumps(manifeste, ensure_ascii=False, indent=1))
        for nom_f, data in sorties:
            z.writestr(zipfile.ZipInfo(nom_f), data,
                       compress_type=zipfile.ZIP_STORED)
    return buf.getvalue()
```

Ajouter `"tabletopia_px"` et `"build_tabletopia"` à `__all__`.

- [ ] **Step 4 : la route**

```python
@router.post("/tabletopia")
async def post_tabletopia(did: str, spec: str = Form("{}"),
                          fronts: list[UploadFile] = File(default=[]),
                          backs: list[UploadFile] = File(default=[])):
    """Le deck pour Tabletopia : une image par face, jamais un collage."""
    doc = _deck(did)
    body = _json_form(spec)
    if not fronts:
        raise HTTPException(400, "Aucune carte reçue : le navigateur doit "
                                 "rendre les cartes avant l'export")
    g = _geom_du_deck(doc)
    f_im = await _lire(fronts, g, "Le recto")
    b_im = await _lire(backs, g, "Le verso")
    nom = str(body.get("nom") or doc.get("name") or "Jeu")

    def work():
        return VTT.build_tabletopia(nom, g, f_im, b_im)
    try:
        out = await asyncio.to_thread(work)
    except Exception as e:
        logger.exception("cards/edition: export Tabletopia impossible")
        raise HTTPException(500, f"Export impossible: {e}")
    w, h = VTT.tabletopia_px(g)
    return Response(content=out, media_type="application/zip", headers={
        "Content-Disposition": 'attachment; filename="tabletopia.zip"',
        "X-CF-Sheets": "0",
        "X-CF-Cards": str(len(f_im)),
        "X-CF-Cell-Px": f"{w}x{h}",
        "X-CF-Max-Px": str(VTT.TABLETOPIA_MAX_PX),
    })
```

- [ ] **Step 5 : relancer**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_edition.py
```

Attendu : `14 passed`.

- [ ] **Step 6 : commit proposé**

```bash
git add backend/app/services/cards/edition_vtt.py backend/app/services/cards/edition.py backend/tests/test_cards_edition.py
git commit -m 'cartes : Tabletopia recoit un fichier par face, pas un collage' -m 'R10d écrivait « collage 10 x 7 » pour les deux tables ; la documentation Tabletopia relue le 03/09 dit le contraire — recto et verso dans des fichiers SÉPARÉS de même taille, 2000 x 2000 px au plus. Le manifeste porte la raison et la source datée, pour que personne ne « corrige » ce paquet en collage six mois plus tard. Le plafond est appliqué sur la plus grande dimension et jamais dépassé vers le haut : on ne grossit pas une carte, cela inventerait des pixels.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Task 8 : Dos variables — l'image de dos par carte, et la mire d'alignement

**Ce qui existe déjà, mesuré le 03/09/2026 — à ne PAS réécrire :**

- Le **miroir verso est livré et mesuré** : `print.py:1184 cells_for_page` inverse la
  colonne (pli long) ou la ligne (pli court), `print.py:1206 origin_for` pose
  l'origine miroir **même hors centrage** (le commentaire cite les 708,54 px =
  59,99 mm du défaut corrigé), `print.py:1258 mirror_px` / `1284 mirror_um` mesurent
  l'écart case par case, `print.py:2971 mirror_um_bytes` le relit **dans les octets**,
  l'en-tête `X-CF-Mirror-Um` le publie et `test_cards_print.py` le verrouille
  (critère 9). **Aucune ligne de miroir n'est à écrire.**
- La **colonne « dos » du CSV existe** : `data.py:109 RESERVED = {"art", "back",
  "id"}`, libellée « Dos (card.back) » (`data.py:110`), proposée par le mappeur
  (`mod-data.js:51`).

**Ce qui manque, et c'est tout ce que fait cette tâche :**

1. `card.back` est lu par **deux pièces dans deux espaces de noms** — `mod-frame.js:3190`
   y cherche un **motif du catalogue** (`byId(BACKS, card.back)`), `mod-face.js:2063`
   y cherche une **illustration**. Aucune ne le dit à l'autre, et une valeur qui n'est
   ni l'un ni l'autre **retombe silencieusement** sur le dos commun. La tâche nomme le
   partage et fait dire à l'écran, par carte, **d'où vient le dos qui sera imprimé**.
2. Une **mire d'alignement recto-verso imprimée** : une page à imprimer en recto-verso,
   à regarder à contre-jour, qui donne le décalage réel de l'imprimante en millimètres.
   `mirror_um` mesure le **fichier** ; la mire mesure la **machine**.

**Files:**
- Modify: `backend/app/services/cards/data.py:1592-1636` (après `deck_table`)
- Modify: `backend/app/services/cards/data.py:2243` (route `/dos`)
- Modify: `backend/app/services/cards/print.py:4456` (route `/mire`)
- Modify: `frontend/cardforge/js/mod-data.js` (origine du dos, par carte)
- Create: `backend/tests/test_cards_dos.py`

**Coût de patch** : aucun côté bundle. Aucun sidecar neuf.

- [ ] **Step 1 : écrire le banc qui échoue**

Créer `backend/tests/test_cards_dos.py` :

```python
# -*- coding: utf-8 -*-
"""Card Forge — P3 « Dos variables ». CE QUI EXISTE N'EST PAS RÉÉCRIT.

Le miroir verso est livré et mesuré (print.py:1206 origin_for, 1258 mirror_px,
2971 mirror_um_bytes) : ce banc le CONSTATE en une assertion et passe à la
suite. Ce qu'il verrouille vraiment :

  1. `card.back` est lu par DEUX pièces — mod-frame.js y cherche un motif du
     catalogue, mod-face.js une illustration. Le backend doit dire, par carte,
     laquelle des deux servira, au lieu de laisser la valeur retomber en
     silence sur le dos commun.
  2. La mire : `mirror_um` mesure le FICHIER, la mire mesure la MACHINE. Deux
     questions différentes, et seule la seconde manquait.

Run : cd backend ; python tests/test_cards_dos.py
"""
import asyncio
import io
import os
import pathlib
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest                                                    # noqa: E402
from httpx import ASGITransport, AsyncClient                     # noqa: E402
from pypdf import PdfReader                                      # noqa: E402

from app.services.cards import data as DA                        # noqa: E402
from app.services.cards import print as PR                       # noqa: E402


def test_le_miroir_verso_existe_deja_et_reste_a_zero_en_impose_centre():
    """CONSTAT, pas travail neuf : la mécanique du miroir est livrée."""
    p = PR.build_plan({"fmt": "poker_us", "dpi": 300, "sheet": "a4",
                       "margin_mm": 10, "gutter_mm": 4, "center": True,
                       "duplex": True, "flip": "long"}, 6)
    assert PR.mirror_um(p) == 0.0, PR.mirror_um(p)


def test_l_origine_du_dos_est_dite_par_carte_et_jamais_devinee():
    """Trois origines possibles, et la quatrième — « rien ne correspond » —
    est la seule qui compte : c'est elle qui retombait en silence."""
    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Dos"})
            did = r.json()["deck"]["id"]
            return await c.post(f"/api/cards/{did}/data/dos", json={
                "columns": ["nom", "dos", "qty"],
                "rows": [["Colosse", "quadrillage", "2"],
                         ["Oracle", "mon_dos.png", "1"],
                         ["Rebut", "", "3"],
                         ["Echo", "inconnu_xyz", "1"]],
                "qty_col": "qty",
                "motifs": ["quadrillage", "toile", "vagues"],
                "images": ["mon_dos.png", "autre.png"],
            })
    r = asyncio.run(go())
    assert r.status_code == 200, r.text
    j = r.json()
    par = {d["valeur"]: d for d in j["dos"]}
    assert par["quadrillage"]["origine"] == "motif"
    assert par["mon_dos.png"]["origine"] == "image"
    assert par[""]["origine"] == "commun"
    assert par["inconnu_xyz"]["origine"] == "introuvable"
    # LE MOT QUI MANQUAIT : une valeur qui ne correspond à rien se DIT
    assert "inconnu_xyz" in j["avertissements"][0]
    assert "DOS COMMUN" in j["avertissements"][0]
    # les compteurs suivent les QUANTITÉS, pas les lignes
    assert j["total_cartes"] == 7
    assert par["quadrillage"]["cartes"] == 2


def test_deck_table_exporte_la_colonne_dos():
    cols, rows = DA.deck_table(
        [{"id": "c1", "row": 0, "copy": 1, "copies": 1, "fields": {},
          "back": "quadrillage"},
         {"id": "c2", "row": 1, "copy": 1, "copies": 1, "fields": {},
          "back": ""}], None)
    assert "dos" in cols
    i = cols.index("dos")
    assert rows[0][i] == "quadrillage"
    assert rows[1][i] == ""


def test_la_mire_est_une_page_recto_verso_avec_une_graduation_lisible():
    """La mire mesure la MACHINE : deux croix superposables, un vernier au
    demi-millimètre, et la phrase qui dit comment le lire."""
    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Mire"})
            did = r.json()["deck"]["id"]
            return await c.get(f"/api/cards/{did}/print/mire?sheet=a4")
    r = asyncio.run(go())
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    rd = PdfReader(io.BytesIO(r.content))
    assert len(rd.pages) == 2, len(rd.pages)
    box = [round(float(v), 2) for v in rd.pages[0].mediabox]
    assert box == [0.0, 0.0, 595.2, 841.92], box
    contenu = b"".join(p.get_contents().get_data() for p in rd.pages)
    # DES TRAITS, pas une image : une mire rééchantillonnée mentirait d'un
    # demi-pixel, l'ordre de grandeur qu'elle mesure
    assert contenu.count(b" l S") >= 80, contenu.count(b" l S")
    assert b"/Image" not in contenu
    assert r.headers["X-CF-Mire-Pas-Mm"] == "0,5"
    assert r.headers["X-CF-Mire-Etendue-Mm"] == "10"


def test_l_ecran_dit_d_ou_vient_le_dos_de_chaque_carte():
    js = (pathlib.Path(__file__).resolve().parents[2] / "frontend" / "cardforge"
          / "js" / "mod-data.js").read_text(encoding="utf-8")
    assert 'M.api.post("dos' in js
    for phrase in ("motif du catalogue", "illustration du verso",
                   "dos commun", "introuvable", "pièce 02", "pièce 01"):
        assert phrase in js, phrase


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
```

- [ ] **Step 2 : lancer, vérifier l'échec**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_dos.py
```

Attendu : 4 échecs. Le premier — le constat du miroir — **passe déjà** : c'est le
but, il prouve qu'il n'y a rien à écrire là.

- [ ] **Step 3 : l'origine du dos, dans `data.py`**

Ajouter après `deck_table` (`data.py:1636`) :

```python
# ── D'OÙ VIENT LE DOS D'UNE CARTE (P3) ──────────────────────────────────────
# `card.back` est lu par DEUX pièces, dans deux espaces de noms distincts :
#   * P2 (frame) y cherche un MOTIF du catalogue — mod-frame.js:3190,
#     `byId(BACKS, card.back)`, seulement si « dos commun » est décoché ;
#   * P1 (face) y cherche une ILLUSTRATION du verso — mod-face.js:2063.
# Aucune ne prévient l'autre, et une valeur qui n'est NI un motif NI une image
# retombe sur le dos commun SANS UN MOT. C'est ce silence qu'on retire : la
# fonction ne décide rien, elle DIT ce qui se passera.
DOS_ORIGINES = ("motif", "image", "commun", "introuvable")


def dos_origine(valeur: Any, motifs: Any, images: Any) -> str:
    """L'origine du dos pour UNE valeur de la colonne. Jamais d'exception."""
    v = str(valeur or "").strip()
    if not v:
        return "commun"
    if v in set(str(m) for m in (motifs or ())):
        return "motif"
    if v in set(str(i) for i in (images or ())):
        return "image"
    return "introuvable"


def dos_report(columns: list, rows: list, back_col: Any = None,
               qty_col: Any = None, motifs: Any = None,
               images: Any = None) -> dict:
    """Le compte rendu des dos, PAR VALEUR, en cartes (quantités appliquées).

    Le nombre de CARTES, pas de lignes : « 2 cartes en quadrillage » est la
    phrase que l'utilisateur vérifie contre sa planche ; « 1 ligne » ne veut
    plus rien dire une fois les quantités résolues.
    """
    cols = [str(c) for c in (columns or ())]
    bc = str(back_col or "").strip() or next(
        (c for c in cols if c.strip().lower() in ("dos", "back")), "")
    if bc and bc not in cols:
        raise ValueError(f"Colonne de dos inconnue: {bc!r}")
    ib = cols.index(bc) if bc else -1
    iq = cols.index(str(qty_col)) if qty_col and str(qty_col) in cols else -1
    par: dict[str, dict] = {}
    total = 0
    for r in (rows or ()):
        v = str(r[ib]).strip() if 0 <= ib < len(r) else ""
        q = read_qty(r[iq]) if 0 <= iq < len(r) else 1
        total += q
        e = par.setdefault(v, {"valeur": v, "lignes": 0, "cartes": 0,
                               "origine": dos_origine(v, motifs, images)})
        e["lignes"] += 1
        e["cartes"] += q
    avert = []
    perdues = [e for e in par.values() if e["origine"] == "introuvable"]
    if perdues:
        noms = ", ".join(sorted(e["valeur"] for e in perdues)[:8])
        n = sum(e["cartes"] for e in perdues)
        avert.append(
            f"{n} carte(s) portent un dos qui n'est ni un motif du catalogue "
            f"ni une illustration connue ({noms}) : elles sortiront avec le "
            f"DOS COMMUN. Corrigez la colonne, ou importez l'image.")
    if not bc:
        avert.append("Aucune colonne « dos » : toutes les cartes partagent le "
                     "dos commun de la pièce 02.")
    return {"colonne": bc, "total_cartes": total,
            "dos": sorted(par.values(), key=lambda e: -e["cartes"]),
            "avertissements": avert}
```

La route, après `post_check` (`data.py:2243`) :

```python
@router.post("/dos")
async def post_dos(did: str, body: Any = Body(default=None)):
    """L'origine du dos, carte par carte — ce qui SERA imprimé, pas ce qu'on
    espère. `motifs` vient du catalogue de la pièce 02, `images` de la
    bibliothèque d'illustrations : l'écran les fournit, le backend juge."""
    _guard(did)
    b = _obj(body)
    cols, rows = _table_of(b)
    try:
        return dos_report(cols, rows, b.get("back_col"), b.get("qty_col"),
                          b.get("motifs"), b.get("images"))
    except ValueError as e:
        raise HTTPException(400, str(e))
```

- [ ] **Step 4 : la mire, dans `print.py`**

Ajouter après `get_foil_mask` (`print.py:4456`) :

```python
MIRE_PAS_MM = 0.5          # graduation : le demi-millimètre se lit à l'œil nu
MIRE_ETENDUE_MM = 10       # de -10 à +10 mm ; au-delà, c'est un bourrage


def mire_pdf(sheet: str, dpi: int = 300) -> bytes:
    """LA MIRE D'ALIGNEMENT RECTO-VERSO — deux pages à imprimer recto-verso et
    à regarder à contre-jour.

    `mirror_um` mesure le FICHIER (l'imposition est-elle bien miroir ?). Cette
    mire mesure la MACHINE (l'imprimante retourne-t-elle la feuille droit ?).
    Deux questions différentes ; seule la seconde manquait, et c'est elle qui
    décide si l'on peut couper une carte à 0,3 mm près.

    TOUT EST VECTORIEL, aucun raster : une mire rééchantillonnée mentirait
    d'un demi-pixel — exactement l'ordre de grandeur qu'on lui demande de
    mesurer.
    """
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, NameObject
    sw, sh = sheet_px(sheet, dpi)
    W, H = px2pt(sw, dpi), px2pt(sh, dpi)
    cx, cy = W / 2.0, H / 2.0
    pas = mm2pt(MIRE_PAS_MM)
    etendue = mm2pt(MIRE_ETENDUE_MM)

    def seg(x0, y0, x1, y1) -> bytes:
        return ("%s %s m %s %s l S"
                % (_pdf_num(x0), _pdf_num(y0),
                   _pdf_num(x1), _pdf_num(y1))).encode("ascii")

    def page_ops(recto: bool) -> bytes:
        ops = [b"0 G", ("%s w" % _pdf_num(mm2pt(0.12))).encode("ascii")]
        # LA CROIX CENTRALE, identique des deux côtés : superposées à
        # contre-jour, elles donnent le décalage d'un coup d'oeil.
        ops.append(seg(cx - etendue, cy, cx + etendue, cy))
        ops.append(seg(cx, cy - etendue, cx, cy + etendue))
        # LA GRADUATION : décalée d'un demi-pas au verso, elle fait VERNIER —
        # le trait qui coïncide donne le décalage, sans règle ni loupe.
        n = int(MIRE_ETENDUE_MM / MIRE_PAS_MM)
        biais = 0.0 if recto else pas / 2.0
        for k in range(-n, n + 1):
            h = mm2pt(3.0 if k % 2 == 0 else 1.6)
            x = cx + k * pas + biais
            ops.append(seg(x, cy - h, x, cy + h))
            y = cy + k * pas + biais
            ops.append(seg(cx - h, y, cx + h, y))
        mot = ("MIRE RECTO - a contre-jour, lisez le trait qui coincide"
               if recto else
               "MIRE VERSO - un trait = 0,5 mm de decalage")
        ops.append(text_paths(slug_chars(mot), mm2pt(12.0), H - mm2pt(14.0),
                              mm2pt(3.2)))
        return b"\n".join(ops)

    w = PdfWriter()
    w.pdf_header = "%PDF-1.4"
    for recto in (True, False):
        page = w.add_blank_page(width=W, height=H)
        st = DecodedStreamObject()
        st.set_data(page_ops(recto))
        page[NameObject("/Contents")] = w._add_object(st)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


@router.get("/mire")
async def get_mire(did: str, sheet: str = "a4", dpi: int = 300):
    """La mire d'alignement, en PDF. À imprimer EN RECTO-VERSO sur la vraie
    imprimante, avec le vrai papier : c'est la machine qu'on mesure."""
    _deck(did)
    try:
        out = await asyncio.to_thread(mire_pdf, sheet, int(dpi))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("cards/print: mire impossible")
        raise HTTPException(500, f"Mire impossible: {e}")
    return Response(content=out, media_type="application/pdf", headers={
        "Content-Disposition": 'attachment; filename="mire_alignement.pdf"',
        "X-CF-Mire-Pas-Mm": _fm(MIRE_PAS_MM, 1),
        "X-CF-Mire-Etendue-Mm": str(MIRE_ETENDUE_MM),
    })
```

> `text_paths` (`print.py:469`) rend déjà des chemins vectoriels et `slug_chars`
> (456) réduit la chaîne aux glyphes que la fonte de trait connaît — d'où
> l'absence d'accents dans les deux phrases. On ne réinvente ni l'un ni l'autre.
> `_fm(0.5, 1)` rend « 0,5 » (virgule française) : c'est ce que le banc attend.

- [ ] **Step 5 : l'écran dit l'origine (`mod-data.js`)**

```js
  /* ══ D'OÙ VIENT LE DOS DE CHAQUE CARTE (P3) ══════════════════════════════
     `card.back` a DEUX lecteurs : la piece 02 y cherche un motif du
     catalogue, la piece 01 une illustration du verso. Une valeur qui n'est ni
     l'un ni l'autre retombait sur le dos commun SANS UN MOT. On le dit. */
  const DOS_MOT = {
    motif: "motif du catalogue (pièce 02)",
    image: "illustration du verso (pièce 01)",
    commun: "dos commun (aucune valeur dans la colonne)",
    introuvable: "introuvable — la carte sortira avec le dos commun",
  };

  async function paintDos() {
    const box = HOST.querySelector("#cf-data-dos");
    if (!box) return;
    const d = CF.doc().data || {};
    if (!d.columns || !d.columns.length) { box.innerHTML = ""; return; }
    try {
      const r = await M.api.post("dos", {
        columns: d.columns, rows: d.rows, qty_col: d.qty_col,
        motifs: CF.get("frame.backs_ids", []),
        images: CF.get("face.images", []),
      });
      box.innerHTML =
        (r.avertissements || []).map((a) =>
          '<p class="cf-data-avert">' + esc(a) + "</p>").join("")
        + '<table class="cf-data-dostab"><tbody>'
        + (r.dos || []).map((e) =>
          "<tr><td>" + esc(e.valeur || "—") + "</td><td>" + e.cartes
          + " carte(s)</td><td>" + esc(DOS_MOT[e.origine] || e.origine)
          + "</td></tr>").join("")
        + "</tbody></table>";
    } catch (e) {
      if (!(e && e.missing)) console.warn("cardforge/data: dos", e);
    }
  }
```

Ajouter `<div id="cf-data-dos" class="cf-data-dos"></div>` à la coquille du
panneau, appeler `paintDos()` après chaque `rebuild()`, styler sous `.cf-data`.

- [ ] **Step 6 : relancer les trois bancs concernés**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_dos.py
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_data.py
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_print.py
```

Attendu : `5 passed` pour les dos ; les deux bancs anciens verts, inchangés.

- [ ] **Step 7 : commit proposé**

```bash
git add backend/app/services/cards/data.py backend/app/services/cards/print.py frontend/cardforge/js/mod-data.js frontend/cardforge/css/mod-data.css backend/tests/test_cards_dos.py
git commit -m 'cartes : le dos par carte dit son origine, et la mire mesure la machine' -m 'Le miroir verso était déjà livré ET mesuré (origin_for, mirror_px, mirror_um_bytes, en-tête X-CF-Mirror-Um) : rien à réécrire, une assertion le constate. Ce qui manquait était plus petit et plus grave — card.back a deux lecteurs, un motif du catalogue pour la pièce 02 et une illustration pour la pièce 01, et une valeur qui n est ni l un ni l autre retombait sur le dos commun sans un mot. Le compte rendu le dit par carte, en cartes et non en lignes. La mire mesure ce que mirror_um ne peut pas voir : le retournement de l imprimante, en vernier au demi-millimètre, tout en traits vectoriels — une mire rééchantillonnée mentirait de l ordre de grandeur qu elle mesure.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Task 9 : Statistiques du deck — histogrammes par colonne

**Files:**
- Create: `backend/app/services/cards/data_stats.py`
- Modify: `backend/app/services/cards/data.py:2243` (route `/stats`)
- Modify: `scripts/qa/lint_cardforge.py:137` (`EXTRA_PY` + clé `"data"`)
- Create: `backend/tests/test_cards_donnees.py`

**Coût de patch** : aucun. Un sidecar de plus. `numpy` est **absent** (T1) : tout
est en Python pur — un deck plafonne à 20 000 cartes (`data.py:81 MAX_CARDS`),
trier une liste suffit.

- [ ] **Step 1 : écrire le banc qui échoue**

Créer `backend/tests/test_cards_donnees.py` avec le même en-tête que
`test_cards_dos.py` (`sys.stdout.reconfigure`, variables d'environnement,
`sys.path.insert`, `import pytest`, `httpx`), puis :

```python
from app.services.cards import data_stats as ST                  # noqa: E402

COLS = ["nom", "atk", "pv", "rarete", "qty"]
ROWS = [["Colosse", "7", "5", "rare", "3"],
        ["Oracle", "2", "3", "commune", "2"],
        ["Rebut", "9", "1", "épique", "5"],
        ["Écho", "1", "9", "commune", "4"],
        ["Vase", "", "4", "commune", "1"]]


def test_une_colonne_numerique_rend_min_max_moyenne_mediane_et_des_classes():
    r = ST.stats_table(COLS, ROWS, qty_col="qty")
    atk = [c for c in r["colonnes"] if c["nom"] == "atk"][0]
    assert atk["genre"] == "numerique"
    # LES QUANTITÉS SONT APPLIQUÉES : 3 Colosses à 7, 2 Oracles à 2…
    assert atk["n"] == 14, atk["n"]           # 3+2+5+4 ; la ligne vide exclue
    assert atk["vides"] == 1
    assert atk["min"] == 1.0 and atk["max"] == 9.0
    assert round(atk["moyenne"], 6) == round((7*3 + 2*2 + 9*5 + 1*4) / 14, 6)
    assert atk["mediane"] == 7.0
    assert sum(b["n"] for b in atk["classes"]) == 14
    assert len(atk["classes"]) == 8


def test_une_colonne_categorielle_rend_ses_valeurs_triees_par_cartes():
    r = ST.stats_table(COLS, ROWS, qty_col="qty")
    rar = [c for c in r["colonnes"] if c["nom"] == "rarete"][0]
    assert rar["genre"] == "categoriel"
    assert [(v["valeur"], v["n"]) for v in rar["valeurs"]] == \
        [("commune", 7), ("épique", 5), ("rare", 3)]
    assert rar["distinctes"] == 3


def test_la_colonne_de_quantite_nest_pas_son_propre_histogramme():
    """`qty` a servi à pondérer : la décrire en plus dirait deux fois la même
    chose, et son histogramme n'aurait aucun sens."""
    r = ST.stats_table(COLS, ROWS, qty_col="qty")
    assert "qty" not in [c["nom"] for c in r["colonnes"]]
    assert r["total_cartes"] == 15


def test_le_maximum_tombe_dans_la_derniere_classe_et_non_dehors():
    """Sans fermer la dernière classe à droite, le maximum n'appartient à
    aucun intervalle et l'histogramme perd une carte, en silence."""
    r = ST.stats_table(["x"], [["0"], ["10"]])
    x = r["colonnes"][0]
    assert sum(b["n"] for b in x["classes"]) == 2
    assert x["classes"][-1]["n"] == 1


def test_une_colonne_a_moitie_numerique_est_dite_categorielle_et_le_dit():
    r = ST.stats_table(["x"], [["1"], ["2"], ["trois"], ["4"]])
    x = r["colonnes"][0]
    assert x["genre"] == "categoriel"
    assert "75" in x["note"], x["note"]


def test_la_route_sert_les_stats_et_refuse_un_corps_mal_forme_sans_500():
    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Stats"})
            did = r.json()["deck"]["id"]
            ok = await c.post(f"/api/cards/{did}/data/stats",
                              json={"columns": COLS, "rows": ROWS,
                                    "qty_col": "qty"})
            ko = await c.post(f"/api/cards/{did}/data/stats", json=[1, 2, 3])
            return ok, ko
    ok, ko = asyncio.run(go())
    assert ok.status_code == 200, ok.text
    assert ok.json()["total_cartes"] == 15
    assert ko.status_code == 400, ko.status_code
```

- [ ] **Step 2 : lancer, vérifier l'échec**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_donnees.py
```

Attendu : `ModuleNotFoundError: app.services.cards.data_stats` à la collecte.

- [ ] **Step 3 : écrire `data_stats.py`**

```python
# -*- coding: utf-8 -*-
"""Card Forge — pièce 04, sidecar « statistiques ».

SIDECAR : aucun `router` (règle 8). Python pur — `numpy` est ABSENT du runtime
embarqué (mesuré le 03/09/2026), et un deck plafonne à 20 000 cartes
(data.MAX_CARDS) : trier une liste suffit, et reste exact sur la médiane.

LES QUANTITÉS SONT APPLIQUÉES, TOUJOURS. « 3 cartes à 7 d'attaque » n'est pas
« 1 ligne à 7 » : c'est l'histogramme du JEU qu'on regarde, pas celui du
fichier. Le dépôt tient déjà cette distinction (data.py:1477).
"""
from __future__ import annotations

from typing import Any

from .data import BLANK, _num, read_qty

__all__ = ["CLASSES", "SEUIL_NUM", "MAX_VALEURS", "colonne_stats",
           "stats_table"]

CLASSES = 8            # classes d'un histogramme numérique
SEUIL_NUM = 0.9        # au-dessous, la colonne est dite catégorielle
MAX_VALEURS = 40       # valeurs distinctes montrées d'une colonne catégorielle


def _clean(v: Any) -> str:
    return str(v if v is not None else "").replace(BLANK, "").strip()


def _mediane(tri: list[float]) -> float:
    n = len(tri)
    if not n:
        return 0.0
    m = n // 2
    return tri[m] if n % 2 else (tri[m - 1] + tri[m]) / 2.0


def colonne_stats(nom: str, valeurs: list[tuple[str, int]]) -> dict:
    """Une colonne. `valeurs` = [(texte, poids en cartes)]."""
    vides = sum(q for v, q in valeurs if not v)
    pleins = [(v, q) for v, q in valeurs if v]
    n = sum(q for _v, q in pleins)
    nums = [(_num(v), q) for v, q in pleins]
    nums = [(x, q) for x, q in nums if x is not None]
    part = (sum(q for _x, q in nums) / n) if n else 0.0
    base = {"nom": nom, "n": n, "vides": vides, "note": ""}

    if n and part >= SEUIL_NUM:
        etendu = sorted(float(x) for x, q in nums for _ in range(q))
        lo, hi = etendu[0], etendu[-1]
        larg = (hi - lo) / CLASSES if hi > lo else 1.0
        classes = []
        for k in range(CLASSES):
            a, b = lo + k * larg, lo + (k + 1) * larg
            # DERNIÈRE CLASSE FERMÉE À DROITE : sans cela le maximum tombe
            # hors de tout intervalle et l'histogramme perd une carte.
            dedans = [x for x in etendu
                      if (a <= x < b) or (k == CLASSES - 1 and x == hi)]
            classes.append({"de": round(a, 4), "a": round(b, 4),
                            "n": len(dedans)})
        base.update({
            "genre": "numerique", "min": lo, "max": hi,
            "moyenne": sum(etendu) / len(etendu), "mediane": _mediane(etendu),
            "classes": classes, "distinctes": len(set(etendu)),
        })
        if part < 1.0:
            base["note"] = ("%d valeur(s) sur %d ne sont pas des nombres et "
                            "sont exclues du calcul"
                            % (n - sum(q for _x, q in nums), n))
        return base

    par: dict[str, int] = {}
    for v, q in pleins:
        par[v] = par.get(v, 0) + q
    tri = sorted(par.items(), key=lambda kv: (-kv[1], kv[0]))
    base.update({
        "genre": "categoriel", "distinctes": len(par),
        "valeurs": [{"valeur": v, "n": q} for v, q in tri[:MAX_VALEURS]],
        "tronque": max(0, len(tri) - MAX_VALEURS),
    })
    if n and 0 < part < SEUIL_NUM:
        base["note"] = ("%d valeur(s) sur %d sont numériques (%.0f %%) : sous "
                        "%.0f %%, la colonne est traitée en catégories"
                        % (sum(q for _x, q in nums), n, part * 100,
                           SEUIL_NUM * 100))
    return base


def stats_table(columns: list, rows: list, qty_col: Any = None,
                skip: Any = None) -> dict:
    """Le deck, colonne par colonne. `qty_col` PONDÈRE et n'est pas décrite."""
    cols = [str(c) for c in (columns or ())]
    qc = str(qty_col) if qty_col and str(qty_col) in cols else ""
    iq = cols.index(qc) if qc else -1
    ecartees = {qc} | {str(s) for s in (skip or ())}
    poids = [read_qty(r[iq]) if 0 <= iq < len(r) else 1 for r in (rows or ())]
    out = []
    for i, c in enumerate(cols):
        if c in ecartees:
            continue
        vals = [(_clean(r[i]) if i < len(r) else "", poids[k])
                for k, r in enumerate(rows or ())]
        out.append(colonne_stats(c, vals))
    return {"total_cartes": sum(poids), "lignes": len(rows or ()),
            "qty_col": qc, "colonnes": out}
```

> `_num` (`data.py:536`) rend `None` pour un texte non numérique et accepte la
> virgule décimale française ; `read_qty` (914) borne la quantité à `MAX_QTY`.
> On les réutilise, on ne les récrit pas.

- [ ] **Step 4 : la route et le lint**

`data.py`, après `post_check` :

```python
@router.post("/stats")
async def post_stats(did: str, body: Any = Body(default=None)):
    """Les statistiques du deck — quantités appliquées. C'est le JEU qu'on
    décrit, pas le fichier."""
    _guard(did)
    b = _obj(body)
    cols, rows = _table_of(b)
    from . import data_stats
    try:
        return data_stats.stats_table(cols, rows, b.get("qty_col"),
                                      b.get("skip"))
    except ValueError as e:
        raise HTTPException(400, str(e))
```

`scripts/qa/lint_cardforge.py:137`, `EXTRA_PY` gagne :

```python
            # data_stats.py : histogrammes et résumés de colonne (P4).
            # Aucun router — la route vit dans data.py.
            "data": ["data_stats.py"],
```

- [ ] **Step 5 : relancer**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_donnees.py
cd ..
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" scripts/qa/lint_cardforge.py --module data
```

Attendu : `6 passed` ; lint `0`.

- [ ] **Step 6 : commit proposé**

```bash
git add backend/app/services/cards/data_stats.py backend/app/services/cards/data.py scripts/qa/lint_cardforge.py backend/tests/test_cards_donnees.py
git commit -m 'cartes : les statistiques du deck, quantites appliquees' -m 'C est le JEU qu on décrit et non le fichier : trois Colosses à 7 d attaque pèsent trois, pas un — le dépôt tenait déjà cette distinction pour « 10 cartes », l histogramme la tient aussi. numpy est absent du runtime embarqué (mesuré) : tout est en Python pur, ce que 20 000 cartes au plus autorisent. La dernière classe est fermée à droite, sinon le maximum tombe hors de tout intervalle et l histogramme perd une carte en silence ; une colonne à moitié numérique est dite catégorielle ET dit son pourcentage.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Task 10 : Grille éditable — la table se corrige dans l'app et repart en CSV

**Files:**
- Modify: `frontend/cardforge/js/mod-data.js` (grille, édition, annulation)
- Modify: `frontend/cardforge/css/mod-data.css`
- Modify: `backend/tests/test_cards_donnees.py`

**Coût de patch** : **zéro backend, zéro bundle.** `doc.data.columns` et
`doc.data.rows` (schéma déclaré, `mod-data.js:3140-3151`) tiennent déjà la table
brute ; `POST /data/build` la transforme et `POST /data/export` l'écrit
(`data.py:2274`, `write_csv` 1571). La grille n'ajoute **aucune** route.

- [ ] **Step 1 : écrire le banc-miroir qui échoue**

```python
def _js_data():
    return (pathlib.Path(__file__).resolve().parents[2] / "frontend"
            / "cardforge" / "js" / "mod-data.js").read_text(encoding="utf-8")


def test_la_grille_ecrit_dans_doc_data_et_jamais_ailleurs():
    """Règle 2 : M.patch n'écrit que sous doc.data. Une grille qui toucherait
    doc.type ou doc.face lèverait — le banc vérifie qu'elle n'essaie pas."""
    js = _js_data()
    assert 'id="cf-data-grille"' in js
    assert "function grilleEcrire" in js
    for interdit in ("M.patch({ face", "M.patch({ type", "M.patch({ print",
                     "M.patch({ frame"):
        assert interdit not in js, interdit


def test_la_grille_annule_la_derniere_edition_et_la_nomme():
    js = _js_data()
    for phrase in ('data-act="grille-annuler"', 'data-act="grille-ligne"',
                   'data-act="grille-colonne"', "Annulé : "):
        assert phrase in js, phrase


def test_editer_la_table_leve_le_drapeau_de_l_aller_retour():
    """Le dépôt compare déjà le CSV rendu aux octets importés, octet par
    octet (SRCDIRTY, mod-data.js:2997). Éditer la table DOIT lever ce
    drapeau, sinon la comparaison jurerait que deux choses différentes sont
    identiques."""
    js = _js_data()
    bloc = js.split("function grilleEcrire")[1][:2000]
    assert "SRCDIRTY = true" in bloc, bloc[:400]
```

- [ ] **Step 2 : lancer, vérifier l'échec** (3 échecs).

- [ ] **Step 3 : écrire la grille dans `mod-data.js`**

```js
  /* ══ GRILLE ÉDITABLE (P4) ════════════════════════════════════════════════
     La table brute vit deja dans doc.data.{columns,rows} — le schema declare
     ligne 3140 : la grille n'a AUCUNE route a ajouter. Elle ecrit sous
     doc.data et nulle part ailleurs (la regle 2 leverait), et elle leve
     SRCDIRTY, sans quoi la comparaison aux octets importes mentirait.
     ══════════════════════════════════════════════════════════════════════ */
  let GHIST = [];                 /* pile d'annulation, 20 pas au plus */

  function grilleEcrire(columns, rows, motif) {
    const d = CF.doc().data || {};
    GHIST.push({ columns: (d.columns || []).slice(),
                 rows: (d.rows || []).map((r) => r.slice()), motif: motif });
    if (GHIST.length > 20) GHIST.shift();
    SRCDIRTY = true;              /* la table ne vient plus du fichier importe */
    M.patch({ rows: rows, columns: columns });
    rebuild();                    /* /data/build puis M.setCards */
    paintGrille();
  }

  function grilleAnnuler() {
    const p = GHIST.pop();
    if (!p) { CF.toast("Rien à annuler"); return; }
    SRCDIRTY = true;
    M.patch({ rows: p.rows, columns: p.columns });
    rebuild();
    paintGrille();
    CF.toast("Annulé : " + p.motif);
  }

  function paintGrille() {
    const box = HOST.querySelector("#cf-data-grille");
    if (!box) return;
    const d = CF.doc().data || {};
    const cols = d.columns || [], rows = d.rows || [];
    if (!cols.length) {
      box.innerHTML = '<p class="hint">Importez un fichier, ou créez une '
        + 'colonne pour saisir la table ici.</p>'
        + '<button type="button" class="cf-btn" data-act="grille-colonne">'
        + 'Ajouter une colonne</button>';
      return;
    }
    box.innerHTML =
      '<div class="cf-data-gbar">'
      + '<button type="button" class="cf-btn" data-act="grille-ligne">'
      + 'Ajouter une ligne</button>'
      + '<button type="button" class="cf-btn" data-act="grille-colonne">'
      + 'Ajouter une colonne</button>'
      + '<button type="button" class="cf-btn" data-act="grille-annuler"'
      + (GHIST.length ? "" : " disabled") + '>Annuler la dernière édition'
      + (GHIST.length ? " (" + GHIST.length + ")" : "") + "</button></div>"
      + '<div class="cf-data-gwrap"><table class="cf-data-gtab"><thead><tr>'
      + '<th class="n">#</th>'
      + cols.map((c, j) => '<th><input class="cf-data-gh" data-j="' + j
        + '" value="' + esc(c) + '"></th>').join("")
      + "</tr></thead><tbody>"
      + rows.map((r, i) =>
        '<tr><td class="n">' + (i + 1) + "</td>"
        + cols.map((_c, j) => '<td><input class="cf-data-gc" data-i="' + i
          + '" data-j="' + j + '" value="'
          + esc(r[j] == null ? "" : r[j]) + '"></td>').join("")
        + "</tr>").join("")
      + "</tbody></table></div>";
  }

  function wireGrille() {
    const box = HOST.querySelector("#cf-data-grille");
    if (!box) return;
    box.addEventListener("change", (ev) => {
      const t = ev.target, d = CF.doc().data || {};
      if (t.classList.contains("cf-data-gc")) {
        const i = Number(t.dataset.i), j = Number(t.dataset.j);
        const rows = (d.rows || []).map((r) => r.slice());
        while (rows[i].length < (d.columns || []).length) rows[i].push("");
        rows[i][j] = String(t.value);
        grilleEcrire((d.columns || []).slice(), rows,
          "cellule ligne " + (i + 1) + ", « " + d.columns[j] + " »");
      } else if (t.classList.contains("cf-data-gh")) {
        const j = Number(t.dataset.j);
        const cols = (d.columns || []).slice();
        const avant = cols[j];
        cols[j] = String(t.value).trim() || avant;
        grilleEcrire(cols, (d.rows || []).map((r) => r.slice()),
          "en-tête « " + avant + " » -> « " + cols[j] + " »");
      }
    });
    box.addEventListener("click", (ev) => {
      const t = ev.target.closest("[data-act]");
      if (!t) return;
      const d = CF.doc().data || {};
      if (t.dataset.act === "grille-ligne") {
        const rows = (d.rows || []).map((r) => r.slice());
        rows.push((d.columns || []).map(() => ""));
        grilleEcrire((d.columns || []).slice(), rows, "ligne ajoutée");
      }
      if (t.dataset.act === "grille-colonne") {
        const cols = (d.columns || []).slice();
        let n = "col" + (cols.length + 1), k = 1;
        while (cols.indexOf(n) >= 0) n = "col" + (cols.length + 1) + "_" + (k++);
        cols.push(n);
        grilleEcrire(cols, (d.rows || []).map((r) => r.concat([""])),
          "colonne « " + n + " » ajoutée");
      }
      if (t.dataset.act === "grille-annuler") grilleAnnuler();
    });
  }
```

Ajouter `<div id="cf-data-grille" class="cf-data-grille"></div>` à la coquille,
appeler `wireGrille()` dans `init(host)` et `paintGrille()` après chaque import et
chaque `rebuild()`.

CSS (`css/mod-data.css` — règle 4 : tout sélecteur porte `.cf-data`) :

```css
.cf-data .cf-data-gbar { display: flex; gap: 6px; margin-bottom: 6px; flex-wrap: wrap; }
.cf-data .cf-data-gwrap { overflow: auto; max-height: 44vh; border: 1px solid var(--line); }
.cf-data .cf-data-gtab { border-collapse: collapse; font-size: 12px; }
.cf-data .cf-data-gtab th,
.cf-data .cf-data-gtab td { border: 1px solid var(--line); padding: 0; }
.cf-data .cf-data-gtab td.n,
.cf-data .cf-data-gtab th.n {
  padding: 2px 6px; opacity: .6; font-variant-numeric: tabular-nums;
  position: sticky; left: 0; background: var(--bg-elev);
}
.cf-data .cf-data-gtab input {
  border: 0; background: transparent; color: inherit; padding: 3px 6px;
  min-width: 90px; font: inherit;
}
.cf-data .cf-data-gtab input:focus { outline: 2px solid var(--cyan); }
.cf-data .cf-data-gh { font-weight: 600; }
```

- [ ] **Step 4 : relancer banc et lint**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_donnees.py
cd ..
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" scripts/qa/lint_cardforge.py --module data
```

Attendu : `9 passed` ; lint `0` (règles 4 et 5 tenues : tout sélecteur et tout
`id=` portent `cf-data`).

- [ ] **Step 5 : commit proposé**

```bash
git add frontend/cardforge/js/mod-data.js frontend/cardforge/css/mod-data.css backend/tests/test_cards_donnees.py
git commit -m 'cartes : la table se corrige dans la grille, et repart en CSV' -m 'Zéro route ajoutée : doc.data.columns et doc.data.rows tiennent déjà la table brute, /data/build la transforme et /data/export l écrit. La grille écrit sous doc.data et nulle part ailleurs — la règle 2 lèverait — et lève SRCDIRTY, sans quoi la comparaison octet par octet aux données importées jurerait que deux choses différentes sont identiques. Chaque édition est annulable, et l annulation NOMME ce qu elle défait.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Task 11 : Import Google Sheets (CSV publié) et Notion

**Files:**
- Modify: `backend/app/services/cards/data.py:2143` (routes `/import-url`, `/notion`)
- Modify: `frontend/cardforge/js/mod-data.js`
- Modify: `backend/tests/test_cards_donnees.py`

**Coût de patch** : aucun. `requests` est **présent** (T1) et `parse_table`
(`data.py:413`) lit déjà CSV, XLSX et ODS : l'import distant n'ajoute qu'un
transport.

- [ ] **Step 1 : écrire le banc qui échoue** (réseau **stubé**, jamais appelé)

```python
CSV_SHEETS = b"nom,atk,qty\nColosse,7,3\nOracle,2,2\n"


def test_une_url_sheets_de_partage_est_reecrite_en_export_csv():
    """Coller le lien de la barre d'adresse est ce que fait un humain. On le
    réécrit : l'URL d'édition rend du HTML, et un parseur de CSV y lirait une
    colonne unique pleine de balises."""
    from app.services.cards import data as D
    assert D.sheets_csv_url(
        "https://docs.google.com/spreadsheets/d/1AbC_dEf/edit#gid=42") == \
        "https://docs.google.com/spreadsheets/d/1AbC_dEf/export?format=csv&gid=42"
    assert D.sheets_csv_url(
        "https://docs.google.com/spreadsheets/d/1AbC_dEf/edit?usp=sharing") \
        .endswith("export?format=csv&gid=0")
    # une URL « Publier sur le Web » est déjà bonne : on n'y touche pas
    pub = "https://docs.google.com/spreadsheets/d/e/2PACX-1v/pub?output=csv"
    assert D.sheets_csv_url(pub) == pub


def test_une_url_qui_nest_pas_un_classeur_est_refusee_en_le_disant():
    from app.services.cards import data as D
    for mauvais in ("https://example.com/x.csv", "ftp://a/b", "javascript:1",
                    "https://docs.google.com/document/d/1x/edit"):
        with pytest.raises(ValueError) as e:
            D.sheets_csv_url(mauvais)
        assert "Google Sheets" in str(e.value), mauvais


def test_les_trois_echecs_qui_se_ressemblent_sont_distingues(monkeypatch):
    """404, 403 et le reste demandent trois gestes différents : on ne rend pas
    « erreur » trois fois."""
    from app.services.cards import data as D

    def faux(code):
        class R:
            status_code = code
            content = b""
        return lambda url, timeout=0, **kw: R()

    for code, mot in ((404, "Partager"), (403, "privé"), (500, "500")):
        monkeypatch.setattr(D, "_http_get", faux(code))
        with pytest.raises(ValueError) as e:
            D.fetch_table("https://docs.google.com/spreadsheets/d/1Z/edit")
        assert mot in str(e.value), (code, str(e.value))


def test_l_import_distant_lit_le_csv_rapporte_sans_toucher_au_reseau(monkeypatch):
    from app.services.cards import data as D
    appels = []

    def faux_get(url, timeout=0, **kw):
        appels.append(url)

        class R:
            status_code = 200
            content = CSV_SHEETS
        return R()

    monkeypatch.setattr(D, "_http_get", faux_get)

    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Sheets"})
            did = r.json()["deck"]["id"]
            return await c.post(f"/api/cards/{did}/data/import-url", json={
                "url": "https://docs.google.com/spreadsheets/d/1Z/edit#gid=7"})
    r = asyncio.run(go())
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["columns"] == ["nom", "atk", "qty"]
    assert len(j["rows"]) == 2
    assert j["source"] == "sheets"
    assert appels == ["https://docs.google.com/spreadsheets/d/1Z/"
                      "export?format=csv&gid=7"], appels


def test_un_export_notion_en_zip_rend_le_csv_qui_est_dedans():
    """Notion exporte un ZIP : un CSV plus des dossiers de médias. On prend LE
    csv ; s'il y en a plusieurs, on refuse EN LES NOMMANT — deviner ne se
    verrait qu'à l'impression."""
    import zipfile as _z
    from app.services.cards import data as D
    z = io.BytesIO()
    with _z.ZipFile(z, "w") as a:
        a.writestr("Base de donnees 1abc.csv", CSV_SHEETS)
        a.writestr("Base de donnees 1abc/img.png", b"\x89PNG")
    cols, rows, note = D.notion_table(z.getvalue())
    assert cols == ["nom", "atk", "qty"] and len(rows) == 2
    assert "Base de donnees" in note

    z2 = io.BytesIO()
    with _z.ZipFile(z2, "w") as a:
        a.writestr("a.csv", CSV_SHEETS)
        a.writestr("b.csv", CSV_SHEETS)
    with pytest.raises(ValueError) as e:
        D.notion_table(z2.getvalue())
    assert "2 fichiers CSV" in str(e.value)
    assert "a.csv" in str(e.value) and "b.csv" in str(e.value)
```

- [ ] **Step 2 : lancer, vérifier l'échec.**

- [ ] **Step 3 : écrire l'import dans `data.py`**

```python
# ── IMPORT DISTANT : Google Sheets, Notion (P4) ─────────────────────────────
# `requests` est présent dans le runtime embarqué (mesuré le 03/09/2026) et
# `parse_table` sait déjà lire CSV, XLSX et ODS : l'import distant n'ajoute
# qu'un TRANSPORT — et des garde-fous, parce qu'une URL vient du dehors.
IMPORT_MAX_BYTES = MAX_BYTES              # le même plafond que l'import local
IMPORT_TIMEOUT_S = 20

_SHEETS_ID = re.compile(
    r"^https://docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]+)")
_SHEETS_PUB = re.compile(
    r"^https://docs\.google\.com/spreadsheets/d/e/[A-Za-z0-9_-]+/pub")
_GID = re.compile(r"[#&?]gid=(\d+)")


def sheets_csv_url(url: str) -> str:
    """Le lien collé depuis la barre d'adresse -> le lien d'export CSV.

    Un humain colle l'URL d'ÉDITION : elle rend du HTML, et un parseur de CSV
    y lirait une colonne unique pleine de balises. On la réécrit. Une URL
    « Publier sur le Web » est déjà bonne et n'est pas touchée.
    """
    u = str(url or "").strip()
    if _SHEETS_PUB.match(u):
        return u
    m = _SHEETS_ID.match(u)
    if not m:
        raise ValueError(
            "Ce lien n'est pas un classeur Google Sheets. Attendu : "
            "https://docs.google.com/spreadsheets/d/… (lien de partage ou "
            "lien « Publier sur le Web » en CSV).")
    gid = _GID.search(u)
    return ("https://docs.google.com/spreadsheets/d/%s/export?format=csv&gid=%s"
            % (m.group(1), gid.group(1) if gid else "0"))


def _http_get(url: str, timeout: int = IMPORT_TIMEOUT_S):
    """LE SEUL point de réseau de cette pièce — isolé pour qu'un banc le
    remplace sans toucher au reste. Aucun test de ce dépôt n'appelle dehors."""
    import requests
    return requests.get(url, timeout=timeout, allow_redirects=True)


def fetch_table(url: str) -> tuple[bytes, str]:
    """Les octets d'un classeur distant. -> (octets, source lisible).

    TROIS ÉCHECS, TROIS PHRASES : introuvable, privé, autre. Ils demandent
    trois gestes différents ; rendre « erreur » trois fois ferait chercher au
    mauvais endroit.
    """
    cible = sheets_csv_url(url)
    r = _http_get(cible)
    code = int(getattr(r, "status_code", 0) or 0)
    if code == 404:
        raise ValueError(
            "Classeur introuvable (404). Sur Google Sheets, « Partager » doit "
            "autoriser « Tout utilisateur disposant du lien », ou utilisez "
            "« Fichier > Partager > Publier sur le Web » en CSV.")
    if code in (401, 403):
        raise ValueError(
            "Classeur privé (%d) : ce lien demande une connexion. Publiez la "
            "feuille en CSV, ou exportez-la et importez le fichier." % code)
    if code != 200:
        raise ValueError(f"Le serveur a répondu {code} pour ce lien.")
    data = bytes(getattr(r, "content", b"") or b"")
    if not data:
        raise ValueError("Le serveur a répondu sans contenu.")
    if len(data) > IMPORT_MAX_BYTES:
        raise ValueError(f"Classeur trop gros ({len(data)} octets ; plafond "
                         f"{IMPORT_MAX_BYTES}).")
    return data, "sheets"


def notion_table(raw: bytes) -> tuple[list, list, str]:
    """L'export Notion : un ZIP qui contient UN csv (plus des médias).

    S'il y en a plusieurs, on REFUSE en les nommant : deviner lequel est le
    bon serait pire que demander, et l'erreur ne se verrait qu'à l'impression.
    """
    if raw[:4] != ZIP_MAGIC:
        cols, rows = parse_table(raw)[:2]
        return cols, rows, "CSV Notion"
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        racine = [n for n in z.namelist()
                  if n.lower().endswith(".csv") and "/" not in n]
        csvs = racine or [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not csvs:
            raise ValueError("Cette archive Notion ne contient aucun CSV.")
        if len(csvs) > 1:
            raise ValueError(
                "Cette archive contient %d fichiers CSV (%s) : exportez une "
                "seule base, ou dézippez et importez le bon."
                % (len(csvs), ", ".join(sorted(csvs)[:4])))
        data = z.read(csvs[0])
    cols, rows = parse_table(data)[:2]
    return cols, rows, csvs[0]
```

> `parse_table` (`data.py:413`) rend un tuple dont les deux premiers éléments
> sont `(columns, rows)` : **relire sa signature exacte avant d'écrire ce
> `[:2]`**, et l'adapter si elle diffère. Ne rien réimplémenter.

Les routes, après `post_parse` (`data.py:2143`) :

```python
@router.post("/import-url")
async def post_import_url(did: str, body: Any = Body(default=None)):
    """Importer un classeur Google Sheets par son lien."""
    _guard(did)
    b = _obj(body)
    try:
        data, src = await asyncio.to_thread(fetch_table,
                                            str(b.get("url") or ""))
        parsed = parse_table(data, str(b.get("sep") or "auto"),
                             str(b.get("encoding") or "auto"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("cards/data: import distant impossible")
        raise HTTPException(502, f"Import impossible: {e}")
    cols, rows = parsed[0], parsed[1]
    return {"columns": cols, "rows": rows, "source": src,
            "octets": len(data)}


@router.post("/notion")
async def post_notion(did: str, body: Any = Body(default=None)):
    """Importer un export Notion (ZIP d'une base, ou CSV nu)."""
    _guard(did)
    b = _obj(body)
    try:
        cols, rows, note = notion_table(_bytes_of(b))
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"columns": cols, "rows": rows, "source": "notion", "note": note}
```

- [ ] **Step 4 : les deux boutons dans `mod-data.js`**

```js
  /* ══ IMPORT DISTANT (P4) ═════════════════════════════════════════════════
     On colle le lien de la barre d'adresse : le backend le REECRIT en export
     CSV. Un lien prive rend une phrase qui dit quoi faire, pas un 403 nu. */
  async function importerUrl() {
    const u = String(prompt("Lien du classeur Google Sheets") || "").trim();
    if (!u) return;
    CF.busy(true, "Import du classeur…");
    try {
      const r = await M.api.post("import-url", { url: u });
      SRCDIRTY = false;
      SRC = { name: u, bytes: null, wb: false, lost: 0 };
      M.patch({ columns: r.columns, rows: r.rows, src: u });
      rebuild(); paintGrille(); paintDos();
      CF.toast(r.rows.length + " ligne(s) importée(s) depuis Google Sheets");
    } catch (e) {
      CF.toast("Import impossible : " + (e && e.message), true);
    } finally { CF.busy(false); }
  }
```

Bouton `data-act="import-url"` dans la coquille, plus un
`<input type="file" accept=".zip,.csv" id="cf-data-notion">` câblé sur
`M.api.post("notion", { b64 })` — le même chemin d'octets que l'import local
déjà en place (`_bytes_of`, `data.py:2111`).

- [ ] **Step 5 : relancer**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_donnees.py
```

Attendu : `14 passed`. **Aucun accès réseau** : le banc remplace `_http_get`.

- [ ] **Step 6 : commit proposé**

```bash
git add backend/app/services/cards/data.py frontend/cardforge/js/mod-data.js backend/tests/test_cards_donnees.py
git commit -m 'cartes : importer un classeur Sheets par son lien, et un export Notion' -m 'Un humain colle l URL d édition ; elle rend du HTML, et un parseur de CSV y lirait une colonne pleine de balises. Le backend la réécrit en export CSV, et distingue les trois échecs qui se ressemblent — introuvable, privé, autre — chacun avec le geste qui le répare. Notion exporte un ZIP : on prend LE csv, et s il y en a plusieurs on refuse EN LES NOMMANT, parce que deviner ne se verrait qu à l impression. Le réseau passe par un seul point que le banc remplace : aucun test de ce dépôt n appelle dehors.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Task 12 : Localisation — une colonne par langue, un rendu par langue

**Files:**
- Modify: `backend/app/services/cards/data.py` (langues, mappage par langue, route `/langues`)
- Modify: `frontend/cardforge/js/mod-data.js:3140` (`state` + clé `lang`) et le panneau
- Create: `backend/tests/test_cards_langues.py`

**Coût de patch** : aucun. **Le rendu par langue est gratuit** : un mappage
colonne → emplacement différent, `build_deck` rejoué, `M.setCards` — le moteur de
rendu ne change pas d'une ligne, et c'est le but.

**Lien, sans replanifier** : faire **tenir** une traduction plus longue dans son
emplacement est le bac **R7 P4** (texte adaptatif : rétrécissement, coupe, mesure PIL
de la largeur avec la fonte embarquée). Cette tâche **mesure** le débordement et le
**dit** ; elle ne le corrige pas.

- [ ] **Step 1 : écrire le banc qui échoue**

Créer `backend/tests/test_cards_langues.py` (même en-tête que `test_cards_dos.py`),
puis :

```python
COLS = ["id", "nom_fr", "nom_en", "texte_fr", "texte_en", "atk", "qty"]
ROWS = [["c1", "Colosse", "Colossus", "Mêlée de lances", "Spear melee", "7", "2"],
        ["c2", "Oracle", "Oracle", "Voit la brume", "Sees the mist", "2", "1"]]


def test_les_langues_se_devinent_par_le_suffixe_des_colonnes():
    from app.services.cards import data as D
    r = D.langues_table(COLS)
    assert [l["code"] for l in r["langues"]] == ["fr", "en"]
    assert r["langues"][0]["colonnes"] == {"nom": "nom_fr", "texte": "texte_fr"}
    # UNE COLONNE SANS SUFFIXE EST NEUTRE : elle sert dans toutes les langues
    # et n'appartient à aucune. Deviner l'inverse dupliquerait `atk`.
    assert r["neutres"] == ["id", "atk", "qty"]


def test_un_deck_se_construit_dans_chaque_langue_avec_les_memes_cartes():
    from app.services.cards import data as D
    slots = [{"id": "titre"}, {"id": "corps"}]
    base = {"nom": "titre", "texte": "corps"}
    fr = D.build_deck(COLS, ROWS, D.map_pour_langue(COLS, base, "fr"),
                      qty_col="qty", slots=slots)
    en = D.build_deck(COLS, ROWS, D.map_pour_langue(COLS, base, "en"),
                      qty_col="qty", slots=slots)
    assert len(fr["cards"]) == len(en["cards"]) == 3
    assert fr["cards"][0]["fields"]["titre"] == "Colosse"
    assert en["cards"][0]["fields"]["titre"] == "Colossus"
    # LES IDENTIFIANTS NE BOUGENT PAS : c'est le même jeu, pas deux jeux
    assert [c["id"] for c in fr["cards"]] == [c["id"] for c in en["cards"]]


def test_une_base_sans_colonne_dans_la_langue_nest_pas_repliee_ailleurs():
    """Imprimer du français sur une carte anglaise sans prévenir est PIRE
    qu'un trou : la base absente sort simplement du mappage."""
    from app.services.cards import data as D
    cols = ["nom_fr", "texte_fr", "nom_en"]
    mp = D.map_pour_langue(cols, {"nom": "titre", "texte": "corps"}, "en")
    assert mp == {"nom_en": "titre"}
    assert "texte_fr" not in mp


def test_une_langue_incomplete_est_dite_carte_par_carte_avant_le_rendu():
    from app.services.cards import data as D
    rows = [r[:] for r in ROWS]
    rows[1][2] = ""                          # nom_en de la carte 2, vidé
    r = D.langues_report(COLS, rows, {"nom": "titre", "texte": "corps"},
                         qty_col="qty")
    en = [l for l in r["langues"] if l["code"] == "en"][0]
    assert en["manquants"] == 1
    assert en["cartes_incompletes"] == 1
    assert "nom_en" in en["details"][0]["colonne"]
    assert [l for l in r["langues"] if l["code"] == "fr"][0]["manquants"] == 0


def test_la_route_langues_repond_et_refuse_un_corps_mal_forme():
    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Langues"})
            did = r.json()["deck"]["id"]
            ok = await c.post(f"/api/cards/{did}/data/langues",
                              json={"columns": COLS, "rows": ROWS,
                                    "map": {"nom": "titre"}, "qty_col": "qty"})
            ko = await c.post(f"/api/cards/{did}/data/langues",
                              json={"columns": COLS, "rows": ROWS,
                                    "map": "oui"})
            return ok, ko
    ok, ko = asyncio.run(go())
    assert ok.status_code == 200, ok.text
    assert ko.status_code == 400, ko.status_code


def test_l_ecran_propose_les_langues_et_renvoie_au_texte_adaptatif():
    js = (pathlib.Path(__file__).resolve().parents[2] / "frontend" / "cardforge"
          / "js" / "mod-data.js").read_text(encoding="utf-8")
    assert 'M.api.post("langues' in js
    assert 'data-act="langue"' in js
    for phrase in ("Langue active", "colonne manquante", "pièce 03"):
        assert phrase in js, phrase
```

- [ ] **Step 2 : lancer, vérifier l'échec.**

- [ ] **Step 3 : écrire les langues dans `data.py`**

```python
# ── LOCALISATION (P5) ───────────────────────────────────────────────────────
# UNE COLONNE PAR LANGUE, repérée au suffixe. Rien de plus : le rendu par
# langue est GRATUIT — un mappage différent, `build_deck` rejoué, `setCards`.
# Le moteur de rendu ne change pas d'une ligne, et c'est le but.
#
# CE QUE CETTE PIÈCE NE FAIT PAS : faire tenir un texte plus long dans son
# emplacement. C'est le texte adaptatif (bac R7 P4 : rétrécissement, coupe,
# mesure PIL de la largeur avec la fonte embarquée). Ici on MESURE le manque
# et on le dit ; le remède est ailleurs, et il est nommé à l'écran.
LANG_SUFFIXE = re.compile(
    r"^(?P<base>.+?)[_\-. ](?P<code>[a-z]{2}(?:[_-][a-z]{2})?)$", re.IGNORECASE)
LANG_NOMS = {"fr": "français", "en": "anglais", "es": "espagnol",
             "de": "allemand", "it": "italien", "pt": "portugais",
             "nl": "néerlandais", "pl": "polonais", "ja": "japonais"}


def langues_table(columns: list) -> dict:
    """Les langues devinées des suffixes, dans l'ordre d'apparition.

    Une colonne sans suffixe est NEUTRE (identifiant, chiffre, quantité) :
    elle sert dans toutes les langues et n'appartient à aucune. Deviner
    l'inverse dupliquerait `atk` en `atk_fr` et `atk_en`.
    """
    cols = [str(c) for c in (columns or ())]
    langs: dict[str, dict] = {}
    neutres: list[str] = []
    for c in cols:
        m = LANG_SUFFIXE.match(c)
        code = m.group("code").lower().replace("_", "-") if m else ""
        if not m or code not in LANG_NOMS:
            neutres.append(c)
            continue
        e = langs.setdefault(code, {"code": code, "label": LANG_NOMS[code],
                                    "colonnes": {}})
        e["colonnes"][m.group("base")] = c
    return {"langues": list(langs.values()), "neutres": neutres}


def map_pour_langue(columns: list, base_map: dict, code: str) -> dict:
    """Le mappage `colonne -> emplacement`, traduit dans une langue.

    `base_map` parle en BASES (« nom » -> « titre ») ; on rend le mappage réel
    (« nom_en » -> « titre »). Une base sans colonne dans cette langue est
    SIMPLEMENT ABSENTE — jamais repliée sur une autre langue : imprimer du
    français sur une carte anglaise sans prévenir est pire qu'un trou.
    """
    par = {l["code"]: l["colonnes"] for l in langues_table(columns)["langues"]}
    cols = set(str(c) for c in (columns or ()))
    out: dict[str, str] = {}
    for base, slot in (base_map or {}).items():
        col = par.get(str(code).lower(), {}).get(str(base))
        if col:
            out[col] = slot
        elif str(base) in cols:        # colonne neutre : elle sert partout
            out[str(base)] = slot
    return out


def langues_report(columns: list, rows: list, base_map: dict,
                   qty_col: Any = None) -> dict:
    """Ce qui manque, PAR LANGUE et PAR CARTE, AVANT le rendu."""
    t = langues_table(columns)
    cols = [str(c) for c in (columns or ())]
    iq = cols.index(str(qty_col)) if qty_col and str(qty_col) in cols else -1
    out = []
    for l in t["langues"]:
        mp = map_pour_langue(cols, base_map, l["code"])
        idx = {c: cols.index(c) for c in mp if c in cols}
        # une base mappée SANS colonne dans cette langue est un trou aussi,
        # et il est constant sur toutes les lignes
        absentes = [b for b in (base_map or ())
                    if b not in l["colonnes"] and b not in cols]
        manquants = incompletes = 0
        details = []
        for k, r in enumerate(rows or ()):
            q = read_qty(r[iq]) if 0 <= iq < len(r) else 1
            trous = [c for c, i in idx.items()
                     if not (str(r[i]).replace(BLANK, "").strip()
                             if i < len(r) else "")]
            if trous or absentes:
                incompletes += 1
                manquants += len(trous) + len(absentes)
                if len(details) < 20:
                    details.append({"ligne": k + 1, "cartes": q,
                                    "colonne": ", ".join(trous + absentes)})
        out.append(dict(l, manquants=manquants, cartes_incompletes=incompletes,
                        details=details, map=mp))
    return {"langues": out, "neutres": t["neutres"]}
```

La route :

```python
@router.post("/langues")
async def post_langues(did: str, body: Any = Body(default=None)):
    """Les langues du fichier, et ce qui manque dans chacune."""
    _guard(did)
    b = _obj(body)
    cols, rows = _table_of(b)
    mp = b.get("map")
    if mp is not None and not isinstance(mp, dict):
        raise HTTPException(400, "`map` doit être un objet JSON")
    try:
        return langues_report(cols, rows, mp or {}, b.get("qty_col"))
    except ValueError as e:
        raise HTTPException(400, str(e))
```

- [ ] **Step 4 : le sélecteur dans `mod-data.js`**

Ajouter `lang: ""` au `state` (`mod-data.js:3140-3151`), puis :

```js
  /* ══ LANGUES (P5) ════════════════════════════════════════════════════════
     Le rendu par langue est GRATUIT : un mappage different, /data/build
     rejoue, setCards. Ce panneau CHOISIT et DIT ce qui manque. Faire TENIR un
     texte plus long n'est pas ici : c'est le texte adaptatif de la piece 03
     (bac R7 P4). On le nomme, on ne le refait pas. */
  let LANGS = [];

  function mapLangue() {
    const d = CF.doc().data || {};
    if (!d.lang) return d.map;
    const l = LANGS.filter((x) => x.code === d.lang)[0];
    return (l && l.map) || d.map;
  }

  async function paintLangues() {
    const box = HOST.querySelector("#cf-data-langues");
    if (!box) return;
    const d = CF.doc().data || {};
    if (!d.columns || !d.columns.length) { box.innerHTML = ""; return; }
    try {
      const r = await M.api.post("langues", { columns: d.columns,
        rows: d.rows, map: d.map, qty_col: d.qty_col });
      LANGS = r.langues || [];
    } catch (e) {
      if (!(e && e.missing)) console.warn("cardforge/data: langues", e);
      return;
    }
    if (!LANGS.length) {
      box.innerHTML = '<p class="hint">Aucune colonne suffixée par une langue '
        + "(<code>nom_fr</code>, <code>nom_en</code>…) : le jeu est monolingue."
        + "</p>";
      return;
    }
    const cur = d.lang || LANGS[0].code;
    const act = LANGS.filter((x) => x.code === cur)[0] || LANGS[0];
    box.innerHTML =
      '<div class="cf-data-langs">'
      + LANGS.map((l) => '<button type="button" class="cf-data-lang'
        + (l.code === cur ? " on" : "") + '" data-act="langue" data-v="'
        + esc(l.code) + '">' + esc(l.label)
        + (l.manquants ? ' <i class="ko">' + l.cartes_incompletes
          + " carte(s) à trous</i>" : ' <i class="ok">complète</i>")
        + "</button>").join("")
      + "</div>"
      + (act.details || []).map((x) => '<p class="cf-data-avert">Ligne '
        + x.ligne + " · colonne manquante : " + esc(x.colonne)
        + " (" + x.cartes + " carte(s))</p>").join("")
      + '<p class="hint">Langue active : le deck est reconstruit avec les '
      + "colonnes de cette langue. Un texte plus long qui déborde de son "
      + "emplacement se règle dans la <b>pièce 03</b> (texte adaptatif), "
      + "pas ici.</p>";
  }
```

Câbler `data-act="langue"` sur `M.patch({ lang })` puis `rebuild()` ; dans
`rebuild()`, envoyer `mapping: mapLangue()` au lieu de `d.map`.

- [ ] **Step 5 : relancer**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_langues.py
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_data.py
```

Attendu : `6 passed` ; `test_cards_data.py` vert.

- [ ] **Step 6 : commit proposé**

```bash
git add backend/app/services/cards/data.py frontend/cardforge/js/mod-data.js backend/tests/test_cards_langues.py
git commit -m 'cartes : une colonne par langue, un rendu par langue' -m 'Le rendu par langue ne coûte rien : un mappage différent, build_deck rejoué, setCards — le moteur ne change pas d une ligne. Ce qui coûtait, c était le silence : une base sans colonne dans la langue choisie N EST PAS repliée sur une autre, parce qu imprimer du français sur une carte anglaise sans prévenir est pire qu un trou. Les trous sont donc comptés par langue et par carte, avant le rendu. Faire TENIR une traduction plus longue reste le texte adaptatif de la pièce 03 : le panneau le nomme, ce plan ne le refait pas.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Task 13 : Traduction proposée par le LLM, validée carte par carte

**Files:**
- Modify: `backend/app/services/cards/data.py` (route `/traduire`)
- Modify: `frontend/cardforge/js/mod-data.js`
- Modify: `backend/tests/test_cards_langues.py`

**Coût de patch** : aucun. `openai_llm.chat(prompt, system=…, max_tokens=…)` et
`gemini_llm.chat(…)` existent avec `available()` (`backend/app/services/openai_llm.py:16,63`).

- [ ] **Step 1 : écrire le banc qui échoue** (LLM **stubé**, jamais appelé)

```python
def test_la_traduction_est_proposee_et_jamais_ecrite_dans_la_table(monkeypatch):
    """LE POINT : la route PROPOSE. Elle ne touche pas à `rows`. C'est
    l'utilisateur qui accepte, carte par carte."""
    from app.services.cards import data as D
    monkeypatch.setattr(D, "_llm_dispo", lambda: True)
    monkeypatch.setattr(D, "_llm_chat",
                        lambda p, s, n: '[{"ligne":1,"valeur":"Colossus"},'
                                        '{"ligne":2,"valeur":"Oracle"}]')

    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Trad"})
            did = r.json()["deck"]["id"]
            return await c.post(f"/api/cards/{did}/data/traduire", json={
                "columns": ["nom_fr", "nom_en"],
                "rows": [["Colosse", ""], ["Oracle", ""]],
                "source": "nom_fr", "cible": "nom_en", "vers": "en"})
    r = asyncio.run(go())
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["etat"] == "proposition"
    assert [p["valeur"] for p in j["propositions"]] == ["Colossus", "Oracle"]
    assert all(p["accepte"] is False for p in j["propositions"])
    assert j["source"] == "nom_fr" and j["cible"] == "nom_en"


def test_une_cellule_deja_remplie_nest_meme_pas_envoyee_au_modele(monkeypatch):
    """On ne paye pas pour écraser un travail humain."""
    from app.services.cards import data as D
    vus = []
    monkeypatch.setattr(D, "_llm_dispo", lambda: True)

    def faux(p, s, n):
        vus.append(p)
        return '[{"ligne":2,"valeur":"Oracle"}]'
    monkeypatch.setattr(D, "_llm_chat", faux)

    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Trad2"})
            did = r.json()["deck"]["id"]
            return await c.post(f"/api/cards/{did}/data/traduire", json={
                "columns": ["nom_fr", "nom_en"],
                "rows": [["Colosse", "Colossus"], ["Oracle", ""]],
                "source": "nom_fr", "cible": "nom_en", "vers": "en"})
    r = asyncio.run(go())
    j = r.json()
    assert [p["ligne"] for p in j["propositions"]] == [2]
    assert j["deja_remplies"] == 1
    assert j["lignes_envoyees"] == 1
    assert "Colosse" not in vus[0], vus[0]


def test_une_reponse_mal_formee_fait_502_avec_la_phrase_qui_dit_quoi_faire(monkeypatch):
    from app.services.cards import data as D
    monkeypatch.setattr(D, "_llm_dispo", lambda: True)
    monkeypatch.setattr(D, "_llm_chat", lambda p, s, n: "Voici : bonjour !")

    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Trad3"})
            did = r.json()["deck"]["id"]
            return await c.post(f"/api/cards/{did}/data/traduire", json={
                "columns": ["a", "b"], "rows": [["x", ""]],
                "source": "a", "cible": "b", "vers": "en"})
    r = asyncio.run(go())
    assert r.status_code == 502, r.status_code
    assert "JSON" in r.text and "à la main" in r.text


def test_sans_cle_la_route_repond_503_et_non_une_traduction_vide(monkeypatch):
    from app.services.cards import data as D
    monkeypatch.setattr(D, "_llm_dispo", lambda: False)

    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Trad4"})
            did = r.json()["deck"]["id"]
            return await c.post(f"/api/cards/{did}/data/traduire", json={
                "columns": ["a", "b"], "rows": [["x", ""]],
                "source": "a", "cible": "b", "vers": "en"})
    assert asyncio.run(go()).status_code == 503


def test_l_ecran_valide_carte_par_carte_et_jamais_en_bloc():
    js = (pathlib.Path(__file__).resolve().parents[2] / "frontend" / "cardforge"
          / "js" / "mod-data.js").read_text(encoding="utf-8")
    assert 'data-act="trad-accepter"' in js
    assert 'data-act="trad-refuser"' in js
    assert 'data-act="trad-tout"' not in js, "pas de validation en bloc"
    for phrase in ("Proposition", "carte par carte",
                   "aucune traduction n’est écrite"):
        assert phrase in js, phrase
```

- [ ] **Step 2 : lancer, vérifier l'échec.**

- [ ] **Step 3 : écrire la traduction dans `data.py`**

```python
# ── TRADUCTION PROPOSÉE (P5) ────────────────────────────────────────────────
# LA ROUTE PROPOSE, ELLE N'ÉCRIT PAS. Une traduction automatique posée droit
# dans la table est une carte imprimée avec une faute que personne n'a vue :
# la réponse est un BROUILLON (`accepte: false`) et c'est l'écran qui accepte,
# ligne par ligne, le texte source en regard.
TRAD_MAX_LIGNES = 200
TRAD_SYSTEM = (
    "Tu traduis des textes de cartes de jeu. Rends UNIQUEMENT un tableau JSON "
    '[{"ligne": <entier>, "valeur": "<traduction>"}], sans texte autour et '
    "sans bloc de code. Garde la casse et la ponctuation du jeu ; ne rallonge "
    "pas inutilement, le texte doit tenir sur une carte."
)


def _llm_dispo() -> bool:
    from app.services import gemini_llm, openai_llm
    return bool(openai_llm.available() or gemini_llm.available())


def _llm_chat(prompt: str, system: str, max_tokens: int) -> str:
    """LE SEUL point d'appel LLM de cette pièce — isolé pour le banc."""
    from app.services import gemini_llm, openai_llm
    if openai_llm.available():
        return openai_llm.chat(prompt, system=system, max_tokens=max_tokens)
    return gemini_llm.chat(prompt, system=system, max_tokens=max_tokens)


def traduire(columns: list, rows: list, source: str, cible: str, vers: str,
             forcer: bool = False) -> dict:
    """-> {etat, propositions:[{ligne, source, valeur, accepte:false}], …}"""
    cols = [str(c) for c in (columns or ())]
    for nom, val in (("source", source), ("cible", cible)):
        if str(val) not in cols:
            raise ValueError(f"Colonne {nom} inconnue: {val!r}")
    isrc, icib = cols.index(str(source)), cols.index(str(cible))
    langue = LANG_NOMS.get(str(vers).lower(), str(vers))
    a_faire, deja = [], 0
    for k, r in enumerate(rows or ()):
        txt = str(r[isrc]).replace(BLANK, "").strip() if isrc < len(r) else ""
        cur = str(r[icib]).replace(BLANK, "").strip() if icib < len(r) else ""
        if not txt:
            continue
        if cur and not forcer:
            deja += 1               # on ne paye pas pour écraser un humain
            continue
        a_faire.append((k + 1, txt))
    if not a_faire:
        return {"etat": "proposition", "source": source, "cible": cible,
                "vers": vers, "propositions": [], "deja_remplies": deja,
                "lignes_envoyees": 0, "sans_reponse": 0}
    if len(a_faire) > TRAD_MAX_LIGNES:
        raise ValueError(
            f"{len(a_faire)} lignes à traduire ; le plafond est "
            f"{TRAD_MAX_LIGNES} par appel. Filtrez, ou traduisez en deux fois.")
    corps = json.dumps([{"ligne": n, "texte": t} for n, t in a_faire],
                       ensure_ascii=False)
    brut = _llm_chat(f"Traduis vers le {langue} :\n{corps}", TRAD_SYSTEM,
                     40 * len(a_faire) + 200)
    txt = str(brut or "").strip()
    if txt.startswith("```"):
        txt = txt.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        brute = json.loads(txt)
        if not isinstance(brute, list):
            raise ValueError("pas un tableau")
    except Exception:
        raise RuntimeError(
            "Le modèle n'a pas rendu de JSON exploitable. Réessayez, ou "
            "traduisez cette colonne à la main.")
    par: dict[int, str] = {}
    for e in brute:
        if isinstance(e, dict) and "ligne" in e:
            try:
                par[int(e["ligne"])] = str(e.get("valeur", ""))
            except (TypeError, ValueError):
                continue
    props = [{"ligne": n, "source": t, "valeur": par.get(n, ""),
              "accepte": False} for n, t in a_faire]
    return {"etat": "proposition", "source": source, "cible": cible,
            "vers": vers, "propositions": props, "deja_remplies": deja,
            "lignes_envoyees": len(a_faire),
            "sans_reponse": len([p for p in props if not p["valeur"]])}
```

La route :

```python
@router.post("/traduire")
async def post_traduire(did: str, body: Any = Body(default=None)):
    """Une PROPOSITION de traduction. La table n'est pas touchée : c'est
    l'écran qui accepte, carte par carte."""
    _guard(did)
    b = _obj(body)
    cols, rows = _table_of(b)
    if not _llm_dispo():
        raise HTTPException(
            503, "Aucun modèle de langue configuré : renseignez une clé "
                 "OpenAI ou Gemini dans les Réglages.")
    try:
        return await asyncio.to_thread(
            traduire, cols, rows, str(b.get("source") or ""),
            str(b.get("cible") or ""), str(b.get("vers") or ""),
            bool(b.get("forcer")))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    except Exception as e:
        logger.exception("cards/data: traduction impossible")
        raise HTTPException(502, f"Traduction impossible: {e}")
```

- [ ] **Step 4 : la validation carte par carte dans `mod-data.js`**

```js
  /* ══ TRADUCTION (P5) ═════════════════════════════════════════════════════
     La route PROPOSE. Aucune traduction n'entre dans la table sans un clic :
     une faute automatique se decouvre a l'impression, quand elle coute. La
     validation est donc carte par carte, le texte source en regard, et elle
     passe par grilleEcrire — annulable, une seule plume. */
  let TRAD = null;

  async function traduire(src, cib, vers) {
    CF.busy(true, "Traduction proposée…");
    try {
      const d = CF.doc().data || {};
      TRAD = await M.api.post("traduire", { columns: d.columns, rows: d.rows,
        source: src, cible: cib, vers: vers });
      paintTrad();
      CF.toast(TRAD.lignes_envoyees + " ligne(s) proposée(s) · "
        + TRAD.deja_remplies + " déjà remplie(s), laissée(s) telles quelles");
    } catch (e) {
      CF.toast("Traduction impossible : " + (e && e.message), true);
    } finally { CF.busy(false); }
  }

  function paintTrad() {
    const box = HOST.querySelector("#cf-data-trad");
    if (!box) return;
    if (!TRAD) { box.innerHTML = ""; return; }
    box.innerHTML =
      '<p class="hint">Proposition — aucune traduction n’est écrite tant '
      + "qu’elle n’est pas acceptée, carte par carte.</p>"
      + '<table class="cf-data-tradtab"><tbody>'
      + TRAD.propositions.map((p, k) =>
        "<tr" + (p.accepte ? ' class="on"' : "") + "><td>" + p.ligne
        + "</td><td>" + esc(p.source) + "</td>"
        + '<td><input class="cf-data-tradv" data-k="' + k + '" value="'
        + esc(p.valeur) + '"></td>'
        + '<td><button type="button" data-act="trad-accepter" data-k="' + k
        + '">Accepter</button> <button type="button" '
        + 'data-act="trad-refuser" data-k="' + k + '">Refuser</button></td>'
        + "</tr>").join("")
      + "</tbody></table>";
  }

  function tradAccepter(k) {
    const p = TRAD && TRAD.propositions[k];
    if (!p) return;
    const d = CF.doc().data || {};
    const inp = HOST.querySelector('.cf-data-tradv[data-k="' + k + '"]');
    const val = inp ? String(inp.value) : p.valeur;
    const j = d.columns.indexOf(TRAD.cible);
    if (j < 0) { CF.toast("Colonne cible introuvable", true); return; }
    const rows = (d.rows || []).map((r) => r.slice());
    rows[p.ligne - 1][j] = val;
    /* la MÊME plume que la grille : annulable, SRCDIRTY leve, une ecriture */
    grilleEcrire((d.columns || []).slice(), rows,
      "traduction ligne " + p.ligne + " -> « " + TRAD.cible + " »");
    p.accepte = true;
    paintTrad();
  }
```

Câbler `trad-accepter` sur `tradAccepter(k)` et `trad-refuser` sur le retrait de
la ligne dans `TRAD.propositions` + `paintTrad()`.

- [ ] **Step 5 : relancer**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_langues.py
```

Attendu : `11 passed`. **Aucun appel réseau** : `_llm_chat` et `_llm_dispo` sont
remplacés par le banc.

- [ ] **Step 6 : commit proposé**

```bash
git add backend/app/services/cards/data.py frontend/cardforge/js/mod-data.js backend/tests/test_cards_langues.py
git commit -m 'cartes : la traduction se propose, elle ne s ecrit pas' -m 'Une traduction automatique posée droit dans la table est une carte imprimée avec une faute que personne n a vue : la route rend un brouillon et la validation se fait ligne par ligne, le texte source en regard. Les cellules déjà remplies ne partent même pas au modèle — on ne paye pas pour écraser un travail humain, et le prompt le prouve. Une réponse mal formée fait 502 avec le geste qui répare, jamais 500 ; sans clé, 503 et non une traduction vide. L acceptation passe par la plume de la grille : annulable, et une seule écriture.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

# Lot 2 — différenciant

## Task 14 : Le coût du deck avant le tir, et le prompt par ligne

**Files:**
- Create: `backend/app/services/cards/face_lot.py`
- Modify: `backend/app/services/cards/face.py` (routes `/lot/devis`, `/lot/prompts`)
- Modify: `scripts/qa/lint_cardforge.py:137` (`EXTRA_PY["face"]`)
- Create: `backend/tests/test_cards_lot_art.py`

**Coût de patch** : aucun. Un sidecar de plus pour `face`. `pricing.estimate(
{"kind": "image", "model": …, "n": …})` existe (`pricing.py:202-227`) et
`_IMAGE_MODELS` (103) porte les prix par modèle : **le devis ne calcule aucun prix
lui-même**.

**Lien, sans replanifier** : les personnages viennent de la bible
(`GET /api/bible/entities`, `routes.py:5109`) et leur planche de référence est
celle de **R3 P3**. Si R3 P3 n'est pas livrée, on lit la planche déjà écrite sur
disque ; on ne réimplémente pas le chaînage d'identité.

- [ ] **Step 1 : écrire le banc qui échoue**

Créer `backend/tests/test_cards_lot_art.py` (même en-tête), puis :

```python
from app.services.cards import face_lot as FL                    # noqa: E402

COLS = ["nom", "espece", "prompt", "art", "qty"]
ROWS = [["Colosse", "golem", "un golem de pierre sous la pluie", "", "3"],
        ["Oracle", "pieuvre", "", "oracle_v2.png", "2"],
        ["Rebut", "golem", "", "", "5"],
        ["Écho", "pieuvre", "un écho translucide", "", "1"]]


def test_le_devis_compte_les_LIGNES_a_generer_et_non_les_cartes():
    """3 Colosses partagent UNE illustration : payer trois fois la même image
    serait le défaut le plus cher de tout le plan."""
    d = FL.devis(COLS, ROWS, model="flux", n_par_ligne=1, qty_col="qty")
    assert d["lignes_a_generer"] == 3          # Oracle a déjà son art
    assert d["cartes_couvertes"] == 9          # 3 + 5 + 1
    assert d["deja_illustrees"] == 1
    assert d["images"] == 3
    assert d["total_usd"] > 0
    assert len(d["breakdown"]) >= 1


def test_le_devis_multiplie_par_les_variantes_demandees():
    d1 = FL.devis(COLS, ROWS, model="flux", n_par_ligne=1, qty_col="qty")
    d4 = FL.devis(COLS, ROWS, model="flux", n_par_ligne=4, qty_col="qty")
    assert d4["images"] == 12
    assert round(d4["total_usd"], 6) == round(d1["total_usd"] * 4, 6)


def test_le_devis_suit_le_prix_du_MODELE_et_ne_le_recalcule_pas():
    from app.services import pricing
    p = pricing.load()
    d = FL.devis(COLS, ROWS, model="nano-banana-pro", n_par_ligne=1,
                 qty_col="qty")
    assert round(d["total_usd"], 6) == round(3 * p["nano_banana_pro_usd"], 6)


def test_le_prompt_dune_ligne_melange_la_colonne_le_style_et_la_bible():
    p = FL.prompt_ligne(
        COLS, ROWS[0], gabarit="{prompt}, {espece}",
        style="affiche polonaise, huile craquelee, fond ronge",
        entites=[{"nom": "Colosse", "espece": "golem",
                  "description": "trois mètres, mousse verte",
                  "planche": "planche_colosse.png"}])
    assert "un golem de pierre sous la pluie" in p["prompt"]
    assert "affiche polonaise" in p["prompt"]
    assert "trois mètres, mousse verte" in p["prompt"]
    assert p["references"] == ["planche_colosse.png"]
    # AUCUN NOM D'ARTISTE : la doctrine du dépôt, tenue mécaniquement
    assert p["entite"] == "Colosse"


def test_une_ligne_sans_prompt_ni_entite_est_signalee_et_non_inventee():
    p = FL.prompt_ligne(COLS, ROWS[2], gabarit="{prompt}", style="", entites=[])
    assert p["prompt"] == ""
    assert p["manque"] == ["prompt"]


def test_la_route_devis_repond_et_grise_sans_cle(monkeypatch):
    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Lot"})
            did = r.json()["deck"]["id"]
            return await c.post(f"/api/cards/{did}/face/lot/devis", json={
                "columns": COLS, "rows": ROWS, "qty_col": "qty",
                "model": "flux", "n": 1})
    r = asyncio.run(go())
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["lignes_a_generer"] == 3 and j["images"] == 3
    assert "total_usd" in j
```

- [ ] **Step 2 : lancer, vérifier l'échec.**

- [ ] **Step 3 : écrire `face_lot.py`**

```python
# -*- coding: utf-8 -*-
"""Card Forge — pièce 01, sidecar « art du deck ».

SIDECAR : aucun `router` (règle 8). Le devis et la fabrique de prompts.

LE DEVIS COMPTE LES LIGNES, PAS LES CARTES. Trois Colosses partagent UNE
illustration : facturer trois fois la même image serait l'erreur la plus chère
de tout ce plan. Et il ne calcule AUCUN prix lui-même — `pricing.estimate`
détient les tarifs par modèle (pricing.py:103), une seule table à tenir.

AUCUN NOM D'ARTISTE dans un prompt : la doctrine du dépôt (skills
`walkuski-style`, `vitrail-mloda-polska`). Le style se porte par des
descripteurs — palette, matière, fractions de composition — jamais par un nom
que les générateurs refusent ou pastichent.
"""
from __future__ import annotations

from typing import Any

from .data import BLANK, read_qty

__all__ = ["devis", "prompt_ligne", "prompts_lot"]


def _clean(v: Any) -> str:
    return str(v if v is not None else "").replace(BLANK, "").strip()


def _col(cols: list, noms) -> int:
    bas = [str(c).strip().lower() for c in cols]
    for n in noms:
        if n in bas:
            return bas.index(n)
    return -1


def devis(columns: list, rows: list, model: str = "flux",
          n_par_ligne: int = 1, qty_col: Any = None,
          art_col: Any = None) -> dict:
    """Le coût du deck AVANT le tir. `pricing` tient les prix, pas nous."""
    from app.services import pricing
    cols = [str(c) for c in (columns or ())]
    ia = cols.index(str(art_col)) if art_col and str(art_col) in cols \
        else _col(cols, ("art", "illustration", "image"))
    iq = cols.index(str(qty_col)) if qty_col and str(qty_col) in cols else -1
    n = max(1, min(4, int(n_par_ligne or 1)))
    a_faire, couvertes, deja = 0, 0, 0
    for r in (rows or ()):
        q = read_qty(r[iq]) if 0 <= iq < len(r) else 1
        if 0 <= ia < len(r) and _clean(r[ia]):
            deja += 1
            continue
        a_faire += 1
        couvertes += q
    est = pricing.estimate({"kind": "image", "model": str(model or "flux"),
                            "n": a_faire * n})
    return {"lignes_a_generer": a_faire, "deja_illustrees": deja,
            "cartes_couvertes": couvertes, "n_par_ligne": n,
            "images": a_faire * n, "model": str(model or "flux"),
            "total_usd": float(est.get("total_usd") or 0.0),
            "breakdown": est.get("breakdown") or []}


def prompt_ligne(columns: list, row: list, gabarit: str = "{prompt}",
                 style: str = "", entites: Any = None,
                 cle_entite: str = "nom") -> dict:
    """Le prompt d'UNE ligne : la colonne, le style de série, la bible.

    Une valeur absente n'est jamais inventée : elle est LISTÉE dans `manque`,
    et l'écran refuse le tir tant qu'il reste des trous — payer pour une image
    fabriquée à partir de rien est un coût sans contrepartie.
    """
    cols = [str(c) for c in (columns or ())]
    val = {c: _clean(row[i]) if i < len(row) else "" for i, c in enumerate(cols)}
    manque = []
    try:
        base = gabarit.format(**val)
    except KeyError as e:
        raise ValueError(f"Le gabarit cite une colonne absente: {e}")
    if not base.strip():
        manque.append("prompt")
    ident = val.get(str(cle_entite), "")
    ent = next((e for e in (entites or ())
                if str(e.get("nom", "")).strip().lower() == ident.lower()), None)
    morceaux = [base.strip()]
    if ent and _clean(ent.get("description")):
        morceaux.append(_clean(ent["description"]))
    if style.strip():
        morceaux.append(style.strip())
    refs = []
    if ent and _clean(ent.get("planche")):
        refs.append(_clean(ent["planche"]))
    return {"prompt": ", ".join(m for m in morceaux if m) if base.strip() else "",
            "entite": (ent or {}).get("nom", ""), "references": refs,
            "manque": manque}


def prompts_lot(columns: list, rows: list, gabarit: str, style: str,
                entites: Any = None, qty_col: Any = None,
                art_col: Any = None) -> dict:
    """Un prompt par LIGNE à générer, dans l'ordre de la table."""
    cols = [str(c) for c in (columns or ())]
    ia = cols.index(str(art_col)) if art_col and str(art_col) in cols \
        else _col(cols, ("art", "illustration", "image"))
    iq = cols.index(str(qty_col)) if qty_col and str(qty_col) in cols else -1
    out, trous = [], 0
    for k, r in enumerate(rows or ()):
        if 0 <= ia < len(r) and _clean(r[ia]):
            continue
        p = prompt_ligne(cols, r, gabarit, style, entites)
        p["ligne"] = k + 1
        p["cartes"] = read_qty(r[iq]) if 0 <= iq < len(r) else 1
        trous += 1 if p["manque"] else 0
        out.append(p)
    return {"prompts": out, "lignes": len(out), "incomplets": trous}
```

- [ ] **Step 4 : les routes dans `face.py` et le lint**

```python
@router.post("/lot/devis")
async def post_lot_devis(did: str, body: Any = Body(default=None)):
    """Le coût du deck avant le tir — lignes à générer, pas cartes."""
    _guard(did)
    b = _obj(body)
    from . import face_lot
    try:
        return face_lot.devis(b.get("columns") or [], b.get("rows") or [],
                              str(b.get("model") or "flux"),
                              int(b.get("n") or 1), b.get("qty_col"),
                              b.get("art_col"))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/lot/prompts")
async def post_lot_prompts(did: str, body: Any = Body(default=None)):
    """Un prompt par ligne : la colonne, le style de série, la bible."""
    _guard(did)
    b = _obj(body)
    from . import face_lot
    try:
        return face_lot.prompts_lot(
            b.get("columns") or [], b.get("rows") or [],
            str(b.get("gabarit") or "{prompt}"), str(b.get("style") or ""),
            b.get("entites"), b.get("qty_col"), b.get("art_col"))
    except ValueError as e:
        raise HTTPException(400, str(e))
```

`lint_cardforge.py:137` : `"face": ["style_walkuski.py", "face_lot.py"]`.

> `_guard` et `_obj` : reprendre les helpers de `face.py` s'ils existent sous
> d'autres noms — `data.py:2097 _guard` / `2102 _obj` en donnent la forme. Ne pas
> en créer un deuxième jeu.

- [ ] **Step 5 : relancer**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_lot_art.py
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_face.py
cd ..
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" scripts/qa/lint_cardforge.py --module face
```

Attendu : `6 passed` ; `test_cards_face.py` vert ; lint `0`.

- [ ] **Step 6 : commit proposé**

```bash
git add backend/app/services/cards/face_lot.py backend/app/services/cards/face.py scripts/qa/lint_cardforge.py backend/tests/test_cards_lot_art.py
git commit -m 'cartes : le cout du deck avant le tir, et le prompt par ligne' -m 'Le devis compte les LIGNES et non les cartes : trois Colosses partagent une illustration, et facturer trois fois la même image serait l erreur la plus chère de tout ce plan. Aucun prix n est recalculé ici — pricing.estimate détient les tarifs par modèle, une seule table à tenir. Un prompt mêle la colonne, le style de série et la description de l entité de la bible, avec la planche de référence en pièce jointe ; une ligne sans rien n est pas inventée, elle est listée, parce que payer pour une image faite à partir de rien est un coût sans contrepartie.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Task 15 : Génération en lot, avec la lignée dans la Bibliothèque

**Files:**
- Modify: `backend/app/services/cards/face.py` (route `/lot/generer`)
- Modify: `backend/app/services/cards/face_lot.py`
- Modify: `frontend/cardforge/js/mod-face.js` (panneau « Art du deck »)
- Modify: `backend/tests/test_cards_lot_art.py`

**Coût de patch** : aucun. `library_index.noter(files, source="cardforge",
deck_id=…)` existe (`library_index.py:63`) et `SOURCES` (24) contient déjà
`"cardforge"` : **la lignée est gratuite**, il suffit de l'appeler.

- [ ] **Step 1 : écrire le banc qui échoue** (génération **stubée**)

```python
def test_la_generation_en_lot_ecrit_une_image_par_ligne_et_remplit_la_colonne(monkeypatch):
    from app.services.cards import face_lot as F
    tirs, notes = [], []

    async def faux_gen(prompt, n, **kw):
        tirs.append((prompt, n))
        return [f"gen_lot_{len(tirs)}.png"]

    async def faux_noter(files, source, **kw):
        notes.append((list(files), source, kw))

    monkeypatch.setattr(F, "_generer", faux_gen)
    monkeypatch.setattr(F, "_noter", faux_noter)

    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Lot2"})
            did = r.json()["deck"]["id"]
            return did, await c.post(f"/api/cards/{did}/face/lot/generer",
                                     json={"columns": COLS, "rows": ROWS,
                                           "qty_col": "qty", "model": "flux",
                                           "n": 1, "gabarit": "{prompt}",
                                           "style": "vitrail"}, timeout=120.0)
    did, r = asyncio.run(go())
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["generees"] == 3
    # LA COLONNE `art` EST RENDUE REMPLIE, la table source n'est pas touchée
    assert [x["ligne"] for x in j["resultats"]] == [1, 3, 4]
    assert all(x["fichier"].startswith("gen_lot_") for x in j["resultats"])
    # LA LIGNÉE : source « cardforge », deck_id du jeu
    assert len(notes) == 3, notes
    assert all(s == "cardforge" for _f, s, _k in notes)
    assert all(k.get("deck_id") == did for _f, _s, k in notes)
    # le style de série est dans CHAQUE prompt
    assert all("vitrail" in p for p, _n in tirs), tirs


def test_un_echec_de_generation_narrete_pas_le_lot_et_se_dit(monkeypatch):
    """Une ligne qui échoue au milieu d'un lot de 60 ne doit pas jeter les 59
    autres — l'utilisateur a déjà payé pour elles."""
    from app.services.cards import face_lot as F
    n = {"k": 0}

    async def faux_gen(prompt, nn, **kw):
        n["k"] += 1
        if n["k"] == 2:
            raise RuntimeError("le fournisseur a répondu 500")
        return [f"gen_{n['k']}.png"]

    monkeypatch.setattr(F, "_generer", faux_gen)
    monkeypatch.setattr(F, "_noter", lambda *a, **k: None)

    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Lot3"})
            did = r.json()["deck"]["id"]
            return await c.post(f"/api/cards/{did}/face/lot/generer",
                                json={"columns": COLS, "rows": ROWS,
                                      "qty_col": "qty", "model": "flux",
                                      "n": 1}, timeout=120.0)
    r = asyncio.run(go())
    j = r.json()
    assert j["generees"] == 2 and j["echecs"] == 1
    assert "500" in j["erreurs"][0]["message"]
    assert j["erreurs"][0]["ligne"] == 3


def test_le_lot_refuse_de_tirer_sil_reste_des_lignes_sans_prompt(monkeypatch):
    from app.services.cards import face_lot as F
    monkeypatch.setattr(F, "_generer",
                        lambda *a, **k: (_ for _ in ()).throw(
                            AssertionError("ne doit pas tirer")))

    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Lot4"})
            did = r.json()["deck"]["id"]
            return await c.post(f"/api/cards/{did}/face/lot/generer",
                                json={"columns": COLS, "rows": ROWS,
                                      "qty_col": "qty", "gabarit": "{prompt}"},
                                timeout=60.0)
    r = asyncio.run(go())
    assert r.status_code == 409, r.status_code
    assert "sans prompt" in r.text


def test_l_ecran_montre_le_devis_avant_le_bouton_et_grise_sans_cle():
    js = (pathlib.Path(__file__).resolve().parents[2] / "frontend" / "cardforge"
          / "js" / "mod-face.js").read_text(encoding="utf-8")
    assert 'M.api.post("lot/devis' in js
    assert 'data-act="lot-generer"' in js
    for phrase in ("ligne(s) à générer", "image(s)", "$",
                   "cartes couvertes", "Bibliothèque"):
        assert phrase in js, phrase
```

- [ ] **Step 2 : lancer, vérifier l'échec.**

- [ ] **Step 3 : compléter `face_lot.py` et la route**

```python
# ── LE TIR EN LOT ───────────────────────────────────────────────────────────
# Les deux points isolés (génération, lignée) : le banc les remplace, aucun
# test de ce dépôt n'appelle un fournisseur ni n'écrit dans l'index.
async def _generer(prompt: str, n: int, model: str = "flux",
                   seed: Any = None, references: Any = None) -> list:
    """LE SEUL point de dépense de cette pièce (règle 17 de la spec)."""
    from app.services import image_providers
    return await image_providers.generate(prompt=prompt, n=int(n),
                                          model=str(model), seed=seed,
                                          image_urls=list(references or []))


async def _noter(files, source: str, **kw) -> None:
    """LE SEUL point d'index. `SOURCES` contient déjà « cardforge »."""
    from app.services import library_index
    await library_index.noter(files, source, kind="image", **kw)


async def generer_lot(did: str, columns: list, rows: list, gabarit: str,
                      style: str, entites: Any, model: str, n: int,
                      qty_col: Any = None, art_col: Any = None) -> dict:
    """Le lot, ligne par ligne. UN ÉCHEC N'ARRÊTE PAS LE LOT : sur soixante
    lignes, jeter les cinquante-neuf réussies parce que la soixantième a
    échoué serait jeter de l'argent déjà dépensé."""
    lot = prompts_lot(columns, rows, gabarit, style, entites, qty_col, art_col)
    res, err = [], []
    for p in lot["prompts"]:
        try:
            noms = await _generer(p["prompt"], n, model, None, p["references"])
            fichier = (noms or [""])[0]
            res.append({"ligne": p["ligne"], "fichier": fichier,
                        "entite": p["entite"], "cartes": p["cartes"],
                        "prompt": p["prompt"]})
            if fichier:
                await _noter([fichier], "cardforge", deck_id=did)
        except Exception as e:                       # noqa: BLE001
            err.append({"ligne": p["ligne"], "message": str(e)})
    return {"generees": len(res), "echecs": len(err), "resultats": res,
            "erreurs": err, "lignes": lot["lignes"]}
```

> `image_providers.generate` : **relire sa signature exacte**
> (`backend/app/services/image_providers.py`) et l'appeler telle quelle. Si elle
> ne prend pas `image_urls`, passer les références par le paramètre qu'elle
> expose, ou les ignorer en le disant dans le commentaire — ne rien inventer.

La route dans `face.py` :

```python
@router.post("/lot/generer")
async def post_lot_generer(did: str, body: Any = Body(default=None)):
    """La génération en lot. Refuse (409) tant qu'une ligne n'a pas de
    prompt : payer pour une image faite à partir de rien est un coût sans
    contrepartie, et l'écran a déjà montré lesquelles."""
    _guard(did)
    b = _obj(body)
    from . import face_lot
    try:
        lot = face_lot.prompts_lot(
            b.get("columns") or [], b.get("rows") or [],
            str(b.get("gabarit") or "{prompt}"), str(b.get("style") or ""),
            b.get("entites"), b.get("qty_col"), b.get("art_col"))
    except ValueError as e:
        raise HTTPException(400, str(e))
    if lot["incomplets"] and not b.get("forcer"):
        lignes = ", ".join(str(p["ligne"]) for p in lot["prompts"]
                           if p["manque"])[:120]
        raise HTTPException(
            409, f"{lot['incomplets']} ligne(s) sans prompt (lignes {lignes}) : "
                 f"complétez la colonne, ou relancez en forçant.")
    try:
        return await face_lot.generer_lot(
            did, b.get("columns") or [], b.get("rows") or [],
            str(b.get("gabarit") or "{prompt}"), str(b.get("style") or ""),
            b.get("entites"), str(b.get("model") or "flux"),
            max(1, min(4, int(b.get("n") or 1))),
            b.get("qty_col"), b.get("art_col"))
    except Exception as e:
        logger.exception("cards/face: lot impossible")
        raise HTTPException(502, f"Génération en lot impossible: {e}")
```

- [ ] **Step 4 : le panneau « Art du deck » dans `mod-face.js`**

```js
  /* ══ ART DU DECK (D1) ════════════════════════════════════════════════════
     LE DEVIS AVANT LE BOUTON. Le depot compte la depense a un seul endroit
     (regle 17) ; ici on la MONTRE avant de la faire, avec ce qu'elle couvre :
     lignes a generer, images, cartes couvertes, dollars. */
  async function lotDevis() {
    const d = CF.doc().data || {};
    const box = HOST.querySelector("#cf-face-lot-devis");
    if (!box) return;
    try {
      const r = await M.api.post("lot/devis", { columns: d.columns,
        rows: d.rows, qty_col: d.qty_col, model: CF.get("face.lot_model",
          "flux"), n: CF.get("face.lot_n", 1) });
      box.innerHTML =
        "<b>" + r.lignes_a_generer + " ligne(s) à générer</b> · "
        + r.images + " image(s) · " + r.cartes_couvertes
        + " cartes couvertes · " + r.deja_illustrees
        + " déjà illustrée(s)<br><b>" + r.total_usd.toFixed(3) + " $</b> "
        + "(modèle " + esc(r.model) + ") — les images rejoindront la "
        + "<b>Bibliothèque</b> avec la lignée de ce jeu.";
    } catch (e) {
      if (!(e && e.missing)) console.warn("cardforge/face: devis", e);
    }
  }
```

Bouton `data-act="lot-generer"`, appel de `lotDevis()` à chaque changement de
modèle, de `n` ou de table. Après le lot, écrire la colonne `art` par la plume
de la grille (pièce 04) via un événement `M.emit("lot-fait", {resultats})` que
`mod-data.js` écoute — **jamais** un `M.patch` sur `doc.data` depuis `face`
(la règle 2 lèverait).

- [ ] **Step 5 : relancer**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_lot_art.py
```

Attendu : `10 passed`. **Aucun appel fournisseur, aucune écriture d'index** :
`_generer` et `_noter` sont remplacés.

- [ ] **Step 6 : commit proposé**

```bash
git add backend/app/services/cards/face_lot.py backend/app/services/cards/face.py frontend/cardforge/js/mod-face.js backend/tests/test_cards_lot_art.py
git commit -m 'cartes : la generation en lot, avec la lignee dans la Bibliotheque' -m 'Un échec au milieu d un lot de soixante ne jette pas les cinquante-neuf réussies : elles sont déjà payées, et la ligne fautive est nommée avec le message du fournisseur. Le tir est refusé tant qu une ligne n a pas de prompt — payer pour une image faite à partir de rien est un coût sans contrepartie. La lignée ne coûte rien : library_index connaît déjà la source cardforge et le deck_id, il suffisait de l appeler. La colonne art est réécrite par la plume de la pièce 04, jamais par un patch venu de la pièce 01 : la règle 2 lèverait, et elle a raison.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Task 16 : Jetons et pions extrudés depuis une carte ou une entité

**Files:**
- Create: `backend/app/services/cards/forge3d_jeu.py`
- Modify: `backend/app/services/cards/forge3d.py:157-170` (`NODE_KINDS`)
- Modify: `scripts/qa/lint_cardforge.py:137` (`EXTRA_PY["forge3d"]`)
- Create: `backend/tests/test_cards_jeu3d.py`

**Coût de patch** : aucun côté bundle. Un troisième sidecar pour `forge3d` (il en a
déjà deux, `forge3d_scene.py` et `forge3d_apercu.py`).

**Lien, sans replanifier** : l'écriture STL/3MF est celle de `print3d`
(`creer_export`, `print3d.py:317`), avec sa garde de plateau **256 mm** qui
**avertit sans interdire** (`print3d.py:338-346`) — c'est le bac **R10f**. Ce plan
appelle, il ne réécrit pas.

- [ ] **Step 1 : écrire le banc qui échoue**

Créer `backend/tests/test_cards_jeu3d.py` (même en-tête), puis :

```python
import math                                                      # noqa: E402
from app.services.cards import forge3d_jeu as J                  # noqa: E402
from app.services import print3d                                 # noqa: E402


def test_un_jeton_rond_a_la_bonne_hauteur_et_le_bon_diametre():
    tris = J.jeton(diam_mm=25.0, ep_mm=3.0, cotes=64)
    (x0, x1), (y0, y1), (z0, z1) = print3d.bbox(tris)
    assert abs((x1 - x0) - 25.0) < 0.05, (x0, x1)
    assert abs((y1 - y0) - 25.0) < 0.05, (y0, y1)
    assert abs((z1 - z0) - 3.0) < 1e-6, (z0, z1)
    # 64 côtés : 2 x 64 pour les deux faces, 2 x 64 pour la tranche
    assert len(tris) == 4 * 64, len(tris)


def test_un_jeton_est_ferme_donc_imprimable():
    """« Fermé » n'est pas un avis : chaque arête doit être vue DEUX fois, une
    fois dans chaque sens. Un solide ouvert sort en bouillie du slicer."""
    tris = J.jeton(diam_mm=20.0, ep_mm=2.0, cotes=32)
    aretes = {}
    for t in tris:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            k = (tuple(round(c, 6) for c in a), tuple(round(c, 6) for c in b))
            aretes[k] = aretes.get(k, 0) + 1
    ouvertes = [k for k in aretes
                if aretes.get((k[1], k[0]), 0) != aretes[k]]
    assert not ouvertes, len(ouvertes)


def test_un_pion_repose_sur_le_plateau_a_z_egal_zero():
    """Un modèle qui flotte ou qui plonge sous le plateau est refusé par tous
    les slicers, et c'est la première chose qu'un débutant ne voit pas."""
    for tris in (J.jeton(20.0, 2.0, 24), J.pion(18.0, 22.0, 3.0, 24)):
        (_x, _X), (_y, _Y), (z0, _z1) = print3d.bbox(tris)
        assert abs(z0) < 1e-9, z0


def test_le_diametre_dun_jeton_est_borne_et_le_refus_donne_les_bornes():
    for mauvais in ((0.0, 3.0), (400.0, 3.0), (25.0, 0.0), (25.0, 60.0)):
        with pytest.raises(ValueError) as e:
            J.jeton(mauvais[0], mauvais[1], 32)
        assert "mm" in str(e.value) and "entre" in str(e.value), mauvais


def test_les_trois_noeuds_du_jeu_entrent_dans_le_graphe():
    from app.services.cards import forge3d as F
    kinds = {k["kind"] for k in F.NODE_KINDS}
    assert {"jeton", "boite", "presentoir"} <= kinds, sorted(kinds)
    jeton = [k for k in F.NODE_KINDS if k["kind"] == "jeton"][0]
    assert set(jeton["params"]) == {"forme", "diam_mm", "ep_mm", "cotes"}


def test_la_route_ecrit_un_STL_relu_sur_le_disque(tmp_path):
    """BANC-MIROIR : on relit le STL ÉCRIT, pas le tableau qui l'a produit."""
    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Jetons"})
            did = r.json()["deck"]["id"]
            return await c.post(f"/api/cards/{did}/forge3d/jeu", json={
                "objet": "jeton", "diam_mm": 25, "ep_mm": 3, "cotes": 48,
                "nom": "jeton mana"})
    r = asyncio.run(go())
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["triangles"] == 4 * 48
    from app.config import settings
    p = (settings.outputs_path / "print3d" / j["dossier"] / j["stl"])
    assert p.is_file(), p
    relu = print3d.lire_stl(p.read_bytes())
    (x0, x1), _y, (z0, z1) = print3d.bbox(relu)[0], None, print3d.bbox(relu)[2]
    assert abs((x1 - x0) - 25.0) < 0.05
    assert abs((z1 - z0) - 3.0) < 1e-6
```

- [ ] **Step 2 : lancer, vérifier l'échec.**

- [ ] **Step 3 : écrire `forge3d_jeu.py`**

```python
# -*- coding: utf-8 -*-
"""Card Forge — pièce 09, sidecar « objets du jeu ».

SIDECAR : aucun `router` (règle 8). De la géométrie en millimètres, rien
d'autre — l'écriture STL/3MF appartient à `print3d` (garde de plateau
256 mm de la Centauri Carbon 2, qui AVERTIT sans interdire : couper est le
métier du slicer).

DEUX RÈGLES, ET ELLES SONT MÉCANIQUES :
  1. TOUT SOLIDE EST FERMÉ. Chaque arête est vue deux fois, une fois dans
     chaque sens ; un solide ouvert sort en bouillie du trancheur, et le banc
     le compte plutôt que de le croire.
  2. TOUT REPOSE À z = 0. Un modèle qui flotte est refusé par tous les
     slicers, et c'est la première chose qu'un débutant ne voit pas.

`numpy` est ABSENT (mesuré) : trigonométrie stdlib, listes de triangles —
la même forme que `print3d.lire_glb_triangles`, [[x,y,z] x 3].
"""
from __future__ import annotations

import math

__all__ = ["DIAM_MM", "EP_MM", "COTES", "jeton", "pion", "presentoir"]

DIAM_MM = (5.0, 300.0)     # bornes d'un jeton, en millimètres
EP_MM = (0.6, 50.0)        # épaisseur : sous 0,6 mm, une buse de 0,4 ne tient pas
COTES = (8, 256)


def _borne(v, lo_hi, quoi: str) -> float:
    lo, hi = lo_hi
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{quoi} doit être un nombre de millimètres")
    if not math.isfinite(x) or x < lo or x > hi:
        raise ValueError(f"{quoi} doit tenir entre {lo:g} et {hi:g} mm "
                         f"(reçu {v!r})")
    return x


def _prisme(profil: list[tuple[float, float]], ep: float) -> list:
    """Un profil fermé (dans le plan XY, sens direct) extrudé de `ep` en Z,
    POSÉ À z = 0. Rend une liste de triangles [[x,y,z] x 3], fermée.

    Les deux couvercles sont triangulés en éventail depuis le centroïde —
    valable parce que tous les profils de ce fichier sont convexes (disque,
    polygone régulier, rectangle). Un profil concave demanderait une vraie
    triangulation : ce fichier n'en produit pas, et le dit.
    """
    n = len(profil)
    cx = sum(p[0] for p in profil) / n
    cy = sum(p[1] for p in profil) / n
    tris = []
    for i in range(n):
        x0, y0 = profil[i]
        x1, y1 = profil[(i + 1) % n]
        # dessous : normale vers -Z, donc sens horaire vu de dessus
        tris.append([[cx, cy, 0.0], [x1, y1, 0.0], [x0, y0, 0.0]])
        # dessus : normale vers +Z
        tris.append([[cx, cy, ep], [x0, y0, ep], [x1, y1, ep]])
        # tranche : deux triangles, orientés vers l'extérieur
        tris.append([[x0, y0, 0.0], [x1, y1, 0.0], [x1, y1, ep]])
        tris.append([[x0, y0, 0.0], [x1, y1, ep], [x0, y0, ep]])
    return tris


def _cercle(diam: float, cotes: int) -> list[tuple[float, float]]:
    r = diam / 2.0
    return [(r * math.cos(2 * math.pi * k / cotes),
             r * math.sin(2 * math.pi * k / cotes)) for k in range(cotes)]


def jeton(diam_mm: float = 25.0, ep_mm: float = 3.0,
          cotes: int = 64) -> list:
    """Un jeton rond (ou polygonal si `cotes` est petit), posé à z = 0."""
    d = _borne(diam_mm, DIAM_MM, "Le diamètre du jeton")
    e = _borne(ep_mm, EP_MM, "L'épaisseur du jeton")
    c = int(_borne(cotes, COTES, "Le nombre de côtés"))
    return _prisme(_cercle(d, c), e)


def pion(diam_bas_mm: float = 18.0, diam_haut_mm: float = 22.0,
         ep_mm: float = 3.0, cotes: int = 48) -> list:
    """Un pion : deux disques de diamètres différents, empilés. Le socle plus
    étroit que la tête tient debout et s'attrape ; l'inverse bascule."""
    db = _borne(diam_bas_mm, DIAM_MM, "Le diamètre du socle")
    dh = _borne(diam_haut_mm, DIAM_MM, "Le diamètre de la tête")
    e = _borne(ep_mm, EP_MM, "L'épaisseur d'un étage")
    c = int(_borne(cotes, COTES, "Le nombre de côtés"))
    bas = _prisme(_cercle(db, c), e)
    haut = [[[x, y, z + e] for x, y, z in t] for t in _prisme(_cercle(dh, c), e)]
    return bas + haut


def presentoir(largeur_mm: float, profondeur_mm: float, ep_mm: float = 4.0,
               rainure_mm: float = 1.2, cotes: int = 4) -> list:
    """Un présentoir : une plaque avec une rainure où poser les cartes.

    La rainure fait `rainure_mm` de large — l'épaisseur d'une carte plus le
    jeu d'impression. Sous 0,8 mm, une buse de 0,4 mm ne creuse rien de
    propre : la borne le dit.
    """
    L = _borne(largeur_mm, (20.0, 300.0), "La largeur du présentoir")
    P = _borne(profondeur_mm, (15.0, 300.0), "La profondeur du présentoir")
    E = _borne(ep_mm, (2.0, 50.0), "L'épaisseur du présentoir")
    R = _borne(rainure_mm, (0.8, 10.0), "La largeur de la rainure")
    # Deux plaques séparées par la rainure : le résultat est fermé, et deux
    # solides disjoints sont légaux en STL comme en 3MF.
    d = (P - R) / 2.0
    if d <= 1.0:
        raise ValueError("La rainure ne laisse pas 1 mm de matière de chaque "
                         "côté : réduisez-la ou augmentez la profondeur.")
    avant = _prisme([(0.0, 0.0), (L, 0.0), (L, d), (0.0, d)], E)
    arriere = [[[x, y + d + R, z] for x, y, z in t]
               for t in _prisme([(0.0, 0.0), (L, 0.0), (L, d), (0.0, d)], E)]
    return avant + arriere
```

- [ ] **Step 4 : les nœuds et la route dans `forge3d.py`**

Ajouter à `NODE_KINDS` (`forge3d.py:157-170`), avant `{"kind": "export"}` :

```python
    # ── OBJETS DU JEU (D2) : ils ne dérivent pas d'une couche, ils sortent
    # d'un profil en millimètres. `print3d` les écrit, garde de plateau
    # comprise (256 mm, avertit sans interdire).
    {"kind": "jeton", "params": ["forme", "diam_mm", "ep_mm", "cotes"]},
    {"kind": "boite", "params": ["largeur_mm", "hauteur_mm", "profondeur_mm",
                                 "rabat_mm"]},
    {"kind": "presentoir", "params": ["largeur_mm", "profondeur_mm", "ep_mm",
                                      "rainure_mm"]},
```

La route :

```python
@router.post("/jeu")
async def post_jeu(did: str, body: Any = Body(default=None)):
    """Un objet du jeu, écrit en STL + 3MF par `print3d` — la garde de
    plateau de la Centauri Carbon 2 avertit, elle n'interdit pas."""
    _guard(did)
    b = _obj(body)
    from app.config import settings
    from app.services import print3d
    from . import forge3d_jeu as JEU
    objet = str(b.get("objet") or "").strip().lower()
    fabriques = {
        "jeton": lambda: JEU.jeton(b.get("diam_mm", 25.0), b.get("ep_mm", 3.0),
                                   int(b.get("cotes") or 64)),
        "pion": lambda: JEU.pion(b.get("diam_bas_mm", 18.0),
                                 b.get("diam_haut_mm", 22.0),
                                 b.get("ep_mm", 3.0), int(b.get("cotes") or 48)),
        "presentoir": lambda: JEU.presentoir(
            b.get("largeur_mm", 90.0), b.get("profondeur_mm", 40.0),
            b.get("ep_mm", 4.0), b.get("rainure_mm", 1.2)),
    }
    if objet not in fabriques:
        raise HTTPException(400, "Objet inconnu: %r. Objets admis: %s"
                                 % (objet, ", ".join(fabriques)))
    try:
        tris = await asyncio.to_thread(fabriques[objet])
    except ValueError as e:
        raise HTTPException(400, str(e))
    try:
        out = await asyncio.to_thread(
            print3d.creer_export, settings.outputs_path / "print3d",
            str(b.get("nom") or objet), tris, None,
            f"cardforge/{did}/{objet}", "fermee")
    except Exception as e:
        logger.exception("cards/forge3d: écriture de l'objet impossible")
        raise HTTPException(500, f"Écriture impossible: {e}")
    return out
```

`lint_cardforge.py:137` : `"forge3d": ["forge3d_scene.py", "forge3d_apercu.py",
"forge3d_jeu.py"]`.

- [ ] **Step 5 : relancer**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_jeu3d.py
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_forge3d.py
cd ..
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" scripts/qa/lint_cardforge.py --module forge3d
```

Attendu : `6 passed` ; `test_cards_forge3d.py` vert ; lint `0`.

- [ ] **Step 6 : commit proposé**

```bash
git add backend/app/services/cards/forge3d_jeu.py backend/app/services/cards/forge3d.py scripts/qa/lint_cardforge.py backend/tests/test_cards_jeu3d.py
git commit -m 'cartes : jetons, pions et presentoir, en millimetres et fermes' -m 'Deux règles mécaniques, pas deux intentions : tout solide est FERMÉ — chaque arête vue deux fois, une fois dans chaque sens, et le banc les compte au lieu de le croire — et tout repose à z = 0, parce qu un modèle qui flotte est refusé par tous les slicers et que c est la première chose qu un débutant ne voit pas. Les couvercles sont triangulés en éventail, ce qui n est valable que sur des profils convexes : ce fichier n en produit pas d autres, et il le dit. L écriture reste celle de print3d, garde de plateau de 256 mm comprise, qui avertit sans interdire — couper est le métier du slicer.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Task 17 : La boîte dépliée en PDF, avec ses plis, aux dimensions du deck

**Files:**
- Modify: `backend/app/services/cards/forge3d_jeu.py` (patron de la boîte)
- Modify: `backend/app/services/cards/forge3d.py` (route `/boite`)
- Modify: `backend/tests/test_cards_jeu3d.py`

**Coût de patch** : aucun. Le PDF est écrit par pypdf, comme le reste
(cf. « Décision : écrire un PDF sans une dépendance de plus »).

- [ ] **Step 1 : écrire le banc qui échoue**

```python
def test_le_patron_de_boite_est_aux_dimensions_du_deck_plus_le_jeu():
    """Une boîte à la taille EXACTE du deck ne se ferme pas : le carton a une
    épaisseur, et l'impression une tolérance. Le jeu est explicite."""
    from app.services.cards import forge3d_jeu as J
    p = J.patron_boite(largeur_mm=63.0, hauteur_mm=88.0, epaisseur_deck_mm=20.0,
                       jeu_mm=1.0, rabat_mm=15.0)
    assert p["boite_mm"] == [64.0, 89.0, 21.0]
    # développé : 2*(l+e) de large, h + 2 rabats de haut
    assert round(p["feuille_mm"][0], 3) == round(2 * (64.0 + 21.0), 3)
    assert round(p["feuille_mm"][1], 3) == round(89.0 + 2 * 15.0, 3)
    assert p["plis"] and all(len(t) == 4 for t in p["plis"])


def test_la_boite_refuse_de_depasser_la_feuille_et_le_dit():
    from app.services.cards import forge3d_jeu as J
    with pytest.raises(ValueError) as e:
        J.patron_boite(200.0, 280.0, 60.0, 1.0, 20.0, feuille="a4")
    assert "A4" in str(e.value) and "mm" in str(e.value)
    assert "A3" in str(e.value), "l'erreur propose la feuille qui tiendrait"


def test_le_pdf_de_la_boite_trace_les_plis_en_pointilles_et_les_coupes_pleines():
    """Un patron où l'on ne distingue pas un pli d'une coupe se découpe
    faux : le trait plein se coupe, le pointillé se plie, et la légende le
    dit sur la feuille."""
    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Boite"})
            did = r.json()["deck"]["id"]
            await c.patch(f"/api/cards/{did}",
                          json={"format": {"fmt": "poker_eu", "dpi": 300}})
            return await c.post(f"/api/cards/{did}/forge3d/boite",
                                json={"cartes": 60, "feuille": "a4"})
    r = asyncio.run(go())
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    from pypdf import PdfReader
    rd = PdfReader(io.BytesIO(r.content))
    assert len(rd.pages) == 1
    box = [round(float(v), 2) for v in rd.pages[0].mediabox]
    assert box == [0.0, 0.0, 595.2, 841.92], box
    flux = rd.pages[0].get_contents().get_data()
    assert b" d\n" in flux or b"] 0 d" in flux, "des pointillés pour les plis"
    assert flux.count(b" l S") >= 8, flux.count(b" l S")
    assert r.headers["X-CF-Boite-Mm"].count("x") == 2
    assert r.headers["X-CF-Cartes"] == "60"


def test_l_epaisseur_du_deck_vient_de_la_piece_05_et_non_dun_chiffre_devine():
    """0,32 mm par carte est l'épaisseur RÉGLÉE dans la pièce 05
    (contract.THICKNESS_MM_DEFAULT) : la boîte lit cette valeur."""
    from app.services.cards import contract as CT
    from app.services.cards import forge3d_jeu as J
    e = J.epaisseur_deck_mm(60, CT.THICKNESS_MM_DEFAULT)
    assert abs(e - 60 * 0.32) < 1e-9
```

- [ ] **Step 2 : lancer, vérifier l'échec.**

- [ ] **Step 3 : écrire le patron dans `forge3d_jeu.py`**

```python
# ── LA BOÎTE (D2) ───────────────────────────────────────────────────────────
# Une tuck box à la taille EXACTE du deck ne se ferme pas : le carton a une
# épaisseur et l'impression une tolérance. Le jeu est donc EXPLICITE, réglable,
# et il apparaît dans le manifeste — un chiffre caché ici coûterait une boîte
# imprimée pour rien.
JEU_MM_DEFAUT = 1.0
RABAT_MM_DEFAUT = 15.0
FEUILLES_MM = {"a4": (210.0, 297.0), "letter": (215.9, 279.4),
               "a3": (297.0, 420.0)}


def epaisseur_deck_mm(cartes: int, ep_carte_mm: float) -> float:
    """L'épaisseur d'un paquet. `ep_carte_mm` vient de la pièce 05
    (`contract.THICKNESS_MM_DEFAULT` = 0,32 mm) : on ne devine pas."""
    return max(0.0, int(cartes)) * float(ep_carte_mm)


def patron_boite(largeur_mm: float, hauteur_mm: float,
                 epaisseur_deck_mm: float, jeu_mm: float = JEU_MM_DEFAUT,
                 rabat_mm: float = RABAT_MM_DEFAUT,
                 feuille: str = "a4") -> dict:
    """Le développé d'une tuck box. -> {boite_mm, feuille_mm, coupes, plis}.

    `coupes` et `plis` sont des segments [x0, y0, x1, y1] en millimètres,
    origine en bas à gauche du développé. Le trait PLEIN se coupe, le
    POINTILLÉ se plie : un patron où l'on ne distingue pas les deux se
    découpe faux, et la feuille porte la légende.
    """
    L = float(largeur_mm) + float(jeu_mm)
    H = float(hauteur_mm) + float(jeu_mm)
    E = float(epaisseur_deck_mm) + float(jeu_mm)
    R = float(rabat_mm)
    fw, fh = FEUILLES_MM.get(str(feuille).lower(), FEUILLES_MM["a4"])
    dw, dh = 2.0 * (L + E), H + 2.0 * R
    if dw > fw or dh > fh:
        plus_grande = next((n for n, (w, h) in FEUILLES_MM.items()
                            if dw <= w and dh <= h), "")
        raise ValueError(
            "Le développé fait %.1f x %.1f mm et ne tient pas sur %s "
            "(%.1f x %.1f mm)%s."
            % (dw, dh, str(feuille).upper(), fw, fh,
               " — %s conviendrait" % plus_grande.upper() if plus_grande
               else " ; aucune feuille du catalogue ne convient"))
    # quatre panneaux : L, E, L, E ; deux rabats en haut et en bas
    x = [0.0, L, L + E, 2.0 * L + E, dw]
    y0, y1 = R, R + H
    coupes = [[0.0, y0, 0.0, y1], [dw, y0, dw, y1],
              [0.0, y0, dw, y0], [0.0, y1, dw, y1],
              [0.0, 0.0, dw, 0.0], [0.0, dh, dw, dh],
              [0.0, 0.0, 0.0, y0], [dw, 0.0, dw, y0],
              [0.0, y1, 0.0, dh], [dw, y1, dw, dh]]
    plis = [[v, y0, v, y1] for v in x[1:4]]
    plis += [[0.0, y0, dw, y0], [0.0, y1, dw, y1]]
    return {"boite_mm": [round(L, 3), round(H, 3), round(E, 3)],
            "feuille_mm": [round(dw, 3), round(dh, 3)],
            "feuille": str(feuille).lower(),
            "jeu_mm": float(jeu_mm), "rabat_mm": R,
            "coupes": coupes, "plis": plis}
```

- [ ] **Step 4 : le PDF, dans `forge3d.py`**

```python
@router.post("/boite")
async def post_boite(did: str, body: Any = Body(default=None)):
    """Le patron de la boîte, en PDF vectoriel : trait plein = coupe,
    pointillé = pli, légende sur la feuille."""
    _guard(did)
    b = _obj(body)
    doc = _deck(did)
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, NameObject
    from . import contract
    from . import forge3d_jeu as JEU
    from . import print as print_mod          # helpers PURS : mm2pt, text_paths
    g = contract.geom((doc.get("format") or {}).get("fmt")
                      or contract.DEFAULT_FMT, 300)
    ep = float((doc.get("solid") or {}).get("thickness_mm")
               or contract.THICKNESS_MM_DEFAULT)
    cartes = max(1, min(1000, int(b.get("cartes") or 60)))
    feuille = str(b.get("feuille") or "a4").lower()
    try:
        pat = JEU.patron_boite(
            g.trim_mm[0], g.trim_mm[1], JEU.epaisseur_deck_mm(cartes, ep),
            float(b.get("jeu_mm", JEU.JEU_MM_DEFAUT)),
            float(b.get("rabat_mm", JEU.RABAT_MM_DEFAUT)), feuille)
    except ValueError as e:
        raise HTTPException(400, str(e))

    def work():
        fw, fh = JEU.FEUILLES_MM[feuille]
        W, H = print_mod.mm2pt(fw), print_mod.mm2pt(fh)
        ox = (W - print_mod.mm2pt(pat["feuille_mm"][0])) / 2.0
        oy = (H - print_mod.mm2pt(pat["feuille_mm"][1])) / 2.0

        def seg(s):
            return ("%.4f %.4f m %.4f %.4f l S"
                    % (ox + print_mod.mm2pt(s[0]), oy + print_mod.mm2pt(s[1]),
                       ox + print_mod.mm2pt(s[2]), oy + print_mod.mm2pt(s[3]))
                    ).encode("ascii")
        ops = [b"0 G", b"0.6 w", b"[] 0 d"]
        ops += [seg(s) for s in pat["coupes"]]
        ops += [b"0.4 w", b"[3 2] 0 d"]          # POINTILLE = PLI
        ops += [seg(s) for s in pat["plis"]]
        ops += [b"[] 0 d"]
        legende = ("trait plein = couper - pointille = plier - boite %s mm"
                   % "x".join("%.1f" % v for v in pat["boite_mm"]))
        ops.append(print_mod.text_paths(
            print_mod.slug_chars(legende), print_mod.mm2pt(10.0),
            H - print_mod.mm2pt(10.0), print_mod.mm2pt(3.0)))
        w = PdfWriter()
        w.pdf_header = "%PDF-1.4"
        page = w.add_blank_page(width=W, height=H)
        st = DecodedStreamObject()
        st.set_data(b"\n".join(ops))
        page[NameObject("/Contents")] = w._add_object(st)
        buf = io.BytesIO()
        w.write(buf)
        return buf.getvalue()

    try:
        out = await asyncio.to_thread(work)
    except Exception as e:
        logger.exception("cards/forge3d: patron de boîte impossible")
        raise HTTPException(500, f"Patron impossible: {e}")
    return Response(content=out, media_type="application/pdf", headers={
        "Content-Disposition": 'attachment; filename="boite.pdf"',
        "X-CF-Boite-Mm": "x".join("%.1f" % v for v in pat["boite_mm"]),
        "X-CF-Feuille-Mm": "x".join("%.1f" % v for v in pat["feuille_mm"]),
        "X-CF-Cartes": str(cartes),
        "X-CF-Jeu-Mm": "%.2f" % pat["jeu_mm"],
    })
```

> `print_mod.mm2pt`, `text_paths` et `slug_chars` sont des fonctions **pures** de
> `print.py` (347, 469, 456) : les importer ne viole pas la règle 8, qui interdit
> d'importer le **router** d'une autre pièce. Le lint le vérifie sur `.router`
> exactement. Si l'on préfère zéro couplage, recopier `mm2pt` (une ligne) —
> mais **pas** `text_paths`, qui porte la fonte de trait.

- [ ] **Step 5 : relancer**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_jeu3d.py
cd ..
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" scripts/qa/lint_cardforge.py --module forge3d
```

Attendu : `10 passed` ; lint `0`.

- [ ] **Step 6 : commit proposé**

```bash
git add backend/app/services/cards/forge3d_jeu.py backend/app/services/cards/forge3d.py backend/tests/test_cards_jeu3d.py
git commit -m 'cartes : la boite depliee, aux dimensions du deck plus le jeu' -m 'Une boîte à la taille exacte du deck ne se ferme pas : le carton a une épaisseur et l impression une tolérance. Le jeu est donc explicite, réglable et écrit dans l en-tête — un chiffre caché ici coûterait une boîte imprimée pour rien. L épaisseur du paquet vient de la pièce 05 (0,32 mm par carte) et non d un nombre deviné. Le trait plein se coupe, le pointillé se plie, et la légende est sur la feuille : un patron où l on ne distingue pas les deux se découpe faux. Un développé trop grand est refusé en proposant la feuille qui conviendrait.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Task 18 : Le livret de règles en PDF

**Files:**
- Create: `backend/app/services/cards/edition_livret.py`
- Modify: `backend/app/services/cards/edition.py` (route `/livret`)
- Modify: `frontend/cardforge/js/mod-edition.js`
- Modify: `backend/tests/test_cards_edition.py`

**Coût de patch** : aucun. Le sidecar est déjà déclaré dans `EXTRA_PY` (T5).

**La décision de forme, dite avant le code** : un livret demande du **vrai texte**,
et `print.py` n'embarque **aucune police** (le cartouche est tracé en chemins par
`glyph`/`text_paths`). Trois options :

| option | coût | verdict |
|---|---|---|
| Embarquer une TTF dans le PDF (`/FontFile2` + largeurs + CMap, à la main) | élevé, et il faudrait le refaire pour chaque fonte des 23 servies | écarté pour ce lot |
| `reportlab` | **ABSENT** du runtime (T1) | écarté |
| **Pages composées par PIL à 300 DPI (`ImageFont` sur les fontes de `/fonts/`), puis assemblées en PDF par PIL + pypdf** | nul : les deux sont présents et déjà utilisés | **retenu** |

**L'écart, marqué** : le texte du livret n'est **pas sélectionnable** et n'a **pas de
couche OCR** — c'est une image de page à 300 DPI. Pour un livret imprimé c'est sans
conséquence ; pour un PDF lu à l'écran, c'en est une, et l'écran le dit.

- [ ] **Step 1 : écrire le banc qui échoue**

```python
# ─────────────────────── T18 : le livret de règles ──────────────────────────
def test_le_livret_pagine_le_texte_et_rend_le_bon_nombre_de_pages():
    from app.services.cards import edition_livret as L
    txt = "\n\n".join("Paragraphe %d. %s" % (i, "mot " * 60) for i in range(20))
    pages = L.paginer(txt, largeur_px=1800, hauteur_px=2600, cap_px=34,
                      interligne=1.45, marge_px=180)
    assert len(pages) >= 3, len(pages)
    assert all(isinstance(p, list) and p for p in pages)
    # AUCUN MOT PERDU : la pagination coupe, elle ne jette pas
    rendu = " ".join(" ".join(l for l in p) for p in pages)
    assert rendu.count("Paragraphe 0.") == 1
    assert rendu.count("Paragraphe 19.") == 1


def test_un_mot_plus_long_que_la_ligne_est_coupe_et_non_perdu():
    from app.services.cards import edition_livret as L
    pages = L.paginer("A" * 400, largeur_px=600, hauteur_px=900, cap_px=40,
                      interligne=1.4, marge_px=40)
    joint = "".join("".join(p) for p in pages)
    assert joint.count("A") == 400, joint.count("A")


def test_le_livret_est_un_PDF_a_la_bonne_page_et_porte_les_cartes_demandees():
    """BANC-MIROIR : on relit le PDF ÉCRIT."""
    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Règles"})
            did = r.json()["deck"]["id"]
            g = CT.geom("poker_us", 300)
            files = [("images", ("c1.png", _png(*g.canvas_px), "image/png"))]
            return await c.post(f"/api/cards/{did}/edition/livret",
                                data={"spec": json.dumps({
                                    "titre": "Règles du jeu",
                                    "texte": "But du jeu.\n\n" + "mot " * 900,
                                    "sheet": "a5"})},
                                files=files, timeout=180.0)
    r = asyncio.run(go())
    assert r.status_code == 200, r.text
    from pypdf import PdfReader
    rd = PdfReader(io.BytesIO(r.content))
    assert len(rd.pages) >= 2
    # A5 à 300 DPI : 1748 x 2480 px -> 419,52 x 595,2 pt
    box = [round(float(v), 2) for v in rd.pages[0].mediabox]
    assert box == [0.0, 0.0, 419.52, 595.2], box
    assert int(r.headers["X-CF-Pages"]) == len(rd.pages)
    assert r.headers["X-CF-Images"] == "1"
    # L'ÉCART EST DIT PAR LE FICHIER QUI PART, pas seulement par l'écran
    assert r.headers["X-CF-Texte"] == "raster"


def test_l_ecart_du_livret_est_ecrit_a_l_ecran_et_non_seulement_en_commentaire():
    js = (FRONT / "js" / "mod-edition.js").read_text(encoding="utf-8")
    for phrase in ("texte n’est pas sélectionnable", "300 DPI",
                   "pour l’impression"):
        assert phrase in js, phrase
```

- [ ] **Step 2 : lancer, vérifier l'échec.**

- [ ] **Step 3 : écrire `edition_livret.py`**

```python
# -*- coding: utf-8 -*-
"""Card Forge — pièce 11, sidecar « livret, mockup, fiche produit ».

SIDECAR : aucun `router` (règle 8).

LA DÉCISION DE FORME, ÉCRITE ICI POUR NE PAS SE REPERDRE : un livret demande
du VRAI texte, et `print.py` n'embarque aucune police (son cartouche est tracé
en chemins). `reportlab` est ABSENT du runtime embarqué (mesuré le 03/09/2026).
Embarquer une TrueType dans le PDF à la main (/FontFile2, largeurs, CMap) est
faisable mais serait à refaire pour chacune des 23 fontes servies.

On compose donc les pages avec PIL à 300 DPI, avec les fontes réelles de
`/fonts/`, et on les assemble en PDF. L'ÉCART EST DIT, à l'écran ET dans
l'en-tête du fichier : le texte n'est PAS sélectionnable et n'a PAS de couche
OCR. Pour un livret imprimé c'est sans conséquence ; pour un PDF lu à l'écran,
c'en est une.
"""
from __future__ import annotations

import io
import math

from PIL import Image, ImageDraw, ImageFont

__all__ = ["FEUILLES_PX", "police", "paginer", "composer_page",
           "build_livret"]

# Feuilles du livret, en pixels à 300 DPI (même règle d'arrondi que le
# contrat : R(mm / 25.4 * dpi) — recopiée d'un bloc, pas dérivée).
FEUILLES_PX = {"a5": (1748, 2480), "a4": (2480, 3508),
               "carre": (2480, 2480)}
MARGE_PX = 180
CAP_PX = 34
INTERLIGNE = 1.45


def police(nom: str = "", taille: int = CAP_PX):
    """Une fonte servie par l'application, ou la fonte par défaut de PIL.

    LE PIÈGE DÉJÀ PAYÉ PAR CE DÉPÔT : `PolandKaito.otf` n'est pas un `.ttf`.
    On ne devine JAMAIS l'extension — on prend le fichier tel qu'il est.
    """
    from app.config import settings
    dossier = getattr(settings, "fonts_path", None)
    if nom and dossier:
        p = dossier / nom
        if p.is_file():
            try:
                return ImageFont.truetype(str(p), int(taille))
            except OSError:
                pass
    return ImageFont.load_default(int(taille))


def _largeur(draw, texte: str, fnt) -> float:
    return draw.textlength(texte, font=fnt)


def paginer(texte: str, largeur_px: int, hauteur_px: int, cap_px: int,
            interligne: float, marge_px: int, fnt=None) -> list:
    """Le texte -> une liste de pages, chaque page une liste de lignes.

    LA MESURE, PAS L'ŒIL : la largeur vient de `textlength` avec la fonte
    réelle. Un mot plus long qu'une ligne est COUPÉ, jamais perdu : jeter un
    caractère dans un livret de règles est une règle de jeu qui disparaît.
    """
    fnt = fnt or police("", cap_px)
    sonde = ImageDraw.Draw(Image.new("L", (8, 8)))
    utile = max(1, int(largeur_px) - 2 * int(marge_px))
    par_page = max(1, int((int(hauteur_px) - 2 * int(marge_px))
                          // (cap_px * interligne)))
    lignes: list[str] = []
    for para in str(texte or "").split("\n"):
        if not para.strip():
            lignes.append("")
            continue
        cur = ""
        for mot in para.split(" "):
            essai = (cur + " " + mot).strip()
            if _largeur(sonde, essai, fnt) <= utile:
                cur = essai
                continue
            if cur:
                lignes.append(cur)
                cur = ""
            while _largeur(sonde, mot, fnt) > utile and len(mot) > 1:
                n = len(mot)
                while n > 1 and _largeur(sonde, mot[:n], fnt) > utile:
                    n -= 1
                lignes.append(mot[:n])       # COUPÉ, pas jeté
                mot = mot[n:]
            cur = mot
        if cur:
            lignes.append(cur)
    pages = [lignes[i:i + par_page] for i in range(0, len(lignes), par_page)]
    return pages or [[""]]


def composer_page(lignes: list, largeur_px: int, hauteur_px: int, cap_px: int,
                  interligne: float, marge_px: int, fnt=None,
                  titre: str = "", numero: int = 0) -> Image.Image:
    fnt = fnt or police("", cap_px)
    im = Image.new("RGB", (int(largeur_px), int(hauteur_px)), (255, 255, 255))
    d = ImageDraw.Draw(im)
    y = float(marge_px)
    if titre and numero == 1:
        gros = police("", int(cap_px * 1.8))
        d.text((marge_px, y), titre, font=gros, fill=(0, 0, 0))
        y += cap_px * 1.8 * interligne
    for l in lignes:
        d.text((marge_px, y), l, font=fnt, fill=(20, 20, 20))
        y += cap_px * interligne
    if numero:
        d.text((largeur_px // 2, hauteur_px - marge_px // 2), str(numero),
               font=fnt, fill=(120, 120, 120), anchor="mm")
    return im


def build_livret(titre: str, texte: str, images: list, feuille: str = "a5",
                 cap_px: int = CAP_PX, fonte: str = "") -> tuple[bytes, int]:
    """Le livret complet. -> (octets PDF, nombre de pages)."""
    w, h = FEUILLES_PX.get(str(feuille).lower(), FEUILLES_PX["a5"])
    fnt = police(fonte, cap_px)
    pages = paginer(texte, w, h, cap_px, INTERLIGNE, MARGE_PX, fnt)
    ims = [composer_page(p, w, h, cap_px, INTERLIGNE, MARGE_PX, fnt,
                         titre, i + 1) for i, p in enumerate(pages)]
    # UNE PLANCHE DE CARTES en fin de livret, si des images sont fournies :
    # les règles renvoient aux cartes, les montrer évite d'aller les chercher.
    if images:
        cols = 3
        rows = max(1, math.ceil(len(images) / cols))
        cw = (w - 2 * MARGE_PX) // cols
        ch = int(cw * images[0].size[1] / images[0].size[0])
        par_page = max(1, (h - 2 * MARGE_PX) // ch)
        for k in range(0, rows, par_page):
            pg = Image.new("RGB", (w, h), (255, 255, 255))
            for j in range(par_page * cols):
                idx = k * cols + j
                if idx >= len(images):
                    break
                r, c = divmod(j, cols)
                pg.paste(images[idx].convert("RGB").resize((cw, ch),
                                                           Image.LANCZOS),
                         (MARGE_PX + c * cw, MARGE_PX + r * ch))
            ims.append(pg)
    # PIÈGE 14 DE LA SPEC : `Image.init()` avant tout save en PDF, sinon
    # `KeyError: 'JPEG'` en production seulement.
    Image.init()
    buf = io.BytesIO()
    ims[0].save(buf, "PDF", resolution=300.0, save_all=True,
                append_images=ims[1:])
    return buf.getvalue(), len(ims)
```

- [ ] **Step 4 : la route et l'écran**

```python
@router.post("/livret")
async def post_livret(did: str, spec: str = Form("{}"),
                      images: list[UploadFile] = File(default=[])):
    """Le livret de règles en PDF. Les pages sont composées à 300 DPI : le
    texte n'est PAS sélectionnable, et l'en-tête le dit."""
    doc = _deck(did)
    body = _json_form(spec)
    from . import edition_livret as LIV
    from PIL import Image as PILImage
    ims = []
    for f in (images or []):
        try:
            im = PILImage.open(io.BytesIO(await f.read()))
            im.load()
            ims.append(im)
        except Exception:
            raise HTTPException(400, f"Image « {f.filename} » illisible")
    try:
        out, n = await asyncio.to_thread(
            LIV.build_livret, str(body.get("titre") or doc.get("name") or ""),
            str(body.get("texte") or ""), ims,
            str(body.get("sheet") or "a5"),
            int(body.get("cap_px") or LIV.CAP_PX),
            str(body.get("fonte") or ""))
    except Exception as e:
        logger.exception("cards/edition: livret impossible")
        raise HTTPException(500, f"Livret impossible: {e}")
    return Response(content=out, media_type="application/pdf", headers={
        "Content-Disposition": 'attachment; filename="livret.pdf"',
        "X-CF-Pages": str(n), "X-CF-Images": str(len(ims)),
        # L'ÉCART, DIT PAR LE FICHIER QUI PART
        "X-CF-Texte": "raster",
    })
```

Dans `mod-edition.js`, un bloc « Livret de règles » avec un `<textarea>`, le
choix de feuille, le bouton, et la phrase de l'écart :

```js
      '<p class="hint">Le livret est composé à <b>300 DPI</b> : le texte '
      + 'n’est pas sélectionnable dans le PDF (aucune police n’est embarquée '
      + 'par ce logiciel). Sans conséquence <b>pour l’impression</b> ; à '
      + 'savoir si le PDF est lu à l’écran.</p>',
```

- [ ] **Step 5 : relancer**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_edition.py
cd ..
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" scripts/qa/lint_cardforge.py --module edition
```

Attendu : `18 passed` ; lint `0`.

- [ ] **Step 6 : commit proposé**

```bash
git add backend/app/services/cards/edition_livret.py backend/app/services/cards/edition.py frontend/cardforge/js/mod-edition.js backend/tests/test_cards_edition.py
git commit -m 'cartes : le livret de regles, compose a 300 DPI, ecart dit' -m 'reportlab est absent du runtime embarqué et print.py n embarque aucune police : le livret est composé par PIL avec les fontes réelles servies par l application, puis assemblé en PDF. L écart est écrit à l écran ET dans l en-tête du fichier — le texte n est pas sélectionnable, ce qui est sans conséquence à l impression et en a une à l écran. La coupure de ligne est MESURÉE avec la fonte, pas estimée, et un mot plus long qu une ligne est coupé et jamais jeté : perdre un caractère dans un livret de règles, c est perdre une règle du jeu.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Task 19 : Mockup marketing et fiche produit

**Files:**
- Modify: `backend/app/services/cards/edition_livret.py` (mockup, fiche)
- Modify: `backend/app/services/cards/edition.py` (routes `/mockup`, `/fiche`)
- Modify: `frontend/cardforge/js/mod-edition.js`
- Modify: `backend/tests/test_cards_edition.py`

**Coût de patch** : aucun.

**Le partage des rôles, dit** : le **rendu 3D** du deck (carte en main, sur table)
appartient au **Forge 3D** (pièce 09, `forge3d_scene.py` — caméras, tournette,
scène). La pièce 11 ne refait pas de moteur : elle **compose** un visuel de
communication à partir d'images déjà rendues (par `CF.renderCard` ou par la scène
du Forge). Un mockup 3D neuf serait une deuxième chaîne de rendu à maintenir.

- [ ] **Step 1 : écrire le banc qui échoue**

```python
# ─────────────────────── T19 : mockup et fiche produit ──────────────────────
def test_le_mockup_est_une_image_aux_proportions_du_reseau_demande():
    from app.services.cards import edition_livret as L
    for cible, att in (("carre", (1080, 1080)), ("story", (1080, 1920)),
                       ("paysage", (1600, 900))):
        im = L.mockup([Image.new("RGBA", (825, 1125), (10, 20, 30, 255))],
                      cible=cible, titre="Deepotus", sous_titre="60 cartes")
        assert im.size == att, (cible, im.size)


def test_le_mockup_etale_les_cartes_sans_en_perdre_une():
    from app.services.cards import edition_livret as L
    cartes = [Image.new("RGBA", (825, 1125), (i * 10 % 255, 20, 30, 255))
              for i in range(7)]
    im, plan = L.mockup_plan(cartes, cible="carre")
    assert len(plan) == 5, plan          # 5 montrées au plus, et c'est DIT
    assert im.size == (1080, 1080)


def test_la_fiche_produit_dit_les_chiffres_du_deck_et_non_des_slogans():
    from app.services.cards import edition_livret as L
    f = L.fiche({"name": "Deepotus", "format": {"fmt": "poker_us", "dpi": 300}},
                cartes=60, langues=["fr", "en"], ep_carte_mm=0.32)
    assert f["cartes"] == 60
    assert f["format"] == "Poker US 2,5 x 3,5 in"
    assert f["dimensions_mm"] == [63.5, 88.9]
    assert abs(f["epaisseur_deck_mm"] - 19.2) < 1e-9
    assert f["langues"] == ["français", "anglais"]
    assert "boite_mm" in f


def test_les_deux_routes_repondent_avec_le_bon_type():
    async def go():
        from app.main import app
        tr = ASGITransport(app=app)
        async with AsyncClient(transport=tr, base_url="http://t") as c:
            r = await c.post("/api/cards/decks", json={"name": "Fiche"})
            did = r.json()["deck"]["id"]
            g = CT.geom("poker_us", 300)
            m = await c.post(f"/api/cards/{did}/edition/mockup",
                             data={"spec": '{"cible":"carre"}'},
                             files=[("images", ("c.png", _png(*g.canvas_px),
                                                "image/png"))], timeout=120.0)
            f = await c.post(f"/api/cards/{did}/edition/fiche",
                             json={"cartes": 60, "langues": ["fr"]})
            return m, f
    m, f = asyncio.run(go())
    assert m.status_code == 200 and m.headers["content-type"] == "image/png"
    assert m.headers["X-CF-Px"] == "1080x1080"
    assert f.status_code == 200
    assert f.json()["cartes"] == 60


def test_l_ecran_dit_que_le_rendu_3D_appartient_au_forge():
    js = (FRONT / "js" / "mod-edition.js").read_text(encoding="utf-8")
    assert "pièce 09" in js
    assert "Forge 3D" in js
```

- [ ] **Step 2 : lancer, vérifier l'échec.**

- [ ] **Step 3 : écrire mockup et fiche dans `edition_livret.py`**

```python
# ── MOCKUP ET FICHE PRODUIT (D3) ────────────────────────────────────────────
# CE QUE CETTE PIÈCE NE FAIT PAS : un moteur de rendu 3D. La carte en main ou
# sur table appartient au Forge 3D (pièce 09, forge3d_scene.py — caméras,
# tournette, scène). Ici on COMPOSE un visuel de communication à partir
# d'images déjà rendues. Une seconde chaîne de rendu serait une seconde
# chaîne à maintenir, et elles finiraient par ne plus dire la même chose.
MOCKUP_CIBLES = {"carre": (1080, 1080), "story": (1080, 1920),
                 "paysage": (1600, 900)}
MOCKUP_MAX = 5          # cartes montrées : au-delà, l'éventail devient bouillie


def mockup_plan(cartes: list, cible: str = "carre") -> tuple:
    """-> (image vide à la bonne taille, plan de pose). Le plan est rendu à
    part pour que le banc le lise sans deviner à l'œil."""
    w, h = MOCKUP_CIBLES.get(str(cible).lower(), MOCKUP_CIBLES["carre"])
    montrees = list(cartes or ())[:MOCKUP_MAX]
    n = max(1, len(montrees))
    cw = int(w * (0.42 if n > 1 else 0.5))
    ch = int(cw * montrees[0].size[1] / montrees[0].size[0]) if montrees else 1
    pas = int(cw * 0.34)
    x0 = (w - (cw + pas * (n - 1))) // 2
    y0 = (h - ch) // 2
    plan = [{"i": i, "x": x0 + i * pas, "y": y0, "w": cw, "h": ch,
             "rot": (i - (n - 1) / 2.0) * 7.0} for i in range(n)]
    return Image.new("RGBA", (w, h), (0, 0, 0, 0)), plan


def mockup(cartes: list, cible: str = "carre", titre: str = "",
           sous_titre: str = "", fond=(14, 18, 24)) -> Image.Image:
    """L'éventail de cartes, sur un fond uni, avec deux lignes de texte."""
    vide, plan = mockup_plan(cartes, cible)
    im = Image.new("RGB", vide.size, tuple(fond))
    for p in plan:
        c = cartes[p["i"]].convert("RGBA").resize((p["w"], p["h"]),
                                                  Image.LANCZOS)
        c = c.rotate(p["rot"], expand=True, resample=Image.BICUBIC)
        im.paste(c, (p["x"] - (c.size[0] - p["w"]) // 2,
                     p["y"] - (c.size[1] - p["h"]) // 2), c)
    d = ImageDraw.Draw(im)
    cap = max(18, im.size[0] // 22)
    if titre:
        d.text((im.size[0] // 2, int(im.size[1] * 0.10)), titre,
               font=police("", cap), fill=(240, 244, 248), anchor="mm")
    if sous_titre:
        d.text((im.size[0] // 2, int(im.size[1] * 0.90)), sous_titre,
               font=police("", int(cap * 0.62)), fill=(170, 180, 190),
               anchor="mm")
    return im


def fiche(doc: dict, cartes: int, langues: list,
          ep_carte_mm: float) -> dict:
    """La fiche produit : DES CHIFFRES, pas des slogans. C'est ce qu'une
    boutique demande, et c'est ce que le vendeur recopie de travers quand il
    doit le retrouver à la main."""
    from .contract import FORMATS, geom
    from .data import LANG_NOMS
    from .forge3d_jeu import (JEU_MM_DEFAUT, RABAT_MM_DEFAUT,
                              epaisseur_deck_mm, patron_boite)
    fmt = str((doc.get("format") or {}).get("fmt") or "poker_eu")
    g = geom(fmt, 300)
    ep = epaisseur_deck_mm(int(cartes), float(ep_carte_mm))
    try:
        boite = patron_boite(g.trim_mm[0], g.trim_mm[1], ep,
                             JEU_MM_DEFAUT, RABAT_MM_DEFAUT, "a3")["boite_mm"]
    except ValueError:
        boite = None
    return {
        "nom": str(doc.get("name") or ""),
        "cartes": int(cartes),
        "format": FORMATS[fmt]["label"],
        "dimensions_mm": [round(v, 2) for v in g.trim_mm],
        "epaisseur_carte_mm": float(ep_carte_mm),
        "epaisseur_deck_mm": ep,
        "boite_mm": boite,
        "langues": [LANG_NOMS.get(str(l).lower(), str(l))
                    for l in (langues or ())],
        "dpi": g.dpi,
    }
```

> `from .data import LANG_NOMS` et `from .forge3d_jeu import …` : ce sont des
> **constantes et des fonctions pures**, jamais des routers — la règle 8 vise le
> routeur, et le lint le vérifie sur `.router`. Le partage reste unidirectionnel :
> `edition` lit, `data` et `forge3d` ne connaissent pas `edition`.

- [ ] **Step 4 : les deux routes**

```python
@router.post("/mockup")
async def post_mockup(did: str, spec: str = Form("{}"),
                      images: list[UploadFile] = File(default=[])):
    """Le visuel de communication. Le rendu 3D du deck reste au Forge 3D."""
    doc = _deck(did)
    body = _json_form(spec)
    from . import edition_livret as LIV
    from PIL import Image as PILImage
    if not images:
        raise HTTPException(400, "Aucune carte reçue pour le mockup")
    ims = []
    for f in images:
        try:
            im = PILImage.open(io.BytesIO(await f.read()))
            im.load()
            ims.append(im)
        except Exception:
            raise HTTPException(400, f"Image « {f.filename} » illisible")
    cible = str(body.get("cible") or "carre").lower()
    if cible not in LIV.MOCKUP_CIBLES:
        raise HTTPException(400, "Cible inconnue: %s. Cibles admises: %s"
                                 % (cible, ", ".join(LIV.MOCKUP_CIBLES)))

    def work():
        im = LIV.mockup(ims, cible, str(body.get("titre")
                                        or doc.get("name") or ""),
                        str(body.get("sous_titre") or ""))
        buf = io.BytesIO()
        im.save(buf, "PNG")
        return buf.getvalue(), im.size
    try:
        out, size = await asyncio.to_thread(work)
    except Exception as e:
        logger.exception("cards/edition: mockup impossible")
        raise HTTPException(500, f"Mockup impossible: {e}")
    return Response(content=out, media_type="image/png", headers={
        "Content-Disposition": 'attachment; filename="mockup.png"',
        "X-CF-Px": f"{size[0]}x{size[1]}",
        "X-CF-Cartes-Montrees": str(min(len(ims), LIV.MOCKUP_MAX)),
    })


@router.post("/fiche")
async def post_fiche(did: str, body: Any = Body(default=None)):
    """La fiche produit : des chiffres, pas des slogans."""
    doc = _deck(did)
    b = body if isinstance(body, dict) else {}
    from . import contract
    from . import edition_livret as LIV
    ep = float((doc.get("solid") or {}).get("thickness_mm")
               or contract.THICKNESS_MM_DEFAULT)
    try:
        return LIV.fiche(doc, int(b.get("cartes") or 0),
                         b.get("langues") or [], ep)
    except ValueError as e:
        raise HTTPException(400, str(e))
```

> `Body` doit être importé dans `edition.py` (`from fastapi import Body`).

- [ ] **Step 5 : relancer**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/test_cards_edition.py
cd ..
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" scripts/qa/lint_cardforge.py
```

Attendu : `23 passed` ; lint `0` sur toutes les pièces.

- [ ] **Step 6 : commit proposé**

```bash
git add backend/app/services/cards/edition_livret.py backend/app/services/cards/edition.py frontend/cardforge/js/mod-edition.js backend/tests/test_cards_edition.py
git commit -m 'cartes : le mockup marketing et la fiche produit' -m 'La pièce 11 ne fabrique pas de moteur de rendu : la carte en main ou sur table appartient au Forge 3D, et deux chaînes de rendu finiraient par ne plus dire la même chose. Elle COMPOSE, à partir d images déjà rendues, et elle plafonne l éventail à cinq cartes parce qu au-delà c est de la bouillie — le chiffre est dans l en-tête. La fiche produit rend des chiffres et non des slogans : format nommé, dimensions, épaisseur du paquet lue dans la pièce 05, dimensions de la boîte calculées par le même patron que la tâche 17, langues nommées en toutes lettres.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

# Écarté

- **E1 — Scripts de génération façon nanDECK.** La sémantique (LINK*, quantités,
  filtres, tri) est **déjà portée par l'interface** — `data.py:745 compile_filter`,
  `869 parse_sort`, `1207 build_deck`, dans l'ordre exact de nanDECK (lignes
  désactivées, filtre, tri, quantités, mappage). Ajouter un langage de script
  au-dessus dupliquerait cette grammaire dans une seconde syntaxe à tenir. Décision
  du dépôt, inchangée.
- **E2 — API The Game Crafter pour envoyer le deck.** L'API développeur `/api/deck`
  existe (vérifié 03/09/2026) mais demande **un compte et une clé** : les gabarits
  (T1–T4) livrent d'abord le fichier au bon format. À instruire plus tard **si et
  seulement si** P1 ne suffit pas, avec la mesure qui le prouve.

---

## Task 20 : Campagne de mutations — `backend/tests/mutations_cartes.py`

**Files:**
- Create: `backend/tests/mutations_cartes.py`

**Coût de patch** : aucun. Le banc **mute les sources du dépôt une à une et les
remet à l'octet près** (assertion sha256) : il ne se lance pas pendant qu'un autre
banc lit ces fichiers.

**Patron** : `backend/tests/mutations_plaque_slicer.py` — même mécanique, même
sortie, une seule différence assumée : ce plan a **sept** bancs au lieu d'un, donc
chaque mutation porte le sien.

- [ ] **Step 1 : écrire la campagne**

```python
# -*- coding: utf-8 -*-
"""Banc de mutations des Cartes : casser → rouge → remettre.

PAS UN TEST : pytest ne le collecte pas (son nom ne commence pas par `test_`)
et run-tests.ps1 ne le liste pas. Il se lance À LA MAIN, depuis backend/ :

    python tests/mutations_cartes.py           # toutes
    python tests/mutations_cartes.py 3 17      # celles-là

Il MUTE les sources du dépôt une à une et les REMET à l'octet près
(assertion), donc il ne se lance pas pendant qu'un autre banc lit ces
fichiers. La liste est l'argument de la revue : chaque mutation nomme le banc
et le test qu'elle fait rougir, et une « VERTE » est une assertion qui manque.

DIFFÉRENCE AVEC mutations_plaque_slicer.py : ce plan a SEPT bancs, pas un.
Chaque mutation porte donc le sien — une mutation lancée sur le mauvais banc
sortirait VERTE en ne prouvant rien, ce qui est précisément le défaut que ce
genre de campagne existe pour trouver.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable

G = "tests/test_cards_gabarits.py"
E = "tests/test_cards_edition.py"
D = "tests/test_cards_dos.py"
N = "tests/test_cards_donnees.py"
L = "tests/test_cards_langues.py"
A = "tests/test_cards_lot_art.py"
J = "tests/test_cards_jeu3d.py"

# (banc, fichier, ancien, nouveau, tests attendus rouges)
M = [
    # ── T1 : les gabarits ───────────────────────────────────────────────────
    (G, "backend/app/services/cards/contract.py",
     '"bleed_mm": 3.048,\n        "safe_mm": 3.048,',
     '"bleed_mm": 3.175,\n        "safe_mm": 3.175,',
     ["les_trois_gabarits_sortent_les_pixels_publies",
      "mpc_ecrit_36_px_et_non_un_huitieme_de_pouce"]),
    (G, "backend/app/services/cards/contract.py",
     "        return geom(f, int(dpi or pr[\"dpi\"]), pr[\"bleed_mm\"], pr[\"safe_mm\"])",
     "        return geom(f, int(dpi or pr[\"dpi\"]))",
     ["les_trois_gabarits_sortent_les_pixels_publies"]),
    (G, "backend/app/services/cards/contract.py",
     "    if f not in pr[\"fmts\"]:",
     "    if False:",
     ["un_gabarit_refuse_un_format_qu_il_ne_sert_pas",
      "le_catalogue_dit_la_livraison_et_la_revendication"]),
    (G, "backend/app/services/cards/contract.py",
     "        except ValueError:\n            row[\"geom\"] = None",
     "        except ValueError:\n            row[\"geom\"] = {}",
     ["le_catalogue_dit_la_livraison_et_la_revendication"]),

    # ── T2 : le paquet ──────────────────────────────────────────────────────
    (G, "backend/app/services/cards/print_gabarits.py",
     "    largeur = max(2, len(str(max(1, int(n)))))",
     "    largeur = 2",
     []),                       # VERTE ATTENDUE : voir la note en fin de liste
    (G, "backend/app/services/cards/print_gabarits.py",
     '    mot = SIDE_WORDS.get(side, side)',
     '    mot = side',
     ["le_paquet_mpc_nomme_recto_verso_et_fait_822x1122"]),
    (G, "backend/app/services/cards/print_gabarits.py",
     '        "canvas_px": list(g.canvas_px),',
     '        "canvas_px": list(g.trim_px),',
     ["le_manifeste_dit_le_gabarit_la_toile_et_le_condensat"]),
    (G, "backend/app/services/cards/print.py",
     '        spec["bleed_mm"] = pr["bleed_mm"]',
     '        spec["bleed_mm"] = spec.get("bleed_mm")',
     ["le_paquet_mpc_nomme_recto_verso_et_fait_822x1122",
      "un_bitmap_a_la_mauvaise_taille_est_refuse_en_le_disant"]),

    # ── T3 : PDF/X-1a ───────────────────────────────────────────────────────
    (G, "backend/app/services/cards/print.py",
     '    "PDF/X-1a:2001": {"colors": ("cmyk_device",), "layers_ok": False},',
     '    "PDF/X-1a:2001": {"colors": ("rgb", "cmyk_device", "cmyk_icc"), "layers_ok": False},',
     ["en_rvb_le_pdf_dtc_tient_les_dimensions_et_ne_revendique_rien"]),
    (G, "backend/app/services/cards/print.py",
     "    if color not in spec[\"colors\"]:\n        return False",
     "    if False:\n        return False",
     ["en_rvb_le_pdf_dtc_tient_les_dimensions_et_ne_revendique_rien"]),
    (G, "backend/app/services/cards/print.py",
     '        spec["marks"] = pr["marks"]',
     '        spec["marks"] = spec.get("marks")',
     ["le_pdf_dtc_fait_198_sur_270_points_et_na_aucun_trait_de_coupe"]),

    # ── T5 / T6 : la pièce 11 et le collage TTS ─────────────────────────────
    (E, "backend/app/services/cards/edition_vtt.py",
     "    cw = TTS_MAX_PX // max(1, int(cols))",
     "    cw = 512",
     ["le_collage_tts_tient_sous_le_plafond_de_texture_mesure",
      "le_collage_recadre_sur_la_rogne_et_non_sur_la_toile"]),
    (E, "backend/app/services/cards/edition_vtt.py",
     "    if ch * rows > TTS_MAX_PX:",
     "    if False:",
     []),                       # VERTE ATTENDUE : voir la note
    (E, "backend/app/services/cards/edition_vtt.py",
     "        tile = trim_crop(im, g).convert(\"RGBA\").resize(\n            (cw, ch), Image.LANCZOS)",
     "        tile = im.convert(\"RGBA\").resize((cw, ch), Image.LANCZOS)",
     ["le_collage_recadre_sur_la_rogne_et_non_sur_la_toile"]),
    (E, "backend/app/services/cards/edition_vtt.py",
     "    x = int(round(g.bleed_off_px[0]))\n    y = int(round(g.bleed_off_px[1]))",
     "    x = int(g.bleed_off_px[0])\n    y = int(g.bleed_off_px[1])",
     []),                       # VERTE ATTENDUE : voir la note
    (E, "backend/app/services/cards/edition_vtt.py",
     "            cid = 100 * did_tts + j",
     "            cid = j",
     ["l_objet_sauvegarde_porte_les_champs_que_tts_lit"]),
    (E, "backend/app/services/cards/edition_vtt.py",
     '            "UniqueBack": bool(backs), "Type": 0,',
     '            "UniqueBack": False, "Type": 0,',
     ["l_objet_sauvegarde_porte_les_champs_que_tts_lit"]),
    (E, "backend/app/services/cards/edition_vtt.py",
     "    planches = max(1, -(-n // par))",
     "    planches = 1",
     ["une_planche_par_soixante_dix_cartes_et_pas_une_de_plus"]),

    # ── T7 : Tabletopia ─────────────────────────────────────────────────────
    (E, "backend/app/services/cards/edition_vtt.py",
     "    f = min(1.0, TABLETOPIA_MAX_PX / float(max(tw, th)))",
     "    f = TABLETOPIA_MAX_PX / float(max(tw, th))",
     []),                       # VERTE ATTENDUE : voir la note
    (E, "backend/app/services/cards/edition_vtt.py",
     '        "collage": False,',
     '        "collage": True,',
     ["le_manifeste_tabletopia_dit_pourquoi_il_ny_a_pas_de_collage"]),
    (E, "backend/app/services/cards/edition_vtt.py",
     '    for side, lot in (("recto", fronts), ("verso", backs)):',
     '    for side, lot in (("recto", fronts), ("verso", backs or fronts)):',
     ["un_deck_sans_verso_ne_fabrique_pas_de_verso_vide"]),

    # ── T8 : le dos et la mire ──────────────────────────────────────────────
    (D, "backend/app/services/cards/data.py",
     '    if v in set(str(i) for i in (images or ())):\n        return "image"\n    return "introuvable"',
     '    return "commun"',
     ["l_origine_du_dos_est_dite_par_carte_et_jamais_devinee"]),
    (D, "backend/app/services/cards/data.py",
     "        e[\"cartes\"] += q",
     "        e[\"cartes\"] += 1",
     ["l_origine_du_dos_est_dite_par_carte_et_jamais_devinee"]),
    (D, "backend/app/services/cards/print.py",
     "        biais = 0.0 if recto else pas / 2.0",
     "        biais = 0.0",
     []),                       # VERTE ATTENDUE : voir la note
    (D, "backend/app/services/cards/print.py",
     "    for recto in (True, False):",
     "    for recto in (True,):",
     ["la_mire_est_une_page_recto_verso_avec_une_graduation_lisible"]),

    # ── T9 : les statistiques ───────────────────────────────────────────────
    (N, "backend/app/services/cards/data_stats.py",
     "                      if (a <= x < b) or (k == CLASSES - 1 and x == hi)]",
     "                      if a <= x < b]",
     ["le_maximum_tombe_dans_la_derniere_classe_et_non_dehors",
      "une_colonne_numerique_rend_min_max_moyenne_mediane_et_des_classes"]),
    (N, "backend/app/services/cards/data_stats.py",
     "        etendu = sorted(float(x) for x, q in nums for _ in range(q))",
     "        etendu = sorted(float(x) for x, q in nums)",
     ["une_colonne_numerique_rend_min_max_moyenne_mediane_et_des_classes"]),
    (N, "backend/app/services/cards/data_stats.py",
     "    ecartees = {qc} | {str(s) for s in (skip or ())}",
     "    ecartees = {str(s) for s in (skip or ())}",
     ["la_colonne_de_quantite_nest_pas_son_propre_histogramme"]),
    (N, "backend/app/services/cards/data_stats.py",
     "    if n and part >= SEUIL_NUM:",
     "    if n and part > 0:",
     ["une_colonne_a_moitie_numerique_est_dite_categorielle_et_le_dit"]),

    # ── T11 : l'import distant ──────────────────────────────────────────────
    (N, "backend/app/services/cards/data.py",
     "    gid = _GID.search(u)\n    return (\"https://docs.google.com/spreadsheets/d/%s/export?format=csv&gid=%s\"\n            % (m.group(1), gid.group(1) if gid else \"0\"))",
     "    return u",
     ["une_url_sheets_de_partage_est_reecrite_en_export_csv",
      "l_import_distant_lit_le_csv_rapporte_sans_toucher_au_reseau"]),
    (N, "backend/app/services/cards/data.py",
     "    if code in (401, 403):",
     "    if False:",
     ["les_trois_echecs_qui_se_ressemblent_sont_distingues"]),
    (N, "backend/app/services/cards/data.py",
     "        if len(csvs) > 1:",
     "        if False:",
     ["un_export_notion_en_zip_rend_le_csv_qui_est_dedans"]),

    # ── T12 / T13 : langues et traduction ───────────────────────────────────
    (L, "backend/app/services/cards/data.py",
     "        elif str(base) in cols:        # colonne neutre : elle sert partout\n            out[str(base)] = slot",
     "        else:\n            for cs in par.values():\n                if str(base) in cs:\n                    out[cs[str(base)]] = slot",
     ["une_base_sans_colonne_dans_la_langue_nest_pas_repliee_ailleurs"]),
    (L, "backend/app/services/cards/data.py",
     "        if not m or code not in LANG_NOMS:\n            neutres.append(c)\n            continue",
     "        if not m:\n            neutres.append(c)\n            continue",
     ["les_langues_se_devinent_par_le_suffixe_des_colonnes"]),
    (L, "backend/app/services/cards/data.py",
     "        if cur and not forcer:\n            deja += 1               # on ne paye pas pour écraser un humain\n            continue",
     "        if False:\n            deja += 1\n            continue",
     ["une_cellule_deja_remplie_nest_meme_pas_envoyee_au_modele"]),
    (L, "backend/app/services/cards/data.py",
     '              "accepte": False} for n, t in a_faire]',
     '              "accepte": True} for n, t in a_faire]',
     ["la_traduction_est_proposee_et_jamais_ecrite_dans_la_table"]),
    (L, "backend/app/services/cards/data.py",
     "    except Exception:\n        raise RuntimeError(\n            \"Le modèle n'a pas rendu de JSON exploitable. Réessayez, ou \"\n            \"traduisez cette colonne à la main.\")",
     "    except Exception:\n        brute = []",
     ["une_reponse_mal_formee_fait_502_avec_la_phrase_qui_dit_quoi_faire"]),

    # ── T14 / T15 : l'art du deck ───────────────────────────────────────────
    (A, "backend/app/services/cards/face_lot.py",
     "        a_faire += 1\n        couvertes += q",
     "        a_faire += q\n        couvertes += q",
     ["le_devis_compte_les_LIGNES_a_generer_et_non_les_cartes",
      "le_devis_suit_le_prix_du_MODELE_et_ne_le_recalcule_pas"]),
    (A, "backend/app/services/cards/face_lot.py",
     '    est = pricing.estimate({"kind": "image", "model": str(model or "flux"),\n                            "n": a_faire * n})',
     '    est = pricing.estimate({"kind": "image", "model": str(model or "flux"),\n                            "n": a_faire})',
     ["le_devis_multiplie_par_les_variantes_demandees"]),
    (A, "backend/app/services/cards/face_lot.py",
     "    if not base.strip():\n        manque.append(\"prompt\")",
     "    if False:\n        manque.append(\"prompt\")",
     ["une_ligne_sans_prompt_ni_entite_est_signalee_et_non_inventee",
      "le_lot_refuse_de_tirer_sil_reste_des_lignes_sans_prompt"]),
    (A, "backend/app/services/cards/face_lot.py",
     "        except Exception as e:                       # noqa: BLE001\n            err.append({\"ligne\": p[\"ligne\"], \"message\": str(e)})",
     "        except Exception as e:                       # noqa: BLE001\n            raise",
     ["un_echec_de_generation_narrete_pas_le_lot_et_se_dit"]),
    (A, "backend/app/services/cards/face_lot.py",
     "            if fichier:\n                await _noter([fichier], \"cardforge\", deck_id=did)",
     "            if False:\n                await _noter([fichier], \"cardforge\", deck_id=did)",
     ["la_generation_en_lot_ecrit_une_image_par_ligne_et_remplit_la_colonne"]),

    # ── T16 / T17 : les objets 3D ───────────────────────────────────────────
    (J, "backend/app/services/cards/forge3d_jeu.py",
     "        tris.append([[cx, cy, 0.0], [x1, y1, 0.0], [x0, y0, 0.0]])",
     "        tris.append([[cx, cy, 0.0], [x0, y0, 0.0], [x1, y1, 0.0]])",
     ["un_jeton_est_ferme_donc_imprimable"]),
    (J, "backend/app/services/cards/forge3d_jeu.py",
     "        tris.append([[x0, y0, 0.0], [x1, y1, ep], [x0, y0, ep]])",
     "",
     ["un_jeton_est_ferme_donc_imprimable",
      "un_jeton_rond_a_la_bonne_hauteur_et_le_bon_diametre"]),
    (J, "backend/app/services/cards/forge3d_jeu.py",
     "    if not math.isfinite(x) or x < lo or x > hi:",
     "    if not math.isfinite(x):",
     ["le_diametre_dun_jeton_est_borne_et_le_refus_donne_les_bornes"]),
    (J, "backend/app/services/cards/forge3d_jeu.py",
     "    L = float(largeur_mm) + float(jeu_mm)\n    H = float(hauteur_mm) + float(jeu_mm)\n    E = float(epaisseur_deck_mm) + float(jeu_mm)",
     "    L = float(largeur_mm)\n    H = float(hauteur_mm)\n    E = float(epaisseur_deck_mm)",
     ["le_patron_de_boite_est_aux_dimensions_du_deck_plus_le_jeu"]),
    (J, "backend/app/services/cards/forge3d_jeu.py",
     "    if dw > fw or dh > fh:",
     "    if False:",
     ["la_boite_refuse_de_depasser_la_feuille_et_le_dit"]),
    (J, "backend/app/services/cards/forge3d.py",
     '        ops += [b"0.4 w", b"[3 2] 0 d"]          # POINTILLE = PLI',
     '        ops += [b"0.4 w"]',
     ["le_pdf_de_la_boite_trace_les_plis_en_pointilles_et_les_coupes_pleines"]),

    # ── T18 / T19 : livret, mockup, fiche ───────────────────────────────────
    (E, "backend/app/services/cards/edition_livret.py",
     "                lignes.append(mot[:n])       # COUPÉ, pas jeté\n                mot = mot[n:]",
     "                mot = mot[n:]",
     ["un_mot_plus_long_que_la_ligne_est_coupe_et_non_perdu"]),
    (E, "backend/app/services/cards/edition_livret.py",
     "    montrees = list(cartes or ())[:MOCKUP_MAX]",
     "    montrees = list(cartes or ())",
     ["le_mockup_etale_les_cartes_sans_en_perdre_une"]),
    (E, "backend/app/services/cards/edition_livret.py",
     "        \"epaisseur_deck_mm\": ep,",
     "        \"epaisseur_deck_mm\": float(cartes) * 0.3,",
     ["la_fiche_produit_dit_les_chiffres_du_deck_et_non_des_slogans"]),
]

# ── LES « VERTES ATTENDUES », ET POURQUOI ELLES SONT DANS LA LISTE ──────────
# Cinq mutations ci-dessus ont une liste d'attendus VIDE : elles ne font
# rougir aucun banc, et c'est SU. Chacune nomme un trou d'assertion que ce
# plan assume :
#   * le zéro-comblement dynamique (largeur = 2) : aucun banc n'exporte un
#     deck de plus de 99 cartes — l'ajouter coûterait 100 rendus de carte.
#   * le repli de hauteur du collage TTS, l'arrondi du recadrage à x,5, et le
#     `min(1.0, …)` de Tabletopia : aucun format du catalogue ne déclenche ces
#     branches à 300 DPI ; il faudrait un format inventé pour les atteindre.
#   * le vernier de la mire (biais nul) : le banc compte les traits, il ne les
#     situe pas — une lecture de position demanderait un analyseur de flux.
# Une VERTE inattendue est un défaut ; une VERTE ÉCRITE ICI est une dette
# nommée. La différence est tout l'intérêt de cette campagne.


def rouges(banc, k):
    """Les tests rouges du banc ciblé — et si RIEN n'a tourné, on le dit.

    pytest sort 0 (tout vert) ou 1 (des rouges) quand il a tourné ; 2 à 5
    quand la COLLECTE a cassé (une erreur de syntaxe, un import qui lève) ou
    qu'aucun test ne correspond. Lue comme « aucun FAILED », une collecte
    cassée passerait pour une mutation VERTE alors que rien n'a été mesuré.
    On lit donc le code de sortie ET les lignes `ERROR`, et l'on rend un
    troisième état.
    """
    r = subprocess.run([PY, "-m", "pytest", banc, "-q", "--no-header",
                        "-p", "no:warnings", "-k", k],
                       capture_output=True, cwd=R / "backend", timeout=1800)
    txt = r.stdout.decode("utf-8", "replace")
    erreur = (r.returncode not in (0, 1)
              or bool(re.search(r"^ERROR ", txt, re.M)))
    return set(re.findall(r"^FAILED [^:]+::(\w+)", txt, re.M)), txt, erreur


def main():
    seuls = sys.argv[1:]
    bilan = []
    for i, (banc, rel, old, new, attendus) in enumerate(M):
        if seuls and str(i) not in seuls:
            continue
        p = R / rel
        src = p.read_bytes()
        brut = src.decode("utf-8")
        # les fichiers de l'arbre sont en CRLF (autocrlf) : on apparie en LF
        # et l'on réécrit avec la fin de ligne du fichier ; la remise se fait
        # à l'octet près depuis `src`.
        eol = "\r\n" if "\r\n" in brut else "\n"
        txt = brut.replace("\r\n", "\n")
        paires = old if isinstance(old, list) else [(old, new)]
        for o, n_ in paires:
            assert txt.count(o) == 1, (i, rel, txt.count(o), o[:60])
            txt = txt.replace(o, n_)
        sha_avant = hashlib.sha256(src).hexdigest()
        p.write_bytes(txt.replace("\n", eol).encode("utf-8"))
        try:
            k = " or ".join(attendus) if attendus else "test_"
            rg, sortie, erreur = rouges(banc, k)
        finally:
            p.write_bytes(src)
            sha_apres = hashlib.sha256(p.read_bytes()).hexdigest()
            assert sha_apres == sha_avant, (i, rel, sha_avant, sha_apres)
        manquants = [a for a in attendus if not any(a in n for n in rg)]
        if erreur:
            verdict = "ERREUR(collecte)"
            print(sortie[-1200:], file=sys.stderr)
        elif attendus:
            verdict = ("ROUGE" if not manquants
                       else ("VERTE" if not rg else "ROUGE(autres)"))
        else:
            verdict = "VERTE(attendue)" if not rg else "ROUGE(inattendu)"
        bilan.append((i, rel, verdict, sorted(rg), manquants))
        apercu = paires[0][0].strip()[:50]
        print(f"[{i:2d}] {verdict:16s} {banc:32s} {apercu!r} -> {sorted(rg)}"
              f"  sha {sha_avant[:10]}={sha_apres[:10]}")
        sys.stdout.flush()
    print(json.dumps([b[:3] for b in bilan], ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2 : lancer la campagne complète**

```powershell
cd backend
& "$env:LOCALAPPDATA\DeepotusVideoGen\runtime\python\python.exe" tests/mutations_cartes.py
```

Attendu, ligne par ligne : **`ROUGE`** pour les 43 mutations qui portent des
attendus, **`VERTE(attendue)`** pour les 5 listées dans le bloc de commentaire.
Aucune ligne `ERREUR(collecte)`, aucune `VERTE` (sans parenthèse), aucune
`ROUGE(inattendu)`.

- [ ] **Step 3 : vérifier que l'arbre est intact**

```powershell
cd ..
git status --porcelain
```

Attendu : **rien** (aucune ligne). La campagne remet chaque fichier à l'octet
près, et l'assertion sha256 échouerait sinon.

- [ ] **Step 4 : traiter les VERTE inattendues**

Toute mutation qui sort `VERTE` sans être dans le bloc de commentaire est **une
assertion qui manque**. Deux issues, jamais une troisième :

1. ajouter l'assertion au banc nommé sur la ligne, la faire rougir, la faire
   passer, relancer cette mutation seule ;
2. ou l'inscrire dans le bloc « VERTES ATTENDUES » **avec la raison mesurée** —
   pas « pas grave », mais ce que coûterait la couvrir.

- [ ] **Step 5 : commit proposé**

```bash
git add backend/tests/mutations_cartes.py
git commit -m 'cartes : la campagne de mutations, quarante-huit trous cherches' -m 'Le patron est celui de mutations_plaque_slicer.py, à une différence assumée : ce plan a sept bancs et non un, donc chaque mutation porte le sien — lancée sur le mauvais banc, elle sortirait verte sans rien prouver, ce qui est précisément le défaut que ce genre de campagne existe pour trouver. Cinq mutations sont vertes ET écrites comme telles, chacune avec ce que la couvrir coûterait : une verte inattendue est un défaut, une verte nommée est une dette. Les fichiers sont remis à l octet près, assertion sha256 à l appui.' -m 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Relecture finale (auto-revue du skill)

**1. Couverture du périmètre.** Chaque bac de R10d a au moins une tâche :

| bac | tâches | verdict |
|---|---|---|
| P1 gabarits imprimeur | T1 (profils + banc de pixels), T2 (paquet PNG MPC/TGC), T3 (PDF DTC), T4 (écran) | couvert |
| P2 TTS + Tabletopia | T5 (relecture datée + pièce 11), T6 (collage + objet), T7 (images par face) | couvert |
| P3 dos variables + miroir | T8 — **et le miroir est constaté livré, pas réécrit** | couvert |
| P4 données | T9 (statistiques), T10 (grille), T11 (Sheets + Notion) | couvert |
| P5 localisation | T12 (colonnes, rendu, export par langue), T13 (traduction validée) | couvert |
| D1 art du deck | T14 (devis + prompt par ligne + bible), T15 (lot + lignée) | couvert |
| D2 objets 3D | T16 (jetons, pions, présentoir), T17 (boîte dépliée) | couvert |
| D3 autour du deck | T18 (livret), T19 (mockup + fiche produit) | couvert |
| E1, E2 | section « Écarté », une ligne chacun | couvert |
| campagne de mutations | T20 | couvert |

**2. Placeholders.** Aucune étape ne dit « TBD », « à compléter », « similaire à la
tâche N » ni « ajouter la gestion d'erreur ». Trois endroits demandent
explicitement de **relire une signature existante avant d'écrire** — `parse_table`
(T11), `image_providers.generate` (T15), `core.deck_or_404` (T5) — et c'est une
instruction, pas un trou : inventer une signature serait pire que la vérifier.

**3. Cohérence des noms entre tâches.** Vérifié :
`contract.profile_geom` / `profile_table` / `printer_profile` (T1) sont appelés
sous ces noms exacts en T2, T3, T4. `print_gabarits.deck_slug` (T2) est réutilisé
par `edition_vtt` (T6, T7). `data.read_qty` et `data.BLANK` (existants) sont
importés par `data_stats` (T9) et `face_lot` (T14). `grilleEcrire` (T10) est la
plume unique de T13. `forge3d_jeu.patron_boite` et `epaisseur_deck_mm` (T17) sont
appelés par `edition_livret.fiche` (T19). `LANG_NOMS` (T12) est lu par T13 et T19.

**4. Corrections faites en relecture, inline :**
- T8 : la première assertion du banc **passe dès le départ** — c'est voulu et c'est
  écrit dans l'étape 2, sans quoi un exécutant croirait à un banc mal écrit.
- T19 : `edition_livret` importe des **fonctions pures** de `data` et `forge3d_jeu` ;
  la note rappelle que la règle 8 vise le **router** et que le lint le vérifie sur
  `.router` — la dépendance reste unidirectionnelle.
- T20 : les cinq mutations vertes sont **listées avec leur raison chiffrée** plutôt
  que retirées, pour que la revue voie la dette au lieu d'une liste flatteuse.

---

## Incertitudes non levées, à trancher pendant l'exécution

1. **La grille TTS 10 × 7 n'est pas un chiffre publié.** La base de connaissances
   publie le champ (« how many cards horizontally and vertically ») et le plafond de
   texture (4096 px), pas de maximum. Le plan en fait un **défaut réglable** et
   dérive la case du plafond. Si un gabarit officiel dit autre chose, seul le défaut
   change — la mécanique tient.
2. **`CardID = 100 × id_de_deck + index`** est lu dans des objets sauvegardés, pas
   dans la documentation. Écrit tel quel **et signalé comme convention** dans le
   manifeste. À reprendre si un deck importé dans TTS sort mélangé.
3. **`FaceURL` / `BackURL`** : selon la version, TTS accepte une URL ou un chemin
   local. Le manifeste dit que le champ **est à remplir**. Non tranché faute d'une
   installation TTS mesurable ici.
4. **MPC au-delà du poker** : les 822 × 1122 sont vérifiés pour le poker US. Les
   autres formats du profil `mpc` sortent de la **même règle** (bleed 3,048 mm) mais
   leurs pixels **ne sont pas vérifiés sur le portail**. T1 ne verrouille que
   `poker_us` ; les autres sont proposés, non certifiés — et le profil devrait le
   dire dans sa note si l'utilisateur en commande un.
5. **PDF/X-1a certifié** : le plan écrit la revendication et la relit dans les
   octets, mais **aucun validateur de conformité** (Acrobat Preflight, veraPDF)
   n'est disponible ici. Ce qui est prouvé : les clés, l'en-tête, l'absence de
   police, l'absence de calques, l'espace CMJN. Ce qui ne l'est pas : qu'un RIP
   d'imprimeur l'accepte. **À faire valider par un vrai envoi DTC** avant de
   promettre le mot « conforme » à l'écran.
6. **`image_providers.generate`** (T15) et **`parse_table`** (T11) : signatures
   supposées d'après leurs appelants, **non relues ligne à ligne**. La première
   étape de chaque tâche est de les ouvrir.
7. **La rainure du présentoir à 1,2 mm** est un choix, pas une mesure : elle vaut
   l'épaisseur d'une carte (0,32 mm) plus un jeu généreux. **À mesurer sur une
   impression réelle** avec la Centauri Carbon 2 avant de la graver comme défaut.
8. **Le seuil `SEUIL_NUM = 0.9`** (T9) qui décide numérique / catégoriel est un
   choix rond, pas une mesure sur des decks réels. Il est **dit à l'écran** quand
   il tranche, ce qui rend le choix visible ; à réviser si un deck réel le prend en
   défaut.
