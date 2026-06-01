"""initial_schema

Revision ID: 0001
Revises:
Create Date: 2026-06-01

Creates all application tables on a fresh database using SQLAlchemy's
create_all so foreign-key ordering is handled automatically.
Existing tables are skipped (checkfirst=True), making this idempotent.
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    import importlib
    import pkgutil

    # Register every model on Base.metadata before create_all
    import backend.app.core.models  # noqa: F401 — User / Role / Tenant
    import backend.app.models as _models_pkg
    from backend.app.models.base import Base

    for _mod in pkgutil.iter_modules(list(_models_pkg.__path__)):
        if _mod.name != "base":
            importlib.import_module(f"backend.app.models.{_mod.name}")

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    import importlib
    import pkgutil

    import backend.app.core.models  # noqa: F401
    import backend.app.models as _models_pkg
    from backend.app.models.base import Base

    for _mod in pkgutil.iter_modules(list(_models_pkg.__path__)):
        if _mod.name != "base":
            importlib.import_module(f"backend.app.models.{_mod.name}")

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
