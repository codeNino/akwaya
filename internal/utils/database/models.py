"""
SQLAlchemy models for prospect database
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy import (
    Column,
    String,
    ARRAY,
    JSON,
    Numeric,
    Boolean,
    DateTime,
    ForeignKey,
    CheckConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Prospect(Base):
    """
    Single source of truth for each unique prospect
    """

    __tablename__ = "prospects"

    prospect_id = Column(String, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    about = Column(String, nullable=True)
    platforms = Column(ARRAY(String), default=[], server_default="{}")
    emails = Column(ARRAY(String), default=[], server_default="{}")
    phones = Column(ARRAY(String), default=[], server_default="{}")
    websites = Column(ARRAY(String), default=[], server_default="{}")
    profile_urls = Column(JSONB, default={}, server_default="{}")
    location = Column(JSONB, default={}, server_default="{}")
    discovery_confidence = Column(
        Numeric(3, 2),
        CheckConstraint(
            "discovery_confidence >= 0.00 AND discovery_confidence <= 1.00"
        ),
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    sources = relationship(
        "ProspectSource", back_populates="prospect", cascade="all, delete-orphan"
    )
    snapshots = relationship(
        "RawSnapshot", back_populates="prospect", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_prospects_discovery_confidence", "discovery_confidence"),
        Index("idx_prospects_created_at", "created_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "prospect_id": str(self.prospect_id),
            "name": self.name,
            "about": self.about,
            "platforms": self.platforms or [],
            "emails": self.emails or [],
            "phones": self.phones or [],
            "websites": self.websites or [],
            "profile_urls": self.profile_urls or {},
            "location": self.location or {},
            "discovery_confidence": (
                float(self.discovery_confidence) if self.discovery_confidence else 0.0
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ProspectSource(Base):
    """
    Track where each prospect was discovered (multiple sources possible)
    """

    __tablename__ = "prospect_sources"

    source_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prospect_id = Column(
        String,
        ForeignKey("prospects.prospect_id", ondelete="CASCADE"),
        nullable=False,
    )
    platform = Column(String(50), nullable=False)
    discovered_at = Column(DateTime, nullable=False)
    discovery_method = Column(String(100))
    raw_snapshot_id = Column(
        UUID(as_uuid=True), ForeignKey("raw_snapshots.snapshot_id", ondelete="SET NULL")
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    prospect = relationship("Prospect", back_populates="sources")
    raw_snapshot = relationship("RawSnapshot", foreign_keys=[raw_snapshot_id])

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "platform IN ('google_maps', 'linkedin')", name="check_platform"
        ),
        Index("idx_prospect_sources_prospect_id", "prospect_id"),
        Index("idx_prospect_sources_platform", "platform"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "source_id": str(self.source_id),
            "prospect_id": str(self.prospect_id),
            "platform": self.platform,
            "discovered_at": (
                self.discovered_at.isoformat() if self.discovered_at else None
            ),
            "discovery_method": self.discovery_method,
            "raw_snapshot_id": (
                str(self.raw_snapshot_id) if self.raw_snapshot_id else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class RawSnapshot(Base):
    """
    Keep original raw data for audit trail
    """

    __tablename__ = "raw_snapshots"

    snapshot_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prospect_id = Column(
        String,
        ForeignKey("prospects.prospect_id", ondelete="CASCADE"),
        nullable=False,
    )
    platform = Column(String(50), nullable=False)
    business_context = Column(String, nullable=True)
    snapshot_at = Column(DateTime, nullable=False)
    is_latest = Column(Boolean, default=True, server_default="true")
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    prospect = relationship("Prospect", back_populates="snapshots")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "platform IN ('google_maps', 'linkedin')", name="check_snapshot_platform"
        ),
        Index("idx_raw_snapshots_prospect_id", "prospect_id"),
        Index("idx_raw_snapshots_platform", "platform"),
        Index(
            "idx_raw_snapshots_is_latest",
            "is_latest",
            postgresql_where=(is_latest == True),
        ),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary with structure matching expected payload"""
        # Format snapshot_at as string (YYYY-MM-DD HH:MM:SS format)
        snapshot_at_str = None
        if self.snapshot_at:
            snapshot_at_str = self.snapshot_at.strftime('%Y-%m-%d %H:%M:%S')
        
        return {
            "snapshot_id": str(self.snapshot_id),
            "prospect_id": str(self.prospect_id),
            "platform": self.platform,
            "contact_info": {
                "email": None,
                "phone": None,
                "website": None,
            },
            "location": "",
            "business_context": self.business_context or "",
            "source_url": "",
            "snapshot_at": snapshot_at_str,
            "is_latest": self.is_latest,
        }
