# API-to-Function Mapping

This document describes **which external API is used for which function** in the AI Travel Planner application.

---

## 1. Flights Search

| Function | File | API | Purpose |
|----------|------|-----|---------|
| **Flight search** | `flights_service.py` | **Duffel API & Booking.com** | Search real flight options (outbound & return) |
| **City → IATA code** | `flights_service.py` | **Local Ollama** | Convert city names to airport codes |

**Flight APIs used:**
- Duffel API (`https://api.duffel.com/air/offer_requests`) (Primary)
- Booking.com Flights API (Fallback)

**Credentials:** `DUFFEL_ACCESS_TOKEN` in `.env`

---

## 2. AI-Powered Suggestions (Hotels, Itinerary, Attractions)

| Function | File | API | Purpose |
|----------|------|-----|---------|
| **Hotel suggestions** | `services/local_llm.py` | **Local Ollama** | Generate structured hotel suggestions |
| **Itinerary & budget** | `agent.py` | **Local Ollama** | Generate day-by-day itinerary and budget breakdown |
| **Attractions** | `api_utils.py` | **Local Ollama** | List attraction ideas near the destination |

**Model:** `phi3` (configurable in `services/ollama_config.py`)
**Endpoint:** `http://localhost:11434/api/generate`

---

## 3. Weather

| Function | File | API | Purpose |
|----------|------|-----|---------|
| **Weather forecast** | `api_utils.py` | **Open-Meteo API** | Current temperature, humidity, min/max temps |
| **City coordinates** | `api_utils.py` | **Open-Meteo Geocoding API** | Convert city name to lat/lon for weather |

**Endpoints:**
- `https://geocoding-api.open-meteo.com/v1/search`
- `https://api.open-meteo.com/v1/forecast`

---

## 4. Destination Information

| Function | File | API | Purpose |
|----------|------|-----|---------|
| **Destination description** | `api_utils.py` | **Wikipedia MediaWiki API** | Text about the destination city |

---

## Summary Table

| Feature | Provider | Credentials Required |
|---------|----------|----------------------|
| Flights | Duffel, Booking.com | `DUFFEL_ACCESS_TOKEN` |
| AI Generation | Local Ollama | None (requires local Ollama instance) |
| Weather | Open-Meteo | None |
| Destination info | Wikipedia | None |
| Email Sending | SendGrid | `SENDGRID_API_KEY`, `SENDER_EMAIL` |
