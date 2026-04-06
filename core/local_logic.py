import re
from pathlib import Path
from faster_whisper import WhisperModel

def sanitize_filename(title):
    return re.sub(r'[\\/*?:"<>|]', "", Path(title).stem).strip()

def process_local_file(file_path, model_name, export_dir, model_dir, log_cb, progress_cb, stop_event):
    """
    處理本地音訊/影片檔案轉錄的核心邏輯
    """
    try:
        log_cb(f"準備分析本地檔案: {Path(file_path).name}")
        log_cb(f"載入 Whisper 模型 ({model_name}) 到 RTX 5070 (float16)...")
        
        # 1. 初始化模型
        model = WhisperModel(model_name, device="cuda", compute_type="float16", download_root=str(model_dir))

        log_cb("啟動 AI 語音識別 (啟用 VAD 過濾)...")
        
        # 本地檔案如果沒有事先用 ffprobe 抓總長度，進度條只能粗估或根據片段時間估算。
        # 這裡我們依靠 faster-whisper 內建的 VAD 來跑。
        segments, info_whisper = model.transcribe(str(file_path), beam_size=5, vad_filter=True)
        
        duration = info_whisper.duration
        if duration <= 0:
            duration = 1 # 避免除以零
            
        output_file = Path(export_dir) / f"{sanitize_filename(file_path)}.txt"
        
        # 2. 轉錄並寫入檔案
        with open(output_file, "w", encoding="utf-8") as f:
            for segment in segments:
                if stop_event.is_set():
                    log_cb(">> 任務中斷，保留已轉錄部分。")
                    break
                
                text_line = f"[{segment.start:>7.2f}s -> {segment.end:>7.2f}s] {segment.text}"
                f.write(text_line + "\n")
                
                progress = min(segment.end / duration, 1.0)
                progress_cb(progress)
                log_cb(text_line)

        if not stop_event.is_set():
            log_cb(f"✅ 完成！儲存至: {output_file.name}")
            return True

    except Exception as e:
        log_cb(f"❌ 錯誤: {str(e)}")
        return False