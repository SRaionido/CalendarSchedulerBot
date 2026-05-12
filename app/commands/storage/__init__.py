"""
storage/__init__.py - Storage backend factory.

get_storage() reads config.STORAGE_BACKEND and returns the right instance.
Add new backends here as elif branches.
"""

from commands.storage.base import BaseStorage
import app.config as config


def get_storage() -> BaseStorage:
    """Return the configured storage backend instance."""
    backend = config.STORAGE_BACKEND.lower()

    if backend == "json":
        from app.commands.storage.json_storage import JsonStorage
        return JsonStorage()

    # ── Future backends (uncomment and implement to enable) ────────────────────
    # elif backend == "sqlite":
    #     from storage.sqlite_storage import SqliteStorage
    #     return SqliteStorage(path=os.path.join(config.DATA_DIR, "scheduler.db"))
    #
    # elif backend == "postgres":
    #     from storage.postgres_storage import PostgresStorage
    #     return PostgresStorage(dsn=config.DATABASE_URL)

    raise ValueError(
        f"Unknown storage backend: {backend!r}. "
        "Check STORAGE_BACKEND in your .env file."
    )