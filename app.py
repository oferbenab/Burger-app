import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- הגדרות דף ---
st.set_page_config(page_title="הפסאז' - ניהול אירועים", layout="wide")

# עיצוב מותאם למובייל (אייפון)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; height: 3.5em; margin-top: 10px; }
    input { font-size: 16px !important; } 
    .main-header { font-size: 24px; font-weight: bold; color: #ff4b4b; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- ניהול זיכרון (Session State) ---
if 'v3_page' not in st.session_state: st.session_state.v3_page = "order"
if 'v3_cart' not in st.session_state: st.session_state.v3_cart = []
if 'v3_qty_key' not in st.session_state: st.session_state.v3_qty_key = 0

# משתני לקוח לשמירה במעבר דפים
for k in ['n', 'p', 'e', 'g', 'b']:
    if k not in st.session_state: st.session_state[k] = None if k in ['g', 'b'] else ""

# --- חיבור למסד נתונים ---
conn = sqlite3.connect('passaz_final.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS menu (item TEXT, price REAL)')
c.execute('CREATE TABLE IF NOT EXISTS orders (name TEXT, phone TEXT, items TEXT, total REAL, date TEXT)')
conn.commit()

# --- 1. תפריט ניווט עליון (שורה אחת) ---
n1, n2, n3 = st.columns(3)
if n1.button("📝 הזמנה"): st.session_state.v3_page = "order"
if n2.button("📋 היסטוריה"): st.session_state.v3_page = "history"
if n3.button("⚙️ תפריט"): st.session_state.v3_page = "menu"
st.divider()

# --- עמוד: הזמנה חדשה ---
if st.session_state.v3_page == "order":
    st.markdown('<div class="main-header">ביצוע הזמנה</div>', unsafe_allow_html=True)
    
    # סידור שדות לפי בקשתך (באייפון יפרסו לפי הצורך)
    # שורה 1: שם וטלפון
    r1_1, r1_2 = st.columns(2)
    st.session_state.n = r1_1.text_input("שם לקוח / קבוצה", value=st.session_state.n)
    st.session_state.p = r1_2.text_input("טלפון", value=st.session_state.p)
    
    # שורה 2: אימייל
    st.session_state.e = st.text_input("אימייל", value=st.session_state.e)
    
    # שורה 3: סועדים ותקציב (מתחת לאימייל)
    r2_1, r2_2 = st.columns(2)
    st.session_state.g = r2_1.number_input("מספר סועדים", min_value=1, step=1, value=st.session_state.g)
    st.session_state.b = r2_2.number_input("תקציב יעד (₪)", min_value=0, step=10, value=st.session_state.b)
    
    # שורה 4: תאריך ושעה
    r3_1, r3_2 = st.columns(2)
    ev_date = r3_1.date_input("תאריך האירוע", value=datetime.now())
    ev_time = r3_2.time_input("שעת האירוע", value=datetime.now())

    st.divider()
    
    # --- חלק הוספת המנות (כאן הייתה הבעיה) ---
    st.subheader("🛒 בחירת מנות מהתפריט")
    menu_df = pd.read_sql_query("SELECT * FROM menu", conn)
    
    if not menu_df.empty:
        # פריט וכמות זה לצד זה
        sel_col, qty_col = st.columns([2, 1])
        item_name = sel_col.selectbox("בחר מנה", menu_df['item'].tolist())
        item_qty = qty_col.number_input("כמות", min_value=1, step=1, value=None, key=f"q_{st.session_state.v3_qty_key}")
        
        if st.button("➕ הוסף להזמנה"):
            if item_qty:
                price = menu_df[menu_df['item'] == item_name]['price'].values[0]
                st.session_state.v3_cart.append({
                    "מנה": item_name, 
                    "כמות": int(item_qty), 
                    "סה''כ": int(item_qty * price)
                })
                st.session_state.v3_qty_key += 1 # איפוס שדה הכמות
                st.rerun()
            else:
                st.warning("נא להזין כמות")
    else:
        st.info("התפריט ריק. יש להוסיף מנות בלשונית 'תפריט'.")

    # הצגת טבלת סיכום
    if st.session_state.v3_cart:
        st.write("### סיכום הזמנה")
        st.table(pd.DataFrame(st.session_state.v3_cart))
        total_price = sum(item["סה''כ"] for item in st.session_state.v3_cart)
        st.write(f"**סה''כ לתשלום: {total_price:,} ₪**")
        
        if st.button("💾 שמור הזמנה סופית"):
            details = ", ".join([f"{i['מנה']} x{i['כמות']}" for i in st.session_state.v3_cart])
            c.execute("INSERT INTO orders VALUES (?,?,?,?,?)", 
                     (st.session_state.n, st.session_state.p, details, total_price, datetime.now().strftime("%d/%m/%Y")))
            conn.commit()
            st.success("ההזמנה נשמרה בהצלחה!")
            st.session_state.v3_cart = []
            st.rerun()

# --- עמוד: ניהול תפריט ---
elif st.session_state.v3_page == "menu":
    st.header("ניהול תפריט")
    with st.form("add_dish"):
        new_name = st.text_input("שם המנה")
        new_price = st.number_input("מחיר", min_value=1)
        if st.form_submit_button("הוסף לתפריט"):
            if new_name:
                c.execute("INSERT INTO menu VALUES (?,?)", (new_name, new_price))
                conn.commit()
                st.rerun()
    
    st.subheader("מנות קיימות")
    st.table(pd.read_sql_query("SELECT * FROM menu", conn))

# --- עמוד: היסטוריה ---
elif st.session_state.v3_page == "history":
    st.header("היסטוריית הזמנות")
    history_df = pd.read_sql_query("SELECT * FROM orders ORDER BY rowid DESC", conn)
    st.dataframe(history_df, use_container_width=True)
