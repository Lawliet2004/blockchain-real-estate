---
name: blockchain-real-estate-ledger
description: >
  Expert guidance for building a blockchain-based real estate ledger management
  system for house buying and selling in India. Use this skill whenever the user
  asks to build, extend, debug, or explain any part of this project — including
  block structure, SHA-256 hashing, digital signature implementation, validation
  engine logic, SQLite schema design, FastAPI endpoints, ACID transaction patterns,
  double-sell prevention, chain tamper detection, or frontend dashboard. Also
  trigger for questions about cryptographic key generation (ECDSA/RSA), ownership
  transfer flow, property registration, error handling, security threat modeling,
  testing with pytest, or deployment. Use even when the user asks conceptual
  questions like "how does the sale flow work" or "how do I prevent fraud" — this
  skill contains the full architecture and domain context needed to answer precisely.
---

# Blockchain Real Estate Ledger — Project Skill

## Project Summary

A tamper-proof, cryptographically secured digital ledger for recording property
ownership events (registration, sale, transfer) in India. Custom-built blockchain
in Python — not Ethereum. Single-node prototype.

**Stack:** Python 3.10+ · FastAPI · SQLite · `cryptography` library · React/HTML

---

## Architecture (Quick Reference)

```
Layer 5 → Frontend (React/HTML)         Property dashboard, sale forms
Layer 4 → FastAPI REST API              9 endpoints (see API section)
Layer 3 → Validation Engine             Signature · Ownership · Lock checks
Layer 2 → Blockchain Core               Block, Chain, SHA-256 hashing
Layer 1 → SQLite Database               blocks · properties · pending_sales
```

---

## Core File Structure

```
project/
├── blockchain/
│   ├── block.py              # Block class — fields, compute_hash()
│   ├── chain.py              # Blockchain class — add_block(), is_valid()
│   └── transaction.py        # PropertyTransaction model
├── crypto/
│   ├── keys.py               # generate_keypair(), load_key()
│   └── signatures.py         # sign_transaction(), verify_signature()
├── db/
│   ├── schema.sql            # CREATE TABLE statements
│   └── ledger_db.py          # LedgerDB class — all DB operations
├── validation/
│   └── engine.py             # ValidationEngine — 3 checks
├── api/
│   ├── main.py               # FastAPI app entry point
│   ├── routes/
│   │   ├── property.py       # /register-property, /property/{id}
│   │   └── sale.py           # /initiate-sale, /confirm-sale, /cancel-sale
│   └── models.py             # Pydantic request/response schemas
├── frontend/
│   └── index.html            # Dashboard UI
└── tests/
    ├── test_block.py
    ├── test_validation.py
    └── test_api.py
```

---

## Block Structure

Every block stores exactly one ownership event:

```python
{
  "index": int,
  "timestamp": float,               # Unix epoch — time.time()
  "transaction": {
    "transaction_id": str,          # SHA-256[:16] — unique dedup key
    "property_id": str,             # e.g. "MH-MUM-2024-00142"
    "seller_public_key": str,       # PEM string
    "buyer_public_key": str,
    "price_inr": float,
    "transaction_type": str,        # REGISTRATION | SALE | TRANSFER
    "metadata": { location, area_sqft, state, district, registration_number },
    "seller_signature": str         # Hex-encoded ECDSA/RSA signature
  },
  "previous_hash": str,             # SHA-256 of previous block (64 hex chars)
  "hash": str,                      # SHA-256 of THIS block's full content
  "nonce": int                      # Optional — Proof of Work
}
```

**Critical:** `json.dumps(..., sort_keys=True)` is mandatory for deterministic hashing.

---

## Database Schema

```sql
-- Append-only chain history
CREATE TABLE blocks (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    block_index       INTEGER NOT NULL UNIQUE,
    timestamp         REAL NOT NULL,
    previous_hash     TEXT NOT NULL,
    hash              TEXT NOT NULL UNIQUE,
    transaction_data  TEXT NOT NULL        -- JSON blob
);

-- Current ownership snapshot (changes on every sale)
CREATE TABLE properties (
    property_id           TEXT PRIMARY KEY,
    owner_public_key      TEXT NOT NULL,
    location              TEXT,
    area_sqft             REAL,
    state                 TEXT,
    district              TEXT,
    registration_number   TEXT,
    registered_at         REAL NOT NULL,
    last_updated          REAL NOT NULL
);

-- Active sale locks (prevents double-selling)
CREATE TABLE pending_sales (
    property_id           TEXT PRIMARY KEY,
    seller_public_key     TEXT NOT NULL,
    buyer_public_key      TEXT NOT NULL,
    initiated_at          REAL NOT NULL,
    expires_at            REAL,
    status                TEXT DEFAULT 'pending'
                          CHECK(status IN ('pending','completed','cancelled'))
);
```

