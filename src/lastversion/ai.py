"""OpenAI-powered helpers for generating RPM changelog summaries.

This module intentionally uses only OpenAI's API (no local heuristics) to
summarize upstream release notes into concise bullets suitable for RPM
%changelog entries.
"""

import json
import os
from typing import List, Optional

import requests


def _get_openai_api_key() -> Optional[str]:
    return os.getenv("LASTVERSION_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")


def _get_openai_model() -> str:
    return os.getenv("LASTVERSION_OPENAI_MODEL", "gpt-4o-mini")


def generate_changelog(raw_notes: str, context: dict) -> Optional[List[str]]:
    """Generate a concise bullet list from upstream release notes using OpenAI.

    Args:
        raw_notes: Upstream release notes/description (markdown/plain).
        context: Minimal context like {"repo": str, "tag": str, "version": str}.
        bullets: Target number of bullets (3-7 permitted).

    Returns:
        List of bullet strings (without leading dashes), or None on failure.
    """
    api_key = _get_openai_api_key()
    if not api_key:
        return None

    # Soft cap on input size to keep latency/token usage reasonable
    if isinstance(raw_notes, str) and len(raw_notes) > 16000:
        raw_notes = raw_notes[:16000]

    system_prompt = (
        "You are an expert RPM packager changelog writer. Summarize upstream "
        "release notes into concise, distribution-friendly entries."
    )

    user_prompt = (
        "Summarize the upstream changes for an RPM %changelog entry.\n"
        "- Output a JSON object with key 'bullets' mapping to an array.\n"
        "- 1 to 7 bullets, each <= 20 words.\n"
        "- Focus on user-facing changes, fixes, security, compatibility, and build/system impacts.\n"
        "- Avoid author names, PR/issue numbers, links, emojis, and hype.\n"
        "- No code fences or extra text; only JSON.\n\n"
        f"Context: {json.dumps(context, ensure_ascii=False)}\n\n"
        f"Release notes:\n{raw_notes}"
    )

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": _get_openai_model(),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.0,
                "max_tokens": 600,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "changelog_bullets",
                        "schema": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "bullets": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "minItems": 1,
                                    "maxItems": 7,
                                }
                            },
                            "required": ["bullets"],
                        },
                        "strict": True,
                    },
                },
            },
            timeout=30,
        )
        if response.status_code == 200:
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            try:
                obj = json.loads(content)
                bullets_list = obj.get("bullets") if isinstance(obj, dict) else None
                if isinstance(bullets_list, list):
                    cleaned: List[str] = []
                    for item in bullets_list[:7]:
                        if isinstance(item, str):
                            s = item.strip()
                            if s.startswith("- "):
                                s = s[2:].strip()
                            elif s.startswith("• "):
                                s = s[2:].strip()
                            if s:
                                cleaned.append(s)
                    if cleaned:
                        return cleaned
            except json.JSONDecodeError:
                return None
        return None
    except Exception:
        return None
