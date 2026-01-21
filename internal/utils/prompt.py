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
