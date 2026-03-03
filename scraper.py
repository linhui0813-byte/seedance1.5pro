"""
电商商品详情页素材本地下载脚本 — 网络拦截版

文字提取：尽力从主页面可见文本中提取。
"""

import asyncio
import logging
import os
import re
import shutil
import sys

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from playwright_stealth import Stealth

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
CHROME_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_data")
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "product_assets")
NAV_TIMEOUT_MS = 60_000
SCROLL_STEP_PX = 1500
SCROLL_PAUSE_MS = 300
SCROLL_TIMEOUT_SEC = 300  # 滚动最大超时时间（5 分钟）

# <p> 标签内容提取正则
P_TAG_RE = re.compile(r'<p[^>]*>(.*?)</p>', re.IGNORECASE | re.DOTALL)

# .title-content 商品标题提取正则（用于网络拦截中提取 1688 商品标题）
TITLE_CONTENT_RE = re.compile(
    r'<div[^>]*class="[^"]*title-content[^"]*"[^>]*>(.*?)</div>',
    re.IGNORECASE | re.DOTALL,
)

# 剔除内嵌 HTML 标签（<span>、<br>、<b> 等）
STRIP_HTML_RE = re.compile(r'<[^>]+>')


# ---------------------------------------------------------------------------
# 步骤一：创建本地资产文件夹
# ---------------------------------------------------------------------------

def prepare_assets_dir():
    """创建 product_assets 文件夹，已存在则清空。"""
    if os.path.exists(ASSETS_DIR):
        shutil.rmtree(ASSETS_DIR)
    os.makedirs(ASSETS_DIR)
    logger.info("资产文件夹已就绪: %s", ASSETS_DIR)


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# 文本清洗（特征排除法）
# ---------------------------------------------------------------------------

# CSS 特征关键词
_CSS_KEYWORDS = ["px;", "margin:", "padding:", "font-size", "color:", "!important", "rgb("]
# JS/JSON 特征关键词
_CODE_KEYWORDS = ["function", "var ", "let ", "=>", '{"', '":[']
# 高密度符号集合
_CODE_SYMBOLS = set("{};<>=_")
# HTML 实体
_HTML_ENTITY_RE = re.compile(r'&(?:nbsp|amp|lt|gt|quot|apos|#\d+|#x[\da-fA-F]+);')
# 未解码的 Unicode 转义（JSON 残余，如 \u4e3a）
_UNESCAPED_UNICODE_RE = re.compile(r'\\u[0-9a-fA-F]{4}')
# 中文字符或英文字母（用于判断是否包含有意义的文字）
_HAS_MEANINGFUL_CHAR_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbfa-zA-Z]')
# 黑名单关键词（免责声明 + 平台 UI 交互 + 无关内容）
_BLACKLIST_KEYWORDS = [
    "保障经营合法合规", "刀具", "郑重承诺", "温馨提示", "免责声明",
    "不作为商品描述", "不代表产品", "仅供参考", "请以实物为准",
    "投诉举报", "违禁信息", "知识产权",
    "编辑商品", "登陆推荐更精准", "翻译", "搜索", "复制", "点击链接进入",
    "尺码推荐", "搭配", "主播", "斤",
]


def clean_title(raw: str) -> str | None:
    """
    清洗 <h1> 商品标题 —— 白名单保护，仅做基础清洗，不经过严格过滤。

    规则：
      1. 剥离嵌套的 HTML 标签（<span>、<br> 等）
      2. 清除 HTML 实体（&nbsp; 等）
      3. 按换行符截断，只保留第一行（排除按钮文字如"编辑商品"）
      4. 兜底移除标题中可能残留的特定脏词
    """
    text = STRIP_HTML_RE.sub('', raw)
    text = _HTML_ENTITY_RE.sub(' ', text)
    # 按换行截断，只保留第一行
    text = text.split('\n')[0].strip()
    # 兜底：移除可能残留的操作按钮文字
    for dirty in ("编辑商品",):
        text = text.replace(dirty, '')
    text = text.strip()
    return text if text else None


