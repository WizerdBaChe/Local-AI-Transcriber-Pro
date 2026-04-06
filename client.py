import os
import threading
import sys
import time
import re
from pathlib import Path
from tkinter import filedialog, messagebox

# 啟用 Windows 高 DPI 支援
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

try:
    import customtkinter as ctk
    from core.youtube_logic import process_youtube
    from core.local_logic import process_local_file
    from core.orchestrator import MindMapGenerator
except ImportError as e:
    print(f"❌ 錯誤: 缺少套件或找不到核心模組: {e}")
    sys.exit()

# 全域路徑配置
BASE_DIR = Path.cwd()
DOWNLOAD_DIR = BASE_DIR / "workspace" / "downloads"
EXPORT_DIR = BASE_DIR / "exports"
MODEL_DIR = BASE_DIR / "models"
ASSETS_DIR = BASE_DIR / "assets"

for folder in [DOWNLOAD_DIR, EXPORT_DIR, MODEL_DIR, ASSETS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

def sanitize_filename(title):
    return re.sub(r'[\\/*?:"<>|]', "", Path(title).stem).strip()

# ==========================================
# 頁面 1: 啟動首頁 (Launcher)
# ==========================================
class HomePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#F2F2F7", corner_radius=0)
        self.controller = controller
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(self, text="AI Studio Launcher", font=ctk.CTkFont(family="Segoe UI", size=36, weight="bold"), text_color="#1C1C1E").grid(row=0, column=0, pady=(100, 10))
        ctk.CTkLabel(self, text="全方位語音分析與知識視覺化工具", font=ctk.CTkFont(size=16), text_color="#8E8E93").grid(row=1, column=0, pady=(0, 60))

        self.cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_frame.grid(row=2, column=0)
        
        self.create_card("▶ YouTube 轉錄", "自動下載網址並產出逐字稿", "#007AFF", lambda: controller.show_frame("YouTubePage"))
        self.create_card("📁 本地分析", "處理電腦中的影音檔案", "#34C759", lambda: controller.show_frame("LocalPage"))
        self.create_card("🧠 心智圖生成", "將 JSON 轉為視覺化圖譜", "#AF52DE", lambda: controller.show_frame("MindMapPage"))

    def create_card(self, title, desc, color, command):
        card = ctk.CTkButton(self.cards_frame, text=f"{title}\n\n{desc}", 
                               width=250, height=130, font=ctk.CTkFont(size=14, weight="bold"),
                               fg_color="#FFFFFF", text_color="#1C1C1E", border_width=1, border_color="#D1D1D6",
                               hover_color="#E5E5EA", command=command)
        card.pack(side="left", padx=15)

# ==========================================
# 頁面 2: YouTube 轉錄器
# ==========================================
class YouTubePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#F2F2F7", corner_radius=0)
        self.controller = controller
        self.is_processing = False
        self.stop_event = threading.Event()
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=40, pady=(40, 20))
        ctk.CTkLabel(header, text="YouTube 影片轉錄", font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), text_color="#1C1C1E").pack(side="left")
        ctk.CTkButton(header, text="← 返回首頁", width=100, height=32, fg_color="transparent", text_color="#007AFF", hover_color="#E5E5EA", command=lambda: controller.show_frame("HomePage")).pack(side="right")

        input_card = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=15, border_width=1, border_color="#D1D1D6")
        input_card.grid(row=1, column=0, sticky="ew", padx=40, pady=10)
        
        self.entry_url = ctk.CTkEntry(input_card, placeholder_text="在此貼上影片網址...", height=45, fg_color="#F2F2F7", border_width=0, text_color="#1C1C1E")
        self.entry_url.pack(fill="x", padx=25, pady=(25, 15))

        btn_frame = ctk.CTkFrame(input_card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=25, pady=(0, 25))
        self.btn_run = ctk.CTkButton(btn_frame, text="🚀 開始轉錄", command=self.start_task, height=40, width=140, fg_color="#007AFF")
        self.btn_run.pack(side="left")
        
        self.btn_stop = ctk.CTkButton(btn_frame, text="🛑 停止", command=self.stop_task, height=40, width=90, 
                                      fg_color="#FFE5E5", text_color="#D70015", hover_color="#FFD1D1", state="disabled",
                                      border_width=1, border_color="#FFB2B2")
        self.btn_stop.pack(side="left", padx=15)

        # [新增] 清空紀錄按鈕
        self.btn_reset = ctk.CTkButton(btn_frame, text="🧹 清空", command=self.reset_ui, height=40, width=90, 
                                       fg_color="#E5E5EA", text_color="#1C1C1E", hover_color="#D1D1D6")
        self.btn_reset.pack(side="right")

        log_card = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=15, border_width=1, border_color="#D1D1D6")
        log_card.grid(row=2, column=0, sticky="nsew", padx=40, pady=(10, 40))
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_rowconfigure(2, weight=1)

        self.status_label = ctk.CTkLabel(log_card, text="系統待命", text_color="#34C759", font=ctk.CTkFont(weight="bold"))
        self.status_label.grid(row=0, column=0, sticky="e", padx=25, pady=(15, 5))

        self.progress_bar = ctk.CTkProgressBar(log_card, height=8, progress_color="#007AFF", fg_color="#E5E5EA")
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=25, pady=(0, 15))
        self.progress_bar.set(0)

        self.textbox = ctk.CTkTextbox(log_card, font=ctk.CTkFont(family="Consolas", size=13), fg_color="#F9F9F9", text_color="#1C1C1E", border_spacing=10)
        self.textbox.grid(row=2, column=0, sticky="nsew", padx=25, pady=(0, 25))

    def log(self, message):
        self.textbox.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.textbox.see("end")

    def update_progress(self, val):
        self.progress_bar.set(val)
        self.status_label.configure(text=f"分析中: {int(val*100)}%")

    def reset_ui(self):
        """[新增] 清除輸入框、日誌與進度條"""
        self.entry_url.delete(0, "end")
        self.textbox.delete("0.0", "end")
        self.progress_bar.set(0)
        self.status_label.configure(text="系統待命", text_color="#34C759")

    def stop_task(self):
        self.stop_event.set()
        self.log(">> 中斷指令已發送...")

    def start_task(self):
        url = self.entry_url.get().strip()
        if not url or self.is_processing: return
        self.is_processing = True
        self.controller.set_nav_state("disabled")
        self.btn_run.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.btn_reset.configure(state="disabled") # 執行中禁用清空按鈕
        self.stop_event.clear()
        threading.Thread(target=self.work_thread, args=(url,), daemon=True).start()

    def work_thread(self, url):
        success = process_youtube(
            url=url, model_name=self.controller.model_option.get(), 
            download_dir=DOWNLOAD_DIR, export_dir=EXPORT_DIR, model_dir=MODEL_DIR,
            log_cb=self.log, progress_cb=self.update_progress, stop_event=self.stop_event
        )
        self.is_processing = False
        self.btn_run.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.btn_reset.configure(state="normal")
        self.controller.set_nav_state("normal")
        if success: self.status_label.configure(text="任務完成", text_color="#34C759")

