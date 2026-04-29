
from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import uuid
import json
import asyncio

from agent import run_travel_agent
from email_sender import send_email
from api_utils import get_weather, get_destination_info, get_attractions
from services.city_recommender import recommend_city, get_all_cities

import os

# Load safe defaults from `.env`, then allow local overrides from `.env.local`
# (which is ignored by git via `.gitignore`).
load_dotenv(".env", override=False)
load_dotenv(".env.local", override=True)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Path to the built frontend
FRONTEND_OUT = os.path.join(os.path.dirname(__file__), "frontend", "out")

# Mount Next.js static assets if they exist
if os.path.exists(os.path.join(FRONTEND_OUT, "_next")):
    app.mount("/_next", StaticFiles(directory=os.path.join(FRONTEND_OUT, "_next")), name="next_static")
    # Also mount frames since they are in public/frames
    if os.path.exists(os.path.join(FRONTEND_OUT, "frames")):
        app.mount("/frames", StaticFiles(directory=os.path.join(FRONTEND_OUT, "frames")), name="frames_static")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Temporary session memory
session_store = {}


# ==========================
# LANDING PAGE
# ==========================
@app.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    index_path = os.path.join(FRONTEND_OUT, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return templates.TemplateResponse("landing.html", {"request": request})



# ==========================
# CREATE TRIP (GET + POST for EDIT) - Index form
# ==========================
@app.get("/create", response_class=HTMLResponse)
@app.post("/create", response_class=HTMLResponse)
async def create_trip(
    request: Request,
    from_location: str = Form(None),
    to_location: str = Form(None),
    departure_date: str = Form(None),
    return_date: str = Form(None),
    adults: int = Form(None),
    children: int = Form(None),
    trip_type: str = Form(None),
    stay_type: str = Form(None),
    hotel_category: str = Form(None),
    description: str = Form(None),
):

    form_data = None

    # If coming from Edit button
    if from_location:
        form_data = {
            "from": from_location,
            "to": to_location,
            "departure_date": departure_date,
            "return_date": return_date,
            "adults": adults,
            "children": children,
            "trip_type": trip_type,
            "stay_type": stay_type,
            "hotel_category": hotel_category,
            "description": description,
        }

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "form_data": form_data
        }
    )


# ==========================
# PLAN TRIP
# ==========================
@app.post("/plan", response_class=HTMLResponse)
async def plan_trip(
    request: Request,
    from_location: str = Form(...),
    to_location: str = Form(...),
    departure_date: str = Form(...),
    return_date: str = Form(None),
    adults: int = Form(...),
    children: int = Form(...),
    trip_type: str = Form(...),
    stay_type: str = Form(...),
    hotel_category: str = Form(...),
    description: str = Form(None),
):

    try:
        thread_id = str(uuid.uuid4())

        # Assuming run_travel_agent is still synchronous or needs run_in_executor
        result = await asyncio.to_thread(
            run_travel_agent,
            from_location,
            to_location,
            departure_date,
            return_date,
            adults,
            children,
            trip_type,
            stay_type,
            hotel_category,
            description,
        )

        # FETCH ADDITIONAL DATA ASYNCHRONOUSLY
        weather_task = get_weather(to_location)
        attractions_task = get_attractions(to_location)
        dest_info_task = get_destination_info(to_location)

        # Run all three in parallel while the AI finish its work (if needed)
        weather, attractions, destination_info = await asyncio.gather(
            weather_task, attractions_task, dest_info_task
        )

        result["weather"] = weather
        result["attractions"] = attractions.get("attractions", []) if isinstance(attractions, dict) else attractions
        result["destination_info"] = destination_info
        result["share_url"] = f"/view-trip/{thread_id}"

        session_store[thread_id] = result
        print(f"✅ Data fetched for Flights")
        print(f"✅ Data fetched for Itinerary")
        print(f"✅ Data fetched for Weather")
        print(f"✅ Data fetched for Attractions")
        print(f"✅ Data fetched for Destination Info")
        print(f"✅ All data successfully fetched for {to_location}!")

        return templates.TemplateResponse(
            "summary.html",
            {
                "request": request,
                "result": result,
                "thread_id": thread_id,
                "email_status": None
            }
        )
    except Exception as e:
        print(f"Error planning trip: {e}")
        form_data = {
            "from": from_location,
            "to": to_location,
            "departure_date": departure_date,
            "return_date": return_date,
            "adults": adults,
            "children": children,
            "trip_type": trip_type,
            "stay_type": stay_type,
            "hotel_category": hotel_category,
            "description": description,
        }
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "form_data": form_data,
                "error": f"Failed to generate trip. Please try again. Error: {str(e)}"
            }
        )


