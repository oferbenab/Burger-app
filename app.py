import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- הגדרות דף ---
st.set_page_config(page_title="הפסאז' - ניהול אירועים", layout="wide")

# --- עיצוב CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; }
    .budget-over { color: #dc3545; font-weight: bold; border: 1px solid #dc3545; padding: 10px; border-radius: 8px; text-align: center; background: #fff5f5; }
    .budget-ok { color: #28a745; font-weight: bold; border: 1px solid #28a745; padding: 10px; border-radius: 8px; text-align: center; background: #f6fff6; }
    </style>
    """, unsafe_allow_html=True)

# --- אתחול משתנים (Session State) ---
if 'page' not in st.session_state: st.session_state.page = "new_order"
if 'cart' not in st.session_state: st.session_state.cart = []
if 'last_selected_item' not in st.session_state: st.session_state.last_selected_item = None

# פונקציית איפוס גלובלית
def reset_all():
    for key in st.session_state.keys():
        if key != 'page': del st.session_state[key]
    st.session_state.cart = []
    st.session_state.last_selected_item = None
    st.rerun()

# --- חיבור ל-DB ---
conn = sqlite3.connect('passaz_pro.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY, item TEXT, price REAL)')
c.execute('''CREATE TABLE IF NOT EXISTS orders 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, group_name TEXT, guests INTEGER, 
              items_json TEXT, total_price INTEGER, timestamp TEXT)''')
conn.commit()

# --- ניווט עליון ---
n1, n2, n3 = st.columns(3)
with n1: 
    if st.button("📝 הזמנה חדשה"): st.session_state.page = "new_order"
with n2: 
    if st.button("📋 היסטוריה"): st.session_state.page = "history"
with n3: 
    if st.button("⚙️ תפריט"): st.session_state.page = "menu_mgmt"

st.divider()

# --- עמוד: הזמנה חדשה ---
if st.session_state.page == "new_order":
    col_h1, col_h2 = st.columns([4, 1])
    col_h1.header("פרטי הזמנה")
    if col_h2.button("✨ לקוח חדש", type="primary"): reset_all()

    # שדות פרטי לקוח - הכל מתחיל ריק
    c1, c2, c3 = st.columns(3)
    g_name = c1.text_input("שם הקבוצה", key="g_name_input", value=st.session_state.get('g_name', ""))
    st.session_state['g_name'] = g_name
    
    # שימוש ב-value=None כדי שהשדה יתחיל ריק ללא 0
    num_guests = c2.number_input("מספר סועדים", min_value=1, step=1, value=st.session_state.get('num_guests'), placeholder="הכנס כמות...")
    st.session_state['num_guests'] = num_guests
    
    target_budget = c3.number_input("תקציב יעד (₪)", min_value=1, step=1, value=st.session_state.get('target_budget'), placeholder="הכנס תקציב...")
    st.session_state['target_budget'] = target_budget

    st.divider()

    # בחירת מנות מהתפריט
    df_menu = pd.read_sql_query("SELECT * FROM menu", conn)
    if not df_menu.empty:
        st.subheader("🛒 הוספת פריטים")
        ci, cq, ca = st.columns([3, 1, 1])
        
        # זוכר את הפריט האחרון שנבחר
        menu_list = df_menu['item'].tolist()
        default_idx = menu_list.index(st.session_state.last_selected_item) if st.session_state.last_selected_item in menu_list else 0
        
        sel_item = ci.selectbox("בחר מנה", menu_list, index=default_idx)
        
        # כמות מתחילה ריקה בכל פעם
        sel_qty = cq.number_input("כמות", min_value=1, step=1, value=None, key="qty_input", placeholder="?")
        
        if ca.button("➕ הוסף", use_container_width=True):
            if sel_qty:
                price = df_menu[df_menu['item'] == sel_item]['price'].values[0]
                st.session_state.cart.append({
                    "מוצר": sel_item, 
                    "כמות": int(sel_qty), 
                    "מחיר": int(price), 
                    "סה''כ": int(sel_qty * price)
                })
                # שמירת הפריט האחרון ואיפוס הכמות (האיפוס קורה בגלל ה-value=None וה-key)
                st.session_state.last_selected_item = sel_item
                st.rerun()
            else:
                st.error("נא להזין כמות")

    # הצגת הטבלה והסיכומים
    if st.session_state.cart:
        st.table(pd.DataFrame(st.session_state.cart))
        total_price = sum(item["סה''כ"] for item in st.session_state.cart)
        
        st.divider()
        col_res1, col_res2 = st.columns(2)
        
        with col_res1:
            t_choice = st.radio("בחר אחוז טיפ (נגזר מהסכום)", ["0%", "10%", "15%", "20%"], horizontal=True)
            t_pct = int(t_choice.replace("%",""))
            tip_val = int(total_price * (t_pct / 100))
            
            st.metric("סכום סופי (₪)", f"{total_price:,}")
            st.write(f"מתוכו טיפ: **{tip_val:,} ₪**")
            st.write(f"נטו מסעדה: **{total_price - tip_val:,} ₪**")

        with col_res2:
            if st.session_state.get('target_budget'):
                diff = st.session_state['target_budget'] - total_price
                if diff < 0:
                    st.markdown(f'<div class="budget-over">חריגה: {abs(diff):,} ₪</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="budget-ok">יתרה בתקציב: {diff:,} ₪</div>', unsafe_allow_html=True)

        if st.button("💾 שמור הזמנה להיסטוריה", use_container_width=True):
            now = datetime.now().strftime("%d/%m/%Y %H:%M")
            items_str = ", ".join([f"{i['מוצר']} x{i['כמות']}" for i in st.session_state.cart])
            c.execute("INSERT INTO orders (group_name, guests, items_json, total_price, timestamp) VALUES (?,?,?,?,?)",
                      (st.session_state['g_name'], st.session_state['num_guests'], items_str, total_price, now))
            conn.commit()
            st.success("ההזמנה נשמרה בהצלחה!")

# --- עמוד: היסטוריה ---
elif st.session_state.page == "history":
    st.header("📋 היסטוריית הזמנות")
    df_h = pd.read_sql_query("SELECT * FROM orders ORDER BY id DESC", conn)
    if not df_h.empty:
        # הצגת מספרים שלמים בטבלה
        df_h['total_price'] = df_h['total_price'].astype(int)
        st.dataframe(df_h, use_container_width=True, hide_index=True)
        
        if st.button("🗑️ נקה היסטוריה (זהירות!)"):
            c.execute("DELETE FROM orders")
            conn.commit()
            st.rerun()
    else:
        st.info("אין הזמנות רשומות")

# --- עמוד: תפריט ---
elif st.session_state.page == "menu_mgmt":
    st.header("⚙️ ניהול תפריט")
    with st.form("add_item"):
        c1, c2 = st.columns(2)
        n = c1.text_input("שם המנה")
        p = c2.number_input("מחיר (₪)", min_value=1, step=1, value=None)
        if st.form_submit_button("הוסף לתפריט"):
            if n and p:
                c.execute("INSERT INTO menu (item, price) VALUES (?,?)", (n, int(p)))
                conn.commit()
                st.rerun()
    
    df_m = pd.read_sql_query("SELECT * FROM menu", conn)
    st.table(df_m[['item', 'price']])