def clean_text(raw: str) -> str | None:
    """
    清洗文本行，返回纯净文案或 None（应丢弃）。

    规则：
      1. 剥离残留 HTML 标签和 HTML 实体
      2. 剔除含 CSS / JS / JSON 代码特征的行
      3. 剔除高密度符号行（代码结构特征 > 15%）
      4. 清洗后长度 < 2 或纯标点符号则丢弃
    """
    # 剥离残留 HTML 标签
    text = STRIP_HTML_RE.sub('', raw)
    # 清理 HTML 实体（&nbsp; → 空格 等）
    text = _HTML_ENTITY_RE.sub(' ', text)
    # 预清洗：剔除字面转义字符、引号和逗号（处理类似 \n ','\\n 的乱码残留）
    text = text.replace('\\n', '').replace('\\r', '').replace('\\t', '')
    text = text.replace("'", '').replace('"', '').replace(',', '')
    text = text.strip()

    if not text:
        return None

    # --- 1) 剔除代码特征 ---
    text_lower = text.lower()
    for kw in _CSS_KEYWORDS:
        if kw in text_lower:
            return None
    for kw in _CODE_KEYWORDS:
        if kw in text_lower:
            return None

    # --- 2) 剔除高密度符号行 ---
    if len(text) > 0:
        symbol_count = sum(1 for ch in text if ch in _CODE_SYMBOLS)
        if symbol_count / len(text) > 0.15:
            return None

    # --- 3) 剔除无意义符号组合（不含任何中文或英文字母） ---
    if not _HAS_MEANINGFUL_CHAR_RE.search(text):
        return None

    # --- 4) 剔除未解码的 Unicode 转义（JSON 残余如 \u4e3a） ---
    if _UNESCAPED_UNICODE_RE.search(text):
        return None

    # --- 5) 剔除黑名单关键词（免责声明 + 平台 UI + 无关内容） ---
    for kw in _BLACKLIST_KEYWORDS:
        if kw in text:
            return None

    # --- 6) 长度检查：< 2 个字符或纯标点符号则丢弃 ---
    if len(text) < 2:
        return None
    if re.fullmatch(r'[\s\d.,;:!?@#$%^&*()\-_+=\\/|<>\[\]{}~`\'"，。！？、；：""''（）…—·]+', text):
        return None

    return text


# ---------------------------------------------------------------------------
# 网络拦截器（核心）
# ---------------------------------------------------------------------------

class NetworkInterceptor:
    """
    底层网络响应拦截器。

    在 page.goto() 之前挂载到 page.on("response", ...)。
    扫描每一个网络响应的文本内容：
      - 用正则提取所有 <p> 标签内的文案
    """

    def __init__(self):
        self.texts: list[str] = []
        self._seen_texts: set[str] = set()
        self.h1_title: str | None = None  # 网络拦截到的 .title-content 商品标题

    async def on_response(self, response):
        try:
            body = await response.text()

            # --- <p> 标签文案拦截 ---
            for raw_p in P_TAG_RE.findall(body):
                text = clean_text(raw_p)
                if text and text not in self._seen_texts:
                    self._seen_texts.add(text)
                    self.texts.append(text)

            # --- .title-content 商品标题拦截（白名单保护，仅基础清洗） ---
            if not self.h1_title:
                for raw_title in TITLE_CONTENT_RE.findall(body):
                    title = clean_title(raw_title)
                    if title:
                        self.h1_title = title
                        logger.info("  [拦截] 捕获 .title-content 商品标题: %s", title)
                        break

        except Exception:
            # 忽略二进制响应、跨域限制、Body 被抢占等报错，
            # 绝不能因为一个请求导致整个脚本崩溃。
            pass


# ---------------------------------------------------------------------------
# 步骤二：真人式缓慢滚动
# ---------------------------------------------------------------------------

async def human_scroll(page):
    """
    模拟真人滚动：每次向下 500 像素，停留 1 秒。
    确保所有懒加载内容真实渲染出来，触发详情区的网络请求。
    带 5 分钟硬超时保护，防止无限挂起。
    """
    import time as _time
    start_time = _time.monotonic()
    prev_height = 0
    stale_count = 0

    while True:
        # 硬超时保护
        if _time.monotonic() - start_time > SCROLL_TIMEOUT_SEC:
            logger.warning("滚动超时 (%d 秒)，强制结束", SCROLL_TIMEOUT_SEC)
            break

        current_height = await page.evaluate("document.body.scrollHeight")
        scroll_top = await page.evaluate("window.scrollY")
        viewport_height = await page.evaluate("window.innerHeight")

        if scroll_top + viewport_height >= current_height:
            if current_height == prev_height:
                stale_count += 1
                if stale_count >= 3:
                    break
            else:
                stale_count = 0
            prev_height = current_height

        await page.evaluate(f"window.scrollBy(0, {SCROLL_STEP_PX})")
        await page.wait_for_timeout(SCROLL_PAUSE_MS)

    logger.info("全页滚动完成，已到达底部")

    # 再次定向滚动详情区，确保触发 desc/mtop 请求
    detail_rect = await page.evaluate("""() => {
        const sels = ['.collapse-body', '#detail', '#de-description-detail', '[id*="detail"]'];
        for (const sel of sels) {
            const el = document.querySelector(sel);
            if (el && el.innerHTML.trim().length > 50) {
                const rect = el.getBoundingClientRect();
                return {top: rect.top + window.scrollY, height: rect.height};
            }
        }
        return null;
    }""")

    if detail_rect:
        logger.info("详情区域定向滚动 (top=%d, height=%d)...",
                     detail_rect["top"], detail_rect["height"])
        pos = max(0, detail_rect["top"] - 200)
        end = detail_rect["top"] + detail_rect["height"]
        while pos < end:
            await page.evaluate(f"window.scrollTo(0, {int(pos)})")
            await page.wait_for_timeout(800)
            pos += 400

    # 滚到底等 3 秒，确保拦截器接收完所有异步数据包
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(3000)


