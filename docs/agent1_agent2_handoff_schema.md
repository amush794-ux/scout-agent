# Agent 1 to Agent 2 Handoff Schema

## Purpose

This document defines the stable contract between Agent 1 (Scout) and Agent 2 (Email Composer). The schema provides compressed intelligence from website scouting that Agent 2 can safely consume to generate personalized outreach drafts without re-scraping or re-scoring leads.

## What Agent 2 is Allowed to Consume

- **Compressed scout intelligence** from the handoff packet
- **Personalization hooks** derived from observable website content
- **Business intelligence** already processed and scored by Agent 1
- **Risk assessments** and confidence flags for decision making

## What Agent 2 is Forbidden to Do

- **Do NOT scrape websites** - use only provided intelligence
- **Do NOT re-score leads** - use urgency_score and trust_score from Agent 1
- **Do NOT reinterpret raw extraction** - use compressed conclusions from handoff packet
- **Do NOT modify business intelligence** - preserve Agent 1's analysis
- **Do NOT bypass human approval** - outreach requires human review before sending

## Required Fields

All fields below must be present in every handoff packet:

| Field | Type | Required | Description |
|--------|------|----------|-------------|
| `company_name` | string | ✅ | Business name from website |
| `url` | string | ✅ | Original scouted URL |
| `language` | string | ✅ | Outreach behavior language ("ro", "en", "unknown") |
| `vertical` | string | ✅ | Industry classification |
| `core_offer` | string | ✅ | Primary product/service offering |
| `target_customer` | string | ✅ | Intended customer base |
| `top_pain_points` | array | ✅ | Up to 3 short pain signals |
| `confirmed_weaknesses` | array | ✅ | Up to 3 verified weaknesses |
| `missing_assets` | array | ✅ | Up to 3 observable gaps |
| `highest_value_opportunity` | string | ✅ | Best opportunity (max 15 words) |
| `best_service_fit` | string | ✅ | Recommended service (max 10 words) |
| `buying_signals` | array | ✅ | Up to 3 engagement indicators |
| `urgency_score` | integer | ✅ | 0-100 priority score from Agent 1 |
| `trust_score` | integer | ✅ | 0-100 credibility score from Agent 1 |
| `personalization_hooks` | array | ✅ | Up to 3 specific site observations |
| `confidence_flags` | object | ✅ | Confidence indicators by category |
| `risk_notes` | array | ✅ | Risk considerations for outreach |
| `do_not_say` | array | ✅ | Phrases to avoid in outreach |
| `schema_version` | string | ✅ | Schema version (always "1.0") |
| `metadata` | object | ✅ | Processing metadata |

## Optional Fields

| Field | Type | Description |
|--------|------|-------------|
| `business_size` | string | Company size estimate |
| `location` | string | Geographic location |
| `contact_info` | object | Available contact details |

## Field Descriptions

### Core Business Intelligence
- **company_name**: Legal/trade name clearly visible on website
- **language**: Outreach behavior language ("ro", "en", "unknown") - Controls which Agent 2 behavior rules to load
- **vertical**: Industry classification (e.g., "healthcare", "technology", "professional_services")
- **core_offer**: Primary product or service offering
- **target_customer**: Intended customer base or audience

### Opportunity Analysis
- **top_pain_points**: Short signals indicating customer problems (max 3)
- **confirmed_weaknesses**: Verified marketing/sales weaknesses (max 3)
- **missing_assets**: Observable gaps in marketing presence (max 3)
- **highest_value_opportunity**: Best actionable opportunity (max 15 words)
- **best_service_fit**: Most relevant service recommendation (max 10 words)

### Engagement Intelligence
- **buying_signals**: Indicators of purchase readiness (max 3)
- **urgency_score**: 0-100 priority score from Agent 1 analysis
- **trust_score**: 0-100 credibility score from Agent 1 analysis
- **personalization_hooks**: Specific observable details for personalization (max 3)

### Safety and Compliance
- **confidence_flags**: Object with confidence levels by category
- **risk_notes**: Array of risk considerations for outreach
- **do_not_say**: Phrases to avoid in outreach messaging

## Allowed Value Guidance

### Vertical Classifications
- "healthcare" - Medical, dental, wellness services
- "technology" - SaaS, software, IT services
- "professional_services" - Consulting, legal, financial
- "ecommerce" - Online retail, marketplace
- "manufacturing" - Production, industrial
- "education" - Training, schools, courses
- "unknown" - Industry not clearly identified

### Urgency Score Ranges
- **0-30**: Low priority, basic needs met
- **31-60**: Medium priority, clear improvement opportunities
- **61-80**: High priority, significant gaps present
- **81-100**: Critical priority, urgent needs identified

