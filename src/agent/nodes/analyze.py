import re
import os
from typing import Literal
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from pathlib import Path
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from agent.models import AgentState, Finding
from agent.prompts import ANALYZER_PROMPT

ENV_FILE_PATH = Path(__file__).parents[3] / ".env"
load_dotenv(ENV_FILE_PATH)

#--------------------------------------------- Output Schema ------------------------------------------------#

class LlmFinding(BaseModel):
    severity: Literal["high", "medium", "low"]
    file: str
    line: int
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)

class SecurityReview(BaseModel):
    findings: list[LlmFinding]


#--------------------------------------------- Model --------------------------------------------------------#

llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview",
    temperature=0.0,  # Gemini 3.0+ defaults to 1.0
    max_tokens=None,
    timeout=None,
    max_retries=2
)
structured_model = llm.with_structured_output(SecurityReview)



#--------------------------------------------- Node ---------------------------------------------------------#


async def analyze(state: AgentState) -> dict:
    file_chunks = parse_diff_by_file(state["diff"])
    focus = (
        state["reflection"]["focus_area"]
        if state.get("reflection") and state["reflection"].get("focus_area")
        else None
    )

    messages = [
        SystemMessage(content=ANALYZER_PROMPT),
        HumanMessage(content=_build_user_message(
            chunks=file_chunks,
            metadata=state["pr_metadata"],
            existing_findings=state.get("findings", []),
            focus_area=focus,
        )),
    ]

    response: SecurityReview = await structured_model.ainvoke(messages)

    return {
        "findings": state.get("findings", []) + [f.model_dump() for f in response.findings],
        "loop_count": state.get("loop_count", 0) + 1,
    }



#--------------------------------------------- Helper functions ---------------------------------------------#


def parse_diff_by_file(raw_diff: str) -> list[dict]:
    """Split a unified diff into per-file chunks with metadata."""
    file_chunks: list[dict] = []
    current = None

    for line in raw_diff.splitlines():
        if line.startswith("diff --git"):
            if current:
                file_chunks.append(current)
            match = re.search(r"diff --git a/(.+) b/(.+)", line)
            current = {
                "filename": match.group(2) if match else "unknown",
                "lines": [],
            }
        elif current is not None:
            current["lines"].append(line)

    if current:
        file_chunks.append(current)

    return [
        {"filename": chunk["filename"], "diff": "\n".join(chunk["lines"])}
        for chunk in file_chunks
    ]


def _build_user_message(
    chunks: list[dict],
    metadata: dict,
    existing_findings: list[Finding],
    focus_area: str | None,
) -> str:
    parts = [
        f"PR: {metadata['title']}",
        f"Author: {metadata['author']} | Base: {metadata['base_branch']}",
        f"Files changed: {metadata['changed_files']} | "
        f"+{metadata['additions']} -{metadata['deletions']}",
    ]

    if metadata.get("body"):
        parts.append(f"Description: {metadata['body']}")

    if existing_findings:
        parts.append(
            f"\nAlready found {len(existing_findings)} issue(s) in a prior pass. "
            "Do not re-report them. Focus on anything missed."
        )

    if focus_area:
        parts.append(f"Focus area for this pass: {focus_area}")

    for chunk in chunks:
        parts.append(f"\n--- {chunk['filename']} ---\n{chunk['diff']}")

    return "\n".join(parts)


def _extract_findings(response) -> list[Finding]:
    for block in response.content:
        if block.type == "tool_use" and block.name == "report_findings":
            return block.input.get("findings", [])
    return []




