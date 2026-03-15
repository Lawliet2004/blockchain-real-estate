"""Digital signature module — sign and verify transaction payloads."""

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature

from crypto.keys import load_private_key, load_public_key


def sign_transaction(private_key_pem: str, payload: str) -> str:
    """Sign a transaction payload with an ECDSA private key.

    Args:
        private_key_pem: PEM-encoded private key string.
        payload: The canonical JSON payload string to sign.

    Returns:
        Hex-encoded signature string.
    """
    private_key = load_private_key(private_key_pem)
    signature = private_key.sign(
        payload.encode("utf-8"),
        ec.ECDSA(hashes.SHA256()),
    )
    return signature.hex()


def verify_signature(public_key_pem: str, payload: str, signature_hex: str) -> bool:
    """Verify an ECDSA signature against a public key and payload.

    Args:
        public_key_pem: PEM-encoded public key string.
        payload: The canonical JSON payload string that was signed.
        signature_hex: Hex-encoded signature to verify.

    Returns:
        True if signature is valid, False otherwise.
    """
    public_key = load_public_key(public_key_pem)
    try:
        public_key.verify(
            bytes.fromhex(signature_hex),
            payload.encode("utf-8"),
            ec.ECDSA(hashes.SHA256()),
        )
        return True
    except InvalidSignature:
        return False
