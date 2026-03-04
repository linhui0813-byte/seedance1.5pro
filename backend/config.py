from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 数据库
DATABASE_URL = f"sqlite:///{PROJECT_ROOT / 'jobs.db'}"

# 工作目录
JOBS_DATA_DIR = PROJECT_ROOT / "jobs_data"
JOBS_DATA_DIR.mkdir(exist_ok=True)

# 原始脚本路径
SCRAPER_SCRIPT = PROJECT_ROOT / "scraper.py"
GENERATE_VIDEO_SCRIPT = PROJECT_ROOT / "generate_video.py"
VIDEO_PIPELINE_SCRIPT = PROJECT_ROOT / "video_pipeline.py"

# Remotion 项目
REMOTION_PROJECT_DIR = PROJECT_ROOT / "remotion-project"

# BGM 模板目录（用于复制到 job 目录）
BGM_TEMPLATE_DIR = PROJECT_ROOT / "product_assets" / "bgm"

# Chrome 数据目录
CHROME_DATA_DIR = PROJECT_ROOT / "chrome_data"
