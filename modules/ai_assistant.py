import pandas as pd
import streamlit as st

from services.ai import get_groq_client, generate_ai_response

def render_page():
    st.title("🤖 AI HR Assistant")
    st.caption("Asisten AI cerdas terintegrasi dengan Database Karyawan & Manpower Cost.")

    client = get_groq_client()
    if client is None:
        st.error("⚠️ API Key Groq belum dikonfigurasi di secrets.toml! Silakan tambahkan GROQ_API_KEY.")
        st.stop()

    df_emp = st.session_state.get("employees", pd.DataFrame())

    if not df_emp.empty and "Status" in df_emp.columns:
        df_aktif = df_emp[df_emp["Status"].astype(str).str.strip().str.title() == "Aktif"].copy()
        df_resign = df_emp[df_emp["Status"].astype(str).str.strip().str.title() == "Resign"].copy()
        total_emp = len(df_emp)
        aktif_emp = len(df_aktif)
        resign_emp = len(df_resign)
    else:
        df_aktif = df_emp.copy() if not df_emp.empty else pd.DataFrame()
        df_resign = pd.DataFrame()
        total_emp = len(df_emp)
        aktif_emp, resign_emp = total_emp, 0

    resign_monthly_summary = ""
    if not df_resign.empty and "Tanggal Resign" in df_resign.columns:
        df_resign_clean = df_resign.copy()
        bulan_map = {
            1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
            7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
        }

        def parse_month_year(date_val):
            if pd.isna(date_val):
                return None, None
            d_str = str(date_val).strip()
            if not d_str or d_str in ["-", "nan", "None", "", "NaT"]:
                return None, None
            try:
                dt_parsed = pd.to_datetime(d_str, format="%Y-%m-%d", errors="coerce")
                if pd.notna(dt_parsed):
                    return bulan_map.get(dt_parsed.month), int(dt_parsed.year)
            except Exception:
                pass
            dt_fallback = pd.to_datetime(d_str, errors="coerce")
            if pd.notna(dt_fallback):
                return bulan_map.get(dt_fallback.month), int(dt_fallback.year)
            return None, None

        parsed_results = df_resign_clean["Tanggal Resign"].apply(parse_month_year)
        df_resign_clean["Bulan_Resign"] = [r[0] for r in parsed_results]
        df_resign_clean["Tahun_Resign"] = [r[1] for r in parsed_results]

        df_resign_parsed = df_resign_clean.dropna(subset=["Bulan_Resign", "Tahun_Resign"])

        if not df_resign_parsed.empty:
            resign_counts = df_resign_parsed.groupby(["Bulan_Resign", "Tahun_Resign"]).size().reset_index(name="Jumlah")
            items_resign = [f"{r['Bulan_Resign']} {int(r['Tahun_Resign'])}: {r['Jumlah']} orang" for _, r in resign_counts.iterrows()]
            resign_monthly_summary = ", ".join(items_resign)

    site_summary = ""
    if not df_aktif.empty and "Site" in df_aktif.columns:
        site_counts = df_aktif["Site"].astype(str).str.strip().str.upper().value_counts().to_dict()
        site_summary = ", ".join([f"{k}: {v} orang" for k, v in site_counts.items() if k and k != "NAN"])

    site_posisi_summary = ""
    if not df_aktif.empty and "Site" in df_aktif.columns and "Posisi" in df_aktif.columns:
        df_grouped = df_aktif.groupby(["Site", "Posisi"])["ID"].count().reset_index(name="Jumlah")
        grouped_items = []
        for _, row in df_grouped.iterrows():
            site_val = str(row["Site"]).strip().upper()
            pos_val = str(row["Posisi"]).strip()
            cnt_val = row["Jumlah"]
            if site_val and site_val != "NAN" and pos_val and pos_val != "NAN":
                grouped_items.append(f"[{site_val} - {pos_val}: {cnt_val} orang]")
        site_posisi_summary = ", ".join(grouped_items)

    cc_summary = ""
    if not df_aktif.empty and "Cost Center" in df_aktif.columns:
        df_cc_clean = df_aktif["Cost Center"].astype(str).str.strip().str.upper().replace({"": "BELUM DIISI"})
        cc_counts = df_cc_clean.value_counts().to_dict()
        cc_summary = ", ".join([f"{k}: {v} orang" for k, v in cc_counts.items() if k and k != "NAN"])

    mp_proj_summary = ""
    df_mc_session = st.session_state.get("df_manpower_cost", pd.DataFrame())
    if not df_mc_session.empty and "Project" in df_mc_session.columns:
        proj_counts = df_mc_session["Project"].astype(str).str.strip().str.upper().value_counts().to_dict()
        mp_proj_summary = ", ".join([f"{k}: {v} orang" for k, v in proj_counts.items() if k and k != "NAN"])

    system_prompt_context = f"""
    Anda adalah Asisten AI HR internal perusahaan yang cerdas, presisi, dan ramah.
    Anda memiliki akses langsung ke data realtime database berikut:

    📊 RINGKASAN UMUM DATABASE KARYAWAN:
    - Total Record Data Karyawan: {total_emp} orang
    - Karyawan Aktif: {aktif_emp} orang
    - Total Karyawan Resign: {resign_emp} orang
    - Rincian Resign per Bulan (SANGAT PENTING): {resign_monthly_summary if resign_monthly_summary else f'Total {resign_emp} orang resign'}
    - Total Karyawan per Site/Lokasi: {site_summary if site_summary else 'Belum ada data'}

    🔥 RINCIAN POSISI PER SITE (LOKASI KERJA):
    {site_posisi_summary if site_posisi_summary else 'Belum ada data detail'}

    💳 SELURUH COST CENTER / PROJECT (MASTER KARYAWAN):
    {cc_summary if cc_summary else 'Belum ada data'}

    📋 DATA PROJECT (TAB MANPOWER COST):
    {mp_proj_summary if mp_proj_summary else 'Belum ada data Manpower Cost'}

    PETUNJUK BALASAN DENGAN PRIORITAS TINGGI:
    1. Jika pengguna menanyakan jumlah karyawan resign pada bulan tertentu (misal: Juli, Juni, dst.), BACA bagian "Rincian Resign per Bulan" dan jawab angka pasti untuk bulan tersebut.
    2. Jawab selalu menggunakan bahasa Indonesia yang sopan, ramah, dan profesional.
    """

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {
                "role": "assistant",
                "content": f"Halo! Saya AI HR Assistant. Saya telah membaca seluruh database ({aktif_emp} Karyawan Aktif & {resign_emp} Karyawan Resign). Silakan tanyakan jumlah karyawan berdasarkan Cost Center, Project, Lokasi Site, maupun Rincian Resign Bulanan!",
            }
        ]

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Tanyakan sesuatu (misal: 'berapa orang yang resign di bulan juni?')..."):
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Mencari data database..."):
                try:
                    api_messages = [{"role": "system", "content": system_prompt_context}] + [
                        {"role": m["role"], "content": m["content"]} for m in st.session_state.chat_messages
                    ]
                    response_text = generate_ai_response(client, api_messages)
                    st.markdown(response_text)
                    st.session_state.chat_messages.append({"role": "assistant", "content": response_text})
                except Exception as e:
                    st.error(f"❌ Terjadi kesalahan pada AI: {e}")
