"""Tests for Block class — hash integrity and serialization."""

import json
from blockchain.block import Block


def test_block_hash_deterministic():
    """Same inputs must produce the same hash."""
    b1 = Block(index=1, transaction={"key": "value"}, previous_hash="0" * 64, timestamp=1000.0)
    b2 = Block(index=1, transaction={"key": "value"}, previous_hash="0" * 64, timestamp=1000.0)
    assert b1.hash == b2.hash


def test_block_hash_changes_on_index():
    """Changing the index must change the hash."""
    b1 = Block(index=1, transaction={"a": 1}, previous_hash="0" * 64, timestamp=1000.0)
    b2 = Block(index=2, transaction={"a": 1}, previous_hash="0" * 64, timestamp=1000.0)
    assert b1.hash != b2.hash


def test_block_hash_changes_on_transaction():
    """Changing the transaction must change the hash."""
    b1 = Block(index=1, transaction={"price": 100}, previous_hash="0" * 64, timestamp=1000.0)
    b2 = Block(index=1, transaction={"price": 200}, previous_hash="0" * 64, timestamp=1000.0)
    assert b1.hash != b2.hash


def test_block_hash_changes_on_previous_hash():
    """Changing previous_hash must change the block's hash."""
    b1 = Block(index=1, transaction={}, previous_hash="a" * 64, timestamp=1000.0)
    b2 = Block(index=1, transaction={}, previous_hash="b" * 64, timestamp=1000.0)
    assert b1.hash != b2.hash


def test_block_hash_changes_on_timestamp():
    """Changing the timestamp must change the hash."""
    b1 = Block(index=1, transaction={}, previous_hash="0" * 64, timestamp=1000.0)
    b2 = Block(index=1, transaction={}, previous_hash="0" * 64, timestamp=2000.0)
    assert b1.hash != b2.hash


def test_compute_hash_matches_stored():
    """compute_hash() must match the hash stored at creation."""
    b = Block(index=5, transaction={"data": "test"}, previous_hash="f" * 64, timestamp=999.0)
    assert b.hash == b.compute_hash()


def test_to_dict_roundtrip():
    """Block.to_dict() → Block.from_dict() must preserve all fields."""
    original = Block(index=3, transaction={"id": "abc"}, previous_hash="0" * 64, timestamp=500.0, nonce=42)
    d = original.to_dict()
    restored = Block.from_dict(d)
    assert restored.index == original.index
    assert restored.timestamp == original.timestamp
    assert restored.transaction == original.transaction
    assert restored.previous_hash == original.previous_hash
    assert restored.hash == original.hash
    assert restored.nonce == original.nonce


def test_hash_is_64_hex_chars():
    """SHA-256 hash must be exactly 64 hex characters."""
    b = Block(index=0, transaction={}, previous_hash="0" * 64, timestamp=0.0)
    assert len(b.hash) == 64
    assert all(c in "0123456789abcdef" for c in b.hash)
