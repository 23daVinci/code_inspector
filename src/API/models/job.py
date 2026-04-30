from pydantic import BaseModel
from typing import Literal

from agent.models import AgentState

class Job(BaseModel):
    id: str
    status: Literal["running", "awaiting_approval", "done", "error"]
    state: AgentState | None = None
    error: str | None = None


