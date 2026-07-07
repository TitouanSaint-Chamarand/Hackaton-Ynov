# Observability security assets (Phase C)

Ce dossier contient les objets Kubernetes utilises pour la vue astreinte securite:

- `cve-critical-alert.yaml`: regle Prometheus/Alertmanager sur les CVE critiques
- `grafana-dashboard-security-incident.yaml`: dashboard Grafana orientee incident
  - variables de triage: `namespace`, `service`, `severity`, `time_window`
  - panneaux sante: CVE, redemarrages, CPU, changements recents
  - logs Loki correles + bloc contexte astreinte

## Verification rapide

```bash
kubectl get prometheusrule -n monitoring cve-critical-alert
kubectl get configmap -n monitoring grafana-dashboard-security-incident
```

## Utilisation en astreinte

1. Ouvrir le dashboard `Astreinte - Incident securite`.
2. Fixer `namespace` puis `service` pour reduire le bruit.
3. Verifier le volume de CVE sur la severite surveillee.
4. Croiser avec les panneaux redemarrages/CPU pour qualifier l'impact.
5. Ouvrir `Logs correles` et rechercher les erreurs au meme intervalle.
6. Utiliser le panneau `Contexte astreinte` pour runbook et escalation.

## Contexte injecte dans l'alerte

L'alerte `CriticalCVEDetected` fournit maintenant:

- `impact`: impact metier/technique attendu
- `owner_team`: equipe responsable
- `runbook_url`: lien d'investigation
- `dashboard_uid`: dashboard cible pour triage
- `logs_query`: requete Loki recommandee

## Scenario de validation on-call

Objectif: confirmer qu'un on-call passe de l'alerte au diagnostic initial en moins de 5 minutes.

1. Injecter un incident securite simule (ou forcer une metrique de test).
2. Verifier le declenchement de `CriticalCVEDetected` (apres `for: 5m`).
3. Ouvrir le dashboard depuis `dashboard_uid`.
4. Appliquer les filtres (`namespace`, `service`, `severity`).
5. Confirmer:
   - CVE visibles dans les panels metriques
   - signaux d'impact (redemarrages/CPU)
   - logs corrigeables dans le panneau Loki
6. Noter le temps total et les blocages.

## Checklist de verification

- Datasources Prometheus et Loki disponibles dans Grafana
- Dashboard importe sans erreur JSON
- Requetes Prometheus retournent des series
- Requete Loki retourne des logs sur le namespace cible
- Champs d'annotations presents dans l'alerte
