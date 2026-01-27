from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

def normalize_url(
    url: str,
    *,
    strip_www: bool = True,
    force_https: bool = False
) -> str:
    """
    Normalize a URL for reliable comparison.

    Args:
        url: The URL to normalize
        strip_www: Remove leading 'www.' from hostname
        force_https: Convert http -> https

    Returns:
        Normalized URL string
    """
    parsed = urlparse(url.strip())

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")  # remove trailing slash
    query = parsed.query
    fragment = ""  # ignore fragments

    # Optionally force HTTPS
    if force_https and scheme == "http":
        scheme = "https"

    # Remove default ports
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    # Strip www
    if strip_www and netloc.startswith("www."):
        netloc = netloc[4:]

    # Normalize query parameters (order-independent)
    if query:
        query = urlencode(sorted(parse_qsl(query, keep_blank_values=True)))

    return urlunparse((scheme, netloc, path, "", query, fragment))


def urls_equal(url1: str, url2: str) -> bool:
    return normalize_url(url1) == normalize_url(url2)
