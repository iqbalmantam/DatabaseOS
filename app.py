import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import date
from fpdf import FPDF

# Set Halaman Streamlit
st.set_page_config(
    page_title="Employee Database Manager",
    page_icon="👥",
    layout="wide"
)

# --- SEMBUNYIKAN HEADER & MENU GITHUB / FORK ---
st.markdown(
    """
    <style>
    header[data-testid="stHeader"] {
        visibility: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- PIN / PASSWORD ADMINISTRATOR ---
ADMIN_PIN = "2273"

# --- KONEKSI GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Fungsi Membaca Data
def load_data():
    try:
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            if "ID" in df.columns:
                df["ID"] = df["ID"].astype(str)
            if "Jabatan" in df.columns and "Posisi" not in df.columns:
                df.rename(columns={"Jabatan": "Posisi"}, inplace=True)
        if "Site" not in df.columns:
            df["Site"] = ""
        return df
    except Exception as e:
        st.error(f"Gagal terhubung ke Google Sheets: {e}")
        return pd.DataFrame(columns=["ID", "Nama Lengkap", "Posisi", "Cost Center", "Tanggal Bergabung", "Akhir Kontrak", "Site"])

# Fungsi Menyimpan Data ke Google Sheets
def save_data(df):
    conn.update(data=df)
    st.session_state.employees = df

# Fungsi Helper Generator PDF
def generate_pdf(df):
    pdf = FPDF(orientation="L", unit="mm", format="A4") # Lanscape A4
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    
    # Title Header
    pdf.cell(0, 10, "LAPORAN DATABASE KARYAWAN", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Dicetak Tanggal: {date.today().strftime('%d-%m-%Y')} | Total Karyawan: {len(df)}", ln=True, align="C")
    pdf.ln(5)
    
    # Header Table
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(230, 230, 230)
    
    # Column Widths (A4 Landscape total width ~ 277mm)
    col_widths = [25, 55, 45, 30, 35, 35, 35]
    headers = ["ID", "Nama Lengkap", "Posisi", "Cost Center", "Tgl Bergabung", "Akhir Kontrak", "Site"]
    
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, align="C", fill=True)
    pdf.ln()
    
    # Table Content
    pdf.set_font("Helvetica", "", 8)
    for _, row in df.iterrows():
        pdf.cell(col_widths[0], 7, str(row.get("ID", "")), border=1, align="C")
        pdf.cell(col_widths[1], 7, str(row.get("Nama Lengkap", ""))[:30], border=1)
        pdf.cell(col_widths[2], 7, str(row.get("Posisi", ""))[:25], border=1)
        pdf.cell(col_widths[3], 7, str(row.get("Cost Center", "")), border=1, align="C")
        pdf.cell(col_widths[4], 7, str(row.get("Tanggal Bergabung", "")), border=1, align="C")
        pdf.cell(col_widths[5], 7, str(row.get("Akhir Kontrak", "")), border=1, align="C")
        pdf.cell(col_widths[6], 7, str(row.get("Site", "")), border=1, align="C")
        pdf.ln()
        
    return bytes(pdf.output())

# Inisialisasi Data dari Google Sheets
if "employees" not in st.session_state:
    st.session_state.employees = load_data()

# Helper function untuk generate ID otomatis
def generate_next_id():
    df = st.session_state.employees
    max_num = 0
    if not df.empty and "ID" in df.columns:
        for emp_id in df["ID"]:
            if str(emp_id).startswith("EMP-"):
                try:
                    num = int(str(emp_id).split("-")[1])
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass
    return f"EMP-{str(max_num + 1).zfill(3)}"


# --- HEADER ---
st.title("Employee Database Manager")
st.caption("Created by iqbalmantam")

# Metric Total Karyawan
total_karyawan = len(st.session_state.employees)
st.metric(label="Total Karyawan Saat Ini", value=total_karyawan)

st.divider()

# --- SIDEBAR: PILIHAN PERAN (ROLE) ---
st.sidebar.header("🔐 Akses Pengguna")
role = st.sidebar.radio("Pilih Mode Akses:", ["Umum (View Only)", "Administrator"])

is_admin = False

if role == "Administrator":
    pin_input = st.sidebar.text_input("Masukkan PIN Admin:", type="password")
    if pin_input == ADMIN_PIN:
        st.sidebar.success("Akses Administrator Aktif!")
        is_admin = True
    elif pin_input != "":
        st.sidebar.error("PIN Salah! Anda berada dalam mode baca.")
    else:
        st.sidebar.info("Masukkan PIN untuk membuka menu kontrol Administrator.")

# --- SIDEBAR: MENU ADMIN ---
if is_admin:
    st.sidebar.markdown("---")
    st.sidebar.header("⚡ Kontrol Administrator")

    # Tombol Refresh Manual
    if st.sidebar.button("🔄 Sync / Refresh Data"):
        st.session_state.employees = load_data()
        st.rerun()

    # 1. Tambah Karyawan Baru
    with st.sidebar.expander("➕ Tambah Karyawan Baru", expanded=False):
        with st.form("add_employee_form", clear_on_submit=True):
            auto_id = generate_next_id()
            new_id = st.text_input("ID Karyawan", value=auto_id)
            new_name = st.text_input("Nama Lengkap")
            new_role = st.text_input("Posisi")
            new_cc = st.text_input("Cost Center", placeholder="CC-101")
            new_join = st.date_input("Tanggal Bergabung", value=date.today())
            new_end = st.date_input("Akhir Kontrak", value=date.today())
            new_site = st.text_input("Site / Lokasi Kerja", placeholder="Contoh: Jakarta / Head Office")
            
            submit_btn = st.form_submit_button("Simpan Karyawan")
            if submit_btn:
                clean_id = new_id.strip()
                existing_ids = [str(x).strip().lower() for x in st.session_state.employees["ID"].values] if "ID" in st.session_state.employees.columns else []
                
                if not clean_id or not new_name or not new_role or not new_cc:
                    st.error("Mohon isi semua kolom yang wajib!")
                elif clean_id.lower() in existing_ids:
                    st.error(f"❌ GAGAL: ID '{clean_id}' sudah digunakan! Gunakan ID yang lain.")
                else:
                    new_row = {
                        "ID": clean_id,
                        "Nama Lengkap": new_name,
                        "Posisi": new_role,
                        "Cost Center": new_cc,
                        "Tanggal Bergabung": new_join.strftime("%Y-%m-%d"),
                        "Akhir Kontrak": new_end.strftime("%Y-%m-%d"),
                        "Site": new_site
                    }
                    updated_df = pd.concat([st.session_state.employees, pd.DataFrame([new_row])], ignore_index=True)
                    save_data(updated_df)
                    st.success(f"✅ ID '{clean_id}' berhasil ditambahkan ke Google Sheets!")
                    st.rerun()

    # 2. Bulk Import Data
    with st.sidebar.expander("📥 Import Banyak Data", expanded=False):
        import_type = st.radio("Metode Import:", ["File CSV", "Tempel Teks (Excel/TSV)"])
        
        if import_type == "File CSV":
            uploaded_file = st.file_uploader("Pilih file CSV", type=["csv"])
            if uploaded_file is not None:
                if st.button("Mulai Import File"):
                    try:
                        df_import = pd.read_csv(uploaded_file, dtype={"ID": str})
                        df_import.columns = [c.strip() for c in df_import.columns]
                        if "Jabatan" in df_import.columns:
                            df_import.rename(columns={"Jabatan": "Posisi"}, inplace=True)
                        
                        existing_ids = set(str(x).strip().lower() for x in st.session_state.employees["ID"].values)
                        initial_count = len(df_import)
                        
                        df_import_filtered = df_import[~df_import["ID"].astype(str).str.strip().str.lower().isin(existing_ids)]
                        added_count = len(df_import_filtered)
                        skipped_count = initial_count - added_count
                        
                        if added_count > 0:
                            updated_df = pd.concat([st.session_state.employees, df_import_filtered], ignore_index=True)
                            save_data(updated_df)
                            st.success(f"Berhasil mengimpor {added_count} data!")
                            if skipped_count > 0:
                                st.warning(f"Dilewati {skipped_count} data karena ID duplikat.")
                            st.rerun()
                        else:
                            st.error("Semua ID pada file sudah terdaftar di database!")
                    except Exception as e:
                        st.error(f"Gagal membaca file: {e}")
                        
        else: # Tempel Teks
            pasted_text = st.text_area(
                "Tempel dari Excel (Tab / Comma separated)", 
                placeholder="EMP-005\tBudi Santoso\tDeveloper\tCC-101\t2024-01-15\t2025-01-15\tJakarta",
                height=150
            )
            if st.button("Mulai Import Teks"):
                if pasted_text.strip():
                    lines = pasted_text.strip().split("\n")
                    added_rows = []
                    skipped_count = 0
                    existing_ids = set(str(x).strip().lower() for x in st.session_state.employees["ID"].values)

                    for line in lines:
                        delimiter = "\t" if "\t" in line else (";" if ";" in line else ",")
                        cols = [c.strip() for c in line.split(delimiter)]
                        if len(cols) >= 4:
                            emp_id, name, role_title, cc = cols[0], cols[1], cols[2], cols[3]
                            join_d = cols[4] if len(cols) > 4 else ""
                            end_d = cols[5] if len(cols) > 5 else ""
                            site_val = cols[6] if len(cols) > 6 else ""
                            
                            if emp_id.lower() not in existing_ids:
                                added_rows.append({
                                    "ID": emp_id, "Nama Lengkap": name, "Posisi": role_title,
                                    "Cost Center": cc, "Tanggal Bergabung": join_d, "Akhir Kontrak": end_d,
                                    "Site": site_val
                                })
                                existing_ids.add(emp_id.lower())
                            else:
                                skipped_count += 1

                    if added_rows:
                        updated_df = pd.concat([st.session_state.employees, pd.DataFrame(added_rows)], ignore_index=True)
                        save_data(updated_df)
                        st.success(f"Berhasil menambahkan {len(added_rows)} data baru!")
                        if skipped_count > 0:
                            st.warning(f"Dilewati {skipped_count} data karena ID duplikat.")
                        st.rerun()
                    else:
                        st.error("Tidak ada data baru yang ditambahkan (semua ID sudah terdaftar).")

    # 3. Export Data CSV & PDF
    st.sidebar.markdown("---")
    csv_data = st.session_state.employees.to_csv(index=False).encode('utf-8-sig')
    st.sidebar.download_button(
        label="📤 Ekspor Semua Data (CSV)",
        data=csv_data,
        file_name="ekspor_database_karyawan.csv",
        mime="text/csv",
        use_container_width=True
    )

# --- HALAMAN UTAMA ---

if is_admin:
    st.info("🔓 **Mode Akses:** Administrator (Tersinkronisasi dengan Google Sheets)")
else:
    st.info("👁️ **Mode Akses:** Umum / Guest (Hanya dapat melihat dan mencari data)")

# --- BAGIAN FITUR SUMMARY / RINGKASAN DATA ---
with st.expander("📊 **Ringkasan Data Karyawan (Summary)**", expanded=False):
    if not st.session_state.employees.empty:
        tab_posisi, tab_cc, tab_site = st.tabs(["📌 Berdasarkan Posisi", "💳 Berdasarkan Cost Center", "🏢 Berdasarkan Site"])
        
        # 1. Summary Posisi
        with tab_posisi:
            if "Posisi" in st.session_state.employees.columns:
                df_role = st.session_state.employees["Posisi"].value_counts().reset_index()
                df_role.columns = ["Posisi", "Jumlah Karyawan"]
                col_t1, col_g1 = st.columns([1, 1])
                with col_t1:
                    st.dataframe(df_role, use_container_width=True)
                with col_g1:
                    st.bar_chart(df_role.set_index("Posisi"))
                
        # 2. Summary Cost Center
        with tab_cc:
            if "Cost Center" in st.session_state.employees.columns:
                df_cc = st.session_state.employees["Cost Center"].value_counts().reset_index()
                df_cc.columns = ["Cost Center", "Jumlah Karyawan"]
                col_t2, col_g2 = st.columns([1, 1])
                with col_t2:
                    st.dataframe(df_cc, use_container_width=True)
                with col_g2:
                    st.bar_chart(df_cc.set_index("Cost Center"))
                
        # 3. Summary Site
        with tab_site:
            if "Site" in st.session_state.employees.columns:
                df_site = st.session_state.employees["Site"].replace("", "Belum Diisi").value_counts().reset_index()
                df_site.columns = ["Site", "Jumlah Karyawan"]
                col_t3, col_g3 = st.columns([1, 1])
                with col_t3:
                    st.dataframe(df_site, use_container_width=True)
                with col_g3:
                    st.bar_chart(df_site.set_index("Site"))
    else:
        st.write("Belum ada data untuk ditampilkan ringkasannya.")

st.divider()

# --- FITUR PENCARIAN & FILTER ---
col_cat, col_src = st.columns([1, 3])

with col_cat:
    search_category = st.selectbox(
        "Cari Berdasarkan:", 
        ["Semua Kolom", "Nama Lengkap", "Posisi", "Cost Center", "Site"]
    )

with col_src:
    search_query = st.text_input("🔍 Masukkan kata kunci pencarian...", "")

df_display = st.session_state.employees.copy()

if search_query and not df_display.empty:
    query = search_query.strip().lower()
    
    if search_category == "Nama Lengkap":
        df_display = df_display[df_display["Nama Lengkap"].astype(str).str.lower().str.contains(query, na=False)]
    elif search_category == "Posisi":
        df_display = df_display[df_display["Posisi"].astype(str).str.lower().str.contains(query, na=False)]
    elif search_category == "Cost Center":
        df_display = df_display[df_display["Cost Center"].astype(str).str.lower().str.contains(query, na=False)]
    elif search_category == "Site":
        df_display = df_display[df_display["Site"].astype(str).str.lower().str.contains(query, na=False)]
    else: # Semua Kolom
        mask_name = df_display["Nama Lengkap"].astype(str).str.lower().str.contains(query, na=False)
        mask_role = df_display["Posisi"].astype(str).str.lower().str.contains(query, na=False) if "Posisi" in df_display.columns else False
        mask_cc = df_display["Cost Center"].astype(str).str.lower().str.contains(query, na=False)
        mask_site = df_display["Site"].astype(str).str.lower().str.contains(query, na=False)
        df_display = df_display[mask_name | mask_role | mask_cc | mask_site]

# Header Tabel & Tombol Cetak PDF
col_tb_title, col_pdf_btn = st.columns([3, 1])
with col_tb_title:
    st.subheader("📋 Tabel Data Karyawan")
with col_pdf_btn:
    if not df_display.empty:
        pdf_bytes = generate_pdf(df_display)
        st.download_button(
            label="📄 Cetak / Download PDF",
            data=pdf_bytes,
            file_name=f"Laporan_Karyawan_{date.today().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# Tabel Tampilan Karyawan
if df_display.empty:
    st.warning("Tidak ada data karyawan yang cocok dengan pencarian.")
else:
    st.dataframe(df_display, use_container_width=True)


# --- EDIT / HAPUS SATUAN ---
if is_admin and not st.session_state.employees.empty:
    st.divider()
    st.subheader("🛠️ Kelola / Edit / Hapus Data Karyawan")
    
    selected_id = st.selectbox("Pilih ID Karyawan untuk Diubah / Dihapus:", options=["-- Pilih ID --"] + list(st.session_state.employees["ID"]))

    if selected_id != "-- Pilih ID --":
        emp_idx = st.session_state.employees[st.session_state.employees["ID"] == selected_id].index[0]
        row = st.session_state.employees.loc[emp_idx]

        with st.form("edit_form"):
            st.write(f"Editing: **{row['Nama Lengkap']}** (ID: `{row['ID']}`)")
            e_name = st.text_input("Nama Lengkap", value=row["Nama Lengkap"])
            e_role = st.text_input("Posisi", value=row.get("Posisi", ""))
            e_cc = st.text_input("Cost Center", value=row["Cost Center"])
            e_join = st.text_input("Tanggal Bergabung (YYYY-MM-DD)", value=row["Tanggal Bergabung"])
            e_end = st.text_input("Akhir Kontrak (YYYY-MM-DD)", value=row["Akhir Kontrak"])
            e_site = st.text_input("Site / Lokasi Kerja", value=row.get("Site", ""))

            col_save, col_del = st.columns(2)
            with col_save:
                btn_save = st.form_submit_button("💾 Simpan Perubahan")
            with col_del:
                btn_del = st.form_submit_button("🗑️ Hapus Karyawan")

            if btn_save:
                st.session_state.employees.loc[emp_idx, ["Nama Lengkap", "Posisi", "Cost Center", "Tanggal Bergabung", "Akhir Kontrak", "Site"]] = [e_name, e_role, e_cc, e_join, e_end, e_site]
                save_data(st.session_state.employees)
                st.success("Data berhasil diperbarui!")
                st.rerun()

            if btn_del:
                updated_df = st.session_state.employees.drop(emp_idx).reset_index(drop=True)
                save_data(updated_df)
                st.success("Data karyawan berhasil dihapus!")
                st.rerun()
