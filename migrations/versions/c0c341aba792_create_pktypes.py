"""create pktypes

Revision ID: c0c341aba792
Revises: 8614e8d155d4
Create Date: 2026-02-10 17:10:39.999251

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime
from sqlalchemy.inspection import inspect

# revision identifiers, used by Alembic.
revision = 'c0c341aba792'
down_revision = '8614e8d155d4'
branch_labels = None
depends_on = None


def _pg_type(column_type):
    if column_type.python_type == datetime:
        if column_type.timezone:
            return "TIMESTAMP WITH TIME ZONE"
        else:
            return "TIMESTAMP"

    return str(column_type)


def _pktype_name(model):
    return f"{model.__table__.name}_pktype"


def create_pktype(model):
    mapper = inspect(model)
    type_declaration = ','.join(
        f"{c.key} {_pg_type(c.type)}" for c in mapper.primary_key
    )
    op.execute(
        f"CREATE TYPE {_pktype_name(model)} AS ({type_declaration})"
    )


def drop_pktype(model):
    op.execute(f"DROP TYPE IF EXISTS {_pktype_name(model)}")


def upgrade():
    from swpt_login import models

    create_pktype(models.ActivateUserSignal)
    create_pktype(models.DeactivateUserSignal)


def downgrade():
    from swpt_login import models

    drop_pktype(models.ActivateUserSignal)
    drop_pktype(models.DeactivateUserSignal)
