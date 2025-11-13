"""
integrated_RE_parser.py

Wrapper to process all cleaned renewable Excel reports in:
  Processed_Renewable_XLSX_reports/

- Resumes from last date present in DATE_DIM
- Parses date from filenames like '1_Aug_2025_Daily_RE_Generation_Report_cleaned.xlsx'
- Handles 'Sept' -> 'Sep' normalization
- Preserves all original functions/logic unchanged
- Commits after each file; continues on errors
"""

import mysql.connector
import pandas as pd
from datetime import datetime, date, timedelta
import re
import traceback
import os

# ============== CONFIG ==============
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root123',
    'database': 'IndianEnergyDB'
}

# Folder containing the cleaned excel files
REPORTS_FOLDER = r"C:\Users\vishn\OneDrive\Desktop\DBMS_Final\Processed_Renewable_XLSX_reports"
# ====================================

# --------------------------
# Add your canonical state code map here (you provided this earlier)
# Keys should be uppercase full state names used as canonical forms
STATE_CODE_MAP = {
    'DELHI': 'DL', 'HARYANA': 'HRN', 'HIMACHAL PRADESH': 'HP', 'JAMMU AND KASHMIR': 'JAK',
    'LADAKH': 'LDK', 'PUNJAB': 'PNB', 'RAJASTHAN': 'RJ', 'UTTARAKHAND': 'UTK', 'UTTAR PRADESH': 'UP',
    'ARUNACHAL PRADESH': 'ACP', 'ASSAM': 'ASM', 'MANIPUR': 'MIP', 'MEGHALAYA': 'MGA', 'MIZORAM': 'MZM',
    'NAGALAND': 'NGD', 'TRIPURA': 'TPA', 'CHHATISGARH': 'CTG', 'GOA': 'GOA', 'GUJARAT': 'GJT',
    'MADHYA PRADESH': 'MPD', 'MAHARASHTRA': 'MHA', 'ANDHRA PRADESH': 'AP', 'KARNATAKA': 'KRT',
    'KERALA': 'KRL', 'LAKSHADWEEP': 'LKS', 'PUDUCHERRY': 'PU', 'TAMIL NADU': 'TND', 'TELANGANA': 'TLG',
    'ANDAMAN AND NICOBAR ISLANDS': 'ANI', 'BIHAR': 'BHR', 'JHARKHAND': 'JHK', 'ODISHA': 'ODI',
    'SIKKIM': 'SKM', 'WEST BENGAL': 'BGL'
}

# Additional common replacements / aliases to handle variations in Excel
STATE_NORMALIZATION_ALIASES = {
    'PONDICHERRY': 'PUDUCHERRY',
    'PONDY': 'PUDUCHERRY',
    'UTTARANCHAL': 'UTTARAKHAND',
    'ORISSA': 'ODISHA',
    'J&K': 'JAMMU AND KASHMIR',
    'J & K': 'JAMMU AND KASHMIR',
    'A & N ISLANDS': 'ANDAMAN AND NICOBAR ISLANDS',
    'A&N ISLANDS': 'ANDAMAN AND NICOBAR ISLANDS',
    'DADRA AND NAGAR HAVELI': 'DADRA AND NAGAR HAVELI',
    'DAMAN AND DIU': 'DAMAN AND DIU',
}

# ===========================
# --- utility: tolerant column getter with synonyms ---
# ===========================
def pick_col(df, synonyms):
    """Return actual column name from df that matches any synonym (case-insensitive)."""
    cols_lower = {c.lower(): c for c in df.columns}
    for s in synonyms:
        key = s.lower()
        if key in cols_lower:
            return cols_lower[key]
    # fallback: find partial match
    for k, real in cols_lower.items():
        for s in synonyms:
            if s.lower() in k:
                return real
    return None

# ===========================
# --- cleaning helpers ---
# ===========================
def is_blank_string(val):
    if val is None:
        return True
    try:
        s = str(val).strip()
        return s == "" or s.lower() in ["nan", "none", "-", "--"]
    except:
        return True

