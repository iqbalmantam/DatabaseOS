from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st

from services.gsheet import (
    load_master_data,
    load_snapshot_data,
    save_master_data,
    save_snapshot_data,
)
from utils.charts import plot_pie_status, plot_top_roles
from utils.excel import generate_excel_formatted
from utils.helper import filter_status_for_period, generate_next_id
from utils.pdf import generate_pdf


def render_page(is_admin):
    st.title("Employee Database Manager")
    st.caption("Created by iqbalmantam")

    # 1. Load Data Karyawan
    if "employees" not in st.session_state:
        st.session_state.employees = load_master_data()

    df_master_current = st.session_state.employees
    total_karyawan = len(df_master_current)

    # 2. Pilihan Periode Dashboard
    df_snap_hist = load_snapshot_data()
    current_period = date.today().strftime("%Y-%m")

    available_periods = []
    if not df_snap_hist.empty and "Periode" in df_snap_hist.columns:
        available_periods = sorted(
            list(df_snap_hist["Periode"].unique()), reverse=True
        )

    realtime_option = f"{current_period} (Bulan Berjalan - Realtime)"
    if realtime_option not in available_periods:
        available_periods.insert(0, realtime_option)

    selected_dash_period = st.selectbox(
        "📅 Pilih Periode Dashboard:", options=available_periods, index=0
    )

    # Ambil format 'YYYY-MM' murni dari teks dropdown
    selected_period = selected_dash_period.split(" ")[0]

    # 3. Pemrosesan Data Analytics Dashboard
    if "Realtime" in selected_dash_period:
        df_ana = st.session_state.employees.copy()
        active_period_str = current_period
    else:
        df_ana = df_snap_hist[
            df_snap_hist["Periode"] == selected_dash_period
        ].copy()
        active_period_str = selected_dash_period

    df_active_filtered, df_resign_filtered, df_pie_chart = (
        filter_status_for_period(df_ana, active_period_str, selected_dash_period)
    )

    # --------------------------------------------------------------------------
    # PERUBAHAN LOGIKA HITUNG RESIGN BERBASIS DATETIME
    # --------------------------------------------------------------------------
    df_calc = df_master_current.copy()

    # 1. Pastikan kolom Tanggal Resign diubah ke tipe Datetime
    df_calc["Tanggal Resign Clean"] = pd.to_datetime(
        df_calc["Tanggal Resign"], errors="coerce"
    )

    # 2. Hitung Karyawan Resign pada periode yang dipilih
    karyawan_resign = df_calc[
        df_calc["Tanggal Resign Clean"].dt.strftime("%Y-%m") == selected_period
    ]
    jumlah_resign = len(karyawan_resign)

    # Total aktif pada periode terfilter
    total_aktif = len(df_active_filtered)

    # 3. Tampilkan Metrik Streamlit
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric(
            label=f"Karyawan Aktif ({selected_period})", value=total_aktif
        )
    with col_m2:
        st.metric(
            label=f"Karyawan Resign ({selected_period})", value=jumlah_resign
        )
    with col_m3:
        st.metric(label="Total Record Data Master", value=total_karyawan)

    st.divider()

    # Kontrol Admin Sidebar
    if is_admin:
        st.sidebar.markdown("---")
        st.sidebar.header("⚡ Kontrol Admin (Master)")

        if st.sidebar.button("🔄 Sync / Refresh Data Master"):
            st.session_state.employees = load_master_data()
            st.rerun()

        with st.sidebar.expander("➕ Tambah Karyawan Baru", expanded=False):
            with st.form("add_employee_form", clear_on_submit=True):
                auto_id = generate_next_id()
                new_id = st.text_input("ID Karyawan", value=auto_id)
                new_name = st.text_input("Nama Lengkap")
                new_role = st.text_input("Posisi")
                new_cc = st.text_input("Cost Center", placeholder="CC-101")
                new_join = st.date_input("Tanggal Bergabung", value=date.today())
                new_end = st.date_input("Akhir Kontrak", value=date.today())
                new_site = st.text_input(
                    "Site / Lokasi Kerja",
                    placeholder="Contoh: JDC / Head Office",
                )
                new_status = st.selectbox(
                    "Status Karyawan", ["Aktif", "Resign", "PKWT"]
                )

                new_resign_date = "-"
                if new_status == "Resign":
                    new_resign_date = st.date_input(
                        "Tanggal Resign", value=date.today()
                    ).strftime("%Y-%m-%d")

                submit_btn = st.form_submit_button("Simpan Karyawan")
                if submit_btn:
                    clean_id = new_id.strip().upper()
                    existing_ids = (
                        [
                            str(x).strip().upper()
                            for x in st.session_state.employees["ID"].values
                        ]
                        if "ID" in st.session_state.employees.columns
                        else []
                    )

                    if not clean_id or not new_name or not new_role or not new_cc:
                        st.error("Mohon isi semua kolom yang wajib!")
                    elif clean_id in existing_ids:
                        st.error(f"❌ ID '{clean_id}' sudah digunakan!")
                    else:
                        new_row = {
                            "ID": clean_id,
                            "Nama Lengkap": new_name.strip().title(),
                            "Posisi": new_role.strip(),
                            "Cost Center": new_cc.strip(),
                            "Tanggal Bergabung": new_join.strftime("%Y-%m-%d"),
                            "Akhir Kontrak": new_end.strftime("%Y-%m-%d"),
                            "Tanggal Resign": new_resign_date,
                            "Site": new_site.strip(),
                            "Status": new_status,
                            "Terakhir Diperbarui": str(date.today()),
                        }
                        updated_df = pd.concat(
                            [
                                st.session_state.employees,
                                pd.DataFrame([new_row]),
                            ],
                            ignore_index=True,
                        )
                        save_master_data(updated_df)
                        st.success(
                            f"✅ ID '{clean_id}' berhasil ditambahkan!"
                        )
                        st.rerun()

        with st.sidebar.expander("📥 Import Banyak Data", expanded=False):
            import_type = st.radio(
                "Metode Import:", ["File CSV", "Tempel Teks (Excel/TSV)"]
            )

            if import_type == "File CSV":
                uploaded_file = st.file_uploader("Pilih file CSV", type=["csv"])
                if uploaded_file is not None and st.button("Mulai Import File"):
                    try:
                        df_import = pd.read_csv(
                            uploaded_file, dtype={"ID": str}
                        )
                        df_import.columns = [
                            c.strip() for c in df_import.columns
                        ]
                        if "Jabatan" in df_import.columns:
                            df_import.rename(
                                columns={"Jabatan": "Posisi"}, inplace=True
                            )
                        if "Status" not in df_import.columns:
                            df_import["Status"] = "Aktif"
                        if "Tanggal Resign" not in df_import.columns:
                            df_import["Tanggal Resign"] = "-"
                        df_import["Terakhir Diperbarui"] = str(date.today())

                        existing_ids = set(
                            str(x).strip().upper()
                            for x in st.session_state.employees["ID"].values
                        )
                        df_import_filtered = df_import[
                            ~df_import["ID"]
                            .astype(str)
                            .str.strip()
                            .str.upper()
                            .isin(existing_ids)
                        ]
                        added_count = len(df_import_filtered)

                        if added_count > 0:
                            updated_df = pd.concat(
                                [
                                    st.session_state.employees,
                                    df_import_filtered,
                                ],
                                ignore_index=True,
                            )
                            save_master_data(updated_df)
                            st.success(
                                f"Berhasil mengimpor {added_count} data!"
                            )
                            st.rerun()
                        else:
                            st.error("Semua ID pada file sudah terdaftar!")
                    except Exception as e:
                        st.error(f"Gagal membaca file: {e}")
            else:
                pasted_text = st.text_area("Tempel dari Excel", height=150)
                if st.button("Mulai Import Teks") and pasted_text.strip():
                    lines = pasted_text.strip().split("\n")
                    added_rows = []
                    existing_ids = set(
                        str(x).strip().upper()
                        for x in st.session_state.employees["ID"].values
                    )

                    for line in lines:
                        delimiter = (
                            "\t"
                            if "\t" in line
                            else (";" if ";" in line else ",")
                        )
                        cols = [c.strip() for c in line.split(delimiter)]
                        if len(cols) >= 4:
                            emp_id, name, role_title, cc = (
                                cols[0].upper(),
                                cols[1].title(),
                                cols[2],
                                cols[3],
                            )
                            join_d = cols[4] if len(cols) > 4 else ""
                            end_d = cols[5] if len(cols) > 5 else ""
                            resign_d = cols[6] if len(cols) > 6 else "-"
                            site_val = cols[7] if len(cols) > 7 else ""
                            status_val = (
                                cols[8] if len(cols) > 8 else "Aktif"
                            )

                            if emp_id not in existing_ids:
                                added_rows.append({
                                    "ID": emp_id,
                                    "Nama Lengkap": name,
                                    "Posisi": role_title,
                                    "Cost Center": cc,
                                    "Tanggal Bergabung": join_d,
                                    "Akhir Kontrak": end_d,
                                    "Tanggal Resign": resign_d,
                                    "Site": site_val,
                                    "Status": status_val,
                                    "Terakhir Diperbarui": str(date.today()),
                                })
                                existing_ids.add(emp_id)

                    if added_rows:
                        updated_df = pd.concat(
                            [
                                st.session_state.employees,
                                pd.DataFrame(added_rows),
                            ],
                            ignore_index=True,
                        )
                        save_master_data(updated_df)
                        st.success(
                            f"Berhasil menambahkan {len(added_rows)} data baru!"
                        )
                        st.rerun()

        with st.sidebar.expander(
            "📸 Freeze / Snapshot Bulanan", expanded=False
        ):
            st.subheader("🔒 Simpan Snapshot Baru")
            selected_periode = st.date_input(
                "Pilih Bulan Periode", value=date.today()
            ).strftime("%Y-%m")

            if st.button(f"🔒 Kunci Data {selected_periode}"):
                try:
                    df_curr = st.session_state.employees.copy()
                    df_active = (
                        df_curr[df_curr["Status"] == "Aktif"].copy()
                        if "Status" in df_curr.columns
                        else df_curr.copy()
                    )
                    df_active["Periode"] = selected_periode
                    df_active["Tanggal Snapshot"] = str(date.today())

                    cols_order = [
                        "Periode",
                        "ID",
                        "Nama Lengkap",
                        "Posisi",
                        "Cost Center",
                        "Tanggal Bergabung",
                        "Akhir Kontrak",
                        "Tanggal Resign",
                        "Site",
                        "Status",
                        "Terakhir Diperbarui",
                        "Tanggal Snapshot",
                    ]

                    df_old_snap = load_snapshot_data()
                    if (
                        not df_old_snap.empty
                        and "Periode" in df_old_snap.columns
                    ):
                        df_old_snap = df_old_snap[
                            df_old_snap["Periode"] != selected_periode
                        ]
                        df_new_snap = pd.concat([
                            df_old_snap,
                            df_active[cols_order],
                        ])
                    else:
                        df_new_snap = df_active[cols_order]

                    save_snapshot_data(df_new_snap)
                    st.success(
                        f"✅ Rekap {selected_periode} berhasil disimpan!"
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"Gagal melakukan snapshot: {e}")

            st.markdown("---")
            st.subheader("🗑️ Hapus Snapshot Periode")
            df_snap_exist = load_snapshot_data()
            if (
                not df_snap_exist.empty
                and "Periode" in df_snap_exist.columns
            ):
                list_snap_periods = sorted(
                    df_snap_exist["Periode"].unique(), reverse=True
                )
                period_to_delete = st.selectbox(
                    "Pilih Periode yang Ingin Dihapus:", list_snap_periods
                )

                if st.button(f"🗑️ Hapus Snapshot {period_to_delete}"):
                    try:
                        df_snap_filtered = df_snap_exist[
                            df_snap_exist["Periode"] != period_to_delete
                        ]
                        save_snapshot_data(df_snap_filtered)
                        st.success(
                            f"✅ Snapshot periode {period_to_delete} berhasil"
                            " dihapus!"
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus snapshot: {e}")

        st.sidebar.markdown("---")
        st.sidebar.subheader("📤 Ekspor Database")
        csv_data = (
            st.session_state.employees.to_csv(index=False).encode("utf-8-sig")
        )
        st.sidebar.download_button(
            label="📄 Ekspor CSV",
            data=csv_data,
            file_name="ekspor_database_karyawan.csv",
            mime="text/csv",
            use_container_width=True,
        )
        excel_data = generate_excel_formatted(st.session_state.employees)
        st.sidebar.download_button(
            label="📊 Ekspor Excel Formatted (.xlsx)",
            data=excel_data,
            file_name=f"Rekap_Karyawan_{date.today().strftime('%Y%m%d')}.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            use_container_width=True,
        )

    if is_admin:
        st.info("🔓 **Mode Akses:** Administrator")
    else:
        st.info("👁️ **Mode Akses:** Umum / Guest (View Only)")

    # Visualisasi Data Dashboard
    with st.expander(
        "📊 **Dashboard Analytics & Visualisasi Data**", expanded=True
    ):
        if not df_ana.empty:
            tab_overview, tab_trend, tab_cost = st.tabs([
                "📈 Ringkasan & Status",
                "🗓️ Tren Snapshot Bulanan",
                "💳 Sebaran Cost Center & Site",
            ])

            with tab_overview:
                c1, c2 = st.columns(2)
                with c1:
                    if (
                        "Status" in df_pie_chart.columns
                        and not df_pie_chart.empty
                    ):
                        fig_status = plot_pie_status(
                            df_pie_chart, active_period_str
                        )
                        st.plotly_chart(fig_status, use_container_width=True)
                    else:
                        st.info("Tidak ada data status untuk ditampilkan.")
                with c2:
                    if "Posisi" in df_active_filtered.columns:
                        top_roles = (
                            df_active_filtered["Posisi"]
                            .value_counts()
                            .head(10)
                            .reset_index()
                        )
                        top_roles.columns = ["Posisi", "Jumlah"]
                        fig_role = plot_top_roles(top_roles, active_period_str)
                        st.plotly_chart(fig_role, use_container_width=True)

            with tab_trend:
                if (
                    not df_snap_hist.empty
                    and "Periode" in df_snap_hist.columns
                ):
                    trend_summary = (
                        df_snap_hist.groupby("Periode")["ID"]
                        .count()
                        .reset_index(name="Karyawan Aktif")
                        .sort_values("Periode")
                    )
                    fig_trend = px.line(
                        trend_summary,
                        x="Periode",
                        y="Karyawan Aktif",
                        markers=True,
                        title=(
                            "Pertumbuhan Jumlah Karyawan Aktif per Periode"
                            " Snapshot"
                        ),
                        line_shape="spline",
                    )
                    fig_trend.update_traces(
                        line_color="#1F4E79", line_width=3, marker_size=8
                    )
                    st.plotly_chart(fig_trend, use_container_width=True)
                else:
                    st.info("Belum ada data snapshot historis.")

            with tab_cost:
                c3, c4 = st.columns(2)
                with c3:
                    if "Cost Center" in df_active_filtered.columns:
                        df_cc_clean = df_active_filtered.copy()
                        df_cc_clean["Cost Center Clean"] = (
                            df_cc_clean["Cost Center"]
                            .astype(str)
                            .str.strip()
                            .str.title()
                            .replace("", "Belum Diisi")
                        )
                        df_cc_clean["Cost Center Clean"] = df_cc_clean[
                            "Cost Center Clean"
                        ].replace({
                            "Vinfast": "VinFast",
                            "Cj Food": "CJ Food",
                            "Fks": "FKS",
                            "Keva & Jotun": "Keva & Jotun",
                            "Jotun, Keva": "Keva & Jotun",
                        })
                        cc_counts = (
                            df_cc_clean["Cost Center Clean"]
                            .value_counts()
                            .reset_index()
                        )
                        cc_counts.columns = ["Cost Center", "Jumlah"]
                        fig_cc = px.bar(
                            cc_counts,
                            x="Jumlah",
                            y="Cost Center",
                            orientation="h",
                            title=(
                                "Jumlah Karyawan per Cost Center"
                                f" ({active_period_str})"
                            ),
                            color="Jumlah",
                            color_continuous_scale="Viridis",
                            text="Jumlah",
                        )
                        fig_cc.update_traces(
                            textposition="outside", textangle=0
                        )
                        fig_cc.update_layout(
                            yaxis={"categoryorder": "total ascending"},
                            height=max(450, len(cc_counts) * 25),
                        )
                        st.plotly_chart(fig_cc, use_container_width=True)
                with c4:
                    if "Site" in df_active_filtered.columns:
                        df_site_clean = df_active_filtered.copy()
                        df_site_clean["Site Clean"] = (
                            df_site_clean["Site"]
                            .astype(str)
                            .str.strip()
                            .str.upper()
                            .replace("", "BELUM DIISI")
                        )
                        site_counts = (
                            df_site_clean["Site Clean"]
                            .value_counts()
                            .reset_index()
                        )
                        site_counts.columns = ["Site", "Jumlah"]
                        fig_site = px.pie(
                            site_counts,
                            names="Site",
                            values="Jumlah",
                            title=(
                                "Distribusi Lokasi Kerja / Site"
                                f" ({active_period_str})"
                            ),
                            hole=0.3,
                        )
                        st.plotly_chart(fig_site, use_container_width=True)

    st.divider()

    # Fitur Pencarian & Tabel Data
    col_mode, col_cat, col_src = st.columns([1.5, 1.5, 3])
    with col_mode:
        view_mode = st.selectbox(
            "Tampilkan Data:",
            ["Master Real-time", "Rekap Snapshot Bulanan"],
        )

    df_display = pd.DataFrame()
    if view_mode == "Rekap Snapshot Bulanan":
        df_snap_all = load_snapshot_data()
        if not df_snap_all.empty and "Periode" in df_snap_all.columns:
            list_periode = sorted(
                df_snap_all["Periode"].unique(), reverse=True
            )
            selected_view_period = st.selectbox(
                "Pilih Periode Rekap:", list_periode
            )
            df_display = df_snap_all[
                df_snap_all["Periode"] == selected_view_period
            ].copy()
        else:
            st.warning("Belum ada data snapshot yang disimpan.")
    else:
        df_display = st.session_state.employees.copy()

    with col_cat:
        search_category = st.selectbox(
            "Cari Berdasarkan:",
            [
                "Semua Kolom",
                "Nama Lengkap",
                "Posisi",
                "Cost Center",
                "Site",
                "Status",
            ],
        )

    with col_src:
        search_query = st.text_input("🔍 Masukkan kata kunci pencarian...", "")

    if search_query and not df_display.empty:
        query = search_query.strip().lower()
        if search_category in df_display.columns:
            df_display = df_display[
                df_display[search_category]
                .astype(str)
                .str.lower()
                .str.contains(query, na=False)
            ]
        else:
            mask = pd.Series(False, index=df_display.index)
            for col in ["Nama Lengkap", "Posisi", "Cost Center", "Site", "Status"]:
                if col in df_display.columns:
                    mask |= (
                        df_display[col]
                        .astype(str)
                        .str.lower()
                        .str.contains(query, na=False)
                    )
            df_display = df_display[mask]

    col_tb_title, col_pdf_btn = st.columns([3, 1])
    with col_tb_title:
        st.subheader(f"📋 Tabel Data Karyawan ({view_mode})")
    with col_pdf_btn:
        if not df_display.empty:
            pdf_bytes = generate_pdf(df_display)
            st.download_button(
                label="📄 Cetak / Download PDF",
                data=pdf_bytes,
                file_name=(
                    f"Laporan_Karyawan_{date.today().strftime('%Y%m%d')}.pdf"
                ),
                mime="application/pdf",
                use_container_width=True,
            )

    if df_display.empty:
        st.warning("Tidak ada data karyawan yang cocok dengan pencarian.")
    else:
        st.dataframe(df_display, use_container_width=True)

    # Edit Data Karyawan (Admin Only)
    if (
        is_admin
        and view_mode == "Master Real-time"
        and not st.session_state.employees.empty
    ):
        st.divider()
        st.subheader("🛠️ Kelola / Edit / Ubah Status Data Karyawan")
        selected_id = st.selectbox(
            "Pilih ID Karyawan untuk Diubah / Dihapus:",
            options=["-- Pilih ID --"] + list(st.session_state.employees["ID"]),
        )

        if selected_id != "-- Pilih ID --":
            emp_idx = st.session_state.employees[
                st.session_state.employees["ID"] == selected_id
            ].index[0]
            row = st.session_state.employees.loc[emp_idx]

            with st.form("edit_form"):
                st.write(
                    f"Editing: **{row['Nama Lengkap']}** (ID: `{row['ID']}`)"
                )
                e_name = st.text_input("Nama Lengkap", value=row["Nama Lengkap"])
                e_role = st.text_input("Posisi", value=row.get("Posisi", ""))
                e_cc = st.text_input("Cost Center", value=row["Cost Center"])
                e_join = st.text_input(
                    "Tanggal Bergabung (YYYY-MM-DD)",
                    value=row["Tanggal Bergabung"],
                )
                e_end = st.text_input(
                    "Akhir Kontrak (YYYY-MM-DD)", value=row["Akhir Kontrak"]
                )
                e_site = st.text_input(
                    "Site / Lokasi Kerja", value=row.get("Site", "")
                )
                current_status = row.get("Status", "Aktif")
                status_opts = ["Aktif", "Resign", "PKWT"]
                idx_stat = (
                    status_opts.index(current_status)
                    if current_status in status_opts
                    else 0
                )
                e_status = st.selectbox(
                    "Status Karyawan", options=status_opts, index=idx_stat
                )
                e_resign = st.text_input(
                    "Tanggal Resign (YYYY-MM-DD)",
                    value=row.get("Tanggal Resign", "-"),
                )

                col_save, col_del = st.columns(2)
                with col_save:
                    btn_save = st.form_submit_button("💾 Simpan Perubahan")
                with col_del:
                    btn_del = st.form_submit_button("🗑️ Hapus Karyawan")

                if btn_save:
                    st.session_state.employees.loc[
                        emp_idx,
                        [
                            "Nama Lengkap",
                            "Posisi",
                            "Cost Center",
                            "Tanggal Bergabung",
                            "Akhir Kontrak",
                            "Tanggal Resign",
                            "Site",
                            "Status",
                            "Terakhir Diperbarui",
                        ],
                    ] = [
                        e_name.strip().title(),
                        e_role.strip(),
                        e_cc.strip(),
                        e_join.strip(),
                        e_end.strip(),
                        e_resign.strip(),
                        e_site.strip(),
                        e_status,
                        str(date.today()),
                    ]
                    save_master_data(st.session_state.employees)
                    st.success("Data berhasil diperbarui!")
                    st.rerun()

                if btn_del:
                    updated_df = st.session_state.employees.drop(
                        emp_idx
                    ).reset_index(drop=True)
                    save_master_data(updated_df)
                    st.success("Data karyawan berhasil dihapus!")
                    st.rerun()
