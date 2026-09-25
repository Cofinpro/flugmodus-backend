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
