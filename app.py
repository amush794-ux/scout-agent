import json
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv

from core.pipeline import run_pipeline


load_dotenv()

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o"

FIRECRAWL_BASE_URL = "https://api.firecrawl.dev/v1"
MAX_SUBPAGES = 5

TIER_COLORS = {
    "CONFIRMED WEAKNESS": "#d32f2f",
    "ABSENCE DETECTED": "#f57c00",
    "INFERENCE ONLY": "#1976d2",
}


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


def parse_json_response(text: str) -> Dict[str, Any]:
    raw = text.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        fenced_match = re.search(r"```json\s*(\{.*?\})\s*```", raw, flags=re.S)
        if fenced_match:
            return json.loads(fenced_match.group(1))
    raise ValueError("Malformed JSON returned by Claude.")


def call_openai(prompt: str, system: str) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("Missing OPENAI_API_KEY in .env")
    client = OpenAI(api_key=OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=3000,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content.strip()


def pass_1_extract(cleaned_text: str) -> Dict[str, Any]:
    def coerce_str_list(raw: Any) -> List[str]:
        if raw is None:
            return []
        if isinstance(raw, str):
            s = raw.strip()
            if s.lower() in ("[]", "{}", "none", "unknown", ""):
                return []
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    raw = parsed
                else:
                    return [s] if s else []
            except (json.JSONDecodeError, TypeError):
                return [s] if s else []
        if not isinstance(raw, list):
            return []
        out: List[str] = []
        for item in raw:
            if item is None:
                continue
            t = str(item).strip()
            if t and t.lower() not in ("none", "unknown"):
                out.append(t)
        return sorted(set(out), key=lambda x: (x.lower(), x))

    def coerce_bool(raw: Any, default: bool = True) -> bool:
        if isinstance(raw, bool):
            return raw
        if raw is None:
            return default
        if isinstance(raw, str):
            s = raw.strip().lower()
            if s in ("true", "1", "yes"):
                return True
            if s in ("false", "0", "no"):
                return False
            if s in ("none", "unknown", ""):
                return default
        return default

    def coerce_business_type(raw: Any) -> str:
        allowed = frozenset(
            {"dental_imaging", "dental_clinic", "healthcare_general", "unknown"}
        )
        if raw is None:
            return "unknown"
        s = str(raw).strip().lower().replace(" ", "_").replace("-", "_")
        if s in allowed:
            return s
        return "unknown"

    def coerce_seo_signals(raw: Any) -> str:
        allowed = frozenset({"present", "absent", "unknown"})
        if raw is None:
            return "unknown"
        s = str(raw).strip().lower()
        if s in allowed:
            return s
        return "unknown"

    def coerce_blog_frequency(raw: Any) -> str:
        allowed = frozenset({"active", "inactive", "unknown"})
        if raw is None:
            return "unknown"
        s = str(raw).strip().lower()
        if s in allowed:
            return s
        return "unknown"

    def coerce_cta_quality(raw: Any) -> str:
        allowed = frozenset({"strong", "weak", "none", "unknown"})
        if raw is None:
            return "unknown"
        s = str(raw).strip().lower()
        if s in allowed:
            return s
        return "unknown"

    def coerce_social_proof(raw: Any) -> Optional[bool]:
        if raw is None:
            return None
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            s = raw.strip().lower()
            if s in ("true", "1", "yes"):
                return True
            if s in ("false", "0", "no"):
                return False
            if s in ("null", "none", "unknown", ""):
                return None
        return None

    def coerce_nonenum_str(raw: Any) -> str:
        if raw is None:
            return "unknown"
        s = str(raw).strip()
        if not s or s.lower() in ("none", "unknown"):
            return "unknown"
        return s

    def strip_unknown_from_list(items: List[str]) -> List[str]:
        return [
            x.strip()
            for x in items
            if x and str(x).strip().lower() not in ("unknown", "none", "n/a", "")
        ]

    def audience_is_unclear(signals: List[str]) -> bool:
        if not signals:
            return True
        vague = frozenset(
            {
                "unknown",
                "general public",
                "everyone",
                "clients",
                "customers",
                "users",
                "people",
                "public",
            }
        )
        if all(s.strip().lower() in vague for s in signals):
            return True
        if all(len(s.strip()) <= 2 for s in signals):
            return True
        return False

    def infer_target_audience(text: str) -> str:
        t = text.lower()
        patient_markers = (
            "patient",
            "patients",
            "your smile",
            "family dentistry",
            "dental care",
            "teeth",
            "oral health",
            "visit our clinic",
            "book your appointment",
        )
        prof_markers = (
            "referring",
            "physicians",
            "clinicians",
            "practitioners",
            "healthcare providers",
            "for practices",
            "b2b",
            "wholesale",
            "medical professionals",
        )
        has_patients = any(m in t for m in patient_markers)
        has_prof = any(m in t for m in prof_markers)
        if has_patients and has_prof:
            return "mixed"
        if has_patients:
            return "patients"
        if has_prof:
            return "healthcare professionals"
        if "dentist" in t or "dental office" in t or "dental clinic" in t:
            return "patients"
        if "clinic" in t or "hospital" in t or "medical center" in t:
            return "patients"
        return "unknown"

    def detect_buying_signals(text: str) -> List[str]:
        t = text.lower()
        found: List[str] = []
        if any(
            p in t
            for p in (
                "book appointment",
                "book online",
                "schedule appointment",
                "schedule online",
                "request appointment",
                "make an appointment",
                "book your visit",
                "online booking",
                "book a visit",
                "book now",
            )
        ) and any(
            p in t
            for p in ("appointment", "book", "schedule", "visit")
        ):
            found.append("appointment booking available")
        if any(
            p in t
            for p in (
                "contact us",
                "get in touch",
                "call us",
                "email us",
                "reach us",
                "contact our",
                "phone:",
                "tel:",
                "telephone",
                "get in contact",
            )
        ):
            found.append("contact CTA present")
        if any(
            p in t
            for p in (
                "inquiry form",
                "request information",
                "service inquiry",
                "contact form",
                "submit your",
                "request a consultation",
                "send us a message",
            )
        ) or ("form" in t and "submit" in t):
            found.append("service inquiry form present")
        if any(
            p in t
            for p in (
                "book now",
                "schedule now",
                "get started",
                "request a demo",
                "start today",
                "talk to us",
                "speak to",
                "get your",
            )
        ):
            found.append("active engagement CTA")
        order = (
            "appointment booking available",
            "contact CTA present",
            "service inquiry form present",
            "active engagement CTA",
        )
        return [s for s in order if s in found]

    def refine_missing_assets(
        base: List[str],
        pricing_visible: bool,
        social_proof: Optional[bool],
        blog_active: bool,
        cta_primary: str,
        cta_quality: str,
    ) -> List[str]:
        abstract_markers = (
            "marketing channel",
            "marketing channels",
            "marketing strategy",
            "strategy",
            "consulting",
            "digital presence",
            "brand awareness",
            "growth strategy",
        )
        out: List[str] = []
        seen_lower: set = set()
        for item in base:
            low = item.strip().lower()
            if not low or low == "unknown":
                continue
            if any(a in low for a in abstract_markers):
                continue
            if low not in seen_lower:
                seen_lower.add(low)
                out.append(item.strip())

        def add(label: str) -> None:
            low = label.lower()
            if low not in seen_lower:
                seen_lower.add(low)
                out.append(label)

        if pricing_visible is False:
            add("pricing information")
        if social_proof is None or social_proof is False:
            add("social proof")
        if blog_active is False:
            add("blog content")
        no_cta = cta_quality == "none" or (
            cta_primary == "unknown" and cta_quality in ("none", "unknown")
        )
        if no_cta:
            add("call to action optimization")
        return sorted(out, key=lambda x: (x.lower(), x))

    system = (
        "You are a strict schema extraction engine. Output a single JSON object only. "
        "No markdown, no commentary. Use ONLY the allowed enum values listed in the user message. "
        "If something is not clearly visible in the text, use 'unknown', null, or [] as instructed — "
        "except list fields must omit vague entries; missing_elements should name concrete, observable gaps only."
    )
    prompt = f"""
Return ONLY valid JSON (no markdown) with exactly these keys:
- company_name
- business_type
- primary_service
- target_audience_signals
- pricing_visible
- blog_active
- blog_frequency_signal
- social_proof
- cta_primary
- cta_quality
- seo_signals
- technology_signals
- channels_detected
- missing_elements

STRICT ENUMS (use only these tokens; lowercase as shown):
- business_type: one of "dental_imaging", "dental_clinic", "healthcare_general", "unknown"
- seo_signals: one of "present", "absent", "unknown"
- blog_frequency_signal: one of "active", "inactive", "unknown"
- cta_quality: one of "strong", "weak", "none", "unknown"
- social_proof: JSON boolean true, JSON boolean false, or JSON null only — never a string

TYPES:
- pricing_visible: boolean
- blog_active: boolean
- target_audience_signals: JSON array of short strings; [] if none
- missing_elements: JSON array of short strings; [] if none
- technology_signals: JSON array of short strings; [] if none
- channels_detected: JSON array of short strings; [] if none

OTHER FIELDS:
- company_name: string; "unknown" if the legal/trade name is not clearly visible
- primary_service: one short factual phrase or "unknown"
- cta_primary: short factual label or "unknown"

RULES:
- Use only what is explicitly supported by the website text. Do not infer hidden strategy or off-site facts.
- Do not output "moderate", descriptive sentences, or narrative — only the allowed enum tokens and short factual strings or lists.
- If unclear: use "unknown" for string enums, null for social_proof, [] for lists.
- target_audience_signals: short factual phrases from the page only; use [] if none (downstream may infer a single controlled label).
- missing_elements: only concrete, on-page absences (e.g. pricing section, testimonials); never abstract consulting gaps.

Website text:
{cleaned_text[:140000]}
"""
    output = call_openai(prompt=prompt, system=system)
    data = parse_json_response(output)
    required_keys = {
        "company_name",
        "business_type",
        "primary_service",
        "target_audience_signals",
        "pricing_visible",
        "blog_active",
        "blog_frequency_signal",
        "social_proof",
        "cta_primary",
        "cta_quality",
        "seo_signals",
        "technology_signals",
        "channels_detected",
        "missing_elements",
    }
    if not required_keys.issubset(set(data.keys())):
        raise ValueError("Pass 1 JSON is missing required keys.")

    out: Dict[str, Any] = {
        "company_name": coerce_nonenum_str(data.get("company_name")),
        "business_type": coerce_business_type(data.get("business_type")),
        "primary_service": coerce_nonenum_str(data.get("primary_service")),
        "target_audience_signals": strip_unknown_from_list(
            coerce_str_list(data.get("target_audience_signals"))
        ),
        "pricing_visible": coerce_bool(data.get("pricing_visible"), True),
        "blog_active": coerce_bool(data.get("blog_active"), True),
        "blog_frequency_signal": coerce_blog_frequency(data.get("blog_frequency_signal")),
        "social_proof": coerce_social_proof(data.get("social_proof")),
        "cta_primary": coerce_nonenum_str(data.get("cta_primary")),
        "cta_quality": coerce_cta_quality(data.get("cta_quality")),
        "seo_signals": coerce_seo_signals(data.get("seo_signals")),
        "technology_signals": strip_unknown_from_list(
            coerce_str_list(data.get("technology_signals"))
        ),
        "channels_detected": strip_unknown_from_list(
            coerce_str_list(data.get("channels_detected"))
        ),
        "missing_elements": strip_unknown_from_list(
            coerce_str_list(data.get("missing_elements"))
        ),
    }

    if audience_is_unclear(out["target_audience_signals"]):
        out["target_audience_signals"] = [infer_target_audience(cleaned_text)]

    out["buying_signals"] = detect_buying_signals(cleaned_text)

    out["missing_elements"] = refine_missing_assets(
        out["missing_elements"],
        out["pricing_visible"],
        out["social_proof"],
        out["blog_active"],
        out["cta_primary"],
        out["cta_quality"],
    )
    return out


def pass_2_analyze(extraction_json: Dict[str, Any]) -> Dict[str, Any]:
    system = (
        "You are a strict GTM analyst. Every claim must be evidence-grounded. "
        "Never treat absence as weakness unless explicitly proven by evidence."
    )
    prompt = f"""
Given this extraction JSON, produce strategic analysis in JSON only.

Required output shape (exact top-level keys):
1_business_overview
2_target_audience
3_current_marketing_presence
4_weak_points_and_gaps
5_opportunity_summary
6_outreach_angle

For keys 1-5, value must be an array of findings.
Each finding must be an object with:
- tier (exactly one of: CONFIRMED WEAKNESS, ABSENCE DETECTED, INFERENCE ONLY)
- finding (specific and commercially actionable statement)
- evidence (quote or concise evidence trace from extraction)

For 6_outreach_angle:
- Value must be a single complete sentence.
- Maximum 20 words.
- Reference exactly one specific gap from the extraction data.
- Name the business or reference something specific to this site — do not write generically.
- Write as if a human consultant personally noticed it while browsing the site.
- Do not use any of these phrases: "we can help", "I noticed", "your website", "your digital presence", "fix that".
- Do not list multiple issues.
- Output the sentence only — no label, no prefix, no punctuation errors.

Hard rules:
- Only claims supported by the extracted data.
- Distinguish absence from weakness.
- If uncertain, mark INFERENCE ONLY and mention verification need in finding.
- No generic advice.

Extraction JSON:
{json.dumps(extraction_json, ensure_ascii=False)}
"""
    output = call_openai(prompt=prompt, system=system)
    analysis = parse_json_response(output)
    raw_angle = str(analysis.get("6_outreach_angle", "")).strip()
    analysis["6_outreach_angle"] = repair_outreach_angle(raw_angle, extraction_json)
    return analysis


def normalize_extraction(extraction: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(extraction)

    def nullify_scalar(v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            low = s.lower()
            if low in ("none", "unknown", "") or s in ("[]", "{}"):
                return None
            return s
        return str(v).strip() or None

    for key in ("social_proof", "seo_signals", "cta_quality"):
        raw = out.get(key)
        if raw is None:
            out[key] = None
        elif isinstance(raw, str):
            out[key] = nullify_scalar(raw)
        else:
            out[key] = nullify_scalar(str(raw))

    raw_me = out.get("missing_elements")
    if raw_me is None:
        out["missing_elements"] = []
    elif isinstance(raw_me, str):
        s = raw_me.strip()
        low = s.lower()
        if low in ("none", "unknown", "") or s in ("[]", "{}"):
            out["missing_elements"] = []
        else:
            out["missing_elements"] = [s] if s else []
    elif isinstance(raw_me, list):
        cleaned: List[str] = []
        for item in raw_me:
            if item is None:
                continue
            if isinstance(item, str):
                ns = nullify_scalar(item)
                if ns is not None:
                    cleaned.append(ns)
            else:
                t = str(item).strip()
                if t:
                    cleaned.append(t)
        out["missing_elements"] = cleaned
    else:
        out["missing_elements"] = []

    for key in ("pricing_visible", "blog_active"):
        v = out.get(key)
        if isinstance(v, bool):
            out[key] = v
        elif v is None:
            out[key] = True
        elif isinstance(v, str):
            s = v.strip().lower()
            if s in ("none", "unknown", ""):
                out[key] = True
            elif s in ("true", "1", "yes"):
                out[key] = True
            elif s in ("false", "0", "no"):
                out[key] = False
            else:
                out[key] = True
        else:
            out[key] = bool(v)

    return out


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
- personalization_hooks (list, max 3 specific observable details from the site only)
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
    required_keys = {
        "company_name", "vertical", "core_offer", "target_customer",
        "top_pain_points", "confirmed_weaknesses", "missing_assets",
        "highest_value_opportunity", "best_service_fit", "buying_signals",
        "urgency_score", "trust_score", "decision_maker_guess",
        "personalization_hooks", "schema_version"
    }
    if not required_keys.issubset(set(packet.keys())):
        raise ValueError("Pass 3 packet is missing required keys.")
    import datetime
    packet["metadata"] = {
        "url": extraction_json.get("_url", "unknown"),
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "schema_version": "1.0"
    }
    return packet


def repair_outreach_angle(raw_angle: str, extraction_json: Dict[str, Any]) -> str:
    banned_phrases = [
        "we can help",
        "i noticed",
        "your website",
        "your digital presence",
        "fix that",
    ]

    def is_valid(angle: str) -> bool:
        candidate = angle.strip()
        if not candidate:
            return False
        if len(candidate.split()) > 20:
            return False
        if len(re.findall(r"[.!?]", candidate)) > 1:
            return False
        lowered = candidate.lower()
        return not any(phrase in lowered for phrase in banned_phrases)

    if is_valid(raw_angle):
        return raw_angle.rstrip(".!?") + "."

    business_type = str(extraction_json.get("business_type") or "This business").strip()
    missing_elements = extraction_json.get("missing_elements")
    top_gap = "clear conversion CTA"
    if isinstance(missing_elements, list) and missing_elements:
        first_gap = str(missing_elements[0]).strip()
        if first_gap:
            top_gap = first_gap

    fallback_system = (
        "You write one outreach sentence for sales personalization. "
        "Follow constraints exactly and return only the sentence."
    )
    fallback_prompt = f"""
Write one single sentence for outreach.

Rules:
- Maximum 20 words.
- Reference exactly one specific gap.
- Do not use these phrases: "we can help", "I noticed", "your website", "your digital presence", "fix that".
- No label or prefix.
- One sentence only.

Business type: {business_type}
Top missing element: {top_gap}
All missing elements: {json.dumps(missing_elements, ensure_ascii=False)}
"""

    try:
        second_try = call_openai(prompt=fallback_prompt, system=fallback_system).strip()
        if is_valid(second_try):
            return second_try.rstrip(".!?") + "."
    except Exception:
        pass

    fallback_sentence = f"{business_type} has no {top_gap}."
    fallback_words = fallback_sentence.split()[:20]
    return " ".join(fallback_words).rstrip(".!?") + "."


def render_tier_badge(tier: str) -> str:
    color = TIER_COLORS.get(tier, "#616161")
    return (
        f"<span style='padding:3px 8px;border-radius:999px;background:{color};"
        f"color:white;font-size:12px;font-weight:600;'>{tier}</span>"
    )


def build_report_text(analysis: Dict[str, Any]) -> str:
    section_labels = {
        "1_business_overview": "1. Business Overview",
        "2_target_audience": "2. Target Audience",
        "3_current_marketing_presence": "3. Current Marketing Presence",
        "4_weak_points_and_gaps": "4. Weak Points & Gaps",
        "5_opportunity_summary": "5. Opportunity Summary",
        "6_outreach_angle": "6. Outreach Angle",
    }

    lines: List[str] = []
    for key, label in section_labels.items():
        lines.append(label)
        value = analysis.get(key)
        if isinstance(value, list):
            for item in value:
                lines.append(f"- [{item.get('tier', 'UNKNOWN')}] {item.get('finding', '')}")
                lines.append(f"  Evidence: {item.get('evidence', '')}")
        else:
            lines.append(str(value or ""))
        lines.append("")
    return "\n".join(lines).strip()


def copy_button(report_text: str) -> None:
    escaped = json.dumps(report_text)
    st.components.v1.html(
        f"""
        <button id="copy-btn" style="
            background:#111827;color:white;border:none;padding:0.5rem 0.9rem;
            border-radius:8px;cursor:pointer;font-weight:600;">
            Copy Report
        </button>
        <span id="copy-status" style="margin-left:8px;color:#374151;"></span>
        <script>
            const btn = document.getElementById('copy-btn');
            const status = document.getElementById('copy-status');
            btn.onclick = async () => {{
                try {{
                    await navigator.clipboard.writeText({escaped});
                    status.innerText = 'Copied.';
                }} catch (e) {{
                    status.innerText = 'Copy failed.';
                }}
            }};
        </script>
        """,
        height=70,
    )


def copy_button_packet(packet: Dict[str, Any]) -> None:
    packet_str = json.dumps(packet, ensure_ascii=False, indent=2)
    escaped = json.dumps(packet_str)
    st.components.v1.html(
        f"""
        <button id="copy-packet-btn" style="
            background:#1976d2;color:white;border:none;padding:0.5rem 0.9rem;
            border-radius:8px;cursor:pointer;font-weight:600;">
            Copy Handoff Packet
        </button>
        <span id="copy-packet-status" style="margin-left:8px;color:#374151;"></span>
        <script>
            const btn = document.getElementById('copy-packet-btn');
            const status = document.getElementById('copy-packet-status');
            btn.onclick = async () => {{
                try {{
                    await navigator.clipboard.writeText({escaped});
                    status.innerText = 'Copied.';
                }} catch (e) {{
                    status.innerText = 'Copy failed.';
                }}
            }};
        </script>
        """,
        height=70,
    )


def render_analysis_cards(analysis: Dict[str, Any]) -> None:
    sections = [
        ("1_business_overview", "Business Overview"),
        ("2_target_audience", "Target Audience"),
        ("3_current_marketing_presence", "Current Marketing Presence"),
        ("4_weak_points_and_gaps", "Weak Points & Gaps"),
        ("5_opportunity_summary", "Opportunity Summary"),
        ("6_outreach_angle", "Outreach Angle"),
    ]

    for key, label in sections:
        with st.expander(label, expanded=True):
            value = analysis.get(key)
            if key == "6_outreach_angle":
                st.write(value or "No outreach angle returned.")
                continue

            if not isinstance(value, list) or not value:
                st.info("No findings returned for this section.")
                continue

            for finding in value:
                tier = str(finding.get("tier", "INFERENCE ONLY"))
                st.markdown(render_tier_badge(tier), unsafe_allow_html=True)
                st.write(f"**Finding:** {finding.get('finding', '')}")
                st.write(f"**Evidence:** {finding.get('evidence', '')}")
                st.divider()


def main() -> None:
    st.set_page_config(page_title="BI Scout", page_icon="📈", layout="wide")
    st.title("Marketing Agency Intelligence Scout")
    st.caption("Evidence-driven business intelligence scouting from public website content.")

    with st.sidebar:
        st.header("Scout Controls")
        url = st.text_input("Website URL", placeholder="https://example.com")
        run = st.button("Scout", type="primary", use_container_width=True)
        st.markdown(
            "Reads `.env` keys: `FIRECRAWL_API_KEY` and `OPENAI_API_KEY`.",
        )

    if run:
        if not url or not is_valid_url(url):
            st.error("Please enter a valid URL (including http/https).")
            return

        if not FIRECRAWL_API_KEY or not OPENAI_API_KEY:
            st.error("Missing API keys. Add FIRECRAWL_API_KEY and OPENAI_API_KEY to `.env`.")
            return

        try:
            with st.spinner("Running scouting pipeline..."):
                result = run_pipeline(url)
                extraction = result["extraction"]
                analysis = result["analysis"]
                packet = result["packet"]

            st.success("Scouting complete.")

            with st.expander("Raw Extraction Data", expanded=False):
                st.json(extraction)

            render_analysis_cards(analysis)

            report_text = build_report_text(analysis)
            copy_button(report_text)
            st.divider()
            st.subheader("Agent Handoff Packet")
            st.json(packet)
            copy_button_packet(packet)

        except ValueError as exc:
            st.error(f"Data formatting issue: {exc}")
        except requests.RequestException as exc:
            st.error(f"Network/API error: {exc}")
        except Exception as exc:
            st.error(f"Processing failed: {exc}")


if __name__ == "__main__":
    main()
