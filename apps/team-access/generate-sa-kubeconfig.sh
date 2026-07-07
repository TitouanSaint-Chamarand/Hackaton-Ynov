#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "Usage: $0 <serviceaccount> <namespace> [duration]"
  echo "Example: $0 user-dev1 demo 48h"
  exit 1
fi

SERVICE_ACCOUNT="$1"
NAMESPACE="$2"
DURATION="${3:-48h}"

CLUSTER_NAME="$(kubectl config view --minify -o jsonpath='{.clusters[0].name}')"
SERVER="$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')"
CA_DATA="$(kubectl config view --raw --minify -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')"
TOKEN="$(kubectl create token "${SERVICE_ACCOUNT}" -n "${NAMESPACE}" --duration="${DURATION}")"

OUTPUT_FILE="${SERVICE_ACCOUNT}-${NAMESPACE}-kubeconfig.yaml"

cat > "${OUTPUT_FILE}" <<EOF
apiVersion: v1
kind: Config
clusters:
  - name: ${CLUSTER_NAME}
    cluster:
      server: ${SERVER}
      certificate-authority-data: ${CA_DATA}
contexts:
  - name: ${SERVICE_ACCOUNT}@${CLUSTER_NAME}
    context:
      cluster: ${CLUSTER_NAME}
      namespace: ${NAMESPACE}
      user: ${SERVICE_ACCOUNT}
current-context: ${SERVICE_ACCOUNT}@${CLUSTER_NAME}
users:
  - name: ${SERVICE_ACCOUNT}
    user:
      token: ${TOKEN}
EOF

echo "kubeconfig genere: ${OUTPUT_FILE}"
echo "test rapide: KUBECONFIG=${OUTPUT_FILE} kubectl get pods -n ${NAMESPACE}"