# ==========================================
# 頁面 3: 本地檔案轉錄器
# ==========================================
class LocalPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#F2F2F7", corner_radius=0)
        self.controller = controller
        self.is_processing = False
        self.stop_event = threading.Event()
        self.selected_file = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=40, pady=(40, 20))
        ctk.CTkLabel(header, text="本地多媒體轉錄", font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), text_color="#1C1C1E").pack(side="left")
        ctk.CTkButton(header, text="← 返回首頁", width=100, height=32, fg_color="transparent", text_color="#007AFF", hover_color="#E5E5EA", command=lambda: controller.show_frame("HomePage")).pack(side="right")

        input_card = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=15, border_width=1, border_color="#D1D1D6")
        input_card.grid(row=1, column=0, sticky="ew", padx=40, pady=10)
        
        file_box = ctk.CTkFrame(input_card, fg_color="#F2F2F7", corner_radius=8)
        file_box.pack(fill="x", padx=25, pady=25)
        
        self.btn_browse = ctk.CTkButton(file_box, text="📁 選擇檔案", command=self.browse_file, width=120, height=40, fg_color="#34C759")
        self.btn_browse.pack(side="left", padx=15, pady=15)
        self.lbl_path = ctk.CTkLabel(file_box, text="尚未選取檔案", text_color="#8E8E93")
        self.lbl_path.pack(side="left", padx=10)

        btn_row = ctk.CTkFrame(input_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=25, pady=(0, 25))
        self.btn_run = ctk.CTkButton(btn_row, text="🚀 開始分析", command=self.start_task, height=40, width=140, state="disabled")
        self.btn_run.pack(side="left")
        self.btn_stop = ctk.CTkButton(btn_row, text="🛑 停止", command=self.stop_task, height=40, width=90, fg_color="#FFE5E5", text_color="#D70015", hover_color="#FFD1D1", state="disabled")
        self.btn_stop.pack(side="left", padx=15)

        # [新增] 清空紀錄按鈕
        self.btn_reset = ctk.CTkButton(btn_row, text="🧹 清空", command=self.reset_ui, height=40, width=90, 
                                       fg_color="#E5E5EA", text_color="#1C1C1E", hover_color="#D1D1D6")
        self.btn_reset.pack(side="right")

        log_card = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=15, border_width=1, border_color="#D1D1D6")
        log_card.grid(row=2, column=0, sticky="nsew", padx=40, pady=(10, 40))
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_rowconfigure(2, weight=1)

        self.status_label = ctk.CTkLabel(log_card, text="系統待命", text_color="#34C759", font=ctk.CTkFont(weight="bold"))
        self.status_label.grid(row=0, column=0, sticky="e", padx=25, pady=(15, 5))

        self.progress_bar = ctk.CTkProgressBar(log_card, height=8, progress_color="#007AFF", fg_color="#E5E5EA")
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=25, pady=(0, 15))
        self.progress_bar.set(0)

        self.textbox = ctk.CTkTextbox(log_card, font=ctk.CTkFont(family="Consolas", size=13), fg_color="#F9F9F9", text_color="#1C1C1E", border_spacing=10)
        self.textbox.grid(row=2, column=0, sticky="nsew", padx=25, pady=(0, 25))

    def log(self, message):
        self.textbox.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.textbox.see("end")

    def update_progress(self, val):
        self.progress_bar.set(val)
        self.status_label.configure(text=f"運算中: {int(val*100)}%")

    def reset_ui(self):
        """[新增] 清除檔案選取與日誌"""
        self.selected_file = None
        self.lbl_path.configure(text="尚未選取檔案", text_color="#8E8E93")
        self.textbox.delete("0.0", "end")
        self.progress_bar.set(0)
        self.status_label.configure(text="系統待命", text_color="#34C759")
        self.btn_run.configure(state="disabled")

    def browse_file(self):
        path = filedialog.askopenfilename(title="選擇檔案", filetypes=(("媒體檔案", "*.mp3 *.wav *.mp4 *.m4a *.mkv"), ("所有檔案", "*.*")))
        if path:
            self.selected_file = path
            self.lbl_path.configure(text=Path(path).name, text_color="#1C1C1E")
            self.btn_run.configure(state="normal")

    def stop_task(self):
        self.stop_event.set()
        self.log(">> 正在嘗試停止運算...")

    def start_task(self):
        if not self.selected_file: return
        self.is_processing = True
        self.controller.set_nav_state("disabled")
        self.btn_run.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.btn_browse.configure(state="disabled")
        self.btn_reset.configure(state="disabled")
        self.stop_event.clear()
        threading.Thread(target=self.work_thread, daemon=True).start()

    def work_thread(self):
        success = process_local_file(
            file_path=self.selected_file, model_name=self.controller.model_option.get(),
            export_dir=EXPORT_DIR, model_dir=MODEL_DIR,
            log_cb=self.log, progress_cb=self.update_progress, stop_event=self.stop_event
        )
        self.is_processing = False
        self.btn_run.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.btn_browse.configure(state="normal")
        self.btn_reset.configure(state="normal")
        self.controller.set_nav_state("normal")
        if success: self.status_label.configure(text="任務完成", text_color="#34C759")

