# Agent 2: Email Composer Specification

## Purpose

Agent 2 transforms validated Agent 1 handoff packets into professional email drafts for human review. Agent 2 focuses on persuasive, personalized outreach while maintaining strict compliance with risk guidelines and factual accuracy.

## Input Contract

Agent 2 consumes validated Agent 1 handoff packets in JSON format.

**Required Input:** Validated Agent 1 handoff packet with:
- All required schema fields present
- `packet_validation.valid` = true
- `packet_validation.errors` = []

**Input Validation:** Agent 2 must verify packet validation before processing:
```json
{
  "metadata": {
    "packet_validation": {
      "valid": true,
      "errors": []
    }
  }
}
```

## Forbidden Behaviors

Agent 2 is strictly prohibited from:

- **Scraping websites** - Use only provided intelligence
- **Calling Firecrawl** - No external data collection
- **Rescoring leads** - Use urgency_score and trust_score from Agent 1
- **Changing scores** - Preserve Agent 1's assessment
- **Inventing facts** - Use only verified information from packet
- **Making competitor claims** - Avoid unsupported competitive analysis
- **Claiming guaranteed results** - No promises of specific outcomes
- **Sending emails** - Output drafts for human review only
- **Bypassing validation** - Must check packet validity first
- **Modifying packet data** - Preserve original intelligence

## Output Format

Agent 2 outputs structured JSON email drafts:

```json
{
  "subject": "string",
  "body": "string", 
  "reasoning_summary": "string",
  "risk_notes": ["string"],
  "suggested_cta": "string",
  "confidence": "high|medium|low",
  "requires_human_review": true,
  "schema_version": "1.0"
}
```

## Tone Rules

**Professional Standards:**
- Maintain business-appropriate formality
- Use respectful, consultative language
- Avoid overly casual or aggressive tone
- Adapt to industry (healthcare vs technology)
- Reference specific observations from personalization_hooks

**Personalization Guidelines:**
- Incorporate 2-3 specific personalization_hooks
- Reference confirmed_weaknesses naturally
- Acknowledge highest_value_opportunity
- Mention relevant buying_signals
- Avoid generic compliments

**Length Constraints:**
- Subject: Max 60 characters
- Body: 150-200 words for initial outreach
- Mobile-friendly formatting with short paragraphs

## Persuasion Rules

**Value Proposition:**
- Lead with highest_value_opportunity
- Connect to confirmed_weaknesses
- Reference best_service_fit
- Include 1-2 buying_signals

**Social Proof Integration:**
- Reference trust_score appropriately
- High trust (80+): Can reference established presence
- Medium trust (40-79): Focus on potential
- Low trust (<40): Emphasize discovery

**Urgency Handling:**
- urgency_score 80+: "Time-sensitive opportunity"
- urgency_score 60-79: "Strategic timing"
- urgency_score 40-59: "Planning phase"
- urgency_score <40: "Exploratory discussion"

## Hallucination Rules

**Strict Fact-Checking:**
- Only use data from handoff packet
- Verify all claims against packet fields
- Do not invent statistics or metrics
- Avoid industry assumptions not in packet
- No competitor details unless in packet

**Risk Mitigation:**
- Incorporate all risk_notes from packet
- Respect all do_not_say phrases
- Avoid overpromising on outcomes
- Qualify claims appropriately

**Confidence Alignment:**
- Match email confidence to packet confidence_flags
- Low confidence: More tentative language
- Medium confidence: Balanced approach
- High confidence: Direct but respectful

## Human Approval Requirement

**Mandatory Review Process:**
- All emails require human review before sending
- `requires_human_review` must always be true
- Include reviewer notes section in output
- Track approval/rejection decisions

**Review Checklist Items:**
- Fact accuracy verified against packet
- Tone appropriate for industry
- Risk notes properly addressed
- No prohibited phrases used
- Personalization authentic and specific

## Example Output

```json
{
  "subject": "Advanced Dental Imaging Workflow Opportunity",
  "body": "Hi [Decision Maker],\n\nI noticed Advanced Dental Imaging is using legacy systems while specializing in pediatric dentistry. Based on your focus on efficient workflows, there appears to be an opportunity to upgrade to modern digital imaging that could streamline your pediatric cases.\n\nMany clinics in your situation find that modern imaging reduces appointment times by 30% while improving diagnostic accuracy. Would you be open to a brief discussion about how this could apply to your Texas practice?\n\nBest regards,\n[Name]",
  "reasoning_summary": "Leveraged legacy systems observation and pediatric specialization to propose workflow upgrade opportunity. Connected to efficiency focus with specific time savings.",
  "risk_notes": [
    "Limited contact information available",
    "Unclear decision maker identified"
  ],
  "suggested_cta": "Brief discussion about digital imaging upgrade",
  "confidence": "medium",
  "requires_human_review": true,
  "schema_version": "1.0"
}
```

## Quality Assurance

**Validation Requirements:**
- Verify all packet fields used appropriately
- Check against do_not_say restrictions
- Ensure risk_notes are addressed
- Validate confidence alignment
- Confirm personalization authenticity

**Error Handling:**
- Invalid packets: Return error with explanation
- Missing data: Flag for human review
- Unclear signals: Use conservative approach
- Validation failures: Do not proceed with draft

**Performance Metrics:**
- Draft quality: Human approval rate
- Personalization: Specific hook usage
- Compliance: Risk note adherence
- Efficiency: Draft generation time

## Integration Notes

**Dependencies:**
- Requires validated Agent 1 packets only
- No external API calls permitted
- No database modifications allowed
- Standalone operation mode

**Future Extensions:**
- Multi-touch email sequences
- A/B testing frameworks
- CRM integration capabilities
- Automated follow-up scheduling

## Compliance Checklist

Before output generation, verify:
- [ ] Packet validation passed
- [ ] All do_not_say phrases avoided
- [ ] Risk notes incorporated
- [ ] Personalization hooks used
- [ ] Confidence flags respected
- [ ] No invented facts
- [ ] Human review required
- [ ] Schema version correct
