"""
视频合成全链路脚本：DeepSeek + Edge-TTS + Remotion

功能：
1. DeepSeek 生成种草文案
2. Edge-TTS 语音与字幕合成
3. 准备 Remotion 渲染数据包
4. 触发 Remotion 渲染
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()

import edge_tts
from mutagen.mp3 import MP3
from openai import OpenAI

# ---------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
ASSETS_DIR = SCRIPT_DIR / "product_assets"
REMOTION_PROJECT_DIR = SCRIPT_DIR / "remotion-project"

DETAIL_TEXT_FILE = ASSETS_DIR / "详情文案.txt"
SCRIPT_TEXT_FILE = ASSETS_DIR / "种草文案.txt"
AUDIO_FILE = ASSETS_DIR / "voiceover.mp3"
SUBTITLE_FILE = ASSETS_DIR / "subtitles.vtt"
RENDER_DATA_FILE = ASSETS_DIR / "render_data.json"
FINAL_VIDEO_FILE = ASSETS_DIR / "final_video.mp4"

# ---------------------------------------------------------------------
# 步骤一：DeepSeek 生成种草文案
# ---------------------------------------------------------------------

def generate_script_with_deepseek():
    """调用 DeepSeek API 生成种草文案"""
    print("=" * 50)
    print("步骤一：正在生成种草文案...")

    # 检查 API Key
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("错误：未设置环境变量 DEEPSEEK_API_KEY")

    # 读取详情文案
    if not DETAIL_TEXT_FILE.exists():
        raise FileNotFoundError(f"详情文案文件不存在: {DETAIL_TEXT_FILE}")

    detail_text = DETAIL_TEXT_FILE.read_text(encoding="utf-8")
    print(f"  已读取详情文案 ({len(detail_text)} 字符)")

    # 调用 DeepSeek API
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )

    system_prompt = """你是一位高级女装种草博主，擅长用温暖、专业且有感染力的语言推荐优质服装。
请结合用户提供的商品详情信息，写一段时长约 30 秒的口语化短视频种草文案（约 120-150 字）。

