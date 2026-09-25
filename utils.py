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


def verify_signature(coin_id: int, signature: int, modulus: int) -> bool:
    """Prüft eine entblindete RSA-Signatur gegen den signierten coin_id."""
    return pow(signature, RSA_PUBLIC_EXPONENT, modulus) == coin_id % modulus


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


def challenge_bits(coin_id: bytes, empfaenger_id: bytes, nonce: bytes) -> list[int]:
    """Welche Hälfte der Zahler pro Paar öffnen muss: SHA-256(coin_id ‖ empfaenger_id ‖ nonce), MSB zuerst."""
    digest = hashlib.sha256(coin_id + empfaenger_id + nonce).digest()
    return [(digest[j >> 3] >> (7 - (j & 7))) & 1 for j in range(NUM_PAIRS)]


def transcript_coin_id(
    bits: list[int], pairs: list[tuple[bytes, bytes, bytes]]
) -> bytes:
    """coin_id aus einem Transcript: geöffnete Hälfte hashen, mit dem mitgeschickten Hash zu X/Y ordnen."""
    hashes = b""
    for bit, (revealed, salt, other_hash) in zip(bits, pairs):
        opened = short_hash(revealed + salt)
        hashes += opened + other_hash if bit == 0 else other_hash + opened
    return hashlib.sha256(hashes).digest()
