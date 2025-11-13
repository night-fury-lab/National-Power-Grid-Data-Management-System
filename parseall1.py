import os
import re
from datetime import datetime, timedelta
import mysql.connector
import pandas as pd

# ---------------------------
# CONFIGURATION
# ---------------------------
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root123', # Replace with your actual password
    'database': 'IndianEnergyDB',
    'port': 3306
}
REPORT_FOLDER = "Daily_Plant_Generation_XLS_Reports"
DEBUG = True

# ---------------------------
# CONSTANT MAPS
# ---------------------------
STATE_MAP = {
    'DELHI': 'DL', 'HARYANA': 'HRN', 'HIMACHAL PRADESH': 'HP', 'JAMMU AND KASHMIR': 'JAK',
    'LADAKH': 'LDK', 'PUNJAB': 'PNB', 'RAJASTHAN': 'RJ', 'UTTARAKHAND': 'UTK', 'UTTAR PRADESH': 'UP',
    'ARUNACHAL PRADESH': 'ACP', 'ASSAM': 'ASM', 'MANIPUR': 'MIP', 'MEGHALAYA': 'MGA', 'MIZORAM': 'MZM',
    'NAGALAND': 'NGD', 'TRIPURA': 'TPA', 'CHHATISGARH': 'CTG', 'GOA': 'GOA', 'GUJARAT': 'GJT',
    'MADHYA PRADESH': 'MPD', 'MAHARASHTRA': 'MHA', 'ANDHRA PRADESH': 'AP', 'KARNATAKA': 'KRT',
    'KERALA': 'KRL', 'LAKSHADWEEP': 'LKS', 'PUDUCHERRY': 'PU', 'TAMIL NADU': 'TND', 'TELANGANA': 'TLG',
    'ANDAMAN AND NICOBAR ISLANDS': 'ANI',
    'BIHAR': 'BHR', 'JHARKHAND': 'JHK', 'ODISHA': 'ODI',
    'SIKKIM': 'SKM', 'WEST BENGAL': 'BGL',
    'BHUTAN': 'BHU'
}
STATE_CODE_TO_NAME = {v: k for k, v in STATE_MAP.items()}

SECTOR_MAP = {
    'STATE SECTOR': 'ST', 'PVT. SECTOR': 'PVT', 'CENTRAL SECTOR': 'CCT',
    'PRIVATE SECTOR': 'PVT', 'STATE': 'ST', 'PRIVATE': 'PVT', 'CENTRAL': 'CCT', 'PVT': 'PVT'
}
TYPE_MAP = {
    'THER (GT)': 'TGT', 'THERMAL': 'TH', 'HYDRO': 'HY', 'NUCLEAR': 'NU',
    'WIND': 'WI', 'SOLAR': 'SO', 'BIOMASS': 'BIO', 'THER (CGT)': 'TGT',
    'THER (DG)': 'TDG'
}
CONTEXT_HEADER_KEYWORDS = {
    'SECTOR:', 'TYPE:', 'STATE SECTOR', 'PVT SECTOR', 'PVT. SECTOR',
    'CENTRAL SECTOR', 'PRIVATE SECTOR', 'THERMAL', 'HYDRO', 'NUCLEAR',
    'THER (GT)', 'THER (DG)', 'STATE', 'PVT', 'CENTRAL', 'PRIVATE'
}
UNIT_REGEX = re.compile(r'^(UNIT[,\s]*\d+|UNIT\b)', re.IGNORECASE)
UNIT_NUMBER_EXTRACT_REGEX = re.compile(r'\d+') # Regex to extract number

# ---------------------------
# UTILITY FUNCTIONS (Same as v8/v7)
# --- [ Utility Functions Placeholder - Copy from previous script ] ---
def try_read_excel(path):
    exts = os.path.splitext(path)[1].lower()
    engines = []
    if exts == '.xls': engines = ['xlrd', None, 'openpyxl']
    else: engines = ['openpyxl', None]
    errs = []
    for eng in engines:
        try:
            if DEBUG: print(f"[READ] Trying engine={eng} for {os.path.basename(path)}")
            engine_arg = {'engine': eng} if eng else {}
            df = pd.read_excel(path, header=None, dtype=object, **engine_arg)
            df = df.map(lambda x: x.replace('\xa0', ' ') if isinstance(x, str) else x)
            if DEBUG: print(f"[READ] Successfully read with engine={eng if eng else 'default'}")
            return df
        except Exception as e:
            errs.append((eng if eng else 'default', str(e)))
            if DEBUG: print(f"[READ] engine={eng if eng else 'default'} failed for {os.path.basename(path)}: {e}")
    error_message = f"Failed to read {os.path.basename(path)}. Tried: " + ", ".join(f"{e[0]} ({e[1]})" for e in errs)
    if '.xls' in path.lower() and 'xlrd' not in [e[0] for e in errs]:
         error_message += "\nConsider installing xlrd==1.2.0: pip install xlrd==1.2.0"
    print(f"[ERROR] {error_message}")
    return None

