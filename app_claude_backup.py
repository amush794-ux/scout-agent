import json
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv


load_dotenv()

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLAUDE_MODEL = "claude-sonnet-4-6"

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


def call_claude(prompt: str, system: str) -> str:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("Missing ANTHROPIC_API_KEY in .env")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=3000,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    chunks = []
    for block in resp.content:
        if getattr(block, "type", "") == "text":
            chunks.append(block.text)
    return "\n".join(chunks).strip()


def pass_1_extract(cleaned_text: str) -> Dict[str, Any]:
    system = (
        "You are a strict web intelligence extraction engine. "
        "Extract facts only from provided website text. "
        "No strategy, no recommendations, no assumptions."
    )
    prompt = f"""
Return ONLY valid JSON (no markdown) with exactly these keys:
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

Rules:
- Use only evidence in text.
- pricing_visible and blog_active must be booleans.
- cta_quality and seo_signals must be one of: none, weak, moderate, strong.
- channels_detected must be a list.
- missing_elements must be a list of things not found.

Website text:
{cleaned_text[:140000]}
"""
    output = call_claude(prompt=prompt, system=system)
    data = parse_json_response(output)
    required_keys = {
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
    if set(data.keys()) != required_keys:
        raise ValueError("Pass 1 JSON is missing keys or contains unexpected keys.")
    return data


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
    output = call_claude(prompt=prompt, system=system)
    analysis = parse_json_response(output)
    raw_angle = str(analysis.get("6_outreach_angle", "")).strip()
    analysis["6_outreach_angle"] = repair_outreach_angle(raw_angle, extraction_json)
    return analysis


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
        second_try = call_claude(prompt=fallback_prompt, system=fallback_system).strip()
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
            "Reads `.env` keys: `FIRECRAWL_API_KEY` and `ANTHROPIC_API_KEY`.",
        )

    if run:
        if not url or not is_valid_url(url):
            st.error("Please enter a valid URL (including http/https).")
            return

        if not FIRECRAWL_API_KEY or not ANTHROPIC_API_KEY:
            st.error("Missing API keys. Add FIRECRAWL_API_KEY and ANTHROPIC_API_KEY to `.env`.")
            return

        try:
            with st.spinner("Scraping website..."):
                pages = crawl_site(url, MAX_SUBPAGES)
                if not pages:
                    raise RuntimeError("No pages were scraped.")

            with st.spinner("Extracting data..."):
                cleaned_text = preprocess_pages(pages)
                extraction = pass_1_extract(cleaned_text)

            with st.spinner("Analyzing intelligence..."):
                analysis = pass_2_analyze(extraction)

            st.success("Scouting complete.")

            with st.expander("Raw Extraction Data", expanded=False):
                st.json(extraction)

            render_analysis_cards(analysis)

            report_text = build_report_text(analysis)
            copy_button(report_text)

        except ValueError as exc:
            st.error(f"Data formatting issue: {exc}")
        except requests.RequestException as exc:
            st.error(f"Network/API error: {exc}")
        except Exception as exc:
            st.error(f"Processing failed: {exc}")


if __name__ == "__main__":
    main()
