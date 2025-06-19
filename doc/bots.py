import multiprocessing
import os
import subprocess
import sys
import uvicorn
import time
import logging
import json
import requests
import pyotp
import sqlite3
import pandas as pd
import glob
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
from datetime import datetime, date, timedelta
from typing import Optional
from kiteconnect import KiteConnect
import argparse

# --- Setup ---
load_dotenv()
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BotManager")

# --- Configuration ---
STRATEGY_DIR = os.getenv("STRATEGY_DIR", "strategies")
SESSION_FILE = "session_cache.json"
DB_NAME = "master_stocks.db"
API_KEY = os.getenv("KITE_API_KEY")
API_SECRET = os.getenv("KITE_API_SECRET")
USER_ID = os.getenv("KITE_USER_ID")
PASSWORD = os.getenv("KITE_PASSWORD")
TOTP_KEY = os.getenv("KITE_TOTP_KEY")

BOT_CONFIGS = [
    {"strategy_tag": "nifty_100", "port": 8001},
    {"strategy_tag": "nifty_mid_cap_100", "port": 8002},
    {"strategy_tag": "nifty_small_cap_100", "port": 8003},
]

# --- Helper Functions ---

def perform_master_login() -> Optional[KiteConnect]:
    logger.info("--- Starting Master Login Process ---")
    try:
        session = requests.Session()
        r1 = session.post("https://kite.zerodha.com/api/login", data={"user_id": USER_ID, "password": PASSWORD})
        r1.raise_for_status()
        request_id = r1.json()["data"]["request_id"]
        r2 = session.post("https://kite.zerodha.com/api/twofa", data={"user_id": USER_ID, "request_id": request_id, "twofa_value": pyotp.TOTP(TOTP_KEY).now()})
        r2.raise_for_status()
        logger.info("Master Login: 2FA successful.")
        
        api_url = f"https://kite.trade/connect/login?api_key={API_KEY}&v=3"
        final_url_with_token = ""
        try:
            response = session.get(api_url, timeout=10)
            final_url_with_token = response.url
        except requests.exceptions.ConnectionError as e:
            final_url_with_token = e.request.url
        
        request_token = parse_qs(urlparse(final_url_with_token).query)["request_token"][0]
        
        kite = KiteConnect(api_key=API_KEY)
        session_data = kite.generate_session(request_token, api_secret=API_SECRET)
        access_token = session_data.get("access_token")
        if not access_token: raise ValueError("Failed to acquire access_token.")
        
        if "login_time" in session_data and isinstance(session_data["login_time"], datetime):
            session_data["login_time"] = session_data["login_time"].isoformat()
        with open(SESSION_FILE, 'w') as f:
            json.dump(session_data, f, indent=4)
        
        logger.info(f"--- Master Login Successful. Session saved to {SESSION_FILE} ---")
        kite.set_access_token(access_token)
        return kite
    except Exception as e:
        logger.error(f"--- Master Login Failed Critically: {e} ---")
        return None

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS instruments (
                instrument_token INTEGER PRIMARY KEY, exchange_token TEXT, tradingsymbol TEXT NOT NULL,
                name TEXT, exchange TEXT, instrument_type TEXT, segment TEXT,
                lot_size INTEGER, pair TEXT NOT NULL, tags TEXT
            )
        """)
        cursor.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)")
        conn.commit()
    logger.info("Database initialized successfully.")

def get_last_update_date() -> Optional[date]:
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM metadata WHERE key = 'last_update'")
            result = cursor.fetchone()
            if result: return date.fromisoformat(result[0])
    except sqlite3.Error: return None
    return None

def set_last_update_date():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)", ('last_update', date.today().isoformat()))
        conn.commit()
    logger.info("Set last instrument update date to: %s", date.today().isoformat())

def is_instrument_data_stale() -> bool:
    last_update = get_last_update_date()
    if not last_update: return True
    today = date.today()
    most_recent_thursday = today - timedelta(days=((today.weekday() - 3 + 7) % 7))
    return last_update < most_recent_thursday

# Replace the existing function with this corrected version

def load_all_whitelists() -> dict:
    """
    Scans the strategy directory, loads all .json whitelists,
    and extracts the 'ticker' value from the list of objects.
    """
    whitelists = {}
    path = os.path.join(STRATEGY_DIR, '*.json')
    for filename in glob.glob(path):
        tag = os.path.splitext(os.path.basename(filename))[0]
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                
                # --- THIS IS THE MODIFIED LOGIC ---
                # Instead of a list of strings, we now have a list of objects.
                # We use a set comprehension to extract the 'ticker' value from each object.
                symbols_list_of_dicts = data.get("symbols", [])
                symbols = {item['ticker'] for item in symbols_list_of_dicts if 'ticker' in item}
                # --- END OF MODIFICATION ---
                
                whitelists[tag] = symbols
                logger.info(f"Loaded whitelist '{tag}' with {len(symbols)} symbols.")
        except Exception as e:
            logger.error(f"Failed to load or parse {filename}: {e}")
    return whitelists

def populate_instruments_from_kite(kite: KiteConnect):
    whitelists = load_all_whitelists()
    if not whitelists:
        logger.error(f"No whitelists found in '{STRATEGY_DIR}' directory. Aborting population.")
        return

    logger.info("Fetching full instrument list from Kite API...")
    instrument_dump = kite.instruments("NSE")
    df = pd.DataFrame(instrument_dump)

    def get_instrument_tags(tradingsymbol: str) -> str:
        instrument_tags = [tag for tag, symbols in whitelists.items() if tradingsymbol in symbols]
        return ",".join(instrument_tags)

    logger.info("Tagging all instruments based on loaded whitelists...")
    df['tags'] = df['tradingsymbol'].apply(get_instrument_tags)

    df = df[df['tags'] != '']
    logger.info(f"Found and tagged a total of {len(df)} instruments from all whitelists.")

    df['pair'] = df['tradingsymbol'] + '/INR'
    df_to_db = df[['instrument_token', 'exchange_token', 'tradingsymbol', 'name', 'exchange', 'instrument_type', 'segment', 'lot_size', 'pair', 'tags']]
    
    with sqlite3.connect(DB_NAME) as conn:
        df_to_db.to_sql('instruments', conn, if_exists='replace', index=False)
    logger.info("Master database population with tagged instruments is complete.")

def start_bridge_instance(config: dict):
    tag = config['strategy_tag']
    port = config['port']
    os.environ['STRATEGY_TAG'] = tag
    uvicorn.run("kite-bridge:app", host="0.0.0.0", port=port, log_level="info")

# --- Main Execution Block ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bot Manager: Run trading bots or initialize the historical database from local files.")
    parser.add_argument(
        '--init-db',
        action='store_true',
        help='Run the historical data importer from local CSV files, then exit.'
    )
    args = parser.parse_args()

    # Decide mode based on the --init-db flag
    if args.init_db:
        # --- LOCAL DATABASE INITIALIZATION MODE ---
        logger.info("Running in --init-db mode to import local CSV data.")
        
        # Call the external downloader/importer script.
        # This mode no longer requires a login.
        logger.info("Starting external data import script...")
        try:
            downloader_script_path = "download_historical_data.py"
            # Execute the script and wait for it to complete.
            result = subprocess.run([sys.executable, downloader_script_path], check=True)
            logger.info("Local data import script finished successfully.")
        except FileNotFoundError:
            logger.error(f"Could not find the script at '{downloader_script_path}'. Aborting.")
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            logger.error(f"The data import script failed with exit code {e.returncode}. Aborting.")
            sys.exit(1)
            
        logger.info("Database initialization from local files is finished.")
        sys.exit(0)

    else:
        # --- BOT RUN MODE ---
        logger.info("Running in Bot Launch mode.")
        
        # Login is only required when running the bots
        kite_client = perform_master_login()
        if not kite_client:
            logger.critical("Could not log in. Aborting bot launch.")
            sys.exit(1)

        # Check and update master instrument list if needed
        init_db()
        if is_instrument_data_stale():
            logger.info("Instrument data is stale, proceeding with update...")
            populate_instruments_from_kite(kite_client)
            set_last_update_date()
        else:
            logger.info("Instrument data is fresh, no update needed.")

        # Launch bridge instances for each bot
        # (This part of your code remains unchanged)
        logger.info(f"Setup complete. Now launching {len(BOT_CONFIGS)} bridge instances...")
        processes = []
        for config in BOT_CONFIGS:
            process = multiprocessing.Process(target=start_bridge_instance, args=(config,))
            processes.append(process)
            process.start()

        try:
            for process in processes:
                process.join()
        except KeyboardInterrupt:
            # (Your shutdown logic remains unchanged)
            logger.info("\nShutdown signal received. Terminating all bridge instances...")
            for process in processes:
                process.terminate()
                process.join()
            if os.path.exists(SESSION_FILE):
                os.remove(SESSION_FILE)
            logger.info("All processes shut down and session file cleaned up.")