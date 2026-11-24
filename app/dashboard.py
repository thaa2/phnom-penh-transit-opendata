import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import folium
from folium.plugins import AntPath, LocateControl
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from streamlit_geolocation import streamlit_geolocation
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

st.title("🚌 CamTransit AI — Phnom Penh Smart Transit Navigator")

tab_route, tab_coverage = st.tabs(
    ["🧭 Live Route & Transfer Navigator", "🗺️ City Coverage & Underserved Areas"]
)

# ==============================================================================
# TAB 1: LIVE ROUTE & TRANSFER NAVIGATOR
# ==============================================================================
with tab_route:
    stop_places = (
        stops_df[["stop_name_kh", "bus_line", "latitude", "longitude"]]
        .drop_duplicates(subset=["stop_name_kh"])
        .copy()
    )
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

    default_start = next((i for i, x in enumerate(place_labels) if "រង្វង់មូលតាខ្មៅ" in x), 0)
    default_end = next((i for i, x in enumerate(place_labels) if "សាលាតិចណូ" in x), 1)

    # --- Compact GPS Toggle Row ---
    gps_toggle_col, gps_btn_col, _ = st.columns([0.8, 0.6, 3.6])
    with gps_toggle_col:
        use_gps = st.checkbox("📡 Use Live GPS", value=False)
    user_loc = None
    with gps_btn_col:
        if use_gps:
            user_loc = streamlit_geolocation()

    # --- Perfectly Aligned Origin & Destination Bars ---
    start_col, end_col = st.columns(2)

    with start_col:
        if use_gps and user_loc and user_loc.get("latitude") is not None:
            origin_lat = float(user_loc["latitude"])
            origin_lng = float(user_loc["longitude"])
            origin_label = f"📡 My Live GPS ({origin_lat:.5f}, {origin_lng:.5f})"
            st.text_input("From (Current Location)", value=origin_label, disabled=True)
        else:
            origin_label = st.selectbox("From (Current Location)", place_labels, index=default_start)
            origin_row = places_df[places_df["label"] == origin_label].iloc[0]
            origin_lat, origin_lng = float(origin_row["latitude"]), float(origin_row["longitude"])
            if use_gps:
                st.caption("Click the target button above to lock onto your GPS.")

    with end_col:
        dest_label = st.selectbox("To (Destination)", place_labels, index=default_end)
        dest_row = places_df[places_df["label"] == dest_label].iloc[0]
        dest_lat, dest_lng = float(dest_row["latitude"]), float(dest_row["longitude"])

    itinerary = router.find_route(origin_lat, origin_lng, dest_lat, dest_lng)

    if not itinerary:
        st.error("No connected bus route found between these two locations.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Bus Transfers", f"{itinerary['num_transfers']} change(s)")
        m2.metric("Total Bus Ride", f"{itinerary['total_ride_km']} km")
        m3.metric("Walk to First Stop", f"{itinerary['walk_to_first_stop_m']:.0f} m")
        m4.metric("Walk to Destination", f"{itinerary['walk_from_last_stop_m']:.0f} m")

        left_col, right_col = st.columns([0.75, 2.25])

        with left_col:
            st.markdown("#### 📋 Route & Transfers")

            if itinerary["walk_to_first_stop_m"] > 15:
                st.info(
                    f"🚶 **Walk {itinerary['walk_to_first_stop_m']:.0f}m** → "
                    f"**{itinerary['segments'][0]['board_stop']}**"
                )

            for idx, seg in enumerate(itinerary["segments"], start=1):
                num_stops = len(seg["stops"]) - 1

                st.success(
                    f"**Leg {idx}: {seg['bus_line']}**\n\n"
                    f"- **Board:** {seg['board_stop']}\n"
                    f"- **Ride:** {num_stops} stops ({seg['distance_m']/1000:.2f} km)\n"
                    f"- **Exit:** {seg['alight_stop']}"
                )

                if idx - 1 < len(itinerary["transfers"]):
                    tr = itinerary["transfers"][idx - 1]
                    st.warning(
                        f"🔄 **TRANSFER ({tr['walk_m']:.0f}m walk)**\n\n"
                        f"**{tr['from_stop']}** ({tr['from_line']}) → "
                        f"**{tr['to_stop']}** ({tr['to_line']})"
                    )

            if itinerary["walk_from_last_stop_m"] > 15:
                st.info(
                    f"🚶 **Walk {itinerary['walk_from_last_stop_m']:.0f}m** to destination"
                )

        with right_col:
            st.markdown("#### 🗺️ Live Transit Map")
            mid_lat = (origin_lat + dest_lat) / 2
            mid_lng = (origin_lng + dest_lng) / 2
            route_map = folium.Map(location=[mid_lat, mid_lng], zoom_start=12, tiles="OpenStreetMap")

            LocateControl(auto_start=use_gps, position="topleft").add_to(route_map)

            folium.Marker(
                [origin_lat, origin_lng],
                tooltip=f"Start: {origin_label}",
                icon=folium.Icon(color="blue" if use_gps else "green", icon="user" if use_gps else "play"),
            ).add_to(route_map)

            folium.Marker(
                [dest_lat, dest_lng],
                tooltip=f"Destination: {dest_label}",
                icon=folium.Icon(color="red", icon="flag"),
            ).add_to(route_map)

            first_stop = itinerary["segments"][0]["stops"][0]
            folium.PolyLine(
                [(origin_lat, origin_lng), (first_stop["latitude"], first_stop["longitude"])],
                color="#555555",
                weight=3,
                dash_array="6, 8",
                tooltip=f"Walk {itinerary['walk_to_first_stop_m']:.0f}m to {first_stop['stop_name_kh']}",
            ).add_to(route_map)

            seg_colors = ["#0055ff", "#e6194b", "#911eb4", "#008080"]
            for s_idx, seg in enumerate(itinerary["segments"]):
                color = seg_colors[s_idx % len(seg_colors)]
                coords = [(s["latitude"], s["longitude"]) for s in seg["stops"]]
                if len(coords) > 1:
                    AntPath(
                        locations=coords,
                        color=color,
                        pulse_color="#ffffff",
                        weight=6,
                        delay=800,
                        tooltip=f"{seg['bus_line']}: {seg['board_stop']} → {seg['alight_stop']}",
                    ).add_to(route_map)

                for step_i, stop in enumerate(seg["stops"], start=1):
                    folium.CircleMarker(
                        [stop["latitude"], stop["longitude"]],
                        radius=4.5,
                        color=color,
                        fill=True,
                        fill_color="#ffffff" if step_i not in (1, len(seg["stops"])) else color,
                        fill_opacity=1.0,
                        tooltip=f"#{step_i} {stop['stop_name_kh']} ({seg['bus_line']})",
                    ).add_to(route_map)

            for t_idx, tr in enumerate(itinerary["transfers"]):
                seg_before_last_stop = itinerary["segments"][t_idx]["stops"][-1]
                seg_after_first_stop = itinerary["segments"][t_idx + 1]["stops"][0]

                folium.PolyLine(
                    [
                        (seg_before_last_stop["latitude"], seg_before_last_stop["longitude"]),
                        (seg_after_first_stop["latitude"], seg_after_first_stop["longitude"]),
                    ],
                    color="#ff8800",
                    weight=4,
                    dash_array="5, 8",
                    tooltip=f"Transfer Walk ({tr['walk_m']:.0f}m): {tr['from_stop']} → {tr['to_stop']}",
                ).add_to(route_map)

                folium.Marker(
                    [seg_after_first_stop["latitude"], seg_after_first_stop["longitude"]],
                    tooltip=f"TRANSFER HERE: {tr['from_line']} → {tr['to_line']} at {tr['to_stop']}",
                    icon=folium.Icon(color="orange", icon="refresh"),
                ).add_to(route_map)

            last_stop = itinerary["segments"][-1]["stops"][-1]
            folium.PolyLine(
                [(last_stop["latitude"], last_stop["longitude"]), (dest_lat, dest_lng)],
                color="#555555",
                weight=3,
                dash_array="6, 8",
                tooltip=f"Walk {itinerary['walk_from_last_stop_m']:.0f}m to destination",
            ).add_to(route_map)

            st_folium(route_map, width=None, height=680, returned_objects=[])


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
    LocateControl(auto_start=False, position="topleft").add_to(cov_map)
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

    st_folium(cov_map, width=None, height=620, returned_objects=[])
