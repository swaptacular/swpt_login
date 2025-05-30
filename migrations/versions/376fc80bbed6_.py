"""empty message

Revision ID: 376fc80bbed6
Revises: 
Create Date: 2025-05-04 16:51:38.079480

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '376fc80bbed6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('activate_user_signal',
    sa.Column('user_id', sa.String(length=64), nullable=False),
    sa.Column('reservation_id', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('salt', sa.String(length=32), nullable=False),
    sa.Column('password_hash', sa.String(length=128), nullable=False),
    sa.Column('recovery_code_hash', sa.String(length=128), nullable=False),
    sa.Column('registered_from_ip', postgresql.INET(), nullable=True),
    sa.Column('inserted_at', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('user_id', 'reservation_id')
    )
    op.create_table('deactivate_user_signal',
    sa.Column('user_id', sa.String(length=64), nullable=False),
    sa.Column('inserted_at', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('user_registration',
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('user_id', sa.String(length=64), nullable=False),
    sa.Column('salt', sa.String(length=32), nullable=False),
    sa.Column('password_hash', sa.String(length=128), nullable=False),
    sa.Column('recovery_code_hash', sa.String(length=128), nullable=False),
    sa.Column('registered_from_ip', postgresql.INET(), nullable=True),
    sa.Column('registered_at', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('email'),
    comment='Represents a registered user. The columns "salt", "password_hash", and "recovery_code_hash" are Base64 encoded. The "salt" column contains the salt used for the password hash. Salt\'s value may *optionally* have a "$hashing_method$" prefix, which determines the hashing method. The salt IS NOT used when calculating the "recovery_code_hash". The "recovery_code_hash" is always calculated using the default hashing method (Scrypt N=128, r=8, p=1, dklen=32), and an empty string as salt.'
    )
    with op.batch_alter_table('user_registration', schema=None) as batch_op:
        batch_op.create_index('idx_user_registration_user_id', ['user_id'], unique=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_registration', schema=None) as batch_op:
        batch_op.drop_index('idx_user_registration_user_id')

    op.drop_table('user_registration')
    op.drop_table('deactivate_user_signal')
    op.drop_table('activate_user_signal')
    # ### end Alembic commands ###
