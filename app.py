"""
app.py - Main Streamlit Entry Point for CIVIX AI
Connects the Citizen Portal and Authority Dashboard with professional dark theme styling.
"""

import streamlit as st
import sys
from pathlib import Path

# Add civic_ai root directory to Python path
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

import database
from views.citizen_portal import render_citizen_portal
from views.authority_dashboard import render_authority_dashboard

# Set wide layout and custom browser title
st.set_page_config(
    page_title="CIVIX AI - Civic Issue Management System",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply global dark navy and blue styling
st.markdown("""
<style>
    /* Dark Navy Main Background */
    .stApp {
        background-color: #0b132b;
        color: #ffffff;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0d1b2a;
        border-right: 1px solid #1c2541;
    }
    section[data-testid="stSidebar"] * {
        color: #e0e1dd !important;
    }
    
    /* Streamlit Card & Container Tweaks */
    div[data-testid="stVerticalBlock"] > div[style*="background"] {
        background-color: #1c2541 !important;
        border: 1px solid #2a3b5c;
        border-radius: 12px;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #1d4ed8 0%, #3b82f6 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.55rem 1.2rem !important;
        box-shadow: 0 4px 14px rgba(59, 130, 246, 0.35) !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #2563eb 0%, #60a5fa 100%) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.5) !important;
    }
    
    /* Inputs & Selectboxes */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div,
    .stNumberInput > div > div > input {
        background-color: #141f36 !important;
        color: #ffffff !important;
        border: 1px solid #2a3b5c !important;
        border-radius: 8px !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25) !important;
    }
    
    /* Metric Cards */
    div[data-testid="stMetricValue"] {
        color: #4cc9f0 !important;
        font-weight: 700 !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #8fa0bc !important;
    }
</style>
""", unsafe_allow_html=True)


def main():
    # Ensure database is initialized
    database.init_db()

    # Sidebar Header
    st.sidebar.markdown("""
    <div style="text-align: center; padding: 12px 0 20px 0;">
        <h2 style="color: #4cc9f0; margin-bottom: 2px; font-weight: 800; letter-spacing: 1px;">CIVIX AI</h2>
        <span style="font-size: 0.75rem; color: #8fa0bc; text-transform: uppercase; letter-spacing: 1.5px; border: 1px solid #3a86ff44; padding: 2px 8px; border-radius: 10px;">
            Civic Tech Hackathon 2026
        </span>
    </div>
    """, unsafe_allow_html=True)

    # Navigation Selection
    nav_option = st.sidebar.radio(
        "Navigation",
        options=["🏛️ Citizen Portal", "🛡️ Authority Dashboard"],
        index=0,
        help="Switch between citizen reporting and administrative triage."
    )

    st.sidebar.divider()

    # System Status in Sidebar
    all_complaints = database.get_all_complaints()
    resolved_count = sum(1 for c in all_complaints if c["status"] == "Resolved")
    critical_count = sum(1 for c in all_complaints if c["priority_level"] == "Critical")

    st.sidebar.markdown(f"""
    <div style="background-color: #141f36; border: 1px solid #2a3b5c; border-radius: 10px; padding: 14px; margin-bottom: 15px;">
        <div style="font-size: 0.85rem; color: #8fa0bc; margin-bottom: 8px; font-weight: 600;">LIVE SYSTEM STATS</div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
            <span style="color: #cdd7e6; font-size: 0.85rem;">Total Complaints:</span>
            <strong style="color: #4cc9f0;">{len(all_complaints)}</strong>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
            <span style="color: #cdd7e6; font-size: 0.85rem;">Resolved Issues:</span>
            <strong style="color: #70e000;">{resolved_count}</strong>
        </div>
        <div style="display: flex; justify-content: space-between;">
            <span style="color: #cdd7e6; font-size: 0.85rem;">Critical Hazards:</span>
            <strong style="color: #ff4d6d;">{critical_count}</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("""
    <div style="font-size: 0.75rem; color: #5c6b84; text-align: center; margin-top: 30px;">
        CIVIX AI System • SQLite + Scikit-learn + Streamlit
    </div>
    """, unsafe_allow_html=True)

    # Route based on navigation
    if nav_option == "🏛️ Citizen Portal":
        render_citizen_portal()
    else:
        render_authority_dashboard()


if __name__ == "__main__":
    main()
