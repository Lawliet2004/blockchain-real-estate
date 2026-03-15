"""Tests for ValidationEngine — lock, ownership, and signature checks."""

import json
import os
import pytest
from fastapi import HTTPException

from crypto.keys import generate_keypair
from crypto.signatures import sign_transaction
from db.ledger_db import LedgerDB
from validation.engine import ValidationEngine


@pytest.fixture
def setup():
    """Create a fresh DB + validator for each test."""
    db_path = "test_validation.db"
    db = LedgerDB(db_path)
    validator = ValidationEngine(db)
    priv, pub = generate_keypair()

    # Register a test property
    db.register_property(
        property_id="TEST-001",
        owner_public_key=pub,
        location="Test Location",
        area_sqft=1000.0,
        state="TestState",
        district="TestDistrict",
    )

    yield db, validator, priv, pub

    db.close()
    if os.path.exists(db_path):
        os.remove(db_path)


def test_lock_check_passes_when_not_locked(setup):
    """Lock check should pass for an unlocked property."""
    db, validator, _, _ = setup
    validator.check_lock("TEST-001")  # Should not raise


def test_lock_check_fails_when_locked(setup):
    """Lock check should raise 409 for a locked property."""
    db, validator, _, pub = setup
    _, buyer_pub = generate_keypair()
    db.create_pending_sale("TEST-001", pub, buyer_pub, 1000000.0, 1000.0)

    with pytest.raises(HTTPException) as exc_info:
        validator.check_lock("TEST-001")
    assert exc_info.value.status_code == 409


def test_ownership_check_passes_for_owner(setup):
    """Ownership check should pass for the actual owner."""
    _, validator, _, pub = setup
    validator.check_ownership("TEST-001", pub)  # Should not raise


def test_ownership_check_fails_for_non_owner(setup):
    """Ownership check should raise 403 for a non-owner."""
    _, validator, _, _ = setup
    _, fake_pub = generate_keypair()

    with pytest.raises(HTTPException) as exc_info:
        validator.check_ownership("TEST-001", fake_pub)
    assert exc_info.value.status_code == 403


def test_ownership_check_fails_for_missing_property(setup):
    """Ownership check should raise 404 for nonexistent property."""
    _, validator, _, pub = setup

    with pytest.raises(HTTPException) as exc_info:
        validator.check_ownership("NONEXISTENT-999", pub)
    assert exc_info.value.status_code == 404


def test_signature_check_passes_for_valid_signature(setup):
    """Signature check should pass for a valid ECDSA signature."""
    _, validator, priv, pub = setup
    payload = json.dumps({"property_id": "TEST-001", "price": 5000000}, sort_keys=True)
    signature = sign_transaction(priv, payload)
    validator.check_signature(pub, payload, signature)  # Should not raise


def test_signature_check_fails_for_invalid_signature(setup):
    """Signature check should raise 401 for an invalid signature."""
    _, validator, _, pub = setup
    payload = json.dumps({"property_id": "TEST-001"}, sort_keys=True)

    with pytest.raises(HTTPException) as exc_info:
        validator.check_signature(pub, payload, "deadbeef" * 16)
    assert exc_info.value.status_code == 401


def test_validate_sale_initiation(setup):
    """Full initiation validation should pass for valid owner + unlocked property."""
    _, validator, _, pub = setup
    validator.validate_sale_initiation("TEST-001", pub)  # Should not raise
