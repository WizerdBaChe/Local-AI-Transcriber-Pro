import customtkinter as ctk
import subprocess
import sys
from pathlib import Path

class Launcher(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI 轉錄工具啟動器")
        self.geometry("450x380")
        
        # 讓視窗置中顯示
        self.eval('tk::PlaceWindow . center')
        self.grid_columnconfigure(0, weight=1)

        self.label_title = ctk.CTkLabel(self, text="請選擇要使用的工具", font=ctk.CTkFont(size=24, weight="bold"))
        self.label_title.grid(row=0, column=0, pady=(30, 20))

        # YouTube 工具按鈕 (預設藍色系)
        self.btn_youtube = ctk.CTkButton(self, text="🌐 YouTube 線上影片轉錄", 
                                        font=ctk.CTkFont(size=18, weight="bold"), 
                                        height=70, width=320,
                                        command=self.launch_youtube)
        self.btn_youtube.grid(row=1, column=0, pady=15)

        # 本地端工具按鈕 (綠色系以作區分)
        self.btn_local = ctk.CTkButton(self, text="📂 本地端影片/音訊轉錄", 
                                      font=ctk.CTkFont(size=18, weight="bold"), 
                                      height=70, width=320,
                                      fg_color="#2b7b5c", hover_color="#1e5c44",
                                      command=self.launch_local)
        self.btn_local.grid(row=2, column=0, pady=15)

    def launch_youtube(self):
        self.run_script("main.py")

    def launch_local(self):
        self.run_script("local_transcriber.py")

    def run_script(self, script_name):
        script_path = Path.cwd() / script_name
        if script_path.exists():
            # 關閉目前的啟動器視窗，並啟動目標程式
            self.destroy()
            subprocess.Popen([sys.executable, str(script_path)])
        else:
            print(f"錯誤: 找不到檔案 {script_name}，請確認檔案是否存在於根目錄。")

if __name__ == "__main__":
    # 設定外觀主題
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    
    app = Launcher()
    app.mainloop()