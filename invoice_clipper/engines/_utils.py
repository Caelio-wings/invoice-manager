"""
识别引擎共享工具函数
"""

import re
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def pdf_to_image(pdf_path: str, dpi: int = 200) -> Optional[bytes]:
    """将 PDF 第一页转为 PNG 图片"""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        page = doc[0]
        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("png")
        doc.close()
        return img_bytes
    except Exception as e:
        logger.error(f"PDF 转图片失败: {e}")
        return None


def normalize_date(date_str: str) -> str:
    """标准化日期格式为 YYYY-MM-DD"""
    if not date_str:
        return ""

    # 去除所有空格
    date_str = re.sub(r'\s+', '', date_str)

    # 处理 "2016年06月02日" 格式
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_str)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # 处理 "2016-06-02" 格式
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", date_str)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # 处理 "2016/06/02" 格式
    m = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})", date_str)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    return date_str


def parse_number(val) -> Optional[float]:
    """解析数字，处理千分位逗号、货币符号、百分号"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = re.sub(r"[¥￥$,%]", "", val.strip())
        try:
            num = float(cleaned)
            # 如果原值包含 %，且大于1，转换为小数（如 6% → 0.06）
            if "%" in val and num > 1:
                num = num / 100
            return num
        except ValueError:
            return None
    return None


def infer_category(text: str) -> str:
    """根据文本关键词推断发票分类"""
    text_lower = text.lower()

    if any(k in text_lower for k in ["餐饮", "餐厅", "饭店", "食堂"]):
        return "餐饮"
    elif any(k in text_lower for k in ["交通", "运输", "通行", "机票", "火车", "滴滴"]):
        return "交通"
    elif any(k in text_lower for k in ["住宿", "酒店", "宾馆", "旅馆"]):
        return "住宿"
    elif any(k in text_lower for k in ["办公", "文具", "打印", "复印", "耗材"]):
        return "办公"
    elif any(k in text_lower for k in ["服务", "咨询", "代理", "顾问", "设计"]):
        return "服务"
    elif any(k in text_lower for k in ["通讯", "通信", "电话", "宽带"]):
        return "通讯"
    else:
        return "其他"


def calculate_confidence(fields: Dict[str, Any]) -> float:
    """计算置信度，基于关键字段是否齐全"""

    def _has_value(val) -> bool:
        if val is None:
            return False
        if isinstance(val, str) and not val.strip():
            return False
        return True

    required = ["invoice_number", "amount_with_tax", "invoice_date", "seller_name"]
    present = sum(1 for f in required if _has_value(fields.get(f)))
    base = present / len(required)

    bonus = 0.0
    if _has_value(fields.get("buyer_tax_num")):
        bonus += 0.05
    if _has_value(fields.get("seller_tax_num")):
        bonus += 0.05
    if _has_value(fields.get("commodity_name")):
        bonus += 0.05
    if fields.get("tax_rate") is not None:
        bonus += 0.05

    return min(1.0, base + bonus)
