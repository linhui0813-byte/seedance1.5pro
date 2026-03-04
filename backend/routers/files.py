from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import JOBS_DATA_DIR

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/{job_id}/{filename}")
def serve_file(job_id: str, filename: str):
    """提供生成的文件下载（视频、音频等）"""
    file_path = JOBS_DATA_DIR / job_id / "product_assets" / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # 安全检查：确保路径在 jobs_data 内
    try:
        file_path.resolve().relative_to(JOBS_DATA_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    media_types = {
        ".mp4": "video/mp4",
        ".mp3": "audio/mpeg",
        ".vtt": "text/vtt",
        ".json": "application/json",
        ".txt": "text/plain; charset=utf-8",
    }
    media_type = media_types.get(file_path.suffix, "application/octet-stream")

    return FileResponse(file_path, media_type=media_type, filename=filename)
