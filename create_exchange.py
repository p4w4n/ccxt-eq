#!/usr/bin/env python3
"""
CCXT Exchange Generator

This script automates the creation of a new exchange implementation for CCXT.
It generates all necessary files across all supported languages and provides
a structured approach to implementing stock exchanges.

Usage:
    python create_exchange.py --name myexchange --config config.json
    python create_exchange.py --interactive

Author: CCXT Exchange Integration Guide
Version: 1.0.0
"""

import os
import sys
import json
import argparse
import shutil
from pathlib import Path
from typing import Dict, Any, List
import re

class ExchangeGenerator:
    """Main class for generating exchange implementations"""
    
    def __init__(self):
        self.ccxt_root = Path.cwd()
        self.templates_dir = self.ccxt_root / "templates"
        self.config = {}
        
    def load_config(self, config_path: str = None) -> Dict[str, Any]:
        """Load configuration from file or interactive input"""
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            return self.interactive_config()
    
    def interactive_config(self) -> Dict[str, Any]:
        """Interactive configuration collection"""
        print("🚀 CCXT Exchange Generator")
        print("=" * 50)
        print("Let's gather information about your exchange...\n")
        
        config = {}
        
        # Basic exchange information
        config['exchange_name'] = self.get_input(
            "Exchange ID (lowercase, no spaces)", 
            validator=self.validate_exchange_name
        )
        
        config['exchange_display_name'] = self.get_input(
            "Exchange Display Name", 
            default=config['exchange_name'].title()
        )
        
        config['exchange_description'] = self.get_input(
            "Short Description",
            default=f"{config['exchange_display_name']} API implementation for CCXT"
        )
        
        config['exchange_long_description'] = self.get_input(
            "Long Description (optional)",
            default=f"Complete API integration for {config['exchange_display_name']} stock exchange",
            required=False
        )
        
        # Location and URLs
        config['country_code'] = self.get_input(
            "Country Code (2-letter ISO)",
            validator=self.validate_country_code
        )
        
        config['country_name'] = self.get_input("Country Name")
        
        config['website_url'] = self.get_input(
            "Website URL", 
            validator=self.validate_url
        )
        
        config['docs_url'] = self.get_input(
            "API Documentation URL", 
            validator=self.validate_url
        )
        
        config['fees_url'] = self.get_input(
            "Fees Information URL (optional)", 
            default=f"{config['website_url']}/fees",
            required=False
        )
        
        config['logo_url'] = self.get_input(
            "Logo URL (optional)",
            default=f"{config['website_url']}/logo.png",
            required=False
        )
        
        # API Configuration
        config['public_api_url'] = self.get_input(
            "Public API Base URL",
            validator=self.validate_url
        )
        
        config['private_api_url'] = self.get_input(
            "Private API Base URL",
            default=config['public_api_url']
        )
        
        config['api_version'] = self.get_input(
            "API Version",
            default="v1"
        )
        
        # Rate limiting
        config['rate_limit'] = int(self.get_input(
            "Rate Limit (milliseconds between requests)",
            default="100",
            validator=self.validate_number
        ))
        
        config['rate_limit_description'] = self.get_input(
            "Rate Limit Description",
            default=f"{1000 // config['rate_limit']} requests per second"
        )
        
        # Authentication
        config['requires_api_key'] = self.get_bool_input(
            "Requires API Key?", 
            default=True
        )
        
        config['requires_secret'] = self.get_bool_input(
            "Requires API Secret?", 
            default=True
        )
        
        config['requires_password'] = self.get_bool_input(
            "Requires Password/Access Token?", 
            default=False
        )
        
        # Fees
        config['maker_fee'] = self.get_input(
            "Maker Fee (as decimal, e.g., 0.001 for 0.1%)",
            default="0.001",
            validator=self.validate_decimal
        )
        
        config['taker_fee'] = self.get_input(
            "Taker Fee (as decimal, e.g., 0.001 for 0.1%)",
            default="0.001",
            validator=self.validate_decimal
        )
        
        # Symbol format
        config['symbol_format'] = self.get_input(
            "Symbol Format Description",
            default="EXCHANGE:SYMBOL/CURRENCY"
        )
        
        config['symbol_example'] = self.get_input(
            "Symbol Example",
            default="NSE:INFY/INR"
        )
        
        # Authentication description
        config['auth_description'] = self.get_input(
            "Authentication Description",
            default="API Key and Secret based authentication"
        )
        
        # Timeframes
        print("\n📊 Configuring Timeframes")
        print("Enter the exchange's API timeframe values:")
        
        timeframes = {
            '1m': 'minute',
            '3m': '3minute', 
            '5m': '5minute',
            '10m': '10minute',
            '15m': '15minute',
            '30m': '30minute',
            '1h': '60minute',
            '1d': 'day'
        }
        
        for tf, default in timeframes.items():
            config[f'timeframe_{tf}'] = self.get_input(
                f"Timeframe for {tf}",
                default=default
            )
        
        # Limits
        config['ohlcv_limit'] = int(self.get_input(
            "OHLCV Fetch Limit (max candles per request)",
            default="1000",
            validator=self.validate_number
        ))
        
        config['ticker_limit'] = int(self.get_input(
            "Ticker Fetch Limit",
            default="1000", 
            validator=self.validate_number
        ))
        
        config['tickers_limit'] = int(self.get_input(
            "Tickers Fetch Limit",
            default="1000",
            validator=self.validate_number
        ))
        
        return config
    
    def get_input(self, prompt: str, default: str = None, validator=None, required: bool = True) -> str:
        """Get user input with validation"""
        while True:
            if default:
                user_input = input(f"{prompt} [{default}]: ").strip()
                if not user_input:
                    user_input = default
            else:
                user_input = input(f"{prompt}: ").strip()
            
            if not user_input and required:
                print("❌ This field is required. Please try again.")
                continue
            
            if validator and user_input:
                if not validator(user_input):
                    continue
            
            return user_input
    
    def get_bool_input(self, prompt: str, default: bool = True) -> bool:
        """Get boolean input from user"""
        default_str = "Y/n" if default else "y/N"
        while True:
            response = input(f"{prompt} [{default_str}]: ").strip().lower()
            if not response:
                return default
            if response in ['y', 'yes', 'true', '1']:
                return True
            elif response in ['n', 'no', 'false', '0']:
                return False
            print("❌ Please answer with y/yes or n/no")
    
    def validate_exchange_name(self, name: str) -> bool:
        """Validate exchange name"""
        if not re.match(r'^[a-z][a-z0-9_]*$', name):
            print("❌ Exchange name must start with a letter and contain only lowercase letters, numbers, and underscores")
            return False
        if len(name) < 3:
            print("❌ Exchange name must be at least 3 characters long")
            return False
        if len(name) > 20:
            print("❌ Exchange name must be no more than 20 characters long")
            return False
        return True
    
    def validate_country_code(self, code: str) -> bool:
        """Validate country code"""
        if not re.match(r'^[A-Z]{2}$', code.upper()):
            print("❌ Country code must be 2 uppercase letters (e.g., US, IN, GB)")
            return False
        return True
    
    def validate_url(self, url: str) -> bool:
        """Validate URL format"""
        if not re.match(r'https?://.+', url):
            print("❌ URL must start with http:// or https://")
            return False
        return True
    
    def validate_number(self, value: str) -> bool:
        """Validate numeric input"""
        try:
            int(value)
            return True
        except ValueError:
            print("❌ Please enter a valid number")
            return False
    
    def validate_decimal(self, value: str) -> bool:
        """Validate decimal input"""
        try:
            float(value)
            return True
        except ValueError:
            print("❌ Please enter a valid decimal number")
            return False
    
    def generate_exchange(self, config: Dict[str, Any]) -> None:
        """Generate the complete exchange implementation"""
        print(f"\n🔧 Generating {config['exchange_name']} exchange...")
        
        # Create TypeScript implementation
        self.create_typescript_exchange(config)
        
        # Update exchanges.json
        self.update_exchanges_json(config)
        
        # Generate API interface
        self.generate_api_interface(config)
        
        # Create test files
        self.create_test_files(config)
        
        # Create documentation
        self.create_documentation(config)
        
        # Create example files
        self.create_examples(config)
        
        print(f"\n✅ Exchange {config['exchange_name']} generated successfully!")
        print("\n📋 Next Steps:")
        print("1. Review and customize the generated TypeScript file")
        print("2. Implement the API endpoint mappings")
        print("3. Add authentication logic")
        print("4. Test with real API credentials")
        print("5. Run transpilation: npm run transpile")
        print("6. Test in all languages")
        print("7. Create pull request")
    
    def create_typescript_exchange(self, config: Dict[str, Any]) -> None:
        """Create the main TypeScript exchange file"""
        template_path = self.templates_dir / "exchange_template.ts"
        output_path = self.ccxt_root / "ts" / "src" / f"{config['exchange_name']}.ts"
        
        print(f"📝 Creating TypeScript implementation: {output_path}")
        
        # Read template
        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")
        
        with open(template_path, 'r') as f:
            template_content = f.read()
        
        # Replace placeholders
        content = self.replace_placeholders(template_content, config)
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(output_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Created: {output_path}")
    
    def replace_placeholders(self, content: str, config: Dict[str, Any]) -> str:
        """Replace template placeholders with actual values"""
        replacements = {
            '{{EXCHANGE_NAME}}': config['exchange_name'],
            '{{EXCHANGE_DISPLAY_NAME}}': config['exchange_display_name'],
            '{{EXCHANGE_DESCRIPTION}}': config['exchange_description'],
            '{{EXCHANGE_LONG_DESCRIPTION}}': config['exchange_long_description'],
            '{{COUNTRY_CODE}}': config['country_code'].upper(),
            '{{COUNTRY_NAME}}': config['country_name'],
            '{{WEBSITE_URL}}': config['website_url'],
            '{{DOCS_URL}}': config['docs_url'],
            '{{FEES_URL}}': config['fees_url'],
            '{{LOGO_URL}}': config['logo_url'],
            '{{PUBLIC_API_URL}}': config['public_api_url'],
            '{{PRIVATE_API_URL}}': config['private_api_url'],
            '{{API_VERSION}}': config['api_version'],
            '{{RATE_LIMIT}}': str(config['rate_limit']),
            '{{RATE_LIMIT_DESCRIPTION}}': config['rate_limit_description'],
            '{{REQUIRES_API_KEY}}': str(config['requires_api_key']).lower(),
            '{{REQUIRES_SECRET}}': str(config['requires_secret']).lower(),
            '{{REQUIRES_PASSWORD}}': str(config['requires_password']).lower(),
            '{{MAKER_FEE}}': config['maker_fee'],
            '{{TAKER_FEE}}': config['taker_fee'],
            '{{SYMBOL_FORMAT}}': config['symbol_format'],
            '{{SYMBOL_EXAMPLE}}': config['symbol_example'],
            '{{AUTH_DESCRIPTION}}': config['auth_description'],
            '{{TIMEFRAME_1M}}': config['timeframe_1m'],
            '{{TIMEFRAME_3M}}': config['timeframe_3m'],
            '{{TIMEFRAME_5M}}': config['timeframe_5m'],
            '{{TIMEFRAME_10M}}': config['timeframe_10m'],
            '{{TIMEFRAME_15M}}': config['timeframe_15m'],
            '{{TIMEFRAME_30M}}': config['timeframe_30m'],
            '{{TIMEFRAME_1H}}': config['timeframe_1h'],
            '{{TIMEFRAME_1D}}': config['timeframe_1d'],
            '{{OHLCV_LIMIT}}': str(config['ohlcv_limit']),
            '{{TICKER_LIMIT}}': str(config['ticker_limit']),
            '{{TICKERS_LIMIT}}': str(config['tickers_limit']),
        }
        
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)
        
        return content
    
    def update_exchanges_json(self, config: Dict[str, Any]) -> None:
        """Update exchanges.json to register the new exchange"""
        exchanges_file = self.ccxt_root / "exchanges.json"
        
        print(f"📝 Updating exchanges registry: {exchanges_file}")
        
        if exchanges_file.exists():
            with open(exchanges_file, 'r') as f:
                exchanges_data = json.load(f)
        else:
            exchanges_data = {"ids": [], "ws": []}
        
        # Add to IDs if not already present
        if config['exchange_name'] not in exchanges_data["ids"]:
            exchanges_data["ids"].append(config['exchange_name'])
            exchanges_data["ids"].sort()
        
        # Write back
        with open(exchanges_file, 'w') as f:
            json.dump(exchanges_data, f, indent=2)
        
        print(f"✅ Updated: {exchanges_file}")
    
    def generate_api_interface(self, config: Dict[str, Any]) -> None:
        """Generate the abstract API interface"""
        print("🔧 Run the following command to generate API interface:")
        print("npm run emitAPITs")
    
    def create_test_files(self, config: Dict[str, Any]) -> None:
        """Create test files for the exchange"""
        tests_dir = self.ccxt_root / "tests"
        tests_dir.mkdir(exist_ok=True)
        
        # Basic functionality test
        basic_test_content = f'''#!/usr/bin/env python3

import ccxt
import asyncio
from pprint import pprint

def test_basic_functionality():
    """Test basic {config['exchange_name']} functionality"""
    exchange = ccxt.{config['exchange_name']}({{
        'apiKey': 'your_api_key',
        'secret': 'your_secret',
        'sandbox': True,  # Use sandbox if available
        'verbose': True,
    }})
    
    try:
        # Test market data
        markets = exchange.fetch_markets()
        print(f"✓ Fetched {{len(markets)}} markets")
        
        if markets:
            symbol = markets[0]['symbol']
            
            # Test ticker
            ticker = exchange.fetch_ticker(symbol)
            print(f"✓ Fetched ticker for {{symbol}}: {{ticker['last']}}")
            
            # Test OHLCV
            ohlcv = exchange.fetch_ohlcv(symbol, '1d', limit=10)
            print(f"✓ Fetched {{len(ohlcv)}} OHLCV records")
        
        print("✅ All basic tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {{e}}")
        raise

async def test_async_functionality():
    """Test async functionality"""
    exchange = ccxt.async_support.{config['exchange_name']}({{
        'apiKey': 'your_api_key',
        'secret': 'your_secret',
        'sandbox': True,
    }})
    
    try:
        markets = await exchange.fetch_markets()
        print(f"✓ Async: Fetched {{len(markets)}} markets")
        
        await exchange.close()
        print("✅ Async tests passed!")
        
    except Exception as e:
        print(f"❌ Async test failed: {{e}}")
        raise

if __name__ == '__main__':
    print("🧪 Testing {config['exchange_display_name']} Implementation")
    test_basic_functionality()
    asyncio.run(test_async_functionality())
'''
        
        test_file = tests_dir / f"test_{config['exchange_name']}_basic.py"
        with open(test_file, 'w') as f:
            f.write(basic_test_content)
        
        print(f"✅ Created: {test_file}")
    
    def create_documentation(self, config: Dict[str, Any]) -> None:
        """Create documentation for the exchange"""
        docs_dir = self.ccxt_root / "wiki" / "exchanges"
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        doc_content = f'''# {config['exchange_display_name']}

## Overview

{config['exchange_long_description']}

## API Documentation

Link to official API documentation: {config['docs_url']}

## Supported Features

### Market Data
- [x] fetchMarkets
- [x] fetchTicker
- [x] fetchTickers
- [x] fetchOHLCV
- [ ] fetchOrderBook
- [ ] fetchTrades

### Trading
- [x] fetchBalance
- [x] createOrder
- [x] cancelOrder
- [x] fetchOrder
- [x] fetchOpenOrders
- [x] fetchClosedOrders
- [x] fetchMyTrades

### Other
- [ ] fetchDepositAddress
- [ ] withdraw
- [ ] fetchDeposits
- [ ] fetchWithdrawals

## Authentication

### API Credentials
1. Sign up at [{config['exchange_display_name']}]({config['website_url']})
2. Go to API section in your account
3. Create new API key
4. Enable required permissions

### Configuration
```javascript
const exchange = new ccxt.{config['exchange_name']}({{
    'apiKey': 'your_api_key',
    'secret': 'your_api_secret',
    'sandbox': true, // Use sandbox for testing
}});
```

## Markets and Symbols

### Symbol Format
- CCXT format: `{config['symbol_format']}`
- Example: `{config['symbol_example']}`

### Available Markets
- Spot trading
- Margin trading (if supported)
- Futures (if supported)

## Rate Limits

- {config['rate_limit_description']}

## Fees

### Trading Fees
- Maker: {float(config['maker_fee']) * 100}%
- Taker: {float(config['taker_fee']) * 100}%

### Deposit/Withdrawal Fees
See: {config['fees_url']}

## Error Handling

Common error codes and their meanings:
- `INVALID_API_KEY`: Invalid API credentials
- `INSUFFICIENT_BALANCE`: Not enough balance for the operation
- `ORDER_NOT_FOUND`: Order ID not found
- `RATE_LIMIT_EXCEEDED`: Too many requests

## Examples

### Fetch Markets
```javascript
const markets = await exchange.fetchMarkets();
console.log(markets);
```

### Place Order
```javascript
const order = await exchange.createOrder('{config['symbol_example']}', 'limit', 'buy', 0.001, 50000);
console.log(order);
```

## Notes

- Always test with sandbox mode first
- Some endpoints may require additional verification
- WebSocket support is planned for future releases

## Support

- Official documentation: {config['docs_url']}
- CCXT issues: https://github.com/ccxt/ccxt/issues
- Exchange support: support@{config['exchange_name']}.com
'''
        
        doc_file = docs_dir / f"{config['exchange_name']}.md"
        with open(doc_file, 'w') as f:
            f.write(doc_content)
        
        print(f"✅ Created: {doc_file}")
    
    def create_examples(self, config: Dict[str, Any]) -> None:
        """Create example files"""
        examples_dir = self.ccxt_root / "examples"
        
        # JavaScript example
        js_dir = examples_dir / "js"
        js_dir.mkdir(parents=True, exist_ok=True)
        
        js_content = f'''
'use strict';

const ccxt = require('../../js/ccxt.js');

async function example() {{
    const exchange = new ccxt.{config['exchange_name']}({{
        'apiKey': process.env.{config['exchange_name'].upper()}_API_KEY,
        'secret': process.env.{config['exchange_name'].upper()}_SECRET,
        'sandbox': true,
    }});

    try {{
        // Fetch markets
        const markets = await exchange.fetchMarkets();
        console.log('Markets:', markets.length);

        // Fetch ticker
        if (markets.length > 0) {{
            const symbol = markets[0].symbol;
            const ticker = await exchange.fetchTicker(symbol);
            console.log('Ticker:', ticker);
        }}

        // Fetch balance
        const balance = await exchange.fetchBalance();
        console.log('Balance:', balance);

    }} catch (error) {{
        console.error('Error:', error);
    }}
}}

example();
'''
        
        js_file = js_dir / f"{config['exchange_name']}-basic.js"
        with open(js_file, 'w') as f:
            f.write(js_content)
        
        # Python example
        py_dir = examples_dir / "py"
        py_dir.mkdir(parents=True, exist_ok=True)
        
        py_content = f'''
import ccxt
import os

def main():
    exchange = ccxt.{config['exchange_name']}({{
        'apiKey': os.getenv('{config['exchange_name'].upper()}_API_KEY'),
        'secret': os.getenv('{config['exchange_name'].upper()}_SECRET'),
        'sandbox': True,
    }})

    try:
        # Fetch markets
        markets = exchange.fetch_markets()
        print(f'Markets: {{len(markets)}}')

        # Fetch ticker
        if markets:
            symbol = markets[0]['symbol']
            ticker = exchange.fetch_ticker(symbol)
            print(f'Ticker: {{ticker}}')

        # Fetch balance
        balance = exchange.fetch_balance()
        print(f'Balance: {{balance}}')

    except Exception as e:
        print(f'Error: {{e}}')

if __name__ == '__main__':
    main()
'''
        
        py_file = py_dir / f"{config['exchange_name']}-basic.py"
        with open(py_file, 'w') as f:
            f.write(py_content)
        
        print(f"✅ Created: {js_file}")
        print(f"✅ Created: {py_file}")
    
    def save_config(self, config: Dict[str, Any], filename: str = None) -> None:
        """Save configuration to file"""
        if not filename:
            filename = f"{config['exchange_name']}_config.json"
        
        with open(filename, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"💾 Configuration saved to: {filename}")

def main():
    parser = argparse.ArgumentParser(
        description="Generate a new CCXT exchange implementation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_exchange.py --interactive
  python create_exchange.py --name myexchange --config myexchange_config.json
  python create_exchange.py --name myexchange --country US --api-url https://api.myexchange.com
        """
    )
    
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Interactive mode - asks questions to gather configuration'
    )
    
    parser.add_argument(
        '--name', '-n',
        help='Exchange name (lowercase, no spaces)'
    )
    
    parser.add_argument(
        '--config', '-c',
        help='Configuration file path (JSON)'
    )
    
    parser.add_argument(
        '--save-config',
        help='Save configuration to specified file'
    )
    
    args = parser.parse_args()
    
    generator = ExchangeGenerator()
    
    try:
        if args.interactive or not args.config:
            config = generator.interactive_config()
        else:
            config = generator.load_config(args.config)
        
        if args.name:
            config['exchange_name'] = args.name
        
        if args.save_config:
            generator.save_config(config, args.save_config)
        
        generator.generate_exchange(config)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 