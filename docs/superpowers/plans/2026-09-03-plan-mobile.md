# Application mobile compagnon — plan d'implémentation (lecture B)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faire du téléphone un **second poste autonome** de DeepotusVideoGen — il publie le lot de la semaine quand le PC est éteint, génère par les mêmes moteurs avec les mêmes clés, écrit sous verrou, et rend tout au PC au retour sur le Wi-Fi maison.

**Architecture:** Un **nouveau dépôt** natif multiplateforme (`deepotus-mobile/`, hors de ce dépôt) plus, côté PC : `HOST` réellement configurable jusqu'au lanceur, une table `devices` avec jeton haché, une garde de jeton sur **toute** route quand le client n'est pas loopback, un appairage par QR (adresse LAN + secret à usage unique, 5 minutes), des routes de synchronisation LAN et un Scheduler bicéphale. `_require_localhost` reste **intact** : le téléphone ne lit jamais les clés par le backend ; il les reçoit par l'archive chiffrée de R11 D1.

**Tech Stack:** PC — Python **embarqué stdlib pur + Pillow**, FastAPI/Starlette, SQLAlchemy async + SQLite, bancs autonomes `python tests/test_<x>.py` depuis `backend/`. Mobile — décidé mesuré en tâche 1 (verdict pré-inscrit : **React Native / Expo, dev build**), TypeScript, `expo-secure-store`, `expo-sqlite`, `expo-notifications`, `expo-background-task`, tests `jest-expo`.

---

## Périmètre

Exactement les bacs de **R12** du balayage (`docs/superpowers/plans/2026-09-02-balayage-meilleur-de-sa-classe.md`, `### R12`), dans l'ordre que R12 donne lui-même à sa section « Coût » (« P1+P2 (socle), P3 (premier lot), P4+P5+P6, puis D1–D4 ») :

| Bac | Ce qu'il couvre | Lot |
|---|---|---|
| **P1** | Appairage et jeton d'appareil | Lot 1 |
| **P2** | Archive chiffrée → coffre du téléphone | Lot 1 |
| **P3** | Premier lot : le Scheduler dans la poche | Lot 1 |
| **P4** | Synchronisation LAN au retour | Lot 2 |
| **P5** | Notifications | Lot 2 |
| **P6** | Dépenses | Lot 2 |
| **D1** | Générer dans la poche, ranger au retour | Lot 3 |
| **D2** | Partages entrants triés | Lot 3 |
| **D3** | Écrire hors ligne sous verrou | Lot 3 |
| **D4** | Recette lançable depuis le téléphone | Lot 3 |
| **E1–E5** | Écarté — une ligne chacun, section « Écarté » | — |

**Ce que ce plan ne fait PAS, et à qui cela appartient** — ces sections sont référencées, jamais replanifiées :

- **R11 D1** — le coffre à mot de passe maître et l'**archive chiffrée** (et la décision technique AES : bibliothèque embarquée ou DPAPI par `ctypes`). Ce plan **consomme** l'archive côté téléphone ; il ne la produit pas.
- **R11 P2** — les **plafonds** de dépense côté PC. Ce plan n'ajoute que le plafond journalier **local au téléphone** et la fusion des compteurs.
- **R6 P1** — les trois **adaptateurs automatiques** (Instagram Reels, YouTube Shorts, TikTok Direct Post). Ce plan publie X et Telegram depuis le téléphone ; les trois autres passent par le **partage vers l'app native** tant que R6 P1 n'existe pas.
- **R6 D1** — « le téléphone publie quand le PC est éteint » : R6 le pose, **ce plan l'exécute** (tâches 8 à 11).
- **R9 P2/P3** — **projets** et **lignée** en base. Ce plan écrit un **fichier de recette à côté du fichier déposé** (`<nom>.recette.json`) que R9 P3 consommera ; il n'ajoute aucune colonne de lignée.
- **R3 P2** — **versions du texte** d'un chapitre. Ce plan pose le **verrou** et rien d'autre ; le versionnage est à R3.
- **R1 P1** — « Rouvrir dans Quick, prérempli ». Ce plan écrit la recette dans un format que R1 P1 pourra relire des deux côtés ; il ne touche pas à l'écran Quick.

---

## Architecture B, sans détour

### Ce que le code fait aujourd'hui (relu le 03/09/2026, chemins et lignes)

| Fait mesuré | Où |
|---|---|
| `HOST: str = "127.0.0.1"` et `PORT: int = 8765` | `backend/app/config.py:102-103` |
| Le lanceur livré **ignore** `settings.HOST` : il code en dur `--host 127.0.0.1 --port 8765` | `scripts/launch-silent.vbs:56` |
| `uvicorn.run(..., host=settings.HOST, port=settings.PORT, reload=True)` ne sert **que** le mode développeur `python -m app.main` | `backend/app/main.py:590-597` |
| Garde CSRF : refuse 403 les requêtes **non-GET** dont l'`Origin` n'est pas dans `_ALLOWED_ORIGIN_HOSTS = {"127.0.0.1", "localhost", "::1", ""}` — **une requête SANS en-tête `Origin` passe** (`if origin:` avant le test) | `backend/app/main.py:206`, `:209-221` |
| `_require_localhost` refuse 403 tout client hors `("127.0.0.1", "::1", "localhost", "testclient")` sur les routes de clés | `backend/app/api/routes.py:3547-3553`, appelé 14 fois |
| Les clés vivent en clair dans `.env` sous `DATA_ROOT` ; la liste blanche fait 24 noms | `backend/app/api/routes.py:3501-3517` |
| Aucun appairage, aucun jeton d'appareil, aucune table `devices` | `grep -rn "device" backend/app` → rien de tel |
| La boucle du Scheduler tourne **dans le backend**, tick 60 s : PC éteint, rien ne part | `backend/app/services/marketing.py:849-896` |
| Seuls **Telegram** et **X** ont un adaptateur automatique | `backend/app/services/marketing.py:760-768` |
| `fire_post` réclame le post (`status="posting"`) avant de publier — la double publication est déjà gardée | `backend/app/services/marketing.py:770-790` |
| Une **table neuve** n'a pas besoin d'entrée dans `_auto_migrate` : `create_all` suffit (précédent `LibraryAsset`) | `backend/app/services/storage.py:228-248`, `:533-538` |
| `_auto_migrate` ne sait ajouter que des **colonnes** à des tables listées | `backend/app/services/storage.py:511-531` |
| `PUT /chapters/{chapter_id}` écrase `script_text` sans aucune garde | `backend/app/api/routes.py:5751-5770` |
| `library_index.SOURCES` a 13 clés ; `mobile` n'y est pas | `backend/app/services/library_index.py:24-38` |
| La chaîne de patchs du bundle finit sur `seedance25` (`python scripts/repatch_all.py --list`) | `scripts/repatch_all.py` |
| Le bundle `frontend/dist/assets/index-BEOJX8L5.js` pèse **1 395 299 o**, CRLF=**11884**, LF isolés=**0**, CR isolés=**0** | mesuré le 03/09 |
| Le python EMBARQUÉ est **stdlib pur + Pillow** : ni `cryptography`, ni `zeroconf`, ni `qrcode`, ni `numpy` | `backend/requirements.txt`, rappel R11 |

### Les cinq décisions, et leur mesure

**D-A — Le compagnon est un NOUVEAU dépôt, hors de celui-ci.**
Mesure : ce dépôt embarque déjà un runtime Python, un bundle minifié patché et 22 Mo de catalogue CC0 ; y greffer un projet natif (Gradle, Xcode, `node_modules`) casserait `scripts/build-installer.ps1` et la règle du bundle. Arborescence en tâche 1.

**D-B — `HOST` réellement configurable, jusqu'au lanceur.**
Mesure : `settings.HOST` existe déjà (`config.py:102`) mais le lanceur livré le contourne (`launch-silent.vbs:56`). Changer `config.py` seul ne changerait **rien** sur une machine installée. La valeur par défaut reste `127.0.0.1` : ouvrir le LAN est un geste explicite.

**D-C — La vraie garde est le JETON, pas la garde CSRF.**
Mesure : `main.py:212` teste `if origin:` — une application native n'envoie pas d'`Origin`, donc elle **passe** la garde CSRF aujourd'hui. Ouvrir `HOST` sans jeton exposerait toute l'API à quiconque est sur le Wi-Fi. La garde CSRF est **conservée** (elle protège toujours le navigateur du PC contre une page hostile) ; le jeton est ajouté **par-dessus**.
Mesure de l'ordre : `starlette.applications.Starlette.add_middleware` fait `self.user_middleware.insert(0, ...)` (starlette 0.37.2, `applications.py:142`). Le **dernier** middleware déclaré est donc le **plus extérieur** et s'exécute en **premier**. La garde de jeton se déclare **après** `_csrf_origin_guard` dans `main.py` pour rejeter un client sans jeton avant tout le reste.

**D-D — `_require_localhost` reste intact ; les clés voyagent par l'archive chiffrée.**
Mesure : R12 réponse 5 (« oui, par l'archive chiffrée de Settings (R11 D1) »). Le téléphone ne demande **jamais** `/settings/keys`. Conséquence de conception : l'export du lot (tâche 8) renvoie vidéos, légendes, heures et canaux — **jamais** les jetons X ou Telegram ; ils sont déjà dans le coffre du téléphone.

**D-E — mDNS par le service système, pas par du multicast brut.**
Mesure R12 : « seulement dans mon réseau (Wi-Fi maison) », aucun service tiers. Le PC doit donc **publier** un service `_deepotus._tcp.local.` et le téléphone le **parcourir** par l'API du système (NSNetServiceBrowser / NsdManager). *De mémoire, à vérifier (tâche 15) : iOS exige l'entitlement `com.apple.developer.networking.multicast` pour du multicast/broadcast BRUT, mais seulement `NSLocalNetworkUsageDescription` + `NSBonjourServices` pour Bonjour par l'API système.* Le PC ne peut pas utiliser `zeroconf` (absent du runtime) : le répondeur mDNS est écrit en `socket` stdlib.

---

## Coût

Le coût est répété **tâche par tâche** dans une ligne `**Coût :**`. Vue d'ensemble :

| Poste | Coût | Pourquoi |
|---|---|---|
| Nouveau dépôt `deepotus-mobile/` | **élevé, une fois** — projet natif, deux plateformes, une chaîne de build par store | R12 réponse 7 : natif, iPhone **et** Android |
| Backend : appairage, jeton, `devices`, QR | **moyen** — 3 fichiers neufs, 1 middleware, 1 table neuve (`create_all` suffit) | aucune migration de colonne |
| Backend : routes de synchronisation, verrous, lot | **moyen** — 1 fichier neuf `sync.py`, 1 table neuve `chapter_locks`, 1 garde sur `PUT /chapters` | |
| Backend : répondeur mDNS stdlib | **moyen** — `zeroconf` absent du runtime embarqué, tout est à écrire | mesuré : `requirements.txt` |
| Encodeur QR stdlib | **moyen** — `qrcode` absent ; version 4-L à un seul bloc RS pour éviter l'entrelacement | mesuré : `requirements.txt` |
| **Bundle** : page « Appareils » dans Settings | **UN patch, tag `dzappair`, EN QUEUE après `seedance25`** — 4 ancres mesurées uniques | c'est le seul patch du plan |
| Lanceur `launch-silent.vbs` | **faible** — une ligne, plus une lecture de `.env` | |
| Mobile : Lot 1 | **élevé** — appairage, coffre, file du lot, notifications à l'heure, publication X/Telegram | |
| Mobile : Lot 2 | **moyen** — découverte, transfert repris, notifications, plafond | |
| Mobile : Lot 3 | **élevé** — génération, extensions de partage (une par plateforme), éditeur hors ligne | |

**Le bundle n'est touché qu'une fois.** Règles rappelées de « Pièges hérités » : tag **NEUF**, backup `.js.bak_dzappair`, position **EN QUEUE**, ancre **unique** vérifiée par `count == 1`, `newline=""` partout (CRLF), jamais d'ancre imprimée (cp1252), et `python scripts/repatch_all.py --from dzappair` seulement si un patch aval apparaît un jour.

---

## Références vérifiées

**Vérifiées et datées — reprises de R12 et R6 (03/09/2026), rien d'autre n'a ce statut :**

- **Web Share Target** (recevoir un partage dans une PWA) : Android/Chrome avec PWA installée ; **pas sur iOS Safari** — developer.mozilla.org, web.dev, bugs.webkit.org, 03/09. → l'application est **native** (R12 réf. 1, E3).
- **Web Push iOS** : seulement pour les web apps ajoutées à l'écran d'accueil depuis 16.4, sur geste utilisateur — webkit.org, 03/09. Sans objet en natif, gardé pour mémoire (R12 réf. 2).
- **X API** : palier gratuit **500 posts et 100 lectures par mois** par projet ; Basic 10 000 posts/mois ; Pro 1 M ; Enterprise à partir de 42 k$/mois — docs.x.com, devcommunity.x.com, 03/09 (R6). Les **mêmes bornes** valent depuis le téléphone, avec les **mêmes jetons** (R12 réf. 3).
- **Instagram (Meta)** : publication par l'API réservée aux comptes **professionnels** ; reels publiables en média unique ; **50 posts par 24 h** ; accès Standard pour ses propres comptes — developers.facebook.com, 03/09 (R6).
- **YouTube Data API** : `videos.insert` dans son propre seau de quota, **100 envois par jour** par défaut ; 10 000 unités/jour pour le reste — developers.google.com, 03/09 (R6).
- **TikTok Content Posting API (Direct Post)** : client **non audité** = visibilité **SELF_ONLY**, compte privé obligatoire, 5 utilisateurs par 24 h ; plafond ~15 posts/jour/créateur — developers.tiktok.com, 03/09 (R6).
- **Postiz** : open source, auto-hébergeable, 30+ plateformes, API — postiz.com, github.com, 03/09 (R6). Écarté ici (E2).

**De mémoire, à vérifier — chaque affirmation porte la commande WebFetch qui la mesure, dans la tâche qui en dépend :**

| Affirmation | Vérifiée en | Commande |
|---|---|---|
| iOS ne garantit pas l'exécution d'une tâche de fond à l'heure exacte (BGTaskScheduler) | tâche 9 | `WebFetch url="https://developer.apple.com/documentation/backgroundtasks/bgtaskscheduler" prompt="Does BGTaskScheduler guarantee execution at an exact requested time? Quote the sentences about earliestBeginDate, system discretion and scheduling. List every reason a submitted task can be skipped."` |
| Android permet une exécution à heure fixe (WorkManager, alarmes exactes) | tâche 9 | `WebFetch url="https://developer.android.com/topic/libraries/architecture/workmanager" prompt="Is WorkManager suitable for exact-time execution? Quote what the page says about minimum periodic interval and deferrability."` puis `WebFetch url="https://developer.android.com/develop/background-work/services/alarms/schedule-exact-alarms" prompt="What permission is needed for exact alarms on Android 12, 13 and 14+? Quote SCHEDULE_EXACT_ALARM and USE_EXACT_ALARM eligibility rules and how the user grants them."` |
| iOS : Bonjour par l'API système ne demande que `NSLocalNetworkUsageDescription` + `NSBonjourServices` ; le multicast brut demande un entitlement accordé sur demande | tâche 15 | `WebFetch url="https://developer.apple.com/documentation/technotes/tn3179-understanding-local-network-privacy" prompt="Which Info.plist keys are required to browse Bonjour services? When is the com.apple.developer.networking.multicast entitlement required, and how is it obtained?"` |
| Expo couvre coffre système, SQLite, notifications locales, tâches de fond en modules de premier rang | tâche 1 | six WebFetch listés dans la tâche 1 |
| Flutter couvre les mêmes besoins par des paquets communautaires, mDNS excepté (`multicast_dns`, publié par flutter.dev) | tâche 1 | six WebFetch listés dans la tâche 1 |
| QR version **4**, correction **L** : 33×33 modules, 100 mots de code au total, **20** de correction, **80** de données, **un seul bloc**, capacité mode octet **78** octets | tâche 3 | `WebFetch url="https://www.thonky.com/qr-code-tutorial/error-correction-table" prompt="For QR version 4 with error correction level L: total codewords, EC codewords per block, number of blocks in group 1, data codewords per block. Also give the byte-mode character capacity for 4-L."` |
| L'API publique GitHub `releases/latest` donne version et notes | hors périmètre (R11 P4) | — |

---

## Lot 1 — socle et premier lot (P1 + P2 + P3)

### Tâche 1 : Trancher le cadre mobile, mesuré, et créer le dépôt

**Files:**
- Create: `C:\Users\olivi\deepotus-mobile\` (dépôt NEUF, **hors** de `C:\Users\olivi\DeepotusVideo`)
- Create: `C:\Users\olivi\deepotus-mobile\DECISIONS.md`
- Create: `C:\Users\olivi\deepotus-mobile\src\lib\version.ts`
- Test: `C:\Users\olivi\deepotus-mobile\src\lib\__tests__\version.test.ts`

**Coût :** élevé, une fois. Deux chaînes de build (Gradle + Xcode), deux comptes développeur à terme. Aucun coût sur le dépôt PC : rien n'est écrit dans `C:\Users\olivi\DeepotusVideo`.

- [ ] **Step 1 : Mesurer Expo sur les six besoins**

Lancer ces six WebFetch et **coller les réponses** (une phrase chacune, avec la date du jour) dans un brouillon local :

```
WebFetch url="https://docs.expo.dev/versions/latest/sdk/securestore/" prompt="Which native store backs SecureStore on iOS and on Android? Any size limit per value?"
WebFetch url="https://docs.expo.dev/versions/latest/sdk/sqlite/" prompt="Does expo-sqlite provide a synchronous and an async API? Does it work in a bare/dev build without Expo Go?"
WebFetch url="https://docs.expo.dev/versions/latest/sdk/notifications/" prompt="Can expo-notifications schedule a LOCAL notification at an exact calendar date and time on iOS and Android? What are the stated limitations on each platform?"
WebFetch url="https://docs.expo.dev/versions/latest/sdk/background-task/" prompt="Which OS API backs expo-background-task on iOS and on Android? What is the minimum interval and is exact-time execution guaranteed?"
WebFetch url="https://docs.expo.dev/guides/sharing-data/" prompt="How does an Expo app receive a share from another app on iOS and on Android? Is a native share extension target required on iOS?"
WebFetch url="https://docs.expo.dev/develop/development-builds/introduction/" prompt="What is a development build and why is it required for native modules not included in Expo Go?"
```

- [ ] **Step 2 : Mesurer Flutter sur les six mêmes besoins**

```
WebFetch url="https://pub.dev/packages/flutter_secure_storage" prompt="Which native store is used on iOS and Android? Who publishes the package and what is its current popularity/likes score?"
WebFetch url="https://pub.dev/packages/sqflite" prompt="Who publishes it and what platforms are supported? Is it a Flutter Favorite?"
WebFetch url="https://pub.dev/packages/flutter_local_notifications" prompt="Can it schedule a notification at an exact date and time? Quote what it says about zonedSchedule and androidScheduleMode exactAllowWhileIdle."
WebFetch url="https://pub.dev/packages/workmanager" prompt="Which OS APIs back it on iOS and Android? Is exact-time execution guaranteed on iOS?"
WebFetch url="https://pub.dev/packages/receive_sharing_intent" prompt="What native setup is required on iOS to receive shared content? Is a Share Extension target required?"
WebFetch url="https://pub.dev/packages/multicast_dns" prompt="Who publishes this package? Is it pure Dart, and can it browse Bonjour/mDNS services on iOS and Android?"
```

- [ ] **Step 3 : Écrire la table de décision et TRANCHER**

Créer `C:\Users\olivi\deepotus-mobile\DECISIONS.md` avec exactement cette structure, en remplaçant chaque cellule « (réponse du step 1/2) » par la phrase mesurée :

```markdown
# Décisions du compagnon

## D1 — React Native (Expo) contre Flutter — tranché le <date du jour>

| Besoin mesuré (R12) | Expo / React Native | Flutter | Avantage |
|---|---|---|---|
| Partage entrant iOS | (réponse step 1.5) — extension native requise | (réponse step 2.5) — extension native requise | égalité |
| Partage entrant Android | (réponse step 1.5) | (réponse step 2.5) | égalité |
| Keychain / Keystore | `expo-secure-store`, module de PREMIER RANG (réponse 1.1) | `flutter_secure_storage`, communautaire (réponse 2.1) | Expo |
| Notifications locales à l'heure | `expo-notifications` (réponse 1.3) | `flutter_local_notifications`, `zonedSchedule` + `exactAllowWhileIdle` (réponse 2.3) | Flutter |
| Tâches en arrière-plan | `expo-background-task` (réponse 1.4) | `workmanager` (réponse 2.4) | égalité |
| mDNS / Bonjour | paquet communautaire à bridger | `multicast_dns`, publié par flutter.dev, Dart pur (réponse 2.6) | Flutter |
| SQLite | `expo-sqlite`, premier rang (réponse 1.2) | `sqflite`, communautaire (réponse 2.2) | Expo |
| Compétence déjà là | l'UI du PC est React (frontend/dist, React 18) | rien | Expo |
| Modules de PREMIER RANG couvrant les besoins | 4 sur 6 | 1 sur 6 | Expo |

**Verdict : React Native / Expo, en development build (pas Expo Go).**
Raison, dans l'ordre : (a) quatre des six besoins sont couverts par des modules
de premier rang du framework, contre un pour Flutter ; (b) l'interface du PC est
React, le vocabulaire est déjà celui du propriétaire ; (c) les deux frameworks
exigent la MÊME extension native pour le partage entrant iOS — ce besoin, le
plus coûteux, ne départage pas.

**Ce qui ferait basculer vers Flutter, et rien d'autre** : si le step 1.3 dit
qu'`expo-notifications` ne sait PAS programmer une notification locale à une
date et une heure exactes sur Android — la promesse de P3 en dépend
entièrement. Dans ce cas, reprendre ce plan avec Flutter : les tâches 1, 10,
16, 17 changent d'outil, aucune autre tâche ne bouge (le protocole et le
backend sont indépendants du framework).

## D2 — Les clés ne viennent JAMAIS du backend
Le téléphone lit l'archive chiffrée de R11 D1 et range les clés dans le coffre
système. `_require_localhost` (backend/app/api/routes.py:3547) reste intact.
```

- [ ] **Step 4 : Créer le projet (commandes exactes)**

```bash
cd /c/Users/olivi
npx create-expo-app@latest deepotus-mobile --template blank-typescript
cd deepotus-mobile
npx expo install expo-secure-store expo-sqlite expo-notifications expo-background-task expo-task-manager expo-file-system expo-crypto expo-camera expo-barcode-scanner
npm install --save-dev jest jest-expo @types/jest @testing-library/react-native
npm install oauth-1.0a crypto-js
npm install --save-dev @types/crypto-js
```

Attendu : `create-expo-app` imprime `✅ Your project is ready!`, puis `expo install` imprime une ligne `added N packages` sans `ERESOLVE`.

- [ ] **Step 5 : Câbler jest**

Ajouter dans `C:\Users\olivi\deepotus-mobile\package.json`, dans l'objet racine :

```json
  "scripts": {
    "start": "expo start",
    "android": "expo run:android",
    "ios": "expo run:ios",
    "test": "jest"
  },
  "jest": {
    "preset": "jest-expo",
    "testMatch": ["**/__tests__/**/*.test.ts", "**/__tests__/**/*.test.tsx"]
  }
```

- [ ] **Step 6 : Écrire le test qui échoue**

`C:\Users\olivi\deepotus-mobile\src\lib\__tests__\version.test.ts` :

```typescript
import { PROTOCOLE, userAgent } from "../version";

test("le protocole de synchronisation est versionné", () => {
  expect(PROTOCOLE).toBe(1);
});

test("l'agent nomme l'appareil et la version du protocole", () => {
  expect(userAgent("iPhone de Oli")).toBe("deepotus-mobile/1 (iPhone de Oli; p=1)");
});
```

- [ ] **Step 7 : Lancer le test, vérifier qu'il échoue**

Run : `cd /c/Users/olivi/deepotus-mobile && npm test`
Attendu : ÉCHEC, `Cannot find module '../version'`.

- [ ] **Step 8 : Écrire l'implémentation minimale**

`C:\Users\olivi\deepotus-mobile\src\lib\version.ts` :

```typescript
/** Version du protocole de synchronisation parlé avec le PC.
 *  Le PC renvoie la sienne dans /api/sync/manifeste ; un écart fait
 *  refuser la synchronisation en le DISANT, jamais en la tentant. */
export const PROTOCOLE = 1;

export function userAgent(nomAppareil: string): string {
  return `deepotus-mobile/1 (${nomAppareil}; p=${PROTOCOLE})`;
}
```

- [ ] **Step 9 : Lancer le test, vérifier qu'il passe**

Run : `cd /c/Users/olivi/deepotus-mobile && npm test`
Attendu : `Tests: 2 passed, 2 total`.

- [ ] **Step 10 : Commit (dépôt mobile)**

```bash
cd /c/Users/olivi/deepotus-mobile
git init -b main
git add -A
git commit -m 'socle : projet Expo, cadre tranche, protocole versionne' -m 'Le cadre est tranche sur six besoins MESURES (DECISIONS.md) : Expo couvre
quatre des six par des modules de premier rang, contre un pour Flutter, et
lidiome React est deja celui du PC. La condition qui ferait basculer vers
Flutter est ecrite, pas sous-entendue.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Tâche 2 : Table `devices` et service d'appairage (PC)

**Files:**
- Modify: `backend/app/services/storage.py:248` (juste après la classe `LibraryAsset`, avant `class Chapter`)
- Create: `backend/app/services/appairage.py`
- Test: `backend/tests/test_appairage.py`

**Coût :** faible. **Table neuve** → `create_all` suffit, aucune entrée dans `_auto_migrate` (précédent mesuré : `LibraryAsset`, `storage.py:234`). Aucun patch de bundle.

- [ ] **Step 1 : Écrire le banc qui échoue**

Créer `backend/tests/test_appairage.py` :

```python
# -*- coding: utf-8 -*-
"""P1 — appairage, jeton d'appareil, garde de jeton, QR.

Banc-miroir : il lit la BASE et les OCTETS rendus, jamais le code qui
prétend les produire. Un processus par fichier :

    python tests/test_appairage.py            # depuis backend/
"""
import asyncio
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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _base():
    from app.services.storage import init_db
    asyncio.run(init_db())


def test_la_table_devices_existe_et_a_ses_colonnes():
    """Miroir : on interroge la BASE (PRAGMA), pas le modèle Python."""
    from sqlalchemy import text
    from app.services.storage import _engine
    _base()

    async def lire():
        async with _engine.begin() as conn:
            r = await conn.execute(text("PRAGMA table_info(devices)"))
            return {row[1]: row[2] for row in r.fetchall()}

    cols = asyncio.run(lire())
    assert cols, "table devices absente de la base"
    for nom in ("id", "nom", "jeton_sha256", "cree", "revoque", "vu_le"):
        assert nom in cols, (nom, sorted(cols))


def test_un_secret_est_a_usage_unique_et_expire_en_5_minutes():
    from app.services import appairage
    _base()
    s = appairage.creer_secret()
    assert len(s.secret) == 32 and all(c in "0123456789abcdef" for c in s.secret)
    assert 299 <= (s.expire_a - s.cree_a) <= 301, (s.cree_a, s.expire_a)
    jeton, appareil = asyncio.run(appairage.reclamer(s.secret, "iPhone de Oli"))
    assert len(jeton) == 64
    assert appareil["nom"] == "iPhone de Oli"
    # USAGE UNIQUE : la seconde réclamation est refusée, en le disant
    try:
        asyncio.run(appairage.reclamer(s.secret, "second essai"))
    except appairage.SecretRefuse as e:
        assert "consomme" in str(e), str(e)
    else:
        raise AssertionError("un secret consommé a été accepté deux fois")


def test_le_secret_expire_se_refuse_en_le_disant():
    from app.services import appairage
    _base()
    s = appairage.creer_secret()
    appairage._SECRETS[s.secret]["expire_a"] -= 400   # on vieillit le secret
    try:
        asyncio.run(appairage.reclamer(s.secret, "trop tard"))
    except appairage.SecretRefuse as e:
        assert "expire" in str(e), str(e)
    else:
        raise AssertionError("un secret expiré a été accepté")


def test_le_jeton_nest_jamais_stocke_en_clair():
    """Miroir : on relit la LIGNE écrite, pas la valeur rendue."""
    import hashlib
    from sqlalchemy import text
    from app.services.storage import _engine
    from app.services import appairage
    _base()
    s = appairage.creer_secret()
    jeton, appareil = asyncio.run(appairage.reclamer(s.secret, "tablette"))

    async def lire():
        async with _engine.begin() as conn:
            r = await conn.execute(text(
                "SELECT jeton_sha256 FROM devices WHERE id = :i"),
                {"i": appareil["id"]})
            return r.fetchone()[0]

    stocke = asyncio.run(lire())
    assert stocke != jeton
    assert stocke == hashlib.sha256(jeton.encode()).hexdigest()


def test_cinq_appareils_au_plus():
    from app.services import appairage
    _base()
    asyncio.run(appairage.revoquer_tout())
    for i in range(5):
        s = appairage.creer_secret()
        asyncio.run(appairage.reclamer(s.secret, f"appareil {i}"))
    s = appairage.creer_secret()
    try:
        asyncio.run(appairage.reclamer(s.secret, "le sixième"))
    except appairage.SecretRefuse as e:
        assert "cinq" in str(e), str(e)
    else:
        raise AssertionError("un sixième appareil a été appairé")


def test_la_revocation_est_immediate_pour_la_garde():
    from app.services import appairage
    _base()
    asyncio.run(appairage.revoquer_tout())
    s = appairage.creer_secret()
    jeton, appareil = asyncio.run(appairage.reclamer(s.secret, "à révoquer"))
    assert asyncio.run(appairage.jeton_valide(jeton)) is True
    asyncio.run(appairage.revoquer(appareil["id"]))
    # pas de « dans 5 secondes » : la révocation invalide le cache
    assert asyncio.run(appairage.jeton_valide(jeton)) is False


def test_la_liste_des_consoles_couvre_les_cles_qui_depensent():
    from app.services import appairage
    noms = {c["cle"] for c in appairage.CONSOLES}
    for k in ("FAL_KEY", "HEYGEN_API_KEY", "MESHY_API_KEY",
              "ELEVENLABS_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
              "GEMINI_API_KEY", "X_API_KEY", "TELEGRAM_BOT_TOKEN"):
        assert k in noms, k
    for c in appairage.CONSOLES:
        assert c["url"].startswith("https://"), c


TESTS = [test_la_table_devices_existe_et_a_ses_colonnes,
         test_un_secret_est_a_usage_unique_et_expire_en_5_minutes,
         test_le_secret_expire_se_refuse_en_le_disant,
         test_le_jeton_nest_jamais_stocke_en_clair,
         test_cinq_appareils_au_plus,
         test_la_revocation_est_immediate_pour_la_garde,
         test_la_liste_des_consoles_couvre_les_cles_qui_depensent]

if __name__ == "__main__":
    failed = []
    for t in TESTS:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed.append(t.__name__)
            print(f"FAIL {t.__name__}: {e!r}")
    print(f"\n{len(TESTS) - len(failed)}/{len(TESTS)} OK")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2 : Lancer le banc, vérifier qu'il échoue**

Run : `cd backend && python tests/test_appairage.py`
Attendu : `FAIL test_la_table_devices_existe_et_a_ses_colonnes: AssertionError('table devices absente de la base')` puis six `FAIL ... ModuleNotFoundError("No module named 'app.services.appairage'")`, et la dernière ligne `0/7 OK`.

- [ ] **Step 3 : Ajouter le modèle `Device`**

Dans `backend/app/services/storage.py`, **après** la classe `LibraryAsset` (elle finit ligne 248 par `default=datetime.utcnow)`) et **avant** `class Chapter(Base):` :

```python
class Device(Base):
    """P1 (03/09) — un appareil appairé. Le jeton n'est JAMAIS stocké :
    seul son sha256 l'est, comme un mot de passe. `revoque` non nul =
    l'appareil ne passe plus la garde, immédiatement (le cache de la
    garde est invalidé par la révocation, pas par son TTL).
    Table neuve : `create_all` suffit, aucune entrée dans _auto_migrate
    (même décision que LibraryAsset)."""
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    nom: Mapped[str] = mapped_column(String(60), default="")
    jeton_sha256: Mapped[str] = mapped_column(String(64), index=True)
    cree: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    revoque: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    vu_le: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 4 : Écrire le service d'appairage**

Créer `backend/app/services/appairage.py` :

