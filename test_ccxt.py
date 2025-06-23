#!/usr/bin/env python3
"""Test CCXT installation and functionality"""

try:
    import ccxt
    print("✅ CCXT import successful")
    
    # Test basic attributes
    if hasattr(ccxt, '__version__'):
        print(f"✅ CCXT version: {ccxt.__version__}")
    else:
        print("⚠️  CCXT __version__ not found")
    
    # Test Precise import
    from ccxt import Precise
    print("✅ Precise import successful")
    
    # Test creating a Precise instance
    p = Precise('123.456')
    print(f"✅ Precise creation successful: {p}")
    
    # Test zerodha exchange
    try:
        exchange = ccxt.zerodha()
        print("✅ Zerodha exchange creation successful")
        print(f"   Exchange ID: {exchange.id}")
        print(f"   Exchange name: {exchange.name}")
    except Exception as e:
        print(f"❌ Zerodha exchange creation failed: {e}")
    
    # List available exchanges
    print(f"📊 Available exchanges: {len(ccxt.exchanges)} total")
    if 'zerodha' in ccxt.exchanges:
        print("✅ Zerodha is available in exchanges list")
    else:
        print("❌ Zerodha not found in exchanges list")
        
except ImportError as e:
    print(f"❌ CCXT import failed: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}") 