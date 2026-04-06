import sys
import os
import subprocess
import re
from pathlib import Path

# --- 配置區：定義專案結構 ---
REQUIRED_DIRS = [
    "core",
    "workspace/downloads",
    "models",
    "exports"
]

# 定義檔案內容模板，若檔案不存在則會自動建立
FILE_TEMPLATES = {
    "requirements.txt": "customtkinter\nfaster-whisper\nyt-dlp\npillow\n",
    "core/__init__.py": "",
    ".env": "PYTHONPATH=.\nHF_HUB_DISABLE_SYMLINKS_WARNING=1\n",
    "core/youtube_logic.py": '''import os
import re
import yt_dlp
from pathlib import Path
from faster_whisper import WhisperModel

def sanitize_filename(title):
    return re.sub(r'[\\\\/*?:"<>|]', "", Path(title).stem).strip()

def process_youtube(url, model_name, download_dir, export_dir, model_dir, log_cb, progress_cb, stop_event):
    audio_path = None
    try:
        log_cb(f"解析 YouTube 網址: {url}")
        ydl_opts = {
            'format': 'm4a/bestaudio/best',
            'outtmpl': str(Path(download_dir) / '%(id)s.%(ext)s'),
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}],
            'quiet': True, 'no_warnings': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_path = Path(download_dir) / f"{info['id']}.mp3"
            duration = info.get('duration', 1)
            video_title = sanitize_filename(info.get('title', info['id']))

        if stop_event.is_set(): return False
        
        log_cb(f"目標影片: {video_title}")
        model = WhisperModel(model_name, device="cuda", compute_type="float16", download_root=str(model_dir))
        segments, _ = model.transcribe(str(audio_path), beam_size=5, vad_filter=True)
        
        output_file = Path(export_dir) / f"{video_title}.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            for segment in segments:
                if stop_event.is_set(): break
                text_line = f"[{segment.start:>7.2f}s -> {segment.end:>7.2f}s] {segment.text}"
                f.write(text_line + "\\n")
                progress_cb(min(segment.end / duration, 1.0))
                log_cb(text_line)
        return True
    except Exception as e:
        log_cb(f"❌ 錯誤: {str(e)}")
        return False
    finally:
        if audio_path and audio_path.exists(): os.remove(audio_path)
''',
    "core/local_logic.py": '''import re
from pathlib import Path
from faster_whisper import WhisperModel

def sanitize_filename(title):
    return re.sub(r'[\\\\/*?:"<>|]', "", Path(title).stem).strip()

def process_local_file(file_path, model_name, export_dir, model_dir, log_cb, progress_cb, stop_event):
    try:
        log_cb(f"準備分析本地檔案: {Path(file_path).name}")
        model = WhisperModel(model_name, device="cuda", compute_type="float16", download_root=str(model_dir))
        segments, info_whisper = model.transcribe(str(file_path), beam_size=5, vad_filter=True)
        duration = info_whisper.duration or 1
        output_file = Path(export_dir) / f"{sanitize_filename(file_path)}.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            for segment in segments:
                if stop_event.is_set(): break
                text_line = f"[{segment.start:>7.2f}s -> {segment.end:>7.2f}s] {segment.text}"
                f.write(text_line + "\\n")
                progress_cb(min(segment.end / duration, 1.0))
                log_cb(text_line)
        return True
    except Exception as e:
        log_cb(f"❌ 錯誤: {str(e)}")
        return False
'''
}

def check_and_init():
    print("="*50)
    print("🚀 AI Studio 專案初始化與診斷工具")
    print("="*50)

    # 1. 檢查並建立資料夾
    print("\n📂 [1/3] 檢查資料夾結構...")
    for folder in REQUIRED_DIRS:
        p = Path(folder)
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            print(f"  - ✅ 已建立目錄: {folder}")
        else:
            print(f"  - 🆗 資料夾已存在: {folder}")

    # 2. 檢查並建立必備檔案
    print("\n📄 [2/3] 檢查核心檔案...")
    for file_path, content in FILE_TEMPLATES.items():
        p = Path(file_path)
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  - ✅ 已建立預設檔案: {file_path}")
        else:
            print(f"  - 🆗 檔案已存在: {file_path}")

    # 3. 環境診斷
    print("\n🛠️ [3/3] 系統環境診斷...")
    print(f"  - 🐍 Python 版本: {sys.version.split()[0]}")

    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print("  - 🎥 FFmpeg 狀態: ✅ 已安裝")
    except:
        print("  - 🎥 FFmpeg 狀態: ❌ 未安裝或路徑錯誤")

    packages = ["customtkinter", "faster_whisper", "yt_dlp", "PIL"]
    print("  - 📦 套件安裝狀況:")
    for pkg in packages:
        try:
            __import__(pkg)
            print(f"      └─ {pkg}: ✅ OK")
        except ImportError:
            print(f"      └─ {pkg}: ❌ 缺失")

    print("\n" + "="*50)
    print("✨ 診斷結束。")
    print("="*50)

if __name__ == "__main__":
    check_and_init()
    input("\n按任意鍵結束...")