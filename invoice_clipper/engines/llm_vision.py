"""
第2级引擎：LLM Vision API
调用 OpenAI 兼容格式的多模态大模型进行发票识别
支持 DeepSeek-VL、Qwen-VL、GPT-4V 等
"""
import base64
import json
import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any

import httpx
import fitz

from .base import BaseEngine, EngineResult

logger = logging.getLogger(__name__)

# 默认 Prompt 模板
DEFAULT_PROMPT = """请识别这张发票图片，严格以 JSON 格式返回以下字段：
{
  "invoice_number": "发票号码",
  "invoice_code": "发票代码",
  "invoice_date": "开票日期 YYYY-MM-DD",
  "commodity_name": "项目名称（第一项即可）",
  "specification_model": "规格型号（若无则留空字符串）",
  "buyer_name": "购买方名称",
  "buyer_tax_num": "购买方纳税人识别号",
  "seller_name": "销售方名称",
  "seller_tax_num": "销售方纳税人识别号",
  "tax_rate": "税率（小数，如0.13）",
  "tax_amount": "税额",
  "amount_with_tax": "价税合计",
  "category": "发票分类（餐饮/交通/办公/服务/通讯/其他）"
}

注意：
- 如果字段无法识别或不存在，使用空字符串 ""
- 金额字段必须是数字，不要包含千分位逗号或货币符号
- 税率如果是百分比，请转换为小数（如6% → 0.06）
- 只返回 JSON，不要任何解释文字。"""


