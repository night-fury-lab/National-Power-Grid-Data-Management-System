"""
update_region_demand_mu.py

Updates REGION_DETAILS.Demand_MU from state_daily_avg.csv
only for dates that exist in DATE_DIM.
"""

import mysql.connector
import pandas as pd
from mysql.connector import Error

# ---------- CONFIGURATION ----------
DB_CONFIG = {
    "host": "localhost",
    "user": "root",        # 🔧 change to your username
    "password": "root123", # 🔧 change to your password
    "database": "IndianEnergyDB"
}

CSV_FILE = "state_daily_avg.csv"


# ---------- FUNCTIONS ----------
def connect_db():
    """Establish a MySQL connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            print("✅ Connected to MySQL Database")
            return conn
    except Error as e:
        print("❌ Error while connecting to MySQL:", e)
    return None


def get_existing_dates(conn):
    """Fetch all available dates from DATE_DIM."""
    cursor = conn.cursor()
    cursor.execute("SELECT `Date` FROM DATE_DIM")
    # Convert list of (datetime.date,) tuples to a set of date objects
    dates_set = {r[0] for r in cursor.fetchall()}
    cursor.close()
    return dates_set


def upsert_demand_mu(conn, df, valid_dates): # Renamed function
    """
    Insert or Update Demand_MU in REGION_DETAILS if the date exists.
    Uses INSERT ... ON DUPLICATE KEY UPDATE.
    """
    cursor = conn.cursor()
    affected_rows = 0 # Will count inserts (1) and updates (2)
    skipped = 0

    for _, row in df.iterrows():
        state_code = row["StateCode"]
        date = pd.to_datetime(row["Date"]).date()
        avg_demand = float(row["Avg_Demand"])

        # Skip invalid dates
        if date not in valid_dates:
            skipped += 1
            continue

        # [REFINED] Changed from UPDATE to INSERT ... ON DUPLICATE KEY UPDATE
        query = """
            INSERT INTO REGION_DETAILS (State_Code, Report_Date, Demand_MU)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                Demand_MU = VALUES(Demand_MU)
        """
        
        try:
            cursor.execute(query, (state_code, date, avg_demand))
            # Note: rowcount returns 1 for a new INSERT, 2 for an UPDATE
            affected_rows += cursor.rowcount
        except Error as e:
            print(f"❌ Error upserting {state_code} on {date}: {e}")
            skipped += 1


    conn.commit()
    cursor.close()
    print(f"✅ Upserted (Inserted/Updated) {affected_rows} records in REGION_DETAILS.")
    print(f"⚠️ Skipped {skipped} records (missing in DATE_DIM or error).")


# ---------- MAIN ----------
def main():
    print(f"📂 Reading data from {CSV_FILE} ...")
    df = pd.read_csv(CSV_FILE)

    # Check required columns
    required_cols = {"StateCode", "Date", "Avg_Demand"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"❌ CSV missing required columns: {required_cols - set(df.columns)}")

    # Normalize data
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    df["Avg_Demand"] = pd.to_numeric(df["Avg_Demand"], errors="coerce").fillna(0)

    conn = connect_db()
    if not conn:
        return

    valid_dates = get_existing_dates(conn)
    print(f"📅 Loaded {len(valid_dates)} valid dates from DATE_DIM")

    # [REFINED] Call the new function name
    upsert_demand_mu(conn, df, valid_dates)

    conn.close()
    print("🔚 MySQL connection closed.")


if __name__ == "__main__":
    main()
