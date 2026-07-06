# TODO — Boucle d'audit et de remédiation GitOps assistée par IA

**Repo :** https://github.com/TitouanSaint-Chamarand/Hackaton-Ynov.git (branche `main`)
**Contexte :** Hackathon Lille Ynov Campus × OVHcloud, 6-7 juillet 2026. Un seul développeur, assisté par Cursor.

---

## Comment utiliser ce fichier

Collez-le à la racine du repo (`TODO.md`), ouvrez-le dans Cursor, et demandez-lui d'exécuter les tâches dans l'ordre. Consignes pour l'agent :

- Traiter les tâches **dans l'ordre des phases**. À l'intérieur d'une phase, les sous-tâches peuvent être parallélisées si elles sont indépendantes.
- Chaque tâche a un **DoD (Definition of Done)** vérifiable par une commande. Ne pas passer à la suivante tant que le DoD n'est pas confirmé.
- Cocher `[x]` et committer (message court, en anglais ou français, peu importe) après chaque tâche terminée. Push régulièrement.
- Si une tâche est marquée **⚠️ INPUT REQUIS**, s'arrêter et demander la valeur à l'utilisateur plutôt que d'inventer une valeur plausible.
- Ne jamais committer `kubeconfig.yaml`, `token.txt`, ou tout fichier `.env` contenant des secrets. Créer un `.gitignore` dès la Phase 1 qui les exclut.
- Ne jamais automatiser le merge d'une Pull Request. C'est une action humaine, sans exception.
- Le ServiceAccount du remédiateur ne doit avoir **aucun droit d'écriture sur le cluster** — lecture seule sur les CRD de rapports, écriture uniquement via l'API Git.
- Après la Phase 2, plus aucune installation manuelle `helm install` en direct (sauf Argo CD lui-même) : tout nouveau composant passe par une Application Argo CD committée dans `infra/argocd-apps/`.

---

## Variables d'environnement nécessaires

À collecter avant la Phase 8. Créer un fichier `.env.example` (sans valeurs réelles) et un `.env` local (gitignored, valeurs réelles) :

