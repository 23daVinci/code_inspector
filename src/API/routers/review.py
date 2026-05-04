import uuid
import json
import asyncio
from fastapi import APIRouter, status, HTTPException
from sse_starlette.sse import EventSourceResponse

from API.models import ReviewRequest, ReviewResponse, Job
from agent.graph import CodeInspectorAgent


router = APIRouter(prefix="/v1", tags=["review"])
agent = CodeInspectorAgent()

# In-memory job store — replace with Redis or a DB for multi-process deployments
_jobs: dict[str, Job] = {}
_queues: dict[str, asyncio.Queue] = {}


# ── Background task helpers ────────────────────────────────────────────────────

async def _run_review(job_id: str, pr_url: str) -> None:
    config = {"configurable": {"thread_id": job_id}}
    queue = _queues[job_id]
    try:
        async for event in agent.stream_events(pr_url=pr_url, config=config):
            await queue.put(event)
        _jobs[job_id] = Job(id=job_id, status="awaiting_approval")
    except Exception as e:
        _jobs[job_id] = Job(id=job_id, status="error", error=str(e))
        await queue.put({"status": "error", "error": str(e)})


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/review", response_model=ReviewResponse,
             status_code=status.HTTP_202_ACCEPTED)
async def create_review(body: ReviewRequest) -> ReviewResponse:
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = Job(id=job_id, status="running")
    _queues[job_id] = asyncio.Queue()
    asyncio.create_task(_run_review(job_id, body.pr_url))
    return ReviewResponse(job_id=job_id, status="running")


@router.get("/review/{job_id}/stream")
async def stream_review(job_id: str) -> EventSourceResponse:
    if job_id not in _jobs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    async def event_generator():
        queue = _queues[job_id]
        while True:
            event = await queue.get()
            yield json.dumps(event)
            terminal_statuses = {"awaiting_approval", "error"}
            if event.get("status") in terminal_statuses:
                _queues.pop(job_id, None)
                break

    return EventSourceResponse(event_generator())
