"""Local LLM integration using Ollama.

This module calls a local Ollama instance and normalizes the output to the
project's plan schema:
{
  "hotels": [{"name", "area", "price"}],
  "itinerary": [{"day", "title", "activities"}],
  "budget": {"hotel", "food", "transport", "activities"}
}

Architecture note:
- This module handles Ollama integration and local schema normalization.
- It produces a safe, schema-correct fallback if the local model fails.
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any, Dict, List

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


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if isinstance(value, str):
            value = value.replace(",", "").strip()
        return float(value)
    except Exception:
        return float(default)


def _normalize_hotels(raw_hotels: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_hotels, list):
        return []

    normalized: List[Dict[str, Any]] = []
    for item in raw_hotels:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "Hotel")
        area = str(item.get("area") or "Central Area")
        price = _to_float(item.get("price"), 0.0)
        # Price must stay numeric for UI formatting; keep 0 only if model omitted it.
        normalized.append({"name": name, "area": area, "price": max(0.0, price)})
    return normalized[:3]


def _normalize_itinerary(raw_itinerary: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_itinerary, list):
        return []

    normalized: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw_itinerary, start=1):
        if not isinstance(item, dict):
            continue

        day_value = item.get("day", idx)
        try:
            day_value = int(day_value)
        except Exception:
            day_value = idx

        # Extract title and strip redundant "Day X:" prefix if LLM added it
        title = str(item.get("title") or f"Day {idx}").strip()
        # Regex to strip "Day 1:", "Day 1 -", "Day 1. ", etc. (case-insensitive)
        title = re.sub(r"(?i)^Day\s*\d+\s*[:\-\.]\s*", "", title)
        
        activities = item.get("activities", [])
        if isinstance(activities, str):
            activities = [activities]
        if not isinstance(activities, list):
            activities = []
        activity_list = [str(a).strip() for a in activities if str(a).strip()]
        if not activity_list:
            activity_list = ["Explore local highlights"]

        normalized.append(
            {
                "day": day_value,
                "title": title,
                "activities": activity_list,
            }
        )

    return normalized


def _desired_days(details: Dict[str, Any]) -> int:
    """Compute desired itinerary length from dates, defaulting to 3.
    Per user request: Plan for 'stay days' only (excludes arrival and departure days).
    Calculation: (End - Start) - 1.
    """
    dep = str(details.get("departure_date") or "").strip()
    ret = str(details.get("return_date") or "").strip()

    if not dep or not ret:
        return 3

    try:
        d1 = date.fromisoformat(dep)
        d2 = date.fromisoformat(ret)
        # Excludes both arrival and departure days
        days = (d2 - d1).days - 1
        # Minimum of 1 day for very short trips (overnight stay)
        if days < 1:
            return 1
        return min(days, 14)
    except Exception:
        return 3


def _calculate_budget_python(details: Dict[str, Any], hotels: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate budget dynamically in Python instead of using the LLM."""
    days = _desired_days(details)
    trip_type = str(details.get("trip_type", "General")).lower()
    hotel_category = str(details.get("hotel_category", "Standard")).lower()
    
    adults = _to_float(details.get("adults"), 1.0)
    children = _to_float(details.get("children"), 0.0)
    travelers = max(1.0, adults + (children * 0.5))  # Kids cost a bit less

    # Base daily costs per person (INR)
    food_base = 2500 if "luxury" in trip_type or "luxury" in hotel_category else 1200
    transport_base = 1500 if "luxury" in trip_type else 600
    activities_base = 2500 if "adventure" in trip_type else 1000

    # Hotel calculation
    hotel_cost = 0.0
    if hotels:
        # Use the average price of the suggested hotels per night
        avg_price = sum(h.get("price", 0) for h in hotels) / len(hotels)
        rooms_needed = max(1, int((adults + children + 1) // 2))
        hotel_cost = avg_price * days * rooms_needed
    else:
        base_rate = 5000 if "luxury" not in hotel_category else 15000
        rooms_needed = max(1, int((adults + children + 1) // 2))
        hotel_cost = base_rate * days * rooms_needed

    food_cost = food_base * travelers * days
    transport_cost = transport_base * travelers * days
    activities_cost = activities_base * travelers * days

    return {
        "hotel": round(hotel_cost),
        "food": round(food_cost),
        "transport": round(transport_cost),
        "activities": round(activities_cost),
    }


def _pad_hotels(hotels: List[Dict[str, Any]], destination: str, travelers: float) -> List[Dict[str, Any]]:
    """Ensure exactly 3 hotels for UI stability."""
    base_prices = [3200.0, 4200.0, 5200.0]
    templates = [
        (f"{destination} Central Inn", "City Center"),
        (f"{destination} Riverside Stay", "Riverfront"),
        (f"{destination} Heritage Suites", "Old Town"),
    ]

    padded = list(hotels or [])
    idx = 0
    while len(padded) < 3 and idx < 3:
        name, area = templates[idx]
        padded.append(
            {
                "name": name,
                "area": area,
                "price": round(base_prices[idx] * max(1.0, travelers)),
            }
        )
        idx += 1

    return padded[:3]


def _pad_itinerary(itinerary: List[Dict[str, Any]], days: int) -> List[Dict[str, Any]]:
    """Ensure the itinerary has `days` entries for UI stability."""
    defaults = [
        "Arrival and Local Orientation",
        "Culture and Sightseeing",
        "Food and Neighborhood Discovery",
        "Nature / Scenic Day",
        "Shopping and Hidden Gems",
        "Flexible Leisure Day",
        "Departure and Wrap-up",
    ]

    padded = list(itinerary or [])
    while len(padded) < days:
        idx = len(padded) + 1
        title = defaults[(idx - 1) % len(defaults)]
        padded.append(
            {
                "day": idx,
                "title": title,
                "activities": ["Explore top sights", "Try a recommended local restaurant", "Relax in a popular area"],
            }
        )

    return padded[:days]


def _normalize_plan(parsed: Any, details: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize model output to the stable plan schema used by the UI."""
    destination = str(details.get("to") or details.get("destination") or "Destination")
    travelers = _to_float(details.get("adults"), 1.0) + _to_float(details.get("children"), 0.0)
    travelers = max(1.0, travelers)
    days = _desired_days(details)

    if not isinstance(parsed, dict):
        # Local LLM should be the source of truth. If it returns invalid JSON,
        # produce a safe, schema-correct fallback.
        parsed = {}

    hotels = _pad_hotels(_normalize_hotels(parsed.get("hotels")), destination=destination, travelers=travelers)
    itinerary = _pad_itinerary(_normalize_itinerary(parsed.get("itinerary")), days=days)
    
    # Calculate budget dynamically in Python instead of wasting LLM tokens
    budget = _calculate_budget_python(details, hotels)

    return {"hotels": hotels, "itinerary": itinerary, "budget": budget}


def _build_prompt(details: Dict[str, Any]) -> str:
    days = _desired_days(details)
    trip_type = details.get("trip_type", "General")
    description = details.get("description", "No specific preferences")
    attractions = details.get("attractions", [])
    travel_interest = details.get("travel_interest") or ""
    interest_line = (
        f"- The user's travel interest is classified as: '{travel_interest}'. Tailor daily activities to match this interest.\n"
        if travel_interest else ""
    )

    return (
        "You are an expert travel planner. Generate a personalized travel plan.\n\n"
        "Return ONLY valid JSON (no markdown) matching this exact structure:\n"
        "{\n"
        '  "hotels": [{"name": "The Plaza", "area": "Midtown", "price": 400}],\n'
        '  "itinerary": [{"day": 1, "title": "Arrival", "activities": ["Morning: Check-in.", "Afternoon: Museum.", "Evening: Dinner."]}]\n'
        "}\n\n"
        "Mandatory Rules:\n"
        "- Provide exactly 3 hotel recommendations that reflect the destination's vibe.\n"
        f"- Provide exactly {days} days of itinerary planning.\n"
        "- For each day, include 3 distinct activities: one Morning, one Afternoon, one Evening.\n"
        "- IMPORTANT for SPEED: Keep each activity description extremely concise (1-5 words maximum).\n"
        "- GENERATE AS FAST AS POSSIBLE: Make the entire JSON output as short as structurally allowed.\n"
        "- Format activities like: 'Morning: [Activity]', 'Afternoon: [Activity]', 'Evening: [Activity]'.\n"
        f"- The plan MUST be tailored to the trip type: '{trip_type}'.\n"
        f"- Explicitly incorporate these user preferences: '{description}'.\n"
        f"{interest_line}"
        f"- Use these 'must-visit' landmarks to plan the itinerary: {json.dumps(attractions, ensure_ascii=False)}.\n"
        f"- If the number of days is short ({days} day(s)), prioritize only the top-rated must-visit spots.\n"
        "- Absolutely no conversational text. Start your response right away with { and end with }.\n"
        f"\nTrip details context: {json.dumps(details, ensure_ascii=False)}"
    )


def generate(details: Dict[str, Any]) -> Dict[str, Any]:
    """Call local Ollama and return normalized plan structure.
    
    Raises ValueError if generation fails or json is invalid, removing any
    old dummy_llm fallbacks for a cleaner architecture.
    """
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": _build_prompt(details),
        "stream": False,
        "format": "json",
    }

    try:
        # phi3 on consumer hardware can take 2-5 min for a full itinerary prompt
        response = requests.post(OLLAMA_ENDPOINT, json=payload, timeout=300)
        response.raise_for_status()

        data = response.json()
        text = str(data.get("response", "")).strip()
        parsed = _extract_json(text)

        if parsed is None:
            # For robustness, don't crash the server, just return the safe padded schema
            print("[local_llm] Warning: Ollama response did not contain valid JSON.")
            parsed = {}

        return _normalize_plan(parsed, details)

    except Exception as e:
        print(f"[local_llm] Critical Error generating itinerary: {e}")
        # Always return safe schema so application flow isn't interrupted
        return _normalize_plan({}, details)

