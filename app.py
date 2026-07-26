import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google import genai

# ==========================================
# 1. KONFIGURASI APLIKASI STREAMLIT
# ==========================================
st.set_page_config(
    page_title="Employee Database Manager",
    page_icon="👥",
    layout="wide"
)

# ==========================================
# 2. CONNECTOR GOOGLE SHEETS & GEMINI CLIENT
# ==========================================
@st.cache_data(ttl=600)  # Cache data selama 10 menit
def load_data_from_gsheets():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    # Mengambil Credentials dari Streamlit Secrets
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # Buka Google Sheet berdasarkan Spreadsheet ID
    sheet = client.open_by_key(st.secrets["gsheets"]["spreadsheet_id"]).sheet1
    data = sheet.get_all_records()
    
    return pd.DataFrame(data)

@st.cache_resource
def get_gemini_client():
    # Inisialisasi Gemini Client menggunakan API Key dari Streamlit Secrets
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# ==========================================
# 3. MODUL AI HR ASSISTANT CHATBOT
# ==========================================
def render_ai_bot_tab(df: pd.DataFrame):
    st.subheader("🤖 HR Data Assistant (AI Query)")
    st.caption("Tanyakan data karyawan menggunakan bahasa sehari-hari. AI akan menganalisis data secara otomatis.")

    # Inisialisasi Riwayat Chat
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Halo! Ada yang bisa saya bantu terkait data karyawan hari ini?"}
        ]

    # Menampilkan Riwayat Chat
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Input Query dari User
    if user_query := st.chat_input("Contoh: Tampilkan grafik jumlah karyawan per Cost Center"):
        # Tampilkan pesan user
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.write(user_query)

        # Proses dengan Gemini
        with st.chat_message("assistant"):
            with st.spinner("Menganalisis data..."):
                try:
                    client = get_gemini_client()

                    # Informasi skema data saja (Aman & menjaga privasi)
                    data_schema = f"""
                    DataFrame bernama `df` memiliki kolom berikut:
                    {df.dtypes.to_string()}

                    Sampel data (2 baris):
                    {df.head(2).to_dict(orient='records')}
                    """

                    prompt = f"""
                    Kamu adalah Data Analyst profesional untuk sistem HR.
                    Berikut adalah struktur dataframe `df`:
                    {data_schema}

                    Pertanyaan User: "{user_query}"

                    TUGAS:
                    Tuliskan KODE PYTHON SAJA untuk menjawab pertanyaan di atas.

                    ATURAN KODE:
                    1. Gunakan variabel `df` yang sudah ada.
                    2. Simpan hasil jawaban teks atau dataframe ke variabel `result`.
                    3. Jika user meminta grafik/chart, gunakan Plotly Express (`px`) dan simpan ke variabel `fig`.
                    4. Sertakan HANYA kode di dalam block ```python ... ``` tanpa teks penjelasan lain di luar block.
                    """

                    response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                    )

                    # Extract kode Python dari response Gemini
                    raw_text = response.text
                    code_block = raw_text.split("```python")[1].split("```")[0].strip()

                    # Eksekusi Kode secara Lokal di Server Streamlit
                    local_env = {"df": df, "px": px, "pd": pd}
                    exec(code_block, globals(), local_env)

                    # Tampilkan Output Grafis atau Teks
                    if "fig" in local_env:
                        st.plotly_chart(local_env["fig"], use_container_width=True)
                        st.session_state.chat_history.append({"role": "assistant", "content": "[Menampilkan Visualisasi Grafik]"})
                    
                    if "result" in local_env:
                        res = local_env["result"]
                        if isinstance(res, pd.DataFrame):
                            st.dataframe(res, use_container_width=True)
                        else:
                            st.write(res)
                        st.session_state.chat_history.append({"role": "assistant", "content": str(res)})

                except Exception as e:
                    st.error(f"Gagal memproses pertanyaan: {str(e)}")
                    st.caption("Coba tanyakan dengan kalimat atau kata kunci yang lebih spesifik.")

# ==========================================
# 4. APLIKASI UTAMA (MAIN APP)
# ==========================================
def main():
    st.title("👥 Employee Database Manager")
    
    # Load Data Karyawan dari Google Sheets
    try:
        df_employee = load_data_from_gsheets()
    except Exception as e:
        st.error("❌ Gagal mengambil data dari Google Sheets. Detail Error:")
        st.exception(e)
        st.stop()

    # --- TAMPILAN SIDEBAR ---
    st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
    st.sidebar.title("Navigasi HR")
    st.sidebar.info(f"Total Karyawan Terdata: **{len(df_employee)}** orang")
    
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    # --- TAB APLIKASI ---
    tab_master, tab_snapshot, tab_ai = st.tabs([
        "📋 Master Data Karyawan", 
        "📸 Snapshot Bulanan & Resign", 
        "🤖 AI HR Assistant"
    ])

    # TAB 1: MASTER DATA
    with tab_master:
        st.subheader("Data Karyawan Aktif")
        
        col1, col2, col3 = st.columns(3)
        
        # Deteksi nama kolom agar sesuai dengan Google Sheets
        name_col = "Nama Lengkap" if "Nama Lengkap" in df_employee.columns else ("Nama" if "Nama" in df_employee.columns else None)
        dept_col = "Cost Center" if "Cost Center" in df_employee.columns else ("Departemen" if "Departemen" in df_employee.columns else None)
        
        with col1:
            search_name = st.text_input("🔍 Cari Nama Karyawan")
        with col2:
            if dept_col and dept_col in df_employee.columns:
                departments = ["Semua"] + [str(d) for d in df_employee[dept_col].unique() if d]
            else:
                departments = ["Semua"]
            selected_dept = st.selectbox("🏢 Filter Cost Center / Dept", departments)
        with col3:
            if "Site" in df_employee.columns:
                sites = ["Semua"] + [str(s) for s in df_employee["Site"].unique() if s]
            else:
                sites = ["Semua"]
            selected_site = st.selectbox("📍 Filter Site", sites)

        # Penerapan Filter Data
        filtered_df = df_employee.copy()
        
        if search_name and name_col in filtered_df.columns:
            filtered_df = filtered_df[filtered_df[name_col].astype(str).str.contains(search_name, case=False, na=False)]
            
        if selected_dept != "Semua" and dept_col:
            filtered_df = filtered_df[filtered_df[dept_col].astype(str) == selected_dept]

        if selected_site != "Semua" and "Site" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Site"].astype(str) == selected_site]

        st.dataframe(filtered_df, use_container_width=True)

    # TAB 2: SNAPSHOT & RESIGN
    with tab_snapshot:
        st.subheader("Laporan Snapshot Bulanan")
        st.write("Area untuk mengelola data snapshot historis dan status karyawan resign.")
        
        if "Status" in df_employee.columns:
            resigned_df = df_employee[df_employee["Status"].astype(str).str.lower() == "resign"]
            active_df = df_employee[df_employee["Status"].astype(str).str.lower() == "aktif"]
            
            m1, m2 = st.columns(2)
            m1.metric("Total Karyawan Aktif", len(active_df))
            m2.metric("Total Karyawan Resign", len(resigned_df))
            
            st.markdown("### Daftar Karyawan Resign")
            st.dataframe(resigned_df, use_container_width=True)
        else:
            st.info("Kolom 'Status' tidak ditemukan dalam data saat ini.")

    # TAB 3: INTEGRASI AI CHATBOT
    with tab_ai:
        render_ai_bot_tab(df_employee)

if __name__ == "__main__":
    main()
