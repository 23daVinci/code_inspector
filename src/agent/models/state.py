from typing import Annotated, TypedDict, Literal
from langgraph.graph.message import add_messages

class Finding(TypedDict):
    severity: Literal["high", "medium", "low"]
    file: str
    line: int
    description: str
    confidence: float          # 0.0–1.0

class Reflection(TypedDict):
    should_loop: bool
    reason: str
    focus_area: str | None     # hint to analyze on next pass

class AgentState(TypedDict):
    # Input
    pr_url: str

    # Fetched data
    diff: str
    pr_metadata: dict

    cve_data: list[dict]        # populated by osv_lookup
    owasp_mappings: list[dict]  # populated by owasp_classify
    orphan_cves: list[dict]     # CVEs with no matching finding

    # LLM conversation history (auto-merges via reducer)
    messages: Annotated[list, add_messages]

    # Analysis outputs (accumulate across loops)
    findings: list[Finding]
    reflection: Reflection | None

    # Loop control
    loop_count: int

    # Output
    comment_body: str

    # Error handling
    error: dict | None         # {"node": str, "message": str}