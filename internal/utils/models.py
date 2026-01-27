# """
# Pydantic models for deduplication pipeline
# """

# import uuid
# from typing import List, Dict, Set, Any, Optional
# from datetime import datetime

# from pydantic import BaseModel, Field
# from internal.domain.scraper.sources.dto import ProspectDict


# class MergedContactInfo(BaseModel):
#     """Merged contact information with sets for deduplication"""
#     emails: Set[str] = Field(default_factory=set)
#     phones: Set[str] = Field(default_factory=set)
#     websites: Set[str] = Field(default_factory=set)
    
#     def merge(self, other: 'MergedContactInfo') -> None:
#         """Union merge of contact points"""
#         self.emails.update(other.emails)
#         self.phones.update(other.phones)
#         self.websites.update(other.websites)
    
#     def to_dict(self) -> Dict:
#         return {
#             'emails': list(self.emails),
#             'phones': list(self.phones),
#             'websites': list(self.websites)
#         }


# class SourceReference(BaseModel):
#     """Traceable source metadata"""
#     temp_prospect_id: str
#     source_platform: str
#     source_url: str
#     discovery_confidence: float
#     timestamp: str
#     # raw_data: Dict[str, Any]


# class CanonicalProspect(BaseModel):
#     """Canonical prospect entity after deduplication"""
#     prospect_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
#     name: str
#     contact_info: MergedContactInfo = Field(default_factory=MergedContactInfo)
#     location: str
#     about: List[str]
#     business_context: Optional[str] = None
#     confidence_score: float  # Highest from merged sources
#     sources: List[SourceReference] = Field(default_factory=list)
#     created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
#     def merge_with(self, raw_prospect: ProspectDict) -> None:
#         """Merge another raw prospect into this canonical entity"""
#         # Union contacts
#         if raw_prospect['contact_info'].get('email'):
#             self.contact_info.emails.add(raw_prospect['contact_info']['email'])
#         if raw_prospect['contact_info'].get('phone'):
#             self.contact_info.phones.add(raw_prospect['contact_info']['phone'])
#         if raw_prospect['contact_info'].get('website'):
#             self.contact_info.websites.add(raw_prospect['contact_info']['website'])
        
#         # Merge about field (collect unique about texts)
#         raw_about = raw_prospect.get('about')
#         if raw_about:
#             # Convert to list if it's a string
#             if isinstance(raw_about, str):
#                 raw_about = [raw_about]
#             # Add unique about texts to the list
#             for about_text in raw_about:
#                 if about_text and about_text not in self.about:
#                     self.about.append(about_text)
        
#         # Update confidence to highest
#         self.confidence_score = max(
#             self.confidence_score,
#             raw_prospect['discovery_confidence_score']
#         )
        
#         # Append source reference
#         self.sources.append(SourceReference(
#             temp_prospect_id=raw_prospect['prospect_id'],
#             source_platform=raw_prospect['source_platform'],
#             source_url=raw_prospect['source_url'],
#             discovery_confidence=raw_prospect['discovery_confidence_score'],
#             timestamp=raw_prospect['timestamp']
#         ))
        
#         # Prefer non-null business context
#         if not self.business_context and raw_prospect.get('business_context'):
#             self.business_context = raw_prospect['business_context']
    
#     def to_dict(self) -> Dict:
#         return {
#             'prospect_id': self.prospect_id,
#             'name': self.name,
#             'contact_info': self.contact_info.to_dict(),
#             'location': self.location,
#             'about': self.about if isinstance(self.about, list) else [self.about] if self.about else [],
#             'business_context': self.business_context,
#             'confidence_score': self.confidence_score,
#             'source_count': len(self.sources),
#             'sources': [s.model_dump() for s in self.sources],
#             'created_at': self.created_at
#         }

