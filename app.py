import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, time

# --- הגדרות דף ---
st.set_page_config(page_title="הפסאז' - ממשק נקי", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; justify-content: center; }
    input { font-size: 16px !important; }
    /* מניעת הופעת חיצים בשדות מספרים למראה נקי */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    </style>
    """, unsafe_allow_html=True)

# --- חיבור ל-DB ---
conn = sqlite3.connect('passaz_final_v11.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, price INTEGER)')
c.execute('CREATE TABLE IF NOT EXISTS orders (name TEXT, details TEXT, total INTEGER, date TEXT, notes TEXT)')
conn.commit()

# --- ניהול זיכרון (Session State) ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'q_idx' not in st.session_state: st.session_state.q_idx = 0

# אתחול שדות לקוח כריקים (None)
cust_keys = ['nm', 'ph', 'em', 'gs', 'ppg', 'bd', 'notes']
for k in cust_keys:
    if k not in st.session_state:
        st.session_state[k] = None if k in ['gs', 'ppg', 'bd'] else ""

tab1, tab2, tab3 = st.tabs(["📝 הזמנה", "📋 היסטוריה", "⚙️ תפריט"])

# --- לשונית 1: הזמנה ---
with tab1:
    with st.expander("👤 פרטי אירוע", expanded=True):
        c1, c2 = st.columns(2)
        st.session_state.nm = c1.text_input("שם לקוח", value=st.session_state.nm if st.session_state.nm else "")
        st.session_state.ph = c2.text_input("טלפון", value=st.session_state.ph if st.session_state.ph else "")
        st.session_state.em = st.text_input("אימייל", value=st.session_state.em if st.session_state.em else "")
        
        c3, c4, c5 = st.columns(3)
        # שדות מספרים ללא ערך התחלתי (value=None) ובפורמט שלם
        st.session_state.gs = c3.number_input("סועדים", min_value=1, step=1, value=st.session_state.gs, placeholder="הכנס...")
        st.session_state.ppg = c4.number_input("לסועד", min_value=0, step=1, value=st.session_state.ppg, placeholder="₪")
        st.session_state.bd = c5.number_input("תקציב", min_value=0, step=1, value=st.session_state.bd, placeholder="₪")
        
        st.write("📅 מועד האירוע:")
        col_d, col_t = st.columns(2)
        ev_date = col_d.date_input("תאריך", label_visibility="collapsed")
        ev_time = col_t.time_input("שעה", value=time(20, 0), label_visibility="collapsed")
        
        st.session_state.notes = st.text_area("הערות מיוחדות", value=st.session_state.notes if st.session_state.notes else "")

    st.divider()
    
    # סל מנות
    m_df = pd.read_sql_query("SELECT item, price FROM menu", conn)
    if not m_df.empty:
        c_it, c_qy, c_ad = st.columns([3, 1, 1])
        sel_item = c_it.selectbox("בחר מנה", m_df['item'].tolist(), label_visibility="collapsed")
        sel_qty = c_qy.number_input("כמות", min_value=1, step=1, value=None, key=f"q_{st.session_state.q_idx}", placeholder="?")
        if c_ad.button("➕"):
            if sel_qty:
                price = int(m_df[m_df['item'] == sel_item]['price'].values[0])
                st.session_state.cart.append({"מנה": sel_item, "כמות": int(sel_qty), "מחיר": price, "סה''כ": int(sel_qty * price)})
                st.session_state.q_idx += 1
                st.rerun()
    
    if st.session_state.cart:
        st.table(pd.DataFrame(st.session_state.cart))
        
        # חישובים בשלמים
        gs_val = st.session_state.gs if st.session_state.gs else 0
        ppg_val = st.session_state.ppg if st.session_state.ppg else 0
        bd_val = st.session_state.bd if st.session_state.bd else 0
        
        subtotal = sum(i["סה''כ"] for i in st.session_state.cart) + (gs_val * ppg_val)
        tip_pct = st.radio("טיפ", [0, 10, 15, 20], format_func=lambda x: f"{x}%", horizontal=True)
        total_all = int(subtotal * (1 + tip_pct/100))
        
        m1, m2 = st.columns(2)
        m1.metric("סה''כ", f"{total_all:,} ₪")
        if bd_val > 0:
            diff = bd_val - total_all
            m2.metric("תקציב", f"{bd_val:,} ₪", delta=int(diff))
        
        if st.button("💾 שמור הזמנה סופית", type="primary"):
            summary = f"סועדים: {gs_val} | " + ", ".join([f"{i['מנה']} x{i['כמות']}" for i in st.session_state.cart])
            full_date = f"{ev_date.strftime('%d/%m/%y')} {ev_time.strftime('%H:%M')}"
            c.execute("INSERT INTO orders (name, details, total, date, notes) VALUES (?,?,?,?,?)", 
                     (st.session_state.nm, summary, total_all, full_date, st.session_state.notes))
            conn.commit()
            st.success("נשמר בהצלחה!")

# --- לשונית 2: היסטוריה ---
with tab2:
    st.subheader("היסטוריית הזמנות")
    st.dataframe(pd.read_sql_query("SELECT * FROM orders ORDER BY rowid DESC", conn), use_container_width=True)

# --- לשונית 3: ניהול תפריט ---
with tab3:
    st.subheader("⚙️ עריכת תפריט")
    df_menu = pd.read_sql_query("SELECT id, item as 'שם המוצר', price as 'מחיר' FROM menu", conn)
    # המרת מחירים לשלמים בטבלה
    df_menu['מחיר'] = df_menu['מחיר'].fillna(0).astype(int)
    
    edited_df = st.data_editor(
        df_menu, 
        column_config={
            "id": None, 
            "מחיר": st.column_config.NumberColumn("מחיר (₪)", format="%d", step=1)
        },
        num_rows="dynamic", 
        use_container_width=True, 
        hide_index=True, 
        key="menu_v11"
    )
    
    if st.button("💾 שמור שינויים בתפריט"):
        c.execute("DELETE FROM menu")
        for _, row in edited_df.iterrows():
            if row['שם המוצר']:
                # וידוא שמירה כמספר שלם
                price_save = int(row['מחיר']) if pd.notnull(row['מחיר']) else 0
                c.execute("INSERT INTO menu (item, price) VALUES (?,?)", (row['שם המוצר'], price_save))
        conn.commit()
        st.success("התפריט עודכן!")
        st.rerun()
