#!/usr/bin/env python3
"""发票夹子 Web UI — FastAPI + Jinja2 (v3.0)"""
import re
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Request, Form, File, UploadFile, Query, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from invoice_clipper import (
    load_config, init_db, query_invoices, update_invoice_status, update_invoice,
    get_invoice_by_id, get_all_invoices, delete_invoice,
    get_attachments, insert_attachment, delete_attachment,
    InvoiceProcessor, export_excel, export_merged_pdf, build_export_label,
    build_attachment_path, next_attachment_seq,
)

BASE_DIR = Path(__file__).parent
app = FastAPI(title="发票夹子", version="3.0")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.on_event("startup")
def startup():
    app.state.config = load_config()
    db_path = str(Path(app.state.config["storage"]["db_path"]).expanduser().resolve())
    init_db(db_path)


def get_db_path(cfg: dict) -> Path:
    return Path(cfg["storage"]["db_path"]).expanduser().resolve()


def db(cfg: dict) -> str:
    return str(get_db_path(cfg))


# ── Helpers ───────────────────────────────────────
def flash_redirect(url: str, message: str, msg_type: str = "success") -> RedirectResponse:
    return RedirectResponse(f"{url}?message={message}&msg_type={msg_type}", status_code=303)


def get_flash(request: Request) -> dict:
    return {
        "message": request.query_params.get("message"),
        "msg_type": request.query_params.get("msg_type", "success"),
    }


INVOICE_FIELDS = [
    "invoice_number", "invoice_code", "invoice_date",
    "commodity_name", "specification_model", "category",
    "buyer_name", "buyer_tax_num", "seller_name", "seller_tax_num",
    "amount_with_tax", "tax_amount", "tax_rate",
    "belong_project", "belong_person", "remark",
]


def build_filters(request: Request) -> dict:
    f = {}
    for key in ("date_from", "date_to", "seller", "buyer", "project", "person"):
        val = request.query_params.get(key)
        if val:
            f[key] = val
    return f


# ── Routes ────────────────────────────────────────

@app.get("/")
def root():
    return RedirectResponse("/list", status_code=303)


@app.get("/scan")
def get_scan(request: Request):
    ctx = get_flash(request)
    ctx.update({"page": "scan", "results": None, "summary": None})
    return templates.TemplateResponse(request, "scan.html", ctx)


@app.post("/scan")
async def post_scan(request: Request, files: list[UploadFile] = File(...)):
    cfg = request.app.state.config
    proc = InvoiceProcessor(cfg)
    results = []

    for f in files:
        safe_name = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{f.filename or 'upload'}"
        tmp = Path(tempfile.gettempdir()) / safe_name
        content = await f.read()
        with open(tmp, "wb") as fp:
            fp.write(content)

        r = proc.process_file(tmp, source="web")
        results.append({
            "id": r.get("id", "?") if r else "?",
            "filename": f.filename or "-",
            "ok": r is not None,
            "invoice_number": r.get("invoice_number", "-") if r else "-",
            "invoice_date": r.get("invoice_date", "-") if r else "-",
            "seller_name": r.get("seller_name", "-") if r else "-",
            "amount_with_tax": r.get("amount_with_tax", 0) if r else 0,
        })
        if tmp.exists():
            tmp.unlink()

    ok_count = sum(1 for r in results if r["ok"])
    ctx = get_flash(request)
    ctx.update({
        "page": "scan",
        "results": results,
        "summary": {"ok_count": ok_count, "total_count": len(results)},
    })
    return templates.TemplateResponse(request, "scan.html", ctx)


@app.get("/list")
def get_list(request: Request, search: str = "", status: list[str] = Query(default=["正常"])):
    cfg = request.app.state.config
    invoices = get_all_invoices(db(cfg))
    invoices.sort(key=lambda i: i.get("invoice_date") or "", reverse=True)

    show_normal = "正常" in status
    show_excluded = "排除" in status
    if show_normal and not show_excluded:
        invoices = [i for i in invoices if not i.get("excluded")]
    elif show_excluded and not show_normal:
        invoices = [i for i in invoices if i.get("excluded")]
    elif not show_normal and not show_excluded:
        invoices = []

    search_lower = search.strip().lower()
    if search_lower:
        invoices = [
            i for i in invoices
            if (search_lower in (i.get("seller_name") or "").lower()
                or search_lower in (i.get("buyer_name") or "").lower()
                or search_lower in (i.get("invoice_number") or "").lower()
                or search_lower in (i.get("commodity_name") or "").lower())
        ]

    all_invs = get_all_invoices(db(cfg))
    total = len(all_invs)
    ok = sum(1 for i in all_invs if not i.get("excluded"))
    excluded = total - ok
    reimbursable = sum(i.get("amount_with_tax") or 0 for i in all_invs if not i.get("excluded"))
    total_amount = sum(i.get("amount_with_tax") or 0 for i in all_invs)

    ctx = get_flash(request)
    ctx.update({
        "page": "list",
        "invoices": invoices,
        "search": search, "status_filter": status,
        "stats": {
            "total": total, "ok_count": ok, "excluded_count": excluded,
            "reimbursable_amount": reimbursable, "total_amount": total_amount,
        },
    })
    return templates.TemplateResponse(request, "list.html", ctx)


