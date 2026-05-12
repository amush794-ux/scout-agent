import json
import os
from typing import Dict, List
import sqlite3
from datetime import datetime, timezone


def init_db(db_path: str = "data/agency.db") -> None:
    """Initialize database with required tables."""
    # Create data folder if missing
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create leads table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            business_name TEXT,
            industry TEXT,
            location TEXT,
            source TEXT,
            status TEXT NOT NULL DEFAULT 'new',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    # Create scout_results table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scout_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            url TEXT NOT NULL,
            scout_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(lead_id) REFERENCES leads(id)
        )
    """)
    
    # Add review state columns to leads table if they don't exist
    cursor.execute("PRAGMA table_info(leads)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    
    review_columns = [
        ("draft_status", "TEXT DEFAULT 'draft_pending'"),
        ("revision_count", "INTEGER DEFAULT 0"),
        ("latest_email_draft", "TEXT"),
        ("draft_generated_at", "TEXT"),
        ("approved_at", "TEXT"),
        ("rejected_at", "TEXT"),
        ("rejection_reason", "TEXT")
    ]
    
    for column_name, column_def in review_columns:
        if column_name not in existing_columns:
            cursor.execute(f"ALTER TABLE leads ADD COLUMN {column_name} {column_def}")
    
    conn.commit()
    conn.close()


def insert_lead(
    url: str,
    business_name: str = "",
    industry: str = "",
    location: str = "",
    source: str = "",
    db_path: str = "data/agency.db"
) -> int:
    """Insert a lead if URL does not exist, return existing lead ID if URL already exists."""
    init_db(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if URL already exists
    cursor.execute("SELECT id FROM leads WHERE url = ?", (url,))
    existing = cursor.fetchone()
    
    if existing:
        lead_id = existing[0]
        conn.close()
        return lead_id
    
    # Insert new lead
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        INSERT INTO leads (url, business_name, industry, location, source, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (url, business_name, industry, location, source, now, now))
    
    lead_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return lead_id


def update_lead_status(
    lead_id: int,
    status: str,
    db_path: str = "data/agency.db"
) -> None:
    """Update lead status with validation."""
    valid_statuses = {"new", "analyzed", "draft_ready", "approved", "rejected", "sent", "failed"}
    
    if status not in valid_statuses:
        raise ValueError(f"Invalid status: {status}. Must be one of: {valid_statuses}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    now = datetime.now(timezone.utc).isoformat()
    cursor.execute("""
        UPDATE leads SET status = ?, updated_at = ? WHERE id = ?
    """, (status, now, lead_id))
    
    conn.commit()
    conn.close()


def save_scout_result(
    lead_id: int,
    url: str,
    scout_json: dict,
    db_path: str = "data/agency.db"
) -> int:
    """Save scout result and update lead status."""
    init_db(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    now = datetime.now(timezone.utc).isoformat()
    scout_json_text = json.dumps(scout_json, ensure_ascii=False)
    
    # Insert scout result
    cursor.execute("""
        INSERT INTO scout_results (lead_id, url, scout_json, created_at)
        VALUES (?, ?, ?, ?)
    """, (lead_id, url, scout_json_text, now))
    
    scout_result_id = cursor.lastrowid
    
    # Update lead status to analyzed using same connection to avoid database lock
    cursor.execute("""
        UPDATE leads SET status = ?, updated_at = ? WHERE id = ?
    """, ("analyzed", now, lead_id))
    
    conn.commit()
    conn.close()
    
    return scout_result_id


def fetch_leads_by_status(
    status: str,
    db_path: str = "data/agency.db"
) -> List[Dict]:
    """Fetch leads by status with validation."""
    valid_statuses = {"new", "analyzed", "draft_ready", "approved", "rejected", "sent", "failed"}
    
    if status not in valid_statuses:
        raise ValueError(f"Invalid status: {status}. Must be one of: {valid_statuses}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, url, business_name, industry, location, source, status, created_at, updated_at
        FROM leads WHERE status = ?
        ORDER BY created_at DESC
    """, (status,))
    
    columns = ["id", "url", "business_name", "industry", "location", "source", "status", "created_at", "updated_at"]
    results = []
    
    for row in cursor.fetchall():
        results.append(dict(zip(columns, row)))
    
    conn.close()
    return results


def fetch_scout_results_for_lead(
    lead_id: int,
    db_path: str = "data/agency.db"
) -> List[Dict]:
    """Fetch all scout results for a specific lead."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, lead_id, url, scout_json, created_at
        FROM scout_results WHERE lead_id = ?
        ORDER BY created_at DESC
    """, (lead_id,))
    
    columns = ["id", "lead_id", "url", "scout_json", "created_at"]
    results = []
    
    for row in cursor.fetchall():
        result = dict(zip(columns, row))
        # Parse JSON back to dict
        result["scout_json"] = json.loads(result["scout_json"])
        results.append(result)
    
    conn.close()
    return results


if __name__ == "__main__":
    # Test block
    print("Running database tests...")
    
    # Initialize database
    init_db()
    
    # Insert test lead
    test_lead_id = insert_lead(
        url="https://example.com",
        business_name="Test Business",
        industry="technology",
        location="US",
        source="manual"
    )
    print(f"Inserted lead with ID: {test_lead_id}")
    
    # Save test scout result
    test_scout_data = {
        "extraction": {"company_name": "Test Company"},
        "analysis": {"1_business_overview": []},
        "packet": {"company_name": "Test Company"}
    }
    
    scout_result_id = save_scout_result(
        lead_id=test_lead_id,
        url="https://example.com",
        scout_json=test_scout_data
    )
    print(f"Saved scout result with ID: {scout_result_id}")
    
    # Fetch analyzed leads
    analyzed_leads = fetch_leads_by_status("analyzed")
    print(f"Found {len(analyzed_leads)} analyzed leads:")
    for lead in analyzed_leads:
        print(f"  - {lead['business_name']} ({lead['url']})")
    
    print("Database tests completed successfully!")