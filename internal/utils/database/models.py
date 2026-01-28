"""
SQLAlchemy models for prospect database
"""

import uuid
from typing import Dict, Any
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    ARRAY,
    Boolean,
    DateTime,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Prospect(Base):
    """
    Single source of truth for each unique prospect
    """

    __tablename__ = "prospects"

    prospect_id = Column(String, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    about = Column(String, nullable=True)
    platforms = Column(String, nullable=True)
    emails = Column(String, nullable=True)
    phones = Column(String, nullable=True)
    websites = Column(String, nullable=True)
    country = Column(String, nullable=True)
    country_acronym = Column(String, nullable=True)
    address = Column(String, nullable=True)
    business_context = Column(String, nullable=True)
    has_phone = Column(Boolean, default=False)
    has_email = Column(Boolean, default=False)
    is_called = Column(Boolean, default=False)
    verification_call_summary = Column(String, nullable=True)
    verification_recording_url = Column(String, nullable=True)
    is_qualified = Column(Boolean, default=False)
    is_relevant_industry = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), default=datetime.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), default=datetime.now()
    )

    # Indexes
    __table_args__ = (
        Index("idx_prospects_created_at", "created_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "prospect_id": str(self.prospect_id),
            "name": self.name,
            "about": self.about,
            "platforms": self.platforms,
            "emails": self.emails,
            "phones": self.phones,
            "websites": self.websites,
            "country": self.country,
            "country_acronym": self.country_acronym or None,
            "address": self.address,
            "business_context": self.business_context,
            "has_phone": self.has_phone,
            "has_email": self.has_email,
            "is_called": self.is_called,
            "verification_call_summary": self.verification_call_summary,
            "verification_recording_url": self.verification_recording_url,
            "is_qualified": self.is_qualified,
            "is_relevant_industry": self.is_relevant_industry,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
