import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- הגדרות דף ---
st.set_page_config(page_title="הפסאז' - ניהול אירועים", layout="wide")

# --- עיצוב CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3.5em; }
    /* עיצוב שדות קטנים וצפופים יותר */
    .stTextInput, .stNumberInput, .stDateInput { margin-bottom: -10px; }
    </style>
    """, unsafe_allow_html=True)

# --- ניהול זיכרון (Session State) ---
if 'v2_page' not in st.session_state: st.session_state.v2_page = "order"
if 'v2_cart' not in st.session_state: st.session_state.v2_cart = []
if 'v2_qty_key' not in st.session_state: st.session_state.v2_qty_key = 0
if 'v2_last_item' not in st.session_state: st.session_state.v2_last_item = None

# שדות לקוח - ערכים שחייבים להישמר
if 'v2_name' not in st.session_state: st.session_state.v2_name = ""
if 'v2_phone' not in st.session_state: st.session_state.v2_phone = ""
if 'v2_email' not in st.session_state: st.session_state.v2_email = ""
if 'v2_guests' not in st.session_state: st.session_state.v2_guests = None
if 'v2_budget' not in st.session_state: st.session_state.v2_budget = None

def reset_to_new_client():
    st.session_state.v2_name = ""
    st.session_state.v2_phone = ""
    st.session_state.v2_email = ""
    st.session_state.v2_guests = None
    st.session_state.v2_budget = None
    st.session_state.v2_cart = []
    st.rerun()

# --- DB ---
conn = sqlite3.connect('passaz_pro_v2.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY, item TEXT, price REAL)')
c.execute('''CREATE TABLE IF NOT EXISTS orders 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, email TEXT, 
              guests INTEGER, items TEXT, total INTEGER, timestamp TEXT)''')
conn.commit()

# --- 4. כפתורי ניווט בשורה אחת (בראש האפליקציה) ---
nav_1, nav_2, nav_3 = st.columns(3)
if nav_1.button("📝 מסך הזמנה"): st.session_state.v2_page = "order"
if nav_2.button("📋 היסטוריה"): st.session_state.v2_page = "history"
if nav_3.button("⚙️ ניהול תפריט"): st.session_state.v2_page = "menu"

st.divider()

# --- עמוד הזמנה ---
if st.session_state.v2_page == "order":
    
    col_title, col_reset = st.columns([4, 1])
    col_title.subheader("פרטי לקוח ואירוע")
    if col_reset.button("✨ לקוח חדש"): reset_to_new_client()

    # 1. שם וטלפון זה לצד זה
    r1_c1, r1_c2 = st.columns(2)
    st.session_state.v2_name = r1_c1.text_input("שם לקוח / קבוצה", value=st.session_state.v2_name)
    st.session_state.v2_phone = r1_c2.text_input("טלפון", value=st.session_state.v2_phone)

    # אימייל (מתחת לשורה הראשונה)
    st.session_state.v2_email = st.text_input("אימייל", value=st.session_state.v2_email)

    # 2. סועדים ותקציב זה לצד זה (מתחת לאימייל)
    r2_c1, r2_c2 = st.columns(2)
    st.session_state.v2_guests = r2_c1.number_input("מספר סועדים", min_value=1, step=1, value=st.session_state.v2_guests)
    st.session_state.v2_budget = r2_c2.number_input("תקציב יעד (₪)", min_value=1, step=1, value=st.session_state.v2_budget)

    # 3. תאריך ושעה זה לצד זה
    r3_c1, r3_c2 = st.columns(2)
    ev_date = r3_c1.date_input("תאריך האירוע", value=datetime.now())
    ev_time = r3_c2.time_input("שעת האירוע", value=datetime.now())

    st.divider()

    # --- הוספת פריטים (האופציה שחזרה) ---
    df_m = pd.read_sql_query("SELECT * FROM menu", conn)
    if not df_m.empty:
        st.subheader("🛒 הוספת פריטים")
        # פריט וכמות זה לצד זה
        ci, cq, ca = st.columns([3, 1, 1])
        
        m_list = df_m['item'].tolist()
        last_idx = m_list.index(st.session_state.v2_last_item) if st.session_state.v2_last_item in m_list else 0
        sel_item = ci.selectbox("בחר מנה", m_list, index=last_idx)
        
        # איפוס כמות (ריק אחרי הוספה)
        sel_qty = cq.number_input("כמות", min_value=1, step=1, value=None, key=f"q_{st.session_state.v2_qty_key}", placeholder="?")
        
        if ca.button("➕ הוסף"):
            if sel_qty:
                price = df_m[df_m['item'] == sel_item]['price'].values[0]
                st.session_state.v2_cart.append({
                    "מוצר": sel_item, "כמות": int(sel_qty), "מחיר": int(price), "סה''כ": int(sel_qty * price)
                })
                st.session_state.v2_last_item = sel_item
                st.session_state.v2_qty_key += 1 # מאפס את שדה הכמות
                st.rerun()

    # תצוגת הסל
    if st.session_state.v2_cart:
        st.table(pd.DataFrame(st.session_state.v2_cart))
        total = sum(i["סה''כ"] for i in st.session_state.v2_cart)
        st.metric("סה''כ לתשלום", f"{total:,} ₪")
        
        if st.button("💾 שמור הזמנה סופית"):
            items_txt = ", ".join([f"{i['מוצר']} x{i['כמות']}" for i in st.session_state.v2_cart])
            c.execute("INSERT INTO orders (name, phone, email, guests, items, total, timestamp) VALUES (?,?,?,?,?,?,?)",
                      (st.session_state.v2_name, st.session_state.v2_phone, st.session_state.v2_email, 
                       st.session_state.v2_guests, items_txt, total, datetime.now().strftime("%d/%m/%Y %H:%M")))
            conn.commit()
            st.success("ההזמנה נשמרה בהיסטוריה!")

# --- עמוד היסטוריה ---
elif st.session_state.v2_page == "history":
    st.header("📋 היסטוריה")
    df_h = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
    st.dataframe(df_h, use_container_width=True)

# --- עמוד תפריט ---
elif st.session_state.v2_page == "menu":
    st.header("⚙️ ניהול תפריט")
    with st.form("new_dish"):
        n = st.text_input("שם המנה")
        p = st.number_input("מחיר", min_value=1, step=1, value=None)
        if st.form_submit_button("הוסף לתפריט"):
            if n and p:
                c.execute("INSERT INTO menu (item, price) VALUES (?,?)", (n, int(p)))
                conn.commit()
                st.rerun()
    st.table(pd.read_sql_query("SELECT item, price FROM menu", conn))
