import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- הגדרות דף ועיצוב ---
st.set_page_config(page_title="הפסאז' - ניהול אירועים", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3em; }
    /* צמצום מרווחים בין אלמנטים */
    .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

# --- ניהול זיכרון (Session State) ---
if 'active_page' not in st.session_state: st.session_state.active_page = "order"
if 'cart' not in st.session_state: st.session_state.cart = []

# --- 4. כפתורי ניווט בראש האפליקציה (אחד לצד השני) ---
nav_col1, nav_col2, nav_col3 = st.columns(3)
if nav_col1.button("📝 מסך הזמנה"): st.session_state.active_page = "order"
if nav_col2.button("📋 היסטוריה"): st.session_state.active_page = "history"
if nav_col3.button("⚙️ ניהול תפריט"): st.session_state.active_page = "menu"

st.divider()

# --- עמוד הזמנה ---
if st.session_state.active_page == "order":
    
    # 1. שדה לקוח וטלפון זה לצד זה
    col_name, col_phone = st.columns(2)
    with col_name:
        client_name = st.text_input("שם לקוח / קבוצה", placeholder="הכנס שם...")
    with col_phone:
        client_phone = st.text_input("טלפון", placeholder="05x-xxxxxxx")

    # שדה אימייל (מעל הסועדים והתקציב)
    client_email = st.text_input("אימייל", placeholder="example@mail.com")

    # 2. שדה סועדים ושדה תקציב זה לצד זה (מתחת לאימייל)
    col_guests, col_budget = st.columns(2)
    with col_guests:
        guests = st.number_input("מספר סועדים", min_value=1, step=1, value=None, placeholder="כמות")
    with col_budget:
        budget = st.number_input("תקציב יעד (₪)", min_value=1, step=1, value=None, placeholder="תקציב")

    # 3. שדה תאריך ושדה שעה זה לצד זה (מתחת לסועדים ותקציב)
    col_date, col_time = st.columns(2)
    with col_date:
        event_date = st.date_input("תאריך האירוע")
    with col_time:
        event_time = st.time_input("שעת האירוע")

    st.divider()
    st.subheader("🛒 הוספת פריטים להזמנה")
    # כאן יבוא המשך הלוגיקה של בחירת המנות והסל...

# --- עמוד היסטוריה ---
elif st.session_state.active_page == "history":
    st.header("📋 היסטוריית הזמנות")
    st.info("כאן תוצג רשימת ההזמנות שנשמרו.")

# --- עמוד ניהול תפריט ---
elif st.session_state.active_page == "menu":
    st.header("⚙️ ניהול תפריט")
    st.info("כאן תוכל להוסיף ולערוך מנות.")
