"""Add google_permission_mode to User model

Revision ID: 6a1b2c3d4e5f
Revises: 5c69053ed761_add_ai_assistant_settings_with_defaults
Create Date: 2025-09-22 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6a1b2c3d4e5f'
down_revision = '5c69053ed761'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('google_permission_mode', sa.String(length=20), nullable=False, server_default='events'))


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('google_permission_mode')
