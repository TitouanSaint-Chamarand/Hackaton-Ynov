# TODO — Ajustements retour coachs OVHcloud (jour 2)

**Contexte :** ce fichier complète `TODO.md` (ne le remplace pas). Restitutions cet après-midi — priorités classées de la plus rentable à la plus sacrifiable. Si le temps manque, s'arrêter à la dernière tâche cochée et l'assumer en soutenance plutôt que de bâcler la suite.

**Repo :** https://github.com/TitouanSaint-Chamarand/Hackaton-Ynov.git

---

## Consignes pour l'agent

- Traiter les phases **dans l'ordre A → B → C**. Ne pas commencer C si A et B ne sont pas finis.
- Pour tout ce qui touche aux clés Helm `values` (`resources.limits`, etc.), **vérifier d'abord avec `helm show values <repo> <chart> --version <version>`** avant d'écrire l'override — les noms de clés diffèrent d'un chart à l'autre, ne pas deviner.
- Committer + push après chaque tâche, comme sur `TODO.md`.

---

## Phase A — Corrections coachs (⏱ 30-45 min)

### A1. Figer les versions des charts Helm

- [ ] Pour chaque Application déjà déployée (`trivy-operator`, `kyverno`, `kube-prometheus-stack`, `falco` si présent), récupérer la version actuellement synchronisée :
  ```bash
  kubectl get application <nom> -n argocd -o jsonpath='{.status.sync.revision}{"\n"}'
  ```
- [x] Remplacer `targetRevision: "*"` par cette version exacte dans chaque `infra/argocd-apps/*.yaml`

**DoD :** plus aucun `targetRevision: "*"` dans le repo.

### A2. Limites CPU/RAM sur les vrais composants (pas le workload vulnérable)

- [x] Pour chaque chart (`trivy-operator`, `kyverno`, `falco`, `kube-prometheus-stack`), lancer `helm show values <repo> <chart>` et repérer la clé `resources` correspondante
- [x] Ajouter un bloc `resources.limits` raisonnable (ex. `cpu: 500m`, `memory: 512Mi` — ajuster selon la taille réelle du cluster) dans le `helm.values` de l'Application Argo CD concernée

**DoD :** `kubectl get pods -n <namespace> -o jsonpath='{.items[*].spec.containers[*].resources}'` montre des limites non vides pour chaque composant d'infra (pas le workload vulnérable, qui doit rester sans limites — c'est une des 4 failles volontaires).

### A3. Tags d'image toujours figés

- [ ] Vérifier que `policies/disallow-latest-tag.yaml` (Kyverno) est bien déployé : `kubectl get clusterpolicy disallow-latest-tag`
- [x] Relire le prompt système du remédiateur (`apps/remediator/remediator.py`) : confirmer qu'il impose explicitement un tag de version précis dans le YAML corrigé, jamais `:latest`

**DoD :** `kubectl get policyreports -A` ne montre plus de violation `disallow-latest-tag` après le prochain correctif mergé.

---

## Phase B — Le différenciateur : traçabilité (⏱ 45 min-1h)

### B1. Activer l'audit natif OVHcloud (⏱ 15 min — très rentable, à ne pas sauter)

- [ ] Ouvrir le Manager OVHcloud → votre cluster → onglet **Audit Logs** — c'est déjà natif, rien à installer
- [ ] *(Optionnel si temps)* Abonner ce flux à Logs Data Platform pour la rétention/recherche :
  ```
  POST /cloud/project/{serviceName}/kube/{kubeId}/log/subscription
  { "kind": "audit", "streamId": "<streamId de votre compte LDP>" }
  ```
- [ ] Préparer une capture d'écran de cet onglet pour la démo (filet de sécurité si la démo live a un souci)

**DoD :** capable de montrer en direct un log d'action sur le cluster avec l'identité de l'utilisateur qui l'a faite.

⚠️ Ces logs couvrent les actions sur l'API Kubernetes (qui a créé/modifié quoi), pas les logs applicatifs des containers — c'est le rôle de Loki (Phase C).

### B2. Users Kubernetes personnalisés (un par membre de l'équipe)

Pas de CSR/certificats signés (trop long) — on passe par des ServiceAccounts avec token.

- [x] Créer 4 `ServiceAccount` (un par personne), namespace `demo` ou `default` selon vos besoins :
  ```yaml
  apiVersion: v1
  kind: ServiceAccount
  metadata:
    name: user-<prenom>
    namespace: demo
  ```
- [x] Un `RoleBinding` par personne, adapté à son rôle réel (ex. lecture seule pour la partie IA, plus large pour Infra) :
  ```yaml
  apiVersion: rbac.authorization.k8s.io/v1
  kind: RoleBinding
  metadata:
    name: user-<prenom>-binding
    namespace: demo
  subjects:
    - kind: ServiceAccount
      name: user-<prenom>
      namespace: demo
  roleRef:
    kind: ClusterRole
    name: edit          # ou "view" pour un accès lecture seule
    apiGroup: rbac.authorization.k8s.io
  ```
