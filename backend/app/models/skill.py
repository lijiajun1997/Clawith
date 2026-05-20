"""Global Skill registry model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# 预定义技能分类
SKILL_CATEGORIES = ["办公", "审计", "咨询", "其他"]


class Skill(Base):
    """A globally registered skill definition."""

    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(50), default="其他")
    icon: Mapped[str] = mapped_column(String(100), default="IconPackages")
    icon_type: Mapped[str] = mapped_column(String(20), default="tabler")
    folder_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Related files (SKILL.md + optional auxiliaries)
    files: Mapped[list["SkillFile"]] = relationship(back_populates="skill", cascade="all, delete-orphan")


class SkillFile(Base):
    """A file within a skill folder (e.g. SKILL.md, scripts/helper.py)."""

    __tablename__ = "skill_files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.id"), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)  # e.g. "SKILL.md" or "scripts/helper.py"
    content: Mapped[str] = mapped_column(Text, default="")

    skill: Mapped["Skill"] = relationship(back_populates="files")
