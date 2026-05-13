import sqlite3
from typing import Dict, List

from database.db import get_lead_draft_state, update_lead_draft_status

_DB_PATH = "data/agency.db"


def get_pending_reviews() -> List[Dict]:
    """Query leads where draft_status = 'draft_reviewing'.
    
    Returns list of dicts with url, draft_status, revision_count.
    Returns [] if database query fails.
    """
    try:
        conn = sqlite3.connect(_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT url, draft_status, revision_count FROM leads WHERE draft_status = ?",
            ("draft_reviewing",)
        )
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "url": row[0],
                "draft_status": row[1],
                "revision_count": row[2],
            }
            for row in rows
        ]
    except Exception:
        return []


def approve_draft(url: str) -> bool:
    """Approve a draft after state validation.
    
    Returns False if:
    - Lead state not found
    - Current status is not 'draft_reviewing'
    - Update fails
    """
    try:
        state = get_lead_draft_state(url)
        if not state:
            return False
        if state.get("draft_status") != "draft_reviewing":
            return False
        return update_lead_draft_status(url, "draft_approved")
    except Exception:
        return False


def reject_draft(url: str, feedback: str = None) -> bool:
    """Reject a draft after state validation, optionally storing feedback.
    
    Returns False if:
    - Lead state not found
    - Current status is not 'draft_reviewing'
    - Update fails
    """
    try:
        state = get_lead_draft_state(url)
        if not state:
            return False
        if state.get("draft_status") != "draft_reviewing":
            return False
        return update_lead_draft_status(url, "draft_rejected", rejection_reason=feedback)
    except Exception:
        return False


if __name__ == "__main__":
    from database.db import init_db, insert_lead

    print("Running review_pipeline tests...")

    # Initialize database and create test lead
    init_db()
    test_url = "https://review-test.example.com"
    insert_lead(url=test_url, business_name="Review Test Lead")

    # Set to draft_reviewing
    update_lead_draft_status(test_url, "draft_reviewing")

    # Test get_pending_reviews
    pending = get_pending_reviews()
    print(f"Pending reviews: {pending}")

    # Test approve_draft
    approve_result = approve_draft(test_url)
    print(f"Approve draft result: {approve_result}")

    # Reset to draft_reviewing for reject test
    update_lead_draft_status(test_url, "draft_reviewing")

    # Test reject_draft
    reject_result = reject_draft(test_url, "test feedback")
    print(f"Reject draft result: {reject_result}")

    print("Review pipeline tests completed!")
