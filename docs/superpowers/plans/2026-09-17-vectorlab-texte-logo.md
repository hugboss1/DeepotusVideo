# Vectorlab — Texte & logo : sélecteur de typographie, édition en place, contours, 3D — plan d'exécution

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> (exécution inline, TDD strict : RED constaté au banc avant chaque module pur).

> Demande du 17/09/2026 : « plus de fenêtre pour le texte : un véritable
> sélecteur de texte avec une bibliothèque de typos, l'édition des contours
> de la typo, tout pour générer un logo imprimable en 3D avec extrusion ».
> Après le lot « design aéré » (`33c4e7d`). D7 : zéro API — les polices
> sont celles du dist (OFL) et celles que l'utilisateur dépose ;
> `queryLocalFonts` du navigateur est proposé quand il existe.

> **RELEVÉ DE LIVRAISON (17/09/2026) : LIVRÉ, PROUVÉ EN RÉEL, DÉPLOYÉ — Python touché : RELANCE du backend installé (8765) par l'utilisateur.**
>
> **Livré** (commits `054f0ec`→`05a5b7a`, poussés) : `mod-typo.js` —
> bibliothèque de polices (16 OFL du dist + déposées + système par
> `queryLocalFonts` quand le navigateur l'offre), `@font-face` injectés,
> éditeur de texte EN PLACE (zone de saisie sur la scène dans la police, le
> corps et la couleur du texte ; Entrée valide, Maj+Entrée = ligne, Échap
> annule, double-clic réédite) — plus aucun `prompt` sur le chemin nominal
> —, panneau Texte (contenu, sélecteur VISUEL des polices, dépôt d'une
> police TTF / OTF / WOFF, polices du système, corps, graisse,
> interlettrage, interligne, ancre, « un chemin par glyphe », Contours,
> Logo 3D, Épaissir ±, → cadre, sur le chemin) ; modèle : texte
> multi-lignes en `<tspan>`, `style.ancre`, `op_texte_vectoriser` par liste
> de glyphes → groupe de chemins aux ids neufs ; export : les textes en
> polices de bibliothèque deviennent des chemins (un SVG chargé en `<img>`
> ne charge aucune police) ; backend `fonts_service.py` (`DATA_ROOT/fonts`,
> magic vérifié, nom assaini, chemin refusé) + `GET /fonts`, `POST
> /fonts/upload`, `GET /fonts/user/{name}` ; les rangées Fonte / 3D du
> panneau Apparence ont migré dans le panneau Texte.
>
> **TDD** : RED ×3 (typo.test.mjs sur la vraie Anton.ttf, pytest magasin +
> routes) ; node **970 contrôles sur 60 bancs**, pytest `test_vector_docs`
> **40 passed** (+3).
>
> **Prouvé en réel** (8799, viewport 1400×900, `window.prompt` piégé :
> jamais appelé) : 16 polices, 16 `@font-face`, Anton chargée par
> `document.fonts` ; outil Texte + clic → texte posé et éditeur en place
> focalisé (Anton 48 px) ; « DEEP » + Entrée → texte `Anton` 48, largeur
> écran 86 px, outil revenu à la sélection ; sélecteur → **Bebas Neue**
> (bouton actif, `font-family` du DOM), corps 72, ancre `middle`
> (`text-anchor`), deux lignes → **2 tspans** ; double-clic → éditeur
> rouvert avec « DEEP⏎OTUS », Échap → contenu intact ; Contours par glyphe →
> groupe de **8 chemins** « DEEPOTUS », evenodd, 8 `<path>` au DOM ; outil
> Nœuds sur une lettre → **22 ancres** ; contour ± 2 → chemin plus large (24
> → 28 px) ; export : 0 `<text>` restant, `tx9` devenu `<path>` evenodd ;
> Logo 3D → dialogue Impression 3D ouvert en mode **logo**, aperçu 3D
> présent, le texte vectorisé ; dépôt d'une police par le champ fichier →
> « Ma-Typo » déposée, 17 polices et 17 `@font-face`, chargée, listée par le
> serveur, texte dans cette police vectorisé.
>
> **Deux défauts attrapés par la preuve** : des liaisons orphelines des
> anciennes rangées Fonte (mod-style) cassaient tout rendu avec un texte
> sélectionné ; après la pose d'un texte l'outil restait « texte » et le
> double-clic ne rééditait pas.
>
> **Déployé** : 12 fichiers (= base `a1cc6ce` par hash-object, 3 absents)
> → sauvegarde `_backup_predeploy_2026-09-17k-vectorlab-texte` → `git
> archive 05a5b7a` → **12 = cible, 116/116 du Vectorlab = cible**, pré-vol
> `import app.main` + `fonts_service` OK. **`routes.py` et
> `fonts_service.py` touchés : l'utilisateur relance le backend installé.**
>
> **Reste** : les polices du système ne sont pas prouvées (permission du
> navigateur) ; le rendu du texte à l'écran dépend des polices chargées par
> `@font-face` (celles du système s'affichent si installées) ; l'éditeur en
> place ignore la rotation d'un texte ; la graisse ne s'applique pas aux
> contours (opentype prend la police telle quelle) ; l'édition des glyphes
> passe par les outils Nœuds / Coin / booléens existants.

**Goal :** l'outil Texte pose un texte et l'édite EN PLACE (zone de saisie
sur la scène, Entrée valide, Maj+Entrée = nouvelle ligne, Échap annule ;
double-clic pour rééditer) ; un panneau « Texte » avec un sélecteur de
polices VISUEL (chaque nom rendu dans sa police : bibliothèque OFL du dist +
polices déposées + polices du système si le navigateur les donne), corps,
graisse, interlettrage, interligne, alignement ; « Contours » : le texte
devient des chemins (un par glyphe ou un seul), éditables aux nœuds,
épaississables (contour ±), booléens ; « → Logo 3D » enchaîne contours puis
le dialogue Impression 3D en mode logo (biseau, évidement, STL / 3MF).

**Architecture :** `mod-typo.js` — partie PURE bancable (familles de
polices : `polices_toutes(lib, user, systeme)`, `font_face_css(polices,
base)`, `police_fichier_valide(nom, octets)` (magic TTF / OTF / WOFF /
WOFF2), `glyphes_separes(font, texte, taille, x, y, interlettrage)` →
`[{car, d}]`, `texte_multi_d(font, lignes, taille, x, y, interlettrage,
interligne, ancre)`) et `initTypo(VL)` (injection des `@font-face`, panneau
Texte, éditeur en place, sélecteur visuel, dépôt de police, vectorisation,
logo 3D, remplacement des `prompt()` de mod-tools par `VL.editerTexte`) ;
`mod-doc.js` : le `texte` accepte plusieurs lignes (`<tspan x dy>`,
`style.interligne`, `style.ancre` start | middle | end) et
`op_texte_vectoriser` accepte une liste de chemins (un par glyphe → groupe
d'objets `path`, ids neufs) ; backend `fonts_service.py` (dossier
`DATA_ROOT/fonts`, liste, dépôt vérifié par magic, lecture) + routes `GET
/fonts`, `POST /fonts/upload`, `GET /fonts/user/{name}` ; `mod-export.js`
convertit à l'export les textes en polices de bibliothèque en chemins (un
SVG chargé en `<img>` ne charge aucune police).

**Décisions :** l'éditeur en place est un `<textarea>` superposé (police,
corps, couleur du texte), pas un contentEditable ; le sélecteur visuel est
une grille de noms rendus dans leur police (`@font-face` sur `/fonts/…` et
`/api/fonts/user/…`) ; une police déposée est GLOBALE (bibliothèque du
poste), pas liée au document ; les polices du système passent par
`queryLocalFonts()` (bouton, permission du navigateur, absence tolérée) et
se vectorisent par leur `blob()` ; « un chemin par glyphe » pose un groupe
(les lettres se déplacent et s'éditent séparément) ; « → Logo 3D » exige un
texte vectorisé (il le fait d'abord) puis ouvre `VL.impression("logo")`.

## Tasks
1. `mod-typo.js` pur (banc `typo.test.mjs`, vraie Anton.ttf) + `mod-doc.js` texte multi-lignes / ancre + vectorisation par glyphe (banc étendu).
2. Backend `fonts_service.py` + routes (pytest RED : liste, dépôt TTF / refus, lecture, nom hors patron).
3. UI `initTypo` + mod-tools (plus de prompt) + mod-style (rangée Fonte déléguée) + mod-export (textes → chemins) + index / CSS / core ; miroir pytest.
4. Preuve en réel, déploiement (Python touché → relance), relevé.
