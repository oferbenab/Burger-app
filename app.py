import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# הגדרת דף
st.set_page_config(page_title="בורגר-קונטרול", layout="centered")

# פונקציות בסיס נתונים
def init_db():
    conn = sqlite3.connect('burger_orders.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS menu (id INTEGER PRIMARY KEY, item TEXT, price REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS orders (group_name TEXT, items TEXT, total REAL, date TEXT)')
    
    c.execute("SELECT count(*) FROM menu")
    if c.fetchone()[0] == 0:
        products = [("המבורגר קלאסי", 55), ("צ'יפס גדול", 20), ("קולה", 12), ("המבורגר טבעוני", 58)]
        c.executemany("INSERT INTO menu (item, price) VALUES (?, ?)", products)
    conn.commit()
    conn.close()

init_db()

st.title("🍔 מערכת הזמנות המבורגר")

# תפריט צד (Sidebar) לניהול
menu_action = st.sidebar.selectbox("תפריט ניהול", ["הזמנה חדשה", "צפייה בהזמנות", "ניהול תפריט"])

conn = sqlite3.connect('burger_orders.db')

if menu_action == "הזמנה חדשה":
    st.subheader("יצירת הזמנה לקבוצה")
    
    group_name = st.text_input("שם הקבוצה / לקוח")
    
    # שליפת התפריט
    df_menu = pd.read_sql_query("SELECT * FROM menu", conn)
    items_list = df_menu['item'].tolist()
    
    # בחירה מרובה של מוצרים
    selected_items = st.multiselect("בחר מוצרים מהתפריט", items_list)
    
    order_details = []
    total_price = 0
    
    if selected_items:
        st.write("---")
        for item in selected_items:
            price = df_menu[df_menu['item'] == item]['price'].values[0]
            qty = st.number_input(f"כמות עבור {item} (מחיר: {price}₪)", min_value=1, value=1, key=item)
            subtotal = price * qty
            total_price += subtotal
            order_details.append(f"{item} ({qty})")
        
        st.write("---")
        st.metric("סה''כ לתשלום", f"{total_price} ₪")
        
        if st.button("אישור ושמירת הזמנה"):
            if group_name:
                items_str = ", ".join(order_details)
                date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                c = conn.cursor()
                c.execute("INSERT INTO orders (group_name, items, total, date) VALUES (?, ?, ?, ?)",
                          (group_name, items_str, total_price, date_str))
                conn.commit()
                st.success(f"ההזמנה של {group_name} נשמרה!")
            else:
                st.error("נא להזין שם קבוצה")

elif menu_action == "צפייה בהזמנות":
    st.subheader("היסטוריית הזמנות")
    df_orders = pd.read_sql_query("SELECT * FROM orders", conn)
    st.dataframe(df_orders, use_container_width=True)
    
    if not df_orders.empty:
        # כפתור ייצוא לאקסל ישירות מהדפדפן
        csv = df_orders.to_csv(index=False).encode('utf-8-sig')
        st.download_button("הורד דוח (CSV)", data=csv, file_name="burger_report.csv", mime="text/csv")

elif menu_action == "ניהול תפריט":
    st.subheader("הוספת מוצר לתפריט")
    new_item = st.text_input("שם המוצר")
    new_price = st.number_input("מחיר", min_value=0.0)
    if st.button("הוסף לתפריט"):
        c = conn.cursor()
        c.execute("INSERT INTO menu (item, price) VALUES (?, ?)", (new_item, new_price))
        conn.commit()
        st.success(f"המוצר {new_item} נוסף בהצלחה")

conn.close()
