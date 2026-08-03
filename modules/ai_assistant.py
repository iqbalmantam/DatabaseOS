import streamlit as st
import pandas as pd
from groq import Groq
from services.gsheet import load_master_data

def generate_ai_context(df):
    """Membuat ringkasan teks otomatis dari DataFrame untuk dibaca oleh Groq AI."""
    if df.empty:
        return "Data karyawan saat ini kosong."
    
    total_emp = len(df)
    
    # Ringkasan per Site
    site_summary = df['Site'].value_counts().to_dict() if 'Site' in df.columns else {}
    
    # Ringkasan per Cost Center
    cc_summary = df['Cost Center'].value_counts().to_dict() if 'Cost Center' in df.columns else {}
    
    # Ringkasan Karyawan Aktif vs Resign
    status_summary = df['Status'].value_counts().to_dict() if 'Status' in df.columns else {}
    
    # Kross-Filter Site vs Cost Center
    cross_summary = {}
    if 'Site' in df.columns and 'Cost Center' in df.columns:
        cross_df = df.groupby(['Site', 'Cost Center']).size().reset_index(name='Jumlah')
        for _, row in cross_df.iterrows():
            s, cc, j = row['Site'], row['Cost Center'], row['Jumlah']
            if s not in cross_summary:
                cross_summary[s] = {}
            cross_summary[s][cc] = j

    # Format Teks Konteks
    context = f"""
    BERIKUT ADALAH DATA REKAP DATABASE KARYAWAN TERBARU:
    - Total Karyawan dalam Database: {total_emp} orang
    - Ringkasan Status: {status_summary}
    - Rincian Jumlah Karyawan per Site: {site_summary}
    - Rincian Jumlah Karyawan per Cost Center: {cc_summary}
    
    - RINCIAN KOMBINASI (SITE -> COST CENTER):
    {cross_summary}
    """
    return context

def render_page(is_admin=False):
    st.title("🤖 AI HR Assistant")
    st.caption("Created by iqbalmantam")
    st.info("Tanyakan informasi seputar data karyawan, statistik site, cost center, atau aturan HR.")

    # Ambil data master
    if "employees" not in st.session_state or st.session_state.employees.empty:
        st.session_state.employees = load_master_data()

    df_master = st.session_state.employees

    # Siapkan Groq Client
    groq_api_key = st.secrets.get("GROQ_API_KEY", "")
    if not groq_api_key:
        st.error("🔑 GROQ_API_KEY belum dikonfigurasi di Streamlit Secrets.")
        return

    client = Groq(api_key=groq_api_key)

    # Inisialisasi riwayat chat
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Tampilkan riwayat chat
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Input User
    if user_prompt := st.chat_input("Tanyakan sesuatu... (misal: Berapa jumlah karyawan JDC dengan Cost Center Transport?)"):
        # Tampilkan pesan user
        st.chat_message("user").markdown(user_prompt)
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})

        # Buat System Prompt Dinamis membawa Data Konteks
        data_context = generate_ai_context(df_master)
        system_prompt = f"""
        Anda adalah AI HR Assistant profesional untuk perusahaan. 
        Tugas Anda adalah menjawab pertanyaan pengguna secara akurat berdasarkan data karyawan berikut.
        
        {data_context}
        
        Aturan Jawaban:
        1. Jawablah pertanyaan pengguna dengan sopan, jelas, dan langsung pada inti angka/informasinya.
        2. Jika pengguna menanyakan kombinasi Site dan Cost Center (misal: JDC dan Transport), periksa bagian RINCIAN KOMBINASI pada data di atas.
        3. Jangan katakan 'Saya tidak memiliki informasi' jika data kombinasi tersebut ada di dalam konteks di atas.
        """

        # Panggil Groq API
        messages_for_api = [{"role": "system", "content": system_prompt}]
        for msg in st.session_state.chat_history[-5:]: # Ambil 5 riwayat terakhir
            messages_for_api.append({"role": msg["role"], "content": msg["content"]})

        with st.chat_message("assistant"):
            with st.spinner("Berpikir..."):
                try:
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=messages_for_api,
                        temperature=0.2,
                    )
                    ai_response = response.choices[0].message.content
                    st.markdown(ai_response)
                    st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
                except Exception as e:
                    st.error(f"Gagal memproses pesan AI: {e}")
