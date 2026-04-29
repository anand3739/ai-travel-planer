"""IATA resolution using local Ollama (Phi-3).

Used as a primary path to map user-entered city names (misspellings, local names, common names, etc.) to valid IATA airport codes before falling back to Amadeus.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

import requests
from services.ollama_config import OLLAMA_ENDPOINT, OLLAMA_MODEL


def _extract_json(text: str) -> Any:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "```").strip("`").strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _build_prompt(city_name: str) -> str:
    return (
        "You are an expert at identifying airport codes for any city, town, or region worldwide.\n"
        "Find the IATA code for the closest major airport near the input, even if the city name is misspelled, abbreviated, or informal.\n"
        "Return ONLY valid JSON (no markdown).\n"
        "Example Output:\n"
        '{ "iata": "JFK" }\n'
        "Rules:\n"
        "- IATA must be exactly 3 uppercase letters.\n"
        "- Always return the IATA code of the closest major airport, even for misspelled or partial city names.\n"
        "- Prefer the IATA *city* code when the city has multiple airports (e.g. NYC for New York, LON for London).\n"
        '- If you genuinely cannot identify any nearby airport, return { "iata": "" }.\n'
        "- GENERATE AS FAST AS POSSIBLE. Make the JSON as short as structurally allowed.\n"
        "- Absolutely no conversational text. Start your response with {.\n"
        f"City input: {city_name}\n"
    )


def resolve_city_to_iata(city_name: str) -> Optional[str]:
    try:
        payload: Dict[str, Any] = {"model": OLLAMA_MODEL, "prompt": _build_prompt(city_name), "stream": False, "format": "json"}
        response = requests.post(OLLAMA_ENDPOINT, json=payload, timeout=120)
        response.raise_for_status()

        data = response.json()
        text = str(data.get("response", "")).strip()
        parsed = _extract_json(text)
        if not isinstance(parsed, dict):
            return None

        iata = str(parsed.get("iata") or "").strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", iata):
            return None
        return iata
    except Exception as e:
        print(f"[local_iata] Ollama unavailable or slow: {e}")
        return None

