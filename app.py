import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- הגדרות דף ---
st.set_page_config(page_title="הפסאז' - Mobile Optimized", layout="wide")

# עיצוב מותאם למובייל
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    
    /* עיצוב ה-Expander שיהיה בולט יותר */
    .streamlit-expanderHeader { background-color: #f0f2f6; border-radius: 10px; font-weight: bold; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; }
    
    /* הצמדת עמודות במובייל */
    [data-testid="column"] { min-width: 45% !important; flex: 1 1 45% !important; }
    
    .budget-card { padding: 15px; border-radius: 10px; text-align: center; border: 2px solid #ddd; }
    </style>
    """, unsafe_allow_html=True)

# --- ניהול זיכרון (Session State) ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'page' not in st.session_state: st.session_state.page = "order"
if 'q_reset' not in st.session_state: st.session_state.q_reset = 0

# שדות לקוח (נשמרים לאורך כל הסשן)
for f, d in {'n': "", 'p': "", 'e': "", 'g': 1, 'b': 0}.items():
    if f not in st.session_state: st.session_state[f] = d

# --- חיבור ל-DB ---
conn = sqlite3.connect('passaz_pro.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS menu (item TEXT, price REAL)')
c.execute('CREATE TABLE IF NOT EXISTS orders (name TEXT, details TEXT, total REAL, date TEXT)')
conn.commit()

# --- ניווט עליון ---
n1, n2, n3 = st.columns(3)
if n1.button("📝 הזמנה"): st.session_state.page = "order"
if n2.button("📋 היסטוריה"): st.session_state.page = "history"
if n3.button("⚙️ תפריט"): st.session_state.page = "menu"
st.divider()

# --- דף הזמנה ---
if st.session_state.page == "order":
    
    # 1. כרטיסיית פרטי אירוע
    with st.expander("👤 פרטי לקוח וזמנים", expanded=True):
        c1, c2 = st.columns(2)
        st.session_state.n = c1.text_input("שם", value=st.session_state.n)
        st.session_state.p = c2.text_input("טלפון", value=st.session_state.p)
        st.session_state.e = st.text_input("אימייל", value=st.session_state.e)
        
        c3, c4 = st.columns(2)
        st.session_state.g = c3.number_input("סועדים", min_value=1, value=st.session_state.g)
        st.session_state.b = c4.number_input("תקציב (₪)", min_value=0, value=st.session_state.b)
        
        st.write("מתי האירוע?")
        c5, c6, c7 = st.columns([2, 1, 1])
        ev_date = c5.date_input("תאריך", label_visibility="collapsed")
        h = c6.selectbox("שעה", [f"{i:02d}" for i in range(24)], index=20)
        m = c7.selectbox("דקות", [f"{i:02d}" for i in range(0,60,5)], index=0)

    # 2. כרטיסיית הוספת מנות
    with st.expander("🍽️ בחירת מנות מהתפריט", expanded=True):
        m_df = pd.read_sql_query("SELECT * FROM menu", conn)
        if not m_df.empty:
            col_i, col_q = st.columns([2, 1])
            sel_item = col_i.selectbox("מנה", m_df['item'].tolist())
            sel_qty = col_q.number_input("כמות", min_value=1, value=None, key=f"qr_{st.session_state.q_reset}")
            
            if st.button("➕ הוסף לסל"):
                if sel_qty:
                    price = m_df[m_df['item'] == sel_item]['price'].values[0]
                    st.session_state.cart.append({
                        "מנה": sel_item, "כמות": int(sel_qty), 
                        "מחיר": int(price), "סה''כ": int(sel_qty * price)
                    })
                    st.session_state.q_reset += 1
                    st.rerun()
        else:
            st.info("הוסף מנות בדף 'ניהול תפריט'")

    # 3. כרטיסיית סיכום ושמירה (נפתחת רק כשיש פריטים)
    if st.session_state.cart:
        with st.expander("💰 סיכום תשלום ושמירה", expanded=True):
            st.table(pd.DataFrame(st.session_state.cart))
            
            subtotal = sum(i["סה''כ"] for i in st.session_state.cart)
            
            # בחירת טיפ
            tip_p = st.select_slider("בחר אחוז טיפ", options=[0, 10, 15, 20], value=0)
            tip_a = int(subtotal * (tip_p / 100))
            grand_total = subtotal + tip_a
            
            st.divider()
            
            # תצוגת תקציב
            r1, r2 = st.columns(2)
            r1.metric("סה''כ לתשלום", f"{grand_total:,} ₪", delta=f"טיפ: {tip_a}")
            
            if st.session_state.b > 0:
                diff = st.session_state.b - grand_total
                status = "יתרה" if diff >= 0 else "חריגה"
                color = "green" if diff >= 0 else "red"
                r2.markdown(f"""<div class="budget-card">
                            <span style="color:{color}; font-size:1.1em; font-weight:bold;">{status}</span><br>
                            <span style="font-size:1.4em;">{abs(diff):,} ₪</span>
                            </div>""", unsafe_allow_html=True)
            
            if st.button("💾 שמור הזמנה סופית"):
                summary = ", ".join([f"{i['מנה']} x{i['כמות']}" for i in st.session_state.cart])
                c.execute("INSERT INTO orders VALUES (?,?,?,?)", 
                         (st.session_state.n, summary, grand_total, datetime.now().strftime("%d/%m/%Y %H:%M")))
                conn.commit()
                st.success("נשמר בהצלחה! הנתונים נשארים על המסך.")

# --- ניהול תפריט ---
elif st.session_state.page == "menu":
    st.header("ניהול תפריט")
    with st.form("add"):
        n_item = st.text_input("שם המנה")
        p_item = st.number_input("מחיר", min_value=1)
        if st.form_submit_button("הוסף"):
            c.execute("INSERT INTO menu VALUES (?,?)", (n_item, p_item))
            conn.commit()
            st.rerun()
    st.table(pd.read_sql_query("SELECT * FROM menu", conn))

# --- היסטוריה ---
elif st.session_state.page == "history":
    st.header("היסטוריה")
    st.dataframe(pd.read_sql_query("SELECT * FROM orders ORDER BY rowid DESC", conn), use_container_width=True)
