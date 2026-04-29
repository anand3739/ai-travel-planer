"""
AI Travel Agent Module

Orchestrates the travel planning workflow by:
1. Validating user input
2. Fetching real-time data (IATA codes, attractions)
3. Running AI generation and flight search in parallel
4. Combining results for complete travel plan

Uses:
- Local LLM for itinerary generation
- Amadeus API for flights
- Real attractions data
- ML-based interest classification
- ML-based city recommendations
"""

from flights_service import get_flights
from services.local_llm import generate as generate_summary


def run_travel_agent(
    from_location,
    to_location,
    depart_date,
    return_date,
    adults,
    children,
    trip_type,
    stay_type,
    hotel_category,
    description,
    travel_interest=None,
):
    """
    Run the complete travel planning agent.

    Args:
        from_location (str): Departure city
        to_location (str): Destination city
        depart_date (str): Departure date (YYYY-MM-DD)
        return_date (str): Return date (YYYY-MM-DD, optional)
        adults (int): Number of adults
        children (int): Number of children
        trip_type (str): Type of trip (solo, family, friends, etc.)
        stay_type (str): Type of accommodation
        hotel_category (str): Hotel category (budget, mid, luxury)
        description (str): User's travel description/preferences
        travel_interest (str, optional): ML-classified travel interest

    Returns:
        dict: Complete travel plan with AI itinerary and flights
    """

    # 🔹 Fetch real attractions context for the AI
    # (Move import inside to avoid top-level circular dependencies)
    from api_utils import get_attractions_sync
    attractions_data = get_attractions_sync(to_location)
    attractions_list = attractions_data.get("attractions", [])

    # 🔹 Prepare user details + attractions
    details = {
        "from": from_location,
        "to": to_location,
        "departure_date": depart_date,
        "return_date": return_date,
        "adults": adults,
        "children": children,
        "trip_type": trip_type,
        "stay_type": stay_type,
        "hotel_category": hotel_category,
        "description": description,
        "attractions": attractions_list,
        "travel_interest": travel_interest,
    }

    # 🔹 Protect Local AI: Pre-fetch IATA codes sequentially.
    # If the flight search (which needs IATA codes) hits the AI at the same time 
    # as the itinerary generation, Ollama will crash on consumer hardware.
    from flights_service import get_iata_code
    print("⏳ Pre-fetching IATA codes sequentially to prevent AI overload...")
    get_iata_code(from_location)
    get_iata_code(to_location)

    # 🔹 Generate AI itinerary & Get flights Parallelly
    from concurrent.futures import ThreadPoolExecutor
    
    print(f"🚀 Starting parallel tasks for {to_location}...")
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Task 1: AI generation (Heavy Local Hardware)
        future_ai = executor.submit(generate_summary, details)
        
        # Task 2: Flight search (Fast Network Call, IATA already cached)
        future_flights = executor.submit(
            get_flights,
            from_location,
            to_location,
            depart_date,
            return_date,
            adults
        )

        # Collect results as they finish
        ai_data = future_ai.result()
        flights = future_flights.result()

    print(f"✅ Parallel tasks completed for {to_location}.")

    # 🔹 Return structured result
    return {
        "details": details,
        "ai_data": ai_data,
        "flights": flights
    }
