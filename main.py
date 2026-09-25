"""FastAPI-Endpoints der Bank.  Start: uvicorn api:app --reload"""

import json
import secrets
from collections.abc import Generator
from contextlib import asynccontextmanager
from typing import Annotated

import segno
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, Session, SQLModel, select

from admin import setup_admin
from models import Account, AccountPublic, create_db_and_tables, engine
from schemas import (
    IssueFinishRequest,
    IssueFinishResponse,
    IssueStartRequest,
    IssueStartResponse,
)
from utils import (
    NUM_CANDIDATES,
    NUM_PAIRS,
    RSA_PUBLIC_EXPONENT,
    VALUE_BYTES,
    compute_coin_id,
)

with open("keys/keys.json") as keys_file:
    SIGNING_KEYS = {
        int(coin_value): (int(key["modulus"], 16), int(key["private_exponent"], 16))
        for coin_value, key in json.load(keys_file).items()
    }

SESSIONS = {}

PUBLIC_URL = "https://dime-claim-qualm.ngrok-free.dev"
templates = Jinja2Templates(directory="templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)
setup_admin(app, engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_session() -> Generator[Session]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


class AccountCreate(SQLModel):
    username: str = Field(min_length=1, max_length=64)


def parse_hex_values(hex_values: list[str]) -> list[bytes]:
    """Hex-Liste → Bytes; genau NUM_PAIRS Werte à VALUE_BYTES, sonst 400."""
    try:
        values = [bytes.fromhex(hex_value) for hex_value in hex_values]
    except ValueError:
        raise HTTPException(400, "bad_opening")
    if len(values) != NUM_PAIRS or any(len(value) != VALUE_BYTES for value in values):
        raise HTTPException(400, "bad_opening")
    return values


@app.get("/", response_class=HTMLResponse)
async def root(request: Request) -> HTMLResponse:
    qr_svg = segno.make(PUBLIC_URL, error="m").svg_inline(
        scale=8, border=0, dark="#121419"
    )
    return templates.TemplateResponse(request, "home.html", {"qr_svg": qr_svg})


@app.post(
    "/accounts",
    response_model=AccountPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_account(account_in: AccountCreate, session: SessionDep) -> AccountPublic:
    account = Account(username=account_in.username)
    session.add(account)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Benutzername ist bereits vergeben"
        )
    session.refresh(account)
    return AccountPublic.from_account(account)


@app.get("/accounts", response_model=list[AccountPublic])
def list_accounts(session: SessionDep) -> list[AccountPublic]:
    accounts = session.exec(select(Account)).all()
    return [AccountPublic.from_account(account) for account in accounts]


@app.get("/api/arrivals")
def arrivals(session: SessionDep) -> list[str]:
    """Neueste Benutzernamen für die Startseite – bewusst ohne account_id."""
    newest = select(Account.username).order_by(Account.created_at.desc()).limit(20)
    return list(session.exec(newest))


@app.post("/api/issue/start", response_model=IssueStartResponse)
def issue_start(request: IssueStartRequest) -> IssueStartResponse:
    session_id = secrets.token_hex(16)
    kept_candidate_index = secrets.randbelow(NUM_CANDIDATES)
    SESSIONS[session_id] = {
        "account_id": request.account_id,
        "coin_value": 1,
        "blinded_candidates": [
            int(blinded, 16) for blinded in request.blinded_candidates
        ],
        "kept_candidate_index": kept_candidate_index,
    }
    return IssueStartResponse(
        session_id=session_id, kept_candidate_index=kept_candidate_index
    )


@app.post("/api/issue/finish", response_model=IssueFinishResponse)
def issue_finish(
    request: IssueFinishRequest, db_session: SessionDep
) -> IssueFinishResponse:
    pending = SESSIONS.pop(request.session_id)  # pop: nur einmal nutzbar
    account = db_session.get(Account, pending["account_id"])
    modulus, private_exponent = SIGNING_KEYS[pending["coin_value"]]
    blinded_candidates = pending["blinded_candidates"]

    for opening in request.candidate_openings:  # mit eigener Identität nachrechnen
        coin_id = compute_coin_id(
            account.u,
            parse_hex_values(opening.masks),
            parse_hex_values(opening.left_salts),
            parse_hex_values(opening.right_salts),
        )
        blinding_factor = int(opening.blinding_factor, 16)
        reblinded = (
            coin_id * pow(blinding_factor, RSA_PUBLIC_EXPONENT, modulus) % modulus
        )
        if (
            not 1 < blinding_factor < modulus
            or reblinded != blinded_candidates[opening.candidate_index]
        ):
            raise HTTPException(400, "cheating_detected")

    account.balance -= pending["coin_value"]
    db_session.add(account)
    db_session.commit()

    kept_blinded = blinded_candidates[pending["kept_candidate_index"]]
    blind_signature = pow(kept_blinded, private_exponent, modulus)
    return IssueFinishResponse(blind_signature=format(blind_signature, "0256x"))
