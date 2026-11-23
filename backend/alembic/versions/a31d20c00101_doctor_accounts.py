"""Doctor accounts and manual verification (module 20, step 1)."""
from alembic import op
import sqlalchemy as sa

revision = "a31d20c00101"
down_revision = "7ef1fa9d8cc5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("account_type", sa.Text(), nullable=False, server_default="patient"))
    op.create_check_constraint("users_account_type_check", "users", "account_type IN ('patient','doctor','admin')")
    op.create_table(
        "doctors",
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("registration_number", sa.Text(), nullable=False),
        sa.Column("registration_council", sa.Text(), nullable=False),
        sa.Column("specialty", sa.Text()),
        sa.Column("clinic_name", sa.Text()),
        sa.Column("verification_status", sa.Text(), nullable=False, server_default="unverified"),
        sa.Column("verified_by", sa.UUID(), sa.ForeignKey("users.id")),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("verification_status IN ('unverified','verified','rejected','suspended')",
                           name="doctors_verification_status_check"),
    )


def downgrade() -> None:
    op.drop_table("doctors")
    op.drop_constraint("users_account_type_check", "users", type_="check")
    op.drop_column("users", "account_type")
