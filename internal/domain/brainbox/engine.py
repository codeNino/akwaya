from internal.config.secret import SecretManager

from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableSequence
from openai import LengthFinishReasonError

from .prompt import (
    keyword_generation_prompt,
    sourced_leads_preprocessing_prompt,
    scraped_website_evaluation_prompt,
    leads_extraction_from_articles_prompt
)
from internal.domain.common.dto import(
    KeywordGenerationOutput,
    LeadsPreprocessingOutput,
    Prospect,
    WebsiteScrapingOutput,
    ArticleExtractionOutput
)
from internal.utils.logger import AppLogger

logger = AppLogger("internal.domain.brainbox.engine")()

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.5,
    api_key=SecretManager.OPENAI_KEY,
    max_tokens=16384,
)


def generate_keywords(query: str) -> List[str]:
    chain = keyword_generation_prompt | llm.with_structured_output(KeywordGenerationOutput)
    response = chain.invoke({"query": query})
    return response.model_dump()["keywords"]



def chunk_list(items, size):
    return [items[i:i + size] for i in range(0, len(items), size)]


def _merge_preprocessing_outputs(a: LeadsPreprocessingOutput, b: LeadsPreprocessingOutput) -> LeadsPreprocessingOutput:
    return LeadsPreprocessingOutput(
        individuals=a.individuals + b.individuals,
        businesses=a.businesses + b.businesses,
        articles=a.articles + b.articles,
    )


async def _preprocess_batch_with_retry(
    chain: RunnableSequence,
    batch: List[Prospect],
) -> LeadsPreprocessingOutput:
    """Invoke chain on one batch; on length limit error, split batch and retry."""
    empty = LeadsPreprocessingOutput(individuals=[], businesses=[], articles=[])
    if not batch:
        return empty
    try:
        out = await chain.ainvoke({"leads": batch})
        return out
    except LengthFinishReasonError as e:
        logger.warning(
            "LLM length limit reached for batch of %d leads (prompt or completion too long). Splitting batch. Usage: %s",
            len(batch),
            getattr(e, "completion", None),
        )
        if len(batch) == 1:
            logger.warning("Skipping single lead that exceeded length limit (content too large).")
            return empty
        mid = len(batch) // 2
        left = await _preprocess_batch_with_retry(chain, batch[:mid])
        right = await _preprocess_batch_with_retry(chain, batch[mid:])
        return _merge_preprocessing_outputs(left, right)


async def preprocess_leads(leads: List[Prospect], batch_size: int = 10) -> LeadsPreprocessingOutput:
    if not leads:
        return LeadsPreprocessingOutput(individuals=[], businesses=[], articles=[])
    batches = chunk_list(leads, batch_size)
    chain = sourced_leads_preprocessing_prompt | llm.with_structured_output(LeadsPreprocessingOutput)

    processed_leads = LeadsPreprocessingOutput(individuals=[], businesses=[], articles=[])
    for batch in batches:
        out = await _preprocess_batch_with_retry(chain, batch)
        processed_leads.individuals.extend(out.individuals)
        processed_leads.businesses.extend(out.businesses)
        processed_leads.articles.extend(out.articles)

    return processed_leads


async def _eval_batch_with_retry(chain: RunnableSequence, batch: List[Dict]) -> WebsiteScrapingOutput:
    empty = WebsiteScrapingOutput(information=[])
    if not batch:
        return empty
    try:
        return await chain.ainvoke({"website_data": batch})
    except LengthFinishReasonError as e:
        logger.warning("LLM length limit in website evaluation (batch size %d). Splitting.", len(batch))
        if len(batch) == 1:
            logger.warning("Skipping single website that exceeded length limit.")
            return empty
        mid = len(batch) // 2
        left = await _eval_batch_with_retry(chain, batch[:mid])
        right = await _eval_batch_with_retry(chain, batch[mid:])
        return WebsiteScrapingOutput(information=left.information + right.information)


async def evaluate_scraped_website(website_data: List[Dict], batch_size: int = 6) -> WebsiteScrapingOutput:
    if not website_data:
        return WebsiteScrapingOutput(information=[])
    batches = chunk_list(website_data, batch_size)
    chain = scraped_website_evaluation_prompt | llm.with_structured_output(WebsiteScrapingOutput)
    processed_websites = WebsiteScrapingOutput(information=[])
    for batch in batches:
        out = await _eval_batch_with_retry(chain, batch)
        processed_websites.information.extend(out.information)
    return processed_websites


async def _extract_batch_with_retry(chain: RunnableSequence, batch: List[Dict]) -> ArticleExtractionOutput:
    empty = ArticleExtractionOutput(individuals=[], businesses=[])
    if not batch:
        return empty
    try:
        return await chain.ainvoke({"scraped_data": batch})
    except LengthFinishReasonError as e:
        logger.warning("LLM length limit in article extraction (batch size %d). Splitting.", len(batch))
        if len(batch) == 1:
            logger.warning("Skipping single article that exceeded length limit.")
            return empty
        mid = len(batch) // 2
        left = await _extract_batch_with_retry(chain, batch[:mid])
        right = await _extract_batch_with_retry(chain, batch[mid:])
        return ArticleExtractionOutput(
            individuals=left.individuals + right.individuals,
            businesses=left.businesses + right.businesses,
        )


async def extract_leads_from_articles(articles: List[Dict], batch_size: int = 6) -> ArticleExtractionOutput:
    if not articles:
        return ArticleExtractionOutput(individuals=[], businesses=[])
    batches = chunk_list(articles, batch_size)
    chain = leads_extraction_from_articles_prompt | llm.with_structured_output(ArticleExtractionOutput)
    processed_articles = ArticleExtractionOutput(individuals=[], businesses=[])
    for batch in batches:
        out = await _extract_batch_with_retry(chain, batch)
        processed_articles.individuals.extend(out.individuals)
        processed_articles.businesses.extend(out.businesses)
    return processed_articles
