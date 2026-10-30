"""
database.py - SQLite Database Management for CIVIX AI
Handles connection, table creation, insertion, retrieval, and status updates.
"""

import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Database file location inside the civic_ai directory
DB_PATH = Path(__file__).parent / "civix.db"


def hash_password(password: str) -> str:
    """Computes SHA-256 hash for secure credential storage."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_db_connection() -> sqlite3.Connection:
    """Creates and returns a SQLite connection with dict-like row access."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initializes the database schema if tables do not already exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS complaints (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        predicted_category TEXT,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        address TEXT,
        image_path TEXT,
        status TEXT DEFAULT 'Submitted',
        department TEXT DEFAULT 'Unassigned',
        assigned_officer TEXT DEFAULT 'Unassigned',
        priority_score REAL DEFAULT 0.0,
        priority_level TEXT DEFAULT 'Medium',
        priority_factors TEXT,
        is_duplicate INTEGER DEFAULT 0,
        duplicate_of_id TEXT,
        cluster_id INTEGER DEFAULT -1,
        action_recommendation TEXT,
        citizen_name TEXT DEFAULT 'Anonymous',
        citizen_contact TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # Ensure assigned_officer column exists for upgraded databases
    cursor.execute("PRAGMA table_info(complaints);")
    columns = [col["name"] for col in cursor.fetchall()]
    if "assigned_officer" not in columns:
        cursor.execute("ALTER TABLE complaints ADD COLUMN assigned_officer TEXT DEFAULT 'Unassigned';")

    # Audit Trail / Action History Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS action_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id TEXT NOT NULL,
        action_type TEXT NOT NULL,
        performed_by TEXT NOT NULL,
        details TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (complaint_id) REFERENCES complaints(id)
    );
    """)

    # Authority Users & RBAC Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS authority_users (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL,
        department TEXT DEFAULT 'All',
        created_at TEXT NOT NULL
    );
    """)

    # Create helpful indexes for fast lookup during dashboard queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON complaints(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON complaints(category);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_priority ON complaints(priority_level);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cluster ON complaints(cluster_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_complaint ON action_history(complaint_id);")

    # Seed default authority staff accounts if not present
    cursor.execute("SELECT COUNT(*) as count FROM authority_users;")
    user_count = cursor.fetchone()["count"]
    if user_count == 0:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        default_users = [
            ("admin", hash_password("admin123"), "Dr. Rajesh Sharma (Commissioner)", "Admin", "All", now_str),
            ("officer_pwd", hash_password("pwd123"), "Er. Vikram Reddy (Chief Engineer)", "Department Officer", "Public Works Department", now_str),
            ("officer_elec", hash_password("elec123"), "Er. Anita George (Superintendent)", "Department Officer", "Electricity Supply Board", now_str),
            ("officer_water", hash_password("water123"), "Er. Ramesh Gowda (Exec Engineer)", "Department Officer", "Water Supply & Sewerage Board", now_str),
            ("inspector_field", hash_password("field123"), "Karthik Nair (Field Inspector)", "Field Inspector", "All", now_str)
        ]
        cursor.executemany("""
        INSERT INTO authority_users (username, password_hash, full_name, role, department, created_at)
        VALUES (?, ?, ?, ?, ?, ?);
        """, default_users)

    conn.commit()
    conn.close()
    print(f"[DB] Initialized database at: {DB_PATH}")


def generate_next_complaint_id() -> str:
    """Generates the next sequential complaint ID, e.g., CIVIX-1001."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM complaints ORDER BY rowid DESC LIMIT 1;")
    last_row = cursor.fetchone()
    conn.close()

    if not last_row:
        return "CIVIX-1001"

    last_id = last_row["id"]
    try:
        num_part = int(last_id.split("-")[-1])
        return f"CIVIX-{num_part + 1}"
    except (ValueError, IndexError):
        return f"CIVIX-{datetime.now().strftime('%m%d%H%M%S')}"


def insert_complaint(complaint: Dict[str, Any]) -> str:
    """
    Inserts a new civic complaint into the database.
    Returns the assigned complaint ID.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    complaint_id = complaint.get("id") or generate_next_complaint_id()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO complaints (
        id, title, description, category, predicted_category,
        latitude, longitude, address, image_path, status,
        department, assigned_officer, priority_score, priority_level, priority_factors,
        is_duplicate, duplicate_of_id, cluster_id, action_recommendation,
        citizen_name, citizen_contact, created_at, updated_at
    ) VALUES (
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?
    );
    """, (
        complaint_id,
        complaint.get("title", "Untitled Complaint"),
        complaint.get("description", ""),
        complaint.get("category", "Uncategorized"),
        complaint.get("predicted_category", None),
        float(complaint.get("latitude", 0.0)),
        float(complaint.get("longitude", 0.0)),
        complaint.get("address", ""),
        complaint.get("image_path", ""),
        complaint.get("status", "Submitted"),
        complaint.get("department", "Unassigned"),
        complaint.get("assigned_officer", "Unassigned"),
        float(complaint.get("priority_score", 0.0)),
        complaint.get("priority_level", "Medium"),
        complaint.get("priority_factors", ""),
        int(complaint.get("is_duplicate", 0)),
        complaint.get("duplicate_of_id", None),
        int(complaint.get("cluster_id", -1)),
        complaint.get("action_recommendation", ""),
        complaint.get("citizen_name", "Anonymous"),
        complaint.get("citizen_contact", ""),
        complaint.get("created_at", now_str),
        complaint.get("updated_at", now_str)
    ))

    conn.commit()
    conn.close()
    return complaint_id


def get_all_complaints() -> List[Dict[str, Any]]:
    """Retrieves all complaints from the database ordered by creation date (newest first)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM complaints ORDER BY created_at DESC;")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_complaint_by_id(complaint_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single complaint by its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM complaints WHERE id = ?;", (complaint_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_complaint_status(complaint_id: str, new_status: str, department: Optional[str] = None) -> bool:
    """
    Updates the status (and optionally department) of a complaint.
    Returns True if update succeeded, False if complaint ID was not found.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if department:
        cursor.execute("""
        UPDATE complaints
        SET status = ?, department = ?, updated_at = ?
        WHERE id = ?;
        """, (new_status, department, now_str, complaint_id))
    else:
        cursor.execute("""
        UPDATE complaints
        SET status = ?, updated_at = ?
        WHERE id = ?;
        """, (new_status, now_str, complaint_id))

    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0


def update_complaint_ai_metadata(complaint_id: str, ai_data: Dict[str, Any]) -> bool:
    """
    Updates AI-calculated fields (priority, cluster_id, duplicate flags, recommendations).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    fields = []
    values = []
    allowed_keys = [
        "predicted_category", "priority_score", "priority_level",
        "priority_factors", "is_duplicate", "duplicate_of_id",
        "cluster_id", "action_recommendation", "department", "assigned_officer"
    ]

    for key in allowed_keys:
        if key in ai_data:
            fields.append(f"{key} = ?")
            values.append(ai_data[key])

    if not fields:
        conn.close()
        return False

    fields.append("updated_at = ?")
    values.append(now_str)
    values.append(complaint_id)

    query = f"UPDATE complaints SET {', '.join(fields)} WHERE id = ?;"
    cursor.execute(query, tuple(values))
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0


# ── Action History / Audit Trail Functions ───────────────────────────────────

def log_action_history(complaint_id: str, action_type: str, performed_by: str, details: str) -> int:
    """
    Records an entry in the complaint action audit log.
    Returns the log entry ID.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO action_history (complaint_id, action_type, performed_by, details, created_at)
    VALUES (?, ?, ?, ?, ?);
    """, (complaint_id, action_type, performed_by, details, now_str))

    entry_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return entry_id


