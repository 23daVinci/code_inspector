from agent.models.state import AgentState

def consolidate_findings(state: AgentState) -> dict:
    """
    Merge raw findings, OWASP mappings, and CVE data into a single
    enriched findings list ready for reflect and format_comment.
    """
    findings = state.get("findings", [])
    owasp_mappings = state.get("owasp_mappings", [])
    cve_data = state.get("cve_data", [])

    # Index OWASP mappings by finding_index for O(1) lookup
    owasp_by_index = {m["finding_index"]: m for m in owasp_mappings}

    # Index CVEs by package name for O(1) lookup
    cves_by_package = {}
    for cve in cve_data:
        cves_by_package.setdefault(cve["package"], []).append(cve)

    enriched = []
    for i, finding in enumerate(findings):

        # Attach OWASP mapping
        owasp = owasp_by_index.get(i)

        # Attach CVEs — match by any package name mentioned in the finding description
        related_cves = []
        for package, cves in cves_by_package.items():
            if package.lower() in finding["description"].lower():
                related_cves.extend(cves)

        enriched.append({
            **finding,
            "owasp_code": owasp["owasp_code"] if owasp else None,
            "owasp_name": owasp["owasp_name"] if owasp else None,
            "owasp_rationale": owasp["rationale"] if owasp else None,
            "related_cves": related_cves,
        })

    # Attach orphan CVEs — packages with CVEs not mentioned in any finding
    mentioned_packages = {
        package
        for finding in enriched
        for package in cves_by_package
        if package.lower() in finding["description"].lower()
    }
    orphan_cves = [
        cve
        for package, cves in cves_by_package.items()
        if package not in mentioned_packages
        for cve in cves
    ]

    return {
        "findings": enriched,
        "orphan_cves": orphan_cves,
    }