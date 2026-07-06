#!/usr/bin/env python3
"""Remédiateur GitOps assisté par IA — lit Trivy, propose un correctif via PR."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from typing import Any

import yaml
from github import Github
from kubernetes import client, config
from openai import OpenAI

GITHUB_REPO = os.getenv("GITHUB_REPO", "TitouanSaint-Chamarand/Hackaton-Ynov")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OVH_AI_TOKEN = os.getenv("OVH_AI_TOKEN")
OVH_AI_BASE_URL = os.getenv(
    "OVH_AI_BASE_URL", "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1"
)
OVH_AI_MODEL = os.getenv("OVH_AI_MODEL", "Qwen3-Coder-30B-A3B-Instruct")
MANIFEST_PATH = os.getenv("MANIFEST_PATH", "apps/vulnerable-app/deployment.yaml")
TARGET_NAMESPACE = os.getenv("TARGET_NAMESPACE", "demo")
PR_BRANCH_PREFIX = "fix/ai-remediation-"

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}

SYSTEM_PROMPT = """Tu es un assistant de remédiation Kubernetes.
On te fournit un résumé de vulnérabilités Trivy et le manifeste Deployment actuel.

Corrige le manifeste en respectant ces règles :
- Mettre à jour l'image nginx vers une version récente sans CVE critiques connues
- Retirer privileged: true et runAsUser: 0 ; utiliser runAsNonRoot: true et runAsUser: 101
- Ajouter resources.limits (cpu et memory) sur chaque conteneur
- Conserver apiVersion, kind, name, namespace et labels

Réponds EXACTEMENT avec ce format (sans markdown autour du YAML) :

EXPLANATION:
<2 à 4 phrases en français expliquant les corrections>

