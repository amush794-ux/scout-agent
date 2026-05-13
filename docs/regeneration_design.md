# Regeneration Design

## Preconditions
- State must be draft_reviewing or draft_rejected
- revision_count must be < 3
- Original packet must exist in scout_results

## Flow
1. Validate state and revision_count
2. Fetch original packet via get_scout_packet_by_url(url)
3. Call generate_email_draft(packet, feedback)
4. If generation fails: return error, do NOT increment revision_count
5. If generation succeeds: increment revision_count, persist new draft, set draft_reviewing
6. Return success with new draft

## Rules
- revision_count tracks successful regenerations only
- No draft_regenerating status (synchronous execution)
- generate_email_draft must accept feedback parameter (not yet implemented)
- Steps 5-6 are not atomic, acceptable for current stage

## Not Yet Implemented
- Telegram integration
- Background/async regeneration
- Atomic transaction for increment + persist
