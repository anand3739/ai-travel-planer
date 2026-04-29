"""Centralized Ollama configuration.

All services that call local Ollama (local_llm, local_attractions, local_iata)
import from here so the endpoint and model name are defined in a single place.
"""

OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "phi3"
