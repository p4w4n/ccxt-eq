#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script to verify Zerodha credentials work with REST API
"""

import sys
import os

# Add the ccxt directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'python'))

# Hardcoded credentials for testing
ZERODHA_API_KEY = 'ugnbfdntjkbuddb8qh'
ZERODHA_ACCESS_TOKEN = 'vWtF7uDJRhikR7du0KtWK8qxKJgazOpG'

async def test_credentials():
    """Test if the credentials work with REST API"""
    
    try:
        from ccxt.async_support import zerodha
        
        print("🔧 Testing Zerodha REST API credentials...")
        
        exchange = zerodha({
            'apiKey': ZERODHA_API_KEY,
            'password': ZERODHA_ACCESS_TOKEN,  # access_token is stored in password field
            'sandbox': False,
            'enableRateLimit': True,
        })
        
        # Test basic API call
        print("📊 Testing fetch_ticker...")
        ticker = await exchange.fetch_ticker(13710)
        print(f"✅ Ticker received: {ticker['symbol']} - ₹{ticker['last']}")
        
        # Test fetch_tickers
        print("📊 Testing fetch_tickers...")
        tickers = await exchange.fetch_tickers(['NSE:INFY/INR', 'NSE:TCS/INR'])
        print(f"✅ Tickers received: {len(tickers)} symbols")
        
        # Test fetch_ohlcv
        print("📈 Testing fetch_ohlcv...")
        ohlcv = await exchange.fetch_ohlcv('NSE:INFY/INR', '1d', limit=5)
        print(f"✅ OHLCV received: {len(ohlcv)} candles")
        
        await exchange.close()
        
        print("\n🎉 All REST API tests passed!")
        print("💡 The credentials are valid for REST API calls.")
        print("🔌 WebSocket connection issues might be due to:")
        print("   - Access token expiration")
        print("   - Different authentication method for WebSocket")
        print("   - WebSocket URL format")
        
        return True
        
    except Exception as e:
        print(f"❌ REST API test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function"""
    print("🧪 Testing Zerodha Credentials")
    print("=" * 50)
    
    success = await test_credentials()
    
    if success:
        print("\n✅ Credentials are working with REST API!")
        print("🔌 For WebSocket, you may need to:")
        print("   1. Generate a fresh access token")
        print("   2. Check if WebSocket requires different authentication")
        print("   3. Verify the WebSocket endpoint URL")
    else:
        print("\n❌ Credentials are not working!")
        print("💡 Please check your API key and access token.")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main()) 