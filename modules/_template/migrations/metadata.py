"""The MetaData of this module's models: `make check-migrations` compares it with the chain.

Every table of the module is declared on `target_metadata`, which carries the module's schema, so
`Table("thing", target_metadata, ...)` lands in `{{MODULE_KEY}}.thing`. Models (`../models.py`)
import `target_metadata` from here; this file must not import anything that needs a database.
"""

import sqlalchemy as sa

target_metadata = sa.MetaData(schema="{{MODULE_KEY}}")
