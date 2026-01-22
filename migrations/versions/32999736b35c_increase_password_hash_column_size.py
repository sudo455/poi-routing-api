"""Increase password_hash column size

Revision ID: 32999736b35c
Revises: fcc28b416676
Create Date: 2026-01-22 16:22:46.063056

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '32999736b35c'
down_revision = 'fcc28b416676'
branch_labels = None
depends_on = None


def upgrade():
    # Increase password_hash column size for werkzeug scrypt hashes
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('password_hash',
               existing_type=sa.VARCHAR(length=128),
               type_=sa.String(length=256),
               existing_nullable=False)


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('password_hash',
               existing_type=sa.String(length=256),
               type_=sa.VARCHAR(length=128),
               existing_nullable=False)
