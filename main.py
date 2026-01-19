from internal.utils.search_engine import search_with_google_cse


def find_forex_trader_sources(
):
    queries = [
        "forex trading forum",
        "forex traders community",
        "forex and trading groups on facebook"
        "retail forex traders discussion",
    ]

    all_results = []

    for q in queries:
        try:
            results = search_with_google_cse(
                query=q,
            )
            all_results.extend(results)
        except Exception as e:
            print(f"Failed query '{q}': {e}")

    # Deduplicate by URL
    seen = set()
    unique_results = []
    for r in all_results:
        if r["link"] not in seen:
            seen.add(r["link"])
            unique_results.append(r)

    return unique_results

def main():
    sources = find_forex_trader_sources()
    for s in sources:
        print(s)


if __name__ == "__main__":
    main()
