import json
import os
import argparse
import logging
from typing import Dict, Any, Tuple

# ---------------------------------------------------------
# 系統觀測性設定 (Observability Configuration)
# ---------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("MindMapOrchestrator")

class MindMapGenerator:
    """
    STT 心智圖生成器 (Phase 2 - 增強版)
    職責：資料解析、容錯處理、生成 Markdown 並注入 CDN 模板。
    """
    def __init__(self, template_path: str):
        self.template_path = template_path

    def _validate_schema(self, data: Dict[str, Any]) -> bool:
        """
        [安全性檢查] 確保 JSON 具備最基本的渲染結構。
        不檢查 metadata，因為它是選填的。
        """
        try:
            root = data.get("root", {})
            return "content" in root
        except AttributeError:
            return False

    def _format_node_content(self, node: Dict[str, Any]) -> str:
        """
        [資料處理] 提取節點內容並安全地附加 Metadata (如時間戳)。
        實作了「缺失不報錯，優雅忽略」的容錯機制。
        """
        # 1. 取得主內容，提供防呆預設值
        content = node.get("content", "未命名節點")

        # 2. 安全地嘗試獲取 metadata 字典
        metadata = node.get("metadata", {})

        # 3. 嘗試獲取時間戳
        timestamp = metadata.get("timestamp")

        if timestamp:
            # 使用 Markdown 的行內程式碼 (`) 語法來凸顯時間戳
            return f"{content} 🕒 `{timestamp}`"
        
        return content

    def _to_markdown(self, node: Dict[str, Any], level: int = 1) -> str:
        """
        [資料轉換] 將 JSON 樹遞迴轉為 Markdown 標題清單
        """
        if not node:
            return ""

        indent = "#" * level
        
        # 使用封裝好的容錯方法獲取節點文字
        formatted_text = self._format_node_content(node)
        md_line = f"{indent} {formatted_text}\n"
        
        # 安全地遞迴子節點
        children = node.get("children", [])
        if isinstance(children, list):
            for child in children:
                md_line += self._to_markdown(child, level + 1)
            
        return md_line

    def generate(self, input_json: str, output_html: str) -> Tuple[bool, str]:
        """
        執行生成流程。
        返回 Tuple: (是否成功, 訊息或檔案路徑) 供 GUI Launcher 調用判斷。
        """
        try:
            logger.info(f"開始處理 JSON 檔案: {input_json}")
            
            # 1. 讀取並驗證 JSON
            if not os.path.exists(input_json):
                raise FileNotFoundError(f"輸入檔案不存在: {input_json}")

            with open(input_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not self._validate_schema(data):
                raise ValueError("JSON 格式驗證失敗：缺少 root 節點或 content 屬性。")

            # 2. 將結構化資料降維成 Markdown 字串
            markdown_text = self._to_markdown(data["root"])
            logger.debug(f"Markdown 轉換完成，共 {len(markdown_text)} 字元")

            # 3. 讀取輕量級 HTML 模板
            if not os.path.exists(self.template_path):
                raise FileNotFoundError(f"找不到模板檔案: {self.template_path}")
            
            with open(self.template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()

            # 4. 注入資料
            final_content = template_content.replace("{{MARKDOWN_DATA}}", markdown_text.strip())

            # 5. 寫出實體 HTML 檔案
            os.makedirs(os.path.dirname(output_html), exist_ok=True)
            with open(output_html, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            file_size_kb = os.path.getsize(output_html) / 1024
            abs_path = os.path.abspath(output_html)
            
            logger.info(f"生成成功！檔案大小: {file_size_kb:.2f} KB")
            logger.info(f"輸出位置: {abs_path}")
            
            # 回傳成功標記與絕對路徑，利於 GUI 調用
            return True, abs_path

        except Exception as e:
            error_msg = f"生成失敗: {str(e)}"
            logger.error(error_msg, exc_info=False) # 在除錯時可將 exc_info 改為 True 顯示 Traceback
            return False, error_msg

# ---------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="STT Mind Map Generator (Phase 2)")
    parser.add_argument("-i", "--input", required=True, help="輸入的 JSON 檔案路徑")
    parser.add_argument("-o", "--output", required=True, help="輸出的 HTML 檔案路徑")
    parser.add_argument("-t", "--template", default="assets/template.html", help="HTML 模板路徑")
    
    args = parser.parse_args()

    generator = MindMapGenerator(template_path=args.template)
    success, result = generator.generate(args.input, args.output)
    
    # 根據執行結果設定 Exit Code，這對 CLI 腳本串接很重要
    if not success:
        import sys
        sys.exit(1)