YAML:
<manifeste Deployment complet corrigé>
"""


def load_k8s_config() -> None:
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        config.load_incluster_config()
    else:
        config.load_kube_config()


def get_vulnerability_reports(namespace: str) -> list[dict[str, Any]]:
    load_k8s_config()
    api = client.CustomObjectsApi()
    result = api.list_namespaced_custom_object(
        group="aquasecurity.github.io",
        version="v1alpha1",
        namespace=namespace,
        plural="vulnerabilityreports",
    )
    return result.get("items", [])


def summarize_report(report: dict[str, Any]) -> str:
    meta = report.get("metadata", {})
    name = meta.get("name", "unknown")
    artifact = report.get("report", {}).get("artifact", {})
    vulns = report.get("report", {}).get("vulnerabilities", [])
    sorted_vulns = sorted(
        vulns,
        key=lambda v: SEVERITY_ORDER.get(v.get("severity", "UNKNOWN"), 5),
    )

    lines = [
        f"Report: {name}",
        f"Image: {artifact.get('repository', '?')}:{artifact.get('tag', '?')}",
        f"Total vulnérabilités: {len(vulns)}",
        "",
    ]
    for vuln in sorted_vulns[:25]:
        lines.append(
            f"- {vuln.get('vulnerabilityID', '?')} "
            f"({vuln.get('severity', '?')}) "
            f"fixedVersion={vuln.get('fixedVersion', 'none')}"
        )
    if len(sorted_vulns) > 25:
        lines.append(f"... et {len(sorted_vulns) - 25} autres")
    return "\n".join(lines)


def get_manifest_from_github(repo: str, path: str) -> tuple[str, str]:
    if not GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN manquant")
    gh = Github(GITHUB_TOKEN)
    content = gh.get_repo(repo).get_contents(path)
    return content.decoded_content.decode("utf-8"), content.sha


def _parse_ai_response(content: str) -> tuple[str, str]:
    explanation_match = re.search(
        r"EXPLANATION:\s*(.*?)\s*YAML:", content, re.DOTALL | re.IGNORECASE
    )
    yaml_match = re.search(r"YAML:\s*(.*)", content, re.DOTALL | re.IGNORECASE)
    explanation = (
        explanation_match.group(1).strip() if explanation_match else "Correction IA."
    )
    fixed_yaml = yaml_match.group(1).strip() if yaml_match else content.strip()
    fixed_yaml = re.sub(r"^```(?:yaml)?\s*", "", fixed_yaml)
    fixed_yaml = re.sub(r"\s*```$", "", fixed_yaml)
    return explanation, fixed_yaml


def ask_ai_for_fix(summary: str, manifest: str) -> tuple[str, str]:
    if not OVH_AI_TOKEN:
        raise RuntimeError("OVH_AI_TOKEN manquant")
    ai = OpenAI(api_key=OVH_AI_TOKEN, base_url=OVH_AI_BASE_URL)
    response = ai.chat.completions.create(
        model=OVH_AI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Résumé Trivy:\n{summary}\n\nManifeste actuel:\n{manifest}",
            },
        ],
        temperature=0.1,
        max_tokens=4096,
    )
    content = response.choices[0].message.content or ""
    return _parse_ai_response(content)


def validate_yaml(yaml_content: str) -> bool:
    try:
        docs = list(yaml.safe_load_all(yaml_content))
    except yaml.YAMLError:
        return False
    if not docs or not any(docs):
        return False

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as handle:
        handle.write(yaml_content)
        path = handle.name

    try:
        cmd = ["kubectl", "apply", "--dry-run=server", "-f", path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0 and "connection refused" not in result.stderr.lower():
            print(result.stderr, file=sys.stderr)
        return result.returncode == 0
    except FileNotFoundError:
        return True
    finally:
        os.unlink(path)


def _primary_cve(report: dict[str, Any]) -> str:
    vulns = report.get("report", {}).get("vulnerabilities", [])
    for severity in ("CRITICAL", "HIGH"):
        for vuln in vulns:
            if vuln.get("severity") == severity:
                return vuln.get("vulnerabilityID", "CVE-unknown")
    return vulns[0].get("vulnerabilityID", "remediation") if vulns else "remediation"


def _pr_already_open(gh_repo: Any, remediation_id: str) -> bool:
    branch = f"{PR_BRANCH_PREFIX}{remediation_id}"
    owner = gh_repo.owner.login
    for pr in gh_repo.get_pulls(state="open"):
        if pr.head.ref == branch or pr.head.ref.startswith(PR_BRANCH_PREFIX):
            print(f"PR déjà ouverte: {pr.html_url}")
            return True
    try:
        gh_repo.get_git_ref(f"heads/{branch}")
        print(f"Branche existante: {branch}")
        return True
    except Exception:
        return False


def open_pull_request(
    repo: str,
    path: str,
    fixed_yaml: str,
    sha: str,
    cve_id: str,
    explanation: str,
) -> str:
    if not GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN manquant")

    remediation_id = cve_id.replace("/", "-")
    gh_repo = Github(GITHUB_TOKEN).get_repo(repo)

    if _pr_already_open(gh_repo, remediation_id):
        raise RuntimeError(f"Une PR {PR_BRANCH_PREFIX}{remediation_id} existe déjà")

    branch_name = f"{PR_BRANCH_PREFIX}{remediation_id}"
    main_sha = gh_repo.get_git_ref("heads/main").object.sha
    gh_repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=main_sha)
    gh_repo.update_file(
        path=path,
        message=f"fix: remediate {cve_id}",
        content=fixed_yaml,
        sha=sha,
        branch=branch_name,
    )
    pr = gh_repo.create_pull(
        title=cve_id,
        body=explanation,
        head=branch_name,
        base="main",
    )
    return pr.html_url


def _select_report(reports: list[dict[str, Any]]) -> dict[str, Any] | None:
    for report in reports:
        name = report.get("metadata", {}).get("name", "")
        if "vulnerable-web" in name:
            return report
    return reports[0] if reports else None


def main() -> int:
    reports = get_vulnerability_reports(TARGET_NAMESPACE)
    report = _select_report(reports)
    if not report:
        print("Aucun VulnerabilityReport trouvé.")
        return 0

    summary = summarize_report(report)
    manifest, sha = get_manifest_from_github(GITHUB_REPO, MANIFEST_PATH)
    explanation, fixed_yaml = ask_ai_for_fix(summary, manifest)

    if not validate_yaml(fixed_yaml):
        print("Validation YAML échouée.", file=sys.stderr)
        return 1

    cve_id = _primary_cve(report)
    pr_url = open_pull_request(
        GITHUB_REPO, MANIFEST_PATH, fixed_yaml, sha, cve_id, explanation
    )
    print(f"PR créée: {pr_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
