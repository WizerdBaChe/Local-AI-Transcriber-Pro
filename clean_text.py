import re
import os
from pathlib import Path

def clean_transcript():
    """
    讀取 exports 資料夾中的所有 .txt 檔案，
    移除 [ 0.00s -> 5.00s] 格式的時間軸，
    並將內容合併為完整段落。
    """
    export_dir = Path.cwd() / "exports"
    
    if not export_dir.exists():
        print("❌ 找不到 exports 資料夾。")
        return

    # 取得所有 .txt 檔案，排除已經清理過的
    files = [f for f in export_dir.glob("*.txt") if not f.stem.endswith("_cleaned")]

    if not files:
        print("💡 沒有發現需要處理的逐字稿檔案。")
        return

    print(f"🔍 發現 {len(files)} 個檔案，準備開始清理...\n")

    for file_path in files:
        cleaned_file_path = export_dir / f"{file_path.stem}_cleaned.txt"
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            cleaned_content = []
            for line in lines:
                # 使用正則表達式移除像 [ 64.26s -> 66.66s] 或 [ 64.26s] 這樣的時間標籤
                # 規則：匹配中括號內包含數字、點、s、空格或箭頭的所有內容
                text_only = re.sub(r'\[.*?\]', '', line).strip()
                if text_only:
                    cleaned_content.append(text_only)

            # 將所有語句拼湊，中間以空格連接（適合英文）或直接連接（適合中文）
            # 這裡採用空格連接，如果是純中文影片，可以改為 "".join(cleaned_content)
            final_text = " ".join(cleaned_content)

            with open(cleaned_file_path, "w", encoding="utf-8") as f:
                f.write(final_text)

            print(f"✅ 處理完成: {file_path.name} -> {cleaned_file_path.name}")

        except Exception as e:
            print(f"❌ 處理 {file_path.name} 時發生錯誤: {e}")

if __name__ == "__main__":
    clean_transcript()
    input("\n處理結束，按任意鍵退出...")