def sanitize_string(x):
    if x is None or (isinstance(x, float) and pd.isna(x)): return ''
    return str(x).strip()

def safe_float(x):
    if x is None or (isinstance(x, float) and pd.isna(x)): return None
    s = str(x).strip()
    if s in ['', '-', '—', 'NA', 'N.A.', 'N/A', 'nan']: return None
    s_clean = s.replace(',', '')
    s_clean = re.sub(r'[^\d\.\-]', '', s_clean)
    if s_clean in ['', '.', '-', '-.']: return None
    try: return float(s_clean)
    except ValueError:
        if s.upper() in ['0', '0.0', 'NIL']: return 0.0
        # Reduced verbosity
        # if DEBUG: print(f"[DEBUG] safe_float conversion error for '{s}' -> cleaned '{s_clean}'")
        return None

def parse_date_top_rows(df):
    for i in range(min(10, len(df))):
        txt = " ".join([str(x) for x in df.iloc[i].values if pd.notna(x) and str(x).strip() != ''])
        if not txt: continue
        m = re.search(r'(\d{2})[\/\-](\d{2})[\/\-](\d{4})', txt)
        if m:
            dd, mm, yyyy = m.groups()
            try: dt = datetime(int(yyyy), int(mm), int(dd)); return dt.strftime("%Y-%m-%d"), dd, mm, yyyy
            except ValueError: pass
        m2 = re.search(r'(\d{4})[\/\-](\d{2})[\/\-](\d{2})', txt)
        if m2:
            yyyy, mm, dd = m2.groups()
            try: dt = datetime(int(yyyy), int(mm), int(dd)); return dt.strftime("%Y-%m-%d"), dd, mm, yyyy
            except ValueError: pass
    return None, None, None, None

def find_header_columns_by_text(df, keywords, search_rows=14):
    cols = df.shape[1]; found = {k: None for k in keywords.keys()}
    header_rows_indices = list(range(min(search_rows, len(df))))
    potential_header_row = -1; max_matches = 0
    for r in header_rows_indices:
        matches_in_row = 0; row_content = set()
        for c in range(cols):
            val = df.iat[r, c]
            if pd.notna(val): row_content.add(str(val).upper().strip())
        for alias, subs in keywords.items():
            if any(any(sub in cell_content for cell_content in row_content) for sub in subs): matches_in_row += 1
        if matches_in_row > max_matches and matches_in_row > 2: max_matches = matches_in_row; potential_header_row = r
    search_indices = []
    if potential_header_row != -1:
         # Reduced verbosity
         # if DEBUG: print(f"[HDR] Identified potential header row index: {potential_header_row}")
         search_indices = [potential_header_row]
         if potential_header_row + 1 < min(search_rows, len(df)): search_indices.append(potential_header_row + 1)
    else:
         # if DEBUG: print("[HDR] No clear single header row found, searching all initial rows.")
         search_indices = header_rows_indices
    for r in search_indices:
         for c in range(cols):
              val = df.iat[r, c];
              if pd.isna(val): continue
              s = str(val).upper().strip()
              for alias, subs in keywords.items():
                  if found[alias] is None:
                      for sub in subs:
                          pattern = r'\b' + re.escape(sub) + r'\b' if len(sub) > 3 else re.escape(sub)
                          if re.search(pattern, s):
                              found[alias] = c
                              # Reduced verbosity
                              # if DEBUG: print(f"[HDR] Found '{alias}' at r{r} c{c} ('{sub}') -> '{s[:60]}'")
                              break
                  if found[alias] is not None: continue
              if all(v is not None for v in found.values()): break
         if all(v is not None for v in found.values()): break
    # Reduced verbosity
    # if DEBUG and not all(f is not None for f in found.values()):
    #    print(f"[HDR WARN] Missing some headers: {[k for k,v in found.items() if v is None]}")
    return found


def parse_date_like(v):
    if v is None or (isinstance(v, float) and pd.isna(v)): return None
    if isinstance(v, (datetime, pd.Timestamp)): return v.strftime('%Y-%m-%d')
    s = str(v).strip();
    if s == '': return None
    if isinstance(v, (int, float)) and 10000 < v < 100000:
        try: d = pd.to_datetime(v, unit='D', origin='1899-12-30'); return d.strftime('%Y-%m-%d')
        except (ValueError, TypeError, OverflowError): pass
    for fmt in ('%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%y', '%d-%b-%Y', '%d %b %Y'):
        try: d = datetime.strptime(s.split(' ')[0], fmt); return d.strftime('%Y-%m-%d')
        except (ValueError, TypeError): continue
    m = re.search(r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})', s)
    if m:
        p1, p2, y = m.groups();
        try:
            y_int = int(y)
            if len(y) == 2: y = "20" + y
            y_int = int(y)
            p1_int = int(p1); p2_int = int(p2)
            try: return datetime(y_int, p2_int, p1_int).strftime('%Y-%m-%d') # MM/DD
            except ValueError:
                try: return datetime(y_int, p1_int, p2_int).strftime('%Y-%m-%d') # DD/MM
                except ValueError: pass
        except ValueError: pass
    # Reduced verbosity
    # if DEBUG: print(f"[WARN] Could not parse date-like value: '{v}'")
    return None

