"""
ai/action_recommender.py - AI Action & SOP Recommendation Engine.
Maps complaint category, priority level, and contextual urgency keywords to
concrete operational steps, responsible departments, and SLA turnaround times.

This is a deterministic rule-based engine — no external API needed.
It is fully explainable: every recommendation traces back to an auditable rule.
"""

import re
from typing import Dict, List, Tuple

# ── Department Master ─────────────────────────────────────────────────────────
DEPARTMENTS: Dict[str, str] = {
    "Roads & Infrastructure"       : "Public Works Department",
    "Water Supply & Drainage"      : "Water Supply & Sewerage Board",
    "Electricity & Power"          : "Electricity Supply Board",
    "Sanitation & Waste Management": "Solid Waste Management Department",
    "Public Safety"                : "Civic Safety & Emergency Response",
}

# ── SLA turnaround by (category, priority_level) ─────────────────────────────
SLA_MATRIX: Dict[Tuple[str, str], str] = {
    ("Electricity & Power",           "Critical"): "Within 2 Hours",
    ("Electricity & Power",           "High")    : "Within 6 Hours",
    ("Electricity & Power",           "Medium")  : "Within 24 Hours",
    ("Electricity & Power",           "Low")     : "Within 72 Hours",

    ("Water Supply & Drainage",       "Critical"): "Within 3 Hours",
    ("Water Supply & Drainage",       "High")    : "Within 8 Hours",
    ("Water Supply & Drainage",       "Medium")  : "Within 48 Hours",
    ("Water Supply & Drainage",       "Low")     : "Within 5 Days",

    ("Roads & Infrastructure",        "Critical"): "Within 4 Hours",
    ("Roads & Infrastructure",        "High")    : "Within 12 Hours",
    ("Roads & Infrastructure",        "Medium")  : "Within 72 Hours",
    ("Roads & Infrastructure",        "Low")     : "Within 7 Days",

    ("Sanitation & Waste Management", "Critical"): "Within 4 Hours",
    ("Sanitation & Waste Management", "High")    : "Within 24 Hours",
    ("Sanitation & Waste Management", "Medium")  : "Within 48 Hours",
    ("Sanitation & Waste Management", "Low")     : "Within 5 Days",

    ("Public Safety",                 "Critical"): "Immediate / Within 1 Hour",
    ("Public Safety",                 "High")    : "Within 4 Hours",
    ("Public Safety",                 "Medium")  : "Within 24 Hours",
    ("Public Safety",                 "Low")     : "Within 72 Hours",
}
DEFAULT_SLA = "Within 5 Business Days"

# ── Keyword → specific action overrides ──────────────────────────────────────
# Checked against (title + description) lowercase.
# Format: (trigger_keywords, action_text)
KEYWORD_ACTIONS: List[Tuple[List[str], str]] = [
    (["live wire", "snapped wire", "sparking wire", "wire touching water"],
     "EMERGENCY: Isolate feeder circuit immediately. Deploy electrical safety crew with insulated equipment and rubber boots. Cordon 20 m radius with hazard tape."),

    (["transformer", "spark", "smoke", "explod"],
     "Trip distribution transformer breaker. Deploy substation emergency team with CO₂ fire extinguishers. Inspect windings and replace if needed."),

    (["gas leak", "lpg", "gas smell", "pipeline leak"],
     "EMERGENCY: Notify Fire & Disaster Response. Close isolation valve on affected gas supply line. Evacuate 100 m radius. No open flames."),

    (["sinkhole", "cave-in", "road collapse", "tarmac collapsed"],
     "Close affected lanes immediately with jersey barriers. Mobilise geotechnical assessment team for sub-base soil stability test. Apply concrete backfill."),

    (["sewage overflow", "sewage burst", "black water", "sewage flooding"],
     "Deploy emergency drainage jetting truck to clear blockage. Apply lime disinfectant. Cordon pedestrian access until cleaned."),

    (["contaminated water", "yellow water", "foul smell water", "cholera"],
     "Halt distribution on affected pipeline segment. Send water quality inspector for sampling. Issue public health advisory to affected ward."),

    (["biomedical", "syringe", "medical waste", "needle"],
     "Dispatch authorised bio-hazardous waste containment vehicle. Seal area with bio-hazard tape. Issue formal regulatory notice to offending clinic."),

    (["open manhole", "missing manhole", "manhole cover"],
     "Cover immediately with temporary safety steel grating. Install certified lockable composite replacement lid within 24 hours."),

    (["flyover", "flyover pillar", "bridge crack", "structural"],
     "Dispatch structural engineering inspection unit. Restrict heavy vehicle traffic on span. Commission ultrasound integrity test."),

    (["fallen tree", "hanging branch", "tree fallen"],
     "Deploy hydraulic tree cutter vehicle. Ensure overhead power lines are clear. Remove debris from roadway."),

    (["pothole", "deep pothole", "road surface"],
     "Deploy rapid asphalt patching van. Fill pothole with cold-mix or hot-mix asphalt. Place reflector cones until surface cures."),

    (["flooding", "waterlogging", "flooded road"],
     "Deploy mobile dewatering pump. Clear blocked storm drains with vacuum jetting truck. Inspect and clear inlet gratings."),

    (["garbage", "waste dump", "illegal dump"],
     "Send heavy waste loader and 2 compactor trucks. Sanitise perimeter with lime powder. Issue penalty notice for illegal dumping."),

    (["stray dog", "dog pack", "dog biting"],
     "Deploy Animal Welfare Squad for humane capture. Vaccinate and transfer to veterinary shelter for sterilisation."),
]

