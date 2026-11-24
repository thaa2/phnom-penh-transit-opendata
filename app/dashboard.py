import re
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

# Common Khmer -> English transit landmark glossary for searchable bilingual labels
KH_EN_GLOSSARY = {
    "សាលាតិចណូ": "Sala Techno (ITC)",
    "រង្វង់មូលតាខ្មៅ": "Ta Khmau Roundabout",
    "ផ្សារតាខ្មៅ": "Ta Khmau Market",
    "សាលាក្រុងតាខ្មៅ": "Ta Khmau City Hall",
    "ផ្សារធំថ្មី": "Central Market (Phsar Thmey)",
    "ផ្សារអូរឫស្សី": "Orussey Market",
    "ផ្សារដើមគរ": "Doeum Kor Market",
    "ផ្សារចាស់": "Old Market (Phsar Chas)",
    "ផ្សាររាត្រី": "Night Market",
    "មន្ទីរពេទ្យព្រះអង្គឌួង": "Preah Ang Duong Hospital",
    "មន្ទីរពេទ្យកាល់ម៉ែត": "Calmette Hospital",
    "មន្ទីរពេទ្យមិត្តភាពខ្មែរ-សូវៀត": "Khmer-Soviet Friendship Hospital",
    "វិមានឯករាជ្យ": "Independence Monument",
    "វត្តភ្នំ": "Wat Phnom",
    "ព្រលានយន្តហោះអន្តរជាតិភ្នំពេញ": "Phnom Penh International Airport",
    "សាកលវិទ្យាល័យភូមិន្ទភ្នំពេញ": "Royal University of Phnom Penh (RUPP)",
    "ស្ពានជ្រោយចង្វារ": "Chroy Changvar Bridge",
    "ស្ពានព្រះមុនីវង្ស": "Monivong Bridge",
    "ស្ពានអាកាសក្បាលថ្នល់": "Kbal Thnal Skybridge",
    "ស្ពានអាកាសស្ទឹងមានជ័យ": "Stung Meanchey Skybridge",
    "ស្ពានអាកាស៥មករា": "5 Makara Skybridge",
    "ស្ពានអាកាស៧មករា": "7 Makara Skybridge",
    "ផ្សារទំនើបអ៊ីអន": "AEON Mall",
}

