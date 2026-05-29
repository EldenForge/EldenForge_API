#!/usr/bin/env bash
# Déploiement de l'API EldenForge sur le VPS.
# Appelé par GitHub Actions (workflow deploy.yml) via SSH.
# Usage : deploy.sh <prod|recette>
set -euo pipefail

ENV="${1:?usage: deploy.sh <prod|recette>}"
if [ "$ENV" = "prod" ]; then
  DIR=/opt/eldenforge
  BRANCH=main
  SVC=eldenforge-api
elif [ "$ENV" = "recette" ]; then
  DIR=/opt/eldenforge-recette
  BRANCH=recette
  SVC=eldenforge-api-recette
else
  echo "env inconnu: $ENV (attendu: prod|recette)" >&2
  exit 1
fi

cd "$DIR/EldenForge_API"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"
.venv/bin/pip install -q -r requirements.txt
.venv/bin/alembic upgrade head
sudo systemctl restart "$SVC"
echo "API ($ENV) déployée depuis origin/$BRANCH."
