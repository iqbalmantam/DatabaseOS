import io
from datetime import date
from fpdf import FPDF
import pandas as pd
import matplotlib.pyplot as plt
from utils.helper import to_num

def generate_pdf(df):
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)

    pdf.cell(0, 10, "LAPORAN DATABASE KARYAWAN", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(
        0, 6,
        f"Dicetak Tanggal: {date.today().strftime('%d-%m-%Y')} | Total Record: {len(df)}",
        new_x="LMARGIN", new_y="NEXT", align="C"
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(230, 230, 230)

    col_widths = [22, 45, 35, 25, 25, 25, 25, 25, 20, 30]
    headers = ["ID", "Nama Lengkap", "Posisi", "Cost Center", "Tgl Join", "End Kontrak", "Tgl Resign", "Site", "Status", "Updated"]

    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 7, h, border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 7)
    for _, row in df.iterrows():
        pdf.cell(col_widths[0], 6, str(row.get("ID", "")), border=1, align="C")
        pdf.cell(col_widths[1], 6, str(row.get("Nama Lengkap", ""))[:25], border=1)
        pdf.cell(col_widths[2], 6, str(row.get("Posisi", ""))[:20], border=1)
        pdf.cell(col_widths[3], 6, str(row.get("Cost Center", "")), border=1, align="C")
        pdf.cell(col_widths[4], 6, str(row.get("Tanggal Bergabung", "")), border=1, align="C")
        pdf.cell(col_widths[5], 6, str(row.get("Akhir Kontrak", "")), border=1, align="C")
        pdf.cell(col_widths[6], 6, str(row.get("Tanggal Resign", "-")), border=1, align="C")
        pdf.cell(col_widths[7], 6, str(row.get("Site", "")), border=1, align="C")
        pdf.cell(col_widths[8], 6, str(row.get("Status", "Aktif")), border=1, align="C")
        pdf.cell(col_widths[9], 6, str(row.get("Terakhir Diperbarui", "")), border=1, align="C")
        pdf.ln()

    out = pdf.output()
    return bytes(out) if isinstance(out, (str, bytearray)) else out

def generate_manpower_pdf_with_charts(df_filtered, total_hc, total_sal, total_mp, total_pay, top_proj, top_val):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "LAPORAN EXECUTIVE MANPOWER COST", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Dicetak Tanggal: {date.today().strftime('%d-%m-%Y')} | Total Record: {len(df_filtered)}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "1. Executive Summary & Key Metrics", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"- Total Headcount          : {total_hc:,} orang", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"- Total Salary             : Rp {total_sal:,}".replace(",", "."), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"- Total Manpower Cost      : Rp {total_mp:,}".replace(",", "."), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, f"- Total Payment Amount     : Rp {total_pay:,}".replace(",", "."), new_x="LMARGIN", new_y="NEXT")
    if top_proj:
        pdf.cell(0, 6, f"- Top Project Anggaran     : {top_proj} (Rp {top_val:,})".replace(",", "."), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "2. Breakdown Total Payment per Project (Top 10)", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(100, 7, "Nama Project", border=1, align="C", fill=True)
    pdf.cell(45, 7, "Headcount", border=1, align="C", fill=True)
    pdf.cell(45, 7, "Total Payment (Rp)", border=1, align="C", fill=True)
    pdf.ln()
    
    pdf.set_font("Helvetica", "", 8)
    df_temp = df_filtered.copy()
    proj_grp = pd.DataFrame()
    if "Project" in df_temp.columns and "Total Payment Amount" in df_temp.columns:
        df_temp["Parsed_Payment"] = to_num(df_temp["Total Payment Amount"])
        df_temp["Parsed_Overtime"] = to_num(df_temp["Overtime"])
        
        proj_grp = df_temp.groupby("Project").agg(
            HC=("Name", "count"),
            Payment=("Parsed_Payment", "sum")
        ).reset_index().sort_values("Payment", ascending=False).head(10)
        
        for _, r in proj_grp.iterrows():
            pdf.cell(100, 6, str(r["Project"])[:45], border=1)
            pdf.cell(45, 6, f"{r['HC']:,} orang", border=1, align="C")
            pdf.cell(45, 6, f"Rp {int(r['Payment']):,}".replace(",", "."), border=1, align="R")
            pdf.ln()
    
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "3. Visualisasi Dashboard Analytics", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    try:
        df_m = df_temp.groupby("Month")["Parsed_Payment"].sum().reset_index()
        df_m["Month_Dt"] = pd.to_datetime(df_m["Month"], errors="coerce")
        df_m = df_m.sort_values("Month_Dt", ascending=True)
        
        fig_m, ax_m = plt.subplots(figsize=(8, 3.2))
        bars = ax_m.bar(df_m["Month"], df_m["Parsed_Payment"] / 1e9, color="#1F4E79")
        ax_m.set_title("Total Payment Amount per Bulan (Milyar Rp)", fontsize=10, fontweight="bold")
        ax_m.set_ylabel("Milyar Rp")
        for bar in bars:
            yval = bar.get_height()
            ax_m.text(bar.get_x() + bar.get_width()/2, yval, f"{yval:.2f} M", ha="center", va="bottom", fontsize=8)
        
        img_buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(img_buf, format="png", dpi=150)
        plt.close(fig_m)
        
        pdf.image(img_buf, w=180)
        pdf.ln(4)
    except Exception:
        pass

    try:
        if not proj_grp.empty:
            fig_p, ax_p = plt.subplots(figsize=(8, 3.5))
            proj_top = proj_grp.sort_values("Payment", ascending=True)
            bars_p = ax_p.barh(proj_top["Project"], proj_top["Payment"] / 1e6, color="#2CA02C")
            ax_p.set_title("Top 10 Project Berdasarkan Total Payment (Juta Rp)", fontsize=10, fontweight="bold")
            ax_p.set_xlabel("Juta Rp")
            for bar in bars_p:
                xval = bar.get_width()
                ax_p.text(xval, bar.get_y() + bar.get_height()/2, f" {xval:,.0f} Jt", ha="left", va="center", fontsize=7)
            
            img_buf2 = io.BytesIO()
            plt.tight_layout()
            plt.savefig(img_buf2, format="png", dpi=150)
            plt.close(fig_p)
            
            pdf.image(img_buf2, w=180)
            pdf.ln(4)
    except Exception:
        pass

    try:
        if "Work Location" in df_temp.columns and "Month" in df_temp.columns:
            pdf.add_page()
            df_ot = df_temp.groupby(["Work Location", "Month"])["Parsed_Overtime"].sum().unstack().fillna(0)
            month_cols = sorted(df_ot.columns, key=lambda x: pd.to_datetime(x, errors="coerce"))
            df_ot = df_ot[month_cols]
            
            fig_ot, ax_ot = plt.subplots(figsize=(8, 3.5))
            df_ot.plot(kind="bar", ax=ax_ot, colormap="tab10", width=0.7)
            ax_ot.set_title("Perbandingan Overtime Work Location (Compare per Bulan)", fontsize=10, fontweight="bold")
            ax_ot.set_ylabel("Rupiah")
            ax_ot.set_xlabel("Work Location")
            plt.xticks(rotation=20, ha="right", fontsize=8)
            
            img_buf3 = io.BytesIO()
            plt.tight_layout()
            plt.savefig(img_buf3, format="png", dpi=150)
            plt.close(fig_ot)
            
            pdf.image(img_buf3, w=180)
            pdf.ln(4)
    except Exception:
        pass

    try:
        if not proj_grp.empty:
            fig_hc, ax_hc = plt.subplots(figsize=(8, 3.5))
            proj_hc_top = proj_grp.sort_values("HC", ascending=True)
            bars_hc = ax_hc.barh(proj_hc_top["Project"], proj_hc_top["HC"], color="#17BECF")
            ax_hc.set_title("Top 10 Project Berdasarkan Jumlah Headcount", fontsize=10, fontweight="bold")
            ax_hc.set_xlabel("Jumlah Karyawan")
            for bar in bars_hc:
                xval = bar.get_width()
                ax_hc.text(xval, bar.get_y() + bar.get_height()/2, f" {int(xval)} orang", ha="left", va="center", fontsize=7)
            
            img_buf4 = io.BytesIO()
            plt.tight_layout()
            plt.savefig(img_buf4, format="png", dpi=150)
            plt.close(fig_hc)
            
            pdf.image(img_buf4, w=180)
            pdf.ln(4)
    except Exception:
        pass

    try:
        if "Employment Status" in df_temp.columns:
            df_emp_st = df_temp.groupby(["Project", "Employment Status"])["Parsed_Payment"].sum().unstack().fillna(0)
            top_projects = proj_grp["Project"].tolist()
            df_emp_st = df_emp_st.reindex(top_projects).dropna(how="all")
            
            fig_es, ax_es = plt.subplots(figsize=(8, 3.8))
            (df_emp_st / 1e6).plot(kind="bar", ax=ax_es, colormap="Set2", width=0.7)
            ax_es.set_title("Perbandingan Biaya (Total Payment) FDW vs TDW per Project (Juta Rp)", fontsize=10, fontweight="bold")
            ax_es.set_ylabel("Juta Rp")
            ax_es.set_xlabel("Project")
            plt.xticks(rotation=25, ha="right", fontsize=8)
            
            img_buf5 = io.BytesIO()
            plt.tight_layout()
            plt.savefig(img_buf5, format="png", dpi=150)
            plt.close(fig_es)
            
            pdf.image(img_buf5, w=180)
    except Exception:
        pass
    
    out = pdf.output()
    return bytes(out) if isinstance(out, (str, bytearray)) else out
