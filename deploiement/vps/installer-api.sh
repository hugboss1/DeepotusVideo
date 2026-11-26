#!/usr/bin/env bash
# Sur le VPS, lancé par publier-api.sh : met le code du site dans /opt/deepotus-site, prépare dossiers et secrets,
# ajoute les blocs api/stats au Caddyfile s'ils manquent, puis démarre goatcounter et l'api. Idempotent.
set -euo pipefail
TAR="$1"; BRANCHE="${2:-main}"
CIBLE=/opt/deepotus-site; ENV=/srv/deepotus/secrets/api.env; VPS=/opt/deepotus/deploiement/vps

git -C /opt/deepotus fetch -q origin "$BRANCHE"
git -C /opt/deepotus checkout -q "$BRANCHE" && git -C /opt/deepotus merge -q --ff-only "origin/$BRANCHE"
echo "deepotus : $(git -C /opt/deepotus log --oneline -1)"

rm -rf "$CIBLE.neuf"; mkdir -p "$CIBLE.neuf"; tar -x -C "$CIBLE.neuf" -f "$TAR"
rm -rf "$CIBLE.ancien"; if [ -d "$CIBLE" ]; then mv "$CIBLE" "$CIBLE.ancien"; fi; mv "$CIBLE.neuf" "$CIBLE"

mkdir -p /srv/deepotus/api /srv/deepotus/stats /srv/deepotus/telechargements /srv/deepotus/secrets
chown 1000:1000 /srv/deepotus/api /srv/deepotus/stats /srv/deepotus/telechargements
if [ ! -f "$ENV" ]; then install -m 600 "$VPS/api.env.exemple" "$ENV"; echo "secrets : $ENV créé depuis le modèle"; fi
for v in ATTENTE_SECRET ATTENTE_CLE_CHIFFREMENT; do
  if grep -q "^$v=$" "$ENV"; then sed -i "s/^$v=$/$v=$(openssl rand -hex 32)/" "$ENV"; echo "secrets : $v généré"; fi
done

cd "$VPS"
if ! grep -q '^api\.deepotus\.tech' Caddyfile; then sed -n '/^# Site deepotus.tech (26\/11/,$p' Caddyfile.exemple >> Caddyfile; echo "Caddyfile : blocs api et stats ajoutés"; fi
docker run --rm --env-file .env -v "$PWD/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2 caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile 2>&1 | tail -1

docker compose up -d --build goatcounter
if grep -q '^BREVO_API_KEY=.\+' "$ENV" && grep -q '^ATTENTE_EXPEDITEUR=.\+' "$ENV"; then
  docker compose up -d --force-recreate api
else
  echo "api : NON démarrée, BREVO_API_KEY ou ATTENTE_EXPEDITEUR vide dans $ENV"
fi
docker compose exec -T caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
sleep 3
docker compose ps --format '{{.Service}} {{.State}} {{.Status}}'
docker compose logs --tail 15 api 2>/dev/null || true
echo "api/defi : $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8787/api/attente/defi) · stats : $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8081/)"
