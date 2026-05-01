import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, time
import json

# --- הגדרות דף ---
st.set_page_config(page_title="הפסאז' Pro", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; justify-content: center; }
    input { font-size: 16px !important; }
    /* כפתורי היסטוריה קטנים וצמודים */
    .stButton>button { padding: 2px 10px; font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

# --- חיבור ל-DB ---
conn = sqlite3.connect('passaz_pro_v14.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, price INTEGER)')
c.execute('''CREATE TABLE IF NOT EXISTS orders 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, date TEXT, total INTEGER, 
              details_text TEXT, raw_cart TEXT, customer_data TEXT)''')
conn.commit()

# --- פונקציות ניהול ---
def reset_order():
    st.session_state.cart = []
    st.session_state.q_idx += 100
    for k in ['nm', 'ph', 'em', 'gs', 'ppg', 'bd', 'notes']:
        st.session_state[k] = None if k in ['gs', 'ppg', 'bd'] else ""

def load_order(raw_cart, cust_data):
    st.session_state.cart = json.loads(raw_cart)
    data = json.loads(cust_data)
    for k, v in data.items():
        st.session_state[k] = v
    st.toast("הנתונים נטענו ללשונית הזמנה!")

# --- Session State אתחול ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'q_idx' not in st.session_state: st.session_state.q_idx = 0
cust_keys = ['nm', 'ph', 'em', 'gs', 'ppg', 'bd', 'notes']
for k in cust_keys:
    if k not in st.session_state:
        st.session_state[k] = None if k in ['gs', 'ppg', 'bd'] else ""

# --- ממשק ראשי ---
st.button("🆕 הזמנה חדשה", on_click=reset_order)

tab1, tab2, tab3 = st.tabs(["📝 הזמנה", "📋 היסטוריה", "⚙️ תפריט"])

# --- לשונית 1: הזמנה (זהה לגרסה קודמת) ---
with tab1:
    with st.expander("👤 פרטי לקוח", expanded=True):
        c1, c2 = st.columns(2)
        st.session_state.nm = c1.text_input("שם", value=st.session_state.nm)
        st.session_state.ph = c2.text_input("טלפון", value=st.session_state.ph)
        c3, c4, c5 = st.columns(3)
        st.session_state.gs = c3.number_input("סועדים", min_value=1, value=st.session_state.gs)
        st.session_state.ppg = c4.number_input("לסועד", min_value=0, value=st.session_state.ppg)
        st.session_state.bd = c5.number_input("תקציב", min_value=0, value=st.session_state.bd)
        st.session_state.notes = st.text_area("הערות", value=st.session_state.notes)

    m_df = pd.read_sql_query("SELECT item, price FROM menu", conn)
    if not m_df.empty:
        ci, cq, ca = st.columns([3, 1, 1])
        s_it = ci.selectbox("מנה", m_df['item'].tolist())
        s_qy = cq.number_input("כמות", min_value=1, value=None, key=f"q_{st.session_state.q_idx}")
        if ca.button("➕"):
            if s_qy:
                pr = int(m_df[m_df['item'] == s_it]['price'].values[0])
                st.session_state.cart.append({"מנה": s_it, "כמות": int(s_qy), "מחיר": pr, "סה''כ": int(s_qy * pr)})
                st.session_state.q_idx += 1
                st.rerun()
    
    if st.session_state.cart:
        st.table(pd.DataFrame(st.session_state.cart))
        sub = sum(i["סה''כ"] for i in st.session_state.cart) + (int(st.session_state.gs or 0) * int(st.session_state.ppg or 0))
        total = int(sub * 1.1) # ברירת מחדל 10% טיפ לחישוב מהיר
        st.subheader(f"סה''כ: {total:,} ₪")
        if st.button("💾 שמור סופית"):
            raw_c = json.dumps(st.session_state.cart)
            raw_cust = json.dumps({k: st.session_state[k] for k in cust_keys})
            c.execute("INSERT INTO orders (name, date, total, details_text, raw_cart, customer_data) VALUES (?,?,?,?,?,?)", 
                     (st.session_state.nm, datetime.now().strftime("%d/%m/%y %H:%M"), total, "", raw_c, raw_cust))
            conn.commit()
            st.success("נשמר!")

# --- לשונית 2: היסטוריה (השדרוג המרכזי) ---
with tab2:
    search_term = st.text_input("🔍 חפש שם לקוח...", placeholder="הקלד שם לסינון...")
    
    query = "SELECT * FROM orders ORDER BY id DESC"
    hist_df = pd.read_sql_query(query, conn)
    
    if not hist_df.empty:
        # סינון לפי חיפוש
        if search_term:
            hist_df = hist_df[hist_df['name'].str.contains(search_term, na=False, case=False)]
        
        st.write("---")
        # כותרות לטבלה הויזואלית
        h_c1, h_c2, h_c3, h_c4 = st.columns([3, 2, 2, 2])
        h_c1.caption("לקוח")
        h_c2.caption("תאריך | סכום")
        h_c3.caption("טעינה")
        h_c4.caption("מחיקה")

        for idx, row in hist_df.iterrows():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            
            col1.write(f"**{row['name']}**")
            col2.write(f"{row['date']}\n\n**{row['total']:,} ₪**")
            
            if col3.button("🔄", key=f"ld_{row['id']}"):
                load_order(row['raw_cart'], row['customer_data'])
                st.rerun()
                
            if col4.button("🗑️", key=f"del_{row['id']}"):
                c.execute("DELETE FROM orders WHERE id=?", (row['id'],))
                conn.commit()
                st.rerun()
            st.write("---")
    else:
        st.info("אין נתונים להצגה")

# --- לשונית 3: תפריט ---
with tab3:
    df_m = pd.read_sql_query("SELECT id, item, price FROM menu", conn)
    edited = st.data_editor(df_m, column_config={"id": None}, num_rows="dynamic", use_container_width=True, hide_index=True)
    if st.button("💾 שמור תפריט"):
        c.execute("DELETE FROM menu")
        for _, r in edited.iterrows():
            if r['item']: c.execute("INSERT INTO menu (item, price) VALUES (?,?)", (r['item'], int(r['price'])))
        conn.commit()
        st.success("עודכן!")
