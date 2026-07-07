#!/usr/bin/env python3
"""Test isolé Phase 8 — appel OVH AI Endpoints."""

import json
import os
import sys

from openai import OpenAI, PermissionDeniedError

from env_loader import load_repo_env

OVH_TOKEN_HELP = """
Erreur 403 : le token OVH AI Endpoints est invalide ou expiré.

Ce n'est PAS le token GitHub ni le fichier token.txt du hackathon.
Il faut une « API access key » créée dans le manager OVH :

  Public Cloud → AI & Machine Learning → AI Endpoints → API keys
  → « Create a new API key »

Copie la clé dans .env (format attendu) :
  OVH_AI_TOKEN: <api_key>

Puis relance : .venv/bin/python test_ai.py
"""


def main() -> int:
    load_repo_env()

    base_url = os.environ.get(
        "OVH_AI_BASE_URL", "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1"
    )
    model = os.environ.get("OVH_AI_MODEL", "Qwen3-Coder-30B-A3B-Instruct")
    token = os.environ.get("OVH_AI_TOKEN")
    if not token:
        print(
            "OVH_AI_TOKEN manquant — renseigne-le dans ../../.env",
            file=sys.stderr,
        )
        return 1

    client = OpenAI(api_key=token, base_url=base_url)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ça marche ?"}],
            max_tokens=64,
        )
    except PermissionDeniedError:
        print(OVH_TOKEN_HELP, file=sys.stderr)
        return 1

    payload = response.model_dump()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    content = payload["choices"][0]["message"]["content"]
    print(f"\nRéponse: {content}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
