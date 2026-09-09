# -*- coding: utf-8 -*-
"""PushIt 桌面启动器：双击即用（PyInstaller onefile 入口）。

行为：初始化本地库（幂等）→ 起本地服务 8765 → 自动打开浏览器（?api=1）。
数据写在 exe 同目录 data 目录下；前端/后端资源来自打包内容。
"""
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


def main():
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    data_dir = Path.cwd() / "data"
    data_dir.mkdir(exist_ok=True)
    os.environ["PUSHIT_DATA_DIR"] = str(data_dir)
    os.environ["PUSHIT_FRONT_DIR"] = str(base / "frontend")
    sys.path.insert(0, str(base))

    import uvicorn  # noqa: E402
    import backend.main as appmod  # noqa: E402 —— 静态 import，供 PyInstaller 追踪依赖
    import scripts.seed_mock as sm  # noqa: E402
    sm.main()  # 幂等：迁移 001-003 + mock 种子（首次启动建库）

    threading.Thread(target=uvicorn.run, kwargs=dict(
        app=appmod.app, host="127.0.0.1", port=8765,
        log_level="warning"), daemon=True).start()
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:8765/?api=1")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
