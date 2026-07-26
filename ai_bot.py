import streamlit as st
import pandas as pd
import plotly.express as px
from google import genai

@st.cache_resource
def get_gemini_client():
    # Mengambil Gemini API Key dari Streamlit Secrets
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

def render_ai_bot_tab(df: pd.DataFrame):
    st.subheader("🤖 HR Data Assistant")
    st.caption("Tanyakan data karyawan menggunakan bahasa sehari-hari. AI akan menganalisis data secara otomatis.")

    # 1. Inisialisasi Riwayat Chat
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Halo! Ada yang bisa saya bantu terkait data karyawan hari ini?"}
        ]

    # 2. Tampilkan Riwayat Chat
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # 3. Input Pertanyaan User
    if user_query := st.chat_input("Contoh: Tampilkan grafik jumlah karyawan per divisi"):
        # Tampilkan pesan user
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.write(user_query)

        # 4. Proses dengan Gemini API
        with st.chat_message("assistant"):
            with st.spinner("Menganalisis data..."):
                try:
                    client = get_gemini_client()

                    # Informasi skema data saja (Aman: Tanpa mengirim seluruh data sensitif ke API)
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

                    # Eksekusi Kode secara Lokal di Streamlit
                    local_env = {"df": df, "px": px, "pd": pd}
                    exec(code_block, globals(), local_env)

                    # Tampilkan Hasil
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
                    st.caption("Coba tanyakan dengan kalimat yang lebih spesifik.")
