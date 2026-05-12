import json
import os
from dotenv import load_dotenv
from openai import OpenAI

# Agent 2 may import shared validation utilities from core/
from core.packet_validation import validate_handoff_packet

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o"

def generate_email_draft(packet: dict) -> dict:
    """
    Generate a professional outreach email draft from a validated Agent 1 handoff packet.
    
    Args:
        packet: Validated Agent 1 handoff packet
        
    Returns:
        dict: {
            "success": True/False,
            "errors": [],
            "draft": {...} or None
        }
    """
    # Validate packet first
    is_valid, validation_errors = validate_handoff_packet(packet)
    
    if not is_valid:
        return {
            "success": False,
            "errors": validation_errors,
            "draft": None
        }
    
    # Check API key
    if not OPENAI_API_KEY:
        return {
            "success": False,
            "errors": ["Missing OPENAI_API_KEY in environment"],
            "draft": None
        }
    
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        system_prompt = """You are writing a personalized business email after manually reviewing a company's website. Sound like a real human who observed specific details, not a marketing automation system.

CRITICAL RULES:
- Use ONLY facts present in the packet
- Never invent claims or statistics
- Never promise guaranteed results
- Respect all do_not_say phrases from packet
- Use 1-2 personalization_hooks naturally in conversation
- Reference one real observed weakness naturally
- Keep email concise (max 180 words)
- Sound conversational-professional, not corporate
- Avoid generic phrases: "strengthen your digital presence", "boost your online visibility", "enhance your brand", "drive engagement"
- Avoid mass outreach language
- Human review is required for all emails
- Return ONLY valid JSON. No markdown. No explanations. No surrounding text.

Email Structure:
- Subject: Max 60 characters, compelling but professional
- Body: 2-3 short paragraphs, mobile-friendly
- Reference specific observations from packet
- Include clear but respectful call-to-action
- Avoid aggressive sales language"""

        user_prompt = f"""Generate a personalized business email based on this handoff packet:

{json.dumps(packet, ensure_ascii=False, indent=2)}

Return ONLY valid JSON with exactly these fields:
- subject (string, max 50 characters)
- body (string, max 180 words)
- reasoning_summary (string, explain approach)
- risk_notes (array of concerns from packet)
- suggested_cta (string, specific call-to-action)
- confidence (string: "high" or "medium" or "low")
- requires_human_review (boolean, must be true)
- schema_version (string, must be "1.0")

Requirements:
- requires_human_review must always be true
- schema_version must equal "1.0"
- Use 1-2 personalization_hooks naturally in conversation
- Reference one confirmed_weakness naturally
- Mention one concrete observation from packet
- Subject: Max 50 characters, specific and compelling
- Body: 2-3 short paragraphs, conversational-professional
- Avoid buzzwords and excessive adjectives
- No marketing clichés or corporate jargon
- Respect all do_not_say restrictions
- Tone matches urgency_score and trust_score
- Sound like you actually reviewed their website"""

        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content.strip()
        
        # Enhanced JSON parsing
        try:
            # Remove any markdown code fences if present
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
            
            # Strip whitespace before parsing
            content = content.strip()
            draft = json.loads(content)
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "errors": [f"Invalid JSON response from AI: {str(e)}"],
                "draft": content  # Include raw content for debugging
            }
        
        # Validate required fields
        required_fields = [
            "subject", "body", "reasoning_summary", "risk_notes",
            "suggested_cta", "confidence", "requires_human_review", "schema_version"
        ]
        
        missing_fields = [field for field in required_fields if field not in draft]
        if missing_fields:
            return {
                "success": False,
                "errors": [f"Missing required fields: {', '.join(missing_fields)}"],
                "draft": None
            }
        
        # Validate critical constraints
        validation_errors = []
        
        if draft.get("requires_human_review") is not True:
            validation_errors.append("requires_human_review must be true")
        
        if draft.get("schema_version") != "1.0":
            validation_errors.append("schema_version must be '1.0'")
        
        if draft.get("confidence") not in ["high", "medium", "low"]:
            validation_errors.append("confidence must be 'high', 'medium', or 'low'")
        
        if len(draft.get("subject", "")) > 50:
            validation_errors.append("subject must be max 50 characters")
        
        if validation_errors:
            return {
                "success": False,
                "errors": validation_errors,
                "draft": draft  # Return partial draft for debugging
            }
        
        return {
            "success": True,
            "errors": [],
            "draft": draft
        }
        
    except Exception as e:
        return {
            "success": False,
            "errors": [f"AI generation failed: {str(e)}"],
            "draft": None
        }


if __name__ == "__main__":
    print("Testing Agent 2 Email Composer...")
    
    # Minimal test packet
    test_packet = {
        "company_name": "Advanced Dental Imaging",
        "url": "https://advanceddental.com",
        "vertical": "healthcare",
        "core_offer": "Dental imaging equipment",
        "target_customer": "Dental clinics",
        "top_pain_points": ["outdated equipment", "inefficient workflow"],
        "confirmed_weaknesses": ["no online pricing", "weak CTA"],
        "missing_assets": ["social proof", "demo videos"],
        "highest_value_opportunity": "Modern digital imaging workflow",
        "best_service_fit": "Equipment financing",
        "buying_signals": ["contact form", "pricing page"],
        "urgency_score": 75,
        "trust_score": 65,
        "personalization_hooks": ["Using legacy systems", "Located in Texas"],
        "confidence_flags": {
            "business_identity": "high",
            "target_customer": "medium",
            "weaknesses": "medium",
            "outreach_angle": "medium"
        },
        "risk_notes": ["uncertain target customer", "weak evidence"],
        "do_not_say": ["guaranteed results", "revenue claims"],
        "schema_version": "1.0",
        "metadata": {
            "url": "https://advanceddental.com",
            "timestamp": "2026-05-12T18:45:00.000Z",
            "schema_version": "1.0",
            "packet_validation": {
                "valid": True,
                "errors": []
            }
        }
    }
    
    result = generate_email_draft(test_packet)
    
    print(f"Success: {result['success']}")
    if result['errors']:
        print("Errors:")
        for error in result['errors']:
            print(f"  - {error}")
    
    if result['draft']:
        print("\nGenerated Draft:")
        print(json.dumps(result['draft'], indent=2))
    
    print("\nAgent 2 Email Composer test completed.")
