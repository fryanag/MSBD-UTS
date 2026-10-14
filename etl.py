import os
import time
from datetime import datetime, timezone

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from pymongo import MongoClient
from dotenv import load_dotenv

# Load konfigurasi dari file .env
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

CSV_PATH = os.path.join(BASE_DIR, "data", "penjualan.csv")


def main():
    started = time.time()
    run_id = datetime.now(timezone.utc).strftime(
        "etl_%Y%m%dT%H%M%S_%fZ"
    )

    status = "success"
    error_message = None
    extracted = 0
    transformed = 0
    loaded = 0

    pg = None
    mongo_client = None

    try:
        # ==========================================
        # 1. EXTRACT: Membaca data CSV
        # ==========================================
        print("Memulai proses ETL...")
        print("Membaca data CSV...")

        if not os.path.exists(CSV_PATH):
            raise FileNotFoundError(
                f"File CSV tidak ditemukan: {CSV_PATH}"
            )

        df = pd.read_csv(CSV_PATH)
        extracted = len(df)

        print(f"Data berhasil dibaca: {extracted} baris")

        # ==========================================
        # 2. VALIDASI KOLOM
        # ==========================================
        required = [
            "transaction_id",
            "transaction_date",
            "product_id",
            "product_name",
            "category",
            "unit_price",
            "stock_qty",
            "quantity",
            "sale_unit_price",
            "total_amount",
            "payment_method",
        ]

        missing = [
            col for col in required
            if col not in df.columns
        ]

        if missing:
            raise ValueError(
                f"Kolom wajib tidak ditemukan: {missing}"
            )

        # ==========================================
        # 3. TRANSFORM: Membersihkan data
        # ==========================================
        print("Membersihkan dan mentransformasi data...")

        df = df.dropna(
            subset=[
                "transaction_id",
                "transaction_date",
                "product_id",
            ]
        ).copy()

        df["transaction_date"] = pd.to_datetime(
            df["transaction_date"],
            errors="coerce",
        )

        numeric_cols = [
            "product_id",
            "unit_price",
            "stock_qty",
            "quantity",
            "sale_unit_price",
            "total_amount",
        ]

        for col in numeric_cols:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce",
            )

        df = df.dropna(
            subset=["transaction_date"] + numeric_cols
        ).copy()

        # Validasi nilai numerik
        df = df[
            (df["product_id"] > 0)
            & (df["product_id"] % 1 == 0)
            & (df["stock_qty"] >= 0)
            & (df["stock_qty"] % 1 == 0)
            & (df["quantity"] > 0)
            & (df["quantity"] % 1 == 0)
            & (df["unit_price"] >= 0)
            & (df["sale_unit_price"] >= 0)
            & (df["total_amount"] >= 0)
        ].copy()

        # Validasi data teks agar tidak kosong
        for col in [
            "transaction_id",
            "product_name",
            "category",
            "payment_method",
        ]:
            df[col] = df[col].astype("string").str.strip()

        df = df[
            df["transaction_id"].notna()
            & (df["transaction_id"] != "")
            & df["product_name"].notna()
            & (df["product_name"] != "")
            & df["category"].notna()
            & (df["category"] != "")
            & df["payment_method"].notna()
            & (df["payment_method"] != "")
        ].copy()

        # Pastikan tipe data sesuai
        df["product_id"] = df["product_id"].astype(int)
        df["stock_qty"] = df["stock_qty"].astype(int)
        df["quantity"] = df["quantity"].astype(int)

        # Hitung total transaksi berdasarkan harga jual
        df["sale_unit_price"] = df[
            "sale_unit_price"
        ].round(2)

        df["unit_price"] = df["unit_price"].round(2)

        df["total_amount"] = (
            df["quantity"] * df["sale_unit_price"]
        ).round(2)

        transformed = len(df)

        print(
            f"Transformasi selesai: {transformed} baris"
        )

        if df.empty:
            raise ValueError(
                "Tidak ada data valid untuk dimuat ke PostgreSQL."
            )

        # ==========================================
        # 4. LOAD: Koneksi PostgreSQL
        # ==========================================
        print("Menghubungkan ke PostgreSQL...")

        pg = psycopg2.connect(
            host=os.getenv("PG_HOST", "localhost"),
            port=os.getenv("PG_PORT", "5432"),
            dbname=os.getenv(
                "PG_DATABASE", "umkm_smartstock"
            ),
            user=os.getenv("PG_USER", "postgres"),
            password=os.getenv("PG_PASSWORD", "bachata8"),
            connect_timeout=10,
        )

        pg.autocommit = False

        with pg.cursor() as cur:
            # Periksa database dan schema aktif
            cur.execute("""
                SELECT current_database(), current_schema();
            """)

            database_info = cur.fetchone()

            print(
                f"Database ETL: {database_info[0]}"
            )
            print(
                f"Schema aktif: {database_info[1]}"
            )

            # Periksa keberadaan tabel tujuan
            cur.execute("""
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('products', 'sales');
            """)

            existing_tables = {
                row[1] for row in cur.fetchall()
            }

            missing_tables = {
                "products", "sales"
            } - existing_tables

            if missing_tables:
                raise RuntimeError(
                    "Tabel berikut tidak ditemukan di "
                    f"database {database_info[0]}, schema public: "
                    f"{sorted(missing_tables)}. "
                    "Periksa PG_DATABASE pada file .env "
                    "dan pastikan tabel sudah dibuat."
                )

            # ==========================================
            # LOAD PRODUCTS
            # ==========================================
            print("Memuat data produk...")

            product_df = (
                df.sort_values("transaction_date")
                .drop_duplicates(
                    subset=["product_id"],
                    keep="last",
                )
            )

            product_rows = [
                (
                    int(r.product_id),
                    str(r.product_name),
                    str(r.category),
                    float(r.unit_price),
                    int(r.stock_qty),
                    datetime.now(),
                )
                for r in product_df.itertuples(index=False)
            ]

            execute_values(
                cur,
                """
                INSERT INTO public.products (
                    product_id,
                    product_name,
                    category,
                    unit_price,
                    stock_qty,
                    updated_at
                )
                VALUES %s
                ON CONFLICT (product_id)
                DO UPDATE SET
                    product_name = EXCLUDED.product_name,
                    category = EXCLUDED.category,
                    unit_price = EXCLUDED.unit_price,
                    stock_qty = EXCLUDED.stock_qty,
                    updated_at = EXCLUDED.updated_at
                """,
                product_rows,
            )

            print(
                f"Produk diproses: {len(product_rows)}"
            )

            # ==========================================
            # LOAD SALES
            # ==========================================
            print("Memuat data penjualan...")

            sale_rows = [
                (
                    str(r.transaction_id),
                    r.transaction_date.to_pydatetime(),
                    int(r.product_id),
                    int(r.quantity),
                    float(r.sale_unit_price),
                    float(r.total_amount),
                    str(r.payment_method),
                )
                for r in df.itertuples(index=False)
            ]

            execute_values(
                cur,
                """
                INSERT INTO public.sales (
                    transaction_id,
                    transaction_date,
                    product_id,
                    quantity,
                    unit_price,
                    total_amount,
                    payment_method
                )
                VALUES %s
                ON CONFLICT (transaction_id)
                DO UPDATE SET
                    transaction_date = EXCLUDED.transaction_date,
                    product_id = EXCLUDED.product_id,
                    quantity = EXCLUDED.quantity,
                    unit_price = EXCLUDED.unit_price,
                    total_amount = EXCLUDED.total_amount,
                    payment_method = EXCLUDED.payment_method
                """,
                sale_rows,
            )

            loaded = len(sale_rows)

        # Simpan perubahan PostgreSQL
        pg.commit()

        print("Data berhasil disimpan ke PostgreSQL!")

    except Exception as exc:
        status = "failed"
        error_message = str(exc)

        if pg:
            pg.rollback()

        print(f"Kesalahan ETL: {error_message}")

    finally:
        if pg:
            pg.close()

    # ==========================================
    # 5. LOGGING: Simpan metadata ke MongoDB
    # ==========================================
    print("Memeriksa MongoDB...")

    try:
        mongo_client = MongoClient(
            os.getenv(
                "MONGO_URI",
                "mongodb://localhost:27017/",
            ),
            serverSelectionTimeoutMS=3000,
        )

        mongo_client.admin.command("ping")

        print("MongoDB BERHASIL terhubung!")

        db = mongo_client[
            os.getenv(
                "MONGO_DATABASE",
                "smartstock_analytics",
            )
        ]

        db.etl_logs.insert_one({
            "run_id": run_id,
            "started_at": datetime.now(timezone.utc),
            "status": status,
            "source_file": os.path.basename(CSV_PATH),
            "rows_extracted": extracted,
            "rows_transformed": transformed,
            "rows_loaded": loaded,
            "duration_seconds": round(
                time.time() - started, 3
            ),
            "error": error_message,
        })

        if status == "success":
            db.daily_sales_summary.replace_one(
                {"document_type": "latest_run_summary"},
                {
                    "document_type": "latest_run_summary",
                    "updated_at": datetime.now(timezone.utc),
                    "run_id": run_id,
                    "rows_loaded": loaded,
                    "status": status,
                },
                upsert=True,
            )

    except Exception as mongo_exc:
        print(
            f"MongoDB log warning: {mongo_exc}"
        )

    finally:
        if mongo_client:
            mongo_client.close()

    # ==========================================
    # 6. HASIL AKHIR ETL
    # ==========================================
    print(
        f"ETL {status.upper()} | "
        f"extracted={extracted} "
        f"transformed={transformed} "
        f"loaded={loaded}"
    )

    if error_message:
        raise RuntimeError(error_message)


if __name__ == "__main__":
    main()
