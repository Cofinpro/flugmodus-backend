"""Request- und Response-Typen der API. Alle Binärwerte als Hex-Strings."""

from typing import Annotated

from pydantic import BaseModel, StringConstraints

Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]+$")]


class IssueStartRequest(BaseModel):
    account_id: str
    coin_value: int = 1
    blinded_candidates: list[Hex]  # 100 × hex


class IssueStartResponse(BaseModel):
    session_id: str
    kept_candidate_index: int  # dieser Kandidat wird NICHT geöffnet


class CandidateOpening(BaseModel):
    candidate_index: int
    masks: list[Hex]  # 12 × hex
    left_salts: list[Hex]  # 12 × hex
    right_salts: list[Hex]  # 12 × hex
    blinding_factor: Hex  # hex


class IssueFinishRequest(BaseModel):
    session_id: str
    candidate_openings: list[CandidateOpening]  # 99 Stück


class IssueFinishResponse(BaseModel):
    blind_signature: Hex  # hex, 256 Zeichen (128 Byte)


class Coin(BaseModel):
    coin_value: int
    coin: Hex  # hex, 256 Zeichen (128 Byte) – die Blindsignatur


class WalletCoinsRequest(BaseModel):
    wallet_id: Hex


class RevealedPair(BaseModel):
    revealed: Hex  # geöffnete Hälfte: mask_j (Bit 0) oder mask_j ⊕ u (Bit 1), 12 Byte
    salt: Hex  # passendes Salt, 12 Byte
    other_hash: Hex  # Hash der nicht geöffneten Hälfte, 12 Byte


class SpendCoin(BaseModel):
    coin_value: int
    coin_id: Hex  # hex, der signierte Wert (32 Byte / 64 Zeichen)
    signature: Hex  # hex, entblindete RSA-Signatur (128 Byte / 256 Zeichen)
    # Zahlungs-Transcript: damit die Bank bei einer Doppelausgabe den Zahler aufdecken kann.
    # Optional, damit ältere Apps weiter einreichen können.
    nonce: Hex | None = None  # nonce der Zahlungsanfrage, 16 Byte
    pairs: list[RevealedPair] | None = None  # 12 offengelegte Paare


class SyncRequest(BaseModel):
    wallet_id: Hex  # Wallet, die die Coins beim Bezahlen bekommen hat
    coins: list[SpendCoin]


class RejectedCoin(BaseModel):
    coin_id: Hex
    reason: str  # unknown_coin_value | invalid_coin | coin_already_redeemed


class SyncResponse(BaseModel):
    account_id: str
    credited: int  # Summe der gutgeschriebenen Coin-Werte
    balance: int  # neuer Kontostand
    # Münzen, die nicht gutgeschrieben wurden – die gültigen der Einreichung zählen trotzdem
    rejected: list[RejectedCoin] = []
