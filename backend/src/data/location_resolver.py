"""
Location Resolver: Indian Cities & Meteorological Subdivisions
Smart India Hackathon - NCMRWF / Ministry of Earth Sciences

Resolves free-text location queries to the 32 IMD meteorological subdivisions.
City-to-subdivision mapping is computed programmatically via Haversine distance
to the nearest IMD subdivision centroid from schema.SUBDIVISIONS.
"""

import math
from typing import Dict, List, Optional, Tuple
from src.data.schema import SUBDIVISIONS, SubdivisionInfo


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two coordinates in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 2)


# Curated catalog of major Indian cities, state capitals, and meteorological stations
# with accurate WGS84 geographic coordinates.
INDIAN_CITIES_COORDINATES: Dict[str, Tuple[float, float]] = {
    # Northern & Central Capital Cities
    "Delhi": (28.6139, 77.2090),
    "New Delhi": (28.6139, 77.2090),
    "Chandigarh": (30.7333, 76.7794),
    "Shimla": (31.1048, 77.1734),
    "Dehradun": (30.3165, 78.0322),
    "Srinagar": (34.0837, 74.7973),
    "Jammu": (32.7266, 74.8570),
    "Leh": (34.1526, 77.5771),
    "Jaipur": (26.9124, 75.7873),
    "Jodhpur": (26.2389, 73.0243),
    "Lucknow": (26.8467, 80.9462),
    "Kanpur": (26.4499, 80.3319),
    "Varanasi": (25.3176, 82.9739),
    "Agra": (27.1767, 78.0081),
    "Patna": (25.5941, 85.1376),
    "Gaya": (24.7914, 85.0002),
    "Bhopal": (23.2599, 77.4126),
    "Indore": (22.7196, 75.8577),
    "Gwalior": (26.2183, 78.1828),
    "Jabalpur": (23.1815, 79.9864),
    "Raipur": (21.2514, 81.6296),
    "Ranchi": (23.3441, 85.3096),
    "Jamshedpur": (22.8046, 86.2029),

    # Eastern & Northeastern
    "Kolkata": (22.5726, 88.3639),
    "Howrah": (22.5958, 88.2636),
    "Siliguri": (26.7271, 88.3953),
    "Bhubaneswar": (20.2961, 85.8245),
    "Cuttack": (20.4625, 85.8830),
    "Puri": (19.8135, 85.8312),
    "Guwahati": (26.1445, 91.7362),
    "Shillong": (25.5788, 91.8933),
    "Itanagar": (27.0844, 93.6053),
    "Gangtok": (27.3389, 88.6065),
    "Agartala": (23.8315, 91.2868),
    "Imphal": (24.8170, 93.9368),
    "Aizawl": (23.7271, 92.7176),
    "Kohima": (25.6751, 94.1086),

    # Western
    "Mumbai": (19.0760, 72.8777),
    "Pune": (18.5204, 73.8567),
    "Nagpur": (21.1458, 79.0882),
    "Nashik": (19.9975, 73.7898),
    "Aurangabad": (19.8762, 75.3433),
    "Chhatrapati Sambhajinagar": (19.8762, 75.3433),
    "Ahmedabad": (23.0225, 72.5714),
    "Gandhinagar": (23.2156, 72.6369),
    "Surat": (21.1702, 72.8311),
    "Vadodara": (22.3072, 73.1812),
    "Rajkot": (22.3039, 70.8022),
    "Panaji": (15.4909, 73.8278),
    "Goa": (15.2993, 74.1240),

    # Southern
    "Chennai": (13.0827, 80.2707),
    "Madurai": (9.9252, 78.1198),
    "Coimbatore": (11.0168, 76.9558),
    "Tiruchirappalli": (10.7905, 78.7047),
    "Bengaluru": (12.9716, 77.5946),
    "Bangalore": (12.9716, 77.5946),
    "Mysuru": (12.2958, 76.6394),
    "Mysore": (12.2958, 76.6394),
    "Mangalore": (12.9141, 74.8560),
    "Hubli": (15.3647, 75.1240),
    "Hyderabad": (17.3850, 78.4867),
    "Warangal": (17.9689, 79.5941),
    "Visakhapatnam": (17.6868, 83.2185),
    "Vijayawada": (16.5062, 80.6480),
    "Tirupati": (13.6288, 79.4192),
    "Thiruvananthapuram": (8.5241, 76.9366),
    "Kochi": (9.9312, 76.2673),
    "Kozhikode": (11.2588, 75.7804),
    "Puducherry": (11.9416, 79.8083),
}


