#!/usr/bin/env bash
set -euo pipefail

echo "== Check A3: Kyverno policy deployed =="
kubectl get clusterpolicy disallow-latest-tag

echo
echo "== Check policy reports related to latest tag =="
kubectl get policyreports -A | rg "disallow-latest-tag|NAME|NAMESPACE" || true

echo
echo "== Check C1: Loki datasource config exists in monitoring =="
kubectl get configmap grafana-datasource-loki -n monitoring

echo
echo "== Check C1: Loki stack and promtail are running =="
kubectl get pods -n logging

echo
echo "== Suggested manual Grafana Explore query =="
echo "{namespace=\"demo\"}"
