from fastapi import FastAPI
from API.routers import health, review


app = FastAPI(
    title="Code Inspector API",
    description="",
    version="0.0.1"
)

app.include_router(review.router)