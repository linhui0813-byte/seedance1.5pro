import sys
from pathlib import Path

from ..config import PROJECT_ROOT

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_video_generation(assets_dir: Path) -> dict:
    """
    调用 generate_video.py 批量生成视频。
    assets_dir 中应有 .jpg/.png 图片 和 详情文案.txt。
    返回: {"success": int, "failed": int}
    """
    from generate_video import scan_directory, create_and_poll_task, download_video
    import os
    import logging

    logger = logging.getLogger(__name__)

    image_files, _ = scan_directory(str(assets_dir))

    if not image_files:
        logger.warning("未在 %s 找到图片文件", assets_dir)
        return {"success": 0, "failed": 0}

    prompt = "生成一个模特自由摆造型的视频，不要有任何背景音乐，不要有任何旁白"
    success_count = 0
    fail_count = 0

    for i, image_path in enumerate(image_files, 1):
        image_name = os.path.basename(image_path)
        logger.info("[%d/%d] 正在生成视频: %s", i, len(image_files), image_name)

        try:
            video_url = create_and_poll_task(image_path, prompt)
            if video_url:
                base_name = os.path.splitext(image_name)[0]
                video_output_path = os.path.join(str(assets_dir), f"{base_name}.mp4")
                if download_video(video_url, video_output_path):
                    success_count += 1
                else:
                    fail_count += 1
            else:
                fail_count += 1
        except Exception as e:
            logger.error("视频生成失败 %s: %s", image_name, e)
            fail_count += 1

    return {"success": success_count, "failed": fail_count}
