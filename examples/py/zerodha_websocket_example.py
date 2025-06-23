#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Zerodha WebSocket Example using CCXT Pro

This example demonstrates how to use the Zerodha WebSocket API through CCXT Pro
to receive real-time market data and order updates.

Prerequisites:
1. Install kiteconnect: pip install kiteconnect
2. Generate access token using the auto token script
3. Ensure you have valid API credentials

Usage:
    python zerodha_websocket_example.py
"""

import asyncio
import sys
import os

# Add the ccxt directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'python'))

async def main():
    """Main function to demonstrate WebSocket functionality"""
    
    # Import the WebSocket exchange
    from ccxt.pro.zerodha import zerodha
    
    # Initialize the exchange with your credentials
    # The exchange will automatically load api_key and access_token from cache
    exchange = zerodha({
        'sandbox': False,  # Set to True for paper trading
        'enableRateLimit': True,
    })
    
    print("Initializing Zerodha WebSocket connection...")
    
    try:
        # Load markets first
        print("Loading markets...")
        await exchange.load_markets()
        print(f"Loaded {len(exchange.markets)} markets")
        
        # Connect to WebSocket
        print("Connecting to WebSocket...")
        await exchange.connect()
        print("WebSocket connected successfully!")
        
        # Register event handlers
        def on_ticker(ticker):
            print(f"Ticker update for {ticker['symbol']}: LTP={ticker['last']}, Volume={ticker['baseVolume']}")
        
        def on_order(order):
            print(f"Order update: {order['id']} - {order['status']} - {order['symbol']}")
        
        def on_error(error):
            print(f"Error: {error}")
        
        exchange.on('ticker', on_ticker)
        exchange.on('order', on_order)
        exchange.on('error', on_error)
        
        # Subscribe to some popular instruments
        # Let's subscribe to NIFTY and BANKNIFTY futures using their instrument tokens
        instrument_tokens_to_watch = [
            738561,  # NIFTY 50
            5633,    # BANK NIFTY
            2885,    # RELIANCE
            11536,   # TCS
        ]
        
        print(f"Subscribing to {len(instrument_tokens_to_watch)} instrument tokens...")
        
        # Subscribe to tickers using instrument tokens directly
        for token in instrument_tokens_to_watch:
            try:
                await exchange.subscribe_to_token(token)
                print(f"Subscribed to instrument token: {token}")
            except Exception as e:
                print(f"Failed to subscribe to token {token}: {e}")
        
        # Subscribe to order book for NIFTY (using token)
        try:
            await exchange.subscribe_to_token(738561, 'full')  # NIFTY in full mode for depth
            print("Subscribed to NIFTY order book (full mode)")
        except Exception as e:
            print(f"Failed to subscribe to order book: {e}")
        
        print("\nListening for real-time updates...")
        print("Press Ctrl+C to stop")
        
        # Keep the connection alive and listen for updates
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping WebSocket connection...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Close the connection
        await exchange.close()
        print("WebSocket connection closed")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 