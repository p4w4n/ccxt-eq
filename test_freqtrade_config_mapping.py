#!/usr/bin/env python3

import sys
import os
import json

# Add our custom CCXT to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

def test_freqtrade_config_mapping():
    """Test how Freqtrade maps its config to CCXT"""
    
    print("=== Freqtrade Config Mapping Test ===")
    
    # Simulate Freqtrade's exchange config
    freqtrade_config = {
        "exchange": {
            "name": "zerodha",
            "key": "test_api_key",
            "secret": "test_secret",
            "password": "test_access_token",
            "ccxt_config": {
                "enableRateLimit": True,
                "rateLimit": 100
            }
        }
    }
    
    print("Freqtrade config:")
    print(json.dumps(freqtrade_config, indent=2))
    
    # Simulate what Freqtrade should pass to CCXT
    ccxt_config = {
        "apiKey": freqtrade_config["exchange"].get("key", ""),
        "secret": freqtrade_config["exchange"].get("secret", ""),
        "password": freqtrade_config["exchange"].get("password", ""),
        "enableRateLimit": freqtrade_config["exchange"].get("ccxt_config", {}).get("enableRateLimit", True),
        "rateLimit": freqtrade_config["exchange"].get("ccxt_config", {}).get("rateLimit", 100)
    }
    
    print("\nWhat should be passed to CCXT:")
    print(json.dumps(ccxt_config, indent=2))
    
    # Test with our custom CCXT
    try:
        import ccxt
        
        print("\nTesting with our custom CCXT:")
        exchange = ccxt.zerodha(ccxt_config)
        
        print(f"✓ Exchange created successfully")
        print(f"apiKey: {exchange.apiKey}")
        print(f"secret: {exchange.secret}")
        print(f"access_token: {exchange.access_token}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_freqtrade_fix():
    """Show how to fix Freqtrade config mapping"""
    
    print("\n=== Freqtrade Fix Options ===")
    print("The issue is that Freqtrade is not properly mapping its config to CCXT.")
    print()
    print("Option 1: Check Freqtrade version and config format")
    print("- Make sure you're using a recent version of Freqtrade")
    print("- Verify your config format matches Freqtrade's expected format")
    print()
    print("Option 2: Try different config keys")
    print("In your Freqtrade config, try:")
    print("```json")
    print("{")
    print('  "exchange": {')
    print('    "name": "zerodha",')
    print('    "apiKey": "your_api_key",')
    print('    "secret": "your_secret",')
    print('    "password": "your_access_token"')
    print("  }")
    print("}")
    print("```")
    print()
    print("Option 3: Check Freqtrade documentation")
    print("- Look for the correct exchange configuration format")
    print("- Verify that 'key' maps to 'apiKey' in Freqtrade")

if __name__ == "__main__":
    success = test_freqtrade_config_mapping()
    show_freqtrade_fix()
    
    if success:
        print("\n✓ Config mapping test passed!")
    else:
        print("\n✗ Config mapping test failed!")
        sys.exit(1) 