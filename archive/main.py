import os
import threading
import sys
import time
import re
from pathlib import Path

# 1. 啟用 Windows 高 DPI 支援 (解決字體模糊問題)
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# 抑制 Windows Symlink 警告
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

try:
    import customtkinter as ctk
    from faster_whisper import WhisperModel
    import yt_dlp
except ImportError:
    print("缺少必要套件，請執行: pip install customtkinter faster-whisper yt-dlp")
    sys.exit()

# 路徑定義
BASE_DIR = Path.cwd()
DOWNLOAD_DIR = BASE_DIR / "workspace" / "downloads"
EXPORT_DIR = BASE_DIR / "exports"
MODEL_DIR = BASE_DIR / "models"

for folder in [DOWNLOAD_DIR, EXPORT_DIR, MODEL_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

def sanitize_filename(title):
    return re.sub(r'[\\/*?:"<>|]', "", title).strip()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # --- UI 基礎設定 ---
        self.title("AI Transcriber Pro")
        self.geometry("1050x700")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        
        # 字體設定 (使用系統級高階字體)
        self.font_title = ctk.CTkFont(family="Segoe UI", size=28, weight="bold")
        self.font_h2 = ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        self.font_body = ctk.CTkFont(family="Segoe UI", size=13)
        self.font_mono = ctk.CTkFont(family="Consolas", size=13) # 用於日誌輸出

        self.is_processing = False
        self.stop_event = threading.Event()

        # --- 網格佈局 (Grid System) ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ==========================================
        # 左側導航欄 (Sidebar)
        # ==========================================
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#1c1c1e")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(4, weight=1) # 讓下方留白

        self.logo_label = ctk.CTkLabel(self.sidebar, text="AI Studio", font=self.font_title, text_color="#ffffff")
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 10), sticky="w")
        
        self.version_label = ctk.CTkLabel(self.sidebar, text="Local Transcriber v2.0", font=self.font_body, text_color="#8e8e93")
        self.version_label.grid(row=1, column=0, padx=20, pady=(0, 30), sticky="w")

        # 側邊欄 - 模型設定
        self.setting_label = ctk.CTkLabel(self.sidebar, text="核心設定 (ENGINE)", font=self.font_body, text_color="#8e8e93")
        self.setting_label.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="w")
        
        self.model_option = ctk.CTkOptionMenu(
            self.sidebar, 
            values=["base", "small", "medium", "large-v3"],
            font=self.font_body,
            fg_color="#2c2c2e",
            button_color="#3a3a3c",
            button_hover_color="#48484a"
        )
        self.model_option.set("large-v3")
        self.model_option.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

        # ==========================================
        # 主內容區 (Main Workspace)
        # ==========================================
        self.main_content = ctk.CTkFrame(self, fg_color="#121212", corner_radius=0)
        self.main_content.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_rowconfigure(2, weight=1)

        # 標題區
        self.header_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=40, pady=(40, 20))
        ctk.CTkLabel(self.header_frame, text="新建轉錄任務", font=self.font_title).pack(side="left")

        # 卡片 1: 任務輸入區
        self.input_card = ctk.CTkFrame(self.main_content, fg_color="#1c1c1e", corner_radius=15)
        self.input_card.grid(row=1, column=0, sticky="ew", padx=40, pady=10)
        
        self.entry_url = ctk.CTkEntry(
            self.input_card, 
            placeholder_text="在此貼上 YouTube 影片網址 (例如: https://youtu.be/...)", 
            height=50, 
            font=self.font_body,
            border_width=1,
            border_color="#3a3a3c",
            fg_color="#000000"
        )
        self.entry_url.pack(fill="x", padx=25, pady=(25, 15))

        self.btn_frame = ctk.CTkFrame(self.input_card, fg_color="transparent")
        self.btn_frame.pack(fill="x", padx=25, pady=(0, 25))
        
        self.btn_run = ctk.CTkButton(
            self.btn_frame, 
            text="開始執行", 
            command=self.start_task, 
            height=40, 
            width=140,
            font=self.font_h2,
            corner_radius=8,
            fg_color="#0a84ff",
            hover_color="#0066cc"
        )
        self.btn_run.pack(side="left")
        
        self.btn_stop = ctk.CTkButton(
            self.btn_frame, 
            text="強制停止", 
            command=self.stop_task, 
            height=40, 
            width=100,
            font=self.font_body,
            corner_radius=8,
            fg_color="#ff453a",
            hover_color="#d70015",
            state="disabled"
        )
        self.btn_stop.pack(side="left", padx=15)

        # 卡片 2: 狀態與日誌監控區
        self.log_card = ctk.CTkFrame(self.main_content, fg_color="#1c1c1e", corner_radius=15)
        self.log_card.grid(row=2, column=0, sticky="nsew", padx=40, pady=(10, 40))
        self.log_card.grid_columnconfigure(0, weight=1)
        self.log_card.grid_rowconfigure(2, weight=1)

        self.status_header = ctk.CTkFrame(self.log_card, fg_color="transparent")
        self.status_header.grid(row=0, column=0, sticky="ew", padx=25, pady=(20, 10))
        
        self.status_title = ctk.CTkLabel(self.status_header, text="即時監控", font=self.font_h2)
        self.status_title.pack(side="left")
        
        self.status_label = ctk.CTkLabel(self.status_header, text="系統待命", font=self.font_body, text_color="#34c759")
        self.status_label.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(self.log_card, height=6, progress_color="#0a84ff", fg_color="#3a3a3c")
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=25, pady=(0, 15))
        self.progress_bar.set(0)

        # 日誌輸出框 (使用等寬字體增強科技感)
        self.textbox = ctk.CTkTextbox(
            self.log_card, 
            font=self.font_mono, 
            fg_color="#000000", 
            border_spacing=15,
            text_color="#e5e5ea"
        )
        self.textbox.grid(row=2, column=0, sticky="nsew", padx=25, pady=(0, 25))

    # --- 邏輯功能 ---
    def log(self, message):
        self.textbox.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.textbox.see("end")

    def update_ui_state(self, processing):
        self.is_processing = processing
        if processing:
            self.btn_run.configure(state="disabled", text="運算中...", fg_color="#3a3a3c")
            self.btn_stop.configure(state="normal")
            self.stop_event.clear()
            self.progress_bar.set(0)
            self.status_label.configure(text="初始化...", text_color="#ff9f0a") # 琥珀色
        else:
            self.btn_run.configure(state="normal", text="開始執行", fg_color="#0a84ff")
            self.btn_stop.configure(state="disabled")

    def stop_task(self):
        self.stop_event.set()
        self.log(">> 中斷指令已發送，正在安全關閉任務...")
        self.status_label.configure(text="正在終止", text_color="#ff453a") # 紅色

    def start_task(self):
        url = self.entry_url.get().strip()
        if not url or self.is_processing: return
        self.update_ui_state(True)
        threading.Thread(target=self.work_thread, args=(url,), daemon=True).start()

    def work_thread(self, url):
        audio_path = None
        try:
            # 1. 抓取資訊與下載
            self.log(f"解析網址: {url}")
            ydl_opts = {
                'format': 'm4a/bestaudio/best',
                'outtmpl': str(DOWNLOAD_DIR / '%(id)s.%(ext)s'),
                'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}],
                'quiet': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                audio_path = DOWNLOAD_DIR / f"{info['id']}.mp3"
                duration = info.get('duration', 1)
                video_title = sanitize_filename(info.get('title', info['id']))

            self.status_label.configure(text="模型載入中")
            self.log(f"目標影片: {video_title}")
            
            if self.stop_event.is_set(): raise Exception("使用者強制中止")

            # 2. 模型初始化
            self.log("配置 RTX 5070 (float16) 推論引擎...")
            selected_model = self.model_option.get()
            model = WhisperModel(selected_model, device="cuda", compute_type="float16", download_root=str(MODEL_DIR))

            # 3. 執行轉錄
            self.status_label.configure(text="AI 轉錄中", text_color="#0a84ff")
            self.log("啟動 Whisper 語音識別核心 (啟用 VAD 過濾)...")
            segments, info = model.transcribe(str(audio_path), beam_size=5, vad_filter=True)
            
            output_file = EXPORT_DIR / f"{video_title}.txt"
            
            with open(output_file, "w", encoding="utf-8") as f:
                for segment in segments:
                    if self.stop_event.is_set(): break
                    
                    text_line = f"[{segment.start:>7.2f}s -> {segment.end:>7.2f}s] {segment.text}"
                    f.write(text_line + "\n")
                    
                    # 更新視覺元件
                    progress = min(segment.end / duration, 1.0)
                    self.progress_bar.set(progress)
                    self.textbox.insert("end", text_line + "\n")
                    self.textbox.see("end")

            if not self.stop_event.is_set():
                self.log(f"完成！逐字稿已儲存: {output_file.name}")
                self.status_label.configure(text="任務完成", text_color="#34c759")

        except Exception as e:
            self.log(f"錯誤中斷: {str(e)}")
            self.status_label.configure(text="系統錯誤", text_color="#ff453a")
        finally:
            if audio_path and audio_path.exists():
                try: os.remove(audio_path)
                except: pass
            self.update_ui_state(False)

if __name__ == "__main__":
    app = App()
    app.mainloop()