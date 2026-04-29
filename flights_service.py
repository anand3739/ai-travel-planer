from dotenv import load_dotenv
from datetime import datetime
import os
import requests

# Load safe defaults first, then allow local overrides (matches main.py)
load_dotenv(".env", override=False)
load_dotenv(".env.local", override=True)

# ---------------- AIRLINE INFO ----------------
AIRLINE_INFO = {
    # Indian carriers
    "AI": "Air India",
    "6E": "IndiGo",
    "UK": "Vistara",
    "SG": "SpiceJet",
    "G8": "Go First",
    "IX": "Air India Express",
    "I5": "Air Asia India",
    "QP": "Akasa Air",
    # Major international
    "EK": "Emirates",
    "EY": "Etihad Airways",
    "QR": "Qatar Airways",
    "SQ": "Singapore Airlines",
    "TG": "Thai Airways",
    "BA": "British Airways",
    "LH": "Lufthansa",
    "AF": "Air France",
    "KL": "KLM",
    "AA": "American Airlines",
    "UA": "United Airlines",
    "DL": "Delta Air Lines",
    "MH": "Malaysia Airlines",
    "CX": "Cathay Pacific",
    "9W": "Jet Airways",
    "AK": "AirAsia",
    "FZ": "flydubai",
    "G9": "Air Arabia",
}

CITY_ALIASES = {
    # Delhi variations
    "new delhi": "Delhi",
    "delhi ncr": "Delhi",
    "dilli": "Delhi",
    # Bangalore variations
    "bangalore": "Bengaluru",
    "banglore": "Bengaluru",
    "bangaluru": "Bengaluru",
    "blr": "Bengaluru",
    # Hyderabad variations
    "hydrabad": "Hyderabad",
    "hyderabad": "Hyderabad",
    "hyd": "Hyderabad",
    "hyderbad": "Hyderabad",
    # Mumbai variations
    "bombay": "Mumbai",
    "mum": "Mumbai",
    # Chennai variations
    "madras": "Chennai",
    "channai": "Chennai",
    # Kolkata variations
    "calcutta": "Kolkata",
    "kolkatta": "Kolkata",
    # Ahmedabad variations
    "ahmedabad": "Ahmedabad",
    "ahemdabad": "Ahmedabad",
    "ahmedabad": "Ahmedabad",
    # Pune variations
    "poona": "Pune",
    # Kochi variations
    "cochin": "Kochi",
    # Thiruvananthapuram variations
    "trivandrum": "Thiruvananthapuram",
    # Other common
    "goa": "Goa",
    "goa airport": "Goa",
    "varanasi": "Varanasi",
    "benaras": "Varanasi",
    "banaras": "Varanasi",
    "amritsar": "Amritsar",
    "pathankot": "Pathankot",
    "shimla": "Shimla",
    "simla": "Shimla",
    # International variations
    "dubai": "Dubai",
    "dubay": "Dubai",
    "singapore": "Singapore",
    "singapur": "Singapore",
    "london": "London",
    "newyork": "New York",
    "new york city": "New York",
    "nyc": "New York",
}

# ---------------- SERVICES ----------------
from services.local_iata import resolve_city_to_iata
from services.cache import get_cache, set_cache, delete_cache, generate_cache_key

# ---------------- IATA CONVERTER ----------------
def get_iata_code(city_name):
    # Caching check
    cache_key = generate_cache_key("get_iata_code", {"city_name": city_name})
    cached_res = get_cache(cache_key)
    if cached_res:
        # "FAILED_IATA" is a short-lived sentinel. Purge it so the
        # upgraded prompt can retry on the next request.
        if cached_res == "FAILED_IATA":
            delete_cache(cache_key)
            return None
        print(f"⚡ Using cache (IATA): {city_name}")
        return cached_res

    print(f"🌍 Fetching fresh data (IATA): {city_name}")
    try:
        normalized_city = CITY_ALIASES.get(city_name.strip().lower(), city_name)

        # --- LLM LOOKUP ---
        # Ask the AI (flexible with spellings and common names)
        res = resolve_city_to_iata(normalized_city)

        if res:
            set_cache(cache_key, res)
        else:
            set_cache(cache_key, "FAILED_IATA")
        return res

    except Exception as e:
        print(f"IATA ERROR: {type(e).__name__} - {str(e)}")
        set_cache(cache_key, "FAILED_IATA")
        return None


