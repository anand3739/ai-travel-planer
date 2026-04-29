"""City Recommender using TF-IDF + Logistic Regression.

Trains on keywords-to-city mappings from CSV file.
recommend_city(text) -> {"city": str, "country": str, "confidence": float}
"""
from __future__ import annotations

import csv
import os
from typing import Dict, List, Tuple

# Lazy-loaded sklearn objects - imported only on first use
_pipeline = None
_city_mapping = None  # Maps class index to (city, country) tuple


def _load_training_data() -> Tuple[List[str], List[str], Dict[int, Tuple[str, str]]]:
    """Load training data from CSV file.
    
    Returns:
        (texts, labels, city_mapping)
        - texts: list of keyword strings
        - labels: list of city names (matching texts order)
        - city_mapping: dict mapping label index to (city, country) tuple
    """
    csv_path = os.path.join(os.path.dirname(__file__), "../data/city_keywords.csv")
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Training data not found: {csv_path}")
    
    texts = []
    labels = []
    city_info = {}  # city -> country mapping
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            keywords = row['keywords'].strip()
            city = row['city'].strip()
            country = row['country'].strip()
            
            if keywords and city and country:
                texts.append(keywords)
                labels.append(city)
                
                # Store country for each city (use the last one if multiple)
                city_info[city] = country
    
    if not texts:
        raise ValueError("No training data found in CSV")
    
    # Create mapping from unique labels to (city, country)
    unique_labels = list(dict.fromkeys(labels))  # Preserve order while removing duplicates
    city_mapping = {
        i: (label, city_info.get(label, "Unknown"))
        for i, label in enumerate(unique_labels)
    }
    
    return texts, labels, city_mapping


def _build_pipeline() -> object:
    """Lazy-initialize and train the TF-IDF vectorizer and Logistic Regression model.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    texts, labels, city_map = _load_training_data()
    global _city_mapping
    _city_mapping = city_map

    pipeline = Pipeline([
        ('vectorizer', TfidfVectorizer(
            ngram_range=(1, 3),
            min_df=1,
            max_features=4000,
            sublinear_tf=True,
            stop_words='english',
        )),
        ('clf', LogisticRegression(random_state=42, max_iter=1000, class_weight='balanced'))
    ])
    
    pipeline.fit(texts, labels)
    return pipeline


def recommend_city(text: str) -> Dict[str, object]:
    """Recommend a city based on keywords/description using Logistic Regression.

    Args:
        text: Keywords or description string

    Returns:
        {
            "city": str,
            "country": str,
            "confidence": float,
            "all_recommendations": list of top 5 recommendations
        }
    """
    import numpy as np
    
    global _pipeline, _city_mapping

    if _pipeline is None:
        _pipeline = _build_pipeline()

    # Predict probabilities for all classes
    probas = _pipeline.predict_proba([text])[0]
    classes = _pipeline.classes_
    
    # Sort by probability (descending) and get top 5
    top_indices = np.argsort(probas)[::-1][:5]
    top_5 = [(classes[i], float(probas[i])) for i in top_indices]
    
    # Build a city name -> country mapping from city_mapping
    city_to_country = {}
    for city, country in _city_mapping.values():
        city_to_country[city] = country
    
    # Convert to recommendations format
    recommendations = []
    for city_name, score in top_5:
        country = city_to_country.get(city_name, "Unknown")
        confidence = round(score * 100, 1)  # Convert probability [0,1] to percentage [0,100]
        recommendations.append({
            "city": str(city_name),
            "country": str(country),
            "confidence": float(confidence)
        })
    
    # Return top recommendation as primary
    if recommendations:
        return {
            "city": recommendations[0]["city"],
            "country": recommendations[0]["country"],
            "confidence": recommendations[0]["confidence"],
            "all_recommendations": recommendations
        }
    else:
        return {
            "city": "Unknown",
            "country": "Unknown",
            "confidence": 0.0,
            "all_recommendations": []
        }


def get_all_cities() -> List[Dict[str, str]]:
    """Get list of all available cities in the training data.
    
    Returns:
        List of dicts with 'city' and 'country' keys
    """
    global _pipeline, _city_mapping

    if _pipeline is None:
        _pipeline = _build_pipeline()

    cities = []
    seen = set()
    for city, country in _city_mapping.values():
        key = f"{city}_{country}"
        if key not in seen:
            cities.append({"city": city, "country": country})
            seen.add(key)
    
    return sorted(cities, key=lambda x: x["city"])
