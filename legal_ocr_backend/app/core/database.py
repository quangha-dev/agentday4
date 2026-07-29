from collections.abc import Generator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)

if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_database() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    if settings.database_url.startswith("sqlite"):
        existing = {column["name"] for column in inspect(engine).get_columns("documents")}
        additions = {
            "document_number": "VARCHAR(200) NOT NULL DEFAULT ''",
            "issued_date": "DATE",
            "effective_date": "DATE",
            "document_type": "VARCHAR(200) NOT NULL DEFAULT ''",
            "issuing_authority": "VARCHAR(300) NOT NULL DEFAULT ''",
            "signer": "VARCHAR(300) NOT NULL DEFAULT ''",
            "summary": "TEXT NOT NULL DEFAULT ''",
            "version_number": "INTEGER NOT NULL DEFAULT 1",
            "previous_version_id": "VARCHAR(36)",
        }
        with engine.begin() as connection:
            for column, definition in additions.items():
                if column not in existing:
                    connection.execute(text(f"ALTER TABLE documents ADD COLUMN {column} {definition}"))
        page_existing = {column["name"] for column in inspect(engine).get_columns("document_pages")}
        page_additions = {
            "ocr_engine": "VARCHAR(100)",
            "ocr_languages": "VARCHAR(100)",
        }
        with engine.begin() as connection:
            for column, definition in page_additions.items():
                if column not in page_existing:
                    connection.execute(text(f"ALTER TABLE document_pages ADD COLUMN {column} {definition}"))
