import os
import logging
import threading
import time
import sqlite3
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date
from contextlib import asynccontextmanager
from urllib.parse import urlparse, parse_qs
import re
import pandas as pd
import pyotp
import requests
import pytz
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from kiteconnect import KiteConnect
import json

# --- Setup ---
load_dotenv()
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("API-Bridge")

# --- Configuration ---
STRATEGY_TAG = os.getenv("STRATEGY_TAG")
DB_NAME = "master_stocks.db"
SESSION_FILE = "session_cache.json"
API_KEY = os.getenv("KITE_API_KEY")

# --- Configuration Switch ---
DRY_RUN_ENABLED = os.getenv("BRIDGE_DRY_RUN", "false").lower() == "true"




KITE_HISTORICAL_LIMITS = {
    "minute": 60, "3minute": 100, "5minute": 100, "10minute": 100,
    "15minute": 200, "30minute": 200, "60minute": 400, "day": 2000,
}

# --- Database & Scraper Helper Functions ---

def init_data_db():
    """Initializes the historical OHLCV data database."""
    db_name = "historical_data.db"
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        # This table will store all candle data for all instruments and timeframes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv_data (
                instrument_token INTEGER NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER NOT NULL,
                PRIMARY KEY (instrument_token, timeframe, timestamp)
            )
        """)
        conn.commit()
    logger.info(f"Historical data database '{db_name}' initialized successfully.")

def init_db():
    """Initializes the database and creates tables with the new 'tags' column."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Add the 'tags TEXT' field to the table definition
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
    except sqlite3.Error as e: logger.error(f"DB error getting last update date: {e}")
    return None

def set_last_update_date():
    today_str = date.today().isoformat()
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)", ('last_update', today_str))
            conn.commit()
        logger.info("Set last instrument update date to: %s", today_str)
    except sqlite3.Error as e: logger.error(f"DB error setting last update date: {e}")

def is_instrument_data_stale() -> bool:
    last_update = get_last_update_date()
    if not last_update:
        logger.info("No last update date found. Data is considered stale.")
        return True
    today = date.today()
    days_since_thursday = (today.weekday() - 3 + 7) % 7
    most_recent_thursday = today - timedelta(days=days_since_thursday)
    if last_update < most_recent_thursday:
        logger.info(f"Data is stale. Last update {last_update} was before last Thursday {most_recent_thursday}.")
        return True
    logger.info(f"Instrument data is fresh. Last updated on {last_update}.")
    return False

def fetch_index_constituents(index_name: str) -> set:
    """Dynamically fetches constituent stock symbols for an index from the NSE website."""
    logger.info(f"Fetching constituents for {index_name}...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    index_urls = {
        "NIFTY 50": "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050",
        "NIFTY NEXT 50": "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20NEXT%2050"
    }
    url = index_urls.get(index_name)
    if not url: return set()
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        symbols = {item['symbol'] for item in response.json()['data']}
        logger.info(f"Successfully fetched {len(symbols)} symbols for {index_name}.")
        return symbols
    except Exception as e:
        logger.error(f"Failed to fetch data for index {index_name}. Error: {e}")
        return set()

def populate_instruments_from_kite(kite: KiteConnect):
    """Fetches instruments from Kite, filters for NIFTY 100, and populates the DB."""
    nifty50_symbols = fetch_index_constituents("NIFTY 50")
    niftynext50_symbols = fetch_index_constituents("NIFTY NEXT 50")
    if not nifty50_symbols or not niftynext50_symbols:
        logger.error("Could not fetch index lists. Aborting instrument population.")
        return
    nifty100_symbols = nifty50_symbols.union(niftynext50_symbols)
    logger.info(f"Total unique symbols in dynamic NIFTY 100 list: {len(nifty100_symbols)}.")

    logger.info("Fetching full instrument list from Kite API...")
    instrument_dump = kite.instruments("NSE")
    df = pd.DataFrame(instrument_dump)

    df = df[(df['instrument_type'] == 'EQ') & (df['tradingsymbol'].isin(nifty100_symbols))]
    logger.info(f"Filtered down to {len(df)} NIFTY 100 equity instruments.")

    df['pair'] = df['tradingsymbol'] + '/INR'
    
    df_to_db = df[['instrument_token', 'exchange_token', 'tradingsymbol', 'name', 'exchange', 'instrument_type', 'segment', 'lot_size', 'pair']]
    with sqlite3.connect(DB_NAME) as conn:
        df_to_db.to_sql('instruments', conn, if_exists='replace', index=False)
    logger.info("Database population with filtered list is complete.")

