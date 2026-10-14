import os
import pandas as pd
import streamlit as st
import psycopg2
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()
st.set_page_config(page_title="UMKM SmartStock", page_icon="📦", layout="wide")
st.title("📦 UMKM SmartStock")
st.caption("Dashboard monitoring penjualan dan stok — data simulasi untuk demonstrasi capstone.")

def get_pg_connection():
    return psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=os.getenv("PG_PORT", "5432"),
        dbname=os.getenv("PG_DATABASE", "smartstock"),
        user=os.getenv("PG_USER", "postgres"),
        password=os.getenv("PG_PASSWORD", "")
    )

if st.button("🔄 Refresh data"):
    st.cache_data.clear()

@st.cache_data(ttl=30)
def load_data():
    with get_pg_connection() as conn:
        sales = pd.read_sql_query("""
            SELECT s.transaction_id, s.transaction_date, p.product_name, p.category,
                   s.quantity, s.unit_price, s.total_amount, s.payment_method
            FROM sales s JOIN products p ON p.product_id=s.product_id
            ORDER BY s.transaction_date
        """, conn)
        products = pd.read_sql_query("""
            SELECT product_id, product_name, category, unit_price, stock_qty
            FROM products ORDER BY product_name
        """, conn)
    return sales, products

try:
    sales, products = load_data()
except Exception as e:
    st.error("Belum dapat terhubung ke PostgreSQL. Pastikan database, schema, dan file .env sudah benar.")
    st.code(str(e))
    st.stop()

if sales.empty:
    st.info("Belum ada data penjualan. Jalankan `python etl.py` terlebih dahulu.")
    st.stop()

sales["transaction_date"] = pd.to_datetime(sales["transaction_date"])
total_sales = float(sales["total_amount"].sum())
total_transactions = int(sales["transaction_id"].nunique())
units_sold = int(sales["quantity"].sum())
low_stock = int((products["stock_qty"] <= 10).sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Penjualan", f"Rp {total_sales:,.0f}")
c2.metric("Jumlah Transaksi", f"{total_transactions:,}")
c3.metric("Unit Terjual", f"{units_sold:,}")
c4.metric("Produk Stok Menipis", f"{low_stock:,}")

left, right = st.columns(2)
with left:
    st.subheader("Tren Penjualan Harian")
    daily = sales.set_index("transaction_date").resample("D")["total_amount"].sum().reset_index()
    st.line_chart(daily, x="transaction_date", y="total_amount")
with right:
    st.subheader("Produk Terlaris")
    best = (sales.groupby("product_name", as_index=False)["quantity"].sum()
            .sort_values("quantity", ascending=False).head(10))
    st.bar_chart(best, x="product_name", y="quantity")

st.subheader("Daftar Stok Barang")
stock_view = products.copy()
stock_view["status_stok"] = stock_view["stock_qty"].apply(lambda x: "Menipis" if x <= 10 else "Aman")
st.dataframe(stock_view, use_container_width=True, hide_index=True)

st.subheader("Riwayat Transaksi")
st.dataframe(sales.sort_values("transaction_date", ascending=False), use_container_width=True, hide_index=True)

st.subheader("Status ETL dari MongoDB")
try:
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"), serverSelectionTimeoutMS=1500)
    client.admin.command("ping")
    db = client[os.getenv("MONGO_DATABASE", "smartstock_analytics")]
    latest = db.etl_logs.find_one(sort=[("started_at", -1)], projection={"_id": 0})
    if latest:
        st.json(latest, expanded=False)
    else:
        st.info("Belum ada log ETL. Jalankan `python etl.py` setelah konfigurasi MongoDB.")
    client.close()
except Exception as e:
    st.warning("MongoDB belum terhubung; metrik penjualan tetap dapat dibaca dari PostgreSQL.")
    st.caption(str(e))
