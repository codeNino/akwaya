import json
from typing import Dict, List
from scrapfly import ScrapeConfig, ScrapflyClient, ScrapeApiResponse

import asyncio
import http.client

from internal.domain.scraper.sources.dto import ProspectDict
from internal.domain.scraper.sources.parser import extract_linkedin_profiles, normalize_linkedin_url
from internal.utils.logger import AppLogger

from internal.config.secret import SecretManager
from .dto import LinkedInProfileSummary

logger = AppLogger("internal.domain.scraper.sources.linkedIn")()

#### Intial search using serper

def _search_with_serper_sync(query: str, page: int):
    conn = http.client.HTTPSConnection("google.serper.dev")
    payload = json.dumps({
        "q": query,
        "page": page
    })
    headers = {
        'X-API-KEY': SecretManager.SERPER_API_KEY,
        'Content-Type': 'application/json'
    }
    conn.request("POST", "/search", payload, headers)
    res = conn.getresponse()
    data = res.read().decode("utf-8")
    data = json.loads(data)

    return data.get("organic", [])

async def get_data_from_linkedIn_serper_search(query: str, total_results: int = 50):
    loop = asyncio.get_running_loop()
    results_fetched = []
    page = 1

    while len(results_fetched) < total_results:

        data = await loop.run_in_executor(
            None,
            _search_with_serper_sync,
            query,
            page,
        )

        if len(data) > 0:
            for item in data:
                results_fetched.append({
                    "title": item.get("title"),
                    "link": normalize_linkedin_url(item.get("link")),
                    "about" : item.get("snippet")
                })
        else:
            break

        page += 1

    return results_fetched


async def search_linkedin(query: str, batch_size: int = 10) -> List[ProspectDict]:
    prefix = "site:linkedin.com/in/  "
  
    cse_results = await get_data_from_linkedIn_serper_search(prefix + query, batch_size)
    
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, extract_linkedin_profiles, cse_results)


### Deep scraping using scrapfly


SCRAPFLY = ScrapflyClient(key=SecretManager.SCRAPFLY_KEY)

BASE_CONFIG = {
    "asp": True,
    "country": "US",
    "headers": {
        "Accept-Language": "en-US,en;q=0.5"
    },
    "render_js": True,
    "proxy_pool": "public_residential_pool"    
}

def refine_profile(data: Dict) -> Dict: 
    """refine and clean the parsed profile data"""
    parsed_data = {}
    profile_data = [key for key in data["@graph"] if key["@type"]=="Person"][0]
    profile_data["worksFor"] = [profile_data["worksFor"]]
    articles = [key for key in data["@graph"] if key["@type"]=="Article"]
    parsed_data["profile"] = profile_data
    parsed_data["posts"] = articles
    return parsed_data


def extract_linkedin_profile_summary(
    data: Dict,
    max_posts: int = 10
) -> LinkedInProfileSummary:
    summary: LinkedInProfileSummary = {
        "recent_posts": [],
        "recent_job_title": None,
        "recent_company": None,
        "location": None,
        "profile_url": None,
    }

    profile = data.get("profile", {})
    posts = data.get("posts", [])

    employment_history = profile.get("worksFor", None)
    if isinstance(employment_history, list):
        summary["recent_company"] = employment_history[0].get("name", None)
    summary["recent_job_title"] = profile.get("jobTitle", None)
    address = profile.get("address", None)
    if isinstance(address, dict):
        summary["location"] = address.get("addressLocality", None)

    summary["recent_posts"] = [
        post.get("headline")
        for post in posts[:max_posts]
        if isinstance(post.get("headline"), str)
    ]

    profile_url = profile.get("url")
    if isinstance(profile_url, str):
        summary["profile_url"] = normalize_linkedin_url(profile_url)

    return summary


def parse_profile(response: ScrapeApiResponse) -> LinkedInProfileSummary:
    """parse profile data from hidden script tags"""
    selector = response.selector
    data = json.loads(selector.xpath("//script[@type='application/ld+json']/text()").get())
    refined_data = refine_profile(data)
    return extract_linkedin_profile_summary(refined_data)


async def deep_scrape_linkedin_profiles(urls: List[str]) -> List[LinkedInProfileSummary]:
    """scrape public linkedin profile pages"""
    to_scrape = [ScrapeConfig(url, **BASE_CONFIG) for url in urls]
    data = []
    # scrape the URLs concurrently
    async for response in SCRAPFLY.concurrent_scrape(to_scrape):
        try:
            profile_data = parse_profile(response)
            data.append(profile_data)
        except Exception as e:
            logger.error("An occured while scraping profile pages %s", e)
            pass
    logger.info(f"scraped {len(data)} profiles from Linkedin")
    return data

