"""
test_phase3_ai.py - pytest test suite for CIVIX AI Intelligence Engine.

Each test_* function maps to one concrete assertion so that
`pytest test_phase3_ai.py -v` shows a clean, readable per-test line.

Modules covered:
  1. Categorizer        (TF-IDF + Naive Bayes)
  2. Duplicate Detector (TF-IDF Cosine + Haversine proximity)
  3. Priority Scorer    (Explainable weighted heuristic)
  4. Hotspot Detector   (DBSCAN Haversine clustering)
  5. Action Recommender (SOP rule engine)
  6. Full Pipeline      (analyze_complaint end-to-end)
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))

import pytest
import database
from ai.categorizer         import predict_category
from ai.duplicate_detector  import detect_duplicates
from ai.priority_scorer     import compute_priority
from ai.hotspot_detector    import detect_hotspots, apply_cluster_labels
from ai.action_recommender  import generate_recommendation
from ai                     import analyze_complaint


# ============================================================================
# MODULE 1 – COMPLAINT CATEGORIZER
# ============================================================================

class TestCategorizer:
    """TF-IDF + Multinomial Naive Bayes category prediction."""

    def test_roads_and_infrastructure(self):
        r = predict_category(
            "Large pothole on 80ft road causing bike accidents",
            "Deep 1-meter pothole at the main junction. Two vehicles fell this morning."
        )
        assert r["predicted_category"] == "Roads & Infrastructure"

    def test_water_supply_and_drainage(self):
        r = predict_category(
            "Sewage pipeline burst flooding road",
            "Main sewage pipe ruptured. Black wastewater covering two lanes. Unbearable stench."
        )
        assert r["predicted_category"] == "Water Supply & Drainage"

    def test_electricity_and_power(self):
        r = predict_category(
            "Transformer sparking and catching fire near ITPL gate",
            "Orange sparks and smoke from the roadside distribution transformer unit."
        )
        assert r["predicted_category"] == "Electricity & Power"

    def test_sanitation_and_waste(self):
        r = predict_category(
            "Illegal garbage dump rotting for 10 days",
            "Piles of decomposing organic waste and plastic blocking the street corner."
        )
        assert r["predicted_category"] == "Sanitation & Waste Management"

    def test_public_safety_gas_leak(self):
        r = predict_category(
            "Gas pipeline leak smell detected near residential complex",
            "Intense LPG odour spreading 200 metres. Residents feeling dizzy. Explosion risk."
        )
        assert r["predicted_category"] == "Public Safety"

    def test_electricity_street_light(self):
        r = predict_category(
            "Streetlight pole broken, area pitch dark after 7pm",
            "Four consecutive street light poles dead on the main road stretch."
        )
        assert r["predicted_category"] == "Electricity & Power"

    def test_contaminated_water(self):
        r = predict_category(
            "Drinking water yellow and smells of sewage",
            "Municipal tap water cloudy and foul-smelling. Fear of cholera outbreak."
        )
        assert r["predicted_category"] == "Water Supply & Drainage"

    def test_result_has_confidence_pct(self):
        r = predict_category("pothole road damage", "large pothole near school")
        assert "confidence_pct" in r
        assert "%" in r["confidence_pct"]

    def test_result_has_method_field(self):
        r = predict_category("pothole road damage", "large pothole near school")
        assert r["method"] in ("ml_model", "keyword_fallback")

    def test_result_has_all_scores(self):
        r = predict_category("garbage dump near park", "waste uncollected for days")
        assert isinstance(r["all_scores"], dict)
        assert len(r["all_scores"]) == 5  # one score per category


# ============================================================================
# MODULE 2 – DUPLICATE DETECTOR
# ============================================================================

class TestDuplicateDetector:
    """TF-IDF cosine similarity + Haversine geographic proximity filter."""

    # Near-identical complaint very close to CIVIX-1004 (Koramangala pothole)
    NEAR_DUP = {
        "id"         : "CIVIX-NEW1",
        "title"      : "Huge deep pothole near Sony World signal causing bike falls",
        "description": "Very large pothole right in front of the Sony junction on 80 feet road. Multiple bikers slipped.",
        "category"   : "Roads & Infrastructure",
        "latitude"   : 12.9353,
        "longitude"  : 77.6246,
    }

    # Completely different topic & different location
    UNRELATED = {
        "id"         : "CIVIX-NEW2",
        "title"      : "Broken playground swing at Madhavan Park",
        "description": "Iron chain swing snapped. Sharp metal bar sticking out. Children at risk.",
        "category"   : "Public Safety",
        "latitude"   : 12.9295,
        "longitude"  : 77.5840,
    }

    # Similar text but ~60 km away from CIVIX-1016
    FAR_AWAY = {
        "id"         : "CIVIX-NEW3",
        "title"      : "Transformer sparking near residential area",
        "description": "Orange sparks and smoke from roadside transformer. People scared.",
        "category"   : "Electricity & Power",
        "latitude"   : 13.1200,
        "longitude"  : 77.3000,
    }

    def test_near_duplicate_is_detected(self, small_pool):
        r = detect_duplicates(self.NEAR_DUP, small_pool, exclude_id="CIVIX-NEW1")
        assert r["is_duplicate"] is True

    def test_near_duplicate_best_match_is_correct(self, small_pool):
        r = detect_duplicates(self.NEAR_DUP, small_pool, exclude_id="CIVIX-NEW1")
        assert r["best_match_id"] == "CIVIX-1004"

    def test_near_duplicate_similarity_pct_is_string(self, small_pool):
        r = detect_duplicates(self.NEAR_DUP, small_pool, exclude_id="CIVIX-NEW1")
        assert r["best_similarity_pct"] is not None
        assert "%" in r["best_similarity_pct"]

    def test_near_duplicate_has_explanation(self, small_pool):
        r = detect_duplicates(self.NEAR_DUP, small_pool, exclude_id="CIVIX-NEW1")
        assert len(r["explanation"]) > 10

    def test_unrelated_complaint_not_duplicate(self, small_pool):
        r = detect_duplicates(self.UNRELATED, small_pool, exclude_id="CIVIX-NEW2")
        assert r["is_duplicate"] is False

    def test_unrelated_complaint_has_no_matches(self, small_pool):
        r = detect_duplicates(self.UNRELATED, small_pool, exclude_id="CIVIX-NEW2")
        assert len(r["matches"]) == 0

    def test_geographically_distant_not_duplicate(self, small_pool):
        """Same text, but 60+ km away -> geographic filter must block it."""
        r = detect_duplicates(self.FAR_AWAY, small_pool, exclude_id="CIVIX-NEW3")
        assert r["is_duplicate"] is False

    def test_empty_pool_returns_no_duplicate(self):
        r = detect_duplicates(self.NEAR_DUP, [], exclude_id="CIVIX-NEW1")
        assert r["is_duplicate"] is False
        assert r["confidence_level"] == "None"

    def test_matches_sorted_by_similarity(self, small_pool):
        r = detect_duplicates(self.NEAR_DUP, small_pool, exclude_id="CIVIX-NEW1")
        scores = [float(m["similarity_pct"].strip("%")) for m in r["matches"]]
        assert scores == sorted(scores, reverse=True)


# ============================================================================
# MODULE 3 – PRIORITY SCORER
# ============================================================================

class TestPriorityScorer:
    """Transparent weighted urgency scoring (0-100)."""

    def test_live_wire_school_is_critical(self):
        r = compute_priority({
            "title"      : "Live electrical wire snapped over waterlogged school crossing",
            "description": "High-tension cable touching water on pedestrian crossing in front of school. Shock risk.",
            "category"   : "Electricity & Power",
        }, similar_count=2, is_in_hotspot=True)
        assert r["priority_level"] == "Critical"

    def test_live_wire_score_above_80(self):
        r = compute_priority({
            "title"      : "Live electrical wire snapped over waterlogged school crossing",
            "description": "High-tension cable touching water on pedestrian crossing in front of school. Shock risk.",
            "category"   : "Electricity & Power",
        }, similar_count=2, is_in_hotspot=True)
        assert r["priority_score"] >= 80.0

    def test_pothole_with_hotspot_is_high(self):
        r = compute_priority({
            "title"      : "Large pothole causing accidents near main junction",
            "description": "Big dangerous pothole at junction. Two bike accidents today. Danger for commuters.",
            "category"   : "Roads & Infrastructure",
        }, similar_count=1, is_in_hotspot=True)
        assert r["priority_level"] == "High"

    def test_broken_signboard_is_low(self):
        r = compute_priority({
            "title"      : "Road name signage fallen on footpath",
            "description": "Metal street board knocked down. Sharp edges on walkway.",
            "category"   : "Roads & Infrastructure",
        }, similar_count=0, is_in_hotspot=False)
        assert r["priority_level"] == "Low"

    def test_gas_leak_is_critical(self):
        r = compute_priority({
            "title"      : "Gas pipeline leak near residential complex",
            "description": "Intense LPG smell. Residents dizzy. Explosion risk. Emergency needed.",
            "category"   : "Public Safety",
        }, similar_count=3, is_in_hotspot=True)
        assert r["priority_level"] == "Critical"

    def test_garbage_bin_is_low(self):
        r = compute_priority({
            "title"      : "Broken garbage bin lid",
            "description": "Bin near bus stop has a broken lid.",
            "category"   : "Sanitation & Waste Management",
        }, similar_count=0, is_in_hotspot=False)
        assert r["priority_level"] == "Low"

    def test_score_capped_at_100(self):
        r = compute_priority({
            "title"      : "explosion fire live wire emergency danger hazard accident school children hospital",
            "description": "gas leak lpg snapped sparking electrocution sinkhole collapse biomedical emergency",
            "category"   : "Electricity & Power",
        }, similar_count=5, is_in_hotspot=True)
        assert r["priority_score"] <= 100.0

    def test_factors_contains_keyword_label(self):
        r = compute_priority({
            "title": "overflowing drain near hospital danger",
            "description": "sewage blocking road",
            "category": "Water Supply & Drainage",
        })
        assert "keyword" in r["priority_factors"].lower()

    def test_factors_contains_category_label(self):
        r = compute_priority({
            "title": "overflowing drain near hospital danger",
            "description": "sewage blocking road",
            "category": "Water Supply & Drainage",
        })
        assert "category" in r["priority_factors"].lower()

    def test_hotspot_bonus_increases_score(self):
        base = compute_priority({
            "title": "pothole road damaged",
            "description": "pothole near junction",
            "category": "Roads & Infrastructure",
        }, similar_count=0, is_in_hotspot=False)
        with_hotspot = compute_priority({
            "title": "pothole road damaged",
            "description": "pothole near junction",
            "category": "Roads & Infrastructure",
        }, similar_count=0, is_in_hotspot=True)
        assert with_hotspot["priority_score"] > base["priority_score"]

    def test_duplicate_bonus_increases_score(self):
        base = compute_priority({
            "title": "garbage dump waste street",
            "description": "Illegal dump corner",
            "category": "Sanitation & Waste Management",
        }, similar_count=0)
        with_dups = compute_priority({
            "title": "garbage dump waste street",
            "description": "Illegal dump corner",
            "category": "Sanitation & Waste Management",
        }, similar_count=3)
        assert with_dups["priority_score"] > base["priority_score"]


# ============================================================================
# MODULE 4 – HOTSPOT DETECTOR
# ============================================================================

# Synthetic dataset: 2 dense geographic clusters + 2 noise outliers
HOTSPOT_COMPLAINTS = [
    # Cluster A – Koramangala (~5 complaints within 400 m)
    {"id": "K1", "latitude": 12.9350, "longitude": 77.6244, "category": "Roads & Infrastructure",     "priority_level": "High"},
    {"id": "K2", "latitude": 12.9353, "longitude": 77.6247, "category": "Roads & Infrastructure",     "priority_level": "High"},
    {"id": "K3", "latitude": 12.9348, "longitude": 77.6241, "category": "Water Supply & Drainage",    "priority_level": "Medium"},
    {"id": "K4", "latitude": 12.9355, "longitude": 77.6249, "category": "Roads & Infrastructure",     "priority_level": "Critical"},
    {"id": "K5", "latitude": 12.9346, "longitude": 77.6240, "category": "Electricity & Power",        "priority_level": "Medium"},
    # Cluster B – Indiranagar (~4 complaints within 300 m)
    {"id": "I1", "latitude": 12.9718, "longitude": 77.6410, "category": "Water Supply & Drainage",    "priority_level": "High"},
    {"id": "I2", "latitude": 12.9722, "longitude": 77.6413, "category": "Water Supply & Drainage",    "priority_level": "Critical"},
    {"id": "I3", "latitude": 12.9715, "longitude": 77.6408, "category": "Water Supply & Drainage",    "priority_level": "Medium"},
    {"id": "I4", "latitude": 12.9720, "longitude": 77.6415, "category": "Sanitation & Waste Management", "priority_level": "Low"},
    # Outliers (noise)
    {"id": "O1", "latitude": 13.0800, "longitude": 77.5000, "category": "Public Safety",              "priority_level": "Low"},
    {"id": "O2", "latitude": 12.8000, "longitude": 77.4000, "category": "Electricity & Power",        "priority_level": "Medium"},
]


@pytest.fixture(scope="module")
def hotspot_result():
    return detect_hotspots(HOTSPOT_COMPLAINTS)


class TestHotspotDetector:
    """DBSCAN Haversine geographic clustering."""

    def test_at_least_two_clusters_detected(self, hotspot_result):
        assert hotspot_result["total_clusters"] >= 2

    def test_noise_outliers_detected(self, hotspot_result):
        assert hotspot_result["total_noise"] >= 2

    def test_cluster_summary_has_cluster_id(self, hotspot_result):
        for s in hotspot_result["cluster_summaries"]:
            assert "cluster_id" in s

    def test_cluster_summary_has_complaint_count(self, hotspot_result):
        for s in hotspot_result["cluster_summaries"]:
            assert "complaint_count" in s
            assert s["complaint_count"] >= 2  # DBSCAN min_samples=2

    def test_cluster_summary_has_dominant_category(self, hotspot_result):
        for s in hotspot_result["cluster_summaries"]:
            assert "dominant_category" in s
            assert len(s["dominant_category"]) > 0

    def test_cluster_summary_has_severity_level(self, hotspot_result):
        for s in hotspot_result["cluster_summaries"]:
            assert s["severity_level"] in ("Critical", "High", "Medium", "Low")

    def test_cluster_summary_has_centroid(self, hotspot_result):
        for s in hotspot_result["cluster_summaries"]:
            assert "centroid_lat" in s
            assert "centroid_lon" in s
            # Centroid must be a valid latitude/longitude
            assert -90 <= s["centroid_lat"] <= 90
            assert -180 <= s["centroid_lon"] <= 180

    def test_cluster_summary_has_complaint_ids(self, hotspot_result):
        for s in hotspot_result["cluster_summaries"]:
            assert "complaint_ids" in s
            assert isinstance(s["complaint_ids"], list)

    def test_cluster_ids_consistent_between_labels_and_summaries(self, hotspot_result):
        summary_cluster_ids = {s["cluster_id"] for s in hotspot_result["cluster_summaries"]}
        label_cluster_ids   = {v for v in hotspot_result["labels"].values() if v != -1}
        assert summary_cluster_ids == label_cluster_ids

    def test_koramangala_complaints_share_cluster(self, hotspot_result):
        labels = hotspot_result["labels"]
        k_labels = {labels[k] for k in ["K1", "K2", "K3", "K4", "K5"]}
        # All 5 Koramangala points should be in the same cluster (not -1)
        assert len(k_labels) == 1
        assert -1 not in k_labels

    def test_indiranagar_complaints_share_cluster(self, hotspot_result):
        labels = hotspot_result["labels"]
        i_labels = {labels[k] for k in ["I1", "I2", "I3", "I4"]}
        assert len(i_labels) == 1
        assert -1 not in i_labels

    def test_outliers_labeled_as_noise(self, hotspot_result):
        labels = hotspot_result["labels"]
        assert labels["O1"] == -1
        assert labels["O2"] == -1

    def test_apply_cluster_labels_sets_cluster_id_on_all(self, hotspot_result):
        complaints = [dict(c) for c in HOTSPOT_COMPLAINTS]
        apply_cluster_labels(complaints, hotspot_result["labels"])
        assert all("cluster_id" in c for c in complaints)


# ============================================================================
# MODULE 5 – ACTION RECOMMENDER
# ============================================================================

class TestActionRecommender:
    """SOP rule engine: department routing, SLA, keyword overrides."""

    def test_electricity_critical_department(self):
        r = generate_recommendation({"title": "Live wire snapped", "description": "live wire touching water near school crossing.", "category": "Electricity & Power", "priority_level": "Critical"})
        assert "Electricity" in r["department"]

    def test_electricity_critical_sla(self):
        r = generate_recommendation({"title": "Live wire snapped", "description": "live wire touching water", "category": "Electricity & Power", "priority_level": "Critical"})
        assert "2 Hours" in r["sla"]

    def test_electricity_keyword_trigger_action(self):
        r = generate_recommendation({"title": "Live wire snapped over waterlogged road", "description": "live wire touching water pedestrian crossing", "category": "Electricity & Power", "priority_level": "Critical"})
        assert "Isolate" in r["action_recommendation"] or "EMERGENCY" in r["action_recommendation"]

    def test_water_high_department(self):
        r = generate_recommendation({"title": "Sewage pipe burst", "description": "sewage overflow flooding two lanes", "category": "Water Supply & Drainage", "priority_level": "High"})
        assert "Water" in r["department"]

    def test_water_high_sla(self):
        r = generate_recommendation({"title": "Sewage pipe burst", "description": "sewage overflow flooding two lanes", "category": "Water Supply & Drainage", "priority_level": "High"})
        assert "8 Hours" in r["sla"]

    def test_roads_high_department(self):
        r = generate_recommendation({"title": "Pothole on 80ft road", "description": "Large pothole causing accidents", "category": "Roads & Infrastructure", "priority_level": "High"})
        assert "Public Works" in r["department"]

    def test_roads_high_sla(self):
        r = generate_recommendation({"title": "Pothole on 80ft road", "description": "Large pothole causing accidents", "category": "Roads & Infrastructure", "priority_level": "High"})
        assert "12 Hours" in r["sla"]

    def test_sanitation_low_sla(self):
        r = generate_recommendation({"title": "Garbage bin overflowing", "description": "bin near bus stop not collected for a week", "category": "Sanitation & Waste Management", "priority_level": "Low"})
        assert "5 Days" in r["sla"]

    def test_public_safety_critical_immediate_sla(self):
        r = generate_recommendation({"title": "Gas leak near apartment", "description": "LPG gas smell detected near residential gate", "category": "Public Safety", "priority_level": "Critical"})
        assert "1 Hour" in r["sla"]

    def test_citizen_update_message_present(self):
        r = generate_recommendation({"title": "broken road", "description": "pothole", "category": "Roads & Infrastructure", "priority_level": "Medium"})
        assert len(r.get("citizen_update_message", "").strip()) > 10

    def test_recommendation_basis_mentions_category(self):
        r = generate_recommendation({"title": "broken road", "description": "pothole", "category": "Roads & Infrastructure", "priority_level": "Medium"})
        assert "category" in r["recommendation_basis"].lower()

    def test_recommendation_basis_mentions_priority(self):
        r = generate_recommendation({"title": "broken road", "description": "pothole", "category": "Roads & Infrastructure", "priority_level": "Medium"})
        assert "priority" in r["recommendation_basis"].lower()

    def test_gas_leak_keyword_triggers_emergency_action(self):
        r = generate_recommendation({"title": "Gas leak lpg pipeline near colony", "description": "gas smell spreading. Explosion risk.", "category": "Public Safety", "priority_level": "Critical"})
        action = r["action_recommendation"].lower()
        assert "gas" in action or "fire" in action or "evacuate" in action or "valve" in action

    def test_sewage_keyword_triggers_jetting_action(self):
        r = generate_recommendation({"title": "sewage overflow on main road", "description": "sewage burst flooding road", "category": "Water Supply & Drainage", "priority_level": "High"})
        action = r["action_recommendation"].lower()
        assert "drain" in action or "jetting" in action or "lime" in action


# ============================================================================
# MODULE 6 – FULL AI PIPELINE (analyze_complaint)
# ============================================================================

class TestFullPipeline:
    """End-to-end analyze_complaint() integration test."""

    TRANSFORMER_COMPLAINT = {
        "id"          : "CIVIX-TEST01",
        "title"       : "Sparks and smoke from power transformer near ITPL gate",
        "description" : "Transformer on the footpath is blasting sparks onto parked motorcycles. Fire danger.",
        "category"    : "Electricity & Power",
        "latitude"    : 12.9867,
        "longitude"   : 77.7379,
        "address"     : "ITPL Main Road Gate 2, Whitefield",
        "status"      : "Submitted",
        "priority_level": "Medium",
    }

    @pytest.fixture(scope="class")
    @classmethod
    def pipeline_result(cls, all_complaints):
        return analyze_complaint(cls.TRANSFORMER_COMPLAINT, all_complaints)

    def test_predicted_category_is_electricity(self, pipeline_result):
        assert pipeline_result["predicted_category"] == "Electricity & Power"

    def test_duplicate_is_detected(self, pipeline_result):
        # Seed has CIVIX-1016 and CIVIX-1017 at nearly identical coords & text
        assert pipeline_result["is_duplicate"] == 1

    def test_duplicate_has_match_id(self, pipeline_result):
        assert pipeline_result["duplicate_of_id"] is not None

    def test_priority_score_is_high(self, pipeline_result):
        assert pipeline_result["priority_score"] >= 55.0

    def test_priority_level_is_high_or_critical(self, pipeline_result):
        assert pipeline_result["priority_level"] in ("High", "Critical")

    def test_department_is_electricity_board(self, pipeline_result):
        dept = pipeline_result.get("department", "").lower()
        assert "electricity" in dept or "power" in dept or "electric" in dept

    def test_action_recommendation_is_non_trivial(self, pipeline_result):
        action = pipeline_result.get("action_recommendation", "")
        assert len(action) > 20

    def test_priority_factors_is_explainable(self, pipeline_result):
        factors = pipeline_result.get("priority_factors", "")
        assert "keyword" in factors.lower()
        assert "category" in factors.lower()

    def test_result_contains_all_required_keys(self, pipeline_result):
        required = {
            "predicted_category", "is_duplicate", "duplicate_of_id",
            "cluster_id", "priority_score", "priority_level",
            "priority_factors", "department", "action_recommendation",
        }
        assert required.issubset(pipeline_result.keys())

    def test_cluster_id_is_integer(self, pipeline_result):
        assert isinstance(pipeline_result["cluster_id"], int)
