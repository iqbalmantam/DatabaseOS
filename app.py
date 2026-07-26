import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Import modul AI Chatbot yang dibuat di file terpisah
from ai_bot import render_ai_bot_tab

# --- CONFIG APLIKASI ---
st.set_page_config(
    page_title="Employee Database Manager",
    page_icon="👥",
    layout="wide"
)

# --- CONNECTOR GOOGLE SHEETS ---
@st.cache_data(ttl=600)  # Cache data selama 10 menit
def load_data_from_gsheets():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    # Mengambil Service Account Credentials dari Streamlit Secrets
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # Buka Google Sheet berdasarkan Nama atau Key (Sesuaikan nama Sheet kamu)
    sheet = client.open(st.secrets["gsheets"]["spreadsheet_name"]).sheet1
    data = sheet.get_all_records()
    
    return pd.DataFrame(data)

# --- MAIN APP ---
def main():
    st.title("👥 Employee Database Manager")
    
    # Load Data Karyawan dari Google Sheets
    try:
        df_employee = load_data_from_gsheets()
    except Exception as e:
        st.error(f"Gagal mengambil data dari Google Sheets: {e}")
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
        
        # Filter Sederhana
        col1, col2 = st.columns(2)
        with col1:
            search_name = st.text_input("🔍 Cari Nama Karyawan")
        with col2:
            departments = ["Semua"] + list(df_employee["Departemen"].unique()) if "Departemen" in df_employee.columns else ["Semua"]
            selected_dept = st.selectbox("🏢 Filter Departemen", departments)

        # Apply Filter
        filtered_df = df_employee.copy()
        if search_name:
            filtered_df = filtered_df[filtered_df["Nama"].str.contains(search_name, case=False, na=False)]
        if selected_dept != "Semua":
            filtered_df = filtered_df[filtered_df["Departemen"] == selected_dept]

        st.dataframe(filtered_df, use_container_width=True)

    # TAB 2: SNAPSHOT & RESIGN
    with tab_snapshot:
        st.subheader("Laporan Snapshot Bulanan")
        st.write("Area untuk mengelola data snapshot historis dan status karyawan resign.")
        # Tempatkan logika/fitur snapshot kamu di sini
        if "Status" in df_employee.columns:
            resigned_df = df_employee[df_employee["Status"].str.lower() == "resign"]
            st.metric("Total Karyawan Resign", len(resigned_df))
            st.dataframe(resigned_df, use_container_width=True)

    # TAB 3: INTEGRASI AI CHATBOT
    with tab_ai:
        # Memanggil fungsi AI Bot dari file ai_bot.py
        render_ai_bot_tab(df_employee)

if __name__ == "__main__":
    main()
