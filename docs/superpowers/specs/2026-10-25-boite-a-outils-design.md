# Boîte à outils de l'agent : clients et canaux, WhatsApp, scan, capture et live — spec de conception

Date : 25/10/2026. Branche `chantier/boite-a-outils` (base `origin/main` e0d6e51e). Partie mobile : worktree
`C:\Users\olivi\deepotus-mobile-boite`, branche `chantier/boite-a-outils` tirée de `chantier/l4-socle` (c8eacc3),
spec jumelle `docs/superpowers/specs/2026-10-25-boite-a-outils-mobile-design.md`.

Les décisions de l'utilisateur sont marquées **(utilisateur)**. Celles de Claude sont marquées **(choix de Claude)**
et sont reprises au §12 pour être vérifiées à la relecture.

## 1. Intention

L'utilisateur prépare sa stratégie marketing à venir. Il veut que l'application ait **déjà** les fonctions et les
sécurités qu'elle demandera (utilisateur) :

1. **Des tiers.** Chaque utilisateur doit pouvoir gérer, pour des **clients tiers**, leur communication ou la
   création de leurs produits. Il doit aussi pouvoir gérer ses propres marques et les autres produits qu'il
   fabrique. Quand on crée une marque, un produit ou un client, on enregistre ses **canaux de diffusion** dès la
   création, et on vérifie qu'ils sont réellement utilisables. Chacun a ses **projets**, qu'on sélectionne
   séparément et qui sont orientés vers **ses** canaux.
2. **Le compagnon mobile** fait la même chose. L'utilisateur y travaille en ce moment.
3. **L'auto-promotion de l'app** par ses utilisateurs : sur PC comme sur mobile, ils enregistrent l'écran de l'app
   façon streaming. On voit l'écran, on entend la voix et le commentaire, on enregistre les clics, et la caméra de
   l'utilisateur peut apparaître dans un encart flottant s'il l'accepte. L'habillage se modifie comme un **skin de
   chaîne YouTube**. On peut aussi **diffuser en direct** sur Twitch, YouTube, Discord, etc. Les clics enregistrés
   enrichissent l'**agent tutoriel** de l'app et le partage avec la communauté.
4. **Le scan.** Une photo de page de livre devient un texte exploitable par l'agent Chapitres ou l'Atelier. Une
   photo d'illustration ou de schéma devient la base d'une animation motion. Depuis une inspiration, on
   **refabrique un contenu neuf** et on le poste, à l'aide des outils de la boîte de l'agent. On ne republie pas
   l'original (utilisateur).
