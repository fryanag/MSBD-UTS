# UMKM SmartStock — Hybrid Database & ETL Capstone

Starter project for the Database Management Systems capstone.

## Architecture
- **CSV**: simulated source data for sales transactions.
- **PostgreSQL**: structured product and sales data, suitable for constraints, joins, and transactional consistency.
- **MongoDB**: ETL execution logs and flexible analytics documents.
- **Python ETL**: extracts CSV, validates/transforms rows, upserts data to PostgreSQL, and records a run summary in MongoDB.
- **Streamlit**: dashboard reads transactional metrics from PostgreSQL and ETL status from MongoDB.

> The included CSV is synthetic demonstration data, not real UMKM data.

## 1. Prerequisites
- Python 3.10+
- PostgreSQL running locally
- MongoDB running locally (or a MongoDB Atlas connection string)
- Git (optional, for repository publishing)

## 2. Create databases
Create a PostgreSQL database named `smartstock`, then run `sql/schema.sql` in pgAdmin or psql.

MongoDB database and collection are created automatically by the ETL script.

## 3. Setup Python
Windows PowerShell:
```powershell
cd path\to\umkm_smartstock
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```
Edit `.env` with your local credentials.

## 4. Run ETL
```powershell
python etl.py
```
Run it again after changing the CSV to test repeated ingestion. Product records use an upsert pattern; transaction rows use `transaction_id` as a unique key to avoid duplicates.

## 5. Run dashboard
```powershell
streamlit run dashboard.py
```
Open the local URL printed by Streamlit. Use the dashboard's refresh button to reload the latest metrics.

## 6. Automation
For a simple local demonstration, schedule `python etl.py` with Windows Task Scheduler. For example, run it every 5 minutes while demonstrating. Do not claim continuous streaming unless a streaming technology is actually implemented.

## 7. Current scope / next improvements
- Add user authentication and role-based access.
- Add stock mutation rules and transaction entry forms.
- Add stronger data-quality reports and automated tests.
- Add true event streaming only if required by the lecturer.
- Measure ETL duration and dashboard query latency during evaluation.
