# Statuts CNCF des composants utilisés

| Composant | Projet CNCF | Statut | Usage dans ce repo |
|---|---|---|---|
| **Argo CD** | [argoproj/argo-cd](https://www.cncf.io/projects/argo/) | Graduated | GitOps, app-of-apps |
| **Kyverno** | [kyverno/kyverno](https://www.cncf.io/projects/kyverno/) | Incubating | Policies Audit (privileged, limits, tags) |
| **Falco** | [falcosecurity/falco](https://www.cncf.io/projects/falco/) | Incubating | Détection runtime eBPF |
| **Prometheus** | [prometheus/prometheus](https://www.cncf.io/projects/prometheus/) | Graduated | Métriques (via kube-prometheus-stack) |
| **Grafana** | [grafana/grafana](https://www.cncf.io/projects/grafana/) | Not CNCF (LGTM stack) | Dashboards (chart prometheus-community) |
| **Trivy Operator** | Aqua Security (non CNCF) | — | Scan vulnérabilités images |
| **Kubernetes** | [kubernetes/kubernetes](https://www.cncf.io/projects/kubernetes/) | Graduated | Plateforme OVH Managed K8s |

Sources : [CNCF Landscape](https://landscape.cncf.io/) — juillet 2026.
