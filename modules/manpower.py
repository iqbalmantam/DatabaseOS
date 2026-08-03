from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st

from utils.auth import check_manpower_access
from utils.helper import format_rp_short, to_num
from utils.pdf import generate_manpower_pdf_with_charts
from utils.charts import plot_manpower_trend
from services.gsheet import load_manpower_cost_data, save_manpower_data

MANPOWER_COST_HEADERS = [
    "Month", "Invoice No", "Name", "Employee ID (by Vendor)", "Cost Center Name",
    "Department", "Work Location", "Job Position", "Type", "Gender", "Contract",
    "Employment Status", "Project", "Basic Salary", "Meals & Transp", "Overtime",
    "Position", "Skill", "Other", "Shortage", "Deduction", "Total Salary", "BPJS",
    "Management Fee", "Total Manpower Cost", "Grand Total", "CJI", "KHQ Report",
    "PPN", "PPH23", "Total Payment Amount",
]

def render_page(is_admin):
    if not check_manpower_access():
        st.stop()

    col_mc_head, col_mc_lock = st.columns([4, 1])
    with col_mc_head:
        st.title("💳 Manpower Cost Manager")
        st.caption("Modul Pengelolaan Biaya Tenaga Kerja (Manpower Cost), PPN/PPh 23, & Invoice Detail.")
    with col_mc_lock:
        st.write("")
        if st.button("🔒 Kunci Modul", use_container_width=True, help="Keluar dan kunci kembali halaman ini"):
            st.session_state["manpower_authenticated"] = False
            st.rerun()

    if "df_manpower_cost" not in st.session_state or st.sidebar.button("🔄 Refresh Data Manpower Cost"):
        st.session_state.df_manpower_cost = load_manpower_cost_data(MANPOWER_COST_HEADERS)

    df_mc = st.session_state.df_manpower_cost

    if is_admin:
        with st.expander("📥 **Upload / Import File Manpower Cost**", expanded=False):
            st.info("Upload file Excel/CSV Manpower Cost bulanan untuk disimpan ke Google Sheets.")
            mc_file = st.file_uploader("Pilih File Excel/CSV Manpower Cost:", type=["xlsx", "xls", "csv"], key="mc_uploader")
            if mc_file is not None and st.button("🚀 Simpan Data Manpower Cost ke Sheets"):
                try:
                    if mc_file.name.endswith(".csv"):
                        df_mc_upload = pd.read_csv(mc_file)
                    else:
                        df_mc_upload = pd.read_excel(mc_file)

                    df_mc_upload.columns = [str(c).strip() for c in df_mc_upload.columns]

                    for col in MANPOWER_COST_HEADERS:
                        if col not in df_mc_upload.columns:
                            df_mc_upload[col] = ""

                    df_mc_upload = df_mc_upload[MANPOWER_COST_HEADERS]
                    df_mc_old = load_manpower_cost_data(MANPOWER_COST_HEADERS)
                    updated_mc = pd.concat([df_mc_old, df_mc_upload], ignore_index=True)

                    save_manpower_data(updated_mc)
                    st.session_state.df_manpower_cost = updated_mc.fillna("")
                    st.success(f"✅ Berhasil mengimpor {len(df_mc_upload)} baris data Manpower Cost!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal memproses file: {e}")

    st.divider()
    if df_mc.empty:
        st.info("Sheet `Manpower_Cost` masih kosong. Silakan upload file terlebih dahulu.")
        st.dataframe(pd.DataFrame(columns=MANPOWER_COST_HEADERS), use_container_width=True)
    else:
        df_mc_clean = df_mc.fillna("").astype(str)

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            months = sorted([x.strip() for x in df_mc_clean["Month"].unique() if x.strip() != "" and x.strip().lower() != "nan"])
            selected_months = st.multiselect("Filter Bulan (Month):", options=months, default=months)
        with col_f2:
            projects = sorted([x.strip() for x in df_mc_clean["Project"].unique() if x.strip() != "" and x.strip().lower() != "nan"])
            selected_project = st.multiselect("Filter Project:", options=projects, default=projects)
        with col_f3:
            locations = sorted([x.strip() for x in df_mc_clean["Work Location"].unique() if x.strip() != "" and x.strip().lower() != "nan"])
            selected_location = st.multiselect("Filter Work Location:", options=locations, default=locations)

        filtered_mc = df_mc_clean.copy()
        if selected_months:
            filtered_mc = filtered_mc[filtered_mc["Month"].str.strip().isin(selected_months)]
        if selected_project:
            filtered_mc = filtered_mc[filtered_mc["Project"].str.strip().isin(selected_project)]
        if selected_location:
            filtered_mc = filtered_mc[filtered_mc["Work Location"].str.strip().isin(selected_location)]

        total_headcount = len(filtered_mc)
        total_salary = int(round(to_num(filtered_mc["Total Salary"]).astype(float).sum()))
        total_mp_cost = int(round(to_num(filtered_mc["Total Manpower Cost"]).astype(float).sum()))
        total_payment = int(round(to_num(filtered_mc["Total Payment Amount"]).astype(float).sum()))

        km1, km2, km3, km4 = st.columns(4)
        km1.metric("Total Headcount", f"{total_headcount:,}")
        km2.metric("Total Salary", f"Rp {total_salary:,}".replace(",", "."))
        km3.metric("Total Manpower Cost", f"Rp {total_mp_cost:,}".replace(",", "."))
        km4.metric("Total Payment Amount", f"Rp {total_payment:,}".replace(",", "."))

        with st.expander("📊 **Dashboard Analytics & Sebaran Biaya Manpower**", expanded=True):
            df_chart = filtered_mc.copy()
            df_chart["Parsed_Payment"] = to_num(df_chart["Total Payment Amount"])
            df_chart["Parsed_Salary"] = to_num(df_chart["Total Salary"])
            df_chart["Parsed_Overtime"] = to_num(df_chart["Overtime"])

            top_proj_name = ""
            top_proj_val = 0
            if not df_chart.empty:
                top_proj_name = df_chart.groupby("Project")["Parsed_Payment"].sum().idxmax()
                top_proj_val = df_chart.groupby("Project")["Parsed_Payment"].sum().max()
                formatted_top_val = f"Rp {int(top_proj_val):,}".replace(",", ".")
                st.info(f"💡 **Ringkasan Eksekutif:** Anggaran total payment terbesar saat ini dipegang oleh project **{top_proj_name}** dengan nilai sebesar **{formatted_top_val}**.")

            gc1, gc2 = st.columns(2)
            with gc1:
                trend_month = df_chart.groupby("Month")["Parsed_Payment"].sum().reset_index()
                trend_month["Month_Dt"] = pd.to_datetime(trend_month["Month"], errors="coerce")
                trend_month = trend_month.sort_values(by="Month_Dt", ascending=True)
                trend_month["Text_Format"] = trend_month["Parsed_Payment"].apply(format_rp_short)

                fig_trend = plot_manpower_trend(trend_month)
                st.plotly_chart(fig_trend, use_container_width=True)

            with gc2:
                top_cost_proj = df_chart.groupby("Project")["Parsed_Payment"].sum().nlargest(10).reset_index()
                top_cost_proj["Text_Format"] = top_cost_proj["Parsed_Payment"].apply(format_rp_short)

                fig_proj_cost = px.bar(
                    top_cost_proj,
                    x="Parsed_Payment",
                    y="Project",
                    orientation="h",
                    title="Top 10 Project Berdasarkan Total Payment",
                    text="Text_Format",
                    color="Parsed_Payment",
                    color_continuous_scale="Viridis",
                )
                fig_proj_cost.update_traces(textangle=0, textposition="outside", hovertemplate="<b>Project:</b> %{y}<br><b>Total Payment:</b> Rp %{x:,.0f}<extra></extra>")
                fig_proj_cost.update_layout(yaxis={"categoryorder": "total ascending"}, xaxis_title="Total Payment (Rp)", yaxis_title="Project")
                st.plotly_chart(fig_proj_cost, use_container_width=True)

            gc_ot, gc4 = st.columns(2)
            with gc_ot:
                df_ot_loc_month = df_chart.groupby(["Work Location", "Month"])["Parsed_Overtime"].sum().reset_index()
                df_ot_loc_month["Text_Format"] = df_ot_loc_month["Parsed_Overtime"].apply(format_rp_short)

                fig_ot_loc = px.bar(
                    df_ot_loc_month,
                    x="Work Location",
                    y="Parsed_Overtime",
                    color="Month",
                    barmode="group",
                    title="Perbandingan Overtime Work Location (Compare per Bulan)",
                    text="Text_Format",
                )
                fig_ot_loc.update_traces(textangle=0, textposition="outside", hovertemplate="<b>Location:</b> %{x}<br><b>Overtime:</b> Rp %{y:,.0f}<extra></extra>")
                fig_ot_loc.update_layout(xaxis_title="Work Location", yaxis_title="Total Overtime (Rp)", xaxis_tickangle=-25)
                st.plotly_chart(fig_ot_loc, use_container_width=True)

            with gc4:
                top_hc = df_chart.groupby("Project")["Name"].count().nlargest(10).reset_index(name="Headcount")
                fig_hc = px.bar(
                    top_hc,
                    x="Headcount",
                    y="Project",
                    orientation="h",
                    title="Top 10 Project Berdasarkan Jumlah Headcount",
                    text_auto=True,
                    color="Headcount",
                    color_continuous_scale="Teal",
                )
                fig_hc.update_traces(textangle=0)
                fig_hc.update_layout(yaxis={"categoryorder": "total ascending"}, xaxis_title="Jumlah Karyawan", yaxis_title="Project")
                st.plotly_chart(fig_hc, use_container_width=True)

            gc3, gc_emp = st.columns(2)
            with gc3:
                top_projects_list = df_chart.groupby("Project")["Parsed_Payment"].sum().nlargest(8).index
                df_proj_month = df_chart[df_chart["Project"].isin(top_projects_list)].groupby(["Project", "Month"])["Parsed_Payment"].sum().reset_index()
                df_proj_month["Text_Format"] = df_proj_month["Parsed_Payment"].apply(format_rp_short)

                fig_proj_month = px.bar(
                    df_proj_month,
                    x="Project",
                    y="Parsed_Payment",
                    color="Month",
                    barmode="group",
                    title="Perbandingan Biaya Project (Compare per Bulan)",
                    text="Text_Format",
                )
                fig_proj_month.update_traces(textangle=0, textposition="outside", hovertemplate="<b>Project:</b> %{x}<br><b>Total Payment:</b> Rp %{y:,.0f}<extra></extra>")
                fig_proj_month.update_layout(xaxis_title="Project", yaxis_title="Total Payment (Rp)", xaxis_tickangle=-25)
                st.plotly_chart(fig_proj_month, use_container_width=True)

            with gc_emp:
                if "Employment Status" in df_chart.columns and "Project" in df_chart.columns:
                    df_emp_chart = df_chart.copy()
                    df_emp_chart["Employment Status Clean"] = df_emp_chart["Employment Status"].astype(str).str.strip().str.upper().replace("", "BELUM DIISI")
                    top_emp_projects = df_emp_chart.groupby("Project")["Parsed_Payment"].sum().nlargest(8).index

                    df_stat_proj = df_emp_chart[df_emp_chart["Project"].isin(top_emp_projects)].groupby(["Project", "Employment Status Clean"])["Parsed_Payment"].sum().reset_index()
                    df_stat_proj["Text_Format"] = df_stat_proj["Parsed_Payment"].apply(format_rp_short)

                    fig_stat_proj = px.bar(
                        df_stat_proj,
                        x="Project",
                        y="Parsed_Payment",
                        color="Employment Status Clean",
                        barmode="group",
                        title="Perbandingan Biaya (Total Payment) FDW vs TDW per Project",
                        text="Text_Format",
                        color_discrete_sequence=px.colors.qualitative.Bold,
                    )
                    fig_stat_proj.update_traces(
                        textangle=0,
                        textposition="outside",
                        textfont=dict(size=11),
                        cliponaxis=False,
                        hovertemplate="<b>Project:</b> %{x}<br><b>Status:</b> %{fullData.name}<br><b>Total Payment:</b> Rp %{y:,.0f}<extra></extra>",
                    )
                    fig_stat_proj.update_layout(xaxis_title="Project", yaxis_title="Total Payment (Rp)", xaxis_tickangle=-25, legend_title_text="Employment Status", margin=dict(t=60, b=50))
                    st.plotly_chart(fig_stat_proj, use_container_width=True)

            st.divider()

            pdf_bytes_full = generate_manpower_pdf_with_charts(
                filtered_mc, total_headcount, total_salary, total_mp_cost, total_payment, top_proj_name, int(top_proj_val)
            )
            st.download_button(
                label="📄 Generate & Download Laporan PDF (Termasuk Grafik)",
                data=pdf_bytes_full,
                file_name=f"Laporan_Manpower_Cost_Lengkap_{date.today().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        with st.expander("🔍 Cek Detail / Baris Angka Total Payment Amount", expanded=False):
            st.caption("Gunakan tabel ini untuk memastikan apakah ada baris yang bernilai 0 atau salah format.")
            debug_df = filtered_mc[["Month", "Project", "Name", "Total Payment Amount"]].copy()
            debug_df["Parsed Numeric"] = to_num(filtered_mc["Total Payment Amount"])
            st.dataframe(debug_df, use_container_width=True)

        display_matrix = filtered_mc.copy()
        financial_cols = [
            "Basic Salary", "Meals & Transp", "Overtime", "Position", "Skill",
            "Other", "Shortage", "Deduction", "Total Salary", "BPJS",
            "Management Fee", "Total Manpower Cost", "Grand Total", "CJI",
            "KHQ Report", "PPN", "PPH23", "Total Payment Amount",
        ]

        for col in financial_cols:
            if col in display_matrix.columns:
                display_matrix[col] = display_matrix[col].apply(
                    lambda x: f"{int(round(to_num(pd.Series([x])).iloc[0])):,}".replace(",", ".")
                    if str(x).strip() not in ["", "nan", "none", "-"] else ""
                )

        st.subheader("📋 Data Manpower Cost Matrix")
        st.dataframe(display_matrix, use_container_width=True, height=450)

        st.download_button(
            label="📊 Download Data Manpower Cost (CSV)",
            data=filtered_mc.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"Manpower_Cost_Export_{date.today().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
