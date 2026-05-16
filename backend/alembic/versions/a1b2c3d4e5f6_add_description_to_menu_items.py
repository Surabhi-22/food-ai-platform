"""add_description_to_menu_items

Revision ID: a1b2c3d4e5f6
Revises: ccb66340423c
Create Date: 2026-05-16 23:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'ccb66340423c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'menu_items',
        sa.Column('description', sa.String(length=1000), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('menu_items', 'description')
