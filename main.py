"""FastAPI-Endpoints der Bank.  Start: uvicorn api:app --reload"""

import asyncio
import json
import os
import secrets
from collections.abc import Generator
from contextlib import asynccontextmanager
from typing import Annotated
from urllib.parse import urlencode

import segno
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, Session, SQLModel, select

import double_spend
from admin import setup_admin
from events import bus
from models import (
    Account,
    AccountPublic,
    Emission,
    Redemption,
    create_db_and_tables,
    engine,
)
from schemas import (
    Coin,
    IssueFinishRequest,
    IssueFinishResponse,
    IssueStartRequest,
    IssueStartResponse,
    RejectedCoin,
    SpendCoin,
    SyncRequest,
    SyncResponse,
    WalletCoinsRequest,
)
from utils import (
    COIN_VALUE,
    NUM_CANDIDATES,
    NUM_PAIRS,
    RSA_PUBLIC_EXPONENT,
    VALUE_BYTES,
    compute_coin_id,
    verify_signature,
)

with open("keys/keys.json") as keys_file:
    SIGNING_KEYS = {
        int(coin_value): (int(key["modulus"], 16), int(key["private_exponent"], 16))
        for coin_value, key in json.load(keys_file).items()
    }

SESSIONS = {}

load_dotenv()
# Adressen kommen aus .env (Vorlage: .env.example)
BACKEND_PUBLIC_URL = os.environ["BACKEND_PUBLIC_URL"].rstrip("/")
FRONTEND_URL = os.environ["FRONTEND_URL"].rstrip("/")
templates = Jinja2Templates(directory="templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    bus.bind_loop(asyncio.get_running_loop())
    yield


app = FastAPI(lifespan=lifespan)
app.mount("/design", StaticFiles(directory="design"), name="design")
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
    photo: str | None = Field(
        default=None, max_length=400_000
    )  # data-URL des Selfies, optional


class AccountCreated(AccountPublic):
    """Antwort auf die Anmeldung: Konto plus öffentlicher Schlüssel der Bank."""

    bank_public_key: str  # Modulus n, hex
    bank_exponent: int  # e


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
    # Registrieren: Handy-Kamera öffnet direkt die Signup-Seite der App, die Backend-Adresse reist mit.
    # Mit Schrägstrich: GitHub Pages liefert dort dist/signup/index.html ohne Umleitung aus.
    # Anmelden: wie bisher die Backend-Adresse, für den Scanner in der App.
    signup_link = f"{FRONTEND_URL}/signup/?{urlencode({'backend': BACKEND_PUBLIC_URL})}"
    qr = {
        mode: segno.make(content, error="m").svg_inline(
            scale=8, border=0, dark="#121419", omitsize=True
        )
        for mode, content in {
            "signup": signup_link,
            "signin": BACKEND_PUBLIC_URL,
        }.items()
    }
    return templates.TemplateResponse(
        request, "home.html", {"signup_qr": qr["signup"], "signin_qr": qr["signin"]}
    )


@app.post(
    "/accounts",
    response_model=AccountCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_account(account_in: AccountCreate, session: SessionDep) -> AccountCreated:
    account = Account(username=account_in.username, photo=account_in.photo)
    session.add(account)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Benutzername ist bereits vergeben"
        )
    session.refresh(account)
    bus.publish("account_created", username=account.username)
    modulus, _ = SIGNING_KEYS[COIN_VALUE]  # nur der öffentliche Teil geht raus
    return AccountCreated(
        **AccountPublic.from_account(account).model_dump(),
        bank_public_key=format(modulus, "x"),
        bank_exponent=RSA_PUBLIC_EXPONENT,
    )


@app.get("/accounts", response_model=list[AccountPublic])
def list_accounts(session: SessionDep) -> list[AccountPublic]:
    accounts = session.exec(select(Account)).all()
    return [AccountPublic.from_account(account) for account in accounts]


@app.get("/api/arrivals")
def arrivals(session: SessionDep) -> list[str]:
    """Neueste Benutzernamen für die Startseite – bewusst ohne account_id."""
    newest = select(Account.username).order_by(Account.created_at.desc()).limit(20)
    return list(session.exec(newest))


@app.get("/api/events")
async def events(request: Request) -> StreamingResponse:
    """Transaktions-Ticker für die Startseite (Server-Sent Events)."""
    last_event_id = request.headers.get("last-event-id", "")
    return StreamingResponse(
        bus.stream(int(last_event_id) if last_event_id.isdigit() else None),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
            bus.publish("cheating_detected", username=account.username)
            raise HTTPException(400, "cheating_detected")

    kept_blinded = blinded_candidates[pending["kept_candidate_index"]]
    blind_signature = pow(kept_blinded, private_exponent, modulus)
    blind_signature_hex = format(blind_signature, "0256x")

    account.balance -= pending["coin_value"]
    db_session.add(account)
    db_session.add(
        Emission(
            wallet_id=account.wallet_id,
            coin_value=pending["coin_value"],
            coin=bytes.fromhex(blind_signature_hex),
        )
    )
    db_session.commit()
    # Für den Live-Log: Fingerabdruck des VERBLENDETEN Werts – mehr sieht die Bank von der Münze nie
    bus.publish(
        "coin_issued",
        username=account.username,
        amount=pending["coin_value"],
        blinded=format(kept_blinded, "0256x")[:16],
    )

    return IssueFinishResponse(blind_signature=blind_signature_hex)


@app.post("/api/wallet/coins", response_model=list[Coin])
def wallet_coins(request: WalletCoinsRequest, session: SessionDep) -> list[Coin]:
    """Alle bisher an eine Wallet ausgegebenen Münzen (z.B. zur Wiederherstellung)."""
    wallet_id = bytes.fromhex(request.wallet_id)
    emissions = session.exec(
        select(Emission).where(Emission.wallet_id == wallet_id)
    ).all()
    return [
        Coin(coin_value=emission.coin_value, coin=emission.coin.hex())
        for emission in emissions
    ]


@app.post("/api/account/sync", response_model=SyncResponse)
def sync_account(request: SyncRequest, session: SessionDep) -> SyncResponse:
    """Bezahlte Münzen einlösen: prüfen, gutschreiben, als eingelöst vermerken."""
    wallet_id = bytes.fromhex(request.wallet_id)
    account = session.exec(
        select(Account).where(Account.wallet_id == wallet_id)
    ).first()
    if account is None:
        bus.publish("sync_failed", reason="unknown_wallet_id")
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown_wallet_id")

    if not request.coins:
        bus.publish("sync_failed", username=account.username, reason="no_coins")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no_coins")

    coin_ids_in_request = {coin.coin_id for coin in request.coins}
    if len(coin_ids_in_request) != len(request.coins):
        bus.publish(
            "sync_failed", username=account.username, reason="duplicate_coin_in_request"
        )
        raise HTTPException(status.HTTP_409_CONFLICT, "duplicate_coin_in_request")

    # Jede Münze einzeln prüfen: gültige werden gutgeschrieben, ungültige einzeln abgelehnt.
    # Früher scheiterte die ganze Einreichung an einer einzigen Münze – dann blieben auch die
    # ehrlichen Münzen hängen, und jeder neue Sync-Versuch meldete dieselbe Doppelausgabe erneut.
    accepted: list[SpendCoin] = []
    rejected: list[RejectedCoin] = []
    for coin in request.coins:
        if coin.coin_value not in SIGNING_KEYS:
            reason = "unknown_coin_value"
        elif not verify_signature(
            int(coin.coin_id, 16),
            int(coin.signature, 16),
            SIGNING_KEYS[coin.coin_value][0],
        ):
            reason = "invalid_coin"
        elif session.exec(
            select(Redemption).where(Redemption.coin_id == bytes.fromhex(coin.coin_id))
        ).first():
            reason = "coin_already_redeemed"
        else:
            accepted.append(coin)
            continue
        rejected.append(RejectedCoin(coin_id=coin.coin_id, reason=reason))

    credited = sum(coin.coin_value for coin in accepted)
    account.balance += credited
    session.add(account)
    for coin in accepted:
        session.add(
            Redemption(
                coin_id=bytes.fromhex(coin.coin_id),
                coin_value=coin.coin_value,
                wallet_id=wallet_id,
                account_id=account.account_id,
            )
        )
        # erstes Transcript merken – eine spätere Doppelausgabe lässt sich damit dem Zahler zuordnen
        double_spend.store_transcript(session, coin, wallet_id, account.account_id)
    session.commit()
    session.refresh(account)
    if accepted:
        bus.publish(
            "account_synced",
            username=account.username,
            credited=credited,
            coins=sorted(coin.coin_id for coin in accepted),
            to=wallet_id.hex(),
        )
    # Abgelehnte Münzen einer Einreichung zusammenfassen: eine Zeile pro Transaktion statt pro Münze.
    # Wird dabei eine Doppelausgabe aufgedeckt, erscheint nur sie (pro enttarntem Zahler eine Zeile,
    # mit einer Münze als Beispiel für die Erklärung).
    coins_by_id = {coin.coin_id: coin for coin in request.coins}
    exposed: dict[str, dict] = {}  # u → Ereignis
    unexplained: dict[str, list[str]] = {}  # Grund → coin_ids
    for item in rejected:
        revealed = None
        if item.reason == "coin_already_redeemed":
            # beide Transcripts da? Dann Zahler per XOR der offengelegten Hälften aufdecken
            revealed = double_spend.reveal(
                session, coins_by_id[item.coin_id], wallet_id, account
            )
        if revealed is None:
            unexplained.setdefault(item.reason, []).append(item.coin_id)
            continue
        event = exposed.setdefault(
            revealed["u"], {**revealed, "coins": [], "amount": 0}
        )
        event["coins"].append(item.coin_id)
        event["amount"] += coins_by_id[item.coin_id].coin_value
    for event in exposed.values():
        bus.publish("double_spend_detected", **event)
    if not exposed:
        for reason, coin_ids in unexplained.items():
            bus.publish(
                "sync_failed", username=account.username, reason=reason, coins=coin_ids
            )

    return SyncResponse(
        account_id=account.account_id,
        credited=credited,
        balance=account.balance,
        rejected=rejected,
    )
