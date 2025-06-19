#!/usr/bin/env python3
"""
Zerodha Kite Connect Automated Token Generator

This script automates the entire Zerodha login and token generation process,
including handling 2FA with TOTP. It can be run manually or scheduled to run
daily at 7 AM IST.

Usage:
    python zerodha_auto_token.py                 # Run once and exit
    python zerodha_auto_token.py --schedule      # Run continuously, generating token at 7 AM daily
    python zerodha_auto_token.py --daemon        # Run as daemon process

Requirements:
    pip install kiteconnect pyotp requests python-dotenv schedule
"""

import os
import sys
import json
import time
import logging
import argparse
import schedule
import signal
from pathlib import Path
from datetime import datetime, time as dt_time
from typing import Optional
from urllib.parse import urlparse, parse_qs

import pytz
import pyotp
import requests
from dotenv import load_dotenv
from kiteconnect import KiteConnect

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('zerodha_token_generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ZerodhaTokenGenerator")

# Configuration from environment variables
API_KEY = os.getenv("ZERODHA_API_KEY", os.getenv("KITE_API_KEY"))
API_SECRET = os.getenv("ZERODHA_API_SECRET", os.getenv("KITE_API_SECRET"))
USER_ID = os.getenv("ZERODHA_USER_ID", os.getenv("KITE_USER_ID"))
PASSWORD = os.getenv("ZERODHA_PASSWORD", os.getenv("KITE_PASSWORD"))
TOTP_KEY = os.getenv("ZERODHA_TOTP_KEY", os.getenv("KITE_TOTP_KEY"))

# Token cache configuration
CACHE_DIR = Path.home() / '.cache' / 'ccxt-zerodha'
TOKEN_CACHE_FILE = CACHE_DIR / 'token.json'
SESSION_CACHE_FILE = CACHE_DIR / 'session.json'

# Global variable to handle graceful shutdown
should_exit = False


def signal_handler(signum, frame):
    """Handle interrupt signals gracefully."""
    global should_exit
    logger.info("Received interrupt signal. Shutting down gracefully...")
    should_exit = True


def validate_config():
    """Validate that all required configuration is present."""
    required_vars = {
        "API_KEY": API_KEY,
        "API_SECRET": API_SECRET,
        "USER_ID": USER_ID,
        "PASSWORD": PASSWORD,
        "TOTP_KEY": TOTP_KEY
    }
    
    missing = [var for var, value in required_vars.items() if not value]
    
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error("Please set these in your .env file or as environment variables:")
        for var in missing:
            logger.error(f"  - ZERODHA_{var} or KITE_{var}")
        return False
    
    return True


def perform_automated_login() -> Optional[dict]:
    """
    Perform fully automated login to Zerodha Kite Connect.
    Returns session data with access_token on success, None on failure.
    """
    logger.info("Starting automated login process...")
    
    try:
        # Create a session for maintaining cookies
        session = requests.Session()
        
        # Step 1: Initial login with username and password
        logger.info(f"Logging in with user ID: {USER_ID}")
        login_response = session.post(
            "https://kite.zerodha.com/api/login",
            data={
                "user_id": USER_ID,
                "password": PASSWORD
            }
        )
        login_response.raise_for_status()
        
        login_data = login_response.json()
        if login_data.get("status") != "success":
            raise ValueError(f"Login failed: {login_data.get('message', 'Unknown error')}")
        
        request_id = login_data["data"]["request_id"]
        logger.info("Initial login successful, proceeding with 2FA...")
        
        # Step 2: Submit TOTP for two-factor authentication
        totp_code = pyotp.TOTP(TOTP_KEY).now()
        logger.info(f"Submitting TOTP code: {totp_code}")
        
        twofa_response = session.post(
            "https://kite.zerodha.com/api/twofa",
            data={
                "user_id": USER_ID,
                "request_id": request_id,
                "twofa_value": totp_code,
                "twofa_type": "totp"
            }
        )
        twofa_response.raise_for_status()
        
        twofa_data = twofa_response.json()
        if twofa_data.get("status") != "success":
            raise ValueError(f"2FA failed: {twofa_data.get('message', 'Unknown error')}")
        
        logger.info("2FA successful, fetching request token...")
        
        # Step 3: Get the request token by following the API login redirect
        api_login_url = f"https://kite.trade/connect/login?api_key={API_KEY}&v=3"
        
        # We expect a redirect, capture the final URL
        try:
            # Allow redirects but capture the final URL
            api_response = session.get(api_login_url, allow_redirects=True, timeout=10)
            final_url = api_response.url
        except requests.exceptions.ConnectionError as e:
            # Sometimes the redirect goes to a URL that doesn't exist (like a localhost callback)
            # In this case, we can still extract the token from the attempted redirect URL
            if hasattr(e, 'request') and hasattr(e.request, 'url'):
                final_url = e.request.url
            else:
                raise
        
        # Extract request_token from the URL
        parsed_url = urlparse(final_url)
        query_params = parse_qs(parsed_url.query)
        
        if 'request_token' not in query_params:
            raise ValueError(f"No request token found in redirect URL: {final_url}")
        
        request_token = query_params['request_token'][0]
        logger.info(f"Got request token: {request_token[:10]}...")
        
        # Step 4: Exchange request token for access token
        logger.info("Exchanging request token for access token...")
        kite = KiteConnect(api_key=API_KEY)
        session_data = kite.generate_session(request_token, api_secret=API_SECRET)
        
        access_token = session_data.get("access_token")
        if not access_token:
            raise ValueError("Failed to get access token from session data")
        
        # Add metadata
        session_data['generated_at'] = datetime.now().isoformat()
        session_data['user_id'] = USER_ID
        
        # Convert datetime objects to strings for JSON serialization
        if "login_time" in session_data and hasattr(session_data["login_time"], "isoformat"):
            session_data["login_time"] = session_data["login_time"].isoformat()
        
        logger.info(f"Successfully generated access token: {access_token[:10]}...")
        return session_data
        
    except Exception as e:
        logger.error(f"Automated login failed: {type(e).__name__}: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return None


def save_token_data(session_data: dict):
    """Save token data to cache files."""
    try:
        # Ensure cache directory exists
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Save full session data
        with open(SESSION_CACHE_FILE, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        # Save simplified token data for CCXT compatibility
        token_data = {
            'access_token': session_data['access_token'],
            'login_time': session_data.get('login_time', datetime.now(pytz.timezone('Asia/Kolkata')).isoformat()),
            'api_key': API_KEY,
            'user_id': USER_ID,
            'generated_at': session_data.get('generated_at', datetime.now().isoformat())
        }
        
        with open(TOKEN_CACHE_FILE, 'w') as f:
            json.dump(token_data, f, indent=2)
        
        # Set restrictive permissions on cache files (Unix-like systems only)
        try:
            os.chmod(TOKEN_CACHE_FILE, 0o600)
            os.chmod(SESSION_CACHE_FILE, 0o600)
        except:
            pass
        
        logger.info(f"Token data saved to {TOKEN_CACHE_FILE}")
        logger.info(f"Full session data saved to {SESSION_CACHE_FILE}")
        
    except Exception as e:
        logger.error(f"Failed to save token data: {e}")


def generate_token():
    """Main function to generate and save access token."""
    logger.info("=" * 60)
    logger.info("Starting Zerodha token generation")
    logger.info("=" * 60)
    
    if not validate_config():
        return False
    
    session_data = perform_automated_login()
    if not session_data:
        logger.error("Failed to generate access token")
        return False
    
    save_token_data(session_data)
    
    # Display token information
    access_token = session_data['access_token']
    login_time = session_data.get('login_time', 'Unknown')
    
    logger.info("=" * 60)
    logger.info("TOKEN GENERATION SUCCESSFUL!")
    logger.info("=" * 60)
    logger.info(f"Access Token: {access_token}")
    logger.info(f"Login Time: {login_time}")
    logger.info(f"Token will expire at 6:00 AM IST tomorrow")
    logger.info("")
    logger.info("To use with Freqtrade:")
    logger.info(f'  "password": "{access_token}"')
    logger.info("")
    logger.info("Or set as environment variable:")
    logger.info(f'  export FREQTRADE__EXCHANGE__PASSWORD="{access_token}"')
    logger.info("=" * 60)
    
    return True


def is_token_valid():
    """Check if the current token is still valid."""
    if not TOKEN_CACHE_FILE.exists():
        return False
    
    try:
        with open(TOKEN_CACHE_FILE, 'r') as f:
            token_data = json.load(f)
        
        login_time_str = token_data.get('login_time')
        if not login_time_str:
            return False
        
        # Parse login time and check expiry
        ist = pytz.timezone('Asia/Kolkata')
        login_time = datetime.fromisoformat(login_time_str.replace('Z', '+00:00'))
        if login_time.tzinfo is None:
            login_time = ist.localize(login_time)
        else:
            login_time = login_time.astimezone(ist)
        
        now_ist = datetime.now(ist)
        
        # Token expires at 6 AM IST the next day
        expiry_time = login_time.replace(hour=6, minute=0, second=0, microsecond=0)
        if login_time.hour >= 6:
            expiry_time += timedelta(days=1)
        
        is_valid = now_ist < expiry_time
        
        if is_valid:
            logger.info(f"Current token is valid until {expiry_time.strftime('%Y-%m-%d %H:%M:%S IST')}")
        else:
            logger.info("Current token has expired")
        
        return is_valid
        
    except Exception as e:
        logger.error(f"Error checking token validity: {e}")
        return False


def scheduled_token_generation():
    """Function to run token generation as scheduled task."""
    logger.info("Scheduled token generation triggered")
    
    # Check if token is already valid
    if is_token_valid():
        logger.info("Token is still valid, skipping generation")
        return
    
    # Try to generate token with retries
    max_retries = 3
    retry_delay = 60  # seconds
    
    for attempt in range(max_retries):
        if generate_token():
            logger.info("Scheduled token generation completed successfully")
            return
        
        if attempt < max_retries - 1:
            logger.warning(f"Token generation failed, retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
            time.sleep(retry_delay)
    
    logger.error(f"Failed to generate token after {max_retries} attempts")


def run_scheduler():
    """Run the token generation scheduler."""
    global should_exit
    
    # Schedule token generation at 7:00 AM IST every day
    schedule.every().day.at("07:00").do(scheduled_token_generation)
    
    # Also run immediately if token is not valid
    if not is_token_valid():
        logger.info("No valid token found, generating immediately...")
        generate_token()
    
    logger.info("Scheduler started. Token generation scheduled for 7:00 AM IST daily.")
    logger.info("Press Ctrl+C to stop.")
    
    # Keep the scheduler running
    while not should_exit:
        schedule.run_pending()
        time.sleep(1)
    
    logger.info("Scheduler stopped.")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automated Zerodha Kite Connect token generator"
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run continuously and generate token at 7 AM IST daily"
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as daemon process (implies --schedule)"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if current token is valid and exit"
    )
    
    args = parser.parse_args()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if args.check:
            # Just check token validity and exit
            if is_token_valid():
                sys.exit(0)
            else:
                sys.exit(1)
        
        elif args.schedule or args.daemon:
            # Run scheduler
            if args.daemon:
                # Daemonize the process (Unix-like systems only)
                try:
                    import daemon
                    with daemon.DaemonContext():
                        run_scheduler()
                except ImportError:
                    logger.warning("python-daemon not installed, running in foreground")
                    logger.warning("Install with: pip install python-daemon")
                    run_scheduler()
            else:
                run_scheduler()
        
        else:
            # Run once and exit
            success = generate_token()
            sys.exit(0 if success else 1)
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main() 