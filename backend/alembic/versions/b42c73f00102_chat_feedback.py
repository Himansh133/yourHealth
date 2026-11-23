"""Author-scoped web chat records and answer feedback.

Revision ID: b42c73f00102
Revises: 6c4b3e8f2d11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b42c73f00102"
down_revision = "6c4b3e8f2d11"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "chat_records",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("profile_id", sa.UUID(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", postgresql.JSONB(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("feedback IS NULL OR feedback IN ('helpful','too_long','wrong_evidence','missed_question')", name="chat_records_feedback_check"),
    )
    op.create_index("ix_chat_records_profile_id", "chat_records", ["profile_id"])


def downgrade():
    op.drop_index("ix_chat_records_profile_id", table_name="chat_records")
    op.drop_table("chat_records")
