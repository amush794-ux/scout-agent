import json
import os
import re
from typing import Any, Dict, List
from urllib.parse import urljoin, urlparse

import requests
import datetime
import sqlite3
from dotenv import load_dotenv

from agents.scout import run_scout, call_openai, parse_json_response
from core.scoring import calculate_scores
from core.packet_validation import validate_handoff_packet
from agents.email_composer import generate_email_draft
from database.db import init_db, insert_lead, save_scout_result


load_dotenv()

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
FIRECRAWL_BASE_URL = "https://api.firecrawl.dev/v1"
MAX_SUBPAGES = 5


def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")


def firecrawl_scrape(url: str) -> Dict[str, Any]:
    if not FIRECRAWL_API_KEY:
        raise RuntimeError("Missing FIRECRAWL_API_KEY in .env")

    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"url": url, "formats": ["markdown"]}

    response = requests.post(
        f"{FIRECRAWL_BASE_URL}/scrape", headers=headers, json=payload, timeout=60
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"Firecrawl scrape failed ({response.status_code}): {response.text[:500]}"
        )

    body = response.json()
    data = body.get("data") or {}
    markdown = data.get("markdown") or ""
    return {"url": url, "markdown": markdown}


def extract_internal_links(base_url: str, markdown: str) -> List[str]:
    base_domain = urlparse(base_url).netloc
    candidates = re.findall(r"\[[^\]]+\]\((https?://[^)]+|/[^)]+)\)", markdown)
    resolved_links: List[str] = []
    seen = set()

    for link in candidates:
        absolute = urljoin(base_url, link.strip())
        parsed = urlparse(absolute)
        normalized = normalize_url(absolute)
        if parsed.netloc != base_domain:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        resolved_links.append(normalized)

    return resolved_links


def crawl_site(start_url: str, max_subpages: int = MAX_SUBPAGES) -> List[Dict[str, Any]]:
    pages: List[Dict[str, Any]] = []

    main_page = firecrawl_scrape(start_url)
    pages.append(main_page)

    links = extract_internal_links(start_url, main_page["markdown"])
    subpage_links = [u for u in links if u != normalize_url(start_url)][:max_subpages]

    for link in subpage_links:
        try:
            pages.append(firecrawl_scrape(link))
        except Exception:
            # Keep pipeline resilient: skip only failed subpages.
            continue

    return pages


