<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-blue.svg" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/Version-3.3.1-brightgreen.svg" alt="v3.3.1">
</p>

<h1 align="center">发票夹子 🧾</h1>

<p align="center">
  <strong>轻量级发票识别与管理工具</strong><br>
  本地优先 · 三级引擎降级 · 标签系统 · 智能凑票 · 一键导出<br>
  支持 SQLite / PostgreSQL · Web UI + CLI 双入口
</p>

---

## ✨ 功能概览

| 功能 | 说明 |
|------|------|
| 🖥️ **Web UI** | FastAPI 可视化界面，拖拽上传、表格编辑、一键导出 |
| ⌨️ **CLI + MCP** | 命令行批量处理 + AI Agent 接口 (MCP协议) |
| 🔍 **三级识别引擎** | 百度 OCR → 大模型视觉 → 本地 OCR，自动降级 |
| 📁 **智能归档** | `年份/日期_金额_销售方_发票号.pdf` 自动整理 |
| 🏷️ **标签系统** | 自定义彩色标签，快速分类和筛选发票 |
| 🎯 **智能凑票** | 给定目标金额，自动找出最优发票组合 |
| 📊 **灵活导出** | 选择指定发票，合并PDF/源文件ZIP/附件打包 |
| 🗄️ **双数据库** | SQLite（默认）或 PostgreSQL，配置即切 |

---

## 🚀 快速开始

### 安装

```bash
# 从 Wheel 包安装
pip install dist/invoice_manager-3.3.0-py3-none-any.whl
```

### 启动 Web UI

```bash
# 正常启动（带进程锁）
uv run python -m invoice_clipper.__run__

# 调试模式（跳过进程锁）
uv run python -m invoice_clipper.__run__ --debug

# 或直接启动（无锁）
uv run python -m invoice_clipper
```

浏览器打开 http://localhost:8000

### CLI 日常使用

```bash
# 扫描监控目录中的发票
uv run python invoice_clipper/__main__.py scan

# 列出所有发票
uv run python invoice_clipper/__main__.py list

# 按条件查询
uv run python invoice_clipper/__main__.py query --from 2025-01-01 --to 2025-12-31 --seller "科技公司"

# 处理单个文件
uv run python invoice_clipper/__main__.py process invoice.pdf

# 标记排除/恢复报销
uv run python invoice_clipper/__main__.py exclude 3
uv run python invoice_clipper/__main__.py include 3

# 导出报销
uv run python invoice_clipper/__main__.py export --from 2025-03 --format both
```

---

## 📦 安装方式

### Wheel 包（推荐）

```bash
pip install dist/invoice_manager-3.3.1-py3-none-any.whl
```

安装后可用命令：

| 命令 | 说明 |
|------|------|
| `invoice-manager scan/list/...` | CLI 操作 |
| `invoice-manager-web` | 启动 Web UI |

### 源码开发

```bash
git clone https://github.com/yourname/invoice-manager.git
cd invoice-manager
uv sync
# 首次运行自动生成配置
uv run python -m invoice_clipper
```

---

## ⚙️ 配置

### 配置文件搜索顺序

1. `INVOICE_MANAGER_CONFIG` 环境变量（最高优先级）
2. `{INVOICE_ROOT}/config/config.yaml`
3. `~/.config/invoice-manager/config.yaml`
4. 包相对路径 `config/config.yaml`（开发模式）

首次运行自动复制示例配置并初始化数据库。

### 识别引擎

```yaml
ocr:
  # 百度 OCR（推荐，准确率高）
  baidu:
    enabled: true
    api_key: "your_api_key"
    secret_key: "your_secret_key"

  # 大模型视觉（OpenAI 兼容）
  llm:
    enabled: false
    api_key: "your_llm_api_key"
    base_url: "https://api.deepseek.com/v1"
    model: "deepseek-chat"

  # 本地 OCR（完全离线，需安装 PaddleOCR）
  text_ocr:
    enabled: false
```

