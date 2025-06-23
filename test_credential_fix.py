#!/usr/bin/env python3

import sys
import os
import json
from pathlib import Path

# Add the python directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

def test_credential_loading():
    """Test that credentials are loaded correctly from config vs cache"""
    
    # Test 1: Credentials provided in config
    print("Test 1: Credentials provided in config")
    try:
        import ccxt
        
        # Create exchange with credentials in config
        exchange = ccxt.zerodha({
            'apiKey': 'test_api_key',
            'secret': 'test_secret',
            'password': 'test_access_token'
        })
        
        # Check that credentials are loaded from config
        assert exchange.apiKey == 'test_api_key'
        assert exchange.secret == 'test_secret'
        assert exchange.access_token == 'test_access_token'
        
        print("✓ Credentials loaded from config correctly")
        
    except Exception as e:
        print(f"✗ Error testing config credentials: {e}")
        return False
    
    # Test 2: API key from cache, secret from config
    print("\nTest 2: API key from cache, secret from config")
    try:
        # Create cache directory and file
        cache_path = Path.home() / '.cache' / 'ccxt-zerodha' / 'token.json'
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write test data to cache
        cache_data = {
            'api_key': 'cached_api_key',
            'access_token': 'cached_access_token',
            'login_time': '2024-01-01T09:00:00+05:30'
        }
        
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)
        
        # Create exchange with only secret in config
        exchange = ccxt.zerodha({
            'secret': 'config_secret'
        })
        
        # Check that API key is loaded from cache
        assert exchange.apiKey == 'cached_api_key'
        assert exchange.secret == 'config_secret'
        exchange._load_access_token()  # Load access token from cache
        assert exchange.access_token == 'cached_access_token'
        
        print("✓ API key loaded from cache, secret from config")
        
        # Clean up cache file
        cache_path.unlink()
        
    except Exception as e:
        print(f"✗ Error testing cache credentials: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Async version
    print("\nTest 3: Async version credential loading")
    try:
        import ccxt.async_support as ccxt_async
        
        # Create async exchange with credentials in config
        exchange = ccxt_async.zerodha({
            'apiKey': 'async_test_api_key',
            'secret': 'async_test_secret',
            'password': 'async_test_access_token'
        })
        
        # Check that credentials are loaded from config
        assert exchange.apiKey == 'async_test_api_key'
        assert exchange.secret == 'async_test_secret'
        assert exchange.access_token == 'async_test_access_token'
        
        print("✓ Async credentials loaded from config correctly")
        
    except Exception as e:
        print(f"✗ Error testing async credentials: {e}")
        return False
    
    print("\n✓ All credential loading tests passed!")
    return True

if __name__ == "__main__":
    success = test_credential_loading()
    sys.exit(0 if success else 1) 