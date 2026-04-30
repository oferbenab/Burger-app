import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- הגדרות דף ---
st.set_page_config(page_title="הפסאז' - ניהול אירועים", layout="wide", initial_sidebar_state="collapsed")

# --- עיצוב CSS מותאם (RTL, צבעים וכפתורים) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; font-weight: bold; }
    .status-approved { color: #28a745; font-weight: bold; }
    .status-pending { color: #fd7e14; font-weight: bold; }
    .status-cancelled { color: #dc3545; font-weight: bold; }
    .budget-over { color: #dc3545; font-weight: bold; font-size: 1.2em; }
    .budget-ok { color: #28a745; font-weight: bold; font-size: 1.2em; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; }
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

# --- פונקציות עזר ---
def get_menu():
    conn = sqlite3.connect('passaz_pro.db')
    df = pd.read_sql_query("SELECT * FROM menu", conn)
    conn.close()
    return df

# --- Header: לוגו וניווט ---
col_logo, col_empty = st.columns([1, 4])
with col_logo:
    st.markdown("### 🍔 לוגו")
    st.markdown("<h2 style='margin-top: -20px;'>הפסאז'</h2>", unsafe_allow_html=True)

st.divider()

# שורת כפתורי ניווט
nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)
with nav_col1:
    if st.button("📝 הזמנה חדשה"): st.session_state.page = "new_order"
with nav_col2:
    if st.button("📋 היסטוריה"): st.session_state.page = "history"
with nav_col3:
    if st.button("⚙️ תפריט"): st.session_state.page = "menu_mgmt"
with nav_col4:
    if st.button("📥 ייצוא"): st.session_state.page = "export"

if 'page' not in st.session_state:
    st.session_state.page = "new_order"

# --- עמוד: ניהול תפריט ---
if st.session_state.page == "menu_mgmt":
    st.header("⚙️ ניהול תפריט קבוע")
    with st.expander("הוספת מוצר חדש", expanded=True):
        col_n, col_p = st.columns(2)
        new_name = col_n.text_input("שם המוצר")
        new_price = col_p.number_input("מחיר ליחידה", min_value=0.0)
        if st.button("שמור בתפריט"):
            conn = sqlite3.connect('passaz_pro.db')
            conn.cursor().execute("INSERT INTO menu (item, price) VALUES (?, ?)", (new_name, new_price))
            conn.commit()
            conn.close()
            st.success("המוצר נוסף!")
            st.rerun()

    df_m = get_menu()
    st.table(df_m)
    if not df_m.empty:
        to_delete = st.selectbox("בחר מוצר להסרה", df_m['item'].tolist())
        if st.button("מחק מוצר נבחר"):
            conn = sqlite3.connect('passaz_pro.db')
            conn.cursor().execute("DELETE FROM menu WHERE item=?", (to_delete,))
            conn.commit()
            conn.close()
            st.rerun()

# --- עמוד: הזמנה חדשה ---
elif st.session_state.page == "new_order":
    st.header("📝 יצירת הזמנה לקבוצה")
    
    # 1. פרטי קבוצה
    col1, col2 = st.columns(2)
    with col1:
        g_name = st.text_input("שם הקבוצה")
        email = st.text_input("אימייל")
        guests = st.number_input("מספר סועדים", min_value=1, value=1)
    with col2:
        total_budget = st.number_input("תקציב כללי (₪)", min_value=0.0)
        budget_per_guest = st.number_input("תקציב לסועד (₪)", min_value=0.0)
        status = st.selectbox("סטטוס אירוע", ["בהמתנה", "מאושר", "בוטל"])

    st.divider()

    # 2. פירוט הזמנה (בחירת מנות)
    if 'current_order' not in st.session_state:
        st.session_state.current_order = []

    st.subheader("🛒 הוספת מנות")
    df_menu = get_menu()
    if not df_menu.empty:
        col_item, col_qty, col_add = st.columns([3, 1, 1])
        item_to_add = col_item.selectbox("בחר מנה", df_menu['item'].tolist())
        qty_to_add = col_qty.number_input("כמות", min_value=1, value=1)
        if col_add.button("הוסף להזמנה", use_container_width=True):
            price = df_menu[df_menu['item'] == item_to_add]['price'].values[0]
            st.session_state.current_order.append({
                "מוצר": item_to_add, "כמות": qty_to_add, "מחיר": price, "סה''כ": qty_to_add * price
            })

    # תצוגת ההזמנה הנוכחית
    if st.session_state.current_order:
        df_order = pd.DataFrame(st.session_state.current_order)
        st.table(df_order)
        
        subtotal = df_order["סה''כ"].sum()
        
        # 3. טיפ
        st.subheader("💰 טיפ וסיכום")
        tip_pct = st.radio("בחר אחוז טיפ", [0, 10, 15, 20], horizontal=True)
        tip_val = subtotal * (tip_pct / 100)
        st.write(f"סכום הטיפ: **{tip_val:.2f} ₪**")
        
        final_total = subtotal + tip_val
        st.metric("סה''כ הזמנה (כולל טיפ)", f"{final_total:.2f} ₪")

        # 4. מעקב תקציב
        active_budget = total_budget if total_budget > 0 else (budget_per_guest * guests)
        if active_budget > 0:
            diff = active_budget - final_total
            if diff < 0:
                st.markdown(f"<p class='budget-over'>חריגה מהתקציב: {abs(diff):.2f} ₪-</p>", unsafe_allow_html=True)
            else:
                st.markdown(f<p class='budget-ok'>נותרו בתקציב: {diff:.2f} ₪+</p>", unsafe_allow_html=True)

        pay_method = st.selectbox("שיטת תשלום", ["טרם שולם", "אשראי", "שוטף 30"])

        if st.button("💾 שמור הזמנה סופית", use_container_width=True):
            conn = sqlite3.connect('passaz_pro.db')
            c = conn.cursor()
            now = datetime.now().strftime("%d/%m/%Y %H:%M")
            c.execute('''INSERT INTO orders 
                         (group_name, email, total_budget, budget_per_guest, guests, 
                          items_json, total_price, tip_amount, payment_method, status, timestamp) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (g_name, email, total_budget, budget_per_guest, guests, 
                       str(st.session_state.current_order), final_total, tip_val, pay_method, status, now))
            conn.commit()
            conn.close()
            st.session_state.current_order = []
            st.success("ההזמנה נשמרה בהצלחה!")
            st.rerun()

# --- עמודים אחרים (היסטוריה וייצוא) ---
elif st.session_state.page == "history":
    st.header("📋 היסטוריית הזמנות")
    conn = sqlite3.connect('passaz_pro.db')
    df_h = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
    conn.close()
    st.dataframe(df_h, use_container_width=True)

elif st.session_state.page == "export":
    st.header("📥 ייצוא נתונים")
    conn = sqlite3.connect('passaz_pro.db')
    df_exp = pd.read_sql_query("SELECT * FROM orders", conn)
    conn.close()
    csv = df_exp.to_csv(index=False).encode('utf-8-sig')
    st.download_button("הורד דוח ריכוז נתונים", data=csv, file_name="Passaz_Report.csv", mime="text/csv")
