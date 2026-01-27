from internal.config.secret import SecretManager

from typing import List, Dict
from langchain_openai import ChatOpenAI

from .prompt import (
    keyword_generation_prompt,
    sourced_leads_preprocessing_prompt,
    scraped_website_evaluation_prompt
)
from internal.domain.common.dto import(
    KeywordGenerationOutput,
    LeadsPreprocessingOutput,
    Prospect,
    WebsiteScrapingOutput
)



llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.5,
    api_key=SecretManager.OPENAI_KEY,
)


def generate_keywords(query: str) -> List[str]:
    chain = keyword_generation_prompt | llm.with_structured_output(KeywordGenerationOutput)
    response = chain.invoke({"query": query})
    return response.model_dump()["keywords"]



def chunk_list(items, size):
    return [items[i:i + size] for i in range(0, len(items), size)]


async def preprocess_leads(leads: List[Prospect], batch_size: int = 50) -> LeadsPreprocessingOutput:
    batches = chunk_list(leads, batch_size)

    chain = sourced_leads_preprocessing_prompt | llm.with_structured_output(
        LeadsPreprocessingOutput,
    )
    responses = await chain.abatch(
        [{"leads": batch} for batch in batches]
    )

    processed_leads = LeadsPreprocessingOutput(
        individuals=[],
        businesses=[],
        articles=[],
    )
    for output in responses:
        processed_leads.individuals.extend(output.individuals)
        processed_leads.businesses.extend(output.businesses)
        processed_leads.articles.extend(output.articles)

    return processed_leads


async def evaluate_scraped_website(website_data: List[Dict], batch_size: int = 10) -> WebsiteScrapingOutput:
    batches = chunk_list(website_data, batch_size)
    chain = scraped_website_evaluation_prompt | llm.with_structured_output(WebsiteScrapingOutput)
    responses = await chain.abatch(
        [{"website_data": batch} for batch in batches]
    )
    processed_websites = WebsiteScrapingOutput(
        information=[],
    )
    for output in responses:
        processed_websites.information.extend(output.information)
    # print(processed_websites.information[:3])
    return processed_websites