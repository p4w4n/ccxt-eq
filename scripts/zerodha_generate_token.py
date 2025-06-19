#!/usr/bin/env python3
"""
Zerodha Access Token Generator

This script guides users through the process of generating a daily access token
for Zerodha Kite Connect API. The token is required for automated trading with
the CCXT Zerodha wrapper.

Usage:
    python zerodha_generate_token.py

Requirements:
    - Zerodha API Key and Secret (from Kite Connect Developer Portal)
    - Valid Zerodha trading account
    - Internet connection for API calls

The script will:
1. Prompt for API credentials
2. Open the Zerodha login page in browser
3. Guide user through manual login process
4. Generate and cache the access token
5. Display the token for use in trading applications

Security Note: The access token expires daily at 6:00 AM IST and needs to be regenerated.
"""

import hashlib
import json
import webbrowser
import sys
import os
from pathlib import Path
from datetime import datetime
import requests


def get_credentials():
    """Prompt user for API credentials."""
    print("=== Zerodha Access Token Generator ===\n")
    print("This script will help you generate a daily access token for Zerodha Kite Connect.")
    print("You will need your API Key and Secret from the Kite Connect Developer Portal.\n")
    
    api_key = input("Enter your Zerodha API Key: ").strip()
    if not api_key:
        print("Error: API Key is required.")
        sys.exit(1)
    
    api_secret = input("Enter your Zerodha API Secret: ").strip()
    if not api_secret:
        print("Error: API Secret is required.")
        sys.exit(1)
    
    return api_key, api_secret


def generate_login_url(api_key):
    """Generate the Zerodha login URL."""
    base_url = "https://kite.zerodha.com/connect/login"
    return f"{base_url}?api_key={api_key}&v=3"


def extract_request_token(redirect_url):
    """Extract request_token from the redirect URL."""
    try:
        if 'request_token=' not in redirect_url:
            raise ValueError("request_token not found in URL")
        
        # Extract request_token from URL
        token_part = redirect_url.split('request_token=')[1]
        request_token = token_part.split('&')[0]  # Remove any additional parameters
        
        if not request_token:
            raise ValueError("Empty request_token")
        
        return request_token
    except Exception as e:
        raise ValueError(f"Could not extract request_token: {e}")


def generate_session(api_key, api_secret, request_token):
    """Generate access token using the request token."""
    # Generate checksum as per Zerodha API documentation
    checksum_string = api_key + request_token + api_secret
    checksum = hashlib.sha256(checksum_string.encode()).hexdigest()
    
    # Prepare request data
    url = "https://api.kite.trade/session/token"
    data = {
        'api_key': api_key,
        'request_token': request_token,
        'checksum': checksum
    }
    
    headers = {
        'X-Kite-Version': '3',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        response = requests.post(url, data=data, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get('status') == 'success':
            return result['data']
        else:
            error_msg = result.get('message', 'Unknown error')
            raise Exception(f"API Error: {error_msg}")
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error: {e}")
    except json.JSONDecodeError:
        raise Exception("Invalid response from server")


def save_token_cache(access_token, login_time):
    """Save the access token to cache file."""
    cache_dir = Path.home() / '.cache' / 'ccxt-zerodha'
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    cache_file = cache_dir / 'token.json'
    
    token_data = {
        'access_token': access_token,
        'login_time': login_time,
        'generated_at': datetime.now().isoformat(),
        'expires_info': 'Token expires at 6:00 AM IST next day'
    }
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(token_data, f, indent=2)
        
        # Set restrictive permissions (Unix-like systems only)
        try:
            os.chmod(cache_file, 0o600)
        except (OSError, AttributeError):
            pass  # Windows or permission error
        
        return cache_file
    except Exception as e:
        print(f"Warning: Could not save token to cache: {e}")
        return None


def main():
    """Main function to orchestrate the token generation process."""
    try:
        # Step 1: Get credentials
        api_key, api_secret = get_credentials()
        
        # Step 2: Generate login URL and guide user
        login_url = generate_login_url(api_key)
        
        print("\n" + "="*60)
        print("STEP 1: Login to Zerodha")
        print("="*60)
        print("1. A login page will open in your browser")
        print("2. Enter your Zerodha user ID and password")
        print("3. Complete 2FA if prompted")
        print("4. After successful login, you'll be redirected to a URL")
        print("5. Copy the ENTIRE redirect URL and paste it below")
        print("\nOpening browser...")
        
        # Open browser
        webbrowser.open(login_url)
        
        print(f"\nIf the browser didn't open, manually visit:")
        print(f"{login_url}\n")
        
        # Step 3: Get redirect URL from user
        print("="*60)
        print("STEP 2: Paste Redirect URL")
        print("="*60)
        
        redirect_url = input("Paste the complete redirect URL here: ").strip()
        if not redirect_url:
            print("Error: Redirect URL is required.")
            sys.exit(1)
        
        # Step 4: Extract request token
        try:
            request_token = extract_request_token(redirect_url)
            print(f"✓ Successfully extracted request token: {request_token[:10]}...")
        except ValueError as e:
            print(f"Error: {e}")
            print("\nThe redirect URL should look like:")
            print("https://your-redirect-url?request_token=XXXXXX&action=login&status=success")
            sys.exit(1)
        
        # Step 5: Generate access token
        print("\n" + "="*60)
        print("STEP 3: Generating Access Token")
        print("="*60)
        print("Connecting to Zerodha API...")
        
        session_data = generate_session(api_key, api_secret, request_token)
        access_token = session_data['access_token']
        login_time = session_data['login_time']
        
        print("✓ Access token generated successfully!")
        
        # Step 6: Save to cache
        cache_file = save_token_cache(access_token, login_time)
        if cache_file:
            print(f"✓ Token cached at: {cache_file}")
        
        # Step 7: Display results
        print("\n" + "="*60)
        print("SUCCESS - Access Token Generated")
        print("="*60)
        print("\n🔑 ACCESS TOKEN:")
        print("-" * 60)
        print(access_token)
        print("-" * 60)
        
        print("\n📋 USAGE INSTRUCTIONS:")
        print("1. Copy the access token above")
        print("2. In your Freqtrade config.json, set:")
        print(f'   "password": "{access_token}"')
        print("3. Or set environment variable:")
        print(f'   export FREQTRADE__EXCHANGE__PASSWORD="{access_token}"')
        
        print("\n⚠️  IMPORTANT REMINDERS:")
        print("• This token expires at 6:00 AM IST tomorrow")
        print("• You must regenerate the token daily")
        print("• Keep your token secure and never share it")
        print("• For automated trading, update your config before 6:00 AM IST")
        
        print(f"\n📊 TOKEN DETAILS:")
        print(f"• Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"• Login time: {login_time}")
        print(f"• API Key: {api_key}")
        print(f"• Cached: {'Yes' if cache_file else 'No'}")
        
        print("\n✅ Token generation completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nIf the problem persists:")
        print("1. Verify your API credentials")
        print("2. Check your internet connection")
        print("3. Ensure you have access to the Kite Connect API")
        print("4. Visit https://kite.trade/docs/connect/v3/ for more help")
        sys.exit(1)


if __name__ == "__main__":
    main() 