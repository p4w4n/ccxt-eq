# -*- coding: utf-8 -*-

import hashlib
import json
from pathlib import Path
from datetime import datetime, time
import pytz

from ccxt.base.exchange import Exchange
from ccxt.base.precise import Precise
from ccxt.base.decimal_to_precision import TICK_SIZE, NO_PADDING
from ccxt.base.errors import (
    ExchangeError,
    AuthenticationError,
    PermissionDenied,
    BadRequest,
    InvalidOrder,
    InsufficientFunds,
    RateLimitExceeded,
    NetworkError,
    ExchangeNotAvailable
)
from ccxt.abstract.zerodha import ImplicitAPI


class zerodha(Exchange, ImplicitAPI):
    """
    Zerodha Kite Connect API v3 implementation for CCXT
    
    This implementation follows the comprehensive integration guide for Zerodha Kite Connect
    with Freqtrade. It provides a stateful session manager to handle daily token expiration
    and maps Indian equity trading to the CCXT unified API.
    
    Symbol Convention: {EXCHANGE}:{TRADINGSYMBOL}/{CURRENCY}
    Example: NSE:INFY/INR (Infosys on NSE in Indian Rupees)
    
    Authentication: Uses a daily-expiring access_token managed through a separate
    generate_token.py script due to Zerodha's manual login requirement.
    """

    def describe(self):
        return self.deep_extend(super(zerodha, self).describe(), {
            'id': 'zerodha',
            'name': 'Zerodha',
            'countries': ['IN'],  # India
            'version': 'v3',
            'rateLimit': 100,  # 10 requests per second = 100ms between requests
            'has': {
                'CORS': False,
                'spot': True,
                'margin': False,
                'swap': False,
                'future': False,  # Set to True when F&O is implemented
                'option': False,  # Set to True when F&O is implemented
                'addMargin': False,
                'borrowCrossMargin': False,
                'borrowIsolatedMargin': False,
                'cancelOrder': True,
                'cancelOrders': False,
                'createDepositAddress': False,
                'createOrder': True,
                'createStopLimitOrder': False,
                'createStopMarketOrder': False,
                'createStopOrder': False,
                'editOrder': False,
                'fetchBalance': True,
                'fetchBorrowInterest': False,
                'fetchCanceledOrders': False,
                'fetchClosedOrder': False,
                'fetchClosedOrders': True,
                'fetchCurrencies': False,
                'fetchDepositAddress': False,
                'fetchDeposits': False,
                'fetchFundingHistory': False,
                'fetchFundingRate': False,
                'fetchFundingRateHistory': False,
                'fetchFundingRates': False,
                'fetchIndexOHLCV': False,
                'fetchMarkets': True,
                'fetchMarkOHLCV': False,
                'fetchMyTrades': True,
                'fetchOHLCV': True,
                'fetchOpenOrder': False,
                'fetchOpenOrders': True,
                'fetchOrder': True,
                'fetchOrderBook': False,
                'fetchOrders': False,
                'fetchOrderTrades': False,
                'fetchPositions': False,
                'fetchPremiumIndexOHLCV': False,
                'fetchTicker': True,
                'fetchTickers': True,  # Emulated with multiple fetchTicker calls
                'fetchTime': False,
                'fetchTrades': False,
                'fetchTradingFee': False,
                'fetchTradingFees': False,
                'fetchWithdrawals': False,
                'repayCrossMargin': False,
                'repayIsolatedMargin': False,
                'setLeverage': False,
                'setMarginMode': False,
                'transfer': False,
                'withdraw': False,
            },
            'features': {
                'spot': {
                    'fetchOHLCV': {
                        'limit': 1000,  # Zerodha allows up to 1000 candles per request
                    },
                    'fetchTicker': {
                        'limit': 1000,
                    },
                    'fetchTickers': {
                        'limit': 1000,
                    },
                },
                'futures': {
                    'fetchOHLCV': {
                        'limit': 1000,
                    },
                    'fetchTicker': {
                        'limit': 1000,
                    },
                    'fetchTickers': {
                        'limit': 1000,
                    },
                },
            },
            'timeframes': {
                '1m': 'minute',
                '3m': '3minute',
                '5m': '5minute',
                '10m': '10minute',
                '15m': '15minute',
                '30m': '30minute',
                '1h': '60minute',
                '1d': 'day',
            },
            'urls': {
                'logo': 'https://zerodha.com/static/images/logo.svg',
                'api': {
                    'public': 'https://api.kite.trade',
                    'private': 'https://api.kite.trade',
                },
                'www': 'https://zerodha.com',
                'doc': [
                    'https://kite.trade/docs/connect/v3/',
                ],
                'fees': 'https://zerodha.com/pricing',
            },
            'api': {
                'public': {
                    'get': [
                        'instruments',
                        'instruments/{exchange}',
                        'quote',
                        'quote/ltp',
                        'quote/ohlc',
                    ],
                },
                'private': {
                    'get': [
                        'user/profile',
                        'user/margins',
                        'user/margins/{segment}',
                        'portfolio/positions',
                        'portfolio/holdings',
                        'orders',
                        'orders/{order_id}',
                        'trades',
                        'trades/{order_id}',
                        'instruments/historical/{instrument_token}/{interval}',
                    ],
                    'post': [
                        'orders/{variety}',
                        'orders/{variety}/{order_id}',
                        'portfolio/positions',
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
                    'tierBased': False,
                    'percentage': True,
                    'maker': self.parse_number('0.0'),
                    'taker': self.parse_number('0.0325'),  # 0.0325% per side for equity delivery
                },
            },
            'requiredCredentials': {
                'apiKey': False,  # Can be loaded from cache
                'secret': False,  # Not needed for session-based auth
                'password': False,  # Repurposed for access_token, can be loaded from cache
                'login': False,
                'privateKey': False,
                'walletAddress': False,
                'token': False,
            },
            'exceptions': {
                'exact': {
                    'TokenException': AuthenticationError,
                    'UserException': PermissionDenied,
                    'OrderException': InvalidOrder,
                    'InputException': BadRequest,
                    'MarginException': InsufficientFunds,
                    'HoldingException': InsufficientFunds,
                    'NetworkException': NetworkError,
                    'DataException': ExchangeError,
                    'GeneralException': ExchangeError,
                },
                'broad': {
                    'Invalid API credentials': AuthenticationError,
                    'Insufficient funds': InsufficientFunds,
                    'Order not found': InvalidOrder,
                    'Rate limit exceeded': RateLimitExceeded,
                },
            },
            'precisionMode': TICK_SIZE,
            'paddingMode': NO_PADDING,
        })

    def __init__(self, config={}):
        super(zerodha, self).__init__(config)
        self.token_cache_path = Path.home() / '.cache' / 'ccxt-zerodha' / 'session.json'
        self.token_cache_path.parent.mkdir(parents=True, exist_ok=True)
        # The 'password' field from config is repurposed for the access_token
        self.access_token = self.password
        self.login_time = None
        
        # Load credentials from cache if not provided in config
        if not self.apiKey or not self.access_token:
            self._load_credentials_from_cache()

    def _load_credentials_from_cache(self):
        """Load credentials from the cached token file"""
        try:
            if self.token_cache_path.exists():
                with open(self.token_cache_path, 'r') as f:
                    token_data = json.load(f)
                    if not self.apiKey:
                        self.apiKey = token_data.get('api_key')
                    if not self.access_token:
                        self.access_token = token_data.get('access_token')
                    if not self.login_time and token_data.get('login_time'):
                        self.login_time = self.parse8601(token_data.get('login_time'))
        except Exception as e:
            # Silently fail if cache loading fails
            pass

    def _is_token_expired(self):
        """Checks if the access token has expired (past 6 AM IST next day)."""
        if not self.access_token or not self.login_time:
            return True

        ist = pytz.timezone('Asia/Kolkata')
        now_ist = datetime.now(ist)
        expiry_time = time(6, 0)
        
        if hasattr(self.login_time, 'tzinfo') and self.login_time.tzinfo is not None:
            login_date = self.login_time.date()
        else:
            # If no timezone info, assume IST
            login_date = self.login_time.replace(tzinfo=ist).date()
        
        if now_ist.date() > login_date:
            # It's a day after the login date
            if now_ist.time() >= expiry_time:
                # It's after 6 AM on a subsequent day
                return True
        
        return False

    def fetch_markets(self, params={}):
        """
        retrieves data on all markets for zerodha
        @param {dict} params extra parameters specific to the exchange API endpoint
        @returns {dict} an array of objects representing market data
        """
        response = self.publicGetInstruments(params)
        markets = []
        
        # Handle CSV response - Zerodha returns CSV data
        if isinstance(response, str):
            # Parse CSV response
            import csv
            import io
            
            # Split by lines and parse each line
            lines = response.strip().split('\n')
            if len(lines) < 2:  # Need at least header + 1 data row
                return markets
            
            # Parse header
            header = lines[0].split(',')
            
            # Parse data rows
            for line in lines[1:]:
                try:
                    # Split by comma, but handle quoted fields properly
                    row = list(csv.reader([line]))[0]
                    
                    # Create market data dict
                    market_data = {}
                    for i, field in enumerate(row):
                        if i < len(header):
                            market_data[header[i]] = field
                    
                    # Process the market data
                    exchange = market_data.get('exchange', '')
                    trading_symbol = market_data.get('tradingsymbol', '')
                    instrument_type = market_data.get('instrument_type', '')
                    
                    # Focus on equity instruments for now (extensible to F&O later)
                    if instrument_type == 'EQ':
                        id = market_data.get('instrument_token', '')
                        tick_size = float(market_data.get('tick_size', 0.05))
                        lot_size = int(market_data.get('lot_size', 1))
                        
                        # Skip if no instrument token
                        if not id:
                            continue
                        
                        base = exchange + ':' + trading_symbol
                        quote = 'INR'
                        symbol = base + '/' + quote
                        
                        market = {
                            'id': id,
                            'symbol': symbol,
                            'base': base,
                            'quote': quote,
                            'settle': None,
                            'baseId': trading_symbol,
                            'quoteId': 'INR',
                            'settleId': None,
                            'type': 'spot',
                            'spot': True,
                            'margin': False,
                            'swap': False,
                            'future': False,
                            'option': False,
                            'active': True,
                            'contract': False,
                            'linear': None,
                            'inverse': None,
                            'contractSize': None,
                            'expiry': None,
                            'expiryDatetime': None,
                            'strike': None,
                            'optionType': None,
                            'precision': {
                                'amount': lot_size,
                                'price': tick_size,
                            },
                            'limits': {
                                'leverage': {
                                    'min': None,
                                    'max': None,
                                },
                                'amount': {
                                    'min': lot_size,
                                    'max': None,
                                },
                                'price': {
                                    'min': tick_size,
                                    'max': None,
                                },
                                'cost': {
                                    'min': None,
                                    'max': None,
                                },
                            },
                            'created': None,
                            'info': market_data,
                        }
                        markets.append(market)
                        
                except Exception as e:
                    # Log error but continue processing other markets
                    self.log(f"Error processing market data line: {e}")
                    continue
        else:
            # Handle JSON response (fallback)
            for instrument in response:
                try:
                    # Parse the instrument data
                    instrument_token = str(instrument.get('instrument_token', ''))
                    tradingsymbol = instrument.get('tradingsymbol', '')
                    name = instrument.get('name', '')
                    instrument_type = instrument.get('instrument_type', '')
                    exchange = instrument.get('exchange', '')
                    segment = instrument.get('segment', '')
                    
                    # Skip if essential fields are missing
                    if not instrument_token or not tradingsymbol or not exchange:
                        continue
                    
                    # Determine the base and quote currencies
                    if instrument_type == 'EQ':
                        # For equity, the symbol is the base currency
                        base = tradingsymbol
                        quote = 'INR'
                    elif instrument_type in ['FUT', 'OPT']:
                        # For futures/options, extract the underlying
                        base = tradingsymbol.split('-')[0] if '-' in tradingsymbol else tradingsymbol
                        quote = 'INR'
                    else:
                        # For other instruments, use the symbol as base
                        base = tradingsymbol
                        quote = 'INR'
                    
                    # Create the market ID
                    market_id = f"{base}/{quote}"
                    
                    # Create market object
                    market = {
                        'id': instrument_token,
                        'symbol': market_id,
                        'base': base,
                        'quote': quote,
                        'settle': None,
                        'baseId': tradingsymbol,
                        'quoteId': 'INR',
                        'settleId': None,
                        'type': 'spot' if instrument_type == 'EQ' else 'future' if instrument_type == 'FUT' else 'option',
                        'spot': instrument_type == 'EQ',
                        'margin': False,
                        'swap': False,
                        'future': instrument_type == 'FUT',
                        'option': instrument_type == 'OPT',
                        'active': True,
                        'contract': instrument_type in ['FUT', 'OPT'],
                        'linear': True,
                        'inverse': False,
                        'contractSize': 1,
                        'expiry': None,
                        'expiryDatetime': None,
                        'strike': None,
                        'optionType': None,
                        'settlementType': None,
                        'feeLoaded': False,
                        'info': instrument,
                    }
                    
                    markets.append(market)
                    
                except Exception as e:
                    # Skip malformed data
                    continue
        
        return markets

    def fetch_ticker(self, symbol, params={}):
        """
        Fetches a price ticker for a specific symbol
        
        @param {str} symbol unified symbol of the market to fetch the ticker for
        @param {dict} params extra parameters specific to the exchange API endpoint
        @returns {dict} a ticker structure
        """
        self.load_markets()
        market = self.market(symbol)
        
        # Zerodha quote endpoint expects format 'EXCHANGE:TRADINGSYMBOL'
        instrument = market['info']['exchange'] + ':' + market['info']['tradingsymbol']
        
        request = {
            'i': instrument,
        }
        
        response = self.public_get_quote(self.extend(request, params))
        ticker_data = self.safe_value(response['data'], instrument)
        
        return self.parse_ticker(ticker_data, market)

    def parse_ticker(self, ticker, market=None):
        """
        Parses ticker data from Zerodha format to CCXT unified structure
        
        @param {dict} ticker raw ticker data from the exchange
        @param {dict} market market structure
        @returns {dict} a ticker structure
        """
        timestamp = self.parse8601(self.safe_string(ticker, 'timestamp'))
        last = self.safe_number(ticker, 'last_price')
        ohlc = self.safe_value(ticker, 'ohlc', {})
        depth = self.safe_value(ticker, 'depth', {})
        buy_depth = self.safe_value(depth, 'buy', [])
        sell_depth = self.safe_value(depth, 'sell', [])
        
        bid = self.safe_number(buy_depth[0], 'price') if len(buy_depth) > 0 else None
        ask = self.safe_number(sell_depth[0], 'price') if len(sell_depth) > 0 else None
        bid_volume = self.safe_number(buy_depth[0], 'quantity') if len(buy_depth) > 0 else None
        ask_volume = self.safe_number(sell_depth[0], 'quantity') if len(sell_depth) > 0 else None
        
        symbol = self.safe_string(market, 'symbol')
        
        return self.safe_ticker({
            'symbol': symbol,
            'timestamp': timestamp,
            'datetime': self.iso8601(timestamp),
            'high': self.safe_number(ohlc, 'high'),
            'low': self.safe_number(ohlc, 'low'),
            'bid': bid,
            'bidVolume': bid_volume,
            'ask': ask,
            'askVolume': ask_volume,
            'vwap': None,
            'open': self.safe_number(ohlc, 'open'),
            'close': last,
            'last': last,
            'previousClose': self.safe_number(ohlc, 'close'),
            'change': None,
            'percentage': None,
            'average': None,
            'baseVolume': self.safe_number(ticker, 'volume'),
            'quoteVolume': None,
            'info': ticker,
        }, market)

    def fetch_tickers(self, symbols=None, params={}):
        """
        Fetches price tickers for multiple symbols
        Implemented by making multiple fetchTicker calls due to Zerodha API limitations
        
        @param {list} symbols list of unified symbols to fetch tickers for, if None fetches all
        @param {dict} params extra parameters specific to the exchange API endpoint
        @returns {dict} a dictionary of ticker structures
        """
        self.load_markets()
        
        if symbols is None:
            symbols = list(self.symbols)
        elif isinstance(symbols, str):
            symbols = [symbols]
        
        # For large numbers of symbols, we should consider batching to avoid rate limits
        # Zerodha allows 10 requests per second, so we batch the requests
        tickers = {}
        
        # Use batch processing to respect rate limits
        batch_size = 8  # Conservative batch size to stay under rate limits
        for i in range(0, len(symbols), batch_size):
            batch_symbols = symbols[i:i + batch_size]
            
            # Make concurrent requests for each batch
            batch_results = []
            for symbol in batch_symbols:
                try:
                    ticker = self.fetch_ticker(symbol, params)
                    tickers[symbol] = ticker
                except Exception as e:
                    # Skip symbols that fail to fetch, but continue with others
                    self.log('fetch_tickers failed for symbol', symbol, str(e))
                    continue
            
            # Small delay between batches to respect rate limits (100ms as per rateLimit)
            if i + batch_size < len(symbols):
                self.sleep(0.1)  # 100ms delay
        
        return tickers

    def fetch_ohlcv(self, symbol, timeframe='1m', since=None, limit=None, params={}):
        """
        Fetches historical candlestick data for backtesting
        
        @param {str} symbol unified symbol of the market to fetch OHLCV data for
        @param {str} timeframe the length of time each candle represents
        @param {int} since timestamp in ms of the earliest candle to fetch
        @param {int} limit the maximum amount of candles to fetch
        @param {dict} params extra parameters specific to the exchange API endpoint
        @returns {list} A list of candles ordered as timestamp, open, high, low, close, volume
        """
        self.load_markets()
        market = self.market(symbol)
        
        request = {
            'instrument_token': market['id'],
            'interval': self.safe_string(self.timeframes, timeframe, timeframe),
        }
        
        # Calculate date range based on since and limit
        if since is not None:
            request['from'] = self.yyyymmdd(since, '-')
        else:
            # Default to last 30 days if no since parameter
            now = self.milliseconds()
            thirty_days_ago = now - (30 * 24 * 60 * 60 * 1000)
            request['from'] = self.yyyymmdd(thirty_days_ago, '-')
        
        # Set 'to' date to today
        request['to'] = self.yyyymmdd(self.milliseconds(), '-')
        
        response = self.private_get_instruments_historical_instrument_token_interval(self.extend(request, params))
        candles = self.safe_value(response['data'], 'candles', [])
        
        return self.parse_ohlcvs(candles, market, timeframe, since, limit)

    def parse_ohlcv(self, ohlcv, market=None):
        """
        Parses OHLCV data from Zerodha format to CCXT unified structure
        
        @param {list} ohlcv raw OHLCV data from the exchange
        @param {dict} market market structure
        @returns {list} OHLCV array [timestamp, open, high, low, close, volume]
        """
        return [
            self.parse8601(ohlcv[0]),
            self.safe_number(ohlcv, 1),  # open
            self.safe_number(ohlcv, 2),  # high
            self.safe_number(ohlcv, 3),  # low
            self.safe_number(ohlcv, 4),  # close
            self.safe_number(ohlcv, 5),  # volume
        ]

    def fetch_balance(self, params={}):
        """
        Fetches account balance including cash and stock holdings
        
        @param {dict} params extra parameters specific to the exchange API endpoint
        @returns {dict} a balance structure
        """
        self.load_markets()
        
        # Fetch both cash margins and stock holdings
        margin_response = self.private_get_user_margins(params)
        holdings_response = self.private_get_portfolio_holdings(params)
        
        result = {
            'info': {
                'margins': margin_response,
                'holdings': holdings_response,
            },
        }
        
        # Parse cash balance from margins
        equity_margins = self.safe_value(margin_response['data'], 'equity')
        if equity_margins:
            available = self.safe_value(equity_margins, 'available', {})
            cash_available = self.safe_number(available, 'cash', 0)
            net_balance = self.safe_number(equity_margins, 'net', 0)
            
            result['INR'] = self.account()
            result['INR']['free'] = cash_available
            result['INR']['total'] = net_balance
            result['INR']['used'] = max(0, net_balance - cash_available)
        
        # Parse stock holdings
        holdings = self.safe_value(holdings_response['data'], 'holdings', [])
        for holding in holdings:
            trading_symbol = self.safe_string(holding, 'tradingsymbol')
            exchange = self.safe_string(holding, 'exchange')
            quantity = self.safe_number(holding, 'quantity', 0)
            
            # Find the market to get unified symbol
            market_id = exchange + ':' + trading_symbol + '/INR'
            market = self.safe_market(market_id)
            
            if market and quantity > 0:
                base = market['base']
                result[base] = self.account()
                result[base]['total'] = quantity
                result[base]['free'] = quantity  # Assuming all holdings are free to trade
                result[base]['used'] = 0
        
        return self.safe_balance(result)

    def create_order(self, symbol, type, side, amount, price=None, params={}):
        """
        Creates a new order
        
        @param {str} symbol unified symbol of the market to create an order in
        @param {str} type 'market' or 'limit'
        @param {str} side 'buy' or 'sell'
        @param {float} amount how much you want to trade in units of base currency
        @param {float} price the price at which the order is to be fulfilled, ignored in market orders
        @param {dict} params extra parameters specific to the exchange API endpoint
        @param {str} params.product 'CNC' for Cash and Carry, 'MIS' for Margin Intraday (REQUIRED)
        @param {str} params.variety 'regular', 'amo', 'co' (default: 'regular')
        @param {str} params.validity 'DAY', 'IOC' (default: 'DAY')
        @param {float} params.trigger_price trigger price for stop orders
        @returns {dict} an order structure
        """
        self.load_markets()
        market = self.market(symbol)
        
        # Product parameter is mandatory for Zerodha
        product = self.safe_string(params, 'product')
        if product is None:
            raise InvalidOrder(self.id + ' createOrder() requires the "product" parameter (e.g., "CNC", "MIS") in params')
        
        variety = self.safe_string(params, 'variety', 'regular')
        validity = self.safe_string(params, 'validity', 'DAY')
        
        request = {
            'variety': variety,
            'tradingsymbol': market['baseId'],
            'exchange': market['info']['exchange'],
            'transaction_type': side.upper(),
            'order_type': type.upper(),
            'quantity': self.amount_to_precision(symbol, amount),
            'product': product.upper(),
            'validity': validity.upper(),
        }
        
        if type == 'limit':
            if price is None:
                raise InvalidOrder(self.id + ' createOrder() requires a price argument for limit orders')
            request['price'] = self.price_to_precision(symbol, price)
        
        trigger_price = self.safe_number(params, 'trigger_price')
        if trigger_price is not None:
            request['trigger_price'] = self.price_to_precision(symbol, trigger_price)
        
        omitted = self.omit(params, ['product', 'variety', 'validity', 'trigger_price'])
        response = self.private_post_orders_variety(self.extend(request, omitted))
        
        order_id = self.safe_string(response['data'], 'order_id')
        return self.safe_order({
            'id': order_id,
            'info': response,
        }, market)

    def cancel_order(self, id, symbol=None, params={}):
        """
        Cancels an existing order
        
        @param {str} id order id
        @param {str} symbol unified symbol of the market the order was made in
        @param {dict} params extra parameters specific to the exchange API endpoint
        @param {str} params.variety 'regular', 'amo', 'co' (default: 'regular')
        @returns {dict} An order structure
        """
        variety = self.safe_string(params, 'variety', 'regular')
        
        request = {
            'variety': variety,
            'order_id': id,
        }
        
        omitted = self.omit(params, ['variety'])
        response = self.private_delete_orders_variety_order_id(self.extend(request, omitted))
        
        return self.parse_order(response['data'])

    def fetch_order(self, id, symbol=None, params={}):
        """
        Fetches information about a specific order
        
        @param {str} id order id
        @param {str} symbol unified symbol of the market the order was made in
        @param {dict} params extra parameters specific to the exchange API endpoint
        @returns {dict} An order structure
        """
        request = {
            'order_id': id,
        }
        
        response = self.private_get_orders_order_id(self.extend(request, params))
        orders = self.safe_value(response, 'data', [])
        
        if not isinstance(orders, list) or len(orders) == 0:
            raise InvalidOrder(self.id + ' order ' + id + ' not found')
        
        return self.parse_order(orders[0])

    def fetch_open_orders(self, symbol=None, since=None, limit=None, params={}):
        """
        Fetches all open orders
        
        @param {str} symbol unified market symbol
        @param {int} since the earliest time in ms to fetch open orders for
        @param {int} limit the maximum number of open orders structures to retrieve
        @param {dict} params extra parameters specific to the exchange API endpoint
        @returns {list} a list of order structures
        """
        self.load_markets()
        
        response = self.private_get_orders(params)
        orders = self.safe_value(response, 'data', [])
        
        open_statuses = ['OPEN', 'TRIGGER PENDING']
        open_orders = [order for order in orders if self.safe_string(order, 'status') in open_statuses]
        
        return self.parse_orders(open_orders, None, since, limit)

    def fetch_closed_orders(self, symbol=None, since=None, limit=None, params={}):
        """
        Fetches all closed orders
        
        @param {str} symbol unified market symbol of the market orders were made in
        @param {int} since the earliest time in ms to fetch orders for
        @param {int} limit the maximum number of order structures to retrieve
        @param {dict} params extra parameters specific to the exchange API endpoint
        @returns {list} a list of order structures
        """
        self.load_markets()
        
        response = self.private_get_orders(params)
        orders = self.safe_value(response, 'data', [])
        
        closed_statuses = ['COMPLETE', 'CANCELLED', 'REJECTED']
        closed_orders = [order for order in orders if self.safe_string(order, 'status') in closed_statuses]
        
        return self.parse_orders(closed_orders, None, since, limit)

    def fetch_my_trades(self, symbol=None, since=None, limit=None, params={}):
        """
        Fetches user's trade history
        
        @param {str} symbol unified market symbol
        @param {int} since the earliest time in ms to fetch trades for
        @param {int} limit the maximum number of trades structures to retrieve
        @param {dict} params extra parameters specific to the exchange API endpoint
        @returns {list} a list of trade structures
        """
        self.load_markets()
        
        response = self.private_get_trades(params)
        trades = self.safe_value(response, 'data', [])
        
        return self.parse_trades(trades, None, since, limit)

    def parse_order(self, order, market=None):
        """
        Parses an order from Zerodha format to CCXT unified structure
        
        @param {dict} order raw order data from the exchange
        @param {dict} market market structure
        @returns {dict} an order structure
        """
        status_map = {
            'OPEN': 'open',
            'TRIGGER PENDING': 'open',
            'COMPLETE': 'closed',
            'CANCELLED': 'canceled',
            'REJECTED': 'rejected',
        }
        
        id = self.safe_string(order, 'order_id')
        status = self.safe_string(status_map, self.safe_string(order, 'status'))
        exchange = self.safe_string(order, 'exchange')
        trading_symbol = self.safe_string(order, 'tradingsymbol')
        market_id = exchange + ':' + trading_symbol + '/INR'
        market = self.safe_market(market_id, market)
        symbol = self.safe_string(market, 'symbol')
        
        timestamp = self.parse8601(self.safe_string(order, 'order_timestamp'))
        type = self.safe_string_lower(order, 'order_type')
        side = self.safe_string_lower(order, 'transaction_type')
        amount = self.safe_number(order, 'quantity')
        filled = self.safe_number(order, 'filled_quantity')
        remaining = self.safe_number(order, 'pending_quantity')
        price = self.safe_number(order, 'price')
        average = self.safe_number(order, 'average_price')
        stop_price = self.safe_number(order, 'trigger_price')
        
        cost = None
        if filled is not None and average is not None:
            cost = filled * average
        
        return self.safe_order({
            'info': order,
            'id': id,
            'clientOrderId': self.safe_string(order, 'tag'),
            'timestamp': timestamp,
            'datetime': self.iso8601(timestamp),
            'lastTradeTimestamp': None,
            'symbol': symbol,
            'type': type,
            'timeInForce': self.safe_string_upper(order, 'validity'),
            'postOnly': None,
            'side': side,
            'amount': amount,
            'price': price,
            'stopPrice': stop_price,
            'triggerPrice': stop_price,
            'cost': cost,
            'average': average,
            'filled': filled,
            'remaining': remaining,
            'status': status,
            'fee': None,  # Fee information is typically in trade data
            'trades': [],
        }, market)

    def parse_trade(self, trade, market=None):
        """
        Parses a trade from Zerodha format to CCXT unified structure
        
        @param {dict} trade raw trade data from the exchange
        @param {dict} market market structure
        @returns {dict} a trade structure
        """
        id = self.safe_string(trade, 'trade_id')
        order_id = self.safe_string(trade, 'order_id')
        exchange = self.safe_string(trade, 'exchange')
        trading_symbol = self.safe_string(trade, 'tradingsymbol')
        market_id = exchange + ':' + trading_symbol + '/INR'
        market = self.safe_market(market_id, market)
        symbol = self.safe_string(market, 'symbol')
        
        timestamp = self.parse8601(self.safe_string(trade, 'fill_timestamp'))
        side = self.safe_string_lower(trade, 'transaction_type')
        amount = self.safe_number(trade, 'quantity')
        price = self.safe_number(trade, 'price')
        
        cost = None
        if amount is not None and price is not None:
            cost = amount * price
        
        return self.safe_trade({
            'info': trade,
            'id': id,
            'order': order_id,
            'timestamp': timestamp,
            'datetime': self.iso8601(timestamp),
            'symbol': symbol,
            'type': None,
            'side': side,
            'amount': amount,
            'price': price,
            'cost': cost,
            'fee': None,  # Fee calculation would need additional data
        }, market)

    def sign(self, path, api='public', method='GET', params={}, headers=None, body=None):
        """Sign the request with session-based authentication"""
        url = self.urls['api'][api] + '/' + self.implode_params(path, params)
        query = self.omit(params, self.extract_params(path))
        
        # Always add auth headers for quote endpoints
        if api == 'private' or path in ['quote', 'quote/ltp', 'quote/ohlc']:
            if not self.apiKey or not self.access_token:
                self._load_credentials_from_cache()
            if not self.apiKey or not self.access_token:
                raise AuthenticationError(self.id + ' requires apiKey and access_token for authentication')
            if headers is None:
                headers = {}
            headers['X-KiteConnect-ApiKey'] = self.apiKey
            headers['Authorization'] = f'token {self.apiKey}:{self.access_token}'
        
        if method == 'GET':
            if query:
                url += '?' + self.urlencode(query)
        else:
            if query:
                body = self.urlencode(query)
                if headers is None:
                    headers = {}
                headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        return {'url': url, 'method': method, 'body': body, 'headers': headers}

    def handle_errors(self, code, reason, url, method, headers, body, response, requestHeaders, requestBody):
        """
        Handles API errors and maps them to CCXT exceptions
        
        @param {int} code HTTP status code
        @param {str} reason HTTP status text
        @param {str} url request URL
        @param {str} method HTTP method
        @param {dict} headers response headers
        @param {str} body response body
        @param {dict} response parsed response
        @param {dict} requestHeaders request headers
        @param {str} requestBody request body
        """
        if response is None:
            return
        
        # Zerodha API returns errors in this format:
        # {"status": "error", "message": "Error message", "error_type": "TokenException"}
        status = self.safe_string(response, 'status')
        if status == 'error':
            error_type = self.safe_string(response, 'error_type')
            message = self.safe_string(response, 'message')
            feedback = self.id + ' ' + message
            
            self.throw_exactly_matched_exception(self.exceptions['exact'], error_type, feedback)
            self.throw_broadly_matched_exception(self.exceptions['broad'], message, feedback)
            
            raise ExchangeError(feedback)
        
        # Handle rate limit errors
        if code == 429:
            raise RateLimitExceeded(self.id + ' rate limit exceeded')
        
        # Handle server errors
        if code >= 500:
            raise ExchangeNotAvailable(self.id + ' server error: ' + body)
