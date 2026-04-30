import uuid
import asyncio
from fastapi import APIRouter

from API.models import ReviewRequest, ReviewResponse, Job
from agent.graph import run_agent

router = APIRouter(prefix="/v1", tags=["review"])


@router.post("/review", response_model=ReviewResponse)
async def create_review(body: ReviewRequest):
    job_id = str(uuid.uuid4())[:6]
    job = Job(id=job_id, status="running")

    config = {"configurable": {"thread_id": job.id}}
    
    asyncio.create_task(run_agent(pr_url=body.pr_url, config=config))
    return ReviewResponse(
                            job_id=job.id,
                            status=job.status,
                        )