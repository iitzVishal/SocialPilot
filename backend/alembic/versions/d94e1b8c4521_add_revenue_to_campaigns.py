"""add_revenue_to_campaigns

Revision ID: d94e1b8c4521
Revises: a83d91f2c410
Create Date: 2026-09-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd94e1b8c4521'
down_revision: Union[str, None] = 'a83d91f2c410'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('campaigns', sa.Column('revenue', sa.Float(), nullable=True, server_default='0.0'))


def downgrade() -> None:
    op.drop_column('campaigns', 'revenue')