def load_instruments_from_db() -> Optional[pd.DataFrame]:
    if not os.path.exists(DB_NAME): return None
    with sqlite3.connect(DB_NAME) as conn:
        try:
            return pd.read_sql_query("SELECT * FROM instruments", conn)
        except pd.io.sql.DatabaseError:
            return None

# --- Automated Login & Lifespan ---
# In main.py, replace the existing function with this one

def auto_login_and_trigger_callback():
    """
    Performs the full automated login and manually triggers the correct callback URL.
    """
    try:
        session = requests.Session()
        # Get the port for the current instance from the environment variable we set
        current_port = os.environ.get('PORT')
        if not current_port:
            logger.error("[BACKGROUND-LOGIN] CRITICAL: PORT environment variable not set for this instance.")
            return

        logger.info(f"[BACKGROUND-LOGIN on Port {current_port}] Starting automated login for user: {USER_ID}")

        # Step 1 & 2: Login and 2FA (same as before)
        request_id_payload = {"user_id": USER_ID, "password": PASSWORD}
        r1 = session.post("https://kite.zerodha.com/api/login", data=request_id_payload, timeout=15)
        r1.raise_for_status()
        request_id = r1.json()["data"]["request_id"]

        twofa_payload = {"user_id": USER_ID, "request_id": request_id, "twofa_value": pyotp.TOTP(TOTP_KEY).now()}
        r2 = session.post("https://kite.zerodha.com/api/twofa", data=twofa_payload, timeout=15)
        r2.raise_for_status()
        logger.info(f"[BACKGROUND-LOGIN on Port {current_port}] Login and 2FA successful.")

        # --- NEW LOGIC: Intercept and Correct Redirect ---

        # Step 3: Make the request but DO NOT follow the redirect automatically
        api_session_url = f"https://kite.trade/connect/login?api_key={API_KEY}&v=3"
        logger.info(f"[BACKGROUND-LOGIN on Port {current_port}] Intercepting redirect from URL: {api_session_url}")
        redirect_response = session.get(api_session_url, allow_redirects=False, timeout=15)

        # Step 4: Extract the incorrect redirect URL and get the request_token
        incorrect_redirect_url = redirect_response.headers['Location']
        parsed_url = urlparse(incorrect_redirect_url)
        request_token = parse_qs(parsed_url.query)["request_token"][0]
        logger.info(f"[BACKGROUND-LOGIN on Port {current_port}] Successfully extracted request_token.")

        # Step 5: Build the CORRECT callback URL and make the final request ourselves
        correct_callback_url = f"http://127.0.0.1:{current_port}/api/callback"
        final_params = {'request_token': request_token}
        
        logger.info(f"[BACKGROUND-LOGIN on Port {current_port}] Manually triggering correct callback: {correct_callback_url}")
        final_response = requests.get(correct_callback_url, params=final_params, timeout=15)
        final_response.raise_for_status()
        
        logger.info(f"[BACKGROUND-LOGIN on Port {current_port}] Callback successful. Login complete.")

    except Exception as e:
        logger.error(f"[BACKGROUND-LOGIN on Port {os.environ.get('PORT', 'UNKNOWN')}] The automated login process failed critically: {e}")

