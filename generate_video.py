import os
import argparse
import base64
import logging
import ssl
import time
import urllib.request
from dotenv import load_dotenv
from volcenginesdkarkruntime import Ark

# 使用 certifi 证书包（如果可用），否则回退到系统默认
try:
    import certifi
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    urllib.request.install_opener(
        urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context))
    )
except ImportError:
    pass  # certifi 不可用时使用系统默认 SSL 证书

# 加载 .env 文件中的环境变量
load_dotenv()

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# 常量配置
MAX_POLL_RETRIES = 180       # 轮询最大重试次数（180 * 5s = 15 分钟）
POLL_INTERVAL_SEC = 5        # 轮询间隔秒数
API_MAX_RETRIES = 3          # API 调用最大重试次数

# 懒加载 Ark 客户端（避免 import 时因缺少 API Key 而崩溃）
_client = None

def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("ARK_API_KEY")
        if not api_key:
            raise SystemExit("Error: ARK_API_KEY environment variable is not set. Please set it before running.")
        _client = Ark(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=api_key,
        )
    return _client


def get_mime_type(filename):
    """根据文件扩展名返回 MIME 类型"""
    ext = os.path.splitext(filename)[1].lower()
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
    }
    return mime_types.get(ext, 'image/jpeg')


def image_to_base64_data_uri(image_path):
    """将本地图片转换为 Base64 Data URI 格式"""
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    mime_type = get_mime_type(image_path)
    return f"data:{mime_type};base64,{image_data}"


def scan_directory(target_dir):
    """扫描目录查找图片和文本文件"""
    # 验证目录存在
    if not os.path.isdir(target_dir):
        raise ValueError(f"目录不存在: {target_dir}")

    # 只查找用户上传的图片（upload_ 前缀）
    image_extensions = {'.jpg', '.jpeg', '.png'}
    image_files = []
    for filename in os.listdir(target_dir):
        if not filename.startswith("upload_"):
            continue
        ext = os.path.splitext(filename)[1].lower()
        if ext in image_extensions:
            image_files.append(os.path.join(target_dir, filename))

    # 查找详情文案文件
    txt_file_path = os.path.join(target_dir, "详情文案.txt")
    if not os.path.isfile(txt_file_path):
        raise ValueError(f"错误: 目录中未找到 详情文案.txt")
    return sorted(image_files), txt_file_path


def read_prompt(txt_file_path):
    """读取提示词文件"""
    with open(txt_file_path, 'r', encoding='utf-8') as f:
        return f.read().strip()


def download_video(video_url, output_path):
    """下载视频到本地，带重试"""
    logger.info("    Downloading to: %s", output_path)
    for attempt in range(API_MAX_RETRIES):
        try:
            urllib.request.urlretrieve(video_url, output_path)
            logger.info("    Downloaded: %s", output_path)
            return True
        except Exception as e:
            if attempt < API_MAX_RETRIES - 1:
                wait = min(2 ** attempt * 2, 30)
                logger.warning("    Download failed (attempt %d/%d): %s, retrying in %ds...",
                               attempt + 1, API_MAX_RETRIES, e, wait)
                time.sleep(wait)
            else:
                logger.error("    Download failed after %d attempts: %s", API_MAX_RETRIES, e)
                return False


