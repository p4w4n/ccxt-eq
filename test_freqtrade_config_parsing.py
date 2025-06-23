#!/usr/bin/env python3

import json
import sys
import os

def test_config_parsing():
    """Test config file parsing"""
    
    print("=== Freqtrade Config Debug ===")
    
    # Common config formats to try
    config_formats = [
        # Format 1: Standard Freqtrade format
        {
            "exchange": {
                "name": "zerodha",
                "apiKey": "test_api_key",
                "secret": "test_secret",
                "password": "test_access_token"
            }
        },
        
        # Format 2: Alternative with 'key' instead of 'apiKey'
        {
            "exchange": {
                "name": "zerodha",
                "key": "test_api_key",
                "secret": "test_secret",
                "password": "test_access_token"
            }
        },
        
        # Format 3: With ccxt_config
        {
            "exchange": {
                "name": "zerodha",
                "apiKey": "test_api_key",
                "secret": "test_secret",
                "password": "test_access_token",
                "ccxt_config": {
                    "enableRateLimit": True,
                    "rateLimit": 100
                }
            }
        }
    ]
    
    print("Try these config formats in your Freqtrade config file:")
    print()
    
    for i, config in enumerate(config_formats, 1):
        print(f"Format {i}:")
        print(json.dumps(config, indent=2))
        print()

def show_debug_steps():
    """Show debugging steps"""
    
    print("=== Debugging Steps ===")
    print()
    print("1. Check your config file location:")
    print("   - Make sure you're using the correct config file")
    print("   - Verify the file path in your Freqtrade command")
    print()
    print("2. Validate your JSON syntax:")
    print("   - Use a JSON validator to check for syntax errors")
    print("   - Make sure all quotes are properly escaped")
    print()
    print("3. Test with a minimal config:")
    print("   Create a minimal config.json with just:")
    print("   ```json")
    print("   {")
    print('     "exchange": {')
    print('       "name": "zerodha",')
    print('       "apiKey": "your_api_key",')
    print('       "secret": "your_secret"')
    print("     }")
    print("   }")
    print("   ```")
    print()
    print("4. Check Freqtrade version:")
    print("   freqtrade --version")
    print()
    print("5. Try running Freqtrade with verbose output:")
    print("   freqtrade trade --config config.json --verbose")

def create_minimal_config():
    """Create a minimal test config"""
    
    minimal_config = {
        "exchange": {
            "name": "zerodha",
            "apiKey": "your_api_key_here",
            "secret": "your_secret_here"
        },
        "dry_run": True,
        "max_open_trades": 1,
        "stake_currency": "INR",
        "stake_amount": "unlimited",
        "tradable_balance_ratio": 0.99,
        "fiat_display_currency": "INR",
        "timeframe": "5m",
        "dry_run_wallet": 1000,
        "cancel_open_orders_on_exit": False,
        "trading_mode": "spot",
        "margin_mode": "",
        "unfilledtimeout": {
            "entry": 10,
            "exit": 10,
            "exit_timeout_count": 0,
            "unit": "minutes"
        },
        "entry_pricing": {
            "price_side": "same",
            "use_order_book": True,
            "order_book_top": 1,
            "price_last_balance": 0.0,
            "check_depth_of_market": {
                "enabled": False,
                "bids_to_ask_delta": 1
            }
        },
        "exit_pricing": {
            "price_side": "same",
            "use_order_book": True,
            "order_book_top": 1
        },
        "exchange": {
            "name": "zerodha",
            "apiKey": "your_api_key_here",
            "secret": "your_secret_here"
        },
        "pair_whitelist": [
            "NSE:INFY/INR",
            "NSE:TCS/INR"
        ],
        "pair_blacklist": []
    }
    
    with open("minimal_config.json", "w") as f:
        json.dump(minimal_config, f, indent=2)
    
    print("Created minimal_config.json")
    print("Replace 'your_api_key_here' and 'your_secret_here' with your actual credentials")

if __name__ == "__main__":
    test_config_parsing()
    show_debug_steps()
    create_minimal_config()
    
    print("\n=== Next Steps ===")
    print("1. Check your config file for JSON syntax errors")
    print("2. Try the minimal_config.json file")
    print("3. Make sure you're using the correct config file path")
    print("4. Verify your Freqtrade version supports the config format") 