5. **Un agent WhatsApp**, sur PC et sur mobile. WhatsApp devient un **canal** qu'on ajoute et qu'on règle par
   produit, marque ou client (utilisateur, d'après le post Instagram de tessa.fairbrook : Kapso branche Claude sur
   l'API officielle de WhatsApp).

Le tout est rangé dans une **boîte à outils propre à chaque fonctionnalité**. Ce sont les outils que l'agent de
l'app peut employer (utilisateur).

## 2. Objectifs, non-objectifs, anti-objectifs

**Objectifs**
- Un **type d'espace** (marque, produit, client), avec une fiche client et un assistant de création qui enregistre
  et vérifie les canaux.
- Des **projets reliés à des canaux** : tout ce qui naît d'un projet vise ses canaux par défaut.
- Deux modes de publication pour un client, réglés client par client (utilisateur : « les deux doivent être
  possibles ») :
  - **validé par le client** : rien ne part sans son accord daté ;
  - **publié par l'utilisateur en son nom**, après une confirmation qui nomme le client.
- **WhatsApp** comme sixième plateforme de `comptes.py`, avec un agent par numéro, réglé par espace.
- Une **boîte Scan** : lecture du texte, mise en calques d'une illustration, et passage de l'inspiration au contenu
  neuf.
- Une **boîte Capture** : enregistrement de l'app avec voix, clics, encart caméra et skin modifiable, et **live**
  multi-destinations.
- Une **boîte à outils de l'agent**, découpée par fonctionnalité, servie au PC et au téléphone.

**Non-objectifs (ce chantier)**
- Pas de multi-utilisateur ni de comptes en ligne : un seul utilisateur par instance (AGENTS.md).
- Pas de serveur à nous. Les services tiers (Kapso, Meta, plateformes de live) sont appelés directement avec les
  clés du coffre.
- Pas de validation par un **lien hébergé** chez nous, ce qui reprend le non-objectif du lot 4 mobile. La validation
  passe par WhatsApp, par le partage natif ou par le compagnon.
- Pas d'enregistrement de tout le bureau Windows : la capture se limite à l'app (choix de Claude, §8.1).
- Pas de diffusion **vidéo** vers Discord par API, car Discord n'a pas d'entrée publique pour un flux (§8.6).

**Anti-objectifs (échec même si « ça marche »)**
- Un post qui part sur le canal d'un autre espace, ou un client publié sans son consentement noté.
- Un message WhatsApp envoyé hors des règles de Meta (pas d'accord du contact, texte libre après 24 h de silence).
- Une capture ou un live qui montre une clé, un jeton, le coffre ou un champ secret.
- La caméra ou le micro allumés sans geste visible et sans témoin à l'écran.
- Un contenu « neuf » qui recopie l'inspiration : un texte quasi identique, ou une illustration d'un autre
  republiée telle quelle.
- Un outil de l'agent qui publie, dépense, change l'espace actif ou lit un secret.

## 3. Contraintes

Celles du dépôt (`AGENTS.md`) s'appliquent toutes :
- FastAPI dans `backend/app` ;
- un bundle SPA **patché**, jamais reconstruit (`scripts/patch_bundle_<tag>.py`, `repatch_all.py`) ;
- des labs autonomes ;
- `dzT` pour toute chaîne visible, en FR et EN ;
- `plafonds.verifier` sur toute route payante ;
- le coffre en localhost ;
- le TDD, les mutations et la preuve sur 8799, **jamais 8765** ;
- l'installation vérifiée par `git hash-object` ;
- une PR par lot.

Contraintes propres au chantier :
- **Garde réseau** : les écritures ne sont ouvertes qu'en boucle locale (`_garde_ecritures_locales`). Toute
  écriture ouverte au téléphone entre une par une dans `_ECRITURES_OUVERTES`, avec ses bancs.
- **Espace** : on n'appelle jamais `espaces.lire()` depuis une boucle de fond, car il migre et écrit (piège t210).
  L'espace d'un post ou d'un projet est **son** espace, jamais l'actif par défaut.
- **Agent** : la règle de t285a tient toujours : la liste des outils est la liste des droits. Les contenus lus
  (documents, pages, OCR, messages WhatsApp) reviennent **encadrés** (`<<<PREUVE … PREUVE>>>`).
- **Navigateur de l'app** : la SPA tourne dans un navigateur Chromium (`deepotus.localhost:8765`). Element Capture
  (`RestrictionTarget.fromElement`, `track.restrictTo`) demande une **auto-capture** de l'onglet. Il faut le
  vérifier sur la version d'Edge ou de Chrome réellement lancée.

## 4. La boîte à outils de l'agent (socle)

Aujourd'hui, `agent_outils.OUTILS` est une table plate de dix outils pour l'agent Campagnes. On la range en
**boîtes**, une par fonctionnalité (utilisateur : « une boîte à outils spécifique à chaque fonctionnalité »).

- **Module** `services/agent_boites.py` (choix de Claude). Une boîte déclare :
  - un `id` ;
  - un libellé `dzT` ;
  - ses outils, chacun avec sa `nature` (lecture | écriture | carte) ;
  - les **écrans ou agents qui y ont droit** ;
  - un drapeau `mobile` (servie dans le paquet agent ou non).
- **Les boîtes de départ :**

| Boîte | Outils (nature) | Agents |
|---|---|---|
| `campagnes` | les dix outils actuels, inchangés | Campagnes |
| `clients` | `lire_fiche_client` (L), `lire_canaux` (L), `lire_projets` (L), `preparer_validation` (carte), `proposer_canaux_projet` (carte) | Campagnes, WhatsApp |
| `scan` | `lire_texte_image` (L), `calques_illustration` (carte, devis si payant), `angles_inspiration` (L), `deviser_contenu_neuf` (carte) | Campagnes, Chapitres, Atelier |
| `whatsapp` | `lire_conversation` (L), `rediger_reponse` (carte), `choisir_modele` (carte), `proposer_creneaux` (L), `remettre_a_l_humain` (carte) | WhatsApp |
| `capture` | `lire_piste_clics` (L), `proposer_decoupe` (carte), `proposer_chapitres_tuto` (carte) | Campagnes, Tutoriel |

- **Aucun outil ne publie, ne dépense, n'envoie un message, n'active une caméra ni ne lance un live.** Ces gestes
  restent des boutons de l'écran, que l'outil prépare sous forme de **carte**, comme pour `deviser_generation`.
- La **fiche « Générer »** de l'agent et `docs/agent/AGENT.md` listent les outils par boîte, et
  `connaissance-agent` les tient à jour. Le banc `test_agent_boites` fige deux choses : chaque outil a une boîte,
  et aucune boîte n'expose de nature hors des trois.
- **Compatibilité** : `agent_outils.definitions()` rend la même liste qu'aujourd'hui pour l'agent Campagnes, à
  l'octet. Un banc fige ce résultat avant tout changement.
- **Mobile** : le paquet agent de t286 transporte les boîtes marquées `mobile`, avec leurs définitions et leurs
  prompts. Sur le téléphone, les mêmes outils lisent les données du téléphone, ou celles du PC quand il est
  joignable.

## 5. Chantier A — Clients, produits, marques et leurs canaux

### 5.1 Ce qui existe (relevé à e0d6e51e)
- `services/espaces.py` : nom, couleur, kit, archive, persona v2, contenus. **Pas de type.**
- `services/comptes.py` : plateformes x, telegram, youtube, instagram, tiktok. Un compte = un espace. Les secrets
  sont dans `DZC_<ID>_<CHAMP>` au coffre.
- `scheduled_posts.espace_id/comptes` et la **garde 409** sur un compte d'un autre espace (t204).
- `library_projects` : `espace_id` et projet actif par espace (t209). **Pas de canaux.**
- Les comptes se règlent dans Réglages, pas pendant la création d'un espace.

### 5.2 Type d'espace et fiche client
- Nouveau champ `type` ∈ {`marque`, `produit`, `client`}. La migration met `marque` sur l'existant, avec Deepotus
  migré à l'octet. Un `produit` peut avoir un **parent** (marque ou client) : il hérite alors du kit et du persona
  par défaut (choix de Claude).
- Le type `client` ajoute une **fiche** (`DATA_ROOT/espaces/<id>/client.json`, liste blanche de `chemin()`) :
  - société, contact principal (nom, e-mail, WhatsApp), pays, langue, notes ;
  - **mode de publication** : `valide_par_client` | `publie_en_son_nom` ;
  - **consentements datés** : un par canal, avec ce qui est permis, la date et le moyen (écrit, WhatsApp, au doigt
    sur le compagnon) ;
  - les **révocations**, qui sont datées elles aussi.
- La fiche ne contient **jamais** de secret. Elle entre dans l'export `.zip` (t210) et l'import la valide.
- Le format de la fiche est **celui du compte client mobile** (§6.4 du lot 4) : le téléphone écrit et le PC lit le
  même document. Le constructeur aligne les deux avant d'écrire.

### 5.3 Assistant de création avec canaux
L'écran « Nouvel espace » devient un assistant en quatre temps :
1. **Type et identité** : nom, couleur, kit, parent.
2. **Fiche** (client seulement).
3. **Canaux** : on coche les plateformes. Pour chacune, l'assistant montre les **champs requis** (`PLATEFORMES` de
   `comptes.py`) et le mode de connexion (clés ou OAuth). Un bouton **Vérifier** appelle un **test sans
   publication** par plateforme :
   - X : `users/me` ;
   - Telegram : `getMe` puis `getChat` ;
   - YouTube : `channels?mine=true` ;
   - Instagram : `/{ig-id}?fields=username` ;
   - TikTok : `user/info` ;
   - WhatsApp : lecture du numéro (§6).

   Le résultat (vert, orange avec la raison, rouge) est enregistré avec sa date. Un canal non vérifié reste
   enregistrable, mais il est marqué « non vérifié », et le Planificateur le signale.
4. **Récapitulatif** : canaux vérifiés, mode de publication, consentements manquants.

Pour un client, chaque canal demande un **consentement daté** avant d'être utilisable en publication (§5.5).

### 5.4 Projets orientés vers leurs canaux
- `library_projects` gagne `canaux` : une liste d'ids de comptes **de son espace**. Le serveur refuse un compte
  d'un autre espace (409, comme t204).
- Tout ce qui naît dans un projet hérite de ses canaux comme **cibles par défaut** :
  - un brouillon du Planificateur, une carte de l'agent ou un post créé depuis la Bibliothèque ;
  - un contenu neuf issu du scan (§7) ;
  - un clip issu d'une capture (§8).
- Un **sélecteur de projet** montre, à côté de chaque projet, son espace (pastille de couleur) et ses canaux
  (icônes Glyph).
- Le Planificateur filtre par espace, puis par projet.

### 5.5 Sécurités
- **Bandeau « pour qui »** : sur les écrans qui produisent ou publient (Quick, Studio, Planificateur, Bibliothèque,
  Capture), on rappelle en permanence l'espace et le projet en cours, avec la couleur de l'espace. Dans un espace
  `client`, un liseré est ajouté (choix de Claude).
- **Mode `valide_par_client`** :
  - Un post est créé en état **« à valider »**. Le bouton « Envoyer au client pour validation » part par WhatsApp
    (boutons interactifs Valider ou Corriger, §6.4) ou par le partage natif du compagnon.
  - La réponse est **datée et rangée** dans la fiche.
  - Le Planificateur **refuse** de programmer un post « à valider ». Un refus 409 nomme le client.
- **Mode `publie_en_son_nom`** : à la programmation, une confirmation nomme le client et le canal. Elle doit
  s'appuyer sur un consentement daté **en cours** pour ce canal, sinon c'est un refus 409.
- **Révocation** : révoquer un consentement met en pause les posts programmés sur ce canal, comme l'archivage de
  t210.
- **Journal** : toute publication, validation ou révocation d'un client est notée (qui, quoi, quand, canal) et
  lisible dans la fiche.
- La garde 409 de t204 reste la dernière ligne de défense, côté serveur.

## 6. Chantier B — WhatsApp, canal et agent

### 6.1 Fournisseur
- **Kapso** (choix de Claude, d'après le post de l'utilisateur) :
  - c'est une surcouche de l'**API officielle WhatsApp Cloud** de Meta ;
  - l'offre gratuite donne 2 000 messages par mois et un numéro ; l'offre Pro coûte 25 $ par mois pour
    100 000 messages ;
  - les frais des **modèles de message** sont facturés **à part par Meta**, sur le compte Meta Business de
    l'espace.

  Kapso résout ce que le PC ne peut pas faire seul : **recevoir** les messages. L'API de Meta pousse vers un
  webhook public, or le PC reste fermé au réseau (`HOST=127.0.0.1`). Kapso garde donc le webhook, et le PC (ou le
  téléphone) **lit** les messages entrants par l'API de Kapso, puis envoie par elle.
- **Adaptateur** `services/whatsapp.py`, avec un pilote `kapso`. Un pilote `meta_direct` est prévu dans
  l'interface mais pas écrit : il demanderait un tunnel, renvoyé à plus tard comme le tunnel du lot 4.
- **Plateforme `whatsapp` dans `comptes.py`** :
  - secrets : `KAPSO_API_KEY` ;
  - publics : `WHATSAPP_NUMERO`, `WHATSAPP_PHONE_ID` ;
  - le rattachement à un espace est obligatoire ; un numéro = un espace.
- **Comptes Kapso et Meta par client (utilisateur, 25/10)** : chaque client fournit **son** compte Kapso et
  **son** compte Meta Business. Il a son numéro et paie ses modèles de message. Vos marques et produits utilisent
  vos comptes. `KAPSO_API_KEY` est donc rangée **par compte** (`DZC_<ID>_KAPSO_API_KEY`), jamais en clé plate
  unique. Les 2 000 messages gratuits ne sont pas partagés, et le plafond se compte par espace. L'arrivée d'un
  numéro client fait partie de l'assistant de création (§5.3) : le client crée son compte Kapso, relie son numéro
  et confie sa clé, avec un consentement daté.
- **Coûts** : chaque envoi passe par un devis et `plafonds.verifier`. Les modèles sont chiffrés d'après la grille
  de Meta saisie dans `pricing` (catégorie et pays), jamais en dur. Un prix inconnu est refusé.

### 6.2 Agent WhatsApp par espace
- Un agent par numéro, avec :
  - le **persona de l'espace** ;
  - les **mots interdits** ;
  - ses **rôles** cochés : FAQ produit, prise de rendez-vous, prise de commande ou de demande, validation client
    (§6.4) ;
  - ses **horaires** ;
  - un **message hors horaires**.
- Il ne voit que la boîte `whatsapp` et, en lecture, les boîtes `clients` et `scan`. Il n'a aucun outil pour
  publier, payer ou lire un secret.
- **Mode de réponse** (choix de Claude, réglable par agent) :
  - `brouillon` (par défaut) : l'agent rédige, l'utilisateur envoie d'un geste, sur PC ou sur mobile ;
  - `auto` : il répond seul, dans les limites listées au §6.3.
- **Hors ligne** (PC et téléphone éteints) : un **message d'absence** réglé chez Kapso répond. Les messages
  attendent ensuite la reprise et sont relus dans l'ordre. Faire tourner l'agent chez Kapso, PC éteint, est noté
  comme option future, car les données sortiraient alors de chez l'utilisateur (§12).

### 6.3 Règles WhatsApp (dures, côté serveur)
- **Accord du contact** : on n'envoie pas de premier message à un numéro sans accord enregistré (date, source).
  Une demande entrante vaut accord pour la conversation.
- **Fenêtre de 24 h** : au-delà de 24 h depuis le dernier message du contact, seuls des **modèles approuvés**
  partent, et le serveur refuse le texte libre.
- **Arrêt** : « STOP » (et ses équivalents FR et EN) coupe les envois au contact et le note.
- **Limites du mode `auto`** :
  - un plafond de messages par jour et par contact ;
  - le passage à l'humain sur un mot-clé, un sentiment négatif ou une demande d'argent ;
  - jamais de prix ou d'engagement hors de la fiche produit.
- Chaque message est **journalisé** par espace.

### 6.4 Validation client par WhatsApp
- Pour un espace `valide_par_client`, « Envoyer pour validation » envoie au contact WhatsApp de la fiche un
  **modèle** qui contient l'aperçu (image, ou vidéo courte avec un lien vers le fichier joint) et deux boutons,
  **Valider** et **Corriger**.
- La réponse change l'état du post, avec la date et le numéro. « Corriger » ouvre une note qui revient à l'agent
  Campagnes.

### 6.5 Écrans
- **PC** :
  - une nouvelle page **WhatsApp** : conversations par espace, brouillons de l'agent, reprise en main, modèles,
    accords ;
  - les réglages de l'agent dans Réglages › Espaces › *espace* › WhatsApp.
- **Mobile** : la spec jumelle traite des notifications de conversation à reprendre, de la réponse en un geste et
  de la validation client.

## 7. Chantier C — Scan : texte, illustration, inspiration → contenu neuf

### 7.1 Entrées
- **PC** : déposer ou coller une image (ou plusieurs pages) dans une **boîte Scan**, ouverte depuis l'Atelier, les
  Chapitres, le Vectorlab, Quick ou la barre de l'agent.
- **Mobile** : Capter (§6.2 et §6.3 du lot 4). Le téléphone fait la lecture sur l'appareil, puis envoie au PC par
  la file.

### 7.2 Page de livre → texte exploitable
- **Lecture locale gratuite** sur PC : **Windows.Media.Ocr**, intégré à Windows 10 et 11, hors réseau, appelé par
  un petit pont Python (choix de Claude, à mesurer contre Tesseract sur 10 pages réelles FR et EN). Le **modèle de
  vision de Claude** sert de **secours payant**, avec son devis, pour les pages difficiles (colonnes, écriture
  manuscrite, faible contraste).
- **Nettoyage** :
  - recoller les césures ;
  - remettre les colonnes dans l'ordre ;
  - ôter les numéros de page et les titres courants répétés ;
  - garder les sauts de paragraphe ;
  - marquer les mots incertains (confiance basse) pour qu'on les relise.
- **Sorties** :
  - vers l'**Atelier** par la route existante (`/atelier/manuscript`), au format du PC ;
  - vers **Chapitres**, où `manuscript_agent.segment_chapters` propose le découpage.

  Jamais de format parallèle.

### 7.3 Illustration ou schéma → base d'animation motion
- On **détoure** (`detourage.py`), puis on **vectorise** (moteur du Vectorlab, `mod-image.js`). On obtient des
  **calques nommés** : formes, flèches, étiquettes (texte reconnu par la même lecture). Le résultat est un document
  du Vectorlab.
- Depuis ce document, on l'envoie vers **Animation** : le chorégraphe et le rendu motion code (t238) reçoivent les
  calques comme éléments animables. Pour un schéma, on propose un **ordre de révélation** qui suit les flèches
  (choix de Claude).

### 7.4 Inspiration → contenu neuf (utilisateur : refabriquer, pas republier)
1. L'agent lit la capture **encadrée comme preuve** et en extrait la **matière** : idées, structure, ton,
   composition, palette, et pour un schéma, la logique.
2. Il propose **trois angles neufs** dans la voix de l'espace, en respectant le persona et les mots interdits.
3. L'utilisateur en choisit un. Une **carte de devis** apparaît (`deviser_contenu_neuf`) : texte, visuel fal,
   animation selon le cas.
4. La génération se fait au clic. Le résultat devient un **brouillon** du projet en cours, qui vise ses canaux
   (§5.4) et respecte le mode de validation du client (§5.5).
5. **Gardes anti-copie** :
   - Texte : on refuse un brouillon dont une suite de plus de 12 mots reprend la capture. Une mesure de proximité
     est affichée (choix de Claude pour le seuil).
   - Image : l'image captée n'est **jamais** envoyée telle quelle comme visuel du post. Elle peut servir de
     référence de composition, ce qui est noté.
   - La **source** de l'inspiration reste dans la fiche du contenu (Bibliothèque, recette), jamais publiée par
     défaut.

## 8. Chantier D — Capture façon streaming, skins et live

### 8.1 Ce qu'on enregistre (utilisateur)
- **L'écran de l'app** : `getDisplayMedia({ preferCurrentTab: true })`, puis **Element Capture**, restreint à la
  racine de l'app. Barres d'onglets, notifications et autres fenêtres restent hors champ. Si Element Capture
  manque, on garde la capture de l'onglet, et on le dit (choix de Claude).
- **La voix** : `getUserMedia({ audio })`, avec une jauge et la suppression du bruit du navigateur.
- **La caméra**, seulement si l'utilisateur l'accepte : elle apparaît dans un **encart flottant**, déplaçable et
  redimensionnable. Sa forme (cercle, carré, coins vifs) et sa place viennent du skin. Un **témoin** reste visible
  tant que la caméra tourne.
- **La piste des clics** : un journal horodaté (`.dzclics.json`) qui contient, pour chaque clic :
  - la position ;
  - l'**élément cliqué**, identifié par le localisateur du catalogue de l'assistant « Demander »
    (`docs/agent/catalogue`, `ancres.json`) ;
  - l'écran ;
  - le libellé `dzT`.

  On enregistre aussi les changements d'écran et les débuts et fins de génération. **On ne journalise jamais les
  touches tapées.**

### 8.2 Sécurité de la capture
- **Masquage automatique** : tout élément marqué `data-dz-secret` est flouté **dans le rendu et dans le live**.
  Sont concernés les champs de clés, le coffre, les jetons, l'appairage et la page Appareils. Le banc vérifie que
  chaque champ `type=password` et chaque écran du coffre porte cette marque. Pendant une capture, les fenêtres du
  coffre affichent un cache (choix de Claude).
- **Pastille « en direct »** ou « enregistrement » dans la coque, avec un bouton d'arrêt toujours accessible.
- Rien n'est envoyé ailleurs sans geste : l'enregistrement reste local, dans la Bibliothèque, et le live demande
  un clic sur « Passer en direct ».

### 8.3 La scène : un même compositeur pour l'enregistrement et le live
- On compose sur un **canvas** dans la page :
  - la capture de l'app ;
  - l'encart caméra ;
  - les éléments du **skin** (cadre, bandeau, logo, alertes, minuteur, chapitre en cours) ;
  - les **effets de clic** (halo, et zoom en direct, désactivable).
- `canvas.captureStream()` alimente l'enregistrement **et** le live (choix de Claude).
- On garde aussi les **pistes brutes** (écran, caméra, voix, clics) pour le montage après coup.

### 8.4 Montage après coup, façon Screen Studio
D'après le relevé du 25/10 (Screen Studio, Cap, Recordly/OpenScreen, ScreenArc), l'état de l'art est le suivant :
on enregistre le brut **plus une piste d'événements**, puis on calcule le zoom auto, le lissage du curseur et la
mise en page **au rendu**. C'est donc éditable. Notre avantage est de savoir **quel outil** a été cliqué, et pas
seulement où.
- L'éditeur propose :
  - des **zooms automatiques** sur les clics, qu'on peut ajuster (début, fin, niveau) ou supprimer ;
  - les coupes des temps morts (attente d'une génération accélérée ou coupée) ;
  - les **chapitres** tirés des changements d'écran ;
  - un sous-titrage de la voix par le chemin existant ;
  - le choix du **format** : 16:9, 9:16 (recadrage qui suit les zooms) ou 1:1.
- Le rendu passe par ffmpeg et la chaîne existante. Le résultat entre dans la **Bibliothèque** avec sa recette,
  puis dans le **Planificateur**, sur les canaux du projet (§5.4).
- **Recast** (option) : appliquer à l'encart caméra le changement de voix ou d'avatar de l'Avatar live
  (`recast_service.py`), avec son devis.

### 8.5 Skins modifiables, façon chaîne YouTube (utilisateur)
- Un **skin** est un document `DATA_ROOT/skins/<id>.json`, avec ses images. Il est rattaché à un espace ; par
  défaut, on prend celui de l'espace en cours. Il contient :
  - le cadre et le fond ;
  - les couleurs et polices, lues dans le **kit de l'espace** par défaut ;
  - le logo ;
  - le **bandeau titre** (lower third) ;
  - l'**intro** et l'**outro** : cartes de quelques secondes, ou court rendu motion ;
  - l'encart caméra (forme, bord, place, ombre) ;
  - les **alertes** de live (nouvel abonné, message) ;
  - les écrans « on revient tout de suite » et « fin du direct » ;
  - le style des zooms et du curseur.
- Un **éditeur de skin** : aperçu en direct sur une capture d'exemple, glisser-déposer des éléments, et
  quelques skins livrés (sobre, néon, presse, jeu).
- Le **skin Deepotus** livré fait la promotion organique : un petit « Fait avec DeepotusVideo » réglable. Il est
  désactivable, mais actif par défaut (choix de Claude).
- Un skin s'**exporte** et s'**importe** (`.zip`, liste blanche), pour être partagé avec la communauté.

### 8.6 Live multi-destinations (utilisateur : Twitch, YouTube, Discord…)
- **Chaîne technique** (choix de Claude) :
  1. le flux du canvas est encodé dans la page (MediaRecorder, H.264 si le navigateur le donne, sinon VP8 ou VP9) ;
  2. il est envoyé par **WebSocket** au backend local ;
  3. un **ffmpeg** le pousse en **RTMP ou RTMPS** vers chaque destination, en un seul encodage, distribué par le
     muxer `tee` ;
  4. la latence visée est sous 5 s.

  Le backend n'écoute qu'en boucle locale, comme tout le reste.
- **Destinations v1** : **Twitch**, **YouTube Live**, **Kick** et **RTMP personnalisé**, ce qui couvre aussi
  Facebook, LinkedIn et Restream. Les **clés de stream** vont au coffre, rangées par compte de l'espace :
  `twitch` et `youtube_live` deviennent des plateformes de `comptes.py`. YouTube peut créer la diffusion par l'API
  avec l'OAuth déjà en place (à vérifier), sinon on colle la clé.
- **Discord** n'a **pas d'entrée publique** pour un flux vidéo : « Go Live » n'existe que dans le client Discord, et
  les bots ne diffusent pas de vidéo. Ce qu'on fait :
  - à « Passer en direct », un **message d'annonce** part par **webhook Discord** dans le salon choisi, avec le
    lien du live Twitch ou YouTube ;
  - on fournit un guide pour partager la fenêtre de l'app dans Discord à la main.

  On le dit en clair dans l'écran, jamais contourné.
- **Pendant le direct** :
  - santé du flux (débit, images perdues, par destination) ;
  - bouton « Pause écran » (écran « on revient tout de suite ») ;
  - marqueurs de chapitre ;
  - chat de Twitch et YouTube en lecture (option, plus tard).
- **Après le direct** : le fichier enregistré entre dans l'éditeur (§8.4) pour en tirer des clips 9:16.

### 8.7 Vers l'agent tutoriel et la communauté
- La piste des clics (§8.1) se convertit en **brouillon de tutoriel** : étapes nommées (outil, écran, libellé),
  captures des trois temps, phrase courte par étape.
- Ce brouillon nourrit :
  - les **fiches didactiques** du Vectorlab, du Spritelab et du Tilelab (skill `didacticiel-option`) ;
  - les **scènes du guide** (`guide-deepotus`) ;
  - le **catalogue de « Demander »** (`connaissance-agent`), avec un exemple de parcours réel par élément.
- **Partage communautaire** : un export « parcours » (`.dzparcours`) contient la vidéo, la piste des clics et les
  étapes. Il s'importe dans une autre installation, qui rejoue les étapes en surlignant les vrais boutons avec le
  pointeur de « Demander ». La piste ne contient ni texte saisi ni chemin de fichier personnel (choix de Claude).

## 9. Chantier E — Mobile (résumé, détail dans la spec jumelle)
- Il **amende le lot 4** (`2026-10-23-lot4-consultant-design.md`), qu'il ne remplace pas :
  - le compte client du §6.4 gagne le **mode de publication** et les **consentements par canal** (format partagé,
    §5.2) ;
  - les projets avec leurs canaux sont lus depuis le PC.
- **WhatsApp** : conversations à reprendre (notification), réponse ou validation en un geste, et brouillons de
  l'agent. Le téléphone lit et envoie par Kapso avec la clé du coffre, sous la règle D9 du lot 4.
- **Scan** : Capter gagne l'issue « contenu neuf » dans l'Orienteur (§6.3 du lot 4). La lecture sur l'appareil
  (Vision, ML Kit) est déjà prévue en L4.5.
- **Capture** : enregistrement **dans l'app** (ReplayKit en mode app sur iOS, MediaProjection sur Android, par un
  module local Expo comme `dz-pbkdf2`), avec voix, encart caméra frontale et piste des touches. Le montage et le
  skin se font au PC, ou en version simple sur le téléphone.
- **Live depuis le téléphone** : RTMP natif (HaishinKit sur iOS, RootEncoder ou StreamPack sur Android, par un
  module local). Il est **décalé dans un sous-lot tardif**, après la capture.
- **Boîte à outils** : servie par le paquet agent (§4).

## 10. Écritures et lectures PC ouvertes au téléphone (à ajouter, une par une)
Chacune est une tâche PC, avec ses bancs qui figent la liste :
1. lire le type, la fiche et les canaux d'un espace ;
2. écrire une fiche client et ses consentements (prolonge le point 4 du §9 du lot 4) ;
3. lire les projets et leurs canaux ;
4. écrire l'état de validation d'un post ;
5. déposer une capture vidéo avec sa piste de clics (prolonge le point 3 du §9 du lot 4) ;
6. lire les skins ;
7. déposer les accords, les STOP et les envois WhatsApp du téléphone (§11 bis).

## 11. Découpage proposé (lots du suivi, prio 3, numéros à prendre après le dernier t du suivi)

| Ordre | Lot | Contenu | Taille |
|---|---|---|---|
| A0 | Boîtes de l'agent | `agent_boites.py`, Campagnes figé à l'octet, banc, AGENT.md | M |
| A1 | Type d'espace et fiche client | Migration, `client.json`, export et import, API, bancs | M |
| A2 | Assistant de création et vérification des canaux | Assistant en 4 temps (maillon de bundle), tests sans publication par plateforme | L |
| A3 | Projets → canaux | Colonne, garde 409, héritage des cibles, sélecteur | M |
| A4 | Validation client et sécurités | États « à valider », confirmations, révocation, journal, bandeau « pour qui » | L |
| B1 | WhatsApp : canal et adaptateur Kapso | Plateforme, lecture et envoi, règles 24 h, accord, STOP, prix, plafonds | L |
| B2 | Agent WhatsApp et page WhatsApp | Agent par espace, brouillon ou auto, page conversations, validation client par WhatsApp | L |
| C1 | Scan : texte | Windows.Media.Ocr, secours Claude, nettoyage, envoi Atelier et Chapitres | M |
| C2 | Scan : illustration → motion | Détourage, vectorisation, calques, envoi Animation | M |
| C3 | Inspiration → contenu neuf | Angles, devis, brouillon, gardes anti-copie | M |
| D1 | Capture : enregistreur et sécurité | Element Capture, voix, caméra, piste des clics, masquage `data-dz-secret` | L |
| D2 | Skins et éditeur | Format, éditeur, skins livrés, export et import | L |
| D3 | Montage après coup | Zooms auto, coupes, chapitres, formats, rendu, Recast en option | L |
| D4 | Live | WebSocket → ffmpeg → RTMP `tee`, destinations, annonce Discord, santé du flux | L |
| D5 | Tutoriel et parcours partagés | Brouillon de tutoriel, `.dzparcours`, rejeu avec le pointeur | M |
| E* | Mobile | Sous-lots de la spec jumelle, entrelacés avec leurs écritures PC (§10) | — |
| Z | Guide, traduction, catalogue | Chapitres du guide, `dzT` FR et EN, `connaissance-agent` à chaque lot visible | — |

Ordre recommandé : A0 → A1 → A3 → A2 → A4 → B1 → B2 → C1 → C3 → C2 → D1 → D2 → D3 → D4 → D5. Les sous-lots mobiles
suivent leurs prérequis PC. Une session et une PR par lot. On demande l'accord de l'utilisateur avant chaque lot.

## 11 bis. Réponses à la relecture du constructeur (25/10)
- **Où vivent les accès d'un canal client** (choix de Claude, cohérent avec la décision du lot 4 : le client
  connecte lui-même ses réseaux sur le téléphone et ses jetons y restent).
  - Un canal a un **identifiant stable**, `canal_id` = `<plateforme>:<id distant>`, partagé par le PC et le
    téléphone. C'est sur lui que portent consentements, projets et validations.
  - Les secrets vivent **là où le canal a été connecté** : au coffre du PC (`comptes.py`, `DZC_<ID>`), ou au coffre
    du téléphone. Le canal est publié par celui qui détient les secrets. Le PC route un post vers le téléphone par
    la délégation D6 (`delegue_a`) quand le canal est « porté par le téléphone ».
  - Sur un tel canal, « Vérifier » affiche « porté par le téléphone, vérifié le … » d'après la dernière déclaration
    du téléphone (point 11 du §9 du lot 4). Le PC ne demande jamais les jetons.
