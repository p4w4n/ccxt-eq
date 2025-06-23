#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Complete CCXT Integration Test for Zerodha

This test verifies that all three implementations are working correctly:
1. Synchronous REST API
2. Asynchronous REST API  
3. WebSocket API

Usage:
    python test_complete_integration.py
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the ccxt directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

def test_sync_implementation():
    """Test the synchronous REST API implementation"""
    print("🔍 Testing Synchronous REST API...")
    
    from ccxt.zerodha import zerodha
    
    try:
        # Initialize exchange
        exchange = zerodha({
            'sandbox': False,
            'enableRateLimit': True,
        })
        
        # Test credential loading
        print("  📋 Testing credential loading...")
        if not exchange.apiKey or not exchange.access_token:
            print("  ❌ Credentials not loaded from cache")
            return False
        print(f"  ✅ API Key: {exchange.apiKey[:10]}...")
        print(f"  ✅ Access Token: {exchange.access_token[:10]}...")
        
        # Test market loading
        print("  📊 Testing market loading...")
        markets = exchange.load_markets()
        print(f"  ✅ Loaded {len(markets)} markets")
        
        # Test ticker fetching
        print("  💰 Testing ticker fetching...")
        # Find a market with a valid symbol
        test_symbol = None
        for symbol, market in markets.items():
            if 'NSE:' in symbol and '/INR' in symbol:
                test_symbol = symbol
                break
        
        if test_symbol:
            ticker = exchange.fetch_ticker(test_symbol)
            print(f"  ✅ Fetched ticker for {test_symbol}: ₹{ticker['last']}")
        else:
            print("  ⚠️  No suitable test symbol found")
        
        print("  ✅ Synchronous implementation test completed")
        return True
        
    except Exception as e:
        print(f"  ❌ Synchronous implementation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_async_implementation():
    """Test the asynchronous REST API implementation"""
    print("🔍 Testing Asynchronous REST API...")
    
    from ccxt.async_support.zerodha import zerodha
    
    try:
        # Initialize exchange
        exchange = zerodha({
            'sandbox': False,
            'enableRateLimit': True,
        })
        
        # Test credential loading
        print("  📋 Testing credential loading...")
        if not exchange.apiKey or not exchange.access_token:
            print("  ❌ Credentials not loaded from cache")
            return False
        print(f"  ✅ API Key: {exchange.apiKey[:10]}...")
        print(f"  ✅ Access Token: {exchange.access_token[:10]}...")
        
        # Test market loading
        print("  📊 Testing market loading...")
        markets = await exchange.load_markets()
        print(f"  ✅ Loaded {len(markets)} markets")
        
        # Test ticker fetching
        print("  💰 Testing ticker fetching...")
        # Find a market with a valid symbol
        test_symbol = None
        for symbol, market in markets.items():
            if 'NSE:' in symbol and '/INR' in symbol:
                test_symbol = symbol
                break
        
        if test_symbol:
            ticker = await exchange.fetch_ticker(test_symbol)
            print(f"  ✅ Fetched ticker for {test_symbol}: ₹{ticker['last']}")
        else:
            print("  ⚠️  No suitable test symbol found")
        
        # Test OHLCV fetching
        print("  📈 Testing OHLCV fetching...")
        if test_symbol:
            ohlcv = await exchange.fetch_ohlcv(test_symbol, '1d', limit=5)
            print(f"  ✅ Fetched {len(ohlcv)} OHLCV candles")
        
        await exchange.close()
        print("  ✅ Asynchronous implementation test completed")
        return True
        
    except Exception as e:
        print(f"  ❌ Asynchronous implementation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_websocket_implementation():
    """Test the WebSocket API implementation"""
    print("🔍 Testing WebSocket API...")
    
    from ccxt.pro.zerodha import zerodha
    
    try:
        # Initialize exchange
        exchange = zerodha({
            'sandbox': False,
            'enableRateLimit': True,
        })
        
        # Test credential loading
        print("  📋 Testing credential loading...")
        if not exchange.apiKey or not exchange.access_token:
            print("  ❌ Credentials not loaded from cache")
            return False
        print(f"  ✅ API Key: {exchange.apiKey[:10]}...")
        print(f"  ✅ Access Token: {exchange.access_token[:10]}...")
        
        # Test market loading
        print("  📊 Testing market loading...")
        await exchange.load_markets()
        print(f"  ✅ Loaded {len(exchange.markets)} markets")
        
        # Test WebSocket connection
        print("  🔌 Testing WebSocket connection...")
        await exchange.connect()
        print("  ✅ WebSocket connected successfully")
        
        # Test subscription
        print("  📡 Testing subscription...")
        test_token = 738561  # NIFTY 50
        await exchange.subscribe_to_token(test_token)
        print(f"  ✅ Subscribed to instrument token: {test_token}")
        
        # Wait a bit for any data
        print("  ⏳ Waiting for data (5 seconds)...")
        await asyncio.sleep(5)
        
        # Test unsubscribe
        print("  📡 Testing unsubscription...")
        await exchange.unsubscribe_from_token(test_token)
        print(f"  ✅ Unsubscribed from instrument token: {test_token}")
        
        await exchange.close()
        print("  ✅ WebSocket implementation test completed")
        return True
        
    except Exception as e:
        print(f"  ❌ WebSocket implementation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print("🚀 Complete CCXT Integration Test for Zerodha")
    print("=" * 60)
    
    results = []
    
    # Test synchronous implementation
    sync_result = test_sync_implementation()
    results.append(('Synchronous REST API', sync_result))
    print()
    
    # Test asynchronous implementation
    async_result = await test_async_implementation()
    results.append(('Asynchronous REST API', async_result))
    print()
    
    # Test WebSocket implementation
    ws_result = await test_websocket_implementation()
    results.append(('WebSocket API', ws_result))
    print()
    
    # Summary
    print("📊 Test Results Summary")
    print("=" * 60)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All tests passed! CCXT integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    return all_passed

if __name__ == "__main__":
    asyncio.run(main()) 