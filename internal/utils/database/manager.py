"""
Database manager for prospect operations
"""

import uuid
from typing import List, Dict, Optional, Any, TypedDict
from datetime import datetime

from sqlalchemy.orm import Session

from internal.utils.logger import AppLogger
from internal.utils.database.models import Prospect

logger = AppLogger("utils.database.manager")()


# dataclass for enrichments queue
class EnrichmentsQueue(TypedDict):
    prospect_id: str
    linkedin_url: Optional[str]
    website_url: Optional[str]
    discovery_confidence: float


class DatabaseManager:
    """Manages database operations for prospects"""

    def __init__(self, session: Optional[Session] = None):
        """
        Initialize database manager

        Args:
            session: Optional SQLAlchemy session. If None, uses context manager
        """
        self._session = session
        self._use_context = session is None

    def _get_session(self) -> Session:
        """Get database session"""
        if self._use_context:
            raise RuntimeError(
                "Session not provided. Use DatabaseManager with context manager: "
                "with get_session() as session: DatabaseManager(session=session)"
            )
        return self._session

    def create_prospect(
        self,
        prospect_id: str,
        name: str,
        emails: List[str],
        phones: List[str],
        websites: List[str],
        platforms: List[str],
        country: Optional[str],
        country_acronym: Optional[str],
        address: Optional[str],
        business_context: Optional[str],
        has_phone: bool,
        has_email: bool,
        created_at: datetime,
        about: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> Optional[Prospect]:
        """
        Create or update a prospect

        Args:
            prospect_id: UUID string
            name: Prospect name
            emails: List of email addresses
            phones: List of phone numbers
            websites: List of website URLs
            platforms: List of platforms (e.g., ['linkedin', 'google_maps'])
            country: Country name
            country_acronym: Country acronym
            address: Address
            business_context: Business context
            has_phone: Whether the prospect has a phone
            has_email: Whether the prospect has an email
            created_at: Creation timestamp
            about: Optional about/description text
            session: Optional session (if not using context manager)

        Returns:
            Prospect model instance or None if error
        """
        db_session = session or self._get_session()

        try:
            # Prospect.prospect_id is String, not UUID
            prospect = (
                db_session.query(Prospect)
                .filter(Prospect.prospect_id == prospect_id)
                .first()
            )

            if prospect:
                prospect.name = name
                prospect.about = about
                prospect.platforms = platforms
                prospect.emails = emails
                prospect.phones = phones
                prospect.websites = websites
                prospect.country = country
                prospect.country_acronym = country_acronym
                prospect.address = address
                prospect.business_context = business_context
                prospect.has_phone = has_phone
                prospect.has_email = has_email
                logger.debug("Updated prospect %s", prospect_id)
            else:
                prospect = Prospect(
                    prospect_id=prospect_id,
                    name=name,
                    about=about,
                    platforms=platforms,
                    emails=emails,
                    phones=phones,
                    websites=websites,
                    country=country,
                    country_acronym=country_acronym,
                    address=address,
                    business_context=business_context,
                    has_phone=has_phone,
                    has_email=has_email,
                    created_at=created_at,
                )
                db_session.add(prospect)
                logger.debug("Created prospect %s", prospect_id)

            if not session:
                db_session.commit()

            return prospect
        except Exception as e:
            if not session:
                db_session.rollback()
            logger.error("Failed to create/update prospect %s: %s", prospect_id, e)
            return None

    def get_prospects_with_phones(self, limit: Optional[int] = None) -> List[Prospect]:
        """
        Get prospects with phone numbers and not called
        """
        db_session = self._get_session()
        try:
            query = (
                db_session.query(Prospect)
                .filter(Prospect.has_phone == True)
                .filter(Prospect.phones.isnot(None))
                .filter(Prospect.phones != "")
                .filter(Prospect.is_called == False)
            )
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error("Failed to get prospects with phones: %s", e)
            return []
        finally:
            db_session.close()

    def update_prospect_verification_call(
        self,
        prospect_id: str,
        call_summary: Optional[str] = None,
        recording_url: Optional[str] = None,
        is_qualified: Optional[bool] = None,
        is_relevant_industry: Optional[bool] = None,
    ) -> Optional[Prospect]:
        """
        Update prospect verification call
        """
        db_session = self._get_session()
        try:
            prospect = (
                db_session.query(Prospect)
                .filter(Prospect.prospect_id == prospect_id)
                .first()
            )
            if prospect:
                prospect.verification_call_summary = call_summary
                prospect.verification_recording_url = recording_url
                prospect.is_qualified = is_qualified
                prospect.is_relevant_industry = is_relevant_industry
                prospect.is_called = True
                db_session.commit()
                return prospect
            else:
                logger.error("Prospect %s not found", prospect_id)
                return None
        except Exception as e:
            logger.error(
                "Failed to update prospect verification call %s: %s", prospect_id, e
            )
            return None

    def get_qualified_prospects(
        self, limit: Optional[int] = None, is_qualified: bool = True
    ) -> List[Prospect]:
        """
        Get qualified prospects
        """
        db_session = self._get_session()
        try:
            query = db_session.query(Prospect).filter(
                Prospect.is_qualified == is_qualified
            )
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error("Failed to get qualified prospects: %s", e)
            return []
        finally:
            db_session.close()

    def get_called_prospects(self, limit: Optional[int] = None) -> List[Prospect]:
        """
        Get all prospects that have been called (is_called=True), for tracking and re-calling.
        Ordered by updated_at descending (most recent first).
        """
        db_session = self._get_session()
        try:
            query = (
                db_session.query(Prospect)
                .filter(Prospect.is_called == True)
                .order_by(Prospect.updated_at.desc())
            )
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error("Failed to get called prospects: %s", e)
            return []
        finally:
            db_session.close()

    def get_prospect_by_id(self, prospect_id: str) -> Optional[Prospect]:
        """
        Get prospect by ID
        """
        db_session = self._get_session()
        try:
            return db_session.query(Prospect).filter(Prospect.prospect_id == prospect_id).first()
        except Exception as e:
            logger.error("Failed to get prospect by ID %s: %s", prospect_id, e)
            return None
        finally:
            db_session.close()

    def delete_prospect(self, prospect_id: str) -> bool:
        """
        Delete a prospect by ID. Returns True if deleted, False if not found or error.
        """
        db_session = self._get_session()
        try:
            prospect = db_session.query(Prospect).filter(Prospect.prospect_id == prospect_id).first()
            if prospect:
                db_session.delete(prospect)
                db_session.commit()
                logger.info("Deleted prospect %s", prospect_id)
                return True
            return False
        except Exception as e:
            db_session.rollback()
            logger.error("Failed to delete prospect %s: %s", prospect_id, e)
            return False
        finally:
            db_session.close()