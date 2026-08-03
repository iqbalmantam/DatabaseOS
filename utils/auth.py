import streamlit as st

def check_password():
    """Memeriksa password aplikasi utama."""
    def password_entered():
        if st.session_state.get("app_password_input") == st.secrets.get("PASSWORD"):
            st.session_state["app_password_correct"] = True
            if "app_password_input" in st.session_state:
                del st.session_state["app_password_input"]
        else:
            st.session_state["app_password_correct"] = False

    if not st.session_state.get("app_password_correct", False):
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🔒 Employee Database Manager")
            st.caption("Silakan masukkan password untuk mengakses aplikasi.")
            st.text_input(
                "Masukkan Password:",
                type="password",
                on_change=password_entered,
                key="app_password_input",
            )
            if "app_password_correct" in st.session_state and not st.session_state["app_password_correct"]:
                st.error("❌ Password salah. Silakan coba lagi.")
        return False
    return True

def check_manpower_access():
    """Memeriksa akses khusus Manpower Cost Manager."""
    if "manpower_authenticated" not in st.session_state:
        st.session_state["manpower_authenticated"] = False

    if st.session_state["manpower_authenticated"]:
        return True

    st.title("🔒 Manpower Cost Manager")
    st.warning("Halaman ini berisi data sensitif finansial dan rahasia perusahaan.")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("form_manpower_auth", clear_on_submit=True):
            st.subheader("Otorisasi Diperlukan")
            input_pass = st.text_input("Masukkan Password Akses Manpower Cost:", type="password")
            btn_submit = st.form_submit_button("Buka Akses Dashboard", use_container_width=True)

            if btn_submit:
                correct_pass = st.secrets.get("MANPOWER_PASSWORD", "PasswordManpower2026!")
                if input_pass == correct_pass:
                    st.session_state["manpower_authenticated"] = True
                    st.success("Akses Diterima! Memuat data...")
                    st.rerun()
                else:
                    st.error("❌ Password salah. Silakan coba lagi.")
    return False

def check_admin_pin():
    """Mengecek otentikasi PIN Administrator di Sidebar."""
    admin_pin = st.secrets.get("ADMIN_PIN", "2273")
    st.sidebar.header("🔐 Akses Pengguna")
    role = st.sidebar.radio("Pilih Mode Akses:", ["Umum (View Only)", "Administrator"])

    is_admin = False
    if role == "Administrator":
        pin_input = st.sidebar.text_input("Masukkan PIN Admin:", type="password")
        if pin_input == admin_pin:
            st.sidebar.success("Akses Administrator Aktif!")
            is_admin = True
        elif pin_input != "":
            st.sidebar.error("PIN Salah!")
        else:
            st.sidebar.info("Masukkan PIN Administrator.")
    return is_admin
