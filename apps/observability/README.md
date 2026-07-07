# Observability security assets (Phase C)

Ce dossier contient les objets Kubernetes pour la phase C:

- `cve-critical-alert.yaml`: regle Prometheus/Alertmanager sur les CVE critiques
- `grafana-dashboard-security-incident.yaml`: dashboard Grafana avec 2 panels
  - metrique Prometheus `sum(trivy_image_vulnerabilities{severity="Critical"})`
  - logs Loki `{namespace="demo"}`

## Verification rapide

```bash
kubectl get prometheusrule -n monitoring cve-critical-alert
kubectl get configmap -n monitoring grafana-dashboard-security-incident
```

Dans Grafana:

1. Verifier que la datasource Loki existe
2. Ouvrir le dashboard `Scenario incident securite`
3. Aligner la plage temporelle et observer metriques + logs