要求：
1. 突出纯羊绒大衣的保暖性能、优雅版型和高级质感
2. 自然植入品牌名称"牧蓉旗舰店"
3. 语言亲切自然，像在对朋友推荐一样
4. 不要使用 emoji 表情
5. 直接输出文案内容，不要加引号或前缀"""

    user_prompt = f"商品详情信息：\n{detail_text}"

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=500,
    )

    script_text = response.choices[0].message.content.strip()

    # 保存文案
    SCRIPT_TEXT_FILE.write_text(script_text, encoding="utf-8")
    print(f"  种草文案已保存: {SCRIPT_TEXT_FILE}")
    print(f"  文案内容: {script_text[:50]}...")
    print()

    return script_text


# ---------------------------------------------------------------------
# 步骤二：Edge-TTS 语音与字幕合成
# ---------------------------------------------------------------------

class SubtitleMaker:
    """从 Edge-TTS 输出中提取字幕时间轴"""

    def __init__(self):
        self.subs = []

    async def on(self, stream):
        """接收 Edge-TTS 流数据"""
        async for chunk in stream:
            if chunk["type"] == "WordBoundary":
                self.subs.append({
                    "text": chunk["text"],
                    "offset": chunk["offset"] / 10000000,  # 转换为秒
                    "duration": chunk["duration"] / 10000000,
                })

    def generate_vtt(self):
        """生成 VTT 格式字幕"""
        if not self.subs:
            return ""

        vtt_lines = ["WEBVTT", ""]

        for i, sub in enumerate(self.subs):
            start_time = self._format_time(sub["offset"])
            end_time = self._format_time(sub["offset"] + sub["duration"])
            text = sub["text"].replace("\n", " ")

            vtt_lines.append(f"{i + 1}")
            vtt_lines.append(f"{start_time} --> {end_time}")
            vtt_lines.append(text)
            vtt_lines.append("")

        return "\n".join(vtt_lines)

    @staticmethod
    def _format_time(seconds):
        """格式化时间戳为 VTT 格式 (HH:MM:SS.mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


async def synthesize_audio_and_subtitles():
    """使用 Edge-TTS 合成语音并生成字幕"""
    print("=" * 50)
    print("步骤二：正在合成语音并生成字幕...")

    # 读取种草文案
    if not SCRIPT_TEXT_FILE.exists():
        raise FileNotFoundError(f"种草文案文件不存在: {SCRIPT_TEXT_FILE}")

    script_text = SCRIPT_TEXT_FILE.read_text(encoding="utf-8")
    print(f"  已读取种草文案 ({len(script_text)} 字符)")

    # 创建 Edge-TTS Communicate 对象
    communicate = edge_tts.Communicate(script_text, "zh-CN-XiaoxiaoNeural")

    # 创建字幕生成器
    submaker = SubtitleMaker()
    communicate.subs = submaker

    # 异步保存音频并收集字幕数据
    submaker = SubtitleMaker()
    communicate = edge_tts.Communicate(script_text, "zh-CN-XiaoxiaoNeural")

    # 使用 on 回调收集字幕数据
    communicate = edge_tts.Communicate(script_text, "zh-CN-XiaoxiaoNeural")

    # 保存音频文件
    await communicate.save(str(AUDIO_FILE))
    print(f"  语音已保存: {AUDIO_FILE}")

    # 重新生成字幕（因为 communicate 不直接暴露 subs）
    communicate = edge_tts.Communicate(script_text, "zh-CN-XiaoxiaoNeural")
    submaker = SubtitleMaker()

    # 手动收集所有 chunk
    all_chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "AudioWindow":
            all_chunks.append(chunk)

    # 重新遍历生成字幕
    communicate = edge_tts.Communicate(script_text, "zh-CN-XiaoxiaoNeural")

    # 创建临时文件来获取音频，同时收集字幕
    import tempfile
    import shutil

    submaker = SubtitleMaker()

    # 使用 communicate 的 on 方法
    communicate = edge_tts.Communicate(script_text, "zh-CN-XiaoxiaoNeural")

    # 保存音频
    await communicate.save(str(AUDIO_FILE))

    # 重新生成字幕 - 使用 list_all_lines 获取完整文本
    submaker = SubtitleMaker()
    communicate = edge_tts.Communicate(script_text, "zh-CN-XiaoxiaoNeural")

    # 获取音频时长
    audio = MP3(str(AUDIO_FILE))
    audio_duration = audio.info.length
    print(f"  音频时长: {audio_duration:.2f} 秒")

    # 生成字幕 - 简单按字数均分时间
    char_count = len(script_text)
    char_duration = audio_duration / char_count

    vtt_lines = ["WEBVTT", ""]
    idx = 1
    pos = 0

    # 按短句分割（加入逗号和顿号，让每段字幕更短，强制单行显示）
    import re
    sentences = re.split(r'([，。！？、\n,.\?!])', script_text)

    current_time = 0
    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i]
        if not sentence.strip():
            continue

        sentence = sentence.strip()
        duration = len(sentence) * char_duration

        start_time = SubtitleMaker._format_time(current_time)
        end_time = SubtitleMaker._format_time(current_time + duration)

        vtt_lines.append(f"{idx}")
        vtt_lines.append(f"{start_time} --> {end_time}")
        vtt_lines.append(sentence)
        vtt_lines.append("")

        current_time += duration
        idx += 1

    vtt_content = "\n".join(vtt_lines)
    SUBTITLE_FILE.write_text(vtt_content, encoding="utf-8")
    print(f"  字幕已保存: {SUBTITLE_FILE}")
    print()

    return audio_duration


# ---------------------------------------------------------------------
# 步骤三：准备 Remotion 渲染数据包
# ---------------------------------------------------------------------

