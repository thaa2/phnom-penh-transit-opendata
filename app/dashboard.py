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
from src.road_geometry import snap_to_road

st.set_page_config(
    page_title="CamTransit AI — Phnom Penh Smart Transit",
    page_icon="🚌",
    layout="wide",
)

DATA_DIR = Path("data/processed")

LINE_COLORS = [
    "#3cb44b", "#3cb44b", "#3cb44b", "#e6194b",
    "#e6194b", "#e6194b", "#1e5aa8", "#e888b3",
    "#f58231", "#911eb4", "#008080", "#9a6324",
    "#800000", "#000075", "#808000", "#46f0f0",
]

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

SERVICES_DATA = {
    "daily": {
        "icon": "🚌",
        "title_en": "Daily Bus Operations",
        "title_km": "ប្រតិបត្តិការខ្សែរត់ប្រចាំថ្ងៃ",
        "days_en": "Daily (Monday – Sunday)",
        "days_km": "ដំណើរការរៀងរាល់ថ្ងៃ",
        "hours_en": "05:30 AM – 08:30 PM",
        "hours_km": "០៥:៣០នាទីព្រឹក ដល់ ២០:៣០នាទីយប់",
        "wait_en": "10 to 15 minutes",
        "wait_km": "១០ ទៅ ១៥ នាទី",
        "price_en": "1,500 KHR",
        "price_km": "១៥០០ រៀល",
        "qty_en": "1 Person",
        "qty_km": "១ នាក់",
        "valid_en": "1 Trip",
        "valid_km": "១ លើក",
        "line_codes": ["1", "2", "3", "4A", "4C", "5A", "5B", "6", "7", "8", "9", "10", "11", "12", "13"],
        "note_en": "Covers all regular Phnom Penh City Bus routes across the capital and Ta Khmau.",
        "note_km": "គ្របដណ្តប់គ្រប់ខ្សែរថយន្តក្រុងសាធារណៈប្រចាំថ្ងៃក្នុងរាជធានីភ្នំពេញ និងក្រុងតាខ្មៅ។",
    },
    "walk_street": {
        "icon": "🚶‍♂️🚌",
        "title_en": "Weekend Walk Street Support",
        "title_km": "ប្រតិបត្តិការខ្សែរត់គាំទ្រផ្លូវថ្មើរជើង (Walk Street)",
        "days_en": "Every Saturday & Sunday",
        "days_km": "រៀងរាល់ថ្ងៃសៅរ៍ និងថ្ងៃអាទិត្យ",
        "hours_en": "06:00 PM – 11:00 PM",
        "hours_km": "១៨:០០នាទីរសៀល ដល់ ២៣:០០នាទីយប់",
        "wait_en": "10 to 15 minutes",
        "wait_km": "១០ ទៅ ១៥ នាទី",
        "price_en": "1,500 KHR",
        "price_km": "១៥០០ រៀល",
        "qty_en": "1 Person",
        "qty_km": "១ នាក់",
        "valid_en": "1 Trip",
        "valid_km": "១ លើក",
        "line_codes": ["1", "2", "3", "4A"],
        "note_en": "Evening shuttle support connecting Riverside / Chaktomuk Walk Street visitors via Lines 1C, 2A, 3, and 4A.",
        "note_km": "សេវាដឹកជញ្ជូនពេលល្ងាចគាំទ្រអ្នកដើរកម្សាន្តផ្លូវថ្មើរជើងមាត់ទន្លេ តាមរយៈខ្សែទី 1C, 2A, 3 និង 4A។",
    },
    "aeb": {
        "icon": "✈️🚌",
        "title_en": "Airport Express Bus (AEB)",
        "title_km": "ប្រតិបត្តិការខ្សែរត់ Airport Express Bus (AEB)",
        "days_en": "Daily (Monday – Sunday)",
        "days_km": "រៀងរាល់ថ្ងៃ",
        "hours_en": "05:30 AM – 11:30 PM",
        "hours_km": "០៥:៣០នាទីព្រឹក ដល់ ២៣:៣០នាទីយប់",
        "wait_en": "10 to 15 minutes",
        "wait_km": "១០ ទៅ ១៥ នាទី",
        "price_en": "1,500 KHR",
        "price_km": "១៥០០ រៀល",
        "qty_en": "1 Person",
        "qty_km": "១ នាក់",
        "valid_en": "1 Trip",
        "valid_km": "១ លើក",
        "line_codes": ["AEB"],
        "note_en": "Direct express bus corridor connecting central Phnom Penh (Canadia Park / Monivong / Hun Sen Blvd) to Techo International Airport.",
        "note_km": "ខ្សែរថយន្តក្រុងពិសេសតភ្ជាប់ពីកណ្តាលរាជធានីភ្នំពេញ (សួនកាណាឌីយ៉ា / មហាវិថីព្រះមុនីវង្ស / មហាវិថីសម្តេចតេជោ ហ៊ុន សែន) ទៅអាកាសយានដ្ឋានអន្តរជាតិតេជោ។",
    },
}

