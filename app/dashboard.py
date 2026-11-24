import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from src.router import TransitRouter

st.set_page_config(
    page_title="CamTransit AI — Phnom Penh Smart Transit",
    page_icon="🚌",
    layout="wide",
)

DATA_DIR = Path("data/processed")

LINE_COLORS = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231",
    "#911eb4", "#008080", "#f032e6", "#9a6324",
    "#800000", "#000075", "#e6beff", "#808000",
    "#46f0f0", "#bcf60c", "#fabebe", "#aaffc3",
]


@st.cache_data
def load_data():
    stops = pd.read_csv(DATA_DIR / "bus_stops_clean.csv")
    admin = pd.read_csv(DATA_DIR / "admin_transit_coverage.csv")
    return stops, admin


@st.cache_resource
def get_router(stops_df):
    return TransitRouter(stops_df, transfer_radius_m=250.0)


stops_df, admin_df = load_data()
router = get_router(stops_df)

st.title("🚌 CamTransit AI — Phnom Penh Smart Transit Assistant")

tab_route, tab_coverage = st.tabs(
    ["🧭 Route & Transfer Finder", "🗺️ City Coverage & Underserved Areas"]
)

# ==============================================================================
# TAB 1: ROUTE & TRANSFER PLANNER
# ==============================================================================
with tab_route:
    st.subheader("Where are you going in Phnom Penh?")

    # Build a combined searchable list of Bus Stops + Sangkats/Khans
    stop_places = stops_df[["stop_name_kh", "bus_line", "latitude", "longitude"]].drop_duplicates(
        subset=["stop_name_kh"]
    ).copy()
    stop_places["label"] = "🚏 Stop: " + stop_places["stop_name_kh"]

    admin_places = admin_df[admin_df["location_type"].isin(["Khan", "Sangkat"])][
        ["name", "location_type", "latitude", "longitude"]
    ].copy()
    admin_places["label"] = "📍 " + admin_places["location_type"] + ": " + admin_places["name"]

    places_df = pd.concat(
        [
            stop_places[["label", "latitude", "longitude"]],
            admin_places[["label", "latitude", "longitude"]],
        ],
        ignore_index=True,
    )

    place_labels = places_df["label"].tolist()

    # Default example: Ta Khmau Roundabout -> ITC (សាលាតិចណូ)
    default_start = next(
        (i for i, x in enumerate(place_labels) if "រង្វង់មូលតាខ្មៅ" in x), 0
    )
    default_end = next(
        (i for i, x in enumerate(place_labels) if "សាលាតិចណូ" in x), 1
    )

    c1, c2 = st.columns(2)
    with c1:
        origin_label = st.selectbox("From (Current Location)", place_labels, index=default_start)
    with c2:
        dest_label = st.selectbox("To (Destination)", place_labels, index=default_end)

    origin_row = places_df[places_df["label"] == origin_label].iloc[0]
    dest_row = places_df[places_df["label"] == dest_label].iloc[0]

    itinerary = router.find_route(
        origin_row["latitude"],
        origin_row["longitude"],
        dest_row["latitude"],
        dest_row["longitude"],
    )

    if not itinerary:
        st.error("No connected bus route found between these two locations.")
    else:
        # Summary KPIs
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Bus Transfers Needed", f"{itinerary['num_transfers']} transfer(s)")
        m2.metric("Total Bus Ride", f"{itinerary['total_ride_km']} km")
        m3.metric("Walk to First Stop", f"{itinerary['walk_to_first_stop_m']:.0f} m")
        m4.metric("Walk to Destination", f"{itinerary['walk_from_last_stop_m']:.0f} m")

        left_col, right_col = st.columns([1, 1.4])

        with left_col:
            st.markdown("### 📋 Step-by-Step Directions")

            if itinerary["walk_to_first_stop_m"] > 20:
                st.info(
                    f"🚶 **Walk {itinerary['walk_to_first_stop_m']:.0f}m** to boarding stop: "
                    f"**{itinerary['segments'][0]['board_stop']}**"
                )

            for idx, seg in enumerate(itinerary["segments"], start=1):
                num_stops = len(seg["stops"]) - 1
                st.success(
                    f"**Step {idx} — Take {seg['bus_line']}**\n\n"
                    f"- **Board at:** {seg['board_stop']}\n"
                    f"- **Ride:** {num_stops} stop(s) ({seg['distance_m']/1000:.2f} km)\n"
                    f"- **Get off at:** {seg['alight_stop']}"
                )

                if idx - 1 < len(itinerary["transfers"]):
                    tr = itinerary["transfers"][idx - 1]
                    st.warning(
                        f"🔄 **CHANGE BUS ({tr['walk_m']:.0f}m walk)**\n\n"
                        f"Get off **{tr['from_line']}** at **{tr['from_stop']}** "
                        f"→ Switch to **{tr['to_line']}** at **{tr['to_stop']}**"
                    )

            if itinerary["walk_from_last_stop_m"] > 20:
                st.info(
                    f"🚶 **Walk {itinerary['walk_from_last_stop_m']:.0f}m** from "
                    f"**{itinerary['segments'][-1]['alight_stop']}** to your destination."
                )

        with right_col:
            st.markdown("### 🗺️ Route Map")
            mid_lat = (origin_row["latitude"] + dest_row["latitude"]) / 2
            mid_lng = (origin_row["longitude"] + dest_row["longitude"]) / 2
            route_map = folium.Map(location=[mid_lat, mid_lng], zoom_start=12, tiles="OpenStreetMap")

            # Start & End Pins
            folium.Marker(
                [origin_row["latitude"], origin_row["longitude"]],
                tooltip=f"Start: {origin_label}",
                icon=folium.Icon(color="green", icon="play"),
            ).add_to(route_map)

            folium.Marker(
                [dest_row["latitude"], dest_row["longitude"]],
                tooltip=f"Destination: {dest_label}",
                icon=folium.Icon(color="red", icon="flag"),
            ).add_to(route_map)

            seg_colors = ["#0055ff", "#e6194b", "#911eb4", "#f58231"]
            for s_idx, seg in enumerate(itinerary["segments"]):
                color = seg_colors[s_idx % len(seg_colors)]
                coords = [(s["latitude"], s["longitude"]) for s in seg["stops"]]
                if len(coords) > 1:
                    folium.PolyLine(
                        coords,
                        color=color,
                        weight=5,
                        opacity=0.9,
                        tooltip=f"{seg['bus_line']}: {seg['board_stop']} → {seg['alight_stop']}",
                    ).add_to(route_map)

                for stop in seg["stops"]:
                    folium.CircleMarker(
                        [stop["latitude"], stop["longitude"]],
                        radius=4,
                        color=color,
                        fill=True,
                        fill_color=color,
                        tooltip=f"{stop['stop_name_kh']} ({seg['bus_line']})",
                    ).add_to(route_map)

            # Highlight transfer points with orange circles
            for tr in itinerary["transfers"]:
                tr_stop = next(
                    (n for n in itinerary["path_nodes"] if n["stop_name_kh"] == tr["to_stop"]),
                    None,
                )
                if tr_stop:
                    folium.Marker(
                        [tr_stop["latitude"], tr_stop["longitude"]],
                        tooltip=f"TRANSFER: {tr['from_line']} → {tr['to_line']} at {tr['to_stop']}",
                        icon=folium.Icon(color="orange", icon="refresh"),
                    ).add_to(route_map)

            st_folium(route_map, width=None, height=520, returned_objects=[])


