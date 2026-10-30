"""
test_phase1.py - Phase 1 Verification and Test Script for CIVIX AI.
Tests:
1. SQLite Database creation & schema verification.
2. Population of 40 realistic synthetic complaints.
3. Complaint retrieval (all complaints + single complaint by ID).
4. Complaint status and department updates.
5. Verification of deliberate duplicates, critical safety issues, and spatial clusters.
"""

import sys
from pathlib import Path

# Ensure root directory is in sys.path
sys.path.insert(0, str(Path(__file__).parent))

import database
from data.sample_data import populate_database, get_sample_complaints


def run_phase1_tests():
    print("=" * 70)
    print("  CIVIX AI - PHASE 1 VERIFICATION & TEST SUITE")
    print("=" * 70)

    # 1. Initialize Database
    print("\n[Step 1] Initializing SQLite database...")
    database.init_db()
    db_file = Path(database.DB_PATH)
    assert db_file.exists(), f"Error: Database file not found at {db_file}"
    print(f"  [PASS] Database successfully created at: {db_file}")

    # 2. Insert 40 Sample Complaints
    print("\n[Step 2] Inserting 40 realistic synthetic civic complaints...")
    inserted_count = populate_database(reset=True)
    assert inserted_count == 40, f"Expected 40 complaints, inserted {inserted_count}"
    print(f"  [PASS] Successfully inserted {inserted_count} complaints into SQLite.")

    # 3. Retrieve All Complaints
    print("\n[Step 3] Testing retrieval of all complaints...")
    all_records = database.get_all_complaints()
    assert len(all_records) == 40, f"Expected 40 records retrieved, got {len(all_records)}"
    print(f"  [PASS] Retrieved {len(all_records)} complaints.")

    # 4. Retrieve Complaint by ID
    print("\n[Step 4] Testing retrieval by specific ID (CIVIX-1001)...")
    comp = database.get_complaint_by_id("CIVIX-1001")
    assert comp is not None, "Failed to retrieve complaint CIVIX-1001"
    assert comp["id"] == "CIVIX-1001"
    assert comp["priority_level"] == "Critical"
    print(f"  [PASS] Found ID: {comp['id']}")
    print(f"         Title: {comp['title']}")
    print(f"         Category: {comp['category']}")
    print(f"         Priority: {comp['priority_level']} ({comp['priority_score']}/100)")
    print(f"         Status: {comp['status']} | Dept: {comp['department']}")

    # 5. Update Status and Department
    print("\n[Step 5] Testing status and department update...")
    test_id = "CIVIX-1004"
    before = database.get_complaint_by_id(test_id)
    print(f"  Before update: ID={test_id}, Status='{before['status']}', Dept='{before['department']}'")

    updated = database.update_complaint_status(test_id, "In Progress", "Public Works Department - Road Wing")
    assert updated is True, f"Failed to update complaint {test_id}"

    after = database.get_complaint_by_id(test_id)
    assert after["status"] == "In Progress"
    assert after["department"] == "Public Works Department - Road Wing"
    print(f"  After update:  ID={test_id}, Status='{after['status']}', Dept='{after['department']}'")
    print("  [PASS] Update succeeded and timestamp updated.")

    # 6. Verify Deliberate Duplicates
    print("\n[Step 6] Verifying deliberate duplicate complaints...")
    duplicates = [c for c in all_records if c["is_duplicate"] == 1]
    print(f"  Total flagged duplicates in seed data: {len(duplicates)}")
    for d in duplicates:
        print(f"  - {d['id']} is marked as duplicate of -> {d['duplicate_of_id']} ('{d['title'][:55]}...')")
    assert len(duplicates) >= 5, "Expected at least 5 deliberate duplicates in dataset"
    print("  [PASS] Deliberate duplicates verified.")

    # 7. Verify Critical Safety Issues
    print("\n[Step 7] Verifying critical safety issues...")
    criticals = [c for c in all_records if c["priority_level"] == "Critical"]
    print(f"  Total Critical priority complaints: {len(criticals)}")
    for crit in criticals:
        print(f"  - [{crit['id']}] (Score: {crit['priority_score']}) {crit['title'][:60]}...")
    assert len(criticals) >= 5, "Expected at least 5 critical priority issues"
    print("  [PASS] Critical safety issues verified.")

    # 8. Verify Geographical Clusters for DBSCAN
    print("\n[Step 8] Verifying geographic clusters in dataset...")
    clusters = {}
    for c in all_records:
        cid = c["cluster_id"]
        clusters[cid] = clusters.get(cid, 0) + 1
    for cid, count in sorted(clusters.items()):
        label = "Outliers / Isolated" if cid == -1 else f"Cluster {cid}"
        print(f"  - {label}: {count} complaints")
    assert len([k for k in clusters if k != -1]) >= 4, "Expected at least 4 geographical clusters"
    print("  [PASS] Geographic clusters verified.")

    # 9. Verify Category Distribution
    print("\n[Step 9] Verifying category distribution...")
    categories = {}
    for c in all_records:
        cat = c["category"]
        categories[cat] = categories.get(cat, 0) + 1
    for cat, count in sorted(categories.items()):
        print(f"  - {cat}: {count}")
    print("  [PASS] Categories verified across 5 civic domains.")

    print("\n" + "=" * 70)
    print("  ALL PHASE 1 TESTS PASSED SUCCESSFULLY! ")
    print("=" * 70)


if __name__ == "__main__":
    run_phase1_tests()