def _find_nearest_subdivision(lat: float, lon: float) -> Tuple[SubdivisionInfo, float]:
    """Finds the nearest IMD subdivision by Haversine distance."""
    best_sub: Optional[SubdivisionInfo] = None
    min_dist = float("inf")

    for sub in SUBDIVISIONS:
        dist = haversine_distance_km(lat, lon, sub.lat, sub.lon)
        if dist < min_dist:
            min_dist = dist
            best_sub = sub

    return best_sub, min_dist


# Programmatically precomputed static lookup table of cities -> nearest subdivision
CITY_TO_SUBDIVISION_MAP: Dict[str, Dict] = {}
for city_name, (clat, clon) in INDIAN_CITIES_COORDINATES.items():
    nearest_sub, distance_km = _find_nearest_subdivision(clat, clon)
    CITY_TO_SUBDIVISION_MAP[city_name.lower()] = {
        "city_name": city_name,
        "city_lat": clat,
        "city_lon": clon,
        "subdivision_name": nearest_sub.name,
        "subdivision_lat": nearest_sub.lat,
        "subdivision_lon": nearest_sub.lon,
        "distance_km": distance_km,
    }


def resolve_location(query: str) -> Optional[Dict]:
    """
    Resolves a location query string to an IMD meteorological subdivision.
    
    1. Checks direct match against IMD subdivision names (exact, then substring).
    2. Checks major Indian cities lookup table (precomputed via nearest centroid).
    
    Returns structured resolution dictionary or None if no match found.
    """
    if not query or not query.strip():
        return None

    clean_q = query.strip()
    q_lower = clean_q.lower()

    # Step 1: Match against subdivision names
    # Exact match
    for sub in SUBDIVISIONS:
        if q_lower == sub.name.lower():
            return {
                "query": clean_q,
                "resolved_subdivision": sub.name,
                "subdivision_lat": sub.lat,
                "subdivision_lon": sub.lon,
                "match_confidence": "exact_subdivision",
                "matched_name": sub.name,
                "distance_km": 0.0,
                "note": (
                    "All results are reported at meteorological subdivision resolution. "
                    "City-level resolution is a known MVP limitation with high-resolution "
                    "numerical grids planned for future phases."
                ),
            }

    # Substring match on subdivision names
    for sub in SUBDIVISIONS:
        if q_lower in sub.name.lower():
            return {
                "query": clean_q,
                "resolved_subdivision": sub.name,
                "subdivision_lat": sub.lat,
                "subdivision_lon": sub.lon,
                "match_confidence": "exact_subdivision",
                "matched_name": sub.name,
                "distance_km": 0.0,
                "note": (
                    "All results are reported at meteorological subdivision resolution. "
                    "City-level resolution is a known MVP limitation with high-resolution "
                    "numerical grids planned for future phases."
                ),
            }

    # Step 2: Match against city lookup table
    # Exact city match
    if q_lower in CITY_TO_SUBDIVISION_MAP:
        entry = CITY_TO_SUBDIVISION_MAP[q_lower]
        return {
            "query": clean_q,
            "resolved_subdivision": entry["subdivision_name"],
            "subdivision_lat": entry["subdivision_lat"],
            "subdivision_lon": entry["subdivision_lon"],
            "match_confidence": "resolved_from_city",
            "matched_name": entry["city_name"],
            "distance_km": entry["distance_km"],
            "note": (
                "All results are reported at meteorological subdivision resolution. "
                "City-level resolution is a known MVP limitation with high-resolution "
                "numerical grids planned for future phases."
            ),
        }

    # Substring city match
    for city_key, entry in CITY_TO_SUBDIVISION_MAP.items():
        if q_lower in city_key or city_key in q_lower:
            return {
                "query": clean_q,
                "resolved_subdivision": entry["subdivision_name"],
                "subdivision_lat": entry["subdivision_lat"],
                "subdivision_lon": entry["subdivision_lon"],
                "match_confidence": "resolved_from_city",
                "matched_name": entry["city_name"],
                "distance_km": entry["distance_km"],
                "note": (
                    "All results are reported at meteorological subdivision resolution. "
                    "City-level resolution is a known MVP limitation with high-resolution "
                    "numerical grids planned for future phases."
                ),
            }

    return None
