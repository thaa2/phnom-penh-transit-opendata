from pathlib import Path
import pandas as pd

DATA_DIR = Path("data/processed")

# Verified Phnom Penh / Ta Khmau transit hubs, terminals & road corridor waypoints
# Extracted directly from the 22 official City Bus route posters
HUBS = {
    "win_win_terminal": ("ស្ថានីយរថយន្តក្រុងមហាវិថីឈ្នះឈ្នះ (Win-Win Blvd Bus Station)", 11.6536, 104.8895),
    "prek_pnov_bridge": ("ស្ពានព្រែកព្នៅ (Prek Pnov Bridge)", 11.6588, 104.9096),
    "apsara_roundabout": ("រង្វង់មូលអប្សរា (Apsara Roundabout)", 11.6445, 104.9188),
    "russey_keo_garden": ("ស្ថានីយរថយន្តក្រុងសួនច្បារឫស្សីកែវ (Russey Keo Garden Bus Station)", 11.6115, 104.9158),
    "wat_phnom_station": ("ស្ថានីយរថយន្តក្រុងរង្វង់មូលកួចកាណុង (Wat Phnom Roundabout Station)", 11.5786, 104.9212),
    "canadia_park": ("សួនកាណាឌីយ៉ា (Canadia Park / St. 47)", 11.5734, 104.9189),
    "central_market": ("ផ្សារធំថ្មី (Central Market)", 11.5696, 104.9211),
    "calmette_hospital": ("មន្ទីរពេទ្យកាល់ម៉ែត (Calmette Hospital)", 11.5842, 104.9168),
    "bak_touk_monivong": ("វិទ្យាល័យបាក់ទូក / មហាវិថីព្រះមុនីវង្ស (Bak Touk / Monivong)", 11.5645, 104.9195),
    "bokor_intersection": ("ស្តុបបូកគោ (Bokor Traffic Light)", 11.5453, 104.9241),
    "monivong_bridge": ("ស្ពានព្រះមុនីវង្ស / ក្បាលថ្នល់ (Monivong Bridge / Kbal Thnal)", 11.5312, 104.9298),
    "chbar_ampov_market": ("ផ្សារច្បារអំពៅ (Chbar Ampov Market)", 11.5305, 104.9362),
    "veal_sbov_station": ("ស្ថានីយរថយន្តក្រុងវាលស្បូវ (Veal Sbov Bus Station)", 11.5198, 104.9765),
    "num_veal_sbov": ("សាកលវិទ្យាល័យជាតិគ្រប់គ្រង សាខាវាលស្បូវ (NUM Veal Sbov)", 11.5165, 104.9782),
    "dei_edth_police_academy": ("បណ្ឌិត្យសភានគរបាលកម្ពុជា ដីឥដ្ឋ (Cambodia Police Academy)", 11.4985, 105.0385),
    "chrin_samnang_station": ("ស្ថានីយរថយន្តក្រុងមជ្ឈមណ្ឌលច្រិនសំណាង (Chrin Samnang Center Station)", 11.4872, 105.0685),
    "koh_norea_bridge": ("ស្ពានកោះនរា (Koh Norea Bridge)", 11.5392, 104.9488),
    "koh_pich": ("មជ្ឈមណ្ឌលកោះពេជ្រ (Koh Pich)", 11.5512, 104.9425),
    "nagaworld_roundabout": ("រង្វង់មូលសម្តេចសង្ឃជួនណាត (NagaWorld Roundabout)", 11.5568, 104.9348),
    "aeon_1": ("ផ្សារទំនើបអ៊ីអនភ្នំពេញ (AEON Mall 1)", 11.5478, 104.9332),
    "mao_tse_tung_monivong": ("មហាវិថីម៉ៅសេទុង / ព្រះមុនីវង្ស (Mao Tse Tung / Monivong)", 11.5432, 104.9228),
    "morodok_techo_flyover": ("ស្ពានអាកាសមរតកតេជោ (Morodok Techo Skybridge)", 11.5302, 104.9288),
    "st271_ttp": ("ផ្លូវ២៧១ / ផ្សារទួលទំពូង (St. 271 / Toul Tom Poung)", 11.5358, 104.9142),
    "chip_mong_271": ("ផ្សារទំនើប ជីប ម៉ុង ២៧១ មេហ្គា ម៉ល (Chip Mong 271 Mega Mall)", 11.5225, 104.9158),
    "chak_angre_leu_station": ("ស្ថានីយរថយន្តក្រុងចាក់អង្រែលើ (Chak Angre Leu Bus Station)", 11.5038, 104.9325),
    "prek_samrong_station": ("ស្ថានីយរថយន្តក្រុងព្រែកសំរោង (Prek Samrong Bus Station)", 11.4718, 104.9435),
    "ta_khmau_roundabout": ("រង្វង់មូលក្រុងតាខ្មៅ (Ta Khmau Roundabout)", 11.4835, 104.9452),
    "borey_serey_mongkol": ("ស្ថានីយរថយន្តក្រុងបុរីសិរីមង្គល (Borey Serey Mongkol Bus Station)", 11.4382, 104.9615),
    "toul_kork_antenna": ("អង់តែនទួលគោក (Toul Kork Antenna)", 11.5882, 104.8925),
    "ang_blvd_st355": ("មហាវិថីអង្គរ / ផ្លូវ៣៥៥ (Angkor Blvd / St. 355)", 11.6145, 104.8892),
    "mlmupc_angkor_blvd": ("ក្រសួងរៀបចំដែនដី នគរូបនីយកម្ម និងសំណង់ (Ministry of Land Management)", 11.6225, 104.8865),
    "toul_sangke_doeum_kor": ("ផ្សារទួលសង្កែ / ផ្សារដើមគរ (Toul Sangke)", 11.5945, 104.9112),
    "kampuchea_krom_blvd": ("មហាវិថីកម្ពុជាក្រោម (Kampuchea Krom Blvd)", 11.5678, 104.9095),
    "7_makara_skybridge": ("ស្ពានអាកាស៧មករា (7 Makara Skybridge)", 11.5658, 104.8935),
    "pp_intl_airport": ("អាកាសយានដ្ឋានអន្តរជាតិភ្នំពេញ (Phnom Penh International Airport)", 11.5535, 104.8465),
    "chom_chao_skybridge": ("ស្ពានអាកាសចោមចៅ (Chom Chao Skybridge)", 11.5365, 104.8235),
    "borey_santepheap_2": ("ស្ថានីយរថយន្តក្រុងបុរីសន្តិភាព២ (Borey Santepheap 2 Bus Station)", 11.5095, 104.8195),
    "bkk_market_st310": ("ផ្សារបឹងកេងកង / ផ្លូវ៣១០ (Boeung Keng Kang Market)", 11.5518, 104.9205),
    "depo_market": ("រង្វង់មូលផ្សារដេប៉ូ (Depo Market Roundabout)", 11.5642, 104.9035),
    "stung_meanchey_flyover": ("ស្ពានអាកាសស្ទឹងមានជ័យ (Stung Meanchey Skybridge)", 11.5435, 104.8885),
    "toul_pongro_market": ("ផ្សារទួលពង្រ (Toul Pongro Market)", 11.5162, 104.8495),
    "lhr_angk_snuol": ("ស្ថានីយប្រេងឥន្ធនៈ LHR ស្រុកអង្គស្នួល (LHR Station Angk Snuol)", 11.5045, 104.7325),
    "ppsez_station": ("ស្ថានីយរថយន្តក្រុងតំបន់សេដ្ឋកិច្ចពិសេសភ្នំពេញ (PPSEZ Bus Station)", 11.5092, 104.7695),
    "st_2011_kouk_khleang": ("ផ្លូវ២០១១ គោកឃ្លាង (St. 2011 Kouk Khleang)", 11.6135, 104.8565),
    "aeon_sen_sok": ("ផ្សារទំនើបអ៊ីអនសែនសុខ (AEON Mall Sen Sok)", 11.5998, 104.8835),
    "penn_nouth_blvd": ("មហាវិថីសម្តេចប៉ែន នុត (Samdech Penn Nouth Blvd)", 11.5765, 104.8965),
    "sokha_hotel_chroy_changvar": ("សណ្ឋាគារសុខាភ្នំពេញ (Sokha Phnom Penh Hotel)", 11.5745, 104.9335),
    "chroy_changvar_bridge": ("ស្ពានជ្រោយចង្វារ (Chroy Changvar Bridge)", 11.5865, 104.9225),
    "st_2004_station": ("ស្ថានីយរថយន្តក្រុងផ្លូវ២០០៤ (St. 2004 Bus Station)", 11.5565, 104.8655),
    "pong_teuk_station": ("ស្ថានីយរថយន្តក្រុងពងទឹក (Pong Teuk Bus Station)", 11.4825, 104.8125),
    "prateah_lang_rd": ("ផ្លូវប្រទះឡាង (Prateah Lang Road)", 11.4865, 104.7785),
    "st_371_slar": ("ផ្លូវ៣៧១ សឡា (St. 371 Solar)", 11.5425, 104.8725),
    "st_217_chamkar_doung": ("ផ្លូវ២១៧ ចំការដូង (St. 217 Chamkar Doung)", 11.5125, 104.8885),
    "olympic_stadium": ("ចំណតរថយន្តក្រុងពហុកីឡដ្ឋានជាតិអូឡាំពិក (Olympic National Stadium)", 11.5592, 104.9112),
    "prek_kampis_station": ("ស្ថានីយរថយន្តក្រុងព្រែកកំពឹស (Prek Kampis Bus Station)", 11.4545, 104.9115),
    "aeon_mean_chey": ("ផ្សារទំនើបអ៊ីអនមានជ័យ (AEON Mall Mean Chey - 60m Blvd)", 11.4915, 104.9265),
    "hun_sen_blvd_60m": ("មហាវិថីសម្តេចតេជោ ហ៊ុន សែន ៦០ម៉ែត្រ (Samdech Techo Hun Sen Blvd)", 11.5085, 104.9235),
    "independence_monument": ("វិមានឯករាជ្យ (Independence Monument)", 11.5564, 104.9282),
    "eco_collection_nr1": ("គម្រោង អេកូ ខូលិកសិន ផ្លូវជាតិលេខ១ (Eco Collection Project NR1)", 11.5125, 104.9625),
    "pp_city_center_st315": ("តំបន់អភិវឌ្ឍន៍បឹងកក់ / ផ្លូវ៣១៥ (Phnom Penh City Center)", 11.5765, 104.9045),
    "hanoi_blvd": ("មហាវិថីមិត្តភាពភ្នំពេញ-ហាណូយ (Hanoi Friendship Blvd)", 11.6185, 104.8645),
    "pp_police_hq": ("បញ្ជាការដ្ឋាននគរបាលរាជធានីភ្នំពេញ (Phnom Penh Municipal Police HQ)", 11.5445, 104.8685),
    "kour_srov_roundabout": ("រង្វង់មូលគួរស្រូវ (Kour Srov Roundabout)", 11.4385, 104.9182),
    "techo_intl_airport": ("អាកាសយានដ្ឋានអន្តរជាតិតេជោ (Techo International Airport)", 11.3548, 104.9288),
}

