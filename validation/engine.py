"""Validation engine — three-check pipeline for sale transactions."""

from fastapi import HTTPException

from crypto.signatures import verify_signature
from db.ledger_db import LedgerDB


class ValidationEngine:
    """Runs lock, ownership, and signature checks before accepting a sale."""

    def __init__(self, db: LedgerDB) -> None:
        self.db = db

    def check_lock(self, property_id: str) -> None:
        """Check that the property is NOT currently locked in a pending sale.

        Raises:
            HTTPException 409 if property is already locked.
        """
        if self.db.is_property_locked(property_id):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "PROPERTY_LOCKED",
                    "message": "Property is in a pending sale",
                    "status": 409,
                },
            )

    def check_ownership(self, property_id: str, seller_public_key: str) -> None:
        """Check that the seller is the current registered owner.

        Raises:
            HTTPException 404 if property not found.
            HTTPException 403 if seller is not the owner.
        """
        prop = self.db.get_property(property_id)
        if prop is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "PROPERTY_NOT_FOUND",
                    "message": f"No property found with ID: {property_id}",
                    "status": 404,
                },
            )
        if prop["owner_public_key"].strip() != seller_public_key.strip():
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "NOT_OWNER",
                    "message": "Seller is not the registered owner of this property",
                    "status": 403,
                },
            )

    def check_signature(
        self, public_key_pem: str, payload: str, signature_hex: str
    ) -> None:
        """Verify the seller's digital signature on the transaction payload.

        Raises:
            HTTPException 401 if signature is invalid.
        """
        if not verify_signature(public_key_pem, payload, signature_hex):
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "INVALID_SIGNATURE",
                    "message": "Seller signature verification failed",
                    "status": 401,
                },
            )

    def validate_sale_initiation(
        self, property_id: str, seller_public_key: str
    ) -> None:
        """Run lock + ownership checks for sale initiation (in order)."""
        self.check_lock(property_id)
        self.check_ownership(property_id, seller_public_key)

    def validate_sale_confirmation(
        self,
        property_id: str,
        seller_public_key: str,
        payload: str,
        signature_hex: str,
    ) -> None:
        """Run signature check for sale confirmation."""
        self.check_signature(seller_public_key, payload, signature_hex)
