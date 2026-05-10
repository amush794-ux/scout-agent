import json
import os
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o"


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


def run_scout(website_content: str) -> dict:
    extraction = pass_1_extract(website_content)
    extraction = normalize_extraction(extraction)
    analysis = pass_2_analyze(extraction)
    return {"extraction": extraction, "analysis": analysis}

