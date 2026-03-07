import logging
import random
import shutil
import asyncio
import json
import os
import subprocess
import sys
import time
import threading
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

import edge_tts
from mutagen.mp3 import MP3
from openai import OpenAI

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Remotion 渲染锁（防止并发渲染冲突）
_remotion_render_lock = threading.Lock()

# ---------------- 配置 ----------------
SCRIPT_DIR = Path(__file__).parent
ASSETS_DIR = SCRIPT_DIR / "product_assets"
REMOTION_PROJECT_DIR = SCRIPT_DIR / "remotion-project"

DETAIL_TEXT_FILE = ASSETS_DIR / "详情文案.txt"
SCRIPT_TEXT_FILE = ASSETS_DIR / "种草文案.txt"
AUDIO_FILE = ASSETS_DIR / "voiceover.mp3"
SUBTITLE_FILE = ASSETS_DIR / "subtitles.vtt"
RENDER_DATA_FILE = ASSETS_DIR / "render_data.json"
FINAL_VIDEO_FILE = ASSETS_DIR / "final_video.mp4"

BGM_DIR = ASSETS_DIR / "bgm"

# DeepSeek API 重试配置
API_MAX_RETRIES = 5

# Chrome 浏览器路径（优先使用环境变量）
CHROME_EXECUTABLE = os.environ.get(
    "CHROME_EXECUTABLE",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
)

# ---------------- 步骤一 ----------------
def generate_script_with_deepseek(assets_dir: Path = ASSETS_DIR):
    print("=" * 50)
    print("步骤一：正在生成种草文案...")
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("缺少 DEEPSEEK_API_KEY 环境变量，请检查 .env 文件")
    detail_text_file = assets_dir / "详情文案.txt"
    script_text_file = assets_dir / "种草文案.txt"
    detail_text = detail_text_file.read_text(encoding="utf-8")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        timeout=120.0,    # 读取响应超时 120 秒（默认太短，大响应容易断）
        max_retries=5,    # SDK 内部重试 5 次
    )
    system_prompt = "你是一位高级女装种草博主...请写一段约 50-60 字的口语化短视频种草文案。不要使用 emoji，直接输出内容。"
    user_prompt = f"商品详情信息：\n{detail_text}"

    # 带重试的 API 调用
    for attempt in range(API_MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                max_tokens=500,
            )
            break
        except Exception as e:
            if attempt < API_MAX_RETRIES - 1:
                wait = min(2 ** attempt * 5, 60)
                logger.warning("DeepSeek API 调用失败 (第 %d/%d 次): %s, %d 秒后重试...",
                               attempt + 1, API_MAX_RETRIES, e, wait)
                time.sleep(wait)
            else:
                raise

    script_text = response.choices[0].message.content.strip()
    script_text_file.write_text(script_text, encoding="utf-8")
    print("  种草文案已生成。")
    return script_text

# ---------------- 步骤一點五：生成朋友圈文案 ----------------
def generate_wechat_moments_copy(assets_dir: Path = ASSETS_DIR):
    print("=" * 50)
    print("步骤一点五：正在生成朋友圈营销文案...")
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("缺少 DEEPSEEK_API_KEY 环境变量，请检查 .env 文件")

    script_text_file = assets_dir / "种草文案.txt"
    moments_copy_file = assets_dir / "朋友圈文案.txt"

    if not script_text_file.exists():
        print("  [警告] 种草文案不存在，跳过朋友圈文案生成")
        return None

    script_text = script_text_file.read_text(encoding="utf-8")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        timeout=120.0,
        max_retries=5,
    )

    system_prompt = """你是一位资深的社交媒体文案专家，擅长写朋友圈营销文案。
请根据给定的种草文案，浓缩成一段适合发朋友圈的营销文案。
要求：
1. 30-50字
2. 文案内有丰富的相关emoji
3. 适合朋友圈风格，亲切有感染力
4. 直接输出文案内容，不要加任何解释"""

    user_prompt = f"种草文案：\n{script_text}"

    # 带重试的 API 调用
    for attempt in range(API_MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=200,
            )
            break
        except Exception as e:
            if attempt < API_MAX_RETRIES - 1:
                wait = min(2 ** attempt * 5, 60)
                logger.warning("DeepSeek API 调用失败 (第 %d/%d 次): %s, %d 秒后重试...",
                              attempt + 1, API_MAX_RETRIES, e, wait)
                time.sleep(wait)
            else:
                raise

    moments_copy = response.choices[0].message.content.strip()
    moments_copy_file.write_text(moments_copy, encoding="utf-8")
    print("  朋友圈文案已生成。")
    return moments_copy

