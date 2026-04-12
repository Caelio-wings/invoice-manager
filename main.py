#!/usr/bin/env python3
"""
发票夹子 - 主入口 CLI（重构版 v2.0）
支持 scan, list, query, export, exclude, include 命令
"""
import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    cfg_path = Path(__file__).parent / "config" / "config.yaml"
    if not cfg_path.exists():
        logger.error(f"配置文件不存在: {cfg_path}")
        sys.exit(1)
    # ✅ 指定 encoding='utf-8'
    with open(cfg_path, encoding='utf-8') as f:
        return yaml.safe_load(f)

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

    invoices = query_invoices(
        str(Path(config["storage"]["db_path"]).expanduser()),
        {"only_included": False}
    )

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
    invoices = query_invoices(
        str(Path(config["storage"]["db_path"]).expanduser()), filters
    )

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
    invoices = query_invoices(
        str(Path(config["storage"]["db_path"]).expanduser()), filters
    )

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

    update_invoice_status(
        str(Path(config["storage"]["db_path"]).expanduser()),
        inv_id,
        excluded=True,
    )
    return f"✅ 发票 #{inv_id} 已标记为不报销"


def cmd_include(config: dict, inv_id: int) -> str:
    """恢复发票为可报销"""
    from invoice_clipper.database import update_invoice_status

    update_invoice_status(
        str(Path(config["storage"]["db_path"]).expanduser()),
        inv_id,
        excluded=False,
    )
    return f"✅ 发票 #{inv_id} 已恢复为可报销"


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
    config = load_config()

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