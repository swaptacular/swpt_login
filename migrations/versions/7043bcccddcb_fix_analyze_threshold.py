"""fix analyze threshold

Revision ID: 7043bcccddcb
Revises: c0c341aba792
Create Date: 2026-02-14 13:31:46.049326

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7043bcccddcb'
down_revision = 'c0c341aba792'
branch_labels = None
depends_on = None


def set_storage_params(table, **kwargs):
    storage_params = ', '.join(
        f"{param} = {str(value).lower()}" for param, value in kwargs.items()
    )
    op.execute(f"ALTER TABLE {table} SET ({storage_params})")


def reset_storage_params(table, param_names):
    op.execute(f"ALTER TABLE {table} RESET ({', '.join(param_names)})")


def upgrade():
    reset_storage_params(
        'activate_user_signal',
        [
            'autovacuum_analyze_threshold',
        ]
    )
    reset_storage_params(
        'deactivate_user_signal',
        [
            'autovacuum_analyze_threshold',
        ]
    )


def downgrade():
    set_storage_params(
        'activate_user_signal',
        autovacuum_analyze_threshold=2000000000,
    )
    set_storage_params(
        'deactivate_user_signal',
        autovacuum_analyze_threshold=2000000000,
    )
