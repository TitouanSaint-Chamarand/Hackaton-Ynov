# Installation — Hackaton-Ynov

Guide d'installation du projet **Boucle d'audit et remédiation GitOps assistée par IA** sur un cluster Kubernetes OVH.

**Repo :** https://github.com/TitouanSaint-Chamarand/Hackaton-Ynov  
**Branche :** `main`

---

## Prérequis

| Outil | Version minimale | Usage |
|---|---|---|
| `kubectl` | 1.28+ | Interaction avec le cluster |
| `git` | — | Cloner le repo |
| Accès cluster OVH | — | Fichier `kubeconfig` (hors repo) |

Optionnel (remédiateur local) :

| Outil | Version | Usage |
|---|---|---|
| Python | 3.12+ | Script `apps/remediator/` |
| Docker | — | Build de l'image du remédiateur |

---

## 1. Cloner le dépôt

```bash
git clone https://github.com/TitouanSaint-Chamarand/Hackaton-Ynov.git
cd Hackaton-Ynov
```

---

## 2. Configurer l'accès au cluster

Exporter le kubeconfig fourni par OVH (ne jamais le committer) :

```bash
export KUBECONFIG=/chemin/vers/kubeconfig.yaml
kubectl get nodes
```

Vérifier que le cluster répond avant de continuer.

---

## 3. Installer Argo CD (seule installation manuelle)

Argo CD est le **seul composant installé à la main**. Tout le reste est déployé via GitOps.

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

Attendre que tous les pods soient `Running` :

```bash
kubectl get pods -n argocd -w
```

Récupérer le mot de passe admin initial :

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d && echo
```

Accéder à l'UI Argo CD (optionnel) :

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

- URL : https://localhost:8080
- Utilisateur : `admin`
- Mot de passe : celui récupéré ci-dessus

---

## 4. Bootstrap GitOps (app-of-apps)

Appliquer l'application racine — **dernier `kubectl apply` manuel du projet** :

```bash
kubectl apply -f infra/argocd-apps/root-app.yaml
```

Cette application `root` surveille le dossier `infra/argocd-apps/` et déploie automatiquement tous les composants :

| Application Argo CD | Source | Namespace |
|---|---|---|
| `vulnerable-app` | `apps/vulnerable-app/` | `demo` |
| `trivy-operator` | Chart Helm Aqua Security | `trivy-system` |
| `kyverno` | Chart Helm Kyverno | `kyverno` |
| `policies` | `policies/` | `kyverno` |
| `kube-prometheus-stack` | Chart Helm prometheus-community | `monitoring` |
| `falco` | Chart Helm Falco | `falco` |
| `remediator` | `apps/remediator/k8s/` | `remediator` |

Vérifier que tout est synchronisé :

```bash
kubectl get applications -n argocd
```

Toutes les apps doivent être `Synced` / `Healthy` (peut prendre quelques minutes).

---

## 5. Vérifications par composant

### App vulnérable (cible de démo)

```bash
kubectl get pods -n demo
```

Attendu : `vulnerable-web` en `Running`.

### Trivy Operator (scan de vulnérabilités)

```bash
kubectl get vulnerabilityreports -A
```

Attendu : un rapport pour `vulnerable-web` avec des CVE `CRITICAL` / `HIGH`.

### Kyverno (politiques de sécurité)

```bash
kubectl get policyreports -n demo
```

Attendu : des violations `fail` pour `vulnerable-web` (mode `Audit`, pas de blocage).

### Prometheus / Grafana (observabilité)

```bash
kubectl port-forward svc/kube-prometheus-stack-grafana -n monitoring 3000:80
```

Ouvrir http://localhost:3000 (identifiants par défaut du chart : `admin` / `prom-operator`).

### Falco (détection runtime)

```bash
kubectl exec -it deploy/vulnerable-web -n demo -- sh -c "cat /etc/shadow"
kubectl logs -n falco -l app.kubernetes.io/name=falco --tail=20
```

Attendu : une alerte Falco dans les logs.

---

## 6. Variables d'environnement (remédiateur)

Copier le modèle et renseigner les valeurs réelles :

```bash
cp .env.example .env
```

| Variable | Description |
|---|---|
| `KUBECONFIG` | Chemin vers le kubeconfig |
| `GITHUB_TOKEN_REPO` | PAT fine-grained GitHub (Contents + Pull requests Read/Write) |
| `GHCR_PULL_TOKEN` | Token dedie registre GHCR (scope minimal `read:packages`) |
| `GITHUB_REPO` | `TitouanSaint-Chamarand/Hackaton-Ynov` |
| `OVH_AI_TOKEN` | Clé API OVH AI Endpoints |
| `OVH_AI_BASE_URL` | `https://oai.endpoints.kepler.ai.cloud.ovh.net/v1` |
| `OVH_AI_MODEL` | ex. `Qwen3-Coder-30B-A3B-Instruct` |

