"""Integration tests for the FastAPI REST API."""

import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a fresh TestClient with a temporary database for each test."""
    db_path = str(tmp_path / "test_ledger.db")

    # Patch LedgerDB to use temp path
    import api.main as main_module

    original_lifespan = main_module.lifespan

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def test_lifespan(app):
        from blockchain.chain import Blockchain
        from db.ledger_db import LedgerDB
        from validation.engine import ValidationEngine

        main_module.db = LedgerDB(db_path)
        main_module.blockchain = Blockchain()

        persisted_blocks = main_module.db.get_all_blocks()
        if persisted_blocks:
            main_module.blockchain.load_from_blocks(persisted_blocks)

        main_module.validator = ValidationEngine(main_module.db)
        yield
        main_module.db.close()

    main_module.app.router.lifespan_context = test_lifespan

    with TestClient(main_module.app) as c:
        yield c

    # Restore original lifespan
    main_module.app.router.lifespan_context = original_lifespan


@pytest.fixture
def keypair():
    """Generate a fresh ECDSA key pair."""
    from crypto.keys import generate_keypair
    return generate_keypair()


@pytest.fixture
def registered_property(client, keypair):
    """Register a property and return its data."""
    _, pub = keypair
    res = client.post("/register-property", json={
        "property_id": "MH-MUM-2024-00142",
        "owner_public_key": pub,
        "location": "Flat 4B, Lodha Altamount, Mumbai",
        "area_sqft": 1200,
        "state": "Maharashtra",
        "district": "Mumbai",
        "registration_number": "MH-REG-2024-556677",
    })
    assert res.status_code == 201
    return res.json()


# ── Key Generation ───────────────────────────────────────────────────

def test_generate_keys(client):
    """POST /generate-keys should return a valid key pair."""
    res = client.post("/generate-keys")
    assert res.status_code == 200
    data = res.json()
    assert "BEGIN PRIVATE KEY" in data["private_key"]
    assert "BEGIN PUBLIC KEY" in data["public_key"]


# ── Property Registration ────────────────────────────────────────────

def test_register_property(client, keypair):
    """POST /register-property should create a property and return block info."""
    _, pub = keypair
    res = client.post("/register-property", json={
        "property_id": "TEST-REG-001",
        "owner_public_key": pub,
        "location": "Test Location",
        "state": "TestState",
        "district": "TestDistrict",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["property_id"] == "TEST-REG-001"
    assert "block_hash" in data


def test_register_duplicate_property(client, keypair, registered_property):
    """Registering the same property twice should return 409."""
    _, pub = keypair
    res = client.post("/register-property", json={
        "property_id": "MH-MUM-2024-00142",
        "owner_public_key": pub,
    })
    assert res.status_code == 409


# ── Property Lookup ──────────────────────────────────────────────────

def test_get_property(client, keypair, registered_property):
    """GET /property/{id} should return property details."""
    _, pub = keypair
    res = client.get("/property/MH-MUM-2024-00142")
    assert res.status_code == 200
    data = res.json()
    assert data["property_id"] == "MH-MUM-2024-00142"
    assert data["owner_public_key"] == pub


def test_get_property_not_found(client):
    """GET /property/{id} should return 404 for nonexistent property."""
    res = client.get("/property/NONEXISTENT-999")
    assert res.status_code == 404


# ── Ownership Verification ───────────────────────────────────────────

def test_verify_owner_true(client, keypair, registered_property):
    """GET /verify-owner/{id} should return is_verified=True for real owner."""
    from urllib.parse import quote
    _, pub = keypair
    res = client.get(f"/verify-owner/MH-MUM-2024-00142?public_key={quote(pub)}")
    assert res.status_code == 200
    assert res.json()["is_verified"] is True


def test_verify_owner_false(client, keypair, registered_property):
    """GET /verify-owner/{id} should return is_verified=False for wrong key."""
    from urllib.parse import quote
    from crypto.keys import generate_keypair
    _, other_pub = generate_keypair()
    res = client.get(f"/verify-owner/MH-MUM-2024-00142?public_key={quote(other_pub)}")
    assert res.status_code == 200
    assert res.json()["is_verified"] is False


# ── Sale Flow ────────────────────────────────────────────────────────

def test_full_sale_flow(client, keypair, registered_property):
    """Complete sale flow: initiate → sign → confirm → verify new owner."""
    from crypto.keys import generate_keypair as gen_keys
    from crypto.signatures import sign_transaction
    from blockchain.transaction import build_signing_payload

    seller_priv, seller_pub = keypair
    _, buyer_pub = gen_keys()

    # 1. Initiate sale
    res = client.post("/initiate-sale", json={
        "property_id": "MH-MUM-2024-00142",
        "seller_public_key": seller_pub,
        "buyer_public_key": buyer_pub,
        "price_inr": 5000000,
    })
    assert res.status_code == 200
    sale_data = res.json()
    payload_timestamp = sale_data["payload_timestamp"]

    # 2. Sign the payload client-side
    signing_payload = build_signing_payload(
        property_id="MH-MUM-2024-00142",
        buyer_public_key=buyer_pub,
        price_inr=5000000,
        timestamp=payload_timestamp,
    )
    signature = sign_transaction(seller_priv, signing_payload)

    # 3. Confirm sale
    res = client.post("/confirm-sale", json={
        "property_id": "MH-MUM-2024-00142",
        "seller_public_key": seller_pub,
        "buyer_public_key": buyer_pub,
        "price_inr": 5000000,
        "seller_signature": signature,
    })
    assert res.status_code == 201
    confirm_data = res.json()
    assert confirm_data["new_owner"] == buyer_pub

    # 4. Verify new owner
    res = client.get("/property/MH-MUM-2024-00142")
    assert res.json()["owner_public_key"] == buyer_pub


def test_initiate_sale_not_owner(client, keypair, registered_property):
    """Initiating a sale as a non-owner should return 403."""
    from crypto.keys import generate_keypair as gen_keys
    _, fake_pub = gen_keys()
    _, buyer_pub = gen_keys()

    res = client.post("/initiate-sale", json={
        "property_id": "MH-MUM-2024-00142",
        "seller_public_key": fake_pub,
        "buyer_public_key": buyer_pub,
        "price_inr": 1000000,
    })
    assert res.status_code == 403


def test_double_sell_rejected(client, keypair, registered_property):
    """Second initiate-sale for a locked property should return 409."""
    from crypto.keys import generate_keypair as gen_keys
    _, seller_pub = keypair
    _, buyer1 = gen_keys()
    _, buyer2 = gen_keys()

    # First sale — should succeed
    res = client.post("/initiate-sale", json={
        "property_id": "MH-MUM-2024-00142",
        "seller_public_key": seller_pub,
        "buyer_public_key": buyer1,
        "price_inr": 5000000,
    })
    assert res.status_code == 200

    # Second sale — should be rejected
    res = client.post("/initiate-sale", json={
        "property_id": "MH-MUM-2024-00142",
        "seller_public_key": seller_pub,
        "buyer_public_key": buyer2,
        "price_inr": 5000000,
    })
    assert res.status_code == 409


def test_cancel_sale(client, keypair, registered_property):
    """Cancelling a sale should release the lock."""
    from crypto.keys import generate_keypair as gen_keys
    _, seller_pub = keypair
    _, buyer_pub = gen_keys()

    client.post("/initiate-sale", json={
        "property_id": "MH-MUM-2024-00142",
        "seller_public_key": seller_pub,
        "buyer_public_key": buyer_pub,
        "price_inr": 5000000,
    })

    res = client.delete("/cancel-sale/MH-MUM-2024-00142")
    assert res.status_code == 200

    # Should be able to initiate again
    res = client.post("/initiate-sale", json={
        "property_id": "MH-MUM-2024-00142",
        "seller_public_key": seller_pub,
        "buyer_public_key": buyer_pub,
        "price_inr": 5000000,
    })
    assert res.status_code == 200


# ── Property History ─────────────────────────────────────────────────

def test_property_history(client, keypair, registered_property):
    """GET /property/{id}/history should return the registration event."""
    res = client.get("/property/MH-MUM-2024-00142/history")
    assert res.status_code == 200
    data = res.json()
    assert data["total_transfers"] >= 1
    assert data["history"][0]["transaction_type"] == "REGISTRATION"


# ── Chain Validation ─────────────────────────────────────────────────

def test_chain_validate(client, registered_property):
    """GET /chain/validate should return valid for an untampered chain."""
    res = client.get("/chain/validate")
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
