from collections.abc import Generator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Field, Session, SQLModel

from models import Account, create_db_and_tables, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

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


class AccountPublic(SQLModel):
    account_id: str
    username: str
    u: str  # hex-kodiert
    wallet_id: str  # hex-kodiert
    balance: int
    created_at: datetime

    @classmethod
    def from_account(cls, account: Account) -> AccountPublic:
        return cls(
            account_id=account.account_id,
            username=account.username,
            u=account.u.hex(),
            wallet_id=account.wallet_id.hex(),
            balance=account.balance,
            created_at=account.created_at,
        )


@app.get("/")
async def root():
    return {"message": "Offline Bank Inc. - Your secure banking solution."}


@app.post(
    "/accounts",
    response_model=AccountPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_account(account_in: AccountCreate, session: SessionDep) -> AccountPublic:
    account = Account(username=account_in.username)
    session.add(account)
    session.commit()
    session.refresh(account)
    return AccountPublic.from_account(account)
