"""Blockchain module — manages the chain of blocks."""

from typing import Any

from blockchain.block import Block


class Blockchain:
    """Custom blockchain for recording property ownership events."""

    def __init__(self) -> None:
        self.chain: list[Block] = []
        self._create_genesis_block()

    def _create_genesis_block(self) -> None:
        """Create the first block in the chain with no real transaction."""
        genesis = Block(
            index=0,
            transaction={"transaction_type": "GENESIS", "message": "Genesis Block"},
            previous_hash="0" * 64,
            timestamp=0.0,
        )
        self.chain.append(genesis)

    def get_last_block(self) -> Block:
        """Return the most recent block in the chain."""
        return self.chain[-1]

    def add_block(self, transaction: dict[str, Any]) -> Block:
        """Create a new block with the given transaction and append it to the chain.

        Args:
            transaction: The property transaction dict to store in this block.

        Returns:
            The newly created and appended Block.
        """
        last_block = self.get_last_block()
        new_block = Block(
            index=last_block.index + 1,
            transaction=transaction,
            previous_hash=last_block.hash,
        )
        self.chain.append(new_block)
        return new_block

    def is_valid(self) -> tuple[bool, str]:
        """Validate the entire chain by checking hashes and links.

        Returns:
            Tuple of (is_valid, message). If invalid, message indicates where it broke.
        """
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # Verify current block's hash is correct
            if current.hash != current.compute_hash():
                return False, f"Block {current.index}: hash mismatch (data tampered)"

            # Verify link to previous block
            if current.previous_hash != previous.hash:
                return False, f"Block {current.index}: previous_hash link broken"

        return True, "Chain is valid"

    def get_chain(self) -> list[dict[str, Any]]:
        """Return the full chain as a list of serialized block dicts."""
        return [block.to_dict() for block in self.chain]

    def load_from_blocks(self, blocks: list[dict[str, Any]]) -> None:
        """Rebuild the in-memory chain from persisted block data.

        Args:
            blocks: List of block dicts from the database, ordered by index.
        """
        self.chain = [Block.from_dict(b) for b in blocks]