```python
# -*- coding: utf-8 -*-
"""P1 — appairage d'un appareil, jeton révocable, garde de jeton.

Trois faits mesurés le 03/09 qui commandent tout ce fichier :

1. `main.py:212` fait `if origin:` — une application NATIVE n'envoie pas
   d'en-tête `Origin` et passe donc la garde CSRF. Ouvrir `HOST` sur le
   LAN sans jeton exposerait toute l'API au Wi-Fi. Le jeton est LA garde.
2. `routes.py:3547` (`_require_localhost`) reste INTACT : le téléphone ne
   lit jamais les clés par le backend. Elles lui viennent de l'archive
   chiffrée de R11 D1.
3. Le runtime embarqué est stdlib pur : `secrets`, `hashlib` et `time`
   suffisent — aucune dépendance neuve.
"""
import hashlib
import secrets as _secrets
import time
from dataclasses import dataclass
from datetime import datetime

from loguru import logger
from sqlalchemy import select as _select, update as _update

DUREE_SECRET_S = 300          # 5 minutes (R12 réponse 11)
MAX_APPAREILS = 5             # « jusqu'à cinq appareils nommés »
_CACHE_TTL_S = 5.0            # la synchro tire des centaines de vignettes

#: secret à usage unique -> {"cree_a": float, "expire_a": float}
_SECRETS: dict[str, dict] = {}

#: cache des sha256 encore valides + l'instant de son chargement
_ACTIFS: set[str] = set()
_ACTIFS_A: float = 0.0


class SecretRefuse(Exception):
    """Le secret d'appairage est inconnu, expiré, déjà consommé, ou le
    quota de cinq appareils est atteint. Le message DIT lequel."""


@dataclass
class Secret:
    secret: str
    cree_a: float
    expire_a: float


#: R12 réponse 12 — « révocation + rappel de régénérer les clés chez chaque
#: fournisseur (liste avec liens vers chaque console) ». Les noms sont ceux
#: de _ALLOWED_ENV_KEYS (routes.py:3501).
CONSOLES: list[dict] = [
    {"cle": "FAL_KEY", "nom": "fal.ai", "url": "https://fal.ai/dashboard/keys"},
    {"cle": "HEYGEN_API_KEY", "nom": "HeyGen",
     "url": "https://app.heygen.com/settings/api"},
    {"cle": "MESHY_API_KEY", "nom": "Meshy",
     "url": "https://www.meshy.ai/settings/api"},
    {"cle": "ELEVENLABS_API_KEY", "nom": "ElevenLabs",
     "url": "https://elevenlabs.io/app/settings/api-keys"},
    {"cle": "ANTHROPIC_API_KEY", "nom": "Anthropic",
     "url": "https://console.anthropic.com/settings/keys"},
    {"cle": "OPENAI_API_KEY", "nom": "OpenAI",
     "url": "https://platform.openai.com/api-keys"},
    {"cle": "GEMINI_API_KEY", "nom": "Google AI Studio",
     "url": "https://aistudio.google.com/app/apikey"},
    {"cle": "FIGMA_TOKEN", "nom": "Figma",
     "url": "https://www.figma.com/settings"},
    {"cle": "X_API_KEY", "nom": "X (developer portal)",
     "url": "https://developer.x.com/en/portal/dashboard"},
    {"cle": "TELEGRAM_BOT_TOKEN", "nom": "Telegram BotFather",
     "url": "https://t.me/BotFather"},
]


def creer_secret() -> Secret:
    """Un secret à usage unique, valable 5 minutes. Le QR le porte."""
    s = _secrets.token_hex(16)          # 32 caractères hexadécimaux
    maintenant = time.time()
    _SECRETS[s] = {"cree_a": maintenant,
                   "expire_a": maintenant + DUREE_SECRET_S}
    _purger()
    return Secret(secret=s, cree_a=maintenant,
                  expire_a=maintenant + DUREE_SECRET_S)


def _purger() -> None:
    mort = [k for k, v in _SECRETS.items() if v["expire_a"] < time.time()]
    for k in mort:
        _SECRETS.pop(k, None)


async def reclamer(secret: str, nom: str) -> tuple[str, dict]:
    """Consomme le secret et rend (jeton en clair, fiche de l'appareil).
    Le jeton en clair n'est rendu qu'ICI, une seule fois."""
    from uuid import uuid4
    from app.services.storage import Device, async_session_factory

    fiche = _SECRETS.get(secret)
    if fiche is None:
        raise SecretRefuse("secret inconnu ou deja consomme")
    if fiche["expire_a"] < time.time():
        _SECRETS.pop(secret, None)
        raise SecretRefuse("secret expire (5 minutes) — reaffichez le QR")
    async with async_session_factory() as session:
        res = await session.execute(
            _select(Device).where(Device.revoque.is_(None)))
        if len(list(res.scalars().all())) >= MAX_APPAREILS:
            raise SecretRefuse(
                "cinq appareils sont deja appaires — revoquez-en un")
        jeton = _secrets.token_hex(32)          # 64 caractères
        appareil = Device(
            id=str(uuid4()),
            nom=(nom or "appareil").strip()[:60],
            jeton_sha256=hashlib.sha256(jeton.encode()).hexdigest(),
            cree=datetime.utcnow())
        session.add(appareil)
        await session.commit()
    _SECRETS.pop(secret, None)                  # USAGE UNIQUE
    invalider_cache()
    logger.info(f"appairage: {appareil.nom} ({appareil.id})")
    return jeton, {"id": appareil.id, "nom": appareil.nom,
                   "cree": appareil.cree.isoformat()}


def invalider_cache() -> None:
    """La révocation doit mordre TOUT DE SUITE, pas au bout du TTL."""
    global _ACTIFS_A
    _ACTIFS_A = 0.0


async def _charger_actifs() -> set[str]:
    global _ACTIFS, _ACTIFS_A
    if time.time() - _ACTIFS_A < _CACHE_TTL_S:
        return _ACTIFS
    from app.services.storage import Device, async_session_factory
    async with async_session_factory() as session:
        res = await session.execute(
            _select(Device.jeton_sha256).where(Device.revoque.is_(None)))
        _ACTIFS = {row[0] for row in res.all()}
    _ACTIFS_A = time.time()
    return _ACTIFS


async def jeton_valide(jeton: str) -> bool:
    if not jeton or len(jeton) != 64:
        return False
    empreinte = hashlib.sha256(jeton.encode()).hexdigest()
    return empreinte in await _charger_actifs()


async def lister() -> list[dict]:
    from app.services.storage import Device, async_session_factory
    async with async_session_factory() as session:
        res = await session.execute(_select(Device).order_by(Device.cree))
        return [{"id": d.id, "nom": d.nom, "cree": d.cree.isoformat(),
                 "revoque": d.revoque.isoformat() if d.revoque else None,
                 "vu_le": d.vu_le.isoformat() if d.vu_le else None}
                for d in res.scalars().all()]


async def revoquer(device_id: str) -> bool:
    from app.services.storage import Device, async_session_factory
    async with async_session_factory() as session:
        r = await session.execute(
            _update(Device).where(Device.id == device_id)
            .where(Device.revoque.is_(None))
            .values(revoque=datetime.utcnow()))
        await session.commit()
    invalider_cache()
    return r.rowcount > 0


async def revoquer_tout() -> int:
    from app.services.storage import Device, async_session_factory
    async with async_session_factory() as session:
        r = await session.execute(
            _update(Device).where(Device.revoque.is_(None))
            .values(revoque=datetime.utcnow()))
        await session.commit()
    invalider_cache()
    return r.rowcount
```

- [ ] **Step 5 : Lancer le banc, vérifier qu'il passe**

Run : `cd backend && python tests/test_appairage.py`
Attendu : sept lignes `PASS`, puis `7/7 OK`.

- [ ] **Step 6 : Commit**

```bash
git add backend/app/services/storage.py backend/app/services/appairage.py backend/tests/test_appairage.py
git commit -m 'appairage : la table des appareils, le secret a usage unique, le jeton hache' -m 'Le jeton nest jamais stocke en clair : seul son sha256 lest, et le banc le
LIT dans la base au lieu de croire le code. Le secret dappairage vaut cinq
minutes et une seule reclamation ; le refus DIT lequel des trois cas il
sagit. La revocation invalide le cache tout de suite, sans attendre son TTL.
Table neuve, donc create_all suffit — meme decision que LibraryAsset.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Tâche 3 : Encodeur QR minimal, stdlib (version 4, correction L)

**Files:**
- Create: `backend/app/services/qrcode_min.py`
- Test: `backend/tests/test_qrcode_min.py`

**Coût :** moyen. Le paquet `qrcode` est **absent** de `backend/requirements.txt` (mesuré) et le runtime est stdlib pur. La version **4-L** est choisie parce qu'elle a **un seul bloc** de correction d'erreur : aucun entrelacement à écrire, et 78 octets de capacité pour une URL d'appairage de ~45 caractères.

- [ ] **Step 1 : Vérifier les nombres de la version 4-L**

```
WebFetch url="https://www.thonky.com/qr-code-tutorial/error-correction-table" prompt="For QR version 4 with error correction level L: total codewords, EC codewords per block, number of blocks in group 1, data codewords per block. Also give the byte-mode character capacity for 4-L."
```

Attendu (à confirmer, sinon corriger les constantes du step 3) : **100** mots de code au total, **20** de correction, **1** bloc, **80** mots de données, capacité mode octet **78**.

- [ ] **Step 2 : Écrire le banc qui échoue — un DÉCODEUR indépendant**

Créer `backend/tests/test_qrcode_min.py`. Le banc ne lit pas l'encodeur : il **décode la matrice rendue** avec un second code, écrit autrement.

```python
# -*- coding: utf-8 -*-
"""QR minimal (version 4, correction L) — banc-miroir par DÉCODAGE.

Le banc ne relit pas l'encodeur : il décode la MATRICE produite avec une
implémentation indépendante (démasquage, lecture en zigzag, en-tête de
mode, longueur, octets). Deux implémentations qui se rejoignent valent
mieux qu'une assertion sur des internes.

    python tests/test_qrcode_min.py            # depuis backend/
"""
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
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

