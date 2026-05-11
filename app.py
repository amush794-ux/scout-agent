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
