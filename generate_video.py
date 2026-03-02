import os
import argparse
import base64
import ssl
import urllib.request
from dotenv import load_dotenv
from volcenginesdkarkruntime import Ark

# 忽略 SSL 证书验证
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

# 加载 .env 文件中的环境变量
load_dotenv()

# 初始化Ark客户端，从环境变量中读取 API Key
client = Ark(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key=os.environ.get("ARK_API_KEY"),
)


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

    # 查找所有图片文件
    image_extensions = {'.jpg', '.jpeg', '.png'}
    image_files = []
    for filename in os.listdir(target_dir):
        ext = os.path.splitext(filename)[1].lower()
        if ext in image_extensions:
            image_files.append(os.path.join(target_dir, filename))

    # 查找单个 txt 文件
    txt_files = [f for f in os.listdir(target_dir) if f.endswith('.txt')]

    if not txt_files:
        raise ValueError(f"错误: 目录中未找到 .txt 文件")
    if len(txt_files) > 1:
        raise ValueError(f"错误: 目录中发现了多个 .txt 文件 ({len(txt_files)} 个)，请只保留一个")

    txt_file_path = os.path.join(target_dir, txt_files[0])
    return sorted(image_files), txt_file_path


def read_prompt(txt_file_path):
    """读取提示词文件"""
    with open(txt_file_path, 'r', encoding='utf-8') as f:
        return f.read().strip()


def download_video(video_url, output_path):
    """下载视频到本地"""
    print(f"    Downloading to: {output_path}")
    try:
        urllib.request.urlretrieve(video_url, output_path)
        print(f"    Downloaded: {output_path}")
        return True
    except Exception as e:
        print(f"    Download failed: {e}")
        return False


def create_and_poll_task(image_path, prompt):
    """创建任务并轮询获取结果"""
    # 将图片转换为 Base64 Data URI
    image_data_uri = image_to_base64_data_uri(image_path)

    # 添加默认参数到提示词
    full_prompt = f"{prompt} --duration 4 --camerafixed false --watermark false"

    # 创建任务
    create_result = client.content_generation.tasks.create(
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

    task_id = create_result.id
    print(f"    Task ID: {task_id}")

    # 轮询任务状态
    while True:
        get_result = client.content_generation.tasks.get(task_id=task_id)
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
            print(f"    Status: {status}, waiting 3s...")
            time.sleep(3)


def main():
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='批量使用 Seedance 1.5 Pro 生成视频')
    parser.add_argument('directory', help='目标目录路径（包含图片和单个 txt 文件）')
    args = parser.parse_args()

    target_dir = args.directory

    print(f"===== 开始扫描目录: {target_dir} =====")

    # 扫描目录
    image_files, txt_file_path = scan_directory(target_dir)

    if not image_files:
        print("错误: 目录中未找到图片文件 (.jpg, .jpeg, .png)")
        return

    print(f"找到 {len(image_files)} 个图片文件")
    print(f"提示词文件: {os.path.basename(txt_file_path)}")

    # 读取提示词
    prompt = read_prompt(txt_file_path)
    print(f"提示词内容: {prompt[:50]}..." if len(prompt) > 50 else f"提示词内容: {prompt}")

    # 输出文件
    output_file = os.path.join(target_dir, 'results.txt')

    # 批量处理
    print(f"\n===== 开始批量生成视频 =====")
    success_count = 0
    fail_count = 0

    for i, image_path in enumerate(image_files, 1):
        image_name = os.path.basename(image_path)
        print(f"\n[{i}/{len(image_files)}] Processing: {image_name}")

        try:
            video_url = create_and_poll_task(image_path, prompt)

            if video_url:
                # 生成输出视频路径 (将 .jpg/.png 改为 .mp4)
                base_name = os.path.splitext(image_name)[0]
                video_output_path = os.path.join(target_dir, f"{base_name}.mp4")

                # 下载视频
                if download_video(video_url, video_output_path):
                    # 写入结果文件
                    with open(output_file, 'a', encoding='utf-8') as f:
                        f.write(f"{image_name},{video_url}\n")

                    print(f"    SUCCESS: {video_output_path}")
                    success_count += 1
                else:
                    # 下载失败但记录 URL
                    with open(output_file, 'a', encoding='utf-8') as f:
                        f.write(f"{image_name},{video_url},DOWNLOAD_FAILED\n")
                    fail_count += 1
            else:
                print(f"    FAILED: 无法获取视频 URL")
                fail_count += 1

        except Exception as e:
            print(f"    FAILED: {str(e)}")
            fail_count += 1
            # 继续处理下一个图片

    print(f"\n===== 完成 =====")
    print(f"成功: {success_count}, 失败: {fail_count}")
    print(f"结果已保存至: {output_file}")


if __name__ == "__main__":
    import time
    main()
