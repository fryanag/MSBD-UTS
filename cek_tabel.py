
import os
import psycopg2
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

try:
    conn = psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=os.getenv("PG_PORT", "5432"),
        dbname=os.getenv("PG_DATABASE", "umkm_smartstock"),
        user=os.getenv("PG_USER", "postgres"),
        password=os.getenv("PG_PASSWORD", "bachata8"),
    )

    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                current_database(),
                current_user,
                current_schema(),
                current_setting('search_path');
        """)

        info = cur.fetchone()

        print("\n=== INFORMASI KONEKSI ===")
        print("Database :", info[0])
        print("User     :", info[1])
        print("Schema   :", info[2])
        print("Search path:", info[3])

        cur.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_type = 'BASE TABLE'
            ORDER BY table_schema, table_name;
        """)

        tables = cur.fetchall()

        print("\n=== SEMUA TABEL ===")

        if tables:
            for schema, table in tables:
                print(f"{schema}.{table}")
        else:
            print("Tidak ada tabel yang ditemukan.")

    conn.close()

except Exception as e:
    print("Gagal memeriksa PostgreSQL:", e)
