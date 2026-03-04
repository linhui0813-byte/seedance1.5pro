import asyncio
import sys
from pathlib import Path

from ..config import PROJECT_ROOT

# 确保项目根目录在 sys.path 中
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


async def run_scraper(url: str, assets_dir: Path) -> dict:
    """
    调用 scraper.py 的 scrape_product 函数。
    返回: {"title": str|None, "text_lines": int, "images": [str]}
    """
    from scraper import scrape_product
    result = await scrape_product(url, assets_dir=str(assets_dir))
    return result or {"title": None, "text_lines": 0, "images": []}
