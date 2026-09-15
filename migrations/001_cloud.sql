CREATE TABLE IF NOT EXISTS fm_schema (version INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS fm_runs (
    id TEXT PRIMARY KEY, owner TEXT NOT NULL, started DOUBLE PRECISION NOT NULL,
    status TEXT NOT NULL, config TEXT NOT NULL, snapshot BYTEA NOT NULL
);
CREATE INDEX IF NOT EXISTS fm_runs_owner_started ON fm_runs(owner, started DESC);
CREATE TABLE IF NOT EXISTS fm_frames (
    run_id TEXT NOT NULL REFERENCES fm_runs(id) ON DELETE CASCADE,
    tick INTEGER NOT NULL, snapshot BYTEA NOT NULL, PRIMARY KEY(run_id, tick)
);
CREATE TABLE IF NOT EXISTS fm_commands (
    owner TEXT NOT NULL, request_id TEXT NOT NULL, signature TEXT NOT NULL,
    result TEXT, created DOUBLE PRECISION NOT NULL, PRIMARY KEY(owner, request_id)
);
INSERT INTO fm_schema(version) VALUES (1) ON CONFLICT(version) DO NOTHING;
