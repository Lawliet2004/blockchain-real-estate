"""Tests for Blockchain class — chain operations and integrity."""

from blockchain.chain import Blockchain


def test_genesis_block_created():
    """A new blockchain must have exactly one genesis block."""
    bc = Blockchain()
    assert len(bc.chain) == 1
    assert bc.chain[0].index == 0
    assert bc.chain[0].previous_hash == "0" * 64


def test_add_block():
    """Adding a block must increase chain length and link correctly."""
    bc = Blockchain()
    tx = {"property_id": "TEST-001", "transaction_type": "REGISTRATION"}
    block = bc.add_block(tx)
    assert len(bc.chain) == 2
    assert block.index == 1
    assert block.previous_hash == bc.chain[0].hash
    assert block.transaction == tx


def test_add_multiple_blocks():
    """Multiple blocks must form a proper chain."""
    bc = Blockchain()
    for i in range(5):
        bc.add_block({"data": f"block_{i}"})
    assert len(bc.chain) == 6  # genesis + 5
    for i in range(1, len(bc.chain)):
        assert bc.chain[i].previous_hash == bc.chain[i - 1].hash


def test_chain_is_valid():
    """An untampered chain must pass validation."""
    bc = Blockchain()
    bc.add_block({"tx": "one"})
    bc.add_block({"tx": "two"})
    is_valid, msg = bc.is_valid()
    assert is_valid is True
    assert msg == "Chain is valid"


def test_chain_invalid_after_data_tamper():
    """Modifying a block's data must break validation."""
    bc = Blockchain()
    bc.add_block({"price": 1000})
    bc.add_block({"price": 2000})

    # Tamper with block 1's transaction
    bc.chain[1].transaction["price"] = 9999
    is_valid, msg = bc.is_valid()
    assert is_valid is False
    assert "hash mismatch" in msg


def test_chain_invalid_after_hash_tamper():
    """Modifying a block's hash must break the link to the next block."""
    bc = Blockchain()
    bc.add_block({"a": 1})
    bc.add_block({"b": 2})

    # Tamper with block 1's hash
    bc.chain[1].hash = "0" * 64
    is_valid, msg = bc.is_valid()
    assert is_valid is False


def test_get_chain_returns_dicts():
    """get_chain() must return serializable dicts."""
    bc = Blockchain()
    bc.add_block({"test": True})
    chain = bc.get_chain()
    assert isinstance(chain, list)
    assert isinstance(chain[0], dict)
    assert "hash" in chain[0]


def test_load_from_blocks():
    """Loading blocks must rebuild the chain correctly."""
    bc1 = Blockchain()
    bc1.add_block({"tx": "first"})
    bc1.add_block({"tx": "second"})
    exported = bc1.get_chain()

    bc2 = Blockchain()
    bc2.load_from_blocks(exported)
    assert len(bc2.chain) == len(bc1.chain)
    for a, b in zip(bc1.chain, bc2.chain):
        assert a.hash == b.hash
