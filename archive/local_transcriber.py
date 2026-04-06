import os
import threading
import sys
import time
import re
import subprocess
from pathlib import Path

# 抑制 Windows Symlink 警告
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

try:
    import customtkinter as ctk
    from customtkinter import filedialog
    from faster_whisper import WhisperModel
except ImportError:
    print("缺少必要套件，請執行: pip install customtkinter faster-whisper")
    sys.exit()

BASE_DIR = Path.cwd()
EXPORT_DIR = BASE_DIR / "exports"
MODEL_DIR = BASE_DIR / "models"

for folder in [EXPORT_DIR, MODEL_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

def sanitize_filename(title):
    return re.sub(r'[\\/*?:"<>|]', "", title).strip()

def get_video_duration(file_path):
    """利用 ffprobe 獲取本地影片的精確秒數"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        return float(result.stdout.strip())
    except Exception as e:
        print(f"獲取影片長度失敗，預設為 1 秒: {e}")
        return 1.0

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI 本地影片轉錄工具 - RTX 5070 效能優化版")
        self.geometry("800x700")
        self.is_processing = False
        self.stop_event = threading.Event()
        self.selected_file_path = None

        self.grid_columnconfigure(0, weight=1)
        self.label_title = ctk.CTkLabel(self, text="本地影音檔案分析", font=ctk.CTkFont(size=26, weight="bold"))
        self.label_title.grid(row=0, column=0, pady=(20, 10))

        self.file_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.file_frame.grid(row=1, column=0, pady=10)
        
        self.btn_browse = ctk.CTkButton(self.file_frame, text="📂 選擇本地影片", command=self.browse_file, width=150, height=40)
        self.btn_browse.pack(side="left", padx=10)
        
        self.lbl_file_path = ctk.CTkLabel(self.file_frame, text="尚未選擇檔案...", width=400, anchor="w")
        self.lbl_file_path.pack(side="left", padx=10)

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.grid(row=2, column=0, pady=15)

        self.btn_run = ctk.CTkButton(self.btn_frame, text="🚀 開始分析", command=self.start_task, width=160, height=45, state="disabled")
        self.btn_run.pack(side="left", padx=10)

        self.btn_stop = ctk.CTkButton(self.btn_frame, text="🛑 停止運算", command=self.stop_task, fg_color="#942727", state="disabled")
        self.btn_stop.pack(side="left", padx=10)

        self.status_label = ctk.CTkLabel(self, text="準備就緒", text_color="#3a7ebf")
        self.status_label.grid(row=3, column=0)

        self.progress_bar = ctk.CTkProgressBar(self, width=600)
        self.progress_bar.grid(row=4, column=0, pady=10)
        self.progress_bar.set(0)

        self.textbox = ctk.CTkTextbox(self, width=700, height=300, font=("Microsoft JhengHei", 12))
        self.textbox.grid(row=5, column=0, padx=20, pady=10)

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="選擇影片或音訊檔案",
            filetypes=[("Media Files", "*.mp4 *.mkv *.avi *.mov *.mp3 *.wav *.m4a"), ("All Files", "*.*")]
        )
        if file_path:
            self.selected_file_path = Path(file_path)
            self.lbl_file_path.configure(text=self.selected_file_path.name)
            self.btn_run.configure(state="normal")

    def log(self, message):
        self.textbox.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.textbox.see("end")

    def stop_task(self):
        self.stop_event.set()
        self.log("🛑 已發出中斷請求，將在處理完當前片段後停止...")

    def start_task(self):
        if not self.selected_file_path or self.is_processing: return
        self.is_processing = True
        self.btn_browse.configure(state="disabled")
        self.btn_run.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.stop_event.clear()
        threading.Thread(target=self.work_thread, args=(self.selected_file_path,), daemon=True).start()

    def work_thread(self, file_path):
        try:
            self.status_label.configure(text="正在讀取影片資訊...")
            duration = get_video_duration(file_path)
            video_title = sanitize_filename(file_path.stem)

            self.status_label.configure(text="正在初始化 RTX 5070 運算引擎...")
            model = WhisperModel("large-v3", device="cuda", compute_type="float16", download_root=str(MODEL_DIR))
            
            self.log(f"開始分析檔案: {file_path.name} (長度: {duration:.2f} 秒)")
            segments, info = model.transcribe(str(file_path), beam_size=5, vad_filter=True)
            
            output_file = EXPORT_DIR / f"{video_title}.txt"
            
            with open(output_file, "w", encoding="utf-8") as f:
                for segment in segments:
                    if self.stop_event.is_set(): break
                    text_line = f"[{segment.start:>7.2f}s -> {segment.end:>7.2f}s] {segment.text}"
                    f.write(text_line + "\n")
                    
                    progress = min(segment.end / duration, 1.0) if duration > 1 else 0
                    self.progress_bar.set(progress)
                    self.status_label.configure(text=f"分析中: {int(progress*100)}%")
                    self.textbox.insert("end", text_line + "\n")
                    self.textbox.see("end")

            if not self.stop_event.is_set():
                self.progress_bar.set(1.0)
                self.status_label.configure(text="分析完成！")
                self.log(f"✅ 完成！檔案已儲存至: {output_file.name}")

        except Exception as e:
            self.log(f"❌ 錯誤: {str(e)}")
            self.status_label.configure(text="發生錯誤")
        finally:
            self.is_processing = False
            self.btn_browse.configure(state="normal")
            self.btn_run.configure(state="normal")
            self.btn_stop.configure(state="disabled")

if __name__ == "__main__":
    app = App()
    app.mainloop()