# ---------------- 步骤二 ----------------
def format_vtt_time(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{secs:06.3f}"

async def synthesize_audio_and_subtitles(assets_dir: Path = ASSETS_DIR):
    print("=" * 50)
    print("步骤二：合成语音与字幕...")
    script_text_file = assets_dir / "种草文案.txt"
    audio_file = assets_dir / "voiceover.mp3"
    subtitle_file = assets_dir / "subtitles.vtt"
    script_text = script_text_file.read_text(encoding="utf-8")
    communicate = edge_tts.Communicate(script_text, "zh-CN-XiaoxiaoNeural")
    word_boundaries = []

    with open(audio_file, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_boundaries.append({
                    "text": chunk["text"],
                    "start": chunk["offset"] / 10000000,
                    "end": (chunk["offset"] + chunk["duration"]) / 10000000
                })

    audio = MP3(str(audio_file))
    audio_duration = audio.info.length
    vtt_lines = ["WEBVTT", ""]
    idx = 1

    # 关键修复：如果 AI 没有吐出时间戳，启动智能标点均分兜底方案，保证绝对有字幕！
    if not word_boundaries:
        print("  [提示] 启用标点均分降级算法生成字幕...")
        import re
        sentences = [s for s in re.split(r'([，。！？、,.\?!])', script_text) if s.strip()]
        merged = [sentences[i] + sentences[i+1] for i in range(0, len(sentences)-1, 2)]
        if len(sentences) % 2 != 0: merged.append(sentences[-1])
        
        current_time = 0.0
        char_count = sum(len(s) for s in merged)
        for s in merged:
            duration = (len(s) / max(1, char_count)) * audio_duration
            clean_text = "".join([c for c in s if c not in "，。！？、,.\?!"]).strip()
            if clean_text:
                vtt_lines.extend([str(idx), f"{format_vtt_time(current_time)} --> {format_vtt_time(current_time + duration)}", clean_text, ""])
                idx += 1
            current_time += duration
    else:
        # 如果有时间戳，就按照精确时间戳断句单行显示
        current_sentence = ""
        sentence_start = -1
        for i, word in enumerate(word_boundaries):
            if sentence_start == -1: sentence_start = word["start"]
            current_sentence += word["text"]
            sentence_end = word["end"]
            
            is_last = (i == len(word_boundaries) - 1)
            has_pause = not is_last and (word_boundaries[i+1]["start"] - sentence_end) > 0.15
            
            if has_pause or is_last or len(current_sentence) >= 12:
                clean_text = "".join([c for c in current_sentence if c not in "，。！？、,.\?!"]).strip()
                if clean_text:
                    vtt_lines.extend([str(idx), f"{format_vtt_time(sentence_start)} --> {format_vtt_time(sentence_end)}", clean_text, ""])
                    idx += 1
                current_sentence = ""
                sentence_start = -1

    subtitle_file.write_text("\n".join(vtt_lines), encoding="utf-8")
    return audio_duration

# ---------------- 步骤三 ----------------
def get_video_duration(file_path):
    """提取视频真实时长供 React 循环使用"""
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, timeout=30)
        return float(result.stdout.strip())
    except Exception as e:
        logger.warning("无法获取视频时长 (%s): %s, 使用默认 5.0s", file_path, e)
        return 5.0

def prepare_render_data(audio_duration: float, assets_dir: Path = ASSETS_DIR,
                        remotion_project_dir: Path = REMOTION_PROJECT_DIR):
    print("=" * 50)
    print("步骤三：准备渲染数据包...")
    audio_file = assets_dir / "voiceover.mp3"
    subtitle_file = assets_dir / "subtitles.vtt"
    moments_copy_file = assets_dir / "朋友圈文案.txt"
    render_data_file = assets_dir / "render_data.json"
    bgm_dir = assets_dir / "bgm"

    remotion_assets_dir = remotion_project_dir / "public" / "assets"
    if remotion_assets_dir.exists():
        shutil.rmtree(remotion_assets_dir)
    remotion_assets_dir.mkdir(parents=True, exist_ok=True)

    # 复制主语音
    if audio_file.exists(): shutil.copy2(audio_file, remotion_assets_dir / "voiceover.mp3")
    if subtitle_file.exists(): shutil.copy2(subtitle_file, remotion_assets_dir / "subtitles.vtt")

    # --- 随机抽取背景音乐 ---
    bgm_relative = ""
    if bgm_dir.exists():
        bgm_files = list(bgm_dir.glob("*.mp3"))
        if bgm_files:
            chosen_bgm = random.choice(bgm_files)
            print(f"  已随机选取背景音乐: {chosen_bgm.name}")
            shutil.copy2(chosen_bgm, remotion_assets_dir / "current_bgm.mp3")
            bgm_relative = "assets/current_bgm.mp3"
    else:
        print("  未找到 bgm 文件夹，跳过背景音乐配置。")

    # 构建数据包
    render_data = {
        "audioPath": "assets/voiceover.mp3" if audio_file.exists() else "",
        "bgmPath": bgm_relative,
        "vttContent": subtitle_file.read_text(encoding="utf-8") if subtitle_file.exists() else "",
        "audioDurationInSeconds": audio_duration,
        "videoClips": [],
        "wechatMomentsCopy": moments_copy_file.read_text(encoding="utf-8") if moments_copy_file.exists() else "",
    }
    render_data_file.write_text(json.dumps(render_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return render_data_file

# ---------------- 步骤四 ----------------
def trigger_remotion_render(assets_dir: Path = ASSETS_DIR,
                            remotion_project_dir: Path = REMOTION_PROJECT_DIR):
    print("=" * 50)
    print("步骤四：触发渲染...")
    final_video_file = assets_dir / "final_video.mp4"
    render_data_file = assets_dir / "render_data.json"
    remotion_assets_dir = remotion_project_dir / "public" / "assets"
    remotion_assets_dir.mkdir(parents=True, exist_ok=True)

    # 复制生成的视频片段到 Remotion assets 并更新 render_data
    video_clips_data = []
    for mp4_file in sorted(assets_dir.glob("*.mp4")):
        if mp4_file.name != "final_video.mp4":
            shutil.copy2(mp4_file, remotion_assets_dir / mp4_file.name)
            dur = get_video_duration(mp4_file)
            video_clips_data.append({"path": f"assets/{mp4_file.name}", "originalDuration": dur})

    if render_data_file.exists():
        render_data = json.loads(render_data_file.read_text(encoding="utf-8"))
        render_data["videoClips"] = video_clips_data
        render_data_file.write_text(json.dumps(render_data, ensure_ascii=False, indent=2), encoding="utf-8")

    with _remotion_render_lock:
        subprocess.run(["npx", "remotion", "clear-cache"], cwd=str(remotion_project_dir), capture_output=True, timeout=60)

        cmd = [
            "npx", "remotion", "render", "src/index.ts", "Main", str(final_video_file),
            "--props=" + str(render_data_file), "--port=3333", "--concurrency=1",
            f"--browser-executable={CHROME_EXECUTABLE}",
            "--disable-web-security", "--ignore-certificate-errors", "--log=verbose", "--timeout=120000"
        ]
        env = os.environ.copy()
        env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
        env["REMOTION_CHROMIUM_EXECUTABLE_PATH"] = CHROME_EXECUTABLE

        process = subprocess.Popen(cmd, cwd=str(remotion_project_dir), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
        try:
            for line in process.stdout:
                print(f"    {line.rstrip()}")
            process.wait(timeout=600)
        except subprocess.TimeoutExpired:
            process.kill()
            raise TimeoutError("Remotion 渲染超时（10 分钟），已强制终止")

    return final_video_file

# ---------------- 主干 ----------------
async def main():
    script_text = generate_script_with_deepseek()
    # 生成朋友圈营销文案
    generate_wechat_moments_copy()
    audio_duration = await synthesize_audio_and_subtitles()
    prepare_render_data(audio_duration)
    trigger_remotion_render()
    print("\n✅ 渲染大功告成！")

if __name__ == "__main__":
    asyncio.run(main())