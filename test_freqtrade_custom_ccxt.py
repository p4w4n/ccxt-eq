#!/usr/bin/env python3

import sys
import os

def test_custom_ccxt_path():
    """Test adding our custom CCXT to the Python path"""
    
    print("=== Testing Custom CCXT Path ===")
    
    # Add our custom CCXT to the beginning of sys.path
    custom_ccxt_path = os.path.join(os.path.dirname(__file__), 'python')
    sys.path.insert(0, custom_ccxt_path)
    
    print(f"Added to path: {custom_ccxt_path}")
    
    try:
        import ccxt
        print(f"✓ CCXT imported successfully")
        print(f"CCXT file location: {ccxt.__file__}")
        
        # Check if it's our version
        if 'ccxt-eq/python' in ccxt.__file__:
            print("✓ Now using our custom CCXT implementation")
        else:
            print("✗ Still using system CCXT")
            
        # Test zerodha import
        try:
            from ccxt import zerodha
            print(f"✓ Zerodha implementation found")
            
            # Test instantiation
            exchange = zerodha()
            print(f"✓ Zerodha instantiated successfully: {exchange}")
            
            # Test async
            import ccxt.async_support as ccxt_async
            async_exchange = ccxt_async.zerodha()
            print(f"✓ Async zerodha instantiated successfully: {async_exchange}")
            
            return True
            
        except Exception as e:
            print(f"✗ Error with zerodha: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except ImportError as e:
        print(f"✗ CCXT import failed: {e}")
        return False

def show_freqtrade_instructions():
    """Show instructions for making Freqtrade use our custom CCXT"""
    
    print("\n=== Instructions for Freqtrade ===")
    print("To make Freqtrade use our custom CCXT implementation:")
    print()
    print("1. Set PYTHONPATH environment variable:")
    print(f"   set PYTHONPATH={os.path.abspath('python')}")
    print()
    print("2. Or modify Freqtrade's Python path in your config:")
    print("   Add this to your Freqtrade config:")
    print(f"   \"python_path\": \"{os.path.abspath('python')}\"")
    print()
    print("3. Or run Freqtrade with:")
    print(f"   python -c \"import sys; sys.path.insert(0, '{os.path.abspath('python')}'); import freqtrade.main; freqtrade.main.main()\"")
    print()
    print("4. Or create a wrapper script that sets the path before importing Freqtrade")

if __name__ == "__main__":
    success = test_custom_ccxt_path()
    show_freqtrade_instructions()
    
    if success:
        print("\n✓ Custom CCXT path test passed!")
    else:
        print("\n✗ Custom CCXT path test failed!")
        sys.exit(1) 