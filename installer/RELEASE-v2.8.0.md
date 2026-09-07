# Deepotus Video Gen — Release notes

## 🐙 Deepotus Video Gen v2.8.0 — "Le transfert entre machines"

**Tout ce qu'une installation a créé peut désormais changer de machine — et
vos clés d'API ne bougent pas.** Un bouton exporte la bibliothèque et ses
provenances, les rendus, la bible, les plans de communication, les documents
vectoriels, les séries de cartes et les modèles 3D vers un disque ou une clé ;
un autre les reprend sur l'installation qui reçoit. Les deux montrent leur
avancement, fichier par fichier.

### Transfert entre machines
- **Une catégorie dédiée dans les Réglages** — « Transfert entre machines »,
  en bas de la liste, avec ses deux gestes : *Exporter…* et *Importer…*.
- **Le choix de la destination** : les volumes détectés (disques, Bureau,
  Documents) avec leur place libre, ou un chemin saisi à la main. La place
  nécessaire est comparée à la place disponible **avant** d'écrire la moindre
  ligne.
- **Un modal d'avancement** : la phase en cours, le pourcentage, le nombre de
  fichiers, le poids et le nom du fichier qui passe. À la fin, le chemin exact
  du paquet.
- **Les clés d'API ne partent JAMAIS.** Le fichier `.env` et ses variantes sont
  écartés, comme les journaux, les fichiers WAL et tout ce que l'application
  sait reconstruire (caches, aperçus, rendus temporaires).
- **La base part dans un état cohérent** : un `backup()` SQLite, jamais une
  copie d'octets — celle-ci laisse les dernières écritures dans le journal
  (mesuré : 105 enregistrements au lieu de 116).
- **L'import FUSIONNE, il n'écrase pas.** Ce que la machine réceptrice possède
  déjà reste intact, et un second import du même paquet n'ajoute rien.
- **Les chemins sont ré-ancrés** : les six colonnes qui portent un chemin
  absolu de la machine d'origine sont réécrites sur la racine locale — sans
  quoi la bibliothèque pointerait dans le vide.
- **Un paquet illisible se refuse en le disant** : manifeste absent, format
  inconnu, base manquante — chaque refus nomme sa cause.

### Sous le capot
- Cinq routes locales (`/api/transfer/destinations`, `export`, `inspect`,
  `import`, `jobs/{id}`), toutes réservées à la machine elle-même.
- L'avancement se lit au moment de la demande et non à la création du travail :
  une copie figée laissait la barre à « 0 % » pendant tout un export.
- Deux bancs neufs : 38 contrôles côté service (deux postes simulés, racines et
  identifiants différents, base d'origine laissée OUVERTE en WAL pour que la
  cohérence de l'instantané soit réellement exercée) et 41 côté écran (le bloc
  injecté doit ÊTRE la couche octet pour octet, et celle-ci s'exécute sous
  node).
- Le patcher de bundle lit et écrit désormais en octets : le mode texte
  repliait 17 204 fins de ligne CRLF en silence.

### Rappel
Le script `scripts\export-migration.ps1`, lui, copie l'installation **avec**
les clés : il sert à déménager un poste entier, pas à partager du contenu. Le
nouveau bouton est le geste à préférer pour envoyer votre travail ailleurs.
