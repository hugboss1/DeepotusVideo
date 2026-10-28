# t312 — Mesure de la lecture locale d'un scan (28/10/2026)

Tâche 7 du plan `docs/superpowers/plans/2026-10-28-t312-scan-texte.md`. Décisions utilisateur du 28/10 : pas de
Tesseract ; 10 pages test **fabriquées** avec texte de référence (pas de pages réelles).

## Méthode

- **Pages** : `scripts/scan_mesure.py --sortie <dossier> [--json r.json]` les fabrique avec Pillow (polices de
  `C:/Windows/Fonts` : Georgia, Times New Roman, Garamond, Arial), à 150 dpi, en A5 (874 × 1240 px) ou A4
  (1240 × 1754 px). Textes de référence : prose originale écrite pour le banc. Les pages, les références et les
  textes lus vont dans le dossier `--sortie` (hors dépôt) ; le script se relance à l'identique.
- **Chemin mesuré** : celui des routes `/api/scan/lire` — `scan_pages.charger` (comme l'envoi de fichiers) puis
  `scan_lecture._lire_ocr` (Windows.Media.Ocr par `scan_ocr.lire_page`, puis `scan_nettoyage.nettoyer`). Langue
  `fr` pour les cas FR, `en` pour les cas EN ; puis une seconde lecture en `auto`.
- **CER / WER** : distance de Levenshtein (caractères / mots) rapportée à la référence ; blancs normalisés (sauts de
  ligne et de paragraphe = une espace), apostrophes ’ ‘ ramenées à '. Les paragraphes sont comptés à part.
- **Mots incertains** : un mot lu est « faux » si son cœur (sans la ponctuation collée) diffère du mot de référence
  aligné (alignement mot à mot par Levenshtein), ou s'il est en trop. Un mot MANQUANT n'a pas de mot lu à marquer : il
  compte dans le WER, pas dans le rappel. Précision = marqués faux / marqués ; rappel = faux marqués / faux.
- **Durée** : temps de `_lire_ocr` divisé par le nombre de pages (PowerShell lancé à chaque page compris).
- Machine : Windows 11 Pro, langues OCR `fr-FR` et `en-US` installées. Aucun appel réseau.

## Résultats (langue choisie)

| Cas | Page | Pages | Mots réf. | CER | WER | Mots faux | Marqués | Précision / rappel | § lus/réf. | s/page |
|---|---|---|---|---|---|---|---|---|---|---|
| fr1 | Une colonne simple (Georgia 11 pt, A5) | 1 | 153 | 0,00 % | 0,00 % | 0 | 0 | — / — | 4/4 | 1,14 |
| fr2 | Deux colonnes (Times 11 pt, A4) | 1 | 183 | 0,00 % | 0,00 % | 0 | 0 | — / — | 5/5 | 0,99 |
| fr3 | Césures en fin de ligne (Times 12 pt, colonne étroite) | 1 | 82 | 0,91 % | 3,66 % | 3 | 0 | — / 0 % | 3/3 | 1,10 |
| fr4 | Folios + titre courant, 2 pages (Garamond 12,5 pt) | 2 | 246 | 0,55 % | 2,44 % | 6 | 0 | — / 0 % | 6/6 | 1,08 |
| fr5 | Dialogues à tirets cadratins (Times 12 pt) | 1 | 122 | 0,31 % | 0,82 % | 1 | 0 | — / 0 % | 9/9 | 1,09 |
| en1 | Faible contraste, gris (168) sur blanc cassé (Arial 10,5 pt) | 1 | 168 | 0,00 % | 0,00 % | 0 | 0 | — / — | 4/4 | 1,10 |
| en2 | Petite police 9 pt (Times, A4) | 1 | 253 | 0,14 % | 0,40 % | 1 | 0 | — / 0 % | 6/6 | 1,02 |
| en3 | Rotation de 1° (Georgia 11 pt) | 1 | 172 | 0,56 % | 0,58 % | 0 | 0 | — / — | 4/4 | 1,14 |
| en4 | Texte justifié (Times 12 pt) | 1 | 143 | 0,00 % | 0,00 % | 0 | 0 | — / — | 3/3 | 1,25 |
| en5 | Chiffres et unités (Arial 10,5 pt) | 1 | 155 | 0,90 % | 3,87 % | 5 | 0 | — / 0 % | 4/4 | 1,09 |

### Moyennes

| Langue | CER moyen | WER moyen | Mots faux / mots réf. | s/page | Paragraphes justes |
|---|---|---|---|---|---|
| Français (5 cas, 6 pages) | **0,35 %** | **1,38 %** | 10 / 786 | **1,08** | 5/5 cas |
| Anglais (5 cas, 5 pages) | **0,32 %** | **0,97 %** | 6 / 891 | **1,12** | 5/5 cas |

Folios (42, 43) et titre courant « LES CARNETS DU FLEUVE » de la paire fr4 : tous retirés ; la phrase coupée entre
les deux pages se recolle. Deux colonnes (fr2) : gauche puis droite, le paragraphe coupé par le bas de colonne
continue sans saut. Césures (fr3, 8 coupures) : 7 recollées, la 8e (« souterr-/ain. ») a perdu sa suite à la lecture (limite 3).

### Mode « auto » (deux passes fr-FR + en-US)

| Cas | Langue retenue | CER | Marqués | Précision / rappel | s/page |
|---|---|---|---|---|---|
| fr1 | fr | 0,00 % | 10 | 0 % / — | 2,24 |
| fr2 | fr | 0,00 % | 9 | 0 % / — | 2,05 |
| fr3 | fr | 0,91 % | 12 | 0 % / 0 % | 2,21 |
| fr4 | fr | 0,55 % | 32 | 3 % / 17 % | 2,21 |
| fr5 | fr | 0,31 % | 11 | 0 % / 0 % | 2,17 |
| en1 | **fr** | 0,22 % | 2 | 100 % / 100 % | 2,22 |
| en2 | **fr** | 0,14 % | 3 | 67 % / 100 % | 2,08 |
| en3 | **fr** | 0,89 % | 3 | 100 % / 100 % | 2,28 |
| en4 | **fr** | 0,13 % | 1 | 100 % / 100 % | 2,19 |
| en5 | **fr** | 1,03 % | 2 | 100 % / 33 % | 2,17 |

Moyennes auto : FR CER 0,35 % (74 marqués, 1 juste) ; EN CER 0,48 % (11 marqués, 10 justes) ; ~2,2 s/page.

## Limites observées

1. **Mots incertains sans valeur en langue choisie** : 0 mot marqué sur les 10 cas, rappel 0 % sur 16 mots faux.
   Les erreurs de Windows.Media.Ocr sont des mots plausibles faits de lettres (« mam » pour « main », « qul »,
   « farme », « semame », « moms », « librmy ») ou une majuscule fautive (« Immédiatement », « Immobiles ») ;
   la règle de la Décision 3 (chiffres mêlés aux lettres, signes inhabituels, répétitions) ne peut pas les voir.
   Aucun réglage de seuil n'y change rien : il faudrait un lexique (mot absent du dictionnaire de la langue) — piste
   pour un lot suivant, pas dans t312. L'écran doit donc inviter à relire, pas promettre que tout faux est surligné.
2. **Mode auto** : (a) la langue retenue est TOUJOURS « fr » sur les pages anglaises — les deux passes ont 0 mot
   incertain, et l'égalité va au français (Décision 2) ; le texte reste bon (CER 0,48 % contre 0,32 %), seule
   l'étiquette de langue est fausse. (b) Sur les pages françaises, la passe en-US lit mal les accents et le Garamond
   (« lumiére », « å », « nviére », « pcnssons ») : chaque désaccord marque un mot JUSTE de la passe gardée
   (précision 1 sur 74). Sur les pages anglaises, au contraire, les désaccords tombent bien (10 sur 11).
   Recommandation (non faite ici, c'est une décision de conception) : départager par un score de mots courants de
   chaque langue plutôt que par le nombre d'incertains, et ne marquer un désaccord que si la passe de l'AUTRE langue
   que celle retenue lit un mot du lexique. En attendant, le défaut de l'écran (Français) est le bon choix.
3. **Mots courts perdus par l'OCR** : « ain. » (fin de « souterrain » coupé, seul sur sa ligne, fr3) et « When »
   (premier mot d'une ligne, page tournée de 1°, en3) ne sont pas rendus par Windows.Media.Ocr (vérifié sur la sortie
   brute de `lire_page`) — ce n'est pas le nettoyage. Effet : une césure qui reste « souterr- » en fin de paragraphe.
4. **Chiffres et symboles** (en5) : « -12 °C » lu « -12 0 C » (degré lu zéro), « 11:20 » lu « 1 1 », « 1,240 »
   lu « 1 ,240 ». Aucun n'est marqué (chiffres seuls). Les unités usuelles (kg, km/h, L, MB, %) passent.
5. **Diacritiques** : « À » lu « A », « boîte » lu « boite » (Garamond) ; en Times et Georgia, les accents passent.
6. Ce qui se lit bien malgré les pièges : faible contraste (gris 168 sur fond 246, grâce à l'`autocontrast`),
   9 pt à 150 dpi, rotation de 1°, justifié, dialogues à tirets cadratins (9 paragraphes sur 9).
7. Durée : ~1,1 s par page et par passe (le lancement de PowerShell compte pour l'essentiel) ; le mode auto double.
   Dix pages = ~11 s en langue choisie, ~22 s en auto : sous le délai de 90 s de l'écran.

## Correctif fait à partir de la mesure

- **Colonne de droite courte, lignes déphasées** (premier tirage de fr2, colonnes déséquilibrées : 20 lignes à
  gauche, 5 à droite, la droite décalée d'une demi-ligne par un écart de paragraphe) : **CER 39,5 %**, les cinq
  lignes de droite lues en travers des cinq premières de gauche. Cause : `_coupe_valide` exige des lignes « côte à
  côte », et `_chevauche` demandait un recouvrement vertical d'au moins **50 %** de la hauteur ; ici 10 px sur 21
  (48 %). Seuil ramené à **15 %** (`scan_nettoyage._chevauche`) : des lignes déphasées d'une colonne voisine se
  recouvrent de 20 à 45 % ; des lignes qui alternent sans se toucher (le cas adversaire 3f : répliques courtes et
  lignes en retrait) ne se recouvrent pas du tout et restent une seule colonne. Bancs : `test_scan_nettoyage.py` 10h
  (rouge avant, vert après) et 10i (garde de 3f) — 104 PASS. Après correctif, la même page se lit dans l'ordre (CER 0,00 %, relancée avec ces colonnes) ; la
  mesure publiée ci-dessus emploie des colonnes équilibrées (le cas courant).

Aucun autre seuil n'est changé : les erreurs restantes viennent de l'OCR (limites 1, 3, 4, 5) ou d'une décision de
conception (limite 2).
