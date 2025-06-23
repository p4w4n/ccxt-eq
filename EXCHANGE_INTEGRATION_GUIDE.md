# Complete Guide: Adding Stock Exchanges to CCXT

This comprehensive guide will walk you through adding a new stock exchange to the CCXT library, using the Zerodha implementation as a reference. This guide is specifically tailored for **stock exchanges** (equity trading platforms) and provides beginner-friendly step-by-step instructions, pre-built templates, and automation scripts.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Understanding CCXT Architecture](#understanding-ccxt-architecture)
3. [Step 1: Research and Planning](#step-1-research-and-planning)
4. [Step 2: Development Environment Setup](#step-2-development-environment-setup)
5. [Step 3: Implementation](#step-3-implementation)
6. [Step 4: Testing](#step-4-testing)
7. [Step 5: Transpilation and Build](#step-5-transpilation-and-build)
8. [Step 6: Documentation](#step-6-documentation)
9. [Step 7: Quality Assurance](#step-7-quality-assurance)
10. [Step 8: Submission](#step-8-submission)
11. [Templates and Automation](#templates-and-automation)
12. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements
- **Node.js** (v18 or higher)
- **Python** 3.8+
- **Git**
- **npm** or **yarn**
- **Code editor** (VS Code recommended)

### Knowledge Requirements
- Basic **JavaScript/TypeScript**
- **REST API** concepts
- **Stock trading** fundamentals (markets, orders, tickers, positions)
- **HTTP** request/response patterns
- Basic **Git** usage

### Exchange Requirements
- **API documentation** for the target exchange
- **Test API credentials** (API key, secret, access token)
- Understanding of the exchange's **authentication** mechanism
- Knowledge of **symbol formats** and **market structure**

## Understanding CCXT Architecture

### The Multi-Language Architecture

CCXT supports 6 programming languages using a **source-generated** approach:

```
TypeScript (SOURCE) → Transpiler → JavaScript
                                 → Python (sync)  
                                 → Python (async)
                                 → PHP (sync)
                                 → PHP (async)
                                 → C#
                                 → Go
```

**Key Principle:** You write **one TypeScript implementation**, and CCXT automatically generates equivalent code in all other languages.

### Directory Structure

```
ccxt/
├── ts/src/                     # 🎯 PRIMARY: TypeScript source
│   ├── abstract/              # Auto-generated API interfaces
│   ├── base/                  # Base classes and utilities
│   ├── yourexchange.ts        # Your exchange implementation
│   └── zerodha.ts            # Reference implementation
├── js/src/                    # Generated JavaScript
├── python/ccxt/               # Generated Python (sync)
├── python/ccxt/async_support/ # Generated Python (async)
├── php/                       # Generated PHP (sync)
├── php/async/                 # Generated PHP (async)
├── cs/ccxt/                   # Generated C#
├── go/v4/                     # Generated Go
├── exchanges.json             # Exchange registry
└── templates/                 # Templates and tools
```

### The Implementation Flow

1. **Create** TypeScript implementation (`ts/src/yourexchange.ts`)
2. **Register** exchange in `exchanges.json`
3. **Generate** abstract interface (`ts/src/abstract/yourexchange.ts`)
4. **Transpile** to all languages
5. **Update** entry points (`js/ccxt.js`, `python/ccxt/__init__.py`, etc.)
6. **Test** across languages
7. **Document** and provide examples

## Step 1: Research and Planning

### 1.1 Exchange API Analysis Checklist

Before writing any code, thoroughly analyze your target exchange's API:

#### 📋 API Documentation Review
- [ ] **Base URLs** for REST API (public/private)
- [ ] **API version** and versioning scheme
- [ ] **Authentication** method (API key, OAuth, session-based, etc.)
- [ ] **Rate limiting** rules and headers
- [ ] **Request/response formats** (JSON, XML, CSV, etc.)
- [ ] **Error codes** and error handling
- [ ] **Pagination** methods for large datasets
- [ ] **Time synchronization** requirements

#### 📋 Market Data Endpoints
- [ ] **Instruments/Markets** listing endpoint
- [ ] **Ticker/Quote** data (real-time prices)
- [ ] **Order book** data (bid/ask depths)
- [ ] **Historical data** (OHLCV candles)
- [ ] **Trades** history (recent transactions)

#### 📋 Account Management Endpoints
- [ ] **User profile** information
- [ ] **Account balance** (cash and holdings)
- [ ] **Positions** (current holdings)
- [ ] **Margins** and buying power

#### 📋 Trading Endpoints
- [ ] **Place orders** (market, limit, stop-loss)
- [ ] **Cancel orders**
- [ ] **Modify orders**
- [ ] **Order status** and details
- [ ] **Order history** (filled/cancelled orders)
- [ ] **Trade history** (execution details)

#### 📋 Market Structure Analysis
- [ ] **Available markets** (NSE, BSE, MCX, etc.)
- [ ] **Instrument types** (EQ, FUT, OPT, COMMODITY)
- [ ] **Symbol naming** conventions
- [ ] **Tick sizes** and **lot sizes**
- [ ] **Trading sessions** and hours
- [ ] **Settlement cycles** (T+2, T+1, etc.)
- [ ] **Corporate actions** handling

### 1.2 Create Your Implementation Plan

Document your findings in a structured plan:

```markdown
# [Exchange Name] Integration Plan

## Exchange Details
- **Name**: XYZ Stock Exchange
- **Country**: India
- **Website**: https://xyz.com
- **API Docs**: https://api.xyz.com/docs

## API Configuration
- **Base URL**: https://api.xyz.com/v3
- **Authentication**: API Key + Secret + Access Token
- **Rate Limit**: 10 requests/second (100ms between requests)
- **Data Format**: JSON

## Symbol Format
- **CCXT Format**: NSE:INFY/INR
- **API Format**: instrument_token or tradingsymbol
- **Example**: NSE equity INFY (Infosys) in Indian Rupees

## Supported Features
- [x] Spot Trading (Equity)
- [x] Fetch Markets
- [x] Fetch Balance (Cash + Holdings)
- [x] Create/Cancel Orders
- [x] Historical Data (OHLCV)
- [ ] Futures & Options (Future enhancement)
- [ ] WebSocket (Future enhancement)

## Authentication Flow
1. Daily access token generation (manual/automated)
2. API key + access token for requests
3. Request signing with API secret

## Error Handling
- TokenException → AuthenticationError
- OrderException → InvalidOrder
- MarginException → InsufficientFunds
```

## Step 2: Development Environment Setup

### 2.1 Clone and Setup CCXT

```bash
# Clone the CCXT repository
git clone https://github.com/ccxt/ccxt.git
cd ccxt

# Install dependencies
npm install

# Verify the build system works
npm run build
```

### 2.2 Create Your Feature Branch

```bash
# Create a new branch for your exchange
git checkout -b add-yourexchange-integration

# Or for specific exchange
git checkout -b add-nse-integration
```

### 2.3 Understand the Zerodha Reference

Study the Zerodha implementation as it's designed for Indian stock markets:

```bash
# Examine the Zerodha implementation
less ts/src/zerodha.ts
less python/ccxt/zerodha.py
```

Key patterns to understand:
- **Authentication** with daily token renewal
- **Symbol mapping** (NSE:INFY/INR format)
- **Market data parsing** for equity instruments
- **Order management** for stock trading
- **Balance handling** (cash + stock holdings)

## Step 3: Implementation

### 3.1 Use the Automated Generator

The fastest way to start is using the automation script:

```bash
# Interactive mode (recommended for beginners)
python create_exchange.py --interactive

# Or with config file
python create_exchange.py --name yourexchange --config config.json
```

This will generate:
- ✅ TypeScript implementation with placeholders
- ✅ Abstract interface definition
- ✅ Test files
- ✅ Documentation templates
- ✅ Example usage files
- ✅ Exchange registration

### 3.2 Manual Implementation (Advanced)

If you prefer manual implementation, create `ts/src/yourexchange.ts`:

```typescript
// ts/src/yourexchange.ts
import Exchange from './abstract/yourexchange.js';
import { TICK_SIZE } from './base/functions/number.js';
import { 
    AuthenticationError, 
    ExchangeError, 
    RateLimitExceeded, 
    InvalidOrder, 
    InsufficientFunds, 
    BadRequest, 
    PermissionDenied, 
    NetworkError 
} from './base/errors.js';

import type { 
    Int, OrderSide, OrderType, Trade, OHLCV, Order, 
    Str, Ticker, Balances, Tickers, Market, Dict, int, Num 
} from './base/types.js';

/**
 * @class yourexchange
 * @augments Exchange
 * @description Your Exchange API implementation for CCXT
 */
export default class yourexchange extends Exchange {
    
    public describe () {
        return this.deepExtend (super.describe (), {
            'id': 'yourexchange',
            'name': 'Your Exchange',
            'countries': [ 'IN' ], // India
            'rateLimit': 100, // 10 requests per second
            'version': 'v3',
            'certified': false,
            'pro': false,
            'has': {
                'CORS': undefined,
                'spot': true,
                'margin': false,
                'swap': false,
                'future': false,
                'option': false,
                'cancelOrder': true,
                'createOrder': true,
                'fetchBalance': true,
                'fetchClosedOrders': true,
                'fetchMarkets': true,
                'fetchMyTrades': true,
                'fetchOHLCV': true,
                'fetchOpenOrders': true,
                'fetchOrder': true,
                'fetchTicker': true,
                'fetchTickers': true,
            },
            'timeframes': {
                '1m': 'minute',
                '5m': '5minute',
                '15m': '15minute',
                '1h': '60minute',
                '1d': 'day',
            },
            'urls': {
                'logo': 'https://yourexchange.com/logo.png',
                'api': {
                    'public': 'https://api.yourexchange.com',
                    'private': 'https://api.yourexchange.com',
                },
                'www': 'https://yourexchange.com',
                'doc': ['https://docs.yourexchange.com'],
                'fees': 'https://yourexchange.com/pricing',
            },
            'api': {
                'public': {
                    'get': [
                        'instruments',
                        'quote',
                        'quote/ltp',
                        'quote/ohlc',
                    ],
                },
                'private': {
                    'get': [
                        'user/profile',
                        'user/margins',
                        'portfolio/positions',
                        'portfolio/holdings',
                        'orders',
                        'orders/{order_id}',
                        'trades',
                    ],
                    'post': [
                        'orders/{variety}',
                    ],
                    'put': [
                        'orders/{variety}/{order_id}',
                    ],
                    'delete': [
                        'orders/{variety}/{order_id}',
                    ],
                },
            },
            'fees': {
                'trading': {
                    'tierBased': false,
                    'percentage': true,
                    'maker': this.parseNumber ('0.0'),
                    'taker': this.parseNumber ('0.0325'), // 0.0325%
                },
            },
            'requiredCredentials': {
                'apiKey': true,
                'secret': true,
                'password': false, // Access token
                'login': false,
            },
            'exceptions': {
                'exact': {
                    'TokenException': AuthenticationError,
                    'OrderException': InvalidOrder,
                    'MarginException': InsufficientFunds,
                },
                'broad': {
                    'Invalid API credentials': AuthenticationError,
                    'Insufficient funds': InsufficientFunds,
                    'Rate limit exceeded': RateLimitExceeded,
                },
            },
            'precisionMode': TICK_SIZE,
        });
    }

    // Implement required methods
    async fetchMarkets (params = {}): Promise<Market[]> {
        // TODO: Implement market fetching
        const response = await this.publicGetInstruments (params);
        return this.parseMarkets (response);
    }

    async fetchBalance (params = {}): Promise<Balances> {
        // TODO: Implement balance fetching
        await this.loadMarkets ();
        const response = await this.privateGetUserMargins (params);
        return this.parseBalance (response);
    }

    async fetchTicker (symbol: string, params = {}): Promise<Ticker> {
        // TODO: Implement ticker fetching
        await this.loadMarkets ();
        const market = this.market (symbol);
        const response = await this.publicGetQuote (params);
        return this.parseTicker (response, market);
    }

    // TODO: Implement other required methods
    // - fetchOHLCV
    // - createOrder
    // - cancelOrder
    // - fetchOrder
    // - fetchOpenOrders
    // - fetchClosedOrders
    // - fetchMyTrades

    // TODO: Implement parsing methods
    // - parseMarket
    // - parseBalance
    // - parseTicker
    // - parseOrder
    // - parseTrade
    // - parseOHLCV

    // TODO: Implement authentication
    sign (path: string, api = 'public', method = 'GET', params = {}, headers: any = undefined, body: any = undefined): any {
        // TODO: Implement request signing
    }

    // TODO: Implement error handling  
    handleErrors (code: int, reason: string, url: string, method: string, headers: Dict, body: string, response: any, requestHeaders: any, requestBody: any): any {
        // TODO: Implement error handling
    }
}
```

### 3.3 Register Your Exchange

Add your exchange to `exchanges.json`:

```json
{
  "ids": [
    "alpaca",
    "yourexchange",
    "zerodha",
    "zonda"
  ]
}
```

### 3.4 Generate Abstract Interface

Generate the abstract interface from your API definition:

```bash
npm run emitAPITs
```

This creates `ts/src/abstract/yourexchange.ts` with method signatures.

## Step 4: Testing

### 4.1 Create Test Configuration

Create a test configuration file:

```json
// test_config.json
{
  "yourexchange": {
    "apiKey": "your_api_key",
    "secret": "your_api_secret", 
    "password": "your_access_token",
    "sandbox": true
  }
}
```

### 4.2 Basic Functionality Tests

```javascript
// test_yourexchange.js
const ccxt = require('./js/ccxt.js');

(async () => {
    const exchange = new ccxt.yourexchange({
        apiKey: 'your_api_key',
        secret: 'your_secret',
        password: 'your_access_token',
        sandbox: true,
    });

    try {
        // Test public methods
        console.log('Loading markets...');
        const markets = await exchange.loadMarkets();
        console.log(`Loaded ${Object.keys(markets).length} markets`);

        console.log('Fetching ticker...');
        const ticker = await exchange.fetchTicker('NSE:INFY/INR');
        console.log('Ticker:', ticker);

        // Test private methods
        console.log('Fetching balance...');
        const balance = await exchange.fetchBalance();
        console.log('Balance:', balance);

    } catch (error) {
        console.error('Test failed:', error);
    }
})();
```

### 4.3 Run Tests

```bash
# Test your specific exchange
node test_yourexchange.js

# Run CCXT test suite (after transpilation)
npm run test yourexchange
```

## Step 5: Transpilation and Build

### 5.1 Build TypeScript

```bash
# Build TypeScript only
npm run build-ts

# Or build everything
npm run build
```

### 5.2 Transpile to All Languages

```bash
# Transpile your specific exchange
npx tsx build/transpile.ts yourexchange

# Transpile everything (slow)
npm run transpile
```

### 5.3 Verify Generated Code

Check that code was generated correctly:

```bash
# Check JavaScript
ls js/src/yourexchange.js

# Check Python
ls python/ccxt/yourexchange.py

# Check PHP
ls php/yourexchange.php
```

## Step 6: Documentation

### 6.1 Exchange Documentation

Create `wiki/exchanges/yourexchange.md`:

```markdown
# Your Exchange

## Overview
Your Exchange is a leading stock trading platform in India...

## Supported Features
- Spot trading
- Real-time quotes
- Historical data
- Order management

## Authentication
Your Exchange uses API key authentication...

## Rate Limits
- 10 requests per second
- Daily limits apply

## Examples

### Python
```python
import ccxt

exchange = ccxt.yourexchange({
    'apiKey': 'your_api_key',
    'secret': 'your_secret',
    'password': 'your_access_token',
})

markets = exchange.load_markets()
ticker = exchange.fetch_ticker('NSE:INFY/INR')
```

### JavaScript
```javascript
const ccxt = require('ccxt');

const exchange = new ccxt.yourexchange({
    apiKey: 'your_api_key',
    secret: 'your_secret', 
    password: 'your_access_token',
});

const markets = await exchange.loadMarkets();
const ticker = await exchange.fetchTicker('NSE:INFY/INR');
```
```

### 6.2 API Reference

The API reference is automatically generated from your TypeScript implementation.

## Step 7: Quality Assurance

### 7.1 Code Quality Checklist

- [ ] **All required methods implemented**
- [ ] **Error handling** for all API calls
- [ ] **Rate limiting** respected
- [ ] **Symbol parsing** works correctly
- [ ] **Precision handling** for prices and amounts
- [ ] **Timezone handling** for timestamps
- [ ] **Authentication** works reliably
- [ ] **Market data** parses correctly
- [ ] **Order management** functions properly
- [ ] **Balance calculation** is accurate

### 7.2 Performance Testing

```javascript
// performance_test.js
const ccxt = require('./js/ccxt.js');

(async () => {
    const exchange = new ccxt.yourexchange({ /* credentials */ });
    
    console.time('loadMarkets');
    await exchange.loadMarkets();
    console.timeEnd('loadMarkets');
    
    console.time('fetchTicker');
    await exchange.fetchTicker('NSE:INFY/INR');
    console.timeEnd('fetchTicker');
})();
```

### 7.3 Cross-Language Testing

Test your implementation in multiple languages:

```bash
# Python test
python -c "import ccxt; exchange = ccxt.yourexchange(); print(exchange.id)"

# PHP test  
php -r "require 'vendor/autoload.php'; $exchange = new \ccxt\yourexchange(); echo $exchange->id;"
```

## Step 8: Submission

### 8.1 Pre-Submission Checklist

- [ ] **All tests pass**
- [ ] **Documentation complete**
- [ ] **Examples provided**
- [ ] **Code follows CCXT conventions**
- [ ] **No lint errors**
- [ ] **Performance acceptable**
- [ ] **Cross-language compatibility verified**

### 8.2 Create Pull Request

```bash
# Commit your changes
git add .
git commit -m "Add YourExchange integration

- Implement spot trading support
- Add market data and order management
- Include comprehensive documentation
- Add test examples"

# Push to your fork
git push origin add-yourexchange-integration

# Create pull request on GitHub
```

### 8.3 Pull Request Template

```markdown
## Exchange: Your Exchange

### Summary
This PR adds support for Your Exchange, a major stock trading platform in India.

### Features Implemented
- [x] Spot trading (equity)
- [x] Market data (tickers, OHLCV)
- [x] Account management (balance, positions)
- [x] Order management (create, cancel, fetch)
- [x] Authentication and error handling

### Testing
- [x] Unit tests pass
- [x] Integration tests with live API
- [x] Cross-language compatibility verified
- [x] Performance tests acceptable

### Documentation
- [x] Exchange documentation
- [x] Code examples
- [x] API reference
```

## Templates and Automation

### Available Tools

1. **Automation Script**: `python create_exchange.py --interactive`
   - Interactive configuration
   - Template generation
   - File structure creation
   - Exchange registration

2. **TypeScript Template**: `templates/exchange_template.ts`
   - Complete exchange class template
   - Placeholder replacements
   - Best practices included

3. **Test Templates**: Auto-generated test files
   - Basic functionality tests
   - Performance tests
   - Error handling tests

### Using the Automation Script

```bash
# Interactive mode (recommended)
python create_exchange.py --interactive

# Follow the prompts:
# - Exchange name and details
# - API configuration
# - Authentication method
# - Supported features
# - Rate limits and fees
```

The script will generate:
- Complete TypeScript implementation
- Abstract interface
- Test files
- Documentation templates
- Example usage files
- Updated exchange registry

## Troubleshooting

### Common Issues

#### 1. Transpilation Fails
```bash
# Check TypeScript errors
npm run build-ts

# Common fix: Check import statements
# Make sure all imports use .js extensions:
import Exchange from './abstract/yourexchange.js';
```

#### 2. Authentication Errors
```bash
# Verify credentials format
# Check API documentation for exact requirements
# Test with exchange's official tools first
```

#### 3. Rate Limiting Issues
```bash
# Adjust rateLimit in describe()
'rateLimit': 200, // Increase from 100ms to 200ms

# Implement exponential backoff in error handling
```

#### 4. Symbol Parsing Issues
```bash
# Debug symbol parsing
console.log('Market:', market);
console.log('Symbol:', this.symbol(market));

# Check symbol format matches exchange API
```

### Getting Help

1. **CCXT Documentation**: https://docs.ccxt.com
2. **GitHub Issues**: https://github.com/ccxt/ccxt/issues
3. **Discord Community**: https://discord.gg/ccxt
4. **Stack Overflow**: Tag `ccxt`

### Best Practices

1. **Start Small**: Implement basic features first
2. **Follow Zerodha**: Use as reference for stock exchanges
3. **Test Frequently**: Test after each method implementation
4. **Read Docs**: Study exchange API documentation thoroughly  
5. **Use Templates**: Leverage provided templates and automation
6. **Ask Questions**: Engage with CCXT community for help

---

## Conclusion

Adding a stock exchange to CCXT requires careful planning, methodical implementation, and thorough testing. By following this guide and using the provided templates and automation tools, you can successfully integrate any stock exchange into the CCXT ecosystem.

The key to success is understanding both the CCXT architecture and your target exchange's API thoroughly before beginning implementation. Take time in the research phase - it will save significant debugging time later.

Good luck with your integration! 🚀