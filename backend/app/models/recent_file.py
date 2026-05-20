"""Recent file tracking model.

Lightweight table that records every file mutation (upload, write, edit,
generate, delete) across all agents.  Used by the "Recent Files" sidebar
and, in the future, by agent context injection.

Deliberately kept separate from WorkspaceFileRevision which stores full
file content for diff/rollback — here we only need metadata.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RecentFile(Base):
    __tablename__ = "recent_files"
    __table_args__ = (
        Index("ix_recent_files_agent_created", "agent_id", "created_at"),
        Index("ix_recent_files_agent_path", "agent_id", "path"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False,
    )
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    operation: Mapped[str] = mapped_column(String(20), nullable=False)  # upload|write|edit|generate|delete
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False, default="agent")  # user|agent|system
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
