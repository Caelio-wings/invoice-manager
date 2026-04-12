"""
识别引擎基类定义
"""

from dataclasses import dataclass
from typing import Optional


# 置信度阈值：低于此值视为无效，触发降级
CONFIDENCE_THRESHOLD = 0.6


@dataclass
class EngineResult:
    """识别引擎返回结果"""

    data: Optional[dict]       # 提取到的字段字典
    confidence: float          # 置信度 0-1
    engine: str                # 来源引擎名称
    raw_text: str = ""         # 原始响应文本（调试用）
    raw_json: str = ""         # 原始 JSON 字符串（调试用）
    error: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """
        判断识别结果是否有效

        规则：
        1. data 不能为 None
        2. 必须包含发票号码和价税合计（核心字段）
        3. confidence >= CONFIDENCE_THRESHOLD
        """
        if self.data is None:
            return False
        if not self.data.get("invoice_number"):
            return False
        if not self.data.get("amount_with_tax"):
            return False
        return self.confidence >= CONFIDENCE_THRESHOLD


class BaseEngine:
    """识别引擎抽象基类"""

    name: str = "base"
    priority: int = 99  # 越小优先级越高

    def is_available(self) -> bool:
        """检查引擎是否可用（配置完整、网络可达等）"""
        raise NotImplementedError

    def extract(self, file_path: str) -> EngineResult:
        """对文件执行识别，返回 EngineResult"""
        raise NotImplementedError