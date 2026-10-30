"""
views/citizen_portal.py - Citizen Interface for CIVIX AI
Features:
- Dark navy & electric blue theme with modern card-based layout.
- Welcome & introduction banner.
- Complaint submission form (Title, Category, Description, Geo-coords, Image Upload, Contact).
- Image storage in /uploads directory.
- Input validation & unique complaint ID generation.
- Interactive Complaint Status Tracker.
"""

import os
from pathlib import Path
from datetime import datetime
import streamlit as st
from PIL import Image

import database
from ai import analyze_complaint

# Paths
BASE_DIR = Path(__file__).parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Standard Civic Categories
CATEGORIES = [
    "Roads & Infrastructure",
    "Water Supply & Drainage",
    "Electricity & Power",
    "Sanitation & Waste Management",
    "Public Safety"
]

# Quick Location Presets (Bengaluru Metro Area for easy demo testing)
LOCATION_PRESETS = {
    "Select a preset or enter manually...": {"lat": 12.9716, "lng": 77.5946, "address": ""},
    "Koramangala 5th Block (Roads & Infrastructure)": {
        "lat": 12.9352, "lng": 77.6245, "address": "80ft Road, Sony World Junction, Koramangala"
    },
    "Indiranagar 100ft Road (Water & Drainage)": {
        "lat": 12.9719, "lng": 77.6412, "address": "100 Feet Road, near 12th Main, Indiranagar"
    },
    "Whitefield ITPL Road (Electrical & Power)": {
        "lat": 12.9866, "lng": 77.7378, "address": "ITPL Main Road, opposite Gate 2, Whitefield"
    },
    "Jayanagar 4th Block (Sanitation & Waste)": {
        "lat": 12.9298, "lng": 77.5843, "address": "Near 4th Block Market Complex, Jayanagar"
    },
    "Hebbal Flyover (Public Safety)": {
        "lat": 13.0358, "lng": 77.5970, "address": "Hebbal Flyover Approach Road"
    }
}


def inject_custom_css():
    """Injects dark navy, blue, and modern card styling."""
    st.markdown("""
    <style>
        /* Base typography & backgrounds */
        .main {
            background-color: #0b132b;
            color: #ffffff;
        }
        
        /* Hero Card */
        .hero-card {
            background: linear-gradient(135deg, #1c2541 0%, #0b132b 100%);
            border: 1px solid #3a86ff44;
            border-radius: 16px;
            padding: 28px;
            margin-bottom: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
        }
        
        .hero-title {
            font-size: 2.2rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 6px;
            letter-spacing: -0.5px;
        }
        
        .hero-badge {
            background-color: #3a86ff22;
            color: #4cc9f0;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            border: 1px solid #4cc9f055;
            display: inline-block;
            margin-bottom: 12px;
        }
        
        .hero-subtitle {
            font-size: 1.05rem;
            color: #cdd7e6;
            margin-top: 4px;
            line-height: 1.5;
        }

        /* Metric / Feature Pill Cards */
        .feature-card {
            background-color: #1c2541;
            border: 1px solid #2a3b5c;
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }
        .feature-card:hover {
            border-color: #3a86ff;
            transform: translateY(-2px);
        }
        .feature-icon {
            font-size: 1.8rem;
            margin-bottom: 6px;
        }
        .feature-title {
            font-weight: 600;
            color: #ffffff;
            font-size: 0.95rem;
        }
        .feature-desc {
            color: #8fa0bc;
            font-size: 0.8rem;
            margin-top: 4px;
        }

        /* Form Card */
        .content-card {
            background-color: #141f36;
            border: 1px solid #223254;
            border-radius: 14px;
            padding: 24px;
            margin-bottom: 20px;
        }

        /* Success ID Banner */
        .success-box {
            background: linear-gradient(135deg, #0d3b66 0%, #1c2541 100%);
            border: 1.5px solid #00b4d8;
            border-radius: 14px;
            padding: 22px;
            margin-top: 15px;
            margin-bottom: 20px;
            text-align: center;
        }
        .ticket-id {
            font-size: 2rem;
            font-weight: 800;
            color: #4cc9f0;
            letter-spacing: 1.5px;
            margin: 10px 0;
        }

        /* Status Pills */
        .status-pill {
            display: inline-block;
            padding: 4px 14px;
            border-radius: 16px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        .status-submitted { background-color: #ffaa0022; color: #ffbe0b; border: 1px solid #ffaa00; }
        .status-in-progress { background-color: #3a86ff22; color: #4cc9f0; border: 1px solid #3a86ff; }
        .status-resolved { background-color: #38b00022; color: #70e000; border: 1px solid #38b000; }
        .status-critical { background-color: #d9042922; color: #ff4d6d; border: 1px solid #d90429; }
    </style>
    """, unsafe_allow_html=True)


