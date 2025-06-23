#!/usr/bin/env python3
"""
Zerodha Freqtrade Credential Setup Script

This script helps you set up your Zerodha API credentials in the Freqtrade configuration.
"""
import json
import os
import sys

def setup_credentials():
    """Set up Zerodha credentials in the configuration file"""
    
    # Find the config file
    config_files = [
        "freqtrade_zerodha_config.json",
        "config.json",
        "freqtrade_configs/config_nifty100.json"
    ]
    
    config_file = None
    for cf in config_files:
        if os.path.exists(cf):
            config_file = cf
            break
    
    if not config_file:
        print("❌ No configuration file found. Please create one first.")
        return False
    
    print(f"📄 Using config file: {config_file}")
    
    # Load the config
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
    except Exception as e:
        print(f"❌ Error reading config file: {e}")
        return False
    
    # Get credentials from user
    print("\n🔑 Setting up Zerodha API Credentials")
    print("Get these from: https://developers.kite.trade/apps/")
    print()
    
    api_key = input("Enter your Zerodha API Key: ").strip()
    api_secret = input("Enter your Zerodha API Secret: ").strip()
    
    print("\n🎫 Access Token Setup")
    print("Access tokens expire daily at 6 AM IST.")
    print("Generate new token from: https://kite.zerodha.com/connect/login")
    print()
    
    access_token = input("Enter your current Access Token: ").strip()
    
    if not all([api_key, api_secret, access_token]):
        print("❌ All credentials are required!")
        return False
    
    # Update the config
    if "exchange" not in config:
        config["exchange"] = {}
    
    if "ccxt_config" not in config["exchange"]:
        config["exchange"]["ccxt_config"] = {}
    
    config["exchange"]["ccxt_config"]["apiKey"] = api_key
    config["exchange"]["ccxt_config"]["secret"] = api_secret
    config["exchange"]["ccxt_config"]["password"] = access_token
    
    # Save the config
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)
        
        print(f"\n✅ Credentials saved to {config_file}")
        print("\n⚠️  Security Notice:")
        print("- Keep this config file secure")
        print("- Don't commit it to version control")
        print("- Update access token daily before 6 AM IST")
        
        return True
        
    except Exception as e:
        print(f"❌ Error saving config: {e}")
        return False

def test_credentials():
    """Test the credentials by loading markets"""
    print("\n🧪 Testing credentials...")
    
    try:
        import ccxt
        
        # Load config
        with open("freqtrade_zerodha_config.json", 'r') as f:
            config = json.load(f)
        
        exchange_config = config["exchange"]["ccxt_config"]
        
        # Create exchange instance
        exchange = ccxt.zerodha({
            'apiKey': exchange_config['apiKey'],
            'secret': exchange_config['secret'],
            'password': exchange_config['password'],
            'enableRateLimit': True,
            'rateLimit': 200,
        })
        
        # Test by loading markets
        print("📊 Loading markets...")
        markets = exchange.fetch_markets()
        
        print(f"✅ Success! Loaded {len(markets)} markets")
        print("🎯 Your credentials are working correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Credential test failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Verify your API key and secret")
        print("2. Generate a fresh access token")
        print("3. Check if your Kite app has the required permissions")
        
        return False

def main():
    print("🔧 Zerodha Freqtrade Setup")
    print("=" * 30)
    
    # Step 1: Set up credentials
    if setup_credentials():
        # Step 2: Test credentials
        test_credentials()
    
    print("\n📚 Next Steps:")
    print("1. Start Freqtrade with your config:")
    print("   freqtrade trade --config freqtrade_zerodha_config.json")
    print("2. Remember to update access token daily before market open")
    print("3. Monitor logs for any issues")

if __name__ == "__main__":
    main() 