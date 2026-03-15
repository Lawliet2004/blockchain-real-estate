"""Database module — PostgreSQL persistence for the blockchain ledger."""

import json
import os
import time
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from blockchain.block import Block


class LedgerDB:
    """Manages all PostgreSQL operations for blocks, properties, and pending sales."""

    def __init__(self, db_url: str | None = None) -> None:
        self.db_url = db_url or os.environ.get("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL must be set for PostgreSQL connection")
        
        # We don't keep a persistent connection, but we connect to init schema
        self._init_schema()

    def get_connection(self):
        """Get a fresh database connection configured for RealDictCursor."""
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def _init_schema(self) -> None:
        """Create tables from schema.sql if they don't exist."""
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, "r") as f:
            schema_sql = f.read()
            
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(schema_sql)
            conn.commit()

    # ── Block operations ──────────────────────────────────────────────

    def save_block(self, block: Block) -> None:
        """Insert a block into the blocks table."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO blocks (block_index, timestamp, previous_hash, hash, transaction_data) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (
                        block.index,
                        block.timestamp,
                        block.previous_hash,
                        block.hash,
                        json.dumps(block.transaction, sort_keys=True),
                    ),
                )
            conn.commit()

    def get_all_blocks(self) -> list[dict[str, Any]]:
        """Retrieve all blocks ordered by index."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT block_index, timestamp, previous_hash, hash, transaction_data "
                    "FROM blocks ORDER BY block_index"
                )
                rows = cursor.fetchall()
        
        blocks = []
        for row in rows:
            blocks.append({
                "index": row["block_index"],
                "timestamp": row["timestamp"],
                "previous_hash": row["previous_hash"],
                "hash": row["hash"],
                "transaction": json.loads(row["transaction_data"]),
                "nonce": 0,
            })
        return blocks

    def get_blocks_by_property(self, property_id: str) -> list[dict[str, Any]]:
        """Retrieve all blocks related to a specific property."""
        all_blocks = self.get_all_blocks()
        return [
            b for b in all_blocks
            if b["transaction"].get("property_id") == property_id
        ]

    # ── Property operations ───────────────────────────────────────────

    def register_property(
        self,
        property_id: str,
        owner_public_key: str,
        location: str | None = None,
        area_sqft: float | None = None,
        state: str | None = None,
        district: str | None = None,
        registration_number: str | None = None,
    ) -> None:
        """Insert a new property into the properties table."""
        now = time.time()
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO properties "
                    "(property_id, owner_public_key, location, area_sqft, state, district, "
                    "registration_number, registered_at, last_updated) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (property_id, owner_public_key, location, area_sqft, state, district,
                     registration_number, now, now),
                )
            conn.commit()

    def get_property(self, property_id: str) -> dict[str, Any] | None:
        """Retrieve a property by ID. Returns None if not found."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM properties WHERE property_id = %s", (property_id,)
                )
                row = cursor.fetchone()
        
        if row is None:
            return None
        return dict(row)

    def update_owner(
        self, property_id: str, new_owner_public_key: str, timestamp: float
    ) -> None:
        """Update the owner of a property."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE properties SET owner_public_key = %s, last_updated = %s "
                    "WHERE property_id = %s",
                    (new_owner_public_key, timestamp, property_id),
                )
            conn.commit()

    # ── Pending sale operations ───────────────────────────────────────

    def create_pending_sale(
        self,
        property_id: str,
        seller_public_key: str,
        buyer_public_key: str,
        price_inr: float | None,
        payload_timestamp: float,
        expires_at: float | None = None,
    ) -> None:
        """Create a pending sale lock for a property."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO pending_sales "
                    "(property_id, seller_public_key, buyer_public_key, price_inr, "
                    "initiated_at, expires_at, payload_timestamp, status) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')",
                    (property_id, seller_public_key, buyer_public_key, price_inr,
                     time.time(), expires_at, payload_timestamp),
                )
            conn.commit()

    def get_pending_sale(self, property_id: str) -> dict[str, Any] | None:
        """Retrieve a pending sale by property ID. Returns None if not found."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM pending_sales WHERE property_id = %s AND status = 'pending'",
                    (property_id,),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def remove_pending_sale(self, property_id: str) -> None:
        """Delete a pending sale record (on completion or cancellation)."""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM pending_sales WHERE property_id = %s", (property_id,)
                )
            conn.commit()

    def is_property_locked(self, property_id: str) -> bool:
        """Check if a property has an active pending sale."""
        return self.get_pending_sale(property_id) is not None

    # ── Atomic sale completion ────────────────────────────────────────

    def complete_sale(
        self,
        block: Block,
        property_id: str,
        buyer_public_key: str,
    ) -> None:
        """Atomically complete a sale: save block, update owner, remove pending lock."""
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cursor:
                    # 1. Save the new block
                    cursor.execute(
                        "INSERT INTO blocks (block_index, timestamp, previous_hash, hash, transaction_data) "
                        "VALUES (%s, %s, %s, %s, %s)",
                        (
                            block.index,
                            block.timestamp,
                            block.previous_hash,
                            block.hash,
                            json.dumps(block.transaction, sort_keys=True),
                        ),
                    )
                    # 2. Transfer ownership
                    cursor.execute(
                        "UPDATE properties SET owner_public_key = %s, last_updated = %s "
                        "WHERE property_id = %s",
                        (buyer_public_key, block.timestamp, property_id),
                    )
                    # 3. Remove pending sale lock
                    cursor.execute(
                        "DELETE FROM pending_sales WHERE property_id = %s", (property_id,)
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def close(self) -> None:
        """PostgreSQL doesn't persist connection in this class anymore."""
        pass
