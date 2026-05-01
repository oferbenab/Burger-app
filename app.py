import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- הגדרות דף ---
st.set_page_config(page_title="הפסאז' - גרסה יציבה", layout="wide")

# עיצוב CSS אגרסיבי כדי למנוע מהאייפון לשבור שורות
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    
    /* מניעת שבירת עמודות במובייל */
    [data-testid="column"] {
        display: inline-block !important;
        min-width: 45% !important;
        flex: 1 1 45% !important;
    }
    
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; height: 3.5em; }
    input { font-size: 16px !important; }
    .budget-status { padding: 15px; border-radius: 10px; text-align: center; font-size: 1.2em; }
    </style>
    """, unsafe_allow_html=True)

# --- אתחול זיכרון (Session State) - לא מוחקים כלום בלי בקשה ---
if 'main_page' not in st.session_state: st.session_state.main_page = "order"
if 'cart' not in st.session_state: st.session_state.cart = []
if 'q_key' not in st.session_state: st.session_state.q_key = 0
if 'tip_pct' not in st.session_state: st.session_state.tip_pct = 0

# שדות לקוח - נשארים מלאים גם אחרי שמירה
for field, default in {'name': "", 'phone': "", 'email': "", 'guests': 1, 'budget': 0}.items():
    if field not in st.session_state: st.session_state[field] = default

# --- חיבור למסד נתונים ---
conn = sqlite3.connect('passaz_stable.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS menu (item TEXT, price REAL)')
c.execute('CREATE TABLE IF NOT EXISTS orders (name TEXT, details TEXT, total REAL, date TEXT)')
conn.commit()

# --- ניווט עליון (שורה אחת) ---
n1, n2, n3 = st.columns(3)
if n1.button("📝 מסך הזמנה"): st.session_state.main_page = "order"
if n2.button("📋 היסטוריה"): st.session_state.main_page = "history"
if n3.button("⚙️ ניהול תפריט"): st.session_state.main_page = "menu"
st.divider()

# --- 1. מסך הזמנה ---
if st.session_state.main_page == "order":
    
    # שורה 1: שם וטלפון
    c1, c2 = st.columns(2)
    st.session_state.name = c1.text_input("שם לקוח / קבוצה", value=st.session_state.name)
    st.session_state.phone = c2.text_input("טלפון", value=st.session_state.phone)
    
    # שורה 2: אימייל
    st.session_state.email = st.text_input("אימייל", value=st.session_state.email)
    
    # שורה 3: סועדים ותקציב
    c3, c4 = st.columns(2)
    st.session_state.guests = c3.number_input("מספר סועדים", min_value=1, value=st.session_state.guests)
    st.session_state.budget = c4.number_input("תקציב יעד (₪)", min_value=0, value=st.session_state.budget)
    
    # שורה 4: בחירת זמן יעילה
    st.write("זמן האירוע:")
    c5, c6, c7 = st.columns([2, 1, 1])
    ev_date = c5.date_input("תאריך", label_visibility="collapsed")
    h = c6.selectbox("שעה", [f"{i:02d}" for i in range(24)], index=20)
    m = c7.selectbox("דקות", [f"{i:02d}" for i in range(0,60,5)], index=0)

    st.divider()

    # --- מחלקת הזמנות (תמיד מופיעה) ---
    st.subheader("🛒 תפריט והזמנה")
    menu_data = pd.read_sql_query("SELECT * FROM menu", conn)
    
    if not menu_data.empty:
        col_it, col_qt, col_btn = st.columns([2, 1, 1])
        selected_item = col_it.selectbox("בחר מנה", menu_data['item'].tolist())
        selected_qty = col_qt.number_input("כמות", min_value=1, value=None, key=f"q_{st.session_state.q_key}", placeholder="?")
        
        if col_btn.button("➕ הוסף"):
            if selected_qty:
                price = menu_data[menu_data['item'] == selected_item]['price'].values[0]
                st.session_state.cart.append({
                    "מנה": selected_item, "כמות": int(selected_qty), 
                    "מחיר": int(price), "סה''כ": int(selected_qty * price)
                })
                st.session_state.q_key += 1
                st.rerun()
    else:
        st.warning("התפריט ריק. הוסף מנות ב'ניהול תפריט'.")

    # סיכום הזמנה וחישובים
    if st.session_state.cart:
        st.write("### פירוט הזמנה")
        st.table(pd.DataFrame(st.session_state.cart))
        
        subtotal = sum(i["סה''כ"] for i in st.session_state.cart)
        
        # פונקציית טיפ
        st.write("**הוספת טיפ:**")
        tip_pct = st.radio("אחוז טיפ", [0, 10, 15, 20], format_func=lambda x: f"{x}%", horizontal=True)
        tip_amount = int(subtotal * (tip_pct / 100))
        total_with_tip = subtotal + tip_amount
        
        # הצגת תקציב ופער
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.metric("סה''כ לפני טיפ", f"{subtotal:,} ₪")
            st.metric("לתשלום סופי (כולל טיפ)", f"{total_with_tip:,} ₪")
            if tip_amount > 0: st.write(f"מרכיב הטיפ: {tip_amount:,} ₪")
            
        with res_col2:
            if st.session_state.budget > 0:
                diff = st.session_state.budget - total_with_tip
                bg_color = "#d4edda" if diff >= 0 else "#f8d7da"
                text_color = "#155724" if diff >= 0 else "#721c24"
                label = "יתרה בתקציב" if diff >= 0 else "חריגה מהתקציב"
                st.markdown(f"""<div class="budget-status" style="background-color:{bg_color}; color:{text_color}; border: 1px solid {text_color};">
                            {label}:<br><span style="font-size:1.5em;">{abs(diff):,} ₪</span></div>""", unsafe_allow_html=True)

        if st.button("💾 שמור הזמנה סופית (הנתונים יישמרו במסך)"):
            summary = ", ".join([f"{i['מנה']} x{i['כמות']}" for i in st.session_state.cart])
            c.execute("INSERT INTO orders VALUES (?,?,?,?)", 
                     (st.session_state.name, summary, total_with_tip, datetime.now().strftime("%d/%m/%Y")))
            conn.commit()
            st.success("ההזמנה נשמרה בבסיס הנתונים!")

# --- 2. ניהול תפריט ---
elif st.session_state.main_page == "menu":
    st.header("⚙️ ניהול תפריט")
    with st.form("dish_form"):
        new_name = st.text_input("שם המנה")
        new_price = st.number_input("מחיר", min_value=1)
        if st.form_submit_button("הוסף לתפריט"):
            if new_name:
                c.execute("INSERT INTO menu VALUES (?,?)", (new_name, new_price))
                conn.commit()
                st.rerun()
    st.subheader("תפריט קיים")
    st.table(pd.read_sql_query("SELECT * FROM menu", conn))

# --- 3. היסטוריה ---
elif st.session_state.main_page == "history":
    st.header("📋 היסטוריית הזמנות")
    st.dataframe(pd.read_sql_query("SELECT * FROM orders ORDER BY rowid DESC", conn), use_container_width=True)
