
任务指令：重构纯净版“电商详情页文案提取” Python 脚本

1. 任务背景与目标

基于我之前写的完整电商素材抓取脚本，现需要你提取出纯文本抓取的功能，编写一个新的精简版 Python 脚本（命名为 text_scraper.py）。
该脚本的唯一目标是：通过 Playwright 访问电商商品详情页，利用“网络请求拦截 + DOM 兜底”提取纯净的商品描述文案，并保存为 .txt 文件。

绝对要求：去除所有与图片（ibank URL 提取、PIL 体检、图片下载）和视频（** 标签提取与下载）相关的逻辑。**

2. 核心架构与必须保留的机制

请使用 playwright 和 playwright_stealth 库。脚本需包含以下核心机制：

2.1. 浏览器环境与登录态管理

保留 CHROME_DATA_DIR 的持久化上下文（Persistent Context）机制。
保留 --login 参数和 login_interactive() 函数，允许用户手动打开浏览器扫码登录并保存状态。
使用 --disable-blink-features=AutomationControlled 并应用 stealth 隐藏 WebDriver 特征。
2.2. 网络拦截提取 (Network Interceptor)

在 page.goto() 之前挂载拦截器。
扫描网络响应（Response body），使用正则暴力提取：
<p> 标签内容：r'<p[^>]*>(.*?)</p>'
.title-content 商品标题：r'<div[^>]*class="[^"]*title-content[^"]*"[^>]*>(.*?)</div>'
2.3. 真人缓慢滚动 (Human Scroll)

页面加载后，执行每次向下滚动 500 像素、暂停 1 秒的循环，直到页面底部。
定向滚动详情区域（如 .collapse-body, #detail 等），以触发异步的数据包请求。
2.4. DOM 兜底提取

滚动完成后，从 DOM 层精准查找标题（document.querySelector('.title-content')）。
兜底提取文案：在指定的详情容器内（如 .collapse-body, #detail, #de-description-detail）查找所有 <p> 标签，并严格排除推荐区 #bottom 内的内容。
3. 严格的文本清洗规则（核心！）

请在脚本中完整实现以下预设的常量和清洗函数，不要遗漏规则：

import re

# 清洗常量定义
_CSS_KEYWORDS = ["px;", "margin:", "padding:", "font-size", "color:", "!important", "rgb("]
_CODE_KEYWORDS = ["function", "var ", "let ", "=>", '{"', '":[']
_CODE_SYMBOLS = set("{};<>=_")
_HTML_ENTITY_RE = re.compile(r'&(?:nbsp|amp|lt|gt|quot|apos|#\d+|#x[\da-fA-F]+);')
_UNESCAPED_UNICODE_RE = re.compile(r'\\u[0-9a-fA-F]{4}')
_HAS_MEANINGFUL_CHAR_RE = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbfa-zA-Z]')
_BLACKLIST_KEYWORDS = [
    "保障经营合法合规", "刀具", "郑重承诺", "温馨提示", "免责声明",
    "不作为商品描述", "不代表产品", "仅供参考", "请以实物为准",
    "投诉举报", "违禁信息", "知识产权",
    "编辑商品", "登陆推荐更精准", "翻译", "搜索", "复制", "点击链接进入",
    "尺码推荐", "搭配", "主播", "斤",
]
STRIP_HTML_RE = re.compile(r'<[^>]+>')
函数逻辑：

剥离 HTML 标签 (STRIP_HTML_RE) 和 HTML 实体 (_HTML_ENTITY_RE)。
剔除转义符（换行、制表、引号、逗号）。
丢弃包含代码特征的行（CSS/JS 关键词，或高密度符号 > 15%）。
丢弃不含中英文字符的行、包含未解码 Unicode 的行。
丢弃包含 _BLACKLIST_KEYWORDS 脏词的行。
丢弃长度小于 2 或全标点符号的行。
4. 输出格式

将清洗去重后的所有文案汇总。
在 product_assets/详情文案.txt 中保存结果。
文件第一行为 【商品标题】：[提取到的标题]，第二行为分割线 -------------------------，之后为逐行文案。





