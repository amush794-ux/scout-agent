import json
import os
from dotenv import load_dotenv
from openai import OpenAI

# Agent 2 may import shared validation utilities from core/
from core.packet_validation import validate_handoff_packet

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o"

ABSOLUTE_BANNED_PHRASES = [
    "game-changer",
    "game changer",
    "boost your visibility",
    "enhance your brand",
    "enhance your digital presence",
    "strengthen your digital presence",
    "drive engagement",
    "unlock growth",
    "take your business to the next level",
    "creșterea vizibilității",
    "prezență online",
    "soluții digitale",
    "strategie digitală",
    "transformare digitală",
]

SOFT_WARNING_PHRASES = [
    "i hope this message finds you well",
    "i just took a look at your website",
    "would you be open to",
    "support you",
    "optimize your",
    "synergy",
    "leverage",
    "innovative solution",
    "cutting-edge",
    "v-ar interesa",
    "ați fi deschiși",
    "o discuție scurtă",
    "putem discuta",
    "cum vă putem ajuta",
    "cu respect",
    "cu stimă",
    "îmbunătăți conversiile",
    "alte clinici",
]

def find_banned_phrases(text: str) -> list[str]:
    """Find absolute banned phrases in text (case-insensitive)."""
    if not isinstance(text, str) or not text.strip():
        return []
    
    text_lower = text.lower()
    found_phrases = []
    
    for phrase in ABSOLUTE_BANNED_PHRASES:
        if phrase in text_lower:
            found_phrases.append(phrase)
    
    return found_phrases

def find_soft_warning_phrases(text: str) -> list[str]:
    """Find soft warning phrases in text (case-insensitive)."""
    if not isinstance(text, str) or not text.strip():
        return []
    
    text_lower = text.lower()
    found_phrases = []
    
    for phrase in SOFT_WARNING_PHRASES:
        if phrase in text_lower:
            found_phrases.append(phrase)
    
    return found_phrases

