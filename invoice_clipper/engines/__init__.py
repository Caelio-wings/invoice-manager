"""
发票识别引擎模块 - 重构版 v2.0

两级识别链路：
  第1级 百度OCR API → 增值税发票结构化识别
  第2级 LLM Vision API → 多模态大模型识别
"""

from .base import BaseEngine, EngineResult
from .text_ocr import TextOCREngine
from .baidu_ocr import BaiduOCREngine
from .llm_vision import LLMVisionEngine

__all__ = [
    "BaseEngine",
    "EngineResult",
    "TextOCREngine",
    "BaiduOCREngine",
    "LLMVisionEngine",
]
