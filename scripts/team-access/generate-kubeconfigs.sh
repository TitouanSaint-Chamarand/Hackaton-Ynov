#!/usr/bin/env bash
set -euo pipefail

# Generate one kubeconfig per ServiceAccount in a namespace.
# Usage:
#   ./scripts/team-access/generate-kubeconfigs.sh demo user-dev1 user-dev2
#   ./scripts/team-access/generate-kubeconfigs.sh demo user-dev1 --duration=48h

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <namespace> <serviceaccount...> [--duration=48h]"
  exit 1
fi

namespace="$1"
shift

duration="48h"
users=()

for arg in "$@"; do
  if [[ "$arg" == --duration=* ]]; then
    duration="${arg#--duration=}"
  else
    users+=("$arg")
  fi
done

if [[ ${#users[@]} -eq 0 ]]; then
  echo "Error: provide at least one serviceaccount name"
  exit 1
fi

cluster_name="$(kubectl config view --minify -o jsonpath='{.contexts[0].context.cluster}')"
server="$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')"
ca_data="$(kubectl config view --raw --minify -o jsonpath='{.clusters[0].cluster.certificate-authority-data}')"

output_dir="generated-kubeconfigs"
mkdir -p "${output_dir}"

for sa in "${users[@]}"; do
  echo "Generating token for ${sa} in namespace ${namespace}..."
  token="$(kubectl create token "${sa}" -n "${namespace}" --duration="${duration}")"

  kubeconfig_path="${output_dir}/kubeconfig-${sa}.yaml"

  cat > "${kubeconfig_path}" <<EOF
apiVersion: v1
kind: Config
clusters:
  - name: ${cluster_name}
    cluster:
      server: ${server}
      certificate-authority-data: ${ca_data}
users:
  - name: ${sa}
    user:
      token: ${token}
contexts:
  - name: ${sa}@${cluster_name}
    context:
      cluster: ${cluster_name}
      namespace: ${namespace}
      user: ${sa}
current-context: ${sa}@${cluster_name}
EOF

  chmod 600 "${kubeconfig_path}"
  echo "Wrote ${kubeconfig_path}"
done

echo "Done. Share kubeconfig files securely with each teammate."