def get_action_history(complaint_id: str) -> List[Dict[str, Any]]:
    """Retrieves all action history entries for a specific complaint ordered newest first."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM action_history
    WHERE complaint_id = ?
    ORDER BY id DESC;
    """, (complaint_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Authority Assignment & Resolution Functions ──────────────────────────────

def update_complaint_assignment(
    complaint_id: str,
    department: str,
    assigned_officer: str,
    updated_by: str = "Authority",
    notes: str = ""
) -> bool:
    """
    Updates the assigned department and officer for a complaint, and logs the action.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    UPDATE complaints
    SET department = ?, assigned_officer = ?, updated_at = ?
    WHERE id = ?;
    """, (department, assigned_officer, now_str, complaint_id))

    rows = cursor.rowcount
    conn.commit()
    conn.close()

    if rows > 0:
        detail_msg = f"Reassigned to {department} | Officer: {assigned_officer}"
        if notes:
            detail_msg += f" | Notes: {notes}"
        log_action_history(complaint_id, "Assignment Update", updated_by, detail_msg)
        return True
    return False


def update_complaint_resolution(
    complaint_id: str,
    new_status: str,
    action_notes: str = "",
    updated_by: str = "Authority"
) -> bool:
    """
    Updates complaint status with resolution/action notes and logs to audit trail.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    UPDATE complaints
    SET status = ?, updated_at = ?
    WHERE id = ?;
    """, (new_status, now_str, complaint_id))

    rows = cursor.rowcount
    conn.commit()
    conn.close()

    if rows > 0:
        detail_msg = f"Status changed to '{new_status}'"
        if action_notes:
            detail_msg += f" | Action notes: {action_notes}"
        log_action_history(complaint_id, "Status Transition", updated_by, detail_msg)
        return True
    return False


# ── Authority Authentication & Users ─────────────────────────────────────────

def authenticate_authority(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Validates authority user credentials against hashed password.
    Returns user dict with role and department if valid, else None.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    pwd_hash = hash_password(password)

    cursor.execute("""
    SELECT username, full_name, role, department
    FROM authority_users
    WHERE username = ? AND password_hash = ?;
    """, (username.strip().lower(), pwd_hash))

    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_authority_users() -> List[Dict[str, Any]]:
    """Retrieves all registered authority user accounts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, full_name, role, department, created_at FROM authority_users;")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def reset_db() -> None:
    """Drops existing complaints, action_history, authority_users and re-initializes clean schema."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS complaints;")
    cursor.execute("DROP TABLE IF EXISTS action_history;")
    cursor.execute("DROP TABLE IF EXISTS authority_users;")
    conn.commit()
    conn.close()
    init_db()
    print("[DB] Database reset complete.")


if __name__ == "__main__":
    print("Testing database.py independently...")
    reset_db()
    test_id = insert_complaint({
        "title": "Broken street light on 5th Avenue",
        "description": "The street light in front of house 42 has been completely off for three days.",
        "category": "Electricity & Power",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "address": "5th Avenue, Ward 12",
        "priority_score": 65.0,
        "priority_level": "Medium"
    })
    print(f"Inserted test complaint ID: {test_id}")
    complaint = get_complaint_by_id(test_id)
    print(f"Retrieved complaint: {complaint['title']} - Status: {complaint['status']}")
    update_complaint_status(test_id, "In Progress", "Electrical Maintenance Board")
    updated = get_complaint_by_id(test_id)
    print(f"After update: Status = {updated['status']}, Dept = {updated['department']}")
    print("Self-test completed successfully!")

