"""一键演示：同时启动后端 API 与前端控制台。

用法（在 FinFlow 根目录）：
    .venv\\Scripts\\python.exe demo.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = ROOT / ".venv" / "Scripts" / "python.exe"


def main() -> int:
    if not PY.exists():
        print("未找到 .venv，请先执行 python -m venv .venv 并安装依赖")
        return 1

    procs: list[subprocess.Popen] = []
    try:
        print("启动后端 API ...")
        procs.append(
            subprocess.Popen(
                [str(PY), "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000"],
                cwd=ROOT,
            )
        )
        time.sleep(2)
        npm = shutil.which("npm") or "npm.cmd"
        print("启动前端控制台 ...")
        procs.append(
            subprocess.Popen([npm, "run", "dev"], cwd=ROOT / "frontend")
        )
        print("\nFinFlow 已启动：")
        print("  前端控制台: http://localhost:5173")
        print("  后端 API:    http://127.0.0.1:8000")
        print("  演示数据:    AAPL / MSFT（mock 模式）")
        print("\n按 Ctrl+C 停止全部服务。")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止 ...")
    finally:
        for p in procs:
            p.terminate()
        print("已停止。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
