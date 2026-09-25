import secrets
from datetime import UTC, datetime

from sqlalchemy import inspect, text
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
    photo: str | None = Field(
        default=None
    )  # Selfie (data-URL), nur für den Steckbrief bei Doppelausgabe
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
    """Eine eingelöste Münze – verhindert, dass ein coin_id zweimal gutgeschrieben wird."""

    id: int | None = Field(default=None, primary_key=True)
    coin_id: bytes = Field(unique=True, index=True)
    coin_value: int
    wallet_id: bytes  # einreichende Wallet
    account_id: str  # gutgeschriebenes Konto
    redeemed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SpendTranscript(SQLModel, table=True):
    """Erstes Zahlungs-Transcript einer eingelösten Münze. Kommt dieselbe Münze mit einer anderen
    Challenge noch einmal, ergeben die beiden offengelegten Hälften per XOR die Identität u."""

    id: int | None = Field(default=None, primary_key=True)
    coin_id: bytes = Field(unique=True, index=True)
    wallet_id: bytes  # Empfänger (empfaenger_id) – geht in die Challenge ein
    nonce: bytes
    pairs: str  # JSON: [{"revealed", "salt", "other_hash"}, …] als Hex
    account_id: str  # Konto, das die Münze eingereicht hat
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)


# Spalten, die nach dem ersten Anlegen dazukamen. create_all legt nur fehlende TABELLEN an,
# keine Spalten – bestehende database.db-Dateien bekommen sie hier nachgetragen.
ADDED_COLUMNS = {"account": {"photo": "TEXT"}}


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    existing = inspect(engine)
    with engine.begin() as connection:
        for table, columns in ADDED_COLUMNS.items():
            present = {column["name"] for column in existing.get_columns(table)}
            for name, sql_type in columns.items():
                if name not in present:
                    connection.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")
                    )


if __name__ == "__main__":
    # mit uv run models.py
    create_db_and_tables()
