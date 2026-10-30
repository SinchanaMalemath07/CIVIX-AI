"""
ai/categorizer.py - Automatic complaint categorization module.
Uses Scikit-learn TF-IDF Vectorizer and Multinomial Naive Bayes classifier
to predict civic complaint categories with confidence scores.

How it works:
1. A small labelled training set of representative civic complaints
   is defined in-module (no external API needed).
2. A Scikit-learn Pipeline (TfidfVectorizer → MultinomialNB) is trained
   at first call and cached for the session.
3. Incoming text is vectorised and the classifier returns the most
   probable category plus a confidence percentage.
4. If confidence is below CONFIDENCE_THRESHOLD, a keyword-match fallback
   takes over so the system always returns a usable result.
"""

import re
from functools import lru_cache
from typing import Dict, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

# ── Category labels ──────────────────────────────────────────────────────────

CATEGORIES = [
    "Roads & Infrastructure",
    "Water Supply & Drainage",
    "Electricity & Power",
    "Sanitation & Waste Management",
    "Public Safety",
]

# Confidence below this → fallback to keyword matching
CONFIDENCE_THRESHOLD = 0.35

# ── Training corpus ───────────────────────────────────────────────────────────
# Each entry is (text, label).  Include synonyms, spelling variants, and short
# phrases so the tiny NB model generalises well.

TRAINING_DATA: list[Tuple[str, str]] = [
    # Roads & Infrastructure
    ("pothole road broken cracked surface", "Roads & Infrastructure"),
    ("large deep pothole causing accident", "Roads & Infrastructure"),
    ("road cave in sinkhole tarmac collapsed", "Roads & Infrastructure"),
    ("road divider barrier fallen concrete debris", "Roads & Infrastructure"),
    ("footpath pavement broken tiles rebar exposed", "Roads & Infrastructure"),
    ("bridge flyover pillar cracks structural damage", "Roads & Infrastructure"),
    ("road encroachment illegal construction footpath", "Roads & Infrastructure"),
    ("speed breaker missing road sign uprooted", "Roads & Infrastructure"),
    ("traffic road median damage blocks lane", "Roads & Infrastructure"),
    ("construction pit excavation unfenced road ditch", "Roads & Infrastructure"),
    ("road waterlogging flooded street puddle", "Roads & Infrastructure"),
    ("streetlight pole damaged broken footpath", "Roads & Infrastructure"),

    # Water Supply & Drainage
    ("water pipeline burst flooding road leak", "Water Supply & Drainage"),
    ("drinking water contaminated yellow foul smell", "Water Supply & Drainage"),
    ("no water supply shortage pipe dry", "Water Supply & Drainage"),
    ("sewage overflow drain manhole flooding", "Water Supply & Drainage"),
    ("stormwater drain blocked clogged silt", "Water Supply & Drainage"),
    ("water pressure low trickle barely flows", "Water Supply & Drainage"),
    ("drain culvert submerged backflow basement flooding", "Water Supply & Drainage"),
    ("open manhole missing cover sewer", "Water Supply & Drainage"),
    ("pipeline leaking water gushing potable supply", "Water Supply & Drainage"),
    ("sewage pipe ruptured black waste water stench", "Water Supply & Drainage"),
    ("cholera contamination health risk water tap", "Water Supply & Drainage"),

    # Electricity & Power
    ("power cut electricity outage no light", "Electricity & Power"),
    ("live wire snapped sparking hanging road", "Electricity & Power"),
    ("transformer sparking smoke fire electrical", "Electricity & Power"),
    ("street light dead broken not working dark", "Electricity & Power"),
    ("overhead cable touching tree branch fire risk", "Electricity & Power"),
    ("substation earthing wire cut voltage fluctuation", "Electricity & Power"),
    ("electric pole tilted fallen cable danger", "Electricity & Power"),
    ("exposed underground cable conduit open trench", "Electricity & Power"),
    ("electricity supply faulty frequent tripping", "Electricity & Power"),
    ("transformer humming loud noise sparks explode", "Electricity & Power"),
    ("traffic signal lights dead junction dark", "Electricity & Power"),

    # Sanitation & Waste Management
    ("garbage dump waste uncollected rotting smell", "Sanitation & Waste Management"),
    ("illegal dumping waste plastic burning open", "Sanitation & Waste Management"),
    ("biomedical waste syringes needles medical hazard", "Sanitation & Waste Management"),
    ("construction dust truck uncovered particulate", "Sanitation & Waste Management"),
    ("stray animals rats garbage heap street", "Sanitation & Waste Management"),
    ("waste bin overflowing litter footpath", "Sanitation & Waste Management"),
    ("sewage sludge dumped footpath contractor", "Sanitation & Waste Management"),
    ("carcass dead animal decomposing road", "Sanitation & Waste Management"),
    ("open burning plastic toxic smoke fumes", "Sanitation & Waste Management"),
    ("solid waste compactor not collected area", "Sanitation & Waste Management"),

    # Public Safety
    ("gas leak lpg pipeline explosion danger", "Public Safety"),
    ("stray dog pack biting chasing pedestrian", "Public Safety"),
    ("noise pollution loudspeaker late night blasting", "Public Safety"),
    ("open manhole near school park children danger", "Public Safety"),
    ("fallen tree branch bus stop overhead hazard", "Public Safety"),
    ("broken swing playground metal sharp children", "Public Safety"),
    ("dangerous structure collapsing wall building", "Public Safety"),
    ("unauthorized construction unsafe building", "Public Safety"),
    ("road accident black spot no signage", "Public Safety"),
    ("flood risk waterlogging pedestrian danger", "Public Safety"),
    ("fire risk hazardous material stored road", "Public Safety"),
    ("chemical fumes toxic odor hazardous barrels leak", "Public Safety"),
]


