#!/usr/bin/env bash
# Sur le PC (Git Bash) : envoie le code du site (dépôt deepotus-site, HEAD commité) sur le VPS et (re)démarre l'API et
# GoatCounter. Une seule connexion SSH (une seule phrase de passe). Le VPS n'a donc besoin d'aucun accès au dépôt privé.
#   bash deploiement/vps/publier-api.sh [dossier site-vitrine] [branche de /opt/deepotus, défaut main]
set -euo pipefail
SITE="${1:-$HOME/DeepotusVideo/site-vitrine}"
BRANCHE="${2:-main}"
HOTE="${HOTE:-deepotus-vps}"
ICI="$(cd "$(dirname "$0")" && pwd)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
git -C "$SITE" archive --format=tar -o "$tmp/site.tar" HEAD
echo "site : $(git -C "$SITE" log --oneline -1)"
cp "$ICI/installer-api.sh" "$tmp/"
tar -C "$tmp" -cf - site.tar installer-api.sh \
  | ssh "$HOTE" "d=\$(mktemp -d) && tar -x -C \"\$d\" && bash \"\$d/installer-api.sh\" \"\$d/site.tar\" '$BRANCHE'; s=\$?; rm -rf \"\$d\"; exit \$s"
