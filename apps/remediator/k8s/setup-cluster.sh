#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
ENV_FILE="${ROOT}/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Fichier .env introuvable à la racine du repo." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${GITHUB_TOKEN_REPO:?GITHUB_TOKEN_REPO manquant dans .env}"
: "${GHCR_PULL_TOKEN:?GHCR_PULL_TOKEN manquant dans .env}"
: "${OVH_AI_TOKEN:?OVH_AI_TOKEN manquant dans .env}"
: "${KUBECONFIG:?KUBECONFIG manquant dans .env}"

OVH_AI_BASE_URL="${OVH_AI_BASE_URL:-https://oai.endpoints.kepler.ai.cloud.ovh.net/v1}"
OVH_AI_MODEL="${OVH_AI_MODEL:-Qwen3-Coder-30B-A3B-Instruct}"

kubectl create secret generic remediator-secrets \
  -n remediator \
  --from-literal=GITHUB_TOKEN="$GITHUB_TOKEN_REPO" \
  --from-literal=OVH_AI_TOKEN="$OVH_AI_TOKEN" \
  --from-literal=OVH_AI_BASE_URL="$OVH_AI_BASE_URL" \
  --from-literal=OVH_AI_MODEL="$OVH_AI_MODEL" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret docker-registry ghcr-pull-secret \
  -n remediator \
  --docker-server=ghcr.io \
  --docker-username=TitouanSaint-Chamarand \
  --docker-password="$GHCR_PULL_TOKEN" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f "$(dirname "$0")/rbac.yaml" -f "$(dirname "$0")/cronjob.yaml"

echo "Secrets et manifests appliqués. Nettoyage des anciens jobs..."
kubectl delete jobs -n remediator --all --ignore-not-found
kubectl get cronjob,pods -n remediator
