"""
ai/__init__.py - CIVIX AI Intelligence Engine Public API
Exposes a single convenience function `analyze_complaint` that runs the full
5-stage AI pipeline on a new complaint and returns enriched metadata.

Pipeline stages:
  1. categorizer       → predicted_category, confidence
  2. duplicate_detector→ is_duplicate, best_match_id, similarity
  3. hotspot_detector  → cluster_id (from current DB state)
  4. priority_scorer   → priority_score, priority_level, priority_factors
  5. action_recommender→ department, action_recommendation, sla
"""

from typing import Dict, List

from ai.categorizer       import predict_category
from ai.duplicate_detector import detect_duplicates
from ai.hotspot_detector  import detect_hotspots, apply_cluster_labels
from ai.priority_scorer   import compute_priority
from ai.action_recommender import generate_recommendation


def analyze_complaint(new_complaint: Dict, all_existing: List[Dict]) -> Dict:
    """
    Runs the full CIVIX AI pipeline on a single new complaint.

    Parameters
    ----------
    new_complaint : dict – the just-submitted complaint (already in DB)
    all_existing  : list of dicts – all complaints from the database
                    (including new_complaint itself)

    Returns
    -------
    Enriched dict containing all AI-derived fields, ready to be passed to
    database.update_complaint_ai_metadata().
    """
    result: Dict = {}

    # ── Stage 1: Categorization ───────────────────────────────────────────────
    cat_result = predict_category(
        new_complaint.get("title", ""),
        new_complaint.get("description", "")
    )
    result["predicted_category"] = cat_result["predicted_category"]

    # ── Stage 2: Duplicate Detection ─────────────────────────────────────────
    dup_result = detect_duplicates(
        new_complaint,
        all_existing,
        exclude_id=new_complaint.get("id")
    )
    result["is_duplicate"]    = 1 if dup_result["is_duplicate"] else 0
    result["duplicate_of_id"] = dup_result.get("best_match_id") if dup_result["is_duplicate"] else None

    # ── Stage 3: Geographic Clustering (DBSCAN on full DB) ────────────────────
    hotspot_result = detect_hotspots(all_existing)
    labels         = hotspot_result["labels"]
    cluster_id     = labels.get(new_complaint.get("id"), -1)
    result["cluster_id"] = cluster_id

    # ── Stage 4: Priority Scoring ─────────────────────────────────────────────
    similar_count  = len(dup_result.get("matches", []))
    is_in_hotspot  = cluster_id != -1
    enriched_comp  = {**new_complaint, **result}   # include predicted_category
    prio_result    = compute_priority(
        enriched_comp,
        similar_count=similar_count,
        is_in_hotspot=is_in_hotspot
    )
    result["priority_score"]   = prio_result["priority_score"]
    result["priority_level"]   = prio_result["priority_level"]
    result["priority_factors"] = prio_result["priority_factors"]

    # ── Stage 5: Action Recommendation ───────────────────────────────────────
    rec_input = {**new_complaint, **result}
    rec_result = generate_recommendation(rec_input)
    result["department"]            = rec_result["department"]
    result["action_recommendation"] = rec_result["action_recommendation"]

    # Attach duplicate explanation for display
    result["duplicate_explanation"] = dup_result.get("explanation", "")
    result["duplicate_matches"]     = dup_result.get("matches", [])

    return result

