"""
SQLAlchemy session utilities for CDSS.

Supports:
- Aurora PostgreSQL IAM auth via `RDS_CONFIG_SECRET_NAME` (Secrets Manager)
- Direct `DATABASE_URL` (local dev/tests)
- SQLite support for fast local testing
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

_ENGINE = None
_SESSION_FACTORY = None


def _build_url_from_secret() -> str | None:
    """Build IAM auth URL from Secrets Manager (best-effort)."""
    secret_name = os.environ.get("RDS_CONFIG_SECRET_NAME", "").strip()
    if not secret_name:
        return None
    try:
        import boto3
        from urllib.parse import quote_plus

        region = os.environ.get("AWS_REGION", "ap-south-1")
        sm = boto3.client("secretsmanager", region_name=region)
        resp = sm.get_secret_value(SecretId=secret_name)
        raw = resp.get("SecretString", "{}")
        cfg = json.loads(raw)
        
        host = cfg.get("host")
        port = int(cfg.get("port", 5432))
        database = cfg.get("database", "cdssdb")
        username = cfg.get("username")
        if not (host and username):
            return None

        # Generate IAM auth token
        rds = boto3.client("rds", region_name=region)
        token = rds.generate_db_auth_token(DBHostname=host, Port=port, DBUsername=username)
        password = quote_plus(token)
        
        # Non-standard port or tunnel? Check environment override.
        tunnel_port = os.environ.get("TUNNEL_LOCAL_PORT")
        if tunnel_port:
            host, port = "127.0.0.1", int(tunnel_port)

        return f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}?sslmode=require"
    except Exception as e:
        logger.debug("Failed to build DB URL from secret: %s", e)
        return None


def get_engine():
    """Return cached SQLAlchemy engine; creates it if needed."""
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    db_url = os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        db_url = _build_url_from_secret() or ""

    if not db_url:
        raise RuntimeError(
            "Database not configured. Set DATABASE_URL or RDS_CONFIG_SECRET_NAME."
        )

    # Performance and stability tunings
    connect_args = {"connect_timeout": int(os.environ.get("DB_CONNECT_TIMEOUT", "3"))}

    try:
        if db_url.startswith("sqlite"):
            _ENGINE = create_engine(
                db_url,
                future=True,
                connect_args={"check_same_thread": False},
            )
        else:
            _ENGINE = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_size=int(os.environ.get("DB_POOL_SIZE", "5")),
                max_overflow=int(os.environ.get("DB_MAX_OVERFLOW", "5")),
                connect_args=connect_args,
                echo=bool(os.environ.get("SQL_ECHO")),
            )

        # Optional: perform a lightweight connectivity check so failures are logged
        test_on_init = (
            os.environ.get("DB_TEST_ON_INIT", "true").strip().lower() in {"1", "true", "yes"}
        )
        if test_on_init:
            with _ENGINE.connect() as _:
                # Connection attempt is enough to surface auth/network errors.
                pass

        return _ENGINE
    except Exception as exc:
        # Log the underlying error without leaking full connection details.
        msg = getattr(exc, "pgerror", None) or str(exc)
        logger.error("Failed to initialize database engine: %s", msg, exc_info=True)
        _ENGINE = None
        raise


@contextlib.contextmanager
def get_session() -> Iterator[Session]:
    """Yield a database session. Commit on success, rollback on exception."""
    global _SESSION_FACTORY
    if _SESSION_FACTORY is None:
        _SESSION_FACTORY = sessionmaker(
            bind=get_engine(), 
            autocommit=False, 
            autoflush=False, 
            expire_on_commit=False
        )
    
    session = _SESSION_FACTORY()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create all tables in the database."""
    from cdss.db.models import Base
    Base.metadata.create_all(get_engine())
