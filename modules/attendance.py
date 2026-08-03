import pandas as pd
import plotly.express as px
import streamlit as st
from services.gsheet import load_absensi_data, save_absensi_data

def render_page(is_admin):
    st.title("⏱️ Rekap & Import Absensi Karyawan Site")
    st.caption("Upload file Excel Timesheet untuk memperbarui rekap absensi di Google Sheets.")

    if "df_absensi" not in st.session_state or st.sidebar.button("🔄 Refresh Data Absensi"):
        st.session_state.df_absensi = load_absensi_data()

    if is_admin:
        with st.expander("📥 **Upload File Excel Timesheet**", expanded=False):
            st.info("Pastikan file Excel memiliki 9 kolom: ID, Nama Lengkap, Site, Job Title, Tanggal, In, Out, Shift (atau Sta), Status")
            uploaded_file = st.file_uploader("Pilih File Excel:", type=["xlsx", "xls"])

            if uploaded_file is not None and st.button("🚀 Simpan ke Database Google Sheets"):
                try:
                    df_upload = pd.read_excel(uploaded_file)
                    df_upload.columns = [c.strip() for c in df_upload.columns]

                    df_upload.rename(columns={"Sta": "Shift", "Ket": "Status"}, inplace=True)
                    if "Status" not in df_upload.columns:
                        df_upload["Status"] = "Hadir"

                    df_upload["Tanggal"] = pd.to_datetime(df_upload["Tanggal"]).dt.strftime("%Y-%m-%d")
                    df_upload["ID"] = df_upload["ID"].astype(str).str.strip().str.upper()
                    df_upload["Nama Lengkap"] = df_upload["Nama Lengkap"].astype(str).str.strip().str.title()

                    df_lama = load_absensi_data()
                    updated_absensi = pd.concat([df_lama, df_upload], ignore_index=True)
                    updated_absensi = updated_absensi.drop_duplicates(subset=["ID", "Tanggal"], keep="last")

                    save_absensi_data(updated_absensi)
                    st.session_state.df_absensi = updated_absensi

                    st.success(f"✅ Berhasil menyimpan {len(df_upload)} baris data absensi ke Google Sheets!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal memproses file Excel: {e}")

    df_absen = st.session_state.df_absensi

    if not df_absen.empty:
        with st.expander("📊 **Dashboard Analytics & Visualisasi Data Absensi**", expanded=True):
            df_analytics = df_absen.copy()

            def clean_status_val(row):
                status_raw = str(row.get("Status", "")).strip().lower()
                in_val = str(row.get("In", "")).strip().lower()
                out_val = str(row.get("Out", "")).strip().lower()

                if status_raw in ["sakit"]:
                    return "Sakit"
                elif status_raw in ["cuti"]:
                    return "Cuti"
                elif status_raw in ["izin", "ijin"]:
                    return "Izin"
                elif status_raw in ["alpha", "mangkir", "tidak hadir"]:
                    return "Tidak Hadir"
                elif status_raw in ["late", "terlambat"]:
                    return "Late"

                in_empty = pd.isna(row.get("In")) or in_val in ["none", "nan", "", "-", "null"]
                out_empty = pd.isna(row.get("Out")) or out_val in ["none", "nan", "", "-", "null"]

                if in_empty and out_empty:
                    return "Tidak Hadir"

                return "Hadir"

            df_analytics["Status_Clean"] = df_analytics.apply(clean_status_val, axis=1)
            df_analytics["Tanggal_Clean"] = pd.to_datetime(df_analytics["Tanggal"]).dt.strftime("%Y-%m-%d")

            total_records = len(df_analytics)
            hadir_count = len(df_analytics[df_analytics["Status_Clean"] == "Hadir"])
            late_count = len(df_analytics[df_analytics["Status_Clean"] == "Late"])
            tidak_hadir_count = len(df_analytics[df_analytics["Status_Clean"].isin(["Sakit", "Cuti", "Izin", "Tidak Hadir"])])

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Record Absensi", f"{total_records:,}")
            m2.metric("Total Hadir Normal", f"{hadir_count:,}", delta=f"{round(hadir_count/total_records*100, 1) if total_records else 0}%")
            m3.metric("Terlambat (Late)", f"{late_count:,}", delta=f"-{late_count}" if late_count > 0 else "0", delta_color="inverse")
            m4.metric("Tidak Hadir (Sakit/Cuti/Izin/Tidak Hadir)", f"{tidak_hadir_count:,}")

            st.markdown("---")

            tab_stat, tab_shift, tab_top_late = st.tabs(["📊 Ringkasan Status", "⏱️ Sebaran Shift Work", "⚠️ Catatan Status Khusus"])

            with tab_stat:
                c1, c2 = st.columns(2)
                with c1:
                    status_counts = df_analytics["Status_Clean"].value_counts().reset_index()
                    status_counts.columns = ["Status", "Jumlah"]
                    fig_status = px.pie(
                        status_counts,
                        names="Status",
                        values="Jumlah",
                        title="Komposisi Status Kehadiran Karyawan",
                        hole=0.4,
                        color_discrete_map={
                            "Hadir": "#66C2A5", "Sakit": "#FFC000", "Cuti": "#1F4E79",
                            "Izin": "#17BECF", "Late": "#FC8D62", "Tidak Hadir": "#E78AC3",
                        },
                    )
                    fig_status.update_traces(textposition="inside", textinfo="percent+label")
                    st.plotly_chart(fig_status, use_container_width=True)

                with c2:
                    daily_trend = df_analytics.groupby(["Tanggal_Clean", "Status_Clean"])["ID"].count().reset_index(name="Total Scan")
                    fig_daily = px.bar(
                        daily_trend,
                        x="Tanggal_Clean",
                        y="Total Scan",
                        color="Status_Clean",
                        title="Volume Absensi Harian (Berdasarkan Status)",
                        text="Total Scan",
                        color_discrete_map={
                            "Hadir": "#1F4E79", "Sakit": "#FFC000", "Cuti": "#2CA02C",
                            "Izin": "#17BECF", "Late": "#FF7F0E", "Tidak Hadir": "#D62728",
                        },
                    )
                    fig_daily.update_traces(textangle=0)
                    fig_daily.update_xaxes(type="category", title_text="Tanggal")
                    fig_daily.update_layout(legend_title_text="Status")
                    st.plotly_chart(fig_daily, use_container_width=True)

            with tab_shift:
                if "Shift" in df_analytics.columns and "Tanggal_Clean" in df_analytics.columns:
                    shift_df = df_analytics.copy()
                    shift_df["Shift_Clean"] = shift_df["Shift"].astype(str).str.replace(".0", "", regex=False).str.strip().str.upper()

                    target_shifts = ["1", "2", "3", "M"]
                    shift_filtered = shift_df[shift_df["Shift_Clean"].isin(target_shifts)]

                    if not shift_filtered.empty:
                        total_days = shift_df["Tanggal_Clean"].nunique()
                        shift_avg = shift_filtered.groupby("Shift_Clean")["ID"].count().div(total_days).round(1).reset_index(name="Rata_Rata_Karyawan")

                        shift_order = {"1": 1, "2": 2, "3": 3, "M": 4}
                        shift_avg["Order"] = shift_avg["Shift_Clean"].map(shift_order)
                        shift_avg = shift_avg.sort_values("Order")

                        fig_shift = px.bar(
                            shift_avg,
                            x="Shift_Clean",
                            y="Rata_Rata_Karyawan",
                            text="Rata_Rata_Karyawan",
                            title=f"Rata-Rata Jumlah Karyawan per Hari (Total {total_days} Hari Data)",
                            color="Rata_Rata_Karyawan",
                            color_continuous_scale="Viridis",
                            labels={"Shift_Clean": "Shift Work", "Rata_Rata_Karyawan": "Rata-Rata Orang / Hari"},
                        )
                        fig_shift.update_traces(textposition="outside", texttemplate="%{text} orang/hari", textangle=0)
                        fig_shift.update_xaxes(type="category")
                        st.plotly_chart(fig_shift, use_container_width=True)
                    else:
                        st.info("Tidak ditemukan data untuk Shift 1, 2, 3, atau Middle (M).")

            with tab_top_late:
                df_late_only = df_analytics[df_analytics["Status_Clean"].isin(["Late", "Terlambat", "Sakit", "Cuti", "Izin", "Tidak Hadir"])]
                if not df_late_only.empty:
                    top_late = df_late_only.groupby(["Nama Lengkap", "Status_Clean"]).size().reset_index(name="Frekuensi")
                    top_employees = top_late.groupby("Nama Lengkap")["Frekuensi"].sum().nlargest(10).index
                    top_late = top_late[top_late["Nama Lengkap"].isin(top_employees)]

                    fig_top = px.bar(
                        top_late,
                        x="Frekuensi",
                        y="Nama Lengkap",
                        color="Status_Clean",
                        orientation="h",
                        title="Top 10 Karyawan Catatan Khusus (Rincian per Status)",
                        text="Frekuensi",
                        color_discrete_map={
                            "Late": "#FF0000", "Sakit": "#FFC000", "Cuti": "#1F4E79",
                            "Izin": "#17BECF", "Tidak Hadir": "#8B0000",
                        },
                    )
                    fig_top.update_traces(textangle=0)
                    fig_top.update_layout(yaxis={"categoryorder": "total ascending"}, legend_title_text="Status Khusus")
                    st.plotly_chart(fig_top, use_container_width=True)
                else:
                    st.success("🎉 Tidak ditemukan catatan keterlambatan atau ketidakhadiran khusus pada data absensi saat ini.")

    st.divider()
    st.subheader("📊 Timesheet Matrix")

    if df_absen.empty:
        st.warning("Belum ada data absensi di Google Sheets. Silakan upload file Excel terlebih dahulu.")
    else:
        list_site = ["Semua Site"] + sorted(list(df_absen["Site"].dropna().astype(str).unique()))
        selected_site = st.selectbox("Tampilkan Site:", list_site)

        if selected_site != "Semua Site":
            df_absen = df_absen[df_absen["Site"] == selected_site]

        df_absen_clean = df_absen.copy()
        df_absen_clean["ID"] = df_absen_clean["ID"].astype(str).str.strip().str.upper()
        df_absen_clean["Nama Lengkap"] = df_absen_clean["Nama Lengkap"].astype(str).str.strip().str.title()

        id_to_name = df_absen_clean.groupby("ID")["Nama Lengkap"].last().to_dict()
        df_absen_clean["Nama Lengkap"] = df_absen_clean["ID"].map(id_to_name)

        df_absen_clean = df_absen_clean.sort_values(by=["ID", "Tanggal", "In"], ascending=[True, True, False])
        df_absen_clean = df_absen_clean.drop_duplicates(subset=["ID", "Tanggal"], keep="first").copy()

        df_absen_clean["Tgl_Format"] = pd.to_datetime(df_absen_clean["Tanggal"]).dt.strftime("%d-%b\n%a")

        def clean_shift(val):
            if pd.isna(val) or str(val).strip().lower() in ["none", "nan", "", "-"]:
                return "-"
            try:
                val_float = float(val)
                if val_float.is_integer():
                    return str(int(val_float))
                return str(val)
            except ValueError:
                return str(val)

        df_absen_clean["Shift"] = df_absen_clean["Shift"].apply(clean_shift)

        df_melted = df_absen_clean.melt(
            id_vars=["ID", "Nama Lengkap", "Tgl_Format"],
            value_vars=["In", "Out", "Shift", "Status"],
            var_name="SubHeader",
            value_name="Value",
        )

        matrix_df = df_melted.pivot_table(
            index=["ID", "Nama Lengkap"],
            columns=["Tgl_Format", "SubHeader"],
            values="Value",
            aggfunc="first",
        )

        unique_dates = df_absen_clean["Tgl_Format"].unique()
        sub_headers = ["In", "Out", "Shift", "Status"]

        full_columns = pd.MultiIndex.from_product([unique_dates, sub_headers], names=["Tgl_Format", "SubHeader"])

        matrix_df = matrix_df.reindex(columns=full_columns)
        matrix_df = matrix_df.fillna("-")
        matrix_df = matrix_df.map(lambda x: "-" if str(x).strip().lower() in ["none", "nan", ""] else x)

        def apply_matrix_styles(df):
            styles_df = pd.DataFrame("", index=df.index, columns=df.columns)
            for col in df.columns:
                sub_header = col[1]
                if sub_header == "Status":
                    for idx in df.index:
                        val_str = str(df.loc[idx, col]).strip().lower()
                        if val_str in ["sakit", "cuti", "izin", "ijin"]:
                            styles_df.loc[idx, col] = "background-color: #FFC000; color: black; font-weight: bold;"
                        elif val_str in ["late", "terlambat"]:
                            styles_df.loc[idx, col] = "background-color: #FF0000; color: white; font-weight: bold;"
                        elif val_str in ["alpha", "mangkir", "tidak hadir"]:
                            styles_df.loc[idx, col] = "background-color: #8B0000; color: white; font-weight: bold;"
            return styles_df

        styled_matrix = matrix_df.style.apply(apply_matrix_styles, axis=None).set_properties(
            **{"text-align": "center", "font-size": "12px", "border": "1px solid #d3d3d3"}
        )

        st.dataframe(styled_matrix, use_container_width=True, height=500)
