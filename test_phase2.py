"""
test_phase2.py - Phase 2 Verification and Test Script for Citizen Portal.
Tests:
1. Citizen complaint submission workflow.
2. Image storage in uploads/ folder.
3. Verification that complaint data is saved in SQLite database.
4. Verification of complaint tracking lookup by ID.
"""

import sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))

import database
from views.citizen_portal import UPLOADS_DIR

def run_phase2_tests():
    print("=" * 70)
    print("  CIVIX AI - PHASE 2 (CITIZEN PORTAL) VERIFICATION SUITE")
    print("=" * 70)

    # 1. Generate Next ID
    print("\n[Step 1] Testing unique complaint ID generation...")
    next_id = database.generate_next_complaint_id()
    print(f"  Generated Next ID: {next_id}")
    assert next_id.startswith("CIVIX-"), "Complaint ID must start with 'CIVIX-'"
    print("  [PASS] ID generation verified.")

    # 2. Simulate Image Upload
    print("\n[Step 2] Simulating image evidence upload...")
    test_img = Image.new("RGB", (200, 200), color=(58, 134, 255))
    test_filename = f"{next_id}_evidence.jpg"
    img_dest = UPLOADS_DIR / test_filename
    test_img.save(img_dest)
    assert img_dest.exists(), f"Image was not saved to {img_dest}"
    print(f"  [PASS] Simulated image saved to: {img_dest}")

    # 3. Insert Citizen Complaint into SQLite
    print("\n[Step 3] Submitting complaint to SQLite via database controller...")
    new_complaint = {
        "id": next_id,
        "title": "Severe road waterlogging near Indiranagar Metro Station",
        "description": "After heavy rains, water has accumulated up to 1.5 feet blocking the metro entry pedestrian ramp. Commuters are unable to access the station.",
        "category": "Water Supply & Drainage",
        "predicted_category": "Water Supply & Drainage",
        "latitude": 12.9784,
        "longitude": 77.6385,
        "address": "CMH Road, opposite Indiranagar Metro Station Entrance A",
        "image_path": f"uploads/{test_filename}",
        "status": "Submitted",
        "department": "Unassigned",
        "priority_score": 50.0,
        "priority_level": "Medium",
        "priority_factors": "Citizen submitted. Pending authority triage.",
        "is_duplicate": 0,
        "duplicate_of_id": None,
        "cluster_id": -1,
        "action_recommendation": "Pending authority review and dispatch.",
        "citizen_name": "Aakash Mehta",
        "citizen_contact": "9876501234"
    }

    inserted_id = database.insert_complaint(new_complaint)
    assert inserted_id == next_id, f"Inserted ID {inserted_id} does not match {next_id}"
    print(f"  [PASS] Complaint {inserted_id} inserted successfully.")

    # 4. Verify in SQLite Database
    print("\n[Step 4] Verifying complaint retrieval by ID from SQLite...")
    retrieved = database.get_complaint_by_id(next_id)
    assert retrieved is not None, f"Failed to retrieve complaint {next_id}"
    assert retrieved["title"] == new_complaint["title"]
    assert retrieved["category"] == "Water Supply & Drainage"
    assert retrieved["status"] == "Submitted"
    assert retrieved["image_path"] == f"uploads/{test_filename}"
    assert retrieved["citizen_name"] == "Aakash Mehta"
    print(f"  [PASS] Record matches database entry:")
    print(f"         ID: {retrieved['id']}")
    print(f"         Title: {retrieved['title']}")
    print(f"         Category: {retrieved['category']}")
    print(f"         Status: {retrieved['status']}")
    print(f"         Image Path: {retrieved['image_path']}")
    print(f"         Created At: {retrieved['created_at']}")

    # 5. Check Total Count in Database
    print("\n[Step 5] Checking updated total complaints count...")
    all_complaints = database.get_all_complaints()
    print(f"  Total complaints now in database: {len(all_complaints)}")
    assert len(all_complaints) == 41, f"Expected 41 complaints (40 seed + 1 new), got {len(all_complaints)}"
    print("  [PASS] Total count matches expected (41).")

    print("\n" + "=" * 70)
    print("  PHASE 2 BACKEND & INTEGRATION TESTS PASSED! ")
    print("=" * 70)

if __name__ == "__main__":
    run_phase2_tests()

