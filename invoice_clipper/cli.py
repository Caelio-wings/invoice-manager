#!/usr/bin/env python3
"""
发票夹子 - 主入口 CLI（v3.1.3）
支持 scan, list, query, export, exclude, include, init 命令
"""
import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

from invoice_clipper import load_config, init_db
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

def cmd_scan(config: dict) -> str:
    """扫描监控目录"""
    from invoice_clipper.processor import InvoiceProcessor

    proc = InvoiceProcessor(config)
    total = 0

    # 扫描本地监控目录
    for watch_dir in config.get("watch_dirs", []):
        watch_path = Path(watch_dir).expanduser()
        if watch_path.exists():
            results = proc.process_directory(watch_path, source="dir")
            total += len(results)
        else:
            logger.warning(f"监控目录不存在: {watch_path}")

    return f"✅ 扫描完成，共处理 {total} 张发票"


def cmd_list(config: dict) -> str:
    """列出所有发票"""
    from invoice_clipper.database import query_invoices

    invoices = query_invoices({"only_included": False})

    if not invoices:
        return "没有发票记录"

    total_amount = sum(i.get("amount_with_tax") or 0 for i in invoices)
    lines = [f"共 {len(invoices)} 张发票，合计 ¥{total_amount:.2f}：\n"]
    for inv in invoices:
        inv_id = inv.get("id")
        date = inv.get("invoice_date") or ""
        seller = inv.get("seller_name") or ""
        buyer = inv.get("buyer_name") or ""
        amount = inv.get("amount_with_tax") or 0
        status = "❌" if inv.get("excluded") else "✅"
        lines.append(f"  {status} #{inv_id} | {date} | {seller} | {buyer} | ¥{amount:.2f}")

    return "\n".join(lines)


def cmd_query(config: dict, date_from: str = None, date_to: str = None,
              seller: str = None, buyer: str = None,
              project: str = None, person: str = None) -> str:
    """查询发票"""
    from invoice_clipper.database import query_invoices

    filters = {
        "date_from": date_from,
        "date_to": date_to,
        "seller": seller,
        "buyer": buyer,
        "project": project,
        "person": person,
    }
    invoices = query_invoices(filters)

    if not invoices:
        return "没有找到符合条件的发票"

    total_amount = sum(i.get("amount_with_tax") or 0 for i in invoices)
    lines = [f"共 {len(invoices)} 张发票，合计 ¥{total_amount:.2f}：\n"]
    for inv in invoices:
        inv_id = inv.get("id")
        date = inv.get("invoice_date") or ""
        seller_name = inv.get("seller_name") or ""
        buyer_name = inv.get("buyer_name") or ""
        amount = inv.get("amount_with_tax") or 0
        status = "❌" if inv.get("excluded") else "✅"
        lines.append(f"  {status} #{inv_id} | {date} | {seller_name} | {buyer_name} | ¥{amount:.2f}")

    return "\n".join(lines)


def cmd_export(config: dict, date_from: str = None, date_to: str = None,
               seller: str = None, buyer: str = None,
               project: str = None, person: str = None,
               exclude_ids: list = None, fmt: str = "both") -> str:
    """导出发票"""
    from invoice_clipper.database import query_invoices
    from invoice_clipper.exporter import (
        export_excel, export_merged_pdf, build_export_label
    )

    filters = {
        "date_from": date_from,
        "date_to": date_to,
        "seller": seller,
        "buyer": buyer,
        "project": project,
        "person": person,
        "exclude_ids": exclude_ids,
    }
    invoices = query_invoices(filters)

    if not invoices:
        return "没有找到符合条件的发票"

    export_dir = Path.home() / "Documents" / "发票夹子" / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    label = build_export_label(filters)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    results = []
    total_amount = sum(i.get("amount_with_tax") or 0 for i in invoices)

    if fmt in ["excel", "both"]:
        excel_path = export_dir / f"报销明细_{label}_{timestamp}.xlsx"
        export_excel(invoices, excel_path)
        results.append(f"📊 Excel: {excel_path}")

    if fmt in ["pdf", "both"]:
        pdf_path = export_dir / f"报销发票_{label}_{timestamp}.pdf"
        result = export_merged_pdf(invoices, pdf_path)
        if result:
            results.append(f"📄 合并PDF: {pdf_path}")

    summary = f"✅ 导出完成！共 {len(invoices)} 张发票，合计 ¥{total_amount:.2f}\n"
    summary += "\n".join(results)
    return summary


def cmd_exclude(config: dict, inv_id: int) -> str:
    """标记发票为不报销"""
    from invoice_clipper.database import update_invoice_status

    update_invoice_status(inv_id, excluded=True)
    return f"✅ 发票 #{inv_id} 已标记为不报销"


def cmd_include(config: dict, inv_id: int) -> str:
    """恢复发票为可报销"""
    from invoice_clipper.database import update_invoice_status

    update_invoice_status(inv_id, excluded=False)
    return f"✅ 发票 #{inv_id} 已恢复为可报销"


