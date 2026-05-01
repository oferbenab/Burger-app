import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, time
import json

# --- הגדרות דף ---
st.set_page_config(page_title="הפסאז' Pro - גרסה מלאה", layout="wide")

# CSS לקיבוע אלמנטים בשורה אחת ומראה מובייל
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    
    /* מניעת קריסת עמודות במובייל - חשוב להיסטוריה */
    [data-testid="column"] { min-width: auto !important; flex: 1 1 0% !important; }
    div[data-testid="stHorizontalBlock"] { gap: 5px; }
    
    .stTabs [data-baseweb="tab-list"] { gap: 5px; }
    .stMetric { background: #fdfdfd; padding: 5px; border-radius: 5px; border: 1px solid #eee; }
    
    /* עיצוב כפתורים קטנים להיסטוריה */
    .small-btn button { padding: 2px 5px !important; height: 30px !important; width: 100% !important; }
    </style>
    """, unsafe_allow_html=True)

# --- חיבור ל-DB ---
conn = sqlite3.connect('passaz_final_v15.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, price INTEGER)')
c.execute('''CREATE TABLE IF NOT EXISTS orders 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, date TEXT, total INTEGER, 
              details_text TEXT, raw_cart TEXT, customer_data TEXT)''')
conn.commit()

# --- פונקציות ליבה ---
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
    st.toast("הנתונים נטענו בהצלחה!")

# --- אתחול Session State ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'q_idx' not in st.session_state: st.session_state.q_idx = 0
cust_keys = ['nm', 'ph', 'em', 'gs', 'ppg', 'bd', 'notes']
for k in cust_keys:
    if k not in st.session_state:
        st.session_state[k] = None if k in ['gs', 'ppg', 'bd'] else ""

# --- שורה עליונה: כפתור איפוס ---
st.button("🆕 הזמנה חדשה (איפוס שדות)", on_click=reset_order, use_container_width=True)

tab1, tab2, tab3 = st.tabs(["📝 הזמנה", "📋 היסטוריה", "⚙️ תפריט"])

# --- לשונית 1: הזמנה ---
with tab1:
    with st.expander("👤 פרטי לקוח ואירוע", expanded=True):
        c1, c2 = st.columns(2)
        st.session_state.nm = c1.text_input("שם לקוח", value=st.session_state.nm)
        st.session_state.ph = c2.text_input("טלפון", value=st.session_state.ph)
        st.session_state.em = st.text_input("אימייל", value=st.session_state.em)
        
        c3, c4, c5 = st.columns(3)
        st.session_state.gs = c3.number_input("סועדים", min_value=1, step=1, value=st.session_state.gs, placeholder="?")
        st.session_state.ppg = c4.number_input("פר סועד", min_value=0, step=1, value=st.session_state.ppg, placeholder="₪")
        st.session_state.bd = c5.number_input("תקציב", min_value=0, step=1, value=st.session_state.bd, placeholder="₪")
        
        c6, c7 = st.columns(2)
        ev_date = c6.date_input("תאריך")
        ev_time = c7.time_input("שעה", value=time(20, 0))
        st.session_state.notes = st.text_area("הערות", value=st.session_state.notes)

    st.divider()
    
    # ניהול מנות
    m_df = pd.read_sql_query("SELECT item, price FROM menu", conn)
    if not m_df.empty:
        ci, cq, ca = st.columns([3, 1, 1])
        s_it = ci.selectbox("מנה", m_df['item'].tolist(), label_visibility="collapsed")
        s_qy = cq.number_input("כמות", min_value=1, step=1, value=None, key=f"q_{st.session_state.q_idx}", placeholder="?")
        if ca.button("➕"):
            if s_qy:
                pr = int(m_df[m_df['item'] == s_it]['price'].values[0])
                st.session_state.cart.append({"מנה": s_it, "כמות": int(s_qy), "מחיר": pr, "סה''כ": int(s_qy * pr)})
                st.session_state.q_idx += 1
                st.rerun()
    
    if st.session_state.cart:
        st.table(pd.DataFrame(st.session_state.cart))
        
        # חישובים
        gs_val = st.session_state.gs if st.session_state.gs else 0
        ppg_val = st.session_state.ppg if st.session_state.ppg else 0
        base_total = sum(i["סה''כ"] for i in st.session_state.cart) + (gs_val * ppg_val)
        
        tip_pct = st.radio("תוספת טיפ", [0, 10, 12, 15], format_func=lambda x: f"{x}%", horizontal=True)
        tip_amount = int(base_total * (tip_pct/100))
        final_total = base_total + tip_amount
        
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("לפני טיפ", f"{base_total:,} ₪")
        col_m2.metric(f"טיפ ({tip_pct}%)", f"{tip_amount:,} ₪")
        col_m3.metric("סה''כ סופי", f"{final_total:,} ₪")
        
        if st.button("💾 שמור הזמנה סופית", type="primary", use_container_width=True):
            summary = f"סועדים: {gs_val} | " + ", ".join([f"{i['מנה']} x{i['כמות']}" for i in st.session_state.cart])
            f_date = f"{ev_date.strftime('%d/%m/%y')} {ev_time.strftime('%H:%M')}"
            raw_c = json.dumps(st.session_state.cart)
            raw_cust = json.dumps({k: st.session_state[k] for k in cust_keys})
            
            c.execute("INSERT INTO orders (name, date, total, details_text, raw_cart, customer_data) VALUES (?,?,?,?,?,?)", 
                     (st.session_state.nm, f_date, final_total, summary, raw_c, raw_cust))
            conn.commit()
            st.success("ההזמנה נשמרה!")

# --- לשונית 2: היסטוריה ---
with tab2:
    search = st.text_input("🔍 חיפוש לקוח", placeholder="הקלד שם...")
    hist_df = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
    
    if not hist_df.empty:
        if search:
            hist_df = hist_df[hist_df['name'].str.contains(search, na=False, case=False)]
        
        # כותרות "טבלה"
        st.markdown("**לקוח | תאריך | סכום | פעולות**")
        st.write("---")
        
        for idx, row in hist_df.iterrows():
            # שימוש ב-Columns עם רוחב מוגדר ומניעת קריסה ב-CSS
            cols = st.columns([3, 3, 2, 1, 1])
            cols[0].write(f"**{row['name']}**")
            cols[1].write(row['date'])
            cols[2].write(f"{row['total']:,} ₪")
            
            if cols[3].button("🔄", key=f"l_{row['id']}"):
                load_order(row['raw_cart'], row['customer_data'])
                st.rerun()
                
            if cols[4].button("🗑️", key=f"d_{row['id']}"):
                c.execute("DELETE FROM orders WHERE id=?", (row['id'],))
                conn.commit()
                st.rerun()
            st.divider()

# --- לשונית 3: תפריט ---
with tab3:
    df_m = pd.read_sql_query("SELECT id, item, price FROM menu", conn)
    edited = st.data_editor(df_m, column_config={"id": None}, num_rows="dynamic", use_container_width=True, hide_index=True)
    if st.button("💾 שמור תפריט מעודכן"):
        c.execute("DELETE FROM menu")
        for _, r in edited.iterrows():
            if r['item']: c.execute("INSERT INTO menu (item, price) VALUES (?,?)", (r['item'], int(r['price'])))
        conn.commit()
        st.rerun()
