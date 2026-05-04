from pydantic import BaseModel
from typing import Literal


class Job(BaseModel):
    id: str
    status: Literal["running", "awaiting_approval", "done", "error"]
    state: dict | None = None
    error: str | None = None