TAILLE = 33          # version 4 : 4*4 + 17
MASQUES = [
    lambda r, c: (r + c) % 2 == 0,
    lambda r, c: r % 2 == 0,
    lambda r, c: c % 3 == 0,
    lambda r, c: (r + c) % 3 == 0,
    lambda r, c: (r // 2 + c // 3) % 2 == 0,
    lambda r, c: (r * c) % 2 + (r * c) % 3 == 0,
    lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
    lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
]


def _reserve(taille):
    """Les modules de FONCTION (repères, timing, format, alignement) —
    recalculés ici, indépendamment de l'encodeur."""
    res = [[False] * taille for _ in range(taille)]
    for (r0, c0) in ((0, 0), (0, taille - 7), (taille - 7, 0)):
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                r, c = r0 + dr, c0 + dc
                if 0 <= r < taille and 0 <= c < taille:
                    res[r][c] = True
    for i in range(taille):
        res[6][i] = True
        res[i][6] = True
    for dr in range(-2, 3):                     # alignement v4 : (26, 26)
        for dc in range(-2, 3):
            res[26 + dr][26 + dc] = True
    for i in range(9):                          # format info
        res[8][i] = True
        res[i][8] = True
    for i in range(8):
        res[8][taille - 1 - i] = True
        res[taille - 1 - i][8] = True
    res[taille - 8][8] = True                   # module noir permanent
    return res


def _lire_masque(m):
    """Les 15 bits de format en haut-gauche donnent (correction, masque)."""
    bits = []
    for i in range(6):
        bits.append(m[8][i])
    bits.append(m[8][7])
    bits.append(m[8][8])
    bits.append(m[7][8])
    for i in range(6):
        bits.append(m[5 - i][8])
    val = 0
    for b in bits:
        val = (val << 1) | (1 if b else 0)
    val ^= 0b101010000010010                    # masque de format de la norme
    correction = (val >> 13) & 0b11
    masque = (val >> 10) & 0b111
    return correction, masque


def _decoder(m):
    res = _reserve(TAILLE)
    _, masque = _lire_masque(m)
    f = MASQUES[masque]
    bits = []
    col = TAILLE - 1
    haut = True
    while col > 0:
        if col == 6:
            col -= 1
        lignes = range(TAILLE - 1, -1, -1) if haut else range(TAILLE)
        for r in lignes:
            for c in (col, col - 1):
                if res[r][c]:
                    continue
                v = m[r][c]
                if f(r, c):
                    v = not v
                bits.append(1 if v else 0)
        haut = not haut
        col -= 2
    octets = []
    for i in range(0, (len(bits) // 8) * 8, 8):
        o = 0
        for b in bits[i:i + 8]:
            o = (o << 1) | b
        octets.append(o)
    flux = 0
    for b in bits[:4]:
        flux = (flux << 1) | b
    assert flux == 0b0100, f"mode attendu octet (0100), lu {flux:04b}"
    longueur = 0
    for b in bits[4:12]:
        longueur = (longueur << 1) | b
    charge = bytearray()
    for i in range(longueur):
        o = 0
        for b in bits[12 + i * 8:20 + i * 8]:
            o = (o << 1) | b
        charge.append(o)
    return bytes(charge), octets


def test_la_matrice_a_la_bonne_forme():
    from app.services import qrcode_min
    m = qrcode_min.matrice("dz1://pair?h=192.168.1.20&p=8765&s=" + "a" * 32)
    assert len(m) == TAILLE and all(len(l) == TAILLE for l in m)
    for (r0, c0) in ((0, 0), (0, TAILLE - 7), (TAILLE - 7, 0)):
        assert m[r0][c0] and m[r0 + 6][c0 + 6], (r0, c0)     # coin du repère
        assert not m[r0 + 1][c0 + 1]                          # anneau blanc
        assert m[r0 + 3][c0 + 3]                              # cœur noir
    for i in range(8, TAILLE - 8):
        assert m[6][i] == (i % 2 == 0), ("timing horizontal", i)
        assert m[i][6] == (i % 2 == 0), ("timing vertical", i)


def test_le_decodeur_independant_relit_lurl():
    from app.services import qrcode_min
    url = "dz1://pair?h=192.168.1.20&p=8765&s=" + "0f" * 16
    charge, _ = _decoder(qrcode_min.matrice(url))
    assert charge.decode("ascii") == url


def test_toutes_les_charges_de_1_a_78_octets_se_relisent():
    from app.services import qrcode_min
    for n in (1, 2, 45, 77, 78):
        texte = "".join(chr(97 + (i % 26)) for i in range(n))
        charge, _ = _decoder(qrcode_min.matrice(texte))
        assert charge.decode("ascii") == texte, n


def test_au_dela_de_78_octets_le_refus_est_nomme():
    from app.services import qrcode_min
    try:
        qrcode_min.matrice("x" * 79)
    except ValueError as e:
        assert "78" in str(e), str(e)
    else:
        raise AssertionError("79 octets acceptés dans une version 4-L")


def test_le_png_rendu_a_la_taille_demandee_et_deux_couleurs():
    """Miroir : on rouvre le PNG écrit et on compte ses couleurs."""
    from io import BytesIO
    from PIL import Image
    from app.services import qrcode_min
    png = qrcode_min.png("dz1://pair?h=10.0.0.5&p=8765&s=" + "1" * 32,
                         module=8, marge=4)
    im = Image.open(BytesIO(png))
    cote = (TAILLE + 8) * 8
    assert im.size == (cote, cote), im.size
    couleurs = {p for p in im.convert("L").getdata()}
    assert couleurs == {0, 255}, sorted(couleurs)


TESTS = [test_la_matrice_a_la_bonne_forme,
         test_le_decodeur_independant_relit_lurl,
         test_toutes_les_charges_de_1_a_78_octets_se_relisent,
         test_au_dela_de_78_octets_le_refus_est_nomme,
         test_le_png_rendu_a_la_taille_demandee_et_deux_couleurs]

if __name__ == "__main__":
    failed = []
    for t in TESTS:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed.append(t.__name__)
            print(f"FAIL {t.__name__}: {e!r}")
    print(f"\n{len(TESTS) - len(failed)}/{len(TESTS)} OK")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 3 : Lancer le banc, vérifier qu'il échoue**

Run : `cd backend && python tests/test_qrcode_min.py`
Attendu : cinq `FAIL ... ModuleNotFoundError("No module named 'app.services.qrcode_min'")`, puis `0/5 OK`.

- [ ] **Step 4 : Écrire l'encodeur**

Créer `backend/app/services/qrcode_min.py` :

```python
# -*- coding: utf-8 -*-
"""QR code minimal, stdlib pur — VERSION 4, correction L, mode octet.

POURQUOI si peu : le paquet `qrcode` est absent de requirements.txt et le
runtime livré est stdlib + Pillow (mesuré 03/09). Le QR d'appairage porte
au plus « dz1://pair?h=<ip>&p=<port>&s=<32 hex> », soit ~50 octets.

POURQUOI la version 4 et la correction L : c'est la plus petite version
dont la capacité (78 octets en mode octet) couvre l'URL, et 4-L n'a QU'UN
SEUL bloc de correction — l'entrelacement des blocs, la partie la plus
délicate de la norme, disparaît entièrement.

Nombres de la version 4-L (à vérifier avant de les changer) :
  33 x 33 modules, 100 mots de code, 20 de correction, 80 de données,
  un unique motif d'alignement en (26, 26), pas d'information de version
  (elle n'existe qu'à partir de la version 7).
"""
import struct
import zlib

VERSION = 4
TAILLE = 4 * VERSION + 17          # 33
MOTS_DONNEES = 80
MOTS_CORRECTION = 20
CAPACITE_OCTETS = 78               # 80 mots - 4 bits de mode - 8 de longueur
ALIGNEMENT = (26, 26)

_MASQUES = [
    lambda r, c: (r + c) % 2 == 0,
    lambda r, c: r % 2 == 0,
    lambda r, c: c % 3 == 0,
    lambda r, c: (r + c) % 3 == 0,
    lambda r, c: (r // 2 + c // 3) % 2 == 0,
    lambda r, c: (r * c) % 2 + (r * c) % 3 == 0,
    lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
    lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
]

# ── GF(256), polynôme 0x11D, la table de la norme ────────────────────────────
_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def _generateur(n: int) -> list[int]:
    g = [1]
    for i in range(n):
        g2 = [0] * (len(g) + 1)
        for j, c in enumerate(g):
            g2[j] ^= c
            g2[j + 1] ^= _mul(c, _EXP[i])
        g = g2
    return g


def _correction(donnees: bytes, n: int) -> list[int]:
    g = _generateur(n)
    reste = list(donnees) + [0] * n
    for i in range(len(donnees)):
        tete = reste[i]
        if tete:
            for j, c in enumerate(g):
                reste[i + j] ^= _mul(c, tete)
    return reste[len(donnees):]


def _bits(charge: bytes) -> list[int]:
    """Mode octet (0100), longueur sur 8 bits (versions 1 à 9), données,
    terminateur, remplissage par 0xEC / 0x11."""
    b: list[int] = [0, 1, 0, 0]
    for i in range(7, -1, -1):
        b.append((len(charge) >> i) & 1)
    for o in charge:
        for i in range(7, -1, -1):
            b.append((o >> i) & 1)
    b += [0] * min(4, MOTS_DONNEES * 8 - len(b))
    while len(b) % 8:
        b.append(0)
    remplissage = (0xEC, 0x11)
    k = 0
    while len(b) < MOTS_DONNEES * 8:
        for i in range(7, -1, -1):
            b.append((remplissage[k % 2] >> i) & 1)
        k += 1
    return b


def _reserve() -> list[list[bool]]:
    res = [[False] * TAILLE for _ in range(TAILLE)]
    for (r0, c0) in ((0, 0), (0, TAILLE - 7), (TAILLE - 7, 0)):
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                r, c = r0 + dr, c0 + dc
                if 0 <= r < TAILLE and 0 <= c < TAILLE:
                    res[r][c] = True
    for i in range(TAILLE):
        res[6][i] = True
        res[i][6] = True
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            res[ALIGNEMENT[0] + dr][ALIGNEMENT[1] + dc] = True
    for i in range(9):
        res[8][i] = True
        res[i][8] = True
    for i in range(8):
        res[8][TAILLE - 1 - i] = True
        res[TAILLE - 1 - i][8] = True
    res[TAILLE - 8][8] = True
    return res


def _motifs(m: list[list[bool]]) -> None:
    for (r0, c0) in ((0, 0), (0, TAILLE - 7), (TAILLE - 7, 0)):
        for dr in range(7):
            for dc in range(7):
                bord = dr in (0, 6) or dc in (0, 6)
                coeur = 2 <= dr <= 4 and 2 <= dc <= 4
                m[r0 + dr][c0 + dc] = bord or coeur
    for i in range(TAILLE):
        m[6][i] = i % 2 == 0
        m[i][6] = i % 2 == 0
    for dr in range(-2, 3):
        for dc in range(-2, 3):
            bord = abs(dr) == 2 or abs(dc) == 2
            m[ALIGNEMENT[0] + dr][ALIGNEMENT[1] + dc] = bord or (dr == dc == 0)
    m[TAILLE - 8][8] = True


def _format(m: list[list[bool]], masque: int) -> None:
    """15 bits : 2 de correction (L = 01), 3 de masque, 10 de BCH, XOR
    du masque de format de la norme."""
    val = (0b01 << 3) | masque
    reste = val << 10
    for i in range(4, -1, -1):
        if reste & (1 << (i + 10)):
            reste ^= 0b10100110111 << i
    bits15 = ((val << 10) | reste) ^ 0b101010000010010
    liste = [(bits15 >> (14 - i)) & 1 for i in range(15)]
    for i in range(6):
        m[8][i] = bool(liste[i])
    m[8][7] = bool(liste[6])
    m[8][8] = bool(liste[7])
    m[7][8] = bool(liste[8])
    for i in range(6):
        m[5 - i][8] = bool(liste[9 + i])
    for i in range(8):
        m[TAILLE - 1 - i][8] = bool(liste[i])
    for i in range(7):
        m[8][TAILLE - 7 + i] = bool(liste[8 + i])


def _penalite(m: list[list[bool]]) -> int:
    """Règle 1 seule (séries de 5+), suffisante pour choisir un masque
    honnête sur une charge de 50 octets — la norme en compte quatre."""
    p = 0
    for ligne in list(m) + [list(col) for col in zip(*m)]:
        n, prec = 1, ligne[0]
        for v in ligne[1:]:
            if v == prec:
                n += 1
            else:
                if n >= 5:
                    p += 3 + (n - 5)
                n, prec = 1, v
        if n >= 5:
            p += 3 + (n - 5)
    return p


def matrice(texte: str) -> list[list[bool]]:
    """La matrice 33x33 de `texte` (ASCII/UTF-8), version 4, correction L."""
    charge = texte.encode("utf-8")
    if len(charge) > CAPACITE_OCTETS:
        raise ValueError(
            f"{len(charge)} octets : une version 4-L en porte 78 au plus")
    bits = _bits(charge)
    donnees = bytes(
        int("".join(str(b) for b in bits[i:i + 8]), 2)
        for i in range(0, len(bits), 8))
    flux = list(donnees) + _correction(donnees, MOTS_CORRECTION)
    suite = [(o >> i) & 1 for o in flux for i in range(7, -1, -1)]

    res = _reserve()
    meilleure, meilleur_score = None, None
    for masque in range(8):
        m = [[False] * TAILLE for _ in range(TAILLE)]
        _motifs(m)
        f = _MASQUES[masque]
        k = 0
        col, haut = TAILLE - 1, True
        while col > 0:
            if col == 6:
                col -= 1
            lignes = range(TAILLE - 1, -1, -1) if haut else range(TAILLE)
            for r in lignes:
                for c in (col, col - 1):
                    if res[r][c]:
                        continue
                    v = bool(suite[k]) if k < len(suite) else False
                    k += 1
                    m[r][c] = (not v) if f(r, c) else v
            haut = not haut
            col -= 2
        _format(m, masque)
        s = _penalite(m)
        if meilleur_score is None or s < meilleur_score:
            meilleure, meilleur_score = m, s
    return meilleure


def png(texte: str, module: int = 8, marge: int = 4) -> bytes:
    """Le QR en PNG noir sur blanc, écrit sans Pillow (zlib suffit)."""
    m = matrice(texte)
    cote = (TAILLE + 2 * marge) * module
    lignes = bytearray()
    for y in range(cote):
        lignes.append(0)                        # filtre None
        r = y // module - marge
        for x in range(cote):
            c = x // module - marge
            noir = (0 <= r < TAILLE and 0 <= c < TAILLE and m[r][c])
            lignes.append(0 if noir else 255)

    def bloc(tag: bytes, data: bytes) -> bytes:
        corps = tag + data
        return (struct.pack(">I", len(data)) + corps
                + struct.pack(">I", zlib.crc32(corps) & 0xFFFFFFFF))

    entete = struct.pack(">IIBBBBB", cote, cote, 8, 0, 0, 0, 0)  # gris 8 bits
    return (b"\x89PNG\r\n\x1a\n" + bloc(b"IHDR", entete)
            + bloc(b"IDAT", zlib.compress(bytes(lignes), 9))
            + bloc(b"IEND", b""))
```

- [ ] **Step 5 : Lancer le banc, vérifier qu'il passe**

Run : `cd backend && python tests/test_qrcode_min.py`
Attendu : cinq lignes `PASS`, puis `5/5 OK`.

- [ ] **Step 6 : Vérification humaine — le QR se scanne vraiment**

```bash
cd backend && python -c "import sys; sys.path.insert(0,'.'); from app.services import qrcode_min; open('qr_essai.png','wb').write(qrcode_min.png('dz1://pair?h=192.168.1.20&p=8765&s=' + '0f'*16))"
```

Ouvrir `backend/qr_essai.png`, le scanner avec l'appareil photo du téléphone.
Attendu : le téléphone propose l'ouverture de `dz1://pair?h=192.168.1.20&p=8765&s=0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f`.
Un banc ne peut pas mesurer cela ; c'est la seule étape manuelle du plan. Puis :

```bash
rm backend/qr_essai.png
```

- [ ] **Step 7 : Commit**

```bash
git add backend/app/services/qrcode_min.py backend/tests/test_qrcode_min.py
git commit -m 'appairage : un encodeur QR stdlib, version 4-L, un seul bloc de correction' -m 'Le paquet qrcode est absent du runtime embarque (mesure) : lencodeur est
ecrit. La version 4-L est choisie parce quelle na QUUN bloc de correction —
lentrelacement, la partie la plus delicate de la norme, disparait — et que
ses 78 octets couvrent lURL dappairage.

Le banc ne relit pas lencodeur : il DECODE la matrice avec une seconde
implementation, ecrite autrement. Le PNG rendu est rouvert et ses couleurs
comptees. La lecture par un vrai telephone reste letape manuelle.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Tâche 4 : Routes d'appairage et garde de jeton sur toute route

**Files:**
- Modify: `backend/app/main.py:206-221` (la garde CSRF reste ; la garde de jeton se déclare **après** elle, donc s'exécute **avant**)
- Modify: `backend/app/api/routes.py` (ajouter les routes à la fin du fichier, après la ligne 9575)
- Test: `backend/tests/test_appairage_routes.py`

**Coût :** faible côté code, **structurant** côté sécurité. Aucune migration, aucun patch de bundle. Le fichier `routes.py` fait déjà 9 575 lignes ; les routes d'appairage y sont ajoutées **à la fin** pour ne déplacer aucune ligne existante et garder les repères des autres plans valides.

- [ ] **Step 1 : Écrire le banc qui échoue**

Créer `backend/tests/test_appairage_routes.py` :

```python
# -*- coding: utf-8 -*-
"""P1 — la garde de jeton, mesurée sur de VRAIES requêtes.

Mesure du 03/09 qui commande ce banc : starlette 0.37.2 code en dur
`"client": ["testclient", 50000]` dans le scope du TestClient
(starlette/testclient.py:301 et :320). On ne peut donc PAS régler
`client.host` par un paramètre : on enveloppe l'application dans une
coquille ASGI qui réécrit `scope["client"]` avant de déléguer.

    python tests/test_appairage_routes.py       # depuis backend/
"""
import asyncio
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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _client(ip="testclient"):
    """TestClient dont le scope porte l'IP demandée."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.storage import init_db
    asyncio.run(init_db())

    async def coquille(scope, receive, send):
        if scope["type"] == "http":
            scope = dict(scope)
            scope["client"] = (ip, 50000)
        await app(scope, receive, send)

    return TestClient(coquille)


def test_le_loopback_passe_sans_jeton():
    r = _client("127.0.0.1").get("/api/jobs")
    assert r.status_code == 200, (r.status_code, r.text[:200])


def test_le_lan_sans_jeton_est_refuse_sur_une_route_de_lecture():
    r = _client("192.168.1.42").get("/api/jobs")
    assert r.status_code == 401, (r.status_code, r.text[:200])
    assert "jeton" in r.text.lower()


def test_le_lan_sans_jeton_est_refuse_sur_le_frontend_aussi():
    """« toute route » veut dire TOUTE : la page elle-même est fermée."""
    r = _client("192.168.1.42").get("/api/health")
    assert r.status_code == 401, (r.status_code, r.text[:200])


def test_le_lan_avec_un_jeton_valide_passe():
    from app.services import appairage
    c = _client("127.0.0.1")
    s = c.post("/api/pair/start").json()
    assert len(s["secret"]) == 32 and s["url"].startswith("dz1://pair?")
    lan = _client("192.168.1.42")
    rep = lan.post("/api/pair/claim",
                   json={"secret": s["secret"], "nom": "iPhone de Oli"})
    assert rep.status_code == 200, (rep.status_code, rep.text[:200])
    jeton = rep.json()["jeton"]
    r = lan.get("/api/jobs", headers={"Authorization": f"Bearer {jeton}"})
    assert r.status_code == 200, (r.status_code, r.text[:200])
    asyncio.run(appairage.revoquer_tout())


def test_un_jeton_revoque_ne_passe_plus_tout_de_suite():
    from app.services import appairage
    c = _client("127.0.0.1")
    s = c.post("/api/pair/start").json()
    lan = _client("192.168.1.42")
    jeton = lan.post("/api/pair/claim",
                     json={"secret": s["secret"], "nom": "perdu"}).json()["jeton"]
    h = {"Authorization": f"Bearer {jeton}"}
    assert lan.get("/api/jobs", headers=h).status_code == 200
    ident = c.get("/api/devices").json()["appareils"][-1]["id"]
    assert c.post(f"/api/devices/{ident}/revoke").status_code == 200
    assert lan.get("/api/jobs", headers=h).status_code == 401


def test_les_cles_restent_interdites_au_lan_meme_avec_un_jeton():
    """_require_localhost INTACT : c'est la décision D-D du plan."""
    from app.services import appairage
    c = _client("127.0.0.1")
    s = c.post("/api/pair/start").json()
    lan = _client("192.168.1.42")
    jeton = lan.post("/api/pair/claim",
                     json={"secret": s["secret"], "nom": "curieux"}).json()["jeton"]
    r = lan.get("/api/settings/keys",
                headers={"Authorization": f"Bearer {jeton}"})
    assert r.status_code == 403, (r.status_code, r.text[:200])
    asyncio.run(appairage.revoquer_tout())


def test_la_garde_csrf_reste_en_place():
    """Elle protège toujours le navigateur du PC d'une page hostile."""
    r = _client("127.0.0.1").post(
        "/api/schedule", json={"title": "x", "run_at": "2026-09-04T09:00:00"},
        headers={"Origin": "https://evil.example"})
    assert r.status_code == 403, (r.status_code, r.text[:200])
    assert "Cross-origin" in r.text


def test_les_routes_dappairage_sont_reservees_au_loopback():
    r = _client("192.168.1.42").post("/api/pair/start")
    assert r.status_code == 401, (r.status_code, r.text[:200])


def test_la_route_de_rotation_liste_les_consoles():
    r = _client("127.0.0.1").get("/api/devices/rotation")
    assert r.status_code == 200
    cles = {c["cle"] for c in r.json()["consoles"]}
    assert "FAL_KEY" in cles and "TELEGRAM_BOT_TOKEN" in cles


TESTS = [test_le_loopback_passe_sans_jeton,
         test_le_lan_sans_jeton_est_refuse_sur_une_route_de_lecture,
         test_le_lan_sans_jeton_est_refuse_sur_le_frontend_aussi,
         test_le_lan_avec_un_jeton_valide_passe,
         test_un_jeton_revoque_ne_passe_plus_tout_de_suite,
         test_les_cles_restent_interdites_au_lan_meme_avec_un_jeton,
         test_la_garde_csrf_reste_en_place,
         test_les_routes_dappairage_sont_reservees_au_loopback,
         test_la_route_de_rotation_liste_les_consoles]

if __name__ == "__main__":
    failed = []
    for t in TESTS:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed.append(t.__name__)
            print(f"FAIL {t.__name__}: {e!r}")
    print(f"\n{len(TESTS) - len(failed)}/{len(TESTS)} OK")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2 : Lancer le banc, vérifier qu'il échoue**

Run : `cd backend && python tests/test_appairage_routes.py`
Attendu : `PASS test_le_loopback_passe_sans_jeton`, `PASS test_la_garde_csrf_reste_en_place`, et sept `FAIL` (les routes n'existent pas, la garde non plus), dernière ligne `2/9 OK`.

- [ ] **Step 3 : Déclarer la garde de jeton dans `main.py`**

Dans `backend/app/main.py`, insérer **juste après** la fin de `_csrf_origin_guard` (la ligne `    return await call_next(request)` à `:221`) et **avant** `app.include_router(router, prefix="/api")` (`:224`) :

```python
# Garde de jeton d'appareil (P1, 03/09). MESURE qui la rend nécessaire : la
# garde CSRF ci-dessus fait `if origin:` — une application NATIVE n'envoie
# pas d'Origin et passe donc. Dès que HOST écoute le LAN, n'importe quel
# appareil du Wi-Fi pourrait dépenser des crédits. Le jeton est LA garde.
#
# MESURE de l'ordre : Starlette.add_middleware fait `user_middleware.insert(0)`
# (starlette 0.37.2, applications.py:142) — le DERNIER déclaré est le PLUS
# EXTÉRIEUR. Déclarée ici, après la garde CSRF, celle-ci s'exécute donc EN
# PREMIER : un client LAN sans jeton est refusé avant tout le reste, y compris
# avant le service des fichiers statiques.
_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}
#: la seule route ouverte au LAN sans jeton — c'est l'amorçage lui-même,
#: et elle exige un secret à usage unique valable 5 minutes.
_ROUTES_SANS_JETON = {"/api/pair/claim"}


@app.middleware("http")
async def _device_token_guard(request, call_next):
    host = (request.client.host if request.client else "") or ""
    if host in _LOOPBACK_HOSTS:
        return await call_next(request)
    if request.url.path in _ROUTES_SANS_JETON:
        return await call_next(request)
    entete = request.headers.get("authorization", "")
    jeton = entete[7:].strip() if entete[:7].lower() == "bearer " else ""
    from app.services import appairage as _appairage
    if not await _appairage.jeton_valide(jeton):
        return _JSONResponse(
            {"detail": "jeton d'appareil requis — appairez le telephone "
                       "depuis Settings > Appareils"},
            status_code=401)
    return await call_next(request)
```

- [ ] **Step 4 : Ajouter les routes à la fin de `routes.py`**

Ajouter **à la fin** de `backend/app/api/routes.py` (après la ligne 9575) :

```python
# ── P1 : appairage d'un appareil (03/09) ─────────────────────────────────────
# `_require_localhost` garde ces routes : seul le PC affiche un QR et révoque.
# `/pair/claim` est l'exception, ouverte au LAN par _ROUTES_SANS_JETON dans
# main.py — le secret à usage unique de 5 minutes y tient lieu de garde.

def _adresse_lan() -> str:
    """L'IP de la machine sur le LAN, vue par le routeur. Aucun paquet n'est
    envoyé : `connect` sur un socket UDP ne fait que choisir l'interface."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.168.1.1", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


@router.post("/pair/start")
async def pair_start(request: Request):
    """Un secret à usage unique + l'URL que le QR porte + le QR en PNG."""
    _require_localhost(request)
    import base64
    from app.services import appairage, qrcode_min
    s = appairage.creer_secret()
    hote = _adresse_lan()
    url = f"dz1://pair?h={hote}&p={settings.PORT}&s={s.secret}"
    png = qrcode_min.png(url, module=8, marge=4)
    return {"secret": s.secret, "url": url, "hote": hote,
            "port": settings.PORT, "expire_dans_s": appairage.DUREE_SECRET_S,
            "qr_png_b64": base64.b64encode(png).decode("ascii")}


@router.post("/pair/claim")
async def pair_claim(body: dict):
    """Le téléphone échange le secret contre son jeton. Rendu UNE fois."""
    from app.services import appairage
    secret = str((body or {}).get("secret") or "")
    nom = str((body or {}).get("nom") or "appareil")
    try:
        jeton, appareil = await appairage.reclamer(secret, nom)
    except appairage.SecretRefuse as e:
        raise HTTPException(403, str(e))
    return {"jeton": jeton, "appareil": appareil,
            "protocole": 1, "version": APP_VERSION}


@router.get("/devices")
async def devices_list(request: Request):
    _require_localhost(request)
    from app.services import appairage
    return {"appareils": await appairage.lister(),
            "max": appairage.MAX_APPAREILS}


@router.post("/devices/{device_id}/revoke")
async def devices_revoke(device_id: str, request: Request):
    _require_localhost(request)
    from app.services import appairage
    if not await appairage.revoquer(device_id):
        raise HTTPException(404, "appareil inconnu ou deja revoque")
    return {"revoque": device_id}


@router.get("/devices/rotation")
async def devices_rotation(request: Request):
    """R12 réponse 12 : après un téléphone perdu, révoquer NE SUFFIT PAS —
    les clés ont voyagé dans l'archive chiffrée. Voici où les régénérer."""
    _require_localhost(request)
    from app.services import appairage
    return {"consoles": appairage.CONSOLES}
```

- [ ] **Step 5 : Lancer le banc, vérifier qu'il passe**

Run : `cd backend && python tests/test_appairage_routes.py`
Attendu : neuf lignes `PASS`, puis `9/9 OK`.

- [ ] **Step 6 : Vérifier que rien d'ancien n'a bougé**

Run : `cd backend && python tests/test_security_guards.py 2>&1 | tail -3`
Attendu : aucune ligne `FAIL` (ce fichier tourne sous pytest ; s'il ne s'exécute pas seul, lancer `.\scripts\run-tests.ps1 -Filter test_security_guards.py` depuis la racine et attendre `1 file passed`).

- [ ] **Step 7 : Commit**

```bash
git add backend/app/main.py backend/app/api/routes.py backend/tests/test_appairage_routes.py
git commit -m 'appairage : la garde de jeton sur toute route hors loopback, et le QR' -m 'La garde CSRF laisse passer les requetes SANS Origin — cest mesure, ligne
212 de main.py — donc une application native passe. Le jeton est la vraie
garde : declaree APRES la garde CSRF, elle sexecute AVANT elle (Starlette
insere chaque middleware en tete de pile), et refuse 401 tout client non
loopback sans Bearer, routes statiques comprises.

_require_localhost reste intact : un telephone appaire recoit toujours 403
sur /settings/keys. Le banc le mesure en forcant client.host par une coquille
ASGI — le TestClient de starlette 0.37.2 code son client en dur.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Tâche 5 : `HOST` configurable jusqu'au lanceur

**Files:**
- Modify: `backend/app/config.py:102-103` (commentaire seulement — la valeur par défaut ne change PAS)
- Modify: `scripts/launch-silent.vbs:56` (la ligne qui code `--host 127.0.0.1` en dur)
- Test: `backend/tests/test_appairage_routes.py` (deux tests de plus)

**Coût :** faible en lignes, **élevé en conséquence**. C'est le seul geste du plan qui change ce qu'écoute la machine. Le défaut reste `127.0.0.1` : ouvrir le LAN est une décision explicite, écrite dans `.env`.

- [ ] **Step 1 : Ajouter les tests qui échouent**

Dans `backend/tests/test_appairage_routes.py`, ajouter avant la liste `TESTS` :

```python
def test_le_defaut_reste_le_loopback():
    from app.config import Settings
    assert Settings.model_fields["HOST"].default == "127.0.0.1"


def test_le_lanceur_ne_code_plus_lhote_en_dur():
    """Miroir : on lit le LANCEUR livré, pas config.py — c'est lui qui
    décide de ce que la machine installée écoute (mesuré le 03/09)."""
    vbs = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "launch-silent.vbs"
    txt = vbs.read_text(encoding="utf-8", errors="replace")
    assert "--host 127.0.0.1" not in txt, \
        "launch-silent.vbs code encore l'hote en dur"
    assert "hostArg" in txt and "HOST=" in txt
```

et les ajouter à `TESTS` :

```python
TESTS = [test_le_loopback_passe_sans_jeton,
         test_le_lan_sans_jeton_est_refuse_sur_une_route_de_lecture,
         test_le_lan_sans_jeton_est_refuse_sur_le_frontend_aussi,
         test_le_lan_avec_un_jeton_valide_passe,
         test_un_jeton_revoque_ne_passe_plus_tout_de_suite,
         test_les_cles_restent_interdites_au_lan_meme_avec_un_jeton,
         test_la_garde_csrf_reste_en_place,
         test_les_routes_dappairage_sont_reservees_au_loopback,
         test_la_route_de_rotation_liste_les_consoles,
         test_le_defaut_reste_le_loopback,
         test_le_lanceur_ne_code_plus_lhote_en_dur]
```

- [ ] **Step 2 : Lancer, vérifier l'échec ciblé**

Run : `cd backend && python tests/test_appairage_routes.py`
Attendu : `FAIL test_le_lanceur_ne_code_plus_lhote_en_dur: AssertionError("launch-silent.vbs code encore l'hote en dur")`, `10/11 OK`.

- [ ] **Step 3 : Documenter `HOST` dans `config.py`**

Remplacer, dans `backend/app/config.py`, les lignes 101-103 :

```python
    # Server
    HOST: str = "127.0.0.1"
    PORT: int = 8765
```

par :

```python
    # Server
    # HOST reste 127.0.0.1 PAR DÉFAUT : ouvrir le LAN est une décision, pas un
    # réglage. `HOST=0.0.0.0` dans le .env du DATA_ROOT fait écouter le Wi-Fi —
    # à ne faire QU'APRÈS avoir appairé un appareil, car alors la garde de
    # jeton (main.py, _device_token_guard) devient la seule protection de
    # l'API. `_require_localhost` (routes.py) reste vrai quoi qu'il arrive :
    # les clés ne sortent jamais par le réseau.
    HOST: str = "127.0.0.1"
    PORT: int = 8765
```

- [ ] **Step 4 : Faire lire `HOST` au lanceur**

Dans `scripts/launch-silent.vbs`, remplacer la ligne 56 :

```vbscript
shell.Run """" & py & """ -m uvicorn app.main:app --host 127.0.0.1 --port 8765", 0, False
```

par ce bloc :

```vbscript
' L'hote d'ecoute vient du .env de l'utilisateur (DATA_ROOT), pas d'ici : le
' defaut reste 127.0.0.1, et HOST=0.0.0.0 ouvre le LAN pour le compagnon
' mobile. Sans cette lecture, changer config.py ne changerait RIEN sur une
' machine installee — c'est CETTE ligne qui decide (mesure du 03/09).
hostArg = "127.0.0.1"
envPath = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\DeepotusVideoGenData\.env"
If fso.FileExists(envPath) Then
  Set envFile = fso.OpenTextFile(envPath, 1)
  Do Until envFile.AtEndOfStream
    line = Trim(envFile.ReadLine)
    If Left(line, 5) = "HOST=" Then
      cand = Trim(Mid(line, 6))
      If cand = "0.0.0.0" Or cand = "127.0.0.1" Then hostArg = cand
    End If
  Loop
  envFile.Close
End If
shell.Run """" & py & """ -m uvicorn app.main:app --host " & hostArg & " --port 8765", 0, False
```

- [ ] **Step 5 : Lancer, vérifier que tout passe**

Run : `cd backend && python tests/test_appairage_routes.py`
Attendu : onze lignes `PASS`, puis `11/11 OK`.

- [ ] **Step 6 : Relire le lanceur SANS l'exécuter**

Ne **jamais** lancer `cscript //X scripts\launch-silent.vbs` pour « vérifier » : cette option ouvre le débogueur et démarre réellement le backend. On relit le fichier :

```bash
grep -c -- "--host 127.0.0.1" scripts/launch-silent.vbs
grep -c "hostArg" scripts/launch-silent.vbs
```
Attendu : `0` puis `3` (la déclaration, l'affectation conditionnelle, l'usage dans `shell.Run`).

- [ ] **Step 7 : Commit**

```bash
git add backend/app/config.py scripts/launch-silent.vbs backend/tests/test_appairage_routes.py
git commit -m 'appairage : HOST configurable jusquau lanceur, defaut inchange' -m 'Mesure du 03/09 : le lanceur livre codait --host 127.0.0.1 en dur, donc
changer config.py seul naurait rien change sur une machine installee. Il lit
desormais HOST dans le .env du DATA_ROOT et naccepte que deux valeurs.

Le defaut reste le loopback : ouvrir le LAN est une decision explicite, prise
apres lappairage, et la garde de jeton devient alors la seule protection de
lAPI — cest ecrit dans le commentaire de config.py, pas sous-entendu.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Tâche 6 : Page « Appareils » dans Settings (le SEUL patch du bundle)

**Files:**
- Create: `scripts/patch_bundle_dzappair.py`
- Modify: `frontend/dist/assets/index-BEOJX8L5.js` (par le patcher, jamais à la main)
- Test: `backend/tests/test_patch_dzappair.py`

**Coût :** **UN patch du bundle**, tag NEUF `dzappair`, backup `.js.bak_dzappair`, position **EN QUEUE** après `seedance25` (queue de chaîne mesurée le 03/09 par `python scripts/repatch_all.py --list`). Quatre ancres, toutes mesurées à `count == 1` le 03/09 :

| Ancre | Longueur | Compte |
|---|---|---|
| `const ym=["keys","accounts","personas","branding","pack","defaults","paths","news","appearance","pricing"];` | 107 | 1 |
| `{k:"pricing",l:"Pricing & budget"}]` | 35 | 1 |
| `s==="pricing"&&r.jsx(DzPricing,{})]` | 35 | 1 |
| `function DzPricing(){` | 21 | 1 |

État du bundle avant patch : **1 395 299 o**, CRLF=**11884**, LF isolés=**0**, CR isolés=**0**.

- [ ] **Step 1 : Écrire le banc qui échoue**

Créer `backend/tests/test_patch_dzappair.py` :

```python
# -*- coding: utf-8 -*-
"""Le patch dzappair — banc-miroir sur le BUNDLE ÉCRIT, pas sur le patcher.

    python tests/test_patch_dzappair.py         # depuis backend/
"""
import pathlib
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

R = pathlib.Path(__file__).resolve().parents[2]
BUNDLE = R / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"


def _texte():
    return BUNDLE.read_text(encoding="utf-8", newline="")


def test_le_bundle_reste_en_crlf_homogene():
    raw = BUNDLE.read_bytes()
    crlf = raw.count(b"\r\n")
    assert raw.count(b"\n") - crlf == 0, "des LF isolés sont apparus"
    assert raw.count(b"\r") - crlf == 0, "des CR isolés sont apparus"


def test_la_section_appareils_est_dans_la_liste_des_sections():
    s = _texte()
    assert '"devices"' in s, "la clé de section devices est absente"
    assert s.count('"appearance","pricing","devices"]') == 1


def test_lentree_de_menu_existe_une_fois():
    assert _texte().count('{k:"devices",l:"Paired devices"}') == 1


def test_le_composant_est_branche_une_fois():
    s = _texte()
    assert s.count('s==="devices"&&r.jsx(DzAppair,{})') == 1
    assert s.count("function DzAppair(){") == 1


def test_le_composant_appelle_les_trois_routes():
    s = _texte()
    for route in ("/api/devices", "/api/pair/start", "/api/devices/rotation"):
        assert route in s, route
    assert "/revoke" in s


def test_le_qr_est_affiche_depuis_le_base64_de_la_route():
    """Le QR n'est PAS redessiné côté bundle : le PNG vient du backend."""
    s = _texte()
    assert "data:image/png;base64," in s
    assert "qr_png_b64" in s


def test_aucun_marqueur_en_double():
    assert _texte().count("__dzAppair") == 1


TESTS = [test_le_bundle_reste_en_crlf_homogene,
         test_la_section_appareils_est_dans_la_liste_des_sections,
         test_lentree_de_menu_existe_une_fois,
         test_le_composant_est_branche_une_fois,
         test_le_composant_appelle_les_trois_routes,
         test_le_qr_est_affiche_depuis_le_base64_de_la_route,
         test_aucun_marqueur_en_double]

if __name__ == "__main__":
    failed = []
    for t in TESTS:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed.append(t.__name__)
            print(f"FAIL {t.__name__}: {e!r}")
    print(f"\n{len(TESTS) - len(failed)}/{len(TESTS)} OK")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run : `cd backend && python tests/test_patch_dzappair.py`
Attendu : `PASS test_le_bundle_reste_en_crlf_homogene`, six `FAIL`, `1/7 OK`.

- [ ] **Step 3 : Écrire le patcher**

Créer `scripts/patch_bundle_dzappair.py` :

```python
# -*- coding: utf-8 -*-
# scripts/patch_bundle_dzappair.py
"""Patcher assert-garde : section « Paired devices » dans Settings.

BASELINE : bundle POST-patch seedance25 (queue de chaine mesuree le 03/09
par `python scripts/repatch_all.py --list`).
Backup dedie : `.js.bak_dzappair`. Position : EN QUEUE, apres seedance25.

CE QUE LE PATCH NE FAIT PAS
  Il ne dessine pas de QR : le PNG vient de POST /api/pair/start en
  base64 (l'encodeur est en Python, banc `test_qrcode_min.py`). Il
  n'affiche jamais un jeton : la route n'en rend qu'un, une fois, au
  telephone. Aucune CSS, aucun composant neuf : la section reutilise le
  meme rail que « Pricing & budget », donc les memes jetons visuels.

QUATRE ANCRES, toutes mesurees a count == 1 le 03/09 :
  A1  la liste des cles de section (`ym`)
  A2  la derniere entree du rail de gauche
  A3  le dernier branchement de composant
  A4  le point d'insertion de la fonction (avant DzPricing)

DANGERS : lancement SEUL, newline='' partout (CRLF), jamais d'ancre
imprimee (cp1252). Si un patch AVAL apparait un jour :
`python scripts/repatch_all.py --from dzappair`.

Run :
    python scripts/patch_bundle_dzappair.py            # depot
    python scripts/patch_bundle_dzappair.py --check    # n'ecrit rien
    python scripts/patch_bundle_dzappair.py --deltas   # affiche les deltas
"""
import os
import pathlib
import shutil
import sys
import time

REL_BUNDLE = pathlib.Path("frontend/dist/assets/index-BEOJX8L5.js")
TAG = "dzappair"
MARKER = "__dzAppair"
MARKER_ATTENDU = 1

A1 = ('const ym=["keys","accounts","personas","branding","pack","defaults",'
      '"paths","news","appearance","pricing"];')
A2 = '{k:"pricing",l:"Pricing & budget"}]'
A3 = 's==="pricing"&&r.jsx(DzPricing,{})]'
A4 = "function DzPricing(){"

COMPOSANT = (
    "function DzAppair(){/*__dzAppair*/"
    "const[l,sl]=x.useState([]),[q,sq]=x.useState(null),"
    "[rot,srot]=x.useState([]),[err,se]=x.useState(\"\");"
    "const rech=()=>fetch(\"/api/devices\").then(r=>r.json())"
    ".then(d=>sl(d.appareils||[])).catch(e=>se(String(e)));"
    "x.useEffect(()=>{rech();"
    "fetch(\"/api/devices/rotation\").then(r=>r.json())"
    ".then(d=>srot(d.consoles||[])).catch(()=>{})},[]);"
    "const pair=()=>fetch(\"/api/pair/start\",{method:\"POST\"})"
    ".then(r=>r.json()).then(d=>{sq(d);setTimeout(()=>{sq(null);rech()},"
    "(d.expire_dans_s||300)*1000)}).catch(e=>se(String(e)));"
    "const rev=i=>fetch(\"/api/devices/\"+i+\"/revoke\",{method:\"POST\"})"
    ".then(rech);"
    "return r.jsxs(r.Fragment,{children:["
    "r.jsx(\"div\",{className:\"display\",style:{fontSize:22,"
    "color:\"var(--ink-strong)\",marginBottom:4},children:\"Paired devices\"}),"
    "r.jsx(\"div\",{style:{fontSize:12,color:\"var(--ink-soft)\","
    "marginBottom:20},children:\"Un appareil appaire peut lire et ecrire par "
    "le reseau local quand HOST=0.0.0.0. Les cles API ne sortent jamais par "
    "le reseau : elles voyagent par l archive chiffree.\"}),"
    "err?r.jsx(\"div\",{style:{fontSize:11.5,color:\"var(--red)\","
    "marginBottom:12},children:err}):null,"
    "r.jsx(\"button\",{onClick:pair,style:{height:30,padding:\"0 12px\","
    "background:\"var(--brand)\",color:\"#0b0f14\",border:\"none\","
    "borderRadius:\"var(--r-sm)\",fontSize:12.5,cursor:\"pointer\","
    "marginBottom:14},children:\"Appairer un appareil\"}),"
    "q?r.jsxs(\"div\",{style:{marginBottom:18},children:["
    "r.jsx(\"img\",{alt:\"QR d appairage\",width:264,height:264,"
    "src:\"data:image/png;base64,\"+q.qr_png_b64,"
    "style:{imageRendering:\"pixelated\",borderRadius:6}}),"
    "r.jsx(\"div\",{className:\"mono\",style:{fontSize:11,"
    "color:\"var(--ink-soft)\",marginTop:6},children:q.url}),"
    "r.jsx(\"div\",{style:{fontSize:11,color:\"var(--amber)\"},"
    "children:\"Valable \"+Math.round((q.expire_dans_s||300)/60)"
    "+\" minutes, un seul appareil.\"})]}):null,"
    "r.jsx(\"div\",{children:l.map(d=>r.jsxs(\"div\",{style:{display:\"flex\","
    "alignItems:\"center\",gap:10,padding:\"7px 0\","
    "borderBottom:\"1px solid var(--stroke)\"},children:["
    "r.jsx(\"span\",{style:{fontSize:12.5,color:\"var(--ink-strong)\","
    "flex:1},children:d.nom}),"
    "r.jsx(\"span\",{className:\"mono\",style:{fontSize:11,"
    "color:\"var(--ink-soft)\"},children:(d.cree||\"\").slice(0,10)}),"
    "d.revoque?r.jsx(\"span\",{style:{fontSize:11,color:\"var(--red)\"},"
    "children:\"revoque\"}):r.jsx(\"button\",{onClick:()=>rev(d.id),"
    "style:{fontSize:11,padding:\"4px 9px\",background:\"transparent\","
    "border:\"1px solid var(--stroke)\",borderRadius:6,"
    "color:\"var(--red)\",cursor:\"pointer\"},children:\"Revoquer\"})]},"
    "d.id))}),"
    "r.jsxs(\"div\",{style:{marginTop:18,padding:12,"
    "background:\"var(--bg-panel)\",borderLeft:\"2px solid var(--amber)\","
    "borderRadius:4},children:["
    "r.jsx(\"div\",{style:{fontSize:11.5,color:\"var(--ink)\","
    "marginBottom:6},children:\"Appareil perdu ? Revoquer ne suffit pas : "
    "les cles ont voyage dans l archive. Regenerez-les ici.\"}),"
    "rot.map(c=>r.jsx(\"a\",{href:c.url,target:\"_blank\",rel:\"noreferrer\","
    "style:{display:\"inline-block\",fontSize:11,marginRight:10,"
    "color:\"var(--brand)\"},children:c.nom},c.cle))]})]})}"
)

PATCHES = [
    ("A1-cles",
     A1,
     'const ym=["keys","accounts","personas","branding","pack","defaults",'
     '"paths","news","appearance","pricing","devices"];'),
    ("A2-menu",
     A2,
     '{k:"pricing",l:"Pricing & budget"},{k:"devices",l:"Paired devices"}]'),
    ("A3-branchement",
     A3,
     's==="pricing"&&r.jsx(DzPricing,{}),s==="devices"&&r.jsx(DzAppair,{})]'),
    ("A4-composant",
     A4,
     COMPOSANT + "function DzPricing(){"),
]

STABLE_PROBES = [
    ("rail-settings", '[{k:"keys",l:"API keys"}', 1),
    ("pricing", "function DzPricing(){", 1),
]

POST_COUNTS = [
    ('"appearance","pricing","devices"]', 1),
    ('{k:"devices",l:"Paired devices"}', 1),
    ('s==="devices"&&r.jsx(DzAppair,{})', 1),
    ("function DzAppair(){", 1),
    (MARKER, MARKER_ATTENDU),
]


def deltas():
    dc = sum(len(rp) - len(a) for _t, a, rp in PATCHES)
    db = sum(len(rp.encode("utf-8")) - len(a.encode("utf-8"))
             for _t, a, rp in PATCHES)
    return dc, db


def apply(s, anchor, replacement, tag):
    n = s.count(anchor)
    if n != 1:
        raise SystemExit(f"[{tag}] anchor count={n} (want 1). Aborting.")
    return s.replace(anchor, replacement)


def read_src(p):
    return p.read_text(encoding="utf-8", newline="")


def eol_stats(data):
    crlf = data.count(b"\r\n")
    return crlf, data.count(b"\n") - crlf, data.count(b"\r") - crlf


def resolve_root(args):
    if "--root" in args:
        return pathlib.Path(args[args.index("--root") + 1]).resolve()
    here = pathlib.Path(".").resolve()
    if (here / REL_BUNDLE).is_file():
        return here
    return pathlib.Path(__file__).resolve().parent.parent


def guard_downstream(bak):
    if not bak.exists():
        return
    stem = bak.name.rsplit(".bak_", 1)[0]
    for other in bak.parent.glob(stem + ".bak_*"):
        if other != bak and other.stat().st_mtime > bak.stat().st_mtime:
            raise SystemExit(
                f"[garde-chaine] backup aval detecte : {other.name}. "
                f"{TAG} doit rester le DERNIER maillon ; utilisez "
                "repatch_all.py --from dzappair.")


def ensure_tail_order(bak):
    stem = bak.name.rsplit(".bak_", 1)[0]
    others = [p.stat().st_mtime for p in bak.parent.glob(stem + ".bak_*")
              if p != bak]
    if not others:
        return False
    top = max(others)
    if bak.stat().st_mtime > top:
        return False
    t = max(time.time(), top + 1.0)
    os.utime(bak, (t, t))
    return True


def main():
    args = sys.argv[1:]
    dc, db = deltas()
    if "--deltas" in args:
        print(f"[{TAG}] delta +{dc} car / +{db} o")
        return
    root = resolve_root(args)
    bundle = root / REL_BUNDLE
    if not bundle.is_file():
        raise SystemExit(f"[{TAG}] bundle introuvable : {bundle}")
    bak = bundle.with_name(bundle.name + ".bak_" + TAG)
    if "--force-unchained" not in args:
        guard_downstream(bak)

    if "--check" in args:
        src = bak if bak.exists() else bundle
        s = read_src(src)
        if s.count(MARKER):
            raise SystemExit(f"[{TAG}] marqueur deja present x{s.count(MARKER)}")
        for tag, anchor, _r in PATCHES:
            n = s.count(anchor)
            if n != 1:
                raise SystemExit(f"[{tag}] anchor count={n} (want 1).")
        for name, probe, want in STABLE_PROBES:
            if s.count(probe) != want:
                raise SystemExit(f"[sonde {name}] count={s.count(probe)}")
        crlf, lf, cr = eol_stats(src.read_bytes())
        print(f"[{TAG}] applicable sur {src}")
        print(f"[{TAG}] {len(PATCHES)} ancres OK, {len(STABLE_PROBES)} sondes")
        print(f"[{TAG}] CRLF={crlf} LF-isole={lf} CR-isole={cr} ; "
              f"delta +{dc} car / +{db} o")
        return

    if not bak.exists():
        if MARKER in read_src(bundle):
            raise SystemExit(f"[{TAG}] marqueur present sans {bak.name}.")
        shutil.copy2(bundle, bak)
        if ensure_tail_order(bak):
            print("mtime du backup pousse en queue de chaine")
        print("backup ->", bak.name)
    else:
        shutil.copy2(bak, bundle)
        print("restore <-", bak.name)

    before = bundle.read_bytes()
    crlf0, lf0, cr0 = eol_stats(before)
    if lf0 or cr0:
        raise SystemExit(f"[{TAG}] fins de ligne non homogenes. Aborting.")
    s = read_src(bundle)
    chars0 = len(s)
    if MARKER in s:
        raise SystemExit(f"[{TAG}] backup empoisonne. Aborting.")
    for tag, anchor, repl in PATCHES:
        s = apply(s, anchor, repl, tag)
    with open(bundle, "w", encoding="utf-8", newline="") as fh:
        fh.write(s)

    after = bundle.read_bytes()
    crlf1, lf1, cr1 = eol_stats(after)
    problems = []
    if (crlf1, lf1, cr1) != (crlf0, 0, 0):
        problems.append("fins de ligne changees")
    if len(after) != len(before) + db:
        problems.append(f"taille {len(after)} o, attendu {len(before) + db}")
    if len(s) != chars0 + dc:
        problems.append(f"caracteres {len(s)}, attendu {chars0 + dc}")
    for probe, want in POST_COUNTS:
        if s.count(probe) != want:
            problems.append(f"post {probe!a} x{s.count(probe)} (want {want})")
    if problems:
        shutil.copy2(bak, bundle)
        raise SystemExit(f"[{TAG}] VERIFICATION ECHOUEE, bundle restaure :\n  "
                         + "\n  ".join(problems))
    print("OK - bundle patche (Settings > Paired devices).")
    print(f"   taille : {len(before)} -> {len(after)} o (+{db})")
    print("   suite  : copie .mjs + node --check, puis DEPLOYER le bundle")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    main()
```

- [ ] **Step 4 : Vérifier sans écrire**

Run : `python scripts/patch_bundle_dzappair.py --check`
Attendu :
```
[dzappair] applicable sur ...\index-BEOJX8L5.js
[dzappair] 4 ancres OK, 2 sondes
[dzappair] CRLF=11884 LF-isole=0 CR-isole=0 ; delta +NNNN car / +NNNN o
```

- [ ] **Step 5 : Appliquer**

Run : `python scripts/patch_bundle_dzappair.py`
Attendu : `backup -> index-BEOJX8L5.js.bak_dzappair`, puis `OK - bundle patche (Settings > Paired devices).` et une taille finale égale à `1395299 + delta`.

- [ ] **Step 6 : Vérifier la syntaxe JavaScript du bundle patché**

```bash
cp frontend/dist/assets/index-BEOJX8L5.js /tmp/dzappair-check.mjs && node --check /tmp/dzappair-check.mjs && echo SYNTAXE-OK && rm /tmp/dzappair-check.mjs
```
Attendu : `SYNTAXE-OK` sans autre sortie.

- [ ] **Step 7 : Vérifier l'inventaire (aucune fonction perdue)**

```bash
git show HEAD:frontend/dist/assets/index-BEOJX8L5.js | grep -o "function [A-Za-z_$][A-Za-z0-9_$]*(" | sort -u > /tmp/avant.txt
grep -o "function [A-Za-z_$][A-Za-z0-9_$]*(" frontend/dist/assets/index-BEOJX8L5.js | sort -u | comm -23 /tmp/avant.txt -
```
Attendu : **aucune ligne** (rien de perdu). Puis :
```bash
grep -o "function [A-Za-z_$][A-Za-z0-9_$]*(" frontend/dist/assets/index-BEOJX8L5.js | sort -u | comm -13 /tmp/avant.txt - ; rm /tmp/avant.txt
```
Attendu : exactement `function DzAppair(`.

- [ ] **Step 8 : Lancer le banc, vérifier qu'il passe**

Run : `cd backend && python tests/test_patch_dzappair.py`
Attendu : sept lignes `PASS`, puis `7/7 OK`.

- [ ] **Step 9 : Commit**

```bash
git add scripts/patch_bundle_dzappair.py frontend/dist/assets/index-BEOJX8L5.js backend/tests/test_patch_dzappair.py
git commit -m 'appairage : la section Paired devices dans Settings, un seul patch' -m 'Tag NEUF dzappair, backup dedie, EN QUEUE apres seedance25 (chaine mesuree
le 03/09). Quatre ancres, toutes a count == 1 : la liste des cles de section,
la derniere entree du rail, le dernier branchement de composant, le point
dinsertion avant DzPricing.

Le patch ne dessine aucun QR : le PNG vient du backend en base64, et il
naffiche jamais un jeton — la route nen rend quun, une fois, au telephone.
Verifie par node --check et par inventaire de fonctions : une seule ajoutee,
aucune perdue.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Tâche 7 : P2 — l'archive chiffrée lue par le téléphone, clés au coffre

**Files:**
- Create: `deepotus-mobile/src/lib/archive.ts`
- Create: `deepotus-mobile/src/lib/coffre.ts`
- Test: `deepotus-mobile/src/lib/__tests__/coffre.test.ts`

**Coût :** faible côté PC (**zéro** : l'archive appartient à R11 D1), moyen côté mobile. **Dépendance dure** : tant que R11 D1 n'a pas tranché entre bibliothèque AES embarquée et DPAPI, le format d'archive n'existe pas. La tâche pose donc l'**interface** et un format d'essai, et son banc ne mesure que le **coffre** et le **contrat** — jamais un déchiffrement inventé.

- [ ] **Step 1 : Écrire le contrat que R11 D1 devra tenir**

Ajouter à `deepotus-mobile/DECISIONS.md` :

````markdown
## D3 — Le format d'archive attendu de R11 D1

Le compagnon lit un fichier unique. Il n'invente rien : si l'un des quatre
champs manque, il refuse en le disant.

```json
{
  "dz_archive": 1,
  "kdf": "<nom et paramètres du dérivateur choisi par R11 D1>",
  "sel_b64": "<sel>",
  "nonce_b64": "<nonce>",
  "chiffre_b64": "<clés + défauts, chiffrés>"
}
```

Ce que le compagnon fait du contenu déchiffré : chaque paire `NOM=valeur`
va dans le coffre système sous la clé `dz.<NOM>`, et **rien** n'est écrit
dans SQLite ni dans un fichier. Si R11 D1 choisit DPAPI (lié au compte
Windows, sans mot de passe), l'archive n'est **pas** lisible par le
téléphone et cette tâche est bloquée : c'est la question à poser à R11
AVANT de commencer ce lot.
````

- [ ] **Step 2 : Écrire le test qui échoue**

`deepotus-mobile/src/lib/__tests__/coffre.test.ts` :

```typescript
import { CLES_ATTENDUES, verifierEnveloppe, nomDeCoffre } from "../archive";

jest.mock("expo-secure-store", () => {
  const magasin: Record<string, string> = {};
  return {
    setItemAsync: jest.fn(async (k: string, v: string) => { magasin[k] = v; }),
    getItemAsync: jest.fn(async (k: string) => magasin[k] ?? null),
    deleteItemAsync: jest.fn(async (k: string) => { delete magasin[k]; }),
    __magasin: magasin,
  };
});

test("le nom de coffre est prefixe et sans surprise", () => {
  expect(nomDeCoffre("FAL_KEY")).toBe("dz.FAL_KEY");
});

test("une enveloppe complete est acceptee", () => {
  expect(verifierEnveloppe({
    dz_archive: 1, kdf: "x", sel_b64: "a", nonce_b64: "b", chiffre_b64: "c",
  })).toEqual({ ok: true });
});

test("une enveloppe amputee est refusee EN DISANT ce qui manque", () => {
  const r = verifierEnveloppe({ dz_archive: 1, kdf: "x", sel_b64: "a" });
  expect(r.ok).toBe(false);
  expect(r.raison).toContain("nonce_b64");
  expect(r.raison).toContain("chiffre_b64");
});

test("une version d'archive inconnue est refusee", () => {
  const r = verifierEnveloppe({
    dz_archive: 2, kdf: "x", sel_b64: "a", nonce_b64: "b", chiffre_b64: "c",
  });
  expect(r.ok).toBe(false);
  expect(r.raison).toContain("version 2");
});

test("les cles qui depensent sont toutes attendues", () => {
  for (const k of ["FAL_KEY", "HEYGEN_API_KEY", "ELEVENLABS_API_KEY",
                   "X_API_KEY", "TELEGRAM_BOT_TOKEN"]) {
    expect(CLES_ATTENDUES).toContain(k);
  }
});

test("ranger puis relire passe par le coffre systeme, jamais par un fichier",
  async () => {
    const { rangerAuCoffre, lireDuCoffre } = await import("../coffre");
    const secure = require("expo-secure-store");
    await rangerAuCoffre({ FAL_KEY: "abc", TELEGRAM_BOT_TOKEN: "123:xyz" });
    expect(await lireDuCoffre("FAL_KEY")).toBe("abc");
    expect(Object.keys(secure.__magasin)).toEqual(
      ["dz.FAL_KEY", "dz.TELEGRAM_BOT_TOKEN"]);
  });
```

- [ ] **Step 3 : Lancer, vérifier l'échec**

Run : `cd /c/Users/olivi/deepotus-mobile && npm test`
Attendu : `Cannot find module '../archive'`, six tests en échec.

- [ ] **Step 4 : Écrire `archive.ts`**

```typescript
/** P2 — l'enveloppe de l'archive chiffrée produite par R11 D1.
 *  Ce module ne DÉCHIFFRE rien : il vérifie la forme et nomme les clés.
 *  Le déchiffrement viendra quand R11 D1 aura tranché son algorithme —
 *  d'ici là, inventer un format serait un mensonge que le banc ne
 *  pourrait pas mesurer. */

export const VERSION_ARCHIVE = 1;

/** Les noms de _ALLOWED_ENV_KEYS (backend/app/api/routes.py:3501) qui
 *  servent au téléphone : ceux qui dépensent, ceux qui publient. */
export const CLES_ATTENDUES = [
  "FAL_KEY",
  "HEYGEN_API_KEY",
  "MESHY_API_KEY",
  "ELEVENLABS_API_KEY",
  "ELEVENLABS_VOICE_ID_EN",
  "ELEVENLABS_VOICE_ID_FR",
  "ANTHROPIC_API_KEY",
  "OPENAI_API_KEY",
  "GEMINI_API_KEY",
  "X_API_KEY",
  "X_API_SECRET",
  "X_ACCESS_TOKEN",
  "X_ACCESS_SECRET",
  "TELEGRAM_BOT_TOKEN",
  "TELEGRAM_CHAT_ID",
] as const;

export type Verdict = { ok: true } | { ok: false; raison: string };

const CHAMPS = ["kdf", "sel_b64", "nonce_b64", "chiffre_b64"] as const;

export function verifierEnveloppe(o: any): Verdict {
  if (!o || typeof o !== "object") {
    return { ok: false, raison: "l archive n est pas un objet JSON" };
  }
  if (o.dz_archive !== VERSION_ARCHIVE) {
    return { ok: false, raison: `version ${o.dz_archive} inconnue (attendu ${VERSION_ARCHIVE})` };
  }
  const absents = CHAMPS.filter((c) => typeof o[c] !== "string" || !o[c]);
  if (absents.length) {
    return { ok: false, raison: `champs manquants : ${absents.join(", ")}` };
  }
  return { ok: true };
}

export function nomDeCoffre(cle: string): string {
  return `dz.${cle}`;
}
```

- [ ] **Step 5 : Écrire `coffre.ts`**

```typescript
import * as SecureStore from "expo-secure-store";
import { nomDeCoffre } from "./archive";

/** Les clés vont dans Keychain (iOS) / Keystore (Android) et NULLE PART
 *  ailleurs : ni SQLite, ni AsyncStorage, ni un fichier. */
export async function rangerAuCoffre(cles: Record<string, string>): Promise<void> {
  for (const [k, v] of Object.entries(cles)) {
    if (!v) continue;
    await SecureStore.setItemAsync(nomDeCoffre(k), v);
  }
}

export async function lireDuCoffre(cle: string): Promise<string | null> {
  return SecureStore.getItemAsync(nomDeCoffre(cle));
}

export async function viderLeCoffre(cles: readonly string[]): Promise<void> {
  for (const k of cles) {
    await SecureStore.deleteItemAsync(nomDeCoffre(k));
  }
}
```

- [ ] **Step 6 : Lancer, vérifier que tout passe**

Run : `cd /c/Users/olivi/deepotus-mobile && npm test`
Attendu : `Tests: 8 passed, 8 total` (les 2 de la tâche 1 plus les 6 d'ici).

- [ ] **Step 7 : Commit**

```bash
cd /c/Users/olivi/deepotus-mobile
git add -A
git commit -m 'archive : lenveloppe verifiee, les cles au coffre systeme, rien dinvente' -m 'Le module ne dechiffre RIEN : R11 D1 na pas encore tranche entre une
bibliotheque AES embarquee et DPAPI, et inventer un format serait un
mensonge quaucun banc ne pourrait mesurer. Le contrat attendu est ecrit
dans DECISIONS.md, et le refus NOMME le champ manquant.

Le coffre systeme est le SEUL magasin : le banc verifie que rien datterit
ailleurs, en listant les cles du magasin simule.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Tâche 8 : P3 — export du lot validé et retour d'état (PC)

**Files:**
- Create: `backend/app/services/sync_lot.py`
- Modify: `backend/app/api/routes.py` (à la fin, après les routes d'appairage)
- Test: `backend/tests/test_sync_lot.py`

**Coût :** faible. Aucune migration (`ScheduledPost` a déjà `status`, `run_at`, `channels`, `caption`, `job_id`, `error`, `posted_at` — mesuré `storage.py:82-121`), aucun patch de bundle. **Décision de conception : le lot ne porte AUCUN jeton** — ils sont déjà dans le coffre du téléphone (tâche 7). C'est la conséquence directe de D-D.

- [ ] **Step 1 : Écrire le banc qui échoue**

Créer `backend/tests/test_sync_lot.py` :

```python
# -*- coding: utf-8 -*-
"""P3 — le lot de la semaine exporté vers le téléphone, l'état qui revient.

    python tests/test_sync_lot.py               # depuis backend/
"""
import asyncio
import os
import pathlib
import sys
import tempfile
from datetime import datetime, timedelta

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


def _semer():
    """Trois posts : un dû demain, un dû dans 30 jours, un déjà publié.

    IDEMPOTENTE : plusieurs tests du MÊME processus l'appellent, et
    réinsérer les mêmes clés primaires casserait sur la contrainte UNIQUE
    dès le deuxième appel. On vide d'abord."""
    from sqlalchemy import delete as _del
    from app.services.storage import (JobRecord, ScheduledPost, init_db,
                                      async_session_factory)
    asyncio.run(init_db())
    video = pathlib.Path(_tmp, "outputs", "clip.mp4")
    video.write_bytes(b"\x00" * 2048)

    async def vider():
        async with async_session_factory() as s:
            await s.execute(_del(ScheduledPost))
            await s.execute(_del(JobRecord))
            await s.commit()
    asyncio.run(vider())

    async def poser():
        async with async_session_factory() as s:
            job = JobRecord(id="job-1", status="completed",
                            image_filename="a.png",
                            final_video_path=str(video))
            s.add(job)
            s.add(ScheduledPost(
                id="p-demain", title="Demain", caption="Une legende",
                channels="x,telegram",
                run_at=datetime.utcnow() + timedelta(days=1),
                status="scheduled", mode="auto", job_id="job-1"))
            s.add(ScheduledPost(
                id="p-loin", title="Trop loin", caption="",
                channels="x", run_at=datetime.utcnow() + timedelta(days=30),
                status="scheduled", mode="auto"))
            s.add(ScheduledPost(
                id="p-fait", title="Deja fait", caption="",
                channels="x", run_at=datetime.utcnow() - timedelta(days=1),
                status="posted", mode="auto"))
            await s.commit()
    asyncio.run(poser())


def test_le_lot_ne_prend_que_la_fenetre_demandee():
    from app.services import sync_lot
    _semer()
    lot = asyncio.run(sync_lot.lot(jours=7))
    ids = {p["id"] for p in lot["posts"]}
    assert ids == {"p-demain"}, ids


def test_le_lot_ne_contient_AUCUN_jeton():
    """Décision D-D : les jetons voyagent par l'archive, pas par l'API."""
    import json
    from app.services import sync_lot
    _semer()
    brut = json.dumps(asyncio.run(sync_lot.lot(jours=7)))
    for interdit in ("X_API_KEY", "X_ACCESS_TOKEN", "TELEGRAM_BOT_TOKEN",
                     "api_key", "secret", "token"):
        assert interdit.lower() not in brut.lower(), interdit


def test_le_post_porte_sa_video_son_poids_et_son_empreinte():
    from app.services import sync_lot
    _semer()
    p = asyncio.run(sync_lot.lot(jours=7))["posts"][0]
    assert p["media"]["nom"] == "clip.mp4"
    assert p["media"]["taille"] == 2048
    assert len(p["media"]["sha256"]) == 64
    assert p["canaux"] == ["x", "telegram"]
    assert p["legende"] == "Une legende"
    assert p["run_at"].endswith("Z"), p["run_at"]


def test_letat_publie_revient_dans_la_base():
    """Miroir : on relit la LIGNE, pas la réponse de la route."""
    from sqlalchemy import text
    from app.services import sync_lot
    from app.services.storage import _engine
    _semer()
    asyncio.run(sync_lot.appliquer_etat([
        {"id": "p-demain", "statut": "posted", "detail": "x: ok",
         "publie_a": "2026-09-04T09:00:00Z", "appareil": "iPhone de Oli"}]))

    async def lire():
        async with _engine.begin() as conn:
            r = await conn.execute(text(
                "SELECT status, posted_at, error FROM scheduled_posts "
                "WHERE id = 'p-demain'"))
            return r.fetchone()

    statut, publie, erreur = asyncio.run(lire())
    assert statut == "posted", statut
    assert publie is not None
    assert "iPhone de Oli" in (erreur or ""), erreur


def test_un_echec_du_telephone_revient_en_ready_avec_sa_raison():
    from sqlalchemy import text
    from app.services import sync_lot
    from app.services.storage import _engine
    _semer()
    asyncio.run(sync_lot.appliquer_etat([
        {"id": "p-demain", "statut": "failed",
         "detail": "x: 403 duplicate content", "appareil": "iPhone de Oli"}]))

    async def lire():
        async with _engine.begin() as conn:
            r = await conn.execute(text(
                "SELECT status, error FROM scheduled_posts WHERE id='p-demain'"))
            return r.fetchone()

    statut, erreur = asyncio.run(lire())
    assert statut == "ready", statut
    assert "duplicate content" in erreur


def test_un_post_deja_publie_par_le_PC_nest_pas_ecrase():
    """Le téléphone rentre après le PC : le dernier mot revient au PC."""
    from sqlalchemy import text
    from app.services import sync_lot
    from app.services.storage import _engine
    _semer()
    conflits = asyncio.run(sync_lot.appliquer_etat([
        {"id": "p-fait", "statut": "failed", "detail": "x: timeout",
         "appareil": "iPhone de Oli"}]))
    assert len(conflits) == 1 and conflits[0]["id"] == "p-fait"

    async def lire():
        async with _engine.begin() as conn:
            r = await conn.execute(text(
                "SELECT status FROM scheduled_posts WHERE id='p-fait'"))
            return r.fetchone()[0]

    assert asyncio.run(lire()) == "posted"


TESTS = [test_le_lot_ne_prend_que_la_fenetre_demandee,
         test_le_lot_ne_contient_AUCUN_jeton,
         test_le_post_porte_sa_video_son_poids_et_son_empreinte,
         test_letat_publie_revient_dans_la_base,
         test_un_echec_du_telephone_revient_en_ready_avec_sa_raison,
         test_un_post_deja_publie_par_le_PC_nest_pas_ecrase]

if __name__ == "__main__":
    failed = []
    for t in TESTS:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed.append(t.__name__)
            print(f"FAIL {t.__name__}: {e!r}")
    print(f"\n{len(TESTS) - len(failed)}/{len(TESTS)} OK")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run : `cd backend && python tests/test_sync_lot.py`
Attendu : six `FAIL ... ModuleNotFoundError("No module named 'app.services.sync_lot'")`, `0/6 OK`.

- [ ] **Step 3 : Écrire le service**

Créer `backend/app/services/sync_lot.py` :

```python
# -*- coding: utf-8 -*-
"""P3 — « le Scheduler dans la poche » : le lot part, l'état revient.

CE QUE LE LOT NE CONTIENT PAS, ET POURQUOI : aucun jeton, aucune clé. Le
téléphone les a déjà par l'archive chiffrée (R11 D1, tâche 7). Le backend
ne fait jamais sortir un secret par le réseau — c'est la décision D-D, et
`_require_localhost` (routes.py:3547) en est l'autre moitié.

QUI GAGNE EN CAS DE CONFLIT : le PC. Un post que le PC a déjà passé à
`posted` ne redevient jamais `ready` parce que le téléphone rentre avec un
échec vieux de trois heures. Le conflit est RENDU, pas avalé.
"""
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

from loguru import logger
from sqlalchemy import select as _select

PROTOCOLE = 1
_EMPREINTES: dict[tuple[str, int], str] = {}


def _sha256(chemin: Path) -> str:
    """sha256 avec cache sur (chemin, mtime_ns) — un rendu fini ne change
    plus, et la synchro relit le manifeste souvent."""
    try:
        cle = (str(chemin), chemin.stat().st_mtime_ns)
    except OSError:
        return ""
    if cle in _EMPREINTES:
        return _EMPREINTES[cle]
    h = hashlib.sha256()
    with open(chemin, "rb") as fh:
        for bloc in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloc)
    if len(_EMPREINTES) > 4096:
        _EMPREINTES.clear()
    _EMPREINTES[cle] = h.hexdigest()
    return _EMPREINTES[cle]


def _iso(d: datetime | None) -> str | None:
    return d.replace(microsecond=0).isoformat() + "Z" if d else None


async def lot(jours: int = 7) -> dict:
    """Les posts actionnables des `jours` prochains, avec leur média."""
    from app.services.storage import (JobRecord, ScheduledPost,
                                      async_session_factory)
    limite = datetime.utcnow() + timedelta(days=jours)
    posts = []
    async with async_session_factory() as session:
        res = await session.execute(
            _select(ScheduledPost)
            .where(ScheduledPost.status.in_(("scheduled", "ready")))
            .where(ScheduledPost.run_at <= limite)
            .order_by(ScheduledPost.run_at.asc()))
        for p in res.scalars().all():
            media = None
            if p.job_id:
                job = await session.get(JobRecord, p.job_id)
                chemin = Path(job.final_video_path) if job and \
                    job.final_video_path else None
                if chemin and chemin.is_file():
                    media = {"nom": chemin.name,
                             "taille": chemin.stat().st_size,
                             "sha256": _sha256(chemin),
                             "url": f"/api/sync/media/{p.job_id}"}
            posts.append({
                "id": p.id,
                "titre": p.title,
                "legende": p.caption or "",
                "canaux": [c for c in (p.channels or "").split(",") if c],
                "run_at": _iso(p.run_at),
                "mode": p.mode,
                "statut": p.status,
                "media": media,
            })
    return {"protocole": PROTOCOLE, "posts": posts,
            "genere_a": _iso(datetime.utcnow())}


async def appliquer_etat(rapports: list[dict]) -> list[dict]:
    """Le téléphone rentre : on applique, sauf là où le PC a tranché.
    Rend la liste des conflits, jamais silencieux."""
    from app.services.storage import ScheduledPost, async_session_factory
    conflits: list[dict] = []
    async with async_session_factory() as session:
        for r in rapports or []:
            ident = str(r.get("id") or "")
            statut = str(r.get("statut") or "")
            if statut not in ("posted", "failed"):
                continue
            p = await session.get(ScheduledPost, ident)
            if p is None:
                conflits.append({"id": ident, "raison": "post inconnu"})
                continue
            if p.status == "posted":
                conflits.append({
                    "id": ident, "raison": "deja publie par le PC",
                    "rapport_ignore": statut})
                continue
            appareil = str(r.get("appareil") or "telephone")[:60]
            detail = str(r.get("detail") or "")[:400]
            if statut == "posted":
                p.status = "posted"
                brut = str(r.get("publie_a") or "").replace("Z", "")
                try:
                    p.posted_at = datetime.fromisoformat(brut)
                except ValueError:
                    p.posted_at = datetime.utcnow()
                p.error = f"publie par {appareil}: {detail}"[:500]
            else:
                p.status = "ready"
                p.error = f"echec sur {appareil}: {detail}"[:500]
        await session.commit()
    if conflits:
        logger.warning(f"sync_lot: {len(conflits)} conflit(s) au retour")
    return conflits
```

- [ ] **Step 4 : Lancer, vérifier que ça passe**

Run : `cd backend && python tests/test_sync_lot.py`
Attendu : six lignes `PASS`, puis `6/6 OK`.

- [ ] **Step 5 : Ajouter les routes**

À la fin de `backend/app/api/routes.py` :

```python
# ── P3 : le lot de la semaine, dans la poche ────────────────────────────────
# Ouvertes au LAN AVEC jeton (la garde de main.py s'en charge) ; elles ne
# renvoient jamais de secret : le téléphone a ses clés par l'archive.

@router.get("/sync/lot")
async def sync_lot_get(jours: int = 7):
    from app.services import sync_lot as _sl
    return await _sl.lot(jours=jours)


@router.post("/sync/lot/etat")
async def sync_lot_etat(body: dict):
    from app.services import sync_lot as _sl
    conflits = await _sl.appliquer_etat((body or {}).get("rapports") or [])
    return {"applique": True, "conflits": conflits}


@router.get("/sync/media/{job_id}")
async def sync_media(job_id: str):
    """La vidéo d'un rendu, en Range pour reprendre après une coupure."""
    from fastapi.responses import FileResponse
    j = await Pipeline.get_job(job_id)
    if not j or not j.final_video_path:
        raise HTTPException(404, "aucune video pour ce rendu")
    p = Path(j.final_video_path)
    if not p.is_file():
        raise HTTPException(404, "fichier absent du magasin")
    return FileResponse(str(p), media_type="video/mp4", filename=p.name)
```

- [ ] **Step 6 : Vérifier la route de bout en bout**

Ajouter à `backend/tests/test_sync_lot.py`, avant `TESTS` :

```python
def test_la_route_du_lot_repond_au_lan_avec_un_jeton():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services import appairage
    _semer()

    async def coquille(scope, receive, send):
        if scope["type"] == "http":
            scope = dict(scope)
            scope["client"] = ("192.168.1.42", 50000)
        await app(scope, receive, send)

    local = TestClient(app)
    s = local.post("/api/pair/start").json()
    lan = TestClient(coquille)
    jeton = lan.post("/api/pair/claim",
                     json={"secret": s["secret"], "nom": "banc"}).json()["jeton"]
    r = lan.get("/api/sync/lot?jours=7",
                headers={"Authorization": f"Bearer {jeton}"})
    assert r.status_code == 200, (r.status_code, r.text[:200])
    assert [p["id"] for p in r.json()["posts"]] == ["p-demain"]
    asyncio.run(appairage.revoquer_tout())
```

et l'ajouter à `TESTS`. Run : `cd backend && python tests/test_sync_lot.py`
Attendu : sept lignes `PASS`, `7/7 OK`.

- [ ] **Step 7 : Commit**

```bash
git add backend/app/services/sync_lot.py backend/app/api/routes.py backend/tests/test_sync_lot.py
git commit -m 'lot : le Scheduler part dans la poche, letat revient, le PC a le dernier mot' -m 'Le lot porte videos, legendes, heures et canaux — et AUCUN jeton : le
telephone a ses cles par larchive chiffree, jamais par lAPI. Le banc le
mesure en cherchant les mots interdits dans le JSON entier.

Au retour, un post que le PC a deja passe a posted nest jamais ecrase : le
conflit est RENDU au telephone, pas avale. Chaque media porte sa taille et
son sha256 pour que le transfert se verifie.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Tâche 9 : P3 — mesurer l'arrière-plan iOS et Android, fixer la promesse

**Files:**
- Create: `deepotus-mobile/docs/arriere-plan.md`
- Modify: `deepotus-mobile/DECISIONS.md`

**Coût :** nul en code, **décisif** en promesse. C'est la tâche qui empêche de promettre une publication silencieuse qu'iOS ne garantit pas. Rien n'est écrit dans le dépôt PC.

- [ ] **Step 1 : Mesurer iOS**

```
WebFetch url="https://developer.apple.com/documentation/backgroundtasks/bgtaskscheduler" prompt="Does BGTaskScheduler guarantee execution at an exact requested time? Quote the sentences about earliestBeginDate, system discretion and scheduling. List every reason a submitted task can be skipped."
```

Puis :

```
WebFetch url="https://developer.apple.com/documentation/backgroundtasks/bgapprefreshtaskrequest/earliestbegindate" prompt="Quote exactly what earliestBeginDate means: is it a deadline, a hint, or a guarantee? What happens if the app is force-quit by the user?"
```

- [ ] **Step 2 : Mesurer Android**

```
WebFetch url="https://developer.android.com/topic/libraries/architecture/workmanager" prompt="Is WorkManager suitable for exact-time execution? Quote what the page says about minimum periodic interval and deferrability."
```

```
WebFetch url="https://developer.android.com/develop/background-work/services/alarms/schedule-exact-alarms" prompt="What permission is needed for exact alarms on Android 12, 13 and 14+? Quote SCHEDULE_EXACT_ALARM and USE_EXACT_ALARM eligibility rules and how the user grants them. Which app categories are eligible for USE_EXACT_ALARM?"
```

- [ ] **Step 3 : Écrire le verdict**

Créer `deepotus-mobile/docs/arriere-plan.md` :

```markdown
# Ce que l'arrière-plan permet vraiment — mesuré le <date du jour>

## iOS
(citations exactes du step 1, avec l'URL et la date)

**Conséquence :** <une phrase>

## Android
(citations exactes du step 2, avec l'URL et la date)

**Conséquence :** <une phrase>

## La promesse, et rien de plus

**Ce qui est PROMIS, sur les deux plateformes :**
à l'heure du post, une **notification locale** s'affiche ; un appui ouvre
l'application, qui publie **au premier plan**, montre le résultat, et le
renvoie au PC à la prochaine synchronisation.

**Ce qui est un OBJECTIF MESURÉ, jamais promis :**
la publication **silencieuse**, sans ouvrir l'application. Elle sera
tentée par <l'API retenue au step 1/2> et **mesurée sur dix posts réels
consécutifs** avant d'apparaître dans l'interface. Tant que ces dix
mesures n'existent pas, l'écran dit « rappel à 9 h 00 », jamais
« publication à 9 h 00 ».

**Ce qui n'est PAS promis du tout :**
publier si l'utilisateur a **forcé la fermeture** de l'application, ou si
le téléphone est **hors réseau** à l'heure dite. Dans les deux cas la
notification reste, et le post part au premier lancement suivant, avec
son retard affiché.
```

- [ ] **Step 4 : Reporter la décision**

Ajouter à `deepotus-mobile/DECISIONS.md` :

```markdown
## D4 — La promesse de P3, arrêtée le <date du jour>
Notification locale à l'heure, publication au premier plan. La publication
silencieuse est un objectif mesuré (docs/arriere-plan.md), pas une promesse.
Cette décision vient des citations, pas d'un souvenir.
```

- [ ] **Step 5 : Commit**

```bash
cd /c/Users/olivi/deepotus-mobile
git add -A
git commit -m 'arriere-plan : ce quiOS et Android permettent, cite, et la promesse qui en decoule' -m 'La recommandation du brief etait ecrite de memoire. Les citations exactes
des deux documentations officielles sont maintenant dans docs/arriere-plan.md,
avec leur URL et leur date.

Promis : une notification locale a lheure, puis la publication au premier
plan. Objectif mesure, jamais promis : la publication silencieuse — dix
posts reels consecutifs avant de lecrire dans linterface.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Tâche 10 : P3 — la file du lot, la notification à l'heure, la publication (mobile)

**Files:**
- Create: `deepotus-mobile/src/lib/pc.ts` (le client du PC : jeton, appels)
- Create: `deepotus-mobile/src/lib/lot.ts` (la file locale, SQLite)
- Create: `deepotus-mobile/src/lib/publier.ts` (X et Telegram depuis le téléphone)
- Create: `deepotus-mobile/src/lib/rappels.ts` (notifications locales)
- Test: `deepotus-mobile/src/lib/__tests__/lot.test.ts`, `deepotus-mobile/src/lib/__tests__/publier.test.ts`

**Coût :** élevé. C'est le cœur du premier lot. Deux adaptateurs seulement (X, Telegram) — les trois autres canaux appartiennent à **R6 P1** et passent d'ici là par le partage vers l'app native. **Bornes rappelées, vérifiées le 03/09** : X gratuit **500 posts/mois**, et ce sont **les mêmes jetons** donc **le même compteur** que le PC.

- [ ] **Step 1 : Écrire les tests qui échouent**

`deepotus-mobile/src/lib/__tests__/lot.test.ts` :

```typescript
import { aPublier, retard, resumeRapport } from "../lot";

const T = (iso: string) => new Date(iso).getTime();

test("un post du a l heure passee est a publier", () => {
  const posts = [
    { id: "a", run_at: "2026-09-04T09:00:00Z", statut: "scheduled" },
    { id: "b", run_at: "2026-09-04T18:00:00Z", statut: "scheduled" },
    { id: "c", run_at: "2026-09-04T08:00:00Z", statut: "posted" },
  ] as any;
  expect(aPublier(posts, T("2026-09-04T09:30:00Z")).map((p) => p.id))
    .toEqual(["a"]);
});

test("le retard est dit en minutes, jamais masque", () => {
  expect(retard("2026-09-04T09:00:00Z", T("2026-09-04T09:47:00Z"))).toBe(47);
  expect(retard("2026-09-04T09:00:00Z", T("2026-09-04T08:59:00Z"))).toBe(0);
});

test("le rapport renvoye au PC porte lappareil et le detail", () => {
  const r = resumeRapport("a", true, "x: ok", "iPhone de Oli",
                          T("2026-09-04T09:47:00Z"));
  expect(r).toEqual({
    id: "a", statut: "posted", detail: "x: ok",
    publie_a: "2026-09-04T09:47:00Z", appareil: "iPhone de Oli",
  });
  expect(resumeRapport("a", false, "x: 403", "iPhone de Oli",
                       T("2026-09-04T09:47:00Z")).statut).toBe("failed");
});
```

`deepotus-mobile/src/lib/__tests__/publier.test.ts` :

```typescript
import { enteteOAuth, corpsTelegram, BORNES } from "../publier";

test("l entete OAuth 1.0a porte les six champs obligatoires", () => {
  const e = enteteOAuth("POST", "https://api.x.com/2/tweets",
    { key: "ck", secret: "cs" }, { key: "at", secret: "as" },
    { nonce: "abc", timestamp: "1780000000" });
  for (const champ of ["oauth_consumer_key", "oauth_nonce",
                       "oauth_signature", "oauth_signature_method",
                       "oauth_timestamp", "oauth_token"]) {
    expect(e).toContain(champ);
  }
  expect(e).toContain('oauth_signature_method="HMAC-SHA1"');
  expect(e.startsWith("OAuth ")).toBe(true);
});

test("deux signatures du meme appel sont identiques", () => {
  const a = enteteOAuth("POST", "https://api.x.com/2/tweets",
    { key: "ck", secret: "cs" }, { key: "at", secret: "as" },
    { nonce: "abc", timestamp: "1780000000" });
  const b = enteteOAuth("POST", "https://api.x.com/2/tweets",
    { key: "ck", secret: "cs" }, { key: "at", secret: "as" },
    { nonce: "abc", timestamp: "1780000000" });
  expect(a).toBe(b);
});

test("le corps Telegram nomme le canal et la legende", () => {
  const f = corpsTelegram("-100123", "Une legende", "clip.mp4");
  expect(f.get("chat_id")).toBe("-100123");
  expect(f.get("caption")).toBe("Une legende");
});

test("les bornes des reseaux sont ecrites, avec leur date de mesure", () => {
  expect(BORNES.x.postsParMois).toBe(500);
  expect(BORNES.x.mesureLe).toBe("2026-09-03");
  expect(BORNES.x.note).toContain("memes jetons");
});
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run : `cd /c/Users/olivi/deepotus-mobile && npm test`
Attendu : `Cannot find module '../lot'` et `'../publier'`, sept tests en échec.

- [ ] **Step 3 : Écrire `lot.ts`**

```typescript
export type Post = {
  id: string;
  titre?: string;
  legende?: string;
  canaux?: string[];
  run_at: string;
  statut: string;
  media?: { nom: string; taille: number; sha256: string; url: string } | null;
};

export type Rapport = {
  id: string;
  statut: "posted" | "failed";
  detail: string;
  publie_a: string;
  appareil: string;
};

/** Les posts dont l'heure est passée et qui n'ont pas encore abouti. */
export function aPublier(posts: Post[], maintenant: number): Post[] {
  return posts.filter(
    (p) => p.statut === "scheduled" && new Date(p.run_at).getTime() <= maintenant,
  );
}

/** Le retard en minutes entières. Il est AFFICHÉ : un post parti à 9 h 47
 *  au lieu de 9 h 00 doit le dire, pas faire semblant. */
export function retard(runAt: string, maintenant: number): number {
  const d = maintenant - new Date(runAt).getTime();
  return d <= 0 ? 0 : Math.floor(d / 60000);
}

export function resumeRapport(
  id: string, ok: boolean, detail: string, appareil: string, quand: number,
): Rapport {
  return {
    id,
    statut: ok ? "posted" : "failed",
    detail,
    publie_a: new Date(quand).toISOString().replace(/\.\d{3}Z$/, "Z"),
    appareil,
  };
}
```

- [ ] **Step 4 : Écrire `publier.ts`**

```typescript
import OAuth from "oauth-1.0a";
import HmacSHA1 from "crypto-js/hmac-sha1";
import Base64 from "crypto-js/enc-base64";

/** Bornes VÉRIFIÉES le 03/09/2026 (docs.x.com, developers.facebook.com,
 *  developers.google.com, developers.tiktok.com — reprises de R6 et R12).
 *  Elles valent DEPUIS LE TÉLÉPHONE aussi : ce sont les mêmes jetons, donc
 *  le même compteur que le PC. */
export const BORNES = {
  x: {
    postsParMois: 500,
    lecturesParMois: 100,
    mesureLe: "2026-09-03",
    note: "palier gratuit, par projet ; memes jetons que le PC donc meme compteur",
  },
  instagram: {
    postsPar24h: 50,
    mesureLe: "2026-09-03",
    note: "compte professionnel obligatoire ; adaptateur API = R6 P1",
  },
  youtube: {
    envoisParJour: 100,
    mesureLe: "2026-09-03",
    note: "videos.insert, seau de quota propre ; adaptateur API = R6 P1",
  },
  tiktok: {
    postsParJour: 15,
    mesureLe: "2026-09-03",
    note: "sans audit : SELF_ONLY, compte prive ; adaptateur API = R6 P1",
  },
} as const;

export type Jetons = { key: string; secret: string };

/** L'en-tête OAuth 1.0a d'un appel X. `fixe` sert au banc : sans lui, le
 *  nonce et l'horodatage rendraient deux signatures incomparables. */
export function enteteOAuth(
  methode: string,
  url: string,
  client: Jetons,
  utilisateur: Jetons,
  fixe?: { nonce: string; timestamp: string },
): string {
  const oauth = new OAuth({
    consumer: client,
    signature_method: "HMAC-SHA1",
    hash_function(base: string, cle: string) {
      return Base64.stringify(HmacSHA1(base, cle));
    },
    ...(fixe
      ? {
          nonce_length: 32,
          getNonce: () => fixe.nonce,
          getTimeStamp: () => Number(fixe.timestamp),
        }
      : {}),
  } as any);
  const donnees = oauth.authorize(
    { url, method: methode },
    { key: utilisateur.key, secret: utilisateur.secret },
  );
  if (fixe) {
    (donnees as any).oauth_nonce = fixe.nonce;
    (donnees as any).oauth_timestamp = Number(fixe.timestamp);
  }
  return oauth.toHeader(donnees).Authorization;
}

export function corpsTelegram(
  chatId: string, legende: string, nomFichier: string,
): FormData {
  const f = new FormData();
  f.append("chat_id", chatId);
  f.append("caption", legende);
  f.append("supports_streaming", "true");
  f.append("__nom", nomFichier);
  return f;
}
```

- [ ] **Step 5 : Lancer, vérifier que tout passe**

Run : `cd /c/Users/olivi/deepotus-mobile && npm test`
Attendu : `Tests: 15 passed, 15 total`.
Si le test « deux signatures identiques » échoue avec un nonce différent, c'est que `getNonce`/`getTimeStamp` ne sont pas honorés par la version installée d'`oauth-1.0a` : la réécriture explicite des deux champs juste avant `toHeader` (déjà dans le code) doit suffire ; sinon, remplacer `oauth.authorize` par un calcul direct de la base de signature.

- [ ] **Step 6 : Écrire `pc.ts` et `rappels.ts`**

`deepotus-mobile/src/lib/pc.ts` :

```typescript
import * as SecureStore from "expo-secure-store";
import { userAgent, PROTOCOLE } from "./version";

const CLE_JETON = "dz.appairage.jeton";
const CLE_HOTE = "dz.appairage.hote";

export async function enregistrerAppairage(
  hote: string, port: number, jeton: string,
): Promise<void> {
  await SecureStore.setItemAsync(CLE_JETON, jeton);
  await SecureStore.setItemAsync(CLE_HOTE, `${hote}:${port}`);
}

export async function appeler(
  chemin: string, init: RequestInit = {}, nomAppareil = "telephone",
): Promise<Response> {
  const jeton = await SecureStore.getItemAsync(CLE_JETON);
  const hote = await SecureStore.getItemAsync(CLE_HOTE);
  if (!jeton || !hote) throw new Error("appareil non appaire");
  return fetch(`http://${hote}${chemin}`, {
    ...init,
    headers: {
      ...(init.headers || {}),
      Authorization: `Bearer ${jeton}`,
      "User-Agent": userAgent(nomAppareil),
      "X-DZ-Protocole": String(PROTOCOLE),
    },
  });
}
```

`deepotus-mobile/src/lib/rappels.ts` :

```typescript
import * as Notifications from "expo-notifications";
import type { Post } from "./lot";

