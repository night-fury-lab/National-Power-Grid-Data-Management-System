"""
integrated_web_scrapping.py

This script integrates the following components into one sequential workflow:
1. Daily Plant XLS Report Sync
2. Daily Renewable PDF Report Download
3. Renewable PDF Report Processing (PDF → Excel)
4. State-wise Daily Average CSV Computation

All original logic, messages, and folder structures are preserved.
"""

import os
import re
import time
import zipfile
import shutil
import urllib3
import pdfplumber
import pandas as pd
import requests
from io import StringIO
from datetime import datetime, timedelta
from requests.exceptions import RequestException, ConnectTimeout
from urllib3.exceptions import IncompleteRead

# -------------------------------------------------------------------
# 1️⃣ DAILY PLANT DETAILS (from daily_plant_details.py)
# -------------------------------------------------------------------

ZIP_URL = 'https://github.com/vanga/india-power-generation/raw/main/data/npp/daily-generation/raw/2025.zip'
DOWNLOAD_FOLDER = 'temp_download'
EXTRACT_FOLDER = 'temp_extract'
XLS_OUTPUT_FOLDER = 'Daily_Plant_Generation_XLS_Reports'
DOWNLOAD_FILE_PATH = os.path.join(DOWNLOAD_FOLDER, '2025.zip')

def setup_folders():
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    os.makedirs(EXTRACT_FOLDER, exist_ok=True)
    os.makedirs(XLS_OUTPUT_FOLDER, exist_ok=True)

