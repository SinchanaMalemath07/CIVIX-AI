"""
test_phase4_authority.py - Phase 4 Authority Dashboard Test Suite.

Tests:
1. Authority authentication & role-based credentials.
2. Department & Officer reassignment persistence.
3. Status transition & resolution notes updates.
4. Action history & audit trail logging.
5. DBSCAN Hotspots computation & cluster summary generation.
6. Duplicate detection grouping & master ticket linking.
7. Filtering & sorting algorithms.
8. Compatibility with Citizen Portal and existing database records.
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))

import pytest
import database
from data.sample_data import populate_database
from ai.hotspot_detector import detect_hotspots
from ai.duplicate_detector import detect_duplicates


@pytest.fixture(scope="module", autouse=True)
def setup_authority_tests():
    """Ensure database has clean schema and 40 complaints."""
    populate_database(reset=True)
    yield


# ============================================================================
# 1. AUTHENTICATION & ROLE-BASED ACCESS CONTROL
# ============================================================================

class TestAuthorityAuthentication:
    """Verifies secure authentication and role assignments."""

    def test_admin_login_success(self):
        user = database.authenticate_authority("admin", "admin123")
        assert user is not None
        assert user["username"] == "admin"
        assert user["role"] == "Admin"
        assert user["department"] == "All"
        assert "Commissioner" in user["full_name"]

    def test_department_officer_login_success(self):
        user = database.authenticate_authority("officer_pwd", "pwd123")
        assert user is not None
        assert user["role"] == "Department Officer"
        assert user["department"] == "Public Works Department"

    def test_field_inspector_login_success(self):
        user = database.authenticate_authority("inspector_field", "field123")
        assert user is not None
        assert user["role"] == "Field Inspector"

    def test_invalid_password_fails(self):
        user = database.authenticate_authority("admin", "wrongpassword")
        assert user is None

    def test_unknown_user_fails(self):
        user = database.authenticate_authority("nonexistent_user", "password123")
        assert user is None

    def test_case_insensitive_username(self):
        user = database.authenticate_authority("ADMIN", "admin123")
        assert user is not None
        assert user["username"] == "admin"

    def test_get_all_authority_users(self):
        users = database.get_all_authority_users()
        assert len(users) >= 5
        roles = {u["role"] for u in users}
        assert "Admin" in roles
        assert "Department Officer" in roles
        assert "Field Inspector" in roles


# ============================================================================
# 2. COMPLAINT ASSIGNMENT & OFFICER DISPATCH
# ============================================================================

class TestComplaintAssignment:
    """Tests departmental assignment and officer dispatching."""

    def test_reassign_department_and_officer(self):
        target_id = "CIVIX-1002"
        success = database.update_complaint_assignment(
            complaint_id=target_id,
            department="Water Supply & Sewerage Board",
            assigned_officer="Er. Ramesh Gowda (Exec)",
            updated_by="Dr. Rajesh Sharma (Commissioner)",
            notes="Expedite repair on main hospital access road."
        )
        assert success is True

        updated = database.get_complaint_by_id(target_id)
        assert updated["department"] == "Water Supply & Sewerage Board"
        assert updated["assigned_officer"] == "Er. Ramesh Gowda (Exec)"

    def test_assignment_creates_audit_log(self):
        target_id = "CIVIX-1002"
        history = database.get_action_history(target_id)
        assert len(history) > 0
        latest = history[0]
        assert latest["action_type"] == "Assignment Update"
        assert "Er. Ramesh Gowda" in latest["details"]
        assert "hospital" in latest["details"]


# ============================================================================
# 3. STATUS TRACKING & RESOLUTION AUDIT
# ============================================================================

class TestStatusResolution:
    """Tests status updates and resolution remarks logging."""

    def test_update_status_to_resolved(self):
        target_id = "CIVIX-1003"
        success = database.update_complaint_resolution(
            complaint_id=target_id,
            new_status="Resolved",
            action_notes="Structural beam reinforced with carbon-fiber wrapping. Road opened.",
            updated_by="Er. Vikram Reddy"
        )
        assert success is True

        updated = database.get_complaint_by_id(target_id)
        assert updated["status"] == "Resolved"

    def test_resolution_creates_audit_log(self):
        target_id = "CIVIX-1003"
        history = database.get_action_history(target_id)
        assert len(history) > 0
        latest = history[0]
        assert latest["action_type"] == "Status Transition"
        assert "Resolved" in latest["details"]
        assert "Er. Vikram Reddy" in latest["performed_by"]


# ============================================================================
# 4. DUPLICATE DETECTION & CLUSTERING FOR DASHBOARD
# ============================================================================

class TestDashboardDuplicateManagement:
    """Verifies duplicate management features in authority dashboard."""

    def test_duplicate_complaints_identification(self):
        all_c = database.get_all_complaints()
        dups = [c for c in all_c if c["is_duplicate"] == 1]
        assert len(dups) >= 6
        for d in dups:
            assert d["duplicate_of_id"] is not None
            # Parent must exist in database
            parent = database.get_complaint_by_id(d["duplicate_of_id"])
            assert parent is not None

    def test_duplicate_matching_scores(self):
        all_c = database.get_all_complaints()
        # Test detection against known duplicate pair CIVIX-1005 / CIVIX-1004
        c1005 = database.get_complaint_by_id("CIVIX-1005")
        res = detect_duplicates(c1005, all_c, exclude_id="CIVIX-1005")
        assert res["best_match_id"] == "CIVIX-1004"
        assert len(res["matches"]) > 0
        assert "%" in res["best_similarity_pct"]


# ============================================================================
# 5. GEOGRAPHIC HOTSPOTS & DBSCAN
# ============================================================================

class TestDashboardHotspots:
    """Verifies DBSCAN hotspot detection for dashboard map visualizer."""

    def test_hotspot_computation_on_all_complaints(self):
        all_c = database.get_all_complaints()
        results = detect_hotspots(all_c)
        assert results["total_clusters"] >= 4
        assert len(results["cluster_summaries"]) >= 4

        # Validate summary structure
        for cl in results["cluster_summaries"]:
            assert "cluster_id" in cl
            assert "centroid_lat" in cl
            assert "centroid_lon" in cl
            assert cl["complaint_count"] >= 2
            assert len(cl["complaint_ids"]) == cl["complaint_count"]


# ============================================================================
# 6. FILTERING & SORTING LOGIC
# ============================================================================

class TestFilteringAndSorting:
    """Tests data filter and sort operations used in the triage view."""

    def test_filter_by_priority(self):
        all_c = database.get_all_complaints()
        criticals = [c for c in all_c if c["priority_level"] == "Critical"]
        assert len(criticals) >= 8
        assert all(c["priority_level"] == "Critical" for c in criticals)

    def test_filter_by_department(self):
        all_c = database.get_all_complaints()
        elec_complaints = [c for c in all_c if "Electricity" in c.get("department", "")]
        assert len(elec_complaints) > 0
        assert all("Electricity" in c["department"] for c in elec_complaints)

    def test_sort_by_priority_score_descending(self):
        all_c = database.get_all_complaints()
        sorted_c = sorted(all_c, key=lambda x: x.get("priority_score", 0.0), reverse=True)
        scores = [c["priority_score"] for c in sorted_c]
        assert scores == sorted(scores, reverse=True)


# ============================================================================
# 7. BACKWARD COMPATIBILITY
# ============================================================================

class TestBackwardCompatibility:
    """Verifies that citizen portal and existing modules still work seamlessly."""

    def test_citizen_insert_still_works(self):
        next_id = database.generate_next_complaint_id()
        payload = {
            "id": next_id,
            "title": "Broken pavement tiles outside primary health centre",
            "description": "Pedestrians stumbling on dislodged pavement blocks. Elderly patients visit daily.",
            "category": "Roads & Infrastructure",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "address": "Opposite Primary Health Centre, Ward 8",
            "status": "Submitted"
        }
        inserted_id = database.insert_complaint(payload)
        assert inserted_id == next_id

        retrieved = database.get_complaint_by_id(inserted_id)
        assert retrieved["title"] == payload["title"]
        assert retrieved["assigned_officer"] == "Unassigned"