# ── 进程锁 ────────────────────────────────────────


def acquire_lock(root: str) -> bool:
    """获取进程锁（invoice.lock），防止多实例冲突。

    返回 True 表示成功获取锁，False 表示已有实例在运行。
    """
    lock_file = Path(root) / "invoice.lock"
    import socket, json
    hostname = socket.gethostname()
    pid = os.getpid()
    lock_data = json.dumps({"pid": pid, "host": hostname})

    try:
        # 以独占方式创建锁文件（原子操作）
        fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        os.write(fd, lock_data.encode())
        os.close(fd)
        return True
    except FileExistsError:
        # 锁文件已存在，检查是否 valid
        try:
            with open(lock_file) as f:
                old = json.load(f)
            print(f"  ⚠ 已有实例在运行 (PID {old['pid']} @ {old['host']})")
        except (json.JSONDecodeError, OSError):
            print(f"  ⚠ 锁文件已存在 (可能来自异常退出)")
        return False


def release_lock(root: str):
    """释放进程锁"""
    lock_file = Path(root) / "invoice.lock"
    try:
        lock_file.unlink()
    except OSError:
        pass


# ── 安装引导 ──────────────────────────────────────


def cmd_init() -> str:
    """交互式安装引导"""
    from invoice_clipper import get_invoice_root, DEFAULT_CONFIG, deep_merge

    print("=" * 52)
    print("  发票夹子 — 交互式安装引导")
    print("=" * 52)
    print()

    # ── 1. 安装目录 ────────────────────────────────
    current_root = get_invoice_root()
    hint = f"（当前: {current_root}）"
    print(f"📁 INVOICE_ROOT {hint}")
    reply = input(f"   回车接受，或输入新路径: ").strip()
    root = os.path.realpath(reply) if reply else current_root
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    print(f"  ✓ 根目录: {root}")
    print()

    # ── 2. 检查是否已安装 ──────────────────────────
    marker = root_path / ".invoice-install"
    if marker.exists():
        print("  ⚠ 此目录已安装发票夹子（发现 .invoice-install）")
        import shutil
        overwrite = input("   覆盖配置? (y/N): ").strip().lower()
        if overwrite != "y":
            print("  保留现有配置。")
            print()
            print("  💡 设置环境变量使用:")
            print(f"     export INVOICE_ROOT={root}")
            print("     invoice list")
            return "已跳过安装"
    print()

    # ── 3. 创建目录结构 ────────────────────────────
    (root_path / "config").mkdir(exist_ok=True)
    (root_path / "data").mkdir(exist_ok=True)
    (root_path / "data" / "inbox").mkdir(exist_ok=True)

    # 安装标记
    marker.write_text(f"# invoice-manager 安装标记\n# 创建时间: {datetime.now().isoformat()}\n")
    print(f"  ✓ 目录结构已创建: {root}")
    print()

    # ── 4. 数据库选择 ──────────────────────────────
    print("数据库类型:")
    print("  1) SQLite（默认，无需额外配置）")
    print("  2) PostgreSQL（需要已运行的数据库服务）")
    db_choice = input("请选择 [1]: ").strip() or "1"
    print()

    # ── 5. 生成配置 ────────────────────────────────
    cfg_file = root_path / "config" / "config.yaml"
    db_path = root_path / "data" / "invoices.db"

    user_cfg = {
        "storage": {
            "base_dir": root,
            "db_type": "postgresql" if db_choice == "2" else "sqlite",
            "db_path": str(db_path),
        },
        "watch_dirs": [str(root_path / "data" / "inbox")],
    }

    if db_choice == "2":
        print("--- PostgreSQL 配置 ---")
        user_cfg["storage"]["pg_host"] = input(f"  主机 [localhost]: ").strip() or "localhost"
        user_cfg["storage"]["pg_port"] = int(input(f"  端口 [5432]: ").strip() or "5432")
        user_cfg["storage"]["pg_database"] = input(f"  数据库名 [invoice_manager]: ").strip() or "invoice_manager"
        user_cfg["storage"]["pg_user"] = input(f"  用户名 [postgres]: ").strip() or "postgres"
        user_cfg["storage"]["pg_password"] = input(f"  密码: ").strip()
        print()

    # 合并默认值后写入
    merged = deep_merge(DEFAULT_CONFIG, user_cfg)
    cfg_file.write_text(yaml.dump(merged, allow_unicode=True, default_flow_style=False), encoding="utf-8")
    print(f"  ✓ 配置文件: {cfg_file}")
    print()

    # ── 6. 初始化数据库 ────────────────────────────
    print("初始化数据库 ...")
    init_db({"storage": {"db_type": merged["storage"]["db_type"],
                          "db_path": merged["storage"]["db_path"]}})
    print("  ✓ 数据库初始化完成")
    print()

    # ── 7. 创建快捷命令 ────────────────────────────
    print("创建快捷命令 ...")
    import os as os_mod
    if os_mod.name == "nt":
        scripts_dir = Path.home() / "AppData" / "Local" / "Programs" / "Python" / "Scripts"
        if not scripts_dir.exists():
            scripts_dir = Path.home() / ".local" / "bin"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        bat_path = scripts_dir / "invoice.bat"
        bat_path.write_text(
            f"""@echo off
set INVOICE_ROOT={root}
python -m invoice_clipper %*
""", encoding="utf-8")
        print(f"  ✓ {bat_path}")
    else:
        bin_dir = Path.home() / ".local" / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        script_path = bin_dir / "invoice"
        script_path.write_text(f"""#!/usr/bin/env bash
export INVOICE_ROOT={root}
exec python -m invoice_clipper "$@"
""", encoding="utf-8")
        script_path.chmod(0o755)
        print(f"  ✓ {script_path}")

    print()
    print("=" * 52)
    print("  ✅ 安装完成！")
    print("=" * 52)
    print()
    print(f"  INVOICE_ROOT={root}")
    print(f"  配置文件: {cfg_file}")
    print()
    print("  使用方式:")
    print("    export INVOICE_ROOT={root}")
    print("    invoice scan           扫描发票")
    print("    invoice list           列出发票")
    print("    invoice web            启动 Web UI")
    print()

    return "安装引导完成"


