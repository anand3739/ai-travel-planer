# 🌍 AI Travel Agent

## 📖 Overview
The **AI Travel Agent** is an advanced, full-stack application designed to generate highly personalized travel itineraries, recommend destinations based on user interests, and provide real-time travel data. By leveraging local Large Language Models (LLMs), machine learning algorithms, and real-time external APIs, the application offers a comprehensive, privacy-first travel planning experience.

## ✨ Key Features
- 🤖 **Local-First AI Generation**: Utilizes a local Ollama instance (defaulting to the `phi3` model) to intelligently generate day-by-day travel itineraries, budget estimates, and attraction recommendations without sending sensitive prompt data to external LLM providers.
- 🎯 **ML-Powered City Recommender**: Features a semantic recommendation engine built with Scikit-learn (`TfidfVectorizer` and Cosine Similarity). Users can input interests (e.g., "beach", "technology", "spiritual meditation") and receive highly accurate, normalized confidence scores for 50+ global destinations.
- ✈️ **Real-Time Flight Search**: Integrates seamlessly with **Duffel API** (primary) and **Booking.com** (fallback) to perform live flight shopping, returning actual flight offers. It utilizes local AI to dynamically resolve city names to IATA airport codes.
- 🌤️ **Live Contextual Data**: Pulls live weather forecasts via the **Open-Meteo API** and destination background information via the **Wikipedia API** to augment the AI-generated itinerary.
- 📧 **Email Integration**: Users can share their dynamically generated travel plans instantly via email using the **SendGrid API**.
- 🎨 **Modern Scrollytelling Frontend**: A beautifully designed frontend built with **Next.js**, **React**, **Tailwind CSS**, and **Framer Motion**, which is statically exported and seamlessly served by the backend.

## 🏗️ Architecture & Tech Stack

### Backend
- **Framework**: FastAPI (Python) running on Uvicorn
- **AI Integration**: Local Ollama REST API (`/api/generate`)
- **Machine Learning**: Scikit-Learn (TF-IDF, Cosine Similarity)
- **Templating**: Jinja2 (for dynamically rendering trip summaries)

### Frontend
- **Framework**: Next.js (Static HTML Export)
- **Styling**: Tailwind CSS
- **Animations**: Framer Motion

### External APIs
- **Duffel**: Primary Flight Offers Search
- **Booking.com**: Fallback Flight Offers Search
- **Open-Meteo**: Geocoding and Weather Forecasting
- **Wikipedia**: MediaWiki API for destination insights
- **SendGrid**: Email delivery

## 🚀 Getting Started

### Prerequisites
Before you begin, ensure you have the following installed:
- **Python 3.8+**
- **Node.js 18+ & npm** (for frontend development and building)
- **Ollama**: Download and install [Ollama](https://ollama.com/). Once installed, pull the required model:
  ```bash
  ollama run phi3
  ```
- **API Keys**:
  - [Duffel](https://duffel.com/) (For flight search fallback)
  - [SendGrid](https://sendgrid.com/) (For email features)

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd ai-travel-agent
```

### 2. Backend Setup
Create a virtual environment and install dependencies:
```bash
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Environment Variables
Copy the example environment file and fill in your API credentials:
```bash
# Windows
copy .env.example .env.local
# macOS/Linux
cp .env.example .env.local
```
Edit `.env.local` to include your actual API keys:
```env
DUFFEL_ACCESS_TOKEN=your_duffel_token
SENDGRID_API_KEY=your_sendgrid_key
SENDER_EMAIL=you@example.com
```

### 4. Frontend Setup
The frontend is a Next.js application that needs to be built so FastAPI can serve its static files.
```bash
cd frontend
npm install
npm run build
cd ..
```
*(The `npm run build` command exports the static files into the `frontend/out` directory, which FastAPI is configured to mount automatically.)*

### 5. Running the Application
Ensure your local Ollama server is running in the background. Then, start the FastAPI server:
```bash
python -m uvicorn main:app --reload
```
- The main landing page will be available at: `http://localhost:8000/`
- You can navigate to create a trip at: `http://localhost:8000/create`
- *(Optional)* For frontend development with Hot Module Replacement, you can run `npm run dev` inside the `frontend/` directory.

## 📁 Project Structure

```text
ai-travel-agent/
│
├── main.py                     # Main FastAPI application entry point
├── agent.py                    # Orchestrates the AI travel planning flow
├── api_utils.py                # External API wrappers (Weather, Wikipedia, Attractions)
├── email_sender.py             # SendGrid email integration
├── flights_service.py          # Flight search integration (Duffel API)
│
├── services/                   # Core business logic and AI services
│   ├── local_llm.py            # Local Ollama LLM integration
│   ├── city_recommender.py     # ML-based city recommendation engine
│   ├── local_iata.py           # AI-powered city-to-IATA fallback resolution
│   ├── local_attractions.py    # Local AI generation of landmarks
│   ├── cache.py                # Local JSON caching to prevent API overuse
│   └── ollama_config.py        # Centralized model settings
│
├── data/                       # Datasets
│   └── city_keywords.csv       # Keywords mapped to cities for the ML recommender
│
├── frontend/                   # Next.js scrollytelling frontend application
│   ├── src/                    # React components and app logic
│   ├── package.json
│   └── next.config.mjs
│
├── static/                     # Global static assets (CSS, images)
├── templates/                  # Jinja2 HTML templates for the backend views
│
└── API_DOCUMENTATION.md        # Detailed mapping of all external APIs used
```

## 📚 API & Documentation Reference
For a detailed breakdown of how each external API is utilized across the application, please refer to the `API_DOCUMENTATION.md` file. It covers the specific endpoints, required credentials, and function mappings for Flights, Weather, Destination Info, and AI Generation.

## 🛠️ Recent Improvements
- **Semantic City Recommender**: Upgraded the recommendation engine from a basic Logistic Regression classifier to a robust **TF-IDF + Cosine Similarity** model. This provides highly accurate, semantically meaningful destination matches (e.g., matching "beach" correctly to coastal cities instead of landlocked tech hubs) with properly normalized confidence scores (0-100%).

---
*Built with ❤️ utilizing Local AI for privacy and performance.*
