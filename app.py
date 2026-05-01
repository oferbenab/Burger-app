import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- הגדרות דף ---
st.set_page_config(page_title="הפסאז'", layout="wide")

# עיצוב מותאם לאייפון (טקסט גדול יותר וכפתורים נוחים)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; height: 3.5em; margin-bottom: 5px; }
    input { font-size: 16px !important; } /* מונע זום אוטומטי באייפון */
    </style>
    """, unsafe_allow_html=True)

# --- ניהול זיכרון (Session State) ---
if 'pg' not in st.session_state: st.session_state.pg = "order"
if 'cart_items' not in st.session_state: st.session_state.cart_items = []
if 'q_reset' not in st.session_state: st.session_state.q_reset = 0

# שימור נתוני לקוח
for key in ['nm', 'ph', 'em', 'gst', 'bdg']:
    if key not in st.session_state:
        st.session_state[key] = None if key in ['gst', 'bdg'] else ""

# --- ניווט (כפתורים בשורה אחת) ---
# באייפון הם עשויים להיות אחד מעל השני אם המסך צר מאוד
n1, n2, n3 = st.columns(3)
if n1.button("📝 הזמנה"): st.session_state.pg = "order"
if n2.button("📋 היסטוריה"): st.session_state.pg = "history"
if n3.button("⚙️ תפריט"): st.session_state.pg = "menu"
st.divider()

# --- חיבור ל-DB ---
conn = sqlite3.connect('passaz_mobile.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS menu (item TEXT, price REAL)')
c.execute('CREATE TABLE IF NOT EXISTS orders (name TEXT, details TEXT, total REAL, time TEXT)')
conn.commit()

# --- דף הזמנה ---
if st.session_state.pg == "order":
    st.subheader("פרטי אירוע")
    
    # שדות לצד זה (באייפון יוצגו אחד מתחת לשני, אך עם הגדרות נכונות)
    r1_1, r1_2 = st.columns(2)
    st.session_state.nm = r1_1.text_input("שם לקוח", value=st.session_state.nm)
    st.session_state.ph = r1_2.text_input("טלפון", value=st.session_state.ph)
    
    st.session_state.em = st.text_input("אימייל", value=st.session_state.em)
    
    r2_1, r2_2 = st.columns(2)
    st.session_state.gst = r2_1.number_input("סועדים", min_value=1, step=1, value=st.session_state.gst)
    st.session_state.bdg = r2_2.number_input("תקציב (₪)", min_value=0, step=10, value=st.session_state.bdg)
    
    r3_1, r3_2 = st.columns(2)
    ev_d = r3_1.date_input("תאריך", value=datetime.now())
    ev_t = r3_2.time_input("שעה", value=datetime.now())

    st.divider()
    
    # --- הוספת מנות ---
    st.subheader("🛒 הוספת מנות")
    m_df = pd.read_sql_query("SELECT * FROM menu", conn)
    if not m_df.empty:
        c_i, c_q = st.columns([2, 1])
        sel_i = c_i.selectbox("מנה", m_df['item'].tolist())
        sel_q = c_q.number_input("כמות", min_value=1, step=1, value=None, key=f"q_{st.session_state.q_reset}")
        
        if st.button("➕ הוסף לסל"):
            if sel_q:
                pr = m_df[m_df['item'] == sel_i]['price'].values[0]
                st.session_state.cart_items.append({"מנה": sel_i, "כמות": sel_q, "סה''כ": sel_q * pr})
                st.session_state.q_reset += 1
                st.rerun()
    
    # תצוגת הסל ושמירה
    if st.session_state.cart_items:
        st.write("---")
        st.table(pd.DataFrame(st.session_state.cart_items))
        total = sum(i["סה''כ"] for i in st.session_state.cart_items)
        st.write(f"### סה''כ: {total} ₪")
        
        if st.button("💾 שמור הזמנה"):
            details = ", ".join([f"{i['מנה']} x{i['כמות']}" for i in st.session_state.cart_items])
            c.execute("INSERT INTO orders VALUES (?,?,?,?)", (st.session_state.nm, details, total, datetime.now().strftime("%H:%M")))
            conn.commit()
            st.success("נשמר!")
            st.session_state.cart_items = []
            st.rerun()

# --- דף תפריט ---
elif st.session_state.pg == "menu":
    st.subheader("ניהול תפריט")
    with st.form("add"):
        n = st.text_input("שם מנה")
        p = st.number_input("מחיר")
        if st.form_submit_button("הוסף"):
            c.execute("INSERT INTO menu VALUES (?,?)", (n, p))
            conn.commit()
            st.rerun()
    st.table(pd.read_sql_query("SELECT * FROM menu", conn))

# --- דף היסטוריה ---
elif st.session_state.pg == "history":
    st.subheader("היסטוריה")
    st.dataframe(pd.read_sql_query("SELECT * FROM orders", conn))