# ---------------------------------------------------------------------------
# 步骤三：提取并保存文本（双重提取：网络拦截 + DOM 兜底）
# ---------------------------------------------------------------------------

async def save_text(page, intercepted_texts: list, assets_dir: str,
                    intercepted_h1: str | None = None):
    """
    双重提取文案并写入 详情文案.txt：
      0. 提取商品标题（.title-content）—— DOM 精准获取 + 网络拦截兜底，白名单保护
      1. 网络拦截器已从数据包中提取的 <p> 标签文案（主力）
      2. DOM 层兜底：从 .collapse-body 内提取 <p> 标签 innerText
    严格排除 #bottom 推荐区的内容。
    商品标题置顶写入文件第一行。
    """
    # ===== 提取商品标题 =====
    product_title = None

    # --- DOM 层精准获取 .title-content ---
    dom_h1 = await page.evaluate("""() => {
        const el = document.querySelector('.title-content');
        return el ? el.innerText.trim() : null;
    }""")
    if dom_h1:
        product_title = clean_title(dom_h1)
        logger.info("  [DOM] 提取到 .title-content 商品标题: %s", product_title)

    # --- 网络拦截兜底 ---
    if not product_title and intercepted_h1:
        product_title = intercepted_h1
        logger.info("  [网络拦截兜底] 使用拦截到的 .title-content 商品标题: %s", product_title)

    if product_title:
        logger.info("  最终商品标题: %s", product_title)
    else:
        logger.warning("  未能提取到 .title-content 商品标题")

    # ===== 提取详情文案 =====
    all_texts: list[str] = []
    seen: set[str] = set()

    def add_text(raw: str):
        cleaned = clean_text(raw)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            all_texts.append(cleaned)

    # --- 1) 网络层拦截到的 <p> 文案 ---
    for t in intercepted_texts:
        add_text(t)
    logger.info("  [网络拦截] 文案条数: %d", len(all_texts))

    # --- 2) DOM 层兜底：从详情容器内的 <p> 标签提取 ---
    dom_count_before = len(all_texts)
    dom_texts = await page.evaluate("""() => {
        const texts = [];

        // 严格排除 #bottom 推荐区
        const bottomRegion = document.querySelector(
            '#bottom, [data-spm="bottom"], .region-bottom'
        );

        // 在详情容器内查找 <p>
        const containerSels = [
            '.collapse-body', '#detail', '#de-description-detail',
            '[id*="detail-description"]', '[class*="offer-description"]',
            '[class*="detail-desc"]',
        ];

        let container = null;
        for (const sel of containerSels) {
            const el = document.querySelector(sel);
            if (el && el.innerHTML.trim().length > 50) {
                container = el;
                break;
            }
        }
        if (!container) container = document.body;

        for (const p of container.querySelectorAll('p')) {
            // 跳过 #bottom 内的元素
            if (bottomRegion && bottomRegion.contains(p)) continue;
            const text = p.innerText?.trim();
            if (text && text.length > 2) {
                texts.push(text);
            }
        }
        return texts;
    }""")

    for t in dom_texts:
        add_text(t)
    logger.info("  [DOM 兜底] 新增文案条数: %d", len(all_texts) - dom_count_before)

    # --- 保存（标题置顶） ---
    text_path = os.path.join(assets_dir, "详情文案.txt")
    with open(text_path, "w", encoding="utf-8") as f:
        if product_title:
            f.write(f"【商品标题】：{product_title}\n")
            f.write("--------------------------------------------------\n")
        f.write("\n".join(all_texts))

    logger.info("文案已保存: %s (共 %d 行)", text_path, len(all_texts))
    return len(all_texts)


# ---------------------------------------------------------------------------
# 反爬检测
# ---------------------------------------------------------------------------

