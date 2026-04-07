"""Memory system ORM models.

Token-based compression:
- context_window_tokens: Model context window (128k/200k/1M), None = use model default
- compress_threshold: Trigger compression at X% of context window (default 0.75)
- preserve_ratio: Keep recent X% of messages (default 0.25)
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MemorySystemConfig(Base):
    """Company-level memory configuration."""
    __tablename__ = "memory_system_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True, index=True,
    )

    # None = use model's default context window
    context_window_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compress_threshold: Mapped[float] = mapped_column(Float, default=0.75)
    preserve_ratio: Mapped[float] = mapped_column(Float, default=0.25)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('tenant_id', name='uq_memory_config_tenant'),
    )


class AgentMemoryConfig(Base):
    """Agent-level memory config override. None = inherit from company."""
    __tablename__ = "agent_memory_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )

    context_window_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    compress_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    preserve_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)

    last_compress_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_compressions: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CompressionSummary(Base):
    """Stored compression summaries."""
    __tablename__ = "compression_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    session_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    summary_text: Mapped[str] = mapped_column(String(10000), nullable=False)
    original_token_count: Mapped[int] = mapped_column(Integer, default=0)
    summary_token_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
