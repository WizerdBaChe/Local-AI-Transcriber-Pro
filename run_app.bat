@echo off
title AI Studio Launcher
echo [1/2] 正在檢查環境結構...
python init_project.py

echo [2/2] 正在啟動 AI Studio (淺色模式)...
:: 若要隱藏視窗，將 python 改成 pythonw 並在前面加上 start /b
:: 建議初次執行保持 python 模式以觀察 log
start /b .venv\Scripts\pythonw.exe client.py
exit