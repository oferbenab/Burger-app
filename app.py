import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- הגדרות דף ---
st.set_page_config(page_title="הפסאז' - ניהול אירועים", layout="wide")

# --- CSS עיצוב ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

# --- אתחול משתנים (Session State) לשימור נתונים ---
if 'page' not in st.session_state: st.session_state.page = "new_order"
if 'cart' not in st.session_state: st.session_state.cart = []
if 'qty_key' not in st.session_state: st.session_state.qty_key = 0

# ערכי ברירת מחדל לשדות (כדי שלא יתאפסו במעבר דפים)
if 'g_name' not in st.session_state: st.session_state.g_name = ""
if 'g_phone' not in st.session_state: st.session_state.g_phone = ""
if 'g_email' not in st.session_state: st.session_state.g_email = ""
if 'num_guests' not in st.session_state: st.session_state.num_guests = None
if 'target_budget' not in st.session_state: st.session_state.target_budget = None

# פונקציית איפוס לקוח חדש
def reset_client():
    st.session_state.g_name = ""
    st.session_state.g_phone = ""
    st.session_state.g_email = ""
    st.session_state.num_guests = None
    st.session_state.target_budget = None
    st.session_state.cart = []
    st.rerun()

# --- חיבור ל-DB ---
conn = sqlite3.connect('passaz_pro.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY, item TEXT, price REAL)')
c.execute('''CREATE TABLE IF NOT EXISTS orders 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, group_name TEXT, phone TEXT, email TEXT, 
              guests INTEGER, items_json TEXT, total_price INTEGER, timestamp TEXT)''')
conn.commit()

# --- ניווט עליון (כפתורי "יציאה" וחזרה בין דפים) ---
nav_cols = st.columns(3)
if nav_cols[0].button("📝 מסך הזמנה"): st.session_state.page = "new_order"
if nav_cols[1].button("📋 היסטוריה"): st.session_state.page = "history"
if nav_cols[2].button("⚙️ ניהול תפריט"): st.session_state.page = "menu_mgmt"
st.divider()

# --- עמוד: הזמנה חדשה ---
if st.session_state.page == "new_order":
    col_h1, col_h2 = st.columns([4, 1])
    col_h1.header("פרטי לקוח ואירוע")
    if col_h2.button("✨ לקוח חדש", type="primary"): reset_client()

    # שורת פרטי קשר
    c1, c2, c3 = st.columns(3)
    st.session_state.g_name = c1.text_input("שם הקבוצה/לקוח", value=st.session_state.g_name)
    st.session_state.g_phone = c2.text_input("טלפון", value=st.session_state.g_phone)
    st.session_state.g_email = c3.text_input("אימייל", value=st.session_state.g_email)

    # שורת פרטי אירוע
    c4, c5, c6 = st.columns(3)
    st.session_state.num_guests = c4.number_input("מספר סועדים", min_value=1, step=1, value=st.session_state.num_guests, placeholder="כמות...")
    st.session_state.target_budget = c5.number_input("תקציב יעד (₪)", min_value=1, step=1, value=st.session_state.target_budget, placeholder="תקציב...")
    
    st.divider()

    # בחירת מנות (הלוגיקה של איפוס הכמות נשמרה)
    df_menu = pd.read_sql_query("SELECT * FROM menu", conn)
    if not df_menu.empty:
        st.subheader("🛒 הוספת מנות")
        ci, cq, ca = st.columns([3, 1, 1])
        sel_item = ci.selectbox("מוצר", df_menu['item'].tolist())
        sel_qty = cq.number_input("כמות", min_value=1, step=1, value=None, key=f"qty_{st.session_state.qty_key}", placeholder="?")
        
        if ca.button("➕ הוסף להזמנה"):
            if sel_qty:
                price = df_menu[df_menu['item'] == sel_item]['price'].values[0]
                st.session_state.cart.append({"מוצר": sel_item, "כמות": int(sel_qty), "מחיר": int(price), "סה''כ": int(sel_qty * price)})
                st.session_state.qty_key += 1
                st.rerun()

    # הצגת הסל ושמירה
    if st.session_state.cart:
        st.table(pd.DataFrame(st.session_state.cart))
        total = sum(i["סה''כ"] for i in st.session_state.cart)
        st.metric("סה''כ לתשלום", f"{total:,} ₪")
        
        if st.button("💾 שמור הזמנה סופית"):
            items_txt = ", ".join([f"{i['מוצר']} x{i['כמות']}" for i in st.session_state.cart])
            c.execute("INSERT INTO orders (group_name, phone, email, guests, items_json, total_price, timestamp) VALUES (?,?,?,?,?,?,?)",
                      (st.session_state.g_name, st.session_state.g_phone, st.session_state.g_email, st.session_state.num_guests, items_txt, total, datetime.now().strftime("%d/%m/%Y %H:%M")))
            conn.commit()
            st.success("ההזמנה נשמרה בהיסטוריה!")

# --- עמוד: היסטוריה ---
elif st.session_state.page == "history":
    st.header("📋 היסטוריית הזמנות")
    # כפתור חזרה מהיר (כפתור יציאה)
    if st.button("🔙 חזור למסך הזמנה (שומר נתונים)"):
        st.session_state.page = "new_order"
        st.rerun()
    
    df_h = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
    st.dataframe(df_h, use_container_width=True)

# --- עמוד: תפריט ---
elif st.session_state.page == "menu_mgmt":
    st.header("⚙️ ניהול תפריט")
    if st.button("🔙 חזור למסך הזמנה"):
        st.session_state.page = "new_order"
        st.rerun()
    
    # כאן נשאר קוד הוספת המנות המקורי שלך...
