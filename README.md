# National Power Grid Data Management System — Local Setup

This repository contains a React frontend and a Flask backend backed by a MySQL database.

Quick notes:
- Backend expects a MySQL 8+ instance and the SQL files located at `IndianEnergyDB.sql` and `DML.sql` to be imported.
- There are some admin endpoints that call stored procedures — ensure `DML.sql` contains the stored procedures the backend expects (see `backend/app/routes/db_admin.py`).
- Don't commit secrets. Use the `.env.example` files as templates.

## Prerequisites
- Python 3.10+
- Node 18+
- MySQL 8.0+
- npm

## Database: import schema and DML
Start your MySQL server and import the SQL files (PowerShell):

```powershell
# Replace -u and -p with your credentials. You will be prompted for password.
mysql -u root -p < "${PWD}\IndianEnergyDB.sql"
mysql -u root -p < "${PWD}\DML.sql"
```

Note: If you have existing stored procedures referenced by `backend/app/routes/db_admin.py` that are not present in `DML.sql`, create or merge them before running those admin endpoints.

## Backend (Flask)

1. Open PowerShell and create a virtual environment and install dependencies:

```powershell
cd "c:\Users\vishn\OneDrive\Desktop\DBMS_Final\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Set environment variables (temporary for the shell) or create a `backend/.env` file (DO NOT commit it):

```powershell
$env:DB_HOST = 'localhost'
$env:DB_PORT = '3306'
$env:DB_NAME = 'IndianEnergyDB'
$env:DB_USER = 'root'
$env:DB_PASSWORD = '<your_db_password>'
$env:SECRET_KEY = 'change-me'
$env:FLASK_ENV = 'development'
$env:FLASK_DEBUG = 'True'
```

3. Start the backend:

```powershell
python run.py
# The API will be available at http://localhost:5000/api
```

4. Health check:

```powershell
# GET http://localhost:5000/api/health
Invoke-RestMethod -Uri http://localhost:5000/api/health -Method GET | ConvertTo-Json
```

## Frontend (React)

1. Install dependencies and start dev server:

```powershell
cd "c:\Users\vishn\OneDrive\Desktop\DBMS_Final\frontend"
npm install
# Optionally copy .env.example to .env.development and tweak
# Start dev server
npm start
# The app runs at http://localhost:3000 and calls the backend at REACT_APP_API_URL
```

## Notes & Next steps
- I added a lightweight health endpoint at `/api/health` (returns JSON with `db: true/false`). Use this to verify the backend and DB connectivity.
- The backend still calls some stored procedures from `db_admin.py` (for daily reports and metrics). If those fail, either implement the stored procedures in the DB or modify `db_admin.py` to use queries instead — I can help with that.
- Consider adding `docker-compose.yml` to orchestrate MySQL + backend + frontend for reproducible dev environments.

If you'd like, I can:
- add Docker Compose for the whole stack,
- implement or synthesize the missing stored procedures referenced by `db_admin.py`, or
- add a small integration test script that exercises a few endpoints.
