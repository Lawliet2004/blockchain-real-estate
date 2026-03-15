"""Transaction module — helpers for building property transaction payloads."""

import hashlib
import json
import time
import secrets
from typing import Any


def create_transaction_id() -> str:
    """Generate a unique transaction ID: SHA-256[:16] of timestamp + random bytes."""
    raw = f"{time.time()}{secrets.token_hex(16)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def build_transaction(
    property_id: str,
    seller_public_key: str,
    buyer_public_key: str,
    price_inr: float | None,
    transaction_type: str,
    metadata: dict[str, Any] | None = None,
    seller_signature: str = "",
) -> dict[str, Any]:
    """Assemble a complete transaction dictionary for a block.

    Args:
        property_id: Unique property identifier (e.g., 'MH-MUM-2024-00142').
        seller_public_key: PEM-encoded public key of the seller/registrar.
        buyer_public_key: PEM-encoded public key of the buyer/new owner.
        price_inr: Sale price in INR (None for registrations).
        transaction_type: One of REGISTRATION, SALE, TRANSFER, MORTGAGE.
        metadata: Property metadata (location, area, state, district, reg number).
        seller_signature: Hex-encoded digital signature of the seller.

    Returns:
        Complete transaction dict ready to be embedded in a Block.
    """
    return {
        "transaction_id": create_transaction_id(),
        "property_id": property_id,
        "seller_public_key": seller_public_key,
        "buyer_public_key": buyer_public_key,
        "price_inr": price_inr,
        "transaction_type": transaction_type,
        "metadata": metadata or {},
        "seller_signature": seller_signature,
    }


def build_signing_payload(
    property_id: str,
    buyer_public_key: str,
    price_inr: float | None,
    timestamp: float,
) -> str:
    """Build the canonical JSON string that sellers must sign.

    Uses sort_keys=True for deterministic serialization so that
    the same payload is produced on both client and server.
    """
    return json.dumps(
        {
            "property_id": property_id,
            "buyer_public_key": buyer_public_key,
            "price_inr": float(price_inr) if price_inr is not None else None,
            "timestamp": timestamp,
        },
        sort_keys=True,
    )
