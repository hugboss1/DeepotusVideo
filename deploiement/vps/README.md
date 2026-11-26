# Deepotus VideoGen sur le VPS — pas à pas (t531)

Plan : `docs/superpowers/plans/2026-11-20-couche-hebergee-vps.md`. VPS Hostinger KVM 2, Ubuntu 24.04 avec Docker.
Nom public : `studio.deepotus.tech`. Phase 1 : toi seul, un mot de passe devant la porte.

```
navigateur ──https──▶ Caddy (80/443, mot de passe) ──▶ 127.0.0.1:8765 Deepotus (conteneur, réseau de l'hôte)
PC Windows ──sftp (clé, port 2222)──▶ /srv/deepotus/depot ──(lecture seule)──▶ /depot = source de bibliothèque
```

Toutes les commandes se tapent **sur le VPS**, connecté en SSH, sauf mention « sur le PC ».

## 1. Accès SSH par clé

Sur le PC (PowerShell), une clé pour administrer le VPS :

```
ssh-keygen -t ed25519 -f $HOME\.ssh\vps_deepotus -C "admin vps"
type $HOME\.ssh\vps_deepotus.pub
```

Colle la ligne `.pub` dans hPanel › VPS › Paramètres › Clés SSH, puis `ssh -i $HOME\.ssh\vps_deepotus root@<IP>`.
Une fois la connexion par clé vérifiée, désactive le mot de passe :

```
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh
```

## 2. Pare-feu, fail2ban, mises à jour

```
apt update && apt install -y ufw fail2ban unattended-upgrades
ufw default deny incoming
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 2222/tcp
ufw enable
systemctl enable --now fail2ban
```

8765 n'est **jamais** ouvert : Deepotus n'écoute que la boucle locale. Attention : Docker contourne ufw pour les ports
qu'il publie ; seul le SFTP (2222) en publie un, et il doit être ouvert de toute façon.

## 3. DNS

Zone DNS de deepotus.tech (hPanel › Domaines › DNS) : enregistrement **A** `studio` → IP du VPS, TTL 300. Le site
vitrine (apex et `www`) ne bouge pas. Vérifier : `getent hosts studio.deepotus.tech`.

## 4. Dossiers et code

```
mkdir -p /srv/deepotus/data /srv/deepotus/depot /srv/deepotus/secrets
chown -R 1000:1000 /srv/deepotus
chmod 700 /srv/deepotus/secrets
git clone https://github.com/hugboss1/DeepotusVideo.git /opt/deepotus
cd /opt/deepotus/deploiement/vps
cp .env.exemple .env
cp Caddyfile.exemple Caddyfile
```

`data` = base, bibliothèque, coffre (sauvegardé) ; `depot` = ce que le PC envoie ; `secrets` = la clé du coffre
retenu (t532), **hors** de la sauvegarde.

## 5. Mot de passe de Caddy

```
docker run --rm caddy:2 caddy hash-password --plaintext 'une phrase longue et unique'
```

Remplace `REMPLACER_PAR_LE_HASH_BCRYPT` dans `Caddyfile` par la ligne obtenue (elle commence par `$2a$`). Le mot de
passe est la seule serrure : derrière Caddy, le backend croit toutes les requêtes locales.

## 6. SFTP du dépôt

Sur le PC, une clé **dédiée** au dépôt (sans phrase : l'app l'utilise seule) :

```
ssh-keygen -t ed25519 -f $HOME\.ssh\deepotus_depot -N '""' -C "depot deepotus"
```

Sur le VPS, copie le contenu de `deepotus_depot.pub` dans `cles/pc.pub`, puis crée la clé d'hôte une fois pour toutes
(sinon elle change à chaque redémarrage du conteneur) :

```
mkdir -p cles
nano cles/pc.pub
ssh-keygen -t ed25519 -f cles/ssh_host_ed25519_key -N ''
```

## 7. Démarrer

```
docker compose up -d --build
docker compose ps
docker compose logs -f deepotus
```

La première construction prend quelques minutes. Ensuite : `https://studio.deepotus.tech`, mot de passe, et l'app
s'ouvre vide (aucune donnée du PC n'est importée).

## 8. Dans l'app hébergée

- Réglages › Coffre : poser la phrase du coffre, cocher « retenir » (fichier `/secrets/coffre.cle`, t532).
- Réglages › Clés : saisir les clés des fournisseurs ; Réglages › Dépenses : fixer les plafonds.
- Réglages › Chemins : un emplacement de type dossier `/depot` avec le rôle **bibliothèque**.

## 9. Sur le PC

Réglages › Chemins › Ajouter : type SFTP, hôte `studio.deepotus.tech`, port `2222`, utilisateur `depot`, dossier
distant `/upload`, clé `C:\Users\<toi>\.ssh\deepotus_depot`, rôles **miroir** et **sauvegarde**. « Tester ».

## 10. Mettre à jour

```
cd /opt/deepotus && git pull && cd deploiement/vps && docker compose up -d --build
```

## 11. Sauvegarde

Chaque nuit, `restic` vers un bucket B2 ou R2 : `/srv/deepotus/data` et `/srv/deepotus/depot` (jamais `secrets`),
30 jours gardés, et une restauration à blanc testée une fois. Détail fourni au moment de la mise en service.

## 12. Site deepotus.tech : API, e-mails, téléchargements, mesure d'audience (26/11/2026)

Le site reste sur l'hébergement web Hostinger ; le VPS sert ce qui est dynamique, dans le même Compose et le même Caddy :

```
deepotus.tech (Hostinger) ──fetch──▶ api.deepotus.tech ──▶ Caddy ──▶ 127.0.0.1:8787 api (node, site-fusion/server/attente.mjs)
Stripe ──webhook signé──▶ api.deepotus.tech/api/stripe/webhook          └─▶ Brevo (e-mails)   /srv/deepotus/api (SQLite)
toutes les pages ──pixel──▶ stats.deepotus.tech ──▶ Caddy ──▶ 127.0.0.1:8081 goatcounter      /srv/deepotus/stats (SQLite)
```

1. DNS : enregistrements **A** `api` et `stats` → IP du VPS.
2. Sur le PC (Git Bash), une seule connexion SSH : `bash deploiement/vps/publier-api.sh ~/DeepotusVideo/site-vitrine`.
   Le script envoie le code commité du site (`git archive`) dans `/opt/deepotus-site` (le VPS n'a aucun accès au dépôt
   privé), crée les dossiers et `/srv/deepotus/secrets/api.env` depuis `api.env.exemple` (clés `ATTENTE_*` générées),
   ajoute les blocs `api` et `stats` au `Caddyfile`, puis démarre `goatcounter` et `api`.
3. Compléter `/srv/deepotus/secrets/api.env` (Brevo, Stripe), puis relancer le même script.
4. Mettre à jour l'API après un commit du site : relancer le même script.
5. Compte GoatCounter (une fois) : `docker compose run --rm goatcounter db create site -vhost stats.deepotus.tech -user.email TOI@… -db sqlite+/data/goatcounter.sqlite3`
   (le mot de passe est demandé). Réglages › Données : conservation 395 jours.
6. Stripe › Développeurs › Webhooks : point de terminaison `https://api.deepotus.tech/api/stripe/webhook`, événements
   `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `charge.refunded` ; son secret `whsec_…` dans
   `STRIPE_WEBHOOK_SECRET` (et celui du mode test dans `STRIPE_WEBHOOK_SECRET_TEST`).
7. Installeur : `scp VideoGen-Setup.exe deepotus-vps:/srv/deepotus/telechargements/` (nom = `TELECHARGEMENT_FICHIER`).

