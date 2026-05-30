#!/usr/bin/env python3
"""发票夹子 Web UI 开发入口 — FastAPI + Jinja2 (v3.1.3)

仅用于开发调试，安装后请使用 invoice web 命令。"""
import uvicorn
from invoice_clipper import load_config

if __name__ == "__main__":
    cfg, cfg_path = load_config()
    host = cfg.get("server", {}).get("host", "127.0.0.1")
    port = int(cfg.get("server", {}).get("port", 8000))
    print(f"配置文件: {cfg_path}")
    uvicorn.run("invoice_clipper.web:app", host=host, port=port, reload=True)
