import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io

# --- הגדרות דף ---
st.set_page_config(page_title="הפסאז' - ניהול אירועים", layout="wide")

# --- CSS עיצוב ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; }
    .budget-over { color: #dc3545; font-weight: bold; border: 1px solid #dc3545; padding: 10px; border-radius: 8px; text-align: center; background: #fff5f5; }
    .budget-ok { color: #28a745; font-weight: bold; border: 1px solid #28a745; padding: 10px; border-radius: 8px; text-align: center; background: #f6fff6; }
    /* סידור כפתורי ניווט בשורה */
    .nav-col { display: flex; gap: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- אתחול משתנים (Session State) ---
if 'page' not in st.session_state: st.session_state.page = "new_order"
if 'cart' not in st.session_state: st.session_state.cart = []
if 'last_selected_item' not in st.session_state: st.session_state.last_selected_item = None
if 'edit_data' not in st.session_state: st.session_state.edit_data = {}

# פונקציית איפוס לקוח חדש
def reset_for_new_client():
    keys_to_keep = ['page', 'last_selected_item']
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            del st.session_state[key]
    st.session_state.cart = []
    st.session_state.edit_data = {}
    st.rerun()

# --- חיבור ל-DB ---
conn = sqlite3.connect('passaz_pro.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY, item TEXT, price REAL)')
c.execute('''CREATE TABLE IF NOT EXISTS orders 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, group_name TEXT, guests INTEGER, 
              event_date TEXT, event_time TEXT, items_json TEXT, total_price INTEGER, timestamp TEXT)''')
conn.commit()

# --- ניווט עליון (כפתורים אחד לצד השני) ---
nav_col1, nav_col2, nav_col3 = st.columns(3)
with nav_col1: 
    if st.button("📝 הזמנה חדשה"): st.session_state.page = "new_order"
with nav_col2: 
    if st.button("📋 היסטוריה"): st.session_state.page = "history"
with nav_col3: 
    if st.button("⚙️ תפריט"): st.session_state.page = "menu_mgmt"

st.divider()

# --- עמוד: הזמנה חדשה ---
if st.session_state.page == "new_order":
    col_h1, col_h2 = st.columns([4, 1])
    col_h1.header("פרטי הזמנה")
    if col_h2.button("✨ לקוח חדש", type="primary"): reset_for_new_client()

    # פרטי לקוח
    c1, c2, c3 = st.columns(3)
    # טעינת נתונים אם אנחנו ב"טעינה מחדש"
    default_name = st.session_state.edit_data.get('group_name', "")
    default_guests = st.session_state.edit_data.get('guests', None)
    
    g_name = c1.text_input("שם הקבוצה", key="g_name_input", value=default_name)
    num_guests = c2.number_input("מספר סועדים", min_value=1, step=1, value=default_guests, placeholder="הכנס כמות...")
    target_budget = c3.number_input("תקציב יעד (₪)", min_value=1, step=1, value=None, placeholder="הכנס תקציב...")

    c_date, c_time, c_empty = st.columns(3)
    order_date = c_date.date_input("תאריך הזמנה", value=datetime.now())
    order_time = c_time.time_input("שעת הזמנה", value=datetime.now())

    st.divider()

    # בחירת מנות
    df_menu = pd.read_sql_query("SELECT * FROM menu", conn)
    if not df_menu.empty:
        st.subheader("🛒 הוספת פריטים")
        ci, cq, ca = st.columns([3, 1, 1])
        
        menu_list = df_menu['item'].tolist()
        default_idx = menu_list.index(st.session_state.last_selected_item) if st.session_state.last_selected_item in menu_list else 0
        
        sel_item = ci.selectbox("בחר מנה", menu_list, index=default_idx)
        # כמות מתאפסת (value=None)
        sel_qty = cq.number_input("כמות", min_value=1, step=1, value=None, key="qty_input", placeholder="?")
        
        if ca.button("➕ הוסף", use_container_width=True):
            if sel_qty:
                price = df_menu[df_menu['item'] == sel_item]['price'].values[0]
                st.session_state.cart.append({
                    "מוצר": sel_item, "כמות": int(sel_qty), "מחיר": int(price), "סה''כ": int(sel_qty * price)
                })
                st.session_state.last_selected_item = sel_item
                st.rerun()
            else: st.error("נא להזין כמות")

    # סיכום
    if st.session_state.cart:
        st.table(pd.DataFrame(st.session_state.cart))
        total_price = sum(item["סה''כ"] for item in st.session_state.cart)
        
        st.divider()
        col_res1, col_res2 = st.columns(2)
        
        with col_res1:
            t_choice = st.radio("בחר אחוז טיפ (מתוך הסכום)", ["0%", "10%", "15%", "20%"], horizontal=True)
            t_pct = int(t_choice.replace("%",""))
            tip_val = int(total_price * (t_pct / 100))
            
            st.metric("סכום סופי (₪)", f"{total_price:,}")
            st.write(f"מתוכו טיפ: **{tip_val:,} ₪**")

        with col_res2:
            if target_budget:
                diff = target_budget - total_price
                if diff < 0: st.markdown(f'<div class="budget-over">חריגה: {abs(diff):,} ₪</div>', unsafe_allow_html=True)
                else: st.markdown(f'<div class="budget-ok">יתרה: {diff:,} ₪</div>', unsafe_allow_html=True)

        # כפתורי פעולה סופיים
        btn1, btn2 = st.columns(2)
        if btn1.button("💾 שמור להיסטוריה", use_container_width=True):
            now_ts = datetime.now().strftime("%d/%m/%Y %H:%M")
            items_str = ", ".join([f"{i['מוצר']} x{i['כמות']}" for i in st.session_state.cart])
            c.execute("INSERT INTO orders (group_name, guests, event_date, event_time, items_json, total_price, timestamp) VALUES (?,?,?,?,?,?,?)",
                      (g_name, num_guests, str(order_date), str(order_time), items_str, total_price, now_ts))
            conn.commit()
            st.success("נשמר!")

        # כפתור PDF (בסיסי)
        if btn2.button("📄 ייצוא לסיכום PDF", use_container_width=True):
            st.info("הפונקציה מייצרת קובץ להורדה - וודא שמותקנת ספריית fpdf")
            # כאן ניתן להטמיע לוגיקה של fpdf

# --- עמוד: היסטוריה ---
elif st.session_state.page == "history":
    st.header("📋 היסטוריה")
    df_h = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
    if not df_h.empty:
        for idx, row in df_h.iterrows():
            with st.expander(f"{row['group_name']} | {row['event_date']} | {row['total_price']} ₪"):
                st.write(f"**פרטים:** {row['items_json']}")
                st.write(f"**זמן אירוע:** {row['event_time']}")
                
                hc1, hc2, hc3 = st.columns(3)
                if hc1.button("🗑️ מחק", key=f"del_{row['id']}"):
                    c.execute("DELETE FROM orders WHERE id=?", (row['id'],))
                    conn.commit()
                    st.rerun()
                
                if hc2.button("🔄 טען להזמנה", key=f"load_{row['id']}"):
                    st.session_state.edit_data = {
                        'group_name': row['group_name'],
                        'guests': row['guests']
                    }
                    # הערה: טעינת הסל דורשת פירוק של ה-string השמור או שמירה בפורמט JSON
                    st.session_state.page = "new_order"
                    st.rerun()
    else: st.info("ההיסטוריה ריקה")

# --- עמוד: תפריט ---
elif st.session_state.page == "menu_mgmt":
    st.header("⚙️ ניהול תפריט")
    with st.form("add_item"):
        c1, c2 = st.columns(2)
        n = c1.text_input("שם המנה")
        p = c2.number_input("מחיר (₪)", min_value=1, step=1, value=None)
        if st.form_submit_button("הוסף"):
            if n and p:
                c.execute("INSERT INTO menu (item, price) VALUES (?,?)", (n, int(p)))
                conn.commit()
                st.rerun()
    
    df_m = pd.read_sql_query("SELECT * FROM menu", conn)
    st.table(df_m[['item', 'price']])
