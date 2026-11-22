"""add_managed_apps_table

Revision ID: 7a8b9c0d1e2f
Revises: 547d035c0646
Create Date: 2026-10-23 09:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7a8b9c0d1e2f'
down_revision: str | Sequence[str] | None = '547d035c0646'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema to add managed_apps table."""
    op.create_table(
        'managed_apps',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('target_path', sa.Text(), nullable=False),
        sa.Column('target_type', sa.String(length=32), nullable=False, server_default='executable'),
        sa.Column('category', sa.String(length=64), nullable=False, server_default='General'),
        sa.Column('icon_path', sa.Text(), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_available', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('last_launched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('managed_apps', schema=None) as batch_op:
        batch_op.create_index('idx_managed_apps_category', ['category'], unique=False)
        batch_op.create_index('idx_managed_apps_enabled', ['is_enabled'], unique=False)
        batch_op.create_index('idx_managed_apps_name', ['name'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('managed_apps', schema=None) as batch_op:
        batch_op.drop_index('idx_managed_apps_name')
        batch_op.drop_index('idx_managed_apps_enabled')
        batch_op.drop_index('idx_managed_apps_category')
    op.drop_table('managed_apps')
