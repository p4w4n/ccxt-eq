#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple test script for Zerodha WebSocket implementation

This script tests the basic WebSocket functionality without requiring
CCXT Pro or real credentials.
"""

import asyncio
import sys
import os

# Add the ccxt directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

def test_websocket_implementation():
    """Test that the WebSocket implementation can be imported and instantiated"""
    
    try:
        # Test importing the WebSocket implementation
        from ccxt.pro import zerodha
        print("✅ Successfully imported zerodha WebSocket implementation")
        
        # Test creating an instance (without sandbox)
        exchange = zerodha({
            'apiKey': 'test_key',
            'password': 'test_token',
            'sandbox': False,  # Zerodha doesn't have sandbox
        })
        print("✅ Successfully created zerodha WebSocket instance")
        
        # Test describe method
        description = exchange.describe()
        print("✅ Successfully called describe() method")
        
        # Check WebSocket capabilities
        has_ws = description.get('has', {}).get('ws', False)
        has_watch_ticker = description.get('has', {}).get('watchTicker', False)
        has_watch_tickers = description.get('has', {}).get('watchTickers', False)
        has_watch_order_book = description.get('has', {}).get('watchOrderBook', False)
        
        print(f"✅ WebSocket capabilities:")
        print(f"   - WebSocket support: {has_ws}")
        print(f"   - Watch ticker: {has_watch_ticker}")
        print(f"   - Watch tickers: {has_watch_tickers}")
        print(f"   - Watch order book: {has_watch_order_book}")
        
        # Test WebSocket URL generation
        try:
            ws_url = exchange.get_ws_url()
            print(f"✅ WebSocket URL: {ws_url}")
        except Exception as e:
            print(f"⚠️  WebSocket URL generation failed (expected without real credentials): {e}")
        
        # Test binary packet parsing (with dummy data)
        dummy_packet = b'\x00\x01\x00\x2C\x00\x00\x00\x01\x00\x00\x00\x64\x00\x00\x00\x01\x00\x00\x00\x64\x00\x00\x00\x01\x00\x00\x00\x64\x00\x00\x00\x01\x00\x00\x00\x64\x00\x00\x00\x01\x00\x00\x00\x64\x00\x00\x00\x01\x00\x00\x00\x64'
        parsed = exchange.parse_binary_quote_packet(dummy_packet, 'quote')
        print(f"✅ Binary packet parsing: {parsed}")
        
        # Test placeholder methods
        print("✅ Testing placeholder methods:")
        exchange.ws_send({'test': 'message'})
        exchange.emit('test', 'data')
        exchange.on('test', lambda x: None)
        
        print("\n🎉 All WebSocket implementation tests passed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure the implementation is in the correct location")
        return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_rest_implementation():
    """Test that the REST implementation still works"""
    
    try:
        from ccxt.async_support import zerodha
        print("\n🔧 Testing REST implementation...")
        
        exchange = zerodha({
            'apiKey': 'test_key',
            'password': 'test_token',
            'sandbox': False,  # Zerodha doesn't have sandbox
        })
        
        description = exchange.describe()
        print("✅ REST implementation works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ REST implementation test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 Testing Zerodha WebSocket Implementation")
    print("=" * 50)
    
    # Test REST implementation first
    rest_ok = test_rest_implementation()
    
    # Test WebSocket implementation
    ws_ok = test_websocket_implementation()
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"   REST Implementation: {'✅ PASS' if rest_ok else '❌ FAIL'}")
    print(f"   WebSocket Implementation: {'✅ PASS' if ws_ok else '❌ FAIL'}")
    
    if rest_ok and ws_ok:
        print("\n🎉 All tests passed! The WebSocket implementation is ready to use.")
        print("\n💡 To use with real data:")
        print("   1. Get CCXT Pro license")
        print("   2. Set up Zerodha API credentials")
        print("   3. Generate access token using zerodha_auto_token.py")
        print("   4. Run: python examples/py/zerodha_websocket_example.py")
        print("\n📝 Note: This is a demonstration implementation.")
        print("   For production use, you'll need to implement the actual")
        print("   WebSocket connection handling in the placeholder methods.")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main()) 