async def check_bot_protection(page):
    """检测是否遇到验证码或风控拦截页面。"""
    page_text = await page.evaluate("document.body ? document.body.innerText : ''")
    if len(page_text) > 500:
        return

    keywords = ["验证", "安全验证", "滑块", "captcha", "slider", "punish"]
    page_text_lower = page_text.lower()
    for kw in keywords:
        if kw in page_text_lower:
            raise RuntimeError(
                f"检测到反爬拦截 (关键词: '{kw}')。"
                "请使用 --login 打开浏览器手动完成验证。"
            )


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

async def scrape_product(url: str):
    """
    主抓取流程：
      1. 创建 product_assets 文件夹
      2. 挂载网络拦截器（在 goto 之前）
      3. 真人式缓慢滚动，触发详情请求
      4. 提取文字 → 详情文案.txt
    """

    # ===== 步骤一：创建本地资产文件夹 =====
    prepare_assets_dir()

    os.makedirs(CHROME_DATA_DIR, exist_ok=True)

    async with async_playwright() as pw:
        context = await pw.chromium.launch_persistent_context(
            user_data_dir=CHROME_DATA_DIR,
            headless=True,
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = context.pages[0] if context.pages else await context.new_page()

        stealth = Stealth()
        await stealth.apply_stealth_async(page)

        try:
            # ===== 步骤二：挂载网络拦截器（必须在 goto 之前） =====
            interceptor = NetworkInterceptor()
            page.on("response", interceptor.on_response)
            logger.info("网络拦截器已挂载，正则目标: alicdn.com/img/ibank/")

            # ===== 步骤三：访问页面 + 真人式缓慢滚动 =====
            logger.info("正在访问: %s", url)
            await page.goto(url, timeout=NAV_TIMEOUT_MS, wait_until="domcontentloaded")

            try:
                await page.wait_for_load_state("networkidle", timeout=30_000)
            except PlaywrightTimeout:
                logger.warning("networkidle 超时，继续处理")

            # 检测登录重定向
            if any(kw in page.url.lower() for kw in ["login.", "signin"]):
                raise RuntimeError(
                    "页面被重定向到登录页，请先运行 --login 模式完成扫码登录：\n"
                    f"  python {sys.argv[0]} --login"
                )

            await check_bot_protection(page)

            logger.info("开始真人式缓慢滚动（触发详情请求）...")
            await human_scroll(page)

            logger.info("滚动结束，网络拦截器共捕获 %d 条文案", len(interceptor.texts))

            # ===== 步骤四：提取并保存文本 =====
            logger.info("正在提取文案（网络拦截 + DOM 兜底）...")
            text_lines = await save_text(page, interceptor.texts, ASSETS_DIR,
                                         intercepted_h1=interceptor.h1_title)

            # 摘要
            logger.info("=" * 50)
            logger.info("全部完成!")
            logger.info("  文案: %d 行 → product_assets/详情文案.txt", text_lines)
            logger.info("=" * 50)

        finally:
            await context.close()


# ---------------------------------------------------------------------------
# 登录模式
# ---------------------------------------------------------------------------

async def login_interactive():
    """打开可见浏览器窗口，让用户手动扫码登录 1688。"""
    os.makedirs(CHROME_DATA_DIR, exist_ok=True)

    async with async_playwright() as pw:
        context = await pw.chromium.launch_persistent_context(
            user_data_dir=CHROME_DATA_DIR,
            headless=False,
            viewport={"width": 1280, "height": 900},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = context.pages[0] if context.pages else await context.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(page)

        await page.goto("https://login.1688.com/member/signin.htm", timeout=NAV_TIMEOUT_MS)

        print("=" * 60)
        print("浏览器已打开，请扫码登录 1688。")
        print("登录成功后，在此处按 Enter 键关闭浏览器并保存登录态...")
        print("=" * 60)

        await asyncio.get_event_loop().run_in_executor(None, input)
        await context.close()
        logger.info("登录态已保存至 %s", CHROME_DATA_DIR)


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

async def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("用法:")
        print(f"  python {sys.argv[0]} --login       # 首次登录（打开浏览器扫码）")
        print(f"  python {sys.argv[0]} <商品URL>     # 抓取素材到 product_assets/")
        print()
        print("输出:")
        print("  product_assets/详情文案.txt    详情区文字")
        sys.exit(1)

    if sys.argv[1] == "--login":
        await login_interactive()
        return

    url = sys.argv[1]
    if not url.startswith(("http://", "https://")):
        print(f"错误: 无效的 URL '{url}'，必须以 http:// 或 https:// 开头")
        sys.exit(1)
    await scrape_product(url)


if __name__ == "__main__":
    asyncio.run(main())
