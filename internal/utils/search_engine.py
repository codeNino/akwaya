import requests
import time
import asyncio
from typing import List
import json
import http.client

from internal.config.secret import SecretManager
from internal.utils.dto import ProspectDict
from internal.utils.parser import extract_important_google_places_info, extract_linkedin_profiles
from internal.utils.logger import AppLogger

logger = AppLogger("SearchEngine")()

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
                    "link": item.get("link"),
                    "about" : item.get("snippet")
                })
        else:
            break

        page += 1

    return results_fetched


async def search_linkedin(query: str, batch_size: int = 10) -> List[ProspectDict]:
    """
    Searches LinkedIn Via Custom Search Engine with a text query and returns up to batch_size results.
    """
    prefix = "site:linkedin.com/in/  "
    # This call is now async (offloaded to thread)
    cse_results = await get_data_from_linkedIn_serper_search(prefix + query, batch_size)
    
    # extract_linkedin_profiles uses synchronous LLM invoke, so we offload it too
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, extract_linkedin_profiles, cse_results)

def _search_google_places_sync(text_query: str, batch_size: int) -> List[ProspectDict]:
    crawled_and_formatted: List[ProspectDict] = []
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
        "places.googleMapsUri,"
    )
    }

    params = {"textQuery": text_query}

    while True:
        response = requests.post(url, headers=headers, json=params)
        if response.status_code != 200:
            raise Exception(f"Request failed: {response.status_code} - {response.text}")

        response_body = response.json()
        places_found = response_body.get("places", [])
        
        if places_found:
            cleaned_results = extract_important_google_places_info(places_found)
            crawled_and_formatted.extend(cleaned_results)

        # Stop if no nextPageToken or batch size reached
        if not response_body.get("nextPageToken") or len(crawled_and_formatted) >= batch_size:
            break

        # Prepare for next iteration
        params = {
            "textQuery": text_query,
            "pageToken": response_body["nextPageToken"]
        }
        logger.info("Fetching next page of data...")
        time.sleep(2)  # avoid hitting rate limits

    logger.info("Done fetching data for query from google places")
    return crawled_and_formatted[:batch_size]

async def search_google_places(text_query: str, batch_size: int = 10) -> List[ProspectDict]:
    """
    Searches Google Places API with a text query and returns up to batch_size results.
    Fetches only the fields required by extract_important_place_info for efficiency.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _search_google_places_sync, text_query, batch_size)