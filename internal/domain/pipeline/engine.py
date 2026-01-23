"""
Deduplication engine orchestrator
"""

import uuid
from typing import List, Dict

from internal.domain.scraper.sources.dto import ProspectDict
from internal.utils.logger import AppLogger
from internal.utils.models import CanonicalProspect, MergedContactInfo, SourceReference
from internal.domain.pipeline.matcher import ProspectMatcher

logger = AppLogger("domain.pipeline.engine")()


class DeduplicationEngine:
    """Main deduplication orchestrator"""

    def __init__(self):
        self.auto_merged: List[CanonicalProspect] = []
        self.review_flagged: List[Dict] = []
        self.unmatched: List[CanonicalProspect] = []
        self.stats = {
            'total_processed': 0,
            'auto_merged_count': 0,
            'review_flagged_count': 0,
            'unmatched_count': 0,
            'merge_rate': 0.0,
            'flagged_rate': 0.0
        }

    def process(self, raw_prospects: List[ProspectDict]) -> Dict:
        """
        Main processing pipeline
        Returns: Complete deduplication results
        """
        logger.info("Starting deduplication process for %d raw prospects", len(raw_prospects))
        self.stats['total_processed'] = len(raw_prospects)

        clusters = self._build_clusters(raw_prospects)
        logger.debug("Built %d prospect clusters", len(clusters))

        # Process each cluster
        for cluster in clusters:
            if len(cluster['prospects']) == 1:
                self._create_unmatched_prospect(cluster['prospects'][0])
            elif cluster['match_level'] == 'high':
                # Auto-merge
                self._create_merged_prospect(cluster['prospects'])
            elif cluster['match_level'] == 'medium':
                # Flag for review
                self._flag_for_review(cluster)
            else:
                for p in cluster['prospects']:
                    self._create_unmatched_prospect(p)

        # Calculate final statistics
        self._calculate_stats()

        logger.info(
            "Deduplication complete: %d auto-merged, %d flagged, %d unmatched",
            self.stats['auto_merged_count'],
            self.stats['review_flagged_count'],
            self.stats['unmatched_count']
        )

        return self._generate_output()

    def _build_clusters(self, raw_prospects: List[ProspectDict]) -> List[Dict]:
        """Group prospects into match clusters"""
        clusters = []
        processed = set()

        for i, p1 in enumerate[ProspectDict](raw_prospects):
            if i in processed:
                continue

            cluster = {
                'prospects': [p1],
                'match_level': 'none',
                'confidence': 0.0
            }
            processed.add(i)

            # Find all matches for this prospect
            for j, p2 in enumerate(raw_prospects[i+1:], start=i+1):
                if j in processed:
                    continue

                level, conf = ProspectMatcher.match_confidence(p1, p2)

                if level == 'high':
                    cluster['prospects'].append(p2)
                    cluster['match_level'] = 'high'
                    cluster['confidence'] = max(cluster['confidence'], conf)
                    processed.add(j)
                elif level == 'medium' and cluster['match_level'] != 'high':
                    cluster['prospects'].append(p2)
                    cluster['match_level'] = 'medium'
                    cluster['confidence'] = max(cluster['confidence'], conf)
                    processed.add(j)

            clusters.append(cluster)

        return clusters

    def _create_merged_prospect(self, raw_prospects: List[ProspectDict]) -> None:
        """Create auto-merged canonical prospect"""
        # Use first prospect as base
        base = raw_prospects[0]

        # Initialize about as list (convert string to list if needed)
        base_about = base.get('about', '')
        if isinstance(base_about, str):
            about_list = [base_about] if base_about else []
        else:
            about_list = base_about if isinstance(base_about, list) else []
        
        prospect = CanonicalProspect(
            # use new uuid for prospect_id
            prospect_id=str(uuid.uuid4()),
            name=base['name'],
            about=about_list,
            contact_info=MergedContactInfo(),
            location=base['location'],
            business_context=base.get('business_context'),
            confidence_score=base['discovery_confidence_score']
        )

        # Merge all prospects
        for raw in raw_prospects:
            prospect.merge_with(raw)

        self.auto_merged.append(prospect)
        self.stats['auto_merged_count'] += 1
        logger.debug(
            "Auto-merged %d prospects into canonical prospect %s",
            len(raw_prospects),
            prospect.prospect_id,
        )

    def _flag_for_review(self, cluster: Dict) -> None:
        """Flag medium-confidence matches for manual review"""
        self.review_flagged.append({
            'flag_id': str(uuid.uuid4()),
            'match_confidence': cluster['confidence'],
            'prospects': cluster['prospects'],
            'reason': 'Medium confidence match - requires manual review',
            'recommended_action': 'Verify if these represent the same entity'
        })
        self.stats['review_flagged_count'] += 1
        logger.debug("Flagged %d prospects for review", len(cluster['prospects']))

    def _create_unmatched_prospect(self, raw_prospect: ProspectDict) -> None:
        """Create standalone prospect from single raw record"""
        contact_info = MergedContactInfo()
        if raw_prospect['contact_info'].get('email'):
            contact_info.emails.add(raw_prospect['contact_info']['email'])
        if raw_prospect['contact_info'].get('phone'):
            contact_info.phones.add(raw_prospect['contact_info']['phone'])
        if raw_prospect['contact_info'].get('website'):
            contact_info.websites.add(raw_prospect['contact_info']['website'])

        # Initialize about as list (convert string to list if needed)
        raw_about = raw_prospect.get('about', '')
        if isinstance(raw_about, str):
            about_list = [raw_about] if raw_about else []
        else:
            about_list = raw_about if isinstance(raw_about, list) else []
        
        prospect = CanonicalProspect(
            # use prospect_id from raw_prospect
            prospect_id=raw_prospect['prospect_id'], 
            name=raw_prospect['name'],
            about=about_list,
            contact_info=contact_info,
            location=raw_prospect['location'],
            business_context=raw_prospect.get('business_context'),
            confidence_score=raw_prospect['discovery_confidence_score']
        )

        prospect.sources.append(SourceReference(
            temp_prospect_id=raw_prospect['prospect_id'],
            source_platform=raw_prospect['source_platform'],
            source_url=raw_prospect['source_url'],
            discovery_confidence=raw_prospect['discovery_confidence_score'],
            timestamp=raw_prospect['timestamp']
        ))

        self.unmatched.append(prospect)
        self.stats['unmatched_count'] += 1

    def _calculate_stats(self) -> None:
        """Calculate final processing statistics"""
        total = self.stats['total_processed']
        if total > 0:
            self.stats['merge_rate'] = (self.stats['auto_merged_count'] / total) * 100
            self.stats['flagged_rate'] = (self.stats['review_flagged_count'] / total) * 100

    def _generate_output(self) -> Dict:
        """Generate final output"""
        return {
            'summary': {
                'total_raw_prospects_processed': self.stats['total_processed'],
                'canonical_prospects_created': len(self.auto_merged) + len(self.unmatched),
                'auto_merged_count': self.stats['auto_merged_count'],
                'review_flagged_count': self.stats['review_flagged_count'],
                'unmatched_count': self.stats['unmatched_count'],
                'merge_rate_percent': round(self.stats['merge_rate'], 2),
                'flagged_rate_percent': round(self.stats['flagged_rate'], 2)
            },
            'prospects_for_enrichment': [p.to_dict() for p in self.auto_merged + self.unmatched],
            'review_flagged': self.review_flagged,
            'auto_merged_details': [p.to_dict() for p in self.auto_merged],
            'unmatched_details': [p.to_dict() for p in self.unmatched]
        }