/** UNE notification locale par post, à son heure. C'est ce que le plan
 *  PROMET (docs/arriere-plan.md) : la publication silencieuse reste un
 *  objectif mesuré, elle n'est jamais annoncée ici. */
export async function programmerRappel(p: Post): Promise<string> {
  return Notifications.scheduleNotificationAsync({
    content: {
      title: `A publier : ${p.titre || p.id}`,
      body: (p.legende || "").slice(0, 120),
      data: { postId: p.id },
    },
    trigger: { date: new Date(p.run_at) } as any,
  });
}

export async function annulerTousLesRappels(): Promise<void> {
  await Notifications.cancelAllScheduledNotificationsAsync();
}
```

- [ ] **Step 7 : Commit**

```bash
cd /c/Users/olivi/deepotus-mobile
git add -A
git commit -m 'lot : la file du telephone, le rappel a lheure, X et Telegram' -m 'Le telephone tient sa file, affiche le retard au lieu de le masquer, et
renvoie au PC un rapport nomme (appareil, detail, heure reelle).

Deux adaptateurs seulement : X (OAuth 1.0a signe sur le telephone) et
Telegram. Les trois autres canaux appartiennent a R6 P1 et passent dici la
par le partage vers lapp native. Les bornes des reseaux sont dans le code
avec leur DATE DE MESURE, et le fait quun tir depuis le telephone consomme
le MEME compteur que le PC.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Tâche 11 : Fin du lot 1 — la recette complète, mesurée de bout en bout

**Files:**
- Test: `backend/tests/test_appairage.py`, `test_appairage_routes.py`, `test_qrcode_min.py`, `test_sync_lot.py`, `test_patch_dzappair.py`
- Modify: `CHANGELOG.md`

**Coût :** nul en code. C'est la porte de sortie du lot : rien ne passe au lot 2 avant qu'elle soit verte.

- [ ] **Step 1 : Les cinq bancs, un processus chacun**

```bash
cd backend
for f in test_appairage.py test_appairage_routes.py test_qrcode_min.py test_sync_lot.py test_patch_dzappair.py; do
  echo "=== $f"; python tests/$f | tail -2
done
```
Attendu : `7/7 OK`, `11/11 OK`, `5/5 OK`, `7/7 OK`, `7/7 OK`.

- [ ] **Step 2 : La suite entière, pour la non-régression**

Run : `powershell -ExecutionPolicy Bypass -File scripts\run-tests.ps1`
Attendu : le récapitulatif final ne liste **aucun** fichier dans `failed`.

- [ ] **Step 3 : Les bancs mobiles**

Run : `cd /c/Users/olivi/deepotus-mobile && npm test`
Attendu : `Tests: 15 passed, 15 total`.

- [ ] **Step 4 : Noter le lot au journal**

Ajouter en tête de la section non publiée de `CHANGELOG.md` :

```markdown
### Compagnon mobile — lot 1 (appairage, archive, le Scheduler dans la poche)
- Table `devices`, appairage par QR (adresse LAN + secret a usage unique de
  5 minutes), jeton d'appareil revocable, cinq appareils au plus.
- Garde de jeton sur **toute** route hors loopback ; `_require_localhost`
  intact — les cles ne sortent jamais par le reseau.
- `HOST` configurable jusqu'au lanceur ; le defaut reste `127.0.0.1`.
- Encodeur QR stdlib (version 4-L) : aucune dependance ajoutee.
- Export du lot de la semaine (videos, legendes, heures, canaux — **aucun
  jeton**) et retour d'etat, le PC gardant le dernier mot.
- Settings > Paired devices (un seul patch du bundle, tag `dzappair`).
```

- [ ] **Step 5 : Commit**

