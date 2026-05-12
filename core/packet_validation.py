from typing import Dict, List, Tuple

# Required fields for Agent Handoff Packet v1.0
REQUIRED_PACKET_FIELDS = [
    "company_name",
    "url",
    "vertical",
    "core_offer",
    "target_customer",
    "top_pain_points",
    "confirmed_weaknesses",
    "missing_assets",
    "highest_value_opportunity",
    "best_service_fit",
    "buying_signals",
    "urgency_score",
    "trust_score",
    "personalization_hooks",
    "confidence_flags",
    "risk_notes",
    "do_not_say",
    "schema_version",
    "metadata",
]

# Future optional fields — not yet guaranteed to be produced by Agent 1.
OPTIONAL_PACKET_FIELDS = [
    "key_decision_makers",
    "main_pain_points",
    "unique_selling_opportunity",
    "tone_recommendation",
    "competitor_mentions",
    "competitor_context",
    "urgency_signals",
    "risk_factors",
    "recommended_outreach_angle",
]

VALID_CONFIDENCE_VALUES = {"high", "medium", "low"}

# Fields that must be lists if present
LIST_FIELDS = [
    "top_pain_points",
    "confirmed_weaknesses",
    "missing_assets",
    "buying_signals",
    "personalization_hooks",
    "risk_notes",
    "do_not_say",
]

def validate_handoff_packet(packet: dict) -> Tuple[bool, List[str]]:
    """
    Validate Agent Handoff Packet against schema requirements.
    
    Returns:
        (True, []) if valid
        (False, errors) if invalid
    """
    errors: List[str] = []
    
    # Check required fields
    for field in REQUIRED_PACKET_FIELDS:
        if field not in packet:
            errors.append(f"Missing required field: {field}")
    
    # Validate list fields
    for field in LIST_FIELDS:
        if field in packet:
            if not isinstance(packet[field], list):
                errors.append(f"Field {field} must be a list")
            else:
                # Check list items are strings
                for i, item in enumerate(packet[field]):
                    if not isinstance(item, str):
                        errors.append(f"Field {field}[{i}] must be a string")
    
    # Validate numeric fields
    numeric_fields = ["urgency_score", "trust_score"]
    for field in numeric_fields:
        if field in packet:
            if not isinstance(packet[field], (int, float)):
                errors.append(f"Field {field} must be a number")
            else:
                # Check score ranges
                score = packet[field]
                if not (0 <= score <= 100):
                    errors.append(f"Field {field} must be between 0 and 100")
    
    # Validate confidence_flags
    if "confidence_flags" in packet:
        if not isinstance(packet["confidence_flags"], dict):
            errors.append("confidence_flags must be a dict")
        else:
            for key, value in packet["confidence_flags"].items():
                if value not in VALID_CONFIDENCE_VALUES:
                    errors.append(f"confidence_flags.{key} must be one of {VALID_CONFIDENCE_VALUES}")
    
    # Validate schema_version
    if "schema_version" in packet:
        if packet["schema_version"] != "1.0":
            errors.append("schema_version must be '1.0'")
    
    # Validate language field
    if "language" in packet:
        if packet["language"] not in ["ro", "en", "unknown"]:
            errors.append("language must be 'ro', 'en', or 'unknown'")
    
    # Validate metadata
    if "metadata" in packet:
        if not isinstance(packet["metadata"], dict):
            errors.append("metadata must be a dict")
    
    # Note: Extra fields are allowed and should NOT cause validation failure
    # Existing fields like decision_maker_guess should be ignored if present
    
    return (len(errors) == 0, errors)


if __name__ == "__main__":
    print("Testing packet validation...")
    
    # Valid sample packet
    valid_packet = {
        "company_name": "Test Company",
        "url": "https://example.com",
        "vertical": "technology",
        "core_offer": "Software development",
        "target_customer": "Small businesses",
        "top_pain_points": ["outdated systems", "inefficient workflow"],
        "confirmed_weaknesses": ["no online pricing", "weak CTA"],
        "missing_assets": ["social proof", "demo videos"],
        "highest_value_opportunity": "Modern software integration",
        "best_service_fit": "Custom development services",
        "buying_signals": ["contact form", "pricing page"],
        "urgency_score": 75,
        "trust_score": 65,
        "personalization_hooks": ["Using legacy systems", "Located in US"],
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
            "url": "https://example.com",
            "timestamp": "2026-05-12T18:45:00.000Z",
            "schema_version": "1.0"
        },
        # Extra field should be allowed
        "decision_maker_guess": "CTO"
    }
    
    is_valid, errors = validate_handoff_packet(valid_packet)
    print(f"Valid packet result: {is_valid}")
    if errors:
        print("Errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("No validation errors found")
    
    print("\n" + "="*50 + "\n")
    
    # Invalid sample packet
    invalid_packet = {
        "company_name": "Test Company",
        # Missing required fields
        "urgency_score": "invalid",  # Should be number
        "trust_score": 150,  # Should be 0-100
        "top_pain_points": "not a list",  # Should be list
        "confidence_flags": {
            "business_identity": "invalid_value"  # Should be high/medium/low
        },
        "schema_version": "2.0",  # Should be 1.0
        "metadata": "not a dict"  # Should be dict
    }
    
    is_valid, errors = validate_handoff_packet(invalid_packet)
    print(f"Invalid packet result: {is_valid}")
    if errors:
        print("Errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("No validation errors found")
    
    print("\nPacket validation tests completed.")
