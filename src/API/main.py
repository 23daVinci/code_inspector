from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from API.routers import health, review

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="Code Inspector API",
    description="",
    version="0.0.1"
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(review.router)

@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(STATIC_DIR / "index.html")