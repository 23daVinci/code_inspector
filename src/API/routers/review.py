import uuid
import asyncio
from fastapi import APIRouter, HTTPException

from API.models import ReviewRequest, ReviewResponse, DecisionRequest, Job
from agent.graph import CodeInspectorAgent


router = APIRouter(prefix="/v1", tags=["review"])
agent = CodeInspectorAgent()

# In-memory job store — replace with Redis or a DB for multi-process deployments
_jobs: dict[str, Job] = {}


# ── Background task helpers ────────────────────────────────────────────────────

async def _run_review(job_id: str, pr_url: str) -> None:
    config = {"configurable": {"thread_id": job_id}}
    try:
        result = await agent.run(pr_url=pr_url, config=config)
        _jobs[job_id] = Job(id=job_id, status="awaiting_approval", state=result)
    except Exception as e:
        _jobs[job_id] = Job(id=job_id, status="error", error=str(e))


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/review", response_model=ReviewResponse, status_code=202)
async def create_review(body: ReviewRequest) -> ReviewResponse:
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = Job(id=job_id, status="running")
    asyncio.create_task(_run_review(job_id, body.pr_url))
    return ReviewResponse(job_id=job_id, status="running")
