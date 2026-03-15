"""Tests for crypto module — key generation, signing, verification."""

import json

from crypto.keys import generate_keypair, load_private_key, load_public_key
from crypto.signatures import sign_transaction, verify_signature


def test_generate_keypair():
    """Key generation must return valid PEM strings."""
    private_pem, public_pem = generate_keypair()
    assert "BEGIN PRIVATE KEY" in private_pem
    assert "BEGIN PUBLIC KEY" in public_pem


def test_load_keys_roundtrip():
    """Generated keys must be loadable back as key objects."""
    private_pem, public_pem = generate_keypair()
    priv = load_private_key(private_pem)
    pub = load_public_key(public_pem)
    assert priv is not None
    assert pub is not None


def test_sign_and_verify():
    """A valid signature must verify successfully."""
    private_pem, public_pem = generate_keypair()
    payload = json.dumps({"property_id": "TEST-001", "price": 5000000}, sort_keys=True)
    signature = sign_transaction(private_pem, payload)
    assert verify_signature(public_pem, payload, signature) is True


def test_verify_fails_on_tampered_payload():
    """Signature must fail if the payload is modified."""
    private_pem, public_pem = generate_keypair()
    payload = json.dumps({"property_id": "TEST-001", "price": 5000000}, sort_keys=True)
    signature = sign_transaction(private_pem, payload)

    tampered = json.dumps({"property_id": "TEST-001", "price": 9999999}, sort_keys=True)
    assert verify_signature(public_pem, tampered, signature) is False


def test_verify_fails_on_wrong_key():
    """Signature must fail if verified with a different public key."""
    priv1, pub1 = generate_keypair()
    _, pub2 = generate_keypair()
    payload = json.dumps({"data": "test"}, sort_keys=True)
    signature = sign_transaction(priv1, payload)
    assert verify_signature(pub2, payload, signature) is False


def test_signature_is_hex_string():
    """sign_transaction must return a hex-encoded string."""
    private_pem, _ = generate_keypair()
    sig = sign_transaction(private_pem, "test payload")
    assert all(c in "0123456789abcdef" for c in sig)


def test_different_payloads_different_signatures():
    """Different payloads must produce different signatures."""
    private_pem, _ = generate_keypair()
    sig1 = sign_transaction(private_pem, "payload_one")
    sig2 = sign_transaction(private_pem, "payload_two")
    assert sig1 != sig2
