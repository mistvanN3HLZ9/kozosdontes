-- Visszakövethető adatváltozások a parlamenti importhoz.
-- Nem tárol API tokent vagy egyéb hitelesítési adatot.
CREATE TABLE IF NOT EXISTS proposal_sync_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  proposal_id INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
  external_id TEXT NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('created','changed')),
  previous_checksum TEXT,
  current_checksum TEXT,
  recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sync_events_recent ON proposal_sync_events(recorded_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_sync_events_proposal ON proposal_sync_events(proposal_id, id DESC);

CREATE TRIGGER IF NOT EXISTS log_proposal_creation
AFTER INSERT ON proposals
BEGIN
  INSERT INTO proposal_sync_events (
    proposal_id, external_id, event_type, previous_checksum, current_checksum
  ) VALUES (NEW.id, NEW.external_id, 'created', NULL, NEW.source_checksum);
END;

CREATE TRIGGER IF NOT EXISTS log_proposal_content_change
AFTER UPDATE OF source_checksum ON proposals
WHEN OLD.source_checksum IS NOT NEW.source_checksum
BEGIN
  INSERT INTO proposal_sync_events (
    proposal_id, external_id, event_type, previous_checksum, current_checksum
  ) VALUES (NEW.id, NEW.external_id, 'changed', OLD.source_checksum, NEW.source_checksum);
END;
