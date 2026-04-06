import ast
import os

def analyze_code(file_path):
    if not os.path.exists(file_path):
        print(f"❌ 找不到檔案: {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    print(f"🔍 正在分析 {file_path} 的語法結構...\n")
    
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    imports = []
    
    for node in tree.body:
        if isinstance(node, ast.Import):
            for n in node.names:
                imports.append(n.name)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)

    print(f"📦 導入的模組: {', '.join(set(imports))}")
    print(f"🏛️ 定義的類別: {[c.name for c in classes]}")
    
    for cls in classes:
        methods = [n.name for n in cls.body if isinstance(n, ast.FunctionDef)]
        print(f"  └─ {cls.name} 的方法: {methods}")

    # 檢查關鍵邏輯：是否有使用 Threading
    has_threading = any("threading" in imp for imp in imports)
    print(f"\n✅ 多線程支援: {'通過' if has_threading else '未偵測到'}")
    
    # 檢查是否包含 WhisperModel 調用
    code_str = ast.dump(tree)
    if "WhisperModel" in code_str:
        print("✅ Whisper 引擎調用: 通過")
    if "YoutubeDL" in code_str:
        print("✅ YouTube 下載模組: 通過")

if __name__ == "__main__":
    analyze_code("main.py")