def create_db_conn(cfg):
    try: 
        cnx = mysql.connector.connect(**cfg);
    # Reduced verbosity
    # if DEBUG: print("[DB] Connected successfully.")
        return cnx
    except mysql.connector.Error as err: raise RuntimeError(f"DB connection error: {err}")
    except Exception as e: raise RuntimeError(f"DB connection error: {e}")
# ---------------------------
# PASS 1: Extract Region Data
# ---------------------------
# ---------------------------
# PASS 1: Extract Region Data
# ---------------------------
def pre_scan_for_region_data(df, report_iso, monitored_col_idx, cnx):
    """Scans DF, finds state totals (MW), and inserts into REGION_DETAILS."""
    if DEBUG: print(f"\n--- Starting Pass 1: Region Data for {report_iso} ---")
    pass1_cursor = None
    inserted_count = 0
    all_state_codes = set(STATE_MAP.values())
    if 'BHU' in all_state_codes: all_state_codes.remove('BHU') # Exclude Bhutan import

    try:
        pass1_cursor = cnx.cursor()
        # [REFINED v8] Updated SQL to insert MW and NULLs for other fields
        sql_region = """INSERT INTO REGION_DETAILS (
                            State_Code, Report_Date, Monitored_Capacity_MW,
                            Generated_MU, Imported_MU, Surplus_MU, Demand_MU, Grid_Frequency_HZ
                        ) VALUES (%s, %s, %s, NULL, NULL, NULL, NULL, NULL)
                        ON DUPLICATE KEY UPDATE Monitored_Capacity_MW=VALUES(Monitored_Capacity_MW)"""

        current_state_code_pass1 = None # Persistent context for this pass
        region_data_found = {} # {state_code: capacity_MW}

        for r in range(len(df)):
            row_vals = [sanitize_string(df.iat[r, c]) if c < df.shape[1] else '' for c in range(df.shape[1])]
            combined = " ".join([x.upper() for x in row_vals if x])
            if combined.strip() == '': continue

            # Detect State Header - Update persistent context
            is_state_header = False
            state_code_in_row = None
            for name, code in STATE_MAP.items():
                pattern = r'\b' + re.escape(name).replace('AND', '(?:AND|&)') + r'\b' # Flexible & vs AND
                if re.search(pattern, combined):
                    state_code_in_row = code # Note mention
                    non_empty_cells = sum(1 for x in row_vals if x)
                    name_in_first_cols = any(name in (row_vals[c].upper() if c<len(row_vals) else '') for c in range(3))
                    # Header: Name prominent, few other entries
                    if name_in_first_cols and non_empty_cells < 8:
                         current_state_code_pass1 = code # Update main context for Pass 1
                         is_state_header = True
                         # Reduced verbosity
                         # if DEBUG: print(f"[PASS 1 CTX] Row {r}: State Context -> {name} ({current_state_code_pass1})")
                         break # Found definitive state header

            if is_state_header: continue # Skip the header row itself

            # Detect STATE TOTAL / REGION TOTAL row
            if re.search(r'\b(STATE|REGION)\s*TOTAL\b', combined):
                monitored_val = safe_float(df.iat[r, monitored_col_idx]) if monitored_col_idx is not None else None
                if monitored_val is None:
                    numbers = [safe_float(v) for v in row_vals if safe_float(v) is not None]
                    monitored_val = max(numbers) if numbers else None
                # [REFINED v8] Store MW value directly
                monitored_mw = monitored_val

                # Use the persistent context from this pass
                state_code_to_use = current_state_code_pass1
                # Fallback: if context missing, check if state was mentioned in *this* total row
                if not state_code_to_use and state_code_in_row:
                    state_code_to_use = state_code_in_row
                    # if DEBUG: print(f"[PASS 1 WARN] Row {r}: Using state '{state_code_to_use}' from TOTAL row.")

                # Reduced verbosity
                # if DEBUG: print(f"[PASS 1 DEBUG] Row {r}: Found TOTAL. Context State={state_code_to_use}. MW={monitored_mw}.")
                if state_code_to_use:
                    region_data_found[state_code_to_use] = monitored_mw # Store MW
                # elif DEBUG: print(f"[PASS 1 WARN] Row {r}: Found TOTAL row but no state context!")

        # Insert collected/missing region data
        for state_code in sorted(list(all_state_codes)): # Insert in predictable order
            mw_value = region_data_found.get(state_code, None) # Get MW value or None
            try:
                # [REFINED v8] Insert MW value
                pass1_cursor.execute(sql_region, (state_code, report_iso, mw_value))
                inserted_count += 1
                # Reduced verbosity
                # if DEBUG and (mw_value is not None or state_code == 'CTG'):
                #      print(f"[PASS 1 INSERT] REGION_DETAILS: State={state_code}, MW={mw_value}")
            except mysql.connector.Error as err:
                 print(f"[DB ERROR - PASS 1] REGION_DETAILS insert failed for State={state_code}: {err}")
            except Exception as e:
                 print(f"[ERROR - PASS 1] REGION insert for State={state_code}: {e}")

        cnx.commit()
        if DEBUG: print(f"--- Pass 1 Complete ({report_iso}): Committed {inserted_count} REGION_DETAILS ---")

    except Exception as e:
        print(f"[ERROR - PASS 1] ({report_iso}) Error: {e}")
        if cnx.is_connected(): cnx.rollback() # Rollback on error
    finally:
        if pass1_cursor:
             try: pass1_cursor.close()
             except: pass # Ignore close errors

