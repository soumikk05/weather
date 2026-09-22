"""
Unit and Integration Tests for Location Search & Resolution
Forecast Bust Detection System — NCMRWF / Ministry of Earth Sciences

Covers:
- GET /locations/search?q=<query>
- Direct subdivision name matches ("exact_subdivision")
- Major Indian city / district resolution ("resolved_from_city")
- Mandatory caveat note regarding subdivision granularity
- 404 response for unresolvable location queries
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from api.main import app
from src.data.schema import SUBDIVISIONS

client = TestClient(app)


def test_direct_subdivision_search():
    """Verify that querying exact or partial subdivision names yields 'exact_subdivision'."""
    queries = ["Konkan & Goa", "Punjab", "Odisha", "Bihar", "Assam"]
    for q in queries:
        response = client.get(f"/locations/search?q={q}")
        assert response.status_code == 200
        data = response.json()
        assert data["match_confidence"] == "exact_subdivision"
        assert "subdivision_lat" in data
        assert "subdivision_lon" in data
        assert "note" in data
        assert "subdivision resolution" in data["note"].lower()


def test_major_city_resolution():
    """Verify major Indian cities resolve to containing/nearest subdivision with 'resolved_from_city'."""
    test_cities = [
        ("Chennai", "Rayalaseema"),  # Nearest IMD centroid based on schema lat/lon
        ("Mumbai", "Madhya Maharashtra"),
        ("Bengaluru", "South Interior Karnataka"),
        ("Kolkata", "Gangetic West Bengal"),
        ("Hyderabad", "Telangana"),
        ("Ahmedabad", "Gujarat Region"),
        ("Jaipur", "East Rajasthan"),
        ("Lucknow", "East Uttar Pradesh"),
        ("Bhubaneswar", "Odisha"),
    ]

    for city, expected_sub in test_cities:
        response = client.get(f"/locations/search?q={city}")
        assert response.status_code == 200, f"Failed resolving city '{city}'"
        data = response.json()
        assert data["match_confidence"] == "resolved_from_city"
        assert data["resolved_subdivision"] == expected_sub
        assert data["distance_km"] >= 0.0
        assert "subdivision resolution" in data["note"].lower()


def test_location_note_always_present():
    """Ensure every resolved location carries the explicit resolution caveat."""
    for q in ["Delhi", "Nagpur", "Kerala"]:
        response = client.get(f"/locations/search?q={q}")
        assert response.status_code == 200
        data = response.json()
        assert "note" in data
        assert "subdivision resolution" in data["note"]
        assert "MVP limitation" in data["note"]


def test_unknown_location_404():
    """Verify 404 is returned when location cannot be resolved."""
    response = client.get("/locations/search?q=AtlantisFictionalCity999")
    assert response.status_code == 404
    data = response.json()
    assert "no meteorological subdivision" in data["detail"].lower()


def test_empty_location_422():
    """Verify empty query string triggers 422 validation error."""
    response = client.get("/locations/search?q=")
    assert response.status_code == 422
