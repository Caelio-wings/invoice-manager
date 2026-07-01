# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Web UI (primary interface)
python app.py                           # FastAPI server at http://localhost:8000
# Or: uv run uvicorn invoice_clipper.web:app --reload --port 8000
# After pip install: invoice-manager-web

# Debug / dev (no process lock)
python -m invoice_clipper                # 直接启动 Web UI，无进程锁
python -m invoice_clipper.__run__ --debug  # 通过 __run__ 启动，跳过锁
# After pip install: invoice-manager-web  # 安装版同样无锁

# CLI
python main.py scan                     # Scan configured watch_dirs for new invoices
python main.py list                     # List all invoices in DB
python main.py query --from 2025-03-01 --to 2025-03-31 --seller "科技公司"
python main.py process /path/to/invoice.pdf  # Process a single file
python main.py export --from 2025-03-01 --to 2025-03-31 --format both
python main.py exclude 3                # Mark invoice #3 as non-reimbursable
python main.py include 3                # Restore invoice #3 as reimbursable
python main.py init                     # Interactive setup wizard
# After pip install: invoice-manager scan|list|query|...

# Install (uv)
uv sync
# Or with pip:
pip install -r requirements.txt

# Debug
sqlite3 ~/invoice-manager/invoices.db "SELECT * FROM invoices LIMIT 5;"
```

No test suite exists for this project.

## Architecture

**Dual entry points**: `app.py` (FastAPI + Jinja2 Web UI, port 8000) and `main.py` (CLI with argparse subcommands). Both call `load_config()` from `invoice_clipper/` which reads `config/config.yaml`.

**Web UI** (`app.py` — FastAPI routes + `templates/` Jinja2 templates + `static/style.css`):
- Routes: `/scan` (upload+process), `/list` (table+search), `/list/{id}` (edit+attachments), `/query` (filter), `/export` (generate+download)
- Flash messages via URL query string (`?message=xxx&msg_type=success|warning|error`)
- File downloads via `FileResponse` (streaming, not in-memory)

**Processing pipeline** (`invoice_clipper/processor.py` — `InvoiceProcessor.process_file()`):
1. Preprocess: OFD → PDF conversion if needed (original OFD saved to `{base_dir}/ofd_original/`)
2. Content pre-check: extract PDF text, look for invoice keywords (non-blocking)
3. Recognition: cascade through engines in priority order until one returns `is_valid`
4. Dedup check: reject if invoice_number + amount or invoice_number alone already exists
5. Archive: move file to `{base_dir}/{year}/{date}_{amount}_{seller}_{inv_no}.pdf`
6. DB insert: build record and insert into SQLite

**Recognition engines** (`invoice_clipper/engines/`):
- All inherit from `BaseEngine` and return `EngineResult` (data dict, confidence 0-1, error)
- `_utils.py`: shared functions extracted from the 3 engines — `pdf_to_image()`, `normalize_date()`, `parse_number()`, `infer_category()`, `calculate_confidence()`
- `EngineResult.is_valid` requires confidence ≥ 0.6 AND presence of `invoice_number` and `amount_with_tax`
- Priority order (sorted by `engine.priority`): TextOCR (1) → Baidu OCR (1) → LLM Vision (2)
- TextOCR/baidu both have priority=1 but TextOCR registers first; whichever engine is available and enabled runs first
- Each engine has `enabled` toggle in `config.yaml`

**Database** (`invoice_clipper/database.py`):
- SQLite at path from config `storage.db_path`, with foreign keys enabled
- `invoices` table: `id`, `invoice_number`, `invoice_code`, `invoice_date`, `commodity_name`, `specification_model`, `buyer_name`/`buyer_tax_num`, `seller_name`/`seller_tax_num`, `tax_rate`, `tax_amount`, `amount_with_tax`, `category`, `belong_project`, `belong_person`, `remark`, `source`, `original_filename`, `stored_path`, `excluded`, `created_at`, `raw_text`, `raw_json`. Indexed on invoice_number, invoice_date, seller_name, buyer_name, belong_project, belong_person, excluded.
- `attachments` table: `id`, `invoice_id` (FK → invoices.id CASCADE DELETE), `filename`, `original_name`, `file_type` (payment/receipt/other), `stored_path`, `file_size`, `created_at`
- `query_invoices()` supports filters: date_from/to, seller/buyer (LIKE), project/person (exact), only_included, exclude_ids
- Key functions: `insert_invoice()`, `update_invoice()` (dynamic SET), `is_duplicate()`, `exists_by_invoice_number()`, `delete_invoice()` (cascades attachments), plus attachment CRUD (`get_attachments`, `insert_attachment`, `delete_attachment`)

**Export** (`invoice_clipper/exporter.py`):
- `export_excel()`: styled Excel with frozen header, alternating row colors, summary row
- `export_merged_pdf()`: merges stored PDFs via PyMuPDF
- `build_export_label()`: generates filename label from filter criteria

**File utilities** (`invoice_clipper/file_utils.py`):
- `extract_text_from_pdf()`: quick text extraction via PyMuPDF for content pre-check
- `ofd_to_pdf()`: tries easyofd library first, falls back to ofd2pdf CLI; copies to temp dir to avoid non-ASCII path issues
- `build_archive_path()`: `{base_dir}/{year}/{date}_{amount}_{seller}_{inv_no_short}.pdf`
- `archive_invoice()`: moves file, handles name conflicts with `_01` suffix
- `build_attachment_path()` / `next_attachment_seq()`: attachment file paths with auto-incrementing sequence numbers
- `make_safe_filename()`: sanitizes filenames by removing illegal characters and truncating

## Adding a new recognition engine

1. Create `invoice_clipper/engines/my_engine.py`, subclass `BaseEngine`, implement `is_available()`, `extract(file_path)`
2. Use shared utilities from `engines/_utils.py` for common tasks (date normalization, number parsing, category inference, confidence calculation, PDF-to-image)
3. Export it in `engines/__init__.py`
4. Register in `InvoiceProcessor._init_engines()` in `processor.py`

## Adding a new DB field

1. `database.py`: add column to `init_db()` CREATE TABLE and `insert_invoice()` col list
2. `processor.py`: add field mapping in `_build_record()`
3. `app.py`: add column to DataFrame and edit form in `page_list()`, plus `page_query()` if needed

## Conventions

- Python 3.14+ required (see `.python-version`, `pyproject.toml`)
- Package manager: `uv` (has `uv.lock`); `requirements.txt` also maintained
- All file I/O uses `encoding='utf-8'`
- All paths use `pathlib.Path` with `.expanduser()` for `~` resolution
- Temp files use `tempfile.gettempdir()`, never hardcoded `/tmp` (Windows compat)
- OFD→PDF conversion copies to temp dir first to avoid easyofd's non-ASCII path bug
- Config loaded via `load_config()` from `invoice_clipper/__init__.py`
- Engine cascade: each engine tried in priority order until `EngineResult.is_valid` (confidence ≥ 0.6 AND non-empty `invoice_number` + `amount_with_tax`)
- Engine shared utilities live in `engines/_utils.py` (not `base.py`) to keep PyMuPDF dependency optional for base consumers
