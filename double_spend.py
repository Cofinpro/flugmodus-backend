"""Doppelausgaben aufdecken: aus zwei Zahlungs-Transcripts derselben Münze die Identität u per XOR gewinnen.

Pro Zahlung öffnet der Zahler je Paar genau eine Hälfte – welche, bestimmt die Challenge
SHA-256(coin_id ‖ empfaenger_id ‖ nonce). Bit 0 öffnet mask_j, Bit 1 öffnet mask_j ⊕ u.
Wird dieselbe Münze bei einer zweiten Zahlung (anderer Empfänger oder andere nonce) noch einmal
ausgegeben, unterscheiden sich die Bits in einigen Paaren. Dort liegen beide Hälften vor:
mask_j ⊕ (mask_j ⊕ u) = u.
"""

import json

from sqlmodel import Session, select

from models import Account, SpendTranscript
from schemas import SpendCoin
from utils import NUM_PAIRS, VALUE_BYTES, challenge_bits, transcript_coin_id, xor_bytes


def _pairs(raw: list[dict]) -> list[tuple[bytes, bytes, bytes]]:
    return [
        (
            bytes.fromhex(p["revealed"]),
            bytes.fromhex(p["salt"]),
            bytes.fromhex(p["other_hash"]),
        )
        for p in raw
    ]


def _transcript_of(coin: SpendCoin) -> list[dict] | None:
    """Transcript aus der Einreichung, nur wenn vollständig (12 Paare à 12 Byte, nonce 16 Byte)."""
    if coin.nonce is None or coin.pairs is None or len(coin.pairs) != NUM_PAIRS:
        return None
    raw = [pair.model_dump() for pair in coin.pairs]
    try:
        if len(bytes.fromhex(coin.nonce)) != 16:
            return None
        if any(len(part) != VALUE_BYTES for pair in _pairs(raw) for part in pair):
            return None
    except ValueError:
        return None
    return raw


def _consistent(
    coin_id: bytes, wallet_id: bytes, nonce: bytes, raw: list[dict]
) -> bool:
    """Passen die offengelegten Hälften unter dieser Challenge wirklich zu genau dieser Münze?"""
    return (
        transcript_coin_id(challenge_bits(coin_id, wallet_id, nonce), _pairs(raw))
        == coin_id
    )


def store_transcript(
    session: Session, coin: SpendCoin, wallet_id: bytes, account_id: str
) -> None:
    """Nach dem Gutschreiben: erstes Transcript der Münze merken (nur wenn es zur Münze passt)."""
    raw = _transcript_of(coin)
    coin_id = bytes.fromhex(coin.coin_id)
    if raw is None or not _consistent(
        coin_id, wallet_id, bytes.fromhex(coin.nonce), raw
    ):
        return
    if session.exec(
        select(SpendTranscript).where(SpendTranscript.coin_id == coin_id)
    ).first():
        return
    session.add(
        SpendTranscript(
            coin_id=coin_id,
            wallet_id=wallet_id,
            nonce=bytes.fromhex(coin.nonce),
            pairs=json.dumps(raw),
            account_id=account_id,
        )
    )


def reveal(
    session: Session, coin: SpendCoin, wallet_id: bytes, merchant: Account
) -> dict | None:
    """Bei einer schon eingelösten Münze: Zahler aufdecken. Ergebnis ist das Event für den Live-Log,
    oder None, wenn eines der Transcripts fehlt oder nicht zur Münze passt."""
    coin_id = bytes.fromhex(coin.coin_id)
    first = session.exec(
        select(SpendTranscript).where(SpendTranscript.coin_id == coin_id)
    ).first()
    second_raw = _transcript_of(coin)
    if first is None or second_raw is None:
        return None
    first_raw = json.loads(first.pairs)
    second_nonce = bytes.fromhex(coin.nonce)
    # Niemanden auf Grundlage eines gefälschten Transcripts beschuldigen
    if not _consistent(
        coin_id, first.wallet_id, first.nonce, first_raw
    ) or not _consistent(coin_id, wallet_id, second_nonce, second_raw):
        return None

    bits_first = challenge_bits(coin_id, first.wallet_id, first.nonce)
    bits_second = challenge_bits(coin_id, wallet_id, second_nonce)
    pairs, identities = [], set()
    for j in range(NUM_PAIRS):
        a, b = first_raw[j]["revealed"], second_raw[j]["revealed"]
        entry = {
            "j": j,
            "bit_first": bits_first[j],
            "bit_second": bits_second[j],
            "revealed_first": a,
            "revealed_second": b,
        }
        if bits_first[j] != bits_second[j]:
            # eine Seite zeigt mask_j, die andere mask_j ⊕ u
            entry["xor"] = xor_bytes(bytes.fromhex(a), bytes.fromhex(b)).hex()
            identities.add(entry["xor"])
        pairs.append(entry)
    if len(identities) != 1:
        return None  # gleiche Challenge (Wahrscheinlichkeit 2⁻¹²) – dann ist nichts aufzudecken
    u = identities.pop()
    payer = session.exec(select(Account).where(Account.u == bytes.fromhex(u))).first()
    first_merchant = session.get(Account, first.account_id)
    return {
        "username": payer.username if payer else None,  # enttarnter Zahler
        "merchant": merchant.username,
        "first_merchant": first_merchant.username if first_merchant else None,
        "coin_id": coin.coin_id,
        "amount": coin.coin_value,
        "u": u,
        "first": {"wallet_id": first.wallet_id.hex(), "nonce": first.nonce.hex()},
        "second": {"wallet_id": wallet_id.hex(), "nonce": coin.nonce},
        "pairs": pairs,
    }