def prepare_render_data(audio_duration: float):
    """准备 Remotion 渲染所需的 JSON 数据"""
    print("=" * 50)
    print("步骤三：正在准备渲染数据包...")

    # 创建 public/assets 目录
    assets_dir = REMOTION_PROJECT_DIR / "public" / "assets"
    if assets_dir.exists():
        # 清空旧素材
        import shutil
        shutil.rmtree(assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)
    print(f"  资产目录已创建: {assets_dir}")

    # 复制视频片段到 public/assets
    video_clips_relative = []
    for mp4_file in ASSETS_DIR.glob("*.mp4"):
        # 排除 final_video.mp4
        if mp4_file.name != "final_video.mp4":
            dest_path = assets_dir / mp4_file.name
            import shutil
            shutil.copy2(mp4_file, dest_path)
            video_clips_relative.append(f"assets/{mp4_file.name}")
            print(f"  已复制视频: {mp4_file.name}")

    if not video_clips_relative:
        raise FileNotFoundError("未找到任何视频片段 (.mp4 文件)")

    print(f"  找到 {len(video_clips_relative)} 个视频片段")

    # 复制音频文件
    audio_relative = "assets/voiceover.mp3"
    if AUDIO_FILE.exists():
        import shutil
        shutil.copy2(AUDIO_FILE, assets_dir / "voiceover.mp3")
        print(f"  已复制音频: voiceover.mp3")

    # 复制字幕文件
    subtitle_relative = "assets/subtitles.vtt"
    if SUBTITLE_FILE.exists():
        import shutil
        shutil.copy2(SUBTITLE_FILE, assets_dir / "subtitles.vtt")
        print(f"  已复制字幕: subtitles.vtt")

    # 读取种草文案
    script_text = SCRIPT_TEXT_FILE.read_text(encoding="utf-8")

    # 读取 VTT 字幕文件内容（直接传递给 React 组件）
    vtt_content = ""
    if SUBTITLE_FILE.exists():
        vtt_content = SUBTITLE_FILE.read_text(encoding="utf-8")

    # 构建数据（使用相对路径）
    render_data = {
        "audioPath": audio_relative,
        "subtitlePath": subtitle_relative,
        "vttContent": vtt_content,
        "audioDurationInSeconds": audio_duration,
        "videoClips": video_clips_relative,
        "scriptText": script_text,
    }

    # 保存 JSON
    RENDER_DATA_FILE.write_text(json.dumps(render_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  渲染数据已保存: {RENDER_DATA_FILE}")
    print()


# ---------------------------------------------------------------------
# 步骤四：触发 Remotion 渲染
# ---------------------------------------------------------------------

def trigger_remotion_render():
    """执行 Remotion 渲染命令"""
    print("=" * 50)
    print("步骤四：正在调用 Remotion 渲染...")

    # 检查 Remotion 项目目录
    if not REMOTION_PROJECT_DIR.exists():
        raise FileNotFoundError(f"Remotion 项目目录不存在: {REMOTION_PROJECT_DIR}")

    # 步骤 4.1: 清除 Remotion 缓存
    print("  正在清除 Remotion 缓存...")
    subprocess.run(
        ["npx", "remotion", "clear-cache"],
        cwd=str(REMOTION_PROJECT_DIR),
        capture_output=True,
    )

    # 构建命令（删除固定端口，添加 Chrome 容错标志）
    # 构建命令（删除固定端口，添加 Chrome 容错标志）
    # 构建命令
    cmd = [
        "npx",
        "remotion",
        "render",
        "src/index.ts",
        "Main",
        str(FINAL_VIDEO_FILE),
        "--props=" + str(RENDER_DATA_FILE),
        "--port=3333",      #启用3333端口
        "--concurrency=1",    # <--- 新增：强制单线程渲染，防止浏览器崩溃
        "--browser-executable=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", # <--- 加回本地 Chrome 路径
        "--disable-web-security",
        "--ignore-certificate-errors",
        "--log=verbose",
        "--timeout=120000",
        # 注意：我删除了 --browser-executable 和 --host，让它用最原生的方式运行
    ]

    print(f"  执行命令: {' '.join(cmd)}")
    print("  渲染进度:")

    # 设置环境变量（解决 SSL 证书问题 + 使用本地 Chrome）
    env = os.environ.copy()
    env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
    env["REMOTION_CHROMIUM_EXECUTABLE_PATH"] = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    # 执行命令（cwd 已设置为 REMOTION_PROJECT_DIR）
    process = subprocess.Popen(
        cmd,
        cwd=str(REMOTION_PROJECT_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )

    # 实时打印输出
    for line in process.stdout:
        print(f"    {line.rstrip()}")

    process.wait()

    if process.returncode != 0:
        raise RuntimeError(f"Remotion 渲染失败，返回码: {process.returncode}")

    if not FINAL_VIDEO_FILE.exists():
        raise FileNotFoundError(f"渲染完成但未找到输出文件: {FINAL_VIDEO_FILE}")

    print()
    print(f"  渲染完成! 输出文件: {FINAL_VIDEO_FILE}")
    file_size = FINAL_VIDEO_FILE.stat().st_size / (1024 * 1024)
    print(f"  文件大小: {file_size:.2f} MB")
    print()


# ---------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------

async def main():
    print("\n" + "=" * 50)
    print("视频合成全链路脚本启动")
    print("=" * 50 + "\n")

    try:
        # 步骤一：DeepSeek 生成种草文案
        script_text = generate_script_with_deepseek()

        # 步骤二：Edge-TTS 语音与字幕合成
        audio_duration = await synthesize_audio_and_subtitles()

        # 步骤三：准备渲染数据包
        prepare_render_data(audio_duration)

        # 步骤四：触发 Remotion 渲染
        trigger_remotion_render()

        print("=" * 50)
        print("全部完成!")
        print(f"  最终视频: {FINAL_VIDEO_FILE}")
        print("=" * 50)

    except Exception as e:
        print(f"\n错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