# ---------------- DURATION CALCULATOR ----------------
def calculate_duration(departure, arrival):
    try:
        dep = datetime.fromisoformat(departure)
        arr = datetime.fromisoformat(arrival)
        diff = arr - dep

        # Use total_seconds() to correctly handle overnight/multi-day flights
        total = int(diff.total_seconds())
        if total < 0:
            return "N/A"
        hours = total // 3600
        minutes = (total % 3600) // 60

        return f"{hours}h {minutes}m"
    except Exception:
        return "N/A"


# ---------------- REMOVE DUPLICATES ----------------
def remove_duplicates(flights):
    seen = set()
    unique = []

    for flight in flights:
        key = (
            flight["airline_name"],
            flight["departure"],
            flight["arrival"],
            flight["price"]
        )

        if key not in seen:
            seen.add(key)
            unique.append(flight)

    return unique


# ---------------- RUN DUFFEL FALLBACK ----------------
def get_duffel_flights(origin_code, destination_code, departure_date, return_date=None, adults=1):
    api_key = os.getenv("DUFFEL_ACCESS_TOKEN")
    if not api_key:
        print("DUFFEL_ACCESS_TOKEN is missing in env, skipping fallback")
        return {"outbound": [], "return": []}

    print("Falling back to Duffel.com...")
    
    url = "https://api.duffel.com/air/offer_requests"
    headers = {
        "Duffel-Version": "v2",
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    slices = [{
        "origin": origin_code,
        "destination": destination_code,
        "departure_date": departure_date
    }]
    
    if return_date:
        slices.append({
            "origin": destination_code,
            "destination": origin_code,
            "departure_date": return_date
        })
        
    passengers = [{"type": "adult"} for _ in range(int(adults))]

    payload = {
        "data": {
            "slices": slices,
            "passengers": passengers,
            "return_offers": True
        }
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if not resp.ok:
            print("Duffel Response Body:", resp.text)
        resp.raise_for_status()
        data = resp.json().get("data", {})
        offers = data.get("offers", [])
        
        outbound = []
        return_list = []
        
        # Take the top cheapest 20 to parse
        for offer in offers[:20]:
            price = float(offer.get("total_amount", 0.0))
            currency = offer.get("total_currency", "USD")
            
            # Convert to INR based on currency provided by Duffel
            if currency == "USD":
                price = round(price * 83.5)
            elif currency == "GBP":
                price = round(price * 105.2)
            elif currency == "EUR":
                price = round(price * 90.1)
                
            offer_slices = offer.get("slices", [])
            for index, slice_obj in enumerate(offer_slices):
                segments = slice_obj.get("segments", [])
                if not segments:
                    continue
                    
                dep = segments[0].get("departure_datetime", "")
                arr = segments[-1].get("arrival_datetime", "")
                duration = calculate_duration(dep, arr)
                
                # Check stops (number of segments - 1)
                stops = len(segments) - 1
                stop_label = "Non Stop" if stops == 0 else f"{stops} Stop(s)"
                
                # Take airline from first segment
                marketing = segments[0].get("marketing_carrier", {})
                airline_code = marketing.get("iata_code", "Unknown")
                
                # Some marketing payloads have generic name or generic code
                if airline_code == "Unknown":
                    airline_name = "Unknown Airline"
                else:
                    airline_name = marketing.get("name", AIRLINE_INFO.get(airline_code, airline_code))
                    
                flight_num = segments[0].get("operating_carrier_flight_number", "NA")
                flight_number = f"{airline_code} {flight_num}"
                
                leg_packet = {
                    "airline_name": airline_name,
                    "flight_number": flight_number,
                    "departure": dep,
                    "arrival": arr,
                    "duration": duration,
                    "stops": stops,
                    "stop_label": stop_label,
                    "price": price
                }
                
                if index == 0:
                    outbound.append(leg_packet)
                elif index == 1:
                    return_list.append(leg_packet)
                    
        return {
            "outbound": remove_duplicates(outbound)[:6],
            "return": remove_duplicates(return_list)[:6]
        }
        
    except Exception as e:
        print(f"Duffel ERROR: {e}")
        return {"outbound": [], "return": []}


# -------------- BOOKING.COM FALLBACK --------------
def get_booking_flights_fallback(origin_code, destination_code, departure_date, return_date=None, adults=1):
    try:
        print("Falling back to Booking.com...")
        type_param = "ROUNDTRIP" if return_date else "ONEWAY"
        
        url = "https://flights.booking.com/api/flights/"
        params = {
            "type": type_param,
            "adults": str(adults),
            "cabinClass": "ECONOMY",
            "from": f"{origin_code}.AIRPORT",
            "to": f"{destination_code}.AIRPORT",
            "depart": departure_date,
            "sort": "BEST",
            "travelPurpose": "leisure",
            "aid": "2311236",
            "label": "en-in-booking-desktop"
        }
        if return_date:
            params["return"] = return_date

        headers = {
            "accept": "application/json",
            "accept-language": "en-US,en-IN;q=0.9,en;q=0.8",
            "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
            "sec-ch-ua-platform": '"Windows"',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36",
            "x-booking-affiliate-id": "2311236",
            "x-booking-flights-client-hints": "price_change_v2",
            "x-flights-context-name": "search_results",
            "x-flights-context-pos": "in"
        }

        response = requests.get(url, params=params, headers=headers, timeout=20)
        
        if not response.ok:
            print(f"Booking.com blocked request: Status {response.status_code}")
            return {"outbound": [], "return": []}
            
        data = response.json()
        
        outbound = []
        return_list = []
        
        offers = data.get("flightOffers", [])
        
        for offer in offers:
            # Extracted strictly in INR as point-of-sale is forced to 'in'
            price = offer.get("priceBreakdown", {}).get("total", {}).get("units", 0)
            
            segments = offer.get("segments", [])
            if not segments:
                continue
                
            # Parse OUTBOUND
            out_segment = segments[0]
            out_legs = out_segment.get("legs", [])
            if not out_legs:
                continue
                
            dep = out_segment.get("departureTimeTz", out_segment.get("departureTime", ""))
            arr = out_segment.get("arrivalTimeTz", out_segment.get("arrivalTime", ""))
            
            # Count stops (legs - 1)
            stops = len(out_legs) - 1
            stop_label = "Non Stop" if stops == 0 else f"{stops} Stop(s)"
            
            airline_code = out_legs[0].get("carriers", [""])[0]
            flight_num = out_legs[0].get("flightInfo", {}).get("flightNumber", "")
            flight_number = f"{airline_code} {flight_num}".strip() if flight_num else airline_code
            
            airline_name = "Unknown"
            carriers_data = out_legs[0].get("carriersData", [])
            if carriers_data:
                airline_name = carriers_data[0].get("name", AIRLINE_INFO.get(airline_code, airline_code))
            else:
                airline_name = AIRLINE_INFO.get(airline_code, airline_code)
                
            dep_clean = dep.split("+")[0]
            arr_clean = arr.split("+")[0]
            
            outbound_leg = {
                "airline_name": airline_name,
                "flight_number": flight_number,
                "departure": dep_clean,
                "arrival": arr_clean,
                "duration": calculate_duration(dep_clean, arr_clean),
                "stops": stops,
                "stop_label": stop_label,
                "price": price
            }
            outbound.append(outbound_leg)
            
            # Parse RETURN (if exists)
            if return_date and len(segments) > 1:
                ret_segment = segments[1]
                ret_legs = ret_segment.get("legs", [])
                if not ret_legs:
                    continue
                    
                r_dep = ret_segment.get("departureTimeTz", ret_segment.get("departureTime", ""))
                r_arr = ret_segment.get("arrivalTimeTz", ret_segment.get("arrivalTime", ""))
                
                r_stops = len(ret_legs) - 1
                r_stop_label = "Non Stop" if r_stops == 0 else f"{r_stops} Stop(s)"
                
                r_airline_code = ret_legs[0].get("carriers", [""])[0]
                r_flight_num = ret_legs[0].get("flightInfo", {}).get("flightNumber", "")
                r_flight_number = f"{r_airline_code} {r_flight_num}".strip() if r_flight_num else r_airline_code
                
                r_airline_name = "Unknown"
                r_carriers_data = ret_legs[0].get("carriersData", [])
                if r_carriers_data:
                    r_airline_name = r_carriers_data[0].get("name", AIRLINE_INFO.get(r_airline_code, r_airline_code))
                else:
                    r_airline_name = AIRLINE_INFO.get(r_airline_code, r_airline_code)

                r_dep_clean = r_dep.split("+")[0]
                r_arr_clean = r_arr.split("+")[0]
                    
                ret_leg = {
                    "airline_name": r_airline_name,
                    "flight_number": r_flight_number,
                    "departure": r_dep_clean,
                    "arrival": r_arr_clean,
                    "duration": calculate_duration(r_dep_clean, r_arr_clean),
                    "stops": r_stops,
                    "stop_label": r_stop_label,
                    "price": price
                }
                return_list.append(ret_leg)

        outbound = remove_duplicates(outbound)
        return_list = remove_duplicates(return_list)

        # Sort by lowest price
        outbound = sorted(outbound, key=lambda x: x["price"])[:6]
        return_list = sorted(return_list, key=lambda x: x["price"])[:6]
        
        return {
            "outbound": outbound,
            "return": return_list
        }
        
    except Exception as e:
        print(f"Booking.com ERROR: {e}")
        return {"outbound": [], "return": []}


# ---------------- MAIN FLIGHT FUNCTION ----------------
def get_flights(origin, destination, departure_date, return_date=None, adults=1):
    # Caching check
    cache_params = {
        "origin": origin,
        "destination": destination,
        "departure_date": departure_date,
        "return_date": return_date,
        "adults": adults
    }
    cache_key = generate_cache_key("get_flights", cache_params)
    cached_res = get_cache(cache_key)
    if cached_res:
        print(f"⚡ Using cache (Flights): {origin} -> {destination}")
        return cached_res

    print(f"🌍 Fetching fresh data (Flights): {origin} -> {destination}")
    try:
        # Convert city → IATA
        origin_code = get_iata_code(origin)
        destination_code = get_iata_code(destination)

        if not origin_code or not destination_code:
            print("Invalid city entered")
            return {"outbound": [], "return": []}

        print("Using Duffel API for flight search...")
        duffel_res = get_duffel_flights(origin_code, destination_code, departure_date, return_date, adults)
        if duffel_res and (duffel_res.get("outbound") or duffel_res.get("return")):
             set_cache(cache_key, duffel_res)
             return duffel_res
             
        # Fallback to Booking.com
        booking_res = get_booking_flights_fallback(origin_code, destination_code, departure_date, return_date, adults)
        if booking_res:
             set_cache(cache_key, booking_res)
        return booking_res

    except Exception as e:
        print(f"FLIGHT SEARCH ERROR: {type(e).__name__} - {str(e)}")
        return {"outbound": [], "return": []}
