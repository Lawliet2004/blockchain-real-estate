"""Key generation module — ECDSA secp256k1 key pair management."""

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization


def generate_keypair() -> tuple[str, str]:
    """Generate a new ECDSA secp256k1 key pair.

    Returns:
        Tuple of (private_key_pem, public_key_pem) as strings.
        Private key is NEVER to be stored server-side.
    """
    private_key = ec.generate_private_key(ec.SECP256K1())

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return private_pem, public_pem


def load_private_key(pem: str) -> ec.EllipticCurvePrivateKey:
    """Deserialize a PEM-encoded ECDSA private key."""
    return serialization.load_pem_private_key(pem.encode("utf-8"), password=None)  # type: ignore[return-value]


def load_public_key(pem: str) -> ec.EllipticCurvePublicKey:
    """Deserialize a PEM-encoded ECDSA public key."""
    return serialization.load_pem_public_key(pem.encode("utf-8"))  # type: ignore[return-value]