def clean_state_name(raw):
    """Extract the English portion from bilingual names or return normalized string.
       Returns None for invalid/missing names."""
    if pd.isna(raw):
        return None
    s = str(raw).strip()
    if s == "":
        return None
    # Replace newlines and multiple spaces
    s = re.sub(r"[\r\n]+", " ", s)
    # If bilingual with '/', choose the English-looking part (has ASCII letters)
    if '/' in s:
        parts = [p.strip() for p in s.split('/') if p.strip() != '']
        # pick part that contains ascii letters (English)
        for p in reversed(parts):  # often English is last
            if re.search(r'[A-Za-z]', p):
                s = p
                break
        else:
            s = parts[-1]  # fallback
    # Try to extract ascii letters (English portion)
    match = re.search(r"[A-Za-z&\-\.\(\)\/\s]+", s)
    if match:
        extracted = match.group(0).strip()
        # cleanup slashes and extra spaces
        extracted = extracted.split('/')[-1].strip() if '/' in extracted else extracted
        extracted = re.sub(r"\s{2,}", " ", extracted)
        if extracted.lower() in ["", "-", "nan"]:
            return None
        return extracted
    # fallback: remove non-ascii characters
    ascii_only = ''.join(ch for ch in s if ord(ch) < 128)
    ascii_only = ascii_only.strip()
    return ascii_only if ascii_only and ascii_only.lower() not in ["-", "nan"] else None

def normalize_state_name_for_lookup(name):
    """Normalize to an uppercase canonical-like form, apply alias replacements."""
    if not name:
        return None
    n = name.strip().upper()
    # remove stray punctuation
    n = re.sub(r'[\.\,]+', '', n)
    # apply alias map if exists
    if n in STATE_NORMALIZATION_ALIASES:
        n = STATE_NORMALIZATION_ALIASES[n]
    return n

def clean_numeric(value):
    """Return float or None. Remove commas, non-numeric characters except . and -."""
    if pd.isna(value):
        return None
    s = str(value).strip()
    if s == "" or s.lower() in ["nan", "-", "none", "--"]:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", s)
    if cleaned == "" or cleaned == "-" or cleaned == ".":
        return None
    try:
        val = float(cleaned)
        return val
    except:
        return None

def is_invalid_row_name(name):
    """Skip row if name is summary/total/region/all-india-like."""
    if name is None:
        return True
    s = str(name).strip().lower()
    if s == "" or s in ["nan", "-", "--"]:
        return True
    junk_keywords = ["total", "region", "summary", "all india", "northern region",
                     "southern region", "western region", "eastern region", "north-eastern region",
                     "north east", "north west", "south east", "south west", "total daily"]
    return any(k in s for k in junk_keywords)

# ===========================
# --- DB helpers ---
# ===========================
def get_db_connection(cfg):
    try:
        conn = mysql.connector.connect(**cfg)
        print("✅ Connected to MySQL.")
        return conn
    except mysql.connector.Error as e:
        print("❌ DB connection error:", e)
        raise

def fetch_lookup_map(cursor, query, key_col, val_col):
    cursor.execute(query)
    rows = cursor.fetchall()
    # Normalize keys to lowercase stripped for robust matching
    lookup = {}
    for r in rows:
        key = r[key_col]
        val = r[val_col]
        if key is None:
            continue
        lookup[str(key).strip().lower()] = val
    return lookup

def get_next_plant_id(cursor):
    cursor.execute("SELECT MAX(CAST(SUBSTRING(Plant_ID, 2) AS UNSIGNED)) AS max_id FROM POWERPLANTS WHERE Plant_ID LIKE 'P%'")
    row = cursor.fetchone()
    max_id = row['max_id'] if row and 'max_id' in row else None
    return (max_id or 0) + 1

def ensure_date_exists(cursor, log_date):
    cursor.execute("SELECT COUNT(*) AS cnt FROM DATE_DIM WHERE `Date` = %s", (log_date,))
    cnt = cursor.fetchone()['cnt']
    if cnt == 0:
        cursor.execute("INSERT INTO DATE_DIM (`Date`, `Day`, `Month`, `Year`) VALUES (%s,%s,%s,%s)",
                       (log_date, log_date.day, log_date.month, log_date.year))
        print(f"🗓️ Inserted {log_date} into DATE_DIM")

