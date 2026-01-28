"""
Database manager for prospect operations
"""

import uuid
from typing import List, Dict, Optional, Any, TypedDict
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_

from internal.utils.logger import AppLogger
from internal.utils.database.models import Prospect
from internal.utils.database.session import get_session

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
        profile_urls: Dict[str, str],
        location: Dict[str, Any],
        business_context: Optional[str],
        has_phone: bool,
        has_email: bool,
        created_at: datetime,
        about: Optional[str] = None,
        session: Optional[Session] = None
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
            profile_urls: Dict mapping platform to URL
            location: Dict with location data
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
            prospect = db_session.query(Prospect).filter(
                Prospect.prospect_id == prospect_id
            ).first()
            
            if prospect:
                prospect.name = name
                prospect.about = about
                prospect.platforms = platforms
                prospect.emails = emails
                prospect.phones = phones
                prospect.websites = websites
                prospect.profile_urls = profile_urls
                prospect.location = location
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
                    profile_urls=profile_urls,
                    location=location,
                    business_context=business_context,
                    has_phone=has_phone,
                    has_email=has_email,
                    created_at=created_at
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
    
    # def create_prospect_source(
    #     self,
    #     prospect_id: str,
    #     platform: str,
    #     discovered_at: datetime,
    #     discovery_method: Optional[str] = None,
    #     raw_snapshot_id: Optional[str] = None,
    #     session: Optional[Session] = None
    # ) -> Optional[ProspectSource]:
    #     """
    #     Create a prospect source record
        
    #     Args:
    #         prospect_id: UUID string
    #         platform: 'linkedin' or 'google_maps'
    #         discovered_at: Discovery timestamp
    #         discovery_method: Optional discovery method
    #         raw_snapshot_id: Optional UUID string of related snapshot
    #         session: Optional session
            
    #     Returns:
    #         ProspectSource model instance or None if error
    #     """
    #     db_session = session or self._get_session()
        
    #     try:
    #         # Validate and convert raw_snapshot_id to UUID if provided
    #         raw_snapshot_uuid = None
    #         if raw_snapshot_id:
    #             try:
    #                 raw_snapshot_uuid = uuid.UUID(raw_snapshot_id)
    #             except (ValueError, TypeError):
    #                 logger.warning("Invalid raw_snapshot_id format: %s", raw_snapshot_id)
    #                 raw_snapshot_uuid = None
            
    #         source = ProspectSource(
    #             prospect_id=prospect_id,  # String, not UUID
    #             platform=platform,
    #             discovered_at=discovered_at,
    #             discovery_method=discovery_method,
    #             raw_snapshot_id=raw_snapshot_uuid
    #         )
    #         db_session.add(source)
            
    #         if not session:
    #             db_session.commit()
            
    #         logger.debug("Created prospect source for %s", prospect_id)
    #         return source
    #     except Exception as e:
    #         if not session:
    #             db_session.rollback()
    #         logger.error("Failed to create prospect source for %s: %s", prospect_id, e)
    #         return None
    
    # def create_raw_snapshot(
    #     self,
    #     prospect_id: str,
    #     platform: str,
    #     snapshot_at: datetime,
    #     business_context: Optional[str] = None,
    #     session: Optional[Session] = None
    # ) -> Optional[RawSnapshot]:
    #     """
    #     Create a raw snapshot record
        
    #     Args:
    #         prospect_id: String (canonical prospect_id)
    #         platform: 'linkedin' or 'google_maps'
    #         business_context: Optional business context text
    #         snapshot_at: Snapshot timestamp
    #         session: Optional session
            
    #     Returns:
    #         RawSnapshot model instance or None if error
    #     """
    #     db_session = session or self._get_session()
        
    #     try:
    #         db_session.query(RawSnapshot).filter(
    #             and_(
    #                 RawSnapshot.prospect_id == prospect_id,  # String, not UUID
    #                 RawSnapshot.platform == platform,
    #                 RawSnapshot.is_latest == True
    #             )
    #         ).update({'is_latest': False})
            
    #         snapshot = RawSnapshot(
    #             prospect_id=prospect_id,  # String, not UUID
    #             platform=platform,
    #             business_context=business_context,
    #             snapshot_at=snapshot_at,
    #             is_latest=True
    #         )
    #         db_session.add(snapshot)
            
    #         if not session:
    #             db_session.commit()
            
    #         logger.debug("Created raw snapshot for prospect %s", prospect_id)
    #         return snapshot
    #     except Exception as e:
    #         if not session:
    #             db_session.rollback()
    #         logger.error("Failed to create raw snapshot for %s: %s", prospect_id, e)
    #         return None
    
    def get_enrichment_queue(
        self,
        min_confidence: float = 0.5,
        session: Optional[Session] = None
    ) -> List[EnrichmentsQueue]:
        """
        Get prospects for enrichment queue
        
        Args:
            min_confidence: Minimum discovery confidence threshold
            session: Optional session
            
        Returns:
            List of prospects with linkedin_url, website_url, and discovery_confidence
        """
        db_session = session or self._get_session()
        
        try:
            prospects = db_session.query(Prospect).filter(
                Prospect.discovery_confidence > min_confidence
            ).order_by(Prospect.discovery_confidence.desc()).all()
            
            results = []
            for prospect in prospects:
                linkedin_url = prospect.profile_urls.get('linkedin') if prospect.profile_urls else None
                website_url = prospect.websites[0] if prospect.websites else None
                
                results.append({
                    'prospect_id': str(prospect.prospect_id),
                    'linkedin_url': linkedin_url,
                    'website_url': website_url,
                    'discovery_confidence': float(prospect.discovery_confidence) if prospect.discovery_confidence else 0.0
                })
            
            return results
        except Exception as e:
            logger.error("Failed to get enrichment queue: %s", e)
            return []


    def enrich_prospect(self, prospect_id: str, session: Optional[Session] = None) -> None:
        """
        Enrich a prospect

        Args:
            prospect_id: ID of the prospect to enrich
        """
        db_session = session or self._get_session()
        try:
            prospect = db_session.query(Prospect).filter(
                Prospect.prospect_id == prospect_id
            ).first()
            if not prospect:
                logger.error("Prospect not found: %s", prospect_id)
                return
            prospect.enriched = True
            db_session.commit()
            logger.info("Prospect enriched: %s", prospect_id)
        except Exception as e:
            logger.error("Failed to enrich prospect %s: %s", prospect_id, e)
            return None