# ==============================================================================
# TAB 2: CITY COVERAGE & UNDERSERVED AREAS
# ==============================================================================
with tab_coverage:
    st.caption("Green dots = Well-served areas | Red dots = Underserved areas (far from any bus stop)")

    all_lines = sorted(stops_df["bus_line"].dropna().unique().tolist())

    f1, f2, f3 = st.columns([2, 1, 1])
    with f1:
        selected_lines = st.multiselect("Filter Bus Lines", options=all_lines, default=all_lines)
    with f2:
        admin_level = st.selectbox("Administrative Layer", options=["Sangkat", "Village", "Khan"], index=0)
    with f3:
        walk_threshold_m = st.slider("Walk Threshold (m)", 200, 2000, 500, 100)

    filtered_stops = stops_df[stops_df["bus_line"].isin(selected_lines)]
    filtered_admin = admin_df[admin_df["location_type"] == admin_level].copy()
    filtered_admin["is_underserved"] = filtered_admin["nearest_stop_m"] > walk_threshold_m

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Bus Stops Shown", f"{len(filtered_stops):,}")
    k2.metric("Bus Lines Selected", f"{len(selected_lines)} / {len(all_lines)}")
    underserved_count = int(filtered_admin["is_underserved"].sum())
    total_admin = len(filtered_admin)
    k3.metric(
        f"Underserved {admin_level}s (>{walk_threshold_m}m)",
        f"{underserved_count} / {total_admin}",
        f"{(underserved_count / total_admin * 100):.1f}% outside radius",
        delta_color="inverse",
    )
    k4.metric(f"Median Distance ({admin_level})", f"{filtered_admin['nearest_stop_m'].median():.0f} m")

    cov_map = folium.Map(location=[11.5564, 104.9282], zoom_start=12, tiles="OpenStreetMap")
    line_color_map = {line: LINE_COLORS[i % len(LINE_COLORS)] for i, line in enumerate(all_lines)}

    for line in selected_lines:
        line_stops = filtered_stops[filtered_stops["bus_line"] == line].sort_values("stop_number")
        coords = list(zip(line_stops["latitude"], line_stops["longitude"]))
        if len(coords) > 1:
            folium.PolyLine(
                coords,
                color=line_color_map.get(line, "#3388ff"),
                weight=3,
                opacity=0.75,
                tooltip=line,
            ).add_to(cov_map)

    for _, row in filtered_admin.iterrows():
        is_far = row["is_underserved"]
        marker_color = "#d90429" if is_far else "#2b9348"
        folium.CircleMarker(
            [row["latitude"], row["longitude"]],
            radius=6 if admin_level != "Village" else 3.5,
            color=marker_color,
            fill=True,
            fill_color=marker_color,
            fill_opacity=0.75,
            tooltip=f"{row['name']} ({row['nearest_stop_m']:.0f}m to nearest stop)",
        ).add_to(cov_map)

    st_folium(cov_map, width=None, height=500, returned_objects=[])