def download_zip_file():
    print(f"Downloading zip file from {ZIP_URL}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(ZIP_URL, headers=headers, stream=True, timeout=60)
        response.raise_for_status()
        with open(DOWNLOAD_FILE_PATH, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Download complete.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading the file: {e}")
        return False

def extract_zip_file():
    print(f"Extracting {DOWNLOAD_FILE_PATH} to {EXTRACT_FOLDER}...")
    try:
        with zipfile.ZipFile(DOWNLOAD_FILE_PATH, 'r') as zip_ref:
            zip_ref.extractall(EXTRACT_FOLDER)
        print("Extraction complete.")
    except (zipfile.BadZipFile, Exception) as e:
        print(f"An error occurred during extraction: {e}")

def process_and_copy_files(start_date):
    print("Processing extracted files...")
    processed_count = 0
    data_folder = os.path.join(EXTRACT_FOLDER, '2025', 'xls')
    if not os.path.exists(data_folder):
        print(f"Error: Could not find the data folder at {data_folder}")
        return
    for filename in os.listdir(data_folder):
        if filename.endswith('.xls'):
            try:
                date_str_from_file = filename.replace('dgr2-', '').replace('.xls', '')
                file_date = datetime.strptime(date_str_from_file, '%Y-%m-%d').date()
                destination_filepath = os.path.join(XLS_OUTPUT_FOLDER, filename)
                if file_date >= start_date and not os.path.exists(destination_filepath):
                    print(f"  -> Found new report: {filename}. Copying...")
                    shutil.copy(os.path.join(data_folder, filename), destination_filepath)
                    print(f"     Saved as {destination_filepath}")
                    processed_count += 1
            except Exception as e:
                print(f"  -> Could not process file '{filename}'. Reason: {e}")
    if processed_count == 0:
        print("No new reports to process. Your local folder is up to date.")
    else:
        print(f"Successfully copied {processed_count} new reports.")

def cleanup():
    print("Cleaning up temporary files...")
    try:
        shutil.rmtree(DOWNLOAD_FOLDER)
        shutil.rmtree(EXTRACT_FOLDER)
        print("Cleanup complete.")
    except OSError as e:
        print(f"Error during cleanup: {e}")

def sync_daily_plant_reports():
    DEFAULT_START_DATE = datetime(2025, 8, 1).date()
    os.makedirs(XLS_OUTPUT_FOLDER, exist_ok=True)
    latest_date_found = None
    try:
        for filename in os.listdir(XLS_OUTPUT_FOLDER):
            if filename.startswith('dgr2-') and filename.endswith('.xls'):
                date_part = filename.replace('dgr2-', '').replace('.xls', '')
                file_date = datetime.strptime(date_part, '%Y-%m-%d').date()
                if latest_date_found is None or file_date > latest_date_found:
                    latest_date_found = file_date
    except Exception as e:
        print(f"Error scanning output directory: {e}")
    start_date = (latest_date_found + timedelta(days=1)) if latest_date_found else DEFAULT_START_DATE
    print(f"--- Starting Daily Report Sync ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
    print(f"Checking for new files from {start_date} onwards...")
    setup_folders()
    if download_zip_file():
        extract_zip_file()
        process_and_copy_files(start_date)
    cleanup()
    print("--- Sync Finished ---")


# -------------------------------------------------------------------
# 2️⃣ DAILY RENEWABLE DETAILS (from daily_renewable_details.py)
# -------------------------------------------------------------------

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def download_cea_report(session, target_date):
    day_str = str(target_date.day)
    month_str = target_date.strftime("%b")
    year_str = target_date.strftime("%Y")
    base_url = "https://cea.nic.in/wp-content/uploads/daily_reports/"
    file_name = f"{day_str}_{month_str}_{year_str}_Daily_RE_Generation_Report.pdf"
    download_url = f"{base_url}{file_name}"
    local_filepath = os.path.join('Daily_Renewable_PDF_Reports', file_name)
    if os.path.exists(local_filepath):
        print(f"✅ Already exists. Skipping: {file_name}")
        return
    max_retries, retry_delay = 3, 3
    for attempt in range(max_retries):
        print(f"Attempting to download: {file_name} (Attempt {attempt + 1}/{max_retries})")
        try:
            response = session.get(download_url, stream=True, timeout=(10, 30))
            if response.status_code == 200:
                os.makedirs('Daily_Renewable_PDF_Reports', exist_ok=True)
                with open(local_filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"✅ Success! Report saved as: {local_filepath}")
                return
            elif response.status_code == 404:
                print("❌ File not found (404). Report may not exist for this date.")
                return
            else:
                print(f"❌ Server error (Status {response.status_code}).")
        except Exception as e:
            print(f"❌ Connection error: {e}")
        if attempt < max_retries - 1:
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            print("❌ Max retries exceeded. Failed to download this file.")

def download_renewable_pdfs():
    DOWNLOAD_DIR = 'Daily_Renewable_PDF_Reports'
    DEFAULT_START_DATE = datetime(2025, 8, 1).date()
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    latest_date_found = None
    try:
        for filename in os.listdir(DOWNLOAD_DIR):
            if filename.endswith("_Daily_RE_Generation_Report.pdf"):
                date_part = filename.replace("_Daily_RE_Generation_Report.pdf", "")
                file_date = datetime.strptime(date_part, "%d_%b_%Y").date()
                if latest_date_found is None or file_date > latest_date_found:
                    latest_date_found = file_date
    except Exception as e:
        print(f"Error scanning directory: {e}")
    start_date = (latest_date_found + timedelta(days=1)) if latest_date_found else DEFAULT_START_DATE
    end_date = datetime.now().date()
    if start_date > end_date:
        print(f"All reports are up to date. Last file found: {latest_date_found}")
        return
    with requests.Session() as session:
        session.headers.update({'User-Agent': 'Mozilla/5.0'})
        session.verify = False
        print(f"--- Starting download from {start_date} to {end_date} ---")
        current_date = start_date
        while current_date <= end_date:
            print(f"\nProcessing date: {current_date.strftime('%Y-%m-%d')}")
            download_cea_report(session, current_date)
            time.sleep(2)
            current_date += timedelta(days=1)
    print("\n--- Download complete. ---")


# -------------------------------------------------------------------
# 3️⃣ DAILY RENEWABLE PROCESS (from daily_renewable_process.py)
# -------------------------------------------------------------------

def process_renewable_pdfs():
    PDF_DIR = "Daily_Renewable_PDF_Reports"
    OUTPUT_DIR = "Processed_Renewable_XLSX_reports"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    hindi_to_english = {"चडंीगढ़":"Chandigarh","दिल्ली":"Delhi","हररयजणज":"Haryana","दहमजचल प्रिेश":"Himachal Pradesh","र्म्मू और कश्मीर":"Jammu and Kashmir","लद्िजख़":"Ladakh","परं्जब":"Punjab","रजर्स्थजन":"Rajasthan","उत्तर प्रिेश":"Uttar Pradesh","उत्तरजखडं":"Uttarakhand","उत्तरी के्षत्र":"Northern Region","गरु्रजत":"Gujarat","छत्तीसगढ़":"Chhattisgarh","मध्य प्रिेश":"Madhya Pradesh","महजरजष्ट्र":"Maharashtra","आधं्र प्रिेश":"Andhra Pradesh","तलेगंजनज":"Telangana","कनजाटक":"Karnataka","केरल":"Kerala","तममलनजडु":"Tamil Nadu","पवूी के्षत्र":"Eastern Region","पश्श्चमी के्षत्र":"Western Region","िक्षक्षणी के्षत्र":"Southern Region","उत्तर-पवूी के्षत्र":"North Eastern Region","सम्पणूा भजरत":"All India"}
    print(f"--- Starting PDF Processing ---")
    for filename in os.listdir(PDF_DIR):
        if not filename.endswith(".pdf"):
            continue
        pdf_path = os.path.join(PDF_DIR, filename)
        output_filename = filename.replace(".pdf", "_cleaned.xlsx")
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        if os.path.exists(output_path):
            print(f"\n⏭️  Skipping '{filename}' (already processed).")
            continue
        print(f"\n--- Processing '{filename}' ---")
        summary_data, station_data = [], []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                print(f"🔍 Found {total_pages} pages in PDF")
                for i, page in enumerate(pdf.pages):
                    if i == total_pages - 1:
                        print(f"⏭️  Skipping last page ({i+1})...")
                        continue
                    print(f"📄 Processing page {i+1}/{total_pages}...")
                    table = page.extract_table()
                    if not table:
                        print(f"⚠️  No table found on page {i+1}")
                        continue
                    if i == 0:
                        for row in table:
                            if len(row) >= 9:
                                state = row[0]
                                if state:
                                    for hindi, eng in hindi_to_english.items():
                                        if hindi in state:
                                            state = eng
                                            break
                                    wind, solar, others, total = row[1:5]
                                    summary_data.append([state, wind, solar, others, total])
                    else:
                        for row in table:
                            if row and len(row) >= 8:
                                cleaned = [cell if cell else "" for cell in row[:7]]
                                station_data.append(cleaned)
            df_summary = pd.DataFrame(summary_data, columns=["State / Region","Wind Energy","Solar Energy","Others RES","Total"])
            df_station = pd.DataFrame(station_data, columns=["Station","State / Region","Sector","Owner","Type","Operational Capacity","Actual Generation"])
            df_summary = df_summary[df_summary['State / Region']!='State / Region']
            df_station = df_station[df_station['Station']!='Station']
            if df_summary.empty and df_station.empty:
                print(f"⚠️  No data extracted from '{filename}'.")
                continue
            with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                df_summary.to_excel(writer, sheet_name="Summary (State Data)", index=False)
                df_station.to_excel(writer, sheet_name="Stations (Plant Data)", index=False)
            print(f"✅ Extraction complete! File saved as: {output_path}")
        except Exception as e:
            print(f"❌ ERROR processing '{filename}': {e}")
            if os.path.exists(output_path):
                os.remove(output_path)
    print("\n--- All PDF processing complete. ---")


# -------------------------------------------------------------------
# 4️⃣ STATE DAILY AVERAGE (from daily_state_average.py)
# -------------------------------------------------------------------

BASE_URL = "https://raw.githubusercontent.com/vanga/india-power-generation/main/data/meritindia/current-generation/raw/{year}-{month:02d}.csv"
OUTPUT_FILE = "state_daily_avg.csv"

def download_monthly_csv(year, month):
    url = BASE_URL.format(year=year, month=month)
    print(f"🔽 Fetching data from: {url}")
    response = requests.get(url)
    if response.status_code != 200:
        print(f"⚠️  No data found for {year}-{month:02d}")
        return pd.DataFrame()
    df = pd.read_csv(StringIO(response.text))
    print(f"✅ Fetched {len(df)} records for {year}-{month:02d}")
    return df

def detect_datetime_column(columns):
    for c in columns:
        if any(x in c.lower() for x in ["date","time","datetime"]):
            return c
    return None

def compute_daily_average(df):
    df.columns = [col.strip() for col in df.columns]
    datetime_col = detect_datetime_column(df.columns)
    if not datetime_col:
        print(f"⚠️ No datetime-like column found. Available: {list(df.columns)}")
        return pd.DataFrame()
    state_col = next((c for c in df.columns if "state" in c.lower() and "code" in c.lower()), None)
    numeric_cols = [c for c in df.columns if any(k.lower() in c.lower() for k in ["Demand","ISGS","Import","Generation"])]
    if not state_col or not numeric_cols:
        print(f"⚠️ Missing required columns.")
        return pd.DataFrame()
    print(f"🕓 Using datetime column: {datetime_col}")
    df[datetime_col] = pd.to_datetime(df[datetime_col], errors="coerce")
    df = df.dropna(subset=[datetime_col])
    df["Date"] = df[datetime_col].dt.date
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(r"[^0-9\.\-]","",regex=True).replace("",None),errors="coerce")
    grouped = df.groupby([state_col,"Date"],as_index=False)[numeric_cols].mean(numeric_only=True).round(2)
    rename_map = {c:f"Avg_{c}" for c in numeric_cols}
    grouped.rename(columns=rename_map,inplace=True)
    print(f"📊 Computed daily averages.")
    return grouped

def update_local_csv(new_data):
    if os.path.exists(OUTPUT_FILE):
        old = pd.read_csv(OUTPUT_FILE)
        old["Date"]=pd.to_datetime(old["Date"]).dt.date
        combined = pd.concat([old,new_data],ignore_index=True)
        combined.drop_duplicates(subset=["Date","StateCode"],keep="last",inplace=True)
        combined.sort_values(by=["Date"],inplace=True)
    else:
        combined = new_data
    combined.to_csv(OUTPUT_FILE,index=False)
    print(f"💾 Updated local file: {OUTPUT_FILE}")

def compute_state_daily_averages():
    print("🚀 Starting Renewable Energy Data Fetching...")
    last_processed=None
    if os.path.exists(OUTPUT_FILE):
        df=pd.read_csv(OUTPUT_FILE)
        if not df.empty:
            last_processed=pd.to_datetime(df["Date"]).max().date()
            print(f"📆 Last processed date: {last_processed}")
    start_year,start_month=2025,8
    current_year,current_month=datetime.now().year,datetime.now().month
    all_data=[]
    for year in range(start_year,current_year+1):
        for month in range(1,13):
            if (year==start_year and month<start_month) or (year==current_year and month>current_month):
                continue
            df=download_monthly_csv(year,month)
            if df.empty: continue
            df_avg=compute_daily_average(df)
            if df_avg.empty: continue
            if last_processed:
                df_avg=df_avg[df_avg["Date"]>last_processed]
                if df_avg.empty: continue
            all_data.append(df_avg)
    if all_data:
        update_local_csv(pd.concat(all_data,ignore_index=True))
    else:
        print("✅ No new data found.")
    print("🎯 All processing complete.")


# -------------------------------------------------------------------
# MAIN SEQUENCE
# -------------------------------------------------------------------

def main():
    print("\n================= INTEGRATED WEB SCRAPPING PIPELINE =================")
    sync_daily_plant_reports()
    download_renewable_pdfs()
    process_renewable_pdfs()
    compute_state_daily_averages()
    print("\n================= PIPELINE EXECUTION COMPLETE =================")

if __name__ == "__main__":
    main()
