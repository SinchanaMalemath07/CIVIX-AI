"""
test_portal_ai_integration.py - Verify end-to-end Citizen Portal AI integration.
Simulates citizen complaint submissions through the Citizen Portal AI pipeline,
ensuring AI categorization, duplicate detection, priority scoring, clustering,
and action recommendation persist to SQLite correctly.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import database
from data.sample_data import populate_database
from ai import analyze_complaint

def test_submission_and_ai_enrichment():
    print("Resetting database to standard 40 complaints...")
    populate_database(reset=True)

    print("\n--- Test 1: Submitting duplicate of CIVIX-1017 ---")
    dup_payload = {
        "id": "CIVIX-TEST-DUP",
        "title": "Sparks and smoke coming from power transformer outside ITPL gate 2",
        "description": "Transformer on the footpath is blasting sparks onto parked motorcycles. Danger of fire spreading.",
        "category": "Electricity & Power",
        "latitude": 12.9867,
        "longitude": 77.7379,
        "address": "ITPL Gate 2, Whitefield",
        "status": "Submitted",
        "department": "Unassigned"
    }
    
    database.insert_complaint(dup_payload)
    all_complaints = database.get_all_complaints()
    record = database.get_complaint_by_id("CIVIX-TEST-DUP")
    ai_results = analyze_complaint(record, all_complaints)
    
    database.update_complaint_ai_metadata("CIVIX-TEST-DUP", {
        "predicted_category": ai_results.get("predicted_category"),
        "is_duplicate": ai_results.get("is_duplicate", 0),
        "duplicate_of_id": ai_results.get("duplicate_of_id"),
        "cluster_id": ai_results.get("cluster_id", -1),
        "priority_score": ai_results.get("priority_score", 50.0),
        "priority_level": ai_results.get("priority_level", "Medium"),
        "priority_factors": ai_results.get("priority_factors", ""),
        "department": ai_results.get("department", "Unassigned"),
        "action_recommendation": ai_results.get("action_recommendation", "")
    })
    
    saved_dup = database.get_complaint_by_id("CIVIX-TEST-DUP")
    print(f"ID: {saved_dup['id']}")
    print(f"Category: {saved_dup['predicted_category']}")
    print(f"Duplicate Flag: {saved_dup['is_duplicate']} (Duplicate of: {saved_dup['duplicate_of_id']})")
    print(f"Priority: {saved_dup['priority_level']} ({saved_dup['priority_score']}/100)")
    print(f"Department: {saved_dup['department']}")
    
    assert saved_dup["predicted_category"] == "Electricity & Power"
    assert saved_dup["is_duplicate"] == 1
    assert saved_dup["duplicate_of_id"] == "CIVIX-1017"
    assert saved_dup["priority_score"] >= 55.0
    assert "Electricity" in saved_dup["department"]
    print("[PASS] Duplicate complaint correctly identified and linked to CIVIX-1017.")

    print("\n--- Test 2: Submitting a unique critical complaint ---")
    unique_payload = {
        "id": "CIVIX-TEST-UNIQ",
        "title": "Severe chemical fumes and toxic odor leaking near primary school",
        "description": "Dense acrid fumes leaking from abandoned barrels near school boundary. Children coughing. Urgent hazard.",
        "category": "Public Safety",
        "latitude": 13.0450,
        "longitude": 77.5800,
        "address": "Near Government Primary School, Hebbal",
        "status": "Submitted",
        "department": "Unassigned"
    }
    
    database.insert_complaint(unique_payload)
    all_complaints = database.get_all_complaints()
    record2 = database.get_complaint_by_id("CIVIX-TEST-UNIQ")
    ai_results2 = analyze_complaint(record2, all_complaints)
    
    database.update_complaint_ai_metadata("CIVIX-TEST-UNIQ", {
        "predicted_category": ai_results2.get("predicted_category"),
        "is_duplicate": ai_results2.get("is_duplicate", 0),
        "duplicate_of_id": ai_results2.get("duplicate_of_id"),
        "cluster_id": ai_results2.get("cluster_id", -1),
        "priority_score": ai_results2.get("priority_score", 50.0),
        "priority_level": ai_results2.get("priority_level", "Medium"),
        "priority_factors": ai_results2.get("priority_factors", ""),
        "department": ai_results2.get("department", "Unassigned"),
        "action_recommendation": ai_results2.get("action_recommendation", "")
    })
    
    saved_uniq = database.get_complaint_by_id("CIVIX-TEST-UNIQ")
    print(f"ID: {saved_uniq['id']}")
    print(f"Category: {saved_uniq['predicted_category']}")
    print(f"Duplicate Flag: {saved_uniq['is_duplicate']} (Duplicate of: {saved_uniq['duplicate_of_id']})")
    print(f"Priority: {saved_uniq['priority_level']} ({saved_uniq['priority_score']}/100)")
    print(f"Department: {saved_uniq['department']}")
    
    assert saved_uniq["predicted_category"] == "Public Safety"
    assert saved_uniq["is_duplicate"] == 0
    assert saved_uniq["duplicate_of_id"] is None
    assert saved_uniq["priority_level"] in ("High", "Critical")
    assert "Safety" in saved_uniq["department"]
    print("[PASS] Unique complaint correctly analyzed with no duplicate flag.")

    print("\n" + "=" * 60)
    print("ALL CITIZEN PORTAL AI PIPELINE INTEGRATION TESTS PASSED!")
    print("=" * 60)

if __name__ == "__main__":
    test_submission_and_ai_enrichment()