UI_TEXT = {
    "en": {
        "title": "🚌 CamTransit AI — Phnom Penh Smart Transit Navigator",
        "tab_route": "🧭 Live Route & Transfer Navigator",
        "tab_cov": "🗺️ City Coverage & Underserved Areas",
        "use_gps": "📡 Use Live GPS",
        "gps_hint": "Click the target button above to lock onto your GPS.",
        "my_gps": "📡 My Live GPS",
        "from_label": "From (Current Location)",
        "to_label": "To (Destination)",
        "no_route": "No connected bus route found between these two locations.",
        "m_transfers": "Bus Transfers",
        "m_transfers_unit": "change(s)",
        "m_ride": "Total Bus Ride",
        "m_walk_start": "Walk to First Stop",
        "m_walk_end": "Walk to Destination",
        "sec_route": "#### 📋 Route & Transfers",
        "sec_map": "#### 🗺️ Live Transit Map",
        "walk_to": "🚶 **Walk {dist:.0f}m** → **{stop}**",
        "leg_card": "**Leg {idx}: {line}**\n\n- **Board:** {board}\n- **Ride:** {stops} stops ({km:.2f} km)\n- **Exit:** {alight}",
        "transfer_card": "🔄 **TRANSFER ({walk:.0f}m walk)**\n\n**{f_stop}** ({f_line}) → **{t_stop}** ({t_line})",
        "walk_dest": "🚶 **Walk {dist:.0f}m** to destination",
        "cov_caption": "Green dots = Well-served areas | Red dots = Underserved areas (far from any bus stop)",
        "filter_lines": "Filter Bus Lines",
        "admin_layer": "Administrative Layer",
        "walk_thresh": "Walk Threshold (m)",
        "k_stops": "Bus Stops Shown",
        "k_lines": "Bus Lines Selected",
        "k_under": "Underserved {layer}s (>{thresh}m)",
        "k_under_sub": "{pct:.1f}% outside radius",
        "k_median": "Median Distance ({layer})",
    },
    "km": {
        "title": "🚌 CamTransit AI — ប្រព័ន្ធណែនាំផ្លូវរថយន្តក្រុងឆ្លាតវៃរាជធានីភ្នំពេញ",
        "tab_route": "🧭 ស្វែងរកផ្លូវ និងការប្តូរខ្សែរថយន្តក្រុង",
        "tab_cov": "🗺️ តំបន់គ្របដណ្តប់ និងតំបន់ខ្វះសេវាដឹកជញ្ជូន",
        "use_gps": "📡 ប្រើទីតាំង GPS ផ្ទាល់",
        "gps_hint": "សូមចុចប៊ូតុងគោលដៅខាងលើ ដើម្បីចាប់យកទីតាំង GPS របស់អ្នក។",
        "my_gps": "📡 ទីតាំង GPS ផ្ទាល់របស់ខ្ញុំ",
        "from_label": "ចេញដំណើរពី (ទីតាំងបច្ចុប្បន្ន)",
        "to_label": "ទៅកាន់ (គោលដៅ)",
        "no_route": "រកមិនឃើញខ្សែរថយន្តក្រុងតភ្ជាប់រវាងទីតាំងទាំងពីរនេះទេ។",
        "m_transfers": "ចំនួនប្តូររថយន្ត",
        "m_transfers_unit": "ដង",
        "m_ride": "ចម្ងាយជិះសរុប",
        "m_walk_start": "ដើរទៅចំណតដំបូង",
        "m_walk_end": "ដើរទៅគោលដៅ",
        "sec_route": "#### 📋 ជំហានធ្វើដំណើរ និងការប្តូរខ្សែ",
        "sec_map": "#### 🗺️ ផែនទីបង្ហាញទិសដៅផ្ទាល់",
        "walk_to": "🚶 **ដើរចម្ងាយ {dist:.0f} ម៉ែត្រ** → **{stop}**",
        "leg_card": "**ជំហានទី {idx}៖ ជិះ {line}**\n\n- **ឡើងនៅចំណត៖** {board}\n- **ជិះកាត់៖** {stops} ចំណត ({km:.2f} គ.ម)\n- **ចុះនៅចំណត៖** {alight}",
        "transfer_card": "🔄 **ប្តូរខ្សែរថយន្តក្រុង (ដើរ {walk:.0f} ម៉ែត្រ)**\n\nចុះពី **{f_stop}** ({f_line}) → ឡើងនៅ **{t_stop}** ({t_line})",
        "walk_dest": "🚶 **ដើរចម្ងាយ {dist:.0f} ម៉ែត្រ** ទៅដល់គោលដៅ",
        "cov_caption": "ចំណុចពណ៌បៃតង = តំបន់មានសេវារថយន្តក្រុង | ចំណុចពណ៌ក្រហម = តំបន់ឆ្ងាយពីចំណតរថយន្តក្រុង",
        "filter_lines": "ជ្រើសរើសខ្សែរថយន្តក្រុង",
        "admin_layer": "កម្រិតរដ្ឋបាល",
        "walk_thresh": "ចម្ងាយដើរអតិបរមា (ម៉ែត្រ)",
        "k_stops": "ចំណតរថយន្តក្រុងបង្ហាញ",
        "k_lines": "ខ្សែរថយន្តបានជ្រើសរើស",
        "k_under": "{layer} ដែលខ្វះសេវា (>{thresh}m)",
        "k_under_sub": "{pct:.1f}% នៅក្រៅរង្វង់ដើរ",
        "k_median": "ចម្ងាយមធ្យម ({layer})",
    },
}


def format_bus_line(line_kh: str, lang: str) -> str:
    """Display bilingual bus line label e.g. 'Bus Line 2 (ខ្សែរថយន្តក្រុងទី ២)'."""
    kh_digits = str.maketrans("០១២៣៤៥៦៧៨៩", "0123456789")
    normalized = str(line_kh).translate(kh_digits)
    match = re.search(r"(\d+\s*[A-C]?)", normalized)
    en_name = f"Bus Line {match.group(1).strip()}" if match else str(line_kh)
    return f"{en_name} ({line_kh})" if lang == "en" else f"{line_kh} ({en_name})"


