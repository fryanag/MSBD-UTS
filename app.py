import os
from decimal import Decimal
from datetime import date, datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template

# Memuat konfigurasi dari file .env
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

app = Flask(__name__)

LOW_STOCK_LIMIT = 10


def get_db_connection():
    """Membuat koneksi ke PostgreSQL."""
    return psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=os.getenv("PG_PORT", "5432"),
        dbname=os.getenv("PG_DATABASE", "umkm_smartstock"),
        user=os.getenv("PG_USER", "postgres"),
        password=os.getenv("PG_PASSWORD", ""),
        connect_timeout=5,
    )


def json_safe(value):
    """Mengubah tipe data PostgreSQL menjadi tipe JSON."""
    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    return value


def fetch_dashboard_data():
    """Mengambil data dashboard dari PostgreSQL."""
    conn = get_db_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            # 1. Ringkasan produk, transaksi, dan omzet
            cur.execute("""
                SELECT
                    (SELECT COUNT(*)
                     FROM public.products) AS total_products,

                    (SELECT COUNT(*)
                     FROM public.sales) AS total_transactions,

                    (SELECT COALESCE(SUM(total_amount), 0)
                     FROM public.sales) AS total_revenue
            """)

            summary = dict(cur.fetchone())

            # 2. Produk dengan stok rendah
            cur.execute("""
                SELECT
                    product_id,
                    product_name,
                    category,
                    stock_qty
                FROM public.products
                WHERE stock_qty <= %s
                ORDER BY stock_qty ASC, product_name ASC
            """, (LOW_STOCK_LIMIT,))

            low_stock = [dict(row) for row in cur.fetchall()]

            # 3. Lima produk terlaris berdasarkan jumlah unit
            cur.execute("""
                SELECT
                    p.product_id,
                    p.product_name,
                    COALESCE(SUM(s.quantity), 0) AS total_sold,
                    COALESCE(SUM(s.total_amount), 0) AS total_revenue
                FROM public.products p
                LEFT JOIN public.sales s
                    ON s.product_id = p.product_id
                GROUP BY p.product_id, p.product_name
                HAVING COALESCE(SUM(s.quantity), 0) > 0
                ORDER BY total_sold DESC, p.product_name ASC
                LIMIT 5
            """)

            top_products = [
                dict(row) for row in cur.fetchall()
            ]

            # 4. Penjualan per tanggal untuk grafik tren
            cur.execute("""
                SELECT
                    transaction_date::date AS sale_date,
                    SUM(total_amount) AS daily_revenue
                FROM public.sales
                GROUP BY transaction_date::date
                ORDER BY sale_date ASC
            """)

            daily_sales = [
                dict(row) for row in cur.fetchall()
            ]

            return {
                "summary": summary,
                "low_stock": low_stock,
                "top_products": top_products,
                "daily_sales": daily_sales,
                "low_stock_limit": LOW_STOCK_LIMIT,
                "database": os.getenv(
                    "PG_DATABASE", "umkm_smartstock"
                ),
            }

    finally:
        conn.close()


@app.route("/")
def index():
    """Menampilkan halaman utama dashboard."""
    return render_template("index.html")


@app.route("/api/dashboard")
def dashboard_api():
    """API data untuk dashboard JavaScript."""
    try:
        data = fetch_dashboard_data()

        # Pastikan semua nilai bisa dikirim sebagai JSON.
        return jsonify({
            key: (
                [
                    {
                        k: json_safe(v)
                        for k, v in row.items()
                    }
                    for row in value
                ]
                if isinstance(value, list)
                else {
                    k: json_safe(v)
                    for k, v in value.items()
                }
                if isinstance(value, dict)
                else value
            )
            for key, value in data.items()
        })

    except psycopg2.Error:
        app.logger.exception("Kesalahan PostgreSQL")
        return jsonify({
            "error": (
                "Tidak dapat membaca database. "
                "Periksa koneksi PostgreSQL dan struktur tabel."
            )
        }), 500

    except Exception:
        app.logger.exception("Kesalahan dashboard")
        return jsonify({
            "error": "Terjadi kesalahan saat memuat dashboard."
        }), 500


if __name__ == "__main__":
    print("Menjalankan UMKM SmartStock...")
    print(
        "Database:",
        os.getenv("PG_DATABASE", "umkm_smartstock")
    )
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
    )