```bash
git add CHANGELOG.md
git commit -m 'lot 1 : appairage, archive et Scheduler dans la poche, mesures' -m 'Cinq bancs verts un processus chacun, la suite entiere sans regression, et
les quinze bancs du depot mobile. Le journal dit ce qui est livre et ce qui
ne lest pas : la publication silencieuse nest toujours pas promise.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Lot 2 — synchronisation, notifications, dépenses (P4 + P5 + P6)

### Tâche 12 : P4 — le manifeste de synchronisation (PC)

**Files:**
- Modify: `backend/app/services/library_index.py:24-38` (ajouter la source `mobile`)
- Create: `backend/app/services/sync_index.py`
- Modify: `backend/app/api/routes.py` (à la fin)
- Test: `backend/tests/test_sync_index.py`

**Coût :** moyen. Aucune migration : `LibraryAsset` porte déjà `source`, `kind`, `origin`, `job_id` (`storage.py:228-248`). Une clé de plus dans `SOURCES` — c'est un `dict` littéral, pas une table. Aucun patch de bundle. Le coût réel est le **calcul des empreintes** : le cache par `(chemin, mtime_ns)` de la tâche 8 est réutilisé.

- [ ] **Step 1 : Écrire le banc qui échoue**

Créer `backend/tests/test_sync_index.py` :

```python
# -*- coding: utf-8 -*-
"""P4 — le manifeste : index complet des vignettes, projets épinglés.

    python tests/test_sync_index.py             # depuis backend/
"""
import asyncio
import hashlib
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

IMAGES = pathlib.Path(_tmp, "images")


def _semer():
    from app.services.storage import init_db
    asyncio.run(init_db())
    (IMAGES / "gen_aa11bb22.png").write_bytes(b"IMAGE-A" * 100)
    (IMAGES / "news_cc33dd44.png").write_bytes(b"IMAGE-B" * 50)
    (IMAGES / "notice.txt").write_text("pas une image", encoding="utf-8")


def test_le_manifeste_ne_liste_que_des_images_et_dit_sa_version():
    from app.services import sync_index
    _semer()
    m = asyncio.run(sync_index.manifeste())
    assert m["protocole"] == 1
    noms = {e["nom"] for e in m["index"]}
    assert noms == {"gen_aa11bb22.png", "news_cc33dd44.png"}, noms


def test_chaque_entree_porte_taille_empreinte_et_provenance():
    from app.services import sync_index
    _semer()
    m = asyncio.run(sync_index.manifeste())
    e = [x for x in m["index"] if x["nom"] == "gen_aa11bb22.png"][0]
    assert e["taille"] == 700
    assert e["sha256"] == hashlib.sha256(b"IMAGE-A" * 100).hexdigest()
    assert e["source"] == "generation"
    assert e["origine"] in ("depot", "heuristique")


def test_le_manifeste_incremental_ne_rend_que_le_neuf():
    """`genere_a` est tronqué à la seconde : un fichier écrit à 10:00:00,4
    aurait un mtime SUPÉRIEUR à un `genere_a` valant 10:00:00. On encadre
    donc l'instant de référence par deux attentes — le banc est alors
    déterministe au lieu d'être vrai une seconde sur deux."""
    import time
    from datetime import datetime, timezone
    from app.services import sync_index
    _semer()
    time.sleep(1.1)
    t0 = (datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)
          .isoformat() + "Z")
    time.sleep(1.1)
    (IMAGES / "gen_ee55ff66.png").write_bytes(b"IMAGE-C" * 10)
    neuf = asyncio.run(sync_index.manifeste(depuis=t0))
    assert {e["nom"] for e in neuf["index"]} == {"gen_ee55ff66.png"}


def test_la_source_mobile_existe_dans_le_catalogue():
    from app.services import library_index
    assert "mobile" in library_index.SOURCES
    assert library_index.SOURCES["mobile"] == "Compagnon mobile"


def test_les_projets_epingles_sortent_en_entier():
    from app.services import sync_index
    _semer()
    asyncio.run(sync_index.epingler("campagne-septembre",
                                    ["gen_aa11bb22.png"]))
    m = asyncio.run(sync_index.manifeste())
    p = m["projets"][0]
    assert p["nom"] == "campagne-septembre"
    assert p["fichiers"] == ["gen_aa11bb22.png"]
    assert p["entier"] is True


def test_le_manifeste_dit_le_poids_total_a_transferer():
    """Comparé à la SOMME de l'index rendu, jamais à une constante : le
    test incrémental, exécuté avant, ajoute un fichier de plus."""
    from app.services import sync_index
    _semer()
    m = asyncio.run(sync_index.manifeste())
    assert m["poids_index"] == sum(e["taille"] for e in m["index"])
    noms = {e["nom"] for e in m["index"]}
    assert {"gen_aa11bb22.png", "news_cc33dd44.png"} <= noms
    assert m["poids_index"] >= 700 + 350


TESTS = [test_le_manifeste_ne_liste_que_des_images_et_dit_sa_version,
         test_chaque_entree_porte_taille_empreinte_et_provenance,
         test_le_manifeste_incremental_ne_rend_que_le_neuf,
         test_la_source_mobile_existe_dans_le_catalogue,
         test_les_projets_epingles_sortent_en_entier,
         test_le_manifeste_dit_le_poids_total_a_transferer]

if __name__ == "__main__":
    failed = []
    for t in TESTS:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed.append(t.__name__)
            print(f"FAIL {t.__name__}: {e!r}")
    print(f"\n{len(TESTS) - len(failed)}/{len(TESTS)} OK")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run : `cd backend && python tests/test_sync_index.py`
Attendu : six `FAIL`, `0/6 OK`.

- [ ] **Step 3 : Ajouter la source `mobile`**

Dans `backend/app/services/library_index.py`, dans le dict `SOURCES` (ligne 24), ajouter la ligne avant `"inconnu"` :

```python
    "mobile": "Compagnon mobile",
```

- [ ] **Step 4 : Écrire le service**

Créer `backend/app/services/sync_index.py` :

```python
# -*- coding: utf-8 -*-
"""P4 — le manifeste que le téléphone lit au retour sur le Wi-Fi.

R12 réponse 13 : « index complet (vignettes) + projets épinglés en
entier ». Le manifeste dit donc TOUT ce qui existe (nom, taille,
empreinte, provenance) et QUELS fichiers doivent descendre en entier.

Le protocole est versionné : un téléphone qui parle une autre version
refuse la synchronisation en le DISANT, il ne la tente pas.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.services import library_index as LI
from app.services.sync_lot import _sha256, _iso

PROTOCOLE = 1
_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def _fichier_projets() -> Path:
    return settings.outputs_path / "_sync" / "projets.json"


async def epingler(nom: str, fichiers: list[str]) -> dict:
    """Un projet épinglé descend EN ENTIER sur le téléphone.
    Stocké en JSON, pas en base : R9 P2 possède l'entité « projet » ;
    ce fichier est un pense-bête que R9 P2 remplacera."""
    p = _fichier_projets()
    p.parent.mkdir(parents=True, exist_ok=True)
    tout = {}
    if p.is_file():
        try:
            tout = json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            tout = {}
    tout[nom] = sorted({Path(str(f)).name for f in fichiers if f})
    p.write_text(json.dumps(tout, ensure_ascii=False, indent=1),
                 encoding="utf-8")
    return {"nom": nom, "fichiers": tout[nom]}


def _projets() -> list[dict]:
    p = _fichier_projets()
    if not p.is_file():
        return []
    try:
        tout = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []
    return [{"nom": k, "fichiers": v, "entier": True}
            for k, v in sorted(tout.items())]


async def manifeste(depuis: str | None = None) -> dict:
    """L'index complet, ou seulement ce qui a bougé depuis `depuis`
    (ISO renvoyé par un manifeste précédent)."""
    seuil = 0.0
    if depuis:
        try:
            # `genere_a` est en UTC ; `fromisoformat` sur une date NAÏVE
            # rend un datetime naïf que `.timestamp()` interprète comme
            # LOCAL. Sur une machine en UTC+2, le seuil reculerait de deux
            # heures et le mode incrémental renverrait tout.
            seuil = (datetime.fromisoformat(depuis.replace("Z", ""))
                     .replace(tzinfo=timezone.utc).timestamp())
        except ValueError:
            seuil = 0.0
    prov = await LI.carte()
    index, poids = [], 0
    dossier = settings.images_path
    if dossier.is_dir():
        for f in sorted(dossier.iterdir()):
            if not f.is_file() or f.suffix.lower() not in _EXTENSIONS:
                continue
            st = f.stat()
            if st.st_mtime <= seuil:
                continue
            connu = prov.get(f.name)
            index.append({
                "nom": f.name,
                "taille": st.st_size,
                "mtime": round(st.st_mtime, 3),
                "sha256": _sha256(f),
                "source": connu[0] if connu else LI.heuristique(f.name),
                "origine": connu[1] if connu else "heuristique",
            })
            poids += st.st_size
    return {"protocole": PROTOCOLE, "index": index, "projets": _projets(),
            "poids_index": poids, "genere_a": _iso(datetime.utcnow())}
```

- [ ] **Step 5 : Lancer, vérifier que ça passe**

Run : `cd backend && python tests/test_sync_index.py`
Attendu : six lignes `PASS`, puis `6/6 OK`.

- [ ] **Step 6 : Ajouter les routes**

À la fin de `backend/app/api/routes.py` :

```python
# ── P4 : le manifeste de synchronisation ────────────────────────────────────

@router.get("/sync/manifeste")
async def sync_manifeste(depuis: str | None = None):
    from app.services import sync_index as _si
    return await _si.manifeste(depuis=depuis)


@router.post("/sync/projet")
async def sync_projet(body: dict, request: Request):
    """Épingler un projet se fait DEPUIS LE PC : c'est lui qui décide de
    ce qui descend en entier."""
    _require_localhost(request)
    from app.services import sync_index as _si
    nom = str((body or {}).get("nom") or "").strip()
    if not nom:
        raise HTTPException(400, "nom de projet requis")
    return await _si.epingler(nom, (body or {}).get("fichiers") or [])
```

- [ ] **Step 7 : Commit**

```bash
git add backend/app/services/sync_index.py backend/app/services/library_index.py backend/app/api/routes.py backend/tests/test_sync_index.py
git commit -m 'sync : le manifeste, index complet et projets epingles en entier' -m 'Chaque entree porte taille, empreinte et provenance : le telephone sait ce
quil a deja et ce quil doit descendre. Le mode incremental ne rend que ce
qui a bouge depuis le manifeste precedent.

Les projets epingles vivent dans un JSON, pas en base : lentite projet
appartient a R9 P2, et ce fichier est le pense-bete quelle remplacera. La
source mobile entre au catalogue de provenance.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Tâche 13 : P4 — transfert repris et dépôt vérifié

**Files:**
- Create: `backend/app/services/sync_transfert.py`
- Modify: `backend/app/api/routes.py` (à la fin)
- Test: `backend/tests/test_sync_transfert.py`

**Coût :** moyen. Aucune migration, aucun patch de bundle. La **recette** du fichier déposé va dans un fichier voisin `<nom>.recette.json` — R9 P3 le lira pour remplir sa colonne de lignée ; ce plan n'ajoute **aucune colonne**.

- [ ] **Step 1 : Écrire le banc qui échoue**

Créer `backend/tests/test_sync_transfert.py` :

```python
# -*- coding: utf-8 -*-
"""P4 — le transfert qui reprend, le dépôt qui se vérifie.

    python tests/test_sync_transfert.py         # depuis backend/
"""
import asyncio
import hashlib
import json
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

IMAGES = pathlib.Path(_tmp, "images")
CONTENU = b"UNE IMAGE VENUE DU TELEPHONE" * 40
EMPREINTE = hashlib.sha256(CONTENU).hexdigest()


def _base():
    from app.services.storage import init_db
    asyncio.run(init_db())


def test_un_depot_correct_ecrit_le_fichier_et_sa_recette():
    from app.services import sync_transfert
    _base()
    recette = {"moteur": "fal/flux", "prompt": "un poulpe",
               "graine": 42, "cout_usd": 0.03,
               "parent": "gen_aa11bb22.png", "relation": "retouche"}
    r = asyncio.run(sync_transfert.deposer(
        "mob_1234abcd.png", CONTENU, EMPREINTE, recette, "iPhone de Oli"))
    assert r["ok"] is True
    f = IMAGES / "mob_1234abcd.png"
    assert f.read_bytes() == CONTENU
    lu = json.loads((IMAGES / "mob_1234abcd.png.recette.json")
                    .read_text(encoding="utf-8"))
    assert lu["moteur"] == "fal/flux"
    assert lu["parent"] == "gen_aa11bb22.png"
    assert lu["relation"] == "retouche"
    assert lu["appareil"] == "iPhone de Oli"


def test_une_empreinte_fausse_refuse_et_ne_laisse_rien():
    from app.services import sync_transfert
    _base()
    try:
        asyncio.run(sync_transfert.deposer(
            "mob_casse.png", CONTENU, "0" * 64, {}, "iPhone de Oli"))
    except ValueError as e:
        assert "sha256" in str(e)
    else:
        raise AssertionError("une empreinte fausse a été acceptée")
    assert not (IMAGES / "mob_casse.png").exists()
    assert list(IMAGES.glob("*.part")) == []


def test_le_depot_est_indexe_avec_la_source_mobile():
    """Miroir : on relit la LIGNE de library_assets."""
    from sqlalchemy import text
    from app.services import sync_transfert
    from app.services.storage import _engine
    _base()
    asyncio.run(sync_transfert.deposer(
        "mob_indexe.png", CONTENU, EMPREINTE, {}, "tablette"))

    async def lire():
        async with _engine.begin() as conn:
            r = await conn.execute(text(
                "SELECT source, origin FROM library_assets "
                "WHERE filename = 'mob_indexe.png'"))
            return r.fetchone()

    ligne = asyncio.run(lire())
    assert ligne is not None, "le dépôt n'a pas été indexé"
    assert ligne[0] == "mobile" and ligne[1] == "depot"


def test_un_nom_qui_sort_du_magasin_est_refuse():
    from app.services import sync_transfert
    _base()
    for mauvais in ("../evade.png", r"..\evade.png", "sous/dossier.png",
                    "C:/absolu.png", "", "."):
        try:
            asyncio.run(sync_transfert.deposer(
                mauvais, CONTENU, EMPREINTE, {}, "x"))
        except ValueError:
            continue
        raise AssertionError(f"nom accepté : {mauvais!r}")


def test_un_second_depot_du_meme_nom_ne_perd_pas_lancien():
    from app.services import sync_transfert
    _base()
    asyncio.run(sync_transfert.deposer(
        "mob_bis.png", CONTENU, EMPREINTE, {}, "x"))
    autre = b"AUTRE CONTENU"
    r = asyncio.run(sync_transfert.deposer(
        "mob_bis.png", autre, hashlib.sha256(autre).hexdigest(), {}, "x"))
    assert r["nom"] != "mob_bis.png", r
    assert (IMAGES / "mob_bis.png").read_bytes() == CONTENU
    assert (IMAGES / r["nom"]).read_bytes() == autre


TESTS = [test_un_depot_correct_ecrit_le_fichier_et_sa_recette,
         test_une_empreinte_fausse_refuse_et_ne_laisse_rien,
         test_le_depot_est_indexe_avec_la_source_mobile,
         test_un_nom_qui_sort_du_magasin_est_refuse,
         test_un_second_depot_du_meme_nom_ne_perd_pas_lancien]

if __name__ == "__main__":
    failed = []
    for t in TESTS:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed.append(t.__name__)
            print(f"FAIL {t.__name__}: {e!r}")
    print(f"\n{len(TESTS) - len(failed)}/{len(TESTS)} OK")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run : `cd backend && python tests/test_sync_transfert.py`
Attendu : cinq `FAIL ... ModuleNotFoundError`, `0/5 OK`.

- [ ] **Step 3 : Écrire le service**

Créer `backend/app/services/sync_transfert.py` :

```python
# -*- coding: utf-8 -*-
"""P4 — le fichier qui remonte du téléphone, vérifié avant d'exister.

TROIS RÈGLES, chacune contre une perte réelle :
1. On écrit dans `<nom>.part`, on vérifie le sha256, PUIS on renomme.
   Une coupure ne laisse jamais un demi-fichier dans la Bibliothèque.
2. Un nom qui contient un séparateur, un `..` ou une lettre de lecteur
   est refusé — même garde que `GenerateRequest` (test_security_guards).
3. Un nom déjà pris n'écrase RIEN : le dépôt reçoit un suffixe et le dit.

La RECETTE va dans `<nom>.recette.json`, à côté du fichier. La colonne de
lignée appartient à R9 P3 : quand elle existera, elle lira ce fichier.
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path

from loguru import logger

from app.config import settings
from app.services import library_index as LI


def _nom_sur(nom: str) -> str:
    brut = str(nom or "")
    if not brut or brut in (".", ".."):
        raise ValueError("nom de fichier vide")
    if "/" in brut or "\\" in brut or ":" in brut:
        raise ValueError(f"nom hors du magasin : {brut!r}")
    if Path(brut).name != brut:
        raise ValueError(f"nom hors du magasin : {brut!r}")
    return brut


def _libre(dossier: Path, nom: str) -> str:
    if not (dossier / nom).exists():
        return nom
    tige, suffixe = Path(nom).stem, Path(nom).suffix
    for n in range(2, 1000):
        cand = f"{tige}_{n}{suffixe}"
        if not (dossier / cand).exists():
            return cand
    raise ValueError(f"mille variantes de {nom!r} existent deja")


async def deposer(nom: str, contenu: bytes, sha256: str,
                  recette: dict, appareil: str) -> dict:
    """Écrit le fichier SI son empreinte correspond, l'indexe, pose sa
    recette. Rend le nom réellement écrit (il peut différer)."""
    nom = _nom_sur(nom)
    reel = hashlib.sha256(contenu).hexdigest()
    if reel != (sha256 or "").lower():
        raise ValueError(
            f"sha256 attendu {sha256!r}, calcule {reel!r} — depot refuse")
    dossier = settings.images_path
    dossier.mkdir(parents=True, exist_ok=True)
    final = _libre(dossier, nom)
    part = dossier / (final + ".part")
    try:
        part.write_bytes(contenu)
        if hashlib.sha256(part.read_bytes()).hexdigest() != reel:
            raise ValueError("le fichier ecrit ne correspond plus — disque ?")
        part.replace(dossier / final)
    finally:
        if part.exists():
            part.unlink(missing_ok=True)
    fiche = dict(recette or {})
    fiche["appareil"] = str(appareil or "telephone")[:60]
    fiche["depose_a"] = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    fiche["sha256"] = reel
    (dossier / (final + ".recette.json")).write_text(
        json.dumps(fiche, ensure_ascii=False, indent=1), encoding="utf-8")
    await LI.noter([final], "mobile", kind="image")
    logger.info(f"sync: depot {final} depuis {fiche['appareil']}")
    return {"ok": True, "nom": final, "sha256": reel,
            "renomme": final != nom}
```

- [ ] **Step 4 : Lancer, vérifier que ça passe**

Run : `cd backend && python tests/test_sync_transfert.py`
Attendu : cinq lignes `PASS`, puis `5/5 OK`.

- [ ] **Step 5 : Ajouter les routes de transfert**

À la fin de `backend/app/api/routes.py` :

```python
# ── P4 : le transfert dans les deux sens ────────────────────────────────────

@router.get("/sync/fichier/{nom}")
async def sync_fichier(nom: str):
    """Un fichier du magasin, servi en Range (FileResponse le gère) pour
    que le téléphone reprenne après une coupure de Wi-Fi."""
    from fastapi.responses import FileResponse
    from app.services.sync_transfert import _nom_sur
    try:
        sur = _nom_sur(nom)
    except ValueError as e:
        raise HTTPException(400, str(e))
    p = settings.images_path / sur
    if not p.is_file():
        raise HTTPException(404, "fichier absent du magasin")
    return FileResponse(str(p), filename=sur)


@router.post("/sync/depot")
async def sync_depot(request: Request,
                     file: UploadFile = File(...),
                     sha256: str = Form(...),
                     recette: str = Form("{}"),
                     appareil: str = Form("telephone")):
    """Le téléphone rend un rendu ou une génération, avec sa recette."""
    from app.services import sync_transfert
    try:
        fiche = json.loads(recette or "{}")
    except ValueError:
        raise HTTPException(400, "recette illisible (JSON attendu)")
    contenu = await file.read()
    try:
        return await sync_transfert.deposer(
            Path(file.filename or "mobile.png").name, contenu, sha256,
            fiche if isinstance(fiche, dict) else {}, appareil)
    except ValueError as e:
        raise HTTPException(400, str(e))
```

`UploadFile`, `File` et `Form` sont **déjà** importés en tête de `routes.py` (ligne 13 : `from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File, Form, Request, Response`) — mesuré le 03/09. Aucun import à ajouter.

Run : `cd backend && python -c "import sys; sys.path.insert(0,'.'); import app.api.routes; print('IMPORT OK')"`
Attendu : `IMPORT OK`.

- [ ] **Step 6 : Commit**

```bash
git add backend/app/services/sync_transfert.py backend/app/api/routes.py backend/tests/test_sync_transfert.py
git commit -m 'sync : le depot verifie avant dexister, le transfert qui reprend' -m 'On ecrit un .part, on verifie le sha256, PUIS on renomme : une coupure ne
laisse jamais un demi-fichier dans la Bibliotheque, et le banc verifie quil
ne reste aucun .part apres un refus.

Un nom deja pris nest jamais ecrase : le depot recoit un suffixe et le DIT.
La recette part dans un fichier voisin — la colonne de lignee appartient a
R9 P3, qui le lira quand elle existera.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Tâche 14 : P4 — verrous de chapitre et journal des conflits

**Files:**
- Modify: `backend/app/services/storage.py` (deux classes neuves après `Device`)
- Create: `backend/app/services/sync_verrou.py`
- Modify: `backend/app/api/routes.py:5751-5752` (garde en tête de `update_chapter`)
- Test: `backend/tests/test_sync_verrou.py`

**Coût :** faible. **Tables neuves** → `create_all` suffit. La seule modification d'une route existante de tout le plan : sept lignes en tête de `update_chapter`. Aucun patch de bundle — l'écran Chapitres affichera le message 423 tel quel.

- [ ] **Step 1 : Écrire le banc qui échoue**

Créer `backend/tests/test_sync_verrou.py` :

```python
# -*- coding: utf-8 -*-
"""P4 — le chapitre emporté est en lecture seule sur le PC (R12 réponse 14).

    python tests/test_sync_verrou.py            # depuis backend/
"""
import asyncio
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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.storage import init_db
    asyncio.run(init_db())
    return TestClient(app)


def _chapitre(c):
    r = c.post("/api/chapters", json={"title": "Chapitre un",
                                      "script_text": "Le texte du PC."})
    assert r.status_code == 200, r.text[:200]
    return r.json()["id"]


def test_sans_verrou_le_pc_ecrit_comme_avant():
    c = _client()
    i = _chapitre(c)
    r = c.put(f"/api/chapters/{i}", json={"script_text": "Texte modifie."})
    assert r.status_code == 200, (r.status_code, r.text[:200])


def test_un_chapitre_emporte_refuse_lecriture_du_pc_en_le_disant():
    from app.services import sync_verrou
    c = _client()
    i = _chapitre(c)
    asyncio.run(sync_verrou.prendre(i, "dev-1", "iPhone de Oli"))
    r = c.put(f"/api/chapters/{i}", json={"script_text": "Ecrase !"})
    assert r.status_code == 423, (r.status_code, r.text[:200])
    assert "iPhone de Oli" in r.text
    lu = c.get(f"/api/chapters/{i}").json()
    assert lu["script_text"] == "Le texte du PC."


def test_le_verrou_libere_rend_lecriture():
    from app.services import sync_verrou
    c = _client()
    i = _chapitre(c)
    asyncio.run(sync_verrou.prendre(i, "dev-1", "iPhone de Oli"))
    asyncio.run(sync_verrou.liberer(i, "dev-1"))
    r = c.put(f"/api/chapters/{i}", json={"script_text": "De nouveau."})
    assert r.status_code == 200, (r.status_code, r.text[:200])


def test_un_autre_appareil_ne_peut_pas_liberer():
    from app.services import sync_verrou
    c = _client()
    i = _chapitre(c)
    asyncio.run(sync_verrou.prendre(i, "dev-1", "iPhone de Oli"))
    assert asyncio.run(sync_verrou.liberer(i, "dev-2")) is False
    assert c.put(f"/api/chapters/{i}",
                 json={"script_text": "x"}).status_code == 423


def test_deux_appareils_ne_prennent_pas_le_meme_chapitre():
    from app.services import sync_verrou
    c = _client()
    i = _chapitre(c)
    assert asyncio.run(sync_verrou.prendre(i, "dev-1", "iPhone"))["pris"]
    deux = asyncio.run(sync_verrou.prendre(i, "dev-2", "tablette"))
    assert deux["pris"] is False
    assert deux["par"] == "iPhone"


def test_le_journal_garde_la_trace_des_conflits():
    from app.services import sync_verrou
    c = _client()
    i = _chapitre(c)
    asyncio.run(sync_verrou.prendre(i, "dev-1", "iPhone de Oli"))
    c.put(f"/api/chapters/{i}", json={"script_text": "tentative"})
    journal = asyncio.run(sync_verrou.journal())
    assert len(journal) >= 1
    assert journal[0]["chapitre"] == i
    assert journal[0]["par"] == "iPhone de Oli"
    assert journal[0]["quoi"] == "ecriture PC refusee"


TESTS = [test_sans_verrou_le_pc_ecrit_comme_avant,
         test_un_chapitre_emporte_refuse_lecriture_du_pc_en_le_disant,
         test_le_verrou_libere_rend_lecriture,
         test_un_autre_appareil_ne_peut_pas_liberer,
         test_deux_appareils_ne_prennent_pas_le_meme_chapitre,
         test_le_journal_garde_la_trace_des_conflits]

if __name__ == "__main__":
    failed = []
    for t in TESTS:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed.append(t.__name__)
            print(f"FAIL {t.__name__}: {e!r}")
    print(f"\n{len(TESTS) - len(failed)}/{len(TESTS)} OK")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run : `cd backend && python tests/test_sync_verrou.py`
Attendu : `PASS test_sans_verrou_le_pc_ecrit_comme_avant`, cinq `FAIL`, `1/6 OK`.

- [ ] **Step 3 : Ajouter les modèles**

Dans `backend/app/services/storage.py`, après la classe `Device` (tâche 2) :

```python
class ChapterLock(Base):
    """P4 (03/09) — un chapitre « emporté » par un appareil. Tant que la
    ligne existe, `PUT /chapters/{id}` répond 423 sur le PC : R12 réponse
    14 choisit le VERROU, pas la fusion (« plus simple et sans surprise »).
    Table neuve : create_all suffit."""
    __tablename__ = "chapter_locks"

    chapter_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(36))
    device_nom: Mapped[str] = mapped_column(String(60), default="")
    pris_le: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SyncConflit(Base):
    """P4 — le journal des conflits. Rien n'est avalé en silence : une
    écriture refusée laisse une ligne que la synchronisation rapporte."""
    __tablename__ = "sync_conflits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    quoi: Mapped[str] = mapped_column(String(60), default="")
    chapitre: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    par: Mapped[str] = mapped_column(String(60), default="")
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quand: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 4 : Écrire le service**

Créer `backend/app/services/sync_verrou.py` :

```python
# -*- coding: utf-8 -*-
"""P4 — le verrou de chapitre, et le journal qui n'avale rien.

R12 réponse 14, mot pour mot : « verrou — un chapitre emporté est en
lecture seule sur le PC, libéré au retour ». Pas de fusion (E4).
Le versionnage du texte appartient à R3 P2 ; ici, seul le verrou.
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import delete as _delete, select as _select


async def prendre(chapter_id: str, device_id: str, device_nom: str) -> dict:
    from app.services.storage import ChapterLock, async_session_factory
    async with async_session_factory() as session:
        deja = await session.get(ChapterLock, chapter_id)
        if deja is not None:
            if deja.device_id == device_id:
                return {"pris": True, "par": deja.device_nom, "deja": True}
            return {"pris": False, "par": deja.device_nom,
                    "depuis": deja.pris_le.isoformat()}
        session.add(ChapterLock(chapter_id=chapter_id, device_id=device_id,
                                device_nom=(device_nom or "")[:60]))
        await session.commit()
    return {"pris": True, "par": device_nom, "deja": False}


async def liberer(chapter_id: str, device_id: str) -> bool:
    from app.services.storage import ChapterLock, async_session_factory
    async with async_session_factory() as session:
        v = await session.get(ChapterLock, chapter_id)
        if v is None or v.device_id != device_id:
            return False
        await session.execute(
            _delete(ChapterLock).where(ChapterLock.chapter_id == chapter_id))
        await session.commit()
    return True


async def qui(chapter_id: str) -> dict | None:
    from app.services.storage import ChapterLock, async_session_factory
    async with async_session_factory() as session:
        v = await session.get(ChapterLock, chapter_id)
        if v is None:
            return None
        return {"device_id": v.device_id, "nom": v.device_nom,
                "pris_le": v.pris_le.isoformat()}


async def noter_conflit(quoi: str, chapitre: str | None,
                        par: str, detail: str = "") -> None:
    from app.services.storage import SyncConflit, async_session_factory
    async with async_session_factory() as session:
        session.add(SyncConflit(id=str(uuid4()), quoi=quoi[:60],
                                chapitre=chapitre, par=par[:60],
                                detail=detail[:400] or None,
                                quand=datetime.utcnow()))
        await session.commit()


async def journal(limite: int = 100) -> list[dict]:
    from app.services.storage import SyncConflit, async_session_factory
    async with async_session_factory() as session:
        res = await session.execute(
            _select(SyncConflit).order_by(SyncConflit.quand.desc())
            .limit(limite))
        return [{"id": c.id, "quoi": c.quoi, "chapitre": c.chapitre,
                 "par": c.par, "detail": c.detail,
                 "quand": c.quand.isoformat()}
                for c in res.scalars().all()]
```

- [ ] **Step 5 : Garder `PUT /chapters/{chapter_id}`**

Dans `backend/app/api/routes.py`, insérer **juste après** la ligne 5752 (`async def update_chapter(chapter_id: str, body: dict):`) et **avant** `from app.services.storage import Chapter, async_session_factory` :

```python
    # P4 — un chapitre EMPORTÉ par un appareil est en lecture seule ici
    # (R12 réponse 14 : verrou, pas fusion). Le refus NOMME l'appareil.
    from app.services import sync_verrou as _sv
    _verrou = await _sv.qui(chapter_id)
    if _verrou:
        await _sv.noter_conflit("ecriture PC refusee", chapter_id,
                                _verrou["nom"], "PUT /chapters")
        raise HTTPException(
            423, f"chapitre emporte par {_verrou['nom']} depuis "
                 f"{_verrou['pris_le']} — liberez-le depuis l appareil")
```

- [ ] **Step 6 : Lancer, vérifier que ça passe**

Run : `cd backend && python tests/test_sync_verrou.py`
Attendu : six lignes `PASS`, puis `6/6 OK`.

- [ ] **Step 7 : Ajouter les routes**

À la fin de `backend/app/api/routes.py` :

```python
# ── P4 : verrous et journal ─────────────────────────────────────────────────

@router.post("/sync/verrou/{chapter_id}")
async def sync_verrou_prendre(chapter_id: str, body: dict):
    from app.services import sync_verrou as _sv
    r = await _sv.prendre(chapter_id,
                          str((body or {}).get("device_id") or ""),
                          str((body or {}).get("nom") or "appareil"))
    if not r["pris"]:
        raise HTTPException(409, f"deja emporte par {r['par']}")
    return r


@router.delete("/sync/verrou/{chapter_id}")
async def sync_verrou_liberer(chapter_id: str, device_id: str = ""):
    from app.services import sync_verrou as _sv
    if not await _sv.liberer(chapter_id, device_id):
        raise HTTPException(409, "verrou absent ou tenu par un autre appareil")
    return {"libere": chapter_id}


@router.get("/sync/conflits")
async def sync_conflits(limite: int = 100):
    from app.services import sync_verrou as _sv
    return {"conflits": await _sv.journal(limite=limite)}
```

- [ ] **Step 8 : Commit**

```bash
git add backend/app/services/storage.py backend/app/services/sync_verrou.py backend/app/api/routes.py backend/tests/test_sync_verrou.py
git commit -m 'sync : le chapitre emporte est en lecture seule sur le PC, et le dit' -m 'R12 reponse 14 choisit le verrou, pas la fusion. PUT /chapters repond 423
en NOMMANT lappareil et lheure, le texte du PC reste intact, et le refus
laisse une ligne au journal des conflits — rien nest avale.

Deux tables neuves, donc create_all suffit. Le versionnage du texte reste a
R3 P2 : ce plan ne pose que le verrou.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Tâche 15 : P4 — découverte mDNS, répondeur stdlib (PC)

**Files:**
- Create: `backend/app/services/mdns.py`
- Modify: `backend/app/main.py:160-167` (démarrage et arrêt dans `lifespan`)
- Test: `backend/tests/test_mdns.py`

**Coût :** moyen, entièrement dû à une contrainte mesurée : **`zeroconf` est absent de `backend/requirements.txt`** et le runtime embarqué est stdlib pur. Le répondeur est écrit en `socket`. Il ne s'allume **que** si `HOST != 127.0.0.1` : une machine qui n'a pas ouvert le LAN n'annonce rien.

- [ ] **Step 1 : Vérifier la contrainte iOS**

```
WebFetch url="https://developer.apple.com/documentation/technotes/tn3179-understanding-local-network-privacy" prompt="Which Info.plist keys are required to browse Bonjour services on iOS? When is the com.apple.developer.networking.multicast entitlement required, and how is it obtained?"
```

Reporter la réponse dans `deepotus-mobile/docs/arriere-plan.md`, section « Réseau local ». Si l'entitlement s'avère nécessaire **même** pour Bonjour par l'API système, le repli de la tâche 16 (adresse mémorisée puis saisie) devient le chemin principal, et il faut l'écrire dans `DECISIONS.md`.

- [ ] **Step 2 : Écrire le banc qui échoue**

Créer `backend/tests/test_mdns.py` :

```python
# -*- coding: utf-8 -*-
"""P4 — le répondeur mDNS stdlib : on lit les OCTETS rendus.

`zeroconf` est absent du runtime embarqué (mesuré dans requirements.txt) :
la trame est construite à la main, donc elle est mesurée à la main.

    python tests/test_mdns.py                   # depuis backend/