# ==========================================
# 頁面 4: 心智圖生成器
# ==========================================
class MindMapPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="#F2F2F7", corner_radius=0)
        self.controller = controller
        self.selected_json = None
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=40, pady=(40, 20))
        ctk.CTkLabel(header, text="心智圖生成", font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), text_color="#1C1C1E").pack(side="left")
        ctk.CTkButton(header, text="← 返回首頁", width=100, height=32, fg_color="transparent", text_color="#007AFF", hover_color="#E5E5EA", command=lambda: controller.show_frame("HomePage")).pack(side="right")

        input_card = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=15, border_width=1, border_color="#D1D1D6")
        input_card.grid(row=1, column=0, sticky="ew", padx=40, pady=10)
        
        file_box = ctk.CTkFrame(input_card, fg_color="#F2F2F7", corner_radius=8)
        file_box.pack(fill="x", padx=25, pady=25)
        
        self.btn_browse = ctk.CTkButton(file_box, text="📂 選擇 JSON", command=self.browse_json, fg_color="#AF52DE", hover_color="#8942B1")
        self.btn_browse.pack(side="left", padx=15, pady=15)
        self.lbl_path = ctk.CTkLabel(file_box, text="選擇轉錄後產出的 JSON 檔案", text_color="#8E8E93")
        self.lbl_path.pack(side="left", padx=10)

        btn_row = ctk.CTkFrame(input_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=25, pady=(0, 25))
        self.btn_gen = ctk.CTkButton(btn_row, text="🪄 生成 HTML 心智圖", command=self.generate_map, height=40, width=180, state="disabled", fg_color="#AF52DE", hover_color="#8942B1")
        self.btn_gen.pack(side="left")

        # [新增] 清空紀錄按鈕
        self.btn_reset = ctk.CTkButton(btn_row, text="🧹 清空", command=self.reset_ui, height=40, width=90, 
                                       fg_color="#E5E5EA", text_color="#1C1C1E", hover_color="#D1D1D6")
        self.btn_reset.pack(side="right")

        log_card = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=15, border_width=1, border_color="#D1D1D6")
        log_card.grid(row=2, column=0, sticky="nsew", padx=40, pady=(10, 40))
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_rowconfigure(0, weight=1)

        self.textbox = ctk.CTkTextbox(log_card, font=ctk.CTkFont(family="Consolas", size=13), fg_color="#F9F9F9", text_color="#1C1C1E", border_spacing=10)
        self.textbox.grid(row=0, column=0, sticky="nsew", padx=25, pady=25)

    def browse_json(self):
        path = filedialog.askopenfilename(title="選擇 JSON", filetypes=(("JSON 資料", "*.json"), ("所有檔案", "*.*")))
        if path:
            self.selected_json = path
            self.lbl_path.configure(text=Path(path).name, text_color="#1C1C1E")
            self.btn_gen.configure(state="normal")

    def reset_ui(self):
        """[新增] 清除 JSON 檔案選取與日誌"""
        self.selected_json = None
        self.lbl_path.configure(text="選擇轉錄後產出的 JSON 檔案", text_color="#8E8E93")
        self.textbox.delete("0.0", "end")
        self.btn_gen.configure(state="disabled")

    def generate_map(self):
        if not self.selected_json: return
        template_path = ASSETS_DIR / "template.html"
        output_html = EXPORT_DIR / f"{Path(self.selected_json).stem}_map.html"
        
        self.textbox.insert("end", f"[{time.strftime('%H:%M:%S')}] 開始生成...\n")
        generator = MindMapGenerator(template_path=str(template_path))
        success, result = generator.generate(self.selected_json, str(output_html))
        
        if success:
            self.textbox.insert("end", f"[{time.strftime('%H:%M:%S')}] ✅ 成功儲存於：\n{result}\n\n")
            messagebox.showinfo("成功", f"心智圖已匯出！")
        else:
            self.textbox.insert("end", f"[{time.strftime('%H:%M:%S')}] ❌ 錯誤：{result}\n")

