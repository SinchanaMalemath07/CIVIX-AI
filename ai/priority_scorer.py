"""
ai/priority_scorer.py - Explainable Priority Scoring Engine.
Computes a transparent urgency score (0-100) based on weighted factors:
urgency keywords, category severity, public safety risk, and hotspot clustering.

Scoring Formula (total = 100 points):
  ┌─────────────────────────────────┬────────┐
  │ Component                       │ Weight │
  ├─────────────────────────────────┼────────┤
  │ Urgency keyword detection       │  40 pt │
  │ Category baseline severity      │  30 pt │
  │ Similar-report cluster bonus    │  15 pt │
  │ Duplicate / high-volume bonus   │  15 pt │
  └─────────────────────────────────┴────────┘

Each factor is independently computed and stored for full explainability.
"""

import re
from typing import Dict, List, Tuple

# ── Score thresholds ──────────────────────────────────────────────────────────
THRESHOLDS = {
    "Critical": 80,
    "High"    : 55,
    "Medium"  : 30,
    "Low"     : 0,
}

# ── Urgency keyword groups (with individual point values) ─────────────────────
# Keywords are checked case-insensitively against title + description.
KEYWORD_GROUPS: List[Tuple[int, List[str]]] = [
    # 10 pt each – life-threatening
    (10, ["fire", "explosion", "explode", "gas leak", "lpg", "electrocution",
          "electrocuted", "live wire", "snapped wire", "sparking", "shock risk",
          "biohazard", "biomedical", "sinkhole", "structural collapse",
          "collapsed building", "emergency", "snapped", "touching water",
          "cable snapped", "wire snapped"]),
    # 7 pt each – serious safety
    (7,  ["danger", "dangerous", "hazard", "hazardous", "accident", "injured",
          "injury", "fatal", "death", "hospital", "ambulance", "children",
          "school", "kindergarten", "park children", "open manhole",
          "contaminated water", "cholera", "sewage overflow",
          "concrete fell", "flyover pillar", "missing manhole",
          "fallen tree", "hanging wire", "waterlogged", "waterlogging"]),
    # 4 pt each – elevated concern
    (4,  ["urgent", "critical", "severe", "serious", "flooding", "flooded",
          "blocked drain", "pothole accident", "road blocked",
          "traffic blocked", "sparks", "smoke", "burning", "stray dog biting",
          "biting", "medical waste", "high-tension", "high tension"]),
    # 2 pt each – standard concern
    (2,  ["broken", "damaged", "cracked", "missing", "no water", "power cut",
          "no electricity", "garbage", "waste", "uncollected", "overflowing",
          "dark", "dark road", "night", "complaint", "problem", "issue"]),
]

MAX_KEYWORD_SCORE = 40  # cap

# ── Category baseline severity (out of 30) ────────────────────────────────────
CATEGORY_BASELINES: Dict[str, int] = {
    "Electricity & Power"          : 30,
    "Public Safety"                : 28,
    "Water Supply & Drainage"      : 25,
    "Roads & Infrastructure"       : 22,
    "Sanitation & Waste Management": 18,
}
DEFAULT_CATEGORY_SCORE = 15  # fallback for unknown categories


# ── Helpers ───────────────────────────────────────────────────────────────────

def _score_keywords(text: str) -> Tuple[int, List[str]]:
    """Returns (raw_keyword_score capped at MAX, list of matched keywords)."""
    text_lower = text.lower()
    total = 0
    matched = []
    for points, keywords in KEYWORD_GROUPS:
        for kw in keywords:
            if kw in text_lower:
                total += points
                matched.append(f"'{kw}' (+{points})")
    return min(total, MAX_KEYWORD_SCORE), matched


def _level_from_score(score: float) -> str:
    if score >= THRESHOLDS["Critical"]:
        return "Critical"
    if score >= THRESHOLDS["High"]:
        return "High"
    if score >= THRESHOLDS["Medium"]:
        return "Medium"
    return "Low"


# ── Public API ────────────────────────────────────────────────────────────────

def compute_priority(
    complaint: Dict,
    similar_count: int = 0,
    is_in_hotspot: bool = False,
) -> Dict:
    """
    Computes an explainable priority score for a single complaint.

    Parameters
    ----------
    complaint     : dict with keys title, description, category
    similar_count : number of duplicate/similar reports already logged
    is_in_hotspot : whether DBSCAN placed this complaint in an active cluster

    Returns
    -------
    {
      "priority_score"   : float (0-100),
      "priority_level"   : "Critical" | "High" | "Medium" | "Low",
      "keyword_score"    : int,
      "category_score"   : int,
      "cluster_score"    : int,
      "duplicate_score"  : int,
      "matched_keywords" : [str, ...],
      "priority_factors" : str   (human-readable explanation),
    }
    """
    title       = complaint.get("title", "") or ""
    description = complaint.get("description", "") or ""
    category    = complaint.get("category", "") or ""

    combined_text = f"{title} {description}"

    # 1. Keyword score (0-40)
    kw_score, matched_kws = _score_keywords(combined_text)

    # 2. Category baseline score (0-30)
    cat_score = CATEGORY_BASELINES.get(category, DEFAULT_CATEGORY_SCORE)

    # 3. Cluster / hotspot bonus (0-15)
    cluster_score = 12 if is_in_hotspot else 0

    # 4. Duplicate / volume bonus (0-15)
    dup_score = min(15, similar_count * 5)

    raw_total = kw_score + cat_score + cluster_score + dup_score
    final_score = min(100.0, float(raw_total))
    level = _level_from_score(final_score)

    # Build human-readable explanation
    factor_parts = [
        f"Urgency keywords ({kw_score}/40 pts): {', '.join(matched_kws[:5]) if matched_kws else 'none detected'}",
        f"Category severity ({cat_score}/30 pts): '{category}'",
        f"Geographic hotspot bonus ({cluster_score}/15 pts): {'Active hotspot area' if is_in_hotspot else 'No cluster detected'}",
        f"Duplicate report volume ({dup_score}/15 pts): {similar_count} similar report(s)",
    ]
    explanation = " | ".join(factor_parts)

    return {
        "priority_score"   : round(final_score, 1),
        "priority_level"   : level,
        "keyword_score"    : kw_score,
        "category_score"   : cat_score,
        "cluster_score"    : cluster_score,
        "duplicate_score"  : dup_score,
        "matched_keywords" : matched_kws,
        "priority_factors" : explanation,
    }


def score_all_complaints(complaints: List[Dict]) -> List[Dict]:
    """
    Batch-scores a list of complaints.
    Complaints sharing a cluster_id > -1 are flagged is_in_hotspot=True.

    Returns the same list with priority fields updated in-place and returned.
    """
    # Find which cluster_ids are real clusters (not noise = -1)
    hotspot_ids = set(
        c["cluster_id"] for c in complaints
        if c.get("cluster_id") is not None and c["cluster_id"] != -1
    )

    for c in complaints:
        similar_count = sum(
            1 for other in complaints
            if other.get("duplicate_of_id") == c.get("id")
        )
        in_hotspot = c.get("cluster_id") in hotspot_ids and c.get("cluster_id") != -1

        result = compute_priority(c, similar_count=similar_count, is_in_hotspot=in_hotspot)
        c.update({
            "priority_score"  : result["priority_score"],
            "priority_level"  : result["priority_level"],
            "priority_factors": result["priority_factors"],
        })

    return complaints

