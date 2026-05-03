from pydantic import BaseModel
from typing import Literal


class ReviewRequest(BaseModel):
    pr_url: str


class ReviewResponse(BaseModel):
    job_id: str
    status: Literal["running", "awaiting_approval", "done", "error"]
