import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, time

# --- הגדרות דף ---
st.set_page_config(page_title="הפסאז' - Mobile Pro", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; justify-content: center; }
    input { font-size: 16px !important; }
    /* עיצוב רכיב הזמן שייראה טוב באייפון */
    [data-testid="stTimeInput"] { width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- חיבור ל-DB ---
conn = sqlite3.connect('passaz_final_v9.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, price REAL)')
c.execute('CREATE TABLE IF NOT EXISTS orders (name TEXT, details TEXT, total REAL, date TEXT, notes TEXT)')
conn.commit()

# --- ניהול זיכרון ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'q_idx' not in st.session_state: st.session_state.q_idx = 0

# אתחול שדות
cust_fields = {'nm': "", 'ph': "", 'em': "", 'gs': 1, 'ppg': 0.0, 'bd': 0.0, 'notes': ""}
for k, v in cust_fields.items():
    if k not in st.session_state: st.session_state[k] = v

tab1, tab2, tab3 = st.tabs(["📝 הזמנה", "📋 היסטוריה", "⚙️ תפריט"])

# --- לשונית 1: הזמנה ---
with tab1:
    with st.expander("👤 פרטי אירוע", expanded=True):
        c1, c2 = st.columns(2)
        st.session_state.nm = c1.text_input("שם לקוח", value=st.session_state.nm)
        st.session_state.ph = c2.text_input("טלפון", value=st.session_state.ph)
        st.session_state.em = st.text_input("אימייל", value=st.session_state.em)
        
        c3, c4, c5 = st.columns(3)
        st.session_state.gs = c3.number_input("סועדים", min_value=1, value=st.session_state.gs)
        st.session_state.ppg = c4.number_input("לסועד", min_value=0.0, value=st.session_state.ppg)
        st.session_state.bd = c5.number_input("תקציב", min_value=0.0, value=st.session_state.bd)
        
        # --- השדרוג: בורר תאריך וזמן מודרני ---
        st.write("📅 מועד האירוע:")
        col_d, col_t = st.columns(2)
        ev_date = col_d.date_input("תאריך", label_visibility="collapsed")
        # st.time_input פותח באייפון את בורר השעה המובנה (הגלגל)
        ev_time = col_t.time_input("שעה", value=time(20, 0), label_visibility="collapsed")
        
        st.session_state.notes = st.text_area("הערות מיוחדות (אלרגיות, סידור הושבה וכו')", value=st.session_state.notes)

    st.divider()
    
    # ניהול סל
    m_df = pd.read_sql_query("SELECT item, price FROM menu", conn)
    if not m_df.empty:
        c_it, c_qy, c_ad = st.columns([3, 1, 1])
        sel_item = c_it.selectbox("מנה", m_df['item'].tolist(), label_visibility="collapsed")
        sel_qty = c_qy.number_input("כמות", min_value=1, value=None, key=f"q_{st.session_state.q_idx}", placeholder="?")
        if c_ad.button("➕"):
            if sel_qty:
                price = m_df[m_df['item'] == sel_item]['price'].values[0]
                st.session_state.cart.append({"מנה": sel_item, "כמות": int(sel_qty), "מחיר": int(price), "סה''כ": int(sel_qty * price)})
                st.session_state.q_idx += 1
                st.rerun()
    
    if st.session_state.cart:
        st.table(pd.DataFrame(st.session_state.cart))
        subtotal = sum(i["סה''כ"] for i in st.session_state.cart) + (st.session_state.gs * st.session_state.ppg)
        tip_pct = st.radio("טיפ", [0, 10, 15, 20], format_func=lambda x: f"{x}%", horizontal=True)
        total_all = int(subtotal * (1 + tip_pct/100))
        
        m1, m2 = st.columns(2)
        m1.metric("סה''כ", f"{total_all:,} ₪")
        m2.metric("תקציב", f"{st.session_state.bd:,} ₪", delta=st.session_state.bd - total_all)
        
        if st.button("💾 שמור הזמנה סופית", type="primary"):
            summary = f"סועדים: {st.session_state.gs} | " + ", ".join([f"{i['מנה']} x{i['כמות']}" for i in st.session_state.cart])
            full_date = f"{ev_date.strftime('%d/%m/%y')} {ev_time.strftime('%H:%M')}"
            c.execute("INSERT INTO orders VALUES (?,?,?,?,?)", 
                     (st.session_state.nm, summary, total_all, full_date, st.session_state.notes))
            conn.commit()
            st.success(f"הזמנה ל-{st.session_state.nm} נשמרה!")

# --- לשונית 2: היסטוריה ---
with tab2:
    st.subheader("היסטוריית הזמנות")
    st.dataframe(pd.read_sql_query("SELECT * FROM orders ORDER BY rowid DESC", conn), use_container_width=True)

# --- לשונית 3: ניהול תפריט ---
with tab3:
    st.subheader("⚙️ עריכת תפריט")
    df_menu = pd.read_sql_query("SELECT id, item as 'שם המוצר', price as 'מחיר' FROM menu", conn)
    edited_df = st.data_editor(df_menu, column_config={"id": None, "מחיר": st.column_config.NumberColumn("מחיר (₪)", format="%d ₪")},
                               num_rows="dynamic", use_container_width=True, hide_index=True, key="menu_ed_v9")
    
    if st.button("💾 שמור שינויים בתפריט"):
        c.execute("DELETE FROM menu")
        for _, row in edited_df.iterrows():
            if row['שם המוצר']:
                c.execute("INSERT INTO menu (item, price) VALUES (?,?)", (row['שם המוצר'], row['מחיר']))
        conn.commit()
        st.success("עודכן!")
        st.rerun()
