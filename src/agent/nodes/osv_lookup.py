import os
import re
import httpx
from dotenv import load_dotenv
from pathlib import Path

from agent.models import AgentState

ENV_FILE_PATH = Path(__file__).parents[3] / ".env"
load_dotenv(ENV_FILE_PATH)

# ── Ecosystem mapping ──────────────────────────────────────────────────────────

PACKAGE_FILES = {
    "requirements.txt": "PyPI",
    "requirements-dev.txt": "PyPI",
    "Pipfile": "PyPI",
    "pyproject.toml": "PyPI",
    "package.json": "npm",
    "package-lock.json": "npm",
    "yarn.lock": "npm",
    "Gemfile": "RubyGems",
    "Gemfile.lock": "RubyGems",
    "go.mod": "Go",
    "go.sum": "Go",
    "Cargo.toml": "crates.io",
    "Cargo.lock": "crates.io",
    "pom.xml": "Maven",
    "build.gradle": "Maven",
}

# ── Parsers ────────────────────────────────────────────────────────────────────

def parse_packages_from_diff(diff: str) -> list[dict]:
    """Extract added/changed packages from diff across all supported ecosystems."""
    packages = []
    current_file = None

    for line in diff.splitlines():
        if line.startswith("diff --git"):
            match = re.search(r"b/(.+)$", line)
            if match:
                filename = match.group(1).split("/")[-1]
                current_file = filename if filename in PACKAGE_FILES else None

        if current_file and line.startswith("+") and not line.startswith("+++"):
            ecosystem = PACKAGE_FILES[current_file]
            extracted = _parse_line(line[1:].strip(), current_file, ecosystem)
            packages.extend(extracted)

    # Deduplicate by name + ecosystem
    seen = set()
    unique = []
    for p in packages:
        key = (p["name"], p["ecosystem"])
        if key not in seen:
            seen.add(key)
            unique.append(p)

    return unique



def _parse_line(line: str, filename: str, ecosystem: str) -> list[dict]:
    """Parse a single diff line into package dicts based on file type."""
    packages = []

    if filename in ("requirements.txt", "requirements-dev.txt"):
        # flask==2.0.1 or flask>=2.0.1 or flask~=2.0.1
        match = re.match(r"^([A-Za-z0-9_\-\.]+)\s*[=><~!]+\s*([\d\.]+)", line)
        if match:
            packages.append({
                "name": match.group(1).lower(),
                "version": match.group(2),
                "ecosystem": ecosystem,
            })

    elif filename == "package.json":
        # "lodash": "^4.17.15"
        match = re.match(r'^\s*"([^"]+)"\s*:\s*"[\^~]?([\d\.]+)"', line)
        if match and not match.group(1).startswith("@types"):
            packages.append({
                "name": match.group(1),
                "version": match.group(2),
                "ecosystem": ecosystem,
            })

    elif filename == "go.mod":
        # require github.com/gin-gonic/gin v1.9.1
        match = re.match(r"^\s*([^\s]+)\s+v([\d\.]+)", line)
        if match:
            packages.append({
                "name": match.group(1),
                "version": match.group(2),
                "ecosystem": ecosystem,
            })

    elif filename == "Cargo.toml":
        # serde = "1.0.160" or serde = { version = "1.0.160" }
        match = re.match(r'^([a-z0-9_\-]+)\s*=\s*["{].*?([\d]+\.[\d]+\.[\d]+)', line)
        if match:
            packages.append({
                "name": match.group(1),
                "version": match.group(2),
                "ecosystem": ecosystem,
            })

    return packages



# ── OSV batch query ────────────────────────────────────────────────────────────

async def _query_osv_batch(packages: list[dict]) -> list[dict]:
    """Send a single batch request to OSV and return flat list of CVEs."""
    payload = {
        "queries": [
            {
                "package": {
                    "name": p["name"],
                    "ecosystem": p["ecosystem"],
                },
                "version": p["version"],
            }
            for p in packages
        ]
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(f"{os.getenv('OSV_API')}/querybatch", json=payload)
        resp.raise_for_status()
        data = resp.json()

    cve_data = []
    for i, result in enumerate(data.get("results", [])):
        for vuln in result.get("vulns", []):
            cve_data.append({
                "package": packages[i]["name"],
                "ecosystem": packages[i]["ecosystem"],
                "version": packages[i]["version"],
                "id": vuln["id"],
                "summary": vuln.get("summary", "No summary available"),
                "severity": _extract_severity(vuln),
                "aliases": [
                    a for a in vuln.get("aliases", [])
                    if a.startswith("CVE-")
                ],
            })

    return cve_data


def _extract_severity(vuln: dict) -> str | None:
    """Extract CVSS severity label from OSV vulnerability object."""
    for severity in vuln.get("severity", []):
        score = severity.get("score", "")
        # CVSS score is like "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
        match = re.search(r"(\d+\.\d+)$", score)
        if match:
            score_val = float(match.group(1))
            if score_val >= 9.0:   return "critical"
            if score_val >= 7.0:   return "high"
            if score_val >= 4.0:   return "medium"
            return "low"
    return None




# ── Node ───────────────────────────────────────────────────────────────────────

async def osv_lookup(state: AgentState) -> dict:
    packages = parse_packages_from_diff(state["diff"])

    if not packages:
        return {"cve_data": []}

    try:
        cve_data = await _query_osv_batch(packages)
    except httpx.HTTPError as e:
        # OSV being down should not crash the agent — degrade gracefully
        print(f"OSV lookup failed: {e}")
        return {"cve_data": []}

    return {"cve_data": cve_data}