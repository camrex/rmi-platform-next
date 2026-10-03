"""Create the {{MODULE_KEY}} schema. Tables go in later revisions (0002, ...), in this schema."""

from alembic import op

revision = "0001"
down_revision = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA "{{MODULE_KEY}}"')


def downgrade() -> None:
    op.execute('DROP SCHEMA "{{MODULE_KEY}}"')
