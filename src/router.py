from pathlib import Path
import networkx as nx
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

DATA_DIR = Path("data/processed")

# Equirectangular projection constants for Phnom Penh (~11.55° N)
LAT_REF = np.radians(11.55)
M_PER_DEG_LAT = 111_132.0
M_PER_DEG_LNG = 111_320.0 * np.cos(LAT_REF)


def to_xy(lat_series, lng_series):
    return np.column_stack([lng_series * M_PER_DEG_LNG, lat_series * M_PER_DEG_LAT])


class TransitRouter:
    def __init__(self, stops_df: pd.DataFrame, transfer_radius_m: float = 250.0):
        self.stops_df = stops_df.reset_index(drop=True).copy()
        self.stops_df["node_id"] = self.stops_df.index
        self.transfer_radius_m = transfer_radius_m
        self.stop_xy = to_xy(self.stops_df["latitude"], self.stops_df["longitude"])
        self.tree = cKDTree(self.stop_xy)
        self.graph = self._build_graph()

    def _build_graph(self) -> nx.Graph:
        g = nx.Graph()

        for idx, row in self.stops_df.iterrows():
            g.add_node(
                idx,
                stop_name_kh=row["stop_name_kh"],
                bus_line=row["bus_line"],
                stop_number=row["stop_number"],
                latitude=row["latitude"],
                longitude=row["longitude"],
            )

        # 1. Connect consecutive stops on the same bus line (bidirectional)
        for line, group in self.stops_df.groupby("bus_line"):
            ordered = group.sort_values("stop_number")
            idxs = ordered.index.tolist()
            for i in range(len(idxs) - 1):
                u, v = idxs[i], idxs[i + 1]
                dist_m = float(np.linalg.norm(self.stop_xy[u] - self.stop_xy[v]))
                g.add_edge(u, v, edge_type="ride", distance_m=dist_m, weight=dist_m)

        # 2. Connect stops from different lines within transfer_radius_m
        pairs = self.tree.query_pairs(r=self.transfer_radius_m)
        for u, v in pairs:
            if self.stops_df.loc[u, "bus_line"] != self.stops_df.loc[v, "bus_line"]:
                walk_m = float(np.linalg.norm(self.stop_xy[u] - self.stop_xy[v]))
                # Penalty (1200m equivalent) discourages unnecessary line changes
                g.add_edge(u, v, edge_type="transfer", distance_m=walk_m, weight=walk_m + 1200.0)

        return g

    def find_route(self, start_lat: float, start_lng: float, end_lat: float, end_lng: float):
        start_xy = np.array([[start_lng * M_PER_DEG_LNG, start_lat * M_PER_DEG_LAT]])
        end_xy = np.array([[end_lng * M_PER_DEG_LNG, end_lat * M_PER_DEG_LAT]])

        # Check top 5 nearest stops to origin & destination to find the best connected pair
        start_dists, start_idxs = self.tree.query(start_xy, k=5)
        end_dists, end_idxs = self.tree.query(end_xy, k=5)

        best_path = None
        best_cost = float("inf")
        best_walk_start = 0.0
        best_walk_end = 0.0

        for s_dist, s_idx in zip(start_dists[0], start_idxs[0]):
            for e_dist, e_idx in zip(end_dists[0], end_idxs[0]):
                try:
                    cost = nx.shortest_path_length(self.graph, s_idx, e_idx, weight="weight")
                    total_cost = cost + float(s_dist) * 2.0 + float(e_dist) * 2.0
                    if total_cost < best_cost:
                        best_cost = total_cost
                        best_path = nx.shortest_path(self.graph, s_idx, e_idx, weight="weight")
                        best_walk_start = float(s_dist)
                        best_walk_end = float(e_dist)
                except nx.NetworkXNoPath:
                    continue

        if not best_path:
            return None

        return self._format_itinerary(best_path, best_walk_start, best_walk_end)

    def _format_itinerary(self, path: list[int], walk_start_m: float, walk_end_m: float) -> dict:
        segments = []
        transfers = []
        total_ride_m = 0.0
        total_transfer_walk_m = 0.0

        current_seg = {
            "bus_line": self.stops_df.loc[path[0], "bus_line"],
            "board_stop": self.stops_df.loc[path[0], "stop_name_kh"],
            "alight_stop": self.stops_df.loc[path[0], "stop_name_kh"],
            "stops": [self.stops_df.loc[path[0]].to_dict()],
            "distance_m": 0.0,
        }

        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            edge = self.graph.edges[u, v]
            v_row = self.stops_df.loc[v]

            if edge["edge_type"] == "ride":
                current_seg["alight_stop"] = v_row["stop_name_kh"]
                current_seg["stops"].append(v_row.to_dict())
                current_seg["distance_m"] += edge["distance_m"]
                total_ride_m += edge["distance_m"]
            else:
                segments.append(current_seg)
                u_row = self.stops_df.loc[u]
                transfers.append(
                    {
                        "from_line": u_row["bus_line"],
                        "from_stop": u_row["stop_name_kh"],
                        "to_line": v_row["bus_line"],
                        "to_stop": v_row["stop_name_kh"],
                        "walk_m": round(edge["distance_m"], 0),
                    }
                )
                total_transfer_walk_m += edge["distance_m"]
                current_seg = {
                    "bus_line": v_row["bus_line"],
                    "board_stop": v_row["stop_name_kh"],
                    "alight_stop": v_row["stop_name_kh"],
                    "stops": [v_row.to_dict()],
                    "distance_m": 0.0,
                }

        segments.append(current_seg)

        return {
            "walk_to_first_stop_m": round(walk_start_m, 0),
            "walk_from_last_stop_m": round(walk_end_m, 0),
            "total_ride_km": round(total_ride_m / 1000.0, 2),
            "total_transfer_walk_m": round(total_transfer_walk_m, 0),
            "num_transfers": len(transfers),
            "transfers": transfers,
            "segments": segments,
            "path_nodes": [self.stops_df.loc[idx].to_dict() for idx in path],
        }