# ── Category-level default SOPs ───────────────────────────────────────────────
CATEGORY_SOPS: Dict[str, str] = {
    "Roads & Infrastructure":
        "Assign road maintenance crew for site inspection. Barricade hazard area. Schedule repair based on severity assessment.",
    "Water Supply & Drainage":
        "Dispatch drainage/water supply engineer for site inspection. Check pipeline pressure and valve status. Arrange repair crew.",
    "Electricity & Power":
        "Notify on-call electrical engineer. Inspect feeder cable and transformer. Restore supply after fault clearance.",
    "Sanitation & Waste Management":
        "Schedule waste collection truck for next available slot. Assign sanitation inspector for site assessment.",
    "Public Safety":
        "Dispatch civic safety officer for assessment. Coordinate with relevant department (police, fire brigade, animal welfare) as needed.",
}


def _find_keyword_action(text: str) -> str:
    """Returns the first matching specific action override, or empty string."""
    text_lower = text.lower()
    for triggers, action in KEYWORD_ACTIONS:
        if any(kw in text_lower for kw in triggers):
            return action
    return ""


def generate_recommendation(complaint: Dict) -> Dict:
    """
    Generates a full action recommendation for a single complaint.

    Parameters
    ----------
    complaint : dict with keys category, priority_level, title, description

    Returns
    -------
    {
      "department"             : str,
      "action_recommendation"  : str,
      "sla"                    : str,
      "citizen_update_message" : str,
      "recommendation_basis"   : str,
    }
    """
    category = complaint.get("category") or "Public Safety"
    priority = complaint.get("priority_level") or "Medium"
    title    = complaint.get("title", "") or ""
    desc     = complaint.get("description", "") or ""
    text     = f"{title} {desc}"

    department = DEPARTMENTS.get(category, "Municipal Corporation")
    sla        = SLA_MATRIX.get((category, priority), DEFAULT_SLA)

    # Pick action text: specific override > category SOP
    specific = _find_keyword_action(text)
    action   = specific if specific else CATEGORY_SOPS.get(category, "Assign to relevant department for review.")

    basis = (
        f"Category: '{category}' → assigned to {department}. "
        f"Priority: {priority} → SLA: {sla}. "
        f"{'Specific keyword trigger matched.' if specific else 'Standard SOP applied.'}"
    )

    citizen_msg = (
        f"Your complaint has been received and routed to the {department}. "
        f"Based on the priority level '{priority}', a response is expected {sla.lower()}. "
        f"Track progress using your Complaint ID."
    )

    return {
        "department"             : department,
        "action_recommendation"  : action,
        "sla"                    : sla,
        "citizen_update_message" : citizen_msg,
        "recommendation_basis"   : basis,
    }


def batch_recommend(complaints: List[Dict]) -> List[Dict]:
    """
    Applies generate_recommendation to a list of complaints.
    Updates each dict in-place and returns the list.
    """
    for c in complaints:
        rec = generate_recommendation(c)
        c["department"]            = rec["department"]
        c["action_recommendation"] = rec["action_recommendation"]
    return complaints