- **Format de `client.json`** (choix de Claude) : c'est le PC qui le fixe en A1, et L4.2 le reprend. Les sous-lots
  M1 à M3 sont **fondus dans L4.2 et L4.3** au lieu de venir après. M4 à M7 restent après.
- **Vérité de l'état WhatsApp** (choix de Claude) :
  - l'historique des messages et la fenêtre de 24 h se relisent chez **Kapso** avant chaque envoi ;
  - les accords, les STOP et le journal ont le **PC** pour source. Une écriture PC n° 7 est ajoutée au §10 : le
    téléphone y dépose ses accords, ses STOP et ses envois.
  - Avant d'envoyer, le téléphone relit aussi chez Kapso les derniers messages du contact pour y chercher un STOP.
    Si ce n'est pas possible, il refuse d'envoyer.
- **Agents de ce chantier** (choix de Claude) :
  - seules deux boucles d'outils sont branchées : **Campagnes** (existante) et **WhatsApp** (neuve, B2) ;
  - « Tutoriel » désigne l'assistant **Demander** : la boîte `capture` alimente son catalogue (D5), sans boucle
    d'outils neuve ;
  - Chapitres et Atelier reçoivent la boîte `scan` par leurs routes existantes (C1, C2), pas par une boucle d'agent.
  - Les boîtes sont déclarées pour qu'un agent futur s'y branche sans changer leur contrat.
