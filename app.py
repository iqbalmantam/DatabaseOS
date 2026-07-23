import streamlit as st
import pandas as pd
from datetime import date

# Set Halaman Streamlit
st.set_page_config(
    page_title="Employee Database Manager",
    page_icon="👥",
    layout="wide"
)

# --- PIN / PASSWORD ADMINISTRATOR ---
# Anda bisa mengubah PIN ini sesuai kebutuhan
ADMIN_PIN = "2273"

# --- INITIALIZATION STATE (Database Sementara) ---
if "employees" not in st.session_state:
    st.session_state.employees = pd.DataFrame([
        {"ID": "EMP-001", "Nama Lengkap": "Budi Santoso", "Jabatan": "Software Engineer", "Cost Center": "CC-101", "Tanggal Bergabung": "2024-01-15", "Akhir Kontrak": "2025-01-15"},
        {"ID": "EMP-002", "Nama Lengkap": "Siti Rahma", "Jabatan": "HR Generalist", "Cost Center": "CC-202", "Tanggal Bergabung": "2023-06-01", "Akhir Kontrak": "2024-06-01"},
        {"ID": "EMP-003", "Nama Lengkap": "Andi Wijaya", "Jabatan": "Digital Marketer", "Cost Center": "CC-303", "Tanggal Bergabung": "2024-03-10", "Akhir Kontrak": "2025-03-10"},
        {"ID": "EMP-004", "Nama Lengkap": "Rina Permata", "Jabatan": "Financial Analyst", "Cost Center": "CC-404", "Tanggal Bergabung": "2022-11-01", "Akhir Kontrak": "2024-11-01"}
    ])

# Helper function untuk generate ID otomatis
def generate_next_id():
    df = st.session_state.employees
    max_num = 0
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
st.caption("@iqbalmantam, 2026.")

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

# --- SIDEBAR: MENU ADMIN (HANYA MUNCUL JIKA IS_ADMIN = TRUE) ---
if is_admin:
    st.sidebar.markdown("---")
    st.sidebar.header("⚡ Kontrol Administrator")

    # 1. Tambah Karyawan Baru (Dengan Validasi ID Double)
    with st.sidebar.expander("➕ Tambah Karyawan Baru", expanded=False):
        with st.form("add_employee_form", clear_on_submit=True):
            auto_id = generate_next_id()
            new_id = st.text_input("ID Karyawan", value=auto_id)
            new_name = st.text_input("Nama Lengkap")
            new_role = st.text_input("Jabatan")
            new_cc = st.text_input("Cost Center", placeholder="CC-101")
            new_join = st.date_input("Tanggal Bergabung", value=date.today())
            new_end = st.date_input("Akhir Kontrak", value=date.today())
            
            submit_btn = st.form_submit_button("Simpan Karyawan")
            if submit_btn:
                # Normalisasi ID untuk pengecekan aman
                clean_id = new_id.strip()
                existing_ids = [str(x).strip().lower() for x in st.session_state.employees["ID"].values]
                
                if not clean_id or not new_name or not new_role or not new_cc:
                    st.error("Mohon isi semua kolom yang wajib!")
                elif clean_id.lower() in existing_ids:
                    # CEK DENGAN ID DOUBLE (DITOLAK)
                    st.error(f"❌ GAGAL: ID '{clean_id}' sudah digunakan! Gunakan ID yang lain.")
                else:
                    new_row = {
                        "ID": clean_id,
                        "Nama Lengkap": new_name,
                        "Jabatan": new_role,
                        "Cost Center": new_cc,
                        "Tanggal Bergabung": new_join.strftime("%Y-%m-%d"),
                        "Akhir Kontrak": new_end.strftime("%Y-%m-%d")
                    }
                    st.session_state.employees = pd.concat([st.session_state.employees, pd.DataFrame([new_row])], ignore_index=True)
                    st.success(f"✅ Karyawan dengan ID '{clean_id}' berhasil ditambahkan!")
                    st.rerun()

    # 2. Bulk Import Data (Dengan Filter ID Double Automatic Skip)
    with st.sidebar.expander("📥 Import Banyak Data", expanded=False):
        import_type = st.radio("Metode Import:", ["File CSV", "Tempel Teks (Excel/TSV)"])
        
        if import_type == "File CSV":
            uploaded_file = st.file_uploader("Pilih file CSV", type=["csv"])
            if uploaded_file is not None:
                if st.button("Mulai Import File"):
                    try:
                        df_import = pd.read_csv(uploaded_file)
                        df_import.columns = [c.strip() for c in df_import.columns]
                        
                        # Filter ID double
                        existing_ids = set(str(x).strip().lower() for x in st.session_state.employees["ID"].values)
                        initial_count = len(df_import)
                        
                        df_import_filtered = df_import[~df_import["ID"].astype(str).str.strip().str.lower().isin(existing_ids)]
                        added_count = len(df_import_filtered)
                        skipped_count = initial_count - added_count
                        
                        if added_count > 0:
                            st.session_state.employees = pd.concat([st.session_state.employees, df_import_filtered], ignore_index=True)
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
                placeholder="EMP-005\tBudi Santoso\tDeveloper\tCC-101\t2024-01-15\t2025-01-15",
                height=150
            )
            if st.button("Mulai Import Teks"):
                if pasted_text.strip():
                    lines = pasted_text.strip().split("\n")
                    added_count = 0
                    skipped_count = 0
                    existing_ids = set(str(x).strip().lower() for x in st.session_state.employees["ID"].values)

                    for line in lines:
                        delimiter = "\t" if "\t" in line else (";" if ";" in line else ",")
                        cols = [c.strip() for c in line.split(delimiter)]
                        if len(cols) >= 4:
                            emp_id, name, role_title, cc = cols[0], cols[1], cols[2], cols[3]
                            join_d = cols[4] if len(cols) > 4 else ""
                            end_d = cols[5] if len(cols) > 5 else ""
                            
                            # Cek ID Duplikat
                            if emp_id.lower() not in existing_ids:
                                new_row = {
                                    "ID": emp_id, "Nama Lengkap": name, "Jabatan": role_title,
                                    "Cost Center": cc, "Tanggal Bergabung": join_d, "Akhir Kontrak": end_d
                                }
                                st.session_state.employees = pd.concat([st.session_state.employees, pd.DataFrame([new_row])], ignore_index=True)
                                existing_ids.add(emp_id.lower())
                                added_count += 1
                            else:
                                skipped_count += 1

                    if added_count > 0:
                        st.success(f"Berhasil menambahkan {added_count} data baru!")
                        if skipped_count > 0:
                            st.warning(f"Dilewati {skipped_count} data karena ID duplikat.")
                        st.rerun()
                    else:
                        st.error("Tidak ada data baru yang ditambahkan (semua ID sudah terdaftar).")

    # 3. Export Data CSV
    st.sidebar.markdown("---")
    csv_data = st.session_state.employees.to_csv(index=False).encode('utf-8-sig')
    st.sidebar.download_button(
        label="📤 Ekspor Data (CSV)",
        data=csv_data,
        file_name="ekspor_database_karyawan.csv",
        mime="text/csv",
        use_container_width=True
    )