def get_or_create_plant(cursor, plant_name, state_code, sector_id, type_id, next_id):
    # plant_name assumed normalized (string)
    cursor.execute("SELECT Plant_ID FROM POWERPLANTS WHERE Plant_Name = %s", (plant_name,))
    r = cursor.fetchone()
    if r:
        return r['Plant_ID'], next_id
    new_id = f'P{next_id}'
    cursor.execute("""
        INSERT INTO POWERPLANTS (Plant_ID, Plant_Name, State_Code, Sector_ID, Type_ID)
        VALUES (%s,%s,%s,%s,%s)
    """, (new_id, plant_name, state_code, sector_id, type_id))
    print(f"-> Created new plant: {plant_name} (ID: {new_id})")
    return new_id, next_id + 1

# --- sheet detection helper ---
def detect_sheets(file_path):
    xl = pd.ExcelFile(file_path)
    station_sheet = None
    summary_sheet = None
    for s in xl.sheet_names:
        low = s.lower()
        if any(k in low for k in ['station', 'plant', 'stations', 'plants', 'details']):
            station_sheet = s
        if any(k in low for k in ['summary', 'state', 'region', 'state data']):
            summary_sheet = s
    if not station_sheet:
        station_sheet = xl.sheet_names[0]
    if not summary_sheet:
        summary_sheet = xl.sheet_names[-1]
    print(f"Detected sheets -> station: '{station_sheet}', summary: '{summary_sheet}'")
    return station_sheet, summary_sheet