"""
import os
import pathlib
import struct
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

SERVICE = "_deepotus._tcp.local."


def _question(nom: str, qtype: int = 12) -> bytes:
    """Une requête DNS minimale, construite indépendamment du module."""
    corps = b""
    for etiquette in nom.rstrip(".").split("."):
        corps += bytes([len(etiquette)]) + etiquette.encode("ascii")
    corps += b"\x00" + struct.pack(">HH", qtype, 1)
    return struct.pack(">HHHHHH", 0, 0, 1, 0, 0, 0) + corps


def _noms(paquet: bytes) -> list[str]:
    """Extrait les étiquettes lisibles, pointeurs de compression ignorés."""
    out, i = [], 0
    while i < len(paquet):
        n = paquet[i]
        if 32 < n < 64 and i + 1 + n <= len(paquet):
            morceau = paquet[i + 1:i + 1 + n]
            try:
                out.append(morceau.decode("ascii"))
            except UnicodeDecodeError:
                pass
            i += 1 + n
        else:
            i += 1
    return out


def test_une_question_sur_un_autre_service_reste_sans_reponse():
    from app.services import mdns
    r = mdns.repondre(_question("_printer._tcp.local."), "192.168.1.20", 8765)
    assert r is None


def test_la_question_ptr_recoit_ptr_srv_txt_et_a():
    from app.services import mdns
    r = mdns.repondre(_question(SERVICE), "192.168.1.20", 8765)
    assert r is not None
    entete = struct.unpack(">HHHHHH", r[:12])
    assert entete[0] == 0                       # id nul, réponse mDNS
    assert entete[1] & 0x8400 == 0x8400         # réponse + autoritaire
    assert entete[3] == 4, entete               # PTR + SRV + TXT + A
    for attendu in ("_deepotus", "_tcp", "local", "deepotus"):
        assert attendu in _noms(r), (attendu, _noms(r))


def test_ladresse_annoncee_est_celle_quon_lui_donne():
    from app.services import mdns
    r = mdns.repondre(_question(SERVICE), "10.0.0.7", 8765)
    assert bytes([10, 0, 0, 7]) in r


def test_le_port_annonce_est_celui_quon_lui_donne():
    from app.services import mdns
    r = mdns.repondre(_question(SERVICE), "192.168.1.20", 9999)
    assert struct.pack(">H", 9999) in r


def test_le_txt_dit_la_version_du_protocole():
    from app.services import mdns
    r = mdns.repondre(_question(SERVICE), "192.168.1.20", 8765)
    assert b"protocole=1" in r


def test_un_paquet_tronque_ne_leve_pas():
    from app.services import mdns
    for mauvais in (b"", b"\x00", b"\x00" * 11, _question(SERVICE)[:14]):
        assert mdns.repondre(mauvais, "192.168.1.20", 8765) is None


TESTS = [test_une_question_sur_un_autre_service_reste_sans_reponse,
         test_la_question_ptr_recoit_ptr_srv_txt_et_a,
         test_ladresse_annoncee_est_celle_quon_lui_donne,
         test_le_port_annonce_est_celui_quon_lui_donne,
         test_le_txt_dit_la_version_du_protocole,
         test_un_paquet_tronque_ne_leve_pas]

if __name__ == "__main__":
    failed = []
    for t in TESTS:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed.append(t.__name__)
            print(f"FAIL {t.__name__}: {e!r}")
    print(f"\n{len(TESTS) - len(failed)}/{len(TESTS)} OK")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 3 : Lancer, vérifier l'échec**

Run : `cd backend && python tests/test_mdns.py`
Attendu : six `FAIL ... ModuleNotFoundError("No module named 'app.services.mdns'")`, `0/6 OK`.

- [ ] **Step 4 : Écrire le répondeur**

Créer `backend/app/services/mdns.py` :

```python
# -*- coding: utf-8 -*-
"""P4 — répondeur mDNS minimal, stdlib pur.

POURQUOI écrit à la main : `zeroconf` est absent de requirements.txt et
le runtime livré est stdlib + Pillow (mesuré 03/09).

CE QU'IL FAIT, ET RIEN DE PLUS : il écoute 224.0.0.251:5353, et à une
question PTR sur `_deepotus._tcp.local.` il répond PTR + SRV + TXT + A.
Il n'implémente ni la compression de noms (les paquets restent petits),
ni les annonces spontanées, ni le retrait — un service qui disparaît
cesse simplement de répondre.

IL NE S'ALLUME PAS quand HOST vaut 127.0.0.1 : une machine qui n'a pas
ouvert le LAN n'annonce rien du tout.
"""
import asyncio
import socket
import struct

from loguru import logger

GROUPE = "224.0.0.251"
PORT_MDNS = 5353
SERVICE = "_deepotus._tcp.local."
INSTANCE = "deepotus._deepotus._tcp.local."
HOTE = "deepotus.local."
TTL = 120


def _encoder(nom: str) -> bytes:
    out = b""
    for etiquette in nom.rstrip(".").split("."):
        b = etiquette.encode("ascii")
        out += bytes([len(b)]) + b
    return out + b"\x00"


def _lire_nom(paquet: bytes, i: int) -> tuple[str, int]:
    parties = []
    while i < len(paquet):
        n = paquet[i]
        if n == 0:
            return ".".join(parties) + ".", i + 1
        if n & 0xC0:                     # pointeur de compression : refusé
            raise ValueError("compression non geree")
        i += 1
        parties.append(paquet[i:i + n].decode("ascii", "replace"))
        i += n
    raise ValueError("nom tronque")


def _enregistrement(nom: str, rtype: int, donnees: bytes) -> bytes:
    return (_encoder(nom) + struct.pack(">HHIH", rtype, 1, TTL, len(donnees))
            + donnees)


def repondre(paquet: bytes, adresse: str, port: int) -> bytes | None:
    """La réponse aux octets reçus, ou None si la question ne nous vise
    pas ou si le paquet est illisible. Ne lève jamais."""
    try:
        if len(paquet) < 12:
            return None
        _, drapeaux, qd, _, _, _ = struct.unpack(">HHHHHH", paquet[:12])
        if drapeaux & 0x8000 or qd < 1:          # une réponse, pas pour nous
            return None
        i = 12
        vise = False
        for _ in range(qd):
            nom, i = _lire_nom(paquet, i)
            if i + 4 > len(paquet):
                return None
            qtype, _qclass = struct.unpack(">HH", paquet[i:i + 4])
            i += 4
            if nom.lower() == SERVICE and qtype in (12, 255):
                vise = True
        if not vise:
            return None
    except (ValueError, struct.error):
        return None

    txt = b""
    for entree in ("protocole=1", f"port={port}"):
        b = entree.encode("ascii")
        txt += bytes([len(b)]) + b
    corps = (
        _enregistrement(SERVICE, 12, _encoder(INSTANCE))                # PTR
        + _enregistrement(INSTANCE, 33,                                 # SRV
                          struct.pack(">HHH", 0, 0, port) + _encoder(HOTE))
        + _enregistrement(INSTANCE, 16, txt)                            # TXT
        + _enregistrement(HOTE, 1, socket.inet_aton(adresse))           # A
    )
    return struct.pack(">HHHHHH", 0, 0x8400, 0, 4, 0, 0) + corps


class Repondeur(asyncio.DatagramProtocol):
    def __init__(self, adresse: str, port: int):
        self.adresse = adresse
        self.port = port
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        reponse = repondre(data, self.adresse, self.port)
        if reponse and self.transport is not None:
            try:
                self.transport.sendto(reponse, (GROUPE, PORT_MDNS))
            except OSError as e:
                logger.warning(f"mdns: envoi impossible: {e}")


async def demarrer(adresse: str, port: int):
    """Rend le transport, ou None si le LAN n'est pas ouvert / si le
    socket est refusé (un autre répondeur tient déjà le port)."""
    if adresse in ("127.0.0.1", "localhost", "::1", ""):
        logger.info("mdns: HOST est loopback, aucune annonce")
        return None
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("", PORT_MDNS))
        s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                     socket.inet_aton(GROUPE) + socket.inet_aton(adresse))
    except OSError as e:
        s.close()
        logger.warning(f"mdns: repondeur non demarre ({e})")
        return None
    boucle = asyncio.get_running_loop()
    transport, _ = await boucle.create_datagram_endpoint(
        lambda: Repondeur(adresse, port), sock=s)
    logger.info(f"mdns: {SERVICE} annonce sur {adresse}:{port}")
    return transport
```

- [ ] **Step 5 : Lancer, vérifier que ça passe**

Run : `cd backend && python tests/test_mdns.py`
Attendu : six lignes `PASS`, puis `6/6 OK`.

- [ ] **Step 6 : Démarrer le répondeur avec l'application**

Dans `backend/app/main.py`, dans `lifespan`, juste avant le `yield` :

```python
    # P4 — annonce mDNS, seulement si le LAN est ouvert (mdns.demarrer le
    # vérifie lui-même et rend None sinon).
    _mdns_transport = None
    try:
        from app.api.routes import _adresse_lan
        from app.services import mdns as _mdns
        _mdns_transport = await _mdns.demarrer(
            _adresse_lan() if settings.HOST != "127.0.0.1" else "127.0.0.1",
            settings.PORT)
    except Exception as e:  # noqa: BLE001 — l'annonce est un à-côté
        logger.warning(f"mdns: demarrage ignore: {e}")
```

et, dans le bloc d'arrêt (là où `warm_task.cancel()` est appelé, `main.py:165-167`), juste après :

```python
        if _mdns_transport is not None:
            _mdns_transport.close()
```

- [ ] **Step 7 : Vérifier que l'application démarre encore**

Run : `cd backend && python -c "import sys; sys.path.insert(0,'.'); from app.main import app; print('APP OK', len(app.routes))"`
Attendu : `APP OK` suivi d'un nombre de routes supérieur à 300.

- [ ] **Step 8 : Commit**

```bash
git add backend/app/services/mdns.py backend/app/main.py backend/tests/test_mdns.py
git commit -m 'sync : un repondeur mDNS stdlib, allume seulement si le LAN est ouvert' -m 'zeroconf est absent du runtime embarque (mesure) : la trame DNS est
construite a la main, donc le banc la LIT octet par octet — quatre
enregistrements, ladresse annoncee, le port annonce, le TXT qui dit la
version du protocole, et le paquet tronque qui ne leve pas.

Le repondeur ne sallume pas quand HOST vaut 127.0.0.1 : une machine qui na
pas ouvert le LAN nannonce rien.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Tâche 16 : P4 — le client de synchronisation (mobile)

**Files:**
- Create: `deepotus-mobile/src/lib/sync.ts`
- Create: `deepotus-mobile/src/lib/decouverte.ts`
- Test: `deepotus-mobile/src/lib/__tests__/sync.test.ts`

**Coût :** moyen. Le repli « adresse mémorisée puis saisie » est écrit **dès maintenant**, pas plus tard : c'est ce qui rend la découverte optionnelle si l'entitlement iOS de la tâche 15 s'avère nécessaire.

- [ ] **Step 1 : Écrire les tests qui échouent**

`deepotus-mobile/src/lib/__tests__/sync.test.ts` :

```typescript
import { aDescendre, plan, verifierProtocole } from "../sync";

const M = {
  protocole: 1,
  poids_index: 1050,
  genere_a: "2026-09-04T10:00:00Z",
  index: [
    { nom: "a.png", taille: 700, sha256: "aaa", source: "generation", origine: "depot" },
    { nom: "b.png", taille: 350, sha256: "bbb", source: "news", origine: "depot" },
  ],
  projets: [{ nom: "campagne", fichiers: ["b.png"], entier: true }],
};

test("un protocole different refuse la synchro, en le disant", () => {
  const r = verifierProtocole({ ...M, protocole: 2 } as any);
  expect(r.ok).toBe(false);
  expect((r as any).raison).toContain("protocole 2");
  expect(verifierProtocole(M as any)).toEqual({ ok: true });
});

test("seul le neuf ou le change descend", () => {
  const local = { "a.png": "aaa", "b.png": "AUTRE" };
  expect(aDescendre(M as any, local).map((e) => e.nom)).toEqual(["b.png"]);
});

test("le plan descend les projets epingles EN ENTIER, les autres en vignette",
  () => {
    const p = plan(M as any, {});
    expect(p.entier).toEqual(["b.png"]);
    expect(p.vignettes).toEqual(["a.png"]);
    expect(p.octets).toBe(1050);
  });

test("un fichier deja bon ne repart pas", () => {
  const p = plan(M as any, { "a.png": "aaa", "b.png": "bbb" });
  expect(p.entier).toEqual([]);
  expect(p.vignettes).toEqual([]);
  expect(p.octets).toBe(0);
});
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run : `cd /c/Users/olivi/deepotus-mobile && npm test`
Attendu : `Cannot find module '../sync'`, quatre tests en échec.

- [ ] **Step 3 : Écrire `sync.ts`**

```typescript
import { PROTOCOLE } from "./version";

export type Entree = {
  nom: string; taille: number; sha256: string;
  source: string; origine: string;
};
export type Projet = { nom: string; fichiers: string[]; entier: boolean };
export type Manifeste = {
  protocole: number; index: Entree[]; projets: Projet[];
  poids_index: number; genere_a: string;
};

export function verifierProtocole(
  m: Manifeste,
): { ok: true } | { ok: false; raison: string } {
  if (m.protocole !== PROTOCOLE) {
    return {
      ok: false,
      raison: `le PC parle le protocole ${m.protocole}, le telephone le ${PROTOCOLE} — mettez a jour`,
    };
  }
  return { ok: true };
}

/** Ce que le téléphone n'a pas, ou pas dans la bonne version. La
 *  comparaison porte sur le sha256, jamais sur la date : deux horloges ne
 *  sont pas comparables et un fichier recopié change de mtime. */
export function aDescendre(m: Manifeste, local: Record<string, string>): Entree[] {
  return m.index.filter((e) => local[e.nom] !== e.sha256);
}

/** Le plan de la session : ce qui descend en entier (projets épinglés) et
 *  ce qui ne descend qu'en vignette. R12 réponse 13. */
export function plan(m: Manifeste, local: Record<string, string>) {
  const epingles = new Set(
    m.projets.filter((p) => p.entier).flatMap((p) => p.fichiers),
  );
  const manquants = aDescendre(m, local);
  return {
    entier: manquants.filter((e) => epingles.has(e.nom)).map((e) => e.nom),
    vignettes: manquants.filter((e) => !epingles.has(e.nom)).map((e) => e.nom),
    octets: manquants.reduce((s, e) => s + e.taille, 0),
  };
}
```

- [ ] **Step 4 : Écrire `decouverte.ts`**

```typescript
import * as SecureStore from "expo-secure-store";

const CLE_DERNIER = "dz.sync.dernier_hote";

export type Trouvaille = {
  hote: string; port: number; comment: "mdns" | "memoire" | "saisie";
};

/** Découverte, avec REPLI ÉCRIT D'AVANCE. Si Bonjour est indisponible —
 *  entitlement iOS refusé, réseau qui filtre le multicast, hôtel — on
 *  reprend la dernière adresse connue, puis on demande à l'utilisateur.
 *  Le compagnon ne reste jamais bloqué sur une découverte qui ne vient pas. */
export async function trouverLePC(
  parMdns: () => Promise<Trouvaille | null>,
  demanderALUtilisateur: () => Promise<{ hote: string; port: number } | null>,
): Promise<Trouvaille | null> {
  try {
    const t = await parMdns();
    if (t) {
      await SecureStore.setItemAsync(CLE_DERNIER, `${t.hote}:${t.port}`);
      return t;
    }
  } catch {
    /* le repli suit */
  }
  const memoire = await SecureStore.getItemAsync(CLE_DERNIER);
  if (memoire) {
    const [hote, port] = memoire.split(":");
    return { hote, port: Number(port), comment: "memoire" };
  }
  const saisi = await demanderALUtilisateur();
  if (!saisi) return null;
  await SecureStore.setItemAsync(CLE_DERNIER, `${saisi.hote}:${saisi.port}`);
  return { ...saisi, comment: "saisie" };
}
```

- [ ] **Step 5 : Lancer, vérifier que tout passe**

Run : `cd /c/Users/olivi/deepotus-mobile && npm test`
Attendu : `Tests: 19 passed, 19 total`.

- [ ] **Step 6 : Commit**

```bash
cd /c/Users/olivi/deepotus-mobile
git add -A
git commit -m 'sync : le plan de session cote telephone, et le repli ecrit davance' -m 'La comparaison porte sur le sha256, jamais sur la date : deux horloges ne
sont pas comparables et une recopie change le mtime. Les projets epingles
descendent en entier, le reste en vignette — R12 reponse 13.

La decouverte a son repli DES MAINTENANT : mDNS, sinon la derniere adresse
connue, sinon la saisie. Le compagnon ne reste jamais bloque sur une
decouverte qui ne vient pas — un hotel, un reseau qui filtre le multicast,
ou un entitlement iOS refuse.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Tâche 17 : P5 — les quatre notifications, et les événements qui les nourrissent

**Files:**
- Create: `backend/app/services/sync_evenements.py`
- Modify: `backend/app/api/routes.py` (à la fin)
- Create: `deepotus-mobile/src/lib/notifications.ts`
- Test: `backend/tests/test_sync_evenements.py`, `deepotus-mobile/src/lib/__tests__/notifications.test.ts`

**Coût :** faible côté PC (une lecture, aucune écriture, aucune table), moyen côté mobile. Les quatre familles de R12 réponse 9 : **rendu terminé/échoué**, **post à publier/publié/échoué**, **plafond approché/dépassé**, **synchronisation terminée/en conflit**.

- [ ] **Step 1 : Écrire le banc PC qui échoue**

Créer `backend/tests/test_sync_evenements.py` :

```python
# -*- coding: utf-8 -*-
"""P5 — les événements que le téléphone transforme en notifications.

    python tests/test_sync_evenements.py        # depuis backend/
"""
import asyncio
import os
import pathlib
import sys
import tempfile
from datetime import datetime, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _semer():
    """IDEMPOTENTE : plusieurs tests du MÊME processus l'appellent, et
    réinsérer les mêmes clés primaires casserait sur la contrainte UNIQUE
    dès le deuxième appel. On vide d'abord."""
    from sqlalchemy import delete as _del
    from app.services.storage import (JobRecord, ScheduledPost, init_db,
                                      async_session_factory)
    asyncio.run(init_db())

    async def vider():
        async with async_session_factory() as s:
            await s.execute(_del(ScheduledPost))
            await s.execute(_del(JobRecord))
            await s.commit()
    asyncio.run(vider())

    async def poser():
        async with async_session_factory() as s:
            s.add(JobRecord(id="j-ok", status="completed",
                            image_filename="a.png", title="Le poulpe",
                            completed_at=datetime.utcnow()))
            s.add(JobRecord(id="j-ko", status="failed",
                            image_filename="b.png", title="Le rate",
                            error="fal: 402 insufficient credits",
                            completed_at=datetime.utcnow()))
            s.add(JobRecord(id="j-cours", status="running",
                            image_filename="c.png"))
            s.add(ScheduledPost(id="p-du", title="Post du",
                                channels="x", status="ready",
                                run_at=datetime.utcnow() - timedelta(hours=1)))
            await s.commit()
    asyncio.run(poser())


def test_les_rendus_finis_donnent_un_evenement_chacun():
    from app.services import sync_evenements as SE
    _semer()
    ev = asyncio.run(SE.evenements())["evenements"]
    par_type = {e["type"] for e in ev}
    assert "rendu_termine" in par_type and "rendu_echoue" in par_type
    ko = [e for e in ev if e["type"] == "rendu_echoue"][0]
    assert "insufficient credits" in ko["detail"]


def test_un_rendu_en_cours_ne_donne_aucun_evenement():
    from app.services import sync_evenements as SE
    _semer()
    ev = asyncio.run(SE.evenements())["evenements"]
    assert not any(e.get("ref") == "j-cours" for e in ev)


def test_un_post_du_donne_un_evenement_a_publier():
    from app.services import sync_evenements as SE
    _semer()
    ev = asyncio.run(SE.evenements())["evenements"]
    a_publier = [e for e in ev if e["type"] == "post_a_publier"]
    assert len(a_publier) == 1 and a_publier[0]["ref"] == "p-du"


