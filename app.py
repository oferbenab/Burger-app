import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- הגדרות דף ---
st.set_page_config(page_title="הפסאז' - ניהול חכם", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; justify-content: center; }
    .stTabs [data-baseweb="tab"] { background-color: #f0f2f6; border-radius: 10px 10px 0 0; padding: 10px 20px; font-weight: bold; }
    [data-testid="column"] { min-width: 45% !important; flex: 1 1 45% !important; }
    input { font-size: 16px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- ניהול זיכרון (Session State) ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'form_reset' not in st.session_state: st.session_state.form_reset = 0
if 'q_idx' not in st.session_state: st.session_state.q_idx = 0

# שימור שדות לקוח
for k, v in {'nm': "", 'ph': "", 'em': "", 'gs': 1, 'bd': 0}.items():
    if k not in st.session_state: st.session_state[k] = v

# --- חיבור ל-DB ---
conn = sqlite3.connect('passaz_pro_v6.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, price REAL)')
c.execute('CREATE TABLE IF NOT EXISTS orders (name TEXT, details TEXT, total REAL, date TEXT)')
conn.commit()

tab1, tab2, tab3 = st.tabs(["📝 הזמנה חדשה", "📋 היסטוריה", "⚙️ ניהול תפריט"])

# --- לשונית 1: הזמנה ---
with tab1:
    with st.expander("👤 פרטי לקוח ואירוע", expanded=True):
        c1, c2 = st.columns(2)
        st.session_state.nm = c1.text_input("שם", value=st.session_state.nm)
        st.session_state.ph = c2.text_input("טלפון", value=st.session_state.ph)
        st.session_state.em = st.text_input("אימייל", value=st.session_state.em)
        
        c3, c4 = st.columns(2)
        st.session_state.gs = c3.number_input("סועדים", min_value=1, value=st.session_state.gs)
        st.session_state.bd = c4.number_input("תקציב (₪)", min_value=0, value=st.session_state.bd)
        
        st.write("זמן האירוע:")
        c5, c6, c7 = st.columns([2, 1, 1])
        ev_date = c5.date_input("תאריך", label_visibility="collapsed")
        h = c6.selectbox("שעה", [f"{i:02d}" for i in range(24)], index=20)
        m = c7.selectbox("דקות", [f"{i:02d}" for i in range(0,60,5)], index=0)

    st.divider()
    st.subheader("🛒 סל מנות")
    m_df = pd.read_sql_query("SELECT * FROM menu", conn)
    
    if not m_df.empty:
        col_it, col_qty = st.columns([2, 1])
        sel_item = col_it.selectbox("בחר מנה", m_df['item'].tolist())
        sel_qty = col_qty.number_input("כמות", min_value=1, value=None, key=f"q_{st.session_state.q_idx}", placeholder="?")
        
        if st.button("➕ הוסף לסל"):
            if sel_qty:
                price = m_df[m_df['item'] == sel_item]['price'].values[0]
                st.session_state.cart.append({"מנה": sel_item, "כמות": int(sel_qty), "מחיר": int(price), "סה''כ": int(sel_qty * price)})
                st.session_state.q_idx += 1
                st.rerun()
    
    if st.session_state.cart:
        st.table(pd.DataFrame(st.session_state.cart))
        subtotal = sum(i["סה''כ"] for i in st.session_state.cart)
        tip_pct = st.radio("טיפ", [0, 10, 15, 20], format_func=lambda x: f"{x}%", horizontal=True)
        total_all = subtotal + int(subtotal * (tip_pct/100))
        
        m1, m2 = st.columns(2)
        m1.metric("סה''כ סופי", f"{total_all:,} ₪")
        if st.session_state.bd > 0:
            diff = st.session_state.bd - total_all
            m2.metric("יתרה/חריגה", f"{diff:,} ₪", delta=diff)
        
        if st.button("💾 שמור הזמנה"):
            details = ", ".join([f"{i['מנה']} x{i['כמות']}" for i in st.session_state.cart])
            c.execute("INSERT INTO orders VALUES (?,?,?,?)", (st.session_state.nm, details, total_all, datetime.now().strftime("%d/%m/%Y %H:%M")))
            conn.commit()
            st.success("הזמנה נשמרה!")

# --- לשונית 2: היסטוריה ---
with tab2:
    st.dataframe(pd.read_sql_query("SELECT * FROM orders ORDER BY rowid DESC", conn), use_container_width=True)

# --- לשונית 3: ניהול תפריט ---
with tab3:
    st.subheader("➕ הוספת מנה חדשה")
    # טופס הוספה עם איפוס
    with st.form("add_form", clear_on_submit=True):
        n_dish = st.text_input("שם המנה", key=f"n_{st.session_state.form_reset}")
        p_dish = st.number_input("מחיר (₪)", min_value=0.0, step=1.0, value=None, placeholder="הכנס מחיר...", key=f"p_{st.session_state.form_reset}")
        if st.form_submit_button("הוסף לתפריט"):
            if n_dish and p_dish:
                c.execute("INSERT INTO menu (item, price) VALUES (?,?)", (n_dish, p_dish))
                conn.commit()
                st.session_state.form_reset += 1
                st.rerun()

    st.divider()
    st.subheader("📝 עריכת תפריט קיים")
    menu_current = pd.read_sql_query("SELECT * FROM menu", conn)
    
    for idx, row in menu_current.iterrows():
        col_n, col_p, col_upd, col_del = st.columns([2, 1, 1, 1])
        new_name = col_n.text_input("שם", value=row['item'], key=f"edit_n_{row['id']}")
        new_price = col_p.number_input("מחיר", value=float(row['price']), key=f"edit_p_{row['id']}")
        
        if col_upd.button("💾", key=f"upd_{row['id']}", help="עדכן"):
            c.execute("UPDATE menu SET item=?, price=? WHERE id=?", (new_name, new_price, row['id']))
            conn.commit()
            st.rerun()
            
        if col_del.button("🗑️", key=f"del_{row['id']}", help="מחק"):
            c.execute("DELETE FROM menu WHERE id=?", (row['id'],))
            conn.commit()
            st.rerun()