### Trust Score Ranges
- **0-30**: Low credibility, limited social proof
- **31-60**: Medium credibility, some trust indicators
- **61-80**: High credibility, strong social proof
- **81-100**: Very high credibility, established presence

## Confidence Flags

```json
{
  "business_classification": "high" | "medium" | "low",
  "opportunity_assessment": "high" | "medium" | "low", 
  "contact_readiness": "high" | "medium" | "low",
  "personalization_quality": "high" | "medium" | "low"
}
```

## Risk Notes

Common risk considerations to include:
- "Limited contact information available"
- "Generic website content"
- "No clear decision maker identified"
- "Competitive market saturation"
- "Potential privacy compliance concerns"
- "Limited budget indicators"

## Do Not Say Phrases

Phrases to avoid in outreach:
- "we can help"
- "I noticed" 
- "your website"
- "your digital presence"
- "fix that"
- "obviously"
- "clearly"

## Example JSON Packet

```json
{
  "company_name": "Advanced Dental Imaging",
  "url": "https://advanceddental.com",
  "language": "en",
  "vertical": "healthcare",
  "core_offer": "Dental imaging equipment and software",
  "target_customer": "Dental clinics and imaging centers",
  "top_pain_points": ["outdated equipment", "inefficient workflow", "limited imaging capabilities"],
  "confirmed_weaknesses": ["no online pricing", "missing case studies", "weak CTA"],
  "missing_assets": ["pricing information", "social proof", "demo videos"],
  "highest_value_opportunity": "Upgrade to modern digital imaging workflow",
  "best_service_fit": "Equipment financing and implementation",
  "buying_signals": ["request demo form", "contact page", "equipment specs"],
  "urgency_score": 75,
  "trust_score": 65,
  "personalization_hooks": ["Using legacy imaging systems", "Located in Texas", "Specializes in pediatric dentistry"],
  "confidence_flags": {
    "business_classification": "high",
    "opportunity_assessment": "medium",
    "contact_readiness": "high",
    "personalization_quality": "high"
  },
  "risk_notes": ["No pricing transparency", "Competitive imaging market"],
  "do_not_say": ["we can help", "I noticed", "your website"],
  "schema_version": "1.0",
  "metadata": {
    "url": "https://advanceddental.com",
    "timestamp": "2026-05-12T18:45:00.000Z",
    "schema_version": "1.0",
    "processed_by": "agent1_scout"
  }
}
```

## Language Field Examples

**GOOD:**
```json
{
  "language": "ro"
}
```

**GOOD:**
```json
{
  "language": "en"
}
```

**BAD:**
```json
{
  "company_name": "Advanced Dental Imaging"
}
```

## Future Extension Notes

### Version 1.1 Considerations
- Add `competitor_intelligence` field for market positioning
- Include `budget_indicators` for pricing strategy
- Expand `personalization_hooks` to include temporal data
- Add `compliance_flags` for regulated industries

### Version 1.1 Considerations
- Add `language` field for native behavior selection
- Romanian outreach uses Romanian-native rules
- English outreach uses English-native rules
- Future multilingual support should use native behavior layers, not direct translation

### Version 2.0 Considerations
- Multi-location support for franchises
- Integration with CRM systems
- Automated follow-up scheduling
- A/B testing framework for outreach

### Backward Compatibility
- All future versions must maintain required fields
- New fields should be optional with sensible defaults
- Schema version must be explicitly incremented
- Migration paths should be documented for breaking changes

### Architecture Notes
The `language` field enables Agent 2 to select appropriate native behavior rules:
- **"ro"** loads Romanian outreach behavior from `docs/agent2_romanian_outreach_rules.md`
- **"en"** loads English outreach behavior from base system prompt
- **"unknown"** uses conservative fallback behavior
- **Future multilingual support** should add new language-specific behavior files, not translation logic
- **Cultural adaptation** requires behavioral specification, not linguistic translation
- **Scalable framework** - Each language gets its own behavioral specification layer

## Usage Guidelines

1. **Always validate schema_version** before processing
2. **Handle missing optional fields gracefully**
3. **Respect confidence_flags** when generating outreach
4. **Consider risk_notes** in messaging strategy
5. **Use personalization_hooks** for authentic personalization
6. **Never bypass human approval** regardless of scores
7. **Log all outreach attempts** with packet reference

## Compliance Notes

- Respect all privacy regulations in outreach
- Do not make false claims about capabilities
- Honor unsubscribe requests immediately
- Maintain professional communication standards
- Document all decision-making processes