> Ne jamais committer `.env`, `token.txt`, `kubeconfig.yaml`, `kubeconfig.yml` ni `*kubeconfig*.yaml`.

---

## 7. Remédiateur — lancement local

```bash
cd apps/remediator
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export KUBECONFIG=/chemin/vers/kubeconfig.yaml
set -a && source ../../.env && set +a
python3 remediator.py
```

Test isolé de l'API IA :

```bash
python3 test_ai.py
```

---

## 8. Remédiateur — déploiement cluster (CronJob)

Créer le secret Kubernetes (jamais committer) :

```bash
kubectl create namespace remediator --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic remediator-secrets -n remediator \
  --from-literal=GITHUB_TOKEN=<token_repo_rw> \
  --from-literal=OVH_AI_TOKEN=<token> \
  --from-literal=OVH_AI_BASE_URL=https://oai.endpoints.kepler.ai.cloud.ovh.net/v1 \
  --from-literal=OVH_AI_MODEL=Qwen3-Coder-30B-A3B-Instruct
kubectl create secret docker-registry ghcr-pull-secret -n remediator \
  --docker-server=ghcr.io \
  --docker-username=<github_user> \
  --docker-password=<token_ghcr_read_packages>
```

Le CronJob est déployé automatiquement par Argo CD (`infra/argocd-apps/remediator.yaml`), schedule `*/10 * * * *`.

Vérifier le RBAC (lecture seule) :

```bash
kubectl auth can-i create deployments \
  --as=system:serviceaccount:remediator:remediator
```

Attendu : `no`.

---

## 9. Boucle de remédiation complète

1. Trivy détecte des CVE sur `vulnerable-web`
2. Le remédiateur lit le rapport, appelle OVH AI Endpoints
3. Validation dry-run du YAML proposé
4. Ouverture d'une PR GitHub (`fix/ai-remediation-<CVE>`)
5. **Revue humaine + merge manuel** (jamais automatisé)
6. Argo CD resync → nouveau pod → Trivy rescan

---

## 10. Phase B — Traçabilité

### B1. Audit Logs OVHcloud (manuel)

1. Ouvrir OVHcloud Manager
2. Aller sur le projet Public Cloud puis le cluster Kubernetes
3. Ouvrir l'onglet `Audit Logs`
4. Verifier qu'un evenement recent apparait avec l'identite de l'utilisateur
5. Prendre une capture d'ecran pour la soutenance

Optionnel: abonner ce flux a Logs Data Platform selon votre configuration OVH.

### B2. Comptes Kubernetes par membre

Le repo contient maintenant une app Argo CD dediee:

- `infra/argocd-apps/team-access.yaml`
- `apps/team-access/k8s/rbac-users.yaml`

Deploiement et verification:

```bash
kubectl get application team-access -n argocd
kubectl get sa -n demo | rg '^user-'
kubectl get rolebindings -n demo | rg 'user-.*-binding'
```

Generation d'un kubeconfig individuel (token 48h par defaut):

```bash
chmod +x apps/team-access/generate-sa-kubeconfig.sh
./apps/team-access/generate-sa-kubeconfig.sh user-dev1 demo 48h
KUBECONFIG=./user-dev1-demo-kubeconfig.yaml kubectl get pods -n demo
```

Les kubeconfigs individuels (`*kubeconfig*.yaml`) sont generes localement et ne doivent jamais etre pushes.

Controle des droits (exemple):

```bash
kubectl auth can-i get pods --as=system:serviceaccount:demo:user-dev3 -n demo
kubectl auth can-i create deployments --as=system:serviceaccount:demo:user-dev3 -n demo
```

Attendu: un profil en `view` peut lire mais pas creer de deployments.

---

## Fichiers sensibles (ne jamais committer)

```
kubeconfig.yaml
kubeconfig.yml
*kubeconfig*.yaml
*kubeconfig*.yml
token.txt
.env
*.pem
```

---

## Dépannage

| Problème | Piste |
|---|---|
| Application Argo CD `OutOfSync` | `kubectl describe application <nom> -n argocd` |
| Pods en `CrashLoopBackOff` | `kubectl logs -n <ns> <pod>` |
| Pas de `VulnerabilityReport` | Attendre 2-5 min, vérifier les pods `trivy-system` |
| Token IA renvoie 403 | Vérifier `OVH_AI_TOKEN` sur https://endpoints.ai.cloud.ovh.net |
| Grafana inaccessible | Vérifier que `kube-prometheus-stack` est `Healthy` |

---

## Documentation complémentaire

- [Architecture](architecture.md) — schéma et choix techniques
- [Tableau CNCF](cncf-table.md) — statuts des composants
- [Remédiateur](../apps/remediator/README.md) — usage détaillé du script Python
