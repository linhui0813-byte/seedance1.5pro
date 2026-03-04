import asyncio
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db, SessionLocal
from ..models import Job
from ..schemas import JobOut

router = APIRouter(prefix="/api/jobs", tags=["progress"])


@router.get("/{job_id}/progress")
async def job_progress_sse(job_id: str):
    """SSE 实时进度流"""

    async def event_generator():
        last_status = None
        last_pct = -1.0

        while True:
            db = SessionLocal()
            try:
                job = db.query(Job).filter(Job.id == job_id).first()
                if not job:
                    yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                    return

                # 仅在状态或进度变化时推送
                if job.status != last_status or job.progress_pct != last_pct:
                    last_status = job.status
                    last_pct = job.progress_pct

                    job_data = JobOut.model_validate(job).model_dump(mode="json")
                    yield f"data: {json.dumps(job_data, ensure_ascii=False)}\n\n"

                    if job.status in ("completed", "failed"):
                        return
            finally:
                db.close()

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