@app.post("/list/batch-toggle")
def batch_toggle(request: Request, ids: list[int] = Form(...), action: str = Form(...)):
    cfg = request.app.state.config
    excluded = action == "exclude"
    for inv_id in ids:
        update_invoice_status(db(cfg), inv_id, excluded=excluded)
    label = "已排除" if excluded else "已恢复"
    return flash_redirect("/list", f"批量操作完成: {len(ids)} 张发票{label}")


@app.get("/list/{inv_id}")
def get_edit(request: Request, inv_id: int):
    cfg = request.app.state.config
    inv = get_invoice_by_id(db(cfg), inv_id)
    if not inv:
        raise HTTPException(404, "发票不存在")
    attachments = get_attachments(db(cfg), inv_id)
    ctx = get_flash(request)
    ctx.update({
        "page": "list",
        "invoice": dict(inv),
        "attachments": attachments,
        "raw_json": json.dumps(dict(inv), ensure_ascii=False, indent=2, default=str),
    })
    return templates.TemplateResponse(request, "edit.html", ctx)


@app.post("/list/{inv_id}")
async def post_edit(request: Request, inv_id: int):
    cfg = request.app.state.config
    form = await request.form()
    updates = {}
    for field in INVOICE_FIELDS:
        if field in form:
            val = form[field]
            if field in ("amount_with_tax", "tax_amount", "tax_rate"):
                try:
                    updates[field] = float(val)
                except (ValueError, TypeError):
                    updates[field] = 0.0
            else:
                updates[field] = str(val)
    update_invoice(db(cfg), inv_id, updates)
    return flash_redirect(f"/list/{inv_id}", "保存成功")


@app.post("/list/{inv_id}/toggle")
def toggle_status(request: Request, inv_id: int):
    cfg = request.app.state.config
    inv = get_invoice_by_id(db(cfg), inv_id)
    if not inv:
        raise HTTPException(404)
    new_status = not inv.get("excluded")
    update_invoice_status(db(cfg), inv_id, excluded=new_status)
    label = "已排除" if new_status else "已恢复"
    return flash_redirect(f"/list/{inv_id}", f"发票 #{inv_id} {label}")


@app.post("/list/{inv_id}/delete")
def delete_invoice_route(request: Request, inv_id: int):
    cfg = request.app.state.config
    inv = get_invoice_by_id(db(cfg), inv_id)
    if not inv:
        raise HTTPException(404)

    for att in get_attachments(db(cfg), inv_id):
        p = Path(att["stored_path"])
        if p.exists():
            p.unlink()

    stored = inv.get("stored_path")
    if stored:
        p = Path(stored)
        if p.exists():
            p.unlink()
        parent = p.parent
        try:
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
        except OSError:
            pass

    delete_invoice(db(cfg), inv_id)
    return flash_redirect("/list", f"发票 #{inv_id} 已删除")


@app.post("/list/{inv_id}/attachments")
async def upload_attachments(request: Request, inv_id: int,
                              files: list[UploadFile] = File(...),
                              file_type: str = Form("other")):
    cfg = request.app.state.config
    inv = get_invoice_by_id(db(cfg), inv_id)
    if not inv:
        raise HTTPException(404)

    inv_stored = inv.get("stored_path", "")
    if not inv_stored:
        return flash_redirect(f"/list/{inv_id}",
                              "发票未归档，无法上传附件", "warning")

    seq = next_attachment_seq(inv_stored)
    count = 0
    for uf in files:
        content = await uf.read()
        if not content:
            continue
        ext = Path(uf.filename).suffix.lower() if uf.filename else ".bin"
        dest = build_attachment_path(inv_stored, seq, ext)
        with open(dest, "wb") as fp:
            fp.write(content)
        insert_attachment(db(cfg), {
            "invoice_id": inv_id,
            "filename": dest.name,
            "original_name": uf.filename or dest.name,
            "file_type": file_type,
            "stored_path": str(dest),
            "file_size": len(content),
            "created_at": datetime.now().isoformat(),
        })
        seq += 1
        count += 1

    return flash_redirect(f"/list/{inv_id}", f"上传 {count} 个附件")


