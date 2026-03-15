"""Block module — defines the fundamental Block data structure for the blockchain."""

import hashlib
import json
import time
from typing import Any


class Block:
    """A single block in the blockchain containing one property transaction."""

    def __init__(
        self,
        index: int,
        transaction: dict[str, Any],
        previous_hash: str,
        timestamp: float | None = None,
        nonce: int = 0,
    ) -> None:
        self.index = index
        self.timestamp = timestamp or time.time()
        self.transaction = transaction
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of block contents. Uses sort_keys=True for determinism."""
        block_content = json.dumps(
            {
                "index": self.index,
                "timestamp": self.timestamp,
                "transaction": self.transaction,
                "previous_hash": self.previous_hash,
                "nonce": self.nonce,
            },
            sort_keys=True,
        )
        return hashlib.sha256(block_content.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        """Serialize block to a dictionary."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transaction": self.transaction,
            "previous_hash": self.previous_hash,
            "hash": self.hash,
            "nonce": self.nonce,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Block":
        """Reconstruct a Block from a dictionary (e.g., from database)."""
        block = cls(
            index=data["index"],
            transaction=data["transaction"],
            previous_hash=data["previous_hash"],
            timestamp=data["timestamp"],
            nonce=data.get("nonce", 0),
        )
        block.hash = data["hash"]
        return block
