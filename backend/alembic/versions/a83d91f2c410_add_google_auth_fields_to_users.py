"""add_google_auth_fields_to_users

Revision ID: a83d91f2c410
Revises: e71a982f015b
Create Date: 2026-09-03 11:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a83d91f2c410'
down_revision: Union[str, None] = 'e71a982f015b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns for Google Auth
    op.add_column('users', sa.Column('auth_provider', sa.String(length=50), server_default='email', nullable=False))
    op.add_column('users', sa.Column('google_sub', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(length=500), nullable=True))
    op.create_index(op.f('ix_users_google_sub'), 'users', ['google_sub'], unique=True)
    
    # Make hashed_password nullable
    op.alter_column('users', 'hashed_password',
               existing_type=sa.VARCHAR(length=255),
               nullable=True)


def downgrade() -> None:
    op.alter_column('users', 'hashed_password',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)
    op.drop_index(op.f('ix_users_google_sub'), table_name='users')
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'google_sub')
    op.drop_column('users', 'auth_provider')
