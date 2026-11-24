cat << 'EOF' > src/prepare_data.py
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def dms_to_decimal(dms_str: str) -> float:
    """Convert DMS strings like E104° 55' 52.891" or N11° 33' 01.568" to decimal degrees."""
    pattern = r"([NSEW])\s*(\d+)°\s*(\d+)'\s*([\d.]+)\"?"
    match = re.search(pattern, str(dms_str).strip())
    if not match:
        raise ValueError(f"Invalid DMS coordinate format: {dms_str}")
    hemi, deg, minutes, seconds = match.groups()
    decimal = float(deg) + float(minutes) / 60.0 + float(seconds) / 3600.0
    if hemi in ("S", "W"):
        decimal = -decimal
    return round(decimal, 6)


def parse_bus_stops(kml_path: Path) -> pd.DataFrame:
    """Parse Phnom Penh City Bus stops from KML into a clean DataFrame."""
    tree = ET.parse(kml_path)
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    records = []

    for pm in tree.getroot().findall(".//kml:Placemark", ns):
        row = {sd.get("name"): sd.text for sd in pm.findall(".//kml:SimpleData", ns)}
        coords_el = pm.find(".//kml:coordinates", ns)
        if coords_el is not None and coords_el.text:
            lng, lat = map(float, coords_el.text.strip().split(",")[:2])
            row["longitude"] = round(lng, 6)
            row["latitude"] = round(lat, 6)
        records.append(row)

    df = pd.DataFrame(records)
    df = df.rename(
        columns={
            "stop_numbe": "stop_number",
            "name": "stop_name_kh",
            "category": "bus_line",
        }
    )
    df["stop_number"] = pd.to_numeric(df["stop_number"], errors="coerce").astype("Int64")
    keep_cols = ["map_id", "stop_number", "stop_name_kh", "bus_line", "latitude", "longitude"]
    return df[keep_cols]


def clean_admin_locations(csv_path: Path) -> pd.DataFrame:
    """Normalize DMS coordinates and clean administrative hierarchy CSV."""
    df = pd.read_csv(csv_path)
    df = df.rename(
        columns={
            "Zip Code": "zip_code",
            "Name": "name",
            "Type of Location": "location_type",
        }
    )
    df["zip_code"] = df["zip_code"].astype(str)
    df["name"] = df["name"].str.replace(r"/$", "l", regex=True).str.strip()  # Fix Kambou/ -> Kamboul
    df["latitude"] = df["Latitude"].apply(dms_to_decimal)
    df["longitude"] = df["Longtitude"].apply(dms_to_decimal)
    return df[["zip_code", "name", "location_type", "latitude", "longitude"]]


def enrich_with_transit_metrics(admin_df: pd.DataFrame, stops_df: pd.DataFrame) -> pd.DataFrame:
    """Compute distance (meters) to nearest bus stop and count of stops within 500m."""
    # Equirectangular approximation around Phnom Penh (11.55° N) for fast KDTree queries
    lat_ref = np.radians(11.55)
    m_per_deg_lat = 111_132.0
    m_per_deg_lng = 111_320.0 * np.cos(lat_ref)

    stop_xy = np.column_stack(
        [stops_df["longitude"] * m_per_deg_lng, stops_df["latitude"] * m_per_deg_lat]
    )
    admin_xy = np.column_stack(
        [admin_df["longitude"] * m_per_deg_lng, admin_df["latitude"] * m_per_deg_lat]
    )

    tree = cKDTree(stop_xy)
    distances, nearest_idx = tree.query(admin_xy, k=1)
    within_500m = tree.query_ball_point(admin_xy, r=500.0)

    enriched = admin_df.copy()
    enriched["nearest_stop_m"] = np.round(distances, 1)
    enriched["nearest_stop_name_kh"] = stops_df.iloc[nearest_idx]["stop_name_kh"].values
    enriched["nearest_bus_line"] = stops_df.iloc[nearest_idx]["bus_line"].values
    enriched["stops_within_500m"] = [len(idxs) for idxs in within_500m]
    return enriched


def export_stops_geojson(stops_df: pd.DataFrame, out_path: Path) -> None:
    """Export bus stops as standard GeoJSON FeatureCollection."""
    features = []
    for _, row in stops_df.iterrows():
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [row["longitude"], row["latitude"]],
                },
                "properties": {
                    "map_id": row["map_id"],
                    "stop_number": int(row["stop_number"]) if pd.notna(row["stop_number"]) else None,
                    "stop_name_kh": row["stop_name_kh"],
                    "bus_line": row["bus_line"],
                },
            }
        )
    geojson = {"type": "FeatureCollection", "features": features}
    out_path.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    stops_df = parse_bus_stops(RAW_DIR / "PublicTransportationinCambodia.kml")
    admin_df = clean_admin_locations(
        RAW_DIR / "GeographicalcoordinatesofPhnomPenhCapitalCityofCambodia.csv"
    )
    enriched_admin_df = enrich_with_transit_metrics(admin_df, stops_df)

    stops_df.to_csv(PROCESSED_DIR / "bus_stops_clean.csv", index=False)
    enriched_admin_df.to_csv(PROCESSED_DIR / "admin_transit_coverage.csv", index=False)
    export_stops_geojson(stops_df, PROCESSED_DIR / "bus_stops.geojson")

    print(f"Saved {len(stops_df)} clean bus stops -> data/processed/bus_stops_clean.csv & .geojson")
    print(f"Saved {len(enriched_admin_df)} enriched locations -> data/processed/admin_transit_coverage.csv")
    print("\nTop 5 Underserved Sangkats (Furthest from nearest bus stop):")
    sangkats = enriched_admin_df[enriched_admin_df["location_type"] == "Sangkat"]
    print(
        sangkats.sort_values("nearest_stop_m", ascending=False)[
            ["zip_code", "name", "nearest_stop_m", "stops_within_500m"]
        ]
        .head(5)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
EOF