# ---------------------------
# MAIN PROCESSING FUNCTION (for a single file/date) - v11 Logic
# ---------------------------
def process_single_report(df, report_iso_date, db_connection):
    """Processes plants, units, prod logs, op status for a given DataFrame and date."""
    if DEBUG: print(f"\n--- Starting Pass 2: Plant/Unit Data for {report_iso_date} ---")
    cursor = None
    plants_inserted_updated = 0; prodlog_inserted_updated = 0; opstatus_inserted_updated = 0
    try:
        cursor = db_connection.cursor()

        # --- Header Detection ---
        keywords = {
            'MONITORED': ['MONITORED CAP', 'MONITORED\nCAP'], 'TODAYS_PROGRAM': ["TODAY'S\nPROGRAM", "TODAY'S PROGRAM"],
            'TODAYS_ACTUAL': ["TODAY'S\nACTUAL", "TODAY'S ACTUAL"], 'COAL_STOCK': ['COAL STOCK\nIN DAYS', 'COAL STOCK IN DAYS'],
            'UNDER_OUTAGE': ['CAP. UNDER\nOUTAGE', 'CAP. UNDER OUTAGE'], 'OUTAGE_DATE': ['OUTAGE DATE'],
            'EXPECTED_SYNC': ['EXPECTED DATE', 'SYNC. DATE', 'EXPECTED DATE /'], 'REMARKS': ['REMARKS']
        }
        found = find_header_columns_by_text(df, keywords, 14)

        # --- Fallback & Plant Column Detection ---
        fallback_needed=False; essential_cols=['MONITORED','TODAYS_PROGRAM','TODAYS_ACTUAL']
        if any(found.get(k) is None for k in essential_cols): fallback_needed=True
        if fallback_needed:
            if DEBUG: print("[DETECT] Headers missing; using numeric fallback.")
            numeric_counts = {c: sum(1 for r in range(12, min(150, len(df))) if safe_float(df.iat[r, c]) is not None) for c in range(df.shape[1])}
            sorted_cols = sorted(numeric_counts.items(), key=lambda x: x[1], reverse=True)
            monitored_guess = next((c for c, cnt in sorted_cols if c != 0 and cnt > 3), sorted_cols[0][0] if sorted_cols else 1)
            if found.get('MONITORED') is None: found['MONITORED'] = monitored_guess
            if found.get('TODAYS_PROGRAM') is None: found['TODAYS_PROGRAM'] = monitored_guess + 1 if monitored_guess + 1 < df.shape[1] else None
            if found.get('TODAYS_ACTUAL') is None: found['TODAYS_ACTUAL'] = monitored_guess + 2 if monitored_guess + 2 < df.shape[1] else None
            if found.get('COAL_STOCK') is None: found['COAL_STOCK'] = monitored_guess + 5 if monitored_guess + 5 < df.shape[1] else None
            if found.get('UNDER_OUTAGE') is None: found['UNDER_OUTAGE'] = monitored_guess + 7 if monitored_guess + 7 < df.shape[1] else None
            if found.get('OUTAGE_DATE') is None: found['OUTAGE_DATE'] = monitored_guess + 8 if monitored_guess + 8 < df.shape[1] else None
            if found.get('EXPECTED_SYNC') is None: found['EXPECTED_SYNC'] = monitored_guess + 10 if monitored_guess + 10 < df.shape[1] else None
            if found.get('REMARKS') is None: found['REMARKS'] = monitored_guess + 11 if monitored_guess + 11 < df.shape[1] else None
        
        # Reduced verbosity
        # if DEBUG: print(f"[INFO ({report_iso_date})] Column mapping:", {k:v for k,v in found.items()})
        if any(found.get(k) is None for k in ['MONITORED']):
             print(f"[ERROR ({report_iso_date})] MONITORED column not found! Skipping Pass 2.")
             return

        start_scan=10; string_score={c: sum(1 for r in range(start_scan, min(len(df),start_scan+150)) if isinstance(df.iat[r,c], str) and re.search(r'[a-zA-Z]',df.iat[r,c]) and len(df.iat[r,c]) > 2) for c in range(df.shape[1])}
        sorted_scores = sorted(string_score.items(), key=lambda x: x[1], reverse=True)
        if sorted_scores and sorted_scores[0][0] == 0 and sorted_scores[0][1] > 10: plant_col = 0
        else: best_plant_col=next((c for c, score in sorted_scores if c in [0,1]), -1); plant_col = best_plant_col if best_plant_col != -1 else next((c for c, score in sorted_scores if c > 2 and score > 0), 0)
        # if DEBUG: print(f"[DETECT ({report_iso_date})] Chosen plant_col = {plant_col}") # Reduced verbosity

        # --- SQL Templates ---
        sql_plant = """INSERT INTO POWERPLANTS (Plant_ID, Plant_Name, State_Code, Sector_ID, Type_ID) VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE Plant_Name=VALUES(Plant_Name), State_Code=VALUES(State_Code), Sector_ID=VALUES(Sector_ID), Type_ID=VALUES(Type_ID)"""
        sql_prod = """INSERT INTO PRODUCTIONLOG (Plant_ID, Log_Date, Operational_Capacity_MW, Todays_Actual_MU, Capable_Generation_MU, Coal_Stock_Days, Efficiency_Percentage) VALUES (%s, %s, %s, %s, %s, %s, NULL) ON DUPLICATE KEY UPDATE Operational_Capacity_MW=VALUES(Operational_Capacity_MW), Todays_Actual_MU=VALUES(Todays_Actual_MU), Capable_Generation_MU=VALUES(Capable_Generation_MU), Coal_Stock_Days=VALUES(Coal_Stock_Days), Efficiency_Percentage=VALUES(Efficiency_Percentage)"""
        sql_op = """INSERT INTO OPERATIONAL_STATUS (Plant_ID, Unit_Number, Status_Date, Cap_Under_Outage_MW, Status, Expected_Sync_Date, Remarks, Outage_Date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE Cap_Under_Outage_MW=VALUES(Cap_Under_Outage_MW), Status=VALUES(Status), Expected_Sync_Date=VALUES(Expected_Sync_Date), Remarks=VALUES(Remarks), Outage_Date=VALUES(Outage_Date)"""

        # --- State machine variables ---
        current_state_name = None; current_state_code = None
        current_sector_id = None; current_type_id = None
        current_plant_id = None
        
        # Get starting plant counter
        plant_counter = 1; temp_id_cursor = None
        try:
            temp_id_cursor = db_connection.cursor()
            temp_id_cursor.execute("SELECT MAX(CAST(Plant_ID AS UNSIGNED)) FROM POWERPLANTS")
            max_id_result = temp_id_cursor.fetchone()
            plant_counter = (max_id_result[0] if max_id_result[0] else 0) + 1
            # Reduced verbosity
            # if DEBUG: print(f"[DB INFO ({report_iso_date})] Starting plant counter at {plant_counter}")
        except Exception as e: print(f"[DB ERROR ({report_iso_date})] Could not get max Plant_ID: {e}. Starting counter at 1.")
        finally:
             if temp_id_cursor: temp_id_cursor.close()

        # --- Row Loop for Pass 2 ---
        rows = len(df)
        for r in range(rows):
            row_vals = [sanitize_string(df.iat[r, c]) if c < df.shape[1] else '' for c in range(df.shape[1])]
            combined = " ".join([x.upper() for x in row_vals if x])
            if combined.strip() == '': continue

            # --- Context Detection ---
            is_context_row = False; state_code_in_row = None
            # State Header
            matched_state = None
            for name, code in STATE_MAP.items():
                pattern = r'\b' + re.escape(name).replace('AND', '(?:AND|&)') + r'\b'
                if re.search(pattern, combined):
                    state_code_in_row = code
                    non_empty_cells = sum(1 for x in row_vals if x)
                    name_in_first_cols = any(name in (row_vals[c].upper() if c<len(row_vals) else '') for c in range(3))
                    if name_in_first_cols and non_empty_cells < 8:
                         current_state_name = name; current_state_code = code
                         current_sector_id, current_type_id, current_plant_id = None, None, None
                         is_context_row = True
                         # Reduced verbosity
                         # if DEBUG: print(f"\n[PASS 2 CTX] Row {r}: State -> {current_state_name} ({current_state_code})")
                         break
            # Sector Header
            if not is_context_row:
                matched_sector_key = next((k for k in SECTOR_MAP if k in combined), None)
                if not matched_sector_key:
                     m_sector = re.search(r'SECTOR[:\s]*([A-Z \.]{2,30})', combined)
                     if m_sector: cand=m_sector.group(1).strip(); matched_sector_key=next((k for k in SECTOR_MAP if k in cand or cand in k), None)
                if matched_sector_key: current_sector_id = SECTOR_MAP[matched_sector_key]; is_context_row = True
                # if DEBUG and is_context_row: print(f"[PASS 2 CTX] Row {r}: Sector -> {current_sector_id}")
            # Type Header
            if not is_context_row:
                matched_type_key = next((k for k in TYPE_MAP if k in combined), None)
                if matched_type_key: current_type_id = TYPE_MAP[matched_type_key]; is_context_row = True
                # if DEBUG and is_context_row: print(f"[PASS 2 CTX] Row {r}: Type -> {current_type_id}")

            if is_context_row: continue
            if re.search(r'\b(STATE|REGION)\s*TOTAL\b', combined): continue

            # --- Unit or Plant Logic ---
            plant_cell = sanitize_string(df.iat[r, plant_col]) if plant_col < df.shape[1] else ''
            plant_cell_up = plant_cell.upper()

            if plant_cell_up in CONTEXT_HEADER_KEYWORDS: continue

            is_unit = bool(UNIT_REGEX.match(plant_cell_up))
            unit_name_source = plant_cell # Original string like "Unit,1"
            unit_number_to_insert = 'N/A' # Default

            if not is_unit: # Check other columns
                for c in range(df.shape[1]):
                    if c == plant_col: continue
                    v = sanitize_string(df.iat[r, c])
                    if UNIT_REGEX.match(v.upper()): is_unit = True; unit_name_source = v; break

            # [REFINED v11] Extract number if it's a unit
            if is_unit:
                num_match = UNIT_NUMBER_EXTRACT_REGEX.search(unit_name_source)
                if num_match:
                    unit_number_to_insert = num_match.group(0) # e.g., '1', '6'
                # else: unit_number_to_insert remains 'N/A'

            # Process Unit Row (Conditional Insert for OS)
            if is_unit:
                if current_plant_id:
                    outage_mw = safe_float(df.iat[r, found.get('UNDER_OUTAGE')]) if found.get('UNDER_OUTAGE') is not None else None
                    expected_raw = df.iat[r, found.get('EXPECTED_SYNC')] if found.get('EXPECTED_SYNC') is not None else None
                    remarks_raw = df.iat[r, found.get('REMARKS')] if found.get('REMARKS') is not None else None
                    outage_date_raw = df.iat[r, found.get('OUTAGE_DATE')] if found.get('OUTAGE_DATE') is not None else None

                    expected_iso = parse_date_like(expected_raw)
                    outage_date_iso = parse_date_like(outage_date_raw)
                    remarks_clean = sanitize_string(remarks_raw)
                    outage_mw_to_insert = outage_mw # Always insert reported value

                    # [REFINED v11] Specific status logic
                    status_val_db = 'Active' # Default
                    insert_os_record = False # Flag to decide insertion

                    if remarks_clean and outage_date_iso:
                        status_val_db = 'Under Outage'
                        insert_os_record = True
                    elif remarks_clean and not outage_date_iso:
                        status_val_db = 'Not Commisioned' # Only remarks
                        insert_os_record = True
                    elif not remarks_clean and outage_date_iso:
                        status_val_db = 'Active' # Only date means Active
                        insert_os_record = True
                    # else: (no remarks, no outage date) -> Active, insert_os_record = False

                    # Insert status only if needed based on flags
                    if insert_os_record:
                        try:
                            cursor.execute(sql_op, (
                                current_plant_id, unit_number_to_insert, report_iso_date,
                                outage_mw_to_insert, status_val_db,
                                expected_iso, remarks_clean,
                                outage_date_iso
                            ))
                            opstatus_inserted_updated += 1
                            # Reduced verbosity
                            # if DEBUG: print(f"[PASS 2 INSERT] OP_STATUS (unit) plant={current_plant_id} unit='{unit_number_to_insert}' status='{status_val_db}'")
                        except Exception as e: print(f"[DB ERROR - PASS 2] OP_STATUS unit insert failed: {e}")
                    # else: # Implicitly Active - Do not insert
                    #     if DEBUG: print(f"[PASS 2 SKIP] OP_STATUS (unit) '{unit_name_source}' - Active, no outage details.")

                # Reduced verbosity
                # elif DEBUG: print(f"[PASS 2 SKIP] Row {r}: Unit '{unit_name_source}' no current_plant_id.")
                continue # Always skip unit rows from plant logic

            # Process Potential Plant Row
            monitored_val = safe_float(df.iat[r, found.get('MONITORED')]) if found.get('MONITORED') is not None else None
            is_valid_plant_name = bool(plant_cell) and len(plant_cell) >= 2 and re.search(r'[a-zA-Z]', plant_cell)
            is_potential_plant = is_valid_plant_name and (monitored_val is not None)

            if is_potential_plant:
                plant_name = plant_cell
                state_code_to_use = current_state_code
                if not state_code_to_use:
                     if state_code_in_row: state_code_to_use = state_code_in_row
                     # Reduced verbosity
                     # if DEBUG: print(f"[PASS 2 WARN] Row {r}: Using state '{state_code_to_use}' for plant '{plant_name}'")

                # Look up existing plant ID or generate new
                plant_id_to_use = None; temp_find_cursor = None; existing_plant = None
                try:
                    temp_find_cursor = db_connection.cursor(dictionary=True)
                    temp_find_cursor.execute("SELECT Plant_ID FROM POWERPLANTS WHERE Plant_Name = %s AND State_Code = %s", (plant_name, state_code_to_use))
                    existing_plant = temp_find_cursor.fetchone()
                    if existing_plant: plant_id_to_use = existing_plant['Plant_ID']
                    else: plant_id_to_use = str(plant_counter).zfill(3)
                except Exception as lookup_e: print(f"[DB ERROR - PASS 2] Plant lookup failed: {lookup_e}"); continue
                finally:
                    if temp_find_cursor: temp_find_cursor.close()

                # Insert/Update Plant
                try:
                    cursor.execute(sql_plant, (plant_id_to_use, plant_name, state_code_to_use, current_sector_id, current_type_id))
                    if not existing_plant: plant_counter += 1
                    current_plant_id = plant_id_to_use # Update context
                    plants_inserted_updated += 1
                    # Reduced verbosity
                    # if DEBUG: print(f"[PASS 2 UPSERT] POWERPLANT id={current_plant_id} name='{plant_name[:60]}'")
                except Exception as e: print(f"[DB ERROR - PASS 2] PLANT upsert failed for '{plant_name}': {e}"); continue

                # Insert Production Log
                prog_val=safe_float(df.iat[r, found.get('TODAYS_PROGRAM')]) if found.get('TODAYS_PROGRAM') is not None else None
                actual_val=safe_float(df.iat[r, found.get('TODAYS_ACTUAL')]) if found.get('TODAYS_ACTUAL') is not None else None
                coal_days=safe_float(df.iat[r, found.get('COAL_STOCK')]) if found.get('COAL_STOCK') is not None else None
                opcap_mw = monitored_val
                try:
                    cursor.execute(sql_prod, (current_plant_id, report_iso_date, opcap_mw, actual_val, prog_val, coal_days))
                    prodlog_inserted_updated +=1
                    # Reduced verbosity
                    # if DEBUG: print(f"[PASS 2 INSERT] PRODLOG plant={current_plant_id} opcap={opcap_mw}")
                except Exception as e: print(f"[DB ERROR - PASS 2] PRODLOG insert failed: {e}")

                # Insert Main Plant Operational Status (Conditional)
                main_outage_mw = safe_float(df.iat[r, found.get('UNDER_OUTAGE')]) if found.get('UNDER_OUTAGE') is not None else None
                expected_raw = df.iat[r, found.get('EXPECTED_SYNC')] if found.get('EXPECTED_SYNC') is not None else None
                remarks_raw = df.iat[r, found.get('REMARKS')] if found.get('REMARKS') is not None else None
                outage_date_raw = df.iat[r, found.get('OUTAGE_DATE')] if found.get('OUTAGE_DATE') is not None else None

                expected_iso = parse_date_like(expected_raw)
                outage_date_iso = parse_date_like(outage_date_raw)
                remarks_clean = sanitize_string(remarks_raw)
                outage_mw_to_insert = main_outage_mw # Always insert reported value

                # [REFINED v11] Specific status logic & conditional insert
                status_val_db = 'Active' # Default
                insert_os_record = False # Flag

                if remarks_clean and outage_date_iso:
                    status_val_db = 'Under Outage'
                    insert_os_record = True
                elif remarks_clean and not outage_date_iso:
                    if "NOT YET COMMISSIONED" in remarks_clean.upper():
                         status_val_db = 'Not Commisioned'
                    else:
                         status_val_db = 'Under Outage' # Remark implies issue
                    insert_os_record = True
                elif not remarks_clean and outage_date_iso:
                    status_val_db = 'Active' # Date only means Active
                    insert_os_record = True
                # else: (no remarks, no outage date) -> Active, insert_os_record = False

                # Insert status only if needed based on flags
                if insert_os_record:
                    try:
                        cursor.execute(sql_op, (
                            current_plant_id, 'Main', report_iso_date,
                            outage_mw_to_insert, status_val_db,
                            expected_iso, remarks_clean,
                            outage_date_iso
                         ))
                        opstatus_inserted_updated += 1
                        # Reduced verbosity
                        # if DEBUG: print(f"[PASS 2 INSERT] OP_STATUS (main) plant={current_plant_id} status='{status_val_db}'")
                    except Exception as e:
                        print(f"[DB ERROR - PASS 2] OP_STATUS main insert failed for {current_plant_id}: {e}")
                # else:
                #    if DEBUG: print(f"[PASS 2 SKIP] OP_STATUS (main) plant={current_plant_id} - Active, no details.")

                continue # Go to next row

            # --- Skip Row ---
            # Reduced verbosity
            # if DEBUG and r > 10:
            #      if combined.strip(): print(f"[PASS 2 SKIP] Row {r}: No specific match. Plant Cell: '{plant_cell}', Monitored: {monitored_val}.")


        # Commit after processing all rows for this file in Pass 2
        db_connection.commit()
        if DEBUG: print(f"--- Pass 2 Complete ({report_iso_date}): Committed Records ---")
        if DEBUG: print(f"    Plants Upserted: {plants_inserted_updated}")
        if DEBUG: print(f"    ProdLog Upserted: {prodlog_inserted_updated}")
        if DEBUG: print(f"    OpStatus Inserted/Updated: {opstatus_inserted_updated}")


    except Exception as e:
        print(f"[ERROR - PASS 2] ({report_iso_date}) An error occurred: {e}")
        if db_connection.is_connected():
            try: db_connection.rollback()
            except Exception as rb_err: print(f"[DB WARN] Rollback failed: {rb_err}")
    finally:
        # Close only the cursor used in this function pass
        if cursor:
             try: cursor.close()
             # Reduced verbosity
             # if DEBUG: print(f"[DB] Closed Pass 2 cursor for {report_iso_date}")
             except Exception as close_err:
                 print(f"[DB WARN] Error closing Pass 2 cursor for {report_iso_date}: {close_err}")


