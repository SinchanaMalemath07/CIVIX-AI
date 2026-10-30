"""
ai/duplicate_detector.py - Duplicate complaint detection module.
Uses Scikit-learn TF-IDF and Cosine Similarity combined with spatial proximity
to identify potential duplicates with similarity percentages.

How it works:
1. Builds a TF-IDF matrix over all existing complaints in the database.
2. Vectorises the incoming new complaint text.
3. Computes cosine similarity against all existing vectors.
4. Applies a geographic proximity filter (Haversine distance ≤ MAX_DISTANCE_KM).
5. Returns all matches above TEXT_SIM_THRESHOLD sorted by similarity.
"""

import math
import re
from typing import Dict, List, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# ── Thresholds ────────────────────────────────────────────────────────────────
TEXT_SIM_THRESHOLD = 0.35      # cosine similarity >= this -> candidate duplicate
MAX_DISTANCE_KM    = 2.0       # geographic filter radius in kilometres
DEFINITE_DUP_SIM   = 0.60      # >= this -> "High Confidence" duplicate flag

EARTH_RADIUS_KM = 6371.0


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Returns the great-circle distance in kilometres between two GPS points."""
    if None in (lat1, lon1, lat2, lon2):
        return float("inf")
    try:
        rlat1, rlon1, rlat2, rlon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = rlat2 - rlat1
        dlon = rlon2 - rlon1
        a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
        return EARTH_RADIUS_KM * 2 * math.asin(math.sqrt(a))
    except Exception:
        return float("inf")


def _build_text(c: Dict) -> str:
    return _clean(f"{c.get('title', '')} {c.get('description', '')}")


# ── Public API ────────────────────────────────────────────────────────────────

def detect_duplicates(
    new_complaint: Dict,
    existing_complaints: List[Dict],
    exclude_id: Optional[str] = None,
) -> Dict:
    """
    Compares *new_complaint* against *existing_complaints* and returns
    all probable duplicates ranked by similarity.

    Parameters
    ----------
    new_complaint      : dict with keys title, description, latitude, longitude, id, category
    existing_complaints: list of dicts (from database.get_all_complaints())
    exclude_id         : complaint ID to skip (e.g. the new complaint itself)

    Returns
    -------
    {
      "is_duplicate"       : bool,
      "confidence_level"   : "High" | "Medium" | "None",
      "best_match_id"      : str | None,
      "best_similarity_pct": str | None,
      "matches"            : [
          {
            "id"              : str,
            "title"           : str,
            "category"        : str,
            "similarity_pct"  : str,
            "distance_km"     : str,
            "confidence_level": "High" | "Medium"
          }, ...
      ],
      "explanation"        : str,
    }
    """
    # Filter pool – exclude the complaint itself and any with empty text
    pool = [
        c for c in existing_complaints
        if c.get("id") != exclude_id
        and (c.get("title") or c.get("description"))
    ]

    if not pool:
        return _no_duplicate_result("Database is empty – no comparison possible.")

    # Build corpus
    corpus_texts = [_build_text(c) for c in pool]
    new_text = _build_text(new_complaint)

    if not new_text.strip():
        return _no_duplicate_result("Incoming complaint has no text to compare.")

    # TF-IDF matrix
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=5000, sublinear_tf=True)
    try:
        corpus_matrix = vectorizer.fit_transform(corpus_texts)
        new_vector = vectorizer.transform([new_text])
    except Exception as e:
        return _no_duplicate_result(f"Vectorisation error: {e}")

    # Cosine similarities
    sims = cosine_similarity(new_vector, corpus_matrix)[0]

    new_lat = new_complaint.get("latitude")
    new_lon = new_complaint.get("longitude")

    matches = []
    for idx, sim in enumerate(sims):
        if sim < TEXT_SIM_THRESHOLD:
            continue

        c = pool[idx]
        dist_km = _haversine_km(new_lat, new_lon, c.get("latitude"), c.get("longitude"))

        # Geographic filter
        if dist_km > MAX_DISTANCE_KM:
            continue

        conf = "High" if sim >= DEFINITE_DUP_SIM else "Medium"
        matches.append({
            "id"              : c["id"],
            "title"           : c.get("title", ""),
            "category"        : c.get("category", ""),
            "similarity_pct"  : f"{round(sim * 100, 1)}%",
            "similarity_score": float(sim),
            "distance_km"     : f"{round(dist_km, 2)} km" if dist_km != float('inf') else "Unknown",
            "confidence_level": conf,
        })

    matches.sort(key=lambda x: x["similarity_score"], reverse=True)

    if not matches:
        return _no_duplicate_result("No sufficiently similar complaints found within the proximity radius.")

    best = matches[0]
    is_dup = best["similarity_score"] >= DEFINITE_DUP_SIM

    explanation = (
        f"This complaint is {best['similarity_pct']} textually similar to "
        f"{best['id']} (\"{best['title'][:60]}...\") and is located "
        f"{best['distance_km']} away. "
        f"Confidence: {best['confidence_level']}. "
        f"Total similar reports found: {len(matches)}."
    )

    return {
        "is_duplicate"       : is_dup,
        "confidence_level"   : best["confidence_level"],
        "best_match_id"      : best["id"],
        "best_similarity_pct": best["similarity_pct"],
        "matches"            : matches,
        "explanation"        : explanation,
    }


def _no_duplicate_result(reason: str) -> Dict:
    return {
        "is_duplicate"       : False,
        "confidence_level"   : "None",
        "best_match_id"      : None,
        "best_similarity_pct": None,
        "matches"            : [],
        "explanation"        : reason,
    }

