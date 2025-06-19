# How to Add a New Exchange to CCXT

This guide provides comprehensive documentation on adding a new exchange to the CCXT library. CCXT is a multi-language cryptocurrency trading library that supports TypeScript/JavaScript, Python, PHP, C#, and Go.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Project Structure](#project-structure)
4. [Step-by-Step Guide](#step-by-step-guide)
5. [Exchange Implementation](#exchange-implementation)
6. [Testing Your Exchange](#testing-your-exchange)
7. [Transpilation Process](#transpilation-process)
8. [Common Pitfalls](#common-pitfalls)
9. [Submission Process](#submission-process)
10. [Example: Zerodha Exchange Implementation](#example-zerodha-exchange-implementation)

## Overview

CCXT uses a source/generated code architecture where exchanges are primarily written in TypeScript and then transpiled to other languages (JavaScript, Python, PHP, C#, Go). The source of truth is the TypeScript implementation in the `ts/src/` directory.

### Key Principles

1. **TypeScript First**: All exchanges are implemented in TypeScript first
2. **Unified API**: All exchanges must implement the same standardized methods
3. **Code Generation**: JavaScript, Python, PHP, C#, and Go versions are generated from TypeScript
4. **Rate Limiting**: Built-in rate limiting must be respected
5. **Error Handling**: Standardized error types must be used

## Prerequisites

Before adding a new exchange, ensure you have:

1. **Node.js** (v18 or higher)
2. **npm** or **yarn**
3. **Git**
4. **Python 3.x** (for testing Python transpilation)
5. **PHP 7.x+** (for testing PHP transpilation)
6. Exchange API documentation
7. API credentials for testing (API key, secret, etc.)

## Project Structure

```
ccxt/
├── ts/src/                    # TypeScript source files
│   ├── abstract/             # Abstract exchange classes
│   ├── base/                 # Base classes and utilities
│   └── [exchange].ts         # Exchange implementations
├── js/src/                   # Generated JavaScript files
├── python/ccxt/              # Generated Python files
├── php/                      # Generated PHP files
├── cs/                       # Generated C# files
└── go/                       # Generated Go files
```

## Step-by-Step Guide

### 1. Fork and Clone CCXT

```bash
git fork https://github.com/ccxt/ccxt
git clone https://github.com/YOUR_USERNAME/ccxt
cd ccxt
npm install
```

### 2. Create Exchange Files

Create the following files:

- `ts/src/myexchange.ts` - Main implementation
- `ts/src/abstract/myexchange.ts` - Abstract class

### 3. Run Build Commands

```bash
npm run build        # Build all
npm run build-ts     # Build TypeScript only
```

## Exchange Implementation

### Exchange Class Structure

```typescript
// ts/src/myexchange.ts
import Exchange from './abstract/myexchange.js';
import { ExchangeError } from './base/errors.js';

export default class myexchange extends Exchange {
    describe() {
        return this.deepExtend(super.describe(), {
            'id': 'myexchange',
            'name': 'My Exchange',
            'countries': ['US'],
            'version': 'v1',
            'rateLimit': 100,
            'has': {
                'spot': true,
                'fetchBalance': true,
                'fetchTicker': true,
                // ... other capabilities
            },
            'urls': {
                'api': 'https://api.myexchange.com',
                'www': 'https://myexchange.com',
                'doc': 'https://docs.myexchange.com',
            },
            // ... more configuration
        });
    }
    
    // Implement required methods
    async fetchMarkets(params = {}) {
        // Implementation
    }
    
    async fetchBalance(params = {}) {
        // Implementation
    }
    
    // ... other methods
}
```

### Required Methods

At minimum, implement these methods:

1. `describe()` - Exchange configuration and capabilities
2. `fetchMarkets()` - Load trading pairs
3. `fetchBalance()` - Get account balance
4. `fetchTicker()` - Get current prices
5. `fetchOHLCV()` - Get historical data
6. `createOrder()` - Place orders
7. `cancelOrder()` - Cancel orders
8. `fetchOrder()` - Get order details
9. `fetchOpenOrders()` - Get open orders
10. `fetchClosedOrders()` - Get order history

### Parsing Methods

Implement parsing methods for consistent data format:

```typescript
parseTicker(ticker, market = undefined) {
    return {
        'symbol': market['symbol'],
        'timestamp': timestamp,
        'datetime': this.iso8601(timestamp),
        'high': this.safeNumber(ticker, 'high'),
        'low': this.safeNumber(ticker, 'low'),
        'bid': this.safeNumber(ticker, 'bid'),
        'ask': this.safeNumber(ticker, 'ask'),
        'last': this.safeNumber(ticker, 'last'),
        'close': this.safeNumber(ticker, 'last'),
        'baseVolume': this.safeNumber(ticker, 'volume'),
        'info': ticker,
    };
}
```

## Testing Your Exchange

### Unit Tests

Create test files:
- `ts/src/test/Exchange/test.myexchange.ts`

### Manual Testing

```javascript
// test-exchange.js
const ccxt = require('./js/ccxt.js');

(async () => {
    const exchange = new ccxt.myexchange({
        apiKey: 'YOUR_API_KEY',
        secret: 'YOUR_SECRET',
    });
    
    // Test public methods
    const markets = await exchange.loadMarkets();
    console.log(markets);
    
    // Test private methods
    const balance = await exchange.fetchBalance();
    console.log(balance);
})();
```

## Transpilation Process

CCXT uses an AST-based transpiler to convert TypeScript to other languages:

```bash
npm run build           # Build all languages
npm run build-python    # Build Python only
npm run build-php       # Build PHP only
```

## Common Pitfalls

1. **Rate Limiting**: Always respect API rate limits
2. **Timestamp Handling**: Use milliseconds for all timestamps
3. **Number Precision**: Use string numbers for financial data
4. **Error Mapping**: Map exchange-specific errors to CCXT errors
5. **Symbol Format**: Use BASE/QUOTE format (e.g., BTC/USDT)

## Submission Process

1. Write comprehensive tests
2. Update documentation
3. Run linting: `npm run lint`
4. Create a pull request
5. Address review feedback

## Example: Zerodha Exchange Implementation

As a practical example, we've implemented the Zerodha exchange for Indian equity markets. This implementation demonstrates how to adapt CCXT's cryptocurrency-focused framework for traditional stock markets.

### Key Features of Zerodha Implementation

1. **Indian Stock Market Support**: Handles NSE and BSE equities
2. **Unique Authentication**: Daily token-based authentication system
3. **Symbol Convention**: Uses `EXCHANGE:SYMBOL/INR` format (e.g., `NSE:RELIANCE/INR`)
4. **Product Types**: Supports CNC (delivery), MIS (intraday) order types

### Files Created

1. **TypeScript Implementation**:
   - `ts/src/zerodha.ts` - Main exchange class
   - `ts/src/abstract/zerodha.ts` - Abstract base class

2. **JavaScript Implementation**:
   - `js/src/zerodha.js` - Transpiled JavaScript
   - `js/src/abstract/zerodha.js` - Abstract JavaScript class
   - `js/src/zerodha.d.ts` - TypeScript declarations
   - `js/src/abstract/zerodha.d.ts` - Abstract TypeScript declarations

3. **Python Implementation**:
   - `python/ccxt/zerodha.py` - Python implementation
   - `python/ccxt/abstract/zerodha.py` - Abstract Python class

4. **Helper Scripts**:
   - `scripts/zerodha_generate_token.py` - Daily token generation script

5. **Examples**:
   - `examples/config_zerodha.json` - Freqtrade configuration example
   - `examples/strategies/SimpleRSI_NSE.py` - Sample trading strategy

### Zerodha-Specific Considerations

1. **Authentication Flow**:
   ```python
   # Daily token generation required
   python scripts/zerodha_generate_token.py
   ```

2. **Order Parameters**:
   ```javascript
   // Zerodha requires product type
   await exchange.createOrder('NSE:INFY/INR', 'limit', 'buy', 10, 1500, {
       'product': 'CNC'  // Required: CNC for delivery, MIS for intraday
   });
   ```

3. **Rate Limits**:
   - Historical data: 3 requests/second
   - Order placement: 10 requests/second
   - General API: 10 requests/second

### Using Zerodha with Freqtrade

1. **Configuration**:
   ```json
   {
       "exchange": {
           "name": "zerodha",
           "key": "YOUR_API_KEY",
           "secret": "YOUR_API_SECRET",
           "password": "DAILY_ACCESS_TOKEN"
       }
   }
   ```

2. **Daily Workflow**:
   - Generate token each morning after 6:00 AM IST
   - Update configuration with new token
   - Restart trading bot

### Future Enhancements

The Zerodha implementation is designed to be extensible:

- **F&O Support**: Symbol format already supports futures/options
- **WebSocket**: Can be added for real-time data
- **Advanced Orders**: GTT, CO, BO order types

This implementation serves as a template for adding other traditional brokers to CCXT, demonstrating how to handle:
- Session-based authentication
- Traditional market conventions
- Regulatory requirements
- Market hours and holidays

## Contributing

Please read [CONTRIBUTING.md](https://github.com/ccxt/ccxt/blob/master/CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## Resources

- [CCXT Documentation](https://docs.ccxt.com)
- [CCXT GitHub](https://github.com/ccxt/ccxt)
- [Exchange API Documentation](https://github.com/ccxt/ccxt/wiki/Exchange-Markets-By-Country)
- [CCXT Pro](https://ccxt.pro) - WebSocket implementations

## Support

- GitHub Issues: https://github.com/ccxt/ccxt/issues
- Discord: https://discord.gg/ccxt
- Stack Overflow: Tag with `ccxt`

---

Remember: The goal is to provide a consistent, reliable interface across all exchanges while respecting each exchange's unique characteristics and requirements. 