def run_login_in_background():
    logger.info("Background thread started. Waiting 5s for server to ready...")
    time.sleep(5)
    auto_login_and_trigger_callback()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"[{STRATEGY_TAG}] Bridge instance starting up...")
    
    app.state.kite = KiteConnect(api_key=API_KEY)
    app.state.access_token = None
    app.state.strategy_instruments_df = None
    
    try:
        with open(SESSION_FILE, 'r') as f:
            session_data = json.load(f)
        access_token = session_data.get("access_token")

        if access_token:
            app.state.access_token = access_token
            app.state.kite.set_access_token(access_token)
            logger.info(f"[{STRATEGY_TAG}] Successfully loaded access token.")
            
            master_df = load_instruments_from_db()
            if master_df is not None and not master_df.empty:
                logger.info(f"[{STRATEGY_TAG}] Filtering master instrument list for tag: '{STRATEGY_TAG}'")
                app.state.strategy_instruments_df = master_df[
                    master_df['tags'].str.contains(STRATEGY_TAG, na=False)
                ]
                logger.info(f"[{STRATEGY_TAG}] This bot instance will operate on {len(app.state.strategy_instruments_df)} instruments. Bridge is ready.")
            else:
                logger.warning(f"[{STRATEGY_TAG}] Could not load instruments from database, or database is empty.")
        else:
            logger.error(f"[{STRATEGY_TAG}] Session file found, but access_token is missing.")
    except FileNotFoundError:
        logger.error(f"[{STRATEGY_TAG}] CRITICAL: Session file '{SESSION_FILE}' not found.")
    except Exception as e:
        logger.error(f"[{STRATEGY_TAG}] An error occurred during startup: {e}", exc_info=True)
        
    yield
    logger.info(f"[{STRATEGY_TAG}] Server shutting down.")

# --- FastAPI App & Endpoints ---
app = FastAPI(title=f"Kite Bridge - {STRATEGY_TAG}", version="7.0.0", lifespan=lifespan)

@app.get("/api/callback", summary="Automated Login Callback")
async def api_callback(request_token: str):
    logger.info("[CALLBACK] Received request_token. Generating session...")
    try:
        session_data = app.state.kite.generate_session(request_token, api_secret=API_SECRET)
        app.state.access_token = session_data.get("access_token")
        app.state.kite.set_access_token(app.state.access_token)
        logger.info("[CALLBACK] Access Token generated successfully.")
        if is_instrument_data_stale():
            populate_instruments_from_kite(app.state.kite)
            set_last_update_date()
        app.state.instruments_df = load_instruments_from_db()
        logger.info("[CALLBACK] Bridge is now fully operational.")
        return {"status": "success"}
    except Exception as e:
        logger.error("[CALLBACK] Critical failure during callback handling: %s", e)
        return {"status": "error", "message": str(e)}

@app.get("/health", summary="Health Check")
async def health_check():
    is_ready = False
    if DRY_RUN_ENABLED:
        is_ready = app.state.instruments_df is not None and not app.state.instruments_df.empty
    else:
        is_ready = app.state.access_token is not None and app.state.instruments_df is not None and not app.state.instruments_df.empty
    return {"status": "ok", "mode": "dry_run" if DRY_RUN_ENABLED else "live", "bridge_ready": is_ready}

def get_instrument_token(df: pd.DataFrame, pair: str) -> Optional[int]:
    if not isinstance(df, pd.DataFrame) or df.empty: return None
    try:
        instrument = df[df.pair == pair]
        return int(instrument.iloc[0]['instrument_token']) if not instrument.empty else None
    except Exception as e:
        logger.error(f"Error finding instrument token for {pair}: {e}")
    return None

# Add this entire function to your kite-bridge.py script

