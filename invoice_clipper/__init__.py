"""
发票夹子核心模块 - 重构版 v2.0
提供发票处理、数据库操作、导出功能的统一入口
"""
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
    exclude_invoice,
    is_duplicate,
    exists_by_invoice_number,
)
from .exporter import export_excel, export_merged_pdf, build_export_label
from .file_utils import ofd_to_pdf, build_archive_path, archive_invoice

__all__ = [
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
    "exclude_invoice",
    "is_duplicate",
    "exists_by_invoice_number",
    # 导出
    "export_excel",
    "export_merged_pdf",
    "build_export_label",
    # 文件工具
    "ofd_to_pdf",
    "extract_text_from_pdf",
    "build_archive_path",
    "archive_invoice",
]