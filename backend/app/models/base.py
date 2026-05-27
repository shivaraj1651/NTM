"""Shared SQLAlchemy declarative base for all NTM domain models.

Every model file must import Base from here — never call declarative_base()
in individual model files. This single Base's metadata is what Alembic reads
for autogenerate migrations.
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()