def render_citizen_portal():
    """Main render function for the Citizen Portal."""
    inject_custom_css()

    # =========================================================================
    # 1. WELCOME HERO SECTION
    # =========================================================================
    st.markdown("""
    <div class="hero-card">
        <span class="hero-badge">🏛️ CIVIX AI CITIZEN PORTAL</span>
        <div class="hero-title">From Complaints to Action</div>
        <div class="hero-subtitle">
            Report civic issues in your neighborhood with real-time AI categorization, 
            duplicate detection, priority scoring, and transparent tracking.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3-Pillar Highlights
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">⚡</div>
            <div class="feature-title">Instant AI Triage</div>
            <div class="feature-desc">Natural language categorization & urgency analysis</div>
        </div>
        """, unsafe_allow_html=True)
    with col_f2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📍</div>
            <div class="feature-title">Geo-Spatial Hotspots</div>
            <div class="feature-desc">DBSCAN clustering connects related neighborhood reports</div>
        </div>
        """, unsafe_allow_html=True)
    with col_f3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🛡️</div>
            <div class="feature-title">Transparent Accountability</div>
            <div class="feature-desc">Track resolution milestones by ticket ID 24/7</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    # =========================================================================
    # 2. MAIN TABS (LODGE COMPLAINT vs TRACK STATUS)
    # =========================================================================
    tab_lodge, tab_track, tab_about = st.tabs([
        "📝 Lodge a Complaint",
        "🔍 Track Complaint Status",
        "ℹ️ How It Works"
    ])

    # -------------------------------------------------------------------------
    # TAB 1: LODGE COMPLAINT
    # -------------------------------------------------------------------------
    with tab_lodge:
        st.markdown("### Lodge a Civic Complaint")
        st.caption("Provide details of the civic issue below. Our AI engine will analyze and prioritize your report.")

        with st.form("complaint_submission_form", clear_on_submit=False):
            # Row 1: Title and Category
            col_title, col_cat = st.columns([2, 1])
            with col_title:
                title = st.text_input(
                    "Issue Title *",
                    placeholder="e.g., Deep pothole causing skidding near Sony Signal",
                    help="Provide a concise 1-line summary of the problem."
                )
            with col_cat:
                category = st.selectbox(
                    "Category *",
                    options=CATEGORIES,
                    help="Select the category that best fits the issue."
                )

            # Row 2: Detailed Description
            description = st.text_area(
                "Detailed Description *",
                placeholder="Describe what happened, exact landmark, danger to public safety, and how long the issue has persisted...",
                height=120,
                help="Detailed descriptions help our AI determine urgency and prevent duplicates."
            )

            # Row 3: Location Preset & Coordinates
            st.markdown("##### 📍 Location Details")
            preset_choice = st.selectbox(
                "Quick Bangalore Landmark Preset (Optional)",
                options=list(LOCATION_PRESETS.keys()),
                help="Select a preset to auto-fill coordinates, or type your own coordinates below."
            )

            selected_preset = LOCATION_PRESETS[preset_choice]
            default_lat = selected_preset["lat"]
            default_lng = selected_preset["lng"]
            default_addr = selected_preset["address"]

            col_addr, col_lat, col_lng = st.columns([2, 1, 1])
            with col_addr:
                address = st.text_input(
                    "Address / Landmark *",
                    value=default_addr,
                    placeholder="e.g., 5th Cross Road, near Madhavan Park Gate"
                )
            with col_lat:
                latitude = st.number_input(
                    "Latitude *",
                    value=float(default_lat),
                    format="%.6f",
                    step=0.0001,
                    min_value=-90.0,
                    max_value=90.0
                )
            with col_lng:
                longitude = st.number_input(
                    "Longitude *",
                    value=float(default_lng),
                    format="%.6f",
                    step=0.0001,
                    min_value=-180.0,
                    max_value=180.0
                )

            # Row 4: Image Upload & Citizen Info
            st.markdown("##### 📷 Evidence & Citizen Details")
            col_img, col_citizen = st.columns([1.5, 1])
            with col_img:
                uploaded_image = st.file_uploader(
                    "Upload Photo / Image Evidence (Optional)",
                    type=["jpg", "jpeg", "png"],
                    help="Visual proof helps municipal engineers inspect and verify the issue faster."
                )
                if uploaded_image:
                    st.image(uploaded_image, caption="Uploaded Evidence Preview", width=260)

            with col_citizen:
                citizen_name = st.text_input(
                    "Your Name (Optional)",
                    value="Anonymous Citizen",
                    help="Leave as Anonymous or enter your name."
                )
                citizen_contact = st.text_input(
                    "Contact Number / Email (Optional)",
                    placeholder="e.g., 9876543210",
                    help="For SMS / email progress updates."
                )

            st.write("")
            submit_btn = st.form_submit_button("🚀 Submit Complaint to CIVIX AI", use_container_width=True)

        # Form Submission Logic
        if submit_btn:
            # 1. Validation
            errors = []
            if not title or len(title.strip()) < 5:
                errors.append("Please enter a descriptive Title (at least 5 characters).")
            if not description or len(description.strip()) < 10:
                errors.append("Please enter a detailed Description (at least 10 characters).")
            if not address or len(address.strip()) < 3:
                errors.append("Please enter a valid Address or landmark.")
            if latitude == 0.0 and longitude == 0.0:
                errors.append("Please provide valid geographic latitude and longitude.")

            if errors:
                for err in errors:
                    st.error(f"⚠️ {err}")
            else:
                # 2. Process Image Saving
                saved_image_rel_path = ""
                # Generate new complaint ID upfront
                new_id = database.generate_next_complaint_id()

                if uploaded_image:
                    ext = Path(uploaded_image.name).suffix or ".jpg"
                    safe_filename = f"{new_id}_evidence{ext}"
                    disk_target = UPLOADS_DIR / safe_filename
                    try:
                        with open(disk_target, "wb") as f:
                            f.write(uploaded_image.getbuffer())
                        saved_image_rel_path = f"uploads/{safe_filename}"
                    except Exception as e:
                        st.warning(f"Could not save image file: {e}")

                # 3. Create Complaint Dictionary
                complaint_payload = {
                    "id": new_id,
                    "title": title.strip(),
                    "description": description.strip(),
                    "category": category,
                    "predicted_category": category,  # Initially mapped to category
                    "latitude": float(latitude),
                    "longitude": float(longitude),
                    "address": address.strip(),
                    "image_path": saved_image_rel_path,
                    "status": "Submitted",
                    "department": "Unassigned",
                    "priority_score": 50.0,  # Default neutral score until AI batch triage
                    "priority_level": "Medium",
                    "priority_factors": "Initial citizen submission. Pending authority AI pipeline review.",
                    "is_duplicate": 0,
                    "duplicate_of_id": None,
                    "cluster_id": -1,
                    "action_recommendation": "Complaint logged. Assigned for automated AI verification and dispatch.",
                    "citizen_name": citizen_name.strip() if citizen_name else "Anonymous Citizen",
                    "citizen_contact": citizen_contact.strip() if citizen_contact else "",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                # 4. Insert into SQLite (initial record)
                inserted_id = database.insert_complaint(complaint_payload)

                # 5. Run AI Pipeline automatically
                with st.spinner("🤖 CIVIX AI is analysing your complaint..."):
                    try:
                        all_complaints = database.get_all_complaints()
                        new_record     = database.get_complaint_by_id(inserted_id)
                        ai_results     = analyze_complaint(new_record, all_complaints)
                        # Persist AI-enriched fields back to SQLite
                        database.update_complaint_ai_metadata(inserted_id, {
                            "predicted_category"   : ai_results.get("predicted_category"),
                            "is_duplicate"         : ai_results.get("is_duplicate", 0),
                            "duplicate_of_id"      : ai_results.get("duplicate_of_id"),
                            "cluster_id"           : ai_results.get("cluster_id", -1),
                            "priority_score"       : ai_results.get("priority_score", 50.0),
                            "priority_level"       : ai_results.get("priority_level", "Medium"),
                            "priority_factors"     : ai_results.get("priority_factors", ""),
                            "department"           : ai_results.get("department", "Unassigned"),
                            "action_recommendation": ai_results.get("action_recommendation", ""),
                        })
                    except Exception as ai_err:
                        st.warning(f"AI analysis encountered an issue: {ai_err}. Complaint saved with default values.")
                        ai_results = {}

                # 6. Success Notification & Card
                st.balloons()
                prio_level  = ai_results.get("priority_level", "Medium")
                prio_score  = ai_results.get("priority_score", 50.0)
                pred_cat    = ai_results.get("predicted_category", category)
                dept        = ai_results.get("department", "Unassigned")
                is_dup      = ai_results.get("is_duplicate", 0)
                dup_id      = ai_results.get("duplicate_of_id")

                prio_color  = {"Critical": "#ff4d6d", "High": "#ffbe0b", "Medium": "#4cc9f0", "Low": "#70e000"}.get(prio_level, "#4cc9f0")

                st.markdown(f"""
                <div class="success-box">
                    <div style="font-size: 1.1rem; color: #a0c4ff;">✅ Complaint Registered & AI Analysis Complete!</div>
                    <div class="ticket-id">{inserted_id}</div>
                    <div style="color: #e0e1dd; font-size: 0.95rem;">
                        Keep this unique Complaint ID to track progress, departmental assignment, and resolution milestones.
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # AI Results summary columns
                r1, r2, r3, r4 = st.columns(4)
                r1.metric("🤖 AI Category",   pred_cat)
                r2.metric("⚡ Priority",       f"{prio_level} ({prio_score:.0f}/100)")
                r3.metric("🏢 Assigned To",    dept)
                r4.metric("🔁 Duplicate Flag", f"Yes → {dup_id}" if is_dup else "No")

                if ai_results.get("priority_factors"):
                    with st.expander("📊 View AI Score Breakdown"):
                        st.info(ai_results["priority_factors"])

                if is_dup and dup_id:
                    st.warning(f"⚠️ **Potential Duplicate Detected!** This complaint is similar to **{dup_id}**. It has been flagged for authority review. A separate tracking ID **{inserted_id}** is still assigned.")

                action_text = ai_results.get("action_recommendation", "")
                if action_text:
                    st.success(f"🛠️ **Recommended Action:** {action_text}")

    # -------------------------------------------------------------------------
    # TAB 2: TRACK STATUS
    # -------------------------------------------------------------------------
    with tab_track:
        st.markdown("### 🔍 Track Complaint Status")
        st.caption("Enter your unique Complaint ID (e.g., `CIVIX-1001`) to view its current status and assigned department.")

        col_search, col_btn = st.columns([3, 1])
        with col_search:
            search_id = st.text_input("Enter Complaint ID", placeholder="CIVIX-XXXX", label_visibility="collapsed")
        with col_btn:
            search_clicked = st.button("🔎 Look Up Ticket", use_container_width=True)

        if search_id or search_clicked:
            clean_id = search_id.strip().upper()
            record = database.get_complaint_by_id(clean_id)

            if record:
                st.write("")
                # Status Pill Determination
                status_raw = record["status"]
                pill_class = "status-submitted"
                if status_raw == "In Progress":
                    pill_class = "status-in-progress"
                elif status_raw == "Resolved":
                    pill_class = "status-resolved"
                elif record["priority_level"] == "Critical":
                    pill_class = "status-critical"

                st.markdown(f"""
                <div class="content-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                        <span style="font-size: 1.4rem; font-weight: 700; color: #4cc9f0;">{record['id']}</span>
                        <span class="status-pill {pill_class}">Status: {record['status']}</span>
                    </div>
                    <h3 style="color: #ffffff; margin-top: 0; margin-bottom: 8px;">{record['title']}</h3>
                    <p style="color: #cdd7e6; line-height: 1.5;">{record['description']}</p>
                </div>
                """, unsafe_allow_html=True)

                # Metadata Cards
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("Category", record["category"])
                with c2:
                    st.metric("Priority Level", f"{record['priority_level']} ({record['priority_score']:.0f}/100)")
                with c3:
                    st.metric("Assigned Dept", record["department"] if record["department"] != "Unassigned" else "Pending Triage")
                with c4:
                    st.metric("Registered On", record["created_at"].split()[0])

                # Location & Recommendation
                col_loc, col_rec = st.columns(2)
                with col_loc:
                    st.markdown("##### 📍 Location & Address")
                    st.info(f"**Address:** {record['address']}\n\n**Coordinates:** {record['latitude']:.4f}, {record['longitude']:.4f}")

                with col_rec:
                    st.markdown("##### 🛠️ AI Action / Operational Next Step")
                    rec_text = record.get("action_recommendation") or "Under review by municipal authorities."
                    st.success(f"{rec_text}")

                # Display Evidence Photo if exists
                if record.get("image_path"):
                    full_img_path = BASE_DIR / record["image_path"]
                    if full_img_path.exists():
                        st.markdown("##### 📷 Uploaded Evidence")
                        st.image(str(full_img_path), width=380, caption=f"Evidence for {record['id']}")

            else:
                st.warning(f"No complaint found with ID **{clean_id}**. Please double-check your ID (e.g., `CIVIX-1001`).")

    # -------------------------------------------------------------------------
    # TAB 3: HOW IT WORKS
    # -------------------------------------------------------------------------
    with tab_about:
        st.markdown("""
        ### How CIVIX AI Powers Civic Impact

        CIVIX AI bridges the gap between citizens reporting local urban issues and civic authorities acting on them swiftly.

        #### 🤖 The 5-Stage AI Intelligence Pipeline:
        1. **Automatic Complaint Categorization**: Analyzes free-form complaints using NLP and TF-IDF classifiers to instantly route tickets to the correct municipal department.
        2. **Intelligent Duplicate Detection**: Computes TF-IDF vector cosine similarity and spatial proximity to detect and merge duplicate complaints reported by multiple citizens.
        3. **Explainable Priority Scoring**: Weighs urgency keywords, category safety baselines, and active hotspot density to calculate an interpretable 0–100 urgency score.
        4. **Geographic Hotspot Detection**: Applies Scikit-Learn **DBSCAN** spatial clustering with Haversine distance to flag geographic clusters needing immediate infrastructure intervention.
        5. **Prescriptive Action Recommendations**: Generates Standard Operating Procedures (SOPs), turnaround SLAs, and immediate dispatch directives for municipal authorities.
        """)
