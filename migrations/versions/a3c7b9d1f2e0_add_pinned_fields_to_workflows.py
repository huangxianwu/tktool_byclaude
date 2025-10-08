"""add pinned fields to workflows

Revision ID: a3c7b9d1f2e0
Revises: 009380d2cc74
Create Date: 2025-10-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a3c7b9d1f2e0'
down_revision = '009380d2cc74'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('workflows', schema=None) as batch_op:
        batch_op.add_column(sa.Column('pinned', sa.Boolean(), nullable=False, server_default=sa.text('false')))
        batch_op.add_column(sa.Column('pinned_at', sa.DateTime(), nullable=True))
    # 移除server_default以避免后续模型层冲突
    with op.batch_alter_table('workflows', schema=None) as batch_op:
        batch_op.alter_column('pinned', server_default=None)


def downgrade():
    with op.batch_alter_table('workflows', schema=None) as batch_op:
        batch_op.drop_column('pinned_at')
        batch_op.drop_column('pinned')