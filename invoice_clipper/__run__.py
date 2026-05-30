#!/usr/bin/env python3
"""
发票夹子 Web UI — 启动入口（v3.1.3）
"""
import sys
import os
import webbrowser


def main():
    # 加载配置
    from invoice_clipper import load_config
    cfg, cfg_path = load_config()
    root = cfg.get("storage", {}).get("base_dir", "")

    # 进程锁
    from invoice_clipper.cli import acquire_lock
    if not acquire_lock(root):
        print("  退出（已有实例运行）")
        sys.exit(1)

    host = cfg.get("server", {}).get("host", "127.0.0.1")
    port = int(cfg.get("server", {}).get("port", 8000))
    url = f"http://{host}:{port}"

    print(f"🚀 发票夹子正在启动 ...")
    print(f"   📍 {url}")
    print(f"   📄 {cfg_path}")

    # 后台打开浏览器
    import threading
    threading.Timer(2.5, lambda: webbrowser.open(url)).start()

    # 启动 uvicorn
    from invoice_clipper.web import app
    import uvicorn
    try:
        uvicorn.run(app, host=host, port=port, reload=False)
    finally:
        from invoice_clipper.cli import release_lock
        release_lock(root)


if __name__ == "__main__":
    main()
