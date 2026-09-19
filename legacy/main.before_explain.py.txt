from __future__ import annotations

import getpass
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
DEEPSEEK_DIR = PROJECT_DIR / "deepseek_agent"
KEY_FILE = DEEPSEEK_DIR / "deepseek_key.txt"


def ensure_api_key() -> None:
    if KEY_FILE.exists() and KEY_FILE.read_text(encoding="utf-8").strip():
        return
    print("首次运行需要配置 DeepSeek API Key。")
    api_key = getpass.getpass("DeepSeek API Key: ").strip()
    if not api_key:
        raise SystemExit("API Key 不能为空。")
    KEY_FILE.write_text(api_key, encoding="utf-8")
    print("API Key 已保存在本机 deepseek_agent/deepseek_key.txt。")


def main() -> None:
    ensure_api_key()
    sys.path.insert(0, str(DEEPSEEK_DIR))
    from deepseek_app import main as run_server

    run_server()


if __name__ == "__main__":
    main()
