import asyncio
import logging
import traceback
from pathlib import Path

from sqlalchemy.orm import Session

from .config import JOBS_DATA_DIR
from .database import SessionLocal
from .models import Job, JobStep

logger = logging.getLogger(__name__)


def _update_job(db: Session, job_id: str, **kwargs):
    db.query(Job).filter(Job.id == job_id).update(kwargs)
    db.commit()


def _update_step(db: Session, step_id: int, **kwargs):
    db.query(JobStep).filter(JobStep.id == step_id).update(kwargs)
    db.commit()


def _get_step(db: Session, job_id: str, step_name: str) -> JobStep:
    return db.query(JobStep).filter(
        JobStep.job_id == job_id, JobStep.step_name == step_name
    ).first()


def run_pipeline(job_id: str):
    """在后台线程中运行完整管道"""
    db = SessionLocal()
    try:
        _run_pipeline_inner(db, job_id)
    except Exception as e:
        logger.error("Pipeline failed for job %s: %s", job_id, e)
        logger.error(traceback.format_exc())
        _update_job(db, job_id, status="failed", error_message=str(e))
        # 标记所有未完成的 step 为 failed
        db.query(JobStep).filter(
            JobStep.job_id == job_id,
            JobStep.status.in_(["pending", "running"])
        ).update({"status": "failed"}, synchronize_session="fetch")
        db.commit()
    finally:
        db.close()


def _run_pipeline_inner(db: Session, job_id: str):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise ValueError(f"Job {job_id} not found")

    assets_dir = JOBS_DATA_DIR / job_id / "product_assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # ===== Step 1: Scrape =====
    step = _get_step(db, job_id, "scrape")
    _update_step(db, step.id, status="running", detail="正在抓取商品信息...")
    _update_job(db, job_id, status="scraping", progress_pct=5.0)

    from .services.scraper_service import run_scraper
    loop = asyncio.new_event_loop()
    try:
        scrape_result = loop.run_until_complete(run_scraper(job.url, assets_dir))
    finally:
        loop.close()

    product_title = scrape_result.get("title")
    _update_step(db, step.id, status="completed",
                 detail=f"抓取完成: {scrape_result.get('text_lines', 0)} 行文案")
    _update_job(db, job_id, product_title=product_title, progress_pct=15.0)

    # 统计用户上传的图片数量（已在创建任务时保存到 assets_dir）
    image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
    image_count = sum(1 for f in assets_dir.iterdir() if f.name.startswith("upload_") and f.suffix.lower() in image_extensions)

    if image_count == 0:
        raise RuntimeError("未找到任何商品图片，请上传至少一张图片")

    # ===== Step 2: Generate Script =====
    step = _get_step(db, job_id, "generate_script")
    _update_step(db, step.id, status="running", detail="正在生成种草文案...")
    _update_job(db, job_id, status="composing", progress_pct=16.0)

    from .services.composition_service import generate_script
    generate_script(assets_dir)

    _update_step(db, step.id, status="completed", detail="种草文案已生成")
    _update_job(db, job_id, progress_pct=25.0)

    # ===== Step 3: Synthesize Audio =====
    step = _get_step(db, job_id, "synthesize_audio")
    _update_step(db, step.id, status="running", detail="正在合成语音与字幕...")
    _update_job(db, job_id, progress_pct=26.0)

    from .services.composition_service import synthesize_audio
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(synthesize_audio(assets_dir))
    finally:
        loop.close()

    _update_step(db, step.id, status="completed", detail="语音与字幕合成完成")
    _update_job(db, job_id, progress_pct=35.0)

    # ===== Step 4: Prepare Render =====
    step = _get_step(db, job_id, "prepare_render")
    _update_step(db, step.id, status="running", detail="正在准备渲染数据包...")
    _update_job(db, job_id, progress_pct=36.0)

    from .services.composition_service import prepare_render
    prepare_render(assets_dir)

    _update_step(db, step.id, status="completed", detail="渲染数据包已就绪")
    _update_job(db, job_id, progress_pct=45.0)

    # ===== Step 5: Generate Videos =====
    step = _get_step(db, job_id, "generate_videos")
    _update_step(db, step.id, status="running", detail=f"正在为 {image_count} 张图片生成视频...")
    _update_job(db, job_id, status="generating_videos", progress_pct=46.0)

    from .services.video_gen_service import run_video_generation
    gen_result = run_video_generation(assets_dir)

    _update_step(db, step.id, status="completed",
                 detail=f"视频生成完成: {gen_result['success']} 成功, {gen_result['failed']} 失败")
    _update_job(db, job_id, progress_pct=85.0)

    if gen_result["success"] == 0:
        raise RuntimeError("所有视频生成均失败")

    # ===== Step 6: Remotion Render =====
    step = _get_step(db, job_id, "render_video")
    _update_step(db, step.id, status="running", detail="正在渲染最终视频...")

    from .services.composition_service import render_video
    final_path = render_video(assets_dir)

    _update_step(db, step.id, status="completed", detail="视频渲染完成")
    _update_job(db, job_id,
                status="completed",
                progress_pct=100.0,
                final_video_path=str(final_path))