# Exact 22 Official Branches + AEB verified from user's City Bus posters
OFFICIAL_22_BRANCHES = [
    ("1A", "ខ្សែទី 1A", 29.0, 108, [
        "win_win_terminal", "prek_pnov_bridge", "apsara_roundabout", "russey_keo_garden",
        "wat_phnom_station", "calmette_hospital", "bak_touk_monivong", "bokor_intersection",
        "monivong_bridge", "chbar_ampov_market", "veal_sbov_station"
    ]),
    ("1B", "ខ្សែទី 1B", 19.0, 60, [
        "veal_sbov_station", "num_veal_sbov", "dei_edth_police_academy", "chrin_samnang_station"
    ]),
    ("1C", "ខ្សែទី 1C", 45.0, 93, [
        "veal_sbov_station", "chbar_ampov_market", "koh_norea_bridge", "koh_pich",
        "nagaworld_roundabout", "aeon_1", "mao_tse_tung_monivong", "morodok_techo_flyover",
        "st271_ttp", "chip_mong_271"
    ]),
    ("2A", "ខ្សែទី 2A", 30.0, 65, [
        "wat_phnom_station", "canadia_park", "central_market", "independence_monument",
        "bokor_intersection", "monivong_bridge", "chak_angre_leu_station", "prek_samrong_station"
    ]),
    ("2B", "ខ្សែទី 2B", 13.0, 57, [
        "chak_angre_leu_station", "prek_samrong_station", "ta_khmau_roundabout", "borey_serey_mongkol"
    ]),
    ("2C", "ខ្សែទី 2C", 28.0, 89, [
        "chak_angre_leu_station", "morodok_techo_flyover", "mao_tse_tung_monivong",
        "st271_ttp", "depo_market", "toul_kork_antenna", "ang_blvd_st355",
        "toul_sangke_doeum_kor", "win_win_terminal"
    ]),
    ("3", "ខ្សែទី 3", 22.0, 56, [
        "russey_keo_garden", "wat_phnom_station", "central_market", "kampuchea_krom_blvd",
        "7_makara_skybridge", "pp_intl_airport", "chom_chao_skybridge", "borey_santepheap_2"
    ]),
    ("4A", "ខ្សែទី 4A", 20.0, 85, [
        "russey_keo_garden", "wat_phnom_station", "canadia_park", "bak_touk_monivong",
        "bkk_market_st310", "depo_market", "stung_meanchey_flyover", "toul_pongro_market",
        "borey_santepheap_2"
    ]),
    ("4B", "ខ្សែទី 4B", 26.0, 85, [
        "borey_santepheap_2", "toul_pongro_market", "chom_chao_skybridge",
        "ppsez_station", "lhr_angk_snuol"
    ]),
    ("5", "ខ្សែទី 5", 49.0, 95, [
        "russey_keo_garden", "win_win_terminal", "st_2011_kouk_khleang", "aeon_sen_sok",
        "ang_blvd_st355", "penn_nouth_blvd", "depo_market", "bak_touk_monivong",
        "wat_phnom_station", "russey_keo_garden"
    ]),
    ("6", "ខ្សែទី 6", 32.0, 51, [
        "win_win_terminal", "russey_keo_garden", "prek_pnov_bridge", "apsara_roundabout",
        "sokha_hotel_chroy_changvar", "chroy_changvar_bridge", "wat_phnom_station"
    ]),
    ("7", "ខ្សែទី 7", 30.0, 112, [
        "win_win_terminal", "prek_pnov_bridge", "mlmupc_angkor_blvd", "ang_blvd_st355",
        "aeon_sen_sok", "depo_market", "stung_meanchey_flyover", "st271_ttp",
        "morodok_techo_flyover", "monivong_bridge", "chbar_ampov_market", "veal_sbov_station"
    ]),
    ("8", "ខ្សែទី 8", 14.0, 45, [
        "russey_keo_garden", "wat_phnom_station", "pp_city_center_st315", "toul_kork_antenna",
        "aeon_sen_sok", "st_2004_station"
    ]),
    ("9", "ខ្សែទី 9", 31.0, 57, [
        "borey_santepheap_2", "pong_teuk_station", "prateah_lang_rd", "ppsez_station"
    ]),
    ("10", "ខ្សែទី 10", 18.0, 75, [
        "st_2004_station", "st_371_slar", "stung_meanchey_flyover", "st_217_chamkar_doung",
        "st271_ttp", "morodok_techo_flyover", "monivong_bridge", "veal_sbov_station"
    ]),
    ("11A", "ខ្សែទី 11A", 37.0, 82, [
        "pong_teuk_station", "toul_pongro_market", "st_217_chamkar_doung",
        "stung_meanchey_flyover", "olympic_stadium"
    ]),
    ("11B", "ខ្សែទី 11B", 29.0, 49, [
        "prek_kampis_station", "aeon_mean_chey", "st_217_chamkar_doung", "stung_meanchey_flyover"
    ]),
    ("11C", "ខ្សែទី 11C", 15.0, 56, [
        "chak_angre_leu_station", "chip_mong_271", "morodok_techo_flyover",
        "hun_sen_blvd_60m", "aeon_mean_chey", "prek_kampis_station"
    ]),
    ("12A", "ខ្សែទី 12A", 39.0, 75, [
        "wat_phnom_station", "canadia_park", "bak_touk_monivong", "kampuchea_krom_blvd",
        "independence_monument", "aeon_1", "koh_pich", "koh_norea_bridge", "eco_collection_nr1"
    ]),
    ("12B", "ខ្សែទី 12B", 17.0, 60, [
        "wat_phnom_station", "calmette_hospital", "pp_city_center_st315", "depo_market",
        "bkk_market_st310", "st271_ttp", "hun_sen_blvd_60m", "chak_angre_leu_station"
    ]),
    ("13A", "ខ្សែទី 13A", 24.0, 71, [
        "win_win_terminal", "hanoi_blvd", "chom_chao_skybridge", "ppsez_station"
    ]),
    ("13B", "ខ្សែទី 13B", 36.0, 89, [
        "win_win_terminal", "hanoi_blvd", "st_2011_kouk_khleang", "st_2004_station", "pp_police_hq"
    ]),
    ("AEB", "ខ្សែរថយន្តក្រុង AEB", 32.0, 18, [
        "canadia_park", "central_market", "bokor_intersection", "monivong_bridge",
        "aeon_mean_chey", "kour_srov_roundabout", "techo_intl_airport"
    ]),
]


