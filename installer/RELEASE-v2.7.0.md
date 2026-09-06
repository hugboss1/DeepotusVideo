# Deepotus Video Gen — Release notes

## 🐙 Deepotus Video Gen v2.7.0 — "La table de montage"

**Le Montage devient un vrai banc de travail, le Vectorlab un atelier de
vitrail, et la facture cesse d'inventer une dépense.** L'écran de montage
gagne les projets nommés, le remplacement de source d'un plan, une timeline
qui s'étend au lieu de rogner, une barre d'outils flottante, le son des plans
extrait sur la piste de dialogue, une transcription qui vise juste dans
dix-sept langues, la traduction des répliques, et deux sortes de pistes
vidéo. Le tout mesuré : le banc du bundle passe de 855 à 1 301 contrôles.

### La table de montage
- **Projets nommés** : créer, dupliquer, ouvrir, supprimer — la sauvegarde
  automatique suit le projet ouvert, et une construction depuis la
  Bibliothèque ne devient jamais votre sauvegarde à votre insu.
- **La timeline s'étend au lieu de rogner** : poser une vidéo de 6 s près de
  la fin ne la coupe plus ; la durée du projet grandit et la note le dit. La
  durée se règle aussi à la main, à côté du zoom.
- **Le son d'un plan suit sa vidéo** : une vidéo posée sur V1 reçoit son
  jumeau audio sur la piste de dialogue (un seul « Annuler » retire les
  deux) ; « Extraire le son → A1 » dans l'inspecteur pour les plans déjà
  posés ; la route `has-audio` sonde sans décoder.
- **La transcription vise juste** : elle transcrit les clips de la piste de
  dialogue (un appel par fichier, coût annoncé avant le clic), pose les mots
  au temps du CLIP et non du fichier, et propose dix-sept langues dont
  « auto » (détection par le moteur).
- **Traduire les répliques** : un sélecteur « vers » et un bouton avec sa
  pastille de coût ; les temps sont conservés, un compte de lignes faux ne
  détruit rien, un Annuler restaure.
- **Deux sortes de pistes vidéo** : « vidéo » (plein cadre, son extrait) et
  « incrust. » (image dans l'image réglable, muette) ; les pistes V3+ ne
  sont plus des fantômes — aperçu, inspecteur, trajectoires.
- **Remplacer la source d'un plan** sans perdre ses réglages, avec retour
  arrière ; un plan dont la source n'est pas une vidéo porte une chip
  cliquable au lieu de faire échouer l'aperçu en silence.
- **Barre d'outils flottante** (handoff claude.design) : onglet OUTILS,
  déplaçable et aimantée, raccourci `O`, clavier complet, `prefers-reduced-motion`.

### Vectorlab — l'atelier de vitrail
- Les panneaux de verre se **tracent au glisser** : baie à arc, rosette,
  grille losangée, plomb libre — déterministes par graine.
- Un panneau posé reste **retouchable** : gamme, travées, plomb, joints,
  « nouveau tirage ».
- **Gammes de verre** : la fiche épinglée, Chartres, Or & ambre, Forêt,
  Aube, et une gamme personnelle (curseurs T/S/V, banque de treize verres).
- **Illustration IA** : décrire, le modèle configuré pose des masses de
  verre vectorielles — réponse filtrée serveur, appel payant annoncé.

### Moteurs et 3D
- **Seedance 2.5** et **Nano Banana Pro** dans toutes les listes.
- **Tripo H3.1** partout, la chaîne **Tripo → Meshy** (le volume depuis
  quatre vues, la texture chez Meshy), le Plateau et sa prévisualisation,
  la phase D de la spec Magnific (capacités par moteur, fiche du maillage,
  contrôle de silhouette).

### La facture qui cesse d'inventer une dépense
- La pastille de coût n'affiche plus un total qui mélange estimations et
  dépenses réelles : « ≥ $ » quand une part n'est pas tarifée, l'infobulle
  explique, et les jobs internes (proxys du montage) ne polluent ni le
  projet ni la facture.

### Sous le capot
- Bancs autonomes : bundle 855 → **1 301**, deux bancs neufs (transcription
  ciblée 62, traduction 29), media 88, et la règle des assertions négatives
  passée sur les dix bancs — chaque ligne prouvée par mutation.
- Chaîne de patchers : 66 ancres, sonde aval à 60, marqueurs de la pastille
  à 7 ; le patch de version reste le dernier maillon.
- Migration : aucune table ni colonne nouvelle — vos données restent telles
  quelles ; l'installeur met à jour par-dessus l'existant.
