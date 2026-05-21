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

## email_brief

email_brief is the preferred source for Agent 2 when generating Romanian outreach emails. It should contain only email-ready information: real problems, usable specific details, weak details to avoid, suggested consequence, suggested offer, and subject options.

Schema:

```json
{
  "email_brief": {
    "business_name": "string",
    "vertical_label": "string",
    "customer_word": "string",
    "comparison_context": "string",
    "main_email_angle": "string",
    "usable_specific_details": ["string"],
    "avoid_as_email_details": ["string"],
    "confirmed_email_problems": [
      {
        "problem": "string",
        "evidence_type": "string",
        "confidence": "high|medium|low"
      }
    ],
    "consequence_seed": "string",
    "offer_seed": "string",
    "subject_options": ["string"],
    "confidence": "high|medium|low",
    "must_not_say": ["string"]
  }
}
```

Field meanings:

- **business_name**: company name used in the email subject and opening.
- **vertical_label**: human-readable Romanian business category, for example "clinică de imagistică dentară", "salon", "restaurant".
- **customer_word**: vertical-specific loss word, for example "pacienți", "programări", "rezervări", "clienți".
- **comparison_context**: realistic buyer context, for example "pentru cineva care compară clinici".
- **main_email_angle**: short Romanian summary of the commercial email angle.
- **usable_specific_details**: specific business-relevant details that are safe and useful in the email.
- **avoid_as_email_details**: weak, generic, technical, or UI-only details that should not appear directly in the email.
- **confirmed_email_problems**: 2-3 email-ready problems, written in Romanian when possible and based only on packet evidence.
- **consequence_seed**: suggested Romanian consequence sentence for the second paragraph.
- **offer_seed**: suggested Romanian offer sentence for the third paragraph.
- **subject_options**: 2-4 subject lines Agent 2 may choose from.
- **confidence**: overall confidence of the email brief.
- **must_not_say**: claims Agent 2 must avoid.

### Rules

1. email_brief is additional. It must not replace existing packet fields yet.

2. email_brief should be assembled by `core/pipeline.py` after the standard packet is created.

3. During the transition, email_brief is optional and should not be required by packet validation yet.

4. Once implemented, Agent 2 should treat email_brief as the primary source for Romanian emails.

5. The pipeline email_brief builder must be defensive. If a source packet field is missing, empty, renamed, or malformed, it must use a safe fallback instead of crashing.

Safe fallback examples:
- missing business_name -> use company_name if available, otherwise "compania"
- missing vertical -> use "business local"
- missing customer_word -> use "clienți"
- missing usable_specific_details -> use an empty list
- missing confirmed_email_problems -> build only from confirmed weaknesses that are present
- missing subject_options -> use "{business_name}, opinie sinceră" when business_name exists

6. Do not put weak UI labels in usable_specific_details.

Weak details that should usually go into avoid_as_email_details:
- AFLĂ MAI MULT CTA
- active blog
- strong CTA
- contact CTA present
- generic CTA labels
- generic SEO/content observations

7. usable_specific_details should prefer concrete business-relevant details:
- technology names
- named services
- pricing
- testimonials
- visible results
- booking path
- menu
- contact path
- location
- visible trust proof

8. confirmed_email_problems must be email-ready, not raw analysis labels.

Bad:
- no social proof
- pricing information missing
- conversion rate issues

Good:
- prețurile nu sunt vizibile
- lipsesc testimoniale sau dovezi reale
- tehnologia 3Shape TRIOS nu este suficient evidențiată

9. consequence_seed must not promise business results. It should describe realistic client behavior.

Good:
Un pacient care caută o clinică de încredere și nu găsește rapid prețuri sau dovezi reale poate pierde interesul și alege altă clinică.

Bad:
Acest lucru va crește numărul de pacienți.

10. offer_seed should describe a new version of the site, not observations.

Good:
Am făcut deja o variantă nouă a site-ului - mai clară, mai interactivă și mai ușor de navigat, cu tehnologia, serviciile și contactul prezentate mai convingător.

Bad:
Am notat câteva observații.

11. email_brief must not invent facts. If a specific technology, service, or proof point is not present in the packet, it should not be added as confirmed.

12. If no strong specific detail exists, usable_specific_details can be empty and confidence should usually be medium or low.

13. Cost rule:
Do not ask the LLM to generate email_brief in normal operation. The goal is to reduce repeated Agent 2 reasoning and keep token usage low by passing a compact, deterministic email brief.

### Evidence Types

Evidence types may include:
- missing_pricing
- missing_social_proof
- missing_testimonials
- missing_contact_path
- weak_visual_trust
- weak_navigation
- specific_detail_underused
- unclear_target_customer
- other

specific_detail_underused means a real business-relevant detail exists in the packet, such as a technology, service, product, menu, booking option, result, or location, but it is not presented strongly enough for outreach positioning.

When `core/pipeline.py` later builds email_brief, it must handle evidence_type defensively. Unknown evidence_type values should not crash the pipeline. They should fall back to "other".

### Visiodent Example

```json
{
  "email_brief": {
    "business_name": "Visiodent",
    "vertical_label": "clinică de imagistică dentară",
    "customer_word": "pacienți",
    "comparison_context": "pentru cineva care compară clinici",
    "main_email_angle": "Refacere site pentru claritate, încredere și prezentarea mai convingătoare a tehnologiei, serviciilor și contactului.",
    "usable_specific_details": [
      "3Shape TRIOS",
      "servicii de imagistică dentară"
    ],
    "avoid_as_email_details": [
      "AFLĂ MAI MULT CTA",
      "active blog",
      "contact CTA present"
    ],
    "confirmed_email_problems": [
      {
        "problem": "prețurile nu sunt vizibile",
        "evidence_type": "missing_pricing",
        "confidence": "high"
      },
      {
        "problem": "lipsesc testimoniale sau dovezi reale",
        "evidence_type": "missing_social_proof",
        "confidence": "high"
      },
      {
        "problem": "tehnologia 3Shape TRIOS nu este suficient evidențiată",
        "evidence_type": "specific_detail_underused",
        "confidence": "medium"
      }
    ],
    "consequence_seed": "Un pacient care caută o clinică de încredere și nu găsește rapid prețuri sau dovezi reale poate pierde interesul și alege altă clinică.",
    "offer_seed": "Am făcut deja o variantă nouă a site-ului - mai clară, mai interactivă și mai ușor de navigat, cu tehnologia, serviciile și contactul prezentate mai convingător.",
    "subject_options": [
      "Visiodent, opinie sinceră",
      "Visiodent, prima impresie",
      "Observații despre Visiodent"
    ],
    "confidence": "medium",
    "must_not_say": [
      "rezultate garantate",
      "mai mulți pacienți garantat",
      "creștere de venit",
      "afirmații nesusținute de packet"
    ]
  }
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
