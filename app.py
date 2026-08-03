import streamlit as st
from utils.auth import check_password, check_admin_pin
from modules import master, attendance, manpower, ai_assistant

# Set Halaman Streamlit
st.set_page_config(
    page_title="Employee Database Manager", page_icon="👥", layout="wide"
)

# Sembunyikan Toolbar default Streamlit
st.markdown(
    """
    <style>
    div[data-testid="stToolbarActions"] { display: none !important; }
    div[data-testid="stDecoration"] { display: none !important; }
    #MainMenu { visibility: hidden !important; }
    [data-testid="stCollapsedControl"] { display: flex !important; visibility: visible !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Autentikasi Password Utama
if not check_password():
    st.stop()

# Sidebar Control
if st.sidebar.button("🚪 Keluar Aplikasi"):
    st.session_state["app_password_correct"] = False
    st.session_state["manpower_authenticated"] = False
    st.rerun()

st.sidebar.markdown("---")

# Otentikasi Admin
is_admin = check_admin_pin()

# Navigasi Menu Utama
st.sidebar.header("📁 Menu Utama")
menu_pilihan = st.sidebar.radio(
    "Pilih Halaman:",
    [
        "👥 Master Data Karyawan",
        "⏱️ Rekap Absensi (Timesheet)",
        "💳 Manpower Cost Manager",
        "🤖 AI HR Assistant",
    ],
)
st.sidebar.markdown("---")

# Routing Ke Modul Terkait
if menu_pilihan == "👥 Master Data Karyawan":
    master.render_page(is_admin)

elif menu_pilihan == "⏱️ Rekap Absensi (Timesheet)":
    attendance.render_page(is_admin)

elif menu_pilihan == "💳 Manpower Cost Manager":
    manpower.render_page(is_admin)

elif menu_pilihan == "🤖 AI HR Assistant":
    ai_assistant.render_page()