| Variable | Description | Statut |
|---|---|---|
| `KUBECONFIG` | Chemin vers le kubeconfig du cluster (déjà fourni par l'utilisateur, hors repo) | ✅ disponible |
| `GITHUB_TOKEN` | Fine-grained PAT GitHub, scope `Contents: Read/Write` + `Pull requests: Read/Write` sur ce repo | ⚠️ INPUT REQUIS — distinct du `token.txt` déjà fourni, qui est probablement une clé AI Endpoints et non un token GitHub |
| `GITHUB_REPO` | `TitouanSaint-Chamarand/Hackaton-Ynov` | ✅ connu |
| `OVH_AI_TOKEN` | Clé API OVHcloud AI Endpoints | ⚠️ à confirmer — vérifier si `token.txt` correspond bien à ceci |
| `OVH_AI_BASE_URL` | URL de base du modèle choisi | ⚠️ INPUT REQUIS — dépend du modèle, à récupérer sur sa fiche dans le catalogue (`endpoints.ai.cloud.ovh.net`) |
| `OVH_AI_MODEL` | Nom exact du modèle (ex. `Meta-Llama-3_3-70B-Instruct` ou `Qwen2.5-Coder-32B-Instruct`) | ⚠️ INPUT REQUIS |

---

## Phase 1 — Bootstrap du repo

**Objectif :** structure de base en place et poussée sur `main`.

- [x] Cloner `https://github.com/TitouanSaint-Chamarand/Hackaton-Ynov.git`
- [x] Créer la structure :
  ```
  apps/
    vulnerable-app/
    remediator/
  infra/
    argocd-apps/
  policies/
  docs/
  ```
- [x] Créer `.gitignore` :
  ```
  kubeconfig.yaml
  kubeconfig.yml
  token.txt
  .env
  *.pem
  ```
- [x] Commit initial + push sur `main`

**DoD :** `git log` montre le commit, les dossiers existent sur GitHub.

---

## Phase 2 — Argo CD (le seul install manuel du projet)

**Objectif :** Argo CD tourne et surveille le repo. Jalon cible : aujourd'hui (lundi) midi.

- [x] `kubectl create namespace argocd`
- [x] `kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argocd/stable/manifests/install.yaml`
- [x] Attendre que tous les pods soient `Running` : `kubectl get pods -n argocd -w`
- [x] Récupérer le mot de passe admin initial :
  ```
  kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
  ```
- [x] Créer `infra/argocd-apps/root-app.yaml` (app-of-apps racine) :
  ```yaml
  apiVersion: argoproj.io/v1alpha1
  kind: Application
  metadata:
    name: root
    namespace: argocd
  spec:
    project: default
    source:
      repoURL: https://github.com/TitouanSaint-Chamarand/Hackaton-Ynov.git
      targetRevision: main
      path: infra/argocd-apps
    destination:
      server: https://kubernetes.default.svc
      namespace: argocd
    syncPolicy:
      automated: { prune: true, selfHeal: true }
  ```
- [x] `kubectl apply -f infra/argocd-apps/root-app.yaml` — **dernier `kubectl apply` manuel du projet, hors debug**
- [x] Commit + push `infra/argocd-apps/root-app.yaml`

**DoD :** `kubectl get applications -n argocd` liste `root` en `Synced`/`Healthy`.

---

## Phase 3 — Workload volontairement vulnérable

**Objectif :** une cible avec 4 familles de failles pour alimenter scanners + démo.

- [x] Créer `apps/vulnerable-app/deployment.yaml` :
  ```yaml
  apiVersion: apps/v1
  kind: Deployment
  metadata:
    name: vulnerable-web
    namespace: demo
  spec:
    replicas: 1
    selector:
      matchLabels: { app: vulnerable-web }
    template:
      metadata:
        labels: { app: vulnerable-web }
      spec:
        containers:
          - name: web
            image: nginx:1.14          # FAILLE 1 : CVE connues
            securityContext:
              privileged: true          # FAILLE 2
              runAsUser: 0              # FAILLE 3
            ports:
              - containerPort: 80
            # FAILLE 4 : pas de resources.limits
  ```
- [x] Créer `infra/argocd-apps/vulnerable-app.yaml` :
  ```yaml
  apiVersion: argoproj.io/v1alpha1
  kind: Application
  metadata:
    name: vulnerable-app
    namespace: argocd
  spec:
    project: default
    source:
      repoURL: https://github.com/TitouanSaint-Chamarand/Hackaton-Ynov.git
      targetRevision: main
      path: apps/vulnerable-app
    destination:
      server: https://kubernetes.default.svc
      namespace: demo
    syncPolicy:
      automated: { prune: true, selfHeal: true }
      syncOptions: [CreateNamespace=true]
  ```
- [x] Commit + push

**DoD :** `kubectl get pods -n demo` montre `vulnerable-web` en `Running`. Garder ce commit identifiable — il servira à "rejouer" la faille en démo (`git revert` du futur correctif).

---

## Phase 4 — Trivy-operator (détection de vulnérabilités)

- [x] Créer `infra/argocd-apps/trivy-operator.yaml` :
  ```yaml
  apiVersion: argoproj.io/v1alpha1
  kind: Application
  metadata:
    name: trivy-operator
    namespace: argocd
  spec:
    project: default
    source:
      repoURL: https://aquasecurity.github.io/helm-charts/
      chart: trivy-operator
      targetRevision: "*"
      helm:
        values: |
          trivy:
            ignoreUnfixed: true
    destination:
      server: https://kubernetes.default.svc
      namespace: trivy-system
    syncPolicy:
      automated: { prune: true, selfHeal: true }
      syncOptions: [CreateNamespace=true]
  ```
- [x] Commit + push

**DoD :** après quelques minutes, `kubectl get vulnerabilityreports -A` montre un rapport pour `vulnerable-web` avec des CVE `CRITICAL`/`HIGH`.

---

## Phase 5 — Kyverno (policy-as-code)

**Note :** garder `validationFailureAction: Audit` — jamais `Enforce`, sinon Kyverno bloquerait votre propre workload vulnérable et il n'y aurait plus rien à démontrer.

- [ ] Créer `infra/argocd-apps/kyverno.yaml` :
  ```yaml
  apiVersion: argoproj.io/v1alpha1
  kind: Application
  metadata:
    name: kyverno
    namespace: argocd
  spec:
    project: default
    source:
      repoURL: https://kyverno.github.io/kyverno/
      chart: kyverno
      targetRevision: "*"
    destination:
      server: https://kubernetes.default.svc
      namespace: kyverno
    syncPolicy:
      automated: { prune: true, selfHeal: true }
      syncOptions: [CreateNamespace=true, ServerSideApply=true]
  ```
- [ ] Créer `policies/disallow-privileged.yaml`, `policies/require-limits.yaml`, `policies/disallow-latest-tag.yaml` (3 ClusterPolicy en mode `Audit`, cf. bibliothèque officielle : https://kyverno.io/policies/)
- [ ] Créer `infra/argocd-apps/policies.yaml` pointant sur le dossier `policies/` (même modèle que `vulnerable-app.yaml`)
- [ ] Commit + push

**DoD :** `kubectl get policyreports -n demo` montre des violations `fail` pour `vulnerable-web`.

---

## Phase 6 — Prometheus (observabilité)

- [ ] Créer `infra/argocd-apps/prometheus.yaml` (chart `kube-prometheus-stack`, repo `https://prometheus-community.github.io/helm-charts`, namespace `monitoring`, `ServerSideApply=true`)
- [ ] Commit + push

**DoD :** `kubectl port-forward svc/kube-prometheus-stack-grafana -n monitoring 3000:80` puis Grafana accessible.

---

## Phase 7 — Falco (détection runtime)

**Priorité basse** : le brief le liste comme obligatoire, mais en solo, ne pas bloquer la Phase 9 pour ça. À faire si Phases 1-6 sont bouclées avec de l'avance.

- [ ] Créer `infra/argocd-apps/falco.yaml` (chart `falco`, repo `https://falcosecurity.github.io/charts`, `driver.kind: modern_ebpf`, `falcosidekick.enabled: true`)
- [ ] Commit + push

**DoD :** `kubectl exec -it deploy/vulnerable-web -n demo -- sh -c "cat /etc/shadow"` déclenche une alerte visible dans `kubectl logs -n falco -l app.kubernetes.io/name=falco`.

---

## Phase 8 — AI Endpoints : premier appel isolé

⚠️ **INPUT REQUIS avant de continuer** : `OVH_AI_BASE_URL` et `OVH_AI_MODEL` (fiche du modèle sur le catalogue). Ne pas deviner une URL.

- [ ] Test curl :
  ```bash
  curl -s "$OVH_AI_BASE_URL/chat/completions" \
    -H "Authorization: Bearer $OVH_AI_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"model":"'"$OVH_AI_MODEL"'","messages":[{"role":"user","content":"ça marche ?"}]}'
  ```
- [ ] Test Python équivalent avec le client `openai` (`base_url` + `api_key` pointant vers AI Endpoints)

**DoD :** réponse JSON contenant `choices[0].message.content`.

---

## Phase 9 — Le remédiateur (`apps/remediator/remediator.py`)

**C'est le vrai livrable applicatif.** Contrat attendu — pas de code fourni ici, à écrire :

| Fonction | Entrée | Sortie |
|---|---|---|
| `get_vulnerability_reports(namespace)` | nom de namespace | liste des `VulnerabilityReport` (group `aquasecurity.github.io`, version `v1alpha1`, plural `vulnerabilityreports`) |
| `summarize_report(report)` | un rapport | résumé texte compact (CVE triées par sévérité, avec `fixedVersion`) pour le prompt |
| `get_manifest_from_github(repo, path)` | chemin du manifeste | contenu YAML actuel + sha (pour le commit) |
| `ask_ai_for_fix(summary, manifest)` | résumé + manifeste | `(explication, yaml_corrigé)` — forcer un format de sortie strict côté prompt système |
| `validate_yaml(yaml_corrigé)` | YAML proposé | bool — dry-run (`kubectl apply --dry-run=server` ou `yaml.safe_load`) avant toute création de PR |
| `open_pull_request(...)` | branche + patch + explication | URL de la PR créée |

**Garde-fous obligatoires (à implémenter, pas optionnels) :**
- [ ] Validation dry-run du YAML avant d'ouvrir la PR
- [ ] Vérifier qu'une PR `fix/ai-remediation-<id>` n'est pas déjà ouverte avant d'en créer une
- [ ] Titre de la PR = identifiant CVE, description = explication de l'IA
- [ ] `requirements.txt` : `openai`, `kubernetes`, `PyGithub`, `pyyaml`

**DoD :** exécuter le script ouvre une vraie PR sur `TitouanSaint-Chamarand/Hackaton-Ynov` avec un manifeste corrigé (image à jour, `privileged` retiré, non-root, `resources.limits` ajoutées) et une explication lisible.

---

## Phase 10 — Fermer la boucle

- [ ] Relire la PR (revue humaine)
- [ ] Merger **manuellement** (jamais automatisé)
- [ ] Vérifier resync Argo CD (`kubectl get pods -n demo` → nouveau pod)
- [ ] Relancer/attendre un scan Trivy et vérifier que le `VulnerabilityReport` critique a disparu

**DoD :** boucle complète prouvée de bout en bout sur au moins une vulnérabilité.

---

## Phase 11 — RBAC + packaging CronJob (bonus)

- [ ] `ServiceAccount` + `ClusterRole` (lecture seule sur `vulnerabilityreports`) + `ClusterRoleBinding`
- [ ] `Dockerfile` pour `apps/remediator/`
- [ ] `infra/argocd-apps/remediator.yaml` (CronJob packagé, déployé lui aussi via Argo CD, schedule `*/10 * * * *`)
- [ ] Adapter le script pour `config.load_incluster_config()` au lieu du kubeconfig local

**DoD :** `kubectl auth can-i create deployments --as=system:serviceaccount:<ns>:<sa>` répond `no`. Une exécution manuelle du CronJob réussit.

---

## Phase 12 — Vérification sécurité (ne pas sauter)

- [ ] RBAC du remédiateur confirmé lecture seule
- [ ] Aucune étape n'automatise le merge
- [ ] Aucun secret commité (vérifier l'historique git aussi, pas juste l'état actuel)

---

## Phase 13 — Documentation

- [ ] `apps/remediator/README.md` (comment lancer, variables d'env nécessaires)
- [ ] `docs/architecture.md` — rapport 1-2 pages : schéma, rôle de chaque brique, choix (Trivy vs Kubescape, script vs opérateur), limites
- [ ] `docs/cncf-table.md` — tableau statuts CNCF des composants réellement utilisés

---

## Aide-mémoire liens

| Sujet | Lien |
|---|---|
| Argo CD | https://argo-cd.readthedocs.io |
| Trivy-operator | https://github.com/aquasecurity/trivy-operator |
| Kyverno policies | https://kyverno.io/policies/ |
| Falco | https://falco.org/docs/ |
| kube-prometheus-stack | https://github.com/prometheus-community/helm-charts |
| AI Endpoints | https://endpoints.ai.cloud.ovh.net |
| PyGithub | https://pygithub.readthedocs.io/en/stable/ |
| GitHub REST — Create a PR | https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#create-a-pull-request |
