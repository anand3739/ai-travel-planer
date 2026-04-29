import os
import logging
import re
from html import unescape
from typing import Any, Dict, Optional, Tuple

import httpx
import asyncio
from services.local_attractions import generate as generate_attractions
from services.cache import get_cache, set_cache, generate_cache_key

logger = logging.getLogger(__name__)


def _weather_code_label(code: Any) -> str:
    """Map Open-Meteo/WMO weather codes to friendly labels."""
    try:
        c = int(code)
    except Exception:
        return "Unknown"

    mapping = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        56: "Light freezing drizzle",
        57: "Dense freezing drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Light freezing rain",
        67: "Heavy freezing rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail",
    }
    return mapping.get(c, "Unknown")


async def _get_city_coordinates(city: str) -> Optional[Tuple[float, float]]:
    geo_url = "https://geocoding-api.open-meteo.com/v1/search"
    geo_params = {"name": city, "count": 1, "language": "en", "format": "json"}
    async with httpx.AsyncClient() as client:
        geo_response = await client.get(geo_url, params=geo_params, timeout=8)
        geo_response.raise_for_status()
        geo_data = geo_response.json()

    results = geo_data.get("results", [])
    if not results:
        return None

    location = results[0]
    return float(location["latitude"]), float(location["longitude"])


def _strip_html(text: str) -> str:
    plain = re.sub(r"<[^>]+>", "", text or "")
    return unescape(plain).strip()


def _destination_info_fallback(city: str) -> Dict[str, Any]:
    return {
        "title": city,
        "description": f"Travel destination information for {city}.",
        "wiki_url": f"https://en.wikipedia.org/wiki/{city.replace(' ', '_')}",
    }


# ============ WEATHER API ============
async def get_weather(city: str) -> Dict[str, Any]:
    """Fetch weather data using Open-Meteo (free, no API key required)."""

    # Caching check
    cache_key = generate_cache_key("get_weather", {"city": city})
    cached_res = get_cache(cache_key)
    if cached_res:
        print(f"⚡ Using cache (Weather): {city}")
        return cached_res

    print(f"🌍 Fetching fresh data (Weather): {city}")
    try:
        coordinates = await _get_city_coordinates(city)
        if not coordinates:
            return {"error": "City not found"}
        lat, lon = coordinates

        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "auto",
        }
        async with httpx.AsyncClient() as client:
            weather_response = await client.get(weather_url, params=weather_params, timeout=8)
            weather_response.raise_for_status()
            weather_data = weather_response.json()

        current = weather_data.get("current", {})
        daily = weather_data.get("daily", {})

        code = current.get("weather_code", 0)
        result = {
            "city": city,
            "temperature": round(float(current.get("temperature_2m", 0.0))),
            "humidity": round(float(current.get("relative_humidity_2m", 0.0))),
            "condition": code,
            "condition_label": _weather_code_label(code),
            "max_temp": round(float(daily.get("temperature_2m_max", [0.0])[0])),
            "min_temp": round(float(daily.get("temperature_2m_min", [0.0])[0])),
            "timezone": weather_data.get("timezone", "UTC"),
        }
        set_cache(cache_key, result)
        return result
    except Exception as e:
        logger.warning("Weather API Error: %s", e)
        return {"error": str(e)}


# ============ DESTINATION INFO ============
async def get_destination_info(city: str) -> Dict[str, Any]:
    """Fetch destination info from Wikipedia API with multi-paragraph extract."""

    wiki_headers = {
        "User-Agent": "AITravelAgent/1.0 (https://github.com/nirbar1985/ai-travel-agent; ai-travel-agent@example.com)",
        "Accept": "application/json",
    }
    try:
        # Step 1: Search for the page
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": city,
            "format": "json",
            "srlimit": 1,
        }
        async with httpx.AsyncClient(headers=wiki_headers, timeout=10) as client:
            search_response = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params=search_params,
            )
            search_response.raise_for_status()
            items = search_response.json().get("query", {}).get("search", [])
            if not items:
                return _destination_info_fallback(city)

            title = items[0].get("title", city)
            encoded_title = title.replace(" ", "_")

            # Step 2: Fetch full intro extract (multiple paragraphs, up to ~15 sentences)
            extract_params = {
                "action": "query",
                "titles": title,
                "prop": "extracts",
                "exintro": True,
                "explaintext": True,
                "exsentences": 15,
                "format": "json",
                "redirects": 1,
            }
            extract_response = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params=extract_params,
            )
            extract_response.raise_for_status()
            pages = extract_response.json().get("query", {}).get("pages", {})
            page_id = next(iter(pages.keys()), None)
            if page_id and page_id != "-1":
                extract = pages[page_id].get("extract", "").strip()
                if extract:
                    return {
                        "title": title,
                        "description": extract,
                        "wiki_url": f"https://en.wikipedia.org/wiki/{encoded_title}",
                    }

            # Fallback: use search snippet if extract failed
            snippet = _strip_html(items[0].get("snippet", "No description available"))
            return {
                "title": title,
                "description": snippet or "No description available",
                "wiki_url": f"https://en.wikipedia.org/wiki/{encoded_title}",
            }
    except Exception as e:
        logger.warning("Destination info fallback used for %s: %s", city, e)
        return _destination_info_fallback(city)


# ============ ATTRACTIONS ============
async def get_attractions(city: str) -> Dict[str, Any]:
    """Get attractions using local LLM."""

    # Caching check
    cache_key = generate_cache_key("get_attractions", {"city": city})
    cached_res = get_cache(cache_key)
    if cached_res:
        print(f"⚡ Using cache (Attractions): {city}")
        if isinstance(cached_res, list):
            return {"city": city, "attractions": cached_res}
        return cached_res

    print(f"🌍 Fetching fresh data (Attractions): {city}")
    try:
        # Assuming generate_attractions is synchronous or needs run_in_executor
        names = await asyncio.to_thread(generate_attractions, city)
        result = {"city": city, "attractions": names or []}
        set_cache(cache_key, result)
        return result
    except Exception as e:
        logger.warning("Attractions Error: %s", e)
        return {"city": city, "attractions": []}


# ============ SYNC WRAPPERS (for use inside threads / non-async code) ============
def get_attractions_sync(city: str) -> Dict[str, Any]:
    """Sync wrapper around get_attractions — safe to call from agent.py running in a thread."""
    return asyncio.run(get_attractions(city))


def get_weather_sync(city: str) -> Dict[str, Any]:
    """Sync wrapper around get_weather — safe to call from threads."""
    return asyncio.run(get_weather(city))


def get_destination_info_sync(city: str) -> Dict[str, Any]:
    """Sync wrapper around get_destination_info — safe to call from threads."""
    return asyncio.run(get_destination_info(city))
