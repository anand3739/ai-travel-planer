"""Attractions generation using local Ollama.

Local mode requirement:
- Use local Ollama (llama3) to generate attractions (no external attractions API).
- Falls back to a static curated list when Ollama is unavailable.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

import requests
from services.ollama_config import OLLAMA_ENDPOINT, OLLAMA_MODEL

# ---------- Static curated fallback (no Ollama required) ----------
STATIC_ATTRACTIONS: Dict[str, List[str]] = {
    "dubai": ["Burj Khalifa", "Dubai Mall", "Palm Jumeirah", "Dubai Creek", "Desert Safari"],
    "singapore": ["Marina Bay Sands", "Gardens by the Bay", "Sentosa Island", "Clarke Quay", "Orchard Road"],
    "london": ["Big Ben & Parliament", "Tower of London", "British Museum", "Buckingham Palace", "Hyde Park"],
    "paris": ["Eiffel Tower", "Louvre Museum", "Notre-Dame Cathedral", "Champs-Élysées", "Versailles Palace"],
    "new york": ["Statue of Liberty", "Central Park", "Times Square", "Metropolitan Museum of Art", "Brooklyn Bridge"],
    "tokyo": ["Senso-ji Temple", "Shibuya Crossing", "Tsukiji Market", "Akihabara", "Mount Fuji Day Trip"],
    "bangkok": ["Grand Palace", "Wat Pho", "Chatuchak Market", "Floating Markets", "Khao San Road"],
    "bali": ["Uluwatu Temple", "Tegalalang Rice Terraces", "Kuta Beach", "Ubud Monkey Forest", "Mount Batur"],
    "delhi": ["Red Fort", "Qutub Minar", "Humayun's Tomb", "India Gate", "Lotus Temple"],
    "mumbai": ["Gateway of India", "Marine Drive", "Elephanta Caves", "Chhatrapati Shivaji Terminus", "Juhu Beach"],
    "bangalore": ["Lalbagh Botanical Garden", "Cubbon Park", "Bangalore Palace", "ISKCON Temple", "Nandi Hills"],
    "hyderabad": ["Charminar", "Golconda Fort", "Hussain Sagar Lake", "Salar Jung Museum", "Ramoji Film City"],
    "chennai": ["Marina Beach", "Kapaleeshwarar Temple", "Fort St. George", "Government Museum", "Mahabalipuram"],
    "kolkata": ["Victoria Memorial", "Howrah Bridge", "Dakshineswar Kali Temple", "Indian Museum", "Park Street"],
    "goa": ["Baga Beach", "Old Goa Churches", "Dudhsagar Falls", "Anjuna Flea Market", "Fort Aguada"],
    "jaipur": ["Amber Fort", "Hawa Mahal", "City Palace", "Jantar Mantar", "Nahargarh Fort"],
    "amsterdam": ["Rijksmuseum", "Anne Frank House", "Van Gogh Museum", "Vondelpark", "Canal Cruises"],
    "rome": ["Colosseum", "Vatican Museums", "Trevi Fountain", "Roman Forum", "Pantheon"],
    "barcelona": ["Sagrada Família", "Park Güell", "La Rambla", "Barceloneta Beach", "Camp Nou"],
    "istanbul": ["Hagia Sophia", "Grand Bazaar", "Topkapi Palace", "Bosphorus Cruise", "Blue Mosque"],
    "sydney": ["Sydney Opera House", "Bondi Beach", "Harbour Bridge Climb", "Blue Mountains", "Taronga Zoo"],
    "doha": ["Museum of Islamic Art", "Souq Waqif", "The Pearl-Qatar", "Katara Cultural Village", "Al Zubarah Fort"],
    "singapore": ["Marina Bay Sands", "Gardens by the Bay", "Sentosa Island", "Clarke Quay", "Orchard Road"],
    "kuala lumpur": ["Petronas Twin Towers", "Batu Caves", "KL Bird Park", "Central Market", "Bukit Bintang"],
    "hong kong": ["Victoria Peak", "Temple Street Night Market", "Disneyland Hong Kong", "Ocean Park", "Big Buddha (Lantau)"],
    "cairo": ["Pyramids of Giza", "Egyptian Museum", "Khan el-Khalili Bazaar", "Sphinx", "Luxor Day Trip"],
    "nairobi": ["Nairobi National Park", "David Sheldrick Wildlife Trust", "Karen Blixen Museum", "Giraffe Centre", "Bomas of Kenya"],
    "johannesburg": ["Apartheid Museum", "Soweto Township Tour", "Gold Reef City", "Constitution Hill", "Lion & Safari Park"],
}


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


def _build_prompt(city: str) -> str:
    return (
        f"You are a local guide for {city}.\n"
        "Return ONLY valid JSON (no markdown) with this exact schema:\n"
        '{ "attractions": ["string"] }\n'
        "Rules:\n"
        "- Provide exactly 5 attraction ideas.\n"
        "- Keep them short and specific. GENERATE AS FAST AS POSSIBLE.\n"
        "- Absolutely no conversational text. Start your response with {.\n"
        f"City: {city}\n"
    )


def generate(city: str) -> List[str]:
    """Return 5 attraction names for a city.

    Priority:
    1. Local Ollama (dynamic, personalised)
    2. Static curated list (offline fallback for popular cities)
    3. Empty list (caller handles gracefully)
    """
    try:
        payload: Dict[str, Any] = {
            "model": OLLAMA_MODEL,
            "prompt": _build_prompt(city),
            "stream": False,
        }
        response = requests.post(OLLAMA_ENDPOINT, json=payload, timeout=120)
        response.raise_for_status()

        data = response.json()
        text = str(data.get("response", "")).strip()
        parsed = _extract_json(text)
        if not isinstance(parsed, dict):
            raise ValueError("Ollama returned non-JSON response")

        items = parsed.get("attractions", [])
        if isinstance(items, str):
            items = [items]
        if not isinstance(items, list):
            raise ValueError("Ollama attractions not a list")
        names = [str(x).strip() for x in items if str(x).strip()]
        if names:
            return names[:5]
        raise ValueError("Ollama returned empty attractions list")

    except Exception as e:
        print(f"[local_attractions] Ollama unavailable: {e}")
        # Use static curated list for popular cities
        static = STATIC_ATTRACTIONS.get(city.strip().lower())
        if static:
            print(f"[local_attractions] Using static fallback for '{city}'")
            return static
        return []