AEB_STOPS = [
    {"stop_number": 1, "stop_name_kh": "ចំណតសួនកាណាឌីយ៉ា (Canadia Park Terminal)", "latitude": 11.5734, "longitude": 104.9189},
    {"stop_number": 2, "stop_name_kh": "ផ្សារធំថ្មី (Central Market)", "latitude": 11.5696, "longitude": 104.9211},
    {"stop_number": 3, "stop_name_kh": "ស្តុបបូកគោ (Bokor Traffic Light)", "latitude": 11.5453, "longitude": 104.9241},
    {"stop_number": 4, "stop_name_kh": "ស្ពានអាកាសក្បាលថ្នល់ (Kbal Thnal Skybridge)", "latitude": 11.5312, "longitude": 104.9298},
    {"stop_number": 5, "stop_name_kh": "ផ្សារទំនើបអ៊ីអន ៣ (AEON Mall Mean Chey)", "latitude": 11.4915, "longitude": 104.9265},
    {"stop_number": 6, "stop_name_kh": "រង្វង់មូលគួរស្រូវ (Kour Srov Roundabout)", "latitude": 11.4385, "longitude": 104.9182},
    {"stop_number": 7, "stop_name_kh": "អាកាសយានដ្ឋានអន្តរជាតិតេជោ (Techo International Airport)", "latitude": 11.3548, "longitude": 104.9288},
]

