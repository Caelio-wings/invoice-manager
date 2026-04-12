## 发票夹子 v2.0 🧾

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

> 轻量级发票识别与管理工具 · 本地优先 · API 两级降级 · 一键导出报销

**发票夹子 v2.0** 是一个专注于**发票识别、归档、管理、导出**的轻量级工具。  
剥离了旧版的复杂风控、邮件拉取和验真功能，保留核心发票处理流程，支持 CLI 命令行和 Web 可视化界面双入口，适合个人、自由职业者或小微企业快速整理电子发票。

---

## ✨ 功能特性

- **双入口操作**  
  - 🖥️ **Streamlit Web UI**：拖拽上传、表格管理、在线编辑、一键导出  
  - ⌨️ **CLI 命令行**：适合自动化脚本、批量处理

- **两级智能识别**（可配置启停）  
  1. 百度 OCR API —— 增值税发票结构化识别（准确率高）  
  2. 大模型视觉 API —— 支持 OpenAI 兼容格式（DeepSeek / Qwen / GPT-4V 等）  
  3. 可选本地混合 OCR（pdfplumber + PaddleOCR）完全离线识别

- **全字段支持**  
  覆盖发票号码、代码、日期、商品名称、规格型号、购销双方名称与税号、税率、税额、价税合计、分类、归属项目、归属人、备注等

- **智能归档**  
  识别后的 PDF/OFD 文件按 `年份/日期_金额_销售方_发票号.pdf` 自动整理归档

- **数据管理**  
  - SQLite 本地存储，无需额外数据库  
  - 支持标记“排除报销”、批量操作  
  - Web UI 中可在线编辑所有字段（包括自定义归属）

- **一键导出报销**  
  生成 Excel 明细表（含合计行）+ 合并 PDF 报销包

---

## 📦 快速开始

### 1. 环境要求

- Python 3.10+
- 推荐使用虚拟环境（conda / venv）

### 2. 安装依赖

```bash
git clone https://github.com/yourname/invoice-manager.git
cd invoice-manager
pip install -r requirements.txt
```

### 3. 配置文件

复制配置模板并填写 API 密钥：

```bash
cp config/config.yaml.example config/config.yaml
```

编辑 `config/config.yaml`，至少配置一种识别引擎（百度 OCR 或 LLM）。

```yaml
storage:
  base_dir: ~/Documents/发票夹子
  db_path: ~/Documents/发票夹子/invoices.db

watch_dirs:
  - ~/Documents/发票夹子/inbox

ocr:
  # 百度 OCR（推荐）
  baidu:
    enabled: true
    api_key: "your_api_key"
    secret_key: "your_secret_key"

  # 大模型视觉
  llm:
    enabled: true
    api_key: "your_llm_api_key"
    base_url: "https://api.deepseek.com/v1"
    model: "deepseek-chat"
```

### 4. 运行

#### Web UI（推荐）

```bash
streamlit run app.py
```

浏览器自动打开 http://localhost:8501

#### CLI 命令行

```bash
python main.py scan           # 扫描监控目录
python main.py list           # 列出所有发票
python main.py export --format both  # 导出报销 Excel + PDF
```

---

## 🗂️ 目录结构

```
invoice-manager/
├── app.py                     # Streamlit Web 入口
├── main.py                    # CLI 入口
├── setup_config.py            # 交互式配置向导（可选）
├── config/
│   └── config.yaml            # 配置文件
├── invoice_clipper/           # 核心包
│   ├── processor.py           # 发票处理主流程
│   ├── database.py            # SQLite 数据库操作
│   ├── exporter.py            # Excel / PDF 导出
│   ├── file_utils.py          # 文件转换、归档工具
│   └── engines/               # 识别引擎
│       ├── base.py
│       ├── text_ocr.py        # 本地 OCR（可选）
│       ├── baidu_ocr.py       # 百度 OCR
│       └── llm_vision.py      # 大模型视觉
├── requirements.txt
└── README.md
```

---

## ⚙️ 配置详解

### 存储路径

- `storage.base_dir`：发票 PDF 归档根目录，按年份自动分层  
- `storage.db_path`：SQLite 数据库文件位置

### 识别引擎

每个引擎均可通过 `enabled: true/false` 单独控制。

#### 1. 百度 OCR（`baidu`）

- 需在[百度智能云](https://console.bce.baidu.com/ai/#/ai/ocr/overview)创建应用获取 API Key / Secret Key  
- 增值税发票识别准确率高，推荐作为第一级

#### 2. 大模型视觉（`llm`）

- 支持 OpenAI 兼容 API（DeepSeek、Qwen、GPT-4V、本地 Ollama 等）  
- 可自定义 `base_url`、`model`、`prompt_template`  
- 作为百度 OCR 失败时的降级方案

#### 3. 本地混合 OCR（`text_ocr`）

- 使用 `pdfplumber` 提取文本 + `PaddleOCR` 识别扫描件  
- **完全离线**，无需 API 密钥  
- 依赖较多，默认关闭，适合内网或无网络环境

---

## 🧪 使用示例

### Web UI 典型流程

1. 打开 **📤 扫描发票** 页，上传 PDF/OFD/图片  
2. 系统自动识别并入库  
3. 在 **📋 发票列表** 页查看所有发票，可在线编辑任意字段、标记排除、批量操作  
4. 需要报销时，进入 **📥 导出报销** 页，选择日期范围，一键下载 Excel 和合并 PDF

### CLI 常用命令

```bash
# 扫描监控目录
python main.py scan

# 列出所有发票
python main.py list

# 按条件查询
python main.py query --from 2025-01-01 --to 2025-12-31 --seller "科技公司"

# 标记排除/恢复
python main.py exclude 3
python main.py include 3

# 导出报销（Excel + PDF）
python main.py export --from 2025-03-01 --to 2025-03-31 --format both
```

---

## 🔧 依赖清单

核心依赖见 `requirements.txt`，主要包含：

- `streamlit` - Web UI  
- `pandas` / `openpyxl` - 数据处理与 Excel 导出  
- `PyMuPDF` - PDF 文本提取、合并、转图片  
- `httpx` - API 请求  
- `easyofd` - OFD 转 PDF  
- `pyyaml` - 配置文件解析  
- 可选：`paddlepaddle`、`paddleocr`、`pdfplumber`、`pdf2image`（本地 OCR）

---

## ❓ 常见问题

### Q: 百度 OCR 或 LLM 识别失败怎么办？

- 检查 `config.yaml` 中 API 密钥是否正确，网络是否通畅  
- 可在 Web UI 的发票详情页手动编辑修正字段

### Q: 如何完全离线使用？

- 启用 `text_ocr` 引擎（需安装 PaddleOCR 相关依赖）  
- 或使用本地部署的 Ollama + 视觉模型，在 `llm` 中配置 `base_url` 指向本地服务

### Q: 上传文件时报 `FileNotFoundError: /tmp/...` 错误？

- Windows 系统下临时目录问题，已在最新版修复，使用系统 `tempfile` 目录

### Q: 数据库字段可以自定义吗？

- 目前支持编辑所有预定义字段，如需新增字段需修改数据库表结构和相关代码

---

## 📄 开源协议

MIT License - 详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- [百度智能云 OCR](https://cloud.baidu.com/product/ocr.html)  
- [DeepSeek](https://www.deepseek.com/)  
- [Streamlit](https://streamlit.io/)  
- [PyMuPDF](https://pymupdf.readthedocs.io/)

---

**发票夹子 v2.0** —— 让发票管理回归简单。如有问题或建议，欢迎提交 Issue。