**Rule:** All three tables must update inside one `BEGIN`/`COMMIT` transaction block on sale completion. If any step fails → `ROLLBACK`.

---

## Validation Engine (Three Checks)

Run in this exact order before accepting any sale:

```
1. LOCK CHECK      → Is property_id in pending_sales?       → HTTP 409 if yes
2. OWNERSHIP CHECK → Does seller_pubkey == properties[id].owner?  → HTTP 403 if no
3. SIGNATURE CHECK → Is ECDSA/RSA signature cryptographically valid? → HTTP 401 if invalid
```

Never reorder. Lock check first is intentional — it short-circuits before expensive crypto.

---

## Cryptography

**Algorithm:** ECDSA secp256k1 (preferred) or RSA-2048
**Library:** `pip install cryptography`

```python
# Signing (client-side — NEVER server-side)
payload = json.dumps({"property_id": ..., "buyer": ..., "price": ...}, sort_keys=True)
signature = private_key.sign(payload.encode(), ec.ECDSA(hashes.SHA256()))

# Verifying (server-side)
try:
    public_key.verify(bytes.fromhex(sig), payload.encode(), ec.ECDSA(hashes.SHA256()))
except InvalidSignature:
    raise HTTP 401
```

**Hard rules:**
- Private key NEVER leaves the client
- Public key IS the user's identity on chain
- Signing payload must match verification payload exactly (sort_keys=True both sides)

---

## API Endpoints

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | /register-property | Admin JWT | Seed initial ownership on chain |
| POST | /generate-keys | None | Return new public/private key pair |
| POST | /initiate-sale | None | Lock property, create pending record |
| POST | /confirm-sale | None | Validate + create block + transfer ownership |
| DELETE | /cancel-sale/{id} | None | Release lock |
| GET | /property/{id} | None | Current owner + metadata |
| GET | /property/{id}/history | None | Full chain replay for property |
| GET | /verify-owner/{id} | None | Boolean check (for banks/lawyers) |
| GET | /chain/validate | Admin | Full SHA-256 integrity check |

---

## Sale Transaction Flow (Step by Step)

```
POST /initiate-sale
  → LockValidator: property in pending_sales? → 409 if yes
  → OwnershipValidator: seller == current owner? → 403 if no
  → INSERT into pending_sales
  → Return transaction_payload to client

[Client signs payload with private key]

POST /confirm-sale + signature
  → SignatureValidator: valid ECDSA/RSA sig? → 401 if invalid
  → BEGIN DB TRANSACTION
      INSERT INTO blocks
      UPDATE properties SET owner = buyer
      DELETE FROM pending_sales
  → COMMIT
  → Return 201 with new block_hash
```

---

## Error Response Format

Always return structured JSON:

```json
{ "error": "PROPERTY_LOCKED",   "message": "...", "status": 409 }
{ "error": "NOT_OWNER",         "message": "...", "status": 403 }
{ "error": "INVALID_SIGNATURE", "message": "...", "status": 401 }
{ "error": "PROPERTY_NOT_FOUND","message": "...", "status": 404 }
{ "error": "CHAIN_INVALID",     "message": "...", "status": 500 }
```

---

## Security Threat Model (Summary)

| Threat | Mitigation |
|---|---|
| Fake ownership claim | Signature check — impossible without private key |
| Double-selling | pending_sales UNIQUE lock — second request → 409 |
| Chain tampering | SHA-256 hash chain — any edit breaks all downstream hashes |
| Replay attack | Unique transaction_id + timestamp per transaction |
| Concurrent lock race | SQLite UNIQUE constraint on pending_sales.property_id |

---

## Testing Checklist (pytest)

Must cover:
- [ ] Block hash changes when any field changes
- [ ] Chain `is_valid()` returns False after tampering any block
- [ ] Signature verification fails on tampered payload
- [ ] Initiate-sale rejected when property already locked
- [ ] Confirm-sale rejected when seller is not owner
- [ ] ATOMIC: if block save fails, ownership table is NOT updated
- [ ] `/property/{id}/history` returns blocks in correct order

---

## Property ID Format

Recommended: `{STATE_CODE}-{DISTRICT_CODE}-{YEAR}-{SEQ}`
Example: `MH-MUM-2024-00142`

This allows filtering by state/district without a full scan.

---

## Known Limitations (Prototype Scope)

- Single-node only — no P2P consensus
- No Proof of Work
- SQLite not suited for concurrent writes at scale
- No private key recovery mechanism
- No legal enforceability without Registration Act amendment
- Public key ≠ verified real identity (no Aadhaar/DigiLocker integration)

## Out of Scope

Ethereum/Solidity · IPFS · P2P networking · PoW mining · DigiLocker API ·
Flutter mobile app · Token economics · Multi-signature transactions
