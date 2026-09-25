"""Protokoll-Konstanten und reine Krypto-Hilfsfunktionen – kein FastAPI, keine DB."""

import hashlib

NUM_CANDIDATES = 100  # Kandidaten pro Abhebung, 99 werden geöffnet
NUM_PAIRS = 12  # Paare pro Münze
VALUE_BYTES = 12  # Länge von Identität, Masken, Salts, Kurz-Hashes
RSA_PUBLIC_EXPONENT = 65537
COIN_VALUE = 1  # vorerst nur 1-€-Münzen


def short_hash(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()[:VALUE_BYTES]


def xor_bytes(left: bytes, right: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(left, right))


def compute_coin_id(
    identity: bytes,
    masks: list[bytes],
    left_salts: list[bytes],
    right_salts: list[bytes],
) -> int:
    """Münz-ID als Zahl: SHA-256 über alle linken und rechten Hashes."""
    pair_hashes = b"".join(
        short_hash(masks[pair] + left_salts[pair])
        + short_hash(xor_bytes(masks[pair], identity) + right_salts[pair])
        for pair in range(NUM_PAIRS)
    )
    return int.from_bytes(hashlib.sha256(pair_hashes).digest(), "big")
