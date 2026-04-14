---
name: invoice-manager
description: >
  发票管理 v2.0.1 - 轻量级发票识别、归档、管理与导出工具。
  支持双入口：Streamlit Web UI 和 CLI 命令行。
  识别引擎：百度 OCR（默认）+ LLM Vision（降级）+ 本地混合 OCR（可选）。
  适用于个人、小微企业快速整理电子发票。
version: 2.0.1
metadata:
  entrypoint: app.py
  cli: main.py
  config: config/config.yaml
  requires:
    python: ">=3.10"
    packages: [streamlit, pandas, pymupdf, httpx, openpyxl, pyyaml]
---

# 发票夹子 (Invoice Manager) v2.0

## 📌 项目概述

纯 Python 实现的发票管理工具，专注于：
- 发票文件上传/扫描识别
- SQLite 本地存储与归档
- 全字段编辑与筛选
- 一键导出 Excel 明细表 + 合并 PDF


## 🚀 快速开始（Agent 执行）

### 1. 环境准备

```bash
cd /path/to/project
pip install -r requirements.txt
```

### 2. 配置文件

确保 `config/config.yaml` 存在并填写 API 密钥。模板如下：

```yaml
storage:
  base_dir: ~/Documents/发票夹子
  db_path: ~/Documents/发票夹子/invoices.db

watch_dirs:
  - ~/Documents/发票夹子/inbox

ocr:
  baidu:
    enabled: true
    api_key: "your_api_key"
    secret_key: "your_secret_key"
  llm:
    enabled: true
    api_key: "your_llm_key"
    base_url: "https://api.deepseek.com/v1"
    model: "deepseek-chat"
  text_ocr:
    enabled: false   # 可选本地 OCR
```

### 3. 启动 Web UI

```bash
streamlit run app.py
# 访问 http://localhost:8501
```

### 4. CLI 命令

```bash
python main.py scan                # 扫描监控目录
python main.py list                # 列出所有发票
python main.py query --from 2025-03-01 --to 2025-03-31
python main.py export --from 2025-03-01 --format both
python main.py exclude 5           # 排除 #5 号发票
python main.py process /path/to/invoice.pdf
```

## 🧠 Agent 常用操作指南

### 意图 → 命令映射

| 用户自然语言 | 应执行的 CLI 命令 |
|-------------|------------------|
| "扫描新发票" / "整理收件箱" | `python main.py scan` |
| "显示所有发票" | `python main.py list` |
| "查询3月份的发票" | `python main.py query --from 2025-03-01 --to 2025-03-31` |
| "导出本月的报销单" | `python main.py export --from $(date +%Y-%m-01) --format both` |
| "不要报销 #3 那张" | `python main.py exclude 3` |
| "恢复 #3 发票" | `python main.py include 3` |

### 如何通过 Python 代码调用（供 Agent 内部使用）

```python
from invoice_clipper.processor import InvoiceProcessor
from invoice_clipper.database import query_invoices, update_invoice_metadata

# 初始化处理器
config = load_config()   # 从 config.yaml 加载
proc = InvoiceProcessor(config)

# 处理单张发票
result = proc.process_file(Path("/path/to/invoice.pdf"), source="agent")
if result:
    print(f"入库成功，ID={result['id']}")

# 查询发票
invoices = query_invoices(db_path, {"date_from": "2025-03-01", "only_included": True})
```

## 📁 目录结构

```
invoice-manager/
├── app.py                     # Streamlit Web 入口
├── main.py                    # CLI 入口
├── config/
│   └── config.yaml
├── invoice_clipper/
│   ├── processor.py           # 发票处理主流程
│   ├── database.py            # SQLite 操作
│   ├── exporter.py            # Excel/PDF 导出
│   ├── file_utils.py          # 文件转换、归档
│   └── engines/               # 识别引擎
│       ├── base.py
│       ├── baidu_ocr.py
│       ├── llm_vision.py
│       └── text_ocr.py
├── requirements.txt
└── README.md
```

### 修改导出格式

编辑 `exporter.py` 中的 `export_excel` 和 `export_merged_pdf` 函数。

## ⚠️ 注意事项

- 所有文件读写均需使用 `encoding='utf-8'`
- 临时文件请用 `tempfile.gettempdir()` 获取系统临时目录，避免 Windows 下 `/tmp` 不存在
- 识别引擎通过 `EngineResult.is_valid`（置信度≥0.6且含核心字段）决定是否降级
- 数据库路径使用 `pathlib.Path.expanduser()` 处理 `~`