def cmd_process(config: dict, file_path: str) -> str:
    """处理单个文件"""
    from invoice_clipper.processor import InvoiceProcessor

    proc = InvoiceProcessor(config)
    result = proc.process_file(Path(file_path))

    if result:
        return f"✅ 处理成功：{result.get('seller_name')} | ¥{result.get('amount_with_tax', 0):.2f}"
    else:
        return f"❌ 处理失败（可能是重复发票或识别错误）"


def main():
    parser = argparse.ArgumentParser(description="发票夹子 - 自动整理发票")
    subparsers = parser.add_subparsers(dest="command", help="命令")

    # scan
    subparsers.add_parser("scan", help="扫描监控目录")

    # list
    subparsers.add_parser("list", help="列出所有发票")

    # process
    process_parser = subparsers.add_parser("process", help="处理单个文件")
    process_parser.add_argument("file", help="文件路径")

    # query
    query_parser = subparsers.add_parser("query", help="查询发票")
    query_parser.add_argument("--from", dest="date_from", help="开始日期 YYYY-MM-DD")
    query_parser.add_argument("--to", dest="date_to", help="结束日期 YYYY-MM-DD")
    query_parser.add_argument("--seller", help="销售方名称")
    query_parser.add_argument("--buyer", help="购买方名称")
    query_parser.add_argument("--project", help="归属项目")
    query_parser.add_argument("--person", help="归属人")

    # exclude
    exclude_parser = subparsers.add_parser("exclude", help="标记不报销")
    exclude_parser.add_argument("id", type=int, help="发票ID")

    # init
    subparsers.add_parser("init", help="交互式安装引导")

    # include
    include_parser = subparsers.add_parser("include", help="恢复报销")
    include_parser.add_argument("id", type=int, help="发票ID")

    # export
    export_parser = subparsers.add_parser("export", help="导出报销")
    export_parser.add_argument("--from", dest="date_from", help="开始日期 YYYY-MM-DD")
    export_parser.add_argument("--to", dest="date_to", help="结束日期 YYYY-MM-DD")
    export_parser.add_argument("--seller", help="销售方名称")
    export_parser.add_argument("--buyer", help="购买方名称")
    export_parser.add_argument("--project", help="归属项目")
    export_parser.add_argument("--person", help="归属人")
    export_parser.add_argument("--exclude-ids", help="排除的发票ID，逗号分隔")
    export_parser.add_argument("--format", dest="fmt", default="both",
                               choices=["excel", "pdf", "both"],
                               help="导出格式")

    args = parser.parse_args()

    if args.command == "init":
        print(cmd_init())
        return

    config, cfg_path = load_config()
    logger.info(f"配置文件: {cfg_path}")
    init_db(config)

    if args.command == "scan":
        print(cmd_scan(config))
    elif args.command == "list":
        print(cmd_list(config))
    elif args.command == "process":
        print(cmd_process(config, args.file))
    elif args.command == "query":
        print(cmd_query(config, args.date_from, args.date_to,
                        args.seller, args.buyer, args.project, args.person))
    elif args.command == "exclude":
        print(cmd_exclude(config, args.id))
    elif args.command == "include":
        print(cmd_include(config, args.id))
    elif args.command == "export":
        exclude_ids = None
        if args.exclude_ids:
            exclude_ids = [int(x.strip()) for x in args.exclude_ids.split(",")]
        print(cmd_export(config, args.date_from, args.date_to,
                         args.seller, args.buyer, args.project, args.person,
                         exclude_ids, args.fmt))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
