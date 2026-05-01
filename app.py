import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- הגדרות דף ---
st.set_page_config(page_title="הפסאז' - גרסה יציבה", layout="wide")

# עיצוב מותאם לאייפון
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    
    /* עיצוב לשוניות (Tabs) */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; justify-content: center; }
    .stTabs [data-baseweb="tab"] { 
        background-color: #f0f2f6; border-radius: 10px 10px 0 0; 
        padding: 10px 20px; font-weight: bold;
    }
    
    /* מניעת קריסה של עמודות באייפון */
    [data-testid="column"] { min-width: 45% !important; flex: 1 1 45% !important; }
    input { font-size: 16px !important; }
    .stMetric { background: #f8f9fa; padding: 10px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- ניהול זיכרון (Session State) ---
# שימוש במפתחות קבועים כדי למנוע איבוד נתונים
if 'cart' not in st.session_state: st.session_state.cart = []
if 'q_idx' not in st.session_state: st.session_state.q_idx = 0

# אתחול שדות לקוח - לא נמחקים לעולם אלא אם המשתמש משנה
fields = {'nm': "", 'ph': "", 'em': "", 'gs': 1, 'bd': 0}
for k, v in fields.items():
    if k not in st.session_state: st.session_state[k] = v

# --- חיבור ל-DB ---
conn = sqlite3.connect('passaz_final_v5.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS menu (item TEXT, price REAL)')
c.execute('CREATE TABLE IF NOT EXISTS orders (name TEXT, details TEXT, total REAL, date TEXT)')
conn.commit()

# --- תפריט לשוניות עליון ---
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

    # חלק הוספת המנות
    st.subheader("🛒 ניהול סל מנות")
    m_df = pd.read_sql_query("SELECT * FROM menu", conn)
    
    if not m_df.empty:
        col_item, col_qty = st.columns([2, 1])
        sel_item = col_item.selectbox("מנה מהתפריט", m_df['item'].tolist())
        sel_qty = col_qty.number_input("כמות", min_value=1, value=None, key=f"q_{st.session_state.q_idx}", placeholder="?")
        
        if st.button("➕ הוסף להזמנה"):
            if sel_qty:
                price = m_df[m_df['item'] == sel_item]['price'].values[0]
                st.session_state.cart.append({
                    "מנה": sel_item, "כמות": int(sel_qty), 
                    "מחיר": int(price), "סה''כ": int(sel_qty * price)
                })
                st.session_state.q_idx += 1
                st.rerun()
    else:
        st.info("התפריט ריק. הוסף מנות בלשונית 'ניהול תפריט'.")

    # הצגת סל וסיכומים
    if st.session_state.cart:
        st.write("---")
        st.table(pd.DataFrame(st.session_state.cart))
        
        subtotal = sum(i["סה''כ"] for i in st.session_state.cart)
        
        # חישוב טיפ
        st.write("**הוספת טיפ:**")
        tip_pct = st.radio("אחוז", [0, 10, 15, 20], format_func=lambda x: f"{x}%", horizontal=True)
        tip_val = int(subtotal * (tip_pct / 100))
        total_all = subtotal + tip_val
        
        # תצוגת מטריקות (תקציב ופער)
        m1, m2 = st.columns(2)
        m1.metric("סה''כ לתשלום", f"{total_all:,} ₪", delta=f"טיפ: {tip_val}")
        
        if st.session_state.bd > 0:
            diff = st.session_state.bd - total_all
            m2.metric("יתרה/חריגה", f"{diff:,} ₪", delta=diff, delta_color="normal")

        if st.button("💾 שמור הזמנה בבסיס הנתונים"):
            details = ", ".join([f"{i['מנה']} x{i['כמות']}" for i in st.session_state.cart])
            c.execute("INSERT INTO orders VALUES (?,?,?,?)", 
                     (st.session_state.nm, details, total_all, datetime.now().strftime("%d/%m/%Y %H:%M")))
            conn.commit()
            st.success("ההזמנה נשמרה בהצלחה! הנתונים נשמרים במסך.")

# --- לשונית 2: היסטוריה ---
with tab2:
    st.subheader("היסטוריית הזמנות")
    hist_df = pd.read_sql_query("SELECT * FROM orders ORDER BY rowid DESC", conn)
    st.dataframe(hist_df, use_container_width=True)

# --- לשונית 3: תפריט ---
with tab3:
    st.subheader("ניהול מנות")
    with st.form("add_dish"):
        n_dish = st.text_input("שם מנה")
        p_dish = st.number_input("מחיר", min_value=1)
        if st.form_submit_button("הוסף לתפריט"):
            if n_dish:
                c.execute("INSERT INTO menu VALUES (?,?)", (n_dish, p_dish))
                conn.commit()
                st.rerun()
    
    st.write("---")
    st.table(pd.read_sql_query("SELECT * FROM menu", conn))
