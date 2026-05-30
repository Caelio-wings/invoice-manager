<p align="center">
  <img src="https://img.shields.io/badge/Python-3.14+-blue.svg" alt="Python 3.14+">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/Wheel-3.1.2-brightgreen.svg" alt="Wheel v3.1.2">
</p>

<h1 align="center">发票夹子 🧾</h1>

<p align="center">
  <strong>轻量级发票识别与管理工具</strong><br>
  本地优先 · 三级引擎降级 · 归属管理 · 一键导出<br>
  支持 SQLite / PostgreSQL · Web UI + CLI 双入口
</p>

---

## ✨ 功能概览

| 功能 | 说明 |
|------|------|
| 🖥️ **Web UI** | FastAPI 可视化界面，拖拽上传、表格编辑、一键导出 |
| ⌨️ **CLI 命令行** | 批量处理、自动化脚本友好 |
| 🔍 **三级识别引擎** | 百度 OCR → 大模型视觉 → 本地 OCR，自动降级 |
| 📁 **智能归档** | `年份/日期_金额_销售方_发票号.pdf` 自动整理 |
| 🏷️ **归属管理** | 自定义归属项目/归属人，扫描时快速分配 |
| 🗄️ **双数据库** | SQLite（默认）或 PostgreSQL，配置即切 |
| 📊 **一键导出** | Excel 明细表 + 合并 PDF + 附件打包 |
| 📱 **响应式设计** | 桌面 + 移动端自适应 |

---

## 🚀 快速开始

### 安装

```bash
# 1. 从 Wheel 包安装
pip install dist/invoice_manager-3.1.2-py3-none-any.whl

# 2. 运行安装引导（交互式）
invoice-manager init
```

引导程序会：
- 选择数据存储目录
- 选择数据库类型（SQLite / PostgreSQL）
- 生成配置文件 `config.yaml`
- 初始化数据库表
- 创建 `invoice` 快捷命令

### 启动 Web UI

```bash
invoice web
# 或
invoice-manager-web
```

浏览器打开 http://localhost:8000

### CLI 日常使用

```bash
# 扫描监控目录中的发票
invoice scan

# 列出所有发票
invoice list

# 按条件查询
invoice query --from 2025-01-01 --to 2025-12-31 --seller "科技公司"

# 处理单个文件
invoice process invoice.pdf

# 标记排除/恢复报销
invoice exclude 3
invoice include 3

# 导出报销
invoice export --from 2025-03 --format both
```

---

## 📦 安装方式

### Wheel 包（推荐）

```bash
pip install dist/invoice_manager-3.1.2-py3-none-any.whl
```

安装后可用命令：

| 命令 | 说明 |
|------|------|
| `invoice-manager init` | 交互式安装引导 |
| `invoice-manager scan/list/...` | CLI 操作 |
| `invoice-manager-web` | 启动 Web UI |
| `invoice scan/list/...` | 快捷命令（init 后可用） |
| `invoice web` | 快捷启动 Web UI |

### 源码开发

```bash
git clone https://github.com/yourname/invoice-manager.git
cd invoice-manager
uv sync
cp config/config.example.yaml config/config.yaml
# 编辑 config.yaml 配置 API 密钥
python app.py          # Web UI
python main.py list    # CLI
```

---

## ⚙️ 配置

### 配置文件搜索顺序

1. `INVOICE_MANAGER_CONFIG` 环境变量（最高优先级）
2. `./config/config.yaml`（可执行文件同目录）
3. `invoice_clipper/../config/config.yaml`（包相对路径）

### 数据库配置

```yaml
storage:
  # SQLite（默认）
  db_type: sqlite
  db_path: ~/invoice-manager/invoices.db

  # 或 PostgreSQL
  # db_type: postgresql
  # pg_host: localhost
  # pg_port: 5432
  # pg_database: invoice_manager
  # pg_user: postgres
  # pg_password: "xxx"
```

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
    enabled: true
    api_key: "your_llm_api_key"
    base_url: "https://api.deepseek.com/v1"
    model: "deepseek-chat"

  # 本地 OCR（完全离线）
  text_ocr:
    enabled: false
```

---

## 🖥️ Web UI 页面

| 页面 | 路由 | 功能 |
|------|------|------|
| 📤 扫描发票 | `/scan` | 文件上传 + 归属分配 + 实时结果 |
| 📋 发票列表 | `/list` | 表格展示、排序、搜索、批量操作 |
| 🔍 查询筛选 | `/query` | 多条件筛选 |
| ✏️ 编辑详情 | `/list/{id}` | 全字段编辑 + 附件管理 |
| 🏷️ 归属管理 | `/assignments` | 创建/删除归属项目与归属人 |
| 📥 导出报销 | `/export` | Excel + PDF + 附件打包 |

---

## 🗂️ 项目结构

```
invoice-manager/
├── app.py                        # FastAPI Web 入口
├── main.py                       # CLI 入口（含 init 引导命令）
├── run.py                        # 启动入口（配置加载 + 浏览器打开）
├── pyproject.toml                # 项目元数据 + 构建配置
├── config/
│   ├── config.yaml               # 用户配置（已 gitignore）
│   └── config.example.yaml       # 配置模板
├── templates/                    # Jinja2 模板
│   ├── base.html                 # 顶部导航布局
│   ├── scan.html                 # 扫描上传
│   ├── list.html                 # 发票列表（含排序 JS）
│   ├── edit.html                 # 编辑 + 附件管理
│   ├── query.html                # 查询筛选
│   ├── export.html               # 导出选项
│   └── assignments.html          # 归属管理
├── static/
│   └── style.css                 # Seline Analytics 设计系统
├── invoice_clipper/              # 核心 Python 包
│   ├── __init__.py               # load_config + exports
│   ├── __main__.py               # pip 入口点（invoice 命令）
│   ├── database.py               # 数据库调度层
│   ├── db_backends.py            # SQLite + PostgreSQL 后端实现
│   ├── processor.py              # 发票处理主流程
│   ├── exporter.py               # Excel / PDF / 附件导出
│   ├── file_utils.py             # 文件转换与归档
│   └── engines/                  # 识别引擎
│       ├── base.py               # 抽象基类
│       ├── _utils.py             # 共享工具函数
│       ├── text_ocr.py           # 本地 OCR
│       ├── baidu_ocr.py          # 百度 OCR
│       └── llm_vision.py         # 大模型视觉
└── dist/
    └── invoice_manager-3.1.2-py3-none-any.whl
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
| `easyofd` | OFD → PDF 转换 |
| `python-multipart` | 文件上传 |
| `baidu-aip` | 百度 OCR SDK |
| `pyyaml` | 配置解析 |
| `psycopg2-binary` | PostgreSQL 支持 |

---

## 🧪 使用示例

### 扫描并分配归属

```bash
# 先创建归属项目和人
invoice-manager init
# 然后在 Web UI 上传时选择归属

# 或 CLI 扫描后编辑
invoice list
```

### 批量导出带附件

1. 打开 `/export` 页
2. 设置筛选条件
3. 勾选「合并发票 PDF」和「随附附件打包」
4. 点击导出 → 下载 Excel + PDF + 附件 ZIP

---

## 📄 开源协议

MIT License

---

## 🙏 致谢

- [百度智能云 OCR](https://cloud.baidu.com/product/ocr.html)
- [FastAPI](https://fastapi.tiangolo.com/)
- [PyMuPDF](https://pymupdf.readthedocs.io/)
- [Seline Analytics](https://seline.so/) — UI 设计参考
