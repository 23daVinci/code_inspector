import re
import httpx

from models.state import AgentState


GITHUB_API = "https://api.github.com"

HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def parse_pr_url(url: str) -> tuple[str, str, int]:
    """Extract owner, repo, pr_number from a GitHub PR URL."""
    pattern = r"github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.search(pattern, url)
    if not match:
        raise ValueError(f"Could not parse PR URL: {url}")
    owner, repo, number = match.groups()
    return owner, repo, int(number)


async def fetch_pr(state: AgentState) -> dict:
    owner, repo, pr_number = parse_pr_url(state["pr_url"])

    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:

        # 1. PR metadata
        meta_resp = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}"
        )
        if meta_resp.status_code == 404:
            return {"error": {"node": "fetch_pr", "message": f"PR not found: {state['pr_url']}"}}
        if meta_resp.status_code == 403:
            return {"error": {"node": "fetch_pr", "message": "Rate limited. Try again in a minute."}}
        meta_resp.raise_for_status()
        meta = meta_resp.json()

        # 2. Diff
        diff_resp = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}",
            headers={**HEADERS, "Accept": "application/vnd.github.v3.diff"},
        )
        diff_resp.raise_for_status()

    return {
        "diff": diff_resp.text,
        "pr_metadata": {
            "title": meta["title"],
            "body": meta["body"] or "",
            "author": meta["user"]["login"],
            "base_branch": meta["base"]["ref"],
            "head_branch": meta["head"]["ref"],
            "changed_files": meta["changed_files"],
            "additions": meta["additions"],
            "deletions": meta["deletions"],
            "html_url": meta["html_url"],
        },
        "error": None,
    }