if __name__ == "__main__":

    print("\n================= MULTI-DAY DGR REPORT PROCESSOR (v11) =================")

    # --- Establish DB Connection ONCE ---
    main_cnx = None
    try:
        main_cnx = mysql.connector.connect(**DB_CONFIG)
        if DEBUG:
            print("[DB] Connected successfully.")

        # --- Find last processed date from DATE_DIM ---
        cursor = main_cnx.cursor()
        cursor.execute("SELECT MAX(Date) FROM DATE_DIM;")
        result = cursor.fetchone()
        if result and result[0]:
            last_date = result[0]
            start_date = last_date + timedelta(days=1)
            print(f"[INFO] Last processed date found in DB: {last_date}")
        else:
            start_date = datetime(2025, 8, 1).date()
            print(f"[INFO] No previous date found. Starting from {start_date}")
        cursor.close()

        # --- Collect all matching XLS files ---
        all_files = [
            f for f in os.listdir(REPORT_FOLDER)
            if re.match(r"dgr2-\d{4}-\d{2}-\d{2}\.xls$", f)
        ]
        if not all_files:
            print(f"[CRITICAL ERROR] No DGR XLS files found in folder: {REPORT_FOLDER}")
            exit(1)

        # Sort files by date
        file_dates = []
        for f in all_files:
            m = re.search(r"(\d{4}-\d{2}-\d{2})", f)
            if m:
                try:
                    dt = datetime.strptime(m.group(1), "%Y-%m-%d").date()
                    file_dates.append((dt, f))
                except ValueError:
                    continue
        file_dates.sort()

        # --- Filter files to process ---
        to_process = [(d, f) for (d, f) in file_dates if d >= start_date]
        if not to_process:
            print(f"[INFO] All reports up to date. Last date processed: {start_date - timedelta(days=1)}")
            exit(0)

        print(f"[INFO] Found {len(to_process)} files to process (from {to_process[0][0]} to {to_process[-1][0]}).")

        # --- Loop through each file and process sequentially ---
        for report_date, filename in to_process:
            fullpath = os.path.join(REPORT_FOLDER, filename)
            print(f"\n================ Processing {filename} ({report_date}) ================")

            if not os.path.exists(fullpath):
                print(f"[SKIP] File missing: {fullpath}")
                continue

            try:
                # --- Read Excel ---
                df_current = try_read_excel(fullpath)
                if df_current is None:
                    print(f"[ERROR] Could not read {filename}, skipping.")
                    continue

                # --- Insert date into DATE_DIM ---
                date_insert_success = False
                try:
                    temp_cursor_date = main_cnx.cursor()
                    yyyy, mm, dd = report_date.year, report_date.month, report_date.day
                    sql_date_main = """INSERT INTO DATE_DIM (`Date`, Day, Month, Year)
                                       VALUES (%s, %s, %s, %s)
                                       ON DUPLICATE KEY UPDATE `Date`=VALUES(`Date`)"""
                    temp_cursor_date.execute(sql_date_main, (report_date, dd, mm, yyyy))
                    main_cnx.commit()
                    date_insert_success = True
                except Exception as e:
                    print(f"[DB ERROR] Date insert failed for {report_date}: {e}")
                    main_cnx.rollback()
                finally:
                    temp_cursor_date.close()

                if not date_insert_success:
                    print(f"[SKIP] Skipping {filename} due to date insert failure.")
                    continue

                # --- Run Pass 1 ---
                pre_scan_for_region_data(df_current, report_date, None, main_cnx)

                # --- Run Pass 2 ---
                process_single_report(df_current, report_date, main_cnx)

                print(f"[DONE] Successfully processed {filename}")

            except Exception as e:
                print(f"[CRITICAL ERROR] While processing {filename}: {e}")
                continue  # Continue to next file

        print("\n================= ALL REPORTS PROCESSED SUCCESSFULLY =================")

    except mysql.connector.Error as err:
        print(f"[CRITICAL ERROR] Database error: {err}")
    except Exception as e:
        print(f"[CRITICAL ERROR] Unexpected error: {e}")
    finally:
        if main_cnx and main_cnx.is_connected():
            main_cnx.close()
            if DEBUG:
                print("[DB] Main connection closed.")