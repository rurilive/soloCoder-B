"""add users table and user_id columns

Revision ID: 7d8f9a3b4c5e
Revises: 05e1c6eef966
Create Date: 2026-05-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7d8f9a3b4c5e'
down_revision: Union[str, Sequence[str], None] = '05e1c6eef966'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('users',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('username', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    
    op.add_column('categories', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'categories', 'users', ['user_id'], ['id'])
    
    op.add_column('bookmarks', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'bookmarks', 'users', ['user_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(None, 'bookmarks', type_='foreignkey')
    op.drop_column('bookmarks', 'user_id')
    
    op.drop_constraint(None, 'categories', type_='foreignkey')
    op.drop_column('categories', 'user_id')
    
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
