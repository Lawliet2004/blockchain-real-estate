-- Blockchain Real Estate Ledger — Database Schema
-- PostgreSQL

-- Append-only chain history
CREATE TABLE IF NOT EXISTS blocks (
    id                SERIAL PRIMARY KEY,
    block_index       INTEGER NOT NULL UNIQUE,
    timestamp         DOUBLE PRECISION NOT NULL,
    previous_hash     TEXT NOT NULL,
    hash              TEXT NOT NULL UNIQUE,
    transaction_data  TEXT NOT NULL   -- JSON blob
);

-- Current ownership snapshot (changes on every sale)
CREATE TABLE IF NOT EXISTS properties (
    property_id           TEXT PRIMARY KEY,
    owner_public_key      TEXT NOT NULL,
    location              TEXT,
    area_sqft             DOUBLE PRECISION,
    state                 TEXT,
    district              TEXT,
    registration_number   TEXT,
    registered_at         DOUBLE PRECISION NOT NULL,
    last_updated          DOUBLE PRECISION NOT NULL
);

-- Active sale locks (prevents double-selling)
CREATE TABLE IF NOT EXISTS pending_sales (
    property_id           TEXT PRIMARY KEY,
    seller_public_key     TEXT NOT NULL,
    buyer_public_key      TEXT NOT NULL,
    price_inr             DOUBLE PRECISION,
    initiated_at          DOUBLE PRECISION NOT NULL,
    expires_at            DOUBLE PRECISION,
    payload_timestamp     DOUBLE PRECISION NOT NULL,
    status                TEXT DEFAULT 'pending'
                          CHECK(status IN ('pending','completed','cancelled'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_blocks_index ON blocks(block_index);
CREATE INDEX IF NOT EXISTS idx_blocks_hash ON blocks(hash);
CREATE INDEX IF NOT EXISTS idx_properties_owner ON properties(owner_public_key);
