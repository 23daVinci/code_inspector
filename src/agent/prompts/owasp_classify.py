

# ── OWASP Top 10 reference ─────────────────────────────────────────────────────

_OWASP_TOP_10 = {
    "A01": "Broken Access Control",
    "A02": "Cryptographic Failures",
    "A03": "Injection",
    "A04": "Insecure Design",
    "A05": "Security Misconfiguration",
    "A06": "Vulnerable and Outdated Components",
    "A07": "Identification and Authentication Failures",
    "A08": "Software and Data Integrity Failures",
    "A09": "Security Logging and Monitoring Failures",
    "A10": "Server-Side Request Forgery",
}

_OWASP_DESCRIPTIONS = "\n".join(
    f"- {code}: {name}" for code, name in _OWASP_TOP_10.items()
)


# ── System prompt ──────────────────────────────────────────────────────────────

OWASP_PROMPT = f"""You are a security expert familiar with the OWASP Top 10 (2021).

You will be given a list of security findings from a code review. 
Map each finding to the most relevant OWASP Top 10 category.

OWASP Top 10 categories:
{_OWASP_DESCRIPTIONS}

Rules:
- Every finding must be mapped to exactly one category
- Use finding_index to reference which finding you are mapping (0-based)
- Keep rationale to one concise sentence
- Prefer the most specific category over a generic one"""