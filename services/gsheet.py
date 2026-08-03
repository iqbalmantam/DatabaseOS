from datetime import date
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection


def get_connection():
    # Menginisialisasi koneksi gsheets dari secrets
    return st.connection("gsheets", type=GSheetsConnection)


def load_master_data():
    conn = get_connection()
    try:
        # Membaca worksheet spesifik dari koneksi
        df = conn.read(worksheet="Master_Karyawan", ttl=0)
        if df is not None and not df.empty:
            if "ID" in df.columns:
                df["ID"] = df["ID"].astype(str).str.strip().str.upper()
            if "Jabatan" in df.columns and "Posisi" not in df.columns:
                df.rename(columns={"Jabatan": "Posisi"}, inplace=True)
            if "Site" not in df.columns:
                df["Site"] = ""
            if "Status" not in df.columns:
                df["Status"] = "Aktif"
            if "Tanggal Resign" not in df.columns:
                df["Tanggal Resign"] = "-"
            if "Terakhir Diperbarui" not in df.columns:
                df["Terakhir Diperbarui"] = str(date.today())
        return df if df is not None else pd.DataFrame()
    except Exception as e:
        # Fallback jika nama worksheet tidak ditemukan
        try:
            df = conn.read(ttl=0)
            if df is not None and not df.empty:
                if "ID" in df.columns:
                    df["ID"] = df["ID"].astype(str).str.strip().str.upper()
                if "Jabatan" in df.columns and "Posisi" not in df.columns:
                    df.rename(columns={"Jabatan": "Posisi"}, inplace=True)
                if "Site" not in df.columns:
                    df["Site"] = ""
                if "Status" not in df.columns:
                    df["Status"] = "Aktif"
                if "Tanggal Resign" not in df.columns:
                    df["Tanggal Resign"] = "-"
                if "Terakhir Diperbarui" not in df.columns:
                    df["Terakhir Diperbarui"] = str(date.today())
            return df if df is not None else pd.DataFrame()
        except Exception as ex:
            st.error(f"Gagal terhubung ke Google Sheets: {ex}")
            return pd.DataFrame(
                columns=[
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
                ]
            )


def load_snapshot_data():
    conn = get_connection()
    try:
        df_snap = conn.read(worksheet="Snapshot_Bulanan", ttl=0)
        return df_snap if df_snap is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def save_master_data(df):
    conn = get_connection()
    clean_df = df.fillna("")
    conn.update(worksheet="Master_Karyawan", data=clean_df)
    st.session_state.employees = clean_df


def save_snapshot_data(df):
    conn = get_connection()
    clean_df = df.fillna("")
    conn.update(worksheet="Snapshot_Bulanan", data=clean_df)


def load_absensi_data():
    conn = get_connection()
    try:
        df_absen = conn.read(worksheet="Absensi_Karyawan", ttl=0)
        if df_absen is not None and not df_absen.empty:
            df_absen["ID"] = df_absen["ID"].astype(str).str.strip().str.upper()
            df_absen["Nama Lengkap"] = (
                df_absen["Nama Lengkap"].astype(str).str.strip().str.title()
            )
            df_absen["Tanggal"] = pd.to_datetime(
                df_absen["Tanggal"]
            ).dt.strftime("%Y-%m-%d")
            if "Status" not in df_absen.columns:
                df_absen["Status"] = "Hadir"
        return df_absen if df_absen is not None else pd.DataFrame()
    except Exception:
        return pd.DataFrame(
            columns=[
                "ID",
                "Nama Lengkap",
                "Site",
                "Job Title",
                "Tanggal",
                "In",
                "Out",
                "Shift",
                "Status",
            ]
        )


def save_absensi_data(df):
    conn = get_connection()
    clean_df = df.fillna("")
    conn.update(worksheet="Absensi_Karyawan", data=clean_df)


def load_manpower_cost_data(headers):
    conn = get_connection()
    df_mc = None
    try:
        df_mc = conn.read(worksheet="Manpower_Cost", ttl=0)
    except Exception:
        try:
            df_mc = conn.read(ttl=0)
        except Exception:
            df_mc = None

    if df_mc is not None and isinstance(df_mc, pd.DataFrame) and not df_mc.empty:
        df_mc.columns = [str(c).strip() for c in df_mc.columns]
        col_map = {str(c).strip().lower(): c for c in df_mc.columns}

        new_df = pd.DataFrame()
        for target_col in headers:
            key = target_col.strip().lower()
            if key in col_map:
                new_df[target_col] = df_mc[col_map[key]]
            else:
                new_df[target_col] = ""

        if "Month" in new_df.columns:
            new_df = new_df[new_df["Month"].astype(str).str.strip() != ""]

        return new_df

    return pd.DataFrame(columns=headers)


def save_manpower_data(df):
    conn = get_connection()
    clean_mc = df.fillna("")
    try:
        conn.update(worksheet="Manpower_Cost", data=clean_mc)
    except Exception:
        conn.update(data=clean_mc)