def format_stop_name(stop_kh: str) -> str:
    """Append English landmark name if available in glossary for easy bilingual search."""
    clean = str(stop_kh).strip()
    for kh_key, en_val in KH_EN_GLOSSARY.items():
        if kh_key in clean:
            return f"{clean} — {en_val}"
    return clean


@st.cache_data
def load_data():
    stops = pd.read_csv(DATA_DIR / "bus_stops_clean.csv")
    admin = pd.read_csv(DATA_DIR / "admin_transit_coverage.csv")
    stops["stop_bilingual"] = stops["stop_name_kh"].apply(format_stop_name)
    return stops, admin


@st.cache_resource
def get_router(stops_df):
    return TransitRouter(stops_df, transfer_radius_m=250.0)


stops_df, admin_df = load_data()
router = get_router(stops_df)

# --- Top Header + Language Switcher ---
title_col, lang_col = st.columns([4.2, 0.8])
with lang_col:
    lang_choice = st.radio(
        "Language / ភាសា",
        options=["English", "ភាសាខ្មែរ"],
        horizontal=True,
        label_visibility="collapsed",
    )
lang = "en" if lang_choice == "English" else "km"
t = UI_TEXT[lang]

with title_col:
    st.title(t["title"])

tab_route, tab_coverage = st.tabs([t["tab_route"], t["tab_cov"]])