class LLMVisionEngine(BaseEngine):
    """
    LLM Vision API 识别引擎
    支持任何 OpenAI 兼容的 vision API（DeepSeek、Qwen、GPT-4V 等）
    """

    name = "llm_vision"
    priority = 2  # 第二优先级，百度 OCR 失败后使用

    def __init__(self, config: dict):
        self.cfg = config
        llm_cfg = config.get("ocr", {}).get("llm", {})
        self.enabled = llm_cfg.get("enabled", True)
        self.api_key = llm_cfg.get("api_key", "")
        self.base_url = llm_cfg.get("base_url", "https://api.deepseek.com/v1")
        self.model = llm_cfg.get("model", "deepseek-chat")
        self.prompt_template = llm_cfg.get("prompt_template", DEFAULT_PROMPT)
        self.timeout = llm_cfg.get("timeout", 120)

        if not self.api_key:
            logger.warning("LLM API Key 未配置，引擎不可用")

    def is_available(self) -> bool:
        if not self.enabled:
            logger.debug("LLM Vision 引擎已禁用")
            return False
        return bool(self.api_key)

    def extract(self, file_path: str) -> EngineResult:
        """对文件执行发票识别"""
        path = Path(file_path)
        suffix = path.suffix.lower()

        try:
            # 准备图片 Base64
            if suffix == ".pdf":
                img_bytes = self._pdf_to_image(file_path)
            elif suffix in (".png", ".jpg", ".jpeg", ".bmp", ".webp"):
                img_bytes = Path(file_path).read_bytes()
            else:
                return EngineResult(
                    data=None,
                    confidence=0,
                    engine=self.name,
                    error=f"不支持的文件类型: {suffix}",
                )

            if not img_bytes:
                return EngineResult(
                    data=None,
                    confidence=0,
                    engine=self.name,
                    error="文件转图片失败",
                )

            b64_image = base64.b64encode(img_bytes).decode("utf-8")

            # 调用 LLM API
            response_text = self._call_llm_api(b64_image)
            if not response_text:
                return EngineResult(
                    data=None,
                    confidence=0,
                    engine=self.name,
                    error="LLM API 返回空响应",
                )

            # 解析 JSON
            data = self._parse_json(response_text)
            if not data:
                return EngineResult(
                    data=None,
                    confidence=0,
                    engine=self.name,
                    raw_text=response_text,
                    error="JSON 解析失败",
                )

            # 后处理
            data = self._post_process(data)

            # 计算置信度
            confidence = self._calculate_confidence(data)

            return EngineResult(
                data=data,
                confidence=confidence,
                engine=self.name,
                raw_text=response_text,
                raw_json=json.dumps(data, ensure_ascii=False),
            )

        except Exception as e:
            return EngineResult(
                data=None,
                confidence=0,
                engine=self.name,
                error=f"识别异常: {e}",
            )

    def _call_llm_api(self, b64_image: str) -> Optional[str]:
        """调用 OpenAI 兼容的 Vision API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # 构造消息（OpenAI Vision 格式）
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": self.prompt_template},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64_image}"},
                    },
                ],
            }
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 2048,
        }

        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )

            if resp.status_code != 200:
                logger.error(f"LLM API 返回 HTTP {resp.status_code}: {resp.text}")
                return None

            result = resp.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content

        except httpx.TimeoutException:
            logger.error(f"LLM API 请求超时 ({self.timeout}s)")
            return None
        except Exception as e:
            logger.error(f"LLM API 调用异常: {e}")
            return None

    def _pdf_to_image(self, pdf_path: str, dpi: int = 200) -> Optional[bytes]:
        """将 PDF 第一页转为 PNG 图片"""
        try:
            doc = fitz.open(pdf_path)
            page = doc[0]
            pix = page.get_pixmap(dpi=dpi)
            img_bytes = pix.tobytes("png")
            doc.close()
            return img_bytes
        except Exception as e:
            logger.error(f"PDF 转图片失败: {e}")
            return None

    def _parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """从 LLM 响应中解析 JSON"""
        if not text:
            return None

        # 清理文本
        text = text.strip()

        # 尝试提取 Markdown 代码块中的 JSON
        for block in text.split("```"):
            block = block.strip()
            if block.startswith("json"):
                block = block[4:].strip()
            try:
                return json.loads(block)
            except json.JSONDecodeError:
                continue

        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 正则提取 JSON 对象
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass

        return None

    def _post_process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化字段格式"""
        processed = {}

        # 字符串字段
        str_fields = [
            "invoice_number", "invoice_code", "commodity_name",
            "specification_model", "buyer_name", "buyer_tax_num",
            "seller_name", "seller_tax_num", "category"
        ]
        for f in str_fields:
            val = data.get(f, "")
            processed[f] = str(val).strip() if val else ""

        # 日期标准化
        date_str = data.get("invoice_date", "")
        processed["invoice_date"] = self._normalize_date(str(date_str))

        # 金额字段
        for f in ["tax_rate", "tax_amount", "amount_with_tax"]:
            processed[f] = self._parse_number(data.get(f))

        # 如果没有分类，尝试推断
        if not processed.get("category"):
            processed["category"] = self._infer_category(data)

        return processed

    def _normalize_date(self, date_str: str) -> str:
        """标准化日期格式为 YYYY-MM-DD"""
        if not date_str:
            return ""

        # 处理 "2023-01-01" 格式
        m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", date_str)
        if m:
            return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

        # 处理 "2023年01月01日" 格式
        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_str)
        if m:
            return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

        # 处理 "2023/01/01" 格式
        m = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})", date_str)
        if m:
            return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

        return date_str

    def _parse_number(self, val) -> Optional[float]:
        """解析数字，处理字符串和千分位"""
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            # 移除千分位逗号、百分号、货币符号
            cleaned = re.sub(r"[¥￥$,%]", "", val.strip())
            try:
                num = float(cleaned)
                # 如果原值包含 %，且大于1，可能是百分比值（如 6%），转换为小数
                if "%" in val and num > 1:
                    num = num / 100
                return num
            except ValueError:
                return None
        return None

    def _infer_category(self, data: Dict[str, Any]) -> str:
        """根据销售方名称等推断分类"""
        seller = data.get("seller_name", "").lower()
        commodity = data.get("commodity_name", "").lower()

        text = f"{seller} {commodity}"

        if any(k in text for k in ["餐饮", "餐厅", "饭店", "食堂"]):
            return "餐饮"
        elif any(k in text for k in ["交通", "运输", "通行", "机票", "火车", "滴滴"]):
            return "交通"
        elif any(k in text for k in ["住宿", "酒店", "宾馆", "旅馆"]):
            return "住宿"
        elif any(k in text for k in ["办公", "文具", "打印", "复印", "耗材"]):
            return "办公"
        elif any(k in text for k in ["服务", "咨询", "代理", "顾问", "设计"]):
            return "服务"
        elif any(k in text for k in ["通讯", "通信", "电话", "宽带"]):
            return "通讯"
        else:
            return "其他"

    def _calculate_confidence(self, fields: Dict[str, Any]) -> float:
        """
        计算置信度，基于关键字段是否齐全
        """
        required = ["invoice_number", "amount_with_tax", "invoice_date", "seller_name"]
        present = sum(1 for f in required if fields.get(f))

        base = present / len(required)

        # 额外加分
        bonus = 0
        if fields.get("buyer_tax_num"):
            bonus += 0.05
        if fields.get("seller_tax_num"):
            bonus += 0.05
        if fields.get("commodity_name"):
            bonus += 0.05
        if fields.get("tax_rate") is not None:
            bonus += 0.05

        return min(1.0, base + bonus)