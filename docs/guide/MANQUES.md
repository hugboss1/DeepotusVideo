# Guide v3 : ce qui manque au guide v2.8.0

Généré par `scripts/guide/relever_manques.py` : ne pas éditer à la main.

- 1094 fonctions visibles livrées depuis le 07/09/2026 (v2.8.0) ; 42 sont payantes.
- 194 fonctions décrites par le guide v2.8.0 (22 chapitres c0-c21).
- 37 chapitres dans le sommaire v3, en 6 familles.

Chaque chapitre liste d'abord ce que l'ancien guide disait de FAUX (à corriger), puis les fonctions manquantes. Le lot coche une ligne quand le chapitre l'explique.

## Démarrer

### Faire le tour de l'application (`tour`, lot t171, reprend : nouveau) — 9 manques

**Application (coque, comportements transversaux)** — accès : Toute l'application : lanceur Windows, toutes les pages et tous les labs

- [x] **Adresse nommée deepotus.localhost** : Le lanceur ouvre l'application à l'adresse http://deepotus.localhost:8765 au lieu d'une adresse IP. — *Raccourci de lancement de l'app* (commits 1484969e, 81f42b75 · fusion 44cd1214)
- [x] **Dialogues maison partout** : Toutes les confirmations, alertes et saisies de l'Atelier, du Card Forge, du Studio 3D, du Vectorlab et de l'app principale passent par un même dialogue aux couleurs Deepotus, plus aucune boîte native du navigateur. — *Dialogue maison (confirmer / informer / saisir) ; au Vectorlab, brouillon proposé par « Restaurer » / « Repartir du serveur »* (commits 8815cba4, 0965ea6b, ec479987 · fusion 44cd1214)
- [x] **Titres d'onglets « Deepotus — <outil> »** : Chaque onglet du navigateur porte le nom de l'outil ouvert (ex. « Deepotus — Vectorlab »). (commit 1484969e · fusion 44cd1214)
- [x] **Clé absente = message clair (503)** : Quand une clé de fournisseur manque, l'app répond partout le même refus lisible (« non configurée », « configure la clé ») au lieu d'erreurs disparates. (PR #48 · commit 4bb39655 · P1 #11)
- [x] **Erreurs serveur lisibles** : Un refus qui n'est pas en JSON affiche « HTTP <code> : <texte du serveur> » au lieu d'un simple code. — *Bandeau d'erreur (ex. « Run failed: HTTP 500 : Internal Server Error »)* (PR #47 · commit fe5ae334 · P1 #10)
- [x] **Génération payante réservée au PC** : Les sept routes de génération payantes (vidéo, lots, HeyGen, images, composition) refusent tout client qui n'est pas ce PC. (PR #51 · commit 001e3295 · P1 #14)
- [x] **Écritures réservées à la machine locale** : Aucun autre appareil du réseau ne peut modifier, générer ou dépenser : toute écriture vers l'app depuis un autre hôte est refusée (« Écriture réservée à la machine locale »), les lectures restent ouvertes. (PR #51 · commits 001e3295, 838f9689 · P1 #14)
- [x] **Import d'images : homonymes conservés** : Une image du même nom qu'une existante n'écrase plus rien : elle devient nom-1, nom-2… (PR #96 · commit e3d06489)
- [x] **Import d'images : non-images refusées** : Un fichier qui n'est pas une vraie image (PNG, JPEG, WebP, GIF, BMP, AVIF) est refusé avec un message qui le nomme, et rien n'entre en Bibliothèque. — *Tout dépôt / upload d'image* (PR #96 · commit e3d06489)

### Installer, choisir sa langue, mettre à jour (`installer`, lot t171, reprend : c0) — 21 manques

À corriger dans l'ancien texte :

- [ ] « Settings → API keys », bouton « Save » (libellés anglais ; UI désormais traduite FR/EN, Réglages refondus : coffre à clés #20, test de clé, recherche #22, plafonds #16, mise à jour #18)
- [ ] « Collez vos clés … puis redémarrez l'app » (clés à chaud #17 : redémarrage plus nécessaire)
- [ ] « palette de commandes ⌘K → « Replay onboarding » » (glyphe macOS sur app Windows ; libellé anglais)
- [ ] Pastilles « fal / heygen / voice » : à vérifier vs barre actuelle
- [ ] Tableau des clés : ni Meshy, ni coffre DPAPI, ni plafonds de dépense, ni OAuth YouTube/Instagram/TikTok du Scheduler
- [ ] Coûts « HeyGen ≈ 6 crédits » (HeyGen v3 = wallet USD)

**Traduction FR/EN de l'interface** — accès : Langue choisie à l'installation, puis Réglages → « Langue de l'interface »

- [x] **Choix de la langue à l'installation** : La langue choisie dans l'installeur (français ou anglais) devient la langue de l'interface, sans écraser un choix déjà fait. — *Installeur → écran de langue* (PR #262 · commit 368f29ea · t134 (L0))
- [x] **Traduction automatique des écrans pas encore migrés** : En anglais, les textes français connus sont traduits à l'affichage dans l'app et les huit labs (jamais vos saisies) ; le serveur reçoit aussi la langue choisie. (PR #262 · commit 368f29ea · t134 (L0))
- [x] **Bibliothèque traduite** : L'écran Bibliothèque est entièrement traduit. (PR #272 · commit c1addc0a · t141 (L1))
- [x] **Coque et navigation traduites** : Barre latérale, en-tête, accueil et navigation entièrement en français ou en anglais, dates relatives comprises. (PR #272 · commit c1addc0a · t141 (L1))
- [x] **Réglages traduits (14 onglets)** : Les 14 onglets des Réglages et la recherche des Réglages s'affichent dans la langue choisie. (PR #272 · commit c1addc0a · t141 (L1))
- [x] **Catalogues du serveur dans la langue choisie** : Les listes d'effets, transitions, préréglages de livraison et titres envoyées par le serveur arrivent traduites selon la langue de l'interface. (PR #279 · commit 5c5eb59f · t144 (L4))
- [x] **News traduit** : L'écran News est traduit. (PR #276 · commit f395cfdf · t142 (L2))
- [x] **Quick traduit** : L'écran Quick passe en anglais ou en français selon la langue. (PR #276 · commit f395cfdf · t142 (L2))
- [x] **Raccourcis clavier affichés dans la langue** : Les sections et noms de touches des raccourcis (Maj/Shift, Échap/Esc, Suppr/Del) s'affichent traduits. — *Liste des raccourcis du Montage / Son & VFX* (PR #279 · commits 5c5eb59f, 5938d724 · t144 (L4))
- [x] **Rack VFX traduit** : Le rack d'effets visuels est traduit. (PR #279 · commit 5c5eb59f · t144 (L4))
- [x] **SFX Studio traduit** : Le studio d'effets sonores est traduit. (PR #279 · commit 5c5eb59f · t144 (L4))
- [x] **Scheduler traduit** : Le Scheduler est traduit, dates, jours et vues Semaine / Mois compris selon la langue. (PR #276 · commit f395cfdf · t142 (L2))
- [x] **Son & VFX traduit** : L'écran Son & VFX et le panneau Son & VFX du Montage sont traduits. (PR #279 · commit 5c5eb59f · t144 (L4))
- [x] **Studio traduit** : Le Studio, son catalogue de nœuds et ses messages sont traduits. (PR #276 · commit f395cfdf · t142 (L2))
- [x] **Templates traduits** : L'écran Templates (dont les kits et les tables de gabarits) est traduit. (PR #276 · commit f395cfdf · t142 (L2))
- [x] **Épisodes traduit** : L'écran Épisodes est traduit. (PR #276 · commit f395cfdf · t142 (L2))
- [x] **Dialogues maison traduits** : Les boutons et textes des dialogues maison suivent la langue choisie. (PR #290 · commit c4306b8d · t145 (L5))
- [x] **Montage traduit** : L'écran Montage (728 libellés) s'affiche dans la langue choisie. (PR #289 · commit 68927356 · t143 (L3))
- [x] **Sous-titres traduits** : L'éditeur de sous-titres est traduit. (PR #290 · commit c4306b8d · t145 (L5))
- [x] **Transfert entre machines traduit** : L'écran de transfert (export, import, lots, intégrité) est traduit. (PR #290 · commit c4306b8d · t145 (L5))
- [x] **Étiquettes des plans en anglais** : Les petites étiquettes posées sur les plans (sans sous-titre, muet) s'affichent aussi en anglais. (PR #290 · commit b7e47469 · t145 (L5))

### Brancher ses clés et ses moteurs d'IA (`cles`, lot t171, reprend : c11) — 0 manques

À corriger dans l'ancien texte :

- [ ] Badges « v1.15 » (h2) et « v1.21 » (tip Gemini)
- [ ] « Depuis la v1.15, vous choisissez… »
- [ ] « Provider defaults », « Local LLM (Ollama) », « missing » (anglais)
- [ ] « redémarrez le backend/l'app » après Save
- [ ] Aucune capture


### Maîtriser ses dépenses (`budget`, lot t171, reprend : nouveau) — 0 manques


### Régler l'application, personas et marque (`reglages`, lot t171, reprend : c1, c13) — 36 manques

À corriger dans l'ancien texte :

- [ ] « Settings → Personas », « New persona » (libellés anglais)
- [ ] « Save brand », « Reset to deepotus », « Logo… » (anglais)
- [ ] Lien avec kits de marque des Templates (/branding = kit actif) non décrit

**Réglages (Settings)** — accès : Barre latérale → Settings (Réglages) ; 14 onglets : Clés d'API, Fournisseurs par défaut, Comptes connectés, Identité visuelle (Branding), Personas, News, Pack de sous-titres, Tarifs et budget, Diagnostic, Coffre, Appareils, Transfert entre machines, Chemins, Apparence ; URL directe ?section=diag pour le Diagnostic

- [x] **Clé Figma (FIGMA_TOKEN)** : Le jeton Figma, exigé par l'import Figma de la Bibliothèque et des Templates, s'enregistre maintenant depuis les Réglages. — *Réglages → Clés d'API → rangée « Figma (import de calques) » (en dernier)* (PR #38 · commit 904d917e · P1 #2)
- [x] **Plafond vidéo par requête et durée max par clip** : Deux champs de l'onglet Tarifs bornent le coût d'une génération vidéo et les secondes générées par clip ; le Studio envoie le coût affiché comme plafond et l'enregistrement des tarifs ne remplace plus vos valeurs posées à la main. — *Réglages → Tarifs et budget → « Plafond vidéo par requête » et « Secondes générées max par clip »* (PR #46 · commit cc0453f7 · P1 #9)
- [x] **Alerte au seuil de plafond** : Un bandeau prévient une fois par mois quand un plafond atteint le pourcentage choisi. — *Réglages → Tarifs et budget → Plafonds du mois → champ « Alerte à (% d'un plafond) »* (PR #54 · commit 17dae285 · tâche #16)
- [x] **Archive chiffrée des clés** : Un fichier .dzk qui emporte vos clés (coffre et .env), vos plafonds et votre grille de prix vers un second poste ou le téléphone, protégé par son propre mot de passe. — *Réglages → Coffre → Archive chiffrée → « Exporter l'archive » / « Importer une archive… »* (PR #58 · PR #59 · commits cac0c119, 11204441 · tâche #20)
- [x] **Bandeau « version disponible »** : Une carte annonce la nouvelle version ; Télécharger récupère l'installeur (pourcentage puis chemin du fichier, rien n'est lancé tout seul) ; Plus tard la masque pour cette version. — *Carte de mise à jour → « Télécharger » / « Plus tard » / « Notes »* (PR #56 · commit 9239fd20 · tâche #18)
- [x] **Bouton Tester par clé** : Chaque ligne de clé a un bouton Tester (appel sans dépense, clé relue côté serveur) ; la clé est aussi testée dans la foulée de l'enregistrement et le message du serveur est affiché. — *Réglages → Clés d'API → « Tester » sur la ligne* (PR #55 · commit d828268b · tâche #17)
- [x] **Clés appliquées à chaud** : Une clé enregistrée depuis l'interface sert tout de suite, sans redémarrer l'application (plus aucune promesse de redémarrage). — *Réglages → Clés d'API → saisir → Save* (PR #55 · commit d828268b · tâche #17)
- [x] **Coffre : changer le mot de passe** : Rechiffre le coffre avec un nouveau mot de passe (8 caractères au moins, saisi deux fois). — *Réglages → Coffre → « Changer le mot de passe » → « Changer »* (PR #59 · commit 11204441 · tâche #20)
- [x] **Coffre : ouvrir / fermer** : Ouvrir déchiffre le coffre et rend ses clés actives tout de suite ; Fermer les retire de la mémoire (écrire, tester ou importer une clé est alors refusé). — *Réglages → Coffre → « Ouvrir » / « Fermer »* (PR #59 · commit 11204441 · tâche #20)
- [x] **Coffre : retenir sur ce PC** : Le coffre s'ouvre seul au lancement pour cette session Windows (DPAPI) ; Ne plus retenir redemande le mot de passe. — *Réglages → Coffre → « Retenir sur ce PC » / « Ne plus retenir »* (PR #59 · commit 11204441 · tâche #20)
- [x] **Coffre à clés : poser le coffre** : Vos clés secrètes sont chiffrées par un mot de passe maître (AES-256-GCM) et quittent le fichier .env en clair. — *Réglages → Coffre → mot de passe saisi deux fois → « Poser le coffre » → confirmation* (PR #58 · PR #59 · commits cac0c119, 11204441 · tâche #20)
- [x] **Confirmation au dépassement de plafond (402)** *(coût variable)* : Quand un tir dépasserait un plafond, un dialogue maison s'ouvre partout dans l'app : on peut tirer quand même (la même requête repart) ou annuler avec un message lisible. — *Dialogue « Tirer quand même » / « Annuler »* (PR #54 · commit 17dae285 · tâche #16)
- [x] **Guides fournisseurs** : Chaque ligne de clé a un lien Guide qui ouvre la page du fournisseur où créer la clé, avec ses tarifs. — *Réglages → Clés d'API → « Guide »* (PR #55 · commit d828268b · tâche #17)
- [x] **Onglet Diagnostic** : Un écran qui montre d'un coup la version, le poids du dossier de données par catégorie, les dernières alertes du journal, l'état de chaque clé (définie / absente, jamais affichée) et les soldes des fournisseurs. — *Réglages → Diagnostic ; bouton « Rafraîchir » (relit clés, disque mesuré 5 min, journal et soldes)* (PR #52 · commit b4dedbc9 · tâche #15)
- [x] **Pastille de clé à trois états** : Chaque clé affiche où elle vit et si elle est utilisable : au .env, au coffre, ou coffre verrouillé (qui renvoie vers l'onglet Coffre). — *Réglages → Clés d'API (pastille de chaque ligne)* (PR #59 · commit 11204441 · tâche #20)
- [x] **Plafonds de dépense mensuels par moteur** : Fixez un plafond en dollars par mois pour chaque moteur payant ; au-delà, chaque tir payant demande confirmation avant de partir ; des barres montrent le dépensé (réel quand le fournisseur le dit, sinon le devis). — *Réglages → Tarifs et budget → « Plafonds du mois » (vide ou 0 = aucun) → « Enregistrer les plafonds » ; le plafond global reste le champ « Plafond de budget mensuel »* (PR #53 · PR #54 · commits 1948440f, 17dae285 · tâche #16)
- [x] **Recherche dans les Réglages** : Un champ cherche un réglage par son nom ou ses mots (sans accents ni casse) et un résultat ouvre directement la bonne section. — *Champ « Rechercher un réglage… » en tête des Réglages ; Entrée ouvre le premier résultat, Échap vide le champ* (PR #61 · commit 521ed045 · tâche #22)
- [x] **Tableau des dépenses réel contre estimé** : Une ligne par moteur et par écran avec son état (réel, réel partiel n/m, estimé, estimé non rapproché), le nombre de tirs et l'écart réel − estimé, pour le mois en cours. — *Réglages → Tarifs et budget (sous les plafonds) et en bas du Diagnostic : « Dépenses du mois — réel contre estimé »* (PR #60 · commit e7e552ff · tâche #21)
- [x] **Tester une clé (Diagnostic)** : Chaque clé du Diagnostic a un bouton qui fait un appel authentifié sans dépense pour dire si elle marche (HeyGen v3 : crédits et dollars restants). — *Réglages → Diagnostic → « Tester » sur la ligne de la clé* (PR #52 · commit b4dedbc9 · tâche #15)
- [x] **Transfert : empreintes et contrôle d'intégrité** : Chaque fichier exporté porte son empreinte sha256 ; un bouton relit tout le paquet après un export ou avant un import, et l'import écarte en le nommant un fichier abîmé. — *Réglages → Transfert entre machines → « Contrôler l'intégrité »* (PR #57 · commit 7e123bed · tâche #19)
- [x] **Transfert : lots optionnels cochables** : Cases pour emporter aussi les journaux et les rebuts (corbeilles datées), décochées par défaut, avec leur poids ; les clés ne voyagent jamais, le coffre non plus. — *Réglages → Transfert entre machines → cases « Journaux » et « Rebuts — corbeilles datées »* (PR #57 · commit 7e123bed · tâche #19)
- [x] **Vérification de mise à jour** : L'app demande une fois par jour à GitHub la dernière version publiée (jamais bloquant) et l'affiche dans un bloc version en tête du Diagnostic. — *Réglages → Diagnostic → bloc version → « Vérifier » pour forcer* (PR #56 · commit 9239fd20 · tâche #18)
- [x] **Comptes connectés : TikTok** : Quatre champs TikTok (client key, secret, refresh token, audité) ; sans audit les envois restent privés. — *Réglages → Comptes connectés → TikTok* (PR #67 · PR #71 · commits 29ab8dcf, 6bdd634a · tâches #28, #31)
- [x] **Comptes connectés : YouTube et Instagram** : YouTube et Instagram s'activent automatiquement dès que leurs clés sont saisies et se testent depuis l'écran. — *Réglages → Comptes connectés* (PR #67 · PR #71 · commits 29ab8dcf, 6bdd634a · tâches #28, #31)
- [x] **Connecter YouTube / TikTok (OAuth)** : Un bouton ouvre la page de consentement du réseau dans un onglet ; le jeton revient tout seul et se range au coffre (refusé si le coffre est fermé, raison affichée). — *Réglages → Comptes connectés → « Connecter »* (PR #67 · PR #71 · commits 29ab8dcf, 6bdd634a · tâches #28, #31)
- [x] **Appareil perdu : rotation des clés** : La page Appareils rappelle que révoquer ne suffit pas pour un téléphone perdu et donne les liens vers la console de chaque fournisseur pour régénérer les clés. — *Réglages → Appareils → bloc « Appareil perdu ? »* (PR #98 · commit 5d1671f9 · tâche #56)
- [x] **Liste et révocation des appareils** : La liste des appareils appairés (n / 5, date d'appairage) avec un bouton qui retire tout accès à l'un d'eux tout de suite ; ses posts et chapitres emportés reviennent au PC. — *Réglages → Appareils → « Révoquer » (confirmation)* (PR #98 · commit 5d1671f9 · tâche #56)
- [x] **Page Appareils : appairer un téléphone** : Affiche un QR valable 5 minutes pour un seul appareil ; il se ferme seul quand le téléphone l'a scanné ; cinq appareils au plus. — *Réglages → Appareils → « Appairer un appareil » → scanner avec l'application Deepotus du téléphone* (PR #98 · commit 5d1671f9 · tâche #56)
- [x] **État du réseau local** : La page Appareils dit si l'app n'écoute que ce PC ou si le réseau local est ouvert, et comment l'ouvrir au Wi-Fi (HOST dans le .env). — *Réglages → Appareils (mention « ce PC seulement » / « réseau local ouvert »)* (PR #97 · PR #98 · commits e000ef39, 5d1671f9 · tâche #56)
- [x] **Kit figé à l'envoi d'un rendu** : Un rendu de template garde le kit actif au moment de l'envoi, même si vous changez de kit pendant le rendu ; un jeton {{brand.x}} inconnu est refusé en le nommant. (PR #126 · commit dfdb0f55 · tâche #72)
- [x] **Kits de marque** : Plusieurs kits de marque (logo, nom, sous-titre, couleurs) ; les champs de Branding modifient le kit actif, dont le nom est indiqué en tête. — *Réglages → Identité visuelle (Branding) → liste des kits* (PR #126 · PR #127 · commits dfdb0f55, d563ac05 · tâche #72)
- [x] **Nouveau kit / Activer** : Créer un kit et choisir lequel est actif ; activer rafraîchit l'app et recharge les champs. — *Réglages → Branding → « Nouveau kit » ; « Activer » sur un kit (« actif » sinon)* (PR #127 · commit d563ac05 · tâche #72)
- [x] **Renommer, dupliquer, supprimer un kit** : Gérer chaque kit par le dialogue maison ; le kit actif et le dernier kit ne se suppriment pas (bouton grisé qui dit pourquoi). — *Réglages → Branding → « Renommer » / « Dupliquer » / « Supprimer »* (PR #127 · commit d563ac05 · tâche #72)
- [x] **Langue de l'interface** : Basculer l'interface entre français et anglais depuis les Réglages, appliqué à chaud. — *Réglages → rangée « Langue de l'interface »* (PR #262 · commit 368f29ea · t134)
- [x] **Modèle de voix (TTS) par défaut** : Choisir le modèle ElevenLabs avec lequel naissent les nouveaux nœuds Voiceover. — *Réglages → Fournisseurs par défaut → « Modèle de voix (TTS) par défaut »* (PR #260 · commit bfe667bb · t130)
- [x] **Modèle vidéo par défaut** : Choisir le modèle avec lequel naissent les nouveaux nœuds Seedance du Studio (les nœuds existants gardent le leur). — *Réglages → Fournisseurs par défaut → « Modèle vidéo par défaut »* (PR #260 · commit bfe667bb · t130)

### Changer d'ordinateur (`transfert`, lot t171, reprend : c16) — 0 manques

À corriger dans l'ancien texte :

- [ ] Badge « nouveau »
- [ ] Chapitre antérieur à la v2.8.0 « Le transfert entre machines » (transfert intégré à l'app, sha256 + lots, #19) : aucune mention
- [ ] « vos sessions Claude Code » dans un guide utilisateur
- [ ] Aucune capture


### Piloter depuis son téléphone (`mobile`, lot t171, reprend : nouveau) — 16 manques

**Compagnon mobile (téléphone + côté PC)** — accès : Application Deepotus du téléphone (Expo, dépôt séparé deepotus-mobile, à construire par EAS) appairée par Réglages → Appareils ; côté PC : Scheduler, Bibliothèque, Atelier → Chapitres

- [x] **Appairage par QR** : Le téléphone scanne le QR des Réglages et reçoit un jeton propre à lui ; un jeton n'ouvre que les lectures, jamais les dépenses ni les clés. — *Téléphone → Appairer → scanner le QR de Réglages → Appareils* (PR #95 · PR #97 · commits 9bd34768, dafebae2, 6960ec72 · tâche #56)
- [x] **Application téléphone (Expo)** : Une application compagnon iOS/Android en React Native / Expo, avec les écrans Accueil, Appairer, Archive, Le lot, Générer et Boîte de réception. (PR #94 · commit efaf3da2 · tâche #55)
- [x] **Archive des clés sur le téléphone** : Les clés arrivent au téléphone par l'archive chiffrée .dzk exportée du Coffre, avec son mot de passe. — *Téléphone → Archive ; PC : Réglages → Coffre → « Exporter l'archive »* (tâche #57 · mémoire mobile-appairage-56)
- [x] **Dépôt d'images du téléphone vers le PC** : Le téléphone dépose des images au PC (vérifiées, jamais de doublon, homonyme renommé) ; elles entrent dans la Bibliothèque avec la source « mobile ». (PR #101 · commit 1d597e18 · tâche #58)
- [x] **Le lot de la semaine dans la poche** : Le téléphone emporte les posts validés ; un post emporté est confié au téléphone et le PC ne le publie plus ; révoquer l'appareil rend les posts au PC. — *Téléphone → Le lot* (PR #99 · commit af5d4a4c · tâche #57)
- [x] **Ouvrir l'app au Wi-Fi (HOST)** : Par défaut l'app n'écoute que le PC ; mettre HOST=0.0.0.0 dans le .env du dossier de données l'ouvre au téléphone sur le Wi-Fi de la maison. — *Fichier .env : HOST=127.0.0.1 → HOST=0.0.0.0, puis relancer* (PR #97 · commit e000ef39 · tâche #56)
- [x] **Publier depuis le téléphone** : Le téléphone publie sur Telegram par l'API et sur X par la feuille de partage, puis l'état revient au PC. — *Téléphone → Le lot → publier ; pour X, « C'est publié » après le partage* (PR #99 · tâche #57 · mémoire mobile-appairage-56)
- [x] **Synchroniser avec le PC** : Le téléphone récupère l'index de la Bibliothèque (tailles, empreintes, provenance) et les images, avec reprise des téléchargements. — *Téléphone → « Synchroniser avec le PC »* (PR #101 · commit 1d597e18 · tâche #58)
- [x] **Boîte de réception des partages** : Ce qu'on partage vers l'app depuis le téléphone arrive dans une boîte : les images partent au PC avec leur destination notée, textes et liens restent sur le téléphone. — *Partager vers Deepotus → Téléphone → Boîte* (tâche #59 · mémoire mobile-generation-59)
- [x] **Chapitre emporté hors ligne** : Emporter un chapitre sur le téléphone, l'écrire et l'annoter sans réseau, puis le rendre au PC ; un conflit garde le texte du téléphone au journal. — *Téléphone → Chapitres → prendre / rendre* (PR #105 · commit d41b610a · tâche #59)
- [x] **Chapitre protégé sur le PC** : Pendant qu'il est emporté, le chapitre est en lecture seule sur le PC avec un bandeau, et peut être repris de force. — *Atelier → Chapitres → bandeau « Emporté par le téléphone » → « Reprendre sur le PC »* (PR #105 · commit d41b610a · tâche #59)
- [x] **Dépenses du téléphone comptées au PC** : Les tirs payants faits sur le téléphone entrent dans le registre des dépenses du PC (catégorie mobile), comptés une seule fois, dans les plafonds et le tableau réel/estimé. — *Téléphone : coût dit avant chaque tir, plafond du jour, journal* (PR #103 · commit 20da061e · tâche #58)
- [x] **Générer des images depuis le téléphone** **payant** : Génération et retouche d'images depuis le téléphone, au prix de la grille du PC mise en cache (refus si elle est trop vieille). — *Téléphone → Générer* (tâche #59 · mémoire mobile-generation-59)
- [x] **Journal des conflits de chapitre** : Les textes du téléphone écartés (conflit, ré-import du manuscrit) restent au journal, à copier ou à reprendre. — *Atelier → Chapitres → journal* (PR #105 · commit d41b610a · tâche #59)
- [x] **Notifications du téléphone** : Le téléphone est prévenu d'un rendu terminé ou échoué, d'un post publié, d'un post qui attend un geste, d'un échec de publication et d'un plafond approché ou dépassé, sans doublon. (PR #102 · commit 5178f8e3 · tâche #58)
- [x] **Projet épinglé sur le téléphone** : Un seul projet de la Bibliothèque est épinglé sur le téléphone et voyage en entier. — *Bibliothèque → projet « épinglé sur le téléphone »* (PR #144 · commit 0305bd6c · tâche #78)

## Créer des vidéos

### Sortir une vidéo en quelques minutes (Quick) (`quick`, lot t172, reprend : c2, c3, c4, c5, c6) — 21 manques

À corriger dans l'ancien texte :

- [ ] Onglet « Library » (Bibliothèque unifiée v2.6 : DAM #77, projets #78, lignée #79, fiche #80, corbeille/doublons #81, recherche CLIP #82, Envoyer vers — rien de cela n'est décrit)
- [ ] « Describe an image to create », « Prompt manager », « Refine with AI », « Use this prompt » (libellés anglais)
- [ ] Glyphes ✏️ et ▶ comme icônes du Job Dock (icônes Deepotus Glyph remplacent les emojis)
- [ ] « Generate » (libellé anglais)
- [ ] « durée (5–60 s) » et Seedance comme modèle implicite (t130 a changé les modèles vidéo par défaut) ; saisie Quick refaite (t129)
- [ ] Badge « v1.15 » sur le h3 du premier chargement
- [ ] « ⏱ » emoji dans le titre h3
- [ ] Migration HeyGen v3 (Avatar III par look, wallet USD, listes en cache disque) non reflétée ; « crédits »
- [ ] « 1 281 avatars » chiffré dans la légende de capture
- [ ] « ⏱ Duration master » (emoji comme icône, libellé anglais)
- [ ] Onglet « Renders » de la Library (Bibliothèque unifiée)
- [ ] Badges « v1.15.6 » (h2) et « v1.17.0 » (h3 Voix off)
- [ ] « Quick → Voice Over » (libellé anglais ; Voicebox Quick/Studio + ducking t131 non décrit)
- [ ] Aucune mention du tiroir Sons / Son & VFX (stems T100, tiroir T101, chanson/voix #102, matte/recherche #103)
- [ ] Glyphes ▶ et ★ comme icônes
- [ ] Aucune capture

**Quick** — accès : Barre latérale → Quick (onglets Seedance, HeyGen, Composition, Voice Over)

- [x] **Interrupteur « Voice (HeyGen comp) » retiré** *(coût variable)* : Le contrôle inerte qui aurait lancé une voix off payante est retiré. (PR #39 · commit 08936b14 · P1 #3)
- [x] **Aperçu propre à chaque onglet** : L'aperçu central montre ce qui concerne l'onglet ouvert (et non plus toujours l'image de départ) ; colonne source à 360 px. (PR #93 · commit de0ef08c · tâche #54)
- [x] **Caméra dans un prompt libre** : Le mouvement de caméra choisi s'ajoute aussi à un prompt écrit à la main. (PR #91 · commit 1179e902 · tâche #54)
- [x] **Curseurs caméra** : Six curseurs de caméra traduits en une phrase adaptée à la famille du modèle, affichée avant le rendu. — *Section Caméra (repliée) : six curseurs et la phrase produite* (PR #92 · commits b2060c2b, c7247087 · tâche #54)
- [x] **Galerie de mouvements de caméra** : Grille de 11 mouvements de caméra × 3 styles en vignettes animées rendues en local (mémo visuel, pas une prédiction du modèle) pour choisir à l'œil. — *Section Parameters → bouton Galerie* (PR #91 · commits 1179e902, 40115df6 · tâche #54)
- [x] **Glisser-déposer une image** : La zone de dépôt accepte réellement une image glissée (refuse ce qui n'est pas une image) et l'envoie dans la Bibliothèque. — *Glisser une image sur la zone de départ ou de fin* (PR #93 · commit de0ef08c · tâche #54)
- [x] **Image de fin grisée avec la raison** : Quand le modèle vidéo choisi n'accepte pas d'image de fin, le champ est remplacé par la raison (et la liste des modèles qui l'acceptent) ; une fin refusée n'est jamais envoyée. — *Onglet Seedance → champ image de fin* (PR #84 · commit 7273f3bc · tâche #49)
- [x] **Lip-sync Kling sur la voix off** **payant** : Synchronise les lèvres du clip Seedance sur la voix off choisie, vérifié et chiffré avant le rendu payant. — *Onglet Seedance → bloc Lip-sync : case (dit payant), choix de la voix, bornes et prix affichés* (PR #89 · commits 359c4f1d, 3029b6ec · tâche #52)
- [x] **Presets nommés par onglet** : Enregistre les réglages d'un onglet sous un nom et les réapplique d'un clic, sur les quatre onglets (voix comprise). — *Rangée Presets en tête de chaque onglet* (PR #90 · commits 7eb5d156, 8a2b1914 · tâche #53)
- [x] **Prolonger le clip (Veo 3.1 Fast)** **payant** : Ajoute environ 7 s générées à un clip déjà rendu ; la source est d'abord mesurée, le prompt et le son (avec ou sans, prix affiché sur chaque bouton) sont demandés, un 402 du plafond annule proprement. — *Envoyer vers → « Prolonger le clip »* (PR #88 · commits fba52d5e, 5b9bcef9 · tâche #51)
- [x] **Recette d'un rendu** : Chaque rendu Quick enregistre ses réglages avant tout appel payant, pour pouvoir être rouvert à l'identique. (PR #83 · commit f3cd66b8 · tâche #48)
- [x] **Rouvrir dans Quick** : Rouvre un rendu dans Quick avec tous ses réglages préremplis. — *Bibliothèque → Renders → « Rouvrir dans Quick », ou icône sur la carte de la file de rendus* (PR #83 · commit 3e41a612 · tâche #48)
- [x] **Sous-titres gravés** *(coût variable)* : Grave des sous-titres sur le rendu : calage gratuit d'un texte connu sur la voix, ou transcription payante seulement si on la coche sans texte. — *Bloc Sous-titres après Duration : interrupteur, style, langue, texte à caler, case de transcription* (PR #86 · commits 0972892f, 442bba30 · tâche #50)
- [x] **Musique baissée sous la voix** : Dans les rendus avec voix off et musique, la musique est désormais baissée automatiquement sous la voix (ducking par défaut). (PR #217 · commit a96a5a56 · T102)
- [x] **Fournisseur de voix Voicebox / ElevenLabs** *(coût variable)* : Choix du fournisseur de voix off par génération (mémorisé) ; Voicebox (local, coût nul) masque modèle et réglage fin ; un fournisseur indisponible est refusé, jamais remplacé en silence. — *Sélecteur de fournisseur de voix* (PR #261 · commit a85913ca · t131)
- [x] **La saisie est gardée** : Quitter Quick puis y revenir retrouve les réglages en cours. (PR #259 · commit 84be3d26 · t129)
- [x] **Pré-écoute Voicebox** : Écoute une voix Voicebox avant de générer, mise en cache. (PR #261 · commit a85913ca · t131)
**Application (coque, comportements transversaux)** — accès : Toute l'application : lanceur Windows, toutes les pages et tous les labs

- [x] **HeyGen : avatar depuis une photo (v3)** **payant** : La création d'avatar à partir d'une photo passe par la v3 ; une image WebP mal nommée est reconnue et convertie. (PR #37 · commit 2975b6df)
- [x] **HeyGen : listes d'avatars et de voix en cache** : Les listes de looks et de voix HeyGen s'affichent tout de suite depuis un cache disque rafraîchi en fond (au lieu de plusieurs minutes). (PR #37 · commit 2975b6df)
- [x] **HeyGen : solde wallet en dollars** : Le solde HeyGen est lu dans le wallet et affiché en dollars (santé, soldes des coûts, Diagnostic). (PR #37 · commit 2975b6df)
- [x] **HeyGen API v3 : Avatar III par look** **payant** : Toutes les vidéos HeyGen passent par l'API v3 ; le moteur par défaut est Avatar III choisi selon le look de l'avatar, et les pauses du script sont gardées. (PR #37 · commit 2975b6df)

### Composer avec le Studio (`studio`, lot t172, reprend : c9, c15) — 31 manques

À corriger dans l'ancien texte :

- [ ] Badge « ENRICHI »
- [ ] « Starter graphs », « New », « Run » (libellés anglais)
- [ ] Épingles Studio (#67), recette/duel (#67-71), Studio R8, avatar HeyGen décalé, table de Montage (v2.7.0, plusieurs séquences t117, courbes t118, Bézier t128) non décrits
- [ ] Badge « nouveau » (date de v1.15.7)
- [ ] « Deux ajouts au node editor » / « désormais » formulés comme nouveautés
- [ ] Aucune capture

**Studio (éditeur de nœuds)** — accès : Barre latérale → Studio ; réglages associés dans Réglages → Tarifs et Réglages → Provider defaults

- [x] **Dictée dans les champs IA** : Un micro dicte le texte par la reconnaissance vocale du navigateur, inséré au curseur. — *Barre du champ IA → micro* (PR #33 · PR #49 · commits 339273ba, de322d63 · retours IA)
- [x] **Dictée transcrite (repli)** **payant** : Si le navigateur ne sait pas dicter, l'enregistrement est transcrit par le serveur après un devis et votre accord (« Non » par défaut). — *Micro → dialogue d'accord avec le montant* (PR #33 · commits 339273ba, 74eb7157 · retours IA)
- [x] **Erreurs de génération lisibles** : « Run failed » affiche la phrase du serveur au lieu du JSON brut, et le texte d'une réponse non-JSON (HTTP 500 : …). (PR #33 · PR #47 · commits 03e5a03d, fe5ae334 · P1 #10)
- [x] **Format HeyGen affiché** : L'inspecteur d'un nœud HeyGen qui alimente un modèle composé affiche le format imposé par la région du template (ex. 16:9). (PR #35 · commit 0b943e71 · tâche #35)
- [x] **GPT Image 2.5 (flare, sunburst)** **payant** : Nouveaux modèles d'image GPT Image 2.5 flare et sunburst, en direct OpenAI ou via fal (0,053 $ l'image, fond transparent possible) ; aussi dans le Material Forge. — *Sélecteur de modèle d'image* (PR #33 · commits fc2d7ad8, 8fc4a3b8 · retours 26/09)
- [x] **Garde de coût vidéo** *(coût variable)* : Une génération vidéo au-dessus du montant annoncé ou du plafond par requête est refusée (402) avant tout appel ; la durée générée est plafonnée à 10 s, ffmpeg prolonge le reste. (PR #33 · commit dc38d0da · retours 26/09)
- [x] **Liseré des champs IA** : Les champs de prompt envoyés à une IA ont un liseré dégradé, holographique au focus, avec un badge IA (dans toute l'application et les pages à part). (PR #33 · commit 42927eab · retours IA)
- [x] **Ouvrir un graphe (icône)** : L'ancien menu déroulant « Open graph… » devient un bouton icône qui déroule la liste des graphes. — *Bouton icône dossier ; Échap ou clic dehors ferme* (PR #35 · commit 0b943e71 · tâche #35)
- [x] **Pastille de modèle des champs IA** : Une pastille dans la barre du champ montre le modèle choisi par la vue et permet d'en changer (clavier compris) ; modèles sans clé grisés avec la clé manquante, prix affiché. — *Barre du champ IA → pastille* (PR #33 · commits 074b7402, 21f7cec6 · retours IA)
- [x] **Plus aucune fenêtre prompt() native** : Dix autres saisies (favori d'animation, lien Figma, taille d'impression 3D, renommer un rendu 3D, une image, un asset…) passent par le dialogue maison. (PR #36 · commit 6d429b88 · tâche #36)
- [x] **Replier l'inspecteur** : Le panneau de droite se replie et l'état est mémorisé au rechargement. — *Bouton dans l'en-tête de l'inspecteur ou du graphe, poignée INSPECTOR sur le canevas* (PR #35 · commit 0b943e71 · tâche #35)
- [x] **Save par dialogue maison** : Le nom du graphe à enregistrer se saisit dans le dialogue de l'application (nom courant prérempli). — *Save → Entrée enregistre, Échap annule* (PR #36 · commit dc2f8501 · tâche #36)
- [x] **Seedance 2.5 par défaut** **payant** : Les nouveaux nœuds Seedance utilisent Seedance 2.5 ; les graphes enregistrés gardent leur modèle ; seedance-v1-pro reste au choix. (PR #33 · commits dc38d0da, 437fba6a · retours 26/09)
- [x] **Coût ≈ $ juste et envoyé en max_usd** *(coût variable)* : Le ≈ $ du graphe est calculé comme la garde du serveur et envoyé comme montant maximal ; un Run sur une estimation périmée est refusé (sauf Preview). — *Run* (PR #46 · commit cc0453f7 · tâche #46 (P1 #9))
- [x] **Deux plafonds vidéo réglables** : Le plafond en dollars par requête vidéo et la durée générée maximale se règlent ; l'enregistrement des tarifs fusionne au lieu d'écraser. — *Réglages → Tarifs (deux champs)* (PR #46 · commit cc0453f7 · tâche #46)
- [x] **Panneau Graph branché** : Format et Render name modifient vraiment le nœud Render ; FPS inerte retiré ; « Audio master » devient un résumé en lecture seule. — *Panneau Graph* (PR #39 · commit 08936b14 · P1 #3)
- [x] **Vignette de coût des modèles vidéo** : La vignette de prix du sélecteur de modèle reflète exactement la garde (durée facturée plafonnée à 10 s). (PR #46 · commits cc0453f7, 4462cf7c · tâche #46)
- [x] **Importer un graphe JSON** : Ouvre un graphe JSON validé par le serveur (5 Mo max) ; les sources manquantes et liens jetés sont listés, remplacement confirmé si un graphe est ouvert ; rien n'est enregistré sans Save. — *Bouton « Importer » à gauche de « Ouvrir un graphe »* (PR #121 · commit d5eb5d44 · tâche #69)
- [x] **Pile des rendus et « Utiliser »** : Les huit derniers rendus d'un nœud sont listés (date, « autres réglages », « en aval ») et on choisit celui qui alimente la suite. — *Inspecteur du nœud → liste sous l'épingle → « Utiliser »* (PR #120 · commit 7728e7ec · tâche #68)
- [x] **Régénérer ce nœud** **payant** : Force la régénération payante d'un nœud épinglé. — *Panneau d'épingle → « Régénérer ce nœud »* (PR #119 · commit 2007013b · tâche #67)
- [x] **Épingler le résultat d'un nœud** : Le rendu payé d'un nœud Seedance ou HeyGen est épinglé automatiquement et réemployé gratuitement tant que sa requête réelle ne change pas ; le ≈ $ dit les nœuds réutilisés. — *Inspecteur du nœud → panneau d'épingle* (PR #118 · PR #119 · commits 49e8e953, 2007013b · tâche #67)
- [x] **Duel de moteurs** **payant** : Sur un nœud Image gen, lance le même prompt sur deux modèles en parallèle après confirmation du coût des deux, puis compare côte à côte (coût, durée) et garde le gagnant ; le perdant reste en Bibliothèque. — *Inspecteur du nœud Image gen → panneau Duel → « Garder »* (PR #124 · commit abb65463 · tâche #71)
- [x] **Envoyer vers → Lancer une recette** **payant** : Lance une recette du Studio à partir d'une image de la Bibliothèque : chaque texte se garde ou se change, devis montré et confirmé. — *Envoyer vers → « Lancer une recette… »* (PR #125 · commit 17e2f3c3 · tâche #71)
- [x] **Envoyer vers → Studio nouveau graphe** : Ouvre un rendu dans un graphe neuf (Existing render → Render) à sa durée réelle. — *Envoyer vers → « Studio — nouveau graphe »* (PR #125 · commit 17e2f3c3 · tâche #71)
- [x] **Figer un graphe en recette** : Transforme un graphe en recette réutilisable dont les images et textes deviennent des trous à remplir ; la liste indique le nombre de trous. — *Bouton « Recette » (avant « Importer »), nom par dialogue* (PR #123 · commit e1956da5 · tâche #71)
- [x] **Lancer une recette** **payant** : Relance une recette avec de nouvelles valeurs après un devis confirmé, avec les mêmes gardes que le rendu ; nœuds inchangés réemployés gratuitement. — *Dialogue de devis puis confirmation* (PR #123 · PR #125 · commits e1956da5, 17e2f3c3 · tâche #71)
- [x] **Résultat image par image** : Le tiroir de résultat avance image par image (cadence lue dans le fichier, compteur f N / M), pause au premier pas. — *Touches « , » et « . » tiroir ouvert, ← → sur la réglette, boutons ‹ ›* (PR #122 · commit 8fffeb91 · tâche #70)
- [x] **Ducking au Render** : Le réglage de ducking de l'AudioMix baisse la musique sous la voix au rendu (léger, moyen, fort). — *Nœud AudioMix → ducking* (PR #261 · commit a85913ca · t131)
- [x] **Fournisseur de voix du nœud Voiceover** *(coût variable)* : Le nœud Voiceover choisit Voicebox ou ElevenLabs par génération. — *Inspecteur du nœud Voiceover → fournisseur* (PR #261 · commit a85913ca · t131)
- [x] **Modèles vidéo et TTS par défaut** : Choix du modèle vidéo et du modèle de voix avec lesquels naissent les nouveaux nœuds Seedance et Voiceover ; les nœuds existants gardent le leur. — *Réglages → Provider defaults (deux rangées)* (PR #260 · commit bfe667bb · t130)
**Application (coque, comportements transversaux)** — accès : Toute l'application : lanceur Windows, toutes les pages et tous les labs

- [x] **Studio sans fenêtre native** : Le bouton Save du Studio et les dix autres demandes de texte passent par le dialogue maison. — *Studio → Save → nom saisi dans le dialogue* (PR #36 · commits dc2f8501, 6d429b88)

### Réutiliser des modèles et des kits de marque (`modeles`, lot t172, reprend : c8) — 26 manques

À corriger dans l'ancien texte :

- [ ] « Save layout », « New template », « Open in Studio » (libellés anglais)
- [ ] Kits de marque (#72-73), masques + texte (#74), image fixe (#75), animations (#76) des Templates non décrits

**Templates (Modèles)** — accès : Barre latérale → Modèles (Templates) ; kits dans Réglages → Branding

- [x] **Format HeyGen suivant la région** : L'avatar HeyGen est généré au format le plus proche de sa région (fini la bande vide et la tête coupée). (commit 7f85396d)
- [x] **Recherche des gabarits** : Le champ Search filtre la galerie par nom, id ou tags (sans casse ni accents) avec un compteur n / total. — *Galerie → Search…* (PR #39 · commit 08936b14 · P1 #3)
- [x] **Régions enregistrées sans perte** : Un réglage décoché (ex. Pulse) ou un champ avancé reste tel qu'édité après Save. (PR #40 · commit 4e201b6f · P1 #4)
- [x] **Animations d'entrée et de sortie** : Chaque région visible peut entrer et sortir en fondu, glissement ou pop, avec durée, délai et courbe (douce, linéaire, rebond). — *Inspecteur → section « Animation »* (PR #139 · PR #142 · commits f6594cb1, 64ec3897 · tâche #76)
- [x] **Aperçu exact du texte** : Rend la case de texte par le vrai moteur pour voir le résultat final. — *Section Texte → « Aperçu exact »* (PR #134 · commit 8759381a · tâche #74)
- [x] **Coupe franche à faible cadence** : Un gabarit séquentiel sous 12,5 i/s ne perd plus l'acte suivant à la coupe. (PR #136 · commit aed97e08)
- [x] **Enregistrer comme composant** : Transforme des régions cochées en composant nommé, avec option de les remplacer par une instance. — *Rangée « Add: » → « Enregistrer comme composant »* (PR #148 · commit e0cf9a52 · tâche #76)
- [x] **Export SVG** : Télécharge un SVG du gabarit (kit appliqué, échantillons embarqués) à glisser dans Figma. — *Éditeur → « SVG ↓ »* (PR #150 · commit 5856f86a · tâche #76)
- [x] **Exporter l'image** : Exporte le gabarit tel qu'à l'écran en image fixe PNG, JPEG ou WebP, qui entre dans la Bibliothèque. — *Éditeur → « Exporter l'image » (après « Open in Studio »)* (PR #137 · commit d9823ff7 · tâche #75)
- [x] **Flash cyan** : Nouvelle transition « cyan flash » (vrai flash de couleur, couleur au choix) ; « flash » reste blanc. — *Studio → Layout séquentiel ou Concatenate → transition* (PR #151 · PR #152 · commits 2e6fb100, 6aa77513 · tâche #76)
- [x] **Gérer les kits de marque** : Liste des kits avec Activer, Renommer, Dupliquer, Supprimer (pas l'actif ni le dernier) et Nouveau kit ; l'en-tête dit quel kit les champs modifient. — *Réglages → Branding* (PR #127 · commit d563ac05 · tâche #72)
- [x] **Importer un cadre Figma** : Transforme un cadre Figma en gabarit éditable (textes, images en échantillon, formes) ; le coût en appels Figma est annoncé avant. — *Galerie → « Importer un cadre Figma… » (jeton FIGMA_TOKEN requis)* (PR #149 · PR #150 · commits 96b26db7, 5856f86a · tâche #76)
- [x] **Masques de région** : Les cases image et vidéo prennent une forme : arrondi, ellipse, polygone, fenêtres ajourées, bord adouci et liseré coloré, avec aperçu sur la toile. — *Inspecteur → section « Masque »* (PR #130 · PR #132 · commits 95fed159, 756b9c51 · tâche #74)
- [x] **Ouvrir dans le Vectorlab** : Ouvre le gabarit tel qu'à l'écran comme document éditable du Vectorlab dans un onglet. — *Éditeur → « Ouvrir dans le Vectorlab »* (PR #150 · commit 5856f86a · tâche #76)
- [x] **Plusieurs kits de marque** : Plusieurs kits (nom, couleurs, logo) ; les gabarits utilisent des jetons {{brand.x}} et un rendu fige le kit actif au moment de l'envoi. (PR #126 · commit dfdb0f55 · tâche #72)
- [x] **Poser un composant** : Insère un groupe de régions réutilisable (dont « Bandeau titre » fourni) au centre de la toile. — *Rangée « Add: » → « + Composant »* (PR #147 · PR #148 · commits 75f79fe1, e0cf9a52 · tâche #76)
- [x] **Rejouer en … (autre format)** : Crée une copie d'un gabarit dans un autre format avec aperçu avant / après et avertissements ; l'original ne change pas. — *Galerie → « Rejouer en : » → « Enregistrer la copie » ou « Annuler »* (PR #128 · PR #129 · commits 03eedf1a, bb4a3cd8 · tâche #73)
- [x] **Rejouer sur la toile** : Rejoue une approximation des animations sur la toile de l'éditeur. — *Section Animation → « Rejouer sur la toile »* (PR #142 · commit 64ec3897 · tâche #76)
- [x] **Styles et effets de texte** : Cinq styles prêts (Aucun effet, Sous-titre réseau, Néon, Bandeau, Titre dégradé), contour, ombre nette ou floue, fond arrondi, dégradé. — *Inspecteur → section « Texte »* (PR #133 · PR #134 · commit 8759381a · tâche #74)
- [x] **Surcharger une instance** : Change les textes et couleurs de chaque sous-région d'une instance, ou revient au composant. — *Inspecteur de l'instance → « Rétablir »* (PR #148 · commit e0cf9a52 · tâche #76)
- [x] **Texte adaptatif** : Le texte s'ajuste à sa case (lignes puis taille, avec taille minimale). — *Inspecteur → section « Texte » → ajustement* (PR #133 · PR #134 · commits 50bd087d, 8759381a · tâche #74)
- [x] **Texte sur arc** : Pose un texte ou sous-titre sur un arc (arche ou sourire, rayon conseillé) ; un arc trop grand est réduit pour tenir. — *Section Texte → « Texte sur arc »* (PR #143 · PR #145 · commits 5eea9f4f, 37ebd857 · tâche #76)
- [x] **Transition du gabarit montrée au Studio** : Sans choix dans le Studio, le menu « Transition k → k+1 » du nœud Layout affiche la transition prévue par le gabarit. — *Studio → nœud Layout* (PR #152 · commit 6aa77513 · tâche #76)
- [x] **Vraies vignettes en galerie** : Les cartes de la galerie montrent une vraie image du gabarit. (PR #135 · PR #137 · commits 3ed090e8, d9823ff7 · tâche #75)
- [x] **Échantillon d'aperçu** : Une image de la Bibliothèque sert d'échantillon dans une case image ou vidéo pour l'aperçu et les vignettes. — *Inspecteur d'une case → choisir l'échantillon* (PR #137 · commit d9823ff7 · tâche #75)
- [x] **Éditeur de points du polygone** : Dessine le polygone d'un masque ; modèles triangle, losange, hexagone, étoile. — *Glisser déplace un point, clic ajoute, double-clic retire* (PR #132 · commit 756b9c51 · tâche #74)

### Raconter une histoire en épisodes (`chapitres`, lot t173, reprend : c7) — 21 manques

À corriger dans l'ancien texte :

- [ ] Badge « v1.15.6 »
- [ ] Glyphes ↑ ↓ ＋ ✕ ▶ comme icônes de boutons
- [ ] Chapitres #62-#66 (exports manuscrit/scénario/storyboard docx/PDF), scènes d'épisode t119, saisie Épisodes t129 non décrits
- [ ] Aucune capture

**Épisodes (Chapitres)** — accès : Barre latérale → Chapitres (page Épisodes)

- [ ] **Narrer** **payant** : Narre les scènes et range la narration complète dans la Bibliothèque audio ; une scène déjà narrée (même texte, voix, langue) n'est jamais repayée. — *Barre → Narrer* (PR #43 · commit 31e0c099 · t132)
- [ ] **Nouveau / Ouvrir / Enregistrer** : Un épisode s'enregistre et se rouvre ; un point signale les modifications non enregistrées et une confirmation protège de leur perte ; l'assemblage enregistre automatiquement. — *Barre Nouveau / Ouvrir / Enregistrer (●)* (PR #43 · commit 31e0c099 · t132, lot B de #6)
- [ ] **Scènes Seedance générées** **payant** : Les scènes « Seedance (animated) » produisent un vrai clip bouclé sur la narration, modèle et résolution par scène, devis à l'étape 4 ; un échec retombe en Ken Burns et c'est signalé. — *Étape 4 → devis puis lancement* (PR #42 · commit 9b8bd332 · P1 #6 lot A)
- [ ] **La saisie est gardée** : Le mode de Chapitres et le texte saisi sont retrouvés en revenant ; la voix choisie n'est plus réinitialisée. (PR #259 · commit 84be3d26 · t129)
**Atelier / Chapitres (manuscrit, storyboard, bible)** — accès : Vue Chapitres (page /atelier/) ; la vue Épisodes s'ouvre par Chapitres → « Flux d'origine » → « Ouvrir ▾ »

- [ ] **Scènes Seedance animées dans un épisode** **payant** : Les scènes « Seedance (animated) » d'un épisode sont réellement générées (clip court bouclé sur la narration), modèle et résolution par scène, devis affiché et garde de coût ; un échec retombe en Ken Burns signalé. — *Vue Épisodes → étape 4 : modèle + résolution par scène, devis* (PR #42 · commit 9b8bd332 · tâche #6)
- [ ] **Animatique** : Monte les plans en vidéo de répétition 540 × 960 (image de production, sinon croquis, sinon carton), muette par défaut, avant tout rendu payant. — *Bouton animatique (pellicule) → modale, progression, lecteur* (PR #112 · commit eda09ff3 · tâche #63)
- [ ] **Animatique vers le Montage (film ou reel)** : Envoie l'animatique dans un NOUVEAU projet de Montage, en film entier ou en reel de 30 s des plans les plus forts, voix témoin en A1. — *Modale de l'animatique → boutons film / reel* (PR #116 · commit 58ad8ecb · tâche #66)
- [ ] **Chapitre emporté sur le téléphone** : Un chapitre pris par le téléphone est protégé sur le PC (bandeau, éditeur en lecture seule) ; on peut le reprendre de force, et les textes en conflit sont gardés au journal. — *Bandeau « Emporté par le téléphone » → « Reprendre sur le PC »* (PR #105 · commit d41b610a · tâche #59)
- [ ] **Dérive d'identité** : Mesure l'écart de couleur et de silhouette entre l'image de production et les vues de l'entité, affiché en lecture (verdict et angle mort). — *Bouton règle sous l'image de production* (PR #110 · commit d0ee229f · tâche #62)
- [ ] **Export du manuscrit (.docx / PDF)** : Exporte le texte du chapitre en .docx ou PDF A4, pages numérotées. — *Boutons de téléchargement du chapitre* (PR #114 · commit ac88c0e8 · tâche #65)
- [ ] **Export du scénario (.docx / PDF)** : Exporte le scénario au format du métier (Courier 12, US Letter, page de titre, retraits) en .docx ou PDF. — *Boutons de téléchargement du chapitre* (PR #114 · commit ac88c0e8 · tâche #65)
- [ ] **Export du storyboard (PDF)** : Exporte le storyboard en PDF, quatre vignettes 9:16 par page A4 avec fiche et action. — *Boutons de téléchargement du chapitre* (PR #114 · commit ac88c0e8 · tâche #65)
- [ ] **Fiche Apparitions** : La fiche d'une entité liste ses mentions, plans et scènes par chapitre ; un clic sur un plan ouvre le chapitre en storyboard. — *Fiche de la bible → bouton « Apparitions »* (PR #106 · commit 45e20293 · tâche #60)
- [ ] **Image de production d'un plan** **payant** : Génère l'image d'un plan avec Nano Banana en lui donnant les vues des entités du plan comme références ; coût dit et confirmé. — *Carte de plan → bouton image (coût affiché) → confirmation* (PR #109 · commit dca3f449 · tâche #62)
- [ ] **Import Fountain / Final Draft** : Importe un scénario .fountain ou .fdx dans les scènes du chapitre, en remplaçant (scénario sauvegardé avant) ou en ajoutant à la suite. — *Bouton « Importer » → deux confirmations (remplacer ? sinon ajouter ?)* (PR #113 · commit 02267aba · tâche #64)
- [ ] **Liens plan ↔ entités** : Le découpage lie automatiquement les entités de la bible aux plans (sans LLM) ; chaque carte de plan a ses cases à cocher d'entités. — *Storyboard → cases « entités du plan » sur chaque carte* (PR #106 · commit 45e20293 · tâche #60)
- [ ] **Réécrire dans le ton de la bible** **payant** : Reformule, resserre, traduit, ou engendre une scène ou un dialogue à partir de la sélection, dans le ton de la bible ; coût dit et confirmé, proposition modifiable avant application. — *Barre de sélection → « Réécrire »* (PR #115 · commit 840c46dd · tâche #66)
- [ ] **Sortie Épisode sans rendu** : Crée un Épisode (une scène par plan, image et voix du Narrateur) sans narrer ni rendre ; narration et rendu payants restent dans la vue Épisodes. — *Storyboard → bouton « Épisode »* (PR #117 · commit a0af8cae · tâche #66)
- [ ] **Versions du texte** : Un instantané est pris à chaque écrasement du texte (dix gardés) ; comparaison côte à côte, restauration, copie d'un scénario. — *Bouton « Versions » → tiroir → « Restaurer » / « Copier »* (PR #107 · commit c2a659ad · tâche #61)
- [ ] **Voix témoin de l'animatique** **payant** : Ajoute sur demande la voix du Narrateur de la bible (ElevenLabs), devis affiché, voix en cache pour ne pas repayer. — *Modale de l'animatique → case « voix témoin » + devis* (PR #112 · commit eda09ff3 · tâche #63)
- [ ] **Vues de référence d'une entité** : Les vues d'une planche de personnage sont retrouvées gratuitement (recette v3 ou découpe vérifiée) et servent ensuite de références. (PR #108 · commit 05b18967 · tâche #62)

### Sons, voix et effets visuels (`son-vfx`, lot t173, reprend : nouveau) — 20 manques

**Son & VFX** — accès : Barre latérale → Son & VFX (écran 06) ; tiroir Sons aussi dans le Montage et dans Bibliothèque → puce Audio ; voix des personnages dans l'Atelier des Chapitres

- [ ] **Améliorer un son** : Chaîne locale égaliseur → débruitage → compresseur → normalisation à −16 LUFS, en un clic, sans fournisseur. — *Tiroir Sons → Améliorer (un clic, fichier clean_ créé)* (PR #211 · PR #214 · commit 18a4287e · T100)
- [ ] **Chanson chantée (ACE-Step, MiniMax Music 2.0)** **payant** : Génère une chanson chantée à partir de tags et de paroles (ACE-Step 5-240 s, ou MiniMax Music 2.0), chiffrée à la seconde sous la garde des plafonds. — *Son & VFX → carte musique : choisir le modèle, écrire les paroles* (PR #217 · commit a96a5a56 · T102)
- [ ] **Chercher un son par description (CLAP)** : Trouve des sons en décrivant ce qu'on veut entendre, avec un score par rangée ; nécessite un service local Clapbox ou un endpoint distant, sinon le bouton est grisé avec la raison. — *Tiroir Sons → ✧ (mode « décrire »), taper la description puis Entrée* (PR #227 · commit 25ee73c0 · T103)
- [ ] **Cloner la voix d'un personnage** **payant** : Crée une voix ElevenLabs clonée (1 à 25 prises du dossier audio) rattachée à un personnage de la bible ; un refus d'ElevenLabs garde la voix d'avant. — *Atelier → 🧬 Cloner (dialogue maison : choix des prises puis confirmation)* (PR #231 · commit 5d9df0d7 · T103)
- [ ] **Détourer le sujet d'une vidéo (BiRefNet)** **payant** : Découpe le sujet d'un plan vidéo (matte avec transparence) pour composer les effets derrière ou devant lui ; le prix fal est encore « à mesurer ». — *Rack VFX → rangée Sujet : 1er clic = devis, 2e clic = tir* (PR #223 · commit 174fde91 · T103)
- [ ] **Effets derrière / devant le sujet** : Les effets du rack se posent derrière le sujet détouré (par défaut) ou devant lui ; l'aperçu du rack passe sous le matte et le Montage suit vitesse, recadrage et zoom du plan. — *Rack VFX → bascule derrière / devant* (PR #223 · commit 174fde91 · T103)
- [ ] **Filtre Tous / Mes sons / Catalogue** : Le tiroir Sons filtre entre tous les sons, ceux de l'utilisateur et ceux du catalogue fourni. — *Tiroir Sons → bascule Tous / Mes sons / Catalogue* (PR #214 · commit c44b914f · T101)
- [ ] **Indexer / Tout réindexer** : Construit l'index de recherche des sons (seuls les fichiers nouveaux ou modifiés sont repris ; Tout réindexer repart de zéro). — *Tiroir Sons → Indexer / Tout réindexer* (PR #227 · commit 25ee73c0 · T103)
- [ ] **Isoler la voix (ElevenLabs)** **payant** : Retire le fond sonore d'une prise de voix grâce à l'isolation ElevenLabs ; le résultat entre dans la Bibliothèque avec sa mère. — *Tiroir Sons → action Isoler sur une voix : 1er clic = devis, 2e clic = tir, Échap désarme* (PR #211 · PR #214 · commit 18a4287e · T100/T101)
- [ ] **Le storyboard joue la voix du personnage** **payant** : Chaque réplique du storyboard part avec la voix et le tempérament de son personnage ; des puces de casting sur la carte plan signalent « sans voix » en ambre. — *Atelier → carte plan (puces de casting)* (PR #231 · commit 5d9df0d7 · T103)
- [ ] **Mix voix + musique (ducking)** : Mixe une voix et une musique en baissant automatiquement la musique sous la voix ; le mix entre dans la Bibliothèque avec la voix pour mère. — *Son & VFX → carte « Mix voix + musique » (trois réglages)* (PR #217 · commit a96a5a56 · T102)
- [ ] **Pré-écoute au survol** : Un son se joue quand on le survole 350 ms ; option coupée par défaut et mémorisée. — *Tiroir Sons → activer la pré-écoute au survol* (PR #214 · commit c44b914f · T101)
- [ ] **Sons voisins** : Liste les sons qui ressemblent à un son donné. — *Tiroir Sons → « ≈ » sur une rangée* (PR #227 · commit 25ee73c0 · T103)
- [ ] **Séparer en stems (Demucs)** **payant** : Découpe une musique en pistes séparées (voix, batterie, basse…) ; chaque stem devient un son de la Bibliothèque rattaché à sa mère et classé (vocals = Voix, le reste = Musique). — *Tiroir Sons → action Stems sur une musique : 1er clic arme et affiche le devis du serveur, 2e clic lance, Échap désarme* (PR #211 · PR #214 · commit 18a4287e · commit c44b914f · T100/T101)
- [ ] **Tags des sons** : Les sons portent des tags éditables (12 au plus) et la liste se cherche par tag. — *Tiroir Sons → éditer les tags d'un son ; champ de recherche* (PR #214 · commit c44b914f · T101)
- [ ] **Tempérament vocal d'un personnage** : Donne à un personnage un tempérament (émotion + voix) choisi dans une palette servie par le serveur, appliqué à chacune de ses répliques. — *Atelier → palette de tempérament du personnage* (PR #231 · commit 5d9df0d7 · T103)
- [ ] **Tiroir Sons dans la Bibliothèque** : La puce Audio de la Bibliothèque affiche le tiroir Sons toujours ouvert, au-dessus de l'import. — *Bibliothèque → puce Audio* (PR #214 · commit c44b914f · T101)
- [ ] **Tri « Plus anciens » et mère affichée** : Le tiroir Sons trie aussi du plus ancien au plus récent et montre le son d'origine (mère) d'un dérivé. — *Tiroir Sons → tri* (PR #214 · commit c44b914f · T101)
- [ ] **Voix off dirigée** **payant** : Ajoute des balises d'émotion et de jeu Eleven v3 (palette servie par le serveur, dont accents) à une voix off, montre ce qui part réellement et la chiffre avant génération ; hors v3 ou sous Voicebox les balises sont retirées et c'est dit. — *Son & VFX → carte « Voix off dirigée » : palette de balises, aperçu, générer armé par le devis* (PR #217 · commit a96a5a56 · T102)
- [ ] **Éditeur de paroles par sections** : Un squelette de paroles est proposé selon le persona et se modifie section par section ; le thème se saisit par un dialogue maison. — *Son & VFX → éditeur de sections des paroles* (PR #217 · commit a96a5a56 · T102)

### Jouer un avatar en direct (`avatar-live`, lot t168, reprend : nouveau) — 0 manques


### Monter une vidéo (`montage`, lot t174, reprend : nouveau) — 50 manques

**Montage — Édition et timeline** — accès : Entrée « Montage » de la barre latérale (écran « Montage · Timeline multipiste »), vue « Montage » de la barre basse Médias · Montage · Livraison

- [ ] **Barre OUTILS hors des pistes** : La barre d'outils flottante se place au-dessus du transport et ne recouvre plus les pistes V1/V2. — *Toujours repliable (O) et déplaçable par sa poignée.* (D-1 · commit bf8f8cbd)
- [ ] **Couper la plage en ripple** : Supprime le contenu de la plage I/O sur toutes les pistes non verrouillées et referme le trou. — *Maj+X* (D-11 · commit 064ed2db)
- [ ] **Historique complet (Ctrl+Z / Ctrl+Y)** : Toute action est désormais annulable : clips, mix, pistes, durée de la timeline, style des sous-titres, plage I/O et marqueurs, sur 50 pas. — *Ctrl+Z annule, Ctrl+Y rétablit ; deux réglages de durée ou de style à moins de 600 ms ne font qu'un pas.* (D-0 · commits 2879b362, ea29d46c, f4ef8b34)
- [ ] **Index des marqueurs** : Panneau listant les marqueurs : aller à un marqueur, changer son titre et sa couleur, le retirer. — *Ctrl+M ; clic sur une ligne = aller au marqueur.* (D-5 · commits 2bf23534, 5bc5389b)
- [ ] **Marqueurs** : Pose des marqueurs colorés et titrés sur la règle, enregistrés avec le projet. — *Maj+M pose ou retire un marqueur à la tête ; Ctrl+↑ / Ctrl+↓ vont au précédent / suivant.* (D-5 · commit 2bf23534)
- [ ] **Plage I/O de la timeline** : Pose une plage d'entrée/sortie dessinée sur la règle et enregistrée avec le projet ; elle sert au mode « remplir la plage », à la coupe de plage, au rendu partiel et à l'apprentissage du bruit. — *I pose l'entrée, U la sortie, X efface la plage.* (D-11 · commit 064ed2db)
- [ ] **Roll** : Déplace le point de coupe entre deux plans V1 sans changer la durée totale, y compris sur les coupes franches. — *Alt + glisser le losange de jonction ; l'infobulle du clip rappelle les trois gestes.* (D-3 · commits 00729c67, fa3fc2f6)
- [ ] **Six modes d'édition** : Choisit comment un média s'ajoute : écraser, insérer (pousse la suite), en fin, au-dessus (piste vidéo libre au-dessus), écraser en ripple, remplir la plage (vitesse calculée pour remplir la plage I/O, bornée 25 %–400 %). — *Rangée de modes dans le sélecteur d'assets ; une aide décrit chaque mode ; « remplir la plage » demande d'abord une plage (I / U).* (D-2 · commits 736e2123, 53bd45b2)
- [ ] **Slide** : Déplace un plan entre ses deux voisins, qui s'allongent ou se raccourcissent pour compenser. — *Maj + glisser le centre du clip.* (D-3 · commit 00729c67)
- [ ] **Slip** : Fait glisser le contenu d'un plan dans sa source sans bouger ses bornes sur la timeline. — *Alt + glisser le centre du clip.* (D-3 · commit 00729c67)
- [ ] **Échanger deux plans voisins** : Permute le clip sélectionné avec son voisin collé, en gardant les bornes extérieures du couple. — *Ctrl+← ou Ctrl+→ sur le clip sélectionné.* (D-4 · commits 1807293a, a456aae5)
- [ ] **Mini-carte de la timeline** : Bande de 30 px au-dessus de la règle montrant toute la timeline et la fenêtre visible. — *Clic sur la mini-carte = centrer la vue à cet endroit.* (D-7 · PR #24 · commit 31406130)
- [ ] **Sélectionner un trou et le refermer** : Un clic dans le vide entre deux clips sélectionne le trou ; Suppr le referme en ripple sur cette piste. — *Clic dans le vide d'une piste, puis Suppr ; Échap désélectionne.* (E-14 · PR #25 · commits 6138fd11, cc34c2c2)
- [ ] **Ajouter un fondu à la coupe** : Pose une transition à la coupe d'entrée du plan sélectionné. — *Alt+T (Ctrl+T est réservé par le navigateur), ou ☰ › Timeline.* (D-10 · PR #27 · commit 4b622fd9)
- [ ] **Copier / coller un clip entre projets** : Copie le clip sélectionné et le colle dans le même projet ou dans un autre, selon le mode d'édition courant. — *Ctrl+C / Ctrl+V, ou menu ☰ › Édition.* (D-6 · PR #27 · commit bb4f468f)
- [ ] **Découper aux changements de plan** : Analyse un clip vidéo et le coupe automatiquement à chaque changement de scène détecté. — *Clic droit sur le clip › « Découper aux changements de plan » (vidéo rendue seulement).* (D-42 · PR #28 · commit 4c48d451)
- [ ] **Exporter / importer les raccourcis** : Sauvegarde le mappage clavier dans un fichier deepotus-raccourcis.json et le recharge ; les collisions sont signalées. — *Panneau « ? » › « Exporter… » / « Importer… ».* (D-10 · PR #27 · commit 4b622fd9)
- [ ] **Plans trop longs / jump cuts** : Surligne sur V1 les plans trop longs (liseré gris pointillé) et les jump cuts d'une même source (liseré rouge). — *☰ › Affichage › « Plans trop longs / jump cuts… » : case Activer, durée maxi 2–60 s, écart mini 1–60 images.* (D-8 · PR #27 · commit b57a7825)
- [ ] **Raccourcis : preset Resolve** : Applique d'un clic un jeu de raccourcis façon DaVinci Resolve (O = sortie de plage, Ctrl+B = lame, barre d'outils sur Alt+O). — *Panneau « ? » des raccourcis › bouton « Preset Resolve ».* (D-10 · PR #27 · commit 4b622fd9)
- [ ] **Trim A/B à la jonction** : Le popover de jonction montre la dernière image du plan gauche et la première du plan droit, et décale la coupe image par image. — *Popover de jonction : « ◀ −1 » / « +1 ▶ » (Maj = dix images) ; grisé si la jonction n'est pas vidéo/vidéo.* (D-3b · PR #27 · commit 6147b72d)
- [ ] **Effets des pistes d'overlay rendus** : L'avertissement « le rendu n'emporte pas les effets des pistes d'overlay » est retiré : les effets posés sur V2 sortent bien au rendu. (t117 · PR #247 · commit 610e6f17)
- [ ] **Transitions et vitesse sur toutes les pistes vidéo** : Les pistes vidéo au-dessus de V1 (plein cadre et incrustation) ont désormais losanges de jonction, transitions, réglage de vitesse et aperçu en direct, comme V1. — *Losange de jonction, inspecteur de transition, Alt+T, vitesse dans l'inspecteur ou le menu de clip.* (t117 · PR #246, #247 · commits 155f4e96, 610e6f17)
**Montage — Interface, médias et projets** — accès : Entrée « Montage » de la barre latérale ; barre de titre du Montage, menu ☰, barre basse Médias · Montage · Livraison

- [ ] **Copie de sûreté avant d'ouvrir** : Avant d'ouvrir un autre projet, le montage non nommé en cours est mis à l'abri en projet au lieu d'être perdu. — *Automatique au clic sur « ouvrir » du panneau Projets.* (E-1 · PR #23 · commit f4b288eb)
- [ ] **Envoyer vers… Montage pose sur V1** : Une vidéo envoyée depuis la Bibliothèque arrive sur V1 avec son jumeau audio A1 (au lieu de V2). — *Bibliothèque › Envoyer vers… › Montage — clip vidéo.* (E-3 · PR #23 · commit f510e872)
- [ ] **Nouveau montage vide** : Crée un projet vide (pistes par défaut, aucun clip) qui n'est plus rempli automatiquement par les derniers rendus de la Bibliothèque. — *Panneau Projets › « nouveau » (deux clics : « nouveau ? »).* (E-1 · PR #23 · commits bdc0ccfc, f4b288eb)
- [ ] **Ouvrir dans le Montage (Studio, Chapitres)** : Un rendu terminé du Studio ou un épisode terminé de Chapitres s'ouvre directement dans le Montage, posé sur V1 à la tête avec son son en A1. — *Bouton « Ouvrir dans le Montage » sur le rendu ou l'épisode.* (E-3 · PR #23 · commit f510e872)
- [ ] **Ancrer la barre d'outils** : Pose la barre OUTILS dans le transport, en version compacte, au lieu de la laisser flotter. — *☰ › Affichage › « Ancrer la barre d'outils ».* (E-10 · PR #25 · commit 90480440)
- [ ] **Barre Preview · Rendre · Publier** : La barre de titre regroupe trois verbes : Preview 480p (gratuit), Rendre… (rendu final) et Publier (renvoie le dernier rendu final au Scheduler). — *Barre de titre du Montage ; aussi ☰ › Projet.* (E-5 · PR #24 · commit 4199cbed)
- [ ] **Boutons grisés et infobulles** : Les boutons indisponibles se grisent au lieu de disparaître et chaque bouton d'outil a une infobulle. (E-12 · PR #25 · commit dc03a697)
- [ ] **Chips de provenance et recherche** : Filtre le tiroir Médias par origine (Studio, Chapitres, Quick, News, Templates, Importés…) et par titre. — *Chips en tête du tiroir ; champ « Rechercher un titre… » (dès 2 caractères).* (E-2 · PR #24 · commit 46a40dd5)
- [ ] **Durées sur les clips** : Affiche la durée de chaque clip sur la timeline. — *Chip « durées » ou ☰ › Affichage › « Durées sur les clips ».* (E-9 · PR #24 · commit 80c79dd4)
- [ ] **Inspecteur à bascule et redimensionnable** : L'inspecteur se ferme et se rouvre, et sa largeur se règle de 260 à 480 px (mémorisée). — *Chip « inspecteur » ; glisser la poignée du bord de l'inspecteur.* (E-8 · PR #24 · commit 95f3040b)
- [ ] **Menu contextuel de clip** : Clic droit sur un clip : couper à la tête, supprimer, remplacer la source, effets, vitesse, transition, copier/coller le grade, découper aux changements de plan. — *Clic droit sur un clip ; Échap ferme.* (E-6 · PR #25 · commit a3bd6849)
- [ ] **Menu contextuel de piste** : Clic droit sur une piste : verrouiller, muet, solo, supprimer la piste ; sur une piste de sous-titres : graver, exporter, nouvelle langue. — *Clic droit sur l'en-tête de piste.* (E-6 · PR #25 · commit a3bd6849)
- [ ] **Menu principal ☰** : Menu unique en six rubriques (Projet, Édition, Timeline, Marqueurs, Affichage, Aide) listant toutes les actions avec leur raccourci. — *Bouton ☰ de la barre de titre.* (E-6 · PR #25 · commits 3208dea0, a3bd6849)
- [ ] **Séparateur lecteur / timeline** : La hauteur de la timeline se règle de 30 à 70 % de l'écran (mémorisée). — *Glisser la poignée au-dessus de la timeline.* (E-9 · PR #24 · commit 80c79dd4)
- [ ] **Tiroir Médias** : Tiroir latéral listant tous les rendus vidéo terminés, paginé, avec vignette, durée et provenance ; clic = poser à la tête de lecture. — *Onglet « médias » de la barre des tiroirs, ou « + » d'une piste vidéo ; bouton « Plus » pour charger la suite.* (E-2 · PR #24 · commits 2849626e, 46a40dd5, 2a7ce7dc)
- [ ] **Trois vues Médias · Montage · Livraison** : Une barre basse bascule l'écran entre la vue Médias (tiroir grand ouvert), la vue Montage et la vue Livraison (réglages de rendu et historique des rendus du projet). — *Barre basse « Médias · Montage · Livraison ».* (E-7 · PR #25 · commit 898b3b18)
- [ ] **Tête dans l'inspecteur** : L'inspecteur indique la position de la tête de lecture dans le plan sélectionné (HH:MM:SS:FF). — *En tête de l'inspecteur.* (E-13 · PR #25 · commit 6138fd11)
- [ ] **Voile sous les popovers de rendu** : Un voile sombre bloque l'écran sous le popover de rendu et le bandeau de fin ; un clic dessus les ferme. — *Clic sur le voile ou Échap.* (E-11 · PR #24 · commit 1abe5bda)
- [ ] **Auto-clips** **payant** : Propose 1 à 8 extraits de 15 à 60 s d'une longue vidéo, classés par l'IA (ou par une heuristique gratuite), puis crée un nouveau projet avec l'extrait choisi. — *Bouton « ✂ auto-clips » sur une ligne du tiroir Médias : texte connu (gratuit), nombre, persona, case « Classer avec l'IA (quelques centimes) », case « Payer la transcription (≈ x $) » si pas de texte, puis « Créer le projet ».* (D-41 · PR #28 · commits 9c55f40a, 11e287b3)
- [ ] **Comparer deux projets** : Affiche les différences entre le montage ouvert et un autre projet : clips ajoutés, supprimés, déplacés, rognés, modifiés. — *Bouton « ⇄ » sur une ligne du panneau Projets (grisé sur le projet ouvert) ; Échap ferme.* (D-39 · PR #27 · commit e7bed94c)
- [ ] **Filtre Good Take** : N'affiche que les rendus notés 3 étoiles ou plus, ou seulement les 5 étoiles. — *Chips « ★ 3+ » / « ★ 5 » du tiroir Médias.* (D-34 · PR #28 · commit 2c66209a)
- [ ] **Notes étoile des rendus** : Note chaque rendu de 0 à 5 étoiles, enregistré en base et transféré entre machines. — *Cinq étoiles sur chaque ligne du tiroir Médias.* (D-34 · PR #28 · commit 2c66209a)
- [ ] **Sources vides ou illisibles refusées** : Un fichier vidéo ou audio vide ou illisible est refusé dès l'import, et un rendu dont une source est illisible s'arrête en nommant le plan, la piste, le temps et le fichier. (PR #31 · commits f4a36ee3, efe39c4d)
- [ ] **Seedance 2.5 par défaut dans le Studio** **payant** : Le nœud vidéo Seedance du Studio propose Seedance 2.5 par défaut (tarif 0,473 $/s affiché) ; les graphes déjà enregistrés gardent leur modèle. — *Studio › nœud Seedance, libellé « Défaut ».* (PR #33 · commit 437fba6a)
- [ ] **Upload refusé lisible** : Un import refusé affiche le message du serveur (ex. « Fichier vide ou illisible ») au lieu d'un code brut. (PR #33 · commit 437fba6a)
- [ ] **Animatique vers le Montage** : L'animatique d'un chapitre sort en nouveau projet de Montage, en film complet ou en reel de 30 s, sans toucher à la timeline en cours. — *Chapitres › modale de l'animatique › boutons film / reel ; le Montage s'ouvre.* (tâche #66 · PR #116 · commit 58ad8ecb)
- [ ] **Projets en grille de cartes** : Le panneau Projets devient une grille de cartes avec vignette, nom et date, et les actions ouvrir, dupliquer, renommer, supprimer. — *Bouton « projets » de la barre de titre (ou ☰ › Projet › Projets…).* (E-1 / t119 · PR #253 · commit 9decadb1)
- [ ] **Un plan par scène d'épisode** : Un épisode ouvert dans le Montage est découpé en un plan par scène (vidéo et son), avec un marqueur « Scène i » par scène ; Annuler le rend en un seul plan. — *Automatique à l'ouverture d'un épisode rendu depuis le 07/10 ; Ctrl+Z pour revenir à un plan unique.* (E-3 / t119 · PR #253 · commit 9decadb1)

### Étalonner, mixer, titrer (`montage-finitions`, lot t174, reprend : nouveau) — 54 manques

**Montage — Couleur** — accès : Entrée « Montage » de la barre latérale ; inspecteur du plan › panneau « Étalonnage », rack VFX (catégorie Étalonnage / Correction), bouton « Scopes » de la rangée du lecteur

- [ ] **Accord automatique** : Neutralise automatiquement une dominante de couleur et étale la luminance du plan. — *Panneau « Étalonnage » › bouton « Auto ».* (D-28 · PR #29 · commit f60dd604)
- [ ] **Accorder sur le plan précédent** : Ajuste automatiquement les couleurs d'un plan V1 pour qu'elles correspondent au plan précédent. — *Panneau « Étalonnage » › « Accorder sur le plan précédent ».* (D-28 · PR #29 · commits 6d98732c, f60dd604)
- [ ] **Anti-banding** : Nouvel effet deband qui gomme les aplats en escalier des dégradés. — *Rack › catégorie Correction.* (D-33 · PR #29 · commit 196b175a)
- [ ] **Anti-scintillement** : Nouvel effet deflicker qui lisse les variations de luminosité. — *Rack › catégorie Correction.* (D-33 · PR #29 · commit 196b175a)
- [ ] **Copier / coller le grade** : Copie les effets couleur et le masque d'un plan et les colle sur un autre plan. — *Ctrl+Alt+C / Ctrl+Alt+V, menu de clip ou boutons « Copier le grade » / « Coller le grade » du panneau.* (D-32 · PR #29 · commit a04930f7)
- [ ] **Courbes à points M/R/V/B** : Éditeur de courbes à 16 points maximum, sur le canal maître ou chaque canal rouge, vert, bleu. — *Panneau « Étalonnage » › Courbes ; double-clic sur un point pour le retirer ; « Remettre ce canal à plat ».* (D-29 · PR #29 · commits 196b175a, f60dd604)
- [ ] **Incrustation fond vert** : Effet chromakey (couleur, similarité, mélange) avec suppression du débordement, pour les overlays V2. — *Rack › effet chromakey.* (D-33 · PR #29 · commit 196b175a)
- [ ] **Lightbox des plans** : Grille de tous les plans V1 avec leur image étalonnée ; clic = aller au plan et le sélectionner. — *☰ › Affichage › « Lightbox des plans » ; Échap ferme.* (D-32 · PR #29 · commit a04930f7)
- [ ] **Masque statique** : Limite les effets d'un plan à un rectangle ou une ellipse, avec adoucissement et inversion, sur V1 comme sur les overlays. — *Panneau « Étalonnage » › Masque : Aucun / Rectangle / Ellipse, X, Y, L, H, Adouc., Inverser ; contour visible sur le lecteur.* (D-30 · PR #29 · commits e6ea32f1, f60dd604)
- [ ] **Monochrome** : Nouvel effet de passage en noir et blanc réglable. — *Rack › effet monochrome.* (D-33 · PR #29 · commit 196b175a)
- [ ] **Netteté étendue** : La fiche Netteté gagne un choix de méthode : unsharp ou CAS. — *Rack › Netteté › mode.* (D-33 · PR #29 · commit 196b175a)
- [ ] **Roues lift / gamma / gain** : Trois roues de couleur (ombres, tons moyens, hautes lumières) et leurs maîtres pour étalonner un plan. — *Panneau « Étalonnage » › Roues ; aussi neuf curseurs dans le rack (effet roues).* (D-27 · PR #29 · commits 196b175a, f60dd604)
- [ ] **Réduction de bruit vidéo** : Nouvel effet de débruitage de l'image (hqdn3d ou atadenoise). — *Rack › catégorie Correction.* (D-33 · PR #29 · commit 196b175a)
- [ ] **Scopes** : Forme d'onde, vectorscope et histogramme de l'image étalonnée sous la tête, rafraîchis à l'arrêt. — *Bouton « Scopes » de la rangée du lecteur.* (D-31 · PR #29 · commits 4bda880b, a04930f7)
- [ ] **Teinte / saturation par bande** : Modifie la teinte et la saturation d'une seule bande de couleur (Hue vs Sat et Hue vs Hue). — *Rack › effet huesat (teinte, saturation, force, bande de couleur).* (D-29 · PR #29 · commit 196b175a)
- [ ] **Traînée (tmix)** : Effet de traînée qui mélange les images successives. — *Rack › effet tmix.* (D-33 · PR #29 · commit 196b175a)
- [ ] **Image étalonnée à l'arrêt dans le lecteur** : Tête arrêtée, le lecteur montre l'image étalonnée réelle du plan (effets, masque, cadrage, zoom) ; la lecture reste brute. (PR #32 · commits c9e2631b, 71673fa3)
- [ ] **Scopes en fenêtre flottante** : Les scopes vivent dans une fenêtre déplaçable et redimensionnable (carré 240–1024 px), position mémorisée. — *Glisser la barre de titre pour déplacer, la poignée de coin pour redimensionner, « × » pour fermer.* (D-31 · PR #32 · commit c2488ee5)
- [ ] **Aperçu à l'arrêt : vitesse, stabilisation, J1** : L'image étalonnée à l'arrêt montre aussi l'interpolation de vitesse, la stabilisation déjà analysée et les effets du clip d'ajustement J1. — *Une pastille dit si la stabilisation n'est pas encore analysée.* (PR #33 · commits a4bbc5f8, a319ef54)
- [ ] **Scopes en plein écran** : La fenêtre des scopes reste disponible lecteur en plein écran. (PR #33 · commit a319ef54)
- [ ] **Scopes fidèles au rendu** : Les scopes tiennent compte de la vitesse, de l'interpolation, de la stabilisation, du clip d'ajustement J1 et de la cadence du rendu final choisie. (P1 #8 · PR #45 · commit d79e532b)
- [ ] **Distorsion d'objectif : corriger** : Préréglage « corriger » qui redresse une distorsion en barillet ; le préréglage « coussinet » ne replie plus l'image dans les coins. — *Rack › Distorsion d'objectif › préréglage corriger.* (D-17 · t118 · PR #250 · commit 1ef65f31)
- [ ] **Lum vs Sat** : Règle la saturation séparément dans les ombres, les tons moyens et les hautes lumières (0–200 %). — *Rack › effet lumsat.* (D-29 · t118 · PR #250 · commit 1ef65f31)
- [ ] **Sat vs Sat** : Règle la saturation des couleurs ternes, moyennes et vives séparément (0–200 %). — *Rack › effet satsat.* (D-29 · t118 · PR #250 · commit 1ef65f31)
**Montage — Audio** — accès : Entrée « Montage » de la barre latérale ; rack audio du clip sélectionné, puce « ● voix off » de la barre de titre

- [ ] **Anti-ronflement** : Retire le ronflement secteur 50 ou 60 Hz et ses harmoniques. — *Rack audio › « Anti-ronflement ».* (D-25 · PR #30 · commits 4d2053f6, 0a07746b)
- [ ] **Apprendre le bruit** : Mesure le bruit sur un passage de bruit seul et l'utilise pour débruiter le clip au rendu. — *Poser une plage I/O (I puis U) sur le bruit seul, puis « Apprendre le bruit » sous le rack ; « Oublier » retire l'apprentissage.* (D-25 · PR #30 · commits 9ea55daa, 0a07746b)
- [ ] **Enregistrer une voix off** : Enregistre une prise au micro de l'ordinateur et la pose sur la piste de dialogue à l'instant où elle a commencé ; la prise est aussi rangée dans la Bibliothèque. — *Puce « ● voix off » ou Alt+R (démarrer / arrêter) ; Ctrl+Z retire la prise en un coup.* (D-26 · PR #30 · commits 22c445d4, 7aecb429)
- [ ] **Fin des débruiteurs conservée** : Les 25 dernières millisecondes d'un clip débruité ne sont plus perdues. (D-25 · PR #30)
- [ ] **Pan à puissance constante** : Le panoramique stéréo garde le même niveau perçu au centre et sur les côtés ; largeur puis pan, dans le bon ordre. — *Rack audio › stéréo.* (D-23 · PR #30 · commit 4d2053f6)
- [ ] **Plancher du débruiteur** : Le débruiteur accepte un plancher de bruit réglé à la main (0 = automatique, −20 dB au plus). — *Rack audio › débruiteur › plancher.* (D-25 · PR #30 · commit 0a07746b)
- [ ] **Écoute rendue du son d'un plan** : Le bouton d'écoute rendue du rack fonctionne aussi sur le son d'un plan vidéo. — *Rack audio › « Écouter (rendu) ».* (D-23 / D-25 · PR #30 · commit 0a07746b)
- [ ] **Égaliseur 6 bandes** : Égaliseur par clip : passe-haut, plateaux grave et aigu, quatre cloches, gains ±12 dB. — *Rack audio › « Égaliseur 6 bandes » (écoute via « Écouter (rendu) »).* (D-23 · PR #30 · commits 4d2053f6, 0a07746b)
- [ ] **Musique en boucle bornée à son clip** : Une musique sur une piste en boucle respecte le début, la fin et l'entrée de son clip, avec fondu de sortie à la fin du clip. (PR #32 · commits e845de1b, 2d3d7505)
- [ ] **Écho et réverbe sans baisser le son sec** : Le réglage « mix » de l'écho et de la réverbe dose seulement l'effet ; le son d'origine reste à son niveau (les rendus qui les utilisent sont plus forts). (PR #32 · commit 234831b8)
- [ ] **Mots transcrits à la bonne vitesse** : Les sous-titres transcrits d'un plan accéléré ou ralenti tombent au bon moment. (t120 · PR #244 · commit 6c85d8b6)
- [ ] **Voix off : prise jamais perdue en silence** : Si l'écran est quitté pendant l'envoi d'une prise, un message dit qu'elle est dans la Bibliothèque ; deux projets sans nom ne sont plus confondus. (t120 · PR #244 · commit 6c85d8b6)
**Montage — Transitions, titres et propriétés de plan** — accès : Entrée « Montage » de la barre latérale ; popover de jonction (losange entre deux plans), piste T1, inspecteur « Propriétés du plan »

- [ ] **Clips Titre (piste T1)** : Ajoute des cartons de titre sur une piste T1 gravée au rendu, au-dessus de la vidéo. — *Maj+T, chip « T+ » ou « + » de la piste T1 : pose un titre à la tête.* (D-21 · commits 3a16c8d9, 48fafc9c)
- [ ] **Fondus joués en direct** : Les fondus simple, au noir et au blanc se voient pendant la lecture sans passer par la Preview ; les autres transitions restent visibles après Preview. (D-12 · commit ccad84be)
- [ ] **Galerie de 58 transitions** : Le popover de jonction présente 58 transitions (plus la coupe et trois historiques) rangées par familles : fondus, glissements, volets, zooms, pixels, formes. — *Clic sur le losange de jonction ; aperçu animé au survol de chaque tuile.* (D-20 · commits 0ed330a1, 3d5239b0)
- [ ] **Huit gabarits de titre** : Choix entre titre plein cadre, tiers inférieur, légende, compteur, chapitre, citation, hashtag et appel à l'action, avec vignettes. — *Inspecteur « Titre — gabarit » du carton sélectionné.* (D-21 · commits fe1756a9, cd4dacfd)
- [ ] **Interpolation de vitesse** : Pour un plan accéléré ou ralenti, choisit image voisine, fondu d'images ou flux optique (lent) pour un mouvement plus fluide. — *Propriétés du plan › « Interpolation » (sans effet à 100 %).* (D-15 · PR #23 · commits 1e8d3a65, 062849a4)
- [ ] **Keyframes d'échelle et d'opacité** : Les points de trajectoire d'un overlay portent aussi l'échelle et l'opacité, animées au rendu. — *Inspecteur de l'overlay : Échelle et Opacité écrivent le point le plus proche de la tête quand une trajectoire existe.* (D-14 · PR #23 · commits 2667e66b, 568e64c7)
- [ ] **Rampe de vitesse** : Divise le plan à la tête et donne une autre vitesse à la partie droite. — *Propriétés du plan › « Rampe » › « Diviser à la tête → » (tête à 0,3 s au moins des bords).* (D-15 · PR #23 · commit 062849a4)
- [ ] **Réglages du carton** : Texte, sous-texte, couleur de la charte, police (16 polices gravables) et taille du titre, avec aperçu vivant dans le lecteur. — *Inspecteur du carton.* (D-21 · commit cd4dacfd)
- [ ] **Stabilisation** : Stabilise un plan V1 tremblé (analyse vidstab mise en cache par source, puis correction au rendu). — *Propriétés du plan › « Stabilis. » : case, « Analyser » (état à analyser / analyse x % / analysée), curseurs Lissage et Zoom, Bords (garder / noir).* (D-16 · PR #23 · commits 70baf74f, 3522f746)
- [ ] **Zoom dynamique** : Anime un zoom/recadrage du début à la fin d'un plan V1 entre deux rectangles (vert = début, rouge = fin), avec courbe douce ou linéaire. — *Inspecteur › Propriétés du plan › « Zoom dyn. » (zoom avant, zoom arrière, personnalisé) ; glisser les rectangles dans le lecteur.* (D-13 · PR #23 · commits 391696a2)
- [ ] **Piste d'ajustement J1** : Un clip d'ajustement sans source applique sa pile d'effets à tout ce qui est dessous, sur sa durée. — *Maj+J, chip « J+ » ou « + » de la piste J1 ; effets via le rack VFX (visibles après Preview).* (D-9 · PR #23 · commits 132c7fdc, 46be3378)
- [ ] **Cadrage (recadrage automatique)** : Choisit la partie de l'image gardée quand la source est plus large que le format : centrée, qui suit le mouvement analysé, ou position manuelle. — *Inspecteur › « Cadrage » : Centré / Suivre / Manuel, curseur Position, « Analyser le mouvement ».* (D-40 · PR #28 · commits d70989c6, 871d5dea)
- [ ] **Coins arrondis et ombre portée** : Arrondit les coins d'un overlay (incrustation) et lui ajoute une ombre portée, rendus au final. — *Inspecteur de l'overlay › « Coins (px) » (0–200) et case « Ombre portée ».* (D-19 · PR #27 · commits 37b8d573, cd18da24)
- [ ] **Pistes de sous-titres par langue** : Crée des pistes de sous-titres supplémentaires (une par langue) ; une seule est gravée au rendu, les autres s'exportent. — *Menu de piste › « Nouvelle piste de langue… », « Graver cette piste au rendu », « Exporter .srt / .vtt / .txt ».* (D-22 · PR #27 · commit 48e2286e)
- [ ] **Traduire vers une nouvelle piste** *(coût variable)* : La traduction des sous-titres peut créer une nouvelle piste de langue au lieu de remplacer le texte. — *Tiroir Sous-titres › « Traduire vers → dans une nouvelle piste ».* (D-22 · PR #27 · commit 48e2286e)
- [ ] **Fondus d'entrée/sortie du clip d'ajustement** : Le clip J1 peut faire apparaître et disparaître ses effets en fondu. — *Inspecteur d'ajustement › « Fondu d'entrée » / « Fondu de sortie » (bornés à la moitié du clip).* (t117 · PR #246, #247 · commits 155f4e96, 610e6f17)
- [ ] **Rampe d'amplitude du shake** : La rampe de l'effet shake fait monter ou descendre l'amplitude du tremblement au lieu d'être ignorée. — *Rack VFX › effet shake › rampe.* (t128 · PR #258 · commit 12cb0a40)
- [ ] **Éditeur de courbe de Bézier des rampes** : Dans le rack VFX, une rampe d'effet peut suivre une courbe de Bézier dessinée à la main (deux poignées, aperçu, champs). — *Rack VFX › rampe › « courbe à la main… ».* (t128 · PR #258 · commit 12cb0a40)

### Livrer : rendus et formats (`montage-livrer`, lot t174, reprend : nouveau) — 15 manques

**Montage — Livraison** — accès : Entrée « Montage » de la barre latérale ; bouton « Rendre… » de la barre de titre, vue « Livraison » de la barre basse

- [ ] **Envoyer vers le Scheduler à la demande** : Crée un brouillon Scheduler du rendu avec les canaux cochés (mémorisés), la date/heure (+2 h par défaut) et une légende pré-remplie. — *Bandeau « Rendu terminé » › « Envoyer vers le Scheduler », ou bouton « Publier » de la barre de titre.* (E-4 / E-5 · PR #23, #24 · commits 5cbb45e2, 4199cbed)
- [ ] **Rendre sans publier** : Le rendu final ne crée plus de brouillon Scheduler et ne change plus d'écran ; à la fin, un bandeau « Rendu terminé » s'affiche. — *Bouton « Rendre… » ; bandeau : Envoyer vers le Scheduler · Voir dans la Bibliothèque · Fermer (Échap).* (E-4 · PR #23 · commits b7b6fed2, 5cbb45e2)
- [ ] **Cadence de sortie** : Choix de la cadence du rendu : 24, 25, 30 ou 60 images/s. — *Popover de rendu › cadence.* (D-35 · PR #26 · commit 32a60d36)
- [ ] **File de rendus** : Met plusieurs rendus finaux en file ; ils s'exécutent l'un après l'autre et leur statut (en file, en cours, terminé, échec) s'affiche dans la vue Livraison. — *Popover de rendu › « Ajouter à la file ».* (D-36 · PR #26 · commits 9609ce86, 32a60d36)
- [ ] **Historique des rendus du projet** : La vue Livraison liste les rendus finaux et aperçus du projet, avec le dernier rendu final et un accès à la Bibliothèque. — *Barre basse › Livraison ; « Voir dans la Bibliothèque ».* (E-7 · PR #25 · commit 898b3b18)
- [ ] **Loudness normée** : Normalise le mix final en deux passes vers −14 LUFS (YouTube/TikTok), −16 (podcast) ou −23 (EBU). — *Popover de rendu › loudness : aucune / −14 / −16 / −23.* (D-24 · PR #26 · commits 2a34fec6, 32a60d36)
- [ ] **Pastille de loudness** : Pastille verte, jaune ou rouge comparant la dernière mesure à la cible choisie (grise sans mesure). — *À côté du choix de loudness ; mesurer d'abord par le bouton « mesurer » du bandeau Son.* (D-24 · PR #26 · commit 32a60d36)
- [ ] **Presets de sortie** : Dix presets : master 1080, web 4K, social 720, ProRes 422, H.265, WebM VP9, audio seul AAC / MP3 / WAV, GIF 480 ; le ratio du projet est conservé. — *Popover de rendu › liste Preset.* (D-35 · PR #26 · commits 42779ea2, 32a60d36)
- [ ] **Presets maison** : Enregistre le réglage de sortie courant comme preset personnel, listé dans le groupe « Maison ». — *Popover de rendu › « Enregistrer ce réglage… ».* (D-35 · PR #26 · commit 32a60d36)
- [ ] **Rendu partiel de la plage** : Ne rend que la plage I/O de la timeline. — *Popover de rendu › case « Rendre la plage I/O seulement » (si une plage est posée).* (D-38 · PR #26 · commits 2a34fec6, 32a60d36)
- [ ] **Export EDL** : Exporte la timeline en EDL CMX 3600 pour la reprendre dans DaVinci Resolve ou un autre logiciel. — *☰ › Projet › « Exporter EDL… » (enregistre d'abord le projet).* (D-37 · PR #28 · commit 5d5eadc6)
- [ ] **Export FCPXML** : Exporte la timeline en FCPXML 1.9 (Final Cut, Resolve). — *☰ › Projet › « Exporter FCPXML… ».* (D-37 · PR #28 · commit 5d5eadc6)
- [ ] **Coupes franches en GIF 12 i/s** : Un GIF 480 à 12 images/s garde toutes ses images aux coupes franches (avant, des plans entiers disparaissaient). (PR #34 · commit 2bb3c667)
- [ ] **Rendu synchrone avec le lecteur** : Le rendu n'a plus une image d'avance sur la timeline et sa durée est exactement celle de la timeline, coupes franches comprises. (PR #33 · commit 3e01fbe9)
- [ ] **Vraies poignées de plan** : Un fondu entre deux plans est centré sur la jonction avec les images réelles de la source : il ne décale plus l'image par rapport au son, et la première image après un trou ne fond plus dans le noir. (P1 #7 · PR #44 · commit c172f054)

## Publier

### Planifier et publier sa semaine (`planificateur`, lot t175, reprend : c10) — 19 manques

À corriger dans l'ancien texte :

- [ ] Badge « ENRICHI »
- [ ] « Generate plan », « Import doc », « New post », « Add to calendar », « Produce », « Send », « Assisted/Auto » (anglais)
- [ ] Auto seulement « (Telegram, X) » : Scheduler YouTube (#25), Instagram (#26), TikTok OAuth (#27), réglages OAuth (#28), métriques (#29), créneaux + validation (#30), écran (#31), lot 2 (#32), débordement (PR #288) non décrits
- [ ] Barre d'emojis : fonction réelle de contenu, à revérifier vs l'UI actuelle

**Scheduler (planificateur de publications)** — accès : Barre latérale → Scheduler ; boutons de l'en-tête Comptes, Valider la semaine, Créneaux, Analytics, Campagne

- [ ] **Publication Instagram Reels** : Publication directe des Reels sur Instagram, envoyés depuis le PC, avec contrôle du compteur Instagram (100 posts par 24 h glissantes) avant chaque envoi. (PR #65 · commit cc307bf4 · tâche #26)
- [ ] **Publication YouTube Shorts** : Le Scheduler publie directement les Shorts sur YouTube (envoi résumable) et dit la visibilité réellement appliquée (privé forcé tant que le projet Google n'est pas vérifié). (PR #64 · commit f74d1275 · tâche #25)
- [ ] **Quotas par canal** : Les plafonds de chaque réseau (X 500/mois, Instagram 100/24 h, YouTube 100/j, TikTok 15/j) sont vérifiés avant l'envoi et comptés après ; un canal déjà publié n'est jamais republié. — *Scheduler → « Comptes » (quotas du mois)* (PR #63 · PR #71 · commits 81e85a00, 6bdd634a · tâches #24, #31)
- [ ] **Analytics — 28 jours** : Tableau de bord des vues, j'aime et engagement par canal, par format et par semaine, top 5 et quotas ; les métriques sont relues chaque jour automatiquement. — *Scheduler → « Analytics » → « Rafraîchir maintenant » (rationné : 10 posts, budget X du mois)* (PR #68 · PR #71 · commits 2bc877f9, 6bdd634a · tâches #29, #31)
- [ ] **Aperçus Reels / Shorts / TikTok à zones sûres** : L'aperçu d'un post vertical (540×960) assombrit les bandes haute et basse et le rail de droite que l'interface du réseau recouvre, avec @compte et légende placés dans la bande basse. — *Aperçu du post dans l'inspecteur* (PR #70 · commit 0d11b800 · tâche #30)
- [ ] **Brief de campagne** *(coût variable)* : Un brief persistant (un seul actif) que le planificateur suit ; ses termes interdits sont retirés des légendes, accroches et hashtags générés. — *Scheduler → « Campagne… » → « Brief de campagne »* (PR #73 · PR #75 · commits 9329f639, 9543c2b3 · tâche #32)
- [ ] **Créneaux par canal** : Des heures locales de publication par canal (et votre fuseau) qu'un plan généré applique automatiquement. — *Scheduler → « Créneaux » → heures HH:MM séparées par des virgules → « Enregistrer »* (PR #70 · PR #71 · commits d22fb7a2, 6bdd634a · tâches #30, #31)
- [ ] **Fils X (Suite)** : Écrire la suite d'un post X : elle part deux minutes après et répond au message précédent (reportée tant que celui-ci n'est pas parti). — *Inspecteur d'un post X → « Suite (fil X) »* (PR #74 · PR #75 · commits 28095032, 9543c2b3 · tâche #32)
- [ ] **Horaire proposé d'après les métriques** : Propose, par canal, l'heure au meilleur engagement moyen dès 5 posts mesurés. — *Scheduler → « Créneaux » → « Proposer d'après mes métriques »* (PR #70 · PR #71 · commits d22fb7a2, 6bdd634a · tâches #30, #31)
- [ ] **Liste rechargée après une action** : Valider, poser une série, proposer un recyclage ou ajouter une suite recharge la liste du Scheduler, même si l'on y est déjà. (PR #75 · commit 9543c2b3 · tâche #32)
- [ ] **Lot validé exportable vers le téléphone** : Les posts validés de la semaine forment un lot (légendes, hashtags, média vérifié) que le téléphone appairé peut emporter, l'état publié revenant au PC. (PR #72 · commit 411424d4 · tâche #32)
- [ ] **Panneau Comptes** : Montre les quotas du mois et permet de connecter YouTube et TikTok par leur page de consentement, sans coller de code. — *Scheduler → « Comptes » → « Connecter YouTube » / « Connecter TikTok »* (PR #71 · commit 6bdd634a · tâche #31)
- [ ] **Publication TikTok Direct Post** : Publication directe sur TikTok ; tant que l'app n'est pas auditée par TikTok, les envois sont privés et c'est dit. (PR #66 · commit 1a877eac · tâche #27)
- [ ] **Recyclage proposé** : Les posts les mieux mesurés publiés depuis 3 semaines reviennent avec une légende variée (sans les interdits du brief), posés en brouillon pour demain ; aucune IA payante appelée depuis l'écran. — *Scheduler → « Campagne… » → « Recyclage proposé » → « Proposer demain »* (PR #74 · PR #75 · commits 36b9da71, 9543c2b3 · tâche #32)
- [ ] **Séries récurrentes** : Une règle (jours, heure locale, canaux, format, gabarit de légende avec {date} {weekday} {week}) pose des brouillons qui passent ensuite par la validation ; poser deux fois ne duplique rien. — *Scheduler → « Campagne… » → « Séries récurrentes » → « Créer la série », « Poser 4 semaines », « Retirer »* (PR #73 · PR #75 · commits f5c3ff68, 9543c2b3 · tâche #32)
- [ ] **TikTok dans les canaux** : TikTok apparaît dans la table des canaux, les icônes et l'écran Distribution, et peut être choisi dans un plan. (PR #71 · commit 6bdd634a · tâche #31)
- [ ] **Valider la semaine (validation par lot)** : Valide d'un coup les posts des 7 prochains jours (ou d'un plan) pour qu'ils partent ; un post sans média est ignoré et nommé ; modifier réellement un post le dévalide. — *Scheduler → « Valider la semaine »* (PR #70 · PR #71 · commits 627351aa, 6bdd634a · tâches #30, #31)
- [ ] **Post confié au téléphone / Reprendre sur le PC** : L'inspecteur indique qu'un post est confié au téléphone (le PC ne le publiera pas) et permet de le reprendre. — *Inspecteur → « Confié au téléphone · Reprendre sur le PC »* (commit 7978a3c3 · tâche #57)
- [ ] **L'écran ne déborde plus** : En-tête et panneau de droite restent visibles dans la fenêtre (1280 à 1600 px), en vues Semaine et Mois ; la barre d'outils passe à la ligne. (PR #288 · commit 2abf446c)

### Connecter ses comptes (`comptes`, lot t175, reprend : c12) — 0 manques

À corriger dans l'ancien texte :

- [ ] « YouTube et Instagram restent en mode assisté » (dépassé : Scheduler YouTube #25 / Instagram #26 ; TikTok #27 absent)
- [ ] « Connected accounts », « Send test message », « Verify credentials » (anglais)
- [ ] Réglages + OAuth (#28) non décrits ; redémarrage après Save


### Suivre l'actualité et en faire des posts (`news`, lot t175, reprend : nouveau) — 13 manques

**News** — accès : Barre latérale → News

- [ ] **Filtre gratuit et dédoublonnage** : Au rafraîchissement, les articles sont filtrés (mots-clés, listes noires, fraîcheur) et les reprises d'une même dépêche fusionnées. (PR #41 · commit 06873afc · P1 #5)
- [ ] **Articles écartés et motifs** : Une puce compte les écartés, motifs au survol ; bascule Tout voir / En tête seulement. — *Puce des écartés ; Tout voir / En tête seulement* (PR #77 · commit d5486061 · tâche #33)
- [ ] **Chaîne du jour** *(coût variable)* : Panneau qui va de l'article au post programmé : Préparer (gratuit), Polir avec l'IA (payant, le brouillon est gardé sur un 402), Programmer le lot (script, légende, créneau édités, reel cartes). — *Bouton « Chaîne du jour » à côté de Send to Studio* (PR #81 · PR #82 · commits dbed3473, 9ca13e8c · tâche #35)
- [ ] **Classer avec l'IA** **payant** : Reclasse le lot par un LLM, sur demande seulement et sous la garde des plafonds. — *Bouton « Classer avec l'IA »* (PR #77 · commit d5486061 · tâche #33)
- [ ] **Déjà couvert** : Un sujet déjà traité ces 30 derniers jours est marqué en ambre (titre au survol) et pénalisé ; les sources trop utilisées reçoivent un malus. (PR #79 · commits e3159226, 2a402535, acab65ff · tâche #34)
- [ ] **Formes de reel chiffrées** *(coût variable)* : Cinq formes de reel (cartes gratuites en local, illustration IA, plans Seedance, avatar, voix off) chiffrées avant tout tir. (PR #80 · commit f0c78d93 · tâche #35)
- [ ] **Réglages du filtre** : Panneau du filtre gratuit (mots-clés, sources et mots bannis, fenêtre de fraîcheur). — *Panneau du filtre* (PR #76 · PR #77 · commits 6278a7eb, d5486061 · tâche #33)
- [ ] **Score du jour** : Les articles sont triés par défaut par un score gratuit (motif et étoile sur la carte), recalculé à chaque brief ; le brief passe d'abord. — *Tri « Score du jour »* (PR #76 · PR #77 · PR #78 · commits 2b2c185c, d5486061, f21851c3 · tâche #33)
- [ ] **Signal X** **payant** : Lit des posts X sur un sujet, sur clic seulement, borné à 3 appels par jour et au quota de lecture X. — *Chaîne du jour → Signal X* (PR #80 · PR #82 · commits 10495c48, 9ca13e8c · tâche #35)
- [ ] **Sources en légende** : La légende du post se termine par une ligne de sources (média, date, domaine). (PR #79 · commit 2a402535 · tâche #34)
- [ ] **Tendances** : Un sujet repris par trois médias le même jour est marqué tendance, affiché en vert sur la carte. (PR #80 · PR #82 · commits 10495c48, 9ca13e8c · tâche #35)
- [ ] **Voix selon le sujet** : Le mode de voix du persona est choisi d'après les mots du sujet (gratuit) ; option « Auto (selon le sujet) » par défaut avec le motif affiché. — *Choix de voix → « Auto (selon le sujet) »* (PR #79 · PR #82 · commits 2a402535, 9ca13e8c · tâches #34, #35)
- [ ] **La saisie est gardée** : Articles cochés, requête, tri, voix, longueur, lecture et script sont retrouvés en revenant sur News. (PR #259 · commit 84be3d26 · t129)

## Images et dessin

### Ranger et retrouver ses médias (`bibliotheque`, lot t176, reprend : nouveau) — 29 manques

**Bibliothèque (Library)** — accès : Barre latérale → Library

- [ ] **Libellés de provenance** : Les puces de source affichent des libellés lisibles (Générateur, Matières, Imports, mobile…) au lieu du code brut. (PR #104 · commit 8bcb1037)
- [ ] **Barre Projet** : Regarder un projet filtre tous les onglets ; créer, renommer, supprimer un projet (les assets restent). — *Barre « Projet » en tête de la Bibliothèque* (PR #144 + #146 · commits 0305bd6c, 09c0a12d · tâche #78)
- [ ] **Envoyer vers → Projet** : Range n'importe quel asset dans un projet ; les projets qui le contiennent sont cochés (un clic le retire), création d'un nouveau projet possible. — *Envoyer vers → « Projet de la Bibliothèque… » → « ＋ Nouveau projet… »* (PR #146 · commit 09c0a12d · tâche #78)
- [ ] **Favori en base** : L'étoile de favori se pose sur la vignette sans ouvrir la fiche et est enregistrée côté serveur (les anciens favoris du navigateur sont repris une fois). — *Étoile sur la vignette* (PR #138 + #140 · commits f1a99d6b, 9e8de952 · tâche #77)
- [ ] **Fiche complète : droits** : Licence (par défaut selon la source), auteur et lien éditables ; alerte ambre « Licence inconnue — à vérifier avant diffusion ». — *Fiche → Droits → « Enregistrer »* (PR #156 + #157 · commits 4451707d, a854ed08 · tâche #80)
- [ ] **Fiche complète : fichier, recette, usages** : Dimensions, poids, format, source, recette du générateur (prompt, style, modèle, graine) et tous les usages de l'image (rendus, posts, bible, plans, projets). — *Fiche d'une image* (PR #156 + #157 · commits 4451707d, a854ed08 · tâche #80)
- [ ] **Lignée Mère / Filles** : La fiche d'une image montre sa mère (avec la relation : recadrage, upscale…) et ses filles en vignettes cliquables ; une mère vidéo affiche son rendu. — *Fiche d'une image → « Mère » / « Filles (n) »* (PR #153 + #154 · commits debb5c35, 936887f3 · tâche #79)
- [ ] **Note 0 à 5** : Une note de 0 à 5, distincte du favori, affichée en points sur la vignette. — *Fiche d'une image → note* (PR #138 + #140 · commits f1a99d6b, 9e8de952 · tâche #77)
- [ ] **Projet actif** : Tout ce qui est produit (images, rendus, 3D, sprites) se range automatiquement dans le projet actif, rappelé et arrêtable. — *Barre Projet → « Ranger ici automatiquement »* (PR #144 + #146 · commits 0305bd6c, 09c0a12d · tâche #78)
- [ ] **Projet épinglé sur le téléphone** : Un seul projet de la Bibliothèque est épinglé pour le téléphone. — *Barre Projet → épingler sur le téléphone* (PR #144 + #146 · commits 0305bd6c, 09c0a12d · tâche #78)
- [ ] **Rejouer la recette** **payant** : Régénère une image avec sa recette d'origine (graine gardée), prix annoncé avant le tir ; la nouvelle image entre en tête de liste. — *Fiche → « Rejouer la recette » → confirmation* (PR #157 · commit a854ed08 · tâche #80)
- [ ] **Tags** : Tags éditables sur chaque image, rangée de puces comptées (« ★ 3+ », Effacer) qui filtre Images et Favoris ; la recherche couvre les tags. — *Fiche d'une image → tags ; rangée de puces* (PR #138 + #140 · commits f1a99d6b, 9e8de952 · tâche #77)
- [ ] **Taille et date dans la grille** : La grille affiche enfin la taille réelle et l'âge du fichier (« 34.0 KB · 2d ago ») au lieu d'un champ vide. (PR #157 · commit a854ed08 · tâche #80)
- [ ] **Versions de l'Établi en arbre** : Dans l'onglet Établi de la Bibliothèque, les versions d'un modèle sont rangées dans l'ordre de leur lignée avec un « ↳ » par génération. — *Onglet Établi* (PR #155 · commit b4ea2aff · tâche #79)
- [ ] **CLIP local : recherche par le sens** : Installe un modèle CLIP local (≈ 186 Mo) qui indexe les images et permet de chercher par description, gratuitement. — *Recherche → bloc CLIP → installer, « Indexer », puis moteur « clip »* (PR #164 · commit a1741c9a · tâche #82)
- [ ] **Commentaires de revue** : Commentaires datés sous la fiche avec statut (à revoir, validé, rejeté) et instant mm:ss pour un son ; ils suivent l'asset renommé ou restauré. — *Fiche → « Commenter » (Entrée), pastilles de statut cliquables* (PR #161 · commit 3df03476 · tâche #82)
- [ ] **Corbeille** : Supprimer une image, un son ou un rendu le met désormais à la corbeille (nombre, poids, éléments de plus de 30 jours signalés). — *Barre « Corbeille »* (PR #158 + #160 · commits 7b07cc6f, 2b258d8d · tâche #81)
- [ ] **Couleur dominante et puce Teinte** : Chaque image reçoit sa couleur dominante et une teinte (12 + neutre) ; des puces par teinte filtrent la grille, la fiche montre la pastille. — *Rangée de puces → teinte* (PR #159 + #160 · commits c9bf84f0, 2b258d8d · tâche #81)
- [ ] **Images semblables** : Trouve les images visuellement proches de celle ouverte (CLIP local). — *Fiche → « ≈ Images semblables »* (PR #164 · commit a1741c9a · tâche #82)
- [ ] **Légendes par modèle vision** **payant** : Fait décrire les images par Gemini Flash-Lite pour mieux les retrouver ; devis affiché (les images sont envoyées à Google), plafond vérifié, suivi faits / total. — *Recherche → bloc Légendes → confirmation* (PR #163 · commit 7ede0d91 · tâche #82)
- [ ] **Nettoyage des doublons** : Montre le poids par sorte et les groupes de doublons exacts ; les copies protégées (favori, usage, projet) sont grisées, les copies en trop partent à la corbeille. — *Barre « Nettoyage » → « Cocher les copies en trop » → confirmation* (PR #159 + #160 · commits c9bf84f0, 2b258d8d · tâche #81)
- [ ] **Recherche texte locale** : Cherche dans les légendes, tags, prompts, recettes, commentaires et noms, sans accents ni casse. — *Barre → « Recherche » → moteur « texte »* (PR #163 · commit 7ede0d91 · tâche #82)
- [ ] **Restaurer depuis la corbeille** : Remet l'asset à sa place avec ses projets (nom voisin si le sien est repris, et dit). — *Corbeille → « Restaurer »* (PR #158 + #160 · commits 7b07cc6f, 2b258d8d · tâche #81)
- [ ] **Tris réparés** : « Most recent » trie réellement et « Size » compare des tailles, non plus du texte. (PR #162 · commit c2e012f9 · tâche #82)
- [ ] **Vider la corbeille** : Supprime définitivement les anciens, tout, ou un seul élément, après confirmation. — *Corbeille → « Vider les anciens » / « tout » / un élément* (PR #158 + #160 · commits 7b07cc6f, 2b258d8d · tâche #81)
- [ ] **Vue Liste triable** : Bascule Grille / Liste ; la liste a dix colonnes triables (nom, source, taille, date, dimensions, tags, note, favori, licence, teinte) et une ligne ouvre la fiche. — *Barre de la Bibliothèque → Grille / Liste* (PR #162 · commit c2e012f9 · tâche #82)
- [ ] **État d'un projet** : Classe les assets d'un projet en monté, publié, imprimé ou inutilisé. — *Barre Projet → bouton « ▦ État »* (PR #162 · commit c2e012f9 · tâche #82)
- [ ] **Puce Audio : tiroir Sons** : L'onglet Audio monte le tiroir Sons de référence (tags, filtres, tri, actions) au-dessus de l'import. — *Onglet / puce Audio* (PR #214 · commit c44b914f · T101)
- [ ] **Envoyer vers Photolab / Vectorlab / Tile Lab** : Envoie une image vers le Photolab, vers un nouveau document du Vectorlab, ou comme source du Tile Lab. — *Envoyer vers → Photolab / Vectorlab / Tile Lab* (PR #266 · commit eeee9ed1 · t139)

### Retoucher une photo (Photolab) (`photolab`, lot t176, reprend : nouveau) — 137 manques

**Photolab — Fichier et documents** — accès : Barre des applications → icône Photolab (iris, « Retouche d'image & calques », comme le Vectorlab) ; URL /photolab/ ; menu Fichier

- [ ] **Moteur photocraft intégré, résultats identiques** : Chaque geste validé est calculé par le moteur photocraft-cli 0.3.0 fourni avec Deepotus : mêmes pixels que l'application d'origine, sans connexion ni coût. (PR #263 · commit 08a9ceb4 · t136)
- [ ] **Barre d'état** : En bas : zoom, mode et profondeur (ex. RVB · 8 bits), dimensions en px, nombre de calques et messages. (PR #264 · commit db72da5b · t137)
- [ ] **Cible « Photolab » de Envoyer vers** : Depuis la Bibliothèque ou un autre écran, « Envoyer vers » ouvre l'image dans le Photolab pour la retoucher. — *Menu « Envoyer vers » → Photolab — retoucher l'image* (PR #266 · commit eeee9ed1 · t139)
- [ ] **Cible « Tile Lab » de Envoyer vers** : Une image envoyée au Tile Lab devient la source de la tuile. — *Menu « Envoyer vers » → Tile Lab — source de la tuile* (PR #266 · commit eeee9ed1 · t139)
- [ ] **Cible « Vectorlab » de Envoyer vers** : Une image envoyée au Vectorlab y crée un document neuf à sa taille avec l'image. — *Menu « Envoyer vers » → Vectorlab — nouveau document avec l'image* (PR #266 · commit eeee9ed1 · t139)
- [ ] **Déposer une image** : Glisser un fichier image sur la zone de travail le range dans la Bibliothèque et l'ouvre. — *Glisser-déposer sur la toile* (PR #264 · commit db72da5b · t137)
- [ ] **Enregistrer dans la Bibliothèque** : Enregistre l'image en PNG dans la Bibliothèque (source « Photolab ») avec un fichier de travail .pcraft qui garde les calques ; toujours un nouveau fichier, jamais d'écrasement. — *Fichier › Enregistrer (Ctrl+S)* (PR #264 · commit db72da5b · t137)
- [ ] **Envoyer vers…** : Envoie l'image courante vers un autre écran depuis le Photolab (via la Bibliothèque). — *Fichier › Envoyer vers…* (PR #266 · commit eeee9ed1 · t139)
- [ ] **Exporter sous** : Exporte le document en PNG, JPG, WEBP (avec qualité), TIFF, PSD ou PCRAFT, puis le télécharge. — *Fichier › Enregistrer sous… (Ctrl+Maj+S) ou Fichier › Exporter › Exporter sous… (Ctrl+Alt+Maj+W)* (PR #264 · commit db72da5b · t137)
- [ ] **Fermer** : Ferme le document actif, avec confirmation s'il a changé depuis le dernier enregistrement. — *Fichier › Fermer (Ctrl+W) ; « Fermer sans enregistrer » dans la confirmation* (PR #264 · commit db72da5b · t137)
- [ ] **Fiches d'aide animées** : Fiches « pour un enfant de cinq ans » avec animation : Sélection rectangulaire, Baguette magique, Recadrage, Noir et blanc, Pinceau, Tampon de duplication, Espace de travail. — *Survol long de l'outil, du réglage ou du sélecteur d'espace, ou bouton « ? »* (PR #267 · commit b810b242 · t140)
- [ ] **Lignée « retouche » dans la Bibliothèque** : Une image retouchée est reliée à son image d'origine dans la fiche de la Bibliothèque. (PR #266 · commit eeee9ed1 · t139)
- [ ] **Messages du moteur** : Le Photolab dit clairement quand le moteur est absent, occupé, trop lent, ou a été relancé (les documents ouverts sont alors perdus et l'écran revient à l'accueil). (PR #264 · commit db72da5b · t137)
- [ ] **Moteur vérifié à l'installation** : L'installeur fournit le moteur et vérifie chaque fichier (taille et empreinte) : un moteur altéré ou incomplet n'est pas livré. (PR #267 · commit b810b242 · t140)
- [ ] **Nouveau document** : Dialogue de création avec catégories (Photo, Film et vidéo, Mobile, Impression, Web) et préréglages (Taille par défaut, HDTV 1080p, 4K UHD, Instagram carré, Story 9:16, A4 300 ppi, Web 1366 × 768). — *Fichier › Nouveau… (Ctrl+N) : nom, largeur, hauteur (1 à 30 000 px), orientation, résolution, contenu de l'arrière-plan (blanc, noir, transparent, couleur), puis Créer* (PR #264 · commit db72da5b · t137)
- [ ] **Ouvrir dans l'app native** : Repli pour ce que l'écran ne fait pas encore : ouvre le document dans l'application photocraft installée (avec ses calques). — *Fichier › Ouvrir dans l'app native…* (PR #267 · commit b810b242 · t140)
- [ ] **Ouvrir depuis la Bibliothèque** : Ouvre une image de la Bibliothèque Deepotus dans le Photolab. — *Fichier › Ouvrir… (Ctrl+O) → sélecteur de la Bibliothèque* (PR #264 · commit db72da5b · t137)
- [ ] **Photolab dans la barre des applications** : Nouveau lab de retouche photo à calques (reproduction de photocraft) ouvert dans l'application, au design Deepotus. — *Icône Photolab dans la barre des applications, juste après le Vectorlab ; ou URL /photolab/* (PR #264 · commit db72da5b · t137)
- [ ] **Reprendre depuis l'app native** : Rapporte dans le Photolab le document retouché dans l'application native, calques compris. — *Fichier › Reprendre depuis l'app native* (PR #267 · commit b810b242 · t140)
- [ ] **Rouvrir avec les calques** : Une image enregistrée par le Photolab se rouvre depuis la Bibliothèque avec ses calques (fichier de travail lié) ; sinon elle s'ouvre aplatie. — *Fichier › Ouvrir… sur une image de source Photolab* (PR #266 · commit eeee9ed1 · t139)
- [ ] **À propos et licences** : Dialogue À propos : version et licence du moteur, polices, liste de mots, icônes, et textes complets des licences tierces. — *Aide › À propos du Photolab* (PR #267 · commit b810b242 · t140)
- [ ] **Écran bilingue** : Tout l'écran (menus, outils, panneaux, dialogues, historique) suit la langue de Deepotus, français ou anglais. — *Réglages de Deepotus → langue* (PR #264 · commit db72da5b · t137)
- [ ] **Écran d'accueil** : Sans document, l'accueil propose de créer un document, d'ouvrir une image de la Bibliothèque ou d'en déposer une. — *Boutons « Nouveau… » (Ctrl+N) et « Ouvrir depuis la Bibliothèque… » (Ctrl+O)* (PR #264 · commit db72da5b · t137)
- [ ] **Enregistrer une copie** : Enregistre une copie du document (le document reste tel quel) vers le téléchargement ou la Bibliothèque (PNG ou JPG), avec lignée vers l'image d'origine. — *Fichier › Enregistrer une copie… (Ctrl+Alt+S) : format, qualité, échelle, nom, destination* (PR #277 · commit 8ad8a6f4 · t158)
- [ ] **Exportation rapide au format PNG** : Exporte le document entier en un clic, au format et vers la destination choisis dans les Préférences. — *Fichier › Exporter › Exportation rapide au format PNG* (PR #277 · commit 8ad8a6f4 · t158)
- [ ] **Fermer les autres** : Ferme tous les documents sauf l'actif, après confirmation des modifiés. — *Fichier › Fermer les autres (Ctrl+Alt+P)* (PR #277 · commit 8ad8a6f4 · t158)
- [ ] **Informations sur le fichier** : Métadonnées du document : titre, auteur, fonction, description, mots-clés, statut et mention de copyright, adresse des droits (http/https). — *Fichier › Informations sur le fichier… (Ctrl+Alt+Maj+I)* (PR #277 · commit 8ad8a6f4 · t158)
- [ ] **Onglets de documents** : Une barre d'onglets montre tous les documents ouverts ; un point signale un document modifié. — *Clic sur un onglet = activer le document ; × = le fermer vraiment* (PR #277 · commit 8ad8a6f4 · t158)
- [ ] **Placer incorporé depuis la Bibliothèque** : Place une image de la Bibliothèque au centre du document, en objet dynamique réduit s'il dépasse, puis ouvre la transformation manuelle. — *Fichier › Placer incorporé…* (PR #277 · commit 8ad8a6f4 · t158)
- [ ] **Revenir à la version enregistrée** : Relit le document depuis son dernier enregistrement ; la confirmation prévient que l'historique sera perdu. — *Fichier › Revenir à la version enregistrée (F12)* (PR #277 · commit 8ad8a6f4 · t158)
- [ ] **Tout fermer** : Ferme tous les documents ; la confirmation liste ceux qui ont des modifications non enregistrées. — *Fichier › Tout fermer (Ctrl+Alt+W)* (PR #277 · commit 8ad8a6f4 · t158)
- [ ] **Icônes Deepotus Glyph** : Outils, menus volants, rail, calques, panneaux et dialogues du Photolab utilisent les icônes de la suite Deepotus Glyph. (PR #283 · commit cbf8f761)
**Photolab — Outils** — accès : Barre des applications → icône Photolab (iris, « Retouche d'image & calques », comme le Vectorlab) ; URL /photolab/ ; barre d'outils à gauche de la toile

- [ ] **Aperçu de la pointe et du trait** : Cercle de la taille de la pointe au survol et aperçu du trait pendant le geste. (PR #268 · commit 7dc1700b · t155)
- [ ] **Baguette magique (W)** : Sélectionne d'un clic une tache de couleur. — *Clic ; barre : tolérance (0-255), contiguë, tous les calques* (PR #264 · commit db72da5b · t137)
- [ ] **Barre d'options de l'outil** : Bandeau en haut qui montre les réglages de l'outil actif. (PR #264 · commit db72da5b · t137)
- [ ] **Barre d'outils à emplacements groupés** : Barre de 20 emplacements ; un emplacement à plusieurs outils ouvre un menu volant (icône, nom, lettre). — *Clic droit ou appui long (350 ms) sur un emplacement marqué d'un coin* (PR #264 · commit db72da5b · t137)
- [ ] **Correcteur (J)** : Répare une zone à partir d'une source choisie, en fondant texture et lumière. — *Alt+clic = source, puis peindre* (PR #268 · commit 7dc1700b · t155)
- [ ] **Correcteur de tache (J)** : Efface une petite imperfection d'un coup de pinceau. — *Glisser sur la tache ; barre : Type (Contenu pris en compte, Créer une texture, Similarité de proximité)* (PR #268 · commit 7dc1700b · t155)
- [ ] **Crayon (B)** : Trait net, sans anticrénelage. — *Glisser ; barre : taille, mode, opacité, effacement automatique* (PR #268 · commit 7dc1700b · t155)
- [ ] **Densité + (O)** : Assombrit les zones peintes. — *Glisser ; mêmes réglages que Densité −* (PR #268 · commit 7dc1700b · t155)
- [ ] **Densité − (O)** : Éclaircit les zones peintes. — *Glisser ; barre : Gamme (tons foncés, moyens, clairs), exposition, Protéger les tons* (PR #268 · commit 7dc1700b · t155)
- [ ] **Doigt** : Étale la peinture comme un doigt. — *Glisser ; barre : intensité, Peinture au doigt* (PR #268 · commit 7dc1700b · t155)
- [ ] **Dégradé (G)** : Trace un dégradé. — *Glisser ; Maj = angle calé par 45° ; barre : 5 styles (Linéaire, Radial, Angle, Réfléchi, Losange), Inverser le dégradé, Tramage* (PR #268 · commit 7dc1700b · t155)
- [ ] **Déplacement (V)** : Déplace le calque ou le contenu de la sélection, avec aperçu pendant le geste. — *Glisser ; Maj = un axe ; flèches = 1 px, Maj+flèches = 10 px ; « Sélection auto. » (calque ou groupe) ou Ctrl+clic = choisir le calque sous le pointeur* (PR #264 · commit db72da5b · t137)
- [ ] **Gomme (E)** : Efface les pixels. — *Glisser ; barre : mode Pinceau ou Crayon, opacité, flux, lissage, « Effacer d'après l'historique »* (PR #268 · commit 7dc1700b · t155)
- [ ] **Gomme d'arrière-plan (E)** : Efface le fond autour d'un sujet en gardant les contours. — *Glisser ; barre : échantillonnage (Continu, Une fois, Nuance d'arrière-plan), Limites (Non contiguës, Contiguës, Recherche des contours), tolérance, Protéger la couleur de premier plan* (PR #268 · commit 7dc1700b · t155)
- [ ] **Gomme magique (E)** : Efface d'un clic une tache de couleur. — *Clic ; barre : tolérance, lissage, pixels contigus, tous les calques, opacité* (PR #268 · commit 7dc1700b · t155)
- [ ] **Goutte (flou)** : Adoucit l'image sous le pinceau. — *Glisser ; barre : intensité, tous les calques* (PR #268 · commit 7dc1700b · t155)
- [ ] **Lasso (L)** : Sélection à main levée. — *Glisser autour de la zone* (PR #264 · commit db72da5b · t137)
- [ ] **Lasso polygonal (L)** : Sélection par sommets. — *Clic = sommet ; double-clic, clic sur le premier ou Entrée = fermer ; Échap = annuler* (PR #264 · commit db72da5b · t137)
- [ ] **Lettres des outils** : Chaque outil a sa lettre ; la même lettre fait passer d'un outil du groupe au suivant. — *V, M, L, W, C, I, J, B, S, Y, E, G, O, P, T, A, U, H, Z (Maj+lettre si la préférence l'exige)* (PR #264 · commit db72da5b · t137)
- [ ] **Main (H)** : Fait défiler la vue. — *Glisser ; Espace tenu = main temporaire ; bouton du milieu de la souris* (PR #264 · commit db72da5b · t137)
- [ ] **Netteté** : Accentue la netteté sous le pinceau. — *Glisser ; barre : intensité, Protéger les détails* (PR #268 · commit 7dc1700b · t155)
- [ ] **Opacité et flux au chiffre** : Règle l'opacité (ou le flux avec Maj) en tapant un chiffre. — *1 = 10 %… 0 = 100 % ; deux chiffres rapides = valeur exacte (4 puis 5 = 45 %) ; Maj+chiffre = flux* (PR #268 · commit 7dc1700b · t155)
- [ ] **Pastilles de couleur** : Couleurs de premier plan et d'arrière-plan sous la barre d'outils. — *Clic = sélecteur de couleur ; X = échanger ; D = couleurs par défaut* (PR #264 · commit db72da5b · t137)
- [ ] **Pinceau (B)** : Peint un trait de la couleur de premier plan. — *Glisser ; Maj = trait droit (0/45/90°), Maj+clic = ligne depuis le trait précédent, Alt = pipette ; barre : taille, dureté, mode, opacité, flux, lissage du tracé* (PR #268 · commit 7dc1700b · t155)
- [ ] **Pinceau d'historique (Y)** : Repeint l'état d'origine du document là où l'on passe. — *Glisser* (PR #268 · commit 7dc1700b · t155)
- [ ] **Pinceau mélangeur (B)** : Mélange la couleur avec celle de l'image. — *Glisser ; barre : humidité, charge, mélange, flux, échantillonner tous les calques* (PR #268 · commit 7dc1700b · t155)
- [ ] **Pipette (I)** : Prélève une couleur de l'image. — *Clic = premier plan ; Alt+clic = arrière-plan* (PR #264 · commit db72da5b · t137)
- [ ] **Pot de peinture (G)** : Remplit d'un clic une zone de couleur. — *Clic ; barre : opacité, tolérance, lissage, contigus ; Alt = pipette* (PR #268 · commit 7dc1700b · t155)
- [ ] **Raccourcis de la pointe** : Taille et dureté de la pointe au clavier pour tous les outils de peinture. — *[ et ] = taille ; Maj+[ et Maj+] = dureté (±25 %)* (PR #268 · commit 7dc1700b · t155)
- [ ] **Recadrage (C)** : Recadre l'image sur un cadre tracé ou sur la sélection. — *Tracer le cadre (poignées), Entrée ou double-clic = recadrer, Échap = annuler ; option « Supprimer les pixels recadrés »* (PR #264 · commit db72da5b · t137)
- [ ] **Sélection elliptique (M)** : Trace une sélection elliptique. — *Glisser, mêmes modes que la sélection rectangulaire* (PR #264 · commit db72da5b · t137)
- [ ] **Sélection rapide (W)** : Sélection peinte au pinceau. — *Glisser ; barre : taille* (PR #264 · commit db72da5b · t137)
- [ ] **Sélection rectangulaire (M)** : Trace une sélection rectangulaire. — *Glisser ; barre : Nouvelle / Ajouter / Soustraire / Intersection, contour progressif, lissage ; Maj = ajouter, Alt = soustraire* (PR #264 · commit db72da5b · t137)
- [ ] **Tampon de duplication (S)** : Recopie une partie de l'image ailleurs. — *Alt+clic = définir la source, puis peindre ; barre : mode, opacité, flux, Aligné, Échantillon (calque actif / actif et inférieurs / tous)* (PR #268 · commit 7dc1700b · t155)
- [ ] **Zoom (Z)** : Agrandit ou réduit la vue. — *Clic sur la toile* (PR #264 · commit db72da5b · t137)
- [ ] **Éponge (O)** : Sature ou désature les couleurs sous le pinceau. — *Glisser ; barre : mode Saturer / Désaturer, flux, vibrance* (PR #268 · commit 7dc1700b · t155)
- [ ] **Barre d'options du texte** : Réglages du texte en cours de saisie. — *Orientation, police (polices du PC, aperçu), style, taille, lissage, alignement, couleur, valider / annuler* (PR #274 · commit e44037ea · t156)
- [ ] **Ellipse (U)** : Dessine un calque de forme ellipse. — *Glisser ; Maj = cercle, Alt = depuis le centre* (PR #274 · commit e44037ea · t156)
- [ ] **Forme personnalisée (U)** : Dessine une forme du panneau Formes (cœur, étoile, flèches, bulles, nature, animaux…). — *Glisser ; forme choisie dans la barre ou le panneau Formes* (PR #274 · commit e44037ea · t156)
- [ ] **Ligne (U)** : Dessine un trait vectoriel. — *Glisser ; Maj = angle par 45° ; barre : épaisseur du trait* (PR #274 · commit e44037ea · t156)
- [ ] **Options de langue du texte** : Montre la direction (gauche-droite / droite-gauche) ou l'orientation verticale selon les langues. — *Texte › Options de langue › Fonctionnalités par défaut / d'Asie orientale / du Moyen-Orient / Composeur* (PR #274 · commit e44037ea · t156)
- [ ] **Plume (P)** : Dessine un tracé de travail ou un calque de forme point par point. — *Clic = sommet ; glisser = sommet lisse ; clic sur le premier = fermer ; Entrée = terminer ; Échap = abandonner ; Ctrl+Entrée = sélection ; barre : mode Tracé ou Forme* (PR #274 · commit e44037ea · t156)
- [ ] **Polygone (U)** : Dessine un polygone au nombre de côtés choisi. — *Glisser ; barre : côtés* (PR #274 · commit e44037ea · t156)
- [ ] **Rectangle (U)** : Dessine un calque de forme rectangle (coins arrondis possibles). — *Glisser ; Maj = carré, Alt = depuis le centre ; barre : remplissage, contour (épaisseur, couleur, position), rayon* (PR #274 · commit e44037ea · t156)
- [ ] **Sélection d'objet (W)** : Trouve l'objet contenu dans un rectangle tracé et le sélectionne. — *Glisser un rectangle ; Maj ajoute, Alt retire ; case Échantillonner tous les calques ; boutons « Sélectionner un sujet » et « Sélectionner et masquer… » dans la barre* (PR #275 · commit 86899170 · t157)
- [ ] **Sélection de tracé (A)** : Déplace la forme active ou le tracé de travail. — *Glisser* (PR #274 · commit e44037ea · t156)
- [ ] **Taille de l'aperçu des polices** : Taille des noms dans la liste des polices. — *Texte › Taille de l'aperçu des polices › Petite, Moyenne, Grande, Très grande, Énorme* (PR #274 · commit e44037ea · t156)
- [ ] **Texte (T)** : Crée ou modifie un calque de texte, rendu par le moteur. — *Clic = texte de point ; glisser = texte de paragraphe ; clic sur un calque de texte = l'éditer ; Ctrl+Entrée, Échap ou clic ailleurs = valider* (PR #274 · commit e44037ea · t156)
- [ ] **Triangle (U)** : Dessine un calque de forme triangle. — *Glisser* (PR #274 · commit e44037ea · t156)
**Photolab — Sélection, édition et transformation** — accès : Barre des applications → icône Photolab (iris, « Retouche d'image & calques », comme le Vectorlab) ; URL /photolab/ ; menus Sélection et Édition

- [ ] **Agrandir et Similaire** : Étend la sélection aux pixels voisins ou semblables. — *Sélection › Agrandir ; Sélection › Similaire* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Alignement et fusion automatiques des calques** : Aligne ou fond automatiquement plusieurs calques. — *Édition › Alignement automatique des calques…, Fusion automatique des calques…* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Annuler, rétablir** : Annule ou rétablit la dernière étape. — *Ctrl+Z / Ctrl+Maj+Z ; Édition › Basculer sur le dernier état (Ctrl+Alt+Z)* (PR #264 · commit db72da5b · t137)
- [ ] **Barre d'options de la transformation** : Point de référence (grille 3 × 3), X/Y (relatif possible), L % et H % liés, angle, inclinaisons H et V, interpolation (Bicubique, Bilinéaire, Au plus proche), valider / annuler. (PR #273 · commit b8197c91 · t154)
- [ ] **Charger et enregistrer la sélection** : Garde une sélection dans une couche alpha et la recharge. — *Sélection › Enregistrer la sélection… / Charger la sélection…* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Contour de sélection animé** : La sélection est montrée en pointillés animés sur la toile. (PR #264 · commit db72da5b · t137)
- [ ] **Couper, copier, coller** : Presse-papiers du moteur, y compris copie des calques fusionnés et collages spéciaux. — *Édition › Couper, Copier, Copier les calques fusionnés (Ctrl+Maj+C), Coller ; Collage spécial › Coller sur place (Ctrl+Maj+V), dans la sélection (Ctrl+Alt+Maj+V), hors de la sélection* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Définir un pinceau, un motif, une forme** : Crée un préréglage à partir de la sélection ou du tracé. — *Édition › Définir un préréglage de pinceau…, Définir un motif…, Définir une forme personnalisée…* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Estomper** : Atténue le dernier filtre ou réglage appliqué. — *Édition › Estomper… (Ctrl+Maj+F)* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Gestes de la transformation** : Coin = homothétie proportionnelle (Maj libère, Alt depuis le point de référence) ; bord = un axe ; dedans = déplacer ; dehors = rotation (Maj par 15°) ; Ctrl+coin = déformation ; Ctrl+bord = inclinaison ; Ctrl+Alt+Maj+coin = perspective. — *Flèches = 1 px, Maj = 10 px ; glisser ou Alt+clic = déplacer le point de référence* (PR #273 · commit b8197c91 · t154)
- [ ] **Modifier la sélection** : Bordure, lissage, extension, contraction et contour progressif de la sélection, par dialogue. — *Sélection › Modifier › Bordure…, Lisser…, Étendre…, Contracter…, Adoucir… (Maj+F6)* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Remplir et Contourner** : Remplit la sélection ou trace son contour. — *Édition › Remplir… (Maj+F5) ; Édition › Contourner…* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Remplissage et échelle d'après le contenu** : Remplit une zone en tenant compte de l'image ; met à l'échelle en préservant le contenu. — *Édition › Remplissage d'après le contenu… ; Mise à l'échelle d'après le contenu (Ctrl+Alt+Maj+C)* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Rotations et symétries rapides** : Rotation de 180°, 90° horaire ou antihoraire, symétrie horizontale ou verticale du calque ; répéter la dernière transformation. — *Édition › Transformation › Répéter (Ctrl+Maj+T), Rotation de 180°, 90°…, Symétrie horizontale/verticale* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Sélections automatiques du moteur** : Sélectionne le sujet, le ciel, une plage de couleurs ou une zone de mise au point. — *Sélection › Sujet, Ciel, Plage de couleurs…, Zone de mise au point…* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Tout sélectionner, désélectionner, inverser** : Commandes de base de la sélection. — *Sélection › Tout sélectionner (Ctrl+A), Désélectionner (Ctrl+D), Resélectionner (Ctrl+Maj+D), Inverser la sélection (Ctrl+Maj+I)* (PR #264 · commit db72da5b · t137)
- [ ] **Transformation libre (Ctrl+T)** : Transforme le calque (ou la partie sélectionnée) avec un cadre à 8 poignées et un point de référence ; l'aperçu est calculé par le moteur. — *Édition › Transformation libre (Ctrl+T) ; Entrée ou double-clic = valider, Échap = annuler, Ctrl+Z = pas précédent dans la session* (PR #273 · commit b8197c91 · t154)
- [ ] **Transformation › Mise à l'échelle, Rotation, Inclinaison, Déformation, Perspective** : Ouvre la session dans un mode contraint : chaque poignée fait le geste du mode. — *Édition › Transformation › …* (PR #273 · commit b8197c91 · t154)
- [ ] **Rechercher (Ctrl+K)** : Palette de recherche dans toutes les commandes de menu actives et les outils. — *Édition › Rechercher… (Ctrl+K) ; ↑ ↓ Entrée Échap* (PR #274 · commit e44037ea · t156)
- [ ] **Réglages de Sélectionner et masquer** : Rayon, rayon dynamique, arrondi, contour progressif, contraste, décalage du contour, inverser, décontaminer les couleurs (quantité). — *Sections Détection des contours et Améliorations globales* (PR #275 · commit 86899170 · t157)
- [ ] **Sortie de Sélectionner et masquer** : Sortie vers une sélection, un masque de fusion, un nouveau calque ou un nouveau calque avec masque ; mémoriser les paramètres. — *Paramètres de sortie › Sortie vers ; case Mémoriser les paramètres ; Réinitialiser* (PR #275 · commit 86899170 · t157)
- [ ] **Sélectionner et masquer** : Affine les bords d'une sélection (cheveux, contours) dans un dialogue non modal avec aperçu calculé par le moteur. — *Sélection › Sélectionner et masquer… (Alt+Ctrl+R) ou bouton dans la barre des outils de sélection* (PR #275 · commit 86899170 · t157)
- [ ] **Vues de Sélectionner et masquer** : Sept vues : Pelure d'oignon, Cadre de la sélection, Incrustation, Sur noir, Sur blanc, Noir et blanc, Sur les calques ; transparence réglable, Afficher l'original. — *Lettres des vues, F = vue suivante, X = couper l'aperçu, P = original* (PR #275 · commit 86899170 · t157)
**Photolab — Réglages, filtres et image** — accès : Barre des applications → icône Photolab (iris, « Retouche d'image & calques », comme le Vectorlab) ; URL /photolab/ ; menus Image et Filtre

- [ ] **Balance des couleurs (Ctrl+B)** : Corrige les dominantes dans les ombres, tons moyens et tons clairs. — *Image › Ajustements › Balance des couleurs…* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Correction de l'objectif** : Corrige les défauts d'objectif. — *Filtre › Correction de l'objectif… (Ctrl+Maj+R)* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Corrections automatiques** : Tonalité, contraste et couleur automatiques. — *Image › Tonalité automatique (Ctrl+Maj+L), Contraste automatique (Ctrl+Alt+Maj+L), Couleur automatique (Ctrl+Maj+B)* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Courbes (Ctrl+M)** : Éditeur de courbes sur mesure avec histogramme, par canal RVB / Rouge / Vert / Bleu. — *Image › Ajustements › Courbes… : clic = point, glisser = déplacer, double-clic ou glisser hors de la grille = retirer, flèches (Maj par 10), Suppr* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Dernier filtre** : Rejoue le dernier filtre appliqué. — *Filtre › Dernier filtre (Ctrl+Alt+F)* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Dialogues de réglage et de filtre avec aperçu** : Chaque filtre et chaque réglage s'ouvre dans un dialogue généré, avec un aperçu calculé par le moteur sur une copie (l'original et l'historique restent intacts). — *Case Aperçu, OK, Annuler, Réinitialiser* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Dupliquer, Appliquer une image, Calculs** : Duplique le document ; combine des couches entre images. — *Image › Dupliquer… ; Appliquer une image… ; Calculs…* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Filtres Bruit** : Ajout de bruit, Supprimer les mouchetures, Poussière et rayures, Médiane, Réduction du bruit. — *Filtre › Bruit › …* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Filtres Déformation** : Pincement, Coordonnées polaires, Ondulation, Cisaillement, Sphérisation, Tourbillon, Onde, Zigzag. — *Filtre › Déformation › …* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Filtres Flou** : Moyenne, Flou, Flou accentué, Flou par boîte, Flou gaussien, Flou d'objectif, Flou de mouvement, Flou radial, Flou selon une forme, Flou intelligent, Flou de surface. — *Filtre › Flou › …* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Filtres Netteté** : Netteté, Netteté des contours, Netteté accentuée, Netteté intelligente, Masque flou. — *Filtre › Netteté › …* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Filtres Pixelisation** : Trame de demi-teintes couleur, Cristallisation, Facettes, Fragmentation, Manière noire, Mosaïque, Pointillisme. — *Filtre › Pixeliser › …* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Filtres Rendu** : Cadre d'image, Arbre, Nuages, Nuages par différence, Fibres, Reflet d'objectif, Effets d'éclairage. — *Filtre › Rendu › …* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Filtres Styliser** : Diffuser, Relief, Extruder, Détecter les contours, Peinture à l'huile, Solariser, Carreaux, Tracer les contours, Vent. — *Filtre › Styliser › …* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Filtres Vidéo et Autre** : Désentrelacer, Couleurs NTSC ; TSL/TSI, Passe-haut, Maximum, Minimum, Décalage. — *Filtre › Vidéo › … ; Filtre › Autre… › …* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Galerie de flous** : Flou de champ, Flou d'iris, Inclinaison-décalage, Flou de tracé, Flou de rotation. — *Filtre › Galerie de flous › …* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Inverser et Désaturer** : Négatif de l'image ; retrait des couleurs. — *Image › Ajustements › Inverser (Ctrl+I) ; Désaturer (Ctrl+Maj+U)* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Niveaux (Ctrl+L)** : Éditeur de niveaux sur mesure : histogramme, curseurs noir / gamma / blanc et niveaux de sortie, par canal. — *Image › Ajustements › Niveaux…* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Noir et blanc (Ctrl+Alt+Maj+B)** : Conversion noir et blanc réglable par couleur, avec teinte possible. — *Image › Ajustements › Noir et blanc…* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Recadrer, Rogner, Tout afficher** : Recadre sur la sélection, rogne les bords transparents ou unis, révèle tout le contenu. — *Image › Recadrer ; Rogner les bords… ; Tout afficher* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Rotation de l'image** : Rotation 180°, 90° horaire ou antihoraire, angle personnalisé ; retourner le canevas horizontalement ou verticalement. — *Image › Rotation de l'image › …* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Réglages de couleur** : Filtre photo, Mélangeur de canaux, Table de correspondance des couleurs, Postériser, Seuil, Mappage de dégradé, Couleur sélective, Remplacer la couleur. — *Image › Ajustements › …* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Réglages de tonalité** : Luminosité/Contraste, Exposition, Vibrance, Ombres/Hautes lumières, Tonalité HDR, Égaliser. — *Image › Ajustements › …* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Taille de l'image et du canevas** : Redimensionne l'image ou agrandit le canevas. — *Image › Taille de l'image… (Ctrl+Alt+I) ; Taille du canevas… (Ctrl+Alt+C)* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Teinte/Saturation (Ctrl+U)** : Teinte, saturation, luminosité, globalement ou par gamme de couleurs. — *Image › Ajustements › Teinte/Saturation…* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Bichromie** : Monotone, bichromie, trichromie ou quadrichromie, avec nom et couleur de chaque encre (courbes d'encre linéaires). — *Image › Mode › Duotone (depuis Niveaux de gris)* (PR #277 · commit 8ad8a6f4 · t158)
- [ ] **Bitmap et Couleurs indexées** : Conversion en bitmap (depuis les niveaux de gris) ou en couleurs indexées, par dialogue. — *Image › Mode › Bitmap / Couleurs indexées* (PR #277 · commit 8ad8a6f4 · t158)
- [ ] **Déplacement** : Déforme l'image selon une carte prise dans un autre document ouvert. — *Filtre › Déformation › Déplacement… : choisir la carte de déplacement* (PR #277 · commit 8ad8a6f4 · t158)
- [ ] **Faire correspondre la couleur** : Reprend les couleurs d'un autre document ouvert (image fusionnée). — *Image › Ajustements › Faire correspondre la couleur… : liste des autres documents ouverts* (PR #277 · commit 8ad8a6f4 · t158)
- [ ] **Flamme** : Rend des flammes le long d'un tracé du document (ou sur toute la toile). — *Filtre › Rendu › Flamme… : choisir le tracé suivi* (PR #277 · commit 8ad8a6f4 · t158)
- [ ] **Galerie de filtres** : 47 effets artistiques en 6 dossiers à vignettes (Artistiques, Contours, Déformation, Esquisse, Esthétiques, Texture), empilables, avec aperçu du moteur. — *Filtre › Galerie de filtres… : pile de calques d'effet (œil, nouveau, supprimer, monter, descendre)* (PR #275 · commit 86899170 · t157)
- [ ] **Image › Mode : conversions** : Conversion en Niveaux de gris, RVB, CMJN, Lab, Multicanal, et profondeur 8, 16 ou 32 bits/canal ; mode et profondeur cochés ; entrées impossibles grisées. — *Image › Mode › … ; confirmation « Aplatir et convertir » quand la conversion aplatit plusieurs calques* (PR #277 · commit 8ad8a6f4 · t158)
- [ ] **Table des couleurs** : Lit et modifie la table d'une image indexée : grille 16 × 16, préréglages (Corps noir, Niveaux de gris, Spectre, Système, Web), couleur transparente. — *Image › Mode › Table des couleurs… ; clic sur une case pour la changer* (PR #277 · commit 8ad8a6f4 · t158)

### Calques, masques et espaces de travail (`photolab-avance`, lot t176, reprend : nouveau) — 109 manques

**Photolab — Calques, masques et styles** — accès : Barre des applications → icône Photolab (iris, « Retouche d'image & calques », comme le Vectorlab) ; URL /photolab/ ; panneau Calques et menu Calque

- [ ] **Aligner et répartir** : Aligne ou répartit les calques sélectionnés (bords, centres). — *Calque › Aligner › … ; Calque › Répartir › …* (PR #264 · commit db72da5b · t137)
- [ ] **Calques de remplissage** : Calque de couleur unie, de dégradé ou de motif. — *Calque › Nouveau calque de remplissage › Couleur unie… / Dégradé… / Motif…* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Calques de réglage** : 16 réglages non destructifs : Luminosité/Contraste, Niveaux, Courbes, Exposition, Vibrance, Teinte/Saturation, Balance des couleurs, Noir et blanc, Filtre photo, Mélangeur de canaux, Table de correspondance, Inverser, Postériser, Seuil, Mappage de dégradé, Couleur sélective. — *Calque › Nouveau calque de réglage › … ou bouton du pied du panneau Calques* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Copier, coller, effacer un style** : Copie les effets d'un calque vers un autre, ou les retire ; lumière globale, masquer tous les effets, mettre les effets à l'échelle. — *Calque › Style de calque › Copier / Coller / Effacer le style de calque, Lumière globale…, Masquer tous les effets, Mettre les effets à l'échelle…* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Filtrer les calques par nom** : Champ de filtre en tête du panneau Calques. (PR #264 · commit db72da5b · t137)
- [ ] **Fusionner et aplatir** : Fusionner les calques (Ctrl+E), fusionner les calques visibles (Ctrl+Maj+E), aplatir l'image. — *Calque › Fusionner…, Aplatir l'image* (PR #264 · commit db72da5b · t137)
- [ ] **Grouper, dissocier, masque de découpe** : Groupe ou dissocie les calques ; crée un masque de découpe. — *Calque › Grouper les calques, Dissocier ; Créer un masque de découpe (Ctrl+Alt+G)* (PR #264 · commit db72da5b · t137)
- [ ] **Liste des calques** : Calques et groupes avec œil, vignette, nom et cadenas de l'arrière-plan ; repli des groupes. — *Clic = choisir, Ctrl+clic = ajouter, Maj+clic = plage ; double-clic sur le nom = renommer* (PR #264 · commit db72da5b · t137)
- [ ] **Menu Calque : nouveaux calques** : Nouveau calque (Ctrl+Maj+N), d'après l'arrière-plan, groupe, groupe d'après des calques, calque par copie (Ctrl+J) ou par coupe (Ctrl+Maj+J). — *Calque › Nouveau › …* (PR #264 · commit db72da5b · t137)
- [ ] **Menus Masque de calque et Masque vectoriel** : Tout afficher, tout masquer, afficher ou masquer la sélection, d'après la transparence, supprimer, appliquer ; masque vectoriel d'après le tracé actif. — *Calque › Masque de calque › … ; Calque › Masque vectoriel › …* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Mode de fusion, opacité, fond** : 27 modes de fusion (Normal… Luminosité), opacité et fond du calque. — *En haut du panneau Calques* (PR #264 · commit db72da5b · t137)
- [ ] **Modifier un calque de réglage dans Propriétés** : Le réglage du calque actif se modifie dans Propriétés / Ajustements ; Courbes et Niveaux y ont leur éditeur. — *Choisir le calque de réglage, puis le panneau Propriétés* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Objets dynamiques** : Convertir en objet dynamique, nouvel objet par copie, rastériser, modes de pile. — *Calque › Objets intelligents › …* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Options de fusion du style** : Mode, opacité et opacité du fond dans le dialogue Style de calque. — *Calque › Style de calque › Options de fusion…* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Organiser les calques** : Mettre au premier plan, avancer, reculer, mettre à l'arrière-plan, inverser l'ordre. — *Calque › Organiser › … (Ctrl+Maj+] / Ctrl+] / Ctrl+[ / Ctrl+Maj+[)* (PR #264 · commit db72da5b · t137)
- [ ] **Pied du panneau Calques** : Nouveau calque, nouveau groupe, dupliquer, fusionner vers le bas, supprimer. — *Boutons au bas du panneau Calques* (PR #264 · commit db72da5b · t137)
- [ ] **Rastériser et détourage** : Rastérise texte, forme, objet dynamique… ; supprime franges, fond noir ou blanc, décontamine les couleurs. — *Calque › Rastériser › … ; Calque › Détourage › …* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Réglages par gamme et par canal** : Teinte/Saturation par gamme, Balance des couleurs par tons (Cyan–Rouge, Magenta–Vert, Jaune–Bleu), Mélangeur de canaux par couche de sortie, Couleur sélective par gamme, Mappage de dégradé (couleurs de départ et d'arrivée). — *Panneau Propriétés d'un calque de réglage* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Réordonner et grouper par glisser** : Déplace un calque au-dessus, en dessous ou dans un groupe. — *Glisser une ligne du panneau Calques* (PR #264 · commit db72da5b · t137)
- [ ] **Style de calque** : Dialogue des effets : Biseautage et estampage, Contour, Ombre interne, Lueur interne, Satin, Incrustation couleur, Incrustation en dégradé, Incrustation de motif, Lueur externe, Ombre portée, avec aperçu. — *Calque › Style de calque › … ; bouton fx du panneau Calques ou double-clic sur le badge fx* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Verrous de calque** : Verrouiller les pixels transparents, les pixels, la position, l'imbrication, ou tout. — *Boutons « Verr. : » du panneau Calques* (PR #264 · commit db72da5b · t137)
- [ ] **Bouton Masque** : Ajoute un masque de fusion qui révèle la sélection (ou tout) ; Alt = masque ; sur un calque déjà masqué, ajoute un masque vectoriel. — *Bouton Masque du pied du panneau Calques* (PR #275 · commit 86899170 · t157)
- [ ] **Convertir pour les filtres dynamiques** : Transforme le calque en objet dynamique dont les filtres restent modifiables. — *Filtre › Convertir pour les filtres intelligents* (PR #275 · commit 86899170 · t157)
- [ ] **Exportation rapide du calque** : Exporte le calque seul, rogné, au format PNG. — *Calque › Exportation rapide au format PNG (Ctrl+Maj+')* (PR #277 · commit 8ad8a6f4 · t158)
- [ ] **Exporter le calque sous** : Exporte le calque seul en PNG, JPG ou WEBP, à l'échelle choisie, vers le téléchargement ou la Bibliothèque. — *Calque › Exporter sous… (Ctrl+Alt+Maj+')* (PR #277 · commit 8ad8a6f4 · t158)
- [ ] **Filtres dynamiques sous le calque** : Les filtres d'un objet dynamique apparaissent en sous-lignes : œil global et par filtre, options de fusion, supprimer, réordonner. — *Panneau Calques : glisser une sous-ligne pour changer l'ordre* (PR #275 · commit 86899170 · t157)
- [ ] **Lier les calques** : Lie deux calques ou plus (icône de lien sur la ligne) ; un second clic les délie. — *Bouton Lier du pied du panneau Calques ou Calque › Lier les calques* (PR #275 · commit 86899170 · t157)
- [ ] **Rééditer un filtre dynamique** : Rouvre le dialogue du filtre (ou la galerie avec sa pile) avec aperçu pour changer ses réglages. — *Double-clic sur la sous-ligne du filtre* (PR #275 · commit 86899170 · t157)
- [ ] **Vignette de masque** : Vignette du masque à côté du calque, rendue par le moteur, avec chaîne de liaison. — *Maj+clic = désactiver (croix rouge) ; Alt+clic = voir le masque seul ; Ctrl+clic = sélection ; clic sur la chaîne = lier/délier* (PR #275 · commit 86899170 · t157)
**Photolab — Panneaux** — accès : Barre des applications → icône Photolab (iris, « Retouche d'image & calques », comme le Vectorlab) ; URL /photolab/ ; colonne de panneaux à droite ou menu Fenêtre

- [ ] **Groupe Pinceaux** : Groupe de quatre onglets : Pinceaux, Paramètres de pinceau, Source de duplication, Outils prédéfinis. — *Fenêtre › Pinceaux / Paramètres du pinceau (F5) / Source de clonage / Préréglages d'outils* (PR #268 · commit 7dc1700b · t155)
- [ ] **Onglet Pinceaux** : Liste des pointes du moteur avec recherche ; un clic applique la pointe. (PR #268 · commit 7dc1700b · t155)
- [ ] **Outils prédéfinis** : Préréglages d'outils (ex. Gomme douce 60 px) ; nouveau, supprimer, filtrer sur l'outil actif. (PR #268 · commit 7dc1700b · t155)
- [ ] **Panneau Compositions de calques** : Enregistre des états de calques (visibilité, position, apparence) et passe de l'un à l'autre ; Dernier état du document. — *Fenêtre › Compositions de calques : nouvelle, appliquer, précédente / suivante, mettre à jour, supprimer, double-clic = renommer* (PR #271 · commit 2301976e · t153)
- [ ] **Panneau Couches** : Couches de couleur et alpha : œil, cible, vignettes ; charger comme sélection, enregistrer la sélection, nouvelle couche, supprimer, renommer une alpha. — *Fenêtre › Canaux ; Ctrl+clic = charger (Maj / Alt pour ajouter / retirer)* (PR #271 · commit 2301976e · t153)
- [ ] **Panneau Couleur** : Couleurs de premier plan et d'arrière-plan, sélecteur et code hexadécimal. — *Fenêtre › Couleur (F6)* (PR #264 · commit db72da5b · t137)
- [ ] **Panneau Dégradés** : Neuf groupes de dégradés du moteur, recherche, nouveau dégradé et groupes. — *Fenêtre › Dégradés ; clic = choisir, double-clic = calque de dégradé* (PR #271 · commit 2301976e · t153)
- [ ] **Panneau Histogramme** : Histogramme par canal (RVB, Rouge, Vert, Bleu, Luminosité) avec moyenne, écart type, médiane et nombre de pixels. — *Fenêtre › Histogramme* (PR #271 · commit 2301976e · t153)
- [ ] **Panneau Historique** : Liste des étapes traduites ; clic sur une étape antérieure = y revenir ; boutons annuler / rétablir. — *Fenêtre › Historique* (PR #264 · commit db72da5b · t137)
- [ ] **Panneau Infos** : Couleur sous le pointeur en R/V/B et C/M/J/N, position X/Y, taille de la sélection et du document. — *Fenêtre › Infos (F8)* (PR #271 · commit 2301976e · t153)
- [ ] **Panneau Motifs** : Motifs à vignettes rendues par le moteur ; Définir un motif depuis la sélection ou le document. — *Fenêtre › Motifs ; clic = choisir, double-clic = calque de motif* (PR #271 · commit 2301976e · t153)
- [ ] **Panneau Navigateur** : Vignette de l'image avec le cadre de la vue. — *Fenêtre › Navigation ; clic ou glisser dans la vignette = recentrer* (PR #264 · commit db72da5b · t137)
- [ ] **Panneau Nuancier** : 40 nuances en 4 groupes, nuances récentes, recherche, groupes personnels gardés par Deepotus. — *Fenêtre › Nuancier ; clic = premier plan, Alt+clic = arrière-plan ; nouvelle nuance, nouveau groupe, double-clic = renommer, clic droit + Supprimer* (PR #271 · commit 2301976e · t153)
- [ ] **Panneau Propriétés** : Sans calque : dimensions, résolution, mode, profondeur du document ; avec calque : nom, type, position et taille. — *Fenêtre › Propriétés* (PR #264 · commit db72da5b · t137)
- [ ] **Paramètres de pinceau** : Forme de la pointe : taille, dureté, pas, espacement, angle, arrondi, retourner X / Y. — *F5* (PR #268 · commit 7dc1700b · t155)
- [ ] **Raccourcis des couches** : Affiche le composite ou une couche seule au clavier. — *Ctrl+2 = composite ; Ctrl+3, Ctrl+4… = couleurs puis alpha* (PR #271 · commit 2301976e · t153)
- [ ] **Rail des panneaux** : Colonne d'icônes à droite pour replier ou rouvrir chaque groupe de panneaux. — *Clic sur une icône du rail* (PR #264 · commit db72da5b · t137)
- [ ] **Source de duplication** : Source du tampon et du correcteur : position, décalage, largeur, hauteur, retournements, réinitialiser. (PR #268 · commit 7dc1700b · t155)
- [ ] **Panneau Caractère** : Police, style, taille, interlignage, crénage, approche, échelles, décalage vertical, couleur, faux gras / italique, capitales, souligné, barré. — *Fenêtre › Caractère ou Texte › Panneaux › Panneau Caractère* (PR #274 · commit e44037ea · t156)
- [ ] **Panneau Formes** : Formes personnalisées par groupes avec vignettes rendues par le moteur. — *Fenêtre › Formes ; clic = forme de l'outil, double-clic = la placer* (PR #274 · commit e44037ea · t156)
- [ ] **Panneau Glyphes** : Caractères par catégorie (latin, grec, cyrillique, ponctuation, monnaies, maths, flèches, ornements) et récents. — *Fenêtre › Glyphes ; double-clic = insérer dans le texte* (PR #274 · commit e44037ea · t156)
- [ ] **Panneau Paragraphe** : Sept alignements, retraits, espace avant / après, césure, direction. — *Fenêtre › Paragraphe* (PR #274 · commit e44037ea · t156)
- [ ] **Panneau Styles** : Styles de calque prêts (Ombre portée, Néon, Chrome, Or, Verre…) à vignettes. — *Fenêtre › Styles ; clic = appliquer, Maj+clic = ajouter ; nouveau style d'après le calque actif* (PR #274 · commit e44037ea · t156)
- [ ] **Panneau Tracés** : Tracés enregistrés, de travail et du calque ; montrer, enregistrer, remplir, contour au pinceau, charger comme sélection, tracé depuis la sélection. — *Fenêtre › Tracés ; double-clic = enregistrer / renommer* (PR #274 · commit e44037ea · t156)
- [ ] **Styles de caractère et de paragraphe** : Styles de texte réutilisables : appliquer (Alt = effacer les remplacements), nouveau, dupliquer, redéfinir, supprimer, renommer. — *Fenêtre › Styles de caractère / Styles de paragraphe* (PR #274 · commit e44037ea · t156)
**Photolab — Affichage et espaces de travail** — accès : Barre des applications → icône Photolab (iris, « Retouche d'image & calques », comme le Vectorlab) ; URL /photolab/ ; menus Affichage et Fenêtre, sélecteur d'espace en haut à droite

- [ ] **Afficher : contours et aperçus** : Contours du calque, contours de la sélection, repères du canevas, grille de pixels (au-delà de 500 %), aperçu du pinceau, Tout. — *Affichage › Afficher › …* (PR #270 · commit d0c16dd1 · t152)
- [ ] **Aimantation** : Aimante sélections, recadrage, déplacement et repères aux repères, à la grille, aux calques et aux limites du document. — *Affichage › Aimanter (Ctrl+Maj+;) ; Affichage › Aimanter à › Repères, Grille, Calques, Limites du document, Tout* (PR #270 · commit d0c16dd1 · t152)
- [ ] **Aperçu pixel art** : Pixels francs à tout niveau de zoom. — *Affichage › Aperçu pixel art* (PR #270 · commit d0c16dd1 · t152)
- [ ] **Disposition mémorisée par espace** : Ordre, repli ou masquage des groupes, onglet devant et barre d'outils sont retenus pour chaque espace. (PR #269 · commit 8b26219d · t151)
- [ ] **Espaces de travail fournis** : Sept dispositions : Essentiel (par défaut), Base (15 outils sur une colonne), Graphisme et web, Mouvement, Peinture, Photo, Pixel art. — *Sélecteur d'espace en haut à droite ou Fenêtre › Espace de travail › …* (PR #269 · commit 8b26219d · t151)
- [ ] **Extras** : Montre ou masque d'un coup grille, repères et contours. — *Affichage › Extras (Ctrl+H)* (PR #270 · commit d0c16dd1 · t152)
- [ ] **Fenêtre › panneaux cochés** : Chaque panneau existant s'ouvre ou se masque depuis le menu Fenêtre, coché quand il est visible ; Fenêtre › Options et Outils masquent les barres. — *Fenêtre › <panneau> ; F5, F6, F7, F8* (PR #269 · commit 8b26219d · t151)
- [ ] **Grille** : Grille d'un pouce en 4 subdivisions par défaut. — *Affichage › Afficher › Grille (Ctrl+')* (PR #270 · commit d0c16dd1 · t152)
- [ ] **Modes d'écran** : Standard, plein écran avec menus, plein écran (barres et panneaux masqués). — *Affichage › Mode d'écran › … ; F = mode suivant, Échap = mode standard* (PR #270 · commit d0c16dd1 · t152)
- [ ] **Navigation dans la toile** : Zoom et défilement à la souris et au clavier. — *Ctrl+molette ou pincement = zoom ; Alt+molette = zoom fin ; molette = défiler (Maj = horizontal) ; Ctrl+0 = adapter ; Ctrl+1 = 100 %* (PR #264 · commit db72da5b · t137)
- [ ] **Nouvel espace de travail** : Enregistre la disposition actuelle comme espace personnel (jusqu'à 20), en option avec la barre d'outils ; gardé dans le dossier de données. — *Fenêtre › Espace de travail › Nouvel espace de travail… : nom, case Barre d'outils* (PR #269 · commit 8b26219d · t151)
- [ ] **Options d'affichage des extras** : Choisit les extras visibles dans un dialogue ; gardé d'une session à l'autre. — *Affichage › Afficher › Options d'affichage des extras…* (PR #270 · commit d0c16dd1 · t152)
- [ ] **Repères** : Créer un repère en glissant depuis une règle ; le déplacer ou le supprimer (en le sortant) avec l'outil Déplacement ; nouveau repère, disposition de repères, effacer. — *Affichage › Afficher › Repères (Ctrl+;) ; Affichage › Nouveau repère…, Nouvelle disposition de repères…, Effacer les repères* (PR #270 · commit d0c16dd1 · t152)
- [ ] **Règles** : Règles graduées autour de la toile. — *Affichage › Règles (Ctrl+R)* (PR #270 · commit d0c16dd1 · t152)
- [ ] **Réinitialiser l'espace** : Remet l'espace actif à sa disposition d'origine. — *Fenêtre › Espace de travail › Réinitialiser <espace>* (PR #269 · commit 8b26219d · t151)
- [ ] **Supprimer un espace** : Supprime un espace personnel ; supprimer l'actif ramène à Essentiel. — *Fenêtre › Espace de travail › Supprimer l'espace de travail…* (PR #269 · commit 8b26219d · t151)
- [ ] **Symétrie horizontale de la vue** : Montre l'image en miroir sans modifier le document. — *Affichage › Symétrie horizontale* (PR #270 · commit d0c16dd1 · t152)
- [ ] **Verrouiller l'espace** : Les changements de disposition restent possibles mais ne sont plus mémorisés. — *Fenêtre › Espace de travail › Verrouiller l'espace de travail* (PR #269 · commit 8b26219d · t151)
- [ ] **Verrouiller les repères** : Empêche de déplacer les repères. — *Affichage › Verrouiller les repères (Ctrl+Alt+;)* (PR #270 · commit d0c16dd1 · t152)
- [ ] **Zooms du menu Affichage** : Zoom avant, zoom arrière, adapter à l'écran, adapter le(s) calque(s), 100 %, 200 %, taille d'impression. — *Affichage › Zoom avant (Ctrl+=), Zoom arrière (Ctrl+-), Adapter à l'écran, 100 % (Ctrl+1), 200 %, Taille d'impression* (PR #270 · commit d0c16dd1 · t152)
**Photolab — Mesure, notes et tranches** — accès : Barre des applications → icône Photolab (iris, « Retouche d'image & calques », comme le Vectorlab) ; URL /photolab/ ; emplacements Pipette (I) et Recadrage (C) de la barre d'outils, menus Image › Analyse et Fenêtre

- [ ] **Échelle et points de données** : Définit l'échelle de mesure et les colonnes relevées. — *Image › Analyse › Définir l'échelle de mesure… ; Sélectionner les points de données…* (PR #265 · commit 5331c8f3 · t138)
- [ ] **Afficher compteur, notes, tranches** : Montre ou masque les marques de comptage, les notes et les tranches sur la toile. — *Affichage › Afficher › Compteur / Notes / Tranches* (PR #280 · commit ad35e86f · t160)
- [ ] **Aimanter aux tranches** : Les bords des tranches deviennent des cibles d'aimantation. — *Affichage › Aimanter à › Tranches* (PR #280 · commit ad35e86f · t160)
- [ ] **Compteur (I)** : Pose des marques numérotées sur l'image. — *Clic = marque ; Alt+clic = retirer ; glisser une marque = déplacer ; barre : groupe, couleur, taille des marques et des numéros, visibilité, nouveau groupe, supprimer, Effacer le comptage* (PR #280 · commit ad35e86f · t160)
- [ ] **Diviser et promouvoir une tranche** : Divise une tranche en lignes et colonnes ; promeut une tranche automatique en tranche utilisateur. — *Barre de la Sélection de tranche → Diviser… / Promouvoir* (PR #280 · commit ad35e86f · t160)
- [ ] **Exporter le journal en CSV** : Télécharge le journal des mesures en CSV (lignes choisies, compatible tableur). — *Bouton Exporter en CSV… du panneau Mesures* (PR #280 · commit ad35e86f · t160)
- [ ] **Importer des notes** : Copie les notes d'un autre document ouvert dans le document actif. — *Fichier › Importer › Notes… : choisir le document source* (PR #280 · commit ad35e86f · t160)
- [ ] **Journal des mesures** : Tableau des mesures enregistrées (règle, comptage, sélection) avec les colonnes choisies ; supprimer des lignes, tout effacer. — *Fenêtre › Journal des mesures (onglet Mesures) ; Image › Analyse › Enregistrer les mesures* (PR #280 · commit ad35e86f · t160)
- [ ] **Note (I)** : Pose une note (auteur, couleur, texte) sur l'image. — *Clic = note ; glisser l'icône = déplacer ; barre : Auteur, Couleur, Effacer toutes les notes, Panneau Notes* (PR #280 · commit ad35e86f · t160)
- [ ] **Options de tranche** : Nom, type (Image, Sans image, Tableau), adresse du lien, cible, message, texte de remplacement, couleur de fond. — *Double-clic sur une tranche ou bouton Options de tranche…* (PR #280 · commit ad35e86f · t160)
- [ ] **Panneau Notes** : Texte de la note choisie, précédente / suivante, supprimer. — *Fenêtre › Notes (onglet Notes du groupe Infos)* (PR #280 · commit ad35e86f · t160)
- [ ] **Redresser le calque** : Fait pivoter le calque pour que la ligne de la règle devienne horizontale. — *Barre de la Règle → Redresser le calque* (PR #280 · commit ad35e86f · t160)
- [ ] **Règle (I)** : Mesure une distance et un angle ; Alt depuis une extrémité = rapporteur ; Maj = 45°. — *Glisser ; barre X, Y, L, H, A, L1, L2 ; Redresser le calque ; Effacer la règle* (PR #280 · commit ad35e86f · t160)
- [ ] **Sélection de tranche (C)** : Choisit, déplace et redimensionne les tranches. — *Clic = choisir ; glisser = déplacer ; poignées = redimensionner ; Suppr = supprimer* (PR #280 · commit ad35e86f · t160)
- [ ] **Tranche (C)** : Découpe l'image en tranches utilisateur (pour le web). — *Glisser (Maj = carré) ; Tranches d'après les repères* (PR #280 · commit ad35e86f · t160)
- [ ] **Verrouiller et effacer les tranches** : Empêche toute nouvelle tranche ou retire toutes les tranches. — *Affichage › Verrouiller les tranches ; Affichage › Effacer les tranches* (PR #280 · commit ad35e86f · t160)
**Photolab — Préférences et personnalisation** — accès : Barre des applications → icône Photolab (iris, « Retouche d'image & calques », comme le Vectorlab) ; URL /photolab/ ; menu Édition › Préférences, Raccourcis clavier, Menus, Préréglages

- [ ] **Dialogue Préférences** : Préférences de l'écran en 18 sections, enregistrées dans le dossier de données de Deepotus ; chaque entrée de menu ouvre sa section. — *Édition › Préférences › … ; OK enregistre, Annuler ne change rien* (PR #278 · commit 53dceb3b · t159)
- [ ] **Exporter / importer des préréglages** : Sauvegarde les préréglages dans un fichier .json téléchargé et les réimporte depuis le PC. — *Édition › Préréglages › Exporter/importer des préréglages…* (PR #278 · commit 53dceb3b · t159)
- [ ] **Gestionnaire de préréglages** : Pinceaux, formes personnalisées et motifs de la session : renommer, supprimer, monter, descendre. — *Édition › Préréglages › Gestionnaire de préréglages…* (PR #278 · commit 53dceb3b · t159)
- [ ] **Menus personnalisés** : Masque des entrées de menu ou leur donne une couleur ; Afficher tous les éléments de menu. — *Édition › Menus… (Ctrl+Alt+Maj+M)* (PR #278 · commit 53dceb3b · t159)
- [ ] **Préférences : Curseurs** : Curseurs des outils de peinture (standard, précis, pointe normale ou en taille réelle), autres curseurs, réticule dans la pointe. — *Édition › Préférences › Curseurs…* (PR #278 · commit 53dceb3b · t159)
- [ ] **Préférences : Espace de travail** : Grands onglets ; mémoriser les modifications des espaces de travail. — *Édition › Préférences › Espace de travail…* (PR #278 · commit 53dceb3b · t159)
- [ ] **Préférences : Gestion des fichiers et Exportation** : Extension en minuscules ; format de l'exportation rapide (PNG, JPG, WEBP), qualité JPG, destination (demander, télécharger, Bibliothèque). — *Édition › Préférences › Gestion des fichiers… / Exportation…* (PR #278 · commit 53dceb3b · t159)
- [ ] **Préférences : Interface** : Couleur du fond de la toile (thème, noir, gris, personnalisée), bordure du document (ombre, filet, aucune), infobulles, couleurs des menus. — *Édition › Préférences › Interface…* (PR #278 · commit 53dceb3b · t159)
- [ ] **Préférences : Outils** : Utiliser Maj pour changer d'outil, défilement au-delà du document, zoom sur le point cliqué au centre. — *Édition › Préférences › Outils…* (PR #278 · commit 53dceb3b · t159)
- [ ] **Préférences : Paramètres** : Zoom avec la molette ; au placement, redimensionner l'image et toujours créer un objet dynamique. — *Édition › Préférences › Paramètres…* (PR #278 · commit 53dceb3b · t159)
- [ ] **Préférences : Repères et grille** : Couleur et style (traits, tirets, pointillés) des repères et de la grille, pas, unité et subdivisions de la grille. — *Édition › Préférences › Repères, grille et tranches…* (PR #278 · commit 53dceb3b · t159)
- [ ] **Préférences : Texte** : Taille de l'aperçu des polices ; Échap valide le texte. — *Édition › Préférences › Texte…* (PR #278 · commit 53dceb3b · t159)
- [ ] **Préférences : Transparence** : Taille et couleurs du damier sous les zones transparentes. — *Édition › Préférences › Transparence et gamut…* (PR #278 · commit 53dceb3b · t159)
- [ ] **Préférences : Unités et règles** : Unité des règles (pixels, pouces, cm, mm, points typographiques, picas, pourcentage). — *Édition › Préférences › Unités et règles…* (PR #278 · commit 53dceb3b · t159)
- [ ] **Raccourcis clavier** : Change les raccourcis des commandes (Ctrl, Alt ou F1-F12) et la lettre des outils ; un conflit est nommé et retiré à l'autre commande ; Par défaut, Tout par défaut. — *Édition › Raccourcis clavier… (Ctrl+Alt+Maj+K) ou Fenêtre › Espace de travail › Raccourcis clavier…* (PR #278 · commit 53dceb3b · t159)
- [ ] **Réinitialiser les préférences** : Remet préférences, raccourcis et menus aux valeurs par défaut, après confirmation. — *Bouton Réinitialiser les préférences… du dialogue* (PR #278 · commit 53dceb3b · t159)
- [ ] **Résumer les raccourcis** : Télécharge la liste des raccourcis en page HTML. — *Raccourcis clavier › Résumer…* (PR #278 · commit 53dceb3b · t159)
- [ ] **Sections explicatives** : Intégrations d'IA, Journal de l'historique, Performances, Disques de travail, Extensions, Commandes avancées, Valeurs Raw : une phrase dit ce que Deepotus gère à leur place. — *Édition › Préférences › …* (PR #278 · commit 53dceb3b · t159)
- [ ] **Touches de modification** : Panneau flottant Maj / Ctrl / Alt pour écran tactile : un clic vaut pour l'action suivante, un double clic tient la touche. — *Fenêtre › Touches de modification* (PR #278 · commit 53dceb3b · t159)

### Dessiner en vectoriel (Vectorlab) (`vectorlab`, lot t177, reprend : nouveau) — 140 manques

**Vectorlab — interface Affinity** — accès : Barre des applications → Vectorlab (page /vectorlab/) ; aussi hub Game Assets → onglet Assets 2D → carte Pixel (ouvre le persona Pixel)

- [ ] **Brouillon automatique** : Le document est sauvegardé en brouillon toutes les 30 s, proposé à la réouverture et effacé à l'Enregistrement. — *Fichier → Restaurer le brouillon* (commit 0339b5c8 · lot A)
- [ ] **Bulles d'information riches** : Bulles stylées centrées sous l'élément, gestes en gras, apparaissant après 450 ms et masquées au clic, au focus ou à la molette. — *Survoler un bouton* (commit a1cc6cec · 1a8134d4 · 5716f970)
- [ ] **Design aéré des panneaux** : Rythme régulier, têtes en petites capitales, libellés alignés, champs de 28 px aux nombres centrés, boutons de hauteur égale. (commit a1cc6cec)
- [ ] **Historique 1000 pas et instantanés** : Jusqu'à 1000 annulations et des instantanés nommés pour revenir à un état précis. — *Édition → Ajouter un instantané ; onglet Historique* (commit e05fc883 · e5ab0958 · lot B)
- [ ] **Menu détaché Apparence** : Fond et contour via le nuancier, sans fond / sans contour, épaisseurs, opacités, dégradés, transparence, motif, effets. — *Bouton-menu Apparence de la barre* (commit 884cae70)
- [ ] **Menu détaché Image** : Poser une image (Bibliothèque, fichier, presse-papiers, génération), vectoriser, image entière, verrou, éditer les pixels. — *Bouton-menu Image de la barre* (commit 884cae70)
- [ ] **Menus détachés de la barre** : Menus surgissants par outil (Forme, Symboles, Sélection, Nœuds, Typographies, Pinceau, Gomme, Coin, Terrains, Pixel, Tranches…) qui regroupent leurs actions. — *Clic droit, triangle d'angle ou appui long sur l'outil* (commit 1a8134d4 · 3c32bf8f)
- [ ] **Miniatures de calques** : Chaque calque montre une vignette de son seul contenu sur damier. — *Panneau Calques* (commit 3be776e3)
- [ ] **Panneau de droite qui défile** : Le panneau ne déborde plus du canevas : réglages qui défilent, sections repliables dont l'état est mémorisé, calques collés en bas. — *Cliquer la tête d'une section pour la replier* (commit 628bbf47)
- [ ] **Aide Raccourcis clavier** : Liste de tous les raccourcis du Vectorlab dans une fenêtre d'aide ; le menu Aide donne aussi le Guide du Vectorlab et À propos. — *F1 ou Aide → Raccourcis clavier…* (commit fbada079 · relooking R1)
- [ ] **Barre contextuelle par outil** : Sous les menus, une barre montre ce qui est sélectionné et les réglages de l'outil courant (opacité, forme, largeur, rayon, profil, terrain, police, rayon/dureté/tolérance des pixels, mode de tranche). — *Changer une valeur l'applique aussitôt* (commit d0b351d8 · relooking R5)
- [ ] **Barre d'état** : Phrase d'aide de l'outil courant avec les gestes en gras (comme Affinity), pagination, messages et cotes de la sélection. — *Bande en bas de l'écran* (commit fbada079 · relooking R1)
- [ ] **Barre de menus Affinity** : Dix menus façon Affinity (Fichier, Édition, Document, Texte, Vecteur, Pixel, Calque, Affichage, Fenêtre, Aide) qui exécutent vraiment les actions ; les entrées impossibles sont grisées. — *Barre du haut ; raccourcis affichés à droite de chaque entrée* (commit fbada079 · ed610c07 · relooking R1)
- [ ] **Colonne d'outils par familles** : Outils regroupés en familles avec icônes fines ; seul l'outil courant de chaque famille est visible, les autres dans un menu vertical. — *Triangle d'angle ou appui long = menu de la famille ; clic droit = réglages de l'outil ; le raccourci clavier bascule l'outil ; famille choisie mémorisée* (commit 3ba22036 · ccd4d1cb · relooking R2)
- [ ] **Configuration du document** : Une seule fenêtre pour la taille, la résolution (dpi), l'unité et le fond du document, annulable d'un Ctrl+Z. — *Barre contextuelle (roue) ou Fichier/Document → Configuration* (commit d0b351d8 · relooking R5)
- [ ] **Deux personas Vecteur / Pixel** : Le Vectorlab a deux espaces de travail, Vecteur et Pixel, avec leurs outils et panneaux ; l'export devient un onglet commun et l'outil Tranche est partagé. — *Pastilles colorées Vecteur / Pixel en haut à gauche, ou Affichage → Persona* (commit 0dd470f6 · fbada079 · relooking R1)
- [ ] **Menu Affichage** : Zoom ajusté ou 100 %, grille, magnétisme aux objets, unité des règles, bascule de persona Vecteur / Pixel. — *Ctrl+0 ajuster, Ctrl+1 100 %, G grille* (commit fbada079 · relooking R1)
- [ ] **Menu Calque** : Nouveau, renommer, supprimer un calque ; grouper / dégrouper ; verrouiller, masquer ; ordre (tout devant, un cran devant, un cran derrière, tout derrière) ; effets de calque. — *Menu Calque ; Ctrl+G grouper, Ctrl+Maj+G dégrouper* (commit fbada079 · relooking R1)
- [ ] **Menu Document** : Configuration, unité d'affichage suivante, Planches, Marges et fond perdu, Grille du document, Plateau et terrains, Carte réelle, Ajouter un instantané, Historique. — *Menu Document* (commit fbada079 · relooking R1)
- [ ] **Menu Fenêtre** : Ouvre directement un onglet de la pile de droite : Couleur, Apparence, Texte, Calques, Tracé, Image, Stock (Bibliothèque), Transformer, Navigateur, Historique, Exporter. — *Menu Fenêtre* (commit fbada079 · relooking R1)
- [ ] **Menu Fichier** : Accueil (Bibliothèque), Nouveau, Ouvrir, Enregistrer, Restaurer le brouillon, Insérer une image, Insérer depuis la Bibliothèque, Nouveau depuis Presse-papiers, Importer un GPX, Exporter, Exporter SVG, Exporter PNG 2×, Impression 3D, Vers la Bible, Configuration du document. — *Ctrl+Alt+H accueil, Ctrl+N, Ctrl+O, Ctrl+S, Ctrl+Maj+M insérer une image, Ctrl+Alt+Maj+S exporter* (commit fbada079 · relooking R1)
- [ ] **Menu Édition** : Annuler, Rétablir, Tout sélectionner, Désélectionner, Sélectionner par attribut, Copier, Coller, Dupliquer, Dupliquer en puissance, Supprimer, Créer un style, Ajouter un instantané, Paramètres. — *Ctrl+Z, Ctrl+Maj+Z, Ctrl+A, Échap, Ctrl+C, Ctrl+V, Ctrl+D, Suppr, Ctrl+, (Paramètres)* (commit fbada079 · relooking R1)
- [ ] **Mode de fusion de calque** : Un calque entier peut prendre l'un des 16 modes de fusion (Produit, Superposition…). — *Tête du panneau Calques → menu de fusion* (commit 5c8749c7 · relooking R3)
- [ ] **Nuancier en place** : Le nuancier vit directement dans l'onglet Couleur (en fenêtre surgissante ailleurs), en version compacte. — *Onglet Couleur* (commit 249afedb · 5716f970 · R4/R6)
- [ ] **Onglet de document** : Un onglet affiche « nom @ zoom » et une étoile quand le document n'est pas enregistré ; le nom du document est aussi rappelé au-dessus de la page. (commit fbada079 · 5716f970 · R1/R6)
- [ ] **Panneau Calques façon Affinity** : En tête l'opacité et le mode de fusion du calque ; chaque rangée montre vignette, nom, verrou et œil ; barre d'actions en bas. — *Onglet Calques* (commit 7911db62 · relooking R3)
- [ ] **Panneau Navigateur** : Vignette de tout le document avec le cadre de la vue et un curseur de zoom logarithmique. — *Onglet Navigateur ; déplacer le curseur pour zoomer* (commit 7911db62 · 5c8749c7 · relooking R3)
- [ ] **Panneau Échantillons** : Montre la palette de couleurs du document pour la réutiliser en un clic. — *Onglet Échantillons* (commit 7911db62 · relooking R3)
- [ ] **Panneaux Transformer et Trait** : Les réglages de position/taille et de contour ont chacun leur onglet, distincts de l'Apparence. — *Onglets Transformer / Trait de la pile* (commit 7911db62 · relooking R3)
- [ ] **Paramètres de l'appli** : Préférences du Vectorlab gardées d'une session à l'autre : bulles d'aide, pas de la grille, aimantation. — *Barre contextuelle (icône curseurs) ou Édition → Paramètres (Ctrl+,)* (commit d0b351d8 · relooking R5)
- [ ] **Pile de droite à onglets** : Les panneaux sont rangés en trois groupes d'onglets par persona (comme Affinity) ; l'onglet actif est mémorisé. — *Cliquer l'onglet ; menu Fenêtre pour en ouvrir un* (commit 7911db62 · relooking R3)
- [ ] **Thème sombre Affinity** : Couleurs et densité d'Affinity : fond gris, canevas uni sans damier, champs compacts, listes sombres, curseurs à poignée ronde. (commit 249afedb · relooking R4)
- [ ] **Aide didactique animée** : Un survol long (900 ms) ou le bouton « ? » ouvre une fiche : titre, phrase simple et animation à trois temps faite de vraies captures. — *Survoler l'option ~1 s ou cliquer « ? » à côté* (commit 8e3be59f · finitions UI 4)
- [ ] **Brouillon : Restaurer / Repartir du serveur** : À l'ouverture d'un document avec un brouillon non sauvé, une fenêtre propose de le restaurer ou de repartir de la version du serveur. — *Fenêtre « Brouillon non sauvé »* (commit ec479987)
- [ ] **Contrôles maison des panneaux** : Curseurs, curseurs de teinte et bascules uniformes dans les panneaux Pixel, Apparence et nuancier ; champs de 28 px, boutons qui se rétractent si la place manque. (commit 28837a3c · 7d3d6a10 · finitions UI 3)
- [ ] **Dialogues maison** : Les confirmations, messages et saisies du Vectorlab s'ouvrent dans des fenêtres au style de l'application, plus aucune boîte native du navigateur. (commit 6d0cbe76 · ec479987 · finitions UI 2)
- [ ] **Fiche « Conique »** : Fiche animée du dégradé conique de l'Apparence +. — *Survol long ou « ? »* (commit 799a21c4)
- [ ] **Fiche « Contour sombre »** : Fiche animée de l'option Contour sombre du persona Pixel. — *Survol long ou « ? »* (commit fb9c82ef)
- [ ] **Fiche « Créer le calque pixel »** : Fiche animée : un calque pixel se pose sur le modèle désigné. — *Survol long ou « ? »* (commit 9003a19d)
- [ ] **Fiche « Dépouille des flancs »** : Fiche animée du réglage Dépouille du dialogue Impression 3D (0° → +20°). — *Survol long ou « ? »* (commit 9003a19d)
- [ ] **Fiche « Désigner comme modèle »** : Fiche animée : l'image pâlit, se fige et reçoit une grille. — *Survol long ou « ? »* (commit 799a21c4)
- [ ] **Fiche « Pixeliser l'image »** : Fiche animée : l'image devient de gros carrés à la taille de tuile. — *Survol long ou « ? »* (commit 799a21c4)
- [ ] **Arbre des calques** : Les calques se déplient en arbre montrant leurs objets, l'écrêtage, les masques de transparence et les effets ; l'état replié est mémorisé. — *Triangle devant le calque* (commit 4d83c9e7)
- [ ] **Barre contextuelle en icônes** : Les boutons de la barre contextuelle deviennent 17 icônes avec bulle d'explication et séparateurs. — *Survoler une icône pour sa bulle* (commit 4d83c9e7)
- [ ] **Fiche « Courbes » (carte)** : Fiche animée des courbes de niveau de la Carte réelle. — *Survol long ou « ? »* (PR #256 · commit eeb2f539 · t126)
- [ ] **Fiche « Découper » (carte)** : Fiche animée : la carte devient des cases hexagonales colorées selon l'altitude. — *Survol long ou « ? »* (PR #256 · commit eeb2f539 · t126)
- [ ] **Fiche « En cadre »** : Fiche animée : un texte long passe dans une boîte et revient à la ligne seul. — *Survol long ou « ? »* (PR #256 · commit eeb2f539 · t126)
- [ ] **Fiche « Motif »** : Fiche animée : la forme se remplit d'un motif répété. — *Survol long ou « ? »* (PR #256 · commit eeb2f539 · t126)
- [ ] **Fiche « Sur chemin »** : Fiche animée : le texte suit la ligne tracée. — *Survol long ou « ? »* (PR #256 · commit eeb2f539 · t126)
- [ ] **Fiche « Transparence »** : Fiche animée : la forme s'efface progressivement d'un côté à l'autre. — *Survol long ou « ? »* (PR #256 · commit eeb2f539 · t126)
- [ ] **Icônes Deepotus Glyph** : Toutes les icônes du Vectorlab (outils, barre contextuelle, menus détachés, calques, panneaux, dialogues, « ? ») passent à la suite Deepotus Glyph ; Sans contour a sa propre icône, Paramètres de l'appli se distingue de Configuration du document. (PR #284 · commit 1d7ed331 · 9f8a06d7 · e284b254 · icônes G3)
**Vectorlab — persona Vecteur** — accès : Barre des applications → Vectorlab (page /vectorlab/) ; aussi hub Game Assets → onglet Assets 2D → carte Pixel (ouvre le persona Pixel) ; pastille Vecteur

- [ ] **Aimantation aux objets** : Les objets s'aimantent aux bords, centres et écarts réguliers des autres, avec lignes d'aide. — *Affichage → Magnétisme aux objets* (commit 3d70a204 · fe21a719 · lot C)
- [ ] **Arrondir les coins** : Arrondit les coins d'un chemin. — *Vecteur → Arrondir les coins* (commit e540aedb · lot B)
- [ ] **Cadre de texte** : Le texte coule dans une boîte et revient à la ligne seul (gauche, centre, droite, justifié, retrait). — *Outil Cadre de texte ; Apparence + → En cadre* (commit dc187d6a · 4174c3e7 · f6414b27 · lot F/R7)
- [ ] **Coller dans / libérer** : Masque d'écrêtage : coller un objet dans une forme, puis le libérer. — *Apparence + → coller dans / libérer* (commit 8503896c · 4174c3e7 · lot F)
- [ ] **Constructeur de formes (S)** : Combine ou retire des zones de formes qui se chevauchent par clics. — *S ; Entrée pour valider* (commit aa48b32b · e5ab0958 · lot B)
- [ ] **Contour en forme** : Transforme un contour en forme pleine (décalage). — *Apparence → Décaler* (commit aa48b32b · lot B)
- [ ] **Contours multiples** : Plusieurs contours empilés sur un même objet. — *Apparence +* (commit 4174c3e7 · lot F)
- [ ] **Convertir en courbes** : Transforme un texte en chemins, en un seul ou un chemin par glyphe. — *Ctrl+Entrée ; Texte → Convertir en courbes par glyphe* (commit b9733140 · 5a556b1a)
- [ ] **Couleurs globales** : Couleurs nommées partagées : les changer met à jour tous les objets qui les utilisent. — *Apparence +* (commit 8503896c · lot F)
- [ ] **Couteau (X)** : Coupe une forme le long d'un trait. — *X* (commit aa48b32b · lot B)
- [ ] **Crayon (B)** : Dessin à main levée simplifié et lissé, fermé automatiquement si on revient au départ. — *B* (commit 951cfe85 · lot B)
- [ ] **Diviser, joindre, inverser** : Diviser au nœud, relier deux courbes, inverser le sens d'un chemin. — *Vecteur → Diviser au nœud / Relier les courbes / Inverser le sens* (commit e540aedb · lot B)
- [ ] **Dupliquer en puissance** : Répète la dernière duplication avec le même décalage. — *Édition → Dupliquer en puissance…* (commit e05fc883 · lot B)
- [ ] **Dégradé conique** : Couleur qui tourne autour du centre de la forme. — *Apparence + → Conique* (commit 410c7f50 · 4174c3e7 · lot F)
- [ ] **Déposer une police** : Ajouter ses propres polices TTF, OTF, WOFF, WOFF2 à la bibliothèque. — *Menu Typographies → déposer* (commit 885e8cec)
- [ ] **Effets de calque** : Six effets (ombre, lueur…) chaînés et éditables sur un objet. — *Apparence + → effets* (commit 410c7f50 · 4174c3e7 · lot F)
- [ ] **Formes paramétriques (F)** : Polygone, étoile, engrenage, flèche, donut, spirale, réglables par poignées. — *F ; menu Forme (flyout) ; tirer les poignées* (commit 0e1b3fc6 · e5ab0958 · lot B)
- [ ] **Formules dans les champs** : Les champs numériques acceptent des calculs (ex. 100/3). — *Taper une formule dans un champ* (commit e05fc883 · lot B)
- [ ] **Gomme vectorielle (W)** : Efface une partie d'une forme vectorielle. — *W* (commit aa48b32b · lot B)
- [ ] **Grille du document** : Quatre réseaux (carré subdivisé, iso, triangulaire, hexagonal pointe ou plat), tracés et aimantants, avec origine et échelle. — *Document → Grille du document ; G pour l'afficher* (commit b411f7a2 · fe21a719 · lot C)
- [ ] **Grouper, ordre, aligner** : Grouper / dégrouper, ordre de superposition, aligner et distribuer depuis les menus. — *Ctrl+G / Ctrl+Maj+G ; menu Calque ; menu Sélection* (commit 3be776e3 · 3c32bf8f)
- [ ] **Générer le plateau** : Génère automatiquement un plateau de tuiles. — *Panneau Plateau / menu Terrains → générer le plateau* (commit 720f5ce7 · 3c32bf8f · lot C)
- [ ] **Générer une image (IA)** **payant** : Créer une image par un générateur IA et la poser dans le document. — *Fichier → Nouveau traitement d'image (IA)… ; menu Image → génération* (commit 9badd4bf · lot A)
- [ ] **Harmonies de couleurs** : Palettes complémentaire, analogue, triade, tétrade, monochrome à partir d'une couleur. — *Apparence +* (commit 7e6d3457 · lot F)
- [ ] **Inclinaison** : Incline (cisaille) un objet. — *Panneau Transformer* (commit e05fc883 · lot B)
- [ ] **Modes de fusion d'objet** : 16 modes de fusion par objet. — *Apparence +* (commit 410c7f50 · lot F)
- [ ] **Motifs de remplissage** : Hachures, points, damier, grille comme remplissage. — *Apparence + → Motif* (commit 410c7f50 · lot F)
- [ ] **Nœuds multiples au lasso** : Sélectionner plusieurs nœuds pour les déplacer, aligner ou transformer. — *Lasso avec l'outil Nœud* (commit e540aedb · e5ab0958 · lot B)
- [ ] **Opérations booléennes** : Union, Soustraction, Intersection, Division de formes. — *Vecteur → Géométrie* (commit 3be776e3 · menus)
- [ ] **Outil Coin (C)** : Arrondit un coin choisi d'une forme. — *C* (commit e5ab0958 · lot B)
- [ ] **Panneau Bibliothèque (Assets)** : La Bibliothèque unifiée dans le panneau, avec recherche : un clic pose l'image. — *Pile de droite → Bibliothèque (Assets) ; Fenêtre → Stock* (commit fe21a719 · lot C)
- [ ] **Panneau Terrains** : Fiche des terrains (nom, couleur, motif) pour les tuiles de plateau. — *Document → Plateau et terrains* (commit fe21a719 · lot C)
- [ ] **Pinceau de tuiles (K)** : Peint des tuiles du terrain choisi sur la grille. — *K ; terrain dans la barre contextuelle* (commit fe21a719 · lot C)
- [ ] **Pinceau vectoriel (J)** : Trait à profil (plat, fuseau, calligraphie à angle fixe) converti en forme pleine. — *J ; profil et largeur dans la barre contextuelle* (commit 26e848e9 · 4174c3e7 · lot F)
- [ ] **Pivot déplaçable** : Le point de rotation se déplace à la souris. — *Glisser le pivot* (commit e5ab0958 · f54fa609 · lot B)
- [ ] **Planches** : Découpe le document en planches exportables séparément. — *Document → Planches…* (commit 720f5ce7 · fe21a719 · lot C)
- [ ] **Poser une forme au clic** : Un simple clic pose une forme de rayon 40. — *Clic sur le canevas* (commit 1a8134d4)
- [ ] **Poser une image** *(coût variable)* : Insérer une image depuis la Bibliothèque, un fichier, le presse-papiers ou une génération. — *Fichier → Insérer une image (Ctrl+Maj+M) / depuis la Bibliothèque ; menu Image* (commit 9badd4bf · lot A)
- [ ] **Repères de fond perdu et zone sûre** : Repères tracés et aimantants pour l'impression, jamais exportés. — *Document → Marges et fond perdu…* (commit 14fd167a · 9badd4bf · lot A)
- [ ] **Rogner et verrouiller une image** : Rogner une image posée et la verrouiller. — *Menu Image* (commit 9badd4bf · lot A)
- [ ] **Réglages typographiques** : Corps, graisse, interlettrage, interligne, ancre. — *Panneau Texte* (commit b9733140)
- [ ] **Styles d'objet** : Enregistrer l'apparence d'un objet et l'appliquer à d'autres. — *Édition → Créer un style ; Apparence +* (commit aa970e2d · lot F)
- [ ] **Symboles vivants** : Créer un symbole, en poser des instances, le modifier : toutes les instances suivent ; détacher ou supprimer. — *Vecteur → Créer un symbole ; menu Symboles (poser / créer)* (commit aa970e2d · 1a8134d4 · lot F)
- [ ] **Sélecteur de typographies** : Choix visuel parmi les polices fournies, déposées et système. — *Texte → Typographies…* (commit b9733140)
- [ ] **Sélectionner par attribut** : Sélectionne tous les objets partageant une même propriété (couleur, type…). — *Édition → Sélectionner par attribut…* (commit e05fc883 · lot B)
- [ ] **Texte sur chemin** : Le texte suit un chemin, avec décalage le long du tracé. — *Apparence + → Sur le chemin* (commit dc187d6a · 4174c3e7 · lot F)
- [ ] **Vectoriser une image** : Transforme une image en tracés vectoriels (couleurs, lissage, seuil, définition), avec aperçu, en local. — *Vecteur → Traçage d'image… ; menu Image → vectoriser* (commit 26473071 · lot A)
- [ ] **Édition du texte en place** : Le texte s'édite directement sur le canevas, multi-lignes. — *Double-clic sur un texte* (commit b9733140 · 05a5b7ab)
- [ ] **Actions de chemin de la Plume** : Vif, Lisse, Fractionner, Ouvrir, Fermer, Courbe lisse, Relier, Inverser. — *Boutons de la barre contextuelle* (commit 45a2e4a6 · R8)
- [ ] **Barre de style du texte** : Police, corps, graisse, italique, souligné, alignement, interligne, approche, sur le texte sélectionné ou par défaut. — *Barre contextuelle de l'outil Texte* (commit 0c859f63 · R11)
- [ ] **Conversion Intelligent** : Lisse automatiquement les nœuds sélectionnés. — *Barre contextuelle de l'outil Nœud* (commit 4b04f00a · R10)
- [ ] **Copie déplacée** : Glisser une copie de l'objet sélectionné. — *Alt + glisser* (commit 4b04f00a · R10)
- [ ] **Double-clic vers l'outil Nœud** : Un double-clic sur une courbe passe à l'outil Nœud sans ajouter de nœud. — *Double-clic sur une courbe* (commit 4b04f00a · R10)
- [ ] **Dégradé (outil)** : Pose un dégradé de la couleur de fond vers le blanc au glisser. — *Famille Dégradé ; glisser sur l'objet* (commit f6414b27 · R7)
- [ ] **Déplacement contraint** : Déplacer une sélection en restant sur un axe. — *Maj pendant le glisser* (commit 4b04f00a · R10)
- [ ] **Gestes de la Plume** : Tangente contrainte à 45°, segment droit, tracé sans magnétisme. — *Maj = 45° ; clic droit = droite ; Alt = sans magnétisme* (commit 45a2e4a6 · R8)
- [ ] **Illustration IA** **payant** : Outil de la famille IA pour produire une illustration par IA. — *Famille IA de la colonne d'outils* (commit 3ba22036 · R2)
- [ ] **Indicateur de débordement** : Un indicateur rouge signale qu'un cadre de texte déborde. (commit 0c859f63 · R11)
- [ ] **Insérer / supprimer un nœud** : Ajouter un nœud au point cliqué d'un segment ; supprimer en gardant la courbe lisse. — *Double-clic sur un segment ; Suppr* (commit 595caa20 · R9)
- [ ] **Magnétisme aux nœuds** : Aimantation aux autres nœuds, réglable à part. — *Barre contextuelle* (commit 4b04f00a · R10)
- [ ] **Main (H) et Loupe (Z)** : Déplacer la vue ; zoomer au clic, dézoomer avec Alt, cadrer une zone. — *H / Z ; Alt+clic = dézoom* (commit f6414b27 · R7)
- [ ] **Modes de la Plume** : Quatre modes : Plume, Intelligent (lissage automatique), Polygone, Ligne. — *Barre contextuelle de la Plume* (commit 45a2e4a6 · R8)
- [ ] **Outil Déplacer / Sélection (V)** : Sélection à la Affinity : le cadre ne prend que les objets entièrement inclus, survol en boîte bleue, X · Y · L · H dans la barre contextuelle. — *V ; Alt pendant le cadre = prendre les objets touchés* (commit 4b04f00a · R10)
- [ ] **Outil Mesure (M)** : Mesure une distance sur le canevas. — *M* (commit 3ba22036 · R2)
- [ ] **Outil Nœud (N) de classe Affinity** : Poignées tirables, segment déformable au glisser, ancre sélectionnée en bleu, alignements et actions dans la barre contextuelle. — *N ; Alt / Maj sur une poignée* (commit 595caa20 · R9)
- [ ] **Outil Texte (T) de classe Affinity** : Glisser = texte au corps de la hauteur tirée ; clic sur une courbe = texte sur ce chemin. — *T* (commit 0c859f63 · R11)
- [ ] **Outil Transparence (Y)** : Dégradé de transparence posé au glisser. — *Y* (commit f6414b27 · R7)
- [ ] **Parcourir les objets au clavier** : Passer d'un objet au suivant ou au précédent. — *Tab / Maj+Tab* (commit 0c859f63 · R11)
- [ ] **Plan de travail** : Outil pour définir des plans de travail (planches) dans le document. — *Famille Plan de travail* (commit f6414b27 · R7)
- [ ] **Plume (P) de classe Affinity** : Tracé de courbes : clic = nœud vif, glisser = nœud lisse, élastique courbe, fermeture sur le premier nœud (rouge), glyphes carrés/ronds. — *P ; Entrée, Échap ou double-clic pour finir ; Retour arrière retire le dernier nœud* (commit 45a2e4a6 · R8)
- [ ] **Prolonger une courbe ouverte** : Reprendre un chemin ouvert par sa fin ou son début avec la Plume. — *Cliquer une extrémité avec la Plume* (commit 45a2e4a6 · R8)
- [ ] **Recadrer** : Rogner une image au glisser ; double-clic retire le rognage. — *Outil Recadrer (famille Image)* (commit f6414b27 · R7)
- [ ] **Rectangle (R), Ellipse (E), Ligne (L)** : Formes de base, regroupées dans la famille Formes. — *R / E / L* (commit 3ba22036 · R2)
- [ ] **Redimensionner depuis le centre** : Redimensionner autour du centre de l'objet. — *Ctrl en tirant une poignée* (commit 4b04f00a · R10)
- [ ] **Sélection auto** : Option : décochée, tout glisser déplace la sélection courante au lieu d'en prendre une nouvelle. — *Case « Sélection auto » de la barre contextuelle* (commit 0c859f63 · R11)
- [ ] **Sélectionner un enfant de groupe** : Atteindre un objet à l'intérieur d'un groupe. — *Ctrl+clic* (commit 0c859f63 · R11)
- [ ] **Transformer plusieurs nœuds** : Poignées d'échelle et de rotation pour une sélection de nœuds. — *Maj = proportions ; Maj en rotation = pas de 15°* (commit 4b04f00a · R10)
- [ ] **Nœuds qui suivent le curseur** : Nœuds, poignées et segments suivent la souris en direct pendant le glisser. (commit 82054dfd · R12)
- [ ] **Pipette (I) de classe Affinity** : Prélève une couleur avec loupe, rayon et source réglables, puis l'applique au fond, au contour ou à la couleur courante. — *I ; Ctrl = prélever tout le style* (commit 4d83c9e7 · e17e288d)
- [ ] **Motif des terrains** : Un terrain peut prendre un motif (hachures, points, damier, grille) dessiné sur ses tuiles ; une saisie inconnue est redemandée. — *Panneau Terrains → retoucher un terrain* (PR #249 · commit f813dfa4 · t122)
- [ ] **Contour vivant** : Un contour décalé reste lié à sa source et se recalcule quand on la modifie ; « détacher » coupe le lien. — *Apparence + → détacher* (PR #252 · commit 229cd3df · t123)
- [ ] **Effets sur les images** : Les effets s'appliquent désormais aussi aux images posées. — *Apparence + sur une image* (PR #252 · commit 229cd3df · t123)
- [ ] **Poignées du cadre de texte** : Redimensionner un cadre recompose le texte sans l'étirer. — *Tirer les poignées du cadre* (PR #252 · commit 04ce049d · t123)
- [ ] **Symbole édité en place** : Modifier un symbole directement sur une instance, puis Terminer (toutes suivent) ou Abandonner. — *Double-clic sur une instance ou menu Symboles ; Terminer par le bandeau, le menu ou Échap à sélection vide* (PR #252 · commit 04ce049d · t123)
- [ ] **Texte sur chemin suiveur** : Le texte reste lié à son chemin et suit chaque modification ; « détacher » coupe le lien. (PR #252 · commit 229cd3df · t123)
**Vectorlab — liens avec les autres écrans** — accès : Card Forge, Bibliothèque / Photolab (Envoyer vers), Templates, hub Game Assets

- [ ] **Éditer cette face dans le Vectorlab** : Depuis le Card Forge, la face rendue s'ouvre dans le Vectorlab au format physique du jeu, avec repères et calque verrouillé. — *Card Forge → « Éditer cette face dans le Vectorlab »* (commit 651482d5 · lot A)
- [ ] **Ouvrir un gabarit dans le Vectorlab** : Un gabarit de Templates s'ouvre en document Vectorlab éditable dans un onglet. — *Templates → éditeur → « Ouvrir dans le Vectorlab »* (PR #150 · commit 5856f86a · tâche #76)
- [ ] **Carte Pixel du hub** : La carte Pixel de l'onglet Assets 2D du hub Game Assets ouvre le Vectorlab directement en persona Pixel. — *Game Assets → Assets 2D → Pixel* (PR #255 · commit 3fff9376 · t125)
- [ ] **Envoyer vers Vectorlab** : Depuis la Bibliothèque ou le Photolab, une image ouvre un document Vectorlab neuf qui la contient. — *Envoyer vers… → Vectorlab ; Photolab : Fichier → Envoyer vers…* (PR #266 · commit eeee9ed1 · t139)

### Pixel art, export, cartes et objets 3D (`vectorlab-pixel`, lot t177, reprend : nouveau) — 81 manques

**Vectorlab — persona Pixel** — accès : Barre des applications → Vectorlab (page /vectorlab/) ; aussi hub Game Assets → onglet Assets 2D → carte Pixel (ouvre le persona Pixel) ; pastille Pixel

- [ ] **Ajustements** : Niveaux, courbes, TSL, noir et blanc, seuil, flou en boîte. — *Pixel → Réglages et filtres…* (commit c5d9244e · lot E)
- [ ] **Annuler les pixels** : Chaque retouche est journalisée et peut être annulée (10 étapes), en restaurant la taille d'origine. — *Bouton Annuler pixels* (commit 9a507b5d · ff186096 · lot E/lot 2)
- [ ] **Envoyer vers Tilelab / Spritelab** : Envoie le pixel-art au Tilelab ou au Spritelab. — *Pixel → Pixel-art vers Tilelab… ; panneau Pixel-art* (commit d0f4fb43 · lot E)
- [ ] **Feuille PNG+JSON et bande** : Exporte les cadres en feuille de sprites avec index JSON ou en bande. — *Panneau Pixel-art* (commit d0f4fb43 · lot E)
- [ ] **Ligne pixel (I) et Rectangle pixel (R)** : Lignes et rectangles pixel-parfaits. — *I / R* (commit d0f4fb43 · lot E)
- [ ] **Masque de calque** : Masquer une partie d'une image sans l'effacer. — *Panneau Pixel* (commit d0f4fb43 · lot E)
- [ ] **Mode Pixel-art** : Taille de tuile, symétrie, palette, quantification, grille de pixels en surimpression. — *Panneau Pixel-art* (commit d0f4fb43 · 6263384d · lot E)
- [ ] **Palette et quantification** : Calcule une palette (median cut) et réduit l'image à ses couleurs. — *Panneau Pixel-art* (commit 12a97d3a · lot E)
- [ ] **Persona Pixel** : Retouche raster des images du document, outils et panneaux dédiés. — *Pastille Pixel ou Affichage → Persona Pixel ; Pixel → Éditer les pixels* (commit d0f4fb43 · lot E)
- [ ] **Pinceau (B) et Gomme (E)** : Peindre ou effacer des pixels avec rayon et dureté. — *B / E ; rayon et dureté dans la barre contextuelle* (commit c5d9244e · d0f4fb43 · lot E)
- [ ] **Pixeliser une image ou une sélection vectorielle** : Ramène une image (ou une sélection vectorielle) à de gros pixels à la taille de tuile. — *Panneau Pixel-art → Pixeliser* (commit d0f4fb43 · lot E)
- [ ] **Pot de peinture (G)** : Remplit une zone contiguë ou toutes les pixels de même couleur (global), avec tolérance. — *G ; tolérance et Global dans la barre* (commit c5d9244e · lot E)
- [ ] **Raccord 3×3** : Aperçu de la tuile répétée en 3×3 avec score de raccord. — *Panneau Pixel-art* (commit 12a97d3a · lot E)
- [ ] **Sélection en vecteur** : Convertit une sélection de pixels en forme vectorielle. — *Panneau Pixel* (commit d0f4fb43 · lot E)
- [ ] **Sélections de pixels** : Rectangle (M), Lasso (L), Baguette magique (W), par couleur ; croître, contracter, inverser. — *M / L / W ; Pixel → Inverser (Ctrl+I), Croître, Contracter, Sélectionner par couleur* (commit c5d9244e · lot E)
- [ ] **Tampon de clonage (C)** : Recopie une zone de l'image ailleurs. — *C* (commit c5d9244e · lot E)
- [ ] **Panneau Histogramme** : Histogramme des quatre canaux et statistiques, calculés sur les pixels édités. — *Premier onglet du groupe 1 du persona Pixel* (commit 5716f970 · db68ed1a · R6)
- [ ] **Retouche Flou / Éclaircir / Assombrir** : Pinceaux de retouche : flouter, éclaircir (densité −), assombrir (densité +). — *Famille Retouche* (commit f6414b27 · R7)
- [ ] **Accentuer** : Renforce le contraste du pixel-art. — *Panneau Pixel → Accentuer* (commit d5192dd5 · lot 5)
- [ ] **Contour sombre** : Entoure le dessin d'un trait sombre pour le détacher du fond. — *Panneau Pixel → Contour sombre* (commit d5192dd5 · lot 5)
- [ ] **Couleur secondaire** : Peindre avec la couleur secondaire ; échanger primaire et secondaire. — *Clic droit = secondaire ; X = échanger* (commit d22e1eb0 · lot 2)
- [ ] **Crayon pixel (K)** : Crayon d'un pixel, en mode pixel-parfait (sans doubles pixels dans les diagonales). — *K ; case Pixel-parfait dans la barre* (commit e0d6cef6 · d22e1eb0 · lot 2)
- [ ] **Créer le calque pixel** : Pose un calque transparent sur le modèle pour dessiner case par case. — *Bouton Créer le calque pixel* (commit e12f068d · lot 3)
- [ ] **Désigner comme modèle** : Une image devient modèle : atténuée, verrouillée, avec grille de cellules en aperçu. — *Panneau Pixel → Désigner comme modèle* (commit e12f068d · 9792ac12 · lot 3)
- [ ] **Export PNG ×1 à ×16** : Exporte le pixel-art agrandi sans flou, de ×1 à ×16. — *Panneau Pixel → export PNG* (commit d5192dd5 · lot 5)
- [ ] **Forme du pinceau** : Pinceau rond ou carré. — *Champ Forme de la barre contextuelle* (commit d22e1eb0 · 989f52b2 · lot 2)
- [ ] **Grille de cellules liée** : Taille de cellule et cible liées pour calquer le modèle case par case. — *Panneau Pixel* (commit aa59ffb0 · e12f068d · lot 3)
- [ ] **Grille sous la rotation du modèle** : La grille d'aperçu suit la rotation du modèle. (commit 3e2f6b09 · lot 5)
- [ ] **Ligne de temps (cadres)** : Vignettes des cadres, lecture, boucle, FPS ; dupliquer, cadre vide, supprimer. — *Entrée = lecture* (commit 81435114 · lot 2)
- [ ] **Palettes unifiées** : Les mêmes palettes que Spritelab et Tilelab (dont Grayscale 16, Handheld 4). — *Panneau Pixel-art → palette* (commit bd10bde0 · f8e731b9 · lots 4-5)
- [ ] **Pelure d'oignon rouge / bleue** : Montre le cadre précédent (rouge) et suivant (bleu). — *Ligne de temps* (commit 81435114 · 1a556755 · lot 2)
- [ ] **Pipette depuis le modèle** : Prélève la couleur d'une cellule du modèle : exacte, moyenne ou dominante. — *Champ Pipette de la barre contextuelle* (commit 04e96219 · e12f068d · lot 3)
- [ ] **Pipette rapide** : Prélève une couleur sans changer d'outil. — *Alt+clic* (commit d22e1eb0 · lot 2)
- [ ] **Plusieurs modèles par document** : Plusieurs paires modèle/calque dans un même document, choisies dans une liste. — *Liste des modèles ; bouton + modèle* (commit 3e2f6b09 · lot 5)
- [ ] **Rasteriser cette image** : Pixelise une image avec palette et tramage (ordonné ou Floyd-Steinberg). — *Bouton Rasteriser cette image* (commit 7eaa4c46 · e54535f8 · lot 2)
- [ ] **Remplir depuis le modèle** : Remplit le calque pixel avec les couleurs du modèle, cellule par cellule. — *Panneau Pixel* (commit aa59ffb0 · e12f068d · lot 3)
- [ ] **Segment droit** : Trace une ligne droite depuis le dernier point peint. — *Maj+clic* (commit d22e1eb0 · lot 2)
- [ ] **Tuile iso 2:1** : Tuile en losange isométrique : peinture limitée au losange de chaque tuile, pavage et score. — *Panneau Pixel-art → tuile iso* (commit 7eaa4c46 · 6a823db7 · lot 2)
- [ ] **Échantillons et couleurs utilisées** : Liste des couleurs utilisées dans le dessin, réutilisables d'un clic. — *Panneau Pixel* (commit e12f068d · lot 3)
- [ ] **Ctrl+Z / Ctrl+Y des pixels** : L'annulation générale du document défait et refait aussi les retouches de pixels. — *Ctrl+Z / Ctrl+Y* (PR #254 · commit ea716f80 · t124)
- [ ] **Raccord iso par tuile** : Le raccord est mesuré sur la tuile sous le curseur. (PR #255 · commit 3fff9376 · t125)
- [ ] **Retouche d'une image tournée** : On peut peindre sur une image tournée : le pointeur suit la rotation. (PR #254 · commit ea716f80 · t124)
- [ ] **Symétrie iso** : Symétrie le long des bords du losange isométrique. — *Panneau Pixel-art → symétrie* (PR #255 · commit 3fff9376 · t125)
**Vectorlab — Export** — accès : Vectorlab → Fichier → Exporter… ou onglet Exporter de la pile de droite

- [ ] **Export DXF** : Export DXF en millimètres pour la découpe ; tranches sans découpe sautées. — *Format DXF du panneau Export +* (commit 8cb5e82c · 8cfece49 · lot G)
- [ ] **Export en lot** : Exporte toutes les tranches × résolutions × formats d'un coup. — *Bouton d'export lot* (commit 7e3e72c0 · lot G)
- [ ] **Export par planche** : Chaque planche s'exporte séparément. — *Panneau Planches* (commit fe21a719 · lot C)
- [ ] **Formats d'export** : PNG, JPEG, WebP, SVG, PDF, DXF. — *Panneau Export +* (commit 7e3e72c0 · lot G)
- [ ] **Modes de tranche** : Cinq modes : document entier, chaque planche, chaque calque visible, chaque objet sélectionné, tranches dessinées ; effacer les tranches. — *Menu Tranches ; barre contextuelle* (commit 7e3e72c0 · 3c32bf8f · lot G)
- [ ] **Outil Tranche** : Dessiner des tranches d'export sur le canevas, partagé entre personas. — *Famille Tranche ; Échap pour quitter* (commit 7e3e72c0 · lot G)
- [ ] **PDF image (ancien mode)** : Option PDF en une image par page, comme avant. — *Panneau Export → réglage PDF « image »* (commit a6c57d39 · 4d68c5fd · lot G/t121)
- [ ] **Plan de nommage** : Noms de fichiers construits automatiquement (tranche, résolution). — *Panneau Export +* (commit 4dc4964c · lot G)
- [ ] **Préréglages d'impression** : Fond perdu, traits de coupe, repères de repérage, dpi et qualité. — *Panneau Export +* (commit 7e3e72c0 · lot G)
- [ ] **Résolutions multiples** : Exporter chaque tranche en plusieurs résolutions (@1x, @2x…). — *Panneau Export +* (commit 4dc4964c · 7e3e72c0 · lot G)
- [ ] **SVG avec images incorporées** : L'export SVG embarque les images posées et convertit les textes en chemins. — *Fichier → Exporter SVG* (commit 9badd4bf · b9733140 · lot A)
- [ ] **PNG 2×** : Export rapide en PNG double résolution. — *Fichier → Exporter PNG 2×* (commit fbada079 · menus)
- [ ] **Vers la Bible** : Envoie le visuel vers la Bible. — *Fichier → Vers la Bible…* (commit fbada079 · menus)
- [ ] **DXF : textes et symboles** : Le DXF contient désormais les textes en contours de glyphes, les instances de symbole et les transformations des groupes. (PR #254 · commit ea716f80 · t124)
- [ ] **Dégradés et motifs dans le PDF** : Dégradés linéaires/radiaux et motifs (dont ceux des terrains) restent vectoriels dans le PDF ; ce qui ne peut pas l'être est rasterisé en le disant. (PR #251 · commit 293e866f · t121)
- [ ] **Onglet Exporter** : L'export est un onglet commun aux deux personas ; ses panneaux Export et Export + sont de nouveau visibles (ils étaient masqués depuis le 18/09). — *Fichier → Exporter… (Ctrl+Alt+Maj+S) ou Fenêtre → Exporter* (PR #251 · commit 4d68c5fd · t121)
- [ ] **PDF vectoriel** : Le PDF est désormais vectoriel par défaut : textes en contours de leur police, page à la taille physique, traits de coupe en vecteurs ; un message compte vecteurs et parties rasterisées avec leurs raisons. — *Panneau Export → réglage PDF « vectoriel » (défaut) ou « image »* (PR #251 · commit 7cca9925 · 4d68c5fd · t121)
**Vectorlab — Impression 3D** — accès : Vectorlab → Fichier → Impression 3D… (ou Texte → Logo 3D…)

- [ ] **Aperçu 3D** : Aperçu du modèle (GLB) dans une visionneuse 3D, en couleurs de pièces. (commit d9927797 · 5ee607b8 · lots D/R12)
- [ ] **Dialogue Impression 3D** : Transforme le dessin en pièces imprimables avec aperçu 3D, en modes Calques, Tuiles, Logo, Relief ou Pixel-art. — *Fichier → Impression 3D… ; Texte → Logo 3D…* (commit d9927797 · lot D)
- [ ] **Mode Logo : biseau et évidement** : Un logo extrudé avec bords biseautés ou évidé à mur minimal. — *Dialogue Impression 3D → Logo* (commit d9927797 · 8bb6daef · lot D)
- [ ] **Mode Relief** : Plaque fermée à partir du relief de la carte : exagération, gravure du tracé, découpe en dalles numérotées. — *Dialogue Impression 3D → Relief* (commit 8935603f · e63df9d5 · lot H)
- [ ] **Mode Tuiles** : Tuiles de plateau en 3D avec socle et relief. — *Dialogue Impression 3D → Tuiles* (commit d9927797 · lot D)
- [ ] **Texte vectorisé pour la 3D** : Le texte est converti en chemins depuis l'Apparence pour être imprimé. (commit d9927797 · 5a556b1a · lot D)
- [ ] **Un STL ou un lot par tuile** : Exporter un STL unique ou un lot : un STL par pièce, plateau.3mf et nomenclature.csv. — *Bouton Lot par tuile / dalle* (commit 8665c098 · d9927797 · lot D)
- [ ] **Couleur des pièces** : Chaque pièce garde sa couleur dans l'aperçu, le GLB et le 3MF (un objet coloré par pièce). (commit cef2d9a4 · fc91736a · 5ee607b8 · R12)
- [ ] **Contours vrais des pièces pixel-art** : Les pièces de pixel-art gardent leurs trous et n'ont plus de faces internes. (commit 49f87644 · lot 5)
- [ ] **Dépouille des flancs** : Incline les flancs d'un logo (±45°) pour faciliter le démoulage. — *Réglage Dépouille (°) + curseur* (commit 708d7428 · 266b2483 · R12)
- [ ] **Mode Pixel-art (3D)** : Une pièce colorée et une hauteur par couleur, dans une table modifiable. — *Dialogue Impression 3D → Pixel-art* (commit a35ef939 · lot 3)
- [ ] **Tenons des dalles** : Dalles de relief avec logements sous le socle et clés séparées (jeu 0,2 mm) pour les assembler. — *Mode Relief en dalles* (PR #254 · commit ea716f80 · t124)
**Vectorlab — Cartes réelles** — accès : Vectorlab → Document → Carte réelle… ou Fichier → Importer un GPX…

- [ ] **Courbes de niveau** : Trace des courbes de niveau en chemins vectoriels, au pas choisi. — *Panneau Carte → Courbes* (commit 8935603f · lot H)
- [ ] **Données sans valeur gérées** : Les zones sans donnée d'altitude prennent le plancher valide au lieu de creux aberrants. (commit abb2de88 · lot H)
- [ ] **Fond OpenStreetMap** : Pose un fond de carte OSM assemblé et rogné, avec attribution. — *Panneau Carte* (commit 6958aef9 · 8935603f · lot H)
- [ ] **Importer un GPX** : Un tracé GPX est importé en trois calques, à l'échelle vraie. — *Fichier → Importer un GPX…* (commit c25955cb · 8935603f · lot H)
- [ ] **Panneau Carte réelle** : Créer une carte à partir de données réelles, sans clé ni coût. — *Document → Carte réelle… ; onglet Carte* (commit 8935603f · lot H)
- [ ] **Relief ombré** : Pose le relief (altitudes Terrarium) en ombrage. — *Panneau Carte* (commit 8935603f · lot H)
- [ ] **Tuiles par palier de relief** : Découpe la carte en tuiles hexagonales colorées selon l'altitude. — *Panneau Carte → Découper* (commit 8935603f · lot H)
- [ ] **Profil altimétrique GPX** : L'altitude enregistrée du GPX est gardée : profil de chaque trace avec longueur, D+ / D−, altitudes min et max. — *Panneau Carte* (PR #254 · commit ea716f80 · t124)
- [ ] **Ruban GPX en relief** : Le tracé GPX devient un ruban posé à l'altitude enregistrée. — *Panneau Carte / Impression 3D* (PR #254 · commit ea716f80 · t124)

## Jeu et 3D

### Fabriquer des assets de jeu (`assets2d`, lot t178, reprend : c17) — 9 manques

À corriger dans l'ancien texte :

- [ ] Badge « nouveau »
- [ ] Glyphes ▶ ★ ✎ 🗑 comme icônes de boutons
- [ ] DÉFAUT FR : 14 apostrophes doublées (« s''affiche », « d''abord », « L''onglet »…), absentes de l'EN
- [ ] 3D Studio, rig Meshy (T104), LOD/textures (T105), vues avant le tir (T106), banc GPU/photos (T107), Plateau 3D (t127), lanceur Assets 2D (t125), Sprites (T108-T112, t111), Tuiles (#113-#116), Matières (T095-T098) non décrits

**Game Assets — onglet Assets 2D et palettes partagées** — accès : Barre latérale → Game Assets → onglet Assets 2D ; palettes dans les réglages Pixel-art du Sprite Lab, du Tile Lab et du persona Pixel du Vectorlab

- [ ] **Palette Grayscale 16** : Pixelise en 16 niveaux de gris. — *Pixel-art (9b) → Couleurs → Grayscale 16* (commit f8e731b9 · lot 5)
- [ ] **Palette Handheld 4** : Pixelise en 4 tons façon console portable. — *Pixel-art (9b) → Couleurs → Handheld 4* (commit f8e731b9 · lot 5)
- [ ] **Palettes unifiées** : Une seule liste de palettes nommées (PICO-8, Game Boy, NES, Sweetie 16, 1-bit…) partagée par le Sprite Lab, le Tile Lab et le persona Pixel. — *Réglage « Couleurs » de Pixel-art (9b) ; « Préréglage » du persona Pixel* (commit bd10bde0 · lot 4)
- [ ] **Carte Card Forge** : Ouvre le Card Forge depuis le hub. — *Assets 2D → carte Card Forge* (PR #255 · t125)
- [ ] **Carte Pixel** : Ouvre le Vectorlab directement en persona Pixel. — *Assets 2D → carte Pixel* (PR #255 · t125)
- [ ] **Carte Sprite Lab** : Ouvre le Sprite Lab depuis le hub. — *Assets 2D → carte Sprite Lab* (PR #255 · t125)
- [ ] **Carte Tile Lab** : Ouvre le Tile Lab depuis le hub. — *Assets 2D → carte Tile Lab* (PR #255 · t125)
- [ ] **Onglet Assets 2D** : Nouvel onglet du hub Game Assets qui rassemble les outils 2D en quatre cartes-lanceurs. — *Game Assets → onglet « Assets 2D »* (PR #255 · commit 3fff9376 · t125)
- [ ] **Icônes Deepotus Glyph dans les labs 2D** : Le Sprite Lab et le Tile Lab passent aux icônes Deepotus Glyph (une icône par fonction) ; la loupe se pose dans les champs de recherche, les boutons à icône seule sont annoncés aux lecteurs d'écran. (PR #282 · commit d7bf9db3 · icônes G5)

### Animer des sprites (Sprite Lab) (`spritelab`, lot t178, reprend : nouveau) — 58 manques

**Sprite Lab** — accès : Barre latérale → Game Assets → onglet Assets 2D → carte Sprite Lab (ou sous-onglet Sprites) ; page /spritelab/

- [ ] **Aligner gauche / droite** : Recale seulement le centre horizontal des frames. — *Section Alignement → « Gauche / droite »* (commit 33fd28a5 · lot 1 Feuille)
- [ ] **Aligner les pieds** : Pose le bas de chaque personnage à la même hauteur, comme sur un même sol. — *Section Alignement → « Pieds » (fiche d'aide animée disponible)* (commit 33fd28a5 · lot 1 Feuille)
- [ ] **Aligner sur les deux axes** : Recale chaque frame sur la première frame sélectionnée, centre horizontal et pieds, sans sortir de la case. — *Section Alignement → « Les deux axes »* (commit 33fd28a5 · lot 1 Feuille)
- [ ] **Auto-détecter la grille** : Compte tout seul les colonnes, lignes et cases occupées de la planche à partir de la transparence. — *Onglet Feuille → bouton « Auto-détecter »* (commits 67cb2b1b, 08c283c2 · lot 1 Feuille)
- [ ] **Copier le JSON (manifest v2)** : Copie dans le presse-papiers le manifest v2 : grille, frames, décalages, fps et sections. — *Feuille → Export → « Copier le JSON »* (commit 012c3bdb · lot 1 Feuille)
- [ ] **Décaler la frame courante au pixel** : Pousse la frame courante d'un pixel vers le haut, le bas, la gauche ou la droite. — *« Frame courante : » → quatre flèches 1 px* (commit 08c283c2 · lot 1 Feuille)
- [ ] **Déplacer le sprite au clavier** : Fait marcher le sprite dans la scène de la préviz. — *Touches W A S D ou flèches* (commit 596c16a0 · lot 5 Playground)
- [ ] **Fonds de scène du Playground** : Montre le sprite animé devant des décors Ciel, Extérieur, Donjon ou Cave, en plus des fonds unis. — *Préviz → menu « Fond de la préviz »* (commit 596c16a0 · lot 5 Playground)
- [ ] **Grille manuelle colonnes × lignes** : Impose un nombre de colonnes et de lignes quand la détection ne convient pas. — *Champs « Grille _ × _ » puis bouton Appliquer* (commit 08c283c2 · lot 1 Feuille)
- [ ] **Lecture / pause au clavier** : Lance ou arrête l'animation de la préviz. — *Touche Espace, ou bouton Lecture / pause* (commit 596c16a0 · lot 5 Playground)
- [ ] **Miroir gauche / droite** : Retourne le personnage pour le faire regarder de l'autre côté dans la préviz. — *Préviz → bouton ⇋ « Miroir gauche / droite (Invert L/R) » (fiche d'aide animée)* (commit 596c16a0 · lot 5 Playground)
- [ ] **Onglet Feuille** : Ouvre une planche déjà faite (IA, autre outil, dessin perso) pour la découper, l'aligner et l'exporter, tout en local et sans crédit. — *Colonne source → onglet Feuille ; choisir une planche de la Library (champ « Filtrer les planches de la Library… ») ou « Ouvrir un PNG de mon PC »* (commit 08c283c2 · lot 1 Feuille)
- [ ] **Planche alignée PNG** : Télécharge la planche recomposée avec les alignements appliqués. — *Feuille → Export → « Planche alignée »* (commit 012c3bdb · lot 1 Feuille)
- [ ] **Planche alignée vers la Library** : Sauve la planche alignée dans la Bibliothèque (préfixe sprites_feuille_), d'où « Envoyer vers » le Vectorlab. — *Feuille → Export → « Sheet » (vers la Library)* (commit 08c283c2 · lot 1 Feuille)
- [ ] **Remettre les décalages** : Retire tous les décalages d'alignement appliqués. — *Section Alignement → « Remettre »* (commit 08c283c2 · lot 1 Feuille)
- [ ] **Sections nommées** : Range des plages de frames sous un nom (marche, saut…) avec un mode de lecture boucle, ping-pong ou inversé. — *Section Sections → nom + mode → « depuis la sélection »* (commit 012c3bdb · lot 1 Feuille)
- [ ] **Sélection au glisser** : Choisit les cases à garder en peignant la sélection sur la planche. — *Glisser peint la sélection · Ctrl ajoute / retire · Maj étend depuis la dernière case* (commit 08c283c2 · lot 1 Feuille)
- [ ] **Toutes / Aucune** : Sélectionne toutes les cases occupées ou vide la sélection d'un clic. — *Boutons « Toutes » et « Aucune » sous la grille (compteur n/N)* (commit 08c283c2 · lot 1 Feuille)
- [ ] **Télécharger le JSON** : Télécharge le manifest JSON de la planche. — *Feuille → Export → « JSON »* (commit 08c283c2 · lot 1 Feuille)
- [ ] **Une sur N** : Ne garde qu'une case sur 1, 2, 3 ou 4 pour alléger une animation. — *Boutons « Une sur 1 / 2 / 3 / 4 »* (commit 08c283c2 · lot 1 Feuille)
- [ ] **Vitesse de lecture** : Joue l'animation à demi-vitesse, normale ou double. — *Préviz → menu Vitesse 0,5× / 1× / 2×* (commit 596c16a0 · lot 5 Playground)
- [ ] **4 directions (planche)** : Découpe les vues sud, ouest, est et nord de la planche du personnage et en fait une feuille de 4 directions taguées. — *Onglet Bible → bouton « 4 directions (planche) »* (PR #237, #242 · t111)
- [ ] **8 directions (modèle 3D)** : Rend le modèle 3D du personnage sous 8 angles et en fait une feuille de 8 directions. — *Onglet Bible → bouton « 8 directions (modèle 3D) »* (PR #237, #242 · t111)
- [ ] **Cellule native (sans agrandissement)** : Pose chaque frame à sa vraie taille, sans redimensionner ; la cellule vaut la plus grande frame (1024 px au plus). — *Réglage Cellule → « native (sans agrandissement) » ; au-delà de 1024 px un message dit de pixeliser ou de choisir 128/256/512* (PR #228 · commit c96a01ff · T108)
- [ ] **Changer de frame (hitboxes)** : Passe à la frame précédente ou suivante pour dessiner ses hitboxes. — *Panneau Hitboxes → flèches Frame précédente / suivante* (PR #238 · T112)
- [ ] **Contour** : Entoure le sprite d'un trait de l'épaisseur et de la couleur choisies, en pixels natifs. — *Post-traitement → Contour (épaisseur, 0 = aucun) + couleur (fiche d'aide animée)* (PR #236 · commit cb833003 · T110)
- [ ] **Copier / coller les hitboxes entre frames** : Recopie les rectangles d'une frame sur une autre. — *Boutons Copier / Coller ou Ctrl+C / Ctrl+V* (PR #238 · T112)
- [ ] **Devis avant le tir** : Affiche le coût estimé (images × tarif du générateur par défaut) avant de générer. — *Onglet Prompt → coût à côté de « Générer les images »* (PR #242 · t111)
- [ ] **Durée par image** : Règle la durée de chaque image ; elle vaut pour le GIF d'aperçu, le manifeste et les exports moteur. — *Section Animation → champ « Durée par image » (ms)* (PR #236 · commit cb833003 · T110)
- [ ] **Effacer une hitbox** : Supprime le rectangle choisi. — *Bouton « Effacer » ou touche Suppr* (PR #238 · T112)
- [ ] **Export Aseprite .ase** : Télécharge un fichier Aseprite : un calque, une image par frame et les tags. — *Préviz → bouton « Aseprite .ase »* (PR #229 · commit 837c734e · T109)
- [ ] **Export Atlas JSON** : Télécharge un atlas JSON Hash façon TexturePacker, lu par Phaser et PixiJS. — *Préviz → bouton « Atlas JSON »* (PR #229 · commit 837c734e · T109)
- [ ] **Export Godot .tres** : Télécharge une ressource Godot 4 SpriteFrames : une AtlasTexture par image et une animation par tag. — *Préviz → bouton « Godot .tres » (à poser avec le Sheet PNG)* (PR #229 · commit 837c734e · T109)
- [ ] **Export Paper2D** : Télécharge une feuille Unreal Paper2D dont l'importateur crée texture, sprites et flipbook. — *Préviz → bouton « Paper2D »* (PR #229 · commit 837c734e · T109)
- [ ] **Export Spine JSON** : Télécharge le squelette Spine JSON ; les PNG des pièces sont dans le ZIP (dossier spine/), les tags y deviennent des animations vides. — *Panneau Squelette Spine → « Spine JSON »* (PR #243 · commit 9a953bdb · t111)
- [ ] **Exports moteur dans le ZIP** : Le ZIP (frames + pack Unity) emporte aussi les exports Godot, atlas, Aseprite et Paper2D ; la texture téléchargée seule porte le même nom que le Sheet PNG. — *Préviz → « ZIP (frames + pack Unity) » ; boutons masqués pour une feuille faite avant le 06/10 (la régénérer)* (PR #229 · commit 837c734e · T109)
- [ ] **Générer les images** **payant** : Génère les images avec le générateur par défaut des Réglages, puis les détoure en clé chroma locale et les pose comme source. — *Onglet Prompt → bouton « Générer les images »* (PR #242 · commit 677f09a3 · t111)
- [ ] **Hitboxes enregistrées et exportées** : Les hitboxes s'enregistrent toutes seules, suivent leur frame quand on réordonne, et partent dans l'atlas JSON et le Paper2D. (PR #238 · commit 7fdb07e5 · T112)
- [ ] **Inspecteur de hitbox** : Un clic choisit un rectangle et permet d'en régler x, y, largeur, hauteur et type. — *Clic sur le rectangle → bloc « Rectangle choisi »* (PR #238 · T112)
- [ ] **Lisser les bords** : Fait disparaître les dents d'un pixel sur la silhouette. — *Post-traitement → case « Lisser les bords »* (PR #236 · commit cb833003 · T110)
- [ ] **Nettoyer les pixels orphelins** : Retire les pixels isolés et bouche les trous d'un pixel. — *Post-traitement → case « Nettoyer les pixels orphelins »* (PR #236 · commit cb833003 · T110)
- [ ] **Nommer os et pièces** : Donne un nom à chaque os et chaque pièce directement dans la liste du panneau. — *Panneau Squelette Spine → liste* (PR #243 · t111)
- [ ] **Ombre portée** : Ajoute une ombre décalée derrière le sprite, avec son opacité. — *Post-traitement → Ombre X / Y + Opacité de l'ombre (0-255) (fiche d'aide animée)* (PR #236 · commit cb833003 · T110)
- [ ] **Onglet Bible** : Liste les personnages de la bible qui ont une planche pour en tirer leurs directions. — *Colonne source → onglet Bible (« Filtrer les personnages… »)* (PR #237, #242 · commits 330a2acd, 677f09a3 · t111)
- [ ] **Onglet Prompt** **payant** : Décrit un sprite en texte, génère les images puis les charge comme source pour les pixeliser en local. — *Colonne source → onglet Prompt ; format Carré / Portrait / Paysage* (PR #242 · commit 677f09a3 · t111)
- [ ] **Panneau Hitboxes** : Dessine des rectangles de collision par frame, de type hit (frappe) ou hurt (peut être touché), 16 au plus par frame. — *Préviz → panneau Hitboxes ; glisser pour dessiner* (PR #238 · commit 7fdb07e5 · T112)
- [ ] **Puces de la persona** : Ajoute au prompt d'un clic les mots-clés et couleurs de la persona. — *Onglet Prompt → puces sous le champ* (PR #242 · t111)
- [ ] **Source images de la Library** : De 1 à 64 images de la Library deviennent directement les frames, dans l'ordre, sans extraction vidéo. — *Utilisée par les onglets Bible et Prompt ; un nom avec chemin ou non-image est refusé* (PR #228 · commit c96a01ff · T108)
- [ ] **Squelette Spine : outil Os** : Trace un os en glissant de la base vers le bout ; il s'accroche à l'os choisi. — *Panneau Squelette Spine → bouton « Os » puis glisser sur la frame* (PR #243 · commit 9a953bdb · t111)
- [ ] **Squelette Spine : outil Pièce** : Trace une boîte qui devient une pièce découpée suivant l'os choisi. — *Panneau Squelette Spine → bouton « Pièce » puis glisser* (PR #243 · commit 9a953bdb · t111)
- [ ] **Tags d'animation** : Nomme des animations (idle, run, jump…) sur des plages d'images ; elles sont écrites dans le manifeste, le .tres et le .ase. — *Section Animation → bouton « + Tag »* (PR #236 · commit cb833003 · T110)
- [ ] **Type des rectangles** : Choisit si les prochains rectangles sont hit ou hurt. — *Panneau Hitboxes → menu « hit — frappe / hurt — peut être touché »* (PR #238 · T112)
- [ ] **Volet Préviz qui défile** : Correctif : le volet Préviz défile, les panneaux placés sous l'éditeur sont atteignables. (PR #238 · T112)
- [ ] **Écrire le rig** : Découpe les pièces et écrit le rig Spine 3.8 ; un nouveau rig remplace l'ancien. — *Panneau Squelette Spine → « Écrire le rig »* (PR #243 · commit 9a953bdb · t111)
- [ ] **Éditeur : Appliquer / Annuler** : Réassemble la feuille avec le nouvel ordre, ses tags et sa durée par image, ou revient à l'ordre actuel. — *Bande Éditeur → « Appliquer » ou « Annuler »* (PR #236 · commit cb833003 · T110)
- [ ] **Éditeur : dupliquer une image** : Recopie une image de la feuille à côté d'elle. — *Bande Éditeur → bouton Dupliquer* (PR #236 · commit cb833003 · T110)
- [ ] **Éditeur : réordonner les images** : Change l'ordre des images d'une feuille déjà faite sans refaire le job ni repayer le détourage. — *Bande Éditeur → flèches monter / descendre* (PR #236 · commit cb833003 · T110)
- [ ] **Éditeur : supprimer une image** : Retire une image de la feuille. — *Bande Éditeur → bouton Retirer* (PR #236 · commit cb833003 · T110)

### Peindre des décors en tuiles (Tile Lab) (`tilelab`, lot t178, reprend : nouveau) — 35 manques

**Tile Lab** — accès : Barre latérale → Game Assets → onglet Assets 2D → carte Tile Lab (ou sous-onglet Tuiles) ; page /tilelab/ ; barre de modes Seamless / Feuille de tuiles / Jeu / Formes / Peintre

- [ ] **Détection des tuiles** : Trouve chaque tuile par sa transparence, en ignorant la poussière plus petite que le côté minimal. — *Champ « Côté min » (px) puis bouton « Détecter »* (commits 6f60cf12, 320b2060 · lot 4)
- [ ] **Export Feuille alignée + JSON** : Chaque tuile centrée dans une cellule uniforme (taille commune + marge), avec son JSON. — *Export → champs colonnes, marge → « Feuille alignée + JSON »* (commit 320b2060 · lot 4)
- [ ] **Export Tileset + JSON** : La grille de placement peinte en PNG, avec le JSON des placements. — *Export → « Tileset + JSON »* (commit 320b2060 · lot 4)
- [ ] **Feuille de tuiles vers la Library** : La feuille alignée rejoint la Bibliothèque (préfixe tiles_feuille_). — *Export → « Save to Library »* (commit 320b2060 · lot 4)
- [ ] **Grille de placement carrée ou iso 2:1** : Pose les tuiles sur une grille carrée ou en losanges iso pour tester leurs raccords. — *Menu « Grille de placement » Carrée / Iso 2:1 ; champs cols, rows, cellule (fiche d'aide animée)* (commit 320b2060 · lot 4)
- [ ] **Liste des tuiles détectées** : Montre les tuiles trouvées ; un liseré cyan signale celles déjà posées. — *Clic = choisir une tuile* (commit 320b2060 · lot 4)
- [ ] **Mode Feuille de tuiles** : Ouvre une planche de tuiles existante pour la détecter, tester les raccords et l'exporter alignée, tout en local. — *Barre de modes → « Feuille de tuiles » ; planche de la Library ou « Ouvrir un PNG de mon PC »* (commit 320b2060 · lot 4 Tilelab 2)
- [ ] **Poser / retirer une tuile** : Place la tuile choisie dans une cellule de la grille. — *Clic sur une cellule ; clic droit retire ; bouton « Vider » retire tout* (commit 320b2060 · lot 4)
- [ ] **Raccord ×9** : Affiche la tuile pavée 3×3 pour juger son raccord. — *Double-clic sur une tuile détectée* (commit 320b2060 · lot 4)
- [ ] **Réordonner les tuiles** : Avance ou recule la tuile choisie dans l'ordre ; les placements suivent. — *« Ordre de la tuile choisie : » boutons ◀ ▶* (commit dced3450 · lot 5)
- [ ] **Tuiles séparées (zip)** : Télécharge un zip avec un PNG par tuile. — *Export → « Tuiles séparées (zip) »* (commit dced3450 · lot 5)
- [ ] **Aperçu auto-tuilé** : Dessine une carte tirée au hasard où chaque case reçoit la tuile de ses voisines. — *Mode Jeu → champs cases, densité → « Nouvel aperçu » (fiche d'aide animée)* (PR #245 · commit 8ae6ae97 · t115)
- [ ] **Blob 47 ou Blob 16** : Choisit un jeu de 47 tuiles (8 voisins, coins ronds) ou 16 tuiles (4 arêtes, plus rapide). — *Mode Jeu → menu Jeu « Blob 47 (8 voisins) / Blob 16 (4 arêtes) » (fiche d'aide animée)* (PR #239, #245 · t113)
- [ ] **Carte composée carte.png / carte.json** : Télécharge la carte composée et son plan, écrits dans le dossier du jeu. — *Mode Peintre → liens « carte.png » et « carte.json »* (PR #248 · t116)
- [ ] **Copier le prompt du lieu** : Copie le prompt pour le coller dans le générateur d'images. — *Bouton « Copier le prompt »* (PR #248 · t116)
- [ ] **Côté de la tuile** : Règle la taille en pixels des tuiles du jeu. — *Mode Jeu → champ « Côté »* (PR #245 · t115)
- [ ] **Export Godot .tres** : TileSet Godot 4 avec son terrain set. — *Mode Jeu → Export → « Godot .tres »* (PR #241 · commit 506174bc · t114)
- [ ] **Export LDtk .ldtk** : Projet LDtk 1.5.3 avec couche IntGrid et règles d'auto-layer. — *Mode Jeu → Export → « LDtk .ldtk »* (PR #241 · commit 506174bc · t114)
- [ ] **Export Tiled .tsx** : Tileset externe Tiled avec son jeu Wang (mixed pour blob 47, edge pour blob 16). — *Mode Jeu → Export → « Tiled .tsx » (à poser à côté de atlas.png)* (PR #241 · commit 506174bc · t114)
- [ ] **Export atlas.png** : Télécharge l'atlas PNG que les formats de moteur désignent. — *Mode Jeu → Export → « atlas.png »* (PR #241, #245 · t114)
- [ ] **Exports des formes** : Une tuile losange ou hexagonale s'exporte vers Tiled et Godot ; LDtk refuse en disant qu'il est orthogonal. — *Mode Formes → Export* (PR #245 · commit 010c377d · t115)
- [ ] **Fabriquer la tuile de forme** : Fabrique la tuile à la taille choisie (hauteur iso ou rayon hex) et montre son pavage sur le réseau. — *Mode Formes → champ px → « Fabriquer la tuile »* (PR #245 · t115)
- [ ] **Fabriquer le jeu** : Construit l'atlas du jeu (copié en Bibliothèque comme tile_…_atlas.png) et mesure le raccord des voisines. — *Mode Jeu → « Fabriquer le jeu »* (PR #239, #245 · t113)
- [ ] **Glisser rapide du peintre** : Correctif : un glisser rapide peint toutes les cases traversées, sans trous. (PR #248 · commit a859622b · t116)
- [ ] **Matières A (terrain) et B (fond)** : Choisit par vignettes la matière du terrain puis celle du fond autour. — *Mode Jeu → cases « A · terrain » puis « B · fond », clic sur une image* (PR #245 · t115)
- [ ] **Matières du Material Forge** : Prend la couleur de base d'une matière du Material Forge comme source d'un jeu ou d'une forme. — *Modes Jeu et Formes → bascule « Bibliothèque / Material Forge » ; « Filtrer les matières… »* (PR #248 · commit ef9c7c55 · t116)
- [ ] **Mesures raccord, répétition, éclairage** : Mesure le raccord, la répétition visible et l'écart d'éclairage, chacun avec son seuil et un verdict ok / attention. — *Mode Jeu → « Mesurer »* (PR #245 · commit c8844bba · t115)
- [ ] **Mode Formes** : Une matière devient une tuile losange iso 2:1 ou hexagonale qui pave sans trou ni couture. — *Barre de modes → « Formes » ; menu Forme « Losange isométrique 2:1 / Hexagone à sommet plat » (fiche d'aide animée)* (PR #245 · commits 010c377d, 6608b3d0 · t115)
- [ ] **Mode Jeu** : Deux matières deviennent un jeu de tuiles auto-tuilable, mesuré et exportable. — *Barre de modes → « Jeu »* (PR #239, #245 · commits 4f3576a7, 6608b3d0 · t113, t115)
- [ ] **Mode Peintre** : Peint une petite carte de terrain ; à chaque coup, la bonne tuile du jeu fabriqué est posée selon les voisines. — *Barre de modes → « Peintre » ; clique-glisse pour peindre, repasser gomme* (PR #248 · commit b68af808 · t116)
- [ ] **Style d'un lieu de la bible** : Compose un prompt de tuile contraint par la planche et la palette d'un lieu de la bible, sans rien générer. — *Mode Jeu → bloc « Style d'un lieu de la bible » : Lieu, Surface → « Prompt du lieu » ; pastilles de palette* (PR #248 · commit c3109755 · t116)
- [ ] **Taille et graine de la carte peinte** : Règle largeur et hauteur en cases et la graine des variantes (même graine = mêmes variantes). — *Mode Peintre → champs Largeur, Hauteur, Graine* (PR #248 · t116)
- [ ] **Tout effacer (peintre)** : Vide la grille en gardant sa taille. — *Mode Peintre → « Tout effacer »* (PR #248 · t116)
- [ ] **Variantes** : Fabrique 1 à 5 variantes par tuile ; elles ne touchent que le cœur, le raccord reste parfait. — *Mode Jeu → champ « Variantes » (1 à 5)* (PR #245 · commit 8ae6ae97 · t115)
- [ ] **Recevoir une image envoyée** : Une image envoyée depuis la Bibliothèque ou le Photolab devient la source de la tuile. — *Bibliothèque ou Photolab (Fichier > Envoyer vers…) → « Tile Lab — source de la tuile »* (PR #266 · commit eeee9ed1 · t139)

### Créer des cartes à jouer (Card Forge) (`cardforge`, lot t179, reprend : c18) — 24 manques

À corriger dans l'ancien texte :

- [ ] « huit modules » alors que le chap. 19 décrit un module 09 (incohérence)
- [ ] Gabarits imprimeur MPC/TGC/DriveThruCards + PDF X-1a (#83), édition (#84), dos/mire/stats (#85), langues (#86), art en lot/jeu 3D/livret (#87) non décrits
- [ ] « se règle désormais » (formulation de nouveauté)

**Card Forge (éditeur de cartes à jouer)** — accès : Barre latérale → Game Assets → sous-onglet Card Forge ; modules dans le rail de gauche (01 Face … 07 Impression, 09 Forge 3D, 11 Édition)

- [ ] **Éditer cette face dans le Vectorlab** : Envoie la face rendue dans un document Vectorlab au format physique du jeu, avec repères et calque verrouillé, pour la retoucher en vectoriel. — *Bouton « Éditer cette face dans le Vectorlab »* (commit 651482d5 · Vectorlab lot A)
- [ ] **Art du deck en lot** **payant** : Génère l'illustration de chaque ligne du deck en un lot (prompt gabarit avec {colonne}, style, entité de la bible), avec devis par ligne, mur de dépense par lot et garde des plafonds ; la colonne d'art se remplit en une modification annulable. — *Module 04 Données → panneau « Art du deck en lot » : devis, dialogue de confirmation, variantes au choix* (PR #176 · commit 031db9a0 · tâche #87)
- [ ] **Boîte dépliée (tuck box)** : Génère le patron PDF vectoriel d'une boîte à rabats pour le deck (trait plein = couper, pointillé = plier), épaisseur lue du module 05. — *Module 09 Forge 3D → panneau « Objets du jeu » → boîte* (PR #177 · commit d0084cda · tâche #87)
- [ ] **Export Tabletop Simulator** : Exporte le deck en planches 10 × 7 et objet sauvegardé Tabletop Simulator (dos commun ou dos uniques, surnom = titre de la carte) dans un ZIP. — *Module 11 Édition, cible Tabletop Simulator → « Exporter pour Tabletop Simulator (.zip) »* (PR #168 · commit 2cd3fa00 · tâche #84)
- [ ] **Export Tabletopia** : Exporte une image JPEG par face (recto et verso séparés, dos unique si tous identiques) avec un manifeste, au format attendu par Tabletopia. — *Module 11 Édition, cible Tabletopia → « Exporter pour Tabletopia (.zip) »* (PR #169 · commit 54d6fef9 · tâche #84)
- [ ] **Fiche produit** : Rédige la fiche chiffrée du jeu (format, dimensions, paquet, boîte, langues) et un texte prêt à recopier. — *Module 11 Édition → groupe Mockup / fiche* (PR #178 · commit 59edcc40 · tâche #87)
- [ ] **Gabarits d'imprimeur MPC / TGC / DriveThruCards** : Le jeu se règle d'un clic sur le gabarit exact d'un imprimeur en ligne (fond perdu, zone sûre, DPI, pixels attendus par son portail) ; les formats non vérifiés sont grisés et le disent. — *Module 07 Impression → bloc « Gabarit d'imprimeur » en tête : une carte par imprimeur (maison, MPC, TGC, DTC) ; revenir à « maison » restaure les réglages d'avant* (PR #165 + #166 · commits 0c819313, a4bd70c9 · tâche #83)
- [ ] **Import Google Sheets par lien** : Importe une feuille Google Sheets publique (ou publiée sur le web) directement par son lien ; une feuille non partagée est signalée. — *Module 04 Données → bouton « Lien Google Sheets… » (dialogue de saisie du lien)* (PR #172 · commit bcfc5ac5 · tâche #85)
- [ ] **Import d'un export Notion (.zip)** : Accepte le ZIP d'export d'une base Notion (CSV, même imbriqués) comme source de données du deck, sans clé ni réseau. — *Module 04 Données → import de fichier, .zip accepté* (PR #172 · commit bcfc5ac5 · tâche #85)
- [ ] **Livret de règles** : Compose un livret de règles à 300 DPI avec les polices de l'application (intertitres « # »), et une planche des cartes. — *Module 11 Édition → groupe Livret* (PR #178 · commit 59edcc40 · tâche #87)
- [ ] **Localisation : une colonne par langue** : Les colonnes suffixées par langue (nom_fr, nom-EN, titre_en_us… 12 langues) sont reconnues ; on choisit la langue active du jeu et toutes les pièces suivent, avec ce qui manque carte par carte. — *Module 04 Données → sélecteur « Langue active » (langues marquées si incomplètes)* (PR #173 · commit 87ceb3a0 · tâche #86)
- [ ] **Mire recto-verso à vernier (PDF)** : Imprime une mire de deux pages avec un vrai vernier (lecture au dixième de millimètre) pour mesurer le décalage entre recto et verso de votre imprimante, quel que soit le sens du retournement. — *Module 07 Impression → bouton « Mire recto-verso (PDF) »* (PR #170 · commit b00334cc · tâche #85)
- [ ] **Mockup en éventail** : Produit une image de présentation des cartes en éventail (5 cartes au plus) au format carré, story ou paysage, coins arrondis du jeu. — *Module 11 Édition → groupe Mockup / fiche* (PR #178 · commit 59edcc40 · tâche #87)
- [ ] **Objets du jeu : jetons, pion, présentoir** : Crée en 3D imprimable un jeton, un jeton en relief de la carte, un pion à étages ou un présentoir qui tient la carte, écrits dans le dossier de l'Imprimante. — *Module 09 Forge 3D → panneau « Objets du jeu »* (PR #177 · commit d0084cda · tâche #87)
- [ ] **Origine du dos de chaque carte** : Une ligne « Dos » dit, pour chaque valeur de la colonne dos, d'où vient le verso (motif du catalogue, illustration, image locale, dos commun ou introuvable) et passe au rouge s'il y a perte. — *Module 04 Données → ligne « Dos »* (PR #170 · commit b00334cc · tâche #85)
- [ ] **PDF/X-1a pour DriveThruCards** : Le PDF devient X-1a (CMJN) pour DriveThruCards quand le profil de presse est chargé ; sans profil, les dimensions sont tenues et l'écart est écrit à l'écran. — *Module 07 Impression, gabarit DTC → export PDF* (PR #165 + #166 · commits 0c819313, a4bd70c9 · tâche #83)
- [ ] **Paquet imprimeur (.zip)** : Exporte un ZIP recto/verso nommé d'après le deck, complété à la taille du jeu, avec un manifeste (toile, fond perdu, empreinte de chaque fichier) prêt à téléverser chez MPC ou TGC. — *Module 07 Impression → bouton « Paquet imprimeur (.zip) » (passe par le contrôle avant vol)* (PR #165 + #166 · commits 0c819313, a4bd70c9 · tâche #83)
- [ ] **Pièce 11 « Édition »** : Onzième module du rail pour tout ce qui se livre autour de la carte : choix d'une cible de table virtuelle, livret, mockup, fiche produit. — *Rail de gauche → 11 · Édition* (PR #167 · commit 40ff839d · tâche #84)
- [ ] **Poser dans Tabletop Simulator** : Copie directement le deck exporté dans vos Saved Objects de Tabletop Simulator (dossier Deepotus) ; dit si TTS est absent ou si rien n'est exporté. — *Module 11 Édition → « Poser dans Tabletop Simulator »* (PR #168 · commit 2cd3fa00 · tâche #84)
- [ ] **Statistiques du jeu** : Histogrammes colonne par colonne du deck (quantités appliquées) : min, max, moyenne, médiane, courbe de coût, valeurs catégorielles triées. — *Module 04 Données → bloc repliable « Statistiques du jeu »* (PR #171 · commit bb144001 · tâche #85)
- [ ] **Traduction par LLM validée carte par carte** **payant** : Propose la traduction d'une colonne dans une autre langue ; rien n'entre dans la table sans votre clic, propositions corrigeables, devis avant tout appel (moteur des Réglages, ou Ollama local gratuit). — *Module 04 Données → traduire : devis puis dialogue (coût, fournisseur, colonnes créées), puis acceptation carte par carte* (PR #174 · commit b808f110 · tâche #86)
- [ ] **Finitions de surface laque / cuir / métal brossé / émissif** : Ces quatre finitions habillent maintenant vraiment la carte dans le GLB du Forge 3D (elles étaient auparavant ignorées). — *Module 09 Forge 3D → nœud matière → finition* (PR #213 · commit a8cb5295)
- [ ] **Relief à la hauteur de la matière** : Un relief sans profondeur saisie prend automatiquement la hauteur physique (mm) de la matière chaînée, sinon 0,6 mm ; un écrêtage aux bornes est dit. — *Module 09 Forge 3D → champ profondeur du relief laissé vide = « auto : hauteur de la matière, sinon 0.6 »* (PR #201 · commit f41acef4 · T097)
- [ ] **Icônes Deepotus Glyph (G2)** : Tout le Card Forge (rail, barres d'outils, blocs, galerie, Forge 3D, chevrons) passe aux icônes de la suite Deepotus Glyph ; une image introuvable s'affiche avec l'icône d'erreur. (PR #286 · commits 3ee80d14, 95c084ee, 75f51543)

### Passer de l'image à l'objet 3D (`forge3d`, lot t179, reprend : c19) — 19 manques

À corriger dans l'ancien texte :

- [ ] Badge « nouveau »
- [ ] « qualité NFT »
- [ ] « 30 cr (~0,60 $) » chiffré dans la légende

**3D Studio / Moteurs 3D** — accès : Game Assets → sous-onglet 3D Studio (/studio3d) ; zone Optimiser de la carte 3D du hub (Game Assets → 3D)

- [ ] **Atelier fal** : Panneau qui liste les jobs Game Assets 3D (fal) pour les rigger, convertir, ranger au banc ; les boutons grisés disent pourquoi (clé Meshy, clé fal, approbation, texture). — *Bouton « Atelier fal (rig d'un job) »* (PR #216 · commit f1c1f870 · T104)
- [ ] **Banc de référence des moteurs** : Affiche par moteur les médianes mesurées chez vous (triangles, poids, étanchéité, silhouettes, coût) et permet d'y ranger un job déjà produit. — *Atelier fal → « banc de référence » et « ranger ce job au banc · gratuit »* (PR #230 · commit ead36a78 · T107)
- [ ] **Chaîne de LOD** : Décline le modèle courant en niveaux de détail, avec perte mesurée par niveau (silhouette et normales) et budgets proposés mobile / PC / impression ; téléchargement en ZIP. — *Carte 3D du hub → zone Optimiser → bloc LOD* (PR #219 · commit f41dc2d0 · T105)
- [ ] **Clé fal exigée avant le texturage** *(coût variable)* : Texturer un modèle (Meshy) est refusé tout de suite sans clé fal, au lieu d'échouer plus tard en laissant une dépense estimée. (PR #220 · commit 31eff973)
- [ ] **Conversion FBX / USDZ / BLEND par Meshy** **payant** : Conversion confiée à Meshy (1 crédit par tâche), suivie dans la file, sous la garde des plafonds. — *Atelier fal → bloc Conversion (format Meshy) → confirmation* (PR #222 · commit f8ccbf42 · T105)
- [ ] **Conversion locale OBJ / STL / 3MF / glTF** : Convertit le modèle localement et gratuitement ; STL et 3MF à une taille en millimètres. — *Atelier fal → bloc Conversion → taille (mm) → « Convertir »* (PR #222 · commit f8ccbf42 · T105)
- [ ] **Coût du rig et du raffinement** *(coût variable)* : Le tableau des dépenses chiffre le rig Meshy en crédits et le raffinement à son palier de texture réel. — *Réglages → dépenses* (PR #225 · commit b683ebe2)
- [ ] **Détourer une vue** : Retire le fond d'une vue, en local et gratuitement. — *Vignette → « Retirer le fond »* (PR #224 · commit 53d7eb36 · T106)
- [ ] **Importer un modèle** : Importe un OBJ, STL, glTF ou GLB comme un nouveau job visible de l'Atelier fal, de l'Établi et de la Bibliothèque. — *Atelier fal → « Importer un modèle (OBJ, STL, glTF, GLB) »* (PR #222 · commit f8ccbf42 · T105)
- [ ] **Photos réelles comme vues** : Construit le jeu de vues à partir de photos de la Bibliothèque (celles du téléphone groupées en tête), redressées selon l'EXIF et détourées par défaut. — *Vues d'abord → « jeu de vues depuis les photos · gratuit »* (PR #234 · commit 101a6711 · T107)
- [ ] **Rejouer une vue** **payant** : Régénère une seule vue avec un prompt corrigé. — *Vignette → « Rejouer la vue »* (PR #224 · commit 53d7eb36 · T106)
- [ ] **Rig Meshy d'un job fal** **payant** : Ajoute un squelette au modèle et rapatrie des animations de la bibliothèque Meshy (marche et course incluses), avec devis par tâche et confirmation. — *Atelier fal → taille (m), cases d'actions (3 cr chacune), « Rig Meshy · N cr » puis « Payer »* (PR #216 · commit f1c1f870 · T104)
- [ ] **Service GPU local optionnel** : Moteur local Hunyuan (gratuit) utilisable si un service tourne à côté ; l'atelier affiche son état, la carte graphique et la VRAM, et le moteur reste grisé tant que le service dort. — *État dans l'atelier ; adresse réglable par LOCAL3D_URL* (PR #232 · commit a06968b9 · T107)
- [ ] **Textures aux conventions moteur** : Exporte les textures du maillage renommées selon la convention choisie (standard, Blender, Unity URP/HDRP, Unreal, Godot) avec MaskMap Unity et bordereau. — *Carte 3D du hub → zone Optimiser → bloc Textures (convention, résolution)* (PR #221 · commit 70413103 · T105)
- [ ] **Tirer le maillage sur les vues** **payant** : Lance le moteur 3D sur le jeu de vues validé ; seul le moteur est facturé. — *« Tirer · moteur » puis dialogue de paiement* (PR #224 · commit 53d7eb36 · T106)
- [ ] **Vues d'abord : préparer les vues** **payant** : Génère d'abord les vues (face, dos, profils) avant de lancer le moteur 3D, pour qu'une vue ratée ne coûte pas un maillage. — *Bloc « Vues d'abord · avant le moteur » → nombre de vues, sujet, « Préparer les vues »* (PR #224 · commit 53d7eb36 · T106)
- [ ] **Vues depuis la planche de la bible** : Reprend gratuitement les vues de la planche d'un personnage ou objet de la bible ; le maillage rejoint ensuite la fiche de l'entité. — *Vues d'abord → « vues de la planche · gratuit »* (PR #226 · commit 2c0b63cc · T106)
- [ ] **Icônes Deepotus Glyph (G6)** : Le 3D Studio, l'Atelier, les Matières, l'Établi et le Plateau 3D passent aux icônes Deepotus Glyph ; le favicon devient le logo Deepotus. (PR #285 · commits 0e77a512, b92b1313)
- [ ] **Listes déroulantes sans emoji** : Les photos du téléphone sont groupées sous « Téléphone » dans les listes, sans emoji collé dans les options. (PR #291 · commit a360d7ef)

### Créer des matières (Material Forge) (`matieres`, lot t179, reprend : nouveau) — 13 manques

**Material Forge (Matières)** — accès : Game Assets → sous-onglet Matières (/materialforge/)

- [ ] **Catalogue CC0 Poly Haven** : Trente matières CC0 (six familles) embarquées, filtrables et importables en matières ordinaires avec leur crédit. — *En-tête → bouton « Catalogue CC0 » (aussi dans la galerie vide)* (PR #202 · commit ef0cd603 · T097)
- [ ] **Comparer côte à côte** : Affiche une seconde matière dans un second viewport, même ambiance et même caméra (Mon modèle compris). — *Barre du viewport → « ⇔ Comparer »* (PR #200 · commit 08a7d8d7 · T096)
- [ ] **Convention d'export Blender** : Nouvelle convention de noms pour Blender (fichiers séparés, emplacements du Principled BSDF indiqués dans le bordereau et le LISEZMOI). — *Export → sélecteur de convention → bouton « Blender »* (PR #197 · commit 3ba02144 · T096)
- [ ] **Finitions essayées avant d'être posées** : Choisir un préréglage (dont laque, cuir, émissif animé, métal brossé fin) ne l'écrit plus : l'aperçu le montre, puis on pose ou on annule. — *Préréglages → « Poser » / « Annuler »* (PR #206 · commit 166ed5db · T098)
- [ ] **HDRI personnels** : Importe vos propres ambiances .hdr (ou image 2:1) à côté des sept fournies, et les supprime. — *Sous les puces d'ambiance → « ＋ HDRI… » et corbeille* (PR #199 · commit cdef16e9 · T096)
- [ ] **Hauteur physique (mm)** : La carte de hauteur déclare ses millimètres (0 à 20 mm), repris par le relief du Forge 3D des cartes et noté dans le bordereau. — *Inspecteur → curseur « Hauteur physique (mm) »* (PR #201 · commit f41acef4 · T097)
- [ ] **Intensité émissive sans changement de teinte** : Une émission au-delà de 1 garde sa couleur (l'orange ne vire plus au jaune) grâce à l'extension glTF emissive_strength. (PR #212 · commit ac5e92ae)
- [ ] **Mon modèle** : Prévisualise la matière posée sur un modèle de l'Établi au lieu de la forme standard. — *Viewport → puce « Mon modèle » + sélecteur des jobs de l'Établi* (PR #198 · commit de008ef8 · T096)
- [ ] **Onglet Générateurs** : Dix générateurs de matières sans couture, locaux et gratuits (briques, carrelage, planches, damier, hexagones, galets, métal brossé, cuir, tissu, rayures), réglés en direct avec aperçu. — *Rail gauche → onglet « ◈ Générateurs » → réglages, graine, « Créer la matière »* (PR #203 + #204 · commits 95f9c69f, 7f558599 · T098)
- [ ] **Panneau Photo : redressement par quatre coins** : Cliquez les quatre coins d'une surface photographiée de biais (dans n'importe quel ordre) pour la redresser en carré avant de forger la matière. — *Groupe « Photo » sous la référence → canevas des quatre coins, aperçu, remise à zéro* (PR #195 + #196 · commits 5e8daa8c, 582511eb · T095)
- [ ] **Photo → matière** : Une photo brute devient une matière complète en une requête (rangée dans la Bibliothèque, redressée, délightée) ; sur mobile le champ ouvre l'appareil photo arrière. — *Champ photo* (PR #206 · commit 166ed5db · T098)
- [ ] **Retirer l'éclairage (delighting)** : Retire l'éclairage cuit de la photo avec une intensité réglable ; le badge affiche l'écart d'éclairage avant/après. — *Groupe « Photo » → retirer l'éclairage, intensité* (PR #195 + #196 · commits 5e8daa8c, 582511eb · T095)
- [ ] **Icônes Deepotus Glyph (G6)** : Les Matières passent aux icônes de la suite Deepotus Glyph. (PR #285 · commit 0e77a512)

### Préparer une pièce avant le slicer (Établi) (`etabli`, lot t180, reprend : c21) — 35 manques

À corriger dans l'ancien texte :

- [ ] Badge « nouveau »
- [ ] Aucune capture
- [ ] Liens « vérifiés le 05/10/2026 » (datés)
- [ ] Chemin « Game Assets → 3D Studio → 07 · Établi 3D → » (à vérifier vs navrail actuel)
- [ ] Établi : booléens/connecteurs (T092), rig/export (T093), matériaux + Blender (T094), profils (#88) non décrits

**Établi (atelier 3D avant impression)** — accès : Game Assets → 3D Studio → nœud « 07 · Établi 3D » (l'Établi prend la place de la page, retour par « ← 3D Studio »)

- [ ] **Contour du plateau réel et zone exclue** : La plaque dessine le plateau réel de la machine choisie (contour vert) et la zone où l'on ne pose rien (rectangle rouge) ; une pièce trop grande est refusée par la garde du plateau. — *Visible dès qu'une taille cible est posée* (PR #180 · commit 088734c5 · tâche #88)
- [ ] **Profils d'imprimante** : Choix de l'imprimante : Elegoo Centauri Carbon 2 intégrée, plus les profils OrcaSlicer/ElegooSlicer installés (lus, jamais modifiés) et des profils saisis à la main ; le profil actif sert aussi aux exports d'impression. — *Rail de droite → menu imprimante (sous le repère)* (PR #180 · commit 088734c5 · tâche #88)
- [ ] **Réparer en un clic** : Soude les sommets, retire doublons et triangles plats, remet les normales dans le même sens et (si coché) bouche les trous ; écrit une version de plus et détaille le résultat dans la barre du bas. — *Onglet Fiche → bloc « Réparer le maillage » / « Réparer en un clic » (trous décochés d'office)* (PR #179 · commit 49b864da · tâche #88)
- [ ] **Bouton Aide de l'Établi** : Panneau d'aide sous le repère : le pas à pas du chapitre 21 du guide, les 18 mots du lexique et les liens vers le guide. — *En-tête → bouton « Aide »* (PR #187 · commit 28dfbcc9 · T091)
- [ ] **Contradiction assise / recentrer refusée** : Si « posé sur une face » et « recentrer sur l'origine » sont dans la même file, la barre le dit et « écrire la version » se grise (annuler reste actif). (PR #184 · commit b44736c3 · T090)
- [ ] **Creuser** : Remplace l'intérieur plein par une coque fermée d'épaisseur constante ; dit l'épaisseur qui tient si la paroi demandée est trop épaisse, refuse un maillage ouvert. — *Onglet Fiche → Creuser (paroi en mm, 2 mm pour commencer)* (PR #183 · commit 3c6ce3de · tâche #89)
- [ ] **Décimer** : Réduit le nombre de triangles vers une cible (via gltfpack) et écrit une version de plus ; dit si la cible n'a pas pu être atteinte. — *Onglet Fiche → Décimer* (PR #182 · commit 1e725038 · tâche #89)
- [ ] **Extraire une par une** : Sépare chaque élément du modèle en une version à part, toutes sœurs dans la lignée. — *Onglet Fiche → extraire séparément* (PR #182 · commit 1e725038 · tâche #89)
- [ ] **Lecture chiffrée de la pièce glissée** : Sous « Sur la plaque », une ligne donne le coin, les cotes et l'angle de la pièce courante dans le repère du plateau, mise à jour pendant le glisser, aux flèches et après « Ranger ». — *Glisser une pièce (aimantée au pas, Maj libère) ou la pousser aux flèches* (PR #184 · commits b44736c3, 3b010976 · T090)
- [ ] **Mesurer** : Deux clics donnent une distance, ses composantes x/y/z et l'angle dièdre entre les deux faces, tracés dans la scène. — *Mode « Mesurer »* (PR #181 · commit 6bc91698 · tâche #89)
- [ ] **Ranger sur le plateau** : Pose automatiquement les pièces dans le plateau réel, tournées si cela fait gagner de la place, 2 mm d'écart, jusqu'à 8 plateaux ; ce qui ne tient pas est dit. — *« Sur la plaque » puis bouton « Ranger sur le plateau » (refusé sans taille cible)* (PR #181 · commit 6bc91698 · tâche #89)
- [ ] **Surplombs** : Peint en orange les faces penchées à moins de 45° depuis l'horizontale, là où le slicer posera des supports ; aperçu indicatif, rien n'est écrit. — *Bouton « Surplombs »* (PR #185 · commit d2068652 · T091)
- [ ] **Tranches** : Trace en bleu vingt sections de la version écrite pour voir la forme réelle à chaque hauteur (refusé sur la plaque ou devant une file non écrite). — *Bouton « Tranches »* (PR #185 · commit d2068652 · T091)
- [ ] **→ Impression 3D de la version affichée** : L'export d'impression écrit le STL et le 3MF de la version affichée (réparée, posée, creusée…) aux millimètres de la taille cible, et non plus le brouillon du moteur. — *Onglet Export → « → Impression 3D », puis « Ouvrir dans le slicer »* (PR #186 · commit af8898d6 · T091)
- [ ] **Booléen : différence (A − B)** : Retire la pièce B de la pièce A (poinçon, logement) ; la barre dit la couture et les matières perdues. — *Panneau Parties → différence (A − B), « Appliquer »* (PR #189 · commit b572ac31 · T092)
- [ ] **Booléen : intersection** : Ne garde que le volume commun à A et B. — *Panneau Parties → intersection, « Appliquer »* (PR #189 · commit b572ac31 · T092)
- [ ] **Booléen : union** : Fusionne exactement deux pièces A et B en une seule, les autres pièces restant intactes. — *Panneau Parties → « A = sélection », « B = sélection », union, « Appliquer »* (PR #189 · commit b572ac31 · T092)
- [ ] **Connecteur cheville** : Après une coupe, perce un trou dans chaque moitié et fournit une goupille séparée. — *Barre du couteau → « cheville »* (PR #190 · commit b431341e · T092)
- [ ] **Connecteur queue d'aronde** : Après une coupe, crée une queue d'aronde qui coulisse dans le plan de coupe et retient les moitiés ; les cas impossibles sont dits. — *Barre du couteau → « queue d'aronde »* (PR #190 · commit b431341e · T092)
- [ ] **Connecteur téton** : Après une coupe, ajoute un téton sur une moitié et son logement (avec jeu) dans l'autre. — *Barre du couteau → « téton »* (PR #190 · commit b431341e · T092)
- [ ] **Creuser : triangles d'aire nulle signalés** : Quand la paroi égale le pas du maillage, les triangles intérieurs aplatis sont comptés et un avertissement dédié le dit au lieu d'un faux motif. (PR #235 · commit 84bd500c)
- [ ] **Déposer dans le projet du moteur** : Copie le fichier dans un sous-dossier Deepotus du projet (Assets/Deepotus, Content/Deepotus, deepotus/) après vérification de la racine ; prévient si Unity n'a pas glTFast. — *Onglet Export → « Déposer »* (PR #192 · commit ccf6aa20 · T093)
- [ ] **Facteurs de matériau** : Modifie couleur, opacité, métal, rugosité, émission, mode alpha et double face d'un matériau avec aperçu en direct ; seuls les champs touchés sont écrits, en une version de plus. — *Onglet Fiche → sélecteurs de couleur, curseurs, « Appliquer »* (PR #193 · commit cb0349e7 · T094)
- [ ] **Masques de cavités et d'arêtes** : Affiche en vue B les creux (rouge) et arêtes (vert) lus sur la géométrie, la vue A restant intacte et la caméra synchronisée. — *Panneau Parties → « Masques »* (PR #205 · commit c9101aa1 · T098)
- [ ] **Messages de refus lisibles** : La barre affiche la phrase du refus du serveur au lieu du JSON brut. (PR #192 · commit ccf6aa20)
- [ ] **Orientation automatique** : Propose trois poses classées (appui, surplomb, hauteur) avec un avertissement ; un clic applique la pose choisie. — *Bouton « Orienter » → propositions dans l'onglet Fiche, clic sur l'une* (PR #188 · commit 806a0f33 · T092)
- [ ] **Ouvrir dans l'éditeur du moteur** : Ouvre le fichier dans Blender (importé au lancement) ou le projet Unity / Godot / Unreal ; refuse en nommant le réglage si l'exécutable n'est pas configuré. — *Onglet Export → « Ouvrir »* (PR #192 · commit ccf6aa20 · T093)
- [ ] **Percer un trou de drainage** : Perce la seule paroi sous le clic d'une pièce creusée et recoud le trou (la paroi opposée n'est pas touchée), pour laisser s'écouler la résine. — *Onglet Fiche → « Percer (drainage) », diamètre 3-4 mm, puis clic sur la face ; Échap range le foret* (PR #233 · commit 5cc50348 · t133)
- [ ] **Préparer pour Blender, Godot, Unreal, Unity** : Écrit un glTF standard par moteur cible avec sa fiche d'import (axes, échelle, marche à suivre). — *Onglet Export → cible → « Préparer »* (PR #192 · commit ccf6aa20 · T093)
- [ ] **Retour de Blender** : Réimporte un GLB corrigé dans Blender comme une version de plus et dit ce qui s'est perdu (os, clips, matériaux). — *Onglet Export → « Retour de Blender »* (PR #194 · commit 530be9b5 · T094)
- [ ] **Rig : clips d'animation** : Joue les clips livrés avec le modèle, avec vitesse et arrêt. — *Panneau Rig → clips* (PR #191 · commit edf1b61a · T093)
- [ ] **Rig : poids d'influence** : Affiche en couleurs les sommets influencés par un os. — *Panneau Rig* (PR #191 · commit edf1b61a · T093)
- [ ] **Rig : pose d'essai** : Fait tourner un os par trois curseurs x/y/z relatifs au repos, avec retour au repos. — *Panneau Rig → curseurs x/y/z* (PR #191 · commit edf1b61a · T093)
- [ ] **Rig : squelette et chaîne d'un os** : Dessine les os à travers la peau dans la scène, en arbre indenté, et surligne la chaîne d'un os choisi. — *Panneau Rig* (PR #191 · commit edf1b61a · T093)
- [ ] **Une matière par partie (Habiller)** : Pose une matière du Material Forge sur les parties cochées du modèle et écrit une version de plus. — *Panneau Parties → sélecteur de matière + « Habiller »* (PR #205 · commit c9101aa1 · T098)

### Imprimer ses créations en 3D (`impression3d`, lot t180, reprend : c20) — 0 manques

À corriger dans l'ancien texte :

- [ ] Badge « nouveau »
- [ ] Aucune capture
- [ ] Le Vectorlab n'apparaît que ici (aucun chapitre Vectorlab/Spritelab/Tilelab/Photolab)


### Mettre en scène sur le Plateau 3D (`plateau`, lot t180, reprend : nouveau) — 7 manques

**Plateau 3D** — accès : Page /plateau, ouverte par le bouton Plateau (caméra) sur une carte de plan du storyboard de l'Atelier ; retour par « Atelier »

- [ ] **Appliquer au plan** : Propose au plan lié le type de plan, le mouvement, le prompt de mouvement et les images de bornes, comparés avant/après puis confirmés. — *Sorties → « Appliquer au plan… »* (PR #257 · commit fcaeb561 · t127)
- [ ] **Cadre, format et focale** : Cadre au ratio choisi (16:9, 9:16, 1:1, 2.39:1), focale en mm et guides (tiers, croix, zone-titre, horizon). — *Panneau Cadre* (PR #257 · commit fcaeb561 · t127)
- [ ] **Capturer début / fin** : Capture le cadre du premier et du dernier keyframe vers la Bibliothèque (provenance plateau). — *Sorties → « Capturer début / fin »* (PR #257 · commit fcaeb561 · t127)
- [ ] **Composer le GLB de scène** : Écrit le GLB de la scène, versionné avec sa fiche. — *Sorties → « Composer le GLB »* (PR #257 · commit fcaeb561 · t127)
- [ ] **Composer une scène 3D** : Pose des volumes simples (boîte, capsule, cylindre, sphère) ou un maillage d'un job 3D ou d'une entité de la bible pour bloquer un plan avant tout tir payant. — *Barre Scène → Boîte / Capsule / Cylindre / Sphère / maillage… (« Poser ce maillage »)* (PR #257 · commit fcaeb561 · t127)
- [ ] **Keyframes et mouvement de caméra** : Poser des keyframes caméra sur la tête de lecture, choisir un preset (travelling avant, orbite 90°, grue descendante, plan fixe) et lire le mouvement en boucle. — *Touche K pour poser un keyframe, Espace pour lire* (PR #257 · commit fcaeb561 · t127)
- [ ] **Listes groupées** : Les maillages à poser sont groupés sous « Entités de la bible » et « Maillages 3D ». (PR #291 · commit a360d7ef)

## Repères

### Parcours complets, de l'idée au post (`parcours`, lot t181, reprend : nouveau) — 0 manques


### Lire les icônes (`icones`, lot t170, reprend : nouveau) — 46 manques

**Icônes « Deepotus Glyph »** — accès : Toute l'application et tous les labs ; lexique des icônes dans docs/icones

- [x] **Atelier, Matières, Établi, Plateau 3D, Studio 3D en icônes Glyph** : Ces cinq pages et les éléments partagés (micro du champ IA, carte de mise à jour) passent à la suite ; la marque de l'Atelier devient le logo. (PR #285 · commits 0e77a512, b92b1313 · G6)
- [x] **Card Forge en icônes Glyph** : Rail, barres d'outils, blocs, alignements, galerie et Forge 3D du Card Forge passent à la suite (166 emplacements) ; image introuvable = icône d'erreur. (PR #286 · commits 3ee80d14, 95c084ee · G2)
- [x] **Chevron unique** : Accordéons et rails utilisent un seul chevron « déplier » orienté selon l'état. (PR #287 · commit 99a298fd · G1)
- [x] **Coque React en icônes Glyph** : Coque, Quick, Studio, Templates, News, Scheduler, Épisodes, Game Assets, Bibliothèque et Réglages passent aux icônes de la suite ; titre de la page sans emoji. (PR #287 · commit c101e8bc · G1)
- [x] **Favicon = logo Deepotus** : L'onglet du navigateur de toutes les pages affiche le logo Deepotus. (PR #285 · commit b92b1313 · G6)
- [x] **Icône d'application = logo Deepotus** : L'icône d'application (et l'icône adaptative du téléphone) est le vrai logo Deepotus. (PR #281 · commit dd9e3307 · G0)
- [x] **Lexique des icônes** : Un lexique documente chaque icône et la fonction qu'elle désigne. — *docs/icones (lexique)* (PR #281 · commit 0ab48c7f · G0)
- [x] **Listes déroulantes sans emoji** : Plus de glyphe collé dans les options : au Plateau 3D les choix sont groupés « Entités de la bible » / « Maillages 3D », au Studio 3D les photos du téléphone sont groupées en tête sous « Téléphone ». (PR #291 · commit a360d7ef)
- [x] **Montage, Son & VFX, tiroir Sons, rack VFX en icônes Glyph** : Les couches Montage, Son & VFX, tiroir Sons, rack VFX, les sous-titres et le transfert reçoivent les icônes de la suite, y compris la barre d'outils flottante du Montage et les menus. (PR #287 · commit 99a298fd · G1)
- [x] **Photolab en icônes Glyph** : Les 45 outils, menus volants, calques, panneaux et menus du Photolab passent à la suite (289 emplacements) ; le Doigt garde son pointeur ; Nouveau groupe = nouveau dossier, Position a son icône. (PR #283 · commits cbf8f761, 6e56a3ba · G4)
- [x] **Spritelab et Tilelab en icônes Glyph** : En-têtes, onglets, exports, éditeur, hitboxes, squelette et peintre passent à la suite (124 emplacements) ; la loupe se pose dans les champs de recherche ; les boutons à icône seule sont annoncés aux lecteurs d'écran. (PR #282 · commits d7bf9db3, 6d5c35f0 · G5)
- [x] **Suite d'icônes Deepotus Glyph** : Une suite unique de 526 icônes dessinées (une par fonction) remplace emojis et glyphes disparates dans toute l'app. (PR #281 · commits 0ab48c7f, a30c5a2b · G0)
- [x] **Vectorlab en icônes Glyph** : Outils, menus volants, panneaux, calques, dialogues et barre d'état du Vectorlab passent à la suite (288 emplacements) ; Paramètres de l'appli a sa propre icône, distincte de Configuration du document ; Sans fond et Sans contour ont chacun la leur. (PR #284 · commits 1d7ed331, e284b254, 9f8a06d7 · G3)
**Aide didactique intégrée** — accès : Dans le Vectorlab, le Sprite Lab, le Tile Lab et le Photolab : laisser le pointeur 900 ms sur une option, ou cliquer le petit bouton « ? » à côté

- [x] **Fiche Vectorlab « Conique »** : La couleur tourne autour du milieu de la forme comme les rayons d'une roue. — *Apparence → dégradé Conique* (commit 799a21c4)
- [x] **Fiche Vectorlab « Contour sombre »** : Un trait sombre entoure le dessin pour qu'il se détache du fond. — *Persona Pixel → Contour sombre* (commit fb9c82ef)
- [x] **Fiche Vectorlab « Créer le calque pixel »** : Une feuille transparente se pose sur l'image modèle pour dessiner case par case. — *Persona Pixel → Créer le calque pixel* (commit 9003a19d)
- [x] **Fiche Vectorlab « Dépouille des flancs »** : Les côtés de la pièce penchent : le bas s'élargit, le haut rétrécit. — *Dialogue Impression 3D → Dépouille des flancs* (commit 9003a19d)
- [x] **Fiche Vectorlab « Désigner comme modèle »** : L'image pâlit, se fige et reçoit une grille de cases pour guider. — *Persona Pixel → Désigner comme modèle* (commit 799a21c4)
- [x] **Fiche Vectorlab « Pixeliser l'image »** : L'image devient de gros carrés, autant que la taille de tuile. — *Persona Pixel → Pixeliser l'image* (commit 799a21c4)
- [x] **Fiches animées à trois temps** : Un encart montre le titre de l'option, une phrase simple et une animation faite de vraies captures : départ, geste, résultat. — *Survol long (900 ms) ou bouton « ? »* (commits 8e3be59f, 8d973546)
- [x] **Aide étendue au Sprite Lab et au Tile Lab** : Les fiches s'ouvrent aussi dans le Sprite Lab et le Tile Lab, même sur un bouton désactivé. (PR #256 · commit eeb2f539 · t126)
- [x] **Fiche Sprite Lab « Auto-détecter »** : L'outil compte les images de la planche et dessine une case autour de chacune. — *Feuille → Auto-détecter* (PR #256 · t126)
- [x] **Fiche Sprite Lab « Contour »** : Un trait entoure le personnage pour qu'il se voie sur tout fond. — *Post-traitement → Contour* (PR #256 · t126)
- [x] **Fiche Sprite Lab « Miroir »** : Le personnage se retourne comme dans un miroir. — *Préviz → ⇋* (PR #256 · t126)
- [x] **Fiche Sprite Lab « Ombre X / Y »** : Une ombre décalée se pose derrière le personnage. — *Post-traitement → Ombre X / Y* (PR #256 · t126)
- [x] **Fiche Sprite Lab « Pieds »** : Tous les personnages posent les pieds à la même hauteur. — *Feuille → Alignement → Pieds* (PR #256 · t126)
- [x] **Fiche Sprite Lab « Pixel-art (9b) »** : Le dessin devient de gros carrés et peu de couleurs, comme un vieux jeu vidéo. — *Case Pixel-art (9b)* (PR #256 · t126)
- [x] **Fiche Tile Lab « Forme »** : La tuile devient un losange ou un hexagone. — *Mode Formes → Forme* (PR #256 · t126)
- [x] **Fiche Tile Lab « Grille de placement »** : Les cases deviennent des losanges en quinconce. — *Feuille de tuiles → Grille de placement* (PR #256 · t126)
- [x] **Fiche Tile Lab « Jeu »** : Choisir 47 morceaux pour des coins ronds ou 16 pour aller vite. — *Mode Jeu → Jeu* (PR #256 · t126)
- [x] **Fiche Tile Lab « Méthode »** : Miroir plie la texture en quatre : les bords se touchent toujours parfaitement. — *Mode Seamless → Méthode* (PR #256 · t126)
- [x] **Fiche Tile Lab « Nouvel aperçu »** : Une nouvelle carte se dessine au hasard pour voir si les tuiles vont ensemble. — *Mode Jeu → Nouvel aperçu* (PR #256 · t126)
- [x] **Fiche Tile Lab « Rendre seamless »** : La texture se raccorde : posée côte à côte, on ne voit plus les jointures. — *Mode Seamless → Rendre seamless* (PR #256 · t126)
- [x] **Fiche Vectorlab « Courbes »** : Des lignes relient les endroits de même hauteur sur la carte. — *Panneau Carte réelle → Courbes* (PR #256 · t126)
- [x] **Fiche Vectorlab « Découper »** : La carte devient des cases à six côtés colorées selon la hauteur. — *Panneau Carte réelle → Découper* (PR #256 · t126)
- [x] **Fiche Vectorlab « En cadre »** : Une longue ligne de texte rentre dans une boîte et passe à la ligne toute seule. — *Apparence → texte En cadre* (PR #256 · t126)
- [x] **Fiche Vectorlab « Motif »** : La forme se remplit de petits traits répétés. — *Apparence → Motif* (PR #256 · t126)
- [x] **Fiche Vectorlab « Sur chemin »** : Les mots suivent la ligne tracée. — *Apparence → texte Sur chemin* (PR #256 · t126)
- [x] **Fiche Vectorlab « Transparence »** : La forme s'efface doucement d'un côté à l'autre. — *Apparence → Transparence* (PR #256 · t126)
- [x] **Fiche Photolab « Baguette magique (W) »** : Un clic choisit toute la tache d'une couleur. — *Outil Baguette magique* (PR #267 · t140)
- [x] **Fiche Photolab « Espace de travail »** : Choisir un espace range panneaux et outils pour la tâche voulue. — *Liste des espaces de travail* (PR #269 · commit 8b26219d · t151)
- [x] **Fiche Photolab « Noir et blanc »** : Un clic pose un calque qui retire les couleurs, retirable à tout moment. — *Calque de réglage Noir et blanc* (PR #267 · commit b810b242 · t140)
- [x] **Fiche Photolab « Pinceau (B) »** : Glisser peint un trait de la couleur choisie. — *Outil Pinceau* (PR #268 · commit 7dc1700b · t155)
- [x] **Fiche Photolab « Recadrage (C) »** : Tracer un cadre puis Entrée : le hors-cadre disparaît. — *Outil Recadrage* (PR #267 · t140)
- [x] **Fiche Photolab « Sélection rectangulaire (M) »** : Glisser trace un rectangle en pointillés autour de la zone à modifier. — *Outil Sélection rectangulaire* (PR #267 · t140)
- [x] **Fiche Photolab « Tampon de duplication (S) »** : Alt-clic sur la source puis peindre ailleurs pour recopier ce morceau d'image. — *Outil Tampon de duplication* (PR #268 · t155)

### Raccourcis clavier (`raccourcis`, lot t181, reprend : nouveau) — 0 manques


### Dépannage (`depannage`, lot t181, reprend : c14) — 0 manques

À corriger dans l'ancien texte :

- [ ] TOC « Dépannage & recettes » vs h2 « Dépannage » (incohérence interne)
- [ ] Emoji 🍳 dans les 4 titres de recettes ; 🔥 dans la recette A
- [ ] Badge « v1.15.6 » sur la recette D
- [ ] « Aucune clé Anthropic ni modèle Ollama (chapitres 11–12) » : ignore OpenAI/Gemini et renvoie au chap. 12 (comptes) au lieu du 11
- [ ] Écran News décrit seulement dans la recette C (filtre, score, mémoire, chaîne #33-35 non décrits)
- [ ] « Create image », « Send now », « Refresh », « Build script », « Build illustration », « Send to Scheduler » (anglais)


## Répartition par lot

| Lot | Fonctions | Écrites |
|---|---|---|
| t168 | 0 | 0 |
| t170 | 46 | 46 |
| t171 | 82 | 82 |
| t172 | 78 | 78 |
| t173 | 41 | 0 |
| t174 | 119 | 0 |
| t175 | 32 | 0 |
| t176 | 275 | 0 |
| t177 | 221 | 0 |
| t178 | 102 | 0 |
| t179 | 56 | 0 |
| t180 | 42 | 0 |
| t181 | 0 | 0 |
