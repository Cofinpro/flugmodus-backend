import secrets
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel, create_engine


class Account(SQLModel, table=True):
    account_id: str = Field(
        default_factory=lambda: secrets.token_urlsafe(16), primary_key=True
    )
    username: str = Field(unique=True, index=True)
    u: bytes = Field(
        default_factory=lambda: secrets.token_bytes(12), unique=True, index=True
    )
    wallet_id: bytes = Field(
        default_factory=lambda: secrets.token_bytes(8), unique=True, index=True
    )
    balance: int = Field(default=100, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


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


class Emission(SQLModel, table=True):
    """Eine an eine Wallet ausgegebene Münze (Ergebnis von /api/issue/finish)."""

    id: int | None = Field(default=None, primary_key=True)
    wallet_id: bytes = Field(index=True)
    coin_value: int
    coin: bytes  # Blindsignatur, 128 Byte
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Redemption(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    # mit uv run models.py
    create_db_and_tables()
