import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF

# --- 1. הגדרות דף ---
st.set_page_config(page_title="הפסאז' - ניהול מסעדה", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; }
    .budget-card { padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ניהול הזיכרון (Session State) ---
if 'page' not in st.session_state: st.session_state.page = "new_order"
if 'cart' not in st.session_state: st.session_state.cart = []
if 'qty_reset_key' not in st.session_state: st.session_state.qty_reset_key = 0

# אתחול שדות הלקוח אם אינם קיימים (כדי לשמר אותם במעבר דפים)
field_defaults = {'g_name': "", 'g_phone': "", 'g_email': "", 'num_guests': None, 'target_budget': None, 'last_item': None}
for key, val in field_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

def reset_all_fields():
    for key, val in field_defaults.items(): st.session_state[key] = val
    st.session_state.cart = []
    st.rerun()

# --- 3. DB ---
conn = sqlite3.connect('passaz_pro.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY, item TEXT, price REAL)')
c.execute('''CREATE TABLE IF NOT EXISTS orders 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, group_name TEXT, phone TEXT, email TEXT, 
              guests INTEGER, items_json TEXT, total_price INTEGER, timestamp TEXT)''')
conn.commit()

# --- 4. ניווט עליון (שורה אחת) ---
n1, n2, n3 = st.columns(3)
if n1.button("📝 מסך הזמנה"): st.session_state.page = "new_order"
if n2.button("📋 היסטוריה"): st.session_state.page = "history"
if n3.button("⚙️ ניהול תפריט"): st.session_state.page = "menu_mgmt"
st.divider()

# --- 5. דף הזמנה ---
if st.session_state.page == "new_order":
    h_col, r_col = st.columns([4, 1])
    h_col.header("פרטי לקוח ואירוע")
    if r_col.button("✨ לקוח חדש / איפוס"): reset_all_fields()

    # פרטי לקוח (נשמרים אוטומטית ב-Session State)
    c1, c2, c3 = st.columns(3)
    st.session_state.g_name = c1.text_input("שם לקוח / קבוצה", value=st.session_state.g_name)
    st.session_state.g_phone = c2.text_input("טלפון", value=st.session_state.g_phone)
    st.session_state.g_email = c3.text_input("אימייל", value=st.session_state.g_email)

    c4, c5, c6, c7 = st.columns(4)
    st.session_state.num_guests = c4.number_input("סועדים", min_value=1, step=1, value=st.session_state.num_guests, placeholder="?")
    st.session_state.target_budget = c5.number_input("תקציב יעד (₪)", min_value=1, step=1, value=st.session_state.target_budget, placeholder="?")
    order_date = c6.date_input("תאריך", value=datetime.now())
    order_time = c7.time_input("שעה", value=datetime.now())

    st.divider()

    # הוספת מנות
    df_menu = pd.read_sql_query("SELECT * FROM menu", conn)
    if not df_menu.empty:
        st.subheader("🛒 הוספת מנה")
        mi, mq, ma = st.columns([3, 1, 1])
        items = df_menu['item'].tolist()
        
        # זוכר פריט אחרון
        d_idx = items.index(st.session_state.last_item) if st.session_state.last_item in items else 0
        sel_item = mi.selectbox("מוצר", items, index=d_idx)
        
        # איפוס כמות ע"י שינוי Key
        sel_qty = mq.number_input("כמות", min_value=1, step=1, value=None, key=f"q_{st.session_state.qty_reset_key}", placeholder="?")
        
        if ma.button("➕ הוסף"):
            if sel_qty:
                p = df_menu[df_menu['item'] == sel_item]['price'].values[0]
                st.session_state.cart.append({"מוצר": sel_item, "כמות": int(sel_qty), "מחיר": int(p), "סה''כ": int(sel_qty * p)})
                st.session_state.last_item = sel_item
                st.session_state.qty_reset_key += 1 # מאפס את השדה
                st.rerun()

    # סיכום
    if st.session_state.cart:
        st.table(pd.DataFrame(st.session_state.cart))
        total = sum(i["סה''כ"] for i in st.session_state.cart)
        
        res_c1, res_c2 = st.columns(2)
        with res_c1:
            t_opt = st.radio("טיפ (מתוך הסכום)", ["0%", "10%", "15%", "20%"], horizontal=True)
            tip = int(total * (int(t_opt[:-1])/100))
            st.metric("סה''כ לתשלום", f"{total:,} ₪")
            st.write(f"מתוכו טיפ: {tip:,} ₪")
            
        with res_c2:
            if st.session_state.target_budget:
                diff = st.session_state.target_budget - total
                st.markdown(f'<div class="budget-card" style="background: {"#f6fff6" if diff >=0 else "#fff5f5"}; color: {"green" if diff >=0 else "red"};">{"יתרה" if diff >=0 else "חריגה"}: {abs(diff):,} ₪</div>', unsafe_allow_html=True)

        if st.button("💾 שמור הזמנה להיסטוריה"):
            it_str = ", ".join([f"{i['מוצר']} x{i['כמות']}" for i in st.session_state.cart])
            c.execute("INSERT INTO orders (group_name, phone, email, guests, items_json, total_price, timestamp) VALUES (?,?,?,?,?,?,?)",
                      (st.session_state.g_name, st.session_state.g_phone, st.session_state.g_email, st.session_state.num_guests, it_str, total, datetime.now().strftime("%d/%m/%Y %H:%M")))
            conn.commit()
            st.success("נשמר!")

# --- 6. דף היסטוריה ---
elif st.session_state.page == "history":
    st.header("📋 היסטוריה")
    df_h = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
    for _, row in df_h.iterrows():
        with st.expander(f"{row['group_name']} | {row['total_price']} ₪"):
            st.write(f"**פרטים:** {row['phone']} | {row['email']}")
            st.write(f"**מנות:** {row['items_json']}")
            
            b_c1, b_c2 = st.columns(2)
            if b_c1.button("🗑️ מחק", key=f"del_{row['id']}"):
                c.execute("DELETE FROM orders WHERE id=?", (row['id'],))
                conn.commit()
                st.rerun()
            if b_c2.button("🔄 טען לעריכה", key=f"load_{row['id']}"):
                st.session_state.g_name = row['group_name']
                st.session_state.g_phone = row['phone']
                st.session_state.g_email = row['email']
                st.session_state.num_guests = row['guests']
                # פירוק המנות חזרה לסל
                st.session_state.cart = []
                for entry in row['items_json'].split(", "):
                    p_n, p_q = entry.split(" x")
                    st.session_state.cart.append({"מוצר": p_n, "כמות": int(p_q), "מחיר": 0, "סה''כ": 0})
                st.session_state.page = "new_order"
                st.rerun()

# --- 7. דף תפריט ---
elif st.session_state.page == "menu_mgmt":
    st.header("⚙️ ניהול תפריט")
    with st.form("new_item"):
        n = st.text_input("שם מנה")
        p = st.number_input("מחיר", min_value=1, step=1, value=None)
        if st.form_submit_button("הוסף"):
            if n and p:
                c.execute("INSERT INTO menu (item, price) VALUES (?,?)", (n, int(p)))
                conn.commit()
                st.rerun()
    st.table(pd.read_sql_query("SELECT item, price FROM menu", conn))
