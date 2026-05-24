"""
文件处理工具模块 - 重构版 v2.0
包含：PDF文本提取、OFD转PDF、归档路径构建、文件归档
"""
import re
import shutil
import logging
import tempfile
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: Path) -> str:
    """
    从 PDF 文件提取文本内容（用于快速预检）
    使用 PyMuPDF (fitz) 提取
    """
    try:
        import fitz

        text = ""
        with fitz.open(str(pdf_path)) as doc:
            for page in doc:
                text += page.get_text()

        return text.strip()

    except ImportError:
        raise RuntimeError(
            "PyMuPDF (fitz) 未安装，无法提取 PDF 文本。请运行: pip install PyMuPDF"
        )
    except Exception as e:
        logger.warning(f"PDF 文本提取失败: {pdf_path.name} - {e}")
        return ""


def ofd_to_pdf(ofd_path: Path, output_dir: Optional[Path] = None) -> Path:
    """
    将 OFD 文件转换为 PDF

    优先使用 easyofd Python 库，失败则尝试系统工具 ofd2pdf。

    Args:
        ofd_path: OFD 文件路径
        output_dir: 输出目录（默认为 OFD 所在目录）

    Returns:
        生成的 PDF 文件路径
    """
    if output_dir is None:
        output_dir = ofd_path.parent

    output_path = output_dir / f"{ofd_path.stem}.pdf"
    errors = []

    # 方法1: 使用 easyofd Python 库
    # easyofd 不支持非 ASCII 路径（如中文文件名），需先复制到临时目录
    tmp_dir = None
    try:
        from easyofd import OFD

        tmp_dir = tempfile.mkdtemp(prefix="ofd_conv_")
        tmp_src = Path(tmp_dir) / "input.ofd"
        tmp_out = Path(tmp_dir) / "output.pdf"
        shutil.copy2(str(ofd_path), str(tmp_src))

        ofd = OFD()
        ofd.read(str(tmp_src))
        ofd.to_pdf(str(tmp_out))

        if tmp_out.exists():
            shutil.copy2(str(tmp_out), str(output_path))
            logger.info(f"OFD 转 PDF 成功 (easyofd): {ofd_path.name}")
            return output_path

    except ImportError:
        errors.append("easyofd 未安装，请运行: pip install easyofd")
    except Exception as e:
        errors.append(f"easyofd: {e}")
    finally:
        if tmp_dir and Path(tmp_dir).exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # 方法2: 使用系统工具 ofd2pdf
    try:
        import subprocess

        result = subprocess.run(
            ["ofd2pdf", str(ofd_path), str(output_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and output_path.exists():
            logger.info(f"OFD 转 PDF 成功 (ofd2pdf): {ofd_path.name}")
            return output_path
    except FileNotFoundError:
        errors.append("ofd2pdf 系统工具未安装")
    except Exception as e:
        errors.append(f"ofd2pdf: {e}")

    # 所有方法失败
    raise RuntimeError(
        f"OFD 转换 PDF 失败。已尝试方法: {'; '.join(errors)}。"
        f"请安装 easyofd (pip install easyofd) 或 ofd2pdf 系统工具。"
    )


def build_attachment_dir(base_dir: Path, invoice_id: int) -> Path:
    """
    构建附件存储目录路径，确保目录存在

    路径格式: {base_dir}/attachments/{invoice_id}/
    """
    att_dir = base_dir / "attachments" / str(invoice_id)
    att_dir.mkdir(parents=True, exist_ok=True)
    return att_dir


def make_safe_filename(text: str, max_len: int = 50) -> str:
    """将任意文本转换为安全的文件名"""
    # 移除非法字符，保留中文、字母、数字、空格、横线
    text = re.sub(r'[^\w\u4e00-\u9fff\s-]', '', text)
    # 替换空格为下划线
    text = text.replace(' ', '_')
    # 截断长度
    return text[:max_len]


def build_archive_path(base_dir: Path, invoice: Dict) -> Path:
    """
    根据发票字段构建归档路径

    路径格式: {base_dir}/{year}/{date}_{amount}_{seller}_{inv_no}.pdf
    """
    date = invoice.get("invoice_date") or "0000-00-00"
    year = date[:4] if len(date) >= 4 else "0000"

    # 金额
    amount_raw = invoice.get("amount_with_tax") or 0
    try:
        amount = float(amount_raw)
    except (ValueError, TypeError):
        amount = 0.0

    seller = make_safe_filename(invoice.get("seller_name") or "未知销售方")
    inv_no = invoice.get("invoice_number") or ""

    # 取发票号后6位避免文件名过长
    inv_no_short = inv_no[-6:] if len(inv_no) >= 6 else inv_no

    filename = f"{date}_{amount:.2f}_{seller}_{inv_no_short}.pdf"
    return base_dir / year / filename


def archive_invoice(src_path: Path, dest_path: Path, move: bool = True) -> Path:
    """
    将发票文件归档到目标路径

    Args:
        src_path: 源文件路径
        dest_path: 目标文件路径
        move: True 为移动，False 为复制

    Returns:
        实际归档后的文件路径（可能因重名而添加了序号）
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # 如果目标已存在，加序号
    if dest_path.exists():
        stem = dest_path.stem
        suffix = dest_path.suffix
        for i in range(1, 100):
            new_dest = dest_path.parent / f"{stem}_{i:02d}{suffix}"
            if not new_dest.exists():
                dest_path = new_dest
                break

    if move:
        shutil.move(str(src_path), str(dest_path))
    else:
        shutil.copy2(str(src_path), str(dest_path))

    return dest_path