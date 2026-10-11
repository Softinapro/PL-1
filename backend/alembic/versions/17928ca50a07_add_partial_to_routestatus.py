"""add partial to routestatus

Revision ID: 17928ca50a07
Revises: e5a9d9655770
Create Date: 2026-10-11 12:39:20.910793

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '17928ca50a07'
down_revision: Union[str, None] = 'e5a9d9655770'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить PARTIAL в enum routestatus."""
    op.execute("ALTER TYPE routestatus ADD VALUE IF NOT EXISTS 'PARTIAL'")


def downgrade() -> None:
    """
    PostgreSQL не поддерживает удаление значений из enum.
    Откат не реализуем без пересоздания типа.
    """
    pass