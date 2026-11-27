# Couche hébergée sur le VPS (t530-t535) — plan d'exécution

20/11/2026. Conception : artefact « Deepotus sur le VPS » (https://claude.ai/artifact/TbcNEnNMHD56G1E1napFuT, 30/10).
Découpage validé par l'utilisateur le 20/11 : six PR dans l'ordre ci-dessous ; l'image est vérifiée par GitHub Actions
(le PC n'a ni Docker ni WSL) ; nom public **studio.deepotus.tech** ; VPS Hostinger **KVM 2**, Ubuntu 24.04 avec Docker,
déjà en service. Phase 1 : l'utilisateur seul, un mot de passe Caddy devant la porte.

## Décision d'architecture ajoutée au relevé du 30/10 : réseau de l'hôte

Les gardes du backend (`_garde_ecritures_locales`, `_device_token_guard`, Réglages) exigent que `request.client.host`
soit la boucle locale. Un port publié par Docker (`127.0.0.1:8765:8765`) arrive dans le conteneur depuis la passerelle
du pont (172.x.0.1) : toutes les écritures seraient refusées en 403. Le compose met donc **deepotus et caddy en
`network_mode: host`**, uvicorn écoute **127.0.0.1:8765** (jamais 0.0.0.0), et ufw n'ouvre pas 8765. Uvicorn tourne
avec `--no-proxy-headers` : sinon il remplacerait l'adresse cliente par `X-Forwarded-For` que Caddy envoie depuis
127.0.0.1 (en plus du `header_up -X-Forwarded-For` du Caddyfile). Conséquence assumée : le mot de passe de Caddy est la
seule serrure de la phase 1.

## Pièces (une branche `claude/hebergee-<pièce>` et une PR chacune, bancs d'abord)

### ① t530 — nom d'hôte public
- `config.py` : `APP_HOSTNAME` lu dans `DEEPOTUS_HOSTNAME` (nettoyé : minuscules, sans port ni schéma, refus des
  caractères hors nom DNS → repli sur `deepotus.localhost` avec un avertissement) ; `APP_HOSTNAME_LOCAL` reste
  `deepotus.localhost` ; `app_url()` inchangée sous Windows.
- `main.py` : `_ALLOWED_ORIGIN_HOSTS` contient les deux noms.
- `live_routes._origine_sure` : l'en-tête Host accepte aussi le nom public (avec ou sans port) ; l'adresse cliente
  reste exigée locale.
- Banc `backend/tests/test_hebergee_hote_t530.py` : défaut inchangé ; variable posée → POST avec Origin du domaine
  accepté, autre domaine refusé ; WebSocket du direct accepté avec Host public, refusé avec un Host étranger ; valeur
  invalide → repli.

### ② t531 — image et déploiement
- `Dockerfile` (racine) : `python:3.13-slim`, `ffmpeg`, `chromium`, polices, `pip install -r backend/requirements.txt`
  (+ paquets importés par l'app mais absents du fichier, relevés à la construction), `frontend/dist` copié, utilisateur
  sans privilèges, `DEEPOTUS_DATA_DIR=/data`, `DEEPOTUS_NAVIGATEUR=/usr/bin/chromium`,
  `CMD uvicorn app.main:app --host 127.0.0.1 --port 8765 --no-proxy-headers` (sans `--reload`), `HEALTHCHECK` sur
  `/api/health`. `.dockerignore`.
- `deploiement/vps/docker-compose.yml` (caddy + deepotus en réseau hôte, sftp atmoz sur 2222, volumes
  `/srv/deepotus/data:/data`, `/srv/deepotus/depot:/depot:ro`), `deploiement/vps/Caddyfile.exemple` (`basic_auth`,
  `header_up -X-Forwarded-For` et `-X-Real-IP`, corps 8 Go, délais 30 min), `deploiement/vps/.env.exemple`,
  `deploiement/vps/README.md` (pas à pas).
- `.github/workflows/image-vps.yml` : construit l'image à chaque PR touchant le backend ou le déploiement, la démarre,
  attend `/api/health`, vérifie qu'un POST d'Origin `https://studio.deepotus.tech` passe la garde CSRF. Rien n'est
  publié.
- Banc `backend/tests/test_hebergee_image_t531.py` : lit les fichiers et vérifie les invariants (pas de `--reload`,
  écoute 127.0.0.1, `--no-proxy-headers`, en-têtes retirés dans le Caddyfile, 8765 jamais publié hors boucle locale,
  dépôt monté en lecture seule, chaque module importé par `app` résolu par requirements).

### ③ t532 — coffre retenu par fichier de clé
- `services/coffre.py` : quand DPAPI est absent (non-Windows) et `DEEPOTUS_COFFRE_CLE_FICHIER` posé, « retenir »
  écrit la clé du coffre dans ce fichier (création 0600, refus si le fichier est lisible par le groupe ou les autres),
  et le démarrage déverrouille par lui. Format DZKV1 inchangé ; sous Windows, DPAPI reste la seule voie.
- Banc `test_coffre_fichier_t532.py` (simule l'absence de DPAPI) : aller-retour, permissions refusées, fichier absent
  = coffre verrouillé sans exception, oubli efface le fichier.

### ④ t533 — emplacements sous Linux
- `verifier_dossier` : chemin POSIX absolu accepté hors Windows (PureWindowsPath conservé sous Windows) ; même règle
  pour `cle_ssh`.
- SFTP : sans secret, aucun `askpass.cmd` ; avec secret hors Windows, `askpass` en script shell 0700, ou refus
  i18n clair (à trancher au moment du banc selon `lancer_sftp`).
- Banc `test_emplacements_linux_t533.py` (plate-forme simulée).

### ⑤ t534 — rappels OAuth
- `youtube_publisher.redirect_uri()` / `tiktok_publisher.redirect_uri()` : `https://<DEEPOTUS_HOSTNAME>/api/oauth/…`
  quand le nom public n'est pas un `.localhost` ; sinon l'URL loopback actuelle, octet pour octet.
- Banc `test_oauth_rappel_t534.py` + guide FR/EN des consoles Google et TikTok (type d'application web).

### ⑥ t535 — outils Windows seulement
- Relevé : photocraft, scan OCR (Windows.Media.Ocr), installeur CLIP (roues win_amd64), Blender MCP (`.exe`),
  `print3d.py` (`os.startfile`), `cards/edition.py` (`SHGetKnownFolderPath`), et tout autre `ctypes.windll` /
  `winreg` / `os.startfile` atteint au démarrage ou par une route.
- Chacun répond un diagnostic i18n (« disponible sur l'app Windows ») et n'est jamais importé au démarrage.
- Banc `test_hebergee_windows_seul_t535.py` : import de `app.main` avec une plate-forme simulée Linux sans exception,
  routes concernées → refus 501 traduit.

## Partie serveur (après fusion)
Guidage pas à pas, chaque commande lancée par l'utilisateur : clé SSH, ufw 22/80/443/2222, fail2ban, enregistrement A
`studio.deepotus.tech`, `/srv/deepotus/{data,depot}`, `docker compose up -d --build`, coffre posé, emplacement SFTP
côté PC (rôles miroir + sauvegarde) et `/depot` en source de bibliothèque côté serveur, sauvegarde restic → B2/R2 et
restauration à blanc, recette Mac / PC / iPhone.

## Fini quand
Six PR fusionnées, bancs verts sous Windows, image construite par la CI, https://studio.deepotus.tech répond derrière
Caddy avec le mot de passe, une génération test comptée dans Dépenses, un fichier envoyé du PC visible dans la
Bibliothèque hébergée.

Hors périmètre : le compagnon mobile (`deepotus-mobile`, http en dur dans `src/lib/pc.ts`), chantier séparé.
