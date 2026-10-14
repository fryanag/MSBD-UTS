
import os
import psycopg2
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

# Tes PostgreSQL
print("Memeriksa PostgreSQL...")
try:
    pg = psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        dbname=os.getenv("PG_DATABASE"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
        connect_timeout=5
    )

    with pg.cursor() as cursor:
        cursor.execute("SELECT current_database();")
        print("PostgreSQL BERHASIL:", cursor.fetchone()[0])

    pg.close()
except Exception as e:
    print("PostgreSQL GAGAL:", e)

# Tes MongoDB
print("\nMemeriksa MongoDB...")
client = None

try:
    client = MongoClient(
        os.getenv("MONGO_URI", "mongodb://localhost:27017/"),
        serverSelectionTimeoutMS=3000
    )

    client.admin.command("ping")
    print("MongoDB BERHASIL terhubung!")
except Exception as e:
    print("MongoDB GAGAL:", e)
finally:
    if client is not None:
        client.close()
