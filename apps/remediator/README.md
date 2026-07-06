# Remédiateur IA

Script Python qui lit les `VulnerabilityReport` Trivy, demande un correctif à OVH AI Endpoints, valide le YAML puis ouvre une Pull Request GitHub.

## Prérequis

- Python 3.12+
- `kubectl` configuré (dry-run serveur)
- Tokens dans un fichier `.env` local (voir `.env.example` à la racine)

## Installation

```bash
cd apps/remediator
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Variables d'environnement

| Variable | Description |
|---|---|
| `KUBECONFIG` | Chemin vers le kubeconfig (hors repo) |
| `GITHUB_TOKEN` | PAT fine-grained : Contents + Pull requests (Read/Write) |
| `GITHUB_REPO` | `TitouanSaint-Chamarand/Hackaton-Ynov` |
| `OVH_AI_TOKEN` | Clé API OVH AI Endpoints |
| `OVH_AI_BASE_URL` | `https://oai.endpoints.kepler.ai.cloud.ovh.net/v1` |
| `OVH_AI_MODEL` | ex. `Qwen3-Coder-30B-A3B-Instruct` |
| `TARGET_NAMESPACE` | Namespace scanné (défaut : `demo`) |
| `MANIFEST_PATH` | Chemin du manifeste à corriger |

## Lancement local

```bash
export KUBECONFIG=~/Downloads/kubeconfig.yaml
set -a && source ../../.env && set +a
python3 remediator.py
```

## Test AI Endpoints (Phase 8)

```bash
set -a && source ../../.env && set +a
python3 test_ai.py
```

## Déploiement cluster (CronJob)

1. Créer le secret Kubernetes (jamais committer) :

```bash
kubectl create namespace remediator
kubectl create secret generic remediator-secrets -n remediator \
  --from-literal=GITHUB_TOKEN=... \
  --from-literal=OVH_AI_TOKEN=... \
  --from-literal=OVH_AI_BASE_URL=https://oai.endpoints.kepler.ai.cloud.ovh.net/v1 \
  --from-literal=OVH_AI_MODEL=Qwen3-Coder-30B-A3B-Instruct
```

2. Builder et pousser l'image Docker, puis laisser Argo CD synchroniser `infra/argocd-apps/remediator.yaml`.

## Garde-fous

- Dry-run `kubectl apply --dry-run=server` avant toute PR
- Pas de PR si une branche `fix/ai-remediation-*` existe déjà
- Titre PR = identifiant CVE, description = explication IA
- ServiceAccount cluster : lecture seule sur `vulnerabilityreports` uniquement
- **Aucun merge automatique** — revue humaine obligatoire
