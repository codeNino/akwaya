import requests
from typing import List, Dict
from internal.config.secret import SecretManager

GOOGLE_CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"

def search_with_google_cse(
    query: str,
    num_results: int = 10
) -> List[Dict]:
    params = {
        "key": SecretManager.CSE_API_KEY,
        "cx": SecretManager.CSE_ID,
        "q": query,
        "num": min(num_results, 10)
    }

    response = requests.get(GOOGLE_CSE_ENDPOINT, params=params)
    response.raise_for_status()
    data = response.json()

    results = []
    for item in data.get("items", []):
        results.append({
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet"),
            "displayLink": item.get("displayLink")
        })

    return results



