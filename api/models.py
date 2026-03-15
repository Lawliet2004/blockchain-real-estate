"""Pydantic models for API request/response validation."""

from pydantic import BaseModel


# ── Request Models ────────────────────────────────────────────────────

class RegisterPropertyRequest(BaseModel):
    """Request body for POST /register-property."""
    property_id: str
    owner_public_key: str
    location: str | None = None
    area_sqft: float | None = None
    state: str | None = None
    district: str | None = None
    registration_number: str | None = None


class InitiateSaleRequest(BaseModel):
    """Request body for POST /initiate-sale."""
    property_id: str
    seller_public_key: str
    buyer_public_key: str
    price_inr: float


class ConfirmSaleRequest(BaseModel):
    """Request body for POST /confirm-sale."""
    property_id: str
    seller_public_key: str
    buyer_public_key: str
    price_inr: float
    seller_signature: str


# ── Response Models ───────────────────────────────────────────────────

class RegisterPropertyResponse(BaseModel):
    """Response for POST /register-property."""
    block_index: int
    block_hash: str
    property_id: str
    message: str


class InitiateSaleResponse(BaseModel):
    """Response for POST /initiate-sale."""
    property_id: str
    message: str
    signing_payload: str
    payload_timestamp: float


class ConfirmSaleResponse(BaseModel):
    """Response for POST /confirm-sale."""
    block_index: int
    block_hash: str
    new_owner: str
    transaction_id: str


class PropertyResponse(BaseModel):
    """Response for GET /property/{id}."""
    property_id: str
    owner_public_key: str
    location: str | None = None
    area_sqft: float | None = None
    state: str | None = None
    district: str | None = None
    registration_number: str | None = None
    registered_at: float
    last_updated: float


class HistoryEntry(BaseModel):
    """A single entry in the property ownership history."""
    block_index: int
    timestamp: float
    transaction_type: str
    seller: str | None = None
    buyer: str | None = None
    price_inr: float | None = None


class PropertyHistoryResponse(BaseModel):
    """Response for GET /property/{id}/history."""
    property_id: str
    total_transfers: int
    history: list[HistoryEntry]


class VerifyOwnerResponse(BaseModel):
    """Response for GET /verify-owner/{id}."""
    property_id: str
    owner_public_key: str
    is_verified: bool


class ChainValidateResponse(BaseModel):
    """Response for GET /chain/validate."""
    is_valid: bool
    message: str
    total_blocks: int


class KeyPairResponse(BaseModel):
    """Response for POST /generate-keys."""
    private_key: str
    public_key: str
    warning: str


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    message: str
    status: int