# --- HALAMAN UTAMA (Tampilan Data untuk Semua Pengguna) ---

# Status Banner Mode Akses
if is_admin:
    st.info("🔓 **Mode Akses:** Administrator (Dapat menambah, mengubah, atau menghapus data)")
else:
    st.info("👁️ **Mode Akses:** Umum / Guest (Hanya dapat melihat dan mencari data)")

# Fitur Pencarian
search_query = st.text_input("🔍 Cari nama karyawan...", "")

df_display = st.session_state.employees.copy()
if search_query:
    df_display = df_display[df_display["Nama Lengkap"].str.contains(search_query, case=False, na=False)]

# Tabel Tampilan Karyawan
if df_display.empty:
    st.warning("Tidak ada data karyawan yang cocok dengan pencarian.")
else:
    st.dataframe(df_display, use_container_width=True)


# --- EDIT / HAPUS SATUAN (HANYA AKTIF DI MODE ADMINISTRATOR) ---
if is_admin:
    st.divider()
    st.subheader("🛠️ Kelola / Edit / Hapus Data Karyawan")
    
    selected_id = st.selectbox("Pilih ID Karyawan untuk Diubah / Dihapus:", options=["-- Pilih ID --"] + list(st.session_state.employees["ID"]))

    if selected_id != "-- Pilih ID --":
        emp_idx = st.session_state.employees[st.session_state.employees["ID"] == selected_id].index[0]
        row = st.session_state.employees.loc[emp_idx]

        with st.form("edit_form"):
            st.write(f"Editing: **{row['Nama Lengkap']}** (ID: `{row['ID']}`)")
            e_name = st.text_input("Nama Lengkap", value=row["Nama Lengkap"])
            e_role = st.text_input("Jabatan", value=row["Jabatan"])
            e_cc = st.text_input("Cost Center", value=row["Cost Center"])
            e_join = st.text_input("Tanggal Bergabung (YYYY-MM-DD)", value=row["Tanggal Bergabung"])
            e_end = st.text_input("Akhir Kontrak (YYYY-MM-DD)", value=row["Akhir Kontrak"])

            col_save, col_del = st.columns(2)
            with col_save:
                btn_save = st.form_submit_button("💾 Simpan Perubahan")
            with col_del:
                btn_del = st.form_submit_button("🗑️ Hapus Karyawan")

            if btn_save:
                st.session_state.employees.loc[emp_idx, ["Nama Lengkap", "Jabatan", "Cost Center", "Tanggal Bergabung", "Akhir Kontrak"]] = [e_name, e_role, e_cc, e_join, e_end]
                st.success("Data berhasil diperbarui!")
                st.rerun()

            if btn_del:
                st.session_state.employees = st.session_state.employees.drop(emp_idx).reset_index(drop=True)
                st.success("Data karyawan berhasil dihapus!")
                st.rerun()
