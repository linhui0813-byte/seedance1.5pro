import shutil
import threading
from typing import List

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from ..config import JOBS_DATA_DIR
from ..database import get_db
from ..models import Job, JobStep
from ..schemas import JobOut, JobListOut
from ..job_runner import run_pipeline

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# 管道步骤模板
PIPELINE_STEPS = [
    (1, "scrape",              "抓取商品详情"),
    (2, "generate_script",     "生成种草文案"),
    (3, "generate_moments_copy", "生成朋友圈文案"),
    (4, "synthesize_audio",   "合成语音与字幕"),
    (5, "prepare_render",      "准备渲染数据"),
    (6, "generate_videos",     "生成视频片段"),
    (7, "render_video",       "渲染最终视频"),
]


@router.post("/", response_model=JobOut)
def create_job(
    url: str = Form(...),
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    if not images:
        raise HTTPException(status_code=422, detail="请至少上传一张商品图片")

    job = Job(url=url)
    db.add(job)
    db.flush()

    # 保存上传的图片到 product_assets 目录
    assets_dir = JOBS_DATA_DIR / job.id / "product_assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    for idx, img in enumerate(images, start=1):
        ext = img.filename.rsplit(".", 1)[-1] if "." in (img.filename or "") else "jpg"
        dest = assets_dir / f"upload_{idx:02d}.{ext}"
        with open(dest, "wb") as f:
            shutil.copyfileobj(img.file, f)

    for order, name, display in PIPELINE_STEPS:
        step = JobStep(
            job_id=job.id,
            step_order=order,
            step_name=name,
            display_name=display,
        )
        db.add(step)

    db.commit()
    db.refresh(job)

    # 启动后台线程
    t = threading.Thread(target=run_pipeline, args=(job.id,), daemon=True)
    t.start()

    return job


@router.get("/", response_model=list[JobListOut])
def list_jobs(db: Session = Depends(get_db)):
    return db.query(Job).order_by(Job.created_at.desc()).limit(50).all()


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
