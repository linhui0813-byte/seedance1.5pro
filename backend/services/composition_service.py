import asyncio
import shutil
import sys
from pathlib import Path

from ..config import PROJECT_ROOT, REMOTION_PROJECT_DIR, BGM_TEMPLATE_DIR

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def generate_script(assets_dir: Path) -> str:
    """生成种草文案"""
    from video_pipeline import generate_script_with_deepseek
    return generate_script_with_deepseek(assets_dir=assets_dir)


async def synthesize_audio(assets_dir: Path) -> float:
    """合成语音和字幕，返回音频时长"""
    from video_pipeline import synthesize_audio_and_subtitles
    return await synthesize_audio_and_subtitles(assets_dir=assets_dir)


def prepare_render(assets_dir: Path) -> Path:
    """准备渲染数据，返回 render_data.json 路径"""
    # 复制 BGM 文件到 job assets_dir
    bgm_dest = assets_dir / "bgm"
    if BGM_TEMPLATE_DIR.exists() and not bgm_dest.exists():
        shutil.copytree(BGM_TEMPLATE_DIR, bgm_dest)

    from video_pipeline import prepare_render_data
    return prepare_render_data(
        audio_duration=_get_audio_duration(assets_dir),
        assets_dir=assets_dir,
        remotion_project_dir=REMOTION_PROJECT_DIR,
    )


def render_video(assets_dir: Path) -> Path:
    """触发 Remotion 渲染，返回最终视频路径"""
    from video_pipeline import trigger_remotion_render
    return trigger_remotion_render(
        assets_dir=assets_dir,
        remotion_project_dir=REMOTION_PROJECT_DIR,
    )


def _get_audio_duration(assets_dir: Path) -> float:
    """读取已生成的 voiceover.mp3 时长"""
    from mutagen.mp3 import MP3
    audio_file = assets_dir / "voiceover.mp3"
    if audio_file.exists():
        return MP3(str(audio_file)).info.length
    return 0.0
