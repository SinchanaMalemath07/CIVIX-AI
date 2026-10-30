"""
views/authority_dashboard.py - Authority Dashboard for CIVIX AI.
Features:
- Secure Role-Based Access Control (Admin, Department Officer, Field Inspector).
- Overview KPI statistics and Plotly charts (Category breakdown, Priority distribution, Status pipeline).
- AI-Prioritized Complaint Triage with full explainability factors.
- Department & Officer reassignment with instant audit logging.
- Status transition & resolution notes management.
- Duplicate detection viewer with similarity percentages and parent-child linking.
- DBSCAN Geographic Hotspots with interactive Folium map visualization.
- Audit history timeline tracking every operational action.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium

import database
from ai.hotspot_detector import detect_hotspots
from ai.duplicate_detector import detect_duplicates

# Paths
BASE_DIR = Path(__file__).parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"

# Civic Departments List
DEPARTMENTS = [
    "Public Works Department",
    "Water Supply & Sewerage Board",
    "Electricity Supply Board",
    "Solid Waste Management Department",
    "Civic Safety & Emergency Response",
    "Parks & Recreation Department",
    "Town Planning & Encroachment",
    "Animal Husbandry & Control",
    "Traffic Police Department",
    "Pollution Control Board"
]

OFFICERS_BY_DEPT = {
    "Public Works Department": ["Er. Vikram Reddy (Chief)", "Er. K. Murthy (Roads)", "Unassigned"],
    "Water Supply & Sewerage Board": ["Er. Ramesh Gowda (Exec)", "Er. S. Rao (Drainage)", "Unassigned"],
    "Electricity Supply Board": ["Er. Anita George (Superintendent)", "Er. V. Nair (Substation)", "Unassigned"],
    "Solid Waste Management Department": ["Dr. Farhan Qureshi (Health)", "S. Iyengar (Sanitation)", "Unassigned"],
    "Civic Safety & Emergency Response": ["Capt. Sanjeev Bakshi", "Inspector K. Nair", "Unassigned"]
}

STATUS_OPTIONS = ["Submitted", "Under Review", "In Progress", "Resolved", "Rejected"]


# ── Styling Helpers ──────────────────────────────────────────────────────────

def inject_authority_css():
    st.markdown("""
    <style>
        .auth-card {
            background-color: #141f36;
            border: 1px solid #223254;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
        }
        .auth-title {
            font-size: 1.15rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 6px;
        }
        .audit-entry {
            border-left: 3px solid #3a86ff;
            padding-left: 12px;
            margin-bottom: 12px;
        }
        .audit-time {
            font-size: 0.78rem;
            color: #8fa0bc;
        }
        .audit-actor {
            font-size: 0.85rem;
            font-weight: 600;
            color: #4cc9f0;
        }
        .audit-detail {
            font-size: 0.88rem;
            color: #e0e1dd;
            margin-top: 2px;
        }
        .badge-critical { background: #d9042933; color: #ff4d6d; border: 1px solid #d90429; padding: 3px 10px; border-radius: 12px; font-weight: 700; font-size: 0.8rem; }
        .badge-high { background: #ffaa0033; color: #ffbe0b; border: 1px solid #ffaa00; padding: 3px 10px; border-radius: 12px; font-weight: 700; font-size: 0.8rem; }
        .badge-medium { background: #3a86ff33; color: #4cc9f0; border: 1px solid #3a86ff; padding: 3px 10px; border-radius: 12px; font-weight: 700; font-size: 0.8rem; }
        .badge-low { background: #38b00033; color: #70e000; border: 1px solid #38b000; padding: 3px 10px; border-radius: 12px; font-weight: 700; font-size: 0.8rem; }
    </style>
    """, unsafe_allow_html=True)


# ── 1. Authentication View ───────────────────────────────────────────────────

def render_login_view():
    """Renders the secure Authority Login portal."""
    st.markdown("""
    <div style="text-align: center; max-width: 520px; margin: 40px auto 20px auto;">
        <h2 style="color: #4cc9f0; font-weight: 800; letter-spacing: 0.5px;">🛡️ CIVIX AI AUTHORITY GATEWAY</h2>
        <p style="color: #cdd7e6; font-size: 0.95rem;">
            Municipal Administration & Civic Incident Command Centre
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_pad_left, col_form, col_pad_right = st.columns([1, 1.8, 1])

    with col_form:
        st.markdown("""
        <div style="background-color: #141f36; border: 1px solid #2a3b5c; border-radius: 14px; padding: 24px;">
            <h4 style="color: #ffffff; margin-top: 0; margin-bottom: 12px;">Authority Sign-In</h4>
            <div style="font-size: 0.85rem; color: #8fa0bc; margin-bottom: 16px;">
                Enter verified municipal credentials to access administrative triage controls.
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("authority_login_form"):
            username = st.text_input("Username", placeholder="e.g., admin or officer_pwd")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            login_submit = st.form_submit_button("🔐 Authenticate & Enter Dashboard", use_container_width=True)

        if login_submit:
            if not username or not password:
                st.error("Please enter both username and password.")
            else:
                user = database.authenticate_authority(username, password)
                if user:
                    st.session_state["auth_user"] = user
                    st.success(f"Welcome, {user['full_name']} ({user['role']})!")
                    st.rerun()
                else:
                    st.error("Invalid credentials. Please verify your municipal username and password.")

        # Demo Credentials Hint for Evaluators
        with st.expander("🔑 Demo Authority Credentials (for Hackathon Evaluation)"):
            st.markdown("""
            | Username | Password | Role | Department Access |
            | :--- | :--- | :--- | :--- |
            | `admin` | `admin123` | **Admin (Commissioner)** | All Departments |
            | `officer_pwd` | `pwd123` | **Department Officer** | Public Works Department |
            | `officer_elec` | `elec123` | **Department Officer** | Electricity Supply Board |
            | `officer_water` | `water123` | **Department Officer** | Water Supply & Sewerage Board |
            | `inspector_field` | `field123` | **Field Inspector** | All Localities |
            """)


# ── 2. Header & User Profile Bar ─────────────────────────────────────────────

def render_authority_header(user: Dict[str, Any]):
    """Renders the top banner with active officer role and logout."""
    col_info, col_logout = st.columns([4, 1])
    with col_info:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
            <span style="font-size: 1.6rem; font-weight: 800; color: #ffffff;">🏛️ Authority Command Center</span>
            <span style="background: #3a86ff22; color: #4cc9f0; border: 1px solid #3a86ff; padding: 2px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 600;">
                {user['role']}
            </span>
        </div>
        <div style="color: #8fa0bc; font-size: 0.88rem;">
            Logged in as <strong>{user['full_name']}</strong> • Department Scope: <strong>{user.get('department', 'All')}</strong>
        </div>
        """, unsafe_allow_html=True)
    with col_logout:
        st.write("")
        if st.button("🚪 Log Out", use_container_width=True):
            del st.session_state["auth_user"]
            st.rerun()
    st.divider()


# ── 3. Overview Statistics & Analytics Tab ───────────────────────────────────

def render_overview_tab(complaints: List[Dict[str, Any]], user: Dict[str, Any]):
    """Renders high-level KPI metrics and interactive Plotly analytics."""
    st.markdown("### 📊 Operational Overview & Civic Intelligence")

    # Metrics Row
    total = len(complaints)
    resolved = sum(1 for c in complaints if c["status"] == "Resolved")
    in_progress = sum(1 for c in complaints if c["status"] == "In Progress")
    submitted = sum(1 for c in complaints if c["status"] == "Submitted")
    critical = sum(1 for c in complaints if c["priority_level"] == "Critical")
    duplicates = sum(1 for c in complaints if c["is_duplicate"] == 1)

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Total Complaints", total)
    m2.metric("Critical Hazards", critical, delta=f"{critical} Urgent", delta_color="inverse")
    m3.metric("In Progress", in_progress)
    m4.metric("Resolved", resolved, delta=f"{resolved}/{total}")
    m5.metric("Pending Review", submitted)
    m6.metric("Duplicates Flagged", duplicates)

    st.write("")

    if not complaints:
        st.info("No complaints found in the database.")
        return

    df = pd.DataFrame(complaints)

    # Analytics Charts
    col_c1, col_c2 = st.columns(2)

    with col_c1:
        st.markdown("##### 🏷️ Complaints by Civic Category")
        cat_counts = df["category"].value_counts().reset_index()
        cat_counts.columns = ["Category", "Count"]
        fig_cat = px.pie(
            cat_counts,
            names="Category",
            values="Count",
            hole=0.45,
            color_discrete_sequence=["#3a86ff", "#00b4d8", "#7209b7", "#4361ee", "#4cc9f0"]
        )
        fig_cat.update_layout(
            paper_bgcolor="#0b132b",
            plot_bgcolor="#0b132b",
            font_color="#e0e1dd",
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=-0.3)
        )
        st.plotly_chart(fig_cat, use_container_width=True)

    with col_c2:
        st.markdown("##### ⚡ Priority Level Distribution")
        prio_order = ["Critical", "High", "Medium", "Low"]
        prio_counts = df["priority_level"].value_counts().reindex(prio_order, fill_value=0).reset_index()
        prio_counts.columns = ["Priority", "Count"]
        colors = {"Critical": "#ff4d6d", "High": "#ffbe0b", "Medium": "#4cc9f0", "Low": "#70e000"}
        fig_prio = px.bar(
            prio_counts,
            x="Priority",
            y="Count",
            color="Priority",
            color_discrete_map=colors,
            text="Count"
        )
        fig_prio.update_layout(
            paper_bgcolor="#0b132b",
            plot_bgcolor="#141f36",
            font_color="#e0e1dd",
            showlegend=False,
            margin=dict(l=20, r=20, t=30, b=20),
            yaxis=dict(gridcolor="#223254")
        )
        st.plotly_chart(fig_prio, use_container_width=True)

    # Status Breakdown & Department Workload
    col_c3, col_c4 = st.columns(2)
    with col_c3:
        st.markdown("##### 🔄 Resolution Status Pipeline")
        status_counts = df["status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        fig_status = px.bar(
            status_counts,
            x="Count",
            y="Status",
            orientation="h",
            color="Status",
            color_discrete_sequence=px.colors.sequential.Blues_r
        )
        fig_status.update_layout(
            paper_bgcolor="#0b132b",
            plot_bgcolor="#141f36",
            font_color="#e0e1dd",
            showlegend=False,
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(gridcolor="#223254")
        )
        st.plotly_chart(fig_status, use_container_width=True)

    with col_c4:
        st.markdown("##### 🏢 Departmental Workload")
        dept_counts = df["department"].value_counts().reset_index()
        dept_counts.columns = ["Department", "Complaints"]
        fig_dept = px.bar(
            dept_counts,
            x="Complaints",
            y="Department",
            orientation="h",
            color_discrete_sequence=["#4cc9f0"]
        )
        fig_dept.update_layout(
            paper_bgcolor="#0b132b",
            plot_bgcolor="#141f36",
            font_color="#e0e1dd",
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(gridcolor="#223254")
        )
        st.plotly_chart(fig_dept, use_container_width=True)


# ── 4. AI Prioritized Management & Triage Tab ────────────────────────────────

def render_triage_tab(complaints: List[Dict[str, Any]], user: Dict[str, Any]):
    """Renders the AI-prioritized complaint queue with filtering, assignment, and status updates."""
    st.markdown("### ⚡ AI-Prioritized Complaint Management")
    st.caption("Complaints are ranked by transparent AI priority score. Filter, reassign departments, and update resolution milestones.")

    # ── Filter Bar ──
    with st.expander("🔍 Filters & Search Options", expanded=True):
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            prio_filter = st.selectbox("Priority Level", ["All", "Critical", "High", "Medium", "Low"])
        with f2:
            status_filter = st.selectbox("Status", ["All", "Submitted", "Under Review", "In Progress", "Resolved", "Rejected"])
        with f3:
            cat_filter = st.selectbox("Category", ["All", "Roads & Infrastructure", "Water Supply & Drainage", "Electricity & Power", "Sanitation & Waste Management", "Public Safety"])
        with f4:
            # Department filter (scoped if role is Department Officer)
            user_dept = user.get("department", "All")
            dept_options = ["All"] + DEPARTMENTS
            if user["role"] == "Department Officer" and user_dept != "All":
                dept_filter = user_dept
                st.info(f"Scoped to: {user_dept}")
            else:
                dept_filter = st.selectbox("Department", dept_options)

        f5, f6 = st.columns([2, 1])
        with f5:
            search_query = st.text_input("Search (ID, Title, Address, or Keyword)", placeholder="e.g., CIVIX-1001, transformer, indiranagar...")
        with f6:
            sort_by = st.selectbox("Sort Order", ["Priority (High to Low)", "Priority (Low to High)", "Newest First", "Oldest First"])

    # Apply Filters
    filtered = complaints
    if prio_filter != "All":
        filtered = [c for c in filtered if c["priority_level"] == prio_filter]
    if status_filter != "All":
        filtered = [c for c in filtered if c["status"] == status_filter]
    if cat_filter != "All":
        filtered = [c for c in filtered if c["category"] == cat_filter]
    if dept_filter != "All":
        filtered = [c for c in filtered if c["department"] == dept_filter]
    if search_query:
        q = search_query.strip().lower()
        filtered = [c for c in filtered if q in c["id"].lower() or q in c["title"].lower() or q in c.get("address", "").lower() or q in c["description"].lower()]

    # Sort
    if sort_by == "Priority (High to Low)":
        filtered.sort(key=lambda x: x.get("priority_score", 0.0), reverse=True)
    elif sort_by == "Priority (Low to High)":
        filtered.sort(key=lambda x: x.get("priority_score", 0.0))
    elif sort_by == "Newest First":
        filtered.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    elif sort_by == "Oldest First":
        filtered.sort(key=lambda x: x.get("created_at", ""))

    st.markdown(f"**Showing {len(filtered)} of {len(complaints)} complaints**")

    if not filtered:
        st.warning("No complaints match the selected filter criteria.")
        return

    # Render Complaint Cards
    for comp in filtered:
        prio_lvl = comp.get("priority_level", "Medium")
        badge_cls = f"badge-{prio_lvl.lower()}"
        status_raw = comp.get("status", "Submitted")

        with st.container():
            st.markdown(f"""
            <div class="auth-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div>
                        <span style="font-size: 1.25rem; font-weight: 700; color: #4cc9f0;">{comp['id']}</span>
                        <span style="color: #8fa0bc; font-size: 0.85rem; margin-left: 8px;">📍 {comp.get('address', 'Location not specified')}</span>
                    </div>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <span class="{badge_cls}">AI Priority: {prio_lvl} ({comp.get('priority_score', 0):.0f}/100)</span>
                        <span style="background: #1c2541; border: 1px solid #3a86ff44; color: #cdd7e6; padding: 3px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 600;">
                            Status: {status_raw}
                        </span>
                    </div>
                </div>
                <div class="auth-title">{comp['title']}</div>
                <div style="color: #cdd7e6; font-size: 0.9rem; line-height: 1.4; margin-bottom: 10px;">{comp['description']}</div>
                <div style="display: flex; gap: 20px; font-size: 0.82rem; color: #8fa0bc; margin-bottom: 6px;">
                    <span>🏷️ <strong>Category:</strong> {comp['category']}</span>
                    <span>🏢 <strong>Department:</strong> {comp.get('department', 'Unassigned')}</span>
                    <span>👤 <strong>Officer:</strong> {comp.get('assigned_officer', 'Unassigned')}</span>
                    <span>📅 <strong>Logged:</strong> {comp.get('created_at', '').split()[0]}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Interactive Detail & Management Drawer
            with st.expander(f"⚙️ Triage & Update Actions for {comp['id']}"):
                col_actions, col_ai = st.columns([1.2, 1])

                with col_actions:
                    st.markdown("##### 📝 Authority Action & Assignment")
                    with st.form(f"update_form_{comp['id']}"):
                        new_st = st.selectbox("Update Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index(status_raw) if status_raw in STATUS_OPTIONS else 0)

                        cur_dept = comp.get("department", "Unassigned")
                        dept_idx = DEPARTMENTS.index(cur_dept) if cur_dept in DEPARTMENTS else 0
                        new_dp = st.selectbox("Assign Department", DEPARTMENTS, index=dept_idx)

                        officer_list = OFFICERS_BY_DEPT.get(new_dp, ["Unassigned"])
                        cur_off = comp.get("assigned_officer", "Unassigned")
                        off_idx = officer_list.index(cur_off) if cur_off in officer_list else 0
                        new_off = st.selectbox("Assign Field Officer", officer_list, index=off_idx)

                        action_notes = st.text_area("Operational Notes / Resolution Remarks", placeholder="e.g., Work crew dispatched; replacement transformer unit delivered.")

                        apply_btn = st.form_submit_button("💾 Save Changes & Log Audit Entry", use_container_width=True)

                    if apply_btn:
                        # Update status and department/officer
                        status_changed = (new_st != status_raw)
                        dept_changed = (new_dp != cur_dept or new_off != cur_off)

                        if dept_changed:
                            database.update_complaint_assignment(comp['id'], new_dp, new_off, updated_by=user['full_name'], notes=action_notes)
                        if status_changed or action_notes:
                            database.update_complaint_resolution(comp['id'], new_st, action_notes=action_notes, updated_by=user['full_name'])

                        st.success(f"Complaint {comp['id']} updated successfully!")
                        st.rerun()

                with col_ai:
                    st.markdown("##### 🤖 Explainable AI Insights")
                    st.info(f"**Priority Breakdown:**\n\n{comp.get('priority_factors', 'No factor breakdown available.')}")
                    st.success(f"**Target Action Recommendation:**\n\n{comp.get('action_recommendation', 'Pending triage recommendation.')}")

                    if comp.get("is_duplicate") == 1:
                        dup_parent = comp.get("duplicate_of_id", "Unknown")
                        st.warning(f"⚠️ **Duplicate Alert:** This complaint is flagged as duplicate of **{dup_parent}**.")

                    if comp.get("image_path"):
                        img_file = BASE_DIR / comp["image_path"]
                        if img_file.exists():
                            st.image(str(img_file), caption=f"Evidence for {comp['id']}", width=240)


# ── 5. Duplicate Detection & Clustering Tab ──────────────────────────────────

def render_duplicates_tab(complaints: List[Dict[str, Any]]):
    """Renders duplicate reports analysis with parent-child links and similarity metrics."""
    st.markdown("### 🔁 Duplicate Complaint Detection & Merging")
    st.caption("Identify redundant citizen reports using TF-IDF cosine similarity and spatial proximity. Prevent duplicated field dispatches.")

    duplicates = [c for c in complaints if c.get("is_duplicate") == 1]
    originals = {c["id"]: c for c in complaints if c.get("is_duplicate") == 0}

    d1, d2, d3 = st.columns(3)
    d1.metric("Flagged Duplicates", len(duplicates))
    d2.metric("Primary Parent Tickets", len(set(c.get("duplicate_of_id") for c in duplicates if c.get("duplicate_of_id"))))
    d3.metric("Estimated Redundant Hours Saved", f"{len(duplicates) * 4} hrs")

    st.write("")

    if not duplicates:
        st.info("No duplicate complaints detected in the current database.")
        return

    st.markdown("#### Duplicate Ticket Relationships")

    for dup in duplicates:
        parent_id = dup.get("duplicate_of_id")
        parent = originals.get(parent_id)

        with st.container():
            st.markdown(f"""
            <div class="auth-card" style="border-left: 4px solid #ffbe0b;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                    <span style="color: #ffbe0b; font-weight: 700; font-size: 1.1rem;">🔁 Duplicate Ticket: {dup['id']}</span>
                    <span style="color: #4cc9f0; font-weight: 600;">Links to Parent: {parent_id or 'Unlinked'}</span>
                </div>
                <div style="color: #ffffff; font-weight: 600; margin-bottom: 4px;">{dup['title']}</div>
                <div style="color: #8fa0bc; font-size: 0.85rem; margin-bottom: 10px;">{dup['description']}</div>
            </div>
            """, unsafe_allow_html=True)

            if parent:
                with st.expander(f"🔎 Compare with Master Ticket {parent_id}"):
                    c_left, c_right = st.columns(2)
                    with c_left:
                        st.markdown(f"**Master Ticket:** `{parent['id']}`")
                        st.markdown(f"**Title:** {parent['title']}")
                        st.markdown(f"**Description:** {parent['description']}")
                        st.markdown(f"**Status:** `{parent['status']}` | **Dept:** `{parent['department']}`")
                    with c_right:
                        st.markdown(f"**Duplicate Report:** `{dup['id']}`")
                        st.markdown(f"**Title:** {dup['title']}")
                        st.markdown(f"**Description:** {dup['description']}")
                        st.markdown(f"**Status:** `{dup['status']}` | **Priority:** `{dup['priority_level']}`")


# ── 6. Geographic Hotspot Detection (DBSCAN + Folium) ─────────────────────────

def render_hotspots_tab(complaints: List[Dict[str, Any]]):
    """Renders DBSCAN geographic clustering on an interactive Folium map."""
    st.markdown("### 📍 Geographic Hotspot Detection (DBSCAN)")
    st.caption("Identifies neighborhood problem clusters using Haversine-metric density clustering (DBSCAN).")

    # Run DBSCAN
    hotspot_results = detect_hotspots(complaints)
    clusters = hotspot_results.get("cluster_summaries", [])
    total_clusters = hotspot_results.get("total_clusters", 0)
    total_noise = hotspot_results.get("total_noise", 0)

    # Metrics
    h1, h2, h3 = st.columns(3)
    h1.metric("Identified Hotspots", total_clusters)
    h2.metric("Hotspot Incidents", len(hotspot_results.get("hotspot_complaint_ids", [])))
    h3.metric("Isolated Outliers", total_noise)

    st.write("")

    # Map Rendering
    # Default map centre: Bengaluru
    map_center = [12.9716, 77.5946]
    if clusters:
        map_center = [clusters[0]["centroid_lat"], clusters[0]["centroid_lon"]]

    civix_map = folium.Map(
        location=map_center,
        zoom_start=12,
        tiles="CartoDB dark_matter"
    )

    # Add Cluster Boundary Circles
    cluster_colors = ["#ff0055", "#ffaa00", "#00d4ff", "#7928ca", "#00df8f"]
    for idx, cl in enumerate(clusters):
        c_color = cluster_colors[idx % len(cluster_colors)]
        folium.Circle(
            location=[cl["centroid_lat"], cl["centroid_lon"]],
            radius=600,  # 600 meter radius
            color=c_color,
            fill=True,
            fill_color=c_color,
            fill_opacity=0.25,
            popup=f"<b>Hotspot Cluster {cl['cluster_id']}</b><br>Incidents: {cl['complaint_count']}<br>Dominant: {cl['dominant_category']}<br>Severity: {cl['severity_level']}"
        ).add_to(civix_map)

    # Add Complaint Markers
    for comp in complaints:
        lat = comp.get("latitude")
        lng = comp.get("longitude")
        if lat is None or lng is None or (lat == 0.0 and lng == 0.0):
            continue

        prio = comp.get("priority_level", "Medium")
        marker_color = "red" if prio == "Critical" else "orange" if prio == "High" else "blue" if prio == "Medium" else "green"

        popup_html = f"""
        <div style="font-family: sans-serif; font-size: 12px; width: 220px;">
            <b style="color: #1d4ed8;">{comp['id']}</b> ({comp['status']})<br>
            <b>{comp['title'][:50]}...</b><br>
            <span style="color: #666;">Category: {comp['category']}</span><br>
            <span style="color: #c00;">Priority: {prio} ({comp.get('priority_score', 0):.0f})</span>
        </div>
        """

        folium.CircleMarker(
            location=[lat, lng],
            radius=6,
            color=marker_color,
            fill=True,
            fill_color=marker_color,
            fill_opacity=0.85,
            popup=folium.Popup(popup_html, max_width=250)
        ).add_to(civix_map)

    # Display Map
    st_folium(civix_map, width=1000, height=480)

    # Hotspot Cluster Summaries Table
    if clusters:
        st.markdown("#### 📋 Active Neighborhood Hotspots")
        summary_rows = []
        for cl in clusters:
            summary_rows.append({
                "Cluster ID": f"Cluster #{cl['cluster_id']}",
                "Incidents": cl["complaint_count"],
                "Dominant Domain": cl["dominant_category"],
                "Max Severity": cl["severity_level"],
                "Coordinates (Lat, Lng)": f"{cl['centroid_lat']:.4f}, {cl['centroid_lon']:.4f}",
                "Affected Ticket IDs": ", ".join(cl["complaint_ids"])
            })
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)


# ── 7. Audit History & Resolution Timeline Tab ───────────────────────────────

def render_history_tab(complaints: List[Dict[str, Any]]):
    """Renders operational audit logs and resolution history for any complaint."""
    st.markdown("### 📜 Complaint Action & Resolution History")
    st.caption("Immutable audit log of all administrative assignments, AI categorizations, and resolution notes.")

    selected_id = st.selectbox(
        "Select Complaint to Inspect Audit Trail",
        options=[c["id"] for c in complaints],
        format_func=lambda x: f"{x} - {next((c['title'][:50] for c in complaints if c['id'] == x), '')}"
    )

    if selected_id:
        comp = next((c for c in complaints if c["id"] == selected_id), None)
        history = database.get_action_history(selected_id)

        if comp:
            st.markdown(f"""
            <div class="auth-card">
                <span style="font-size: 1.2rem; font-weight: 700; color: #4cc9f0;">{comp['id']}</span>
                <span style="margin-left: 10px; color: #ffffff; font-weight: 600;">{comp['title']}</span>
                <div style="font-size: 0.85rem; color: #8fa0bc; margin-top: 4px;">
                    Category: <strong>{comp['category']}</strong> • Current Status: <strong>{comp['status']}</strong> • Department: <strong>{comp['department']}</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)

        if not history:
            st.info(f"No manual action logs recorded yet for {selected_id}. Changes made in the Triage tab will appear here.")
        else:
            st.markdown("#### Operational Timeline")
            for entry in history:
                st.markdown(f"""
                <div class="audit-entry">
                    <div style="display: flex; justify-content: space-between;">
                        <span class="audit-actor">{entry['action_type']} — by {entry['performed_by']}</span>
                        <span class="audit-time">⏱️ {entry['created_at']}</span>
                    </div>
                    <div class="audit-detail">{entry['details']}</div>
                </div>
                """, unsafe_allow_html=True)


# ── Main Render Entry Point ──────────────────────────────────────────────────

def render_authority_dashboard():
    """Main render controller for the Authority Dashboard."""
    inject_authority_css()

    # RBAC Check: Ensure user is logged in
    auth_user = st.session_state.get("auth_user")
    if not auth_user:
        render_login_view()
        return

    # Render Header & Logout
    render_authority_header(auth_user)

    # Fetch all complaints
    complaints = database.get_all_complaints()

    # Main Tabs
    tab_overview, tab_triage, tab_hotspots, tab_dups, tab_history = st.tabs([
        "📊 Dashboard Overview",
        "⚡ AI Complaint Triage",
        "📍 Geographic Hotspots (DBSCAN)",
        "🔁 Duplicate Detection",
        "📜 Action & Audit History"
    ])

    with tab_overview:
        render_overview_tab(complaints, auth_user)

    with tab_triage:
        render_triage_tab(complaints, auth_user)

    with tab_hotspots:
        render_hotspots_tab(complaints)

    with tab_dups:
        render_duplicates_tab(complaints)

    with tab_history:
        render_history_tab(complaints)
