#!/usr/bin/env python3

import sys
import os
import json
from pathlib import Path

# Add the python directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

def test_session_based_auth():
    """Test session-based authentication with api_key and access_token from cache"""
    
    print("=== Session-Based Authentication Test ===")
    
    # Create a test token cache file
    cache_path = Path.home() / '.cache' / 'ccxt-zerodha' / 'token.json'
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Test data
    test_token_data = {
        'access_token': 'test_access_token_12345',
        'login_time': '2024-06-19T09:00:00+05:30',
        'api_key': 'test_api_key_67890',
        'user_id': 'test_user',
        'generated_at': '2024-06-19T09:00:00+00:00'
    }
    
    # Write test data to cache
    with open(cache_path, 'w') as f:
        json.dump(test_token_data, f, indent=2)
    
    print(f"Created test token cache at: {cache_path}")
    
    try:
        import ccxt
        
        # Test 1: No credentials in config, load from cache
        print("\nTest 1: Loading credentials from cache")
        exchange = ccxt.zerodha({})
        
        # Check that credentials are loaded from cache
        assert exchange.apiKey == 'test_api_key_67890'
        assert exchange.access_token == 'test_access_token_12345'
        
        print("✓ Credentials loaded from cache correctly")
        
        # Test 2: Override with config credentials
        print("\nTest 2: Override with config credentials")
        exchange2 = ccxt.zerodha({
            'apiKey': 'config_api_key',
            'password': 'config_access_token'
        })
        
        # Check that config credentials take precedence
        assert exchange2.apiKey == 'config_api_key'
        assert exchange2.access_token == 'config_access_token'
        
        print("✓ Config credentials override cache correctly")
        
        # Test 3: Async version
        print("\nTest 3: Async version")
        import ccxt.async_support as ccxt_async
        
        async_exchange = ccxt_async.zerodha({})
        
        # Check that async credentials are loaded from cache
        assert async_exchange.apiKey == 'test_api_key_67890'
        assert async_exchange.access_token == 'test_access_token_12345'
        
        print("✓ Async credentials loaded from cache correctly")
        
        # Test 4: Test authentication header format
        print("\nTest 4: Test authentication header format")
        
        # Simulate a private API call
        signed_request = exchange.sign('/user/profile', 'private')
        
        # Check that the Authorization header is correct
        expected_auth = 'token test_api_key_67890:test_access_token_12345'
        assert signed_request['headers']['Authorization'] == expected_auth
        
        print("✓ Authentication header format is correct")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up test cache file
        if cache_path.exists():
            cache_path.unlink()
            print(f"\nCleaned up test cache file: {cache_path}")

def test_no_cache_fallback():
    """Test behavior when no cache file exists"""
    
    print("\n=== No Cache Fallback Test ===")
    
    # Ensure no cache file exists
    cache_path = Path.home() / '.cache' / 'ccxt-zerodha' / 'token.json'
    if cache_path.exists():
        cache_path.unlink()
    
    try:
        import ccxt
        
        # Test with no cache and no config
        print("Test: No cache, no config credentials")
        exchange = ccxt.zerodha({})
        
        # Should have empty credentials
        assert exchange.apiKey is None or exchange.apiKey == ''
        assert exchange.access_token is None or exchange.access_token == ''
        
        print("✓ No credentials when cache and config are empty")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing session-based authentication for Zerodha CCXT...")
    
    success1 = test_session_based_auth()
    success2 = test_no_cache_fallback()
    
    if success1 and success2:
        print("\n✓ All session-based authentication tests passed!")
        print("\nThe CCXT implementation now works with:")
        print("- api_key and access_token from cache (no secret needed)")
        print("- Session-based authentication using 'token api_key:access_token' format")
        print("- Automatic credential loading from ~/.cache/ccxt-zerodha/token.json")
    else:
        print("\n✗ Some tests failed!")
        sys.exit(1) 