"""empty message

Revision ID: a5da48a60001
Revises: 655213bc148f
Create Date: 2022-08-15 23:10:55.981138

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a5da48a60001'
down_revision = '655213bc148f'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('registered_user_signal',
                    column_name='reservation_id',
                    type_=sa.String(255),
                    nullable=False,
                    existing_type=sa.BigInteger(),
                    existing_nullable=False)


def downgrade():
    op.alter_column('registered_user_signal',
                    column_name='reservation_id',
                    type_=sa.BigInteger(),
                    nullable=False,
                    existing_type=sa.String(),
                    existing_nullable=False,
                    postgresql_using='reservation_id::bigint')
