import os
import httpx

from models import AgentState
from utils import parse_pr_url

GITHUB_API = "https://api.github.com"

HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
}

# ── Node ───────────────────────────────────────────────────────────────────────

async def post_comment(state: AgentState) -> dict:
    owner, repo, pr_number = parse_pr_url(state["pr_url"])

    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
        resp = await client.post(
            f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments",
            json={"body": state["comment_body"]},
        )

        if resp.status_code == 401:
            return {"error": {"node": "post_comment", "message": "Invalid or missing GITHUB_TOKEN."}}
        if resp.status_code == 403:
            return {"error": {"node": "post_comment", "message": "Token lacks write permission on this repo."}}
        if resp.status_code == 404:
            return {"error": {"node": "post_comment", "message": "Repo or PR not found. Check the URL."}}

        resp.raise_for_status()

    return {"error": None}