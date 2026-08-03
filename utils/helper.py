import re
import pandas as pd
import streamlit as st

def format_rp_short(val):
    if val >= 1e9:
        return f"Rp {val/1e9:.2f} M".replace(".", ",")
    elif val >= 1e6:
        return f"Rp {val/1e6:.1f} Jt".replace(".", ",")
    elif val > 0:
        return f"Rp {val:,.0f}".replace(",", ".")
    return "Rp 0"

def to_num(series):
    def parse_val(val):
        if pd.isna(val):
            return 0.0
        s = str(val).strip()
        if not s or s.lower() in ["nan", "none", "-", ""]:
            return 0.0

        s_clean = re.sub(r"[^\d.,-]", "", s)
        if not s_clean:
            return 0.0

        if "," in s_clean and "." in s_clean:
            if s_clean.rfind(",") > s_clean.rfind("."):
                s_clean = s_clean.replace(".", "").replace(",", ".")
            else:
                s_clean = s_clean.replace(",", "")
        elif "," in s_clean:
            parts = s_clean.split(",")
            if len(parts) == 2 and len(parts[1]) <= 2:
                s_clean = s_clean.replace(",", ".")
            else:
                s_clean = s_clean.replace(",", "")
        elif "." in s_clean:
            parts = s_clean.split(".")
            if len(parts) > 2:
                s_clean = s_clean.replace(".", "")
            elif len(parts) == 2 and len(parts[1]) == 3:
                s_clean = s_clean.replace(".", "")

        try:
            return float(s_clean)
        except ValueError:
            return 0.0

    return series.apply(parse_val)

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

def filter_status_for_period(df, target_period, selected_dash_period):
    if df.empty:
        return df, pd.DataFrame(), pd.DataFrame()

    df_copy = df.copy()
    target_dt = pd.to_datetime(target_period + "-01", errors="coerce")

    active_rows = []
    resign_rows = []

    for _, row in df_copy.iterrows():
        join_date_str = str(row.get("Tanggal Bergabung", ""))
        resign_date_str = str(row.get("Tanggal Resign", ""))
        status_curr = str(row.get("Status", "Aktif")).strip().title()

        join_dt = pd.to_datetime(join_date_str, errors="coerce")
        resign_dt = pd.to_datetime(resign_date_str, errors="coerce")

        joined_in_time = True
        if pd.notna(join_dt) and pd.notna(target_dt):
            if join_dt.strftime("%Y-%m") > target_period:
                joined_in_time = False

        if not joined_in_time:
            continue

        is_resign_this_month = False
        is_still_active = True

        if pd.notna(resign_dt) and pd.notna(target_dt):
            resign_month = resign_dt.strftime("%Y-%m")
            if resign_month == target_period:
                is_resign_this_month = True
                is_still_active = False
            elif resign_month < target_period:
                is_still_active = False

        elif status_curr == "Resign" and "Realtime" in selected_dash_period:
            is_still_active = False

        if is_resign_this_month:
            row_mod = row.copy()
            row_mod["Status"] = "Resign"
            resign_rows.append(row_mod)
        elif is_still_active:
            row_mod = row.copy()
            row_mod["Status"] = "Aktif"
            active_rows.append(row_mod)

    df_active_res = pd.DataFrame(active_rows) if active_rows else pd.DataFrame(columns=df.columns)
    df_resign_res = pd.DataFrame(resign_rows) if resign_rows else pd.DataFrame(columns=df.columns)
    
    df_combined = pd.concat([df_active_res, df_resign_res], ignore_index=True) if not df_active_res.empty or not df_resign_res.empty else pd.DataFrame(columns=df.columns)
    return df_active_res, df_resign_res, df_combined
