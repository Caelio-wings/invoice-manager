"""
发票夹子核心模块 - v3.0
提供发票处理、数据库操作、导出功能的统一入口
"""
import sys
import yaml
from pathlib import Path

from .processor import InvoiceProcessor
from .database import (
    init_db,
    insert_invoice,
    query_invoices,
    update_invoice_status,
    update_invoice,
    get_invoice_by_id,
    get_all_invoices,
    get_distinct_projects,
    get_distinct_persons,
    is_duplicate,
    exists_by_invoice_number,
    get_attachments,
    insert_attachment,
    delete_attachment,
    delete_attachments_by_invoice,
    delete_invoice,
)
from .exporter import export_excel, export_merged_pdf, build_export_label
from .file_utils import (
    ofd_to_pdf, extract_text_from_pdf,
    build_archive_path, archive_invoice,
    build_attachment_path, next_attachment_seq,
)


def load_config() -> dict:
    """从 config/config.yaml 加载配置（相对于项目根目录）"""
    cfg = Path(__file__).resolve().parent.parent / "config" / "config.yaml"
    if not cfg.exists():
        raise FileNotFoundError(f"配置文件不存在: {cfg}")
    with open(cfg, encoding="utf-8") as f:
        return yaml.safe_load(f)


__all__ = [
    # 配置
    "load_config",
    # 处理器
    "InvoiceProcessor",
    # 数据库核心函数
    "init_db",
    "insert_invoice",
    "query_invoices",
    "update_invoice_status",
    "update_invoice",
    "get_invoice_by_id",
    "get_all_invoices",
    "get_distinct_projects",
    "get_distinct_persons",
    "is_duplicate",
    "exists_by_invoice_number",
    # 附件
    "get_attachments",
    "insert_attachment",
    "delete_attachment",
    "delete_attachments_by_invoice",
    "delete_invoice",
    # 导出
    "export_excel",
    "export_merged_pdf",
    "build_export_label",
    # 文件工具
    "ofd_to_pdf",
    "extract_text_from_pdf",
    "build_archive_path",
    "archive_invoice",
    "build_attachment_path",
    "next_attachment_seq",
]