# ==========================================
# 總控台 (Main App Controller)
# ==========================================
class ClientApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI Studio - Pro Max Edition")
        self.geometry("1150x800")
        ctk.set_appearance_mode("light")
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color="#FFFFFF", border_width=1, border_color="#E5E5EA")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(7, weight=1)

        ctk.CTkLabel(self.sidebar, text="AI STUDIO", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color="#007AFF").grid(row=0, column=0, padx=20, pady=(40, 40))

        self.nav_btns = {}
        self.add_nav_btn(1, "🏠 Launcher", "HomePage")
        self.add_nav_btn(2, "▶ YouTube 轉錄", "YouTubePage")
        self.add_nav_btn(3, "📁 本地分析", "LocalPage")
        self.add_nav_btn(4, "🧠 心智圖生成", "MindMapPage")

        ctk.CTkLabel(self.sidebar, text="轉錄引擎設定", text_color="#8E8E93", font=ctk.CTkFont(size=12)).grid(row=8, column=0, padx=20, pady=(10, 5), sticky="w")
        self.model_option = ctk.CTkOptionMenu(self.sidebar, values=["base", "small", "medium", "large-v3"], fg_color="#F2F2F7", text_color="#1C1C1E", button_color="#D1D1D6", button_hover_color="#C7C7CC")
        self.model_option.set("large-v3")
        self.model_option.grid(row=9, column=0, padx=20, pady=(0, 30), sticky="ew")

        self.container = ctk.CTkFrame(self, fg_color="#F2F2F7", corner_radius=0)
        self.container.grid(row=0, column=1, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (HomePage, YouTubePage, LocalPage, MindMapPage):
            page_name = F.__name__
            frame = F(parent=self.container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("HomePage")

    def add_nav_btn(self, row, text, target):
        btn = ctk.CTkButton(self.sidebar, text=text, command=lambda: self.show_frame(target), 
                            fg_color="transparent", text_color="#1C1C1E", hover_color="#F2F2F7", anchor="w", height=40)
        btn.grid(row=row, column=0, padx=15, pady=5, sticky="ew")
        self.nav_btns[target] = btn

    def show_frame(self, page_name):
        self.frames[page_name].tkraise()
        for name, btn in self.nav_btns.items():
            if name == page_name:
                btn.configure(fg_color="#E5F2FF", text_color="#007AFF")
            else:
                btn.configure(fg_color="transparent", text_color="#1C1C1E")

    def set_nav_state(self, state):
        for btn in self.nav_btns.values(): btn.configure(state=state)
        self.model_option.configure(state=state)

if __name__ == "__main__":
    app = ClientApp()
    app.mainloop()