# ==============================================================================
# TAB 1: LIVE ROUTE & TRANSFER NAVIGATOR
# ==============================================================================
with tab_route:
    stop_places = (
        stops_df[["stop_bilingual", "latitude", "longitude"]]
        .drop_duplicates(subset=["stop_bilingual"])
        .copy()
    )
    stop_places["label"] = "🚏 " + stop_places["stop_bilingual"]

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
    gps_toggle_col, gps_btn_col, _ = st.columns([1.0, 0.6, 3.4])
    with gps_toggle_col:
        use_gps = st.checkbox(t["use_gps"], value=False)
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
            origin_label = f"{t['my_gps']} ({origin_lat:.5f}, {origin_lng:.5f})"
            st.text_input(t["from_label"], value=origin_label, disabled=True)
        else:
            origin_label = st.selectbox(t["from_label"], place_labels, index=default_start)
            origin_row = places_df[places_df["label"] == origin_label].iloc[0]
            origin_lat, origin_lng = float(origin_row["latitude"]), float(origin_row["longitude"])
            if use_gps:
                st.caption(t["gps_hint"])

    with end_col:
        dest_label = st.selectbox(t["to_label"], place_labels, index=default_end)
        dest_row = places_df[places_df["label"] == dest_label].iloc[0]
        dest_lat, dest_lng = float(dest_row["latitude"]), float(dest_row["longitude"])

    itinerary = router.find_route(origin_lat, origin_lng, dest_lat, dest_lng)

    if not itinerary:
        st.error(t["no_route"])
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(t["m_transfers"], f"{itinerary['num_transfers']} {t['m_transfers_unit']}")
        m2.metric(t["m_ride"], f"{itinerary['total_ride_km']} km")
        m3.metric(t["m_walk_start"], f"{itinerary['walk_to_first_stop_m']:.0f} m")
        m4.metric(t["m_walk_end"], f"{itinerary['walk_from_last_stop_m']:.0f} m")

        left_col, right_col = st.columns([0.8, 2.2])

        with left_col:
            st.markdown(t["sec_route"])

            if itinerary["walk_to_first_stop_m"] > 15:
                st.info(
                    t["walk_to"].format(
                        dist=itinerary["walk_to_first_stop_m"],
                        stop=format_stop_name(itinerary["segments"][0]["board_stop"]),
                    )
                )

            for idx, seg in enumerate(itinerary["segments"], start=1):
                num_stops = len(seg["stops"]) - 1
                st.success(
                    t["leg_card"].format(
                        idx=idx,
                        line=format_bus_line(seg["bus_line"], lang),
                        board=format_stop_name(seg["board_stop"]),
                        stops=num_stops,
                        km=seg["distance_m"] / 1000,
                        alight=format_stop_name(seg["alight_stop"]),
                    )
                )

                if idx - 1 < len(itinerary["transfers"]):
                    tr = itinerary["transfers"][idx - 1]
                    st.warning(
                        t["transfer_card"].format(
                            walk=tr["walk_m"],
                            f_stop=format_stop_name(tr["from_stop"]),
                            f_line=format_bus_line(tr["from_line"], lang),
                            t_stop=format_stop_name(tr["to_stop"]),
                            t_line=format_bus_line(tr["to_line"], lang),
                        )
                    )

            if itinerary["walk_from_last_stop_m"] > 15:
                st.info(t["walk_dest"].format(dist=itinerary["walk_from_last_stop_m"]))

        with right_col:
            st.markdown(t["sec_map"])
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
                tooltip=f"Walk {itinerary['walk_to_first_stop_m']:.0f}m → {format_stop_name(first_stop['stop_name_kh'])}",
            ).add_to(route_map)

            seg_colors = ["#0055ff", "#e6194b", "#911eb4", "#008080"]
            for s_idx, seg in enumerate(itinerary["segments"]):
                color = seg_colors[s_idx % len(seg_colors)]
                coords = [(s["latitude"], s["longitude"]) for s in seg["stops"]]
                line_label = format_bus_line(seg["bus_line"], lang)
                if len(coords) > 1:
                    AntPath(
                        locations=coords,
                        color=color,
                        pulse_color="#ffffff",
                        weight=6,
                        delay=800,
                        tooltip=f"{line_label}: {seg['board_stop']} → {seg['alight_stop']}",
                    ).add_to(route_map)

                for step_i, stop in enumerate(seg["stops"], start=1):
                    folium.CircleMarker(
                        [stop["latitude"], stop["longitude"]],
                        radius=4.5,
                        color=color,
                        fill=True,
                        fill_color="#ffffff" if step_i not in (1, len(seg["stops"])) else color,
                        fill_opacity=1.0,
                        tooltip=f"#{step_i} {format_stop_name(stop['stop_name_kh'])} ({line_label})",
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
                    tooltip=f"TRANSFER / ប្តូរខ្សែ: {format_bus_line(tr['from_line'], lang)} → {format_bus_line(tr['to_line'], lang)}",
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
    st.caption(t["cov_caption"])

    all_lines = sorted(stops_df["bus_line"].dropna().unique().tolist())

    f1, f2, f3 = st.columns([2, 1, 1])
    with f1:
        selected_lines = st.multiselect(
            t["filter_lines"],
            options=all_lines,
            default=all_lines,
            format_func=lambda x: format_bus_line(x, lang),
        )
    with f2:
        admin_level = st.selectbox(t["admin_layer"], options=["Sangkat", "Village", "Khan"], index=0)
    with f3:
        walk_threshold_m = st.slider(t["walk_thresh"], 200, 2000, 500, 100)

    filtered_stops = stops_df[stops_df["bus_line"].isin(selected_lines)]
    filtered_admin = admin_df[admin_df["location_type"] == admin_level].copy()
    filtered_admin["is_underserved"] = filtered_admin["nearest_stop_m"] > walk_threshold_m

    k1, k2, k3, k4 = st.columns(4)
    k1.metric(t["k_stops"], f"{len(filtered_stops):,}")
    k2.metric(t["k_lines"], f"{len(selected_lines)} / {len(all_lines)}")
    underserved_count = int(filtered_admin["is_underserved"].sum())
    total_admin = len(filtered_admin)
    k3.metric(
        t["k_under"].format(layer=admin_level, thresh=walk_threshold_m),
        f"{underserved_count} / {total_admin}",
        t["k_under_sub"].format(pct=(underserved_count / total_admin * 100) if total_admin else 0),
        delta_color="inverse",
    )
    k4.metric(
        t["k_median"].format(layer=admin_level),
        f"{filtered_admin['nearest_stop_m'].median():.0f} m",
    )

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
                tooltip=format_bus_line(line, lang),
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
