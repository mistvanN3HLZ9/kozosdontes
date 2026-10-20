PRAGMA foreign_keys = ON;

-- Csak publikus parlamenti metaadatok az első fázisban.
CREATE TABLE IF NOT EXISTS proposals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  external_id TEXT NOT NULL UNIQUE,
  reference_code TEXT,
  slug TEXT NOT NULL UNIQUE,
  official_title TEXT NOT NULL,
  display_title TEXT NOT NULL,
  summary TEXT,
  category TEXT NOT NULL DEFAULT 'Egyéb',
  lifecycle_status TEXT NOT NULL DEFAULT 'unknown',
  record_kind TEXT NOT NULL DEFAULT 'official' CHECK (record_kind IN ('official','demo')),
  submitted_at TEXT,
  official_url TEXT,
  source_checksum TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_proposals_recent ON proposals(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_proposals_kind ON proposals(record_kind, updated_at DESC);

CREATE TABLE IF NOT EXISTS proposal_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  proposal_id INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
  version_label TEXT NOT NULL,
  source_checksum TEXT NOT NULL,
  document_url TEXT,
  detected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(proposal_id, source_checksum)
);

CREATE TABLE IF NOT EXISTS source_documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  proposal_id INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
  proposal_version_id INTEGER REFERENCES proposal_versions(id),
  title TEXT NOT NULL,
  source_url TEXT,
  section_label TEXT,
  content_sha256 TEXT,
  retrieved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS explanations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  proposal_id INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
  proposal_version_id INTEGER REFERENCES proposal_versions(id),
  version_number INTEGER NOT NULL,
  short_text TEXT NOT NULL,
  detailed_text TEXT NOT NULL,
  model_provider TEXT NOT NULL,
  model_id TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  review_status TEXT NOT NULL DEFAULT 'draft' CHECK (review_status IN ('draft','needs_review','published','withdrawn')),
  UNIQUE(proposal_id, version_number)
);

CREATE TABLE IF NOT EXISTS explanation_claims (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  explanation_id INTEGER NOT NULL REFERENCES explanations(id) ON DELETE CASCADE,
  claim_text TEXT NOT NULL,
  source_document_id INTEGER REFERENCES source_documents(id),
  cited_section TEXT,
  verification_status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS error_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  explanation_id INTEGER NOT NULL REFERENCES explanations(id),
  category TEXT NOT NULL,
  description TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS parliamentary_votes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  external_vote_id TEXT NOT NULL UNIQUE,
  proposal_id INTEGER REFERENCES proposals(id),
  proposal_version_id INTEGER REFERENCES proposal_versions(id),
  vote_type TEXT NOT NULL,
  voted_at TEXT,
  yes_count INTEGER,
  no_count INTEGER,
  abstain_count INTEGER,
  official_source_url TEXT
);

-- Ezek előkészített táblák, a szavazati API csak egy későbbi fázisban készül el.
CREATE TABLE IF NOT EXISTS user_profiles (
  auth_uid TEXT PRIMARY KEY,
  username TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ballots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  proposal_id INTEGER NOT NULL REFERENCES proposals(id),
  proposal_version_id INTEGER NOT NULL REFERENCES proposal_versions(id),
  opens_at TEXT NOT NULL,
  closes_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','open','closed','cancelled')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS votes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ballot_id INTEGER NOT NULL REFERENCES ballots(id),
  user_uid TEXT NOT NULL REFERENCES user_profiles(auth_uid),
  choice TEXT NOT NULL CHECK (choice IN ('yes','no','abstain')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(ballot_id, user_uid)
);
CREATE INDEX IF NOT EXISTS idx_votes_ballot_choice ON votes(ballot_id, choice);

CREATE TABLE IF NOT EXISTS topic_rounds (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  opens_at TEXT NOT NULL,
  closes_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft'
);
CREATE TABLE IF NOT EXISTS topic_preferences (
  round_id INTEGER NOT NULL REFERENCES topic_rounds(id),
  proposal_id INTEGER NOT NULL REFERENCES proposals(id),
  user_uid TEXT NOT NULL REFERENCES user_profiles(auth_uid),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (round_id, proposal_id, user_uid)
);

CREATE TABLE IF NOT EXISTS sync_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at TEXT,
  source_name TEXT NOT NULL,
  status TEXT NOT NULL,
  processed_count INTEGER NOT NULL DEFAULT 0,
  error_message TEXT
);
CREATE TABLE IF NOT EXISTS audit_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor TEXT NOT NULL,
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  details_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
