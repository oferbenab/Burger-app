import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, time
import json

# --- הגדרות דף ---
st.set_page_config(page_title="הפסאז' - ניהול מתקדם", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; justify-content: center; }
    input { font-size: 16px !important; }
    .stButton>button[kind="secondary"] { width: 100%; border: 2px solid #ff4b4b; color: #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

# --- חיבור ל-DB ---
conn = sqlite3.connect('passaz_pro_v13.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, price INTEGER)')
# שדרוג טבלת הזמנות לשמירת נתונים מורכבים ב-JSON לטעינה חוזרת
c.execute('''CREATE TABLE IF NOT EXISTS orders 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, date TEXT, total INTEGER, 
              details_text TEXT, raw_cart TEXT, customer_data TEXT)''')
conn.commit()

# --- ניהול זיכרון (Session State) ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'q_idx' not in st.session_state: st.session_state.q_idx = 0

cust_keys = ['nm', 'ph', 'em', 'gs', 'ppg', 'bd', 'notes']
for k in cust_keys:
    if k not in st.session_state:
        st.session_state[k] = None if k in ['gs', 'ppg', 'bd'] else ""

# --- פונקציות עזר ---
def reset_order():
    st.session_state.cart = []
    st.session_state.q_idx += 100
    for k in ['nm', 'ph', 'em', 'gs', 'ppg', 'bd', 'notes']:
        st.session_state[k] = None if k in ['gs', 'ppg', 'bd'] else ""

def load_order(raw_cart, cust_data):
    try:
        st.session_state.cart = json.loads(raw_cart)
        data = json.loads(cust_data)
        for k, v in data.items():
            st.session_state[k] = v
        st.toast("ההזמנה נטענה! ניתן לערוך בלשונית הזמנה")
    except:
        st.error("שגיאה בטעינת הנתונים")

# --- ממשק משתמש ---
st.button("🆕 הזמנה חדשה (איפוס שדות)", on_click=reset_order, type="secondary")

tab1, tab2, tab3 = st.tabs(["📝 הזמנה", "📋 היסטוריה", "⚙️ תפריט"])

# --- לשונית 1: הזמנה ---
with tab1:
    with st.expander("👤 פרטי אירוע", expanded=True):
        c1, c2 = st.columns(2)
        st.session_state.nm = c1.text_input("שם לקוח", value=st.session_state.nm)
        st.session_state.ph = c2.text_input("טלפון", value=st.session_state.ph)
        st.session_state.em = st.text_input("אימייל", value=st.session_state.em)
        
        c3, c4, c5 = st.columns(3)
        st.session_state.gs = c3.number_input("סועדים", min_value=1, step=1, value=st.session_state.gs, placeholder="הכנס...")
        st.session_state.ppg = c4.number_input("לסועד", min_value=0, step=1, value=st.session_state.ppg, placeholder="₪")
        st.session_state.bd = c5.number_input("תקציב", min_value=0, step=1, value=st.session_state.bd, placeholder="₪")
        
        st.write("📅 מועד:")
        col_d, col_t = st.columns(2)
        ev_date = col_d.date_input("תאריך")
        ev_time = col_t.time_input("שעה", value=time(20, 0))
        st.session_state.notes = st.text_area("הערות", value=st.session_state.notes)

    st.divider()
    
    m_df = pd.read_sql_query("SELECT item, price FROM menu", conn)
    if not m_df.empty:
        c_it, c_qy, c_ad = st.columns([3, 1, 1])
        sel_item = c_it.selectbox("מנה", m_df['item'].tolist(), label_visibility="collapsed")
        sel_qty = c_qy.number_input("כמות", min_value=1, step=1, value=None, key=f"q_{st.session_state.q_idx}", placeholder="?")
        if c_ad.button("➕"):
            if sel_qty:
                price = int(m_df[m_df['item'] == sel_item]['price'].values[0])
                st.session_state.cart.append({"מנה": sel_item, "כמות": int(sel_qty), "מחיר": price, "סה''כ": int(sel_qty * price)})
                st.session_state.q_idx += 1
                st.rerun()
    
    if st.session_state.cart:
        st.table(pd.DataFrame(st.session_state.cart))
        gs_v = st.session_state.gs if st.session_state.gs else 0
        ppg_v = st.session_state.ppg if st.session_state.ppg else 0
        subtotal = sum(i["סה''כ"] for i in st.session_state.cart) + (gs_v * ppg_v)
        tip_pct = st.radio("טיפ", [0, 10, 15, 20], format_func=lambda x: f"{x}%", horizontal=True)
        total_all = int(subtotal * (1 + tip_pct/100))
        
        st.metric("סה''כ סופי", f"{total_all:,} ₪")
        
        if st.button("💾 שמור הזמנה סופית", type="primary"):
            summary = f"סועדים: {gs_v} | " + ", ".join([f"{i['מנה']} x{i['כמות']}" for i in st.session_state.cart])
            f_date = f"{ev_date.strftime('%d/%m/%y')} {ev_time.strftime('%H:%M')}"
            
            # שמירת נתונים גולמיים לטעינה עתידית
            raw_cart = json.dumps(st.session_state.cart)
            cust_data = json.dumps({k: st.session_state[k] for k in cust_keys})
            
            c.execute("INSERT INTO orders (name, date, total, details_text, raw_cart, customer_data) VALUES (?,?,?,?,?,?)", 
                     (st.session_state.nm, f_date, total_all, summary, raw_cart, cust_data))
            conn.commit()
            st.success("נשמר!")

# --- לשונית 2: היסטוריה ---
with tab2:
    st.subheader("📋 היסטוריית הזמנות")
    hist_df = pd.read_sql_query("SELECT id, name as 'לקוח', date as 'תאריך', total as 'סכום', raw_cart, customer_data FROM orders ORDER BY id DESC", conn)
    
    if hist_df.empty:
        st.info("אין הזמנות שמורות")
    else:
        for idx, row in hist_df.iterrows():
            with st.container():
                # שורה אחת לכל רשומה בהיסטוריה
                c_data, c_load, c_del = st.columns([4, 1, 1])
                c_data.write(f"**{row['לקוח']}** | {row['תאריך']} | **{row['סכום']:,} ₪**")
                
                # כפתור טעינה
                if c_load.button("🔄 טען", key=f"ld_{row['id']}", help="טען להזמנה חדשה"):
                    load_order(row['raw_cart'], row['customer_data'])
                    st.rerun()
                
                # כפתור מחיקה
                if c_del.button("🗑️", key=f"del_{row['id']}", help="מחק מהיסטוריה"):
                    c.execute("DELETE FROM orders WHERE id=?", (row['id'],))
                    conn.commit()
                    st.rerun()
                st.divider()

# --- לשונית 3: תפריט ---
with tab3:
    st.subheader("⚙️ עריכת תפריט")
    df_m = pd.read_sql_query("SELECT id, item as 'שם המוצר', price as 'מחיר' FROM menu", conn)
    df_m['מחיר'] = df_m['מחיר'].fillna(0).astype(int)
    edited = st.data_editor(df_m, column_config={"id": None}, num_rows="dynamic", use_container_width=True, hide_index=True, key="menu_v13")
    
    if st.button("💾 שמור תפריט"):
        c.execute("DELETE FROM menu")
        for _, r in edited.iterrows():
            if r['שם המוצר']:
                c.execute("INSERT INTO menu (item, price) VALUES (?,?)", (r['שם המוצר'], int(r['מחיר'])))
        conn.commit()
        st.success("עודכן!")
