import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF
import io

# --- 1. הגדרות דף ועיצוב (UI) ---
st.set_page_config(page_title="הפסאז' - ניהול אירועים", layout="wide")

# עיצוב CSS לשמירה על נראות מקצועית ועברית
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; height: 3.5em; background-color: #f0f2f6; }
    .stButton>button:hover { border: 1px solid #ff4b4b; color: #ff4b4b; }
    .budget-over { color: #dc3545; font-weight: bold; border: 1px solid #dc3545; padding: 10px; border-radius: 8px; text-align: center; background: #fff5f5; }
    .budget-ok { color: #28a745; font-weight: bold; border: 1px solid #28a745; padding: 10px; border-radius: 8px; text-align: center; background: #f6fff6; }
    [data-testid="stMetricValue"] { font-size: 1.5rem; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. אתחול משתני מערכת (Session State) ---
# ניווט
if 'page' not in st.session_state: st.session_state.page = "new_order"
# סל קניות
if 'cart' not in st.session_state: st.session_state.cart = []
# מפתח לאיפוס שדה הכמות
if 'qty_key' not in st.session_state: st.session_state.qty_key = 0
# זיכרון פריט אחרון שנבחר
if 'last_item' not in st.session_state: st.session_state.last_item = None

# שדות פרטי לקוח (Persistence - נשמרים במעבר בין דפים)
keys_to_init = {
    'g_name': "", 'g_phone': "", 'g_email': "", 
    'num_guests': None, 'target_budget': None,
    'order_date': datetime.now().date(),
    'order_time': datetime.now().time()
}
for key, val in keys_to_init.items():
    if key not in st.session_state:
        st.session_state[key] = val

# פונקציית איפוס לקוח חדש (מוחקת הכל)
def reset_full_system():
    for key in keys_to_init.keys():
        st.session_state[key] = keys_to_init[key]
    st.session_state.cart = []
    st.session_state.last_item = None
    st.rerun()

# --- 3. בסיס נתונים (SQLite) ---
conn = sqlite3.connect('passaz_pro.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY, item TEXT, price REAL)')
c.execute('''CREATE TABLE IF NOT EXISTS orders 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, group_name TEXT, phone TEXT, email TEXT, 
              guests INTEGER, event_date TEXT, event_time TEXT, items_json TEXT, 
              total_price INTEGER, tip_amount INTEGER, timestamp TEXT)''')
conn.commit()

# --- 4. פונקציית ייצוא ל-PDF ---
def create_pdf_report(info, cart, total, tip):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Order Summary - Passaz Restaurant", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Customer: {info['name']}", ln=True)
    pdf.cell(200, 10, txt=f"Phone: {info['phone']} | Email: {info['email']}", ln=True)
    pdf.cell(200, 10, txt=f"Date: {info['date']} | Time: {info['time']}", ln=True)
    pdf.ln(5)
    pdf.cell(100, 10, "Item", border=1)
    pdf.cell(40, 10, "Qty", border=1)
    pdf.cell(40, 10, "Price", border=1, ln=True)
    for item in cart:
        pdf.cell(100, 10, str(item['מוצר']), border=1)
        pdf.cell(40, 10, str(item['כמות']), border=1)
        pdf.cell(40, 10, f"{item['סה''כ']} NIS", border=1, ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt=f"Total Amount: {total} NIS (Including {tip} NIS Tip)", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- 5. תפריט ניווט עליון (שורה אחת) ---
n1, n2, n3 = st.columns(3)
if n1.button("📝 מסך הזמנה"): st.session_state.page = "new_order"
if n2.button("📋 היסטוריה"): st.session_state.page = "history"
if n3.button("⚙️ ניהול תפריט"): st.session_state.page = "menu_mgmt"
st.divider()

# --- 6. דף הזמנה חדשה ---
if st.session_state.page == "new_order":
    col_title, col_reset = st.columns([4, 1])
    col_title.header("פרטי לקוח ואירוע")
    if col_reset.button("✨ לקוח חדש", type="primary"): reset_full_system()

    # שורת פרטי קשר
    row1_1, row1_2, row1_3 = st.columns(3)
    st.session_state.g_name = row1_1.text_input("שם הלקוח / קבוצה", value=st.session_state.g_name)
    st.session_state.g_phone = row1_2.text_input("מספר טלפון", value=st.session_state.g_phone)
    st.session_state.g_email = row1_3.text_input("כתובת אימייל", value=st.session_state.g_email)

    # שורת תאריך, סועדים ותקציב
    row2_1, row2_2, row2_3, row2_4 = st.columns(4)
    st.session_state.num_guests = row2_1.number_input("מספר סועדים", min_value=1, step=1, value=st.session_state.num_guests, placeholder="?")
    st.session_state.target_budget = row2_2.number_input("תקציב יעד (₪)", min_value=1, step=1, value=st.session_state.target_budget, placeholder="?")
    st.session_state.order_date = row2_3.date_input("תאריך", value=st.session_state.order_date)
    st.session_state.order_time = row2_4.time_input("שעה", value=st.session_state.order_time)

    st.divider()

    # הוספת מנות מהתפריט
    df_menu = pd.read_sql_query("SELECT * FROM menu", conn)
    if not df_menu.empty:
        st.subheader("🛒 בניית הזמנה")
        ci, cq, ca = st.columns([3, 1, 1])
        menu_items = df_menu['item'].tolist()
        
        # שמירת פריט אחרון שנבחר
        default_idx = menu_items.index(st.session_state.last_item) if st.session_state.last_item in menu_items else 0
        sel_item = ci.selectbox("בחר פריט", menu_items, index=default_idx)
        
        # איפוס כמות ע"י החלפת מפתח (Key)
        sel_qty = cq.number_input("כמות", min_value=1, step=1, value=None, key=f"qty_field_{st.session_state.qty_key}", placeholder="?")
        
        if ca.button("➕ הוסף לסל"):
            if sel_qty:
                price = df_menu[df_menu['item'] == sel_item]['price'].values[0]
                st.session_state.cart.append({
                    "מוצר": sel_item, 
                    "כמות": int(sel_qty), 
                    "מחיר": int(price), 
                    "סה''כ": int(sel_qty * price)
                })
                st.session_state.last_item = sel_item # זוכר את הפריט
                st.session_state.qty_key += 1 # מאפס את השדה
                st.rerun()
            else:
                st.error("נא להזין כמות")

    # סיכום הזמנה
    if st.session_state.cart:
        st.subheader("📋 סיכום זמני")
        st.table(pd.DataFrame(st.session_state.cart))
        total_order = sum(item["סה''כ"] for item in st.session_state.cart)
        
        sum_col1, sum_col2 = st.columns(2)
        with sum_col1:
            tip_opt = st.radio("בחר אחוז טיפ (נגזר מהסכום)", ["0%", "10%", "15%", "20%"], horizontal=True)
            tip_val = int(total_order * (int(tip_opt[:-1])/100))
            st.metric("סכום סופי לתשלום", f"{total_order:,} ₪")
            st.write(f"מתוכו טיפ למלצרים: **{tip_val:,} ₪**")
        
        with sum_col2:
            if st.session_state.target_budget:
                diff = st.session_state.target_budget - total_order
                if diff < 0:
                    st.markdown(f'<div class="budget-over">חריגה מהתקציב: {abs(diff):,} ₪</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="budget-ok">יתרה בתקציב: {diff:,} ₪</div>', unsafe_allow_html=True)

        # כפתורי פעולה סופיים
        act1, act2 = st.columns(2)
        if act1.button("💾 שמור הזמנה להיסטוריה"):
            items_str = ", ".join([f"{i['מוצר']} x{i['כמות']}" for i in st.session_state.cart])
            c.execute('''INSERT INTO orders (group_name, phone, email, guests, event_date, event_time, items_json, total_price, tip_amount, timestamp) 
                         VALUES (?,?,?,?,?,?,?,?,?,?)''',
                      (st.session_state.g_name, st.session_state.g_phone, st.session_state.g_email, st.session_state.num_guests, 
                       str(st.session_state.order_date), str(st.session_state.order_time), items_str, total_order, tip_val, 
                       datetime.now().strftime("%d/%m/%Y %H:%M")))
            conn.commit()
            st.success("ההזמנה נשמרה בבסיס הנתונים!")

        # הכנת נתונים ל-PDF
        pdf_info = {
            "name": st.session_state.g_name, "phone": st.session_state.g_phone, 
            "email": st.session_state.g_email, "date": str(st.session_state.order_date), 
            "time": str(st.session_state.order_time)
        }
        pdf_file = create_pdf_report(pdf_info, st.session_state.cart, total_order, tip_val)
        act2.download_button("📄 הורד סיכום בפורמט PDF", data=pdf_file, file_name=f"Order_{st.session_state.g_name}.pdf")

# --- 7. דף היסטוריה (כולל טעינה ומחיקה) ---
elif st.session_state.page == "history":
    st.header("📋 היסטוריית הזמנות")
    df_h = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
    
    if df_h.empty:
        st.info("אין הזמנות קודמות להצגה.")
    else:
        for idx, row in df_h.iterrows():
            with st.expander(f"📍 {row['group_name']} | {row['event_date']} | {row['total_price']} ₪"):
                st.write(f"**פרטי קשר:** {row['phone']} | {row['email']}")
                st.write(f"**מנות:** {row['items_json']}")
                st.write(f"**זמן אירוע:** {row['event_time']}")
                
                h_col1, h_col2 = st.columns(2)
                if h_col1.button("🗑️ מחק רשומה", key=f"del_{row['id']}"):
                    c.execute("DELETE FROM orders WHERE id=?", (row['id'],))
                    conn.commit()
                    st.rerun()
                
                if h_col2.button("🔄 טען לעריכה חוזרת", key=f"load_{row['id']}"):
                    st.session_state.g_name = row['group_name']
                    st.session_state.g_phone = row['phone']
                    st.session_state.g_email = row['email']
                    st.session_state.num_guests = row['guests']
                    # פירוק הטקסט חזרה לסל הקניות
                    st.session_state.cart = []
                    for entry in row['items_json'].split(", "):
                        try:
                            p_name, p_qty = entry.split(" x")
                            st.session_state.cart.append({"מוצר": p_name, "כמות": int(p_qty), "מחיר": 0, "סה''כ": 0})
                        except: pass
                    st.session_state.page = "new_order"
                    st.rerun()

# --- 8. דף ניהול תפריט ---
elif st.session_state.page == "menu_mgmt":
    st.header("⚙️ ניהול תפריט המסעדה")
    with st.form("new_dish"):
        c_n = st.text_input("שם המנה")
        c_p = st.number_input("מחיר למנה (₪)", min_value=1, step=1, value=None)
        if st.form_submit_button("הוסף מנה לתפריט"):
            if c_n and c_p:
                c.execute("INSERT INTO menu (item, price) VALUES (?,?)", (c_n, int(c_p)))
                conn.commit()
                st.success(f"המנה '{c_n}' נוספה!")
                st.rerun()
    
    st.subheader("מנות קיימות")
    df_m = pd.read_sql_query("SELECT item as 'שם המנה', price as 'מחיר' FROM menu", conn)
    st.table(df_m)
