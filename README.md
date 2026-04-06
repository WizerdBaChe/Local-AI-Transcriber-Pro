# AI Studio Pro Max - 本地影音轉錄與知識視覺化工具

# 

# 這是一個專為高效能本地運算（優化於 RTX 5070）打造的 AI 工具箱。整合了 YouTube 下載、高效語音轉文字（Whisper）以及心智圖生成功能。

# 

# 🌟 核心特色

# 

# RTX 5070 優化: 採用 faster-whisper 並使用 float16 精度與 VAD 過濾，1 小時影片僅需約 3\~5 分鐘即可完成轉錄。

# 

# 全本地化運算: 保護隱私，無需支付 API 費用，無額度限制。

# 

# 多功能整合: 支援 YouTube URL 下載及本地影音檔案處理。

# 

# 知識視覺化: 內建心智圖生成器，可將結構化 JSON 轉為單一 HTML 離線心智圖。

# 

# 現代化 UI: 採用淺色系設計，優化長時間使用的視覺舒適度。

# 

# 🛠️ 環境要求

# 

# GPU: NVIDIA RTX 30/40/50 系列 (建議 8GB VRAM 以上)

# 

# 系統: Windows 10/11

# 

# 必備工具: FFmpeg (需加入系統環境變數)

# 

# 🚀 快速開始

# 

# 建立環境:

# 

# python -m venv .venv

# .\\.venv\\Scripts\\activate

# pip install -r requirements.txt

# 

# 

# 初始化結構: 執行 python init\_project.py 自動建立必要目錄。

# 

# 啟動程式: 雙擊執行 run\_app.bat。

# 

# 📁 專案架構

# 

# client.py: 總控台 GUI 介面。

# 

# core/: 存放各項任務的核心邏輯。

# 

# assets/: 存放心智圖 HTML 模板。

# 

# exports/: 存放轉錄後的 .txt 檔案與 HTML 心智圖。

# 

# 📜 授權協議

# 

# 本專案採用 MIT License。引用之模型權重版權歸原作者所有。

