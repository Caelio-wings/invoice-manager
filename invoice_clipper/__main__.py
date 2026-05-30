"""
发票夹子 — CLI 入口点

pip 安装后可通过以下命令运行：
    invoice-manager scan|list|query|...     # CLI
    invoice-manager-web                     # Web UI
"""
import sys


def cli_main():
    """CLI 入口：委托给 invoice_clipper.cli"""
    from invoice_clipper.cli import main
    sys.argv[0] = "invoice-manager"
    main()


def web_main():
    """Web UI 入口：委托给 invoice_clipper.web"""
    from invoice_clipper.web import main
    sys.argv[0] = "invoice-manager-web"
    main()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "web":
        web_main()
    else:
        cli_main()
