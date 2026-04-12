"""
发票数据库模块 - SQLite 存储（重构版 v2.0）
移除风控、验真相关字段，新增归属、税号、备注等字段
"""
import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


def get_conn(db_path: str) -> sqlite3.Connection:
    """获取数据库连接，设置 row_factory"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str):
    """初始化数据库表（新版结构）"""
    with get_conn(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT,
                invoice_code TEXT,
                invoice_date TEXT,
                commodity_name TEXT,
                specification_model TEXT,
                buyer_name TEXT,
                buyer_tax_num TEXT,
                seller_name TEXT,
                seller_tax_num TEXT,
                tax_rate REAL,
                tax_amount REAL,
                amount_with_tax REAL,
                category TEXT,
                belong_project TEXT,
                belong_person TEXT,
                remark TEXT,
                source TEXT,
                original_filename TEXT,
                stored_path TEXT,
                excluded INTEGER DEFAULT 0,
                created_at TEXT,
                raw_text TEXT,
                raw_json TEXT
            )
        """)
        # 创建常用索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_invoice_number ON invoices(invoice_number)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_invoice_date ON invoices(invoice_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_seller_name ON invoices(seller_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_buyer_name ON invoices(buyer_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_belong_project ON invoices(belong_project)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_belong_person ON invoices(belong_person)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_excluded ON invoices(excluded)")
        conn.commit()
    logger.info(f"数据库初始化完成: {db_path}")


def insert_invoice(db_path: str, data: dict) -> int:
    """插入发票记录，返回自增ID"""
    cols = [
        "invoice_number", "invoice_code", "invoice_date",
        "commodity_name", "specification_model",
        "buyer_name", "buyer_tax_num",
        "seller_name", "seller_tax_num",
        "tax_rate", "tax_amount", "amount_with_tax",
        "category",
        "belong_project", "belong_person", "remark",
        "source", "original_filename", "stored_path",
        "created_at", "raw_text", "raw_json"
    ]
    placeholders = ",".join(":" + c for c in cols)
    with get_conn(db_path) as conn:
        cur = conn.execute(
            f"INSERT INTO invoices ({','.join(cols)}) VALUES ({placeholders})",
            {k: v for k, v in data.items() if k in cols}
        )
        conn.commit()
        return cur.lastrowid


def is_duplicate(db_path: str, invoice_number: str, amount_with_tax: float) -> bool:
    """检查发票号+金额是否已存在（重复报销）"""
    if not invoice_number:
        return False
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM invoices WHERE invoice_number=? AND amount_with_tax=?",
            (invoice_number, amount_with_tax)
        ).fetchone()
    return row is not None


def exists_by_invoice_number(db_path: str, invoice_number: str) -> bool:
    """检查发票号码是否已入库（防止同一发票多次识别）"""
    if not invoice_number:
        return False
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT id FROM invoices WHERE invoice_number=? LIMIT 1",
            (invoice_number,)
        ).fetchone()
    return row is not None


def query_invoices(db_path: str, filters: dict) -> List[dict]:
    """
    查询发票列表
    filters 支持：
        date_from, date_to: 开票日期范围 (invoice_date)
        seller: 销售方名称模糊匹配 (seller_name)
        buyer: 购买方名称模糊匹配 (buyer_name)
        project: 归属项目精确匹配 (belong_project)
        person: 归属人精确匹配 (belong_person)
        exclude_ids: 排除的ID列表
        only_included: 只返回未排除的发票（默认True）
    """
    sql = "SELECT * FROM invoices WHERE 1=1"
    params = []

    if filters.get("date_from"):
        sql += " AND invoice_date >= ?"
        params.append(filters["date_from"])
    if filters.get("date_to"):
        sql += " AND invoice_date <= ?"
        params.append(filters["date_to"])
    if filters.get("seller"):
        sql += " AND seller_name LIKE ?"
        params.append(f"%{filters['seller']}%")
    if filters.get("buyer"):
        sql += " AND buyer_name LIKE ?"
        params.append(f"%{filters['buyer']}%")
    if filters.get("project"):
        sql += " AND belong_project = ?"
        params.append(filters["project"])
    if filters.get("person"):
        sql += " AND belong_person = ?"
        params.append(filters["person"])
    if filters.get("only_included", True):
        sql += " AND excluded = 0"
    if filters.get("exclude_ids"):
        placeholders = ",".join("?" * len(filters["exclude_ids"]))
        sql += f" AND id NOT IN ({placeholders})"
        params.extend(filters["exclude_ids"])

    sql += " ORDER BY invoice_date ASC, id ASC"

    with get_conn(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def update_invoice_status(db_path: str, inv_id: int, excluded: bool = True):
    """标记发票为排除/恢复"""
    with get_conn(db_path) as conn:
        conn.execute(
            "UPDATE invoices SET excluded=? WHERE id=?",
            (1 if excluded else 0, inv_id)
        )
        conn.commit()


def update_invoice(db_path: str, inv_id: int, updates: dict):
    """更新发票任意字段"""
    if not updates:
        return
    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [inv_id]
    sql = f"UPDATE invoices SET {set_clause} WHERE id = ?"
    with get_conn(db_path) as conn:
        conn.execute(sql, values)
        conn.commit()


def get_invoice_by_id(db_path: str, invoice_id: int) -> Optional[dict]:
    """根据ID获取单张发票"""
    with get_conn(db_path) as conn:
        row = conn.execute("SELECT * FROM invoices WHERE id=?", (invoice_id,)).fetchone()
    return dict(row) if row else None


def get_all_invoices(db_path: str) -> List[dict]:
    """获取所有发票（按日期升序）"""
    with get_conn(db_path) as conn:
        rows = conn.execute("SELECT * FROM invoices ORDER BY invoice_date ASC").fetchall()
    return [dict(r) for r in rows]


def get_distinct_projects(db_path: str) -> List[str]:
    """获取所有不重复的归属项目（用于下拉筛选）"""
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT belong_project FROM invoices WHERE belong_project != '' ORDER BY belong_project"
        ).fetchall()
    return [r[0] for r in rows if r[0]]


def get_distinct_persons(db_path: str) -> List[str]:
    """获取所有不重复的归属人（用于下拉筛选）"""
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT belong_person FROM invoices WHERE belong_person != '' ORDER BY belong_person"
        ).fetchall()
    return [r[0] for r in rows if r[0]]


def exclude_invoice(db_path: str, invoice_id: int, excluded: bool = True):
    """标记发票为排除/恢复（别名，兼容旧调用）"""
    update_invoice_status(db_path, invoice_id, excluded)