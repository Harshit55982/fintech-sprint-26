PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS farmers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS farmer_state (
    farmer_id INTEGER PRIMARY KEY,
    balance INTEGER NOT NULL DEFAULT 0,
    policy_active INTEGER NOT NULL DEFAULT 0,
    oracles TEXT NOT NULL DEFAULT '[18, 19, 17]',
    payout INTEGER,
    last_decision TEXT,
    history TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY (farmer_id) REFERENCES farmers (id) ON DELETE CASCADE
);
