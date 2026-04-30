from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from agent.prompts import REFLECTION_PROMPT
from agent.models import AgentState


# ── Output schema ──────────────────────────────────────────────────────────────

class Reflection(BaseModel):
    should_loop: bool
    reason: str
    focus_area: str | None

#--------------------------------------------- Model --------------------------------------------------------#

llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite-preview",
    temperature=0.0,  # Gemini 3.0+ defaults to 1.0
    max_tokens=None,
    timeout=None,
    max_retries=2
)
structured_model = llm.with_structured_output(Reflection)

#-------------------------------------------------- Node -------------------------------------------------#

async def reflect(state: AgentState) -> dict:
    findings_summary = "\n".join([
        f"- [{f.severity.upper()}] {f.file} line {f.line}: {f.description} "
        f"(confidence: {f.confidence})"
        for f in state["findings"]
    ])

    messages = [
        SystemMessage(content=REFLECTION_PROMPT),
        HumanMessage(content=f"""PR: {state['pr_metadata']['title']}
                                Files changed: {state['pr_metadata']['changed_files']}
                                +{state['pr_metadata']['additions']} -{state['pr_metadata']['deletions']}

                                Diff:
                                {state['diff']}

                                Findings so far:
                                {findings_summary}

                                Is this analysis complete?"""),
                ]

    response: Reflection = await structured_model.ainvoke(messages)

    return {"reflection": response.model_dump()} 