def test_le_filtre_depuis_ne_rend_que_le_neuf():
    """Bornes EXPLICITES, pas `genere_a` : celui-ci est tronqué à la
    seconde, et un `completed_at` à 10:00:00,5 lui serait supérieur une
    fois sur deux. Une heure avant, une heure après : déterministe."""
    from app.services import sync_evenements as SE
    _semer()
    passe = (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
    futur = (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"
    assert asyncio.run(SE.evenements(depuis=passe))["evenements"], \
        "une borne dans le passé doit tout rendre"
    assert asyncio.run(SE.evenements(depuis=futur))["evenements"] == []


def test_les_quatre_familles_de_R12_sont_toutes_nommees():
    from app.services import sync_evenements as SE
    assert set(SE.FAMILLES) == {
        "rendu_termine", "rendu_echoue",
        "post_a_publier", "post_publie", "post_echoue",
        "plafond_approche", "plafond_depasse",
        "sync_terminee", "sync_conflit"}


def test_la_famille_plafond_dit_quelle_nest_pas_disponible():
    """Elle ne ment pas avec un zero : R11 P2 possede les plafonds."""
    from app.services import sync_evenements as SE
    _semer()
    p = asyncio.run(SE.evenements())["plafond"]
    assert p["disponible"] is False
    assert "R11" in p["raison"]


TESTS = [test_les_rendus_finis_donnent_un_evenement_chacun,
         test_un_rendu_en_cours_ne_donne_aucun_evenement,
         test_un_post_du_donne_un_evenement_a_publier,
         test_le_filtre_depuis_ne_rend_que_le_neuf,
         test_les_quatre_familles_de_R12_sont_toutes_nommees,
         test_la_famille_plafond_dit_quelle_nest_pas_disponible]

if __name__ == "__main__":
    failed = []
    for t in TESTS:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed.append(t.__name__)
            print(f"FAIL {t.__name__}: {e!r}")
    print(f"\n{len(TESTS) - len(failed)}/{len(TESTS)} OK")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run : `cd backend && python tests/test_sync_evenements.py`
Attendu : six `FAIL`, `0/6 OK`.

- [ ] **Step 3 : Écrire le service**

Créer `backend/app/services/sync_evenements.py` :

```python
# -*- coding: utf-8 -*-
"""P5 — les événements du PC, lus par le téléphone quand il rentre.

R12 réponse 9 demande QUATRE familles : rendu terminé ou échoué, post à
publier / publié / échoué, plafond approché ou dépassé, synchronisation
terminée ou en conflit. Les notifications sont NATIVES (E3) : ce module
ne notifie rien, il fournit la matière.

Le plafond est calculé par R11 P2 ; tant qu'il n'existe pas, la famille
`plafond_*` reste vide et le DIT — elle ne ment pas avec un zéro.
"""
from datetime import datetime

from sqlalchemy import select as _select

from app.services.sync_lot import _iso

FAMILLES = (
    "rendu_termine", "rendu_echoue",
    "post_a_publier", "post_publie", "post_echoue",
    "plafond_approche", "plafond_depasse",
    "sync_terminee", "sync_conflit",
)


async def evenements(depuis: str | None = None, limite: int = 200) -> dict:
    from app.services.storage import (JobRecord, ScheduledPost,
                                      async_session_factory)
    seuil = None
    if depuis:
        try:
            seuil = datetime.fromisoformat(depuis.replace("Z", ""))
        except ValueError:
            seuil = None
    out: list[dict] = []
    async with async_session_factory() as session:
        q = _select(JobRecord).where(
            JobRecord.status.in_(("completed", "failed")))
        if seuil is not None:
            q = q.where(JobRecord.completed_at > seuil)
        for j in (await session.execute(
                q.order_by(JobRecord.completed_at.desc())
                 .limit(limite))).scalars().all():
            out.append({
                "type": "rendu_termine" if j.status == "completed"
                        else "rendu_echoue",
                "ref": j.id,
                "titre": j.title or j.id,
                "detail": (j.error or "")[:200],
                "quand": _iso(j.completed_at),
            })
        q2 = _select(ScheduledPost).where(
            ScheduledPost.status.in_(("ready", "posted", "failed")))
        if seuil is not None:
            q2 = q2.where(ScheduledPost.run_at > seuil)
        for p in (await session.execute(
                q2.order_by(ScheduledPost.run_at.desc())
                  .limit(limite))).scalars().all():
            famille = {"ready": "post_a_publier", "posted": "post_publie",
                       "failed": "post_echoue"}[p.status]
            out.append({
                "type": famille,
                "ref": p.id,
                "titre": p.title,
                "detail": (p.error or "")[:200],
                "quand": _iso(p.posted_at or p.run_at),
            })
    return {"evenements": out, "familles": list(FAMILLES),
            "plafond": {"disponible": False,
                        "raison": "les plafonds appartiennent a R11 P2"},
            "genere_a": _iso(datetime.utcnow())}
```

- [ ] **Step 4 : Lancer, vérifier que ça passe**

Run : `cd backend && python tests/test_sync_evenements.py`
Attendu : six lignes `PASS`, puis `6/6 OK`.

- [ ] **Step 5 : Ajouter la route**

À la fin de `backend/app/api/routes.py` :

```python
@router.get("/sync/evenements")
async def sync_evenements_get(depuis: str | None = None, limite: int = 200):
    from app.services import sync_evenements as _se
    return await _se.evenements(depuis=depuis, limite=limite)
```

- [ ] **Step 6 : Écrire le test mobile qui échoue**

`deepotus-mobile/src/lib/__tests__/notifications.test.ts` :

```typescript
import { enNotification, FAMILLES_SILENCIEUSES } from "../notifications";

test("un rendu termine devient une notification lisible", () => {
  const n = enNotification({
    type: "rendu_termine", ref: "j-1", titre: "Le poulpe",
    detail: "", quand: "2026-09-04T09:00:00Z",
  });
  expect(n).not.toBeNull();
  expect(n!.title).toBe("Rendu termine : Le poulpe");
});

test("un rendu echoue porte la raison, pas un mot vague", () => {
  const n = enNotification({
    type: "rendu_echoue", ref: "j-2", titre: "Le rate",
    detail: "fal: 402 insufficient credits", quand: "2026-09-04T09:00:00Z",
  });
  expect(n!.body).toContain("insufficient credits");
});

test("les familles silencieuses ne notifient pas", () => {
  for (const f of FAMILLES_SILENCIEUSES) {
    expect(enNotification({ type: f, ref: "x", titre: "t", detail: "",
                            quand: "2026-09-04T09:00:00Z" })).toBeNull();
  }
});

test("un type inconnu ne fabrique pas une notification vide", () => {
  expect(enNotification({ type: "quelque_chose", ref: "x", titre: "t",
                          detail: "", quand: "2026-09-04T09:00:00Z" }))
    .toBeNull();
});
```

- [ ] **Step 7 : Écrire `notifications.ts`**

```typescript
export type Evenement = {
  type: string; ref: string; titre: string; detail: string; quand: string;
};

/** Ces événements arrivent par paquets à chaque synchronisation : les
 *  notifier tous transformerait le retour à la maison en avalanche. */
export const FAMILLES_SILENCIEUSES = ["post_publie"] as const;

const TITRES: Record<string, (e: Evenement) => string> = {
  rendu_termine: (e) => `Rendu termine : ${e.titre}`,
  rendu_echoue: (e) => `Rendu echoue : ${e.titre}`,
  post_a_publier: (e) => `A publier : ${e.titre}`,
  post_echoue: (e) => `Publication echouee : ${e.titre}`,
  plafond_approche: () => "Plafond approche",
  plafond_depasse: () => "Plafond depasse",
  sync_terminee: () => "Synchronisation terminee",
  sync_conflit: () => "Synchronisation : conflit",
};

export function enNotification(
  e: Evenement,
): { title: string; body: string } | null {
  if ((FAMILLES_SILENCIEUSES as readonly string[]).includes(e.type)) return null;
  const faire = TITRES[e.type];
  if (!faire) return null;
  return { title: faire(e), body: e.detail || e.titre };
}
```

- [ ] **Step 8 : Lancer les deux bancs**

Run : `cd /c/Users/olivi/deepotus-mobile && npm test`
Attendu : `Tests: 23 passed, 23 total`.
Run : `cd backend && python tests/test_sync_evenements.py`
Attendu : `6/6 OK`.

- [ ] **Step 9 : Commit**

```bash
git add backend/app/services/sync_evenements.py backend/app/api/routes.py backend/tests/test_sync_evenements.py
git commit -m 'notifications : les evenements du PC, les quatre familles de R12' -m 'Le backend ne notifie rien : il fournit la matiere, et les notifications
sont natives (E3). Un rendu echoue porte SA RAISON, pas un mot vague.

La famille plafond dit quelle nest pas disponible et POURQUOI — les
plafonds appartiennent a R11 P2 — au lieu de mentir avec un zero.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

```bash
cd /c/Users/olivi/deepotus-mobile
git add -A
git commit -m 'notifications : la traduction des evenements, sans avalanche' -m 'Les posts deja publies ne notifient pas : ils arrivent par paquets a chaque
synchronisation et transformeraient le retour a la maison en avalanche. Un
type inconnu ne fabrique pas une notification vide : il nen fabrique aucune.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Tâche 18 : P6 — dépenses : coût affiché, plafond mobile, compteur fondu

**Files:**
- Create: `deepotus-mobile/src/lib/depenses.ts`
- Create: `backend/app/services/sync_depenses.py`
- Modify: `backend/app/api/routes.py` (à la fin)
- Test: `deepotus-mobile/src/lib/__tests__/depenses.test.ts`, `backend/tests/test_sync_depenses.py`

**Coût :** faible. Le plafond journalier est **local au téléphone** (R12 réponse 10) : aucune table côté PC. Les tirs du téléphone sont **fondus** dans un fichier JSON — le registre estimé de `/cost/usage` appartient à R11 et n'est pas touché.

- [ ] **Step 1 : Écrire le test mobile qui échoue**

`deepotus-mobile/src/lib/__tests__/depenses.test.ts` :

```typescript
import { autorise, PLAFOND_DEFAUT_USD, resume } from "../depenses";

test("sous le plafond, le tir passe et le cout est dit", () => {
  const r = autorise(0.42, 1.5, PLAFOND_DEFAUT_USD);
  expect(r.ok).toBe(true);
  expect(r.message).toContain("0.42");
  expect(r.message).toContain("1.92");
});

test("au-dessus du plafond, le tir est refuse en chiffres", () => {
  const r = autorise(3.0, 4.5, 5.0);
  expect(r.ok).toBe(false);
  expect(r.message).toContain("5.00");
  expect(r.message).toContain("7.50");
});

test("pile sur le plafond, le tir passe encore", () => {
  expect(autorise(0.5, 4.5, 5.0).ok).toBe(true);
});

test("un cout inconnu est refuse plutot que devine", () => {
  const r = autorise(Number.NaN, 0, 5.0);
  expect(r.ok).toBe(false);
  expect(r.message).toContain("cout inconnu");
});

test("le resume du jour se fond dans le registre du PC", () => {
  const r = resume([
    { moteur: "fal", usd: 0.4, quand: "2026-09-04T09:00:00Z" },
    { moteur: "fal", usd: 0.2, quand: "2026-09-04T11:00:00Z" },
    { moteur: "elevenlabs", usd: 0.05, quand: "2026-09-04T12:00:00Z" },
  ], "2026-09-04");
  expect(r.jour).toBe("2026-09-04");
  expect(r.total_usd).toBeCloseTo(0.65, 5);
  expect(r.par_moteur).toEqual({ fal: 0.6, elevenlabs: 0.05 });
});
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run : `cd /c/Users/olivi/deepotus-mobile && npm test`
Attendu : `Cannot find module '../depenses'`, cinq tests en échec.

- [ ] **Step 3 : Écrire `depenses.ts`**

```typescript
/** P6 — R12 réponse 10 : « confirmation avec coût affiché + plafond
 *  journalier propre au mobile ». Le plafond du PC (mensuel, par moteur)
 *  appartient à R11 P2 ; celui-ci est LOCAL et journalier. */
export const PLAFOND_DEFAUT_USD = 5.0;

export type Tir = { moteur: string; usd: number; quand: string };

export function autorise(
  coutUsd: number, dejaAujourdhui: number, plafondUsd: number,
): { ok: boolean; message: string } {
  if (!Number.isFinite(coutUsd)) {
    return {
      ok: false,
      message: "cout inconnu : le tir est refuse plutot que devine",
    };
  }
  const apres = dejaAujourdhui + coutUsd;
  if (apres > plafondUsd) {
    return {
      ok: false,
      message: `plafond ${plafondUsd.toFixed(2)} $ : ce tir porterait la journee a ${apres.toFixed(2)} $`,
    };
  }
  return {
    ok: true,
    message: `${coutUsd.toFixed(2)} $ — la journee passerait a ${apres.toFixed(2)} $ sur ${plafondUsd.toFixed(2)} $`,
  };
}

export function resume(tirs: Tir[], jour: string) {
  const duJour = tirs.filter((t) => t.quand.startsWith(jour));
  const parMoteur: Record<string, number> = {};
  let total = 0;
  for (const t of duJour) {
    parMoteur[t.moteur] = Number(((parMoteur[t.moteur] || 0) + t.usd).toFixed(6));
    total += t.usd;
  }
  return { jour, total_usd: Number(total.toFixed(6)), par_moteur: parMoteur };
}
```

- [ ] **Step 4 : Écrire le banc PC qui échoue**

Créer `backend/tests/test_sync_depenses.py` :

```python
# -*- coding: utf-8 -*-
"""P6 — les tirs du téléphone fondus au registre du PC.

    python tests/test_sync_depenses.py          # depuis backend/
"""
import json
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


def test_une_fusion_ecrit_un_fichier_lisible():
    from app.config import settings
    from app.services import sync_depenses as SD
    SD.fondre("iPhone de Oli", {"jour": "2026-09-04", "total_usd": 0.65,
                                "par_moteur": {"fal": 0.6,
                                               "elevenlabs": 0.05}})
    f = settings.outputs_path / "_sync" / "depenses_mobile.json"
    lu = json.loads(f.read_text(encoding="utf-8"))
    assert lu["2026-09-04"]["iPhone de Oli"]["total_usd"] == 0.65


def test_une_seconde_fusion_du_meme_jour_remplace_sans_additionner():
    """Le téléphone envoie son TOTAL du jour, pas un delta : additionner
    doublerait la journée à chaque synchronisation."""
    from app.services import sync_depenses as SD
    SD.fondre("iPhone", {"jour": "2026-09-05", "total_usd": 1.0,
                         "par_moteur": {"fal": 1.0}})
    SD.fondre("iPhone", {"jour": "2026-09-05", "total_usd": 1.4,
                         "par_moteur": {"fal": 1.4}})
    assert SD.lire()["2026-09-05"]["iPhone"]["total_usd"] == 1.4


def test_deux_appareils_du_meme_jour_sadditionnent_au_total():
    from app.services import sync_depenses as SD
    SD.fondre("iPhone", {"jour": "2026-09-06", "total_usd": 1.0,
                         "par_moteur": {"fal": 1.0}})
    SD.fondre("tablette", {"jour": "2026-09-06", "total_usd": 0.5,
                           "par_moteur": {"fal": 0.5}})
    assert SD.total_du_jour("2026-09-06") == 1.5


def test_un_resume_malforme_est_refuse_en_le_disant():
    from app.services import sync_depenses as SD
    for mauvais in ({}, {"jour": "2026-09-07"},
                    {"jour": "pas-une-date", "total_usd": 1.0},
                    {"jour": "2026-09-07", "total_usd": "beaucoup"}):
        try:
            SD.fondre("x", mauvais)
        except ValueError:
            continue
        raise AssertionError(f"resume accepte : {mauvais!r}")


TESTS = [test_une_fusion_ecrit_un_fichier_lisible,
         test_une_seconde_fusion_du_meme_jour_remplace_sans_additionner,
         test_deux_appareils_du_meme_jour_sadditionnent_au_total,
         test_un_resume_malforme_est_refuse_en_le_disant]

if __name__ == "__main__":
    failed = []
    for t in TESTS:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed.append(t.__name__)
            print(f"FAIL {t.__name__}: {e!r}")
    print(f"\n{len(TESTS) - len(failed)}/{len(TESTS)} OK")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 5 : Écrire le service PC**

Créer `backend/app/services/sync_depenses.py` :

```python
# -*- coding: utf-8 -*-
"""P6 — les tirs du téléphone, fondus au registre du PC.

Ce module n'ÉCRIT PAS dans `/cost/usage` : ce registre estimé appartient
à R11, et le mélanger ferait mentir sa colonne « estimé ». Les dépenses
mobiles vivent dans leur propre fichier ; R11 P2 les additionnera quand
ses plafonds existeront.

Le téléphone envoie son TOTAL du jour, jamais un delta : additionner
doublerait la journée à chaque synchronisation.
"""
import json
import re
from pathlib import Path

from loguru import logger

from app.config import settings

_JOUR = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _fichier() -> Path:
    return settings.outputs_path / "_sync" / "depenses_mobile.json"


def lire() -> dict:
    f = _fichier()
    if not f.is_file():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        logger.warning("depenses mobiles illisibles, repart de zero")
        return {}


def fondre(appareil: str, resume: dict) -> dict:
    jour = str((resume or {}).get("jour") or "")
    if not _JOUR.match(jour):
        raise ValueError(f"jour attendu AAAA-MM-JJ, recu {jour!r}")
    total = (resume or {}).get("total_usd")
    if not isinstance(total, (int, float)) or isinstance(total, bool):
        raise ValueError(f"total_usd attendu numerique, recu {total!r}")
    tout = lire()
    tout.setdefault(jour, {})[str(appareil or "telephone")[:60]] = {
        "total_usd": round(float(total), 6),
        "par_moteur": {str(k): round(float(v), 6)
                       for k, v in ((resume or {}).get("par_moteur")
                                    or {}).items()
                       if isinstance(v, (int, float))},
    }
    f = _fichier()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(tout, ensure_ascii=False, indent=1),
                 encoding="utf-8")
    return tout[jour]


def total_du_jour(jour: str) -> float:
    return round(sum(v["total_usd"] for v in lire().get(jour, {}).values()), 6)
```

- [ ] **Step 6 : Lancer les deux bancs**

Run : `cd backend && python tests/test_sync_depenses.py`
Attendu : quatre lignes `PASS`, `4/4 OK`.
Run : `cd /c/Users/olivi/deepotus-mobile && npm test`
Attendu : `Tests: 28 passed, 28 total`.

- [ ] **Step 7 : Ajouter la route**

À la fin de `backend/app/api/routes.py` :

```python
@router.post("/sync/depenses")
async def sync_depenses_post(body: dict):
    from app.services import sync_depenses as _sd
    try:
        jour = _sd.fondre(str((body or {}).get("appareil") or "telephone"),
                          (body or {}).get("resume") or {})
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"fondu": True, "jour": jour}
```

- [ ] **Step 8 : Fin du lot 2 — tout mesurer**

```bash
cd backend
for f in test_sync_index.py test_sync_transfert.py test_sync_verrou.py test_mdns.py test_sync_evenements.py test_sync_depenses.py; do
  echo "=== $f"; python tests/$f | tail -2
done
```
Attendu : `6/6 OK`, `5/5 OK`, `6/6 OK`, `6/6 OK`, `6/6 OK`, `4/4 OK`.

Run : `powershell -ExecutionPolicy Bypass -File scripts\run-tests.ps1`
Attendu : aucun fichier dans `failed`.

- [ ] **Step 9 : Commit**

```bash
git add backend/app/services/sync_depenses.py backend/app/api/routes.py backend/tests/test_sync_depenses.py
git commit -m 'depenses : le plafond du telephone est a lui, le compteur se fond sans mentir' -m 'Le telephone envoie son TOTAL du jour, jamais un delta : additionner
doublerait la journee a chaque synchronisation, et le banc le verifie.

Le registre estime de /cost/usage nest PAS touche : le melanger ferait
mentir sa colonne estime. Les depenses mobiles ont leur fichier, que R11 P2
additionnera quand ses plafonds existeront.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

```bash
cd /c/Users/olivi/deepotus-mobile
git add -A
git commit -m 'depenses : confirmation chiffree avant chaque tir, plafond journalier local' -m 'Un cout inconnu est REFUSE plutot que devine : cest la seule reponse
honnete quand la grille de prix ne couvre pas le moteur choisi.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Lot 3 — le différenciant (D1 + D2 + D3 + D4)

### Tâche 19 : D1 — générer dans la poche, ranger au retour

**Files:**
- Create: `deepotus-mobile/src/lib/moteurs.ts`
- Create: `deepotus-mobile/src/lib/recette.ts`
- Create: `deepotus-mobile/src/lib/generer.ts`
- Test: `deepotus-mobile/src/lib/__tests__/moteurs.test.ts`, `deepotus-mobile/src/lib/__tests__/recette.test.ts`

**Coût :** élevé côté mobile, **nul côté PC** — la route de dépôt existe depuis la tâche 13, et la recette qu'elle écrit à côté du fichier est exactement ce que R9 P3 (lignée) et R1 P1 (« rouvrir prérempli ») liront. Aucun patch de bundle. R12 réponse 15 demande **tout** : images et retouches, clips et extension, voix et musique, texte par LLM ; ce lot livre le **socle commun** (registre, estimation, appel, dépôt) et le décline moteur par moteur.

- [ ] **Step 1 : Écrire les tests qui échouent**

`deepotus-mobile/src/lib/__tests__/moteurs.test.ts` :

```typescript
import { MOTEURS, estimer, clesRequises } from "../moteurs";

test("les six familles de R12 reponse 15 sont toutes au registre", () => {
  const familles = new Set(Object.values(MOTEURS).map((m) => m.famille));
  expect(familles).toEqual(new Set(["image", "retouche", "video",
                                    "extension", "voix", "musique", "texte"]));
});

test("chaque moteur dit sa cle, son unite et son prix", () => {
  for (const [id, m] of Object.entries(MOTEURS)) {
    expect(typeof m.cle).toBe("string");
    expect(m.cle.length).toBeGreaterThan(0);
    expect(["appel", "seconde", "caractere", "millier_de_jetons"])
      .toContain(m.unite);
    expect(typeof m.usd_par_unite).toBe("number");
    expect(m.usd_par_unite).toBeGreaterThan(0);
    expect(m.mesure_le).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(id).toBe(m.id);
  }
});

test("l estimation multiplie la quantite par le prix", () => {
  const m = MOTEURS["fal-flux-image"];
  expect(estimer("fal-flux-image", 1)).toBeCloseTo(m.usd_par_unite, 6);
  expect(estimer("fal-flux-image", 4)).toBeCloseTo(m.usd_par_unite * 4, 6);
});

test("un moteur inconnu rend NaN, jamais zero", () => {
  expect(Number.isNaN(estimer("moteur-qui-nexiste-pas", 1))).toBe(true);
});

test("les cles requises sont dedupliquees et triees", () => {
  const c = clesRequises(["fal-flux-image", "fal-veo-extend",
                          "elevenlabs-tts"]);
  expect(c).toEqual(["ELEVENLABS_API_KEY", "FAL_KEY"]);
});
```

`deepotus-mobile/src/lib/__tests__/recette.test.ts` :

```typescript
import { batirRecette, verifierRecette } from "../recette";

test("la recette porte les six champs que le PC relira", () => {
  const r = batirRecette({
    moteurId: "fal-flux-image",
    prompt: "un poulpe bioluminescent",
    graine: 42,
    coutUsd: 0.03,
    parent: "gen_aa11bb22.png",
    relation: "retouche",
  });
  expect(r).toEqual({
    moteur: "fal-flux-image",
    prompt: "un poulpe bioluminescent",
    graine: 42,
    cout_usd: 0.03,
    parent: "gen_aa11bb22.png",
    relation: "retouche",
  });
});

test("une generation sans parent n en invente pas", () => {
  const r = batirRecette({
    moteurId: "fal-flux-image", prompt: "p", graine: null, coutUsd: 0.03,
  });
  expect(r.parent).toBeNull();
  expect(r.relation).toBeNull();
});

test("une relation sans parent est refusee", () => {
  const v = verifierRecette({
    moteur: "m", prompt: "p", graine: null, cout_usd: 0.1,
    parent: null, relation: "retouche",
  });
  expect(v.ok).toBe(false);
  expect(v.raison).toContain("relation sans parent");
});

test("un cout non numerique est refuse", () => {
  const v = verifierRecette({
    moteur: "m", prompt: "p", graine: null, cout_usd: Number.NaN,
    parent: null, relation: null,
  });
  expect(v.ok).toBe(false);
  expect(v.raison).toContain("cout_usd");
});

test("les six relations de R9 P3 sont les seules acceptees", () => {
  for (const rel of ["retouche", "extension", "stems", "version",
                     "detourage", "recadrage"]) {
    expect(verifierRecette({
      moteur: "m", prompt: "p", graine: null, cout_usd: 0.1,
      parent: "a.png", relation: rel,
    }).ok).toBe(true);
  }
  expect(verifierRecette({
    moteur: "m", prompt: "p", graine: null, cout_usd: 0.1,
    parent: "a.png", relation: "bricolage",
  }).ok).toBe(false);
});
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run : `cd /c/Users/olivi/deepotus-mobile && npm test`
Attendu : `Cannot find module '../moteurs'` et `'../recette'`, dix tests en échec.

- [ ] **Step 3 : Écrire `moteurs.ts`**

```typescript
/** D1 — les moteurs que le TÉLÉPHONE peut appeler lui-même, avec les
 *  mêmes clés que le PC. Les prix sont ceux relevés dans la grille de
 *  `backend/app/services/pricing.py` : chaque ligne porte SA date de
 *  relevé, parce qu'un prix sans date est un souvenir.
 *
 *  AVANT DE MODIFIER UN PRIX : le relever sur la page tarifaire du
 *  fournisseur, écrire la date du jour dans `mesure_le`, et refaire
 *  passer le banc. */
export type Unite = "appel" | "seconde" | "caractere" | "millier_de_jetons";

export type Moteur = {
  id: string;
  famille: "image" | "retouche" | "video" | "extension" | "voix"
         | "musique" | "texte";
  libelle: string;
  cle: string;
  point: string;
  unite: Unite;
  usd_par_unite: number;
  mesure_le: string;
};

export const MOTEURS: Record<string, Moteur> = {
  "fal-flux-image": {
    id: "fal-flux-image", famille: "image", libelle: "Image (FLUX)",
    cle: "FAL_KEY", point: "fal-ai/flux/dev",
    unite: "appel", usd_par_unite: 0.025, mesure_le: "2026-09-03",
  },
  "fal-nano-banana-retouche": {
    id: "fal-nano-banana-retouche", famille: "retouche",
    libelle: "Retouche (Nano Banana Pro)",
    cle: "FAL_KEY", point: "fal-ai/nano-banana-pro/edit",
    unite: "appel", usd_par_unite: 0.14, mesure_le: "2026-09-03",
  },
  "fal-seedance-25": {
    id: "fal-seedance-25", famille: "video", libelle: "Clip (Seedance 2.5)",
    cle: "FAL_KEY", point: "fal-ai/bytedance/seedance/v2-5/image-to-video",
    unite: "seconde", usd_par_unite: 0.473, mesure_le: "2026-09-03",
  },
  "fal-veo-extend": {
    id: "fal-veo-extend", famille: "extension",
    libelle: "Extension (Veo 3.1 extend)",
    cle: "FAL_KEY", point: "fal-ai/veo3.1/extend-video",
    unite: "seconde", usd_par_unite: 0.4, mesure_le: "2026-09-03",
  },
  "elevenlabs-tts": {
    id: "elevenlabs-tts", famille: "voix", libelle: "Voix off (ElevenLabs)",
    cle: "ELEVENLABS_API_KEY", point: "text-to-speech",
    unite: "caractere", usd_par_unite: 0.00018, mesure_le: "2026-09-03",
  },
  "fal-lyria-musique": {
    id: "fal-lyria-musique", famille: "musique", libelle: "Musique (Lyria 3)",
    cle: "FAL_KEY", point: "fal-ai/lyria3",
    unite: "appel", usd_par_unite: 0.06, mesure_le: "2026-09-03",
  },
  "anthropic-texte": {
    id: "anthropic-texte", famille: "texte", libelle: "Texte (Anthropic)",
    cle: "ANTHROPIC_API_KEY", point: "messages",
    unite: "millier_de_jetons", usd_par_unite: 0.015, mesure_le: "2026-09-03",
  },
};

/** Le coût estimé d'un tir. Un moteur inconnu rend NaN — jamais zéro :
 *  `depenses.autorise` refuse alors le tir au lieu de le laisser passer
 *  pour gratuit. */
export function estimer(moteurId: string, quantite: number): number {
  const m = MOTEURS[moteurId];
  if (!m) return Number.NaN;
  return m.usd_par_unite * quantite;
}

export function clesRequises(moteurIds: string[]): string[] {
  return [...new Set(moteurIds.map((i) => MOTEURS[i]?.cle).filter(Boolean))]
    .sort() as string[];
}
```

- [ ] **Step 4 : Écrire `recette.ts`**

```typescript
/** D1 — la recette qui accompagne CHAQUE fichier remonté au PC.
 *  `sync_transfert.deposer` l'écrit dans `<nom>.recette.json`, et c'est
 *  R9 P3 (lignée) puis R1 P1 (« rouvrir prérempli ») qui la reliront.
 *  Les six relations sont exactement celles nommées par R9 P3. */
export const RELATIONS = ["retouche", "extension", "stems", "version",
                          "detourage", "recadrage"] as const;

export type Recette = {
  moteur: string;
  prompt: string;
  graine: number | null;
  cout_usd: number;
  parent: string | null;
  relation: string | null;
};

export function batirRecette(o: {
  moteurId: string; prompt: string; graine?: number | null;
  coutUsd: number; parent?: string | null; relation?: string | null;
}): Recette {
  return {
    moteur: o.moteurId,
    prompt: o.prompt,
    graine: o.graine ?? null,
    cout_usd: o.coutUsd,
    parent: o.parent ?? null,
    relation: o.relation ?? null,
  };
}

export function verifierRecette(
  r: Recette,
): { ok: true } | { ok: false; raison: string } {
  if (!Number.isFinite(r.cout_usd)) {
    return { ok: false, raison: "cout_usd doit etre un nombre" };
  }
  if (r.relation && !r.parent) {
    return { ok: false, raison: "relation sans parent : la lignee serait fausse" };
  }
  if (r.relation && !(RELATIONS as readonly string[]).includes(r.relation)) {
    return {
      ok: false,
      raison: `relation ${r.relation} inconnue (attendu : ${RELATIONS.join(", ")})`,
    };
  }
  return { ok: true };
}
```

- [ ] **Step 5 : Écrire `generer.ts`**

```typescript
import { MOTEURS, estimer } from "./moteurs";
import { batirRecette, verifierRecette, type Recette } from "./recette";
import { autorise } from "./depenses";
import { lireDuCoffre } from "./coffre";
import { appeler } from "./pc";

/** Un tir depuis le téléphone : estimer, faire confirmer, appeler le
 *  fournisseur avec la clé DU COFFRE, puis rendre le fichier et sa
 *  recette. Le dépôt au PC se fait à la synchronisation suivante, pas
 *  ici : le téléphone doit pouvoir générer sans réseau local. */
export type Resultat = {
  octets: Uint8Array; nom: string; recette: Recette; sha256: string;
};

export async function tirer(o: {
  moteurId: string;
  quantite: number;
  prompt: string;
  graine?: number | null;
  parent?: string | null;
  relation?: string | null;
  dejaAujourdhui: number;
  plafondUsd: number;
  confirmer: (message: string) => Promise<boolean>;
  envoyer: (point: string, cle: string, corps: unknown) => Promise<Uint8Array>;
  empreinte: (o: Uint8Array) => Promise<string>;
}): Promise<Resultat | null> {
  const m = MOTEURS[o.moteurId];
  if (!m) throw new Error(`moteur inconnu : ${o.moteurId}`);
  const cout = estimer(o.moteurId, o.quantite);
  const verdict = autorise(cout, o.dejaAujourdhui, o.plafondUsd);
  if (!verdict.ok) throw new Error(verdict.message);
  if (!(await o.confirmer(verdict.message))) return null;

  const cle = await lireDuCoffre(m.cle);
  if (!cle) {
    throw new Error(
      `${m.cle} absente du coffre — importez l archive chiffree du PC`);
  }
  const octets = await o.envoyer(m.point, cle, {
    prompt: o.prompt, seed: o.graine ?? undefined,
  });
  const recette = batirRecette({
    moteurId: o.moteurId, prompt: o.prompt, graine: o.graine ?? null,
    coutUsd: cout, parent: o.parent ?? null, relation: o.relation ?? null,
  });
  const v = verifierRecette(recette);
  if (!v.ok) throw new Error(v.raison);
  const sha256 = await o.empreinte(octets);
  return { octets, nom: `mob_${sha256.slice(0, 8)}.png`, recette, sha256 };
}

/** Le dépôt au PC, à la synchronisation. Rend le nom RÉELLEMENT écrit :
 *  le PC renomme quand le nom est déjà pris, et le téléphone doit le
 *  savoir pour ne pas croire qu'il a envoyé autre chose. */
export async function deposer(r: Resultat, appareil: string): Promise<string> {
  const f = new FormData();
  f.append("file", new Blob([r.octets]) as any, r.nom);
  f.append("sha256", r.sha256);
  f.append("recette", JSON.stringify(r.recette));
  f.append("appareil", appareil);
  const rep = await appeler("/api/sync/depot", { method: "POST", body: f as any },
                            appareil);
  if (!rep.ok) throw new Error(`depot refuse : ${await rep.text()}`);
  return (await rep.json()).nom as string;
}
```

- [ ] **Step 6 : Lancer, vérifier que tout passe**

Run : `cd /c/Users/olivi/deepotus-mobile && npm test`
Attendu : `Tests: 38 passed, 38 total`.

- [ ] **Step 7 : Mesurer un tir réel, une fois**

Sur un téléphone appairé, clés importées : générer une image, la déposer, puis sur le PC :

```bash
cd backend && python -c "import sys,json,glob,os; sys.path.insert(0,'.'); from app.config import settings; f=sorted(glob.glob(str(settings.images_path/'mob_*.recette.json')), key=os.path.getmtime)[-1]; print(f); print(open(f,encoding='utf-8').read())"
```
Attendu : le chemin de la recette la plus récente, puis un JSON portant `moteur`, `prompt`, `graine`, `cout_usd`, `parent`, `relation`, `appareil`, `depose_a`, `sha256`.

- [ ] **Step 8 : Commit**

```bash
cd /c/Users/olivi/deepotus-mobile
git add -A
git commit -m 'generer : le telephone tire avec les memes cles, et rend sa recette' -m 'Chaque moteur porte sa cle, son unite, son prix et LA DATE de son releve :
un prix sans date est un souvenir. Un moteur inconnu rend NaN, jamais zero —
le plafond refuse alors le tir au lieu de le laisser passer pour gratuit.

La recette porte les six champs que le PC relira, et refuse une relation
sans parent : une lignee fausse est pire quune lignee absente. Le depot rend
le nom REELLEMENT ecrit, parce que le PC renomme quand le nom est pris.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Tâche 20 : D2 — partages entrants triés

**Files:**
- Create: `deepotus-mobile/src/lib/partage.ts`
- Modify: `deepotus-mobile/app.json` (extensions natives)
- Test: `deepotus-mobile/src/lib/__tests__/partage.test.ts`

**Coût :** élevé et **irréductible** : une extension de partage iOS est une cible native séparée, et Android demande ses filtres d'intention. C'est le poste que la tâche 1 a mesuré comme **ne départageant pas** les deux frameworks — il coûte pareil des deux côtés. Aucune ligne côté PC : les cibles réutilisent les routes existantes.

- [ ] **Step 1 : Écrire le test qui échoue**

`deepotus-mobile/src/lib/__tests__/partage.test.ts` :

```typescript
import { CIBLES, trier } from "../partage";

test("une photo propose les quatre cibles visuelles, dans l ordre", () => {
  const t = trier({ mime: "image/jpeg", uri: "file:///photo.jpg" });
  expect(t.map((c) => c.id))
    .toEqual(["bibliotheque", "quick", "materiel", "trois_d"]);
});

test("un lien va vers News", () => {
  const t = trier({ mime: "text/plain", texte: "https://exemple.fr/article" });
  expect(t[0].id).toBe("news");
});

test("un texte sans URL va vers Chapitres puis brief", () => {
  const t = trier({ mime: "text/plain", texte: "une idee de scene" });
  expect(t.map((c) => c.id)).toEqual(["chapitres", "brief"]);
});

test("un texte QUI CONTIENT une URL au milieu va quand meme vers News", () => {
  const t = trier({ mime: "text/plain",
                    texte: "regarde ca https://exemple.fr/a c est bien" });
  expect(t[0].id).toBe("news");
});

test("une video n est pas confondue avec une photo", () => {
  const t = trier({ mime: "video/mp4", uri: "file:///clip.mp4" });
  expect(t.map((c) => c.id)).toEqual(["bibliotheque"]);
});

test("un type inconnu ne propose rien plutot que n importe quoi", () => {
  expect(trier({ mime: "application/x-inconnu", uri: "file:///x.bin" }))
    .toEqual([]);
});

test("chaque cible nomme la route qu elle appellera", () => {
  for (const c of CIBLES) {
    expect(c.route.startsWith("/api/")).toBe(true);
    expect(c.libelle.length).toBeGreaterThan(0);
  }
});
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run : `cd /c/Users/olivi/deepotus-mobile && npm test`
Attendu : `Cannot find module '../partage'`, sept tests en échec.

- [ ] **Step 3 : Écrire `partage.ts`**

```typescript
/** D2 — R12 réponse 8, mot pour mot : « photo → Bibliothèque/Quick/
 *  Material Forge/3D ; lien ou article → News ; texte ou idée →
 *  Chapitres ou brief ». Le tri est une TABLE, pas une suite de `if`
 *  cachés dans un écran : il se mesure. */
export type Entrant = { mime: string; uri?: string; texte?: string };

export type Cible = {
  id: string; libelle: string; route: string;
  accepte: (e: Entrant) => boolean;
};

const EST_IMAGE = (e: Entrant) => e.mime.startsWith("image/");
const EST_VIDEO = (e: Entrant) => e.mime.startsWith("video/");
const EST_TEXTE = (e: Entrant) => e.mime.startsWith("text/") && !!e.texte;
const A_UNE_URL = (e: Entrant) => /https?:\/\/\S+/.test(e.texte || "");

export const CIBLES: Cible[] = [
  { id: "bibliotheque", libelle: "Bibliotheque", route: "/api/sync/depot",
    accepte: (e) => EST_IMAGE(e) || EST_VIDEO(e) },
  { id: "quick", libelle: "Quick — image vers clip",
    route: "/api/sync/depot", accepte: EST_IMAGE },
  { id: "materiel", libelle: "Material Forge", route: "/api/sync/depot",
    accepte: EST_IMAGE },
  { id: "trois_d", libelle: "Image vers 3D", route: "/api/sync/depot",
    accepte: EST_IMAGE },
  { id: "news", libelle: "News — article vers reel",
    route: "/api/news/ingest", accepte: (e) => EST_TEXTE(e) && A_UNE_URL(e) },
  { id: "chapitres", libelle: "Chapitres", route: "/api/chapters",
    accepte: (e) => EST_TEXTE(e) && !A_UNE_URL(e) },
  { id: "brief", libelle: "Brief de campagne", route: "/api/schedule",
    accepte: (e) => EST_TEXTE(e) && !A_UNE_URL(e) },
];

/** Les cibles possibles, dans l'ordre du plus probable au moins probable.
 *  Une entrée qu'aucune cible n'accepte rend une liste VIDE : l'écran dit
 *  « rien à faire de ce partage » au lieu de proposer n'importe quoi. */
export function trier(e: Entrant): Cible[] {
  return CIBLES.filter((c) => c.accepte(e));
}
```

- [ ] **Step 4 : Lancer, vérifier que tout passe**

Run : `cd /c/Users/olivi/deepotus-mobile && npm test`
Attendu : `Tests: 45 passed, 45 total`.

- [ ] **Step 5 : Déclarer les extensions natives**

Dans `deepotus-mobile/app.json`, dans `expo` :

```json
    "ios": {
      "bundleIdentifier": "xyz.deepotus.compagnon",
      "infoPlist": {
        "NSLocalNetworkUsageDescription": "Pour retrouver votre PC DeepotusVideoGen sur le Wi-Fi de la maison.",
        "NSBonjourServices": ["_deepotus._tcp"],
        "NSCameraUsageDescription": "Pour scanner le QR d appairage affiche par le PC."
      }
    },
    "android": {
      "package": "xyz.deepotus.compagnon",
      "permissions": ["INTERNET", "CAMERA", "POST_NOTIFICATIONS",
                      "CHANGE_WIFI_MULTICAST_STATE"],
      "intentFilters": [
        {
          "action": "SEND",
          "category": ["DEFAULT"],
          "data": [{ "mimeType": "image/*" }, { "mimeType": "video/*" },
                   { "mimeType": "text/plain" }]
        }
      ]
    }
```

- [ ] **Step 6 : Reconstruire les projets natifs**

```bash
cd /c/Users/olivi/deepotus-mobile
npx expo prebuild --clean
```
Attendu : `✔ Finished prebuild`, et les dossiers `android/` et `ios/` recréés.

Vérifier que le plist a bien reçu les clés :
```bash
grep -c "NSBonjourServices" ios/*/Info.plist
```
Attendu : `1`.

- [ ] **Step 7 : Ajouter l'extension de partage iOS**

L'extension iOS est une **cible native** : `expo prebuild` ne la crée pas. Suivre exactement, dans `ios/deepotusmobile.xcodeproj` ouvert dans Xcode : `File > New > Target > Share Extension`, nom `PartageDeepotus`, langage Swift, puis dans son `Info.plist` régler `NSExtensionActivationRule` sur :

```xml
<key>NSExtensionActivationRule</key>
<dict>
  <key>NSExtensionActivationSupportsImageWithMaxCount</key><integer>1</integer>
  <key>NSExtensionActivationSupportsMovieWithMaxCount</key><integer>1</integer>
  <key>NSExtensionActivationSupportsText</key><true/>
  <key>NSExtensionActivationSupportsWebURLWithMaxCount</key><integer>1</integer>
</dict>
```

Cette cible écrit l'entrée partagée dans le groupe d'app `group.xyz.deepotus.compagnon` ; l'application la lit au lancement et appelle `trier()`.

Vérification, sur un iPhone : partager une photo depuis Photos, choisir « Deepotus », et voir les **quatre** cibles visuelles. Une extension qui n'apparaît pas dans la feuille de partage signifie que la règle d'activation ci-dessus n'a pas été enregistrée.

- [ ] **Step 8 : Commit**

```bash
cd /c/Users/olivi/deepotus-mobile
git add -A
git commit -m 'partage : le tri des entrants est une table, donc il se mesure' -m 'R12 reponse 8 donne trois routes : photo vers quatre cibles visuelles, lien
vers News, texte vers Chapitres ou brief. Le tri vit dans une TABLE et non
dans une suite de conditions cachees dans un ecran : sept tests le mesurent,
y compris le texte qui contient une URL au milieu.

Un type inconnu ne propose RIEN : lecran dit quil ne sait pas quoi en faire
plutot que de proposer nimporte quoi.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Tâche 21 : D3 — écrire hors ligne sous verrou

**Files:**
- Create: `backend/app/api/routes.py` — route `POST /sync/chapitre/{chapter_id}` (à la fin)
- Create: `deepotus-mobile/src/lib/chapitre.ts`
- Test: `backend/tests/test_sync_chapitre.py`, `deepotus-mobile/src/lib/__tests__/chapitre.test.ts`

**Coût :** faible côté PC (une route, aucune table neuve — `ChapterLock` existe depuis la tâche 14), moyen côté mobile. **Ce que cette tâche NE fait PAS** : versionner le texte. R3 P2 possède les versions ; le verrou garantit seulement que **le PC n'a pas touché au texte pendant l'absence**, donc rien n'est écrasé en aveugle.

- [ ] **Step 1 : Écrire le banc PC qui échoue**

Créer `backend/tests/test_sync_chapitre.py` :

```python
# -*- coding: utf-8 -*-
"""D3 — le chapitre écrit hors ligne, rendu au retour.

    python tests/test_sync_chapitre.py          # depuis backend/
"""
import asyncio
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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _client():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services.storage import init_db
    asyncio.run(init_db())
    return TestClient(app)


def _chapitre(c):
    return c.post("/api/chapters", json={"title": "Emporte",
                                         "script_text": "Texte du PC."}).json()["id"]


def test_lappareil_qui_tient_le_verrou_ecrit_a_travers():
    c = _client()
    i = _chapitre(c)
    assert c.post(f"/api/sync/verrou/{i}",
                  json={"device_id": "dev-1", "nom": "iPhone"}).status_code == 200
    r = c.post(f"/api/sync/chapitre/{i}",
               json={"device_id": "dev-1", "script_text": "Ecrit dans le train."})
    assert r.status_code == 200, (r.status_code, r.text[:200])
    assert c.get(f"/api/chapters/{i}").json()["script_text"] == \
        "Ecrit dans le train."


def test_un_autre_appareil_ne_peut_pas_ecrire_a_travers():
    c = _client()
    i = _chapitre(c)
    c.post(f"/api/sync/verrou/{i}", json={"device_id": "dev-1", "nom": "iPhone"})
    r = c.post(f"/api/sync/chapitre/{i}",
               json={"device_id": "dev-2", "script_text": "Vol de texte."})
    assert r.status_code == 409, (r.status_code, r.text[:200])
    assert c.get(f"/api/chapters/{i}").json()["script_text"] == "Texte du PC."


def test_sans_verrou_lecriture_a_travers_est_refusee():
    """Cette route sert le RETOUR d'un chapitre emporté, pas une porte
    dérobée pour écrire sans avoir rien emporté."""
    c = _client()
    i = _chapitre(c)
    r = c.post(f"/api/sync/chapitre/{i}",
               json={"device_id": "dev-1", "script_text": "x"})
    assert r.status_code == 409, (r.status_code, r.text[:200])


def test_rendre_libere_le_verrou_et_le_PC_reecrit():
    c = _client()
    i = _chapitre(c)
    c.post(f"/api/sync/verrou/{i}", json={"device_id": "dev-1", "nom": "iPhone"})
    r = c.post(f"/api/sync/chapitre/{i}",
               json={"device_id": "dev-1", "script_text": "Rendu.",
                     "rendre": True})
    assert r.status_code == 200 and r.json()["libere"] is True
    assert c.put(f"/api/chapters/{i}",
                 json={"script_text": "Le PC reprend."}).status_code == 200


def test_les_annotations_horodatees_sont_conservees():
    c = _client()
    i = _chapitre(c)
    c.post(f"/api/sync/verrou/{i}", json={"device_id": "dev-1", "nom": "iPhone"})
    c.post(f"/api/sync/chapitre/{i}", json={
        "device_id": "dev-1", "script_text": "Texte.",
        "annotations": [{"quand": "2026-09-04T09:00:00Z", "offset": 3,
                         "texte": "verifier ce nom"}]})
    lu = c.get(f"/api/sync/chapitre/{i}/annotations").json()["annotations"]
    assert len(lu) == 1
    assert lu[0]["texte"] == "verifier ce nom"
    assert lu[0]["par"] == "iPhone"


TESTS = [test_lappareil_qui_tient_le_verrou_ecrit_a_travers,
         test_un_autre_appareil_ne_peut_pas_ecrire_a_travers,
         test_sans_verrou_lecriture_a_travers_est_refusee,
         test_rendre_libere_le_verrou_et_le_PC_reecrit,
         test_les_annotations_horodatees_sont_conservees]

if __name__ == "__main__":
    failed = []
    for t in TESTS:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed.append(t.__name__)
            print(f"FAIL {t.__name__}: {e!r}")
    print(f"\n{len(TESTS) - len(failed)}/{len(TESTS)} OK")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run : `cd backend && python tests/test_sync_chapitre.py`
Attendu : cinq `FAIL` (404 sur la route absente), `0/5 OK`.

- [ ] **Step 3 : Ajouter la route**

À la fin de `backend/app/api/routes.py` :

```python
# ── D3 : le chapitre emporté revient ────────────────────────────────────────
# Cette route est la SEULE façon d'écrire un chapitre verrouillé, et elle
# exige l'appareil qui l'a emporté. Elle ne VERSIONNE pas : R3 P2 possède
# les versions ; le verrou garantit que le PC n'a rien changé entre-temps,
# donc rien n'est écrasé en aveugle.

@router.post("/sync/chapitre/{chapter_id}")
async def sync_chapitre_rendre(chapter_id: str, body: dict):
    import json as _json
    from app.services import sync_verrou as _sv
    from app.services.storage import Chapter, async_session_factory
    device_id = str((body or {}).get("device_id") or "")
    verrou = await _sv.qui(chapter_id)
    if not verrou or verrou["device_id"] != device_id:
        raise HTTPException(
            409, "ce chapitre n est pas emporte par cet appareil")
    async with async_session_factory() as session:
        ch = await session.get(Chapter, chapter_id)
        if not ch:
            raise HTTPException(404, "Chapter not found")
        if "script_text" in body:
            ch.script_text = body["script_text"] or ""
        ch.updated_at = datetime.utcnow()
        await session.commit()
    annotations = (body or {}).get("annotations") or []
    if annotations:
        dossier = settings.outputs_path / "_sync" / "annotations"
        dossier.mkdir(parents=True, exist_ok=True)
        f = dossier / f"{Path(chapter_id).name}.json"
        deja = []
        if f.is_file():
            try:
                deja = _json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                deja = []
        for a in annotations:
            deja.append({"quand": str(a.get("quand") or ""),
                         "offset": int(a.get("offset") or 0),
                         "texte": str(a.get("texte") or "")[:1000],
                         "par": verrou["nom"]})
        f.write_text(_json.dumps(deja, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    libere = False
    if (body or {}).get("rendre"):
        libere = await _sv.liberer(chapter_id, device_id)
    return {"ecrit": True, "libere": libere}


@router.get("/sync/chapitre/{chapter_id}/annotations")
async def sync_chapitre_annotations(chapter_id: str):
    import json as _json
    f = (settings.outputs_path / "_sync" / "annotations"
         / f"{Path(chapter_id).name}.json")
    if not f.is_file():
        return {"annotations": []}
    try:
        return {"annotations": _json.loads(f.read_text(encoding="utf-8"))}
    except ValueError:
        return {"annotations": []}
```

- [ ] **Step 4 : Lancer, vérifier que ça passe**

Run : `cd backend && python tests/test_sync_chapitre.py`
Attendu : cinq lignes `PASS`, puis `5/5 OK`.

- [ ] **Step 5 : Écrire le test mobile qui échoue**

`deepotus-mobile/src/lib/__tests__/chapitre.test.ts` :

```typescript
import { fusionnerAnnotations, resumeDuRetour } from "../chapitre";

test("les annotations sont triees par instant, pas par ordre d arrivee", () => {
  const a = fusionnerAnnotations([
    { quand: "2026-09-04T12:00:00Z", offset: 10, texte: "b" },
    { quand: "2026-09-04T09:00:00Z", offset: 3, texte: "a" },
  ]);
  expect(a.map((x) => x.texte)).toEqual(["a", "b"]);
});

test("deux annotations identiques ne sont ecrites qu une fois", () => {
  const meme = { quand: "2026-09-04T09:00:00Z", offset: 3, texte: "a" };
  expect(fusionnerAnnotations([meme, { ...meme }]).length).toBe(1);
});

test("le resume du retour dit ce qui part et ce qui reste", () => {
  const r = resumeDuRetour("Texte du PC.", "Texte du train.", 2);
  expect(r).toContain("2 annotation");
  expect(r).toContain("15 caracteres");
});

test("un texte inchange le dit au lieu de faire semblant d ecrire", () => {
  expect(resumeDuRetour("pareil", "pareil", 0)).toContain("inchange");
});
```

- [ ] **Step 6 : Écrire `chapitre.ts`**

```typescript
export type Annotation = { quand: string; offset: number; texte: string };

/** Les annotations remontent triées par INSTANT, pas par ordre d'arrivée :
 *  R9 D2 les veut horodatées, et deux appareils peuvent en produire. */
export function fusionnerAnnotations(a: Annotation[]): Annotation[] {
  const vues = new Set<string>();
  const uniques: Annotation[] = [];
  for (const x of a) {
    const cle = `${x.quand}|${x.offset}|${x.texte}`;
    if (vues.has(cle)) continue;
    vues.add(cle);
    uniques.push(x);
  }
  return uniques.sort((p, q) => p.quand.localeCompare(q.quand));
}

/** Ce que l'écran affiche AVANT de rendre le chapitre. Un retour qui
 *  n'annonce pas ce qu'il va écrire est un retour qu'on n'ose pas faire. */
export function resumeDuRetour(
  avant: string, apres: string, nbAnnotations: number,
): string {
  if (avant === apres && nbAnnotations === 0) {
    return "texte inchange, aucune annotation — rien a rendre";
  }
  const delta = apres.length - avant.length;
  const signe = delta >= 0 ? "+" : "";
  return `${signe}${delta} caracteres, ${nbAnnotations} annotation(s) — le verrou sera libere`;
}
```

- [ ] **Step 7 : Lancer les deux bancs**

Run : `cd /c/Users/olivi/deepotus-mobile && npm test`
Attendu : `Tests: 49 passed, 49 total`.
Run : `cd backend && python tests/test_sync_chapitre.py`
Attendu : `5/5 OK`.

- [ ] **Step 8 : Commit**

```bash
git add backend/app/api/routes.py backend/tests/test_sync_chapitre.py
git commit -m 'chapitre : le retour passe par le verrou, et par lui seul' -m 'Ecrire un chapitre verrouille na quune porte, et elle exige lappareil qui
la emporte : un autre appareil recoit 409 et le texte du PC ne bouge pas.
Sans verrou du tout, la route refuse aussi — elle sert le RETOUR dun
chapitre emporte, pas une porte derobee.

Elle ne versionne PAS : R3 P2 possede les versions. Le verrou garantit que
le PC na rien change pendant labsence, donc rien nest ecrase en aveugle —
cest ecrit dans le code, pas suppose.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

```bash
cd /c/Users/olivi/deepotus-mobile
git add -A
git commit -m 'chapitre : les annotations triees par instant, le retour annonce' -m 'Un retour qui nannonce pas ce quil va ecrire est un retour quon nose pas
faire : lecran dit le delta en caracteres et le nombre dannotations, et dit
inchange quand il ny a rien a rendre.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

### Tâche 22 : D4 — recette lançable depuis le téléphone

**Files:**
- Create: `backend/app/services/sync_recettes.py`
- Modify: `backend/app/api/routes.py` (à la fin)
- Test: `backend/tests/test_sync_recettes.py`

**Coût :** faible et **délibérément borné**. **Ce que cette tâche fait** : lister les graphes sauvegardés et mettre une exécution EN FILE pour le PC. **Ce qu'elle ne fait PAS** : exécuter un graphe. L'exécution appartient à **R2 D1** ; ce plan écrit la file et prouve sa forme, pas plus. Mesure qui le permet : les graphes sont déjà sur disque, `settings.outputs_path / "_graphs" / "<job_id>.json"` (`routes.py:227-240`).

- [ ] **Step 1 : Écrire le banc qui échoue**

Créer `backend/tests/test_sync_recettes.py` :

```python
# -*- coding: utf-8 -*-
"""D4 — les recettes listées, et la file que le PC videra.

    python tests/test_sync_recettes.py          # depuis backend/
"""
import asyncio
import json
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

GRAPHE = {"nodes": [{"id": "n1", "type": "image"},
                    {"id": "n2", "type": "seedance"}],
          "edges": [{"from": "n1", "to": "n2"}]}


def _semer():
    from app.config import settings
    from app.services.storage import init_db
    asyncio.run(init_db())
    d = settings.outputs_path / "_graphs"
    d.mkdir(parents=True, exist_ok=True)
    (d / "job-graphe.json").write_text(json.dumps(GRAPHE), encoding="utf-8")
    (d / "job-vide.json").write_text("pas du json", encoding="utf-8")


def test_les_recettes_lisibles_sont_listees_les_autres_dites():
    from app.services import sync_recettes as SR
    _semer()
    r = SR.lister()
    par_id = {x["job_id"]: x for x in r["recettes"]}
    assert par_id["job-graphe"]["noeuds"] == 2
    assert par_id["job-graphe"]["lisible"] is True
    assert par_id["job-vide"]["lisible"] is False
    assert "json" in par_id["job-vide"]["raison"].lower()


def test_une_mise_en_file_ecrit_une_entree_relisible():
    from app.services import sync_recettes as SR
    _semer()
    e = SR.mettre_en_file("job-graphe", {"image": "mob_1234abcd.png"},
                          "iPhone de Oli")
    file = SR.file()
    assert len(file) == 1
    assert file[0]["id"] == e["id"]
    assert file[0]["job_id"] == "job-graphe"
    assert file[0]["sources"] == {"image": "mob_1234abcd.png"}
    assert file[0]["appareil"] == "iPhone de Oli"
    assert file[0]["etat"] == "en_attente"


def test_une_recette_illisible_ne_se_met_pas_en_file():
    from app.services import sync_recettes as SR
    _semer()
    try:
        SR.mettre_en_file("job-vide", {}, "x")
    except ValueError as e:
        assert "lisible" in str(e)
    else:
        raise AssertionError("un graphe illisible a ete mis en file")


def test_un_job_inconnu_est_refuse():
    from app.services import sync_recettes as SR
    _semer()
    try:
        SR.mettre_en_file("job-qui-nexiste-pas", {}, "x")
    except ValueError as e:
        assert "aucun graphe" in str(e)
    else:
        raise AssertionError("un job inconnu a ete mis en file")


def test_la_file_dit_quelle_attend_le_PC():
    """Honnêteté : ce plan ne LANCE rien, il met en file. R2 D1 exécute."""
    from app.services import sync_recettes as SR
    _semer()
    SR.mettre_en_file("job-graphe", {}, "x")
    assert SR.entete()["execute_par"] == "PC (R2 D1)"
    assert SR.entete()["en_attente"] == 1


TESTS = [test_les_recettes_lisibles_sont_listees_les_autres_dites,
         test_une_mise_en_file_ecrit_une_entree_relisible,
         test_une_recette_illisible_ne_se_met_pas_en_file,
         test_un_job_inconnu_est_refuse,
         test_la_file_dit_quelle_attend_le_PC]

if __name__ == "__main__":
    failed = []
    for t in TESTS:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:  # noqa: BLE001
            failed.append(t.__name__)
            print(f"FAIL {t.__name__}: {e!r}")
    print(f"\n{len(TESTS) - len(failed)}/{len(TESTS)} OK")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2 : Lancer, vérifier l'échec**

Run : `cd backend && python tests/test_sync_recettes.py`
Attendu : cinq `FAIL ... ModuleNotFoundError`, `0/5 OK`.

- [ ] **Step 3 : Écrire le service**

Créer `backend/app/services/sync_recettes.py` :

```python
# -*- coding: utf-8 -*-
"""D4 — les graphes du Studio, listés pour le téléphone, mis en file.

CE QUE CE MODULE NE FAIT PAS : exécuter un graphe. L'exécution d'une
recette sauvegardée appartient à R2 D1. Ici, le téléphone choisit une
recette, donne ses nouvelles sources, et l'entrée attend le PC — l'entête
de la file le DIT (`execute_par`), pour qu'aucun écran ne laisse croire
qu'un rendu est parti.

Mesure qui rend ce module possible : les graphes sont déjà sur disque, à
`outputs/_graphs/<job_id>.json` (routes.py:227-240).
"""
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.config import settings


def _dossier() -> Path:
    return settings.outputs_path / "_graphs"


def _fichier_file() -> Path:
    return settings.outputs_path / "_sync" / "file_recettes.json"


def _lire_graphe(job_id: str) -> dict | None:
    p = _dossier() / f"{Path(job_id).name}.json"
    if not p.is_file():
        return None
    try:
        g = json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return {}
    return g if isinstance(g, dict) else {}


def lister() -> dict:
    """Toutes les recettes sauvegardées. Une recette illisible est
    LISTÉE quand même, avec sa raison : la cacher ferait croire qu'elle
    n'existe pas."""
    out = []
    d = _dossier()
    if d.is_dir():
        for p in sorted(d.glob("*.json")):
            job_id = p.stem
            g = _lire_graphe(job_id)
            noeuds = len((g or {}).get("nodes") or [])
            lisible = bool(g) and noeuds > 0
            out.append({
                "job_id": job_id,
                "noeuds": noeuds,
                "lisible": lisible,
                "raison": "" if lisible else "graphe illisible (json invalide "
                                             "ou sans noeud)",
                "mtime": round(p.stat().st_mtime, 3),
            })
    return {"recettes": out}


def file() -> list[dict]:
    f = _fichier_file()
    if not f.is_file():
        return []
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []


def entete() -> dict:
    entrees = file()
    return {"execute_par": "PC (R2 D1)",
            "en_attente": sum(1 for e in entrees
                              if e.get("etat") == "en_attente"),
            "total": len(entrees)}


def mettre_en_file(job_id: str, sources: dict, appareil: str) -> dict:
    g = _lire_graphe(job_id)
    if g is None:
        raise ValueError(f"aucun graphe sauvegarde pour {job_id!r}")
    if not g or not (g.get("nodes") or []):
        raise ValueError(f"graphe de {job_id!r} non lisible — rien en file")
    entree = {
        "id": str(uuid4()),
        "job_id": job_id,
        "sources": {str(k): str(v) for k, v in (sources or {}).items()},
        "appareil": str(appareil or "telephone")[:60],
        "etat": "en_attente",
        "depose_a": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    }
    entrees = file()
    entrees.append(entree)
    f = _fichier_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(entrees, ensure_ascii=False, indent=1),
                 encoding="utf-8")
    return entree
```

- [ ] **Step 4 : Lancer, vérifier que ça passe**

Run : `cd backend && python tests/test_sync_recettes.py`
Attendu : cinq lignes `PASS`, puis `5/5 OK`.

- [ ] **Step 5 : Ajouter les routes**

À la fin de `backend/app/api/routes.py` :

```python
# ── D4 : recettes lançables depuis le téléphone ─────────────────────────────

@router.get("/sync/recettes")
async def sync_recettes_list():
    from app.services import sync_recettes as _sr
    return {**_sr.lister(), "file": _sr.entete()}


@router.post("/sync/recettes/{job_id}/file")
async def sync_recettes_file(job_id: str, body: dict):
    from app.services import sync_recettes as _sr
    try:
        return _sr.mettre_en_file(job_id, (body or {}).get("sources") or {},
                                  str((body or {}).get("appareil") or ""))
    except ValueError as e:
        raise HTTPException(400, str(e))
```

- [ ] **Step 6 : Fin du lot 3 — tout mesurer**

```bash
cd backend
for f in test_sync_chapitre.py test_sync_recettes.py; do
  echo "=== $f"; python tests/$f | tail -2
done
```
Attendu : `5/5 OK`, `5/5 OK`.

Run : `cd /c/Users/olivi/deepotus-mobile && npm test`
Attendu : `Tests: 49 passed, 49 total`.

Run : `powershell -ExecutionPolicy Bypass -File scripts\run-tests.ps1`
Attendu : aucun fichier dans `failed`.

- [ ] **Step 7 : Commit**

```bash
git add backend/app/services/sync_recettes.py backend/app/api/routes.py backend/tests/test_sync_recettes.py
git commit -m 'recettes : le telephone met en file, le PC executera' -m 'Ce module ne LANCE rien, et lentete de la file le dit noir sur blanc
(execute_par) : lexecution dune recette sauvegardee appartient a R2 D1.
Aucun ecran ne pourra laisser croire quun rendu est parti.

Une recette illisible est LISTEE avec sa raison plutot que cachee — la
cacher ferait croire quelle nexiste pas — mais elle ne peut pas entrer en
file.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Écarté

Repris tel quel de **R12**, avec la mesure qui l'a écarté :

- **E1 — Lecture A (télécommande + Wake-on-LAN)** : R12 réponse 3 dit « le PC est vraiment éteint (portable, déplacements) » — ne pas construire un tunnel pour un PC absent.
- **E2 — Lecture C (relais permanent)** : aucun hôte permanent déclaré (réponse 4), aucun service tiers voulu (réponse 6) ; **Postiz** (vérifié le 03/09) reste une note pour le jour où un hôte existerait.
- **E3 — PWA** : Web Share Target absent d'iOS Safari (vérifié le 03/09 : MDN, web.dev, bugs.webkit.org) et le coffre système hors de portée d'une page web — donc natif.
- **E4 — Fusion automatique des textes** : R12 réponse 14 choisit le verrou, « plus simple et sans surprise » ; la tâche 14 le pose, et la tâche 21 est la seule porte d'écriture.
- **E5 — Effacement à distance des clés** : contredirait « seulement dans mon réseau » (réponse 6) ; à la place, révocation du jeton (tâche 4) **plus** la liste des consoles où faire tourner chaque clé (`appairage.CONSOLES`, tâche 2).

---

## Campagne de mutations

### Tâche 23 : `backend/tests/mutations_appairage.py`

**Files:**
- Create: `backend/tests/mutations_appairage.py`
- Patron : `backend/tests/mutations_plaque_slicer.py`

**Coût :** faible en écriture, **élevé en valeur**. C'est la seule tâche qui mesure la **qualité des bancs** plutôt que celle du code : une mutation « VERTE » est une assertion qui manque. Elle ne couvre que la **partie PC** — le dépôt mobile a sa propre suite jest, hors du périmètre de ce fichier.

**Différence avec le patron, mesurée :** `mutations_plaque_slicer.py` lance `pytest -k` et lit les lignes `FAILED file::nom`. Les bancs de ce plan sont **auto-exécutants** (`python tests/test_x.py`) et impriment `FAIL <nom>: <erreur>`. Le lecteur change ; le reste (mutation vérifiée, remise à l'octet près, troisième état « ERREUR ») est repris tel quel.

- [ ] **Step 1 : Écrire le banc de mutations**

Créer `backend/tests/mutations_appairage.py` :

```python
# -*- coding: utf-8 -*-
"""Banc de mutations du compagnon (partie PC) : casser -> rouge -> remettre.

PAS UN TEST : son nom ne commence pas par `test_`, donc `run-tests.ps1`
ne le liste pas et pytest ne le collecte pas. Il se lance A LA MAIN,
depuis backend/ :

    python tests/mutations_appairage.py            # toutes
    python tests/mutations_appairage.py 3 17       # celles-la

Il MUTE les sources du depot une a une et les REMET a l'octet pres
(assertion sha256), donc il ne se lance pas pendant qu'un autre banc lit
ces fichiers. La liste est l'argument de la revue : chaque mutation nomme
le test qu'elle fait rougir, et une VERTE est une assertion qui manque.

DIFFERENCE AVEC mutations_plaque_slicer.py : les bancs de ce plan sont
auto-executants et impriment `PASS <nom>` / `FAIL <nom>: <erreur>`. On lit
donc ces lignes, et l'on garde le TROISIEME etat : un banc qui n'a rien
imprime du tout n'est pas vert, il est casse (import rompu, syntaxe).
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
PY = sys.executable

# (fichier relatif au depot, ancien, nouveau, banc, tests attendus rouges)
M = [
    # ── appairage.py : le secret et le jeton ────────────────────────────────
    ("backend/app/services/appairage.py",
     "    _SECRETS.pop(secret, None)                  # USAGE UNIQUE",
     "    pass                                        # USAGE UNIQUE",
     "test_appairage.py",
     ["test_un_secret_est_a_usage_unique_et_expire_en_5_minutes"]),
    ("backend/app/services/appairage.py",
     "DUREE_SECRET_S = 300",
     "DUREE_SECRET_S = 3000",
     "test_appairage.py",
     ["test_un_secret_est_a_usage_unique_et_expire_en_5_minutes"]),
    ("backend/app/services/appairage.py",
     "    if fiche[\"expire_a\"] < time.time():",
     "    if False:",
     "test_appairage.py",
     ["test_le_secret_expire_se_refuse_en_le_disant"]),
    ("backend/app/services/appairage.py",
     "            jeton_sha256=hashlib.sha256(jeton.encode()).hexdigest(),",
     "            jeton_sha256=jeton,",
     "test_appairage.py",
     ["test_le_jeton_nest_jamais_stocke_en_clair"]),
    ("backend/app/services/appairage.py",
     "MAX_APPAREILS = 5",
     "MAX_APPAREILS = 50",
     "test_appairage.py",
     ["test_cinq_appareils_au_plus"]),
    ("backend/app/services/appairage.py",
     "    invalider_cache()\n    return r.rowcount > 0",
     "    return r.rowcount > 0",
     "test_appairage.py",
     ["test_la_revocation_est_immediate_pour_la_garde"]),
    ("backend/app/services/appairage.py",
     "        _select(Device.jeton_sha256).where(Device.revoque.is_(None)))",
     "        _select(Device.jeton_sha256))",
     "test_appairage.py",
     ["test_la_revocation_est_immediate_pour_la_garde"]),
    # ── main.py : la garde de jeton ─────────────────────────────────────────
    ("backend/app/main.py",
     "    if not await _appairage.jeton_valide(jeton):",
     "    if False:",
     "test_appairage_routes.py",
     ["test_le_lan_sans_jeton_est_refuse_sur_une_route_de_lecture",
      "test_le_lan_sans_jeton_est_refuse_sur_le_frontend_aussi",
      "test_un_jeton_revoque_ne_passe_plus_tout_de_suite",
      "test_les_routes_dappairage_sont_reservees_au_loopback"]),
    ("backend/app/main.py",
     "    jeton = entete[7:].strip() if entete[:7].lower() == \"bearer \" else \"\"",
     "    jeton = entete.strip()",
     "test_appairage_routes.py",
     ["test_le_lan_avec_un_jeton_valide_passe"]),
    ("backend/app/main.py",
     "_ROUTES_SANS_JETON = {\"/api/pair/claim\"}",
     "_ROUTES_SANS_JETON = {\"/api/pair/claim\", \"/api/jobs\"}",
     "test_appairage_routes.py",
     ["test_le_lan_sans_jeton_est_refuse_sur_une_route_de_lecture"]),
    ("backend/app/main.py",
     "_LOOPBACK_HOSTS = {\"127.0.0.1\", \"::1\", \"localhost\", \"testclient\"}",
     "_LOOPBACK_HOSTS = {\"127.0.0.1\", \"::1\", \"localhost\", \"testclient\", \"192.168.1.42\"}",
     "test_appairage_routes.py",
     ["test_le_lan_sans_jeton_est_refuse_sur_une_route_de_lecture"]),
    # ── qrcode_min.py : la trame ────────────────────────────────────────────
    ("backend/app/services/qrcode_min.py",
     "    if len(charge) > CAPACITE_OCTETS:",
     "    if False:",
     "test_qrcode_min.py",
     ["test_au_dela_de_78_octets_le_refus_est_nomme"]),
    ("backend/app/services/qrcode_min.py",
     "    flux = list(donnees) + _correction(donnees, MOTS_CORRECTION)",
     "    flux = list(donnees) + [0] * MOTS_CORRECTION",
     "test_qrcode_min.py",
     ["test_le_decodeur_independant_relit_lurl"]),
    ("backend/app/services/qrcode_min.py",
     "        m[6][i] = i % 2 == 0\n        m[i][6] = i % 2 == 0",
     "        m[6][i] = i % 2 == 1\n        m[i][6] = i % 2 == 1",
     "test_qrcode_min.py",
     ["test_la_matrice_a_la_bonne_forme"]),
    ("backend/app/services/qrcode_min.py",
     "    bits15 = ((val << 10) | reste) ^ 0b101010000010010",
     "    bits15 = (val << 10) | reste",
     "test_qrcode_min.py",
     ["test_le_decodeur_independant_relit_lurl"]),
    # ── sync_lot.py : le lot et le dernier mot du PC ────────────────────────
    ("backend/app/services/sync_lot.py",
     "            if p.status == \"posted\":",
     "            if False:",
     "test_sync_lot.py",
     ["test_un_post_deja_publie_par_le_PC_nest_pas_ecrase"]),
    ("backend/app/services/sync_lot.py",
     "            .where(ScheduledPost.run_at <= limite)",
     "            .where(ScheduledPost.run_at <= limite.replace(year=2099))",
     "test_sync_lot.py",
     ["test_le_lot_ne_prend_que_la_fenetre_demandee"]),
    ("backend/app/services/sync_lot.py",
     "                             \"sha256\": _sha256(chemin),",
     "                             \"sha256\": \"\",",
     "test_sync_lot.py",
     ["test_le_post_porte_sa_video_son_poids_et_son_empreinte"]),
    ("backend/app/services/sync_lot.py",
     "                p.status = \"ready\"\n                p.error = f\"echec sur {appareil}: {detail}\"[:500]",
     "                p.status = \"failed\"\n                p.error = f\"echec sur {appareil}: {detail}\"[:500]",
     "test_sync_lot.py",
     ["test_un_echec_du_telephone_revient_en_ready_avec_sa_raison"]),
    # ── sync_transfert.py : le depot verifie ────────────────────────────────
    ("backend/app/services/sync_transfert.py",
     "    if reel != (sha256 or \"\").lower():",
     "    if False:",
     "test_sync_transfert.py",
     ["test_une_empreinte_fausse_refuse_et_ne_laisse_rien"]),
    ("backend/app/services/sync_transfert.py",
     "    if \"/\" in brut or \"\\\\\" in brut or \":\" in brut:",
     "    if False:",
     "test_sync_transfert.py",
     ["test_un_nom_qui_sort_du_magasin_est_refuse"]),
    ("backend/app/services/sync_transfert.py",
     "    final = _libre(dossier, nom)",
     "    final = nom",
     "test_sync_transfert.py",
     ["test_un_second_depot_du_meme_nom_ne_perd_pas_lancien"]),
    ("backend/app/services/sync_transfert.py",
     "    await LI.noter([final], \"mobile\", kind=\"image\")",
     "    await LI.noter([final], \"import\", kind=\"image\")",
     "test_sync_transfert.py",
     ["test_le_depot_est_indexe_avec_la_source_mobile"]),
    # ── sync_verrou.py + la garde de PUT /chapters ──────────────────────────
    ("backend/app/api/routes.py",
     "    _verrou = await _sv.qui(chapter_id)\n    if _verrou:",
     "    _verrou = await _sv.qui(chapter_id)\n    if False:",
     "test_sync_verrou.py",
     ["test_un_chapitre_emporte_refuse_lecriture_du_pc_en_le_disant",
      "test_un_autre_appareil_ne_peut_pas_liberer",
      "test_le_journal_garde_la_trace_des_conflits"]),
    ("backend/app/services/sync_verrou.py",
     "        if v is None or v.device_id != device_id:",
     "        if v is None:",
     "test_sync_verrou.py",
     ["test_un_autre_appareil_ne_peut_pas_liberer"]),
    ("backend/app/services/sync_verrou.py",
     "            if deja.device_id == device_id:\n                return {\"pris\": True, \"par\": deja.device_nom, \"deja\": True}\n            return {\"pris\": False, \"par\": deja.device_nom,\n                    \"depuis\": deja.pris_le.isoformat()}",
     "            return {\"pris\": True, \"par\": deja.device_nom, \"deja\": True}",
     "test_sync_verrou.py",
     ["test_deux_appareils_ne_prennent_pas_le_meme_chapitre"]),
    # ── mdns.py : la trame annoncee ─────────────────────────────────────────
    ("backend/app/services/mdns.py",
     "            if nom.lower() == SERVICE and qtype in (12, 255):",
     "            if qtype in (12, 255):",
     "test_mdns.py",
     ["test_une_question_sur_un_autre_service_reste_sans_reponse"]),
    ("backend/app/services/mdns.py",
     "        + _enregistrement(HOTE, 1, socket.inet_aton(adresse))           # A",
     "        + _enregistrement(HOTE, 1, socket.inet_aton(\"127.0.0.1\"))       # A",
     "test_mdns.py",
     ["test_ladresse_annoncee_est_celle_quon_lui_donne"]),
    ("backend/app/services/mdns.py",
     "        if len(paquet) < 12:",
     "        if False:",
     "test_mdns.py",
     ["test_un_paquet_tronque_ne_leve_pas"]),
    ("backend/app/services/mdns.py",
     "    for entree in (\"protocole=1\", f\"port={port}\"):",
     "    for entree in (f\"port={port}\",):",
     "test_mdns.py",
     ["test_le_txt_dit_la_version_du_protocole"]),
    # ── sync_depenses.py : la fusion ────────────────────────────────────────
    ("backend/app/services/sync_depenses.py",
     "    if not _JOUR.match(jour):",
     "    if False:",
     "test_sync_depenses.py",
     ["test_un_resume_malforme_est_refuse_en_le_disant"]),
    ("backend/app/services/sync_depenses.py",
     "    tout.setdefault(jour, {})[str(appareil or \"telephone\")[:60]] = {",
     "    tout.setdefault(jour, {})[\"tous\"] = {",
     "test_sync_depenses.py",
     ["test_deux_appareils_du_meme_jour_sadditionnent_au_total"]),
    # ── sync_recettes.py : la file honnete ──────────────────────────────────
    ("backend/app/services/sync_recettes.py",
     "    if not g or not (g.get(\"nodes\") or []):",
     "    if False:",
     "test_sync_recettes.py",
     ["test_une_recette_illisible_ne_se_met_pas_en_file"]),
    ("backend/app/services/sync_recettes.py",
     "    return {\"execute_par\": \"PC (R2 D1)\",",
     "    return {\"execute_par\": \"telephone\",",
     "test_sync_recettes.py",
     ["test_la_file_dit_quelle_attend_le_PC"]),
]


def rouges(banc):
    """Les tests rouges du banc auto-executant, et le TROISIEME etat.

    Un banc de ce plan imprime `PASS <nom>` et `FAIL <nom>: <erreur>`, puis
    `N/M OK`. Une mutation peut casser l'IMPORT du module : le banc sort
    alors sans imprimer une seule ligne PASS/FAIL. Lu comme « aucun FAIL »,
    cela passerait pour une mutation VERTE alors que RIEN n'a ete mesure.
    On rend donc explicitement cet etat d'erreur.
    """
    p = subprocess.run([PY, f"tests/{banc}"], capture_output=True,
                       cwd=R / "backend", timeout=900)
    txt = (p.stdout + p.stderr).decode("utf-8", "replace")
    echecs = set(re.findall(r"^FAIL (\w+):", txt, re.M))
    passes = set(re.findall(r"^PASS (\w+)$", txt, re.M))
    erreur = (not echecs and not passes) or "Traceback" in txt and not passes
    return echecs, txt, erreur


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
        assert txt.count(old) == 1, (i, rel, txt.count(old), old[:60])
        txt = txt.replace(old, new)
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
            verdict = "ERREUR(import)"
            print(sortie[-1200:], file=sys.stderr)
        elif not manquants:
            verdict = "ROUGE"
        elif rg:
            verdict = "ROUGE(autres)"
        else:
            verdict = "VERTE"
        bilan.append((i, rel, banc, verdict, sorted(rg), manquants))
        apercu = old.strip()[:46]
        print(f"[{i:2d}] {verdict:14s} {banc:26s} {apercu!r} -> {sorted(rg)}"
              f"  sha {sha_avant[:10]}={sha_apres[:10]}")
        sys.stdout.flush()
    verts = [b for b in bilan if b[3] == "VERTE"]
    casses = [b for b in bilan if b[3].startswith("ERREUR")]
    print(f"\n{len(bilan)} mutation(s) : "
          f"{len(bilan) - len(verts) - len(casses)} ROUGE, "
          f"{len(verts)} VERTE, {len(casses)} ERREUR")
    if verts:
        print("VERTES (assertions manquantes) :")
        for b in verts:
            print(f"  [{b[0]}] {b[1]} — banc {b[2]}, attendait {b[5]}")
    print(json.dumps([b[:4] for b in bilan], ensure_ascii=False))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
```

- [ ] **Step 2 : Lancer la campagne entière**

Run : `cd backend && python tests/mutations_appairage.py`
Attendu : 34 lignes, chacune `ROUGE`, et la dernière ligne de bilan `34 mutation(s) : 34 ROUGE, 0 VERTE, 0 ERREUR`.

- [ ] **Step 3 : Traiter chaque VERTE**

Une mutation **VERTE** signifie qu'un comportement décrit dans le plan n'est mesuré par aucune assertion. Pour chacune : **ajouter l'assertion manquante** au banc nommé, relancer cette mutation seule (`python tests/mutations_appairage.py <n>`), vérifier qu'elle est passée `ROUGE`. Ne jamais supprimer la mutation pour faire disparaître le vert.

Une mutation **ERREUR(import)** signifie que la mutation casse le fichier au point que le banc ne démarre plus : reformuler la mutation pour qu'elle reste du Python valide.

- [ ] **Step 4 : Vérifier que le dépôt est intact**

```bash
git status --porcelain backend/app
```
Attendu : **aucune ligne** — le banc remet chaque fichier à l'octet près et l'assertion sha256 le prouve à chaque mutation.

- [ ] **Step 5 : Relancer toute la suite**

Run : `powershell -ExecutionPolicy Bypass -File scripts\run-tests.ps1`
Attendu : aucun fichier dans `failed`.

- [ ] **Step 6 : Commit**

```bash
git add backend/tests/mutations_appairage.py
git commit -m 'mutations : 34 coupures qui doivent rougir, et le troisieme etat' -m 'La campagne mesure les BANCS, pas le code : chaque mutation nomme le test
quelle doit faire rougir, et une VERTE est une assertion qui manque.

Difference mesuree avec le patron de la plaque : les bancs de ce plan sont
auto-executants et impriment PASS/FAIL, la ou pytest imprime FAILED. Le
troisieme etat est garde et adapte : un banc qui nimprime RIEN a un import
casse, pas un code sain — le lire comme aucun FAIL en ferait une fausse
verte.

Chaque fichier est remis a loctet pres, et lassertion sha256 le prouve a
chaque mutation.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>'
```

---

## Relecture finale

Trois corrections apportées **après** la première rédaction, faites en ligne dans les tâches concernées plutôt que listées ici comme des dettes :

1. **Fuseau horaire du manifeste incrémental (tâche 12)** — `datetime.fromisoformat(depuis).timestamp()` interprète une date naïve comme **locale**, alors que `genere_a` est en UTC : sur une machine en UTC+2, le seuil reculait de deux heures et le mode incrémental renvoyait tout. Corrigé par `.replace(tzinfo=timezone.utc)`, et le banc a été rendu déterministe (deux attentes encadrant l'instant de référence) au lieu de dépendre de la troncature à la seconde.
2. **Semences non idempotentes (tâches 8 et 17)** — un `_semer()` appelé par plusieurs tests du même processus réinsérait les mêmes clés primaires et cassait à la deuxième contrainte `UNIQUE`. Les deux semences vident désormais leurs tables avant d'écrire.
3. **Assertion dépendante de l'ordre (tâche 12)** — le test du poids total comparait à une constante que le test incrémental, exécuté avant lui, invalidait en créant un fichier de plus. Il compare maintenant le poids annoncé à la **somme de l'index rendu**, ce qui mesure la même chose sans dépendre de l'ordre.

Trois faits ont par ailleurs été **vérifiés dans le dépôt** au lieu d'être supposés, et les étapes correspondantes ont été simplifiées : `Form` et `APP_VERSION` sont déjà importés en tête de `routes.py` (lignes 13 et 18), et la route `/health` existe (`routes.py:3460`).

## Handoff

Plan complet, enregistré dans `docs/superpowers/plans/2026-09-03-plan-mobile.md`. Deux façons de l'exécuter :

1. **Par sous-agents (recommandé)** — un sous-agent neuf par tâche, revue entre chaque : `superpowers:subagent-driven-development`.
2. **En ligne** — exécution par lots avec points de contrôle : `superpowers:executing-plans`.

**Avant de lancer le lot 1, une question à trancher hors de ce plan** : R11 D1 doit dire si l'archive chiffrée utilise une bibliothèque AES embarquée ou DPAPI. **DPAPI rendrait la tâche 7 impossible** (clé liée au compte Windows, illisible par un téléphone) et bloquerait P2 tout entier.
