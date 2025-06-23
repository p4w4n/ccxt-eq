#!/usr/bin/env python3

import sys
import os

def check_ccxt_installation():
    """Check which CCXT installation is being used"""
    
    print("=== CCXT Installation Check ===")
    
    # Check if ccxt is installed
    try:
        import ccxt
        print(f"✓ CCXT imported successfully")
        print(f"CCXT version: {ccxt.__version__}")
        print(f"CCXT file location: {ccxt.__file__}")
        
        # Check if our zerodha implementation exists
        try:
            from ccxt import zerodha
            print(f"✓ Zerodha implementation found at: {zerodha.__file__}")
            
            # Check if it's our version (should be in the python directory)
            if 'ccxt-eq/python' in zerodha.__file__:
                print("✓ Using our custom CCXT implementation")
            else:
                print("✗ Using system CCXT installation, not our custom version")
                
        except ImportError as e:
            print(f"✗ Zerodha implementation not found: {e}")
            
    except ImportError as e:
        print(f"✗ CCXT not installed: {e}")
        return False
    
    print("\n=== Python Path ===")
    for i, path in enumerate(sys.path):
        print(f"{i}: {path}")
    
    print("\n=== Environment Variables ===")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    
    return True

def test_zerodha_import():
    """Test if we can import and instantiate zerodha"""
    
    print("\n=== Zerodha Import Test ===")
    
    try:
        import ccxt
        
        # Test sync import
        print("Testing sync import...")
        exchange = ccxt.zerodha()
        print(f"✓ Sync zerodha instantiated: {exchange}")
        
        # Test async import
        print("Testing async import...")
        import ccxt.async_support as ccxt_async
        async_exchange = ccxt_async.zerodha()
        print(f"✓ Async zerodha instantiated: {async_exchange}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error importing zerodha: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Checking CCXT installation for Freqtrade...")
    
    success1 = check_ccxt_installation()
    success2 = test_zerodha_import()
    
    if success1 and success2:
        print("\n✓ All checks passed!")
    else:
        print("\n✗ Some checks failed!")
        sys.exit(1) 