"""
第1级引擎：百度增值税发票识别 API
使用百度智能云 OCR 服务进行发票结构化识别
"""
import base64
import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import httpx

from .base import BaseEngine, EngineResult
from ._utils import pdf_to_image, normalize_date, parse_number, infer_category, calculate_confidence

logger = logging.getLogger(__name__)

# 百度 OCR API 端点
TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
VAT_INVOICE_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/vat_invoice"

# Access Token 缓存（全局，避免频繁请求）
_token_cache: Dict[str, Tuple[str, float]] = {}


class BaiduOCREngine(BaseEngine):
    """
    百度增值税发票识别引擎
    支持 PDF、OFD（已转PDF）、图片格式
    """

    name = "baidu_ocr"
    priority = 1  # 第一优先级

    def __init__(self, config: dict):
        self.cfg = config
        ocr_cfg = config.get("ocr", {})
        baidu_cfg = ocr_cfg.get("baidu", {})
        self.enabled = baidu_cfg.get("enabled", True)
        self.api_key = baidu_cfg.get("api_key", "")
        self.secret_key = baidu_cfg.get("secret_key", "")

        if not self.api_key or not self.secret_key:
            logger.warning("百度 OCR 未配置 API Key/Secret Key，引擎不可用")

    def is_available(self) -> bool:
        if not self.enabled:
            logger.debug("百度 OCR 引擎已禁用")
            return False
        return bool(self.api_key and self.secret_key)

    def extract(self, file_path: str) -> EngineResult:
        """对文件执行发票识别"""
        path = Path(file_path)
        suffix = path.suffix.lower()

        # 获取 access_token
        access_token = self._get_access_token()
        if not access_token:
            return EngineResult(
                data=None,
                confidence=0,
                engine=self.name,
                error="获取百度 access_token 失败",
            )

        # 根据文件类型准备请求
        if suffix == ".pdf":
            return self._process_pdf(file_path, access_token)
        elif suffix in (".png", ".jpg", ".jpeg", ".bmp"):
            return self._process_image(file_path, access_token)
        else:
            return EngineResult(
                data=None,
                confidence=0,
                engine=self.name,
                error=f"不支持的文件类型: {suffix}",
            )

    def _get_access_token(self) -> Optional[str]:
        """获取百度 API access_token（带缓存）"""
        cache_key = f"{self.api_key}:{self.secret_key}"

        # 检查缓存（有效期 30 天，这里缓存 29 天以确保安全）
        if cache_key in _token_cache:
            token, expires_at = _token_cache[cache_key]
            if time.time() < expires_at:
                logger.debug("使用缓存的 access_token")
                return token

        # 请求新 token
        try:
            params = {
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret_key,
            }
            resp = httpx.post(TOKEN_URL, params=params, timeout=10)
            if resp.status_code != 200:
                logger.error(f"获取 access_token 失败: HTTP {resp.status_code}")
                return None

            data = resp.json()
            access_token = data.get("access_token")
            if not access_token:
                logger.error(f"响应中无 access_token: {data}")
                return None

            # 缓存 token，有效期 29 天
            expires_in = data.get("expires_in", 2592000)  # 默认 30 天
            expires_at = time.time() + expires_in - 86400  # 提前 1 天过期
            _token_cache[cache_key] = (access_token, expires_at)

            logger.info("获取百度 access_token 成功")
            return access_token

        except Exception as e:
            logger.error(f"获取 access_token 异常: {e}")
            return None

    def _process_pdf(self, pdf_path: str, access_token: str) -> EngineResult:
        """处理 PDF 文件（转图片后调用 API）"""
        try:
            # 将 PDF 第一页转为 PNG 图片
            img_bytes = pdf_to_image(pdf_path, dpi=300)
            if not img_bytes:
                return EngineResult(
                    data=None,
                    confidence=0,
                    engine=self.name,
                    error="PDF 转图片失败",
                )
            return self._call_api(img_bytes, access_token)

        except Exception as e:
            return EngineResult(
                data=None,
                confidence=0,
                engine=self.name,
                error=f"PDF 处理异常: {e}",
            )

    def _process_image(self, img_path: str, access_token: str) -> EngineResult:
        """处理图片文件"""
        try:
            img_bytes = Path(img_path).read_bytes()
            return self._call_api(img_bytes, access_token)
        except Exception as e:
            return EngineResult(
                data=None,
                confidence=0,
                engine=self.name,
                error=f"图片读取异常: {e}",
            )

    def _call_api(self, image_bytes: bytes, access_token: str) -> EngineResult:
        """调用百度增值税发票识别 API"""
        try:
            # Base64 编码
            b64_image = base64.b64encode(image_bytes).decode("utf-8")

            # 构造请求
            url = f"{VAT_INVOICE_URL}?access_token={access_token}"
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            data = {"image": b64_image}

            resp = httpx.post(url, headers=headers, data=data, timeout=60)
            if resp.status_code != 200:
                return EngineResult(
                    data=None,
                    confidence=0,
                    engine=self.name,
                    error=f"百度 API 返回 HTTP {resp.status_code}",
                )

            result = resp.json()

            # 检查错误
            if "error_code" in result:
                error_msg = result.get("error_msg", "未知错误")
                return EngineResult(
                    data=None,
                    confidence=0,
                    engine=self.name,
                    error=f"百度 API 错误: {error_msg}",
                )

            # 解析识别结果
            words_result = result.get("words_result", {})
            if not words_result:
                return EngineResult(
                    data=None,
                    confidence=0,
                    engine=self.name,
                    error="未识别到任何内容",
                )

            # 映射到我们的字段结构
            fields = self._map_fields(words_result)
            raw_json = json.dumps(result, ensure_ascii=False)

            # 计算置信度（基于关键字段是否齐全）
            confidence = calculate_confidence(fields)

            return EngineResult(
                data=fields,
                confidence=confidence,
                engine=self.name,
                raw_text="",  # 百度 API 不返回原始文本
                raw_json=raw_json,
            )

        except Exception as e:
            return EngineResult(
                data=None,
                confidence=0,
                engine=self.name,
                error=f"API 调用异常: {e}",
            )

    def _map_fields(self, wr: Dict[str, Any]) -> Dict[str, Any]:
        """
        将百度 API 返回的 words_result 映射到我们的数据库字段
        """
        # 辅助函数：从数组中提取第一项的 word
        def _first_word(arr, default=""):
            if isinstance(arr, list) and len(arr) > 0:
                item = arr[0]
                if isinstance(item, dict):
                    return item.get("word", default)
            return default

        # 辅助函数：从数组中提取第一项，并转为浮点数
        def _first_float(arr, default=None):
            word = _first_word(arr, "")
            if word:
                try:
                    return float(word.replace(",", "").replace("%", ""))
                except ValueError:
                    pass
            return default

        # 辅助函数：提取税率（处理百分号）
        def _parse_tax_rate(arr):
            word = _first_word(arr, "")
            if word:
                # 移除 % 并转为小数
                word = word.replace("%", "")
                try:
                    rate = float(word)
                    # 如果是整数（如 6），转为小数 0.06
                    if rate > 1:
                        rate = rate / 100
                    return rate
                except ValueError:
                    pass
            return None

        # 发票分类判断
        service_type = wr.get("ServiceType", "")
        invoice_type = wr.get("InvoiceType", "")
        category = infer_category(f"{service_type} {invoice_type}")

        fields = {
            # 发票基础信息
            "invoice_number": wr.get("InvoiceNum", ""),
            "invoice_code": wr.get("InvoiceCode", ""),
            "invoice_date": normalize_date(wr.get("InvoiceDate", "")),

            # 商品信息（取第一项）
            "commodity_name": _first_word(wr.get("CommodityName", [])),
            "specification_model": _first_word(wr.get("CommodityType", [])),

            # 购买方
            "buyer_name": wr.get("PurchaserName", ""),
            "buyer_tax_num": wr.get("PurchaserRegisterNum", ""),

            # 销售方
            "seller_name": wr.get("SellerName", ""),
            "seller_tax_num": wr.get("SellerRegisterNum", ""),

            # 金额与税率
            "tax_rate": _parse_tax_rate(wr.get("CommodityTaxRate", [])),
            "tax_amount": _first_float(wr.get("CommodityTax", []), 0.0),
            "amount_with_tax": parse_number(wr.get("AmountInFiguers", 0)) or 0.0,

            # 分类
            "category": category,
        }

        # 如果没有单独的商品税额，尝试从合计税额获取
        if fields["tax_amount"] == 0:
            fields["tax_amount"] = parse_number(wr.get("TotalTax", 0)) or 0.0

        return fields