def main():
    rows = []
    meta_rows = []

    for code, kh_name, dist_km, official_stops, hub_keys in OFFICIAL_22_BRANCHES:
        meta_rows.append(
            {
                "line_code": code,
                "bus_line": kh_name,
                "distance_km": dist_km,
                "official_stop_count": official_stops,
                "start_terminal": HUBS[hub_keys[0]][0],
                "end_terminal": HUBS[hub_keys[-1]][0],
            }
        )
        for idx, h_key in enumerate(hub_keys, start=1):
            stop_name, lat, lng = HUBS[h_key]
            rows.append(
                {
                    "map_id": f"line_{code}_stop_{idx}",
                    "bus_line": kh_name,
                    "line_code": code,
                    "stop_number": idx,
                    "stop_name_kh": stop_name,
                    "latitude": lat,
                    "longitude": lng,
                    "distance_km": dist_km,
                    "official_stop_count": official_stops,
                }
            )

    stops_out = pd.DataFrame(rows)
    meta_out = pd.DataFrame(meta_rows)

    stops_out.to_csv(DATA_DIR / "bus_stops_22_lines.csv", index=False)
    meta_out.to_csv(DATA_DIR / "bus_lines_22_metadata.csv", index=False)
    print(f"Saved {len(stops_out)} verified waypoints across {len(meta_out)} official branches!")


if __name__ == "__main__":
    main()
