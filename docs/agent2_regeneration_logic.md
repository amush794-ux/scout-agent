# Agent 2 Regeneration Logic

## 1. Purpose
First draft generation is separate from regeneration workflow.

## 2. Ownership
- core/pipeline.py = first draft generation
- Future core/review_pipeline.py = approval/rejection/regeneration
- agents/email_composer.py = draft generation only
- database/db.py = state persistence only

## 3. Initial Draft Flow
- run_pipeline(url)
- Generate first draft
- Save latest_email_draft
- Set draft_status = draft_reviewing
- revision_count remains 0

## 4. Rejection Flow
- User rejects draft
- Optional future feedback
- Set draft_status = draft_rejected
- Preserve original packet
- No rescraping

## 5. Regeneration Flow
- get_lead_draft_state(url)
- If revision_count < 3:
  - increment_revision_count(url)
  - Regenerate draft from original packet + feedback
  - Save new draft
  - Set draft_status = draft_reviewing
- Else:
  - Set draft_status = draft_failed
  - Stop regeneration

## 6. Approval Flow
- User approves draft
- Set draft_status = draft_approved
- Save approved_at timestamp

## 7. Rules
- revision_count tracks regenerations only
- Max retries = 3
- No infinite loops
- No sending without approval
- No rescraping during regeneration
- Packet remains source of truth

## 8. Future Notes
Future implementation:
- core/review_pipeline.py
- approve_draft()
- reject_draft()
- regenerate_draft()
