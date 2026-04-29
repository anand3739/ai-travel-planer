"""Quick health-check for Ollama / phi3 – tests IATA and attractions prompts."""
import requests
import time
import json
import re

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "phi3"


def call(prompt: str, timeout: int = 45) -> tuple[str, float]:
    start = time.time()
    r = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "prompt": prompt, "stream": False, "format": "json"},
        timeout=timeout,
    )
    r.raise_for_status()
    elapsed = round(time.time() - start, 1)
    return r.json().get("response", "").strip(), elapsed


def extract_json(text: str):
    cleaned = text.strip().lstrip("`").strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", cleaned)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return None


print("=" * 50)
print(" Ollama / phi3 Health Check")
print("=" * 50)

# ── Test 1: IATA ──────────────────────────────────
print("\n[1] IATA resolution  →  Hyderabad")
IATA_PROMPT = (
    "You are an expert at identifying airport IATA codes for any city worldwide.\n"
    "Find the IATA code for the closest major airport near: Hyderabad\n"
    'Return ONLY valid JSON (no markdown). Example: { "iata": "JFK" }\n'
    "Rules:\n"
    "- IATA must be exactly 3 uppercase letters.\n"
    '- If unknown return { "iata": "" }\n'
    "- Start your response with {\n"
)
try:
    text, t = call(IATA_PROMPT)
    parsed = extract_json(text)
    iata = (parsed or {}).get("iata", "")
    status = "✅ PASS" if re.fullmatch(r"[A-Z]{3}", iata or "") else "⚠️  WARN – unexpected value"
    print(f"  Raw     : {text[:120]}")
    print(f"  Parsed  : {parsed}")
    print(f"  IATA    : {iata!r}")
    print(f"  Time    : {t}s")
    print(f"  Result  : {status}")
except Exception as e:
    print(f"  ❌ FAIL – {e}")

# ── Test 2: Attractions ───────────────────────────
print("\n[2] Attractions  →  Dubai")
ATTR_PROMPT = (
    "You are a local guide for Dubai.\n"
    'Return ONLY valid JSON (no markdown) with this exact schema: { "attractions": ["string"] }\n'
    "Rules:\n"
    "- Provide exactly 5 attraction ideas.\n"
    "- Keep them short and specific.\n"
    "- Absolutely no conversational text. Start your response with {\n"
    "City: Dubai\n"
)
try:
    text2, t2 = call(ATTR_PROMPT)
    parsed2 = extract_json(text2)
    items = (parsed2 or {}).get("attractions", [])
    status2 = "✅ PASS" if isinstance(items, list) and len(items) >= 3 else "⚠️  WARN – fewer than 3 items"
    print(f"  Raw     : {text2[:200]}")
    print(f"  Items   : {items}")
    print(f"  Count   : {len(items)}")
    print(f"  Time    : {t2}s")
    print(f"  Result  : {status2}")
except Exception as e:
    print(f"  ❌ FAIL – {e}")

# ── Test 3: Itinerary (mini) ──────────────────────
print("\n[3] Itinerary generation  →  Dubai, 1 day")
ITIN_PROMPT = (
    "You are an expert travel planner. Generate a 1-day travel plan for Dubai.\n"
    "Return ONLY valid JSON (no markdown) matching this exact structure:\n"
    '{ "hotels": [{"name": "X", "area": "Y", "price": 100}], '
    '"itinerary": [{"day": 1, "title": "Arrival", "activities": ["Morning: Check-in.", "Afternoon: Museum.", "Evening: Dinner."]}] }\n'
    "Rules:\n"
    "- Provide exactly 3 hotels and exactly 1 day itinerary.\n"
    "- Keep each field very short.\n"
    "- Absolutely no conversational text. Start your response with {\n"
)
try:
    text3, t3 = call(ITIN_PROMPT, timeout=60)
    parsed3 = extract_json(text3)
    hotels = (parsed3 or {}).get("hotels", [])
    itin = (parsed3 or {}).get("itinerary", [])
    ok = isinstance(hotels, list) and len(hotels) >= 1 and isinstance(itin, list) and len(itin) >= 1
    status3 = "✅ PASS" if ok else "⚠️  WARN – incomplete schema"
    print(f"  Hotels  : {hotels}")
    print(f"  Itin    : {itin}")
    print(f"  Time    : {t3}s")
    print(f"  Result  : {status3}")
except Exception as e:
    print(f"  ❌ FAIL – {e}")

print("\n" + "=" * 50)
print(" Done")
print("=" * 50)