@app.get("/account/v1/currencies", summary="Mock Currencies Endpoint for CCXT")
async def fetch_currencies():
    """
    CCXT calls this endpoint during initialization to get a list of available currencies.
    This bridge isn't a real crypto exchange, so we return a minimal list containing
    our quote currency, 'INR', to satisfy the library's requirement.
    The response format mimics the real BitMart API.
    """
    logger.info("Serving mock currency data for CCXT initialization.")
    return {
        "message": "OK",
        "code": 1000,
        "trace": str(uuid.uuid4()),
        "data": {
            "currencies": [
                {
                    "currency": "INR",
                    "name": "Indian Rupee",
                    "chain": "INR", # Not relevant for us, but good to have a value
                    "full_name": "Indian Rupee",
                    "precision": "2",
                    "deposit_enabled": True,
                    "withdraw_enabled": True,
                }
            ]
        }
    }

# Replace your existing fetch_markets function with this one.

# Replace your existing fetch_markets_for_ccxt function with this updated one.
# The path must be /spot/v1/symbols/details

@app.get("/spot/v1/symbols/details", summary="Fetch Available Markets for Freqtrade")
async def fetch_markets_for_ccxt():
    """
    Returns the list of tradable pairs in a raw format that precisely mimics the real
    BitMart API's /spot/v1/symbols/details endpoint. CCXT will fetch this raw data
    and parse it into the format that Freqtrade uses.
    """
    if app.state.strategy_instruments_df is None or app.state.strategy_instruments_df.empty:
        logger.warning(f"[{STRATEGY_TAG}] /spot/v1/symbols/details called but instruments are not loaded.")
        raise HTTPException(status_code=503, detail="Instruments not loaded yet.")

    logger.info(f"[{STRATEGY_TAG}] Building and serving ACCURATE raw market data for {len(app.state.strategy_instruments_df)} symbols.")
    
    symbols_list = []
    for _, instrument in app.state.strategy_instruments_df.iterrows():
        # This structure now precisely matches the real BitMart API response.
        symbols_list.append({
            "symbol": instrument['pair'].replace('/', '_'),
            "symbol_id": instrument['instrument_token'],
            "base_currency": instrument['tradingsymbol'],
            "quote_currency": "INR",
            "quote_increment": "0.05",          # Price precision (tick size)
            "base_min_size": "1",               # Amount precision (lot size)
            "price_min_precision": 2,
            "price_max_precision": 2,
            "expiration": "NA",                 # Added field
            "min_buy_amount": "1.0",            # Added field: Min order size in quote currency
            "min_sell_amount": "1.0",           # Added field: Min order size in quote currency
            "trade_status": "trading"
        })
        
    return {
        "message": "OK",
        "code": 1000,
        "trace": str(uuid.uuid4()),
        "data": {
            "symbols": symbols_list
        }
    }

 @app.get("/ohlcv", summary="Fetch OHLCV Data with Looping for Extended History")
 async def fetch_ohlcv(symbol: str, timeframe: str = '5m', since: Optional[int] = None):
     if (DRY_RUN_ENABLED or app.state.access_token) and app.state.instruments_df is not None:
         instrument_token = get_instrument_token(app.state.instruments_df, symbol)
         if not instrument_token:
             raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found.")
       
         # In dry run, we cannot fetch live data, so we might return empty or dummy data.
         # For simplicity, we'll let it call the API, which will fail if not logged in.
         # A more robust dry-run would return fake data here.
         if not app.state.access_token and not DRY_RUN_ENABLED:
              raise HTTPException(status_code=401, detail="Bridge is not in a ready state.")

         kite_interval = KITE_HISTORICAL_LIMITS.get(timeframe.replace('m', 'minute').replace('h','hour'), "minute") # Simplified mapping
         days_limit = KITE_HISTORICAL_LIMITS.get(kite_interval, 60)
         to_date = datetime.now(pytz.timezone("Asia/Kolkata"))
         from_date = pd.to_datetime(since, unit='ms', utc=True).tz_convert('Asia/Kolkata') if since else to_date - timedelta(days=3*365)
       
         data_chunks = []
         current_date_from = from_date
         while current_date_from < to_date:
             chunk_date_to = current_date_from + timedelta(days=days_limit)
             if chunk_date_to > to_date: chunk_date_to = to_date
             try:
                 chunk = app.state.kite.historical_data(instrument_token, current_date_from, chunk_date_to, timeframe)
                 if chunk: data_chunks.append(pd.DataFrame(chunk))
                 current_date_from = chunk_date_to
                 time.sleep(0.5)
                 if chunk_date_to >= to_date: break
             except Exception as e:
                 logger.error(f"Error fetching data chunk for {symbol}: {e}")
                 break
         if not data_chunks: return []
         final_df = pd.concat(data_chunks, ignore_index=True).drop_duplicates(subset=['date'], keep='first')
         final_df['date'] = pd.to_datetime(final_df['date']).dt.tz_convert('Asia/Kolkata')
         final_df['timestamp'] = final_df['date'].apply(lambda x: int(x.timestamp() * 1000))
         return final_df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].values.tolist()
     else:
         raise HTTPException(status_code=401, detail="Bridge is not ready. Please wait and try again.")

