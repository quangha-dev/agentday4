"""ver2 page OCR metadata

Revision ID: c4f3a19e2b10
Revises: 6257374112e3
"""

import sqlalchemy as sa
from alembic import op

revision = "c4f3a19e2b10"
down_revision = "6257374112e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_pages", sa.Column("ocr_engine", sa.String(length=100), nullable=True))
    op.add_column("document_pages", sa.Column("ocr_languages", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("document_pages", "ocr_languages")
    op.drop_column("document_pages", "ocr_engine")
