import secrets
from datetime import UTC, datetime

from sqlmodel import Field, SQLModel, create_engine


class Account(SQLModel, table=True):
    account_id: str = Field(
        default_factory=lambda: secrets.token_urlsafe(16), primary_key=True
    )
    username: str
    u: bytes = Field(
        default_factory=lambda: secrets.token_bytes(12), unique=True, index=True
    )
    wallet_id: bytes = Field(
        default_factory=lambda: secrets.token_bytes(8), unique=True, index=True
    )
    balance: int = Field(default=100, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Emission(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)


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
