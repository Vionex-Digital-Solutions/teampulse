"""Enforce kudos.category as a DB-level CHECK constraint.

The kudos category is validated at the app layer by the ``KudosCategory`` enum
in ``app/schemas/kudos.py``. This migration adds the *same* rule as a database
CHECK constraint, so an invalid category can never be stored even if a future
code path bypasses the schema (a raw INSERT, a bug, a different client).

Applied with ``ALTER TABLE ... ADD CONSTRAINT`` — the kudos table already
exists (it was created before this rule), so editing the model + restarting
would not touch it; a migration is required. Postgres validates existing rows
when the constraint is added, so if any current row had an invalid category the
ALTER would fail and roll back (we confirmed none do before applying).

Revision ID: 0001_kudos_category_check
Revises:
"""

from alembic import op

# Keep this list in sync with KudosCategory / Kudos._ALLOWED_CATEGORIES.
_ALLOWED_CATEGORIES = (
    "teamwork",
    "innovation",
    "mentorship",
    "above_and_beyond",
    "quality",
    "communication",
)
_CATEGORY_CHECK_SQL = "category IN (" + ", ".join(f"'{c}'" for c in _ALLOWED_CATEGORIES) + ")"

# revision identifiers, used by Alembic.
revision = "0001_kudos_category_check"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the category CHECK constraint to the existing kudos table."""
    op.create_check_constraint(
        "ck_kudos_category_valid",
        "kudos",
        _CATEGORY_CHECK_SQL,
    )


def downgrade() -> None:
    """Drop the constraint (fully reversible)."""
    op.drop_constraint("ck_kudos_category_valid", "kudos", type_="check")
