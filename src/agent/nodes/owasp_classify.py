from typing import Literal
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from agent.models import AgentState
from agent.prompts import OWASP_PROMPT


# ── Output schema ──────────────────────────────────────────────────────────────

OWASPCode = Literal["A01", "A02", "A03", "A04", "A05", 
                    "A06", "A07", "A08", "A09", "A10"]

class OWASPMapping(BaseModel):
    finding_index: int          # index into state["findings"]
    owasp_code: OWASPCode
    owasp_name: str
    rationale: str              # one sentence explaining why this finding maps here

class OWASPClassification(BaseModel):
    mappings: list[OWASPMapping]


# ── Model ──────────────────────────────────────────────────────────────────────

llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview",
    temperature=0.0,  # Gemini 3.0+ defaults to 1.0
    max_tokens=None,
    timeout=None,
    max_retries=2
)
structured_model = llm.with_structured_output(OWASPClassification)


# ── Node ───────────────────────────────────────────────────────────────────────

async def owasp_classify(state: AgentState) -> dict:
    findings = state.get("findings", [])

    if not findings:
        return {"owasp_mappings": []}

    findings_text = "\n".join(
        f"{i}. [{f['severity'].upper()}] {f['file']} line {f['line']}: {f['description']}"
        for i, f in enumerate(findings)
    )

    messages = [
        SystemMessage(content=OWASP_PROMPT),
        HumanMessage(content=f"Classify these findings:\n\n{findings_text}"),
    ]

    response: OWASPClassification = await structured_model.ainvoke(messages)

    return {"owasp_mappings": [m.model_dump() for m in response.mappings]}