UI_TEXT = {
    "en": {
        "title": "🚌 CamTransit AI — Phnom Penh Smart Transit Navigator",
        "tab_route": "🧭 Live Route & Transfer Navigator",
        "tab_services": "🚏 Public Bus Services & Schedules",
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
        "sec_map": "#### 🗺️ Live Road-Snapped Transit Map",
        "walk_to": "🚶 **Walk {dist:.0f}m** → **{stop}**",
        "leg_card": "**{idx}. {line}**\n\n- **Board:** {board}\n- **Ride:** {stops} stops ({km:.2f} km)\n- **Exit:** {alight}",
        "transfer_card": "🔄 **TRANSFER ({walk:.0f}m walk)**\n\n**{f_stop}** ({f_line}) → **{t_stop}** ({t_line})",
        "walk_dest": "🚶 **Walk {dist:.0f}m** to destination",
        "svc_header": "Public Bus Services",
        "svc_choose": "Select a Bus Service:",
        "op_hours_title": "🕒 Operating Hours",
        "op_days": "Operating Days",
        "op_time": "Service Hours",
        "op_wait": "Waiting Interval",
        "ticket_title": "🎟️ Ticket Fare",
        "col_price": "Price",
        "col_qty": "Passengers",
        "col_valid": "Validity",
        "route_map_title": "🗺️ Public Bus Route Map",
        "select_line_label": "Select Bus Line to Inspect on Map",
        "all_service_lines": "All Lines in This Service",
        "stops_count_badge": "{n} stops along selected route",
    },
    "km": {
        "title": "🚌 CamTransit AI — ប្រព័ន្ធណែនាំផ្លូវរថយន្តក្រុងឆ្លាតវៃរាជធានីភ្នំពេញ",
        "tab_route": "🧭 ស្វែងរកផ្លូវ និងការប្តូរខ្សែរថយន្តក្រុង",
        "tab_services": "🚏 សេវាកម្មរបស់រថយន្តក្រុងសាធារណៈ",
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
        "sec_map": "#### 🗺️ ផែនទីបង្ហាញទិសដៅតាមបណ្តោយផ្លូវ",
        "walk_to": "🚶 **ដើរចម្ងាយ {dist:.0f} ម៉ែត្រ** → **{stop}**",
        "leg_card": "**{idx}. ជិះ {line}**\n\n- **ឡើងនៅចំណត៖** {board}\n- **ជិះកាត់៖** {stops} ចំណត ({km:.2f} គ.ម)\n- **ចុះនៅចំណត៖** {alight}",
        "transfer_card": "🔄 **ប្តូរខ្សែរថយន្តក្រុង (ដើរ {walk:.0f} ម៉ែត្រ)**\n\nចុះពី **{f_stop}** ({f_line}) → ឡើងនៅ **{t_stop}** ({t_line})",
        "walk_dest": "🚶 **ដើរចម្ងាយ {dist:.0f} ម៉ែត្រ** ទៅដល់គោលដៅ",
        "svc_header": "សេវាកម្មរបស់រថយន្តក្រុងសាធារណៈ",
        "svc_choose": "ជ្រើសរើសប្រភេទសេវាកម្ម៖",
        "op_hours_title": "🕒 ពេលវេលាប្រតិបត្តិការ",
        "op_days": "ថ្ងៃប្រតិបត្តិការ",
        "op_time": "ម៉ោងប្រតិបត្តិការ",
        "op_wait": "រយៈពេលរង់ចាំចន្លោះ",
        "ticket_title": "🎟️ តម្លៃសំបុត្រ",
        "col_price": "តម្លៃ",
        "col_qty": "ចំនួន",
        "col_valid": "សុពលភាព",
        "route_map_title": "🗺️ តម្រាយផ្លូវរថយន្តក្រុងសាធារណៈ",
        "select_line_label": "ជ្រើសរើសខ្សែរថយន្តក្រុងដើម្បីមើលលើផែនទី",
        "all_service_lines": "បង្ហាញគ្រប់ខ្សែក្នុងសេវាកម្មនេះ",
        "stops_count_badge": "មាន {n} ចំណតតាមបណ្តោយផ្លូវដែលបានជ្រើសរើស",
    },
}


def extract_line_code(line_kh: str) -> str:
    kh_digits = str.maketrans("០១២៣៤៥៦៧៨៩", "0123456789")
    normalized = str(line_kh).translate(kh_digits)
    match = re.search(r"(\d+\s*[A-C]?)", normalized)
    return match.group(1).replace(" ", "") if match else str(line_kh)


def format_bus_line(line_kh: str, lang: str) -> str:
    code = extract_line_code(line_kh)
    en_name = f"Bus Line {code}"
    return f"{en_name} ({line_kh})" if lang == "en" else f"{line_kh} ({en_name})"


def format_stop_name(stop_kh: str) -> str:
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
    stops["line_code"] = stops["bus_line"].apply(extract_line_code)
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

tab_route, tab_services = st.tabs([t["tab_route"], t["tab_services"]])

