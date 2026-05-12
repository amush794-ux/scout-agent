# Database Review State Design

## New Fields for leads table

### Schema Extension

| Field | Type | Default | Purpose |
|---------|------|----------|---------|
| draft_status | TEXT | "draft_pending" | Current workflow state |
| revision_count | INTEGER | 0 | Number of regeneration attempts |
| latest_email_draft | TEXT (JSON) | NULL | Current active draft JSON |
| draft_generated_at | TEXT (ISO timestamp) | NULL | When latest draft was generated |
| approved_at | TEXT (ISO timestamp) | NULL | When human approved |
| rejected_at | TEXT (ISO timestamp) | NULL | When human rejected |
| rejection_reason | TEXT | NULL | Feedback for regeneration |

## Constraints

### draft_status Enum
```sql
CHECK (draft_status IN (
    'draft_pending', 
    'draft_reviewing', 
    'draft_approved', 
    'draft_rejected', 
    'draft_regenerating', 
    'draft_failed'
))
```

### Revision Count Limits
```sql
CHECK (revision_count >= 0 AND revision_count <= 3)
```

### Timestamp Constraints
```sql
-- approved_at and rejected_at cannot both be set
CHECK (
    (approved_at IS NULL) OR 
    (rejected_at IS NULL)
)

-- timestamps must be valid ISO format
CHECK (
    (draft_generated_at IS NULL OR 
     draft_generated_at LIKE '%Y-%m-%dT%H:%M:%S.%fZ')
)
```

### JSON Validation
```sql
-- latest_email_draft must contain valid JSON when present
CHECK (
    latest_email_draft IS NULL OR 
    json_valid(latest_email_draft)
)
```

## Migration Notes

### SQLite ALTER TABLE Commands
```sql
-- Add new columns to existing leads table
ALTER TABLE leads ADD COLUMN draft_status TEXT DEFAULT 'draft_pending';
ALTER TABLE leads ADD COLUMN revision_count INTEGER DEFAULT 0;
ALTER TABLE leads ADD COLUMN latest_email_draft TEXT;
ALTER TABLE leads ADD COLUMN draft_generated_at TEXT;
ALTER TABLE leads ADD COLUMN approved_at TEXT;
ALTER TABLE leads ADD COLUMN rejected_at TEXT;
ALTER TABLE leads ADD COLUMN rejection_reason TEXT;

-- Add constraints
ALTER TABLE leads ADD CONSTRAINT chk_draft_status 
    CHECK (draft_status IN ('draft_pending', 'draft_reviewing', 'draft_approved', 'draft_rejected', 'draft_regenerating', 'draft_failed'));

ALTER TABLE leads ADD CONSTRAINT chk_revision_count 
    CHECK (revision_count >= 0 AND revision_count <= 3);
```

### Backward Compatibility
- **Existing Data**: All new columns have sensible defaults
- **No Breaking Changes**: Existing queries continue to work
- **Gradual Migration**: Can enable review workflow incrementally
- **Data Integrity**: Foreign keys and existing constraints preserved

## Future Fields

### Multi-User Support
| Field | Type | Purpose |
|--------|------|---------|
| previous_drafts | TEXT (JSON array) | Array of past versions |
| reviewed_by | TEXT | User ID of reviewer |
| sent_at | TEXT (ISO timestamp) | When email actually sent |

### Audit Trail Enhancement
| Field | Type | Purpose |
|--------|------|---------|
| workflow_history | TEXT (JSON array) | Complete state transition log |
| quality_metrics | TEXT (JSON object) | Phrase violations and scores |

## Index Recommendations

### Performance Indexes
```sql
-- Filter by workflow status
CREATE INDEX idx_leads_draft_status ON leads(draft_status);

-- Audit queries by approval time
CREATE INDEX idx_leads_approved_at ON leads(approved_at);

-- Find stale drafts needing review
CREATE INDEX idx_leads_draft_generated_at ON leads(draft_generated_at);

-- Track revision patterns
CREATE INDEX idx_leads_revision_count ON leads(revision_count);
```

### Query Optimization
```sql
-- Get drafts needing human review
SELECT * FROM leads 
WHERE draft_status = 'draft_pending' 
AND draft_generated_at < datetime('now', '-1 day');

-- Find stuck regeneration loops
SELECT * FROM leads 
WHERE revision_count >= 3 
AND draft_status = 'draft_regenerating';

-- Audit trail for specific lead
SELECT draft_status, revision_count, draft_generated_at, approved_at, rejected_at
FROM leads 
WHERE id = ? 
ORDER BY draft_generated_at DESC;
```

## Data Integrity

### State Transitions
```sql
-- Ensure valid state transitions
CREATE TRIGGER validate_draft_status_transition
BEFORE UPDATE ON leads
FOR EACH ROW
BEGIN
    -- Validate state machine transitions
    IF NEW.draft_status = 'draft_approved' AND OLD.draft_status != 'draft_reviewing' THEN
        RAISE(ABORT, 'Invalid transition: Can only approve from reviewing state');
    END IF;
    
    -- Auto-increment revision count on regeneration
    IF NEW.draft_status = 'draft_regenerating' AND OLD.draft_status = 'draft_rejected' THEN
        SET NEW.revision_count = OLD.revision_count + 1;
    END IF;
END;
```

### Referential Integrity
```sql
-- Ensure timestamps are logical
CREATE TRIGGER validate_timestamps
BEFORE INSERT OR UPDATE ON leads
FOR EACH ROW
BEGIN
    -- approved_at requires draft_generated_at
    IF NEW.approved_at IS NOT NULL AND NEW.draft_generated_at IS NULL THEN
        RAISE(ABORT, 'Cannot approve draft without generation timestamp');
    END IF;
    
    -- rejection_reason requires rejected_at
    IF NEW.rejection_reason IS NOT NULL AND NEW.rejected_at IS NULL THEN
        RAISE(ABORT, 'Rejection reason requires rejection timestamp');
    END IF;
END;
```

## Storage Considerations

### JSON Draft Storage
- **Compression**: Consider compressing large email drafts
- **Validation**: JSON schema validation before storage
- **Versioning**: Store draft version for compatibility

### Timestamp Management
- **UTC Consistency**: All timestamps in UTC with Z suffix
- **Indexing**: Timestamp fields optimized for range queries
- **Cleanup**: Archive old drafts after approval

### Performance Optimization
- **Selective Loading**: Load only necessary fields for UI
- **Batch Operations**: Bulk status updates for multiple leads
- **Caching**: Cache recent drafts for frequent access

## Security Considerations

### Data Access
- **Review Permissions**: Only authorized users can approve/reject
- **Audit Logging**: All status changes logged
- **Data Retention**: Define cleanup policies for old drafts

### Privacy Protection
- **PII Handling**: Ensure email drafts don't contain sensitive data
- **Access Controls**: Restrict draft history viewing
- **Encryption**: Consider encrypting draft content at rest