- [ ] Générer un token + kubeconfig individuel :
  ```bash
  kubectl create token user-<prenom> -n demo --duration=48h
  ```
  (construire un kubeconfig minimal avec ce token + l'URL du cluster + le CA déjà présent dans le kubeconfig admin)
- [x] Ajouter un script repo pour automatiser cette génération : `scripts/team-access/generate-kubeconfigs.sh`
- [ ] Chaque membre utilise désormais SON kubeconfig pour ses actions manuelles

**DoD :** `kubectl get pods -n demo --as=system:serviceaccount:demo:user-<prenom>` reflète les droits attendus (pas plus).

---

## Phase C — Observabilité avancée (⏱ 1h30-2h — sacrifier en premier si le temps manque)

### C1. Loki (logs applicatifs)

- [x] Créer `infra/argocd-apps/loki.yaml` :
  ```yaml
  apiVersion: argoproj.io/v1alpha1
  kind: Application
  metadata:
    name: loki-stack
    namespace: argocd
  spec:
    project: default
    source:
      repoURL: https://grafana.github.io/helm-charts
      chart: loki-stack
      targetRevision: "<figer une version précise>"
      helm:
        values: |
          grafana:
            enabled: false   # vous avez déjà Grafana via kube-prometheus-stack
          promtail:
            enabled: true
    destination:
      server: https://kubernetes.default.svc
      namespace: logging
    syncPolicy:
      automated: { prune: true, selfHeal: true }
      syncOptions: [CreateNamespace=true]
  ```
- [ ] Dans Grafana (déjà déployé), ajouter Loki comme datasource si pas auto-détecté
- [ ] Vérifier : requête LogQL `{namespace="demo"}` dans Grafana Explore montre les logs de `vulnerable-web`
- [x] Ajouter un script de vérification cluster A3/C1 : `scripts/security/verify-phase-a3-c1.sh`

**DoD :** logs du conteneur `vulnerable-web` visibles dans Grafana, sur la même timeline que les métriques Prometheus.

### C2. Alertmanager — alerte sur CVE critique

- [x] Créer une `PrometheusRule` (Alertmanager est déjà bundlé dans `kube-prometheus-stack`, rien à réinstaller) :
  ```yaml
  apiVersion: monitoring.coreos.com/v1
  kind: PrometheusRule
  metadata:
    name: cve-critical-alert
    namespace: monitoring
    labels:
      release: kube-prometheus-stack
  spec:
    groups:
      - name: security
        rules:
          - alert: CriticalCVEDetected
            expr: sum(trivy_image_vulnerabilities{severity="Critical"}) > 0
            for: 5m
            labels:
              severity: critical
            annotations:
              summary: "Au moins une CVE critique détectée dans le cluster"
  ```
- [x] Commit dans `infra/argocd-apps/` (ou via une Application dédiée pointant sur ce fichier)

**DoD :** l'alerte apparaît dans l'UI Alertmanager (`kubectl port-forward svc/kube-prometheus-stack-alertmanager -n monitoring 9093:9093`) quand une CVE critique est présente.

### C3. Dashboard Grafana "scénario d'incident"

- [x] Un dashboard avec 2 panels minimum : courbe `sum(trivy_image_vulnerabilities{severity="Critical"})` (Prometheus) + panel logs Loki `{namespace="demo"}`, alignés sur la même plage de temps
- [ ] Repérer visuellement le moment où la courbe chute après un merge — c'est le moment le plus fort de la démo

**DoD :** capable de montrer en 30 secondes "voilà quand la faille est apparue, voilà les logs à ce moment, voilà quand c'est corrigé".

---

## Si vous n'avez que 2h

Faites A en entier + B1 (audit natif, 15 min) + B2 sur 2 personnes sur 4 pour prouver le principe. Sautez C entièrement et dites-le en soutenance comme piste identifiée mais non implémentée faute de temps — c'est une vraie réponse, pas un aveu de faiblesse.

---

## Annexe — Workload vulnerable-app (juice shop)

Objectif: remplacer le workload Nginx minimal par une app web volontairement vulnérable
pour une demo securite plus realiste.

### Manifests ajoutes/mis a jour

- `apps/vulnerable-app/deployment.yaml`
- `apps/vulnerable-app/service.yaml`
- `apps/vulnerable-app/ingress.yaml`
- `apps/vulnerable-app/security-misconfig.yaml`

### Deploiement

```bash
kubectl apply -f apps/vulnerable-app/
kubectl get pods,svc,ing -n demo
```

Si vous utilisez un Ingress NGINX local:

```bash
echo "127.0.0.1 vulnerable-web.local" | sudo tee -a /etc/hosts
```

Puis ouvrir `http://vulnerable-web.local` (ou faire un `port-forward` sur le service).

### Failles volontairement presentes

1. **Applicatif**: OWASP Juice Shop (vulnerabilites natives de l'application).
2. **Runtime container permissif**: `privileged: true`, `runAsUser: 0`,
   `allowPrivilegeEscalation: true`, capabilities ajoutees.
3. **RBAC excessif**: ServiceAccount `vulnerable-admin` lie a `cluster-admin`.
4. **Pas de limites de ressources**: absence de `resources.limits`.

### Verification securite (attendue)

- `kyverno` doit remonter des violations sur le contexte de securite et/ou policies.
- `trivy-operator` doit pouvoir lister des vulnerabilites image/app.
- Les dashboards/alertes securite doivent montrer un signal plus riche que le cas Nginx.