# ====== Main integrated processor (core logic copied unchanged) ======
def process_single_file(conn, cursor, file_path, report_date):
    """Processes a single Excel file exactly like the original script logic."""
    print(f"\n================ Processing {os.path.basename(file_path)} ({report_date}) ================")
    maps = {
        'states': fetch_lookup_map(cursor, "SELECT State_Name, State_Code FROM STATE", 'State_Name', 'State_Code'),
        'sectors': fetch_lookup_map(cursor, "SELECT Sector_Name, Sector_ID FROM SECTOR", 'Sector_Name', 'Sector_ID')
    }

    next_id = get_next_plant_id(cursor)
    ensure_date_exists(cursor, report_date)

    station_sheet, summary_sheet = detect_sheets(file_path)
    skipped_state_list = []

    # --------- PROCESS SUMMARY (State Data) FIRST ----------
    print("\nProcessing summary data from sheet:", summary_sheet)
    df_sum = pd.read_excel(file_path, sheet_name=summary_sheet)
    df_sum = df_sum.dropna(how='all')  # remove empty rows
    # find columns for state and biomass/others-res (try multiple synonyms)
    state_col = pick_col(df_sum, ['State / Region', 'State', 'State Name', 'State / Region '])
    others_col = pick_col(df_sum, ['Others RES', 'Others RES (MU)', 'Biomass (MU)', 'Others', 'Total (MU)', 'Generation (MU)'])

    if state_col is None:
        print("⚠️ Could not find a 'State / Region' column in summary sheet; aborting summary processing.")
    else:
        summary_inserted = 0
        summary_skipped = 0
        for _, row in df_sum.iterrows():
            raw_state = row.get(state_col)
            state_name = clean_state_name(raw_state)
            if state_name is None or is_invalid_row_name(state_name):
                summary_skipped += 1
                continue

            normalized = normalize_state_name_for_lookup(state_name)
            # Try DB map (lowercase keys), then fallback to STATE_CODE_MAP (uppercase keys)
            state_code = None
            if normalized:
                state_code = maps['states'].get(normalized.lower())
            if state_code is None:
                # try alias map or direct canonical map
                state_code = STATE_CODE_MAP.get(normalized)
            if state_code is None:
                # try one more: try raw uppercase trimmed
                alt = STATE_CODE_MAP.get(state_name.strip().upper())
                if alt:
                    state_code = alt

            if state_code is None:
                print(f" -> Skipping state '{state_name}': not found in STATE table or STATE_CODE_MAP.")
                skipped_state_list.append(state_name)
                summary_skipped += 1
                continue

            plant_name = f"Biomass_{state_code}"
            sector_id = 'CCT'
            type_id = 'BIO'

            # read Others/Biomass value robustly
            actual_mu = None
            if others_col:
                actual_mu = clean_numeric(row.get(others_col))
            # Also try columns like 'Generation (MU)' or other synonyms if others_col missing
            if actual_mu is None:
                alt = pick_col(df_sum, ['Generation (MU)', 'Daily Generation (MU)', 'Total (MU)', 'RE Generation (MU)'])
                if alt:
                    actual_mu = clean_numeric(row.get(alt))

            if actual_mu is None:
                # nothing to insert
                summary_skipped += 1
                continue

            plant_id, next_id = get_or_create_plant(cursor, plant_name, state_code, sector_id, type_id, next_id)
            cursor.execute("""
                INSERT INTO PRODUCTIONLOG (Plant_ID, Log_Date, Todays_Actual_MU)
                VALUES (%s,%s,%s)
                ON DUPLICATE KEY UPDATE Todays_Actual_MU = VALUES(Todays_Actual_MU)
            """, (plant_id, report_date, actual_mu))
            summary_inserted += 1

        print(f"Summary done: inserted={summary_inserted}, skipped={summary_skipped}")

    # --------- PROCESS STATION (Plant) DATA NEXT ----------
    print("\nProcessing station data from sheet:", station_sheet)
    df_st = pd.read_excel(file_path, sheet_name=station_sheet)
    df_st = df_st.dropna(how='all')
    # pick important columns with synonyms
    station_col = pick_col(df_st, ['Station', 'Station Name', 'Plant', 'Plant Name', 'Station/ Plant'])
    state_col_st = pick_col(df_st, ['State / Region', 'State', 'State Name'])
    op_cap_col = pick_col(df_st, ['Operational Capacity (MW)', 'Operational Capacity', 'Capacity (MW)', 'Operational_Capacity_MW'])
    actual_col = pick_col(df_st, ['Actual Generation (MU)', 'Actual Generation', 'Todays Actual (MU)', 'Todays_Actual_MU', 'Generation (MU)'])
    capable_col = pick_col(df_st, ['Capable Generation (MU)', 'Capable Generation', 'Capable_Generation_MU'])
    eff_col = pick_col(df_st, ['Efficiency (%)', 'Efficiency', 'Efficiency_Percentage'])

    if station_col is None:
        print("⚠️ Could not find 'Station' column in station sheet; aborting station processing.")
    else:
        st_inserted = 0
        st_skipped = 0
        type_name_map = {'solar': 'SO', 'wind': 'WI', 'hydro': 'HY', 'thermal': 'TH', 'nuclear': 'NU', 'biomass': 'BIO'}
        for _, row in df_st.iterrows():
            raw_plant = row.get(station_col)
            if pd.isna(raw_plant):
                st_skipped += 1
                continue
            plant_name = str(raw_plant).strip()
            if is_blank_string(plant_name) or is_invalid_row_name(plant_name):
                st_skipped += 1
                continue

            raw_state = row.get(state_col_st) if state_col_st else None
            state_name = clean_state_name(raw_state)
            normalized = normalize_state_name_for_lookup(state_name) if state_name else None
            state_code = None
            if normalized:
                state_code = maps['states'].get(normalized.lower())
            if state_code is None and normalized:
                state_code = STATE_CODE_MAP.get(normalized)
            if state_code is None and state_name:
                state_code = STATE_CODE_MAP.get(state_name.strip().upper())

            # Sector and Type mapping
            sector_col = pick_col(df_st, ['Sector', 'Sector Name'])
            sector_raw = row.get(sector_col) if sector_col else None
            sector_id = maps['sectors'].get(str(sector_raw).strip().lower()) if sector_raw is not None else None
            type_col = pick_col(df_st, ['Type', 'Plant Type', 'Technology'])
            type_raw = row.get(type_col) if type_col else None
            type_id = None
            if type_raw is not None:
                type_id = type_name_map.get(str(type_raw).strip().lower())

            # If state not found, log and skip (we require a valid state to link)
            if (state_name and state_code is None) or (not state_name):
                print(f" -> Skipping plant '{plant_name}': state '{state_name}' not resolved.")
                st_skipped += 1
                continue

            # Numeric fields
            op_cap = clean_numeric(row.get(op_cap_col)) if op_cap_col else None
            actual_mu = clean_numeric(row.get(actual_col)) if actual_col else None
            capable_mu = clean_numeric(row.get(capable_col)) if capable_col else None
            efficiency = clean_numeric(row.get(eff_col)) if eff_col else None

            # Do not insert rows with no numeric payload
            if op_cap is None and actual_mu is None and capable_mu is None and efficiency is None:
                st_skipped += 1
                continue

            # create/find plant
            plant_id, next_id = get_or_create_plant(cursor, plant_name, state_code, sector_id, type_id, next_id)

            # Insert into productionlog: include fields if present
            cursor.execute("""
                INSERT INTO PRODUCTIONLOG
                (Plant_ID, Log_Date, Efficiency_Percentage, Todays_Actual_MU, Capable_Generation_MU, Operational_Capacity_MW)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    Efficiency_Percentage = VALUES(Efficiency_Percentage),
                    Todays_Actual_MU = VALUES(Todays_Actual_MU),
                    Capable_Generation_MU = VALUES(Capable_Generation_MU),
                    Operational_Capacity_MW = VALUES(Operational_Capacity_MW)
            """, (plant_id, report_date, efficiency, actual_mu, capable_mu, op_cap))

            st_inserted += 1

        print(f"Station done: inserted={st_inserted}, skipped={st_skipped}")

    # commit once after both parts
    conn.commit()
    print("\n🎉 All data processed and committed.")

    if skipped_state_list:
        print("\n⚠️ The following states were present in the sheet but could not be resolved to a state code:")
        for s in sorted(set(skipped_state_list)):
            print("   -", s)

