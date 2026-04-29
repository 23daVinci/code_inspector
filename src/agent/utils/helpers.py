import re


def parse_pr_url(url: str) -> tuple[str, str, int]:
    """Extract owner, repo, pr_number from a GitHub PR URL."""
    pattern = r"github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.search(pattern, url)
    if not match:
        raise ValueError(f"Could not parse PR URL: {url}")
    owner, repo, number = match.groups()
    return owner, repo, int(number)
