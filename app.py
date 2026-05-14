import json
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
import streamlit as st
from dotenv import load_dotenv

from core.pipeline import run_pipeline
from core.review_pipeline import get_pending_reviews, approve_draft, reject_draft, regenerate_draft


load_dotenv()

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

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

    st.markdown(
        """
        <style>
        div[data-testid="stButton"] button[kind="primary"] {
            background-color: #16a34a;
            border-color: #16a34a;
            color: white;
        }
        div[data-testid="stButton"] button[kind="primary"]:hover {
            background-color: #15803d;
            border-color: #15803d;
            color: white;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.4, 1])

    with left:
        st.header("Scout Controls")
        url = st.text_input("Website URL", placeholder="https://example.com")
        run = st.button("Scout", use_container_width=True)
        st.markdown(
            "Reads `.env` keys: `FIRECRAWL_API_KEY` and `OPENAI_API_KEY`.",
        )

    result = None
    extraction = None
    analysis = None
    packet = None
    email_draft = None

    if run:
        valid_run = True

        if not url or not is_valid_url(url):
            with left:
                st.error("Please enter a valid URL (including http/https).")
            valid_run = False

        if not FIRECRAWL_API_KEY or not OPENAI_API_KEY:
            with left:
                st.error("Missing API keys. Add FIRECRAWL_API_KEY and OPENAI_API_KEY to `.env`.")
            valid_run = False

        if valid_run:
            try:
                with st.spinner("Running scouting pipeline..."):
                    result = run_pipeline(url)
                    extraction = result["extraction"]
                    analysis = result["analysis"]
                    packet = result["packet"]
                    email_draft = result.get("email_draft", {})

                    st.session_state["latest_scout_output"] = {
                        "extraction": extraction,
                        "analysis": analysis,
                        "packet": packet,
                        "email_draft": email_draft,
                    }

                with right:
                    st.success("Scouting complete.")

                st.session_state["active_review_url"] = packet.get("url", url)

            except ValueError as exc:
                with right:
                    st.error(f"Data formatting issue: {exc}")
            except requests.RequestException as exc:
                with right:
                    st.error(f"Network/API error: {exc}")
            except Exception as exc:
                with right:
                    st.error(f"Processing failed: {exc}")

    with left:
        st.divider()
        st.subheader("Current draft review")
        active_review_url = st.session_state.get("active_review_url")
        
        if not active_review_url:
            st.info("No active draft. Run Scout to load a draft for review.")
        else:
            pending_reviews = get_pending_reviews()
            matching_review = None
            
            exact_match = None
            normalized_match = None
            
            for review in pending_reviews:
                review_url = review.get('url', '')
                if review_url == active_review_url:
                    exact_match = review
                    break
                if review_url.rstrip("/") == active_review_url.rstrip("/"):
                    if normalized_match is None:
                        normalized_match = review
            
            matching_review = exact_match or normalized_match
            
            if not matching_review:
                st.info("No pending draft found for the current URL.")
            else:
                i = 0
                url = matching_review.get('url', 'N/A')
                st.markdown(f"**URL:** {url}")
                st.markdown(f"**revision_count:** {matching_review.get('revision_count', 'N/A')}")

                latest_email_draft = matching_review.get("latest_email_draft", {}) or {}
                if latest_email_draft:
                    st.markdown(f"**Subject:** {latest_email_draft.get('subject', 'N/A')}")
                    with st.container(border=True):
                        st.write(latest_email_draft.get('body', ''))
                else:
                    st.warning("No email draft content found for this review.")
                
                feedback_key = f"feedback_{url}_{i}"
                feedback = st.session_state.get(feedback_key, "")
                
                col_approve, col_remake = st.columns([1, 1])
                with col_approve:
                    if st.button("Approve draft", key=f"approve_{url}_{i}", type="primary"):
                        result = approve_draft(url)
                        if result:
                            st.success(f"Approved draft for {url}")
                        else:
                            st.error(f"Failed to approve draft for {url}")
                with col_remake:
                    if st.button("🔴 Remake draft", key=f"regenerate_{url}_{i}"):
                        result = regenerate_draft(url, feedback)
                        if result.get("success"):
                            st.success(f"Regeneration complete. Revision count: {result.get('revision_count', 'N/A')}")
                        else:
                            st.error(result.get("error", "Regeneration failed"))
                
                st.text_area("Feedback for remake or rejection", key=feedback_key, height=50)

                if latest_email_draft:
                    st.markdown(f"**Confidence:** {latest_email_draft.get('confidence', 'N/A')}")

                st.caption("Only use Reject / skip if this lead should leave review.")
                if st.button("🟣 Reject / skip", key=f"reject_{url}_{i}"):
                    result = reject_draft(url, feedback)
                    if result:
                        st.success(f"Rejected draft for {url}")
                    else:
                        st.error(f"Failed to reject draft for {url}")
                
                st.divider()

    with right:
        latest_scout_output = st.session_state.get("latest_scout_output")

        if latest_scout_output:
            extraction = latest_scout_output.get("extraction")
            analysis = latest_scout_output.get("analysis")
            packet = latest_scout_output.get("packet")
            email_draft = latest_scout_output.get("email_draft")

            st.success("Latest Scout output")

            with st.expander("Raw Extraction Data", expanded=False):
                st.json(extraction)

            render_analysis_cards(analysis)

            report_text = build_report_text(analysis)
            copy_button(report_text)

            st.divider()
            st.subheader("Agent Handoff Packet")
            st.json(packet)
            copy_button_packet(packet)

            st.divider()
            st.subheader("Agent 2 Email Draft")
            st.json(email_draft)
        else:
            st.info("No Scout output yet.")


if __name__ == "__main__":
    main()