# ===========================
# Controller (multi-file loop & summary)
# ===========================
def main():
    conn = None
    cursor = None
    processed_count = 0
    skipped_pattern_count = 0
    failed_count = 0

    try:
        conn = get_db_connection(DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        print("➡️ Processing all valid files found in the folder...")
        print("   (ON DUPLICATE KEY UPDATE will refresh existing entries.)")

        # gather valid files with parseable dates
        valid_files = []
        for fname in os.listdir(REPORTS_FOLDER):
            if not fname.lower().endswith(".xlsx"):
                continue
            
            try:
                # Try parsing dd-mm-yyyy.xlsx
                file_date = datetime.strptime(fname, "%d-%m-%Y.xlsx").date()
                valid_files.append((file_date, fname))
            except ValueError:
                # Fallback for the old _cleaned.xlsx format
                
                # --- THIS IS THE FIX ---
                # Added an underscore '_' between the month and year
                match = re.search(r"(\d{1,2}_[A-Za-z]{3,4}_\d{4})", fname)
                # --- END OF FIX ---

                if not match:
                    print(f"⚠️ Skipping file without valid date pattern: {fname}")
                    skipped_pattern_count += 1
                    continue
                date_part = match.group(1)
                # normalize Sept -> Sep for parsing
                date_part_norm = date_part.replace("_Sept_", "_Sep_").replace("_SEPT_", "_Sep_")
                try:
                    file_date = datetime.strptime(date_part_norm, "%d_%b_%Y").date()
                    valid_files.append((file_date, fname))
                except ValueError:
                    print(f"⚠️ Skipping file with unparseable date: {fname} (extracted='{date_part}' normalized='{date_part_norm}')")
                    skipped_pattern_count += 1
                    continue
            
        # sort by date
        valid_files.sort(key=lambda t: t[0])

        if not valid_files:
            print("No valid files found in folder. Exiting.")
            return

        print(f"Found {len(valid_files)} candidate files to process.") # This should now show 96

        for file_date, fname in valid_files:
            
            file_path = os.path.join(REPORTS_FOLDER, fname)
            try:
                process_single_file(conn, cursor, file_path, file_date)
                processed_count += 1
            except Exception as e:
                print(f"❌ Error processing {fname}: {e}")
                traceback.print_exc()
                try:
                    conn.rollback()
                except Exception:
                    pass
                failed_count += 1
                # continue to next file

        # final summary
        print("\n================ SUMMARY ================\n")
        print(f"Attempted to process: {processed_count}")
        print(f"Skipped (bad pattern): {skipped_pattern_count}")
        print(f"Failed files       : {failed_count}")
        print("\n=========================================\n")

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        traceback.print_exc()
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass
            print("🔒 DB connection closed.")

if __name__ == "__main__":
    main()
