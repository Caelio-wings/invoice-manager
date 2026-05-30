"""
发票夹子 — Web UI 入口点

pip 安装后可通过以下命令运行：
    invoice-manager-web                     # Web UI（含 MCP 接口）
"""
import sys


def web_main():
    """Web UI 入口：委托给 invoice_clipper.web（MCP SSE 自动挂载在 /mcp）"""
    from invoice_clipper.web import main
    sys.argv[0] = "invoice-manager-web"
    main()


if __name__ == "__main__":
    web_main()