- **Un produit rattaché à un client suit ses règles** (choix de Claude) : il hérite du mode de publication, des
  consentements, du liseré et du journal de son client. Le serveur résout le « client responsable » en remontant au
  parent.

## 12. Choix de Claude à vérifier à la relecture
1. Kapso comme pilote WhatsApp (webhook gardé par Kapso, PC en lecture) ; Meta en direct plus tard, avec un tunnel.
2. Agent WhatsApp en mode `brouillon` par défaut ; `auto` en option avec ses limites ; pas d'agent hébergé chez
   Kapso.
3. Un numéro WhatsApp = un espace.
4. Type `produit` avec un parent facultatif qui transmet kit et persona.
5. Windows.Media.Ocr comme lecture locale (à mesurer contre Tesseract), Claude vision en secours payant.
6. Seuil anti-copie : 12 mots consécutifs.
7. Capture limitée à l'app (Element Capture), pas au bureau entier.
8. Un compositeur canvas commun à l'enregistrement et au live ; pistes brutes gardées pour le montage.
9. Live : WebSocket local → ffmpeg → RTMP `tee` ; Twitch, YouTube, Kick et RTMP personnalisé ; Discord = annonce
   par webhook.
10. Skin Deepotus « Fait avec DeepotusVideo » actif par défaut et désactivable.
11. Piste des clics sans touches ni chemins personnels ; masquage `data-dz-secret`.
12. Live depuis le téléphone dans un sous-lot tardif.

## 13. Laissé au constructeur
- Les endpoints exacts de Kapso et sa pagination : on lit la doc Kapso au moment de construire, jamais de mémoire.
- La grille de prix des modèles WhatsApp de Meta, saisie dans `pricing`.
- La disponibilité d'Element Capture et de l'encodage H.264 de MediaRecorder sur le navigateur réellement lancé.
- Le choix des icônes Glyph (`dz-etat-direct`, `dz-canal-whatsapp`, `dz-canal-twitch`, etc.) selon DESIGN.md §15.
- Le découpage des maillons de bundle : un maillon de queue par lot visible, chaîné selon la règle du dépôt.
