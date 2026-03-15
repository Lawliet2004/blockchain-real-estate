"""Property routes — registration, lookup, history, verification."""

import time

from fastapi import APIRouter, HTTPException

from api.models import (
    RegisterPropertyRequest,
    RegisterPropertyResponse,
    PropertyResponse,
    PropertyHistoryResponse,
    HistoryEntry,
    VerifyOwnerResponse,
)
from blockchain.transaction import build_transaction

router = APIRouter()


@router.post("/register-property", response_model=RegisterPropertyResponse, status_code=201)
def register_property(req: RegisterPropertyRequest) -> RegisterPropertyResponse:
    """Register a new property on the blockchain (government admin endpoint)."""
    from api.main import blockchain, db

    # Check if property already exists
    existing = db.get_property(req.property_id)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "PROPERTY_EXISTS",
                "message": f"Property {req.property_id} is already registered",
                "status": 409,
            },
        )

    metadata = {
        "location": req.location or "",
        "area_sqft": req.area_sqft,
        "registration_number": req.registration_number or "",
        "state": req.state or "",
        "district": req.district or "",
    }

    transaction = build_transaction(
        property_id=req.property_id,
        seller_public_key="GOVERNMENT_AUTHORITY",
        buyer_public_key=req.owner_public_key,
        price_inr=None,
        transaction_type="REGISTRATION",
        metadata=metadata,
    )

    # Add block to chain
    new_block = blockchain.add_block(transaction)

    # Save block to DB
    db.save_block(new_block)

    # Register property in properties table
    db.register_property(
        property_id=req.property_id,
        owner_public_key=req.owner_public_key,
        location=req.location,
        area_sqft=req.area_sqft,
        state=req.state,
        district=req.district,
        registration_number=req.registration_number,
    )

    return RegisterPropertyResponse(
        block_index=new_block.index,
        block_hash=new_block.hash,
        property_id=req.property_id,
        message="Property registered on blockchain",
    )


@router.get("/property/{property_id}", response_model=PropertyResponse)
def get_property(property_id: str) -> PropertyResponse:
    """Get current property details and owner."""
    from api.main import db

    prop = db.get_property(property_id)
    if prop is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "PROPERTY_NOT_FOUND",
                "message": f"No property found with ID: {property_id}",
                "status": 404,
            },
        )

    return PropertyResponse(**prop)


@router.get("/property/{property_id}/history", response_model=PropertyHistoryResponse)
def get_property_history(property_id: str) -> PropertyHistoryResponse:
    """Get the full ownership history of a property from the blockchain."""
    from api.main import db

    # Verify property exists
    prop = db.get_property(property_id)
    if prop is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "PROPERTY_NOT_FOUND",
                "message": f"No property found with ID: {property_id}",
                "status": 404,
            },
        )

    blocks = db.get_blocks_by_property(property_id)
    history: list[HistoryEntry] = []

    for block in blocks:
        tx = block["transaction"]
        entry = HistoryEntry(
            block_index=block["index"],
            timestamp=block["timestamp"],
            transaction_type=tx.get("transaction_type", "UNKNOWN"),
            seller=tx.get("seller_public_key"),
            buyer=tx.get("buyer_public_key"),
            price_inr=tx.get("price_inr"),
        )
        history.append(entry)

    return PropertyHistoryResponse(
        property_id=property_id,
        total_transfers=len(history),
        history=history,
    )


@router.get("/verify-owner/{property_id}", response_model=VerifyOwnerResponse)
def verify_owner(property_id: str, public_key: str = "") -> VerifyOwnerResponse:
    """Verify if a public key is the current owner of a property."""
    from api.main import db

    prop = db.get_property(property_id)
    if prop is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "PROPERTY_NOT_FOUND",
                "message": f"No property found with ID: {property_id}",
                "status": 404,
            },
        )

    is_verified = False
    if public_key:
        is_verified = prop["owner_public_key"].strip() == public_key.strip()

    return VerifyOwnerResponse(
        property_id=property_id,
        owner_public_key=prop["owner_public_key"],
        is_verified=is_verified,
    )
