"""FastAPI application — entry point for the Real Estate Blockchain Ledger API."""

import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.models import KeyPairResponse, ChainValidateResponse
from api.routes import property as property_routes
from api.routes import sale as sale_routes
from blockchain.chain import Blockchain
from crypto.keys import generate_keypair
from db.ledger_db import LedgerDB
from validation.engine import ValidationEngine

# ── Global state ──────────────────────────────────────────────────────
db: LedgerDB
blockchain: Blockchain
validator: ValidationEngine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and tear down application state."""
    global db, blockchain, validator

    db = LedgerDB()
    blockchain = Blockchain()

    # Reload chain from DB if blocks exist
    persisted_blocks = db.get_all_blocks()
    if persisted_blocks:
        blockchain.load_from_blocks(persisted_blocks)

    validator = ValidationEngine(db)
    yield
    db.close()


app = FastAPI(
    title="Blockchain Real Estate Ledger",
    description="Tamper-proof property ownership ledger for India",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Include route modules ─────────────────────────────────────────────
app.include_router(property_routes.router, tags=["Property"])
app.include_router(sale_routes.router, tags=["Sale"])


# ── Top-level endpoints ──────────────────────────────────────────────

@app.post("/generate-keys", response_model=KeyPairResponse)
def generate_keys() -> KeyPairResponse:
    """Generate a new ECDSA secp256k1 key pair.

    WARNING: The private key is returned ONCE and must be saved by the client.
    The server does NOT store private keys.
    """
    private_pem, public_pem = generate_keypair()
    return KeyPairResponse(
        private_key=private_pem,
        public_key=public_pem,
        warning="Save your private key securely. It will NOT be stored on the server.",
    )


@app.get("/chain/validate", response_model=ChainValidateResponse)
def validate_chain() -> ChainValidateResponse:
    """Run a full SHA-256 integrity check on the blockchain."""
    is_valid, message = blockchain.is_valid()
    return ChainValidateResponse(
        is_valid=is_valid,
        message=message,
        total_blocks=len(blockchain.chain),
    )


@app.get("/")
def root() -> dict:
    """Health check / landing page redirect."""
    return {
        "service": "Blockchain Real Estate Ledger",
        "version": "1.0.0",
        "docs": "/docs",
        "frontend": "/static/index.html",
    }


# ── Mount static files for frontend ──────────────────────────────────
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