---

## 🖥️ Web UI 页面

| 页面 | 路由 | 功能 |
|------|------|------|
| 📤 扫描发票 | `/scan` | 文件上传 + 归属分配 + 实时识别结果 |
| 📋 发票列表 | `/list` | 表格展示、排序搜索、行内快速操作、批量操作 |
| 🔍 查询筛选 | `/query` | 多条件筛选（含标签过滤） |
| ✏️ 编辑详情 | `/list/{id}` | 全字段编辑 + 附件管理 + 标签选择 |
| 🏷️ 标签管理 | `/tags` | 创建/删除彩色标签 |
| 🎯 智能凑票 | `/match-amount` | 输入目标金额，自动匹配最优发票组合 |
| 📊 导出报销 | `/export` | 选发票/按条件、合并PDF/源文件ZIP/附件打包 |
| 🏷️ 归属管理 | `/assignments` | 创建/删除归属项目与归属人 |

---

## 🗂️ 项目结构

```
invoice-manager/
├── pyproject.toml                # 项目元数据 + 构建配置
├── invoice_clipper/              # 核心 Python 包
│   ├── __init__.py               # load_config + 所有模块导出
│   ├── __main__.py               # pip 入口点
│   ├── __run__.py                # 进程锁启动入口（支持 --debug）
│   ├── web.py                    # FastAPI Web UI (v3.3.1)
│   ├── mcp_server.py             # MCP AI Agent 接口
│   ├── database.py               # 数据库调度层
│   ├── db_backends.py            # SQLite + PostgreSQL 后端
│   ├── processor.py              # 发票处理主流程
│   ├── exporter.py               # Excel / PDF / ZIP 导出
│   ├── file_utils.py             # 文件转换与归档
│   ├── matcher.py                # 智能凑票算法
│   ├── config.example.yaml       # 配置模板
│   ├── static/
│   │   └── style.css             # 完整样式系统
│   ├── templates/                # Jinja2 模板
│   │   ├── base.html             # 布局 + 导航
│   │   ├── scan.html             # 扫描上传
│   │   ├── list.html             # 发票列表
│   │   ├── edit.html             # 编辑 + 附件 + 标签
│   │   ├── query.html            # 查询筛选
│   │   ├── export.html           # 导出选项
│   │   ├── tags.html             # 标签管理
│   │   ├── match_amount.html     # 智能凑票
│   │   └── assignments.html      # 归属管理
│   └── engines/                  # 识别引擎
│       ├── base.py               # 抽象基类
│       ├── _utils.py             # 共享工具函数
│       ├── text_ocr.py           # 本地 OCR
│       ├── baidu_ocr.py          # 百度 OCR
│       └── llm_vision.py         # 大模型视觉
└── dist/
    └── invoice_manager-3.3.1-py3-none-any.whl
```

---

## 🔧 依赖

核心依赖（见 `pyproject.toml`）：

| 包 | 用途 |
|----|------|
| `fastapi` / `uvicorn` / `jinja2` | Web UI 框架 |
| `openpyxl` | Excel 导出 |
| `PyMuPDF` | PDF 处理 + 图片转 PDF |
| `httpx` | API 请求 |
| `mcp` | MCP AI Agent 协议 |
| `python-multipart` | 文件上传 |
| `pyyaml` | 配置解析 |

可选依赖：
- `easyofd` → OFD 电子发票格式支持
- `psycopg2-binary` → PostgreSQL 支持
- `paddlepaddle` + `paddleocr` → 本地离线 OCR

---

## 🎯 v3.3.1 新增功能

| 功能 | 说明 |
|------|------|
| 🐛 **批量状态修复** | 批量标记排除/恢复正常接口修复 |
| ♾️ **凑票张数不限** | `max_count=0` 表示不限制张数 |

---

## 📄 开源协议

MIT License
