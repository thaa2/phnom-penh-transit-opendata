import requests
import streamlit as st

OSRM_BASE = "https://router.project-osrm.org/route/v1"


@st.cache_data(show_spinner=False, ttl=86400)
def snap_to_road(coords: tuple[tuple[float, float], ...], profile: str = "driving") -> list[tuple[float, float]]:
    """
    Snap a sequence of (lat, lng) waypoints onto real OpenStreetMap road geometry via OSRM.
    Falls back to original straight coordinates if offline or rate-limited.
    """
    if len(coords) < 2:
        return list(coords)

    # Chunk waypoints (max ~45 per request) so long routes stay within URL limits
    chunk_size = 45
    full_path: list[tuple[float, float]] = []

    for start_idx in range(0, len(coords) - 1, chunk_size - 1):
        chunk = coords[start_idx : start_idx + chunk_size]
        coord_str = ";".join(f"{lng:.6f},{lat:.6f}" for lat, lng in chunk)
        url = f"{OSRM_BASE}/{profile}/{coord_str}"
        params = {
            "overview": "full",
            "geometries": "geojson",
            "continue_straight": "true",
        }

        try:
            resp = requests.get(url, params=params, timeout=6)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == "Ok" and data.get("routes"):
                # GeoJSON returns [lng, lat] -> convert back to (lat, lng) for Folium
                segment_pts = [(pt[1], pt[0]) for pt in data["routes"][0]["geometry"]["coordinates"]]
                if full_path and segment_pts:
                    full_path.extend(segment_pts[1:])
                else:
                    full_path.extend(segment_pts)
            else:
                full_path.extend(chunk)
        except Exception:
            full_path.extend(chunk)

    return full_path if full_path else list(coords)
