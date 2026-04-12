#!/usr/bin/env python3
"""发票夹子 Web UI - Streamlit版本 (v2.0 重构版)"""
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import yaml
import tempfile

st.set_page_config(page_title="发票夹子", page_icon="📎", layout="wide")

# ─────────────────────────────────────────────────────────
# 配置加载
# ─────────────────────────────────────────────────────────
@st.cache_resource
def load_config():
    cfg = Path(__file__).parent / "config" / "config.yaml"
    if not cfg.exists():
        st.error("配置文件不存在，请先配置 config.yaml")
        st.stop()
    with open(cfg, encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_db_path(cfg):
    return Path(cfg["storage"]["db_path"]).expanduser().resolve()

def get_invoice_count(cfg):
    invs = load_invoices(cfg, {"only_included": False})
    total = len(invs)
    reimbursable = sum(1 for i in invs if not i.get("excluded"))
    return total, reimbursable, total - reimbursable

@st.cache_data(ttl=30)
def load_invoices(cfg, filters=None):
    from invoice_clipper.database import query_invoices as _q
    return _q(str(get_db_path(cfg)), filters or {})

def sidebar_nav():
    st.sidebar.title("📎 发票夹子")
    st.sidebar.markdown("---")
    page = st.sidebar.radio("功能菜单",
        ["📤 扫描发票", "📋 发票列表", "🔍 查询筛选", "📥 导出报销"],
        label_visibility="collapsed")
    st.sidebar.markdown("---")
    st.sidebar.caption("v2.0 | 发票管理专用")
    return page

# ─────────────────────────────────────────────────────────
# 扫描页
# ─────────────────────────────────────────────────────────
def page_scan(cfg):
    st.header("📤 扫描发票")
    st.markdown("上传 PDF 或图片文件，自动识别发票信息（百度OCR → LLM 两级识别）。")

    files = st.file_uploader(
        "拖拽文件到此处，或点击选择",
        type=["pdf", "png", "jpg", "jpeg", "bmp", "tiff", "ofd"],
        accept_multiple_files=True)

    if not files:
        return

    st.markdown("---")
    st.subheader("识别结果")
    from invoice_clipper.processor import InvoiceProcessor
    proc = InvoiceProcessor(cfg)
    results = []
    bar = st.progress(0)
    status_text = st.empty()

    for idx, f in enumerate(files):
        bar.progress((idx + 1) / len(files))
        status_text.text(f"正在处理: {f.name}")
        tmp_dir = Path(tempfile.gettempdir())
        safe_name = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{f.name}"
        tmp = tmp_dir / safe_name

        with open(tmp, "wb") as fp:
            fp.write(f.getvalue())

        r = proc.process_file(tmp, source="web")
        if r:
            results.append({
                "ID": r.get("id", "?"),
                "文件名": f.name,
                "状态": "✅ 成功",
                "发票号码": r.get("invoice_number", "-"),
                "开票日期": r.get("invoice_date", "-"),
                "销售方": r.get("seller_name", "-"),
                "价税合计": f"¥{r.get('amount_with_tax', 0):,.2f}",
            })
        else:
            results.append({
                "ID": "-", "文件名": f.name, "状态": "❌ 失败",
                "发票号码": "-", "开票日期": "-", "销售方": "-",
                "价税合计": "-",
            })
        if tmp.exists():
            tmp.unlink()

    bar.empty()
    status_text.empty()

    if not results:
        return

    for r in results:
        with st.expander(
            f"{r['状态']} | {r['文件名']} | 发票号码: {r['发票号码']} | 金额: {r['价税合计']}",
            expanded=(r["状态"] == "❌ 失败")):
            st.json(r)

    ok = sum(1 for r in results if r["状态"] == "✅ 成功")
    st.success(f"处理完成：{ok}/{len(results)} 张识别成功")

# ─────────────────────────────────────────────────────────
# 列表页
# ─────────────────────────────────────────────────────────
def page_list(cfg):
    st.header("📋 发票列表")
    invs_all = load_invoices(cfg, {"only_included": False})
    if not invs_all:
        st.info("暂无发票记录，请先扫描发票")
        return

    invs_ok = [i for i in invs_all if not i.get("excluded")]
    invs_ex = [i for i in invs_all if i.get("excluded")]

    total_amount = sum(i.get("amount_with_tax", 0) for i in invs_all)
    reimbursable_amount = sum(i.get("amount_with_tax", 0) for i in invs_ok)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总发票数", f"{len(invs_all)} 张")
    c2.metric("可报销", f"{len(invs_ok)} 张")
    c3.metric("已排除", f"{len(invs_ex)} 张")
    c4.metric("可报销金额", f"¥{reimbursable_amount:,.2f}",
              delta=f"总金额 ¥{total_amount:,.2f}")

    st.markdown("---")
    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        filt = st.multiselect("状态筛选", ["✅ 正常", "❌ 排除"],
                              default=["✅ 正常"], key="list_filt")
    with c2:
        search = st.text_input("搜索销售方 / 购买方 / 发票号码", placeholder="输入关键词...", key="list_search")
    with c3:
        st.write("")
        st.write("")

    # 构建展示数据
    data = []
    for i in invs_all:
        data.append({
            "ID": i.get("id"),
            "开票日期": i.get("invoice_date", ""),
            "发票号码": i.get("invoice_number", ""),
            "项目名称": i.get("commodity_name", ""),          # 新增
            "规格型号": i.get("specification_model", ""),     # 新增
            "销售方": i.get("seller_name", ""),
            "购买方": i.get("buyer_name", ""),
            "价税合计": i.get("amount_with_tax", 0),
            "税额": i.get("tax_amount", 0),
            "归属项目": i.get("belong_project", ""),
            "归属人": i.get("belong_person", ""),
            "备注": i.get("remark", ""),
            "状态": "❌ 排除" if i.get("excluded") else "✅ 正常",
        })

    df = pd.DataFrame(data)

    # 过滤
    fd = df.copy()
    if "✅ 正常" not in filt and "❌ 排除" not in filt:
        fd = fd.iloc[:0]
    elif len(filt) == 1:
        fd = fd[fd["状态"] == filt[0]]
    if search:
        fd = fd[
            fd["销售方"].str.contains(search, case=False, na=False) |
            fd["购买方"].str.contains(search, case=False, na=False) |
            fd["发票号码"].str.contains(search, case=False, na=False)
        ]

    st.dataframe(
        fd.drop(columns=["ID"]),
        use_container_width=True, hide_index=True,
        column_config={
            "价税合计": st.column_config.NumberColumn(format="¥%.2f"),
            "税额": st.column_config.NumberColumn(format="¥%.2f"),
        })

    # ── 发票详情编辑 ──────────────────────────────────────
    if not fd.empty:
        st.markdown("---")
        st.subheader("📄 发票详情与编辑")
        selected_id = st.selectbox(
            "选择发票 ID 查看/编辑",
            options=fd["ID"].tolist(),
            format_func=lambda x: f"#{x} - {fd[fd['ID']==x]['发票号码'].values[0]} - "
                                  f"¥{fd[fd['ID']==x]['价税合计'].values[0]:,.2f}",
            key="detail_select")
        if selected_id:
            inv = next((i for i in invs_all if i.get("id") == selected_id), None)
            if inv:
                col1, col2, col3= st.columns(3)
                with col1:
                    inv_num = st.text_input("发票号码", value=inv.get("invoice_number", ""))
                    inv_code = st.text_input("发票代码", value=inv.get("invoice_code", ""))
                    inv_date = st.text_input("开票日期", value=inv.get("invoice_date", ""))
                    commodity = st.text_input("项目名称", value=inv.get("commodity_name", ""))
                    spec = st.text_input("规格型号", value=inv.get("specification_model", ""))
                    category = st.text_input("分类", value=inv.get("category", ""))
                with col2:
                    buyer_name = st.text_input("购买方名称", value=inv.get("buyer_name", ""))
                    buyer_tax = st.text_input("购买方税号", value=inv.get("buyer_tax_num", ""))
                    seller_name = st.text_input("销售方名称", value=inv.get("seller_name", ""))
                    seller_tax = st.text_input("销售方税号", value=inv.get("seller_tax_num", ""))

                with col3:
                    amount = st.number_input("价税合计", value=float(inv.get("amount_with_tax", 0)), format="%.2f")
                    tax = st.number_input("税额", value=float(inv.get("tax_amount", 0)), format="%.2f")
                    tax_rate = st.number_input("税率 (小数)", value=float(inv.get("tax_rate") or 0), format="%.4f")
                    belong_project = st.text_input("归属项目", value=inv.get("belong_project", ""))
                    belong_person = st.text_input("归属人", value=inv.get("belong_person", ""))
                    remark = st.text_input("备注", value=inv.get("remark", ""))

                if st.button("💾 保存修改", use_container_width=True):
                    from invoice_clipper.database import update_invoice
                    updates = {
                        "invoice_number": inv_num,
                        "invoice_code": inv_code,
                        "invoice_date": inv_date,
                        "commodity_name": commodity,
                        "specification_model": spec,
                        "buyer_name": buyer_name,
                        "buyer_tax_num": buyer_tax,
                        "seller_name": seller_name,
                        "seller_tax_num": seller_tax,
                        "amount_with_tax": amount,
                        "tax_amount": tax,
                        "tax_rate": tax_rate,
                        "category": category,
                        "belong_project": belong_project,
                        "belong_person": belong_person,
                        "remark": remark,
                    }
                    update_invoice(str(get_db_path(cfg)), int(selected_id), updates)
                    st.success("修改已保存")
                    st.rerun()

                with st.expander("📦 原始数据（JSON）"):
                    st.json(inv)

    # ── 批量操作 ───────────────────────────────────────
    st.markdown("---")
    st.subheader("批量操作")
    c1, c2 = st.columns(2)
    with c1:
        ids = st.multiselect("选择发票 ID",
            options=df["ID"].tolist(),
            format_func=lambda x: f"#{x}",
            key="batch_ids")
    cc1, cc2 = st.columns(2)
    with cc1:
        if st.button("🚫 标记为排除", use_container_width=True) and ids:
            from invoice_clipper.database import update_invoice_status
            for i in ids:
                update_invoice_status(str(get_db_path(cfg)), int(i), excluded=True)
            st.success(f"已排除 {len(ids)} 张发票")
            st.rerun()
    with cc2:
        if st.button("✅ 恢复为正常", use_container_width=True) and ids:
            from invoice_clipper.database import update_invoice_status
            for i in ids:
                update_invoice_status(str(get_db_path(cfg)), int(i), excluded=False)
            st.success(f"已恢复 {len(ids)} 张发票")
            st.rerun()

# ─────────────────────────────────────────────────────────
# 查询页
# ─────────────────────────────────────────────────────────
def page_query(cfg):
    st.header("🔍 查询筛选")
    c1, c2 = st.columns(2)
    with c1:
        d1 = st.date_input("开始日期", value=None, key="q_date_from")
    with c2:
        d2 = st.date_input("结束日期", value=None, key="q_date_to")
    c1, c2 = st.columns(2)
    with c1:
        seller = st.text_input("销售方名称", placeholder="输入销售方关键词...", key="q_seller")
    with c2:
        buyer = st.text_input("购买方名称", placeholder="输入购买方关键词...", key="q_buyer")
    c1, c2 = st.columns(2)
    with c1:
        project = st.text_input("归属项目", placeholder="精确匹配", key="q_project")
    with c2:
        person = st.text_input("归属人", placeholder="精确匹配", key="q_person")
    only = st.checkbox("只显示可报销发票", value=True, key="qry_only")

    if st.button("🔍 查询", type="primary", use_container_width=True):
        filters = {
            "date_from": d1.strftime("%Y-%m-%d") if d1 else None,
            "date_to": d2.strftime("%Y-%m-%d") if d2 else None,
            "seller": seller if seller else None,
            "buyer": buyer if buyer else None,
            "project": project if project else None,
            "person": person if person else None,
            "only_included": only,
        }
        invs = load_invoices(cfg, filters)
        if not invs:
            st.warning("没有找到符合条件的发票")
            return

        data = [{
            "ID": i.get("id"),
            "开票日期": i.get("invoice_date", ""),
            "发票号码": i.get("invoice_number", ""),
            "项目名称": i.get("commodity_name", ""),
            "规格型号": i.get("specification_model", ""),
            "销售方": i.get("seller_name", ""),
            "购买方": i.get("buyer_name", ""),
            "价税合计": i.get("amount_with_tax", 0),
            "归属项目": i.get("belong_project", ""),
            "归属人": i.get("belong_person", ""),
            "状态": "❌ 排除" if i.get("excluded") else "✅ 正常",
        } for i in invs]
        df = pd.DataFrame(data)
        total = df[df['状态'] == '✅ 正常']['价税合计'].sum()
        st.success(f"找到 {len(df)} 张发票，可报销合计 ¥{total:,.2f}")
        st.dataframe(df.drop(columns=["ID"]),
            use_container_width=True, hide_index=True,
            column_config={"价税合计": st.column_config.NumberColumn(format="¥%.2f")})

# ─────────────────────────────────────────────────────────
# 导出页
# ─────────────────────────────────────────────────────────
def page_export(cfg):
    st.header("📥 导出报销")
    st.markdown("选择筛选条件，一键导出 Excel 明细表和 PDF 报销包。")
    st.subheader("筛选条件")
    c1, c2 = st.columns(2)
    with c1:
        d1 = st.date_input("开始日期", value=None, key="efrom")
    with c2:
        d2 = st.date_input("结束日期", value=None, key="eto")
    c1, c2 = st.columns(2)
    with c1:
        seller = st.text_input("销售方名称", placeholder="可选", key="eseller")
    with c2:
        buyer = st.text_input("购买方名称", placeholder="可选", key="ebuyer")
    c1, c2 = st.columns(2)
    with c1:
        project = st.text_input("归属项目", placeholder="可选", key="eproject")
    with c2:
        person = st.text_input("归属人", placeholder="可选", key="eperson")
    fmt = st.radio("导出格式", ["Excel + PDF", "仅 Excel", "仅 PDF"], horizontal=True)

    st.markdown("---")
    st.subheader("预览")
    filters = {
        "date_from": d1.strftime("%Y-%m-%d") if d1 else None,
        "date_to": d2.strftime("%Y-%m-%d") if d2 else None,
        "seller": seller if seller else None,
        "buyer": buyer if buyer else None,
        "project": project if project else None,
        "person": person if person else None,
        "only_included": True,
    }
    invs = load_invoices(cfg, filters)
    if not invs:
        st.warning("没有符合条件的发票")
        return
    total = sum(i.get("amount_with_tax", 0) for i in invs)
    st.info(f"将导出 {len(invs)} 张发票，可报销合计 ¥{total:,.2f}")

    if st.button("📥 开始导出", type="primary", use_container_width=True):
        from invoice_clipper.exporter import export_excel, export_merged_pdf, build_export_label
        edir = Path.home() / "Documents" / "发票夹子" / "exports"
        edir.mkdir(parents=True, exist_ok=True)
        label = build_export_label(filters)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = []
        if fmt in ["Excel + PDF", "仅 Excel"]:
            xlpath = edir / f"报销明细_{label}_{ts}.xlsx"
            export_excel(invs, xlpath)
            results.append(("Excel 明细表", xlpath))
        if fmt in ["Excel + PDF", "仅 PDF"]:
            pdfpath = edir / f"报销发票_{label}_{ts}.pdf"
            r = export_merged_pdf(invs, pdfpath)
            if r:
                results.append(("PDF 报销包", pdfpath))
        st.success("导出完成！")
        for name, path in results:
            with open(path, "rb") as f:
                st.download_button(
                    label=f"下载 {name}", data=f.read(),
                    file_name=path.name, mime="application/octet-stream",
                    use_container_width=True)

# ─────────────────────────────────────────────────────────
# 主函数
# ─────────────────────────────────────────────────────────
def main():
    cfg = load_config()
    page = sidebar_nav()
    if page == "📤 扫描发票":
        page_scan(cfg)
    elif page == "📋 发票列表":
        page_list(cfg)
    elif page == "🔍 查询筛选":
        page_query(cfg)
    elif page == "📥 导出报销":
        page_export(cfg)

if __name__ == "__main__":
    main()