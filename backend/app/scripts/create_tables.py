"""Dev bootstrap: create all SQLAlchemy tables on the configured database.

The project has no Alembic migration files, so this imports every model module
(registering tables on the shared Base.metadata) and runs create_all (checkfirst,
so existing tables are skipped). Use for local/dev only — production should use
real migrations.

Run: python -m backend.app.scripts.create_tables
"""
import asyncio
import importlib
import os
import pkgutil

from sqlalchemy.ext.asyncio import create_async_engine

import backend.app.core.models  # noqa: F401 — registers User/Role/Tenant
import backend.app.models as models_pkg
from backend.app.models.base import Base


def _import_all_models() -> None:
    for module in pkgutil.iter_modules(list(models_pkg.__path__)):
        if module.name != "base":
            importlib.import_module(f"backend.app.models.{module.name}")


async def create_all() -> list[str]:
    _import_all_models()
    database_url = os.environ["DATABASE_URL"]
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    return sorted(Base.metadata.tables.keys())


if __name__ == "__main__":
    tables = asyncio.run(create_all())
    print(f"create_all complete — {len(tables)} tables registered:")
    for name in tables:
        print(f"  - {name}")