# ==========================
# SEND EMAIL
# ==========================
@app.post("/send-email", response_class=HTMLResponse)
async def email_trip(
    request: Request,
    background_tasks: BackgroundTasks,
    thread_id: str = Form(...),
    receiver: str = Form(...)
):

    data = session_store.get(thread_id)

    if not data:
        return templates.TemplateResponse(
            "summary.html",
            {
                "request": request,
                "result": None,
                "thread_id": thread_id,
                "email_status": "Session expired. Please regenerate plan."
            }
        )

    # Add email sending to background tasks
    background_tasks.add_task(send_email, receiver, data)
    email_status = f"✅ Email to {receiver} is being sent in the background."

    return templates.TemplateResponse(
        "summary.html",
        {
            "request": request,
            "result": data,
            "thread_id": thread_id,
            "email_status": email_status
        }
    )


# ==========================
# VIEW SHARED TRIP
# ==========================
@app.get("/view-trip/{thread_id}", response_class=HTMLResponse)
async def view_shared_trip(request: Request, thread_id: str):
    data = session_store.get(thread_id)
    
    if not data:
        return """
        <html><body style="font-family: Arial; text-align: center; padding: 50px;">
            <h2>Trip Not Found</h2>
            <p>This trip link has expired or doesn't exist.</p>
            <a href="/create">Create a new trip</a>
        </body></html>
        """
    
    return templates.TemplateResponse(
        "summary.html",
        {
            "request": request,
            "result": data,
            "thread_id": thread_id,
            "email_status": None,
            "is_shared": True
        }
    )

# ==========================
# API ENDPOINTS
# ==========================

@app.get("/api/weather")
async def get_trip_weather(city: str):
    """Get weather for a city"""
    weather = await get_weather(city)
    return JSONResponse(weather)


@app.get("/api/attractions")
async def get_trip_attractions(city: str):
    """Get attractions for a city"""
    attractions = await get_attractions(city)
    return JSONResponse(attractions)

@app.get("/api/destination-info")
async def get_trip_destination_info(city: str):
    """Get destination information"""
    info = await get_destination_info(city)
    return JSONResponse(info)


@app.get("/api/recommend-city")
async def recommend_city_endpoint(keywords: str):
    """Recommend cities based on keywords/interests using ML model."""
    if not keywords or not keywords.strip():
        return JSONResponse({
            "error": "Keywords required",
            "city": "",
            "country": "",
            "all_recommendations": []
        })
    try:
        # recommend_city might be sync
        result = await asyncio.to_thread(recommend_city, keywords.strip())
        clean_result = {
            "city": result["city"],
            "country": result["country"],
            "confidence": result.get("confidence", 0.0),
            "all_recommendations": [
                {
                    "city": rec["city"],
                    "country": rec["country"],
                    "confidence": rec.get("confidence", 0.0)
                }
                for rec in result.get("all_recommendations", [])
            ]
        }
        return JSONResponse(clean_result)
    except Exception as e:
        print(f"City recommendation error: {e}")
        return JSONResponse({
            "error": str(e),
            "city": "",
            "country": "",
            "all_recommendations": []
        })


@app.get("/api/available-cities")
async def available_cities():
    """Get list of all available cities in the ML model."""
    try:
        cities = await asyncio.to_thread(get_all_cities)
        return JSONResponse({
            "cities": cities,
            "count": len(cities)
        })
    except Exception as e:
        print(f"Get cities error: {e}")
        return JSONResponse({
            "error": str(e),
            "cities": [],
            "count": 0
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

