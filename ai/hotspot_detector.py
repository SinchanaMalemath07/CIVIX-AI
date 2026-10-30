"""
ai/hotspot_detector.py - Geographic Hotspot Detection Module.
Uses Scikit-learn DBSCAN with Haversine distance metric to cluster geographic
coordinates (latitude and longitude) and flag spatial problem zones.

How it works:
1. Latitude/longitude pairs are converted to radians (required by Haversine).
2. DBSCAN(eps = radius_km / EARTH_RADIUS, min_samples) runs the clustering.
3. Each complaint is assigned a cluster_id:
     -1  → noise / isolated (no nearby neighbours)
      0+ → active geographic cluster (hotspot)
4. Per-cluster statistics (centroid, dominant category, severity) are computed.
5. Results are ready to update the database and render on a Folium map.
"""

import math
from collections import Counter
from typing import Dict, List, Tuple

import numpy as np
from sklearn.cluster import DBSCAN

EARTH_RADIUS_KM  = 6371.0
CLUSTER_RADIUS_KM = 0.6      # complaints within 600 m → same cluster
MIN_SAMPLES       = 2         # minimum points to form a cluster


def _to_radians(lat: float, lon: float) -> Tuple[float, float]:
    return math.radians(lat), math.radians(lon)


def _centroid(coords: List[Tuple[float, float]]) -> Tuple[float, float]:
    """Returns (mean_lat, mean_lon) for a list of (lat, lon) pairs."""
    lats, lons = zip(*coords)
    return round(sum(lats) / len(lats), 6), round(sum(lons) / len(lons), 6)


def _dominant(values: List[str]) -> str:
    if not values:
        return "Unknown"
    return Counter(values).most_common(1)[0][0]


def _cluster_severity(complaints: List[Dict]) -> str:
    """Highest priority level found in the cluster."""
    order = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
    levels = [c.get("priority_level", "Low") for c in complaints]
    return max(levels, key=lambda x: order.get(x, 0))


# ── Public API ────────────────────────────────────────────────────────────────

def detect_hotspots(complaints: List[Dict]) -> Dict:
    """
    Runs DBSCAN clustering on complaint GPS coordinates.

    Parameters
    ----------
    complaints : list of dicts (from database.get_all_complaints())
                 Each dict must have 'latitude', 'longitude', and 'id'.

    Returns
    -------
    {
      "labels"              : {complaint_id: cluster_id},   # -1 = noise
      "cluster_summaries"   : [
          {
            "cluster_id"      : int,
            "complaint_count" : int,
            "dominant_category": str,
            "severity_level"  : str,
            "centroid_lat"    : float,
            "centroid_lon"    : float,
            "complaint_ids"   : [str, ...],
          }, ...
      ],
      "total_clusters"      : int,
      "total_noise"         : int,
      "hotspot_complaint_ids": [str, ...],   # all IDs in any cluster
    }
    """
    # Filter complaints with valid coordinates
    valid = [
        c for c in complaints
        if c.get("latitude") is not None
        and c.get("longitude") is not None
        and not (c["latitude"] == 0.0 and c["longitude"] == 0.0)
    ]

    if len(valid) < MIN_SAMPLES:
        return {
            "labels"              : {},
            "cluster_summaries"   : [],
            "total_clusters"      : 0,
            "total_noise"         : len(valid),
            "hotspot_complaint_ids": [],
        }

    # Build radians matrix
    coords_rad = np.array([
        [math.radians(c["latitude"]), math.radians(c["longitude"])]
        for c in valid
    ])

    eps_rad = CLUSTER_RADIUS_KM / EARTH_RADIUS_KM

    db = DBSCAN(
        eps=eps_rad,
        min_samples=MIN_SAMPLES,
        algorithm="ball_tree",
        metric="haversine",
        n_jobs=1,
    )
    db.fit(coords_rad)
    raw_labels = db.labels_

    # Build label mapping  {complaint_id: cluster_id}
    label_map: Dict[str, int] = {valid[i]["id"]: int(raw_labels[i]) for i in range(len(valid))}

    # Complaints not in the valid list default to noise
    for c in complaints:
        if c["id"] not in label_map:
            label_map[c["id"]] = -1

    # Build per-cluster summaries
    cluster_groups: Dict[int, List[Dict]] = {}
    for i, c in enumerate(valid):
        cid = int(raw_labels[i])
        if cid == -1:
            continue
        cluster_groups.setdefault(cid, []).append(c)

    cluster_summaries = []
    for cid, members in sorted(cluster_groups.items()):
        coords = [(m["latitude"], m["longitude"]) for m in members]
        centroid = _centroid(coords)
        cluster_summaries.append({
            "cluster_id"       : cid,
            "complaint_count"  : len(members),
            "dominant_category": _dominant([m.get("category", "") for m in members]),
            "severity_level"   : _cluster_severity(members),
            "centroid_lat"     : centroid[0],
            "centroid_lon"     : centroid[1],
            "complaint_ids"    : [m["id"] for m in members],
        })

    hotspot_ids = [cid for cid, label in label_map.items() if label != -1]
    noise_ids   = [cid for cid, label in label_map.items() if label == -1]

    return {
        "labels"               : label_map,
        "cluster_summaries"    : cluster_summaries,
        "total_clusters"       : len(cluster_summaries),
        "total_noise"          : len(noise_ids),
        "hotspot_complaint_ids": hotspot_ids,
    }


def apply_cluster_labels(complaints: List[Dict], labels: Dict[str, int]) -> List[Dict]:
    """
    Updates each complaint dict with the cluster_id from DBSCAN labels.
    Returns the updated list (also mutates in-place for convenience).
    """
    for c in complaints:
        c["cluster_id"] = labels.get(c["id"], -1)
    return complaints

