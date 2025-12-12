"""storage params

Revision ID: 8614e8d155d4
Revises: e61c239caaae
Create Date: 2025-12-11 14:28:10.809974

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8614e8d155d4'
down_revision = 'e61c239caaae'
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
    set_storage_params(
        'user_registration',
        fillfactor=88,
        autovacuum_vacuum_scale_factor=0.04,
        autovacuum_vacuum_insert_scale_factor=0.1,
    )
    set_storage_params(
        'activate_user_signal',
        fillfactor=100,
        autovacuum_vacuum_cost_delay=0.0,
        autovacuum_vacuum_insert_threshold=-1,
        autovacuum_analyze_threshold=2000000000,
    )
    set_storage_params(
        'deactivate_user_signal',
        fillfactor=100,
        autovacuum_vacuum_cost_delay=0.0,
        autovacuum_vacuum_insert_threshold=-1,
        autovacuum_analyze_threshold=2000000000,
    )


def downgrade():
    reset_storage_params(
        'user_registration',
        [
            'fillfactor',
            'autovacuum_vacuum_scale_factor',
            'autovacuum_vacuum_insert_scale_factor',
        ]
    )
    reset_storage_params(
        'activate_user_signal',
        [
            'fillfactor',
            'autovacuum_vacuum_cost_delay',
            'autovacuum_vacuum_insert_threshold',
            'autovacuum_analyze_threshold',
        ]
    )
    reset_storage_params(
        'deactivate_user_signal',
        [
            'fillfactor',
            'autovacuum_vacuum_cost_delay',
            'autovacuum_vacuum_insert_threshold',
            'autovacuum_analyze_threshold',
        ]
    )
