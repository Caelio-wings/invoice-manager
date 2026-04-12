# 发票夹子 v2.0 · AI Agent 开发指南

本指南旨在帮助 **Claude Code** 等 AI 编程助手快速理解项目结构、运行方式及二次开发切入点。通过阅读本文，AI 可高效完成功能扩展、Bug 修复或定制化修改。

---

## 🚀 项目速览

- **名称**：发票夹子 (Invoice Manager)
- **版本**：v2.0
- **目标**：轻量级发票识别、归档、管理、导出工具
- **技术栈**：Python 3.10+ · Streamlit · SQLite · PyMuPDF · 百度OCR API / LLM Vision API
- **双入口**：Web UI (`app.py`) + CLI (`main.py`)

---

## 📁 核心文件与职责（AI 重点关注）

| 文件/目录 | 作用 | AI 扩展点 |
|-----------|------|-----------|
| `app.py` | Streamlit Web 界面 | 新增页面、修改表格列、添加图表统计 |
| `main.py` | CLI 命令入口 | 添加新子命令、调整参数 |
| `config/config.yaml` | 配置文件（API密钥、路径、引擎开关） | 新增配置项 |
| `invoice_clipper/processor.py` | **发票处理主流程**（预处理→识别→去重→归档→入库） | 修改处理逻辑、增加预处理步骤 |
| `invoice_clipper/database.py` | SQLite 数据库操作（建表、CRUD） | 新增字段需同步修改表结构 |
| `invoice_clipper/exporter.py` | Excel 明细与 PDF 合并导出 | 自定义导出格式、增加图表 |
| `invoice_clipper/file_utils.py` | PDF 文本提取、OFD 转 PDF、归档路径构建 | 优化归档规则 |
| `invoice_clipper/engines/` | **识别引擎集合**（基类、百度OCR、LLM、本地OCR） | **新增识别引擎**的主要位置 |

---

## ⚙️ 配置文件说明 (`config/config.yaml`)

```yaml
storage:
  base_dir: ~/Documents/发票夹子   # 归档根目录
  db_path: ~/Documents/发票夹子/invoices.db

watch_dirs:                        # CLI scan 扫描目录
  - ~/Documents/发票夹子/inbox

ocr:
  text_ocr:                        # 本地 OCR（默认关闭）
    enabled: false
  baidu:                           # 百度 OCR
    enabled: true
    api_key: "your_key"
    secret_key: "your_secret"
  llm:                             # 大模型视觉
    enabled: true
    api_key: "your_key"
    base_url: "https://api.deepseek.com/v1"
    model: "deepseek-chat"
    prompt_template: "..."         # 可自定义识别提示词
```

- **引擎优先级**：`text_ocr` (priority=1) → `baidu` (priority=2) → `llm` (priority=3)
- **开关控制**：每个引擎下的 `enabled` 字段决定是否启用

---

## 🔌 识别引擎扩展（AI 二次开发重点）

### 1. 新增自定义引擎

1. 在 `invoice_clipper/engines/` 下新建 `my_engine.py`
2. 继承 `BaseEngine`，实现 `__init__`、`is_available()`、`extract(file_path)`
3. 在 `engines/__init__.py` 中导出
4. 在 `processor.py` 的 `_init_engines` 中注册

**示例模板**：
```python
from .base import BaseEngine, EngineResult

class MyEngine(BaseEngine):
    name = "my_engine"
    priority = 10   # 越小越先执行

    def __init__(self, config):
        self.enabled = config.get("ocr", {}).get("my_engine", {}).get("enabled", False)

    def is_available(self) -> bool:
        return self.enabled

    def extract(self, file_path: str) -> EngineResult:
        # 实现识别逻辑，返回 EngineResult
        data = {"invoice_number": "123456", ...}
        return EngineResult(data=data, confidence=0.9, engine=self.name)
```

### 2. 修改 Prompt 模板（针对 LLM 引擎）

直接在 `config.yaml` 的 `llm.prompt_template` 中调整，无需改代码。

### 3. 调整归档路径规则

修改 `file_utils.py` 中的 `build_archive_path()` 函数。

---

## 🗃️ 数据库表结构

表名：`invoices`  
关键字段：`invoice_number`, `invoice_code`, `invoice_date`, `commodity_name`, `specification_model`, `buyer_name`, `buyer_tax_num`, `seller_name`, `seller_tax_num`, `tax_rate`, `tax_amount`, `amount_with_tax`, `category`, `belong_project`, `belong_person`, `remark`, `excluded`, `stored_path`, `created_at`

**添加新字段步骤**：
1. 修改 `database.py` 的 `init_db()` 建表语句和 `insert_invoice()` 列列表
2. 更新 `processor.py` 中 `_build_record()` 的字段映射
3. 如需前端展示/编辑，修改 `app.py` 中的 DataFrame 列和编辑表单

---

## 🖥️ 前端修改指南 (`app.py`)

- **增加页面**：在 `sidebar_nav()` 中添加选项，并编写对应 `page_xxx()` 函数
- **修改表格显示列**：调整 `page_list` 和 `page_query` 中构建 `data` 列表的字段
- **编辑表单字段**：在 `page_list` 的详情编辑区域内增删 `st.text_input` / `st.number_input` 控件

---

## 🧪 常用调试命令

```bash
# 运行 Web 界面（开发模式，自动重载）
streamlit run app.py

# 单文件处理测试
python main.py process /path/to/invoice.pdf

# 查看数据库内容
sqlite3 ~/Documents/发票夹子/invoices.db "SELECT * FROM invoices LIMIT 5;"
```

---

## 🤖 AI Agent 典型任务示例

### 任务 1：增加“发票验真”功能（调用第三方 API）

1. 在 `config.yaml` 中添加验真 API 配置段
2. 新建 `invoice_clipper/verifier.py`，实现验真逻辑
3. 在 `processor.py` 的 `process_file` 中调用验真函数，将结果存入数据库（需扩展表字段）
4. 在 `app.py` 中展示验真状态

### 任务 2：导出时增加图表统计

1. 在 `exporter.py` 的 `export_excel` 中利用 `openpyxl` 插入图表（参考 openpyxl 官方文档）
2. 可选：在 Web UI 导出页增加图表预览

### 任务 3：支持更多发票类型（如定额发票、火车票）

1. 研究目标发票的识别方案（现有引擎能否覆盖？）
2. 若需特殊解析逻辑，新增一个识别引擎或在现有引擎中扩展字段提取正则
3. 更新数据库字段（如有新属性）

---

## 📌 注意事项

- **Windows 路径问题**：项目已使用 `pathlib` 和 `expanduser()`，兼容性好，但需注意临时目录处理（`tempfile.gettempdir()`）
- **编码统一 UTF-8**：所有文件读写均指定 `encoding='utf-8'`
- **引擎降级逻辑**：识别结果通过 `EngineResult.is_valid`（置信度 ≥ 0.6 且含核心字段）判断是否继续下一级

---

**AI 可基于以上信息快速定位修改点，无需通读全部源码。** 如需更详细的模块说明，请查看各文件的文档注释。