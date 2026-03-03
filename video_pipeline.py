import random
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

import edge_tts
from mutagen.mp3 import MP3
from openai import OpenAI

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

# ---------------- 步骤一 ----------------
def generate_script_with_deepseek():
    print("=" * 50)
    print("步骤一：正在生成种草文案...")
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    detail_text = DETAIL_TEXT_FILE.read_text(encoding="utf-8")
    
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    system_prompt = "你是一位高级女装种草博主...请写一段约 120-150 字的口语化短视频种草文案。不要使用 emoji，直接输出内容。"
    user_prompt = f"商品详情信息：\n{detail_text}"

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        max_tokens=500,
    )
    script_text = response.choices[0].message.content.strip()
    SCRIPT_TEXT_FILE.write_text(script_text, encoding="utf-8")
    print("  种草文案已生成。")
    return script_text

# ---------------- 步骤二 ----------------
def format_vtt_time(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{int(hours):02d}:{int(minutes):02d}:{secs:06.3f}"

async def synthesize_audio_and_subtitles():
    print("=" * 50)
    print("步骤二：合成语音与字幕...")
    script_text = SCRIPT_TEXT_FILE.read_text(encoding="utf-8")
    communicate = edge_tts.Communicate(script_text, "zh-CN-XiaoxiaoNeural")
    word_boundaries = []

    with open(AUDIO_FILE, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                word_boundaries.append({
                    "text": chunk["text"],
                    "start": chunk["offset"] / 10000000,
                    "end": (chunk["offset"] + chunk["duration"]) / 10000000
                })

    audio = MP3(str(AUDIO_FILE))
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

    SUBTITLE_FILE.write_text("\n".join(vtt_lines), encoding="utf-8")
    return audio_duration

# ---------------- 步骤三 ----------------
def get_video_duration(file_path):
    """提取视频真实时长供 React 循环使用"""
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
        return float(result.stdout.strip())
    except:
        return 5.0 # 降级容错

def prepare_render_data(audio_duration: float):
    print("=" * 50)
    print("步骤三：准备渲染数据包...")
    assets_dir = REMOTION_PROJECT_DIR / "public" / "assets"
    if assets_dir.exists():
        import shutil
        shutil.rmtree(assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)

    video_clips_data = []
    for mp4_file in ASSETS_DIR.glob("*.mp4"):
        if mp4_file.name != "final_video.mp4":
            import shutil
            shutil.copy2(mp4_file, assets_dir / mp4_file.name)
            dur = get_video_duration(mp4_file)
            video_clips_data.append({"path": f"assets/{mp4_file.name}", "originalDuration": dur})

    # 复制主语音
    if AUDIO_FILE.exists(): shutil.copy2(AUDIO_FILE, assets_dir / "voiceover.mp3")
    if SUBTITLE_FILE.exists(): shutil.copy2(SUBTITLE_FILE, assets_dir / "subtitles.vtt")

    # --- 新增：随机抽取背景音乐 ---
    bgm_relative = ""
    if BGM_DIR.exists():
        bgm_files = list(BGM_DIR.glob("*.mp3"))
        if bgm_files:
            chosen_bgm = random.choice(bgm_files)  # 随机选一首
            print(f"  已随机选取背景音乐: {chosen_bgm.name}")
            import shutil
            shutil.copy2(chosen_bgm, assets_dir / "current_bgm.mp3") # 统一重命名复制过去
            bgm_relative = "assets/current_bgm.mp3"
    else:
        print("  未找到 bgm 文件夹，跳过背景音乐配置。")

    # 构建数据包
    render_data = {
        "audioPath": "assets/voiceover.mp3" if AUDIO_FILE.exists() else "",
        "bgmPath": bgm_relative,  # <--- 新增这行，传给前端
        "vttContent": SUBTITLE_FILE.read_text(encoding="utf-8") if SUBTITLE_FILE.exists() else "",
        "audioDurationInSeconds": audio_duration,
        "videoClips": video_clips_data,
    }
    RENDER_DATA_FILE.write_text(json.dumps(render_data, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------- 步骤四 ----------------
def trigger_remotion_render():
    print("=" * 50)
    print("步骤四：触发渲染...")
    subprocess.run(["npx", "remotion", "clear-cache"], cwd=str(REMOTION_PROJECT_DIR), capture_output=True)

    cmd = [
        "npx", "remotion", "render", "src/index.ts", "Main", str(FINAL_VIDEO_FILE),
        "--props=" + str(RENDER_DATA_FILE), "--port=3333", "--concurrency=1",
        "--browser-executable=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--disable-web-security", "--ignore-certificate-errors", "--log=verbose", "--timeout=120000"
    ]
    env = os.environ.copy()
    env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
    env["REMOTION_CHROMIUM_EXECUTABLE_PATH"] = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    process = subprocess.Popen(cmd, cwd=str(REMOTION_PROJECT_DIR), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
    for line in process.stdout: print(f"    {line.rstrip()}")
    process.wait()

# ---------------- 主干 ----------------
async def main():
    script_text = generate_script_with_deepseek()
    audio_duration = await synthesize_audio_and_subtitles()
    prepare_render_data(audio_duration)
    trigger_remotion_render()
    print("\n✅ 渲染大功告成！")

if __name__ == "__main__":
    asyncio.run(main())