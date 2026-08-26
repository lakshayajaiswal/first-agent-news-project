"""
URL Normalization and Canonicalization Engine.
Removes marketing tracking parameters, normalizes protocols/hosts, and resolves canonical paths.
"""

from __future__ import annotations
import urllib.parse
from typing import Set

# Common tracking parameters to strip
TRACKING_PARAMS: Set[str] = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_name",
    "fbclid",
    "gclid",
    "msclkid",
    "mc_eid",
    "mc_cid",
    "_hsenc",
    "_hsmi",
    "mkt_tok",
    "ref",
    "source",
}


def canonicalize_url(url: str, base_url: str = "") -> str:
    """
    Produce a clean canonical URL:
    - Resolves relative links against base_url
    - Converts scheme and netloc to lowercase
    - Strips URL fragments (#section)
    - Removes known analytics/tracking query params
    - Sorts remaining query parameters
    - Normalizes trailing slashes
    """
    if not url:
        return ""

    url_str = url.strip()

    # Handle relative URLs
    if base_url and not urllib.parse.urlparse(url_str).netloc:
        url_str = urllib.parse.urljoin(base_url, url_str)

    parsed = urllib.parse.urlsplit(url_str)

    scheme = parsed.scheme.lower() if parsed.scheme else "https"
    netloc = parsed.netloc.lower()

    # Strip default ports
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    # Normalize path: collapse multi-slashes
    path = parsed.path or "/"
    while "//" in path:
        path = path.replace("//", "/")

    # If path is longer than 1 character and ends in slash (unless root), keep consistent
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    # Parse and clean query parameters
    query_params = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
    filtered_params = [
        (k, v) for k, v in query_params if k.lower() not in TRACKING_PARAMS and not k.startswith("utm_")
    ]
    # Sort query params deterministically
    filtered_params.sort(key=lambda x: (x[0], x[1]))
    
    new_query = urllib.parse.urlencode(filtered_params)

    # Reconstruct without fragment
    return urllib.parse.urlunsplit((scheme, netloc, path, new_query, ""))
