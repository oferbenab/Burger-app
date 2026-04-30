import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF
import io

# --- הגדרות דף ---
st.set_page_config(page_title="הפסאז' - ניהול אירועים", layout="wide")

# --- CSS עיצוב ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3em; }
    .budget-over { color: #dc3545; font-weight: bold; border: 1px solid #dc3545; padding: 10px; border-radius: 8px; text-align: center; background: #fff5f5; }
    .budget-ok { color: #28a745; font-weight: bold; border: 1px solid #28a745; padding: 10px; border-radius: 8px; text-align: center; background: #f6fff6; }
    </style>
    """, unsafe_allow_html=True)

# --- אתחול משתנים (Session State) ---
if 'page' not in st.session_state: st.session_state.page = "new_order"
if 'cart' not in st.session_state: st.session_state.cart = []
if 'qty_key' not in st.session_state: st.session_state.qty_key = 0 # המפתח לאיפוס הכמות
if 'last_item' not in st.session_state: st.session_state.last_item = None

# פונקציית איפוס לקוח חדש
def reset_client():
    for key in list(st.session_state.keys()):
        if key not in ['page', 'qty_key']: del st.session_state[key]
    st.session_state.cart = []
    st.rerun()

# --- חיבור ל-DB ---
conn = sqlite3.connect('passaz_pro.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY, item TEXT, price REAL)')
c.execute('''CREATE TABLE IF NOT EXISTS orders 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, group_name TEXT, guests INTEGER, 
              event_date TEXT, event_time TEXT, items_json TEXT, total_price INTEGER, timestamp TEXT)''')
conn.commit()

# --- ניווט עליון (אחד לצד השני) ---
nav_cols = st.columns(3)
if nav_cols[0].button("📝 הזמנה"): st.session_state.page = "new_order"
if nav_cols[1].button("📋 היסטוריה"): st.session_state.page = "history"
if nav_cols[2].button("⚙️ תפריט"): st.session_state.page = "menu_mgmt"
st.divider()

# --- פונקציית PDF בסיסית ---
def export_pdf(data, cart):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Order Summary: {data.get('g_name', 'Client')}", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Date: {data.get('date', '')} | Guests: {data.get('guests', '')}", ln=True, align='R')
    pdf.ln(10)
    for item in cart:
        pdf.cell(100, 10, txt=f"{item['מוצר']} x{item['כמות']}", border=1)
        pdf.cell(50, 10, txt=f"{item['סה''כ']} NIS", border=1, ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- עמוד: הזמנה חדשה ---
if st.session_state.page == "new_order":
    col_h1, col_h2 = st.columns([4, 1])
    col_h1.header("פרטי אירוע")
    if col_h2.button("✨ לקוח חדש", type="primary"): reset_client()

    c1, c2, c3 = st.columns(3)
    g_name = c1.text_input("שם הקבוצה", key="g_name", value=st.session_state.get('g_name', ""))
    num_guests = c2.number_input("סועדים", min_value=1, step=1, value=st.session_state.get('guests'), placeholder="כמות...")
    target_budget = c3.number_input("תקציב יעד (₪)", min_value=1, step=1, value=None, placeholder="תקציב...")

    c_date, c_time, c_empty = st.columns(3)
    order_date = c_date.date_input("תאריך", value=datetime.now())
    order_time = c_time.time_input("שעה", value=datetime.now())

    st.divider()

    # בחירת מנות
    df_menu = pd.read_sql_query("SELECT * FROM menu", conn)
    if not df_menu.empty:
        st.subheader("🛒 הוספת מנות")
        ci, cq, ca = st.columns([3, 1, 1])
        
        items = df_menu['item'].tolist()
        last_idx = items.index(st.session_state.last_item) if st.session_state.last_item in items else 0
        sel_item = ci.selectbox("מוצר", items, index=last_idx)
        
        # שימוש ב-qty_key כדי לאפס את השדה בכוח
        sel_qty = cq.number_input("כמות", min_value=1, step=1, value=None, key=f"qty_{st.session_state.qty_key}", placeholder="?")
        
        if ca.button("➕ הוסף", use_container_width=True):
            if sel_qty:
                price = df_menu[df_menu['item'] == sel_item]['price'].values[0]
                st.session_state.cart.append({"מוצר": sel_item, "כמות": int(sel_qty), "מחיר": int(price), "סה''כ": int(sel_qty * price)})
                st.session_state.last_item = sel_item
                st.session_state.qty_key += 1 # משנה את המפתח -> השדה מתאפס
                st.rerun()

    if st.session_state.cart:
        st.table(pd.DataFrame(st.session_state.cart))
        total = sum(i["סה''כ"] for i in st.session_state.cart)
        
        st.divider()
        res1, res2 = st.columns(2)
        with res1:
            t_choice = st.radio("טיפ (מתוך הסכום)", ["0%", "10%", "15%", "20%"], horizontal=True)
            tip = int(total * (int(t_choice[:-1])/100))
            st.metric("סכום סופי", f"{total:,} ₪")
            st.write(f"טיפ כלול: **{tip:,} ₪**")
        
        with res2:
            if target_budget:
                diff = target_budget - total
                st.markdown(f'<div class="{"budget-ok" if diff >=0 else "budget-over"}">{"יתרה" if diff >=0 else "חריגה"}: {abs(diff):,} ₪</div>', unsafe_allow_html=True)

        b1, b2 = st.columns(2)
        if b1.button("💾 שמור להיסטוריה"):
            items_txt = ", ".join([f"{i['מוצר']} x{i['כמות']}" for i in st.session_state.cart])
            c.execute("INSERT INTO orders (group_name, guests, event_date, event_time, items_json, total_price, timestamp) VALUES (?,?,?,?,?,?,?)",
                      (g_name, num_guests, str(order_date), str(order_time), items_txt, total, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            st.success("נשמר!")
        
        pdf_data = {"g_name": g_name, "date": str(order_date), "guests": num_guests}
        b2.download_button("📄 הורד סיכום PDF", data=export_pdf(pdf_data, st.session_state.cart), file_name="order.pdf")

# --- עמוד: היסטוריה ---
elif st.session_state.page == "history":
    st.header("📋 היסטוריה")
    df_h = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
    for _, row in df_h.iterrows():
        with st.expander(f"{row['group_name']} | {row['event_date']} | {row['total_price']} ₪"):
            st.write(f"**מנות:** {row['items_json']}")
            hc1, hc2 = st.columns(2)
            if hc1.button("🗑️ מחק", key=f"del_{row['id']}"):
                c.execute("DELETE FROM orders WHERE id=?", (row['id'],))
                conn.commit()
                st.rerun()
            if hc2.button("🔄 טען להזמנה", key=f"load_{row['id']}"):
                st.session_state.g_name = row['group_name']
                st.session_state.guests = row['guests']
                # טעינת המנות חזרה לסל (פירוק הטקסט)
                st.session_state.cart = []
                for entry in row['items_json'].split(", "):
                    name_part, qty_part = entry.split(" x")
                    st.session_state.cart.append({"מוצר": name_part, "כמות": int(qty_part), "מחיר": 0, "סה''כ": 0})
                st.session_state.page = "new_order"
                st.rerun()

# --- עמוד: תפריט ---
elif st.session_state.page == "menu_mgmt":
    st.header("⚙️ ניהול תפריט")
    with st.form("add"):
        n = st.text_input("שם מנה")
        p = st.number_input("מחיר", min_value=1, step=1, value=None)
        if st.form_submit_button("הוסף"):
            if n and p:
                c.execute("INSERT INTO menu (item, price) VALUES (?,?)", (n, int(p)))
                conn.commit()
                st.rerun()
    st.table(pd.read_sql_query("SELECT item, price FROM menu", conn))
