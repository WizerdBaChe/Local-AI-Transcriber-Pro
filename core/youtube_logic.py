import os
import re
import yt_dlp
from pathlib import Path
from faster_whisper import WhisperModel

def sanitize_filename(title):
    return re.sub(r'[\\/*?:"<>|]', "", Path(title).stem).strip()

def process_youtube(url, model_name, download_dir, export_dir, model_dir, log_cb, progress_cb, stop_event):
    """
    處理 YouTube 下載與轉錄的核心邏輯
    """
    audio_path = None
    try:
        log_cb(f"解析 YouTube 網址: {url}")
        
        # 1. yt-dlp 下載設定
        ydl_opts = {
            'format': 'm4a/bestaudio/best',
            'outtmpl': str(Path(download_dir) / '%(id)s.%(ext)s'),
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}],
            'quiet': True,
            'no_warnings': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_path = Path(download_dir) / f"{info['id']}.mp3"
            duration = info.get('duration', 1)
            video_title = sanitize_filename(info.get('title', info['id']))

        if stop_event.is_set(): 
            log_cb(">> 任務已被使用者強制中斷")
            return False

        log_cb(f"目標影片: {video_title}")
        log_cb(f"載入 Whisper 模型 ({model_name}) 到 RTX 5070 (float16)...")
        
        # 2. 初始化模型
        model = WhisperModel(model_name, device="cuda", compute_type="float16", download_root=str(model_dir))

        log_cb("啟動 AI 語音識別 (啟用 VAD 過濾)...")
        segments, info_whisper = model.transcribe(str(audio_path), beam_size=5, vad_filter=True)
        
        output_file = Path(export_dir) / f"{video_title}.txt"
        
        # 3. 轉錄並寫入檔案
        with open(output_file, "w", encoding="utf-8") as f:
            for segment in segments:
                if stop_event.is_set():
                    log_cb(">> 任務中斷，保留已轉錄部分。")
                    break
                
                text_line = f"[{segment.start:>7.2f}s -> {segment.end:>7.2f}s] {segment.text}"
                f.write(text_line + "\n")
                
                # 計算並回傳進度 (0.0 ~ 1.0)
                progress = min(segment.end / duration, 1.0)
                progress_cb(progress)
                log_cb(text_line) # 即時回傳句子

        if not stop_event.is_set():
            log_cb(f"✅ 完成！逐字稿已儲存至: {output_file.name}")
            return True

    except Exception as e:
        log_cb(f"❌ 錯誤發生: {str(e)}")
        return False
        
    finally:
        # 清理暫存音檔
        if audio_path and audio_path.exists():
            try:
                os.remove(audio_path)
            except:
                pass