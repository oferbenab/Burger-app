import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- הגדרות דף ---
st.set_page_config(page_title="הפסאז' - ניהול יעיל", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Assistant', sans-serif; text-align: right; direction: rtl; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; justify-content: center; }
    input { font-size: 16px !important; }
    /* עיצוב כפתור שמירה ירוק בניהול תפריט */
    .stButton>button[kind="primary"] { background-color: #28a745; color: white; border: none; }
    </style>
    """, unsafe_allow_html=True)

# --- חיבור ל-DB ---
conn = sqlite3.connect('passaz_pro_v7.db', check_same_thread=False)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, price REAL)')
c.execute('CREATE TABLE IF NOT EXISTS orders (name TEXT, details TEXT, total REAL, date TEXT)')
conn.commit()

# --- ניהול זיכרון ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'q_idx' not in st.session_state: st.session_state.q_idx = 0
for k, v in {'nm': "", 'ph': "", 'em': "", 'gs': 1, 'bd': 0}.items():
    if k not in st.session_state: st.session_state[k] = v

tab1, tab2, tab3 = st.tabs(["📝 הזמנה חדשה", "📋 היסטוריה", "⚙️ ניהול תפריט"])

# --- לשונית 1: הזמנה (ללא שינוי לוגי, רק עיצוב רזה) ---
with tab1:
    with st.expander("👤 פרטי לקוח", expanded=False):
        c1, c2 = st.columns(2)
        st.session_state.nm = c1.text_input("שם", value=st.session_state.nm)
        st.session_state.ph = c2.text_input("טלפון", value=st.session_state.ph)
        st.session_state.bd = st.number_input("תקציב (₪)", min_value=0, value=st.session_state.bd)
    
    st.subheader("🛒 סל מנות")
    m_df = pd.read_sql_query("SELECT item, price FROM menu", conn)
    
    if not m_df.empty:
        col_it, col_qty, col_add = st.columns([3, 1, 1])
        sel_item = col_it.selectbox("בחר מנה", m_df['item'].tolist(), label_visibility="collapsed")
        sel_qty = col_qty.number_input("כמות", min_value=1, value=None, key=f"q_{st.session_state.q_idx}", placeholder="?")
        if col_add.button("➕"):
            if sel_qty:
                price = m_df[m_df['item'] == sel_item]['price'].values[0]
                st.session_state.cart.append({"מנה": sel_item, "כמות": int(sel_qty), "מחיר": int(price), "סה''כ": int(sel_qty * price)})
                st.session_state.q_idx += 1
                st.rerun()
    
    if st.session_state.cart:
        st.table(pd.DataFrame(st.session_state.cart))
        subtotal = sum(i["סה''כ"] for i in st.session_state.cart)
        tip_pct = st.radio("טיפ", [0, 10, 15, 20], format_func=lambda x: f"{x}%", horizontal=True)
        total_all = subtotal + int(subtotal * (tip_pct/100))
        st.metric("סה''כ סופי", f"{total_all:,} ₪", delta=f"פער תקציב: {st.session_state.bd - total_all}")
        if st.button("💾 שמור הזמנה"):
            details = ", ".join([f"{i['מנה']} x{i['כמות']}" for i in st.session_state.cart])
            c.execute("INSERT INTO orders VALUES (?,?,?,?)", (st.session_state.nm, details, total_all, datetime.now().strftime("%d/%m/%Y %H:%M")))
            conn.commit()
            st.success("נשמר!")

# --- לשונית 2: היסטוריה ---
with tab2:
    st.dataframe(pd.read_sql_query("SELECT * FROM orders ORDER BY rowid DESC", conn), use_container_width=True)

# --- לשונית 3: ניהול תפריט (התיקון המרכזי) ---
with tab3:
    st.subheader("⚙️ ניהול תפריט מהיר")
    st.write("ניתן לערוך שמות ומחירים ישירות בטבלה, למחוק שורות או להוסיף בתחתית.")
    
    # טעינת התפריט
    menu_query = "SELECT id, item as 'שם המוצר', price as 'מחיר' FROM menu"
    df_menu = pd.read_sql_query(menu_query, conn)
    
    # שימוש ב-Data Editor - מאפשר עריכה, הוספה ומחיקה בשורה אחת
    edited_df = st.data_editor(
        df_menu,
        column_config={
            "id": None, # הסתרת עמודת ה-ID
            "מחיר": st.column_config.NumberColumn("מחיר (₪)", min_value=0, format="%d ₪"),
            "שם המוצר": st.column_config.TextColumn("שם המוצר", required=True),
        },
        num_rows="dynamic", # מאפשר להוסיף ולמחוק שורות
        use_container_width=True,
        key="menu_editor",
        hide_index=True
    )
    
    if st.button("💾 שמור שינויים בתפריט", type="primary"):
        # עדכון בסיס הנתונים: מחיקה וכתיבה מחדש (הדרך הבטוחה ב-Lite)
        c.execute("DELETE FROM menu")
        for _, row in edited_df.iterrows():
            if row['שם המוצר']: # הוספה רק אם יש שם
                c.execute("INSERT INTO menu (item, price) VALUES (?,?)", (row['שם המוצר'], row['מחיר']))
        conn.commit()
        st.success("התפריט עודכן בהצלחה!")
        st.rerun()

    st.info("💡 **טיפ לאייפון:** כדי למחוק שורה, סמן אותה ולחץ על האייקון של פח האשפה בפינת הטבלה. כדי להוסיף, לחץ על ה-'+' בתחתית הטבלה.")