# Replace your existing 'fetch_ohlcv' function with this new one.

# Add this mapping dictionary at the top of your kite-bridge.py file
KITE_INTERVAL_MAP = {
    "1": "1m", "3": "3m", "5": "5m", "10": "10m",
    "15": "15m", "30": "30m", "60": "60m",
    # Freqtrade may request '1d', which ccxt translates to 1440 minutes
    "1440": "day",
}

# In kite-bridge.py, replace the function that serves OHLCV data with this one.

def sanitize_table_name(name: str) -> str:
    """
    Sanitizes a string to be a valid SQL table name.
    MUST be identical to the function in the importer script.
    """
    return re.sub(r'[^a-zA-Z0-9_]', '_', name)

# In kite-bridge.py, replace the existing function with this one.

@app.get("/spot/quotation/v3/klines", summary="Fetch OHLCV Data from Per-Instrument Table")
async def fetch_klines_from_db(symbol: str, step: str, after: Optional[int] = None, limit: int = 1000):
    """
    Handles CCXT's request for historical data by querying a specific table
    for the requested instrument and timeframe. This version uses the 'after'
    and 'limit' parameters to fetch only the required data chunk, making it very fast.
    """
    timeframe = KITE_INTERVAL_MAP.get(step, step) 
    stock_symbol = symbol.split('_')[0]
    table_name = sanitize_table_name(f"{stock_symbol}_{timeframe}")
    
    logger.info(f"Received DB kline request for {symbol}, timeframe: {timeframe}. Querying table: '{table_name}' for data after timestamp {after}.")

    try:
        with sqlite3.connect("historical_data.db") as conn:
            # --- THIS IS THE CRITICAL FIX ---
            # We now build a query that uses the 'after' timestamp to only get the data we need.
            params = []
            query = f"SELECT timestamp, open, high, low, close, volume FROM {table_name}"
            
            if after is not None:
                # The 'after' parameter is the timestamp of the last candle from the previous batch.
                # We need all candles that came after it.
                query += " WHERE timestamp > ?"
                params.append(after)

            query += " ORDER BY timestamp ASC LIMIT ?"
            params.append(limit)
            # --- END OF FIX ---

            df = pd.read_sql_query(query, conn, params=tuple(params))

        # Check if the table exists or if the query returned data
        if df.empty:
            # This is normal if there's no more data in the requested range
            logger.info(f"No more data found for table '{table_name}' after timestamp {after}. Returning empty list.")
            return {"message": "success", "code": 1000, "trace": str(uuid.uuid4()), "data": []}

        ohlcv_list = []
        for _, row in df.iterrows():
            quote_volume = row['volume'] * row['close']
            ohlcv_list.append([
                str(int(row['timestamp'])), str(row['open']), str(row['high']),
                str(row['low']), str(row['close']), str(row['volume']), str(quote_volume)
            ])
        
        return {
            "message": "success", "code": 1000, "trace": str(uuid.uuid4()), "data": ohlcv_list
        }
    except Exception as e:
        # This will catch cases where the table doesn't exist.
        if "no such table" in str(e):
             logger.warning(f"Table '{table_name}' does not exist. Returning empty list.")
             return {"message": "success", "code": 1000, "trace": str(uuid.uuid4()), "data": []}
        else:
            logger.error(f"Error fetching historical data for {symbol} from DB table {table_name}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

# Add this new function to your kite-bridge.py file

@app.get("/contract/public/details", summary="Mock Futures/Contract Endpoint")
async def fetch_contract_details():
    """
    During initialization, ccxt also tries to load futures markets.
    This endpoint catches that call and returns an empty list of symbols,
    effectively telling ccxt that there are no futures markets,
    which stops it from making any real external API calls.
    """
    logger.info("Serving mock/empty contract details to prevent external API call.")
    return {
        "code": 1000,
        "message": "Ok",
        "data": {
            "symbols": [] # Return an empty list of symbols
        },
        "trace": str(uuid.uuid4())
    } 

@app.get("/balance", summary="Fetch Account Balance")
async def fetch_balance():
    if DRY_RUN_ENABLED:
        logger.info("[DRY RUN] Simulating balance request.")
        return {'INR': {'free': 10000.0, 'used': 0.0, 'total': 10000.0}, 'info': "Dry Run Balance"}
    if not app.state.access_token:
        raise HTTPException(status_code=401, detail="Bridge is not ready.")
    try:
        margins = app.state.kite.margins()
        equity_margins = margins.get('equity', {})
        return {'INR': {'free': equity_margins.get('available', {}).get('live_balance', 0), 'used': equity_margins.get('utilised', {}).get('debits', 0), 'total': equity_margins.get('net', 0)}, 'info': margins}
    except Exception as e:
        logger.error(f"Error fetching margins: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Order Management Endpoints with Dry Run Logic ---
@app.post("/orders", summary="Place an Order")
async def create_order(symbol: str, type: str, side: str, amount: float, price: Optional[float] = None):
    if DRY_RUN_ENABLED:
        logger.info(f"[DRY RUN] Simulating create_order for {side} {amount} of {symbol}")
        fake_order_id = str(uuid.uuid4())
        simulated_order = {
            "id": fake_order_id, "symbol": symbol, "type": type.lower(), "side": side.lower(),
            "price": price, "amount": amount, "filled": 0.0, "remaining": amount, "status": "open",
            "timestamp": datetime.now(pytz.timezone("Asia/Kolkata")).isoformat(), "info": {"message": "Dry run simulated order"}
        }
        app.state.simulated_orders.append(simulated_order)
        return {"id": fake_order_id, "info": simulated_order}
    else:
        if not app.state.access_token: raise HTTPException(status_code=401, detail="Bridge is not ready for live trading.")
        try:
            instrument = app.state.instruments_df[app.state.instruments_df.pair == symbol].iloc[0]
            order_id = app.state.kite.place_order(
                variety=app.state.kite.VARIETY_REGULAR, exchange=instrument['exchange'], tradingsymbol=instrument['tradingsymbol'],
                transaction_type=app.state.kite.TRANSACTION_TYPE_BUY if side.lower() == 'buy' else app.state.kite.TRANSACTION_TYPE_SELL,
                quantity=int(amount), product=app.state.kite.PRODUCT_MIS,
                order_type=app.state.kite.ORDER_TYPE_LIMIT if type.lower() == 'limit' else app.state.kite.ORDER_TYPE_MARKET,
                price=price
            )
            logger.info(f"[LIVE] Successfully placed order with ID: {order_id}")
            return {"id": order_id, "info": {"message": "Live order placed successfully"}}
        except Exception as e:
            logger.error(f"[LIVE] Failed to place order for {symbol}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        
# Add this entire function to your main.py script

@app.get("/markets", summary="Fetch Available Markets for Freqtrade")
async def fetch_markets():
    """
    Returns the list of tradable pairs for the currently configured strategy
    in a format that CCXT/Freqtrade understands.
    """
    if app.state.strategy_instruments_df is None or app.state.strategy_instruments_df.empty:
        logger.warning(f"[{STRATEGY_TAG}] /markets endpoint called but instruments are not loaded.")
        return {} # Return an empty dict if not ready

    logger.info(f"[{STRATEGY_TAG}] Serving {len(app.state.strategy_instruments_df)} markets.")
    
    markets = {}
    for _, instrument in app.state.strategy_instruments_df.iterrows():
        pair_symbol = instrument['pair']
        
        # Build the market dictionary in the format CCXT/Freqtrade expects
        markets[pair_symbol] = {
            'id': instrument['tradingsymbol'],
            'symbol': pair_symbol,
            'base': instrument['tradingsymbol'],
            'quote': 'INR',
            'active': True,
            'type': 'spot', # Freqtrade uses 'spot' for regular trading
            'precision': {
                'price': 0.05, # Tick size
                'amount': 1.0,   # Lot size
            },
            'limits': {
                'amount': {'min': 1.0, 'max': None},
                'price': {'min': None, 'max': None},
                'cost': {'min': None, 'max': None}
            },
            'info': instrument.to_dict() # Include original data for debugging
        }
        
    return markets

@app.get("/orders/{order_id}", summary="Fetch an Order Status")
async def fetch_order(order_id: str):
    if DRY_RUN_ENABLED:
        order_to_update = next((o for o in app.state.simulated_orders if o['id'] == order_id), None)
        if not order_to_update: raise HTTPException(status_code=404, detail=f"Simulated order {order_id} not found.")
        if order_to_update['status'] == 'open':
            order_to_update['status'] = 'closed'
            order_to_update['filled'] = order_to_update['amount']
            order_to_update['remaining'] = 0
            logger.info(f"[DRY RUN] Order {order_id} has been simulated as 'closed'.")
        return order_to_update
    else:
        if not app.state.access_token: raise HTTPException(status_code=401, detail="Bridge is not ready.")
        try:
            order_history = app.state.kite.order_history(order_id=order_id)
            if not order_history: raise HTTPException(status_code=404, detail=f"Order ID {order_id} not found.")
            latest_status = order_history[-1]
            status_map = {'COMPLETE': 'closed', 'CANCELLED': 'canceled', 'REJECTED': 'rejected'}
            status = status_map.get(latest_status['status'], 'open')
            return {
                "id": latest_status['order_id'], "status": status, "symbol": latest_status['tradingsymbol'],
                "type": latest_status['order_type'].lower(), "side": latest_status['transaction_type'].lower(),
                "price": latest_status['price'], "amount": latest_status['quantity'], "filled": latest_status['filled_quantity'],
                "remaining": latest_status['pending_quantity'], "average": latest_status['average_price'], "info": latest_status
            }
        except Exception as e:
            logger.error(f"Failed to fetch order {order_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

@app.delete("/orders/{order_id}", summary="Cancel an Order")
async def cancel_order(order_id: str):
    if DRY_RUN_ENABLED:
        order_to_cancel = next((o for o in app.state.simulated_orders if o['id'] == order_id), None)
        if not order_to_cancel: raise HTTPException(status_code=404, detail=f"Simulated order {order_id} not found.")
        order_to_cancel['status'] = 'canceled'
        logger.info(f"[DRY RUN] Order {order_id} has been simulated as 'canceled'.")
        return order_to_cancel
    else:
        if not app.state.access_token: raise HTTPException(status_code=401, detail="Bridge is not ready.")
        try:
            cancelled_id = app.state.kite.cancel_order(variety=app.state.kite.VARIETY_REGULAR, order_id=order_id)
            return {"id": cancelled_id, "info": {"message": "Order cancellation request sent successfully"}}
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))