def create_and_poll_task(image_path, prompt):
    """创建任务并轮询获取结果，带重试和超时保护"""
    # 将图片转换为 Base64 Data URI
    image_data_uri = image_to_base64_data_uri(image_path)

    # 添加默认参数到提示词
    full_prompt = f"{prompt} --duration 5 --camerafixed false --watermark false"

    # 创建任务（带重试）
    create_result = None
    for attempt in range(API_MAX_RETRIES):
        try:
            create_result = get_client().content_generation.tasks.create(
                model="doubao-seedance-1-5-pro-251215",
                content=[
                    {
                        "type": "text",
                        "text": full_prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_uri
                        }
                    }
                ]
            )
            break
        except Exception as e:
            if attempt < API_MAX_RETRIES - 1:
                wait = min(2 ** attempt * 2, 30)
                logger.warning("    Task creation failed (attempt %d/%d): %s, retrying in %ds...",
                               attempt + 1, API_MAX_RETRIES, e, wait)
                time.sleep(wait)
            else:
                raise

    task_id = create_result.id
    logger.info("    Task ID: %s", task_id)

    # 轮询任务状态（带超时保护）
    for poll_count in range(MAX_POLL_RETRIES):
        try:
            get_result = get_client().content_generation.tasks.get(task_id=task_id)
        except Exception as e:
            logger.warning("    Polling error (attempt %d): %s", poll_count + 1, e)
            time.sleep(POLL_INTERVAL_SEC)
            continue

        status = get_result.status

        if status == "succeeded":
            # 提取视频 URL - 从 content 字段获取
            video_url = None
            if hasattr(get_result, 'content') and get_result.content:
                video_url = get_result.content.video_url if hasattr(get_result.content, 'video_url') else None
            return video_url

        elif status == "failed":
            error_msg = get_result.error if hasattr(get_result, 'error') else "Unknown error"
            raise Exception(f"任务失败: {error_msg}")

        else:
            logger.info("    Status: %s, waiting %ds... (%d/%d)",
                        status, POLL_INTERVAL_SEC, poll_count + 1, MAX_POLL_RETRIES)
            time.sleep(POLL_INTERVAL_SEC)

    raise TimeoutError(f"任务轮询超时: 已等待 {MAX_POLL_RETRIES * POLL_INTERVAL_SEC} 秒, task_id={task_id}")


def main():
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='批量使用 Seedance 1.5 Pro 生成视频')
    parser.add_argument('directory', help='目标目录路径（包含图片和单个 txt 文件）')
    args = parser.parse_args()

    target_dir = args.directory

    logger.info("===== 开始扫描目录: %s =====", target_dir)

    # 扫描目录
    image_files, txt_file_path = scan_directory(target_dir)

    if not image_files:
        logger.error("错误: 目录中未找到图片文件 (.jpg, .jpeg, .png)")
        return

    logger.info("找到 %d 个图片文件", len(image_files))
    logger.info("提示词文件: %s", os.path.basename(txt_file_path))

    # 读取提示词
    prompt = read_prompt(txt_file_path)
    logger.info("提示词内容: %s", prompt[:50] + "..." if len(prompt) > 50 else prompt)

    # 输出文件
    output_file = os.path.join(target_dir, 'results.txt')

    # 批量处理（结果先收集，最后一次性写入）
    logger.info("\n===== 开始批量生成视频 =====")
    success_count = 0
    fail_count = 0
    results = []

    for i, image_path in enumerate(image_files, 1):
        image_name = os.path.basename(image_path)
        logger.info("\n[%d/%d] Processing: %s", i, len(image_files), image_name)

        try:
            video_url = create_and_poll_task(image_path, prompt)

            if video_url:
                # 生成输出视频路径 (将 .jpg/.png 改为 .mp4)
                base_name = os.path.splitext(image_name)[0]
                video_output_path = os.path.join(target_dir, f"{base_name}.mp4")

                # 下载视频
                if download_video(video_url, video_output_path):
                    results.append(f"{image_name},{video_url}")
                    logger.info("    SUCCESS: %s", video_output_path)
                    success_count += 1
                else:
                    results.append(f"{image_name},{video_url},DOWNLOAD_FAILED")
                    fail_count += 1
            else:
                logger.warning("    FAILED: 无法获取视频 URL")
                fail_count += 1

        except Exception as e:
            logger.error("    FAILED on %s: %s", image_name, e, exc_info=True)
            fail_count += 1
            # 继续处理下一个图片

    # 一次性写入结果文件
    if results:
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write("\n".join(results) + "\n")

    logger.info("\n===== 完成 =====")
    logger.info("成功: %d, 失败: %d", success_count, fail_count)
    logger.info("结果已保存至: %s", output_file)


if __name__ == "__main__":
    main()
