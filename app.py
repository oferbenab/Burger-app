import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- הגדרות דף ---
st.set_page_config(page_title="הפסאז' - ניהול אירועים", layout="wide", initial_sidebar_state="collapsed")

# --- עיצוב CSS מותאם (RTL, צבעים ומובייל) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; font-weight: bold; }
    
    /* עיצוב חיווי תקציב */
    .budget-over { 
        color: #dc3545; font-weight: bold; font-size: 1.1em; 
        border: 2px solid #dc3545; padding: 10px; border-radius: 8px; background-color: #fff5f5; 
        text-align: center; margin: 10px 0;
    }
    .budget-ok { 
        color: #28a745; font-weight: bold; font-size: 1.1em; 
        border: 2px solid #28a745; padding: 10px; border-radius: 8px; background-color: #f6fff6; 
        text-align: center; margin: 10px 0;
    }
    
    div[data-testid="stMetricValue"] { font-size: 1.6rem; text-align: right; }
    .stDataFrame, .stTable { direction: rtl; text-align: right; }
    </style>
    """, unsafe_allow_html=True)

# --- ניהול בסיס נתונים ---
def init_db():
    conn = sqlite3.connect('passaz_pro.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY, item TEXT, price REAL)')
    c.execute('''CREATE TABLE IF NOT EXISTS orders 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, group_name TEXT, email TEXT, 
                  total_budget REAL, budget_per_guest REAL, guests INTEGER,
                  items_json TEXT, total_price REAL, tip_amount REAL, 
                  payment_method TEXT, status TEXT, timestamp TEXT)''')
    conn.commit()
    conn.close()

init_db()

def get_menu():
    conn = sqlite3.connect('passaz_pro.db')
    df = pd.read_sql_query("SELECT * FROM menu", conn)
    conn.close()
    return df

# --- Header: לוגו וניווט ---
col_l, col_r = st.columns([1, 4])
with col_l:
    st.markdown("### 🍔")
    st.markdown("<h2 style='margin-top: -20px;'>הפסאז'</h2>", unsafe_allow_html=True)

st.divider()

# יצירת כפתורי ניווט בשורה אחת
n1, n2, n3, n4 = st.columns(4)
if 'page' not in st.session_state: st.session_state.page = "new_order"

with n1:
    if st.button("📝 הזמנה"): st.session_state.page = "new_order"
with n2:
    if st.button("📋 היסטוריה"): st.session_state.page = "history"
with n3:
    if st.button("⚙️ תפריט"): st.session_state.page = "menu_mgmt"
with n4:
    if st.button("📥 ייצוא"): st.session_state.page = "export"

# --- עמוד: ניהול תפריט ---
if st.session_state.page == "menu_mgmt":
    st.header("⚙️ ניהול תפריט קבוע")
    with st.form("menu_form"):
        st.subheader("הוספה או עדכון מנה")
        c1, c2 = st.columns(2)
        name = c1.text_input("שם המנה")
        prc = c2.number_input("מחיר (₪)", min_value=0.0, step=1.0)
        if st.form_submit_button("שמור בתפריט"):
            if name:
                conn = sqlite3.connect('passaz_pro.db')
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM menu WHERE item=?", (name,))
                if cursor.fetchone():
                    cursor.execute("UPDATE menu SET price=? WHERE item=?", (prc, name))
                else:
                    cursor.execute("INSERT INTO menu (item, price) VALUES (?, ?)", (name, prc))
                conn.commit()
                conn.close()
                st.success(f"המוצר {name} נשמר!")
                st.rerun()
            else: st.error("חובה להזין שם מוצר")

    df_m = get_menu()
    if not df_m.empty:
        st.divider()
        st.subheader("מנות קיימות")
        st.dataframe(df_m[['item', 'price']], use_container_width=True, hide_index=True)
        del_item = st.selectbox("בחר מנה למחיקה", df_m['item'].tolist())
        if st.button("🗑️ מחק מנה נבחרת"):
            conn = sqlite3.connect('passaz_pro.db')
            conn.cursor().execute("DELETE FROM menu WHERE item=?", (del_item,))
            conn.commit()
            conn.close()
            st.rerun()

# --- עמוד: הזמנה חדשה ---
elif st.session_state.page == "new_order":
    st.header("📝 הזמנה לקבוצה")
    
    col_a, col_b = st.columns(2)
    with col_a:
        g_name = st.text_input("שם הקבוצה")
        mail = st.text_input("אימייל")
        num_guests = st.number_input("מספר סועדים", min_value=1, value=1)
    with col_b:
        b_type = st.radio("סוג תקציב", ["כללי", "פר סועד"], horizontal=True)
        if b_type == "כללי":
            t_budget = st.number_input("תקציב כולל (₪)", min_value=0.0)
            p_guest_budget = 0.0
        else:
            p_guest_budget = st.number_input("תקציב לסועד (₪)", min_value=0.0)
            t_budget = 0.0
        st_val = st.selectbox("סטטוס אירוע", ["בהמתנה", "מאושר", "בוטל"])

    st.divider()

    if 'cart' not in st.session_state: st.session_state.cart = []
    
    df_menu = get_menu()
    if not df_menu.empty:
        st.subheader("🛒 הוספת מנות")
        ci, cq, ca = st.columns([3,1,1])
        sel_item = ci.selectbox("בחירת מנה מהתפריט", df_menu['item'].tolist())
        sel_qty = cq.number_input("כמות", min_value=1, value=1)
        if ca.button("➕ הוסף", use_container_width=True):
            p = df_menu[df_menu['item'] == sel_item]['price'].values[0]
            st.session_state.cart.append({"מוצר": sel_item, "כמות": sel_qty, "מחיר": p, "סה''כ": p * sel_qty})

    if st.session_state.cart:
        st.table(pd.DataFrame(st.session_state.cart))
        if st.button("🗑️ נקה הכל"): 
            st.session_state.cart = []; st.rerun()
            
        sub = sum(item["סה''כ"] for item in st.session_state.cart)
        
        st.divider()
        st.subheader("💰 סיכום ותקציב")
        t_choice = st.radio("בחר טיפ", ["0%", "10%", "15%", "20%"], horizontal=True)
        t_pct = int(t_choice.replace("%",""))
        t_val = sub * (t_pct / 100)
        final = sub + t_val
        
        col_s1, col_s2 = st.columns(2)
        col_s1.metric("סה''כ מנות", f"{sub:,.2f} ₪")
        col_s1.write(f"סכום הטיפ ({t_choice}): **{t_val:,.2f} ₪**")
        col_s2.metric("סה''כ לתשלום", f"{final:,.2f} ₪")

        # חישוב תקציב
        target = t_budget if b_type == "כללי" else (p_guest_budget * num_guests)
        if target > 0:
            diff = target - final
            if diff < 0:
                st.markdown(f'<div class="budget-over">חריגה מהתקציב: {abs(diff):,.2f} ₪-</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="budget-ok">יתרה בתקציב: {diff:,.2f} ₪+</div>', unsafe_allow_html=True)
        
        pay = st.selectbox("שיטת תשלום", ["טרם שולם", "אשראי", "שוטף 30"])

        if st.button("💾 שמור הזמנה סופית", use_container_width=True):
            if g_name:
                conn = sqlite3.connect('passaz_pro.db')
                c = conn.cursor()
                its = ", ".join([f"{i['מוצר']} (x{i['כמות']})" for i in st.session_state.cart])
                c.execute('''INSERT INTO orders 
                    (group_name, email, total_budget, budget_per_guest, guests, 
                    items_json, total_price, tip_amount, payment_method, status, timestamp) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (g_name, mail, t_budget, p_guest_budget, num_guests, its, final, t_val, pay, st_val, datetime.now().strftime("%d/%m/%Y %H:%M")))
                conn.commit(); conn.close()
                st.session_state.cart = []
                st.success("ההזמנה נשמרה!"); st.rerun()
            else: st.error("חובה להזין שם קבוצה")

# --- עמוד: היסטוריה ---
elif st.session_state.page == "history":
    st.header("📋 היסטוריית הזמנות")
    conn = sqlite3.connect('passaz_pro.db')
    df_h = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
    conn.close()
    if not df_h.empty:
        q = st.text_input("🔍 חיפוש קבוצה")
        if q: df_h = df_h[df_h['group_name'].str.contains(q, na=False)]
        st.dataframe(df_h, use_container_width=True, hide_index=True)
    else: st.info("אין עדיין הזמנות במערכת")

# --- עמוד: ייצוא ---
elif st.session_state.page == "export":
    st.header("📥 ייצוא נתונים")
    conn = sqlite3.connect('passaz_pro.db')
    df_e = pd.read_sql_query("SELECT * FROM orders", conn)
    conn.close()
    if not df_e.empty:
        csv = df_e.to_csv(index=False).encode('utf-8-sig')
        st.download_button("הורד קובץ ריכוז נתונים (CSV)", csv, "Passaz_Report.csv", "text/csv")
    else: st.warning("אין נתונים לייצוא")
