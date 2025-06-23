# -*- coding: utf-8 -*-

import struct
import json
import asyncio
import websockets
from typing import Dict, List, Optional, Any
from ccxt.async_support.zerodha import zerodha as zerodhaRest


class zerodha(zerodhaRest):
    """
    Zerodha Kite Connect WebSocket API implementation for CCXT Pro
    
    This implementation extends the REST API with real-time WebSocket streaming
    for live market data, order updates, and trade notifications.
    
    WebSocket Features:
    - Real-time ticker data (LTP, Quote, Full modes)
    - Live order book updates
    - Order status updates
    - Trade notifications
    - Support for up to 3000 instruments per connection
    """
    
    def __init__(self, config={}):
        super().__init__(config)
        self.ws = None
        self.ws_connected = False
        self.event_handlers = {}
        self.subscribed_instruments = set()
        self.ws_task = None
        
    def describe(self):
        return self.deep_extend(super(zerodha, self).describe(), {
            'has': {
                'ws': True,
                'watchTicker': True,
                'watchTickers': True,
                'watchOrderBook': True,
                'watchOHLCV': False,  # Not directly supported, would need to build from ticks
                'watchTrades': False,  # Not directly supported
                'watchOrders': True,
                'watchMyTrades': True,
                'watchBalance': False,  # Not directly supported
                'watchPositions': False,  # Not directly supported
            },
            'urls': {
                'api': {
                    'ws': 'wss://ws.kite.trade',
                },
            },
            'options': {
                'ws': {
                    'defaultMode': 'quote',  # 'ltp', 'quote', or 'full'
                    'maxInstruments': 3000,
                    'heartbeatInterval': 2000,
                },
            },
            'streaming': {
                'keepAlive': 2000,
            },
        })

    def get_ws_url(self):
        """Get WebSocket URL with authentication parameters"""
        if not self.apiKey or not self.access_token:
            self._load_credentials_from_cache()
        
        if not self.apiKey or not self.access_token:
            raise Exception('WebSocket requires apiKey and access_token')
        
        url = self.urls['api']['ws']
        url += f'?api_key={self.apiKey}&access_token={self.access_token}'
        return url

    async def _handle_ws_message(self, message):
        """Handle incoming WebSocket messages"""
        try:
            # Check if message is binary (market data) or text (postbacks/updates)
            if isinstance(message, bytes):
                # Binary message - parse market data
                packets = self.parse_binary_message(message)
                for packet in packets:
                    await self._handle_tick(packet)
            else:
                # Text message - parse JSON
                try:
                    data = json.loads(message)
                    await self._handle_text_message(data)
                except json.JSONDecodeError:
                    # Ignore non-JSON messages (like heartbeats)
                    pass
        except Exception as e:
            self.log(f"Error handling WebSocket message: {e}")

    async def _handle_tick(self, tick):
        """Process individual tick data"""
        instrument_token = tick.get('instrument_token')
        if not instrument_token:
            return
        
        # Find market by instrument token
        market = None
        for symbol, market_info in self.markets.items():
            if market_info['id'] == str(instrument_token):
                market = market_info
                break
        
        if not market:
            return
        
        # Create ticker structure from tick data
        ticker = {
            'symbol': market['symbol'],
            'timestamp': tick.get('exchange_timestamp', self.milliseconds()),
            'datetime': self.iso8601(tick.get('exchange_timestamp', self.milliseconds())),
            'high': tick.get('high_price'),
            'low': tick.get('low_price'),
            'bid': None,
            'bidVolume': None,
            'ask': None,
            'askVolume': None,
            'vwap': None,
            'open': tick.get('open_price'),
            'close': tick.get('close_price'),
            'last': tick.get('last_price'),
            'previousClose': tick.get('close_price'),
            'change': None,
            'percentage': None,
            'average': tick.get('average_traded_price'),
            'baseVolume': tick.get('volume_traded'),
            'quoteVolume': None,
            'info': tick,
        }
        
        # Add bid/ask from depth if available
        depth = tick.get('depth', {})
        if depth:
            buy_depth = depth.get('buy', [])
            sell_depth = depth.get('sell', [])
            
            if buy_depth:
                ticker['bid'] = buy_depth[0].get('price')
                ticker['bidVolume'] = buy_depth[0].get('quantity')
            
            if sell_depth:
                ticker['ask'] = sell_depth[0].get('price')
                ticker['askVolume'] = sell_depth[0].get('quantity')
        
        # Update tickers cache
        self.tickers[market['symbol']] = ticker
        
        # Emit ticker update
        self._emit_event('ticker', ticker)

    async def _handle_text_message(self, data):
        """Handle text WebSocket messages (postbacks, errors, etc.)"""
        message_type = data.get('type')
        message_data = data.get('data', {})
        
        if message_type == 'order':
            # Handle order update
            order = self.parse_order(message_data)
            self._emit_event('order', order)
        elif message_type == 'error':
            # Handle error
            error_msg = message_data
            self.log(f"WebSocket error: {error_msg}")
        elif message_type == 'message':
            # Handle broker message
            msg = message_data
            self.log(f"Broker message: {msg}")

    def _emit_event(self, event, data):
        """Emit event to registered handlers"""
        if event in self.event_handlers:
            for handler in self.event_handlers[event]:
                try:
                    # Run handler in event loop if it's async
                    if asyncio.iscoroutinefunction(handler):
                        asyncio.create_task(handler(data))
                    else:
                        handler(data)
                except Exception as e:
                    self.log(f"Error in event handler for {event}: {e}")

    def parse_binary_quote_packet(self, data: bytes, mode: str = 'quote') -> Dict[str, Any]:
        """Parse binary quote packet according to Zerodha's specification"""
        if len(data) < 8:
            return {}
        
        # Parse basic fields
        instrument_token = struct.unpack('>I', data[0:4])[0]
        last_price = struct.unpack('>I', data[4:8])[0] / 100.0  # Convert from paise
        
        result = {
            'instrument_token': instrument_token,
            'last_price': last_price,
        }
        
        if mode == 'ltp':
            return result
        
        if len(data) < 44:
            return result
        
        # Parse quote fields
        result.update({
            'last_traded_quantity': struct.unpack('>I', data[8:12])[0],
            'average_traded_price': struct.unpack('>I', data[12:16])[0] / 100.0,
            'volume_traded': struct.unpack('>I', data[16:20])[0],
            'total_buy_quantity': struct.unpack('>I', data[20:24])[0],
            'total_sell_quantity': struct.unpack('>I', data[24:28])[0],
            'open_price': struct.unpack('>I', data[28:32])[0] / 100.0,
            'high_price': struct.unpack('>I', data[32:36])[0] / 100.0,
            'low_price': struct.unpack('>I', data[36:40])[0] / 100.0,
            'close_price': struct.unpack('>I', data[40:44])[0] / 100.0,
        })
        
        if mode == 'quote':
            return result
        
        if len(data) < 184:
            return result
        
        # Parse full fields
        result.update({
            'last_traded_timestamp': struct.unpack('>I', data[44:48])[0],
            'open_interest': struct.unpack('>I', data[48:52])[0],
            'open_interest_day_high': struct.unpack('>I', data[52:56])[0],
            'open_interest_day_low': struct.unpack('>I', data[56:60])[0],
            'exchange_timestamp': struct.unpack('>I', data[60:64])[0],
        })
        
        # Parse market depth (5 bids + 5 asks)
        depth = {'buy': [], 'sell': []}
        
        # Parse bid entries (bytes 64-124)
        for i in range(5):
            offset = 64 + (i * 12)
            if offset + 12 <= len(data):
                quantity = struct.unpack('>I', data[offset:offset+4])[0]
                price = struct.unpack('>I', data[offset+4:offset+8])[0] / 100.0
                orders = struct.unpack('>H', data[offset+8:offset+10])[0]
                depth['buy'].append({
                    'quantity': quantity,
                    'price': price,
                    'orders': orders
                })
        
        # Parse ask entries (bytes 124-184)
        for i in range(5):
            offset = 124 + (i * 12)
            if offset + 12 <= len(data):
                quantity = struct.unpack('>I', data[offset:offset+4])[0]
                price = struct.unpack('>I', data[offset+4:offset+8])[0] / 100.0
                orders = struct.unpack('>H', data[offset+8:offset+10])[0]
                depth['sell'].append({
                    'quantity': quantity,
                    'price': price,
                    'orders': orders
                })
        
        result['depth'] = depth
        return result

    def parse_binary_message(self, data: bytes) -> List[Dict[str, Any]]:
        """Parse binary WebSocket message containing multiple quote packets"""
        if len(data) < 4:
            return []
        
        # Parse header
        num_packets = struct.unpack('>H', data[0:2])[0]
        packets = []
        
        offset = 4
        for i in range(num_packets):
            if offset + 2 > len(data):
                break
            
            # Get packet length
            packet_length = struct.unpack('>H', data[offset:offset+2])[0]
            offset += 2
            
            if offset + packet_length > len(data):
                break
            
            # Extract packet data
            packet_data = data[offset:offset+packet_length]
            offset += packet_length
            
            # Parse packet (assuming quote mode for now)
            packet = self.parse_binary_quote_packet(packet_data, 'quote')
            if packet:
                packets.append(packet)
        
        return packets

    async def watch_ticker(self, symbol, params={}):
        """Watch a price ticker for a specific symbol"""
        await self.load_markets()
        market = self.market(symbol)
        instrument_token = int(market['id'])
        
        # Get mode from params or use default
        mode = self.safe_string(params, 'mode', self.options['ws']['defaultMode'])
        
        # Subscribe to the instrument
        await self.subscribe_to_instrument(instrument_token, mode)
        
        # Return the current ticker (will be updated via WebSocket)
        return await self.fetch_ticker(symbol, params)

    async def watch_tickers(self, symbols: Optional[List[str]] = None, params={}):
        """Watch price tickers for multiple symbols"""
        await self.load_markets()
        
        if symbols is None:
            symbols = list(self.symbols)
        
        # Limit to max instruments per connection
        max_instruments = self.options['ws']['maxInstruments']
        if len(symbols) > max_instruments:
            raise ValueError(f'Cannot subscribe to more than {max_instruments} instruments')
        
        # Get mode from params or use default
        mode = self.safe_string(params, 'mode', self.options['ws']['defaultMode'])
        
        # Get instrument tokens
        instrument_tokens = []
        for symbol in symbols:
            market = self.market(symbol)
            instrument_tokens.append(int(market['id']))
        
        # Subscribe to all instruments
        await self.subscribe_to_instruments(instrument_tokens, mode)
        
        # Return current tickers (will be updated via WebSocket)
        return await self.fetch_tickers(symbols, params)

    async def watch_order_book(self, symbol, limit=None, params={}):
        """Watch order book updates for a specific symbol"""
        await self.load_markets()
        market = self.market(symbol)
        instrument_token = int(market['id'])
        
        # Subscribe in 'full' mode to get market depth
        await self.subscribe_to_instrument(instrument_token, 'full')
        
        # Return current order book (will be updated via WebSocket)
        ticker = await self.fetch_ticker(symbol, params)
        return self.parse_order_book_from_ticker(ticker, symbol)

    async def watch_orders(self, symbol=None, since=None, limit=None, params={}):
        """Watch order updates"""
        # Order updates come through WebSocket automatically
        # Return current open orders (will be updated via WebSocket)
        return await self.fetch_open_orders(symbol, since, limit, params)

    async def watch_my_trades(self, symbol=None, since=None, limit=None, params={}):
        """Watch trade updates"""
        # Trade updates come through WebSocket automatically
        # Return current trades (will be updated via WebSocket)
        return await self.fetch_my_trades(symbol, since, limit, params)

    async def subscribe_to_instrument(self, instrument_token: int, mode: str = 'quote'):
        """Subscribe to a single instrument by token"""
        # Add to subscribed instruments set
        self.subscribed_instruments.add(instrument_token)
        
        # Send subscription message if connected
        if self.ws_connected and self.ws:
            message = {
                'a': 'subscribe',
                'v': [instrument_token]
            }
            
            # Set mode if not default
            if mode != self.options['ws']['defaultMode']:
                mode_message = {
                    'a': 'mode',
                    'v': [mode, [instrument_token]]
                }
                await self.ws.send(json.dumps(mode_message))
            
            await self.ws.send(json.dumps(message))

    async def subscribe_to_instruments(self, instrument_tokens: List[int], mode: str = 'quote'):
        """Subscribe to multiple instruments by tokens"""
        if len(instrument_tokens) > self.options['ws']['maxInstruments']:
            raise ValueError(f'Cannot subscribe to more than {self.options["ws"]["maxInstruments"]} instruments')
        
        # Add to subscribed instruments set
        self.subscribed_instruments.update(instrument_tokens)
        
        # Send subscription message if connected
        if self.ws_connected and self.ws:
            message = {
                'a': 'subscribe',
                'v': instrument_tokens
            }
            
            # Set mode if not default
            if mode != self.options['ws']['defaultMode']:
                mode_message = {
                    'a': 'mode',
                    'v': [mode, instrument_tokens]
                }
                await self.ws.send(json.dumps(mode_message))
            
            await self.ws.send(json.dumps(message))

    async def subscribe_to_token(self, instrument_token: int, mode: str = 'quote'):
        """Subscribe to an instrument by token (direct method)"""
        return await self.subscribe_to_instrument(instrument_token, mode)

    async def subscribe_to_tokens(self, instrument_tokens: List[int], mode: str = 'quote'):
        """Subscribe to multiple instruments by tokens (direct method)"""
        return await self.subscribe_to_instruments(instrument_tokens, mode)

    async def unsubscribe_from_instrument(self, instrument_token: int):
        """Unsubscribe from a single instrument"""
        self.subscribed_instruments.discard(instrument_token)
        
        if self.ws_connected and self.ws:
            message = {
                'a': 'unsubscribe',
                'v': [instrument_token]
            }
            await self.ws.send(json.dumps(message))

    async def unsubscribe_from_instruments(self, instrument_tokens: List[int]):
        """Unsubscribe from multiple instruments"""
        for token in instrument_tokens:
            self.subscribed_instruments.discard(token)
        
        if self.ws_connected and self.ws:
            message = {
                'a': 'unsubscribe',
                'v': instrument_tokens
            }
            await self.ws.send(json.dumps(message))

    async def unsubscribe_from_token(self, instrument_token: int):
        """Unsubscribe from an instrument by token (direct method)"""
        return await self.unsubscribe_from_instrument(instrument_token)

    async def unsubscribe_from_tokens(self, instrument_tokens: List[int]):
        """Unsubscribe from multiple instruments by tokens (direct method)"""
        return await self.unsubscribe_from_instruments(instrument_tokens)

    def parse_order_book_from_ticker(self, ticker, symbol):
        """Parse order book from ticker depth data"""
        depth = self.safe_value(ticker, 'info', {}).get('depth', {})
        bids = self.safe_value(depth, 'buy', [])
        asks = self.safe_value(depth, 'sell', [])
        
        order_book = {
            'symbol': symbol,
            'bids': [[self.safe_number(bid, 'price'), self.safe_number(bid, 'quantity')] for bid in bids],
            'asks': [[self.safe_number(ask, 'price'), self.safe_number(ask, 'quantity')] for ask in asks],
            'timestamp': ticker.get('timestamp'),
            'datetime': ticker.get('datetime'),
            'nonce': None,
        }
        return order_book

    async def _ws_loop(self):
        """WebSocket connection loop"""
        url = self.get_ws_url()
        
        try:
            async with websockets.connect(url) as websocket:
                self.ws = websocket
                self.ws_connected = True
                self.log("WebSocket connected successfully")
                
                # Resubscribe to previously subscribed instruments
                if self.subscribed_instruments:
                    instrument_tokens = list(self.subscribed_instruments)
                    message = {
                        'a': 'subscribe',
                        'v': instrument_tokens
                    }
                    await websocket.send(json.dumps(message))
                
                # Keep connection alive and handle messages
                async for message in websocket:
                    await self._handle_ws_message(message)
                    
        except Exception as e:
            self.log(f"WebSocket error: {e}")
        finally:
            self.ws_connected = False
            self.ws = None

    async def connect(self):
        """Connect to WebSocket"""
        if not self.ws_connected:
            self.ws_task = asyncio.create_task(self._ws_loop())
            
            # Wait for connection
            timeout = 10  # 10 seconds timeout
            start_time = asyncio.get_event_loop().time()
            while not self.ws_connected:
                if asyncio.get_event_loop().time() - start_time > timeout:
                    raise Exception("WebSocket connection timeout")
                await asyncio.sleep(0.1)

    def on(self, event, callback):
        """Register event listener"""
        if event not in self.event_handlers:
            self.event_handlers[event] = []
        self.event_handlers[event].append(callback)

    async def close(self):
        """Close WebSocket connection"""
        if self.ws_task:
            self.ws_task.cancel()
            try:
                await self.ws_task
            except asyncio.CancelledError:
                pass
        
        if self.ws:
            await self.ws.close()
        
        self.ws_connected = False
        self.ws = None
        
        await super().close() 