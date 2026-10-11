"""add partial to routestatus

Revision ID: e5a9d9655770
Revises: e074509c7497
Create Date: 2026-10-11 12:38:43.739044

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5a9d9655770'
down_revision: Union[str, None] = 'e074509c7497'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