def remove_noise_lines(text: str) -> str:
    noise_patterns = [
        r"cookie",
        r"privacy policy",
        r"terms of service",
        r"all rights reserved",
        r"legal",
        r"disclaimer",
        r"navigation",
        r"menu",
        r"subscribe to our newsletter",
    ]
    keep_signals = [
        r"^#",
        r"contact",
        r"email",
        r"phone",
        r"book a call",
        r"get started",
        r"request a demo",
        r"pricing",
        r"testimonial",
        r"case study",
        r"blog",
    ]

    cleaned_lines: List[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        lower = line.lower()
        is_noise = any(re.search(p, lower) for p in noise_patterns)
        is_keep_signal = any(re.search(p, line.lower()) for p in keep_signals)

        if is_noise and not is_keep_signal:
            continue
        if len(line) < 3:
            continue
        cleaned_lines.append(line)

    # Remove frequent repeated lines (common header/footer fragments).
    frequency: Dict[str, int] = {}
    for line in cleaned_lines:
        frequency[line] = frequency.get(line, 0) + 1

    deduped = [line for line in cleaned_lines if frequency[line] < 3]
    return "\n".join(deduped)


def preprocess_pages(pages: List[Dict[str, Any]]) -> str:
    combined = []
    for page in pages:
        section = f"URL: {page['url']}\n{page.get('markdown', '')}"
        combined.append(remove_noise_lines(section))
    return "\n\n---\n\n".join(combined)


def save_to_database(url: str, extraction: Dict[str, Any], analysis: Dict[str, Any], packet: Dict[str, Any]) -> None:
    import sqlite3
    import datetime
    conn = sqlite3.connect("prospects.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prospects (
            url TEXT PRIMARY KEY,
            timestamp TEXT,
            pass1_json TEXT,
            pass2_json TEXT,
            handoff_packet TEXT,
            urgency_score INTEGER,
            schema_version TEXT
        )
    """)
    cursor.execute("""
        INSERT INTO prospects (url, timestamp, pass1_json, pass2_json, handoff_packet, urgency_score, schema_version)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
            timestamp=excluded.timestamp,
            pass1_json=excluded.pass1_json,
            pass2_json=excluded.pass2_json,
            handoff_packet=excluded.handoff_packet,
            urgency_score=excluded.urgency_score,
            schema_version=excluded.schema_version
    """, (
        url,
        datetime.datetime.utcnow().isoformat(),
        json.dumps(extraction, ensure_ascii=False),
        json.dumps(analysis, ensure_ascii=False),
        json.dumps(packet, ensure_ascii=False),
        packet.get("urgency_score", 0),
        "1.0"
    ))
    conn.commit()
    conn.close()


def pass_3_compress(extraction_json: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
    import datetime
    scores = calculate_scores(extraction_json)
    system = (
        "You are a data compression engine for AI agents. "
        "Output strict JSON only. No prose. No markdown. No extra keys. "
        "Every field must be commercially actionable. "
        "If uncertain, use the string 'unknown'."
    )
    prompt = f"""
Compress this intelligence into a strict agent handoff packet.
Return ONLY valid JSON with exactly these keys:
- company_name (string)
- url (string)
- vertical (string)
- core_offer (string)
- target_customer (string)
- top_pain_points (list, max 3 short signals, no full sentences)
- confirmed_weaknesses (list, max 3 short signals, no full sentences)
- missing_assets (list, max 3 short signals, no full sentences)
- highest_value_opportunity (string, max 15 words)
- best_service_fit (string, max 10 words)
- buying_signals (list, max 3 short signals)
- urgency_score (integer 0-100)
- trust_score (integer 0-100)
- decision_maker_guess (string)
- personalization_hooks (list, max 3 specific observable details from site only)
- confidence_flags (object with business_identity, target_customer, weaknesses, outreach_angle)
- risk_notes (array of risk considerations)
- do_not_say (array of phrases to avoid)
- schema_version (string, always "1.0")
Rules:
- No full sentences unless the field requires it.
- No marketing language.
- No generic advice.
- No repeated information across fields.
- personalization_hooks must reference specific observable details from the site, not recommendations.
- urgency_score and trust_score must be estimated from evidence only.
- If a field has no evidence, use "unknown" or empty list.
Extraction JSON:
{json.dumps(extraction_json, ensure_ascii=False)}
Analysis JSON:
{json.dumps(analysis, ensure_ascii=False)}
"""
    output = call_openai(prompt=prompt, system=system)
    packet = parse_json_response(output)
    packet["urgency_score"] = scores["urgency_score"]
    packet["trust_score"] = scores["trust_score"]
    
    # Add missing schema fields
    packet["url"] = extraction_json.get("_url", "")
    packet["confidence_flags"] = {
        "business_identity": "medium",
        "target_customer": "medium", 
        "weaknesses": "medium",
        "outreach_angle": "medium"
    }
    packet["risk_notes"] = [
        "uncertain target customer",
        "weak evidence for pain point",
        "avoid overclaiming results",
        "unclear decision maker"
    ]
    packet["do_not_say"] = [
        "guaranteed results",
        "claims about revenue improvement",
        "assumptions not supported by Scout data"
    ]
    required_keys = {
        "company_name", "url", "vertical", "core_offer", "target_customer",
        "top_pain_points", "confirmed_weaknesses", "missing_assets",
        "highest_value_opportunity", "best_service_fit", "buying_signals",
        "urgency_score", "trust_score", "decision_maker_guess",
        "personalization_hooks", "confidence_flags", "risk_notes", "do_not_say",
        "schema_version"
    }
    if not required_keys.issubset(set(packet.keys())):
        raise ValueError("Pass 3 packet is missing required keys.")
    import datetime
    packet["metadata"] = {
        "url": extraction_json.get("_url", "unknown"),
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "schema_version": "1.0"
    }
    
    # Hard-default language to Romanian
    packet["language"] = "ro"
    
    # Validate packet and add results to metadata
    is_valid_packet, packet_validation_errors = validate_handoff_packet(packet)
    packet["metadata"]["packet_validation"] = {
        "valid": is_valid_packet,
        "errors": packet_validation_errors
    }
    
    return packet


def run_pipeline(url: str) -> dict:
    if not is_valid_url(url):
        raise ValueError("Please enter a valid URL (including http/https).")
    pages = crawl_site(url, MAX_SUBPAGES)
    if not pages:
        raise RuntimeError("No pages were scraped.")
    cleaned_text = preprocess_pages(pages)
    scout_result = run_scout(cleaned_text)
    extraction = scout_result["extraction"]
    analysis = scout_result["analysis"]
    extraction["_url"] = url
    
    packet = pass_3_compress(extraction, analysis)
    save_to_database(url, extraction, analysis, packet)
    
    # Save to new database
    try:
        init_db()
        lead_id = insert_lead(
            url=url,
            business_name=extraction.get("company_name", ""),
            industry=extraction.get("business_type", ""),
            source="scout_agent"
        )
        save_scout_result(
            lead_id=lead_id,
            url=url,
            scout_json={
                "extraction": extraction,
                "analysis": analysis,
                "packet": packet
            }
        )
    except Exception as exc:
        # Database failure should not break Scout run
        pass
    
    # Generate email draft using Agent 2
    email_result = generate_email_draft(packet)
    
    return {
        "extraction": extraction,
        "analysis": analysis,
        "packet": packet,
        "email_draft": email_result,
    }

