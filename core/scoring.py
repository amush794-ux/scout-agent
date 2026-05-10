from typing import Any, Dict


def calculate_scores(extraction: Dict[str, Any]) -> Dict[str, int]:
    urgency = 0

    pricing_visible = extraction.get("pricing_visible", True)
    if pricing_visible is False:
        urgency += 20

    cta_quality = extraction.get("cta_quality")
    if cta_quality in ("weak", "none"):
        urgency += 25

    social_proof = extraction.get("social_proof")
    social_proof_missing = social_proof is None or (
        isinstance(social_proof, str) and social_proof.strip() == ""
    )
    if social_proof_missing:
        urgency += 25

    blog_active_raw = extraction.get("blog_active", True)
    blog_active = blog_active_raw if isinstance(blog_active_raw, bool) else True
    if blog_active is False:
        urgency += 10

    seo_signals = extraction.get("seo_signals")
    seo_absent = seo_signals == "absent"
    if seo_absent:
        urgency += 20

    missing = extraction.get("missing_elements", [])
    booking_keywords = ("booking", "appointment", "reservation", "schedule")
    booking_gap = isinstance(missing, list) and any(
        k in " ".join(missing).lower() for k in booking_keywords
    )
    if booking_gap:
        urgency += 15

    urgency = min(urgency, 100)

    trust = 100
    if social_proof_missing:
        trust -= 35
    if pricing_visible is False:
        trust -= 20
    if blog_active is False:
        trust -= 10
    if seo_absent:
        trust -= 15

    trust = max(trust, 0)
    return {"urgency_score": urgency, "trust_score": trust}


def score(extraction: Dict[str, Any]) -> Dict[str, int]:
    return calculate_scores(extraction)

