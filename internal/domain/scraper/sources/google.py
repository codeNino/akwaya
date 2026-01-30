import http.client
import json
import requests
import time
import asyncio
from typing import List

from internal.config.secret import SecretManager
from internal.domain.common.dto import Prospect
from internal.domain.scraper.sources.parser import extract_important_google_places_info
from internal.utils.logger import AppLogger

logger = AppLogger("internal.domain.scraper.sources.google")()


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

async def search_google_with_serper(query: str, total_results: int = 50):
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
                    "source_platform": "google_search",
                    "name": item.get("title"),
                    "contact": {
                        "website": item.get("link")
                    },
                    "about" : item.get("snippet")
                })
        else:
            break

        page += 1

    return results_fetched


def _search_google_places_sync(text_query: str, batch_size: int) -> List[Prospect]:
    crawled_and_formatted: List[Prospect] = []
    url = "https://places.googleapis.com/v1/places:searchText"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": SecretManager.GOOGLE_API_KEY,
        "X-Goog-FieldMask": (
            "places.displayName.text,"
            "places.primaryType,"
            "places.websiteUri,"
            "places.nationalPhoneNumber,"
            "places.shortFormattedAddress,"
            "places.addressComponents,"
        ),
    }

    params = {"textQuery": text_query}
    max_retries = 3
    retry_delays = [2, 4, 8]

    def _do_request():
        return requests.post(url, headers=headers, json=params, timeout=30)

    response = None
    for attempt in range(max_retries):
        try:
            response = _do_request()
            break
        except requests.exceptions.RequestException as e:
            is_dns = "name resolution" in str(e).lower() or "failed to resolve" in str(e).lower() or "Errno -3" in str(e)
            if attempt == max_retries - 1:
                if is_dns:
                    logger.warning(
                        "Google Places unreachable (DNS/network). Check internet, DNS, and that places.googleapis.com is allowed. Error: %s",
                        e,
                    )
                raise
            delay = retry_delays[attempt]
            logger.info("Google Places request failed (attempt %d/%d), retrying in %ds: %s", attempt + 1, max_retries, delay, e)
            time.sleep(delay)

    if response is None:
        raise RuntimeError("Google Places request failed after retries")

    if response.status_code != 200:
        raise Exception(f"Request failed: {response.status_code} - {response.text}")

    response_body = response.json()
    places_found = response_body.get("places", [])

    if places_found:
        cleaned_results = extract_important_google_places_info(places_found)
        crawled_and_formatted.extend(cleaned_results)

    while True:
        if not response_body.get("nextPageToken") or len(crawled_and_formatted) >= batch_size:
            break
        params = {
            "textQuery": text_query,
            "pageToken": response_body["nextPageToken"],
        }
        logger.info("Fetching next page of data...")
        time.sleep(2)
        try:
            response = _do_request()
        except requests.exceptions.RequestException as e:
            logger.warning("Failed to fetch next page: %s. Returning %d results so far.", e, len(crawled_and_formatted))
            break
        if response.status_code != 200:
            break
        response_body = response.json()
        places_found = response_body.get("places", [])
        if places_found:
            cleaned_results = extract_important_google_places_info(places_found)
            crawled_and_formatted.extend(cleaned_results)

    logger.info("Done fetching data for query from google places")
    return crawled_and_formatted[:batch_size]

async def search_google_places(text_query: str, batch_size: int = 10) -> List[Prospect]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _search_google_places_sync, text_query, batch_size)