# ==============================================================================
# TAB 1: LIVE ROUTE & TRANSFER NAVIGATOR (ROAD-SNAPPED)
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

    gps_toggle_col, gps_btn_col, _ = st.columns([1.0, 0.6, 3.4])
    with gps_toggle_col:
        use_gps = st.checkbox(t["use_gps"], value=False)
    user_loc = None
    with gps_btn_col:
        if use_gps:
            user_loc = streamlit_geolocation()

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

            # 1. Road-snapped walking path: Origin -> First Boarding Stop
            first_stop = itinerary["segments"][0]["stops"][0]
            walk_start_coords = snap_to_road(
                ((origin_lat, origin_lng), (first_stop["latitude"], first_stop["longitude"])),
                profile="foot",
            )
            if len(walk_start_coords) > 1:
                folium.PolyLine(
                    walk_start_coords,
                    color="#444444",
                    weight=4,
                    dash_array="6, 8",
                    tooltip=f"Walk {itinerary['walk_to_first_stop_m']:.0f}m → {format_stop_name(first_stop['stop_name_kh'])}",
                ).add_to(route_map)

            # 2. Road-snapped animated bus segments along actual Phnom Penh streets
            seg_colors = ["#0055ff", "#e6194b", "#911eb4", "#008080"]
            for s_idx, seg in enumerate(itinerary["segments"]):
                color = seg_colors[s_idx % len(seg_colors)]
                raw_coords = tuple((s["latitude"], s["longitude"]) for s in seg["stops"])
                road_coords = snap_to_road(raw_coords, profile="driving")
                line_label = format_bus_line(seg["bus_line"], lang)

                if len(road_coords) > 1:
                    AntPath(
                        locations=road_coords,
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

            # 3. Road-snapped walking path at each Transfer point
            for t_idx, tr in enumerate(itinerary["transfers"]):
                seg_before_last_stop = itinerary["segments"][t_idx]["stops"][-1]
                seg_after_first_stop = itinerary["segments"][t_idx + 1]["stops"][0]

                walk_tr_coords = snap_to_road(
                    (
                        (seg_before_last_stop["latitude"], seg_before_last_stop["longitude"]),
                        (seg_after_first_stop["latitude"], seg_after_first_stop["longitude"]),
                    ),
                    profile="foot",
                )

                folium.PolyLine(
                    walk_tr_coords,
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

            # 4. Road-snapped walking path: Last Stop -> Destination
            last_stop = itinerary["segments"][-1]["stops"][-1]
            walk_end_coords = snap_to_road(
                ((last_stop["latitude"], last_stop["longitude"]), (dest_lat, dest_lng)),
                profile="foot",
            )
            if len(walk_end_coords) > 1:
                folium.PolyLine(
                    walk_end_coords,
                    color="#444444",
                    weight=4,
                    dash_array="6, 8",
                    tooltip=f"Walk {itinerary['walk_from_last_stop_m']:.0f}m to destination",
                ).add_to(route_map)

            st_folium(route_map, width=None, height=680, returned_objects=[])


# ==============================================================================
# TAB 2: PUBLIC BUS SERVICES, SCHEDULES, FARES & ROAD-SNAPPED LINE MAPS
# ==============================================================================
with tab_services:
    st.subheader(t["svc_header"])

    service_keys = ["daily", "walk_street", "aeb"]
    service_labels = {
        k: f"{SERVICES_DATA[k]['icon']}  {SERVICES_DATA[k][f'title_{lang}']}" for k in service_keys
    }

    selected_service_key = st.radio(
        t["svc_choose"],
        options=service_keys,
        format_func=lambda k: service_labels[k],
        horizontal=True,
    )

    svc = SERVICES_DATA[selected_service_key]
    st.info(f"**{svc['icon']} {svc[f'title_{lang}']}** — {svc[f'note_{lang}']}")

    info_col, map_col = st.columns([0.95, 2.05])

    with info_col:
        st.markdown(f"#### {t['op_hours_title']}")
        st.markdown(
            f"- **{t['op_days']}:** {svc[f'days_{lang}']}\n"
            f"- **{t['op_time']}:** {svc[f'hours_{lang}']}\n"
            f"- **{t['op_wait']}:** {svc[f'wait_{lang}']}"
        )

        st.divider()

        st.markdown(f"#### {t['ticket_title']}")
        fare_df = pd.DataFrame(
            [
                {
                    t["col_price"]: svc[f"price_{lang}"],
                    t["col_qty"]: svc[f"qty_{lang}"],
                    t["col_valid"]: svc[f"valid_{lang}"],
                }
            ]
        )
        st.table(fare_df)

        st.divider()

        st.markdown(f"#### {t['route_map_title']}")
        available_codes = svc["line_codes"]

        if selected_service_key == "aeb":
            selected_code = "AEB"
            st.success("🔵 **AEB** — Airport Express Bus")
        else:
            line_options = ["ALL"] + available_codes
            selected_code = st.selectbox(
                t["select_line_label"],
                options=line_options,
                format_func=lambda c: t["all_service_lines"]
                if c == "ALL"
                else (f"Line {c} (ខ្សែទី {c})" if lang == "en" else f"ខ្សែទី {c} (Line {c})"),
            )

            badge_html = " ".join(
                [
                    f"<span style='display:inline-block;padding:4px 10px;margin:2px;border-radius:14px;"
                    f"background-color:{LINE_COLORS[i % len(LINE_COLORS)]};color:white;font-weight:bold;font-size:13px;'>"
                    f"{code}</span>"
                    for i, code in enumerate(available_codes)
                ]
            )
            st.markdown(badge_html, unsafe_allow_html=True)

    with map_col:
        if selected_service_key == "aeb":
            aeb_df = pd.DataFrame(AEB_STOPS)
            svc_map = folium.Map(location=[11.465, 104.924], zoom_start=11, tiles="OpenStreetMap")
            LocateControl(auto_start=False, position="topleft").add_to(svc_map)

            raw_coords = tuple(zip(aeb_df["latitude"], aeb_df["longitude"]))
            road_coords = snap_to_road(raw_coords, profile="driving")

            AntPath(
                locations=road_coords,
                color="#1f78b4",
                pulse_color="#ffffff",
                weight=6,
                delay=800,
                tooltip="AEB — Airport Express Bus",
            ).add_to(svc_map)

            for _, s_row in aeb_df.iterrows():
                is_terminal = s_row["stop_number"] in (1, len(aeb_df))
                folium.Marker(
                    [s_row["latitude"], s_row["longitude"]],
                    tooltip=f"#{s_row['stop_number']} {s_row['stop_name_kh']}",
                    icon=folium.Icon(
                        color="blue" if s_row["stop_number"] == 1 else ("red" if is_terminal else "cadetblue"),
                        icon="plane" if s_row["stop_number"] == len(aeb_df) else "bus",
                        prefix="fa",
                    ),
                ).add_to(svc_map)

            st.caption(t["stops_count_badge"].format(n=len(aeb_df)))
            st_folium(svc_map, width=None, height=600, returned_objects=[])
        else:
            if selected_code == "ALL":
                target_stops = stops_df[stops_df["line_code"].isin(available_codes)]
            else:
                target_stops = stops_df[stops_df["line_code"] == selected_code]

            svc_map = folium.Map(location=[11.5564, 104.9282], zoom_start=12, tiles="OpenStreetMap")
            LocateControl(auto_start=False, position="topleft").add_to(svc_map)

            active_lines = sorted(target_stops["bus_line"].dropna().unique().tolist())
            for i, line in enumerate(active_lines):
                line_stops = target_stops[target_stops["bus_line"] == line].sort_values("stop_number")
                raw_coords = tuple(zip(line_stops["latitude"], line_stops["longitude"]))
                road_coords = snap_to_road(raw_coords, profile="driving")
                color = LINE_COLORS[i % len(LINE_COLORS)]
                line_label = format_bus_line(line, lang)

                if len(road_coords) > 1:
                    if selected_code != "ALL":
                        AntPath(
                            locations=road_coords,
                            color=color,
                            pulse_color="#ffffff",
                            weight=5,
                            delay=800,
                            tooltip=line_label,
                        ).add_to(svc_map)
                    else:
                        folium.PolyLine(
                            road_coords,
                            color=color,
                            weight=3.5,
                            opacity=0.85,
                            tooltip=line_label,
                        ).add_to(svc_map)

                for _, s_row in line_stops.iterrows():
                    folium.CircleMarker(
                        [s_row["latitude"], s_row["longitude"]],
                        radius=4,
                        color=color,
                        fill=True,
                        fill_color=color,
                        fill_opacity=0.9,
                        tooltip=f"{format_stop_name(s_row['stop_name_kh'])} ({line_label})",
                    ).add_to(svc_map)

            st.caption(t["stops_count_badge"].format(n=len(target_stops)))
            st_folium(svc_map, width=None, height=600, returned_objects=[])
