from langchain_core.prompts import ChatPromptTemplate

parser_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are a data extraction engine.

You will receive a list of Google Custom Search results for LinkedIn profiles.
Each item contains:
- title
- snippet
- link

Your task:
- Extract one LinkedIn profile per item
- Infer name, headline, company, and location if present
- Summarize about section based on information available
- Extract contact info if available in the information
- If a field is missing, return null
- Always include the profile_url
- Return ONLY valid JSON matching the schema
"""
    ),
    (
        "human",
        """
Input results:
{results}
"""
    )
])

# Scoring prompt template
scoring_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert lead scoring analyst specializing in identifying high-quality prospects for financial services and trading platforms.

Your task is to evaluate prospects and assign a quality score from 0.0 to 1.0 based on:
1. **Relevance**: How well the prospect matches the target profile (forex/trading professionals, mentors, analysts)
2. **Authority**: Professional credibility, experience level, and industry standing
3. **Engagement Potential**: Likelihood of being interested in and engaging with our services
4. **Contact Quality**: Availability and quality of contact information
5. **Business Context**: Clarity and specificity of their business description

Consider these factors:
- Years of experience mentioned
- Specific trading expertise (forex, options, stocks, etc.)
- Professional titles and roles
- Company affiliations (banks, trading firms, etc.)
- Educational credentials (CFA, CMT, etc.)
- Presence of website or professional content
- Location relevance
- Completeness of profile information

Return ONLY a JSON object with this structure:
{{
    "prospect_id": "string",
    "llm_score": 0.0-1.0,
    "reasoning": "brief explanation of the score"
}}

Be strict in your scoring - only assign high scores (0.7+) to truly exceptional prospects."""
    ),
    (
        "human",
        """Evaluate this prospect:

**Name**: {name}
**About**: {about}
**Business Context**: {business_context}
**Location**: {location}
**Contact Info**: 
  - Email: {email}
  - Phone: {phone}
  - Website: {website}
**Source URL**: {source_url}
**Discovery Confidence**: {discovery_confidence}

Return the JSON score."""
    )
])