def load_system_prompt() -> str:
    """Load Agent 2 system prompt from markdown file."""
    try:
        with open("docs/agent2_system_prompt.md", "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "You are a professional outbound consultant."

def load_language_rules(language: str) -> str:
    """Load language-specific outreach rules from markdown file."""
    if language == "ro":
        try:
            with open("docs/agent2_romanian_outreach_rules.md", "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""
    elif language == "en":
        return ""
    elif language == "unknown":
        return ""
    else:
        return ""

def generate_email_draft(packet: dict, feedback: str = None) -> dict:
    """
    Generate a professional outreach email draft from a validated Agent 1 handoff packet.
    
    Args:
        packet: Validated Agent 1 handoff packet
        feedback: Optional feedback to incorporate into the draft
        
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
        
        # Load language-specific rules
        language = packet.get("language", "ro")
        base_system_prompt = load_system_prompt()
        language_rules = load_language_rules(language)
        
        # Combine base prompt with language rules
        system_prompt = base_system_prompt
        if language_rules:
            system_prompt += "\n\n" + language_rules
        
        # Add explicit language instruction
        if language == "ro":
            system_prompt += "\n\nIMPORTANT: Write the email in Romanian. Do not translate English templates. Follow Romanian-native rules."

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
- Sound like you actually reviewed their website

ROMANIAN STYLE EXAMPLES:
The following examples teach style and structure only. Do not reuse their facts unless those facts exist in the packet.

GOOD SUBJECT EXAMPLES:
- O observație despre prețuri
- Despre programările de pe site
- Despre formularul de contact
- Un lucru despre pagina de servicii
- O observație despre servicii

BAD SUBJECT EXAMPLES:
- Oportunitate de colaborare
- Soluții digitale pentru afacerea dumneavoastră
- Creștere rapidă prin AI
- Transformare digitală completă
- Hai să programăm un call
- Despre informațiile de pe site

GOOD BODY EXAMPLE 1:
Bună ziua,

Am observat că programările se fac doar prin telefon, deși mulți clienți caută informațiile direct de pe site.

Asta poate însemna pași în plus pentru cineva care vrea doar să verifice rapid disponibilitatea.

Am notat 2-3 ajustări simple care ar face procesul mai clar.

Merită să vi le trimit?

GOOD BODY EXAMPLE 2:
Bună ziua,

Am observat că informațiile despre servicii sunt împărțite în mai multe zone ale site-ului.

Pentru cineva care compară rapid opțiunile, asta poate face decizia mai lentă sau mai neclară.

Vă trimit observațiile, dacă sunt utile?

BAD BODY EXAMPLE 1:
Stimate domn,

Vă oferim soluții inovatoare pentru optimizarea prezenței digitale și creșterea semnificativă a performanței afacerii dumneavoastră.

Cu stimă,
[Nume]

BAD BODY EXAMPLE 2:
Bună ziua,

Folosim tehnologie de ultimă generație pentru a vă ajuta să transformați digital afacerea și să obțineți rezultate excepționale.

Putem programa un call pentru a discuta mai multe?

GOOD CTA EXAMPLES:
- Merită să vi le trimit?
- Vă trimit observațiile?
- Vreți să vedeți ce am observat?
- Dacă e util, vă trimit detaliile.

BAD CTA EXAMPLES:
- Programați un call.
- Hai să stabilim o întâlnire.
- Când sunteți disponibil?
- Contactați-ne acum.
- Nu ratați această oportunitate.

STYLE RULE:
Follow the GOOD examples for structure and tone. Avoid the BAD examples completely. The email must start from one concrete observation in the packet, connect it to one practical friction, and end with a low-pressure Romanian CTA.

ROMANIAN PRACTICAL FRICTION RULE:
Avoid generic business claims. Do not write vague sentences like:
- Într-o piață competitivă, transparența poate face diferența.
- Acest lucru poate atrage mai mulți clienți.
- Acest aspect poate îmbunătăți imaginea companiei.
- Asta poate crește performanța afacerii.
- Poate aduce beneficii importante.

Instead, after the first concrete observation, connect it to one practical friction:
- poate adăuga un pas în plus înainte ca persoana să ia legătura
- poate face comparația mai grea pentru cineva care caută rapid opțiuni
- poate lăsa întrebări fără răspuns înainte de contact
- poate face procesul mai neclar pentru un client nou
- poate reduce numărul de cereri trimise prin site
- poate face decizia mai lentă pentru cineva care compară furnizori

RULE:
Every email body must include one concrete practical friction sentence immediately after the first concrete observation. The friction must be based on packet evidence. Do not use generic business filler."""

        if feedback:
            user_prompt += f"\n\nFeedback: {feedback}\n\nIf feedback is provided, address it while still obeying all packet facts, do_not_say rules, Romanian rules, quality gates, required JSON fields, and human review requirement."

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
        
        # Phrase quality gate
        combined_text = f"{draft.get('subject', '')} {draft.get('body', '')}"
        banned_phrases = find_banned_phrases(combined_text)
        soft_warnings = find_soft_warning_phrases(combined_text)
        
        # Handle absolute banned phrases (fail generation)
        for phrase in banned_phrases:
            validation_errors.append(f"Banned phrase detected: {phrase}")
        
        # Handle soft warning phrases (warn but don't fail)
        final_errors = validation_errors.copy()
        for phrase in soft_warnings:
            final_errors.append(f"Soft warning phrase detected: {phrase}")
        
        # Fail only if there are banned phrases or other validation errors
        if validation_errors:
            return {
                "success": False,
                "errors": validation_errors,
                "draft": draft  # Return partial draft for debugging
            }
        
        # Success with soft warnings included
        return {
            "success": True,
            "errors": [f"Soft warning phrase detected: {phrase}" for phrase in soft_warnings],
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
    
    # Verify system prompt loading
    system_prompt = load_system_prompt()
    print(f"System prompt loaded (first 100 chars): {system_prompt[:100]}...")
    print()
    
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
    
    print("\n" + "="*50 + "\n")
    
    # Test phrase detection
    print("Testing phrase detection...")
    
    # Test banned phrases
    banned_text = "This is a game-changer solution that will enhance your digital presence"
    banned_found = find_banned_phrases(banned_text)
    print(f"Banned phrases in: '{banned_text}'")
    print(f"Found: {banned_found}")
    
    # Test soft warning phrases
    soft_text = "I hope this message finds you well. Would you be open to discussing?"
    soft_found = find_soft_warning_phrases(soft_text)
    print(f"\nSoft warning phrases in: '{soft_text}'")
    print(f"Found: {soft_found}")
    
    # Test clean text
    clean_text = "Modern solutions for your business needs"
    clean_found_banned = find_banned_phrases(clean_text)
    clean_found_soft = find_soft_warning_phrases(clean_text)
    print(f"\nClean text: '{clean_text}'")
    print(f"Banned found: {clean_found_banned}")
    print(f"Soft warnings found: {clean_found_soft}")
    
    print("\nAgent 2 Email Composer test completed.")