@app.post("/list/{inv_id}/attachments/{att_id}/delete")
def delete_attachment_route(request: Request, inv_id: int, att_id: int):
    cfg = request.app.state.config
    atts = get_attachments(db(cfg), inv_id)
    target = next((a for a in atts if a["id"] == att_id), None)
    if target:
        p = Path(target["stored_path"])
        if p.exists():
            p.unlink()
        delete_attachment(db(cfg), att_id)
    return flash_redirect(f"/list/{inv_id}", "附件已删除")


@app.get("/query")
def get_query(request: Request):
    cfg = request.app.state.config
    filters = build_filters(request)
    if request.query_params.get("only_included"):
        filters["only_included"] = True

    results = None
    total_amount = 0.0
    if filters:
        results = query_invoices(db(cfg), filters)
        total_amount = sum(r.get("amount_with_tax") or 0 for r in results)

    ctx = get_flash(request)
    ctx.update({
        "page": "query",
        "results": results,
        "total_amount": total_amount,
        "filters": {
            "date_from": request.query_params.get("date_from", ""),
            "date_to": request.query_params.get("date_to", ""),
            "seller": request.query_params.get("seller", ""),
            "buyer": request.query_params.get("buyer", ""),
            "project": request.query_params.get("project", ""),
            "person": request.query_params.get("person", ""),
            "only_included": request.query_params.get("only_included", ""),
        },
    })
    return templates.TemplateResponse(request, "query.html", ctx)


@app.get("/export")
def get_export(request: Request):
    ctx = get_flash(request)
    ctx.update({
        "page": "export",
        "filters": {"date_from": "", "date_to": "", "seller": "", "buyer": "",
                     "project": "", "person": "", "format": "both"},
        "download_links": None, "invoice_count": None, "total_amount": 0.0,
    })
    return templates.TemplateResponse(request, "export.html", ctx)


@app.post("/export")
async def post_export(request: Request):
    cfg = request.app.state.config
    form = await request.form()

    filters = {}
    for key in ("date_from", "date_to", "seller", "buyer", "project", "person"):
        val = form.get(key, "").strip()
        if val:
            filters[key] = val
    filters["only_included"] = True

    fmt = form.get("format", "both")
    invoices = query_invoices(db(cfg), filters) if filters else []
    total_amount = sum(i.get("amount_with_tax") or 0 for i in invoices)

    export_dir = Path.home() / "Documents" / "发票夹子" / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    label = build_export_label(filters) if filters else "全部"
    download_links = []

    try:
        if fmt in ("excel", "both"):
            excel_path = export_dir / f"报销明细_{label}.xlsx"
            export_excel(invoices, str(excel_path))
            download_links.append({"label": "下载 Excel", "filename": excel_path.name})

        if fmt in ("pdf", "both"):
            pdf_path = export_dir / f"报销发票_{label}.pdf"
            result = export_merged_pdf(invoices, str(pdf_path))
            if result:
                download_links.append({"label": "下载合并 PDF", "filename": pdf_path.name})
    except Exception as e:
        return flash_redirect("/export", f"导出失败: {e}", "error")

    ctx = get_flash(request)
    ctx.update({
        "page": "export",
        "filters": {**filters, "format": fmt},
        "download_links": download_links,
        "invoice_count": len(invoices),
        "total_amount": total_amount,
    })
    return templates.TemplateResponse(request, "export.html", ctx)


@app.get("/export/download/{filename}")
def download_export(filename: str):
    export_dir = Path.home() / "Documents" / "发票夹子" / "exports"
    filepath = export_dir / filename
    if not filepath.resolve().is_relative_to(export_dir.resolve()):
        raise HTTPException(404)
    if not re.match(r'^报销(明细|发票)_.+\.(xlsx|pdf)$', filename):
        raise HTTPException(404)
    if not filepath.exists():
        raise HTTPException(404)
    return FileResponse(filepath, filename=filename)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
