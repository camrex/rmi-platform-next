"""A one-table chain the harness tests run; it is not part of the platform's schema."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade() -> None:
    op.create_table(
        "harness_sample",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("label", sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("harness_sample")
