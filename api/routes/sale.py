"""Sale routes — initiate, confirm, and cancel property sales."""

import time

from fastapi import APIRouter, HTTPException

from api.models import (
    InitiateSaleRequest,
    InitiateSaleResponse,
    ConfirmSaleRequest,
    ConfirmSaleResponse,
)
from blockchain.transaction import build_transaction, build_signing_payload

router = APIRouter()


@router.post("/initiate-sale", response_model=InitiateSaleResponse, status_code=200)
def initiate_sale(req: InitiateSaleRequest) -> InitiateSaleResponse:
    """Lock a property and create a pending sale record.

    Returns a signing payload that the seller must sign client-side.
    """
    from api.main import db, validator

    # Validation: lock check + ownership check (in order)
    validator.validate_sale_initiation(req.property_id, req.seller_public_key)

    # Generate the payload the seller needs to sign
    payload_timestamp = time.time()
    signing_payload = build_signing_payload(
        property_id=req.property_id,
        buyer_public_key=req.buyer_public_key,
        price_inr=req.price_inr,
        timestamp=payload_timestamp,
    )

    # Lock the property
    db.create_pending_sale(
        property_id=req.property_id,
        seller_public_key=req.seller_public_key,
        buyer_public_key=req.buyer_public_key,
        price_inr=req.price_inr,
        payload_timestamp=payload_timestamp,
    )

    return InitiateSaleResponse(
        property_id=req.property_id,
        message="Sale initiated. Sign the payload with your private key and submit to /confirm-sale.",
        signing_payload=signing_payload,
        payload_timestamp=payload_timestamp,
    )


@router.post("/confirm-sale", response_model=ConfirmSaleResponse, status_code=201)
def confirm_sale(req: ConfirmSaleRequest) -> ConfirmSaleResponse:
    """Validate the seller's signature and complete the ownership transfer."""
    from api.main import blockchain, db, validator

    # Verify there is a pending sale for this property
    pending = db.get_pending_sale(req.property_id)
    if pending is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NO_PENDING_SALE",
                "message": f"No pending sale found for property: {req.property_id}",
                "status": 404,
            },
        )

    # Rebuild the signing payload using the timestamp from initiation
    signing_payload = build_signing_payload(
        property_id=req.property_id,
        buyer_public_key=req.buyer_public_key,
        price_inr=req.price_inr,
        timestamp=pending["payload_timestamp"],
    )

    # Validate signature
    validator.validate_sale_confirmation(
        property_id=req.property_id,
        seller_public_key=req.seller_public_key,
        payload=signing_payload,
        signature_hex=req.seller_signature,
    )

    # Build transaction
    prop = db.get_property(req.property_id)
    metadata = {
        "location": prop["location"] or "" if prop else "",
        "area_sqft": prop["area_sqft"] if prop else None,
        "registration_number": prop["registration_number"] or "" if prop else "",
        "state": prop["state"] or "" if prop else "",
        "district": prop["district"] or "" if prop else "",
    }

    transaction = build_transaction(
        property_id=req.property_id,
        seller_public_key=req.seller_public_key,
        buyer_public_key=req.buyer_public_key,
        price_inr=req.price_inr,
        transaction_type="SALE",
        metadata=metadata,
        seller_signature=req.seller_signature,
    )

    # Add block to chain and complete sale atomically
    new_block = blockchain.add_block(transaction)

    db.complete_sale(
        block=new_block,
        property_id=req.property_id,
        buyer_public_key=req.buyer_public_key,
    )

    return ConfirmSaleResponse(
        block_index=new_block.index,
        block_hash=new_block.hash,
        new_owner=req.buyer_public_key,
        transaction_id=transaction["transaction_id"],
    )


@router.delete("/cancel-sale/{property_id}", status_code=200)
def cancel_sale(property_id: str) -> dict:
    """Cancel a pending sale and release the property lock."""
    from api.main import db

    pending = db.get_pending_sale(property_id)
    if pending is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "NO_PENDING_SALE",
                "message": f"No pending sale found for property: {property_id}",
                "status": 404,
            },
        )

    db.remove_pending_sale(property_id)
    db.conn.commit()

    return {
        "property_id": property_id,
        "message": "Sale cancelled and property lock released",
    }
