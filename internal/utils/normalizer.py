from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import re
from typing import Optional, List


EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DIGITS_ONLY = re.compile(r"\D+")

# Add more 20 country calling codes here
COUNTRY_CALLING_CODES = {
    "AE": "+971",
    "SA": "+966",
    "EG": "+20",
    "LB": "+961",
    "JO": "+962",
    "PS": "+970",
    "QA": "+974",
    "KW": "+965",
    "NR": "+674",
    "NZ": "+64",
    "AU": "+61",
    "US": "+1",
    "CA": "+1",
    "GB": "+44",
    "DE": "+49",
    "FR": "+33",
    "ES": "+34",
    "NG": "+234",
    "ZA": "+27",
    "IN": "+91",
    "CN": "+86",
    "JP": "+81",
    "KR": "+82",
    "TW": "+886",
    "HK": "+852",
    "MO": "+853",
    "SG": "+65",
    "MY": "+60",
    "PH": "+63",
    "TH": "+66",
    "VN": "+84",
    "ID": "+62",
}

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


def normalize_phone(phone: str, country_acronym: str) -> Optional[str]:
    if not phone or not country_acronym:
        return None
    digits = DIGITS_ONLY.sub("", phone)

    country_code = COUNTRY_CALLING_CODES.get(country_acronym)
    if not country_code:
        return None

    if digits.startswith("0"):
        digits = digits[1:]

    if digits.startswith(country_code.replace("+", "")):
        return f"+{digits}"

    return f"{country_code}{digits}"

def normalize_email(email: str) -> Optional[str]:
    if not isinstance(email, str):
        return None

    email = email.strip().lower()

    return email if EMAIL_REGEX.match(email) else None

def flatten_list(nested_list: List[List]):
    if not nested_list:
        return
    flat_list = [item for sublist in nested_list for item in sublist]

    return flat_list


def flatten_list(nested_list: List[List]):
    if not nested_list:
        return
    flat_list = [item for sublist in nested_list for item in sublist]

    return flat_list