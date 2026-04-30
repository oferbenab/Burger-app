import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF
import io

# --- 1. הגדרות דף ועיצוב ---
st.set_page_config(page_title="הפסאז' - מערכת ניהול", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3em; }
    .budget-over { color: #dc3545; font-weight: bold; border: 1px solid #dc3545; padding: 10px; border-radius: 8px; text-align: center; background: #fff5f5; }
    .budget-ok { color: #28a745; font-weight: bold; border: 1px solid #28a745; padding: 10px; border-radius: 8px; text-align: center; background: #f6fff6; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. אתחול משתני מערכת (Session State) ---
if 'page' not in st.session_state: st.session_state.page = "new_order"
if 'cart' not in st.session_state: st.session_state.cart = []
if 'qty_key' not in st.session_state: st.session_state.qty_key = 0
if 'last_item' not in st.session_state: st.session_state.last_item = None

# שדות פרטי לקוח לשימור נתונים
for key in ['g_name', 'g_phone', 'g_email', 'num_guests', 'target_budget']:
    if key not in st.session_state:
        st.session_state[key] = None if key in ['num_guests', 'target_budget'] else ""

# פונקציות עזר
def reset_client():
    st.session_state.g_name = ""
    st.session_state.g_phone = ""
    st.session_state.g_email = ""
    st.session_state.num_guests = None
    st.session_state.target_budget = None
    st.session_state.cart = []
    st.rerun()

# --- 3. בסיס נתונים ---
conn = sqlite3.connect('passaz_pro.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY, item TEXT, price REAL)')
c.execute('''CREATE TABLE IF NOT EXISTS orders 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, group_name TEXT, phone TEXT, email TEXT, 
              guests INTEGER, event_date TEXT, event_time TEXT, items_json TEXT, 
              total_price INTEGER, tip_amount INTEGER, timestamp TEXT)''')
conn.commit()

# --- 4. ניווט עליון (שורה אחת) ---
nav_cols = st.columns(3)
if nav_cols[0].button("📝 הזמנה"): st.session_state.page = "new_order"
if nav_cols[1].button("📋 היסטוריה"): st.session_state.page = "history"
if nav_cols[2].button("⚙️ תפריט"): st.session_state.page = "menu_mgmt"
st.divider()

# --- 5. פונקציית PDF ---
def create_pdf(client_data, cart_items, total, tip):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Order Summary - Passaz", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Client: {client_data['name']} | Phone: {client_data['phone']}", ln=True, align='L')
    pdf.cell(200, 10, txt=f"Date: {client_data['date']} | Time: {client_data['time']}", ln=True, align='L')
    pdf.ln(5)
    for item in cart_items:
        pdf.cell(100, 10, txt=f"{item['מוצר']} x{item['כמות']}", border=1)
        pdf.cell(50, 10, txt=f"{item['סה''כ']} NIS", border=1, ln=True)
    pdf.ln(5)
    pdf.cell(200, 10, txt=f"Total: {total} NIS (Includes {tip} NIS Tip)", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- 6. דף הזמנה חדשה ---
if st.session_state.page == "new_order":
    col_h1, col_h2 = st.columns([4, 1])
    col_h1.header("פרטי אירוע ולקוח")
    if col_h2.button("✨ לקוח חדש", type="primary"): reset_client()

    # שורת פרטי קשר
    c1, c2, c3 = st.columns(3)
    st.session_state.g_name = c1.text_input("שם הקבוצה", value=st.session_state.g_name)
    st.session_state.g_phone = c2.text_input("טלפון", value=st.session_state.g_phone)
    st.session_state.g_email = c3.text_input("אימייל", value=st.session_state.g_email)

    # שורת כמות ותקציב
    c4, c5, c6, c7 = st.columns(4)
    st.session_state.num_guests = c4.number_input("סועדים", min_value=1, step=1, value=st.session_state.num_guests, placeholder="?")
    st.session_state.target_budget = c5.number_input("תקציב (₪)", min_value=1, step=1, value=st.session_state.target_budget, placeholder="?")
    order_date = c6.date_input("תאריך", value=datetime.now())
    order_time = c7.time_input("שעה", value=datetime.now())

    st.divider()

    # הוספת מנות
    df_menu = pd.read_sql_query("SELECT * FROM menu", conn)
    if not df_menu.empty:
        st.subheader("🛒 תפריט")
        ci, cq, ca = st.columns([3, 1, 1])
        items = df_menu['item'].tolist()
        last_idx = items.index(st.session_state.last_item) if st.session_state.last_item in items else 0
        sel_item = ci.selectbox("בחר מנה", items, index=last_idx)
        
        # איפוס כמות ע"י שינוי מפתח
        sel_qty = cq.number_input("כמות", min_value=1, step=1, value=None, key=f"q_{st.session_state.qty_key}", placeholder="?")
        
        if ca.button("➕ הוסף"):
            if sel_qty:
                price = df_menu[df_menu['item'] == sel_item]['price'].values[0]
                st.session_state.cart.append({"מוצר": sel_item, "כמות": int(sel_qty), "מחיר": int(price), "סה''כ": int(sel_qty * price)})
                st.session_state.last_item = sel_item
                st.session_state.qty_key += 1
                st.rerun()

    if st.session_state.cart:
        st.table(pd.DataFrame(st.session_state.cart))
        total = sum(i["סה''כ"] for i in st.session_state.cart)
        
        # חישוב טיפ ותקציב
        res1, res2 = st.columns(2)
        with res1:
            t_choice = st.radio("טיפ מתוך הסכום", ["0%", "10%", "15%", "20%"], horizontal=True)
            tip = int(total * (int(t_choice[:-1])/100))
            st.metric("סכום סופי", f"{total:,} ₪")
            st.write(f"מתוכו טיפ: **{tip:,} ₪**")
        
        with res2:
            if st.session_state.target_budget:
                diff = st.session_state.target_budget - total
                st.markdown(f'<div class="{"budget-ok" if diff >=0 else "budget-over"}">{"יתרה" if diff >=0 else "חריגה"}: {abs(diff):,} ₪</div>', unsafe_allow_html=True)

        # שמירה וייצוא
        b1, b2 = st.columns(2)
        if b1.button("💾 שמור להיסטוריה"):
            items_txt = ", ".join([f"{i['מוצר']} x{i['כמות']}" for i in st.session_state.cart])
            c.execute('''INSERT INTO orders (group_name, phone, email, guests, event_date, event_time, items_json, total_price, tip_amount, timestamp) 
                         VALUES (?,?,?,?,?,?,?,?,?,?)''',
                      (st.session_state.g_name, st.session_state.g_phone, st.session_state.g_email, st.session_state.num_guests, 
                       str(order_date), str(order_time), items_txt, total, tip, datetime.now().strftime("%d/%m/%Y %H:%M")))
            conn.commit()
            st.success("נשמר בהצלחה!")
        
        pdf_info = {"name": st.session_state.g_name, "phone": st.session_state.g_phone, "date": str(order_date), "time": str(order_time)}
        b2.download_button("📄 הורד PDF", data=create_pdf(pdf_info, st.session_state.cart, total, tip), file_name=f"{st.session_state.g_name}.pdf")

# --- 7. דף היסטוריה ---
elif st.session_state.page == "history":
    st.header("📋 היסטוריית הזמנות")
    df_h = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
    for _, row in df_h.iterrows():
        with st.expander(f"{row['group_name']} | {row['event_date']} | {row['total_price']} ₪"):
            st.write(f"**טלפון:** {row['phone']} | **אימייל:** {row['email']}")
            st.write(f"**פירוט:** {row['items_json']}")
            
            hc1, hc2 = st.columns(2)
            if hc1.button("🗑️ מחק", key=f"del_{row['id']}"):
                c.execute("DELETE FROM orders WHERE id=?", (row['id'],))
                conn.commit()
                st.rerun()
            if hc2.button("🔄 טען להזמנה", key=f"load_{row['id']}"):
                st.session_state.g_name = row['group_name']
                st.session_state.g_phone = row['phone']
                st.session_state.g_email = row['email']
                st.session_state.num_guests = row['guests']
                st.session_state.cart = []
                for entry in row['items_json'].split(", "):
                    try:
                        name_p, qty_p = entry.split(" x")
                        st.session_state.cart.append({"מוצר": name_p, "כמות": int(qty_p), "מחיר": 0, "סה''כ": 0})
                    except: pass
                st.session_state.page = "new_order"
                st.rerun()

# --- 8. דף תפריט ---
elif st.session_state.page == "menu_mgmt":
    st.header("⚙️ ניהול תפריט")
    with st.form("add_item"):
        n = st.text_input("שם מנה")
        p = st.number_input("מחיר", min_value=1, step=1, value=None)
        if st.form_submit_button("הוסף לתפריט"):
            if n and p:
                c.execute("INSERT INTO menu (item, price) VALUES (?,?)", (n, int(p)))
                conn.commit()
                st.rerun()
    st.table(pd.read_sql_query("SELECT item, price FROM menu", conn))
