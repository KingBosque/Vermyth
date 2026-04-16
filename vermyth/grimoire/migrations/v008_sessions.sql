CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    opened_at TEXT NOT NULL,
    closed_at TEXT NULL,
    status TEXT NOT NULL,
    transport TEXT NOT NULL,
    local_identity_json TEXT NOT NULL,
    remote_identity_json TEXT NOT NULL,
    capabilities_json TEXT NOT NULL,
    last_sequence INTEGER NOT NULL DEFAULT 0,
    anchor_cast_id TEXT NULL,
    channel_branch_id TEXT NULL
);

CREATE TABLE IF NOT EXISTS session_packets (
    session_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    packet_type TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    proof TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(session_id, sequence),
    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS session_responses (
    session_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    payload_hash TEXT NOT NULL,
    accepted INTEGER NOT NULL,
    proof TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(session_id, sequence),
    FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_session_packets_session_seq
ON session_packets (session_id, sequence);

CREATE INDEX IF NOT EXISTS idx_sessions_status_opened_at
ON sessions (status, opened_at DESC);

