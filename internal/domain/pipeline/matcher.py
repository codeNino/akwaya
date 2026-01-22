"""
Prospect matching logic for deduplication
"""

from typing import Optional, Tuple
from urllib.parse import urlparse
from difflib import SequenceMatcher
import re

from internal.utils.dto import ProspectDict


class ProspectMatcher:
    """Deterministic prospect matching logic"""
    
    # Matching thresholds
    HIGH_NAME_SIMILARITY = 0.90
    MEDIUM_NAME_SIMILARITY = 0.75
    
    @staticmethod
    def normalize_domain(url: Optional[str]) -> Optional[str]:
        """Extract and normalize domain from URL/website"""
        if not url:
            return None
        try:
            # Add scheme if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            domain = urlparse(url).netloc.lower()
            # Remove www prefix
            return domain.replace('www.', '')
        except Exception:
            return None
    
    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize name for comparison"""
        # Remove common business suffixes
        name = re.sub(r'\b(LLC|Ltd|Inc|Corp|Limited|Corporation|Co)\b\.?', '', name, flags=re.IGNORECASE)
        # Remove extra whitespace and convert to lowercase
        return ' '.join(name.lower().split())
    
    @staticmethod
    def name_similarity(name1: str, name2: str) -> float:
        """Calculate normalized name similarity (0-1)"""
        n1 = ProspectMatcher.normalize_name(name1)
        n2 = ProspectMatcher.normalize_name(name2)
        return SequenceMatcher(None, n1, n2).ratio()
    
    @staticmethod
    def extract_linkedin_id(url: str) -> Optional[str]:
        """Extract LinkedIn profile/company ID from URL"""
        if not url or 'linkedin.com' not in url.lower():
            return None
        # Match patterns like /in/username or /company/name
        match = re.search(r'linkedin\.com/(in|company)/([^/?]+)', url, re.IGNORECASE)
        return match.group(2) if match else None
    
    @staticmethod
    def match_confidence(p1: ProspectDict, p2: ProspectDict) -> Tuple[str, float]:
        """
        Determine match confidence level
        Returns: (level, confidence_score)
        Levels: 'high', 'medium', 'low'
        """
        # HIGH CERTAINTY: Same LinkedIn profile
        linkedin_id1 = ProspectMatcher.extract_linkedin_id(p1.get('source_url', ''))
        linkedin_id2 = ProspectMatcher.extract_linkedin_id(p2.get('source_url', ''))
        
        if linkedin_id1 and linkedin_id2 and linkedin_id1 == linkedin_id2:
            return ('high', 1.0)
        
        # HIGH CERTAINTY: Same website domain
        domain1 = ProspectMatcher.normalize_domain(p1['contact_info'].get('website'))
        domain2 = ProspectMatcher.normalize_domain(p2['contact_info'].get('website'))
        
        if domain1 and domain2 and domain1 == domain2:
            return ('high', 0.95)
        
        # Calculate name similarity
        name_sim = ProspectMatcher.name_similarity(p1['name'], p2['name'])
        
        # HIGH CERTAINTY: Strong email + name similarity
        email1 = p1['contact_info'].get('email')
        email2 = p2['contact_info'].get('email')
        
        if email1 and email2 and email1.lower() == email2.lower():
            if name_sim >= ProspectMatcher.MEDIUM_NAME_SIMILARITY:
                return ('high', 0.90)
        
        # MEDIUM CERTAINTY: High name similarity + same location
        location1 = p1.get('location', '').lower().strip()
        location2 = p2.get('location', '').lower().strip()
        
        if name_sim >= ProspectMatcher.HIGH_NAME_SIMILARITY:
            if location1 and location2 and location1 == location2:
                return ('medium', 0.80)
        
        # MEDIUM CERTAINTY: Very high name similarity
        if name_sim >= ProspectMatcher.HIGH_NAME_SIMILARITY:
            return ('medium', 0.75)

        return ('low', name_sim)

