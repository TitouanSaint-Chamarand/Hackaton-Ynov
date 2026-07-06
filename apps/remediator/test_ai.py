#!/usr/bin/env python3
"""Test isolé Phase 8 — appel OVH AI Endpoints."""

import json
import os
import sys

from openai import OpenAI


def main() -> int:
    base_url = os.environ.get(
        "OVH_AI_BASE_URL", "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1"
    )
    model = os.environ.get("OVH_AI_MODEL", "Qwen3-Coder-30B-A3B-Instruct")
    token = os.environ.get("OVH_AI_TOKEN")
    if not token:
        print("OVH_AI_TOKEN manquant", file=sys.stderr)
        return 1

    client = OpenAI(api_key=token, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "ça marche ?"}],
        max_tokens=64,
    )
    payload = response.model_dump()
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    content = payload["choices"][0]["message"]["content"]
    print(f"\nRéponse: {content}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
