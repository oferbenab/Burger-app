import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- הגדרות דף ---
st.set_page_config(page_title="הפסאז'", layout="wide")

# עיצוב מיוחד לאייפון - מניעת שבירת שורות ושיפור כפתורים
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; height: 3em; }
    input { font-size: 16px !important; }
    /* ניסיון להצמדת עמודות במובייל */
    [data-testid="column"] { min-width: 45% !important; flex: 1 1 45% !important; }
    .budget-box { padding: 10px; border-radius: 10px; text-align: center; font-weight: bold; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- ניהול זיכרון (Session State) ---
if 'page' not in st.session_state: st.session_state.page = "הזמנה"
if 'order_cart' not in st.session_state: st.session_state.order_cart = []
if 'qty_key' not in st.session_state: st.session_state.qty_key = 0

# אתחול שדות לקוח
client_fields = {'name': "", 'phone': "", 'email': "", 'guests': 1, 'budget': 0, 'tip_pct': "0%"}
for key, val in client_fields.items():
    if key not in st.session_state: st.session_state[key] = val

# --- חיבור ל-DB ---
conn = sqlite3.connect('passaz_v4.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS menu (item TEXT, price REAL)')
c.execute('CREATE TABLE IF NOT EXISTS orders (details TEXT, total REAL, client TEXT, date TEXT)')
conn.commit()

# --- ניווט עליון ---
n1, n2, n3 = st.columns(3)
if n1.button("📝 מסך הזמנה"): st.session_state.page = "הזמנה"
if n2.button("📋 היסטוריה"): st.session_state.page = "היסטוריה"
if n3.button("⚙️ תפריט"): st.session_state.page = "תפריט"
st.divider()

# --- עמוד הזמנה ---
if st.session_state.page == "הזמנה":
    st.subheader("פרטי לקוח ואירוע")
    
    # שורה 1: שם וטלפון
    c1, c2 = st.columns(2)
    st.session_state.name = c1.text_input("שם לקוח", value=st.session_state.name)
    st.session_state.phone = c2.text_input("טלפון", value=st.session_state.phone)
    
    # שורה 2: אימייל (מתחת)
    st.session_state.email = st.text_input("אימייל", value=st.session_state.email)
    
    # שורה 3: סועדים ותקציב
    c3, c4 = st.columns(2)
    st.session_state.guests = c3.number_input("סועדים", min_value=1, value=st.session_state.guests)
    st.session_state.budget = c4.number_input("תקציב (₪)", min_value=0, value=st.session_state.budget)
    
    # שורה 4: תאריך ושעה (בחירה יעילה)
    c5, c6, c7 = st.columns([2, 1, 1])
    ev_date = c5.date_input("תאריך", value=datetime.now())
    # בחירת שעה ודקות במקום הקלדה
    hours = [f"{i:02d}" for i in range(24)]
    mins = [f"{i:02d}" for i in range(0, 60, 5)]
    sel_h = c6.selectbox("שעה", hours, index=19)
    sel_m = c7.selectbox("דקות", mins, index=0)

    st.divider()
    
    # --- הוספת פריטים ---
    st.subheader("🛒 ניהול הזמנה")
    m_df = pd.read_sql_query("SELECT * FROM menu", conn)
    
    col_sel, col_q, col_add = st.columns([2, 1, 1])
    if not m_df.empty:
        items_list = m_df['item'].tolist()
        chosen_item = col_sel.selectbox("בחר מנה", items_list)
        chosen_qty = col_q.number_input("כמות", min_value=1, value=None, key=f"q_{st.session_state.qty_key}", placeholder="?")
        
        if col_add.button("➕ הוסף"):
            if chosen_qty:
                item_price = m_df[m_df['item'] == chosen_item]['price'].values[0]
                st.session_state.order_cart.append({
                    "מנה": chosen_item, "כמות": int(chosen_qty), 
                    "מחיר": int(item_price), "סה''כ": int(chosen_qty * item_price)
                })
                st.session_state.qty_key += 1
                st.rerun()
    else:
        st.info("התפריט ריק. הוסף מנות בניהול תפריט.")

    # תצוגת הסל וחישובים
    if st.session_state.order_cart:
        st.table(pd.DataFrame(st.session_state.order_cart))
        
        raw_total = sum(i["סה''כ"] for i in st.session_state.order_cart)
        
        # פונקציית טיפ
        st.write("**הוספת טיפ:**")
        tip_choice = st.radio("בחר אחוז", ["0%", "10%", "15%", "20%"], horizontal=True, key="tip_radio")
        tip_val = int(raw_total * (int(tip_choice[:-1])/100))
        final_total = raw_total + tip_val
        
        # תצוגת חישובים ותקציב
        res_c1, res_c2 = st.columns(2)
        with res_c1:
            st.metric("סה''כ הזמנה", f"{raw_total:,} ₪")
            if tip_val > 0: st.write(f"טיפ: {tip_val:,} ₪")
            st.metric("לתשלום סופי", f"{final_total:,} ₪")
            
        with res_c2:
            if st.session_state.budget > 0:
                diff = st.session_state.budget - final_total
                color = "#e6fffa" if diff >= 0 else "#fff5f5"
                text_color = "green" if diff >= 0 else "red"
                status = "יתרה" if diff >= 0 else "חריגה"
                st.markdown(f"""<div class="budget-box" style="background:{color}; color:{text_color};">
                            {status}: {abs(diff):,} ₪</div>""", unsafe_allow_html=True)

        if st.button("💾 שמור הזמנה (ללא מחיקה)"):
            order_summary = ", ".join([f"{i['מנה']} x{i['כמות']}" for i in st.session_state.order_cart])
            c.execute("INSERT INTO orders VALUES (?,?,?,?)", 
                     (order_summary, final_total, st.session_state.name, datetime.now().strftime("%d/%m/%Y")))
            conn.commit()
            st.success("ההזמנה נשמרה בבסיס הנתונים!")

# --- עמוד תפריט ---
elif st.session_state.page == "תפריט":
    st.header("ניהול תפריט")
    with st.form("new_item"):
        n = st.text_input("שם מנה")
        p = st.number_input("מחיר", min_value=1)
        if st.form_submit_button("הוסף"):
            if n:
                c.execute("INSERT INTO menu VALUES (?,?)", (n, p))
                conn.commit()
                st.rerun()
    st.table(pd.read_sql_query("SELECT * FROM menu", conn))

# --- עמוד היסטוריה ---
elif st.session_state.page == "היסטוריה":
    st.header("היסטוריה")
    st.dataframe(pd.read_sql_query("SELECT * FROM orders", conn), use_container_width=True)