def _clean_text(text: str) -> str:
    """Lowercase and strip special characters, keeping spaces."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


@lru_cache(maxsize=1)
def _get_trained_pipeline() -> Pipeline:
    """Trains and caches the TF-IDF + NB pipeline (runs once per session)."""
    texts, labels = zip(*TRAINING_DATA)
    texts = [_clean_text(t) for t in texts]

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=2000,
            min_df=1,
            sublinear_tf=True
        )),
        ("clf", MultinomialNB(alpha=0.5))
    ])
    pipeline.fit(texts, labels)
    return pipeline


# Keyword fallback dictionary ─────────────────────────────────────────────────
_KEYWORD_MAP: Dict[str, list[str]] = {
    "Roads & Infrastructure": [
        "pothole", "road", "footpath", "pavement", "flyover", "bridge",
        "sinkhole", "tarmac", "median", "divider", "encroachment", "signage"
    ],
    "Water Supply & Drainage": [
        "water", "pipe", "drain", "sewage", "sewer", "manhole", "clog",
        "flood", "leak", "contaminated", "supply", "culvert", "drainage"
    ],
    "Electricity & Power": [
        "electricity", "power", "wire", "cable", "transformer", "electric",
        "streetlight", "voltage", "current", "spark", "outage", "light"
    ],
    "Sanitation & Waste Management": [
        "garbage", "waste", "trash", "dump", "litter", "biomedical",
        "syringe", "burning", "smoke", "dust", "carcass", "rat"
    ],
    "Public Safety": [
        "gas", "explosion", "danger", "stray", "dog", "noise", "accident",
        "hazard", "unsafe", "fire", "risk", "collapse", "playground",
        "chemical", "toxic", "fumes"
    ],
}


def _keyword_fallback(text: str) -> Tuple[str, float]:
    """Counts keyword hits per category and returns the best match."""
    text_lower = text.lower()
    scores = {cat: 0 for cat in CATEGORIES}
    for cat, keywords in _KEYWORD_MAP.items():
        for kw in keywords:
            if kw in text_lower:
                scores[cat] += 1

    best_cat = max(scores, key=scores.__getitem__)
    best_score = scores[best_cat]
    # Normalise to a rough confidence (max 0.60 so it stays below ML scores)
    confidence = min(0.60, best_score / max(len(_KEYWORD_MAP[best_cat]), 1))
    return best_cat, confidence


def predict_category(title: str, description: str) -> Dict:
    """
    Predicts the civic complaint category from its title and description.

    Returns a dict with:
      - predicted_category (str)
      - confidence (float, 0-1)
      - confidence_pct (str, e.g. "78%")
      - method (str: "ml_model" | "keyword_fallback")
      - all_scores (dict: {category: probability})
    """
    combined = _clean_text(f"{title} {description}")

    pipeline = _get_trained_pipeline()
    proba = pipeline.predict_proba([combined])[0]
    classes = pipeline.classes_
    scores = dict(zip(classes, proba))

    best_idx = proba.argmax()
    best_cat = classes[best_idx]
    best_conf = float(proba[best_idx])

    method = "ml_model"
    if best_conf < CONFIDENCE_THRESHOLD:
        fallback_cat, fallback_conf = _keyword_fallback(combined)
        best_cat = fallback_cat
        best_conf = fallback_conf
        method = "keyword_fallback"

    return {
        "predicted_category": best_cat,
        "confidence": round(best_conf, 4),
        "confidence_pct": f"{round(best_conf * 100, 1)}%",
        "method": method,
        "all_scores": {k: round(float(v), 4) for k, v in scores.items()},
    }

